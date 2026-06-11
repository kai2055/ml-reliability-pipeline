# ADR 024 — Training Pipeline Orchestration

**Date:** 2026-05-24
**Component:** `scripts/run_training.py`
**Status:** Decided

---

## Relationship to prior ADRs

This ADR documents the orchestration script that wires together every file built
in the model layer. It is not a new component — it is the conductor. It calls
the nine model-layer files in fixed order and produces the two artifacts the rest
of the system depends on: a trained pipeline and a baseline snapshot.

This ADR depends on:
- **ADR 016 / ADR 017** — `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES` are
  imported from `dataset_builder.py`. The orchestration script does not re-
  declare them.
- **ADR 021** — The cost ratio (`COST_FN = 5.0`, `COST_FP = 1.0`) used by the
  selector is a placeholder grounded in the conservative end of the 5–10x range.
  The orchestration script inherits that decision.
- **ADR 022 / ADR 023** — The registry and baseline saver define their own
  overwrite guards and artifact formats. The orchestration script calls them; it
  does not reimplement their logic.

---

## Context

The model layer had nine files, each doing one job. Nothing ran them in sequence.
The orchestration script is the answer to: *how does the whole pipeline execute
as one operation?*

Five design questions were settled before and during the build.

---

## Decision

### Q1 — Location: `scripts/run_training.py`

The script lives at `scripts/run_training.py`, not inside `src/`. `src/` contains
importable library code. This script is a runnable entry point — it consumes
`src/`, it is not part of it. A `sys.path` insert at the top makes `src/`
importable without pip-installing the project. This is a deliberate pragmatic
choice for a project not yet packaged, commented in the script so the intent
is visible to a future reader.

### Q2 — Inputs: uppercase constants, not argparse

All inputs — data path, cost ratio, output directories — are declared as
`UPPERCASE` constants in a fenced config block at the top of the script. They
are fixed. They do not vary run-to-run. Argparse and YAML config files solve a
flexibility problem that does not exist here; adding them would be machinery for
a need that has not arrived.

Named constants also communicate intent: these values are fixed by design, not
by accident. `YAGNI` drives this decision, the same principle that has governed
every equivalent choice in the project.

### Q3 — MLflow: one flat run, selected model only

One MLflow run per pipeline execution. The unit of comparison across runs is the
whole pipeline's outcome — the selected model's test metrics — not the internal
tuning search. Logging three sets of nested child runs would fragment that
comparison without adding value to the question a future engineer actually asks:
*which pipeline run produced the best model, and what did it find?*

What gets logged: input parameters (data path, row counts, cost ratio, winning
model name, best hyperparameters, decision threshold), tuning scores for all
three candidates, and final validation and test metrics. Artifact files are not
logged to MLflow — they are already persisted to disk by `registry` and
`baseline_saver`. No duplicate source of truth.

Errors are not logged to MLflow. A crashed run has no completed run to log into.

### Q4 — Testing: one integration test, slow-marked

The orchestration script is the most integration-sensitive file in the project.
A mocked unit test would only verify that the code is the code — it would not
catch a wiring failure. Running nothing means the wiring is verified once,
manually, and trusted forever after. Neither is acceptable.

One integration test, marked `@pytest.mark.slow`, runs the full script on a
small data slice and asserts the wiring contract: the script runs start to
finish, the expected artifacts appear on disk, and those artifacts load back
correctly. It does not assert model quality. This test is not yet written — it
is the remaining open item before this ADR is fully closed.

### Q5 — Stage ordering: validate after transform

The validator expects post-transform data. Raw `loanstatus` arrives as
`'P I F'` / `'CHGOFF'`; the validator expects `'pif'` / `'chgoff'`. The fixed
stage order is:
load → transform → validate → build_dataset → split → tune
→ select → evaluate → save_model → compute_baseline → save_baseline
→ log to MLflow

This constraint is non-obvious — running validate on raw data produces zero
usable rows with no error, which is exactly the class of silent failure the
project exists to prevent. The ordering is fixed here and must not be changed.

---

## First-run findings

Two bugs surfaced on the first end-to-end run against real data and were fixed
before the clean run completed.

**1. `pd.NA` in categorical features reaching sklearn**

The transformer coerces all string columns to pandas `StringDtype`, which
represents missing values as `pd.NA` rather than `NaN`. These `NA` values rode
through `build_dataset` into sklearn's `OneHotEncoder`, which cannot sort a
mix of `str` and `NAType` and raised a `TypeError`.

Fix: `_fill_missing_categoricals()` added to `dataset_builder.py`, called after
`_select_features()`. The fix lives in the dataset builder because the decision
of *what to do with missing categorical values for the purpose of modelling* is
semantic — it belongs to the ML-facing layer, not to the transformer whose job
is mechanical normalisation. Missing values are filled with the string
`"missing"`, preserving them as an explicit category the model can learn from.

**2. Unknown categories during cross-validation**

Rare `processingmethod` values appeared only in validation folds during
hyperparameter search, not in training folds. `OneHotEncoder` raised a
`ValueError` on the first scoring call.

Fix: `handle_unknown="infrequent_if_exist"` set on the encoder in
`trainer.py`. This is not merely a cross-validation fix — in production,
unseen categories are inevitable as the SBA introduces new loan programmes.
Crashing on them would be exactly the kind of silent reliability failure this
project is built to prevent. The fix encodes that production reality into the
pipeline at training time.

---

## Consequences

The model layer is complete. `scripts/run_training.py` is the single entry point
for all future retraining runs. The parameters and metrics from every run are
stored in MLflow and comparable across runs.

The integration test (Q4) is the only open item. Until it exists, the wiring is
verified by the manual run recorded in this ADR but not by a standing automated
check.

The monitoring layer is next. ADR 023 defines its input contract. Q17 — drift
thresholds and alerting policy — is the first open question it must resolve.

---

## Follow-up (2026-05-25)

The integration test (Q4) is now written and passing — `tests/test_scripts/test_run_training.py`,
slow-marked, runs the full pipeline on a 300-row schema-valid fixture and asserts
the wiring contract. This closes the one open item noted above; the model layer
is complete.
