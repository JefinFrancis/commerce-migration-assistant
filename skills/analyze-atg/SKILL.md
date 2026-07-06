---
name: analyze-atg
description: Phase 1 of an ATG-to-commercetools migration. Analyze an Oracle ATG / Oracle Commerce source (repository-definition XML, GSA database, documentation, and/or live storefront) and produce a Canonical Commerce Model (ccm.json). Fans out to sub-analyzers and reconciles them. Use after /migrate-init when the source platform is ATG.
user-invocable: true
---

# analyze-atg — Phase 1: analyze the ATG source

> **Status: scaffold.** Structure and contract defined; implementation pending.
> See [`docs/architecture.md`](../../docs/architecture.md) (§3, §5, §10 Scaling) and
> [`ccm/schema/ccm.schema.json`](../../ccm/schema/ccm.schema.json).

## Purpose

Turn whatever the client provided into one validated `ccm.json`. This is the **root
skill**: it dispatches to input-specific sub-analyzers and reconciles their partial
models by **confidence + provenance**.

## Sub-analyzers (agents)

| Agent | Reads | Contributes |
|---|---|---|
| [`atg-codebase-analyzer`](../../agents/atg-codebase-analyzer.md) | repository-definition XML / item-descriptors | intended shape |
| [`atg-database-analyzer`](../../agents/atg-database-analyzer.md) | GSA schema (tables, FKs, cardinality) | real columns, DB-only custom props |
| [`atg-docs-analyzer`](../../agents/atg-docs-analyzer.md) | provided documentation | intent, business meaning |
| [`atg-website-analyzer`](../../agents/atg-website-analyzer.md) | live storefront | what's actually merchandised |

## Adapter knowledge

ATG-specific mapping rules (item-descriptor → CCM, property-type → attribute-type,
product/SKU → product/variant levels) live in [`adapters/atg/`](../../adapters/atg/).

## Output contract

- A single `ccm.json` that **validates against `ccm/schema/ccm.schema.json`**.
- Every element carries `origin`, `sourceRef`, `confidence`, and any `decisionsNeeded[]`.
- Domain priors from the active pack (e.g. [`domains/telecom/`](../../domains/telecom/))
  are merged with `origin: domain-pack`.

## Scale strategy (deterministic parse first — see architecture §10)

Large ATG installs are handled by width and rules, not a bigger context window:

1. **Extract deterministically** — parse repository XML / DB schema into a complete
   **raw inventory** with no model involved. This is the work-list.
2. **Rule-based mapping for the easy majority** via `adapters/atg/`.
3. **Model reasoning only for the hard cases** (custom descriptors, ambiguities,
   conflicts, labels, decisions).
4. **Fan out** the judgment work across sub-analyzers with bounded context; **dedup
   repeated patterns** (reason once, apply to many); **checkpoint** so the run is
   resumable and incremental.

## Steps (to implement)

1. Read `manifest.json`; determine which inputs are present.
2. **Deterministically extract** a raw inventory from each available input
   (sub-analyzers do structured parsing first, model reasoning only where needed).
3. Launch/coordinate the sub-analyzers (in parallel, sharded for large sources)
   against `inputs/`.
4. Merge their partial CCM fragments; resolve conflicts by confidence + provenance;
   record ambiguities as `decisionsNeeded[]`.
5. Apply the domain pack priors.
6. Validate against the CCM schema and write `ccm.json`.
7. Suggest `/migration-report --phase analysis` to review.

## Related

The generic core here is reused by every platform. A new source platform adds its
own `analyze-<platform>` skill + sub-analyzers + `adapters/<platform>/` and targets
this same CCM contract — see [`docs/extending.md`](../../docs/extending.md).
