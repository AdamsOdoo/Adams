# DEC-031 — CORE-R2 Replay-Safety Registry (Layer 1) & Deferred Mutation Hardening (Layer 2) (AR-048)

> **Proposed for ChatGPT review — NOT accepted.** This record resolves
> **AR-048** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
> Full evidence, option analysis, and self-critique live in the companion
> document,
> [`../03-architecture/core-r2-job-execution-replay-safety.md`](../03-architecture/core-r2-job-execution-replay-safety.md).
> **Acceptance would not by itself authorize implementation** — a future,
> separately authorized implementation-gate session is still required
> (`CLAUDE.md` §9) for the Layer 1 registry (companion doc §9, Immediate
> Slice 1).
>
> **Revised 2026-07-15 (control-room review `4701015790`).** The first
> draft of this record made the full Option-A durable-ownership protocol an
> immediate requirement. Control-room review found that disproportionate to
> current UAT scope, where every implemented Shopify handler is read-only.
> This revision splits the decision into **Layer 1** (a minimal replay-policy
> registry — decided now) and **Layer 2** (Option A and mutation hardening —
> deferred until the first Shopify-mutation domain). The evidence base is
> unchanged; only the decision's scope and immediacy are narrowed.

## Status

**Proposed for ChatGPT review.** Not accepted. Not implementation-authorizing.

## Date

2026-07-15 (revised same day — control-room review `4701015790`).

## Scope

Resolves the specific gap PR #163 (`AdamsOdoo/Adams#163`, draft, unmerged,
head `655e1cd744c9a9c9d82d65a926369168e0429de0`) identified: a
transaction-scoped row lock (`try_lock_for_update`) alone does not durably
own a job across a PostgreSQL rollback, so after a genuine concurrency
failure, (a) another worker can legitimately claim the released row and
re-invoke the real handler, and (b) the recovered job's bounded auto-retry
class (`concurrency_race_conflict`) schedules a further automatic replay —
in both cases, with no proof that a prior Shopify transport did not already
occur.

**This revision narrows what is decided *now* to Layer 1 only**: a
fail-closed replay-policy registry that makes it structurally impossible for
a future mutation handler to silently inherit today's read-safe retry
behavior, while leaving PR #163's mechanism and current read-only retry
behavior exactly as shipped. Layer 2 (durable execution ownership, Option A,
and the rest of the original package's mutation-hardening design) is
recorded as the correct future architecture but is **not decided or
authorized by this record** — it is reopened as its own future decision the
moment a Shopify-mutation domain is proposed for implementation (see
"Decision proposed," Layer 2, below).

**Does not** re-litigate or reopen any already-accepted decision (DEC-005,
DEC-006, DEC-008, DEC-009, DEC-010, DEC-011, DEC-013…DEC-025) — Layer 1
extends DEC-009's ambiguous-outcome rule only insofar as its fail-closed
default prevents an undeclared handler from relying on
`concurrency_race_conflict`'s blanket auto-retry; it does not change
DEC-009's taxonomy. **Does not** decide the exact reconciliation-read state
machine for a future mutation sub-class, and does not decide anything about
a specific future mutation domain (fulfillment/inventory-export/refunds)
beyond their default-safe (fail-closed) classification.

## Accepted context this record builds on

- **DEC-009** (Accepted 2026-07-02): the 16-class error taxonomy, the
  `retry_waiting`/`failed_retryable`/`blocked_manual_review`/`failed_final`
  state machine, and the already-accepted **ambiguous-outcome rule**: a
  Shopify temporary/network failure on a non-`@idempotent` write is never
  blindly auto-retried. Layer 1's registry is the mechanism that keeps that
  rule from being silently bypassed by an undeclared future `job_type`
  (companion doc §2.2).
- **DEC-025** (Accepted 2026-07-08): explicitly left "which job-claiming
  concurrency mechanism to use" and "the job-claiming-time concurrency
  guard" as **named, undecided** architecture questions. Layer 1's
  acceptance of PR #163's mechanism as-is (for current read-only scope) is
  a partial, scope-limited answer to that named-open item; full resolution
  (multi-worker/multi-server proof) remains owed, tracked at SRR-04/SRR-09.
- **PR #163's accepted progress** (not yet merged, still draft): re-raising
  genuine PostgreSQL concurrency exceptions instead of routing them through
  an already-aborted transaction; the re-lock-and-revalidate recovery
  discipline. **Layer 1 accepts this mechanism exactly as shipped, gated by
  the new registry — it does not modify it.**
- **`sync-engine-risk-register.md` SRR-03**: the pre-existing, already-OPEN
  risk row tracking this exact problem family, runtime-confirmed by PR #153
  as `DEF-PB-1`. **Remains OPEN after this record** — Layer 1 does not close
  it; only a triggered, accepted Layer 2 plus multi-worker runtime proof
  could.
- **Rejected-approaches log**: checked in full (RA-001…RA-024); none blocks
  any option this record or its companion document evaluates; none is
  re-proposed.

## Decision proposed

### Layer 1 — decided now (routed to this record for acceptance)

1. **A small, fail-closed replay-policy registry, owned by the core
   dispatcher.** `_get_replay_policies()`, mirroring the existing
   `_get_handlers()` seam (companion doc §5), returns a `job_type ->
   replay_policy` mapping consulted by `_recover_after_concurrency_conflict`
   before it lets `concurrency_race_conflict` auto-retry.
2. **Three declared policy classes** — not five: `local_only`,
   `remote_read_replay_safe`, `remote_effect_not_replay_safe` (companion
   doc §3.2). A more precise name for the third class was considered and
   this is it; no finer split is introduced because no current handler
   requires one.
3. **Explicit current declarations:** the core diagnostic/self-test handler
   → `local_only`; the current customer import handler → `remote_read_
   replay_safe`; the current product import handler → `remote_read_
   replay_safe` — each explicit, verified against the handler's own
   Shopify-call behavior (companion doc §2.1), never inferred from module
   name or domain adjacency.
4. **Task 012 order import is not pre-registered by this decision.** It has
   no registry entry today. When it is implemented, it must declare
   `remote_read_replay_safe` on its own, based on its own verified read-only
   design — never inherited, assumed, or pre-registered here.
5. **Missing or undeclared `job_type`s fail closed** to
   `remote_effect_not_replay_safe` — never to `remote_read_replay_safe`.
6. **A missing or conservative policy never inherits automatic remote
   replay merely because another handler is read-safe.** The registry
   lookup is keyed per `job_type`, populated only by explicit registration,
   with no "assume safe" fallback anywhere (companion doc §3.3, §5).
7. **Current read-only handlers keep exactly today's behavior, explicitly
   accepted as correct for this scope:** replaying the Shopify query is
   safe because it has no Shopify-side mutation; the failed Odoo transaction
   is rolled back; importer duplicate prevention, bindings, and uniqueness
   constraints remain the local data-integrity protection; PR #163's
   rollback, reset, re-lock, revalidation, and bounded-retry behavior is
   **accepted as sufficient** for this read-only scope, unmodified.
8. **No immediate requirement for:** `attempt_id`; `owner_worker_ref`;
   `transport_attempted`; committed `running` ownership; a stale-owner cron;
   a new model; a migration; or reconciliation infrastructure. None of these
   is proposed for implementation by Layer 1.

**No claim is made that durable attempt ownership is required for current
read-only jobs.** It is not — a replayed read has no side effect to
duplicate, so nothing about Layer 1's scope depends on, or is weakened by
the absence of, Option A's ownership protocol.

### Layer 2 — mutation hardening, deferred (not decided by this record)

Option A and the deeper mutation architecture (companion doc §4, §6, §8.2)
remain the correct future requirement **before any Shopify-write handler is
authorized** — not decided, not scheduled, and not authorized now:

- durable execution ownership (committed `running` + `attempt_id`);
- persisted attempt identity;
- transport-ambiguity tracking (`transport_attempted`);
- stale-owner recovery (timeout-driven sweep);
- Shopify idempotency-key persistence;
- reconciliation-before-retry;
- mutation-specific multi-worker runtime proof.

**Explicit reopening trigger:** inventory export, fulfillment/tracking
update, product export, refund creation, or any other Shopify mutation.
Layer 2 does **not** block current product, customer, or order read-only
UAT, and is not broken into current mandatory implementation sessions
(companion doc §9).

## Consequences

- **Positive:** closes the exact gap PR #163 found, for the scope that
  actually exists today, without discarding PR #163's accepted progress;
  makes it structurally impossible (fail-closed default plus a
  registry-completeness test) for a future mutation handler to silently
  inherit read-safe retry behavior; adds **no** new model, field, migration,
  or cron for the current scope; every currently-shipped job type's
  observable behavior is unchanged.
- **Negative / trade-offs:** Layer 1 alone does **not** close SRR-03 — it
  narrows the live-relevant surface of the gap to "no mutation handler
  exists yet," not to "the ownership question is resolved." The moment a
  mutation handler is proposed, Layer 2 must be decided **before** that
  handler ships, or the same PR #163 gap reopens for real Shopify writes.
- **Follow-ups:** Layer 1's registry (companion doc §9, Immediate Slice 1)
  is the next implementation step **after this record is accepted** — a
  small, separately authorized implementation-gate session per `CLAUDE.md`
  §9, not authorized by acceptance of this record alone. Layer 2 has no
  scheduled follow-up; it is reopened by name when triggered.

## Alternatives considered

| Alternative | Why not chosen (now) | Logged as rejected? |
| --- | --- | --- |
| Option D — transaction row lock only (PR #163 as-is) | **Not an alternative for Layer 1 — this is what Layer 1 accepts and keeps**, gated by the new registry. Proven insufficient **on its own** for a future mutation (no durable, cross-transaction ownership signal; `_recover_after_concurrency_conflict` accepts "another worker winning the post-rollback claim" as valid by its own documented contract) — which is exactly why Layer 2 exists for when a mutation handler is proposed. | Not logged as rejected — kept and extended by the registry (Layer 1), not discarded |
| Option A — committed running state + attempt token + stale-owner sweep | Correct, but disproportionate as an **immediate** requirement — no mutation handler exists for it to protect today. Deferred to Layer 2, reopened by name on the trigger conditions above. | Not logged as rejected — deferred, revisit condition: any Shopify-mutation domain authorized for implementation |
| Option B — dedicated execution-attempt/lease table | Same reasoning as the original package: more schema than any current or Layer-1 scope requires. | Not logged as rejected — deferred, revisit condition unchanged from the original package (companion doc §4) |
| Option C — durable outbox/attempt-state protocol | Correct long-term destination for a real mutation domain, heavier than Layer 1 or the initial Layer 2 slice requires now. | Not logged as rejected — deferred, revisit condition unchanged (companion doc §4) |
| A `pg_advisory_xact_lock`-based quiescence/ownership barrier | Already evaluated and rejected by the CORE-R2 disconnect-quiescence design for reasons that generalize here; not re-proposed by either layer. | Reasoning present in SRR-09 and the AR-047 analysis; not itself a formal RA-log row (pre-existing documentation gap, noted not created, by the original package) |

> No new row is added to
> [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
> by this record — Option D is kept (as Layer 1's accepted mechanism,
> registry-gated) and Options A/B/C are explicitly **deferred**, not
> rejected, each with a stated revisit condition above.

## Evidence / references

Unchanged from the original package — see the companion document's full
reference list
(`../03-architecture/core-r2-job-execution-replay-safety.md` §"References")
for the complete, citation-by-citation evidence base: in-repo code
(`shopify_connector_job.py`, `shopify_connector_job_dispatch.py`,
`shopify_connector_call_lease.py`, `shopify_connector_api_client.py`,
`shopify_connector_store.py`, both domain importers), PR #163's body and
diff, DEC-009/DEC-025/DEC-010/DEC-011, the AR-047 disconnect-quiescence
analysis, `sync-engine-risk-register.md` (SRR-03/04/09), and official Odoo
19 / Shopify Admin GraphQL API facts independently re-verified by the
original session (access date 2026-07-15) — including the confirmation
that every currently shipped handler (core diagnostic, customer import,
product import) is read-only, which is the direct basis for Layer 1's three
explicit declarations. This revision performed no new research; it
re-verified only that PR #164/PR #163's states, heads, and base SHA are
unchanged (companion doc §1 "Revision verification").

## No implementation authorized

**This record does not itself authorize implementation, even if accepted.**
It creates no code, no database DDL, no Python class, no Odoo module, and no
file outside `docs/03-architecture/**` and `docs/04-decisions/**`. The
no-code gate (`CLAUDE.md` §4–§5) remains in force.

If accepted, the **next** step is a small, separately-authorized
implementation-gate session scoped to companion doc §9 Immediate Slice 1
(the registry only — no schema, no model, no cron) — not implied or opened
by this record's acceptance alone, per `CLAUDE.md` §9. Layer 2 has no
implementation step to authorize yet; it is not reopened until one of its
named trigger domains is separately proposed.

**PR #163 remains open, draft, and unmerged, and is not modified by this
record.**
