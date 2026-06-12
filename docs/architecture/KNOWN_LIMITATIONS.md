# Known Limitations

Documented performance and architectural limitations that are deferred
until the scale or trigger described in each entry justifies the fix.
Reviewed as part of the pre-multi-merchant hardening pass.

Last updated: 2026-05-30 (post-audit P3 triage)

---

## 1. Rate Limiter Not Shared Across Client Instances (P3-1)

**What:** `ShopifyClient.__init__` creates a new `ShopifyRateLimiter`
per instance.  Each sync class (`BaseImporter`, `RefundSync`, etc.)
calls `backend._make_api_client()` independently, so concurrent sync
runs or cron jobs for the same backend each believe they hold the full
1000-point budget while Shopify enforces one shared per-shop bucket.

**Current impact:** Negligible.  The limiter self-corrects after the
first API response via `update_from_response()` which reads Shopify's
`throttleStatus.currentlyAvailable`.  Odoo crons are advisory-locked
(same cron cannot run twice), so true concurrent API access from the
same backend is rare.  The retry logic (429 handling + circuit breaker)
absorbs any initial over-spend.

**Trigger to revisit:** Concurrent/parallel sync jobs per backend, or
sustained 429 errors visible in production logs beyond the first call
per sync run.

**Sketched fix:** Module-level `dict` keyed by `(db_name, backend_id)`
holding a shared `ShopifyRateLimiter` instance with TTL-based cleanup.
Cross-process sharing (multiple Odoo workers) would require a DB row
or Redis — significantly more complex.

---

## 2. One-Shot Clients Created Per-Record in Loops (P3-1 sub-finding)

**What:** Several code paths create a new `ShopifyClient` inside a
per-record loop, discarding it after one API call:

- `PaymentStatusHandler._get_transaction_gateway()` (payment_status_sync.py:533)
  — creates a new client per order during payment registration.
- `AccountMove._shopify_reverse_sync_payment()` (account_move.py:61)
  — creates a new client per invoice posted.
- `AccountMove._shopify_reverse_sync_refund()` (account_move.py:110)
  — same pattern for refund reverse sync.

The adaptive rate limiter never benefits because the client is garbage-
collected after one request.

**Current impact:** Harmless — each call is 5-10 points, well within
the budget.  Wasteful object creation (Session, HTTPAdapter, Lock) but
not a performance bottleneck.

**Trigger to revisit:** Next time these files are touched for any
reason (natural cleanup opportunity).

**Sketched fix:** Hoist `_make_api_client()` out of the loop — store
`self.client` on the handler at `__init__` time, or accept the client
as a parameter.  5-minute refactor per call site.

---

## 3. No Bulk Operations API for Large Backfills (P3-2)

**What:** Refund and transaction imports issue one GraphQL query per
order (`FETCH_REFUNDS`, `GetOrderTransactions`).  This is inherent to
Shopify's per-order data model — there is no top-level `refunds` or
`transactions` connection in the Admin GraphQL API.

Shopify's `bulkOperationRunQuery` API could export all orders with
their refunds/transactions as a single async JSONL download, but the
module does not use it.

**Current impact:** Low at single-merchant scale.  A store with 100
orders/month and 5% refund rate = 5 API calls/month for refunds.
The refund scan pruning fix (Layer 1 + Layer 2) eliminates repeat
calls on already-imported orders, so steady-state cost is near zero.

**Trigger to revisit:** Initial backfill of a store with >5,000
historical refunded orders, or migration from another connector with
years of order history.

**Sketched fix:** Implement `bulkOperationRunQuery` as an alternative
import path for initial sync.  Requires: async webhook callback for
completion, JSONL parser, polling for operation status.  Substantial
complexity — only justified for large-scale backfills.

---

## 4. Reconciliation N+1 Loop (P3-3, partially addressed)

**What:** `_reconcile_payment_status()` and `_reconcile_fulfillment_status()`
in `shopify_reconciliation.py` iterate bindings with per-record
`order.invoice_ids.filtered()` and `order.picking_ids.filtered()` calls.
Pass 2 (refund reconciliation) additionally fires one `search_count()`
SQL query per binding inside the loop.

**Partially addressed:** Indexes added to `shopify_financial_status`
and `shopify_fulfillment_status` (P3-3 fix) to speed up the initial
search queries.  The per-record loops remain.

**Current impact:** Bounded by `reconciliation_order_days` (default 30).
At single-merchant scale (<10K order bindings), the `filtered()` calls
operate on Odoo-prefetched data (not true N+1 SQL) and the
`search_count` loop is bounded to refunded orders (~5% of 30-day
window).  The same pattern in `_compute_reconciliation_health` runs on
every backend form render but on the same bounded dataset.

**Trigger to revisit:** Reconciliation cron runtime exceeding 60s, or
>50K order bindings in the table.

**Sketched fix:** Replace per-record loops with batched queries:
- `filtered()` loops → single `search()` on `account.move` joined
  via `sale.order` to collect all orders with/without posted invoices.
- `search_count` per binding → single `read_group` on
  `shopify.refund.binding` grouped by `order_binding_id`.
- Collapses N queries → 2 queries per pass regardless of binding count.

---

## 5. Shipping Tax Import Gap (from P0/P2-3 audit)

**What:** `OrderImporter._create_shipping_line()` in `order_sync.py`
creates the shipping line from `totalShippingPriceSet` but does not
map Shopify's per-shipping-line tax amounts to Odoo tax records.
Shipping tax is included in the order's `totalTaxSet` but not broken
out onto the shipping product's invoice line.

The refund path (`RefundImporter._create_refund_credit_note`) now
correctly handles shipping tax on refund credit notes (fixed in P0),
but the forward import path does not.

**Current impact:** Shipping tax is captured in the order total but
not attributed to the shipping line specifically.  For merchants with
tax-exempt shipping or flat-rate shipping in non-tax jurisdictions,
this has zero impact.  For merchants with taxed shipping, the tax
allocation between product lines and shipping lines may be slightly
off (though the invoice total is correct).

**Trigger to revisit:** Merchant reports tax-line discrepancies on
invoices, or tax compliance audit requires per-line tax attribution.

**Sketched fix:** Parse `shippingLines.taxLines` from the order
GraphQL response, map to Odoo `account.tax` records via fiscal
position, and set `tax_ids` on the shipping product's sale order line.
Requires extending the `FETCH_ORDERS` query to include shipping tax
detail.
