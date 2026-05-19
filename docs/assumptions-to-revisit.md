
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
- **Status:** 🔴 Open — partially closed; broader metrics debate remains open
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
- **ADR status:** ADR 015 documented the evaluator's metric choices for
  v1. ADR 021 (model selection and threshold policy) closes the
  threshold-setting subset of this question by establishing expected
  cost as the selection criterion and a vectorised threshold sweep as
  the mechanism. The broader debate — whether the v1 metric set is
  sufficient as monitoring matures, and what additional metrics (e.g.
  calibration over time, decile lift, KS statistic) should be tracked —
  remains open.
- **Opened:** 2026-05-11

---







**Feature Engineering (v2 candidates)**

### Q7: Should `naicscode` be re-introduced as a bucketed industry feature?
- **Status:** 🔴 Open
- **Surfaced in:** ADR 017
- **What we did:** Excluded `naicscode` from v1 features. Its raw 6-digit cardinality (thousands of unique codes) would flood the one-hot encoded feature space.
- **Reason given at the time:** Industry information likely carries real predictive signal (restaurants and medical practices have different default rates) but the raw column is unusable without engineering. v2 work — bucket at 2-digit (~20 sectors) or 3-digit (~100 subsectors) level.
- **Where the answer lives:** Géron Ch. 2 (binning and bucketing); the NAICS hierarchy documentation directly; v2 experiment comparing 2-digit and 3-digit aggregation against v1 baseline.
- **Opened:** 2026-05-15




### Q8: Should bank-level historical features be engineered from `bankfdicnumber`?
- **Status:** 🔴 Open
- **Surfaced in:** ADR 017
- **What we did:** Excluded `bankfdicnumber` from v1 features. Hundreds of unique values, no useful raw treatment.
- **Reason given at the time:** Could be engineered into bank-level features — origination volume, historical default rate, average loan size by bank. These would generalise where the raw identifier doesn't. Careful target-leakage management needed (the bank's historical default rate must be computed only on past, resolved loans, not the loan currently being scored).
- **Where the answer lives:** Zheng "Feature Engineering for Machine Learning" Ch. 7 (target encoding, mean encoding, and the leakage traps that come with them).
- **Opened:** 2026-05-15




### Q9: Should date-derived features be engineered?
- **Status:** 🔴 Open
- **Surfaced in:** ADR 017
- **What we did:** Excluded all date columns from v1. `approvaldate` and `firstdisbursementdate` are not available pre-approval. `asofdate` carries no signal. `approvalfy` was excluded as a temporal proxy.
- **Reason given at the time:** If drift monitoring reveals that temporal patterns matter — economic cycles, seasonality, post-COVID effects — date-derived features could be engineered (year buckets, days-between-events, month-of-year). For v1, the drift pipeline is responsible for handling temporal effects.
- **Where the answer lives:** Géron Ch. 2 (date feature engineering); the drift detection results from v1 itself, once deployed.
- **Opened:** 2026-05-15



### Q10: Are `subprogram` and `processingmethod` redundant?
- **Status:** 🔴 Open
- **Surfaced in:** ADR 017
- **What we did:** Kept both features for v1, accepted potential redundancy.
- **Reason given at the time:** Both describe "what kind of 7(a) loan is this." Without inspecting co-occurrence in the actual data, we couldn't tell whether they carry overlapping information. v1 keeps both — multicollinearity doesn't bother tree-based models, and may only weakly affect logistic regression at small dataset sizes.
- **Where the answer lives:** Inspect the data directly (cross-tab of `subprogram` × `processingmethod`); compare feature importances from the random forest run; ISLP Ch. 6 on collinearity in linear models.
- **Opened:** 2026-05-15




###  **Governance & Fairness**
 
### Q11: Should geographic features be re-introduced after fairness analysis?
- **Status:** 🔴 Open
- **Depends on:** Q12
- **Surfaced in:** ADR 017
- **What we did:** Excluded `borrstate`, `projectstate`, and `sbadistrictoffice` from v1 features.
- **Reason given at the time:** Manageable cardinality (~50 US states, ~70 SBA district offices), but geographic features in credit decisions can act as proxies for protected attributes like race. Re-introduction requires a formal fairness analysis the project is not yet equipped to do.
- **Where the answer lives:** Q12's resolution must come first. After that, v2 PR with a fairness analysis ADR comparing the v1 baseline against a model with geographic features included.
- **Opened:** 2026-05-15


### Q12: What is the fairness review process for any feature that could proxy for protected attributes?
- **Status:** 🔴 Open
- **Blocks:** Q11
- **Surfaced in:** ADR 017
- **What we did:** Did not establish a fairness review process for v1. Excluded geographic features rather than introduce features without one.
- **Reason given at the time:** A fairness analysis is a governance artifact, not a code artifact. It requires deciding what protected attributes are relevant (race, gender, age, national origin), what disparate-impact metrics to compute (equal opportunity, demographic parity, predictive parity), and what threshold of disparity is acceptable. v1 ships without this; the analysis is a precondition for any feature that could proxy for a protected attribute.
- **Where the answer lives:** Berlin/EU regulatory guidance on fair lending (GDPR, AI Act); academic literature on fairness metrics in ML (Barocas, Hardt, Narayanan); existing fairness analysis frameworks from regulated fintechs.
- **Opened:** 2026-05-15



 **Feature Availability (clarification needed)**
 
### Q13: What does `soldsecmrktind` represent — origination intent or post-origination outcome?
- **Status:** 🔴 Open
- **Surfaced in:** ADR 017
- **What we did:** Excluded `soldsecmrktind` from v1 features conservatively.
- **Reason given at the time:** Could represent the lender's intent at origination to sell the loan into the secondary market (available at prediction time, usable as a feature) or could represent whether the loan was actually sold at some later point (post-origination, leakage). The SBA data dictionary entry is ambiguous on this point. v1 excludes it; if the semantics are clarified and it represents intent, v2 could re-introduce it.
- **Where the answer lives:** SBA 7(a) data dictionary detail page for `soldsecmrktind`; SBA loan origination process documentation; possibly contact SBA data steward directly.
- **Opened:** 2026-05-15


## Threshold Policy & Cost Modelling

These are v2 candidates tied to the monitoring layer's feedback loop. They have concrete change drivers (drift signals), not hypothetical flexibility.

### Q14: How should the cost ratio be re-estimated when business conditions shift?
- **Status:** 🔴 Open
- **Surfaced in:** ADR 021
- **What we did:** Chose a hand-picked cost ratio (`cost_fn=5, cost_fp=1`) for v1 as a documented placeholder. The ratio is recorded on `SelectionResult.cost_ratio` for audit.
- **Reason given at the time:** Real Datatroniq P&L data doesn't exist (fictional company). Computing from SBA data conflates known loss-given-default with unknown counterfactual revenue. Hand-chosen ratio with documented reasoning is the most honest v1 stance.
- **Why this matters:** The threshold is a function of the cost ratio. When monitoring detects drift (interest rate changes, recovery rate shifts, regulatory changes), the cost ratio used at v1 selection time may no longer reflect business reality. Without a re-estimation process, the system silently uses a stale assumption.
- **Where the answer lives:** Banking/credit-risk literature on cost-sensitive learning. FDIC reports on small business lending economics. Conversations with credit-risk practitioners about how operational ratios are re-estimated in production fintechs.
- **Opened:** 2026-05-21



### Q15: When does the threshold need re-computation, and how is the new threshold derived?
- **Status:** 🔴 Open
- **Depends on:** Q14 (cost ratio must be settled before threshold re-derivation makes sense)
- **Surfaced in:** ADR 021
- **What we did:** Computed the v1 threshold by minimising expected cost on FY2010–2019 validation data. The threshold is recorded on `SelectionResult.threshold` for audit.
- **Reason given at the time:** Threshold-setting is a one-shot decision in v1. The monitoring layer is responsible for detecting when the v1 threshold is no longer appropriate.
- **Why this matters:** When FY2020+ production data drifts away from training distribution, the model's predicted probabilities become less calibrated. The same threshold value (e.g. 0.27) applied to a model whose probabilities now mean something different produces different decisions than intended. Without a re-computation protocol, this becomes silent degradation by another name.
- **Constraint:** Any re-computation must not contaminate the test set. A re-derived threshold based on production data is essentially re-tuning — it requires fresh held-out data, a new ADR, and possibly a model retrain.
- **Where the answer lives:** Drift detection literature on adaptive thresholding. Production ML papers on retraining triggers. The monitoring layer's own output once v1 is deployed will inform this.
- **Opened:** 2026-05-21



## Closed Questions

### Q1: Should every feature be used, or should some be pruned?
- **Status:** 🟢 Closed
- **Resolved by:** ADR 017
- **Surfaced in:** `src/models/trainer.py`
- **What we decided:** Of the 42 columns in the schema, 12 are used as features for v1. One is the target. 29 are excluded.
- **Reasoning:** A column has to pass four checks to make it into v1 — available at prediction time, has enough variation to carry signal, cardinality is manageable, no governance concerns we can't yet handle. Exclusions group naturally: outcome columns (target leakage), identifiers (no generalisation), geographic features (fairness governance deferred), date columns (not available pre-approval), temporal proxies, columns with no variation, and one column whose semantics are unclear.
- **Alternatives considered:**
  - *Use all features.* Rejected — would have introduced target leakage from outcome columns and flooded the feature space with high-cardinality identifiers.
  - *Use only obviously numerical columns.* Rejected — too restrictive, would have dropped real categorical signals like `subprogram` and `businessage`.
  - *Engineer features now (NAICS bucketing, geographic features after fairness review).* Deferred to v2. Adding feature engineering before the v1 baseline exists makes future improvements unevaluable.
- **When this resolution holds:** For v1, against the SBA 7(a) loan data, for a pre-approval binary classification model.
- **When to revisit:** Each v2 PR adds or modifies features against a measured v1 baseline. Q9–Q13 below are the open v2 feature questions opened by ADR 017.
- **Connections:**
  - ADR 016 establishes `dataset_builder.py` as the file where these decisions live.
  - ADR 017 documents the full feature list with per-column reasoning.
  - The drift detection pipeline this project builds will catch when the v1 feature set stops being adequate — that's the signal to revisit, not abstract claims about what "should" help.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-15

---

### Q2: Why are certain columns treated as numerical vs categorical?
- **Status:** 🟢 Closed
- **Resolved by:** ADR 017
- **Surfaced in:** `src/models/trainer.py`
- **What we decided:** Within the 12 v1 features, 5 are numerical (scaled) and 7 are categorical (one-hot encoded). The dtype declared in `schema.py` does not automatically determine the modelling treatment.
- **Reasoning:** The schema declares dtype — what Python type best represents the column. The model layer declares semantic role — whether a column is a continuous quantity the model should reason about linearly, or a category the model should treat as discrete. These can disagree. `revolverstatus` is integer-typed but is a 0/1 flag, so it's categorical for modelling. `jobssupported` is integer-typed and is a genuinely continuous quantity (10 jobs is meaningfully twice 5 jobs), so it's numerical. `terminmonths` is the same case as `jobssupported`.
- **Alternatives considered:**
  - *Derive feature groups mechanically from `STRING_COLUMNS`, `INTEGER_COLUMNS`, `FLOAT_COLUMNS`.* Rejected — would have treated `revolverstatus` as numerical (wrong) and `approvalfy` as a meaningful continuous feature (wrong). Mechanical derivation cannot tell flags apart from quantities.
  - *Treat everything as categorical.* Rejected — destroys the actual continuous signal in columns like `grossapproval` and `initialinterestrate`.
  - *Treat everything as numerical.* Rejected — categorical features like `businesstype` and `processingmethod` have no meaningful ordering or scale.
- **When this resolution holds:** For v1, for the current 12 features, with `StandardScaler` and `OneHotEncoder`.
- **When to revisit:** When v2 feature engineering changes which columns are features, or if Q4 (preprocessing across model families) closes and tree-based models stop needing the same preprocessing as logistic regression.
- **Connections:**
  - ADR 017 documents the specific groupings.
  - Q4 (is `StandardScaler + OneHotEncoder` appropriate for all three model families?) remains open and could shift this in v2.
  - The `NUMERICAL_FEATURES` and `CATEGORICAL_FEATURES` constants in `dataset_builder.py` are the single source of truth for these groupings — both `trainer.py` and `tuner.py` import from there.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-15
---




## Cross-Validation Strategy

### Q6: Why stratified k-fold over random k-fold, and why k=5?
- **Status:** 🟢 Closed
- **Resolved by:** ADR 018
- **Surfaced in:** `src/models/tuner.py`
- **What we decided:** Stratified k-fold cross-validation with k=5, shuffle=True, random_state=42. Defined as a module-level constant `CV` in `tuner.py`, shared across all tuning configs.
- **Reasoning:**
  - *Stratified over random:* The target classes are imbalanced (pif majority, chgoff minority). Random k-fold can produce folds with skewed class proportions, distorting cross-validation results fold to fold. Stratified k-fold preserves the class ratio in every fold so scores across folds are comparable.
  - *k=5:* k=5 trains each model on 80% of the data and averages five reasonably independent scores — the conventional default for a reason. k=3 produces high-variance estimates over too few folds. k=10 doubles compute cost for marginal accuracy gain. The SBA dataset is large enough that 5 folds give stable estimates, and Random search with n_iter=20 × 5 folds = 100 fits is already a substantial compute budget.
  - *shuffle=True:* Without shuffling, `StratifiedKFold` preserves row order within strata. SBA loan data has temporal structure (applications come in over time); unshuffled folds can introduce subtle leakage where earlier rows train and later rows test. Shuffling breaks this.
- **Alternatives considered:**
  - *Random (unstratified) k-fold.* Rejected — on imbalanced data, fold class ratios can drift, inflating CV variance and silently degrading the metric estimate for the minority class.
  - *k=10 instead of k=5.* Considered. Marginal stability gain, 2× compute cost. k=5 chosen as the sufficient default; k=10 remains a reasonable v2 option if stability becomes a concrete concern.
  - *Time-series CV (e.g. `TimeSeriesSplit`).* Deferred to v2. Could matter if drift monitoring surfaces temporal patterns that v1 CV is not respecting. Not tied to a specific feedback loop in v1's design, so YAGNI applies.
- **When this resolution holds:** For v1, for the current binary classification target, with the SBA dataset's class imbalance and (assumed) IID-within-stratum behaviour.
- **When to revisit:** When v2 drift monitoring suggests temporal effects matter (move to time-series CV); when class imbalance shifts substantially (re-validate stratification assumptions); when compute budget allows k=10 to be evaluated against k=5.
- **Connections:**
  - ADR 018 documents the full tuning architecture including the CV choice.
  - The `CV` constant in `tuner.py` is the single source of truth — all three tuning configs share it.
  - This decision is structurally separate from `scoring` (Q5 / ADR 015 / ADR 018) — scoring is per-config policy, CV is shared mechanics. The split is documented in ADR 018, decision 9.
- **Opened:** 2026-05-11
- **Closed:** 2026-05-17