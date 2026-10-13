"""FAO EcoCrop thermal suitability and extreme temperature stress assessment.

Evaluates crop and rotation climate suitability based on:
1. FAO EcoCrop cardinal temperature thresholds (Tmin_abs, Tmin_opt, Tmax_opt, Tmax_abs).
2. Documented daily heat-stress thresholds (e.g. PAU Rabi terminal heat for wheat).
3. Frost / killing temperature thresholds (when documented).

Separation of Concerns:
- Water demand, rainfall, and irrigation deficit are handled solely by FAO-56 in `fao56.py`.
- Temperature regime compatibility and thermal stress days are handled solely here.
- No machine learning or uncalibrated yield predictions are made.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CropThermalProfile:
    """Documented temperature requirements from FAO EcoCrop and regional packages."""

    crop_id: str
    crop_name: str
    status: str  # "documented_ecocrop" or "unknown"
    ecocrop_code: int | None
    tmin_absolute: float | None
    tmin_optimal: float | None
    tmax_optimal: float | None
    tmax_absolute: float | None
    killing_temperature: float | None = None
    extreme_heat_threshold: float | None = None
    extreme_heat_threshold_context: str | None = None
    notes: str | None = None
    source_ids: tuple[str, ...] = ()

    @classmethod
    def from_crop_dict(cls, crop: dict) -> CropThermalProfile:
        ts = crop.get("temperature_suitability", {})
        return cls(
            crop_id=crop.get("id", "unknown"),
            crop_name=crop.get("name", "Unknown"),
            status=ts.get("status", "unknown"),
            ecocrop_code=ts.get("ecocrop_code"),
            tmin_absolute=ts.get("tmin_absolute"),
            tmin_optimal=ts.get("tmin_optimal"),
            tmax_optimal=ts.get("tmax_optimal"),
            tmax_absolute=ts.get("tmax_absolute"),
            killing_temperature=ts.get("killing_temperature"),
            extreme_heat_threshold=ts.get("extreme_heat_threshold"),
            extreme_heat_threshold_context=ts.get("extreme_heat_threshold_context"),
            notes=ts.get("notes"),
            source_ids=tuple(ts.get("source_ids", ())),
        )


@dataclass(frozen=True)
class CropClimateAssessment:
    """Climate thermal suitability evaluation for a single crop during its growing season."""

    crop_id: str
    crop_name: str
    season: str
    t_mean: float | None
    t_min: float | None
    t_max: float | None
    t_min_avg: float | None
    t_max_avg: float | None
    tmin_optimal: float | None
    tmax_optimal: float | None
    tmin_absolute: float | None
    tmax_absolute: float | None
    base_thermal_suitability: float | None  # 0.0 to 1.0 EcoCrop piece-wise linear score
    extreme_heat_threshold: float | None
    heat_stress_days: int
    killing_temperature: float | None
    frost_stress_days: int
    stress_penalty: float  # 0.0 to 1.0 deduction
    climate_suitability_score: float | None  # 0.0 to 1.0 final score
    status: str  # "suitable", "marginal", "unsuitable", "unavailable"
    method: str
    warnings: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationClimateAssessment:
    """Rotation-level aggregation of crop climate suitability."""

    crops: tuple[CropClimateAssessment, ...]
    climate_suitability_score: float | None
    status: str  # "available", "partial", "unavailable"
    method: str
    warnings: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


def ecocrop_temperature_suitability(
    t_mean: float | None,
    tmin_abs: float | None,
    tmin_opt: float | None,
    tmax_opt: float | None,
    tmax_abs: float | None,
) -> float | None:
    """Calculate the FAO EcoCrop piece-wise linear temperature suitability (0.0 to 1.0).

    Piece-wise linear response function:
      - 0.0 if t_mean <= tmin_abs or t_mean >= tmax_abs
      - linear increase from 0.0 to 1.0 for tmin_abs < t_mean < tmin_opt
      - 1.0 if tmin_opt <= t_mean <= tmax_opt
      - linear decrease from 1.0 to 0.0 for tmax_opt < t_mean < tmax_abs

    Returns None if any input is None, NaN, or logically inconsistent.
    """
    if (
        t_mean is None or math.isnan(t_mean)
        or tmin_abs is None or tmin_opt is None
        or tmax_opt is None or tmax_abs is None
    ):
        return None

    if not (tmin_abs < tmin_opt <= tmax_opt < tmax_abs):
        return None

    if t_mean <= tmin_abs or t_mean >= tmax_abs:
        return 0.0
    elif tmin_abs < t_mean < tmin_opt:
        return (t_mean - tmin_abs) / (tmin_opt - tmin_abs)
    elif tmin_opt <= t_mean <= tmax_opt:
        return 1.0
    else:  # tmax_opt < t_mean < tmax_abs
        return (tmax_abs - t_mean) / (tmax_abs - tmax_opt)


def calculate_stress_penalty(
    heat_days: int,
    frost_days: int,
    total_valid_days: int,
) -> float:
    """Calculate the thermal stress deduction from extreme heat and frost days.

    Deduction is proportional to the fraction of stressed days:
      penalty = min(1.0, 0.5 * (heat_days / N) + 0.5 * (frost_days / N))
    """
    if total_valid_days <= 0:
        return 0.0
    f_heat = heat_days / total_valid_days
    f_frost = frost_days / total_valid_days
    return min(1.0, 0.5 * f_heat + 0.5 * f_frost)


def assess_crop_climate(
    crop_data: dict,
    climate_slice: pd.DataFrame | None,
    season: str = "kharif",
) -> CropClimateAssessment:
    """Assess growing-season climate thermal suitability for a single crop."""
    profile = CropThermalProfile.from_crop_dict(crop_data)
    warnings: list[str] = []

    # 1. Check if crop thresholds are documented
    if (
        profile.status != "documented_ecocrop"
        or profile.tmin_absolute is None
        or profile.tmin_optimal is None
        or profile.tmax_optimal is None
        or profile.tmax_absolute is None
    ):
        warnings.append(f"Crop-specific thermal thresholds are undocumented for {profile.crop_name}.")
        return CropClimateAssessment(
            crop_id=profile.crop_id,
            crop_name=profile.crop_name,
            season=season,
            t_mean=None,
            t_min=None,
            t_max=None,
            t_min_avg=None,
            t_max_avg=None,
            tmin_optimal=None,
            tmax_optimal=None,
            tmin_absolute=None,
            tmax_absolute=None,
            base_thermal_suitability=None,
            extreme_heat_threshold=profile.extreme_heat_threshold,
            heat_stress_days=0,
            killing_temperature=profile.killing_temperature,
            frost_stress_days=0,
            stress_penalty=0.0,
            climate_suitability_score=None,
            status="unavailable",
            method="FAO EcoCrop — thresholds undocumented",
            warnings=tuple(warnings),
            source_ids=profile.source_ids,
        )

    # 2. Check climate data availability
    if climate_slice is None or not isinstance(climate_slice, pd.DataFrame) or climate_slice.empty:
        warnings.append(f"No daily climate data provided for {profile.crop_name} ({season}).")
        return CropClimateAssessment(
            crop_id=profile.crop_id,
            crop_name=profile.crop_name,
            season=season,
            t_mean=None,
            t_min=None,
            t_max=None,
            t_min_avg=None,
            t_max_avg=None,
            tmin_optimal=profile.tmin_optimal,
            tmax_optimal=profile.tmax_optimal,
            tmin_absolute=profile.tmin_absolute,
            tmax_absolute=profile.tmax_absolute,
            base_thermal_suitability=None,
            extreme_heat_threshold=profile.extreme_heat_threshold,
            heat_stress_days=0,
            killing_temperature=profile.killing_temperature,
            frost_stress_days=0,
            stress_penalty=0.0,
            climate_suitability_score=None,
            status="unavailable",
            method="FAO EcoCrop — climate observations unavailable",
            warnings=tuple(warnings),
            source_ids=profile.source_ids,
        )

    # 3. Extract temperature series
    # Support T2M, or derive from T2M_MAX and T2M_MIN
    has_t2m = "T2M" in climate_slice.columns
    has_tmax = "T2M_MAX" in climate_slice.columns
    has_tmin = "T2M_MIN" in climate_slice.columns

    if not (has_t2m or (has_tmax and has_tmin)):
        warnings.append("Temperature columns (T2M or T2M_MAX/T2M_MIN) missing from climate data.")
        return CropClimateAssessment(
            crop_id=profile.crop_id,
            crop_name=profile.crop_name,
            season=season,
            t_mean=None,
            t_min=None,
            t_max=None,
            t_min_avg=None,
            t_max_avg=None,
            tmin_optimal=profile.tmin_optimal,
            tmax_optimal=profile.tmax_optimal,
            tmin_absolute=profile.tmin_absolute,
            tmax_absolute=profile.tmax_absolute,
            base_thermal_suitability=None,
            extreme_heat_threshold=profile.extreme_heat_threshold,
            heat_stress_days=0,
            killing_temperature=profile.killing_temperature,
            frost_stress_days=0,
            stress_penalty=0.0,
            climate_suitability_score=None,
            status="unavailable",
            method="FAO EcoCrop — missing temperature parameters",
            warnings=tuple(warnings),
            source_ids=profile.source_ids,
        )

    tmax_series = climate_slice["T2M_MAX"] if has_tmax else climate_slice["T2M"]
    tmin_series = climate_slice["T2M_MIN"] if has_tmin else climate_slice["T2M"]
    tmean_series = climate_slice["T2M"] if has_t2m else (tmax_series + tmin_series) / 2.0

    valid_mask = tmean_series.notna() & tmax_series.notna() & tmin_series.notna()
    total_days = len(climate_slice)
    valid_days = int(valid_mask.sum())
    missing_days = total_days - valid_days

    if valid_days == 0:
        warnings.append("All daily temperature observations are missing/NaN.")
        return CropClimateAssessment(
            crop_id=profile.crop_id,
            crop_name=profile.crop_name,
            season=season,
            t_mean=None,
            t_min=None,
            t_max=None,
            t_min_avg=None,
            t_max_avg=None,
            tmin_optimal=profile.tmin_optimal,
            tmax_optimal=profile.tmax_optimal,
            tmin_absolute=profile.tmin_absolute,
            tmax_absolute=profile.tmax_absolute,
            base_thermal_suitability=None,
            extreme_heat_threshold=profile.extreme_heat_threshold,
            heat_stress_days=0,
            killing_temperature=profile.killing_temperature,
            frost_stress_days=0,
            stress_penalty=0.0,
            climate_suitability_score=None,
            status="unavailable",
            method="FAO EcoCrop — all observations missing",
            warnings=tuple(warnings),
            source_ids=profile.source_ids,
        )

    if missing_days > 0:
        warnings.append(f"{missing_days} day(s) missing from temperature record ({valid_days}/{total_days} valid).")

    v_mean = tmean_series[valid_mask]
    v_max = tmax_series[valid_mask]
    v_min = tmin_series[valid_mask]

    t_mean_val = float(v_mean.mean())
    t_min_val = float(v_min.min())
    t_max_val = float(v_max.max())
    t_min_avg = float(v_min.mean())
    t_max_avg = float(v_max.mean())

    # 4. EcoCrop piece-wise linear base score
    base_score = ecocrop_temperature_suitability(
        t_mean=t_mean_val,
        tmin_abs=profile.tmin_absolute,
        tmin_opt=profile.tmin_optimal,
        tmax_opt=profile.tmax_optimal,
        tmax_abs=profile.tmax_absolute,
    )

    # 5. Extreme temperature stress days
    heat_days = 0
    if profile.extreme_heat_threshold is not None:
        heat_days = int((v_max >= profile.extreme_heat_threshold).sum())
        if heat_days > 0:
            warnings.append(
                f"{heat_days} day(s) exceeded documented heat threshold "
                f"({profile.extreme_heat_threshold:.1f}°C)."
            )

    frost_days = 0
    if profile.killing_temperature is not None:
        frost_days = int((v_min <= profile.killing_temperature).sum())
        if frost_days > 0:
            warnings.append(
                f"{frost_days} day(s) reached frost/killing temperature "
                f"({profile.killing_temperature:.1f}°C)."
            )

    # 6. Combined score
    penalty = calculate_stress_penalty(heat_days, frost_days, valid_days)
    if base_score is not None:
        final_score = max(0.0, min(1.0, round(base_score * (1.0 - penalty), 4)))
    else:
        final_score = None

    # Status classification
    if final_score is None:
        status_label = "unavailable"
    elif final_score >= 0.70:
        status_label = "suitable"
    elif final_score >= 0.35:
        status_label = "marginal"
    else:
        status_label = "unsuitable"

    method_str = (
        f"FAO EcoCrop (Code {profile.ecocrop_code}) linear thermal suitability "
        f"adjusted for {heat_days} heat day(s) and {frost_days} frost day(s)"
    )

    return CropClimateAssessment(
        crop_id=profile.crop_id,
        crop_name=profile.crop_name,
        season=season,
        t_mean=t_mean_val,
        t_min=t_min_val,
        t_max=t_max_val,
        t_min_avg=t_min_avg,
        t_max_avg=t_max_avg,
        tmin_optimal=profile.tmin_optimal,
        tmax_optimal=profile.tmax_optimal,
        tmin_absolute=profile.tmin_absolute,
        tmax_absolute=profile.tmax_absolute,
        base_thermal_suitability=base_score,
        extreme_heat_threshold=profile.extreme_heat_threshold,
        heat_stress_days=heat_days,
        killing_temperature=profile.killing_temperature,
        frost_stress_days=frost_days,
        stress_penalty=penalty,
        climate_suitability_score=final_score,
        status=status_label,
        method=method_str,
        warnings=tuple(warnings),
        source_ids=profile.source_ids,
    )


def assess_rotation_climate(
    crops: Sequence[dict],
    climate_data: pd.DataFrame | None,
    seasons: Sequence[str],
) -> RotationClimateAssessment:
    """Aggregate per-crop climate assessments across a planned rotation sequence."""
    if climate_data is None or not isinstance(climate_data, pd.DataFrame) or climate_data.empty:
        return RotationClimateAssessment(
            crops=(),
            climate_suitability_score=None,
            status="unavailable",
            method="FAO EcoCrop thermal suitability — no daily climate observations provided",
            warnings=("No daily climate data provided in farm profile.",),
            source_ids=(),
        )

    # Partition climate data across crops if multi-season
    n_crops = len(crops)
    n_days = len(climate_data)
    days_per_crop = max(1, n_days // n_crops)

    crop_assessments: list[CropClimateAssessment] = []
    all_source_ids: set[str] = set()

    for idx, (crop_dict, season) in enumerate(zip(crops, seasons)):
        start_idx = idx * days_per_crop
        end_idx = (idx + 1) * days_per_crop if idx < n_crops - 1 else n_days
        slice_df = climate_data.iloc[start_idx:end_idx] if n_days > 0 else climate_data

        assessment = assess_crop_climate(crop_dict, slice_df, season=season)
        crop_assessments.append(assessment)
        all_source_ids.update(assessment.source_ids)

    valid_scores = [c.climate_suitability_score for c in crop_assessments if c.climate_suitability_score is not None]
    total_crops = len(crop_assessments)
    warnings: list[str] = []

    for c in crop_assessments:
        warnings.extend(c.warnings)

    if len(valid_scores) == total_crops and total_crops > 0:
        rot_score = round(float(np.mean(valid_scores)), 4)
        status = "available"
        method = f"Mean FAO EcoCrop thermal suitability across {total_crops} planned season(s)"
    elif len(valid_scores) > 0:
        rot_score = round(float(np.mean(valid_scores)), 4)
        status = "partial"
        missing_names = [c.crop_name for c in crop_assessments if c.climate_suitability_score is None]
        warnings.append(
            f"Partial evidence: scored for {len(valid_scores)}/{total_crops} crops; "
            f"thresholds unavailable for: {', '.join(missing_names)}."
        )
        method = f"Partial FAO EcoCrop thermal suitability ({len(valid_scores)}/{total_crops} crops with evidence)"
    else:
        rot_score = None
        status = "unavailable"
        method = "FAO EcoCrop thermal suitability — all crops lack documented thresholds"
        warnings.append("No crop in this rotation has documented thermal thresholds.")

    return RotationClimateAssessment(
        crops=tuple(crop_assessments),
        climate_suitability_score=rot_score,
        status=status,
        method=method,
        warnings=tuple(dict.fromkeys(warnings)),
        source_ids=tuple(sorted(all_source_ids)),
    )
