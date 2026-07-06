# reporters/templates

The shared HTML/CSS template used by the `migration-report` skill to render
read-only review reports.

> **Status: scaffold.** This directory will hold the report template(s).

## What lives here (planned)

- A **single self-contained HTML template** (inline CSS + minimal vanilla JS — no
  framework, no build step, opens offline) with two modes:
  - **analysis** — source → CCM: confidence bars, provenance (`sourceRef`), origin
    badges (source / domain-pack / manual), and a "Decisions needed" panel.
  - **plan** — CCM → commercetools + Terraform resource: manual/custom additions
    badged, plus a "what `terraform apply` will create" summary.

## Design rules

1. The report is a **pure view** of the workspace JSON artifacts — never a source of
   truth.
2. **Regenerate on demand** (no server, no file-watcher in v1).

See [`docs/architecture.md`](../../docs/architecture.md) (§3 "Review reports").
