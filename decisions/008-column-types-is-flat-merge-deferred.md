
# 008 — COLUMN_TYPES is Flat, Merge Deferred

**Date:** 2026-05-04
**Component:** Data validation layer (`src/data/`)
**Status:** Decided

---

## Context

`COLUMN_TYPES` is being added to 'schema.py' to declare the expected type of each column after transformation. Two design options exist: keep it flat (`{column: type_string}`) with valid-value tuples as separate top-level constants, or merge everything into a richer structure (`{column: {"type": ..., "valid_values": ...}}`).

The transformer does not exist yet. Without real transformer code to evaluate against, the richer structure is speculative.

---

## Decision

`COLUMN_TYPES` is a flat dict mapping column name to type string. Derived view tuples (`STRING_COLUMNS`, `INTEGER_COLUMNS`, `FLOAT_COLUMNS`, `DATE_COLUMNS`) are computed from it. Existing valid-value tuples stay as separate top-level constants.

The merge into a richer schema object is deferred to ADR 010, to be written after 'transformer.py' exists and the trade-offs are concrete.

---

## Consequences

Simple now. No speculative nesting. The flat structure is easy to read, easy to compute derived views from, and easy to change later.

The operational cost: consumers validating a column must consult both `COLUMN_TYPES` (for the expected type) and the separate valid-value tuples (for allowed values). These are two lookups, not one. This friction is the evidence ADR 010 will weigh when deciding whether to merge.

If future evidence shows merging would reduce bugs or duplication, the refactor is straightforward. If not, nothing was overbuilt. The trigger for revisiting is real transformer code, not imagined scenarios.
