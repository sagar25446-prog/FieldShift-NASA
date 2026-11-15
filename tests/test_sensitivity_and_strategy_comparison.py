"""Tests for ranking sensitivity and transparent strategy explanations."""

from pathlib import Path
from types import SimpleNamespace

from src.fieldshift.rotation_engine import FarmProfile, RotationEngine, SoilInformation
from src.fieldshift.sensitivity import RankStabilityReport, evaluate_rank_stability, generate_plain_language_explanation
from src.fieldshift.strategy_comparison import compare_existing_rotation


ROOT = Path(__file__).resolve().parents[1]
ENGINE = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")


def _profile() -> FarmProfile:
    return FarmProfile(
        latitude=30.9010,
        longitude=75.8573,
        soil=SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False),
        climate=None,
        total_crop_water_budget_mm=600.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 0.4, "rotation_diversity": 0.6},
        start_season="kharif",
        number_of_seasons=3,
    )


def test_rank_stability_analysis():
    result = ENGINE.generate(_profile())
    assert result.plans
    report = evaluate_rank_stability(result.plans, {"water_suitability": 0.4, "rotation_diversity": 0.6}, delta_fraction=0.20)
    assert isinstance(report, RankStabilityReport)
    assert 0.0 <= report.stability_percentage <= 100.0
    assert report.total_perturbations_tested > 0
    assert report.baseline_top_plan == result.plans[0].crop_names


def test_plain_language_explanation():
    plan = ENGINE.generate(_profile()).plans[0]
    explanation = generate_plain_language_explanation(plan)
    assert "**Why recommended:**" in explanation


def test_plain_language_explanation_does_not_claim_unmeasured_water_savings():
    plan = SimpleNamespace(
        water_balance=SimpleNamespace(total_net_irrigation_mm=594.0),
        crop_names=("Bajra", "Moong"),
        crop_ids=("bajra", "moong"),
        metrics={"rotation_diversity": SimpleNamespace(score=1.0)},
        climate_assessment=SimpleNamespace(climate_suitability_score=0.85),
    )
    explanation = generate_plain_language_explanation(plan)
    assert "modelled net irrigation deficit of about 594 mm" in explanation
    assert "saves" not in explanation.lower()
    assert "nitrogen contribution depends on local conditions" in explanation


def test_strategy_comparison_uses_plan_evidence_and_discloses_boundaries():
    profile = _profile()
    alternatives = ENGINE.generate(profile).plans
    strategies = compare_existing_rotation(ENGINE, profile, ("rice", "wheat", "moong"), alternatives)
    assert len(strategies) >= 3
    for strategy in strategies:
        assert strategy.why_suggested
        assert strategy.evidence_support
        assert strategy.benefits_offered
        assert strategy.information_gaps
        assert strategy.risks_and_expert_review
        assert "not a prediction" in strategy.pest_break_analysis
        assert "guarantee" not in " ".join(strategy.benefits_offered).lower()
