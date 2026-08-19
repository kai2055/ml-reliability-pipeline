# ML Reliability Pipeline

**How do you notice when a model's world has changed underneath it?**

A model that passed every test on launch day slowly goes wrong as the world moves on — and the first sign is usually an angry user. This end-to-end loan-default pipeline exists to catch that gap early: it trains on 2010–2019 U.S. SBA loan data, then watches 2020-onward production data for drift against that training baseline. **The model isn't the point — the monitoring is.**

[![CI](https://github.com/kai2055/ml-reliability-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/kai2055/ml-reliability-pipeline/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![PSI drift](https://img.shields.io/badge/drift-PSI-orange)
![MLflow](https://img.shields.io/badge/MLflow-0194E2?logo=mlflow&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Cloud Run](https://img.shields.io/badge/GCP%20Cloud%20Run-4285F4?logo=googlecloud&logoColor=white)
![tests](https://img.shields.io/badge/tests-112-brightgreen)
![coverage gate](https://img.shields.io/badge/coverage%20gate-75%25-green)
![ADRs](https://img.shields.io/badge/ADRs-27-blue)

🔗 **[Live API](https://ml-reliability-pipeline-1061232555311.europe-west1.run.app/docs)** — call all four endpoints from the browser, no code required &nbsp;·&nbsp; 🎥 Demo *(coming)* <!-- replace with: 🎥 [Watch demo](VIDEO_URL) -->

<!-- Screenshot slot — drop a drift-report or /docs screenshot here:
![drift report](docs/img/drift-report.png)
-->

---

## What the monitor caught

After COVID, a model trained on a pre-pandemic world kept scoring 2020 applicants as if nothing had changed. The monitoring layer surfaced exactly that:

| Signal | Finding |
| --- | --- |
| 🚩 Features drifted significantly (PSI > 0.25) | **7 of 12** |
| 📈 Strongest drift | **initial interest rate — 1.46 standard deviations** post-COVID |
| 🧪 Baseline model | Random Forest, ROC-AUC **0.9721** on held-out test |

**On that 0.97 — it's a red flag, not a trophy.** An AUC that high on loan-default prediction almost always means label leakage: some feature quietly encoding the outcome it's meant to predict. The leakage audit is scoped for v2; until then the model is scaffolding — something for the monitoring layer to watch. Naming that openly is deliberate. Reliability work means knowing where your system is weak.

Full write-up: [`docs/case-study.md`](docs/case-study.md).

---

## How it's built

Four layers, each with exactly one job. The flow runs in order: **train → snapshot baseline → monitor production → serve.**

| Layer | Job |
| --- | --- |
| **Data** | Loads the FOIA extracts, validates them against a frozen schema, transforms them for training. If the extract format changes, the pipeline **fails fast** with a clear error instead of quietly training on the wrong thing. |
| **Models** | Trains candidates, tunes, evaluates, and selects one — every run tracked in MLflow, the chosen model saved as a versioned artifact. |
| **Monitoring** | Snapshots a baseline at training time, scores production data against it with **PSI**, and applies a documented drift policy to decide what counts as significant. |
| **Serving** | A FastAPI app exposes the prediction and drift endpoints, deployed on GCP Cloud Run. |

**Design principles:** separation of concerns (no cross-layer imports the contracts don't demand) · frozen dataclasses for config and results · metadata-rich outputs (every tuning run, selection, and drift report carries full audit info) · reproducibility first (fixed seeds, explicit `ddof`, UTC timestamps).

---

## Decisions are written down

Every non-trivial decision is an **Architecture Decision Record** — 27 of them in [`decisions/`](decisions/), numbered in the order they were made. The code tells you *what*; the ADRs tell you *why*. A few:

- **ADR-012** — the schema is the single source of truth; everything validates against it
- **ADR-021** — how the model and its classification threshold get selected
- **ADR-027** — why v1 stops at *detecting* drift instead of auto-retraining

---

## Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Train + select the best model on FY2010–2019 data
python scripts/run_training.py

# 3. Detect drift in FY2020+ production data against the training baseline
python scripts/run_monitoring.py

# 4. Serve
uvicorn src.api.app:app --reload   # interactive docs at http://127.0.0.1:8000/docs
```

### Getting the data

The pipeline expects two CSVs in `data/raw/` (not committed). Column expectations are enforced by `src/data/schema.py` — it fails fast if the extract format has drifted.

| File | Source | Rows |
| --- | --- | --- |
| `sba_7a_2010_2019.csv` | SBA 7(a) FOIA extracts FY2010–FY2019 | ~545k |
| `sba_7a_2020_present.csv` | SBA 7(a) FOIA extracts FY2020+ | production window |

Download the CSV extracts from the SBA 7(a) & 504 FOIA data page, concatenate the FY2010–2019 range into the first file, and the FY2020–present window into the second.

---

## Deploying to Cloud Run

The model artifact is 218 MB, so Cloud Run needs at least 2 GB of memory:

```bash
gcloud run deploy ml-reliability-pipeline \
  --image gcr.io/ml-reliability-pipeline-2026/ml-reliability-pipeline \
  --platform managed --region europe-west1 --allow-unauthenticated --memory 2Gi
```

---

## Tests & CI

**112 tests**, including slow integration tests that drive both orchestration scripts end to end.

```bash
pytest --ignore=tests/test_scripts   # everything except the slow integration tests
pytest -m slow                       # only the slow integration tests
pytest                               # full suite
```

Every push and PR to `main` runs `.github/workflows/ci.yml`: **ruff** lint · **mypy** type check · fast tests with a **coverage gate** (build fails below 75% on `src`) · **codespell** · a separate **Docker build** job. Slow integration tests run locally. Deployment is a manual `gcloud run deploy` — so this pipeline covers continuous *integration*, not automated deployment.

---

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
