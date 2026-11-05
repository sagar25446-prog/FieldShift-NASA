# FieldShift project status and challenge fit

**Reviewed:** 2026-11-05
**Challenge:** [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)

## Executive summary

The official brief asks for a decision-support tool combining NASA Earth observations, local soil information, crop characteristics and farmer priorities so farmers can explore crop-rotation strategies that may protect soil, conserve water and adapt to changing conditions. FieldShift has a real NASA POWER daily climate client, farmer-entered soil and water profile, a documented crop catalogue, and a deterministic rotation engine for four configured pilot regions. It therefore addresses the core idea.

It is **not yet a validated global farm recommendation product**. Anywhere on Earth, the user can inspect NASA POWER climate context and, in some cells, a historical crop calendar. Those global calendar comparisons check dates only; they do not invoke the regional agronomy engine. The working rotation planner applies only when a supported pilot-region catalogue and rules are selected. Modelled climate is not a field observation; unknown soil values remain uncertain. No agronomist or representative farmer validation has been recorded in this repository.

## Fit against the challenge

| Challenge element | What the project currently does | Status and gap |
|---|---|---|
| NASA Earth observations | Retrieves NASA POWER daily climate and derives summaries; optional modules cover other datasets and projections. | **Core demonstrated.** NASA POWER is the dependable primary integration. Other dataset availability varies by feature and should not be described as one fused, always-active six-mission feed. |
| Local soil information | Accepts farmer/lab values and can request SoilGrids estimates. | **Implemented with limits.** A gridded soil estimate is not a lab result. Field-level samples, test dates, and adviser review are still needed for real decisions. |
| Crop characteristics | Structured, source-linked catalogues and region-specific crop rules exist. | **Implemented for supported regions.** Crop seasons and local evidence still need expert confirmation; the global Sacks calendar is historical timing evidence only. |
| Farmer priorities | Editable weights are passed to the deterministic engine. | **Implemented.** Weights change rankings only where the compared plans have different available metric scores. |
| Explore crop rotations | Engine generates and explains multiple plans under documented rules. | **Implemented for pilot catalogues.** Unsupported coordinates cannot receive an agronomic rotation recommendation. |
| Protect soil / conserve water | Separate water, soil-related and diversity metrics, scenarios and simplified state modelling are present. | **Exploratory.** Scores and soil-state calculations are model outputs, not proof of future soil or water outcomes. Calibration and field trials are absent. |
| Adapt to changing conditions | Historical summaries, hypothetical stress tests, and optional future-climate comparison exist. | **Partly implemented.** Stress tests are assumptions, and climate projections are scenarios, not farm forecasts. Coverage and interpretation must be reviewed for each use. |
| Usable by farmers | Streamlit app has an interactive globe, pilot map, form-based workflow, charts, and exports. | **Prototype.** Usability, accessibility, translations, mobile browser performance, and farmer comprehension require observed user testing. |

## Important documentation corrections

- Some older README and methods sections claim multiple NASA feeds are all fused into every recommendation. That overstates what a user can currently retrieve and what the engine consumes.
- Statements such as “exactly how it drives ranking,” “fully operational,” “verified,” “every crop parameter,” and “tested with farmers” should be retained only where the repository contains a reproducible calculation, exact source, and test or review record.
- Challenge participation is not certification or NASA endorsement. FieldShift is a team prototype.
- The current app can explore arbitrary coordinates, but should say clearly when it has climate-only context, calendar timing only, or a regional rule-based plan.

## What is done well

NASA POWER is retrieved through a dedicated client with units, request provenance, missing-data handling and cached requests. Agronomic decision code is kept out of Streamlit. The crop catalogue and rule sources are documented, farmer inputs can remain unknown, plans show component metrics and explanations, and stress scenarios are labelled as hypothetical. The global crop-calendar file preserves empty cells rather than extrapolating observations.

## What remains before farmer-facing use

1. A qualified agronomist should review crop seasons, crop-family rules, water assumptions, thermal thresholds and soil-state parameters for each pilot region.
2. Farmers and extension advisers should complete observed task testing, including entry of soil-card results, understanding unknown values, and interpreting the plans.
3. Maintain a claim-to-code-and-source check so UI copy, README, challenge mapping and actual data availability agree.
4. Re-run automated and live integration checks on a clean deployment environment and capture the result with a date. A Git push alone does not prove the Streamlit app rebuilt successfully.
5. Keep the worldwide experience useful and honest: climate exploration works globally; crop timing is shown only where the historical atlas has a record; agronomic rotation rules remain region-limited.

## Improvement made after this review

The home page now distinguishes arbitrary-location climate/calendar exploration from a supported pilot-region rotation planner. Its map identifies itself as a geographic illustration, and its location report labels NASA POWER as gridded climate context and the calendar atlas as historical regional timing. See [Earth explorer methods](EARTH_EXPLORER.md).
