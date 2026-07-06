# Extending the Framework

The whole point of the [hub-and-spoke design](architecture.md#2-hub-and-spoke-architecture)
is that you extend it by adding **spokes**, not by touching the commercetools side.
This guide covers the two most common extensions: **a new source platform** and
**a new domain pack**.

> Read the [Architecture](architecture.md) first — especially the
> [Canonical Commerce Model](architecture.md#4-canonical-commerce-model-ccm). Every
> extension is ultimately "how does this produce (or consume) a valid CCM."

---

## Add a new source platform (e.g. OCC, Shopify, Hybris)

Adding a platform means writing **one analyzer that maps the source → CCM**. You do
**not** touch the planner or the Terraform emitter — they consume the CCM and are
reused as-is.

### 1. Create the analyzer skill

```
skills/analyze-<platform>/SKILL.md      # e.g. skills/analyze-shopify/SKILL.md
```

The SKILL.md frontmatter follows the standard
[skills format](https://code.claude.com/docs/en/skills.md):

```yaml
---
name: analyze-shopify
description: Analyze a Shopify source (API export, theme, docs) into ccm.json.
user-invocable: true
---
```

Model it on `analyze-atg`: a **root skill** that fans out to input-specific
sub-analyzers and reconciles their output by confidence + provenance into one
`ccm.json`.

### 2. Add sub-analyzers for the input types the platform exposes

```
agents/<platform>-<input>-analyzer.md   # e.g. agents/shopify-api-analyzer.md
```

Each is an [agent](https://code.claude.com/docs/en/sub-agents.md) that reads one
input type (API export, code, database, docs, storefront) and emits **partial CCM
fragments** — always with `origin`, `sourceRef`, `confidence`, and any
`decisionsNeeded[]`.

### 3. Add adapter knowledge

```
adapters/<platform>/                     # e.g. adapters/shopify/
```

This is the platform-specific mapping knowledge — how the source's concepts map to
CCM entities (the way `adapters/atg/` maps ATG item-descriptors and property types).

### 4. Map to CCM, not to commercetools

The single most important rule: **your analyzer's only output contract is a valid
`ccm.json`.** If your mappings validate against `ccm/schema/`, the existing planner
and emitter turn them into commercetools Terraform for free. Do not emit HCL or
reference `commercetools_*` resources from an analyzer.

### 5. Reuse the report

`/migration-report` renders any valid CCM — no per-platform work needed.

**Checklist**

- [ ] `skills/analyze-<platform>/SKILL.md` (root, fan-out + reconcile)
- [ ] `agents/<platform>-*-analyzer.md` (one per input type)
- [ ] `adapters/<platform>/` (mapping knowledge)
- [ ] Output validates against `ccm/schema/`
- [ ] No commercetools/Terraform references in the analyzer

---

## Add a new domain pack (e.g. manufacturing, wireless B2B)

Domain packs are **data and priors, not forked pipeline code**. A pack primes the
analyzers and planner with the entities a vertical is expected to contain, and
encodes the commercetools modeling convention for concepts CT lacks natively.

```
domains/<vertical>/                      # e.g. domains/manufacturing/
```

A pack typically contains:

- **Expected entities** — what to look for (e.g. manufacturing: BOMs, configurable
  products, contract pricing tiers).
- **Product-type priors** — the standard shapes/attributes for the vertical, tagged
  `origin: domain-pack` when they land in the CCM.
- **Decision heuristics** — how to resolve common ambiguities for this vertical.

A pack must **not** branch the pipeline or add platform-specific code — if you find
yourself doing that, the logic belongs in an analyzer or the emitter, not a pack.

---

## Keep the CCM contract stable

Analyzers, packs, the planner, and the emitter all meet at the CCM. When you extend:

- **Prefer mapping into existing CCM entities.** Only propose a new CCM entity when
  something genuinely can't be expressed — and then update `ccm/schema/` and the
  emitter together.
- **Isolate commercetools/provider version specifics in the emitter**, never in an
  analyzer or a pack (see the [CT version strategy](architecture.md#versioning--commercetools-updates)).
- **Everything gets provenance.** `origin` + `sourceRef` + `confidence` on every
  element you produce — the review reports and consultant trust depend on it.

---

## Local development

Point Claude Code at your working copy instead of the published plugin:

```
/plugin marketplace add ./                # from the repo root
/plugin install commerce-migration-assistant@<local-marketplace-name>
```

Iterate on skills/agents, re-run against a sample workspace, and validate emitted
CCM against `ccm/schema/` before opening a PR.
