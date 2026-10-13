"""Simplified soil-state and nutrient-balance estimation (Feature E).

This module implements a **simplified** Nitrogen balance and soil organic-carbon
change estimate using published FAO and IPCC Tier 1 relationships.

References
----------
- FAO Fertilizer and Plant Nutrition Bulletin 16 (2006): Nutrient balance
- IPCC 2006 Guidelines Vol. 4 Ch. 2: N₂O emissions from managed soils
- Brady & Weil, *The Nature and Properties of Soils*, 15th ed. (2017)
- Janssen (1984): one-compartment first-order SOC decay model

IMPORTANT CALIBRATION LIMITATIONS
----------------------------------
- The nitrogen-fixation credit for legumes is a rough FAO estimate (20–40 kg N/ha)
  and has NOT been calibrated to Punjab conditions.
- The SOC decay constant (k = 0.02–0.04 yr⁻¹) is from temperate studies and may
  not transfer to Indo-Gangetic Plain conditions without local validation.
- Residue-return fractions are assumed defaults; actual farmer practice varies.
- This model does not account for irrigation-related nutrient leaching,
  volatilisation from urea, or micronutrient dynamics.
- All outputs are labelled as "Simplified estimate — not calibrated to local
  conditions" and should be reviewed by a qualified agronomist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


# --- Published reference values ---

# FAO Fertilizer and Plant Nutrition Bulletin 16
LEGUME_N_FIXATION_RANGE_KG_HA = (20.0, 40.0)  # conservative FAO range
DEFAULT_RESIDUE_N_RETURN_FRACTION = 0.3  # fraction of above-ground N returned

# IPCC 2006 Vol 4 Ch 5 / Brady & Weil (2017) Table 12.3
SOC_DECAY_CONSTANTS = {
    "tropical_wet": 0.04,   # yr⁻¹
    "tropical_dry": 0.03,
    "temperate": 0.02,
    "subtropical_semiarid": 0.025,  # interpolated for Punjab
}

# Approximate crop residue C:N ratios from Brady & Weil (2017)
RESIDUE_CN_RATIOS: dict[str, float] = {
    "rice": 60.0,
    "wheat": 80.0,
    "maize": 55.0,
    "cotton": 40.0,
    "moong": 20.0,
    "soybean": 20.0,
    "chickpea": 25.0,
    "pearl_millet": 50.0,
    "rapeseed_mustard": 35.0,
    "potato": 25.0,
}

# Approximate above-ground dry-matter production (t/ha) — Punjab field-guide ranges
RESIDUE_DRY_MATTER_T_HA: dict[str, tuple[float, float]] = {
    "rice": (5.0, 8.0),
    "wheat": (4.0, 6.0),
    "maize": (5.0, 7.0),
    "cotton": (2.0, 4.0),
    "moong": (1.0, 2.0),
    "soybean": (2.0, 3.5),
    "chickpea": (1.5, 2.5),
    "pearl_millet": (3.0, 5.0),
    "rapeseed_mustard": (2.0, 3.5),
    "potato": (1.0, 2.0),
}


@dataclass(frozen=True)
class NutrientBalanceEstimate:
    """Simplified per-season N balance from published FAO/IPCC relationships."""

    crop_id: str
    crop_name: str
    season: str
    legume_n_credit_kg_ha: tuple[float, float] | None  # (low, high) or None
    residue_n_return_kg_ha: tuple[float, float]  # (low, high)
    residue_c_input_kg_ha: tuple[float, float]
    method_description: str
    calibration_warning: str


@dataclass(frozen=True)
class SOCChangeEstimate:
    """Janssen (1984) first-order SOC change for one rotation cycle."""

    initial_soc_percent: float | None
    annual_c_input_kg_ha: tuple[float, float]
    decay_constant_yr: float
    estimated_annual_change_direction: str  # "likely_increase", "likely_decrease", "uncertain"
    method_description: str
    calibration_warning: str


@dataclass(frozen=True)
class SoilStateReport:
    """Complete soil-state estimate for a rotation with full disclosure."""

    nutrient_estimates: tuple[NutrientBalanceEstimate, ...]
    soc_estimate: SOCChangeEstimate | None
    required_inputs: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    limitations: tuple[str, ...]


def estimate_nutrient_balance(
    crop_ids: Sequence[str],
    crop_names: Sequence[str],
    seasons: Sequence[str],
    is_legume: Mapping[str, bool],
) -> tuple[NutrientBalanceEstimate, ...]:
    """Estimate per-crop N contributions using FAO reference ranges.

    This does NOT estimate total N requirement or recommend fertiliser rates.
    """
    estimates: list[NutrientBalanceEstimate] = []
    for crop_id, crop_name, season in zip(crop_ids, crop_names, seasons):
        legume_credit = LEGUME_N_FIXATION_RANGE_KG_HA if is_legume.get(crop_id, False) else None

        dm_range = RESIDUE_DRY_MATTER_T_HA.get(crop_id, (2.0, 4.0))
        cn_ratio = RESIDUE_CN_RATIOS.get(crop_id, 40.0)

        # Residue N = DM (kg) × fraction_returned × (1/CN)
        # DM in t/ha → kg/ha = ×1000
        n_low = dm_range[0] * 1000 * DEFAULT_RESIDUE_N_RETURN_FRACTION / cn_ratio
        n_high = dm_range[1] * 1000 * DEFAULT_RESIDUE_N_RETURN_FRACTION / cn_ratio

        # Residue C input = DM × 0.42 (carbon fraction of dry matter) × fraction returned
        c_low = dm_range[0] * 1000 * 0.42 * DEFAULT_RESIDUE_N_RETURN_FRACTION
        c_high = dm_range[1] * 1000 * 0.42 * DEFAULT_RESIDUE_N_RETURN_FRACTION

        estimates.append(NutrientBalanceEstimate(
            crop_id=crop_id,
            crop_name=crop_name,
            season=season,
            legume_n_credit_kg_ha=legume_credit,
            residue_n_return_kg_ha=(round(n_low, 1), round(n_high, 1)),
            residue_c_input_kg_ha=(round(c_low, 1), round(c_high, 1)),
            method_description=(
                "Residue N and C estimated from published dry-matter ranges, "
                "assumed 30% residue-return fraction, and literature C:N ratios. "
                "FAO Bulletin 16 legume N-fixation range applied where applicable."
            ),
            calibration_warning=(
                "Simplified estimate — not calibrated to local Punjab conditions. "
                "Actual residue return depends on farmer practice (burning, baling, incorporation). "
                "Does not account for fertiliser inputs, leaching, or volatilisation."
            ),
        ))
    return tuple(estimates)


def estimate_soc_change(
    crop_ids: Sequence[str],
    initial_soc_percent: float | None,
    climate_zone: str = "subtropical_semiarid",
) -> SOCChangeEstimate | None:
    """One-compartment first-order SOC model after Janssen (1984).

    SOC_change = C_input − k × SOC_stock
    where k is a climate-zone-specific decay constant.
    """
    k = SOC_DECAY_CONSTANTS.get(climate_zone)
    if k is None:
        return None

    # Sum annual C inputs from all crops in the rotation
    total_c_low = 0.0
    total_c_high = 0.0
    for crop_id in crop_ids:
        dm = RESIDUE_DRY_MATTER_T_HA.get(crop_id, (2.0, 4.0))
        total_c_low += dm[0] * 1000 * 0.42 * DEFAULT_RESIDUE_N_RETURN_FRACTION
        total_c_high += dm[1] * 1000 * 0.42 * DEFAULT_RESIDUE_N_RETURN_FRACTION

    # Determine direction without computing an absolute change
    # (because we may not have initial SOC)
    if initial_soc_percent is not None and initial_soc_percent > 0:
        # Assume 0-20 cm depth, bulk density ~1.4 Mg/m³
        soc_stock_kg_ha = initial_soc_percent / 100 * 1.4e6 * 0.20
        annual_loss = k * soc_stock_kg_ha
        if total_c_low > annual_loss:
            direction = "likely_increase"
        elif total_c_high < annual_loss:
            direction = "likely_decrease"
        else:
            direction = "uncertain"
    else:
        direction = "uncertain"

    return SOCChangeEstimate(
        initial_soc_percent=initial_soc_percent,
        annual_c_input_kg_ha=(round(total_c_low, 0), round(total_c_high, 0)),
        decay_constant_yr=k,
        estimated_annual_change_direction=direction,
        method_description=(
            "Janssen (1984) one-compartment first-order decay model. "
            f"Climate zone: {climate_zone}, k = {k} yr⁻¹. "
            "Assumes 0–20 cm depth, bulk density 1.4 Mg/m³, C fraction 0.42 of dry matter."
        ),
        calibration_warning=(
            "This model has NOT been validated for Indo-Gangetic Plain conditions. "
            "The decay constant is from temperate/subtropical studies. "
            "Actual SOC dynamics depend on tillage, irrigation, temperature regime, "
            "clay content, and microbial activity — none of which are modelled here. "
            "Treat the direction indicator as a hypothesis, not a prediction."
        ),
    )


def build_soil_state_report(
    crop_ids: Sequence[str],
    crop_names: Sequence[str],
    seasons: Sequence[str],
    is_legume: Mapping[str, bool],
    initial_soc_percent: float | None = None,
) -> SoilStateReport:
    """Assemble a fully-disclosed soil-state report for a rotation plan."""
    nutrient_estimates = estimate_nutrient_balance(crop_ids, crop_names, seasons, is_legume)
    soc_estimate = estimate_soc_change(crop_ids, initial_soc_percent)

    required = (
        "Crop residue management practice (returned, burned, removed)",
        "Initial soil organic carbon (%) from laboratory analysis",
        "Soil bulk density (Mg/m³) from field measurement",
        "Applied fertiliser rates (kg N/ha) per crop",
        "Irrigation method and scheduling",
    )
    missing: list[str] = []
    if initial_soc_percent is None:
        missing.append("Initial soil organic carbon (%) — SOC direction estimate is less reliable")
    missing.append("Residue management practice — a default 30% return fraction is assumed")
    missing.append("Applied fertiliser rates — not modelled")

    limitations = (
        "All estimates use published reference ranges, not field-calibrated values.",
        "Legume N-fixation credit is a literature range (FAO Bulletin 16), not measured inoculation response.",
        "Residue C:N ratios are textbook values; actual values vary by cultivar, maturity, and method.",
        "SOC model is a first-order approximation; real SOC dynamics are nonlinear and site-specific.",
        "No micronutrient, phosphorus, or potassium balance is estimated.",
        "This module is provided for educational comparison only — consult a soil scientist for farm decisions.",
    )

    return SoilStateReport(
        nutrient_estimates=nutrient_estimates,
        soc_estimate=soc_estimate,
        required_inputs=required,
        missing_inputs=tuple(missing),
        limitations=limitations,
    )
