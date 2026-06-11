

# 011 — REQUIRED_COLUMNS and Nullness Validation Architecture

**Date:** 2026-05-07
**Component:** Data validation layer (`src/data/`)
**Status:** Decided

---

## Context

The validator had no way to distinguish columns that must never be null from columns where nulls are legitimate. Without this distinction, two failure modes exist: either all nulls are treated equally (missing borrower names and missing franchise codes look the same), or the validator has no nullness check at all.

Evidence from the full dataset (545,751 rows) showed a clear split. Seven columns had zero nulls across every row: `program`, `loanstatus`, `approvaldate`, `grossapproval`, `revolverstatus`, `initialinterestrate`, and `terminmonths`. These are structural — a loan without a program identifier or a loan status is not a loan record, it is a corrupted row.

Other columns are legitimately nullable. `franchisecode` is 95% null because most businesses are not franchises. `franchisename` is similarly sparse. `chargeoffdate` and `paidinfulldate` are null for any loan that has not yet reached that outcome. These nulls are not errors — they are correct representations of the data.

The validator needed a way to encode this distinction. Seven columns must be present and non-null. Everything else permits nulls.

---

## Decision

A new schema constant `REQUIRED_COLUMNS` is introduced — a tuple of column names that must never contain null values. It is stored as a separate top-level constant in `schema.py`, not merged into `COLUMN_TYPES`. The reasoning: whether a column is required is orthogonal to its data type. Merging would create a composite structure (`{column: {type, required, ...}}`) that ADR 008 already deferred. When that merge is revisited in ADR 013, required-ness joins the discussion. For now, a separate tuple keeps the structure simple and the concerns visible.

The nullness check is non-fatal. Missing values in required columns are flagged in the validation report but do not reject the dataset. The reasoning: a structural problem (wrong columns, wrong file) makes every downstream check unreliable and warrants immediate rejection. A content problem (a few null borrower names in 545,751 rows) is a data quality issue worth flagging but does not render the dataset unusable. The data team can decide whether to drop those rows, investigate the source, or proceed with them excluded.

Cross-column conditional checks are explicitly deferred. The requirement "FDIC number OR NCUA number must be non-null" is a valid constraint — every bank should have one identifier or the other — but it is a different category of check (logical consistency, not column-level nullness) and will be addressed separately.

---

## Consequences

The validator now has a principled nullness check. Seven structural columns are enforced. Nullable columns are correctly permitted without false positives. The validation report distinguishes between "required column has nulls" (flagged, non-fatal) and "column is missing entirely" (already caught by `check_columns`, fatal).

**Cost:** Two lookups instead of one — `COLUMN_TYPES` for type, `REQUIRED_COLUMNS` for nullness. This friction is the same trade-off documented in ADR 008. If future evidence shows the composite structure would reduce bugs, the merge happens then.

**Deferred:** Cross-column conditional checks. Not forgotten — explicitly noted here so they have a clear place to land when addressed.
