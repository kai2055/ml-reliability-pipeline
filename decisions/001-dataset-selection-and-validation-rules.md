# 001 — Dataset Selection and Validation Rules

**Date:** 2026-04-30  
**Component:** Data validation layer  
**Status:** Decided

---

## Decision 1: I chose a real dataset over a synthetic one

**What I decided:** Use a real publicly available dataset rather than generating a synthetic one.

**What I considered:** Generating a synthetic dataset tailored to Spreekredit's profile.

**Why I rejected it:** When you generate synthetic data, you unconsciously make it too clean. You avoid the exact messiness that the validation layer is supposed to catch. That defeats the whole point. I also worried that synthetic data might have unnatural patterns baked in without me even realising it.

**Why I went with real data:** The whole point of this pipeline is production reliability. Real data has the genuine issues — missing values, inconsistent formatting, weird coded fields, edge cases — that I actually need to validate against.

---

## Decision 2: I chose the SBA 7(a) Loans dataset (FY2020–Present)

**What I decided:** Use the US Small Business Administration 7(a) FOIA loan dataset, specifically the FY2020–Present file.

**What I considered:**
1. **Lending Club** — real peer-to-peer lending data, 890k rows, 75 features. I rejected this because it is consumer lending, not small business lending. The applicant is an individual person, not a company. That is a fundamental mismatch with what Spreekredit does.
2. **SBA 504 program** — also real SBA data but specifically for large fixed-asset purchases like buildings and equipment. I rejected this because Spreekredit does general-purpose small business lending, not fixed-asset financing.

**Why I chose 7(a):**
- It is the closest match to Spreekredit's domain — general-purpose small business loans.
- It is real and messy in the way government data tends to be — coded fields, inconsistencies, missing values.
- Most importantly: the FY2020–Present window includes COVID-19. Small businesses were hit hard from March 2020 onward. The type of applicants, the industries, the loan sizes — all of it shifted dramatically. That means there is a real documented drift event sitting inside this dataset, not a simulated one. That is directly useful for the drift detection part of the pipeline.

**Source:** https://data.sba.gov/dataset/7-a-504-foia

---

## Decision 3: I will reject datasets where too many loans are EXEMPT status

**What I decided:** The validation layer will check what percentage of rows have `LoanStatus = EXEMPT`. If that percentage is above a threshold I will define during implementation, the entire dataset gets rejected. If it is below the threshold, I drop those rows and log how many were removed.

**Some context:** The `LoanStatus` column has five possible values — `COMMIT`, `PIF` (Paid in Full), `CHGOFF` (Charged Off), `CANCLD` (Cancelled), and `EXEMPT`. EXEMPT means the loan is still active — it has not been paid off, defaulted, or cancelled yet. It is in limbo.

Spreekredit's model is trying to answer one question: will this applicant pay or default? So the only labels that matter are `PIF` and `CHGOFF`. EXEMPT rows have no answer yet.

**Why I am excluding EXEMPT rows:**
- If I include them, the model picks up patterns from loans with no clear outcome, which teaches it something meaningless for the actual prediction task.
- It could cause the model to behave as if there is a third category — "still active" — which is not a credit decision, it is just a data pipeline problem.
- I want to keep things simple. If a label is not meaningful for the task, it should not go anywhere near the model.

**What I considered instead:** Giving EXEMPT rows a very low sample weight during training so their influence would be tiny. I rejected this because it adds complexity for no real benefit. If the label does not mean anything useful, the right call is to remove it entirely, not to sneak it in with a low weight.

**Threshold:** To be decided during implementation. The principle is simple — if too many rows are EXEMPT, the dataset does not have enough real labelled examples to train on, and the whole thing should be rejected before any further processing.

**The rule in plain terms:**
1. Count the rows where `LoanStatus = EXEMPT`
2. Work out what percentage of the total that is
3. If above threshold → reject the dataset and log why
4. If below threshold → drop the EXEMPT rows, log how many were dropped, and continue
