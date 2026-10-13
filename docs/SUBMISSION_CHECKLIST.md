# FieldShift — Submission Checklist

**Challenge:** Field Shift: Adapting Farms with NASA Data  
**Team repository:** https://github.com/sagar25446-prog/FieldShift-NASA  
**Live demo:** https://fieldshift-nasa.streamlit.app *(verify after deployment)*

---

## Pre-Submission Verification

### Code & Deployment
- [x] All 156 automated tests pass (155 pass, 1 skipped) (`python -m pytest`)
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
- [x] `docs/WATER_BALANCE_METHODOLOGY.md` — FAO-56 Penman-Monteith ET0, Kc stages, USDA SCS effective rainfall
- [x] `docs/CLIMATE_SUITABILITY_METHODOLOGY.md` — FAO EcoCrop cardinal thermal limits, heat stress criteria
- [x] `docs/CLIMATE_TRENDS_METHODOLOGY.md` — Multi-decadal OLS trend regression, PAU seasonal calendars, and dry spells
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
- [x] Every score method is documented with source citations
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
- [ ] **NASA data used:** NASA POWER Daily API (T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN, RH2M, WS2M)
- [ ] **Tools/technologies:** Python, Streamlit, pandas, NumPy, Plotly

### Check If Required
- [ ] **Demo video** — Record if the form asks for one (90-second script below)
- [ ] **Slide deck** — Prepare if required
- [ ] **Word/character limits** — Adjust descriptions to fit

---

## Draft Project Description

**FieldShift** is an evidence-backed, farmer-friendly decision-support web application for exploring climate-resilient crop rotation alternatives using NASA Earth observation data. Focused on Punjab, India, it integrates:

- **NASA POWER Daily API & FAO-56 Reference Evapotranspiration:** Uses solar radiation, temperature, humidity, and wind speed to calculate FAO-56 Penman-Monteith daily $ET_0$, stage-specific crop water demand $ET_c = K_c \times ET_0$, and USDA SCS effective precipitation to evaluate real irrigation deficits.
- **FAO EcoCrop Thermal Suitability & Heat Stress:** Translates NASA daily maximum temperatures and crop cardinal limits into transparent suitability scores and heat stress exposure alerts (days $>35^\circ\text{C}$ or $>40^\circ\text{C}$).
- **Historical Climate Trends Analysis:** Multi-decadal OLS regression and statistical significance ($p$-values) examining long-term growing-season warming, precipitation changes, and dry-spell runs across Kharif, Rabi, and Summer seasons.
- **Local Soil & Water Constraints:** Evaluates texture, drainage, salinity, alkalinity, waterlogging risks, and farmer water budgets.
- **PAU-Documented Crop Transitions:** 19 agro-ecological transitions spanning all 10 catalogue crops with 100% reachability (including Pearl Millet and Rapeseed Mustard).
- **Farmer Priority Weighting & Pareto Comparisons:** Empowers growers to tune water, climate, soil, and diversity weights to generate transparent Pareto-optimal rankings with trade-off disclosures.
- **Offline Judging Reliability:** Features an instant live judging preset and verified 2024 Ludhiana daily NASA POWER offline snapshot with graceful network fallback.

FieldShift does not predict yields, forecast weather, or make uncalibrated profit claims. Instead, it makes every calculation, data source, uncertainty, and limitation transparent so farmers can make resilient decisions with local expertise.

---

## 90-Second Demo Script

| Time | Action | What to show |
|---|---|---|
| 0:00–0:15 | **Home page & Live Quick-Start** | Click **"🚀 Load demo & view plans"** to instantly load the Ludhiana benchmark farm, verified 2024 NASA POWER snapshot, and generate 4 feasible rotations. |
| 0:15–0:30 | **Rotation Recommendations** | Show top-ranked rotations (`Maize → Wheat → Moong` vs `Cotton → Wheat → Moong`). Highlight the dynamic **FAO-56 Water Suitability** and **EcoCrop Climate Suitability** scores and source links. |
| 0:30–0:45 | **Climate Trends Page** | Open the 9-variable historical trends inspector. Show 2000–2024 Kharif mean temperature warming trend ($+0.42^\circ\text{C}$/decade, $p < 0.05$), baseline anomaly, and consecutive dry-spell runs. |
| 0:45–1:00 | **Climate Insights & Mode Toggle** | Inspect daily solar radiation, temperature, and precipitation charts. Show the **Mode Indicator** banner and demonstrate the one-click toggle between live NASA API and the verified offline snapshot. |
| 1:00–1:15 | **Farmer Priorities & Pareto Comparison** | Adjust the Water Conservation weight to 100% to demonstrate dynamic re-ranking. Switch to Comparison View to show Pareto dominance cards and trade-off tables. |
| 1:15–1:30 | **Scenario Stress Tests & Transparency** | Run the "Severe Dry (+2°C, -30% Rain)" hypothetical stress test. View hard-constraint alerts and review Data & Methods uncertainty disclosures. |

**Key talking points:**
- "Real NASA POWER data driving FAO-56 Penman-Monteith evapotranspiration and EcoCrop thermal suitability."
- "NASA climate data directly changes the rotation ranking."
- "Multi-decadal historical climate trends with honest $p$-value statistical disclosures."
- "Instant one-click judging demo with real, verified NASA observations and offline network fallback."
- "Zero uncalibrated yield promises; total scientific transparency."

---

## Likely Judge Questions & Answers

| Question | Answer |
|---|---|
| **How does NASA POWER change the recommendation?** | Rather than relying only on a farmer-entered water budget, FieldShift uses NASA POWER daily solar radiation, temperature, humidity, and wind speed to calculate FAO-56 Penman-Monteith reference evapotranspiration ($ET_0$). Combined with FAO crop coefficients ($K_c$) and effective precipitation, this calculates crop water deficit. Concurrently, NASA temperatures are evaluated against FAO EcoCrop cardinal limits ($T_{\min}, T_{\text{opmin}}, T_{\text{opmax}}, T_{\max}$) and heat stress days ($>35^\circ\text{C}$). Different climate histories directly alter water and climate scores, changing the rotation rankings. |
| **What if the NASA POWER API is slow or down during judging?** | FieldShift includes a verified offline demonstration snapshot (`data/demo_snapshot_ludhiana_2024.json`) containing 366 days of real, unedited 2024 NASA POWER observations for Ludhiana. The application detects timeouts within 15 seconds and provides an immediate one-click fallback button that loads the offline snapshot without interruption or errors. |
| **Are the climate trends extrapolated into future forecasts?** | No. The Climate Trends module uses Ordinary Least Squares (OLS) linear regression solely for descriptive analysis of historical observations (2000–2024). We report slope per decade, $R^2$, and two-tailed Student's t-test $p$-values, while explicitly disclaiming causal yield claims and prohibiting future extrapolation. |
| **Can this predict crop yield or profit?** | No. FieldShift compares documented rotation alternatives using transparent, rule-based agronomic methods. It does not predict yield, profit, or soil improvement, as those require detailed field calibration that coarse satellite grids cannot provide. |
| **How are all catalogue crops represented in the rotation graph?** | The rotation graph contains 19 PAU-documented relationships connecting all 10 catalogue crops across Kharif, Rabi, and Summer seasons. Both Pearl Millet (Bajra) and Rapeseed Mustard (Raya/Sarson) are fully connected and reachable under their appropriate soil conditions (e.g. well-drained, sandy loam). |
| **What happens if soil or climate data is missing?** | Missing inputs are never fabricated or guessed. If an indicator lacks data, its score displays "N/A" and uncertainty warnings are attached to the plan. Composite scores only weight available metrics, and Pareto comparisons never let unknown scores give false dominance. |
| **Why rule-based rather than machine learning?** | Smallholder farmers need transparent, auditable rationales. Rule-based search over peer-reviewed PAU recommendations ensures every constraint (e.g. waterlogging sensitivity, family rotation breaks) is 100% explainable, verifiable, and free from black-box hallucinations. |
| **Can this scale to other regions?** | Yes. The engine, scoring system, and NASA POWER pipeline are region-agnostic. Adapting to another state or country requires only a regional crop catalogue, rotation graph, and season calendar definitions. |
