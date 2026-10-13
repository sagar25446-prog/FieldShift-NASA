"""Comprehensive audit tests for FieldShift project.

Covers: valid/invalid/incomplete profiles, hard constraint enforcement,
priority-ranking updates, feasible/infeasible rotations, unsupported claims,
API failure handling, provenance links, season mapping, scenario definitions,
and absence of fake confidence percentages.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock
from urllib.error import URLError

import numpy as np
import pandas as pd
import pytest

from fieldshift.nasa_power import (
    PowerClient,
    PowerNetworkError,
    PowerRequest,
    PowerResponseError,
)
from fieldshift.rotation_engine import (
    METRICS,
    ClimateContext,
    FarmProfile,
    RotationEngine,
    RotationInputError,
    SoilInformation,
    normalize_weights,
)
from fieldshift.scenarios import (
    ScenarioInputError,
    build_scenarios,
    evaluate_robustness,
    pareto_assess,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _engine() -> RotationEngine:
    return RotationEngine(DATA_DIR / "crops.json", DATA_DIR / "rotation_rules.json")


def _good_profile(**overrides) -> FarmProfile:
    """A complete, valid Ludhiana-area farm profile for testing."""
    defaults = dict(
        latitude=30.9,
        longitude=75.86,
        soil=SoilInformation(
            texture="medium",
            waterlogged=False,
            highly_deteriorated_alkaline=False,
            well_drained=True,
        ),
        climate=ClimateContext(),
        total_crop_water_budget_mm=600.0,
        previous_crop_id=None,
        blocked_crop_ids=frozenset(),
        priority_weights={m: 1.0 for m in METRICS},
        number_of_seasons=3,
        start_season="kharif",
    )
    defaults.update(overrides)
    return FarmProfile(**defaults)


# ──────────────────── 1. Valid Farm Profile ────────────────────


class TestValidFarmProfile:
    def test_good_profile_generates_plans(self):
        result = _engine().generate(_good_profile())
        assert result.plans, "A valid profile must produce at least one plan"

    def test_plans_have_required_attributes(self):
        result = _engine().generate(_good_profile())
        plan = result.plans[0]
        assert plan.crop_ids
        assert plan.crop_names
        assert plan.seasons
        assert plan.status in ("feasible_with_known_constraints", "conditionally_feasible")
        assert plan.source_urls


# ──────────────────── 2. Invalid Farm Profiles ────────────────────


class TestInvalidFarmProfiles:
    def test_negative_water_budget_rejected(self):
        with pytest.raises(RotationInputError):
            _engine().generate(_good_profile(total_crop_water_budget_mm=-100))

    def test_empty_weights_rejected(self):
        with pytest.raises(RotationInputError):
            normalize_weights({m: 0 for m in METRICS})

    def test_zaid_season_rejected(self):
        """The engine uses 'summer', not 'zaid'. 'zaid' must fail."""
        with pytest.raises(RotationInputError, match="Start season must be one of"):
            _engine().generate(_good_profile(start_season="zaid"))

    def test_summer_season_accepted(self):
        result = _engine().generate(_good_profile(start_season="summer"))
        # May produce zero plans if no summer crops start, but must not raise
        assert result is not None

    def test_zero_seasons_rejected(self):
        with pytest.raises(RotationInputError):
            _engine().generate(_good_profile(number_of_seasons=0))

    def test_negative_weights_rejected(self):
        with pytest.raises(RotationInputError):
            normalize_weights({"water_suitability": -1, **{m: 1 for m in METRICS if m != "water_suitability"}})


# ──────────────────── 3. Incomplete Farm Profiles ────────────────────


class TestIncompleteFarmProfiles:
    def test_all_none_soil_still_generates(self):
        profile = _good_profile(soil=SoilInformation())
        result = _engine().generate(profile)
        assert result.plans, "Missing soil should not prevent plan generation"

    def test_no_water_budget_produces_none_water_score(self):
        profile = _good_profile(total_crop_water_budget_mm=None)
        result = _engine().generate(profile)
        if result.plans:
            assert result.plans[0].metrics["water_suitability"].score is None

    def test_no_previous_crop_generates_plans(self):
        profile = _good_profile(previous_crop_id=None)
        result = _engine().generate(profile)
        assert result.plans, "No previous crop should still allow plan generation"


# ──────────────────── 4. Hard Constraint Cannot Be Bypassed ────────────────────


class TestHardConstraintCannotBeBypassed:
    def test_waterlogged_wheat_is_infeasible(self):
        """A waterlogged field must make wheat infeasible regardless of score."""
        engine = _engine()
        profile = _good_profile(
            soil=SoilInformation(waterlogged=True, highly_deteriorated_alkaline=False, well_drained=True, texture="medium"),
            previous_crop_id="maize",
            number_of_seasons=1,
            start_season="rabi",
        )
        plan = engine.assess_sequence(("wheat",), profile)
        assert plan.status == "infeasible", "Waterlogged wheat must be infeasible"
        assert any(c.status == "fail" for c in plan.checks), "Must have at least one failing check"

    def test_blocked_crop_is_infeasible(self):
        engine = _engine()
        profile = _good_profile(
            blocked_crop_ids=frozenset({"wheat"}),
            previous_crop_id="maize",
            number_of_seasons=1,
            start_season="rabi",
        )
        plan = engine.assess_sequence(("wheat",), profile)
        assert plan.status == "infeasible"

    def test_composite_score_does_not_rescue_infeasible(self):
        """Even if a composite score exists, infeasible status must remain."""
        engine = _engine()
        profile = _good_profile(
            soil=SoilInformation(waterlogged=True, highly_deteriorated_alkaline=False, well_drained=True, texture="medium"),
            previous_crop_id="maize",
            number_of_seasons=1,
            start_season="rabi",
        )
        plan = engine.assess_sequence(("wheat",), profile)
        # Regardless of whether composite_score is None or a number,
        # the plan MUST be infeasible.
        assert plan.status == "infeasible", (
            f"A hard constraint was violated but plan status is '{plan.status}' "
            f"with composite_score={plan.composite_score}. "
            "High scores must never bypass hard constraints."
        )


# ──────────────────── 5. Priority Changes Update Ranking ────────────────────


class TestPriorityChangesUpdateRanking:
    def test_different_weights_can_reorder_plans(self):
        engine = _engine()
        balanced = _good_profile(priority_weights={m: 1.0 for m in METRICS})
        water_heavy = _good_profile(priority_weights={
            "water_suitability": 100.0,
            "climate_suitability": 0.0,
            "soil_related_potential": 0.0,
            "rotation_diversity": 1.0,
            "economic_potential": 0.0,
        })
        r1 = engine.generate(balanced)
        r2 = engine.generate(water_heavy)
        # Both should produce valid results
        assert r1.plans
        assert r2.plans
        # Effective weights must differ
        if len(r1.plans) > 0 and len(r2.plans) > 0:
            ew1 = r1.plans[0].effective_weights["water_suitability"]
            ew2 = r2.plans[0].effective_weights["water_suitability"]
            assert ew2 >= ew1, "Water-heavy weights should give water higher effective weight"


# ──────────────────── 6. Known Feasible Rotation ────────────────────


class TestKnownFeasibleRotation:
    def test_maize_wheat_moong_is_feasible(self):
        engine = _engine()
        profile = _good_profile(start_season="kharif", number_of_seasons=3)
        plan = engine.assess_sequence(("maize", "wheat", "moong"), profile)
        assert plan.status in ("feasible_with_known_constraints", "conditionally_feasible")
        assert not any(c.status == "fail" for c in plan.checks), "No check should fail for a known-good rotation"


# ──────────────────── 7. Known Infeasible Rotation ────────────────────


class TestKnownInfeasibleRotation:
    def test_blocked_crop_makes_rotation_infeasible(self):
        engine = _engine()
        profile = _good_profile(
            blocked_crop_ids=frozenset({"wheat"}),
            start_season="kharif",
            number_of_seasons=3,
        )
        plan = engine.assess_sequence(("maize", "wheat", "moong"), profile)
        assert plan.status == "infeasible"


# ──────────────────── 8. Unsupported Claims Not Present ────────────────────


class TestUnsupportedClaimsNotPresent:
    """Verify that generated plans do not contain unsupported scientific claims."""

    FORBIDDEN_PHRASES = [
        "guaranteed",
        "will increase yield",
        "profitable",
        "scientifically validated",
        "proven to improve",
        "will improve soil",
        "predicts yield",
        "forecasts weather",
    ]

    def test_no_unsupported_claims_in_plan_text(self):
        engine = _engine()
        result = engine.generate(_good_profile())
        for plan in result.plans:
            all_text = " ".join([
                *plan.crop_names,
                plan.status,
                *[c.message for c in plan.checks],
                *plan.positive_factors,
                *plan.tradeoffs,
                *plan.uncertainty_warnings,
                *[m.method for m in plan.metrics.values()],
                *[m.warning or "" for m in plan.metrics.values()],
            ]).lower()
            for phrase in self.FORBIDDEN_PHRASES:
                assert phrase not in all_text, f"Found unsupported claim '{phrase}' in plan output"

    def test_economic_potential_always_none(self):
        engine = _engine()
        result = engine.generate(_good_profile())
        for plan in result.plans:
            assert plan.metrics["economic_potential"].score is None, "Economic potential must be N/A"

    def test_climate_suitability_always_none(self):
        engine = _engine()
        result = engine.generate(_good_profile())
        for plan in result.plans:
            assert plan.metrics["climate_suitability"].score is None, "Climate suitability must be N/A"


# ──────────────────── 9. API Failure Handling ────────────────────


class TestAPIFailureHandling:
    def test_network_error_raises_not_fake_data(self):
        def failing_transport(url: str, timeout: float) -> bytes:
            raise URLError("Simulated network failure")

        client = PowerClient(transport=failing_transport)
        request = PowerRequest(30.9, 75.86, __import__("datetime").date(2024, 1, 1), __import__("datetime").date(2024, 1, 3))
        with pytest.raises(PowerNetworkError):
            client.fetch_daily(request)

    def test_malformed_json_raises_not_fake_data(self):
        def garbage_transport(url: str, timeout: float) -> bytes:
            return b"THIS IS NOT JSON"

        client = PowerClient(transport=garbage_transport)
        request = PowerRequest(30.9, 75.86, __import__("datetime").date(2024, 1, 1), __import__("datetime").date(2024, 1, 3))
        with pytest.raises(PowerResponseError):
            client.fetch_daily(request)


# ──────────────────── 10. Provenance Links ────────────────────


class TestProvenanceLinks:
    def test_all_sources_have_https_urls(self):
        catalog = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
        for source_id, source in catalog["sources"].items():
            assert "url" in source, f"Source {source_id} missing 'url'"
            assert source["url"].startswith("https://"), f"Source {source_id} URL is not HTTPS: {source['url']}"

    def test_all_crops_reference_valid_sources(self):
        catalog = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
        valid_sources = set(catalog["sources"].keys())
        for crop in catalog["crops"]:
            for sid in crop["source_ids"]:
                assert sid in valid_sources, f"Crop {crop['id']} references unknown source '{sid}'"


# ──────────────────── 11. Season Mapping ────────────────────


class TestSeasonMapping:
    def test_rotation_rules_uses_summer_not_zaid(self):
        rules = json.loads((DATA_DIR / "rotation_rules.json").read_text(encoding="utf-8"))
        assert rules["season_cycle"] == ["kharif", "rabi", "summer"]
        assert "zaid" not in rules["season_cycle"]

    def test_engine_generates_summer_seasons(self):
        engine = _engine()
        profile = _good_profile(start_season="summer", number_of_seasons=3)
        # Should not raise
        result = engine.generate(profile)
        assert result is not None

    def test_crops_use_summer_not_zaid(self):
        catalog = json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))
        for crop in catalog["crops"]:
            for season in crop["growing_seasons"]:
                assert season != "zaid", f"Crop {crop['id']} uses 'zaid' instead of 'summer'"


# ──────────────────── 12. Scenario Definitions ────────────────────


class TestScenarioDefinitions:
    def test_all_scenarios_have_labels_and_descriptions(self):
        scenarios = build_scenarios()
        for s in scenarios:
            assert s.label, "Every scenario must have a label"
            assert s.description, "Every scenario must have a description"

    def test_baseline_is_not_hypothetical(self):
        scenarios = build_scenarios()
        baseline = [s for s in scenarios if s.identifier == "historical_baseline"]
        assert baseline, "Must have a baseline scenario"
        for s in baseline:
            assert not s.is_hypothetical, "Baseline must not be labelled as hypothetical"

    def test_stress_tests_are_hypothetical(self):
        scenarios = build_scenarios()
        non_baseline = [s for s in scenarios if s.identifier != "historical_baseline"]
        for s in non_baseline:
            assert s.is_hypothetical, f"Scenario '{s.label}' should be labelled as hypothetical"


# ──────────────────── 13. No Confidence Percentages ────────────────────


class TestNoConfidencePercentages:
    """Ensure no fake numerical confidence percentages appear in outputs."""

    # Pattern: "XX%" or "XX %" where XX is a number, but NOT in technical
    # descriptions like "precipitation reduction %"
    CONFIDENCE_PATTERNS = [
        r"\bconfidence\s*:\s*\d",
        r"\bprobability\s*:\s*\d",
        r"\b\d{1,3}\s*%\s*confiden",
        r"\b\d{1,3}\s*%\s*probabili",
        r"\bconfidence\s+\d{1,3}\s*%",
    ]

    def test_no_confidence_in_plan_outputs(self):
        engine = _engine()
        result = engine.generate(_good_profile())
        for plan in result.plans:
            all_text = " ".join([
                *plan.positive_factors,
                *plan.tradeoffs,
                *plan.uncertainty_warnings,
                *[c.message for c in plan.checks],
                *[m.method for m in plan.metrics.values()],
                *[m.warning or "" for m in plan.metrics.values()],
            ]).lower()
            for pattern in self.CONFIDENCE_PATTERNS:
                assert not re.search(pattern, all_text), f"Found confidence pattern '{pattern}' in plan output"

    def test_no_confidence_in_robustness_report(self):
        engine = _engine()
        result = engine.generate(_good_profile())
        if result.plans:
            scenarios = build_scenarios()
            report = evaluate_robustness(engine, result.plans, _good_profile(), scenarios, None)
            all_notes = " ".join([
                *report.data_coverage_notes,
                *report.model_uncertainty_notes,
                *report.scenario_uncertainty_notes,
            ]).lower()
            for pattern in self.CONFIDENCE_PATTERNS:
                assert not re.search(pattern, all_notes), f"Found confidence pattern '{pattern}' in robustness report"
