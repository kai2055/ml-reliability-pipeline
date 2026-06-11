# 023 — Baseline Snapshot and Drift Detection Strategy

**Date:** 2026-05-22
**Component:** Model layer (`src/models/baseline_saver.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR introduces the final file in the model layer, `src/models/baseline_saver.py`. It is the bridge between the model layer and the monitoring layer: it captures a frozen snapshot of the training data's distribution, which the monitoring layer later reads to detect drift.

This ADR depends on:
- **ADR 002** — Established that FY2010–2019 is the training data and FY2020–Present is the simulated production data. The baseline is computed from the FY2010–2019 training split; the monitoring layer compares FY2020+ production data against it.
- **ADR 016 / ADR 017** — Established `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES` in `dataset_builder.py`. The baseline saver imports these constants; the numerical/categorical split that governs how each feature is described is single-sourced from there.
- **ADR 022** — The registry's two-file artifact format and its overwrite-guard pattern. The baseline saver mirrors the overwrite guard, with one deliberate difference noted below.

This ADR also makes a forward commitment that the not-yet-built monitoring layer must honour: the drift metrics, the binning strategy, and the standard-deviation convention described here are the contract the monitoring layer reads against.

---

## Context

A deployed model is trained on a specific dataset. Over time, the data arriving in production drifts away from that training distribution — applicant profiles shift, economic conditions change. The model does not crash; it keeps returning predictions. But those predictions quietly become less reliable. This is the silent-failure mode the entire project exists to surface.

Detecting that drift requires a fixed reference: a description of what the training data looked like, captured at training time and never changed. Without such a reference, "has the data drifted?" is unanswerable — there is nothing to compare against.

`baseline_saver.py` produces that reference. Several decisions had to be made:

1. **What kind of drift is in scope** — and, honestly, what is out of scope.
2. **Which drift metrics the system will use** — and why those, not the alternatives.
3. **What the baseline must store** so those metrics can be computed later.
4. **How numerical distributions are summarised** — the central technical choice.
5. **How the file is structured** — function surface and format.

These are bundled in one ADR because they are mutually determining: the choice of drift metric dictates what the baseline must store, which dictates the file's structure.

---

## Decision

### 1. Scope: data drift only; concept drift is a stated blind spot

Three kinds of drift are conceptually distinct:

- **Data drift** — `P(X)` changes. The distribution of the input features shifts. *Observable immediately* from incoming data.
- **Concept drift** — `P(y|X)` changes. The same kind of applicant now defaults at a different rate; the input–outcome relationship itself moves. *Observable only once ground-truth outcomes arrive* — in lending, months to years after origination.
- **Prediction drift** — `P(ŷ)` changes. The model's output distribution shifts. Usually a downstream symptom of data drift.

The baseline saver and the monitoring layer target **data drift**. They compare feature distributions; they never see outcomes. They therefore *cannot* detect concept drift directly.

This is a real limitation and it is stated deliberately rather than hidden. The justification: in credit lending, ground-truth outcomes are unavailable for months or years, so a concept-drift detector would always be reporting on a world long past. Data drift detection is an **early-warning proxy** — when the input distribution shifts substantially, the input–outcome relationship is at risk, and the team is alerted *before* the defaults materialise rather than discovering the degradation from the loss numbers a year later.

For the Spreekredit scenario this is sufficient: the FY2010→FY2020 transition (COVID) produces large, immediately-visible data drift, which is exactly what this system is built to catch.

### 2. Drift metrics: PSI for all features, Wasserstein (std-normalised) for numerical features

The monitoring layer will use two metrics. The baseline must store what they need as input.

**PSI (Population Stability Index)** — applied to every feature, numerical and categorical. PSI bins a feature's range and compares the per-bin proportion of records between training and production. It is finance-native — credit-risk teams have used it for decades for exactly this purpose — and it has well-known interpretability bands (under ~0.1: little shift; ~0.1–0.25: moderate; above ~0.25: significant). Those bands turn drift into a signal a non-ML stakeholder can act on, which serves the project's thesis of making silent failure *visible*.

**Wasserstein distance, normalised by the training standard deviation** — applied to numerical features only. PSI has a real blind spot: it only sees mass *crossing bin boundaries*. A distribution can change shape substantially while the per-bin proportions stay constant, and PSI reports nothing. Wasserstein is bin-free — it measures the total "cost" of reshaping one distribution into the other — so it catches within-bin shape change PSI misses.

Raw Wasserstein distance is in the feature's own units (dollars for `grossapproval`, rate-points for `initialinterestrate`), so raw values are not comparable across features and cannot share a threshold. Normalising by the training standard deviation converts it to a unitless quantity — "the distribution moved by N standard deviations" — comparable across all numerical features and thresholdable with a single rule. This is why the baseline stores `std` per numerical feature.

**KS (Kolmogorov–Smirnov) was considered and rejected.** KS is a formal statistical test producing a p-value. Its fatal weakness for this project is large-sample over-sensitivity: with the 50,000+ rows specified by ADR 005, KS's statistical power becomes a liability — it flags shifts that are statistically detectable but practically irrelevant, driving p-values toward zero for drift no one needs to act on. A monitoring system that raises alarms on meaningless shifts gets ignored. Wasserstein has no such failure mode: its value reflects the *magnitude* of the shift, which does not inflate with sample size. Since the project's expected finding is a large, real, COVID-driven shift, a metric that reports *how big the move is* is more useful than one that reports *the statistical certainty that a move occurred*.

This is a deliberate departure from the conventional "PSI + KS" pairing seen in credit scorecard validation. The departure is documented here precisely so it reads as a reasoned choice rather than an unawareness of the convention.

### 3. What the baseline stores

For each **numerical** feature:
- **99 percentiles** (1st through 99th) — the distribution's shape map
- **mean, standard deviation, min, max**
- **missing_fraction** — the proportion of rows with a missing value

For each **categorical** feature:
- the **frequency of each category** — the proportion of rows in each, with missing values kept as a separate category

Plus metadata: `created_at`, `n_training_rows`, `numerical_features`, `categorical_features`.

### 4. Numerical distributions are stored as a 99-percentile quantile grid

The central technical decision. To compute Wasserstein and PSI later, the monitoring layer needs a faithful description of each numerical feature's distribution. Two options were weighed:

- **A retained random sample** of training values.
- **A quantile grid** — the value at each of the 1st…99th percentiles.

The quantile grid was chosen, for four reasons:

1. **Reproducibility.** A percentile is a deterministic function of the data — recomputed on the same input, it yields identical numbers. A random sample carries sampling noise; fixing a seed only makes that noise repeatable, not absent. The project insists on reproducibility everywhere (fixed seeds, frozen dataclasses); a quantile grid is reproducible *by construction*.
2. **Honest tail representation.** Credit risk cares about rare large loans. A random sample captures the tail only by luck of the draw. A quantile grid pins the 1st and 99th percentiles explicitly.
3. **Fixed, small size.** 99 numbers per feature regardless of whether the training set has 50,000 or 5,000,000 rows.
4. **Privacy.** A percentile is an aggregate statistic, not any individual applicant's record.

The one advantage of a retained sample — it can feed any future metric, including ones not yet chosen — was discounted under the project's standing YAGNI principle: v1 does not pay a real cost now (sampling noise, weaker tails, privacy weight) for an uncertain future need.

**PSI bins are not stored.** They are *derived* from the percentiles by the monitoring layer. Equal-frequency PSI bins are defined by percentile values directly (10 equal-frequency bins ⇒ edges at the 10th, 20th, …, 90th percentiles, each bin holding 10% of training data by definition). Storing bins separately would duplicate information already present in the percentiles — a two-sources-of-truth hazard the project rejects. It also keeps responsibilities clean: the baseline saver *describes the data*; deciding how many PSI bins to use is a monitoring-layer *policy* choice.

### 5. Standard deviation convention: population (ddof=0)

`std` is computed with `ddof=0` (population standard deviation), stated explicitly in code rather than inheriting a library default. This matters because pandas' `.std()` defaults to `ddof=1` (sample) while numpy's defaults to `ddof=0` (population) — a silent inconsistency waiting to happen. The monitoring layer, when it normalises Wasserstein distance by this `std`, **must use the same convention**. On 50,000+ rows the numerical difference between `ddof=0` and `ddof=1` is negligible, but the explicitness removes the trap.

### 6. Missingness is tracked for both feature types

Missing values are a distribution fact in their own right — if the missing rate of a feature drifts in production, that is real drift worth catching.

- **Numerical features** drop NaN before percentile computation (a percentile of a missing value is undefined), but the discarded information is preserved as `missing_fraction`.
- **Categorical features** keep missing values as a *separate category* in the frequency table, so a rising missing rate shifts that category's frequency and PSI detects it.

### 7. File structure: one JSON file, three functions

The baseline contains only numbers, strings, and nested lists/dicts — no fitted model, no binary object. It is therefore stored as a single human-readable file, `baseline.json`. Unlike the registry (ADR 022), which needed two files because it carried a binary pipeline alongside readable metadata, the baseline has no binary part; one file suffices.

The file exposes three functions:

- **`compute_baseline(X_train) -> dict`** — pure: computes the distribution snapshot, performs no I/O. Kept separate from saving so it is unit-testable in isolation without touching the filesystem — the same purity principle ADR 018 applied to `tune()`.
- **`save_baseline(baseline, directory, overwrite=False)`** — serialises the dict to `baseline.json`.
- **`load_baseline(directory) -> dict`** — reads it back.

`compute_baseline` and `save_baseline` are deliberately separate. Although the orchestration script always computes and saves together, the test suite is a caller that needs them apart — a unit test for `compute_baseline` must inspect its output without a file write. One caller needing them separated is enough to require the split.

### 8. Overwrite guard: protects the file, not the directory

`save_baseline` refuses to overwrite an existing `baseline.json` unless `overwrite=True` is passed — mirroring `registry.save_model` (ADR 022), because a baseline is the monitoring layer's reference point and silently replacing it would shift that reference without anyone deciding so.

One deliberate difference from `registry.save_model`: the guard checks the **file**, not the **directory**. The baseline typically lives in the same run directory as the model artifact, which the orchestration script will already have created when it saved the model. Guarding the directory would force `overwrite=True` on every call. Guarding the file protects the actual asset without that friction.

---

## Consequences

**For the monitoring layer (pending):** This ADR is its input contract. It reads `baseline.json`, derives PSI bins from the stored percentiles, computes PSI for all features and std-normalised Wasserstein for numerical features, and **must** use `ddof=0` when computing production-side standard deviations to match the baseline.

**For the orchestration script (pending):** After the data split, it calls `compute_baseline(X_train)` and `save_baseline(...)`. The baseline can be computed as soon as `X_train` exists — before model selection — because the baseline is a property of the data, not the model.

**For `dataset_builder.py`:** No changes. The baseline saver imports `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES` from it; the numerical/categorical split is single-sourced.

**For testing:** `baseline_saver.py` has its own test surface (`tests/test_models/test_baseline_saver.py`, 9 tests) covering structure, metadata, the numerical summary shape and sanity, percentile count and monotonicity, categorical frequency sums, the `missing_fraction` logic with injected NaNs, the save/load round trip, and both halves of the overwrite guard.

**For interview defensibility:** Every choice has a documented rationale — the data-drift scope and its honest concept-drift blind spot, the metric selection with KS explicitly considered and rejected, the quantile-grid over retained-sample decision, the explicit `ddof` convention. The departure from the conventional PSI+KS pairing is reasoned in writing.

---

## Open questions opened by this ADR

- **Q16 — Concept drift detection.** v1 detects data drift only. Once ground-truth loan outcomes for FY2020+ data become available, what process detects whether `P(y|X)` has shifted, and how does it integrate with the existing data-drift signals? Deferred to v2; its concrete change driver is the eventual arrival of resolved-loan outcomes.

- **Q17 — Drift thresholds and alerting policy.** This ADR fixes the *metrics* (PSI, Wasserstein) but not the *thresholds* at which the monitoring layer raises an alert, nor how per-feature drift aggregates into a system-level signal. PSI has conventional bands; std-normalised Wasserstein needs a threshold chosen deliberately. This is monitoring-layer policy, to be settled when that layer is built.
