# Odoo 19 Green-Gate Failures — `shopify_connector_core` hotfix

**Date:** 2026-07-07
**Scope:** `addons/shopify_connector_core/models/shopify_connector_job_log.py`
plus `test_credential_access.py`, `test_credential_service.py`,
`test_job_log_system_append.py`, `test_test_connection.py`. No Task 004 /
domain / UI / controller / webhook / cron / Shopify API-client-behavior
work. This is a runtime-stabilization hotfix only.
**Trigger:** After PR #105 (merge commit `f915211`, removed `required=True`
from `shopify.connector.job.idempotency_key`) merged into
`Shopify-connector`, live validation was re-run against a live Odoo 19 +
PostgreSQL instance. The run is still failing:

```
1 failed, 4 error(s) of 39 tests
```

Odoo halted the run again after its max-failed-tests threshold, so
additional failures beyond the five recorded below may still be hidden.

---

## 1. Latest live run summary

| Metric | Value |
| --- | --- |
| Total tests loaded | 39 |
| Failed | 1 |
| Errors | 4 |
| Halt reason | Odoo's max-failed-tests threshold reached; run stopped before confirming every remaining test |

## 2. Every current failure/error — root cause and classification

| # | Test | Failure kind | Root cause | Production or test-expectation? |
| --- | --- | --- | --- | --- |
| 1 | `test_credential_access.TestCredentialAccess.test_non_admin_roles_denied_all_crud_and_search` | Failure at the `self.assertTrue(...)` `fields_get()`-disjoint assertion | **Test expectation.** `fields_get()` is a schema call in Odoo — it is not gated by `ir.model.access` CRUD rows, only by each field's own `groups=` attribute. The prior assertion (added in the PR #105 hotfix) still treated the *absence of certain field names from `fields_get()`* as proof that a role with zero ACL rows on the model cannot reach the data. That premise doesn't hold in Odoo 19 for fields with no `groups=` attribute of their own (`store_id`, `token_variant`, `credential_state`) — the schema call may legitimately return them regardless of model ACL. This is not a security regression: the five actual-operation assertions in the same test (`search`/`create`/`read`/`write`/`unlink`, all `AccessError`) already prove no non-admin role can reach any credential data. | Test expectation only — no security regression. |
| 2 | SQL log noise: `duplicate key value violates unique constraint "shopify_connector_store_credential_store_id_uniq"` | Not a test failure by itself — an avoidable `ERROR`-level `odoo.sql_db` log line emitted by the intentional duplicate-constraint test (`test_credential_service.test_duplicate_credential_row_for_same_store_raises`) | **Test-log hygiene, not a defect.** The test correctly expects this violation (wrapped in `self.env.cr.savepoint()` since the PR #105 hotfix) — but Odoo's SQL layer still logs the underlying `psycopg2` error at `ERROR` level, polluting the live test log even though the test passes. | Test-expectation / log-hygiene only — the underlying `_store_id_uniq` constraint itself is correct and unchanged. |
| 3 | `test_job_log_system_append.TestJobLogSystemAppend.test_non_admin_indirect_append_succeeds_but_direct_create_denied` | Error: `null value in column "store_id" of relation "shopify_connector_job_log" violates not-null constraint` | **Production behavior.** `shopify.connector.job.log.store_id` was declared `related='job_id.store_id', store=True, required=True`. In Odoo 19, a new record's stored-related fields are populated *after* the row's initial INSERT (identical ordering issue to the `idempotency_key` defect fixed in PR #105), so every `_system_append()` call's `create()` inserts `NULL` into a `NOT NULL` column before the related value is ever read. | **Production model runtime issue** — fixed in `shopify_connector_job_log.py`, not the test. |
| 4 | `test_job_log_system_append.TestJobLogSystemAppend.test_redaction_of_message_technical_detail_payload_snapshot` | Error: same `job.log.store_id` NOT NULL violation, via the same `_system_append()` call path | **Production behavior** — identical root cause to #3. | Production model runtime issue — same fix as #3 covers both. |
| 5 | `test_job_log_system_append.TestJobLogSystemAppend.test_system_append_creates_one_row` | Error: same `job.log.store_id` NOT NULL violation | **Production behavior** — identical root cause to #3. | Production model runtime issue — same fix as #3 covers both. |
| 6 | `test_test_connection.TestTestConnection.test_auth_failure_sets_credential_invalid` | Error: same `job.log.store_id` NOT NULL violation, raised inside `action_test_connection()`'s `except ShopifyClientError` branch when it calls `JobLog._system_append(...)` | **Production behavior** — identical root cause to #3, reached via a second call site (`shopify_connector_store.py::action_test_connection`, four `_system_append()` call sites total, all sharing the one production fix). | Production model runtime issue — same fix as #3 covers all four `_system_append()` call sites in `action_test_connection()`. |

The task description lists six items (including the SQL log-noise item as
"#2"); the table above numbers all six for completeness, matching that
enumeration.

## 3. Production fix — `job.log.store_id`

`addons/shopify_connector_core/models/shopify_connector_job_log.py`:
removed `required=True` from `store_id`. Preserved unchanged:

- `related='job_id.store_id'`
- `store=True`
- `index=True`
- `readonly=True`

`job_id` itself remains `required=True`, so once the row exists,
`store_id` always resolves to a non-empty value — the same reasoning
already accepted for `idempotency_key` in PR #105. `_system_append()`
itself was **not** modified — no new `sudo()`, no ACL change, no
call-site change. Every one of the four `_system_append()` call sites in
`shopify_connector_store.py::action_test_connection()` (attempt-started,
auth-failure, identity-mismatch, success) shares this one field
definition, so the fix covers all of them, not just the observed
failures.

**Regression coverage added:** `test_job_log_system_append.py`'s three
`_system_append()`-exercising tests
(`test_system_append_creates_one_row`,
`test_non_admin_indirect_append_succeeds_but_direct_create_denied`,
`test_redaction_of_message_technical_detail_payload_snapshot`) now each
assert `row.store_id == job.store_id` on the row they create.
`test_test_connection.py`'s `test_pass_path_writes_mirrors_and_job_log`
(success path) and `test_auth_failure_sets_credential_invalid` (failure
path, the one observed to error) now also assert every `job.log` row
created for that job has `store_id == self.store`. Together, the success
path and the `except ShopifyClientError` failure path cover both
`_system_append()` branches inside `action_test_connection()`'s
try/except; the identity-mismatch and attempt-started call sites share
the exact same field definition and call signature, so no separate
assertion was added for them (avoiding a broad test rewrite for a fix
that is provably identical across all four sites).

## 4. Test fix — `fields_get()` misuse in `test_credential_access.py`

`test_non_admin_roles_denied_all_crud_and_search`: removed the
`fields_get()`-disjoint assertion entirely. The test already proves
non-admin roles are denied all access via five real operations
(`search`, `create`, `read`, `write`, `unlink`, each asserted to raise
`AccessError`) — that is the actual security property this test exists
to protect, and it is unchanged and unweakened.

Every other `fields_get()` call site in the allowed test files was
searched and reviewed:

- `test_credential_access.test_field_groups_independent_of_model_acl` —
  **kept, justified.** This one calls `fields_get()` *after* temporarily
  widening the operator role's model-level read ACL (a test-local,
  rolled-back `ir.model.access` row), specifically to prove the
  `access_token` field's own independent field-level `groups=` attribute
  still hides it — a mechanism `fields_get()` *does* honor in Odoo,
  unlike model-level CRUD ACL. The real proof remains the actual `read()`
  call immediately after, asserted to raise `AccessError`; the
  `fields_get()` check is supplementary, not a security oracle by
  itself. A clarifying comment was added inline.
- `test_credential_service._assert_dummy_absent_except_access_token` and
  `test_test_connection.test_no_secret_persisted_anywhere` — **kept,
  justified.** Both use `fields_get()` purely to enumerate `char`/`text`
  field *names* so the test can scan each field's actual *value* for
  leaked token content. Neither treats presence/absence in `fields_get()`
  output as proof of access control. Clarifying comments were added
  inline to both.

No CRUD/security `AccessError` assertion was removed, weakened, or
replaced anywhere in this hotfix.

## 5. Expected SQL-log handling

`@mute_logger('odoo.sql_db')` (from `odoo.tools`, a long-standing,
version-stable Odoo test utility) was added to the two tests in the
allowed-files list that intentionally trigger a raw database
unique-constraint violation:

- `test_credential_service.test_duplicate_credential_row_for_same_store_raises`
  (`shopify_connector_store_credential_store_id_uniq`)
- `test_test_connection.test_core_readiness_check_untouched_still_collides`
  (the job model's `(store_id, idempotency_key)` uniqueness, documenting
  TD-001)

Both tests already ran their expected-to-fail `create()` inside
`self.env.cr.savepoint()` (added in the PR #104/#105 hotfixes) — that
part is unchanged. `mute_logger` only suppresses the `ERROR`-level
`odoo.sql_db` log line for the expected failure; it changes no assertion
and does not affect whether the constraint still fires. TD-001
(`core_readiness_check`'s target-less duplicate-collision exposure)
remains **open and untouched**, as required — the collision still
occurs, only the log noise around the already-passing test is quieted.

**Availability caveat:** no Odoo runtime exists in this environment
(`python3 -c "import odoo"` fails — see §7), so `mute_logger`'s import
path could not be executed and confirmed live in this session. It is a
core Odoo ORM test utility present across many major versions including
current ones; if it is somehow unavailable in this Odoo 19 build, the
live test run will surface an `ImportError` on these two files, and the
tester must report that back rather than assume success. No other
duplicate/unique-constraint test was found in the allowed files beyond
these two (confirmed by grep for `savepoint`, `assertRaises(Exception)`,
and `_uniq` across the module's test files).

## 6. Files changed

| File | Change |
| --- | --- |
| `addons/shopify_connector_core/models/shopify_connector_job_log.py` | Removed `required=True` from `store_id` (kept `related`, `store=True`, `index=True`, `readonly=True`). |
| `addons/shopify_connector_core/tests/test_credential_access.py` | Removed the `fields_get()`-disjoint assertion from `test_non_admin_roles_denied_all_crud_and_search`; added a justifying comment to the remaining legitimate `fields_get()` use in `test_field_groups_independent_of_model_acl`. |
| `addons/shopify_connector_core/tests/test_credential_service.py` | Added `@mute_logger('odoo.sql_db')` to `test_duplicate_credential_row_for_same_store_raises`; added a justifying comment to the `fields_get()` schema-enumeration use in `_assert_dummy_absent_except_access_token`. |
| `addons/shopify_connector_core/tests/test_job_log_system_append.py` | Added `row.store_id == job.store_id` assertions to all three `_system_append()`-exercising tests. |
| `addons/shopify_connector_core/tests/test_test_connection.py` | Added `@mute_logger('odoo.sql_db')` to `test_core_readiness_check_untouched_still_collides`; added `job.log.store_id` assertions to `test_pass_path_writes_mirrors_and_job_log` and `test_auth_failure_sets_credential_invalid`; added a justifying comment to the `fields_get()` schema-enumeration use in `test_no_secret_persisted_anywhere`. |
| `addons/shopify_connector_core/__manifest__.py` | Version bumped `19.0.1.2.2` → `19.0.1.2.3` (production model behavior changed). No dependency change. |
| `docs/05-qa/odoo-19-green-gate-failures.md` | New — this document. |
| `docs/05-qa/task-003-validation-results.md` | Updated with this round's live result and status. |
| `docs/01-research/research-handoff.md` | New compact entry for this hotfix. |

## 7. Regression checks performed (static only)

- `python3 -m py_compile` passed on all six changed Python files.
- No test skip marker (`skip`, `@unittest.skip`, `SkipTest`) exists anywhere in `addons/shopify_connector_core/tests/`.
- `def test_` counts are unchanged before/after in all four changed test files (4 / 11 / 4 / 9) — no test method added or removed.
- No CRUD/security `AccessError` assertion was removed without an equal-or-stronger replacement.
- No `ir.model.access.csv` / `shopify_connector_security.xml` diff (confirmed via `git diff --stat`).
- No `shopify_connector_api_client.py` diff — no Shopify API client/behavior change.
- No product/customer/order/inventory/fulfillment logic added anywhere in the diff.
- No Task 004 file touched.
- Repo-wide grep for `required=True` near `store=True`/`related=` across `addons/shopify_connector_core/models/*.py` confirms zero stored computed/related fields remain `required=True` (the only two, `job.idempotency_key` and `job.log.store_id`, were fixed across PR #105 and this hotfix respectively; `job.operation_scope_key`, also stored+computed, was never `required=True` and needed no change).
- `grep -rn "\.sudo("` across `addons/shopify_connector_core/models/*.py` confirms exactly two sanctioned sudo sites remain (`shopify_connector_job_log.py`, `shopify_connector_store_credential.py`) — unchanged, matching the existing AST-based test guards in both `test_credential_service.py` and `test_job_log_system_append.py`.
- `mute_logger` applied to exactly the two intentional duplicate-constraint tests found in the allowed files; both remain wrapped in `self.env.cr.savepoint()`.
- No Odoo runtime exists in this environment (`python3 -c "import odoo"` fails with `ModuleNotFoundError`; no `odoo`/`odoo-bin` on `PATH`) — **runtime validation was not performed in this session.**

## 8. Remaining live validation required

**This PR must not be merged, and must not be marked ready for review,
until a live Odoo 19 + PostgreSQL run against this exact code path comes
back green.** The tester must re-run, after this PR is reviewed:

1. The four affected test classes first: `test_credential_access`, `test_credential_service`, `test_job_log_system_append`, `test_test_connection`.
2. Then the full `shopify_connector_core` test suite (all 39+ tests), confirming the run no longer halts early and no new failure appears beyond this round's six items.
3. Confirm the `odoo.sql_db` `ERROR` log line for the two intentional duplicate-constraint tests no longer appears (or, if `mute_logger` proves unavailable in this Odoo 19 build, report that back rather than treating the noise as acceptable).
4. Record results in `docs/05-qa/task-003-validation-results.md`, and only then resume `task-003-manual-validation-checklist.md` from VAL-A1.

Do not mark any validation row as passed, and do not mark this PR ready
or merge it, based on this session's static analysis alone.
