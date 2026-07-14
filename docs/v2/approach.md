# Commerce Migration Assistant — V2 Direction & Brainstorm

> **Status: brainstorm / direction — NOT final, NOT implemented.**
> This document is intentionally separate from the V1 design. **V1 is unchanged**
> (`docs/architecture.md` and the shipped pipeline remain the source of truth for
> what exists today). V2 is a *superset* of V1: it keeps the V1 phases and adds new
> ones. Nothing here modifies V1 behavior.

Derived from the manager update and three meetings (Jefin/Jags, Adriano/Jefin, and
the stakeholder strategy notes), July 2026.

---

## 1. Context

V1 delivers a schema-only migration: **init → analyze → review → plan → emit
(Terraform)**, producing a reproducible commercetools *project schema* via a
Canonical Commerce Model (CCM). Stakeholders now want to expand this from a *schema
generator* into a *full migration + application accelerator*.

Confirmed directions from the calls:

- Keep the phased, platform-agnostic, AI-driven approach and the canonical model
  (Jags: keep it **current** and **domain-adapted**, e.g. Telco).
- Expand scope beyond the object model to **frontend + backend component migration**.
- Add **data migration** (populate the new environment, incl. scraping live sites).
- Add **CMS integration** for dynamic content (open-source, e.g. Sanity).
- Use a **common design system + Storybook** for UI — not random generation or
  scraped UI.
- Keep **human-in-the-loop** review via HTML reports **plus natural-language
  prompting** for iterative adjustments and edge cases.
- Investigate an **agent/workflow framework** ("AI Harness") for orchestration.

---

## 2. What changes in V2 (delta from V1)

| Area | V1 (today) | V2 (proposed) |
|---|---|---|
| Output | CT project **schema** (Terraform) | Schema **+ data + storefront + backend + CMS** |
| Data | none (schema only) | **Data migration** via CT Import API, incl. scraping |
| Frontend | none | **Storefront** from a shared design system (Next.js default) |
| Backend | none | **Backend/BFF** (Node.js default) + integration connectors |
| Content | none | **CMS** (Sanity/OSS) for dynamic content |
| Review | read-only HTML + edit JSON | HTML **+ natural-language prompting** loop |
| Orchestration | Claude Code skills + Python | Evaluate explicit agent/workflow framework |
| Scraping | none | Dual use: **data population** + **quick demo mocks** |

V1's phases 1–3 (init → analyze → plan/emit-schema) become the **core** of V2,
unchanged in spirit. V2 adds phases 4–6.

---

## 3. Revised end-to-end flow (V2)

```
1. Initialization    project context (client, domain, source platform, inputs)
2. Analysis          source -> Canonical Commerce Model (+ human review)
3. Design & Planning CCM -> commercetools schema (Terraform)          [V1 core]
   ── review (HTML report + natural-language prompting) ──
4. Frontend/Backend  storefront + backend from the shared design system,
                     Next.js / Node defaults with overrides
5. Data Migration    populate commercetools (Import API), source export and/or
                     scraped live data; throttled, resumable, idempotent
6. CMS Integration   wire an OSS CMS (e.g. Sanity) for dynamic content
```

Human review and NL prompting apply **between every phase**, as in V1.

---

## 4. How V2 extends the V1 architecture

The **hub-and-spoke** design still holds — and it is what makes this expansion
tractable. The recommendation is to **keep the CCM as the schema hub** (its strength
is normalizing *structure*), and add **companion models** rather than bloating it:

```
                         ┌── (V1) CT schema  -> Terraform emitter
   sources ─▶ analyzers ─┼── Content Model   -> CMS (Sanity) schema
        (spokes)   CCM ──┤── Storefront blueprint -> component/config generation
                         └── data mappings   -> Import API data pipeline
```

- **CCM (schema)** — unchanged from V1; the stable center.
- **Data pipeline** — reuses the CCM's *mappings* to transform source *records* into
  commercetools import drafts. It does **not** need a separate canonical "data model";
  it needs mapping + throughput.
- **Content Model** — a companion model for CMS content types (some derived from the
  CCM, e.g. category/product content; some editorial-only).
- **Storefront blueprint** — configuration that binds the shared design-system
  components to this client's catalog/content (not bespoke code generation).

Open question: do we formalize "Content Model" and "Storefront blueprint" as new
schema'd artifacts (like `ccm.json`), or keep them as lighter config? (See §7.)

---

## 5. New subsystems

### 5.1 Data migration  ⭐ highest effort / highest risk

- **Not Terraform.** Terraform is for schema/config, not bulk records. Use the
  commercetools **Import API** (import containers/operations) and/or
  **commercetools-sync**. Terraform stays for schema; data is a separate pipeline.
- **Respect API limits.** commercetools enforces rate limits (HTTP 429) and request
  quotas; bulk loads must be **batched, throttled with backoff, resumable, and
  idempotent** (stable keys so re-runs converge). *Exact limits must be pulled from
  the CT docs in a live environment — automated fetch is blocked here.*
- **Source priority.** A **source DB export is authoritative**; scraping is a lossy
  fallback. Prefer exports for real data; use scraping to fill gaps or for demos.
- **Deterministic-first**, like the analyzers: transform records with mapping code,
  reserve the model for messy/ambiguous values.

### 5.2 Storefront / component accelerator

The steer from the call: **do not randomly generate or scrape the real UI.** Instead:

- Maintain a **shared design system** — a curated component library with
  **Storybook** (cards, PLP/PDP, cart, etc.) that is the reusable asset.
- Maintain a **reference storefront** (Next.js default) wired to commercetools + CMS.
- **Per client = theme + configure**, not rebuild: apply brand tokens and bind
  components to the client's catalog/content via the storefront blueprint.
- **Backend** (Node.js default) = BFF/API layer + connectors (CT, CMS). Defaults with
  **overrides** for teams with other stacks.
- **Scraping is only for throwaway demos/mocks** to showcase quickly — a separate,
  lower-fidelity track from the real accelerator.

### 5.3 CMS integration

- Use an **open-source headless CMS** for dynamic content; the call named **Sanity**.
- **Nuance to resolve:** Sanity's *Studio* is open-source (MIT), but its content
  backend/datastore is a **hosted SaaS** — it is not fully self-hostable. If
  "open-source" means *self-hosted*, alternatives are **Payload, Strapi, or
  Directus**. Decision needed (see §7).
- Content types derive partly from the CCM (product/category content) plus editorial
  types; the frontend composes **commerce data (CT) + content (CMS)**.

### 5.4 Scraping (coordinate with Sivaram)

- **Two distinct uses:** (a) supplementary **data** source for migration; (b) fast
  **demo/mock** component generation for showcasing.
- **Tech:** JS-rendered sites need a headless browser — **Playwright is already
  available** in the Claude Code environment.
- **Action item:** confirm the status of Sivaram's existing scraping component and
  whether V2 consumes it or builds fresh.
- Position scraping as **fallback/demo**, never the authoritative data source.

### 5.5 Orchestration — "AI Harness" evaluation

- **We already run on an agent harness: Claude Code** (skills + subagents + the
  Workflow tool). V1's plugin distribution model depends on this.
- **Harness.io "AI / Worker Agents"** is CI/CD-pipeline-oriented — likely **not** the
  fit for an interactive migration tool.
- If we ever need explicit, deterministic, long-running **graph orchestration**, the
  real contenders are **LangGraph** or the **Microsoft Agent Framework** — but
  adopting one **diverges from the Claude Code plugin model** and adds a heavier
  runtime. NL review "for free" is a strength of staying Claude-native.
- **Lean:** keep the *interactive* workflow Claude-native; run *batch* jobs
  (data migration) as plain, testable Python jobs — which need scheduling/retry, not
  necessarily an agent framework. Treat "adopt a framework" as a deliberate,
  evidence-based decision, not a default. (Jefin action item to evaluate.)

### 5.6 Human review + natural-language prompting

- Keep V1's read-only HTML reports (regenerate on demand).
- Add an explicit **NL prompting loop**: the reviewer tells Claude, in plain
  language, what to change; Claude edits the underlying artifact (CCM, mappings,
  blueprint) and regenerates. This is native to Claude Code — reinforcing §5.5.

---

## 6. Canonical model: currency, domain adaptation, CT best practices

- Keep the CCM; **keep it current** and **domain-adapted** (Telco pack first, as in
  V1's roadmap).
- Encode commercetools **product-modeling** and **categorization** best practices
  into the planner (e.g. categories-vs-attributes guidance, variant modeling) — pull
  the specifics from the CT learning docs in a live environment.
- Feed **API limits** into the data-migration pipeline's batching/throttling.
- Reaffirm the V1 trade-off: the canonical model adds complexity but gives a
  consistent, industry-structured model — especially valuable for clients on
  **multiple** source platforms.

---

## 7. Key decisions & open questions

1. **Scope sequencing** — do all of 4/5/6 at once, or phase them? (Recommend phased —
   see §8.)
2. **Companion models** — formalize a schema'd "Content Model" and "Storefront
   blueprint", or keep them as lighter config?
3. **CMS choice** — Sanity (OSS Studio + hosted backend) vs a fully self-hostable OSS
   CMS (Payload / Strapi / Directus)? Depends on whether "open-source" means
   "self-hosted".
4. **Data source of truth** — source DB export vs scraping as primary? (Recommend
   export-primary, scraping-fallback.)
5. **Orchestration** — stay Claude-native vs adopt LangGraph / MS Agent Framework?
   (Recommend Claude-native for interactive; plain jobs for batch.)
6. **Default stacks** — confirm Next.js (frontend) / Node.js (backend); define the
   override mechanism.
7. **Design system** — build fresh, or adopt/extend an existing component library +
   Storybook?
8. **Relationship to V1** — is V2 a new major version of the same plugin, or a
   separate set of plugins in the same marketplace (e.g. `cma-data`, `cma-storefront`,
   `cma-cms`)?

---

## 8. Risks & recommended rollout

- **Scope explosion.** Six phases and ~five new subsystems is a lot. Recommend a
  **phased V2**:
  - **V2.0 — Data migration** (highest value on top of V1's schema; unlocks a
    populated environment).
  - **V2.1 — Storefront accelerator** (design system + Storybook + reference app).
  - **V2.2 — CMS integration** (Sanity/OSS).
  - Scraping and NL-review threaded through as they mature.
- **Data correctness & volume** — the biggest new risk; needs limits-aware,
  resumable, idempotent tooling and strong verification.
- **Scraping reliability** — brittle across sites; keep it fallback/demo.
- **Orchestration lock-in** — adopting an external framework could fight the plugin
  distribution model; decide deliberately.
- **CMS "OSS" ambiguity** — resolve self-hosted vs hosted before committing to Sanity.

---

## 9. Action items (from the calls)

- **Jefin** — check with **Sivaram** on the scraping component status.
- **Jefin** — evaluate "AI Harness" applicability (see §5.5 — likely re-frame as
  "do we need an external agent framework at all?").
- **Jefin** — request a second laptop to isolate dev environments.
- **Jefin** — secure/document the meeting transcripts.
- **Adriano** — consult Jacks/Kiran on additional resourcing (Cspire bandwidth).

---

## 10. References

- commercetools — product modeling best practices:
  https://docs.commercetools.com/learning-model-your-product-catalog/product-modeling/best-practices
- commercetools — categorization best practices:
  https://docs.commercetools.com/learning-model-your-product-catalog/categorization/best-practices-and-advanced-category-management
- commercetools — API limits: https://docs.commercetools.com/api/limits
- AI agent frameworks overview: https://www.langchain.com/resources/ai-agent-frameworks
- Harness.io Worker Agents (CI/CD-oriented): https://www.harness.io/products/harness-ai/agents
