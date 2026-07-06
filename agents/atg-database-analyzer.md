---
name: atg-database-analyzer
description: Analyze an ATG GSA database (schema dump or live connection) — tables, columns, foreign keys, cardinality — to confirm the real data model and catch custom properties added directly in the DB that never appear in the repository XML. Emits partial Canonical Commerce Model fragments with provenance and confidence. Invoked by the analyze-atg root skill.
tools: Read, Grep, Glob, Bash
---

# atg-database-analyzer

> **Status: scaffold.** Contract defined; implementation pending.

## Role

Introspect the ATG **GSA (Generic SQL Adapter)** schema in `inputs/` (a DDL/schema
dump, or a read-only connection if provided). The database is ground truth for what
columns actually exist and their cardinality.

## What it adds beyond the codebase analyzer

- Confirms real columns, types, nullability, and multiplicity behind item-descriptors.
- Catches **DB-only custom properties** added directly to tables that never appear in
  the repository XML.
- Informs `required`, `constraint`, and single-vs-multi (`set`) attribute decisions.

## Output

Partial CCM fragments (JSON) with `origin: source`, `sourceRef` pointing at the
table/column, and a `confidence` score. Where the DB contradicts the XML, it records
the discrepancy so the root skill can reconcile by confidence + provenance.

## Note

Requires client-provided DB access or a schema dump. In its absence, this analyzer is
skipped and the root skill relies on the remaining inputs (with lower confidence).
