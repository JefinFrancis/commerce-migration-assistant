# Implementation Plan — V1 completion + V2

> Turns the agreed designs into an ordered build plan. Covers **finishing V1** (the
> schema pipeline has working cores but several stub pieces) and then **building V2**
> (the storefront/demo/CMS accelerator, `docs/v2/approach.md`). V2 stacks on a
> complete V1, so V1 gaps come first.

**Legend:** 🟢 built · 🟡 partial · ⬜️ not started · 🧪 testable in this sandbox ·
🌐 needs live services / a model at runtime (not fully testable here).

---

## 1. Current state (honest snapshot)

**Built (deterministic Python cores + tests, 🟢):**

- `adapters/atg/` — `extract.py` (repository XML → inventory), `db_extract.py`
  (GSA DDL → inventory), `mappings.py`, `to_ccm.py` (build + DB reconciliation),
  `analyze.py` (CLI wiring **codebase + DB only**).
- `emitters/terraform/emit.py` — emits **versions, product-types, categories,
  customer-groups** only.
- `reporters/render.py` — analysis + plan HTML reports.
- CCM JSON Schema + example; 37 passing tests.

**Stub / missing (⬜️):**

- **All 5 skills are stub `SKILL.md`** — they document behavior but do not actually
  orchestrate the Python tools or a workspace. There is no working `migrate-init`,
  and skills don't yet invoke the cores.
- **`analyze-atg` orchestration** — no reconciliation across all analyzers, no
  model-reasoning for hard cases, no domain-pack merge.
- **docs analyzer + website analyzer** — not implemented.
- **`plan-migration-to-ct`** — no code (the emitter currently maps CCM→CT internally).
- **Emitter families** — no custom types, attribute groups, B2B/org, fulfillment,
  states, project settings, custom objects.
- **Telecom domain pack** — `domains/telecom/` is a README only.
- **Second source platform** (OCC/Shopify) — not started.
- **All of V2** — nothing built.

---

## 2. Foundations (shared by V1 completion and V2)

These unblock everything else; do them first.

| ID | Task | Notes | Test |
|---|---|---|---|
| **F1** | **Workspace convention + `migrate-init`** | Define + implement the per-client workspace: `manifest.json`, `inputs/`, `ccm.json`, `mappings/`, `reports/`, `terraform/`, `decisions.md`. Every skill reads/writes it. | 🧪 |
| **F2** | **Skill-wiring pattern** | Make a skill actually orchestrate: invoke the Python cores (Bash), read/write the workspace, fan out to agents. Establish once, reuse for all V1 + V2 skills. | 🧪 |
| **F3** | **Dual-target packaging skeleton** | Add `HARNESS.md` + `.leaf-detectors` + routing files over the existing tree (per `docs/v2/approach.md` §11); wire `ahar validate` in CI. Prepares the `cma-*` split. | 🧪 |

---

## 3. Part A — Complete V1 (to a coherent, demoable schema pipeline)

| ID | Task | Depends on | Test |
|---|---|---|---|
| **A1** | **`analyze-atg` root orchestration** — run codebase + DB cores, reconcile fragments, surface `decisionsNeeded`, write `ccm.json`. Add the **model-reasoning hook** for the hard 20% (custom descriptors, conflicts, labels). | F1, F2 | 🧪 core / 🌐 reasoning |
| **A2** | **`plan-migration-to-ct`** — Phase 2: CCM → CT target design + `mappings/ccm-to-ct.json` + decision report. Refactor the emitter to consume the plan (single source for the mapping the report already renders). | A1 | 🧪 |
| **A3** | **Emit remaining resource families** — `commercetools_type` + attribute groups; B2B/org (`business_unit_company`/`_division`, `associate_role`, `product_selection`); fulfillment (`tax_category`+rate, `shipping_zone`+rate, `shipping_method`); `state`; `project_settings`; `custom_object`. Extend for_each where homogeneous. | A2 | 🧪 syntax / 🌐 provider validate |
| **A4** | **Telecom domain pack** — implement `domains/telecom/` priors (expected entities, product-type priors tagged `origin: domain-pack`, decision heuristics); merge in A1. | A1 | 🧪 |
| **A5** | **docs analyzer + website analyzer** — RAG over docs; Playwright storefront crawl; both emit CCM fragments the root reconciles. | A1 | 🌐 |
| **A6** | **Live Terraform validation** — `terraform init/validate/plan` against a real CT project + provider (the check we can't run in-sandbox). | A3 | 🌐 |
| **A7** | **Second source platform (OCC or Shopify)** — new `analyze-<platform>` + adapter → same CCM; proves hub-and-spoke reuse. | A1–A3 | 🧪/🌐 |

**Order within A:** F1–F3 → A1 → A2 → A3 → A4 → A5 → A6 → A7. After **A3** the
framework can stand up a storefront-usable CT project — the entry point for V2.0.

---

## 4. Part B — V2.0 Storefront accelerator

> **Gate:** the Object Edge DS has tokens + aesthetic but **no commerce components**.
> Designing those (B1) blocks the build and is a design-team dependency.

| ID | Task | Depends on | Test |
|---|---|---|---|
| **B0** | **Repo split into `cma-*` plugins** — `cma-core` (V1 pipeline), `cma-storefront`, `cma-seed`, `cma-cms`, per-platform `cma-atg`… in one marketplace; each dual-target (plugin + harness). | F3, A-complete | 🧪 |
| **B1** | **Design the commerce component set** in the Object Edge language — product card, PLP grid, PDP, cart/mini-cart, header/nav + mega-menu, facets, footer. **(design dependency)** | DS | — |
| **B2** | **Design-system package** — vendor `object-edge-design` as a skill; derive a **web-scaled** token ramp from the deck ramp; load fonts via `next/font`. | B1 | 🧪 |
| **B3** | **Component library + Storybook** — implement B1 as React components on the tokens. | B2 | 🧪 |
| **B4** | **Reference Next.js storefront** — pages (home/PLP/PDP/cart) wired to commercetools (SDK/API); theming via tokens; **Storefront Blueprint** (light config) shape + loader. | B3, A3 | 🌐 |
| **B5** | **Node.js backend/BFF** — service layer + commercetools connector (defaults, overridable). | B4 | 🌐 |
| **B6** | **`build-storefront` skill** — inputs: `ccm.json` + blueprint + DS; output: a themed, configured storefront for the client. | B4, B5, F2 | 🌐 |

---

## 5. Part C — V2.1 Demo seeding

| ID | Task | Depends on | Test |
|---|---|---|---|
| **C1** | **New scraping mechanism** (Playwright) — pull a small product sample from a live site → normalized product records. Best-effort, small-sample. | — | 🌐 |
| **C2** | **Mock-product ingestion** — a defined format for client-supplied sample products. | — | 🧪 |
| **C3** | **Seeder** — records → commercetools product drafts (small, polite loader) and/or seed files the app reads. Idempotent by key. | A3, C1/C2 | 🌐 |
| **C4** | **`seed-demo` skill** — orchestrates scrape-or-mock → seed → point at the running app. | C3, B6, F2 | 🌐 |

---

## 6. Part D — V2.2 CMS integration

| ID | Task | Depends on | Test |
|---|---|---|---|
| **D1** | **Content Model (FORMAL)** — JSON Schema (like `ccm.json`) for content types; derive some from the CCM (category/product content) + editorial types. | A1 | 🧪 |
| **D2** | **Sanity schema generation** — Content Model → Sanity `schemaTypes`; free-tier project setup. | D1 | 🌐 |
| **D3** | **Frontend content wiring** — storefront composes commercetools + Sanity behind a thin content interface (swappable). | B4, D2 | 🌐 |
| **D4** | **`integrate-cms` skill**. | D2, D3, F2 | 🌐 |

---

## 7. Cross-cutting

- **Human review + NL prompting** — the report + "tell Claude to change X → regenerate"
  loop applies between every phase; build it into the skill-wiring (F2), not per skill.
- **Testing** — deterministic cores → unit tests (as V1). App/runtime pieces →
  Playwright end-to-end + manual demo verification. Be explicit in each PR about what
  was and wasn't exercised (many 🌐 items can't be fully tested in this sandbox).
- **Versioning** — each `cma-*` plugin is semver'd; the CT/provider support matrix
  (architecture §8/§10) is pinned per release.

---

## 8. Sequencing summary

```
Foundations   F1 workspace/migrate-init → F2 skill-wiring → F3 harness skeleton
     │
Part A (V1)   A1 analyze → A2 plan → A3 emit-all ── (CT project usable) ──┐
              → A4 telecom → A5 docs/website → A6 live-validate → A7 2nd platform
     │                                                                   │
Part B (V2.0) B1 component design (GATE) → B2 DS pkg → B3 Storybook →    │
              B4 Next.js storefront → B5 Node backend → B6 build-storefront ◀┘
     │
Part C (V2.1) C1 scraper / C2 mock → C3 seeder → C4 seed-demo
     │
Part D (V2.2) D1 Content Model → D2 Sanity → D3 wiring → D4 integrate-cms
```

**Minimum path to the first V2 demo:** F1–F2 → A1–A3 → B1–B6 → C1/C2 + C3–C4.
(A4/A5/A7 and Part D can follow.)

---

## 9. Open dependencies & decisions to resolve before building

1. **Commerce component designs (B1)** — the hard gate for V2.0. Owner + timeline?
   Ideally extend the Object Edge DS with the DS author rather than inventing solo.
2. **Live commercetools project + API credentials** — needed for A6, B4–B6, C3, D2+.
3. **commercetools SDK choice** for the storefront/backend (e.g. the TS client) — fix
   once, in B4/B5.
4. **Dev environment** — Node/Next toolchain + a Sanity free-tier account.
5. **Model-reasoning boundary (A1, A5)** — confirm which decisions stay deterministic
   vs go to the model, to keep cost/behavior predictable.
