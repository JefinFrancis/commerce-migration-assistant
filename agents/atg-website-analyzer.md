---
name: atg-website-analyzer
description: Inspect a live ATG storefront (crawl catalog, category, and product pages) to sanity-check what is actually merchandised against the model derived from code, database, and docs. Emits corroborating Canonical Commerce Model signals with provenance and confidence. Invoked by the analyze-atg root skill.
tools: Read, Grep, Glob, Bash, WebFetch
---

# atg-website-analyzer

> **Status: scaffold.** Contract defined; implementation pending.

## Role

Crawl/inspect the live storefront URL from `manifest.json` to observe what is
*actually* merchandised — the reality check on the code/DB/docs model.

## What it adds

- Confirms which categories, product types, and attributes are **customer-facing**
  vs. dormant in the schema.
- Surfaces facet/filter attributes and enum value sets visible in the UI.
- Flags gaps: things on the site not found in the model (and vice-versa) as
  `decisionsNeeded[]`.

## Output

Corroborating CCM signals (JSON) with `origin: source`, `sourceRef` citing the crawled
URL, and a `confidence` score. Used mainly to raise or lower confidence on elements
the other analyzers found.

## Note

Requires a reachable storefront URL. Respect the client's environment (rate limits,
non-production URLs). Skipped if no site is available.
