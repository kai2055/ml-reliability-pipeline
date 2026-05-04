
# 007 — Transformer is Dataset-Specific, Not Generic

**Date:** 2026-05-04  
**Component:** Data validation layer (`src/data/`)  
**Status:** Decided

---

## Context

Before working through this dataset, my assumption was that a transformer is a reusable component — write it once, use it across any dataset. The operations themselves looked generic enough: strip whitespace, lowercase strings, coerce booleans to integers. Nothing about those operations seemed tied to SBA data specifically.

Inspecting the data changed that. The transformations the SBA file needs are not "clean string columns in general." They are: lowercase because the schema declares lowercase as the canonical form, strip whitespace because raw values arrive padded, replace internal whitespace because `loanstatus` is polluted with values like `"P I F"`, coerce `revolverstatus` strings to integers because the schema declares them as `0` and `1`.

Each of those transformations exists because the schema declared a specific form and the raw data deviates from it in a specific way. A different dataset with a different schema would need different transformations. A schema that declared uppercase as canonical would need uppercase normalisation, not lowercase. A schema with case-sensitive identifiers would need casing left alone entirely.

The transformer is not a generic utility. It is the bridge between *this* raw dataset and *this* schema. Treating it as generic would mean either making invisible assumptions about what "clean" means, or overgeneralising to the point where the transformer corrupts data on inputs it wasn't designed for.

---

## Decision

The transformer is dataset-specific by design. It is written against a specific schema and the conventions of a specific dataset. If Datatroniq ingested a different dataset tomorrow, a new transformer would be written for it, and that is correct, not duplication to be refactored away.

What is generic is the **infrastructure around the transformer** — the validation framework, drift detection logic, MLflow tracking, FastAPI serving layer, deployment pipeline. These components do not care what the data looks like. They operate on whatever the schema and transformer produce.

The seam is clear:

- **Dataset-specific:** schema, transformer
- **Generic:** validator framework, drift detection, MLflow, FastAPI, Docker, CI/CD

---

## Consequences

Future-me will be tempted to "DRY up" the transformer once a second dataset enters the project. This decision exists to push back against that. Shared transformation logic across datasets is almost always an illusion — the moment one dataset's convention diverges, the shared code either breaks silently or grows conditional branches that obscure what each dataset actually needs.

A generic transformer is the failure mode this entire project is built to detect. It silently corrupts data on inputs it wasn't designed for, the model keeps returning predictions, and degradation only surfaces downstream when business outcomes have already been affected. Building that pattern into the data layer would mean the pipeline causes the exact failure its monitoring layer is meant to catch.

The kitchen analogy is the way I want to remember this. A commercial kitchen's stoves, knives, dishwasher, and ticket system are generic — they work for sushi, tacos, or French bistro food. But the prep is dish-specific. You cannot write one universal "prep function" that dices everything to 5mm cubes. It would ruin the sushi (the fish needs slicing) and ruin the bistro sauce (shallots need to be finer). The prep being specific to the ingredient is not a flaw — it is what makes the food correct. The transformer is the prep station. It is supposed to be specific.

---

## Revisiting

This decision should be revisited only if the project's scope changes such that multiple datasets with genuinely identical conventions need to be ingested through the same transformer. In that case, the right move is not a generic transformer — it is a shared schema, with the transformer pointed at it. The principle stays: transformer follows schema, schema follows dataset.