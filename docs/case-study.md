# Datatroniq ML Reliability Pipeline — Case Study

## The Problem: Silent Model Degradation

Datatroniq is a Berlin‑based fintech offering small business loans. Their credit risk model scores loan applicants and predicts default probability. The model was trained on a decade of historical SBA 7(a) loan data — stable, pre‑COVID lending from 2010 to 2019.

In early 2020, COVID‑19 disrupted small business lending fundamentally. Government emergency programmes flooded the SBA with applications from businesses that would never have applied before. The profile of applicants changed overnight. Loan sizes shifted. Processing methods changed as the SBA fast‑tracked emergency programmes. Industries that were previously low‑risk became high‑risk.

The model didn't crash. It kept returning predictions. But the data it was seeing looked nothing like the data it was trained on. This is **silent model degradation** — the hardest failure mode in production ML to detect.

This pipeline exists to catch it.

---

## Pipeline Overview

1. **Train** the model on historical data (FY2010–2019) and save baseline feature distributions.
2. **Score** incoming production loans (FY2020–present) in real time.
3. **Monitor** each batch of production data: compute PSI and Wasserstein distance against the baseline.
4. **Alert** when drift exceeds defined thresholds (PSI > 0.25 or Wasserstein > 0.8σ).

No outcome labels are required — drift is detected as soon as new data arrives.

---

## The Model: Training on a Decade of Stable Lending

- **Training data:** SBA 7(a) FOIA loans, FY2010–2019
- **Rows after filtering to resolved outcomes:** ~422,000
- **Default rate:** 7.3% (30,849 charged off, 391,693 paid in full)
- **Features:** 12 v1 features — 5 numerical, 7 categorical

### Model Tuning

Three model families were tuned using randomised and grid search with 5‑fold stratified cross‑validation:

| Model | Tuning Strategy | Configurations Tried |
|-------|----------------|----------------------|
| Logistic Regression | Grid search | 10 |
| Random Forest | Random search | 20 |
| XGBoost | Random search | 20 |

- **Selected model:** Random Forest
- **Selection criterion:** Minimum expected cost on validation set (cost ratio FN = 5×FP)
- **Decision threshold:** 0.23

### Test Set Performance

| Metric | Value |
|--------|-------|
| ROC‑AUC | 0.9721 |
| Recall | 0.8643 |
| Precision | 0.6094 |
| Log Loss | 0.1074 |
| Brier Score | 0.0292 |

The model achieves 0.9721 ROC‑AUC. Recall of 86.4% means the model catches 86 out of every 100 actual defaults. Precision of 60.9% means roughly 6 in 10 flagged loans are genuine defaults. The asymmetry is deliberate — missing a default costs 5× more than a false alarm, so the model is tuned to cast a wide net.

---

## The Baseline: Freezing the Training Distribution

After training, the pipeline saves a statistical snapshot of the training data. For each feature, it stores the full distribution — 99 percentiles for numerical features, category frequencies for categoricals. This baseline is the monitoring layer's reference point: *what did normal data look like when this model was trained?*

### Key Training Distributions (FY2010–2019)

| Feature | Mean | Std |
|---------|------|-----|
| gross approval | $342,726 | $638,863 |
| initial interest rate | 6.53% | 1.57% |
| term in months | 113 months | 75 months |

| Feature | Dominant category | Share |
|---------|-------------------|-------|
| processing method | SBA Express Program | 51.8% |
| business age | Existing 5+ years | 40.8% |
| business type | Corporation | 87.1% |

---

## The Drift: COVID‑19 as a Documented Distribution Shift

- **Production data:** SBA 7(a) FOIA loans, FY2020–present (373,974 rows)
- **Monitoring run:** Full production dataset compared against FY2010–2019 baseline

### Drift Results — All 12 Features

| Feature | PSI | Severity | Wasserstein (σ) | W. Severity |
|---------|-----|----------|----------------|-------------|
| business age | 7.614 | **Significant** | — | — |
| term in months | 3.840 | **Significant** | 0.337 | Moderate |
| initial interest rate | 1.755 | **Significant** | 1.460 | **Significant** |
| processing method | 0.788 | **Significant** | — | — |
| jobs supported | 0.743 | **Significant** | 0.049 | Low |
| subprogram | 0.708 | **Significant** | — | — |
| gross approval | 0.266 | **Significant** | 0.314 | Moderate |
| SBA guaranteed approval | 0.143 | Moderate | 0.318 | Moderate |
| collateral indicator | 0.064 | Low | — | — |
| business type | 0.059 | Low | — | — |
| fixed or variable interest | 0.024 | Low | — | — |
| revolver status | 0.019 | Low | — | — |

**Severity thresholds:**
- **PSI:** <0.1 = low, 0.1–0.25 = moderate, >0.25 = significant
- **Wasserstein:** <0.3σ = low, 0.3–0.8σ = moderate, >0.8σ = significant

**Summary:** 7 significant, 1 moderate, 4 low features drifted.

---

## What the Drift Means

### `business age` — PSI 7.614 (most drifted feature)
The distribution of business ages completely changed. Pre‑COVID, 40.8% of applicants were established businesses (5+ years old). COVID emergency programmes brought in newer, more vulnerable businesses seeking survival loans — a fundamentally different applicant pool.

### `initial interest rate` — PSI 1.755, Wasserstein 1.46σ
The Federal Reserve cut rates to near‑zero in March 2020. The training distribution was built on a decade of rates averaging 6.53%. The post‑COVID rate environment moved the entire distribution by 1.46 standard deviations — the strongest Wasserstein signal in the report.

### `term in months` — PSI 3.840, Wasserstein 0.34σ
Emergency loans came with different term structures than standard business lending.

### `processing method` and `subprogram` — PSI 0.788, 0.708
The SBA introduced entirely new emergency loan programmes in 2020. Processing methods that barely existed in training data became dominant.

### `gross approval` — PSI 0.266
Emergency loan sizes shifted away from the training distribution.

### Stable features
`collateral indicator`, `business type`, `fixed or variable interest`, and `revolver status` all show low drift (PSI < 0.1). The structural characteristics of loans didn't change much — the disruption was in who was applying and under what conditions.

---

## The System's Value

The monitoring layer raised the alarm on **7 features showing significant drift** — without needing loan outcomes. In credit lending, outcomes take 3–7 years to resolve fully.

By detecting input distribution shift at the point of production data arrival, the pipeline gives the Datatroniq team actionable signal months before the defaults materialise.

The `initial interest rate` drift alone — 1.46 standard deviations — signals that the macroeconomic regime has changed. A model trained on 6.53% average rates, now scoring applications at near‑zero rates, is operating outside its training distribution in the most consequential feature for credit risk.

**Catch silent degradation early, before it becomes a business problem.**

---

## Limitations and Future Work

- **Current scope:** Input distribution shift (covariate shift) only.
- **Future:** Monitor concept drift as outcomes materialise, using rolling AUC and calibration curves.
- **Retraining policy:** Manual trigger when significant drift is detected; automated retraining is a v2 item.

---

## Technical Summary

| Component | Detail |
|-----------|--------|
| Training data | SBA 7(a) FY2010–2019, 545,751 raw rows |
| Production data | SBA 7(a) FY2020–present, 373,974 rows |
| Selected model | Random Forest, threshold 0.23 |
| Test ROC‑AUC | 0.9721 |
| Drift metrics | PSI (all 12 features), Wasserstein (5 numerical features) |
| Severity thresholds | PSI: 0.1/0.25; Wasserstein: 0.3σ/0.8σ |
| Features with significant drift | 7 of 12 |
| Infrastructure | FastAPI · Docker · GCP Cloud Run · GitHub Actions CI |
| Tests | 110 passing |
| ADRs | 26 architectural decision records |
| Live API | https://ml-reliability-pipeline-1061232555311.europe-west1.run.app |

*Last updated: 2026‑06‑11*