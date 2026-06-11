# ML Reliability Pipeline

An end-to-end ML pipeline for SBA loan default prediction with automated drift monitoring.

## Quick Start

### Install dependencies

pip install -r requirements.txt

### Run the training pipeline
Trains and selects the best model on FY2010-2019 data.

python scripts/run_training.py

### Run the monitoring pipeline
Detects drift in FY2020+ production data against the training baseline.

python scripts/run_monitoring.py

### Start the API

uvicorn src.api.app:app --reload

Interactive API documentation available at http://127.0.0.1:8000/docs.

---

## Live API

The API is deployed on GCP Cloud Run and publicly accessible:

**Base URL:** https://ml-reliability-pipeline-1061232555311.europe-west1.run.app

**Interactive documentation:** https://ml-reliability-pipeline-1061232555311.europe-west1.run.app/docs

The /docs page lets you explore and call all four endpoints directly from your browser without writing any code.

### Deploying to Cloud Run

The model artifact is 218MB. Cloud Run requires at least 2GB memory:

gcloud run deploy ml-reliability-pipeline --image gcr.io/ml-reliability-pipeline-2026/ml-reliability-pipeline --platform managed --region europe-west1 --allow-unauthenticated --memory 2Gi

---

## Case Study

See docs/case-study.md for the full results — model performance on FY2010-2019 data and the COVID-19 drift story detected on FY2020-present data.

**Headline results:**
- Selected model: Random Forest, ROC-AUC 0.9721 on test set
- 7 of 12 features showing significant drift (PSI > 0.25) in production data
- Strongest signal: initialinterestrate shifted 1.46 standard deviations post-COVID

---

## Running Tests

# All tests except slow integration tests
pytest --ignore=tests/test_scripts

# Only slow integration tests
pytest -m slow

# Full test suite
pytest

---

## Architecture

The pipeline has four layers:

- **Data layer** (src/data/) — load, transform, validate raw SBA CSV data
- **Model layer** (src/models/) — feature engineering, hyperparameter tuning, model selection, artifact persistence
- **Monitoring layer** (src/monitoring/) — drift detection (PSI + Wasserstein), severity classification, reporting
- **API layer** (src/api/) — FastAPI serving layer for single predictions and batch drift monitoring

Every non-obvious design decision is documented in decisions/. There are 26 ADRs covering the data layer, model layer, monitoring layer, orchestration, and infrastructure. Key decisions include:

- Why PSI and Wasserstein over KS test (ADR 023)
- How the drift detection output contract was designed (ADR 025)
- Containerisation and CI/CD strategy (ADR 026)

---

## Project Structure

data/
  raw/                # SBA CSV files
  baseline/           # Saved baseline snapshots
artifacts/            # Saved model artifacts
decisions/            # Architecture Decision Records (ADRs)
docs/                 # Case study and architecture notes
scripts/
  run_training.py
  run_monitoring.py
src/
  data/               # Data layer
  models/             # Model layer
  monitoring/         # Monitoring layer
  api/                # FastAPI serving layer
tests/                # Test suite

---

## Key Design Principles

- **Separation of concerns** — each layer has one job; no cross-layer imports where contracts don't demand it
- **Frozen dataclasses** — all configuration and result objects are immutable
- **Metadata-rich outputs** — every tuning run, selection, and drift report carries full audit information
- **Reproducibility first** — fixed seeds, explicit ddof conventions, UTC timestamps
- **Tested wiring** — 110 tests including slow integration tests for both orchestration scripts