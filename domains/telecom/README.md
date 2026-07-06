# domains/telecom

The **telecom** domain pack — data and priors (not forked pipeline code) that prime
the analyzers and planner for telecom migrations.

> **Status: scaffold.** This directory will hold the telecom priors.

## What lives here (planned)

- **Expected entities** — what a telecom catalog should contain: rate plans,
  subscription/recurring products, device+plan bundles, SIM/provisioning.
- **Product-type priors** — standard shapes/attributes injected with
  `origin: domain-pack`:
  - `device` — color, storage, IMEI-related attributes.
  - `plan` — data allowance, billing cycle, contract term.
  - `bundle` / `accessory`.
- **Modeling conventions** — commercetools has no native subscription concept, so the
  pack encodes how recurring/subscription concepts are represented (product types +
  recurring-term attributes) so every telecom migration is consistent.
- **Decision heuristics** — common telecom ambiguities and their recommended resolutions.

## Rule

A domain pack must **not** branch the pipeline or add platform-specific code. Adding a
new vertical (e.g. `domains/manufacturing/`) is a new pack, not a new pipeline — see
[`docs/extending.md`](../../docs/extending.md).
