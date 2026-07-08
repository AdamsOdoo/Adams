# Sync Engine — Proposed Architecture Gate (Task 006B)

> **Proposed architecture gate. Not an accepted decision. Not implementation
> authorization.** This document converts the accepted Task 006A research
> package (PR #123 competitor/common-pattern research, PR #124 Odoo/repo
> substrate research, PR #126 queue/idempotency/retry/backoff/dead-letter
> research, PR #125 final synthesis/evidence map, PR #127 completeness audit
> — all merged into `Shopify-connector`) into a proposed architecture-level
> shape for the future **domain-neutral sync engine**. Every claim below is
> classified per `CLAUDE.md` §8 (**Fact** / **Competitor claim** / **Inference**
> / **Recommendation** / **Decision** / **Open question**). Nothing in this
> document is a **Decision** — the companion record
> [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md)
> is **Status: Proposed / Pending ChatGPT review**, not Accepted. The companion
> QA checklist is
> [`../05-qa/task-006b-architecture-gate-review-checklist.md`](../05-qa/task-006b-architecture-gate-review-checklist.md).

- **Session date:** 2026-07-08.
- **Branch:** `claude/task-006b-sync-engine-gate-865mw5` (harness-designated
  session branch; see the "Branch note" at the end of this document).
- **Based on `origin/Shopify-connector` HEAD:**
  `3207791412ebedbc83eceaf70592df8c8df0d97a` (PR #127 merge commit),
  confirmed an ancestor of this branch's base before any edit.
- **Primary evidence base:** the five Task 006A documents —
  [`../05-qa/task-006a-completeness-audit.md`](../05-qa/task-006a-completeness-audit.md),
  [`../01-research/sync-engine-source-inventory.md`](../01-research/sync-engine-source-inventory.md),
  [`../01-research/sync-engine-source-notes.md`](../01-research/sync-engine-source-notes.md),
  [`../01-research/sync-engine-evidence-map.md`](../01-research/sync-engine-evidence-map.md),
  [`../05-qa/sync-engine-open-questions.md`](../05-qa/sync-engine-open-questions.md),
  [`../05-qa/sync-engine-risk-register.md`](../05-qa/sync-engine-risk-register.md),
  [`../01-research/sync-engine-odoo-repo-source-notes.md`](../01-research/sync-engine-odoo-repo-source-notes.md),
  [`../01-research/sync-engine-queue-idempotency-source-notes.md`](../01-research/sync-engine-queue-idempotency-source-notes.md),
  [`../01-research/sync-engine-competitor-pattern-notes.md`](../01-research/sync-engine-competitor-pattern-notes.md) —
  read in full this session, plus the accepted governance layer
  ([`DEC-005`](../04-decisions/DEC-005-sync-orchestration-strategy.md),
  [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md),
  [`DEC-024`](../04-decisions/DEC-024-task-005-closure.md),
  [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md),
  [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md),
  [`../05-qa/technical-debt-register.md`](../05-qa/technical-debt-register.md),
  [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)),
  all read in full this session. No new external research (no fresh
  `WebFetch`/`WebSearch`) was performed by this session; this is a synthesis
  session, not a research session.
- **Revision note (this PR revision, 2026-07-08):** `docs/01-research/
  shopify-official-api-notes.md` and `docs/01-research/odoo-official-
  architecture-notes.md` (the pre-006A baselines, `R24`/`R25`) were **directly
  read in full during this revision**, in response to control-room review
  feedback on the first version of this gate, which had cited them only via
  the Task 006A synthesis layer rather than independently. Both remain
  **baseline / pre-006A sources** — Task 006A's own deeper research (PR #124's
  `sync-engine-odoo-repo-source-notes.md`; PR #126's `sync-engine-
  queue-idempotency-source-notes.md`; the source inventory's §3 "Synthesis
  hierarchy" and version-caveats section) remains the **controlling, latest
  source** wherever it re-verifies, sharpens, or corrects a baseline fact —
  consistent with this repo's own "latest dated refresh wins" convention,
  already used throughout both baseline documents' own revision history.
  Direct inspection **did not require any material change to this gate's
  proposed architecture content.** Every fact this gate cites from the two
  baselines (GraphQL-preferred direction, REST/GraphQL rate-limit mechanics,
  webhook HMAC/dedup/retry facts, bulk-operation mechanics, the `ir.cron`
  failure-count/deactivation constants, the "no core async job queue, only
  `ir.cron`" inference, OCA `queue_job` as community/reference-only) is
  confirmed present and unchanged in the baseline text, and every fact this
  gate cites that goes *beyond* the two baselines (the GraphQL HTTP-200/
  `THROTTLED`-body behavior, `SKIP LOCKED`/`lock_for_update()` job-claiming
  precedent, the >64-savepoint performance warning, `retrying()`'s RPC-layer
  serialization retry, the 16-vs-17 `@idempotent` mutation-count discrepancy)
  is correctly attributed to Task 006A's own deeper source-level research
  (`O5`–`O9`, `OD-1`, `OD-3`, `OD-5`, `S16`, `SH-4`), not to these two
  baselines, which do not contain those facts. One genuine sharpening was
  found and is worth naming explicitly: `odoo-official-architecture-notes.md`
  describes `ir.cron`'s 5-failures-over-≥7-days deactivation as notifying
  "the DB admin" at the documentation level; Task 006A's source-level reading
  of `ir_cron.py` (`O7`) found the base `_notify_admin()` implementation is a
  `_logger.warning()` call only, explicitly meant to be overridden — a
  sharpening from "a notification occurs" to "a log line is written unless a
  real notification is wired up," not a contradiction. This gate's §E and §C
  already cited the sharper, source-level fact (via `O7`/SRR-05), so no
  content change was needed there either.
- **`docs/01-research/sync-engine-shopify-source-notes.md`** does not exist —
  per the accepted Task 006A completeness audit (PR #127, Recommendation A),
  its intended content is covered-by-synthesis across the source inventory
  and evidence map and is treated as such here.

---

## A. Purpose and non-goals

**[Recommendation]** This document proposes an architecture-level shape for a
future **domain-neutral sync engine** inside `shopify_connector_core`, to be
reviewed and either accepted, revised, or rejected by ChatGPT.

**This document explicitly is NOT:**

- **Not implementation authorization.** It creates no code, no Odoo module, no
  model, no view, no security file, no migration, no CI/workflow file, and no
  file outside `docs/**`. The no-code gate (`CLAUDE.md` §4–§5) remains in full
  force.
- **Not a resolution of:**
  - **OAuth / token-acquisition architecture** — MBQ-05 remains **Partially
    routed / Open**, not resolved here (§K).
  - **VAL-B2** — remains deferred / not passed (§K).
  - **TD-002** — the `read_fulfillments` readiness-scope concern remains
    **Open** (§K).
  - **The fulfillment API model** (legacy `Fulfillment` vs.
    `FulfillmentOrder`-based) — remains undecided (§K, §I).
  - **Product first-sync deduplication thresholds** — remain domain design
    work for a future product-domain task (§K, §I).
  - **Lite/Full packaging strategy** — remains product strategy, not decided
    here (§K).
- **Not a source of domain sync logic.** It adds no product, customer, order,
  inventory, or fulfillment field mapping, matching rule, or business logic
  beyond what the already-accepted Master Blueprint (DEC-013/014/015/016)
  already states at blueprint level. §I names domain responsibilities only at
  the boundary level — it does not specify how any domain module does its
  work.
- **Not a selection of Task 006C, or of any core-engine or domain-handler
  implementation spec.** See §J.

**What this document IS:** a synthesis of Task 006A's evidence into a proposed
shape for (a) the principles the sync engine must satisfy (§B), (b) the
architecture-level responsibilities of a core engine (§C), (c) how jobs enter
the system (§D), (d) retry/failure policy (§E), (e) idempotency/duplicate
prevention (§F), (f) the Odoo substrate it runs on (§G), (g) the Shopify API
behavior it must accommodate (§H), (h) core-vs-domain boundaries (§I), and (i)
what accepting this gate would — and would not — unlock (§J), while
faithfully preserving every open item Task 006A left open (§K).

---

## B. Architecture principles

Each principle below restates an **already-accepted** decision or an
**evidence-backed, high-confidence** finding from Task 006A — this document
does not invent new principles.

1. **The sync engine must be domain-neutral.** **[Accepted — DEC-005; DEC-008;
   DEC-013 (blueprint §A.2/§A.3/§K.2)]** Core owns job/queue/log dispatch;
   domain modules register via extension seams; core never imports domain
   logic. **[Inference, evidence-backed]** This is the accepted design intent,
   not a claim the mechanism is fully built — no domain-neutral operation
   *handler* registry exists yet (only the unrelated readiness-*check*
   registry; `sync-engine-odoo-repo-source-notes.md` "Current gaps";
   evidence map claim 1).
2. **Domain modules must not implement separate queue/retry/log engines.**
   **[Accepted — RA-013 (binding, rejected-approaches-log.md); DEC-008 §K.2]**
   Any domain job type is added via `selection_add` on the existing `job_type`
   field; no parallel job/log/error-class model may be created.
3. **Manual sync, scheduled sync, webhook-triggered sync, reconciliation, and
   Odoo-event-triggered sync must converge into the same job execution
   path.** **[Accepted — DEC-005; DEC-019 (`odoo_event` job source)]** All five
   business `job_source` values (`webhook`, `manual_sync`, `scheduled_sync`,
   `reconciliation`, `odoo_event`) are already declared on
   `shopify.connector.job` and gated identically by `create()`/`write()`
   (`sync-engine-source-inventory.md` R1; evidence map claim 4) — no code yet
   creates a job with any of them, but the schema and gating already treat
   them as one path, not five.
4. **Webhooks must verify and enqueue/signal work, not perform complex
   mutations directly.** **[Accepted — DEC-005; blueprint §A.5 seam 7; MBQ-65
   (product webhooks: enqueue-only, mandatory follow-up authoritative read,
   never a direct write); MBQ-63 (inventory webhooks: not implemented Phase 1,
   drift-detection candidate only)]** HMAC-verify + `X-Shopify-Webhook-Id`
   dedup + enqueue is the webhook receiver's entire job; the authoritative
   read/write happens inside the job handler, never inline in the HTTP
   request.
5. **Core owns orchestration, job lifecycle, retries, logging, visibility,
   and shared guardrails.** **[Accepted — DEC-008 §A.2 responsibilities 2–8;
   blueprint §D]** The job/queue/log/error abstraction, the error-class
   registry, the dashboard/sync-center/error-center, and the setup/readiness
   wizard are all core-owned, single-instance substrate.
6. **Domain modules own domain handlers, mapping, dedup rules, payload
   interpretation, Shopify API operations, and Odoo business-object
   mutations.** **[Accepted — DEC-008 §A.3; blueprint §K.3]** Core must never
   hold a foreign key to, or import, a domain-specific model.
7. **Domain modules register into the core through extension seams; core
   must not import domain modules.** **[Accepted — blueprint §A.5, seven
   named seams: binding-contract extension, job-type registration,
   error-class mapping, settings/flag contribution, dashboard/error-center
   contribution, setup-wizard step contribution, webhook-topic
   registration]** The readiness-check `_get_checks()` inheritance-append
   pattern (`shopify_connector_readiness_check.py`, R4) is a working, tested
   precedent for this shape, though it registers *checks*, not sync
   *operations* — adaptation, not verbatim reuse, is required
   (`sync-engine-odoo-repo-source-notes.md` §5).

---

## C. Proposed core sync engine shape

**[Recommendation]** The responsibilities below are proposed at
**architecture level only** — no model, field, or method name below is
implementation-final. Where an existing model/field already exists and is
accepted (Task 001–005 substrate), it is cited as such; where a shape is
merely a **candidate**, it is labeled explicitly.

- **Job creation/enqueue API.** **[Candidate — not yet built]** A future
  service surface that creates `shopify.connector.job` rows for the five
  business `job_source` values. Today the schema and store-state gating
  already exist (R1) but no code path creates a job with any business source
  (`sync-engine-odoo-repo-source-notes.md` "Current gaps"). This gate does
  not name the service's exact method signature.
- **Job claiming/drain loop.** **[Candidate]** One or a small number of
  `ir.cron` scheduled actions draining the queue in batches
  (**[Accepted — DEC-005]**). The concurrency-safe *claiming* mechanism itself
  (how multiple workers pick up rows without racing) is **undesigned** — the
  official Odoo precedent is `ir.cron`'s own `_acquire_one_job()`, using
  `FOR NO KEY UPDATE SKIP LOCKED` (O7/OD-1), and the row-locking primitives
  `lock_for_update()`/`try_lock_for_update()` (O9/OD-3) whose only official
  documented use case is exactly this cron-batch-processing pattern
  (`sync-engine-odoo-repo-source-notes.md` §2). Whether the engine reuses this
  pattern, the existing `operation_scope_key` unique constraint alone, or
  PostgreSQL advisory locks (a hazard-bearing alternative newly surfaced by
  PR #126, see §F) is an **open architecture question** (open questions 5,
  29, 41).
- **Execution dispatcher.** **[Candidate]** Dispatches a claimed job by
  `job_type` to a registered handler. Today `job_type` has exactly three
  values, all core/diagnostic (`core_readiness_check`,
  `core_manual_maintenance`, `core_test_connection`) — no domain job type is
  registered anywhere yet.
- **Handler registry / extension seam.** **[Candidate, precedented]** The
  `_get_checks()` inheritance-append pattern (classic Odoo `_inherit` +
  `super()` + append, already tested) is a real, working precedent for a
  future job-type/handler registry (blueprint §A.5 seam 2), but it registers
  *checks* (independently evaluated, aggregated fail-closed), not sync
  *operations* (which need dispatch, ordering, and per-operation error/retry
  semantics) — the pattern requires real adaptation, not verbatim reuse.
- **Retry scheduling.** **[Accepted policy, candidate mechanism]** DEC-009's
  classified retry policy (§E) governs *which* classes retry; the scheduling
  mechanism (a cron-driven `retry_waiting` sweep) is not yet built. MBQ-16's
  accepted implementation-planning defaults (12 attempts, exponential 30s
  base ×2, capped at 30 minutes, ±20% jitter, 24-hour window — per
  `core-naming-schema-planning.md` §9, cited via R11) are **adjustable
  planning defaults, not final production-tuned constants**, per DEC-009's
  own acceptance note.
- **Idempotency and duplicate-running guardrails.** **[Accepted, partial;
  candidate, partial]** `idempotency_key` and `operation_scope_key` with their
  DB-level `UNIQUE(store_id, ...)` constraints already exist and are
  already-tested (R1) — a real, working single-active-operation guard at job
  *creation* time. A job-*claiming*-time guard (for concurrent execution) is
  a **candidate**, undesigned (see §F).
- **Permanent-failure / manual-review surface.** **[Accepted]**
  `failed_final` and `blocked_manual_review` are already-accepted terminal/
  loop-back job states (DEC-009); the dashboard/error-center (blueprint §F/
  §H) is the accepted operator-visible surface — **not** `ir.cron`'s own
  `_notify_admin()`, which is a no-op logger call by default and must not be
  relied upon (O7; SRR-05).
- **Checkpoint/resume support.** **[Candidate, unresolved ownership]** No
  checkpoint/resume model exists today; `operation_scope_key` is a cleared
  presence/absence lock, not a cursor (`sync-engine-odoo-repo-source-notes.md`
  "Unsupported claims removed"). Whether checkpoint state is core-owned (a
  generic "resume this paginated job" primitive) or domain-owned (each import
  job manages its own cursor) is an **open question** (open question 7),
  compounded by GraphQL cursor durability being undocumented by Shopify
  (open question 10) and REST `page_info` cursors being explicitly documented
  as temporary (SH-16).
- **Job logs / user-visible audit trail.** **[Accepted, implemented]**
  `shopify.connector.job.log`'s append-only, single-sanctioned-write-path
  (`_system_append()`) substrate already exists (R2) and is the path any
  future job handler must log through — no parallel logging mechanism.
- **Redaction and technical-detail boundaries.** **[Accepted, implemented]**
  `redact()` at the single sanctioned write path (R2); DEC-009's user-facing
  log requirements (readable reason primary, technical detail secondary/
  expandable) — corroborated by OWASP's never-log list (E9/GEN-41).
- **Store-state / domain-enabled gating at enqueue and execution time.**
  **[Accepted, implemented for store-state; candidate for domain-enablement]**
  `create()`/`write()` already gate the five business `job_source` values on
  `store.state == 'connected'` at both enqueue time and the moment of the
  `state → 'running'` transition, using the *effective* post-write values,
  not a stale read (R1; a directly-tested, two-checkpoint defense-in-depth
  pattern). Blueprint §I.3 proposes extending this same two-checkpoint shape
  to per-domain enablement flags — an **accepted direction**, with the
  execution-time re-check scoped to **fail-safe gating only** (it may stop/
  hold/cancel/block, never alter an enqueue-time decision such as a
  notification flag or source-of-truth choice).
- **Lifecycle behavior on disconnect/reconnect/credential mutation.**
  **[Accepted, implemented, with an open risk]** `action_disconnect()`
  already cancels every non-terminal business job on disconnect, preserving
  history (R3); credential mutation already invalidates derived `store.state`
  (R5; the DEC-024 §4 lesson). **[Risk, unresolved]** Whether a business job
  already `running` inside an in-flight `ir.cron` batch at the exact instant
  of disconnect is fully interrupted is **not proven by any source**
  (SRR-03; open question 17/30) — requires live Odoo.sh proof before any
  design relies on the race being closed.

---

## D. Job trigger model

**[Accepted — DEC-005; DEC-019]** Five business trigger sources already exist
in the accepted schema and must all create or route to the **same** core job
mechanism (`shopify.connector.job`), sharing one state machine, one error-class
registry, and one dashboard/log surface:

| Trigger | Nature | Evidence |
| --- | --- | --- |
| **Manual sync** | Operator-initiated, on-demand ("sync now" / "reconcile now") | DEC-005; blueprint §G.3 |
| **Scheduled sync** | `ir.cron`-driven periodic run | DEC-005 |
| **Webhook enqueue** | HMAC-verified, `X-Shopify-Webhook-Id`-deduped, fast-ack, enqueue-only | DEC-005; blueprint §A.5 seam 7; MBQ-65 |
| **Reconciliation** | Mandatory, always-on `updated_at`-filtered correctness backstop — never optional, since webhook delivery is not guaranteed | DEC-005; S13/SH-7 |
| **Odoo event** | A job enqueued because an Odoo-side business event occurred (not a webhook, not operator-initiated, not a timer, not reconciliation, not a preview run) — carries a required `trigger_origin` sub-classification (`inventory_stock_change`, `fulfillment_picking_validation`) | DEC-019 (MBQ-62) |

**Trigger source is explicitly distinct from job type / domain handler.**
**[Accepted — R1; evidence map claim 3]** Store-state gating keys on
`job_source` (the fixed vocabulary above), **not** on `job_type` (which
domain modules extend via `selection_add`) — so a future domain job type is
gated automatically with no per-domain gating code needed. A single trigger
(e.g. `manual_sync`) can dispatch to any domain's handler; a single domain
handler (e.g. product import) can be invoked by any applicable trigger.

**Two additional job sources exist and are structurally distinct from the
five above:** `setup_readiness_check` and `export_preview_dry_run` are
read-only/preview-only, exempt from store-state gating by design (gating them
on `connected` would be circular), and are **not business sync runs**
(blueprint §D.2/§E.6). They are noted here for completeness, not conflated
with the trigger model above.

---

## E. Retry and failure policy

**[Accepted — DEC-009]** Bounded retries only — **no infinite retries** under
any circumstance. Every job failure is assigned an error class (the fixed
16-class registry) at the point of failure:

- **Auto-retry with backoff:** Shopify throttling/rate-limit; concurrency/race
  conflict; Shopify temporary/server/network failures on **reads** or on
  **`@idempotent` writes** (same persisted key, within Shopify's 24-hour
  window).
- **Ambiguous-outcome rule (no blind retry):** a temporary/network failure on
  a **non-`@idempotent` write** with an unknown outcome is never auto-retried
  — a safe verification read precedes any re-attempt where one exists,
  otherwise the job routes to `blocked_manual_review`.
- **Manual fix then retry:** permission/scope/auth; userErrors/validation;
  Odoo validation/configuration; mapping missing; data shape mismatch.
- **Operator confirmation required (`blocked_manual_review`):** ambiguous
  match; binding conflict; duplicate risk; destructive-write guard blocked;
  inventory location missing; fulfillment notification confirmation missing.
- **Conservative, never silent:** financial total mismatch.
- **Single safety-net auto-retry, then human** `[Implementation-planning
  default]`: unknown/system error.

**Rate-limit specifics this policy must honor:**

- **[Fact]** Shopify REST returns HTTP **429** with a `Retry-After` header on
  rate-limit exceedance, against a leaky-bucket capacity model reported via
  `X-Shopify-Shop-Api-Call-Limit` (SH-1).
- **[Fact]** A throttled Shopify **GraphQL** call can return **HTTP 200**
  with a `THROTTLED` error code in the response **body**, not a 4xx status
  (SH-4; independently surfaced by PR #126). **[Recommendation]** The
  response-parsing layer must inspect the GraphQL response body for a
  `THROTTLED` code on every call — a client modeled only on REST's
  status-code branching would silently miscount a throttled call as
  successful (SRR-08).
- **[Fact]** GraphQL responses carry `extensions.cost` with
  `throttleStatus.currentlyAvailable`/`restoreRate` (SH-2). **[Open
  question]** No documented `Retry-After`-equivalent exists for GraphQL
  `THROTTLED` responses specifically — the fallback is deriving a wait time
  from `throttleStatus` (open question 40).
- **[Recommendation, candidate policy]** Jittered exponential backoff is the
  candidate shape, following MBQ-16's accepted implementation-planning
  defaults (12 attempts / 30s exponential base ×2 / capped 30 minutes / ±20%
  jitter / 24-hour window) — **explicitly not final, production-tuned
  constants**, per DEC-009's own acceptance note; this gate does not
  hard-code them as binding.

**Failure visibility:** **[Accepted]** Permanent failure must be visible,
queryable, and recoverable through manual review — `failed_final` and
`blocked_manual_review` states, surfaced through the core dashboard/
error-center. **[Risk, evidence-backed]** `ir.cron`'s own coarse
5-failures-over-≥7-days deactivation triggers only a no-op logger call by
default (`_notify_admin`, O7) — failed jobs must **never** be allowed to
disappear into raw `ir.cron` logs; this repo's own job/log substrate, not
`ir.cron`'s admin-notify step, is the real operator-visible failure surface
(SRR-05).

---

## F. Idempotency and duplicate prevention

**[Recommendation]** A layered architecture, with core-owned and
domain-owned layers kept explicitly distinct:

| Layer | Owner | Status | Evidence |
| --- | --- | --- | --- |
| Job idempotency key (`idempotency_key`) | **Core** | Accepted, implemented | R1; `UNIQUE(store_id, idempotency_key)` |
| Operation-scope serialization guard (`operation_scope_key`) | **Core** | Accepted, implemented (creation-time only — clears on terminal/superseded state) | R1; `UNIQUE(store_id, operation_scope_key)` |
| Webhook delivery ID dedup (`X-Shopify-Webhook-Id`) | **Core** | Accepted | DEC-005; S14/SH-5 |
| Shopify `@idempotent` mutation handling | **Domain** (per-mutation, where applicable) | Accepted concept; exact mutation count disputed | S15/S16 (16 named, self-dated 2 Feb 2026) vs. DEC-009/AR-006 brief ("17 mutations") — **unresolved discrepancy**, does not affect the core-engine-level claim (evidence map claim 22) |
| Domain binding uniqueness / first-sync match rules | **Domain** | Accepted at policy level; exact thresholds open | DEC-006 `(store, Shopify GID)` / `(store, Odoo model, Odoo record)`; match-key priority existing-binding → SKU/reference → barcode → email → manual (RA-006); product first-sync dedup thresholds remain domain design (MBQ-59) |
| Duplicate-running protection at job **creation** | **Core** | Accepted, implemented | `operation_scope_key` unique constraint (R1) |
| Duplicate-running protection at job **execution** (concurrent claiming) | **Core** (candidate) | **Undesigned** | Candidate patterns: `SKIP LOCKED` row claiming (O7/OD-1 precedent), `lock_for_update()`/`try_lock_for_update()` (O9/OD-3), or PostgreSQL advisory locks (a newly-surfaced alternative with its own hazards — session-scoped advisory locks are not released by a rollback, and a `LIMIT`-bounded query can lock rows before `LIMIT` applies; GEN-30/GEN-31, SRR-09) |
| Checkpoint/resume (must not skip or double-process) | **Undecided** | No model exists today | `sync-engine-odoo-repo-source-notes.md` "Current gaps"; cursor durability unconfirmed for GraphQL (open question 10), REST `page_info` explicitly temporary (SH-16) |

**[Accepted — DEC-009 risk #5]** The internal job idempotency key prevents
duplicate connector-side **processing**; it never, by itself, makes a
non-`@idempotent` Shopify mutation safe to re-send after an ambiguous
outcome. The ambiguous-outcome rule (§E) closes that gap — a verification
read or `blocked_manual_review`, never a blind retry.

---

## G. Odoo execution substrate

- **[Accepted — DEC-005]** `ir.cron` is the official Odoo background
  primitive for Phase 1, unless later revisited. **[Fact]** It is the
  **only** documented background/deferred-execution primitive in Odoo 19
  core, poll-based, bounded by `--max-cron-threads` (default 2); on Odoo.sh
  it runs "best effort" — never guaranteed more often than every ~5 minutes
  in production, and disabled entirely on staging/development branches
  (O7/OD-1/OD-2/OD-8).
- **[Accepted — RA-004 binding]** OCA `queue_job` remains **reference-only**,
  not adopted by this architecture gate. This gate does not revisit RA-004 —
  its documented revisit condition (Odoo.sh officially demonstrating
  `server_wide_modules`/turnkey Jobrunner support, or MVP-scale throughput
  proving the internal cron-queue insufficient) is not met by anything in
  the Task 006A evidence base.
- **[Fact, evidence, not yet runtime-proven]** `ir.cron`'s own job-claiming
  query uses `FOR NO KEY UPDATE SKIP LOCKED` (O7/OD-1), and Odoo 19 ships
  official row-locking primitives (`lock_for_update()`/`try_lock_for_update()`,
  O9/OD-3) whose only official documented use case is exactly the
  cron-batch-processing pattern a future dispatcher would need
  (`sync-engine-odoo-repo-source-notes.md` §2/§Concurrency). **[Open
  question, three-shard-corroborated]** Whether this holds under actual
  concurrent multi-worker execution — and, separately, whether it holds
  with **no additional cross-server coordination** when multiple Odoo
  application servers share one PostgreSQL database — is **not proven by
  source-reading alone** in this package, PR #124, or PR #126 (open
  questions 17, 18, 30, 41, 43; SRR-03, SRR-04, SRR-09). **Live Odoo.sh
  (and, for the multi-server variant, multi-server) runtime proof is
  required** before any implementation relies on these concurrency
  assumptions.
- **[Fact — official Odoo coding guidelines, O8; independently corroborated
  by PR #124]** Savepoints are a **performance constraint, not a hard cap**:
  PostgreSQL performance degrades after more than 64 savepoints in a single
  transaction (worse with replicas) — a batch-sizing input, not an enforced
  ceiling in code (SRR-01). Core `create()`/`write()` do not wrap themselves
  in a savepoint automatically; savepoints are used selectively.
- **[Inference, requires runtime proof]** Whether Odoo's automatic RPC-layer
  serialization retry (`retrying()`, bounded at 5 tries with randomized
  exponential backoff — O5/O6/OD-5) extends to protect a cron job's own
  domain-record-processing code is a **source-backed inference, not a
  proven fact** — `ir.cron._callback()` shows no equivalent retry wrapper in
  the code reviewed (O7), and this exact open-question framing is now
  **three-shard-corroborated** (this package, PR #124, PR #126; evidence map
  claim 20; SRR-04). This must remain labeled as an inference requiring
  runtime proof, not asserted as settled.

---

## H. Shopify API implications

- **[Accepted — DEC-004; RA-002 (REST-heavy strategy rejected)]** The
  GraphQL Admin API is the preferred direction where applicable.
- **[Fact]** GraphQL cost/rate limits must influence batching: a single
  query cannot exceed 1,000 cost points regardless of plan; each response
  carries `extensions.cost` with `throttleStatus`
  (`maximumAvailable`/`currentlyAvailable`/`restoreRate`) (SH-2). Per-plan
  point rates are subject to drift — the 2023 changelog figure for the
  Advanced plan is superseded by the current API-limits page (SH-8 vs. SH-2;
  re-verify at implementation time, not hard-coded here).
- **[Fact]** REST and GraphQL throttling differ structurally: REST uses a
  leaky-bucket model with 429 + `Retry-After` (SH-1); GraphQL uses cost-point
  throttling and can return **HTTP 200 with a `THROTTLED` body code** rather
  than a 4xx status (SH-4) — see §E for the resulting response-parsing
  requirement.
- **[Fact]** Cursor pagination (`endCursor`/`pageInfo`, forward/backward
  paging, 250-item max page — S1/S2/SH-9/SH-10) requires checkpoint/resume
  thinking, but Shopify does not document cursor durability/reuse across a
  paused-and-resumed sync for GraphQL (open question 10); the REST
  equivalent (`page_info`) **is** explicitly documented as temporary and
  "not meant to be saved" (SH-16) — suggestive context for GraphQL, not
  proof either way.
- **[Fact]** Bulk operations may be useful for large imports but are **not
  automatically MVP** and are **not resumable at the API level** — recovery
  is whole-operation resubmission only, with no documented partial-resume
  mechanism (S7/S8/SH-14); concurrency limits are version-gated (1
  concurrent operation per shop pre-2026-01, up to 5 from 2026-01 onward).
  This trade-off against cursor pagination's finer-grained (but also
  unconfirmed-durability) checkpoint story is a concrete consideration for a
  future product-import domain decision, not resolved here (SRR-07; evidence
  map claim 14).
- **[Fact]** Webhook delivery is **not guaranteed** — out-of-order delivery
  is possible, and Shopify's own guidance is to use reconciliation jobs to
  periodically fetch data (S13/SH-7). This directly reaffirms why
  reconciliation is a mandatory, always-on layer (§B, §D), consistent with
  the already-accepted product-webhook posture (MBQ-65: enqueue-only,
  mandatory follow-up authoritative read) and the inventory-webhook posture
  (MBQ-63: not implemented in Phase 1 at all — drift-detection candidate
  only, with layered scheduled/manual/`odoo_event`/reconciliation as the
  only Phase 1 inventory-sync paths).

---

## I. Domain boundaries

**Architecture-level only — no final field mappings.** This table restates
already-accepted module-boundary decisions (DEC-008, DEC-013 §C.8, DEC-010,
DEC-011, DEC-014) at the responsibility level; it does not add new domain
scope.

| Layer | Owns (architecture-level) | Does **not** own |
| --- | --- | --- |
| **Core engine** (`shopify_connector_core`) | Job/queue/log/error abstraction; webhook receiver (HMAC + dedup + enqueue); `ir.cron` drain loop; retry scheduling; error-class registry (16 fixed classes); idempotency key + serialization-guard mechanics; dashboard / sync-center / error-center; setup/readiness wizard; store/credential/settings substrate; the Shopify Location **reference/cache only** (never Odoo-location IDs or mapping decisions); connector-wide role/permission substrate; the abstract binding contract (shape only) | Any domain business logic; domain field mapping; concrete domain binding tables; Odoo↔Shopify location mapping; any domain-specific Shopify API call semantics |
| **Product** | Product/variant import/export/update within DEC-007 scope; product-template and product-variant binding models (on the core abstract contract); first-sync product dedup **policy** (exact match-confidence thresholds remain domain design, MBQ-59); product webhook handling (enqueue-only + mandatory follow-up read, MBQ-65) | A separate queue/retry/log engine; customer, order, inventory, or fulfillment logic |
| **Customer** | Customer matching/binding (email-only automatic match key beyond existing binding, MBQ-31; phone/name advisory/manual-only); customer import | A separate queue/retry/log engine; product/order/inventory/fulfillment logic |
| **Sale / Order** | Order import; order binding; the whole-order-hold rule for an unmatched product line; the mandatory total-check guard; the Phase 1 same-currency-only automatic-import posture (MBQ-64) | A separate queue/retry/log engine; product/customer resolution logic (reused via the product module, not duplicated) |
| **Inventory** | Inventory-level binding `(store, inventory_item_id, location_id)`; **exclusive** ownership of Odoo↔Shopify location mapping; ongoing Odoo-as-source-of-truth write-back; the first-push guard (no coarser than per store+location-pair+binding, MBQ-33) | Fulfillment logic; the core Shopify Location reference itself; a separate queue/retry/log engine |
| **Fulfillment** | FulfillmentOrder/Fulfillment binding; validated `stock.picking` as the trigger; FulfillmentOrder-based mutations only (never the legacy API, RA-022); matched order/FulfillmentOrder/line/quantity (RA-023); the notification-default-off guard | Any dependency on the inventory module (must never read inventory's location-mapping table — DEC-008/DEC-010/DEC-011); a separate queue/retry/log engine |
| **Future accounting / refund / payout** | Not yet scoped by any accepted decision. Full accounting/payment reconciliation, refund sync, and payout reconciliation are explicitly excluded from Phase 1 (RA-010; DEC-003 Domain 9 rule: "preserves financial evidence and order actionability; does not automate accounting") | Any Phase 1 sync obligation of any kind |

**[Recommendation]** The core-vs-domain split above is consistent with the
DEC-008 dependency DAG (`core` → `product`; `sale`/`inventory` as siblings on
`core`+`product`; `fulfillment` on `core`+`sale`, never on `inventory`) and
with RA-011/RA-012 (no giant module, no per-feature micro-module
explosion).

---

## J. MVP implication

**[Recommendation]** If ChatGPT accepts this gate, it would enable — but does
**not** itself authorize — a later, separately-scoped session to draft:

- **Task 006C** — sync-engine implementation-scope drafting.
- A **core sync-engine skeleton** implementation (job-creation API, drain
  loop, dispatcher, retry scheduler) written to the `CLAUDE.md` §9
  implementation-task template.
- **Domain handler specs** for how product/customer/order/inventory/
  fulfillment modules register into the core (per §I, §B seam 7).
- **Product first-sync dedup design** (the exact match-confidence thresholds
  MBQ-59 defers).

**No implementation starts until ChatGPT explicitly accepts this gate AND
separately opens an implementation scope** (`CLAUDE.md` §5, §9;
`../05-qa/quality-feedback-loop.md` §10). Accepting this document is not
itself that act.

---

## K. Open questions and blocked items

**Carried forward unchanged from Task 006A — none is resolved by this
gate:**

- **VAL-B2** remains **deferred / not passed** — no live Shopify Admin API
  connection has been made or attempted by any task to date
  (`DEC-021-val-b2-deferral-for-task-004.md`).
- **MBQ-05** remains **Partially routed / Open** — the scalable,
  many-unrelated-customer token-acquisition/distribution architecture is
  undecided (`master-blueprint-open-questions.md` MBQ-05; `DEC-023`).
  DEC-023 accepted only a limited routing (a one-store/private/
  evidence-gathering path); the scalable multi-customer architecture (branch
  B) remains a separate, not-yet-scoped research/decision task.
- **TD-002** remains **Open** — the `REQUIRED_MVP_SCOPES` `read_fulfillments`
  scope-correctness concern, routed to the future fulfillment domain task
  once the fulfillment API model is decided (`technical-debt-register.md`).
- **Fulfillment scope/API model cannot be finalized yet** — the legacy
  `Fulfillment` vs. `FulfillmentOrder`-based choice (DEC-011/MBQ-42/MBQ-60)
  and TD-002 both remain undecided; this gate's job-trigger and retry
  policies (§D, §E) treat this as an explicit unknown, not a silent
  assumption.
- **Product first-sync deduplication** still requires domain design — MBQ-59's
  exact eligibility-check/match-confidence thresholds are deferred to a
  future product-domain task.
- **Token acquisition for many unrelated customers** remains unresolved
  (MBQ-05 branch B, `DEC-023` §3.2) — a sync engine that assumed any
  particular credential-acquisition shape beyond the single already-accepted
  `token_variant='offline_custom_app'` seam would be building on an
  unresolved foundation; this gate does not.
- **The 16-vs-17 `@idempotent` mutation-count discrepancy** remains open
  (S16: 16 named, self-dated 2 Feb 2026; DEC-009/AR-006 brief: 17) — does not
  affect this gate's core-engine-level idempotency claims (§F), but must be
  re-verified before any domain module hard-codes a specific mutation list.
- **The OCA `queue_job` worker-count wording discrepancy** (`--workers > 0`
  per the pre-006A baseline vs. `--workers > 1` per PR #126) remains open but
  **non-blocking** — immaterial to RA-004 either way (`queue_job` remains
  reference-only).
- **Multi-server / Odoo.sh runtime concurrency proof remains required**
  before implementation relies on any concurrency assumption named in §C/§G
  — specifically: the disconnect/in-flight-job race (SRR-03), whether
  `ir.cron`'s row-lock-only job acquisition holds under real concurrent
  worker execution (open questions 17/18/30) and under a multi-server/
  load-balanced deployment sharing one PostgreSQL database (open question
  41/43; SRR-09).
- **Lite/Full packaging** is product strategy and enablement design, not
  fully decided here — no such packaging-tier concept exists anywhere in the
  reviewed documentation corpus, though the underlying domain-enablement
  *mechanism* (per-store flags, block-new-enqueue-when-disabled,
  never-delete-history) is already accepted and partially implemented
  (evidence map claim 18; open questions 6, 21, 27).

**New architecture-level open questions this gate itself surfaces (none
resolved here — carried forward for a future implementation-scope session):**

- Which job-*claiming* concurrency mechanism the drain loop should use
  (`SKIP LOCKED`-style row claiming, `lock_for_update()`, PostgreSQL advisory
  locks, or a combination) — §C, §F.
- Whether checkpoint/resume state (for long-running paginated or bulk-import
  jobs) is core-owned or domain-owned — §C, §F.
- Whether the readiness-check `_get_checks()` seam pattern can be literally
  extended to job-type/handler dispatch, or needs a materially different
  shape — §C.

---

## L. Proposed decision record

See [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md).

**Status: Proposed / Pending ChatGPT review.** DEC-025 summarizes this gate,
lists the accepted research inputs it draws on, lists its proposed
architecture decisions, lists its explicit non-decisions, lists open
questions, and lists risks requiring runtime validation. **No decision in
DEC-025 is Accepted; nothing here authorizes implementation.**

---

## M. Review checklist

See [`../05-qa/task-006b-architecture-gate-review-checklist.md`](../05-qa/task-006b-architecture-gate-review-checklist.md)
for the QA checklist ChatGPT can use to accept, revise, or reject this gate.

---

## Branch note

This session's harness-designated branch is
`claude/task-006b-sync-engine-gate-865mw5` (assigned by the session
environment, already based on `origin/Shopify-connector` HEAD
`3207791412ebedbc83eceaf70592df8c8df0d97a` — the PR #127 merge commit — at
session start). The task prompt's suggested branch name,
`claude/task-006b-sync-engine-architecture-gate`, was not used, per the
governance instruction to develop on the harness-assigned branch and never
push to a different branch without explicit permission. See the session's
final report for detail.

## No implementation authorized

**This document does not authorize implementation of any kind.** No addon
file, Python, XML, CSV, manifest, security, migration, CI/workflow,
controller, view, wizard, OAuth, or domain-sync code was created or modified
by this session. The no-code gate (`CLAUDE.md` §4–§5) remains in force until
ChatGPT accepts DEC-025 **and** separately opens an implementation gate per
`../05-qa/quality-feedback-loop.md` §10 and `CLAUDE.md` §9.
