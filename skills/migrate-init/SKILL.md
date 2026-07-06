---
name: migrate-init
description: Phase 0 of a commercetools migration. Initialize a client migration workspace — capture client pre-context (client name, domain, source platform, B2B/B2C, available inputs) into manifest.json. Use at the very start of a new migration engagement.
user-invocable: true
---

# migrate-init — Phase 0: initialize the workspace

> **Status: scaffold.** Structure and contract defined; implementation pending.
> See [`docs/architecture.md`](../../docs/architecture.md) and
> [`docs/usage.md`](../../docs/usage.md).

## Purpose

Set up a per-client migration **workspace** and capture the pre-context every later
phase depends on.

## Inputs (prompt the user)

- **client** — client name.
- **domain** — vertical / domain pack (e.g. `telecom`).
- **sourcePlatform** — `atg` (first supported), later `occ`, `shopify`, ….
- **audience** — `b2c`, `b2b`, or `b2b+b2c`.
- **inputs** — which artifacts exist: source code, database, docs, live website (any
  combination; more inputs → higher-confidence analysis).

## Outputs

- `manifest.json` — the captured context (mirrors `meta` in the CCM schema).
- `inputs/` — directory for the client's artifacts (code checkout, DB dump, docs).
- Empty `ccm.json`, `mappings/`, `reports/`, `terraform/`, `decisions.md` placeholders.

## Steps (to implement)

1. Prompt for the context above (or read it from arguments).
2. Write `manifest.json`.
3. Create the workspace directory skeleton.
4. Tell the user what to drop into `inputs/` and to run `/analyze-<sourcePlatform>` next.
