# Soil Data: Farmer/Laboratory Values and SoilGrids Estimates

FieldShift accepts soil information from two kinds of source and never merges them silently:

1. **Farmer-entered values**: a laboratory soil test, a farmer observation, or (in the demo only) an illustrative value. The farmer states which.
2. **Optional SoilGrids estimates**: model predictions from ISRIC SoilGrids 2.0 for a 250 m grid cell, labelled **"Estimated from SoilGrids"**.

A farmer-entered value always overrides an estimate. An estimate fills a field only if the farmer left it empty, and only where the property is appropriate for that use (see the table below).

---

## 1. Source verification (checked 2026-10-13)

| Item | Finding | Evidence |
|---|---|---|
| Product | SoilGrids 2.0 global soil-property maps, 250 m, six GlobalSoilMap depth intervals, CC BY 4.0 | [ISRIC SoilGrids](https://www.isric.org/explore/soilgrids) |
| Properties offered | bdod, cec, cfvo, clay, nitrogen, ocd, ocs, phh2o, sand, silt, soc, wv0010, wv0033, wv1500 | [SoilGrids FAQ – units](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html) |
| Depth intervals | 0–5, 5–15, 15–30, 30–60, 60–100, 100–200 cm | same |
| Uncertainty | Q0.05, Q0.5, Q0.95 quantiles, mean, and an "uncertainty" layer = (Q0.95 − Q0.05)/Q0.50, stored ×10 | same; verified numerically against live responses |
| Access methods | WMS/WCS (`maps.isric.org`), WebDAV full VRT/GeoTIFF maps (`files.isric.org`, ~5 GB per map), SoilGrids.org, Google Earth Engine, REST API v2.0 (beta) | [SoilGrids FAQ – access](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html) |
| REST API conditions | Beta. No uptime guarantee or support. Fair use is **5 calls per minute**. ISRIC's site says the API is **"temporarily paused" because of issues**, with no restoration date. ISRIC recommends WebDAV/WCS for production use | same; ISRIC SoilGrids page |
| Observed behaviour | Despite the notice, the REST endpoint answered during development. A full query (6 properties × 3 depths × 5 values) took about 21–29 s server-side. The former demo coordinates in central Ludhiana (30.9010 N, 75.8573 E; MODIS land cover *urban*) return **null for every value**; the current demo farm (30.85 N, 75.70 E; *cropland*) returns complete values | Live requests, saved unmodified in `tests/fixtures/soilgrids_*.json` |

**Chosen method:** the REST `properties/query` endpoint, one targeted point request per click. WCS would need GeoTIFF parsing (an extra GDAL/rasterio dependency) for a single pixel, and WebDAV means downloading global maps. Neither is justified for a point lookup. Because the REST service is beta and may be paused, every failure leads to a graceful fallback (Section 5).

The source does not say why some pixels return null. FieldShift reports "no prediction returned" and does not guess a cause.

## 2. What FieldShift requests and stores

- **Endpoint:** `https://rest.isric.org/soilgrids/v2.0/properties/query`
- **Properties:** `clay`, `sand`, `silt` (texture), `soc` (soil organic carbon), `phh2o` (pH in water), `nitrogen` (total N)
- **Depths:** `0-5cm`, `5-15cm`, `15-30cm`
- **Values:** `mean`, `Q0.05`, `Q0.5`, `Q0.95`, `uncertainty`

For every value FieldShift keeps the source URL (the exact request), the retrieval time (UTC), the requested and returned coordinates, the property name, the mapped and conventional units, the `d_factor`, the depth interval (top/bottom cm), the resolution statement, the quantiles, the uncertainty ratio and the licence. Code: `src/fieldshift/soil_data.py` (`SoilGridsClient`, `parse_soilgrids_response`, `SoilGridsEstimate`).

### Units

| Property | Mapped unit (API) | ÷ d_factor | Conventional unit used | Used as |
|---|---|---|---|---|
| clay, sand, silt | g/kg | 10 | % | texture group (if robust) |
| soc | dg/kg | 10 | g/kg, then ÷10 → % | starting SOC for the soil-state model |
| phh2o | pH × 10 | 10 | pH | context only |
| nitrogen | cg/kg | 100 | g/kg | context only |
| uncertainty | ratio × 10 | 10 | unitless ratio | displayed |

If the API reports a conventional unit other than the documented one, parsing **fails** rather than converting under a wrong assumption.

## 3. Depth handling

When an estimate feeds a calculation, FieldShift uses one depth only: **0–30 cm**, the thickness-weighted mean of the 0–5, 5–15 and 15–30 cm predicted means (weights 5/30, 10/30, 15/30).

- 0–30 cm is the depth for which the FAO/HWSD three-class topsoil texture groups are defined.
- If any of the three interval means is missing, no 0–30 cm value is produced. A partial depth is never presented as 0–30 cm.
- Quantiles cannot be averaged across depths. The displayed range is the lowest Q0.05 to the highest Q0.95 of the three intervals: a conservative envelope, **not a statistical prediction interval**.
- Farmer/laboratory values keep the sampling depth the farmer typed (e.g. "0–15 cm"), shown as "Not stated" if blank. A 0–15 cm laboratory value is never averaged with a 0–30 cm estimate.

## 4. Where estimates are (and are not) used

| Planner input | Farmer/lab value | SoilGrids estimate | Reason |
|---|---|---|---|
| Texture (light/medium/heavy) for the PAU "best soil context" checks of rapeseed/mustard and pearl millet | Used | Used **only if the whole 0–30 cm sand × clay uncertainty box lies in one FAO texture group**; otherwise unknown | These checks can only pass or stay unknown, never reject. Requiring the full range to stay in one group stops a highly uncertain mean from passing a check. At the rural test point the clay range is 1.8–86.3 %, so texture stays unknown |
| Organic carbon (%) for the simplified SOC-direction model | Used | Used (0–30 cm, with range) | The model is educational and uncalibrated. With an estimate it uses a 0.30 m depth, and it reports a direction only if the direction is the same at the value and at both ends of the range; otherwise "uncertain" |
| pH | Shown | Shown | No source-backed pH threshold exists in the crop catalogue, so no check uses pH |
| Total nitrogen (g/kg) | Shown | Shown | No catalogue threshold. Total N is **not** Soil Health Card "available N" (kg/ha); the two are never compared |
| EC, waterlogging, drainage, highly deteriorated alkaline condition | Used | **Never** | SoilGrids does not estimate these. Hard constraints (e.g. PAU's wheat exceptions) rely only on farmer evidence |

No soil-health score is built from missing properties. If nothing usable is available, the soil-related score stays "N/A" with an explanation.

**FAO/HWSD texture groups (0–30 cm):** fine = clay > 35 %; coarse = clay < 18 % and sand > 65 %; medium = everything else ([UNEP/MapX topsoil textural class, citing HWSD v1.21](https://wesr-search.unep.org/ckan/dataset/mapx-topsoil-textural-class)). FieldShift reads coarse → "light", medium → "medium", fine → "heavy". That terminology mapping needs agronomist review before it is relied on.

**Method difference:** SoilGrids organic carbon is harmonised from many laboratory methods. Indian soil-test reports often use Walkley–Black oxidisable carbon. The two are not converted into each other, and the UI says so.

## 5. Failure and fallback

| Situation | What the farmer sees | Planner behaviour |
|---|---|---|
| Network error, timeout (60 s) or HTTP 5xx | "SoilGrids estimate unavailable … You can continue planning" | Soil properties stay as entered or unknown |
| HTTP 429, or a second request within 12 s | Fair-use message (5 calls/min) | Same |
| Malformed JSON or unexpected units | Unavailable message | Same; nothing is converted |
| All values null for the location | "SoilGrids returned no prediction for this exact location" | Same |
| Coordinates changed after an estimate | Estimate is discarded | An estimate is never reused for another location |

Successful results are cached in memory per coordinate for the session's process (SoilGrids maps are static releases).

## 6. Spatial-resolution limits

- Each value is a **model prediction for a 250 m grid cell (~6 ha)**, not a measurement of a particular field.
- Fields inside one cell can differ widely, especially after years of different irrigation, residue and fertiliser management. SoilGrids cannot see recent management.
- The 90 % prediction ranges at Punjab test points are very wide (clay 1.8–86 %, SOC 0.13–2.9 %). An estimate is a starting point for discussion, not a basis for fertiliser or crop decisions.

## 7. How a farmer replaces an estimate with a laboratory measurement

1. Open **Farm Profile**.
2. Under **"Soil test or farmer-entered soil values"**, set **"What are these soil values based on?"** to **"Laboratory soil test (farmer-entered)"**.
3. Type the laboratory values (e.g. organic carbon %, pH, EC), the **sampling depth** (e.g. "0–15 cm") and the **report reference** (e.g. Soil Health Card number and date).
4. Click **Save farm profile**.

The **"Soil values the planner actually uses"** table then shows the laboratory value with source "Laboratory soil test (farmer-entered)". The SoilGrids estimate moves to the "Not used (shown for comparison)" column. Clearing a field hands it back to the estimate, if one is appropriate, or to "Unknown".

## 8. Tests

- `tests/test_soil_data.py` (fixture-based, deterministic) covers unit conversion, uncertainty ratio, depth intervals, missing values (all-null location, partial depth, missing quantiles), the texture appropriateness rule, source precedence and manual overrides, failed requests (network, timeout, HTTP 429/503, invalid JSON, invalid coordinates), the fair-use guard and caching, engine disclosure, and the SOC-range logic.
- `tests/test_soilgrids_integration.py` is a **live** test, skipped unless `RUN_SOILGRIDS_INTEGRATION=1`. It passed on 2026-10-13 (24.9 s).
