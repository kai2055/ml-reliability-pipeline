# 019 — Logistic Regression API Update (sklearn 1.8 deprecation)

**Date:** 2026-05-18
**Component:** Model layer (`src/models/tuning_configs.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR supersedes part of **ADR 018**. ADR 018 specified the logistic regression tuning configuration with:
- `solver="liblinear"`
- `param_space` including `"model__penalty": ["l1", "l2"]`

These choices are no longer compatible with current sklearn. This ADR documents the migration to the sklearn 1.8+ API. The rest of ADR 018 — the architecture, the search strategies for RF and XGB, the scoring choice, the CV strategy — remains in force.

Append-only: ADR 018 is not edited. The audit trail is the dated sequence — ADR 018 dated 2026-05-17, ADR 019 dated 2026-05-18, with ADR 019 explicitly superseding only the logreg-specific decisions.

---

## Context

When `test_logreg_config_smoke_run` was first executed, sklearn emitted a `FutureWarning`:

> `'penalty' was deprecated in version 1.8 and will be removed in 1.10. To avoid this warning, leave 'penalty' set to its default value and use 'l1_ratio' or 'C' instead.`

The new API replaces the `penalty` parameter with `l1_ratio`, which expresses regularisation type as a continuous mixing parameter:
- `l1_ratio=0.0` — pure L2 regularisation (equivalent to the old `penalty="l2"`)
- `l1_ratio=1.0` — pure L1 regularisation (equivalent to the old `penalty="l1"`)
- Values between 0.0 and 1.0 — elastic-net (a blend of L1 and L2)

This API change requires the `saga` solver instead of `liblinear`, since `saga` is the sklearn solver that supports the full elastic-net family.

Three options were considered:

1. **Pin sklearn to a version that still supports `penalty`.** Rejected — postpones the problem and risks missing other fixes.
2. **Defer the change until sklearn 1.10 forces it.** Rejected — would result in surprise CI breakage when sklearn upgrades. The deprecation warning is a clear signal to migrate now.
3. **Migrate the config now.** Chosen.

The migration preserves the original v1 search semantics:
- The original 5 × 2 × 2 = 20 grid is preserved.
- `l1_ratio=[0.0, 1.0]` covers the same conceptual space as `penalty=["l1", "l2"]` — pure L2 and pure L1, no blend.
- Elastic-net values (`l1_ratio` strictly between 0.0 and 1.0) are deferred to v2 if monitoring surfaces a reason to explore them.

---

## Decision

The `LOGREG_TUNING_CONFIG` in `src/models/tuning_configs.py` is updated:

```python
LOGREG_TUNING_CONFIG = TuningConfig(
    name="logistic_regression",
    pipeline=build_pipeline(
        NUMERICAL_FEATURES,
        CATEGORICAL_FEATURES,
        LogisticRegression(
            solver="saga",
            max_iter=2000,
            random_state=42,
        ),
    ),
    search_class=GridSearchCV,
    param_space={
        "model__C": [0.01, 0.1, 1.0, 10.0, 100.0],
        "model__l1_ratio": [0.0, 1.0],
        "model__class_weight": [None, "balanced"],
    },
    scoring="roc_auc",
)
```

Three specific changes from ADR 018:

1. `solver="liblinear"` → `solver="saga"`.
2. `max_iter=1000` → `max_iter=2000`. `saga` is iterative and needs more iterations than `liblinear` to converge reliably, especially with strong regularisation.
3. `"model__penalty": ["l1", "l2"]` → `"model__l1_ratio": [0.0, 1.0]`.

The grid size (5 × 2 × 2 = 20 combinations) and the conceptual search space (pure L2 vs pure L1, with five `C` values and two `class_weight` values) are preserved.

---

## Consequences

**For `tuning_configs.py`:** Only the logreg config is touched. RF and XGB configs are unchanged.

**For `tuner.py`:** No changes. `tune()` is config-agnostic.

**For tests:** `test_logreg_config_smoke_run` now passes without the deprecation warning. No new tests are needed — the existing test surface already verifies that the config runs end-to-end and produces a valid AUC.

**For runtime:** `saga` is slower than `liblinear` for small datasets but scales better and supports a wider range of penalties. For the SBA dataset's scale (>50k rows), the runtime difference is acceptable. `max_iter=2000` increases the per-fit ceiling but does not significantly change typical runtime since most fits converge well before the ceiling.

**For interview defensibility:** The migration is documented as a response to a specific sklearn API change, with the v1 semantics preserved exactly. Future readers understand that the move to `saga` and `l1_ratio` was forced by deprecation, not a methodological choice. The deferred elastic-net exploration (`l1_ratio` values between 0.0 and 1.0) is left as a v2 candidate.

**For the assumptions tracker:** No new questions are opened. The migration is mechanical, not a re-opened design question.

---

## Open questions opened by this ADR

None. The migration is a direct response to a deprecation, with the original v1 semantics preserved.
