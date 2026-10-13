"""Hypothetical climate-stress tests and transparent robustness reporting.

These are deterministic sensitivity tests. They are not weather forecasts,
probability estimates, crop-yield models, or calibrated soil simulations.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping, Sequence

import pandas as pd

from .rotation_engine import METRICS, FarmProfile, RotationEngine, RotationPlan


class ScenarioInputError(ValueError):
    """Raised when a hypothetical stress-test setting is outside its safe range."""


@dataclass(frozen=True)
class ScenarioDefinition:
    """A precisely defined deterministic transformation of baseline context."""

    identifier: str
    label: str
    description: str
    precipitation_factor: float = 1.0
    temperature_delta_c: float = 0.0
    water_budget_factor: float = 1.0
    is_hypothetical: bool = False


@dataclass(frozen=True)
class ScenarioOutcome:
    """One baseline rotation assessed under one named scenario."""

    scenario: ScenarioDefinition
    crop_ids: tuple[str, ...]
    feasibility: str
    hard_constraint_violated: bool
    hard_failure_messages: tuple[str, ...]
    component_scores: Mapping[str, float | None]
    score_changes_from_baseline: Mapping[str, float | None]
    composite_score: float | None
    water_budget_mm: float | None
    plan: RotationPlan


@dataclass(frozen=True)
class RobustnessReport:
    """Scenario outcomes and non-numeric uncertainty notes for one planning run."""

    scenarios: tuple[ScenarioDefinition, ...]
    outcomes: Mapping[tuple[str, ...], tuple[ScenarioOutcome, ...]]
    data_coverage_notes: tuple[str, ...]
    model_uncertainty_notes: tuple[str, ...]
    scenario_uncertainty_notes: tuple[str, ...]


@dataclass(frozen=True)
class ParetoAssessment:
    """Whether a candidate is dominated using only fully comparable objectives."""

    candidate_id: str
    non_dominated: bool
    dominated_by: tuple[str, ...]
    comparable_objectives: tuple[str, ...]


def build_scenarios(
    dry_precipitation_reduction_pct: float = 25.0,
    hot_temperature_increase_c: float = 2.0,
    irrigation_reduction_pct: float = 0.0,
) -> tuple[ScenarioDefinition, ...]:
    """Create the baseline plus explicitly labelled hypothetical stress tests.

    The dry case scales each available daily precipitation value by the stated
    factor. The hot case adds the stated Celsius increment to available daily
    temperature values. Neither transformation changes missing observations.
    Irrigation reduction changes only a farmer-provided water budget; it is never
    inferred from NASA POWER precipitation.
    """
    if not 0 <= dry_precipitation_reduction_pct <= 100:
        raise ScenarioInputError("Dry precipitation reduction must be between 0 and 100 percent.")
    if not 0 <= hot_temperature_increase_c <= 10:
        raise ScenarioInputError("Temperature increase must be between 0 and 10 °C for this sensitivity test.")
    if not 0 <= irrigation_reduction_pct <= 100:
        raise ScenarioInputError("Irrigation reduction must be between 0 and 100 percent.")
    scenarios = [
        ScenarioDefinition("historical_baseline", "Historical baseline", "Unmodified historical NASA POWER context and farmer-provided water budget."),
        ScenarioDefinition(
            "dry_stress",
            "Dry stress test",
            f"Hypothetical stress test: each available daily PRECTOTCORR value is reduced by {dry_precipitation_reduction_pct:g}%. Water budget is not changed by this transformation.",
            precipitation_factor=1 - dry_precipitation_reduction_pct / 100,
            is_hypothetical=True,
        ),
        ScenarioDefinition(
            "hot_stress",
            "Hotter-than-baseline stress test",
            f"Hypothetical stress test: {hot_temperature_increase_c:g} °C is added to each available daily T2M, T2M_MIN and T2M_MAX value. No crop thermal threshold is assumed.",
            temperature_delta_c=hot_temperature_increase_c,
            is_hypothetical=True,
        ),
    ]
    if irrigation_reduction_pct > 0:
        scenarios.append(
            ScenarioDefinition(
                "irrigation_reduction",
                "Reduced water-budget stress test",
                f"Hypothetical planning test: farmer-provided total crop-water budget is reduced by {irrigation_reduction_pct:g}%. This is not inferred from NASA data.",
                water_budget_factor=1 - irrigation_reduction_pct / 100,
                is_hypothetical=True,
            )
        )
    return tuple(scenarios)


def transform_climate_frame(frame: pd.DataFrame, scenario: ScenarioDefinition) -> pd.DataFrame:
    """Return a labelled copy of daily climate context after a scenario transform."""
    transformed = frame.copy(deep=True)
    if "PRECTOTCORR" in transformed:
        transformed["PRECTOTCORR"] = transformed["PRECTOTCORR"] * scenario.precipitation_factor
    for column in ("T2M", "T2M_MIN", "T2M_MAX"):
        if column in transformed:
            transformed[column] = transformed[column] + scenario.temperature_delta_c
    return transformed


def scenario_profile(profile: FarmProfile, scenario: ScenarioDefinition) -> FarmProfile:
    """Apply only the documented budget adjustment and climate perturbation to a planning profile."""
    budget = profile.total_crop_water_budget_mm
    adjusted_budget = None if budget is None else budget * scenario.water_budget_factor
    transformed_climate = None
    if profile.climate_data is not None and isinstance(profile.climate_data, pd.DataFrame):
        transformed_climate = transform_climate_frame(profile.climate_data, scenario)
    return replace(
        profile,
        total_crop_water_budget_mm=adjusted_budget,
        climate_scenario=scenario.label,
        climate_data=transformed_climate,
    )


def evaluate_robustness(
    engine: RotationEngine,
    baseline_plans: Sequence[RotationPlan],
    profile: FarmProfile,
    scenarios: Sequence[ScenarioDefinition],
    climate_frame: pd.DataFrame | None = None,
) -> RobustnessReport:
    """Assess every baseline plan under every scenario without hiding failures."""
    if not scenarios:
        raise ScenarioInputError("At least one scenario is required.")
    baseline_id = "historical_baseline"
    if baseline_id not in {scenario.identifier for scenario in scenarios}:
        raise ScenarioInputError("Scenario comparison requires the historical_baseline scenario.")
    outcomes: dict[tuple[str, ...], tuple[ScenarioOutcome, ...]] = {}
    for baseline_plan in baseline_plans:
        evaluated: list[ScenarioOutcome] = []
        baseline_scores: Mapping[str, float | None] | None = None
        for scenario in scenarios:
            assessed = engine.assess_sequence(baseline_plan.crop_ids, scenario_profile(profile, scenario))
            scores = {metric: assessed.metrics[metric].score for metric in METRICS}
            if scenario.identifier == baseline_id:
                baseline_scores = scores
            changes = {
                metric: None if baseline_scores is None or scores[metric] is None or baseline_scores[metric] is None else scores[metric] - baseline_scores[metric]
                for metric in METRICS
            }
            failures = tuple(check.message for check in assessed.checks if check.status == "fail")
            evaluated.append(
                ScenarioOutcome(
                    scenario=scenario,
                    crop_ids=baseline_plan.crop_ids,
                    feasibility=assessed.status,
                    hard_constraint_violated=bool(failures),
                    hard_failure_messages=failures,
                    component_scores=scores,
                    score_changes_from_baseline=changes,
                    composite_score=assessed.composite_score,
                    water_budget_mm=scenario_profile(profile, scenario).total_crop_water_budget_mm,
                    plan=assessed,
                )
            )
        outcomes[baseline_plan.crop_ids] = tuple(evaluated)
    return RobustnessReport(
        scenarios=tuple(scenarios),
        outcomes=outcomes,
        data_coverage_notes=_data_coverage_notes(profile, climate_frame),
        model_uncertainty_notes=_model_uncertainty_notes(engine, baseline_plans),
        scenario_uncertainty_notes=tuple(s.description for s in scenarios if s.is_hypothetical),
    )


def pareto_assess(vectors: Mapping[str, Mapping[str, float | None]]) -> tuple[ParetoAssessment, ...]:
    """Classify candidates without treating unknown objectives as zero.

    Candidate B dominates A only if every objective known for either candidate is
    known for both, B is at least as high on all of them, and strictly higher on
    at least one. This conservative definition preserves options when evidence is
    incomplete.
    """
    assessments: list[ParetoAssessment] = []
    for candidate_id, values in vectors.items():
        dominating: list[str] = []
        comparable_for_report: set[str] = set()
        for other_id, other_values in vectors.items():
            if other_id == candidate_id:
                continue
            objectives = tuple(sorted(set(values) | set(other_values)))
            comparable = tuple(name for name in objectives if values.get(name) is not None or other_values.get(name) is not None)
            if not comparable or not all(values.get(name) is not None and other_values.get(name) is not None for name in comparable):
                continue
            comparable_for_report.update(comparable)
            if all(other_values[name] >= values[name] for name in comparable) and any(other_values[name] > values[name] for name in comparable):
                dominating.append(other_id)
        assessments.append(ParetoAssessment(candidate_id, not dominating, tuple(dominating), tuple(sorted(comparable_for_report))))
    return tuple(assessments)


def _data_coverage_notes(profile: FarmProfile, climate_frame: pd.DataFrame | None) -> tuple[str, ...]:
    notes: list[str] = []
    missing_soil = [label for label, value in (("texture", profile.soil.texture), ("pH", profile.soil.ph), ("organic carbon", profile.soil.organic_carbon_percent), ("electrical conductivity", profile.soil.electrical_conductivity_ds_m), ("waterlogging status", profile.soil.waterlogged)) if value is None]
    if missing_soil:
        notes.append("Missing farmer/laboratory soil information: " + ", ".join(missing_soil) + ". Missing values are not treated as favourable or unfavourable.")
    if climate_frame is None:
        notes.append("No retrieved climate frame is attached, so climate-record coverage cannot be assessed.")
    else:
        missing = int(climate_frame.isna().sum().sum())
        if missing:
            notes.append(f"Retrieved climate frame contains {missing} missing daily value(s); stress transforms preserve missing values.")
        else:
            notes.append("Retrieved climate frame has no missing values in the selected parameters/date range.")
        notes.append("NASA POWER point-query data represents source-native gridded climate context, not field-scale measurements.")
    return tuple(notes)


def _model_uncertainty_notes(engine: RotationEngine, plans: Sequence[RotationPlan]) -> tuple[str, ...]:
    selected = {crop_id for plan in plans for crop_id in plan.crop_ids}
    uncertain_temperature = [engine.crops[crop_id]["name"] for crop_id in sorted(selected) if engine.crops[crop_id]["temperature_suitability"]["status"] == "unknown"]
    uncertain_water = [engine.crops[crop_id]["name"] for crop_id in sorted(selected) if engine.crops[crop_id]["water_requirement"]["status"] != "documented_approximation"]
    notes = ["The rule engine checks only documented hard constraints and sequence relationships. It does not predict yield, income, pests, nitrogen fixation, or soil-carbon change."]
    if uncertain_temperature:
        notes.append("No crop-specific thermal threshold is configured for: " + ", ".join(uncertain_temperature) + ". Hot-stress results therefore do not become a climate-suitability score.")
    if uncertain_water:
        notes.append("No documented water range is configured for: " + ", ".join(uncertain_water) + ". Water scores remain unavailable where such a crop is present.")
    return tuple(notes)
