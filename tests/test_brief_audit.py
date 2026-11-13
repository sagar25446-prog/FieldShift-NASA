"""Regression cases discovered while reviewing the full challenge brief."""
from pathlib import Path

import pytest

from fieldshift.rotation_engine import (
    ClimateContext, FarmProfile, RotationEngine, RotationInputError,
    SoilInformation, normalize_weights,
)
from fieldshift.strategy_comparison import compare_existing_rotation
from fieldshift.scenarios import build_scenarios, evaluate_robustness
from fieldshift.export_import import generate_farmer_summary_card_html

ROOT = Path(__file__).resolve().parents[1]


def engine_and_profile():
    engine = RotationEngine(ROOT / "data/crops.json", ROOT / "data/rotation_rules.json")
    profile = FarmProfile(30.85, 75.70, SoilInformation(), ClimateContext(), 600, None,
                          priority_weights={"water_suitability": .5, "rotation_diversity": .5})
    return engine, profile


def test_existing_rotation_is_retained_even_when_water_constraint_fails():
    engine, profile = engine_and_profile()
    alternatives = engine.generate(profile).plans
    strategies = compare_existing_rotation(engine, profile, ("rice", "wheat", "moong"), alternatives)
    assert len(strategies) >= 3
    assert strategies[0].is_current
    assert strategies[0].plan.status == "infeasible"
    assert any(c.rule == "documented_water_requirement" and c.status == "fail" for c in strategies[0].plan.checks)
    assert all(s.plan.status != "infeasible" for s in strategies[1:])


def test_existing_sequence_is_not_duplicated_and_scores_recompute_with_priorities():
    engine, profile = engine_and_profile()
    alternatives = engine.generate(profile).plans
    current = alternatives[0].crop_ids
    result = compare_existing_rotation(engine, profile, current, alternatives)
    assert len({s.plan.crop_ids for s in result}) == len(result)
    assert result == compare_existing_rotation(engine, profile, current, alternatives)
    assert result[0].plan.status == "conditionally_feasible"
    profile.priority_weights = {"rotation_diversity": 1}
    changed = compare_existing_rotation(engine, profile, current, alternatives)
    assert all(s.plan.effective_weights["rotation_diversity"] == 1 for s in changed)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_priorities_are_rejected(value):
    with pytest.raises(RotationInputError):
        normalize_weights({"water_suitability": value})


def test_scenario_deltas_do_not_depend_on_baseline_order():
    engine, profile = engine_and_profile()
    plans = engine.generate(profile).plans[:1]
    scenarios = build_scenarios(irrigation_reduction_pct=50)
    normal = evaluate_robustness(engine, plans, profile, scenarios)
    reordered = evaluate_robustness(engine, plans, profile, tuple(reversed(scenarios)))
    expected = {o.scenario.identifier: o.score_changes_from_baseline for o in normal.outcomes[plans[0].crop_ids]}
    assert {o.scenario.identifier: o.score_changes_from_baseline for o in reordered.outcomes[plans[0].crop_ids]} == expected


def test_export_keeps_unknowns_and_does_not_claim_unretrieved_satellite_data():
    card = generate_farmer_summary_card_html({}, ["Unknown crop"], ["summer"])
    assert "Score unavailable" in card
    assert "Unknown; local review needed" in card
    assert "NASA POWER request not attached" in card
    assert "NASA SMAP" not in card and "NASA GRACE" not in card
    assert "+ Legume Credit" not in card


def test_current_rotation_comparison_returns_current_and_distinct_alternatives():
    engine, profile = engine_and_profile()
    strategies = compare_existing_rotation(engine, profile, ("rice", "wheat", "moong"), engine.generate(profile).plans)
    assert strategies[0].label == "Your current rotation"
    assert len({strategy.plan.crop_ids for strategy in strategies}) == len(strategies)
