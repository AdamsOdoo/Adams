# Task JOB-ACTIONS — Validation Results

## Status

**Implementation complete on draft PR #172; exact-head Odoo.sh runtime pending.**

- **Branch:** `sol/wave-1-readonly-foundation`
- **PR:** #172 → `mvp/program-integration` (draft, unmerged)
- **Stage:** Wave 1 Stage 3
- **Date:** 2026-07-15
- **Runtime claim:** None. No Odoo runtime is available in this execution environment; the required Odoo.sh run remains open.

## Scope implemented

D-JA-1 is implemented as the packet's additive `shopify.connector.job`
extension:

- `action_manual_retry()` accepts only
  `failed_retryable`/`failed_final`/`blocked_manual_review`/`skipped`,
  re-queues the job, resets `retry_count` to zero, clears the incompatible
  manual-review subreason, and appends exactly one `manual_action` audit row.
- blocked-review retry requires Reviewer or Administrator; the other retry
  states require Operator or Administrator.
- `action_cancel(reason)` accepts only
  `draft`/`queued`/`running`/`retry_waiting`, requires a non-empty
  reason, stores it, finishes the job as `cancelled`, and appends exactly one
  `manual_action` audit row.
- neither method exposes a force/bypass parameter.
- this stage contains no `sudo()`; SEC-1 owns the already-reserved elevation
  at these two write sites.

No Area 6 scan, cron, enumeration, domain manual-sync, Task 012, UI,
inventory, fulfillment, product-export, or DEC-031 Layer 2 work is present.

## Focused matrix

`test_job_actions.py` contains nine test methods covering:

1. manual retry from all four allowed states, retry budget reset, and exact audit;
2. blocked-review Reviewer/Admin boundary and Operator denial;
3. non-blocked Operator/Admin boundary and Auditor/Reviewer denial;
4. illegal retry states with no write or audit residue;
5. cancellation from all four allowed states with stored reason and exact audit;
6. missing, false, non-string, and whitespace-only reason denial;
7. Auditor/Reviewer cancellation denial and Administrator success;
8. terminal/recovery-state cancellation denial with no write;
9. source-level public-method, signature, and pre-SEC-1 no-`sudo` guards.

## Executed checks

| Check | Command/form | Result |
| --- | --- | --- |
| Model syntax | Python `compile(..., 'exec')` against the complete new model source | PASS |
| Test syntax | Python `compile(..., 'exec')` against the complete new test source | PASS |
| Packet scope | Manual path/line inventory against §5 allowlist | PASS |
| Forbidden core edit | `shopify_connector_job.py` unchanged by Stage 3 | PASS |
| Live Shopify calls | New model has no API-client or transport reference | PASS by source inspection |
| Odoo.sh focused runtime | `--test-tags /shopify_connector_core:TestJobActions` | **PENDING** |
| Full core/product/sale runtime | exact-head Odoo.sh matrix | **PENDING** |

## Required exact-head Odoo.sh proof

At the final Wave 1 runtime gate, record the build number, database, Odoo
version, exact checked-out SHA, addon versions, command forms, test tags, test
counts, warning/error classification, and residue/leak scan. The focused
JOB-ACTIONS suite and full inherited suites must be green before Wave 1 can be
claimed complete.

## Rollback

Revert the Stage 3 JOB-ACTIONS commit series: remove the new model/test files,
their two import lines, the validation/AR/handoff entries, and restore the core
version. This stage adds no field or migration. Jobs already manually retried
or cancelled retain their audited state, which is equivalent to other
sanctioned lifecycle state changes and requires no destructive rollback.
