# Odoo 19 Runtime Test Failures — `shopify_connector_core` hotfix

**Date:** 2026-07-07
**Scope:** `addons/shopify_connector_core/models/shopify_connector_job.py`
plus the three test files whose classes surfaced failures
(`test_credential_access.py`, `test_credential_service.py`,
`test_job_log_system_append.py`). No Task 004 / domain / UI / controller /
webhook / cron / API-client work.
**Trigger:** After PR #103 (registry-load blocker) and PR #104
(`res.users.groups_id` → `group_ids` + module-wide compatibility audit)
merged into `Shopify-connector`, live validation was re-run against a live
Odoo 19 + PostgreSQL instance. The module now reaches Odoo 19 test
execution and loads all 36 tests, but the run reported:

```
2 failed, 3 error(s) of 36 tests
```

Odoo halted the run after its max-failed-tests threshold, so additional
failures beyond the five recorded below may still be hidden — in
particular, `test_test_connection.py`'s own job-creation paths depend on
the same `idempotency_key` production fix in this hotfix, but that file
runs alphabetically after the three fixed here and was not confirmed to
reach execution in the halted run.

---

## 1. Latest live run summary

| Metric | Value |
| --- | --- |
| Total tests loaded | 36 |
| Failed | 2 |
| Errors | 3 |
| Passed | 31 (by subtraction; not independently itemized in the halted run's output) |
| Halt reason | Odoo's max-failed-tests threshold reached; run stopped before confirming whether tests after the halt point (e.g. `test_test_connection.py`) also fail |

## 2. Each failing test — root cause and classification

| # | Test | Failure kind | Root-cause classification | Production or test-expectation? |
| --- | --- | --- | --- | --- |
| 1 | `test_credential_access.TestCredentialAccess.test_non_admin_roles_denied_all_crud_and_search` | Failure: `self.assertEqual(exposed_fields, {})` — actual `fields_get()` returned base/meta fields, not `{}` | **Test expectation.** Odoo 19's `fields_get()` may return the model's schema (not record data) even for a role with zero ACL rows on the model; that alone does not expose any credential data. The prior assertion conflated "schema call returns something" with "sensitive data is exposed," which is not the actual security property this test protects. | Test expectation only — no security regression. Security intent (non-admin roles denied all CRUD/search on the credential model, and `access_token` never exposed) is unchanged and still fully asserted. |
| 2 | `test_credential_service.TestCredentialService.test_duplicate_credential_row_for_same_store_raises` | Error: `duplicate key value violates unique constraint "shopify_connector_store_credential_store_id_uniq"` — raised on the test's *first* `Credential.create({'store_id': self.store.id})` call | **Both.** (a) Test isolation: the test used the shared class-level `self.store` fixture, so a credential row left by test-ordering/transaction interaction with another test method could already exist for that store before this test's own two `create()` calls run. (b) Test expectation: the constraint (`models.Constraint`, a raw SQL `UNIQUE(store_id)`) raises a raw database-level integrity error in Odoo 19, not the `ValidationError` the test expected, and the un-savepointed `create()` call risked poisoning the surrounding transaction on failure. | Test expectation + isolation. The underlying uniqueness guarantee (`_store_id_uniq`) is completely unchanged in production code. |
| 3 | `test_credential_service.TestCredentialService.test_empty_or_non_string_value_raises_without_echoing` | Failure: `self.assertNotIn(str(bad_value), str(catcher.exception))` for `bad_value == ''` | **Test expectation — logically invalid assertion.** `assertNotIn('', message)` can never pass: the empty string is a substring of every string, including the intended generic error message itself. This is not an Odoo-19 behavior change; the assertion was unsound for this input from the start. | Test expectation only. `action_set_token`/`action_replace_token` already raise the fixed generic message `"A non-empty credential value is required."` with no echo of the bad value — production code needed no change. |
| 4 | `test_job_log_system_append.TestJobLogSystemAppend.test_non_admin_indirect_append_succeeds_but_direct_create_denied` | Error: `null value in column "idempotency_key" of relation "shopify_connector_job" violates not-null constraint` | **Production behavior.** `shopify.connector.job.idempotency_key` was declared `compute=..., store=True, required=True`. In Odoo 19, a new record's stored-computed fields are evaluated *after* its initial row is inserted, so the INSERT itself carries `NULL` for `idempotency_key` — the `NOT NULL` column (added because of `required=True`) rejects that INSERT before the compute method ever runs, for every `shopify.connector.job` creation, regardless of caller. | **Production model runtime issue** — fixed in `shopify_connector_job.py`, not the test. |
| 5 | `test_job_log_system_append.TestJobLogSystemAppend.test_redaction_of_message_technical_detail_payload_snapshot` | Error: same `idempotency_key` NOT NULL violation as #4 (via the same `_create_job()` helper) | **Production behavior** — identical root cause to #4. | Production model runtime issue — same fix as #4 covers both. |

## 3. Files changed

| File | Change |
| --- | --- |
| `addons/shopify_connector_core/models/shopify_connector_job.py` | Removed `required=True` from the `idempotency_key` field (kept `compute`, `store=True`, `index=True`, `readonly=True`; `_compute_idempotency_key` and the `(store_id, idempotency_key)` unique constraint untouched). |
| `addons/shopify_connector_core/tests/test_credential_access.py` | Replaced the `assertEqual(exposed_fields, {})` assertion with an Odoo-19-compatible assertion that `access_token` and every other credential business field (`store_id`, `token_variant`, `credential_state`) are absent from whatever `fields_get()` returns; all five CRUD/search `AccessError` assertions in the same test left unchanged. |
| `addons/shopify_connector_core/tests/test_credential_service.py` | (a) `test_duplicate_credential_row_for_same_store_raises` now creates its own fresh, test-local store and wraps the expected-to-fail second `create()` in `self.env.cr.savepoint()`, asserting a broad `Exception` (matching the pre-existing `test_test_connection.test_core_readiness_check_untouched_still_collides` pattern for the same class of `models.Constraint` violation). (b) `test_empty_or_non_string_value_raises_without_echoing` now asserts the exact generic message (`CREDENTIAL_VALUE_ERROR_MESSAGE = "A non-empty credential value is required."`) via `assertEqual`, for both `action_set_token` and `action_replace_token`, for all three bad values (`''`, `None`, `12345`) — this is a strictly stronger check than the old `assertNotIn` (exact-message equality implies non-echo) and is not logically broken for the empty-string case. |
| `addons/shopify_connector_core/tests/test_job_log_system_append.py` | `_create_job()` now asserts `self.assertTrue(job.idempotency_key)` immediately after creating the job, so every test that uses the helper (`test_system_append_creates_one_row`, `test_non_admin_indirect_append_succeeds_but_direct_create_denied`, `test_redaction_of_message_technical_detail_payload_snapshot`) guards the production fix. |
| `addons/shopify_connector_core/__manifest__.py` | Version bumped `19.0.1.2.1` → `19.0.1.2.2` (production model behavior changed). |

## 4. Regression checks performed

**Source/static:**
- `python3 -m py_compile` passed on all five changed files.
- Repo-wide grep confirms no test skip marker (`skip`, `@unittest.skip`, etc.) was added to any of the three changed test files.
- `def test_` counts are unchanged before/after in all three test files (4 / 11 / 4) — no test method added or removed.
- Grep for `compute=` across `addons/shopify_connector_core/models/*.py` confirms exactly two stored-computed fields remain (`idempotency_key`, `operation_scope_key`); `operation_scope_key` was never `required=True` and needed no change; no other computed-stored-required field exists in the module.
- `grep -n "idempotency_key = fields.Char"` confirms `required=True` is gone and `compute`/`store=True`/`index=True`/`readonly=True` are all still present.

**Test integrity:**
- No test class removed.
- No test method removed.
- Exactly one `assertRaises` changed (`ValidationError` → `Exception` in `test_duplicate_credential_row_for_same_store_raises`), and it is a replacement, not a removal — justified by the observed Odoo 19 raw-integrity-error shape and mirrored against the already-existing, already-accepted `test_core_readiness_check_untouched_still_collides` pattern in `test_test_connection.py` (not itself modified by this hotfix).
- No other assertion removed without a same-or-stronger replacement (the `fields_get` and empty-string assertions were both replaced with strictly more precise checks, not deleted).
- No `sudo()` added anywhere (grep confirms zero new `.sudo(` call sites in this diff).

**Production non-regression:**
- No API client file changed (`shopify_connector_api_client.py` untouched).
- No Shopify API behavior changed.
- `shopify_connector_store_credential.py` (credential service) **not modified** — the generic error message it already raised (`"A non-empty credential value is required."`) was sufficient once the test's assertion was corrected.
- `shopify_connector_job_log.py` (`_system_append`) **not modified**.
- No ACL CSV / security XML changed.
- No Task 004 work of any kind.

**Constraint/idempotency regression:**
- `(store_id, idempotency_key)` uniqueness (`_store_idempotency_key_uniq`) is untouched — still a `models.Constraint`.
- `idempotency_key` is populated after every job `create()` (guarded by the new `_create_job()` assertion in `test_job_log_system_append.py`, and by the same compute logic — unchanged — used everywhere else, including `core_test_connection`'s `payload_hash` UUID4 nonce path in `shopify_connector_store.py`, which this hotfix does not touch).
- `core_test_connection` continues to use a fresh UUID4 `payload_hash` nonce per run (`shopify_connector_store.py`, untouched by this hotfix).
- TD-001 (`core_readiness_check`'s target-less duplicate-collision exposure, `docs/05-qa/technical-debt-register.md`) remains **open and untouched** — this hotfix does not fix it, per explicit instruction.

**Runtime:**
- No Odoo runtime or PostgreSQL instance exists in this environment (confirmed: `python3 -c "import odoo"` fails with `ModuleNotFoundError`, no `odoo`/`odoo-bin` binary on `PATH`). **Runtime validation was not performed in this session.** The tester must re-run, after this PR merges:
  1. The three affected test classes first: `test_credential_access`, `test_credential_service`, `test_job_log_system_append`.
  2. Then the full `shopify_connector_core` test suite (all 36+ tests, watching specifically for whether `test_test_connection.py` surfaces any *new* failure now that the run should no longer halt early on the five fixed here).
  3. Record results in `docs/05-qa/task-003-validation-results.md`, restarting from VAL-A1 as that document already requires.

## 5. Remaining live validation required

Task 003 live validation (`task-003-manual-validation-checklist.md`,
tracked in `task-003-validation-results.md`) remains **blocked** until a
tester re-runs the full clean install + test-execution cycle against a
live Odoo 19 + PostgreSQL instance and confirms:

- `2 failed, 3 error(s) of 36 tests` no longer occurs.
- No new failure appears in `test_test_connection.py` or any other class
  that the previous halted run did not reach.
- All 36 (or more, if further tests are reached now that the run no
  longer halts early) tests pass cleanly.

Do not mark any `task-003-validation-results.md` row as passed based on
this session's static analysis alone.
