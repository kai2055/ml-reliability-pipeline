

# 015 — evaluator.py Design Decisions

**Date:** 2026-05-11
**Component:** src/models/evaluator.py
**Status:** Decided

---

## Context

Building the evaluator required two decisions: which metrics to compute,
and how to structure the functions. Both decisions have direct
consequences for how the risk team at Spreekredit interacts with model
output and how the monitoring layer consumes evaluation results.

---

## Decision

**Two functions over one**

The file exposes two functions — predict() and evaluate() — rather than
a single combined function. predict() takes a fitted pipeline and test
features and returns a DataFrame of probabilities and hard labels.
evaluate() takes that DataFrame and true labels and returns a metrics
dict.

The separation exists because predictions and metrics serve different
consumers. The monitoring layer may need raw predictions for drift
analysis without recomputing metrics. Future runs may want to compare
predictions across models before committing to a metric summary.
Combining both into one function would couple two distinct concerns and
remove that flexibility.

**Four metrics — precision, recall, ROC AUC, log loss and Brier score**

Accuracy was considered and rejected. At Spreekredit, approving a
defaulter is a direct financial loss and rejecting a good applicant is
missed revenue. These are not symmetric errors. Accuracy treats them as
equally costly and would hide the asymmetry that actually matters to the
business.

Precision measures the quality of approval decisions — of every loan
approved, how many actually repaid. Recall measures coverage — of every
applicant who would have repaid, how many did the model catch. Together
they capture the precision-recall tradeoff that the risk team manages
through threshold policy.

ROC AUC is threshold-independent. It measures how well the model
separates defaulters from repayers across all possible thresholds at
once. This is the right metric for comparing two models before the risk
team has decided where to set the threshold.

Log loss and Brier score measure probability calibration quality, not
just the hard label. A model that says 95% repayment probability and
gets a default should be penalised more heavily than one that said 52%.
Precision and recall would not catch this. Log loss and Brier score do,
from two different angles — log loss penalises confident wrong
predictions exponentially, Brier score measures mean squared error
between predicted probability and outcome.

**Default threshold of 0.50**

The threshold is a business lever, not an algorithm detail. The risk
team should be able to tighten it in a downturn and loosen it in a
growth phase without touching source code. For this reason threshold is
exposed as a parameter in predict() rather than hardcoded.

The default is set to 0.50 because it is the universal baseline every
data scientist expects. Calling predict(pipeline, X) should work without
requiring a business decision upfront. The default is explicit in the
signature and documented in the docstring so no caller is surprised. When
the risk team has a policy decision to make, they override it. Until
then, 0.50 is the sensible starting point.

---

## Consequences

The metrics dict returned by evaluate() is the direct input to
log_and_save() in trainer.py. The keys must stay stable — renaming a
metric key breaks the logging call without a visible error.

The threshold default means experiments run consistently at 0.50 unless
overridden. If the risk team changes their policy threshold, they need
to pass it explicitly — it will not change automatically. That friction
is intentional. Threshold changes should be deliberate.
