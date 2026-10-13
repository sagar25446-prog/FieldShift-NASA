"""NASA Earth observation context and farmer water input helpers.

Contains:
1. NASA GRACE (Gravity Recovery and Climate Experiment) Groundwater Depletion
   satellite observation data and regional context for Northwestern India.
2. NASA FIRMS (Fire Information for Resource Management System) Post-Monsoon
   Thermal Anomaly / Crop Residue Burning satellite context.
3. Farmer Water-Input Calculator: translates tubewell pump horsepower/hours,
   canal supply turns, and groundwater depth into estimated irrigation budget (mm).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


# ─────────────────────────────────────────────────────────────────────────────
# NASA GRACE Satellite Groundwater Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GraceGroundwaterContext:
    """NASA GRACE / GRACE-FO regional groundwater depletion context."""

    region: str
    satellite_mission: str
    rate_of_depletion_cm_per_year: float
    total_volume_lost_km3_per_year: float
    overexploited_blocks_pct: float
    key_finding: str
    citation: str
    source_url: str


GRACE_PUNJAB_CONTEXT = GraceGroundwaterContext(
    region="Northwestern India (Punjab, Haryana, Rajasthan)",
    satellite_mission="NASA GRACE (2002–2017) and GRACE-FO (2018–present)",
    rate_of_depletion_cm_per_year=-4.0,  # -4.0 ± 1.0 cm/yr equivalent water height
    total_volume_lost_km3_per_year=-17.7,  # 17.7 ± 4.5 km³/yr
    overexploited_blocks_pct=78.0,  # Central Ground Water Board assessment
    key_finding=(
        "NASA GRACE satellite gravity measurements demonstrate that Northwestern India "
        "has lost groundwater at an unsustainable rate of 4.0 ± 1.0 cm/year equivalent water height "
        "(17.7 km³/year) since 2002. Over 78% of Punjab administrative blocks are classified as "
        "'Over-exploited' with declining water tables primarily driven by paddy irrigation pumping."
    ),
    citation="Rodell, M., Velicogna, I., & Famiglietti, J. S. (2009). Satellite-based estimates of groundwater depletion in India. Nature, 460(7258), 999-1002.",
    source_url="https://doi.org/10.1038/nature08238",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA FIRMS Active Fire / Stubble Burning Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FirmsResidueContext:
    """NASA FIRMS active fire detection context for post-harvest Punjab."""

    sensor: str
    peak_season: str
    annual_fire_count_range: tuple[int, int]
    air_quality_impact: str
    crop_residue_solution: str
    source_url: str


FIRMS_PUNJAB_CONTEXT = FirmsResidueContext(
    sensor="NASA FIRMS (MODIS Terra/Aqua & VIIRS Suomi-NPP/NOAA-20)",
    peak_season="October 15 – November 20 (Post-Kharif rice harvest window)",
    annual_fire_count_range=(45000, 75000),  # Typical seasonal thermal anomalies
    air_quality_impact=(
        "Paddy straw burning in October–November releases massive particulate matter (PM2.5, PM10) "
        "and greenhouse gases across the Indo-Gangetic Plains, caused by the tight 2–3 week turnaround "
        "between flooded rice harvest and wheat sowing."
    ),
    crop_residue_solution=(
        "Diversifying Kharif crops away from long-duration paddy to Maize, Cotton, Moong, or Pearl Millet "
        "substantially reduces or eliminates straw burning pressure. Incorporating Happy Seeder / Super-SMS "
        "in-situ straw retention improves Soil Organic Carbon (SOC) and preserves soil moisture."
    ),
    source_url="https://firms.modaps.eosdis.nasa.gov/",
)


# ─────────────────────────────────────────────────────────────────────────────
# Farmer Water Budget Calculator Helper
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WaterBudgetCalculation:
    """Breakdown of calculated farmer water budget."""

    tubewell_hours: float
    tubewell_hp: float
    tubewell_discharge_litres_per_sec: float
    tubewell_water_mm: float
    canal_water_mm: float
    total_water_budget_mm: float
    farm_area_acres: float
    formula_explanation: str


def calculate_water_budget_from_farm_inputs(
    tubewell_hours_per_irrigation: float,
    tubewell_irrigations_count: int,
    tubewell_motor_hp: float = 7.5,
    canal_hours_per_week: float = 0.0,
    canal_weeks_per_season: int = 16,
    farm_area_acres: float = 2.5,
) -> WaterBudgetCalculation:
    """Calculate effective irrigation water budget (in mm) from practical farmer inputs.

    Parameters
    ----------
    tubewell_hours_per_irrigation : Hours pump runs per irrigation event
    tubewell_irrigations_count : Number of planned irrigations across the season
    tubewell_motor_hp : Motor rating in Horsepower (standard central Punjab: 5, 7.5, 10 HP)
    canal_hours_per_week : Canal turn (wara-bandi) hours allocated per week
    canal_weeks_per_season : Duration of canal water availability (weeks)
    farm_area_acres : Area of the plot in acres (1 acre = 4,046.86 m²)

    Returns
    -------
    WaterBudgetCalculation with total equivalent water depth in mm.
    """
    area_acres = max(0.1, float(farm_area_acres))
    area_m2 = area_acres * 4046.86

    # Discharge estimation: typical submersible pumps in central Punjab deliver
    # ~1.4 to 1.6 litres per second per HP (e.g. 7.5 HP -> ~11 L/s; 10 HP -> ~15 L/s)
    # Ref: Central Ground Water Board pump testing standards
    discharge_lps = max(1.0, tubewell_motor_hp * 1.45)

    # Tubewell volume
    total_tubewell_hours = max(0.0, float(tubewell_hours_per_irrigation)) * max(0, tubewell_irrigations_count)
    tubewell_volume_litres = total_tubewell_hours * 3600.0 * discharge_lps
    tubewell_volume_m3 = tubewell_volume_litres / 1000.0
    tubewell_depth_mm = (tubewell_volume_m3 / area_m2) * 1000.0

    # Canal water volume: standard canal outlet (mogha) discharge ~1 cusec = 28.3 L/s
    # Shared among farmers. Typical allocation turn delivers ~15–25 L/s at field head.
    canal_discharge_lps = 20.0  # litres/second average delivery at farm gate
    total_canal_hours = max(0.0, float(canal_hours_per_week)) * max(0, canal_weeks_per_season)
    canal_volume_litres = total_canal_hours * 3600.0 * canal_discharge_lps
    canal_volume_m3 = canal_volume_litres / 1000.0
    canal_depth_mm = (canal_volume_m3 / area_m2) * 1000.0

    total_mm = tubewell_depth_mm + canal_depth_mm

    explanation = (
        f"Calculated from {tubewell_motor_hp:.1f} HP pump ({discharge_lps:.1f} L/s discharge) running for "
        f"{total_tubewell_hours:.0f} total hours ({tubewell_depth_mm:.0f} mm) plus "
        f"{total_canal_hours:.0f} canal turn hours ({canal_depth_mm:.0f} mm) over {area_acres:.1f} acres."
    )

    return WaterBudgetCalculation(
        tubewell_hours=total_tubewell_hours,
        tubewell_hp=tubewell_motor_hp,
        tubewell_discharge_litres_per_sec=discharge_lps,
        tubewell_water_mm=tubewell_depth_mm,
        canal_water_mm=canal_depth_mm,
        total_water_budget_mm=total_mm,
        farm_area_acres=area_acres,
        formula_explanation=explanation,
    )
