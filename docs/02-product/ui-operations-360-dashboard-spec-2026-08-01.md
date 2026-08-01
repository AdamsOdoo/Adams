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

## 3. Information architecture (decision order)

One page, eight regions, in this order. No tabs, no second dashboard.

| # | Region | Contents |
| --- | --- | --- |
| A | **Shared header** | "Shopify Store 360" + subtitle; store selector (only listing real `shopify.connector.store` rows; "All stores" entry only when >1 store); period selector 24 h / 7 d / 30 d; comparison caption "vs previous 7 days"; Refresh button; "Updated HH:MM"; sales-freshness caption ("Sales data synchronized through …" — same source as region G). |
| B | **Critical status** (conditional) | One concise band shown **only** when a connector problem makes commercial figures materially incomplete or stale (§9.3). Names the cause, states the commercial consequence ("figures below may be incomplete"), one Review drill-down. Routine all-clear text never occupies this slot. |
| C | **Store performance** | Four KPI cards (max five allowed; the truthful set is four): Imported Shopify sales · Imported orders · Average imported order value · Units sold. Each: value, period, delta vs previous equivalent period, currency where applicable, definition line, native drill-down. |
| D | **Sales trend** | The page's only chart: daily (hourly for 24 h) imported-sales bars for the current period + dashed neutral line for the previous equivalent period. Accessible summary sentence + full table equivalent (`<details>`). Order counts live in the table, not on a second axis. |
| E | **Top products** | ≤5 rows: product, units, imported sales value, share of the period's imported sales, drill-down. No chart. |
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

## 6. Metric traceability table (the gate)

Every displayed element passes this gate or does not appear. "Endpoint"
means the new bounded aggregate contract (slice 1 of the handoff): the data
source exists at the exact current head; the aggregate RPC that serves it is
the (not yet implemented) production step. Domains are the truthful
definitions the endpoint must implement; commercial rows additionally apply
the §7 truth rules. Company isolation for every row: record rules on
connector models + an explicit `company_id in allowed_companies` term +
`sec3_scope_quarantined = False`; the endpoint never uses `sudo()`.

| # | Displayed label | Operator question | Source model · stored fields | Domain / filter | Aggregation | Time window | Store isolation | Zero/empty behaviour | Stale-data behaviour | Native drill-down | Supported at `a1c5931`? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Imported Shopify sales | What value of Shopify orders landed in Odoo this period? | `sale.order.amount_total`, `currency_id` joined via `shopify.connector.order.binding.sale_order_id` | binding: `store_id=?`, `sec3_scope_quarantined=False`, `shopify_cancelled_at=False`; order: `state != 'cancel'`, `date_order` in window | SUM | `date_order` (= Shopify `processedAt`) in selected window, user-TZ boundaries | `binding.store_id` | Show `0.00 CUR`; if orders=0 and bridge healthy → region-D/E empty state "No sales in this period" | Card carries completeness dot + caption bound to region G state | Orders Workspace `shopify_connector_sale.action_shopify_connector_order_workspace` + same domain | **Yes** (data); endpoint = slice 1 |
| C2 | Imported orders | How many Shopify orders were imported for the period? | `shopify.connector.order.binding` (+ joined order state) | as C1 | COUNT | as C1 | as C1 | `0` | as C1 | as C1 | **Yes**; endpoint = slice 1 |
| C3 | Average imported order value | Typical imported order size? | derived C1/C2 | as C1 | SUM/COUNT | as C1 | as C1 | `—` when C2=0 (never divide by zero) | as C1 | as C1 | **Yes** (derived) |
| C4 | Units sold (imported) | How many product units were sold? | `sale.order.line.product_uom_qty`, filter `shopify_line_item_gid != False` | line join order join binding, C1 exclusions | SUM | as C1 | via binding join | `0` | as C1 | as C1 (order-level list) | **Yes**; endpoint = slice 1 |
| C∆ | "vs previous period" delta on C1/C2/C3/C4 | Better or worse than the preceding equivalent period? | same as each card | same, window shifted back by its own length | same | previous equivalent window | same | When previous value is 0 → "no prior-period data", never a % | inherits card state | n/a (caption) | **Yes** (derived) |
| D1 | Sales trend (bars + previous-period line) | How did imported sales move across the period? | as C1 | as C1 | SUM per bucket (day; hour for 24 h) | buckets in user TZ, stated on chart caption | as C1 | Honest empty state (one of the three §9.4 variants) | chart caption inherits G | table rows link to Orders Workspace day-filtered | **Yes**; endpoint = slice 1 |
| E1 | Top products (≤5) | Which products drove imported sales? | `sale.order.line`: `product_id`, `product_uom_qty`, `price_subtotal` (untaxed) | as C4 | GROUP BY product, SUM value+units, ORDER value DESC LIMIT 5 | as C1 | via binding join | Section hidden behind "No product sales in this period" line | inherits G | Product form (`product.template`) + Orders Workspace period filter; exact per-store *line* list needs server-built domain (slice 2 note) | **Yes** (display); drill-down exactness = slice 2 |
| E2 | Share of imported sales (per top product) | How concentrated were sales? | derived E1 value / C1-untaxed-basis | as E1; denominator = SUM `price_subtotal` over all C4 lines | ratio | as C1 | as C1 | Hidden when denominator 0 | inherits G | n/a (cell) | **Yes** (derived; same-basis numerator/denominator) |
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

**Rejected at the gate** (must not appear; recorded per prompt §10): refunds
/ returned value (no refund records exist anywhere — §8.1), "Net sales"
(label unreproducible — §7.1), success-rate percentage for flows (denominator
ambiguity between scans/syncs within a family made the number misleading;
replaced by absolute backlog+failure counts, which drill down exactly),
"next scheduled check" clock time (needs `ir.cron` sudo read — deferred),
delivered-inconsistency fulfillment counter (field exists but no code ever
writes it — would always read 0; recorded caveat from module inventory).

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
| Cancelled / test orders | pre-cancelled and (by default) test orders never imported; if `order_import_include_test` is on, test orders are indistinguishable — the settings surface, not the dashboard, owns that disclosure |
| Discounts | line-level discounts are inside `amount_total` (converted to line discount % at import; residual as a negative adjustment line) |
| Taxes / shipping / duties / fees | taxes+shipping included (stated on the card); duties/tips/fees orders are never imported at all |
| Refunds / returns / edits | never imported; REFUNDED/VOIDED/EXPIRED never imported; PARTIALLY_REFUNDED blocked at review; post-import refresh never changes amounts — hence no reversal treatment exists to display |
| Sale date | `date_order` = Shopify `processedAt` (fallback `createdAt`) |
| Reversal date | n/a (no reversals imported) |
| Period boundary & TZ | window and buckets in the requesting user's Odoo timezone, stated in the chart caption; deviation from Shopify's shop-timezone reporting disclosed in the definition |
| Previous period | same length, immediately preceding, same TZ rules |
| Currency | one currency per store (enforced at import); cross-currency totals never combined |
| Incomplete import | never silently ignored — region G states it and region B escalates it (§9.3) |
| Drill-down domain | the C1 domain verbatim on the Orders Workspace |

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

## 9. States and behaviour

### 9.1 Refresh contract

Manual Refresh button + auto-refresh ≥30 s, paused in hidden tabs (existing
`PB-12` behaviour, `shopify_connector_dashboard.js:84-134`). Header shows
"Updated HH:MM" from `generated_at`. Nothing is labelled live.

### 9.2 Severity model

Unchanged from U0 (`_derive_state`): `empty / healthy / warning /
manual_review / degraded`; a healthy lead can never coexist with an active
danger/warning item; decision items are distinguished from technical failures
by icon + owner label + wording, never colour alone.

### 9.3 Data-completeness bridge states (region G, drives region B)

| State | Truthful condition (all fields stored today) |
| --- | --- |
| **Complete & current** | `order_sync_scheduled` true · G2 = 0 · G3 = 0 · checkpoint age ≤ 45 min (3× the 15-min scan cron) |
| **Processing** | G2 > 0, G3 = 0, checkpoint age ≤ 45 min — figures may rise shortly; no alarm |
| **Stale** | checkpoint age > 45 min with scheduling on, or scheduling off with import history present |
| **Incomplete — action needed** | G3 > 0, or store `reconnect_needed/disconnected`, or sale domain disabled while other flows run → region B renders the critical band naming the commercial consequence |

### 9.4 Empty states (three distinguishable variants, correction §7)

1. **No sales in this period** — bridge Complete & current, C2 = 0: calm
   line inside C/D; connector sections render normally.
2. **Sales data not synchronized yet** — sale domain disabled or no
   checkpoint/no bindings: C–E collapse to one guided card ("Order import
   hasn't run for this store — an administrator can enable it in Store
   Settings"), no fake zeros; F renders fully.
3. **Period predates imported history / insufficient permissions** — window
   start earlier than the earliest imported order with the 30-day default
   import window disclosed ("Orders before *date* were not imported; import
   window 30 days; administrators can run a historical backfill"), or the
   caller lacks `sale.order` read access ("Your role can't read sales
   amounts — connector health is unaffected"), detected by catching the
   ACL refusal server-side. Never rendered as `0.00`.

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
- **Mobile (390 px):** sections stack in decision order A→B→C→G→D→E→F→H; KPI
  cards full-width (no horizontal card scrolling); the freshness/completeness
  line stays adjacent to the sales cards; every drill-down remains reachable;
  tables (top products, multi-store, chart equivalent) scroll inside their
  own `overflow-x: auto` container — the page itself never scrolls
  horizontally.
- Healthy screens are commercially useful (sales content fills them);
  attention screens state explicitly whether the connector problem affects
  the displayed sales figures (region B copy + card completeness dots).

## 12. Prototype

`prototypes/shopify-operations-360-dashboard.html` + adjacent
`shopify-operations-360-dashboard.css`:

- Self-contained except the one adjacent stylesheet; no network requests, no
  external assets/fonts/CDNs/chart libraries; sanitized static demonstration
  data only; permanently labelled **"DESIGN PROTOTYPE — NOT LIVE DATA"**.
- Three states (healthy / attention / empty variants) + LTR/RTL, switched by
  a small deterministic inline script (state toggles set `data-state`/`dir`;
  no timers, no fetch, no randomness). The switcher is prototype chrome only
  and is excluded from the design surface.
- Focus styles are real and demonstrable by keyboard; the attention state is
  understandable with colour removed (icons + owner labels + wording).

## 13. Prototype verification record (real browser, this session)

Chromium (Playwright, `/opt/pw-browsers/chromium`), file:// load. The numbers
below are measured DOM facts from the runs that produced the committed
screenshots; screenshots alone are not treated as proof.

Environment: Chromium **141.0.7390.37** (Playwright 1.56.1), viewports at
`deviceScaleFactor: 1`. Each run loaded the committed prototype from disk
with a state hash and captured a full-page screenshot after verifying the
state and direction had genuinely applied (`document.body.dataset.state`,
computed `direction` on the surface root).

| Run (committed screenshot) | Viewport | State/dir applied | `scrollWidth` vs `innerWidth` | Clipped text outside sanctioned scroll containers | Flow drill-downs visible | Keyboard: Tab presses to the LAST flow-row "Open" | Focus indicator (first focused control) | Requests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `healthy-desktop-1366px.png` | 1366×900 | healthy / ltr | 1366 = 1366 — none | 0 elements | 5/5 rows | 23 | 2px solid `#175CD3`, offset 2px | 2, both `file://` |
| `attention-desktop-1366px.png` | 1366×900 | attention / ltr | 1366 = 1366 — none | 0 elements | 5/5 rows | 26 | 2px solid `#175CD3` | 2, both `file://` |
| `attention-tablet-768px.png` | 768×1024 | attention / ltr | 768 = 768 — none | 0 elements | 5/5 rows | 26 | 2px solid `#175CD3` | 2, both `file://` |
| `attention-mobile-390px.png` | 390×844 | attention / ltr | 390 = 390 — none | 0 elements | 5/5 rows | 26 | 2px solid `#175CD3` | 2, both `file://` |
| `attention-rtl-desktop-1366px.png` | 1366×900 | attention / **rtl** | 1366 = 1366 — none | 0 elements | 5/5 rows | 26 | 2px solid `#175CD3` | 2, both `file://` |
| `empty-desktop-1366px.png` | 1366×900 | empty / ltr | 1366 = 1366 — none | 0 elements | 5/5 rows | 16 | 2px solid `#175CD3` | 2, both `file://` |

Additional measured facts:

- **Network isolation:** every run issued exactly 2 requests — the HTML file
  and its adjacent CSS file, both `file://`. Zero external requests of any
  kind.
- **RTL is a real mirror, not a claim:** with `dir="rtl"`, the attention
  exception's accent edge computes `border-right-width: 4px` /
  `border-left-width: 1px` (the LTR render shows the reverse), and the
  header identity block moves from x≈93 to x≈1021 while the controls cross
  to the opposite side (`header_mirrored: true`). Directional arrow icons
  flip via `[dir="rtl"] .ic--arrow`. Expected bidi artefact recorded
  honestly: untranslated English copy in an RTL context reorders neutral
  punctuation ("+4.1%" renders as "4.1%+"), exactly as Odoo renders
  untranslated strings under an RTL locale; translated production copy does
  not exhibit it.
- **Reduced motion:** under emulated `prefers-reduced-motion: reduce`,
  button `transition-duration` computes to 0.000001 s in every run; no
  animation carries meaning anywhere.
- **Attention state without colour:** each of the three attention items
  carries an icon, a kind chip ("Connection" / "Technical failure" /
  "Human decision") and an owner label ("Owner: Administrator" / "Owner:
  Operator" / "Owner: Reviewer / Administrator") — measured from the DOM,
  not asserted from the stylesheet.
- **States are materially distinct:** the visible-section inventory differs
  per state (healthy: KPI row + bridge-ok + sales row + full health block;
  attention: critical band + flagged KPI row + bridge-bad + sales row +
  degraded health + needs-attention + stores table; empty: guided card +
  annotation + simplified health, no KPI/bridge/sales row).
- The keyboard walk uses real `Tab` key dispatches; the first surface
  control receives focus on press 6 in every run and shows the 2 px solid
  outline (`outline-color: rgb(23, 92, 211)`).

## 14. Sources

Repository: exact head `a1c593183f6aaa1238e87486ca518717cefc53a9` — files
cited inline (§2, §5, §6). External: the competitor/platform pages listed
with access status and date in the
[benchmark document](../01-research/ui-operations-360-competitor-benchmark-2026-08-01.md);
WCAG 2.2 criteria references as recorded in
`docs/05-qa/ui-u2-validation-results.md` §6 (accessed 2026-07-27).
