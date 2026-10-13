# Observed Seasonal Land Use (NASA MODIS MCD12Q2)

FieldShift compares each rotation plan with how the land at the farm's location has actually been used in recent years. If a plan puts a crop in a season that has shown **no vegetation cycle** in recent years, FieldShift flags it as an *added cropping season* and states that season's extra crop water demand.

Selection reasoning and the comparison with GPM IMERG and SMAP: [`DATA_SOURCES.md`](DATA_SOURCES.md#additional-nasa-earth-observation-dataset-selection-task-7).

## Dataset

| Item | Value |
|---|---|
| Product | MODIS/Terra+Aqua Land Cover Dynamics **MCD12Q2**, Collection 6.1 |
| Input signal | Daily NBAR-EVI2 (two-band Enhanced Vegetation Index from BRDF-adjusted reflectance) |
| Spatial resolution | 500 m sinusoidal grid cell (463 m nominal) |
| Temporal resolution | Yearly; up to two vegetation cycles reported per year; 2001–2025 available (checked 2026-10-13) |
| Access | ORNL DAAC Land Product Subsets REST API, `https://modis.ornl.gov/rst/api/v1/MCD12Q2/subset`, **no authentication**. One request per band (max 10 years), single pixel (`kmAboveBelow=0&kmLeftRight=0`); no global download |
| Bands used | `NumCycles`; for cycles 1 and 2: `Greenup`, `MidGreenup`, `MidGreendown`, `Dormancy`, `EVI_Amplitude`, `QA_Overall` |
| Units / scaling | Dates as days since 1970-01-01; EVI2 amplitude × 0.0001; QA 0–3 = best, good, fair, poor; fill value 32767 → missing |
| Reference | Gray, Sulla-Menashe & Friedl, *User Guide to Collection 6.1 MODIS Land Cover Dynamics (MCD12Q2)*, 2022 ([PDF](https://lpdaac.usgs.gov/documents/1417/MCD12Q2_User_Guide_V61.pdf)) |

From the user guide:
- A cycle is valid if its EVI2 amplitude is at least 0.1 and at least 35 % of the three-year range.
- Phase dates are where EVI2 crosses 15 %, 50 % and 90 % of the cycle amplitude.
- A cycle belongs to the product year in which its peak falls.
- Only the two largest cycles are reported.
- Multi-cycle results "are not guaranteed to represent two distinct cropping cycles" when a pixel mixes fields.

## Method

1. **Cycle centre** = midpoint of MidGreenup and MidGreendown. The ORNL service does not offer the Peak layer, and the guide recommends the mid-greenness dates as the more stable season start/end.
2. **Season assignment.** Each cycle is placed in the FieldShift season window that contains its centre: kharif 1 Jun–31 Oct, rabi 1 Nov–30 Apr, summer 1 Apr–15 Jun. Windows overlap in April and 1–15 June; a tie goes to the window covering most of the MidGreenup–MidGreendown span.
3. **Per season and year:** *cycle*, *no cycle*, or *unclear*. A year is unclear when:
   - the cycle count is missing,
   - the matching cycle has poor QA (3), or
   - more than two cycles exist but none matched (a smaller third cycle may exist unreported).

   A rabi season Y–Y+1 is evaluated only if both product years are present.
4. **Summary (FieldShift screening rules, not agronomic thresholds):**
   - *usually green*: a cycle in more than half of the clear years;
   - *not green*: no cycle in any clear year;
   - *irregular*: otherwise;
   - *insufficient*: fewer than 3 clear years.

## Role in the recommendation

| Planned season is… | Plan check `observed_seasonal_land_use` | Effect |
|---|---|---|
| usually green | **pass** | Factor: the plan continues recent land use |
| not green | **unknown**: "adds a cropping season compared with recent land use" | Plan becomes *conditionally feasible*. Trade-off states the added crop's FAO-56 ETc as **extra crop water demand beyond the observed cropping pattern**. Shown in the Comparison View column |
| irregular / insufficient | unknown | Uncertainty note |

The check **never rejects** a plan and **does not change any score**. The composite and water scores are identical with and without MODIS data (tested), so crop water demand is not counted twice. The dataset's job is to make one specific decision visible: *does this plan add a cropping season that recent land use does not have, and what water would that season need?*

## Demonstration result (actual data)

Demo farm pixel 30.85 N, 75.70 E (rural Ludhiana district; MCD12Q1 class "Croplands" 2020–2024), product years 2016–2025, saved ORNL response `data/modis_mcd12q2_demo_farm_2016_2025.json` (retrieved 2026-10-13):

| Season | Result |
|---|---|
| Kharif | Cycle in 10 of 10 years (mid-greenup ≈ late July, mid-greendown ≈ mid-October), QA best |
| Rabi | Cycle in 9 of 9 years (mid-greenup ≈ early January, mid-greendown ≈ early April), QA best |
| Summer (zaid) | **No cycle in any of 10 years** |

With the saved 2024 NASA POWER record and an 800 mm farmer water budget (balanced priorities), the engine returns:

| Plan | Added season | Extra crop water demand | Status |
|---|---|---|---|
| Pearl millet → Rapeseed/mustard → Summer moong | summer | ≈ 477 mm | conditionally feasible |
| Cotton → Wheat → Summer moong | summer | ≈ 477 mm | conditionally feasible |
| Cotton → Wheat (2-season horizon) | none | 0 mm | unchanged by MODIS |

**User-facing decision:** the farmer sees that every three-season plan relies on a summer moong crop in a window that has been bare at this location for a decade, and that this crop needs about 477 mm of water in the hottest months. The choice is between that plan and a two-season plan that keeps the observed pattern. FieldShift does not say which is better. Summer moong is a PAU-documented diversification option, and the decision depends on the farmer's water access and priorities.

## Limitations

- Greenness is **not** yield, crop identity, crop health or soil fertility.
- The farm's own field may differ from the 500 m pixel average; small or mixed holdings blur the signal.
- At most two cycles per year are reported.
- MCD12Q2 is published about six months after the year ends, so the latest season is not available.
- Terra and Aqua are ageing satellites in drifting orbits.
- The season windows are FieldShift's regional windows; a crop sown outside them (e.g. cotton in April) can be assigned to a neighbouring window.
- The ORNL service occasionally returns HTTP 502. The client retries twice and then reports the failure. Planning continues without the comparison.

## Tests

- `tests/test_land_use_phenology.py`: fixture-based, deterministic. Covers parsing, fill values, units/scaling, QA, season assignment and overlap tie-breaks, unclear years, summary rules, client retries/errors/limits/caching, the plan check, the extra-water trade-off, no score double counting, and the demo workflow in Streamlit AppTest.
- `tests/test_modis_integration.py`: **live**, skipped unless `RUN_MODIS_INTEGRATION=1`. Passed on 2026-10-13 (46.9 s).
