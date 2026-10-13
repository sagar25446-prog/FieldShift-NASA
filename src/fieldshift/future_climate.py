"""Future-climate scenario comparison from NASA NEX-GDDP-CMIP6.

Climate projections describe a range of plausible 20-year climates under an
emissions pathway, as simulated by individual climate models. They are not
weather forecasts for any particular year, and models disagree. FieldShift
therefore never compares a projection with observations directly. Each future
period is compared with **the same model's** historical simulation, for the
same 0.25° grid cell, using the same FAO-56 and EcoCrop calculations:

    change = model(SSP, 2041–2060) − model(historical, 1995–2014)

Results are summarised across models as the median and the range. NASA POWER
observations remain a separate reference, and the user-configured
hypothetical stress tests (``scenarios.py``) are a different thing again.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from statistics import median
from typing import Mapping, Sequence

import pandas as pd

from .growing_season import crop_season_slices


DEMO_EXTRACT_DIR = Path(__file__).resolve().parents[2] / "data" / "nex_gddp_cmip6_demo_farm"
REFERENCE_EXPERIMENT = "historical"
SCENARIO_LABELS = {
    "historical": "Model historical simulation (1995–2014)",
    "ssp245": "SSP2-4.5 — intermediate emissions (2041–2060)",
    "ssp585": "SSP5-8.5 — very high emissions (2041–2060)",
}
SHORT_LABELS = {"historical": "Historical (models)", "ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}

# Source units (as recorded from each file's attributes) → FieldShift/POWER-style columns.
# Only tasmax, tasmin and pr are extracted (see docs/FUTURE_CLIMATE.md); radiation,
# humidity and wind use FAO-56 missing-data procedures (Eq. 50, Eq. 48, 2 m/s)
# identically for the historical and future periods.
EXPECTED_UNITS = {"tasmax": "K", "tasmin": "K", "pr": "kg m-2 s-1"}


class ProjectionDataError(ValueError):
    """The scenario extract is missing, inconsistent or uses unexpected units."""


@dataclass(frozen=True)
class ProjectionRecord:
    model: str
    experiment: str
    years: tuple[int, int]
    variant: str
    grid_cell: tuple[float, float]
    licence: str | None
    dataset_version: str | None
    calendar: str | None
    frame: pd.DataFrame  # POWER-style columns and units


@dataclass(frozen=True)
class ProjectionExtract:
    requested_latitude: float
    requested_longitude: float
    grid_cell: tuple[float, float]
    models: tuple[str, ...]
    experiments: Mapping[str, tuple[int, int]]
    records: Mapping[tuple[str, str], ProjectionRecord]
    retrieved_utc: str
    citation: str
    documentation: str
    technical_note: str

    def covers(self, latitude: float, longitude: float) -> bool:
        """True if the point lies in the extract's 0.25° grid cell."""
        lat, lon = self.grid_cell
        return abs(latitude - lat) <= 0.125 and abs((longitude % 360) - (lon % 360)) <= 0.125


def convert_units(raw: pd.DataFrame, units: Mapping[str, str]) -> pd.DataFrame:
    """Convert NEX-GDDP-CMIP6 variables to the units used by the engine.

    Refuses to convert a variable whose source unit is not the documented one.
    """
    for variable, expected in EXPECTED_UNITS.items():
        if variable not in raw.columns:
            raise ProjectionDataError(f"Variable {variable} is missing from the extract.")
        if units.get(variable) != expected:
            raise ProjectionDataError(f"{variable} is in '{units.get(variable)}', expected '{expected}'; refusing to convert.")
    frame = pd.DataFrame(index=raw.index)
    frame["T2M_MAX"] = raw["tasmax"] - 273.15
    frame["T2M_MIN"] = raw["tasmin"] - 273.15
    frame["T2M"] = (frame["T2M_MAX"] + frame["T2M_MIN"]) / 2.0  # FAO-56 Eq. 9 daily mean
    frame["PRECTOTCORR"] = raw["pr"] * 86400.0  # kg m-2 s-1 → mm/day
    if (frame["T2M_MAX"] < frame["T2M_MIN"]).any():
        raise ProjectionDataError("Daily maximum temperature below minimum in the extract.")
    frame.index.name = "date"
    return frame


def load_extract(directory: Path | str | None = None) -> ProjectionExtract:
    """Load and validate a scenario extract written by ``scripts/extract_nex_gddp_cmip6.py``."""
    folder = Path(directory or DEMO_EXTRACT_DIR)
    meta_path = folder / "metadata.json"
    if not meta_path.exists():
        raise ProjectionDataError(f"No projection extract at {folder}.")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    experiments = {name: tuple(years) for name, years in meta["experiments"].items()}
    if REFERENCE_EXPERIMENT not in experiments:
        raise ProjectionDataError("The extract has no historical reference experiment.")
    future_periods = {years for name, years in experiments.items() if name != REFERENCE_EXPERIMENT}
    if len(future_periods) != 1:
        raise ProjectionDataError("All future scenarios must cover the same period.")
    records: dict[tuple[str, str], ProjectionRecord] = {}
    cells: set[tuple[float, float]] = set()
    for model, model_meta in meta["models"].items():
        for experiment, years in experiments.items():
            info = model_meta["experiments"].get(experiment)
            if info is None:
                raise ProjectionDataError(f"{model} is missing experiment {experiment}.")
            if tuple(info["years"]) != years:
                raise ProjectionDataError(f"{model} {experiment} covers {info['years']}, not {list(years)}.")
            path = folder / f"{model}_{experiment}_{years[0]}-{years[1]}.csv.gz"
            if not path.exists():
                path = path.with_suffix("")  # uncompressed fallback
            raw = pd.read_csv(path, parse_dates=["date"], index_col="date")
            frame = convert_units(raw, info["units"])
            first, last = frame.index.min().year, frame.index.max().year
            if (first, last) != years:
                raise ProjectionDataError(f"{model} {experiment} data span {first}–{last}, not {years[0]}–{years[1]}.")
            cell = tuple(info["grid_cell_centre"])
            cells.add(cell)  # type: ignore[arg-type]
            records[(model, experiment)] = ProjectionRecord(
                model=model, experiment=experiment, years=years, variant=info["variant"],
                grid_cell=cell, licence=model_meta.get("licence"),  # type: ignore[arg-type]
                dataset_version=info.get("dataset_version"), calendar=model_meta.get("calendar"), frame=frame,
            )
    if len(cells) != 1:
        raise ProjectionDataError(f"Records come from different grid cells: {sorted(cells)}.")
    return ProjectionExtract(
        requested_latitude=float(meta["requested_latitude"]),
        requested_longitude=float(meta["requested_longitude"]),
        grid_cell=cells.pop(),
        models=tuple(meta["models"]),
        experiments=experiments,
        records=records,
        retrieved_utc=str(meta.get("retrieval_finished_utc", meta.get("retrieval_started_utc"))),
        citation=meta["citation"],
        documentation=meta["documentation"],
        technical_note=meta["technical_note"],
    )


# ─────────────────────────── climate indicators ───────────────────────────

HEAT_DAY_THRESHOLD_C = 35.0  # same default as the historical climate-trend module


@dataclass(frozen=True)
class SeasonClimate:
    mean_temperature_c: float
    mean_tmax_c: float
    precipitation_mm: float
    heat_days: float  # days with Tmax ≥ 35 °C, per season
    seasons: int


def season_climate(frame: pd.DataFrame, season_id: str) -> SeasonClimate | None:
    """Per-season means over every complete season occurrence in ``frame``."""
    slices = crop_season_slices(frame, season_id, None, required_columns=("T2M", "T2M_MAX", "PRECTOTCORR"))
    complete = [occ for occ in slices.occurrences if not occ.composite]
    if not complete:
        return None
    means = [o.frame["T2M"].mean() for o in complete]
    tmax = [o.frame["T2M_MAX"].mean() for o in complete]
    rain = [o.frame["PRECTOTCORR"].sum() for o in complete]
    heat = [(o.frame["T2M_MAX"] >= HEAT_DAY_THRESHOLD_C).sum() for o in complete]
    n = len(complete)
    return SeasonClimate(sum(means) / n, sum(tmax) / n, sum(rain) / n, float(sum(heat)) / n, n)


@dataclass(frozen=True)
class Spread:
    """Median and range across models of a change (future − same model's historical)."""

    median: float
    low: float
    high: float
    per_model: Mapping[str, float]

    @classmethod
    def of(cls, values: Mapping[str, float]) -> "Spread":
        data = list(values.values())
        return cls(median(data), min(data), max(data), dict(values))

    @property
    def agreement(self) -> str:
        """How many models agree on the sign of the change."""
        positive = sum(1 for v in self.per_model.values() if v > 0)
        negative = sum(1 for v in self.per_model.values() if v < 0)
        total = len(self.per_model)
        if positive == total:
            return f"all {total} models show an increase"
        if negative == total:
            return f"all {total} models show a decrease"
        return f"models disagree on direction ({positive} up, {negative} down)"


def climate_changes(extract: ProjectionExtract, season_id: str) -> dict[str, dict[str, Spread]]:
    """Seasonal climate change per scenario: {scenario: {indicator: Spread}}."""
    result: dict[str, dict[str, Spread]] = {}
    for scenario in (e for e in extract.experiments if e != REFERENCE_EXPERIMENT):
        changes: dict[str, dict[str, float]] = {"mean_temperature_c": {}, "mean_tmax_c": {}, "precipitation_pct": {}, "heat_days": {}}
        for model in extract.models:
            base = season_climate(extract.records[(model, REFERENCE_EXPERIMENT)].frame, season_id)
            future = season_climate(extract.records[(model, scenario)].frame, season_id)
            if base is None or future is None:
                continue
            changes["mean_temperature_c"][model] = future.mean_temperature_c - base.mean_temperature_c
            changes["mean_tmax_c"][model] = future.mean_tmax_c - base.mean_tmax_c
            changes["heat_days"][model] = future.heat_days - base.heat_days
            if base.precipitation_mm > 0:
                changes["precipitation_pct"][model] = 100.0 * (future.precipitation_mm - base.precipitation_mm) / base.precipitation_mm
        result[scenario] = {name: Spread.of(values) for name, values in changes.items() if values}
    return result


# ─────────────────────────── rotation comparison ───────────────────────────

PLAN_INDICATORS = ("water_suitability", "climate_suitability", "composite", "total_etc_mm", "net_irrigation_mm", "heat_stress_days")
INDICATOR_LABELS = {
    "water_suitability": "Water score (0–1)",
    "climate_suitability": "Climate score (0–1)",
    "composite": "Composite score (0–1)",
    "total_etc_mm": "Crop water demand ETc (mm per rotation)",
    "net_irrigation_mm": "Irrigation need beyond rain (mm per rotation)",
    "heat_stress_days": "Heat-stress days per rotation",
}


def plan_indicators(plan: object) -> dict[str, float | None]:
    wb = getattr(plan, "water_balance", None)
    ca = getattr(plan, "climate_assessment", None)
    heat = None
    if ca is not None and getattr(ca, "crops", ()):
        heat = float(sum(c.heat_stress_days for c in ca.crops))
    return {
        "water_suitability": plan.metrics["water_suitability"].score,  # type: ignore[attr-defined]
        "climate_suitability": plan.metrics["climate_suitability"].score,  # type: ignore[attr-defined]
        "composite": plan.composite_score,  # type: ignore[attr-defined]
        "total_etc_mm": getattr(wb, "total_etc_mm", None),
        "net_irrigation_mm": getattr(wb, "total_net_irrigation_mm", None),
        "heat_stress_days": heat,
    }


@dataclass(frozen=True)
class PlanScenarioComparison:
    crop_ids: tuple[str, ...]
    absolute: Mapping[str, Mapping[str, Mapping[str, float | None]]]  # experiment → model → indicator → value
    changes: Mapping[str, Mapping[str, Spread]]  # scenario → indicator → Spread of (future − historical)
    hard_failures: Mapping[str, tuple[str, ...]]  # experiment → models where a hard constraint failed


def compare_plan(engine: object, crop_ids: Sequence[str], profile: object, extract: ProjectionExtract) -> PlanScenarioComparison:
    """Run the same plan, constraints and farmer weights through every model and period."""
    absolute: dict[str, dict[str, dict[str, float | None]]] = {}
    failures: dict[str, list[str]] = {}
    for experiment in extract.experiments:
        absolute[experiment] = {}
        for model in extract.models:
            scenario_profile = replace(
                profile,  # type: ignore[type-var]
                climate_data=extract.records[(model, experiment)].frame,
                climate_scenario=f"NEX-GDDP-CMIP6 {model} {SHORT_LABELS[experiment]}",
            )
            plan = engine.assess_sequence(tuple(crop_ids), scenario_profile)  # type: ignore[attr-defined]
            absolute[experiment][model] = plan_indicators(plan)
            if plan.status == "infeasible":
                failures.setdefault(experiment, []).append(model)
    changes: dict[str, dict[str, Spread]] = {}
    for scenario in (e for e in extract.experiments if e != REFERENCE_EXPERIMENT):
        changes[scenario] = {}
        for indicator in PLAN_INDICATORS:
            deltas = {
                model: absolute[scenario][model][indicator] - absolute[REFERENCE_EXPERIMENT][model][indicator]  # type: ignore[operator]
                for model in extract.models
                if absolute[scenario][model][indicator] is not None and absolute[REFERENCE_EXPERIMENT][model][indicator] is not None
            }
            if deltas:
                changes[scenario][indicator] = Spread.of(deltas)
    return PlanScenarioComparison(tuple(crop_ids), absolute, changes, {k: tuple(v) for k, v in failures.items()})


def ensemble_median(comparison: PlanScenarioComparison, experiment: str, indicator: str) -> float | None:
    values = [v[indicator] for v in comparison.absolute[experiment].values() if v[indicator] is not None]
    return median(values) if values else None


ASSUMPTIONS = (
    "Projections are 20-year climate statistics under an emissions pathway, not forecasts of any particular year's weather.",
    "Each future period is compared with the same model's historical simulation (1995–2014), on the same grid cell, with the same FAO-56 and EcoCrop calculations. Observations are never mixed into these comparisons.",
    "Periods follow the IPCC AR6 convention: reference 1995–2014 and mid-century 2041–2060.",
    "Five of the 35 NEX-GDDP-CMIP6 models were used (one per modelling centre, all with complete variables). They are not weighted by skill, and the full CMIP6 range is wider.",
    "Data are bias-corrected and downscaled to 0.25° (about 25 km). They are not field-level predictions. The BCSD method assumes present-day spatial patterns persist.",
    "Only daily maximum/minimum temperature and precipitation are used. FAO-56 reference evapotranspiration then estimates solar radiation from the temperature range (Eq. 50, kRs = 0.16), vapour pressure from Tmin (Eq. 48) and uses a 2 m/s wind, identically in every period, so projected changes in humidity, cloud and wind are not represented.",
    "Daily mean temperature is (Tmax + Tmin) / 2 (FAO-56 Eq. 9). GFDL-ESM4 uses a 365-day calendar (no 29 February).",
    "Crop calendars, crop coefficients, thresholds, the farmer's water budget and priorities are held fixed. Adaptation (sowing dates, varieties, irrigation changes) and CO₂ effects on crops are not modelled.",
)
