# 027 — Drift Response Strategy: Rebaselining, Retraining, and Why v1 Stops at Detection

**Date:** 2026-06-11
**Component:** Monitoring layer (design-level; no code in v1)
**Status:** Decided — detection-only for v1; closed-loop response deferred with documented preconditions

---

## Relationship to prior ADRs

This ADR answers the question every reader of ADR 023 eventually asks: *the system has detected drift — now what?* It defines what a correct drift response would look like, documents one tempting-but-wrong response that was explicitly considered and rejected, and explains why the correct response cannot be built honestly on the current label definition.

This ADR depends on:
- **ADR 002** — FY2010–2019 as training data, FY2020+ as simulated production. The drift this ADR responds to is the (deliberate, COVID-driven) shift between those windows.
- **ADR 023** — The baseline snapshot is a frozen description of the *training* distribution. That framing is load-bearing here: it is the reason one of the options below is wrong.
- **ADR 025** — The monitoring layer that produces the drift signal this ADR consumes.

---

## Context

The monitoring run on FY2020+ data fires at maximum severity (see `docs/case-study.md`). The natural follow-up idea: split the FY2020–present data into two temporal halves; use the first half to update the system; use the second half to verify the update helped.

The question is *what* gets updated. Two candidate loops were considered.

---

## Options considered

**A: Rebaseline only.** Recompute the baseline snapshot from the first half of production data. Monitoring the second half against the new baseline would show drift back below thresholds.

Rejected. The baseline is not a description of "what data looks like lately" — per ADR 023 it is a description of *what the model was trained on*. Updating the baseline without updating the model decouples the monitor from the thing it monitors: drift metrics would report "all clear" while the model continues to score applicants from a distribution it has never seen. The reduced drift on the second half is nearly tautological (adjacent periods resemble each other) and proves nothing about prediction quality. This option silences the alarm without putting out the fire. It is recorded here because it is an easy mistake to make and a common one in practice: **the baseline must only ever change as a byproduct of retraining, never as an independent action.**

**B: Retrain, validate, promote atomically.** Retrain the model on the first (earlier) half; evaluate the incumbent model and the retrained challenger on the second (later) half; promote the challenger only if it wins; regenerate the baseline from the challenger's training set in the same operation (`baseline_saver` already derives the snapshot from training data, so atomicity is structurally guaranteed).

This is the correct loop — a standard champion/challenger drift response. It is the design target. It is *not* implemented in v1, for the reason below.

---

## Why option B cannot be evaluated honestly today

The loop requires measuring model performance on the second half of FY2020+ data. That requires labels. Under the current label definition (loan status = `pif` or `chgoff`, i.e. *resolved* outcomes only):

1. Most FY2020+ loans have not resolved — outcomes take years. The evaluable subset is small.
2. Worse, the subset that *has* resolved by the data pull date is maximally selection-biased: short-term loans and early chargeoffs, almost nothing else. Any performance number computed on it is dominated by resolution-time censoring, not by model quality.

So the verification step of the loop — the entire point of holding out the second half — would produce numbers that cannot be trusted. Building the loop without fixing this would be reliability theater: a retraining pipeline whose promotion decisions rest on a biased metric.

**Precondition for v2:** redefine the label as a fixed-horizon outcome (e.g. *charged off within 24 months of approval*). Under that definition every loan at least 24 months old is fully observable, the censoring asymmetry disappears, and recent vintages become usable for both retraining and champion/challenger evaluation. This touches `dataset_builder`, the baseline, and the registry, and changes what the model predicts — it is a v2-scale refactor, not a patch.

A secondary open question, deliberately left empirical: whether the challenger should train on recent data only or on a longer rolling window. The FY2020–21 regime (emergency programs, rate environment) partially reverted afterward; a model trained purely on it may generalize worse to later vintages than one trained on a combined window. The champion/challenger harness, once it exists, is itself the right instrument to answer this.

---

## Decision

v1 is a **detection system, not a closed-loop system**, and says so plainly. The drift signal's value in v1 is as an *early-warning trigger for human investigation* — which, in a domain where outcome labels lag origination by years, is the only signal available at all. The closed loop (option B) is the documented design target, gated on the fixed-horizon label redesign. Option A is recorded as rejected and must not be implemented in any version.

---

## Consequences

- The case study's "Limitations" section gains a pointer to this ADR, replacing vaguer wording about retraining being out of scope.
- Any future change to `data/baseline/` contents must originate from a training run. There is no supported path to regenerate the baseline alone; if one is ever added for operational reasons, it must carry the model version it was derived from so monitor/model coupling stays verifiable.
- The v2 label redesign (fixed-horizon default) is now the documented prerequisite for both the retraining loop and the resolution-censoring concerns raised during model evaluation — one refactor unblocks both.