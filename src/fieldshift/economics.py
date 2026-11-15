"""Optional economics calculations, gated on verified crop-level inputs.

The current catalogue has no complete, source-verified price, yield and cost
triplets. Missing inputs stay missing; this module never substitutes zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping, Sequence


ECONOMIC_DISCLAIMERS: tuple[str, ...] = (
    "Economic comparison is unavailable until crop-level prices, yields and costs have traceable sources.",
    "An announced support price does not establish a realised farm price or profit.",
)


@dataclass(frozen=True)
class CropEconomics:
    """Indicative economic metrics for one crop in a rotation."""

    crop_id: str
    crop_name: str
    season: str
    msp_inr_per_q: float | None
    benchmark_yield_q_ha: float | None
    benchmark_cost_inr_ha: float | None
    indicative_gross_revenue_inr_ha: float | None
    indicative_gross_margin_inr_ha: float | None
    msp_procurement_assured: bool
    notes: str


@dataclass(frozen=True)
class RotationEconomics:
    """Aggregated indicative economics for a candidate rotation sequence."""

    crop_economics: tuple[CropEconomics, ...]
    total_cost_inr_ha: float | None
    total_revenue_inr_ha: float | None
    total_margin_inr_ha: float | None
    water_productivity_inr_per_m3: float | None
    disclaimers: tuple[str, ...] = ECONOMIC_DISCLAIMERS


def compute_crop_economics(crop: Mapping[str, object], season: str) -> CropEconomics:
    """Compute indicative economics for a single crop."""
    econ = crop.get("indicative_economics") or {}
    crop_id = str(crop.get("id", ""))
    crop_name = str(crop.get("name", crop_id))

    verified = econ.get("status") == "source_verified" and bool(econ.get("source_urls"))
    price = econ.get("realised_price_inr_per_q") if verified else None
    yield_input = econ.get("benchmark_yield_q_ha") if verified else None
    cost_input = econ.get("benchmark_cost_inr_ha") if verified else None
    price_val = float(price) if price is not None else None
    yield_val = float(yield_input) if yield_input is not None else None
    cost_val = float(cost_input) if cost_input is not None else None
    rev_val = price_val * yield_val if price_val is not None and yield_val is not None else None
    margin_val = rev_val - cost_val if rev_val is not None and cost_val is not None else None

    return CropEconomics(
        crop_id=crop_id,
        crop_name=crop_name,
        season=season,
        msp_inr_per_q=price_val,
        benchmark_yield_q_ha=yield_val,
        benchmark_cost_inr_ha=cost_val,
        indicative_gross_revenue_inr_ha=rev_val,
        indicative_gross_margin_inr_ha=margin_val,
        msp_procurement_assured=False,
        notes=str(econ.get("notes", "")),
    )


def compute_rotation_economics(
    crops: Sequence[Mapping[str, object]],
    seasons: Sequence[str],
    net_irrigation_mm: float | None = None,
) -> RotationEconomics:
    """Compute indicative economics for a sequence of crops in a rotation."""
    items: list[CropEconomics] = []
    total_cost: float | None = 0.0
    total_rev: float | None = 0.0
    total_margin: float | None = 0.0

    for crop, season in zip(crops, seasons):
        ce = compute_crop_economics(crop, season)
        items.append(ce)
        if total_cost is not None and ce.benchmark_cost_inr_ha is not None:
            total_cost += ce.benchmark_cost_inr_ha
        else:
            total_cost = None
        if ce.indicative_gross_revenue_inr_ha is not None and total_rev is not None:
            total_rev += ce.indicative_gross_revenue_inr_ha
        else:
            total_rev = None

        if ce.indicative_gross_margin_inr_ha is not None and total_margin is not None:
            total_margin += ce.indicative_gross_margin_inr_ha
        else:
            total_margin = None

    # Water productivity: ₹ gross margin per m³ of irrigation water
    # 1 mm over 1 ha = 10 m³
    water_prod: float | None = None
    if total_margin is not None and net_irrigation_mm is not None and net_irrigation_mm > 0:
        water_volume_m3_ha = net_irrigation_mm * 10.0
        water_prod = total_margin / water_volume_m3_ha

    return RotationEconomics(
        crop_economics=tuple(items),
        total_cost_inr_ha=total_cost,
        total_revenue_inr_ha=total_rev,
        total_margin_inr_ha=total_margin,
        water_productivity_inr_per_m3=water_prod,
    )


@dataclass(frozen=True)
class WaterSavingsComparison:
    """Comparative water and economic impact vs Rice–Wheat baseline."""

    baseline_sequence: tuple[str, ...]
    candidate_sequence: tuple[str, ...]
    baseline_net_irrigation_mm: float
    candidate_net_irrigation_mm: float
    water_saved_mm: float
    water_saved_pct: float
    water_saved_m3_per_ha: float
    water_saved_litres_per_ha: float
    cost_diff_inr_ha: float | None
    margin_diff_inr_ha: float | None
    headline_summary: str


def compare_vs_rice_wheat_baseline(
    candidate_crops: Sequence[Mapping[str, object]],
    candidate_seasons: Sequence[str],
    candidate_irrigation_mm: float,
    baseline_irrigation_mm: float | None = None,
    baseline_cost_ha: float | None = None,
    baseline_margin_ha: float | None = None,
) -> WaterSavingsComparison:
    """Compare modelled irrigation with an explicitly supplied baseline.

    The caller must validate and cite the baseline. The result does not measure
    aquifer withdrawals or actual water saved on a field.
    """
    if baseline_irrigation_mm is None or not isfinite(baseline_irrigation_mm) or baseline_irrigation_mm <= 0:
        raise ValueError("A positive, documented baseline irrigation value is required.")
    if not isfinite(candidate_irrigation_mm) or candidate_irrigation_mm < 0:
        raise ValueError("Candidate irrigation must be a nonnegative finite value.")
    cand_econ = compute_rotation_economics(candidate_crops, candidate_seasons, candidate_irrigation_mm)
    saved_mm = baseline_irrigation_mm - candidate_irrigation_mm
    saved_pct = (saved_mm / baseline_irrigation_mm * 100.0) if baseline_irrigation_mm > 0 else 0.0
    saved_m3 = saved_mm * 10.0
    saved_litres = saved_m3 * 1000.0

    cost_diff = (cand_econ.total_cost_inr_ha - baseline_cost_ha) if cand_econ.total_cost_inr_ha is not None and baseline_cost_ha is not None else None
    margin_diff = (cand_econ.total_margin_inr_ha - baseline_margin_ha) if cand_econ.total_margin_inr_ha is not None and baseline_margin_ha is not None else None

    headline = (
        f"Modelled net irrigation difference: {saved_mm:+.0f} mm ({saved_pct:+.1f}%) "
        f"versus the supplied baseline, equivalent to {saved_m3:+,.0f} m³/ha "
        "of irrigation demand. This is not observed groundwater saved."
    )

    return WaterSavingsComparison(
        baseline_sequence=("Rice", "Wheat"),
        candidate_sequence=tuple(str(c.get("name", c.get("id", ""))) for c in candidate_crops),
        baseline_net_irrigation_mm=baseline_irrigation_mm,
        candidate_net_irrigation_mm=candidate_irrigation_mm,
        water_saved_mm=saved_mm,
        water_saved_pct=saved_pct,
        water_saved_m3_per_ha=saved_m3,
        water_saved_litres_per_ha=saved_litres,
        cost_diff_inr_ha=cost_diff,
        margin_diff_inr_ha=margin_diff,
        headline_summary=headline,
    )
