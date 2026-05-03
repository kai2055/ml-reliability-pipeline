
# 006 — Component Build Order Revision

**Date:** 2026-05-04  
**Component:** Project-wide  
**Status:** Decided

---

## Context

Original order had drift detection at step 2, before model building. The thinking was that drift detection only needs a baseline snapshot and incoming data — it doesn't depend on the model directly, so it could be built independently.

That logic is technically correct but misses the point. This project is both a learning portfolio and a showcase portfolio. Building drift detection before the model means there's no trained model, no real baseline, no concrete feature space to work against. Everything would be abstract. The ML story would be built backwards.

---

## Decision

Revised build order — sklearn pipeline with MLflow tracking moves to step 2:

1. Data validation layer
2. sklearn pipeline with MLflow tracking
3. Drift detection (PSI + KS)
4. FastAPI serving layer
5. GCP deployment + CI/CD
6. pytest coverage

---

## Consequences

Building the model first means drift detection has something real to work with — a trained model, a saved baseline distribution, actual feature distributions to compare against. The story makes sense end to end.

From a learning perspective this also flows better. The concepts from model building — preprocessing, pipeline structure, MLflow tracking, baseline snapshots — are exactly what drift detection builds on. Doing it in this order means each layer adds to the previous one rather than jumping ahead of it.