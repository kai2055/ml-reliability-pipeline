
# 020 — Data Splitter Architecture

**Date:** 2026-05-21
**Component:** Model layer (`src/models/data_splitter.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR introduces a new file, `src/models/data_splitter.py`. It sits between the data layer's output (clean `(X, y)`) and the model layer's downstream consumers (tuner, selector, evaluator).

This ADR depends on:
- **ADR 002** — Established that FY2010–2019 is the training data and FY2020–Present is the simulated production data. The splits described in this ADR happen *inside* FY2010–2019; FY2020–Present is never touched by modelling code.
- **ADR 016** — Established `dataset_builder.py` as the source of `(X, y)`. The data splitter is its downstream consumer.

This ADR is a precondition for ADR 021 (model selection and threshold policy), which requires a held-out validation set distinct from both training and final test data.

---

## Context

Before this ADR, the model layer produced a single `(X, y)` from `dataset_builder.py`. That output was passed directly to `tune()`, which performed its own internal cross-validation. There was no held-out test set, no validation set for non-CV decisions, and no architectural place to define one.

This was acceptable while the model layer was just "tune and report CV scores." It is not acceptable for two reasons that became unavoidable when the selector was designed:

1. **CV scores are optimistic for model selection across families.** Each tuning run picks the winning hyperparameter combination via CV, which means `best_score` already reflects a selection process. Using the same `best_score` to pick between model families stacks selection optimism on top of selection optimism. A genuinely held-out validation set is the standard fix.

2. **Threshold policy needs data the threshold wasn't fit on.** The selector's threshold-setting step (per ADR 021) searches a grid of thresholds to minimise expected business cost. That search must operate on data that was not seen during tuning — otherwise the threshold inherits all the optimism of the tuning process.

Two distinct held-out partitions are needed:
- **A validation set** — used by the selector for model selection and threshold-setting
- **A test set** — used once, at the very end, to produce an honest performance report

The test set is sacred: it is the audit. If any modelling decision uses it, the final report is no longer honest.

---

## Decision

A new file is created: `src/models/data_splitter.py`. It exposes a single function:

```python
def split_train_val_test(
    X: pd.DataFrame,
    y: pd.Series,
    val_size: float = 0.15,
    test_size: float = 0.15,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    ...
```

The function returns a 6-tuple `(X_train, X_val, X_test, y_train, y_val, y_test)`, matching sklearn's `train_test_split` conventions.

Four specific decisions:

**1. Separate file, not folded into `dataset_builder.py`.**

`dataset_builder.py`'s job is *what does the data look like for this modelling problem* — filter rows, derive target, select features, group features. The splitter's job is *how do we partition data for evaluation* — an entirely different concern that changes for entirely different reasons. Folding splitting into `dataset_builder.py` would couple a modelling protocol decision to a data shape decision.

**2. Three-way split (train / val / test).**

ADR 021's design requires a validation set distinct from training. The test set must remain untouched until final evaluation. Two-way splits (train/test only) can't provide both. K-fold-on-everything is too expensive and conflates model selection with hyperparameter tuning.

**3. Stratified, not random.**

The target classes are imbalanced — roughly 20% defaults in the SBA data. Random splitting can produce partitions with skewed class ratios, which inflates variance in the AUC and cost estimates and degrades the validation set's usefulness for selection. Stratified splitting preserves the class ratio in every partition by construction.

**4. Test set extracted first, then train/val from remainder.**

Two sequential `train_test_split` calls produce the three splits. The order matters subtly:
- **Test first, then train/val from remainder** (chosen): the test set is defined once and never reshuffled. Whatever rows are extracted as test stay as test for the entire selection process.
- **Train first, then val/test from remainder**: the test set's specific rows depend on a second split operation, which adds a small layer of indirection without benefit.

The math is equivalent in expectation, but the chosen order matches the intuition that "the test set is sacred" — it's the first thing defined and the last thing touched.

**5. 70 / 15 / 15 as defaults.**

The training set is the most data-hungry — it feeds k-fold CV and the model fitting. Validation and test sets only need enough rows for stable estimates of AUC, expected cost, and the evaluator's other metrics. With the FY2010–2019 dataset at ~50,000 rows, 15% gives ~7,500 rows per held-out set — comfortably enough for stable point estimates without starving training.

**6. `random_state=42` for reproducibility.**

Same principle as everywhere else in the project: every randomness source has a seed; every seed is documented.

---

## Consequences

**For `dataset_builder.py`:** No changes. It still produces `(X, y)` from the clean DataFrame. The splitter is its downstream consumer, not a modification to it.

**For `tuner.py`:** No changes. `tune()` still receives `(X_train, y_train)` and performs internal k-fold CV. The fact that the input is now `X_train` instead of the full `X` is transparent to the tuner.

**For `selector.py`:** Receives `(X_val, y_val)` from the splitter to use for cost-optimal threshold-setting and model comparison.

**For `evaluator.py` on the test set:** Receives `(X_test, y_test)` for final reporting. This is the audit moment — touched once.

**For orchestration scripts (to be written):** The script that ties everything together calls the splitter once, near the top of the pipeline, and threads the six partitions through to their respective consumers. No other file is responsible for splitting.

**For testing:** The splitter has its own test surface (`tests/test_models/test_data_splitter.py`) covering size proportions, stratification preservation, disjoint indices, and reproducibility. Other tests that need split data can reuse the splitter rather than constructing splits inline.

**For monitoring:** The splitter operates only on FY2010–2019. FY2020–Present data is the responsibility of the monitoring layer; it is never split, never used for training or selection. This boundary is non-negotiable per ADR 002.

**For the assumptions tracker:** No new questions are opened by this ADR. The decisions are mechanical applications of standard practice given the constraints from ADR 002 and the requirements set by ADR 021.

---

## Open questions opened by this ADR

None for v1. Larger splits (e.g. 80/10/10) and time-aware splitting (TimeSeriesSplit) are deferred to v2 if monitoring surfaces signals that v1's random stratified split is missing temporal effects. Neither is held open as a tracker question — both have v2 paths but no concrete change driver in v1.