"""Small, deterministic, evidence-linked crop-rotation search engine.

This module does not predict yield, profit, nitrogen fixation, or soil-carbon change.
It only checks documented catalogue constraints and makes uncertainty explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Mapping


METRICS = ("water_suitability", "climate_suitability", "soil_related_potential", "rotation_diversity", "economic_potential")


class RotationInputError(ValueError):
    """Raised when the planner's input shape cannot be interpreted safely."""


@dataclass(frozen=True)
class SoilInformation:
    """Farmer/lab-provided soil information. ``None`` means not measured or unknown."""

    ph: float | None = None
    electrical_conductivity_ds_m: float | None = None
    organic_carbon_percent: float | None = None
    waterlogged: bool | None = None
    highly_deteriorated_alkaline: bool | None = None
    well_drained: bool | None = None
    texture: str | None = None
    source_description: str | None = None


@dataclass(frozen=True)
class ClimateContext:
    """Reference to available, retrieved climate context; no suitability threshold is implied."""

    source_url: str | None = None
    date_range: str | None = None
    available_parameters: tuple[str, ...] = ()


@dataclass(frozen=True)
class FarmProfile:
    """Inputs used by the rule engine for one planning run."""

    latitude: float
    longitude: float
    soil: SoilInformation
    climate: ClimateContext
    total_crop_water_budget_mm: float | None
    previous_crop_id: str | None
    blocked_crop_ids: frozenset[str] = frozenset()
    blocked_families: frozenset[str] = frozenset()
    priority_weights: Mapping[str, float] = field(default_factory=dict)
    number_of_seasons: int = 3
    start_season: str = "kharif"
    climate_scenario: str = "historical NASA POWER context"


@dataclass(frozen=True)
class FeasibilityCheck:
    """One transparent outcome from a hard or evidence-limited rule."""

    rule: str
    status: str  # pass, fail, unknown
    message: str
    source_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class MetricScore:
    """A normalised 0–1 score or an explicit unavailable metric."""

    score: float | None
    method: str
    warning: str | None = None


@dataclass(frozen=True)
class RotationPlan:
    """A candidate sequence and its evidence, metrics and uncertainty."""

    crop_ids: tuple[str, ...]
    crop_names: tuple[str, ...]
    seasons: tuple[str, ...]
    status: str
    checks: tuple[FeasibilityCheck, ...]
    metrics: Mapping[str, MetricScore]
    effective_weights: Mapping[str, float]
    composite_score: float | None
    positive_factors: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    uncertainty_warnings: tuple[str, ...]
    source_urls: tuple[str, ...]


@dataclass(frozen=True)
class PlanningResult:
    """Plans plus exclusions useful when the supported graph yields no result."""

    plans: tuple[RotationPlan, ...]
    exclusions: tuple[FeasibilityCheck, ...]
    message: str


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Validate non-negative preferences and normalise them to exactly one."""
    unknown = set(weights) - set(METRICS)
    if unknown:
        raise RotationInputError(f"Unknown priority metrics: {sorted(unknown)}")
    completed = {metric: float(weights.get(metric, 0.0)) for metric in METRICS}
    if any(value < 0 for value in completed.values()):
        raise RotationInputError("Priority weights cannot be negative.")
    total = sum(completed.values())
    if total <= 0:
        raise RotationInputError("At least one priority weight must be greater than zero.")
    return {metric: value / total for metric, value in completed.items()}


class RotationEngine:
    """Search the small, source-linked relationship graph with deterministic DFS."""

    def __init__(self, catalog_path: Path | str, rules_path: Path | str) -> None:
        catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
        rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        self.crops = {crop["id"]: crop for crop in catalog["crops"]}
        self.sources = catalog["sources"]
        self.season_cycle = tuple(rules["season_cycle"])
        self.successors: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
        for relationship in rules["relationships"]:
            self.successors.setdefault(relationship["from"], []).append((relationship["to"], tuple(relationship["source_ids"])))
        for values in self.successors.values():
            values.sort(key=lambda item: item[0])

    def generate(self, profile: FarmProfile, max_plans: int = 12) -> PlanningResult:
        """Generate non-duplicate, non-dominated supported sequences."""
        if profile.number_of_seasons < 1:
            raise RotationInputError("Plan at least one season.")
        if profile.start_season not in self.season_cycle:
            raise RotationInputError(f"Start season must be one of {self.season_cycle}.")
        if profile.total_crop_water_budget_mm is not None and profile.total_crop_water_budget_mm < 0:
            raise RotationInputError("Total crop-water budget cannot be negative.")
        weights = normalize_weights(profile.priority_weights)
        seasons = self._seasons(profile.start_season, profile.number_of_seasons)
        exclusions: list[FeasibilityCheck] = []
        raw_paths: list[tuple[str, ...]] = []

        def search(path: tuple[str, ...]) -> None:
            position = len(path)
            if position == profile.number_of_seasons:
                raw_paths.append(path)
                return
            target_season = seasons[position]
            if position == 0:
                choices = [(crop_id, ()) for crop_id in sorted(self.crops)]
                if profile.previous_crop_id:
                    choices = self.successors.get(profile.previous_crop_id, [])
            else:
                choices = self.successors.get(path[-1], [])
            if not choices:
                exclusions.append(FeasibilityCheck("documented_rotation_relationship", "fail", f"No supported successor relationship is documented for {path[-1] if path else profile.previous_crop_id}.", ()))
            for crop_id, source_ids in choices:
                checks = self._eligibility(crop_id, target_season, profile, source_ids)
                if any(check.status == "fail" for check in checks):
                    exclusions.extend(checks)
                    continue
                search(path + (crop_id,))

        search(())
        plans = [self._build_plan(path, seasons, profile, weights) for path in sorted(set(raw_paths))]
        plans = self._without_dominated(plans)
        plans.sort(key=lambda plan: (-(plan.composite_score if plan.composite_score is not None else -1), plan.crop_ids))
        if not plans:
            return PlanningResult((), tuple(exclusions), "No supported rotation was generated. Review season selection, documented relationship coverage, known hard constraints, and farmer-provided avoidance restrictions.")
        return PlanningResult(tuple(plans[:max_plans]), tuple(exclusions), f"Generated {min(len(plans), max_plans)} supported rotation(s). Plans with unknown suitability are marked as conditional, not confirmed.")

    def assess_sequence(self, crop_ids: tuple[str, ...], profile: FarmProfile) -> RotationPlan:
        """Assess one stated sequence, including known failures, without searching.

        Scenario analysis needs to retain a baseline sequence even when a stress
        test makes it infeasible. This method therefore returns an explicit
        ``infeasible`` plan rather than silently dropping it from the result.
        """
        if len(crop_ids) != profile.number_of_seasons:
            raise RotationInputError("The supplied sequence length must match the number of planned seasons.")
        if not crop_ids:
            raise RotationInputError("Assess at least one crop.")
        unknown = [crop_id for crop_id in crop_ids if crop_id not in self.crops]
        if unknown:
            raise RotationInputError(f"Unknown crop identifier(s): {unknown}")
        weights = normalize_weights(profile.priority_weights)
        seasons = self._seasons(profile.start_season, profile.number_of_seasons)
        checks: list[FeasibilityCheck] = []
        for index, crop_id in enumerate(crop_ids):
            relationship_sources: tuple[str, ...] = ()
            if index == 0 and profile.previous_crop_id:
                relationship_sources = next((sources for candidate, sources in self.successors.get(profile.previous_crop_id, []) if candidate == crop_id), ())
                if not relationship_sources:
                    checks.append(FeasibilityCheck("documented_rotation_relationship", "fail", f"No supported relationship is documented from previous crop {profile.previous_crop_id} to {crop_id}.", ()))
            elif index > 0:
                relationship_sources = next((sources for candidate, sources in self.successors.get(crop_ids[index - 1], []) if candidate == crop_id), ())
                if not relationship_sources:
                    checks.append(FeasibilityCheck("documented_rotation_relationship", "fail", f"No supported relationship is documented from {crop_ids[index - 1]} to {crop_id}.", ()))
            checks.extend(self._eligibility(crop_id, seasons[index], profile, relationship_sources))
        return self._assemble_plan(crop_ids, seasons, profile, weights, checks)

    def _seasons(self, start_season: str, count: int) -> tuple[str, ...]:
        index = self.season_cycle.index(start_season)
        return tuple(self.season_cycle[(index + offset) % len(self.season_cycle)] for offset in range(count))

    def _urls(self, source_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        return tuple(self.sources[source_id]["url"] for source_id in source_ids if source_id in self.sources)

    def _eligibility(self, crop_id: str, season: str, profile: FarmProfile, relationship_sources: tuple[str, ...]) -> tuple[FeasibilityCheck, ...]:
        crop = self.crops[crop_id]
        checks: list[FeasibilityCheck] = []
        if season not in crop["growing_seasons"]:
            checks.append(FeasibilityCheck("catalogue_growing_season", "fail", f"{crop['name']} is catalogued for {crop['growing_seasons']}, not {season}.", self._urls(crop["source_ids"])))
        else:
            checks.append(FeasibilityCheck("catalogue_growing_season", "pass", f"{crop['name']} matches the planned {season} season.", self._urls(crop["source_ids"])))
        if crop_id in profile.blocked_crop_ids or crop["family"] in profile.blocked_families:
            checks.append(FeasibilityCheck("farmer_provided_rotation_or_pest_restriction", "fail", f"{crop['name']} is blocked by a farmer-provided crop/family restriction.", ()))
        else:
            checks.append(FeasibilityCheck("farmer_provided_rotation_or_pest_restriction", "pass", "No farmer-provided crop/family restriction applies.", ()))
        water = crop["water_requirement"]
        if profile.total_crop_water_budget_mm is None:
            checks.append(FeasibilityCheck("documented_water_requirement", "unknown", "No total crop-water budget was provided; water feasibility cannot be established.", self._urls(water["source_ids"])))
        elif water["status"] == "documented_approximation":
            if profile.total_crop_water_budget_mm < water["range_min"]:
                checks.append(FeasibilityCheck("documented_water_requirement", "fail", f"Budget {profile.total_crop_water_budget_mm:g} mm is below the documented minimum {water['range_min']:g} mm for this source/method context.", self._urls(water["source_ids"])))
            else:
                checks.append(FeasibilityCheck("documented_water_requirement", "pass", "Budget meets the catalogue's documented minimum for its stated method context.", self._urls(water["source_ids"])))
        else:
            checks.append(FeasibilityCheck("documented_water_requirement", "unknown", "This crop has no documented water range in the catalogue; it is not rejected for missing evidence.", ()))
        checks.extend(self._soil_checks(crop, profile.soil))
        temperature = crop["temperature_suitability"]
        if temperature["status"] == "unknown":
            checks.append(FeasibilityCheck("climate_suitability", "unknown", "Climate data may be retrieved, but this catalogue has no documented crop-specific thermal threshold for this crop.", ()))
        if relationship_sources:
            checks.append(FeasibilityCheck("documented_rotation_relationship", "pass", "Crop-to-crop transition is in the supported relationship graph.", self._urls(relationship_sources)))
        return tuple(checks)

    def _soil_checks(self, crop: Mapping[str, object], soil: SoilInformation) -> tuple[FeasibilityCheck, ...]:
        crop_id = str(crop["id"])
        urls = self._urls(crop["soil_constraints"]["source_ids"])  # type: ignore[index]
        if crop_id == "wheat":
            if soil.waterlogged is True or soil.highly_deteriorated_alkaline is True:
                return (FeasibilityCheck("documented_wheat_soil_constraint", "fail", "PAU lists highly deteriorated alkaline and water-logged soils as exceptions for wheat.", urls),)
            if soil.waterlogged is False and soil.highly_deteriorated_alkaline is False:
                return (FeasibilityCheck("documented_wheat_soil_constraint", "pass", "Provided soil conditions do not match the documented wheat exceptions.", urls),)
            return (FeasibilityCheck("documented_wheat_soil_constraint", "unknown", "Waterlogging and highly deteriorated alkaline condition were not both confirmed; wheat soil feasibility cannot be established.", urls),)
        if crop_id == "rapeseed_mustard":
            if soil.well_drained is True and soil.texture in {"light", "medium"}:
                return (FeasibilityCheck("documented_rapeseed_mustard_soil_context", "pass", "Provided drainage and texture match PAU's stated best soil context.", urls),)
            return (FeasibilityCheck("documented_rapeseed_mustard_soil_context", "unknown", "PAU gives a best-soil context, but the required drainage/texture evidence is incomplete or not matching; no hard rejection is made.", urls),)
        return (FeasibilityCheck("soil_constraint", "unknown", "No crop-specific soil threshold has been validated in the catalogue.", urls),)

    def _build_plan(self, path: tuple[str, ...], seasons: tuple[str, ...], profile: FarmProfile, weights: Mapping[str, float]) -> RotationPlan:
        checks: list[FeasibilityCheck] = []
        for index, crop_id in enumerate(path):
            relationship_sources = () if index == 0 else next(sources for candidate, sources in self.successors[path[index - 1]] if candidate == crop_id)
            checks.extend(self._eligibility(crop_id, seasons[index], profile, relationship_sources))
        return self._assemble_plan(path, seasons, profile, weights, checks)

    def _assemble_plan(
        self,
        path: tuple[str, ...],
        seasons: tuple[str, ...],
        profile: FarmProfile,
        weights: Mapping[str, float],
        checks: list[FeasibilityCheck],
    ) -> RotationPlan:
        metrics = self._metrics(path, profile)
        available = {name: metric for name, metric in metrics.items() if metric.score is not None and weights[name] > 0}
        total_weight = sum(weights[name] for name in available)
        effective_weights = {name: (weights[name] / total_weight if name in available else 0.0) for name in METRICS} if total_weight else {name: 0.0 for name in METRICS}
        composite = sum(available[name].score * effective_weights[name] for name in available) if available else None
        unknown_checks = [check for check in checks if check.status == "unknown"]
        warnings = [check.message for check in unknown_checks]
        warnings.extend(metric.warning for metric in metrics.values() if metric.warning)
        failed_checks = [check for check in checks if check.status == "fail"]
        factors = [f"Rotation contains {len({self.crops[crop]['family'] for crop in path})} crop family/families across {len(path)} planned season(s)."]
        if not failed_checks:
            factors.insert(0, "Every crop-to-crop step is documented in the supported relationship graph.")
        tradeoffs = ["Composite score is a preference-weighted comparison, not a probability of success."]
        if metrics["economic_potential"].score is None:
            tradeoffs.append("Economic potential is unavailable because no credible local cost/price data is configured.")
        source_ids = {source_id for crop_id in path for source_id in self.crops[crop_id]["source_ids"]}
        for check in checks:
            for url in check.source_urls:
                matching_source = next((source_id for source_id, source in self.sources.items() if source["url"] == url), None)
                if matching_source:
                    source_ids.add(matching_source)
        return RotationPlan(
            crop_ids=path,
            crop_names=tuple(self.crops[crop_id]["name"] for crop_id in path),
            seasons=seasons,
            status="infeasible" if failed_checks else ("conditionally_feasible" if unknown_checks else "feasible_with_known_constraints"),
            checks=tuple(checks), metrics=metrics, effective_weights=effective_weights, composite_score=composite,
            positive_factors=tuple(factors), tradeoffs=tuple(tradeoffs), uncertainty_warnings=tuple(dict.fromkeys(warnings)),
            source_urls=tuple(sorted(self.sources[source_id]["url"] for source_id in source_ids)),
        )

    def _metrics(self, path: tuple[str, ...], profile: FarmProfile) -> dict[str, MetricScore]:
        crops = [self.crops[crop_id] for crop_id in path]
        water_values: list[float] = []
        if profile.total_crop_water_budget_mm is None:
            water = MetricScore(None, "Unavailable: no total crop-water budget was supplied.", "Water suitability cannot be scored without a total crop-water budget.")
        elif any(crop["water_requirement"]["status"] != "documented_approximation" for crop in crops):
            water = MetricScore(None, "Unavailable: at least one crop lacks a documented water range.", "Water suitability is not scored when a selected crop has unknown water evidence.")
        else:
            for crop in crops:
                requirement = crop["water_requirement"]
                low, high = requirement["range_min"], requirement["range_max"]
                if profile.total_crop_water_budget_mm >= high:
                    water_values.append(1.0)
                else:
                    margin_score = 0.5 + 0.5 * (profile.total_crop_water_budget_mm - low) / (high - low)
                    water_values.append(min(1.0, max(0.0, margin_score)))
            water = MetricScore(sum(water_values) / len(water_values), "Mean 0–1 margin above documented crop-method minimums; values are only comparable within stated catalogue contexts.")
        soil_values: list[float] = []
        if "wheat" in path and profile.soil.waterlogged is False and profile.soil.highly_deteriorated_alkaline is False:
            soil_values.append(1.0)
        if "rapeseed_mustard" in path and profile.soil.well_drained is True and profile.soil.texture in {"light", "medium"}:
            soil_values.append(1.0)
        soil = MetricScore(sum(soil_values) / len(soil_values), "Mean of only documented favourable soil-context checks; it is not a soil-health prediction.") if soil_values else MetricScore(None, "Unavailable: no documented favourable soil-context check could be evaluated.", "Missing soil evidence reduces confidence but does not reject crops by itself.")
        diversity = MetricScore(len({crop["family"] for crop in crops}) / len(crops), "Unique crop families divided by planned seasons; a composition indicator, not a soil-benefit estimate.")
        return {
            "water_suitability": water,
            "climate_suitability": MetricScore(None, "Unavailable: crop-specific thermal thresholds are not documented in the catalogue.", "Retrieved climate data is preserved but cannot be converted to crop suitability without sourced thresholds."),
            "soil_related_potential": soil,
            "rotation_diversity": diversity,
            "economic_potential": MetricScore(None, "Unavailable: no credible local cost or price data is configured.", "No economic estimate is fabricated."),
        }

    @staticmethod
    def _without_dominated(plans: list[RotationPlan]) -> list[RotationPlan]:
        retained: list[RotationPlan] = []
        for candidate in plans:
            dominated = False
            for other in plans:
                if candidate is other:
                    continue
                # A plan may only dominate another when both have scores for every
                # comparable configured metric. Missing evidence must not erase a
                # documented alternative merely because it cannot be quantified.
                comparable = [name for name in METRICS if candidate.metrics[name].score is not None or other.metrics[name].score is not None]
                if comparable and all(candidate.metrics[name].score is not None and other.metrics[name].score is not None for name in comparable) and all(other.metrics[name].score >= candidate.metrics[name].score for name in comparable) and any(other.metrics[name].score > candidate.metrics[name].score for name in comparable):
                    dominated = True
                    break
            if not dominated:
                retained.append(candidate)
        return retained
