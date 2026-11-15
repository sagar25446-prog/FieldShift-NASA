# FieldShift rotation engine

FieldShift generates candidate crop sequences with a deterministic search of the selected pilot catalogue. A candidate is excluded when a **known hard rule** fails. Missing measurements produce an unknown or conditional result, not an invented measurement. The app shows the checks, source links, available scores, priority weights and trade-offs for each returned plan.

## Regional scope

The supported rotation catalogues cover Punjab, the US Corn Belt pilot in Iowa, Andalusia and a semi-arid India pilot. Elsewhere, FieldShift can show NASA POWER climate history and available historical crop-calendar timing; it does not extrapolate a locally validated rotation recommendation to every point on Earth. See [crop provenance](../data/README.md) and [agronomic assumptions](AGRONOMIC_ASSUMPTIONS.md).

## Checks and scores

| Component | Current method | Interpretation |
|---|---|---|
| Crop season and rotation rules | Catalogue seasons, previous-crop information and documented compatibility edges | A known violation excludes a sequence. An undocumented edge is unsupported evidence, not proof that the sequence is impossible. |
| Water suitability | Documented crop requirements and, when NASA POWER data are sufficient, a FAO-56-based climate water-balance estimate | An estimated irrigation deficit compared with the farmer's stated water budget; not measured groundwater withdrawal. |
| Climate suitability | Documented crop thermal ranges compared with historical NASA POWER temperatures | Historical temperature fit, not a yield or future-weather prediction. |
| Soil-related potential | Known drainage, alkalinity and other catalogue constraints, using farmer/laboratory data first | Unknown soil measurements remain unknown; a modelled SoilGrids estimate is labelled separately. |
| Rotation diversity | Crop-family differences and other documented sequence characteristics | A structural comparison, not a measured soil-health gain. |
| Economic potential | Unavailable | Complete crop-level realised prices, yields and costs with precise regional sources have not been verified. Its ranking weight is zero. |

Available component scores are scaled from 0 to 1 and combined using the farmer's normalized weights. The composite is a preference-weighted comparison among supported alternatives. It is **not** a probability of success. The engine cannot override a failed hard rule with a high score. See [water-balance method](WATER_BALANCE_METHODOLOGY.md), [climate-suitability method](CLIMATE_SUITABILITY_METHODOLOGY.md) and [uncertainty handling](SCENARIOS_AND_UNCERTAINTY.md).

## Boundaries

NASA POWER is gridded historical climate context. It does not measure field soil chemistry, irrigation withdrawals or crop yield. Dry and hot scenario changes are hypothetical stress tests; the separate NEX-GDDP-CMIP6 page shows model projections only where the supplied extract applies.

Numerical groundwater-savings, gross-margin, soil-carbon and nitrogen-gain claims need locally sourced inputs and validation. The current farmer-facing recommendations do not show those as established outcomes. Research modules retained in the repository are not active recommendation inputs. Review [known limitations](KNOWN_LIMITATIONS.md) before presenting a plan to a farmer.
