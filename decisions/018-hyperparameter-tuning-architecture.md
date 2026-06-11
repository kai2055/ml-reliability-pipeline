
# 018 — Hyperparameter Tuning Architecture

**Date:** 2026-05-17
**Component:** Model layer (`src/models/tuner.py`, `src/models/tuning_configs.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR introduces two new files: `src/models/tuner.py` and `src/models/tuning_configs.py`. They sit between `dataset_builder.py` (which produces `(X, y)`) and `selector.py` (which will compare tuned models and set thresholds).

This ADR closes **Q6** from `docs/assumptions-to-revisit.md` (why stratified k-fold, why k=5).

This ADR depends on:
- **ADR 014** — `trainer.build_pipeline()` takes column lists and a model object. `tuning_configs.py` builds three pipelines using this function.
- **ADR 015** — Threshold is a business lever, not an algorithm detail. This ADR's choice of AUC as the scoring metric follows directly: tune on a threshold-independent metric so the threshold lever stays free for `selector.py`.
- **ADR 016** — `dataset_builder.py` is the source of `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES`. `tuning_configs.py` imports these constants.

---

## Context

Hyperparameter tuning is a mechanically simple but easy-to-misdesign part of an ML pipeline. The temptation is to wire sklearn's search objects directly into a training script — call `GridSearchCV`, fit it, read off the best estimator, done. That works once. It does not survive:

- Adding a second model family (now two scripts duplicate the search wiring)
- Wanting to record what the search actually did (sklearn's `cv_results_` is a flat dict, easy to lose)
- Wanting to swap search strategy per model (Grid for small spaces, Random for large)
- Wanting to log results to MLflow without making the tuning code MLflow-dependent

The drift-detection thesis of this project amplifies these concerns. The whole point of the system is that ML decisions made *now* will be re-examined *later*, when monitoring surfaces new information. Tuning runs are evidence that needs to be reproducible and auditable — not throwaway experiments.

Several specific design decisions follow from these constraints. They are bundled in one ADR because they are tightly coupled — splitting them would lose the through-line.

---

## Decision

### 1. One generic `tune()` + per-model configs

`tuner.py` exposes a single function `tune(X, y, config) -> TuningResult`. It does not know about logreg vs RF vs XGB. It receives a `TuningConfig` and runs whatever search that config specifies.

`tuning_configs.py` exposes three `TuningConfig` instances — `LOGREG_TUNING_CONFIG`, `RF_TUNING_CONFIG`, `XGB_TUNING_CONFIG` — each declaring the specific search space and strategy for one model family.

The split separates *mechanics* (how does tuning work?) from *policy* (what specific searches did we decide on?). Mechanics rarely change. Policy changes whenever we add a model family or revise a parameter range. Keeping them in separate files means a parameter-range change does not touch `tuner.py`.

The alternative — three functions `tune_logreg()`, `tune_rf()`, `tune_xgb()` — was rejected. The mechanics of running a hyperparameter search are the same for all three models. Duplicating them three times means three places to update when sklearn's search API evolves.

### 2. `TuningResult` is a structured dataclass, not a tuple or dict

`TuningResult` has five fields: `best_estimator`, `best_params`, `best_score`, `cv_results`, and `search_metadata` (itself a `SearchMetadata` dataclass with ten fields documenting how the search was conducted).

A plain tuple would force callers to index by position (`result[0]`, `result[1]`), which is unreadable and breaks if the order changes. A plain dict would force callers to remember key spellings without IDE support. The dataclass is the right shape because there are too many fields for positional access and the fields are stable enough to deserve names.

Both `TuningResult` and `SearchMetadata` are frozen (`@dataclass(frozen=True)`). A tuning result is a record of what happened — mutating it would destroy the audit trail.

### 3. `TuningConfig` is also frozen

A `TuningConfig` is a declared policy. The whole reason for putting configs in their own file is to make them the agreed-upon search definition. If `tune()` or any caller could mutate the config mid-run, the guarantee that "what we ran" matches "what the config says" would be lost.

`TuningConfig` carries seven fields: `name`, `pipeline`, `search_class`, `param_space`, `scoring`, `n_iter` (defaults to `None` for Grid), and `random_state` (defaults to 42).

### 4. MLflow logging is the caller's job, not `tune()`'s

`tune()` is pure: it runs a search and returns a result. It does not log to MLflow. The training script that calls `tune()` is responsible for logging whatever it wants from the `TuningResult` to MLflow.

This keeps `tuner.py` testable without an MLflow setup. It also respects the separation between "computing a result" and "recording that result somewhere" — the latter is an output side effect, the former is the actual work.

### 5. AUC as the scoring callable

All three configs use `scoring="roc_auc"`.

AUC measures the model's *ranking quality*: does it tend to score defaulters higher than non-defaulters, regardless of where the threshold is drawn? Precision and recall measure *decision quality* at a fixed threshold.

ADR 015 establishes that threshold is a business lever, not an algorithm detail — `selector.py` will set the threshold based on business cost asymmetries after tuning completes. Tuning on a threshold-independent metric keeps that lever free. If we tuned on precision or recall at threshold 0.50, we would be optimising for one specific decision rule, and the threshold-policy decision would be reduced to "use 0.50."

Log loss and Brier score are also threshold-independent, but they measure *calibration* — whether predicted probabilities are accurate as probabilities. AUC measures ranking, which is more directly tied to what the credit risk model needs to do (sort applicants by default risk). Calibration is captured in evaluation (per ADR 015) but not used for tuning.

### 6. Stratified k-fold with k=5 (closes Q6)

The shared cross-validator is a module-level constant in `tuner.py`:

```python
CV = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
```

**Stratified** rather than plain k-fold: the target classes are imbalanced (`pif` is the majority, `chgoff` the minority). Plain k-fold could produce folds with very different class ratios, which inflates variance in the CV estimate. Stratified k-fold preserves the class ratio in every fold, which is the right behaviour for any imbalanced classification problem.

**k=5** rather than k=10 or k=3: k=5 is the conventional default for a reason. k=3 produces high-variance estimates (each fold is large but the average over only three folds is noisy). k=10 is more expensive (10 fits per parameter combination instead of 5) for marginal accuracy gain. The SBA dataset is large enough that 5 folds give stable estimates, and Random search with n_iter=20 × 5 folds = 100 fits is already a substantial compute budget.

**shuffle=True**: without shuffling, `StratifiedKFold` preserves row order within strata. If the data has any temporal structure (and SBA loan data does — applications come in over time), unshuffled folds can introduce subtle leakage where earlier rows train and later rows test. Shuffling breaks this.

**random_state=42**: makes the splits reproducible.

### 7. Search strategy per model family

- **Logistic regression** → `GridSearchCV`, 5 × 2 × 2 = 20 combinations (`C`, `penalty`, `class_weight`). Exhaustive because the space is small enough to enumerate.
- **Random forest** → `RandomizedSearchCV`, `n_iter=20`. The full space (n_estimators × max_depth × min_samples_split × min_samples_leaf × max_features × class_weight) is too large to enumerate. Random sampling gives broader coverage than a coarse grid.
- **XGBoost** → `RandomizedSearchCV`, `n_iter=20`. Eight hyperparameters, mostly continuous-ish. Same reasoning as RF.

For Random search, scipy distributions (`randint`, `uniform`, `loguniform`) are used for continuous-ish parameters; lists are used for categorical or special-value parameters (e.g. `max_features=["sqrt", "log2", 0.5]`).

`learning_rate` for XGBoost uses `loguniform(0.01, 0.3)` because learning rate is multiplicative — going from 0.01 to 0.03 is a bigger change in regularisation than from 0.1 to 0.12. Log-uniform sampling gives every order of magnitude equal attention.

### 8. Bayesian search deferred to v2

Bayesian hyperparameter search (e.g. Optuna, scikit-optimize) is more sample-efficient than random search for continuous parameter spaces — it learns from previous trials to focus on promising regions.

Deferred for v1 because:
- It introduces a new dependency and a new API surface.
- The benefit is uncertain without a v1 baseline to measure against.
- Random search with n_iter=20 is a defensible starting point; the question "is Bayesian search worth the added complexity?" is only answerable once we have v1 results to compare to.

### 9. `scoring` is a `TuningConfig` field; `cv` is a module constant

Both `scoring` and `cv` are currently identical across all three configs ("roc_auc" and the shared `CV` object). The decision about which to put in the config is not about current uniformity but about *foreseeable change drivers*.

**`scoring` belongs in the config** because the monitoring layer (the project's core feature) is expected to produce specific reasons to change it. Drift patterns may surface that a different metric better captures the model's degradation. There is a concrete, named feedback loop that will drive this.

**`cv` belongs in `tuner.py` as a constant** because there is no equivalent driver for changing the cross-validation strategy. Time-series CV might matter someday, but it is not tied to a specific feedback loop in this project's design. YAGNI applies — add the field when an actual reason appears.

The principle: configuration fields are justified by *concrete change drivers*, not by *hypothetical flexibility*.

### 10. `random_state` on `TuningConfig`; `n_jobs` hardcoded in `tune()`

Both fields control runtime behaviour, but they serve different concerns.

**`random_state` is a reproducibility concern.** It belongs in declared policy because reproducibility audits require knowing exactly which seed produced which result. Different configs might also need different seeds — for example, to run the same config twice with different seeds to check sensitivity.

**`n_jobs` is a performance concern.** It is purely about how many CPU cores the search uses. No config should declare a specific `n_jobs` — the only sensible values are -1 (use all cores) for production and 1 (single-threaded) for debugging. The latter is a developer-time intervention, not a policy declaration. Hardcoded as `n_jobs=-1` in `tune()`.

The principle: reproducibility settings are policy; performance settings are implementation.

---

## Consequences

**For `tuner.py`:** The file defines three dataclasses (`SearchMetadata`, `TuningConfig`, `TuningResult`) and one function (`tune`). All dataclasses are frozen. The function is pure — no MLflow side effects, no global state mutation. The shared `CV` constant lives at module level.

**For `tuning_configs.py`:** The file imports `TuningConfig` from `tuner.py`, `build_pipeline` from `trainer.py`, and `NUMERICAL_FEATURES` / `CATEGORICAL_FEATURES` from `dataset_builder.py`. It exports three `TuningConfig` instances. The file is pure data — no functions, no logic, just declared search configurations.

**For training scripts (not yet written):** A training script imports the relevant config, calls `tune(X, y, config)`, receives a `TuningResult`, and chooses what to do with it. Logging to MLflow, saving the fitted estimator, comparing to other models — all are caller responsibilities.

**For `selector.py` (future):** It will receive `TuningResult` objects from multiple tuning runs and compare their `best_score` and `best_estimator` values. The structured `TuningResult` makes this comparison straightforward.

**For `baseline_saver.py` (future):** Once a model is selected, the baseline saver snapshots the training distribution. The baseline saver does not interact with `TuningResult` directly — it operates on the fitted pipeline that the selector chose.

**For testing:** `tuner.py` needs tests covering: `tune()` returns a `TuningResult` with all five fields populated; the search strategy branch correctly handles both `GridSearchCV` and `RandomizedSearchCV` configs; `SearchMetadata` fields are populated correctly. `tuning_configs.py` needs lightweight tests that simply import the three configs and assert each is a valid `TuningConfig` instance with expected `search_class` and `n_iter` values.

**For the assumptions tracker:** Q6 (why stratified k-fold, why k=5) is closed by this ADR. No new questions are opened — this ADR commits to specific choices for v1; alternatives like Bayesian search are deferred but not held open as questions.

**For interview defensibility:** Every design decision has a documented rationale. The split between mechanics and policy, the choice of AUC, the per-model search strategy, the immutability of configs and results — each is a defensible choice with a stated alternative considered.

---

## Open questions opened by this ADR

None for v1. The deferred items (Bayesian search, time-series CV) are noted as v2 candidates in this ADR but not added to the tracker — they have no concrete change driver in the current scope.
