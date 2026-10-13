"""Tests for multi-year rotation simulation module."""

import pytest

from src.fieldshift.multi_year_simulation import (
    simulate_multi_year_rotation,
    MultiYearSimulationReport,
    YearlyStep,
)


def test_simulate_multi_year_rotation_3_years():
    crops = ["maize", "wheat", "moong"]
    report = simulate_multi_year_rotation(
        rotation_crop_ids=crops,
        horizon_years=3,
        initial_soc_percent=0.55,
        candidate_annual_irrigation_mm=1030.0,
        baseline_annual_irrigation_mm=2100.0,
    )

    assert isinstance(report, MultiYearSimulationReport)
    assert report.horizon_years == 3
    assert len(report.yearly_steps) == 3
    assert report.total_water_saved_mm > 0
    # Annual water saved is ~1070 mm per year, so 3 years ~ 3210 mm
    assert report.total_water_saved_mm == pytest.approx(3210.0, abs=10.0)
    assert report.total_water_saved_m3_ha == pytest.approx(report.total_water_saved_mm * 10.0, abs=10.0)

    # Check SOC progression
    step1 = report.yearly_steps[0]
    step3 = report.yearly_steps[2]
    assert isinstance(step1, YearlyStep)
    assert step1.year == 1
    assert step3.year == 3
    assert report.final_soc_percent >= 0.1
    assert "conserves" in report.headline_narrative


def test_simulate_multi_year_rotation_5_years():
    crops = ["corn", "soybean", "cereal_rye"]
    report = simulate_multi_year_rotation(
        rotation_crop_ids=crops,
        horizon_years=5,
        initial_soc_percent=2.80,
        candidate_annual_irrigation_mm=500.0,
        baseline_annual_irrigation_mm=750.0,
    )

    assert report.horizon_years == 5
    assert len(report.yearly_steps) == 5
    assert report.total_water_saved_mm == pytest.approx(1250.0, abs=10.0)
    assert report.yearly_steps[-1].cumulative_water_saved_mm == report.total_water_saved_mm
