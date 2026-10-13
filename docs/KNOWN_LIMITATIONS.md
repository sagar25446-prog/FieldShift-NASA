# FieldShift — Known Limitations

> **This document honestly discloses the boundaries of FieldShift's capabilities.**  
> It is part of the project's commitment to transparency over false precision.

---

## Scope Limitations

1. **Regional focus:** Prototype supports Punjab, India crop rotations only (Ludhiana demonstration region).
2. **Crop catalogue size:** 10 crops in catalogue, 11 documented crop-to-crop relationships.
3. **Season model:** Fixed cycle: kharif → rabi → summer. No inter-season or partial-season planning.
4. **Planning horizon:** Maximum 3 seasons (configurable to 2). No multi-year tracking.
5. **Graph coverage:** `pearl_millet` and `rapeseed_mustard` exist in the catalogue but have no documented transitions in `rotation_rules.json`, so they cannot appear in generated multi-season sequences.

---

## Data Limitations

1. **Climate data:** NASA POWER is gridded (~0.5° resolution), not field-level measurement. It is historical context, not a forecast.
2. **Soil data:** No remote soil sensing. All soil values are farmer/lab-provided. Unknown values remain unknown — they are never fabricated.
3. **Temperature thresholds:** No crop-specific thermal thresholds are documented in the catalogue. Climate suitability is always N/A.
4. **Economic data:** No credible local cost/price data is configured. Economic potential is always N/A.
5. **Water requirements:** Documented as approximation ranges from Government of India annexure. Not field-calibrated to specific Punjab districts.
6. **Missing observations:** NASA POWER fill values (-999.0) are converted to NaN and counted. They are never silently replaced with interpolated values.

---

## Model Limitations

1. **Composite score:** A preference-weighted comparison, not a probability of success. It cannot be interpreted as yield prediction.
2. **Pareto analysis:** Only compares on available numeric scores. Missing scores are preserved as N/A, not treated as zero. This prevents false dominance claims.
3. **Soil-state model:** Simplified FAO/IPCC N-balance and Janssen (1984) SOC model. **NOT calibrated to Punjab conditions.** Uses assumed defaults for residue parameters. Labelled as "educational comparison only" in the UI.
4. **Rotation graph:** Small deterministic DFS over documented relationships. Absence of a relationship means "unsupported by this prototype," not "agronomically impossible."
5. **No machine learning:** No ML models are used. This is intentional — the goal is decision quality and transparency over complexity.
6. **No pest/disease modelling:** Pest and disease cycles are not modelled. Farmers can provide avoidance restrictions but the system does not predict pest pressure.

---

## UI/UX Limitations

1. **Mobile layout:** Not optimised. 5-column metric layouts and dynamic Pareto card columns can be cramped on screens < 480px wide. Streamlit provides basic responsiveness but no custom mobile CSS is applied.
2. **No offline mode:** Requires internet for NASA POWER requests. Catalogue-only checks work offline but climate context is absent.
3. **No multi-user support:** No authentication, no persistent user accounts, no database.
4. **Session persistence:** Session state is lost on page refresh (Streamlit limitation). No server-side storage.
5. **Charts require JavaScript:** Plotly charts will not render in environments where JavaScript is disabled.

---

## Security Considerations

1. **No authentication system:** This is a prototype. No user login or access control.
2. **No persistent user data:** All data is session-only and discarded on refresh/close.
3. **NASA POWER API:** Public endpoint, no API key required, no credentials stored.
4. **Input validation:** Streamlit provides basic protection. Server-side validation exists for coordinates, dates, and numeric ranges. No SQL or command injection risk (no database, no shell commands).
5. **CORS:** Not applicable — single-page Streamlit application.
6. **Dependency pinning:** `requirements.txt` does not pin exact versions. This could cause issues with breaking Streamlit/Plotly/pandas updates.

---

## Items Requiring Expert Review

1. **Crop water requirement ranges** need agronomist validation for specific Punjab districts.
2. **Soil constraint rules** need agronomist review beyond PAU general recommendations.
3. **Soil-state model equations** need calibration with Punjab field trial data before any real-world use.
4. **Rotation compatibility graph** needs extension with more documented crop-to-crop relationships.
5. **Season definitions** may need adjustment for specific microclimates within Punjab.
6. **Temperature suitability thresholds** are entirely absent — sourced crop thermal limits are needed.

---

## Future Work (Not Implemented)

| Priority | Feature | Notes |
|---|---|---|
| High | Temperature suitability thresholds | Requires sourced crop-specific thermal limits |
| High | Extended rotation graph | Add transitions for pearl_millet, rapeseed_mustard, potato-based sequences |
| Medium | GPM precipitation integration | Higher-resolution precipitation data |
| Medium | MODIS vegetation indices | Monitor crop health and growth |
| Medium | Local economics module | Requires verified, up-to-date cost/price data |
| Medium | Multi-year planning | Track cumulative soil state across years |
| Low | SMAP/NASA-USDA soil moisture | Complement farmer-provided soil data |
| Low | Pest/disease cycle integration | Requires crop-specific pest calendars |
| Low | Browser accessibility audit | WCAG 2.1 AA automated testing |
| Low | Multi-language support | Punjabi, Hindi translations |
| Low | Dependency version pinning | Lock versions for reproducible deployments |

---

## Disclaimer

FieldShift is an **explainable decision-support prototype**. It does not:
- Measure soil chemistry from space
- Forecast weather
- Predict crop yield or profit
- Guarantee soil improvement
- Replace local agronomic advice

All outputs should be confirmed with qualified agricultural advisors and local evidence before making farming decisions.
