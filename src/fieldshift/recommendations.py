"""Future home for transparent rotation-comparison logic."""


class RecommendationNotReadyError(RuntimeError):
    """Raised before verified inputs and documented rules are available."""


def compare_rotations(*_: object, **__: object) -> None:
    """Guard against a recommendation before supporting logic exists."""
    raise RecommendationNotReadyError(
        "Rotation comparison is unavailable until verified data and agronomic rules are implemented."
    )
