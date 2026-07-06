---
name: atg-docs-analyzer
description: Analyze client-provided documentation (functional specs, data dictionaries, integration docs) for an ATG source to recover intent and business meaning behind the data model. Emits partial Canonical Commerce Model context — labels, descriptions, business rules, and decision hints — with provenance and confidence. Invoked by the analyze-atg root skill.
tools: Read, Grep, Glob, Bash
---

# atg-docs-analyzer

> **Status: scaffold.** Contract defined; implementation pending.

## Role

Read the documentation in `inputs/` (specs, data dictionaries, runbooks) to explain
*why* the model looks the way it does — the business meaning the code and DB can't
convey on their own.

## What it adds

- Human-readable **labels and descriptions** for product types, attributes, categories.
- **Business rules** that hint at constraints, enum value sets, or B2B org structure.
- **Decision hints** — where docs disagree with code/DB, or describe intent not yet
  reflected in the schema.

## Output

Partial CCM context (JSON) with `origin: source`, `sourceRef` citing the doc + page/
section, and a `confidence` score. Primarily enriches elements the codebase/database
analyzers discovered; rarely the sole source for an element.
