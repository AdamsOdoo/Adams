# Task 004 — Validation Results (Readiness-Check Substrate)

## Summary

**ACCEPTED.** PR #115 ("Task 004 readiness-check substrate implementation")
merged into `Shopify-connector` on 2026-07-08, merge commit
`4145faf69ae6c1d541006890fc2b997fe4c07238`. Before merge, the PR's exact
head commit (`ddecd9d28ac543145e9b4ec303e84e2afbbd2b15`) was live-validated
against a real Odoo 19 + PostgreSQL registry on Odoo.sh: both the full
`shopify_connector_core` automated test suite and the focused Task 004
`TestReadinessCheck` test class ran with **zero failures and zero
errors**. TD-001 (the pre-existing `core_readiness_check` idempotency
collision defect) is resolved by this same PR, proven by its own
regression test running live in that same validation pass. This document
is the live-validation evidence record required by
[`task-004-manual-validation-checklist.md`](./task-004-manual-validation-checklist.md)
and [`task-004-quality-gates.md`](./task-004-quality-gates.md) before
Task 004 acceptance.

## Scope validated

The readiness-check substrate for `shopify_connector_core`, exactly as
implemented in PR #115:

- `shopify.connector.readiness.check` (`models.AbstractModel`) — the
  check registry/service, its domain-extension registration seam
  (`_get_checks`), fail-closed aggregation (`_aggregate`), and the public
  `run_for_store(store)` entry point.
- The nine MBQ-06/DEC-018 essential checks: credential/test-connection
  stored evidence, required MVP scopes, API-version health, store
  identity, `web.base.url` HTTPS reachability, domain-flag enablement,
  and three registered-pending-slot checks (webhook HMAC, mapped
  Location, cron/queue health — see "Remaining deferrals" below).
- The TD-001 fix: a fresh UUID4 `payload_hash` nonce on
  `core_readiness_check` job creation.
- The full pre-existing `shopify_connector_core` test suite
  (`test_api_client`, `test_credential_access`, `test_credential_service`,
  `test_job_log_system_append`, `test_redaction`, `test_test_connection`),
  confirmed to still pass unchanged alongside the new tests.

## Environment

- **Runtime:** Odoo.sh branch shell (live Odoo 19 + PostgreSQL registry,
  not a local or simulated environment).
- **Odoo version:** Odoo Server 19.0.
- **Branch database:**
  `adamsmen-claude-task-004-readiness-substrate-me21qg-34601850`.
- **Commit under test (confirmed in Odoo.sh before running):**
  `ddecd9d28ac543145e9b4ec303e84e2afbbd2b15` — the exact PR #115 head SHA
  that was subsequently merged as `4145faf69ae6c1d541006890fc2b997fe4c07238`.

## Commands run

Full `shopify_connector_core` module suite:

```
odoo-bin -d adamsmen-claude-task-004-readiness-substrate-me21qg-34601850 \
  -u shopify_connector_core \
  --test-enable --test-tags /shopify_connector_core \
  --stop-after-init --log-level=test
```

Focused Task 004 test class:

```
odoo-bin -d adamsmen-claude-task-004-readiness-substrate-me21qg-34601850 \
  -u shopify_connector_core \
  --test-enable --test-tags /shopify_connector_core:TestReadinessCheck \
  --stop-after-init --log-level=test
```

## Results

Full module run:

```
shopify_connector_core: 90 tests 0.73s 1411 queries
0 failed, 0 error(s) of 78 tests
```

Focused `TestReadinessCheck` run:

```
shopify_connector_core: 33 tests 0.10s 218 queries
0 failed, 0 error(s) of 31 tests
```

A grep pass over the run logs for the words "fail"/"error" matched only
test method *names* that happen to contain those words (e.g.
`test_credential_check_fails_on_stored_failure`,
`test_no_secret_leakage_in_job_or_log`) — the final Odoo result lines for
both runs are clean: zero failures, zero errors.

## Evidence interpretation

- The module installs/upgrades cleanly on Odoo 19 with the new
  `shopify.connector.readiness.check` model present — no registry-load
  error, no schema drift to any pre-existing Task 001–003 model.
- All 31 `TestReadinessCheck` test methods passed live, including: the
  TD-001 regression test; the `core_test_connection` unchanged-behavior
  assertion; the fail-closed aggregation unit tests; the required-MVP-
  scope and domain-flag-enablement corrections from the ChatGPT-review
  revision; the payload-snapshot/summary-mirror tests; the
  domain-extension-seam test; the read-only-guarantee tests (including
  the AST-level structural scan); and the redaction/no-secret-leakage
  test.
- The full-module run (78 tests, a superset including the six
  pre-existing test files) shows the new substrate did not regress any
  previously-accepted Task 001–003 behavior — in particular,
  `test_source_level_two_sudo_sites_total` still confirms the codebase
  carries exactly two `sudo()` call sites, unchanged.
- This is a real `TransactionCase` run against a live Odoo 19 registry
  and PostgreSQL database — not a static/dry-run/`py_compile`-only
  check. It supersedes the local sessions' dry-run harness and
  `py_compile`-only evidence recorded in PR #115 itself.

## What this does not prove

- **Does not prove VAL-B2.** No live Shopify Admin API connection was
  made or attempted by this validation — the readiness substrate is
  deliberately read-only against stored evidence only (per DEC-021 §4),
  and this test run does not touch Shopify at all.
- **Does not prove customer-facing readiness.** A fresh/current-state
  store still computes overall readiness `fail` by design (see
  "Remaining deferrals" below) — this validation proves the *substrate
  and its tests* behave correctly on Odoo 19, not that a merchant could
  use this to confirm their store is ready to sync.
- **Does not prove production-scale or concurrency behavior.** The test
  database is a disposable Odoo.sh branch build; no load, concurrency, or
  production-data testing was performed.
- **Does not resolve MBQ-05** or any other open architecture question
  beyond what PR #115 itself already resolved (MBQ-06's essential/warning
  split, already accepted via DEC-018 prior to this task).
- **Does not authorize Task 005** or any further implementation — this
  document records validation and acceptance of Task 004's own scope
  only.

## Remaining deferrals / non-claims

- **VAL-B2 remains deferred, not passed.** The credential/test-connection
  check reports `not_proven` whenever `store.last_test_connection_result`
  has never recorded a pass — it never asserts "connected"/"pass" from
  absent evidence.
- **MBQ-05 remains deferred for Task 004 only, not resolved** as a final
  token-acquisition strategy.
- **No OAuth implemented.**
- **No setup wizard implemented.**
- **No UI implemented** (no views, menus, actions, wizards, or
  controllers of any kind).
- **No lifecycle actions implemented** (no activate/disconnect/reconnect
  code).
- **No product/customer/order/inventory/fulfillment/domain sync
  implemented.**
- **No Shopify API call is made by the readiness substrate** — every
  check reads only already-stored core evidence or `ir.config_parameter`;
  confirmed both behaviorally
  (`test_readiness_check_never_calls_shopify_api_client`) and
  structurally (the AST read-only scanner), and this live run exercised
  both tests successfully.
- **No customer-facing readiness pass is claimed.** Three of the nine
  essential checks remain **registered pending slots by design**, with no
  real signal to compute yet:
  - webhook HMAC (no webhook implementation exists)
  - mapped Location (Location↔domain mapping is owned by a future
    inventory domain module)
  - cron/queue health (no cron/queue implementation exists)

  Because these are essential-tier and fail-closed aggregation never
  infers a pass from an unproven/uncomputed state, **a
  fresh/current-state store may still compute overall readiness `fail`
  by design**, until the future tasks that implement webhooks, domain
  Location mapping, and cron/queue health give these checks a real
  signal. This is intentional, not a defect — it is the correct
  behavior under DEC-021 §4's "no customer-facing readiness pass from
  absent evidence" rule.

## Final acceptance decision

**Task 004 (readiness-check substrate) is ACCEPTED**, scoped exactly to
what PR #115 implemented:

- PR #115 merged into `Shopify-connector` — merge commit
  `4145faf69ae6c1d541006890fc2b997fe4c07238`.
- Live Odoo.sh validation passed — full module suite
  (`0 failed, 0 error(s) of 78 tests`) and the focused
  `TestReadinessCheck` class (`0 failed, 0 error(s) of 31 tests`), both
  against a real Odoo 19 + PostgreSQL registry.
- **TD-001 is resolved** by this implementation and this validation —
  see [`technical-debt-register.md`](./technical-debt-register.md) for
  the resolution note.
- This acceptance proves the Task 004 readiness-check substrate and its
  tests pass in Odoo 19 — it does **not** prove, and does not claim,
  that the connector as a whole is customer-ready, that VAL-B2 has
  passed, or that MBQ-05 is resolved.

**Next step:** control room (ChatGPT) decides the next gated task —
Task 005 planning, or a small documentation/governance gate before any
setup-wizard/OAuth work — per
[`../01-research/research-handoff.md`](../01-research/research-handoff.md).
