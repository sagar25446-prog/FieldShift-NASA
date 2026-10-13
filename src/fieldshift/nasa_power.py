"""NASA POWER Daily API client with explicit provenance and error handling.

NASA POWER is gridded climate context. It is not a field instrument, soil test,
crop-yield measurement, or forecast service.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
import json
from pathlib import Path
from time import monotonic
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd


POWER_DAILY_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_DOCUMENTATION_URL = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"
DEFAULT_PARAMETERS = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "ALLSKY_SFC_SW_DWN",
)
FAO56_METEOROLOGICAL_PARAMETERS = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "ALLSKY_SFC_SW_DWN",
    "RH2M",
    "WS2M",
)


class PowerError(RuntimeError):
    """Base error for a NASA POWER request that cannot produce trustworthy data."""


class PowerValidationError(PowerError):
    """Raised before an invalid request is sent."""


class PowerNetworkError(PowerError):
    """Raised for timeouts, connection errors, and HTTP errors."""


class PowerAPIError(PowerError):
    """Raised when POWER returns an API-level error or warning-only response."""


class PowerResponseError(PowerError):
    """Raised when a successful response does not match the documented schema."""


@dataclass(frozen=True)
class PowerRequest:
    """A validated daily point request. Dates are inclusive ISO dates."""

    latitude: float
    longitude: float
    start_date: date
    end_date: date
    parameters: tuple[str, ...] = DEFAULT_PARAMETERS
    time_standard: str = "UTC"

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise PowerValidationError("Latitude must be between -90 and 90 degrees.")
        if not -180 <= self.longitude <= 180:
            raise PowerValidationError("Longitude must be between -180 and 180 degrees.")
        if self.start_date > self.end_date:
            raise PowerValidationError("The start date must be on or before the end date.")
        if self.start_date < date(1981, 1, 1):
            raise PowerValidationError("NASA POWER daily data is available from 1981-01-01.")
        if not self.parameters:
            raise PowerValidationError("Select at least one NASA POWER parameter.")
        if self.time_standard not in {"UTC", "LST"}:
            raise PowerValidationError("Time standard must be UTC or LST.")


@dataclass(frozen=True)
class ParameterMetadata:
    """Metadata returned by NASA POWER for an individual parameter."""

    name: str
    long_name: str
    unit: str


@dataclass(frozen=True)
class PowerProvenance:
    """Enough context to explain where a retrieved climate series came from."""

    source_name: str
    source_url: str
    documentation_url: str
    retrieved_at_utc: str
    api_version: str | None
    source_datasets: tuple[str, ...]
    latitude_requested: float
    longitude_requested: float
    latitude_returned: float | None
    longitude_returned: float | None
    elevation_returned_m: float | None
    start_date: str
    end_date: str
    time_standard: str
    temporal_resolution: str
    spatial_applicability: str
    fill_value: float | None
    parameter_metadata: Mapping[str, ParameterMetadata]
    missing_observation_counts: Mapping[str, int]
    api_messages: tuple[str, ...]


@dataclass(frozen=True)
class PowerDataset:
    """Daily values plus the provenance needed to interpret them."""

    data: pd.DataFrame
    provenance: PowerProvenance

    def copy(self) -> "PowerDataset":
        """Prevent callers from mutating a cached DataFrame."""
        return PowerDataset(data=self.data.copy(deep=True), provenance=self.provenance)


Transport = Callable[[str, float], bytes]


def _default_transport(url: str, timeout_seconds: float) -> bytes:
    """Fetch an API response without an API key or third-party HTTP dependency."""
    try:
        with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS endpoint
            return response.read()
    except HTTPError as error:
        raise PowerNetworkError(f"NASA POWER returned HTTP {error.code}. Retry shortly or adjust the request.") from error
    except URLError as error:
        raise PowerNetworkError("Could not reach NASA POWER. Check the network and retry.") from error
    except TimeoutError as error:
        raise PowerNetworkError("NASA POWER timed out. Retry the same request shortly.") from error


class PowerClient:
    """Fetch and cache NASA POWER daily point data for the active process.

    Caching is in-memory and time-limited. Use ``force_refresh=True`` when a user
    explicitly requests a new copy; no credentials are required by this API path.
    """

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        cache_ttl_seconds: float = 21_600.0,
        transport: Transport = _default_transport,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self._transport = transport
        self._cache: dict[PowerRequest, tuple[float, PowerDataset]] = {}

    def build_url(self, request: PowerRequest) -> str:
        """Return the exact public API URL recorded in provenance."""
        query = urlencode(
            {
                "parameters": ",".join(request.parameters),
                "community": "AG",
                "longitude": request.longitude,
                "latitude": request.latitude,
                "start": request.start_date.strftime("%Y%m%d"),
                "end": request.end_date.strftime("%Y%m%d"),
                "format": "JSON",
                "time-standard": request.time_standard,
            }
        )
        return f"{POWER_DAILY_ENDPOINT}?{query}"

    def fetch_daily(self, request: PowerRequest, force_refresh: bool = False) -> PowerDataset:
        """Retrieve, validate, parse and cache a daily point response."""
        cached = self._cache.get(request)
        if not force_refresh and cached and monotonic() - cached[0] < self.cache_ttl_seconds:
            return cached[1].copy()

        url = self.build_url(request)
        try:
            payload = json.loads(self._transport(url, self.timeout_seconds).decode("utf-8"))
        except HTTPError as error:
            raise PowerNetworkError(f"NASA POWER returned HTTP {error.code}. Retry shortly or adjust the request.") from error
        except URLError as error:
            raise PowerNetworkError("Could not reach NASA POWER. Check the network and retry.") from error
        except TimeoutError as error:
            raise PowerNetworkError("NASA POWER timed out. Retry the same request shortly.") from error
        except UnicodeDecodeError as error:
            raise PowerResponseError("NASA POWER returned a response that is not UTF-8 JSON.") from error
        except json.JSONDecodeError as error:
            raise PowerResponseError("NASA POWER returned malformed JSON. Retry the request shortly.") from error

        dataset = parse_power_daily_response(payload, request, url)
        self._cache[request] = (monotonic(), dataset)
        return dataset.copy()


def parse_power_daily_response(payload: object, request: PowerRequest, source_url: str) -> PowerDataset:
    """Parse the documented POWER Daily JSON response without inventing values."""
    if not isinstance(payload, dict):
        raise PowerResponseError("NASA POWER response must be a JSON object.")
    messages = tuple(str(message) for message in payload.get("messages", []) if message)
    if payload.get("errors"):
        raise PowerAPIError(f"NASA POWER rejected the request: {payload['errors']}")

    try:
        properties = payload["properties"]
        parameter_values = properties["parameter"]
        parameter_details = payload["parameters"]
        header = payload["header"]
    except (KeyError, TypeError) as error:
        raise PowerResponseError("NASA POWER response is missing properties, parameters, or header metadata.") from error
    if not isinstance(parameter_values, dict) or not isinstance(parameter_details, dict) or not isinstance(header, dict):
        raise PowerResponseError("NASA POWER response metadata has an unexpected format.")

    missing_parameters = set(request.parameters) - set(parameter_values)
    if missing_parameters:
        detail = "; ".join(messages) if messages else "No API explanation was returned."
        raise PowerAPIError(f"NASA POWER omitted requested parameter(s) {sorted(missing_parameters)}. {detail}")

    series_by_parameter: dict[str, pd.Series] = {}
    metadata: dict[str, ParameterMetadata] = {}
    fill_value = header.get("fill_value")
    for parameter in request.parameters:
        values = parameter_values[parameter]
        details = parameter_details.get(parameter, {})
        if not isinstance(values, dict) or not isinstance(details, dict):
            raise PowerResponseError(f"NASA POWER parameter {parameter} has an unexpected format.")
        if not details.get("units") or not details.get("longname"):
            raise PowerResponseError(f"NASA POWER metadata for {parameter} is incomplete.")
        try:
            index = pd.to_datetime(list(values), format="%Y%m%d", errors="raise")
            series = pd.Series(list(values.values()), index=index, name=parameter, dtype="float64")
        except (TypeError, ValueError) as error:
            raise PowerResponseError(f"NASA POWER values for {parameter} are not daily numeric values.") from error
        if fill_value is not None:
            series = series.mask(series == float(fill_value))
        series_by_parameter[parameter] = series
        metadata[parameter] = ParameterMetadata(parameter, str(details["longname"]), str(details["units"]))

    frame = pd.concat(series_by_parameter.values(), axis=1).sort_index()
    expected_dates = pd.date_range(request.start_date, request.end_date, freq="D")
    frame = frame.reindex(expected_dates)
    frame.index.name = "date"
    if frame.empty:
        raise PowerAPIError("NASA POWER returned no daily observations for the selected request.")

    returned_latitude = returned_longitude = returned_elevation = None
    geometry = payload.get("geometry")
    if isinstance(geometry, dict) and isinstance(geometry.get("coordinates"), list):
        coordinates = geometry["coordinates"]
        if len(coordinates) >= 2:
            returned_longitude, returned_latitude = float(coordinates[0]), float(coordinates[1])
        if len(coordinates) >= 3:
            returned_elevation = float(coordinates[2])
    missing_counts = {name: int(frame[name].isna().sum()) for name in frame.columns}
    provenance = PowerProvenance(
        source_name="NASA POWER Daily API",
        source_url=source_url,
        documentation_url=POWER_DOCUMENTATION_URL,
        retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
        api_version=str(header.get("api", {}).get("version")) if isinstance(header.get("api"), dict) else None,
        source_datasets=tuple(str(item) for item in header.get("sources", [])),
        latitude_requested=request.latitude,
        longitude_requested=request.longitude,
        latitude_returned=returned_latitude,
        longitude_returned=returned_longitude,
        elevation_returned_m=returned_elevation,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        time_standard=str(header.get("time_standard", request.time_standard)),
        temporal_resolution="daily",
        spatial_applicability="NASA POWER point query at source-native gridded resolution; not a field measurement.",
        fill_value=float(fill_value) if fill_value is not None else None,
        parameter_metadata=metadata,
        missing_observation_counts=missing_counts,
        api_messages=messages,
    )
    return PowerDataset(data=frame, provenance=provenance)


DEMO_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "demo_snapshot_ludhiana_2024.json"

# The demonstration farm is a MODIS-confirmed cropland pixel in rural Ludhiana
# district (MCD12Q1 IGBP class 12, 2020-2024), about 16 km WSW of the city.
DEMO_LATITUDE = 30.85
DEMO_LONGITUDE = 75.70
DEMO_SNAPSHOT_SOURCE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CT2M_MAX%2CT2M_MIN%2CPRECTOTCORR%2CALLSKY_SFC_SW_DWN%2CRH2M%2CWS2M&community=AG&longitude=75.7&latitude=30.85&start=20240101&end=20241231&format=JSON&time-standard=UTC"
DEMO_SNAPSHOT_RETRIEVED_AT_UTC = "2026-10-13T13:14:00Z"


def load_offline_demo_snapshot(path: Path | str | None = None) -> PowerDataset:
    """Load the saved, unmodified NASA POWER daily response for the demo farm (2024).

    The file is the raw API response for ``DEMO_SNAPSHOT_SOURCE_URL``, saved on
    ``DEMO_SNAPSHOT_RETRIEVED_AT_UTC``. Provenance reports that retrieval time,
    not the time the file was loaded.
    """
    snapshot_file = Path(path) if path is not None else DEMO_SNAPSHOT_PATH
    if not snapshot_file.exists():
        raise FileNotFoundError(f"Offline demonstration snapshot not found at {snapshot_file}")
    payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
    parameters = tuple(payload["properties"]["parameter"].keys())
    req = PowerRequest(
        latitude=DEMO_LATITUDE,
        longitude=DEMO_LONGITUDE,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        parameters=parameters,
    )
    dataset = parse_power_daily_response(payload, req, DEMO_SNAPSHOT_SOURCE_URL)
    return PowerDataset(dataset.data, replace(dataset.provenance, retrieved_at_utc=DEMO_SNAPSHOT_RETRIEVED_AT_UTC))
