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
