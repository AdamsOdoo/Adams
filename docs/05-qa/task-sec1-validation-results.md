# Task SEC-1 — Validation Results

## Status

**Stage 4 implementation active on draft PR #172; exact-head Odoo.sh runtime pending.**

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

## Runtime evidence

**Pending.** Record build, database, Odoo version, exact tested SHA, addon
versions, command forms, tags/classes, counts, warnings/errors, residue/leak
checks, and failure ownership only after genuine Odoo.sh execution.
