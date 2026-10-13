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
from typing import Any, Mapping


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

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "satellite": self.satellite_mission,
            "resolution": "300–400 km regional mass change",
            "finding": self.key_finding,
            "primary_driver": "Paddy rice flood-irrigation tubewell pumping exceeding natural recharge",
            "relevance_to_fieldshift": "Demonstrates that shifting Kharif crops to Maize, Cotton, or Moong directly stems aquifer depletion.",
            "source_citation": self.citation,
            "source_url": self.source_url,
        }
        return mapping.get(key, getattr(self, key, ""))


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

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "sensors": self.sensor,
            "stubble_burning_season": self.peak_season,
            "agricultural_driver": "Narrow 2–3 week turnaround between flooded rice harvest and wheat sowing",
            "relevance_to_fieldshift": self.crop_residue_solution,
            "source_citation": "NASA Earthdata FIRMS Active Fire System",
            "source_url": self.source_url,
        }
        return mapping.get(key, getattr(self, key, ""))


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

    def __getitem__(self, key: str) -> Any:
        mapping = {
            "total_water_budget_mm": self.total_water_budget_mm,
            "tubewell_contribution_mm": self.tubewell_water_mm,
            "canal_contribution_mm": self.canal_water_mm,
            "tubewell_water_mm": self.tubewell_water_mm,
            "canal_water_mm": self.canal_water_mm,
            "formula_explanation": self.formula_explanation,
        }
        return mapping.get(key, getattr(self, key, 0.0))


def calculate_water_budget_from_farm_inputs(
    tubewell_hours_per_irrigation: float | None = None,
    tubewell_irrigations_count: int | None = None,
    tubewell_motor_hp: float = 7.5,
    canal_hours_per_week: float = 0.0,
    canal_weeks_per_season: int = 16,
    farm_area_acres: float = 2.5,
    tubewell_hp: float | None = None,
    hours_per_week: float | None = None,
    weeks_operating: float | None = None,
    canal_turns_per_season: int | None = None,
    canal_depth_inches: float | None = None,
    farm_size_acres: float | None = None,
    **kwargs: Any,
) -> WaterBudgetCalculation:
    """Calculate effective irrigation water budget (in mm) from practical farmer inputs.

    Supports both per-irrigation event counts and seasonal weekly schedules.
    """
    effective_hp = tubewell_hp if tubewell_hp is not None else tubewell_motor_hp
    area_acres = max(0.1, float(farm_size_acres if farm_size_acres is not None else farm_area_acres))
    area_m2 = area_acres * 4046.86

    discharge_lps = max(1.0, effective_hp * 1.45)

    if hours_per_week is not None and weeks_operating is not None:
        total_tubewell_hours = max(0.0, float(hours_per_week)) * max(0.0, float(weeks_operating))
    elif tubewell_hours_per_irrigation is not None and tubewell_irrigations_count is not None:
        total_tubewell_hours = max(0.0, float(tubewell_hours_per_irrigation)) * max(0, tubewell_irrigations_count)
    else:
        total_tubewell_hours = 0.0

    tubewell_volume_litres = total_tubewell_hours * 3600.0 * discharge_lps
    tubewell_volume_m3 = tubewell_volume_litres / 1000.0
    tubewell_depth_mm = (tubewell_volume_m3 / area_m2) * 1000.0

    if canal_turns_per_season is not None and canal_depth_inches is not None:
        canal_depth_mm = max(0.0, float(canal_turns_per_season)) * max(0.0, float(canal_depth_inches)) * 25.4
    else:
        canal_discharge_lps = 20.0
        total_canal_hours = max(0.0, float(canal_hours_per_week)) * max(0, canal_weeks_per_season)
        canal_volume_litres = total_canal_hours * 3600.0 * canal_discharge_lps
        canal_volume_m3 = canal_volume_litres / 1000.0
        canal_depth_mm = (canal_volume_m3 / area_m2) * 1000.0

    total_mm = tubewell_depth_mm + canal_depth_mm

    explanation = (
        f"Calculated from {effective_hp:.1f} HP pump ({discharge_lps:.1f} L/s discharge) running for "
        f"{total_tubewell_hours:.0f} total hours ({tubewell_depth_mm:.0f} mm) plus "
        f"canal supply ({canal_depth_mm:.0f} mm) over {area_acres:.1f} acres."
    )

    return WaterBudgetCalculation(
        tubewell_hours=total_tubewell_hours,
        tubewell_hp=effective_hp,
        tubewell_discharge_litres_per_sec=discharge_lps,
        tubewell_water_mm=tubewell_depth_mm,
        canal_water_mm=canal_depth_mm,
        total_water_budget_mm=total_mm,
        farm_area_acres=area_acres,
        formula_explanation=explanation,
    )


# ─────────────────────────────────────────────────────────────────────────────
# NASA SMAP Soil Moisture Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SmapSoilMoistureContext:
    """NASA SMAP (Soil Moisture Active Passive) L3/L4 satellite moisture context."""

    satellite_mission: str
    spatial_resolution_km: float
    surface_moisture_m3_m3: float  # 0–5 cm volumetric water content
    rootzone_moisture_m3_m3: float  # 0–100 cm root-zone volumetric content
    climatological_percentile: float
    moisture_status: str
    citation: str
    source_url: str


SMAP_PUNJAB_CONTEXT = SmapSoilMoistureContext(
    satellite_mission="NASA SMAP (Radiometer L3/L4 Root-Zone Soil Moisture)",
    spatial_resolution_km=9.0,
    surface_moisture_m3_m3=0.18,
    rootzone_moisture_m3_m3=0.22,
    climatological_percentile=34.0,
    moisture_status="Below average root-zone storage; indicates irrigation dependency for seedling establishment.",
    citation="Entekhabi, D., et al. (2010). The Soil Moisture Active Passive (SMAP) Mission. Proceedings of the IEEE, 98(5), 704-716.",
    source_url="https://smap.jpl.nasa.gov/",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA GPM IMERG Precipitation Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GpmPrecipitationContext:
    """NASA GPM (Global Precipitation Measurement) IMERG satellite precipitation context."""

    satellite_constellation: str
    spatial_resolution_deg: float
    temporal_resolution: str
    gauge_calibration_status: str
    satellite_vs_power_agreement: str
    citation: str
    source_url: str


GPM_GLOBAL_CONTEXT = GpmPrecipitationContext(
    satellite_constellation="NASA/JAXA GPM Core Observatory + Partner Constellation (IMERG V07)",
    spatial_resolution_deg=0.1,  # ~10 km
    temporal_resolution="Half-hourly & Daily",
    gauge_calibration_status="GPCC-calibrated monthly; verified against NASA POWER daily reanalysis.",
    satellite_vs_power_agreement=(
        "NASA GPM IMERG satellite radar/microwave precipitation tracks monsoon progression "
        "and storm intensity with high spatial fidelity. In the Indo-Gangetic Plains, IMERG "
        "shows strong correlation (r > 0.88) with NASA POWER daily precipitation totals."
    ),
    citation="Huffman, G. J., et al. (2020). The Integrated Multi-satellitE Retrievals for GPM (IMERG). In Satellite Precipitation Measurement (pp. 343-353). Springer.",
    source_url="https://gpm.nasa.gov/",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA MODIS NDVI Vegetation Vigor Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ModisNdviContext:
    """NASA MODIS (MOD13Q1) 250m 16-day Vegetation Index context."""

    sensor: str
    spatial_resolution_m: int
    temporal_cadence_days: int
    peak_ndvi_kharif: float
    peak_ndvi_rabi: float
    bare_soil_ndvi: float
    finding: str
    citation: str
    source_url: str


MODIS_NDVI_CONTEXT = ModisNdviContext(
    sensor="NASA MODIS Terra/Aqua (MOD13Q1 Version 6.1)",
    spatial_resolution_m=250,
    temporal_cadence_days=16,
    peak_ndvi_kharif=0.76,  # Dense green canopy during peak August monsoon
    peak_ndvi_rabi=0.82,    # Peak February wheat canopy
    bare_soil_ndvi=0.18,    # Post-harvest fallow / stubble
    finding=(
        "Bimodal MODIS NDVI peaks clearly delineate the Kharif (rice/maize/cotton) and Rabi (wheat/mustard) "
        "greenness cycles, confirming intensive double-cropping with brief dry-down windows."
    ),
    citation="Didan, K. (2015). MOD13Q1 MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V006. NASA EOSDIS Land Processes DAAC.",
    source_url="https://modis.gsfc.nasa.gov/",
)

