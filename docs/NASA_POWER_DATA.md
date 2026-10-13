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
| `T2M` | Temperature at 2 meters | `C` | Monthly/seasonal average temperature; FAO-56 $T_{\text{mean}}$ |
| `T2M_MAX` | Temperature at 2 meters maximum | `C` | Monthly maximum summary; FAO-56 saturation vapour pressure $e_s(T_{\max})$ |
| `T2M_MIN` | Temperature at 2 meters minimum | `C` | Monthly minimum summary; FAO-56 saturation vapour pressure $e_s(T_{\min})$, dewpoint fallback |
| `PRECTOTCORR` | Precipitation corrected | `mm/day` | Selected-range total and declared dry-period analysis; USDA SCS effective rainfall |
| `ALLSKY_SFC_SW_DWN` | All-sky surface shortwave downward irradiance | `MJ/m^2/day` | FAO-56 solar radiation $R_s$ and net radiation $R_n$ computation |
| `RH2M` | Relative humidity at 2 meters | `%` | FAO-56 actual vapour pressure $e_a$ calculation |
| `WS2M` | Wind speed at 2 meters | `m/s` | FAO-56 aerodynamic term ($u_2$) |

The meanings and units above were verified from live POWER Daily JSON responses for `community=AG`. `DEFAULT_PARAMETERS` retains the original 5 parameters for backward compatibility with baseline fixtures, while `FAO56_METEOROLOGICAL_PARAMETERS` includes `RH2M` and `WS2M`. When relative humidity or wind speed are absent, the FAO-56 calculator applies documented FAO-56 standard fallbacks ($e_a \approx e_s(T_{\min})$, $u_2 \approx 2.0\text{ m/s}$).

## Stored schema

`PowerDataset.data` is a pandas DataFrame indexed by daily `date`, with one float column per requested API parameter. POWER's fill value is converted to `NaN`, never to zero. `PowerDataset.provenance` stores the exact source URL, UTC retrieval time, API version, returned source datasets, requested and returned coordinates, returned elevation, date range, time standard, daily resolution, fill value, parameter names/units, API messages and missing-value counts.

POWER parameters are based on satellite-derived solar radiation and meteorological assimilation-model data. A point query is at source-native gridded resolution, not a direct measurement from the selected farm. It does not measure soil pH, NPK, organic carbon, field soil moisture, or crop yield.

## Derived indicators

- **Season boundary definition:** in this MVP, “season” means the user's inclusive historical start and end dates. FieldShift deliberately does not impose a universal Kharif/Rabi crop calendar because crop windows vary by crop, cultivar, method and local conditions. The selected date range is saved in provenance.
- **Reference evapotranspiration ($ET_0$):** Daily Penman–Monteith calculation (FAO-56 Eq. 6) combining net radiation, temperature, atmospheric vapour deficit, and wind speed.
- **Crop evapotranspiration ($ET_c$):** $ET_c = K_c \times ET_0$ using stage-interpolated crop coefficients from FAO-56 Table 12.
- **USDA SCS Effective Rainfall ($P_{\text{eff}}$):** Monthly USDA Soil Conservation Service formula separating usable rainfall from runoff/deep percolation.
- **Net Irrigation Requirement / Water Deficit ($NIR$):** $\max(0, \sum ET_c - P_{\text{eff}})$, fed directly into rotation water suitability scoring.
- **FAO EcoCrop Thermal Suitability:** Piece-wise linear score (0.0 to 1.0) evaluating mean growing-season temperature against cardinal thermal limits ($T_{\min,\text{abs}}, T_{\min,\text{opt}}, T_{\max,\text{opt}}, T_{\max,\text{abs}}$).
- **Extreme Heat Stress Days:** Count of days where daily $T_{\max}$ reaches or exceeds documented crop threshold (e.g. 32°C for wheat, 35°C for rice, 30°C for potato), reducing suitability proportionally.
- **Selected-range precipitation total:** sum of available `PRECTOTCORR` daily values, reported in mm and warned when days are missing.
- **Monthly temperature summary:** mean `T2M`, minimum `T2M_MIN`, and maximum `T2M_MAX` by calendar month.
- **Historical anomaly:** current indicator minus the mean of a caller-supplied, same-definition historical baseline. The baseline label and values are required; the code does not select one silently.
- **Historical Climate Trends:** Ordinary Least Squares (OLS) multi-year linear trends, decadal rates of change, statistical significance ($p$-values), baseline comparisons, and consecutive dry-spell runs across regional Kharif, Rabi, and Summer crop windows.

See [`docs/WATER_BALANCE_METHODOLOGY.md`](WATER_BALANCE_METHODOLOGY.md) for water balance formulas, [`docs/CLIMATE_SUITABILITY_METHODOLOGY.md`](CLIMATE_SUITABILITY_METHODOLOGY.md) for thermal suitability equations, and [`docs/CLIMATE_TRENDS_METHODOLOGY.md`](CLIMATE_TRENDS_METHODOLOGY.md) for long-term climate trend statistics.

## Error, retry and cache policy

Malformed JSON, missing schema elements, omitted parameters, invalid coordinates, API errors, network failures, timeouts, and all-missing requested series produce named errors. The UI presents the error and a visible retry button; it never uses sample data as a replacement. Successful requests are cached in memory for six hours per exact request. Users can force a refresh. The cache resets when the app process restarts.

## Later extensions

GPM, MODIS and NASA–USDA/SMAP-derived soil-moisture products remain later work. They may require Earthdata authentication, product-specific QA/processing, or scale validation. They must not block this POWER MVP or be represented as field soil measurements.
