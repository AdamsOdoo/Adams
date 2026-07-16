# Performance SLO Benchmark Plan — PB-1..23 + Provisional New-Domain SLOs

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** This plan operationalizes every row of
> [`../03-architecture/performance-budgets.md`](../03-architecture/performance-budgets.md)
> (PB-1..23, provisional budgets — [Fact] that file is the budget authority
> and its recalibration rule governs any number change) into an executable
> benchmark plan, and proposes **new provisional SLO rows** for the Wave 2–5
> domains. Numbers policy: **no unlabeled numbers** — every figure below is
> either (a) an existing PB row [Fact — cited], (b) derived from Shopify's
> published throttle restore rates [Fact —
> [`../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md) §11],
> or (c) an explicit [Recommendation] with rationale, calibrated by
> PERF-1/Wave 6 before it can gate anything.

## 1. Shared test environment and datasets

- **Odoo.sh environment [Recommendation]:** the program's existing Odoo.sh
  project, staging-class build (the same class that produced the Wave 1
  runtime evidence, builds `34986844`/`34995642`), multi-worker where the
  test requires it (Layer 2/concurrency rows). Exact build IDs are recorded
  per run; a budget measured on a different build class is labeled as such.
- **Dev store:** the VAL-B2 Shopify dev store (acceptance-matrix row 22
  precondition). [Fact] Dev stores run at the Standard-plan restore rate
  unless documented otherwise — throttle-bound throughput measured there is
  a **conservative floor** for Advanced/Plus/Enterprise merchants (restore
  rates 100/200/1000/2000 points/s — [Fact], capture §11).
- **Datasets:** RD-1 and RD-2 exactly as defined in
  [`performance-budgets.md`](../03-architecture/performance-budgets.md) §1.4
  [Fact]. This plan adds the following extensions for the new domains, all
  [Recommendation], sized from the budget file's own corpus plus the mission
  brief's dataset spec:

| Dataset | Spec | Basis |
| --- | --- | --- |
| RD-1 (baseline) | 1 store, 1k products (100 multi-variant), 10k variants, 100k partners, 5k orders, 10k jobs, 100k log rows, 2 locations | [Fact] PB §1.4 |
| RD-2 (large) | RD-1 with jobs/logs ×10 (100k jobs, 1M log rows) | [Fact] PB §1.4 |
| RD-3 (multi-store) | 3 stores sharing one DB, each with the RD-1 product/partner corpus scaled to ⅓ | [Recommendation] proves per-store isolation (watermarks, queues, reconciliation independence — MBQ-17 posture) |
| RD-4 (catalog scale) | 10k and 50k products; one 2,048-variant edge product (fixture-only — [Fact] 2048 is the Shopify ceiling, capture §10; MVP export jobs are bounded ≤100 variants, D-015-4, so the edge product exercises **import** and UI rendering, not export) | [Recommendation] |
| RD-5 (operations day) | Simulated operating day: 500 orders/day (avg 3 lines, max 50 lines), 1,000 inventory level updates/hr peak, 300 fulfillments/day | [Recommendation] — sized so the order volume stays within PB-18's enumeration budget (500/min ≫ 500/day) and the inventory peak deliberately exceeds PB-20 (300/hr) to exercise coalescing/backlog behavior |

- **Measurement classes** [B]/[U]/[T] per PB §1.2 [Fact]; [T] rows measured
  over ≥5 min [Fact].
- **Warning vs failure thresholds [Recommendation, uniform rule]:** failure
  = the PB budget itself (a failed budget is a defect — [Fact] PB §1.3);
  warning = 80 % of the budget consumed (latency rows: measured ≥ 0.8 ×
  budget; throughput rows: measured ≤ 1.25 × budget floor). Rationale: a
  fixed uniform margin keeps the table auditable and avoids inventing 23
  bespoke numbers; PERF-1/Wave 6 may recalibrate per row with evidence.

## 2. Interactive rows PB-1..8 [U]/[B]

| Row | Rationale | Method | Warning / failure | Fallback / degradation | Required proof |
| --- | --- | --- | --- | --- | --- |
| PB-1 enqueue ≤300 ms p95 / UI ≤500 ms | Enqueue-only design means the click is a DB write, not a network call | [B] server timing over ≥50 clicks on RD-1; [U] devtools trace in the UAT session | 240/300 ms; 400/500 ms | None — a slow enqueue is a defect (no degradation mode) | Odoo.sh: timing log; dev store: n/a |
| PB-2 dashboard first render ≤1.5 s p75 (RD-1) / ≤2.5 s (RD-2) | First-screen answer bar is the product's core promise | [U] tour/devtools p75 over ≥20 loads, both datasets | 1.2/1.5 s; 2.0/2.5 s | Aggregates only (PB-10); if RD-2 degrades super-linearly → index/query defect (PB-11) | Odoo.sh UI walkthrough recording |
| PB-3 interaction ≤200 ms p75 | [Fact] INP "good" ≤200 ms (PB grounding, captures 2026-07-11 §13) | [U] INP measurement across the UAT keyboard run | 160 ms / 200 ms | Visibility-aware refresh; no synchronous recompute on click | Odoo.sh UI trace |
| PB-4/PB-5 list loads ≤1.5 s (RD-1) / ≤2.5 s (RD-2) | Server-paginated lists must stay flat with job-count growth | [U] p75 over ≥20 loads per dataset per screen | 1.2/1.5 s; 2.0/2.5 s | Server pagination is structural (PB-9); no full-recordset fetch exists to fall back from | Odoo.sh runs at both RD-1 and RD-2 |
| PB-6 job-log detail ≤1 s at 500 rows | Log thread is the debugging hot path | [U] p75, fixture job with 500 log rows | 0.8 s / 1 s | Paginated log thread | Odoo.sh UI trace |
| PB-7 no main-thread block >500 ms; INP ≤200 ms | Browser responsiveness during operation | [U] performance trace across the UAT run | any block >400 ms warning / >500 ms failure | — | Odoo.sh UI trace |
| PB-8 DOM ≤1,500 nodes; heap stable ±20 % over 10 min | Leak prevention on auto-refresh surfaces | [U] devtools memory sampling, 10-min Sync-Center session | 1,200 nodes / 1,500; ±15 % / ±20 % | Pause auto-refresh in background tabs (PB-12) | Odoo.sh UI session recording |

## 3. Structural rules PB-9..12

These are binding design rules, not numbers [Fact — PB §3]. Benchmark plan:
PB-9 and PB-10's aggregate-only rule get **source-guard tests** (list
fetches carry explicit limits; dashboard components use
`read_group`/count); PB-10's ≤500 ms aggregate query bound and PB-11's
RD-1-vs-RD-2 super-linearity check run as [B] query timing in the Wave 6
session; PB-12 (≥30 s polling, visibility-aware) is a UI code review +
runtime observation item. Failure of any = defect owned by the shipping
task [Fact — PB-11].

## 4. Backend/domain rows PB-13..23

| Row | Rationale / evidence | Environment + dataset | Method | Warning / failure | Fallback | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| PB-13 single-customer match ≤50 ms p95 @100k partners | Calibrated by D-011B-7(a) benchmark [Fact]; already measured green on build `34863138` (acceptance matrix row 8) | Odoo.sh, RD-1 partners | [B] benchmark suite re-run | 40/50 ms | Indexed path is the design; regression = defect | Odoo.sh benchmark log (re-confirmation) |
| PB-14 matching throughput ≥20/s @100k | D-011B-7(b) [Fact] | as PB-13 | [B] | ≤25/s warning floor check / <20/s failure | — | Odoo.sh benchmark log |
| PB-15 100-variant product import ≤10 s p95 (excl. images) | D-010B-11 [Fact] | Odoo.sh, RD-4 fixture | [B] | 8/10 s | — | Odoo.sh timing |
| PB-16 import incl. images ≤60 s / 100-variant product | D-010B-11 dev-store run [Fact] | dev store | [B] | 48/60 s | Image download failures route per media error handling, never block field import | Dev-store timing |
| PB-17 variant structure (3-option, 50-variant) ≤5 s | Task 010B suite [Fact] | Odoo.sh | [B] | 4/5 s | — | Odoo.sh timing |
| PB-18 order scan ≥500 enumerated+enqueued/min | Sized for catch-up after long gaps; RD-5's 500 orders/day makes live load trivial — the budget protects reconnect/backfill | Odoo.sh + dev store, RD-5 order corpus | [T] ≥5 min | ≤625/min warning / <500/min failure | Throttle-aware paging degrades gracefully (backoff, lower backfill priority — RB policy §5.5) | Odoo.sh log + dev-store scan run |
| PB-19 drain ≥600 jobs/hour (topology A) | [Fact] owned and calibrated by Task PERF-1 (see the PB-19 cell's full history); demonstrated against a representative handler-latency profile, not stub arithmetic | Odoo.sh single worker, RD-1/RD-2 job corpus | [T] sustained ≥5 min with representative latency profile | ≤750/h warning / <600/h failure | Configurable per-pass cap/cadence (PERF-1); backlog visible to operator | Odoo.sh PERF-1 calibration record |
| PB-20 inventory push ≥300 level-pushes/hour | [Fact] PB row; plausibility vs platform [Fact — capture §11]: mutations cost 10 points, Standard restores 100 points/s ⇒ ~10 mutations/s theoretical ceiling ≈ 36,000/h — the 300/h budget consumes <1 % of the Standard throttle, so the budget is connector-bound, not platform-bound | Dev store (Task 013 run), RD-5 inventory peak | [T] ≥5 min sustained, throttle pacing on | ≤375/h warning / <300/h failure | Last-value-wins coalescing bounds backlog by pair count (inventory model §9); backlog age surfaced | Dev-store Task 013 run |
| PB-21 baseline preview @1k mapped pairs ≤5 min | 013B preview must fit an operator's attention span | Odoo.sh + dev store, 1k mapped pairs | [B] | 4/5 min | Preview is read-only; a slow preview delays, never corrupts | Dev-store 013B run |
| PB-22 media submit ≤5 s/image; READY within 30 min poll SLA or FAILED routing | 015B pipeline [Fact] | dev store | [B]+[T] | 4 s / 5 s; 24/30 min | FAILED routes to review (never imageless mid-replacement) | Dev-store 015B run |
| PB-23 011B backfill @100k partners ≤10 min | D-011B-4 [Fact] | Odoo.sh, RD-1 partners | [B] measured and quoted | 8/10 min | Module-upgrade window planning | Odoo.sh upgrade log |

## 5. NEW proposed SLO rows — Wave 2–5 domains

All rows below are **provisional — calibrated by PERF-1/Wave 6**. None is a
release gate until measured and adopted into
[`performance-budgets.md`](../03-architecture/performance-budgets.md) via
its dated-edit recalibration rule. Each number's basis is labeled.

| ID (proposed) | Operation | Provisional target | Basis | Method / dataset | Warning / failure | Fallback / degradation | Required proof |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PB-24p | **Order import throughput** (full per-order import incl. binding, customer resolve, financial gate, SO create) | ≥120 orders/hour sustained per worker | [Recommendation] — derived from PB-19: order import jobs ride the same drain (≥600 jobs/h); an order consumes several sub-steps, so a 5:1 derate is a conservative planning floor; it also clears RD-5's 500 orders/day (~21/h avg) with >5× headroom. Platform is not the constraint: reads are cost-cheap vs the Standard 100 points/s restore rate [Fact — capture §11] | [T] ≥5 min, dev store + Odoo.sh, RD-5 corpus | ≤150/h warning / <120/h failure | Queue depth + backlog age surfaced; catch-up/backfill run at lower priority than live sync | PERF-1 + Wave 2 dev-store run |
| PB-25p | **COD ledger computation** (five values recomputed on a picking validation or collection event) | ≤500 ms p95 per order at 50 order lines | [Recommendation] — the ledger is a bounded per-order aggregation over moves + events (COD doc §4); 500 ms aligns with PB-10's aggregate-query bound; no platform dependency | [B], fixture orders at 3/10/50 lines | 400/500 ms | Computation is derived/read-model — a slow compute delays display, never money truth | Wave 4 suite timing |
| PB-26p | **Backfill preview latency** (read-only preview of a 30-day range at RD-5 volume ≈ 15k orders) | ≤10 min | [Recommendation] — Shopify-read-bound: enumeration at the PB-18 floor (500/min) covers 15k orders in 30 min worst-case; preview reads less per order than import, and PB-21 (5 min/1k pairs) establishes the operator-attention precedent; 10 min is the midpoint pending measurement. Restore-rate math [Fact — capture §11]: paged order reads at Standard rate do not throttle-bind this volume | [B]+[T], dev store, seeded 30-day range | 8/10 min | Preview shows progress + is cancellable; count accuracy is UAT-RB-3.1's job, not speed | Wave 2 dev-store run |
| PB-27p | **Layer 2 attempt overhead** (extra latency per mutation from C1/C2/C3 commits + attempt-row insert vs a bare call) | ≤50 ms p95 added per mutation attempt | [Recommendation] — L2 design §13 [Inference basis]: ~2 extra commits + one row insert, "dwarfed by the network round-trip"; 50 ms is a planning ceiling for two commits on Odoo.sh-class PG, to be measured | [B] paired benchmark (wrapper on/off) on Odoo.sh | 40/50 ms | None — safety machinery is not disableable; if overhead exceeds budget the fix is implementation tuning, never bypass | Layer 2 runtime-proof pass |
| PB-28p | **Reconciliation-read latency** (uncertain-outcome resolution read, per L2 §4.2 row) | ≤30 s p95 from job start to attempt-outcome decision (excluding queue wait) | [Recommendation] — each reconciliation is one targeted read (InventoryLevel quantities / FO remaining / product by identifier) costing single-digit query points [Fact — objects cost 1, capture §11]; 30 s covers throttle backoff (recommended 1 s [Fact]) with margin | [B]+[T], dev store fault-injection runs | 24/30 s | Inconclusive after N=3 → `blocked_manual_review` (L2-D9) — the taxonomy, not speed, bounds the worst case | Layer 2 runtime-proof pass |
| PB-29p | **Inventory push throughput** | ≥300 level-pushes/hour | [Fact] — this is PB-20 restated for the new-domain table; not a new number. Batched multi-entry `inventorySetQuantities` (25–50 entries [Recommendation — inventory model §9]) raises effective throughput; per-entry userErrors keep failures per-pair | as PB-20 | as PB-20 | as PB-20 | Task 013 dev-store run |
| PB-30p | **Catch-up scan completion** (per domain, 7-day gap at RD-5 volume) | ≤60 min per domain | [Recommendation] — 7 days × 500 orders/day = 3.5k changed records; at the PB-18 enumeration floor this is ≈7 min of scanning plus import time at PB-24p; 60 min keeps the "Catching up…" phase within one operator session | [T], dev store, staged 7-day gap | 48/60 min | Per-domain progress UI; domains complete independently; abandoned checkouts explicitly lowest priority | Wave 6 reconnect UAT run |

**Competitor/platform evidence note.** [Competitor claim] The 2026-07-16
competitor refresh
([`../00-source-materials/competitor-refresh-2026-07-16.md`](../00-source-materials/competitor-refresh-2026-07-16.md))
records recurring real-world complaints about duplicate records and unsafe
re-import in competing connectors, but **no competitor publishes verifiable
throughput/latency SLOs** in our corpus — so no competitor number is used as
a calibration basis above; the platform-side bases are Shopify's published
restore rates and costs [Fact — capture §11] only. Publishing measured SLOs
is therefore itself a differentiator, provided every number ships measured,
not promised.

## 6. Go/No-Go integration

Per [Fact — PB §5]: release Go/No-Go receives this table fully measured, or
each unmeasured row with an explicit dated waiver — silence is not a waiver.
PERF-1 (PB-19 owner) is sequenced before performance UAT [Fact]. Each
measurement replaces "provisional" with "measured YYYY-MM-DD" in
[`performance-budgets.md`](../03-architecture/performance-budgets.md) via
its dated-edit rule; the PB-24p..30p rows are adopted into that file (with
final IDs) only through the same rule — this plan never edits budgets by
itself.
