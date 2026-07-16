# Task LC-1 — Lifecycle / Uninstall Validation Results

> **Wave 1 Stage 2 implementation record — PR #172, 2026-07-15.**
> DEC-030 and the locked lifecycle design are binding. This record does not
> LC-1 runtime proof was obtained on Odoo.sh build `34986844`. A later SEC-1
> binding-surface correction changes no LC-1 production path but requires the
> final Wave 1 exact-head lifecycle regression to be repeated.

## Scope implemented

- Permanent core `historic_domain_job` sink.
- Indexed, readonly, set-once `original_job_type`, filled from the effective
  creation `job_type` and protected from a forged create value.
- Idempotent `19.0.1.8.0` post-migration backfill for pre-existing rows.
- `_reassign_to_historic_job_type()`: non-terminal jobs cancel with one
  `manual_action` audit row before retyping; terminal jobs only retype; job
  logs are never removed.
- Product/customer selection-removal callables use the core historic converter.
- Dispatcher rejects any malformed non-terminal historic job.
- The LC-1 stage originally advanced core/product/sale to `19.0.1.8.0`,
  `19.0.2.1.0`, and `19.0.1.1.0`. The current corrected Wave 1 manifests are
  `19.0.1.9.1`, `19.0.2.1.2`, and `19.0.1.2.1` after the subsequent
  JOB-ACTIONS/SEC-1 stages and consolidated security correction.

## Data-survival posture

Disable-first remains the supported operational path and preserves everything.
Supported physical domain uninstall preserves Odoo business records and all
core job/log history. Domain-owned binding/mapping tables follow Odoo module
uninstall semantics and are therefore export/re-derive data, as DEC-030 states;
LC-1 does not falsely claim those tables survive. Core uninstall remains full
connector removal.

No business-data `ondelete='restrict'` link or append-only job-log posture is
changed. No destructive migration exists.

## Focused tests authored

`test_lifecycle_uninstall.py` covers original-type creation/anti-forgery,
terminal history preservation, every non-terminal cancellation class, audit
cardinality/actor/from→to, idempotent conversion, fail-closed dispatch, both
domain `selection_add ondelete` registrations, additive/idempotent migration
source, and no unlink/sudo in the conversion method.

The exact-head Odoo.sh matrix must additionally run:

1. fresh core/product/sale install;
2. upgrade from the inherited baseline and SQL verification that every
   pre-existing job has `original_job_type`;
3. disable-first proof;
4. product and sale uninstall-after-use, with business/core history assertions;
5. reinstall plus deterministic product/customer binding re-derivation;
6. full core/product/sale regressions and zero-residue audit.

## Static validation

The changed Python sources were syntax/AST reviewed in-session. Odoo
`TransactionCase`, registry upgrade, and physical uninstall/reinstall were not
executed in this environment; no local Odoo runtime is available. They remain
owned by the exact-head Odoo.sh gate.

## Rollback

Revert the Stage 2 commits. Restore the two domain `ondelete` values and prior
manifest versions; remove the conversion/dispatcher code and test import. Leave
the additive column and historic selection metadata inert if already applied;
do not drop schema. Never delete business records, jobs, or logs during rollback.

## Runtime result

**Prior LC-1 runtime GREEN:** Odoo.sh 19 build `34986844` at exact prior code
SHA `05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723` passed lifecycle `0/0/9`,
fresh all-module `0/0/635`, and standard `0/0/635`, with clean residue.
Install/uninstall/reinstall behavior was included in the accepted matrix.

**Current corrected-head status:** revalidation pending after production
correction `36974edc68c1985e6ccfae8f6bb5c7386f820156`. The correction touches
binding guards/importer writer elevation only; it does not alter historic-job
conversion, selection `ondelete`, job/log history, or lifecycle architecture.
