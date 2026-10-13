"""Regression test proving that NASA POWER climate data materially influences FieldShift rotation rankings.

This test uses two distinct, clearly labelled deterministic climate datasets
(an arid/water-stressed dataset vs. a humid/abundant-rainfall dataset) for the
identical synthetic farm and preferences.

It validates:
1. The calculated water indicators (ET0, effective rain, deficit) change as expected.
2. The water suitability scores depend on those climate-derived indicators.
3. The recommendation ranking changes between the two climate regimes.
4. Removing or replacing NASA-derived climate inputs changes the results.
5. Missing NASA data produces an explicit degraded state rather than fake values.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from fieldshift.fao56 import compute_et0_series
from fieldshift.rotation_engine import (
    ClimateContext,
    FarmProfile,
    RotationEngine,
    SoilInformation,
    METRICS,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _make_engine() -> RotationEngine:
    return RotationEngine(DATA_DIR / "crops.json", DATA_DIR / "rotation_rules.json")


def _make_climate_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate two distinct 120-day climate regimes for Ludhiana (30.9° N)."""
    dates = pd.date_range("2024-06-01", periods=120, freq="D")

    # Dataset A: Arid / High water stress (high heat, high solar radiation, drought)
    arid_data = pd.DataFrame({
        "T2M": [34.0] * 120,
        "T2M_MAX": [41.0] * 120,
        "T2M_MIN": [27.0] * 120,
        "ALLSKY_SFC_SW_DWN": [24.0] * 120,
        "PRECTOTCORR": [0.5] * 120,  # 60 mm total seasonal precipitation
        "RH2M": [40.0] * 120,
        "WS2M": [3.0] * 120,
    }, index=dates)

    # Dataset B: Wet / Abundant monsoon rainfall (moderate heat, low deficit)
    wet_data = pd.DataFrame({
        "T2M": [26.0] * 120,
        "T2M_MAX": [30.0] * 120,
        "T2M_MIN": [22.0] * 120,
        "ALLSKY_SFC_SW_DWN": [14.0] * 120,
        "PRECTOTCORR": [7.5] * 120,  # 900 mm total seasonal precipitation
        "RH2M": [80.0] * 120,
        "WS2M": [1.5] * 120,
    }, index=dates)

    return arid_data, wet_data


def _synthetic_profile(climate_data: pd.DataFrame | None, budget_mm: float = 2300.0) -> FarmProfile:
    """Standard Ludhiana farm profile with identical farmer preferences."""
    weights = {
        "water_suitability": 0.85,
        "rotation_diversity": 0.15,
        "soil_related_potential": 0.0,
        "climate_suitability": 0.0,
        "economic_potential": 0.0,
    }
    return FarmProfile(
        latitude=30.9,
        longitude=75.86,
        soil=SoilInformation(
            texture="medium",
            waterlogged=False,
            highly_deteriorated_alkaline=False,
            well_drained=True,
        ),
        climate=ClimateContext(),
        total_crop_water_budget_mm=budget_mm,
        previous_crop_id=None,
        blocked_crop_ids=frozenset(),
        number_of_seasons=3,
        start_season="kharif",
        priority_weights=weights,
        climate_data=climate_data,
    )


class TestNASADataDependency:
    """Verify that NASA POWER climate inputs materially alter rotation ranking and scores."""

    def test_calculated_water_indicators_differ_between_climates(self):
        """Reference ET0 and precipitation must reflect the differing climate datasets."""
        arid_df, wet_df = _make_climate_datasets()

        et0_arid = compute_et0_series(arid_df, latitude_deg=30.9)
        et0_wet = compute_et0_series(wet_df, latitude_deg=30.9)

        assert et0_arid.total_et0_mm is not None
        assert et0_wet.total_et0_mm is not None
        # Arid climate (hot, sunny, windy) must produce significantly higher ET0 demand
        assert et0_arid.total_et0_mm > et0_wet.total_et0_mm * 1.5

        # Rainfall in wet climate must far exceed arid rainfall
        assert wet_df["PRECTOTCORR"].sum() > arid_df["PRECTOTCORR"].sum() * 10

    def test_scores_depend_on_climate_indicators(self):
        """Water scores for candidate rotations must be lower under arid stress."""
        engine = _make_engine()
        arid_df, wet_df = _make_climate_datasets()

        prof_arid = _synthetic_profile(arid_df, budget_mm=2300.0)
        prof_wet = _synthetic_profile(wet_df, budget_mm=2300.0)

        p_arid = engine.assess_sequence(("rice", "potato", "moong"), prof_arid)
        p_wet = engine.assess_sequence(("rice", "potato", "moong"), prof_wet)

        # Under the wet regime with 900 mm rainfall, water score must be strictly higher
        score_arid = p_arid.metrics["water_suitability"].score
        score_wet = p_wet.metrics["water_suitability"].score

        assert score_arid is not None and score_wet is not None
        assert score_wet > score_arid
        assert p_wet.water_balance.total_net_irrigation_mm < p_arid.water_balance.total_net_irrigation_mm

    def test_recommendation_ranking_changes_between_climates(self):
        """The relative ranking of candidate rotations must invert based on NASA climate data."""
        engine = _make_engine()
        arid_df, wet_df = _make_climate_datasets()

        prof_arid = _synthetic_profile(arid_df, budget_mm=2300.0)
        prof_wet = _synthetic_profile(wet_df, budget_mm=2300.0)

        # Evaluate two feasible rotations with different water demands:
        # Sequence 1: Maize-Wheat-Moong (lower water demand)
        # Sequence 2: Rice-Potato-Moong (higher water demand, higher diversity)
        maize_arid = engine.assess_sequence(("maize", "wheat", "moong"), prof_arid)
        rice_arid = engine.assess_sequence(("rice", "potato", "moong"), prof_arid)

        maize_wet = engine.assess_sequence(("maize", "wheat", "moong"), prof_wet)
        rice_wet = engine.assess_sequence(("rice", "potato", "moong"), prof_wet)

        # 1. Under Arid conditions, Maize-Wheat-Moong ranks HIGHER than Rice-Potato-Moong
        # because Maize stays within the irrigation budget while Rice incurs a deficit.
        assert maize_arid.composite_score > rice_arid.composite_score, (
            f"Expected Maize ({maize_arid.composite_score:.3f}) > Rice ({rice_arid.composite_score:.3f}) under Arid"
        )

        # 2. Under Wet conditions, Rice-Potato-Moong ranks HIGHER than Maize-Wheat-Moong
        # because monsoon rainfall eliminates the deficit, letting Rice-Potato-Moong's diversity win.
        assert rice_wet.composite_score > maize_wet.composite_score, (
            f"Expected Rice ({rice_wet.composite_score:.3f}) > Maize ({maize_wet.composite_score:.3f}) under Wet"
        )

        # 3. In generate(), Rice-Potato-Moong is excluded (dominated) in Arid, but included in Wet
        res_arid = engine.generate(prof_arid)
        res_wet = engine.generate(prof_wet)

        arid_seqs = [p.crop_ids for p in res_arid.plans]
        wet_seqs = [p.crop_ids for p in res_wet.plans]

        assert ("rice", "potato", "moong") not in arid_seqs, "Rice-Potato-Moong should be dominated under drought"
        assert ("rice", "potato", "moong") in wet_seqs, "Rice-Potato-Moong should be non-dominated under wet climate"

    def test_removing_climate_data_changes_ranking_and_falls_back(self):
        """Removing climate data must not silently leave rankings unchanged."""
        engine = _make_engine()
        arid_df, _ = _make_climate_datasets()

        prof_with_climate = _synthetic_profile(arid_df, budget_mm=600.0)
        prof_no_climate = _synthetic_profile(None, budget_mm=600.0)

        res_climate = engine.generate(prof_with_climate)
        res_no_climate = engine.generate(prof_no_climate)

        # With climate data, FAO-56 is used; without climate data, fallback is used
        plan_climate = res_climate.plans[0]
        plan_fallback = res_no_climate.plans[0]

        assert "FAO-56" in plan_climate.metrics["water_suitability"].method
        assert (
            "Fallback" in plan_fallback.metrics["water_suitability"].method
            or "Unavailable" in plan_fallback.metrics["water_suitability"].method
        )

        # Scores must differ
        climate_scores = [p.composite_score for p in res_climate.plans]
        fallback_scores = [p.composite_score for p in res_no_climate.plans]
        assert climate_scores != fallback_scores

    def test_missing_meteorological_inputs_produce_degraded_state(self):
        """Incomplete NASA observations must produce an explicit degraded or unavailable state."""
        dates = pd.date_range("2024-06-01", periods=30, freq="D")
        # Missing solar radiation completely (all NaN)
        incomplete_df = pd.DataFrame({
            "T2M": [30.0] * 30,
            "T2M_MAX": [36.0] * 30,
            "T2M_MIN": [24.0] * 30,
            "ALLSKY_SFC_SW_DWN": [float("nan")] * 30,
            "PRECTOTCORR": [2.0] * 30,
        }, index=dates)

        engine = _make_engine()
        prof_incomplete = _synthetic_profile(incomplete_df, budget_mm=600.0)
        res = engine.generate(prof_incomplete)

        # When ET0 cannot be computed from solar radiation, water score degrades cleanly to fallback
        for plan in res.plans:
            assert plan.water_balance is None or plan.water_balance.total_etc_mm is None
            # Must not fabricate a zero demand
            assert "Fallback" in plan.metrics["water_suitability"].method or plan.metrics["water_suitability"].score is None
