# Commerce Migration Assistant

A reusable, AI-agent-driven framework for migrating **any** commerce platform
(ATG, Oracle Commerce Cloud, Shopify, SAP Hybris, …) to **[commercetools](https://commercetools.com/)**.

It ships as a **Claude Code plugin**: a set of skills that analyze a source
platform, normalize it into a platform-neutral model, and emit a reproducible
commercetools project schema as **Terraform**.

> **Release 1 scope:** schema/structure only — product types, taxonomy, custom
> fields, customer groups, tax/shipping, channels/stores, and B2B org structure.
> No records or data are migrated.

---

## How it works — hub-and-spoke

Instead of writing a direct mapper for every source→commercetools pair, every
source maps into one **Canonical Commerce Model (CCM)**, and a single emitter maps
the CCM to commercetools. Adding a platform means writing *one* analyzer; the whole
commercetools side is reused.

```
   ATG  ─┐
   OCC  ─┤                                      ┌─ commercetools (Terraform)
Shopify ─┼──▶  analyzers  ──▶  CCM  ──▶  planner + emitter  ──▶
 Hybris ─┘        (spokes in)   (hub)      (hub → target)
```

## The pipeline

| Phase | Skill | Produces |
|---|---|---|
| 0 · Init | `/migrate-init` | Workspace manifest (client, domain, source, inputs) |
| 1 · Analyze | `/analyze-atg` | `ccm.json` (source → CCM), reconciled from sub-analyzers |
| — · Review | `/migration-report --phase analysis` | `mapping-report.html` (read-only) |
| 2 · Plan | `/plan-migration-to-ct` | commercetools target design + mapping tables |
| — · Review | `/migration-report --phase plan` | `plan-report.html` (read-only) |
| 3 · Emit | `/emit-terraform` | `terraform/` HCL modules — run `terraform apply` |

Each phase reads the previous phase's file artifacts and writes its own, so the
pipeline is **resumable, diff-able, and reviewable**. `ccm.json` and the mapping
tables are the source of truth; the HTML reports are read-only views regenerated on
demand.

## Install

```bash
/plugin marketplace add JefinFrancis/commerce-migration-assistant
/plugin install commerce-migration-assistant@<marketplace-name>
```

## Quick start

```bash
# 1. Start a client migration in a fresh workspace directory
/migrate-init            # answer prompts: client, domain (e.g. telecom), source (ATG), inputs

# 2. Analyze the source into the canonical model
/analyze-atg             # fans out to sub-analyzers, writes ccm.json

# 3. See what got mapped
/migration-report --phase analysis    # open mapping-report.html

# 4. Plan the commercetools target
/plan-migration-to-ct
/migration-report --phase plan        # open plan-report.html

# 5. Emit and apply
/emit-terraform
cd terraform && terraform init && terraform plan
```

See the **[usage guide](docs/usage.md)** for the full walkthrough, including how to
review mappings, edit the model, and add custom CT-side attributes.

## Documentation

- **[Architecture](docs/architecture.md)** — the design reference (CCM, pipeline,
  ATG strategy, telecom pack, Terraform emission, packaging, CT version strategy).
- **[Usage guide](docs/usage.md)** — step-by-step walkthrough of a migration.
- **[Extending](docs/extending.md)** — adding a new source platform or domain pack.
- **[V2 direction](docs/v2/approach.md)** — *planned, not yet implemented.* Expands
  the scope to a full demo-ready storefront accelerator (storefront, backend, demo
  seeding, CMS). Includes a [stakeholder deck](docs/v2/stakeholder-deck.html).

## Status

The architecture is defined; implementation follows the [roadmap](docs/architecture.md#11-roadmap).
Current first slice: **ATG → commercetools**, **telecom** domain, **B2B + B2C**.

Everything shipped today is **schema-only** (this README's scope). A future **V2**
extends the framework to storefront/backend/CMS generation and demo seeding — see
the [V2 direction](docs/v2/approach.md); none of it is built yet.

## License

TBD.
