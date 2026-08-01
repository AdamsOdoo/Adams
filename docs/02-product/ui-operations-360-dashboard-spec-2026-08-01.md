# Shopify Store 360 — Dashboard Product Specification (2026-08-01)

**Subtitle: Sales performance and connector health.**

> **Status: Design concept + prototype specification. NOT implemented, NOT
> accepted, NOT a review.** Produced on the isolated branch
> `fable/ui-operations-360-concept` from the exact PR #204 head
> `a1c593183f6aaa1238e87486ca518717cefc53a9`. Nothing under `addons/**`
> changed; PR #204 is untouched. Every repository fact below was read at that
> exact head and cites its file. Classification per CLAUDE.md §8 throughout.

Companions: [competitor benchmark](../01-research/ui-operations-360-competitor-benchmark-2026-08-01.md) ·
[implementation handoff](../07-implementation-plan/ui-operations-360-dashboard-handoff-2026-08-01.md) ·
prototype [`prototypes/shopify-operations-360-dashboard.html`](prototypes/shopify-operations-360-dashboard.html)
(+ adjacent `.css`, screenshots under
[`prototypes/operations-360-dashboard-2026-08-01/`](prototypes/operations-360-dashboard-2026-08-01/)).

---

## 1. Product definition

One responsive page, replacing the current U0 dashboard content, that answers
two questions in order:

1. **How is my Shopify store performing?** (sales imported into Odoo)
2. **Is the connector operating correctly, and are those figures complete?**

The page stays **read-only**: it navigates to filtered native Odoo lists and
forms and does nothing else. It never initiates a Shopify mutation, enqueues
work, retries a job, reconnects a store, approves a decision, modifies
configuration, reads a credential, or calls Shopify. It is served by one
bounded aggregate RPC (the successor of
`shopify.connector.ui.dashboard.get_dashboard_data`,
`addons/shopify_connector_core/models/shopify_connector_ui_dashboard.py:60`),
run as the current user so ACLs and record rules apply.

**Never claimed:** "live", "real-time", Shopify Analytics parity, complete
store performance while imports are pending or failed, or any cross-currency
combined total.

## 2. Current-dashboard assessment (baseline read at `a1c5931`)

`[Fact — files read directly]`

- The U0 dashboard is a single Owl client action + AbstractModel aggregate
  with hard guarantees worth keeping: bounded constant-query reads, no
  sensitive data across the RPC boundary, count/domain agreement between a
  number and the list it opens, a single severity model, ≤3 exceptions,
  8-row activity feed, 30 s visibility-aware refresh floor
  (`shopify_connector_ui_dashboard.py`, `shopify_connector_dashboard.js`).
- **The healthy screen wastes its space.** The committed evidence screenshot
  (`docs/05-qa/evidence/wave-5-onboarding-2026-07-29/screenshots/u0-dashboard-healthy-desktop-1366px.png`)
  shows two stacked all-clear bands saying the same thing, five chips that are
  mostly `0`, one activity row, and more than half the viewport empty. A
  merchant learns nothing commercial from a healthy connector page.
- The 7-day sparkline renders only after seven full days of history and
  duplicates what two text counters can say.
- No commercial data appears anywhere on the dashboard today, while the
  repository already stores enough to answer "what did my store sell?"
  truthfully (§7).
- Strengths retained verbatim: severity model, count/domain agreement,
  redaction discipline, native drill-down mechanism, refresh contract, token
  layer, logical-property/RTL discipline.

> **Correction revision (control room, 2026-08-01).** This document was
> corrected in place on the concept branch: security-preserving aggregation
> (§6 intro, handoff §6), native sales-report feasibility (handoff §14),
> historical-coverage language (§9.4), dynamic test-order disclosure (§7.1),
> top-product denominator renamed (§6 E2), completeness-bridge language
> (§9.3), the Order lifecycle region (§3 L, §7.3–§7.5), the workflow
> traceability matrix (§14), and re-verified prototype evidence (§12–§13).
> **Final correction tail (2026-08-01):** drill-down/rule-model matrix and
> lifecycle-projection ruling (§6.1), warehouse-population labelling
> (ruling D), mobile exception-action containment and the ≥11 px chart-axis
> target at 390 px (§11, §13).

## 3. Information architecture (decision order)

One page, nine regions, in this order. No tabs, no second dashboard.

| # | Region | Contents |
| --- | --- | --- |
| A | **Shared header** | "Shopify Store 360" + subtitle; store selector (only listing real `shopify.connector.store` rows; "All stores" entry only when >1 store); period selector 24 h / 7 d / 30 d; comparison caption "vs previous 7 days"; Refresh button; "Updated HH:MM"; sales-freshness caption ("Sales data synchronized through …" — same source as region G). |
| B | **Critical status** (conditional) | One concise band shown **only** when a connector problem makes commercial figures materially incomplete or stale (§9.3). Names the cause, states the commercial consequence ("figures below may be incomplete"), one Review drill-down. Routine all-clear text never occupies this slot. |
| C | **Store performance** | Four KPI cards (max five allowed; the truthful set is four): Imported Shopify sales · Imported orders · Average imported order value · Units sold. Each: value, period, delta vs previous equivalent period, currency where applicable, definition line, native drill-down. |
| D | **Sales trend** | The page's only chart: daily (hourly for 24 h) imported-sales bars for the current period + dashed neutral line for the previous equivalent period. Accessible summary sentence + full table equivalent (`<details>`). Order counts live in the table, not on a second axis. |
| E | **Top products** | ≤5 rows: product, units, imported sales value, **share of goods subtotal** (denominator = the same eligible goods-line `price_subtotal` basis as the numerator — never the tax-and-shipping-inclusive headline), drill-down. No chart. |
| L | **Order lifecycle** (correction addendum §A) | Compact, exception-led block between top products and connector health, scoped to **imported Odoo orders in the selected period** (skipped Shopify states never appear as zeros — the caption says so). Three status strips + one exception list: **Payment** (Paid · Authorized — capture pending · Payment pending — non-COD · COD, with a needs-review remainder), **COD** (awaiting approval / quotation / confirmed; collection: nothing / partially / fully collected), **Fulfillment & dispatch** (Shopify order fulfillment progress from the stored snapshot + Odoo delivery-order dispatch states + oldest paid-unfulfilled age, elapsed time only, no invented SLA). Carrier delivery is **not** shown (unsupported at this head — §7.5). ≤3 lifecycle exceptions, each with what/why/who/freshness/drill-down. Every count opens the exact native record set with the same domain. Payment-evidence freshness caption from `shopify_last_evidence_refresh_at`. The full order population belongs to the (recommended) Order Operations Analysis workspace — this region summarizes and routes. |
| F | **Connector health** | Compact operational block: overall state line with quiet metadata (API health, last successful processing, scheduled-sync posture); four operational counters (active backlog, oldest waiting item, needs review, final failures); **five flow rows** (Orders, Catalog, Inventory, Product export, Fulfillment) each with plain-language state, last success, backlog, failures, drill-down; needs-attention list (≤3, severity+owner+reason+Review, decision items visually distinct from technical failures by icon+label, never colour alone); recent activity (≤8); "Last 7 days: N succeeded, M failed" as text, not a chart. |
| G | **Data-completeness bridge** | The explicit link between C–E and F: "Sales data synchronized through *timestamp* · *N* orders awaiting import · *M* order imports need attention", with one of four states — **Complete & current / Processing (within normal delay) / Stale / Incomplete — action needed** — and direct drill-downs to the pending/failed records. Rendered adjacent to the sales cards on every breakpoint. |
| H | **Multi-store health** (conditional) | Only when >1 store in scope: compact table — store, connection state, last successful activity, backlog, attention count, sales in period (per-store currency), drill-down. Single-store screens never render it. |

**Cross-currency rule:** when "All stores" is selected and store currencies
differ, regions C–E show per-store rows in H instead of combined money totals,
with the caption "Stores use different currencies — select a store for sales
totals." Combined totals across currencies are never shown (§7 truth rules).

## 4. What is deliberately omitted

- Revenue/"Net sales"/profit labels (§7.1), refunds column (§8), geography,
  customer segmentation, channel attribution, conversion/traffic, ROAS,
  margin, CLV, forecasting, AI recommendations, payout analytics (§8).
- A second operational chart, pies/donuts, gauges, configurable widgets,
  separate per-module dashboards, PDF packs.
- Any control that mutates state (retry, reconnect, approve, enqueue, setup
  shortcut stays only on the empty state as today — navigation, not
  authorization: `shopify_connector_dashboard.js:157-164`).

## 5. Data foundations `[Fact — exact head, cited]`

- Order binding: `shopify.connector.order.binding`
  (`addons/shopify_connector_sale/models/shopify_connector_order_binding.py`)
  — `sale_order_id` (M2O `sale.order`, required, indexed), `store_id`,
  `company_id` (related store company, stored), `shopify_processed_at`,
  `shopify_created_at`, `shopify_cancelled_at`, `shopify_financial_status_snapshot`,
  `status` (`active|stale|manually_overridden|review`),
  `sec3_scope_quarantined`. All Shopify money snapshots are **`Char` by
  design** (`shopify_order_total_amount` etc.) and are not aggregable.
- The importer **guarantees** each imported order's Odoo totals reconcile
  with Shopify money evidence or the import fails
  (`_solve_and_assert_totals`, `shopify_connector_order_importer.py:1845-1919`,
  error class `financial_total_mismatch`). So `sale.order.amount_total` is a
  verified mirror of the imported Shopify order total.
- `sale.order.date_order` = Shopify `processedAt` (fallback `createdAt`,
  fallback now) — importer:498-500. Currency is forced: the pricelist currency
  must equal the shop currency or the job fails (importer `_resolve_pricelist`);
  presentment≠shop currency orders are never imported. **All imported orders
  of one store share one currency.**
- Never imported (policy, at scan/import): already-cancelled orders
  (`order_pre_cancelled`), REFUNDED/VOIDED/EXPIRED, order edits, orders with
  duties/tips/fees/cash-rounding, test orders unless
  `order_import_include_test`; PARTIALLY_REFUNDED is routed to review, not
  imported. Post-import divergence (incl. cancellation) only snapshots
  evidence and routes the binding to review — Odoo lines/amounts are frozen
  (`_refresh_existing`, importer:2305+, "existing commercial lines were left
  unchanged").
- Product lines carry `sale.order.line.shopify_line_item_gid` (indexed);
  shipping (`SHOPIFY-SHIPPING`), rounding (`SHOPIFY-ADJUSTMENT`) and residual
  discount lines are created **without** it — so gid-filtered lines are
  exactly the goods lines.
- Freshness anchors: `store.order_sync_last_checkpoint_at` ("Discovered up
  to"), `order_sync_scheduled` (verifies the 15-min cron is genuinely active),
  `order_sync_active_scan_count`, plus per-domain checkpoints:
  `product_last_import_success_at`, `inventory_last_push_scan_at`,
  `fulfillment_last_reconciliation_at`, export `applied_at`/`export_reconcile_at`.
- Jobs: states `draft queued running succeeded failed_final skipped cancelled
  retry_waiting failed_retryable blocked_manual_review`
  (`shopify_connector_job.py:6-17`); per-flow `job_type` families (exact
  values §6 flow rows); `retry_count`, `next_retry_at`, `started_at`,
  `finished_at`; queue age via `create_date`.
- Decisions: uncertain mutation attempts (`observed_outcome='uncertain'`,
  `resolution_disposition=False`), product match decisions
  (`shopify.connector.product.match.decision`, `state='pending'`), manual
  gateway approvals (`manual_gateway_approval_state='pending'`), tax-mapping
  configuration failures (jobs `failed_retryable` +
  `error_class='odoo_validation_configuration'` — the existing
  "Awaiting Configuration" action).
- **Payment / COD evidence on the order binding** (order_binding.py:31-111):
  raw `shopify_financial_status_snapshot` +
  `shopify_previous_financial_status_snapshot` (Char — raw enum value
  preserved), `financial_status_changed_at` + `financial_status_trigger_source`,
  `shopify_last_evidence_refresh_at` (payment-evidence freshness),
  `manual_gateway_name` / `manual_gateway_evidence_state`
  (`not_manual|unambiguous|mixed`) / `manual_gateway_approval_state`
  (`not_required|pending|approved|superseded`) + approver/uid/at fields,
  `is_cod` (Boolean), `cod_commercial_state`
  (`imported|quotation|confirmed|review|cancelled`), `cod_fulfillment_state`
  (**selection contains only `not_dispatched`**), `cod_collection_state`
  (`nothing_collected|partially_collected|fully_collected|discrepancy`), and
  the five `cod_*_value_amount` **Char** snapshots. Import policy machine:
  `_confirmation_outcome` (importer:2178-2230) — PAID/AUTHORIZED confirm per
  `order_confirmation_policy`; PENDING is COD **only** with an unambiguous
  approved manual gateway (never inferred from PENDING alone); PENDING
  non-manual waits (`retry_waiting`, recheck loop) until
  `pending_wait_expiry`, then the job is **skipped**
  (`payment_pending_expired`, importer:2745-2773); PARTIALLY_PAID imports
  only under `quotations_only` and then as a review binding; unknown enum
  values fail closed (`data_shape_schema_mismatch`, importer:676-686 and
  refresh path 828-842). Dormant at this head (selection values with **no
  production writer**): `cod_collection_state='discrepancy'`,
  `cod_commercial_state='cancelled'`, the entire `cod_fulfillment_state`
  lifecycle beyond `not_dispatched`; `cod_refunded_value_amount` /
  `cod_cancelled_value_amount` / `cod_fulfilled_value_amount` are written as
  literal `'0'`.
- **Fulfillment / delivery evidence** (fulfillment module): per created
  fulfillment a binding (`shopify.connector.fulfillment.binding`:
  `picking_id` UNIQUE per store, `shopify_status_snapshot` +
  `shopify_status_normalized` + `shopify_last_synced_at`, tracking
  snapshots); per **observed** fulfillment an evidence row
  (`shopify.connector.fulfillment.inbound.evidence`: A4
  `fulfillment_status_raw/normalized/is_success` with the fail-closed
  unknown-value contract `schema_warning`, A7 `display_status_raw` /
  `display_status_normalized` — **display only, never an automation
  input**, `first_observed_at`/`last_observed_at`, `origin_class`
  connector/external_*, `reconciled_state`
  observed/review/acknowledged/applied/superseded, named `review_reason`
  vocabulary). Order-level fulfillment progress:
  `binding.shopify_fulfillment_status_snapshot` (raw Shopify
  `displayFulfillmentStatus`, refreshed at import + evidence refresh).
  **Carrier delivery is not tracked at this head**: the production GraphQL
  readers fetch only `status` + `displayStatus` + `trackingInfo`
  (fulfillment_reader.py:60, fulfillment_tracking_strategy.py:37) — A5
  `FulfillmentEvent` records are never queried; `delivered_inconsistency`
  (inbound_evidence.py:142) and the `delivered_not_validated` /
  `unknown_status_value` review reasons have **no production writer**;
  `cancelled_after_validation` **is** written
  (fulfillment_scans.py:187-202). Mode 1 routes external fulfillments to
  review (`external_fulfillment_observed` / `origin_unconfirmed`,
  fulfillment_inbound.py:183-193); Mode 2 (16-condition engine) applies via
  `picking._action_done()` or opens a named review case
  (fulfillment_mode2.py:623,705).
- Store settings policy fields read by region L captions:
  `order_confirmation_policy` (`paid_only|paid_or_authorized|quotations_only`),
  `manual_gateway_policy` (`confirm_auto|quotation|require_approval`),
  `approved_manual_gateways`, `order_import_window` (default 30 days; >60
  requires the granted `read_all_orders` scope — store_settings.py:184-198),
  `pending_wait_expiry`, `order_import_include_test` (Boolean, default
  False — the test-order disclosure source, enforced at scan
  (`test:false` clause, order_scan.py:202-203) **and** import
  (importer:602)).

## 6. Metric traceability table (the gate)

Every displayed element passes this gate or does not appear. "Endpoint"
means the new bounded aggregate contract (slice 1 of the handoff): the data
source exists at the exact current head; the aggregate RPC that serves it is
the (not yet implemented) production step. Domains are the truthful
definitions the endpoint must implement; commercial rows additionally apply
the §7 truth rules. Company isolation for every row: record rules on
connector models + an explicit `company_id in allowed_companies` term +
`sec3_scope_quarantined = False`; the endpoint never uses `sudo()`.

**Security-preserving aggregation (correction A — supersedes the earlier
raw-SQL recommendation):** commercial rows (C1–E2, H1 sales cell, region L
order buckets) are aggregated **on `sale.order` / `sale.order.line`
themselves with ORM grouped reads (`formatted_read_group` / `_read_group`,
plus `search_count`/`search`), as the current user, with the native
sale ACLs and record rules left fully active** — never raw SQL, never
`sudo()`. The store dimension comes from connector-owned, protected, stored,
indexed projection fields contributed by `shopify_connector_sale` (handoff
§6 defines them); binding-side exclusions (Shopify-cancelled-after-import,
SEC-3 quarantine) are mirrored by the same sanctioned writers into stored
projection flags so every predicate is expressible in the rule-respecting
ORM domain. Consequence, by construction: a user whose record rule restricts
`sale.order` sees aggregates over exactly the records their drill-down list
shows — the count/domain-agreement invariant extends to restrictive-rule
users instead of breaking for them. `[Fact]` The repository already proves
Odoo 19 grouped reads are rule-scoped: `test_grouped_read_does_not_leak_foreign_rows`
(`addons/shopify_connector_sale/tests/test_sec3_company_isolation.py:144-158`,
"`formatted_read_group` is the Odoo 19 replacement for the deprecated
`read_group`"). `[Fact]` Official Odoo guidance: record rules "are
*conditions* which must be satisfied in order for an operation to be
allowed… evaluated record-by-record, following access rights", and using
the cursor directly bypasses "the automated behaviours like translations,
invalidation of fields, `active`, access rights and so on"
(odoo/documentation@19.0 `content/developer/reference/backend/security.rst`,
accessed 2026-08-01). Operational rows (G/F/H counts) stay on connector
models exactly as before.

**Drill-down ruling (final correction tail, 2026-08-01) — the aggregate
model, the rule model and the drill-down model must be the same model.**
The earlier revision still routed commercial counts to the Orders Workspace,
which opens `shopify.connector.order.binding` — a model whose record rules
enforce connector company/quarantine scope but do **not** reproduce
arbitrary `sale.order`/`sale.order.line` rules; a relational domain through
`sale_order_id` does not by itself apply the caller's sale-document rules.
That claim is withdrawn. Corrected rulings:

- **Order-grain commercial metrics** (C1–C3, C∆, D1, H1 sales, L1–L4, L6)
  aggregate on `sale.order` and drill down to a **native `sale.order` list**
  via a server-built act_window carrying the identical projected-field
  domain — same model, same domain, same current-user rules, so
  count = drill-down by construction, including for rule-restricted users.
- **Line-grain metrics** (C4, E1, E2 basis) aggregate on `sale.order.line`
  and drill down to a **native `sale.order.line` list** with the identical
  domain — never to a binding list with a claimed equivalence.
- **Lifecycle strips** (L1–L4, L6): the payment/COD/fulfillment source
  fields live on the binding, so the selected architecture extends the
  slice-1 projection with **lifecycle mirror fields on `sale.order`**
  (§6.1 note) written by the same sanctioned import/refresh/approval
  writers in the same transaction — no raw SQL in the dashboard path, no
  `sudo()`, no client-visible ID list, aggregate = drill-down on
  `sale.order` under the caller's rules, and no hidden-order count, label
  or state can leak because every read runs on the ruled model.
- **Warehouse dispatch** (L5) is defined as the **rule-visible warehouse
  population**: it aggregates `stock.picking` as the caller (picking
  ACL/rules govern it — they do not equal sale-order rules and are not
  claimed to) and drills down to the native Delivery Orders list with the
  identical domain — exact on its own model; the label says whose rules
  apply.
- **Lifecycle exceptions** (L7) count connector evidence surfaces
  (bindings, fulfillment evidence, attempts, decisions) under connector
  rules and drill down to those same connector lists — same-model
  agreement; their payload carries connector state names and counts the
  caller can already list natively, never sale-document fields.

### 6.1 Aggregate model → rule model → drill-down model matrix

| Metrics | Aggregate model | ACL/record-rule model that governs | Drill-down `res_model` | Population intersection | Count-to-drill-down agreement | Status |
| --- | --- | --- | --- | --- | --- | --- |
| C1, C2, C3, C∆, D1, H1 sales cell | `sale.order` (grouped reads) | `sale.order` (caller's ACLs + all record rules, applied inside every grouped read) | `sale.order` | projected fields (`shopify_connector_store_id`, cancellation + quarantine mirrors) ∩ the caller's rule-visible orders | identical model + domain + user for aggregate and list | **Selected — slice 1a (core commercial projection, 3 columns + backfill)** |
| C4, E1, E2 basis | `sale.order.line` | `sale.order.line` (independent of the order-level rule) | `sale.order.line` | `shopify_line_item_gid != False` ∩ order-projection terms ∩ the caller's rule-visible lines | identical model + domain + user | **Selected — slice 1a** (no new line field needed) |
| L1 payment strip, L2 freshness, L3 COD states, L4 fulfillment progress, L6 oldest paid-unfulfilled | `sale.order` (lifecycle mirror fields) | `sale.order` | `sale.order` | lifecycle mirrors ∩ the caller's rule-visible orders | identical model + domain + user | **Selected — slice 1b (lifecycle projection, §6.1 note); if the control room declines 1b's schema breadth, these strips become an UNRESOLVED slice-1 prerequisite and region L ships exception-list-only** |
| L5 dispatch | `stock.picking` (as caller) | `stock.picking` | `stock.picking` (native Delivery Orders) | outgoing pickings of bound orders (data relationship via `sale_id` → projected store; **no sale-rule claim**) | identical model + domain + user; labelled "rule-visible warehouse population" | **Selected with the ruling-D label** |
| L7 exceptions | binding / fulfillment evidence / mutation attempts / match decisions | each connector model's own rules (company + SEC-3 quarantine) | the same connector model's list | connector-native visibility (caller can already open these lists) | identical model + domain (existing tested invariant) | **Selected (existing mechanism)** |
| G2, G3, F2–F9, H1 operational cells, B1 | `shopify.connector.job` / store / settings | connector models' rules | Sync Center / Error Center / job or store form | connector-native | identical model + domain (existing tested invariant) | **Selected (unchanged)** |

**§6.1 note — slice-1b lifecycle mirror fields** (all readonly, written only
by the sanctioned importer/refresh/approval writers in the same transaction
that writes the binding, backfilled by the slice-1 migration):
`shopify_connector_financial_status` (Char mirror of the raw snapshot),
`shopify_connector_is_cod` (Boolean), `shopify_connector_approval_state`,
`shopify_connector_cod_commercial_state`,
`shopify_connector_cod_collection_state`,
`shopify_connector_fulfillment_status` (Char mirror),
`shopify_connector_review` (Boolean mirror of `binding.status='review'`),
`shopify_connector_evidence_refreshed_at` (Datetime). This widens the
sale-order footprint from 3 to ~10 connector columns — flagged explicitly
as a control-room review point; declining it triggers the fallback recorded
in the matrix row above, never a silent workaround.

| # | Displayed label | Operator question | Source model · stored fields | Domain / filter | Aggregation | Time window | Store isolation | Zero/empty behaviour | Stale-data behaviour | Native drill-down | Supported at `a1c5931`? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Imported Shopify sales | What value of Shopify orders landed in Odoo this period? | `sale.order.amount_total`, `currency_id` joined via `shopify.connector.order.binding.sale_order_id` | binding: `store_id=?`, `sec3_scope_quarantined=False`, `shopify_cancelled_at=False`; order: `state != 'cancel'`, `date_order` in window | SUM | `date_order` (= Shopify `processedAt`) in selected window, user-TZ boundaries | `binding.store_id` | Show `0.00 CUR`; if orders=0 and bridge healthy → region-D/E empty state "No sales in this period" | Card carries completeness dot + caption bound to region G state | **native `sale.order` list** (server-built act_window, the C1 domain verbatim — same model/rules/domain as the aggregate; the binding workspace is NOT the drill-down: its rules are connector rules, §6.1) | **Yes** (data); endpoint = slice 1 |
| C2 | Imported orders | How many Shopify orders were imported for the period? | `shopify.connector.order.binding` (+ joined order state) | as C1 | COUNT | as C1 | as C1 | `0` | as C1 | as C1 | **Yes**; endpoint = slice 1 |
| C3 | Average imported order value | Typical imported order size? | derived C1/C2 | as C1 | SUM/COUNT | as C1 | as C1 | `—` when C2=0 (never divide by zero) | as C1 | as C1 | **Yes** (derived) |
| C4 | Units sold (imported) | How many product units were sold? | `sale.order.line.product_uom_qty`, filter `shopify_line_item_gid != False` | goods lines ∩ order-projection terms, C1 exclusions | SUM | as C1 | via order projection | `0` | as C1 | **native `sale.order.line` list**, identical domain (same model/rules as the aggregate — §6.1 ruling B) | **Yes**; endpoint = slice 1 |
| C∆ | "vs previous period" delta on C1/C2/C3/C4 | Better or worse than the preceding equivalent period? | same as each card | same, window shifted back by its own length | same | previous equivalent window | same | When previous value is 0 → "no prior-period data", never a % | inherits card state | n/a (caption) | **Yes** (derived) |
| D1 | Sales trend (bars + previous-period line) | How did imported sales move across the period? | as C1 | as C1 | SUM per bucket (day; hour for 24 h) | buckets in user TZ, stated on chart caption | as C1 | Honest empty state (one of the three §9.4 variants) | chart caption inherits G | table rows link to the **native `sale.order` list**, day-filtered with the same domain (§6.1) | **Yes**; endpoint = slice 1 |
| E1 | Top products (≤5) | Which products drove imported sales? | `sale.order.line`: `product_id`, `product_uom_qty`, `price_subtotal` (untaxed) | as C4 | GROUP BY product, SUM value+units, ORDER value DESC LIMIT 5 | as C1 | via order projection | Section hidden behind "No product sales in this period" line | inherits G | Product form (`product.template`, navigation) + **native `sale.order.line` list** with the E1 domain (server-built, slice 2) — count-exact on the same model (§6.1 ruling B) | **Yes** (display); drill-down exactness = slice 2 |
| E2 | **Share of goods subtotal** (per top product) | How concentrated were product sales? | derived: E1 `price_subtotal` value ÷ SUM `price_subtotal` over **all** eligible goods lines (the C4 population) | as E1; denominator = the same eligible goods-line basis as the numerator — **never** C1 (C1 includes tax + shipping; this ratio must not imply it divides the headline) | ratio | as C1 | as C1 | Hidden when denominator 0 | inherits G | n/a (cell; the goods-subtotal basis is printed under the table) | **Yes** (derived; same-basis numerator/denominator, correction §6C) |
| G1 | Sales data synchronized through | Up to when has Shopify order discovery landed? | `shopify.connector.store.order_sync_last_checkpoint_at` (compute over `settings.sale_order_last_import_checkpoint_at`, `shopify_connector_sale/models/shopify_connector_order_scan.py:566`) | store row | latest value | point-in-time | per store | "Not synchronized yet" empty variant | drives the G state machine (§9.3) | Store form | **Yes** |
| G2 | Orders awaiting import | How many discovered orders haven't landed? | `shopify.connector.job` | `job_type='order_import_sync'`, `state in (draft,queued,running,retry_waiting)`, `store_id=?` | COUNT | point-in-time | `job.store_id` | `0` → contributes to "Complete & current" | n/a (is itself the freshness signal) | Sync Center `action_shopify_connector_sync_center` + domain | **Yes** |
| G3 | Order imports needing attention | Is commercial completeness blocked on a human/failure? | `shopify.connector.job` | `job_type in (order_import_scan, order_import_sync)`, `state in (failed_retryable, failed_final, blocked_manual_review)` | COUNT | point-in-time | `job.store_id` | `0` | n/a | Error & Review Center `action_shopify_connector_error_center` + domain | **Yes** |
| F1 | Overall connector state (lead line) | Is anything wrong right now? | derived from F/G counters — same severity model as today (`_derive_state`, ui_dashboard.py:148) | see F2–F5 | derivation | point-in-time | selected store scope | "empty" first-run state | n/a | n/a | **Yes** (existing model, + store param = slice 1) |
| F2 | Active backlog | How much work is in flight? | `shopify.connector.job` | `state in (queued, running, retry_waiting)` (+ store) | COUNT | point-in-time | `job.store_id` | `0` | n/a | Sync Center + domain | **Yes** |
| F3 | Oldest waiting item | Is the queue moving? | `shopify.connector.job.create_date` | `state in (queued, retry_waiting)` (+ store) | MIN via `search(..., order='create_date asc', limit=1)` | point-in-time, shown as age | `job.store_id` | "—" when no waiting work | n/a | that job's form | **Yes** (no dedicated enqueued-at field; `create_date` is the documented proxy) |
| F4 | Needs review | What waits on a human? | jobs `blocked_manual_review` + uncertain attempts (`observed_outcome='uncertain'`, `resolution_disposition=False`) + match decisions `state='pending'` + gateway approvals `manual_gateway_approval_state='pending'` | each with store term | SUM of 4 COUNTs, decomposed in tooltip/attention items | point-in-time | native `store_id` on each model | `0` | n/a | each component its own action (Error Center / Mutation Evidence / Match Decisions / Orders Workspace filtered) | **Yes** |
| F5 | Final failures | What stopped permanently? | `shopify.connector.job` | `state='failed_final'` (+ store) | COUNT | point-in-time | `job.store_id` | `0` | n/a | Error & Review Center + domain | **Yes** |
| F6 | Flow row × 5: state · last success · backlog · failures | Which flow is delayed or failing? | jobs by flow `job_type` families — Orders: `order_import_scan, order_import_sync, customer_import_sync`; Catalog: `product_import_scan, product_import_sync`; Inventory: `inventory_push_sync, inventory_push_scan, inventory_first_push_preview, inventory_location_sync, inventory_activate, inventory_set_quantities, inventory_mutation_reconcile`; Export: the 14 `product_export_*` types; Fulfillment: the 10 `fulfillment_*` types. Last-success anchors: G1 / `settings.product_last_import_success_at` / `settings.inventory_last_push_scan_at` / latest preview `applied_at` / `settings.fulfillment_last_reconciliation_at` | backlog: `state in (queued,running,retry_waiting)` per family; failures: `state in (failed_retryable,failed_final,blocked_manual_review)` per family | COUNT per family (2 read_group calls grouped by `job_type`, mapped to families — constant queries) | point-in-time; last-success = stored watermark | `job.store_id` / settings per store | Flow row renders "No activity yet" | last-success age drives row tone | Sync Center / Error Center with the family `job_type in (...)` domain | **Yes** |
| F7 | Needs attention (≤3 items) | What exactly do I act on first? | existing exception builder (ui_dashboard.py:230-317) + two new sources: pending match decisions (`action_shopify_connector_product_match_decision`), orders awaiting configuration (existing action `action_shopify_connector_orders_awaiting_configuration`) | per candidate; count MUST equal its target domain count (existing test invariant) | COUNT per candidate, ranked danger-first | point-in-time | per candidate store term | Section replaced by single affirmative line | n/a | each item's `target` (res_model + domain + name) | **Yes** |
| F8 | Recent activity (≤8) | What happened just now? | `shopify.connector.job`: `state, job_type, job_source, store_id, finished_at` | `state in (succeeded, failed_final, skipped, cancelled)` (+ store) | `search_read` limit 8, `finished_at desc` | latest 8 | `job.store_id` | "No sync activity yet." | n/a | job form | **Yes** (existing) |
| F9 | Last-7-days counters (text line) | Rough weekly pulse? | jobs `finished_at` in last 7 days | `state='succeeded'` / `state in (failed_final,failed_retryable)` | 2 COUNTs | rolling 7 days | `job.store_id` | Line hidden with <1 day of history | n/a | Sync Center | **Yes** (replaces sparkline queries) |
| F10 | Quiet metadata: API health · next scheduled posture | Anything throttled? Is automation on? | `store.api_health_state (normal/throttled/degraded)`, `api_throttle_observed_at`; `order_sync_scheduled` etc. (cron-verified computes) | store row | latest values | point-in-time | per store | omitted when normal | n/a | Store form | **Yes** ("next scheduled check" timestamp itself = deferred, §8: reading `ir.cron.nextcall` needs a deliberate, security-reviewed sudo read) |
| H1 | Multi-store table | Which store needs me? | per-store: `store.state`, latest terminal `finished_at`, F2/F4+F5 counts, C1 per store currency | grouped by `store_id` (single `read_group` per measure — no N+1) | per-store COUNT/SUM/MAX | point-in-time + selected window for sales | inherent | Region hidden when ≤1 store | sales cell inherits per-store G | Store form; counts → Sync/Error Center store-filtered | **Yes**; endpoint = slice 1 |
| B1 | Critical status band | Does a connector problem make the money numbers wrong? | derived: G state ∈ {Stale, Incomplete} or store `reconnect_needed/disconnected` or sale domain disabled with history present | §9.3 conditions | boolean + worst cause | point-in-time | selected store | absent when conditions false | is itself the stale surface | cause-specific action (Error Center / Store form) | **Yes** (derived) |
| L1 | Payment strip: Paid · Authorized — capture pending · Payment pending (non-COD) · COD · needs review | Which imported orders are actually paid? | `binding.shopify_financial_status_snapshot` (raw), `is_cod`, `binding.status` — counted over the C1 population (imported orders only, caption says so) | C1 exclusions + snapshot buckets: `PAID` / `AUTHORIZED` / `PENDING & is_cod=False` / `is_cod=True` / `status='review'` (payment-caused review incl. PARTIALLY_PAID-as-quotation imports and post-import divergence) | COUNT per bucket | as C1 | as C1 | Strip hidden when C2=0 | caption shows oldest evidence-refresh mirror in the set | **native `sale.order` list** on the lifecycle mirror fields, same bucket domain (§6.1 slice 1b; source fields live on the binding, so this row is served by the lifecycle projection — descoping 1b makes it an unresolved slice-1 prerequisite, never "as C1" by silent analogy) | **Yes** (fields stored on the binding; the sale-order mirror is the slice-1b projection) |
| L2 | Payment-evidence freshness caption | How fresh is the payment evidence? | `shopify_connector_evidence_refreshed_at` (slice-1b mirror of `binding.shopify_last_evidence_refresh_at`) | C1 population | MIN (oldest) | point-in-time | as C1 | omitted when C2=0 | is itself the freshness surface | **native `sale.order` list** ordered by the mirror field (§6.1) | **Yes** (binding field stored; sale-order mirror = slice 1b) |
| L3 | COD block: awaiting approval / quotation / confirmed; collection nothing / partially / fully | Where does each COD order stand commercially? | `manual_gateway_approval_state`, `cod_commercial_state`, `cod_collection_state` | `is_cod=True` + C1 exclusions; approval='pending' / commercial ∈ (quotation, confirmed) / collection ∈ (nothing_collected, partially_collected, fully_collected) | COUNT per state | as C1 | as C1 | Block hidden when COD count = 0 | inherits L2 | **native `sale.order` list** on the lifecycle mirror fields (§6.1 slice 1b); the binding approval queue stays reachable from each order, but the count's drill-down is the same-model sale-order list | **Yes** (states written at import/refresh/approval — importer:2241-2247, 2290-2296, 2361-2384; sale-order mirrors = slice 1b) |
| L4 | Order fulfillment progress: Fulfilled · Partially fulfilled · Unfulfilled | How far along is Shopify order fulfillment? | `binding.shopify_fulfillment_status_snapshot` (raw `displayFulfillmentStatus` — Shopify's own order-level rollup, so multi-fulfillment orders are never double-counted) | C1 population; raw-value buckets, any other/NULL value shown as "Not yet observed" | COUNT per bucket | as C1 | as C1 | hidden when C2=0 | caption: snapshot refreshed at import + evidence refresh (mirror timestamp) — **not** a live carrier feed | **native `sale.order` list** on the fulfillment-status mirror, same bucket domain (§6.1 slice 1b) | **Yes** (display-only snapshot with stated freshness; sale-order mirror = slice 1b) |
| L5 | Odoo dispatch: to dispatch / ready / dispatched | What does the warehouse still owe? | native `stock.picking.state` for outgoing pickings of bound orders (`sale_id` join — the same join production uses, fulfillment_inbound.py:87-89) | pickings of bound-store orders: `state not in (done, cancel)` = to dispatch; `state='assigned'` = ready; `state='done'` = dispatched | COUNT | as C1 | via order projection (data relationship, **not** a sale-rule claim) | `0` | n/a (Odoo-side truth) | native Delivery Orders (`stock.picking`) list, identical domain — exact on its own model | **Yes** — defined as the **rule-visible warehouse population** (ruling D): `stock.picking` ACLs/rules govern this number and they do not equal sale-order rules; the block label states this |
| L6 | Oldest paid-unfulfilled age | Is anything paid but sitting? | derived: MIN `date_order` where the financial mirror is `PAID` + the fulfillment mirror is `UNFULFILLED` (slice-1b fields) | C1 exclusions | MIN age | as C1 | as C1 | omitted when none | elapsed age only — **no SLA claimed** (correction §E: no invented threshold; age is displayed, lateness is not declared) | **native `sale.order` list**, same domain, oldest first (§6.1) | **Yes** (derived; mirrors = slice 1b) |
| L7 | Lifecycle exceptions (≤3): COD awaiting approval · external fulfillment recorded in Shopify · payment status changed after import · Shopify cancelled a validated fulfillment · fulfilled while payment still pending · unknown fulfillment status observed | What lifecycle event needs a human? | approvals `manual_gateway_approval_state='pending'`; evidence `reconciled_state='review'` with `review_reason ∈ (external_fulfillment_observed, origin_unconfirmed)`; binding `status='review'` + `financial_status_changed_at` + previous≠current snapshot; evidence `review_reason='cancelled_after_validation'`; derived snapshot pair (`displayFulfillmentStatus ∈ (FULFILLED, PARTIALLY_FULFILLED)` + financial `PENDING/AUTHORIZED` + `is_cod=False`); evidence `schema_warning=True` | per candidate, store term, count = drill-down domain count (existing invariant) | COUNT per candidate, ranked | point-in-time | native store term on each model | section replaced by one affirmative line | each item names its evidence timestamp (`last_observed_at` / `financial_status_changed_at`) | binding list / fulfillment review list (`action` per source) with the same domain | **Yes** — every named source has a production writer at `a1c5931` (§5); each item states what/why/who/freshness/whether the connector can resolve it (report-only for external events) |

**Rejected at the gate** (must not appear; recorded per prompt §10 and
correction addendum §C/§D): refunds / returned value (no refund records
exist anywhere — §8.1), "Net sales" (label unreproducible — §7.1),
success-rate percentage for flows (denominator ambiguity between scans/syncs
within a family made the number misleading; replaced by absolute
backlog+failure counts, which drill down exactly), "next scheduled check"
clock time (needs `ir.cron` sudo read — deferred),
delivered-inconsistency fulfillment counter (field exists but **no code ever
writes it** — would always read 0), **Delivered / Not delivered / In transit
/ carrier-progress counts** (A5 FulfillmentEvents never queried; no rollup
writer; §7.5 ruling — "not delivered" must never be shown for merely
unfulfilled orders), **COD dispatched/delivered lifecycle**
(`cod_fulfillment_state` exposes only `not_dispatched`; no writer beyond
it), **COD collection discrepancy counter** (`discrepancy` selection value
has no production writer), **COD monetary aggregates** (all five
`cod_*_value_amount` snapshots are `Char`; refunded/cancelled/fulfilled are
literal `'0'` — never aggregable, never summed), **general payment-gateway
dimension** (only unambiguous manual gateway names are persisted
(`manual_gateway_name`); non-manual gateway names are not stored as a
reporting dimension), **exact historical-coverage boundary** ("orders
before *date* were not imported" — no authoritative stored boundary exists;
the earliest imported order proves nothing about coverage — §9.4).

## 7. Commercial metric truth rules

### 7.1 The label

The headline is **"Imported Shopify sales"** — never "Net sales", never
"Revenue". Definition line rendered on the card (and as tooltip):

> Total value, including taxes and shipping, of Shopify orders imported into
> Odoo for this store and period. Excludes orders cancelled on Shopify or in
> Odoo. Not Shopify Analytics "net sales": refunds, returns and post-import
> edits are not imported.

Basis, per the correction's §3 checklist:

| Rule | Definition (all `[Fact]`-backed, §5 citations) |
| --- | --- |
| Source | `sale.order.amount_total` via binding join; totals verified against Shopify money evidence at import by the bounded solver |
| Store isolation | `binding.store_id`; sales never counted without a binding |
| Company isolation | explicit company domain + record rules; no `sudo()` |
| Included states | every imported (bound) order, draft or confirmed — confirmation policy (`paid_only` etc.) decides Odoo state, not commercial existence |
| Excluded | Odoo `state='cancel'`; `binding.shopify_cancelled_at` set (cancelled on Shopify after import — excluded and disclosed in G); quarantined bindings |
| Cancelled / test orders | pre-cancelled and (by default) test orders never imported. **Dynamic disclosure (correction §6B):** the dashboard renders an accessible caption bound to `shopify.connector.store.settings.order_import_include_test` — off: "Shopify test orders excluded"; on: "Includes Shopify test orders" (multi-store scope: names the stores where it is on). The aggregate and its drill-down use the same rule by construction — the setting acts at scan (`test:false`) and import time, so imported test orders are ordinary bindings in both |
| Discounts | line-level discounts are inside `amount_total` (converted to line discount % at import; residual as a negative adjustment line) |
| Taxes / shipping / duties / fees | taxes+shipping included (stated on the card); duties/tips/fees orders are never imported at all |
| Refunds / returns / edits | never imported; REFUNDED/VOIDED/EXPIRED never imported; PARTIALLY_REFUNDED blocked at review; post-import refresh never changes amounts — hence no reversal treatment exists to display |
| Sale date | `date_order` = Shopify `processedAt` (fallback `createdAt`) |
| Reversal date | n/a (no reversals imported) |
| Period boundary & TZ | window and buckets in the requesting user's Odoo timezone, stated in the chart caption; deviation from Shopify's shop-timezone reporting disclosed in the definition |
| Previous period | same length, immediately preceding, same TZ rules |
| Currency | one currency per store (enforced at import); cross-currency totals never combined |
| Incomplete import | never silently ignored — region G states it and region B escalates it (§9.3) |
| Drill-down domain | the C1 domain verbatim on the **native `sale.order` list** (same model, same rules, same domain — §6.1) |

### 7.2 Commercial metric decision table

| Proposed metric | Decision | Reason (evidence §5) |
| --- | --- | --- |
| Sales value | **Include with truthful renamed label** — "Imported Shopify sales" | Value is exact for imported orders (solver guarantee); "Net sales" would overclaim (no refunds/edits) |
| Shopify order count | **Include now** — "Imported orders" | Binding count is exact |
| Average order value | **Include now** | Derived; `—` at zero orders |
| Units sold | **Include now** | Gid-filtered goods lines are exact; shipping/discount lines structurally excluded |
| Period comparison | **Include now** | Same definitions, shifted window; "no prior-period data" instead of % against zero |
| Sales trend (one chart) | **Include now** | Same domain, bucketed |
| Top products (≤5) | **Include now** | Line aggregation exact; drill-down exactness note in slice 2 |
| Sales-data freshness / completeness | **Include now** | Stored checkpoint + job counts |
| Refunds / returned value | **Defer** | No refund/credit-note records exist anywhere in the connector; `cod_refunded_value_amount` is a dead `'0'` Char. Displaying anything would be fiction |
| "Net sales" (Shopify definition) | **Requires backend enhancement** | Needs refund + order-edit import (a product-scope decision, not a dashboard change) |
| Taxes / shipping decomposition | **Defer** (to native Shopify Sales Analysis report, slice 3) | Data exists (`amount_tax`; `SHOPIFY-SHIPPING` lines) but KPI-strip restraint wins; report is the right surface |
| Discount value given | **Defer** (same report) | Reconstructable from goods lines (`price_unit·qty − price_subtotal`); not a headline |
| Cross-currency combined totals | **Requires backend enhancement** | Needs an approved conversion method; until then per-store only (H) |
| Payment-status distribution (imported orders) | **Include now** | Raw snapshot buckets over stored fields; fail-closed upstream; L1 |
| COD approval / commercial / collection counts | **Include now** | All three state machines have production writers (L3) |
| COD amount reporting (order/collected/outstanding value) | **Requires backend enhancement** | The five `cod_*_value_amount` snapshots are `Char` and three are literal `'0'`; needs protected currency-aware numeric fields + migration/backfill + reconciliation tests — never aggregate the Char snapshots |
| COD dispatched / delivered lifecycle | **Requires backend enhancement (lifecycle writer)** | `cod_fulfillment_state` exposes only `not_dispatched`; no writer beyond it — no dispatch/delivery stage may be invented from it |
| COD collection discrepancy alert | **Requires backend enhancement (lifecycle writer)** | `discrepancy` selection value has no production writer at `a1c5931` |
| Order fulfillment progress (Fulfilled / Partially / Unfulfilled) | **Include with truthful freshness caption** | Stored order-level snapshot (Shopify's own rollup); refreshed at import + evidence refresh, stated on the strip (L4) |
| Odoo dispatch states | **Include now** | Native `stock.picking` truth; caller's ACLs apply (L5) |
| Carrier delivery (Delivered / In transit / Not delivered / attempted / delayed) | **Requires backend enhancement** | A5 FulfillmentEvents never queried; `delivered_inconsistency` and `delivered_not_validated` never written; no rollup, no freshness contract — §7.5 ruling |
| General payment-gateway dimension | **Defer** | Non-manual gateway names are not persisted as a reporting dimension; only unambiguous manual gateway identity is stored |

### 7.3 Payment-status support matrix (correction addendum §B)

`[Fact]` Shopify's `OrderDisplayFinancialStatus` enum (all 8 values verified
at https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderDisplayFinancialStatus,
accessed 2026-08-01, Accessible) mapped against the exact-head import policy
(`shopify_connector_order_importer.py`). **Counts on the dashboard are counts
of imported Odoo orders — never the entire Shopify order population.**
Skipped states are never rendered as zeros implying store-wide coverage; the
region caption states the population, and the job-side complement (waiting /
skipped / failed imports) lives in regions G and F.

| Shopify value | Policy at `a1c5931` (citation) | Can exist on an imported binding? | Store 360 treatment |
| --- | --- | --- | --- |
| `PAID` | Imported; confirmed under `paid_only` / `paid_or_authorized` (importer:2194-2197) | Yes | Bucket **Paid** |
| `AUTHORIZED` | Imported; confirmed only under `paid_or_authorized`, else quotation (2198-2199); refresh auto-confirms draft on →PAID transition (2386-2399) | Yes | Bucket **Authorized — capture pending** |
| `PENDING` (unambiguous approved manual gateway) | Imported as COD (`is_cod=True`, 2200-2229); approval per `manual_gateway_policy` | Yes | **COD** block (L3) |
| `PENDING` (non-manual / unapproved) | Not imported while waiting: job `retry_waiting` recheck loop until `pending_wait_expiry`, then **skipped** `payment_pending_expired` (2218-2221, 2745-2773). Under `quotations_only`: imported as quotation | Only under `quotations_only` | Bucket **Payment pending — non-COD** (exists only under that policy; otherwise visible as waiting/skipped jobs in G/F, not as orders) |
| `PARTIALLY_PAID` | Fails to review unless `quotations_only`; then imported with binding `status='review'` (importer:699-707, 2187-2192) | Only under `quotations_only`, as review | Bucket **Partially paid / needs review** |
| `PARTIALLY_REFUNDED` | Never imported (`financial_total_mismatch` review, importer:694-698); post-import transition routes binding to review | Post-import only (as review + previous snapshot) | Lifecycle exception **payment status changed after import** |
| `REFUNDED` / `VOIDED` / `EXPIRED` | Skipped (`unsupported_financial_state`, importer:687-693); approval path also rejects reversed evidence (order_binding.py:232-237) | No (post-import transition → review) | Never a bucket; post-import transitions surface as the change exception |
| Unknown future value | **Fail closed** at import and refresh (`data_shape_schema_mismatch`, importer:676-686, 828-842); raw value preserved in the job evidence | No | Job-side failure in G3/F5 — an imported binding can never carry an unknown value, so no "unknown" bucket can silently absorb orders |

Freshness: every bucket caption carries the oldest
`shopify_last_evidence_refresh_at` in the displayed set; a status change is
timestamped (`financial_status_changed_at`) with its trigger source. Every
count opens the exact native record set with the same domain.

### 7.4 Payment-method / COD support matrix (correction addendum §C)

`[Fact]` COD classification is **never inferred from `PENDING` alone**: it
requires `manual_gateway_evidence_state='unambiguous'` **and** the gateway
name in the store's approved list (importer:2200-2229; transaction
classifier 2137-2176 marks mixed names/malformed evidence as `mixed`).

| Desired metric / state | Classification | Evidence |
| --- | --- | --- |
| Unambiguous approved COD identity (`is_cod`, `manual_gateway_name`) | **Truthful with current fields** | Written at import; protected binding fields |
| Mixed / ambiguous gateway evidence | **Truthful** (`manual_gateway_evidence_state='mixed'` → binding review; never COD, never paid) | importer:2164-2175, 2336-2340 |
| COD awaiting approval / quotation / confirmed | **Truthful** (`manual_gateway_approval_state`, `cod_commercial_state`; approval action gated Reviewer/Admin with reason + company + draft + evidence checks) | order_binding.py:175-260; importer:2361-2384 |
| COD collection: nothing / partially / fully collected | **Truthful** (computed from manual SUCCESS transactions at import/refresh) | importer:2240-2247 |
| COD collection discrepancy | **Requires a lifecycle writer** — selection value never written | grep evidence, §5 |
| COD dispatched / delivered | **Requires a lifecycle writer** — `cod_fulfillment_state` = `not_dispatched` only, written as a literal (importer:2295) | §5 |
| COD amounts (order / collected / outstanding value) | **Requires a stored numeric/reporting projection** — `Char` snapshots must never be aggregated; needs currency-aware numeric fields, migration/backfill, reconciliation tests | order_binding.py:107-111 |
| General online-gateway reporting dimension | **Deferred** — non-manual gateway names not persisted | §5 |

### 7.5 Fulfillment ≠ dispatch ≠ delivery (semantic ruling, addendum §D)

Three concepts are kept separate and labelled so they cannot be confused:

1. **Order fulfillment** (Shopify): Unfulfilled / Partially fulfilled /
   Fulfilled — from the stored order-level `displayFulfillmentStatus`
   snapshot (Shopify's own rollup across multiple fulfillments, so one order
   is counted once regardless of how many fulfillments/locations it spans).
2. **Warehouse dispatch** (Odoo): native `stock.picking` states (to
   dispatch / ready / dispatched-validated), including partial/backorder
   chains as separate pickings.
3. **Carrier delivery** (parcel reached the customer): **not shown at this
   head.** `[Fact]` Neither `stock.picking.state='done'`, nor Shopify
   `Fulfillment.status='SUCCESS'` (A4), nor `displayFulfillmentStatus='FULFILLED'`
   proves customer delivery — Shopify models delivery as
   `FulfillmentDisplayStatus`/`FulfillmentEventStatus` values (`DELIVERED`,
   `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `ATTEMPTED_DELIVERY`, `FAILURE`, …;
   https://shopify.dev/docs/api/admin-graphql/latest/enums/FulfillmentDisplayStatus,
   https://shopify.dev/docs/api/admin-graphql/latest/enums/FulfillmentEventStatus,
   https://shopify.dev/docs/api/admin-graphql/latest/enums/FulfillmentStatus,
   all accessed 2026-08-01, Accessible). The addendum's seven proof
   conditions fail at `a1c5931`: A5 events are never queried (readers fetch
   `status`/`displayStatus`/`trackingInfo` only), no refresh path is
   dedicated to delivery milestones, external-fulfillment coverage depends
   on scan observation, no stale-display contract exists, no multi-fulfillment
   delivery rollup exists, and `delivered_inconsistency` /
   `delivered_not_validated` are never written. **Ruling: customer-delivery
   reporting (Delivered / Not delivered) is a backend enhancement** (A5
   FulfillmentEvent ingestion + per-order rollup writer + freshness
   contract + coverage for external fulfillments). Until then the dashboard
   shows only concepts 1 and 2, and "not delivered" wording is banned —
   an unfulfilled or not-yet-shipped order must never be labelled "not
   delivered". `[Fact]` Odoo's own e-commerce flow separates order
   confirmation, delivery-order generation and validation the same way
   (https://www.odoo.com/documentation/19.0/applications/websites/ecommerce/order_handling.html,
   accessed 2026-08-01, Accessible).

## 8. Deferred, with reasons (recorded so they are not forgotten)

1. Customer geography / orders-by-country — no stored country rollup for
   imported orders; would require partner reads that the dashboard's PII
   discipline forbids. `[Open question]` for a native report with proper
   access rules, not a dashboard card.
2. Customer segmentation, new-vs-returning, returning-customer rate, CLV —
   customer bindings exist but no order↔customer commercial rollup; PII
   discipline; defer.
3. Channel attribution — the importer's GraphQL query never fetches channel
   (`shopify_connector_order_importer.py:59-149`); cannot exist truthfully.
4. Conversion rate, traffic, sessions, ROAS — not in Odoo at all; belongs to
   Shopify Analytics.
5. Profit / gross margin — needs cost data + accounting treatment (Emipro
   gates this behind Enterprise analytic accounting); out of connector scope.
6. Forecasting / AI recommendations — prompt-rejected; out of scope.
7. Payout / accounting analytics — connector has no payout import.
8. "Next scheduled check" clock time — requires reading `ir.cron.nextcall`
   with elevated rights; a deliberate, security-reviewed backend decision.
   The dashboard shows the *posture* ("Scheduled sync on/off", cron-verified)
   instead, which is stored and readable today.
9. Carrier-delivery reporting (Delivered / Not delivered / In transit /
   attempted / delayed) — backend enhancement per the §7.5 ruling: A5
   FulfillmentEvent ingestion, a per-order delivery rollup writer with
   observation timestamps and staleness display, and coverage for
   externally-created fulfillments.
10. COD monetary reporting — backend enhancement: protected currency-aware
    numeric fields (never the `Char` snapshots), migration/backfill for
    existing bindings, reconciliation tests against the totals solver.
11. COD dispatch/delivery lifecycle and collection-discrepancy detection —
    backend enhancement: lifecycle writers for `cod_fulfillment_state`
    (today a `not_dispatched` literal) and `cod_collection_state='discrepancy'`
    (today never assigned).
12. Exact historical-coverage boundary ("orders before *date* were not
    imported") — unsupported at `a1c5931`: no authoritative stored boundary
    exists, and the earliest imported order proves nothing (the store may
    simply have had no earlier orders). Backend enhancement if wanted: a
    per-store stored coverage-boundary field/event written at scan time from
    the actually-used window start (`order_import_window`, plus Shopify's
    60-day default order access without `read_all_orders` —
    store_settings.py:184-198). Until then only the cautious §9.4 copy is
    allowed, and no date is ever invented from the first imported order.

## 9. States and behaviour

### 9.1 Refresh contract

Manual Refresh button + auto-refresh ≥30 s, paused in hidden tabs (existing
`PB-12` behaviour, `shopify_connector_dashboard.js:84-134`). The header
separates **page generation time** ("Page updated HH:MM", from `generated_at`)
from **Shopify-source freshness** ("Shopify order data synchronized through
HH:MM", from the applicable completed order checkpoint/evidence timestamp).
Refreshing the page must never advance or visually replace the Shopify-source
timestamp. Nothing is labelled live.

### 9.2 Severity model

Unchanged from U0 (`_derive_state`): `empty / healthy / warning /
manual_review / degraded`; a healthy lead can never coexist with an active
danger/warning item; decision items are distinguished from technical failures
by icon + owner label + wording, never colour alone.

### 9.3 Data-completeness bridge states (region G, drives region B)

**What the bridge measures (correction §6D):** connector **import
completeness and freshness** — whether Shopify order discovery and import
have caught up. It does **not** claim Shopify Analytics parity, and it does
**not** claim refund-adjusted net-sales completeness (refunds/edits are
never imported, so "complete" means "all discoverable importable orders have
landed", nothing more). The bridge caption carries this scope.

| State | Truthful condition |
| --- | --- |
| **Complete & current** | `order_sync_scheduled` true · store connected · G2 = 0 · G3 = 0 · checkpoint age ≤ 45 min (3× the 15-min scan cron) · the last complete order catch-up is stamped for the current `connection_generation`; when fulfillment-derived L4 data is shown, its completed reconciliation generation must also match |
| **Processing** | G3 = 0 and either G2 > 0 or current-generation reconnect catch-up is running — figures may rise shortly; no alarm |
| **Stale** | checkpoint age > 45 min with scheduling on, scheduling off with import history present, or a reconnect succeeded but no complete catch-up is stamped for the current generation |
| **Incomplete — action needed** | G3 > 0, catch-up failed/partially traversed, store `reconnect_needed/disconnected`, or sale domain disabled while other flows run → region B renders the critical band naming the commercial consequence |

The generation-bound completion stamps are a **backend prerequisite** for this
UI contract; checkpoint age alone can never return a reconnected store to
"Complete & current". A failed or partial traversal does not advance the
relevant completion stamp or watermark.

### 9.4 Empty states (three distinguishable variants, correction §7)

1. **No sales in this period** — bridge Complete & current, C2 = 0: calm
   line inside C/D; connector sections render normally.
2. **Sales data not synchronized yet** — sale domain disabled or no
   checkpoint/no bindings: C–E collapse to one guided card ("Order import
   hasn't run for this store — an administrator can enable it in Store
   Settings"), no fake zeros; F renders fully.
3. **Historical coverage uncertain / insufficient permissions** (corrected
   per §6A of the correction — the earlier draft inferred a coverage
   boundary from the earliest imported order, which proves nothing: a store
   may simply have had no earlier orders). Copy is deliberately cautious:
   "**The selected period may include dates earlier than the connector's
   available imported history.** Import coverage is bounded by the store's
   configured import window (currently *N* days); Shopify grants access to
   orders older than 60 days only with the `read_all_orders` scope." Both
   cited facts are stored/policy facts (`order_import_window`,
   `_check_order_window_policy`); **no cutoff date is ever displayed** —
   exact-boundary detection is a recorded backend enhancement (§8.12).
   Separately, when the caller lacks `sale.order` read access: "Your role
   can't read sales amounts — connector health is unaffected", detected by
   catching the ACL refusal server-side. Never rendered as `0.00`.

### 9.5 Disconnect / reconnect source-and-freshness experience

The dashboard reads stored Odoo data; it does not issue live Shopify queries.
The presentation must make that architecture understandable without exposing
implementation jargon:

- **While disconnected:** preserve historical/last-known Shopify-derived
  figures; never replace them with zero. Region B says: "Shopify connection
  unavailable — figures are last known and may be incomplete · synchronized
  through *timestamp*." Odoo-native operational values (for example Delivery
  Order dispatch state and connector job state) may continue changing and are
  labelled as Odoo activity, not Shopify freshness.
- **Immediately after reconnect:** show "Reconciliation in progress" and retain
  the original Shopify synchronization timestamp. A successful connection
  probe or a young pre-disconnect checkpoint is not enough to show green.
- **After complete current-generation catch-up:** advance the relevant Shopify
  source timestamp and allow "Complete & current" only when §9.3 also passes.
- **After partial or failed catch-up:** remain Stale/Incomplete, name the failed
  domain (orders, payment evidence or fulfillment), and provide a direct Review
  route. Never stamp a partial traversal as complete.
- **Source clarity:** commercial KPIs are labelled "Imported Shopify sales
  (stored in Odoo)"; payment/fulfillment strips say "Shopify status observed
  through *timestamp*"; warehouse dispatch says "Odoo delivery status · page
  updated *timestamp*". The page timestamp and every Shopify-source timestamp
  remain visually distinct.
- **Long gaps:** when complete coverage cannot be proven, including a gap beyond
  Shopify's ordinary 60-day order-access window without `read_all_orders`,
  show a visible coverage warning rather than a green/current state.

Acceptance is the live campaign's reconnect source/freshness case
`R-4`: baseline → disconnect → synthetic Shopify order/payment/fulfillment
changes plus an Odoo delivery change → disconnected capture → reconnect capture
before catch-up → terminal catch-up reconciliation → forced partial-failure
capture. Every displayed count must still equal its drill-down population and
no Shopify GID, binding or Odoo order may duplicate.

This requirement is an improvement for the future Store 360 implementation.
It is not a claim that PR #204 already ships Store 360, and its absence is not
retroactively treated as a PR #204 UAT failure.

## 10. Visual direction

- **Tokens verbatim** from `shopify_connector_tokens.scss` (surfaces, text,
  border, semantic tints, spacing 4–64, type scale, radius 8, motion 100–250 ms,
  platform font stack). The prototype re-declares the same custom properties
  under its own root; no new colours except the two chart series (below).
- One card style (8 px radius, 1 px hairline, no resting shadow); typography
  leads (`--sc-fs-dominant` for KPI values with `font-variant-numeric:
  tabular-nums`); colour is reserved for semantic status; no gradients as
  decoration, no glassmorphism, no hero areas, no meaning-bearing animation.
- CSS logical properties only (`margin-inline`, `padding-block`,
  `inset-inline-start`, `border-inline-start`, `text-align: start`) — RTL
  mirrors without directional overrides; the root binds `dir` from the
  locale, exactly as the shipped dashboard does after the U2 RTL correction.
- Icons: inline SVG strokes drawn for the prototype (no external icon font
  can be loaded in a self-contained file); production uses the same
  Odoo-provided FontAwesome glyphs the current dashboard uses.
- Chart palette (dataviz-validated 2026-08-01): current-period bars
  `#175CD3` (the token accent; passes lightness band, CVD separation, ≥3:1
  contrast on white); previous-period line `#667085` — a **deliberate neutral
  reference series**, not a co-equal category: the validator flags its chroma
  below the categorical floor, which is the intended recessive treatment, and
  the pair's tritan ΔE (6.9) sits in the band that is legal only with
  secondary encoding — provided here by the dashed stroke, the legend, and
  the full table equivalent. Success/failure texture conventions from the
  existing sparkline (diagonal stripes for failure) are retained for any
  future operational bars; the single Store 360 chart carries none because it
  encodes value, not status.
- Focus: 2 px solid `--sc-focus` outline, 2 px offset, on every operable
  element (`:focus-visible`), matching the shipped stylesheet.
- Reduced motion: all transitions collapse under
  `prefers-reduced-motion: reduce`; no animation carries meaning anywhere.

## 11. Responsive presentation

- **Desktop (≥1024 px):** header · (B) · KPI row (4 cards) with the bridge
  line directly beneath · D and E side by side (trend ~2/3, top products
  ~1/3) · F · H. Max content width 1180 px.
- **Tablet (768 px):** KPI cards 2×2; D above E full-width; F counters wrap
  2×2; flow rows become stacked cards.
- **Mobile (390 px, and reflow down to 320 px):** sections stack in decision
  order A→B→C→G→D→E→L→F→H; KPI cards full-width (no horizontal card
  scrolling); the freshness/completeness line stays adjacent to the sales
  cards; every drill-down remains reachable. **Multi-store presentation
  (correction §8B): at ≤640 px the Stores table becomes stacked store cards**
  — each store's connection state, backlog, attention, sales and the primary
  **Open** action are fully visible without any horizontal scrolling; a
  primary operational action is never hidden off-screen. Secondary tabular
  detail (top products, chart equivalent) may still scroll inside its own
  sanctioned `overflow-x: auto` container — the page itself never scrolls
  horizontally, at 390 px, at 320 px, and at 200 % zoom (683 px effective).
  **Mobile chart legibility (correction §8C, tightened in the final
  tail):** the effective rendered axis-label size stays **≥11 px at
  390 px** — implemented by raising the narrow-width SVG label type (the
  SVG scales with its viewBox, so the stylesheet compensates below
  640 px) and measured after rendering, not assumed; the legend wraps and
  the final incomplete-period hatching stays visible. At 320 px the
  requirement is reflow (no page overflow, no clipping) and the measured
  effective size is recorded honestly in §13; the accessible table
  equivalent is always available. Seven daily buckets need no label
  thinning; the production 30-day view may thin alternate labels.
  **Exception actions on mobile (final tail):** at ≤640 px every
  exception's Review action wraps to its own row beneath the content —
  the button, its label, icon and focus outline are fully inside the card
  and viewport, never overlapping the explanatory text (measured at the
  descendant level, §13).
- Healthy screens are commercially useful (sales content fills them);
  attention screens state explicitly whether the connector problem affects
  the displayed sales figures (region B copy + card completeness dots).

## 12. Prototype

`prototypes/shopify-operations-360-dashboard.html` + adjacent
`shopify-operations-360-dashboard.css`:

- Self-contained except the one adjacent stylesheet; no network requests, no
  external assets/fonts/CDNs/chart libraries; sanitized static demonstration
  data only; permanently labelled **"DESIGN PROTOTYPE — NOT LIVE DATA"**.
- Four states (healthy / attention / attention-rtl / empty variants),
  switched by a small deterministic inline script (state toggles set
  `data-state`/`dir`; no timers, no fetch, no randomness). The switcher is
  prototype chrome only and is excluded from the design surface.
- **RTL state (correction §8A):** `#attention-rtl` is a representative
  **Arabic-language** rendering of the attention state (same fixture
  numbers), not merely mirrored English. Technique recorded: prototype-only
  Modern Standard Arabic strings for all visible labels (production
  translations come from Odoo i18n and are **not** claimed to exist);
  Latin-script identifiers (store domains, SKUs, order names) and composite
  numeric tokens (currency amounts, percentages with sign, timestamps)
  wrapped in `<bdi>` / `dir="ltr"` spans so numbers, currency, percentage
  sign order and arrows read in the intended order under `dir="rtl"`;
  directional arrow glyphs mirror via the existing `[dir="rtl"] .ic--arrow`
  rule; the exception accent border and header geometry mirror via logical
  properties.
- Focus styles are real and demonstrable by keyboard; the attention state is
  understandable with colour removed (icons + kind chips + owner labels +
  wording).
- The attention state demonstrates the Order lifecycle region with a
  truthful COD scenario (fixture reconciliation in §12.1); values that
  would require a backend enhancement are **not rendered as data** — they
  appear only as annotated "requires backend enhancement" markers inside
  the prototype-annotation block, so nothing unsupported reads as a live
  metric.

### 12.1 Fixture arithmetic reconciliation (correction §7)

Every demonstration value is internally consistent with the documented
production formulas. Reconciliation (also machine-checked in the browser
harness — §13):

**Healthy state (store "Aurora Home Goods", EUR):**
- KPIs: €18,432.50 / 214 orders / AOV €86.13 = 18,432.50 ÷ 214 (= 86.133…)
  / 507 units.
- Trend bars sum exactly to €18,432.50 (2,210.40 + 2,725.10 + 2,402.30 +
  3,187.90 + 2,646.00 + 2,913.60 + 2,347.20); daily orders sum to 214;
  previous-period column sums to €16,398.71; delta +12.4 % = 18,432.50 ÷
  16,398.71 − 1 (= 0.12402…).
- Top products: shares are value ÷ €17,290.00 (the goods-subtotal
  denominator printed in the caption, E2 basis): 2,436→14.1 %,
  1,978→11.4 %, 1,634→9.5 %, 1,518→8.8 %, 1,147→6.6 %.
- Health: **"Last 7 days: 1,284 succeeded, 0 failed"** — corrected from the
  earlier fixture's "2 failed": under the documented job-state queries a
  nonzero 7-day failure count implies live `failed_final`/`failed_retryable`
  rows, contradicting "0 final failures / needs review 0 / all clear"; no
  separate stored historical-event source exists at `a1c5931`, so the
  healthy fixture must show 0 (correction §7.1).
- Backlog 3 = Orders 1 + Catalog 0 + Inventory 2 + Export 0 + Fulfillment 0
  — stated on the flow block ("the five flows account for the whole
  backlog"). The Orders backlog job is a scan, so "0 orders awaiting
  import" (G2 counts `order_import_sync` only) stays consistent.
- Lifecycle: payment 205 Paid + 6 Authorized + 3 COD + 0 review = 214;
  COD 3 = 3 confirmed, 0 awaiting approval (anything else would contradict
  "Needs review 0"); collection 2 nothing + 1 fully = 3; fulfillment
  198 + 4 + 12 = 214; 9 deliveries to dispatch (7 ready); oldest
  paid-unfulfilled age 1.2 days (age only).
- Header disclosure: "Shopify test orders excluded" (default).

**Attention state (two stores, both EUR — stated in the Stores caption):**
- KPIs: €24,910.80 / 289 orders / AOV €86.20 (24,910.80 ÷ 289 = 86.196…)
  / 683 units; store rows sum: €18,432.50 (Aurora Home Goods) + €6,478.30
  (Aurora Outlet) = €24,910.80.
- Trend bars sum exactly to €24,910.80 (2,950.10 + 3,630.90 + 3,210.40 +
  4,270.20 + 3,556.80 + 3,925.30 + 3,367.10); daily orders sum to 289;
  previous-period column sums to €23,929.68 (delta +4.1 %); final bucket
  hatched ("may still rise — 12 orders awaiting import" = G2).
- Top products: shares are value ÷ €23,400.00 goods subtotal: 3,248→13.9 %,
  2,623→11.2 %, 2,322→9.9 %, 2,070→8.8 %, 1,480→6.3 %.
- **Backlog 27 = Orders 14 + Catalog 2 + Inventory 9 + Export 0 +
  Fulfillment 1 (= 26) + 1 disclosed connector control job** (connection
  health check — a core `job_type` outside the five flows; the remainder
  is disclosed on the flow block instead of leaving an unexplained
  disagreement, correction §7.2). Store backlog rows 6 + 21 = 27 (store
  rows count every job, including the control job). Bridge "12 orders
  awaiting import" ⊂ Orders-flow backlog 14 (the other 2 are scan/customer
  jobs).
- Needs review 6 = 2 blocked catalog imports (`blocked_manual_review`) +
  2 pending match decisions + 1 uncertain mutation attempt + 1
  manual-gateway (COD) approval — the counter note and the "Waiting on a
  decision" exception (count 6) carry the same decomposition. Lead line
  "9 items need your attention" = needs review 6 + final failures 3. Flow
  failed/blocked cells: Orders 3 (the 3 `failed_final`) + Catalog 2 (the
  blocked imports) = 5. "Last 7 days: 1,231 succeeded, **3** failed" — the
  three final failures, all within the window; blocked/review items are
  not "failed" under the F9 definition. Store attention rows 2 (Aurora
  Home Goods: the 2 match decisions) + 7 (Aurora Outlet: 3 final failures
  + 2 blocked + 1 uncertain + 1 COD approval) = 9. Order bindings in
  `status='review'` are surfaced in the lifecycle region (3), not
  double-counted here.
- Lifecycle: payment 261 Paid + 8 Authorized + 3 Pending non-COD
  (quotations-only policy) + 14 COD + 3 needs review = 289; COD 14 =
  1 awaiting approval + 3 quotations + 10 confirmed; collection 6 nothing
  + 3 partially + 5 fully = 14; fulfillment 240 Fulfilled + 11 Partially +
  38 Unfulfilled = 289; 21 deliveries to dispatch (14 ready); oldest
  paid-unfulfilled age 3.4 days (elapsed age, explicitly "no lateness
  threshold is configured").
- Test-order disclosure demonstrated dynamically: "Includes Shopify test
  orders — Aurora Outlet" (that store's fixture has
  `order_import_include_test` on); the healthy state shows the default
  "Shopify test orders excluded".
- The Arabic `attention-rtl` state renders the same numbers (verified in
  the harness by DOM extraction from both states).

## 13. Prototype verification record (real browser, correction session)

Chromium (Playwright, `/opt/pw-browsers/chromium`), file:// load. The numbers
below are measured DOM facts from the runs that produced the committed
screenshots; screenshots alone are not treated as proof. **This is static
prototype verification only — no Odoo browser test, tour, or production UI
acceptance is claimed.**

Environment: Chromium **141.0.7390.37** (Playwright 1.56.1), viewports at
`deviceScaleFactor: 1`. Each run loaded the committed prototype from disk
with a state hash and verified the state and direction genuinely applied
(`document.body.dataset.state`, computed `direction` on the surface root).
Eleven runs in the correction session (six full-page + two lifecycle
element captures + three check-only: 320 px reflow and 200 % zoom ≙ 683 CSS
px at attention and healthy). **Final-tail re-run (same environment): all
runs repeated as checks after the ≤640 px CSS fixes; only the two mobile
screenshots were regenerated (`attention-mobile-390px.png`,
`attention-cod-lifecycle-mobile-390px.png`) — the CSS deltas affect ≤640 px
only, so the six other committed captures remain those of the correction
run. Tail measurements: keyboard 16–44 real Tabs unchanged; reduced motion
unchanged; 2 × `file://` requests per run unchanged; fixture arithmetic
passes unchanged in healthy, attention and Arabic; the mobile/action/axis
paragraphs below carry the tail's updated numbers.**

| Run | Viewport | State/dir | Page overflow (`scrollWidth` vs `innerWidth`) | Clipped text outside sanctioned containers | Flow drill-downs | Tabs to LAST flow "Open" (real key presses) | Focus | Requests | Fixture arithmetic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `healthy-desktop-1366px.png` | 1366×900 | healthy / ltr | 1366 = 1366 | 0 | 5/5 | 33 | 2 px solid `#175CD3` | 2 × `file://` | **all 8 checks pass** |
| `attention-desktop-1366px.png` | 1366×900 | attention / ltr | 1366 = 1366 | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | **all 12 checks pass** |
| `attention-tablet-768px.png` | 768×1024 | attention / ltr | 768 = 768 | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | — |
| `attention-mobile-390px.png` | 390×844 | attention / ltr | 390 = 390 | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | store cards + chart below |
| `attention-rtl-desktop-1366px.png` | 1366×900 | **attention-rtl / rtl (Arabic)** | 1366 = 1366 | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | **all 12 checks pass on the Arabic DOM** (same numbers as English) |
| `empty-desktop-1366px.png` | 1366×900 | empty / ltr | 1366 = 1366 | 0 | 5/5 | 16 | 2 px solid | 2 × `file://` | — |
| `attention-cod-lifecycle-desktop-1366px.png` (element capture, region L) | 1366×900 | attention / ltr | 1366 = 1366 | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | — |
| `attention-cod-lifecycle-mobile-390px.png` (element capture, region L) | 390×844 | attention / ltr | 390 = 390 | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | — |
| 320 px reflow (check-only) | 320×844 | attention / ltr | **320 = 320** | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | store cards pass |
| 200 % zoom ≙ 683 px (check-only) | 683×450 | attention / ltr | **683 = 683** | 0 | 5/5 | 44 | 2 px solid | 2 × `file://` | — |
| 200 % zoom ≙ 683 px (check-only) | 683×450 | healthy / ltr | 683 = 683 | 0 | 5/5 | 33 | 2 px solid | 2 × `file://` | — |

**Fixture arithmetic reconciliation, machine-checked from the rendered DOM**
(the §12.1 sums, recomputed by the harness from the visible page, not from
the source): trend-table sales/orders sums equal the KPI values (18,432.50 /
214 healthy; 24,910.80 / 289 attention); every top-product share matches the
printed goods-subtotal denominator within rounding (largest deviation
0.05 pp); flow-backlog sum reconciles with the backlog counter (healthy
remainder 0; attention remainder exactly the 1 disclosed control job); lead
"9 items" = needs review 6 + final failures 3; lifecycle payment buckets
(261+8+3+14+3) and fulfillment buckets (240+11+38) each sum to 289 (healthy:
205+6+3+0 and 198+4+12 = 214); COD commercial states (1+3+10) and collection
states (6+3+5) each equal the COD bucket (14); store rows sum to the
combined KPIs (sales 24,910.80; backlog 27; attention 9). The identical
checks pass against the **Arabic** DOM, proving the RTL state renders the
same numbers.

**Mobile presentation (correction §8B/§8C, re-measured after the final
tail):** the Stores region renders as stacked cards; both cards and both
primary **Open** actions lie fully inside the viewport (`left ≥ 0`,
`right ≤ 390`); the stores wrapper has no horizontal scroll
(`scrollWidth ≤ clientWidth`). **Exception-action containment (final tail
§6), measured at the DESCENDANT level:** at both 390 px and 320 px, all
7 visible action cards (the critical band + 3 lifecycle + 3 health
exceptions) pass — the Review button box, each of its label/icon
descendants, **and its focus outline inflated by the real 2 px width +
2 px offset** lie fully inside their card and the viewport, and the button
rectangle intersects no explanatory-text rectangle (the actions wrap to
their own row at ≤640 px). The chart at 390 px: axis labels compute to an
effective **11.4 px** (22 SVG-px × the 332/640 scale — **≥ the 11 px §11
target**), all axis labels lie inside the SVG bounds (no clipping), the
hatched incomplete-period bar is present and visible, and the legend fits
the viewport. At 320 px the gate is reflow — no page overflow, no clipped
text, store cards, exception actions and their focus outlines still fully
contained; the axis size computes to **9.3 px** there (recorded openly; the
≥11 px target is defined at 390 px, and the accessible table equivalent is
always available; the chart causes no overflow at any width).

**RTL language evidence (correction §8A), measured on the Arabic state:**
`document.body.dataset.state = 'attention-rtl'`, surface `direction: rtl`,
content sections carry `lang="ar"`; the exception accent edge computes
`border-right-width: 4px` / `border-left-width: 1px` (mirror of LTR); the
header identity block sits at x≈1087 with controls at x≈93
(`header_mirrored: true`); in the flow rows the name cell lies to the right
of the action cell; directional arrows flip via `[dir="rtl"] .ic--arrow`.
Bidi isolation is real, not asserted: the KPI delta's `<bdi>` yields exactly
`+4.1%` (sign leading the number) inside Arabic copy; Latin identifiers
(store names) render inside `<bdi>`. Sample Arabic label recorded from the
DOM: «مبيعات شوبيفاي المستوردة». The translations are prototype-only
representative strings — production translations come from Odoo i18n and
are not claimed to exist.

**Other measured facts:** every run issued exactly 2 requests (the HTML +
adjacent CSS, both `file://`) — zero network; reduced-motion emulation
collapses every transition to 0.000001 s; each lifecycle and health
exception carries icon + kind chip + owner + freshness text (readable
without colour, DOM-measured); the visible-section inventory differs
materially per state (healthy: commercial + lifecycle + calm health;
attention: critical band + flagged KPIs + lifecycle with exceptions +
degraded health + stores; empty: guided card + annotation + simplified
health, no KPI/bridge/sales/lifecycle regions).

**Prototype workflow walk (addendum §H, performed on the prototype):**
overview → lifecycle status → filtered orders → individual order evidence
is reachable for every lifecycle count (each count has an "Open" control
whose production target is the exact same-domain native list, per §6 L
rows); payment and fulfillment labels use disjoint vocabularies
("Paid/Authorized/Pending/COD/review" vs
"Fulfilled/Partially fulfilled/Unfulfilled" vs "deliveries to dispatch"),
so an order carries both a payment and a fulfillment state simultaneously
without either overwriting the other (fixture: 289 orders distribute
independently across both axes); healthy / processing / attention / stale /
incomplete are demonstrated across the bridge states and the two main
states; no unsupported metric or lifecycle state renders as data anywhere —
the unsupported set appears only inside the dashed "requires backend
enhancement" annotation.

## 14. Workflow-to-UI-to-data traceability matrix (correction addendum §F)

Twelve order-lifecycle workflows traced end to end at exact head `a1c5931`.
Columns: the operator/merchant action and system event; the production entry
point; stored evidence before → after; the expected Store 360 surface and
order-workspace state; drill-down + acting role; the failure/review route;
and known gaps. "OW" = Orders Workspace (binding list/form), "FR" =
Fulfillment Review list — these name the **operator's working surface** in
each workflow, not the dashboard counts' drill-down contract: metric
drill-downs follow §6.1 (aggregate model = rule model = drill-down model;
commercial/lifecycle counts open native `sale.order`/`sale.order.line`
lists, connector-evidence counts open their own connector lists). Every
dashboard count opens a list on its own aggregate model with the identical
domain (count/domain invariant).

| # | Workflow / transition (action → event) | Production entry point | Stored evidence (before → after) | Store 360 surface | OW / workspace state | Drill-down · role | Failure/review route | Gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1a | **Paid online order** — customer pays in Shopify → scan discovers | 15-min cron → `order_import_scan` (order_scan.py; `test:false` unless included; `order_import_window`) | none → scan checkpoint advances; `order_import_sync` job queued | G2 +1 (awaiting import); bridge Processing | not yet visible | Sync Center · Operator | scan failure → job `failed_retryable` → G3/F5 | window-bounded discovery (§8.12) |
| 1b | → import lands | `import_order_sync` (importer; totals solver `_solve_and_assert_totals`) | binding created `status='active'`, snapshot `PAID`, `financial_status_trigger_source='initial_import'`; `sale.order` confirmed under paid policy | C1–C4 +1; L1 Paid +1; bridge toward Complete | OW row Paid/confirmed | OW · Sales/Operator | `financial_total_mismatch` → failed job (G3) — order never half-imports | — |
| 1c | → warehouse dispatches | native picking flow; validation → fulfillment admission → `fulfillment_create` job | picking `assigned→done`; fulfillment binding created (UNIQUE store+picking), `notify_customer_sent` frozen at enqueue | L5 dispatched +1; F fulfillment flow activity | OW order links picking | Delivery Orders · Warehouse | create failure → mutation-attempt evidence; uncertain outcome → F4 | — |
| 1d | → Shopify confirms fulfillment; carrier moves parcel | reconciliation scan refreshes snapshots (`fulfillment_reconciliation` → `_refresh_binding_snapshot`) | `shopify_status_snapshot='SUCCESS'`, `shopify_last_synced_at`; order snapshot `FULFILLED` on next evidence refresh | L4 Fulfilled +1 (freshness caption) | OW fulfilled | FR/OW · Operator | read failure → watermark **not** stamped (fail-closed, scans.py:148-162) | **carrier progress/delivery: not tracked (§7.5)** |
| 2 | **Authorized order** — authorization → import → capture → paid | importer `_confirmation_outcome` (AUTHORIZED); refresh `transition_to_paid` (2386-2399) | snapshot `AUTHORIZED`, quotation (unless `paid_or_authorized`) → on PAID evidence: draft order auto-confirmed, `financial_status_changed_at` + trigger | L1 Authorized → Paid; C unchanged (order already counted) | OW quotation → confirmed | OW · Sales | evidence mismatch at refresh → binding review (L1 review) | capture deadline (EXPIRED) surfaces only as post-import change exception |
| 3 | **Pending non-manual payment** — provider processing | importer `OrderPendingWait` → `retry_waiting` recheck loop (2745-2773) | job `retry_waiting`, `next_retry_at`; **no order, no binding** | G2/F2 backlog (waiting job); never an L1 bucket | not in OW (correct) | Sync Center · Operator | expiry → job **skipped** `payment_pending_expired`; never misclassified COD (`is_cod` needs approved manual gateway) | skipped-after-expiry orders need manual re-import decision (functional gap, register G-F3) |
| 4a | **Unambiguous COD** — order placed with approved manual gateway | importer gateway classifier (2137-2176) + `_confirmation_outcome` PENDING branch | binding `is_cod=True`, `manual_gateway_name`, evidence `unambiguous`; per `manual_gateway_policy`: confirmed / quotation / `approval_state='pending'` | L3 (+F4 when approval pending) | OW COD quotation/confirmed | OW COD filter · Reviewer | mixed evidence → review (wf 6) | — |
| 4b | → reviewer approves | `action_approve_manual_gateway_order` (order_binding.py:175-260: role, reason, company, draft, evidence, reversal checks) → enqueued refresh confirms (importer:2361-2370) | `approved_at/by` stamped → refresh: `approval_state='approved'`, `cod_commercial_state='confirmed'`, order confirmed | F4 −1; L3 confirmed +1 | OW confirmed | OW · Reviewer/Admin | evidence changed since approval → `superseded` + review (2379-2384) | — |
| 4c | → dispatch → collection → delivery | dispatch = wf 1c; collection recomputed at evidence refresh (2240-2247) | `cod_collection_state` nothing→partially→fully (from manual SUCCESS transactions); `cod_fulfillment_state` stays `not_dispatched` (literal) | L3 collection counts; L5 dispatch | OW COD states | OW · Finance | — | **COD dispatch/delivery lifecycle + discrepancy: no writer; COD amounts: Char (§7.4)** |
| 5 | **COD partially → fully collected** | evidence refresh triggers (scan-driven within window, manual refresh, approval refresh) | `cod_collected_value_amount` Char snapshot + `cod_collection_state` transitions | L3 partially→fully | OW collection badge | OW · Finance | discrepancy detection: none (no writer) | refresh cadence bounded by scan window — stale collection evidence possible (register G-T5) |
| 6 | **Mixed/ambiguous gateways** | gateway classifier `mixed` (2164-2175); refresh keeps forcing review (2336-2340) | `manual_gateway_evidence_state='mixed'`, binding `status='review'`, `cod_commercial_state='review'`, `is_cod=False` | L1 needs-review; L7 exception | OW review, reason visible | OW · Reviewer | stays review until human resolution | — |
| 7 | **Partially paid order** | importer:699-707 + 2187-2192 | `quotations_only`: binding review + snapshot `PARTIALLY_PAID`; else failed job `financial_total_mismatch` | L1 Partially-paid/review, or G3 | OW review / not present | OW or Error Center · Reviewer | as stated | — |
| 8 | **Partial fulfillment / backorder** | native backorder picking → second `fulfillment_create` per picking | order snapshot `PARTIALLY_FULFILLED`; second fulfillment binding (one per picking) | L4 Partially fulfilled; L5 split pickings | OW partial | Delivery Orders · Warehouse | quantity mismatch cases → FR named reasons (`quantity_overrun` etc.) | — |
| 9 | **Multiple fulfillments / locations** | one fulfillment per picking; a fulfillment may span >1 FO at one location (`shopify_fulfillment_order_gids` JSON) | N bindings ↔ 1 order binding; order-level rollup = Shopify's own `displayFulfillmentStatus` | L4 counts each **order** once (rollup snapshot — no double-count by construction) | OW one row | OW · Operator | ambiguous mapping → FR `line_mapping_ambiguous`/`picking_ambiguous` | per-fulfillment delivery rollup: n/a until §7.5 enhancement |
| 10 | **External Shopify fulfillment** (merchant/app fulfilled outside Odoo) | inbound observation (`_observe_fulfillment` → `_route_observation`); origin from own-GID ledger | evidence row (A4/A7 raw, origin class); **Mode 1**: `reconciled_state='review'`, reason `external_fulfillment_observed` / `origin_unconfirmed` — zero stock change; **Mode 2** (origin confirmed): 16-condition evaluation → `applied` + `picking._action_done()` or named review reason | L7 external-fulfillment exception; F fulfillment flow | FR case listing reason + evidence | FR · Operator/Warehouse | every non-pass condition = named review reason; unknown A4 value → `schema_warning`, never success | — |
| 11 | **Post-import divergence** (payment change, cancellation, refund) | scan detects `updatedAt` change within window → evidence refresh (`_refresh_existing`) | snapshots updated + previous preserved + `financial_status_changed_at` + trigger source; cancellation: `shopify_cancelled_at` + binding review; **amounts frozen** (lines never touched); validated-fulfillment cancellation → FR `cancelled_after_validation` (scans.py:187-202) | L7 change exception; C1 excludes Shopify-cancelled (disclosed in G); B if material | OW review with before/after | OW/FR · Reviewer | evidence mismatch → review (fail-closed) | refunds are never imported — value impact not quantified (§7.2 defer) |
| 12 | **Stale / unknown evidence** | freshness anchors: `shopify_last_evidence_refresh_at`, `last_observed_at`, flow watermarks (fail-closed stamping) | unknown financial value → import/refresh **fails** (`data_shape_schema_mismatch`); unknown A4 fulfillment value → `schema_warning=True`, preserved raw, never success | L2 freshness caption; bridge Stale; L7 unknown-status exception (schema_warning count) | OW/FR with raw value visible | Error Center/FR · Operator | fail-closed by construction | A7 display values have no known-set normalization (display-only by design) |

**Simultaneous payment × fulfillment states:** the two axes live in
different stored fields (`shopify_financial_status_snapshot` vs
`shopify_fulfillment_status_snapshot` + picking states), so an order is
simultaneously "Authorized" and "Partially fulfilled" without either
overwriting the other — verified in the prototype walk (§13) and required
of the production implementation (handoff test plan).

## 15. Sources

Repository: exact head `a1c593183f6aaa1238e87486ca518717cefc53a9` — files
cited inline (§2, §5, §6). External: the competitor/platform pages listed
with access status and date in the
[benchmark document](../01-research/ui-operations-360-competitor-benchmark-2026-08-01.md);
WCAG 2.2 criteria references as recorded in
`docs/05-qa/ui-u2-validation-results.md` §6 (accessed 2026-07-27).
