# Task 003 — Manual Validation Results

## Status

**BLOCKED — VAL-A1 failed on first live install attempt; hotfix pending
review/merge.** Live validation was started against a live Odoo 19 +
PostgreSQL instance and failed immediately at VAL-A1 (clean install). The
observed `install.log` error:

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
`models.Constraint`. A hotfix addressing both is proposed on branch
`claude/odoo19-install-blocker-fnm5ro` (see
`docs/01-research/research-handoff.md`, "Odoo 19 Install-Compatibility
Hotfix" entry). **All live validation is blocked, and every row below
remains unexecuted, until that hotfix is reviewed/merged and VAL-A1 is
re-run from a clean state.**

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
| VAL-A1 | Clean install/upgrade | Installs/upgrades without error | **Failed.** `Failed to load registry` / `ValueError: Invalid field 'category_id' in 'res.groups'` while loading `shopify_connector_security.xml` (see Status section above for full log excerpt). | **Fail** | Blocked pending hotfix on `claude/odoo19-install-blocker-fnm5ro`; must be re-run from a clean install after that PR merges — do not mark Pass from code-reading. |
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
