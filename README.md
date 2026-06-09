```markdown
# ML Reliability Pipeline

An end-to-end ML pipeline for SBA loan default prediction with automated drift monitoring.

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the training pipeline
Trains and selects the best model on FY2010-2019 data.
```bash
python scripts/run_training.py
```

### Run the monitoring pipeline
Detects drift in FY2020+ production data against the training baseline.
```bash
python scripts/run_monitoring.py
```

### Start the API
```bash
uvicorn src.api.app:app --reload
```
Interactive API documentation available at `http://127.0.0.1:8000/docs`.

## Live API

The API is deployed on GCP Cloud Run and publicly accessible:

**Base URL:** https://ml-reliability-pipeline-1061232555311.europe-west1.run.app

**Interactive documentation:** https://ml-reliability-pipeline-1061232555311.europe-west1.run.app/docs

The `/docs` page lets you explore and call all four endpoints directly from your browser without writing any code.

## Running Tests

```bash
# All tests except slow integration tests
pytest --ignore=tests/test_scripts

# Only slow integration tests
pytest -m slow

# Full test suite
pytest
```

## Architecture

The pipeline has four layers:

- **Data layer** (`src/data/`) — load, transform, validate raw SBA CSV data
- **Model layer** (`src/models/`) — feature engineering, hyperparameter tuning, model selection, artifact persistence
- **Monitoring layer** (`src/monitoring/`) — drift detection (PSI + Wasserstein), severity classification, reporting
- **API layer** (`src/api/`) — FastAPI serving layer for single predictions and batch drift monitoring

Every non-obvious design decision is documented in `decisions/`. There are 25 ADRs covering the data layer, model layer, monitoring layer, and orchestration. Key decisions include:

- Why PSI and Wasserstein over KS test (ADR 023)
- Why XGBoost was selected (ADR 021)
- How the drift detection output contract was designed (ADR 025)
- Why the monitoring layer does not import from the model layer (ADR 025)

## Project Structure

```
├── data/                   # Raw and processed data files
│   ├── raw/                # SBA CSV files
│   └── baseline/           # Saved baseline snapshots
├── artifacts/              # Saved model artifacts
├── decisions/              # Architecture Decision Records (ADRs)
├── notebooks/              # Exploratory notebooks
├── scripts/                # Pipeline orchestration scripts
│   ├── run_training.py
│   └── run_monitoring.py
├── src/
│   ├── data/               # Data layer
│   ├── models/             # Model layer
│   ├── monitoring/         # Monitoring layer
│   └── api/                # FastAPI serving layer
└── tests/                  # Test suite
```

## Key Design Principles

- **Separation of concerns** — each layer has one job; no cross-layer imports where contracts don't demand it
- **Frozen dataclasses** — all configuration and result objects are immutable
- **Metadata-rich outputs** — every tuning run, selection, and drift report carries full audit information
- **Reproducibility first** — fixed seeds, explicit `ddof` conventions, UTC timestamps
- **Tested wiring** — 100+ tests including slow integration tests for both orchestration scripts
```