# Future-Climate Scenarios (NASA NEX-GDDP-CMIP6)

FieldShift lets a farmer see how the **water and climate suitability of the same rotation** could change under two emissions pathways by mid-century. It uses NASA's bias-corrected, downscaled CMIP6 projections. These are climate projections, **not weather forecasts for any year**, and climate models disagree, so FieldShift always shows the spread across models.

## 1. Source verification (2026-10-13)

| Item | Verified value | Evidence |
|---|---|---|
| Product | NASA Earth Exchange Global Daily Downscaled Projections, **NEX-GDDP-CMIP6**, files labelled dataset version **2.0** | NCCS collection page; v2 technical note (31 May 2025); `version` attribute of every file used |
| Method | Bias-Correction Spatial Disaggregation (BCSD) against the GMFD/Princeton observational forcing (1960–2014) | Technical note §3 |
| Spatial resolution | **0.25° × 0.25°** (about 25 km); 60° S–90° N | Technical note §2; NCSS/OPeNDAP grid metadata |
| Temporal coverage | Daily; historical experiment 1950–2014; SSPs 2015–2100 | Technical note §2–3 |
| Scenarios | SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5 ("Tier 1") | Technical note §3.1 |
| Models | 35 CMIP6 GCMs (Appendix I) | Technical note |
| Variables and source units | `tasmax`, `tasmin` (K); `pr` (kg m⁻² s⁻¹); also tas, hurs, huss, rlds, rsds, sfcWind | Technical note §2; units read from each file |
| Access | NCCS THREDDS (`https://ds.nccs.nasa.gov/thredds/...`) OPeNDAP and NetCDF Subset Service, and the AWS open bucket `s3://nex-gddp-cmip6`. **No authentication** for THREDDS | NCCS page; tested |
| Licence / terms | CMIP6 Terms of Use apply; each file's `cmip6_license` attribute names its licence. All files used here: **CC-BY 4.0** | Technical note §7; file attributes |
| Recommended use | Research and public understanding of possible future climate; "not recommended" for engineering/design or commercial decisions without a qualified expert | Technical note §5.1 |
| Citation | Thrasher, B., Wang, W., Michaelis, A. et al. (2022). *NASA Global Daily Downscaled Projections, CMIP6.* Sci Data 9, 262. doi:10.1038/s41597-022-01393-4 | Technical note §6 |

The NCCS page notes that the site is migrating to a new web platform through 2026. Request URLs may change.

## 2. What FieldShift extracted

`scripts/extract_nex_gddp_cmip6.py` (re-runnable, resumable) reads **one 0.25° grid cell** per file through OPeNDAP index slices. No global file is downloaded.

| Setting | Value | Reason |
|---|---|---|
| Location | Demo farm 30.85 N, 75.70 E → grid cell centred **30.875 N, 75.625 E** | Nearest cell; recorded from the returned coordinates |
| Reference period | **1995–2014**, each model's own *historical* experiment | IPCC AR6 recent-past reference; the historical experiment ends in 2014 |
| Future period | **2041–2060** | IPCC AR6 mid-term period; relevant to planning horizons |
| Scenarios | **SSP2-4.5** (intermediate) and **SSP5-8.5** (very high emissions; a high-end pathway) | "Moderate" vs "higher-emissions", as requested |
| Models | ACCESS-CM2, EC-Earth3, GFDL-ESM4, MPI-ESM1-2-HR, MRI-ESM2-0 (variant r1i1p1f1) | Five different modelling centres, each with complete variables for all three experiments. **Not** selected or weighted by skill. IITM-ESM was excluded because it has no tasmax/tasmin |
| Variables | `tasmax`, `tasmin`, `pr` | The full set needed about 2,100 slow server-side requests; three variables needed 900 |
| Calendars | proleptic Gregorian, except GFDL-ESM4 (365-day, no 29 Feb) | Decoded explicitly; each year's time axis is checked to run 1 Jan–31 Dec |

The extract (`data/nex_gddp_cmip6_demo_farm/`) stores values **unmodified in source units**, with `metadata.json` (request pattern, grid indices, returned cell, units, calendar, licence, dataset version and retrieval time). It is labelled throughout as a NASA projection extract for this grid cell. It is never used for another location.

## 3. Processing

1. **Units:** K → °C; kg m⁻² s⁻¹ × 86 400 → mm/day. An unexpected source unit stops processing (`ProjectionDataError`).
2. **Daily mean temperature** = (Tmax + Tmin)/2 (FAO-56 Eq. 9).
3. **Reference ET (FAO-56 Penman–Monteith):** with no radiation, humidity or wind in the extract, FAO-56's missing-data procedures are used, identically in every period:
   - solar radiation from the temperature range (Eq. 50, kRs = 0.16 for interior locations);
   - vapour pressure from Tmin (Eq. 48);
   - wind 2 m/s.

   Projected changes in cloudiness, humidity and wind are therefore **not** represented.
4. **Crop periods:** each crop uses only its own season window for its FAO-56 duration (`growing_season.py`). With 20 years of data, every period has 20 complete kharif and summer seasons and 19 complete rabi seasons. Results are averaged.
5. **Indicators:**
   - growing-season mean temperature and mean Tmax;
   - days with Tmax ≥ 35 °C per season;
   - seasonal rainfall;
   - per plan: FAO-56 crop water demand (ETc), irrigation need beyond effective rain, the water score, the EcoCrop climate score and heat-stress days against each crop's documented threshold, and the composite score using the farmer's own weights.
6. **Comparison:** for each model, `future − same model's historical`. Summary = median across the five models, with the lowest and highest model, and how many models agree on the direction of change.

**Never combined:** NASA POWER observations and model output are never differenced. The observed baseline and hypothetical stress tests stay on their own pages. Records from different grid cells, different future periods, or with spans that differ from the declared years are rejected when loading.

## 4. How it feeds the recommendation

The same `RotationEngine` runs with the same crops, crop calendar, crop coefficients and thresholds, documented constraints, water budget and priority weights. Only the daily climate record changes. Projection-derived indicators therefore flow into the existing **water suitability** and **climate suitability** metrics and the composite. The UI shows:

- the seasonal climate change (median and model range, with model agreement);
- for a selected plan: each indicator under the models' historical period and the change under SSP2-4.5 and SSP5-8.5;
- one dot per model for the water and climate scores;
- optionally, the ranking of all plans under each period (ensemble-median composite), so the farmer can see whether the preferred plan changes.

## 5. Worked example

*Filled in from the installed extract; see Section 7.*

## 6. Limitations

- Five of 35 models; the full CMIP6 spread is wider. No model weighting.
- 0.25° grid-cell values, not field conditions. BCSD assumes present-day spatial patterns persist.
- Each future 20-year period is a climate sample, not a forecast for 2041, 2050 or any other year.
- Temperature and precipitation only. The ET0 substitutions mean changes in humidity, radiation and wind are not captured.
- Crop calendars, varieties and irrigation practice are held fixed. Adaptation and CO₂ fertilisation are not modelled.
- Hard constraints based on soil or farmer evidence do not change with climate. A plan can still lose water feasibility if demand rises above the farmer's budget.

## 7. Tests

`tests/test_future_climate.py` covers:
- scenario metadata;
- temporal alignment (declared vs actual spans, shared future period, grid-cell consistency);
- units (conversion and refusal of unexpected units);
- missing variables;
- reproducible, model-paired change calculations on a synthetic extract with known +1/+2/+3 K warming;
- the FAO-56 Eq. 50 substitution being used only when no radiation column exists;
- a consistency check on the installed extract.
