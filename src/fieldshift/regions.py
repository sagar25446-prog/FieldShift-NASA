"""Global multi-region framework for FieldShift.

Provides region-specific configurations, crop catalogs, seasonal calendars,
agronomic sources, and coordinate-based region matching to make FieldShift
applicable to agricultural regions worldwide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RegionDefinition:
    """Full regional specification for global crop rotation planning."""

    id: str
    name: str
    country: str
    flag: str
    climate_zone: str
    koppen_code: str
    latitude: float
    longitude: float
    season_cycle: tuple[str, ...]
    season_display_names: Mapping[str, str]
    default_start_season: str
    catalog_filename: str
    rules_filename: str
    currency_symbol: str
    currency_code: str
    baseline_rotation_name: str
    baseline_rotation_crops: tuple[str, ...]
    baseline_water_mm: float
    groundwater_context: str
    description: str
    agronomic_sources: tuple[str, ...]
    soil_defaults: Mapping[str, float | str | bool] = field(default_factory=dict)


# Regional catalog definitions
REGIONS: dict[str, RegionDefinition] = {
    "punjab": RegionDefinition(
        id="punjab",
        name="Indo-Gangetic Plain (Punjab, India)",
        country="India",
        flag="🇮🇳",
        climate_zone="Monsoonal Subtropical (Hot semi-arid / humid subtropical)",
        koppen_code="BSh / Cwa",
        latitude=30.9010,
        longitude=75.8573,
        season_cycle=("kharif", "rabi", "summer"),
        season_display_names={
            "kharif": "Kharif (Monsoon: Jun – Oct)",
            "rabi": "Rabi (Winter: Nov – Apr)",
            "summer": "Summer / Zaid (Post-Rabi: Apr – Jun)",
        },
        default_start_season="kharif",
        catalog_filename="crops.json",
        rules_filename="rotation_rules.json",
        currency_symbol="₹",
        currency_code="INR",
        baseline_rotation_name="Continuous Rice–Wheat Monoculture",
        baseline_rotation_crops=("rice", "wheat", "moong"),
        baseline_water_mm=2600.0,
        groundwater_context="NASA GRACE detects -4.0 cm/yr groundwater decline; 78% of Punjab blocks overexploited.",
        description=(
            "The breadbasket of India, characterized by intensively irrigated alluvial soils, "
            "severe groundwater overdraft from flood-irrigated paddy rice, and post-harvest "
            "residue burning air quality crises."
        ),
        agronomic_sources=(
            "Punjab Agricultural University (PAU), Ludhiana",
            "Indian Council of Agricultural Research (ICAR)",
            "Commission for Agricultural Costs and Prices (CACP), GoI",
        ),
        soil_defaults={
            "texture": "medium",
            "ph": 7.4,
            "organic_carbon_percent": 0.55,
            "electrical_conductivity_ds_m": 0.35,
            "waterlogged": False,
            "highly_deteriorated_alkaline": False,
            "well_drained": True,
            "water_budget_mm": 800.0,
            "field_size_ha": 2.5,
        },
    ),
    "us_corn_belt": RegionDefinition(
        id="us_corn_belt",
        name="US Corn Belt (Iowa & Upper Midwest, USA)",
        country="United States",
        flag="🇺🇸",
        climate_zone="Humid Continental (Warm summer, cold winter)",
        koppen_code="Dfa",
        latitude=41.8780,
        longitude=-93.0977,
        season_cycle=("spring", "summer", "fall_cover"),
        season_display_names={
            "spring": "Spring (Planting: Apr – Jun)",
            "summer": "Summer (Peak Growth: Jul – Sep)",
            "fall_cover": "Fall / Overwinter Cover (Oct – Mar)",
        },
        default_start_season="spring",
        catalog_filename="regions/us_corn_belt_crops.json",
        rules_filename="regions/us_corn_belt_rules.json",
        currency_symbol="$",
        currency_code="USD",
        baseline_rotation_name="Conventional Continuous Corn / Corn–Soybean",
        baseline_rotation_crops=("corn", "soybean", "cereal_rye"),
        baseline_water_mm=650.0,
        groundwater_context="Nitrate leaching into Mississippi basin; Ogallala and shallow aquifer drawdown in western edge.",
        description=(
            "Highly productive glaciated Mollisols (prairie soils) facing high synthetic N runoff, "
            "erosion, and soil organic matter depletion from simplified 2-year corn-soybean systems. "
            "Diverse 3- to 4-year rotations with small grains and legumes drastically cut fertilizer needs."
        ),
        agronomic_sources=(
            "USDA Agricultural Research Service (USDA-ARS)",
            "Iowa State University Extension and Outreach",
            "Marsden Farm Long-Term Crop Rotation Experiment",
        ),
        soil_defaults={
            "texture": "medium",
            "ph": 6.8,
            "organic_carbon_percent": 2.80,
            "electrical_conductivity_ds_m": 0.15,
            "waterlogged": False,
            "highly_deteriorated_alkaline": False,
            "well_drained": True,
            "water_budget_mm": 600.0,
            "field_size_ha": 40.0,
        },
    ),
    "mediterranean": RegionDefinition(
        id="mediterranean",
        name="Mediterranean Basin (Andalusia, Spain / S. Europe)",
        country="Spain",
        flag="🇪🇸",
        climate_zone="Mediterranean (Hot, dry summer; mild, wet winter)",
        koppen_code="Csa",
        latitude=37.3891,
        longitude=-5.9845,
        season_cycle=("autumn_winter", "spring_summer"),
        season_display_names={
            "autumn_winter": "Autumn–Winter (Sowing & Rains: Oct – Mar)",
            "spring_summer": "Spring–Summer (Maturation & Dry Season: Apr – Sep)",
        },
        default_start_season="autumn_winter",
        catalog_filename="regions/mediterranean_crops.json",
        rules_filename="regions/mediterranean_rules.json",
        currency_symbol="€",
        currency_code="EUR",
        baseline_rotation_name="Continuous Cereal / Fallow (Secano)",
        baseline_rotation_crops=("durum_wheat", "sunflower"),
        baseline_water_mm=450.0,
        groundwater_context="Severe recurrent hydrological drought; Guadalquivir basin reservoir levels frequently drop below 25%.",
        description=(
            "Semi-arid rainfed and deficit-irrigated farming in Southern Europe. High vulnerability "
            "to spring heat waves and desertification. Legume integration (chickpea, faba bean) restores "
            "soil structure and conserves critical moisture."
        ),
        agronomic_sources=(
            "Instituto Andaluz de Investigación Agraria (IFAPA)",
            "Spanish Ministry of Agriculture, Fisheries and Food (MAPA)",
            "FAO Regional Office for Europe and Central Asia",
        ),
        soil_defaults={
            "texture": "medium",
            "ph": 7.9,
            "organic_carbon_percent": 0.85,
            "electrical_conductivity_ds_m": 0.40,
            "waterlogged": False,
            "highly_deteriorated_alkaline": False,
            "well_drained": True,
            "water_budget_mm": 400.0,
            "field_size_ha": 15.0,
        },
    ),
    "semi_arid_tropics": RegionDefinition(
        id="semi_arid_tropics",
        name="Semi-Arid Tropics (Maharashtra & Deccan, India)",
        country="India",
        flag="🇮🇳",
        climate_zone="Tropical Semi-Arid (Dry savanna / Vertisol belt)",
        koppen_code="BSh / Aw",
        latitude=19.0760,
        longitude=74.7421,
        season_cycle=("kharif", "rabi"),
        season_display_names={
            "kharif": "Kharif (Monsoon: Jun – Oct)",
            "rabi": "Rabi (Post-Monsoon: Nov – Mar)",
        },
        default_start_season="kharif",
        catalog_filename="regions/semi_arid_crops.json",
        rules_filename="regions/semi_arid_rules.json",
        currency_symbol="₹",
        currency_code="INR",
        baseline_rotation_name="Cotton / Sugarcane Monoculture",
        baseline_rotation_crops=("sorghum", "chickpea"),
        baseline_water_mm=550.0,
        groundwater_context="Hard-rock basalt aquifers with limited storage; acute farmer vulnerability to monsoon breaks.",
        description=(
            "Deep black clay soils (Vertisols) in rainfed peninsular India. Highly sensitive to "
            "monsoon droughts. Drought-resilient millets (Bajra, Jowar) and nitrogen-fixing pulses "
            "(Pigeonpea, Chickpea) stabilize income and protect groundwater."
        ),
        agronomic_sources=(
            "International Crops Research Institute for the Semi-Arid Tropics (ICRISAT)",
            "Mahatma Phule Krishi Vidyapeeth (MPKV), Rahuri",
            "Indian Council of Agricultural Research (ICAR-CRIDA)",
        ),
        soil_defaults={
            "texture": "fine",
            "ph": 7.8,
            "organic_carbon_percent": 0.45,
            "electrical_conductivity_ds_m": 0.30,
            "waterlogged": False,
            "highly_deteriorated_alkaline": False,
            "well_drained": False,
            "water_budget_mm": 500.0,
            "field_size_ha": 3.0,
        },
    ),
}


def list_regions() -> list[RegionDefinition]:
    """Return all supported global regions."""
    return list(REGIONS.values())


def get_region(region_id: str) -> RegionDefinition:
    """Retrieve a region definition by ID, defaulting to Punjab if not found."""
    return REGIONS.get(region_id, REGIONS["punjab"])


def detect_region_from_coordinates(latitude: float, longitude: float) -> RegionDefinition:
    """Infer the most representative agricultural archetype from global coordinates.

    Uses geographic bounding heuristics first, then spherical distance to region centers.
    """
    # North America: temperate corn belt archetype
    if 24.0 <= latitude <= 52.0 and -130.0 <= longitude <= -65.0:
        return REGIONS["us_corn_belt"]

    # Southern Europe / Mediterranean Basin:
    if 34.0 <= latitude <= 46.0 and -12.0 <= longitude <= 35.0:
        return REGIONS["mediterranean"]

    # Northwestern India / Indo-Gangetic Plains:
    if 26.0 <= latitude <= 36.0 and 70.0 <= longitude <= 88.0:
        return REGIONS["punjab"]

    # Peninsular India / Semi-arid tropics:
    if 8.0 <= latitude <= 25.0 and 70.0 <= longitude <= 85.0:
        return REGIONS["semi_arid_tropics"]

    # Fallback: Spherical distance to regional archetypes
    def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        # Haversine approximation
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return 2 * 6371 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    closest = min(
        REGIONS.values(),
        key=lambda reg: _distance(latitude, longitude, reg.latitude, reg.longitude),
    )
    return closest
