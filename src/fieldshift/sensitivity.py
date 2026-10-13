"""Weight sensitivity and recommendation explainability analysis.

Evaluates how stable rotation rankings are when farmer priority weights
are varied by ±20%, and produces plain-language explanations for each
recommended rotation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .rotation_engine import METRICS, RotationPlan


@dataclass(frozen=True)
class WeightPerturbationResult:
    """Outcome of a single priority weight perturbation."""

    perturbed_weights: Mapping[str, float]
    top_plan_crop_names: tuple[str, ...]
    top_plan_score: float | None
    is_same_top_as_baseline: bool


@dataclass(frozen=True)
class RankStabilityReport:
    """Summary of ranking robustness under priority weight sensitivity sweep."""

    baseline_top_plan: tuple[str, ...]
    stability_percentage: float
    total_perturbations_tested: int
    is_highly_stable: bool
    summary_message: str
    perturbations: tuple[WeightPerturbationResult, ...]


def evaluate_rank_stability(
    plans: Sequence[RotationPlan],
    baseline_weights: Mapping[str, float],
    delta_fraction: float = 0.20,
) -> RankStabilityReport | None:
    """Evaluate whether the #1 ranked rotation changes under ±20% weight shifts.

    Parameters
    ----------
    plans : List of RotationPlan objects (typically the feasible/evaluated plans)
    baseline_weights : Active farmer priority weights
    delta_fraction : Fractional perturbation magnitude (default: 0.20 for ±20%)

    Returns
    -------
    RankStabilityReport detailing stability percentage and sensitivities.
    """
    valid_plans = [p for p in plans if p.status != "infeasible" and p.composite_score is not None]
    if not valid_plans:
        return None

    # Sort plans under baseline weights
    sorted_baseline = sorted(valid_plans, key=lambda p: p.composite_score or 0.0, reverse=True)
    baseline_top = sorted_baseline[0].crop_names

    active_metrics = [m for m in METRICS if baseline_weights.get(m, 0.0) > 0]
    if not active_metrics:
        return RankStabilityReport(
            baseline_top_plan=baseline_top,
            stability_percentage=100.0,
            total_perturbations_tested=1,
            is_highly_stable=True,
            summary_message="Top recommendation is 100% stable (single uniform weighting).",
            perturbations=(),
        )

    perturbation_records: list[WeightPerturbationResult] = []
    same_top_count = 0

    # Test single-metric shifts (+20% and -20%) and pairwise shifts
    test_cases: list[dict[str, float]] = []

    # 1. Single metric +delta and -delta
    for metric in active_metrics:
        for factor in (1.0 + delta_fraction, max(0.01, 1.0 - delta_fraction)):
            w = dict(baseline_weights)
            w[metric] = w[metric] * factor
            test_cases.append(w)

    # 2. Pairwise opposing shifts (e.g. water +20% and soil -20%)
    if len(active_metrics) >= 2:
        for i, m1 in enumerate(active_metrics):
            for m2 in active_metrics[i + 1:]:
                w = dict(baseline_weights)
                w[m1] = w[m1] * (1.0 + delta_fraction)
                w[m2] = w[m2] * max(0.01, 1.0 - delta_fraction)
                test_cases.append(w)
                w_rev = dict(baseline_weights)
                w_rev[m1] = w_rev[m1] * max(0.01, 1.0 - delta_fraction)
                w_rev[m2] = w_rev[m2] * (1.0 + delta_fraction)
                test_cases.append(w_rev)

    for weights in test_cases:
        # Re-score each plan with perturbed weights
        scored_plans: list[tuple[RotationPlan, float]] = []
        for plan in valid_plans:
            available = {
                name: m for name, m in plan.metrics.items()
                if m.score is not None and weights.get(name, 0.0) > 0
            }
            tot_w = sum(weights.get(name, 0.0) for name in available)
            if tot_w > 0:
                eff_w = {name: weights[name] / tot_w for name in available}
                score = sum(available[name].score * eff_w[name] for name in available)
            else:
                score = 0.0
            scored_plans.append((plan, score))

        scored_plans.sort(key=lambda x: x[1], reverse=True)
        top_perturbed = scored_plans[0][0].crop_names
        is_same = (top_perturbed == baseline_top)
        if is_same:
            same_top_count += 1

        perturbation_records.append(
            WeightPerturbationResult(
                perturbed_weights=weights,
                top_plan_crop_names=top_perturbed,
                top_plan_score=scored_plans[0][1],
                is_same_top_as_baseline=is_same,
            )
        )

    total_tests = len(perturbation_records)
    stability_pct = (same_top_count / total_tests * 100.0) if total_tests > 0 else 100.0
    is_stable = stability_pct >= 80.0

    if stability_pct == 100.0:
        msg = f"Top recommendation is 100% stable across all {total_tests} tested priority weight perturbations (±{delta_fraction*100:.0f}%)."
    elif stability_pct >= 80.0:
        msg = (
            f"Top recommendation is robust: remains #1 in {same_top_count} of {total_tests} "
            f"({stability_pct:.0f}%) priority perturbations."
        )
    else:
        msg = (
            f"Recommendation is sensitive to priorities: top choice changes in "
            f"{total_tests - same_top_count} of {total_tests} weight shifts."
        )

    return RankStabilityReport(
        baseline_top_plan=baseline_top,
        stability_percentage=stability_pct,
        total_perturbations_tested=total_tests,
        is_highly_stable=is_stable,
        summary_message=msg,
        perturbations=tuple(perturbation_records),
    )


def generate_plain_language_explanation(plan: RotationPlan) -> str:
    """Generate a crisp, plain-language farmer explanation for why this rotation was recommended."""
    reasons: list[str] = []

    # Water saving reason
    wb = plan.water_balance
    if wb is not None and getattr(wb, "total_net_irrigation_mm", None) is not None:
        nir = wb.total_net_irrigation_mm
        if nir < 800:
            reasons.append(f"saves substantial water (only ~{nir:.0f} mm estimated net irrigation)")
        elif nir < 1200:
            reasons.append(f"maintains moderate water demand (~{nir:.0f} mm net irrigation)")

    # Legume nitrogen reason
    has_legume = any(getattr(c, "legume", False) for c in getattr(plan, "crops", ()))
    legume_names = [name for name, c in zip(plan.crop_names, plan.crop_ids) if c in ("moong", "soybean", "chickpea")]
    if legume_names:
        reasons.append(f"adds a biological nitrogen-fixing break ({', '.join(legume_names)})")

    # Family diversity reason
    if plan.metrics.get("rotation_diversity") and plan.metrics["rotation_diversity"].score is not None:
        div_score = plan.metrics["rotation_diversity"].score
        if div_score >= 0.8:
            reasons.append("maximizes crop family diversification")

    # Thermal suitability
    ca = plan.climate_assessment
    if ca is not None and getattr(ca, "climate_suitability_score", None) is not None:
        if ca.climate_suitability_score >= 0.85:
            reasons.append("fits regional temperature windows with high thermal suitability")

    names = " → ".join(plan.crop_names)
    if reasons:
        return f"**Why recommended:** {names} was selected because it {'; and '.join(reasons)}."
    return f"**Why recommended:** {names} satisfies all documented agronomic compatibility checks."
