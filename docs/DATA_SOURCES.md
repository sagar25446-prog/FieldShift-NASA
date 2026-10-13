# Phase 2 data-source plan

## Demonstration region

**Ludhiana district, Punjab, India** is the FieldShift demonstration region. It is a planning boundary, not a claim that every district field is alike. It was selected because Punjab Agricultural University (PAU), in Ludhiana, publishes current Punjab-specific crop guidance and rotation examples. A future user must provide a field boundary or point; FieldShift will not assume a default farm coordinate.

## Minimum viable data

| Source | Planned use | Classification | Status |
| --- | --- | --- | --- |
| [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) | Daily climate context for an entered location | Gridded NASA meteorological data, not a farm measurement | **Integrated for historical point retrieval; schema/provenance in `NASA_POWER_DATA.md`** |
| Farmer input | Field location, history, irrigation, planting window and priorities | Farmer-provided | Required |
| Soil Health Card/accredited lab report | pH, EC, organic carbon, nutrients with date/depth/method | Measured soil data | Required for a soil rule |
| PAU 2026 packages | Catalogue, crop windows and local rotation examples | Regional extension/research guidance | Catalogue evidence |

The POWER Daily API provides analysis-ready daily solar and meteorological data. The implemented historical point client requests `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, and `ALLSKY_SFC_SW_DWN`, preserves response metadata/units, explicitly requests UTC, and caches exact requests for six hours. `RH2M` and `WS2M` remain candidates for a later justified indicator. POWER warns against repeatedly requesting the same location. These parameters are not crop-suitability thresholds.

## Optional indicators — not first-version dependencies

| Source | Later use | Classification and limitation |
| --- | --- | --- |
| [GPM IMERG Final](https://daac.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary?keywords=IMERGHH) | Rainfall timing and anomaly context | Satellite precipitation estimate; 0.1° Version 07 product; not a farm gauge |
| [MODIS MOD13Q1 NDVI/EVI](https://modis.gsfc.nasa.gov/data/dataprod/mod13.php) | Vegetation-condition context | 16-day, 250 m remote-sensing index; not crop identity, yield or soil health |
| [NASA–USDA Global Soil Moisture](https://earth.gsfc.nasa.gov/hydro/data/nasa-usda-global-soil-moisture-data) | Broad moisture context | 0.25° modelled-assimilated estimate; never a soil-test replacement |

NASA–USDA combines SMAP/SMOS observations with a modified two-layer Palmer model. GPM and this soil-moisture data are too coarse to state a specific field condition, so they are explicitly excluded from the first implementation.

## Soil policy

The preferred evidence is a field-specific laboratory report including date, depth, method/lab and units. India's [Soil Health Card FAQ](https://soilhealth.dac.gov.in/files/FAQ_Final_English.pdf) describes a farmer report based on laboratory-tested samples; PAU also provides [Soil & Water Testing](https://pauwp.pau.edu/testing/). A satellite layer, map or district average must never overwrite a laboratory result. If no valid report exists, a soil-dependent check must state **unknown**.

## Crop references

- [PAU Kharif 2026 package](https://pau.edu/content/ccil/pf/pp_kharif.pdf)
- [PAU Rabi 2026 package](https://pau.edu/content/ccil/pf/pp_rabi.pdf)
- [Government of India crop/irrigation water-requirement annexure](https://sansad.in/getFile/annex/256/AS110.pdf?source=pqars)

Every future input needs source/product ID, retrieval time, unit, spatial/temporal resolution, geographic selection, QA/missing-data flag and transformation history. Economics is not planned yet: costs, prices, returns and profitability remain unavailable.
