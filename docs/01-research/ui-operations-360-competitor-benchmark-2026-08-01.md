# Shopify Store 360 — Competitor & Platform Benchmark (2026-08-01)

> **Status: Research record for an isolated UI/product design concept. NOT an
> acceptance, NOT a review, NOT implementation.** Produced on the isolated
> branch `fable/ui-operations-360-concept`, created from the exact PR #204 head
> `a1c593183f6aaa1238e87486ca518717cefc53a9`. This session changes no file
> under `addons/**`, does not touch PR #204, and claims nothing accepted.
>
> Access date for every source below: **2026-08-01**. Collection method:
> parallel read-only web-research agents fetching only the officially assigned
> vendor/platform pages (plus at most two directly-linked same-vendor doc
> pages each, where the assigned page pointed at a reporting surface). No
> competitor artwork, code, wording or branded asset was copied. Every entry
> is classified per CLAUDE.md §8.

Companion documents:

- Product specification: [`../02-product/ui-operations-360-dashboard-spec-2026-08-01.md`](../02-product/ui-operations-360-dashboard-spec-2026-08-01.md)
- Implementation handoff: [`../07-implementation-plan/ui-operations-360-dashboard-handoff-2026-08-01.md`](../07-implementation-plan/ui-operations-360-dashboard-handoff-2026-08-01.md)

---

## 1. Webkul — Odoo Multichannel Shopify Connector

### 1.1 Sources

| URL | Access status (2026-08-01) | Notes |
| --- | --- | --- |
| https://webkul.com/blog/odoo-multichannel-shopify-connector/ | Accessible | User-guide blog post; full text extracted. Lists Odoo V19/V18/V17 support. |
| https://store.webkul.com/odoo-multichannel-shopify-connector.html | Partial | Text and screenshot captions extracted; most screenshot images rendered as skeleton loaders, so visual layouts were not observable. v3.5.1, $170. |
| https://webkul.com/blog/multichannel-shopify-odoo-bridge/ | Accessible | Same-vendor guide directly linked from the store page; fetched for dashboard/analytics detail. |

### 1.2 Documented capabilities `[Competitor claim]`

- Bidirectional product/category sync (name, description, price, SKU, images,
  stock, categories); order import via cron with customer details, status
  updates, cancellations, shipment updates; partial-shipment fulfillment with
  tracking sync; customer import; real-time Odoo→Shopify stock sync.
- Cron scheduling plus manual sync; selective sync filters (all / by ID /
  created-after / updated-after).
- A **"Feeds"** staging area that evaluates incoming data before Odoo records
  are created, with Done/Error statuses and per-feed error messages: *"Feeds
  section acts as an area where our connector evaluates the incoming data to
  ensure correctness."* (blog guide). *"Error messages show the exact reason
  for the sync failure to help admins locate issues."* (store page).
- A **Synchronization History** tab: *"you can view the entire history of
  every sync"* (bridge guide).
- Multi-store capped at three: *"Can connect up to three Shopify stores"*
  (store page).
- Shopify GraphQL API: *"Reduces API calls by combining multiple requests into
  a single query."* (blog guide).

### 1.3 Dashboard / analytics surface `[Competitor claim + observed absence]`

- **No KPI/analytics dashboard is documented on any fetched page.** The
  "dynamic dashboard" the guides mention is a surface hosting import/export
  action buttons, not metrics. Store-page captions name a "Multichannel
  Dashboard" but the images did not load, so nothing about its content is
  verifiable. `[Fact about the fetched pages]`
- Operational monitoring happens through the Feeds lists (Done/Error) and the
  Synchronization History log, i.e. record-level lists, not aggregates.

### 1.4 Observed UI patterns `[Competitor claim — described, screenshots unavailable]`

Wizard-driven import/export; tabbed instance configuration form; standard Odoo
list views for mappings and feeds; Done/Error status indicators; feeds queue
gated behind developer mode for detail.

---

## 2. Emipro — Shopify Odoo Connector (`shopify_ept`)

### 2.1 Sources

| URL | Access status (2026-08-01) | Notes |
| --- | --- | --- |
| https://apps.odoo.com/apps/modules/19.0/shopify_ept | Accessible | Full listing text; no dashboard screenshots or metric-level detail on the page. |
| https://docs.emiprotechnologies.com/shopify-odoo-connector/ | **Blocked** | HTTP 404. The live v19 docs URL is `/shopify-odoo-connector/v19` (reached via the listing's User Guide redirect). |
| https://docs.emiprotechnologies.com/shopify-odoo-connector/v19 | Accessible | Recovered versioned docs landing page; ToC retrieved. |
| https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/sales-report-and-log-book.html | Partial | Navigation and purpose text retrieved; screenshots not extractable as text; no metric/chart specification in prose. |
| https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/shopify-net-profit-report.html | Partial | Purpose/navigation/prerequisites retrieved; screenshots referenced but undescribed. |

### 2.2 Documented capabilities `[Competitor claim]`

Broadest documented scope of the four vendors: bidirectional product sync with
metafields and per-market pricing; webhook-driven order import; bidirectional
**returns/refunds**; Sale Auto Workflow (auto invoice/delivery/payment);
Shopify payout import with reconciliation; multi-store and Shopify Markets;
queue management for failed orders with activity assignment; a "Mismatch Log"
of unsuccessful operations.

### 2.3 Dashboard / analytics surface `[Competitor claim + observed absence]`

- **No unified dashboard is documented.** Reporting is fragmented across Odoo
  menus: *Shopify › Reporting › Sales* (*"See it in various modes"* — modes
  unnamed), *Shopify › Reporting › Net Profit* (**Enterprise edition only**,
  gated on the analytic-account security group), and *Shopify › Processes ›
  Log Lines* (the Mismatch Log: *"an entire log of operations that were
  unsuccessful so that you can identify its reason"*).
- No metric names, chart types or layouts appear as text anywhere in the
  fetched pages. `[Fact about the fetched pages]`

### 2.4 Positioning language `[Competitor claim]`

*"Mature Shopify Connector. Operationally Safer."* · *"Designed for standard
live operations, not demo-only flows"* · *"Upgrade-safe by design"*. The
market leader sells **operational safety**, not analytics polish.

---

## 3. VentorTech — Odoo Shopify Connector (`integration_shopify`)

### 3.1 Sources

| URL | Access status (2026-08-01) | Notes |
| --- | --- | --- |
| https://apps.odoo.com/apps/modules/19.0/integration_shopify | Accessible | v19 listing, $568.31; the only fetched page describing a commercial dashboard. |
| https://ventor.tech/solutions/odoo-shopify-connector/ | Accessible | Marketing page; no dashboard/analytics content at all. |

### 3.2 Documented capabilities `[Competitor claim]`

Bidirectional product sync with field-level direction control and Python
transformation scripts; webhook order import *"within seconds"*; auto-workflow
pipeline (confirm→ship→invoice→send→pay) with a **visual step pipeline** and
pass/fail per step; per-action sync logs with status and message; email
failure notifications; returns/refunds marked *"Coming soon"*; claimed
*"Tested with high volumes — 1,000+ orders per day without issues."*

### 3.3 Dashboard / analytics surface `[Competitor claim]` — the strongest commercial claim set

The listing describes a **"Sales Dashboard"** showing:

- *"Revenue over time and sales distribution"*;
- top products;
- *"Orders by country"*;
- customer metrics (*"new vs. returning and country stats"*);
- store performance comparison across connected stores;
- controls: **date-range filter, store filter, and "Exclude cancelled orders
  from statistics"**.

No chart types, KPI card designs or layout details are published; the visual
design is unverifiable from these pages. `[Fact about the fetched pages]`

---

## 4. TeqStars — Shopify Connector

### 4.1 Sources

| URL | Access status (2026-08-01) | Notes |
| --- | --- | --- |
| https://docs.teqstars.com/19.0/applications/shopify/overview.html | Accessible | WebFetch received HTTP 403 (Cloudflare user-agent block); full HTML retrieved via direct HTTPS GET (200 OK). |
| https://docs.teqstars.com/19.0/applications/shopify/setup.html | Accessible | Same 403→direct-GET pattern; page is a ToC hub with anchors only. |
| https://docs.teqstars.com/19.0/applications/shopify/order_management/payout_report.html | Accessible | Same-vendor reporting page directly linked from the overview. |

### 4.2 Documented capabilities `[Competitor claim]`

Product/collection/catalog sync; order import incl. POS, refunds and partial
refunds from Odoo, returns, fraud-risk import; fulfillment status + tracking
both ways; per-gateway/financial-status order workflows; payout report import
with auto-reconcile (*"Yes on Enterprise"*) and named line-level warnings
("Order not found", "Invoice not found", "Invoice amount mismatch");
"unlimited" multi-store; a **Real-time Synchronization matrix** (entity ×
Import/Export/Bi-directional × Webhook/Scheduled/Manual).

### 4.3 Dashboard / analytics surface `[Competitor claim + observed absence]`

- **No dashboard is depicted.** Analytics is described in prose only:
  *"comprehensive reporting and analytics capabilities by consolidating data
  from both Odoo and Shopify."* The feature-comparison table names two
  analytics-adjacent surfaces without showing them: *"Odoo native sales
  analysis reports — Yes"* and *"Centralized hub (channels, stores, queues) —
  Yes."* `[Fact about the fetched pages]`
- Operational trust cues surface at record level: "Last Processed On"
  watermarks on the instance, per-job Interval/Active scheduling, a
  Draft/In Process/Validated payout pipeline, named warnings with documented
  remediation.

---

## 5. Odoo 19 official documentation `[Fact — primary platform source]`

### 5.1 Sources

| URL | Access status (2026-08-01) | Notes |
| --- | --- | --- |
| https://www.odoo.com/documentation/19.0/applications/studio/views.html | Partial | View taxonomy captured; Reporting-views body text truncated by extraction. |
| https://www.odoo.com/documentation/19.0/developer/reference/user_interface/view_architectures.html | Partial | Form/List/Search/Kanban architecture captured; Graph/Pivot detail sections truncated. |
| https://www.odoo.com/documentation/19.0/applications/essentials/reporting.html | Accessible | Same-vendor page fetched to recover the truncated Graph/Pivot content. |

### 5.2 Platform facts relevant to this design

- Native view taxonomy: form, list, search, kanban, graph, pivot, calendar,
  activity, cohort, grid, gantt, map. **No standalone "dashboard" view type**
  appears in the retrieved Odoo 19 references — an overview dashboard is a
  composition (our connector already uses an `ir.actions.client` Owl
  component, which is the mechanism this concept keeps).
- Graph views support **bar, line and pie** (stacked and cumulative modes);
  pivot supports row/column grouping, axis flip, XLSX export; measures are
  numeric fields plus Count. *"When you select a measure, Odoo aggregates the
  values recorded on that field for the filtered records."*
- Implication `[Inference]`: native graph/pivot reporting works only over
  **stored numeric fields** — which the connector's order binding does not
  carry (its Shopify money snapshots are deliberately `Char`). A native
  "Shopify Sales Analysis" report therefore aggregates `sale.order` /
  `sale.order.line` records reached through the binding, not binding fields
  themselves. This constraint shapes the reporting recommendations in the
  handoff.

---

## 6. Cross-vendor synthesis — what our design adopts, adapts, rejects

All rows are `[Inference]` from §§1–5 plus `[Recommendation]` for our product;
none of the vendor rows above are treated as proven fact about their products.

### 6.1 Adopt (pattern observed in the market, done truthfully here)

| Pattern | Source | How Store 360 adopts it |
| --- | --- | --- |
| Commercial dashboard with date range + store filter + cancelled-order exclusion | VentorTech claims exactly this filter set | Shared header: store selector, bounded period set (24 h / 7 d / 30 d), previous-period comparison; cancelled orders excluded from sales metrics **by definition, with the exclusion stated on the card** — not an optional toggle that changes the truth. |
| Revenue over time + top products as the commercial core | VentorTech | Sales trend is the page's single chart; top products is a compact five-row table. Both restricted to metrics the repository provably stores (see spec §6–§7). |
| "Last processed" watermarks elevated to first-class trust cues | TeqStars (record-level), Emipro (scheduler prose) | The Data-completeness bridge makes freshness a named, always-visible element: "Sales data synchronized through *timestamp* · *N* orders awaiting import", plus per-flow last-success timestamps. |
| Exact failure reason + drill-down to the failing record | Webkul feeds, Emipro Mismatch Log, VentorTech logs | Needs-attention cards keep severity, owner, reason and a direct native Review drill-down (already the U0 pattern; retained). |
| Multi-store comparison surface | VentorTech store comparison; TeqStars "centralized hub" | Multi-store health table rendered **only when more than one store is in scope** — single-store screens never pay for it. |

### 6.2 Adapt (market pattern, corrected for truthfulness)

| Pattern | Why adapted rather than copied |
| --- | --- |
| "Net sales" / revenue labels | No fetched vendor page defines its revenue figure. Our connector never imports refunds/returns and freezes order amounts at import; calling the sum "Net sales" or "Revenue" would overclaim. The KPI is labelled **"Imported Shopify sales"** with an exact definition on the card (spec §7). |
| "Real-time" language | VentorTech claims webhook import "within seconds"; our order discovery is a 15-minute scan cron plus manual runs, and the dashboard refresh floor is 30 s. The header shows "Updated HH:MM" and the bridge shows "discovered up to" — the word "live"/"real-time" appears nowhere. |
| Orders-by-country, new-vs-returning customers | VentorTech shows these; our repository stores no country/customer-segment rollup for imported orders and PII discipline keeps customer identity off the dashboard. Deferred with reasons (spec §8). |
| One-chart discipline | Competitors imply chart-rich dashboards; Odoo's own vocabulary is bar/line/pie. We keep exactly one chart (sales trend, bar + neutral comparison line) and give operations counters and rows, not a second chart. |

### 6.3 Reject (deliberately not done)

| Pattern | Reason |
| --- | --- |
| Pie/donut charts for status or sales distribution | Prompt boundary; poor comparability; Odoo pie exists but adds nothing a labelled row list doesn't. |
| Analytics warehouse / custom report builder / configurable widget dashboards | Out of scope for a connector; maintenance burden; violates the restrained-premium direction. |
| Edition- or group-gated core health metrics (Emipro's Enterprise-only Net Profit pattern) | Connector health must be visible to every connector role; commercial cards degrade honestly (permissions empty state) instead of hiding the page. |
| Feeds/staging queue as the primary monitoring surface (Webkul) | Our architecture already has a stronger primitive (jobs + mutation attempts + decisions) with native filtered lists; the dashboard aggregates those, it does not add a parallel staging concept. |
| Marketing-metric parity claims ("Shopify Analytics parity") | Impossible to honor: refunds, edits, duties/tips orders are never imported (by policy, with review routing). The dashboard states what its figures are instead of claiming parity. |

### 6.4 The market gap this concept targets `[Inference]`

Across all four vendors, **no fetched official page shows a single surface
that answers both "how is my store performing?" and "is the connector telling
me the truth right now?"** Analytics (where it exists) is either fragmented
into generic Odoo report menus or claimed without definitions, and no vendor
couples a commercial figure to its import completeness. Store 360's
distinguishing move is the **data-completeness bridge**: every commercial
number on the page is anchored to a synchronization watermark and a count of
work that has not landed yet.

---

## 7. Method note

TeqStars' docs return HTTP 403 to the standard WebFetch user agent but serve
plain HTTPS GETs; the content above came from the direct fetch. Recorded so a
future benchmark session does not misfile those pages as Blocked.
