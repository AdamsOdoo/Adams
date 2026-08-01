# Shopify Store 360 — Implementation Handoff (2026-08-01)

> **Status: Design-concept handoff. NOT implemented, NOT accepted, NOT
> scheduled.** Produced on the isolated branch `fable/ui-operations-360-concept`
> from the exact PR #204 head `a1c593183f6aaa1238e87486ca518717cefc53a9`.
> Nothing under `addons/**` changed in this session; PR #204 is untouched.
> Implementation may begin only when the control room authorizes it as a
> wave/batch under CLAUDE.md §13, with its own allowed-files packet,
> independent review and runtime evidence. This document is the input to that
> packet, not a substitute for it.

Normative companions:
[product spec](../02-product/ui-operations-360-dashboard-spec-2026-08-01.md)
(information architecture §3, metric gate §6, truth rules §7, verification
record §13) ·
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
spec §3 decision order; store + period + comparison controls added to the
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

Spec §3, regions A–H in decision order (header → conditional critical status
→ KPI cards → bridge → trend + top products → connector health → multi-store)
with the cross-currency rule (never combine currencies; per-store rows
instead) and the three distinguishable empty-state variants (spec §9.4). The
prototype demonstrates all of it; the committed screenshots and DOM
verification record (spec §13) are the visual acceptance baseline.

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
| E2 | Share of imported sales (per top product) | How concentrated were sales? | derived E1 value / C1-untaxed-basis | as E1; denominator = SUM `price_subtotal` over all C4 lines | ratio | as C1 | as C1 | Hidden when denominator 0 | inherits bridge | n/a (cell) | **Yes** (derived; same-basis numerator/denominator) |
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

**Commercial metric decision table** (correction-mandated classification;
rationale in spec §7.2): Sales value → *include with truthful renamed label*
("Imported Shopify sales"); order count, AOV, units sold, period comparison,
sales trend, top products, freshness/completeness → *include now*; refunds /
returned value → *defer* (no refund records exist anywhere); "Net sales"
(Shopify definition) and cross-currency combined totals → *requires backend
enhancement*; taxes/shipping decomposition and discount value → *defer to the
native Shopify Sales Analysis report*.

## 6. Backend contract changes required

All inside `shopify.connector.ui.dashboard` (AbstractModel — no table, no
ACL row), slice 1:

1. **New RPC** `get_store_360_data(store_id=None, period='7d')` (or a
   versioned successor of `get_dashboard_data`). Validated inputs: `period ∈
   {'24h','7d','30d'}`; `store_id` must be a store the caller can read;
   `None` = all readable stores. Response adds `commercial`, `bridge`,
   `flows`, `stores` blocks and echoes `period`, `generated_at`,
   `refresh_interval_seconds`.
2. **Commercial aggregates need a cross-model join** (binding →
   `sale.order` / `sale.order.line`), which `read_group` cannot express.
   Recommended: **parameterized read-only SQL** inside this one service,
   with the guard suite extended rather than weakened — the AST guard
   currently treats any `execute` as forbidden; it gains a narrow, tested
   allowance for this model only: statements must be SELECT-only, literal
   (no string interpolation of user input; parameters only), and each query
   must embed the isolation predicates (below). Alternative (rejected for
   slice 1, kept as fallback): a stored related `store_id` on `sale.order` —
   rejected because the connector deliberately does not extend `sale.order`
   today and a schema change + backfill migration is a heavier, product-level
   decision.
3. **Isolation predicates in every commercial statement** (raw SQL bypasses
   record rules, so they are mirrored explicitly): `binding.company_id IN
   allowed_companies`, `binding.sec3_scope_quarantined = FALSE`,
   `binding.store_id` term, `so.company_id` match, plus a preliminary
   `check_access_rights('read')` + rule probe on `sale.order` /
   `sale.order.line`; an `AccessError` degrades the commercial block to the
   `no_permission` empty variant — never a zero.
4. **Bridge + flow counters** are ORM `search_count` / two `read_group`
   calls grouped by `job_type` mapped to the five families (exact type lists
   in table row F6) — constant query count.
5. **Per-store block**: one `read_group` per measure grouped by `store_id`;
   no per-store loops.
6. Attention builder gains the two new decision sources (match decisions,
   awaiting-configuration jobs), preserving the count=domain invariant.

No new model, no new stored field, no ACL change, no cron change, no
Shopify request, no credential read. The dashboard stays read-only.

## 7. Bounded query / performance implications

- Total per render: the existing constant set plus ~8 bounded statements
  (4 commercial SUM/COUNT windows incl. previous period, 1 trend GROUP BY
  bucket ≤31 rows, 1 top-products LIMIT 5, 2 family read_groups) and ≤3
  per-store read_groups. Constant in data volume; result sets capped by
  construction (5 products, 8 activities, 3 exceptions, ≤31 buckets).
- Supporting indexes already present at `a1c5931`:
  `binding.sale_order_id`, `binding.store_id`, `binding.company_id`,
  `sale.order.line.shopify_line_item_gid`, job `state/job_type/store_id`.
  `[Open question]` whether `sale_order.date_order` needs a dedicated index
  at target volumes — measure first (see test plan); an index would be a
  small migration, not a redesign.
- Perf evidence requirement: extend `tools/perf0_baseline.py` with a
  `store_360_aggregate` scenario (seeded ≥50k orders / ≥100k jobs) and keep
  the PB-9/10/11 constant-query assertions in `test_ui_performance.py`
  green for the new RPC.

## 8. Security and company-isolation implications

- Runs as the calling user; auditor-floor `AccessError` gate retained.
- Raw-SQL record-rule bypass is handled by explicit mirrored predicates +
  access pre-checks (above) — this is the single riskiest element of the
  design and gets its own adversarial tests (cross-company store, quarantined
  binding, multi-company user, user without sale access).
- Payload discipline unchanged: aggregates, labels, product display names
  and store names only — no customer PII, no payloads, no stack traces, no
  credentials; the recursive forbidden-key/email walk test extends to the
  new blocks.
- Commercial block honestly absent (not zeroed) for roles without
  `sale.order` read.

## 9. Expected production files (later implementation)

- `addons/shopify_connector_core/models/shopify_connector_ui_dashboard.py` — extend (slice 1).
- `addons/shopify_connector_core/tests/test_ui_dashboard.py`,
  `test_ui_performance.py`, `test_ui_source_guards.py` — extend (slice 1).
- `tools/perf0_baseline.py` — add scenario (slice 1).
- `addons/shopify_connector_core/static/src/js/shopify_connector_dashboard.js`,
  `static/src/xml/shopify_connector_dashboard.xml`,
  `static/src/scss/shopify_connector_dashboard.scss`,
  `static/tests/shopify_connector_dashboard.test.js` — extend/replace (slice 2).
- `docs/06-prompts/ui-store-360-copy-deck.md` — new (slice 2).
- Slice 3: `views/` + menu records for "Sync Operations Analysis"
  (graph/pivot/list on `shopify.connector.job`) in core and "Shopify Sales
  Analysis" actions in `shopify_connector_sale`; no new models.
- Module version bumps + (only if measurement demands an index or option (b)
  is chosen) a `migrations/` script.

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
6. **Perf**: scenario at seeded volume; constant-query assertion.

## 11. Migration impact

Slices 1–2: none — no schema change, no data migration; module version bump
only (same-version `-u` adds nothing; genuine upgrades run no scripts for
this feature). Slice 3: none (views/actions only). Conditional: one small
index migration if §7's open question resolves that way; option (b) stored
field would need a backfill migration — currently rejected.

## 12. Rollback plan

Each slice is independently revertable: revert the slice's merge commit and
warm-`-u` the module — slice 1 removes only the added RPC surface (no table,
no rows), slice 2 restores the previous dashboard assets (client action tag
unchanged), slice 3 removes the report actions/menus. No durable state is
created by any slice, so no data cleanup is ever needed.

## 13. Implementation slices (no more than three; not started)

1. **Truthful aggregate contract** — the `get_store_360_data` payload, SQL
   allowance + guards, correctness/security/perf tests. Deliverable is
   invisible to users (old UI still renders). *Estimate: medium batch.*
2. **Responsive presentation and drill-down** — Owl template/SCSS per the
   committed prototype, all drill-downs (incl. server-built top-product line
   domains), copy deck, HOOT + tours + full browser/RTL/zoom campaign.
   *Estimate: large batch (the visual acceptance baseline is the committed
   screenshot set).*
3. **Native reports and final validation** — "Sync Operations Analysis"
   (list/graph/pivot over jobs: store, flow family, state, source, period;
   direct navigation to failed/delayed work) and "Shopify Sales Analysis"
   (list/graph/pivot over binding-scoped orders/lines using the same §5
   definitions; store/product/period filters), plus the closing validation
   campaign. *Estimate: medium batch.*

## 14. Other UI / reporting recommendations, classified

| Candidate | Classification | Reason |
| --- | --- | --- |
| Sync Operations Analysis (native graph/pivot/list over `shopify.connector.job`) | **Include with dashboard** (slice 3, highest reporting priority) | Jobs model natively supports Count-measure graph/pivot today; zero schema work; answers the drill-deeper need the dashboard creates |
| Shopify Sales Analysis (native list/graph/pivot with the approved metric definitions) | **Include with dashboard** (slice 3) | Same truth rules as the cards; gives XLSX export and ad-hoc grouping without a custom builder |
| Data Readiness surface (unresolved matching/mapping/decision work with direct fixing navigation) | **Next small enhancement** | Building blocks exist (match-decision action, awaiting-configuration action, first-push guard queue); an umbrella menu + saved filters, no new models |
| Store Health list enrichment (connection, last processing, backlog, failures as store list columns/filters) | **Next small enhancement** | Computed store projections exist; N+1 compute fields need care in list context |
| Configurable notifications (final failure, stale queue, reconnect required) | **Later** | Needs channel/framework decisions (activities vs mail), per-store settings design (`notification_default_enabled` exists as a seed), and anti-noise rules — a product decision, not a view |
| Custom report builder · per-module dashboards · analytics warehouse · drag-and-drop widgets · scheduled PDF packs · AI recommendations · forecasting · advanced financial reporting | **Reject as unnecessary** | Out of connector scope; maintenance and truthfulness liabilities; contradicts the restrained-premium direction |

## 15. Verification summary (this session's prototype)

Full measured record: spec §13. Chromium 141.0.7390.37; six committed
screenshots; per-run DOM facts: `scrollWidth == innerWidth` at 1366/768/390
(no horizontal page overflow), zero clipped-text elements outside sanctioned
scroll containers, 5/5 flow drill-downs visible per state, keyboard reaches
the last flow drill-down in 16–26 real Tab presses with a 2 px solid
`#175CD3` `:focus-visible` outline, RTL genuinely mirrors (accent border
side + header geometry measured), reduced-motion collapses every transition,
and every run issued exactly two `file://` requests — zero network. The
attention state carries icon + kind chip + owner text on every item, so it
survives with colour removed.

## 16. Not claimed

No implementation, no production file touched, no PR opened or modified, no
PR #204 change, no Odoo.sh or Shopify contact, no credential access, no test
executed against Odoo, no issue action, no acceptance, no ready-marking, no
merge. This concept awaits control-room disposition.
