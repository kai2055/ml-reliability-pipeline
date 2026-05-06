
# 010 — Schema Corrections from Validator Findings

**Date:** 2026-05-06
**Component:** Data validation layer (`src/data/`)
**Status:** Decided

---

## Context

The initial schema was built from the SBA data dictionary plus a smoke test of 1,000 rows. When the validator was run against the full dataset (545,751 rows), it surfaced values that were not in the schema but were clearly meaningful — they followed the same conventions as documented values, appeared in significant quantities, and represented real loan states or categories that the data dictionary simply omitted.

The corrections were:

- **`sbaguaranteedapproval`**: changed from `integer` to `float`. The full dataset contains 318 rows with fractional dollar amounts. The data dictionary describes the guaranteed amount as a dollar figure but does not specify integer-only. The schema now reflects reality.

- **`SOLD_SEC_MRKT_VALUES`**: added `"n"`. The data dictionary describes this as a Y/N indicator but the actual data uses lowercase. The schema now includes both valid values.

- **`BUSINESS_AGE_VALUES`**: added 6 values. The data dictionary documents four broad categories, but the actual data uses finer-grained age buckets. The schema now reflects all values present in the data.

- **`LOAN_STATUS_VALUES`**: `"purch(not c/o)"` → `"purch(notc/o)"`. The transformer strips internal whitespace from loan status values, so `"PURCH(NOT C/O)"` in the raw data becomes `"purch(notc/o)"` after transformation. The schema value was corrected to match the post-transformation form the validator actually compares against.

These were not data quality issues. The data was valid. The schema was incomplete.

---

## Decision

Schema declares valid post-transformation values. When validator findings show the schema is incomplete or inaccurate — rather than the data being malformed — the schema is corrected. This is not the data taking precedence over the schema. Rather, the schema's job is to honestly describe valid reality, and these corrections bring it into alignment with that job.

This is not the same as relaxing schema constraints to accommodate bad data. These values were legitimate, meaningful, and present in volume. The schema was simply wrong about what exists.

---

## Consequences

The validator can now accurately assess row health. Values that were previously flagged as invalid — despite being meaningful — are now recognized. The schema is a more accurate description of the dataset.

**Cost:** Schema corrections require re-running the validator on the full dataset to confirm no other unknown values exist. This is a one-time cost per correction cycle. Additionally, values like `"purch(notc/o)"` in the schema look different from the raw data's `"PURCH(NOT C/O)"` — the schema reflects post-transformation format after the transformer strips internal whitespace from loan status values. A comment at the `LOAN_STATUS_VALUES` definition in `schema.py` documents this format mismatch for future readers.