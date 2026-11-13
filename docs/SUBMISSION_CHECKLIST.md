# FieldShift — Submission checklist

**Challenge:** [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)

**Repository:** https://github.com/sagar25446-prog/Nasa-Hacakathon

**Live application:** https://fieldshift-nasa.streamlit.app/

This is a submission aid, not a claim that a third-party review has occurred.

## What FieldShift can demonstrate

- A farmer enters a location, known soil constraints, an irrigation budget, previous crops, and priorities.
- The app retrieves historical daily climate context from the public NASA POWER API and retains its request URL, dates, units, missing-value information, and retrieval time.
- A deterministic, source-linked engine compares multiple crop-rotation sequences for the supported pilot catalogues.
- Every plan shows hard-rule checks, component scores, trade-offs, uncertainty notes, and source URLs.
- Hypothetical dry, hot, and irrigation-reduction stress tests are explicitly labelled as stress tests, not forecasts.
- The app does **not** claim to measure soil chemistry from space, forecast weather, predict yield or profit, or guarantee soil improvement.

## Before submitting

- [ ] Register for the 2026 event and select a Local or Universal Event.
- [ ] Confirm all team members appear on the official team page.
- [ ] Run the test suite and record the actual dated result in `docs/TEST_REPORT.md`.
- [ ] Open the public app and complete the demo path in `docs/DEMO_VIDEO_SCRIPT.md`.
- [ ] Confirm the live app has rebuilt from the intended `main` commit.
- [ ] Record the format required by the current official guide. A 30-second submission cut and 90-second pitch are ready in `docs/DEMO_VIDEO_SCRIPT.md`.
- [ ] Check every link in the project description, repository, and live demo.
- [ ] Paste the complete cited-source list from `docs/SUBMISSION_REFERENCES.md`.
- [ ] If the form asks about AI use, paste the factual statement from `docs/AI_USE_DISCLOSURE.md` after adding any tools used by other team members.
- [ ] Submit through the **Project** tab on the official Team page.

The 2026 event page states that project submission opens at 9:00 AM on November 14 and closes at 11:59 PM local time on November 15, 2026. Confirm the displayed time zone and required fields on the official page immediately before submitting.

The ready-to-paste project summary, NASA-data description, and links are in `docs/PROJECT_SUBMISSION_CONTENT.md`.

## Project description draft

**FieldShift** is an explainable crop-rotation exploration tool for farmers and extension workers. It combines farmer-provided soil and water information, a source-linked crop catalogue, farmer priorities, and historical NASA POWER climate data. It generates several documented rotation alternatives, checks known hard constraints, shows water, climate, soil-related, diversity, and available economic comparison metrics separately, and makes uncertainty visible rather than filling gaps with invented values. Farmers retain the final decision and should verify all plans with local agronomic advice.

## Links to include

- Challenge: https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/
- Repository: https://github.com/sagar25446-prog/Nasa-Hacakathon
- Live demo: https://fieldshift-nasa.streamlit.app/
- Methods and limits: `docs/DATA_SOURCES.md`, `docs/ROTATION_ENGINE.md`, `docs/SCENARIOS_AND_UNCERTAINTY.md`, and `docs/KNOWN_LIMITATIONS.md`
