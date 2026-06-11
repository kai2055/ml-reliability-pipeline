# 003 — Validation Layer Architecture Decisions

**Date:** 2026-05-01  
**Component:** Data validation layer (`src/data/`)  
**Status:** Decided

---

## Decision 1: loader.py does input validation before pandas ever touches the file

**What I decided:** Before calling `pd.read_csv()`, the loader checks three things explicitly: does the path exist, is it a file and not a directory, and does it have a `.csv` suffix. Each check raises a specific built-in Python exception with a clear message.

**Why I did this:** If the wrong file type or a broken path gets passed in, pandas raises a confusing internal error deep in its own code. I want the error to be caught at the boundary — before it goes anywhere near the data pipeline — with a message that tells you exactly what went wrong.

**Exceptions used:**
- `FileNotFoundError` — path does not exist
- `IsADirectoryError` — path points to a folder
- `ValueError` — file is not a CSV

---

## Decision 2: Structural validation failures are fatal; content issues are flagged and reported

**What I decided:** Some validation failures reject the dataset entirely. Others get logged in a report and passed downstream.

**Fatal checks — dataset is rejected:**
- Column names do not match the expected schema
- No column headings at all
- EXEMPT rows exceed a defined threshold (threshold TBD during implementation)
- Non-7(a) program rows exceed a defined threshold

**Non-fatal checks — flagged and reported:**
- Missing values
- Whitespace pollution in coded fields
- Type mismatches
- Cross-column consistency violations (e.g. `loanstatus = CHGOFF` but `grosschargeoffamount = 0`)
- Invalid coded values

**Why this split:** If the structure is wrong, every downstream check that references a column by name will break. There is no point running content checks on a dataset with the wrong shape. For content issues, I want to collect everything that is wrong before stopping — not abort on the first issue found.

---

## Decision 3: Validator runs in two phases, not one

**What I decided:** The validator does not run all checks in one pass. The order is:

1. Structural validation — column names, column count, fatal threshold checks
2. Transformation — whitespace stripping, type normalisation, EXEMPT row removal
3. Content validation — coded value checks, cross-column consistency, missing value checks

**Why this matters:** Content checks depend on clean data. If I check `loanstatus` values before stripping whitespace, `"P I F"` will fail the check even though it is a valid value. The transformer has to run first so the validator is comparing clean data against clean schema values.

---

## Decision 4: schema.py holds canonical values in lowercase, not the raw data values

**What I decided:** All coded value tuples in `schema.py` use lowercase. The transformer normalises incoming data to lowercase before the validator compares against the schema.

**What I considered:**
- Using raw data values directly — rejected because the data has too much variation, especially in columns with long string values. Trying to capture every variation in the schema would add complexity and defeat the purpose.
- Using data dictionary values as-is — possible, but the data dictionary uses mixed case and the raw data doesn't follow it consistently anyway.

**Why I went with lowercase:** The schema's job is to define what correct looks like after cleaning — not to mirror the mess in the raw data. Converting everything to lowercase makes both diagnosis and transformation simpler and consistent.

**An important distinction I want to record:** The validator's diagnosis shows messiness — it reports what is wrong. The transformation is about the pipeline's ability to function at all — if certain columns can't be parsed or compared, the whole pipeline breaks. These are two different concerns even though they work on the same data.

---

## Decision 5: Empty strings are not valid coded values — they are missing values

**What I decided:** For columns like `soldsecmrktind`, an empty value is treated as a missing value, not a valid coded value. The coded value check only validates against `("y",)`. Missing values are handled by a separate missing value check.

**Why this matters:** Treating an empty string as a valid value would mean the validator passes rows where the field was never filled in. That is a data quality issue, not a valid entry. Missing values and invalid values are different problems and need to be tracked separately in the validation report.
