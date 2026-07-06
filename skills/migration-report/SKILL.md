---
name: migration-report
description: Render a read-only, self-contained HTML report of the migration mappings for human review. Use "--phase analysis" to visualize source-to-CCM after /analyze-*, or "--phase plan" to visualize CCM-to-commercetools after /plan-migration-to-ct. The report is a view of the JSON artifacts, regenerated on demand.
user-invocable: true
---

# migration-report — render a read-only review report

> **Status: scaffold.** Structure and contract defined; implementation pending.
> See [`docs/architecture.md`](../../docs/architecture.md) (§3 "Review reports").

## Purpose

Give consultants and clients a visual, browsable view of the mappings without
reading raw JSON. Output is a **self-contained static HTML file** (inline CSS + a
little vanilla JS — no framework, no build step, opens offline).

## Argument

- `--phase analysis` → render **source → CCM** from `ccm.json`.
- `--phase plan` → render **CCM → commercetools + Terraform resource** from
  `mappings/ccm-to-ct.json`.

## Outputs

- `reports/mapping-report.html` (analysis) or `reports/plan-report.html` (plan).

## Design rules (do not violate)

1. **The report is a pure view, never a source of truth.** It renders from the JSON
   artifacts; all edits happen to `ccm.json` / `mappings/`, then the report is
   regenerated.
2. **Regenerate on demand — no server, no file-watcher (v1).** Re-running is instant.
   (A future upgrade may make the HTML interactive and export an `overrides.json`
   the user drops back into the workspace; that is additive to this design.)

## Contents

- **analysis:** every source → CCM mapping with confidence bars, provenance
  (`sourceRef`), origin badges (source / domain-pack / manual), and a "Decisions
  needed" panel from `decisionsNeeded[]`.
- **plan:** CCM → commercetools resource + Terraform resource, manual/custom
  additions badged, and a "what `terraform apply` will create" summary (counts).

## Implementation

Implemented in [`reporters/render.py`](../../reporters/render.py), styled by
[`reporters/templates/report.css`](../../reporters/templates/report.css):

```
python3 reporters/render.py <ccm.json> --phase analysis --out reports/mapping-report.html
python3 reporters/render.py <ccm.json> --phase plan     --out reports/plan-report.html
```

Produces a single self-contained HTML file (inline CSS + vanilla JS; opens offline).
Analysis mode renders per-product-type attribute tables with confidence bars, origin
badges, provenance, and a "Decisions needed" panel (+ filter / decisions-only
toggle). Plan mode renders the CCM → commercetools → Terraform mapping and a
"what will be created" summary.

Tests: `python3 -m unittest discover -s reporters/tests`.

## Steps

1. Parse `--phase`.
2. Load the relevant JSON artifact from the workspace.
3. Render via `reporters/render.py`.
4. Write the HTML into `reports/` and point the user to it.
