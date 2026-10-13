"""Phase 6 tests — scenario transforms, hard constraints, Pareto, soil-state, reproducibility."""

from pathlib import Path

import pandas as pd
import pytest

from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation
from fieldshift.scenarios import (
    ScenarioInputError,
    build_scenarios,
    evaluate_robustness,
    pareto_assess,
    scenario_profile,
    transform_climate_frame,
)
from fieldshift.soil_nutrient_model import (
    build_soil_state_report,
    estimate_nutrient_balance,
    estimate_soc_change,
)


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


# ── Scenario transformation tests ──

class TestScenarioTransformations:
    """Verify precise, deterministic transforms of climate data."""

    def test_dry_scenario_reduces_precipitation_exactly(self) -> None:
        frame = pd.DataFrame({"PRECTOTCORR": [10.0, 20.0, 0.0], "T2M": [25.0, 30.0, 28.0]})
        scenarios = build_scenarios(dry_precipitation_reduction_pct=50)
        dry = scenarios[1]  # index 0 is baseline
        result = transform_climate_frame(frame, dry)
        assert result["PRECTOTCORR"].tolist() == [5.0, 10.0, 0.0]
        assert result["T2M"].tolist() == [25.0, 30.0, 28.0]  # unchanged

    def test_hot_scenario_increases_all_temperature_columns(self) -> None:
        frame = pd.DataFrame({
            "T2M": [20.0, 22.0],
            "T2M_MIN": [15.0, 17.0],
            "T2M_MAX": [28.0, 30.0],
            "PRECTOTCORR": [5.0, 3.0],
        })
        scenarios = build_scenarios(hot_temperature_increase_c=3.0)
        hot = scenarios[2]
        result = transform_climate_frame(frame, hot)
        assert result["T2M"].tolist() == [23.0, 25.0]
        assert result["T2M_MIN"].tolist() == [18.0, 20.0]
        assert result["T2M_MAX"].tolist() == [31.0, 33.0]
        assert result["PRECTOTCORR"].tolist() == [5.0, 3.0]  # unchanged

    def test_missing_values_are_preserved_through_transforms(self) -> None:
        frame = pd.DataFrame({
            "PRECTOTCORR": [4.0, None, 6.0],
            "T2M": [20.0, None, 22.0],
            "T2M_MIN": [10.0, None, 12.0],
            "T2M_MAX": [30.0, None, 32.0],
        })
        dry, hot = build_scenarios(25, 2)[1:]
        dry_result = transform_climate_frame(frame, dry)
        hot_result = transform_climate_frame(frame, hot)
        assert dry_result["PRECTOTCORR"].iloc[0] == 3.0
        assert pd.isna(dry_result["PRECTOTCORR"].iloc[1])
        assert hot_result["T2M"].iloc[0] == 22.0
        assert pd.isna(hot_result["T2M"].iloc[1])

    def test_baseline_transform_is_identity(self) -> None:
        frame = pd.DataFrame({"PRECTOTCORR": [5.0, 10.0], "T2M": [20.0, 25.0]})
        baseline = build_scenarios()[0]
        result = transform_climate_frame(frame, baseline)
        assert result.equals(frame)

    def test_transforms_are_reproducible(self) -> None:
        frame = pd.DataFrame({"PRECTOTCORR": [5.0, 10.0], "T2M": [20.0, 25.0]})
        scenarios = build_scenarios(30, 2.5)
        for scenario in scenarios:
            r1 = transform_climate_frame(frame, scenario)
            r2 = transform_climate_frame(frame, scenario)
            assert r1.equals(r2)


# ── Hard-constraint violation tests ──

class TestHardConstraintViolations:
    """Verify hard constraints are detected and reported correctly."""

    def test_water_budget_reduction_causes_hard_failure(self) -> None:
        baseline = ENGINE.assess_sequence(("maize", "wheat", "moong"), profile())
        scenarios = build_scenarios(irrigation_reduction_pct=50)
        report = evaluate_robustness(ENGINE, (baseline,), profile(), scenarios)
        outcomes = report.outcomes[baseline.crop_ids]
        water_reduced = next(o for o in outcomes if o.scenario.identifier == "irrigation_reduction")
        assert water_reduced.hard_constraint_violated
        assert water_reduced.feasibility == "infeasible"
        assert water_reduced.water_budget_mm == 300.0

    def test_waterlogged_soil_blocks_wheat(self) -> None:
        waterlogged_profile = profile(soil=SoilInformation(waterlogged=True, highly_deteriorated_alkaline=False))
        assessed = ENGINE.assess_sequence(("maize", "wheat", "moong"), waterlogged_profile)
        assert assessed.status == "infeasible"
        wheat_checks = [c for c in assessed.checks if "wheat" in c.rule.lower()]
        assert any(c.status == "fail" for c in wheat_checks)

    def test_blocked_crop_is_hard_failure(self) -> None:
        blocked = profile(blocked_crop_ids=frozenset({"wheat"}))
        assessed = ENGINE.assess_sequence(("maize", "wheat", "moong"), blocked)
        assert assessed.status == "infeasible"
        assert any(c.rule == "farmer_provided_rotation_or_pest_restriction" and c.status == "fail" for c in assessed.checks)


# ── Missing inputs tests ──

class TestMissingInputs:
    """Missing inputs produce uncertainty notes, never confidence percentages."""

    def test_missing_soil_produces_data_coverage_notes(self) -> None:
        incomplete = profile(soil=SoilInformation(), total_crop_water_budget_mm=None)
        baseline = ENGINE.assess_sequence(("cotton", "wheat", "moong"), incomplete)
        report = evaluate_robustness(ENGINE, (baseline,), incomplete, build_scenarios())
        assert any("Missing farmer/laboratory soil" in note for note in report.data_coverage_notes)

    def test_missing_climate_frame_noted(self) -> None:
        incomplete = profile(soil=SoilInformation())
        baseline = ENGINE.assess_sequence(("cotton", "wheat", "moong"), incomplete)
        report = evaluate_robustness(ENGINE, (baseline,), incomplete, build_scenarios(), climate_frame=None)
        assert any("No retrieved climate frame" in note for note in report.data_coverage_notes)

    def test_no_confidence_percentages_in_any_notes(self) -> None:
        incomplete = profile(soil=SoilInformation(), total_crop_water_budget_mm=None)
        baseline = ENGINE.assess_sequence(("cotton", "wheat", "moong"), incomplete)
        report = evaluate_robustness(ENGINE, (baseline,), incomplete, build_scenarios())
        all_notes = (
            *report.data_coverage_notes,
            *report.model_uncertainty_notes,
            *report.scenario_uncertainty_notes,
        )
        for note in all_notes:
            assert "% confidence" not in note
            assert "probability" not in note.lower()


# ── Score change tests ──

class TestScoreChanges:
    """Verify that scenario transformations change scores as expected."""

    def test_water_reduction_decreases_water_score(self) -> None:
        baseline_plan = ENGINE.assess_sequence(("maize", "wheat", "moong"), profile())
        scenarios = build_scenarios(irrigation_reduction_pct=50)
        report = evaluate_robustness(ENGINE, (baseline_plan,), profile(), scenarios)
        outcomes = report.outcomes[baseline_plan.crop_ids]
        baseline_outcome = outcomes[0]
        reduced_outcome = next(o for o in outcomes if o.scenario.identifier == "irrigation_reduction")
        baseline_water = baseline_outcome.component_scores["water_suitability"]
        reduced_water = reduced_outcome.component_scores["water_suitability"]
        if baseline_water is not None and reduced_water is not None:
            assert reduced_water < baseline_water

    def test_baseline_scenario_has_zero_score_change(self) -> None:
        baseline_plan = ENGINE.assess_sequence(("maize", "wheat", "moong"), profile())
        scenarios = build_scenarios()
        report = evaluate_robustness(ENGINE, (baseline_plan,), profile(), scenarios)
        outcomes = report.outcomes[baseline_plan.crop_ids]
        baseline_outcome = outcomes[0]
        for metric, change in baseline_outcome.score_changes_from_baseline.items():
            if change is not None:
                assert change == 0.0, f"{metric} should have 0 change for baseline"


# ── Pareto comparison tests ──

class TestParetoComparisons:
    """Pareto comparison is conservative with missing evidence."""

    def test_unknown_prevents_false_dominance(self) -> None:
        vectors = {
            "water_first": {"water": 0.9, "soil": None},
            "soil_first": {"water": 0.8, "soil": 1.0},
        }
        result = pareto_assess(vectors)
        by_id = {item.candidate_id: item for item in result}
        assert by_id["water_first"].non_dominated
        assert by_id["soil_first"].non_dominated

    def test_dominated_candidate_is_identified(self) -> None:
        vectors = {
            "better": {"water": 0.9, "soil": 0.8},
            "worse": {"water": 0.7, "soil": 0.6},
        }
        result = pareto_assess(vectors)
        by_id = {item.candidate_id: item for item in result}
        assert by_id["better"].non_dominated
        assert not by_id["worse"].non_dominated
        assert "better" in by_id["worse"].dominated_by

    def test_pareto_is_reproducible(self) -> None:
        vectors = {
            "a": {"x": 0.9, "y": 0.3},
            "b": {"x": 0.5, "y": 0.8},
            "c": {"x": 0.4, "y": 0.4},
        }
        r1 = pareto_assess(vectors)
        r2 = pareto_assess(vectors)
        assert r1 == r2

    def test_equal_scores_means_no_dominance(self) -> None:
        vectors = {
            "x": {"a": 0.5, "b": 0.5},
            "y": {"a": 0.5, "b": 0.5},
        }
        result = pareto_assess(vectors)
        assert all(item.non_dominated for item in result)


# ── Reproducibility tests ──

class TestReproducibility:
    """Engine results must be deterministic across repeated runs."""

    def test_generate_is_reproducible(self) -> None:
        p = profile()
        r1 = ENGINE.generate(p)
        r2 = ENGINE.generate(p)
        assert r1.plans == r2.plans
        assert r1.message == r2.message

    def test_robustness_report_is_reproducible(self) -> None:
        p = profile()
        baseline = ENGINE.assess_sequence(("maize", "wheat", "moong"), p)
        scenarios = build_scenarios()
        r1 = evaluate_robustness(ENGINE, (baseline,), p, scenarios)
        r2 = evaluate_robustness(ENGINE, (baseline,), p, scenarios)
        assert r1.outcomes == r2.outcomes
        assert r1.data_coverage_notes == r2.data_coverage_notes


# ── Scenario parameter validation tests ──

class TestScenarioValidation:
    """Scenario parameters outside safe ranges are rejected."""

    def test_precipitation_over_100_rejected(self) -> None:
        with pytest.raises(ScenarioInputError, match="precipitation"):
            build_scenarios(dry_precipitation_reduction_pct=101)

    def test_negative_precipitation_rejected(self) -> None:
        with pytest.raises(ScenarioInputError, match="precipitation"):
            build_scenarios(dry_precipitation_reduction_pct=-1)

    def test_temperature_over_10_rejected(self) -> None:
        with pytest.raises(ScenarioInputError, match="Temperature"):
            build_scenarios(hot_temperature_increase_c=11)

    def test_irrigation_over_100_rejected(self) -> None:
        with pytest.raises(ScenarioInputError, match="Irrigation"):
            build_scenarios(irrigation_reduction_pct=101)

    def test_irrigation_scenario_only_added_when_positive(self) -> None:
        no_irrig = build_scenarios(irrigation_reduction_pct=0)
        with_irrig = build_scenarios(irrigation_reduction_pct=20)
        assert len(with_irrig) == len(no_irrig) + 1
        assert any(s.identifier == "irrigation_reduction" for s in with_irrig)


# ── Soil-state model tests ──

class TestSoilStateModel:
    """Feature E: simplified nutrient-balance and SOC model."""

    def test_legume_gets_n_fixation_credit(self) -> None:
        estimates = estimate_nutrient_balance(
            crop_ids=("moong",),
            crop_names=("Moong",),
            seasons=("summer",),
            is_legume={"moong": True},
        )
        assert len(estimates) == 1
        assert estimates[0].legume_n_credit_kg_ha is not None
        assert estimates[0].legume_n_credit_kg_ha[0] == 20.0
        assert estimates[0].legume_n_credit_kg_ha[1] == 40.0

    def test_non_legume_has_no_fixation_credit(self) -> None:
        estimates = estimate_nutrient_balance(
            crop_ids=("wheat",),
            crop_names=("Wheat",),
            seasons=("rabi",),
            is_legume={"wheat": False},
        )
        assert estimates[0].legume_n_credit_kg_ha is None

    def test_residue_n_and_c_are_positive_ranges(self) -> None:
        estimates = estimate_nutrient_balance(
            crop_ids=("rice", "wheat", "moong"),
            crop_names=("Rice", "Wheat", "Moong"),
            seasons=("kharif", "rabi", "summer"),
            is_legume={"rice": False, "wheat": False, "moong": True},
        )
        for est in estimates:
            assert est.residue_n_return_kg_ha[0] > 0
            assert est.residue_n_return_kg_ha[1] >= est.residue_n_return_kg_ha[0]
            assert est.residue_c_input_kg_ha[0] > 0

    def test_soc_estimate_without_initial_soc_is_uncertain(self) -> None:
        soc = estimate_soc_change(("rice", "wheat", "moong"), initial_soc_percent=None)
        assert soc is not None
        assert soc.estimated_annual_change_direction == "uncertain"

    def test_soc_estimate_with_initial_soc(self) -> None:
        soc = estimate_soc_change(("rice", "wheat", "moong"), initial_soc_percent=0.5)
        assert soc is not None
        assert soc.estimated_annual_change_direction in ("likely_increase", "likely_decrease", "uncertain")
        assert soc.decay_constant_yr > 0

    def test_full_soil_state_report_includes_limitations(self) -> None:
        report = build_soil_state_report(
            crop_ids=("maize", "wheat", "moong"),
            crop_names=("Maize", "Wheat", "Moong"),
            seasons=("kharif", "rabi", "summer"),
            is_legume={"maize": False, "wheat": False, "moong": True},
        )
        assert len(report.nutrient_estimates) == 3
        assert len(report.limitations) > 0
        assert any("calibrated" in lim.lower() or "simplified" in lim.lower() for lim in report.limitations)
        assert report.soc_estimate is not None

    def test_all_estimates_have_calibration_warnings(self) -> None:
        estimates = estimate_nutrient_balance(
            crop_ids=("wheat",),
            crop_names=("Wheat",),
            seasons=("rabi",),
            is_legume={"wheat": False},
        )
        for est in estimates:
            assert "not calibrated" in est.calibration_warning.lower() or "simplified" in est.calibration_warning.lower()

    def test_soc_has_calibration_warning(self) -> None:
        soc = estimate_soc_change(("wheat",), initial_soc_percent=0.5)
        assert soc is not None
        assert "NOT been validated" in soc.calibration_warning


# ── Scenario profile transformation ──

class TestScenarioProfile:
    """Water budget is correctly adjusted by scenario profile."""

    def test_water_budget_reduced(self) -> None:
        p = profile(total_crop_water_budget_mm=1000)
        scenario = build_scenarios(irrigation_reduction_pct=30)[-1]
        adjusted = scenario_profile(p, scenario)
        assert adjusted.total_crop_water_budget_mm == pytest.approx(700.0)

    def test_none_budget_stays_none(self) -> None:
        p = profile(total_crop_water_budget_mm=None)
        scenario = build_scenarios(irrigation_reduction_pct=30)[-1]
        adjusted = scenario_profile(p, scenario)
        assert adjusted.total_crop_water_budget_mm is None
