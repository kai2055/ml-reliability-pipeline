
# 016 — Model Layer Pre-Processing Seam

**Date:** 2026-05-15
**Component:** Model layer (`src/models/`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR introduces a new file, `src/models/dataset_builder.py`. The file sits between the data layer's output (a clean, typed DataFrame) and the model layer's input (`X` and `y`).

It also supersedes part of **ADR 004**. ADR 004 originally said the transformer should drop loan rows that don't map cleanly to a "paid" or "defaulted" outcome (the bucket logic). That row-dropping work moves out of the transformer and into `dataset_builder.py`. The schema decisions and validator decisions in ADR 004 are unchanged — only where the row filtering happens is different.

---

## Context

The data layer was built to do one thing: take the raw CSV and produce a clean, typed DataFrame. Strings get normalised, dates get parsed, numbers get coerced. The data layer does not decide what's a feature, what's a target, or which rows are useful for modelling — it just makes sure the data is faithfully represented.

When ADR 004 was written, the bucket-and-drop logic for `loanstatus` was placed in the transformer. At the time this seemed reasonable: the transformer was already touching the `loanstatus` column to normalise the formatting, so adding the drop logic there was convenient.

The problem only became visible when the model layer started getting built out. Dropping rows where `loanstatus` is `curr` or `delinq` is not a data cleaning step — it's a modelling decision. A different model (multi-class classification, survival analysis, regression on charge-off amount) would keep some of those rows. The transformer was quietly making a decision that belongs to the model layer.

Three other decisions were also sitting in nobody's file:

- **Target derivation.** Turning `loanstatus` into a 0/1 column (`pif → 0`, `chgoff → 1`) is a modelling decision. A different problem would map it differently.
- **Feature selection.** Which of the 42 columns are features at all, and which are identifiers or outcomes, is a modelling decision. The schema knows dtypes, not roles.
- **Feature grouping.** Within features, which are numerical (to be scaled) and which are categorical (to be encoded) is a modelling decision. `revolverstatus` is an integer in the schema but a 0/1 flag for modelling. `jobssupported` is also an integer but is a real continuous quantity.

All four decisions translate a clean general-purpose DataFrame into the specific shape this binary classifier needs. They belong together, in one file, in the model layer.

---

## Decision

A new file is created: `src/models/dataset_builder.py`.

This file is the single bridge between the data layer and any model-layer code that needs `X` and `y` — `trainer.py`, `tuner.py`, `selector.py`, `baseline_saver.py`. It takes the clean DataFrame from the data layer and returns `X` (features) and `y` (target), ready to be passed to `Pipeline.fit()`.

The file owns four responsibilities:

**1. Row filtering.** Rows where `loanstatus` is not `pif` or `chgoff` are dropped. This implements ADR 004's bucket logic in the model layer: active loans (`curr`, `delinq`, `pstdue`, `deferd`), ambiguous resolutions (`clsln`, `liquid`, `purch(notc/o)`, `soldnc`), and unresolved values (`cancld`, `commit`) are removed. Only rows with a resolved outcome remain.

**2. Target derivation.** A new binary column is built from `loanstatus`: `pif → 0`, `chgoff → 1`. The original `loanstatus` column is then dropped, so it cannot accidentally end up in `X`.

**3. Feature selection.** An explicit list of columns is declared as the v1 feature set. Everything not on the list is dropped from `X`. The specific list and the reasoning for each exclusion is documented in ADR 017.

**4. Feature grouping.** The feature set is split into two lists: numerical (to be scaled) and categorical (to be encoded). `trainer.build_pipeline()` reads these lists to build its `ColumnTransformer`. The specific groupings are documented in ADR 017.

The file produces `X`, `y`, and two module-level constants — `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES` — which other model-layer files import so the feature definitions exist in exactly one place.

---

## Consequences

**For the transformer:** It gets simpler. The bucket logic ADR 004 originally placed in it is removed. Its job is now bounded to type coercion, string normalisation, and date parsing — nothing else. All 36 existing tests in the data layer continue to pass, because they test the mechanical transformations, which don't change.

**For the validator:** Nothing changes. `check_usable_rows` still runs on the post-transform DataFrame, before any filtering. If a dataset doesn't have enough `pif` or `chgoff` rows (under 12% or under 50,000 absolute), it's rejected as fatal per ADR 005, before any model code runs.

**For `trainer.py`:** The function signature of `build_pipeline()` doesn't change — it still takes column lists as arguments. What changes is where those lists come from: `dataset_builder.py` exports them, `trainer.py` imports them. The lists are no longer the caller's responsibility to invent. This closes a real gap — `build_pipeline()` was previously unusable against real data because nobody had defined the lists.

**For `tuner.py`, `selector.py`, `baseline_saver.py`:** Each imports `dataset_builder.py` to get `X`, `y`, and the feature group constants. There is one source of truth for "what counts as a feature in v1."

**For testing:** `dataset_builder.py` needs its own tests in `tests/test_models/test_dataset_builder.py`. The tests should cover: row filtering keeps only `pif` and `chgoff` rows, target derivation produces 0/1 values correctly, `loanstatus` is not in `X` after derivation, excluded columns are not in `X`, and the numerical and categorical lists together cover all columns in `X` with no overlap.

**For separation of concerns:** The data layer's job is now clean — produce a faithful, typed DataFrame. The model layer owns every decision about what that data means for this specific modelling problem. This boundary holds across any future model variations.

**For the assumptions tracker:** Q1 (feature pruning) and Q2 (numerical vs categorical) are closed by ADR 017, which is the policy ADR that depends on this architectural one.