# adapters/atg

ATG-specific mapping knowledge used by the `analyze-atg` skill and its sub-analyzers
to translate an Oracle ATG / Oracle Commerce source into the
[Canonical Commerce Model](../../ccm/schema/ccm.schema.json).

> **Status: scaffold.** This directory will hold the ATG → CCM mapping rules.

## What lives here (planned)

- **Item-descriptor maps** — how standard ATG item-descriptors (`product`, `sku`,
  `category`, `catalog`, price/profile/organization descriptors) map to CCM entities.
- **Property-type maps** — ATG `<property>` types → CCM attribute `type`
  (`enumerated` → `enum`/`lenum`, multi-valued → `set`, references → `reference`/
  `nested`, etc.).
- **Level rules** — product-level vs. SKU-level properties → CCM `level`
  (`product` / `variant`).
- **Heuristics** — resolving custom item-descriptors (product type vs. custom Type
  vs. custom object) and B2B org structures (organizations/roles/contracts →
  business units / associate roles / product selections).

Adding a different source platform means creating a sibling `adapters/<platform>/`
with the same role — see [`docs/extending.md`](../../docs/extending.md).
