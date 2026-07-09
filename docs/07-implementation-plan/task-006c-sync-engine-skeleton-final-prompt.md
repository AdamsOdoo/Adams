# Task 006C — Sync Engine Skeleton Final Implementation Prompt (Final Draft)

> **Status: Final draft / Pending gate acceptance / Not issued.** This is a
> **copy-ready draft** of the future Claude Code prompt for Task 006C
> implementation, revised (Task 006D, 2026-07-09) to incorporate the six
> concrete recommendations proposed in
> [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)'s
> §6. **It is still not issued. It must still not be pasted into any
> Claude Code session and run.** Issuing it requires, in order: (1)
> ChatGPT already accepted
> [`task-006c-sync-engine-skeleton-implementation-scope.md`](./task-006c-sync-engine-skeleton-implementation-scope.md)
> as a planning/scope package (2026-07-08, PR #129); (2) ChatGPT accepts
> this document, including its resolution of every prior `<PLACEHOLDER>`
> below except the merge-commit SHA (which cannot be known before the
> gate-acceptance PR merges); (3) ChatGPT accepts
> [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md);
> (4) ChatGPT accepts the companion gate document
> [`task-006c-sync-engine-skeleton-gate.md`](./task-006c-sync-engine-skeleton-gate.md);
> (5) that gate-acceptance PR merges into `Shopify-connector`, fixing the
> remaining `<TASK_006D_GATE_MERGE_COMMIT_SHA>` placeholder to its actual
> value; and (6) ChatGPT explicitly pastes this exact finalized prompt
> text into a **new** Claude Code session, as its own chat turn. **Nothing
> in this document authorizes Claude to begin implementation now or at any
> point before all six of those conditions are met.** This draft mirrors
> the
> [`task-004-final-implementation-prompt.md`](./task-004-final-implementation-prompt.md)
> draft-then-finalize precedent.

## How this document will be used (once, and only once, all six
## conditions above are met)

1. Confirm the Task 006C gate-acceptance PR is actually merged into
   `Shopify-connector` — do not assume it is because this document exists.
2. Confirm the `<TASK_006D_GATE_MERGE_COMMIT_SHA>` placeholder below is
   filled in with its actual, post-merge value (every other placeholder
   this document previously carried is already resolved by this
   revision — see the six resolved values below).
3. ChatGPT issues the exact prompt text below in chat, as its own
   session/turn.
4. The implementing session stops at its own scoped boundary
   (`CLAUDE.md` §6) — it must not chain into any further Task 006
   sub-slice, any domain-module task, or any other next-feature work.

---

## Draft prompt text (not issued)

```text
You are Claude Code implementing ONE scoped task for the Odoo 19 Shopify
Connector. Implementation is AUTHORISED by ChatGPT for THIS task only —
confirm the Task 006C gate-opening act
(docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md
and docs/07-implementation-plan/task-006c-sync-engine-skeleton-gate.md,
merge commit <TASK_006D_GATE_MERGE_COMMIT_SHA>) exists, is merged, and
carries ChatGPT's explicit acceptance, together with accepted
docs/07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md
and this exact prompt document, before writing any code.

Read first: CLAUDE.md; docs/01-research/research-handoff.md (current
entry); docs/06-prompts/claude-learning-rules.md; the Task 006C
gate-opening proposal and implementation-scope document named above;
docs/04-decisions/DEC-025-task-006-sync-engine-gate.md;
docs/03-architecture/sync-engine-architecture-gate.md;
docs/05-qa/sync-engine-open-questions.md;
docs/05-qa/sync-engine-risk-register.md;
docs/05-qa/rejected-approaches-log.md;
docs/05-qa/architecture-review-log.md;
docs/05-qa/technical-debt-register.md (confirm TD-002 is still Open and is
NOT touched by this task); docs/05-qa/pr-review-checklist.md (A-C).

File-split note (confirm before issuing): the split below between
shopify_connector_job_enqueue.py and shopify_connector_job_dispatch.py is
Decision D of the gate-opening proposal's §6 (Task 006D) — a
[Recommendation] confirming the implementation-scope document's own
default proposal, still pending ChatGPT's acceptance of that proposal and
the companion gate document. If ChatGPT's gate-opening act specifies a
different split (e.g. folding both into shopify_connector_job.py), replace
the two Allowed-files entries below with that decision before this prompt
is issued.

Objective: Implement the core sync-engine skeleton inside
shopify_connector_core: a job enqueue service, an ir.cron-driven claim/
drain loop, a handler-registry dispatch seam (shape: `_get_handlers()`
registry seam on new shopify.connector.job.dispatch AbstractModel,
returning job_type -> handler mapping, adapted from readiness-check
inheritance/append pattern, with safe missing-handler failure — per
Decision B of the gate-opening proposal's own resolution of
implementation-scope §F item 4), a retry scheduler honoring the existing
DEC-009 error-class taxonomy already encoded in shopify_connector_job.py,
duplicate-running guards at both job creation (reusing the existing
operation_scope_key constraint) and job execution (claim-time guard —
mechanism: try_lock_for_update() per candidate job row, skip locked/
unavailable rows, no raw SQL SKIP LOCKED, no PostgreSQL advisory locks —
per Decision A of the gate-opening proposal's own resolution of
implementation-scope §F item 1), an
execution-time-immediately-before-dispatch store-state re-check (narrows
but does not close the SRR-03 disconnect/in-flight-job race — never claim
it is closed), permanent-failure/blocked-manual-review transition helpers, job
log integration exclusively through the existing job.log._system_append()
path, redaction discipline via the existing tools/redaction.py (no new
redaction mechanism), store-state gating (already implemented, do not
duplicate) plus a new domain-enabled execution-time-only gating hook
(fail-safe only, per DEC-013 §I.3 — never alters an enqueue-time decision,
never bypasses a safety guard), and lifecycle handling for disconnected/
reconnect-needed stores building on the existing action_disconnect()
cancellation sweep, unmodified. NO Shopify live call, NO product/customer/
order/inventory/fulfillment domain sync logic, NO webhook controller, NO
setup wizard/UI/view/menu/action work.

Allowed files (exact):
- addons/shopify_connector_core/models/shopify_connector_job.py (MODIFY
  only) — add: an execution-time claim/lock helper implementing
  try_lock_for_update() per candidate job row, skip locked/unavailable
  rows, no raw SQL SKIP LOCKED, no PostgreSQL advisory locks;
  state-transition helper
  methods for retry_waiting / failed_retryable / failed_final /
  blocked_manual_review / skipped; a domain-enabled execution-time
  re-check inside write(), alongside (not replacing) the existing
  store-state re-check; an execution-time-immediately-before-dispatch
  store-state re-check (SRR-03 narrowing, never claim it closes the race);
  exactly ONE new job_type Selection value, core/diagnostic-only, added
  inline to the existing static selection=[...] list — name
  core_dispatch_selftest (Decision F of the gate-opening proposal's §6)
  — reserved solely for this task's own dispatcher/registry self-tests
  (never dispatched to a live Shopify call, never a template for a future
  domain job_type). Do NOT
  remove, weaken, or alter any existing field, constraint, or gating
  check, and do NOT touch the three pre-existing job_type values' meaning.
- addons/shopify_connector_core/models/shopify_connector_job_enqueue.py
  (NEW, AbstractModel, no table, DEFAULT proposal — see File-split note
  above) — the enqueue service wrapping Job.create(); no new idempotency/
  scope-key mechanism (reuse the existing computed fields verbatim).
- addons/shopify_connector_core/models/shopify_connector_job_dispatch.py
  (NEW, AbstractModel, no table, DEFAULT proposal — see File-split note
  above) — the drain-loop entry point, the _get_handlers() registry seam
  described above (mirrors shopify_connector_readiness_check.py's
  _get_checks() precedent), the dispatcher, and the retry-scheduling
  sweep using the named, non-magic-number constants: 12 attempts,
  30-second base delay, multiplier 2, 30-minute cap, ±20% jitter,
  24-hour retry window (per MBQ-16's implementation-planning defaults,
  Decision C of the gate-opening proposal's §6, unless the gate-opening
  act specifies different values).
- addons/shopify_connector_core/models/shopify_connector_job_log.py
  (MODIFY, ONLY if a new event_type value is genuinely required — if the
  existing five values suffice, do NOT touch this file; if you do modify
  it, the change must be limited to one new Selection option, no other
  change).
- addons/shopify_connector_core/data/shopify_connector_cron_drain.xml
  (NEW) — exactly one ir.cron record; no view, menu, or action file
  accompanies it.
- addons/shopify_connector_core/models/__init__.py — new import line(s)
  only, one per new file above.
- addons/shopify_connector_core/tests/test_job_enqueue.py (NEW)
- addons/shopify_connector_core/tests/test_job_dispatch.py (NEW)
- addons/shopify_connector_core/tests/test_job_retry_scheduling.py (NEW,
  or folded into test_job_dispatch.py — your choice, document which in the
  PR body)
- addons/shopify_connector_core/tests/__init__.py — new import line(s)
  only.
- addons/shopify_connector_core/__manifest__.py — version bump only (from
  the version current at execution time) plus exactly one new entry in
  `data` for the new cron XML file above. No other change.
- docs/01-research/research-handoff.md — the mandatory handoff update.
- docs/05-qa/technical-debt-register.md — ONLY if a genuine new shortcut
  is taken during this task; do not edit otherwise.

No other file may be created or modified. In particular, do NOT create or
modify any security/*.csv or *_security.xml file — both new model files
above are AbstractModels (no table); if implementation-time inspection
shows a concrete model with a table is genuinely required, STOP and report
back before writing any code — do not improvise a broader change. Do NOT
modify shopify_connector_store.py, shopify_connector_store_credential.py,
shopify_connector_store_settings.py, shopify_connector_location.py,
shopify_connector_binding_mixin.py, shopify_connector_api_client.py, or
tools/redaction.py.

Forbidden files (exact):
- Any view/menu/action/wizard/controller/XML file other than the one cron
  data file named above
- Any webhook receiver/controller file of any kind
- Any file under a domain module
  (shopify_connector_product/_sale/_inventory/_fulfillment), including any
  such module's creation
- Any OAuth or token-acquisition file
- Any CI/workflow file, Dockerfile, or requirements*.txt
- Any migration file
- Any file not explicitly named in the Allowed files list above

Acceptance criteria (in priority order):
1. No unit test in this task's new files ever calls
   shopify.connector.api.client.execute() against anything but a fake/
   no-op handler — proven by a source-level test.
2. Store-state gating is provably unchanged (existing test_connection_
   lifecycle.py suite still passes unmodified) and the new domain-enabled
   execution-time re-check never alters an enqueue-time decision or
   bypasses an existing safety guard.
3. Duplicate-running is provably prevented at both creation (existing
   operation_scope_key constraint, unmodified) and execution (the new
   claim mechanism) — a test proves two concurrent claim attempts against
   the same job row yield exactly one successful claim.
4. Every dispatcher/enqueue write path is provably routed through
   job.log._system_append() only — no direct job.log.create() call exists
   anywhere in the new code (source-level test).
5. A dummy-secret string threaded through a fake handler's failure path
   never appears unredacted in any job/job.log field (source-level test,
   mirroring the existing test_no_secret_leakage_in_job_or_log pattern).
6. A job whose job_type has no registered handler fails safely
   (unknown_system_error / failed_final), never hangs or silently drops.
7. failed_final and blocked_manual_review transitions correctly set
   manual_review_subreason exactly when required (reusing the existing
   _check_manual_review_subreason_required constraint, unmodified).
8. The full existing shopify_connector_core test suite (all 8 pre-existing
   test files) still passes unmodified — this task adds tests, it does not
   alter existing ones except the two __init__.py import-line additions.
9. No live Shopify call, no domain sync logic, no UI file, no webhook
   controller exists anywhere in the diff.

Tests (all mandatory, per
docs/07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md
§H):
- Enqueue allowed/blocked by store state
- Enqueue idempotency (existing idempotency_key constraint)
- Operation-scope duplicate prevention (existing operation_scope_key
  constraint)
- Execution claim guard (the new mechanism; code-level proof only, NOT a
  claim of real concurrent-worker safety)
- Handler registry dispatch (fake handler registered from outside
  shopify_connector_core, mirroring the readiness-check extension-seam
  test precedent, exercised via the new core_dispatch_selftest job_type —
  the only job_type this task's own tests may use for this purpose)
- Missing handler behavior
- Retryable error schedules retry (next_retry_at set per the approved
  defaults)
- Terminal error goes failed_final / blocked_manual_review as applicable
- Logs appended through sanctioned path only
- Secrets redacted
- Disconnect cancels/blocks relevant jobs (extends the existing
  test_disconnect_cancels_non_terminal_business_jobs coverage)
- Execution-time store-state recheck (extends the existing
  test_business_job_running_blocked_when_not_connected pattern)
- Execution-time domain-enabled recheck
- No live Shopify call in unit tests (source-level test)
- No domain modules required (full new suite passes with zero domain
  modules installed)

Rollback notes: single-PR revert; no destructive schema change (all
shopify_connector_job.py changes are additive methods, or nullable/
optional fields only if a new field proves necessary — never a rename or
removal of an existing column); job/job.log rows created before a
rollback remain in the database as valid audit history
(ondelete='restrict', unchanged); removing the new ir.cron record on
rollback stops future drain runs but does not touch any already-processed
job row.

Definition of done: all tests above written and pass; no live Shopify
call anywhere in the diff (source-level test proves it); lint/format
clean; docs/05-qa/pr-review-checklist.md section C satisfied; any genuine
shortcut logged in docs/05-qa/technical-debt-register.md; only the
allowed files above changed (confirmed by git diff review); the mandatory
research-handoff update (docs/01-research/research-handoff.md, including
the Learning feedback loop section) is included in the PR; a runtime-
validation plan (per the implementation-scope document's §I) is attached
to the PR — NOT claimed as already executed unless it genuinely was, with
evidence.

Explicit hard constraints (restate before finishing, in the PR body):
- No live Shopify API call of any kind, anywhere, including in tests.
- No product/customer/order/inventory/fulfillment sync code of any kind.
- No OAuth or token-acquisition code of any kind.
- No setup wizard, view, menu, action, or wizard file of any kind.
- No webhook controller/receiver of any kind.
- No new security/ACL file (both new models are AbstractModels).
- VAL-B2, MBQ-05, TD-002, the fulfillment API model, product first-sync
  dedup thresholds, and Lite/Full packaging remain exactly as open as
  before this task — none is touched, resolved, or narrowed by this task.
- No claim that the execution-time claim mechanism is proven safe under
  real concurrent-worker or multi-server execution — that requires the
  live Odoo.sh (and, where relevant, multi-server) runtime validation
  named in the implementation-scope document's §I, to be performed and
  evidenced in a SEPARATE follow-up validation pass, not silently assumed
  passed by this PR.

End: run the learning review, update the handoff (Learning feedback loop
section + next prompt), confirm the quality gate per
docs/05-qa/quality-feedback-loop.md, commit/push to the designated branch,
open the PR as DRAFT, then STOP. Do not start any domain-module task, any
further Task 006 sub-slice, or any other next-feature work in this
session.
```

---

## What this document does not do

- Does not execute the prompt above.
- Does not write any implementation code.
- Does not authorize the future Task 006C coding session to start now or
  at any point before all six conditions in the header above are met.
- Does not itself finalize any resolved value above. The
  concurrency-mechanism, handler-registry-shape, and retry-default values
  are this session's proposed recommendations (gate-opening proposal §6),
  not yet ChatGPT-accepted — the remaining `<TASK_006D_GATE_MERGE_COMMIT_SHA>`
  placeholder cannot be resolved at all until the gate-acceptance PR
  merges.
- Does not claim any open item named in
  [`task-006c-sync-engine-skeleton-implementation-scope.md`](./task-006c-sync-engine-skeleton-implementation-scope.md)
  §G is resolved.
- Does not itself open the Task 006C implementation gate — that requires
  [`task-006c-sync-engine-gate-opening-proposal.md`](./task-006c-sync-engine-gate-opening-proposal.md)
  and
  [`task-006c-sync-engine-skeleton-gate.md`](./task-006c-sync-engine-skeleton-gate.md)
  to be separately accepted and merged, per the proposal's own §9
  conditions.
- Does not claim ChatGPT has issued this prompt. Issuance is a distinct,
  later, separate chat turn by ChatGPT in a new Claude Code session — this
  revision's incorporation of the six §6 recommendations does not
  constitute issuance.
