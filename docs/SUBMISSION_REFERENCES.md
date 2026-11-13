# FieldShift — references for the project submission

Use this list in the official Project Submission form. It names the sources used in the repository and distinguishes active sources from optional modules. NASA Space Apps requires teams to cite all resources used in their solution, including open-source and non-NASA resources. See the [2026 Participant Terms and Conditions](https://www.spaceappschallenge.org/legal/).

## NASA and NASA-supported sources

| Resource | How FieldShift uses it | Citation / URL |
|---|---|---|
| NASA POWER Daily API | Primary live historical climate context: temperature, precipitation, radiation, humidity, and wind; exact query provenance is retained. | NASA POWER, [Daily API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) and [API getting started](https://power.larc.nasa.gov/docs/tutorials/api-getting-started/). |
| MODIS MCD12Q2 Collection 6.1 | Optional phenology comparison for recent seasonal greenness at a selected point. It does not identify crops or measure yield. | Gray, J., Sulla-Menashe, D., & Friedl, M. (2022). [MCD12Q2 Collection 6.1 User Guide](https://lpdaac.usgs.gov/documents/1417/MCD12Q2_User_Guide_V61.pdf); [ORNL DAAC subset service](https://modis.ornl.gov/rst/api/v1/MCD12Q2/subset). |
| NASA NEX-GDDP-CMIP6 | Optional, location-specific demonstration extract used only by the separate future-climate page. It is not a weather forecast. | Thrasher, B., Wang, W., Michaelis, A., et al. (2022). *NASA Global Daily Downscaled Projections, CMIP6.* *Scientific Data*, 9, 262. [https://doi.org/10.1038/s41597-022-01393-4](https://doi.org/10.1038/s41597-022-01393-4). |

## Soil, crop-calendar, and agronomic sources

| Resource | How FieldShift uses it | Citation / URL |
|---|---|---|
| ISRIC SoilGrids 2.0 | Optional modelled soil estimate; farmer or laboratory values override it. | [ISRIC SoilGrids](https://www.isric.org/explore/soilgrids); [FAQ: units](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html); [FAQ: access](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html). |
| Sacks crop-calendar archive | Historical global planting/harvest timing lookup only; not a crop-suitability result. | UW SAGE, [0.5-degree crop calendar data](https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/netcdf-0-5-degree/) and [dataset methods](https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/). |
| FAO Irrigation and Drainage Paper 56 | Crop coefficients and the documented FAO-56 water-balance method. | Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). [FAO-56](https://www.fao.org/4/x0490e/x0490e0b.htm). |
| FAO EcoCrop | Crop thermal context in the source-linked catalogue. | [FAO EcoCrop Database](https://ecocrop.apps.fao.org/). |
| Punjab Agricultural University | Punjab crop calendar, crop characteristics, documented rotation examples, and local constraints. | [PAU Kharif 2026 package](https://pau.edu/content/ccil/pf/pp_kharif.pdf); [PAU Rabi 2026 package](https://pau.edu/content/ccil/pf/pp_rabi.pdf). |
| Government of India crop-water annexure | Catalogue water-requirement context. | [Parliament Question Annexure AS110](https://sansad.in/getFile/annex/256/AS110.pdf?source=pqars). |
| CACP and PAU farm-management sources | Indicative economic benchmarks only; not farm prices or profit predictions. | [CACP](https://cacp.dacnet.nic.in/); [Punjab Agricultural University](https://pau.edu/). |

## Software used in the project

- Python — [python.org](https://www.python.org/)
- Streamlit — [streamlit.io](https://streamlit.io/)
- pandas — [pandas.pydata.org](https://pandas.pydata.org/)
- NumPy — [numpy.org](https://numpy.org/)
- Plotly — [plotly.com/python](https://plotly.com/python/)
- pytest — [pytest.org](https://pytest.org/)

## Scope note for judges

NASA POWER is the primary live data path. MODIS MCD12Q2 and the supplied NEX-GDDP-CMIP6 extract are optional, separate workflows. SoilGrids is a labelled estimate. SMAP, GPM, GRACE, ECOSTRESS, Landsat, SRTM, FIRMS, and GEDI are **not** active location-specific rotation inputs in this release; do not list them as implemented data integrations.

For the detailed source schema, limitations, dates, units, and access conditions, see `docs/DATA_SOURCES.md`.
