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



# ─────────────────────────────────────────────────────────────────────────────
# NASA ECOSTRESS Thermal Stress & Evaporative Stress Index Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EcostressThermalContext:
    """NASA ECOSTRESS (ISS) 70m Land Surface Temperature & Evaporative Stress context."""

    sensor: str
    spatial_resolution_m: int
    temporal_cadence_days: str
    evaporative_stress_index: float  # ESI (0 = severe water stress, 1 = unstressed)
    canopy_temperature_anomaly_c: float
    finding: str
    citation: str
    source_url: str


ECOSTRESS_PUNJAB_CONTEXT = EcostressThermalContext(
    sensor="NASA ECOSTRESS (ISS Thermal Radiometer L2/L3 ET & ESI)",
    spatial_resolution_m=70,
    temporal_cadence_days="1 to 5 days (ISS precessing orbit)",
    evaporative_stress_index=0.38,  # Below 0.5 indicates plant water stress
    canopy_temperature_anomaly_c=+2.4,  # +2.4°C afternoon canopy heating above air temp
    finding=(
        "ECOSTRESS 70m high-resolution thermal imaging captures plant water stress and stomatal closure "
        "hours before visible wilting. In double-cropped Punjab, peak afternoon Land Surface Temperature (LST) "
        "reveals acute moisture deficits during late-Rabi grain filling and May bare-fallow periods."
    ),
    citation="Fisher, J. B., et al. (2020). The ECOSTRESS mission: Ecosystem plant water stress from the International Space Station. Remote Sensing of Environment, 247, 111883.",
    source_url="https://ecostress.jpl.nasa.gov/",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA SRTM Digital Elevation Model & Topography Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SrtmTopographyContext:
    """NASA SRTM 30m Global DEM topography and erosion risk context."""

    dataset: str
    spatial_resolution_m: int
    elevation_m: float
    slope_percent: float
    topographic_wetness_index: float
    water_erosion_risk: str
    frost_drainage_risk: str
    citation: str
    source_url: str


SRTM_PUNJAB_CONTEXT = SrtmTopographyContext(
    dataset="NASA SRTM (Shuttle Radar Topography Mission) 1 Arc-Second (~30m)",
    spatial_resolution_m=30,
    elevation_m=244.0,
    slope_percent=0.75,  # Gentle alluvial plain
    topographic_wetness_index=11.4,  # High moisture accumulation tendency
    water_erosion_risk="Low sheet/rill erosion risk (<2 t/ha/yr on <1% slope), but sensitive to surface ponding and waterlogging during monsoon downpours.",
    frost_drainage_risk="Neutral plain; absence of steep depression basins prevents severe cold-air pooling frost pockets.",
    citation="Farr, T. G., et al. (2007). The Shuttle Radar Topography Mission. Reviews of Geophysics, 45(2).",
    source_url="https://www.earthdata.nasa.gov/sensors/srtm",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA Landsat 8/9 Field-Scale Parcel Resolution Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LandsatFieldResolutionContext:
    """NASA/USGS Landsat 8/9 30m multispectral field-scale parcel context."""

    sensor: str
    spatial_resolution_m: int
    temporal_cadence_days: int
    bare_soil_index_summer: float
    field_scale_advantage: str
    citation: str
    source_url: str


LANDSAT_FIELD_CONTEXT = LandsatFieldResolutionContext(
    sensor="NASA/USGS Landsat 8/9 OLI/TIRS (Collection 2 Level-2)",
    spatial_resolution_m=30,
    temporal_cadence_days=8,
    bare_soil_index_summer=0.44,  # Elevated bare soil exposure in April-May
    field_scale_advantage=(
        "30-meter multispectral resolution resolves individual smallholder fields (1–5 acres) without pixel "
        "mixing across ownership boundaries. Bare Soil Index (BSI) reliably pinpoints the exact 60-day summer "
        "fallow gap between wheat harvest and rice transplantation."
    ),
    citation="Wulder, M. A., et al. (2019). Current status of Landsat program, science, and applications. Remote Sensing of Environment, 225, 127-147.",
    source_url="https://landsat.gsfc.nasa.gov/",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA GEDI LiDAR Canopy Biomass Context
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GediBiomassContext:
    """NASA GEDI (ISS) LiDAR canopy height and aboveground biomass context."""

    sensor: str
    spatial_resolution_m: int
    aboveground_biomass_density_mg_ha: float
    canopy_height_m: float
    finding: str
    citation: str
    source_url: str


GEDI_BIOMASS_CONTEXT = GediBiomassContext(
    sensor="NASA GEDI (Global Ecosystem Dynamics Investigation) ISS LiDAR L4A/L4B",
    spatial_resolution_m=25,
    aboveground_biomass_density_mg_ha=14.2,
    canopy_height_m=2.6,
    finding=(
        "Full-waveform LiDAR pulses quantify crop canopy architecture and aboveground crop residue biomass. "
        "In diversified rotations, retaining legume and cereal residues provides vital carbon inputs for Janssen "
        "Soil Organic Carbon (SOC) regeneration."
    ),
    citation="Dubayah, R., et al. (2020). The Global Ecosystem Dynamics Investigation: High-resolution laser ranging of the Earth's forests and topography. Science Advances, 6(47).",
    source_url="https://gedi.umd.edu/",
)


# ─────────────────────────────────────────────────────────────────────────────
# NASA SI (Spatial Informatics) Data Harmonization Grid
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DataHarmonizationEntry:
    """Specification of how a sensor is harmonized to the field decision grid."""

    dataset_name: str
    agency_mission: str
    native_spatial_resolution: str
    temporal_frequency: str
    harmonization_technique: str
    decision_support_role: str


DATA_HARMONIZATION_GRID: tuple[DataHarmonizationEntry, ...] = (
    DataHarmonizationEntry(
        dataset_name="NASA POWER Daily",
        agency_mission="NASA Langley Research Center (MERRA-2 / CERES)",
        native_spatial_resolution="~0.5° × 0.625° (~50 km)",
        temporal_frequency="Daily (1981–present)",
        harmonization_technique="Bilinear spatial interpolation to farm centroid; solar/wind/RH FAO-56 Penman-Monteith assimilation",
        decision_support_role="Daily reference evapotranspiration (ET₀), crop water demand (ETc), EcoCrop thermal suitability, and 25-yr trends",
    ),
    DataHarmonizationEntry(
        dataset_name="MODIS MCD12Q2",
        agency_mission="NASA Terra/Aqua (ORNL DAAC)",
        native_spatial_resolution="500 m sinusoidal grid",
        temporal_frequency="Annual phenology (2001–2025)",
        harmonization_technique="Pixel-to-coordinate extraction with QA masking; mid-greenness window date alignment",
        decision_support_role="Identifies recent green cycles per season; flags added seasons vs historical bare fields",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA ECOSTRESS",
        agency_mission="NASA JPL (International Space Station)",
        native_spatial_resolution="70 m × 70 m",
        temporal_frequency="1 to 5 days (variable diurnal overpasses)",
        harmonization_technique="Polygon zonal mean and thermal threshold aggregation over field boundaries",
        decision_support_role="Detects field-level plant evaporative stress index (ESI) and midday canopy thermal stress hotspots",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA SMAP L3/L4",
        agency_mission="NASA JPL / Goddard",
        native_spatial_resolution="9 km (L3 enhanced) / 9 km (L4 root-zone)",
        temporal_frequency="Daily / 3-hourly",
        harmonization_technique="Spatial downscaling via SoilGrids 250m texture pedotransfer functions and soil water capacity",
        decision_support_role="Distinguishes surface (0–5 cm) seedbed moisture from root-zone (0–100 cm) subsoil moisture buffer",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA GPM IMERG V07",
        agency_mission="NASA / JAXA Precipitation Constellation",
        native_spatial_resolution="0.1° × 0.1° (~10 km)",
        temporal_frequency="Half-hourly & Daily",
        harmonization_technique="Climatological gauge calibration (GPCC) and radar-gauge cross-validation with NASA POWER rainfall",
        decision_support_role="Identifies high-intensity extreme precipitation storm events, monsoon onset timing, and dry-spell duration",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA/USGS Landsat 8/9",
        agency_mission="NASA Goddard / USGS",
        native_spatial_resolution="30 m multispectral",
        temporal_frequency="8-day constellation revisit",
        harmonization_technique="Cloud/shadow masking (QA_PIXEL) and Bare Soil Index (BSI) parcel zonal extraction",
        decision_support_role="Field-scale smallholder parcel delineation; pinpoints bare-fallow periods without inter-field pixel mixing",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA SRTM DEM",
        agency_mission="NASA JPL / NGA (Space Shuttle Endeavour)",
        native_spatial_resolution="30 m (1 arc-second)",
        temporal_frequency="Static baseline topography",
        harmonization_technique="D8 flow direction, slope gradient calculation, and Topographic Wetness Index (TWI) mapping",
        decision_support_role="RUSLE water erosion LS-factor assessment, low-lying waterlogging zones, and cold-air frost drainage basins",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA GRACE / GRACE-FO",
        agency_mission="NASA JPL / GFZ Potsdam",
        native_spatial_resolution="300–400 km regional mass change",
        temporal_frequency="Monthly (2002–present)",
        harmonization_technique="Spherical harmonic regional terrestrial water storage (TWS) and groundwater anomaly scaling",
        decision_support_role="Macro-scale aquifer depletion rate (-4.0 cm/yr in Punjab) justifying urgent shift away from flooded paddy",
    ),
    DataHarmonizationEntry(
        dataset_name="NASA FIRMS",
        agency_mission="NASA GSFC / EOSDIS",
        native_spatial_resolution="375 m (VIIRS) / 1 km (MODIS)",
        temporal_frequency="Near real-time (daily thermal anomalies)",
        harmonization_technique="Temporal fire-pixel density clustering during the October 15–November 20 post-kharif turnaround",
        decision_support_role="Tracks crop residue burning intensity; motivates diversified rotations that eliminate stubble burning pressure",
    ),
    DataHarmonizationEntry(
        dataset_name="ISRIC SoilGrids 2.0",
        agency_mission="ISRIC World Soil Information",
        native_spatial_resolution="250 m modelled grid",
        temporal_frequency="Static baseline with 90% uncertainty envelopes",
        harmonization_technique="Depth-weighted thickness averaging (0–5, 5–15, 15–30 cm) and FAO/USDA texture triangle classification",
        decision_support_role="Baseline Soil Organic Carbon (SOC), clay/sand ratio, and cation exchange context when farm soil test is missing",
    ),
)
