# Usage Guide

A step-by-step walkthrough of a migration with the Commerce Migration Assistant.
This guide uses the first supported slice — **ATG → commercetools**, **telecom**
domain, **B2B + B2C** — but the flow is the same for any source platform.

> **Prerequisites:** the plugin installed (see the [README](../README.md#install)),
> [Terraform](https://developer.hashicorp.com/terraform), and access to whatever
> the client can give you: source code, a database, documentation, and/or a live
> storefront. Any combination works — more inputs means higher-confidence output.

---

## Mental model

You run a **pipeline** of skills. Each one reads the previous phase's files and
writes its own, inside a **workspace** for the client:

```
inputs/          what the client gave you (code, DB dumps, docs, URLs)
manifest.json    client + domain + source + inputs (from /migrate-init)
ccm.json         the Canonical Commerce Model — the source of truth you review
mappings/        source → CCM and CCM → commercetools mapping tables
reports/         mapping-report.html, plan-report.html  (read-only views)
terraform/       generated HCL — run `terraform apply` here
decisions.md     the log of ambiguities and how they were resolved
```

Two things to remember throughout:

- **`ccm.json` is the source of truth.** Reports are read-only views of it.
- **You edit the model, then re-run.** Downstream phases are pure functions of the
  files, so re-running is safe and deterministic.

---

## Phase 0 — Initialize the workspace

```bash
/migrate-init
```

You'll provide client pre-context: **client name**, **domain** (e.g. `telecom`),
**source platform** (e.g. `atg`), whether the migration is **B2B, B2C, or both**,
and which **inputs** you have. This writes `manifest.json`. Drop the client's
artifacts into `inputs/` (a code checkout, DB schema dump, docs, a storefront URL).

---

## Phase 1 — Analyze the source

```bash
/analyze-atg
```

The root skill fans out to sub-analyzers based on the inputs you have:

| Sub-analyzer | Reads | Contributes |
|---|---|---|
| `atg-codebase-analyzer` | repository-definition XML / item-descriptors | the intended shape |
| `atg-database-analyzer` | GSA schema (tables, FKs, cardinality) | real columns, DB-only custom props |
| `atg-docs-analyzer` | provided documentation | intent, business meaning |
| `atg-website-analyzer` | live storefront | what's actually merchandised |

They **cross-validate** — the analyzers corroborate each other, and conflicts are
resolved by **confidence + provenance**. The result is a single `ccm.json` where
every element carries:

- `origin` — `source` / `domain-pack` / `manual`
- `sourceRef` — where it came from
- `confidence` — 0–1
- `decisionsNeeded[]` — ambiguities flagged for you

---

## Review the mapping (read-only report)

```bash
/migration-report --phase analysis
```

This renders **`reports/mapping-report.html`** — open it in any browser (no server,
works offline). You'll see every **source → CCM** mapping with confidence bars,
provenance links, and a **"Decisions needed"** panel listing everything the
analyzers weren't sure about.

The report is **read-only**. To change anything, edit the model and regenerate:

- **Edit `ccm.json` directly**, or just **ask Claude** — e.g. *"in ccm.json, set the
  `warrantyMonths` attribute to type number and resolve decision D-12 as a variant
  attribute."*
- Re-run `/migration-report --phase analysis` to refresh the HTML. Regeneration is
  instant, so it feels live.

### Adding a custom CT-side attribute

Sometimes commercetools needs an attribute the source never had. Add it to
`ccm.json` with `origin: manual` (by hand or by asking Claude). It emits to
Terraform like any other element, and the report **badges it as manually added** so
the provenance stays honest.

---

## Phase 2 — Plan the commercetools target

```bash
/plan-migration-to-ct
```

Reads `ccm.json` and produces the commercetools target design — product types,
categories, Types (custom fields), customer groups, tax/zones/shipping,
channels/stores, business units, associate roles, product selections — plus mapping
tables and a decision report in `mappings/`.

```bash
/migration-report --phase plan
```

Renders **`reports/plan-report.html`**: **CCM → commercetools + Terraform resource**,
with manual/custom additions badged and a **"what will be created"** summary
(counts of product types, categories, etc.). Review, edit the model if needed, and
regenerate — same loop as Phase 1.

---

## Phase 3 — Emit and apply

```bash
/emit-terraform
```

Renders `terraform/` — HCL modules grouped by resource family (product-types,
taxonomy, custom-types, org/B2B, fulfillment, project-settings). Then, as usual with
Terraform:

```bash
cd terraform
terraform init
terraform plan      # review the diff before anything changes
terraform apply     # stands up the commercetools project schema
```

Provide commercetools credentials the way the [`labd/commercetools` provider
expects](https://registry.terraform.io/providers/labd/commercetools/latest/docs)
(project key, client id/secret, scopes, API/auth URLs) — typically via environment
variables, never committed to the workspace.

---

## Re-running and iterating

- **Change the model, re-emit.** Edit `ccm.json` → `/plan-migration-to-ct` →
  `/emit-terraform`. `terraform plan` shows exactly what changed.
- **Reproducible.** The same `ccm.json` + same pinned provider version yields the
  same commercetools project. See the [CT version strategy](architecture.md#versioning--commercetools-updates).
- **Auditable.** `decisions.md` records every ambiguity and its resolution.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Low-confidence mappings everywhere | Too few inputs — add DB schema or docs and re-run `/analyze-atg`. |
| A custom item-descriptor isn't mapped | It's flagged in `decisionsNeeded[]` — decide product type vs. custom Type vs. custom object, then re-run. |
| `terraform plan` errors on a resource | Provider version mismatch — check the pinned version in `terraform/versions.tf` against the [support matrix](architecture.md#versioning--commercetools-updates). |
| Report looks stale | Reports are regenerated on demand — re-run `/migration-report`. |
