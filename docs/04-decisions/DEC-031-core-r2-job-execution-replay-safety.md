# DEC-031 — CORE-R2 Durable Job Execution Ownership & Remote Replay Safety (AR-048)

> **Proposed for ChatGPT review — NOT accepted.** This record resolves
> **AR-048** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
> Full evidence, option analysis, and self-critique live in the companion
> document,
> [`../03-architecture/core-r2-job-execution-replay-safety.md`](../03-architecture/core-r2-job-execution-replay-safety.md).
> **Acceptance would not by itself authorize implementation** — a future,
> separately authorized implementation-gate session is still required
> (`CLAUDE.md` §9), sliced in the companion document §9.

## Status

**Proposed for ChatGPT review.** Not accepted. Not implementation-authorizing.

## Date

2026-07-15.

## Scope

Resolves the specific gap PR #163 (`AdamsOdoo/Adams#163`, draft, unmerged,
head `655e1cd744c9a9c9d82d65a926369168e0429de0`) identified: a
transaction-scoped row lock (`try_lock_for_update`) alone does not durably
own a job across a PostgreSQL rollback, so after a genuine concurrency
failure, (a) another worker can legitimately claim the released row and
re-invoke the real handler, and (b) the recovered job's bounded auto-retry
class (`concurrency_race_conflict`) schedules a further automatic replay —
in both cases, with no proof that a prior Shopify transport did not already
occur. This record decides the connector's **production contract** for
durable job-execution ownership and remote replay safety before further
CORE-R2 implementation is authorized. **Does not** re-litigate or reopen any
already-accepted decision (DEC-005, DEC-006, DEC-008, DEC-009, DEC-010,
DEC-011, DEC-013…DEC-025) — it extends DEC-009's ambiguous-outcome rule to a
second failure source and resolves DEC-025's explicitly-named-open
"job-claiming-time concurrency guard" item (see Accepted context below).
**Does not** decide the exact reconciliation-read state machine for a future
`remote_mutation_reconcile_before_retry` job, and does not decide anything
about a specific future mutation domain (fulfillment/inventory-export/
refunds) beyond their default-safe classification.

## Accepted context this record builds on

- **DEC-009** (Accepted 2026-07-02): the 16-class error taxonomy, the
  `retry_waiting`/`failed_retryable`/`blocked_manual_review`/`failed_final`
  state machine, and — the direct precedent this record generalizes — the
  already-accepted **ambiguous-outcome rule**: a Shopify temporary/network
  failure on a non-`@idempotent` write is never blindly auto-retried; it
  either verifies via a safe read or routes to `blocked_manual_review`. This
  record extends that same rule to a **second** ambiguity source DEC-009 did
  not contemplate: a **local** PostgreSQL concurrency failure occurring
  *after* a transport attempt, currently misclassified under the blanket
  auto-retry class `concurrency_race_conflict` (companion doc §2.2).
- **DEC-025** (Accepted 2026-07-08): explicitly left "which job-claiming
  concurrency mechanism to use" and "the job-claiming-time concurrency
  guard" as **named, undecided** architecture questions. This record is the
  direct, expected resolution of that named-open item, not a reopening of
  anything DEC-025 settled.
- **PR #163's accepted progress** (not yet merged, still draft): re-raising
  genuine PostgreSQL concurrency exceptions instead of routing them through
  an already-aborted transaction; the re-lock-and-revalidate recovery
  discipline. This record's recommended architecture (Option A, below)
  extends — does not discard — this mechanism.
- **`sync-engine-risk-register.md` SRR-03**: the pre-existing, already-OPEN
  risk row tracking this exact problem family, runtime-confirmed by PR #153
  as `DEF-PB-1`.
- **Rejected-approaches log**: checked in full (RA-001…RA-024); none blocks
  any option this record evaluates; none is re-proposed.

## Decision proposed

Adopt **effectively-once delivery, differentiated by declared operation
class** (not a single global delivery semantic), backed by:

1. **Durable ownership: Option A** — commit `state='running'` **and** a new
   opaque `attempt_id`/`owner_worker_ref` immediately after claim, *before*
   the handler runs (two commits per dispatched job instead of one);
   finalize only after re-validating the `attempt_id` still matches under a
   re-acquired row lock; recover a stale-`running` job via a new,
   timeout-driven sweep — never a blind requeue. Extends, does not replace,
   PR #163's re-lock-and-revalidate mechanism. Full rationale and rejected
   alternatives (Option D — PR #163 alone, insufficient; Option B — a
   dedicated attempt/lease table, deferred as unnecessary at current scope;
   Option C — a durable outbox protocol, correct long-term destination but
   heavier than this scope requires; the existing `shopify.connector.call.
   lease` — proven **not** reusable, its lifecycle ends before the job's own
   terminal commit): companion doc §4.
2. **A fail-closed replay-safety registry** (`_get_replay_policies()`,
   mirroring the existing `_get_handlers()` seam): every `job_type` must be
   explicitly declared as one of `local_only` /
   `remote_read_replay_safe` / `remote_mutation_idempotent` /
   `remote_mutation_reconcile_before_retry` /
   `remote_mutation_ambiguous_manual_review`. An **undeclared** `job_type`
   defaults to the most conservative class,
   `remote_mutation_ambiguous_manual_review` — never inherited read-safe
   behavior. A static test must fail the build if any handler lacks a
   registry entry. Companion doc §5.
3. **Current customer/product import job types classified
   `remote_read_replay_safe`, explicitly** — because they issue only
   read-only GraphQL queries (verified directly against
   `shopify_connector_product_importer.py`/`shopify_connector_customer_
   importer.py`), never inferred from module name or handler naming. Task
   012 order import is classified **separately**, on its own frozen
   read-only design, never grouped by domain adjacency. Every future
   export/fulfillment/inventory-mutation/refund job type has **no** registry
   entry yet and therefore defaults to non-replay-safe until its own
   idempotency or reconciliation contract is separately decided. Companion
   doc §5.
4. **The smallest additive vocabulary change**: no 17th `error_class`. A new
   job-level `transport_attempted` field (Boolean, set generically by the
   dispatcher immediately before any handler-driven mutation call) is
   consulted, alongside the replay-policy registry, to decide whether a
   caught `concurrency_race_conflict` may still auto-retry (no transport
   attempted) or must route to the **existing** `blocked_manual_review` /
   `manual_review_subreason='duplicate_risk'` outcome (transport attempted,
   non-idempotent mutation, ambiguous). `duplicate_risk` already exists in
   the accepted vocabulary (`MANUAL_REVIEW_SUBREASON_SELECTION`) — no new
   state or error class is required for this outcome. Companion doc §7.

Full option comparison, crash/stale-owner recovery table, state/error
mapping, and self-critique against every named adversarial scenario: see the
companion document in full.

## Consequences

- **Positive:** closes the exact gap PR #163 found, without discarding its
  accepted progress; makes it structurally impossible (via a fail-closed
  default plus a static completeness test) for a future mutation handler to
  silently inherit read-safe retry behavior; adds no new model/table for the
  current scope; every new field is additive/inert for existing jobs and
  every currently-shipped (read-only) job type's observable behavior is
  unchanged, while its crash-recovery mechanics strictly improve.
- **Negative / trade-offs:** two commits per dispatched job instead of one
  (bounded, small overhead); a second independent timeout-driven mechanism
  (the stale-owner sweep) alongside the existing disconnect-quiescence
  controller, whose interaction is not yet jointly analyzed (open question);
  does not resolve the still-open multi-server/live-runtime proof obligation
  inherited from SRR-04/SRR-09/DEC-025 — this record's ownership protocol
  does not depend on that proof to be correct, but the proof is still owed
  before SRR-03 can close.
- **Follow-ups:** nine implementation slices proposed, none authorized by
  this record (companion doc §9); six open questions logged (companion doc
  §11), none blocking acceptance of the *semantic contract* itself.

## Alternatives considered

| Alternative | Why not chosen | Logged as rejected? |
| --- | --- | --- |
| Option D — transaction row lock only (PR #163 as-is) | Proven insufficient: no durable, cross-transaction ownership signal; accepts "another worker winning the post-rollback claim" as valid by its own documented contract; `concurrency_race_conflict` remains unconditionally auto-retried regardless of transport occurrence | Not logged as a rejected *approach* (RA log) — it is PR #163's own already-shipped mechanism, kept and extended (§1), not discarded |
| Reusing/extending `shopify.connector.call.lease` for job-level ownership | Proven, not assumed, that its lifecycle (admit→reconciliation, both on independent side-cursors) ends before the job's own terminal-state commit — the exact window this gap concerns; repurposing it would degrade the disconnect controller's own timing accuracy | Not logged — an evaluated-and-declined design choice for *this* record, not a rejected architecture approach in the RA-log sense; no prior RA row conflicts with it |
| Option B — dedicated execution-attempt/lease table | Not wrong, but more schema than current scope (all shipped handlers read-only) requires; `job.log` already provides most of the audit value; explicitly deferred, not rejected, pending a real future mutation domain's needs | Not logged as rejected — deferred, revisit condition: a future mutation domain requiring full per-attempt audit history beyond `job.log` |
| Option C — durable outbox/attempt-state protocol | Correct long-term destination, especially once real Shopify mutations (fulfillment/inventory export/refunds) are authorized, but heavier implementation complexity than this scope requires now; Option A's schema is designed as a strict subset so this remains available later without rework | Not logged as rejected — deferred, revisit condition: a future mutation domain's implementation-scope session |
| A `pg_advisory_xact_lock`-based quiescence/ownership barrier | Already evaluated and rejected by the CORE-R2 disconnect-quiescence design (`disconnect-quiescence-remediation-analysis.md` §10, cited in `sync-engine-risk-register.md` SRR-09) for the same reasons that generalize here (no independent cross-transaction visibility, no holder count/timestamps) — not re-proposed | Reasoning present in SRR-09 and the AR-047 analysis; not itself a formal RA-log row (a pre-existing documentation gap noted, not created, by this record) |

> No new row is added to
> [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
> by this record — none of the four durable-ownership options is a
> **rejected approach** in that log's sense; Option D is kept (extended, not
> discarded) and Options B/C are explicitly **deferred**, not rejected, each
> with a stated revisit condition above.

## Evidence / references

See the companion document's full reference list
(`../03-architecture/core-r2-job-execution-replay-safety.md` §"References")
for the complete, citation-by-citation evidence base: in-repo code
(`shopify_connector_job.py`, `shopify_connector_job_dispatch.py`,
`shopify_connector_call_lease.py`, `shopify_connector_api_client.py`,
`shopify_connector_store.py`, both domain importers), PR #163's body and
diff, DEC-009/DEC-025/DEC-010/DEC-011, the AR-047 disconnect-quiescence
analysis, `sync-engine-risk-register.md` (SRR-03/04/09), and official Odoo
19 (`github.com/odoo/odoo`, `19.0` branch) / Shopify Admin GraphQL API
(`shopify.dev`) facts **independently re-verified by this session**
(companion doc §2.3–§2.4, access date 2026-07-15) — including the
confirmation that `refundCreate` and the inventory/location mutation family
become `@idempotent`-mandatory under API 2026-04, that fulfillment's core
mutations and `productSet` are confirmed **not** on Shopify's
idempotent-mutation surface, and that Odoo's own cron-acquisition code
already treats a concurrency conflict as "move to the next job," never as
"retry in place" — independent corroboration for this record's recovery
direction.

## No implementation authorized

**This record does not authorize implementation**, even if accepted. This
record creates no code, no database DDL, no Python class, no Odoo module,
and no file outside `docs/03-architecture/**` and `docs/04-decisions/**`.
The no-code gate (`CLAUDE.md` §4–§5) remains in force. A future,
separately-authorized implementation-gate session, sliced per the companion
document §9, is required before any of §1's schema/registry/sweep changes
may be written as code. **PR #163 remains open, draft, and unmerged, and is
not modified by this record.**
