
# Open Questions

Questions surfaced during build sessions that need follow-up reading.
Build takes priority — these get worked on a separate schedule.
Closed questions are answered ones, with full resolution including
alternatives, when to use / not use, and connections to other parts of
the system.

Status legend:
- 🔴 Open — flagged, not yet read
- 🟡 Reading — book/chapter in progress
- 🟢 Closed — answered and discussed (moved to Closed Questions section)

---

## Feature Selection

### Q1: Should every feature be used, or should some be pruned?
- **Status:** 🔴 Open
- **Surfaced in:** `src/models/trainer.py`
- **What we did:** All features from the schema are passed through to
  the pipeline. No feature selection step exists.
- **Reason given at the time:** Not discussed during the session. The
  feature set was accepted as-is from the data layer.
- **Where the answer lives:** Géron Ch. 2 (feature selection in
  practice); ISLP Ch. 6 (subset selection, regularisation as implicit
  selection)
- **Opened:** 2026-05-11

### Q2: Why are certain columns treated as numerical vs categorical?
- **Status:** 🔴 Open
- **Surfaced in:** `src/models/trainer.py`
- **What we did:** The caller passes `numerical_cols` and
  `categorical_cols` as separate lists. The split itself was inherited
  from the data layer's schema.
- **Reason given at the time:** Not discussed during the trainer.py
  session. The schema's type assignments were accepted without
  examination of edge cases (e.g. is `businessage` ordinal? are there
  numerical columns that should be binned?).
- **Where the answer lives:** Géron Ch. 2 (feature types and encoding
  choices); Zheng "Feature Engineering for Machine Learning" Ch. 2
  (numerical transformations, binning) and Ch. 5 (categorical encoding)
- **Opened:** 2026-05-11

---

## Model Families

### Q3: Why logistic regression, random forest, and XGBoost — not others?
- **Status:** 🔴 Open
- **Surfaced in:** `src/models/trainer.py`
- **What we did:** `trainer.py` accepts any sklearn-compatible
  estimator. The three named candidates are logistic regression, random
  forest, and XGBoost.
- **Reason given at the time:** Not discussed during the session. The
  three models were assumed as the candidate set.
- **Where the answer lives:** ISLP Ch. 4 (logistic regression); ISLP
  Ch. 8 (trees, bagging, boosting). Worth comparing to SVM, LightGBM,
  CatBoost, and simple neural networks to articulate why these three
  cover the design space for tabular credit data.
- **Opened:** 2026-05-11

### Q4: Is StandardScaler + OneHotEncoder appropriate for all three model families equally?
- **Status:** 🔴 Open
- **Surfaced in:** `src/models/trainer.py`
- **What we did:** Applied the same preprocessing pipeline regardless
  of which model is plugged in.
- **Reason given at the time:** Not discussed. The preprocessing was
  chosen as a sensible default; the question of whether tree-based
  models (random forest, XGBoost) actually benefit from scaling or
  one-hot encoding was not raised.
- **Why this matters:** Tree-based models split on individual feature
  thresholds and are scale-invariant — StandardScaler does nothing for
  them. They also handle high-cardinality categoricals poorly when
  one-hot encoded (creates many sparse splits). If true, our pipeline
  is doing unnecessary work for two of three models, and possibly
  hurting their performance.
- **Where the answer lives:** Géron Ch. 4 (why scaling matters for
  gradient-based models specifically); ISLP Ch. 8 (how tree splits
  work, why they're scale-invariant); XGBoost documentation on
  categorical feature handling
- **Opened:** 2026-05-11

---

## Evaluation Metrics

*(will be populated as we build evaluator.py — at minimum: which
metrics, why those, why not others, how to choose when business cost
of FP differs from FN)*

---

## Closed Questions

*(none yet — answered questions move here with their full resolved form)*