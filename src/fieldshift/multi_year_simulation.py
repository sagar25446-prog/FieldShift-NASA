"""Multi-year rotation trajectory simulation module (3–5 year planning horizons).

Models cumulative water savings, Soil Organic Carbon (SOC) trajectory via
Janssen (1984) first-order kinetics, and soil Nitrogen balance over multiple
successive agricultural years.

Methodological References
-------------------------
- Janssen, B. H. (1984). A simple method for calculating decomposition and
  accumulation of 'young' soil organic matter. Plant and Soil, 76(1), 297-304.
- IPCC (2006) Guidelines for National Greenhouse Gas Inventories, Vol. 4 (AFOLU),
  Ch. 5: Cropland.
- FAO Fertilizer and Plant Nutrition Bulletin 16 (2006): Guide to nutrient balance
  calculations.
- Brady & Weil (2017). *The Nature and Properties of Soils*, 15th ed. Pearson.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence


# Published dry matter residue and biological N fixation parameters
# (C source: Brady & Weil 2017; FAO Bulletin 16; PAU Handbooks)
CROP_ANNUAL_PROPERTIES: dict[str, dict[str, float | bool]] = {
    "rice": {"is_legume": False, "c_input_kg_ha": 2200.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 120.0, "default_irrigation_mm": 1750.0},
    "wheat": {"is_legume": False, "c_input_kg_ha": 1800.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 110.0, "default_irrigation_mm": 350.0},
    "maize": {"is_legume": False, "c_input_kg_ha": 2400.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 130.0, "default_irrigation_mm": 500.0},
    "corn": {"is_legume": False, "c_input_kg_ha": 2500.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 140.0, "default_irrigation_mm": 450.0},
    "cotton": {"is_legume": False, "c_input_kg_ha": 1200.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 90.0, "default_irrigation_mm": 650.0},
    "moong": {"is_legume": True, "c_input_kg_ha": 650.0, "n_fixation_kg_ha": 35.0, "n_uptake_kg_ha": 30.0, "default_irrigation_mm": 180.0},
    "soybean": {"is_legume": True, "c_input_kg_ha": 1100.0, "n_fixation_kg_ha": 55.0, "n_uptake_kg_ha": 60.0, "default_irrigation_mm": 400.0},
    "chickpea": {"is_legume": True, "c_input_kg_ha": 850.0, "n_fixation_kg_ha": 45.0, "n_uptake_kg_ha": 40.0, "default_irrigation_mm": 200.0},
    "pigeonpea": {"is_legume": True, "c_input_kg_ha": 1400.0, "n_fixation_kg_ha": 65.0, "n_uptake_kg_ha": 50.0, "default_irrigation_mm": 300.0},
    "pearl_millet": {"is_legume": False, "c_input_kg_ha": 1600.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 75.0, "default_irrigation_mm": 300.0},
    "sorghum": {"is_legume": False, "c_input_kg_ha": 1700.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 80.0, "default_irrigation_mm": 350.0},
    "rapeseed_mustard": {"is_legume": False, "c_input_kg_ha": 1100.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 70.0, "default_irrigation_mm": 250.0},
    "potato": {"is_legume": False, "c_input_kg_ha": 600.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 100.0, "default_irrigation_mm": 450.0},
    "cereal_rye": {"is_legume": False, "c_input_kg_ha": 1500.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 40.0, "default_irrigation_mm": 100.0},
    "alfalfa": {"is_legume": True, "c_input_kg_ha": 2800.0, "n_fixation_kg_ha": 160.0, "n_uptake_kg_ha": 80.0, "default_irrigation_mm": 550.0},
    "durum_wheat": {"is_legume": False, "c_input_kg_ha": 1700.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 95.0, "default_irrigation_mm": 300.0},
    "sunflower": {"is_legume": False, "c_input_kg_ha": 1300.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 70.0, "default_irrigation_mm": 280.0},
    "barley": {"is_legume": False, "c_input_kg_ha": 1500.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 65.0, "default_irrigation_mm": 220.0},
    "oats": {"is_legume": False, "c_input_kg_ha": 1400.0, "n_fixation_kg_ha": 0.0, "n_uptake_kg_ha": 60.0, "default_irrigation_mm": 250.0},
    "green_manure": {"is_legume": True, "c_input_kg_ha": 2200.0, "n_fixation_kg_ha": 80.0, "n_uptake_kg_ha": 20.0, "default_irrigation_mm": 150.0},
    "berseem": {"is_legume": True, "c_input_kg_ha": 2000.0, "n_fixation_kg_ha": 90.0, "n_uptake_kg_ha": 40.0, "default_irrigation_mm": 400.0},
}


@dataclass(frozen=True)
class YearlyStep:
    """One year in the multi-year rotation simulation."""

    year: int
    crops: tuple[str, ...]
    irrigation_mm: float
    cumulative_irrigation_mm: float
    baseline_irrigation_mm: float
    cumulative_baseline_irrigation_mm: float
    annual_water_saved_mm: float
    cumulative_water_saved_mm: float
    cumulative_water_saved_m3_ha: float
    soc_percent: float
    annual_c_input_kg_ha: float
    annual_n_balance_kg_ha: float
    cumulative_n_balance_kg_ha: float
    legumes_count: int


@dataclass(frozen=True)
class MultiYearSimulationReport:
    """Complete 3- to 5-year rotational simulation outcome."""

    horizon_years: int
    yearly_steps: tuple[YearlyStep, ...]
    initial_soc_percent: float
    final_soc_percent: float
    soc_change_absolute_percent: float
    total_water_saved_mm: float
    total_water_saved_m3_ha: float
    total_n_benefit_kg_ha: float
    average_annual_irrigation_mm: float
    headline_narrative: str
    methodological_disclaimer: str
    sources: tuple[str, ...]


def simulate_multi_year_rotation(
    rotation_crop_ids: Sequence[str],
    horizon_years: int = 3,
    initial_soc_percent: float = 0.55,
    candidate_annual_irrigation_mm: float | None = None,
    baseline_annual_irrigation_mm: float = 2100.0,  # Continuous Rice-Wheat default
    soil_depth_m: float = 0.20,
    bulk_density_g_cm3: float = 1.35,
    decay_constant_yr: float = 0.025,
    humification_fraction: float = 0.18,
) -> MultiYearSimulationReport:
    """Simulate multi-year dynamics across 3 to 5 years.

    Calculates:
    - Cumulative water consumption vs baseline.
    - SOC progression using discrete Janssen kinetics:
        SOC_{t} = SOC_{t-1} * (1 - k) + h * (C_input / topsoil_mass_ha) * 100
    - Soil N balance tracking legume biological fixation vs crop uptake.
    """
    if horizon_years not in (3, 4, 5):
        horizon_years = 3

    # Soil mass in top 20cm of 1 ha:
    # 1 ha = 10,000 m2; Volume = 10,000 * 0.20 = 2,000 m3
    # Mass = 2,000 m3 * 1,350 kg/m3 = 2,700,000 kg soil
    topsoil_mass_kg_ha = 10_000.0 * soil_depth_m * (bulk_density_g_cm3 * 1000.0)

    # Determine annual default irrigation from crops if not provided
    auto_irrigation_mm = sum(
        float(CROP_ANNUAL_PROPERTIES.get(cid, {}).get("default_irrigation_mm", 300.0))
        for cid in rotation_crop_ids
    )
    actual_annual_irrigation_mm = candidate_annual_irrigation_mm if candidate_annual_irrigation_mm is not None else auto_irrigation_mm

    # Annual C input and N balance from crops in the rotation
    annual_c_input = sum(
        float(CROP_ANNUAL_PROPERTIES.get(cid, {}).get("c_input_kg_ha", 1000.0))
        for cid in rotation_crop_ids
    )
    annual_n_fixed = sum(
        float(CROP_ANNUAL_PROPERTIES.get(cid, {}).get("n_fixation_kg_ha", 0.0))
        for cid in rotation_crop_ids
    )
    annual_n_uptake = sum(
        float(CROP_ANNUAL_PROPERTIES.get(cid, {}).get("n_uptake_kg_ha", 80.0))
        for cid in rotation_crop_ids
    )
    annual_n_balance = annual_n_fixed - annual_n_uptake
    legumes_count = sum(1 for cid in rotation_crop_ids if CROP_ANNUAL_PROPERTIES.get(cid, {}).get("is_legume", False))

    steps: list[YearlyStep] = []
    current_soc = initial_soc_percent
    cumulative_candidate_water = 0.0
    cumulative_baseline_water = 0.0
    cumulative_n = 0.0

    for yr in range(1, horizon_years + 1):
        cumulative_candidate_water += actual_annual_irrigation_mm
        cumulative_baseline_water += baseline_annual_irrigation_mm
        annual_saved_mm = max(0.0, baseline_annual_irrigation_mm - actual_annual_irrigation_mm)
        cum_saved_mm = cumulative_baseline_water - cumulative_candidate_water
        cum_saved_m3 = cum_saved_mm * 10.0  # 1 mm on 1 ha = 10 m3

        # Janssen (1984) SOC progression
        soc_loss = current_soc * decay_constant_yr
        soc_gain_pct = (annual_c_input * humification_fraction / topsoil_mass_kg_ha) * 100.0
        current_soc = max(0.1, current_soc - soc_loss + soc_gain_pct)

        cumulative_n += annual_n_balance

        steps.append(
            YearlyStep(
                year=yr,
                crops=tuple(rotation_crop_ids),
                irrigation_mm=round(actual_annual_irrigation_mm, 1),
                cumulative_irrigation_mm=round(cumulative_candidate_water, 1),
                baseline_irrigation_mm=round(baseline_annual_irrigation_mm, 1),
                cumulative_baseline_irrigation_mm=round(cumulative_baseline_water, 1),
                annual_water_saved_mm=round(annual_saved_mm, 1),
                cumulative_water_saved_mm=round(cum_saved_mm, 1),
                cumulative_water_saved_m3_ha=round(cum_saved_m3, 1),
                soc_percent=round(current_soc, 3),
                annual_c_input_kg_ha=round(annual_c_input, 1),
                annual_n_balance_kg_ha=round(annual_n_balance, 1),
                cumulative_n_balance_kg_ha=round(cumulative_n, 1),
                legumes_count=legumes_count,
            )
        )

    soc_change = steps[-1].soc_percent - initial_soc_percent
    total_saved_mm = steps[-1].cumulative_water_saved_mm
    total_saved_m3 = steps[-1].cumulative_water_saved_m3_ha
    final_soc = steps[-1].soc_percent

    direction_str = "improved" if soc_change >= 0 else "reduced"
    headline = (
        f"Over {horizon_years} years, this rotation conserves {total_saved_mm:,.0f} mm of irrigation water "
        f"({total_saved_m3:,.0f} m³/ha) vs continuous monoculture while soil organic carbon is "
        f"{direction_str} from {initial_soc_percent:.2f}% to {final_soc:.2f}%."
    )

    disclaimer = (
        "Simplified multi-year simulation based on published Janssen (1984) decomposition kinetics and "
        "FAO/IPCC Tier 1 relationships. Actual farm outcomes depend on management, weather, and tillage."
    )

    sources = (
        "https://doi.org/10.1007/BF02206992",  # Janssen 1984
        "https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol4.html",  # IPCC 2006
        "https://www.fao.org/4/a0443e/a0443e00.htm",  # FAO Bulletin 16
    )

    return MultiYearSimulationReport(
        horizon_years=horizon_years,
        yearly_steps=tuple(steps),
        initial_soc_percent=initial_soc_percent,
        final_soc_percent=final_soc,
        soc_change_absolute_percent=round(soc_change, 3),
        total_water_saved_mm=round(total_saved_mm, 1),
        total_water_saved_m3_ha=round(total_saved_m3, 1),
        total_n_benefit_kg_ha=round(steps[-1].cumulative_n_balance_kg_ha, 1),
        average_annual_irrigation_mm=round(cumulative_candidate_water / horizon_years, 1),
        headline_narrative=headline,
        methodological_disclaimer=disclaimer,
        sources=sources,
    )
