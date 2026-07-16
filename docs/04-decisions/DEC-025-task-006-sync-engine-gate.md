# DEC-025 — Task 006 Sync Engine Architecture Gate (Proposed)

> *Title note (2026-07-16, Fable gap-closure mission): the "(Proposed)" suffix
> in the H1 above is a stale artifact of the drafting phase; this record is
> **Accepted** per the banner below. The title is left unedited to preserve
> link/anchor stability.*

> **Accepted architecture decision record.** ChatGPT accepted this record on
> **2026-07-08**, after PR #128's governance revisions (direct, full
> inspection of the two pre-006A baseline sources; the `AR-030` addition;
> the stale-wording consistency fix) — see *Acceptance note* below. This
> record accepts the **architecture gate only**, synthesized in
> [`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md).
> It does **not** resolve or reopen AR-002 through AR-014 (already accepted,
> unchanged). It resolves the corresponding row, **`AR-030`**, in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> — **`AR-030` is now Accepted**, mirroring this record's own acceptance
> exactly; see this record's "Architecture-review-log note" below.
> **Acceptance does not by itself authorize implementation.** No Task 006C
> and no implementation-scope document is created or authorized by this
> acceptance — both remain a future, separately authorized session.

## Status

**Accepted by ChatGPT.** Acceptance date: **2026-07-08**. Not
implementation-authorizing on its own — see *No implementation authorized*
below.

## Acceptance note (2026-07-08)

- **Accepted by ChatGPT** for PR #128, after this PR's governance revisions
  were applied: direct, full inspection of the two pre-006A baseline
  sources (`shopify-official-api-notes.md`, `odoo-official-architecture-
  notes.md`); the addition of the corresponding `AR-030` row in
  `../05-qa/architecture-review-log.md`; and the consistency fix removing
  this record's stale "does not itself open any new AR row" wording.
- **This accepts the architecture gate only** —
  [`sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md)
  and this record, DEC-025, as the accepted architecture-level shape for the
  future domain-neutral sync engine.
- **This does not authorize implementation.** No code, addon file, Python
  class, Odoo module, view, controller, security file, migration, CI/
  workflow file, or domain module is created or authorized by this
  acceptance.
- **Task 006C, and any implementation-scope document, remain a future,
  separately authorized session** — not created, not started, and not
  implied by this acceptance.
- **Preserved, unchanged by acceptance:** every item in *Open questions*
  below remains exactly as open as before — VAL-B2 (deferred/not passed),
  MBQ-05 (partially routed/open — token acquisition for many unrelated
  customers), TD-002 (Open), the fulfillment API model (unresolved),
  product first-sync deduplication thresholds (domain design work), and
  Lite/Full packaging (not finalized) — none is resolved, narrowed, or
  silently decided by this acceptance. Every item in *Risks and required
  runtime validation* below also stands unchanged — no concurrency claim is
  treated as proven, and live Odoo.sh/multi-server runtime proof is still
  required before any implementation relies on one.

## Date

2026-07-08.

## Scope

**Task 006B only** — a proposed architecture-level gate for the future
**domain-neutral sync engine**, synthesizing the accepted Task 006A research
package (PR #123, #124, #125, #126, #127, all merged into
`Shopify-connector`) into: architecture principles, a proposed core-engine
shape, a job-trigger model, a retry/failure policy, an idempotency/
duplicate-prevention layering, the Odoo execution substrate this engine would
run on, the Shopify API behavior it must accommodate, and core-vs-domain
responsibility boundaries. Full detail lives in the companion document,
[`sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md).

**Does not decide:**

- OAuth/token-acquisition architecture for many unrelated customers (MBQ-05
  branch B).
- VAL-B2 (live Shopify Admin API validation).
- TD-002 (`read_fulfillments` readiness-scope concern).
- The fulfillment API model (legacy `Fulfillment` vs. `FulfillmentOrder`).
- Product first-sync deduplication thresholds (exact match-confidence
  mechanics — MBQ-59's residual).
- Lite/Full packaging/product strategy.
- Any domain sync logic, field mapping, or business rule beyond what the
  already-accepted Master Blueprint (DEC-013/014/015/016) states.
- Task 006C or any implementation-scope document.
- Exact Odoo model/field names beyond what Task 001–005/AR-019 already
  accepted — every name in the companion gate document is either an
  already-accepted identifier (cited as such) or an explicit
  candidate/architecture-level placeholder, never a new implementation-final
  name.

## Accepted research inputs this proposal draws on

- **Task 006A research package** (all merged, `Shopify-connector`):
  `sync-engine-source-inventory.md`, `sync-engine-source-notes.md`,
  `sync-engine-evidence-map.md`, `sync-engine-open-questions.md`,
  `sync-engine-risk-register.md` (PR #125, final synthesis);
  `sync-engine-odoo-repo-source-notes.md` (PR #124, Odoo/repo substrate);
  `sync-engine-queue-idempotency-source-notes.md` (PR #126, queue/
  idempotency/retry/backoff/dead-letter reference patterns);
  `sync-engine-competitor-pattern-notes.md` (PR #123, competitor/common
  sync patterns); `task-006a-completeness-audit.md` (PR #127, confirming all
  four shards merged and ancestor-verified, and recommending proceeding to
  Task 006B without a separate Shopify-shard backfill).
- **Prior accepted architecture decisions:**
  [`DEC-005`](./DEC-005-sync-orchestration-strategy.md) (sync orchestration —
  webhook + `ir.cron` + internal queue, manual sync, mandatory
  reconciliation, per-record isolation, retry counters, dead/final-failed
  state; OCA `queue_job` deferred, not adopted);
  [`DEC-009`](./DEC-009-error-retry-idempotency-strategy.md) (classified
  16-error-class retry taxonomy; layered idempotency; ambiguous-outcome
  rule); [`DEC-024`](./DEC-024-task-005-closure.md) (Task 005 closure —
  connection-lifecycle substrate accepted, complete, and live-validated;
  four unselected next-task candidates named, including "sync engine
  skeleton gate").
- **Master Blueprint Part A** (`master-blueprint-core-substrate.md`,
  accepted via DEC-013): module boundary/responsibilities, the job/queue/
  log/error abstraction (§D), the seven domain-extension seams (§A.5), and
  the accepted binding schema shape (§C.8, resolving MBQ-11).
- **Master Blueprint Open Questions register** (`master-blueprint-open-
  questions.md`), specifically the current status of MBQ-05, MBQ-16, MBQ-62
  (→ DEC-019, `odoo_event` job source), MBQ-63 (inventory webhooks not
  implemented Phase 1), MBQ-65 (product webhooks: enqueue-only + follow-up
  read).
- **Technical Debt Register** (TD-001 Resolved, TD-002 Open) and
  **Rejected Approaches Log** (RA-004 OCA `queue_job` reference-only;
  RA-013 no duplicate domain queue/log/binding abstractions; RA-014 through
  RA-017 the accepted retry/idempotency taxonomy) — checked before drafting
  this proposal, per `CLAUDE.md` §10; **no rejected approach is
  re-proposed** by this record.

## Accepted architecture decisions

This record accepts, at architecture level only (not implementation-final):

1. **The sync engine is domain-neutral**, with core owning orchestration/
   job-lifecycle/retry/logging/visibility/guardrails and domain modules
   owning handlers/mapping/dedup/payload interpretation/Shopify operations/
   Odoo mutations, connected only through the seven named extension seams
   (gate §B, §C).
2. **All five business job triggers** (`webhook`, `manual_sync`,
   `scheduled_sync`, `reconciliation`, `odoo_event`) **converge on one job
   execution mechanism**, with trigger source (`job_source`) kept
   structurally distinct from domain handler (`job_type`) (gate §D).
3. **A classified, bounded retry policy** (DEC-009's existing 16-class
   taxonomy) governs auto-retry, ambiguous-outcome handling, manual-fix,
   operator-confirmation, and conservative-never-silent classes, honoring
   Shopify's REST 429/`Retry-After` and GraphQL HTTP-200/`THROTTLED`-body
   signals (gate §E).
4. **A layered idempotency/duplicate-prevention architecture**, with core
   owning the job idempotency key, the operation-scope serialization guard,
   and webhook delivery-ID dedup, and domain modules owning `@idempotent`
   mutation handling and binding/match-key uniqueness — leaving the
   job-*claiming*-time concurrency guard as an explicitly undesigned
   candidate (gate §F).
5. **`ir.cron` as the Phase 1 execution substrate**, with OCA `queue_job`
   remaining reference-only (RA-004 unchanged), and every concurrency claim
   about `ir.cron`'s row-locking behavior labeled as requiring live Odoo.sh
   (and, where relevant, multi-server) runtime proof before implementation
   relies on it (gate §G).
6. **Shopify API behaviors this engine must accommodate**: GraphQL-preferred
   direction, cost/rate-limit-aware batching, differing REST/GraphQL
   throttle signaling, cursor-pagination checkpoint implications, bulk
   operations as a non-default/non-resumable candidate, and mandatory
   reconciliation given non-guaranteed webhook delivery (gate §H).
7. **A core-vs-domain responsibility table** for product, customer, sale/
   order, inventory, fulfillment, and a not-yet-scoped future accounting/
   refund/payout domain, restating (not expanding) the already-accepted
   DEC-008/010/011/013/014 module boundaries (gate §I).

## Explicit non-decisions

Per `CLAUDE.md` §8, the following are **not** decided by this record, and
must not be treated as decided by any future session citing DEC-025:

- **No implementation is authorized.** No addon file, Python, XML, CSV,
  manifest, security, migration, CI/workflow, controller, view, wizard,
  OAuth, or domain-sync code is created or implied.
- **No Task 006C or implementation-scope document is created or
  authorized.**
- **No final Odoo model/field name is introduced.** Every name used in the
  companion gate document is either already-accepted (Task 001–005/AR-019)
  or explicitly marked candidate/architecture-level.
- **OCA `queue_job` is not adopted.** RA-004 remains binding; its revisit
  condition is not met by this record.
- **VAL-B2, MBQ-05 (token acquisition for many unrelated customers), TD-002,
  the fulfillment API model, product first-sync dedup thresholds, and
  Lite/Full packaging are not resolved** — each remains exactly as open as
  stated in the "Open questions" section below.
- **No job-claiming concurrency mechanism is selected** (`SKIP LOCKED` vs.
  `lock_for_update()` vs. advisory locks vs. a combination) — named as an
  open architecture question, not decided.
- **No checkpoint/resume ownership (core vs. domain) is decided.**
- **No retry-count/backoff constant is finalized** — MBQ-16's planning
  defaults are cited as adjustable, not binding.

## Open questions

Carried forward unchanged from Task 006A (full detail and citations in the
companion gate document §K and in
[`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md)):

- VAL-B2 — deferred / not passed.
- MBQ-05 — Partially routed / Open (token acquisition for many unrelated
  customers).
- TD-002 — Open.
- Fulfillment scope/API model — cannot be finalized yet.
- Product first-sync deduplication — requires domain design.
- The 16-vs-17 `@idempotent` mutation-count discrepancy — unresolved,
  immaterial to this gate.
- The OCA `queue_job` `--workers > 0` vs. `> 1` wording discrepancy —
  unresolved, non-blocking.
- Lite/Full packaging — product strategy, not decided here.
- New, this gate: which job-claiming concurrency mechanism to use; whether
  checkpoint/resume state is core- or domain-owned; whether the readiness-
  check extension-seam pattern literally extends to job-type dispatch.

## Risks and required runtime validation

1. **Disconnect / in-flight-job race (SRR-03).** Whether a business job
   already `running` inside an in-flight `ir.cron` batch is fully
   interrupted by a concurrent disconnect is not proven by any source.
   **Requires live Odoo.sh proof** before any design relies on the race
   being closed.
   **[Program-state update — 2026-07-16]** This risk is retained as the
   record's as-of-2026-07-08 statement. SRR-03 has since been runtime-proven
   and **CLOSED** post-Wave-1 (per the 2026-07-16 reconciliation in
   [`../03-architecture/task-012-order-import-decision-closure.md`](../03-architecture/task-012-order-import-decision-closure.md)
   and [`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md));
   the required live proof now exists. Items 2–3 (SRR-04/SRR-09) stand as
   written — they were reduced, not closed, and still require their tests.
2. **Cron job-acquisition concurrency under real load (SRR-04, three-shard-
   corroborated open question).** Whether Odoo's automatic RPC-layer
   serialization retry protects a cron job's own domain-record-processing
   code is a source-backed inference, not a proven fact. **Requires an
   actual concurrency test.**
3. **Multi-server / load-balanced deployment coordination (SRR-09).**
   Whether `ir.cron`'s row-lock-only job acquisition is sufficient with no
   additional cross-server coordination when multiple Odoo application
   servers share one PostgreSQL database is unconfirmed. **Requires an
   actual multi-server test.**
4. **Savepoint-count performance ceiling (SRR-01).** PostgreSQL performance
   degrades past 64 savepoints per transaction — a batch-sizing constraint
   to validate under realistic catalog/order volumes, not merely a
   documentation warning to note.
5. **GraphQL throttle body-vs-status handling (SRR-08).** A client that
   checks only HTTP status (not the response body) for a GraphQL
   `THROTTLED` code will silently miscount a throttled call as successful —
   a concrete implementation-time requirement, not merely theoretical.
6. **Retry-amplification across layers (SRR-02).** Uncoordinated retry
   logic at more than one layer (API client + job layer + operator manual
   retry) could amplify load against Shopify's own rate limits during an
   incident — mitigated by concentrating retry logic at the job layer only,
   per the design already implied by DEC-005/DEC-009.
7. **Repeat of the PR #121 failure pattern (SRR-06).** This project has
   direct precedent of a concurrency/timing-dependent defect that passed
   every static and adversarial review but only manifested under live
   Odoo.sh execution (`DEC-024` §4). Any future sync-engine concurrency
   mechanism must be validated live, not merely statically, before it is
   trusted.

## Consequences

- **Positive:** gives a future implementation-scope session (not authorized
  by this record) a synthesized, evidence-cited architecture shape to draft
  against, rather than starting from raw Task 006A research; makes explicit
  which concurrency/idempotency questions still require runtime proof before
  any implementation task can safely assume an answer.
- **Negative / trade-offs:** does not resolve any of the listed open
  questions; several architecture-level shapes (job-claiming mechanism,
  checkpoint ownership) remain candidates only, meaning a future
  implementation-scope session will still need its own design work before
  code can be written.
- **Follow-ups:** none authorized by this record, even now that it is
  accepted. The recommended next step is a separately-scoped, separately-
  authorized Task 006C implementation-scope session — not created, and not
  started, by this acceptance.

## Alternatives considered

No alternative architecture shape was evaluated to rejection by this
record — this is a synthesis of already-accepted decisions (DEC-005,
DEC-009, DEC-013) into gate form, not a fresh architecture-option
evaluation. No new row is added to
[`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
by this record.

## Architecture-review-log note

`../05-qa/architecture-review-log.md` records each AR-numbered architecture
question through its "Not decided" → "Proposed for ChatGPT review" →
"Accepted" lifecycle — the same pattern DEC-004/005/006/010/011/013 through
DEC-020 and every subsequent Task 00X gate/decision record already followed.
**This acceptance moves the corresponding row, `AR-030`, from "Proposed for
ChatGPT review" to "Accepted by ChatGPT (2026-07-08)"** — mirroring this
record's own acceptance exactly, in the same acceptance-patch pattern
already used elsewhere in that log (e.g. the AR-010/DEC-013 or AR-018/audit
acceptance pattern). **Implementation remains unauthorized** by this
acceptance: per this log's own "How to use" §1 instruction, an `Accepted`
row means the *architecture proposal* is accepted, not that any code, Odoo
module, or implementation task is thereby created or authorized — `AR-030`'s
own Follow-up action column states this explicitly.

## No implementation authorized

**Acceptance of this architecture decision does not by itself authorize
implementation.** This record creates no code, no database DDL, no Python
class, no Odoo module, and no file outside `docs/03-architecture/**` and
`docs/04-decisions/**`. The no-code gate (`CLAUDE.md` §4–§5) remains in
force. **This record's current status is Accepted by ChatGPT** (acceptance
date 2026-07-08) — but implementation remains blocked until ChatGPT
separately opens a dedicated implementation gate per
`../05-qa/quality-feedback-loop.md` §10 and authorizes a Task 006C
implementation-scope document per `CLAUDE.md` §9. **No Task 006C and no
implementation-scope file is created or authorized by this acceptance** —
both remain a future, separately authorized session.

## Evidence / references

- [`../03-architecture/sync-engine-architecture-gate.md`](../03-architecture/sync-engine-architecture-gate.md)
  — the full proposed architecture gate this record summarizes.
- [`../05-qa/task-006a-completeness-audit.md`](../05-qa/task-006a-completeness-audit.md)
  — access: Accessible, this repository, observed 2026-07-08.
- [`../01-research/sync-engine-source-inventory.md`](../01-research/sync-engine-source-inventory.md),
  [`sync-engine-source-notes.md`](../01-research/sync-engine-source-notes.md),
  [`sync-engine-evidence-map.md`](../01-research/sync-engine-evidence-map.md)
  — access: Accessible, this repository, observed 2026-07-08.
- [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md),
  [`sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md)
  — access: Accessible, this repository, observed 2026-07-08.
- [`../01-research/sync-engine-odoo-repo-source-notes.md`](../01-research/sync-engine-odoo-repo-source-notes.md),
  [`sync-engine-queue-idempotency-source-notes.md`](../01-research/sync-engine-queue-idempotency-source-notes.md),
  [`sync-engine-competitor-pattern-notes.md`](../01-research/sync-engine-competitor-pattern-notes.md)
  — access: Accessible, this repository, observed 2026-07-08.
- [`DEC-005-sync-orchestration-strategy.md`](./DEC-005-sync-orchestration-strategy.md),
  [`DEC-009-error-retry-idempotency-strategy.md`](./DEC-009-error-retry-idempotency-strategy.md),
  [`DEC-024-task-005-closure.md`](./DEC-024-task-005-closure.md) — access:
  Accessible, this repository.
- [`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md),
  [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  — access: Accessible, this repository.
- [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md),
  [`rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) —
  access: Accessible, this repository.
- [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md),
  [`odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md)
  — pre-006A baseline sources, **directly read in full during this
  revision** (2026-07-08); access: Accessible, this repository. Task 006A's
  own deeper research remains controlling wherever it re-verifies or
  corrects a baseline fact — see the companion gate document's "Revision
  note."
