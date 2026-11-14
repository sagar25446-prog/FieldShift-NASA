# FieldShift — ready-to-paste Space Apps project form content

Use the current Project tab on the official team page. The 2026 guide requires English project fields, a public project-demo link, a public final-project link, a description of any Super Intelligence (SI) use, and specific NASA data and reference information.

Do not add results that are not visible in the current app. The text below describes the prototype accurately and does not claim farmer validation, NASA endorsement, yield prediction, profit prediction, or guaranteed soil improvement.

## Project Name

FieldShift

## High-Level Project Summary

FieldShift helps farmers and extension workers explore crop rotations under changing climate and water conditions. A user chooses a farm location, retrieves historical NASA POWER climate context, adds known soil, irrigation, and crop-history information, and sets priorities. The app compares source-linked rotation alternatives, shows hard constraints and trade-offs, and keeps missing information visible. It supports a better local planning conversation; the farmer and local advisers retain the final decision.

## Link to Project Demo

Paste **one public link** after uploading either of these completed assets:

- Preferred: the 30-second video recorded with `docs/DEMO_VIDEO_SCRIPT.md`.
- Alternative: the public seven-slide deck: https://github.com/sagar25446-prog/Nasa-Hacakathon/blob/main/submission/FieldShift_Project_Demo_Deck.pptx

The deck link above is public and available without a GitHub login. Before submitting, replace the team-roster line on slide 1 with the official team name and registered member names, then publish the revised deck. The link must open without a password, permission request, account, or registration.

## Link to Final Project

https://fieldshift-nasa.streamlit.app/

Optional supporting repository link, if the form allows an additional link:

https://github.com/sagar25446-prog/Nasa-Hacakathon

## Detailed Project Description

Farmers must choose crop sequences while rainfall, heat, water availability, soil constraints, and previous crops all matter. A simple recommendation can hide uncertainty or suggest false precision.

FieldShift is an explainable crop-rotation decision-support prototype. The user selects a farm location and retrieves historical daily NASA POWER climate context. The application keeps the NASA request URL, date range, parameters, units, retrieval time, and missing-observation information. It then accepts farmer-provided soil and irrigation information, previous crops, and priority weights. Unknown values remain unknown instead of becoming favourable assumptions.

For the supported pilot catalogues, a deterministic rule engine searches multiple multi-season crop sequences. It excludes sequences that violate documented hard rotation rules and explains every result through separate water, historical-climate, soil-related, diversity, and available economic-comparison metrics. It also shows the farmer's weights, source links, feasibility checks, trade-offs, and uncertainty warnings. The current rotation can be compared with alternatives under the same inputs.

The app includes transparent dry, hot, and irrigation-reduction stress tests. These are hypothetical changes to historical conditions, not weather or climate forecasts. Optional MODIS, SoilGrids, and NEX-GDDP-CMIP6 screens retain their own provenance and limits; they do not silently change the central plan.

FieldShift does not measure soil chemistry from space, predict crop yield or profit, or guarantee soil improvement. It is designed to make Earth-observation context and local uncertainty understandable before a farmer consults regional expertise and makes the final choice.

## Use of Super Intelligence (SI)

**Answer: Yes.** OpenAI Codex assisted the team with coding, test execution, documentation editing, and interface refinement. The deployed FieldShift recommendation path does not call a generative-AI model. Crop-rotation comparison, feasibility checks, scoring, and scenario transforms use deterministic, source-linked code. The team reviewed the submitted material and remains responsible for every claim.

Before submitting, add any other SI tools that any team member used. If the team uses AI-generated images, narration, music, video, or text outside this repository, follow the guide's required acknowledgement or watermark rules.

## NASA Data

**Primary active NASA source: NASA POWER Daily API**

FieldShift requests historical daily climate context for the selected latitude, longitude, and date range through the NASA POWER Daily API. The active request includes precipitation, air temperature, solar radiation, humidity, and wind parameters. The app displays the exact query URL, time range, parameter names, units, retrieval time, and missing-observation information. These gridded historical values provide climate context; they are not direct field measurements or forecasts.

NASA POWER documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/

Additional NASA resources appear only in separately labelled optional workflows:

- MODIS MCD12Q2 Collection 6.1 for historical phenology context.
- NASA NEX-GDDP-CMIP6 demonstration extract for future-climate comparison, clearly labelled as a projection rather than a forecast.

## Space Agency Partner Data and Other References

Paste the source list in `docs/SUBMISSION_REFERENCES.md`. It includes NASA POWER, optional NASA sources, FAO-56, FAO EcoCrop, SoilGrids, the Sacks crop-calendar archive, Punjab Agricultural University materials, Government of India crop-water information, CACP/PAU economics context, and the project software.

## Final accuracy check

- Do not call optional sources live rotation inputs unless they are visibly active in the submitted session.
- Do not list SMAP, GPM, GRACE, ECOSTRESS, Landsat, SRTM, FIRMS, or GEDI as implemented rotation inputs in this release.
- Do not claim NASA endorsement or use NASA logos or branding elements.
- Use the exact public video/deck link that judges can open without access requests.
