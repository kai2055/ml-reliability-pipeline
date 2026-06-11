
# 009 — Schema Type Tags Are Semantic Strings, Not Python Types

**Date:** 2026-05-05
**Component:** Data validation layer (`src/data/`)
**Status:** Decided

---

## Context

`COLUMN_TYPES` declares the type of each column after transformation. The values in the dict could be either Python type objects (`str`, `int`, `float`) or string tags (`"string"`, `"integer"`, `"float"`, `"date"`). The two conventions look similar at a glance and are easy to confuse — yesterday's drafting session produced exactly this slip, with `"str"` written where `"string"` was intended.

The failure mode is silent. Derived views filter the dict by string equality:

```python
STRING_COLUMNS = tuple(c for c, t in COLUMN_TYPES.items() if t == "string")
```

If even one entry in the dict uses the Python type name `"str"` instead of the tag `"string"`, that column is silently excluded from `STRING_COLUMNS`. The transformer then skips it. No error is raised — the program runs to completion, but with incomplete coverage. This is the same class of failure the project's drift-detection pipeline exists to catch in production: things that don't crash but quietly do the wrong thing.

A separate consideration: Python's built-in types are a fixed vocabulary. There is no built-in type for "date" (it lives in `datetime`), and no type at all for project-specific concepts like "percentage" or "identifier." Forcing the dict's values to be Python types would either force inconsistency (mix of builtins and imports) or limit what the schema can express.

---

## Decision

`COLUMN_TYPES` values are tag strings, not Python type objects. The four tags currently in use are `"string"`, `"integer"`, `"float"`, and `"date"`. These are project vocabulary — not aliases for Python types. The transformer reads each tag and decides what mechanical operation to apply; the tag itself is just a label.

This convention is enforced by consistent use throughout `schema.py` and by every consumer (transformer, validator, derived views) filtering on the same exact strings.

---

## Consequences

**Gain — extensibility.** The tag vocabulary is open. New categories that have no Python-type equivalent — `"percentage"`, `"currency_eur"`, `"identifier"`, `"boolean"` — can be added when the project needs them, with no restructuring of the dict. The transformer adds a branch; everything else keeps working.

**Gain — uniformity.** All four current tags follow the same pattern (one lowercase word, descriptive of the post-transformation type). There is no mixing of builtin types and imported types, no special-casing for "date" because it lives in a module rather than as a builtin.

**Cost — convention overhead.** A reader unfamiliar with the codebase will see `"string"` and reasonably wonder why the dict uses a string label instead of `str`. The convention has to be either obvious from context or documented. This ADR is the documentation; consistent use across `schema.py` is the context.

**Cost — silent slips remain possible.** Typing `"string"` or `"Integer"` would still produce silent failures of the same kind. A future hardening step (validation that every value in `COLUMN_TYPES` is one of the four allowed tags) would close this gap, but is not required by this ADR.
