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
- **Parse, don't read.** Structured sources (repository XML, DB schema) are
  extracted *deterministically*; the model reasons about the hard cases, it does
  not read every line. This is what keeps large sources tractable — see §10.

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

         └─ /migration-report --phase analysis
                                Renders mapping-report.html (source → CCM) — a
                                read-only visual of every mapping, confidence,
                                provenance, and open decision.

Phase 2  /plan-migration-to-ct  Reads ccm.json → commercetools target design
                                (product types, categories, types, groups,
                                tax/zones/shipping, channels/stores, business
                                units, associate roles, product selections) +
                                mapping tables + decision report.

         └─ /migration-report --phase plan
                                Renders plan-report.html (CCM → commercetools +
                                Terraform resource), with manual/custom additions
                                badged and a "what will be created" summary.

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

### Review reports (read-only HTML views)

Consultants and clients need to *see* the mappings, not read raw JSON. The
`/migration-report` skill renders a **self-contained static HTML file** (inline
CSS + a little vanilla JS — no framework, no build step) that opens with a
double-click, works offline, and is committable and shareable.

Two rules keep this simple and correct:

- **The report is a pure view, never a source of truth.** It is rendered *from*
  `ccm.json` and the mapping tables. All edits happen to those artifacts (by hand
  or by asking Claude); the report is then regenerated.
- **Regenerate on demand, not live-sync (v1).** Re-running `/migration-report` is
  instant, so it already feels live — no running server or file-watcher. (A future
  upgrade can make the HTML interactive and export an `overrides.json` the user
  drops back into the workspace; that is purely additive to this design.)

`/migration-report --phase analysis` shows **source → CCM** with confidence bars,
provenance links, and a "Decisions needed" panel. `--phase plan` shows
**CCM → commercetools + Terraform resource**, badges manual/custom additions, and
summarizes what `terraform apply` will create.

---

## 4. Canonical Commerce Model (CCM)

The CCM is a JSON document per client workspace (`ccm.json`), validated by a JSON
Schema in `ccm/schema/`. Because v1 is schema-only, the CCM carries *structure*,
not records.

### Design basis — why the model is shaped this way

The CCM is **anchored on the target (commercetools), not on the sources.** Its job
is to be *losslessly emittable* to commercetools, so it is shaped around what CT's
resource model can hold. If the CCM could express something CT cannot represent,
the emitter would silently drop it — the target defines the shape. On top of that
anchor the model adds exactly two things:

- **A thin layer of source-neutral commerce concepts** — every platform has a
  catalog/product structure, a taxonomy, pricing scope, customer segmentation, an
  org structure, and fulfillment geography. That common denominator is what lets
  many sources converge into one model. Source-specific shapes are normalized
  (e.g. ATG's product/SKU split → the CCM's `level: product | variant`).
- **Migration metadata** commercetools itself has no concept of — `sourceRef`,
  `confidence`, `decisionsNeeded[]`.

In one line: *the CCM is the commercetools model, abstracted just enough that any
source maps in, plus migration metadata.*

### Value for a single-platform migration

The hub is not only for multi-platform combinations. The common engagement is a
single source (e.g. ATG only) → commercetools, and the CCM earns its place there
for reasons unrelated to multi-source reuse:

- **Decouples analysis from emission** — uncertain, AI-driven "understand the
  source" work produces a reviewable artifact; deterministic "generate Terraform"
  work consumes it. The CCM is the clean seam.
- **Human-review checkpoint** — a consultant corrects `ccm.json` before any code
  is generated, rather than hand-editing generated HCL.
- **Resumability** — re-emit Terraform without re-running analysis.
- **Reuse across engagements on the same platform** — the ATG analyzer and the
  emitter are shared by every ATG client; the CCM is the contract between them.

Trade-off: for a genuinely one-off, throwaway migration the hub is extra
indirection. The payoff scales with number of platforms, number of clients, and
how much review/auditability matters — all of which apply to a reusable
consultancy framework, so the hub is the right call even for single-source work.

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

Every CCM element carries metadata that makes the framework trustworthy:

- **`origin`** — `source` | `domain-pack` | `manual` (see below).
- **`sourceRef`** — the DB table / doc page / code file it derived from (for
  `source` origin).
- **`confidence`** — a 0–1 score from the analyzer (`1.0` for human-asserted
  elements).
- **`decisionsNeeded[]`** — flagged ambiguities routed to human review rather than
  resolved silently.

### Manual & custom additions (CT-side attributes)

Not everything commercetools needs exists in the source. A consultant must be able
to introduce attributes, product types, or custom-field Types on the CT side that
have no source counterpart — and the model supports this as a first-class case via
the `origin` field:

- **`source`** — derived from the client's platform; has a real `sourceRef`.
- **`domain-pack`** — injected by a vertical pack (e.g. telecom rate-plan
  attributes).
- **`manual`** — hand-added on the CT side; `confidence: 1.0`, emitted to Terraform
  exactly like any other element.

Adding a custom attribute is just adding a CCM element with `origin: manual` (by
editing `ccm.json` or asking Claude). Because origin is tracked, the review report
**badges** what came from the source vs. the domain pack vs. hand-added — honest
provenance a consultant can defend to a client.

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
| *(+ metadata)* | `origin`, `sourceRef`, `confidence`, `decisionsNeeded[]` |

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

### Versioning & commercetools updates

commercetools and the `labd/commercetools` provider each evolve on their own
release cadence. Since migrations must be reproducible, the framework **pins** a
tested version per engagement rather than chasing "latest":

- **Pin, don't chase.** The target commercetools API/provider version is recorded
  in the workspace manifest and in the emitter's `required_providers` block; bumps
  are deliberate and tested, not automatic.
- **Isolate CT churn in the emitter.** This is the hub-and-spoke benefit applied to
  *time*: the CCM stays a slow-moving, source-neutral abstraction, and anything CT
  renames or restructures is absorbed by the one CT-version-specific component.
  (The CCM says `businessUnits[]`; the emitter picks `business_unit_company` vs
  `business_unit_division` per the pinned provider.)
- **Keep the CCM slightly more abstract than raw CT drafts**, so a CT change does
  not ripple back into every source analyzer.
- **Support matrix + conformance check.** Document supported CT/provider versions;
  in CI, run `terraform validate` / `plan` on emitted output and periodically
  re-verify the CT resource list so drift is caught, not discovered mid-project.

Because we chose Terraform, the binding contract is the **provider schema**, which
tracks the CT API on its own cadence — that is the artifact we pin and test
against. (The resource list in this document was verified against the then-current
`labd/commercetools` provider in July 2026.)

---

## 9. Packaging, Distribution & Layout

The framework is distributed as a **single Claude Code plugin** so other developers
install the whole pipeline in one step. The repository *is* the plugin, which fixes
the layout: `skills/` and `agents/` live at the repo root (not under `.claude/`),
and `.claude-plugin/plugin.json` is the manifest.

```
commerce-migration-assistant/          # the plugin repo
├── .claude-plugin/
│   ├── plugin.json                     # manifest: name, version (semver), description
│   └── marketplace.json                # lets devs `/plugin marketplace add <repo>`
├── skills/
│   ├── migrate-init/SKILL.md
│   ├── analyze-atg/SKILL.md
│   ├── plan-migration-to-ct/SKILL.md
│   ├── emit-terraform/SKILL.md
│   └── migration-report/SKILL.md       # read-only HTML views (--phase analysis|plan)
├── agents/
│   └── atg-{codebase,database,docs,website}-analyzer.md
├── ccm/schema/                         # JSON Schema for the Canonical Commerce Model
├── adapters/atg/                       # ATG item-descriptor → CCM knowledge
├── emitters/terraform/                 # CCM → HCL templates + module structure
├── reporters/templates/                # HTML/CSS for the migration-report skill
├── domains/telecom/                    # expected entities, product-type priors
├── docs/                               # architecture, usage, extending
└── README.md
```

Supporting directories (`ccm/`, `adapters/`, `emitters/`, `reporters/`, `domains/`)
ride along as bundled assets that skills read from the plugin root.

### Installing the plugin

```
/plugin marketplace add JefinFrancis/commerce-migration-assistant
/plugin install commerce-migration-assistant@<marketplace-name>
```

### Versioning

The plugin version (semver in `plugin.json`) is the release unit and ties directly
to the **commercetools support matrix** (§8): a plugin release pins a tested
commercetools API / `labd/commercetools` provider version. Bumping the supported CT
version is a plugin release, not a silent change.

### Per-client workspace

A **client migration is a workspace** — a separate directory or repo, not part of
the plugin — holding that client's `inputs/ · ccm.json · mappings/ · reports/ ·
terraform/ · decisions.md`. The plugin is the reusable tool; the workspace is the
per-engagement data.

### Growth path

v1 is one plugin. As source platforms are added, per-platform adapters can split
into their own plugins in the same marketplace (`cma-atg`, `cma-occ`, …) depending
on a core — without changing how the pipeline works.

---

## 10. Scaling & Large Sources

Large ATG installs (hundreds of item-descriptors, sprawling schemas) are handled by
**width and rules**, not by a bigger context window. Two properties make the problem
much smaller than it first appears, and five techniques handle the rest.

### Schema-only bounds the mapping count

v1 migrates *structure, not records*. The number of mappings is bounded by the count
of **distinct** product types, attributes, categories, and custom types — **not** by
how many products/orders/customers exist. A telco with 10M SKUs but 25 product types
is 25 product-type mappings, not 10 million. The remaining concern is **schema
sprawl** (a heavily-customized install), which is bounded and much smaller. (Bulk
*data* migration is a separate future phase — batched/streamed, never through the
model.)

### Deterministic extraction first, model reasoning selectively

The single biggest lever: **never feed the whole codebase to the model.** Repository
XML and DB schemas are structured, so:

1. **Extract deterministically (no model).** A real XML parser reads every
   `item-descriptor`/`property`; DB introspection reads `information_schema`. This
   produces a complete **raw inventory** of the source cheaply and reliably at any
   size — it scales with a parser, not with tokens.
2. **Rule-based mapping for the easy majority.** `adapters/<platform>/` rules map
   `property type → attribute type` mechanically.
3. **Model reasoning only for the hard cases** — custom item-descriptors with no CT
   equivalent, ambiguities, conflicts, labels, and resolving `decisionsNeeded`.

Context per reasoning step stays small regardless of repository size.

### Horizontal fan-out (map-reduce)

For the judgment work, the root analyzer enumerates the work-list from the raw
inventory, shards it by natural boundary (per item-descriptor / module / catalog)
across parallel worker sub-analyzers with bounded context, and merges their CCM
fragments. Merging is mostly mechanical (by `key`); the model is invoked only on
conflicts and decisions.

### Pattern deduplication

Schema sprawl is repetitive — many descriptors reuse the same shapes. Cluster
structurally-identical descriptors, reason about the **pattern once**, apply to all,
and escalate only the outliers. "500 mappings" becomes "12 patterns + a few
exceptions."

### Resumable & incremental

The raw inventory is a durable work-list; the analyzer checkpoints completed items
and writes CCM fragments as it goes. A large migration can run in passes and re-run
only what changed — nothing must fit in one context or one session.

### Compact emission & review at scale

- **Emission:** the Terraform emitter uses `for_each` over data maps, so 400 product
  types is one templated block iterating a map — not 400 hand-written resources — and
  `terraform plan` stays fast.
- **Review:** the report surfaces the risky minority — sorts by confidence, lists
  `decisionsNeeded` first, groups by pattern, and supports bulk approval of repeated
  patterns. Humans review exceptions, not thousands of identical rows.
- **Coverage, never silent truncation:** the report states what was and wasn't mapped
  (e.g. "312 of 340 item-descriptors mapped; 28 deferred as unused/low-priority"),
  prioritizing customer-facing entities (signalled by the website analyzer).
- **Model tiering:** cheap parser + a fast model for routine classification; escalate
  to the strong model only for genuinely hard cases.

---

## 11. Roadmap

1. Scaffold the plugin — `.claude-plugin/plugin.json` + `marketplace.json`, CCM JSON
   Schema, and stub `SKILL.md` / agent files.
2. Build the `analyze-atg` root skill + its four sub-analyzers.
3. Build `plan-migration-to-ct` + the Terraform emitter.
4. Build the `migration-report` skill + shared HTML template.
5. Wire in the telecom domain pack.
6. Add a second source platform (OCC or Shopify) to validate hub-and-spoke reuse.

> **Beyond V1:** a separate **V2 direction** ([`docs/v2/approach.md`](v2/approach.md))
> expands the framework from this schema-only pipeline into a full demo-ready
> storefront accelerator (storefront, backend, demo seeding, CMS). It is planned, not
> yet implemented — this document describes the built V1 system.

---

## Appendix: verified `labd/commercetools` resources

Resource names confirmed against the provider docs:
`product_type`, `type`, `category`, `customer_group`, `tax_category` (+ `_rate`),
`shipping_zone` (+ `_rate`), `shipping_method`, `channel`, `store`,
`product_selection`, `business_unit_company`, `business_unit_division`,
`associate_role`, `attribute_group`, `state` (+ `_transitions`), `custom_object`,
`project_settings`, `api_client`, `api_extension`, `subscription`,
`cart_discount`, `product_discount`, `discount_code`.
