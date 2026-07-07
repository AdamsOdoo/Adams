# Task 003 — Manual Validation Checklist (Live Odoo 19 + PostgreSQL + Shopify Development Store)

## Status

**Package/template only — no live validation has been performed.** This
document does not claim, imply, or mark any step as passed. It is the
checklist a reviewer with a live Odoo 19 + PostgreSQL environment and a
Shopify **development** store must execute to close the runtime-verification
gap left open by PR #101. Pair it with
[`task-003-validation-results.md`](./task-003-validation-results.md), which is
the blank results template to fill in while executing these steps.

This session is a **QA-closure session, not a coding session** — it mirrors
the precedent set by
[`task-001-core-runtime-readiness.md`](./task-001-core-runtime-readiness.md)
for Task 001. No addon code, tests, security file, manifest, migration, or CI
file is created or modified by this document or its companion files.

## Verified starting state

- **PR #101** — "Task 003 API client and test connection" — merged into
  `Shopify-connector`. Merge commit `e27f10e55f3504d1a9b8871a207b3d9762a3c783`.
- Per the PR #101 body and `docs/01-research/research-handoff.md`'s current
  entry: all 32 new tests (19 in `test_api_client.py`, 9 in
  `test_test_connection.py`, 4 in `test_job_log_system_append.py`) plus the
  full pre-existing suite were **written and `py_compile`/`pyflakes`
  re-validated, not executed** — there is no Odoo runtime, PostgreSQL, or CI
  in this repository (unchanged since Task 001A/Task 002).
- Manual validation against a live Odoo 19 instance + development store was
  explicitly **not performed** in PR #101 and was left as an open item — see
  the final implementation prompt's own
  [§Manual validation](../07-implementation-plan/task-003-final-implementation-prompt.md#manual-validation-live-odoo-19--postgresql-with-a-development-store--never-a-production-shop)
  and the pre-implementation checklist's
  [§B "Manual validation performed and recorded honestly"](./task-003-pre-implementation-review-checklist.md)
  gate item, both of which this checklist operationalizes into concrete,
  repeatable steps.
- [`TD-001`](./technical-debt-register.md) — the `core_readiness_check`
  target-less idempotency-collision defect — remains **open** and is
  explicitly **not** fixed by Task 003 or by this validation session.

## Why this exists

Task 003 added a live, outbound (read-only) Shopify Admin GraphQL call —
the first of its kind in this project. Every prior task's static checks
(Python compile, manifest/XML parse, grep sweeps, `py_compile`d tests) reason
about the code correctly but cannot observe: whether the module actually
installs against a real Odoo 19 registry; whether Shopify's actual HTTP/error
behavior matches the fixed 16-class mapping this code assumes; whether the
redaction guarantee holds under a real ORM write; or whether the two
`sudo()`-gated write paths behave as designed under real ACL enforcement.
Per `CLAUDE.md` §9 ("Definition of done") and the final implementation
prompt's own PR-requirements, this manual validation is **mandatory** before
any further feature development (Task 004+) begins.

## Preconditions before starting

- [ ] A live Odoo 19 instance with PostgreSQL is available, isolated from any
      production data.
- [ ] A **Shopify development store** (Shopify Partner test store) is
      available. **A production/live Shopify store must never be used for any
      step below.**
- [ ] The tester has read: this checklist, `task-003-validation-results.md`,
      `docs/07-implementation-plan/task-003-final-implementation-prompt.md`,
      `docs/05-qa/credential-security-redaction-review-checklist.md`, and
      `docs/05-qa/technical-debt-register.md` (`TD-001`).
- [ ] The tester records environment details (Odoo build, database name,
      module version, Shopify API version, dev-store handle, token type) in
      `task-003-validation-results.md` **before** running any test.

---

## A. Module install/upgrade and registry checks

- **VAL-A1 — Clean install.** Install `shopify_connector_core` on a clean
  Odoo 19 database (or upgrade from the pre-Task-003 `19.0.1.1.0` state to
  `19.0.1.2.0` if a Task 002-era database is available).
  **Expected:** module installs/upgrades without a manifest, security, or
  model registry error; no traceback.
- **VAL-A2 — Model registry loads.** Query `ir.model` for
  `shopify.connector.api.client`, `shopify.connector.store`,
  `shopify.connector.job`, `shopify.connector.job.log`.
  **Expected:** `shopify.connector.api.client` is present as a registered
  model with **no table** (`AbstractModel` — confirm no row for it exists in
  `information_schema.tables`, e.g. no `shopify_connector_api_client` table);
  the other three models load with their existing tables intact (no schema
  drift from Task 001/002).
- **VAL-A3 — Three `job_type` values visible in the ORM.** Query
  `ir.model.fields.selection` (or `fields_get('job_type')['selection']` on
  `shopify.connector.job`) via the ORM/shell — **not** via any menu/view.
  **Expected:** exactly three values present:
  `core_readiness_check`, `core_manual_maintenance`, `core_test_connection`
  — no fourth value, no removed value.
- **VAL-A4 — No XML/menu/action/wizard/controller/cron introduced.**
  Inspect the installed module's `ir.ui.menu`, `ir.actions.act_window`,
  `ir.actions.server`, `ir.cron`, and `ir.model.data` records with
  `module='shopify_connector_core'`.
  **Expected:** zero rows of any of these kinds — Task 003 added no XML file
  of any kind (`ir.model.data` should show only the pre-existing Task
  001/002 security records, none newly added by this task).

---

## B. Credential / test-connection behavioral tests

Use only dummy/development-store credentials. Never a production token.

- **VAL-B1 — Invalid-token test.** Using Task 002's credential service, set
  a syntactically-plausible but invalid token (e.g. a revoked or
  never-issued development-store token) on a test store, then call
  `action_test_connection()`.
  **Expected:** the job fails; `error_class='shopify_permission_scope_auth'`;
  the store's `last_test_connection_result='fail'` with a business-friendly
  reason ("Your access token appears invalid or was revoked — replace it.");
  `credential_state` flips to `'invalid'` on the store's credential record.
  **Record the actual observed HTTP status** for this condition (401 is
  assumed but unconfirmed per the final prompt's open questions) in the
  results template.
- **VAL-B2 — Valid development-store token test.** Set a genuine
  development-store access token, then call `action_test_connection()`.
  **Expected:** the job succeeds (`state='succeeded'`);
  `last_test_connection_result='pass'`; `credential_last_verified_at`,
  `granted_scopes` (valid JSON array of scope handles), and
  `granted_scopes_checked_at` are all populated; `last_test_connection_reason`
  is cleared (`False`).
- **VAL-B3 — Repeat test-connection run (idempotency/collision guard).**
  Immediately call `action_test_connection()` a second time on the **same**
  store (either two passing runs, or a pass then a fail, in either order).
  **Expected:** the second call also succeeds in creating its `job` row —
  **no** `store_idempotency_key_uniq` constraint violation — because each
  run's `payload_hash` is a fresh UUID4 nonce, not a fixed value. This is the
  live proof of test item 26 in the final implementation prompt (proven only
  by written/unexecuted tests in PR #101 until this step runs).
- **VAL-B4 — Identity-mismatch behavior.** Point a store record's
  `shop_domain` at a domain that differs from the Shopify shop actually
  reachable with the configured token (e.g. reuse a valid token from a
  *different* development store than the one named in `shop_domain`), then
  call `action_test_connection()`.
  **Expected:** the job fails with `error_class='odoo_validation_configuration'`
  and reason "The connected Shopify store does not match this store's
  configured domain — check the domain and reconnect."; **`credential_state`
  is left untouched** (this is a configuration mismatch, not a credential
  problem).
- **VAL-B5 — Shop-state failure behavior (if reproducible).** If the
  development store (or a Partner-provided test fixture) can be put into a
  frozen/locked/fraudulent-flagged/inactive state, call
  `action_test_connection()` against it for each reproducible condition.
  **Expected:** each maps to `error_class='shopify_permission_scope_auth'`
  with its own distinct reason string (frozen → billing/payment copy; locked
  → "locked by Shopify"; fraudulent → "flagged as fraudulent";
  `SHOP_INACTIVE` → "This store is inactive."); **`credential_state` is not
  changed** in any of these four cases. **If none of these states are
  reproducible in the available development-store tooling, record this
  explicitly as "not reproducible" — do not assert the behavior as confirmed
  without having observed it.**
- **VAL-B6 — `credential_state` flips only on a genuine token-invalid
  signal.** Cross-check VAL-B1 (must flip) against VAL-B4 and VAL-B5 (must
  **not** flip). Confirm no test above where `credential_state` changed for
  a shop-account-state condition, and that it changed only for the
  401/`ACCESS_DENIED`-class failure.
- **VAL-B7 — Version fall-forward warning behavior (if reproducible).** If
  the store's configured `api_version` can be set to an older version than
  what the development store's Shopify instance actually serves (triggering
  a `X-Shopify-API-Version` response-header mismatch), run
  `action_test_connection()` and confirm it still completes as a **pass**.
  **Expected:** `last_test_connection_result` remains `'pass'`;
  `api_health_state='degraded'` and a redacted `api_health_reason` naming
  both the served and configured versions are written — a warning, not a
  failure. **If not reproducible in the available development-store
  tooling** (Shopify may auto-serve the pinned version), record this
  explicitly as "not reproducible."

---

## C. Redaction and access/security checks

- **VAL-C1 — Token redaction across every persisted surface.** After VAL-B1
  and VAL-B2 (both used a real, distinct dummy/dev token), grep:
  - the PostgreSQL database (`store`, `store.credential`, `job`, `job.log`
    tables/columns) for the exact token string used in either run,
  - the Odoo server log file(s) for the same string, at every log level
    including DEBUG.
  **Expected:** **zero hits** in either location, for either token.
- **VAL-C2 — `job.log` direct-create vs `_system_append` path (ACL check).**
  As a non-Admin user who holds `perm_read=1` but **not** `perm_create` on
  `shopify.connector.job.log` (e.g. an Operator/Auditor role per the Task
  001/002 ACL rows): (a) attempt
  `self.env['shopify.connector.job.log'].create({...})` directly —
  **expected: `AccessError`**, proving the ACL itself was not widened; (b)
  as the same user, trigger a code path that calls `_system_append`
  indirectly (e.g. by calling `action_test_connection()` if that user's role
  can reach it) — **expected: the log row is created**, proving the
  elevation inside `_system_append`'s `sudo()` — not a widened ACL — is what
  makes system-appended logging work.
- **VAL-C3 — Exactly two `sudo()` sites, live-confirmed.** Cross-check (this
  is a static/source check, not a runtime behavior, but worth re-confirming
  against the exact installed module version) that the installed
  `shopify_connector_core` module contains exactly two `sudo()` call sites:
  the pre-existing Task 002 `_get_access_token`, and the new
  `_system_append`.

---

## D. Read-only / no-side-effect guarantee

- **VAL-D1 — No Shopify-side mutation.** After every test-connection run
  above (pass and fail), inspect the Shopify development store's admin
  (Orders, Products, Customers, Inventory, Fulfillment, Settings →
  Notifications/Webhooks) for any new or changed record.
  **Expected:** **zero** changes of any kind; **zero** webhooks registered
  for the store at any point in this session.
- **VAL-D2 — No Odoo-side domain mutation.** Confirm no
  product/customer/order/inventory/fulfillment record on the Odoo side was
  created or modified by any step above (this task's scope never touches
  domain models — confirm the negative).

---

## E. Exact job/log row accounting

- **VAL-E1 — Pass-path row accounting.** For a single passing
  `action_test_connection()` run (VAL-B2): confirm exactly **one** `job`
  row is created (`job_type='core_test_connection'`,
  `job_source='setup_readiness_check'`, `state='succeeded'`) and exactly
  **two** `job.log` rows exist for that job: one `event_type='attempt'` row
  logged at creation ("Test connection attempt started.",
  `to_state` unset/`from_state` unset since it's the first row) and one
  `event_type='attempt'` row at completion (`from_state='running'`,
  `to_state='succeeded'`, message mentioning the shop name).
- **VAL-E2 — Fail-path row accounting.** For a single failing run (VAL-B1,
  VAL-B4, or VAL-B5): confirm exactly **one** `job` row
  (`state='failed_final'`, `error_class` set to the mapped class) and
  exactly **two** `job.log` rows: the same attempt-started row, and an
  attempt row with `from_state='running'`, `to_state='failed_final'`, and a
  redacted `message`/`technical_detail`.
- **VAL-E3 — No extra/missing rows.** Confirm no third `job.log` row, no
  orphaned `job` row without a matching `job.log` row, across every run
  performed in this session.

---

## F. `core_readiness_check` / TD-001 regression check

- **VAL-F1 — `core_readiness_check` remains unfixed.** Using a bare
  `create()` (the schema available before Task 003), create a
  `core_readiness_check` job for a store, then attempt to create a
  **second** `core_readiness_check` job for the **same** store.
  **Expected:** the second creation **still collides** on
  `store_idempotency_key_uniq` (an empty/falsy `payload_hash` on both
  attempts yields an identical `idempotency_key`). This is the live proof
  that Task 003 did not silently fix `core_readiness_check`'s defect —
  **TD-001 must remain open** in `technical-debt-register.md` after this
  session; this checklist does not close it, propose a fix for it, or start
  any follow-up task for it.

---

## G. Empirical open-questions capture

Per the final implementation prompt's own §Manual validation step 5, record
— as **observed facts**, not assumptions — in `task-003-validation-results.md`:

- **VAL-G1** — The actual HTTP status Shopify returns for an invalid/revoked
  access token (401 is assumed in code but was never empirically confirmed).
- **VAL-G2** — The actual `THROTTLED` response body shape, if a 429/throttle
  condition was reproducible.
- **VAL-G3** — Whether the `shop { id name myshopifyDomain }` /
  `currentAppInstallation { accessScopes { handle } }` query needed any
  specific OAuth scope to succeed on the development store used.
- **VAL-G4** — The actual missing-scope error shape, if reproducible.

Each must be recorded as either an observed answer (with the raw
response/status captured as evidence) or explicitly marked **"not
reproducible in this session"** — never asserted as confirmed without having
been observed, per `CLAUDE.md` §8's claim-classification rule (these are
**Facts** once observed, not before).

---

## Explicit exclusions for this validation session

- No addon code, test file, security file, manifest, XML, or migration is
  created or modified by executing this checklist.
- No bug found during validation is fixed in this session — defects are
  **recorded** in `task-003-validation-results.md` and, if accepted as
  technical debt, routed to `technical-debt-register.md` by a **future**,
  separately scoped session.
- No Task 004 (or any next feature) work starts as a result of this
  checklist, regardless of outcome.
- No CI/workflow file is created to automate any of the above.
- No production Shopify store is used for any step.
- No Shopify write/mutation/webhook of any kind is performed — every step
  above uses only the existing, read-only `action_test_connection()` entry
  point.

## Acceptance / non-acceptance

This checklist, on its own, **proves nothing** — it is not "passed" or
"failed" until every applicable step (VAL-A1…VAL-G4) has actually been
executed against a live environment and recorded in
[`task-003-validation-results.md`](./task-003-validation-results.md), which
carries the actual go/no-go recommendation once filled in.
