# GitHub presentation checklist

## Suggested repository metadata

**Repository name:** `nyc-fleet-optimizer`

**Description:** `Forecast urban ride demand and optimize dynamic fleet repositioning with XGBoost, Gurobi, SQL/dbt, FastAPI, and Streamlit.`

**Topics:**

`operations-research`, `data-science`, `data-engineering`, `optimization`, `gurobi`, `xgboost`, `fastapi`, `streamlit`, `dbt`, `airflow`, `transportation`, `network-flow`

## Before making the repository public

1. Run `make demo` locally.
2. Confirm `pytest` passes.
3. Launch the Streamlit app and take one real screenshot for the README if you want to replace the static demo visual.
4. Run the real TLC experiment and replace the synthetic benchmark numbers in the resume bullet with real measured results.
5. Add the repo to your GitHub profile pins.
6. In GitHub repository settings, use `assets/hero.svg` as the basis for a social-preview image if desired.

## Strong commit history

Instead of uploading the finished repository as one giant commit, a portfolio-friendly history could be:

1. `feat: add TLC ingestion and zone demand mart`
2. `feat: add temporal feature pipeline and forecast baselines`
3. `feat: implement Gurobi repositioning model`
4. `feat: add rolling fleet simulator and policy baselines`
5. `feat: expose optimizer through FastAPI`
6. `feat: add Streamlit decision dashboard`
7. `chore: add Docker, CI, dbt, and Airflow orchestration`
8. `docs: add architecture, formulation, and benchmark results`

That history makes the engineering progression easier for a recruiter to inspect.
