"""Assess a farmer's stated current sequence alongside generated alternatives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .rotation_engine import FarmProfile, RotationEngine, RotationPlan


@dataclass(frozen=True)
class Strategy:
    label: str
    plan: RotationPlan
    is_current: bool = False
    why_suggested: str = ""
    evidence_support: tuple[str, ...] = ()
    benefits_offered: tuple[str, ...] = ()
    information_gaps: tuple[str, ...] = ()
    risks_and_expert_review: tuple[str, ...] = ()
    bare_field_analysis: str = ""
    vulnerability_analysis: str = ""
    pest_break_analysis: str = ""
    soil_functional_roles: tuple[str, ...] = ()


def _build_strategy_narratives(
    label: str,
    plan: RotationPlan,
    is_current: bool,
    engine: RotationEngine,
    profile: FarmProfile,
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str, str, str, tuple[str, ...]]:
    crop_ids = plan.crop_ids
    crop_names = plan.crop_names
    names_str = " → ".join(crop_names)

    # 1. Why suggested
    if is_current:
        why = (
            f"**Baseline Assessment:** Evaluates the farm's current practice ({names_str}) to establish "
            f"a rigorous agronomic benchmark for water consumption, soil nutrient balances, and climate vulnerability."
        )
    else:
        reasons = []
        wb = plan.water_balance
        if wb is not None and getattr(wb, "total_net_irrigation_mm", None) is not None:
            reasons.append(f"conserves water (~{wb.total_net_irrigation_mm:.0f} mm estimated net irrigation)")
        has_legume = any(getattr(c, "legume", False) for c in getattr(plan, "crops", ())) or any(cid in ("moong", "chickpea", "soybean", "pigeonpea") for cid in crop_ids)
        if has_legume:
            reasons.append("integrates a biological nitrogen-fixing break")
        div_score = plan.metrics.get("rotation_diversity")
        if div_score and div_score.score is not None and div_score.score >= 0.7:
            reasons.append("diversifies botanical plant families")
        why = f"**Why Suggested:** {names_str} was recommended because it {"; and ".join(reasons)} while satisfying regional agronomic compatibility rules." if reasons else f"**Why Suggested:** {names_str} provides a viable, agronomically documented alternative sequence."

    # 2. Evidence support
    evidence = [
        "Regional Agricultural University Packages of Practices (PAU/USDA/IFAPA/ICRISAT) crop transition guidelines.",
        "NASA POWER Daily Surface Meteorology: solar radiation, temperature, and humidity driving FAO-56 Penman-Monteith ET₀ calculations.",
        "FAO EcoCrop cardinal thermal limits (Tmin, Topt, Tmax) evaluated against local historical daily temperature records.",
        "Government procurement benchmarks (CACP MSP 2024-25 / Agricultural Statistics) for indicative economic viability.",
    ]

    # 3. Benefits offered
    benefits = []
    wb = plan.water_balance
    if wb is not None and getattr(wb, "total_net_irrigation_mm", None) is not None:
        benefits.append(f"Water Conservation: Requires estimated {wb.total_net_irrigation_mm:.0f} mm net irrigation, reducing groundwater extraction pressure.")
    if any(cid in ("moong", "chickpea", "soybean", "pigeonpea") for cid in crop_ids):
        benefits.append("Biological Nitrogen Fixation: Legume incorporation fixes 30–50 kg atmospheric N/ha and improves soil organic carbon.")
    if len(set(engine.crops.get(c, {}).get("family", c) for c in crop_ids)) >= 2:
        benefits.append("Pest/Disease Interruption: Alternating botanical families breaks continuous host cycles for cereal stem borers and root pathogens.")
    benefits.append("Income & Market Diversification: Spreads revenue risk across multiple distinct harvest windows rather than a single commodity.")

    # 4. Information gaps
    gaps = (
        "Satellite meteorology (~0.5° NASA POWER) represents regional grid conditions, not microclimatic field station measurements.",
        "Soil nutrient dynamics use published stoichiometric approximations and have not been calibrated with long-term field plot trials.",
        "Local mandi commodity price volatility, storage access, and private trader quality deductions are not dynamically modeled.",
    )

    # 5. Risks and expert review needed
    risks = (
        "Verify certified short-duration seed varieties (e.g. university-recommended cultivars) with local agricultural extension advisers.",
        "Ensure field drainage is adequate before sowing: rainfed or furrow-irrigated crops may be sensitive to temporary waterlogging.",
        "Assess farm labor and equipment availability during tight multi-crop harvesting and field preparation turnaround windows.",
    )

    # 6. Bare field analysis
    has_summer_crop = any(cid in ("moong", "summer_moong", "dhaincha", "sunnhemp") for cid in crop_ids) or "summer" in [s.lower() for s in getattr(plan, "seasons", ())]
    if has_summer_crop:
        bare_field = (
            "🛡️ **Soil Protected:** Summer window (April–June) is actively cultivated, "
            "protecting topsoil from extreme wind erosion, lowering canopy soil temperatures by 4–8°C, and building soil organic matter."
        )
    else:
        bare_field = (
            "⚠️ **Bare-Field Window Detected:** Leaves fields uncropped during the peak solar radiation window (April–June), "
            "exposing bare soil to wind erosion, organic matter depletion, and excessive evaporative moisture loss."
        )

    # 7. Vulnerability analysis
    vulnerabilities = []
    if "wheat" in crop_ids:
        vulnerabilities.append("Late-Rabi terminal heat exposure: March temperatures exceeding 32°C during anthesis/grain filling cause grain shriveling.")
    if "maize" in crop_ids or "cotton" in crop_ids:
        vulnerabilities.append("Kharif seedling monsoon vulnerability: Young seedlings are sensitive to standing water ponding during intense rainfall storms.")
    vulnerability = " · ".join(vulnerabilities) if vulnerabilities else "Moderate seasonal weather exposure within typical regional agronomic tolerance limits."

    # 8. Pest break analysis
    families = [engine.crops.get(c, {}).get("family", "Unknown") for c in crop_ids]
    if len(set(families)) == 1 and families[0] in ("Poaceae", "Grass"):
        pest_break = "⚠️ **Continuous Grass Monoculture:** All crops belong to Poaceae, allowing cereal stem borers and root-knot nematodes to persist across seasons."
    else:
        pest_break = f"✅ **Botanical Break:** Rotates {', '.join(set(families))}, disrupting insect pest reproduction cycles and fungal disease accumulation."

    # 9. Soil functional roles
    roles = []
    for cid in crop_ids:
        c_info = engine.crops.get(cid, {})
        c_name = c_info.get("name", cid.capitalize())
        if c_info.get("legume", False) or cid in ("moong", "chickpea", "soybean", "pigeonpea"):
            roles.append(f"🌿 **Nitrogen-Fixer ({c_name}):** Symbiotic rhizobia fix atmospheric N2, adding organic N to the soil profile.")
        if cid in ("cotton", "mustard", "rapeseed_mustard", "sorghum"):
            roles.append(f"🌱 **Deep-Rooter ({c_name}):** Taproots penetrate subsoil hardpans (up to 1.5–2m), opening macropores that improve water infiltration.")
        if cid in ("pearl_millet", "sorghum"):
            roles.append(f"☀️ **Drought-Tolerant ({c_name}):** C4 photosynthetic metabolism achieves superior water-use efficiency during moisture deficits.")
        if cid in ("cereal_rye", "dhaincha", "sunnhemp", "moong"):
            roles.append(f"🌾 **Soil Armor & Cover ({c_name}):** Provides rapid vegetative ground cover that shields soil aggregates from erosion.")

    return (why, tuple(evidence), tuple(benefits), gaps, risks, bare_field, vulnerability, pest_break, tuple(roles))


def compare_existing_rotation(
    engine: RotationEngine,
    profile: FarmProfile,
    current_crop_ids: tuple[str, ...],
    alternatives: Sequence[RotationPlan],
) -> tuple[Strategy, ...]:
    """Keep the current sequence even when it fails rules or is dominated.

    All scores use the same farm, historical climate, horizon and weights. An
    unsupported transition is a prototype evidence gap, not proof a farmer's
    existing practice is impossible. Do not replace an unknown or fallow crop
    with a guessed catalogue crop.
    """
    current = engine.assess_sequence(current_crop_ids, profile)
    cur_narratives = _build_strategy_narratives("Your current rotation", current, True, engine, profile)
    strategies = [
        Strategy(
            label="Your current rotation",
            plan=current,
            is_current=True,
            why_suggested=cur_narratives[0],
            evidence_support=cur_narratives[1],
            benefits_offered=cur_narratives[2],
            information_gaps=cur_narratives[3],
            risks_and_expert_review=cur_narratives[4],
            bare_field_analysis=cur_narratives[5],
            vulnerability_analysis=cur_narratives[6],
            pest_break_analysis=cur_narratives[7],
            soil_functional_roles=cur_narratives[8],
        )
    ]
    seen = {current_crop_ids}
    for candidate in alternatives:
        if candidate.crop_ids in seen:
            continue
        seen.add(candidate.crop_ids)
        assessed = engine.assess_sequence(candidate.crop_ids, profile)
        alt_label = f"Alternative {len(strategies)}"
        alt_narratives = _build_strategy_narratives(alt_label, assessed, False, engine, profile)
        strategies.append(
            Strategy(
                label=alt_label,
                plan=assessed,
                is_current=False,
                why_suggested=alt_narratives[0],
                evidence_support=alt_narratives[1],
                benefits_offered=alt_narratives[2],
                information_gaps=alt_narratives[3],
                risks_and_expert_review=alt_narratives[4],
                bare_field_analysis=alt_narratives[5],
                vulnerability_analysis=alt_narratives[6],
                pest_break_analysis=alt_narratives[7],
                soil_functional_roles=alt_narratives[8],
            )
        )
    return tuple(strategies)
