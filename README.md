# ML Reliability Pipeline

An end-to-end loan-default pipeline built around one question: how do you notice when a model's world has changed underneath it?

[![CI](https://github.com/kai2055/ml-reliability-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kai2055/ml-reliability-pipeline/actions/workflows/ci.yml)

The pipeline trains on SBA 7(a) loan data from 2010–2019, then watches 2020-onward production data for drift against that training baseline. The interesting part isn't the model — it's what the monitor caught. After COVID, 7 of 12 features drifted significantly, and the average initial interest rate moved 1.46 standard deviations from its pre-pandemic baseline. A model trained in 2019 was making decisions in a world that no longer matched its training data. Noticing that gap is the whole point of the project.

## How it's built

Four layers, each with one job:

- **Data** — loads the extracts, validates them against a frozen schema, and transforms them for training. If the FOIA format changes, the pipeline fails fast with a clear error instead of quietly training on the wrong thing.
- **Models** — trains candidates, tunes them, evaluates, and selects one, with every run tracked in MLflow. The chosen model and its metadata are saved as a versioned artifact.
- **Monitoring** — snapshots a baseline at training time, then scores production data against it with PSI and applies a drift policy to decide what counts as significant.
- **Serving** — a FastAPI app exposes the prediction and drift endpoints, deployed on GCP Cloud Run.

The flow runs in that order: **train → snapshot baseline → monitor production → serve.**

## What the monitor caught

The full write-up is in [`docs/case-study.md`](docs/case-study.md) — model performance on FY2010–2019 and the COVID-19 drift story detected on FY2020+ data. The headline findings:

- **7 of 12 features** drifted significantly (PSI > 0.25) in production data
- The strongest signal was `initialinterestrate`, which shifted **1.46 standard deviations** post-COVID
- The baseline model is a Random Forest (ROC-AUC 0.9721 on the held-out test set), selected by the policy in [ADR-021](decisions/021-model-selection-and-threshold-policy.md)

That 0.97 is a red flag, not a trophy. An AUC that high on loan-default prediction almost always means label leakage — some feature quietly encoding the outcome it's supposed to predict. I haven't run the leakage audit yet; it's scoped for v2. Until then the model is best read as scaffolding: something for the monitoring layer to watch. The monitoring is the point here, not the model.

## Decisions are written down

Every non-trivial decision in this project has an Architecture Decision Record. There are 27 of them in [`decisions/`](decisions/), numbered in the order they were made. A few that show the kind of thing they capture:

- **[ADR-012](decisions/012-schema-is-the-source-of-truth.md)** — the schema is the single source of truth, and everything validates against it
- **[ADR-021](decisions/021-model-selection-and-threshold-policy.md)** — how the model and its classification threshold get selected
- **[ADR-027](decisions/027-drift-response-strategy-rebaselining-retraining-and-why-v1-stops-at-detection.md)** — why v1 stops at *detecting* drift instead of automatically retraining

I kept them because six months later the code tells you what, not why. The ADRs are the why.

## Quick Start

**Install dependencies**
```bash
pip install -r requirements.txt
```

**Run the training pipeline** — trains and selects the best model on FY2010–2019 data.
```bash
python scripts/run_training.py
```

**Run the monitoring pipeline** — detects drift in FY2020+ production data against the training baseline.
```bash
python scripts/run_monitoring.py
```

**Start the API**
```bash
uvicorn src.api.app:app --reload
```
Interactive docs at http://127.0.0.1:8000/docs.

## Live API

The API is deployed on GCP Cloud Run and publicly reachable:

- **Base URL:** https://ml-reliability-pipeline-1061232555311.europe-west1.run.app
- **Interactive docs:** https://ml-reliability-pipeline-1061232555311.europe-west1.run.app/docs

The `/docs` page lets you call all four endpoints from the browser without writing any code.

## Getting the data

The pipeline expects two CSV files in `data/raw/` (the raw files are not committed):

| File | Source | Rows |
|------|--------|------|
| `sba_7a_2010_2019.csv` | SBA 7(a) FOIA extracts FY2010–FY2019 | ~545k |
| `sba_7a_2020_present.csv` | SBA 7(a) FOIA extracts FY2020+ | production window |

1. Visit the [SBA 7(a) & 504 FOIA data page](https://data.sba.gov/dataset/7-a-504-foia)
2. Download the CSV extracts for FY2010 through FY2019
3. Concatenate them into `data/raw/sba_7a_2010_2019.csv`
4. Repeat for the production window (FY2020–present) as `data/raw/sba_7a_2020_present.csv`

Column expectations are enforced by `src/data/schema.py` — the pipeline fails fast if the extract format has drifted.

## Deploying to Cloud Run

The model artifact is 218MB, so Cloud Run needs at least 2GB of memory:

```bash
gcloud run deploy ml-reliability-pipeline \
  --image gcr.io/ml-reliability-pipeline-2026/ml-reliability-pipeline \
  --platform managed --region europe-west1 --allow-unauthenticated --memory 2Gi
```

## Running tests

112 tests, including slow integration tests that exercise both orchestration scripts end to end.

```bash
# Everything except the slow integration tests
pytest --ignore=tests/test_scripts

# Only the slow integration tests
pytest -m slow

# Full suite
pytest
```

## Continuous integration

Every push and pull request to `main` runs the checks in [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

- **Lint** — `ruff` across `src`, `tests`, and `scripts`
- **Type check** — `mypy` on `src`
- **Tests + coverage** — the fast suite runs with a coverage gate; the build fails if coverage of `src` drops below 75%
- **Spell check** — `codespell` across the code, docs, and ADRs
- **Docker build** — a separate job verifies the image actually builds

The slow integration tests are skipped in CI and run locally. Deployment is a manual `gcloud run deploy` (above), so this pipeline covers continuous integration, not automated deployment.

## Project structure

```
├── data/              # raw and processed data, plus saved baseline snapshots
├── artifacts/         # saved model artifacts
├── decisions/         # 27 Architecture Decision Records
├── docs/              # case study and architecture notes
├── scripts/           # pipeline orchestration (run_training, run_monitoring)
├── src/
│   ├── data/          # data layer
│   ├── models/        # model layer
│   ├── monitoring/    # monitoring layer
│   └── api/           # FastAPI serving layer
└── tests/             # test suite
```

## Key design principles

- **Separation of concerns** — each layer has one job; no cross-layer imports where the contracts don't demand it
- **Frozen dataclasses** — configuration and result objects are immutable
- **Metadata-rich outputs** — every tuning run, selection, and drift report carries full audit information
- **Reproducibility first** — fixed seeds, explicit `ddof` conventions, UTC timestamps