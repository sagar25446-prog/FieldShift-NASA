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
from .soil_nutrient_model import build_soil_state_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
PAGES = (
    "Home / Overview",
    "Farm Profile",
    "Climate Insights",
    "Climate Trends",
    "Farmer Priorities",
    "Rotation Recommendations",
    "Scenario stress tests",
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


@st.cache_data
def _weight_profiles() -> dict[str, dict[str, float]]:
    raw = json.loads((DATA_DIR / "priority_weights.json").read_text(encoding="utf-8"))
    return {name: normalize_weights(values) for name, values in raw["profiles"].items()}


@st.cache_data
def _load_historical_fixture_dataset() -> PowerDataset:
    fixture_path = PROJECT_ROOT / "tests" / "fixtures" / "power_daily_ludhiana_historical_2000_2024.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    req = PowerRequest(
        latitude=30.9010,
        longitude=75.8573,
        start_date=date(2000, 1, 1),
        end_date=date(2024, 12, 31),
        parameters=tuple(raw["properties"]["parameter"].keys()),
    )
    return parse_power_daily_response(
        raw,
        req,
        source_url="https://power.larc.nasa.gov/api/temporal/daily/point?start=20000101&end=20241231&latitude=30.9010&longitude=75.8573&community=AG&parameters=T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M&format=JSON",
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
        "soil_source": "", "irrigation": "Unknown", "water_budget_mm": None,
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


def _go(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()


def _reset() -> None:
    for key in list(st.session_state):
        if key.startswith(("farm_", "priority_", "block_")) or key in {
            "farm", "weights", "planning_horizon", "scenario",
            "power_dataset", "power_error", "power_mode",
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


def _profile_from_state() -> FarmProfile:
    farm = st.session_state["farm"]
    dataset: PowerDataset | None = st.session_state["power_dataset"]
    climate = ClimateContext(
        source_url=dataset.provenance.source_url if dataset else None,
        date_range=f"{dataset.provenance.start_date} to {dataset.provenance.end_date}" if dataset else None,
        available_parameters=tuple(dataset.data.columns) if dataset else (),
    )
    soil = SoilInformation(
        ph=farm["ph"], electrical_conductivity_ds_m=farm["electrical_conductivity_ds_m"],
        organic_carbon_percent=farm["organic_carbon_percent"], waterlogged=farm["waterlogged"],
        highly_deteriorated_alkaline=farm["highly_deteriorated_alkaline"], well_drained=farm["well_drained"],
        texture=farm["texture"], source_description=farm["soil_source"] or None,
    )
    return FarmProfile(
        latitude=farm["latitude"], longitude=farm["longitude"], soil=soil, climate=climate,
        total_crop_water_budget_mm=farm["water_budget_mm"], previous_crop_id=farm["previous_crop_id"],
        blocked_crop_ids=frozenset(farm["blocked_crop_ids"]), priority_weights=st.session_state["weights"],
        number_of_seasons=st.session_state["planning_horizon"], start_season=farm["start_season"],
        climate_scenario=st.session_state["scenario"],
        climate_data=dataset.data if dataset else None,
    )


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
        "latitude": 30.9010,
        "longitude": 75.8573,
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
            "Scenario stress tests": "🧪",
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
            st.caption("Pre-configured profile with verified offline NASA POWER dataset.")
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
    st.caption("Optional GPM, MODIS and soil-moisture sources are not required for this first version and are not silently substituted.")
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

    with st.form("farm_profile"):
        st.subheader("📍 Location and climate request")
        a, b = st.columns(2)
        with a:
            latitude = st.text_input("Latitude (degrees)", value="" if farm["latitude"] is None else str(farm["latitude"]), key="farm_latitude", placeholder="Example: 30.9010")
        with b:
            longitude = st.text_input("Longitude (degrees)", value="" if farm["longitude"] is None else str(farm["longitude"]), key="farm_longitude", placeholder="Example: 75.8573")
        c, d = st.columns(2)
        with c:
            start_date = st.date_input("Historical start date", value=farm["start_date"], min_value=date(1981, 1, 1), key="farm_start")
        with d:
            end_date = st.date_input("Historical end date", value=farm["end_date"], min_value=date(1981, 1, 1), key="farm_end")

        st.subheader("🧪 Soil information")
        st.caption("Use laboratory or survey values where possible. These fields are not remotely measured by NASA POWER.")
        e, f, g = st.columns(3)
        with e:
            texture = st.selectbox("Texture", ("Unknown", "light", "medium", "heavy"), index=("Unknown", "light", "medium", "heavy").index(farm["texture"] or "Unknown"), key="farm_texture")
            ph = st.text_input("pH (unitless, optional)", value="" if farm["ph"] is None else str(farm["ph"]), key="farm_ph")
        with f:
            organic = st.text_input("Organic carbon (%; optional)", value="" if farm["organic_carbon_percent"] is None else str(farm["organic_carbon_percent"]), key="farm_organic")
            ec = st.text_input("Electrical conductivity (dS/m; optional)", value="" if farm["electrical_conductivity_ds_m"] is None else str(farm["electrical_conductivity_ds_m"]), key="farm_ec")
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
            values = [_number(item) for item in (ph, organic, ec, budget, field_size)]
            if any(value is not None and value < 0 for value in values):
                raise ValueError("Soil values, water budget, and field size cannot be negative.")
            reverse = {name: crop_id for crop_id, name in labels.items()}
            farm.update({
                "latitude": lat, "longitude": lon, "start_date": start_date, "end_date": end_date,
                "texture": None if texture == "Unknown" else texture, "ph": values[0],
                "organic_carbon_percent": values[1], "electrical_conductivity_ds_m": values[2],
                "waterlogged": waterlogged, "highly_deteriorated_alkaline": alkaline,
                "well_drained": drained, "soil_source": soil_source.strip(),
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

    if _farm_is_ready() and st.button("➡️ Continue to climate insights", type="primary"):
        _go("Climate Insights")
    _footer()


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
            f"Verified NASA POWER Daily archive · Location: **{p.latitude_requested:.4f}°N, {p.longitude_requested:.4f}°E** · "
            f"Date range: **{p.start_date} to {p.end_date}** ({len(dataset.data)} daily observations) · "
            "All values are real archived NASA POWER observations, never fabricated."
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
        st.warning("NASA POWER is currently unreachable or slow. You can load the verified offline snapshot to continue evaluating FieldShift without interruption.")
        if st.button("📦 Load Saved Offline Snapshot for Ludhiana", type="primary", use_container_width=True):
            st.session_state["power_dataset"] = load_offline_demo_snapshot()
            st.session_state["power_mode"] = "offline_snapshot"
            st.session_state["power_error"] = None
            st.rerun()
    dataset: PowerDataset | None = st.session_state["power_dataset"]
    if not dataset:
        st.info("No climate dataset is currently active. Retrieve live data above or load the saved offline snapshot.")
        if st.button("📦 Load Verified Offline NASA POWER Snapshot (2024 Ludhiana)"):
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
                "25-Year NASA POWER Ludhiana benchmark (2000–2024, 9,132 daily observations)",
            ],
            index=0,
            help="At least 3 complete annual seasons are required to estimate a linear trend.",
        )
        use_fixture = "25-Year" in source_choice
    else:
        if session_dataset:
            st.info(
                f"The current session climate request covers {session_dataset.provenance.start_date} to {session_dataset.provenance.end_date} "
                f"({session_span_years} year{'s' if session_span_years > 1 else ''}). Long-term trend analysis requires multi-year seasonal records (minimum 3 years). "
                "Displaying the verified 25-Year NASA POWER historical record (2000–2024) for the Ludhiana demonstration region."
            )
        else:
            st.info(
                "No custom multi-year farm climate record is loaded. "
                "Displaying the verified 25-Year NASA POWER historical record (2000–2024) for the Ludhiana demonstration region."
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
        "- **Descriptive, not causal:** Observed meteorological warming or rainfall trends describe historical atmospheric conditions. They do not prove that crop yield, farm profits, or soil health changed proportionally.\n"
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
        "Current catalogue evidence supports FAO-56 crop water balance and FAO EcoCrop thermal suitability. "
        "Economic potential remains unavailable until credible local cost/price data is configured.",
        icon="ℹ️",
    )
    if st.button("🔄 View rotation recommendations", type="primary"):
        _go("Rotation Recommendations")
    _footer()


def _status_icon(status: str) -> str:
    return {"pass": "✅", "fail": "⛔", "unknown": "⚠️"}.get(status, "•")


def _plan_view(plan: Any, index: int) -> None:
    title = " → ".join(plan.crop_names)
    status_badge = {"feasible_with_known_constraints": "🟢", "conditionally_feasible": "🟡", "infeasible": "🔴"}.get(plan.status, "⚪")
    with st.expander(f"{status_badge} Alternative {index}: {title}", expanded=index == 1):
        # Sequence table
        sequence = pd.DataFrame({"Season": plan.seasons, "Crop": plan.crop_names, "Crop ID": plan.crop_ids})
        st.dataframe(sequence, hide_index=True, use_container_width=True)
        st.caption("Planning seasons are crop-calendar slots, not dated harvest or planting predictions.")

        # Score metrics
        cols = st.columns(len(METRICS))
        for column, metric in zip(cols, METRICS):
            score = plan.metrics[metric].score
            column.metric(METRIC_LABELS[metric], "N/A" if score is None else f"{score:.2f}")
        st.markdown(f"**Composite comparison score:** {'Unavailable' if plan.composite_score is None else f'{plan.composite_score:.2f}'} — preference-weighted comparison only, not a probability of success.")

        # Tabs for details
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "Why these crops",
            "Feasibility checks",
            "Water balance (FAO-56)",
            "Climate suitability (EcoCrop)",
            "Score methods",
            "Factors & trade-offs",
            "Soil-state estimate",
        ])

        with tab1:
            crop_data = _rotation_engine().crops
            for crop_id, season_name in zip(plan.crop_ids, plan.seasons):
                crop = crop_data[crop_id]
                legume = " 🫘 Catalogued as a legume; this does not quantify nitrogen fixation." if crop["legume"] else ""
                st.write(f"- **{crop['name']}** in {season_name}: {crop['intended_role']}.{legume}")

        with tab2:
            for check in plan.checks:
                sources = " ".join(f"[source]({url})" for url in check.source_urls)
                st.markdown(f"{_status_icon(check.status)} **{check.rule}:** {check.message} {sources}")

        with tab3:
            _render_water_balance_tab(plan)

        with tab4:
            _render_climate_suitability_tab(plan)

        with tab5:
            details = pd.DataFrame({
                "Metric": [METRIC_LABELS[m] for m in METRICS],
                "Score": [plan.metrics[m].score for m in METRICS],
                "Effective weight": [plan.effective_weights[m] for m in METRICS],
                "Method": [plan.metrics[m].method for m in METRICS],
            })
            st.dataframe(details.style.format({"Score": "{:.2f}", "Effective weight": "{:.2f}"}, na_rep="N/A"), hide_index=True, use_container_width=True)

        with tab6:
            for heading, items in (("✅ Positive factors", plan.positive_factors), ("⚖️ Trade-offs", plan.tradeoffs), ("⚠️ Missing information / uncertainty", plan.uncertainty_warnings)):
                if items:
                    st.markdown(f"**{heading}**")
                    for item in items:
                        st.write(f"- {item}")

        with tab7:
            _render_soil_state_tab(plan)

        st.caption("Supporting URLs: " + " · ".join(plan.source_urls))


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
    st.caption("Computed using FAO-56 Penman–Monteith ET₀, crop coefficients (Kc), and USDA SCS effective rainfall.")

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
    farm = st.session_state["farm"]
    soc = farm.get("organic_carbon_percent")

    report = build_soil_state_report(
        crop_ids=plan.crop_ids,
        crop_names=plan.crop_names,
        seasons=plan.seasons,
        is_legume=is_legume,
        initial_soc_percent=soc,
    )

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
    for index, plan in enumerate(result.plans, 1):
        _plan_view(plan, index)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧪 Stress-test these alternatives", type="primary", use_container_width=True):
            _go("Scenario stress tests")
    with col2:
        if st.button("📊 Compare alternatives", use_container_width=True):
            _go("Comparison View")
    _footer()


def render_scenarios() -> None:
    st.title("🧪 Scenario stress tests")
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
        trade_rows.append({
            "Alternative": f"Alt {position}: {' → '.join(plan.crop_names)}",
            "Composite score": plan.composite_score,
            "Status": plan.status.replace("_", " "),
            "Positive factors": len(plan.positive_factors),
            "Trade-offs": len(plan.tradeoffs),
            "Uncertainty warnings": len(plan.uncertainty_warnings),
        })
    st.dataframe(
        pd.DataFrame(trade_rows).style.format({"Composite score": "{:.3f}"}, na_rep="N/A"),
        hide_index=True, use_container_width=True,
    )

    st.info("**You retain full control** over the final choice. FieldShift shows all trade-offs but does not select a winner.", icon="ℹ️")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚖️ Change priorities and recalculate", use_container_width=True):
            _go("Farmer Priorities")
    with col2:
        if st.button("🧪 Run scenario stress tests", use_container_width=True):
            _go("Scenario stress tests")
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
            ("Not estimated", "NPK, soil pH, organic carbon, yield, profit, nitrogen fixed, soil-carbon change", "No values are fabricated when evidence is absent."),
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
        "- `data/README.md` — crop-record schema and provenance."
    )
    st.caption("Optional GPM, MODIS, SMAP/NASA-USDA soil moisture and local economics are documented as later extensions, not required inputs to this interface.")
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
        PAGES[7]: render_comparison,
        PAGES[8]: render_methods,
    }
    dispatch[st.session_state["page"]]()
