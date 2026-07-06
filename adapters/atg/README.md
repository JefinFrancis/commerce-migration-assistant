# adapters/atg

ATG-specific mapping knowledge used by the `analyze-atg` skill and its sub-analyzers
to translate an Oracle ATG / Oracle Commerce source into the
[Canonical Commerce Model](../../ccm/schema/ccm.schema.json).

> **Status: in progress.** The deterministic codebase analyzer is implemented; the
> database/docs/website analyzers and model-reasoning layer are still to come.

## Implemented

```
extract.py     parse ATG repository-definition XML -> raw inventory (no model)
db_extract.py  parse ATG GSA schema DDL -> raw inventory (tables, columns, FKs)
mappings.py    ATG data-type / SQL-type -> CCM attribute-type rules; classification
to_ccm.py      assemble CCM fragments with provenance; reconcile against the DB
analyze.py     CLI (see below)
fixtures/      synthetic productCatalog.xml + productCatalog_schema.sql
tests/         unit tests incl. reconciliation + CCM-schema conformance
```

CLI:

```
# codebase only
python3 adapters/atg/analyze.py <repository.xml> --client N --domain D [--out F]
# codebase + database reconciliation
python3 adapters/atg/analyze.py <repository.xml> --db <schema.sql> [--out F]
```

Reconciliation (when `--db` is supplied): corrects `required` from `NOT NULL`,
boosts confidence on confirmed columns, and surfaces **DB-only columns** (present in
the schema but absent from the XML) as attributes carrying a decision.

Run the tests from the repo root:

```
python3 -m unittest discover -s adapters/atg/tests
```

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
