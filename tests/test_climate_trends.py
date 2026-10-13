"""Tests for observed historical climate-trend analysis.

Verifies:
1. Date coverage and parameter completeness auditing.
2. Annual growing-season summaries across single-year (Kharif) and cross-year (Rabi) cycles.
3. Missing days and incomplete season warning handling.
4. Deterministic linear trend calculation on the genuine 2000–2024 NASA POWER record, checked against an
   independent least-squares fit (the fixture is an unmodified API response saved 2026-10-13).
5. Baseline period vs. recent period comparison and delta calculation.
6. Units, slope scaling, and statistical boundary warnings.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.climate_trends import (
    REGIONAL_SEASONS,
    AnnualSeasonSummary,
    SeasonDefinition,
    TrendAnalysisResult,
    analyze_all_season_trends,
    audit_variable_coverage,
    calculate_linear_trend,
    compute_annual_season_summaries,
)
from fieldshift.nasa_power import PowerRequest, parse_power_daily_response

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "power_daily_ludhiana_historical_2000_2024.json"
)


@pytest.fixture(scope="module")
def historical_dataset():
    """Load the unmodified 2000–2024 NASA POWER daily response for the demo farm (30.85 N, 75.70 E)."""
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    req = PowerRequest(30.85, 75.70, date(2000, 1, 1), date(2024, 12, 31), parameters=tuple(payload["properties"]["parameter"]))
    return parse_power_daily_response(payload, req, "https://power.example/historical_2000_2024")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Date Coverage & Completeness Auditing Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestVariableCoverageAudit:
    """Test parameter-level date coverage, observation counts, and completeness."""

    def test_coverage_audit_reports_all_parameters(self, historical_dataset) -> None:
        coverage = audit_variable_coverage(historical_dataset.data)

        expected_params = {"T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"}
        assert expected_params.issubset(coverage.keys())

        t2m_cov = coverage["T2M"]
        assert t2m_cov.first_date == "2000-01-01"
        assert t2m_cov.last_date == "2024-12-31"
        assert t2m_cov.total_calendar_days == 9132
        # The genuine response contains no fill values for this point and period.
        assert t2m_cov.missing_observations == 0
        assert t2m_cov.completeness_percent == 100.0
        assert t2m_cov.is_sufficient_for_trends is True
        assert t2m_cov.unit == "°C"

    def test_empty_dataframe_returns_empty_coverage(self) -> None:
        empty_df = pd.DataFrame()
        assert audit_variable_coverage(empty_df) == {}

    def test_parameter_with_insufficient_span_is_flagged(self) -> None:
        # 1 year only
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        short_df = pd.DataFrame({"T2M": [20.0] * 100}, index=dates)
        cov = audit_variable_coverage(short_df)
        assert cov["T2M"].is_sufficient_for_trends is False
        assert "Insufficient record" in cov["T2M"].notes


# ─────────────────────────────────────────────────────────────────────────────
# 2. Annual Growing-Season Aggregation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAnnualSeasonSummaries:
    """Test annual aggregation for defined regional growing seasons."""

    def test_kharif_season_aggregation(self, historical_dataset) -> None:
        kharif = REGIONAL_SEASONS["kharif"]
        summaries = compute_annual_season_summaries(historical_dataset.data, season=kharif)

        # 25 years: 2000 through 2024
        assert len(summaries) == 25
        assert summaries[0].year == 2000
        assert summaries[-1].year == 2024

        first_s = summaries[0]
        # June 1 to October 31 is 153 days
        assert first_s.expected_days == 153
        assert first_s.valid_days == 153
        assert first_s.completeness_pct == 100.0
        assert first_s.is_valid is True
        assert first_s.mean_temp_c is not None
        assert first_s.total_precip_mm is not None
        assert first_s.dry_spell_max_days is not None

    def test_rabi_cross_year_season_aggregation(self, historical_dataset) -> None:
        rabi = REGIONAL_SEASONS["rabi"]
        assert rabi.is_cross_year is True
        summaries = compute_annual_season_summaries(historical_dataset.data, season=rabi)

        # 24 complete cross-year seasons (2000–01 through 2023–24)
        # plus 1 incomplete trailing season (2024–25, which only has Nov–Dec in the 2024 dataset)
        assert len(summaries) == 25
        valid_seasons = [s for s in summaries if s.is_valid]
        assert len(valid_seasons) == 24
        assert summaries[0].season_label == "2000–01"
        assert summaries[0].start_date == "2000-11-01"
        assert summaries[0].end_date == "2001-04-30"
        assert summaries[-1].season_label == "2024–25"
        assert summaries[-1].is_valid is False
        assert any("excluded from primary trend line" in w for w in summaries[-1].warnings)

    def test_incomplete_season_detects_missing_days_and_warns(self, historical_dataset) -> None:
        kharif = REGIONAL_SEASONS["kharif"]
        # The test creates its own gap in a copy; the fixture itself is never altered.
        frame = historical_dataset.data.copy()
        frame.loc["2012-06-01":"2012-06-16", :] = float("nan")
        summaries = compute_annual_season_summaries(frame, season=kharif)

        s_2012 = next(s for s in summaries if s.year == 2012)
        assert s_2012.missing_days == 16
        assert s_2012.valid_days == 153 - 16
        assert s_2012.completeness_pct == round((137 / 153) * 100, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Linear Trend Calculation & Statistical Verification Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestLinearTrendCalculation:
    """Test OLS regression, change per decade, and statistical significance."""

    def test_known_synthetic_trend_reproduces_exact_slope(self) -> None:
        # Linear sequence: starts at 20.0, increases by 0.05 per year for 20 years
        years = list(range(2000, 2020))
        values = [20.0 + 0.05 * (y - 2000) for y in years]

        res = calculate_linear_trend(years, values, "temp", "Temperature", "°C")

        assert res.valid_years == 20
        assert pytest.approx(res.slope_per_year, rel=1e-3) == 0.050
        assert pytest.approx(res.change_per_decade, rel=1e-3) == 0.500
        assert pytest.approx(res.total_change, rel=1e-3) == 0.050 * 19
        assert res.r_squared == 1.0
        assert res.p_value is not None and res.p_value < 0.0001
        assert res.is_significant is True

    def test_known_historical_fixture_trend(self, historical_dataset) -> None:
        kharif = REGIONAL_SEASONS["kharif"]
        trends = analyze_all_season_trends(historical_dataset.data, season=kharif)

        temp_trend = trends["mean_temperature"]
        assert temp_trend.valid_years == 25
        assert temp_trend.unit == "°C"
        # Independent check: ordinary least squares on the seasonal means.
        summaries = [s for s in compute_annual_season_summaries(historical_dataset.data, season=kharif) if s.is_valid]
        slope = np.polyfit([s.year for s in summaries], [s.mean_temp_c for s in summaries], 1)[0]
        assert temp_trend.change_per_decade == pytest.approx(slope * 10, abs=1e-3)  # module rounds to 3 dp
        # Recorded result for this genuine record (saved 2026-10-13): kharif mean T2M
        # declined by about 0.78 °C/decade at this POWER grid cell (p ≈ 0.0025).
        assert temp_trend.change_per_decade == pytest.approx(-0.782, abs=0.005)
        assert temp_trend.p_value is not None and temp_trend.p_value < 0.01
        assert temp_trend.is_significant is True

        # Baseline vs Recent comparison
        assert temp_trend.baseline_mean is not None
        assert temp_trend.recent_mean is not None
        assert temp_trend.delta_vs_baseline is not None
        assert temp_trend.delta_vs_baseline < 0.0  # recent kharif seasons were cooler in this record

    def test_insufficient_data_returns_honest_warning(self) -> None:
        # Only 2 data points
        res = calculate_linear_trend([2020, 2021], [25.0, 26.0], "t", "T", "°C")
        assert res.slope_per_year is None
        assert res.is_significant is False
        assert any("at least 3" in w.lower() or "insufficient" in w.lower() for w in res.warnings)

    def test_scientific_boundary_warnings_present(self, historical_dataset) -> None:
        kharif = REGIONAL_SEASONS["kharif"]
        trends = analyze_all_season_trends(historical_dataset.data, season=kharif)
        res = trends["mean_temperature"]
        all_warnings = " ".join(res.warnings).lower()
        assert "descriptive" in all_warnings
        assert "causal" in all_warnings or "yield" in all_warnings
        assert "forecast" in all_warnings


# ─────────────────────────────────────────────────────────────────────────────
# 4. UI Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestClimateTrendsUIIntegration:
    """Verify UI wiring, pages list, and fixture loader."""

    def test_pages_tuple_contains_climate_trends(self) -> None:
        from fieldshift.ui import PAGES
        assert "Climate Trends" in PAGES
        assert PAGES[3] == "Climate Trends"

    def test_fixture_loader_returns_valid_dataset(self) -> None:
        from fieldshift.ui import _load_historical_fixture_dataset
        ds = _load_historical_fixture_dataset()
        assert not ds.data.empty
        assert len(ds.data) == 9132
        assert "T2M" in ds.data.columns
        assert ds.provenance.temporal_resolution == "daily"

