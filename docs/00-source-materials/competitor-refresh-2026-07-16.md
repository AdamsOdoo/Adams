# Competitor & Premium-UX Benchmark Refresh (2026-07-16)

> **Capture file** per `docs/00-source-materials/README.md`. Refreshes the
> 2026-06-30/07-01 competitor corpus (re-verified 2026-07-04) with current
> listings, pricing, reviews, and COD/fulfillment/reconnect coverage, plus a
> premium-UX evidence pass. Two parallel research passes, 2026-07-16. Every
> capability statement is classified: [Vendor claim] / [Documented workflow]
> / [Review claim] / [Inference] / [Fact] / [Unverified]. **No screenshots
> could be rendered in this environment** — no "observed screenshot" class is
> used in this refresh; screenshot-described items are labelled
> [Documented workflow — screenshot described, not independently observed].
> Conclusions/deltas land in `../01-research/competitor-feature-matrix.md`,
> `competitor-deep-dives.md`, and `ux-ui-benchmark.md` (dated delta
> sections). Closes gap R-4 of `../01-research/mvp-remaining-gap-inventory.md`.

## Source register (all accessed 2026-07-16)

| # | Source | URL | Access |
|---|---|---|---|
| S1 | Webkul store listing | https://store.webkul.com/odoo-multichannel-shopify-connector.html | Accessible |
| S2 | Webkul user-guide blog | https://webkul.com/blog/odoo-multichannel-shopify-connector/ | Accessible |
| S3 | Odoo Apps — Webkul `shopify_odoo_bridge` (18.0 listing) | https://apps.odoo.com/apps/modules/18.0/shopify_odoo_bridge | Accessible |
| S4 | Odoo Apps — Emipro `shopify_ept` 19.0 | https://apps.odoo.com/apps/modules/19.0/shopify_ept | Accessible |
| S5 | Emipro docs v19 TOC | http://docs.emiprotechnologies.com/shopify-odoo-connector/v19/ | Accessible |
| S6 | Emipro docs — Financial Status (v16 page; v19 URL 404) | https://docs.emiprotechnologies.com/shopify-odoo-connector/v16/sale-auto-workflow-payment-gateway-and-financial-status-configurations/financial-status.html | Accessible |
| S7 | Emipro docs — Sale Auto Workflow (v17) | (docs.emiprotechnologies.com …/sale-auto-workflow.html) | Partial (snippets) |
| S8 | Odoo Apps — Teqstars `shopify` 19.0 | https://apps.odoo.com/apps/modules/19.0/shopify | Accessible |
| S9 | Teqstars docs 19.0 (overview, order_import, update_order_status) | https://docs.teqstars.com/19.0/applications/shopify/overview.html etc. | **Blocked — HTTP 403 (bot protection); snippets only → Partial** |
| S10 | Teqstars blog | https://teqstars.com/blog/integrations-5/odoo-shopify-integration-7 | Blocked (403) |
| S11 | Trustpilot — Emipro | https://www.trustpilot.com/review/emiprotechnologies.com | Partial (snippets) |
| S12 | Odoo Apps — VentorTech `integration_shopify` 19.0 | https://apps.odoo.com/apps/modules/19.0/integration_shopify | Accessible |
| S13 | ventor.tech connector page | https://ventor.tech/odoo-shopify-connector/ | Blocked (404); live page /solutions/odoo-shopify-connector/ surfaced via search — Partial |
| S14 | ecosystem.ventor.tech PRO product page | https://ecosystem.ventor.tech/product/odoo-shopify-connector-pro/ | Partial (snippets) |
| S15 | Odoo Apps — `ecommerce_shopify` 19.0 (vendor: Odoo IN Pvt Ltd) | https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify | Accessible |
| S16 | Odoo Apps — Softhealer `sh_shopify_connector` 19.0 | https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector | Accessible |
| S17 | Fanatics comparison article | https://www.fanatics.nl/blog/choosing-the-best-odoo-shopify-connector/ | Accessible |
| S18 | Polaris React | https://polaris-react.shopify.com/ | Accessible |
| S19 | Shopify App Home (Polaris web components) | https://shopify.dev/docs/api/app-home | Accessible |
| S20 | Celigo error-management docs | https://docs.celigo.com/hc/en-us/articles/360048814732-Intro-to-Error-Management | Blocked (403); snippets Partial |
| S21 | WCAG 2.2 | https://www.w3.org/TR/WCAG22/ + /WAI/WCAG22/quickref/ | Accessible |
| S22 | Apple HIG (accessibility, motion) | https://developer.apple.com/design/human-interface-guidelines/... | Partial (JS-rendered; body not extracted) |

## 1. Webkul — Odoo Multichannel Shopify Connector

- v3.5.1; Odoo 10.x–19.x; GraphQL "newly added" [Vendor claim, S1/S3]. Pricing: $170 (+$34 install; support 3 months incl.) on Webkul store [Vendor claim, S1]; $199.17 on Odoo Apps [Vendor claim, S3]. Requires base "multichannel sale" module [Vendor claim, S1].
- Order import filters: all / ID / date-updated-after / date-created-after [Documented workflow, S2]. **No financial-status gating and no COD handling documented** [Unverified — absence, S2]. Mandatory sequence categories → products → orders [Documented workflow, S2]. No auto-workflow engine documented [Inference from absence, S2].
- Inventory: uni-directional Odoo→Shopify real-time ("Auto Stock"), on-hand vs forecast choice, single default warehouse/location — **no genuine multi-location mapping documented** [Documented workflow + Inference, S2].
- Fulfillment: shipment status + "partial shipment and fulfillment tracking support" [Vendor claim, S1]; mechanics undocumented; Shopify→Odoo fulfillment import undocumented [Unverified].
- Error handling: "Feeds" staging layer — per-record failure reason, manual fix + re-evaluate; no automatic retry documented [Documented workflow, S2; Inference].
- Multi-store: "up to 3 connected stores by default" [Vendor claim, S3]. Reviews: 1 review on Webkul store (5.0); 3.5★ on Shopify App Store per S17 with cron-stock-sync criticism [Review claims, S1/S17].

## 2. Emipro — `shopify_ept`

- Odoo 8.0–19.0; **$627.18** one-time; ~280+ reviews (most-reviewed paid connector) [Fact from listing, S4]. 10h guided implementation; support for latest 3 versions via portal [Vendor claim, S4]; support beyond scope = paid package "$350 that expires in 15 days" [Review claim, S11].
- **Financial-status model (most explicit in market):** per-instance config maps **Financial Status + Payment Gateway → Auto Workflow + Payment Term** [Documented workflow, S6]; import types Unshipped/Partially Fulfilled/Shipped/Cancelled [Documented workflow, S5/S7]; instance creation auto-creates financial-status configs for last 30 days of fulfilled orders [Documented workflow, S6]; docs warn misconfiguration "causes operational problems" [Documented workflow, S6]. Auto Workflow options: Confirm Quotation; Create & Validate Invoice; Register Payment [Documented workflow, S7]. **COD handled only implicitly via gateway mapping; no dedicated COD doc found** [Inference + Unverified, S6].
- Inventory: export/import stock; Shopify location ↔ Odoo warehouse mapping; Free/On-hand/Forecasted export basis [Documented workflow/Vendor claim, S4/S5]. Fulfillment: tracking export ("Update Order Status"); partial shipments claimed; **inbound 3PL fulfillment not documented** [Vendor claim + Unverified, S4/S5]. Refunds: two-way returns/refunds, credit notes, restocking-aware [Vendor claim, S4]. **Payout report import + reconciliation** (differentiator) — but **not supported in multi-company Shopify Markets setups** [Vendor claims incl. stated limitation, S4].
- Queues: queue management, "Log Book" auditing, cron + HMAC webhooks [Documented workflow, S5]; retry granularity undocumented [Unverified].
- **Review complaints [Review claims, S4/S11]:** "80% have been issues and lack of functionalities"; "Pricing logic is the biggest fail… Automation is basically nonexistent"; missing orders; duplicate customer contacts; stock discrepancies/oversells; "does not respect Odoo's core structures"; slow paid support.

## 3. Teqstars — `shopify` (GraphQL Powered)

- 19.0 listed; GraphQL-native "from v1"; 28,632 LOC (listing metadata); **not supported on Odoo Online** [Vendor claims/Fact, S8]. Price $456.95 (~€399.99) incl. 60–90 min guided install; 60 days support [Vendor claims, S8]. Depends on community "Base Marketplace" module [Vendor claim, S8].
- Orders: discounts, duties, tips, taxes, gift cards, fraud-risk scores, POS orders [Vendor claims, S8]. **Per-gateway + financial-status workflow** (confirm / create+validate invoice / register payment) [Documented workflow — snippet, S9]. COD not explicitly documented [Inference/Unverified].
- Inventory: bi-directional, multi-location mapping, "real-time inventory push" [Vendor claims, S8]. Fulfillment: tracking export, status sync, pickup orders [Vendor claims, S8]; partial + inbound fulfillment unconfirmed [Unverified].
- Refunds/RMA: partial/full refunds with credit notes; cancellation with restock; RMA workflow; payout import with Enterprise auto-reconciliation [Vendor claims, S8].
- **Queue UX (market-best claim):** Order Queue Jobs on interval; on error record bypassed, error log created, queue continues, scheduled-activity alert raised; **per-record retry** [Documented workflow — snippet, S9; Vendor claim, S8]. Multi-store unlimited; analytics dashboard (top products, sales by country, store comparison) [Vendor claims, S8].
- Reviews: 5.0 with 84 reviews on the listing; uniformly perfect — treat with mild caution [Review claims + Inference, S8]. Docs 403 to automated access → lower verifiability [Fact, S9/S10].

## 4. VentorTech — `integration_shopify` PRO

- 16.0–19.0, Enterprise & Community; **no Odoo Online**; each version a separate purchase; **$570.06** (19.0) [Vendor claims, S12]. Built on a generic layered "E-Commerce Connector Core" (`integration`) + per-channel modules [Inference from dependency list, S12] — directly relevant to our modular-family architecture.
- Orders: "New Shopify orders appear in Odoo within seconds via webhooks"; **auto-workflow up to 5 steps (confirm → ship → invoice → send → pay); COD and multiple payment methods supported**; fraud scores; multi-currency [Vendor claims, S12].
- Inventory: bidirectional, webhooks or scheduled, location mapping, BoM stock calc [Vendor claims, S12]. Fulfillment: **bidirectional + tracking, partial fulfillment** [Vendor claim, S12]. Products: export with images/variants/collections/translations; "30+ types" of metafield mapping [Vendor claims, S12]. Customers: address matching, metafield→partner mapping, B2B [Vendor claims, S12].
- **Backfill:** "Import full product catalog… Import historical orders from any date." [Vendor claim, S12].
- Jobs: depends on "Integration Queue Job"; "Every sync action is logged — always know what happened and why"; per-user failed-job notifications; Job Queue Manager rights [Documented workflow/Vendor claims, S12/S14]. Dashboard: "dynamic sales dashboard" [Vendor claim — screenshots not independently observed, S12].
- Reviews ~20, 5★ vendor-hosted [Review claim, S12]. Pricing on ecosystem site [Unverified exact figures, S14].

## 5. `ecommerce_shopify` — Odoo IN Pvt Ltd

- Vendor identified: **Odoo IN Pvt Ltd** [Fact from listing, S15] (provenance question from the 06-30 corpus resolved: a private vendor, not Odoo S.A.). OPL-1; $198.99; 19.0 only.
- Orders: **cron every 10 minutes — listing concedes "real-time sync is not available"** [Vendor-documented limitation, S15]; date-range fetch for backfill; cancellation sync; UTM tracking. **COD/payments: payment-provider → journal mapping incl. COD; auto-invoice when paid; refunds → credit notes** [Vendor claims, S15].
- Inventory: push after order sync; manual "Fetch Inventory" pull; multi-location mapping [Vendor claims, S15]. Fulfillment: bidirectional with tracking, split fulfillment; **two modes (fulfil in Odoo or in Shopify)** [Documented workflow, S15] — the only incumbent naming a fulfillment-mode concept.
- Products: **one-way Shopify→Odoo only; no export; variants imported as separate standalone products** [Vendor-documented limitation, S15]. No metafields; pricelists not applied on import; settings frozen while active; OAuth (post-2026-01-01 stores) or custom token [Vendor claims, S15].
- Error UX: email alerts, **API logs only in Debug Mode**, scheduled activities [Documented workflow, S15]. Onboarding requires vendor appointment [Vendor claim + Inference, S15].

## 6. Softhealer — `sh_shopify_connector`

- 12.0–19.0; Enterprise (Odoo.sh/on-prem) + Community; "not compatible with odoo.com (Odoo SaaS)" [Vendor claim, S16]. $169.08; 365 days support; lifetime updates per purchased version [Vendor claims, S16].
- Orders: bidirectional; webhook create/update; auto-invoice/auto-validate-delivery/auto-register-payment; refunds/returns with credit notes; draft orders; Buy with Prime [Vendor claims, S16]. Inventory: "real-time", multi-location [Vendor claims, S16]. Fulfillment: status tracking + export; reverse direction unclear [Vendor claim + Open question, S16].
- Products: import/export with media/tags/variants, publish control, exclude flags, recommendations sync, date-range import [Vendor claims, S16]. Customers: bidirectional + webhooks; metafield mapping products/customers/orders [Vendor claims, S16].
- Queue: "Queue dashboard framework" draft/completed/error [Vendor claim, S16]. Multi-store + multi-company; abandoned checkouts → CRM leads; gift cards; claims "GraphQL API Integration" [Vendor claims, S16; GraphQL claim unverified].
- Reviews: no independent complaint threads surfaced this pass [Open question]; breadth-vs-depth risk is [Inference], not evidence.

## 7. Additional market scan

- **Odoo S.A. native Shopify sync: no evidence found** in this pass [Fact of absence — re-check each Odoo release]. **Cetmix: no Shopify connector found** — excluded.
- Names tracked via S17 [Review/vendor claims relayed by third party]: Techspawn OdooSyncO ($15–30/mo SaaS, 4.6★), Cybrosys (€99 entry). Cross-market signals: cron latency → overselling in flash sales; **duplicate orders** and **silent return failures** are recurring complaint themes; "Shopify deprecated its old REST Admin API as of 1 October 2024" (corroborates GraphQL-first); review-farming warning ("not every high score is trustworthy").

## 8. Premium-UX evidence pass

- **Polaris [Fact, S18/S19]:** Polaris React is now labelled "(Deprecated)"; successor is **Polaris Web Components**; taxonomy Foundations / Components / Tokens ("coded names that represent design decisions for color, spacing, typography, and more" [quote]) / Icons ("over 400 carefully designed icons focused on commerce and entrepreneurship" [quote]). App-home guidance: components "work like native HTML elements" and ensure apps "look and behave like the rest of the Shopify admin" [quotes]. [Recommendation] The connector should mirror this inside Odoo: token-driven, consistent status vocabulary, designed empty states, skeletons — native-feeling premium.
- **Celigo [Documented workflow, Partial, S20]:** "real-time dashboards, transactional error tracking, automatic retries, and detailed error logs" + error classifications with resolve/retry workflows; Zapier by contrast has "basic history" (erppeers.com — Partial). [Inference] The premium bar = per-record error objects with classification, retry, resolve, audit — not a log file.
- **WCAG 2.2 AA [Fact, S21]:** 1.4.3 contrast ≥4.5:1 (large ≥3:1); 1.4.11 non-text contrast ≥3:1 (badges, chart strokes, focus rings); 1.4.13 hover/focus content dismissible-hoverable-persistent; 2.4.7 focus visible; **2.4.11 Focus Not Obscured (new)**; **2.5.8 Target Size (new; commonly 24×24 CSS px — exact normative text to re-verify before quoting)**; 2.3.3 animation-from-interactions (AAA, aspirational — grounds reduced-motion support).
- **Apple HIG [Unverified pending re-fetch, S22]:** target pages live but JS-rendered; do not quote HIG wording until captured. Stripe/Linear/Airtable/Pipe17/Alloy: **not fetched — no claims made**; logged for a screenshot-capable pass.

## 9. Synthesis for the premium product (evidence-backed)

Market clusters: (a) premium one-time modules (Emipro ~$627, VentorTech ~$570) with breadth but reliability complaints (Emipro) or thin review volume (VentorTech); (b) mid/low-cost with hard ceilings (cron-only, one-way products, variant flattening, debug-only logs); (c) SaaS bridges. **Whitespace [Inference/Recommendation]:**
1. Explicit, documented **COD and pending-payment semantics** — no incumbent documents COD behavior properly (Emipro/Teqstars bury it in gateway mapping; VentorTech claims support without workflow docs).
2. **Provable idempotency/duplicate prevention** — duplicate orders/customers are the top real-world complaints.
3. **Queue/job UX** with per-record retry + human-readable failure states + automatic classified retry (Teqstars sets the bar; nobody documents backoff).
4. **True bidirectional fulfillment incl. partial and 3PL-initiated** — undocumented/unverified across all incumbents; `ecommerce_shopify`'s crude two-mode concept validates the Mode 1/Mode 2 direction.
5. **Safe reconnect/backfill with preview and reconciliation reports** — only VentorTech claims any-date backfill; nobody documents duplicate-safe re-import.
6. **Premium dashboard UX** — every incumbent's "dashboard" is stock Odoo views + marketing screenshots.
7. Support without paywall cliffs; genuine role model (absent across all incumbents); honest freshness/status language.
**Avoid [from evidence]:** marketing-only capability claims; hard store caps; multi-company carve-outs in fine print; debug-mode-only logs; variant flattening; cron-only sync sold as "real-time".
