# FieldShift implementation plan

## Purpose

Build an explainable decision-support prototype to compare feasible multi-season crop rotations using verified NASA Earth observations, local soil information, crop characteristics, and farmer priorities. It will not promise yield or soil outcomes.

## Phase 1 — Foundation (this delivery)

Create the project skeleton, documentation, dependency setup, safe configuration practices, and local Streamlit welcome screen.

**Acceptance criteria**

- Data access, agronomic rules, recommendation logic, and UI are separate modules.
- The app starts locally and identifies itself as a decision-support prototype.
- No fabricated or silently substituted NASA, soil, or crop data is shown.
- Setup, assumptions, architecture, data-source policy, and tests are documented.

## Phase 2 — Data contracts and verified source integration (research catalogue completed)

Confirm publicly accessible NASA and soil sources; document fields, units, coverage, refresh behaviour, and attribution. Implement validated retrieval and provenance reporting.

**Acceptance criteria**

- Every displayed observation identifies its source, retrieval time, unit, and coverage.
- Missing, stale, or invalid data produces a clear state rather than a substitute value.
- Retrieval and transformation tests use recorded, clearly labelled fixtures where needed.

## Phase 3 — NASA POWER historical climate integration (completed)

Implement a validated, cached NASA POWER Daily point client; preserve source metadata and distinguish retrieved daily values from historical derived indicators.

**Acceptance criteria**

- Users can request a location and historical date range without an API key.
- The application displays retrieved values, units, source URL, date range, missing coverage and provenance.
- Offline fixtures validate parsing/error paths; an opt-in live integration test validates the public endpoint.
- Historical summaries are never presented as forecasts or field measurements.

## Phase 4 — Agronomic inputs and transparent feasibility rules (initial engine implemented; human review pending)

Define supported crops, rotations, constraints, and farmer-priority inputs with a domain reviewer. Implement deterministic feasibility checks with explanations.

**Acceptance criteria**

- Each accepted or rejected rotation lists the rule and input that caused the result.
- Rules, units, defaults, assumptions, and limitations are documented and tested.
- The app distinguishes missing farmer input from an unfavourable condition.

## Phase 5 — Rotation comparison experience (completed)

Build the farmer-facing workflow, comparison views, uncertainty messaging, and accessible visualizations.

**Acceptance criteria**

- A user can enter field context and priorities, then compare feasible rotations.
- Charts and text use labelled units, source context, and plain-language explanations.
- Loading, validation, empty, and error states are understandable to a non-technical user.
- The interface uses the real NASA POWER client and deterministic rotation engine; it contains no hard-coded recommendations or synthetic climate values.
- Changing documented farmer priorities updates the engine weights and can change the ranked alternatives when their available component scores differ.

## Phase 6 — Scenario comparison and uncertainty handling (completed)

Add deterministic historical, dry, hotter-than-baseline, and optional reduced-water-budget stress tests. Keep data-coverage, model, and scenario uncertainty distinct; use conservative Pareto labels without hiding alternatives.

**Acceptance criteria**

- Every hypothetical scenario states its exact transformation and is never labelled as a forecast.
- A baseline sequence remains visible if a known hard rule fails under a stress test.
- Missing inputs and incomplete source evidence are explained without an invented confidence percentage.
- Pareto labels require fully comparable evidence and preserve non-dominated alternatives.

## Phase 7 — Validation, testing, and demo readiness

Validate calculations and messaging with advisors and representative users; prepare the challenge demo and reproducibility materials.

**Acceptance criteria**

- Unit, integration, and manual test results are recorded.
- Limitations and non-guarantee language are visible in the product and demo.
- A clean setup can run the app and checks using the README instructions.
