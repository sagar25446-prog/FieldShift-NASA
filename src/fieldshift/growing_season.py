"""Select the days of a daily climate record that belong to one crop's growing period.

Both the FAO-56 water balance and the EcoCrop thermal assessment must look at
the same days: the crop's regional season window (``REGIONAL_SEASONS``),
starting on the window's first day and lasting the crop's documented
duration (sum of FAO-56 stage lengths), truncated at the window's end.

Each complete season in the record becomes one *occurrence*; results are
averaged across occurrences. A cross-year season (rabi, Nov–Apr) that is not
fully contained in the record — for example a single calendar year — can be
assembled as a clearly labelled *composite* from the same month-days of the
available record. A composite is never presented as one continuous season.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .climate_trends import REGIONAL_SEASONS


MIN_COVERAGE = 0.9  # share of crop-period days that must be present and valid


@dataclass(frozen=True)
class SeasonOccurrence:
    """The days of one crop period, ordered from the season start."""

    label: str
    frame: pd.DataFrame
    composite: bool


@dataclass(frozen=True)
class CropSeasonSlices:
    season_id: str
    window_description: str
    window_days: int
    crop_days: int
    occurrences: tuple[SeasonOccurrence, ...]
    warnings: tuple[str, ...]

    @property
    def available(self) -> bool:
        return bool(self.occurrences)

    @property
    def composite(self) -> bool:
        return any(item.composite for item in self.occurrences)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(item.label for item in self.occurrences)

    @property
    def summary_label(self) -> str:
        """One readable label: the occurrence itself, or 'N seasons, first–last'."""
        if len(self.occurrences) <= 1:
            return self.labels[0] if self.occurrences else "no complete season"
        first, last = self.occurrences[0].frame.index[0].year, self.occurrences[-1].frame.index[0].year
        name = REGIONAL_SEASONS[self.season_id].name
        return f"{name}: {len(self.occurrences)} seasons starting {first}–{last}"

    def pooled(self) -> pd.DataFrame:
        """All occurrence days stacked (for frequency-based statistics)."""
        if not self.occurrences:
            return pd.DataFrame()
        return pd.concat([item.frame for item in self.occurrences])


def _window_bounds(season_id: str, start_year: int) -> tuple[date, date]:
    season = REGIONAL_SEASONS[season_id]
    start = date(start_year, season.start_month, season.start_day)
    end = date(start_year + (1 if season.is_cross_year else 0), season.end_month, season.end_day)
    return start, end


def _valid_share(frame: pd.DataFrame, required: tuple[str, ...], expected_days: int) -> float:
    if frame.empty or expected_days <= 0:
        return 0.0
    columns = [name for name in required if name in frame.columns]
    if not columns:
        return 0.0
    return float(frame[columns].notna().all(axis=1).sum()) / expected_days


def crop_season_slices(
    frame: pd.DataFrame,
    season_id: str,
    crop_duration_days: int | None,
    required_columns: tuple[str, ...] = ("T2M_MAX", "T2M_MIN"),
    min_coverage: float = MIN_COVERAGE,
) -> CropSeasonSlices:
    """Return every complete crop period in ``frame`` for ``season_id``.

    ``crop_duration_days`` of ``None`` uses the whole season window.
    """
    if season_id not in REGIONAL_SEASONS or season_id == "annual":
        raise ValueError(f"Unknown planning season: {season_id}")
    season = REGIONAL_SEASONS[season_id]
    warnings: list[str] = []
    if frame is None or frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
        return CropSeasonSlices(season_id, season.description, 0, 0, (), ("No daily climate record is available.",))

    # A non-leap reference year keeps window lengths independent of Feb 29.
    ref_start, ref_end = _window_bounds(season_id, 2001)
    window_days = (ref_end - ref_start).days + 1
    crop_days = window_days if not crop_duration_days else min(int(crop_duration_days), window_days)
    if crop_duration_days and crop_duration_days > window_days:
        warnings.append(
            f"Crop duration ({crop_duration_days} days) is longer than the {season.name} window ({window_days} days); "
            f"only the first {window_days} days are counted."
        )

    first, last = frame.index.min().date(), frame.index.max().date()
    occurrences: list[SeasonOccurrence] = []
    for year in range(first.year - 1, last.year + 1):
        start, _ = _window_bounds(season_id, year)
        end = start + timedelta(days=crop_days - 1)
        if start < first or end > last:
            continue
        period = frame.loc[pd.Timestamp(start):pd.Timestamp(end)]
        if _valid_share(period, required_columns, crop_days) >= min_coverage:
            label = f"{season.name} {year}" + (f"–{str(year + 1)[-2:]}" if season.is_cross_year else "")
            occurrences.append(SeasonOccurrence(label, period, composite=False))

    if not occurrences:
        composite = _composite(frame, season_id, crop_days, required_columns, min_coverage)
        if composite is not None:
            occurrences.append(composite)
            warnings.append(
                f"No complete {season.name} season is inside the climate record, so its days were assembled from "
                f"different calendar years ({composite.label}). Treat this as an approximation, not one observed season."
            )
        else:
            warnings.append(f"The climate record does not cover enough of the {season.name} window ({season.description}).")
    return CropSeasonSlices(season_id, season.description, window_days, crop_days, tuple(occurrences), tuple(warnings))


def _composite(
    frame: pd.DataFrame,
    season_id: str,
    crop_days: int,
    required_columns: tuple[str, ...],
    min_coverage: float,
) -> SeasonOccurrence | None:
    """Assemble the crop period from the latest available year of each month-day."""
    ref_start, _ = _window_bounds(season_id, 2001)
    wanted = [ref_start + timedelta(days=offset) for offset in range(crop_days)]
    by_month_day: dict[tuple[int, int], pd.Timestamp] = {}
    for stamp in frame.index:
        by_month_day[(stamp.month, stamp.day)] = stamp  # index is sorted: latest year wins
    chosen = [by_month_day.get((day.month, day.day)) for day in wanted]
    present = [stamp for stamp in chosen if stamp is not None]
    if not present:
        return None
    period = frame.loc[present]
    if _valid_share(period, required_columns, crop_days) < min_coverage:
        return None
    runs: list[list[pd.Timestamp]] = []
    for stamp in present:
        if runs and stamp - runs[-1][-1] == pd.Timedelta(days=1):
            runs[-1].append(stamp)
        else:
            runs.append([stamp])
    parts = [f"{run[0]:%d %b %Y}–{run[-1]:%d %b %Y}" for run in runs]
    return SeasonOccurrence("Composite: " + " + ".join(parts), period, composite=True)


def crop_duration_days(crop: dict) -> int | None:
    """Documented crop duration: sum of FAO-56 stage lengths, if catalogued."""
    kc = crop.get("crop_coefficient", {})
    keys = ("stage_days_ini", "stage_days_dev", "stage_days_mid", "stage_days_late")
    if kc.get("status") != "fao56_table_12" or any(kc.get(key) is None for key in keys):
        return None
    return int(sum(kc[key] for key in keys))
