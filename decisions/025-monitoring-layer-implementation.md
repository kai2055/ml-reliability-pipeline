# ADR 025 — Monitoring Layer Implementation

**Date:** 2026-05-31
**Component:** `src/monitoring/`, `scripts/run_monitoring.py`
**Status:** Decided

---

## Relationship to prior ADRs

This ADR documents the implementation decisions made while building the
monitoring layer. It is the implementation counterpart to ADR 023, which
established the *strategy* — which metrics to use, why PSI and Wasserstein
over KS, and the baseline's input contract. ADR 023 is assumed here; this
ADR records what happened when those decisions were turned into code.

This ADR depends on:
- **ADR 023** — Established PSI and std-normalised Wasserstein as the drift
  metrics, the 99-percentile quantile grid as the baseline format, and the
  `ddof=0` convention. Everything built here is bound by those decisions.
- **ADR 016 / ADR 017** — `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES`
  define the 12 v1 features the monitoring layer operates on.
- **ADR 024** — The training orchestration pattern (`scripts/run_training.py`)
  is mirrored by `scripts/run_monitoring.py`.

---

## Context

ADR 023 fixed the *what* — which metrics, which baseline format, which
conventions. What remained was the *how*: how drift results are structured,
how PSI is actually computed from stored percentiles, how the monitoring
pipeline handles production data differently from training data, and how the
four monitoring files wire together into a runnable script.

Several implementation decisions required real choices that ADR 023 left
open, and one production-data constraint — the absence of resolved loan
outcomes — surfaced a gap in the model layer that had to be closed before
the monitoring layer could work at all.

---

## Decisions

### 1. Output contract: flat `list[FeatureDriftResult]`

The drift detector returns a flat list of frozen dataclasses, one per
baseline feature. The numerical/categorical asymmetry (Wasserstein applies
only to numerical features) is handled by a `feature_type` field and a
`wasserstein=None` value for categoricals — not by splitting the output
into two separate collections.

The rejected alternative was a two-section dict (`"numerical"` /
`"categorical"`). The flat list was chosen because it gives every consumer
a single iteration path; a consumer that needs only numerical features
filters on `feature_type`. The asymmetry is explicit in the data, not
imposed by the container structure.

A frozen dataclass was chosen over a plain dict for the same reason it was
used throughout the model layer: attribute access is typo-proof, the
definition is the contract, and a misspelled key fails immediately rather
than silently returning `None`.

### 2. Feature mismatch handling

A production DataFrame missing a baseline feature raises
`FeatureMismatchError` — the comparison for that feature is impossible and
proceeding would produce a garbage report. This mirrors `_run_fatal_checks`
in the training pipeline: bad inputs stop the run rather than producing
quietly wrong output.

Extra production features (columns not in the baseline) are logged as a
warning and skipped. The asymmetry is principled: a missing feature makes
the detector's task *impossible*; an extra feature leaves it *fully
possible* — every baseline feature is still comparable. The extra-features
case is a deferred tracker item: a warning buried in logs is not reliably
visible, and a future "schema drift" check or prominent report entry should
surface it. For v1, warn-and-skip is acceptable.

### 3. PSI implementation decisions

**Bin count: 10.** Equal-frequency decile bins are the industry standard
for credit-risk PSI, and the conventional interpretation bands (below 0.1,
0.1–0.25, above 0.25) were calibrated on decile-binned PSI. The constraint
`N_PSI_BINS must divide 100` is enforced with an explicit guard at the top
of `_psi_numerical` — a violation raises immediately rather than producing
subtly wrong bin edges.

**Bin edges derived from stored percentiles.** For 10 bins, the internal
edges are the 10th, 20th, … 90th percentiles, stored at indices 9, 19, …
89 of the 99-element percentile array. The target percentile number is
computed first (`k * spacing`), then converted to a storage index (`- 1`
for 0-based offset). An earlier version computed the index directly with
`step * (i+1) - 1` using `step = 99 // 10 = 9`, which silently used the
9th, 18th, … percentiles instead of the intended deciles. That off-by-one
was caught in review and corrected.

**Outer bins are open (`-inf` / `+inf`).** Production values outside the
training range — loans smaller or larger than anything seen at training
time — land in the first or last bin respectively. Hard edges at the
training min/max would silently discard them.

**`PSI_EPSILON = 1e-4` floors both fractions.** A category vanishing from
production (production fraction = 0) or appearing for the first time
(training fraction = 0) would make `ln(production / training)` undefined.
Both sides are floored at epsilon. Dropping zero-fraction bins was rejected
because a vanished category is itself a strong drift signal; the epsilon
floor preserves it as a large PSI contribution rather than hiding it.

**`ddof` risk is resolved by reading, not recomputing.** The Wasserstein
normalisation divides by the baseline's stored `std`. The detector reads
that value — it never recomputes the baseline side. The only live `ddof`
risk is a production-side `std` if one were ever needed; the current
implementation does not compute one, so the risk is effectively closed.

### 4. Severity thresholds in `drift_policy.py`

PSI thresholds follow the industry-standard bands used in credit-risk
scorecard monitoring: PSI < 0.1 is low, 0.1–0.25 is moderate, above 0.25
is significant. Wasserstein thresholds mirror the same three-level
structure in units of training standard deviation: below 0.3σ is low,
0.3σ–0.8σ is moderate, above 0.8σ is significant. Both sets of thresholds
are defined as named constants in `drift_policy.py` and imported by
`report_generator.py` — a single source of truth for policy values.

These thresholds were set by convention and statistical reasoning, not
derived from Datatroniq's actual cost data. Re-estimation from real
business context is deferred (tracker Q17, carried from ADR 023).

### 5. `build_features` split from `build_dataset`

`build_dataset` internally calls `_filter_rows`, which keeps only rows
where `loanstatus` is `"pif"` or `"chgoff"`. Production loans have not yet
resolved — `loanstatus` is `"current"`, `"active"`, etc. — so the filter
would drop nearly all production rows before drift detection ran. This
would make the detector compare the baseline against essentially nothing.

The fix: a new public function `build_features` added to the existing
`src/models/dataset_builder.py` — a deliberate change to a model-layer
file to close a gap the monitoring layer exposed. The monitoring pipeline
calls `build_features`; the training pipeline continues to call
`build_dataset`. Both functions share the same `_select_features` and
`_fill_missing_categoricals` helpers.

### 6. `run_fatal_checks` moved to `validator.py`

The fatal-checks logic (`check_columns`, `check_program_values`,
`check_required_columns`, and optionally `check_usable_rows`) was
originally a private helper inside `scripts/run_training.py`. The
monitoring pipeline needed the same checks, minus `check_usable_rows` —
which gates on resolved-outcome row counts and would always fail on
production data. Rather than duplicate the helper, it was extracted to a
public `run_fatal_checks` function in `validator.py`, importable by both
scripts. The monitoring pipeline calls it with `include_usable_rows=False`.

The `include_usable_rows` boolean flag is a known design trade-off. A
two-function design (`run_fatal_checks` / `run_fatal_checks_monitoring`)
was considered and rejected in favour of keeping one function with an
explicit parameter. The flag is documented in the function signature and
the difference in behaviour is captured in each script's call site.

### 7. Monitoring orchestration: `scripts/run_monitoring.py`

The monitoring script mirrors `run_training.py` in structure: a fenced
uppercase config block, an injectable-parameter function with a testing
seam, and a `__main__` block that wires the constants in. Unlike
`run_training`, `run_monitoring` returns a `DriftReport` — the function
produces something a caller can inspect, not just a side effect.

MLflow logging records: input parameters (data path, baseline dir, row
counts), summary counts (significant/moderate/low features), and per-
feature PSI and Wasserstein scores as named metrics. Artifact files are
not logged to MLflow — the report is the artifact, and it is returned
directly to the caller.

---

## Consequences

The monitoring layer is complete. The full pipeline — from raw production
CSV to a structured drift report logged to MLflow — is runnable with
`python scripts/run_monitoring.py`.

**Open items:**

- **Extra-features visible surfacing** — currently a log warning only.
  A future schema-drift check or report entry should surface this
  prominently. Deferred tracker item.
- **Q17 — drift thresholds** — severity bands are set by convention.
  Re-estimation from real Datatroniq cost data and operational context
  is deferred, as carried forward from ADR 023.
- **`include_usable_rows` flag** — the boolean parameter in
  `run_fatal_checks` is a known design trade-off, noted here for
  awareness. A future refactor could replace it with two explicit
  functions if the monitoring pipeline's fatal-checks surface grows.