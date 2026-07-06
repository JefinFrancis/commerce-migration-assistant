---
name: emit-terraform
description: Phase 3 of a commercetools migration. Render the planned commercetools target design into Terraform (HCL) modules using the labd/commercetools provider — the directly-importable artifact you run with terraform apply. Runs after /plan-migration-to-ct.
user-invocable: true
---

# emit-terraform — Phase 3: emit Terraform

> **Status: scaffold.** Structure and contract defined; implementation pending.
> See [`docs/architecture.md`](../../docs/architecture.md) (§8) and
> [`emitters/terraform/`](../../emitters/terraform/).

## Purpose

Generate reproducible infrastructure-as-code that stands up the commercetools
project **schema** (structure only — no records in v1).

## Inputs

- `ccm.json` and `mappings/ccm-to-ct.json`.
- The pinned provider version from `meta.providerVersion`.

## Outputs (`terraform/`)

HCL modules grouped by resource family:

- `versions.tf` — pinned `required_providers { commercetools = { ... } }`.
- `product-types.tf` — product types (+ attribute groups).
- `taxonomy.tf` — categories.
- `custom-types.tf` — Types (custom fields) and custom objects.
- `org.tf` — business units, associate roles, product selections (B2B).
- `fulfillment.tf` — tax categories, zones, shipping methods.
- `project-settings.tf` — project-level configuration.

## Implementation

The emitter is implemented in [`emitters/terraform/emit.py`](../../emitters/terraform/):

```
python3 emitters/terraform/emit.py <ccm.json> --out-dir terraform/
```

Currently renders `versions.tf` (pinned provider), `product-types.tf` (explicit
generated blocks), and `categories.tf` / `customer-groups.tf` (via `for_each`).
Homogeneous families use `for_each`; product types use explicit blocks (see the
emitter README). Remaining families (custom types, org/B2B, fulfillment,
project-settings) are still to come.

Tests: `python3 -m unittest discover -s emitters/terraform/tests` (content +
HCL-syntax validation).

## Steps (to implement / extend)

1. Load `ccm.json` (+ `mappings/ccm-to-ct.json` once the planner produces it).
2. Render each resource family via `emit.py`.
3. Write the pinned `versions.tf`.
4. Tell the user to run `terraform init && terraform plan` in `terraform/`.

## Notes

- All commercetools/provider **version specifics live here**, never in the analyzers
  or the CCM (see the CT version strategy in the architecture doc).
- Credentials are supplied via environment variables at apply time — never written
  into the workspace.
