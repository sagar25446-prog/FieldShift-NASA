"""FAO-56 Penman–Monteith reference evapotranspiration and crop water balance.

This module implements the equations from:

    Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
    Crop evapotranspiration — Guidelines for computing crop water requirements.
    FAO Irrigation and Drainage Paper 56. Rome: FAO.

It estimates ET₀ (grass-reference ET), ETc (crop ET via Kc coefficients),
effective rainfall (USDA SCS method) and a simplified seasonal water balance.

These are *estimates* suitable for comparing rotations, not irrigation designs.
They are NOT field-calibrated, do NOT model runoff/capillary rise/drainage,
and must NOT be interpreted as measured field water demand.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


# ──────────────────────────── Constants ─────────────────────────────

STEFAN_BOLTZMANN = 4.903e-9  # MJ m⁻² day⁻¹ K⁻⁴
SOLAR_CONSTANT = 0.0820     # MJ m⁻² min⁻¹
ALBEDO = 0.23               # grass reference
PSYCHROMETRIC_CONST_SEA_LEVEL = 0.0665  # kPa °C⁻¹ (at ~101.3 kPa)


# ──────────────────────── Helper functions ──────────────────────────

def _saturation_vapour_pressure(t_celsius: float) -> float:
    """es(T) in kPa — FAO-56 Eq. 11."""
    return 0.6108 * math.exp(17.27 * t_celsius / (t_celsius + 237.3))


def _slope_svp_curve(t_celsius: float) -> float:
    """Δ in kPa °C⁻¹ — FAO-56 Eq. 13."""
    es = _saturation_vapour_pressure(t_celsius)
    return 4098.0 * es / (t_celsius + 237.3) ** 2


def _psychrometric_constant(elevation_m: float) -> float:
    """γ in kPa °C⁻¹ — FAO-56 Eq. 8."""
    p = 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26
    return 0.000665 * p


def _extraterrestrial_radiation(latitude_rad: float, doy: int) -> float:
    """Ra in MJ m⁻² day⁻¹ — FAO-56 Eq. 21."""
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * doy / 365.0)
    delta = 0.409 * math.sin(2.0 * math.pi * doy / 365.0 - 1.39)
    ws = math.acos(-math.tan(latitude_rad) * math.tan(delta))
    ra = (24.0 * 60.0 / math.pi) * SOLAR_CONSTANT * dr * (
        ws * math.sin(latitude_rad) * math.sin(delta)
        + math.cos(latitude_rad) * math.cos(delta) * math.sin(ws)
    )
    return max(0.0, ra)


def _clear_sky_radiation(ra: float, elevation_m: float) -> float:
    """Rso in MJ m⁻² day⁻¹ — FAO-56 Eq. 37."""
    return (0.75 + 2e-5 * elevation_m) * ra


# ────────────────────── Daily ET₀ (FAO-56 PM) ──────────────────────


@dataclass(frozen=True)
class ET0DailyResult:
    """One day's reference ET estimate with quality flags."""
    date: object
    et0_mm: float | None
    method: str
    warnings: tuple[str, ...] = ()


def compute_et0_daily(
    t_max: float | None,
    t_min: float | None,
    rs_mj: float | None,
    rh_mean: float | None,
    ws2_m_s: float | None,
    latitude_deg: float,
    elevation_m: float,
    doy: int,
) -> ET0DailyResult:
    """FAO-56 Penman–Monteith daily ET₀ (Eq. 6).

    Parameters
    ----------
    t_max, t_min : °C (T2M_MAX, T2M_MIN from NASA POWER)
    rs_mj : MJ m⁻² day⁻¹ (ALLSKY_SFC_SW_DWN — already in this unit)
    rh_mean : % (RH2M from NASA POWER)
    ws2_m_s : m s⁻¹ (WS2M from NASA POWER)
    latitude_deg : degrees
    elevation_m : approximate elevation (0 if unknown)
    doy : day of year (1–366)

    Returns
    -------
    ET0DailyResult with et0_mm in mm/day, or None if inputs are insufficient.
    """
    warnings: list[str] = []

    # ── Check required inputs ──
    if t_max is None or t_min is None or math.isnan(t_max) or math.isnan(t_min):
        return ET0DailyResult(None, None, "FAO-56 PM", ("Missing temperature data.",))

    t_mean = (t_max + t_min) / 2.0

    # Humidity: if missing, estimate ea from Tmin (FAO-56 Eq. 48)
    if rh_mean is None or math.isnan(rh_mean):
        ea = _saturation_vapour_pressure(t_min)
        warnings.append("RH unavailable; ea estimated from Tmin (FAO-56 Eq. 48).")
    else:
        es_max = _saturation_vapour_pressure(t_max)
        es_min = _saturation_vapour_pressure(t_min)
        ea = (rh_mean / 100.0) * (es_max + es_min) / 2.0

    # Wind: if missing, use FAO-56 default of 2 m/s
    if ws2_m_s is None or math.isnan(ws2_m_s):
        ws2_m_s = 2.0
        warnings.append("Wind speed unavailable; using FAO-56 default 2 m/s.")

    # Solar radiation: required for full calculation
    if rs_mj is None or math.isnan(rs_mj):
        return ET0DailyResult(None, None, "FAO-56 PM", tuple(warnings) + ("Missing solar radiation.",))

    # ── Calculations ──
    lat_rad = math.radians(latitude_deg)
    gamma = _psychrometric_constant(elevation_m)
    delta_svp = _slope_svp_curve(t_mean)
    es = (_saturation_vapour_pressure(t_max) + _saturation_vapour_pressure(t_min)) / 2.0

    # Net shortwave radiation (Eq. 38)
    rns = (1.0 - ALBEDO) * rs_mj

    # Net longwave radiation (Eq. 39)
    ra = _extraterrestrial_radiation(lat_rad, doy)
    rso = _clear_sky_radiation(ra, elevation_m)
    rs_rso_ratio = min(rs_mj / rso, 1.0) if rso > 0 else 0.5

    rnl = (
        STEFAN_BOLTZMANN
        * ((t_max + 273.16) ** 4 + (t_min + 273.16) ** 4) / 2.0
        * (0.34 - 0.14 * math.sqrt(max(0.0, ea)))
        * (1.35 * rs_rso_ratio - 0.35)
    )

    rn = rns - rnl
    g = 0.0  # Soil heat flux ≈ 0 for daily steps (FAO-56 §4.1)

    # FAO-56 Eq. 6
    numerator = 0.408 * delta_svp * (rn - g) + gamma * (900.0 / (t_mean + 273.0)) * ws2_m_s * (es - ea)
    denominator = delta_svp + gamma * (1.0 + 0.34 * ws2_m_s)

    et0 = numerator / denominator

    method = "FAO-56 Penman–Monteith (Eq. 6)"
    if warnings:
        method += " with substitutions"

    return ET0DailyResult(None, max(0.0, et0), method, tuple(warnings))


# ────────────────── Series-level ET₀ computation ───────────────────


@dataclass(frozen=True)
class ET0SeriesResult:
    """ET₀ computed over a daily climate series."""
    daily_et0_mm: pd.Series          # DatetimeIndex → float (NaN if failed)
    total_et0_mm: float | None       # sum of valid days
    valid_days: int
    total_days: int
    method: str
    warnings: tuple[str, ...] = ()


def compute_et0_series(
    climate_frame: pd.DataFrame,
    latitude_deg: float,
    elevation_m: float = 0.0,
) -> ET0SeriesResult:
    """Compute daily ET₀ from a NASA POWER DataFrame.

    Expected columns: T2M_MAX, T2M_MIN, ALLSKY_SFC_SW_DWN.
    Optional columns: RH2M, WS2M (substituted per FAO-56 if absent).
    """
    required = {"T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN"}
    missing_cols = required - set(climate_frame.columns)
    if missing_cols:
        return ET0SeriesResult(
            pd.Series(dtype=float), None, 0, len(climate_frame),
            "FAO-56 PM — cannot compute",
            (f"Missing required columns: {sorted(missing_cols)}",),
        )

    has_rh = "RH2M" in climate_frame.columns
    has_ws = "WS2M" in climate_frame.columns
    series_warnings: list[str] = []
    if not has_rh:
        series_warnings.append("RH2M not available; ea estimated from Tmin (FAO-56 Eq. 48).")
    if not has_ws:
        series_warnings.append("WS2M not available; using FAO-56 default 2 m/s.")

    et0_values: list[float] = []
    dates = climate_frame.index
    for i, (idx, row) in enumerate(climate_frame.iterrows()):
        doy = idx.timetuple().tm_yday if hasattr(idx, "timetuple") else i + 1
        result = compute_et0_daily(
            t_max=row.get("T2M_MAX"),
            t_min=row.get("T2M_MIN"),
            rs_mj=row.get("ALLSKY_SFC_SW_DWN"),
            rh_mean=row.get("RH2M") if has_rh else None,
            ws2_m_s=row.get("WS2M") if has_ws else None,
            latitude_deg=latitude_deg,
            elevation_m=elevation_m,
            doy=doy,
        )
        et0_values.append(result.et0_mm if result.et0_mm is not None else float("nan"))

    et0_series = pd.Series(et0_values, index=dates, name="ET0_mm")
    valid = et0_series.dropna()
    total = float(valid.sum()) if len(valid) > 0 else None

    if len(valid) < len(et0_values):
        series_warnings.append(
            f"{len(et0_values) - len(valid)} of {len(et0_values)} days could not produce ET0."
        )

    return ET0SeriesResult(
        daily_et0_mm=et0_series,
        total_et0_mm=total,
        valid_days=len(valid),
        total_days=len(et0_values),
        method="FAO-56 Penman–Monteith daily (Allen et al. 1998)",
        warnings=tuple(series_warnings),
    )


# ─────────────────── Effective rainfall (USDA SCS) ─────────────────


def effective_rainfall_usda_scs(monthly_precip_mm: float) -> float:
    """USDA Soil Conservation Service method for effective rainfall.

    Reference: FAO I&D Paper 25 (rev.), Eq. from Dastane (1974).
    Input is *monthly* total precipitation in mm.
    Returns effective rainfall in mm for that month.
    """
    if monthly_precip_mm <= 0:
        return 0.0
    if monthly_precip_mm <= 250.0:
        return monthly_precip_mm * (125.0 - 0.2 * monthly_precip_mm) / 125.0
    return 125.0 + 0.1 * monthly_precip_mm


def estimate_seasonal_effective_rainfall(
    daily_precip: pd.Series,
) -> tuple[float, float]:
    """Compute total and effective seasonal rainfall from daily PRECTOTCORR.

    Returns (total_mm, effective_mm).
    """
    if daily_precip.empty or daily_precip.isna().all():
        return 0.0, 0.0

    total = float(daily_precip.sum(skipna=True))

    # Apply USDA SCS per-month
    monthly = daily_precip.resample("MS").sum()
    effective = sum(effective_rainfall_usda_scs(float(v)) for v in monthly.values if not math.isnan(v))

    return total, effective


# ───────────────── Crop ET and seasonal water balance ──────────────


@dataclass(frozen=True)
class CropKc:
    """Crop coefficient stages from FAO-56 Table 12."""
    kc_ini: float
    kc_mid: float
    kc_end: float
    stage_days_ini: int
    stage_days_dev: int
    stage_days_mid: int
    stage_days_late: int
    source: str

    @property
    def total_days(self) -> int:
        return self.stage_days_ini + self.stage_days_dev + self.stage_days_mid + self.stage_days_late

    def kc_for_day(self, day_in_season: int) -> float:
        """Linearly interpolated Kc for a given day within the growing season."""
        ini_end = self.stage_days_ini
        dev_end = ini_end + self.stage_days_dev
        mid_end = dev_end + self.stage_days_mid
        total = self.total_days

        if day_in_season < 0 or day_in_season >= total:
            return self.kc_end

        if day_in_season < ini_end:
            return self.kc_ini
        elif day_in_season < dev_end:
            # Linear interpolation from kc_ini to kc_mid
            frac = (day_in_season - ini_end) / max(1, self.stage_days_dev)
            return self.kc_ini + frac * (self.kc_mid - self.kc_ini)
        elif day_in_season < mid_end:
            return self.kc_mid
        else:
            # Linear interpolation from kc_mid to kc_end
            frac = (day_in_season - mid_end) / max(1, self.stage_days_late)
            return self.kc_mid + frac * (self.kc_end - self.kc_mid)


@dataclass(frozen=True)
class CropWaterResult:
    """Water balance for one crop in a rotation."""
    crop_id: str
    crop_name: str
    season: str
    et0_total_mm: float | None
    kc_weighted_mean: float | None
    etc_total_mm: float | None
    total_rainfall_mm: float
    effective_rainfall_mm: float
    net_irrigation_requirement_mm: float | None
    method: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationWaterBalance:
    """Full water balance for a candidate rotation sequence."""
    crop_results: tuple[CropWaterResult, ...]
    total_etc_mm: float | None
    total_effective_rainfall_mm: float
    total_net_irrigation_mm: float | None
    climate_water_score: float | None  # 0–1 score derived from water balance
    method: str
    warnings: tuple[str, ...] = ()


def compute_crop_water(
    et0_series: pd.Series,
    precip_series: pd.Series,
    kc: CropKc | None,
    crop_id: str,
    crop_name: str,
    season: str,
) -> CropWaterResult:
    """Compute ETc and water balance for one crop-season.

    If Kc data is unavailable, returns a result with None for ETc fields.
    """
    warnings: list[str] = []

    # ET0
    valid_et0 = et0_series.dropna()
    if valid_et0.empty:
        return CropWaterResult(
            crop_id, crop_name, season,
            et0_total_mm=None, kc_weighted_mean=None, etc_total_mm=None,
            total_rainfall_mm=0.0, effective_rainfall_mm=0.0,
            net_irrigation_requirement_mm=None,
            method="FAO-56 — insufficient ET0 data",
            warnings=("No valid ET0 values for this period.",),
        )

    et0_total = float(valid_et0.sum())
    total_rainfall, effective_rainfall = estimate_seasonal_effective_rainfall(precip_series)

    if kc is None:
        warnings.append("No sourced crop coefficient (Kc) available; ETc cannot be computed.")
        return CropWaterResult(
            crop_id, crop_name, season,
            et0_total_mm=et0_total, kc_weighted_mean=None, etc_total_mm=None,
            total_rainfall_mm=total_rainfall, effective_rainfall_mm=effective_rainfall,
            net_irrigation_requirement_mm=None,
            method="FAO-56 ET0 only — Kc unavailable",
            warnings=tuple(warnings),
        )

    # Compute daily ETc = Kc(day) × ET0(day)
    n_days = len(valid_et0)
    season_length = kc.total_days
    if n_days < season_length:
        warnings.append(
            f"Climate data covers {n_days} days but crop season is {season_length} days. "
            f"ETc estimate uses available data only."
        )

    kc_values = [kc.kc_for_day(i) for i in range(min(n_days, season_length))]
    if n_days > season_length:
        kc_values.extend([kc.kc_end] * (n_days - season_length))

    kc_array = np.array(kc_values[:n_days])
    et0_array = valid_et0.values[:n_days]
    etc_daily = kc_array * et0_array
    etc_total = float(np.nansum(etc_daily))
    kc_mean = float(np.mean(kc_array))

    # Net irrigation requirement
    nir = max(0.0, etc_total - effective_rainfall)

    return CropWaterResult(
        crop_id=crop_id,
        crop_name=crop_name,
        season=season,
        et0_total_mm=et0_total,
        kc_weighted_mean=kc_mean,
        etc_total_mm=etc_total,
        total_rainfall_mm=total_rainfall,
        effective_rainfall_mm=effective_rainfall,
        net_irrigation_requirement_mm=nir,
        method="FAO-56 Penman–Monteith ET0 × Kc (Allen et al. 1998)",
        warnings=tuple(warnings),
    )


def compute_rotation_water_balance(
    crop_results: Sequence[CropWaterResult],
    farmer_budget_mm: float | None = None,
) -> RotationWaterBalance:
    """Aggregate per-crop water results into a rotation-level water balance and score."""
    warnings: list[str] = []

    total_etc: float | None = None
    total_eff_rain = sum(c.effective_rainfall_mm for c in crop_results)
    total_nir: float | None = None

    # Check if all crops have valid ETc
    all_have_etc = all(c.etc_total_mm is not None for c in crop_results)

    if all_have_etc:
        total_etc = sum(c.etc_total_mm for c in crop_results)  # type: ignore[arg-type]
        total_nir = sum(c.net_irrigation_requirement_mm for c in crop_results if c.net_irrigation_requirement_mm is not None)
    else:
        missing = [c.crop_name for c in crop_results if c.etc_total_mm is None]
        warnings.append(f"ETc unavailable for: {', '.join(missing)}. Water score is degraded.")

    # ── Compute climate-based water score ──
    score: float | None = None

    if all_have_etc and total_etc is not None and total_etc > 0:
        # Ratio of effective rainfall to crop demand
        # score = 1.0 means rainfall fully meets demand; 0.0 means no rainfall at all
        rain_coverage = min(1.0, total_eff_rain / total_etc)

        if farmer_budget_mm is not None and total_nir is not None:
            # Farmer budget covers the gap?
            if total_nir <= 0:
                score = 1.0  # No irrigation needed
            elif farmer_budget_mm >= total_nir:
                score = 1.0  # Budget fully covers deficit
            else:
                # Partial coverage: blend rain coverage + budget coverage of deficit
                budget_coverage = farmer_budget_mm / total_nir
                score = rain_coverage + (1.0 - rain_coverage) * min(1.0, budget_coverage)
                score = min(1.0, max(0.0, score))
        else:
            # No farmer budget — score is just rain coverage
            score = rain_coverage
            if farmer_budget_mm is None:
                warnings.append(
                    "No farmer water budget provided; score based on "
                    "rainfall-to-demand ratio only."
                )

    return RotationWaterBalance(
        crop_results=tuple(crop_results),
        total_etc_mm=total_etc,
        total_effective_rainfall_mm=total_eff_rain,
        total_net_irrigation_mm=total_nir,
        climate_water_score=score,
        method="FAO-56 water balance: ETc from Kc×ET0, effective rainfall USDA SCS",
        warnings=tuple(warnings),
    )
