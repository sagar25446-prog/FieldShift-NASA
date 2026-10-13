"""ISRIC SoilGrids v2.0 soil-property estimates and soil source precedence.

SoilGrids values are *modelled predictions* on a 250 m global grid. They are
not soil tests and do not describe exact field-level conditions. This module

- retrieves a small, targeted point query from the SoilGrids REST API (beta),
- keeps every value with its unit, depth interval, quantiles and uncertainty,
- never mixes depth intervals or sources without saying so, and
- resolves which soil value the planner uses: a farmer/laboratory entry always
  overrides an estimate, and an estimate is used only where its property and
  uncertainty make that appropriate.

Access-method notes (verified 2026-10-13, see docs/SOIL_DATA.md):
ISRIC describes the REST API as a beta service without uptime guarantees,
asks users to stay within 5 calls per minute, and has posted that the API is
"temporarily paused" because of issues. Live queries still answered during
development, but callers must treat failure as a normal outcome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from time import monotonic
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


SOILGRIDS_QUERY_ENDPOINT = "https://rest.isric.org/soilgrids/v2.0/properties/query"
SOILGRIDS_DOCUMENTATION_URL = "https://www.isric.org/explore/soilgrids"
SOILGRIDS_UNITS_URL = "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html"
SOILGRIDS_ACCESS_URL = "https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html"
SOILGRIDS_LICENCE = "CC BY 4.0 (ISRIC — World Soil Information)"
SOILGRIDS_RESOLUTION = (
    "250 m global grid (SoilGrids 2.0). A point query returns the predicted value for the grid cell, "
    "which can differ from any individual field inside it."
)
SOILGRIDS_FAIR_USE = "ISRIC fair-use policy for the REST API: at most 5 calls per minute."

SOILGRIDS_PROPERTIES = ("clay", "sand", "silt", "soc", "phh2o", "nitrogen")
SOILGRIDS_DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
SOILGRIDS_VALUES = ("mean", "Q0.05", "Q0.5", "Q0.95", "uncertainty")

# Conventional ("target") units documented by ISRIC after dividing by d_factor.
EXPECTED_TARGET_UNITS = {
    "clay": "%",
    "sand": "%",
    "silt": "%",
    "soc": "g/kg",
    "phh2o": "-",
    "nitrogen": "g/kg",
}
PROPERTY_LABELS = {
    "clay": "Clay",
    "sand": "Sand",
    "silt": "Silt",
    "soc": "Soil organic carbon",
    "phh2o": "pH (water)",
    "nitrogen": "Total nitrogen",
}

# The single depth used whenever an estimate feeds the planner. FAO/HWSD
# topsoil texture groups are defined for 0–30 cm, which is also the union of
# the first three SoilGrids standard intervals.
MODEL_DEPTH_LABEL = "0-30cm"
MODEL_DEPTH_TOP_CM = 0
MODEL_DEPTH_BOTTOM_CM = 30

# FAO / HWSD three-class topsoil texture groups (0–30 cm) and the FieldShift
# terms used by the PAU-derived soil-context checks.
TEXTURE_GROUP_SOURCE_URL = "https://wesr-search.unep.org/ckan/dataset/mapx-topsoil-textural-class"
TEXTURE_GROUP_TO_FIELDSHIFT = {"coarse": "light", "medium": "medium", "fine": "heavy"}

ESTIMATE_LABEL = "Estimated from SoilGrids"
SOURCE_LABELS = {
    "laboratory": "Laboratory soil test (farmer-entered)",
    "farmer_observation": "Farmer observation",
    "unspecified": "Farmer-entered (basis not stated)",
    "illustrative": "Illustrative demonstration input — not measured",
    "soilgrids_estimate": ESTIMATE_LABEL,
    "unknown": "Unknown",
}
MANUAL_SOURCE_TYPES = ("laboratory", "farmer_observation", "unspecified", "illustrative")


class SoilGridsError(RuntimeError):
    """Base error for a SoilGrids request that cannot produce trustworthy estimates."""


class SoilGridsValidationError(SoilGridsError):
    """Raised before an invalid request is sent."""


class SoilGridsNetworkError(SoilGridsError):
    """Timeouts, connection failures and HTTP errors."""


class SoilGridsRateLimitError(SoilGridsError):
    """The request would exceed, or did exceed, ISRIC's fair-use limit."""


class SoilGridsResponseError(SoilGridsError):
    """A response that does not match the documented schema or units."""


@dataclass(frozen=True)
class SoilGridsLayerValue:
    """One property at one standard depth interval, in conventional units."""

    property_name: str
    depth_label: str
    top_cm: int
    bottom_cm: int
    unit: str
    mapped_unit: str
    d_factor: float
    mean: float | None
    q05: float | None
    q50: float | None
    q95: float | None
    uncertainty_ratio: float | None  # (Q0.95 − Q0.05) / Q0.50, unitless

    @property
    def label(self) -> str:
        return PROPERTY_LABELS.get(self.property_name, self.property_name)


@dataclass(frozen=True)
class SoilGridsEstimate:
    """A parsed SoilGrids point query with the provenance needed to interpret it."""

    latitude: float
    longitude: float
    returned_longitude: float | None
    returned_latitude: float | None
    source_url: str
    retrieved_at_utc: str
    query_time_s: float | None
    layers: Mapping[str, Mapping[str, SoilGridsLayerValue]]
    resolution: str = SOILGRIDS_RESOLUTION
    licence: str = SOILGRIDS_LICENCE
    documentation_url: str = SOILGRIDS_DOCUMENTATION_URL
    label: str = ESTIMATE_LABEL

    def value(self, property_name: str, depth_label: str) -> SoilGridsLayerValue | None:
        return self.layers.get(property_name, {}).get(depth_label)

    @property
    def has_any_value(self) -> bool:
        return any(item.mean is not None for depths in self.layers.values() for item in depths.values())

    @property
    def missing(self) -> tuple[str, ...]:
        """Requested property/depth combinations with no predicted mean."""
        gaps = []
        for name in SOILGRIDS_PROPERTIES:
            for depth in SOILGRIDS_DEPTHS:
                item = self.value(name, depth)
                if item is None or item.mean is None:
                    gaps.append(f"{name} {depth}")
        return tuple(gaps)


@dataclass(frozen=True)
class DepthAggregate:
    """Thickness-weighted 0–30 cm mean plus a conservative quantile envelope."""

    property_name: str
    unit: str
    depth_label: str
    mean: float
    envelope_low: float | None
    envelope_high: float | None
    component_depths: tuple[str, ...]
    method: str


@dataclass(frozen=True)
class TextureAssessment:
    """FAO/HWSD texture group for SoilGrids 0–30 cm sand and clay."""

    group_at_mean: str | None
    robust_group: str | None
    fieldshift_texture: str | None  # light / medium / heavy, only when robust
    explanation: str


# ─────────────────────────────── retrieval ───────────────────────────────

Transport = Callable[[str, float], bytes]


def _default_transport(url: str, timeout_seconds: float) -> bytes:
    with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS endpoint
        return response.read()


class SoilGridsClient:
    """Targeted SoilGrids point queries with caching and a fair-use guard.

    SoilGrids maps are static releases, so successful results are cached for
    the life of the process. A live call is refused when the previous one was
    less than ``min_interval_seconds`` ago, keeping the app within ISRIC's
    5-calls-per-minute policy.
    """

    def __init__(
        self,
        timeout_seconds: float = 60.0,
        min_interval_seconds: float = 12.0,
        transport: Transport = _default_transport,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.min_interval_seconds = min_interval_seconds
        self._transport = transport
        self._clock = clock
        self._last_call: float | None = None
        self._cache: dict[tuple[float, float], SoilGridsEstimate] = {}

    @staticmethod
    def build_url(latitude: float, longitude: float) -> str:
        """Return the exact public request URL recorded in provenance."""
        if not -90 <= latitude <= 90:
            raise SoilGridsValidationError("Latitude must be between -90 and 90 degrees.")
        if not -180 <= longitude <= 180:
            raise SoilGridsValidationError("Longitude must be between -180 and 180 degrees.")
        query = [("lon", round(longitude, 5)), ("lat", round(latitude, 5))]
        query += [("property", name) for name in SOILGRIDS_PROPERTIES]
        query += [("depth", depth) for depth in SOILGRIDS_DEPTHS]
        query += [("value", value) for value in SOILGRIDS_VALUES]
        return f"{SOILGRIDS_QUERY_ENDPOINT}?{urlencode(query)}"

    def fetch(self, latitude: float, longitude: float, force_refresh: bool = False) -> SoilGridsEstimate:
        """Retrieve and parse one point; raises a ``SoilGridsError`` subclass on failure."""
        key = (round(latitude, 5), round(longitude, 5))
        if not force_refresh and key in self._cache:
            return self._cache[key]
        url = self.build_url(latitude, longitude)
        now = self._clock()
        if self._last_call is not None and now - self._last_call < self.min_interval_seconds:
            wait = self.min_interval_seconds - (now - self._last_call)
            raise SoilGridsRateLimitError(f"SoilGrids asks users to stay within 5 requests per minute. Wait about {wait:.0f} s and retry.")
        self._last_call = now
        try:
            raw = self._transport(url, self.timeout_seconds)
        except HTTPError as error:
            if error.code == 429:
                raise SoilGridsRateLimitError("SoilGrids reported too many requests (HTTP 429). Wait a minute and retry.") from error
            raise SoilGridsNetworkError(f"SoilGrids returned HTTP {error.code}. The beta REST service may be paused or busy.") from error
        except (URLError, TimeoutError, OSError) as error:
            raise SoilGridsNetworkError("Could not reach SoilGrids or it timed out. The beta REST service may be paused or busy.") from error
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SoilGridsResponseError("SoilGrids returned a response that is not valid JSON.") from error
        estimate = parse_soilgrids_response(
            payload, latitude, longitude, url, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        self._cache[key] = estimate
        return estimate


def _scaled(raw: object, factor: float) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise SoilGridsResponseError(f"SoilGrids returned a non-numeric value: {raw!r}")
    return float(raw) / factor


def parse_soilgrids_response(
    payload: object,
    latitude: float,
    longitude: float,
    source_url: str,
    retrieved_at_utc: str,
) -> SoilGridsEstimate:
    """Parse the documented ``properties/query`` GeoJSON without inventing values.

    Mapped integers are divided by the layer's ``d_factor``. The uncertainty
    value is ISRIC's (Q0.95 − Q0.05)/Q0.50 ratio stored ×10, so it is divided
    by 10. ``null`` stays ``None``.
    """
    if not isinstance(payload, dict):
        raise SoilGridsResponseError("SoilGrids response must be a JSON object.")
    try:
        layers_raw = payload["properties"]["layers"]
    except (KeyError, TypeError) as error:
        raise SoilGridsResponseError("SoilGrids response has no properties.layers list.") from error
    if not isinstance(layers_raw, list):
        raise SoilGridsResponseError("SoilGrids properties.layers is not a list.")

    layers: dict[str, dict[str, SoilGridsLayerValue]] = {}
    for layer in layers_raw:
        try:
            name = str(layer["name"])
            unit_info = layer["unit_measure"]
            factor = float(unit_info["d_factor"])
            target_unit = str(unit_info["target_units"])
            mapped_unit = str(unit_info.get("mapped_units", ""))
            depths = layer["depths"]
        except (KeyError, TypeError, ValueError) as error:
            raise SoilGridsResponseError("A SoilGrids layer is missing its name, unit_measure or depths.") from error
        if name not in EXPECTED_TARGET_UNITS:
            continue  # only properties FieldShift requested and understands
        if factor <= 0:
            raise SoilGridsResponseError(f"SoilGrids {name} has an invalid d_factor {factor}.")
        if target_unit != EXPECTED_TARGET_UNITS[name]:
            raise SoilGridsResponseError(
                f"SoilGrids {name} is reported in '{target_unit}', not the documented '{EXPECTED_TARGET_UNITS[name]}'. "
                "Refusing to convert an unexpected unit."
            )
        for depth in depths:
            try:
                label = str(depth["label"])
                top = int(depth["range"]["top_depth"])
                bottom = int(depth["range"]["bottom_depth"])
                values = depth["values"]
            except (KeyError, TypeError, ValueError) as error:
                raise SoilGridsResponseError(f"SoilGrids {name} depth entry is malformed.") from error
            if bottom <= top:
                raise SoilGridsResponseError(f"SoilGrids {name} {label} has an invalid depth range.")
            layers.setdefault(name, {})[label] = SoilGridsLayerValue(
                property_name=name,
                depth_label=label,
                top_cm=top,
                bottom_cm=bottom,
                unit=target_unit,
                mapped_unit=mapped_unit,
                d_factor=factor,
                mean=_scaled(values.get("mean"), factor),
                q05=_scaled(values.get("Q0.05"), factor),
                q50=_scaled(values.get("Q0.5"), factor),
                q95=_scaled(values.get("Q0.95"), factor),
                uncertainty_ratio=_scaled(values.get("uncertainty"), 10.0),
            )

    returned_lon = returned_lat = None
    geometry = payload.get("geometry")
    if isinstance(geometry, dict) and isinstance(geometry.get("coordinates"), list) and len(geometry["coordinates"]) >= 2:
        returned_lon, returned_lat = float(geometry["coordinates"][0]), float(geometry["coordinates"][1])
    query_time = payload.get("query_time_s")
    return SoilGridsEstimate(
        latitude=latitude,
        longitude=longitude,
        returned_longitude=returned_lon,
        returned_latitude=returned_lat,
        source_url=source_url,
        retrieved_at_utc=retrieved_at_utc,
        query_time_s=float(query_time) if isinstance(query_time, (int, float)) else None,
        layers=layers,
    )


# ─────────────────────────── depth and texture ───────────────────────────

def aggregate_topsoil(estimate: SoilGridsEstimate | None, property_name: str) -> DepthAggregate | None:
    """Thickness-weighted 0–30 cm mean of the 0–5, 5–15 and 15–30 cm means.

    Returns ``None`` when any interval mean is missing, so a partial depth is
    never presented as 0–30 cm. Quantiles cannot be averaged, so the envelope
    is the lowest Q0.05 and highest Q0.95 across the three intervals: a
    conservative range, not a statistical prediction interval.
    """
    if estimate is None:
        return None
    items = [estimate.value(property_name, depth) for depth in SOILGRIDS_DEPTHS]
    if any(item is None or item.mean is None for item in items):
        return None
    thickness = [item.bottom_cm - item.top_cm for item in items]  # type: ignore[union-attr]
    if sum(thickness) != MODEL_DEPTH_BOTTOM_CM - MODEL_DEPTH_TOP_CM:
        return None
    mean = sum(item.mean * width for item, width in zip(items, thickness)) / sum(thickness)  # type: ignore[union-attr, operator]
    lows = [item.q05 for item in items]  # type: ignore[union-attr]
    highs = [item.q95 for item in items]  # type: ignore[union-attr]
    complete = all(value is not None for value in lows + highs)
    return DepthAggregate(
        property_name=property_name,
        unit=items[0].unit,  # type: ignore[union-attr]
        depth_label=MODEL_DEPTH_LABEL,
        mean=mean,
        envelope_low=min(lows) if complete else None,  # type: ignore[type-var]
        envelope_high=max(highs) if complete else None,  # type: ignore[type-var]
        component_depths=SOILGRIDS_DEPTHS,
        method="Thickness-weighted mean of SoilGrids 0–5, 5–15 and 15–30 cm predicted means; range = lowest Q0.05 to highest Q0.95 across those intervals.",
    )


def fao_texture_group(sand_percent: float, clay_percent: float) -> str:
    """FAO/HWSD three-class topsoil texture group (defined for 0–30 cm)."""
    if clay_percent > 35:
        return "fine"
    if clay_percent < 18 and sand_percent > 65:
        return "coarse"
    return "medium"


def _robust_group(sand: DepthAggregate, clay: DepthAggregate) -> str | None:
    """Group that holds for every sand/clay pair inside the envelope box, else ``None``."""
    if None in (sand.envelope_low, sand.envelope_high, clay.envelope_low, clay.envelope_high):
        return None
    if clay.envelope_low > 35:  # type: ignore[operator]
        return "fine"
    if clay.envelope_high < 18 and sand.envelope_low > 65:  # type: ignore[operator]
        return "coarse"
    if clay.envelope_high < 35 and (clay.envelope_low > 18 or sand.envelope_high < 65):  # type: ignore[operator]
        return "medium"
    return None


def assess_texture(estimate: SoilGridsEstimate | None) -> TextureAssessment:
    """Return a texture group only when SoilGrids uncertainty cannot change it."""
    sand, clay = aggregate_topsoil(estimate, "sand"), aggregate_topsoil(estimate, "clay")
    if sand is None or clay is None:
        return TextureAssessment(None, None, None, "SoilGrids sand or clay is missing for at least one 0–30 cm interval; texture stays unknown.")
    at_mean = fao_texture_group(sand.mean, clay.mean)
    robust = _robust_group(sand, clay)
    if robust is None:
        return TextureAssessment(
            at_mean,
            None,
            None,
            f"The SoilGrids mean suggests a '{at_mean}' texture group, but the 90% ranges "
            f"(clay {clay.envelope_low:.0f}–{clay.envelope_high:.0f}%, sand {sand.envelope_low:.0f}–{sand.envelope_high:.0f}%) "
            "cross more than one group, so it is not used for crop soil checks."
            if clay.envelope_low is not None and sand.envelope_low is not None
            else f"The SoilGrids mean suggests a '{at_mean}' texture group, but no uncertainty range was returned, so it is not used for crop soil checks.",
        )
    return TextureAssessment(
        at_mean,
        robust,
        TEXTURE_GROUP_TO_FIELDSHIFT[robust],
        f"The whole SoilGrids 0–30 cm range falls in the FAO '{robust}' group "
        f"(treated as '{TEXTURE_GROUP_TO_FIELDSHIFT[robust]}' texture).",
    )


# ─────────────────────────── source precedence ───────────────────────────

@dataclass(frozen=True)
class ManualSoilEntry:
    """Soil values typed by the farmer. ``None`` means not entered."""

    source_type: str = "unspecified"
    texture: str | None = None
    ph: float | None = None
    organic_carbon_percent: float | None = None
    total_nitrogen_g_kg: float | None = None
    electrical_conductivity_ds_m: float | None = None
    sample_depth: str | None = None
    reference: str | None = None

    def __post_init__(self) -> None:
        if self.source_type not in MANUAL_SOURCE_TYPES:
            raise ValueError(f"Manual soil source must be one of {MANUAL_SOURCE_TYPES}.")


@dataclass(frozen=True)
class ResolvedSoilValue:
    """The one value the planner uses for a property, and where it came from."""

    key: str
    label: str
    value: float | str | None
    unit: str
    source_type: str
    depth: str | None
    used_in_model: bool
    how_used: str
    low: float | None = None
    high: float | None = None
    note: str = ""
    not_used_alternative: str | None = None

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS[self.source_type]


@dataclass(frozen=True)
class ResolvedSoil:
    values: Mapping[str, ResolvedSoilValue]
    estimate_available: bool
    texture_assessment: TextureAssessment | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __getitem__(self, key: str) -> ResolvedSoilValue:
        return self.values[key]


def _manual_value(key: str, label: str, value: object, unit: str, entry: ManualSoilEntry, used: bool, how: str, alternative: str | None) -> ResolvedSoilValue:
    return ResolvedSoilValue(
        key=key, label=label, value=value, unit=unit, source_type=entry.source_type,
        depth=entry.sample_depth or "Not stated", used_in_model=used, how_used=how,
        note="Farmer-entered value takes precedence over any estimate.", not_used_alternative=alternative,
    )


def _unknown(key: str, label: str, unit: str, how: str, note: str) -> ResolvedSoilValue:
    return ResolvedSoilValue(key=key, label=label, value=None, unit=unit, source_type="unknown", depth=None, used_in_model=False, how_used=how, note=note)


def resolve_soil_values(entry: ManualSoilEntry, estimate: SoilGridsEstimate | None) -> ResolvedSoil:
    """Apply precedence: farmer/lab entry > appropriate SoilGrids estimate > unknown.

    Estimates are used only where appropriate:
    - texture: only if the whole 0–30 cm uncertainty box sits in one FAO group;
    - organic carbon: as the starting value for the *simplified* SOC-direction
      model, carrying its 0–30 cm depth and range;
    - pH and total nitrogen: shown as context only, because the crop catalogue
      has no source-backed pH or nitrogen threshold;
    - EC, waterlogging, drainage and alkalinity are never estimated.
    """
    has_estimate = estimate is not None and estimate.has_any_value
    texture = assess_texture(estimate) if has_estimate else None
    values: dict[str, ResolvedSoilValue] = {}

    # Texture — used by PAU soil-context checks (rapeseed/mustard, pearl millet).
    texture_how = "Used by documented best-soil-context checks (rapeseed/mustard, pearl millet); never a hard rejection."
    texture_alt = None
    if texture and texture.group_at_mean:
        texture_alt = f"SoilGrids 0–30 cm suggests FAO '{texture.group_at_mean}' group ({texture.explanation})"
    if entry.texture:
        values["texture"] = _manual_value("texture", "Texture", entry.texture, "class", entry, True, texture_how, texture_alt)
    elif texture and texture.fieldshift_texture:
        values["texture"] = ResolvedSoilValue(
            key="texture", label="Texture", value=texture.fieldshift_texture, unit="class",
            source_type="soilgrids_estimate", depth=MODEL_DEPTH_LABEL, used_in_model=True, how_used=texture_how,
            note=texture.explanation,
        )
    else:
        values["texture"] = _unknown("texture", "Texture", "class", texture_how, texture.explanation if texture else "Not entered and no usable estimate.")

    # Organic carbon — simplified SOC-direction model only.
    soc_how = "Starting value for the simplified, uncalibrated SOC-direction model."
    soc = aggregate_topsoil(estimate, "soc") if has_estimate else None
    soc_alt = None
    if soc is not None:
        soc_alt = f"SoilGrids 0–30 cm estimate {soc.mean / 10:.2f}% (shown for comparison, not used)"
    if entry.organic_carbon_percent is not None:
        values["organic_carbon"] = _manual_value("organic_carbon", "Organic carbon", entry.organic_carbon_percent, "%", entry, True, soc_how, soc_alt)
    elif soc is not None:
        values["organic_carbon"] = ResolvedSoilValue(
            key="organic_carbon", label="Organic carbon", value=soc.mean / 10.0, unit="%",
            source_type="soilgrids_estimate", depth=MODEL_DEPTH_LABEL, used_in_model=True, how_used=soc_how,
            low=None if soc.envelope_low is None else soc.envelope_low / 10.0,
            high=None if soc.envelope_high is None else soc.envelope_high / 10.0,
            note=(
                "Converted from g/kg to % (÷10). SoilGrids organic carbon is harmonised from several laboratory methods; "
                "Indian soil-test reports often use Walkley–Black, so values are not directly interchangeable."
            ),
        )
    else:
        values["organic_carbon"] = _unknown("organic_carbon", "Organic carbon", "%", soc_how, "Not entered and no complete 0–30 cm estimate.")

    # pH and total nitrogen — context only.
    for key, label, unit, manual, prop in (
        ("ph", "pH", "pH units", entry.ph, "phh2o"),
        ("total_nitrogen", "Total nitrogen", "g/kg", entry.total_nitrogen_g_kg, "nitrogen"),
    ):
        how = "Shown for context only: the crop catalogue has no source-backed threshold for this property."
        aggregate = aggregate_topsoil(estimate, prop) if has_estimate else None
        alt = None if aggregate is None else f"SoilGrids 0–30 cm estimate {aggregate.mean:.2f} {unit} (shown for comparison)"
        if manual is not None:
            values[key] = _manual_value(key, label, manual, unit, entry, False, how, alt)
        elif aggregate is not None:
            values[key] = ResolvedSoilValue(
                key=key, label=label, value=aggregate.mean, unit=unit, source_type="soilgrids_estimate",
                depth=MODEL_DEPTH_LABEL, used_in_model=False, how_used=how,
                low=aggregate.envelope_low, high=aggregate.envelope_high,
                note="Total nitrogen is not the same as Soil Health Card 'available N' (kg/ha)." if key == "total_nitrogen" else "",
            )
        else:
            values[key] = _unknown(key, label, unit, how, "Not entered and no complete 0–30 cm estimate.")

    ec_how = "Shown for context only; SoilGrids does not estimate EC."
    if entry.electrical_conductivity_ds_m is not None:
        values["electrical_conductivity"] = _manual_value("electrical_conductivity", "Electrical conductivity", entry.electrical_conductivity_ds_m, "dS/m", entry, False, ec_how, None)
    else:
        values["electrical_conductivity"] = _unknown("electrical_conductivity", "Electrical conductivity", "dS/m", ec_how, "Laboratory measurement only.")

    notes = [
        "Waterlogging, drainage and highly deteriorated alkaline condition come only from the farmer; SoilGrids is never used for these hard constraints.",
    ]
    if estimate is not None and not estimate.has_any_value:
        notes.append("SoilGrids returned no prediction for this location; soil properties remain unknown unless entered.")
    return ResolvedSoil(values=values, estimate_available=has_estimate, texture_assessment=texture, notes=tuple(notes))
