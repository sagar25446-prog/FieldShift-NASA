import json
from pathlib import Path

import pytest

from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, RotationInputError, SoilInformation, normalize_weights


ROOT = Path(__file__).resolve().parents[1]
ENGINE = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")
BALANCED = {"water_suitability": 0.35, "climate_suitability": 0.2, "soil_related_potential": 0.25, "rotation_diversity": 0.2, "economic_potential": 0.0}


def profile(**overrides: object) -> FarmProfile:
    values = {
        "latitude": 30.9009, "longitude": 75.8573,
        "soil": SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False, source_description="illustrative lab/farmer input"),
        "climate": ClimateContext(source_url="https://power.example/request", date_range="2024-01-01 to 2024-03-31", available_parameters=("T2M", "PRECTOTCORR")),
        "total_crop_water_budget_mm": 600, "previous_crop_id": None, "priority_weights": BALANCED,
        "number_of_seasons": 3, "start_season": "kharif",
    }
    values.update(overrides)
    return FarmProfile(**values)


def test_generates_documented_feasible_maize_wheat_moong_sequence() -> None:
    result = ENGINE.generate(profile(), max_plans=20)
    matching = next(plan for plan in result.plans if plan.crop_ids == ("maize", "wheat", "moong"))
    assert matching.status == "conditionally_feasible"
    assert all(check.status != "fail" for check in matching.checks)
    assert matching.metrics["water_suitability"].score == 1.0
    assert matching.metrics["climate_suitability"].score is None
    assert matching.effective_weights["climate_suitability"] == 0.0


def test_known_water_and_soil_constraints_prevent_invalid_sequences() -> None:
    low_water = ENGINE.generate(profile(total_crop_water_budget_mm=200), max_plans=20)
    assert not low_water.plans
    assert any(check.rule == "documented_water_requirement" and check.status == "fail" for check in low_water.exclusions)
    waterlogged = ENGINE.generate(profile(soil=SoilInformation(waterlogged=True, highly_deteriorated_alkaline=False)), max_plans=20)
    assert all("wheat" not in plan.crop_ids for plan in waterlogged.plans)


def test_missing_soil_data_is_conditional_not_rejection_and_results_are_repeatable() -> None:
    input_profile = profile(soil=SoilInformation())
    first, second = ENGINE.generate(input_profile), ENGINE.generate(input_profile)
    assert first.plans and first.plans == second.plans
    wheat_plan = next(plan for plan in first.plans if "wheat" in plan.crop_ids)
    assert wheat_plan.status == "conditionally_feasible"
    assert any(check.rule == "documented_wheat_soil_constraint" and check.status == "unknown" for check in wheat_plan.checks)


def test_priority_weights_are_normalised_and_invalid_weights_fail() -> None:
    weights = normalize_weights({"water_suitability": 2, "rotation_diversity": 2})
    assert weights["water_suitability"] == weights["rotation_diversity"] == 0.5
    assert sum(weights.values()) == 1.0
    with pytest.raises(RotationInputError, match="negative"):
        normalize_weights({"water_suitability": -1})


def test_editable_weight_profiles_are_valid_and_family_restrictions_are_hard() -> None:
    profiles = json.loads((ROOT / "data" / "priority_weights.json").read_text(encoding="utf-8"))["profiles"]
    for weights in profiles.values():
        assert sum(normalize_weights(weights).values()) == 1.0
    result = ENGINE.generate(profile(blocked_families=frozenset({"Poaceae"})), max_plans=20)
    assert not result.plans
    assert any(check.rule == "farmer_provided_rotation_or_pest_restriction" and check.status == "fail" for check in result.exclusions)


def test_priority_changes_can_change_ranking_when_supported_scores_differ() -> None:
    water_first = ENGINE.generate(profile(priority_weights={"water_suitability": 1}), max_plans=20)
    soil_first = ENGINE.generate(profile(priority_weights={"soil_related_potential": 1}), max_plans=20)

    assert water_first.plans[0].crop_ids == ("maize", "potato", "moong")
    assert soil_first.plans[0].crop_ids == ("cotton", "wheat", "moong")
    assert water_first.plans[0].crop_ids != soil_first.plans[0].crop_ids
