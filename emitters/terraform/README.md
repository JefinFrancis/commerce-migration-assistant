# emitters/terraform

Templates and module structure used by the `emit-terraform` skill to render the
[Canonical Commerce Model](../../ccm/schema/ccm.schema.json) into Terraform (HCL)
for the [`labd/commercetools`](https://registry.terraform.io/providers/labd/commercetools/latest/docs)
provider.

> **Status: scaffold.** This directory will hold the CCM → HCL templates.

## What lives here (planned)

HCL templates, one per resource family, plus the pinned provider block:

- `versions.tf.tmpl` — `required_providers { commercetools = { version = ... } }`.
- `product-types.tf.tmpl` — `commercetools_product_type` (+ `commercetools_attribute_group`).
- `taxonomy.tf.tmpl` — `commercetools_category`.
- `custom-types.tf.tmpl` — `commercetools_type`, `commercetools_custom_object`.
- `org.tf.tmpl` — `commercetools_business_unit_company` / `_division`,
  `commercetools_associate_role`, `commercetools_product_selection`.
- `fulfillment.tf.tmpl` — `commercetools_tax_category` (+ `_rate`),
  `commercetools_shipping_zone` (+ `_rate`), `commercetools_shipping_method`.
- `project-settings.tf.tmpl` — `commercetools_project_settings`.

## Design rule

**All commercetools/provider version specifics live here** — never in the analyzers
or the CCM. This is what isolates commercetools churn to one component (see the CT
version strategy in [`docs/architecture.md`](../../docs/architecture.md#versioning--commercetools-updates)).
