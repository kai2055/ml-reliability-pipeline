# 002 — Dataset Split Strategy

**Date:** 2026-04-30  
**Component:** Data validation layer / Drift detection  
**Status:** Decided

---

## Decision: Use FY2010–2019 as training data and FY2020–Present as production data

**What I decided:** Split the two SBA 7(a) files by role. The 2010–2019 file becomes the training dataset and the baseline. The 2020–Present file becomes the simulated production dataset that the monitoring layer watches.

**What changed my thinking:** My original plan was to use only the FY2020–Present file and split it into pre-COVID and post-COVID periods. I assumed there would be enough pre-COVID data inside that file to build a reliable baseline. When I opened the file, the earliest approval date was December 2020 — nine months after COVID had already hit. There was no usable pre-COVID data in that file at all.

**Why this split makes sense:**
- The 2010–2019 file represents stable, pre-COVID lending conditions. This is what the model learns from and what the baseline distribution is built on.
- The 2020–Present file represents a world the model has never seen — COVID disrupted small business lending significantly. Applicant profiles changed, industries that were previously low risk became high risk, and loan patterns shifted.
- This gives us a clean, real, documented before-and-after. The drift is not simulated — it actually happened.

**The monitoring narrative this enables:**
1. Model trained on 2010–2019 data
2. Baseline distribution snapshot saved from training data
3. 2020–Present data fed in as simulated production traffic
4. Monitoring layer detects drift — PSI and KS scores flag that incoming data no longer looks like training data
5. Silent degradation becomes visible before business outcomes are affected
6. Further stretch goal: split the 2020–Present data in two halves — use the first half to show drift and performance degradation, then retrain a new model using monitoring layer findings, and use the second half to show the updated baseline performing better. This demonstrates how baselines evolve over time in a real production system.

**Why this makes the project stronger:** Most drift detection demos simulate drift artificially. This project uses a real economic event as the drift signal. That is a more honest and more compelling demonstration of what a monitoring layer is actually for.