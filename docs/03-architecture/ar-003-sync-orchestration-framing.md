# AR-003 — Sync Orchestration & Queue Strategy (Decision Framing)

> **RB-14 Architecture Preparation — Part 1.** This document **frames** the AR-003
> decision; it **does not decide it.** No choice is made between `ir.cron`-only, an
> internal queue model, OCA `queue_job`, or an external worker, and no hosting
> strategy is finalized. AR-003 stays **[Not decided] / Evidence pending** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
>
> **Classification:** `[Official fact]` · `[Official limitation]` ·
> `[Competitor demonstrated]` · `[Competitor claim]` · `[Inference]` ·
> `[Recommendation]` · `[Open question]` · `[Decision — existing]` · `[Not decided]`.

## Decision question

**How does the connector move sync work reliably, out-of-band, and recoverably —
and on what background-execution substrate?** Concretely:

1. **Orchestration model:** how webhooks, scheduled sync, manual sync, and
   **reconciliation** combine so no single mechanism is the sole source of truth.
2. **Queue/execution substrate:** `ir.cron`-only, `ir.cron` + an internal queue
   model, OCA `queue_job`, or an external worker — and how that survives each Odoo
   hosting tier (Odoo Online / Odoo.sh / on-prem).
3. **Failure isolation & recovery:** per-record isolation, safe manual retry,
   reconciliation cadence, and fast webhook acknowledgement.

## Why it matters

- **[Official fact]** Shopify **webhook delivery is not guaranteed**, so a correct
  sync **requires** a reconciliation path — orchestration is a **correctness**
  requirement, not a performance nicety.
- **[Official fact]** Odoo 19 official docs document **`ir.cron`** as the scheduled/
  background execution mechanism (poll-based, minute-precision, `--max-cron-threads`
  default 2). **[Inference from official fact]** The official docs reviewed **do not
  document a general-purpose async job queue in Odoo core** (absence of documentation,
  not a positive statement); **[Open question]** confirm against the Odoo 19 source if
  this becomes load-bearing. **[Community / not official]** OCA `queue_job` is a
  community dependency, **not Odoo core**. The substrate choice is therefore a real
  architecture decision with a **community-dependency** dimension.
- **[Inference]** AR-003 constrains AR-006 (retry/reconciliation cadence), AR-007
  (inventory apply), and AR-008 (fulfilment) — see
  [`architecture-decision-framing.md`](./architecture-decision-framing.md) §6.

## MVP scope inputs from DEC-003 (`[Decision — existing]`)

- **Layered sync (MVP-critical):** "webhooks + scheduled sync + manual sync +
  **reconciliation** (never one mechanism alone)."
- **Fast webhook acknowledgement**; **HMAC**; **webhook-ID dedup**.
- **Per-record failure isolation**; **safe manual retry**; **retry classification
  concept**; **resumable jobs**; **rate-limit / cost awareness**.
- **Quick actions that enqueue work** — "never run heavy sync inline."
- **Honest freshness** — truthful "last synced / last reconciled"; no "real-time"
  overstatement.
- **Single-store MVP**, but architecture-safe; **Odoo edition/hosting** left open
  (DEC-003 open architecture question #2 — Odoo-Online feasibility).

## Shopify official constraints (`[Official fact]` / `[Official limitation]`)

Refreshed 2026-07-01 (see [`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md)).

- **[Official fact]** "Delivery is not guaranteed" — apps "shouldn't rely on receiving
  webhook data" and should "use reconciliation jobs to periodically fetch data" (e.g.
  `updated_at` filters). Duplicate deliveries are possible → handlers must be
  **idempotent**. (shopify.dev/docs/apps/build/webhooks/best-practices)
- **[Official fact]** Shopify expects a **200** within a **1-second connection /
  5-second total** window; on failure it **retries 8 times over ~4 hours**; after **8
  consecutive failures** an **Admin-API-created subscription is automatically
  deleted**. (…/webhooks/subscribe/https)
- **[Official fact]** Verify **HMAC-SHA256 of the raw body** (`X-Shopify-Hmac-SHA256`)
  **before processing**; **dedupe on `X-Shopify-Webhook-Id`**. (…/webhooks/verify-deliveries)
- **[Official fact]** Rate limits: GraphQL **calculated cost** (points; ≤ 1,000 per
  query; live `throttleStatus` in `extensions.cost`); REST **leaky-bucket** with **429
  + `Retry-After`**. Large jobs can use **Bulk Operations** (async JSONL; concurrency
  up to 5 each since 2026-01; size/time limits). (…/usage/limits;
  …/admin-rest/usage/rate-limits; …/usage/bulk-operations/queries)
- **[Official fact]** `inventorySetQuantities` / `inventoryAdjustQuantities` /
  `refundCreate` require **`@idempotent`** as of 2026-04 — the retry/idempotency hooks
  AR-003's execution model must carry.

## Odoo official constraints (`[Official fact]` / `[Official limitation]` / `[Open question]`)

Citations in [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md).

- **[Official fact]** Odoo 19 official docs document **`ir.cron`** for scheduled/
  background execution — poll-based, minute-precision — including **batching**,
  `_commit_progress`, `_trigger` (dispatches "soon"), the "**not reschedule
  themselves**" rule, cron failure behavior, and cron-worker configuration.
- **[Inference from official fact]** The official docs reviewed **do not document a
  general-purpose async job queue in Odoo core** (absence of documentation, not a
  positive statement).
- **[Open question]** Confirm against the Odoo 19 source/codebase if this becomes
  load-bearing for the substrate decision.
- **[Community / not official]** OCA `queue_job` remains a **community dependency, not
  Odoo core**.
- **[Official limitation]** Cron **failure model is coarse**: **3 consecutive
  errors/timeouts → skip the run**; **5 consecutive failures over ≥ 7 days →
  deactivated + DB admin notified.** So the connector must implement **its own
  per-record retry/backoff and error isolation** (savepoints), not rely on cron-level
  retries.
- **[Official limitation]** Cron throughput is bounded by **`--max-cron-threads`
  (default 2)**; in WSGI deployments a **separate cron process** (`--no-http`) is
  required.
- **[Official fact / Community]** OCA **`queue_job`** provides a true async queue
  (`with_delay()`, Jobrunner, retries, dependency graphs) but is **community, not
  official Odoo**, and requires its own **Jobrunner + `server_wide_modules` + ≥2
  workers** deployment.
- **[Official fact]** **Odoo.sh staging/development crons are disabled** (neutralized
  duplicates) — sync won't auto-run in non-prod; test plans must trigger manually.
- **[Open question → resolved in RB-14 Part 2 for custom-module feasibility]** **Odoo Online
  custom-module feasibility is resolved:** `[Official limitation]` "Odoo Online is incompatible
  with custom modules," so the custom connector module **does not target Odoo Online** (it
  targets **Odoo.sh / on-premise**). What **remains open** is whether **Odoo.sh / on-prem**
  permit `server_wide_modules`, an external Jobrunner, and the outbound HTTPS a given design
  needs — see the RB-14 Part 2 notes and the Required-evidence update below.
- **[Official fact]** Long syncs **must not** run in one HTTP request (worker
  time/memory limits recycle/kill workers) → chunked, out-of-band processing.

## Competitor evidence inputs (`[Competitor demonstrated]` / `[Competitor claim]`)

From Sprint C/C2 (evidence, not facts) — a data-point spread across substrates:

- **[Competitor demonstrated]** **VentorTech** runs on the **OCA `queue_job`** async
  queue (requires `odoo.conf` edits + `server_wide_modules` + ≥2 workers; **not**
  Odoo-Online-installable) with **automatic retry of safe ops** and failed-job
  notifications — the only survey connector on a real async queue.
- **[Competitor demonstrated]** **Emipro** uses **webhooks + per-process scheduler +
  manual**, with **batch Data Queues** (125 products / 50 orders), isolated
  Failed/Cancelled lines, and a **manual import path to recover missed webhooks** — but
  **no automatic retry**.
- **[Competitor demonstrated]** **TeqStars** uses **webhooks (background-thread
  fast-ack) + scheduled Automatic Jobs + manual + per-operation queues**
  (Product/Customer/Order/Return; **Queue Batch Limit 100**; **cron-processed —
  framework not named**), with a collection job that "retries in the next run" and
  incremental Last-Processed cursors. **[Competitor claim]** no explicit
  automatic-retry/backoff taxonomy, no first-class reconciliation surface (verified ⬜).
- **[Competitor demonstrated]** **Softhealer** ships a **Queue Dashboard Framework**
  (Contact/Product/Order/Checkout/Recommendation queues; draft/completed/failed; daily
  activity chart; "Needs Shopify Re-Export" flag) over a queue/cron + webhook model.
- **[Competitor demonstrated]** **Webkul** uses a **Feeds staging** area (cron import,
  event export), **no webhooks**, and exposes raw `ir.cron` fields to users
  (anti-pattern A-UX-2).
- **[Competitor demonstrated]** **ecommerce_shopify** is **cron-only (10-min), no
  webhooks, email-only errors** — the reliability **floor** and an explicit
  anti-pattern (A-SYNC-1, A-LOG-1).
- **[Inference]** The market shows **two viable substrates** for a queue — a real
  async queue (VT: `queue_job`) **and** a **cron-processed per-op queue** (TQ) — so
  `queue_job` is **not** the only demonstrated path. No competitor demonstrates
  **named rate-limit/GraphQL-cost throttling** (whitespace).

## Candidate options (framing only — none selected)

> All options assume the DEC-003 **layered** model (webhooks + scheduled + manual +
> reconciliation). They differ in the **execution substrate**. None is selected.

### Option 1 — `ir.cron`-only (internal batched jobs)

- **Evidence for:** `[Official fact]` no core dependency; installable on every hosting
  tier (subject to Odoo-Online cron availability); simplest deployment.
- **Evidence against:** `[Official limitation]` poll-based, minute-precision,
  `--max-cron-threads` default 2, coarse auto-deactivation; `[Competitor demonstrated]`
  cron-only/webhook-less designs (EC) are the reliability floor.
- **Risks:** throughput/latency ceilings; treating `ir.cron` as a queue (A-SYNC-3);
  self-built retry/backoff still required.
- **UX implications:** must **not** expose raw `ir.cron` fields (A-UX-2); present a
  friendly "every N minutes" + honest freshness.
- **Reliability implications:** acceptable only **with** webhooks + reconciliation +
  self-managed per-record retry; weakest headroom at scale.
- **Hosting implications:** best cross-tier compatibility (if Odoo Online runs crons).
- **Open questions:** does `--max-cron-threads=2` throttle MVP-scale catalogs/orders?

### Option 2 — Webhook + `ir.cron` + an internal queue model (custom job records)

- **Evidence for:** `[Competitor demonstrated]` TQ and EM prove a **cron-processed
  per-op queue** with batch limits, isolation, and cursors works and is Odoo-Online-
  friendlier (no Jobrunner); keeps DEC-003's per-record isolation + resumable jobs
  without a community dependency.
- **Evidence against:** `[Inference]` re-implements part of what `queue_job` gives
  (priorities, retry graphs) — more code to get right; still bounded by cron threads.
- **Risks:** building a robust queue is non-trivial (backoff, dedup, ordering);
  reinventing a solved problem.
- **UX implications:** enables a real **command center + queue dashboard** (SH/EM
  pattern) with failure counts and safe manual retry.
- **Reliability implications:** strong per-record isolation + reconciliation possible;
  retry taxonomy is AR-006.
- **Hosting implications:** likely the **most portable** across Odoo Online / Odoo.sh /
  on-prem (no Jobrunner), pending the Odoo-Online outbound-HTTPS/cron open question.
- **Open questions:** how much queue machinery to build vs adopt; ordering guarantees.

### Option 3 — Webhook + OCA `queue_job`

- **Evidence for:** `[Competitor demonstrated]` VT proves a real async queue with
  auto-retry, dependency graphs, and failed-job notifications; mature community
  module.
- **Evidence against:** `[Official fact / Community]` **not core** — needs Jobrunner +
  `server_wide_modules` + ≥2 workers; `[Competitor demonstrated]` VT is **not
  Odoo-Online-installable** and its `odoo.conf` install is the #1 friction point
  (A-MOD-3).
- **Risks:** install friction / abandonment; non-core dependency lifecycle; excludes
  Odoo-Online merchants unless made turnkey.
- **UX implications:** best background-job semantics, but the **setup wizard** must hide
  or automate the server-config burden.
- **Reliability implications:** strongest out-of-the-box retry/queue semantics.
- **Hosting implications:** Odoo.sh / on-prem only (per current evidence); **Odoo
  Online excluded** — a decision-relevant constraint.
- **Open questions:** can the dependency be made turnkey; is the Odoo-Online exclusion
  acceptable for MVP.

### Option 4 — Webhook + external worker (out-of-Odoo processor)

- **Evidence for:** `[Inference]` fully decouples heavy sync from Odoo workers;
  scales independently.
- **Evidence against:** `[Inference]` heaviest operational surface (a separate service
  to deploy/monitor/secure); no competitor demonstrates it; hardest to install.
- **Risks:** deployment/security complexity; state split across systems; likely
  incompatible with Odoo Online.
- **UX / reliability / hosting implications:** powerful but the least "install-and-go";
  contradicts the DEC-003 effortless-onboarding intent for MVP.
- **Open questions:** is this ever justified for single-store MVP scale? (Likely a
  later-phase scale option, not MVP.)

### Option 5 — Hybrid substrate by hosting tier

- **Evidence for:** `[Inference]` matches the reality that hosting tiers differ (Odoo
  Online constraints vs Odoo.sh/on-prem latitude) — e.g. internal cron-queue on
  constrained tiers, `queue_job` where available.
- **Evidence against:** `[Inference]` two code paths to build/test; more surface for
  drift; complexity.
- **Risks:** matrix of substrate × hosting to validate; harder support story.
- **UX / reliability implications:** consistent operator UX must sit over differing
  substrates (honest freshness regardless).
- **Hosting implications:** the point of the option — but multiplies test burden.
- **Open questions:** is per-tier divergence worth it for MVP, or should MVP target one
  tier and generalize later?

## UX implications (support only — no screens designed)

Grounded in [`../02-product/setup-ux-principles.md`](../02-product/setup-ux-principles.md),
[`../01-research/best-in-class-observations.md`](../01-research/best-in-class-observations.md),
and [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md):

- **No heavy sync inline; fast ack:** quick actions **enqueue**; the UX shows work as
  queued/processing/done, never blocking a request (DEC-003; A-SYNC-4).
- **Command center implications:** the substrate must feed a **unified command center**
  (connection health + queue status + activity timeline + reconciliation status) —
  combining SH's monitoring with VT's diagnostics (O-DASH-1).
- **Per-record failure isolation + manual retry:** the error center must show each
  failure's **record + reason + suggested fix + retry** (EM Log Book bar; O-LOG-1),
  with **safe manual retry** and **never email-only** (A-LOG-1).
- **Reconciliation UX:** because delivery isn't guaranteed, expose a **first-class
  "reconcile now / last reconciled / drift found"** surface (whitespace O-REL-1) — a
  differentiator, but the substrate must make scheduled + on-demand reconciliation
  cheap.
- **Idempotency hooks:** retries must be **safe by construction** (`@idempotent` +
  binding keys, AR-005/006) so a user (or auto-retry) re-running a job never
  double-writes.
- **Honest freshness:** honest "last synced / last reconciled" labels per data type —
  **no "real-time"** overstatement (A-UX-1).
- **Hide Odoo plumbing:** friendly scheduling; **never expose raw `ir.cron` fields**
  (A-UX-2).

## Required evidence before an AR-003 decision

> **RB-14 Part 2 update:** **Odoo Online custom-module feasibility is resolved for this
> connector** — `[Official limitation]` "Odoo Online is incompatible with custom modules," so
> the custom connector module **does not target Odoo Online** (it targets **Odoo.sh /
> on-premise**). The Part 1 "Odoo-Online feasibility" item is therefore **superseded** and is
> **no longer a live gate** for AR-003. The remaining hosting/substrate evidence is:

- **[Open question]** **Odoo.sh / on-prem `server_wide_modules` support** (needed for a
  Jobrunner-based option).
- **[Open question]** **Odoo.sh / on-prem external jobrunner support** (gates OCA `queue_job`,
  Option 3).
- **[Open question]** Whether OCA `queue_job` can be made **turnkey** (no hand-edited
  `odoo.conf`) if adopted.
- **[Open question]** MVP-scale **throughput** under `--max-cron-threads=2` for the
  DEC-003 object set — does an internal cron-queue suffice, or is `queue_job` needed?
- **[Open question]** **Reconciliation cadence/scope** (per-object vs global; how often)
  — jointly with AR-006.
- **[Open question]** **Ordering guarantees** needed (e.g. product-before-inventory) and
  how each substrate provides them.
- **[Open question]** Whether **Bulk Operations** (AR-002) should back large backfills
  within the orchestration model, if relevant.

## Recommended decision criteria (recommendation, not a decision)

- **[Recommendation]** Require the layered model (webhooks + scheduled + manual +
  **first-class reconciliation**) regardless of substrate — this is the correctness
  floor Tier-1 mandates and the market whitespace.
- **[Recommendation]** Decide the **substrate against the hosting target**: if
  Odoo-Online support is required for MVP, favour a substrate that does **not** need a
  Jobrunner; if Odoo.sh/on-prem only, `queue_job` becomes viable — but make any
  non-core dependency **turnkey** (avoid VT's install friction).
- **[Recommendation]** Require **per-record isolation + safe manual retry + idempotent
  writes** in every option (AR-006/AR-005 hooks), and a **command center + recovery-
  first error center** over whichever substrate is chosen.
- **[Recommendation]** Do **not** treat `ir.cron` as a queue without a queue model
  around it (A-SYNC-3), and do **not** expose cron internals to users.

## RB-14 Part 2 notes (2026-07-01) — narrowing, not deciding

> Added by RB-14 Part 2. **Part 1 framing above is preserved.** Evidence:
> [`rb14-part2-open-question-resolution.md`](./rb14-part2-open-question-resolution.md);
> narrowing: [`rb14-decision-candidate-brief.md`](./rb14-decision-candidate-brief.md). All
> narrowing is `[Recommendation]` / `[Decision candidate]`. **AR-003 stays [Not decided].**

- **RQ-003-1 (hosting — core resolved):** `[Official limitation]` **"Odoo Online is
  incompatible with custom modules"** → the connector's custom module **cannot run on Odoo
  Online**; the substrate is **Odoo.sh or on-premise**. This **removes** the Part 1 "must
  support Odoo Online" pressure. **Effect on options:** **Option 5 (per-tier hybrid) is
  weakened** (the Online-vs-rest tier split largely collapses); **Option 3 (`queue_job`) is no
  longer excluded by Odoo Online** — but `[Open question]` Odoo.sh/on-prem
  `server_wide_modules` + jobrunner support keeps it **feasibility-gated**.
- **RQ-003-2/3 (substrate — source facts):** `[Official source-code fact]` the reviewed source
  confirms `ir.cron` (`IrCron`/`IrCronTrigger`/`IrCronProgress`), the `_trigger`/
  `_commit_progress` signatures, and the failure constants (`CONSECUTIVE_TIMEOUT_FOR_FAILURE =
  3`; deactivate only when `failure_count ≥ 5` **and** `≥ 7 days`), and that **`with_delay` is
  absent** from the reviewed files; `[Inference]` a general async job queue was **not found**
  in the reviewed docs/source (`[Open question]` whole-repo absence; `[Community / not
  official]` OCA `queue_job`). Background execution on stock Odoo 19 relies on the
  source-verified `ir.cron`, and a true async queue **remains a community dependency unless
  further source evidence proves otherwise**. → the connector **must** own per-record
  retry/backoff + savepoint isolation regardless of substrate; **Option 1 (cron-only) is a
  floor only** (never `ir.cron`-as-a-queue, A-SYNC-3).
- **Decision-candidate summary (input):** carry **Option 2 (internal cron-queue)** and
  **Option 3 (`queue_job`, made turnkey)** as the two primary candidates; **Option 1** as the
  floor; **Options 4 (external worker) and 5 (per-tier hybrid) weakened**. All still **[Not
  decided]**.

> **No decision is made in this document.** AR-003 remains **[Not decided] / Evidence
> pending**. The options, criteria, and open questions above are **inputs** for a
> future ChatGPT-approved architecture-decision sprint (`CLAUDE.md` §4–§5; RB-14).
