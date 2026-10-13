"""Tests for FAO-56 reference evapotranspiration, Kc interpolation, and water balance.

References:
    Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
    Crop evapotranspiration — Guidelines for computing crop water requirements.
    FAO Irrigation and Drainage Paper 56. Rome: FAO.
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from fieldshift.fao56 import (
    CropKc,
    CropWaterResult,
    compute_crop_water,
    compute_et0_daily,
    compute_et0_series,
    compute_rotation_water_balance,
    effective_rainfall_usda_scs,
    estimate_seasonal_effective_rainfall,
)


class TestET0DailyCalculation:
    """Test the daily FAO-56 Penman-Monteith equation implementation."""

    def test_standard_summer_day_et0_reasonable_range(self):
        """A warm, sunny summer day in Ludhiana (lat 30.9 N) should give ET0 around 5-8 mm/day."""
        res = compute_et0_daily(
            t_max=38.0,
            t_min=24.0,
            rs_mj=22.0,
            rh_mean=55.0,
            ws2_m_s=2.5,
            latitude_deg=30.9,
            elevation_m=247.0,
            doy=170,  # mid-June
        )
        assert res.et0_mm is not None
        assert 4.0 <= res.et0_mm <= 9.0
        assert "FAO-56 Penman–Monteith" in res.method

    def test_standard_winter_day_et0_reasonable_range(self):
        """A cool winter day in Ludhiana (lat 30.9 N) should give ET0 around 1-3 mm/day."""
        res = compute_et0_daily(
            t_max=18.0,
            t_min=6.0,
            rs_mj=12.0,
            rh_mean=70.0,
            ws2_m_s=1.5,
            latitude_deg=30.9,
            elevation_m=247.0,
            doy=15,  # mid-January
        )
        assert res.et0_mm is not None
        assert 0.8 <= res.et0_mm <= 3.5

    def test_missing_solar_radiation_returns_none(self):
        """Solar radiation is mandatory for FAO-56 PM; cannot fabricate it."""
        res = compute_et0_daily(
            t_max=30.0,
            t_min=20.0,
            rs_mj=None,
            rh_mean=50.0,
            ws2_m_s=2.0,
            latitude_deg=30.9,
            elevation_m=247.0,
            doy=150,
        )
        assert res.et0_mm is None
        assert any("radiation" in w.lower() for w in res.warnings)

    def test_missing_temperature_returns_none(self):
        """Temperature is mandatory; missing Tmax returns None."""
        res = compute_et0_daily(
            t_max=None,
            t_min=20.0,
            rs_mj=20.0,
            rh_mean=50.0,
            ws2_m_s=2.0,
            latitude_deg=30.9,
            elevation_m=247.0,
            doy=150,
        )
        assert res.et0_mm is None
        assert any("temperature" in w.lower() for w in res.warnings)

    def test_missing_humidity_uses_fao56_tmin_estimation(self):
        """When RH is missing, FAO-56 Eq. 48 estimates ea from Tmin with a warning."""
        res = compute_et0_daily(
            t_max=32.0,
            t_min=18.0,
            rs_mj=20.0,
            rh_mean=None,
            ws2_m_s=2.0,
            latitude_deg=30.9,
            elevation_m=247.0,
            doy=150,
        )
        assert res.et0_mm is not None
        assert any("RH unavailable" in w for w in res.warnings)

    def test_missing_wind_uses_fao56_default_2ms(self):
        """When wind speed is missing, FAO-56 default 2 m/s is used with a warning."""
        res = compute_et0_daily(
            t_max=32.0,
            t_min=18.0,
            rs_mj=20.0,
            rh_mean=60.0,
            ws2_m_s=None,
            latitude_deg=30.9,
            elevation_m=247.0,
            doy=150,
        )
        assert res.et0_mm is not None
        assert any("Wind speed unavailable" in w for w in res.warnings)


class TestET0SeriesCalculation:
    """Test series-level ET0 processing."""

    def test_computes_series_from_valid_dataframe(self):
        dates = pd.date_range("2024-05-01", periods=10, freq="D")
        df = pd.DataFrame({
            "T2M": [28.0] * 10,
            "T2M_MAX": [35.0] * 10,
            "T2M_MIN": [22.0] * 10,
            "ALLSKY_SFC_SW_DWN": [20.0] * 10,
            "PRECTOTCORR": [0.0] * 10,
        }, index=dates)

        res = compute_et0_series(df, latitude_deg=30.9, elevation_m=247.0)
        assert res.valid_days == 10
        assert res.total_et0_mm is not None
        assert res.total_et0_mm > 0
        assert len(res.daily_et0_mm) == 10

    def test_missing_required_column_returns_empty(self):
        dates = pd.date_range("2024-05-01", periods=5, freq="D")
        df = pd.DataFrame({"T2M": [25.0] * 5}, index=dates)  # missing T2M_MAX, ALLSKY...
        res = compute_et0_series(df, latitude_deg=30.9)
        assert res.total_et0_mm is None
        assert res.valid_days == 0
        assert any("Missing required columns" in w for w in res.warnings)


class TestEffectiveRainfall:
    """Test USDA SCS effective rainfall estimation."""

    def test_zero_precipitation_gives_zero_effective(self):
        assert effective_rainfall_usda_scs(0.0) == 0.0

    def test_light_monthly_rainfall_mostly_effective(self):
        # For 50 mm monthly: 50 * (125 - 0.2*50) / 125 = 50 * 115 / 125 = 46.0 mm
        eff = effective_rainfall_usda_scs(50.0)
        assert math.isclose(eff, 46.0, rel_tol=1e-3)

    def test_heavy_monthly_rainfall_diminishing_effectiveness(self):
        # For 300 mm monthly (>250 mm): 125 + 0.1 * 300 = 155.0 mm
        eff = effective_rainfall_usda_scs(300.0)
        assert math.isclose(eff, 155.0, rel_tol=1e-3)
        assert eff < 300.0

    def test_seasonal_rainfall_summary(self):
        dates = pd.date_range("2024-06-01", periods=90, freq="D")
        # 2 mm daily = ~60 mm/month
        series = pd.Series([2.0] * 90, index=dates)
        total, eff = estimate_seasonal_effective_rainfall(series)
        assert total == 180.0
        assert 0 < eff < total


class TestCropKcInterpolation:
    """Test stage-wise crop coefficient interpolation."""

    def test_kc_interpolation_across_stages(self):
        # 20 days initial, 30 days dev, 40 days mid, 20 days late = 110 days total
        kc = CropKc(
            kc_ini=0.30, kc_mid=1.15, kc_end=0.40,
            stage_days_ini=20, stage_days_dev=30, stage_days_mid=40, stage_days_late=20,
            source="Test FAO-56",
        )
        assert kc.total_days == 110
        # Initial stage
        assert kc.kc_for_day(5) == 0.30
        assert kc.kc_for_day(19) == 0.30
        # Mid stage
        assert kc.kc_for_day(60) == 1.15
        # Late/end stage
        assert math.isclose(kc.kc_for_day(109), 0.40, abs_tol=0.05)
        # Development stage interpolation
        val_dev = kc.kc_for_day(35)  # halfway through 30-day dev stage
        assert 0.30 < val_dev < 1.15


class TestWaterBalanceAndScoring:
    """Test aggregation of crop water into rotation water balance."""

    def test_surplus_rainfall_gives_perfect_score(self):
        """When effective rainfall exceeds ETc, water score is 1.0 (no deficit)."""
        cr = CropWaterResult(
            crop_id="wheat", crop_name="Wheat", season="rabi",
            et0_total_mm=300.0, kc_weighted_mean=0.8, etc_total_mm=240.0,
            total_rainfall_mm=350.0, effective_rainfall_mm=260.0,
            net_irrigation_requirement_mm=0.0,
            method="FAO-56",
        )
        wb = compute_rotation_water_balance([cr], farmer_budget_mm=None)
        assert wb.climate_water_score == 1.0
        assert wb.total_net_irrigation_mm == 0.0

    def test_water_deficit_without_budget_scores_rainfall_fraction(self):
        """Without farmer budget, score is the ratio of effective rainfall to demand."""
        cr = CropWaterResult(
            crop_id="maize", crop_name="Maize", season="kharif",
            et0_total_mm=500.0, kc_weighted_mean=0.8, etc_total_mm=400.0,
            total_rainfall_mm=250.0, effective_rainfall_mm=200.0,
            net_irrigation_requirement_mm=200.0,
            method="FAO-56",
        )
        wb = compute_rotation_water_balance([cr], farmer_budget_mm=None)
        # 200 mm effective rain / 400 mm demand = 0.50
        assert math.isclose(wb.climate_water_score, 0.50, abs_tol=1e-2)

    def test_farmer_budget_covers_deficit(self):
        """When farmer budget fully covers NIR, water score reaches 1.0."""
        cr = CropWaterResult(
            crop_id="maize", crop_name="Maize", season="kharif",
            et0_total_mm=500.0, kc_weighted_mean=0.8, etc_total_mm=400.0,
            total_rainfall_mm=250.0, effective_rainfall_mm=200.0,
            net_irrigation_requirement_mm=200.0,
            method="FAO-56",
        )
        # Budget 250 mm >= 200 mm deficit -> full coverage
        wb = compute_rotation_water_balance([cr], farmer_budget_mm=250.0)
        assert wb.climate_water_score == 1.0

    def test_insufficient_budget_partial_score(self):
        """Partial budget raises score proportionally above rain coverage."""
        cr = CropWaterResult(
            crop_id="maize", crop_name="Maize", season="kharif",
            et0_total_mm=500.0, kc_weighted_mean=0.8, etc_total_mm=400.0,
            total_rainfall_mm=250.0, effective_rainfall_mm=200.0,
            net_irrigation_requirement_mm=200.0,
            method="FAO-56",
        )
        # Budget 100 mm covers half of 200 mm deficit
        wb = compute_rotation_water_balance([cr], farmer_budget_mm=100.0)
        assert 0.50 < wb.climate_water_score < 1.0
