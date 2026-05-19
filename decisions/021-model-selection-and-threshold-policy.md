
# 021 — Model Selection and Threshold Policy

**Date:** 2026-05-21
**Component:** Model layer (`src/models/selector.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR introduces a new file, `src/models/selector.py`. It sits between the tuner's output (three `TuningResult` objects) and the deployable artifact (a fitted pipeline plus a chosen threshold plus audit metadata).

This ADR depends on:
- **ADR 015** — Threshold is a business lever, not an algorithm detail. ADR 015 deferred the threshold-setting design to "the selector ADR." This is that ADR.
- **ADR 018** — Tuning is pure: `tune()` returns a `TuningResult`, doesn't log, doesn't decide. The selector consumes those results.
- **ADR 020** — A held-out validation set distinct from training and test data exists. The selector operates on it.

This ADR closes **Q5** further than ADR 015 did, in the sense that the threshold-related half of Q5 ("how is the model judged at decision time") is now answered. The full metric-set debate within Q5 (which metrics matter beyond v1) remains open.

---

## Context

After tuning, three `TuningResult` objects exist — one per model family. Each carries a fitted pipeline and a CV score from the tuning search. Nothing yet:

- Compares the three models head-to-head on data outside the tuning loop
- Chooses a deployable threshold for the winner
- Produces a structured record of *which* model won, *why* it won, and *what* assumptions were used

These three concerns are tightly coupled. A model is "best" only relative to a decision rule (the threshold). A threshold is "best" only relative to a cost framework. Splitting these into separate files would mean the selection and threshold decisions get made in different places, which is exactly the failure mode where audit trails fragment and assumptions leak.

The selector is the file that owns this coupled decision.

Three categories of design decision are bundled in this ADR because they are mutually constraining:

1. **What data is selection performed on?** (validation set vs CV scores vs test set)
2. **How are models compared?** (AUC vs expected cost vs F1 vs combined criteria)
3. **How is the threshold set?** (fixed default vs metric-maximisation vs business cost)

A coherent answer to one constrains the others. Bundling them keeps the through-line visible.

---

## Decision

### 1. Selection operates on the validation set, not CV scores or the test set

The selector receives `(X_val, y_val)` (from the splitter per ADR 020) and runs each tuning result's `best_estimator` on it to compute fresh metrics. CV scores from the tuning step are recorded but not used for cross-family selection.

The alternative — using `TuningResult.best_score` directly as the comparison metric — was rejected. CV scores are already optimistic: each is the score of the *winning* hyperparameter combination, selected because it scored well. Using the same number to choose between families stacks optimism.

The test set is not touched by the selector. It is reserved for the final honest audit after selection is complete. Any modelling decision that uses the test set destroys the test set's purpose.

### 2. Selection criterion is lowest expected cost on the validation set, with AUC as tie-break

For each candidate model:
- Compute predicted probabilities on `X_val`
- Sweep thresholds across a grid `[0.01, 0.99]` step `0.01`
- For each threshold, compute expected cost: `FN_count × cost_fn + FP_count × cost_fp`
- Record the cost-optimal threshold and the corresponding expected cost

The winner is the candidate with the *lowest* cost-optimal expected cost. Ties (rare on real data, possible on small test fixtures) are broken by higher AUC.

The alternative — selecting by AUC alone, then setting a threshold for the winner — was rejected for consistency. If a cost framework is introduced to set thresholds, ignoring that framework for selection means *"we care about cost enough to draw a line, but not enough to choose a model"* — a contradiction. The cost framework either matters or it doesn't.

This means each candidate gets its own cost-optimal threshold during comparison, not just the winner. This is more rigorous: each model is compared at *its best possible decision rule*, not at an arbitrary default like 0.50.

### 3. Threshold policy: business cost asymmetry with hand-chosen ratio

The selector receives `cost_fn` and `cost_fp` as explicit function parameters. These encode the business framing:
- `cost_fn` — cost of a false negative (approving a defaulter)
- `cost_fp` — cost of a false positive (rejecting a good applicant)

In credit risk, FN is typically more expensive than FP — approving someone who defaults is a direct financial loss, while rejecting a good applicant is opportunity cost. A v1 default of `cost_fn=5, cost_fp=1` encodes this asymmetry.

Three sources for these numbers were considered:

- **Real Datatroniq P&L data** — Doesn't exist (fictional company).
- **Compute from SBA data directly** — Conflates known loss-given-default (the data has it) with unknown counterfactual revenue from rejected applicants. Asymmetric uncertainty.
- **Hand-chosen ratio with documented reasoning** (chosen) — Honest about its own placeholder status. Documented in this ADR. Re-estimation is deferred to v2 once monitoring surfaces reasons to update.

The cost ratio is recorded on `SelectionResult.cost_ratio` for audit. Future monitoring may flag that the v1 assumption no longer reflects business reality, at which point a v2 ADR will revise it.

### 4. Logging happens in the orchestration script, not in `selector.py`

Consistent with ADR 018's principle for `tuner.py`: mechanics in the file, logging in the caller. The selector is pure — it returns a `SelectionResult` with everything the orchestration script needs to log, and the script handles MLflow.

This keeps the selector testable without MLflow setup and preserves the testability separation established by ADR 018. The atomicity concern (could selector and logger record subtly different state?) is solved by having the selector return a comprehensive `SelectionResult` that the script logs as a single unit.

### 5. Output is a frozen `SelectionResult` dataclass with `SelectionMetadata` sub-dataclass

Same pattern as `TuningResult` / `SearchMetadata` from ADR 018.

`SelectionResult` (frozen, 7 fields):
- `best_estimator: Pipeline` — the winning fitted pipeline
- `best_model_name: str` — the family name (`"logistic_regression"`, etc.)
- `threshold: float` — the chosen decision threshold
- `cost_ratio: tuple[float, float]` — the `(cost_fn, cost_fp)` used
- `validation_metrics: dict[str, float]` — six metrics at the chosen threshold (precision, recall, ROC AUC, log loss, Brier score, expected cost)
- `comparison: dict[str, dict]` — per-model breakdown showing each candidate's cost-optimal threshold and metrics
- `selection_metadata: SelectionMetadata` — audit trail

`SelectionMetadata` (frozen, 6 fields):
- `run_started_at: str` — UTC ISO-8601 timestamp
- `run_duration_seconds: float`
- `n_candidates_considered: int`
- `candidate_names: list[str]`
- `validation_set_size: int`
- `threshold_search_grid: str` — human-readable description (e.g. `"0.01..0.99 step 0.01"`)

Both dataclasses are frozen. A selection result is a record of what happened; mutating it destroys the audit trail. A selection metadata object is read-only audit info; mutating it has no legitimate use case.

### 6. Threshold sweep uses vectorised numpy, not a Python loop

The threshold sweep is the hot path. With ~50,000 validation rows and 99 candidate thresholds, a Python loop would be 50× slower than the vectorised equivalent without producing different results.

The vectorisation is straightforward and readable:
```python
y_pred = (proba[:, None] >= THRESHOLD_GRID[None, :]).astype(int)
fn = ((y_val.to_numpy()[:, None] == 1) & (y_pred == 0)).sum(axis=0)
fp = ((y_val.to_numpy()[:, None] == 0) & (y_pred == 1)).sum(axis=0)
costs = fn * cost_fn + fp * cost_fp
```

Numpy broadcasting handles the cross-product of rows and thresholds in a single operation. The readability cost is minimal; the runtime saving is real on production-scale data.

### 7. Threshold grid is `[0.01, 0.99]` step `0.01`

99 candidate thresholds. The endpoints `0.0` and `1.0` are excluded because they correspond to "approve nobody" and "approve everybody" — valid points on the cost curve but useless decision rules in practice.

Step size `0.01` is fine enough that adjacent thresholds give near-identical expected costs (the cost curve is locally smooth) without being wastefully fine. Finer steps (e.g. `0.001`) would 10× the computation for marginal precision improvement.

The grid is a module-level constant in `selector.py`: `THRESHOLD_GRID = np.linspace(0.01, 0.99, 99)`. Centralising it means all selector internals search the same space.

### 8. Each candidate gets its own cost-optimal threshold during comparison

This is a direct consequence of decision 2. The selector doesn't only compute the winner's threshold — it computes every candidate's cost-optimal threshold and records all of them in `comparison`. This makes the comparison field genuinely useful for audit: a future reader can see what each candidate could have achieved at its own best decision point, not just at an arbitrary fixed threshold.

The cost is moderate: three threshold sweeps instead of one. With vectorisation, the total runtime is still trivial.

---

## Consequences

**For `selector.py`:** A new file containing two frozen dataclasses, one private helper (`_find_cost_optimal_threshold`), one public function (`select_best_model`), and one module-level constant (`THRESHOLD_GRID`). The file is pure — no MLflow side effects, no I/O.

**For `tuner.py`, `tuning_configs.py`, `evaluator.py`, `dataset_builder.py`, `data_splitter.py`:** No changes. The selector is a downstream consumer.

**For orchestration scripts (to be written):** The script calls the splitter, then `tune()` three times, then `select_best_model()` once with the results. Logging to MLflow happens after `select_best_model()` returns, using fields from the `SelectionResult` directly.

**For `evaluator.py` on the test set:** After selection, the orchestration script calls `evaluator.predict()` and `evaluator.evaluate()` on `(X_test, y_test)` using `result.best_estimator` and `result.threshold`. This is the audit moment.

**For `baseline_saver.py` (future):** Receives `result.best_estimator` to snapshot the training distribution.

**For `registry.py` (future):** Receives `result.best_estimator` and `result.threshold` to persist the deployable artifact.

**For testing:** `tests/test_models/test_selector.py` covers nine failure modes spanning output shape, selection correctness, threshold correctness, and metadata accuracy. The fitted-results fixture in `conftest.py` provides three predictable classifiers (two `DummyClassifier` variants and one `LogisticRegression`) to drive deterministic tests of selection logic.

**For interview defensibility:** Every selection decision has a documented rationale. The choice of cost-based selection over AUC-based, the choice of vectorised numpy over a loop, the choice of three-way splits, the choice of frozen dataclasses — each is a defensible choice with a stated alternative considered.

**For the assumptions tracker:** Q5 is more thoroughly addressed but not closed. The threshold-policy half of Q5 is resolved by this ADR; the broader metrics debate remains open for v2.

---

## Open questions opened by this ADR

- **Q14 (or next available number) — Cost ratio re-estimation under drift.** The v1 cost ratio (`cost_fn=5, cost_fp=1`) is a documented placeholder. When monitoring surfaces signals that business conditions have shifted, what process re-estimates the ratio? Deferred to v2.

- **Q15 — Threshold stability under drift.** When the data distribution shifts (FY2020+ data arriving), the v1 threshold computed on FY2010–2019 validation data may no longer minimise expected cost. What signals trigger threshold re-computation, and how is the new threshold derived without contaminating the test set? Deferred to v2.

Both questions are added to the assumptions tracker as v2 candidates with concrete change drivers (monitoring signals).