"""Observed seasonal land use from MODIS Land Cover Dynamics (MCD12Q2).

MCD12Q2 reports, for each 500 m pixel and year, how many vegetation cycles the
MODIS NBAR-EVI2 greenness record shows and when each cycle greens up and goes
dormant (Gray, Sulla-Menashe & Friedl, C6.1 user guide). FieldShift uses it
for one purpose: to tell whether a planned crop season (kharif, rabi, summer)
was *green in recent years* at the farm's pixel, so a plan that adds a
cropping season compared with recent land use is visible, together with the
extra crop water demand that season brings.

Greenness is not yield, crop identity or soil fertility. A 500 m pixel can
mix several fields, and at most two cycles are reported per year.

This adapter is deliberately separate from the NASA POWER client.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from time import monotonic
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .climate_trends import REGIONAL_SEASONS


ORNL_SUBSET_ENDPOINT = "https://modis.ornl.gov/rst/api/v1/MCD12Q2/subset"
ORNL_SERVICE_DOCS_URL = "https://modis.ornl.gov/data/modis_webservice.html"
MCD12Q2_USER_GUIDE_URL = "https://lpdaac.usgs.gov/documents/1417/MCD12Q2_User_Guide_V61.pdf"
PRODUCT_LABEL = "MODIS/Terra+Aqua Land Cover Dynamics (MCD12Q2), Collection 6.1, 500 m, yearly"
RESOLUTION = "500 m sinusoidal grid cell (463 m nominal); a point query returns the cell containing the farm location"
FILL_VALUE = 32767
EPOCH = date(1970, 1, 1)
MAX_YEARS_PER_REQUEST = 10  # ORNL limit: 10 dates per subset request

BANDS = ("NumCycles",) + tuple(
    f"{name}.Num_Modes_0{mode}"
    for mode in (1, 2)
    for name in ("Greenup", "MidGreenup", "MidGreendown", "Dormancy", "EVI_Amplitude", "QA_Overall")
)
QA_LABELS = {0: "best", 1: "good", 2: "fair", 3: "poor"}
PLANNING_SEASONS = ("kharif", "rabi", "summer")
MIN_CLEAR_YEARS = 3

DEMO_PHENOLOGY_PATH = Path(__file__).resolve().parents[2] / "data" / "modis_mcd12q2_demo_farm_2016_2025.json"


class PhenologyError(RuntimeError):
    """A MODIS phenology request that cannot produce trustworthy information."""


class PhenologyNetworkError(PhenologyError):
    pass


class PhenologyResponseError(PhenologyError):
    pass


@dataclass(frozen=True)
class VegetationCycle:
    product_year: int
    mode: int
    greenup: date | None
    mid_greenup: date | None
    mid_greendown: date | None
    dormancy: date | None
    evi2_amplitude: float | None
    qa_overall: int | None

    @property
    def centre(self) -> date | None:
        """Midpoint of MidGreenup and MidGreendown, used to place the cycle in a season.

        The ORNL subset service does not offer the Peak layer, and the user
        guide recommends the more stable mid-greenness dates.
        """
        if self.mid_greenup is None or self.mid_greendown is None:
            return None
        return self.mid_greenup + (self.mid_greendown - self.mid_greenup) / 2

    @property
    def quality(self) -> str:
        return QA_LABELS.get(self.qa_overall, "unknown") if self.qa_overall is not None else "unknown"


@dataclass(frozen=True)
class PhenologyRecord:
    latitude: float
    longitude: float
    product: str
    resolution: str
    years: tuple[int, ...]
    num_cycles: Mapping[int, int | None]
    cycles: tuple[VegetationCycle, ...]
    source_urls: tuple[str, ...]
    retrieved_at_utc: str
    processing_dates: tuple[str, ...]
    mode: str = "live"  # "live" or "saved"


@dataclass(frozen=True)
class SeasonYear:
    season_id: str
    label: str
    status: str  # "cycle", "no_cycle", "unclear"
    detail: str


@dataclass(frozen=True)
class SeasonUse:
    season_id: str
    season_name: str
    years: tuple[SeasonYear, ...]
    summary: str  # "regularly_green", "not_green", "irregular", "insufficient"

    @property
    def with_cycle(self) -> int:
        return sum(1 for y in self.years if y.status == "cycle")

    @property
    def without_cycle(self) -> int:
        return sum(1 for y in self.years if y.status == "no_cycle")

    @property
    def unclear(self) -> int:
        return sum(1 for y in self.years if y.status == "unclear")

    @property
    def clear(self) -> int:
        return self.with_cycle + self.without_cycle

    @property
    def period(self) -> str:
        return f"{self.years[0].label} to {self.years[-1].label}" if self.years else "no years"

    def sentence(self) -> str:
        name = self.season_name
        if self.summary == "regularly_green":
            return f"A vegetation cycle was detected in the {name} window in {self.with_cycle} of {self.clear} clear years ({self.period})."
        if self.summary == "not_green":
            return f"No vegetation cycle was detected in the {name} window in any of {self.clear} clear years ({self.period})."
        if self.summary == "irregular":
            return f"A vegetation cycle was detected in the {name} window in only {self.with_cycle} of {self.clear} clear years ({self.period})."
        return f"Too few clear years ({self.clear}) to describe the {name} window ({self.unclear} unclear)."


# ─────────────────────────────── retrieval ───────────────────────────────

Transport = Callable[[str, float], bytes]


def _default_transport(url: str, timeout_seconds: float) -> bytes:
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS endpoint
        return response.read()


def build_band_url(latitude: float, longitude: float, band: str, start_year: int, end_year: int) -> str:
    return (
        f"{ORNL_SUBSET_ENDPOINT}?latitude={latitude}&longitude={longitude}&band={band}"
        f"&startDate=A{start_year}001&endDate=A{end_year}001&kmAboveBelow=0&kmLeftRight=0"
    )


class PhenologyClient:
    """Retrieve one pixel's MCD12Q2 bands (one request per band, ≤10 years)."""

    def __init__(self, timeout_seconds: float = 60.0, retries: int = 2, transport: Transport = _default_transport) -> None:
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self._transport = transport
        self._cache: dict[tuple[float, float, int, int], PhenologyRecord] = {}

    def fetch(
        self,
        latitude: float,
        longitude: float,
        start_year: int,
        end_year: int,
        progress: Callable[[int, int], None] | None = None,
    ) -> PhenologyRecord:
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise PhenologyError("Latitude must be −90 to 90 and longitude −180 to 180.")
        if end_year < start_year or end_year - start_year + 1 > MAX_YEARS_PER_REQUEST:
            raise PhenologyError(f"Request between 1 and {MAX_YEARS_PER_REQUEST} product years.")
        key = (round(latitude, 5), round(longitude, 5), start_year, end_year)
        if key in self._cache:
            return self._cache[key]
        bands: dict[str, dict] = {}
        for index, band in enumerate(BANDS, 1):
            url = build_band_url(latitude, longitude, band, start_year, end_year)
            bands[band] = {"source_url": url, "response": self._get(url)}
            if progress:
                progress(index, len(BANDS))
        wrapper = {
            "_fixture_metadata": {
                "latitude": latitude, "longitude": longitude,
                "retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "bands": bands,
        }
        record = parse_phenology(wrapper, mode="live")
        self._cache[key] = record
        return record

    def _get(self, url: str) -> dict:
        last_error: Exception | None = None
        for _ in range(self.retries + 1):
            started = monotonic()
            try:
                return json.loads(self._transport(url, self.timeout_seconds).decode("utf-8"))
            except HTTPError as error:
                last_error = error
                if error.code < 500:
                    raise PhenologyNetworkError(f"ORNL DAAC returned HTTP {error.code}.") from error
            except (URLError, TimeoutError, OSError) as error:
                last_error = error
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise PhenologyResponseError("ORNL DAAC returned a response that is not JSON.") from error
            if monotonic() - started > self.timeout_seconds:
                break
        raise PhenologyNetworkError(
            "Could not retrieve MODIS phenology from the ORNL DAAC subset service (it sometimes returns HTTP 502). Retry later."
        ) from last_error


# ─────────────────────────────── parsing ───────────────────────────────

def _date(raw: object) -> date | None:
    if raw is None or raw == FILL_VALUE:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise PhenologyResponseError(f"Unexpected date value {raw!r}.")
    return EPOCH + timedelta(days=int(raw))


def _band_values(wrapper: Mapping, band: str) -> dict[int, object]:
    try:
        subset = wrapper["bands"][band]["response"]["subset"]
    except (KeyError, TypeError) as error:
        raise PhenologyResponseError(f"MCD12Q2 band {band} is missing from the response.") from error
    values: dict[int, object] = {}
    for item in subset:
        try:
            year = int(str(item["calendar_date"])[:4])
            data = item["data"]
        except (KeyError, TypeError, ValueError) as error:
            raise PhenologyResponseError(f"MCD12Q2 band {band} has a malformed record.") from error
        if not isinstance(data, list) or len(data) != 1:
            raise PhenologyResponseError(f"MCD12Q2 band {band} should contain exactly one pixel per year.")
        values[year] = data[0]
    return values


def parse_phenology(wrapper: Mapping, mode: str = "saved") -> PhenologyRecord:
    """Parse saved or live ORNL responses; fill values become ``None``."""
    meta = wrapper.get("_fixture_metadata", {}) if isinstance(wrapper, Mapping) else {}
    raw = {band: _band_values(wrapper, band) for band in BANDS}
    years = tuple(sorted(raw["NumCycles"]))
    if not years:
        raise PhenologyResponseError("MCD12Q2 returned no product years.")
    num_cycles: dict[int, int | None] = {}
    cycles: list[VegetationCycle] = []
    for year in years:
        count = raw["NumCycles"].get(year)
        num_cycles[year] = None if count in (None, FILL_VALUE) else int(count)  # type: ignore[arg-type]
        for mode_number in (1, 2):
            suffix = f".Num_Modes_0{mode_number}"
            mid_up = _date(raw["MidGreenup" + suffix].get(year))
            mid_down = _date(raw["MidGreendown" + suffix].get(year))
            if mid_up is None and mid_down is None:
                continue
            amplitude = raw["EVI_Amplitude" + suffix].get(year)
            qa = raw["QA_Overall" + suffix].get(year)
            cycles.append(VegetationCycle(
                product_year=year, mode=mode_number,
                greenup=_date(raw["Greenup" + suffix].get(year)), mid_greenup=mid_up,
                mid_greendown=mid_down, dormancy=_date(raw["Dormancy" + suffix].get(year)),
                evi2_amplitude=None if amplitude in (None, FILL_VALUE) else float(amplitude) * 0.0001,  # type: ignore[arg-type]
                qa_overall=None if qa in (None, FILL_VALUE) else int(qa),  # type: ignore[arg-type]
            ))
    processing = tuple(sorted({
        str(item.get("proc_date")) for item in wrapper["bands"]["NumCycles"]["response"]["subset"] if item.get("proc_date")
    }))
    first = wrapper["bands"]["NumCycles"]["response"]
    return PhenologyRecord(
        latitude=float(meta.get("latitude", first.get("latitude"))),
        longitude=float(meta.get("longitude", first.get("longitude"))),
        product=PRODUCT_LABEL,
        resolution=RESOLUTION,
        years=years,
        num_cycles=num_cycles,
        cycles=tuple(cycles),
        source_urls=tuple(wrapper["bands"][band]["source_url"] for band in BANDS),
        retrieved_at_utc=str(meta.get("retrieved_at_utc", "unknown")),
        processing_dates=processing,
        mode=mode,
    )


def load_demo_phenology(path: Path | str | None = None) -> PhenologyRecord:
    """Saved, unmodified ORNL responses for the demonstration farm pixel (2016–2025)."""
    payload = json.loads(Path(path or DEMO_PHENOLOGY_PATH).read_text(encoding="utf-8"))
    return parse_phenology(payload, mode="saved")


# ─────────────────────────── season assignment ───────────────────────────

def _window(season_id: str, year: int) -> tuple[date, date]:
    season = REGIONAL_SEASONS[season_id]
    start = date(year, season.start_month, season.start_day)
    end = date(year + (1 if season.is_cross_year else 0), season.end_month, season.end_day)
    return start, end


def season_of_cycle(cycle: VegetationCycle) -> tuple[str, int] | None:
    """(season_id, season start year) whose window contains the cycle centre.

    Windows overlap (April: rabi/summer; 1–15 June: summer/kharif). The tie
    goes to the window that overlaps the cycle's MidGreenup–MidGreendown span
    the most.
    """
    centre = cycle.centre
    if centre is None:
        return None
    candidates: list[tuple[int, str, int]] = []
    for season_id in PLANNING_SEASONS:
        for start_year in (centre.year - 1, centre.year):
            start, end = _window(season_id, start_year)
            if start <= centre <= end:
                span_start, span_end = max(start, cycle.mid_greenup), min(end, cycle.mid_greendown)  # type: ignore[type-var]
                overlap = max(0, (span_end - span_start).days)
                candidates.append((overlap, season_id, start_year))
    if not candidates:
        return None
    _, season_id, start_year = max(candidates, key=lambda item: (item[0], item[1]))
    return season_id, start_year


def _season_label(season_id: str, start_year: int) -> str:
    return f"{start_year}–{str(start_year + 1)[-2:]}" if REGIONAL_SEASONS[season_id].is_cross_year else str(start_year)


def season_use(record: PhenologyRecord) -> dict[str, SeasonUse]:
    """Per planning season: was a vegetation cycle detected in each fully covered year?

    Kharif and summer seasons are evaluated for every product year. A rabi
    season Y–Y+1 is evaluated only if both product years are present, because
    its cycle can peak in either year. A year is *unclear* when NumCycles is
    missing, the matching cycle has poor QA, or more than two cycles exist
    (the product reports only the two largest).
    """
    assigned: dict[tuple[str, int], list[VegetationCycle]] = {}
    for cycle in record.cycles:
        placed = season_of_cycle(cycle)
        if placed:
            assigned.setdefault(placed, []).append(cycle)
    years = set(record.years)
    result: dict[str, SeasonUse] = {}
    for season_id in PLANNING_SEASONS:
        season = REGIONAL_SEASONS[season_id]
        if season.is_cross_year:
            starts = [y for y in sorted(years) if y + 1 in years]
            product_years = {y: (y, y + 1) for y in starts}
        else:
            starts = sorted(years)
            product_years = {y: (y,) for y in starts}
        entries: list[SeasonYear] = []
        for start_year in starts:
            label = _season_label(season_id, start_year)
            counts = [record.num_cycles.get(y) for y in product_years[start_year]]
            found = assigned.get((season_id, start_year), [])
            if any(c is None for c in counts):
                entries.append(SeasonYear(season_id, label, "unclear", "Number of cycles not reported for this year."))
            elif found and all(c.qa_overall == 3 for c in found):
                entries.append(SeasonYear(season_id, label, "unclear", "Detected cycle has poor quality (QA 3)."))
            elif found:
                best = min(found, key=lambda c: c.qa_overall if c.qa_overall is not None else 9)
                entries.append(SeasonYear(
                    season_id, label, "cycle",
                    f"Mid-greenup {best.mid_greenup:%d %b %Y}, mid-greendown {best.mid_greendown:%d %b %Y}; QA {best.quality}.",
                ))
            elif any((c or 0) > 2 for c in counts):
                entries.append(SeasonYear(season_id, label, "unclear", "More than two cycles detected; only the two largest are reported."))
            else:
                entries.append(SeasonYear(season_id, label, "no_cycle", "No reported cycle is centred in this window."))
        clear = [e for e in entries if e.status != "unclear"]
        with_cycle = sum(1 for e in clear if e.status == "cycle")
        if len(clear) < MIN_CLEAR_YEARS:
            summary = "insufficient"
        elif with_cycle > len(clear) / 2:
            summary = "regularly_green"
        elif with_cycle == 0:
            summary = "not_green"
        else:
            summary = "irregular"
        result[season_id] = SeasonUse(season_id, season.name, tuple(entries), summary)
    return result
