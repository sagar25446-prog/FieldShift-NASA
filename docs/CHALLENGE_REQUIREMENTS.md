# Challenge Requirements — Field Shift: Adapting Farms with NASA Data

**Challenge URL:** <https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/>  
**Categories:** Advanced, Intermediate  
**Skills:** Arts & Multimedia, Earth Science, Software  
**Last verified:** 2026-10-13

---

## Official Challenge Description

> Farmers around the world navigate shifting temperatures, changing rainfall patterns, water shortages, extreme weather, and declining soil health. These pressures make it difficult to choose crop rotations that protect fields, conserve water, and support long‑term resilience. Your challenge is to create a decision‑support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions.

---

## How FieldShift Addresses Each Requirement

| Challenge requirement | FieldShift response | Status |
|---|---|---|
| **NASA Earth observations** | NASA POWER Daily API — retrieves historical T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN for any entered location. Full provenance recorded. | ✅ Integrated |
| **Local soil information** | Farmer/lab-provided: texture, pH, EC, organic carbon, waterlogging, alkaline condition, drainage. Unknown values remain unknown. | ✅ Integrated |
| **Crop characteristics** | Source-linked Punjab crop catalogue (10 crops, PAU references) with water requirements, soil constraints, growing seasons, family, legume status. | ✅ Integrated |
| **Farmer priorities** | Adjustable weight sliders for water suitability, climate suitability, soil-related potential, rotation diversity, economic potential. Normalized to sum to 1. | ✅ Integrated |
| **Explore rotation strategies** | Deterministic DFS over 11 documented PAU crop-to-crop relationships. Generates multi-season alternatives with feasibility checks. | ✅ Integrated |
| **Strengthen soil health** | Simplified FAO/IPCC N-balance and SOC direction model. Clearly labelled as uncalibrated educational estimate. | ✅ Integrated (with disclaimers) |
| **Adapt to changing conditions** | Scenario stress tests: dry (−precipitation), hot (+temperature), reduced water budget. Robustness assessment across scenarios. | ✅ Integrated |

## What FieldShift Does NOT Do

- ❌ Predict crop yield, profit, or income
- ❌ Forecast weather or climate
- ❌ Guarantee soil improvement
- ❌ Replace agronomic advice
- ❌ Invent missing data values
- ❌ Use machine learning

---

## Submission Interface Items to Verify

> ⚠️ The submission portal's exact fields, word limits, and media requirements must be checked at submission time in the actual interface. The following are common Space Apps submission components based on past years:

- [ ] **Project title** — "FieldShift"
- [ ] **Challenge selection** — "Field Shift: Adapting Farms with NASA Data"
- [ ] **Project description** — See `docs/SUBMISSION_CHECKLIST.md`
- [ ] **GitHub repository link** — https://github.com/sagar25446-prog/FieldShift-NASA
- [ ] **Live demo URL** — https://fieldshift-nasa.streamlit.app (verify after deployment)
- [ ] **Team members** — Enter in submission portal
- [ ] **Video demo** — Check if required; if so, record a 90-second walkthrough
- [ ] **NASA data usage** — Describe NASA POWER Daily API usage
- [ ] **Tools and technologies** — Python, Streamlit, pandas, NumPy, Plotly

> **Do not assume video is mandatory** — verify in the actual submission form. Past years have had optional video fields.
