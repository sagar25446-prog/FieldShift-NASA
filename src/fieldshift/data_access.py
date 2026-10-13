"""Contracts for data-source readiness states.

The NASA POWER client is implemented separately in ``nasa_power.py`` so source
availability is never confused with a fabricated observation.
"""

from dataclasses import dataclass


class DataSourceNotConfiguredError(RuntimeError):
    """Raised when a feature requires a verified source that is not configured."""


@dataclass(frozen=True)
class SourceStatus:
    """Availability and plain-language explanation for one data category."""

    name: str
    available: bool
    message: str


def source_statuses() -> tuple[SourceStatus, ...]:
    """Return honest source availability; this is not data retrieval."""
    return (
        SourceStatus("NASA POWER daily climate data", True, "Ready for an on-demand historical point request. It is gridded climate context, not a farm measurement."),
        SourceStatus("Soil information", True, "Farmer or laboratory values, plus an optional ISRIC SoilGrids 250 m estimate (beta service; may be unavailable). Estimates never replace a soil test."),
        SourceStatus("Crop and rotation reference data", True, "Source-linked Punjab crop catalogue is available; agronomic rules are not implemented."),
    )


def fetch_earth_observations(*_: object, **__: object) -> None:
    """Prevent accidental use of made-up Earth-observation data."""
    raise DataSourceNotConfiguredError(
        "NASA Earth observations are not configured. Connect and validate a documented source before requesting data."
    )
