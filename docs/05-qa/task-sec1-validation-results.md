# Task SEC-1 — Validation Results

## Status

**Odoo.sh build 34985521 validates the complete Wave 1 production behavior and substantive SRR-03 criteria at `d9d2dd018470054944db064cdd553160232713cd`; one test-only AST guard remained and is corrected at `b42042d641ce2d02cad9559a03fcb268ceaac3bc` pending final exact-head verification.**

- **Branch:** `sol/wave-1-readonly-foundation`
- **PR:** #172 → `mvp/program-integration` (draft, open, unmerged)
- **Date:** 2026-07-16
- **Binding clarifications:** product-owner rulings PR #172 comments `4982429209`, `4982750956`, `4984719237`, and accepted runtime ruling `4988098888`
- **Runtime claim:** Build 34985521 is accepted production/SRR-03 evidence for exact SHA `d9d2dd018470054944db064cdd553160232713cd`. Final Wave 1 success is not claimed until the test-only correction passes at the new exact head.

## Accepted exact-head runtime evidence — build 34985521

- **Database / Odoo:** `adamsmen-sol-wave-1-readonly-foundation-34985521`; Odoo 19.0.
- **Exact tested SHA:** `d9d2dd018470054944db064cdd553160232713cd`.
- **Fresh install:** `1 failed / 0 errors / 634 tests`; the only failure was `TestJobDispatch.test_source_level_job_enqueue_only_creates_job_model`, a stale test-only AST receiver helper.
- **Focused Wave 1:** `0 failed / 0 errors / 105 tests`.
- **Full domain suites:** product `0/0/176`; sale `0/0/107`.
- **Lifecycle:** `0/0/9`, including the accepted uninstall/reinstall behavior.
- **Issue #157:** the exact base-Odoo `notification_type`/`color_scheme` post-init fixture artifact was isolated only through the documented reversible database-default accommodation. No Wave 1 failure was classified under #157.
- **SRR-03:** all 11 genuine independent-connection classes passed in each of three distinct OS-process repetitions. The run exercised real PostgreSQL `40001` conflicts and lock timeouts and proved exact-job re-lock, zero handler replay, fail-closed replay policy, disconnect/admission ordering, and zero leaked leases, jobs, workers, sessions, cursors, or cron triggers.
- **Residue/security:** clean; no credential, token, header, raw PII, or temporary-path leakage.

Product-owner ruling `4988098888` accepts the substantive SRR-03 runtime
criteria as satisfied. The authoritative risk row remains **OPEN pending final
exact-head reconciliation only** because the fresh install retained the single
test-only AST failure.

### Test-only AST correction

Commit `b42042d641ce2d02cad9559a03fcb268ceaac3bc` changes only
`test_job_dispatch.py`. The helper recursively unwraps exactly `sudo`,
`with_context`, `with_company`, `with_user`, and `with_env`; arbitrary
wrappers still resolve to `None`. The production guard still appends every
resolved value (including `None`) and asserts the complete list equals exactly
`['shopify.connector.job']`.

Static verification: the changed Python file parses, and five focused helper
cases pass for bare access, `sudo()`, an approved chain, another model, and an
unapproved wrapper. No production, sudo behavior, transition, replay policy,
ACL, manifest, migration, or lifecycle behavior changed. No final Wave 1
success or SRR-03 closure is claimed before the corrected exact-head rerun.

## Binding product-owner clarification

The accepted SEC-1 implementation uses only the current model surface:

1. **Audit carrier:** reuse
   `shopify.connector.store._create_lifecycle_audit_job(message)`.
   SEC-1 narrowly elevates only that helper's protected job
   `create()`/`write()` sites. The helper remains on the caller's Store
   environment so `shopify.connector.job.log._system_append()` records the
   original caller as `actor_uid`.
2. **Atomicity:** each binding override or manual PII mask performs its
   protected mutation first and calls the audit helper afterward in the same
   transaction. Any audit failure therefore rolls the mutation back. A
   retention sweep creates exactly one summary carrier/log for each affected
   store.
3. **Audit content:** identifiers, counts, actor id, and mandatory reason only.
   No raw email, phone, name, token, header, credential, or payload value.
4. **Company rule:** no store company field is added. Current and proposed
   bound records are resolved before sudo in the fixed comodel. Any non-empty
   `company_id` must equal `env.company`; when both are non-empty they must
   equal each other. Company-neutral records remain valid. No caller-supplied
   model or company argument exists.

No new model, table, job type, job source, branch, PR, or governance session is
authorized or introduced by this clarification.

## Required evidence matrix

The final Stage 4 record must include:

- all four roles × direct protected job and binding field mutations;
- `original_job_type` and `cancel_reason` denial for every role;
- create-time anti-spoof and every sanctioned dispatcher/enqueue/readiness/
  store/lifecycle/JOB-ACTIONS writer;
- LC-1 historic conversion after SEC-1;
- exhaustive legal/illegal job transitions;
- binding override same-company and company-neutral success;
- current-record and target-record company mismatch refusal with no write/audit;
- fixed-comodel, malformed/nonexistent id, uniqueness, reason, and role checks;
- exactly one audit carrier/log per binding override or manual PII mask;
- exactly one summary carrier/log per affected store per retention sweep;
- correct original `actor_uid`, redacted identifier/count/reason-only messages,
  and no orphan logs;
- atomic rollback when audit creation fails;
- PII field visibility and masked-display matrix for all roles;
- retention masking, append-only preservation, and no raw PII leakage;
- full core/product/sale regressions and exact sudo inventory.

## Static implementation evidence

- **Implementation commit:** `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5`
  (`feat(sec1): enforce protected mutations and PII controls`).
- **Scope:** 32 packet-owned addon/test files; no ACL CSV, credential model,
  UI, order, Area 6, inventory, fulfillment, export, or Layer 2 file changed.
- **Syntax:** all 31 Python files in the Stage 4 change map parsed
  successfully with Python `ast.parse`; the new cron XML parsed successfully
  with `xml.etree.ElementTree`.
- **Focused test inventory:** 9 core security methods and 12 sale/PII methods,
  plus the three existing binding ACL matrices and the inherited
  JOB-ACTIONS/LC-1/dispatcher/readiness/credential/log guards.
- **Exact core sudo inventory (AST):** binding mixin 1; job 8; job actions 2;
  dispatcher 2; enqueue 1; PII retention 5; readiness 3; store 8; plus the
  inherited job-log 1 and credential 1 sites. The product importer has 9 and
  customer importer 3 packet-owned binding writer elevations. Exact-list
  source guards were updated; no context-flag bypass was introduced.
- **Ruling proof encoded:** `original_job_type` and `cancel_reason` are in
  the server-side protected set and four-role denial matrix; create-time
  `original_job_type` anti-spoof remains; LC-1 historic conversion and all
  sanctioned writers have regressions. Binding override tests cover
  same-company, company-neutral, both mismatch directions, malformed/missing/
  colliding targets, non-overridable seams, no-write/no-audit refusal,
  one-carrier actor/redaction proof, and rollback on audit failure. Manual
  masking and per-store sweeps carry equivalent count/actor/atomicity checks.
- **Boundary scan:** the store model gained no `company_id`; the override
  signature accepts neither a model nor company argument; `env.companies`
  and `create_uid.company_id` are absent. Audit calls reuse only
  `_create_lifecycle_audit_job()`; no audit table/job type/job source was
  added.

These are source/static checks, not Odoo runtime results.

## Runtime evidence

### Odoo.sh diagnostic run — build 34968318 (pre-correction)

- **Database:** `adamsmen-sol-wave-1-readonly-foundation-34968318`
- **Odoo:** 19.0
- **Branch / PR:** `sol/wave-1-readonly-foundation`; draft PR #172
- **Exact tested SHA:** `62b2645f69280aadc68a56045a26bef2063c5821`
- **Module versions:** core `19.0.1.9.0`; product `19.0.2.1.1`; sale `19.0.1.2.0`
- **Upgrade:** completed without runtime errors.
- **Fresh install:** stopped with five transition-related errors after 198 tests; this is not a passing fresh-install result.
- **Focused after the database-only issue #157 accommodation:** CORE-R1 `0 failed / 0 errors / 20`; LC-1 `0/0/9`; JOB-ACTIONS `0/0/9`; SEC-1 core `0/0/9`; PII `0/0/12`.
- **Full suites:** core initially `4 failed / 19 errors / 495`, then `4 failed / 11 errors / 346` after the database-only issue #157 accommodation (15 Wave-1-owned transition failures); product `0 failed / 1 error / 176` (Wave-1-owned transition fixture); sale `0 failed / 2 errors / 95` (one exact issue #157 fixture artifact and one Wave-1-owned transition fixture).
- **Lifecycle:** domain uninstall/reinstall passed.
- **Genuine SRR-03 classes:** `TestGenuineRealAdmission` `0/0/9` ×3 and `TestLifecycleAdmissionRaceGenuine` `0/0/4` ×3 passed; `TestDrainOwnershipReplayGenuine` deterministically failed `1 failed / 4 errors / 6` ×3, and the scheduled-drain case in `TestLifecycleServiceRetryGenuine` failed, because the recovery route attempted state edges omitted by D-SEC1-1.
- **Residue/leak scan:** clean for the completed diagnostic run.
- **Security/log scan:** clean; no credential, token, header, raw PII, or temporary-path leakage was found.
- **Issue #157:** only the exact known `res.users.notification_type` / `color_scheme` post-init test-fixture artifact was accommodated at database level. No new failure was classified under #157.

### Runtime-discovered regression and correction

A genuine PostgreSQL concurrency failure rolls back the original transaction,
including the uncommitted `running` write. CORE-R2 recovery correctly re-locks
the exact job in its committed claimable state (`queued` or due
`retry_waiting`) and routes without replaying the handler. SEC-1's matrix
incorrectly rejected the resulting production recovery states.

Correction commit `2b6d9d8259fada252abca19407d1df53bed9e66f` adds only:

- `queued→retry_waiting|failed_final|blocked_manual_review`;
- `retry_waiting→failed_final|blocked_manual_review`.

It leaves `draft→running` and `draft→retry_waiting` illegal, changes no
replay-policy classification or dispatcher architecture, and adds queued/due
retry recovery coverage for budget remaining, exhaustion, conservative and
undeclared policy, exact-row re-locking, and zero handler replay. Inherited
core/product/sale fixtures now use valid claimable states or controlled
superuser setup for an explicitly later state.

### Pre-push correction checks

All seven changed Python sources parsed successfully. Source guards prove the
transition delta is exactly the five approved edges, production `sudo()` and
bypass-marker inventories are unchanged, the recovery method still calls
`Job.browse(job_id).try_lock_for_update()`, replay policy remains checked, and
the recovery body contains no handler invocation.

**No post-correction Odoo.sh runtime success is claimed.** SRR-03 remains OPEN.
The next required action is another Odoo.sh 19 run at the new exact PR head,
including the complete Wave 1 matrix and the required genuine repetitions.
