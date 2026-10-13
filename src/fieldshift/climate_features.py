"""Transparent climate summaries derived from NASA POWER daily data.

These functions describe historical climate context; they do not forecast weather,
measure soil chemistry, predict yield, or set crop-specific thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


class FeatureValidationError(ValueError):
    """Raised when a requested indicator cannot be supported by the data."""


@dataclass(frozen=True)
class IndicatorResult:
    """A derived value and the explicit definition used to calculate it."""

    name: str
    value: float
    unit: str
    definition: str
    warning: str | None = None


def _daily_frame(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        raise FeatureValidationError(f"Required parameter {column} is unavailable.")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise FeatureValidationError("Climate data must use a daily DatetimeIndex.")
    series = frame[column].sort_index()
    if series.empty:
        raise FeatureValidationError(f"Parameter {column} has no observations.")
    return series


def seasonal_precipitation_total(frame: pd.DataFrame) -> IndicatorResult:
    """Sum daily corrected precipitation; warn if any day is missing."""
    rainfall = _daily_frame(frame, "PRECTOTCORR")
    missing = int(rainfall.isna().sum())
    if missing == len(rainfall):
        raise FeatureValidationError("Corrected precipitation is missing for every requested day.")
    return IndicatorResult(
        name="seasonal_precipitation_total",
        value=float(rainfall.sum(skipna=True)),
        unit="mm",
        definition="Sum of available daily PRECTOTCORR values over the user-selected date range.",
        warning=f"{missing} day(s) are missing and excluded from this total." if missing else None,
    )


def temperature_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Return monthly average/minimum/maximum summaries from daily 2 m temperatures."""
    required = ("T2M", "T2M_MIN", "T2M_MAX")
    for column in required:
        _daily_frame(frame, column)
    monthly = frame.loc[:, required].resample("MS").agg({"T2M": "mean", "T2M_MIN": "min", "T2M_MAX": "max"})
    monthly.index.name = "month"
    return monthly


def historical_anomaly(current: IndicatorResult, baseline_values: pd.Series, baseline_label: str) -> IndicatorResult:
    """Compare an indicator with an explicit, complete baseline series.

    The caller supplies same-definition historical values (for example, one total per
    season). This avoids silently choosing a baseline or mixing unlike seasons.
    """
    valid = baseline_values.dropna()
    if len(valid) < 2:
        raise FeatureValidationError("At least two complete baseline values are required for an anomaly.")
    baseline_mean = float(valid.mean())
    return IndicatorResult(
        name=f"{current.name}_anomaly",
        value=current.value - baseline_mean,
        unit=current.unit,
        definition=f"Current {current.name} minus mean of {len(valid)} same-definition historical values ({baseline_label}).",
    )


def consecutive_dry_periods(frame: pd.DataFrame, dry_day_max_mm: float) -> pd.DataFrame:
    """List contiguous runs of daily precipitation at or below a declared definition.

    ``dry_day_max_mm`` is an analytical definition chosen by the caller, not a crop
    threshold. Missing days terminate a run because continuity is unknown.
    """
    if dry_day_max_mm < 0:
        raise FeatureValidationError("The dry-day definition must be zero or greater.")
    rainfall = _daily_frame(frame, "PRECTOTCORR")
    expected_days = pd.date_range(rainfall.index.min(), rainfall.index.max(), freq="D")
    rainfall = rainfall.reindex(expected_days)
    runs: list[dict[str, object]] = []
    start: pd.Timestamp | None = None
    last: pd.Timestamp | None = None
    for timestamp, value in rainfall.items():
        is_dry = pd.notna(value) and value <= dry_day_max_mm
        if is_dry:
            start = start or timestamp
            last = timestamp
        elif start is not None and last is not None:
            runs.append({"start_date": start, "end_date": last, "days": (last - start).days + 1, "dry_day_max_mm": dry_day_max_mm})
            start = last = None
    if start is not None and last is not None:
        runs.append({"start_date": start, "end_date": last, "days": (last - start).days + 1, "dry_day_max_mm": dry_day_max_mm})
    return pd.DataFrame(runs, columns=["start_date", "end_date", "days", "dry_day_max_mm"])


def seasonal_temperature_indicators(frame: pd.DataFrame) -> dict[str, IndicatorResult]:
    """Calculate mean, minimum, and maximum temperature indicators for the selected date range."""
    required = ("T2M", "T2M_MIN", "T2M_MAX")
    for column in required:
        _daily_frame(frame, column)

    tmean = frame["T2M"]
    tmin = frame["T2M_MIN"]
    tmax = frame["T2M_MAX"]

    missing_mean = int(tmean.isna().sum())
    missing_min = int(tmin.isna().sum())
    missing_max = int(tmax.isna().sum())

    total_days = len(frame)
    if missing_mean == total_days or missing_min == total_days or missing_max == total_days:
        raise FeatureValidationError("Temperature parameters are missing for every requested day.")

    warn_mean = f"{missing_mean} day(s) missing from mean temperature calculation." if missing_mean else None
    warn_min = f"{missing_min} day(s) missing from minimum temperature calculation." if missing_min else None
    warn_max = f"{missing_max} day(s) missing from maximum temperature calculation." if missing_max else None

    return {
        "mean_temperature": IndicatorResult(
            name="mean_temperature",
            value=float(tmean.mean(skipna=True)),
            unit="degC",
            definition="Mean 2 m air temperature (T2M) over the user-selected date range.",
            warning=warn_mean,
        ),
        "mean_tmin": IndicatorResult(
            name="mean_tmin",
            value=float(tmin.mean(skipna=True)),
            unit="degC",
            definition="Average daily minimum 2 m temperature (T2M_MIN) over the date range.",
            warning=warn_min,
        ),
        "mean_tmax": IndicatorResult(
            name="mean_tmax",
            value=float(tmax.mean(skipna=True)),
            unit="degC",
            definition="Average daily maximum 2 m temperature (T2M_MAX) over the date range.",
            warning=warn_max,
        ),
        "min_temperature_observed": IndicatorResult(
            name="min_temperature_observed",
            value=float(tmin.min(skipna=True)),
            unit="degC",
            definition="Lowest daily minimum 2 m temperature (T2M_MIN) observed.",
            warning=warn_min,
        ),
        "max_temperature_observed": IndicatorResult(
            name="max_temperature_observed",
            value=float(tmax.max(skipna=True)),
            unit="degC",
            definition="Highest daily maximum 2 m temperature (T2M_MAX) observed.",
            warning=warn_max,
        ),
    }


def extreme_temperature_days(
    frame: pd.DataFrame,
    heat_threshold: float | None = None,
    frost_threshold: float | None = None,
) -> dict[str, IndicatorResult]:
    """Calculate the count of days exceeding a heat threshold or dropping below a frost threshold.

    Thresholds are analytical or crop-specific thresholds provided by the caller.
    Do not call this a 'flowering-stage heat-stress count' unless both the flowering period
    and threshold are specifically supported by evidence.
    """
    results: dict[str, IndicatorResult] = {}

    if heat_threshold is not None:
        tmax = _daily_frame(frame, "T2M_MAX")
        missing = int(tmax.isna().sum())
        heat_count = int((tmax >= heat_threshold).sum())
        results["heat_stress_days"] = IndicatorResult(
            name="heat_stress_days",
            value=float(heat_count),
            unit="days",
            definition=f"Number of days where daily maximum temperature (T2M_MAX) reached or exceeded {heat_threshold:.1f} degC.",
            warning=f"{missing} day(s) missing from temperature record." if missing else None,
        )

    if frost_threshold is not None:
        tmin = _daily_frame(frame, "T2M_MIN")
        missing = int(tmin.isna().sum())
        frost_count = int((tmin <= frost_threshold).sum())
        results["frost_stress_days"] = IndicatorResult(
            name="frost_stress_days",
            value=float(frost_count),
            unit="days",
            definition=f"Number of days where daily minimum temperature (T2M_MIN) was at or below {frost_threshold:.1f} degC.",
            warning=f"{missing} day(s) missing from temperature record." if missing else None,
        )

    return results

