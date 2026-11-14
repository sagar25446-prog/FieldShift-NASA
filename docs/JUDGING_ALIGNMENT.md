# FieldShift — judging-criteria evidence map

FieldShift is designed for the five published Space Apps judging criteria: **Impact, Creativity, Validity, Relevance, and Presentation**. This is an evidence map, not a prediction of a score or an award.

## Impact

**Judge question:** Does the project address a meaningful problem and help people at useful scale?

**FieldShift evidence**

- The central problem is a real planning burden: farmers must balance changing rainfall and temperature with water limits, soil conditions, and crop history.
- The tool gives farmers and extension workers a transparent way to compare several crop sequences rather than a single opaque answer.
- The same workflow begins at a map point, but rotation guidance remains clearly scoped to documented pilot catalogues. This prevents a broad-scale claim from hiding weak local evidence.

**Show in the demo:** Select the Punjab pilot, show the farmer profile and the comparison page, then state that the tool supports a local decision rather than replacing local expertise.

## Creativity

**Judge question:** Is the approach genuinely thoughtful rather than a generic dashboard or score?

**FieldShift evidence**

- The application joins historical Earth-observation climate context, farmer inputs, crop-family rules, and editable priorities in one traceable flow.
- Unknown soil information stays unknown. It can lower confidence or prompt a check, but it does not silently remove a crop.
- The tool compares the current rotation with alternatives and keeps hard-rule failures visible.
- Dry, hot, and reduced-irrigation views are transparent hypothetical stress tests, not disguised forecasts.

**Show in the demo:** Change a farmer priority, reveal a plan's feasibility checks and trade-offs, and point out the stress-test label.

## Validity

**Judge question:** Is the science and technology credible, and does the working prototype do what it says?

**FieldShift evidence**

- NASA POWER requests use the public official Daily API. The app retains the exact URL, parameter names, units, dates, retrieval time, and missing-observation information.
- The rotation engine is deterministic and source-linked. It rejects known hard-constraint violations and explains scores separately rather than turning a composite into a probability.
- The repository's documented verification includes saved-response tests, live API integration coverage, and full test-suite results in `docs/TEST_REPORT.md`.
- The app explicitly distinguishes retrieved values, calculations, farmer inputs, modelled estimates, assumptions, and unknowns.

**Show in the demo:** Open NASA POWER provenance and one plan's rule evidence. Never call gridded climate context a field measurement, a forecast, or a yield prediction.

## Relevance

**Judge question:** Does the project directly answer Field Shift: Adapting Farms with NASA Data, and can a non-specialist use it?

**FieldShift evidence**

- NASA POWER is part of the active decision workflow, not a decorative citation.
- The farm profile collects exactly the local inputs named by the challenge: soil and water context, crop history, and farmer priorities.
- The engine produces feasible multi-season rotations and explains water, climate, soil-related, diversity, and available economic considerations separately.
- The interface uses plain-language labels, visible units, help text, loading and error states, and a decision-support warning.

**Show in the demo:** Move in order from location to NASA climate context, farm inputs, priorities, and rotation comparison.

## Presentation

**Judge question:** Does the submission tell a clear, engaging story about the problem, solution, and why it matters?

**FieldShift evidence**

- `docs/DEMO_VIDEO_SCRIPT.md` uses the official 30-second structure: people, problem, method, impact, and boundary.
- `submission/FieldShift_Project_Demo_Deck.pptx` provides a seven-slide alternative with one clear idea per slide.
- `docs/PROJECT_SUBMISSION_CONTENT.md` provides polished, specific English copy for every project-page field.
- `docs/SUBMISSION_REFERENCES.md` makes all core data and software sources traceable.

**Show in the demo:** Keep the narrative simple: climate context, farmer context, explainable comparison, final farmer choice.

## Lessons applied from recent winners

NASA's 2025 winners covered very different subjects, including a scientific dashboard (SpaceGenes+), a local water-resilience solution (QUEÑARIS), and an agricultural learning experience (Zumorroda-X). Their projects were not copied. FieldShift applies the useful submission patterns: one clear user decision, data that changes the experience, an understandable interactive prototype, and claims that match the available evidence.

Official winner descriptions: [NASA Announces 2025 International Space Apps Challenge Global Winners](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).

## Award positioning

FieldShift's strongest honest fit is **Best Use of Data** and **Local Impact**. The project makes NASA climate data understandable inside a farmer workflow, while keeping local crop and soil limits explicit. It can also credibly seek **Best Use of Science** only by presenting its documented assumptions, sources, and limitations accurately. Do not claim that an award fit guarantees selection.

## Claims that must stay out of the submission

- “FieldShift predicts yield, profit, or soil improvement.”
- “NASA measures this field's soil pH, NPK, organic carbon, or yield.”
- “The scenario view forecasts the coming season.”
- “The app has been agronomist-validated” unless the team adds truthful evidence of that review.
- “FieldShift works as a locally validated planner everywhere on Earth.”
- Any NASA endorsement claim or use of NASA logos/branding elements.
