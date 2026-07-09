# Task 006C — Sync Engine Skeleton Gate-Opening Proposal

> **Status: Proposed only. Does not open the Task 006C implementation
> gate.** This document proposes the conditions under which ChatGPT could
> later open a dedicated Task 006C implementation gate — it does not open
> one itself. Mirrors the
> [`task-004-gate-opening-proposal.md`](./task-004-gate-opening-proposal.md) →
> [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
> and
> [`task-005-gate-proposal.md`](./task-005-gate-proposal.md)
> precedent. **No coding starts until ChatGPT explicitly accepts this
> proposal, the companion
> [`task-006c-sync-engine-skeleton-implementation-scope.md`](./task-006c-sync-engine-skeleton-implementation-scope.md),
> and separately issues
> [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
> in chat, as its own turn.** Nothing here is implementation authorization.

## 1. Current project state after PR #128

- **Task 006A (sync-engine research) is complete and merged** — PR #123,
  #124, #125, #126, #127 all merged into `Shopify-connector`.
- **Task 006B (architecture gate) is complete and merged.** PR #128
  merged the proposed architecture gate
  ([`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md))
  and its decision record
  ([`DEC-025`](../04-decisions/DEC-025-task-006-sync-engine-gate.md)).
  **DEC-025 is Accepted by ChatGPT (2026-07-08).** `AR-030` in
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  is Accepted, mirroring DEC-025 exactly.
- **DEC-025's acceptance did not authorize implementation and did not
  create Task 006C** — its own Acceptance note states this explicitly, and
  this proposal does not treat DEC-025's acceptance as anything more than
  what it says it is.
- **Task 006C did not exist before this session.** This session (branch
  `claude/task-006c-sync-engine-scope-pmj6ta`) creates the implementation-
  scope package for the first time — this proposal, the companion scope
  document, the final-prompt draft, and the QA checklist.
- **No sync-engine code exists anywhere in the repository.** No enqueue
  service, no dispatcher, no handler registry, no drain loop, no domain job
  type — confirmed by direct inspection of
  `addons/shopify_connector_core/models/` this session (see the companion
  scope document §B).

## 2. Why the implementation gate should open — after ChatGPT review

**[Recommendation]** The evidence base is now, for the first time in this
project's history, sufficient to scope (not yet build) a core sync-engine
skeleton:

1. **The architecture is accepted, not merely researched.** DEC-025
   accepted seven concrete architecture decisions (domain-neutral core,
   unified job-trigger convergence, the classified DEC-009 retry policy,
   layered idempotency, `ir.cron` as the Phase 1 substrate, the Shopify
   API-behavior accommodations, and the core-vs-domain responsibility
   table) — a future coding task now has a cited, ChatGPT-accepted shape
   to implement against, not raw Task 006A research to interpret itself.
2. **The existing substrate already carries every hook this skeleton
   would attach to.** `shopify.connector.job`'s full state machine,
   `idempotency_key`/`operation_scope_key` constraints, store-state
   gating, and `job.log`'s sanctioned append path are already accepted and
   tested (Task 001/003/005) — the skeleton is additive scaffolding on
   top of proven substrate, not a from-scratch design.
3. **This is the named unblocking step for every future domain-sync
   task.** Per the companion scope document §A, no domain module
   (product/customer/order/inventory/fulfillment) can safely enqueue or
   process one real operation until an engine exists to claim, dispatch,
   retry, and fail it — building this now, ahead of any specific domain
   task, prevents each future domain task from reinventing (or worse,
   duplicating, RA-013) its own queue/retry/log mechanism.
4. **The scope is bounded and testable without any of the still-open
   items being resolved.** VAL-B2, MBQ-05, TD-002, the fulfillment API
   model, product first-sync dedup, and Lite/Full packaging are all
   irrelevant to a core skeleton that makes zero live Shopify calls and
   implements zero domain logic — see §4 (non-goals) and the companion
   scope document §G.

**This is a recommendation, not a decision.** Whether to actually open the
gate — and on what exact terms — remains entirely ChatGPT's call, exercised
through the acceptance act named in §5.

## 3. Exact future implementation slice

Restated from the companion scope document (§A, §C, §F), the proposed
slice is:

- A core **job enqueue service** (new `AbstractModel`, wraps the existing
  `Job.create()`, no new idempotency mechanism).
- A core **job dispatcher** and **`ir.cron`-driven claim/drain loop**
  skeleton (new `AbstractModel` + one new `ir.cron` data record).
- A **handler-registry extension seam** (shape: a **candidate requiring
  ChatGPT's explicit approval in the gate-opening act itself** — DEC-025
  names this exact question, whether the `_get_checks()` precedent
  literally extends to `job_type → handler` dispatch, as one of its own
  three new open architecture questions; this proposal recommends, but
  does not select, adapting that precedent via a new `_get_handlers()`
  method), plus exactly one new core/diagnostic `job_type` Selection
  value needed to exercise the seam in tests (candidate:
  `core_dispatch_selftest`).
- A **retry scheduler** honoring the already-accepted DEC-009 error-class
  taxonomy, using MBQ-16's implementation-planning-default constants.
- **Duplicate-running guards** at both job creation (the existing
  `operation_scope_key` constraint, reused verbatim) and job execution (a
  claim-time concurrency guard — the exact mechanism is a **candidate
  requiring ChatGPT's explicit approval in the gate-opening act itself**,
  per the scope document §F item 1; DEC-025 explicitly withheld this
  selection and this proposal does not make it either).
- **Permanent-failure (`failed_final`) and blocked-manual-review
  (`blocked_manual_review`) transition helpers**, implementing
  already-accepted DEC-009 state semantics.
- **Job-log integration** exclusively through the existing
  `_system_append()` path, with existing redaction preserved unchanged.
- **Store-state gating** (already implemented, untouched) plus a new
  **domain-enabled execution-time-only gating hook** (fail-safe only, per
  the already-accepted DEC-013 §I.3 direction — no domain module is built
  to actually drive it).
- **Lifecycle handling** for disconnected/reconnect-needed stores, building
  on (not modifying) the existing `action_disconnect()` cancellation
  sweep, plus a narrowing (not a closing) of the SRR-03 in-flight-job race
  via an execution-time-immediately-before-dispatch re-check.
- **Unit tests for every implemented behavior** — no untested behavior
  ships.

## 4. Risks

Restated and expanded from DEC-025's own risk register and the companion
scope document §I — **none of these is resolved by this proposal or would
be resolved by the future implementation this proposal scopes**:

1. **Concurrency-mechanism selection risk.** Whatever claim mechanism
   ChatGPT approves for §3's execution-time duplicate-running guard, its
   real-world safety under concurrent `ir.cron` workers or a multi-server
   deployment is **not** provable by `TransactionCase` unit tests alone
   (DEC-025 Risks #2/#3, SRR-04/SRR-09) — live Odoo.sh (and, where
   relevant, multi-server) runtime proof remains required **after**
   implementation, not before this gate could open.
2. **Disconnect/in-flight-job race (SRR-03) risk.** The proposed
   execution-time-immediately-before-dispatch re-check narrows, but this
   proposal does **not** claim it closes, the race between a store
   disconnecting and a job already `running` inside an in-flight `ir.cron`
   batch. This remains a named, live-proof-required risk.
3. **Savepoint/batch-sizing risk.** A conservative default batch size
   (§F item 7 of the scope document) is proposed, but its adequacy at
   realistic catalog/order volumes is unvalidated (SRR-01, DEC-025 Risk
   #4) until a live runtime test is run.
4. **Scope-creep risk during implementation.** A skeleton this
   structurally central to the whole connector is exactly the kind of task
   where "just one small domain-facing convenience" could creep in during
   coding. The companion scope document's forbidden-files list (§D) and
   this proposal's non-goals (§5) exist specifically to guard against
   this — the future task's final prompt must be followed literally, not
   reinterpreted expansively.
5. **Handler-registry adaptation risk.** The `_get_checks()` precedent is
   proven for check-aggregation semantics, not dispatch/ordering/
   per-operation error semantics — the adaptation itself carries design
   risk the companion scope document does not resolve and does not select
   (correctly labeled a "candidate requiring ChatGPT approval," per scope
   document §F item 4 — DEC-025 itself lists this exact question as an
   open architecture question, not something this proposal may decide).
6. **Repeat of the PR #121 failure-pattern risk (SRR-06).** This project
   has direct precedent (DEC-024 §4) of a concurrency/timing-dependent
   defect passing every static review but failing live. Any concurrency-
   sensitive code this skeleton introduces (the claim mechanism above all)
   must not be considered validated until proven live, exactly as DEC-024
   already established as a binding lesson.

## 5. All non-goals

This proposal — and the future Task 006C coding session it proposes to
gate — does **not**:

- Authorize any code now. This is a proposal document; nothing here is
  implementation authorization.
- Select the execution-time claim/concurrency mechanism. That selection
  remains for ChatGPT's own gate-opening act (§3), not this proposal.
- Resolve VAL-B2, MBQ-05, TD-002, the fulfillment API model, product
  first-sync dedup thresholds, the 16-vs-17 `@idempotent` mutation-count
  discrepancy, the OCA `queue_job` worker-count wording discrepancy, or
  Lite/Full packaging — every one of these remains exactly as open as
  before this session (companion scope document §G).
- Implement, or authorize implementing, any product/customer/order/
  inventory/fulfillment domain sync logic.
- Implement, or authorize implementing, any OAuth/token-acquisition
  mechanism.
- Implement, or authorize implementing, any setup wizard, view, menu,
  action, or other UI surface.
- Implement, or authorize implementing, any webhook HTTP controller/
  receiver.
- Make any live Shopify API call, or authorize one, anywhere.
- Claim any runtime/concurrency risk named in §4 is closed or validated.
- Reopen, revisit, or reintroduce any entry in
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
  — none is proposed here (checked before drafting, per `CLAUDE.md` §10).
- Modify
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  — this session leaves that file untouched (see the final report for the
  explicit confirmation and the repo-convention question this raises).

**No coding starts until ChatGPT accepts this proposal, accepts the
companion implementation-scope document, and separately issues the
companion final prompt in chat, as its own turn.** Acceptance of this
proposal, by itself, does not constitute issuing that prompt.

## 6. What ChatGPT's gate-opening act would need to fix

If and when ChatGPT chooses to open the Task 006C gate, the acceptance act
itself — not this proposal — must explicitly decide, per the companion
scope document §F:

- The concrete execution-time claim/concurrency mechanism (item 1) —
  this proposal recommends, but does not select, `try_lock_for_update()`
  with skip-on-lock-failure semantics.
- Confirmation (or revision) of the retry-scheduling default constants
  (item 2).
- **The handler-registry seam shape (item 4)** — DEC-025 itself names this
  as one of exactly three new open architecture questions the gate
  surfaces (whether the `_get_checks()` inheritance-append pattern
  literally extends to `job_type → handler` dispatch, or needs a
  materially different shape). This proposal recommends, but does not
  select, a new `_get_handlers()` method adapting the existing precedent.
  This same act should also confirm the candidate name and scope of the
  one new core/diagnostic `job_type` Selection value item 4 identifies as
  necessary to exercise the seam in tests (candidate: `core_dispatch_selftest`).
- Confirmation (or revision) of the proposed file split between
  `shopify_connector_job_enqueue.py` and `shopify_connector_job_dispatch.py`
  versus folding both into `shopify_connector_job.py` — the final-prompt
  draft's own "File-split note" flags this as unresolved and must not be
  issued until this is fixed.
- Confirmation (or revision) of the proposed conservative cron-batch-size
  default (item 7).

Only once those are fixed — by ChatGPT, in the gate-opening act itself, not
inferred by whoever issues the final prompt — should
[`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)'s
placeholders be filled in and the prompt issued.
