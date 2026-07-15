# Task JOB-ACTIONS — Generic Job-Control Services (`action_manual_retry` / `action_cancel`): Implementation-Ready Planning Packet

> **Status: Accepted for Wave 1 Stage 3 implementation under DEC-034.**
> Implementation gate opened; prerequisite is successful completion of
> Task LC-1 (Wave 1 Stage 2) on the same Wave 1 branch. The locked
> prompt in §9 may be used only inside the authorized Wave 1 Sol
> mission, against the verified live `mvp/program-integration` tip.
> Produced 2026-07-15 by the Claude
> control-room Wave 1 packet-reconciliation session, resolving conflict
> finding 1 of Sol's Wave 1 hard-stop (issue #167 comment `4980808811`)
> per [`DEC-034`](../04-decisions/DEC-034-wave-1-packet-dependency-reconciliation.md).
> **Extraction, not new design:** this packet extracts decision D-A6-5
> — "Job-control services (retry/cancel/requeue)" — verbatim from
> `area-6-sync-triggers-implementation-packet.md` §2 (2026-07-11 text,
> unchanged in substance) into its own independently gated, generic,
> core-owned Wave 1 task, exactly as Area 6's own §3 already flagged:
> *"job-control services are generic and belong to core... an
> explicitly-named additive core exception for generic operator
> services, consistent with core owning the job substrate. Flagged for
> ChatGPT."* This packet is that flag being resolved. Sequenced in Wave
> 1 **after Task LC-1, before Task SEC-1**
> (`mvp-completion-program.md` §4, as corrected by DEC-034).

## 1. Why this must be its own task (not Area 6, not folded into SEC-1)

Sol's hard-stop (conflict 1) found that `task-sec1-security-hardening-packet.md`
names `action_manual_retry()`/`action_cancel()` as sanctioned doors
(D-SEC1-3) but requires "Area 6 merged runtime-green" as its own
prerequisite (§7 gate criterion 1, §9 locked prompt) — and Area 6 (scan
jobs, crons, domain manual-sync services, order-scan) is explicitly
Wave 2+ scope gated on Task 012 merging
(`mvp-completion-program.md` §4 Wave 2). Absorbing all of Area 6 into
Wave 1 to satisfy SEC-1 would violate Wave 1 scope; absorbing none of
it would leave SEC-1 unable to name real sanctioned methods. Verified
against the live baseline (2026-07-15): `git grep` across
`addons/**/*.py` for `action_manual_retry`, `action_cancel`, and
`action_resolve_manual_review` returns **zero matches** — none of the
three exists anywhere in the current tree.

The resolution: **only D-A6-5 — the two generic job-control methods —
is extracted into Wave 1**, exactly as this stage's own packet already
names it as a self-contained "additive core exception." Everything
else Area 6 owns (D-A6-2 scan jobs, D-A6-3 crons, D-A6-4 manual
domain-sync services, D-A6-6 progress counters, order/product/customer
enumeration of any kind) **stays in Area 6, stays Wave 2+, and is not
authorized by this packet.**

## 2. Objective, scope, non-goals

Implement, in core, the two generic operator job-control actions —
`action_manual_retry()` and `action_cancel()` — as a pure additive
`_inherit` extension of `shopify.connector.job`, using the **current**
merged write-gate mechanism (no su-elevation; none is required yet,
since Task SEC-1's protected-field guard has not landed at this
stage's implementation time), and **forward-compatible** with the
already-specified SEC-1 D-SEC1-1 legal-transition matrix and D-SEC1-3
sanctioned-methods list, so that when SEC-1 lands next it only adds
su-elevation to these two methods' existing write sites — it does not
redesign them.

**Non-goals:** no scan jobs, crons, enumeration, checkpoints, or any
other Area-6 domain-trigger scope; no `action_resolve_manual_review`
(that is SEC-1's own new method, D-SEC1-3, requiring the protected-field
guard this stage does not yet have — implementing it here would give it
no su-elevation and leave a live gap); no UI; no change to the
dispatcher, retry-scheduling constants, or error taxonomy; no new ACL
rows (the existing `perm_write=1` grant to operator/reviewer/admin on
`shopify.connector.job`, already in place, is sufficient — group checks
inside the two methods narrow *who may call which transition*, they do
not require a new permission bit).

## 3. Decision closure (D-JA-1) — extracted from D-A6-5, unchanged in substance

**D-JA-1 — Job-control services (retry/cancel), current-mechanism
implementation.**

**`action_manual_retry()`** — allowed from
`failed_retryable`/`failed_final`/`blocked_manual_review`/`skipped`
(the `skipped` edge is required: Task 012's D-012-3 `JobPolicySkip`
path and its packet's skip-recovery note depend on manual retry being
the documented recovery route out of it) → re-queues (`state='queued'`,
**`retry_count` reset to `0`** — a manual retry grants a fresh
automatic-retry budget; preserving the count would make a retry from
`failed_final` re-exhaust immediately). Permission: `reviewer`/`admin`
required when the job's current state is `blocked_manual_review`;
`operator`+ (operator or admin) otherwise, per the accepted role
matrix. One `manual_action` log row per call, actor recorded. Any
other from-state raises `UserError` — no silent no-op.

**`action_cancel()`** — allowed from any non-terminal state
(`draft`/`queued`/`running`/`retry_waiting`) → `cancelled`.
**Mandatory non-empty `reason`** (stored in the job's existing
`cancel_reason` field). Permission: `operator`+ (operator or admin).
One `manual_action` log row per call, actor recorded, reason included
in the log message. Any terminal from-state raises `UserError`.

**No force/bypass parameter exists on either method** (the merged
invariant this repository already applies everywhere else — D-SEC1-3,
D-A6-5 original text, LC-1's cancellation helper).

**Mechanism (current, forward-compatible — same pattern LC-1 already
uses for exactly the same reason).** Both methods call `self.write(...)`
directly through the model's own already-merged `write()` — which today
guards only transitions *to* `running` (business-source store-state
re-check) and the domain-flag hook; it does **not** block writes to
`queued` or `cancelled`. **No su-elevation is added by this stage** —
none is required, because Task SEC-1's D-SEC1-2 protected-field guard
has not landed yet at this stage's implementation time, exactly the
same ordering constraint LC-1 satisfied for its own cancellation write
(`module-lifecycle-uninstall-design.md` §7, "Historic-job conversion
mechanics"). **Forward compatibility is mandatory:** the two allowed-from
sets above are byte-identical to the edges SEC-1's D-SEC1-1 legal
transition matrix already reserves for them
(`failed_retryable|failed_final|blocked_manual_review|skipped→queued`;
`non-terminal→cancelled`) — so when SEC-1 lands, these two methods
become matrix-legal automatically and need no behavioral change, only
the su-elevation SEC-1 itself adds at their write sites (§6 below; SEC-1
already reserves this integration point — see DEC-034 §"SEC-1 current
and future surface").

**Audit.** Each call appends exactly one `shopify.connector.job.log`
row via the job model's existing sanctioned `_system_append()` path
(`event_type='manual_action'`, `from_state`/`to_state` populated,
`actor_uid` = the calling user, `message` naming the action and — for
cancel — the reason) — the identical pattern `job.py`'s own
`_log_transition()` helper already uses for every other transition.
Because `shopify_connector_job_actions.py` is a pure `_inherit`
extension of the **same** model, it calls the existing private
`_log_transition()` helper directly; no duplicate logging code is
written.

## 4. Interaction with LC-1 and with Area 6's remaining scope

**LC-1:** no call-path dependency in either direction. LC-1's
`_reassign_to_historic_job_type()` cancels non-terminal jobs through
its own direct write + `_system_append` call (module-lifecycle-uninstall-design.md
§7) — it does not call `action_cancel()`, and this stage's
`action_cancel()` does not call it. Both are independent direct-write
callers of the same current mechanism; SEC-1 later recognizes both as
sanctioned internal writers (DEC-034 §"LC-1/SEC-1 compatibility").
Sequencing LC-1 before this stage (as DEC-034 corrects) has no
mechanical requirement behind it beyond the product-owner's stated
stage order — there is no code dependency either way.

**Area 6 (remaining scope, still Wave 2+, unauthorized here):** once
this stage merges, Area 6's own future packet **must not** re-implement
`action_manual_retry`/`action_cancel` — its allowed-files list and DoD
are corrected by this same reconciliation (`area-6-sync-triggers-implementation-packet.md`,
per DEC-034 §5) to depend on these already-implemented services instead
of owning them. Area 6's `action_sync_selected()` / scan-collision
service methods remain untouched, unimplemented, and out of this
packet's scope.

## 5. Allowed / forbidden files (exhaustive)

**Allowed:**
- `addons/shopify_connector_core/models/shopify_connector_job_actions.py`
  (NEW — pure additive `_inherit` extension of `shopify.connector.job`;
  `action_manual_retry()`, `action_cancel()`; no other method)
- `addons/shopify_connector_core/models/__init__.py` (one import line)
- `addons/shopify_connector_core/tests/test_job_actions.py` (NEW)
- `addons/shopify_connector_core/tests/__init__.py` (one import line)
- `addons/shopify_connector_core/__manifest__.py` (version bump only)
- `docs/05-qa/task-job-actions-validation-results.md` (NEW)
- `docs/05-qa/architecture-review-log.md` (append one AR row)
- `docs/01-research/research-handoff.md` (top entry)

**Forbidden:** `shopify_connector_job.py` itself (no edit — this stage
is additive-only, exactly as Area 6's original D-A6-5 text required);
`shopify_connector_job_dispatch.py`; `shopify_connector_readiness_check.py`;
`shopify_connector_store.py`; `shopify_connector_binding_mixin.py`; any
ACL CSV (no new permission row — existing operator/reviewer/admin
`perm_write=1` on the job model already covers the write; the group
checks inside the two methods are application-level narrowing, not an
ACL change); any product/sale-module file (no domain scan/cron/trigger
scope — Area 6's remaining ownership); views/UI; webhooks/OAuth/CI;
`adams_base`; `main`; plain `dev`.

## 6. SEC-1 integration point (reserved, not implemented here)

This packet does **not** add su-elevation to `action_manual_retry`/
`action_cancel`. When Task SEC-1 lands (next in the corrected Wave 1
order), its own allowed-files list (per DEC-034's revision to
`task-sec1-security-hardening-packet.md` §5) includes
`shopify_connector_job_actions.py` **for the sole purpose of adding the
su-elevation these two methods' write sites need under D-SEC1-2** — the
same "each elevation itemized" discipline SEC-1 already applies to the
dispatcher/enqueue/readiness/store files. This stage's tests
(`test_job_actions.py`) assert only the current-mechanism behavior
(group checks, allowed-from matrix, retry-count reset, audit rows,
no-bypass); SEC-1's own negative RPC matrix (D-SEC1-7) re-asserts the
same methods still function correctly once su-wrapped, per its own
sudo-path-regression requirement.

## 7. Tests (`test_job_actions.py`)

`action_manual_retry`: positive case from each of the four allowed
from-states (`failed_retryable`, `failed_final`, `blocked_manual_review`,
`skipped`) → `queued`, `retry_count` reset to `0`, one `manual_action`
log row with correct `from_state`/`to_state`/`actor_uid`; permission
denial for a non-reviewer/non-admin user retrying a
`blocked_manual_review` job; permission denial for a non-operator
user in the operator+ cases; illegal from-state (e.g. `running`,
`queued`, `cancelled`, `succeeded`) raises `UserError`, no write
occurs. `action_cancel`: positive case from each non-terminal state
→ `cancelled`, `cancel_reason` stored, one `manual_action` log row;
missing/empty `reason` raises `UserError`; permission denial for a
non-operator/non-admin user; illegal (terminal) from-state raises
`UserError`, no write occurs. Both: no bypass/force parameter exists
(source-level signature check). Existing core/product/sale suites stay
green (no shared file touched beyond the two additive files + one
import line each).

## 8. Gate criteria / acceptance criteria / DoD / rollback

Only §5 files changed; all §7 tests green locally and on Odoo.sh
(verbatim quote, OP-43); no other job-model behavior changed
(diff-scope check against `shopify_connector_job.py` itself — it must
show zero diff); validation record + AR row + handoff top entry;
draft PR; the gate closes on draft-open. **Rollback:** revert the
single PR — the new file, its two `__init__.py` import lines, and the
manifest version bump are removed; no schema change (no new field —
`state`, `retry_count`, `cancel_reason` already exist on the job
model); no data loss (jobs already retried/cancelled keep their new
states, identical in kind to LC-1's own rollback note).

## 9. Locked final implementation prompt (Task JOB-ACTIONS)

```text
GATE OPEN — accepted for Wave 1 Stage 3 under DEC-034 and issue #167.
Usable only inside the authorized Wave 1 Sol mission: verify the
current mvp/program-integration tip directly from GitHub before
branching (STOP on drift). (Prerequisite: Task LC-1 merged
runtime-green, per the DEC-034-corrected Wave 1 order.)

Implement Task JOB-ACTIONS — generic job-control services — exactly per
docs/07-implementation-plan/task-job-actions-generic-core-packet.md
(D-JA-1 binding). Branch from the verified current mvp/program-integration
tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES: exactly the §5 list — nothing else. FORBIDDEN:
shopify_connector_job.py itself; dispatcher; readiness check; store;
binding mixin; any ACL CSV; any product/sale-module file; views/UI;
webhooks/OAuth/CI; adams_base; main; plain dev.

IMPLEMENT exactly: D-JA-1 — action_manual_retry() (allowed from
failed_retryable/failed_final/blocked_manual_review/skipped -> queued,
retry_count reset to 0, reviewer/admin required from
blocked_manual_review else operator+, one manual_action log row) and
action_cancel() (allowed from any non-terminal state -> cancelled,
mandatory non-empty reason stored in cancel_reason, operator+ required,
one manual_action log row) as a pure additive _inherit extension of
shopify.connector.job in a NEW file
shopify_connector_job_actions.py. Use the CURRENT merged write() gate
only -- NO su-elevation (SEC-1 adds that later at these exact write
sites, per this packet's §6); no force/bypass parameter on either
method; reuse the existing _log_transition()/_system_append() audit
path. The full §7 test matrix.

Runtime: full Odoo.sh run green before merge review (verbatim quote);
all pre-existing suites green unchanged. Stop condition: draft PR
"Task JOB-ACTIONS: generic job-control services (manual retry /
cancel)"; gate closes on draft-open; no other work.
```
