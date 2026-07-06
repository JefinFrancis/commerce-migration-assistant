# Commerce Migration Assistant — Architecture

> A reusable, AI-agent-driven framework for migrating **any** commerce platform
> (ATG, Oracle Commerce Cloud, Shopify, SAP Hybris, …) to **commercetools**.

---

## 1. Vision & Goals

One framework, many source platforms, a single target: **commercetools**.

The framework operates in two conceptual passes:

1. **Analyze** — understand the source platform and normalize it into a
   platform-neutral model.
2. **Plan / Emit** — map that model to commercetools and generate a reproducible
   project setup.

**Release 1 scope is schema/structure only** — product types, taxonomy, custom
fields, customer groups, tax/shipping, channels/stores, and B2B org structure.
No records or data are migrated. The output is a reproducible commercetools
project *schema*, not populated content.

### Design principles

- **Hub-and-spoke.** Sources map into a shared canonical model; a single emitter
  maps that model to commercetools. commercetools knowledge lives in exactly one
  place.
- **Everything is a reviewable file artifact.** The canonical model, mapping
  tables, and decision logs are files in a per-client workspace — diff-able,
  hand-editable, resumable.
- **Provenance + confidence + explicit decisions.** Every element records where
  it came from, how confident the analyzer is, and any ambiguity that needs a
  human call. The framework never guesses silently.
- **Generic core + thin platform adapters.** The pipeline engine is shared;
  platforms differ only in adapter knowledge.
- **Domain packs are data/priors, not forked code.** Verticals (telecom,
  manufacturing, …) prime the analyzers and planner rather than branching the
  pipeline.

### Locked decisions (v1)

| Decision | Choice |
|---|---|
| Architecture | Hub-and-spoke via a **Canonical Commerce Model (CCM)** |
| Output format | **Terraform** using the `labd/commercetools` provider |
| First source platform | **ATG** (Oracle ATG / Oracle Commerce) |
| First domain pack | **Telecom** |
| Scope | **B2B + B2C together** |

---

## 2. Hub-and-Spoke Architecture

The trap in "migrate *any* platform to commercetools" is building a direct mapper
per source (ATG→CT, OCC→CT, Shopify→CT). That is N mappers, each re-solving "how
do I model a product type in commercetools," and the CT knowledge duplicates and
drifts.

Instead, a **Canonical Commerce Model (CCM)** sits in the middle:

```
   ATG  ─┐
   OCC  ─┤                                     ┌─ commercetools (Terraform)
Shopify ─┼──▶  analyzers  ──▶  CCM  ──▶  planner + emitter  ──▶
 Hybris ─┘        (spokes in)   (hub)      (hub → target)
```

- **Spokes in:** one analyzer per source platform maps it → CCM.
- **Hub → target:** one planner and one Terraform emitter, reused by every source.
- **Adding a platform = writing one new analyzer.** The entire commercetools side
  is reused unchanged.

---

## 3. Pipeline & Skills

The framework is a set of Claude Code skills that run as an ordered pipeline. Each
phase reads the previous phase's file artifacts and writes its own.

```
Phase 0  /migrate-init          Capture client pre-context (domain, B2B/B2C,
                                source platform, available inputs) → workspace
                                manifest.

Phase 1  /analyze-atg           Root skill; fans out to sub-analyzers by input:
         ├─ atg-codebase-analyzer   repository-definition XML / item-descriptors
         ├─ atg-database-analyzer   GSA schema introspection (tables, FKs, cardinality)
         ├─ atg-docs-analyzer       RAG over provided documentation
         └─ atg-website-analyzer    crawl/inspect live storefront
                                Each emits partial CCM fragments + provenance +
                                confidence + decisionsNeeded. Root reconciles →
                                one merged ccm.json.

Phase 2  /plan-migration-to-ct  Reads ccm.json → commercetools target design
                                (product types, categories, types, groups,
                                tax/zones/shipping, channels/stores, business
                                units, associate roles, product selections) +
                                mapping tables + decision report.

Phase 3  /emit-terraform        Renders the plan into .tf (HCL) modules — the
                                "directly importable" artifact (`terraform apply`).
```

### Cross-validation

The four sub-analyzers corroborate one another rather than trusting a single
source:

- **Codebase** — the repository-definition XML defines the intended *shape*.
- **Database** — confirms the real columns and cardinality, and catches custom
  properties added directly in the DB that never appear in XML.
- **Docs** — explain intent and business meaning.
- **Website** — sanity-checks what is actually merchandised.

The root `/analyze-atg` reconciles conflicts by **confidence + provenance**.

### Human-in-the-loop

Between every phase, `ccm.json` and the mapping tables are hand-editable. Because
later phases are pure functions of these files, a human can correct the model and
re-run downstream phases deterministically — the pipeline is resumable and
diff-able.

---

## 4. Canonical Commerce Model (CCM)

The CCM is a JSON document per client workspace (`ccm.json`), validated by a JSON
Schema in `ccm/schema/`. Because v1 is schema-only, the CCM carries *structure*,
not records.

### Entities and their commercetools targets

| CCM entity | commercetools target | Terraform resource (`labd/commercetools`) |
|---|---|---|
| `productTypes[]` (+ attribute defs) | Product Type | `commercetools_product_type` |
| `categories[]` (tree) | Category | `commercetools_category` |
| `customFieldTypes[]` | Type (custom fields) | `commercetools_type` |
| `customerGroups[]` | Customer Group | `commercetools_customer_group` |
| `taxCategories[]` (+ rates) | Tax Category | `commercetools_tax_category`, `commercetools_tax_category_rate` |
| `zones[]`, `shippingMethods[]` | Zone / Shipping Method | `commercetools_shipping_zone`, `commercetools_shipping_zone_rate`, `commercetools_shipping_method` |
| `channels[]` | Channel | `commercetools_channel` |
| `stores[]` | Store | `commercetools_store` |
| `productSelections[]` | Product Selection | `commercetools_product_selection` |
| `businessUnits[]` (B2B) | Business Unit | `commercetools_business_unit_company`, `commercetools_business_unit_division` |
| `associateRoles[]` (B2B) | Associate Role | `commercetools_associate_role` |
| `attributeGroups[]` | Attribute Group | `commercetools_attribute_group` |
| `states[]` | State | `commercetools_state`, `commercetools_state_transitions` |
| `customObjects[]` (fallback) | Custom Object | `commercetools_custom_object` |
| project-level settings | Project Settings | `commercetools_project_settings` |

### Metadata on every element

Every CCM element carries a metadata triplet that makes the framework trustworthy:

- **`sourceRef`** — the DB table / doc page / code file it derived from.
- **`confidence`** — a 0–1 score from the analyzer.
- **`decisionsNeeded[]`** — flagged ambiguities routed to human review rather than
  resolved silently.

### Product-type attribute definitions

`productTypes[].attributes[]` fields:

| Field | Meaning |
|---|---|
| `name`, `label` | identifier and display label |
| `type` | `text` / `ltext` / `enum` / `lenum` / `number` / `boolean` / `money` / `date` / `reference` / `set` / `nested` |
| `required` | whether the attribute is mandatory |
| `constraint` | `none` / `unique` / `combinationUnique` |
| `level` | `product` or `variant` |
| `values` | enum value set (for `enum`/`lenum`) |
| *(+ metadata triplet)* | `sourceRef`, `confidence`, `decisionsNeeded[]` |

---

## 5. ATG → CCM Adapter Strategy

ATG's data model is defined by **repository-definition XML** (e.g.
`productCatalog.xml`) layered over the **GSA (Generic SQL Adapter)**. In that
model, `<item-descriptor>` = a type and `<property>` = a field/column.

### Mapping rules

- **`item-descriptor` "product"** → the shape of a commercetools **Product Type**.
  Its properties split by level: **SKU-level → variant attributes**,
  **product-level → product-level attributes**.
- **`<property>` types** → commercetools attribute types: `enumerated` →
  `enum`/`lenum`, multi-valued → `set`, item reference → `reference`/`nested`,
  `date`/`double`/`boolean` → their equivalents.
- **`category` tree** → commercetools **Categories**; ATG **catalogs** / multisite
  → commercetools **Stores** + **Product Selections**.
- **Price lists** → the CCM `pricingModel` (customer-group / channel / store
  scoped) + tax categories — structure only, no price values.
- **Custom item-descriptors** with no direct CT equivalent become an explicit
  **decision**: promote to a Product Type, fold into a Type (custom fields), or
  store as a Custom Object. The analyzer proposes; the human confirms.

Adapter knowledge — item-descriptor → CCM maps and heuristics — lives in
`adapters/atg/`.

---

## 6. Telecom Domain Pack

The telecom pack (`domains/telecom/`) primes the analyzers and planner with the
entities a telecom catalog is expected to contain:

- **Rate plans** and subscription/recurring products
- **Device + plan bundles**
- **SIM / provisioning attributes** — contract term, billing cycle, data allowance
- **Device attributes** — IMEI, color, storage

commercetools has no native subscription concept, so the pack encodes the modeling
convention (e.g. product types `device` / `plan` / `accessory` / `bundle` plus
recurring-term attributes) so that *every* telecom migration comes out consistent.

Domain packs are data and priors, never forked pipeline code.

---

## 7. B2B + B2C Mapping

The framework models both customer models together:

- **B2B** — ATG organizations / roles / contracts / cost centers →
  commercetools **Business Units** (`business_unit_company` /
  `business_unit_division`) + **Associate Roles**. Contracts hint at per-BU
  **Product Selections** and scoped pricing.
- **B2C** — Customer Groups + Stores + the standard catalog.

All of these are supported by the `labd/commercetools` Terraform provider, so the
full B2B+B2C structure can be emitted as code.

---

## 8. Terraform Emission

The emitter (`emitters/terraform/`) renders the CCM into HCL modules grouped by
resource family:

- `product-types` — product types + attribute groups
- `taxonomy` — categories
- `custom-types` — Types (custom fields) and custom objects
- `org` / B2B — business units, associate roles, product selections
- `fulfillment` — tax categories, zones, shipping methods
- `project-settings` — project-level configuration

The output is a `terraform/` module in the client workspace. `terraform plan` /
`terraform apply` stands up the commercetools project schema, and re-runs are
reproducible and diff-able.

---

## 9. Repository Layout & Per-Client Workspace

```
.claude/skills/       migrate-init, analyze-atg, plan-migration-to-ct, emit-terraform
.claude/agents/       atg-{codebase,database,docs,website}-analyzer
ccm/schema/           JSON Schema for the Canonical Commerce Model
adapters/atg/         ATG item-descriptor → CCM knowledge
emitters/terraform/   CCM → HCL templates + module structure
domains/telecom/      expected entities, product-type priors, decision heuristics
docs/architecture.md  the design record (this document)
workspaces/<client>/  inputs/ · ccm.json · mappings/ · terraform/ · decisions.md
```

- The **framework** is a Claude Code skills/plugin repo the team installs.
- Each **client migration** is a workspace (a subdirectory or a separate repo)
  holding that client's inputs and generated artifacts.

---

## 10. Roadmap

1. Scaffold the repo structure + CCM JSON Schema + stub `SKILL.md` files.
2. Build the `analyze-atg` root skill + its four sub-analyzers.
3. Build `plan-migration-to-ct` + the Terraform emitter.
4. Wire in the telecom domain pack.
5. Add a second source platform (OCC or Shopify) to validate hub-and-spoke reuse.

---

## Appendix: verified `labd/commercetools` resources

Resource names confirmed against the provider docs:
`product_type`, `type`, `category`, `customer_group`, `tax_category` (+ `_rate`),
`shipping_zone` (+ `_rate`), `shipping_method`, `channel`, `store`,
`product_selection`, `business_unit_company`, `business_unit_division`,
`associate_role`, `attribute_group`, `state` (+ `_transitions`), `custom_object`,
`project_settings`, `api_client`, `api_extension`, `subscription`,
`cart_discount`, `product_discount`, `discount_code`.
