# Task JOB-ACTIONS — Validation Results

## Status

**Implementation complete and runtime-green: first on build `34986844`
(pre-SEC-1), then again at the corrected head on build `34995642`
(runtime-tested SHA `95db3db`) after the SEC-1 binding-surface correction.**

- **Branch:** `sol/wave-1-readonly-foundation`
- **PR:** #172 → `mvp/program-integration` (draft, unmerged)
- **Stage:** Wave 1 Stage 3
- **Date:** 2026-07-15; corrected-head evidence and this reconciliation note
  added 2026-07-16.
- **Runtime claim:** Prior exact-SHA JOB-ACTIONS evidence is green, and the
  corrected head has since run green (`TestJobActions` (9), part of the full
  `0/0/644` standard suite recorded in `task-sec1-validation-results.md`,
  build `34995642`).
- **Doc-accuracy correction (2026-07-16, control-room docs-only fix):** the
  "Scope implemented" and "Focused matrix" sections below previously stated
  this stage contains no `sudo()`. That was accurate only for JOB-ACTIONS'
  original Stage 3 commit; SEC-1 commit `60ac4165a0fa9babc070f892bfdeb6dc0a2e48b5`
  subsequently added `self.sudo().write(...)` to both `action_manual_retry()`
  and `action_cancel()` (the two write sites this stage always reserved for
  SEC-1's elevation), and this file's own item-9 test was renamed accordingly
  to assert exactly two `sudo()` sites are present. The text below is
  corrected to state the current, accurate mechanism; no code or test
  changed.

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
- this stage's original Stage 3 commit contained no `sudo()`; SEC-1 has since
  added `self.sudo().write(...)` to both write sites (`action_manual_retry()`
  and `action_cancel()`), the elevation this stage always reserved for SEC-1.
  This is the current, shipped state at the reviewed PR head.

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
9. source-level public-method, signature, and exact-sudo-inventory guards
   (originally a no-`sudo` guard at Stage 3; renamed and re-scoped by SEC-1
   to assert exactly the two sanctioned `sudo()` sites now present).

## Executed checks

| Check | Command/form | Result |
| --- | --- | --- |
| Model syntax | Python `compile(..., 'exec')` against the complete new model source | PASS |
| Test syntax | Python `compile(..., 'exec')` against the complete new test source | PASS |
| Packet scope | Manual path/line inventory against §5 allowlist | PASS |
| Forbidden core edit | `shopify_connector_job.py` unchanged by Stage 3 | PASS |
| Live Shopify calls | New model has no API-client or transport reference | PASS by source inspection |
| Odoo.sh focused runtime | `--test-tags /shopify_connector_core:TestJobActions` | **GREEN on build 34986844; corrected-head repeat GREEN on build 34995642** |
| Full core/product/sale runtime | exact-head Odoo.sh matrix | **GREEN `0/0/635` on build 34986844; corrected-head repeat GREEN `0/0/644` on build 34995642** |

## Required exact-head Odoo.sh proof

At the final Wave 1 runtime gate, record the build number, database, Odoo
version, exact checked-out SHA, addon versions, command forms, test tags, test
counts, warning/error classification, and residue/leak scan. The focused
JOB-ACTIONS suite and full inherited suites must be green before Wave 1 can be
claimed complete.

Prior exact-SHA evidence: Odoo.sh 19 build `34986844` at
`05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723` passed the full standard matrix
`0/0/635` and the Wave 1 focused suites. Production correction
`36974edc68c1985e6ccfae8f6bb5c7386f820156` changes no JOB-ACTIONS method,
state vocabulary, transition, role, or reason behavior (it does add the
`self.sudo()` elevation on both write sites described above, and correspondingly
extends the per-write audit-carrier behavior's execution context to sudo — the
audit content/atomicity contract itself is unchanged). The corrected-head
repeat ran on build `34995642` (runtime-tested SHA `95db3db`): `TestJobActions`
(9) green as part of the full `0 failed / 0 errors / 644` standard suite; see
`task-sec1-validation-results.md` for the authoritative evidence record.

## Rollback

Revert the Stage 3 JOB-ACTIONS commit series: remove the new model/test files,
their two import lines, the validation/AR/handoff entries, and restore the core
version. This stage adds no field or migration. Jobs already manually retried
or cancelled retain their audited state, which is equivalent to other
sanctioned lifecycle state changes and requires no destructive rollback.
