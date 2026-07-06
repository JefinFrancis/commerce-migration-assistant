# reporters/templates

The shared HTML/CSS template used by the `migration-report` skill to render
read-only review reports.

> **Status: implemented.** `report.css` is the stylesheet inlined by the renderer at
> [`reporters/render.py`](../render.py).

## Implemented

- `report.css` — the stylesheet (light + dark aware) inlined into every generated
  report. Editing it changes the look of all future reports.
- The renderer lives at [`reporters/render.py`](../render.py):

```
python3 reporters/render.py <ccm.json> --phase analysis --out mapping-report.html
python3 reporters/render.py <ccm.json> --phase plan     --out plan-report.html
```

Both modes emit a **single self-contained HTML file** (inline CSS + a little vanilla
JS — no framework, no build step, opens offline):

- **analysis** — source → CCM per product type: confidence bars, provenance
  (`sourceRef`), origin badges (source / domain-pack / manual), a "Decisions needed"
  panel surfaced first, and a filter box + "Decisions only" toggle.
- **plan** — CCM → commercetools + Terraform resource, manual/custom additions
  badged, plus a "what `terraform apply` will create" summary.

Tests: `python3 -m unittest discover -s reporters/tests` (content, self-containment,
and well-formedness).

## Design rules

1. The report is a **pure view** of the workspace JSON artifacts — never a source of
   truth.
2. **Regenerate on demand** (no server, no file-watcher in v1).

See [`docs/architecture.md`](../../docs/architecture.md) (§3 "Review reports").
