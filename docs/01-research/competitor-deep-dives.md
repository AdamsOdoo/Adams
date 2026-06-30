# Competitor Deep Dives (Research Sprint C)

> **The main Sprint C output.** Evidence-based, cited, claim-classified deep dives
> of the user-provided competitor connectors, so the Odoo 19 ↔ Shopify Connector
> is designed from real knowledge, not guesses. Source grounding (raw notes,
> quotes, access status) lives in
> [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md)
> and the visual analysis in
> [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md).
>
> **Governance (`CLAUDE.md` §7–§8).** Access date **2026-06-30**. These are
> **competitor sources** (Tier 2–5): capability statements are **competitor
> claims**, not facts, unless a documented step-by-step flow/screenshot
> demonstrates them. On-page price/license/version/author/LOC/reviews are
> **on-page facts as of the access date**. **No claim here is a Tier-1 technical
> fact** (those come only from the official Shopify/Odoo baselines). **No MVP
> scope and no architecture is decided here** — strengths/weaknesses/"do better"
> are **inferences/recommendations**, gated for ChatGPT review.
>
> **Feature-scope legend:**
> `✅ demonstrated` = step-by-step flow and/or screenshot shows it ·
> `🟨 vendor claim` = stated capability, not demonstrated ·
> `➖ implied` = strongly implied but not directly shown ·
> `⬜ not found` = not on the accessed pages ·
> `🔒 blocked/unknown` = behind a wall we did not bypass.

---

## Competitor: Webkul — Odoo Multichannel Shopify Connector (R1)

### Evidence status
- **Sources used:** R1 blog/user-guide `https://webkul.com/blog/odoo-multichannel-shopify-connector/` + store page `https://store.webkul.com/odoo-multichannel-shopify-connector.html`.
- **Date accessed:** 2026-06-30 · **Access status:** Accessible (HTTP 200, no auth).
- **Evidence strength:** Medium — a single vendor user-guide (rich, screenshot-illustrated, but promotional) + a marketplace store page for price/version. No third-party verification.
- **Claim classification note:** the guide demonstrates the **setup and import/export wizards** with screenshots (✅), but resilience features (real-time, dedup, feeds auto-evaluation) are **vendor claims** (🟨).

### Product positioning
- **What the vendor appears to sell:** a Shopify channel for Webkul's broader **"Odoo Multi channel sale"** framework (a base module is a hard prerequisite) — i.e. Shopify is one channel in a multichannel suite, not a standalone Shopify-first product.
- **Target customer:** Odoo merchants already in (or adopting) Webkul's multichannel ecosystem.
- **Odoo version:** blog states **V19/V18/V17**; store lists **10.x–19.x** (discrepancy). **Shopify side:** custom-app OAuth; claims GraphQL API.
- **Hosting:** self-hosted Odoo addon; **SAAS users must migrate to Odoo.sh** before install (per guide).
- **Pricing/license/support:** **$170.00 USD** (store; EUR/INR offered), license "Single application"; support via **UV Desk ticket + support email**. **Version discrepancy unresolved** (blog 1.0.0 vs store 3.5.1).

### Feature scope
- Store/instance connection ✅ · Authentication/credentials ✅ (custom-app OAuth, redirect `…/shopify_odoo_bridge/redirect`) · Setup wizard ✅ · Test connection ✅ · Dashboard 🟨 ("dynamic dashboard" with import/export buttons)
- Product import ✅ · Product export ✅ (categories + product templates) · Variants/options ⬜ · Images/media ⬜ · Price lists 🟨 (pricelist stores original price)
- Inventory sync ✅ config / 🟨 "real-time" · Multi-location ⬜ (single default warehouse/location) · Customer import 🟨 · Customer export ⬜ · Address handling ⬜
- Order import ✅ · Order status mapping 🟨 (cancel/shipment status Odoo→Shopify) · Invoice creation ⬜ · Payment handling ⬜ · Payout reconciliation ⬜ · Refunds/returns/cancellations ⬜ (only cancel-status sync) · Fulfillment/tracking 🟨 (store claims partial shipment); "Import of shipping method is **not available**" (on-page fact)
- Webhooks ⬜ (none documented) · Scheduled/cron sync ✅ · Manual sync ✅ · Queues/jobs ⬜ (no job queue; uses **Feeds** staging) · Error logs ✅ (Feeds error-feeds) · Retry/recovery 🟨 (re-evaluate error feed) · Duplicate prevention 🟨 (SKU+Barcode; "Avoid Duplicity")
- Mappings ✅ · Multi-store ⬜ · Multi-company ✅ (default Company) · Shopify Markets ⬜ · Metafields ➖ (metaobject scopes requested) · Gift cards ➖ (gift-card scopes requested) · POS ⬜ · B2B ⬜ · Permissions/security ⬜ (only Shopify scopes) · Reporting/analytics ⬜ · Configuration/settings ✅ · Troubleshooting/support ✅ (UV Desk) · Updates/release notes 🟨 (dates only, no changelog)

### Workflow reconstruction
- **Setup/credentials (✅):** create Shopify custom app → set Redirect URL → grant scopes → copy Client ID/Secret → Odoo "Connect" → enter URL/Client ID/Secret → Save → **Test Connection** → configure Basic tab. *Error path not documented.*
- **Import (✅):** Operations tab/dashboard → choose Product/Order/Customer/Category wizard → pick filter (all / ID / Date updated after / [Date created after]) → run → data lands in **Feeds** → auto-evaluate or manual approve → record created; visible in Synchronization History. **Error path:** bad data → "error feed" → user fixes mapping → re-evaluate (described, not shown end-to-end).
- **Export (✅):** Operations/dashboard → Category or Product export → push to Shopify → mapping visible.
- **Scheduled import (✅):** Miscellaneous » Global configuration (or Channel Cron) → set Model, Scheduler User, Execute Every, Active, Next Execution Date.

### UX/UI analysis
- **Navigation:** lives inside the multichannel app; per-object wizards + a dynamic dashboard. **Config IA** is tab-segmented (Basic/Sales/Product) — reasonable, but the Sales tab is field-dense and labels ("Auto-evaluate", "API Record Limit", "Stock Action") are jargon without visible tooltips.
- **Status/logs:** the **Feeds** staging area + error-feeds + Synchronization History give decent visibility; exact columns not shown.
- **Friction:** raw Odoo cron internals (Model, Scheduler User, Next Execution Date) are exposed to end users — leaky and technical. Credential setup is manual multi-field copy/paste.
- **Overall:** a competent, guide-driven UX with a **stage-before-commit** concept (Feeds), but it surfaces too much Odoo plumbing and leaves variants/images/refunds undocumented.

### Reliability and robustness analysis
- **Idempotency/dedup:** 🟨 SKU+Barcode + "Avoid Duplicity (Default Code)" toggle — claimed, not demonstrated.
- **Retry/recovery:** 🟨 fix-and-re-evaluate error feeds; no automated retry/backoff.
- **Queue/jobs:** ⬜ no job queue; Feeds staging only. **Webhook reconciliation:** ⬜ none (cron/poll inbound). **Rate-limit handling:** ⬜ only an "API Record Limit" batch size + a GraphQL "reduced API calls" claim.
- **Partial failure:** ➖ per-feed error isolation implied. **Audit logs:** 🟨 Synchronization History. **Permissions/security:** ⬜ no Odoo access-rights model shown.

### Updates, release notes, and maintenance
- Blog "Updated 29 June 2026"; store "Last Update June 8, 2026" / "Released 6 years ago". **No detailed changelog.** **Version mismatch (1.0.0 vs 3.5.1)** is a documentation-quality risk.

### Strengths (evidence-backed)
- A clear, screenshot-driven **setup walkthrough** with an explicit **Test Connection** step; a **Feeds staging + error-feed** model that lets non-developers fix and re-evaluate; per-object **filtered import wizards**; mature support tooling (UV Desk).

### Weaknesses / gaps (evidence-backed or labelled inference)
- **No webhooks** (cron/poll only); **single location** (no multi-location); **variants, images, invoices, refunds/returns, payments/payouts, multi-store, Markets, B2B, POS, reporting, and Odoo-side permissions not documented**; **customer export missing** (import only); version/compat metadata inconsistent (inference: weak doc hygiene).

### What we can learn
- A **stage-before-commit** inbound pipeline with a fixable error queue is a good, demonstrable resilience UX; pair it with an explicit connection test.

### What we can do better
- Replace exposed cron internals with a friendly "every N minutes" scheduler; add webhooks + reconciliation; support multi-location, variants/images, refunds, and customer export as first-class; keep a single authoritative version/changelog.

### What to avoid
- Exposing raw `ir.cron` fields to users; "real-time" labelling for a cron-import model; shipping a feature listing where core domains (variants/images/refunds) are simply absent; inconsistent version metadata across pages.

### Open questions
- Authoritative version (1.0.0 vs 3.5.1)? Are variants/images/refunds actually supported but undocumented? Any webhook support at all? Real-time scope (only Odoo→Shopify stock/status)?

---

## Competitor: Teqstars — Shopify Connector for Odoo (R2)

> **Access caveat (load-bearing).** The **Teqstars documentation host
> (`docs.teqstars.com`, 19.0 and 16.0) is HTTP 403 bot-blocked** — no workflow/
> screenshot evidence could be read, and **no auth was bypassed** (there is no
> login wall; it is a WAF/bot block). The deep dive below is built from the
> **accessible Odoo Apps Store listing** `apps.odoo.com/apps/modules/19.0/shopify`
> (author "TeqStars"), so **almost everything is a `🟨 vendor claim`** with
> on-page facts limited to price/license/version/author/reviews. Treat Teqstars
> as **strong-on-paper but largely unverified**.

### Evidence status
- **Sources used:** Odoo Apps listing (accessible); docs host (Blocked 403); search-index snippets (non-equivalent, used only as labelled fallback).
- **Date accessed:** 2026-06-30 · **Access status:** **Blocked (docs) / Accessible (Apps listing)**.
- **Evidence strength:** Low–Medium — rich vendor marketing on the listing; **zero** directly-readable docs/screenshots; **83 reviews / 5.0 stars** is the only third-party signal (unverified).
- **Claim classification note:** the listing's feature strings are literally present (so "the vendor claims X" is an on-page fact) but **X itself is a competitor claim**, never demonstrated here.

### Product positioning
- **Sells:** "Odoo Shopify Connector **(GraphQL Powered)**" — a premium, GraphQL-native bidirectional connector. **Target:** multichannel Shopify merchants on Odoo CE/EE.
- **Odoo version:** 19.0 listing (vendor states 13–19). **Shopify side:** Shopify GraphQL Admin API "from v1" + webhooks. **Hosting:** Odoo Online / Odoo.sh / On-Premise (listing).
- **Pricing/license/support:** **$326.20**, **OPL-1**, author **TeqStars**; ~28,630 LOC; **83 reviews / 5.0**; vendor claims free 60–90 min install session, pre-installed demo sandbox, "AI-powered docs", 24h support. *(EUR 399.99 is a conversion, not on-page.)*

### Feature scope (almost all 🟨 vendor claim from the listing)
- Store/instance connection 🟨 · Auth/credentials 🟨 (Admin API token, "auto-generated, securely stored" — snippet) · Setup wizard 🟨 ("guides you…checks API access") · Dashboards 🟨 (Marketplace + **Analytics** dashboards)
- Product import/export 🟨 · Variants 🟨 · Images 🟨 + **pHash image dedup** 🟨 · Price lists 🟨 (volume + B2B pricing)
- Inventory sync 🟨 · **Multi-location** 🟨 (locations→warehouses) · Customer import/export 🟨 · Address handling 🟨
- Order import 🟨 (incl. **POS**, gift cards, duties, tips, taxes, tracking) · Order status / **auto order workflow** 🟨 (per payment gateway + financial status) · Invoice creation 🟨 · Payment handling 🟨 (gateway→journal) · **Payout reconciliation** 🟨 (import; "auto-reconciliation on Enterprise") · Refunds/partial refunds 🟨 · Cancellations 🟨 (reason/notify/restock — snippet) · Fulfillment/tracking 🟨 ("Update in Marketplace")
- **Webhooks** 🟨 (real-time product/order/customer; per-event Webhook tab; HTTPS) · Scheduled/cron sync 🟨 · Manual sync 🟨 · **Queue Manager** 🟨 ("per-record error retry"; "one bad record won't block 999") · Error logs/retry 🟨 · Duplicate prevention 🟨 (**SKU/barcode "or both"** smart matching) · Mappings 🟨 (gateway→journal, location→warehouse, metafields)
- Multi-store 🟨 ("unlimited stores, each with own warehouse") · Multi-company ⬜ (not distinguished from multi-store) · **Shopify Markets / B2B** 🟨 · Metafields 🟨 (auto type-casting; conditions/transformations) · Gift cards 🟨 · POS 🟨 · Permissions/security ⬜ (token "securely stored"; no access-model detail) · Reporting 🟨 (Analytics dashboard) · Collections 🟨 · Fraud/risk 🟨 · Updates/release notes 🟨 (2026-04 API/idempotency claim — **unverifiable**)

### Workflow reconstruction (from listing captions + snippets — not directly observed)
- **Connect instance:** install (deps: Sales/Discuss/Invoicing/Inventory/Base Marketplace) → create Shopify Instance → generate Admin API token via custom app → wizard "confirms everything is ready". *Error surfacing unknown (docs 403).*
- **Webhooks:** Marketplace » Configuration » Instance » **Webhook tab** → add line (Name, Event Type, Active). **Order import + auto-workflow:** manual wizard or cron → per gateway+financial-status workflow confirms order, creates+validates invoice, registers payment; **failures land in Queue Manager** and can auto-create an Odoo Activity. **Refund/cancel from Odoo** with "refund to Shopify"/restock/notify checkboxes. **Fulfillment:** "Update in Marketplace" → Shopify Fulfilled + tracking.

### UX/UI analysis (caption-level only — **not verified**)
- Captions imply: a single credentials form; a **match-by (SKU/Barcode/both) selector**; per-gateway workflow mapping rows; a line-based webhook table; **two dashboards** (operational + analytical); a **Queue Manager with a Retry control**; refund/cancel dialogs with propagate-to-Shopify checkboxes. **None visually inspected** — UX quality is unproven.

### Reliability and robustness analysis (claims, unverified)
- **Idempotency:** 🟨 (snippet) "idempotency directives…preventing duplicate inventory changes and double refunds when retrying" — aligns with the Tier-1 2026-04 `@idempotent` requirement but **unverifiable**. **Dedup:** 🟨 SKU/barcode smart matching + pHash image dedup. **Retry/queue:** 🟨 Queue Manager per-record retry + activity-on-failure. **Webhook reconciliation/rate-limit/permissions:** ⬜/🟨 not detailed. The **resilience story is the most marketing-complete of the survey but the least verifiable.**

### Updates, release notes, and maintenance
- **No directly-readable dated changelog** (docs 403). A snippet claims a 2026-04 Shopify-API/idempotency update — **unverified**. **83 reviews / 5.0** suggests adoption/satisfaction (unverified). Vendor support claims are strong (install session, sandbox).

### Strengths (evidence-backed = on-page facts + the review count)
- Strong **on-paper breadth** (Markets, B2B, payouts, metafields, POS, queue manager) at a mid price; **GraphQL-native** positioning; **83×5.0** reviews; explicit smart-matching and gateway→journal mapping in captions.

### Weaknesses / gaps
- **Docs entirely unreadable** (403) → the whole product is **unverified**; **no demonstrated workflow/screenshot**; multi-company vs multi-store unclear; permissions/security model absent; the idempotency/queue resilience is **claim-only**. Buyer due-diligence is hard.

### What we can learn
- The **vendor positioning checklist** to beat: GraphQL-native, dual real-time+cron, smart SKU/barcode matching, per-gateway workflow→journal mapping, a per-record queue with retry, payout reconciliation, Markets/B2B, metafields with transformations. Also: **"one bad record won't block 999"** is the resilience message customers respond to.

### What we can do better
- **Actually demonstrate** these (readable docs, screenshots, an open demo) — Teqstars' biggest weakness is unverifiability. Make idempotency, queue retry, and reconciliation **observable**, not just claimed.

### What to avoid
- A **bot-blocked docs site** that defeats evaluation/trust; presenting idempotency/retry as marketing bullets with no demonstrable surface; conflating multi-store and multi-company.

### Open questions
- Does the docs host block evaluation deliberately? Are the queue-retry/idempotency claims real (no way to verify while 403)? Multi-company support? Is the 2026-04 idempotency update actually shipped? Is "smart matching" in this module or a "PRO" variant?

---

## Competitor: Emipro — Shopify Odoo Connector (R3)

> **The most thoroughly documented and demonstrated connector of the survey** —
> an accessible, screenshot-heavy doc tree (~35 v19 pages with real `.png`
> images). Most feature areas are **✅ demonstrated**, not just claimed.

### Evidence status
- **Sources used:** R3 docs tree `docs.emiprotechnologies.com/shopify-odoo-connector/v19/...` (~35 sub-pages).
- **Date accessed:** 2026-06-30 · **Access status:** Accessible (HTTP 200; static site; real screenshots).
- **Evidence strength:** **High (for behaviour)** — concrete step-by-step flows + screenshots + explicit limitations; **but no price/license/author and a stale published changelog** (docs-only).
- **Claim classification note:** unusually high ratio of **✅ demonstrated** to 🟨 claim; the vendor documents **limitations** plainly (a trust signal).

### Product positioning
- **Sells:** a deep, operations-grade bidirectional Shopify connector for Odoo. **Target:** serious Odoo merchants needing finance-grade order/payout/return handling and Markets.
- **Odoo version:** v19 (selectors 13–19); Path A needs connector "**19.0.3.0 or higher**". **Shopify side:** custom/partner app + token; **REST and GraphQL** (GraphQL required for customer export, SO export, Markets, returns import). **Hosting:** self-hosted; requires **live HTTPS** (webhooks/OAuth; localhost unsupported).
- **Pricing/license/support:** **not shown in docs** (Apps/shop not in R3 scope); support via Helpdesk ticket; vendor Emipro Technologies.

### Feature scope (high ✅ density)
- Store/instance + auth ✅ (Path A direct-install / Path B partner) · Setup wizard ✅ · Dashboard 🟨 (Shopify Dashboard + Smart Dashboard) · Test connection ➖
- Product import ✅ (Create/Update date ranges; "Do not update existing"; "Import Draft") · Product export ✅ · **Product mapping** ✅ (SKU match **or CSV/XLSX upload-and-map**) · Variants 🟨/✅ (variant window; compare-at price; fixed-stock export) · Images ✅ (import; add/update via Odoo Update Product; remove-only in Shopify window) · Price lists ✅ (Pricelist + Compare At Pricelist) · Publishing ✅ (Web / Web+POS; "Shopify Unpublish"; sell-OOS toggle)
- Inventory sync ✅ (Export Stock: only-synced, only-changed-since-last-run else last 30 days, per Shopify Location) · **Stock field choice** ✅ (Forecast vs Free-to-Use, with formulas) · Import Stock ✅ (**creates Inventory Adjustment to process manually** — friction) · Multi-location ✅ (Import Locations; Primary auto-set) · Multi-warehouse delivery ✅
- Customer import ✅ (queue, incremental by last-exec date) · **Customer export** ✅ (Contacts » Action; queue; **email dedup** link-not-duplicate; skip no-email/child/already-linked; GraphQL required) · Customer-as-company ✅ · Address handling ➖ · Segments 🟨
- Order import ✅ (unshipped + shipped/historical; status filter; sequence/prefix) · **Multi-payment** ✅ (gift card + stripe → two payment lines) · Order/financial-status mapping 🟨 (Sale Auto Workflow / Payment Gateway / Financial Status) · Invoice creation 🟨/➖ (per workflow; qty-webhook can invoice) · Payment handling ➖ · **Payouts/reconciliation** ✅ (Shopify Payments only; import → Generate Bank Statement → reconcile) · Refunds/returns ✅ (manual + **webhook**; credit note + return picking; conditions: invoice-exists, restock, fulfilled-only) · Cancellation ✅ (cancels if quotation/undelivered, else log-note only; **never creates a cancel order**) · Fulfillment/tracking ✅ (Export Shipment; **Put in Pack** multi-package; "Fulfilled")
- **Webhooks** ✅ (product create/update/delete, order create/update, customer create/update; SSL; behaviour toggles) · Scheduled/cron ✅ (per-process scheduler + Last Operation Details) · Manual sync ✅ · **Queues/jobs** ✅ (125 products / 50 orders per queue; Draft/Failed/Cancelled/Done; manual process; **Force Done irreversible**; Log Lines) · **Error logs / Log Book** ✅ (Mismatch Log with reasons) · Retry/recovery 🟨 (manual re-run; manual import to recover missed webhooks; **no auto-retry**) · Duplicate prevention ✅ (email/SKU; "Do not update existing"; stored references block re-export)
- Mappings ✅ · Multi-store ➖ · **Multi-company / Markets** ✅ (per-market Company/Warehouse/Pricelist/Fiscal/Language/Journal; order matched **country→currency→fallback**; markets sync-only; **no multi-warehouse delivery with Markets**) · **Metafields** ✅ (product/variant/order/customer; Fetch Scope; Sync Direction; custom-namespace auto-activated) · **Channel/analytic mapping** ✅ (analytic account per channel; exclude-channel with logged reason) · Gift cards 🟨 (scopes + auto-fulfil toggle + multi-payment) · POS 🟨 (Web+POS publish; default POS customer) · Buy with Prime 🟨 · Multi-currency 🟨 · B2B ⬜ · Permissions/security ✅ (Odoo user rights; Shopify fulfillment scopes granted explicitly) · Reporting ✅ (Sales Analysis; **Net Profit report — Enterprise only**) · Updates/release notes ✅ but **stale on v19 path** (only to 17.0.3.2 / Apr 2024)

### Workflow reconstruction (representative — all ✅ with screenshots)
- **Token (Path A):** Odoo "Set Shopify Authorization Details" wizard → paste App URL + Redirect URL into a Shopify app **Version** (warns: **"Any mismatch — including a trailing slash — will cause the authorization to fail"**) → paste full scope string → Release → install → authorize → token.
- **Import products:** Dashboard » Perform Operation → Create/Update date + range (From defaults to last-exec) → options → queue (125/queue) → review; mismatches in Log Lines.
- **Import Stock:** Perform Operation » Import Stock → **creates Inventory Adjustment records that must be processed manually** to take effect (explicit friction).
- **Customer export:** Contacts » Action » Prepare for Export → Create Queues → email-dedup link/create → queue line Done/Failed.
- **Returns via webhook:** enable Order Webhook + Auto-Refund/Return toggles → Shopify Refund (Restock for return) → credit note (**only if invoice exists**) + return picking (**fulfilled/partially-fulfilled only**).
- **Markets sync:** enable Markets → "Sync Markets" (GraphQL) → "N market(s) synced" → set per-market mapping; orders routed **country→currency→fallback**.
- **Payouts:** configure journals → import payout report → Generate Bank Statement → reconcile (Shopify Payments only).

### UX/UI analysis
- **Navigation:** a clear Dashboard "Perform Operation" entry **or** Shopify » Processes » Operations — a consistent dual entry point. **Queues** are the operational heart: state-coloured lists, per-line **Log Lines**, manual processing, a "processed" ribbon, and a **Log Book/Mismatch Log** with reason-coded failures — the **best demonstrated observability** of the survey.
- **Guidance:** docs are precise about **prerequisites, gotchas, and limitations** (trailing-slash auth failure; manual inventory-adjustment processing; Markets-no-multi-warehouse; Net-Profit Enterprise-only; payouts Shopify-Payments-only). This honesty is a strength.
- **Friction:** **Import Stock requires a manual Inventory Adjustment step** (not automatic); **Force Done is irreversible**; very many configuration toggles spread across dense screens; no automatic retry (recovery is manual).
- **Overall:** powerful and trustworthy for an operator, but **expert-oriented** — high surface area, manual steps, and dense config.

### Reliability and robustness analysis
- **Idempotency/dedup:** ✅ email-based customer dedup; SKU keying; "Do not update existing"; stored Shopify references **block re-export** ("order already exported"). **Queue/jobs:** ✅ batch queues with isolated Failed/Cancelled lines (partial-failure friendly) + Log Lines. **Webhook reconciliation:** ✅ manual import paths explicitly exist to **recover missed/delayed webhooks**; refresh button; *Shopify-side retry is **misquoted as "19/48h"** (now outdated vs Tier-1 8/4h) — a docs-accuracy gap.* **Retry/recovery:** 🟨 **manual only** (no auto-retry/backoff). **Rate-limit handling:** ⬜ none documented (only "stagger scheduler intervals" to avoid overloading Odoo). **Audit logs:** ✅ Log Book + chatter notes. **Permissions:** ✅ Odoo user rights + explicit Shopify scope grants.

### Updates, release notes, and maintenance
- **Stale published changelog on the v19 path** (only to 17.0.3.2 / Apr 2024) despite a v19 build (19.0.3.0+) — a **freshness/transparency gap**. Docs themselves are detailed and current in content.

### Strengths (evidence-backed)
- **Deepest demonstrated feature set + best observability** (queues, Log Book, reason-coded errors); **finance-grade** payouts/returns/Markets; **honest documentation of limitations**; concrete dedup (email/SKU + re-export block); CSV product-mapping fallback; per-market deterministic order routing.

### Weaknesses / gaps
- **No automatic retry/backoff** (manual recovery); **manual Inventory-Adjustment** processing on stock import; **no documented rate-limit handling**; **stale v19 changelog**; **outdated Shopify webhook-retry figure** in docs; expert-heavy UX; B2B and multi-store not clearly covered.

### What we can learn
- The **queue + Log Book + reason-coded mismatch log** is the observability bar to match or beat; **email-dedup that links rather than duplicates**; **stored-reference re-export blocking** for idempotency; **document limitations honestly**; **deterministic market routing** (country→currency→fallback).

### What we can do better
- **Automate retry/backoff** (Emipro is manual); **auto-apply imported stock** (no manual Inventory Adjustment); add **rate-limit/cost-aware throttling**; keep an **accurate, current changelog**; simplify the expert-heavy config; cite **current** Shopify limits (not 19/48h).

### What to avoid
- Manual inventory-adjustment processing as a required step; irreversible "Force Done" without strong guards; **publishing stale/outdated platform figures** in docs; leaving retry entirely manual; letting the published changelog rot on the version path.

### Open questions
- Actual price/license (not in docs)? Auto-retry on next cron for failed queue lines? Rate-limit behaviour under 429? B2B support? Interaction of "Is Delivery from Multiple warehouse?" with Markets' no-multi-warehouse limit?

---

## Competitor: VentorTech — Odoo Shopify Connector PRO (R4 + R7)

> **The technical leader of the survey by evidence quality.** Uniquely, its
> claims are backed by a **dated public release-notes trail (1.13.0 Oct 2025 →
> 2.1.6 Jun 23 2026)** that *demonstrates real reliability engineering*
> (idempotency directives, automatic retry, CRITICAL silent-data-loss fixes) and
> a 28-article Confluence KB showing the connector UI. Built on a **background
> job queue (OCA `queue_job`)** and **Shopify GraphQL** (since v2.0.0).

### Evidence status
- **Sources used:** R7 marketing `ventor.tech/solutions/...`; **ecosystem** product/shop pages; **Odoo Apps `integration_shopify`**; **dated release-notes** page; install/why-choose FAQs; **R4 Confluence** KB (11 of 28 child articles, anonymous/partial).
- **Date accessed:** 2026-06-30 · **Access status:** Accessible (R7 cluster) / Partial (R4 Confluence) — no auth bypassed.
- **Evidence strength:** **High** — versioned, dated release notes (mechanism-level), connector-UI screenshots in Confluence, 300+ installs / 20 reviews, Official Odoo partner. **Caveat:** source-attribution discipline applied — many strong claims live on the Apps Store/ecosystem pages, not the thin marketing page; each cited to its URL.
- **Claim classification note:** release-note items with a version+date that name a mechanism are treated as **✅ demonstrated** (the vendor shipped and documented them); pure marketing bullets stay **🟨**.

### Product positioning
- **Sells:** "Odoo Shopify connector **PRO**" by **VentorTech, an Official Odoo partner** — a premium, EU-built, privacy-emphasising connector that scales "10 or 10.000 orders/day". **Target:** Odoo CE/EE on **Odoo.sh or on-premise** (NOT Odoo Online).
- **Odoo version:** Apps Store **13.0–19.0**; module `integration_shopify` **v2.1.6 (2026-06-23)**. **Shopify side:** **OAuth (no manual tokens)**; **GraphQL since v2.0.0**; **8 webhook events** + HMAC-SHA256; Markets & Catalogs; metafields.
- **Hosting:** self-hosted only; **requires `server_wide_modules` + `queue_job`/`integration_queue_job` + ≥2 workers** in `odoo.conf` (a real deployment prerequisite).
- **Pricing/license/support:** **€499/yr** (ecosystem subscription; renewal discounts 20%→40%) or **$569.16 one-time** (Apps Store); OPL-1; 3411 LOC; **300+ installs, 20 reviews**; priority support while subscribed; **automatic git-repo updates** in a separate branch; paid install/config service (~€449–499).

### Feature scope (high ✅ density, version-dated)
- Store/instance + **OAuth** ✅ (no manual tokens; v2.1.3 credential masking) · **Setup wizard** 🟨 (Apps "8-step"; ecosystem "3-step") · **Connection test + auto scope-check** 🟨
- Product import/export ✅ (both directions; draft-export-for-review) · **Auto-export on Odoo change** 🟨 · Variants ✅ (v2.1.4 fixed 250-variant cap) · Images ✅ (both directions, disableable) · SEO/taxonomy ✅ (v2.1.3 Standard Product Taxonomy) · **BoM/kit stock** ✅ (v2.1.2 real-time after MO) · **Multi-language** ✅ (v1.13.0 translation sync) · **Field-mapping engine** 🟨 (per-field direction + **custom Python transforms** + **test against live data**)
- Price lists ✅ (pricelists; per-market via Catalogs) · Inventory sync ✅ (real-time on stock move **or** scheduled; quantity field = Free/On-Hand/Forecasted; v2.1.1 "Export Inventory Now") · **Multi-location** ✅ (locations↔warehouses; multi-location fulfillment) · **Multi-company inventory** ✅ (v2.1.3 combine stock, correct company context)
- Customer import ✅ · **Customer dedup** ✅ (match by email/name/phone before create; v1.13.0 normalize email/phone) · Address handling ➖ · **B2B** ✅ (companies vs individuals; VAT import + **VIES validation, 3× retry**; B2B duplicate-contact prevention v2.1.6)
- Order import ✅ (**real-time via webhooks**, "within seconds"; filter by status/channel/currency; auto-create missing products/carriers/taxes) · Order status mapping ✅ · **Auto-workflow** 🟨 ("up to 5 steps: confirm→ship→invoice→send→pay"; each a background job; "visual pipeline") · Invoice creation ✅ (v2.1.2 advance payments) · Payment handling ✅ (Shopify payments→Odoo invoices; v2.1.3 transaction-date; v2.1.6 currency conversion) · **Refunds/cancellations** ✅ (synced back; **GraphQL refund mutations with idempotency** v2.1.4) · Payout reconciliation ⬜ (not found) · Fulfillment/tracking ✅ (carrier tracking export)
- **Webhooks** ✅ (8 events; **HMAC-SHA256** 🟨; hardened across releases — respect cut-off/import filters; fixed rejection after store-URL migration) · Scheduled sync ✅ · Manual sync ✅ · **Queue/jobs** ✅ (background job queue; `queue_job` dependency; v2.1.1 "Run Now"; v1.13.0 "Failed Job Notifications") · **Error logs / audit** ✅ ("every sync action logged"; v2.0.0 log retention; v2.1.2 contact trace logs) · **Retry/recovery** ✅ (v1.13.0 auto-retry safe ops after network/server errors; failed steps shown + restartable) · **Idempotency** ✅ (v2.1.4/2.1.6 directives prevent double refunds / duplicate inventory) · Duplicate prevention ✅ (contacts/products; SKU/barcode matching; manual mapping)
- Multi-store ✅ ("as many Shopify stores as you want") · **Shopify Markets** ✅ (v2.0.0 Markets & Catalogs) · Metafields ✅ (map any metafield, 30+ types; v2.1.6 custom product metafields in field defs) · Sales channels ✅ (v2.1.4 channel mapping) · Fraud/risk ✅ (import score; threshold flag) · **Product validation tool** 🟨 (pre-sync catalog check) · Permissions/security ➖ (credential masking + HMAC; no connector access-group detail found) · Reporting ⬜ (no dedicated KPI report; only auto-workflow "visual pipeline"/status menu) · POS ⬜ · Gift cards ⬜ · Updates ✅ (frequent, **dated, transparent**)
- **From R4 Confluence (demonstrated UI):** webhook **traffic-light health** (green/yellow="callback URL mismatch, check `web.base.url`"/red); **External Location** multi-location grid; **Markets & Catalogs Preview/Report dry-run**; fulfillment table with per-line "internal info"; order-risk fields; two-step cancel with restock/refund/notify; honest **PII/Basic-plan limitation** disclosure; POS via "Closed" status + default customer.

### Workflow reconstruction
- **Install (self-hosted):** edit `odoo.conf` (`server_wide_modules` incl. `queue_job`/`integration_queue_job`/`integration`/connector; `queue_job channels root:1`; ≥2 workers; Shopify Python reqs) → restart → run initial import. *(Background jobs won't run without this — a real prerequisite.)*
- **Connect:** OAuth to Shopify (no manual tokens) → **auto scope-check** → **connection test** → choose import scope → live sync.
- **Initial import:** unified Import Wizard (v1.13.0) imports products/variants/attributes/categories/payment methods/taxes/shipping/initial stock/languages → auto-map by SKU/barcode → optional historical orders from a chosen date → **validation test** surfaces catalog issues; batching "processes all valid products even if some error".
- **Order import + auto-workflow:** webhook → order queue job ("within seconds") → import details + auto-create missing → import fraud score (flag > threshold) → auto-workflow up to 5 steps (each a job; **visual pipeline**) → payments applied → tracking pushed → status/cancellation synced back. **Failed steps shown with details; restartable.**
- **Pricelist→Catalog (R4):** Import Markets & Catalogs → map → **Preview/Report dry-run** ("detect issues before sending") → Send Prices (manual) or daily auto-export.

### UX/UI analysis
- **Navigation:** Integration/Sales-Integration record with tabbed config (Webhooks, Inventory, Markets & Catalogs, Sale Orders, Customers); an **auto-workflow "visual pipeline"** for order processing status.
- **Status/diagnostics (best-in-class):** **traffic-light webhook health** with a **named cause** for the common failure ("callback URL mismatch → check `web.base.url`"); **Preview/Report dry-run** before export; per-line "internal info" for failed fulfillments; **Failed Job Notifications** on user profiles; an explicit **irreversible-action warning** on cancel; honest **"no PII on Basic plan"** disclosure.
- **Friction:** **install is technical** (odoo.conf/queue_job/workers) — not Odoo-Online-installable; advanced field-mapping (custom Python) is power-user territory; some marketing/ecosystem/Apps inconsistency (versions/pricing).
- **Overall:** the **most polished operational UX + diagnostics** of the survey, aimed at competent admins; install is the main onboarding hurdle.

### Reliability and robustness analysis (strongest, and **demonstrated by dated release notes**)
- **Idempotency:** ✅ GraphQL `@idempotent`-style directives (v2.1.4, v2.1.6) — **matches the Tier-1 2026-04 requirement**; prevents double refunds / duplicate inventory on retry. **Retry/recovery:** ✅ automatic retry of safe ops after network/server errors (v1.13.0); VIES 3× retry; failed steps restartable; "Run Now". **Queue/jobs:** ✅ true background job queue (`queue_job`) — *the only connector built on a real async queue per evidence.* **Webhook security/reconciliation:** 🟨 HMAC-SHA256 + ✅ dated webhook-hardening fixes (cut-off/import-filter respect; store-URL-migration rejection fix) + traffic-light health. **Partial failure:** ✅ batching processes valid records even if some error. **Silent-data-loss:** ✅ **two CRITICAL fixes** (v2.1.6 paging/sorting; v2.1.2 timezone) — *transparently disclosed prior defects, now patched.* **Rate-limit:** 🟨/⬜ "avoid unnecessary API requests" only (no named throttle). **Audit:** ✅ "every sync action logged" + retention + trace logs; reviews praise logging + restartable jobs.

### Updates, release notes, and maintenance
- **The most transparent maintenance trail of the survey:** dated, mechanism-level release notes from **1.13.0 (2025-10-27) to 2.1.6 (2026-06-23)**, including a **major REST→GraphQL migration (v2.0.0, 2026-01-23)**, **Shopify API 2026-04 compliance (v2.1.4)**, and openly-disclosed CRITICAL bug fixes. Frequent cadence; automatic git updates; priority support. This is a strong **trust and currency** signal.

### Strengths (evidence-backed)
- **Real reliability engineering, demonstrably shipped** (idempotency, auto-retry, queue-based async, silent-skip fixes); **GraphQL + 2026-04 compliance**; **best diagnostics** (traffic-light webhooks, dry-run, failed-job notifications); **B2B/VAT/VIES**, Markets, multi-company inventory, BoM stock, custom-Python field mapping; **transparent dated changelog**; Official Odoo partner with 300+ installs.

### Weaknesses / gaps
- **Technical self-hosted install** (odoo.conf/queue_job/workers; **not Odoo Online**) raises onboarding friction; **no payout reconciliation, POS, or gift cards** found; **no dedicated reporting/analytics**; connector-specific Odoo **permission model not detailed**; **rate-limit handling not named**; marketing/ecosystem/Apps **inconsistencies** (versions/pricing); subscription pricing may deter one-time buyers.

### What we can learn
- **Demonstrate reliability with dated release notes**; build on a **real async job queue**; ship **idempotency** aligned to Shopify 2026-04; **traffic-light health + named-cause diagnostics + dry-run + failed-job notifications**; **per-field directional mapping with safe transforms + live-data testing**; **B2B/VAT** support; **disclose and fix silent-data-loss bugs openly**.

### What we can do better
- **Make install effortless** (avoid hand-edited `odoo.conf`/queue_job for basic use; support Odoo Online if feasible, or a guided installer); add **payout reconciliation, POS, gift cards, and a real reporting dashboard**; add **named rate-limit/cost-aware throttling**; ship a **clear connector permission/access model**; keep **one consistent version/price** across surfaces.

### What to avoid
- Requiring **manual `odoo.conf` + queue_job + worker setup** as the only path to background jobs (high abandonment risk); leaving rate-limit handling unnamed; pricing/version drift across marketing vs Apps vs ecosystem; relying on a non-core OCA dependency without making it turnkey.

### Open questions
- Can install be made Odoo-Online-friendly or one-click? Payout reconciliation roadmap? Named rate-limit handling? Connector access-rights/record-rules model? Reconcile €499/yr vs $569.16 one-time. Full R4 coverage (17 unread Confluence articles).

---

## Competitor: Odoo Apps — ecommerce_shopify (R6)

> A **small, new, cron-based** module by **"Odoo IN Pvt Ltd"** (provenance
> unconfirmed). Marketplace listing only; **no UI screenshots, no ratings**, but
> a **fast recent release cadence** (May–Jun 2026). Its setup guide is the
> **blocked Google Doc (R5)**.

### Evidence status
- **Sources used:** R6 listing `apps.odoo.com/apps/modules/19.0/ecommerce_shopify` + author catalog. **Get Started guide → blocked Google Doc (R5)**, not bypassed.
- **Date accessed:** 2026-06-30 · **Access status:** Accessible (listing) / Blocked (setup doc).
- **Evidence strength:** Low–Medium — listing text + a dated changelog, but **zero screenshots, no ratings, 2 comments**; everything is **🟨 vendor claim** except metadata.
- **Claim classification note:** "real-time stock" was **verification-downgraded** — the listing's own automation section is **cron-based (10-min)**.

### Product positioning
- **Sells:** "Shopify Connector for Odoo 19" (`ecommerce_shopify`, **OPL-1**, **$195.56**) — "Modern API. Secure Auth. Clean ERP Sync." **Target:** Odoo 19 + Shopify merchants wanting central order/inventory/accounting; **India-publisher** signals (Razorpay ledger emphasis).
- **Odoo version:** **19.0 only** (a commenter asks about v18 → implies none). **Shopify side:** GraphQL Admin API + "OAuth + Self access". **Hosting:** self-hosted addon.
- **Pricing/license/support:** **$195.56 / OPL-1**; author **"Odoo IN Pvt Ltd"** (listing tagged **"Third Party"**; **no Odoo-Partner badge**); support via appointment booking; **3824 LOC**; **no ratings yet**.
- **PROVENANCE (open question — important):** third-party registries identify "Odoo IN Private Limited" as Odoo's **India entity** (CIN U72900GJ2007PTC050227) — an **inference**, **not confirmed by the listing** to be Odoo S.A. official. **Do not treat as the official baseline.**

### Feature scope (listing claims; cron-based)
- Connection/auth 🟨 (GraphQL + OAuth/Self access) · Product import 🟨 (name/price/images/variants) · Variants 🟨 (one Odoo product per variant) · Images 🟨 · **Product export ⬜ (direction unstated — sync described Shopify→Odoo)** · Mapping/dedup 🟨 (Automatic SKU-based; avoid duplicate customers) · Price lists ⬜
- Inventory sync 🟨/cron (downgraded from "real-time") · Multi-location 🟨 · Auto stock deduction on order 🟨 · Customer import 🟨 (plan-dependent) · Address handling 🟨 · Segmentation 🟨
- Order import 🟨 (auto into SO; status confirmed/shipped/cancelled; tagging) · Invoice creation 🟨 · Payment capture 🟨 · **Payment reconciliation / multi-ledger** 🟨 (Razorpay/Stripe) · Refunds 🟨 (record refund payments) · **Returns** 🟨 (added v19.0.2.0) · Fulfillment/tracking 🟨 (create/confirm delivery when fulfilled; tracking) — **backorder-based** (v19.0.2.1)
- **Webhooks ⬜ (none)** · Scheduled/cron ✅-described ("Orders 10 min; Pickings 10 min; Inventory after order sync; Products/Location initial-manual") · Manual sync 🟨 (date-range fetch under Developer Mode) · Queues/jobs ⬜ (none) · Error logs 🟨 (**email notifications**, consolidated v19.0.1.1) · Retry/recovery 🟨 ("Retry mechanism for failed sync" — no detail) · Tax 🟨 ("Create Taxes" v19.0.1.3)
- Multi-store ⬜ · Multi-company ⬜ · Markets ⬜ · Metafields ⬜ · Gift cards ⬜ · POS ⬜ · B2B ⬜ · Permissions ⬜ · Reporting ⬜ · Dependencies: Sales/Discuss/Invoicing/Inventory + community "eCommerce Engine"

### Workflow reconstruction (reconstructed from features + changelog — **no UI shown**)
- **Order→automation:** cron (or dev-mode date-range fetch) pulls orders → SO created → auto-confirm + invoice → stock deducted → inventory synced right after order sync → payment captured/reconciled → on Shopify fulfillment, Odoo delivery created (backorder-based) + tracking. **Error path:** consolidated failure email + a "retry mechanism" (no queue/log UI).
- **Setup:** listing says a "clear step-by-step flow" exists but the **actual steps are in the blocked Google Doc (R5)** — unknown.

### UX/UI analysis
- **Cannot be assessed** — the listing has **no interface screenshots or video**. Failure surface is **email-only** (no in-app queue/log). This is the **weakest visual/operational evidence** of the survey; buyers see no UX proof.

### Reliability and robustness analysis
- **Dedup:** 🟨 SKU mapping + avoid-duplicate-customers (no order-level idempotency stated). **Retry:** 🟨 unspecified. **Errors:** 🟨 email notifications (consolidated). **Queue/webhooks/rate-limit/audit/permissions:** ⬜ none found. **Sync model:** **cron polling (10-min)** — not real-time, no webhooks.

### Updates, release notes, and maintenance
- **Fast, dated cadence (a positive):** 19.0.1.1 (2026-05-18) → 19.0.2.1 (2026-06-16): consolidated failure emails, date-range fetch, "Create Taxes", **returns/refunds (v19.0.2.0)**, backorder-based fulfillment. Suggests **active early-stage development** — but **small scope (3824 LOC)** and **no adoption signal** (no ratings, 2 comments).

### Strengths (evidence-backed)
- **Active recent development** with a transparent dated changelog; a focused order→invoice→delivery→tracking loop; consolidated failure emails; **lowest complexity** (could mean easy onboarding **if** the blocked guide is good).

### Weaknesses / gaps
- **No webhooks** (cron-poll only); **no queue/in-app logs** (email only); **no screenshots** (no UX proof); **no ratings/adoption**; **small scope** (Markets/metafields/gift cards/POS/B2B/multi-store/reporting all absent); **product export direction unclear**; **provenance unconfirmed**; **setup guide is sign-in-gated**.

### What we can learn
- A **lean, fast-iterating** module can ship the core loop quickly; **consolidating failure emails** into one digest is a nice touch; a tight cron cadence (10-min) is simple to reason about.

### What we can do better
- Add **webhooks + an in-app queue/log** (email-only is a recovery dead-end); **publish UX screenshots**; **don't gate the setup guide** behind sign-in; clarify provenance/official status; broaden scope (Markets/metafields/multi-store) without bloating.

### What to avoid
- **Email-only error handling** with no in-app recovery surface; **cron-only, webhook-less** sync sold as "real-time"; **zero-screenshot listings**; **sign-in-gated getting-started docs**; ambiguous official-vs-partner provenance.

### Open questions
- Official vs partner (Odoo IN Pvt Ltd)? Does product **export** (Odoo→Shopify) exist? Any webhooks/queue/multi-store? What's in the blocked setup Google Doc (R5)? Real adoption (no ratings)?

---

## Competitor: Odoo Apps — sh_shopify_connector (R8, Softhealer)

> The **broadest feature surface** of the survey (gift cards, abandoned-checkout→
> CRM, product recommendations, Buy-with-Prime, queue dashboard + daily activity
> chart), demonstrated through a **~29-group screenshot walkthrough** — but with
> **no ratings and no dated changelog** to corroborate, and "real-time" framing
> that is actually queue/cron + optional webhook.

### Evidence status
- **Sources used:** R8 listing `apps.odoo.com/apps/modules/19.0/sh_shopify_connector` (price/license/deps/LOC + ~29 captioned screenshot groups + verbatim steps) + Softhealer Base store page. Flagship product page **404**.
- **Date accessed:** 2026-06-30 · **Access status:** Accessible.
- **Evidence strength:** Medium–High for **breadth/behaviour** (detailed captioned walkthrough); **Low for trust** (**no ratings, no dated changelog**, pixels not inspected).
- **Claim classification note:** the captioned walkthrough makes many areas **✅ demonstrated** (concrete screens/steps), but "Real Time Inventory Sync" / "Webhook Automation (Real time)" were **verification-flagged** as marketing — core sync is **queue/cron + optional webhook**; **multi-company** was **downgraded to not-found**.

### Product positioning
- **Sells:** "Shopify-Odoo Connector" (`sh_shopify_connector`, **OPL-1**, **$168.81** — the **cheapest** of the set) by **Softhealer Technologies** (self-reported 10K+ customers, 11+ years). **Target:** Odoo merchants wanting the **widest** Shopify feature coverage at a low price.
- **Odoo version:** **12.0–19.0**. **Shopify side:** custom app + credentials + Authenticate; GraphQL + webhooks. **Hosting:** Odoo Online / Odoo.sh / On-Premise (vendor history).
- **Pricing/license/support:** **$168.81 / OPL-1**; **18,951 LOC** (largest codebase of the set); deps incl. CRM/Contacts/Inventory/Invoicing/Sales/eCommerce/Discuss/Calendar/Website + community **Base Integration (`sh_integration_base`, $9.11)**; "lifetime free support". **No ratings / no dated changelog on the listing.**

### Feature scope (broadest; ✅ via captioned walkthrough)
- Store/instance + auth ✅ (custom app → Authenticate → status **Done** → Sync Logs) gated by **"Shopify Configuration Manager" access right** · GraphQL 🟨
- Product import ✅ (desc/images/categories/date-range/warehouse/tags) · Product export ✅ (**Shopify ID write-back**; "Export Based On"/Update) · Variants 🟨 (variant rows; per-variant stock export) · Images 🟨 · **Exclude-from-sync** ✅ · **Publish/unpublish via sales channels** ✅ · **Auto Sync to Shopify** toggle ✅
- Contact import ✅ (email/phone/address/tags/date-range; Contact Queue) · Contact export ✅ · Address handling ➖
- Order import ✅ ("Sync Orders Based On"; Orders Queue draft/completed/failed) · Order export ✅ (line items/discounts/tags/attrs; gated to confirmed orders; **export log history**) · **Payment Gateway Workflow Matrix** ✅ (route per gateway) · **Auto Sale Workflow** ✅ (auto invoice/validate-delivery/register-payment/force-transfer) · Invoice ✅ · **Refunds/returns** ✅ (credit notes; full/partial/restock/multi-currency; export back) · Fulfillment ✅ (validate delivery → queue done + **fulfillment ID** → Shopify status) · **"Needs Shopify Re-Export"** recovery flag ✅
- Inventory sync ✅ (per-variant Export Stock via Actions; "Real Time" is marketing) · Multi-location 🟨 · Multi-store 🟨 ("multiple instances in one Odoo DB") · **Multi-company ⬜ (not found on re-fetch)**
- **Webhooks** ✅ (Shopify Settings›Notifications›Webhooks; products/contacts/orders/fulfillment) · Scheduled/cron ✅ · Manual sync ✅ · **Queue Dashboard Framework** ✅ (Contact/Product/Order/Checkout/Recommendation queues; draft/completed/failed; "Process Queues Manually") · **Error/Sync logs** ✅ (Sync Logs + Export Log history) · Retry/recovery ✅ (re-export flag; manual re-process) · Duplicate prevention 🟨 (ID write-back implies linking; no explicit dedup-key statement)
- **Metafields** ✅ (per-entity, directional, single + bulk) · **Gift cards** ✅ (import/export/**disable-in-Shopify**; masked code/balance/expiry) · **Abandoned checkouts → CRM leads** ✅ (recovery routing) · **Product recommendations** ✅ (alternative/accessory; GraphQL queue + batch; bulk) · **Buy with Prime** ✅ · Date-range filters ✅ · **Permissions/security** ✅ (granular access-rights groups) · **Dashboard/reporting** ✅ (**Shopify Integration Dashboard** + **"Daily Queue Activity Tracking" chart**)
- Markets ⬜ · POS ⬜ · B2B ⬜ · Payout reconciliation ⬜ · Price lists/multi-currency-pricing ⬜ (only multi-currency refunds) · Updates/changelog ⬜ (**none dated on listing**)

### Workflow reconstruction (✅ — captioned step flows)
- **Connect:** enable "Shopify Configuration Manager" access right → Shopify Develop Apps → credentials → Odoo Authenticate → status **Done** → Sync Logs confirm token.
- **Import products/orders:** enable toggle → "Sync Products/Orders" (optional date range / "Based On") → **Queue** (draft/completed/failed) → "Manually Import" or cron → "Open Record" → verify; failures counted in the queue dashboard + Sync Logs.
- **Order export/re-export:** confirmed SO → "Export to Shopify" → Shopify Order ID/Name/Sequence; cancelled/updated → **"Needs Shopify Re-Export"** → Scheduled Action "Run Manually" → flag auto-cleared.
- **Refund:** "Import Refunds" → credit note; or credit note → "Export Refund to Shopify" → "Send to Shopify". **Fulfillment:** "Export Order Status" → Validate delivery → queue done + fulfillment ID.
- **Advanced:** gift card import/export/disable; abandoned checkout sync → CRM leads; recommendation mapping → GraphQL queue → process/bulk; metafield directional sync.

### UX/UI analysis
- **Navigation:** tabbed connector config (Products/Contacts/Orders/Refunds/Gift Cards/Abandoned Checkouts/Recommendations) + a **central Shopify Integration Dashboard**; setup **gated behind an Odoo access right** (good security default).
- **Status/monitoring (a strength):** **Queue dashboards with draft/completed/failed counts**, a **"Daily Queue Activity Tracking" time-series chart**, **Sync/Export Logs** audit tables, and a **"Needs Shopify Re-Export" recovery flag** — strong **operational visibility**.
- **Friction:** **breadth → surface area** (many tabs/toggles); "Real Time" labels overstate a queue/cron+webhook model; **no ratings/changelog** undercuts trust in the breadth; pixel-level UX unverified.
- **Overall:** **the most operationally instrumented dashboard** of the survey (activity chart, failure counts, re-export flag), wrapped around the **widest feature set**, but with the **weakest external trust signals**.

### Reliability and robustness analysis
- **Queue/jobs:** ✅ multi-entity queue dashboards with **explicit failed counts** (partial-failure visible) + "Process Queues Manually". **Retry/recovery:** ✅ **re-export flag** auto-set/cleared; manual re-process (no auto-backoff stated). **Audit:** ✅ Sync Logs + Export Log history (status/timestamp/details). **Webhooks:** ✅ create/update for contacts/products/orders/fulfillment (no documented HMAC/dedup/ordering). **Idempotency:** 🟨 ID write-back implies linking; **no explicit dedup-key/idempotency statement**. **Rate-limit:** ⬜ "GraphQL efficient" only. **Permissions:** ✅ granular access-rights groups.

### Updates, release notes, and maintenance
- **No dated changelog on the listing** (version badges 12.0–19.0 only) — a **transparency gap** vs R6/R7. **No ratings/reviews/downloads** shown. Flagship vendor product page **404** (couldn't cross-check). Large LOC (18,951) implies substantial scope but **maintenance currency is unverifiable**.

### Strengths (evidence-backed)
- **Widest feature coverage** (gift cards, abandoned-checkout→CRM, recommendations, Buy-with-Prime, metafields); **strong monitoring dashboard** (activity chart + failure counts + audit logs + re-export recovery); **access-rights gating**; **lowest price**; **ID write-back linking**; payment-gateway workflow matrix.

### Weaknesses / gaps
- **No ratings, no dated changelog, flagship page 404** → weak trust/currency signals; **"real-time" overstated**; **multi-company unverified**; **no Markets/POS/B2B/payout reconciliation**; **no explicit idempotency/dedup keys** or HMAC/reconciliation detail; pixel UX unverified.

### What we can learn
- A **monitoring dashboard with a daily activity chart + failure counts + audit logs + a re-export recovery flag** is a compelling operational UX; **gate setup behind an access right**; **ID write-back** for linking; cover **high-value extras** (gift cards, abandoned-checkout→CRM, recommendations) that others skip.

### What we can do better
- **Earn trust the breadth lacks**: publish a **dated changelog, ratings, and a working product page**; state **idempotency/dedup keys and HMAC verification** explicitly; **don't label cron/queue "real-time"**; add Markets/payout reconciliation; verify multi-company.

### What to avoid
- **Breadth without trust signals** (no ratings/changelog/working page); **"real-time" marketing** over a queue/cron model; leaving **idempotency/HMAC** unstated; a 404 flagship page; over-broad surface area without guided onboarding.

### Open questions
- Real adoption/satisfaction (no ratings)? Current maintenance (no dated changelog)? Multi-company real? Idempotency/dedup keys and webhook HMAC? Markets/payout roadmap? Is the breadth actually robust or thin-per-feature?

---

## Source: Project Google Doc / internal resource (R5) — BLOCKED

### Evidence status (blocked-source record)
- **Source:** `https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit` — title **"E-commerce user documentation"**.
- **Exact status:** **Blocked** — Google **sign-in wall**; only the title is exposed; body gated. Unchanged across Sprints A/B/C.
- **What was attempted:** a normal anonymous WebFetch (returns only the title + a "Sign in" wall, redirecting to `accounts.google.com`). A re-fetch in the verification pass confirmed the wall.
- **What was NOT attempted:** **no authentication, no bypass, no credential use** (per `CLAUDE.md` §7.6). **No content was inferred** beyond the visible title.
- **What is needed to unblock:** the **owner must grant view access** (e.g. to aysaadab@gmail.com), set link-sharing to "Anyone with the link", **or provide an export** (PDF/DOCX/HTML).
- **What cannot be concluded:** anything about its content, scope, sync model, or whether it is our spec vs general e-commerce docs.

### New cross-source finding (Sprint C)
- **R5 is almost certainly the "Get Started" guide for R6 `ecommerce_shopify`.** R6's on-listing "Get Started" CTA (`odoo.com/r/ecommerce-shopify`) **301-redirects to this exact Google Doc.** This is an **inference** from the redirect, not confirmed content. It remains **Blocked**; content is **not** inferred. (This also means R6's setup steps are themselves gated.)

### Open questions
- Will the owner grant access/export? Is it R6's setup guide, our own connector spec, or general e-commerce documentation? (Decision for ChatGPT.)

---

## Cross-competitor synthesis (inference — not decisions)

> A one-screen orientation. **Inference/recommendation only**; the structured
> matrix is in [`competitor-feature-matrix.md`](./competitor-feature-matrix.md)
> and patterns/gaps in the Stage-5 files. No MVP/architecture is decided here.

| Competitor | Price (2026-06-30) | Sync model | Evidence quality | Standout strength | Biggest weakness |
| --- | --- | --- | --- | --- | --- |
| **Webkul** (R1) | $170 | cron import + event export; **no webhooks** | Med (1 guide) | Feeds staging + error queue | no webhooks/multi-location; gaps in variants/images/refunds |
| **Teqstars** (R2) | $326.20 | **real-time webhooks + cron** (claimed) | **Low** (docs 403) | strong on-paper breadth; 83×5.0 | **unverifiable** (docs blocked) |
| **Emipro** (R3) | n/a in docs | webhooks + cron + manual | **High (behaviour)** | best **observability** (queues + Log Book); finance-grade | **no auto-retry**; manual stock-adjust; stale v19 changelog |
| **VentorTech** (R4+R7) | €499/yr · $569.16 | **webhooks (real-time) + scheduled**, queue_job | **High (dated notes)** | **real reliability eng.** (idempotency/retry/queue); best diagnostics | **technical install** (not Odoo Online); no payouts/POS/gift cards |
| **ecommerce_shopify** (R6) | $195.56 | **cron 10-min; no webhooks** | Low (no shots/ratings) | fast recent cadence; lean | email-only errors; tiny scope; provenance/setup gated |
| **sh_shopify_connector** (R8) | **$168.81** | queue/cron + webhook | Med–High breadth / Low trust | **widest features** + monitoring dashboard | **no ratings/changelog**; "real-time" overstated; idempotency unstated |

**Headline inferences (gated):**
1. **The reliability bar is set by VentorTech and Emipro** — a real **job queue**, **idempotency** (Shopify 2026-04), **reason-coded error logs**, **dry-run/validation**, and **traffic-light diagnostics**. Webhook-less, email-only designs (R6) and unverifiable claims (R2) are the floor.
2. **Webhooks + reconciliation + idempotency** is the emerging table-stakes pattern — and aligns exactly with our Tier-1 Shopify findings (delivery-not-guaranteed → reconcile; `@idempotent` from 2026-04).
3. **"Real-time" is routinely overstated**; most are queue/cron with optional webhooks. Our product should be **honest about latency** and **strong on reconciliation**.
4. **Trust signals matter:** dated changelogs (R6/R7), ratings (R2/R7), readable docs+screenshots (R3), and a non-gated setup guide (counter-example: R5/R6) materially affect evaluability.
5. **Differentiation whitespace** (no single competitor does all well): effortless install **and** real reliability; payout reconciliation **with** demonstrated robustness; unified observability dashboard **with** idempotency; honest latency; clear permission model. (Developed in `gaps-opportunities.md`.)

