# Architecture

```text
app.py (Streamlit entry point)
        |
        v
ui.py  <----- presentation only: messages, controls, charts
        |
        v
recommendations.py <----- transparent comparison orchestration
        |
        +----> agronomy.py <----- documented feasibility rules
        |
        +----> data_access.py <----- source retrieval, validation, provenance

nasa_power.py <----- NASA POWER retrieval, parsing, caching and provenance
        |
        +----> climate_features.py <----- historical derived indicators only
        |
        +----> rotation_engine.py <----- deterministic supported-rotation search
                       |
                       +----> data/crops.json + rotation_rules.json + priority_weights.json
```

The modules are separate so a source change does not rewrite the interface, and a rule can be tested without Streamlit. `nasa_power.py` is the external-data retrieval layer for this MVP. It returns source metadata or a clear error; it never fabricates a replacement value. `rotation_engine.py` does not import Streamlit: it accepts a farm profile and source-linked data files, then returns explainable plans that can be tested without a browser.

## Configuration and secrets

Local environment files (`.env`, `.env.*`) and Streamlit secrets (`.streamlit/secrets.toml`) are ignored by Git. Do not commit keys, tokens, or farmer-identifying information. This foundation requires no secrets.
