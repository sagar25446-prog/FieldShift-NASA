"""Indicative economics module for FieldShift.

Provides transparent gross margin and water-productivity comparisons using
official Government of India Minimum Support Prices (MSP 2024–25) and Punjab
Agricultural University (PAU) indicative operational cost-of-cultivation data.

SCIENTIFIC & LEGAL DISCLOSURE:
These figures are indicative regional benchmarks published by CACP and PAU for
educational and planning comparison only. FieldShift does NOT predict farm
yields or guarantee profits. Actual realized yields, market prices, and
production costs vary widely based on weather, pest pressure, input costs, and
individual farm management.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


ECONOMIC_DISCLAIMERS: tuple[str, ...] = (
    "Indicative only: derived from Government of India Minimum Support Prices (MSP 2024–25) "
    "and PAU Farm Management Guide operational cost estimates.",
    "NOT a yield prediction or profit guarantee. Realized prices, yields, and production costs "
    "depend heavily on local soil, microclimate, input prices, and market access.",
    "Potato is not covered by central MSP; its figure reflects historical modal seasonal farmgate price benchmarks.",
)


@dataclass(frozen=True)
class CropEconomics:
    """Indicative economic metrics for one crop in a rotation."""

    crop_id: str
    crop_name: str
    season: str
    msp_inr_per_q: float | None
    benchmark_yield_q_ha: float
    benchmark_cost_inr_ha: float
    indicative_gross_revenue_inr_ha: float | None
    indicative_gross_margin_inr_ha: float | None
    msp_procurement_assured: bool
    notes: str


@dataclass(frozen=True)
class RotationEconomics:
    """Aggregated indicative economics for a candidate rotation sequence."""

    crop_economics: tuple[CropEconomics, ...]
    total_cost_inr_ha: float
    total_revenue_inr_ha: float | None
    total_margin_inr_ha: float | None
    water_productivity_inr_per_m3: float | None
    disclaimers: tuple[str, ...] = ECONOMIC_DISCLAIMERS


def compute_crop_economics(crop: Mapping[str, object], season: str) -> CropEconomics:
    """Compute indicative economics for a single crop."""
    econ = crop.get("indicative_economics", {})
    crop_id = str(crop.get("id", ""))
    crop_name = str(crop.get("name", crop_id))

    msp = econ.get("msp_inr_per_q")
    if msp is None:
        msp = econ.get("indicative_farmgate_price_inr_q")
    msp_val = float(msp) if msp is not None else None

    yield_val = float(econ.get("benchmark_yield_q_ha", 0.0))
    cost_val = float(econ.get("benchmark_cost_inr_ha", 0.0))

    rev_val = msp_val * yield_val if msp_val is not None else None
    margin_val = rev_val - cost_val if rev_val is not None else None

    return CropEconomics(
        crop_id=crop_id,
        crop_name=crop_name,
        season=season,
        msp_inr_per_q=msp_val,
        benchmark_yield_q_ha=yield_val,
        benchmark_cost_inr_ha=cost_val,
        indicative_gross_revenue_inr_ha=rev_val,
        indicative_gross_margin_inr_ha=margin_val,
        msp_procurement_assured=bool(econ.get("msp_procurement_assured", False)),
        notes=str(econ.get("notes", "")),
    )


def compute_rotation_economics(
    crops: Sequence[Mapping[str, object]],
    seasons: Sequence[str],
    net_irrigation_mm: float | None = None,
) -> RotationEconomics:
    """Compute indicative economics for a sequence of crops in a rotation."""
    items: list[CropEconomics] = []
    total_cost = 0.0
    total_rev: float | None = 0.0
    total_margin: float | None = 0.0

    for crop, season in zip(crops, seasons):
        ce = compute_crop_economics(crop, season)
        items.append(ce)
        total_cost += ce.benchmark_cost_inr_ha
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
    cost_diff_inr_ha: float
    margin_diff_inr_ha: float | None
    headline_summary: str


def compare_vs_rice_wheat_baseline(
    candidate_crops: Sequence[Mapping[str, object]],
    candidate_seasons: Sequence[str],
    candidate_irrigation_mm: float,
    baseline_irrigation_mm: float = 1750.0,
    baseline_cost_ha: float = 90000.0,
    baseline_margin_ha: float = 123250.0,
) -> WaterSavingsComparison:
    """Compare candidate rotation against the continuous Rice–Wheat benchmark.

    Typical central Punjab Rice–Wheat baseline:
    - Rice net irrigation (FAO-56): ~1450 mm; Wheat: ~300 mm -> Total ~1750 mm.
    - Rice cost (PAU): ~Rs 50,000; Wheat: ~Rs 40,000 -> Total Rs 90,000.
    - Rice revenue (65q @ Rs 2300): Rs 149,500; Wheat (50q @ Rs 2275): Rs 113,750 -> Total Rs 263,250.
    - Baseline gross margin: Rs 173,250 - Rs 50,000 - Rs 40,000 = ~Rs 123,250/ha.
    """
    cand_econ = compute_rotation_economics(candidate_crops, candidate_seasons, candidate_irrigation_mm)
    saved_mm = max(0.0, baseline_irrigation_mm - candidate_irrigation_mm)
    saved_pct = (saved_mm / baseline_irrigation_mm * 100.0) if baseline_irrigation_mm > 0 else 0.0
    saved_m3 = saved_mm * 10.0
    saved_litres = saved_m3 * 1000.0

    cost_diff = cand_econ.total_cost_inr_ha - baseline_cost_ha
    margin_diff = (cand_econ.total_margin_inr_ha - baseline_margin_ha) if cand_econ.total_margin_inr_ha is not None else None

    cand_names = " → ".join(str(c.get("name", c.get("id", ""))) for c in candidate_crops)
    headline = (
        f"Conserves {saved_mm:.0f} mm of net irrigation ({saved_pct:.1f}% reduction) "
        f"— equivalent to {saved_m3:,.0f} m³ ({saved_litres:,.0f} litres) of groundwater saved per hectare per year."
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
