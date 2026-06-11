# 022 — Model Registry and Artifact Format

**Date:** 2026-05-21
**Component:** Model layer (`src/models/registry.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR introduces a new file, `src/models/registry.py`. It sits at the persistence boundary of the model layer — it turns the in-memory output of `selector.py` into files on disk, and reads those files back.

This ADR depends on:
- **ADR 021** — `selector.py` produces a `SelectionResult`. The registry's `save_model` consumes one. The registry's `load_model` returns a smaller `ModelArtifact`, not a `SelectionResult` — the asymmetry is deliberate and explained below.
- **ADR 018** — Established that MLflow logging is the orchestration script's job, not the job of pure model-layer files. The registry follows the same principle: it writes a deployable artifact to disk; it does not log to MLflow.

This ADR has a still-pending consumer: **the orchestration script** (not yet built). That script will call `selector.select_best_model`, receive a `SelectionResult`, and pass it to `registry.save_model`. The same script owns MLflow logging. The registry is called *by* the orchestrator; it does not call anything upstream. This dependency is noted here so the deferred relationship stays visible in the written record.

---

## Context

After `selector.py` runs, the system holds a deployable artifact in memory: a fitted pipeline, a chosen threshold, a cost ratio, and selection metadata. That artifact needs to outlive the training process. It must be:

- **Saved** — written to disk so it survives past the training run
- **Loaded** — read back by the FastAPI serving layer (to score applicants), the monitoring layer (to know what model is in production), and any future retraining run (to compare against the current model)

Without a defined persistence format, every consumer would invent its own way of reading a saved model, and the "what does a saved model look like" contract would be implicit and inconsistent. The registry exists to make that contract explicit and single-sourced.

Several design questions had to be answered:

1. **What gets saved** — just the pipeline, or the pipeline plus its decision context?
2. **In what format** — one file or several?
3. **What does loading return** — the same shape that was saved, or a different one?
4. **How is accidental destruction of a deployed model prevented?**

---

## Decision

### 1. Save a bundle, not a bare pipeline

A saved model is the pipeline *plus* everything needed to use it as a decision system. A fitted pipeline alone is insufficient: `predict_proba` returns a probability, but the business decision "approve or reject" requires the threshold that `selector.py` chose. Saving only the pipeline would force the serving layer to hardcode or guess a threshold — both unacceptable.

The saved artifact therefore includes: the pipeline, the threshold, the cost ratio, the model name, the winner's validation metrics, and the selection metadata (timestamps, candidate names, validation set size, threshold grid description).

### 2. Two files, not one blob

The artifact is written as **two files in one directory**:

- `model.joblib` — the fitted sklearn Pipeline. Binary. Only `joblib` can deserialise it.
- `metadata.json` — the threshold, cost ratio, model name, metrics, and selection metadata. Plain JSON. Human-readable.

The alternative — bundling everything into a single `joblib.dump` — was rejected. It would trap the metadata inside a binary blob. Answering a one-line question like "what threshold does this model use?" or "when was this trained?" would require loading the entire fitted pipeline (potentially megabytes of numpy arrays) into memory. The monitoring layer, in particular, may want to check a model's identity or staleness without paying the cost of loading the pipeline.

The two-file split keeps the metadata cheap to read — any tool, including a shell script or a FastAPI health-check endpoint, can read `metadata.json` without importing sklearn or joblib.

The **directory is the unit of artifact**. The two files travel together. Saving creates the directory; loading expects both files inside it.

### 3. JSON conversion is an explicit step

A fitted Pipeline is not JSON-serialisable, and neither are several of the metadata types: `cost_ratio` is a tuple (JSON has no tuple), metric values may be numpy floats (JSON has no numpy types), and `SelectionMetadata` is a frozen dataclass (not directly serialisable).

A private helper, `_selection_result_to_json_dict`, performs the conversion: tuple → list, numpy float → Python float, nested dataclass → plain dict (via `dataclasses.asdict`). The load path reverses the relevant conversions — notably list → tuple for `cost_ratio` — so the round trip is type-honest.

### 4. `comparison` is excluded from the artifact

`SelectionResult.comparison` carries the per-model breakdown of how all three candidates performed. It is **not** written to the artifact.

The artifact's purpose is *deployment*, not *archaeology*. The serving layer and the monitoring layer have no use for how the losing models performed. Including `comparison` would make every serving container and monitoring probe drag along selection-time data it will never read.

Selection history already has a canonical home: the orchestration script logs the full `SelectionResult`, including `comparison`, to MLflow. Duplicating it into the artifact would create two sources of truth for the same audit question with no mechanism to keep them in sync. The artifact is for machines (serving, monitoring); MLflow is for humans (audit of why a model was chosen).

`candidate_names` (a short list, part of `selection_metadata`) *is* kept — that is identity and provenance ("this model was chosen from these candidates on this date"), not the bulky per-model breakdown.

### 5. Loading returns a `ModelArtifact`, not a `SelectionResult`

`save_model` consumes a `SelectionResult`. `load_model` returns a `ModelArtifact` — a smaller frozen dataclass with five fields: `pipeline`, `threshold`, `cost_ratio`, `model_name`, and `metadata` (the full JSON payload as a dict).

The asymmetry is deliberate. `SelectionResult` is the *selection-time* view of a model — it includes `comparison`, which matters only while choosing. `ModelArtifact` is the *deployment-time* view — the subset that matters once selection is over. A loaded artifact is for scoring and monitoring; it should not carry selection-time clutter.

`ModelArtifact` exposes the common fields (`threshold`, `cost_ratio`, `model_name`) as typed top-level attributes for convenient access, and also retains the complete `metadata` dict so monitoring can inspect any field without a schema change.

### 6. Refuse to overwrite by default

`save_model(result, directory, overwrite=False)`.

If the target directory already exists and `overwrite` is `False`, `save_model` raises `FileExistsError`. A saved model is a production asset; silently overwriting one could destroy the currently-deployed model. The safe default forces the caller to be deliberate.

The `overwrite=True` flag exists for development, where training is re-run frequently and replacing the previous artifact is the intended behaviour. This mirrors the pattern of sklearn parameters like `zero_division` — a safe default that protects production, with an explicit opt-out for callers who know what they are doing.

---

## Consequences

**For `selector.py`:** No changes. The registry is a downstream consumer of `SelectionResult`.

**For the orchestration script (pending):** After selection, the script calls `save_model(result, directory)` to persist the winner. The script also logs the full `SelectionResult` (including `comparison`) to MLflow. The two persistence paths — artifact on disk, run record in MLflow — are complementary, not redundant.

**For the FastAPI serving layer (pending):** It calls `load_model(directory)` at startup, receives a `ModelArtifact`, and uses `artifact.pipeline` plus `artifact.threshold` to score applicants. It can read `metadata.json` directly for a health-check endpoint without loading the pipeline.

**For the monitoring layer (pending):** It can read `metadata.json` to check which model is in production and when it was trained, cheaply, without deserialising the pipeline.

**For cross-platform portability:** `metadata.json` is written with explicit `encoding="utf-8"`. The default file encoding differs between Windows (development) and Linux (GCP Cloud Run deployment); pinning UTF-8 ensures the file is written and read identically on both.

**For testing:** `registry.py` has its own test surface (`tests/test_models/test_registry.py`, 11 tests) covering the save/load round trip, the JSON type conversions, the `comparison` exclusion, the overwrite guard, all three missing-file error cases, and a functional check that a loaded pipeline can still produce predictions.

**For the assumptions tracker:** No new questions are opened. The registry's decisions are bounded applications of standard practice given the contract requirements from ADR 021.

---

## Open questions opened by this ADR

None for v1. Model versioning (multiple historical artifacts side by side), remote artifact storage (S3, GCS), and integration with MLflow's own model registry are deferred to v2. None has a concrete change driver in v1 — the v1 system saves one model to one directory — so none is held open as a tracker question.
