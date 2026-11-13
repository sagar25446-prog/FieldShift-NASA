"""Compare a farmer-entered sequence with engine-generated alternatives.

This module is a presentation layer over ``rotation_engine``. It does not add
new agronomic thresholds, pest predictions, or soil-change claims. Each message
is either an engine result or an explicit statement of what cannot be known.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .rotation_engine import FarmProfile, RotationEngine, RotationPlan


@dataclass(frozen=True)
class Strategy:
    """One comparable sequence plus source-linked, plain-language context."""

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


def _check_messages(plan: RotationPlan, status: str) -> tuple[str, ...]:
    """Return unique engine check messages in their original order."""
    return tuple(dict.fromkeys(check.message for check in plan.checks if check.status == status))


def _soil_roles(plan: RotationPlan, engine: RotationEngine) -> tuple[str, ...]:
    """Describe catalogue roles without estimating nitrogen or soil change."""
    roles: list[str] = []
    for crop_id in plan.crop_ids:
        crop = engine.crops[crop_id]
        nutrient = crop.get("nutrient_characteristics", {})
        notes = str(nutrient.get("notes", "")).strip()
        if crop.get("legume"):
            role = f"{crop['name']} is catalogued as a legume."
            if nutrient.get("status") != "unknown" and notes:
                role = f"{role} Catalogue note: {notes}"
            else:
                role = f"{role} Field nitrogen contribution is not estimated by FieldShift."
            roles.append(role)
        elif nutrient.get("status") != "unknown" and notes:
            roles.append(f"{crop['name']}: {notes}")
    return tuple(dict.fromkeys(roles))


def _land_use_statement(plan: RotationPlan) -> str:
    comparison = plan.land_use_comparison
    if comparison is None:
        return (
            "No MODIS phenology comparison is attached to this assessment. "
            "FieldShift cannot establish whether a planned slot is currently bare or covered."
        )
    if comparison.added_seasons:
        slots = ", ".join(comparison.added_seasons)
        return (
            f"The plan adds cropping in the following slot(s) relative to the attached MODIS record: {slots}. "
            "This is a planning difference, not proof of ground cover, erosion reduction, or soil improvement."
        )
    if comparison.continued_seasons:
        return (
            "The attached MODIS record indicates recent seasonal greenness in each planned slot. "
            "It does not identify the crop or measure field-scale ground cover."
        )
    return "The attached MODIS comparison is inconclusive for one or more planned slots."


def _climate_statement(plan: RotationPlan) -> str:
    assessment = plan.climate_assessment
    if assessment is None:
        return (
            "No crop-temperature assessment was available for this sequence. "
            "Historical climate suitability therefore remains unknown."
        )
    if getattr(assessment, "status", "unknown") == "unknown":
        return (
            "The climate record or catalogue thresholds were insufficient for a complete historical thermal assessment. "
            "This is not a weather forecast."
        )
    return (
        "Historical temperature suitability was calculated from the attached climate record and documented catalogue limits. "
        "It is a historical comparison, not a yield prediction or future-weather forecast."
    )


def _pest_statement(plan: RotationPlan, engine: RotationEngine) -> str:
    families = tuple(dict.fromkeys(engine.crops[crop_id]["family"] for crop_id in plan.crop_ids))
    fails = tuple(check for check in plan.checks if check.status == "fail")
    if any("restriction" in check.rule or "relationship" in check.rule for check in fails):
        return "A documented crop/family restriction or rotation relationship fails. The sequence is not presented as feasible."
    return (
        f"The sequence contains {len(families)} documented crop family/families ({', '.join(families)}). "
        "This diversity summary is not a prediction of pest or disease control."
    )


def _build_strategy_narratives(
    plan: RotationPlan,
    is_current: bool,
    engine: RotationEngine,
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...], str, str, str, tuple[str, ...]]:
    """Make a transparent explanation from a completed plan assessment."""
    sequence = " → ".join(plan.crop_names)
    if is_current:
        why = (
            f"**Current rotation assessment:** {sequence} is retained as the farmer-entered baseline and assessed "
            "with the same inputs, rules, and weights as every alternative."
        )
    else:
        why = (
            f"**Engine-generated alternative:** {sequence} was returned by the documented relationship search for the "
            "selected planning slots. It is not a prescription or a guarantee of performance."
        )

    evidence = tuple(plan.source_urls) or (
        "No catalogue source URL was attached to this assessment; review the individual rule checks.",
    )
    benefits = plan.positive_factors or (
        "No additional positive factor could be calculated from the available inputs.",
    )
    gaps = tuple(dict.fromkeys((*plan.uncertainty_warnings, *_check_messages(plan, "unknown")))) or (
        "No additional missing-input warning was generated. This does not replace local validation.",
    )
    risks = tuple(dict.fromkeys((*plan.tradeoffs, *_check_messages(plan, "fail")))) or (
        "Review crop calendar, soil condition, irrigation capacity, equipment, and market access locally before acting.",
    )
    return (
        why,
        evidence,
        benefits,
        gaps,
        risks,
        _land_use_statement(plan),
        _climate_statement(plan),
        _pest_statement(plan, engine),
        _soil_roles(plan, engine),
    )


def _strategy(label: str, plan: RotationPlan, is_current: bool, engine: RotationEngine) -> Strategy:
    values = _build_strategy_narratives(plan, is_current, engine)
    return Strategy(
        label=label,
        plan=plan,
        is_current=is_current,
        why_suggested=values[0],
        evidence_support=values[1],
        benefits_offered=values[2],
        information_gaps=values[3],
        risks_and_expert_review=values[4],
        bare_field_analysis=values[5],
        vulnerability_analysis=values[6],
        pest_break_analysis=values[7],
        soil_functional_roles=values[8],
    )


def compare_existing_rotation(
    engine: RotationEngine,
    profile: FarmProfile,
    current_crop_ids: tuple[str, ...],
    alternatives: Sequence[RotationPlan],
) -> tuple[Strategy, ...]:
    """Keep the current sequence even when it fails known rules or is dominated.

    An unsupported transition is a prototype evidence gap, not proof that a
    farmer's current practice is impossible in the field.
    """
    current = engine.assess_sequence(current_crop_ids, profile)
    strategies = [_strategy("Your current rotation", current, True, engine)]
    seen = {current_crop_ids}
    for candidate in alternatives:
        if candidate.crop_ids in seen:
            continue
        seen.add(candidate.crop_ids)
        assessed = engine.assess_sequence(candidate.crop_ids, profile)
        strategies.append(_strategy(f"Alternative {len(strategies)}", assessed, False, engine))
    return tuple(strategies)
