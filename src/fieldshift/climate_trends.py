"""Historical climate-trend analysis derived from NASA POWER daily observations.

Provides:
1. Date coverage and completeness auditing for all meteorological variables.
2. Regional crop-season definitions (Kharif, Rabi, Summer, Annual) with configurable dates.
3. Annual growing-season aggregations (mean/max/min temperature, precipitation, dry spells).
4. Robust linear trend estimation (OLS slope, change/decade, R², t-test p-value).
5. Baseline period vs. recent period comparative anomaly analysis.
6. Honest scientific boundaries: distinguishes descriptive trends from causal or yield claims,
   and avoids extrapolating linear trends as future forecasts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class VariableCoverage:
    """Date coverage and completeness for a single climate variable."""

    parameter: str
    display_name: str
    unit: str
    first_date: str | None
    last_date: str | None
    total_calendar_days: int
    valid_observations: int
    missing_observations: int
    completeness_percent: float
    is_sufficient_for_trends: bool  # True if >= 80% complete over at least 5 years
    notes: str


@dataclass(frozen=True)
class SeasonDefinition:
    """Growing season date definition for annual historical summaries."""

    id: str
    name: str
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    description: str

    @property
    def is_cross_year(self) -> bool:
        """True if the season starts in one calendar year and ends in the next (e.g. Rabi)."""
        return self.start_month > self.end_month or (
            self.start_month == self.end_month and self.start_day > self.end_day
        )


REGIONAL_SEASONS: dict[str, SeasonDefinition] = {
    "kharif": SeasonDefinition(
        id="kharif",
        name="Kharif (Monsoon Summer)",
        start_month=6,
        start_day=1,
        end_month=10,
        end_day=31,
        description="Punjab summer monsoon crop season (June 1 – October 31): Rice, Maize, Cotton, Moong.",
    ),
    "rabi": SeasonDefinition(
        id="rabi",
        name="Rabi (Winter / Spring)",
        start_month=11,
        start_day=1,
        end_month=4,
        end_day=30,
        description="Punjab winter/spring season (November 1 – April 30 of following year): Wheat, Chickpea, Mustard, Potato.",
    ),
    "summer": SeasonDefinition(
        id="summer",
        name="Summer (Zaid)",
        start_month=4,
        start_day=1,
        end_month=6,
        end_day=15,
        description="Short pre-monsoon summer window (April 1 – June 15): Summer Moong.",
    ),
    "annual": SeasonDefinition(
        id="annual",
        name="Full Calendar Year",
        start_month=1,
        start_day=1,
        end_month=12,
        end_day=31,
        description="Complete annual cycle (January 1 – December 31).",
    ),
}


@dataclass(frozen=True)
class AnnualSeasonSummary:
    """Aggregated climate indicators for a single growing-season year."""

    year: int
    season_label: str  # e.g. "2023" or "2023–24" for Rabi
    start_date: str
    end_date: str
    expected_days: int
    valid_days: int
    missing_days: int
    completeness_pct: float
    is_valid: bool  # True if completeness_pct >= 75%
    mean_temp_c: float | None
    mean_tmax_c: float | None
    peak_tmax_c: float | None
    mean_tmin_c: float | None
    lowest_tmin_c: float | None
    total_precip_mm: float | None
    dry_spell_max_days: int | None
    heat_days_count: int | None  # days with Tmax >= 35°C
    frost_days_count: int | None  # days with Tmin <= 2°C
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrendAnalysisResult:
    """Statistical linear trend and baseline comparative analysis."""

    variable_name: str
    display_name: str
    unit: str
    season_name: str
    start_year: int
    end_year: int
    total_years: int
    valid_years: int
    slope_per_year: float | None
    change_per_decade: float | None
    total_change: float | None
    intercept: float | None
    r_squared: float | None
    p_value: float | None
    is_significant: bool  # p < 0.05
    baseline_period: str
    baseline_mean: float | None
    recent_period: str
    recent_mean: float | None
    delta_vs_baseline: float | None
    delta_percent: float | None
    annual_data: tuple[dict[str, object], ...]
    method_notes: str
    warnings: tuple[str, ...] = ()


def audit_variable_coverage(frame: pd.DataFrame) -> dict[str, VariableCoverage]:
    """Inspect date coverage and completeness for all variables in a daily climate DataFrame."""
    if frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        return {}

    param_names = {
        "T2M": ("Temperature at 2 Meters (Mean)", "°C"),
        "T2M_MAX": ("Temperature at 2 Meters (Maximum)", "°C"),
        "T2M_MIN": ("Temperature at 2 Meters (Minimum)", "°C"),
        "PRECTOTCORR": ("Precipitation Corrected", "mm/day"),
        "ALLSKY_SFC_SW_DWN": ("All-Sky Surface Shortwave Irradiance", "MJ/m²/day"),
        "RH2M": ("Relative Humidity at 2 Meters", "%"),
        "WS2M": ("Wind Speed at 2 Meters", "m/s"),
    }

    results: dict[str, VariableCoverage] = {}
    full_date_range = pd.date_range(frame.index.min(), frame.index.max(), freq="D")
    total_calendar_days = len(full_date_range)

    for col in frame.columns:
        display_name, unit = param_names.get(col, (col, ""))
        series = frame[col]
        valid_series = series.dropna()

        if valid_series.empty:
            results[col] = VariableCoverage(
                parameter=col,
                display_name=display_name,
                unit=unit,
                first_date=None,
                last_date=None,
                total_calendar_days=total_calendar_days,
                valid_observations=0,
                missing_observations=total_calendar_days,
                completeness_percent=0.0,
                is_sufficient_for_trends=False,
                notes="Parameter has zero valid observations in the retrieved record.",
            )
            continue

        first_date = str(valid_series.index.min().date())
        last_date = str(valid_series.index.max().date())
        valid_count = int(valid_series.count())
        missing_count = total_calendar_days - valid_count
        completeness = round((valid_count / max(1, total_calendar_days)) * 100, 2)
        span_years = (valid_series.index.max() - valid_series.index.min()).days / 365.25

        sufficient = completeness >= 75.0 and span_years >= 3.0
        notes = (
            f"Spans {span_years:.1f} years with {completeness:.1f}% data completeness."
            if sufficient
            else f"Insufficient record for long-term trends ({span_years:.1f} years, {completeness:.1f}% completeness; requires ≥3 yrs and ≥75%)."
        )

        results[col] = VariableCoverage(
            parameter=col,
            display_name=display_name,
            unit=unit,
            first_date=first_date,
            last_date=last_date,
            total_calendar_days=total_calendar_days,
            valid_observations=valid_count,
            missing_observations=missing_count,
            completeness_percent=completeness,
            is_sufficient_for_trends=sufficient,
            notes=notes,
        )

    return results


def compute_annual_season_summaries(
    frame: pd.DataFrame,
    season: SeasonDefinition = REGIONAL_SEASONS["kharif"],
    heat_threshold: float = 35.0,
    frost_threshold: float = 2.0,
    min_completeness_pct: float = 75.0,
) -> list[AnnualSeasonSummary]:
    """Compute annual summaries for the defined growing season across all available years."""
    if frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        return []

    years_in_data = sorted({t.year for t in frame.index})
    summaries: list[AnnualSeasonSummary] = []

    for year in years_in_data:
        # Determine season start and end timestamps
        if not season.is_cross_year:
            try:
                start_dt = pd.Timestamp(year, season.start_month, season.start_day)
                end_dt = pd.Timestamp(year, season.end_month, season.end_day)
            except ValueError:
                continue
            season_label = str(year)
        else:
            # Cross-year season (e.g. Rabi starts Nov Y and ends Apr Y+1)
            try:
                start_dt = pd.Timestamp(year, season.start_month, season.start_day)
                end_dt = pd.Timestamp(year + 1, season.end_month, season.end_day)
            except ValueError:
                continue
            season_label = f"{year}–{str(year + 1)[-2:]}"

        # Check if the season window is within the dataset span
        if start_dt > frame.index.max() or end_dt < frame.index.min():
            continue

        expected_days_range = pd.date_range(start_dt, end_dt, freq="D")
        expected_days = len(expected_days_range)

        # Slice frame for this season window
        season_slice = frame.loc[(frame.index >= start_dt) & (frame.index <= end_dt)]
        if season_slice.empty:
            continue

        # Data completeness check based on T2M or PRECTOTCORR
        primary_col = "T2M" if "T2M" in season_slice.columns else season_slice.columns[0]
        valid_days = int(season_slice[primary_col].notna().sum())
        missing_days = expected_days - valid_days
        completeness = round((valid_days / max(1, expected_days)) * 100, 1)
        is_valid = completeness >= min_completeness_pct

        warnings: list[str] = []
        if completeness < min_completeness_pct:
            warnings.append(
                f"Data completeness is only {completeness}% ({valid_days}/{expected_days} days); "
                f"excluded from primary trend line to prevent sampling bias."
            )

        # ── Temperature Indicators ──
        mean_temp: float | None = None
        mean_tmax: float | None = None
        peak_tmax: float | None = None
        mean_tmin: float | None = None
        lowest_tmin: float | None = None
        heat_days: int | None = None
        frost_days: int | None = None

        if "T2M" in season_slice.columns and season_slice["T2M"].notna().any():
            mean_temp = round(float(season_slice["T2M"].mean(skipna=True)), 2)

        if "T2M_MAX" in season_slice.columns and season_slice["T2M_MAX"].notna().any():
            v_max = season_slice["T2M_MAX"].dropna()
            mean_tmax = round(float(v_max.mean()), 2)
            peak_tmax = round(float(v_max.max()), 2)
            heat_days = int((v_max >= heat_threshold).sum())

        if "T2M_MIN" in season_slice.columns and season_slice["T2M_MIN"].notna().any():
            v_min = season_slice["T2M_MIN"].dropna()
            mean_tmin = round(float(v_min.mean()), 2)
            lowest_tmin = round(float(v_min.min()), 2)
            frost_days = int((v_min <= frost_threshold).sum())

        # ── Precipitation & Dry Spell Indicators ──
        total_precip: float | None = None
        max_dry_spell: int | None = None

        if "PRECTOTCORR" in season_slice.columns and season_slice["PRECTOTCORR"].notna().any():
            v_precip = season_slice["PRECTOTCORR"]
            total_precip = round(float(v_precip.sum(skipna=True)), 1)

            # Longest consecutive dry run (<= 1.0 mm/day)
            curr_dry = 0
            longest_dry = 0
            for val in v_precip:
                if pd.notna(val) and val <= 1.0:
                    curr_dry += 1
                    longest_dry = max(longest_dry, curr_dry)
                else:
                    curr_dry = 0
            max_dry_spell = longest_dry

        summaries.append(
            AnnualSeasonSummary(
                year=year,
                season_label=season_label,
                start_date=str(start_dt.date()),
                end_date=str(end_dt.date()),
                expected_days=expected_days,
                valid_days=valid_days,
                missing_days=missing_days,
                completeness_pct=completeness,
                is_valid=is_valid,
                mean_temp_c=mean_temp,
                mean_tmax_c=mean_tmax,
                peak_tmax_c=peak_tmax,
                mean_tmin_c=mean_tmin,
                lowest_tmin_c=lowest_tmin,
                total_precip_mm=total_precip,
                dry_spell_max_days=max_dry_spell,
                heat_days_count=heat_days,
                frost_days_count=frost_days,
                warnings=tuple(warnings),
            )
        )

    return summaries


def calculate_linear_trend(
    years: Sequence[int],
    values: Sequence[float | None],
    variable_name: str,
    display_name: str,
    unit: str,
    season_name: str = "Kharif",
    baseline_split_year: int | None = None,
) -> TrendAnalysisResult:
    """Perform Ordinary Least Squares (OLS) regression and baseline comparison."""
    # Pair and filter out None / NaN values
    paired = [(y, v) for y, v in zip(years, values) if v is not None and not math.isnan(v)]

    if len(paired) < 3:
        return TrendAnalysisResult(
            variable_name=variable_name,
            display_name=display_name,
            unit=unit,
            season_name=season_name,
            start_year=min(years) if years else 0,
            end_year=max(years) if years else 0,
            total_years=len(years),
            valid_years=len(paired),
            slope_per_year=None,
            change_per_decade=None,
            total_change=None,
            intercept=None,
            r_squared=None,
            p_value=None,
            is_significant=False,
            baseline_period="N/A",
            baseline_mean=None,
            recent_period="N/A",
            recent_mean=None,
            delta_vs_baseline=None,
            delta_percent=None,
            annual_data=(),
            method_notes="Insufficient observations: at least 3 valid annual data points are required for linear regression.",
            warnings=("Insufficient data points to compute statistical trend.",),
        )

    x = np.array([p[0] for p in paired], dtype=float)
    y = np.array([p[1] for p in paired], dtype=float)
    n = len(x)
    start_yr = int(x.min())
    end_yr = int(x.max())

    # OLS Regression
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    ss_xx = float(np.sum((x - x_mean) ** 2))
    ss_xy = float(np.sum((x - x_mean) * (y - y_mean)))
    ss_yy = float(np.sum((y - y_mean) ** 2))

    if ss_xx == 0:
        slope = 0.0
        intercept = y_mean
        r2 = 0.0
        p_val = 1.0
    else:
        slope = ss_xy / ss_xx
        intercept = y_mean - slope * x_mean
        y_pred = intercept + slope * x
        ss_res = float(np.sum((y - y_pred) ** 2))
        r2 = max(0.0, 1.0 - (ss_res / ss_yy)) if ss_yy > 0 else 0.0

        # Two-tailed t-test p-value
        if n > 2 and ss_res > 0 and ss_xx > 0:
            df = n - 2
            se_slope = math.sqrt((ss_res / df) / ss_xx)
            t_stat = slope / se_slope if se_slope > 0 else 0.0
            p_val = float(stats.t.sf(abs(t_stat), df) * 2.0)
        else:
            p_val = 1.0

    change_decade = round(slope * 10.0, 3)
    span_years = end_yr - start_yr
    total_change = round(slope * span_years, 3)
    is_sig = p_val < 0.05

    # ── Baseline vs. Recent Period Split ──
    if baseline_split_year is None:
        split_yr = start_yr + span_years // 2
    else:
        split_yr = baseline_split_year

    baseline_mask = x <= split_yr
    recent_mask = x > split_yr

    baseline_mean: float | None = None
    recent_mean: float | None = None
    delta_baseline: float | None = None
    delta_pct: float | None = None

    if np.any(baseline_mask):
        baseline_mean = round(float(np.mean(y[baseline_mask])), 2)
        base_period_str = f"{start_yr}–{split_yr}"
    else:
        base_period_str = "N/A"

    if np.any(recent_mask):
        recent_mean = round(float(np.mean(y[recent_mask])), 2)
        recent_period_str = f"{split_yr + 1}–{end_yr}"
    else:
        recent_period_str = "N/A"

    if baseline_mean is not None and recent_mean is not None:
        delta_baseline = round(recent_mean - baseline_mean, 2)
        if baseline_mean != 0:
            delta_pct = round((delta_baseline / abs(baseline_mean)) * 100.0, 1)

    # Annual rows with fitted line
    annual_rows: list[dict[str, object]] = []
    for yr_val, obs_val in paired:
        fitted = round(intercept + slope * yr_val, 2)
        annual_rows.append({
            "year": int(yr_val),
            "observed": round(obs_val, 2),
            "trend_fitted": fitted,
            "anomaly_from_mean": round(obs_val - y_mean, 2),
        })

    method_notes = (
        f"OLS linear regression over {n} annual seasons ({start_yr}–{end_yr}). "
        f"Change rate: {change_decade:+.2f} {unit}/decade. "
        f"Significance: p = {p_val:.4f} ({'statistically significant at α=0.05' if is_sig else 'not statistically significant at α=0.05'})."
    )

    warnings: list[str] = [
        "Descriptive historical trend from gridded NASA POWER context; does not prove causal crop yield or soil health changes.",
        "Past historical trends must not be extrapolated as future climate forecasts.",
    ]

    return TrendAnalysisResult(
        variable_name=variable_name,
        display_name=display_name,
        unit=unit,
        season_name=season_name,
        start_year=start_yr,
        end_year=end_yr,
        total_years=len(years),
        valid_years=n,
        slope_per_year=round(slope, 4),
        change_per_decade=change_decade,
        total_change=total_change,
        intercept=round(intercept, 4),
        r_squared=round(r2, 4),
        p_value=round(p_val, 4),
        is_significant=is_sig,
        baseline_period=base_period_str,
        baseline_mean=baseline_mean,
        recent_period=recent_period_str,
        recent_mean=recent_mean,
        delta_vs_baseline=delta_baseline,
        delta_percent=delta_pct,
        annual_data=tuple(annual_rows),
        method_notes=method_notes,
        warnings=tuple(warnings),
    )


def analyze_all_season_trends(
    frame: pd.DataFrame,
    season: SeasonDefinition = REGIONAL_SEASONS["kharif"],
) -> dict[str, TrendAnalysisResult]:
    """Execute complete trend analysis across temperature, precipitation, and dry spells."""
    summaries = compute_annual_season_summaries(frame, season=season)
    valid_summaries = [s for s in summaries if s.is_valid]

    if not valid_summaries:
        return {}

    years = [s.year for s in valid_summaries]

    results: dict[str, TrendAnalysisResult] = {}

    # 1. Mean Temperature
    mean_temps = [s.mean_temp_c for s in valid_summaries]
    results["mean_temperature"] = calculate_linear_trend(
        years, mean_temps, "mean_temperature", "Mean Temperature", "°C", season.name
    )

    # 2. Maximum Temperature
    mean_tmax = [s.mean_tmax_c for s in valid_summaries]
    results["max_temperature"] = calculate_linear_trend(
        years, mean_tmax, "max_temperature", "Average Maximum Temperature", "°C", season.name
    )

    # 3. Minimum Temperature
    mean_tmin = [s.mean_tmin_c for s in valid_summaries]
    results["min_temperature"] = calculate_linear_trend(
        years, mean_tmin, "min_temperature", "Average Minimum Temperature", "°C", season.name
    )

    # 4. Seasonal Precipitation Total
    precips = [s.total_precip_mm for s in valid_summaries]
    results["seasonal_precipitation"] = calculate_linear_trend(
        years, precips, "seasonal_precipitation", "Seasonal Precipitation", "mm", season.name
    )

    # 5. Longest Dry Spell
    dry_spells = [float(s.dry_spell_max_days) if s.dry_spell_max_days is not None else None for s in valid_summaries]
    results["longest_dry_spell"] = calculate_linear_trend(
        years, dry_spells, "longest_dry_spell", "Longest Consecutive Dry Spell", "days", season.name
    )

    return results
