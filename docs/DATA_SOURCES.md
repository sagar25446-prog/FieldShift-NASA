# Data Sources

## Demonstration Region

**Ludhiana district, Punjab, India** — selected because Punjab Agricultural University (PAU), in Ludhiana, publishes current Punjab-specific crop guidance and rotation examples.

The illustrative demo farm is at **30.85 N, 75.70 E**, a MODIS-confirmed cropland pixel (MCD12Q1 class 12, 2020–2024) about 16 km WSW of Ludhiana city. It replaced the earlier city-centre point (MCD12Q1 class 13, urban) on 2026-10-13. Both points are in the same NASA POWER grid cell (identical POWER values).

---

## Operational Data Sources

| Source | Use in FieldShift | Classification | Status |
|---|---|---|---|
| [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Historical daily climate context (T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN, RH2M, WS2M) | Gridded NASA meteorological data (~0.5°), not a field measurement | ✅ Integrated |
| [MODIS MCD12Q2 v061](OBSERVED_LAND_USE.md) via ORNL DAAC | Observed vegetation cycles per season (recent land use) | 500 m satellite phenology; not crop identity or yield | ✅ Integrated (observed season-use check) |
| Farmer input | Location, soil conditions, water budget, irrigation, previous crop, blocked crops, priorities | Farmer-provided | ✅ Required input |
| Soil Health Card / lab report | pH, EC, organic carbon, total N, waterlogging, drainage | Measured soil data (farmer states the basis) | ✅ Optional (unknown if absent); always overrides estimates |
| [ISRIC SoilGrids 2.0](https://www.isric.org/explore/soilgrids) REST API (beta) | Optional sand/silt/clay, organic carbon, pH, total N at 0–5, 5–15, 15–30 cm with quantiles and uncertainty | Modelled estimate, 250 m grid, labelled "Estimated from SoilGrids" | ✅ Optional; graceful fallback when unavailable ([details](SOIL_DATA.md)) |
| [PAU Kharif 2026](https://pau.edu/content/ccil/pf/pp_kharif.pdf) | Crop catalogue, growing seasons, rotation sequences | Regional extension guidance | ✅ Catalogue evidence |
| [PAU Rabi 2026](https://pau.edu/content/ccil/pf/pp_rabi.pdf) | Crop catalogue, soil constraints, rotation sequences | Regional extension guidance | ✅ Catalogue evidence |
| [GoI Crop Water Annexure](https://sansad.in/getFile/annex/256/AS110.pdf?source=pqars) | Water requirement ranges (mm) | Government documented approximation | ✅ Catalogue evidence |

## NASA POWER Details

- **Endpoint:** `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Community:** AG (Agroclimatology)
- **Parameters:** T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN
- **Temporal coverage:** 1981-01-01 to near-present
- **Spatial resolution:** ~0.5° × 0.5° grid
- **Authentication:** None required (public API)
- **Fill value:** −999.0 → converted to NaN
- **Time standard:** UTC
- **Caching:** 6-hour in-memory TTL per request
- **Full documentation:** [`docs/NASA_POWER_DATA.md`](NASA_POWER_DATA.md)

## Additional NASA Earth-Observation Dataset: Selection (Task 7)

Decision recorded **before implementation** (2026-10-13). Each candidate was checked against what the recommendation engine already uses and whether it could be retrieved and verified reliably now.

### What the engine already knows

| Engine input | Source | Gap |
|---|---|---|
| Daily rainfall, temperature, radiation, humidity, wind | NASA POWER (MERRA-2 based, ~0.5° × 0.625°) | One precipitation estimate only |
| Crop water demand | FAO-56 from POWER | — |
| Soil properties | Farmer/lab, optional SoilGrids | — |
| **What is actually grown at the location, and in which seasons** | *nothing* | The engine cannot tell whether a plan keeps, adds or drops a cropping season compared with recent land use |

### Candidates compared

| | GPM IMERG (V07, Final) | SMAP | **MODIS vegetation phenology (MCD12Q2 v061)** |
|---|---|---|---|
| New information for the engine | A second, satellite–gauge rainfall estimate at 0.1°, alongside POWER's MERRA-2 rainfall | Soil moisture. The L3 product is the **surface layer (~top 5 cm)**; root-zone moisture is only in the model-based L4 product | **Observed vegetation cycles per year and their timing** (green-up to dormancy), derived from MODIS NBAR-EVI2 |
| Spatial / temporal resolution | 0.1° (~11 km); half-hourly, daily, monthly; 2000–present | L3 enhanced (SPL3SMP_E) 9 km posting, daily, 2015–present; L4 9 km, 3-hourly | 500 m; yearly product (up to two cycles per year), 2001–2025 |
| Access verified 2026-10-13 | **Needs NASA Earthdata Login.** GES DISC OPeNDAP data requests redirect to `urs.earthdata.nasa.gov`; PPS returns 401; the Hydrology Data Rods service has been discontinued. No IMERG value could be retrieved or verified in this session | SPL3SMP_E is on the ORNL DAAC subset service without login. Root-zone L4 (NSIDC) needs Earthdata Login | **No login.** ORNL DAAC Land Product Subsets REST API, one request per band covers up to 10 years; 5–8 s per request in testing |
| Decision value in irrigated Punjab | Limited and risks double counting. Rainfall is already in the water balance; in the 2024 demo record rabi and summer crop periods received ~0–108 mm, so rainfall rarely changes the ranking. A second source would mainly add an uncertainty band | Low for multi-season planning. A daily surface-moisture snapshot reflects recent irrigation or rain, not seasonal water availability. The 9 km pixel mixes many fields | **High and new.** Shows whether a plan *adds* a cropping season (e.g. summer moong) compared with recent land use. That season brings extra crop water demand in a groundwater-stressed region |
| Main limitations | Satellite estimate, not a gauge | Surface ≠ root zone; irrigation signal; coarse | Greenness ≠ yield, crop identity or soil fertility; a 500 m pixel can mix several fields; at most two cycles are reported per year; ORNL service occasionally returns HTTP 502 |

### Choice: MODIS Land Cover Dynamics (MCD12Q2 v061), retrieved via the ORNL DAAC subset service

Reasons:
1. It adds information the engine does not have: observed seasonal land use at the farm's location.
2. It can be retrieved without credentials and was verified now: the demo farm pixel shows two cycles with best QA in every year 2016–2025 (rabi: green-up mid-Dec to dormancy late Apr; kharif: green-up late Jun/early Jul to dormancy early Nov) and **no cycle in the summer window**.
3. Its role in the decision is specific and does not double count. It does **not** change any score. It sets a transparent evidence check on each planned season and quantifies the extra crop water demand of seasons that recent land use leaves bare.

IMERG would be the next candidate if Earthdata credentials are configured. It is documented as future work and has not been integrated or presented as available.

MCD12Q2 is used instead of the raw 16-day MOD13Q1 NDVI because MCD12Q2 provides NASA's published cycle-detection algorithm (Gray, Sulla-Menashe & Friedl, C6.1 user guide). FieldShift therefore does not invent its own greenness thresholds. Raw MOD13Q1 retrieval was also slow and unreliable in testing (HTTP 502 after 61 s).

## Dataset Comparison: What Each Source Contributes

| Source | Variables used | Resolution | Role in a decision | Main limitations |
|---|---|---|---|---|
| NASA POWER Daily (MERRA-2, CERES) | T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN, RH2M, WS2M | ~0.5° × 0.625°; daily; 1981–present | FAO-56 crop water demand and deficit (**water score**); EcoCrop thermal suitability and heat days (**climate score**); historical trends | Gridded reanalysis, not a farm station; one rainfall estimate |
| MODIS MCD12Q2 v061 (via ORNL DAAC) | Number of vegetation cycles; MidGreenup, MidGreendown, Greenup, Dormancy dates; EVI2 amplitude; overall QA | 500 m; yearly; 2001–2025 | **Observed season-use check** per planned season, and **extra crop water demand** of seasons with no recent vegetation cycle. Shown as plan status, trade-off and comparison column; **not** added to the composite score | Greenness is not yield, crop identity or soil fertility; mixed pixels; ≤2 cycles reported; ~6-month product latency |
| MODIS MCD12Q1 (land cover) | IGBP class | 500 m; yearly | Used once to select the demo farm (cropland, not urban) | Not used in scoring |
| NASA NEX-GDDP-CMIP6 v2.0 (5 models; SSP2-4.5, SSP5-8.5) | tasmax, tasmin, pr | 0.25° (~25 km); daily; 1995–2014 vs 2041–2060 | **Future-climate comparison:** the same plan's water score, climate score, ETc, irrigation need and heat days under each model's future vs its own historical run | Projections, not forecasts; 5 of 35 models; temperature and precipitation only; no adaptation or CO₂ effects ([details](FUTURE_CLIMATE.md)) |
| ISRIC SoilGrids 2.0 (optional) | Sand/silt/clay, SOC, pH, total N | 250 m | Starting SOC for the simplified soil model; texture only if robust | Modelled estimate; wide uncertainty; beta API |
| Farmer / laboratory input | Soil tests, water budget, constraints | Field | Hard constraints and overrides | Depends on what the farmer knows |
| GPM IMERG | — | 0.1° | **Not integrated** (needs Earthdata Login) | — |
| SMAP | — | 9 km | **Not integrated** (surface moisture not decision-relevant here) | — |

Full method: [`docs/OBSERVED_LAND_USE.md`](OBSERVED_LAND_USE.md).

## Soil Policy

- Preferred evidence: field-specific laboratory report with date, depth, method, and units
- India's [Soil Health Card](https://soilhealth.dac.gov.in/files/FAQ_Final_English.pdf) program provides farmer reports based on lab-tested samples
- A satellite layer, map, model estimate or district average **never overwrites** a farmer-entered or laboratory result
- An optional ISRIC SoilGrids estimate can fill an **empty** field, labelled "Estimated from SoilGrids", only where the property is appropriate (organic carbon for the educational SOC model; texture only if its full uncertainty range lies in one texture group; pH and total N are context only)
- Hard soil constraints (waterlogging, alkalinity, drainage) and EC come only from the farmer
- If no valid value exists, soil-dependent checks state **unknown**
- No soil values are fabricated. Full method, units, depths, fallback and limitations: [`SOIL_DATA.md`](SOIL_DATA.md)
