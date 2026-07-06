---
name: atg-codebase-analyzer
description: Analyze an ATG source code checkout — repository-definition XML (e.g. productCatalog.xml) and item-descriptors — to extract the intended data model. Emits partial Canonical Commerce Model fragments (product types, attributes, categories) with provenance and confidence. Invoked by the analyze-atg root skill.
tools: Read, Grep, Glob, Bash
---

# atg-codebase-analyzer

> **Status: scaffold.** Contract defined; implementation pending.

## Role

Read the ATG **repository-definition XML** in `inputs/` and derive the intended
shape of the catalog. In ATG, `<item-descriptor>` = a type and `<property>` = a
field/column.

## Mapping (see `adapters/atg/`)

- `item-descriptor` "product" → a CCM **productType**; properties split by level:
  SKU-level → `level: variant`, product-level → `level: product`.
- `<property>` types → CCM attribute `type` (`enumerated` → `enum`/`lenum`,
  multi-valued → `set`, item reference → `reference`/`nested`, date/double/boolean →
  equivalents).
- `category` items → CCM **categories**.
- Custom item-descriptors with no CT equivalent → flag as a `decisionNeeded`
  (product type vs. custom Type vs. custom object).

## Output

Partial CCM fragments (JSON) validating against `ccm/schema/ccm.schema.json`, each
element with `origin: source`, a `sourceRef` (file + item/property), and a
`confidence` score. The `analyze-atg` root skill reconciles these with the other
analyzers.
