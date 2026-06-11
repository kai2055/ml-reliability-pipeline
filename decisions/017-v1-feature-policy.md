
# 017 — v1 Feature Policy

**Date:** 2026-05-15
**Component:** Model layer (`src/models/dataset_builder.py`)
**Status:** Decided

---

## Relationship to prior ADRs

This ADR depends on **ADR 016**, which establishes `dataset_builder.py` as the file where these feature decisions live. ADR 016 is the architectural ADR — it says "there is a file that owns feature decisions." This ADR is the policy ADR — it says "here are the specific decisions for v1."

This ADR closes two open questions from `docs/assumptions-to-revisit.md`:

- **Q1:** Should every feature be used, or some pruned?
- **Q2:** Why are certain columns treated as numerical vs categorical?

Seven new questions are added to the tracker (Q9–Q15).

---

## Context

The schema (`src/data/schema.py`) declares 42 columns and their dtypes. But dtype doesn't tell you a column's role in a model. An integer-typed column could be a continuous quantity (`jobssupported`), a 0/1 flag (`revolverstatus`), or an identifier (`bankfdicnumber`). The schema doesn't distinguish, and it shouldn't — that's a modelling decision.

Without a decision about which columns are features, two things break:

- **Columns the model shouldn't see during training would slip in.** `chargeoffdate` only has a value when a loan has defaulted. If the model sees it during training, it learns "if this column has a value, predict default" — perfect training accuracy, useless predictions on new applicants (where the column is always empty). This is target leakage.

- **High-cardinality columns would flood the feature space.** `borrname` has thousands of unique values. One-hot encoding it produces thousands of feature columns, most of which appear in only a few training rows. The model can't learn anything generalisable from them.

For a column to make it into v1, it has to pass four checks:

1. **Is the value available at prediction time?** If the column only has a value after the loan resolves, it's leakage. We need columns the model could see in production, when scoring a new application.
2. **Does the column have enough variation to carry signal?** A column that's the same value for almost every row teaches the model nothing.
3. **Is the cardinality manageable?** A column with thousands of unique values doesn't generalise. Either it gets engineered into a coarser feature (v2 work), or it's excluded.
4. **Does the column raise governance concerns we can't yet handle?** Geographic features in credit decisions can act as proxies for protected attributes. v1 stays out of that territory entirely.

The v1 feature list is the smallest set that produces a working credit-risk model. Any v2 complexity has to justify itself against the v1 baseline AUC — not against the abstract claim that "more features should help."

---

## Decision

### Target

The target is built from `loanstatus`:

- `pif → 0` (paid in full, no default)
- `chgoff → 1` (charged off, default)

Every other `loanstatus` value (`curr`, `delinq`, `cancld`, etc.) gets dropped from the dataset before training (per ADR 016). The `loanstatus` column itself is also dropped after the target is derived, so it cannot accidentally end up in `X`.

### v1 features (12 total)

**Numerical features (5)** — scaled with `StandardScaler`:

| Column | Why it's a feature |
|---|---|
| `grossapproval` | Total loan amount. A real continuous quantity. |
| `sbaguaranteedapproval` | Portion guaranteed by the SBA. Continuous. |
| `initialinterestrate` | Interest rate at origination. Continuous. |
| `terminmonths` | Loan term length. 60 months is meaningfully twice 30 months — genuinely continuous. |
| `jobssupported` | Number of jobs the loan is intended to support. Self-reported, but a real signal — applicants claiming to support more jobs may have different default profiles. |

A note on `grossapproval` and `initialinterestrate`: strictly speaking, these are *granted* values, set during approval, so they don't exist before the approval decision. But in practice, lenders score against *proposed* values (what the applicant asked for), and the granted values stay close to the proposed values — neither side completes a deal where the numbers are wildly off. So using granted values as a proxy for proposed values is a reasonable v1 simplification.

**Categorical features (7)** — encoded with `OneHotEncoder`:

| Column | Why it's a feature |
|---|---|
| `subprogram` | Sub-classification within 7(a). Low cardinality. |
| `processingmethod` | How the loan was processed. 30 documented values. |
| `fixedorvariableinterestind` | Binary: "f" or "v". |
| `revolverstatus` | 0/1 flag. Integer in the schema, but conceptually a category — it doesn't make sense to scale a flag. |
| `businesstype` | "individual", "partnership", "corporation". Three values. |
| `businessage` | Age buckets like "new business or 2 years or less". 10 documented values. |
| `collateralind` | Binary: "true" or "false". |

### Exclusions (30 columns, grouped by reason)

**Outcome columns — target leakage (3):**
`paidinfulldate`, `chargeoffdate`, `grosschargeoffamount`

These columns only have a value after a loan resolves. A new applicant being scored doesn't have a `chargeoffdate` yet. If the model trained on these, it would learn to cheat — and then fail in production where the cheat isn't available.

**Identifiers — high cardinality, no generalisation (17):**
`borrname`, `borrstreet`, `borrcity`, `borrzip`, `bankname`, `bankfdicnumber`, `bankncuanumber`, `bankstreet`, `bankcity`, `bankzip`, `locationid`, `franchisecode`, `franchisename`, `naicscode`, `naicsdescription`, `projectcounty`, `congressionaldistrict`

Each of these has thousands of unique values across the dataset. One-hot encoding any of them produces thousands of feature columns, each appearing in a tiny fraction of training rows. The model would memorise specific borrowers rather than learning which kinds of borrowers default. `naicscode` is flagged as v2 work — bucketed at the 2-digit or 3-digit level, it becomes a usable industry feature.

**Geographic features — fairness governance (3):**
`borrstate`, `projectstate`, `sbadistrictoffice`

These have manageable cardinality, so the technical case is fine. The governance case isn't. Geographic features in credit decisions can correlate with protected attributes like race, even when the model isn't trying to use them that way. Bringing them in requires a fairness analysis the project isn't yet equipped to do. v1 excludes them entirely. v2 can re-introduce them after the analysis is done.

**Date columns — no pre-approval availability (3):**
`asofdate`, `approvaldate`, `firstdisbursementdate`

`asofdate` is a snapshot timestamp — the same value for every row in a given data extract, so no signal. `approvaldate` and `firstdisbursementdate` are recorded at or after approval. Spreekredit's model scores applicants *before* approval, so these don't exist at prediction time.

**Temporal proxy (1):**
`approvalfy`

Fiscal year as an integer would make the model treat 2020 as "5 units more than 2015" — but creditworthiness doesn't scale linearly with calendar year. Treated as a category, it would teach the model year-specific patterns (e.g. "2020 loans had higher defaults") instead of the underlying features that actually drove those patterns. The drift detection pipeline this project builds is specifically designed to detect when the data distribution shifts over time. Building those temporal effects directly into the model duplicates work that the monitoring layer already does — and makes both harder to reason about.

**Informationally null (1):**
`program`

The validator enforces that ≥92% of rows are `7a` (per ADR 005). A column that's almost always the same value can't teach the model anything.

**Availability ambiguous (1):**
`soldsecmrktind`

This indicator might be set at origination (representing the lender's intent to sell the loan) or it might be set later (representing whether the loan actually got sold). The first is available at prediction time; the second is leakage. Without clarification of the semantics, v1 excludes it.

**The target column itself (1):**
`loanstatus`

Becomes the target. Removed from `X` after `y` is derived.

---

## Consequences

**For `dataset_builder.py`:** Two lists are declared at the module level:

```python
NUMERICAL_FEATURES = [
    "grossapproval", "sbaguaranteedapproval", "initialinterestrate",
    "terminmonths", "jobssupported",
]

CATEGORICAL_FEATURES = [
    "subprogram", "processingmethod", "fixedorvariableinterestind",
    "revolverstatus", "businesstype", "businessage", "collateralind",
]
```

These are the single source of truth for which columns are features and how each is treated. Any model-layer file that builds a pipeline imports these lists from here.

**For `trainer.py`:** Its `build_pipeline()` function reads these lists. No column names are hardcoded inside `trainer.py`.

**For `tuner.py` and `tuning_configs.py`:** Same — the tuning configs use these lists when constructing the pipelines for each model family.

**For interview defensibility:** Every excluded column has a documented reason. Every included column passes the four-check test. v1 ships with a measurable baseline, against which any v2 feature additions can be evaluated honestly.

**For the assumptions tracker:** Seven new questions are opened by this ADR for v2 work:

- **Q9:** NAICS bucketing — re-introduce `naicscode` at the 2-digit or 3-digit level as an industry feature.
- **Q10:** Bank-level historical features — engineer features like origination volume or historical default rate from `bankfdicnumber`.
- **Q11:** Geographic features — re-evaluate `borrstate`, `projectstate`, and `sbadistrictoffice` after fairness analysis.
- **Q12:** Fairness analysis — establish the formal review process for any feature that could proxy for protected attributes. Q11 cannot be resolved without this.
- **Q13:** Date-derived features — engineer features like year buckets or days-between-events if drift monitoring shows temporal patterns matter.
- **Q14:** Subprogram / processingmethod redundancy — check whether the two columns carry overlapping information; prune one if so.
- **Q15:** `soldsecmrktind` semantics — investigate whether it represents origination intent or post-origination outcome.

Each of these is a v2 PR scope: a piece of reading, a code change, and an ADR that measures the change against the v1 baseline.

**For the v1 → v2 evolution:** Simplicity in v1 makes complexity in v2 evaluable. If `naicscode` bucketing in v2 lifts AUC from 0.78 to 0.81, that's a defensible engineering decision — three points of AUC for one feature group's worth of work. Without a v1 baseline, every v2 addition is a guess.
