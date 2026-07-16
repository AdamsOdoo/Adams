# Task SEC-1 — Validation Results

## Status

**SEC-1 binding-surface correction implemented and static-green; corrected
exact-head Odoo.sh revalidation is required before Wave 1 can return to
runtime-green. SRR-03 remains CLOSED.**

- **Branch:** `sol/wave-1-readonly-foundation`
- **PR:** #172 → `mvp/program-integration` (draft, open, unmerged)
- **Date:** 2026-07-16
- **Binding clarifications:** product-owner rulings PR #172 comments
  `4982429209`, `4982750956`, `4984719237`, `4988098888`, and consolidated
  mutation-surface ruling `4988842625`.
- **Current production correction:** `36974edc68c1985e6ccfae8f6bb5c7386f820156`
  (`fix(sec1): protect complete binding system surface`).
- **Runtime claim:** Build 34986844 remains valid for its exact prior code SHA
  `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723` only. It does not validate the
  new production correction.

## Consolidated binding mutation-surface correction

The complete current binding surface was inventoried before editing.

- **Class 1 — identity/structural:** `store_id`, `shopify_gid`, each
  concrete Odoo binding field, and variant `product_template_binding_id`.
- **Class 2 — system-maintained state/provenance/imported snapshot:**
  `status`, `match_key`, `matched_by_uid`, `matched_at`, `override_uid`,
  `override_at`, `override_previous_candidate`, and every Shopify snapshot/
  timestamp/checksum field declared by the three concrete bindings.
- **Class 3 — computed/non-stored:** customer `pii_snapshot_masked`.
- **Class 4 — intentionally user-editable configuration:** none.
- **ORM automatic metadata:** `id`, `display_name` and Odoo access-log fields
  remain framework-maintained and outside the connector mutation surface.

The mixin now unions the common protected set, the concrete
`_odoo_binding_field_name()`, and one reusable
`_additional_protected_binding_fields()` seam. Its classification assertion
fails closed if a protected name is unknown or any connector-owned stored
field is omitted. Generic non-su create/write/clear is denied for all protected
fields with error text covering identity, structure, system state, provenance,
and imported snapshots.

**Exact protected sets:**

- Product template (16): `store_id`, `shopify_gid`,
  `product_template_id`, `status`, `match_key`, `matched_by_uid`,
  `matched_at`, `override_uid`, `override_at`,
  `override_previous_candidate`, `shopify_title`, `shopify_status`,
  `shopify_primary_image_url`, `shopify_last_imported_at`,
  `shopify_updated_at`, `shopify_image_checksum`.
- Product variant (17): `store_id`, `shopify_gid`, `product_variant_id`,
  `status`, `match_key`, `matched_by_uid`, `matched_at`, `override_uid`,
  `override_at`, `override_previous_candidate`,
  `product_template_binding_id`, `shopify_option_values`,
  `shopify_price_snapshot`, `shopify_compare_at_price_snapshot`,
  `shopify_last_imported_at`, `shopify_primary_image_url`,
  `shopify_image_checksum`.
- Customer (14): `store_id`, `shopify_gid`, `partner_id`, `status`,
  `match_key`, `matched_by_uid`, `matched_at`, `override_uid`,
  `override_at`, `override_previous_candidate`, `shopify_display_name`,
  `shopify_email_snapshot`, `shopify_phone_snapshot`,
  `shopify_last_imported_at`.

**Legitimate writer inventory:** mixin `action_override_binding()`; product
template/variant importer create, refresh, stale/review, safe-refresh timestamp,
and image-ownership checksum sites; customer importer create/refresh sites;
manual PII mask; retention sweep. Customer importer and PII paths were already
sanctioned. Product importer adds only two exact-site elevations: existing
variant `snapshot_vals` refresh and post-image
`shopify_image_checksum` ownership update.

**Sudo delta:** core and sale production inventories are unchanged. Product
importer changes from 9 to 11 syntactic `.sudo(` sites, exactly the two
legitimate writers above. No context bypass, broad public-method elevation, ACL
change, group, model, table, job type, job source, transition, replay-policy,
or SRR-03 behavior changed.

**Static proof:** all nine changed Python implementation/test sources parse;
the concrete additional sets are exactly 6/7/4 fields; the product importer
contains one sudoed existing-variant snapshot refresh and one sudoed checksum
write, with no direct checksum assignment; exhaustive four-role tests cover
individual generic create/alter/clear for all 16/17/14 protected fields,
no-write/no-audit refusal, exact-set classification, fail-closed future
omission, sanctioned importer regressions, audited Reviewer/Admin override,
manual mask, and retention.

**Corrected-head runtime state:** pending. Required: targeted binding
protection, focused SEC-1/PII, product/customer binding and importer suites,
fresh install, full core/product/sale, lifecycle, combined SRR-03 smoke, clean
residue/security audit, and reversible issue #157 accommodation if needed.

## Final exact-head runtime evidence — build 34986844

> Historical exact-SHA evidence for the code before correction commit
> `36974edc68c1985e6ccfae8f6bb5c7386f820156`. The results below remain valid
> for `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723` and do not validate the new
> binding guard.

- **Database / Odoo:** `adamsmen-sol-wave-1-readonly-foundation-34986844`; Odoo 19.0.
- **Exact tested SHA:** `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723`, matched at session start and end; working tree clean.
- **Targeted AST:** `0 failed / 0 errors / 2`.
- **Fresh all-module:** `0 failed / 0 errors / 635`.
- **Full standard:** `0 failed / 0 errors / 635` (`core 352 + product 176 + sale 107`).
- **Combined SRR-03 smoke:** all 11 genuine classes `0 failed / 0 errors / 41`; 10 real PostgreSQL `40001` conflicts and one lock timeout exercised.
- **Residue/security:** clean, including zero connector test residue, leases, sessions, cursors, workers, idle transactions, or test cron triggers; no token/header/credential/raw-PII/temp-path leakage.
- **Issue #157 restoration:** the temporary `notification_type='email'` and `color_scheme='system'` database defaults were dropped and verified restored to their pre-run state; no NULLs introduced.

The test-only AST correction is runtime-green without any production change.
Build 34986844 completes the exact-head reconciliation authorized by ruling
`4988527547`. SEC-1 is runtime-green and **SRR-03 is CLOSED**. No
exactly-once remote-effect claim is made and DEC-031 Layer 2 remains
unimplemented. Wave 1 awaits only final Claude control-room review and merge;
PR #172 remains draft.

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
  customer importer 3 packet-owned binding writer elevations. After the
  consolidated correction, product importer is 11 (two exact additional
  protected writer sites) and customer importer remains 3. Exact-list
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
