# 005 — Usable Row & Program Purity Threshold Decisions

**Date:** 2026-05-03  
**Component:** Data validation layer (`src/data/`)  
**Status:** Decided

---

## Context

ADR 003 defined a fatal check for when EXEMPT rows exceed a threshold. After inspecting the actual data, the EXEMPT framing no longer holds. The SBA data contains twelve distinct loan status values, organised into three buckets in ADR 004. EXEMPT does not appear in either file at all.

Two separate concerns emerged from the data inspection:

1. **Usable rows:** Whether enough PIF/CHGOFF rows survive the transformer to make the dataset worth processing. The production file (FY2020–Present) has only 67,637 usable rows out of 373,981 total (18.1%). The training file (FY2010–2019) has 422,542 out of 545,751 (77.4%). A dataset with far fewer resolved loans than expected is probably broken — wrong file, wrong time window, or wrong filtering.

2. **Program purity:** Whether the dataset is actually a 7(a)-only file. The pipeline was designed for 7(a) loans specifically (ADR 002). If a significant number of 504 loans have contaminated the file, the model is training on the wrong population. Inspection of both files confirmed they are overwhelmingly 7(a), but the check should exist as a guardrail.

These are independent checks. Program purity is about whether we have the right loan type. Usable rows is about whether enough of those loans have resolved outcomes. Both need their own threshold.

---

## Decision 1: Usable row threshold

A dataset is rejected as fatal if either condition is true:

- Usable rows fall below **12%** of total rows
- Usable rows fall below **50,000** in absolute count

Both conditions are checked. Either one failing is enough to reject the dataset.

These numbers are grounded in what we actually observed. The training file produces 67,637 usable rows (18.1% of total). The thresholds sit comfortably below that, giving room for natural variation while still catching datasets that are genuinely broken.

The absolute threshold of 50,000 ensures that even a large dataset with a high percentage of active loans — but enough raw numbers to train on — is not rejected purely on the percentage. A million-row file with 6% usable rows still has 60,000 PIF/CHGOFF loans and could be useful. The percentage threshold catches files where the composition is wrong regardless of absolute numbers.

---

## Decision 2: Program purity threshold

A dataset is rejected as fatal if 7(a) rows fall below **92%** of total rows.

This is a percentage-only check. No absolute count is needed because if the usable row threshold already passed, we know the dataset has enough PIF/CHGOFF rows. The program check only needs to verify that those loans are the right type.

The 92% threshold allows for a small amount of contamination — miscoded loans, data entry errors, or a handful of 504 rows in a 7(a) file — without rejecting an otherwise valid dataset. But if more than 8% of the file is non-7(a), something is structurally wrong with the data source.

---

## Consequences

**For `validator.py`:** Two new functions are added, both fatal checks:

- `check_usable_rows(df)` — counts rows where `loanstatus` is `pif` or `chgoff`, checks both percentage (≥12%) and absolute count (≥50,000).
- `check_program_purity(df)` — counts rows where `program` is `7a`, checks percentage (≥92%).

Both functions assume the DataFrame has already been transformed — loanstatus and program values are normalised to lowercase. They are post-transformation checks, consistent with the two-phase architecture defined in ADR 003.

**ADR 003 is superseded on the EXEMPT threshold point.** All other decisions in ADR 003 remain in force.
