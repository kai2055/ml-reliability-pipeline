
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

### Q5: Which metrics should evaluator.py compute, and why those four?
- **Status:** 🔴 Open — decided conceptually, ADR pending after code
- **Surfaced in:** `src/models/evaluator.py` (pre-build session)
- **What we decided:** Four metrics — Precision, Recall, AUC, Log Loss
- **Reason for each:**
  - Precision — of every loan Datatroniq approved, how many actually
    repaid. Measures the quality of the approval decision itself.
  - Recall — of every applicant who would have repaid, how many did
    the model catch. Measures coverage of good applicants.
  - AUC — how well the model separates defaulters from repayers across
    all possible thresholds at once. Threshold-independent. Tells you
    if the model is fundamentally capable before the risk team decides
    where to set the threshold.
  - Log Loss — measures probability calibration quality, not just the
    hard label. Penalises confident wrong predictions heavily. A model
    that says 95% repayment probability and gets a default is punished
    far more than one that said 52%.
- **Why not accuracy:** Accuracy treats both error types as equally
  costly. At Datatroniq they are not — approving a defaulter is a
  direct financial loss, rejecting a good applicant is missed revenue.
  Accuracy would hide this asymmetry.
- **Why not just precision and recall:** They only measure the hard
  decision at a fixed threshold. They say nothing about whether the
  model's probability estimates are trustworthy. Log Loss and AUC fill
  that gap.
- **Where the answer lives:** Zheng — Evaluating Machine Learning
  Models (the whole book is relevant here); Géron Ch. 3 (classification
  metrics in practice)
- **ADR status:** Pending — to be written after evaluator.py is built
- **Opened:** 2026-05-11

---


## Cross-Validation Strategy

### Q6: Why stratified k-fold over random k-fold, and why k=5?
- **Status:** 🔴 Open — decided conceptually, ADR pending after tuner code
- **Surfaced in:** `src/models/tuner.py` (pre-build session)
- **What we decided:** Stratified k-fold cross-validation with k=5
- **Reason — stratified over random:**
  Credit risk is imbalanced at Datatroniq — roughly 80% repay, 20%
  default. Random k-fold can produce chunks with skewed class
  proportions, distorting the cross-validation result for one fold
  relative to another. Stratified k-fold constructs each chunk to
  preserve the original class proportions. Every fold has roughly the
  same repay/default ratio. Scores across folds become comparable.
- **Reason — k=5 over alternatives:**
  k=2 trains each model on only 50% of available data and averages
  only two scores — both underestimate performance and amplify noise.
  k=100 explodes compute by 100x, produces nearly-identical training
  sets across rounds (highly correlated scores), and gives tiny
  validation sets that are themselves noisy. k=5 trains on 80% of
  data, validates on 20%, averages five reasonably independent scores
  — the standard default. k=10 is the next reasonable choice when
  stability matters more than compute time, but k=5 is enough for
  Datatroniq's scale.
- **Why this matters at Datatroniq:** A model selected via
  unstratified CV on imbalanced data may look good in aggregate while
  silently performing poorly on the minority class — exactly the
  defaulters the model is supposed to identify. The cross-validation
  procedure itself becomes a source of silent degradation if not
  chosen with the class imbalance in mind.
- **Where the answer lives:** Géron Ch. 2 (cross-validation in
  practice); ISLP Ch. 5 (resampling methods — k-fold, LOOCV, the
  bias-variance tradeoff of k)
- **ADR status:** Pending — to be written after tuner.py is built
- **Opened:** 2026-05-11

## Closed Questions

*(none yet — answered questions move here with their full resolved form)*