# Provisional Performance Budgets (Binding Targets Pending Runtime Calibration)

> **Status: Proposed for ChatGPT review. NOT accepted. Docs-only.**
> Produced 2026-07-11 by the PR #148 revision session, implementing
> review item 10 of ChatGPT's control-room review (PR #148 comment
> `4942966937`). This supersedes the "MVP explicitly defers hard
> budgets" posture (ARCH §5.11, revised the same session): budgets
> now **exist before implementation**, are testable, and are
> **recalibratable with recorded evidence** — but may not remain
> undefined until release. External grounding: INP "good" ≤ 200 ms
> (stable Core Web Vital) and the RAIL 100 ms response window as
> secondary guidance — captures 2026-07-11 §13
> (`../00-source-materials/odoo19-shopify-official-captures-2026-07-11.md`).
> Internal grounding: merged constants (drain cron 5 min, batch 20;
> savepoint batch 20) and the D-011B-7 / D-010B-11 benchmark rows.

## 1. Rules of the game

1. **Every budget is a named row (PB-x)** with a measurement method.
   A budget changes only by a dated edit here citing measured
   evidence (the recalibration rule) — never by silently ignoring it.
2. **Measurement classes:** [B] backend timing (test harness or
   Odoo.sh log), [U] browser timing (tour/HOOT run or devtools trace
   in the UAT session), [T] throughput (jobs or records per unit
   time, measured over ≥ 5 min).
3. **Gate use:** implementation packets cite the rows they must meet;
   UAT scenarios 27–28 (revised UAT plan) verify the [U] rows with
   pass/fail; release Go/No-Go receives the full measured table.
   A failed budget is a defect (severity per the revised UAT §5), not
   an observation.
4. Baseline reference dataset ("**RD-1**"): 1k products (100
   multi-variant), 10k variants, 100k partners (the D-011B-7 corpus),
   5k orders, 10k jobs, 100k job-log rows, 2 locations, 1 store.
   A "large" dataset ("**RD-2**") scales jobs/logs ×10 (100k jobs,
   1M log rows).

## 2. Interactive budgets (operator-perceived)

| ID | Surface | Budget (provisional) | Method |
| --- | --- | --- | --- |
| PB-1 | Manual action enqueue response (any "Sync now"/retry/cancel button → visual confirmation; enqueue-only by design) | server call ≤ 300 ms p95 on RD-1; UI feedback ≤ 500 ms end-to-end | [B]+[U] |
| PB-2 | Dashboard first useful render (lead answer band + primary exception region visible) | ≤ 1.5 s p75 on RD-1; ≤ 2.5 s on RD-2 | [U] |
| PB-3 | Dashboard interaction response (card click → filtered list starts loading; tab/filter switches) | INP-style ≤ 200 ms p75 (captures §13) | [U] |
| PB-4 | Sync Center list load (default filter, server-paginated page) | ≤ 1.5 s p75 on RD-1 incl. RD-1's 10k jobs; ≤ 2.5 s on RD-2's 100k jobs | [U] |
| PB-5 | Error Center load (manual-review queue default view) | same as PB-4 | [U] |
| PB-6 | Job-log detail open (one job's log thread) | ≤ 1 s p75 at 500 log rows/job | [U] |
| PB-7 | Browser responsiveness during any connector screen use | no main-thread block > 500 ms; INP ≤ 200 ms p75 across the UAT keyboard run | [U] |
| PB-8 | Memory/DOM | dashboard ≤ 1,500 DOM nodes; no unbounded growth: browser heap stable (±20 %) over a 10-minute Sync-Center auto-refresh session | [U] |

## 3. Data-scale rules (pagination/virtualization — binding design rules, not numbers)

| ID | Rule |
| --- | --- |
| PB-9 | Large tables (jobs, logs, bindings) are **server-paginated Odoo-native lists** — never client-side-loaded in full; no custom client action may fetch an unbounded recordset (source-guard in UI tasks: list fetches carry an explicit limit). |
| PB-10 | Dashboard/Owl components read **aggregates** (`read_group`/count queries), never full recordsets; every aggregate query on RD-2 ≤ 500 ms [B]. |
| PB-11 | 10k/100k job-log behavior: list views, filters, and the PB-4/PB-5 loads are measured at **both** RD-1 and RD-2; any query that degrades super-linearly between them is a defect (index or query fix owned by the task that shipped it). |
| PB-12 | No polling loop in the browser faster than 30 s; auto-refresh is visibility-aware (paused in background tabs). |

## 4. Backend/domain budgets

| ID | Operation | Budget (provisional) | Method / calibration source |
| --- | --- | --- | --- |
| PB-13 | Customer matching, single incoming customer at 100k partners | ≤ 50 ms p95 (indexed path) | [B] — D-011B-7(a), the benchmark that calibrates this row |
| PB-14 | Customer import matching throughput (sequential, matching cost only) | ≥ 20 customers/s at 100k partners | [B] — D-011B-7(b) |
| PB-15 | Product import: 100-variant product end-to-end (excl. image downloads) | ≤ 10 s p95 | [B] — D-010B-11 |
| PB-16 | Product import incl. images (dev store, primary+variant) | ≤ 60 s per 100-variant product | [B] — D-010B-11 dev-store run |
| PB-17 | Variant structure creation (attributes/values/lines/variants) for a 3-option, 50-variant product | ≤ 5 s | [B] — Task 010B suite timing |
| PB-18 | Order scan throughput (Area 6 enumeration, excl. per-order import) | ≥ 500 orders enumerated+enqueued/min | [T] |
| PB-19 | Drain throughput (dispatcher, topology A single worker) | ≥ 600 jobs/hour sustained. **Honesty note:** the merged constants (5-min cron × batch 20) cap at ~240/h; the constants are merged *adjustable defaults* (ARCH §5.2) — meeting PB-19 requires tuning them (batch and/or cadence) with evidence at the concurrency-plan run; the budget stands so the 5k-customer onboarding import completes inside one working day (~8.3 h at 600/h), which is the operator-experience bar | [T] — concurrency plan §13.2 |
| PB-20 | Inventory push throughput | ≥ 300 level-pushes/hour sustained within Shopify throttle budget (client already paces on `throttleStatus`) | [T] — Task 013 dev-store run |
| PB-21 | Baseline preview generation (013B) at 1k mapped pairs | ≤ 5 min | [B] |
| PB-22 | Media export pipeline (015B): submit ≤ 5 s/image; READY within poll SLA of 30 min or FAILED routing | [B]+[T] |
| PB-23 | Module-upgrade backfill (011B stored-compute) at 100k partners | ≤ 10 min, measured and quoted | [B] — D-011B-4 |

## 5. Recalibration & ownership

- Rows PB-13/14/23 are calibrated by Task 011B's benchmark; PB-15–17
  by Task 010B; PB-18/19 by the concurrency plan §13.2 + Area 6
  validation; PB-20–22 by the Task 013/013B/015B dev-store runs;
  PB-1–12 by the UI-U1 validation record + UAT scenarios 27–28.
- Each calibration replaces "provisional" with "measured YYYY-MM-DD"
  in this file (dated edit; append-only history note).
- Release Go/No-Go input: this table fully measured, or each
  unmeasured row carrying an explicit dated ChatGPT waiver — silence
  is not a waiver.
- Relationship to ARCH §5.11: that section now points here; "release
  hardening owns budget-setting" is superseded — release hardening
  owns budget *tuning*, the budgets themselves exist now.
