# Scalability and performance report

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

**Status:** source-capacity audit and test proposal. No capacity threshold in
this document is accepted or measured.

## Current controls

| Workload | Current implementation | Observed bound | Assurance consequence |
| --- | --- | --- | --- |
| Dispatcher | `job_dispatch.run_drain()`; default 20 jobs/pass, configurable 1–500; Odoo cron progress and per-job commit | 5-minute cron nominal; bounded by time budget and throttle backpressure | Good boundedness; throughput/backlog recovery unmeasured. |
| Products | `product_scan.py`: cursor pages of 100, maximum 200 pages | 20,000 products per scan window | Above cap fails closed and repeats the same window; no resumable enumeration or Bulk Operations. |
| Product variants | Importer child pagination with bounded accumulated pages | `MAX_VARIANT_PAGES = MAX_ACCUMULATED_VARIANTS + 2` | Shape/cap failure is conservative; large-catalog capacity unproven. |
| Orders | `order_scan.py`: cursor pages of 100, maximum 100 pages, overlap window | 10,000 orders per run | Above cap fails closed; no resumable enumeration or Bulk Operations. |
| Order children | Lines 100/page, shipping/discount pages 50/page, each max 100 pages | Bounded per order | Malformed/incomplete shape fails closed; per-order stress unmeasured. |
| Fulfillment reads | `fulfillment_reader.py`: 50/page, max 100 pages | 5,000 remote nodes/read | Incomplete page set is not treated as absence; large store capacity unproven. |
| Fulfillment reconciliation | `fulfillment_scans.py`: local pages 200, max 250 pages | 50,000 local records/pass | Bounded, fail-closed; backlog recovery unmeasured. |
| API throttle | Client extracts `extensions.cost.throttleStatus`; store persists availability/max/restore rate; drain defers backpressured stores | Shopify app/store bucket and query-cost limits apply | Code is cost-aware; exact configured store cost and recovery rate unmeasured. |
| Database | Store/company indexes and uniqueness; Odoo 19 `try_lock_for_update()` | Depends on Odoo.sh database/worker size | Query counts, lock waits and memory not measured on target build. |

## Missing large-volume capability

No production code references `bulkOperationRunQuery`, bulk operation status,
result download or bulk result reconciliation. Shopify documents Bulk Operations
as an asynchronous path for large connections and volumes. Product/order caps
therefore represent safe local limits, not support for stores larger than those
limits. A correction must choose one of:

1. implement resumable cursor windows with durable checkpoints and forward
   progress; or
2. add a bounded Bulk Operations reader with operation identity, polling,
   result validation, failure/cancel/restart handling and per-store fairness.

The decision must be made before a production capacity claim, not hidden behind
an increased page cap.

## Proposed workload assumptions

These are **[Recommendation] provisional test inputs**, not observed merchant
commitments:

| Scenario | Proposed data/workload |
| --- | --- |
| Medium catalog | 20,000 products, 60,000 variants, 20 locations, 60,000 inventory pairs |
| Large catalog | 100,000 products, 300,000 variants, 50 locations, 300,000 inventory pairs |
| Order burst | 10,000 updated orders across a 30-minute window, with 10% line/discount/fulfillment changes |
| Webhook burst after correction | 100 deliveries/minute for 15 minutes, including 20% duplicates and 5% out-of-order events |
| Multi-store fairness | 10 stores with mixed product/order/inventory/fulfillment queues and one throttled store |
| Recovery | Worker restart at pre-network, post-network/pre-finalization and reconciliation checkpoints |

## Provisional budgets to measure

The following budgets must be agreed by the control room before the performance
run. They are not acceptance results:

| Metric | Provisional budget | Measurement required |
| --- | --- | --- |
| Queue claim/dispatch | At least 90% of claimable jobs drained within 15 minutes under medium workload, excluding Shopify throttle wait | Jobs claimed/completed, backlog age and per-store fairness |
| Reconciliation freshness | 95% of webhook-triggered entities processed within 2 minutes after durable acknowledgement; scheduled fallback within one configured scan window | Delivery timestamp, enqueue/start/end, watermark and remote read |
| API safety | No request exceeds Shopify’s documented single-query cost/input bounds; no uncontrolled retry storm | Requested/actual cost, throttle bucket, retry count and `Retry-After`/classification |
| Database | No unbounded query in a production handler; p95 handler query count and lock wait recorded | Odoo SQL/query counter, `EXPLAIN` for critical searches, lock wait/transaction duration |
| Memory | No worker growth beyond the agreed Odoo.sh worker budget during large scan/import | RSS/worker restart, page/object retention and result sizes |
| Recovery | Backlog returns to pre-failure level within 30 minutes after transient recovery for medium workload | Restart time, retry backlog, manual-review count and no-duplicate audit |
| Duplicate storm | 100% duplicate deliveries coalesce without additional effective mutation | Delivery IDs, job IDs, attempts and remote effective state |

## Required test evidence

- Record volume, page/cursor count, elapsed time, API requested/actual cost,
  throttle availability, jobs/attempts per minute, retries, failure rate,
  backlog age, recovery time, query count, lock waits and memory.
- Test one store exceeding each current cap and verify fail-closed behavior is
  visible and recoverable; then test the selected resumable/Bulk correction.
- Test one throttled store alongside healthy stores to prove fairness and no
  global starvation.
- Test duplicate webhook/event storms only after the webhook implementation
  exists; mocks do not satisfy the live burst gate.
- Run local/runtime stress only against controlled fixtures; do not perform
  harmful load against Shopify. Use small live sampling and remote read-back.

## Current conclusion

**[Inference] Scalability is not assured.** Bounded scans, throttle state and
Odoo cron progress are good foundations, but finite non-resumable caps, no Bulk
Operations path, long inbound cadences and absent webhook backpressure leave
large-store and burst behavior unknown.
