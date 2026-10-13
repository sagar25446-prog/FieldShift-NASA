# FieldShift — Submission Checklist

**Challenge:** Field Shift: Adapting Farms with NASA Data  
**Team repository:** https://github.com/sagar25446-prog/FieldShift-NASA  
**Live demo:** https://fieldshift-nasa.streamlit.app *(verify after deployment)*

---

## Pre-Submission Verification

### Code & Deployment
- [x] All 89 automated tests pass (`python -m pytest`)
- [x] Application starts locally (`streamlit run app.py`)
- [x] No hardcoded secrets, API keys, or credentials in source code
- [x] `.env` and secrets files listed in `.gitignore`
- [x] `requirements.txt` lists all dependencies
- [x] `.streamlit/config.toml` present for deployment
- [x] Code pushed to GitHub (`main` branch)
- [ ] **Deploy to Streamlit Cloud** (manual step — see instructions below)
- [ ] **Verify public URL loads and completes full workflow**

### Documentation
- [x] `README.md` — project overview, features, setup, tests
- [x] `docs/CHALLENGE_REQUIREMENTS.md` — official challenge text mapped to features
- [x] `docs/DATA_SOURCES.md` — all data sources with provenance
- [x] `docs/AGRONOMIC_ASSUMPTIONS.md` — evidence boundaries and expert review items
- [x] `docs/KNOWN_LIMITATIONS.md` — honest disclosure of all limitations
- [x] `docs/TEST_REPORT.md` — automated and manual test results
- [x] `docs/NASA_POWER_DATA.md` — API parameters, units, quality handling
- [x] `docs/ROTATION_ENGINE.md` — scoring, rules, safeguards
- [x] `docs/SCENARIOS_AND_UNCERTAINTY.md` — scenario definitions, uncertainty categories
- [x] `docs/ARCHITECTURE.md` — module architecture
- [x] `data/README.md` — crop catalogue schema

### Scientific Integrity
- [x] No yield, profit, or soil improvement predictions
- [x] No fake confidence percentages
- [x] All scenarios labelled "hypothetical stress test"
- [x] Soil-state model has calibration disclaimers
- [x] Missing data remains unknown (never fabricated)
- [x] Every score method is documented
- [x] Source URLs provided for all catalogue evidence

---

## Streamlit Cloud Deployment Steps

1. Go to **https://share.streamlit.io**
2. Sign in with your **GitHub account** (`sagar25446-prog`)
3. Click **"New app"**
4. Select:
   - **Repository:** `sagar25446-prog/FieldShift-NASA`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Deploy!"**
6. Wait for build to complete (usually 2–5 minutes)
7. Your app will be live at: `https://fieldshift-nasa.streamlit.app` (or similar)
8. **Test the full workflow** on the public URL

---

## Submission Portal (Verify at submission time)

> ⚠️ Check the actual submission form at https://www.spaceappschallenge.org/2026/ for exact fields and requirements. The following is based on the challenge page structure.

### Likely Required Fields
- [ ] **Project title:** FieldShift
- [ ] **Challenge:** Field Shift: Adapting Farms with NASA Data
- [ ] **Project description:** (see draft below)
- [ ] **GitHub link:** https://github.com/sagar25446-prog/FieldShift-NASA
- [ ] **Demo link:** https://fieldshift-nasa.streamlit.app
- [ ] **Team members:** Add all team members
- [ ] **NASA data used:** NASA POWER Daily API (T2M, PRECTOTCORR, etc.)
- [ ] **Tools/technologies:** Python, Streamlit, pandas, NumPy, Plotly

### Check If Required
- [ ] **Demo video** — Record if the form asks for one (90-second script below)
- [ ] **Slide deck** — Prepare if required
- [ ] **Word/character limits** — Adjust descriptions to fit

---

## Draft Project Description

**FieldShift** is a transparent, farmer-friendly decision-support tool for exploring crop rotation strategies using NASA Earth observation data. Built for smallholder farmers in Punjab, India, it combines:

- **NASA POWER Daily API** data (temperature, precipitation, solar radiation) to provide real historical climate context for any location
- **Farmer-provided soil and water information** — pH, texture, waterlogging, irrigation availability, and water budget
- **A source-linked crop catalogue** of 10 Punjab crops with PAU (Punjab Agricultural University) documented rotation relationships
- **Adjustable farmer priorities** — letting farmers weight water conservation, soil potential, and crop diversity
- **Scenario stress tests** — hypothetical dry, hot, and water-reduced conditions to reveal rotation sensitivity
- **Pareto multi-objective comparison** — showing trade-offs between alternatives without hiding uncertainty

FieldShift does not predict yield, forecast weather, or guarantee soil improvement. Instead, it makes every data source, score method, uncertainty, and limitation transparent so farmers can make informed decisions with local expertise.

---

## 90-Second Demo Script

| Time | Action | What to show |
|---|---|---|
| 0:00–0:10 | **Open app, read title** | Home page with disclaimer and feature list |
| 0:10–0:20 | **Click "Load Ludhiana example"** | Farm profile auto-fills with illustrative inputs |
| 0:20–0:30 | **Navigate to Climate Insights, click "Retrieve NASA POWER data"** | Real API call, charts appear |
| 0:30–0:40 | **Navigate to Farmer Priorities** | Adjust water slider up, show normalization |
| 0:40–0:55 | **Navigate to Rotation Recommendations** | Show 2–3 alternatives with source links, feasibility checks |
| 0:55–1:10 | **Navigate to Scenario Stress Tests** | Show dry/hot sliders, robustness table, hard-constraint alert |
| 1:10–1:20 | **Navigate to Comparison View** | Pareto cards, bar chart, trade-off table |
| 1:20–1:30 | **Navigate to Data and Methods** | Uncertainty table, "no confidence %" disclaimer |

**Key talking points:**
- "Real NASA POWER data — no API key needed"
- "Transparent — every score has a documented method"
- "Scenarios are hypothetical stress tests, not forecasts"
- "Farmers retain full control over the final choice"

---

## Likely Judge Questions & Answers

| Question | Answer |
|---|---|
| **How do you use NASA data?** | We retrieve historical daily climate data from NASA POWER (temperature, precipitation, solar radiation) for any user-entered location. This provides real climate context — it's gridded data, not a field measurement, and we label it as such. |
| **Can this predict crop yield?** | No. FieldShift compares documented rotation alternatives using transparent rules. It does not predict yield, profit, or soil improvement. |
| **How does the scoring work?** | Each alternative gets 0–1 scores for available metrics (water suitability, rotation diversity). Unavailable metrics (climate suitability, economics) show N/A — never zero. The composite score is a preference-weighted comparison, not a probability. |
| **What about soil health?** | We include a simplified N-balance and SOC direction model using published FAO/IPCC equations, but it's clearly labelled as uncalibrated to Punjab conditions. Real soil data comes from farmer/lab reports only. |
| **How do scenarios work?** | Users configure hypothetical stress tests: reduce precipitation, increase temperature, cut water budget. These are sensitivity tests, not weather forecasts. The app shows which rotations break under each scenario. |
| **Why no machine learning?** | With 10 crops and 11 documented relationships, ML would add complexity without improving decision quality. Our goal is transparency — every rule and score is explainable and source-linked. |
| **Can this scale to other regions?** | The architecture is region-independent. Adding a new region requires: a source-linked crop catalogue, documented rotation relationships, and local agronomist review. The engine and UI are reusable. |
| **What are the main limitations?** | 10 crops only, no temperature suitability thresholds, no economic data, soil-state model is uncalibrated. These are honestly documented in `docs/KNOWN_LIMITATIONS.md`. |
