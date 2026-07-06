---
name: plan-migration-to-ct
description: Phase 2 of a commercetools migration. Read the Canonical Commerce Model (ccm.json) and produce the commercetools target design — mapping tables from CCM entities to commercetools resources, plus a decision report. Platform-agnostic; runs after any analyze-* phase.
user-invocable: true
---

# plan-migration-to-ct — Phase 2: plan the commercetools target

> **Status: scaffold.** Structure and contract defined; implementation pending.
> See [`docs/architecture.md`](../../docs/architecture.md) (§4).

## Purpose

Map the platform-neutral CCM onto concrete commercetools resources and produce a
reviewable plan. This is the **hub → target** step, reused by every source platform.

## Input

- `ccm.json` (validated against `ccm/schema/ccm.schema.json`).

## Outputs

- `mappings/ccm-to-ct.json` — every CCM entity → its commercetools resource + the
  target Terraform resource name (`labd/commercetools`).
- `mappings/decisions.md` — open decisions surfaced from the CCM plus any planning
  decisions (e.g. how a custom item-descriptor should be realized).

## Mapping reference (from the architecture doc)

`productTypes → commercetools_product_type`, `categories → commercetools_category`,
`customFieldTypes → commercetools_type`, `customerGroups → commercetools_customer_group`,
`taxCategories/zones/shippingMethods → commercetools_tax_category / _shipping_zone / _shipping_method`,
`channels/stores → commercetools_channel / _store`, `productSelections → commercetools_product_selection`,
`businessUnits → commercetools_business_unit_company|_division`,
`associateRoles → commercetools_associate_role`, `states → commercetools_state`,
`customObjects → commercetools_custom_object`.

## Steps (to implement)

1. Load and validate `ccm.json`.
2. For each entity, resolve the target commercetools resource (respecting the pinned
   provider version from `meta`).
3. Emit `mappings/ccm-to-ct.json` and the decision report.
4. Suggest `/migration-report --phase plan` to review, then `/emit-terraform`.
