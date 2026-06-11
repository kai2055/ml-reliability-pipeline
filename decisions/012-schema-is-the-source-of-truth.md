
# 012 — Schema is the Source of Truth

**Date:** 2026-05-07
**Component:** Project-wide
**Status:** Decided

---

## Context

Three times during the project, something pushed against the schema and I had to decide which way to go.

First, pandas inference. Load the CSV, pandas guesses types. Sometimes it's wrong — `revolverstatus` comes out as bool, `naicscode` as int64. If there's no schema saying what the type actually is, those bad guesses just float downstream and no one notices.

Second, implementation convenience. Some type coercions are annoying to write. The easy move is to look at what pandas produced and change the schema to match. If I do that, the schema stops being a rulebook and becomes a description of whatever pandas happened to infer.

Third, the data dictionary gaps. The SBA data dictionary documents certain values for columns like `loanstatus` and `businessage`. Reality has more. Those extra values aren't bad data — they're the data dictionary being incomplete. If I treat them as invalid, the validator cries wolf. If I relax the schema without thinking, I lose the distinction between "data is wrong" and "schema is wrong."

Without a stated rule, each of these gets resolved differently depending on the day. The schema drifts.

---

## Decision

When the schema and something else disagree — data, pandas, implementation — the schema wins by default. Coerce the data. Override the inference. Fix the implementation. The schema does not bend.

The one exception: when the schema itself is wrong. If it was built from incomplete info and is flagging valid data, the schema gets corrected. That's not the data winning. That's the schema being fixed so it does its job properly.

---

## Consequences

Every component gets the same answer when conflicts come up. Not "whatever is easier." Schema wins. Unless the schema is wrong, and here's how to tell the difference.

This becomes the reference rule for any future component touching the schema — drift detection, serving layer, CI checks. The answer is already here.

**Cost:** Sometimes it's more work. Transformer has to coerce bool back to int64. Type corrections need an ADR instead of a silent edit. Schema changes require looking at the data first, not just editing a line. That friction is there on purpose. It means changes are intentional and recorded, not accidental.
