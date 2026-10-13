# NASA POWER daily climate data

## Selected service and endpoint

FieldShift uses the public, keyless NASA POWER Daily point endpoint:

```text
https://power.larc.nasa.gov/api/temporal/daily/point
```

Request options are `community=AG`, `format=JSON`, an explicit `time-standard=UTC` or `LST`, latitude, longitude, inclusive `start`/`end` dates, and a comma-separated parameter list. The code uses UTC by default so dates are explicit and comparable. NASA's Daily API documentation says daily UTC and LST data are available from 1981-01-01 to near-real-time and that the API returns analysis-ready daily time series. No API key is documented or sent by FieldShift. See the [Getting Started guide](https://power.larc.nasa.gov/docs/tutorials/api-getting-started/) and [Daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).

## Initial parameters

| API name | Returned meaning | Returned unit | Intended historical indicator use |
| --- | --- | --- | --- |
| `T2M` | Temperature at 2 meters | `C` | Monthly/seasonal average temperature |
| `T2M_MAX` | Temperature at 2 meters maximum | `C` | Monthly maximum summary |
| `T2M_MIN` | Temperature at 2 meters minimum | `C` | Monthly minimum summary |
| `PRECTOTCORR` | Precipitation corrected | `mm/day` | Selected-range total and declared dry-period analysis |
| `ALLSKY_SFC_SW_DWN` | All-sky surface shortwave downward irradiance | `MJ/m^2/day` | Provenance-preserved climate context; no crop rule yet |

The meanings and units above were verified from a live POWER Daily JSON response on 2026-10-12 for `community=AG`. The client also reads and preserves the API's returned parameter metadata rather than trusting this table alone.

## Stored schema

`PowerDataset.data` is a pandas DataFrame indexed by daily `date`, with one float column per requested API parameter. POWER's fill value is converted to `NaN`, never to zero. `PowerDataset.provenance` stores the exact source URL, UTC retrieval time, API version, returned source datasets, requested and returned coordinates, returned elevation, date range, time standard, daily resolution, fill value, parameter names/units, API messages and missing-value counts.

POWER parameters are based on satellite-derived solar radiation and meteorological assimilation-model data. A point query is at source-native gridded resolution, not a direct measurement from the selected farm. It does not measure soil pH, NPK, organic carbon, field soil moisture, or crop yield.

## Derived indicators

- **Season boundary definition:** in this MVP, “season” means the user's inclusive historical start and end dates. FieldShift deliberately does not impose a universal Kharif/Rabi crop calendar because crop windows vary by crop, cultivar, method and local conditions. The selected date range is saved in provenance.
- **Selected-range precipitation total:** sum of available `PRECTOTCORR` daily values, reported in mm and warned when days are missing.
- **Monthly temperature summary:** mean `T2M`, minimum `T2M_MIN`, and maximum `T2M_MAX` by calendar month.
- **Historical anomaly:** current indicator minus the mean of a caller-supplied, same-definition historical baseline. The baseline label and values are required; the code does not select one silently.
- **Consecutive dry periods:** contiguous days at or below a caller-declared `dry_day_max_mm`. This is an analytical definition, not a crop threshold; missing dates end a run.

The initial UI exposes climate preview only. It does not call a historical summary a forecast and does not compare climate against crop thresholds.

## Error, retry and cache policy

Malformed JSON, missing schema elements, omitted parameters, invalid coordinates, API errors, network failures, timeouts, and all-missing requested series produce named errors. The UI presents the error and a visible retry button; it never uses sample data as a replacement. Successful requests are cached in memory for six hours per exact request. Users can force a refresh. The cache resets when the app process restarts.

## Later extensions

GPM, MODIS and NASA–USDA/SMAP-derived soil-moisture products remain later work. They may require Earthdata authentication, product-specific QA/processing, or scale validation. They must not block this POWER MVP or be represented as field soil measurements.
