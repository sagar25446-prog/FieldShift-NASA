from pathlib import Path

import pandas as pd
import pytest

from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation
from fieldshift.scenarios import ScenarioInputError, build_scenarios, evaluate_robustness, pareto_assess, transform_climate_frame


ROOT = Path(__file__).resolve().parents[1]
ENGINE = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")


def profile(**overrides: object) -> FarmProfile:
    values = {
        "latitude": 30.9009,
        "longitude": 75.8573,
        "soil": SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False),
        "climate": ClimateContext(available_parameters=("T2M", "PRECTOTCORR")),
        "total_crop_water_budget_mm": 600,
        "previous_crop_id": None,
        "priority_weights": {"water_suitability": 0.6, "soil_related_potential": 0.2, "rotation_diversity": 0.2},
        "number_of_seasons": 3,
        "start_season": "kharif",
    }
    values.update(overrides)
    return FarmProfile(**values)


def test_hypothetical_transforms_are_precise_and_preserve_missing_values() -> None:
    frame = pd.DataFrame({"PRECTOTCORR": [4.0, None], "T2M": [20.0, None], "T2M_MIN": [10.0, 11.0], "T2M_MAX": [30.0, 31.0]})
    dry, hot = build_scenarios(25, 2)[1:]
    dry_frame = transform_climate_frame(frame, dry)
    hot_frame = transform_climate_frame(frame, hot)
    assert dry_frame.loc[0, "PRECTOTCORR"] == 3.0
    assert pd.isna(dry_frame.loc[1, "PRECTOTCORR"])
    assert hot_frame["T2M"].tolist()[0] == 22.0
    assert pd.isna(hot_frame.loc[1, "T2M"])
    assert "Hypothetical stress test" in dry.description


def test_reduced_farmer_water_budget_exposes_hard_constraint_and_score_change() -> None:
    baseline = ENGINE.assess_sequence(("maize", "wheat", "moong"), profile())
    scenarios = build_scenarios(irrigation_reduction_pct=50)
    report = evaluate_robustness(ENGINE, (baseline,), profile(), scenarios)
    outcomes = report.outcomes[baseline.crop_ids]
    baseline_outcome = outcomes[0]
    water_reduction = next(item for item in outcomes if item.scenario.identifier == "irrigation_reduction")
    assert baseline_outcome.feasibility == "conditionally_feasible"
    assert water_reduction.hard_constraint_violated
    assert water_reduction.feasibility == "infeasible"
    assert water_reduction.water_budget_mm == 300
    assert water_reduction.component_scores["water_suitability"] < baseline_outcome.component_scores["water_suitability"]


def test_missing_inputs_become_uncertainty_notes_not_confidence_percentages() -> None:
    incomplete = profile(soil=SoilInformation(), total_crop_water_budget_mm=None)
    baseline = ENGINE.assess_sequence(("cotton", "wheat", "moong"), incomplete)
    report = evaluate_robustness(ENGINE, (baseline,), incomplete, build_scenarios())
    assert any("Missing farmer/laboratory soil" in note for note in report.data_coverage_notes)
    assert any("No retrieved climate frame" in note for note in report.data_coverage_notes)
    assert all("% confidence" not in note for note in (*report.data_coverage_notes, *report.model_uncertainty_notes))


def test_pareto_keeps_unknown_evidence_from_creating_false_dominance_and_is_repeatable() -> None:
    vectors = {
        "water_first": {"water": 0.9, "soil": None},
        "soil_first": {"water": 0.8, "soil": 1.0},
        "weaker": {"water": 0.7, "soil": 0.6},
    }
    first = pareto_assess(vectors)
    second = pareto_assess(vectors)
    by_id = {item.candidate_id: item for item in first}
    assert first == second
    assert by_id["water_first"].non_dominated
    assert by_id["soil_first"].non_dominated
    assert not by_id["weaker"].non_dominated
    assert by_id["weaker"].dominated_by == ("soil_first",)


def test_scenario_parameters_are_validated() -> None:
    with pytest.raises(ScenarioInputError, match="precipitation"):
        build_scenarios(dry_precipitation_reduction_pct=101)
