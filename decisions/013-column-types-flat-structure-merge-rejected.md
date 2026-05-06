

# 013 — COLUMN_TYPES Flat Structure: Merge Rejected

**Date:** 2026-05-07
**Component:** Data validation layer (`src/data/`)
**Status:** Decided

---

## Context

ADR 008 introduced `COLUMN_TYPES` as a flat dict mapping column names to type strings. It deferred the question of whether to merge `COLUMN_TYPES`, the valid-value tuples, and `REQUIRED_COLUMNS` into a single richer structure. The deferral was deliberate — we needed real transformer and validator code before judging whether the merge would help.

That code now exists. The transformer reads from `COLUMN_TYPES` (for type coercion) and `STRING_COLUMNS` (for whitespace normalisation). The validator reads from `COLUMN_TYPES` (for type checks), the valid-value tuples (for coded value checks), and `REQUIRED_COLUMNS` (for nullness checks). Three separate schema constants, consumed across two layers.

---

## Decision

Keep the flat structure. Do not merge.

The three-lookup pattern has not caused a single bug. No column has been added where one of the three constants was forgotten. The separation is explicit — type, allowed values, and required-ness are distinct concerns, and keeping them in separate constants makes that distinction visible.

Merging now would touch every consumer of the schema just to solve a problem that hasn't happened. That is speculative refactoring — it adds risk for a benefit that may never materialise.

---

## Consequences

The schema stays as three separate constants. Consumers continue doing three lookups. The trigger that would reopen this decision is concrete: if a new column gets added and someone forgets to update one of the three, that failure is the evidence the merge was needed. Until then, flat stays.