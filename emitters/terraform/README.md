# emitters/terraform

Templates and module structure used by the `emit-terraform` skill to render the
[Canonical Commerce Model](../../ccm/schema/ccm.schema.json) into Terraform (HCL)
for the [`labd/commercetools`](https://registry.terraform.io/providers/labd/commercetools/latest/docs)
provider.

> **Status: in progress.** `emit.py` renders product types, categories, and
> customer groups; the remaining resource families are still to come.

## Implemented (`emit.py`)

```
python3 emitters/terraform/emit.py <ccm.json> --out-dir <terraform/>
```

Emits, for each resource family present in the CCM:

- `versions.tf` — pinned `required_providers { commercetools = { ... } }`
  (version from `meta.providerVersion`, default `~> 1.20`).
- `product-types.tf` — `commercetools_product_type`, explicit generated blocks
  (attributes with type/label/required/constraint; enum values; set element types;
  reference targets).
- `categories.tf` — `commercetools_category` via `for_each` over a data map, with
  parent resolved by self-reference.
- `customer-groups.tf` — `commercetools_customer_group` via `for_each`.

Tests (`tests/test_emit.py`) assert content and validate HCL syntax with
python-hcl2; run from the repo root:

```
python3 -m unittest discover -s emitters/terraform/tests
```

### `for_each` vs. explicit blocks (architecture §10)

Homogeneous resources (categories, customer groups, …) are emitted as a single
`for_each` block over a data map — so 400 categories stay one block and
`terraform plan` stays fast. Product types have a *heterogeneous* nested attribute
schema (enum values, set element types), so they are emitted as explicit generated
blocks; authoring cost is still zero because they are generated from the CCM.

## Still to come

- `commercetools_type` / `custom_object`, `commercetools_attribute_group`.
- Org / B2B: `business_unit_company` / `_division`, `associate_role`, `product_selection`.
- Fulfillment: `tax_category` (+ `_rate`), `shipping_zone` (+ `_rate`), `shipping_method`.
- `project_settings`.

## Design rule

## Design rule

**All commercetools/provider version specifics live here** — never in the analyzers
or the CCM. This is what isolates commercetools churn to one component (see the CT
version strategy in [`docs/architecture.md`](../../docs/architecture.md#versioning--commercetools-updates)).
