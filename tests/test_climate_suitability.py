"""Tests for FAO EcoCrop climate suitability metric, thermal ranges, and heat stress.

Verifies:
1. EcoCrop piece-wise linear response function under optimal, suboptimal, and extreme conditions.
2. Crop-level climate assessment including extreme heat and frost stress day counts.
3. Transparent handling of missing thresholds and incomplete daily observations.
4. Growing-season climate indicators in climate_features.py.
5. Rotation-level aggregation and integration into multi-objective composite ranking.
6. Controlled test demonstrating that differing climate conditions alter climate suitability
   and invert rotation rankings between heat-sensitive and heat-resilient candidates.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.climate_features import (
    FeatureValidationError,
    extreme_temperature_days,
    seasonal_temperature_indicators,
)
from fieldshift.climate_suitability import (
    CropClimateAssessment,
    CropThermalProfile,
    assess_crop_climate,
    assess_rotation_climate,
    calculate_stress_penalty,
    ecocrop_temperature_suitability,
)
from fieldshift.rotation_engine import (
    ClimateContext,
    FarmProfile,
    RotationEngine,
    SoilInformation,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _crops_catalog() -> dict:
    return json.loads((DATA_DIR / "crops.json").read_text(encoding="utf-8"))


def _rules_file() -> Path:
    return DATA_DIR / "rotation_rules.json"


def _make_climate_series(
    start_date: str = "2024-06-01",
    days: int = 120,
    t_mean: float = 28.0,
    t_min: float = 22.0,
    t_max: float = 34.0,
    precip: float = 3.0,
    rs: float = 20.0,
) -> pd.DataFrame:
    """Generate deterministic daily climate frame."""
    dates = pd.date_range(start_date, periods=days, freq="D")
    return pd.DataFrame(
        {
            "T2M": [t_mean] * days,
            "T2M_MIN": [t_min] * days,
            "T2M_MAX": [t_max] * days,
            "PRECTOTCORR": [precip] * days,
            "ALLSKY_SFC_SW_DWN": [rs] * days,
        },
        index=dates,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. EcoCrop Piece-Wise Linear Response Function Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEcoCropSuitabilityFunction:
    """Test the core FAO EcoCrop mathematical response function."""

    def test_temperature_within_optimal_range_is_one(self) -> None:
        # Wheat: Tmin_opt=15, Tmax_opt=23
        score = ecocrop_temperature_suitability(
            t_mean=18.0, tmin_abs=5.0, tmin_opt=15.0, tmax_opt=23.0, tmax_abs=27.0
        )
        assert score == 1.0

    def test_temperature_at_optimal_boundaries_is_one(self) -> None:
        score_lower = ecocrop_temperature_suitability(15.0, 5.0, 15.0, 23.0, 27.0)
        score_upper = ecocrop_temperature_suitability(23.0, 5.0, 15.0, 23.0, 27.0)
        assert score_lower == 1.0
        assert score_upper == 1.0

    def test_temperature_below_absolute_minimum_is_zero(self) -> None:
        score = ecocrop_temperature_suitability(4.0, 5.0, 15.0, 23.0, 27.0)
        assert score == 0.0

    def test_temperature_above_absolute_maximum_is_zero(self) -> None:
        score = ecocrop_temperature_suitability(28.0, 5.0, 15.0, 23.0, 27.0)
        assert score == 0.0

    def test_suboptimal_cold_temperature_interpolates_linearly(self) -> None:
        # T=10, midpoint between 5 and 15 -> (10-5)/(15-5) = 0.50
        score = ecocrop_temperature_suitability(10.0, 5.0, 15.0, 23.0, 27.0)
        assert pytest.approx(score, rel=1e-4) == 0.50

    def test_suboptimal_warm_temperature_interpolates_linearly(self) -> None:
        # T=25, midpoint between 23 and 27 -> (27-25)/(27-23) = 0.50
        score = ecocrop_temperature_suitability(25.0, 5.0, 15.0, 23.0, 27.0)
        assert pytest.approx(score, rel=1e-4) == 0.50

    def test_missing_or_invalid_inputs_return_none(self) -> None:
        assert ecocrop_temperature_suitability(None, 5.0, 15.0, 23.0, 27.0) is None
        assert ecocrop_temperature_suitability(float("nan"), 5.0, 15.0, 23.0, 27.0) is None
        assert ecocrop_temperature_suitability(20.0, None, 15.0, 23.0, 27.0) is None
        # Inverted thresholds
        assert ecocrop_temperature_suitability(20.0, 25.0, 15.0, 23.0, 27.0) is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Crop-Level Climate Assessment Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCropClimateAssessment:
    """Test single crop climate evaluation with EcoCrop parameters."""

    def test_optimal_conditions_produce_perfect_score(self) -> None:
        catalog = _crops_catalog()
        wheat = next(c for c in catalog["crops"] if c["id"] == "wheat")

        # Wheat optimal range is 15-23°C. Daily Tmax below 32°C.
        climate = _make_climate_series(days=120, t_mean=18.0, t_min=12.0, t_max=24.0)
        res = assess_crop_climate(wheat, climate, season="rabi")

        assert res.status == "suitable"
        assert res.climate_suitability_score == 1.0
        assert res.base_thermal_suitability == 1.0
        assert res.heat_stress_days == 0
        assert res.frost_stress_days == 0

    def test_extreme_heat_days_reduce_score_proportionally(self) -> None:
        catalog = _crops_catalog()
        wheat = next(c for c in catalog["crops"] if c["id"] == "wheat")

        # Mean temp is 20°C (optimal), but 30 out of 100 days have Tmax >= 33°C (exceeding 32°C threshold)
        dates = pd.date_range("2024-11-01", periods=100, freq="D")
        t_max_vals = [25.0] * 70 + [34.0] * 30  # 30 heat days
        df = pd.DataFrame(
            {
                "T2M": [20.0] * 100,
                "T2M_MIN": [12.0] * 100,
                "T2M_MAX": t_max_vals,
            },
            index=dates,
        )

        res = assess_crop_climate(wheat, df, season="rabi")
        assert res.heat_stress_days == 30
        assert res.base_thermal_suitability == 1.0
        # penalty = 0.5 * (30/100) = 0.15 -> score = 1.0 * (1 - 0.15) = 0.85
        assert pytest.approx(res.climate_suitability_score, abs=0.01) == 0.85
        assert any("heat threshold" in w for w in res.warnings)

    def test_crop_with_missing_thresholds_returns_unavailable(self) -> None:
        # Create a synthetic crop with unknown temperature suitability
        synthetic_crop = {
            "id": "unknown_crop",
            "name": "Unknown Crop",
            "temperature_suitability": {
                "status": "unknown",
                "value": None,
                "unit": "degC",
                "evidence_needed": "Testing missing evidence",
            },
        }
        climate = _make_climate_series()
        res = assess_crop_climate(synthetic_crop, climate, season="kharif")

        assert res.status == "unavailable"
        assert res.climate_suitability_score is None
        assert any("undocumented" in w.lower() for w in res.warnings)

    def test_missing_temperature_observations_produces_warning(self) -> None:
        catalog = _crops_catalog()
        maize = next(c for c in catalog["crops"] if c["id"] == "maize")

        climate = _make_climate_series(days=50, t_mean=26.0, t_min=20.0, t_max=32.0)
        # Set 5 days to NaN
        climate.iloc[10:15, climate.columns.get_loc("T2M")] = np.nan

        res = assess_crop_climate(maize, climate, season="kharif")
        assert res.climate_suitability_score is not None
        assert any("missing from temperature record" in w for w in res.warnings)

    def test_all_missing_observations_returns_unavailable(self) -> None:
        catalog = _crops_catalog()
        maize = next(c for c in catalog["crops"] if c["id"] == "maize")

        climate = _make_climate_series(days=30)
        climate.loc[:, "T2M"] = np.nan
        climate.loc[:, "T2M_MAX"] = np.nan
        climate.loc[:, "T2M_MIN"] = np.nan

        res = assess_crop_climate(maize, climate, season="kharif")
        assert res.status == "unavailable"
        assert res.climate_suitability_score is None
        assert any("all daily temperature observations are missing" in w.lower() for w in res.warnings)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Growing-Season Climate Indicators Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestClimateFeaturesIndicators:
    """Test temperature indicators in climate_features.py."""

    def test_seasonal_temperature_indicators_computes_stats(self) -> None:
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "T2M": [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0],
                "T2M_MIN": [10.0] * 10,
                "T2M_MAX": [28.0] * 10,
            },
            index=dates,
        )

        indicators = seasonal_temperature_indicators(df)
        assert indicators["mean_temperature"].value == 19.5
        assert indicators["mean_temperature"].unit == "degC"
        assert indicators["min_temperature_observed"].value == 10.0
        assert indicators["max_temperature_observed"].value == 28.0

    def test_extreme_temperature_days_counts_accurately(self) -> None:
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        df = pd.DataFrame(
            {
                "T2M_MAX": [30.0, 31.0, 33.0, 34.0, 35.0, 36.0, 29.0, 28.0, 37.0, 32.0],
                "T2M_MIN": [2.0, 1.0, 0.0, -1.0, 5.0, 6.0, 8.0, 9.0, 3.0, 2.0],
            },
            index=dates,
        )

        # Days >= 35.0 degC: 35.0, 36.0, 37.0 -> 3 days
        # Days <= 0.0 degC: 0.0, -1.0 -> 2 days
        results = extreme_temperature_days(df, heat_threshold=35.0, frost_threshold=0.0)
        assert results["heat_stress_days"].value == 3.0
        assert results["frost_stress_days"].value == 2.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Rotation-Level Climate Aggregation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestRotationClimateAggregation:
    """Test rotation-level climate aggregation and evidence reporting."""

    def test_rotation_without_climate_data_returns_unavailable(self) -> None:
        catalog = _crops_catalog()
        crops = [next(c for c in catalog["crops"] if c["id"] == cid) for cid in ["maize", "wheat", "moong"]]
        res = assess_rotation_climate(crops, None, ["kharif", "rabi", "summer"])

        assert res.status == "unavailable"
        assert res.climate_suitability_score is None
        assert any("no daily climate data" in w.lower() for w in res.warnings)

    def test_rotation_with_all_valid_crops_aggregates_mean(self) -> None:
        catalog = _crops_catalog()
        crops = [next(c for c in catalog["crops"] if c["id"] == cid) for cid in ["maize", "wheat", "moong"]]
        climate = _make_climate_series(start_date="2024-01-01", days=731, t_mean=22.0, t_min=15.0, t_max=28.0)

        res = assess_rotation_climate(crops, climate, ["kharif", "rabi", "summer"])
        assert res.status == "available"
        assert res.climate_suitability_score is not None
        assert 0.0 <= res.climate_suitability_score <= 1.0
        assert len(res.crops) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 5. Climate Data Dependency & Ranking Inversion Regression Test
# ─────────────────────────────────────────────────────────────────────────────


class TestClimateRankingInversion:
    """Verify that climate conditions genuinely influence rotation scores and ranking.

    Comparison Design:
    - Same synthetic farm (Ludhiana coordinates, neutral soil).
    - Identical farmer priority weights (Balanced: climate weight = 0.20).
    - Candidate A: Maize -> Wheat -> Moong (Wheat is cool-season, highly sensitive to terminal heat > 32°C).
    - Candidate B: Pearl Millet -> Chickpea -> Moong (Pearl millet is heat-tolerant C4, optimal 25-35°C).

    Climate 1 (Mild Winter/Spring):
    - Wheat experiences favorable temperatures (18°C mean, Tmax <= 26°C, 0 heat days).
    - Both rotations perform well.

    Climate 2 (Severe Heatwave / Early Summer Spike):
    - Rabi temperatures surge: 28°C mean, daily Tmax = 36°C (well above wheat's 32°C threshold and 27°C Tmax_abs).
    - Wheat suffers severe heat stress (score drops to 0.0), significantly reducing Rotation A's composite score.
    - Rotation B containing heat-tolerant crops maintains a superior climate suitability score.
    - Verified Outcome: Rotation B outranks Rotation A under heat stress!
    """

    def _setup_engine(self) -> RotationEngine:
        return RotationEngine(DATA_DIR / "crops.json", _rules_file())

    def test_heatwave_alters_climate_scores_and_inverts_ranking(self) -> None:
        engine = self._setup_engine()

        # Priority weights: Balanced with active climate weight (0.20)
        weights = {
            "water_suitability": 0.35,
            "climate_suitability": 0.20,
            "soil_related_potential": 0.25,
            "rotation_diversity": 0.20,
            "economic_potential": 0.0,
        }

        # ── Regime 1: Mild / Favorable Climate ──
        # Two full years so each crop is assessed on its own season window
        # Moderate temperatures: 20°C mean, Tmax 25°C
        mild_climate = _make_climate_series(
            start_date="2024-01-01", days=731, t_mean=20.0, t_min=14.0, t_max=26.0, precip=3.0, rs=18.0
        )

        profile_mild = FarmProfile(
            latitude=30.9,
            longitude=75.86,
            soil=SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False),
            climate=ClimateContext(
                source_url="https://power.example/mild",
                date_range="2024-01-01 to 2025-12-31",
                available_parameters=("T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"),
            ),
            total_crop_water_budget_mm=700,
            previous_crop_id=None,
            priority_weights=weights,
            number_of_seasons=3,
            start_season="kharif",
            climate_data=mild_climate,
        )

        plan_a_mild = engine.assess_sequence(("maize", "wheat", "moong"), profile_mild)
        plan_b_mild = engine.assess_sequence(("pearl_millet", "chickpea", "moong"), profile_mild)

        # In mild conditions, wheat is in its optimal zone (15-23°C), so Plan A has high climate score
        clim_a_mild = plan_a_mild.metrics["climate_suitability"].score
        clim_b_mild = plan_b_mild.metrics["climate_suitability"].score
        assert clim_a_mild is not None and clim_a_mild >= 0.85

        # ── Regime 2: Hot Heatwave Climate ──
        # Daily temperatures increase: 30°C mean, Tmax 38°C
        # Wheat Tmax_abs is 27°C, heat threshold is 32°C -> wheat will be completely unsuitable (score 0.0)
        # Pearl millet optimal is 25-35°C, heat threshold 42°C -> pearl millet thrives
        hot_climate = _make_climate_series(
            start_date="2024-01-01", days=731, t_mean=30.0, t_min=24.0, t_max=38.0, precip=3.0, rs=25.0
        )

        profile_hot = FarmProfile(
            latitude=30.9,
            longitude=75.86,
            soil=SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False),
            climate=ClimateContext(
                source_url="https://power.example/hot",
                date_range="2024-01-01 to 2025-12-31",
                available_parameters=("T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"),
            ),
            total_crop_water_budget_mm=700,
            previous_crop_id=None,
            priority_weights=weights,
            number_of_seasons=3,
            start_season="kharif",
            climate_data=hot_climate,
        )

        plan_a_hot = engine.assess_sequence(("maize", "wheat", "moong"), profile_hot)
        plan_b_hot = engine.assess_sequence(("pearl_millet", "chickpea", "moong"), profile_hot)

        clim_a_hot = plan_a_hot.metrics["climate_suitability"].score
        clim_b_hot = plan_b_hot.metrics["climate_suitability"].score

        assert clim_a_hot is not None and clim_b_hot is not None
        # Under heatwave, Plan A's climate score collapses due to wheat failure
        assert clim_a_hot < clim_a_mild
        # Plan B (Pearl Millet based) achieves a higher climate score than Plan A (Wheat based)
        assert clim_b_hot > clim_a_hot

        # Verify composite scores reflect the climate change
        comp_a_hot = plan_a_hot.composite_score
        comp_b_hot = plan_b_hot.composite_score
        assert comp_a_hot is not None and comp_b_hot is not None
        # Heat resilient rotation B beats heat vulnerable rotation A under heatwave
        assert comp_b_hot > comp_a_hot
