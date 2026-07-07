# Task 003 — Manual Validation Results

## Status

**BLOCKED — install progressed past VAL-A1's original failure, but a third
runtime blocker was found after the PR #105 hotfix merged; a fourth
(green-gate) hotfix is pending review/merge, and this PR must remain draft
until a live green run confirms it.**

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
weakening or removing the underlying constraint tests) is proposed on the
current branch/PR (see `docs/01-research/research-handoff.md`, "Odoo 19
Green-Gate Hotfix" entry, for the branch/PR reference).

**All live validation remains blocked, and every row below remains
unexecuted/unpassed, until this green-gate hotfix is reviewed/merged and
the full install + test-execution run is re-run cleanly from VAL-A1 and
comes back fully green.** Do not mark VAL-A1 or any later row as passed
based on this session's static analysis alone — no live re-run was
performed here, and this PR must not be merged until one is.

Every field/row below this point is still a placeholder. **Do not fill in
or check off any row from memory, assumption, or code-reading — only from
an actual observed run against a live Odoo 19 + PostgreSQL instance and a
Shopify development store**, per
[`task-003-manual-validation-checklist.md`](./task-003-manual-validation-checklist.md).

This document does not, and must not, assert that Task 003 validation has
passed. It becomes a real results record only once a tester fills it in
against a live environment; until then it is scaffolding plus the one
recorded VAL-A1 failure above.

---

## 1. Environment details

| Field | Value |
| --- | --- |
| Date executed | _TBD_ |
| Tester | _TBD_ |
| Odoo version/build | _TBD (e.g. Odoo 19.0 commit/tag)_ |
| Odoo install method | _TBD (source checkout / package / Docker — note if any container was introduced for this session only and is not committed to the repo)_ |
| PostgreSQL version | _TBD_ |
| Database name | _TBD (must be a disposable/test database, never a customer database)_ |
| `shopify_connector_core` module version installed | _TBD (expect `19.0.1.2.0` per PR #101)_ |
| Base commit validated | `e27f10e55f3504d1a9b8871a207b3d9762a3c783` (PR #101 merge commit) |
| Shopify development store used (handle/domain) | _TBD — must be a Partner development store, never a production shop_ |
| Shopify API version configured on the test store record | _TBD_ |
| Token type used | _TBD (e.g. custom-app offline access token, per Task 002's `token_variant='offline_custom_app'`)_ |
| Odoo test user role(s) used | _TBD (Admin / Operator / Auditor / Reviewer, per which VAL-Cx step)_ |

## 2. Test case results

Fill in one row per checklist item. Do not skip a row — if a step was not
reproducible, say so explicitly in **Actual result** and set **Pass/Fail** to
`N/A (not reproducible)`, not `Pass`.

| Test ID | Test case | Expected result | Actual result | Pass/Fail | Evidence reference |
| --- | --- | --- | --- | --- | --- |
| VAL-A1 | Clean install/upgrade | Installs/upgrades without error | **Failed (first attempt).** `Failed to load registry` / `ValueError: Invalid field 'category_id' in 'res.groups'` while loading `shopify_connector_security.xml`. **Re-run after PR #103 merged:** install progressed past registry load into Odoo 19 test execution, then **failed with 4 errors** — `ValueError: Invalid field 'groups_id' in 'res.users'` in `test_credential_access`, `test_credential_service`, `test_job_log_system_append`, and `test_test_connection`. **Re-run after PR #104 merged:** install and test loading reached all 36 tests, then **`2 failed, 3 error(s) of 36 tests`** — see the five-item summary in the Status section above and full detail in `odoo-19-runtime-test-failures.md`. **Re-run after PR #105 merged:** install and test loading reached all 39 tests, then **`1 failed, 4 error(s) of 39 tests`** — see the summary in the Status section above and full detail in `odoo-19-green-gate-failures.md`. | **Fail** | Blocked pending the green-gate hotfix (see `docs/01-research/research-handoff.md`, "Odoo 19 Green-Gate Hotfix" entry); must be re-run from a clean install after that PR is reviewed and a live run is performed — do not mark Pass from code-reading or from this session's static checks alone. |
| VAL-A2 | Model registry loads | `api.client` abstract (no table); other 3 models intact | _TBD_ | _TBD_ | _TBD_ |
| VAL-A3 | Three `job_type` values in ORM | Exactly 3 values, no 4th | _TBD_ | _TBD_ | _TBD_ |
| VAL-A4 | No XML/menu/action/wizard/controller/cron | Zero rows of any kind | _TBD_ | _TBD_ | _TBD_ |
| VAL-B1 | Invalid-token test | Fails, auth class, `credential_state='invalid'` | _TBD_ | _TBD_ | _TBD_ |
| VAL-B2 | Valid dev-store token test | Passes, mirrors + scopes populated | _TBD_ | _TBD_ | _TBD_ |
| VAL-B3 | Repeat run (idempotency/collision guard) | Second run succeeds, no unique-constraint collision | _TBD_ | _TBD_ | _TBD_ |
| VAL-B4 | Identity-mismatch behavior | Fails `odoo_validation_configuration`, `credential_state` untouched | _TBD_ | _TBD_ | _TBD_ |
| VAL-B5 | Shop-state failure behavior (if reproducible) | Auth class, distinct reason, `credential_state` untouched | _TBD_ | _TBD_ | _TBD_ |
| VAL-B6 | `credential_state` flips only on genuine token-invalid signal | Confirmed against B1/B4/B5 | _TBD_ | _TBD_ | _TBD_ |
| VAL-B7 | Version fall-forward warning (if reproducible) | Still `pass`; `api_health_state='degraded'` | _TBD_ | _TBD_ | _TBD_ |
| VAL-C1 | Token redaction (DB + server log) | Zero hits for either token | _TBD_ | _TBD_ | _TBD_ |
| VAL-C2 | `job.log` direct-create vs `_system_append` ACL check | Direct create → `AccessError`; indirect via `_system_append` → succeeds | _TBD_ | _TBD_ | _TBD_ |
| VAL-C3 | Exactly two `sudo()` sites (live-confirmed) | 2 sites, no more | _TBD_ | _TBD_ | _TBD_ |
| VAL-D1 | No Shopify-side mutation | Zero changes, zero webhooks | _TBD_ | _TBD_ | _TBD_ |
| VAL-D2 | No Odoo-side domain mutation | Zero domain-model changes | _TBD_ | _TBD_ | _TBD_ |
| VAL-E1 | Pass-path row accounting | 1 job row + 2 job.log rows | _TBD_ | _TBD_ | _TBD_ |
| VAL-E2 | Fail-path row accounting | 1 job row + 2 job.log rows | _TBD_ | _TBD_ | _TBD_ |
| VAL-E3 | No extra/missing rows | Confirmed across all runs | _TBD_ | _TBD_ | _TBD_ |
| VAL-F1 | `core_readiness_check` / TD-001 still collides | Second job for same store still collides | _TBD_ | _TBD_ | _TBD_ |

## 3. Empirical API behavior observed

Record only what was actually observed. Mark unreproduced items explicitly —
do not leave blank and do not assert an unobserved value.

| ID | Open question | Observed answer | Reproducible? | Evidence reference |
| --- | --- | --- | --- | --- |
| VAL-G1 | Actual HTTP status for an invalid/revoked token | _TBD_ | _TBD_ | _TBD_ |
| VAL-G2 | Actual `THROTTLED` response body shape | _TBD_ | _TBD_ | _TBD_ |
| VAL-G3 | Scopes required for `shop`/`currentAppInstallation` query | _TBD_ | _TBD_ | _TBD_ |
| VAL-G4 | Actual missing-scope error shape | _TBD_ | _TBD_ | _TBD_ |

## 4. Defects found

List every deviation from expected behavior found during this session. Do
**not** fix any of them in this session — record only. Each defect must be
routed by a future, separately scoped session either into
`technical-debt-register.md` (if accepted as a known trade-off) or into a
new bug-fix task (if it must be corrected before Task 004).

| ID | Area | Description | Severity | Suggested routing |
| --- | --- | --- | --- | --- |
| _None yet — fill in during execution, or write "None found" if the full checklist passes cleanly._ | | | | |

## 5. Go/No-Go recommendation

**Not yet determined — this section must not be filled in until every
applicable row in §2 has an actual result.** When completed, state plainly:

- **Recommendation:** _TBD (Go / No-Go / Go with conditions)_
- **Rationale:** _TBD — tie directly to the §2 results and §4 defects, not
  to code-reading alone._
- **Conditions (if "Go with conditions"):** _TBD_
- **Blocking defects (if "No-Go"):** _TBD — reference the §4 IDs._

## 6. Sign-off

| Role | Name | Date | Confirmation |
| --- | --- | --- | --- |
| Tester | _TBD_ | _TBD_ | Confirms every row in §2 reflects an actual observed run, not an assumption |
| Reviewer (ChatGPT, per `CLAUDE.md` §2) | _TBD_ | _TBD_ | Reviews this results record before any next feature-development session starts |
