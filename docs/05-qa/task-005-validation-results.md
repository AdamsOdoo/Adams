# Task 005 — Validation Results (Connection Lifecycle Actions)

## Summary

**ACCEPTED.** PR #121 ("Task 005 connection lifecycle actions") merged into
`Shopify-connector` on 2026-07-08, merge commit
`8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82` (PR #121 head commit before
merge: `f2ce29c0422258f92877f6464b1746455d28dcb5`). Before merge, the PR's
final head commit was live-validated against a real Odoo 19 + PostgreSQL
registry on Odoo.sh: both the focused `TestConnectionLifecycle` test class
and the full `shopify_connector_core` automated test suite ran with **zero
failures and zero errors**. This document is the live-validation evidence
record for Task 005's scope, mirroring the format of
[`task-004-validation-results.md`](./task-004-validation-results.md).

## Scope validated

The connection-lifecycle substrate for `shopify_connector_core`, exactly as
implemented and merged in PR #121:

- `action_activate()` — accepted check order: `credential_present` →
  credential row exists → `credential_last_verified_at` truthy →
  `last_test_connection_result == 'pass'` → `last_readiness_result in
  ('pass', 'warning')` → `last_readiness_at` truthy and not older than
  `credential_last_verified_at`. Raises `UserError` before any write on any
  failure; no audit job on rejection; no Shopify call; no readiness run.
- `action_disconnect()` — clears the stored credential via the existing
  Task 002 credential service, cancels non-terminal business jobs
  (preserving history), moves the store to `disconnected`.
- `action_reconnect()` — re-enters credential flow, re-invokes the existing
  Task 003 test-connection and Task 004 readiness substrate, resumes.
- `action_mark_reconnect_needed()` — explicit authentication-failure-signal
  transition to `reconnect_needed`.
- **Business job enqueue-time gating** and **execution-time gating**: jobs
  may only be created/run when the owning store is in the `connected` state.
- **Credential-service state invalidation**, added during PR #121's own
  runtime-fix revisions (see "Earlier failures and final fixes" below):
  - `action_set_token()` / `action_replace_token()` on a `connected` store
    also move it to `reconnect_needed`.
  - `action_clear_token()` on a `connected` or `reconnect_needed` store also
    moves it to `disconnected`.
- Lifecycle and credential-service tests: `test_connection_lifecycle.py`
  and `test_credential_service.py`.

## Environment

- **Runtime:** Odoo.sh branch shell (live Odoo 19 + PostgreSQL registry,
  not a local or simulated environment).
- **Odoo version:** Odoo Server 19.0.
- **Commit under test:** PR #121 head, `f2ce29c0422258f92877f6464b1746455d28dcb5`
  — the exact commit subsequently merged as
  `8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82`.

## Commands used

Full `shopify_connector_core` module suite:

```
odoo-bin -d <db> -u shopify_connector_core \
  --test-enable --test-tags /shopify_connector_core \
  --stop-after-init --log-level=test
```

Focused `TestConnectionLifecycle` class:

```
odoo-bin -d <db> -u shopify_connector_core \
  --test-enable --test-tags /shopify_connector_core:TestConnectionLifecycle \
  --stop-after-init --log-level=test
```

## Results (final, pre-merge, PR #121 head)

Focused `TestConnectionLifecycle` run:

```
0 failed, 0 error(s) of 41 tests
```

Full module run:

```
0 failed, 0 error(s) of 123 tests
```

## Earlier failures and final fixes

Odoo.sh runtime validation of PR #121 was not clean on the first attempt.
Two rounds of real-runtime failures were found and fixed before the head
commit above was reached and merged — both are restated here as the
authoritative closure-level record (full narrative detail is preserved in
the dated PR #121 revision entries in
[`research-handoff.md`](../01-research/research-handoff.md)):

1. **5 activation errors from a brittle `credential.write_date` freshness
   guard.** `action_activate()`'s original freshness check compared
   `credential.write_date > credential_last_verified_at` and raised on
   legitimately fresh evidence under real Odoo.sh write-timing behavior —
   failing `test_activate_succeeds_with_pass_and_pass`,
   `test_activate_succeeds_with_pass_and_warning`, and all three
   `test_activate_rejects_stale_evidence_after_*` tests. This defect passed
   `py_compile` and every static/adversarial review across three prior PR
   revisions; only live Odoo.sh execution exposed it.
2. **1 activation failure from credential replacement leaving the store
   `connected`.** `test_activate_rejects_stale_evidence_after_credential_replace`
   failed (`'connected' == 'connected'`) because `action_replace_token()`
   cleared `credential_last_verified_at` (correctly invalidating the
   verification evidence) but left `store.state` unchanged at `connected` —
   a real product risk, since business-job gating keys off
   `state == 'connected'`.

**Final fix applied** (both issues, closing the PR #121 revision cycle):

- Removed the `credential.write_date` freshness-comparison guard entirely.
- `action_set_token()` now clears `credential_last_verified_at` on every
  token set/update — including updating an existing credential row —
  mirroring `action_replace_token()`'s existing behavior.
- Added a readiness-freshness guard to `action_activate()`:
  `last_readiness_at` must be truthy and not older than
  `credential_last_verified_at`.
- Added credential-service state invalidation: `action_set_token()` /
  `action_replace_token()` move a `connected` store to `reconnect_needed`;
  `action_clear_token()` moves a `connected` or `reconnect_needed` store to
  `disconnected`.

## What this does not prove

- **Does not prove VAL-B2.** No live Shopify Admin API connection was made
  or attempted by this validation or by Task 005's implementation — no
  claim is made about a pass. **VAL-B2 remains deferred, not passed**
  (`../04-decisions/DEC-021-val-b2-deferral-for-task-004.md`).
- **Does not resolve MBQ-05.** The scalable many-unrelated-customer
  distribution/auth architecture remains undecided. **MBQ-05 remains
  partially routed / open**
  (`../03-architecture/master-blueprint-open-questions.md` MBQ-05 row;
  `../04-decisions/DEC-023-token-acquisition-and-val-b2.md`).
- **Does not close TD-002.** The `read_fulfillments` readiness-scope
  correctness concern is unaffected by Task 005. **TD-002 remains Open**
  (`./technical-debt-register.md` TD-002 row).
- **No OAuth implemented.**
- **No setup wizard implemented.**
- **No UI implemented** (no views, menus, actions, wizards, or controllers
  of any kind).
- **No product/customer/order/inventory/fulfillment/domain sync
  implemented.**
- **No security/ACL change.** The `perm_create` store/settings ACL posture
  decided in DEC-022 (remains closed) is unchanged by this implementation.

## Final acceptance decision

**Task 005 (connection lifecycle actions) is ACCEPTED**, scoped exactly to
what PR #121 implemented:

- PR #121 merged into `Shopify-connector` — merge commit
  `8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82`.
- Live Odoo.sh validation passed at the merged head commit — focused
  `TestConnectionLifecycle` (`0 failed, 0 error(s) of 41 tests`) and the
  full `shopify_connector_core` module suite
  (`0 failed, 0 error(s) of 123 tests`), both against a real Odoo 19 +
  PostgreSQL registry.
- This acceptance proves the Task 005 lifecycle substrate and its tests
  pass in Odoo 19 — it does **not** prove, and does not claim, that VAL-B2
  has passed, that MBQ-05 is resolved, or that TD-002 is closed.

**Next step:** control room (ChatGPT) reviews this closure package and
decides the next gated task — see
[`DEC-024-task-005-closure.md`](../04-decisions/DEC-024-task-005-closure.md)
and [`research-handoff.md`](../01-research/research-handoff.md).
