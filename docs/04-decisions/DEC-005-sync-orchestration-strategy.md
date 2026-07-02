# DEC-005 — Sync Orchestration / Queue Strategy (AR-003)

> **Proposed decision record for ChatGPT review.** This is a **recommendation**, not an
> acceptance. It does **not** self-authorize implementation and does **not** change
> DEC-003. If accepted, it resolves **AR-003** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).

## Status

**Proposed for ChatGPT review.** Not accepted. Not implementation-authorizing.

## Date

2026-07-02.

## Scope

**AR-003 only** — Phase 1 **sync orchestration model** and **execution
substrate/hosting target**. Does **not** decide AR-002 (API/distribution — DEC-004),
AR-005 (binding/dedup — DEC-006), AR-006 (retry/error taxonomy — explicitly deferred,
see *Non-goals*), AR-007/AR-008, or AR-004 (module boundaries). Assumes DEC-004's
custom-app/GraphQL-first premise. Does not design job-table fields beyond what is
needed to state the direction.

## Decision summary

Phase 1 targets **Odoo.sh or on-premise** (Odoo Online is excluded — a custom module
cannot run there). Orchestration is **layered**: an **HMAC-verified, fast-acknowledging
webhook receiver** with **webhook-ID deduplication**, enqueuing work into an **internal
Odoo queue/job model**; an **`ir.cron`-driven processing loop** with **per-record
isolation and retry counters**; a **manual sync trigger**; and **scheduled
reconciliation** as a first-class, non-optional mechanism (webhook delivery is not
guaranteed). **OCA `queue_job` is not the Phase 1 default** — it remains a
**documented, optional, later/on-prem accelerator**, gated on confirming Odoo.sh
`server_wide_modules`/Jobrunner feasibility, which official docs do not yet state.

## Recommended option

**AR-003 Option 2 — webhook + `ir.cron` + an internal queue model (custom job
records)**, as the **Phase 1 default substrate**, combined with the DEC-003-mandated
layered model (per
[`ar-003-sync-orchestration-framing.md`](../03-architecture/ar-003-sync-orchestration-framing.md)
and the RB-14 Part 2 narrowing).

- **Webhook receiver:** verifies **HMAC-SHA256 of the raw body** before processing,
  acknowledges fast (Shopify expects a 200 within ~1s connection/5s total), and
  **dedupes on `X-Shopify-Webhook-Id`** before any enqueue.
- **Enqueue, not inline processing:** every webhook/quick action **enqueues** a job
  record; heavy sync work never runs inline in the HTTP request (Odoo worker
  time/memory limits would recycle/kill the process anyway).
- **`ir.cron`-driven processing:** an `ir.cron` job (or a small number of them) drains
  the internal queue in **batches**, using `_trigger`/`_commit_progress` for near-term
  dispatch and progress reporting, honoring `--max-cron-threads` (default 2).
- **Manual sync trigger** for on-demand runs (e.g. "sync now"), and **scheduled
  reconciliation** (periodic `updated_at`-filtered fetch) as the correctness backstop
  for missed/undelivered webhooks — never one mechanism alone.
- **Per-record isolation:** each queued unit processes independently (savepoints);
  one record's failure does not block others in the same batch.
- **Retry states and counters:** every job record carries a retry count and a
  **dead/final-failed state** after a bounded number of attempts, surfaced to a
  recovery-first error center (full taxonomy is **AR-006, not decided here**).
- **`ir.cron`'s own coarse deactivation (5 failures over ≥7 days) is not the retry
  mechanism** — the connector's job model owns retry/backoff itself; `ir.cron`
  deactivating is a rare fallback, not the design.
- **OCA `queue_job`:** kept as a **documented optional accelerator** for on-prem
  deployments where an operator can confirm and maintain a Jobrunner-as-worker-process
  setup — **not** the Phase 1 default, **not** required, **not** rejected outright.

## Rejected / deferred options

| Option | Disposition | Why |
| --- | --- | --- |
| **1 — `ir.cron`-only (no queue model)** | **Kept only as an implicit floor inside Option 2**, never as a standalone design | `ir.cron`-as-a-queue is a demonstrated market anti-pattern (webhook-less/cron-only designs are the reliability floor, not the target); Option 2 already includes `ir.cron` as the processing loop, so Option 1 alone is not separately viable |
| **3 — OCA `queue_job` as the Phase 1 DEFAULT substrate** | **Deferred as default; kept as an optional, later/on-prem accelerator** (proposed; see `rejected-approaches-log.md`) | Non-core dependency; **Odoo.sh `server_wide_modules`/Jobrunner support is not confirmed by official docs** (2026-07-02 refresh); competitor evidence (VentorTech) shows real install friction; DEC-003's effortless-onboarding intent argues against depending on an unconfirmed hosting capability as the *default* |
| **4 — External worker (out-of-Odoo processor)** | **Rejected for Phase 1** (proposed; see `rejected-approaches-log.md`) | Heaviest operational surface (a separate service to deploy/secure/monitor); no competitor demonstrates it; contradicts the DEC-003 install-and-go intent for a single-store MVP |
| **5 — Hybrid substrate by hosting tier** | **Weakened** (Odoo Online exclusion collapses the tier split; no RA row — not formally rejected) | With Odoo Online out of scope, Odoo.sh and on-prem are close enough in capability that maintaining two substrates has little payoff for Phase 1 |

## Evidence used

Dated **2026-07-01** (RB-14 Part 1/2) unless noted **2026-07-02** (this sprint's
targeted refresh,
[`ar002-ar003-ar005-evidence-refresh.md`](../03-architecture/ar002-ar003-ar005-evidence-refresh.md)).

- `[Official fact]` "Delivery is not guaranteed" for webhooks; apps should "use
  reconciliation jobs to periodically fetch data" —
  `shopify.dev/docs/apps/build/webhooks/best-practices`.
- `[Official fact]` verify HMAC-SHA256 of the raw body; dedupe on
  `X-Shopify-Webhook-Id` — `.../webhooks/verify-deliveries`.
- `[Official fact]` a 200 is expected within ~1s connection/5s total; 8 retries over
  ~4h; an Admin-API-created subscription auto-deletes after 8 consecutive failures —
  `.../webhooks/subscribe/https`.
- `[Official limitation]` "Odoo Online is incompatible with custom modules or modules
  from the Odoo Apps Store" — `odoo.com/documentation/19.0/administration/odoo_online.html`
  → the connector's custom module targets **Odoo.sh or on-premise**.
- `[Official source-code fact]` `ir.cron`'s own failure model:
  `CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3`, deactivation only when
  `failure_count ≥ 5` **and** `first_failure_date + 7 days < now`; `_trigger`,
  `method_direct_trigger`, `_commit_progress(processed=0, *, remaining=None,
  deactivate=False)` — `github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py`.
  `with_delay` (the `queue_job` dispatch API) is **absent** from the reviewed 19.0
  source files.
- `[Official fact]` `--max-cron-threads` default **2**; a WSGI deployment needs a
  separate `--no-http` cron process — `odoo.com/documentation/19.0/developer/reference/cli.html`.
- **(2026-07-02)** `[Official fact]` Odoo.sh runs scheduled actions on a **"best
  effort"** basis in **production** too — "cannot guarantee an exact running time,"
  "not... more often than every 5 min," execution-time-limited; guidance to batch,
  commit per batch, and be idempotent —
  `odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html`.
- **(2026-07-02)** `[Open question]` Odoo.sh `server_wide_modules`/external-Jobrunner
  support is **not addressed** in any fetched Odoo.sh page — absence of
  documentation, not a documented denial.
- **(2026-07-02)** `[Community evidence]` OCA `queue_job` (repo `OCA/queue`) has a
  19.0 PyPI release; its Jobrunner **now runs as an Odoo worker process** (not a
  separate external daemon) but still requires `server_wide_modules=...,queue_job`
  and `--workers > 0` — `github.com/OCA/queue/tree/19.0`;
  `raw.githubusercontent.com/OCA/queue/19.0/queue_job/README.rst`.
- `[Competitor demonstrated]` TeqStars and Emipro both run a **cron-processed
  per-operation queue** (batch limits, per-object isolation, incremental cursors)
  without OCA `queue_job` — evidence that Option 2 is a proven market shape, not just
  a theoretical fallback; VentorTech runs on OCA `queue_job` with real install
  friction (`odoo.conf` edits) — an input, not a fact.

## Risks

1. **Throughput ceiling** — `--max-cron-threads=2` (default) bounds batch-processing
   throughput; MVP-scale validation is not yet done (open question, carried forward).
2. **Building a robust internal queue is non-trivial** — backoff, dedup, and ordering
   guarantees (e.g. product-before-inventory) must be engineered correctly; this is
   real work, not "just use `ir.cron`."
3. **Odoo.sh's "best effort" cron behavior** (≥5-minute interval, execution-time
   limits, no exact-time guarantee) means the queue drain cadence is inherently
   approximate, even in production.
4. **Reconciliation is mandatory, not optional** — any implementation that treats
   webhooks as sufficient reintroduces the demonstrated market anti-pattern
   (webhook-only/cron-only drift).
5. **Deferring `queue_job` risks under-provisioning for scale** if Phase 1 throughput
   turns out to need it sooner than expected.

## Mitigations

1. Validate MVP-scale throughput under `--max-cron-threads=2` during implementation
   planning before committing to a fixed batch/interval design (open question, not
   resolved here).
2. Design the internal job model with **per-record isolation (savepoints)**, explicit
   **retry counters**, and a **dead/final-failed state** from the start — do not treat
   `ir.cron`'s own coarse deactivation as the safety net.
3. Build batches and commits to match Odoo.sh's own guidance (small batches, commit
   per batch, idempotent) regardless of hosting tier, so the design is portable to
   on-prem too.
4. Require **scheduled + on-demand reconciliation** as a first-class, always-on
   mechanism, not a fallback feature.
5. Keep OCA `queue_job` as a **documented, ready-to-adopt-later** path (not designed
   out) so a throughput or on-prem-operator need can adopt it without an architecture
   rewrite — see *Revisit triggers*.

## UX implications

- The command center shows work as **queued / processing / done**, never blocking a
  request; **never expose raw `ir.cron` fields** to the operator.
- **Honest freshness** — truthful "last synced / last reconciled" labels; no
  "real-time" overstatement, consistent with Odoo.sh's own "best effort" cron
  behavior.
- A **recovery-first error center**: every failure shows its record, reason, a
  suggested fix, and a **safe manual retry** — never email-only.
- A first-class **"reconcile now / last reconciled / drift found"** surface, since
  webhook delivery is not guaranteed.

## Security implications

- Job records must carry store scoping (ties to DEC-006's per-store binding model)
  enforced via **record rules**, not via `sudo()` — `[Official source-code fact]`
  `sudo()` bypasses record-rule isolation, so orchestration code must not route
  around store scoping that way.
- Credential access needed by a queued job (e.g. the AR-002/DEC-004 offline token)
  must be scoped the same way whether triggered by webhook, cron, or manual action.

## Data-safety implications

- **Idempotent processing** for every queued job — safe to re-run without
  double-writing (ties to DEC-006 binding + AR-006 idempotency keys, not fully
  decided here).
- **Per-record isolation** so one bad record cannot corrupt or block a batch.
- **Dead/final-failed state** prevents a job from retrying forever or silently
  vanishing — every failure ends in a visible, actionable state.

## Performance implications

- Batch processing sized to Odoo.sh's execution-time limits and `--max-cron-threads`
  concurrency; use `_commit_progress` to commit partial batches instead of
  all-or-nothing runs.
- Reconciliation cadence must balance freshness against Shopify's GraphQL cost model
  and REST leaky-bucket limits (rate-limit/cost awareness is DEC-003-mandatory;
  detailed cadence is AR-006, not decided here).

## What this unlocks

- Implementation planning (post ChatGPT phase-exit approval) for the internal job/
  queue data model's **direction** (webhook receiver, `ir.cron` drain loop, manual
  trigger, reconciliation job) — exact fields/tables remain for the domain-model
  sprint.
- AR-006 (retry/error taxonomy + reconciliation cadence) can now be framed against a
  **fixed substrate** instead of an open `ir.cron`-vs-`queue_job` fork.
- AR-007/AR-008 (inventory/fulfilment orchestration) can assume the same substrate.

## What remains blocked

- **Full AR-006 retry/error taxonomy** — not decided here (explicit non-goal).
- **Full job-table field design** — deferred to the domain-model sprint.
- **OCA `queue_job` adoption itself** — remains optional/deferred, not chosen, pending
  the revisit triggers below.
- **Module boundaries (AR-004)** and **binding data model (AR-005/DEC-006)** — separate
  decisions.
- **All implementation** — no code, no Odoo module, until ChatGPT opens the
  implementation gate.

## Revisit triggers

- Odoo.sh (or on-prem, for operators who want it) officially documents/demonstrates
  `server_wide_modules` + Jobrunner-as-worker-process support **and** a turnkey
  install path is achieved (no hand-edited `odoo.conf` friction) — would make OCA
  `queue_job` a stronger default candidate.
- MVP-scale throughput testing shows the internal cron-queue insufficient under
  `--max-cron-threads=2` at realistic single-store catalog/order volumes.
- A specific on-prem deployment with an existing, maintained Jobrunner operator
  justifies `queue_job` for that deployment (a per-deployment choice, not a Phase 1
  default change).

## No implementation authorized

**No implementation is authorized by this decision record until ChatGPT accepts it.**
This record does not create code, an Odoo module, or any file outside
`docs/03-architecture/**` and `docs/04-decisions/**`. The no-code gate
(`CLAUDE.md` §4–§5) remains in force.
