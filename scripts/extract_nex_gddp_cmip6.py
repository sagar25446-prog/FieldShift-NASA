"""Extract a documented NEX-GDDP-CMIP6 point record for one location.

Run once to (re)build the scenario extract FieldShift ships with:

    python scripts/extract_nex_gddp_cmip6.py 30.85 75.70 data/nex_gddp_cmip6_demo_farm

For each model, experiment, variable and year it reads **one 0.25° grid cell**
through the NCCS THREDDS OPeNDAP service (an index slice, so no global file is
downloaded; no authentication), checks the returned cell coordinates and
time axis, and writes the values unmodified, in source units, to one gzipped
CSV per model/experiment. ``metadata.json`` records the request pattern, grid
cell, units, calendar, licence and dataset version read from each file's
attributes, and the retrieval time. The script is resumable.

Variables are limited to tasmax, tasmin and pr: the full seven-variable set
needed ~2,100 slow server-side requests. FieldShift applies the documented
FAO-56 missing-data procedures for radiation, humidity and wind identically to
the historical and future periods (see docs/FUTURE_CLIMATE.md).
"""

from __future__ import annotations

import concurrent.futures as futures
import csv
import gzip
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CATALOG = "https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6"
DODS = "https://ds.nccs.nasa.gov/thredds/dodsC/AMES/NEX/GDDP-CMIP6"
MODELS = ("ACCESS-CM2", "EC-Earth3", "GFDL-ESM4", "MPI-ESM1-2-HR", "MRI-ESM2-0")
EXPERIMENTS = {"historical": (1995, 2014), "ssp245": (2041, 2060), "ssp585": (2041, 2060)}
VARIABLES = ("tasmax", "tasmin", "pr")
LAT0, LON0, STEP = -59.875, 0.125, 0.25  # grid documented in the dataset's dds/das
NOLEAP = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def get(url: str, attempts: int = 6) -> str:
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(url, timeout=90).read().decode("utf-8")
        except Exception as error:  # noqa: BLE001 - retried, then re-raised
            if attempt == attempts - 1:
                raise RuntimeError(f"{url}: {error}") from error
            time.sleep(5 * (attempt + 1))
    raise AssertionError


def decode_day(value: float, units: str, calendar: str) -> date:
    match = re.match(r"days since (\d{4})-(\d{2})-(\d{2})", units)
    if not match:
        raise RuntimeError(f"Unsupported time units {units!r}")
    ref = date(int(match[1]), int(match[2]), int(match[3]))
    days = int(value)  # values are mid-day (x.5)
    if calendar in ("proleptic_gregorian", "gregorian", "standard"):
        return ref + timedelta(days=days)
    if calendar in ("365_day", "noleap"):
        if (ref.month, ref.day) != (1, 1):
            raise RuntimeError("365-day decoding assumes a 1 January reference date")
        year, doy = ref.year + days // 365, days % 365
        month = 0
        while doy >= NOLEAP[month]:
            doy -= NOLEAP[month]
            month += 1
        return date(year, month + 1, doy + 1)
    raise RuntimeError(f"Unsupported calendar {calendar!r}")


def days_in_year(year: int, calendar: str) -> int:
    if calendar in ("365_day", "noleap"):
        return 365
    return 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365


def parse_ascii(text: str, variable: str) -> tuple[list[str], list[float], float, float]:
    values = re.findall(r"^\[\d+\]\[0\], (\S+)$", text.split(f"{variable}.time[")[0], flags=re.M)
    times_block = text.split(f"{variable}.time[")[1].split("\n", 1)[1].split(f"{variable}.lat[")[0]
    times = [float(t) for t in times_block.replace("\n", " ").split(",") if t.strip()]
    lat = float(text.split(f"{variable}.lat[1]")[1].split()[0])
    lon = float(text.split(f"{variable}.lon[1]")[1].split()[0])
    return values, times, lat, lon


def main(latitude: float, longitude: float, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    i_lat = round((latitude - LAT0) / STEP)
    i_lon = round(((longitude % 360) - LON0) / STEP)
    meta: dict = {
        "dataset": "NASA NEX-GDDP-CMIP6",
        "documentation": "https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6",
        "technical_note": "https://www.nccs.nasa.gov/wp-content/uploads/2025/06/NEX-GDDP-CMIP6-v2-Tech_Note.pdf",
        "citation": "Thrasher, B., Wang, W., Michaelis, A. et al. (2022). NASA Global Daily Downscaled Projections, CMIP6. Sci Data 9, 262. https://doi.org/10.1038/s41597-022-01393-4",
        "access": "NCCS THREDDS OPeNDAP index slice of a single grid cell; no authentication",
        "requested_latitude": latitude,
        "requested_longitude": longitude,
        "grid_indices": {"lat": i_lat, "lon": i_lon},
        "experiments": {k: list(v) for k, v in EXPERIMENTS.items()},
        "variables": list(VARIABLES),
        "retrieval_started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "models": {},
    }
    for model in MODELS:
        model_meta: dict = {"experiments": {}}
        for experiment, (start, end) in EXPERIMENTS.items():
            csv_path = out_dir / f"{model}_{experiment}_{start}-{end}.csv.gz"
            part = out_dir / f"{model}_{experiment}.meta.json"
            if part.exists() and csv_path.exists():
                saved = json.loads(part.read_text(encoding="utf-8"))
                model_meta.update({"licence": saved["licence"], "calendar": saved["calendar"]})
                model_meta["experiments"][experiment] = saved["experiment"]
                print(model, experiment, "already extracted", flush=True)
                continue
            variant = re.findall(r'title="(r\d+i\d+p\d+f\d+)"', get(f"{CATALOG}/{model}/{experiment}/catalog.xml"))[0]
            info: dict = {"variant": variant, "years": [start, end], "units": {}, "files": {}}
            jobs = []
            for variable in VARIABLES:
                listing = get(f"{CATALOG}/{model}/{experiment}/{variant}/{variable}/catalog.xml")
                name = re.search(rf'name="({variable}_day_{re.escape(model)}_{experiment}_{variant}_\w+?_{start}(_v[\d.]+)?\.nc)"', listing)[1]
                das = get(f"{DODS}/{model}/{experiment}/{variant}/{variable}/{name}.das")
                attr = lambda key, text=das: (re.search(rf'{key} "([^"]*)"', text) or [None, None])[1]  # noqa: E731
                time_block = das.split("time {")[1].split("}")[0]
                calendar = re.search(r'calendar "([^"]+)"', time_block)[1]
                time_units = re.search(r'units "([^"]+)"', time_block)[1]
                var_block = das.split(f"    {variable} {{")[1].split("}")[0]
                info["units"][variable] = re.search(r'units "([^"]+)"', var_block)[1]
                info["files"][variable] = f"{DODS}/{model}/{experiment}/{variant}/{variable}/" + name.replace(str(start), "{year}")
                model_meta.update({"licence": attr("cmip6_license"), "calendar": calendar})
                info["dataset_version"] = attr("version")
                for year in range(start, end + 1):
                    n = days_in_year(year, calendar)
                    url = f"{info['files'][variable].format(year=year)}.ascii?{variable}%5B0:{n - 1}%5D%5B{i_lat}%5D%5B{i_lon}%5D"
                    jobs.append((variable, year, url, calendar, time_units, n))
            info["request_example"] = jobs[0][2]
            rows: dict[str, dict[str, str]] = {}
            cell = None
            with futures.ThreadPoolExecutor(4) as pool:
                results = pool.map(lambda job: get(job[2]), jobs)
                for done, (job, text) in enumerate(zip(jobs, results), 1):
                    variable, year, _, calendar, time_units, n = job
                    values, times, lat, lon = parse_ascii(text, variable)
                    if len(values) != n or len(times) != n:
                        raise RuntimeError(f"{model} {experiment} {variable} {year}: expected {n} days, got {len(values)}")
                    days = [decode_day(t, time_units, calendar) for t in times]
                    if days[0] != date(year, 1, 1) or days[-1] != date(year, 12, 31):
                        raise RuntimeError(f"{model} {experiment} {variable} {year}: time axis {days[0]}..{days[-1]}")
                    if cell is not None and cell != (lat, lon):
                        raise RuntimeError("Grid cell changed between requests")
                    cell = (lat, lon)
                    for day, value in zip(days, values):
                        rows.setdefault(day.isoformat(), {})[variable] = value
                    if done % 30 == 0:
                        print(f"  {model} {experiment}: {done}/{len(jobs)}", flush=True)
            info["grid_cell_centre"] = [cell[0], cell[1] - 360 if cell[1] > 180 else cell[1]]
            info["days"] = len(rows)
            with gzip.open(csv_path, "wt", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", *VARIABLES])
                for day in sorted(rows):
                    writer.writerow([day, *(rows[day][v] for v in VARIABLES)])
            model_meta["experiments"][experiment] = info
            part.write_text(json.dumps({"licence": model_meta["licence"], "calendar": model_meta["calendar"], "experiment": info}), encoding="utf-8")
            print(model, experiment, len(rows), "days", info["grid_cell_centre"], info["units"], flush=True)
        meta["models"][model] = model_meta
    meta["retrieval_finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("done", out_dir, flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), float(sys.argv[2]), Path(sys.argv[3]))
