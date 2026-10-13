"""Future home for documented, explainable agronomic feasibility rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FeasibilityResult:
    """An explainable result returned by a future agronomic rule."""

    feasible: bool
    explanation: str


def evaluate_rotation(*_: object, **__: object) -> FeasibilityResult:
    """Declare the current limitation instead of inferring agronomic advice."""
    return FeasibilityResult(False, "Rotation feasibility rules have not been validated or configured yet.")
