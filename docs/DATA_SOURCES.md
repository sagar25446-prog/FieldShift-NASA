# Data Sources

## Demonstration Region

**Ludhiana district, Punjab, India** — selected because Punjab Agricultural University (PAU), in Ludhiana, publishes current Punjab-specific crop guidance and rotation examples.

---

## Operational Data Sources

| Source | Use in FieldShift | Classification | Status |
|---|---|---|---|
| [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Historical daily climate context (T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN) | Gridded NASA meteorological data (~0.5°), not a field measurement | ✅ Integrated |
| Farmer input | Location, soil conditions, water budget, irrigation, previous crop, blocked crops, priorities | Farmer-provided | ✅ Required input |
| Soil Health Card / lab report | pH, EC, organic carbon, waterlogging, drainage | Measured soil data | ✅ Optional (unknown if absent) |
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

## Optional Future Sources (Not Implemented)

| Source | Later use | Limitation |
|---|---|---|
| [GPM IMERG Final](https://daac.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary) | Higher-resolution rainfall context | 0.1° satellite estimate; not a farm gauge |
| [MODIS MOD13Q1](https://modis.gsfc.nasa.gov/data/dataprod/mod13.php) | Vegetation condition context | 16-day, 250 m; not crop identity or yield |
| [NASA–USDA Global Soil Moisture](https://earth.gsfc.nasa.gov/hydro/data/nasa-usda-global-soil-moisture-data) | Broad moisture context | 0.25° modelled; never a soil-test replacement |

These are excluded from the first implementation because they are too coarse for field-level statements.

## Soil Policy

- Preferred evidence: field-specific laboratory report with date, depth, method, and units
- India's [Soil Health Card](https://soilhealth.dac.gov.in/files/FAQ_Final_English.pdf) program provides farmer reports based on lab-tested samples
- A satellite layer, map, or district average **never overwrites** a laboratory result
- If no valid report exists, soil-dependent checks state **unknown**
- No soil values are fabricated or estimated from remote sensing
