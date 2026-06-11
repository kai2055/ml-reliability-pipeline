

# 004 — LoanStatus Schema Decision

**Date:** 2026-05-02  
**Component:** Data validation layer (`src/data/`)  
**Status:** Decided

---

## Context

The official SBA data dictionary for the 7(a) dataset documents exactly five values for `loanstatus`: `COMMIT`, `PIF`, `CHGOFF`, `CANCLD`, and `EXEMPT`. When the actual FY2020–Present production file was inspected, twelve distinct values were found. Eight are completely undocumented: `CURR`, `PURCH(NOT C/O)`, `CLSLN`, `LIQUID`, `DELINQ`, `PSTDUE`, `DEFERD`, and `SOLDNC`.

Even the documented values present formatting issues in the raw data — `PIF` appears as `P I F` with spaces between letters. The data dictionary uses mixed case while the raw data does not follow it consistently.

This gap indicates the SBA changed their status coding conventions at some point during the dataset's lifetime. The data dictionary was not updated to reflect these changes. This is a real production data quality issue, not a textbook example.

**Value counts in the production file (FY2020–Present):**

| Value | Count | In Data Dictionary |
|-------|-------|--------------------|
| P I F | 391,693 | Yes (as PIF) |
| CANCLD | 66,740 | Yes |
| CURR | 44,482 | No |
| CHGOFF | 30,849 | Yes |
| PURCH(NOT C/O) | 4,703 | No |
| CLSLN | 2,835 | No |
| LIQUID | 2,667 | No |
| DELINQ | 1,069 | No |
| PSTDUE | 547 | No |
| DEFERD | 116 | No |
| COMMIT | 49 | Yes |
| SOLDNC | 1 | No |

---

## Decision

All twelve values found in the real data are treated as known values in the pipeline. They are organised into three buckets that determine how the transformer handles them downstream.

**Bucket 1 — Active loans (no outcome yet, equivalent to EXEMPT):** `CURR`, `DELINQ`, `PSTDUE`, `DEFERD`

These loans are still live. The borrower is either paying on schedule, behind on payments, or temporarily paused. There is no final credit outcome — the loan has not been paid off or charged off. Functionally, these are the production equivalent of `EXEMPT` in the training file. Including them in training would teach the model patterns from loans with no resolved label, which is meaningless for a default prediction task. These rows are dropped by the transformer.

**Bucket 2 — Resolved loans with ambiguous outcomes:** `CLSLN`, `LIQUID`, `PURCH(NOT C/O)`, `SOLDNC`

These loans reached some kind of resolution — closed, liquidated, or sold — but the outcome cannot be mapped reliably to a binary PIF/CHGOFF label. Without that mapping, these rows cannot contribute a training signal. These rows are dropped by the transformer.

**Bucket 3 — Known, documented values:** `PIF`, `CHGOFF`, `CANCLD`, `COMMIT`

These map to the official data dictionary values. `PIF` and `CHGOFF` are the usable labels for the binary classification task. `CANCLD` and `COMMIT` are dropped — cancelled loans have no outcome, committed loans have not yet been disbursed.

---

## Consequences

**For `schema.py`:** `LOAN_STATUS_VALUES` is expanded from five documented values to all twelve values found in the real data. The schema now reflects what actually exists in production, not just what the data dictionary describes. All twelve values are lowercased, consistent with the convention established in ADR 003.

**For `validator.py`:** The column content check for `loanstatus` validates membership against all twelve known values. Any value outside this set is flagged as unknown — this is a non-fatal check. The validator's job is only to confirm that every value is a known string. It does not apply bucket logic.

**For `transformer.py`:** The bucket categorisation is implemented here. Bucket 1 and Bucket 2 rows are dropped before the dataset reaches the model. Bucket 3 rows pass through, with `CANCLD` and `COMMIT` also dropped at this stage. The transformer is responsible for routing — not the validator.

**Separation of concerns preserved:** The validator diagnoses what is in the data. The transformer decides what to keep. These remain two distinct responsibilities on the same data, consistent with the principle established in ADR 003.
