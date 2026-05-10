
# 014 — trainer.py Design Decisions

**Date:** 2026-05-10
**Component:** src/models/trainer.py
**Status:** Decided

---

## Context

Building the first file in the models layer required several decisions
about preprocessing choices, function design, and persistence strategy.
Each decision had at least one reasonable alternative. The reasoning
needed to be recorded so future changes have a reference point.

---

## Decision

**StandardScaler over MinMaxScaler**
Credit risk data contains outliers — unusually large loans, edge-case
applicants. MinMaxScaler scales relative to the minimum and maximum
values in the column, meaning a single outlier compresses every other
value toward zero. StandardScaler scales relative to mean and standard
deviation, making it robust to outliers. All features are represented
in relation to their spread around a mean of zero.

**OneHotEncoder over OrdinalEncoder**
Loan program type, region, and similar categorical columns have no
natural ordering. OrdinalEncoder assigns integers sequentially, which
implies later categories are greater than earlier ones. The model would
learn a false ordering that does not exist in the data. OneHotEncoder
creates a separate binary column per category, giving each label equal
weight with no implied ranking.

**build_pipeline() accepts columns as arguments**
The modeling layer is an experimentation phase. Different column
combinations, different models, and different configurations need to be
tried. Importing column lists directly from schema would require
modifying schema.py for every experiment, affecting all other parts of
the system that depend on it. Accepting columns as arguments keeps the
function flexible and decoupled. In production the caller retrieves
columns from schema, preserving schema as the source of truth without
coupling the function to it.

**Dual persistence — MLflow and joblib**
MLflow stores the model as part of the experiment run — queryable,
versioned, tied to its params and metrics, and deployable via MLflow
tooling. Joblib stores the model as a portable file loadable by any
Python script without MLflow installed. The monitoring layer needs to
load the model directly without MLflow context. Both copies serve
different consumers.

---

## Consequences

Preprocessing choices are documented with their tradeoffs. If the data
distribution changes and a different scaler becomes appropriate, the
reasoning for the current choice is already here.

The function signature decision means tests can pass arbitrary column
lists without touching schema. Experimentation stays isolated.

The dual persistence adds a small amount of redundancy but removes a
hard dependency on MLflow for anything that just needs the model file.