"""Regression tests: each crop is evaluated only on its own growing-season days.

Before this fix the water balance gave every crop the whole year's ET0 and
rainfall (so annual rainfall was counted once per crop), and the thermal
assessment split the record into chronological thirds, giving "kharif" crops
January–April temperatures.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fieldshift.fao56 import CropWaterResult, average_crop_water
from fieldshift.growing_season import crop_duration_days, crop_season_slices
from fieldshift.nasa_power import load_offline_demo_snapshot
from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot() -> pd.DataFrame:
    return load_offline_demo_snapshot().data


@pytest.fixture(scope="module")
def engine() -> RotationEngine:
    return RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")


def _profile(frame: pd.DataFrame) -> FarmProfile:
    return FarmProfile(
        30.901, 75.8573,
        SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False, well_drained=True, texture="medium"),
        ClimateContext(), 800.0, None,
        priority_weights={"water_suitability": 0.5, "climate_suitability": 0.5},
        climate_data=frame,
    )


class TestSeasonSlices:
    def test_kharif_uses_june_onwards_for_crop_duration(self, snapshot: pd.DataFrame) -> None:
        slices = crop_season_slices(snapshot, "kharif", 125)
        assert slices.available and not slices.composite
        frame = slices.occurrences[0].frame
        assert frame.index[0] == pd.Timestamp("2024-06-01") and len(frame) == 125
        assert slices.labels == ("Kharif (Monsoon Summer) 2024",)

    def test_single_year_rabi_is_a_labelled_composite(self, snapshot: pd.DataFrame) -> None:
        slices = crop_season_slices(snapshot, "rabi", 150)
        assert slices.composite
        label = slices.labels[0]
        assert label.startswith("Composite:") and "Nov 2024" in label and "Jan 2024" in label
        frame = slices.occurrences[0].frame
        assert frame.index[0] == pd.Timestamp("2024-11-01") and len(frame) == 150
        assert any("different calendar years" in w for w in slices.warnings)

    def test_multi_year_record_gives_real_occurrences(self) -> None:
        dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
        frame = pd.DataFrame({"T2M_MAX": 30.0, "T2M_MIN": 20.0}, index=dates)
        slices = crop_season_slices(frame, "rabi", 150)
        assert not slices.composite
        assert slices.labels == ("Rabi (Winter / Spring) 2020–21", "Rabi (Winter / Spring) 2021–22", "Rabi (Winter / Spring) 2022–23")

    def test_crop_longer_than_window_is_truncated_with_warning(self, snapshot: pd.DataFrame) -> None:
        slices = crop_season_slices(snapshot, "kharif", 180)
        assert slices.crop_days == slices.window_days == 153
        assert any("longer than" in w for w in slices.warnings)

    def test_insufficient_coverage_is_unavailable(self) -> None:
        frame = pd.DataFrame({"T2M_MAX": 30.0, "T2M_MIN": 20.0}, index=pd.date_range("2024-06-01", periods=30, freq="D"))
        slices = crop_season_slices(frame, "kharif", 125)
        assert not slices.available and slices.warnings

    def test_missing_values_below_coverage_threshold_are_rejected(self, snapshot: pd.DataFrame) -> None:
        holed = snapshot.copy()
        holed.loc["2024-06-01":"2024-06-30", "T2M_MAX"] = float("nan")
        assert not crop_season_slices(holed, "kharif", 125).available

    def test_crop_duration_from_fao56_stage_lengths(self, engine: RotationEngine) -> None:
        assert crop_duration_days(engine.crops["wheat"]) == 150
        assert crop_duration_days({"crop_coefficient": {"status": "unknown"}}) is None


class TestEngineUsesSeasonWindows:
    def test_rainfall_is_not_counted_once_per_crop(self, engine: RotationEngine, snapshot: pd.DataFrame) -> None:
        plan = engine.assess_sequence(("maize", "wheat", "moong"), _profile(snapshot))
        maize, wheat, moong = plan.water_balance.crop_results
        rain = snapshot["PRECTOTCORR"]
        assert maize.total_rainfall_mm == pytest.approx(rain["2024-06-01":"2024-10-03"].sum())  # 125-day maize
        # Composite uses a non-leap reference calendar: 150 days from 1 Nov end on 30 Mar, without 29 Feb.
        wheat_days = rain["2024-11-01":"2024-12-31"].sum() + rain["2024-01-01":"2024-03-30"].sum() - rain["2024-02-29"]
        assert wheat.total_rainfall_mm == pytest.approx(wheat_days)
        assert moong.total_rainfall_mm == pytest.approx(rain["2024-04-01":"2024-06-14"].sum())  # 75-day moong
        # Previously each crop received the full annual total (3 × annual for 3 crops).
        assert maize.total_rainfall_mm + wheat.total_rainfall_mm + moong.total_rainfall_mm < 1.1 * rain.sum()

    def test_et0_differs_by_crop_period(self, engine: RotationEngine, snapshot: pd.DataFrame) -> None:
        plan = engine.assess_sequence(("maize", "wheat", "moong"), _profile(snapshot))
        et0 = [c.et0_total_mm for c in plan.water_balance.crop_results]
        assert len(set(round(v) for v in et0)) == 3
        assert all("climate period" in c.method for c in plan.water_balance.crop_results)
        assert plan.water_balance.crop_results[0].method.endswith("climate period: Kharif (Monsoon Summer) 2024")

    def test_thermal_assessment_uses_seasonal_temperatures(self, engine: RotationEngine, snapshot: pd.DataFrame) -> None:
        plan = engine.assess_sequence(("maize", "wheat", "moong"), _profile(snapshot))
        maize, wheat, _ = plan.climate_assessment.crops
        assert maize.t_mean > 28 > 20 > wheat.t_mean  # monsoon vs winter, not the reverse
        assert maize.climate_period == "Kharif (Monsoon Summer) 2024"
        assert wheat.climate_period.startswith("Composite:")

    def test_heat_days_are_per_season_averages_when_pooled(self, engine: RotationEngine) -> None:
        dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
        hot = pd.DataFrame({"T2M": 33.0, "T2M_MAX": 40.0, "T2M_MIN": 26.0, "PRECTOTCORR": 1.0, "ALLSKY_SFC_SW_DWN": 22.0}, index=dates)
        plan = engine.assess_sequence(("maize", "wheat", "moong"), _profile(hot))
        maize = plan.climate_assessment.crops[0]
        assert maize.seasons_pooled == 4
        assert maize.heat_stress_days == 125  # every day of one 125-day season, not 4 × 125


def test_average_crop_water_keeps_missing_as_missing() -> None:
    a = CropWaterResult("x", "X", "kharif", 500.0, 0.9, 450.0, 100.0, 80.0, 370.0, "m")
    b = CropWaterResult("x", "X", "kharif", 600.0, None, None, 200.0, 160.0, None, "m")
    mean = average_crop_water([a, b], ["2023", "2024"])
    assert mean.et0_total_mm == 550.0 and mean.etc_total_mm is None
    assert "mean of 2 seasons (2023 to 2024)" in mean.method
