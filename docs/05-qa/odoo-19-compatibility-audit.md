# Odoo 19 Compatibility Audit — `shopify_connector_core`

**Date:** 2026-07-07
**Scope:** Entire `addons/shopify_connector_core/` module (models, security,
tests, tools, manifest) — not limited to the four test classes that
surfaced in the last live-validation failure.
**Trigger:** After PR #103 fixed the `res.groups.category_id` /
`_sql_constraints` install blocker, a re-run of live validation reached
Odoo 19 test execution and then failed with `ValueError: Invalid field
'groups_id' in 'res.users'` in four test classes. Rather than patch only
those four call sites, this audit checks the whole module for sibling
Odoo 19 breaking-change patterns of the same class, so a third live-run
failure doesn't surface one file at a time.
**Method:** Static source audit only (`grep`/`Read` over the full module
tree plus `docs/`), cross-checked against the two Odoo 19 breaking changes
already confirmed this sprint (`res.groups.category_id` → `privilege_id`;
`_sql_constraints` → `models.Constraint`) and the newly confirmed
`res.users.groups_id` → `group_ids` rename. No Odoo 19 runtime is available
in this environment (see "Runtime validation" below) — every finding below
is a **Fact** (directly observed in source, with file:line citations), not
an inference from documentation.

---

## 1. Patterns searched and results

| # | Pattern searched | Where searched | Matches found | Classification |
| --- | --- | --- | --- | --- |
| 1 | `groups_id` | entire `addons/shopify_connector_core/` tree | **0** (after this session's fix; previously 4, one per affected test file — see §2) | Fixed |
| 2 | `category_id` | entire `addons/shopify_connector_core/` tree | 1: `security/shopify_connector_security.xml:12`, on the `res.groups.privilege` record `privilege_shopify_connector` | Safe — correct Odoo 19 usage, not on `res.groups` |
| 3 | `_sql_constraints` | entire `addons/shopify_connector_core/` tree | **0** | Safe — already converted to `models.Constraint` by PR #103 |
| 4 | old `res.groups` category assignment (i.e. `category_id` set directly on a `res.groups` record) | `security/shopify_connector_security.xml` | **0** — all four `res.groups` records (`group_shopify_connector_auditor/_operator/_reviewer/_admin`) use `privilege_id`, not `category_id` (lines 15–36) | Safe |
| 5 | direct `res.users.create` with group assignment | entire `addons/shopify_connector_core/` tree | 4, all in `tests/`: `test_credential_access.py:31`, `test_credential_service.py:37`, `test_job_log_system_append.py:27`, `test_test_connection.py:29` | Fixed by this PR (all now use `group_ids`) |
| 6 | other `res.users`/`res.groups`-related M2M command tuples (`(6, 0, [...])`) | entire `addons/shopify_connector_core/` tree | Same 4 sites as #5 | Fixed — no other command-tuple site exists |
| 7 | test helpers that create users | `tests/` directory | Only the four `_create_group_user` classmethods in the four already-listed files; `test_api_client.py` and `test_redaction.py` create no users and reference neither `res.users` nor `group` (confirmed via direct grep, zero matches in either file) | Safe — no additional test helper needs the same fix |
| 8 | deprecated ORM patterns of the same visible class (`@api.one`, `@api.multi`, `@api.cr`, `osv.`, `orm.Model`, `fields.function`, `track_visibility`, `_inherits`) | entire `addons/shopify_connector_core/` tree | **0** | Safe — no sibling deprecated-API risk found |
| 9 | other `.sudo()` call sites | entire `addons/shopify_connector_core/` tree | 2, both pre-existing and unchanged: `models/shopify_connector_store_credential.py:158` (`_get_access_token`) and `models/shopify_connector_job_log.py:79` (`_system_append`); `tests/test_credential_service.py:178` is a comment referencing `sudo(...)`, not a call site | Safe — matches the exact count the module's own `test_source_level_sanctioned_sudo_sites_guard` / `test_source_level_two_sudo_sites_total` tests assert; unchanged by this session |
| 10 | docs/comments still referring to obsolete fields | `addons/shopify_connector_core/` (inline comments) and `docs/` (repo-wide) | Inline comments in the module: **0** stale references. `docs/01-research/research-handoff.md` and `docs/05-qa/task-003-validation-results.md` reference `groups_id`/`category_id` only in **historical/root-cause narrative** describing the now-fixed failures, not as current guidance | Safe — no doc misleads a future reader into re-introducing the obsolete field names |
| 11 | `res.users`-typed `Many2one` fields in production models (checked for any hidden group-assignment coupling) | `models/shopify_connector_binding_mixin.py:47,49` (`matched_by_uid`, `override_uid`), `models/shopify_connector_job_log.py:51` (`actor_uid`) | 3 — all plain `Many2one(comodel_name='res.users', ...)` FK references, none touch `groups_id`/`group_ids` | Safe — unaffected by the Odoo 19 rename, no change needed |
| 12 | ACL CSV `group_id:id` column | `security/ir.model.access.csv` | Present on all 20 rows, referencing the four `res.groups` XML IDs | Safe — this is the unrelated, still-valid `ir.model.access.group_id` field; not the `res.users.groups_id` field renamed in Odoo 19, no change needed or made |

## 2. Exact fix applied (from the F1 groups_id → group_ids hotfix)

Four occurrences, one per file, each inside the shared `_create_group_user`
test-only classmethod:

```diff
-            'groups_id': [(6, 0, [group.id])],
+            'group_ids': [(6, 0, [group.id])],
```

in:

- `addons/shopify_connector_core/tests/test_credential_access.py:34`
- `addons/shopify_connector_core/tests/test_credential_service.py:40`
- `addons/shopify_connector_core/tests/test_job_log_system_append.py:30`
- `addons/shopify_connector_core/tests/test_test_connection.py:32`

No other line in any of these files changed. Same group XML IDs, same `(6,
0, [group.id])` command, same test users, same test intent, in all four
cases.

## 3. Confirmations (source-level, this audit)

- No `groups_id` remains anywhere under `addons/shopify_connector_core/`
  (module-wide grep, zero hits — see §1 row 1).
- `group_ids` is used in all four affected test helpers (§1 row 5).
- No `category_id` remains on any `res.groups` record (§1 row 4).
- `category_id` remains only on the `res.groups.privilege` record
  `privilege_shopify_connector` (§1 row 2 / row 4).
- No `_sql_constraints` remains under
  `addons/shopify_connector_core/models/` (§1 row 3).
- `models.Constraint` remains in place for all six constraints converted by
  PR #103 (`shopify_connector_location.py:27`, `shopify_connector_store.py:81`,
  `shopify_connector_store_settings.py:42`,
  `shopify_connector_store_credential.py:63`,
  `shopify_connector_job.py:154,158`) — none reverted, none added or removed
  by this session.
- No production connector behavior changed — the only non-doc files in this
  PR's diff are the four test files, each with exactly one dict-key rename
  (verified via `git diff --numstat`, §5).
- No security/ACL widening — `security/shopify_connector_security.xml` and
  `security/ir.model.access.csv` are untouched by this PR (not in the
  changed-files list).
- No Task 004 work performed or started.

## 4. Test integrity regression

- No test class removed: class count in each of the four files is
  identical before/after (`grep -c "^class "` = 1/1 in all four files).
- No test method skipped: `def test_` counts identical before/after in all
  four files (4/4, 11/11, 4/4, 9/9) and no `skip`/`Skip` decorator is
  present in any of the four files.
- No assertion removed or weakened: `self.assert*` counts identical
  before/after in all four files (10/10, 33/33, 12/12, 31/31).
- No `assertRaises` block removed: counts identical before/after in all
  four files (7/7, 6/6, 1/1, 2/2).
- No `sudo()` workaround added to bypass the user/group failure: `.sudo()`
  call-site count in the whole module is unchanged at 2 (§1 row 9); zero
  new `.sudo()` sites in any test file.
- Test users still use the intended Shopify-connector group in every case:
  each `_create_group_user` call site still resolves its group via
  `cls.env.ref('shopify_connector_core.%s' % group_xmlid)` and assigns it
  with the same `(6, 0, [group.id])` command — only the target field name
  changed to match the Odoo 19 `res.users` API.

## 5. Production non-regression

- No API client file changed: `models/shopify_connector_api_client.py` not
  in this PR's diff.
- No credential production model/service file changed:
  `models/shopify_connector_store_credential.py` not in this PR's diff.
- No job/job_log production behavior changed:
  `models/shopify_connector_job.py` and `models/shopify_connector_job_log.py`
  not in this PR's diff.
- No `action_test_connection()` behavior changed: defined in
  `models/shopify_connector_store.py:86`, file not in this PR's diff.
- No `_system_append()` behavior changed: defined in
  `models/shopify_connector_job_log.py:60`, file not in this PR's diff.
- No Shopify API behavior changed: `models/shopify_connector_api_client.py`
  not in this PR's diff, and no test file's mocked-response fixtures
  (`FakeResponse`, `_success_body` in `test_api_client.py`) were touched.
- TD-001 (`docs/05-qa/technical-debt-register.md`, `core_readiness_check`
  idempotency-key collision) remains **Open** and untouched — the register
  entry is unchanged by this PR and `models/shopify_connector_job.py` is not
  in this PR's diff.

## 6. Runtime validation

**Not performed.** No Odoo 19 runtime or PostgreSQL instance exists in this
sandboxed environment. Everything in this audit is a static source-level
check (`grep` over the full module tree plus `docs/`, and `python3 -m
py_compile` over every `.py` file in the module — all compile cleanly,
including files this PR did not change). The tester must re-run the live
Odoo 19 install + test-execution command for `shopify_connector_core` after
this PR merges and confirm:

1. `ValueError: Invalid field 'groups_id' in 'res.users'` no longer occurs
   in `test_credential_access`, `test_credential_service`,
   `test_job_log_system_append`, or `test_test_connection`.
2. No other error surfaces from a pattern this static audit could have
   missed (e.g. a runtime-only Odoo 19 behavior change not visible from
   source). Any such new error must be recorded separately in
   `docs/05-qa/task-003-validation-results.md` and **not** silently folded
   into or fixed under this same PR without ChatGPT authorization.

Do not treat this document, or the static checks in §1–§5, as a substitute
for that live re-run. `docs/05-qa/task-003-validation-results.md` continues
to record every row as unpassed pending that re-run.

## 7. Conclusion

Beyond the four already-identified `groups_id` → `group_ids` call sites
(now fixed), no sibling Odoo 19 compatibility risk was found anywhere else
in `addons/shopify_connector_core/` at the source level — no other
`category_id`-on-`res.groups`, `_sql_constraints`, deprecated-decorator, or
stale-field-reference pattern exists in the module. This audit is a static
finding, not a substitute for the live re-run required in §6.
