# Competition readiness: lessons applied to FieldShift

**Reviewed:** 2026-11-13  
**Purpose:** turn the official challenge into a focused, demonstrable project rather than a catalogue of unverified features.

## What recent winners show

NASA reported that the 2025 Global Winners were selected from more than 11,500 project submissions. The official winner descriptions consistently connect a clear audience, a concrete decision, and a visible product demonstration:

- **SpaceGenes+** made a complex research question usable through an interactive dashboard for researchers and mission planners.
- **SkySense (Twisters)** presented a web app that turns Earth-observation data into personalized weather-risk windows.
- **QUEÑARIS** connected a local water problem to an observable environmental intervention.
- **HerCode Space** made NASA science understandable through a coherent story and visuals.
- **Zumorroda-X** translated agricultural environmental challenges into an approachable, interactive experience.

These are observations from the [official 2025 NASA winners announcement](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/), not a guaranteed formula for winning. The official 2026 challenge asks specifically for a decision-support tool that combines NASA Earth observations, local soil information, crop characteristics, and farmer priorities to help explore rotation strategies. See the [2026 Field Shift brief](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/).

## FieldShift’s judge-ready story

**One user:** a farmer or extension worker deciding among several next-season crop sequences.  
**One decision:** which documented rotation alternatives remain worth discussing after known water, season, soil, crop-family, and climate constraints are inspected.  
**One proof:** a live NASA POWER request is displayed with the exact location, date range, variables, units, source URL, and data gaps; the same climate context feeds the visible water and temperature methods.  
**One honest boundary:** a score is a preference-weighted comparison, not a probability of yield, profit, soil improvement, or success.

## Improvements made from this review

| Competition strength | FieldShift implementation | Boundary kept visible |
|---|---|---|
| Clear local impact | Punjab is the principal demonstration region, with source-linked crop rules and calendars. | Other locations receive climate exploration unless a supported regional catalogue applies. |
| Real NASA data | NASA POWER is retrieved live and shown with provenance. | It is a gridded historical climate product, not a field instrument or forecast. |
| Useful interaction | The workflow collects farmer inputs, lets priorities change rankings, compares current and generated rotations, and runs hypothetical stress tests. | Unknown inputs stay unknown and hard rule failures cannot be overcome by a high score. |
| Explainable science | Rule checks, metric methods, source URLs, missing-data notes, and scenario transforms are inspectable. | Optional sources are never displayed as if they were live inputs when they are not. |
| Presentation | A globe supports location selection, a guided workflow keeps the next action obvious, and the export is printable. | Visual polish does not substitute for field validation. |

## Demonstration route for judges

1. Open **Home** and state the decision question in one sentence.
2. Load the clearly labelled Ludhiana example or enter a farm profile.
3. Open **Climate Insights**, retrieve NASA POWER, and point out the exact request URL and units.
4. Open **Rotation options** and expand a plan’s feasibility checks, metric methods, source links, and uncertainty notes.
5. Change one farmer priority, then show the comparison view to demonstrate that the engine uses the edited weights.
6. Run a hypothetical stress test and say clearly that it is not a forecast.
7. Finish on **Data and methods** and state what FieldShift does not know or predict.

## What would strengthen a later version, but is not claimed today

- Review by a qualified agronomist for each regional catalogue.
- Observed usability sessions with farmers or extension workers.
- Field trial data to evaluate whether the recommended comparison improves outcomes.
- Additional NASA sources only after their live retrieval, provenance, spatial limitations, and decision role are implemented and tested.

## Submission positioning

Describe FieldShift as an **explainable prototype with a live NASA POWER data path**, not as a finished advisory service. That positioning is stronger because a judge can reproduce the shown decision path and inspect the limits.
