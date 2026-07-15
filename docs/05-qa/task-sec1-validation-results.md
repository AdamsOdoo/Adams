# Task SEC-1 — Validation Results

## Status

**Stage 4 implementation is pushed on draft PR #172; exact-head Odoo.sh runtime is blocked by unavailable access.**

- **Branch:** `sol/wave-1-readonly-foundation`
- **PR:** #172 → `mvp/program-integration` (draft, open, unmerged)
- **Date:** 2026-07-15
- **Binding clarifications:** product-owner ruling PR #172 comment `4982750956`
- **Runtime claim:** None yet. Static/source checks and eventual Odoo.sh results are recorded separately and never conflated.

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

**NOT EXECUTED — hard-stop 5.** The connected GitHub status list and workflow
run list for implementation commit `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5`
were both empty. This execution environment has no `odoo` or `odoo-bin`
command and `import odoo` raises `ModuleNotFoundError`; no authenticated
Odoo.sh control surface or database/build credential is available. Therefore
no build number, database, Odoo version, install/upgrade command result, Odoo
test count, concurrency repetition, residue audit, session/cursor/worker
audit, or credential/PII log scan is claimed.

The exact unvalidated Stage 4 code SHA is
`60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5`. SRR-03 remains OPEN and
Stage 5 closure proof is unstarted. Resume only in a genuine Odoo.sh 19 dev
build checked out at the exact final Wave 1 head; execute the complete matrix
from the Wave 1 plan and record every result here before any completion claim.
