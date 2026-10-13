"""Farmer-facing Streamlit workflow wired to FieldShift's real modules."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .climate_features import FeatureValidationError, seasonal_precipitation_total, temperature_summary
from .climate_trends import (
    REGIONAL_SEASONS,
    SeasonDefinition,
    audit_variable_coverage,
    calculate_linear_trend,
    compute_annual_season_summaries,
)
from .data_access import source_statuses
from .nasa_power import (
    DEMO_LATITUDE,
    DEMO_LONGITUDE,
    PowerClient,
    PowerDataset,
    PowerError,
    PowerRequest,
    load_offline_demo_snapshot,
    parse_power_daily_response,
)
from .rotation_engine import (
    METRICS,
    ClimateContext,
    FarmProfile,
    RotationEngine,
    RotationInputError,
    SoilInformation,
    normalize_weights,
)
from .scenarios import ScenarioInputError, build_scenarios, evaluate_robustness, pareto_assess, transform_climate_frame
from .soil_data import (
    ESTIMATE_LABEL,
    MANUAL_SOURCE_TYPES,
    SOILGRIDS_ACCESS_URL,
    SOILGRIDS_DEPTHS,
    SOILGRIDS_FAIR_USE,
    SOILGRIDS_PROPERTIES,
    SOURCE_LABELS,
    ManualSoilEntry,
    ResolvedSoil,
    SoilGridsClient,
    SoilGridsError,
    SoilGridsEstimate,
    resolve_soil_values,
)
from .soil_nutrient_model import build_soil_state_report
from .future_climate import (
    ASSUMPTIONS as PROJECTION_ASSUMPTIONS,
    INDICATOR_LABELS,
    REFERENCE_EXPERIMENT,
    SCENARIO_LABELS,
    SHORT_LABELS,
    ProjectionDataError,
    ProjectionExtract,
    climate_changes,
    compare_plan,
    ensemble_median,
    load_extract,
)
from .land_use_phenology import (
    MCD12Q2_USER_GUIDE_URL,
    ORNL_SERVICE_DOCS_URL,
    PhenologyClient,
    PhenologyError,
    PhenologyRecord,
    load_demo_phenology,
    season_use,
)
from .economics import (
    ECONOMIC_DISCLAIMERS,
    compare_vs_rice_wheat_baseline,
    compute_rotation_economics,
)
from .satellite_context import (
    FIRMS_PUNJAB_CONTEXT,
    GRACE_PUNJAB_CONTEXT,
    calculate_water_budget_from_farm_inputs,
)
from .sensitivity import (
    evaluate_rank_stability,
    generate_plain_language_explanation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PAGES = (
    "Home / Overview",
    "Farm Profile",
    "Climate Insights",
    "Climate Trends",
    "Farmer Priorities",
    "Rotation Recommendations",
    "Hypothetical stress tests",
    "Future climate (NASA CMIP6)",
    "Comparison View",
    "Data and Methods",
)
METRIC_LABELS = {
    "water_suitability": "Water suitability",
    "climate_suitability": "Climate suitability",
    "soil_related_potential": "Soil-related potential",
    "rotation_diversity": "Rotation diversity",
    "economic_potential": "Economic potential",
}

# -- Colour palette --
BRAND_GREEN = "#2e7d32"
BRAND_LIGHT = "#e8f5e9"
ACCENT_AMBER = "#ff8f00"
ACCENT_RED = "#c62828"
ACCENT_BLUE = "#1565c0"
FAMILY_COLOURS = {
    "Poaceae": "#478c5b",
    "Fabaceae": "#8fbf6e",
    "Malvaceae": "#be8b4b",
    "Solanaceae": "#b9584b",
    "Brassicaceae": "#7f78ad",
}


# ─────────────────────────────── cached loaders ────────────────────────────

@st.cache_resource
def _power_client() -> PowerClient:
    return PowerClient()


@st.cache_resource
def _rotation_engine() -> RotationEngine:
    return RotationEngine(DATA_DIR / "crops.json", DATA_DIR / "rotation_rules.json")


@st.cache_resource
def _soilgrids_client() -> SoilGridsClient:
    return SoilGridsClient()


@st.cache_resource
def _phenology_client() -> PhenologyClient:
    return PhenologyClient()


@st.cache_resource
def _projection_extract() -> ProjectionExtract | None:
    try:
        return load_extract()
    except ProjectionDataError:
        return None


@st.cache_data
def _weight_profiles() -> dict[str, dict[str, float]]:
    raw = json.loads((DATA_DIR / "priority_weights.json").read_text(encoding="utf-8"))
    return {name: normalize_weights(values) for name, values in raw["profiles"].items()}


@st.cache_data
def _load_historical_fixture_dataset() -> PowerDataset:
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "power_daily_ludhiana_historical_2000_2024.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    req = PowerRequest(
        latitude=DEMO_LATITUDE,
        longitude=DEMO_LONGITUDE,
        start_date=date(2000, 1, 1),
        end_date=date(2024, 12, 31),
        parameters=tuple(raw["properties"]["parameter"].keys()),
    )
    return parse_power_daily_response(
        raw,
        req,
        source_url="https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CT2M_MAX%2CT2M_MIN%2CPRECTOTCORR%2CALLSKY_SFC_SW_DWN%2CRH2M%2CWS2M&community=AG&longitude=75.7&latitude=30.85&start=20000101&end=20241231&format=JSON&time-standard=UTC",
    )


# ─────────────────────────────── session state ─────────────────────────────

def _fresh_farm() -> dict[str, Any]:
    today = date.today()
    return {
        "latitude": None, "longitude": None,
        "start_date": today - timedelta(days=90), "end_date": today - timedelta(days=1),
        "texture": None, "ph": None, "organic_carbon_percent": None,
        "electrical_conductivity_ds_m": None, "waterlogged": None,
        "highly_deteriorated_alkaline": None, "well_drained": None,
        "soil_source": "", "soil_basis": "unspecified", "soil_sample_depth": "",
        "total_nitrogen_g_kg": None, "irrigation": "Unknown", "water_budget_mm": None,
        "field_size_ha": None, "previous_crop_id": None, "blocked_crop_ids": [],
        "start_season": "kharif",
    }


def _init_state() -> None:
    profiles = _weight_profiles()
    st.session_state.setdefault("farm", _fresh_farm())
    st.session_state.setdefault("weights", dict(profiles["balanced"]))
    st.session_state.setdefault("planning_horizon", 3)
    st.session_state.setdefault("scenario", "Historical NASA POWER context")
    st.session_state.setdefault("dry_reduction_pct", 25)
    st.session_state.setdefault("hot_increase_c", 2.0)
    st.session_state.setdefault("irrigation_reduction_pct", 0)
    st.session_state.setdefault("page", PAGES[0])
    st.session_state.setdefault("power_dataset", None)
    st.session_state.setdefault("power_error", None)
    st.session_state.setdefault("power_mode", None)
    st.session_state.setdefault("soilgrids_estimate", None)
    st.session_state.setdefault("soilgrids_error", None)
    st.session_state.setdefault("phenology_record", None)
    st.session_state.setdefault("phenology_error", None)


def _go(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()


def _reset() -> None:
    for key in list(st.session_state):
        if key.startswith(("farm_", "priority_", "block_")) or key in {
            "farm", "weights", "planning_horizon", "scenario",
            "power_dataset", "power_error", "power_mode",
            "soilgrids_estimate", "soilgrids_error",
            "phenology_record", "phenology_error",
            "dry_reduction_pct", "hot_increase_c", "irrigation_reduction_pct",
        }:
            del st.session_state[key]
    _init_state()
    st.success("The working farm profile and retrieved climate data were cleared.")


def _number(value: Any) -> float | None:
    return None if value in (None, "") else float(value)


def _tristate(label: str, key: str, value: bool | None, help_text: str) -> bool | None:
    choices = {"Unknown": None, "Yes": True, "No": False}
    initial = next(name for name, result in choices.items() if result is value)
    chosen = st.selectbox(label, tuple(choices), index=tuple(choices).index(initial), key=key, help=help_text)
    return choices[chosen]


def _farm_is_ready() -> bool:
    farm = st.session_state["farm"]
    return farm["latitude"] is not None and farm["longitude"] is not None


def _manual_soil_entry() -> ManualSoilEntry:
    farm = st.session_state["farm"]
    return ManualSoilEntry(
        source_type=farm.get("soil_basis", "unspecified"),
        texture=farm["texture"], ph=farm["ph"],
        organic_carbon_percent=farm["organic_carbon_percent"],
        total_nitrogen_g_kg=farm.get("total_nitrogen_g_kg"),
        electrical_conductivity_ds_m=farm["electrical_conductivity_ds_m"],
        sample_depth=farm.get("soil_sample_depth") or None,
        reference=farm["soil_source"] or None,
    )


def _resolved_soil() -> ResolvedSoil:
    """Farmer/lab values first, then appropriate SoilGrids estimates, else unknown."""
    return resolve_soil_values(_manual_soil_entry(), st.session_state.get("soilgrids_estimate"))


def soil_information_from(farm: dict[str, Any], resolved: ResolvedSoil) -> SoilInformation:
    """Build the engine's soil input from resolved values, keeping their sources."""
    texture, soc = resolved["texture"], resolved["organic_carbon"]
    soc_range = (soc.low, soc.high) if soc.low is not None and soc.high is not None else None
    return SoilInformation(
        ph=farm["ph"], electrical_conductivity_ds_m=farm["electrical_conductivity_ds_m"],
        organic_carbon_percent=soc.value, waterlogged=farm["waterlogged"],  # type: ignore[arg-type]
        highly_deteriorated_alkaline=farm["highly_deteriorated_alkaline"], well_drained=farm["well_drained"],
        texture=texture.value, source_description=farm["soil_source"] or None,  # type: ignore[arg-type]
        texture_source=texture.source_type if texture.value is not None else None,
        organic_carbon_source=soc.source_type if soc.value is not None else None,
        organic_carbon_depth=soc.depth if soc.value is not None else None,
        organic_carbon_range_percent=soc_range,
    )


def _profile_from_state() -> FarmProfile:
    farm = st.session_state["farm"]
    dataset: PowerDataset | None = st.session_state["power_dataset"]
    climate = ClimateContext(
        source_url=dataset.provenance.source_url if dataset else None,
        date_range=f"{dataset.provenance.start_date} to {dataset.provenance.end_date}" if dataset else None,
        available_parameters=tuple(dataset.data.columns) if dataset else (),
    )
    soil = soil_information_from(farm, _resolved_soil())
    return FarmProfile(
        latitude=farm["latitude"], longitude=farm["longitude"], soil=soil, climate=climate,
        total_crop_water_budget_mm=farm["water_budget_mm"], previous_crop_id=farm["previous_crop_id"],
        blocked_crop_ids=frozenset(farm["blocked_crop_ids"]), priority_weights=st.session_state["weights"],
        number_of_seasons=st.session_state["planning_horizon"], start_season=farm["start_season"],
        climate_scenario=st.session_state["scenario"],
        climate_data=dataset.data if dataset else None,
        observed_season_use=_observed_season_use(),
    )


def _observed_season_use() -> dict[str, Any] | None:
    """MODIS season use for the saved farm location, or None if absent or for another location."""
    record: PhenologyRecord | None = st.session_state.get("phenology_record")
    farm = st.session_state["farm"]
    if record is None or farm["latitude"] is None:
        return None
    if abs(record.latitude - farm["latitude"]) > 1e-4 or abs(record.longitude - farm["longitude"]) > 1e-4:
        return None
    return season_use(record)


def _plans() -> Any:
    """Generate rotation plans from the current farm profile."""
    if not _farm_is_ready():
        return None
    try:
        profile = _profile_from_state()
        return _rotation_engine().generate(profile)
    except RotationInputError as error:
        st.error(f"The planner needs a correction: {error}")
        return None


def _scenario_definitions() -> tuple[Any, ...]:
    return build_scenarios(
        dry_precipitation_reduction_pct=float(st.session_state["dry_reduction_pct"]),
        hot_temperature_increase_c=float(st.session_state["hot_increase_c"]),
        irrigation_reduction_pct=float(st.session_state["irrigation_reduction_pct"]),
    )


def _load_complete_demo_workflow(with_cached_climate: bool = True) -> None:
    """Load complete, verified demonstration workflow (Ludhiana profile + 2024 NASA snapshot)."""
    st.session_state["farm"] = {
        **_fresh_farm(),
        "latitude": DEMO_LATITUDE,
        "longitude": DEMO_LONGITUDE,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 12, 31),
        "texture": "medium",
        "ph": 7.4,
        "organic_carbon_percent": 0.55,
        "electrical_conductivity_ds_m": 0.35,
        "waterlogged": False,
        "highly_deteriorated_alkaline": False,
        "well_drained": True,
        "soil_source": "Illustrative demonstration input (Ludhiana, Punjab) — replace with farmer/laboratory evidence.",
        "soil_basis": "illustrative",
        "irrigation": "Irrigated",
        "water_budget_mm": 800.0,
        "field_size_ha": 2.5,
        "previous_crop_id": None,
        "blocked_crop_ids": [],
        "start_season": "kharif",
    }
    for key in list(st.session_state):
        if key.startswith(("farm_", "block_")):
            del st.session_state[key]
    st.session_state["soilgrids_estimate"] = None
    st.session_state["soilgrids_error"] = None
    st.session_state["phenology_record"] = load_demo_phenology()
    st.session_state["phenology_error"] = None
    if with_cached_climate:
        st.session_state["power_dataset"] = load_offline_demo_snapshot()
        st.session_state["power_mode"] = "offline_snapshot"
    else:
        st.session_state["power_dataset"] = None
        st.session_state["power_mode"] = None
    st.session_state["power_error"] = None
    st.session_state["planning_horizon"] = 3
    st.toast("Demonstration profile loaded (Ludhiana, Punjab). Not real farmer data.", icon="🌟")


def _load_ludhiana_example() -> None:
    """Load illustrative profile with offline NASA POWER snapshot."""
    _load_complete_demo_workflow(with_cached_climate=True)


# ────────────────────────────────── theme ──────────────────────────────────

def _theme() -> None:
    """Apply FieldShift's custom CSS for a polished agricultural look."""
    st.markdown("""
    <style>
    /* ── Global ── */
    .stApp {
        background: linear-gradient(180deg, #f0f7f0 0%, #ffffff 30%);
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%);
        color: white;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stRadio label span {
        color: white !important;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label[data-selected="true"] {
        background-color: rgba(255,255,255,0.18) !important;
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2);
    }

    /* ── Cards ── */
    div[data-testid="stExpander"] {
        background: white;
        border: 1px solid #c8e6c9;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }
    div.stContainer[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
    }

    /* ── Metrics ── */
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.8rem !important;
        color: #616161 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #2e7d32 !important;
    }

    /* ── Buttons ── */
    button[kind="primary"] {
        background: linear-gradient(135deg, #2e7d32, #43a047) !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(46,125,50,0.3) !important;
    }

    /* ── Headers ── */
    h1 {
        color: #1b5e20 !important;
        font-weight: 800 !important;
    }
    h2, h3 {
        color: #2e7d32 !important;
    }

    /* ── DataFrames ── */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }

    /* ── Info boxes ── */
    div[data-testid="stAlert"] {
        border-radius: 10px !important;
    }

    /* ── Footer ── */
    .fieldshift-footer {
        text-align: center;
        padding: 2rem 0 1rem;
        color: #9e9e9e;
        font-size: 0.8rem;
        border-top: 1px solid #e0e0e0;
        margin-top: 3rem;
    }
    </style>
    """, unsafe_allow_html=True)


# ────────────────────────────────── sidebar ─────────────────────────────────

def _sidebar() -> None:
    with st.sidebar:
        st.markdown("### 🌾 FieldShift")
        st.caption("A transparent crop-rotation planning prototype")
        st.divider()
        current = st.session_state["page"]
        page_icons = {
            "Home / Overview": "🏠",
            "Farm Profile": "🧑‍🌾",
            "Climate Insights": "🌤️",
            "Climate Trends": "📈",
            "Farmer Priorities": "⚖️",
            "Rotation Recommendations": "🔄",
            "Hypothetical stress tests": "🧪",
            "Future climate (NASA CMIP6)": "🌍",
            "Comparison View": "📊",
            "Data and Methods": "📖",
        }
        selected = st.radio(
            "Navigate",
            PAGES,
            index=PAGES.index(current),
            format_func=lambda p: f"{page_icons.get(p, '•')} {p}",
        )
        if selected != current:
            st.session_state["page"] = selected
            st.rerun()
        st.divider()
        if _farm_is_ready():
            farm = st.session_state["farm"]
            st.success(f"📍 Farm: {farm['latitude']:.4f}, {farm['longitude']:.4f}")
            if st.session_state.get("power_dataset"):
                mode = st.session_state.get("power_mode", "live")
                if mode == "offline_snapshot":
                    st.info("📦 Mode: Offline snapshot")
                else:
                    st.success("🌐 Mode: Live NASA API")
            else:
                st.caption("🌤️ Climate data: Not retrieved")
        else:
            st.info("No farm location saved yet.")
        if st.button("🔄 Reset farm profile", use_container_width=True):
            _reset()


# ─────────────────────────────── page renderers ────────────────────────────

def render_home() -> None:
    st.title("🌾 FieldShift")
    st.markdown("#### Plan resilient crop rotations with evidence and transparency")
    st.warning(
        "**Decision-support prototype** — not a guarantee of crop yield, income, "
        "pest control, or soil improvement. Confirm choices with local agronomic "
        "advice and soil or laboratory evidence.",
        icon="⚠️",
    )

    col1, col2 = st.columns((2, 1), gap="large")
    with col1:
        st.markdown(
            "FieldShift combines **farmer-provided information**, historical "
            "**NASA POWER climate context**, and a source-linked crop catalogue. "
            "It compares documented crop sequences; it does not predict yields "
            "or invent unknown soil values."
        )
        st.markdown("##### ✨ What you can do")
        st.markdown("""
- 🧑‍🌾 **Enter your farm profile** — location, soil, water budget
- 🌤️ **Retrieve real NASA POWER climate data** — no API key needed
- ⚖️ **Set your priorities** — water, soil, diversity
- 🔄 **Generate rotation alternatives** — source-linked, transparent
- 🧪 **Stress-test under scenarios** — dry, hot, reduced water
- 📊 **Compare plans** — Pareto analysis, trade-offs visible
- 🌱 **Soil-state estimates** — simplified N-balance and SOC direction
        """)
        if st.button("🚀 Start planning", type="primary", use_container_width=True):
            _go("Farm Profile")

    with col2:
        with st.container(border=True):
            st.markdown("##### 🌟 Live Judging Quick-Start")
            st.write("**Ludhiana demonstration preset**")
            st.caption("Pre-configured illustrative farm with a saved, unmodified 2024 NASA POWER response.")
            if st.button("🚀 Load demo & view plans", type="primary", use_container_width=True):
                _load_complete_demo_workflow(with_cached_climate=True)
                _go("Rotation Recommendations")
            if st.button("▶️ Load demo farm profile", use_container_width=True):
                _load_complete_demo_workflow(with_cached_climate=True)
                _go("Farm Profile")

    st.divider()
    st.markdown("#### 📡 Data readiness")
    cols = st.columns(3)
    for i, status in enumerate(source_statuses()):
        with cols[i]:
            with st.container(border=True):
                icon = "✅" if status.available else "⏳"
                st.markdown(f"**{icon} {status.name}**")
                st.caption(status.message)
    st.caption(
        "Also used: NASA MODIS land-cover dynamics (observed cropping seasons), NASA NEX-GDDP-CMIP6 climate projections "
        "(demo farm grid cell) and optional ISRIC SoilGrids estimates. GPM IMERG and SMAP are not integrated (see docs/DATA_SOURCES.md)."
    )

    with st.expander("🛰️ Regional Earth Observation Context: NASA GRACE & NASA FIRMS (Punjab Agronomic Crisis)", expanded=False):
        g_col, f_col = st.columns(2)
        with g_col:
            st.markdown(f"#### 🌊 NASA GRACE Groundwater Depletion")
            st.markdown(f"""
- **Satellite:** {GRACE_PUNJAB_CONTEXT['satellite']} ({GRACE_PUNJAB_CONTEXT['resolution']})
- **Finding:** {GRACE_PUNJAB_CONTEXT['finding']}
- **Root Cause:** {GRACE_PUNJAB_CONTEXT['primary_driver']}
- **Why FieldShift Helps:** {GRACE_PUNJAB_CONTEXT['relevance_to_fieldshift']}
- **Source:** [{GRACE_PUNJAB_CONTEXT['source_citation']}]({GRACE_PUNJAB_CONTEXT['source_url']})
            """)
        with f_col:
            st.markdown(f"#### 🔥 NASA FIRMS Stubble Fire Detection")
            st.markdown(f"""
- **Sensors:** {FIRMS_PUNJAB_CONTEXT['sensors']}
- **Peak Fire Window:** {FIRMS_PUNJAB_CONTEXT['stubble_burning_season']}
- **Agronomic Driver:** {FIRMS_PUNJAB_CONTEXT['agricultural_driver']}
- **Why FieldShift Helps:** {FIRMS_PUNJAB_CONTEXT['relevance_to_fieldshift']}
- **Source:** [{FIRMS_PUNJAB_CONTEXT['source_citation']}]({FIRMS_PUNJAB_CONTEXT['source_url']})
            """)

    _footer()


def render_farm_profile() -> None:
    st.title("🧑‍🌾 Farm profile")
    st.caption("Enter what you know. Leave a value unknown if it has not been measured; the planner will explain the effect.")

    col_demo_a, col_demo_b = st.columns(2)
    with col_demo_a:
        if st.button("🌟 Load complete demo farm & cached climate data", type="primary", use_container_width=True):
            _load_complete_demo_workflow(with_cached_climate=True)
            st.rerun()
    with col_demo_b:
        if st.button("▶️ Load demo farm inputs only", use_container_width=True):
            _load_complete_demo_workflow(with_cached_climate=False)
            st.rerun()
    st.caption("The demonstration profile is an illustrative benchmark (Ludhiana, Punjab) — replace every value with farm or laboratory evidence before real-world use.")

    farm = st.session_state["farm"]
    crops = _rotation_engine().crops
    labels = {crop_id: crop["name"] for crop_id, crop in crops.items()}

    with st.expander("🧮 Water Budget Helper: Estimate from Tubewell & Canal Turns (for farmers)", expanded=False):
        st.markdown(
            "Converts local irrigation practices (tubewell motor HP, weekly pumping hours, canal water turns) "
            "into an equivalent seasonal crop-water budget in mm."
        )
        wb_c1, wb_c2, wb_c3 = st.columns(3)
        with wb_c1:
            tw_hp = st.number_input("Tubewell motor power (HP)", min_value=1.0, max_value=50.0, value=10.0, step=1.0, key="calc_tw_hp")
            tw_hours = st.number_input("Pumping hours per week", min_value=0.0, max_value=168.0, value=25.0, step=5.0, key="calc_tw_hours")
        with wb_c2:
            tw_weeks = st.number_input("Operating weeks per season", min_value=1.0, max_value=26.0, value=16.0, step=1.0, key="calc_tw_weeks")
            canal_turns = st.number_input("Canal water turns (warrabandi)", min_value=0, max_value=20, value=4, step=1, key="calc_canal_turns")
        with wb_c3:
            canal_depth = st.number_input("Depth per canal turn (inches)", min_value=0.0, max_value=12.0, value=3.0, step=0.5, key="calc_canal_depth")
            farm_acres = st.number_input("Farm size for water calculation (acres)", min_value=0.5, max_value=500.0, value=5.0, step=0.5, key="calc_farm_acres")

        if st.button("Apply estimated water budget (mm)", key="btn_apply_water_calc"):
            est_budget = calculate_water_budget_from_farm_inputs(
                tubewell_hp=tw_hp,
                hours_per_week=tw_hours,
                weeks_operating=tw_weeks,
                canal_turns_per_season=canal_turns,
                canal_depth_inches=canal_depth,
                farm_size_acres=farm_acres,
            )
            st.session_state["farm"]["water_budget_mm"] = est_budget["total_water_budget_mm"]
            st.success(
                f"Calculated: **{est_budget['total_water_budget_mm']:.0f} mm** "
                f"(Tubewell: {est_budget['tubewell_contribution_mm']:.0f} mm, Canal: {est_budget['canal_contribution_mm']:.0f} mm). "
                f"Updated in form below — click 'Save farm profile' to record."
            )
            st.rerun()

    with st.form("farm_profile"):
        st.subheader("📍 Location and climate request")
        a, b = st.columns(2)
        with a:
            latitude = st.text_input("Latitude (degrees)", value="" if farm["latitude"] is None else str(farm["latitude"]), key="farm_latitude", placeholder="Example: 30.85")
        with b:
            longitude = st.text_input("Longitude (degrees)", value="" if farm["longitude"] is None else str(farm["longitude"]), key="farm_longitude", placeholder="Example: 75.70")
        c, d = st.columns(2)
        with c:
            start_date = st.date_input("Historical start date", value=farm["start_date"], min_value=date(1981, 1, 1), key="farm_start")
        with d:
            end_date = st.date_input("Historical end date", value=farm["end_date"], min_value=date(1981, 1, 1), key="farm_end")

        st.subheader("🧪 Soil test or farmer-entered soil values")
        st.caption(
            "Values typed here always take precedence over SoilGrids estimates. Leave a field empty if it has not been measured. "
            "These fields are not remotely measured by NASA POWER."
        )
        basis_keys = list(MANUAL_SOURCE_TYPES)
        b1, b2 = st.columns(2)
        with b1:
            basis = st.selectbox(
                "What are these soil values based on?", basis_keys,
                index=basis_keys.index(farm.get("soil_basis", "unspecified")),
                format_func=lambda key: SOURCE_LABELS[key], key="farm_soil_basis",
                help="Keeps laboratory results identifiable as a separate source from observations, illustrations and estimates.",
            )
        with b2:
            sample_depth = st.text_input("Sampling depth of the soil test (optional)", value=farm.get("soil_sample_depth", ""), key="farm_soil_depth", placeholder="Example: 0–15 cm")
        e, f, g = st.columns(3)
        with e:
            texture = st.selectbox("Texture", ("Unknown", "light", "medium", "heavy"), index=("Unknown", "light", "medium", "heavy").index(farm["texture"] or "Unknown"), key="farm_texture")
            ph = st.text_input("pH (unitless, optional)", value="" if farm["ph"] is None else str(farm["ph"]), key="farm_ph")
        with f:
            organic = st.text_input("Organic carbon (%; optional)", value="" if farm["organic_carbon_percent"] is None else str(farm["organic_carbon_percent"]), key="farm_organic")
            ec = st.text_input("Electrical conductivity (dS/m; optional)", value="" if farm["electrical_conductivity_ds_m"] is None else str(farm["electrical_conductivity_ds_m"]), key="farm_ec")
            nitrogen = st.text_input(
                "Total nitrogen (g/kg; optional)", value="" if farm.get("total_nitrogen_g_kg") is None else str(farm["total_nitrogen_g_kg"]), key="farm_nitrogen",
                help="Total N only. Soil Health Card 'available N' (kg/ha) is a different measurement; do not enter it here.",
            )
        with g:
            waterlogged = _tristate("Waterlogged?", "farm_waterlogged", farm["waterlogged"], "Known waterlogging can be a documented hard constraint for wheat.")
            alkaline = _tristate("Highly deteriorated alkaline?", "farm_alkaline", farm["highly_deteriorated_alkaline"], "Leave unknown unless this condition is known.")
            drained = _tristate("Well drained?", "farm_drained", farm["well_drained"], "Used only against documented rapeseed/mustard context.")
        soil_source = st.text_input("Soil source or laboratory report reference (optional)", value=farm["soil_source"], key="farm_soil_source")

        st.subheader("💧 Water and rotation context")
        h, i, j = st.columns(3)
        with h:
            irrigation = st.selectbox("Irrigation availability", ("Unknown", "Rainfed", "Limited irrigation", "Irrigated"), index=("Unknown", "Rainfed", "Limited irrigation", "Irrigated").index(farm["irrigation"]), key="farm_irrigation")
            budget = st.text_input("Total crop-water budget (mm; optional)", value="" if farm["water_budget_mm"] is None else str(farm["water_budget_mm"]), key="farm_budget", help="A farmer-provided seasonal water budget. This is not derived from rainfall.")
        with i:
            field_size = st.text_input("Field size (ha; optional)", value="" if farm["field_size_ha"] is None else str(farm["field_size_ha"]), key="farm_size")
            previous = st.selectbox("Previous crop (if known)", ("Unknown", *[labels[x] for x in sorted(labels)]), index=0 if not farm["previous_crop_id"] else 1 + sorted(labels).index(farm["previous_crop_id"]), key="farm_previous")
        with j:
            _season_options = {"Kharif": "kharif", "Rabi": "rabi", "Summer (zaid)": "summer"}
            _season_reverse = {v: k for k, v in _season_options.items()}
            _season_display = _season_reverse.get(farm["start_season"], "Kharif")
            _season_label = st.selectbox("First planning season", tuple(_season_options.keys()), index=list(_season_options.keys()).index(_season_display), key="farm_season")
            season = _season_options[_season_label]
            blocked_names = st.multiselect("Avoid crops (farmer/pest reason)", options=[labels[x] for x in sorted(labels)], default=[labels[x] for x in farm["blocked_crop_ids"]], key="block_crops")
        submitted = st.form_submit_button("💾 Save farm profile", type="primary")

    if submitted:
        try:
            lat, lon = float(latitude), float(longitude)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError("Latitude must be −90 to 90 and longitude must be −180 to 180.")
            if start_date > end_date:
                raise ValueError("The historical start date must be on or before the end date.")
            values = [_number(item) for item in (ph, organic, ec, budget, field_size, nitrogen)]
            if any(value is not None and value < 0 for value in values):
                raise ValueError("Soil values, water budget, and field size cannot be negative.")
            reverse = {name: crop_id for crop_id, name in labels.items()}
            if (farm["latitude"], farm["longitude"]) != (lat, lon):
                # An estimate belongs to the coordinates it was retrieved for.
                st.session_state["soilgrids_estimate"] = None
                st.session_state["soilgrids_error"] = None
                st.session_state["phenology_record"] = None
                st.session_state["phenology_error"] = None
            farm.update({
                "latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date,
                "texture": None if texture == "Unknown" else texture, "ph": values[0],
                "organic_carbon_percent": values[1], "electrical_conductivity_ds_m": values[2],
                "waterlogged": waterlogged, "highly_deteriorated_alkaline": alkaline,
                "well_drained": drained, "soil_source": soil_source.strip(),
                "soil_basis": basis, "soil_sample_depth": sample_depth.strip(),
                "total_nitrogen_g_kg": values[5],
                "irrigation": irrigation, "water_budget_mm": values[3],
                "field_size_ha": values[4],
                "previous_crop_id": None if previous == "Unknown" else reverse[previous],
                "blocked_crop_ids": [reverse[name] for name in blocked_names],
                "start_season": season,
            })
            st.session_state["power_dataset"] = None
            st.session_state["power_error"] = None
            st.success("✅ Farm profile saved. Retrieve the real historical climate series next.")
        except ValueError as error:
            st.error(f"Please correct the farm profile: {error}")

    _render_soil_estimate_section()
    _render_land_use_section()

    if _farm_is_ready() and st.button("➡️ Continue to climate insights", type="primary"):
        _go("Climate Insights")
    _footer()


def _request_phenology() -> None:
    farm = st.session_state["farm"]
    end_year = date.today().year - 1  # MCD12Q2 is released about six months after the year ends
    bar = st.progress(0.0, text="Requesting MODIS phenology from ORNL DAAC (13 small requests)…")
    try:
        record = _phenology_client().fetch(
            farm["latitude"], farm["longitude"], end_year - 9, end_year,
            progress=lambda done, total: bar.progress(done / total, text=f"MODIS phenology: {done}/{total} layers"),
        )
        st.session_state["phenology_record"] = record
        st.session_state["phenology_error"] = None
    except PhenologyError as error:
        st.session_state["phenology_error"] = str(error)
    finally:
        bar.empty()


_LAND_USE_ICONS = {"regularly_green": "🟢", "not_green": "⚪", "irregular": "🟡", "insufficient": "❔"}
_LAND_USE_WORDS = {
    "regularly_green": "Usually green (cropped) in recent years",
    "not_green": "Not green in recent years (usually fallow)",
    "irregular": "Green only in some years",
    "insufficient": "Not enough clear years",
}


def _render_land_use_section() -> None:
    """Observed seasonal land use from MODIS MCD12Q2 for the saved farm location."""
    st.subheader("🛰️ Recent land use at this location (NASA MODIS)")
    st.caption(
        "MODIS Land Cover Dynamics (MCD12Q2) records when the land at this 500 m pixel turned green and went dormant each year. "
        "FieldShift uses it to show whether a plan keeps or adds a cropping season compared with recent years. "
        "It does not identify crops, yields or soil quality."
    )
    if not _farm_is_ready():
        st.info("Save a farm location first.")
        return
    if st.button("🛰️ Retrieve recent cropping seasons (MODIS, last 10 years)", use_container_width=True):
        _request_phenology()
    if st.session_state.get("phenology_error"):
        st.warning(
            f"MODIS phenology unavailable: {st.session_state['phenology_error']}\n\n"
            "You can continue planning; plans are then not compared with recent land use."
        )
    use = _observed_season_use()
    record: PhenologyRecord | None = st.session_state.get("phenology_record")
    if use is None or record is None:
        if record is not None:
            st.info("The MODIS record loaded belongs to a different location. Retrieve it again for this farm.")
        return
    mode = "saved ORNL DAAC response" if record.mode == "saved" else "live ORNL DAAC request"
    st.markdown(f"**Source:** {record.product} · {mode} retrieved {record.retrieved_at_utc} · product years {record.years[0]}–{record.years[-1]}")
    cols = st.columns(len(use))
    for col, (season_id, item) in zip(cols, use.items()):
        with col:
            with st.container(border=True):
                st.markdown(f"**{_LAND_USE_ICONS[item.summary]} {item.season_name}**")
                st.write(_LAND_USE_WORDS[item.summary])
                st.caption(item.sentence())
    _land_use_timeline(record)
    with st.expander("📋 Year-by-year detail, method and limitations"):
        st.dataframe(
            pd.DataFrame([
                {"Season": item.season_name, "Year": year.label, "Result": year.status.replace("_", " "), "Detail": year.detail}
                for item in use.values() for year in item.years
            ]),
            hide_index=True, use_container_width=True,
        )
        st.markdown(
            "- Each detected cycle is placed in the season window (kharif 1 Jun–31 Oct, rabi 1 Nov–30 Apr, summer 1 Apr–15 Jun) "
            "that contains the midpoint of its mid-greenup and mid-greendown dates.\n"
            "- A season is **usually green** if a cycle was found in more than half of the clear years, and **not green** if none was found. "
            "At least 3 clear years are needed. These are FieldShift screening rules, not agronomic thresholds.\n"
            "- Years are **unclear** when the cycle count is missing, the cycle quality is poor (QA 3), or more than two cycles exist "
            "(the product reports only the two largest).\n"
            "- A 500 m pixel can mix several fields with different calendars, so two cycles do not prove two crops on one field.\n"
            f"- [MCD12Q2 C6.1 user guide]({MCD12Q2_USER_GUIDE_URL}) · [ORNL DAAC subset service]({ORNL_SERVICE_DOCS_URL})"
        )


def _land_use_timeline(record: PhenologyRecord) -> None:
    """Green-up to dormancy bars per detected cycle (dates normalised to one season year)."""
    rows = []
    for cycle in record.cycles:
        if cycle.greenup is None or cycle.dormancy is None:
            continue
        rows.append({
            "Product year": str(cycle.product_year),
            "Start": pd.Timestamp(cycle.greenup),
            "End": pd.Timestamp(cycle.dormancy),
            "Quality": cycle.quality,
        })
    if not rows:
        return
    fig = px.timeline(pd.DataFrame(rows), x_start="Start", x_end="End", y="Product year", color="Quality",
                      color_discrete_map={"best": BRAND_GREEN, "good": "#66bb6a", "fair": ACCENT_AMBER, "poor": ACCENT_RED},
                      title="Detected vegetation cycles (green-up to dormancy) at this 500 m pixel")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(template="plotly_white", height=320, legend_title_text="MODIS QA", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Gaps between bars are periods with no detected vegetation cycle, such as fallow land or bare soil.")


def _request_soil_estimate() -> None:
    farm = st.session_state["farm"]
    try:
        with st.spinner("Requesting SoilGrids estimates… (the beta service can take ~30 s; timeout 60 s)"):
            st.session_state["soilgrids_estimate"] = _soilgrids_client().fetch(farm["latitude"], farm["longitude"])
        st.session_state["soilgrids_error"] = None
    except SoilGridsError as error:
        st.session_state["soilgrids_estimate"] = None
        st.session_state["soilgrids_error"] = str(error)


def _format_soil_value(value: Any, unit: str) -> str:
    if value is None:
        return "Unknown"
    if isinstance(value, str):
        return value
    if unit == "pH units":
        return f"{value:.1f}"
    return f"{value:.2f} {unit}"


def _render_soil_estimate_section() -> None:
    """Optional SoilGrids estimate plus the table of soil values the planner uses."""
    st.subheader("🛰️ Optional: estimate soil properties from location")
    st.caption(
        "ISRIC SoilGrids predicts soil properties on a 250 m global grid from soil profiles and environmental data. "
        "It is an estimate for the grid cell, not a soil test of your field. Your own entries above always override it."
    )
    if not _farm_is_ready():
        st.info("Save a farm location first to request a SoilGrids estimate.")
        return
    if st.button("🛰️ Estimate soil properties from location", use_container_width=True):
        _request_soil_estimate()

    error = st.session_state.get("soilgrids_error")
    estimate: SoilGridsEstimate | None = st.session_state.get("soilgrids_estimate")
    if error:
        st.warning(
            f"SoilGrids estimate unavailable: {error}\n\n"
            "You can continue planning. Soil properties stay unknown unless you enter them, and the planner explains what that affects.",
            icon="⚠️",
        )
    if estimate is not None and not estimate.has_any_value:
        st.info(
            "SoilGrids returned no prediction for this exact location (every requested value was empty). "
            "The service does not state why; the point may fall outside its soil mask. Soil properties remain unknown unless you enter them."
        )
    if estimate is not None and estimate.has_any_value:
        st.markdown(f"##### 🏷️ {ESTIMATE_LABEL} — not a measured soil test")
        rows = []
        for name in SOILGRIDS_PROPERTIES:
            for depth in SOILGRIDS_DEPTHS:
                item = estimate.value(name, depth)
                if item is None:
                    continue
                interval = f"{item.q05:.2f} – {item.q95:.2f}" if item.q05 is not None and item.q95 is not None else "Not provided"
                rows.append({
                    "Property": item.label,
                    "Depth": f"{item.top_cm}–{item.bottom_cm} cm",
                    "Mean estimate": "No value" if item.mean is None else f"{item.mean:.2f}",
                    "90% prediction range (Q0.05–Q0.95)": interval,
                    "Uncertainty ratio": "Not provided" if item.uncertainty_ratio is None else f"{item.uncertainty_ratio:.1f}",
                    "Unit": item.unit,
                })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.warning(
            "**Spatial resolution:** each value describes a 250 m grid cell (about 6 ha) predicted by a global model. "
            "Fields inside one cell can differ a lot, especially after years of different management. "
            "The wide prediction ranges above show how uncertain the estimate is. Use a laboratory soil test for farm decisions.",
            icon="📏",
        )
        with st.expander("📋 SoilGrids provenance"):
            st.write({
                "label": estimate.label,
                "source_url": estimate.source_url,
                "retrieved_at_utc": estimate.retrieved_at_utc,
                "coordinates_requested": f"{estimate.latitude:.5f}, {estimate.longitude:.5f}",
                "coordinates_returned": None if estimate.returned_latitude is None else f"{estimate.returned_latitude:.5f}, {estimate.returned_longitude:.5f}",
                "resolution": estimate.resolution,
                "uncertainty": "Q0.05/Q0.5/Q0.95 quantiles and ISRIC uncertainty ratio (Q0.95 − Q0.05)/Q0.5",
                "licence": estimate.licence,
                "documentation": estimate.documentation_url,
                "access_notes": f"REST API is a beta service and may be paused. {SOILGRIDS_FAIR_USE} Alternatives: {SOILGRIDS_ACCESS_URL}",
            })

    resolved = _resolved_soil()
    st.markdown("##### ✅ Soil values the planner actually uses")
    st.dataframe(
        pd.DataFrame([
            {
                "Property": item.label,
                "Value used": _format_soil_value(item.value, item.unit),
                "Range": "—" if item.low is None or item.high is None else f"{item.low:.2f} – {item.high:.2f}",
                "Source": item.source_label,
                "Depth": item.depth or "—",
                "Used in calculations?": "Yes" if item.used_in_model and item.value is not None else "No",
                "How it is used": item.how_used,
                "Not used (shown for comparison)": item.not_used_alternative or "—",
            }
            for item in resolved.values.values()
        ]),
        hide_index=True, use_container_width=True,
    )
    for note in resolved.notes:
        st.caption(f"ℹ️ {note}")
    st.caption(
        "🧪 **Replacing an estimate with a laboratory result:** type the laboratory value into the soil form above, "
        "choose “Laboratory soil test (farmer-entered)”, add the sampling depth and report reference, then save. "
        "The laboratory value is used immediately; the SoilGrids estimate stays visible only for comparison."
    )


def _request_climate(force_refresh: bool = False) -> None:
    farm = st.session_state["farm"]
    try:
        request = PowerRequest(farm["latitude"], farm["longitude"], farm["start_date"], farm["end_date"])
        with st.spinner("Retrieving historical daily data from NASA POWER… (timeout: 15 s)"):
            st.session_state["power_dataset"] = _power_client().fetch_daily(request, force_refresh=force_refresh)
        st.session_state["power_mode"] = "live"
        st.session_state["power_error"] = None
    except PowerError as error:
        st.session_state["power_dataset"] = None
        st.session_state["power_mode"] = None
        st.session_state["power_error"] = str(error)


def _climate_provenance(dataset: PowerDataset) -> None:
    p = dataset.provenance
    mode = st.session_state.get("power_mode", "live")
    if mode == "offline_snapshot":
        st.info(
            f"📦 **Mode: Saved Offline Snapshot (Ludhiana Demonstration Region)**\n\n"
            f"Unmodified NASA POWER Daily API response saved on {p.retrieved_at_utc[:10]} · Location: **{p.latitude_requested:.4f}°N, {p.longitude_requested:.4f}°E** "
            "(cropland pixel in rural Ludhiana district) · "
            f"Date range: **{p.start_date} to {p.end_date}** ({len(dataset.data)} daily observations)."
        )
    else:
        st.success(
            f"🌐 **Mode: Live NASA POWER API Data**\n\n"
            f"Retrieved at **{p.retrieved_at_utc} UTC** · Location: **{p.latitude_requested:.4f}°N, {p.longitude_requested:.4f}°E** · "
            f"Date range: **{p.start_date} to {p.end_date}** ({len(dataset.data)} daily observations)."
        )
    st.caption("Retrieved values are gridded NASA POWER context, not direct field or soil measurements, and not a future forecast.")
    col_mode_a, col_mode_b = st.columns([2, 1])
    with col_mode_a:
        st.markdown(f"[Exact API request URL]({p.source_url}) · [NASA POWER daily API documentation]({p.documentation_url})")
    with col_mode_b:
        if mode == "offline_snapshot":
            if st.button("🌐 Switch to Live NASA API", use_container_width=True):
                _request_climate(force_refresh=True)
                st.rerun()
        else:
            if st.button("📦 Switch to Offline Snapshot", use_container_width=True):
                st.session_state["power_dataset"] = load_offline_demo_snapshot()
                st.session_state["power_mode"] = "offline_snapshot"
                st.session_state["power_error"] = None
                st.rerun()
    with st.expander("📋 Detailed Provenance & Quality Metadata"):
        st.write({
            "mode": mode,
            "retrieved_at_utc": p.retrieved_at_utc,
            "parameters": {name: meta.unit for name, meta in p.parameter_metadata.items()},
            "missing_observation_counts": dict(p.missing_observation_counts),
            "source_datasets": p.source_datasets,
            "spatial_applicability": p.spatial_applicability,
        })


def render_climate() -> None:
    st.title("🌤️ Climate insights")
    if not _farm_is_ready():
        st.info("Save a farm location and historical date range before making a NASA POWER request.")
        if st.button("Set up farm profile"):
            _go("Farm Profile")
        return
    farm = st.session_state["farm"]
    st.caption(f"Request: {farm['latitude']:.4f}, {farm['longitude']:.4f}; {farm['start_date']} to {farm['end_date']}. No NASA API key is used.")
    left, right = st.columns(2)
    with left:
        if st.button("☁️ Retrieve NASA POWER data", type="primary", use_container_width=True):
            _request_climate()
    with right:
        if st.button("🔄 Retry / refresh request", use_container_width=True):
            _request_climate(force_refresh=True)
    if st.session_state["power_error"]:
        st.error(f"⚠️ NASA POWER live request failed: {st.session_state['power_error']}")
        st.warning("NASA POWER is currently unreachable or slow. You can load the saved 2024 NASA POWER response for the demonstration farm to continue.")
        if st.button("📦 Load Saved Offline Snapshot for Ludhiana", type="primary", use_container_width=True):
            st.session_state["power_dataset"] = load_offline_demo_snapshot()
            st.session_state["power_mode"] = "offline_snapshot"
            st.session_state["power_error"] = None
            st.rerun()
    dataset: PowerDataset | None = st.session_state["power_dataset"]
    if not dataset:
        st.info("No climate dataset is currently active. Retrieve live data above or load the saved offline snapshot.")
        if st.button("📦 Load saved NASA POWER response (2024, demo farm)"):
            st.session_state["power_dataset"] = load_offline_demo_snapshot()
            st.session_state["power_mode"] = "offline_snapshot"
            st.session_state["power_error"] = None
            st.rerun()
        _footer()
        return
    _climate_provenance(dataset)
    frame = dataset.data
    try:
        precipitation = seasonal_precipitation_total(frame)
        st.metric("Calculated precipitation total", f"{precipitation.value:.1f} {precipitation.unit}", help=precipitation.definition)
        if precipitation.warning:
            st.warning(precipitation.warning)
        temp = temperature_summary(frame)
        a, b = st.columns(2)
        with a:
            fig_temp = px.line(
                frame.reset_index(), x="date", y="T2M",
                title="Daily mean 2 m temperature",
                labels={"T2M": "°C", "date": "Date"},
            )
            fig_temp.update_layout(template="plotly_white")
            st.plotly_chart(fig_temp, use_container_width=True)
        with b:
            fig_precip = px.bar(
                frame.reset_index(), x="date", y="PRECTOTCORR",
                title="Daily corrected precipitation",
                labels={"PRECTOTCORR": "mm/day", "date": "Date"},
                color_discrete_sequence=[BRAND_GREEN],
            )
            fig_precip.update_layout(template="plotly_white")
            st.plotly_chart(fig_precip, use_container_width=True)
        st.subheader("Monthly temperature summary")
        st.dataframe(temp.style.format("{:.2f}"), use_container_width=True)
    except FeatureValidationError as error:
        st.warning(f"A climate indicator could not be calculated: {error}")
    col_tr1, col_tr2 = st.columns([2, 1])
    with col_tr1:
        st.info("Long-term historical anomalies, decadal trends, and statistical significance across growing seasons (Kharif, Rabi, Summer) are analyzed in Climate Trends.")
    with col_tr2:
        if st.button("📈 Explore Climate Trends", use_container_width=True):
            _go("Climate Trends")
    with st.expander("📋 Retrieved daily values and missing observations"):
        st.dataframe(frame, use_container_width=True)
    if st.button("➡️ Continue to priorities", type="primary"):
        _go("Farmer Priorities")
    _footer()


def render_climate_trends() -> None:
    st.title("📈 Historical climate trends")
    st.caption(
        "Empirical long-term growing-season climate trends derived from NASA POWER daily observations. "
        "Calculates rates of change per decade, statistical significance, and shifts against historical baselines."
    )

    # 1. Dataset Selection
    session_dataset: PowerDataset | None = st.session_state.get("power_dataset")
    session_span_years = 0
    if session_dataset and not session_dataset.data.empty:
        session_span_years = (session_dataset.data.index.max().year - session_dataset.data.index.min().year) + 1

    use_fixture = True
    if session_dataset and session_span_years >= 3:
        source_choice = st.radio(
            "Select climate record for trend analysis",
            [
                f"Current farm profile dataset ({session_dataset.provenance.start_date} to {session_dataset.provenance.end_date}, {session_span_years} years)",
                "25-year NASA POWER record for the demo farm grid cell (2000–2024, 9,132 days; unmodified API response saved 2026-10-13)",
            ],
            index=0,
            help="At least 3 complete annual seasons are required to estimate a linear trend.",
        )
        use_fixture = "25-year" in source_choice
    else:
        if session_dataset:
            st.info(
                f"The current session climate request covers {session_dataset.provenance.start_date} to {session_dataset.provenance.end_date} "
                f"({session_span_years} year{'s' if session_span_years > 1 else ''}). Long-term trend analysis requires multi-year seasonal records (minimum 3 years). "
                "Displaying the 25-year NASA POWER record for the demo farm grid cell (2000–2024, 9,132 days; unmodified API response saved 2026-10-13)."
            )
        else:
            st.info(
                "No custom multi-year farm climate record is loaded. "
                "Displaying the 25-year NASA POWER record for the demo farm grid cell (2000–2024, 9,132 days; unmodified API response saved 2026-10-13)."
            )

    active_dataset = _load_historical_fixture_dataset() if use_fixture else session_dataset
    if not active_dataset or active_dataset.data.empty:
        st.error("No climate observations available for trend analysis.")
        _footer()
        return

    frame = active_dataset.data
    provenance = active_dataset.provenance

    # 2. Season Definition
    st.subheader("1. Growing-season definition")
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        season_keys = list(REGIONAL_SEASONS.keys())
        selected_season_key = st.selectbox(
            "Crop season",
            season_keys,
            index=0,
            format_func=lambda k: REGIONAL_SEASONS[k].name,
            help="Select the regional growing season to aggregate annual historical metrics.",
        )
        season_def = REGIONAL_SEASONS[selected_season_key]
    with col_s2:
        st.markdown(f"**Season window:** {season_def.description}")
        if season_def.is_cross_year:
            st.caption("ℹ️ Rabi is a cross-calendar-year season spanning Nov 1 of year Y to Apr 30 of year Y+1. Seasons missing terminal months are excluded from trend calculations to prevent sampling bias.")

    with st.expander("⚙️ Inspect / customize season date thresholds"):
        st.write({
            "season_id": season_def.id,
            "name": season_def.name,
            "start_date_window": f"{season_def.start_month:02d}-{season_def.start_day:02d}",
            "end_date_window": f"{season_def.end_month:02d}-{season_def.end_day:02d}",
            "cross_calendar_year": season_def.is_cross_year,
            "source": "Punjab Agricultural University (PAU) Package of Practices & Agro-ecological calendar",
        })

    # 3. Variable Coverage Audit
    st.subheader("2. NASA POWER variable coverage & completeness audit")
    coverage_dict = audit_variable_coverage(frame)
    if coverage_dict:
        audit_rows = []
        for param, cov in coverage_dict.items():
            audit_rows.append({
                "Parameter": param,
                "Description": cov.display_name,
                "Unit": cov.unit,
                "Coverage": f"{cov.first_date} to {cov.last_date}",
                "Valid Days": cov.valid_observations,
                "Missing Days": cov.missing_observations,
                "Completeness": f"{cov.completeness_percent:.1f}%",
                "Trend Suitability": "Sufficient (≥80%)" if cov.is_sufficient_for_trends else "Insufficient (<80%)",
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)

    # 4. Annual Summaries & Trend Computation
    summaries = compute_annual_season_summaries(frame, season=season_def)
    valid_summaries = [s for s in summaries if s.is_valid]
    incomplete_count = len(summaries) - len(valid_summaries)

    if incomplete_count > 0:
        st.caption(f"⚠️ {incomplete_count} season(s) had <75% valid daily observations (e.g. boundary years or incomplete records) and were excluded from the trend calculation.")

    if len(valid_summaries) < 3:
        st.warning("Fewer than 3 complete annual seasons found for the selected season window. A statistical linear trend cannot be calculated.")
        _footer()
        return

    years = [s.year for s in valid_summaries]

    # Variable selection for trend plot
    st.subheader("3. Historical trend estimation & baseline comparison")
    var_options = {
        "mean_temp": ("Mean Temperature", "°C", [s.mean_temp_c for s in valid_summaries]),
        "max_temp": ("Average Maximum Temperature", "°C", [s.mean_tmax_c for s in valid_summaries]),
        "min_temp": ("Average Minimum Temperature", "°C", [s.mean_tmin_c for s in valid_summaries]),
        "precipitation": ("Seasonal Precipitation Total", "mm", [s.total_precip_mm for s in valid_summaries]),
        "dry_spell": ("Longest Consecutive Dry Spell (≤1 mm/day)", "days", [float(s.dry_spell_max_days) if s.dry_spell_max_days is not None else None for s in valid_summaries]),
    }

    selected_var_key = st.selectbox(
        "Select climate indicator",
        list(var_options.keys()),
        format_func=lambda k: f"{var_options[k][0]} ({var_options[k][1]})",
    )
    v_name, v_unit, v_series = var_options[selected_var_key]

    trend = calculate_linear_trend(
        years=years,
        values=v_series,
        variable_name=selected_var_key,
        display_name=v_name,
        unit=v_unit,
        season_name=season_def.name,
    )

    # Metric Cards Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        rate_val = f"{trend.change_per_decade:+.2f} {v_unit}/decade" if trend.change_per_decade is not None else "N/A"
        st.metric("Rate of change", rate_val)
    with m2:
        tot_val = f"{trend.total_change:+.2f} {v_unit}" if trend.total_change is not None else "N/A"
        st.metric(f"Net change ({trend.start_year}–{trend.end_year})", tot_val)
    with m3:
        if trend.delta_vs_baseline is not None and trend.baseline_mean is not None and trend.recent_mean is not None:
            pct_str = f" ({trend.delta_percent:+.1f}%)" if trend.delta_percent is not None else ""
            delta_str = f"{trend.delta_vs_baseline:+.2f} {v_unit}{pct_str}"
            st.metric(
                "Baseline vs recent",
                delta_str,
                help=f"Baseline ({trend.baseline_period}): {trend.baseline_mean:.2f} {v_unit} vs Recent ({trend.recent_period}): {trend.recent_mean:.2f} {v_unit}",
            )
        else:
            st.metric("Baseline vs recent", "N/A")
    with m4:
        p_str = f"p = {trend.p_value:.4f}" if trend.p_value is not None else "N/A"
        sig_label = "Statistically significant (p < 0.05)" if trend.is_significant else "Not statistically significant"
        st.metric("Statistical significance", p_str, help=f"OLS t-test: {sig_label}. R² = {trend.r_squared:.3f}")

    # Plotly Trend Chart
    if trend.annual_data:
        chart_df = pd.DataFrame(trend.annual_data)
        fig = go.Figure()
        # Observed markers and line
        fig.add_trace(go.Scatter(
            x=chart_df["year"],
            y=chart_df["observed"],
            mode="lines+markers",
            name=f"Observed annual {v_name}",
            line=dict(color=BRAND_GREEN, width=2),
            marker=dict(size=7, color=BRAND_GREEN),
        ))
        # OLS Trend line
        fig.add_trace(go.Scatter(
            x=chart_df["year"],
            y=chart_df["trend_fitted"],
            mode="lines",
            name=f"Linear trend ({trend.change_per_decade:+.2f} {v_unit}/decade)",
            line=dict(color=ACCENT_RED, width=2.5, dash="dash"),
        ))
        # Baseline mean horizontal segment
        if trend.baseline_mean is not None:
            base_end_yr = int(trend.baseline_period.split("–")[-1])
            fig.add_trace(go.Scatter(
                x=[trend.start_year, base_end_yr],
                y=[trend.baseline_mean, trend.baseline_mean],
                mode="lines",
                name=f"Baseline mean ({trend.baseline_period}): {trend.baseline_mean:.2f} {v_unit}",
                line=dict(color=ACCENT_BLUE, width=1.5, dash="dot"),
            ))
        # Recent mean horizontal segment
        if trend.recent_mean is not None:
            rec_start_yr = int(trend.recent_period.split("–")[0])
            fig.add_trace(go.Scatter(
                x=[rec_start_yr, trend.end_year],
                y=[trend.recent_mean, trend.recent_mean],
                mode="lines",
                name=f"Recent mean ({trend.recent_period}): {trend.recent_mean:.2f} {v_unit}",
                line=dict(color=ACCENT_AMBER, width=1.5, dash="dot"),
            ))

        fig.update_layout(
            title=f"Historical {season_def.name} {v_name} ({trend.start_year}–{trend.end_year})",
            xaxis_title="Year",
            yaxis_title=f"{v_name} ({v_unit})",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**Methodology notes:** {trend.method_notes}")

    # 5. Underlying Annual Data Inspector
    with st.expander("📋 Inspect underlying annual season data & anomalies"):
        if trend.annual_data:
            summary_table_df = pd.DataFrame(trend.annual_data)
            st.dataframe(
                summary_table_df.style.format({
                    "observed": "{:.2f}",
                    "trend_fitted": "{:.2f}",
                    "anomaly_from_mean": "{:+.2f}",
                }),
                use_container_width=True,
            )

    # 6. Scientific Boundary Disclosures
    st.info(
        "🛡️ **Scientific & Interpretive Boundaries:**\n"
        "- **Descriptive, not causal:** Observed temperature or rainfall trends describe historical atmospheric conditions in a gridded reanalysis product. They do not prove that crop yield, farm profits, or soil health changed proportionally.\n"
        "- **No linear extrapolation:** Historical trends represent past observations and must not be extrapolated linearly as future climate forecasts.\n"
        "- **Gridded resolution:** NASA POWER observations are derived from NASA GEOS/MERRA-2 gridded models (~0.5° latitude × 0.625° longitude), not direct on-farm microclimate sensors."
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⬅️ Back to climate insights", use_container_width=True):
            _go("Climate Insights")
    with col_btn2:
        if st.button("➡️ Continue to farmer priorities", type="primary", use_container_width=True):
            _go("Farmer Priorities")

    _footer()


def render_priorities() -> None:
    st.title("⚖️ Farmer priorities")
    st.caption("Weights describe what matters most for comparing plans. They are normalized to sum to one and are not probabilities of success.")

    profiles = _weight_profiles()
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.selectbox("Starting profile", tuple(profiles), format_func=lambda item: item.replace("_", " ").title())
    with col2:
        if st.button("Apply this profile", use_container_width=True):
            st.session_state["weights"] = dict(profiles[name])
            for metric, value in profiles[name].items():
                st.session_state[f"priority_{metric}"] = int(round(value * 100))
            st.rerun()

    current = st.session_state["weights"]
    raw: dict[str, float] = {}
    st.markdown("##### Adjust priorities")
    cols = st.columns(len(METRICS))
    for col, metric in zip(cols, METRICS):
        with col:
            raw[metric] = st.slider(
                METRIC_LABELS[metric], 0, 100,
                int(round(current[metric] * 100)),
                key=f"priority_{metric}",
            )

    try:
        weights = normalize_weights(raw)
        st.session_state["weights"] = weights
        with st.container(border=True):
            st.markdown("##### Normalized weights")
            weight_cols = st.columns(len(METRICS))
            for col, m in zip(weight_cols, METRICS):
                with col:
                    st.metric(METRIC_LABELS[m], f"{weights[m]:.2f}")
    except RotationInputError as error:
        st.error(str(error))

    with st.container(border=True):
        st.session_state["planning_horizon"] = st.selectbox(
            "Planning horizon (seasons)", (2, 3),
            index=(2, 3).index(st.session_state["planning_horizon"]),
        )
        st.caption("The baseline plan uses historical NASA POWER context. Hypothetical stress tests are configured after baseline alternatives are generated.")

    st.info(
        "Current catalogue evidence supports FAO-56 crop water balance, FAO EcoCrop thermal suitability, "
        "and indicative GoI MSP/PAU gross margin benchmarks.",
        icon="ℹ️",
    )
    if st.button("🔄 View rotation recommendations", type="primary"):
        _go("Rotation Recommendations")
    _footer()


def _status_icon(status: str) -> str:
    return {"pass": "✅", "fail": "⛔", "unknown": "⚠️"}.get(status, "•")


def _render_economics_tab(plan: Any) -> None:
    """Render indicative economics based on GoI MSP and PAU benchmark costs."""
    crops_dict = _rotation_engine().crops
    plan_crops = [crops_dict[cid] for cid in plan.crop_ids]
    wb = getattr(plan, "water_balance", None)
    net_irr = wb.total_net_irrigation_mm if wb is not None and getattr(wb, "total_net_irrigation_mm", None) is not None else 600.0
    rot_econ = compute_rotation_economics(plan_crops, plan.seasons, net_irrigation_mm=net_irr)
    baseline_comp = compare_vs_rice_wheat_baseline(plan_crops, plan.seasons, net_irr)

    st.markdown("#### 💰 Indicative Rotation Economics & MSP Benchmarks")
    st.caption(
        "Estimated gross margins calculated from Government of India Minimum Support Prices (MSP 2024-25) "
        "and Punjab Agricultural University (PAU) benchmark production costs. Indicative only — not a revenue guarantee."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rev_str = f"₹{rot_econ.total_revenue_inr_ha:,.0f}/ha" if rot_econ.total_revenue_inr_ha is not None else "N/A"
        st.metric("Total Gross Revenue", rev_str)
    with col2:
        st.metric("Benchmark Cost", f"₹{rot_econ.total_cost_inr_ha:,.0f}/ha")
    with col3:
        margin_str = f"₹{rot_econ.total_margin_inr_ha:,.0f}/ha" if rot_econ.total_margin_inr_ha is not None else "N/A"
        st.metric("Indicative Gross Margin", margin_str)
    with col4:
        wp = rot_econ.water_productivity_inr_per_m3
        st.metric("Water Productivity", f"₹{wp:.1f}/m³" if wp is not None else "N/A")

    st.markdown(f"**Comparison vs Conventional Rice-Wheat:** {baseline_comp.headline_summary}")

    rows = []
    for ce in rot_econ.crop_economics:
        c_meta = crops_dict.get(ce.crop_id, {})
        bn = c_meta.get("bilingual_name", {})
        bilingual = f"{bn.get('pa', '')} / {bn.get('hi', '')}" if bn else ""
        price_str = f"₹{ce.msp_inr_per_q:,.0f}/q" if ce.msp_inr_per_q is not None else "N/A"
        proc_str = "✅ Assured (MSP)" if ce.msp_procurement_assured else "⚠️ Market dependent"
        rev_val = f"₹{ce.indicative_gross_revenue_inr_ha:,.0f}" if ce.indicative_gross_revenue_inr_ha is not None else "N/A"
        margin_val = f"₹{ce.indicative_gross_margin_inr_ha:,.0f}" if ce.indicative_gross_margin_inr_ha is not None else "N/A"
        rows.append({
            "Crop": ce.crop_name,
            "Regional Name": bilingual,
            "Season": ce.season,
            "Benchmark Yield (q/ha)": f"{ce.benchmark_yield_q_ha:.1f}" if ce.benchmark_yield_q_ha else "N/A",
            "Price": price_str,
            "Revenue (₹/ha)": rev_val,
            "Cost (₹/ha)": f"₹{ce.benchmark_cost_inr_ha:,.0f}" if ce.benchmark_cost_inr_ha else "N/A",
            "Gross Margin (₹/ha)": margin_val,
            "Procurement": proc_str,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.expander("Sources, assumptions & economic caveats"):
        for disclaimer in ECONOMIC_DISCLAIMERS:
            st.markdown(f"- {disclaimer}")
        st.caption("Data Sources: Commission for Agricultural Costs and Prices (CACP) Price Policy Reports 2024-25; PAU Farm Management Guide (2024).")


def _plan_view(plan: Any, index: int) -> None:
    crops_dict = _rotation_engine().crops
    title = " → ".join(plan.crop_names)
    status_badge = {"feasible_with_known_constraints": "🟢", "conditionally_feasible": "🟡", "infeasible": "🔴"}.get(plan.status, "⚪")
    with st.expander(f"{status_badge} Alternative {index}: {title}", expanded=index == 1):
        # Plain-language explanation for farmers
        plain_text = generate_plain_language_explanation(plan)
        st.info(f"💡 {plain_text}")

        # Sequence table with bilingual names
        bilingual_names = []
        for cid in plan.crop_ids:
            c = crops_dict[cid]
            bn = c.get("bilingual_name", {})
            pa = bn.get("pa", "")
            hi = bn.get("hi", "")
            if pa and hi:
                bilingual_names.append(f"{c['name']} ({pa} / {hi})")
            else:
                bilingual_names.append(c['name'])
        sequence = pd.DataFrame({
            "Season": plan.seasons,
            "Crop (English)": plan.crop_names,
            "ਖੇਤਰੀ ਨਾਮ / क्षेत्रीय नाम": bilingual_names,
            "Crop ID": plan.crop_ids,
        })
        st.dataframe(sequence, hide_index=True, use_container_width=True)
        st.caption("Planning seasons are crop-calendar slots, not dated harvest or planting predictions.")

        # Score metrics
        cols = st.columns(len(METRICS))
        for column, metric in zip(cols, METRICS):
            score = plan.metrics[metric].score
            column.metric(METRIC_LABELS[metric], "N/A" if score is None else f"{score:.2f}")
        st.markdown(f"**Composite comparison score:** {'Unavailable' if plan.composite_score is None else f'{plan.composite_score:.2f}'} — preference-weighted comparison only, not a probability of success.")

        # Tabs for details
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "Why these crops",
            "Feasibility checks",
            "Economics (GoI MSP & PAU)",
            "Water balance (FAO-56)",
            "Climate suitability (EcoCrop)",
            "Score methods",
            "Factors & trade-offs",
            "Soil-state estimate",
            "Recent land use (MODIS)",
        ])

        with tab1:
            for crop_id, season_name in zip(plan.crop_ids, plan.seasons):
                crop = crops_dict[crop_id]
                bn = crop.get("bilingual_name", {})
                bilingual_str = f" ({bn.get('pa', '')} | {bn.get('hi', '')})" if bn else ""
                legume = " 🫘 Catalogued as a legume; this does not quantify nitrogen fixation." if crop["legume"] else ""
                st.write(f"- **{crop['name']}**{bilingual_str} in {season_name}: {crop['intended_role']}.{legume}")

        with tab2:
            for check in plan.checks:
                sources = " ".join(f"[source]({url})" for url in check.source_urls)
                st.markdown(f"{_status_icon(check.status)} **{check.rule}:** {check.message} {sources}")

        with tab3:
            _render_economics_tab(plan)

        with tab4:
            _render_water_balance_tab(plan)

        with tab5:
            _render_climate_suitability_tab(plan)

        with tab6:
            details = pd.DataFrame({
                "Metric": [METRIC_LABELS[m] for m in METRICS],
                "Score": [plan.metrics[m].score for m in METRICS],
                "Effective weight": [plan.effective_weights[m] for m in METRICS],
                "Method": [plan.metrics[m].method for m in METRICS],
            })
            st.dataframe(details.style.format({"Score": "{:.2f}", "Effective weight": "{:.2f}"}, na_rep="N/A"), hide_index=True, use_container_width=True)

        with tab7:
            for heading, items in (("✅ Positive factors", plan.positive_factors), ("⚖️ Trade-offs", plan.tradeoffs), ("⚠️ Missing information / uncertainty", plan.uncertainty_warnings)):
                if items:
                    st.markdown(f"**{heading}**")
                    for item in items:
                        st.write(f"- {item}")

        with tab8:
            _render_soil_state_tab(plan)

        with tab9:
            _render_land_use_tab(plan)

        st.caption("Supporting URLs: " + " · ".join(plan.source_urls))


def _render_land_use_tab(plan: Any) -> None:
    """How this plan's seasons compare with MODIS-observed recent land use."""
    comparison = getattr(plan, "land_use_comparison", None)
    if comparison is None:
        st.info("No MODIS land-use record for this farm location. Retrieve it on the Farm Profile page to compare this plan with recent cropping seasons.")
        return
    if comparison.added_seasons:
        demand = comparison.added_crop_water_demand_mm
        st.warning(
            "**This plan adds a cropping season** compared with recent land use: "
            + ", ".join(f"{crop.replace('_', ' ')} in {season}" for crop, season in zip(comparison.added_crops, comparison.added_seasons))
            + (f". Estimated extra crop water demand: **{demand:.0f} mm** (FAO-56 ETc for that crop period)." if demand is not None else ".")
            + " Confirm that irrigation water, labour and the sowing window are available.",
            icon="💧",
        )
    else:
        st.success("Every planned season was green at this location in most recent years; the plan does not add a cropping season.")
    for line in comparison.evidence:
        st.write(f"- {line}")
    st.caption("This comparison changes the plan's status and trade-offs, not its composite score, so crop water demand is not counted twice.")


def _render_water_balance_tab(plan: Any) -> None:
    """Render the FAO-56 crop water requirement and water balance details."""
    wb = getattr(plan, "water_balance", None)
    if wb is None or getattr(wb, "total_etc_mm", None) is None:
        st.info(
            "💧 **FAO-56 climate water balance is not active for this plan.** "
            "Retrieve NASA POWER climate data in Climate Insights to compute crop water requirements (ETc) "
            "from real meteorological observations."
        )
        water_metric = plan.metrics.get("water_suitability")
        if water_metric and water_metric.method:
            st.caption(f"Current method: {water_metric.method}")
        return

    st.markdown("#### 💧 FAO-56 Crop Water Balance & Net Irrigation Requirement")
    st.caption(
        "Computed using FAO-56 Penman–Monteith ET₀, crop coefficients (Kc), and USDA SCS effective rainfall. "
        "Each crop uses only the days of its own season window (kharif 1 Jun, rabi 1 Nov, summer 1 Apr) for its FAO-56 crop duration. "
        "A 'Composite' period joins days from different calendar years because no complete season is in the record."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total crop demand (ETc)", f"{wb.total_etc_mm:.1f} mm")
    with col2:
        st.metric("Effective rainfall", f"{wb.total_effective_rainfall_mm:.1f} mm")
    with col3:
        nir = wb.total_net_irrigation_mm if wb.total_net_irrigation_mm is not None else 0.0
        st.metric("Net irrigation deficit", f"{nir:.1f} mm")
    with col4:
        score = plan.metrics["water_suitability"].score
        st.metric("Water score", f"{score:.2f}" if score is not None else "N/A")

    rows = []
    for cr in wb.crop_results:
        rows.append({
            "Crop": cr.crop_name,
            "Season": cr.season,
            "ET₀ (mm)": f"{cr.et0_total_mm:.1f}" if cr.et0_total_mm is not None else "N/A",
            "Mean Kc": f"{cr.kc_weighted_mean:.2f}" if cr.kc_weighted_mean is not None else "N/A",
            "ETc demand (mm)": f"{cr.etc_total_mm:.1f}" if cr.etc_total_mm is not None else "N/A",
            "Rainfall (mm)": f"{cr.total_rainfall_mm:.1f}",
            "Eff. rain (mm)": f"{cr.effective_rainfall_mm:.1f}",
            "Deficit (mm)": f"{cr.net_irrigation_requirement_mm:.1f}" if cr.net_irrigation_requirement_mm is not None else "N/A",
            "Climate period used": cr.method.split("climate period: ")[-1] if "climate period: " in cr.method else cr.method.split("mean of ")[-1],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.expander("Methodology, sources & limitations"):
        st.markdown("""
- **ET₀ Method:** FAO-56 Penman–Monteith equation (Allen et al. 1998, Eq. 6) using NASA POWER daily T2M_MAX, T2M_MIN, and ALLSKY_SFC_SW_DWN.
- **Crop Coefficients (Kc):** Sourced from [FAO-56 Table 12](https://www.fao.org/4/x0490e/x0490e0b.htm) for each crop development stage (initial, mid, end).
- **Effective Rainfall:** Estimated using USDA Soil Conservation Service (SCS) method per monthly timestep.
- **Omitted factors:** Deep percolation, surface runoff, groundwater capillary rise, and application efficiency are not modelled.
- **Root zone disclosure:** ET₀ and water deficit do NOT directly measure water stored in a specific farm's root zone.
        """)
        if wb.warnings:
            for w in wb.warnings:
                st.warning(f"⚠️ {w}")


def _render_climate_suitability_tab(plan: Any) -> None:
    """Render the FAO EcoCrop thermal suitability and heat-stress assessment."""
    ca = getattr(plan, "climate_assessment", None)
    if ca is None or not getattr(ca, "crops", ()):
        st.info(
            "🌡️ **FAO EcoCrop climate suitability is not active for this plan.** "
            "Retrieve NASA POWER climate data in Climate Insights to evaluate crop thermal suitability "
            "against documented FAO EcoCrop cardinal temperature ranges."
        )
        clim_metric = plan.metrics.get("climate_suitability")
        if clim_metric and clim_metric.method:
            st.caption(f"Current method: {clim_metric.method}")
        return

    st.markdown("#### 🌡️ FAO EcoCrop Thermal Suitability & Heat Stress Assessment")
    st.caption("Evaluates growing-season temperature compatibility using FAO EcoCrop cardinal thermal limits and regional extreme heat thresholds.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        score = plan.metrics["climate_suitability"].score
        st.metric("Climate score", f"{score:.2f}" if score is not None else "N/A")
    with col2:
        st.metric("Thermal status", ca.status.capitalize())
    with col3:
        total_heat_days = sum(getattr(c, "heat_stress_days", 0) for c in ca.crops)
        st.metric("Heat-stress days", f"{total_heat_days} days")
    with col4:
        total_frost_days = sum(getattr(c, "frost_stress_days", 0) for c in ca.crops)
        st.metric("Frost/chilling days", f"{total_frost_days} days")

    rows = []
    for c in ca.crops:
        opt_str = f"{c.tmin_optimal:.0f} – {c.tmax_optimal:.0f} °C" if c.tmin_optimal is not None else "N/A"
        abs_str = f"{c.tmin_absolute:.0f} – {c.tmax_absolute:.0f} °C" if c.tmin_absolute is not None else "N/A"
        heat_str = f"{c.extreme_heat_threshold:.0f} °C" if c.extreme_heat_threshold is not None else "N/A"
        rows.append({
            "Crop": c.crop_name,
            "Season": c.season,
            "Mean Temp (°C)": f"{c.t_mean:.1f}" if c.t_mean is not None else "N/A",
            "Optimal Range": opt_str,
            "Absolute Limits": abs_str,
            "Max Temp (°C)": f"{c.t_max:.1f}" if c.t_max is not None else "N/A",
            "Heat Threshold": heat_str,
            "Heat Days": str(c.heat_stress_days),
            "Score": f"{c.climate_suitability_score:.2f}" if c.climate_suitability_score is not None else "N/A",
            "Status": c.status.capitalize(),
            "Climate period used": c.climate_period or "—",
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    with st.expander("Methodology, sources & limitations"):
        st.markdown("""
- **Thermal Suitability:** Piece-wise linear response function based on [FAO EcoCrop Database](https://ecocrop.apps.fao.org/) cardinal temperature limits ($T_{\\min,\\text{abs}}$, $T_{\\min,\\text{opt}}$, $T_{\\max,\\text{opt}}$, $T_{\\max,\\text{abs}}$).
- **Extreme Heat Thresholds:** Sourced from Punjab Agricultural University (PAU) Packages of Practices (Rabi & Kharif 2026) for regional thermal risks (e.g. 32°C terminal heat for wheat).
- **Stress Deduction:** Proportional reduction in suitability based on frequency of daily maximum temperatures reaching documented threshold.
- **Scientific Boundary:** Assesses physiological thermal adaptation from gridded meteorological observations. It does not predict yield or model localized microclimate canopy variations.
        """)
        if ca.warnings:
            for w in ca.warnings:
                st.warning(f"⚠️ {w}")


def _render_soil_state_tab(plan: Any) -> None:
    """Feature E: Render the simplified soil-state / nutrient-balance model."""
    engine = _rotation_engine()
    is_legume = {crop_id: engine.crops[crop_id]["legume"] for crop_id in plan.crop_ids}
    soc = _resolved_soil()["organic_carbon"]
    soc_range = (soc.low, soc.high) if soc.low is not None and soc.high is not None else None

    report = build_soil_state_report(
        crop_ids=plan.crop_ids,
        crop_names=plan.crop_names,
        seasons=plan.seasons,
        is_legume=is_legume,
        initial_soc_percent=soc.value,  # type: ignore[arg-type]
        soc_source_type=soc.source_type,
        soc_source_label=soc.source_label if soc.value is not None else None,
        soc_depth_m=0.30 if soc.source_type == "soilgrids_estimate" else 0.20,
        soc_range_percent=soc_range,
    )
    if soc.value is None:
        st.caption("Starting organic carbon: **unknown** (not entered, and no usable SoilGrids estimate).")
    else:
        range_text = f" (range {soc.low:.2f}–{soc.high:.2f}%)" if soc_range else ""
        st.caption(f"Starting organic carbon used: **{soc.value:.2f}%**{range_text} · source: **{soc.source_label}** · depth: {soc.depth}")

    st.warning(
        "**Simplified estimate** — uses published FAO/IPCC equations with assumed defaults. "
        "Not calibrated to local Punjab conditions. For educational comparison only.",
        icon="⚠️",
    )

    # Nutrient balance table
    rows = []
    for est in report.nutrient_estimates:
        rows.append({
            "Crop": est.crop_name,
            "Season": est.season,
            "Residue N return (kg/ha)": f"{est.residue_n_return_kg_ha[0]}–{est.residue_n_return_kg_ha[1]}",
            "Residue C input (kg/ha)": f"{est.residue_c_input_kg_ha[0]}–{est.residue_c_input_kg_ha[1]}",
            "Legume N credit (kg/ha)": f"{est.legume_n_credit_kg_ha[0]}–{est.legume_n_credit_kg_ha[1]}" if est.legume_n_credit_kg_ha else "—",
        })
    st.markdown("**Per-crop nutrient contribution estimates**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # SOC direction
    if report.soc_estimate:
        soc_est = report.soc_estimate
        direction_label = {
            "likely_increase": "🟢 Likely increase",
            "likely_decrease": "🔴 Likely decrease",
            "uncertain": "🟡 Uncertain — more data needed",
        }
        st.markdown("**Soil organic carbon direction (simplified)**")
        st.info(direction_label.get(soc_est.estimated_annual_change_direction, "Unknown"))
        st.caption(soc_est.method_description)

    # Missing inputs & limitations
    with st.expander("Required inputs and limitations"):
        st.markdown("**Required inputs (not all available):**")
        for inp in report.required_inputs:
            st.write(f"- {inp}")
        if report.missing_inputs:
            st.markdown("**Currently missing:**")
            for m in report.missing_inputs:
                st.write(f"- ⚠️ {m}")
        st.markdown("**Limitations:**")
        for lim in report.limitations:
            st.write(f"- {lim}")


def render_recommendations() -> None:
    st.title("🔄 Rotation recommendations")
    if not _farm_is_ready():
        st.info("Save a farm profile before generating source-linked rotations.")
        _footer()
        return
    if not st.session_state["power_dataset"]:
        st.warning("No real NASA POWER request is attached yet. The engine can still check catalogue and farmer-input rules, but climate context is absent. Retrieve it in Climate Insights for the complete intended workflow.")

    result = _plans()
    if not result:
        _footer()
        return
    st.write(result.message)
    if not result.plans:
        st.error("No valid documented rotation can be generated with these inputs.")
        for item in result.exclusions[:12]:
            st.write(f"- {_status_icon(item.status)} {item.message}")
        st.info("Review the selected starting season, previous crop, crop avoidance list, known hard soil constraints, water budget, and supported relationship coverage.")
        _footer()
        return

    st.success(f"🎉 {len(result.plans)} engine-generated alternative(s) shown below.")

    # ── Top Alternative vs Conventional Rice-Wheat Baseline ──
    top_plan = result.plans[0]
    crops_dict = _rotation_engine().crops
    top_crops = [crops_dict[cid] for cid in top_plan.crop_ids]
    wb = getattr(top_plan, "water_balance", None)
    top_irr = wb.total_net_irrigation_mm if wb is not None and getattr(wb, "total_net_irrigation_mm", None) is not None else 600.0
    baseline_comp = compare_vs_rice_wheat_baseline(top_crops, top_plan.seasons, top_irr)
    top_econ = compute_rotation_economics(top_crops, top_plan.seasons, top_irr)
    with st.container(border=True):
        st.markdown("### 🏆 Top Alternative vs Conventional Rice-Wheat Baseline")
        st.markdown(f"**{baseline_comp.headline_summary}**")
        b_c1, b_c2, b_c3, b_c4 = st.columns(4)
        with b_c1:
            st.metric("💧 Water Saved vs Rice-Wheat", f"{baseline_comp.water_saved_mm:.0f} mm", f"-{baseline_comp.water_saved_pct:.1f}%")
        with b_c2:
            margin_str = f"₹{top_econ.total_margin_inr_ha:,.0f}/ha" if top_econ.total_margin_inr_ha is not None else "N/A"
            st.metric("💰 Indicative Gross Margin", margin_str)
        with b_c3:
            diff_str = f"{'+' if (baseline_comp.margin_diff_inr_ha or 0) >= 0 else ''}₹{baseline_comp.margin_diff_inr_ha:,.0f}/ha" if baseline_comp.margin_diff_inr_ha is not None else "N/A"
            st.metric("📈 Margin vs Rice-Wheat", diff_str)
        with b_c4:
            st.metric("💧 Water Saved Volume", f"{baseline_comp.water_saved_m3_per_ha:,.0f} m³/ha")
        st.caption("Baseline: Traditional flooded Rice (Kharif) → Wheat (Rabi) rotation (~1,750 mm irrigation demand, PAU benchmark yields). Economics based on GoI MSP 2024-25 & PAU costs.")

    for index, plan in enumerate(result.plans, 1):
        _plan_view(plan, index)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧪 Stress-test these alternatives", type="primary", use_container_width=True):
            _go("Hypothetical stress tests")
    with col2:
        if st.button("📊 Compare alternatives", use_container_width=True):
            _go("Comparison View")
    _footer()


def render_scenarios() -> None:
    st.title("🧪 Hypothetical stress tests")
    st.info(
        "This page applies **simple what-if changes you choose** (less rain, hotter days, less irrigation water) to the "
        "observed NASA POWER record. These are not NASA climate projections; projections are on the "
        "**🌍 Future climate (NASA CMIP6)** page.",
        icon="🧪",
    )
    st.warning(
        "These are **user-configured hypothetical stress tests**, not forecasts or "
        "probabilities. They expose sensitivity to selected assumptions; they do not "
        "predict crop yield.",
        icon="⚠️",
    )
    result = _plans()
    if not result or not result.plans:
        st.info("Generate baseline alternatives before running stress tests.")
        if st.button("➡️ Open recommendations"):
            _go("Rotation Recommendations")
        _footer()
        return

    # ── Scenario configuration ──
    st.subheader("Set hypothetical stress assumptions")
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            dry = st.slider(
                "🏜️ Dry test: reduce precipitation (%)",
                0, 100, int(st.session_state["dry_reduction_pct"]),
                help="Multiplies available PRECTOTCORR values. It does not change the water budget.",
            )
        with col2:
            hot = st.slider(
                "🌡️ Hot test: increase temperature (°C)",
                0.0, 10.0, float(st.session_state["hot_increase_c"]), step=0.5,
                help="Adds this amount to T2M, T2M_MIN and T2M_MAX. It is not a forecast.",
            )
        with col3:
            irrigation = st.slider(
                "💧 Water-budget reduction (%)",
                0, 100, int(st.session_state["irrigation_reduction_pct"]),
                help="Applies only to the farmer-provided total crop-water budget.",
            )
        if st.button("✅ Apply stress-test assumptions", type="primary", use_container_width=True):
            st.session_state["dry_reduction_pct"] = dry
            st.session_state["hot_increase_c"] = hot
            st.session_state["irrigation_reduction_pct"] = irrigation
            st.toast("Stress-test assumptions updated.", icon="✅")
            st.rerun()

    try:
        scenarios = _scenario_definitions()
    except ScenarioInputError as error:
        st.error(str(error))
        return

    # ── Scenario definitions table ──
    st.subheader("Scenario definitions")
    st.dataframe(
        pd.DataFrame({
            "Scenario": [item.label for item in scenarios],
            "Definition": [item.description for item in scenarios],
            "Type": ["Hypothetical stress test" if item.is_hypothetical else "Retrieved historical context" for item in scenarios],
        }),
        hide_index=True,
        use_container_width=True,
    )

    # ── Transformed climate summaries ──
    dataset: PowerDataset | None = st.session_state["power_dataset"]
    if dataset:
        transformed_rows = []
        for scenario in scenarios:
            frame = transform_climate_frame(dataset.data, scenario)
            transformed_rows.append({
                "Scenario": scenario.label,
                "Mean T2M (°C)": frame["T2M"].mean() if "T2M" in frame else None,
                "Precip. total (mm)": frame["PRECTOTCORR"].sum(skipna=True) if "PRECTOTCORR" in frame else None,
                "Type": "Hypothetical" if scenario.is_hypothetical else "Historical",
            })
        st.subheader("Climate-context changes")
        st.dataframe(
            pd.DataFrame(transformed_rows).style.format({"Mean T2M (°C)": "{:.2f}", "Precip. total (mm)": "{:.1f}"}, na_rep="N/A"),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Retrieve NASA POWER data in Climate Insights to view transformed climate context.")

    # ── Robustness assessment ──
    report = evaluate_robustness(
        _rotation_engine(), result.plans, _profile_from_state(),
        scenarios, dataset.data if dataset else None,
    )

    st.subheader("Rotation robustness")
    rows = []
    for position, plan in enumerate(result.plans, 1):
        for outcome in report.outcomes[plan.crop_ids]:
            rows.append({
                "Alternative": f"Alt {position}: {' → '.join(plan.crop_names)}",
                "Scenario": outcome.scenario.label,
                "Feasibility": outcome.feasibility.replace("_", " "),
                "Hard constraint violated": "⛔ Yes" if outcome.hard_constraint_violated else "✅ No",
                "Water budget (mm)": outcome.water_budget_mm,
                "Water score": outcome.component_scores["water_suitability"],
                "Δ Water score": outcome.score_changes_from_baseline["water_suitability"],
            })
    st.dataframe(
        pd.DataFrame(rows).style.format({
            "Water budget (mm)": "{:.1f}",
            "Water score": "{:.2f}",
            "Δ Water score": "{:+.2f}",
        }, na_rep="N/A"),
        hide_index=True,
        use_container_width=True,
    )

    # Hard-constraint violation alerts
    for plan in result.plans:
        outcomes = report.outcomes[plan.crop_ids]
        failures = [outcome for outcome in outcomes if outcome.hard_constraint_violated]
        if failures:
            st.error(
                f"⛔ {' → '.join(plan.crop_names)} has a hard-constraint failure in: " +
                "; ".join(f"**{item.scenario.label}** ({' '.join(item.hard_failure_messages)})" for item in failures),
            )

    # ── Sensitivity summary ──
    st.subheader("Sensitivity summary")
    for position, plan in enumerate(result.plans, 1):
        outcomes = report.outcomes[plan.crop_ids]
        feasible_count = sum(1 for o in outcomes if not o.hard_constraint_violated)
        total = len(outcomes)
        with st.container(border=True):
            st.markdown(f"**Alt {position}: {' → '.join(plan.crop_names)}**")
            st.progress(feasible_count / total if total else 0, text=f"Feasible in {feasible_count}/{total} scenarios")
            if feasible_count == total:
                st.success("Passes all tested scenarios.")
            elif feasible_count == 0:
                st.error("Fails all tested scenarios — reconsider this rotation or adjust water budget.")
            else:
                st.warning(f"Sensitive to changing assumptions — review the {total - feasible_count} failing scenario(s).")

    # ── Uncertainty section ──
    st.subheader("What remains uncertain")
    uncertainty_tabs = st.tabs(["📋 Data coverage", "🧮 Model uncertainty", "🌀 Scenario uncertainty"])
    for tab, (heading, notes) in zip(uncertainty_tabs, [
        ("Data coverage", report.data_coverage_notes),
        ("Model uncertainty", report.model_uncertainty_notes),
        ("Scenario uncertainty", report.scenario_uncertainty_notes),
    ]):
        with tab:
            for note in notes:
                st.write(f"- {note}")
    st.caption("No numerical confidence percentage is shown because this prototype has no validated probabilistic model.")

    if st.button("📊 Compare plans and trade-offs", type="primary"):
        _go("Comparison View")
    _footer()


def _fmt_spread(spread: Any, unit: str, digits: int = 1) -> str:
    if spread is None:
        return "Not available"
    return f"{spread.median:+.{digits}f} {unit} (models: {spread.low:+.{digits}f} to {spread.high:+.{digits}f})"


def _plan_projection(plan: Any, extract: ProjectionExtract) -> Any:
    """Cache per session: running 5 models × 3 periods takes a few seconds per plan."""
    profile = _profile_from_state()
    key = (
        plan.crop_ids, profile.start_season, profile.total_crop_water_budget_mm,
        tuple(sorted(profile.priority_weights.items())), repr(profile.soil), profile.previous_crop_id,
    )
    cache = st.session_state.setdefault("projection_cache", {})
    if key not in cache:
        cache[key] = compare_plan(_rotation_engine(), plan.crop_ids, profile, extract)
    return cache[key]


def render_future_climate() -> None:
    st.title("🌍 Future climate projections (NASA NEX-GDDP-CMIP6)")
    st.warning(
        "**Climate projections are not weather forecasts.** Each projection describes a plausible 20-year climate under an "
        "emissions pathway, as simulated by one climate model. Models disagree, so FieldShift shows the middle value "
        "and the range across models. Values are for a ~25 km grid cell, not your field.",
        icon="🌍",
    )
    with st.container(border=True):
        st.markdown(
            "**Three kinds of climate information in FieldShift — kept separate:**\n"
            "1. **Observed history** (NASA POWER) — Climate Insights and Climate Trends pages.\n"
            "2. **NASA climate projections** (this page) — each model's future period compared with *the same model's* 1995–2014 simulation.\n"
            "3. **Hypothetical stress tests** — simple what-if changes you choose, on the Hypothetical stress tests page."
        )
    extract = _projection_extract()
    if extract is None:
        st.error("No verified projection extract is installed. See docs/FUTURE_CLIMATE.md for how to create one with scripts/extract_nex_gddp_cmip6.py.")
        _footer()
        return
    if not _farm_is_ready():
        st.info("Save a farm location first.")
        _footer()
        return
    farm = st.session_state["farm"]
    if not extract.covers(farm["latitude"], farm["longitude"]):
        st.info(
            f"The installed projection extract covers only the 0.25° grid cell centred at {extract.grid_cell[0]:.3f} N, "
            f"{extract.grid_cell[1]:.3f} E (the demonstration farm). FieldShift does not borrow it for other locations. "
            "Run scripts/extract_nex_gddp_cmip6.py for this farm's coordinates to add one."
        )
        _footer()
        return

    with st.expander("📋 Data provenance: models, scenarios, periods, licences"):
        rows = []
        for model in extract.models:
            ref = extract.records[(model, REFERENCE_EXPERIMENT)]
            rows.append({
                "Model": model, "Variant": ref.variant, "Licence": ref.licence or "Not stated",
                "Dataset version": ref.dataset_version, "Calendar": ref.calendar,
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.markdown(
            "\n".join(f"- **{SCENARIO_LABELS[name]}**" for name in extract.experiments)
            + f"\n- Grid cell centre: {extract.grid_cell[0]:.3f} N, {extract.grid_cell[1]:.3f} E (0.25°, about 25 km); "
            f"requested point {extract.requested_latitude:.2f} N, {extract.requested_longitude:.2f} E"
            + f"\n- Extracted from the NCCS THREDDS service on {extract.retrieved_utc}"
            + f"\n- Citation: {extract.citation}"
            + f"\n- [Dataset page]({extract.documentation}) · [Technical note]({extract.technical_note})"
        )

    st.subheader("1. How the climate changes by mid-century")
    season_names = {"kharif": "Kharif (Jun–Oct)", "rabi": "Rabi (Nov–Apr)", "summer": "Summer / zaid (Apr–mid-Jun)"}
    season_id = st.radio("Season", list(season_names), format_func=season_names.get, horizontal=True)
    changes = climate_changes(extract, season_id)
    indicator_rows = [
        ("Mean temperature", "mean_temperature_c", "°C", 1),
        ("Average daily maximum", "mean_tmax_c", "°C", 1),
        ("Days with maximum ≥ 35 °C (per season)", "heat_days", "days", 0),
        ("Seasonal rainfall", "precipitation_pct", "%", 0),
    ]
    table = []
    for label, key, unit, digits in indicator_rows:
        row = {"Change vs each model's 1995–2014 simulation": label}
        for scenario, values in changes.items():
            spread = values.get(key)
            row[SHORT_LABELS[scenario]] = _fmt_spread(spread, unit, digits)
            row[f"{SHORT_LABELS[scenario]}: model agreement"] = spread.agreement if spread else "—"
        table.append(row)
    st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    st.caption("Middle value across 5 models, with the lowest and highest model in brackets. Rainfall changes are usually much less certain than temperature changes.")

    st.subheader("2. How your rotation plans compare under each scenario")
    result = _plans()
    if not result or not result.plans:
        st.info("Generate rotation alternatives first (Rotation Recommendations).")
        _footer()
        return
    labels = {f"Alt {i}: {' → '.join(plan.crop_names)}": plan for i, plan in enumerate(result.plans, 1)}
    chosen_label = st.selectbox("Plan to examine", list(labels))
    plan = labels[chosen_label]
    with st.spinner("Running this plan through 5 models × 3 periods…"):
        comparison = _plan_projection(plan, extract)
    detail = []
    for key, label in INDICATOR_LABELS.items():
        base = ensemble_median(comparison, REFERENCE_EXPERIMENT, key)
        row = {"Indicator": label, SHORT_LABELS[REFERENCE_EXPERIMENT]: "—" if base is None else f"{base:.2f}" if base <= 1.5 else f"{base:.0f}"}
        for scenario in comparison.changes:
            spread = comparison.changes[scenario].get(key)
            digits = 2 if key in ("water_suitability", "climate_suitability", "composite") else 0
            row[f"{SHORT_LABELS[scenario]} change"] = _fmt_spread(spread, "", digits).replace(" (", " (").strip()
        detail.append(row)
    st.dataframe(pd.DataFrame(detail), hide_index=True, use_container_width=True)
    st.caption(
        "Same crops, crop calendar, water budget and priority weights in every column. The first column is the middle value of "
        "the five models' historical simulations; the others show the change from each model's own historical value."
    )
    for scenario, models in comparison.hard_failures.items():
        st.error(f"Under {SHORT_LABELS[scenario]}, a documented hard constraint fails for: {', '.join(models)}.")

    chart_rows = []
    for experiment, per_model in comparison.absolute.items():
        for model, values in per_model.items():
            for key in ("water_suitability", "climate_suitability"):
                if values[key] is not None:
                    chart_rows.append({"Period": SHORT_LABELS[experiment], "Model": model, "Score": values[key], "Indicator": INDICATOR_LABELS[key]})
    if chart_rows:
        fig = px.strip(pd.DataFrame(chart_rows), x="Period", y="Score", color="Model", facet_col="Indicator", range_y=[0, 1.05])
        fig.update_layout(template="plotly_white", height=360, legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Each dot is one climate model. A wide spread means the models disagree.")

    if st.checkbox("Compare the ranking of all plans across scenarios (takes longer)"):
        ranking = []
        for label, candidate in labels.items():
            comp = _plan_projection(candidate, extract)
            ranking.append({"Plan": label, **{
                SHORT_LABELS[e]: ensemble_median(comp, e, "composite") for e in extract.experiments
            }})
        frame = pd.DataFrame(ranking)
        for e in extract.experiments:
            frame[f"Rank: {SHORT_LABELS[e]}"] = frame[SHORT_LABELS[e]].rank(ascending=False, method="min").astype("Int64")
        st.dataframe(frame.style.format({SHORT_LABELS[e]: "{:.3f}" for e in extract.experiments}, na_rep="—"), hide_index=True, use_container_width=True)
        st.caption("Composite = your priority weights applied to the median of the five models. A change in rank shows a plan's sensitivity to climate change, not a guarantee.")

    with st.expander("Assumptions used to compare periods"):
        for item in PROJECTION_ASSUMPTIONS:
            st.write(f"- {item}")
    _footer()


def render_comparison() -> None:
    st.title("📊 Compare alternatives")
    result = _plans()
    if not result or not result.plans:
        st.info("Set up a valid farm profile and generate alternatives first.")
        _footer()
        return

    # ── Score comparison bar chart ──
    rows = []
    for position, plan in enumerate(result.plans, 1):
        for metric in METRICS:
            score = plan.metrics[metric].score
            if score is not None:
                rows.append({
                    "Alternative": f"Alt {position}",
                    "Metric": METRIC_LABELS[metric],
                    "Score": score,
                })
    if rows:
        fig = px.bar(
            pd.DataFrame(rows), x="Alternative", y="Score", color="Metric",
            barmode="group", range_y=[0, 1],
            title="Available component scores (0–1)",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=-0.3))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No comparable numeric component scores are available for the current inputs.")

    # ── Pareto comparison ──
    vectors = {
        f"Alt {position}": {metric: plan.metrics[metric].score for metric in METRICS}
        for position, plan in enumerate(result.plans, 1)
    }
    pareto = pareto_assess(vectors)

    st.subheader("Pareto comparison")
    st.caption("A plan is dominated only if another plan is at least as high for every fully comparable available score and higher for at least one. Unknown values never become zero.")

    pareto_cols = st.columns(len(pareto))
    for col, item in zip(pareto_cols, pareto):
        with col:
            with st.container(border=True):
                status = "🏆 Non-dominated" if item.non_dominated else "📉 Dominated"
                st.markdown(f"**{item.candidate_id}**")
                st.markdown(f"Status: {status}")
                if item.dominated_by:
                    st.caption(f"Dominated by: {', '.join(item.dominated_by)}")
                if item.comparable_objectives:
                    st.caption(f"Compared on: {', '.join(item.comparable_objectives)}")

    # ── Planning timeline ──
    st.subheader("Multi-season planning timeline")
    fig = go.Figure()
    for position, plan in enumerate(result.plans, 1):
        for slot, crop_id in enumerate(plan.crop_ids):
            family = _rotation_engine().crops[crop_id]["family"]
            fig.add_bar(
                x=[1], base=[slot], y=[f"Alt {position}"],
                orientation="h",
                marker_color=FAMILY_COLOURS.get(family, "#779"),
                name=family, legendgroup=family,
                showlegend=not any(trace.name == family for trace in fig.data),
                hovertemplate=f"Season: {plan.seasons[slot]}<br>Crop: {plan.crop_names[slot]}<br>Family: {family}<extra></extra>",
            )
    fig.update_layout(
        barmode="overlay",
        template="plotly_white",
        xaxis=dict(
            tickmode="array",
            tickvals=[x + 0.5 for x in range(st.session_state["planning_horizon"])],
            ticktext=[f"Season {x + 1}" for x in range(st.session_state["planning_horizon"])],
            range=[0, st.session_state["planning_horizon"]],
        ),
        yaxis_title="", xaxis_title="Planning slot",
        height=250,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Only available component scores are drawn. A missing score is not treated as zero.")

    # ── Trade-off summary table ──
    st.subheader("Trade-off summary")
    trade_rows = []
    for position, plan in enumerate(result.plans, 1):
        land_use = getattr(plan, "land_use_comparison", None)
        trade_rows.append({
            "Alternative": f"Alt {position}: {' → '.join(plan.crop_names)}",
            "Added season vs recent land use": "Not compared" if land_use is None else (", ".join(land_use.added_seasons) or "None"),
            "Extra crop water for added season (mm)": None if land_use is None else land_use.added_crop_water_demand_mm,
            "Composite score": plan.composite_score,
            "Status": plan.status.replace("_", " "),
            "Positive factors": len(plan.positive_factors),
            "Trade-offs": len(plan.tradeoffs),
            "Uncertainty warnings": len(plan.uncertainty_warnings),
        })
    st.dataframe(
        pd.DataFrame(trade_rows).style.format({"Composite score": "{:.3f}", "Extra crop water for added season (mm)": "{:.0f}"}, na_rep="—"),
        hide_index=True, use_container_width=True,
    )

    # ── Weight Sensitivity & Rank Stability Analysis ──
    st.subheader("⚖️ Priority Weight Sensitivity & Rank Stability")
    st.caption(
        "Evaluates whether the #1 recommendation changes when farmer priority weights are varied by ±20%. "
        "A stable recommendation gives confidence that minor weight uncertainties do not flip the top choice."
    )
    try:
        stability = evaluate_rank_stability(result.plans, st.session_state["weights"], delta_fraction=0.20)
        if stability:
            badge = "🟢 Highly Stable" if stability.is_highly_stable else "🟡 Moderately Sensitive"
            st.markdown(f"**Top Alternative Stability:** {stability.summary_message}")
            st.markdown(f"Status: **{badge}** ({stability.stability_percentage:.0f}% of {stability.total_perturbations_tested} perturbation tests preserved Rank 1)")

            sens_rows = []
            for test in stability.perturbations[:10]:
                sens_rows.append({
                    "Top Plan Under Shift": " → ".join(test.top_plan_crop_names),
                    "Composite Score": f"{test.top_plan_score:.3f}",
                    "Rank 1 Preserved?": "✅ Yes" if test.is_same_top_as_baseline else "⚠️ Shifted",
                })
            st.dataframe(pd.DataFrame(sens_rows), hide_index=True, use_container_width=True)
    except Exception as exc:
        st.caption(f"Sensitivity evaluation: {exc}")

    st.info("**You retain full control** over the final choice. FieldShift shows all trade-offs but does not select a winner.", icon="ℹ️")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚖️ Change priorities and recalculate", use_container_width=True):
            _go("Farmer Priorities")
    with col2:
        if st.button("🧪 Run scenario stress tests", use_container_width=True):
            _go("Hypothetical stress tests")
    _footer()


def render_methods() -> None:
    st.title("📖 Data and methods")
    st.warning("FieldShift is an explainable decision-support prototype. It does not measure soil chemistry from space, forecast weather, predict profit/yield, or guarantee soil improvement.")

    st.subheader("Information types")
    st.dataframe(
        pd.DataFrame([
            ("Farmer-provided", "Coordinates, water budget, irrigation, soil conditions, prior crop, avoid list", "Used as entered; unknown remains unknown."),
            ("Retrieved", "NASA POWER Daily: T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN", "Historical gridded climate context; not a field measurement."),
            ("Calculated", "Precipitation total and monthly temperature summary", "Derived from retrieved daily values over the selected range."),
            ("Estimated (optional)", "ISRIC SoilGrids 250 m: sand, silt, clay, organic carbon, pH, total nitrogen (0–30 cm)", "Labelled 'Estimated from SoilGrids'; farmer/laboratory values override; used only where appropriate."),
            ("Not estimated", "Available NPK, EC, waterlogging, yield, profit, nitrogen fixed, measured soil-carbon change", "No values are fabricated when evidence is absent."),
        ], columns=["Information type", "Examples", "How FieldShift treats it"]),
        hide_index=True, use_container_width=True,
    )

    dataset: PowerDataset | None = st.session_state["power_dataset"]
    if dataset:
        p = dataset.provenance
        st.subheader("Current NASA POWER provenance")
        st.markdown(f"Date range: **{p.start_date} to {p.end_date}** · temporal resolution: **{p.temporal_resolution}** · [exact request]({p.source_url})")
        with st.expander("Parameter metadata"):
            st.write({name: {"name": item.long_name, "unit": item.unit} for name, item in p.parameter_metadata.items()})
    else:
        st.info("Retrieve NASA POWER data in Climate Insights to see request-specific provenance here.")

    st.subheader("How uncertainty is handled")
    st.markdown("""
**FieldShift distinguishes three categories of uncertainty:**

| Category | Examples | How it is disclosed |
|---|---|---|
| **Data coverage** | Missing soil measurements, incomplete climate records, coarse spatial resolution | Listed as specific missing-input notes; missing values are never filled with assumptions |
| **Model uncertainty** | Simplified agronomic rules, absent crop thermal thresholds, uncalibrated soil-state model | Each score method is documented; unavailable metrics show "N/A" not zero |
| **Scenario uncertainty** | User-defined stress tests are not forecasts, precipitation/temperature perturbations are hypothetical | Every stress test is labelled "Hypothetical stress test", never "forecast" or "prediction" |

**No numerical confidence percentage** is reported because this prototype has no validated probabilistic model.
The simplified soil-state module (Feature E) uses published FAO/IPCC relationships but has not been calibrated to Punjab conditions — this is clearly labelled on every output.
    """)

    st.subheader("Documented methods")
    st.markdown(
        "- `docs/NASA_POWER_DATA.md` — API parameters, units, resolution, quality handling, limitations.\n"
        "- `docs/CLIMATE_TRENDS_METHODOLOGY.md` — growing-season aggregations, OLS trend regression, baseline comparisons, and disclosures.\n"
        "- `docs/ROTATION_ENGINE.md` — rule checks, scoring and safeguards.\n"
        "- `docs/AGRONOMIC_ASSUMPTIONS.md` — catalogue evidence and items requiring expert review.\n"
        "- `docs/SCENARIOS_AND_UNCERTAINTY.md` — scenario definitions, transforms, and uncertainty categories.\n"
        "- `docs/SOIL_DATA.md` — SoilGrids access, units, depths, uncertainty, source precedence and limitations.\n"
        "- `data/README.md` — crop-record schema and provenance."
    )
    st.caption(
        "Integrated: NASA POWER, NASA MODIS MCD12Q2 (observed seasonal land use), NASA NEX-GDDP-CMIP6 (projections), ISRIC SoilGrids (optional). "
        "Not integrated: GPM IMERG (needs Earthdata Login), SMAP. Selection reasoning: docs/DATA_SOURCES.md."
    )
    _footer()


def _footer() -> None:
    st.markdown(
        '<div class="fieldshift-footer">'
        '🌾 FieldShift — A transparent crop-rotation planning prototype · '
        'Decision-support only, not agricultural advice'
        '</div>',
        unsafe_allow_html=True,
    )


# ──────────────────────────────── dispatcher ───────────────────────────────

def render_application() -> None:
    _init_state()
    _theme()
    _sidebar()
    dispatch = {
        PAGES[0]: render_home,
        PAGES[1]: render_farm_profile,
        PAGES[2]: render_climate,
        PAGES[3]: render_climate_trends,
        PAGES[4]: render_priorities,
        PAGES[5]: render_recommendations,
        PAGES[6]: render_scenarios,
        PAGES[7]: render_future_climate,
        PAGES[8]: render_comparison,
        PAGES[9]: render_methods,
    }
    dispatch[st.session_state["page"]]()
