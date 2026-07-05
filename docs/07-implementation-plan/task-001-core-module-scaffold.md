# Task 001 — Core Module Scaffold

> Written to the `CLAUDE.md` §9 implementation-task structure (see
> [`../06-prompts/implementation-task-template.md`](../06-prompts/implementation-task-template.md)).
> This document is a **task specification only** — it does not itself
> create code, modules, views, controllers, security files, manifests,
> tests, or CI files. It is authorized by
> [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md)
> §6 as the **only** task this gate opens.

## Status

Authorized by limited core implementation gate, pending ChatGPT
acceptance/merge of this PR.

## Objective

Create the minimal installable `shopify_connector_core` module scaffold
and only the foundation needed for the six accepted core models.

## Allowed implementation files for the future coding PR

- `shopify_connector_core/__init__.py`
- `shopify_connector_core/__manifest__.py`
- `shopify_connector_core/models/__init__.py`
- `shopify_connector_core/models/shopify_connector_store.py`
- `shopify_connector_core/models/shopify_connector_store_settings.py`
- `shopify_connector_core/models/shopify_connector_location.py`
- `shopify_connector_core/models/shopify_connector_binding_mixin.py`
- `shopify_connector_core/models/shopify_connector_job.py`
- `shopify_connector_core/models/shopify_connector_job_log.py`
- `shopify_connector_core/security/ir.model.access.csv`
- `shopify_connector_core/security/shopify_connector_security.xml`
- test files only if the repository's Odoo test structure exists and can
  be followed safely.

## Forbidden implementation files

- any product/customer/order/inventory/fulfillment/accounting/refund/
  payout/multi-store module;
- any wizard XML;
- any menu/action/view XML except security groups if needed;
- any controller;
- any Shopify API client;
- any webhook;
- any credential/token/secret field;
- any cron data file;
- any data migration;
- any unrelated file.

## Required model scope

For each of the six accepted models —
`shopify.connector.store`, `shopify.connector.store.settings`,
`shopify.connector.location`, `shopify.connector.binding.mixin`,
`shopify.connector.job`, and `shopify.connector.job.log` — the accepted
[`AR-019`](../05-qa/architecture-review-log.md) /
[`core-naming-schema-planning.md`](./core-naming-schema-planning.md)
(§3, §4, §5, §6, §7, §8, §12) is the source of truth for names, fields,
and constraints. Field lists are not restated here: **the future coding
PR must implement only the AR-019-accepted field schema and constraints**
— no additional field, model, or mechanism may be introduced without a
separate architecture-review pass.

## Required safety constraints

- no credential fields;
- no external API calls;
- no webhooks;
- no UI;
- no domain sync logic;
- no delete of historical jobs/logs unless explicitly allowed by accepted
  design;
- idempotency and operation serialization fields must remain distinct.

## Acceptance criteria for future coding PR

- module scaffold exists and is installable;
- only allowed files changed;
- six accepted core models implemented;
- no credential/token/secret field exists;
- no Shopify API calls exist;
- no webhooks/controllers exist;
- no operator-facing UI exists;
- security groups/access exist only for accepted core scope;
- tests/manual checks pass;
- research-handoff updated;
- rollback notes included.

## Required tests for future coding PR

The future coding PR must include tests for:

- module install/import if test framework exists;
- core model creation where safe;
- required constraints;
- idempotency key uniqueness behavior if implemented in Task 001;
- operation scope uniqueness behavior if implemented in Task 001;
- access rights for core groups if test framework exists;
- no credential fields created.

If tests cannot be implemented due to repository limitations, the future
coding PR must explain why and include manual verification steps.

## Rollback notes

Rollback is removing the `shopify_connector_core` module scaffold PR
before any dependent module is built. Since this is the first module in
the dependency DAG and nothing depends on it yet, rollback is a single
revert of the coding PR's commit(s) with no downstream migration or data
cleanup required.

## Definition of done

The future coding PR is done only when ChatGPT reviews and accepts the
implementation against this task. Per
[`implementation-task-template.md`](../06-prompts/implementation-task-template.md)
§7: code + tests written and passing, lint/format clean;
[`pr-review-checklist.md`](../05-qa/pr-review-checklist.md) section C
satisfied; any shortcut logged in
[`technical-debt-register.md`](../05-qa/technical-debt-register.md);
modularity preserved and only allowed files changed; self-review
classified; handoff updated; quality gate confirmed. No second task may
start until ChatGPT reviews this one
([`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md)
§5).
