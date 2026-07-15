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
- Add **demo-data seeding** (**not** full-catalog migration): seed a demo storefront
  with a handful of **scraped** live products or **client-provided mock** products.
- Add **CMS integration** for dynamic content — **Sanity (free tier)** for now.
- Use a **common design system + Storybook** for UI — not random generation or
  scraped UI.
- Keep **human-in-the-loop** review via HTML reports **plus natural-language
  prompting** for iterative adjustments and edge cases.
- Investigate the **Agent Harnesses standard** ("AI Harness", agentharnesses.io) — a
  portable, vendor-neutral packaging format for agent roles (a *packaging* concern,
  distinct from workflow orchestration; see §5.5).

---

## 2. What changes in V2 (delta from V1)

| Area | V1 (today) | V2 (proposed) |
|---|---|---|
| Output | CT project **schema** (Terraform) | Schema **+ data + storefront + backend + CMS** |
| Data | none (schema only) | **Demo seeding** — a small set of scraped/mock products (**not** full-catalog migration) |
| Frontend | none | **Storefront** from a shared design system (Next.js default) |
| Backend | none | **Backend/BFF** (Node.js default) + integration connectors |
| Content | none | **CMS** — Sanity (free tier) for dynamic content |
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
5. Demo seeding      seed the demo app with a SMALL set of products — scraped from
                     the client's live site OR supplied as client mock data
                     (NOT full-catalog migration)
6. CMS Integration   wire Sanity (free tier) for dynamic content
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
                         └── demo seed       -> a few products (scrape/mock) into the demo app
```

- **CCM (schema)** — unchanged from V1; the stable center.
- **Demo seeder** — reuses the CCM's *mappings* to shape a *small* set of scraped or
  mock products into commercetools/CMS drafts for the demo app. It is deliberately
  **not** a full data-migration engine — no bulk throughput or canonical "data model".
**Companion models — what they are.** The CCM describes the *schema* (product types,
categories, custom fields…). V2 produces two more things that the CCM does not
describe: **content** (for the CMS) and a **storefront** (UI). A "companion model" is
a small, focused model that sits *beside* the CCM to describe one of those concerns —
derived partly from the CCM, but kept separate so the CCM stays a clean schema hub.

- **Content Model** — the content types the CMS (Sanity) needs. Some mirror commerce
  entities (a CCM category → a "category page" content type); some are purely
  editorial (home hero, promo banner, blog post). It becomes the Sanity schema.
  ```
  contentTypes:
    - key: categoryPage    # derived from CCM categories
      fields: [heroImage, intro, seoTitle, seoDescription]
    - key: homeHero        # editorial-only
      fields: [headline, subhead, image, ctaLabel, ctaHref]
  ```

- **Storefront Blueprint** — a *configuration* (not code) that binds the shared
  design-system components to this client's catalog/content + theme. It is the recipe
  that turns the generic reference storefront into *this* client's storefront.
  ```
  theme: object-edge
  pages:
    home: [Hero(homeHero), FeaturedProducts(category=smartphones), PromoBanner]
    plp:  { component: ProductGrid, facets: [color, storage_gb, brand] }
    pdp:  { attributes: [color, storage_gb, contract_term_months], gallery: true }
  nav: from CCM categories (top 2 levels)
  ```

**Decision:**

- **Content Model → formal** — a schema'd artifact like `ccm.json` (JSON Schema,
  validated, generated by a skill, reviewable in an HTML report). Sanity needs a real
  schema and it maps cleanly from the CCM, so formalizing pays off.
- **Storefront Blueprint → light config** — loose YAML/JSON, hand-authored, no formal
  schema. It is presentation glue that churns early; keep it flexible and formalize
  later only if patterns stabilize.

---

## 5. New subsystems

### 5.1 Demo seeding (NOT full data migration)  ✅ scope reduced

**Decision:** this framework does **not** migrate the client's full catalog/data.
Its job is to **quickstart a demo storefront** populated with a *small* set of
products, so the client sees a working, branded site fast.

- **Two input modes:**
  - **Scrape** a handful of real products from the client's existing live site
    (for a "here's your store, rebuilt" showcase); or
  - **Client mock products** — a small dataset the client hands over — ingested into
    the generated application.
- **Small volume by design** → the hard problems of bulk migration (Import API at
  scale, rate limits / 429 backoff, multi-hour resumable jobs) are **out of scope**.
  A simple, polite loader against the CT API (or seed files the app reads) is enough.
- **Deterministic-first**, like the analyzers: shape records with mapping code,
  reserve the model for messy/ambiguous values.
- **Explicitly out of scope (for now):** full production data migration. If a client
  later needs it, that is a separate effort (Import API / commercetools-sync,
  limits-aware) — documented as a future extension, not part of this framework.

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

#### Design system: Object Edge — "The Missing Layer"

The foundation is the **Object Edge brand design system**, exported from Claude
Design (namespace `ObjectEdgeDesignSystem_cf2683`). It is already packaged as an
**Agent Skill** (`object-edge-design`), so it drops straight into our
skills/harness model.

**What it gives us (the foundation):**

- A production-grade **token layer** (`colors_and_type.css`): grounds
  (paper `#F4EFE6` / ink `#0A0B0D` / teal `#0E3B3C`), amber accent `#C97A2A`,
  light + dark foreground/rule tokens, **Inter Tight + JetBrains Mono**, a full type
  scale, tracking, line-heights, spacing rhythm, radii, and weights, plus semantic
  type classes (`.oe-display`, `.oe-body`, `.oe-eyebrow`, …).
- A clear **aesthetic doctrine**: warm paper ground, ink for emphasis, teal
  interludes, amber sparingly, those two typefaces only, no gradients/emoji.
- UI kits (Hive OE console desktop/mobile, objectedge.com marketing) and slide
  templates — useful as references for the visual language.

**Honest gap (what we still build):** it is a **brand / marketing / deck / console**
system, **not a commerce component library**. It has no product card, PLP grid,
PDP, cart, mini-cart, checkout, facets, or mega-nav. Its type scale is also
*deck-scaled* (display 168px, body 34px @ 1920×1080). So V2.0 still **builds the
commerce components on top**, in this exact visual language, using a **web-scaled**
type ramp derived from the same ratios (the Hive OE app kit shows the realistic UI
scale, e.g. 14px body).

**How it plugs in:**

1. Map `colors_and_type.css` tokens → the Next.js storefront theme (`next/font` for
   the two typefaces; CSS variables / Tailwind theme).
2. Build the commerce components (product card, PLP, PDP, cart, nav) in **Storybook**
   styled with these tokens and the Object Edge aesthetic.
3. Vendor the DS into the harness as `skills/object-edge-design/`; the
   `build-storefront` skill consumes it. Per client = re-theme the tokens, keep the
   commerce components.

Net: the DS is roughly the **foundation** (tokens, type, brand, aesthetic); the
commerce component library is the V2.0 build on top of it.

### 5.3 CMS integration

- **Decision: use Sanity's free tier for now.** Sanity Studio (the editing UI) is
  open-source (MIT); its backend is hosted SaaS, and the free tier is enough for
  demos. Self-hosting / OSS-only alternatives (Payload, Strapi, Directus) are
  **deferred** — revisit only if a client requires a fully self-hosted CMS.
- Content types derive partly from the CCM (product/category content) plus editorial
  types; the frontend composes **commerce data (CT) + content (CMS)**.
- Keep the CMS integration **behind a thin content interface** so the free-tier
  Sanity choice can be swapped later without touching the storefront components.

### 5.4 Scraping (coordinate with Sivaram)

- **Primary use now:** pull a **handful of real products** from the client's live
  site to seed the demo storefront (§5.1). Small volume, showcase-oriented.
- **Secondary use:** capture look-and-feel cues for quick mock/demo components.
- **Tech:** JS-rendered sites need a headless browser — **Playwright is already
  available** in the Claude Code environment.
- **Decision:** build a **new scraping mechanism** for V2 (not dependent on any
  prior/existing component). Playwright-based, small-sample, best-effort.
- Since we only need a **small sample** (not the whole catalog), scraping brittleness
  is far less risky than in a full-migration scenario — keep it best-effort with mock
  products as the always-available fallback.

### 5.5 Packaging & orchestration — the "AI Harness" clarified

The "AI Harness" Jags mentioned is the **Agent Harnesses standard**
(https://agentharnesses.io, https://github.com/agentharnesses/agentharnesses) —
**not** Harness.io's CI/CD product. These are two separate concerns and should be
decided separately:

**(A) Packaging & portability — Agent Harnesses standard.**

- An open, vendor-neutral format (Apache-2.0) for packaging an agent's **role** =
  context + capabilities. A harness is a directory:
  ```
  my-harness/
  ├── HARNESS.md          # required: YAML frontmatter (name, description) + routing body
  ├── .leaf-detectors     # patterns marking leaves, e.g. skill=SKILL.md
  └── tools/ data/ …/     # author-named dirs, each with an uppercase routing file (TOOLS.md)
  ```
- **Progressive disclosure** loading: Load (`HARNESS.md` at start) → Discovery (read
  routing files when a task arrives) → Activation (load only the relevant skill/dir)
  → Execution (run bundled scripts). This keeps context lean — the same concern as
  §10 scaling.
- It **builds on the Agent Skills standard** — the same `SKILL.md` unit our V1
  plugin already uses. Ships a Python reference CLI (`ahar init/validate/prompt`).
- **Key point:** this is about *packaging and context loading*, **not** workflow/DAG
  orchestration. It does not, by itself, "manage workflows"; it standardizes how an
  agent role is defined and distributed.
- **Relevance to us:** our repo is *already* skills + asset dirs. Expressing it as a
  valid Agent Harness (add a `HARNESS.md`, routing files, and a `.leaf-detectors`
  mapping `skill=SKILL.md`) would make the framework **portable across any
  harness-compatible runtime — not just Claude Code** — directly serving the
  "other devs can use this" goal. Low effort because the structure already aligns.
  Recommendation: **dual-target** every plugin — keep the Claude Code plugin form
  *and* expose an Agent Harness view of the same tree. With the split-packaging
  decision (§7), each per-capability plugin (`cma-core`, `cma-storefront`, …) is its
  own dual-target unit in the shared marketplace.

**(B) Workflow orchestration — DECIDED: stay Claude-native.**

- We run interactively on **Claude Code** (skills + subagents + the Workflow tool),
  which also gives us the NL-review loop "for free." **This is the decision** — no
  external agent framework.
- External graph runtimes (**LangGraph**, **Microsoft Agent Framework**) are heavier
  and diverge from the Claude-native + harness model; only revisit on clear evidence
  of a need we can't meet natively.
- Any *batch* work (e.g. demo seeding) runs as plain, testable Python jobs — not an
  agent framework.

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
- **API limits** are a minor concern now that data is demo-seeding only (small
  volume) — just be polite to the CT API; no bulk-throughput engineering needed.
- Reaffirm the V1 trade-off: the canonical model adds complexity but gives a
  consistent, industry-structured model — especially valuable for clients on
  **multiple** source platforms.

---

## 7. Key decisions

### Decided

- **Scope sequencing → phased rollout** (see §8).
- **Data → demo seeding only** — a small set of scraped or client-mock products;
  **no full-catalog migration** (§5.1).
- **CMS → Sanity free tier** for now; self-hosted OSS alternatives deferred (§5.3).
- **Design system → adopt Object Edge "The Missing Layer"** as the foundation; build
  the commerce components on top of it (§5.2).
- **Default stacks → Next.js (frontend) / Node.js (backend)**, with overrides.
- **Workflow orchestration → Claude-native** (no external agent framework) (§5.5).
- **Packaging → split into per-capability plugins in one marketplace** (e.g.
  `cma-core`, `cma-storefront`, `cma-seed`, `cma-cms`, and per-platform `cma-atg` …),
  each also expressed as a **dual-target Agent Harness** (§5.5, §11).
- **Companion models → Content Model formal, Storefront Blueprint light** (§4).

### Still open

_All V2 direction questions are resolved. Remaining work is implementation planning
per phase (V2.0 → V2.2, §8)._

---

## 8. Phased rollout & risks

**Phased rollout** (the headline deliverable is an *instant, branded demo site*):

- **V2.0 — Storefront accelerator.** The reusable asset: shared design system +
  Storybook + reference Next.js/Node app wired to a V1-generated commercetools
  project. Per-client = theme + configure.
- **V2.1 — Demo quickstart.** Seed the themed app with a small set of products —
  scraped from the client's live site or client-supplied mock data (§5.1). Depends
  on V2.0 + scraping (Sivaram).
- **V2.2 — CMS integration.** Wire Sanity (free tier) for dynamic content (§5.3).
- Packaging (dual-target harness) and the NL-review loop are threaded through as the
  above land, not separate phases.

**Risks** (notably smaller after the data de-scope):

- **Storefront accelerator is now the largest build** — a real design system +
  reference app is significant work; treat V2.0 as the main investment.
- **Scraping reliability** — brittle, but low-stakes here: we only need a small
  sample, and client mock data is the always-available fallback.
- **Orchestration lock-in** — don't adopt an external workflow framework without
  clear need; it fights the Claude-native + harness distribution model.
- **Scope creep back toward full data migration** — guard the boundary; keep this a
  demo/quickstart tool, not a bulk-migration engine.

---

## 9. Action items (from the calls)

- **Jefin** — "AI Harness" identified as the **Agent Harnesses standard** (§5.5);
  next step is to prototype the dual-target harness layout (§11) and run
  `ahar validate`.
- **Jefin** — design a **new scraping mechanism** for demo seeding (§5.4).
- **Jefin** — secure/document the meeting transcripts.

> Dropped from the original call notes (no longer pursued): a dedicated additional
> engineer, reusing a prior scraping component, and a separate dev machine.

---

## 10. References

- commercetools — product modeling best practices:
  https://docs.commercetools.com/learning-model-your-product-catalog/product-modeling/best-practices
- commercetools — categorization best practices:
  https://docs.commercetools.com/learning-model-your-product-catalog/categorization/best-practices-and-advanced-category-management
- commercetools — API limits: https://docs.commercetools.com/api/limits
- Agent Harnesses standard (the "AI Harness" meant): https://agentharnesses.io/home
- Agent Harnesses standard — repo + spec + CLI: https://github.com/agentharnesses/agentharnesses
- AI agent frameworks overview (for workflow orchestration, separate concern):
  https://www.langchain.com/resources/ai-agent-frameworks
- Harness.io Worker Agents (CI/CD — NOT the tool meant, noted to avoid confusion):
  https://www.harness.io/products/harness-ai/agents

---

## 11. Appendix — Dual-target Agent Harness layout (sketch)

The framework can be **both** a Claude Code plugin **and** a valid Agent Harness from
the *same* tree. This is **purely additive** — no existing V1 file moves or changes.
The Claude Code runtime reads `.claude-plugin/` + `skills/` and ignores the harness
files; a harness-compatible runtime reads `HARNESS.md` + routing files + leaf
detectors and ignores the plugin manifest. Both share the same `skills/` and assets.

```
commerce-migration-assistant/
├── HARNESS.md              # NEW  role entry: frontmatter + routing body
├── .leaf-detectors         # NEW  e.g. `skill=SKILL.md` → each skills/* is a skill leaf
├── .claude-plugin/         # kept  Claude Code plugin (plugin.json, marketplace.json)
├── skills/                 # kept  Agent Skills — shared by BOTH targets
│   ├── SKILLS.md           # NEW  routing file for the skills branch
│   ├── migrate-init/SKILL.md
│   ├── analyze-atg/SKILL.md
│   ├── plan-migration-to-ct/SKILL.md
│   ├── emit-terraform/SKILL.md
│   ├── migration-report/SKILL.md
│   └── (V2) build-storefront/ · seed-demo/ · integrate-cms/
├── agents/                 # kept  + AGENTS.md   (NEW routing file)
├── adapters/               # kept  + ADAPTERS.md (NEW)  — ATG→CCM knowledge (references)
├── emitters/               # kept  + EMITTERS.md (NEW)
├── reporters/              # kept  + REPORTERS.md (NEW)
├── domains/                # kept  + DOMAINS.md  (NEW)
├── ccm/                    # kept  + CCM.md      (NEW)  — the canonical schema
└── docs/                   # kept  (architecture, usage, extending, v2/)
```

**`HARNESS.md`** (new, root):

```markdown
---
name: Commerce Migration Assistant
description: Migrate any commerce platform to commercetools — analyze a source into
  a Canonical Commerce Model, plan the target, emit Terraform, and (V2) stand up a
  themed demo storefront seeded with sample products.
---

Routing:
- `skills/` — the migration capabilities (see SKILLS.md)
- `ccm/` — the Canonical Commerce Model schema (see CCM.md)
- `adapters/` — per-platform source→CCM knowledge (see ADAPTERS.md)
- `emitters/` — CCM→Terraform templates (see EMITTERS.md)
- `reporters/` — read-only HTML review reports (see REPORTERS.md)
- `domains/` — vertical packs, e.g. telecom (see DOMAINS.md)
```

**`.leaf-detectors`** (new, root):

```
skill=SKILL.md
```

**`skills/SKILLS.md`** (new — routing so an agent loads only the skill it needs,
progressive disclosure):

```markdown
- `migrate-init/` — capture project context
- `analyze-atg/` — ATG source → ccm.json (fans out to the atg-* analyzers)
- `plan-migration-to-ct/` — CCM → commercetools target design
- `emit-terraform/` — CCM → Terraform (labd/commercetools)
- `migration-report/` — render the read-only HTML review report
```

**Validation:** `pip install agentharnesses-cli && ahar validate .` (a CI check).

**Why this is worth it:** it makes the whole framework runnable on *any*
harness-compatible runtime — not only Claude Code — which is the vendor-neutral
answer to "other devs / teams can pick this up and use it". It also formalizes the
progressive-disclosure loading that keeps context lean as we add platforms, domains,
and the V2 storefront/CMS skills (§10 scaling).

> Not applied yet — this is the V2 target layout. Introducing it is a V2.0 task and
> would be additive over the current (V1) tree.

**With split packaging (§7):** the sketch above shows one unit. In V2 the framework
is several plugins in one marketplace — e.g. `cma-core` (the V1 pipeline:
init/analyze/plan/emit/report), `cma-storefront`, `cma-seed`, `cma-cms`, and
per-platform `cma-atg` / `cma-occ` … — and **each** carries its own `HARNESS.md` +
`.claude-plugin/` (dual-target). A top-level `marketplace.json` lists them all; the
current single-plugin V1 repo becomes `cma-core`.
