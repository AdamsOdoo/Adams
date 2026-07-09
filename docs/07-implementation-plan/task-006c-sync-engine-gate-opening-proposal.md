# Task 006C — Sync Engine Skeleton Gate-Opening Proposal

> **Status: Proposed for ChatGPT gate-opening review. Does not open the
> Task 006C implementation gate yet.** This document proposes opening the
> Task 006C coding gate **only after** (a) ChatGPT accepts this proposal,
> (b) ChatGPT accepts the companion gate document
> ([`task-006c-sync-engine-skeleton-gate.md`](./task-006c-sync-engine-skeleton-gate.md)),
> and (c) this PR (or its accepted revision) merges into
> `Shopify-connector`. **Implementation is still NOT authorized by this
> document by itself** — not as a draft, not under review, and not even
> immediately after its own acceptance and merge, taken alone. Opening the
> gate additionally
> requires ChatGPT to separately paste
> [`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)
> in chat, as its own turn, in a new Claude Code session, per `CLAUDE.md`
> §5/§9. Mirrors the
> [`task-004-gate-opening-proposal.md`](./task-004-gate-opening-proposal.md) →
> [`task-004-readiness-check-substrate-gate.md`](./task-004-readiness-check-substrate-gate.md)
> and
> [`task-002-gate-opening-proposal.md`](./task-002-gate-opening-proposal.md) →
> [`task-002-credential-storage-gate.md`](./task-002-credential-storage-gate.md)
> precedent — a **proposal** document (this file), a paired **gate**
> document
> ([`task-006c-sync-engine-skeleton-gate.md`](./task-006c-sync-engine-skeleton-gate.md)),
> and a companion **final prompt**
> ([`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md)).
> **Nothing in this document is a Decision** (`CLAUDE.md` §8) until
> ChatGPT accepts it — every proposed answer below is labelled
> **[Recommendation]**, not **[Decision]**.

**Session note (Task 006D, 2026-07-09):** this revision turns the prior,
general Task 006C gate-opening proposal into a concrete proposed
gate-opening decision package, answering — as recommendations, not
decisions — the six open implementation choices the accepted
implementation-scope package (PR #129, accepted 2026-07-08 as a
planning/scope package only) and the still-**Draft-only** final prompt
both left for a future, separate ChatGPT act. See "Proposed gate-opening
decisions" (§6) below.

---

## 1. Current project state after PR #129

- **Task 006A (sync-engine research) is complete and merged** — PR #123,
  #124, #125, #126, #127, all merged into `Shopify-connector`.
- **Task 006B (architecture gate) is complete and merged.** PR #128
  merged the accepted architecture gate
  ([`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md))
  and its decision record
  ([`DEC-025`](../04-decisions/DEC-025-task-006-sync-engine-gate.md),
  **Accepted by ChatGPT, 2026-07-08**). `AR-030` in
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  is **Accepted**, mirroring DEC-025 exactly.
- **Task 006C (implementation-scope package) is complete and merged.**
  PR #129 merged
  [`task-006c-sync-engine-skeleton-implementation-scope.md`](./task-006c-sync-engine-skeleton-implementation-scope.md),
  this proposal's own prior revision, the final-prompt draft, and the QA
  checklist. ChatGPT **accepted the implementation-scope document's
  content on 2026-07-08, as a planning/scope package only** (control-room
  review, GitHub review artifact/comment ID `4920363287`) — see that
  document's own Acceptance note. **That acceptance did not accept this
  gate-opening proposal, did not accept the final prompt, did not fill any
  placeholder, and did not open any implementation gate** — all three
  remained exactly as this document's prior revision left them, per the
  implementation-scope document's own explicit acceptance-note statement.
- **This session (Task 006D, branch
  `claude/task-006d-sync-engine-gate-opening-fp33xo`) is the first session
  to propose concrete answers** to the six open implementation choices the
  accepted scope package's §F left as candidates requiring ChatGPT
  approval. **No code exists anywhere in the repository implementing any
  of this proposal's content** — confirmed by direct inspection of
  `addons/shopify_connector_core/models/` this session (unchanged since
  the scope document's own §B inventory: three `job_type` values, no
  enqueue/dispatch/registry code, no drain loop).

## 2. Why the implementation gate should open — after ChatGPT review

**[Recommendation]** Restated from this proposal's prior revision, now
strengthened by the scope package's own acceptance:

1. **The architecture is accepted (DEC-025) and the implementation scope
   is accepted as a planning package (PR #129).** A future coding task now
   has both a cited architecture shape and a cited, reviewed implementation
   scope to build against — the only remaining gap is the concrete
   selection of the choices DEC-025 and the scope package explicitly
   withheld (§6/§F).
2. **The existing substrate already carries every hook this skeleton would
   attach to** — `shopify.connector.job`'s full state machine (confirmed
   again by direct inspection this session: `JOB_STATE_SELECTION`,
   `ERROR_CLASS_SELECTION`, `MANUAL_REVIEW_SUBREASON_SELECTION`,
   `idempotency_key`/`operation_scope_key` with their unique constraints,
   the `BUSINESS_JOB_SOURCES`-gated `create()`/`write()`), and
   `job.log._system_append()`'s redaction-enforcing single write path —
   are already accepted and tested.
3. **This is the named unblocking step for every future domain-sync
   task** — unchanged from the prior revision.
4. **The scope is bounded and testable without any of the still-open
   items being resolved** — VAL-B2, MBQ-05, TD-002, the fulfillment API
   model, product first-sync dedup, and Lite/Full packaging remain
   irrelevant to a core skeleton that makes zero live Shopify calls and
   implements zero domain logic (§7, §8 below).

**This is a recommendation, not a decision.** Whether to actually open the
gate — and on what exact terms — remains entirely ChatGPT's call, exercised
through the acceptance act named in §9.

## 3. Exact future implementation slice

Unchanged in substance from the accepted implementation-scope document
(§A, §C, §F) and this proposal's prior revision — restated here with the
six open choices now answered by §6's recommendations rather than left
blank:

- A core **job enqueue service** (new `AbstractModel`, wraps the existing
  `Job.create()`, no new idempotency mechanism) — file split per Decision
  D.
- A core **job dispatcher** and **`ir.cron`-driven claim/drain loop**
  skeleton (new `AbstractModel` + one new `ir.cron` data record) — batch
  size/interval per Decision E.
- A **handler-registry extension seam** — shape per Decision B, plus
  exactly one new core/diagnostic `job_type` Selection value per Decision
  F.
- A **retry scheduler** honoring the already-accepted DEC-009 error-class
  taxonomy, using the constants proposed in Decision C.
- **Duplicate-running guards** at both job creation (the existing
  `operation_scope_key` constraint, reused verbatim) and job execution — a
  claim-time concurrency guard per Decision A.
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
  ships (full list: implementation-scope document §H).

## 4. Risks

Restated and carried forward, unresolved, from DEC-025's own risk register
and the companion scope document's §I — **none of these is resolved by
this proposal, by the six recommendations in §6, or by the future
implementation this proposal scopes**:

1. **Concurrency-mechanism selection risk.** Even if ChatGPT accepts
   Decision A's `try_lock_for_update()` recommendation, its real-world
   safety under concurrent `ir.cron` workers or a multi-server deployment
   is **not** provable by `TransactionCase` unit tests alone (DEC-025
   Risks #2/#3, SRR-04/SRR-09) — live Odoo.sh (and, where relevant,
   multi-server) runtime proof remains required **after** implementation,
   not before this gate could open.
2. **Disconnect/in-flight-job race (SRR-03) risk.** The proposed
   execution-time-immediately-before-dispatch re-check narrows, but this
   proposal does **not** claim it closes, the race between a store
   disconnecting and a job already `running` inside an in-flight `ir.cron`
   batch. This remains a named, live-proof-required risk.
3. **Savepoint/batch-sizing risk.** Decision E's conservative default
   batch size is proposed, but its adequacy at realistic catalog/order
   volumes is unvalidated (SRR-01, DEC-025 Risk #4) until a live runtime
   test is run.
4. **Scope-creep risk during implementation.** A skeleton this
   structurally central to the whole connector is exactly the kind of task
   where "just one small domain-facing convenience" could creep in during
   coding. The final prompt's allowed/forbidden-files lists (unchanged in
   substance by this revision) and this proposal's non-goals (§8) exist
   specifically to guard against this.
5. **Handler-registry adaptation risk.** Decision B's recommendation
   adapts the `_get_checks()` precedent (proven for check-aggregation
   semantics, not dispatch/ordering/per-operation error semantics) — the
   adaptation itself carries design risk this proposal's recommendation
   does not eliminate, only proposes a concrete shape for.
6. **Repeat of the PR #121 failure-pattern risk (SRR-06).** This project
   has direct precedent (DEC-024 §4) of a concurrency/timing-dependent
   defect passing every static review but failing live. Any
   concurrency-sensitive code this skeleton introduces (the claim
   mechanism above all) must not be considered validated until proven
   live.
7. **Diagnostic-`job_type` scope-drift risk.** Decision F's
   `core_dispatch_selftest` value must never be silently treated as a
   template for a future domain `job_type`, and must never be dispatched
   to a handler that calls Shopify — a risk named explicitly so a future
   implementation session does not casually reuse it beyond its stated
   diagnostic purpose.

## 5. What this proposal is not

Restated from the prior revision — this proposal, the companion gate
document, and the future Task 006C coding session they propose to gate,
do **not**:

- Authorize any code now. This is a proposal document; nothing here is
  implementation authorization.
- Finally decide any of the six items in §6 — every one remains a
  **[Recommendation]** until ChatGPT accepts this proposal and the
  companion gate document.
- Resolve VAL-B2, MBQ-05, TD-002, the fulfillment API model, product
  first-sync dedup thresholds, the 16-vs-17 `@idempotent` mutation-count
  discrepancy, the OCA `queue_job` worker-count wording discrepancy, or
  Lite/Full packaging — every one of these remains exactly as open as
  before this session (§7 below).
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
  — none is proposed here (the full log was checked before drafting §6,
  per `CLAUDE.md` §10 — none of the six recommendations reintroduces
  RA-004's rejection of OCA `queue_job` as a default substrate, or any
  other binding rejected approach).
- Fill the final prompt's merge-commit-SHA placeholder — this PR has not
  merged, so that value cannot be known (§9).

## 6. Proposed gate-opening decisions

**Each decision below is a [Recommendation] for ChatGPT's gate-opening
review, not a [Decision].** These are the exact six items the accepted
implementation-scope document's §F and this proposal's prior §6 named as
"candidate requiring ChatGPT approval" or "requiring confirmation." This
section replaces the prior revision's "What ChatGPT's gate-opening act
would need to fix" — instead of only listing the open items, it proposes
a concrete answer for each, for ChatGPT to accept, revise, or reject in
the companion gate document.

### Decision A — execution-time claim/concurrency mechanism

**[Recommendation]** Use Odoo's official row-locking primitive
`try_lock_for_update()`, applied per candidate `shopify.connector.job` row
during the drain loop's claim step; a row that cannot be locked is skipped
in the same drain pass (functionally mirroring `SKIP LOCKED` semantics
using an officially documented Odoo 19 primitive, per the gate document's
own `O9`/`OD-3` citation). **Never** a raw SQL `SKIP LOCKED`
reimplementation. **Never** a PostgreSQL advisory lock (`pg_advisory_lock`
or any variant) in this phase — SRR-09 names documented hazards
(`LIMIT`-ordering interaction, rollback-non-release) this recommendation
avoids by not adopting the primitive at all.

- This is **unit-testable only as code-level behavior under
  `TransactionCase`** — a test proving "two simulated concurrent claim
  attempts against the same job row yield exactly one successful claim" is
  a code-level proof, not a concurrent-worker proof.
- **Real multi-worker/multi-server safety remains runtime validation, not
  proven by unit tests** (DEC-025 Risks #2/#3, SRR-04/SRR-09) — this
  recommendation does not, and could not, close that gap; §8 below
  restates the runtime-validation requirement explicitly.

### Decision B — handler-registry seam shape

**[Recommendation]** A new `shopify.connector.job.dispatch` `AbstractModel`
carrying a `_get_handlers()` registry-seam method, returning a mapping
from `job_type` (string) to a handler — either a callable or a handler
method descriptor (exact calling convention is implementation detail for
the future coding session, not fixed here). The pattern **adapts** the
already-accepted, already-tested `_get_checks()` inheritance-append
extension seam on `shopify.connector.readiness.check` (confirmed by direct
inspection this session — classic `_inherit` + `super()` + append, no
table, no ACL row) — it is **not a literal copy**: `_get_checks()`
aggregates independently-evaluated checks fail-closed; `_get_handlers()`
must instead support dispatch-by-key lookup, since a job has exactly one
`job_type` and must route to exactly one handler, not have every
registered handler run and be aggregated.

- **The dispatcher fails safely for missing handlers** — a job whose
  `job_type` has no registered handler must never hang or silently drop;
  it must route to a safe terminal/retryable outcome (e.g.
  `unknown_system_error` → `failed_final`, per the scope document's own
  §H "Missing handler behavior" test requirement).
- **Domain modules will later extend this seam via inheritance** (classic
  `_inherit` + `super()._get_handlers()` + dict-merge/update, mirroring the
  `_get_checks()` append pattern), **but no domain module is implemented
  now** — this recommendation proposes the seam shape only, exercised in
  the skeleton's own tests exclusively via the diagnostic `job_type` named
  in Decision F.

### Decision C — retry-default constants

**[Recommendation]** Use the DEC-009/MBQ-16 implementation-planning
defaults, unchanged:

| Constant | Value |
| --- | --- |
| Max attempts | 12 |
| Base delay | 30 seconds |
| Exponential multiplier | 2 |
| Max delay (cap) | 30 minutes |
| Jitter | ±20% |
| Retry window | 24 hours |

- **Constants must be named and tunable, not inlined magic numbers** — a
  future retuning session must be able to change these without an
  architecture change, per DEC-009's own acceptance note framing them as
  "implementation-planning defaults, not final production-tuned
  constants."
- **Unit tests may assert deterministic bounds, or use an injectable
  jitter/time helper** (e.g. a seedable/overridable jitter function, or a
  time-source dependency the test can control) — a test must not be
  flaky by relying on unseeded randomness or wall-clock timing.
- **Production tuning remains future work** — this recommendation does
  not claim these six numbers are correct at MVP-realistic volumes; only
  that they are the sole evidence-cited candidates in the accepted corpus
  suitable for shipping a testable skeleton.

### Decision D — enqueue/dispatch file split

**[Recommendation]** Confirm the implementation-scope document's own
default proposal:

- `addons/shopify_connector_core/models/shopify_connector_job_enqueue.py`
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`

Both are `AbstractModel`s (no table, no new ACL row needed — mirroring
`shopify_connector_readiness_check.py`/`shopify_connector_api_client.py`,
both confirmed `AbstractModel`s by direct inspection this session).
**No new `services/` package** — this addon has no such package today
(the Shopify transport boundary itself is an `AbstractModel` under
`models/`, not a `services/` package; this recommendation follows that
existing convention). **No concrete model or table** is proposed by
either file. **No ACL/security file** is proposed — if implementation-time
inspection finds a concrete (non-abstract) model is genuinely required,
the future coding session must stop and report back before adding any
security file, per the scope document's own §C precedent.

### Decision E — cron batch size / default interval

**[Recommendation]**

| Constant | Value |
| --- | --- |
| Batch size | 20 (named constant, well below the documented 64-savepoint performance ceiling, SRR-01) |
| Cron interval | 5 minutes (matching the accepted Odoo.sh "best effort," never-more-often-than-~5-minutes guidance, DEC-005 evidence `O7`/`OD-2`) |

- **These are conservative implementation defaults, not proven
  performance values.** Neither number is validated against realistic
  catalog/order volumes by this proposal or by any prior session.
- **Runtime validation remains required** — §I of the implementation-scope
  document and §8 below both name "savepoint/batch behavior at realistic
  volumes" as a mandatory post-implementation runtime-validation item,
  not merely a documentation warning to restate.

### Decision F — core diagnostic `job_type`

**[Recommendation]** `core_dispatch_selftest`, added inline to
`shopify_connector_job.py`'s existing static `job_type` selection list
(currently exactly three values, confirmed by direct inspection this
session: `core_readiness_check`, `core_manual_maintenance`,
`core_test_connection` — `job_type` has no `selection_add` caller
anywhere yet, since no domain module exists).

**Scope, restated exactly:**

- **Core/diagnostic only** — mirrors the existing three values' own
  core/diagnostic-only nature.
- **Used only to exercise dispatcher/registry tests** — the scope
  document's own §H names this as the *only* `job_type` the skeleton's own
  tests may use to exercise the `_get_handlers()` registry, since the
  three pre-existing values remain reserved for their own
  already-committed synchronous flows.
- **Never calls Shopify** — no handler registered for this `job_type`, in
  any test or in production code, may call
  `shopify.connector.api.client.execute()` against a real endpoint;
  skeleton tests use no-op/fake handlers only.
- **Never represents domain sync** — this value must never be reused,
  aliased, or treated as a template for a future domain `job_type`; a
  domain module registers its own distinct `job_type` value via
  `selection_add`, per the already-accepted extension-seam direction
  (DEC-013 blueprint §A.5 seam 2).
- **Does not alter the meaning of existing `job_type` values** — the three
  pre-existing values' own semantics, callers, and tests are untouched.

---

## 7. Open blockers preserved

**None of the following is resolved, narrowed, advanced, or silently
decided by this proposal, by any of the six recommendations in §6, or by
the future Task 006C coding session this proposal (if accepted) would
gate:**

- **VAL-B2** — remains deferred / not passed. No live Shopify Admin API
  connection has been made or attempted by this session or any prior one.
- **MBQ-05** — remains Partially routed / Open (token acquisition for many
  unrelated customers unresolved).
- **TD-002** — remains Open (`read_fulfillments` readiness-scope
  correctness concern).
- **Fulfillment API model** — remains unresolved (legacy `Fulfillment` vs.
  `FulfillmentOrder`-based).
- **Product first-sync deduplication** — remains domain-design work,
  deferred to a future product-domain task (MBQ-59).
- **Token acquisition for many unrelated customers** — remains unresolved
  (MBQ-05 branch B, DEC-023 §3.2).
- **Lite/Full packaging** — remains not finalized; still treated as
  product strategy, not an architecture or implementation decision.
- **16-vs-17 `@idempotent` mutation-count discrepancy** — remains open,
  unresolved, immaterial to this core-engine-level scope.
- **OCA `queue_job` worker-count wording discrepancy** — remains open,
  still explicitly non-blocking; `queue_job` remains reference-only
  (RA-004 unchanged, not revisited by this proposal).
- **Multi-server/Odoo.sh runtime concurrency proof** — remains explicitly
  required (DEC-025 Risks #1–#3) before any future implementation may rely
  on a claim about Decision A's job-claiming mechanism, the disconnect/
  in-flight-job race (SRR-03), or cross-server coordination.
- **Checkpoint/resume ownership (core vs. domain)** — remains undecided
  (DEC-025 "Explicit non-decisions"); no checkpoint/resume file, field, or
  model is proposed anywhere in this document or the scope document's §C.

## 8. Runtime validation still required

**Accepting the six recommendations in §6 does not, and could not, satisfy
any of the following** — every item is a **post-implementation**, live
Odoo.sh (and, where named, multi-server) validation requirement, restated
from the implementation-scope document's §I:

- Cron drain runs in Odoo runtime (a real scheduled action fires and
  drains queued jobs).
- Concurrency behavior under multiple workers (`--max-cron-threads` > 1,
  or an equivalent harness) — Decision A's mechanism is not proven safe by
  this proposal or by unit tests.
- Disconnect during an active job (a live reproduction of the SRR-03
  scenario) — the execution-time re-check narrows, does not close, this
  race.
- Retry scheduling works over real time, not merely a unit test
  manipulating the clock in-process.
- Failed jobs are visible/queryable in a live registry.
- No token leakage in logs (a live Odoo server-log grep for a dummy-token
  string).
- Savepoint/batch behavior is acceptable at realistic catalog/order
  volumes (Decision E's batch-size default validated live).

None of these runtime checks may be marked passed by any future coding
session's own PR description without an actual live Odoo.sh run producing
the evidence — mirroring the Task 004/Task 005 validation-results
precedent.

## 9. Gate-opening and gate-closing conditions

**Exact condition for the gate to open** — **all** of the following must
be true; none is satisfied by this document alone:

1. ChatGPT accepts this gate-opening proposal (including any revision
   ChatGPT requires).
2. ChatGPT accepts the companion gate document
   ([`task-006c-sync-engine-skeleton-gate.md`](./task-006c-sync-engine-skeleton-gate.md)).
3. This PR (or its accepted revision) merges into `Shopify-connector`.
4. ChatGPT separately issues the final implementation prompt
   ([`task-006c-sync-engine-skeleton-final-prompt.md`](./task-006c-sync-engine-skeleton-final-prompt.md))
   **in chat, as its own turn, in a new Claude Code session** — pasting it
   verbatim, with its merge-commit-SHA placeholder filled in from
   condition 3's actual merge commit. Acceptance of conditions 1–3 does
   not, by itself, constitute issuing that prompt.

**No implementation is authorized by this document.** No Task 006C
implementation gate is opened by this document. This document does not
claim any of the four conditions above is satisfied.

**Exact condition for the gate to close (once opened):** the gate closes
again the moment the future Task 006C implementation PR this gate
authorizes is **opened as a draft** for ChatGPT's own review — no
follow-on coding beyond that one PR is authorized by this gate, and any
further sync-engine work (a second implementation slice, a domain module,
etc.) requires its own separate, later, explicit ChatGPT gate-opening act,
mirroring the AR-021/AR-026/AR-029 precedent.
