# Shopify Store 360 — Implementation Handoff (2026-08-01)

> **Status: Design-concept handoff. NOT implemented, NOT accepted, NOT
> scheduled.** Produced on the isolated branch `fable/ui-operations-360-concept`
> from the exact PR #204 head `a1c593183f6aaa1238e87486ca518717cefc53a9`.
> Nothing under `addons/**` changed in this session; PR #204 is untouched.
> Implementation may begin only when the control room authorizes it as a
> wave/batch under CLAUDE.md §13, with its own allowed-files packet,
> independent review and runtime evidence. This document is the input to that
> packet, not a substitute for it.

> **Correction revision (control room, 2026-08-01):** the raw-SQL aggregate
> recommendation is **withdrawn** and replaced (§6); slice 1 is reclassified
> as a schema enhancement with migration/backfill (§11); Shopify Sales
> Analysis gets a feasible `sale.report`-extension source and is
> reclassified as a reporting backend enhancement (§14.1); adversarial
> record-rule tests are mandatory (§8); gap registers added (§15).

Normative companions:
[product spec](../02-product/ui-operations-360-dashboard-spec-2026-08-01.md)
(information architecture §3, metric gate §6, truth rules §7 incl. the
payment/COD/delivery matrices §7.3–§7.5, workflow traceability §14,
verification record §13) ·
[competitor benchmark](../01-research/ui-operations-360-competitor-benchmark-2026-08-01.md) ·
prototype
[`shopify-operations-360-dashboard.html`](../02-product/prototypes/shopify-operations-360-dashboard.html)
/ [`.css`](../02-product/prototypes/shopify-operations-360-dashboard.css) ·
screenshots
[`operations-360-dashboard-2026-08-01/`](../02-product/prototypes/operations-360-dashboard-2026-08-01/).

---

## 1. Current-dashboard assessment (concise)

The shipped U0 dashboard is architecturally right and commercially empty. Its
guarantees — one bounded aggregate RPC, constant query count, count/domain
agreement with the list an operator lands on, a single severity model,
redaction discipline, a 30 s visibility-aware refresh floor — are exactly what
a premium connector needs and are all retained. But the healthy screen spends
a full viewport saying "everything is fine" twice, shows five near-zero chips,
and answers no merchant question. The repository meanwhile already stores
verified commercial truth (order totals solver-reconciled against Shopify
evidence at import) that no surface shows. Store 360 keeps the operational
skeleton and gives the page a commercial spine.

## 2. Retained / changed / deliberately omitted

**Retained verbatim:** the AbstractModel aggregate pattern and its hard
guarantees; the severity model and its invariants; ≤3 attention items with
`target` (res_model + domain + name) drill-downs and the count=domain-count
test; the 8-row activity feed; ≥30 s visibility-aware refresh; the token
layer; logical-properties/RTL discipline incl. the locale-bound `dir` root;
group gating (auditor floor) and the no-sensitive-data walk.

**Changed:** page renamed **"Shopify Store 360 — Sales performance and
connector health"**; commercial sections (KPI cards, one sales-trend chart,
top products, completeness bridge) become the primary content in the
spec §3 decision order; an **Order lifecycle region (L)** added between top
products and connector health (payment / COD / fulfillment & dispatch
strips + ≤3 lifecycle exceptions — spec §3, §7.3–§7.5); store + period + comparison controls added to the
header; the duplicated all-clear band collapses into one compact health lead
inside the connector block; the 7-day sparkline is replaced by the sales
trend chart plus a two-number text line ("Last 7 days: N succeeded, M
failed"); flow-health rows and four operational counters added; multi-store
table added, rendered only when >1 store is in scope; critical band added,
rendered only when commercial figures are materially affected (spec §9.3).

**Deliberately omitted:** everything in spec §4 and §8 — refunds column (no
refund records exist), "Net sales"/revenue labels, geography, segments,
channel, traffic, ROAS, margin, CLV, forecasting, payouts, second
operational chart, pies, configurable widgets, per-module dashboards, PDF
packs, any mutating control.

## 3. Competitor lessons adopted and rejected

Full analysis with per-vendor sources: benchmark §6. Summary:

- **Adopted:** date-range + store filters with truthful cancelled-order
  exclusion (VentorTech's filter set, hardened into definitions); revenue
  trend + top products as the commercial core (VentorTech claims); freshness
  watermarks elevated to a first-class completeness bridge (TeqStars/Emipro
  record-level cues); exact failure reason + direct drill-down (Webkul
  feeds / Emipro Mismatch Log — already our U0 pattern); multi-store
  comparison, conditional (VentorTech / TeqStars hub).
- **Rejected:** "net sales"/"real-time" language nobody defines; pie charts;
  Enterprise/group-gated core health (Emipro's Net Profit pattern); a
  staging-feed monitoring concept parallel to jobs; Shopify-Analytics-parity
  claims; report builders and analytics warehouses.
- **The gap we target:** no fetched vendor page couples a commercial figure
  to its import completeness. The bridge is the differentiator.

## 4. Approved information architecture

Spec §3, nine regions in decision order (header → conditional critical
status → KPI cards → bridge → trend + top products → **order lifecycle (L)**
→ connector health → multi-store) with the cross-currency rule (never
combine currencies; per-store rows instead) and the three distinguishable
empty-state variants (spec §9.4). The prototype demonstrates all of it; the
committed screenshots and DOM verification record (spec §13) are the visual
acceptance baseline. The workflow-to-UI-to-data traceability matrix is spec
§14.

## 5. Metric traceability table

Reproduced verbatim from spec §6, which is normative if the two ever drift.

| # | Displayed label | Operator question | Source model · stored fields | Domain / filter | Aggregation | Time window | Store isolation | Zero/empty behaviour | Stale-data behaviour | Native drill-down | Supported at `a1c5931`? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Imported Shopify sales | What value of Shopify orders landed in Odoo this period? | `sale.order.amount_total`, `currency_id` joined via `shopify.connector.order.binding.sale_order_id` | binding: `store_id=?`, `sec3_scope_quarantined=False`, `shopify_cancelled_at=False`; order: `state != 'cancel'`, `date_order` in window | SUM | `date_order` (= Shopify `processedAt`) in selected window, user-TZ boundaries | `binding.store_id` | Show `0.00 CUR`; if orders=0 and bridge healthy → "No sales in this period" | Card carries completeness dot + caption bound to bridge state | Orders Workspace `shopify_connector_sale.action_shopify_connector_order_workspace` + same domain | **Yes** (data); endpoint = slice 1 |
| C2 | Imported orders | How many Shopify orders were imported for the period? | `shopify.connector.order.binding` (+ joined order state) | as C1 | COUNT | as C1 | as C1 | `0` | as C1 | as C1 | **Yes**; endpoint = slice 1 |
| C3 | Average imported order value | Typical imported order size? | derived C1/C2 | as C1 | SUM/COUNT | as C1 | as C1 | `—` when C2=0 (never divide by zero) | as C1 | as C1 | **Yes** (derived) |
| C4 | Units sold (imported) | How many product units were sold? | `sale.order.line.product_uom_qty`, filter `shopify_line_item_gid != False` | line join order join binding, C1 exclusions | SUM | as C1 | via binding join | `0` | as C1 | as C1 (order-level list) | **Yes**; endpoint = slice 1 |
| C∆ | "vs previous period" delta on C1/C2/C3/C4 | Better or worse than the preceding equivalent period? | same as each card | same, window shifted back by its own length | same | previous equivalent window | same | When previous value is 0 → "no prior-period data", never a % | inherits card state | n/a (caption) | **Yes** (derived) |
| D1 | Sales trend (bars + previous-period line) | How did imported sales move across the period? | as C1 | as C1 | SUM per bucket (day; hour for 24 h) | buckets in user TZ, stated on chart caption | as C1 | Honest empty state (one of the three spec §9.4 variants) | chart caption inherits bridge | table rows link to Orders Workspace day-filtered | **Yes**; endpoint = slice 1 |
| E1 | Top products (≤5) | Which products drove imported sales? | `sale.order.line`: `product_id`, `product_uom_qty`, `price_subtotal` (untaxed) | as C4 | GROUP BY product, SUM value+units, ORDER value DESC LIMIT 5 | as C1 | via binding join | Section hidden behind "No product sales in this period" line | inherits bridge | Product form + Orders Workspace period filter; exact per-store *line* list needs server-built domain (slice 2 note) | **Yes** (display); drill-down exactness = slice 2 |
| E2 | **Share of goods subtotal** (per top product) | How concentrated were product sales? | derived: E1 `price_subtotal` value ÷ SUM `price_subtotal` over **all** eligible goods lines (the C4 population) | as E1; denominator = the same eligible goods-line basis as the numerator — **never** C1 (C1 includes tax + shipping; this ratio must not imply it divides the headline) | ratio | as C1 | as C1 | Hidden when denominator 0 | inherits bridge | n/a (cell; the goods-subtotal basis is printed under the table) | **Yes** (derived; same-basis numerator/denominator, correction §6C) |
| G1 | Sales data synchronized through | Up to when has Shopify order discovery landed? | `shopify.connector.store.order_sync_last_checkpoint_at` (compute over `settings.sale_order_last_import_checkpoint_at`, `shopify_connector_sale/models/shopify_connector_order_scan.py:566`) | store row | latest value | point-in-time | per store | "Not synchronized yet" empty variant | drives the bridge state machine (spec §9.3) | Store form | **Yes** |
| G2 | Orders awaiting import | How many discovered orders haven't landed? | `shopify.connector.job` | `job_type='order_import_sync'`, `state in (draft,queued,running,retry_waiting)`, `store_id=?` | COUNT | point-in-time | `job.store_id` | `0` → contributes to "Complete & current" | n/a (is itself the freshness signal) | Sync Center `action_shopify_connector_sync_center` + domain | **Yes** |
| G3 | Order imports needing attention | Is commercial completeness blocked on a human/failure? | `shopify.connector.job` | `job_type in (order_import_scan, order_import_sync)`, `state in (failed_retryable, failed_final, blocked_manual_review)` | COUNT | point-in-time | `job.store_id` | `0` | n/a | Error & Review Center `action_shopify_connector_error_center` + domain | **Yes** |
| F1 | Overall connector state (lead line) | Is anything wrong right now? | derived from F/G counters — same severity model as today (`_derive_state`, ui_dashboard.py:148) | see F2–F5 | derivation | point-in-time | selected store scope | "empty" first-run state | n/a | n/a | **Yes** (existing model, + store param = slice 1) |
| F2 | Active backlog | How much work is in flight? | `shopify.connector.job` | `state in (queued, running, retry_waiting)` (+ store) | COUNT | point-in-time | `job.store_id` | `0` | n/a | Sync Center + domain | **Yes** |
| F3 | Oldest waiting item | Is the queue moving? | `shopify.connector.job.create_date` | `state in (queued, retry_waiting)` (+ store) | MIN via `search(..., order='create_date asc', limit=1)` | point-in-time, shown as age | `job.store_id` | "—" when no waiting work | n/a | that job's form | **Yes** (`create_date` is the documented proxy; no dedicated enqueued-at field exists) |
| F4 | Needs review | What waits on a human? | jobs `blocked_manual_review` + uncertain attempts (`observed_outcome='uncertain'`, `resolution_disposition=False`) + match decisions `state='pending'` + gateway approvals `manual_gateway_approval_state='pending'` | each with store term | SUM of 4 COUNTs, decomposed in supporting text | point-in-time | native `store_id` on each model | `0` | n/a | each component its own action (Error Center / Mutation Evidence / Match Decisions / Orders Workspace filtered) | **Yes** |
| F5 | Final failures | What stopped permanently? | `shopify.connector.job` | `state='failed_final'` (+ store) | COUNT | point-in-time | `job.store_id` | `0` | n/a | Error & Review Center + domain | **Yes** |
| F6 | Flow row × 5: state · last success · backlog · failures | Which flow is delayed or failing? | jobs by flow `job_type` families — Orders: `order_import_scan, order_import_sync, customer_import_sync`; Catalog: `product_import_scan, product_import_sync`; Inventory: `inventory_push_sync, inventory_push_scan, inventory_first_push_preview, inventory_location_sync, inventory_activate, inventory_set_quantities, inventory_mutation_reconcile`; Export: the 14 `product_export_*` types; Fulfillment: the 10 `fulfillment_*` types. Last-success anchors: G1 / `settings.product_last_import_success_at` / `settings.inventory_last_push_scan_at` / latest preview `applied_at` / `settings.fulfillment_last_reconciliation_at` | backlog: `state in (queued,running,retry_waiting)` per family; failures: `state in (failed_retryable,failed_final,blocked_manual_review)` per family | COUNT per family (2 `read_group` calls grouped by `job_type`, mapped to families — constant queries) | point-in-time; last-success = stored watermark | `job.store_id` / settings per store | Flow row renders "No activity yet" | last-success age drives row tone | Sync Center / Error Center with the family `job_type in (...)` domain | **Yes** |
| F7 | Needs attention (≤3 items) | What exactly do I act on first? | existing exception builder (ui_dashboard.py:230-317) + two new sources: pending match decisions (`action_shopify_connector_product_match_decision`), orders awaiting configuration (existing action `action_shopify_connector_orders_awaiting_configuration`) | per candidate; count MUST equal its target domain count (existing test invariant) | COUNT per candidate, ranked danger-first | point-in-time | per candidate store term | Section replaced by single affirmative line | n/a | each item's `target` (res_model + domain + name) | **Yes** |
| F8 | Recent activity (≤8) | What happened just now? | `shopify.connector.job`: `state, job_type, job_source, store_id, finished_at` | `state in (succeeded, failed_final, skipped, cancelled)` (+ store) | `search_read` limit 8, `finished_at desc` | latest 8 | `job.store_id` | "No sync activity yet." | n/a | job form | **Yes** (existing) |
| F9 | Last-7-days counters (text line) | Rough weekly pulse? | jobs `finished_at` in last 7 days | `state='succeeded'` / `state in (failed_final,failed_retryable)` | 2 COUNTs | rolling 7 days | `job.store_id` | Line hidden with <1 day of history | n/a | Sync Center | **Yes** (replaces sparkline queries) |
| F10 | Quiet metadata: API health · scheduled-sync posture | Anything throttled? Is automation on? | `store.api_health_state (normal/throttled/degraded)`, `api_throttle_observed_at`; `order_sync_scheduled` etc. (cron-verified computes) | store row | latest values | point-in-time | per store | omitted when normal | n/a | Store form | **Yes** ("next scheduled check" clock time itself = deferred; needs a security-reviewed `ir.cron` read) |
| H1 | Multi-store table | Which store needs me? | per-store: `store.state`, latest terminal `finished_at`, F2/F4+F5 counts, C1 per store currency | grouped by `store_id` (single `read_group` per measure — no N+1) | per-store COUNT/SUM/MAX | point-in-time + selected window for sales | inherent | Region hidden when ≤1 store | sales cell inherits per-store bridge | Store form; counts → Sync/Error Center store-filtered | **Yes**; endpoint = slice 1 |
| B1 | Critical status band | Does a connector problem make the money numbers wrong? | derived: bridge state ∈ {Stale, Incomplete} or store `reconnect_needed/disconnected` or sale domain disabled with history present | spec §9.3 conditions | boolean + worst cause | point-in-time | selected store | absent when conditions false | is itself the stale surface | cause-specific action (Error Center / Store form) | **Yes** (derived) |
| L1 | Payment strip: Paid · Authorized — capture pending · Payment pending (non-COD) · COD · needs review | Which imported orders are actually paid? | `binding.shopify_financial_status_snapshot` (raw), `is_cod`, `binding.status` — counted over the C1 population (imported orders only, caption says so) | C1 exclusions + snapshot buckets: `PAID` / `AUTHORIZED` / `PENDING & is_cod=False` / `is_cod=True` / `status='review'` (payment-caused review incl. PARTIALLY_PAID-as-quotation imports and post-import divergence) | COUNT per bucket | as C1 | as C1 | Strip hidden when C2=0 | caption shows oldest `shopify_last_evidence_refresh_at` in the set | Orders Workspace with the same bucket domain | **Yes** (fields stored; buckets are raw-snapshot equality, fail-closed upstream) |
| L2 | Payment-evidence freshness caption | How fresh is the payment evidence? | `binding.shopify_last_evidence_refresh_at`, `financial_status_changed_at` | C1 population | MIN (oldest) + latest change | point-in-time | as C1 | omitted when C2=0 | is itself the freshness surface | Orders Workspace sorted by evidence age | **Yes** |
| L3 | COD block: awaiting approval / quotation / confirmed; collection nothing / partially / fully | Where does each COD order stand commercially? | `manual_gateway_approval_state`, `cod_commercial_state`, `cod_collection_state` | `is_cod=True` + C1 exclusions; approval='pending' / commercial ∈ (quotation, confirmed) / collection ∈ (nothing_collected, partially_collected, fully_collected) | COUNT per state | as C1 | as C1 | Block hidden when COD count = 0 | inherits L2 | Orders Workspace COD filter; approvals → the binding list `manual_gateway_approval_state='pending'` | **Yes** (states written at import/refresh/approval — importer:2241-2247, 2290-2296, 2361-2384) |
| L4 | Order fulfillment progress: Fulfilled · Partially fulfilled · Unfulfilled | How far along is Shopify order fulfillment? | `binding.shopify_fulfillment_status_snapshot` (raw `displayFulfillmentStatus` — Shopify's own order-level rollup, so multi-fulfillment orders are never double-counted) | C1 population; raw-value buckets, any other/NULL value shown as "Not yet observed" | COUNT per bucket | as C1 | as C1 | hidden when C2=0 | caption: snapshot refreshed at import + evidence refresh (`shopify_last_evidence_refresh_at`) — **not** a live carrier feed | Orders Workspace bucket domain | **Yes** (display-only snapshot with stated freshness) |
| L5 | Odoo dispatch: to dispatch / ready / dispatched | What does the warehouse still owe? | native `stock.picking.state` for outgoing pickings of bound orders (`sale_id` join — the same join production uses, fulfillment_inbound.py:87-89) | pickings of C1 orders: `state not in (done, cancel)` = to dispatch; `state='assigned'` = ready; `state='done'` = dispatched | COUNT | as C1 | via order join | `0` | n/a (Odoo-side truth) | native Delivery Orders list, same domain | **Yes** (native fields; picking ACLs apply to the caller) |
| L6 | Oldest paid-unfulfilled age | Is anything paid but sitting? | derived: MIN `date_order` where snapshot `PAID` + fulfillment snapshot `UNFULFILLED` | C1 exclusions | MIN age | as C1 | as C1 | omitted when none | elapsed age only — **no SLA claimed** (correction §E: no invented threshold; age is displayed, lateness is not declared) | Orders Workspace same domain, oldest first | **Yes** (derived) |
| L7 | Lifecycle exceptions (≤3): COD awaiting approval · external fulfillment recorded in Shopify · payment status changed after import · Shopify cancelled a validated fulfillment · fulfilled while payment still pending · unknown fulfillment status observed | What lifecycle event needs a human? | approvals `manual_gateway_approval_state='pending'`; evidence `reconciled_state='review'` with `review_reason ∈ (external_fulfillment_observed, origin_unconfirmed)`; binding `status='review'` + `financial_status_changed_at` + previous≠current snapshot; evidence `review_reason='cancelled_after_validation'`; derived snapshot pair (`displayFulfillmentStatus ∈ (FULFILLED, PARTIALLY_FULFILLED)` + financial `PENDING/AUTHORIZED` + `is_cod=False`); evidence `schema_warning=True` | per candidate, store term, count = drill-down domain count (existing invariant) | COUNT per candidate, ranked | point-in-time | native store term on each model | section replaced by one affirmative line | each item names its evidence timestamp (`last_observed_at` / `financial_status_changed_at`) | binding list / fulfillment review list (`action` per source) with the same domain | **Yes** — every named source has a production writer at `a1c5931` (spec §5); each item states what/why/who/freshness/whether the connector can resolve it (report-only for external events) |

**Commercial metric decision table** (correction-mandated classification;
rationale in spec §7.2): Sales value → *include with truthful renamed label*
("Imported Shopify sales"); order count, AOV, units sold, period comparison,
sales trend, top products (share = *goods-subtotal basis*),
freshness/completeness, payment-status distribution, COD
approval/commercial/collection counts, order-fulfillment progress
(freshness-captioned), Odoo dispatch states → *include now*; refunds /
returned value → *defer* (no refund records exist anywhere); "Net sales"
(Shopify definition) and cross-currency combined totals → *requires backend
enhancement*; COD amounts, COD dispatch/delivery lifecycle, COD collection
discrepancy, carrier delivery (Delivered / Not delivered / in transit /
attempted) → *requires backend enhancement* (spec §7.4–§7.5);
general payment-gateway dimension → *defer*; taxes/shipping decomposition
and discount value → *defer to the native Shopify Sales Analysis report*.

## 6. Backend contract changes required

> **Correction A (control room, 2026-08-01) — supersedes this handoff's
> earlier raw-SQL recommendation, which is hereby WITHDRAWN.** The earlier
> §6 claimed parameterized raw SQL could coexist with "runs as the current
> user, ACLs and record rules apply". That claim was wrong for record
> rules: `check_access_rights('read')`, a generic rule probe and mirrored
> company/store/quarantine predicates do **not** reproduce an arbitrary
> user-specific `sale.order`/`sale.order.line` record rule (e.g. "salesmen
> see own documents only", or any custom non-company rule). A raw aggregate
> over all company rows could disclose totals, product names or trends the
> caller's rules forbid. `[Fact]` Official guidance: record rules "are
> *conditions* which must be satisfied in order for an operation to be
> allowed… evaluated record-by-record, following access rights"; using the
> cursor directly bypasses "the automated behaviours like translations,
> invalidation of fields, `active`, access rights and so on"
> (odoo/documentation@19.0
> `content/developer/reference/backend/security.rst`, accessed 2026-08-01).

**Selected architecture — connector-owned stored projection on the sale
documents, aggregated with rule-respecting ORM grouped reads.** All
commercial aggregation runs **on `sale.order` / `sale.order.line`
themselves**, as the current user, via `formatted_read_group` /
`_read_group` / `search_count` / bounded `search` — the exact APIs the
repository already uses and adversarially tests for rule-scoped grouped
reads (`test_grouped_read_does_not_leak_foreign_rows`,
`addons/shopify_connector_sale/tests/test_sec3_company_isolation.py:144-158`,
which itself documents "`formatted_read_group` is the Odoo 19 replacement
for the deprecated `read_group`"). No `sudo()` anywhere; native
sale ACLs and record rules stay fully active because the queried model IS
the ruled model.

Slice 1 changes, in `shopify_connector_sale` (projection) +
`shopify_connector_core` (aggregate service):

1. **Projection fields on `sale.order`** (contributed by
   `shopify_connector_sale`, the module that already owns the sale
   extension seam):
   - `shopify_connector_store_id` — M2O `shopify.connector.store`,
     `index=True`, `check_company=True` + `_check_company_auto` (the same
     SEC-3 pattern the bindings use, order_binding.py:12-22), so an order
     can never point at another company's store;
   - `shopify_connector_cancelled_at` — Datetime mirror of the binding's
     `shopify_cancelled_at`, maintained by the **same sanctioned refresh
     writer** that snapshots the binding (importer `_refresh_existing`);
   - `shopify_connector_quarantined` — Boolean mirror of
     `sec3_scope_quarantined`; the SEC-3 quarantine sweeps (which write in
     SQL by design) extend their statements to update this column in the
     same transaction, exactly as the fulfillment module already propagates
     quarantine to child lines in SQL
     (`_sec3_sync_line_quarantine`, fulfillment_inbound_evidence.py:284-305).
   - `sale.order.line` needs **no new field**: `shopify_line_item_gid`
     (goods marker) exists; the store dimension traverses
     `order_id.shopify_connector_store_id` in the ORM domain.
   - Write protection: populated **only** through the sanctioned import /
     refresh / quarantine paths (same protected-field discipline as the
     binding mixin); an ordinary write attempt is rejected — adversarial
     test below.
2. **Exact store/binding relationship**: the projection is written when the
   binding is created/refreshed, from the binding's own `store_id` — with a
   consistency constraint (order's projection store must equal its
   binding's store; company equality enforced by `check_company`). A
   backfill migration populates existing bound orders (§11).
3. **Aggregates** (all rule-respecting, constant count): current + previous
   window `formatted_read_group` on `sale.order`
   (`amount_total:sum`, `__count`), trend `formatted_read_group` grouped by
   `date_order:day` (`:hour` for 24 h), units + top products
   `formatted_read_group` on `sale.order.line` (domain
   `[('shopify_line_item_gid','!=',False), ('order_id.shopify_connector_store_id','=',store)]`
   + window; groupby `product_id`, `limit=5`, ordered by
   `price_subtotal:sum` desc), per-store H sales one grouped read by
   `shopify_connector_store_id`. Domains always include
   `state != 'cancel'`, `shopify_connector_cancelled_at = False`,
   `shopify_connector_quarantined = False`.
4. **Role gating**: the service calls `check_access_rights('read')` on
   `sale.order`(`.line`) only to *classify the refusal* — an `AccessError`
   degrades the commercial + lifecycle blocks to the honest `no_permission`
   variant, never zeros. It is a gate for the empty-state copy, **not** a
   substitute for rules (the rules apply inside every grouped read anyway).
5. **Record-rule behaviour, stated**: a caller restricted by any
   `sale.order`/`sale.order.line` rule sees aggregates over exactly the
   records their native drill-down list shows — count/domain agreement now
   *extends* to restrictive-rule users by construction, because aggregate
   and list run the same model + domain + rules as the same user.
6. **Upgrade risk**: standard inherited-field addition on a core model —
   carried by the module through version upgrades like every existing
   connector field on `sale.order.line`; no view of the sale app is
   overridden; `_read_group`/`formatted_read_group` are the supported 19.0
   APIs (repo evidence above cites odoo/odoo@19.0 30bde9ff).
7. **Performance**: the store M2O is indexed at definition; grouped reads
   hit `(shopify_connector_store_id, date_order)`-shaped predicates — the
   §7 open question about a `date_order` (or composite) index is measured
   in the perf scenario before deciding; the projection adds zero queries
   at dashboard time (it is stored data, not compute).
8. **Rejected alternative — binding-side numeric projection** (aggregate on
   the binding model instead): rejected because `sale.order` record rules
   would NOT apply to a binding-side aggregate; a rule-restricted user
   would see totals their order list hides. The chosen design is the only
   evaluated candidate where the ruled model and the aggregated model are
   the same object. (Raw SQL: withdrawn above. `sudo()`: forbidden.)
9. **Bridge + flow counters** unchanged: connector-model `search_count` /
   two grouped reads by `job_type` mapped to the five families (F6);
   per-store block one grouped read per measure; attention builder gains
   the two decision sources — count=domain invariant kept. **Order
   lifecycle (region L) counters**: grouped reads on the **binding** for
   payment/COD state distributions (connector data, connector rules) — but
   the three commercial-value-bearing surfaces (C, D/E, H sales) and any
   L count that must equal a sale-document drill-down run on the sale
   documents per the architecture above; L5 dispatch counts run on native
   `stock.picking` as the caller (picking ACLs apply).

**Preserved invariants:** no Shopify request, no credential read, no
mutation, no `sudo()`, bounded constant query count, current-user access,
count/domain agreement on every displayed number. The dashboard stays
read-only.

## 7. Bounded query / performance implications

- Total per render: the existing constant set plus ~9 bounded ORM
  statements (2 commercial grouped reads for current+previous window, 1
  trend grouped read ≤31 buckets, 1 units + 1 top-products `limit=5`
  grouped read on lines, 2 family grouped reads on jobs, ~2 lifecycle
  grouped reads on the binding + 1 picking `search_count` set) and ≤3
  per-store grouped reads. Constant in data volume; result sets capped by
  construction (5 products, 8 activities, 3 exceptions, ≤31 buckets,
  fixed state buckets).
- Supporting indexes already present at `a1c5931`:
  `binding.sale_order_id`, `binding.store_id`, `binding.company_id`,
  `sale.order.line.shopify_line_item_gid`, job `state/job_type/store_id`.
  **New with slice 1:** `sale_order.shopify_connector_store_id` (indexed at
  field definition). `[Open question]` whether `sale_order.date_order` (or
  a composite with the store column) needs a dedicated index at target
  volumes — measure first (see test plan); an index would be a small
  follow-up migration, not a redesign.
- Record-rule cost is accepted by design: grouped reads carry the caller's
  rule clauses (that is the point); the perf scenario runs as a
  rule-restricted user as well as an unrestricted one.
- Perf evidence requirement: extend `tools/perf0_baseline.py` with a
  `store_360_aggregate` scenario (seeded ≥50k orders / ≥100k jobs) and keep
  the PB-9/10/11 constant-query assertions in `test_ui_performance.py`
  green for the new RPC.

## 8. Security and company-isolation implications

- Runs as the calling user; auditor-floor `AccessError` gate retained; no
  `sudo()` anywhere in the aggregate path.
- **Record rules are preserved by construction, not mirrored by hand**: the
  commercial aggregates run on `sale.order`/`sale.order.line` with the
  caller's own rules active inside every grouped read (§6). There is no raw
  SQL in the dashboard path and therefore no bypass to compensate for.
- **Mandatory adversarial tests (correction §4.6)** — all must pass before
  slice 1 is accepted:
  1. a user with `sale.order` model read access but a restrictive
     **non-company** `sale.order` record rule: every commercial figure and
     trend bucket equals the sum over exactly the rule-visible records; no
     total, product name or trend movement from a hidden row;
  2. a different restrictive `sale.order.line` rule: units + top products
     obey it independently of the order-level rule;
  3. multi-company and cross-store attempts: store from company B requested
     by a company-A user → no data, no existence leak (same posture as the
     existing SEC-3 suites);
  4. quarantined binding: order excluded from every aggregate and every
     drill-down (`shopify_connector_quarantined` mirror verified against
     the binding flag, including after a SQL sweep);
  5. user without sale read access: commercial + lifecycle blocks are the
     `no_permission` variant — absent, never zeroed;
  6. aggregate count/value equals the exact native drill-down record set —
     asserted per displayed number, **as the restricted user too**;
  7. no commercial product label or aggregate leaks from an inaccessible
     row (assert on the payload walk, not just counts);
  8. projection write protection: an ordinary privileged-sales-user write
     to the projection fields is rejected; only the sanctioned import /
     refresh / quarantine paths may set them.
- Payload discipline unchanged: aggregates, labels, product display names
  and store names only — no customer PII, no payloads, no stack traces, no
  credentials; the recursive forbidden-key/email walk test extends to the
  new blocks (including region L, which carries state names and counts
  only — never gateway credentials, amounts from Char snapshots, or
  customer identity).
- Commercial block honestly absent (not zeroed) for roles without
  `sale.order` read.

## 9. Expected production files (later implementation)

- `addons/shopify_connector_sale/models/` — new sale-order projection
  extension (store link + the two exclusion mirrors, write-protected) +
  sanctioned-writer wiring in the importer refresh path (slice 1).
- `addons/shopify_connector_sale/migrations/…` — backfill script for
  existing bound orders (slice 1).
- `addons/shopify_connector_core/models/shopify_connector_ui_dashboard.py` — extend (slice 1).
- `addons/shopify_connector_core/tests/test_ui_dashboard.py`,
  `test_ui_performance.py`, `test_ui_source_guards.py` +
  `addons/shopify_connector_sale/tests/` (adversarial record-rule suite §8,
  projection-protection tests, backfill tests) — extend (slice 1).
- `tools/perf0_baseline.py` — add scenario (slice 1).
- `addons/shopify_connector_core/static/src/js/shopify_connector_dashboard.js`,
  `static/src/xml/shopify_connector_dashboard.xml`,
  `static/src/scss/shopify_connector_dashboard.scss`,
  `static/tests/shopify_connector_dashboard.test.js` — extend/replace (slice 2).
- `docs/06-prompts/ui-store-360-copy-deck.md` — new (slice 2).
- Slice 3: `views/` + menu records for "Sync Operations Analysis"
  (graph/pivot/list on `shopify.connector.job`, genuinely zero-schema) in
  core; "Shopify Sales Analysis" = `sale.report` projection extension +
  actions in `shopify_connector_sale` (§14.1 — a reporting backend
  enhancement, not zero-schema).
- Module version bumps; slice 1 carries the §11 backfill migration (plus,
  only if measurement demands it, a follow-up index migration).

## 10. Test plan

1. **Aggregate correctness** (slice 1, `test_ui_dashboard.py`): fixtures for
   every truth rule — in/out-of-window orders, Odoo-cancelled,
   Shopify-cancelled-after-import, quarantined binding, review binding,
   second company, second store, draft vs confirmed, zero-order AOV,
   previous-period-zero delta, the four bridge states, the three empty
   variants (incl. a user without sale access), cross-currency store pair
   (no combined total in payload).
2. **Guard suite**: SELECT-only + parameterized SQL AST assertions; no
   `sudo`; no write/enqueue/`_send` reachable; forbidden-key/email walk over
   the full new payload; count=domain agreement for every exception AND
   every flow/bridge drill-down.
3. **HOOT** (slice 2): state rendering (healthy/attention/empty variants),
   bridge tones, chart table equivalent, delta "no prior-period data" path,
   exception → `doAction` payload, refresh floor.
4. **Tours**: navigation drill-downs from KPI card, bridge, flow rows,
   attention items; keyboard-only walk to the last flow drill-down.
5. **Browser campaign** (repo's established instruments): 1366/768/390 +
   real-RTL (rtlcss present) + reduced-motion + 200 % zoom matrix, per-row
   surface-visible proof, no connector-owned clipping, focus-visible
   measurement, contrast table for the two chart colours and completeness
   dot on their real backgrounds.
6. **Perf**: scenario at seeded volume; constant-query assertion — run as
   both an unrestricted and a rule-restricted user.
7. **Adversarial security suite** — the eight §8 tests, mandatory for
   slice-1 acceptance.
8. **Order-lifecycle suite (correction addendum §H)** — required of the
   future implementation, explicitly NOT run in this documentation-only
   correction: Python model/service tests for every region-L bucket
   definition; restrictive-record-rule + company-isolation tests (§8); HOOT
   component tests for the lifecycle strips and exception items; real Odoo
   browser/tour workflow tests walking overview → lifecycle status →
   filtered orders → individual order evidence; exact count/domain tests
   per lifecycle number; stale/unknown-status tests (`schema_warning`
   rows, fail-closed financial values, evidence-age captions); partial and
   multi-fulfillment roll-up tests (one order never counted twice);
   COD transition tests (approval → confirmed → collection states,
   superseded approvals); retry, replay and concurrency tests wherever a
   lifecycle writer is introduced (COD amounts, delivery events);
   simultaneous payment × fulfillment state tests (neither axis overwrites
   the other); manual functional inspection by merchant, warehouse and
   finance roles; and controlled UAT using synthetic paid, authorized,
   pending, COD, partial, fulfilled and delivered scenarios.

## 11. Migration impact (reclassified — correction §4.5)

**Slice 1 is a backend/schema enhancement with a migration — not "no
schema change".** It adds three stored columns to `sale_order`
(`shopify_connector_store_id`, `shopify_connector_cancelled_at`,
`shopify_connector_quarantined`) and ships a **backfill migration** that
populates them for every existing bound order from its binding
(`UPDATE sale_order SET … FROM shopify_connector_order_binding …`,
company-consistent by the binding's own constraints), plus the index that
comes with the store M2O. The SEC-3 quarantine sweeps are extended to
propagate into the mirror column. Rollback of slice 1 must account for the
columns (revert + uninstall-safe: columns are additive and unused by any
other feature). Slice 2: no schema change (presentation only). Slice 3
(reporting): **also a reporting backend enhancement** — the Shopify Sales
Analysis report extends the `sale.report` SQL-view projection (§14) and is
carried by module upgrade like any report extension; no data migration.
Conditional: one small index migration if §7's open question resolves that
way.

## 12. Rollback plan

Each slice is independently revertable: revert the slice's merge commit and
warm-`-u` the module — slice 1 removes only the added RPC surface (no table,
no rows), slice 2 restores the previous dashboard assets (client action tag
unchanged), slice 3 removes the report actions/menus. No durable state is
created by any slice, so no data cleanup is ever needed.

## 13. Implementation slices (no more than three; not started)

1. **Truthful aggregate contract + sale projection** — the slice-1 schema
   enhancement (projection fields, sanctioned writers, backfill migration)
   and the `get_store_360_data` payload on rule-respecting grouped reads
   (§6), with the §8 adversarial suite, correctness and perf tests.
   Deliverable is invisible to users (old UI still renders). *Estimate:
   medium-to-large batch (grew by the projection + migration).*
2. **Responsive presentation and drill-down** — Owl template/SCSS per the
   committed prototype (including region L, the stacked mobile store
   cards and the Arabic-verified RTL behaviour), all drill-downs (incl.
   server-built top-product line domains), copy deck, HOOT + tours + full
   browser/RTL/zoom campaign. *Estimate: large batch (the visual acceptance
   baseline is the committed screenshot set).*
3. **Native reports and final validation** — "Sync Operations Analysis"
   (list/graph/pivot over jobs: store, flow family, state, source, period;
   direct navigation to failed/delayed work) and "Shopify Sales Analysis"
   per §14.1 (the `sale.report` extension — a reporting backend
   enhancement), plus the closing validation campaign. *Estimate: medium
   batch.*

## 14. Other UI / reporting recommendations, classified

| Candidate | Classification | Reason |
| --- | --- | --- |
| Sync Operations Analysis (native graph/pivot/list over `shopify.connector.job`) | **Include with dashboard** (slice 3, highest reporting priority) | Jobs model natively supports Count-measure graph/pivot today (`store_id`, `job_type`, `state`, `job_source`, `create_date`, `finished_at` all stored); genuinely zero schema work; answers the drill-deeper need the dashboard creates |
| Shopify Sales Analysis (native list/graph/pivot with the approved metric definitions) | **Include with dashboard — requires reporting backend enhancement** (slice 3; correction B resolution below) | Feasible source defined below; NOT zero-schema — it depends on the slice-1 stored store link and a `sale.report` projection extension |
| Data Readiness surface (unresolved matching/mapping/decision work with direct fixing navigation) | **Next small enhancement** | Building blocks exist (match-decision action, awaiting-configuration action, first-push guard queue); an umbrella menu + saved filters, no new models |
| Store Health list enrichment (connection, last processing, backlog, failures as store list columns/filters) | **Next small enhancement** | Computed store projections exist; N+1 compute fields need care in list context |
| Configurable notifications (final failure, stale queue, reconnect required) | **Later** | Needs channel/framework decisions (activities vs mail), per-store settings design (`notification_default_enabled` exists as a seed), and anti-noise rules — a product decision, not a view |
| Order Operations Analysis workspace (payment / COD / fulfillment lifecycle over the order-binding population, with the region-L definitions) | **Next small enhancement** (after slice 3) | The detailed order population the dashboard's region L summarizes and routes to; binding list views + saved filters exist today, an umbrella action + lifecycle filters is view work; COD amounts stay excluded until the numeric projection exists |
| Custom report builder · per-module dashboards · analytics warehouse · drag-and-drop widgets · scheduled PDF packs · AI recommendations · forecasting · advanced financial reporting | **Reject as unnecessary** | Out of connector scope; maintenance and truthfulness liabilities; contradicts the restrained-premium direction |

### 14.1 Shopify Sales Analysis — feasible data source (correction B)

The earlier draft simultaneously claimed "no new model / no schema change"
and a native sales report, while the money snapshots are `Char` and no
groupable store dimension existed on Odoo's sales reporting source. That
contradiction is resolved as follows:

- **Source**: extend Odoo's established sales-analysis projection
  `sale.report` — `[Fact]` a `_auto = False` SQL view over
  `sale_order_line`/`sale_order` with documented extension seams
  (`_select_additional_fields()`, `_from_sale()`, `_group_by_sale()`;
  odoo/odoo@19.0 `addons/sale/report/sale_report.py`, accessed 2026-08-01)
  — with the connector store dimension
  `shopify_connector_store_id` **derived from the protected stored order
  link created in slice 1** (§6.1), plus the two exclusion mirrors.
- **Values**: the report's existing stored **numeric** measures
  (`price_total`, `price_subtotal`, `product_uom_qty`, `qty_delivered`,
  `qty_invoiced`) — never the binding's `Char` snapshots.
- **Same truth rules as Store 360**: report domain adds
  `shopify_connector_store_id != False`,
  `shopify_connector_cancelled_at = False`,
  `shopify_connector_quarantined = False`; date = `date` (the projection of
  `date_order`); company isolation via the report's native company field +
  rules.
- **No double-counting / measure semantics**: `sale.report` is
  **line-grain**. Product groupings sum line measures (safe). The native
  `nbr` measure is a **line count and is labelled as such**; an
  order-count measure is NOT synthesized at line grain (summing per-line
  order values would double-count) — exact order counts remain the
  dashboard/workspace's order-grain surfaces, and the report's docs/labels
  state this distinction (correction B requirement).
- **Views**: list, graph (bar/line), pivot — truthful because every measure
  is a line-grain numeric.
- **Security**: `sale.report` keeps its native ACL/record-rule posture (it
  is Odoo's own sales reporting surface); slice 3 tests verify
  restrictive-rule and multi-company behaviour on the extended view before
  acceptance, alongside the §8 suite.
- **Migration/upgrade**: the view is rebuilt on module upgrade (standard
  for `_auto = False` reports); the extension rides `sale.report`'s
  documented seams, so version upgrades carry it like any report
  extension. Classification: **reporting backend enhancement** — never
  again described as zero-schema work.

## 15. Functional and technical gap registers (correction addendum §G)

Classification vocabulary: **[design-fixed]** corrected in this design
revision · **[prereq]** backend prerequisite for Store 360 implementation ·
**[mvp-improvement]** separate MVP improvement · **[later]** deliberate
later enhancement · **[rejected]** unsupported and rejected. Prioritized
top-down within each register.

### 15.1 Functional gaps (merchant-visible)

| # | Gap | Classification |
| --- | --- | --- |
| G-F1 | No commercial/lifecycle surface at all on the shipped dashboard | **[design-fixed]** — this concept |
| G-F2 | Customer-delivery visibility (Delivered / Not delivered / carrier progress / delivery failures) does not exist | **[prereq for any delivery UI — later enhancement for Store 360]**: A5 FulfillmentEvent ingestion + rollup writer (spec §7.5); Store 360 ships without delivery claims |
| G-F3 | Pending-payment orders whose wait expired are silently `skipped` — a merchant has no "expired, decide manually" queue | **[mvp-improvement]** (surface exists: skipped jobs with `payment_pending_expired` detail; needs a saved filter/action, no schema) |
| G-F4 | COD collection amounts / outstanding value not reportable | **[later]** — needs the numeric projection (spec §7.4); until then counts only |
| G-F5 | COD dispatch/delivery stages absent (`not_dispatched` only) | **[later]** — lifecycle writer |
| G-F6 | Collection-discrepancy alerting absent (state exists, never written) | **[later]** — same writer family as G-F4 |
| G-F7 | General gateway mix reporting (which PSPs drive sales) | **[rejected]** for the dashboard; revisit only with a stored gateway dimension |
| G-F8 | Exact historical-coverage boundary ("orders before X not imported") | **[later]** — stored boundary event (spec §8.12); cautious copy ships now **[design-fixed]** |
| G-F9 | Refund-adjusted sales ("Net sales") | **[later]** — refund/edit import is a product-scope decision (§7.2) |
| G-F10 | Paid-order fulfillment aging has no SLA semantics | **[design-fixed]** as elapsed-age-only display; a *named configurable threshold* is **[later]** |

### 15.2 Technical gaps (evidence and platform)

| # | Gap | Classification |
| --- | --- | --- |
| G-T1 | Raw-SQL aggregate design bypassing sale record rules (this handoff's earlier §6) | **[design-fixed]** — withdrawn, replaced by the stored-projection + rule-respecting grouped-read architecture |
| G-T2 | No groupable store dimension on sale documents / sales reporting source | **[prereq]** — slice-1 projection fields + backfill (§6, §11) |
| G-T3 | Incomplete payment-gateway persistence (non-manual gateway names not stored) | **[later]**; region L uses only the sanctioned manual-gateway fields |
| G-T4 | `Char` COD monetary values (three of five literal `'0'`) | **[prereq for COD amounts]** — protected numeric fields + migration + reconciliation tests; never aggregate Char **[design-fixed as a ban]** |
| G-T5 | Payment/collection evidence freshness bounded by scan window + refresh triggers; no dedicated payment-evidence cron | **[design-fixed as disclosure]** (L2 caption); a dedicated refresh cadence is **[later]** |
| G-T6 | `delivered_inconsistency`, `delivered_not_validated`, `unknown_status_value` reasons defined but never written | **[later]** — part of the delivery-evidence enhancement; dashboard must not render them meanwhile **[design-fixed]** |
| G-T7 | External-fulfillment coverage depends on scan observation cadence (`fulfillment_last_reconciliation_at` watermark) | **[design-fixed as disclosure]** — fail-closed watermark already exists; L4 caption names the freshness anchor |
| G-T8 | Partial / multi-fulfillment roll-up for *delivery* (per-order "delivered" across N fulfillments) | **[later]** — depends on G-T6; order-fulfillment rollup itself is supported today via Shopify's own snapshot **[design-fixed]** |
| G-T9 | Multiple transactions per order: only manual SUCCESS/PENDING transactions are classified; presentment-currency collected amounts excluded from collection math (importer:2137-2143) | **[design-fixed as disclosure]** in L3 definitions; richer transaction persistence **[later]** |
| G-T10 | Cancelled/refunded orders live outside ordinary import (skips/review) | **[design-fixed as disclosure]** — counts of skipped work stay job-side (G/F), never faked as order rows |
| G-T11 | Count/amount double-counting risks (line grain vs order grain; multi-fulfillment) | **[design-fixed]** — L4 uses Shopify's order-level rollup; sales report keeps line-grain measures labelled as such (§14.1) |
| G-T12 | Multi-store/company isolation for the new commercial reads | **[prereq]** — §8 adversarial suite mandatory for slice 1 |
| G-T13 | Mixed currency across stores | **[design-fixed]** — never combined; per-store rows (spec §3) |
| G-T14 | Unknown Shopify enum values | **[design-fixed upstream]** — fail-closed import/refresh; `schema_warning` evidence surfaced as an L7 exception |
| G-T15 | Migration/backfill for the projection | **[prereq]** — §11 |
| G-T16 | Restrictive ACL / record-rule behaviour of the aggregate | **[prereq]** — §6.5/§8; count/domain agreement extends to restricted users |
| G-T17 | Exact count-to-drill-down agreement for every new number | **[prereq]** — existing invariant extended (tests §10.2/§10.8) |

## 16. Verification summary (correction session's prototype)

Full measured record: spec §13. Chromium 141.0.7390.37; **eight** committed
screenshots (six full-page + two lifecycle element captures); eleven runs
including 320 px reflow and 200 % zoom (683 CSS px). Per-run DOM facts:
`scrollWidth == innerWidth` at 1366/768/683/390/320 (no horizontal page
overflow anywhere), zero clipped-text elements outside sanctioned scroll
containers, 5/5 flow drill-downs visible per state, keyboard reaches the
last flow drill-down in 16–44 real Tab presses with a 2 px solid `#175CD3`
`:focus-visible` outline, reduced-motion collapses every transition, and
every run issued exactly two `file://` requests — zero network. New in this
correction: **fixture arithmetic is machine-checked from the rendered DOM**
(trend sums = KPIs, shares = goods-subtotal basis, flows+disclosed remainder
= backlog, lifecycle buckets = order count, store rows = combined totals —
all pass in healthy, attention AND the Arabic state); the **mobile Stores
region is stacked cards** with both primary Open actions measured fully
inside the 390 px viewport (and at 320 px); chart axis labels compute to an
effective 9.9 px at 390 px with no SVG clipping and the hatched
incomplete-period bar visible; and the **RTL baseline is a representative
Arabic state** (`lang="ar"`, mirrored geometry measured, `<bdi>`-isolated
values — the KPI delta reads `+4.1%` with the sign leading). Static
prototype verification only — no Odoo browser/tour test is claimed.

## 17. Not claimed

No implementation, no production file touched, no PR opened or modified, no
PR #204 change, no Odoo.sh or Shopify contact, no credential access, no test
executed against Odoo, no issue action, no acceptance, no ready-marking, no
merge. This concept awaits control-room disposition.
