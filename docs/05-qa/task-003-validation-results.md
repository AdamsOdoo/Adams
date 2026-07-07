# Task 003 — Manual Validation Results

## Status

**PARTIALLY VALIDATED (live session, 2026-07-07) — Task 003 manual
validation is not fully complete. A live Odoo shell session exercised most
of the testable checklist items against a real Shopify development store
and recorded real results below, but the valid-token positive-connection
test (VAL-B2) is BLOCKED — not passed and not failed — and several other
items were not exercised this session. Do not treat this document as
proof that Task 003's live validation has fully passed, and do not treat
it as authorization to start Task 004.**

Live validation was first started against a live Odoo 19 + PostgreSQL
instance and failed immediately at VAL-A1 (clean install) with:

```
Loading module shopify_connector_core
Loading shopify_connector_core/security/shopify_connector_security.xml
Failed to load registry

Fatal error:
ValueError: Invalid field 'category_id' in 'res.groups'
```

with a parse location inside `group_shopify_connector_auditor`'s
`<field name="category_id" .../>`, plus a pre-existing warning noted in the
same run: `Model attribute '_sql_constraints' is no longer supported,
please define models.Constraint on the model.` Root cause: Odoo 19 removed
`category_id` from `res.groups` (groups now use `privilege_id` →
`res.groups.privilege`) and deprecated `_sql_constraints` in favor of
`models.Constraint`. This was fixed by PR #103
(`claude/odoo19-install-blocker-fnm5ro`, merge commit `7361fbc`), which has
since merged into `Shopify-connector` (see
`docs/01-research/research-handoff.md`, "Odoo 19 Install-Compatibility
Hotfix" entry).

Live validation was re-run after PR #103 merged. The install progressed
past registry load this time and reached actual **Odoo 19 test execution**
for `shopify_connector_core`, but that run **errored out before
completing, with 4 errors**, in these test classes:

- `shopify_connector_core.tests.test_credential_access.TestCredentialAccess`
- `shopify_connector_core.tests.test_credential_service.TestCredentialService`
- `shopify_connector_core.tests.test_job_log_system_append.TestJobLogSystemAppend`
- `shopify_connector_core.tests.test_test_connection.TestTestConnection`

Observed error: `ValueError: Invalid field 'groups_id' in 'res.users'`. Root
cause: each of these four test classes' shared `_create_group_user` test
helper created a `res.users` record with `'groups_id': [(6, 0,
[group.id])]`; Odoo 19 renamed this field to `group_ids`. This was fixed by
PR #104 (`claude/odoo19-test-groups-id-7v35ym`, merge commit `867074c`),
which also expanded (F1 revision) into a module-wide Odoo 19 compatibility
audit — see `docs/05-qa/odoo-19-compatibility-audit.md` — that found no
sibling `groups_id`/`category_id`/`_sql_constraints`/deprecated-ORM risk
anywhere else in `addons/shopify_connector_core/` beyond the four call
sites fixed there.

Live validation was re-run again after PR #104 merged. The install and
test-loading progressed further this time, reaching **all 36 tests**, but
the run reported:

```
2 failed, 3 error(s) of 36 tests
```

Odoo halted after its max-failed-tests threshold, so additional failures
beyond these five may still be hidden — in particular, `test_test_connection.py`'s
job-creation paths were not confirmed to have been reached before the halt.
Full root-cause detail, classification, and the files-changed list for the
hotfix addressing this round are recorded in
[`odoo-19-runtime-test-failures.md`](./odoo-19-runtime-test-failures.md).
In summary:

1. `test_credential_access.test_non_admin_roles_denied_all_crud_and_search` —
   **failure**, test-expectation only (an Odoo-19-incompatible
   `fields_get()` assertion, not a security regression).
2. `test_credential_service.test_duplicate_credential_row_for_same_store_raises` —
   **error**, test isolation + test-expectation (shared-store collision risk,
   and the Odoo 19 unique-constraint violation is a raw database exception,
   not `ValidationError`).
3. `test_credential_service.test_empty_or_non_string_value_raises_without_echoing` —
   **failure**, a logically-invalid assertion (`assertNotIn('', ...)` can
   never pass), not an Odoo 19 behavior change.
4. `test_job_log_system_append.test_non_admin_indirect_append_succeeds_but_direct_create_denied` —
   **error**, production behavior: `shopify.connector.job.idempotency_key`'s
   `required=True` on a `compute+store` field rejects the row's initial
   INSERT (NULL at insert time) before the compute ever runs, in Odoo 19.
5. `test_job_log_system_append.test_redaction_of_message_technical_detail_payload_snapshot` —
   **error**, identical root cause to #4.

A focused runtime hotfix addressing all five (production model fix for #4/#5;
test-expectation fixes for #1/#2/#3) was applied via PR #105
(`claude/odoo19-credential-test-fixes-l35wbf`, merge commit `f915211`),
which has since merged into `Shopify-connector`.

**Live validation was re-run again after PR #105 merged.** The run reached
all 39 tests this time, but reported:

```
1 failed, 4 error(s) of 39 tests
```

Odoo halted again after its max-failed-tests threshold. Full root-cause
detail, classification, and the files-changed list for this round's
(green-gate) hotfix are recorded in
[`odoo-19-green-gate-failures.md`](./odoo-19-green-gate-failures.md). In
summary:

1. `test_credential_access.test_non_admin_roles_denied_all_crud_and_search` —
   **failure**, test-expectation only. The PR #105 hotfix's own
   `fields_get()`-disjoint assertion still fails, because `fields_get()`
   is a schema call in Odoo and is not gated by `ir.model.access` CRUD
   rows — only by each field's own `groups=` attribute. Not a security
   regression: the five actual-operation `AccessError` assertions in the
   same test are unaffected and still fully prove the access-denial
   property.
2. SQL log noise: `duplicate key value violates unique constraint
   "shopify_connector_store_credential_store_id_uniq"` — the intentional
   duplicate-credential test still passes, but Odoo's `odoo.sql_db` logger
   emits an avoidable `ERROR`-level line for the expected violation,
   polluting the live test log.
3. `test_job_log_system_append.test_non_admin_indirect_append_succeeds_but_direct_create_denied`,
   `test_job_log_system_append.test_redaction_of_message_technical_detail_payload_snapshot`,
   `test_job_log_system_append.test_system_append_creates_one_row`,
   `test_test_connection.test_auth_failure_sets_credential_invalid` — **four
   errors**, all the same production root cause:
   `shopify.connector.job.log.store_id` is a stored related field
   (`related='job_id.store_id', store=True, required=True`). In Odoo 19 a
   new record's stored-related fields are populated *after* its initial
   row INSERT — the identical class of ordering issue already fixed once
   for `job.idempotency_key` in PR #105 — so every `_system_append()`
   call's `create()` inserted `NULL` into a `NOT NULL` column before the
   related value was ever read.

A focused green-gate hotfix addressing all of the above (production model
fix for the four `job.log.store_id` errors; test-expectation fix for the
`fields_get()` failure; `mute_logger` for the SQL log noise, without
weakening or removing the underlying constraint tests) was proposed via the
`claude/odoo-shopify-test-failures-9scudd` branch/PR (see
`docs/01-research/research-handoff.md`, "Odoo 19 Green-Gate Hotfix" entry).

**Live manual validation session — 2026-07-07.** After the green-gate
hotfix landed, a live Odoo shell session was run against database/branch
prompt `adamsmen-shopify-connector-34582665 [dev/19.0]` on **Odoo 19.0**,
with `shopify_connector_core` **installed at version `19.0.1.2.3`**,
targeting the Shopify development store **`mqiu21-yz.myshopify.com`**
(API version `2026-07` configured in the shell variables). This confirms
an **installed-module / registry-load observation** for VAL-A1 —
the module was found installed at this version with the registry loaded
and no traceback during shell startup/module inspection. **This session
did not re-execute a fresh clean install/upgrade command**; the last
full clean-install proof (a fresh install with no error) is the
PR #103/#104/#105 and green-gate hotfix re-run history described above,
not this shell session. A substantial portion of the remaining checklist
was also exercised — see the **Validation summary** table immediately
below for the full per-item breakdown, and §§1–3 for the detailed
results.

**No valid Shopify Admin API access token was available for this
session.** The Shopify Dev Dashboard app used did not provide the older
admin-created custom-app Admin API token issuance path the connector
currently expects (per Task 002's `token_variant='offline_custom_app'`).
Every checklist item that requires a **successful, passing** Shopify
connection — most importantly **VAL-B2**, the valid-token positive-
connection test — is therefore recorded as **BLOCKED, not passed and not
failed**, and everything depending on it (e.g. VAL-E1's pass-path row
accounting) is BLOCKED or not tested as well. **No new runtime code
defect was observed in the tested paths.** However, token acquisition
remains an unresolved product/architecture setup blocker before
customer-facing setup can be accepted — see
`docs/01-research/research-handoff.md` for the routed follow-up.

**This document does not assert that Task 003 validation has passed in
full, and does not assert that a valid Shopify connection has been
proven.** Items marked "Not tested" below were not exercised in this
session and must not be inferred as passing from code-reading alone —
they remain to be executed in a future live session per
[`task-003-manual-validation-checklist.md`](./task-003-manual-validation-checklist.md).

---

## Validation summary (live session, 2026-07-07)

| Test ID | Status | Notes |
| --- | --- | --- |
| VAL-A1 | **Passed (installed-module / registry-load observation only)** | `shopify_connector_core` confirmed installed at `19.0.1.2.3`, registry loaded, no traceback during shell startup/module inspection. **Fresh clean install/upgrade was not re-executed in this shell session** — see the Status narrative above for the last full clean-install proof (the PR #103/#104/#105 and green-gate hotfix re-run cycle). |
| VAL-A2 | **Passed** | Models found: `shopify.connector.api.client`, `shopify.connector.store`, `shopify.connector.job`, `shopify.connector.job.log`, `shopify.connector.store.credential`. No database table exists for `shopify.connector.api.client`, confirming it remains an `AbstractModel`. |
| VAL-A3 | **Passed** | `job_type` selection count is exactly 3: `core_readiness_check`, `core_manual_maintenance`, `core_test_connection`. |
| VAL-A4 | **Static repo check: Passed** (docs-only static/offline sweep, 2026-07-07) | Confirmed by repo/source inspection: Task 003 (PR #101) introduced no XML file, menu, action, wizard, controller, route, cron, or server/scheduled action of any kind. The DB/`ir.model.data`-registry-level half against a live installed instance is still not exercised — no live Odoo instance was available. See `task-003-static-validation-sweep.md`. |
| VAL-B1 | **Passed** | Invalid-token test on store id 7 (`mqiu21-yz.myshopify.com`) with dummy token `shpat_INVALID_INVALID_INVALID0000000000000000`: result `fail`, reason "Your access token appears invalid or was revoked — replace it.", `credential_state='invalid'`, `job` state `failed_final`, `error_class='shopify_permission_scope_auth'`, 2 job-log rows (`['attempt', 'attempt']`), `log_store_ok=True`. Matches the checklist's expected behavior. |
| VAL-B2 | **BLOCKED** | No real Shopify Admin API access token was available. The Dev Dashboard app used did not expose the older admin-created custom-app Admin API token path the connector currently expects (`token_variant='offline_custom_app'`). Not passed, not failed. |
| VAL-B3 | **Passed** | Repeat `action_test_connection()` on the same store: job count BEFORE=1, AFTER=2, CREATED=1 — a fresh `core_test_connection` job was created with no unique-constraint collision. |
| VAL-B4 | Not tested | Identity-mismatch behavior not exercised this session. |
| VAL-B5 | Not tested | Shop-state failure behavior not exercised this session. |
| VAL-B6 | Not tested | Cross-check requires VAL-B4/VAL-B5, neither of which was run this session; only the VAL-B1 flip was observed in isolation. |
| VAL-B7 | Not tested | Version fall-forward warning behavior not exercised this session. |
| VAL-C1 | **PARTIAL** | **DB/ORM unexpected-token-leakage scan: Passed.** A naive token-string scan flagged `('shopify.connector.store.credential', 21, 'access_token')` — this is the **intended, by-design credential storage location**, not a leak. A corrected scan that excludes that intended field returned `UNEXPECTED_LEAKS: []` across the ORM/database-visible surfaces scanned (store mirrors, job rows, job-log rows, messages, `technical_detail`, and `payload_snapshot`). **Odoo server log grep: Not tested.** The live shell session checked ORM/database-visible fields only — it did **not** grep the Odoo server log file(s). **`access_token` is stored in plain text on `shopify.connector.store.credential`, protected only by Odoo ACLs — it is not encrypted at rest.** This is a known, documented residual, not a new finding. **Overall VAL-C1: PARTIAL — DB/ORM scan passed, server-log scan pending.** A subsequent docs-only static/offline session (2026-07-07) confirmed this execution environment has no live Odoo runtime and no server log file of any kind to grep — see `task-003-server-log-redaction-check.md`. The server-log half therefore remains **not testable in this session — logs unavailable**, still not pass/fail, pending a future session with actual live-log access. |
| VAL-C2 | **Passed** | A direct `shopify.connector.job.log.create(...)` attempt by a user in `group_shopify_connector_operator` (uid 18) was denied by Odoo's ACL layer ("Access Denied by ACLs for operation: create"), raising `AccessError` as expected. |
| VAL-C3 | **Static source check: Passed** (docs-only static/offline sweep, 2026-07-07) | Confirmed exactly 2 `sudo()` call sites in production code — `_get_access_token` (`shopify_connector_store_credential.py`) and `_system_append` (`shopify_connector_job_log.py`) — matching the governance-documented expectation. This is a static source count, not a live-installed-module re-verification. See `task-003-static-validation-sweep.md`. |
| VAL-D1 | **Static read-only-query evidence only** (docs-only static/offline sweep, 2026-07-07) | Confirmed `TEST_CONNECTION_QUERY` is read-only and matches the expected query exactly; confirmed no GraphQL `mutation` operation string exists anywhere in `shopify_connector_core`. This is static source evidence, not a live Shopify Admin observation of zero changes/webhooks — that live check remains not tested. See `task-003-static-validation-sweep.md` and `task-003-no-side-effect-baseline.md`. |
| VAL-D2 | **Static code-path evidence only** (docs-only static/offline sweep, 2026-07-07) | Confirmed `action_test_connection()` and its helpers write only to `shopify.connector.store`, `shopify.connector.store.credential` (`credential_state` only), `shopify.connector.job`, and `shopify.connector.job.log` — no product/customer/order/inventory/stock/accounting/sale/purchase model reference anywhere in the code path. This is static code-path evidence, not a live-database mutation observation. See `task-003-static-validation-sweep.md` and `task-003-no-side-effect-baseline.md`. |
| VAL-E1 | **BLOCKED** | Pass-path row accounting requires a successful connection (VAL-B2), which is blocked. |
| VAL-E2 | **Passed** | Two independent fail-path jobs recorded: Job 17 and Job 18, both `state='failed_final'`, `error_class='shopify_permission_scope_auth'`, `payload_hash` and `idempotency_key` both present (truthy), exactly 2 `job.log` rows each (`['attempt', 'attempt']`), `log_store_ok=True`. |
| VAL-E3 | **Passed (fail-path only)** | No extra/missing `job.log` rows observed across Job 17 and Job 18. Pass-path row accounting is not applicable — VAL-B2/VAL-E1 blocked. |
| VAL-F1 | **Passed** | Confirms `TD-001` **remains open** — a second `core_readiness_check` job for the same store (`TD001` regression store) still collides: `duplicate key value violates unique constraint "shopify_connector_job_store_idempotency_key_uniq"` (`UniqueViolation`). Recorded as proof TD-001 is still present, **not** as a fix. |
| VAL-G1 | Not tested | The raw HTTP status code for the VAL-B1 invalid-token response was not captured this session — only the mapped `error_class`/reason were recorded. |
| VAL-G2 | Not tested | Not reproduced this session. |
| VAL-G3 | Not tested | Not reproduced this session. |
| VAL-G4 | Not tested | Not reproduced this session. |

---

## 1. Environment details

| Field | Value |
| --- | --- |
| Date executed | 2026-07-07 |
| Tester | _Not recorded — the shell operator's identity was not captured in the session transcript this document was built from._ |
| Odoo version/build | Odoo 19.0 (exact build/commit not recorded this session) |
| Odoo install method | _Not recorded this session_ |
| PostgreSQL version | _Not recorded this session_ |
| Database name | `adamsmen-shopify-connector-34582665` (shell prompt shows `[dev/19.0]`) |
| `shopify_connector_core` module version installed | `19.0.1.2.3` (post-green-gate hotfix) |
| Base commit validated | `e27f10e55f3504d1a9b8871a207b3d9762a3c783` (PR #101 merge commit) — superseded in practice by the module version above, which reflects the subsequent PR #103/#104/#105 and green-gate hotfixes; the exact commit SHA validated in this live session was not captured. |
| Shopify development store used (handle/domain) | `mqiu21-yz.myshopify.com` |
| Shopify API version configured on the test store record | `2026-07` (as set in the shell session's variables) |
| Token type used | Dummy/invalid token for VAL-B1 (`shpat_INVALID_INVALID_INVALID0000000000000000`); **no valid token was available** for VAL-B2 (BLOCKED) |
| Odoo test user role(s) used | `group_shopify_connector_operator` confirmed used for the VAL-C2 ACL test (uid 18); role(s) used for other shell operations not explicitly recorded in the transcript. |

## 2. Test case results

Fill in one row per checklist item. Do not skip a row — if a step was not
reproducible, say so explicitly in **Actual result** and set **Pass/Fail** to
`N/A (not reproducible)`, not `Pass`.

| Test ID | Test case | Expected result | Actual result | Pass/Fail | Evidence reference |
| --- | --- | --- | --- | --- | --- |
| VAL-A1 | Clean install/upgrade | Installs/upgrades without error | **Failed (first attempt).** `Failed to load registry` / `ValueError: Invalid field 'category_id' in 'res.groups'` while loading `shopify_connector_security.xml`. **Re-run after PR #103 merged:** install progressed past registry load into Odoo 19 test execution, then **failed with 4 errors** — `ValueError: Invalid field 'groups_id' in 'res.users'`. **Re-run after PR #104 merged:** reached all 36 tests, then **`2 failed, 3 error(s) of 36 tests`**. **Re-run after PR #105 merged:** reached all 39 tests, then **`1 failed, 4 error(s) of 39 tests`**. **Live session, 2026-07-07 (post-green-gate hotfix):** confirmed `shopify_connector_core` installed at version `19.0.1.2.3`, registry loaded, no traceback during shell startup/module inspection. **This shell session did not re-execute a fresh clean install/upgrade command** — it observed the state of an already-installed module, not a fresh install run. | **Pass (installed-module / registry-load observation only, 2026-07-07 live session) — fresh clean install/upgrade not re-executed this session** | See Appendix §A "Install/model checks" below. |
| VAL-A2 | Model registry loads | `api.client` abstract (no table); other 3 models intact | Live session confirmed all 5 known models present (`shopify.connector.api.client`, `store`, `job`, `job.log`, `store.credential`); no database table for `shopify.connector.api.client`. | **Pass (2026-07-07)** | See Appendix §A. |
| VAL-A3 | Three `job_type` values in ORM | Exactly 3 values, no 4th | `job_type` selection count = 3 (`core_readiness_check`, `core_manual_maintenance`, `core_test_connection`). | **Pass (2026-07-07)** | See Appendix §A. |
| VAL-A4 | No XML/menu/action/wizard/controller/cron | Zero rows of any kind | Not exercised this session. | **N/A (not tested this session)** | — |
| VAL-B1 | Invalid-token test | Fails, auth class, `credential_state='invalid'` | Store id 7 (`mqiu21-yz.myshopify.com`) created; dummy token `shpat_INVALID_INVALID_INVALID0000000000000000` set; `credential_present=True`; `action_test_connection()` returned RESULT=`fail`, REASON="Your access token appears invalid or was revoked — replace it.", CREDENTIAL_STATE=`invalid`, JOB_STATE=`failed_final`, ERROR_CLASS=`shopify_permission_scope_auth`, JOB_LOG_COUNT=2, LOG_EVENTS=`['attempt', 'attempt']`, LOG_STORE_OK=`True`. Matches expected behavior exactly. | **Pass (2026-07-07)** | See Appendix §B "Invalid-token validation." |
| VAL-B2 | Valid dev-store token test | Passes, mirrors + scopes populated | **Not executable — no valid Shopify Admin API access token was available.** The Dev Dashboard app used did not provide the older admin-created custom-app Admin API token issuance path this connector currently expects. | **BLOCKED (not passed, not failed)** | — |
| VAL-B3 | Repeat run (idempotency/collision guard) | Second run succeeds, no unique-constraint collision | BEFORE=1, AFTER=2, CREATED=1 — repeat `action_test_connection()` created a new `core_test_connection` job with no collision. | **Pass (2026-07-07)** | See Appendix §C "Repeat/idempotency validation." |
| VAL-B4 | Identity-mismatch behavior | Fails `odoo_validation_configuration`, `credential_state` untouched | Not exercised this session. | **N/A (not tested this session)** | — |
| VAL-B5 | Shop-state failure behavior (if reproducible) | Auth class, distinct reason, `credential_state` untouched | Not exercised this session. | **N/A (not tested this session)** | — |
| VAL-B6 | `credential_state` flips only on genuine token-invalid signal | Confirmed against B1/B4/B5 | Cannot be cross-checked — VAL-B4/VAL-B5 not run this session. | **N/A (not tested this session)** | — |
| VAL-B7 | Version fall-forward warning (if reproducible) | Still `pass`; `api_health_state='degraded'` | Not exercised this session. | **N/A (not tested this session)** | — |
| VAL-C1 | Token redaction (DB + server log) | Zero hits for either token, outside intended credential storage | **DB/ORM unexpected-token-leakage scan:** naive scan: `LEAKS: [('shopify.connector.store.credential', 21, 'access_token')]` — this is the **intended** credential storage field, not a leak (see checklist revision, item 4 below). Corrected scan excluding that field: `UNEXPECTED_LEAKS: []` across the ORM/database-visible surfaces scanned. **Odoo server log grep:** not performed this session — the live shell session checked ORM/database-visible fields only. `access_token` remains stored in plain text, protected only by ACLs — no encryption claim is made. | **PARTIAL — DB/ORM scan: Pass; server-log scan: Not tested (2026-07-07)** | See Appendix §D "Token leakage validation." |
| VAL-C2 | `job.log` direct-create vs `_system_append` ACL check | Direct create → `AccessError`; indirect via `_system_append` → succeeds | Direct `job.log.create(...)` by a `group_shopify_connector_operator` user (uid 18) was denied: "Access Denied by ACLs for operation: create, uid: 18, model: shopify.connector.job.log" → `AccessError` raised as expected. Indirect path via `_system_append` not separately re-exercised this session (already proven passing/failing through VAL-B1/VAL-B3's job-log creation, which succeeded via the system path). | **Pass (2026-07-07, direct-create half)** | See Appendix §E "ACL validation." |
| VAL-C3 | Exactly two `sudo()` sites (live-confirmed) | 2 sites, no more | Not re-verified this session. | **N/A (not tested this session)** | — |
| VAL-D1 | No Shopify-side mutation | Zero changes, zero webhooks | Not exercised this session. | **N/A (not tested this session)** | — |
| VAL-D2 | No Odoo-side domain mutation | Zero domain-model changes | Not exercised this session. | **N/A (not tested this session)** | — |
| VAL-E1 | Pass-path row accounting | 1 job row + 2 job.log rows | Not executable — depends on VAL-B2 (blocked). | **BLOCKED (not passed, not failed)** | — |
| VAL-E2 | Fail-path row accounting | 1 job row + 2 job.log rows | Job 17: state `failed_final`, error_class `shopify_permission_scope_auth`, `payload_hash`/`idempotency_key` both present, 2 logs (`['attempt', 'attempt']`), `log_store_ok=True`. Job 18: identical shape. | **Pass (2026-07-07)** | See Appendix §F "Job/log accounting." |
| VAL-E3 | No extra/missing rows | Confirmed across all runs | No extra/missing `job.log` rows observed for Job 17 or Job 18. Pass-path rows not applicable (VAL-B2 blocked). | **Pass (fail-path only, 2026-07-07)** | See Appendix §F. |
| VAL-F1 | `core_readiness_check` / TD-001 still collides | Second job for same store still collides | TD001 regression store created; first `core_readiness_check` job created; second duplicate `core_readiness_check` job attempt raised `duplicate key value violates unique constraint "shopify_connector_job_store_idempotency_key_uniq"` (`UniqueViolation`). Confirms TD-001 is **still open**, not fixed. | **Pass (confirms TD-001 still open, 2026-07-07)** | See Appendix §G "TD-001 validation." |

## 3. Empirical API behavior observed

Record only what was actually observed. Mark unreproduced items explicitly —
do not leave blank and do not assert an unobserved value.

| ID | Open question | Observed answer | Reproducible? | Evidence reference |
| --- | --- | --- | --- | --- |
| VAL-G1 | Actual HTTP status for an invalid/revoked token | Not captured this session — VAL-B1 recorded the mapped `error_class='shopify_permission_scope_auth'` and business-friendly reason, but the raw HTTP status code was not logged/recorded in the transcript. | Not reproduced this session | — |
| VAL-G2 | Actual `THROTTLED` response body shape | Not reproduced this session. | Not reproduced this session | — |
| VAL-G3 | Scopes required for `shop`/`currentAppInstallation` query | Not reproduced this session (no valid token was available to reach a passing call). | Not reproduced this session | — |
| VAL-G4 | Actual missing-scope error shape | Not reproduced this session. | Not reproduced this session | — |

## 4. Defects found

List every deviation from expected behavior found during this session. Do
**not** fix any of them in this session — record only. Each defect must be
routed by a future, separately scoped session either into
`technical-debt-register.md` (if accepted as a known trade-off) or into a
new bug-fix task (if it must be corrected before Task 004).

| ID | Area | Description | Severity | Suggested routing |
| --- | --- | --- | --- | --- |
| _None newly found this session._ | — | VAL-F1 re-confirmed the pre-existing, already-tracked `TD-001` (`core_readiness_check` idempotency-key collision) is still open. This is not a new defect — see `technical-debt-register.md`, which already carries `TD-001` and is not modified by this session. | — | Already routed to `technical-debt-register.md` (pre-existing). |

## 5. Go/No-Go recommendation

**Not yet determined — this session provides partial results only.** Task
003 manual validation cannot be called Go or No-Go until VAL-B2 (or a
formal decision to re-scope it, see the open follow-up in
`docs/01-research/research-handoff.md`), VAL-C1's server-log-grep half,
and the remaining not-tested items (VAL-A4, VAL-B4–B7, VAL-C3, VAL-D1–D2,
VAL-G1–G4) are resolved in a future live session.

- **Recommendation:** _Partial — not a full Go, not a No-Go. Every item
  that was testable without a valid Shopify Admin API token passed or, for
  VAL-A1 and VAL-C1, partially passed within the narrower scope actually
  exercised (see notes below); the positive-connection path (VAL-B2) and
  everything depending on it remain blocked pending a token-acquisition
  decision._
- **Rationale:** Eight checklist items passed cleanly against the live
  environment (VAL-A2–A3, VAL-B1, VAL-B3, VAL-C2, VAL-E2–E3, VAL-F1), with
  no new defects found. VAL-A1 passed only as an installed-module /
  registry-load observation — a fresh clean install/upgrade command was
  not re-executed this session. VAL-C1 is **PARTIAL**: its DB/ORM
  unexpected-token-leakage scan passed, but its Odoo server-log-grep half
  was not tested this session. Two items (VAL-B2, VAL-E1) are blocked
  purely by token-tooling availability. **No new runtime code defect was
  observed in the tested paths.** Twelve items were not exercised this
  session and are not assumed to pass.
- **Conditions (if "Go with conditions"):** Not proposed in this docs-only
  session — routed to ChatGPT per `docs/01-research/research-handoff.md`'s
  open follow-up (offline/custom-app-token-only MVP vs. introducing
  OAuth/Dev-Dashboard-compatible token acquisition).
- **Blocking defects (if "No-Go"):** None — no new runtime code defect was
  observed in the tested paths. However, token acquisition remains an
  unresolved product/architecture setup blocker before customer-facing
  setup can be accepted, and VAL-C1's server-log scan and several other
  checklist items remain not tested.

## 6. Sign-off

| Role | Name | Date | Confirmation |
| --- | --- | --- | --- |
| Tester | _Not recorded_ | 2026-07-07 | Live shell session executed against Odoo 19.0 and `mqiu21-yz.myshopify.com`; results transcribed into this document from that session's actual output, not from assumption. |
| Reviewer (ChatGPT, per `CLAUDE.md` §2) | _TBD_ | _TBD_ | Reviews this results record before any next feature-development session starts. |

## 7. Handoff

**Task 004 remains blocked.** This partial validation record must be
reviewed and accepted by ChatGPT before any further Task 003 validation
work, and certainly before any Task 004 (or other next-feature) session is
authorized. See `docs/01-research/research-handoff.md` for the full
compact handoff entry and the open token-acquisition follow-up this session
routes to ChatGPT.

---

## Appendix — condensed evidence excerpts from the 2026-07-07 live shell session

This appendix records condensed evidence excerpts from the live shell
session, for traceability — it is not a verbatim transcript. It
supplements, and does not replace, the summary and per-row tables above.

### A. Install/model checks

```
shopify_connector_core installed 19.0.1.2.3
Models found:
  shopify.connector.api.client
  shopify.connector.store
  shopify.connector.job
  shopify.connector.job.log
  shopify.connector.store.credential
No database table exists for shopify.connector.api.client.
job_type selection count is 3:
  core_readiness_check
  core_manual_maintenance
  core_test_connection
```

### B. Invalid-token validation

```
Store created:
  id: 7
  shop_domain: mqiu21-yz.myshopify.com
Dummy token used:
  shpat_INVALID_INVALID_INVALID0000000000000000
credential_present: True
action_test_connection result:
  RESULT: fail
  REASON: Your access token appears invalid or was revoked — replace it.
  CREDENTIAL_STATE: invalid
  JOB_STATE: failed_final
  ERROR_CLASS: shopify_permission_scope_auth
  JOB_LOG_COUNT: 2
  LOG_EVENTS: ['attempt', 'attempt']
  LOG_STORE_OK: True
```

### C. Repeat/idempotency validation

```
BEFORE: 1
AFTER: 2
CREATED: 1
```

Confirms repeat test-connection creates a new `core_test_connection` job
and does not collide.

### D. Token leakage validation

```
Naive scan result:
  LEAKS: [('shopify.connector.store.credential', 21, 'access_token')]
```

This is the intended, by-design credential storage location, not an
unexpected leak — the current implementation explicitly stores
`access_token` in plain text behind ACLs; no encryption claim is made.

```
Corrected unexpected-leak scan (excluding store.credential.access_token):
  UNEXPECTED_LEAKS: []
```

Zero unexpected token leakage found across the ORM/database-visible
surfaces scanned (store mirrors, job rows, job-log rows, message/
`technical_detail`/`payload_snapshot` fields), outside the intended
credential storage field. The Odoo server log file(s) were **not**
grepped in this session — that half of VAL-C1 is **Not tested**. DB/ORM
scan recorded as **PASSED**; overall VAL-C1 is **PARTIAL**.

### E. ACL validation

Direct `job.log` create attempted with a user in
`group_shopify_connector_operator`. Odoo logged:

```
Access Denied by ACLs for operation: create, uid: 18, model: shopify.connector.job.log
```

Shell result:

```
DIRECT_CREATE: AccessError OK
```

Recorded as **PASSED**.

### F. Job/log accounting

```
Job 17:
  state: failed_final
  error_class: shopify_permission_scope_auth
  payload_hash: True
  idempotency_key: True
  logs: 2 ['attempt', 'attempt']
  log_store_ok: True

Job 18:
  state: failed_final
  error_class: shopify_permission_scope_auth
  payload_hash: True
  idempotency_key: True
  logs: 2 ['attempt', 'attempt']
  log_store_ok: True
```

### G. TD-001 validation

Created a `TD001` regression store; created a first
`setup_readiness_check`/`core_readiness_check` running job; attempted a
second duplicate readiness-check running job. Odoo raised:

```
duplicate key value violates unique constraint "shopify_connector_job_store_idempotency_key_uniq"
UniqueViolation
```

Shell result:

```
TD001: collision still exists OK
UniqueViolation
```

Recorded as **PASSED** — this confirms TD-001 is still open, not that it
is fixed.

---

## Static/Offline Validation Addendum (docs-only session, 2026-07-07)

This addendum records a **separate, later, docs-only static/offline
session** (branch `claude/task-003-static-validation-cszl88`), run
deliberately in parallel with — and without touching — a separate,
concurrently-running session performing the Fable/manual OAuth
token-acquisition experiment. This session had **no live Odoo instance, no
live Shopify connection, and no valid Shopify Admin API token**; it worked
from repository/source inspection only. It does not repeat, re-derive, or
contradict the live-session results recorded above — it only adds narrower,
static evidence for items that live session left entirely untested.

**Static evidence gathered this session:**

- **VAL-A4** — static repo check **passed**: Task 003 introduced no
  XML/menu/action/wizard/controller/cron of any kind. DB/registry-level
  confirmation against a live instance is still not tested. Full detail:
  `task-003-static-validation-sweep.md`.
- **VAL-C3** — static source check **passed**: exactly 2 `sudo()` call sites
  in production code, matching the governance-documented expectation. Live
  re-verification against an installed module is still not tested. Full
  detail: `task-003-static-validation-sweep.md`.
- **VAL-C1 (server-log half)** — **not testable this session — logs
  unavailable.** No live Odoo runtime and no server log file of any kind
  exists in this session's execution environment. Only the existing dummy
  token (`shpat_INVALID_INVALID_INVALID0000000000000000`) was in scope; no
  real token was used, requested, or recorded. Still not pass/fail. Full
  detail: `task-003-server-log-redaction-check.md`.
- **VAL-D1** — static read-only-query evidence **confirmed**: the
  `TEST_CONNECTION_QUERY` string is read-only and matches the expected query
  exactly; no GraphQL `mutation` operation string exists anywhere in
  `shopify_connector_core`. This is not a live Shopify Admin observation of
  zero changes/webhooks, which remains not tested. Full detail:
  `task-003-no-side-effect-baseline.md`.
- **VAL-D2** — static code-path evidence **confirmed**: `action_test_connection()`
  and its helpers write only to `shopify.connector.store`,
  `shopify.connector.store.credential` (`credential_state` only),
  `shopify.connector.job`, and `shopify.connector.job.log` — no domain
  (product/customer/order/inventory/stock/accounting/sale/purchase) model is
  referenced anywhere in the path. This is not a live-database mutation
  proof, which remains not tested. Full detail:
  `task-003-no-side-effect-baseline.md`.
- **VAL-G1–G4** — remain **not tested**. No live API call was made this
  session; no empirical behavior is asserted or invented.

**Remaining open items (unchanged by this addendum):** VAL-A1 (fresh
install/upgrade re-run), VAL-A4's DB/registry-level half, VAL-B2 and
everything depending on it (VAL-B4–B7, VAL-E1), VAL-C1's server-log half,
VAL-D1/D2's live-observation halves, and VAL-G1–G4. All require a live Odoo
instance, a live Shopify connection, and/or real server logs, none of which
were available to this session.

**This addendum does not change the Go/No-Go recommendation in §5 above —
it is still "Not yet determined."** Task 003 manual validation **remains
incomplete**. Task 004 **remains blocked**. This session makes no claim that
OAuth/token acquisition succeeded or failed, and makes no claim that VAL-B2
passed — that work belongs to a separate, concurrently-running session and
is not duplicated or second-guessed here.
