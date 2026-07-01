# Competitor Source Notes (Research Sprint C)

> **Purpose.** Raw but organized, cited, claim-classified source notes from each
> user-provided competitor resource (R1–R8). This is **source grounding, not
> analysis** — the analysis lives in
> [`../01-research/competitor-deep-dives.md`](../01-research/competitor-deep-dives.md).
>
> - **Access date for every observation below:** **2026-06-30.**
> - **Rules honoured (`CLAUDE.md` §7–§8, `research-methodology.md`):** normal
>   anonymous access only; **no authentication wall was bypassed**; gated content
>   recorded as Blocked/Partial, never captured. Every observation carries an
>   exact evidence URL and a **claim class**: `on-page fact` (price/license/
>   version/author literally on the page), `competitor claim` (vendor capability
>   statement, not proven), `visible demonstrated workflow` (a documented
>   step-by-step flow and/or screenshot shows it), `blocked/unknown`, or
>   `inference` (our deduction, labelled).
> - **Evidence gathering:** a controlled high-power parallel fan-out (one
>   capture agent per source + an adversarial verification pass per source — see
>   the Sprint C plan in `../01-research/research-handoff.md`). Pages were read
>   via the proxy fetcher (page→markdown), so exact pixel detail of screenshots
>   is approximate; field labels and captions are reliable.
> - **Tier reminder:** these are all Tier 2–5 sources → **competitor claims and
>   on-page facts**, never Tier-1 technical facts. Tier-1 facts come only from
>   the official Shopify/Odoo baselines (`../01-research/shopify-official-api-notes.md`,
>   `../01-research/odoo-official-architecture-notes.md`).

---

## R1 — Webkul: Odoo Multichannel Shopify Connector (blog/guide)

### Access status
- **URL:** https://webkul.com/blog/odoo-multichannel-shopify-connector/ (+ store page https://store.webkul.com/odoo-multichannel-shopify-connector.html)
- **Date accessed:** 2026-06-30
- **Access status:** **Accessible** (both pages HTTP 200; no auth wall; price visible without sign-in)
- **Pages/sections reached:** Full blog user-guide (overview, key features, Shopify-app setup, Odoo connection, Basic/Sales/Product settings, cron, Feeds, mappings, synchronization history); store listing (price, version, license, dependency, dates).
- **Pages/sections blocked:** None.
- **Notes on authentication/gating:** None. Pricing is on the **store** page (the blog points to a "Buy Now" link), resolving the Sprint A/B open question.

### Raw source observations
- Product self-states **Odoo V19/V18/V17** (blog) and **10.x–19.x** (store). — blog/store — `on-page fact` (screenshot: no)
- **Version discrepancy:** blog "Current Product Version - 1.0.0" vs store "3.5.1". — `on-page fact` (do not reconcile; cite each separately).
- **Price $170.00 USD** (store; EUR/INR also offered). — store — `on-page fact`.
- Built on the **Webkul "Odoo Multi channel sale" base module** (must be installed first). — store — `on-page fact`.
- Claims the **Shopify GraphQL API** "for faster synchronization, reduced API calls". — blog — `competitor claim`.
- Setup: create Shopify custom app → Redirect URL `{ODOO-URL}/shopify_odoo_bridge/redirect` → grant scopes → Client ID/Secret → Odoo Connect → **Test Connection**. — blog — `visible demonstrated workflow` (screenshots S1–S7).
- Imports categories/products/orders/customers with filters **all / ID / Date updated after / Date created after**; mandatory order **categories » product » order**. — blog — `visible demonstrated workflow`.
- **Feeds** staging area evaluates incoming data; bad data is flagged an **"error feed"**; fixable + re-evaluable without a developer. — blog — `competitor claim` (Feeds list shown S14; the re-evaluate retry itself is described in text).
- **Duplicate prevention** via Internal Reference (SKU) + Barcode, plus a global "Avoid Duplicity (Default Code)" toggle. — blog — `competitor claim`.
- **Inventory:** single default Warehouse/Location; Stock Action = on-hand or forecasted; real-time stock push Odoo→Shopify on stock movement when "Auto Stock" enabled. — blog — mixed `visible demonstrated workflow` (config) + `competitor claim` (real-time).
- "Import of shipping method is not available." — blog — `on-page fact` (explicit absence).
- **No webhook mechanism documented**; inbound is cron/poll-based. — blog — `inference` (absence on accessed pages).

### Important quotes or paraphrases
- "Supports Shopify GraphQL API for faster synchronization, reduced API calls…" — https://webkul.com/blog/odoo-multichannel-shopify-connector/
- "If enabled, stock will be synced from Odoo to Shopify in real time whenever there is a stock movement." — same
- "it first appears in the 'Feeds' section" … "it will be marked as an error feed" … "re-evaluate the feed without needing developer assistance" — same
- "Import of shipping method is not available." — same
- "$170.00" / "depends on the base multichannel sale module. Please install it first." — https://store.webkul.com/odoo-multichannel-shopify-connector.html

### Update/release/patch notes captured
- Blog: **"Updated 29 June 2026"** (prior note 4 Dec 2025); states version 1.0.0. — `on-page fact`.
- Store: **"Last Update June 8, 2026"**, "Released 6 years ago", version 3.5.1. No detailed changelog on either page. — `on-page fact`.

### Open questions from this source
- Which version is authoritative (1.0.0 vs 3.5.1)? Product variants/options, image/media sync, invoice creation, refunds/returns, payment/payout, webhooks, multi-location, multi-store, Markets, B2B, POS, Odoo-side permissions, and reporting were **not found** on the accessed pages. Customer **export** (Odoo→Shopify) not found (only import).

---

## R2 — Teqstars: Shopify Connector for Odoo (docs 19.0 + Odoo Apps listing)

### Access status
- **URL (prompt target):** https://docs.teqstars.com/19.0/applications/shopify/overview.html
- **Date accessed:** 2026-06-30
- **Access status:** **Blocked** for the docs (HTTP **403** bot-block on the whole `docs.teqstars.com` host, including the **16.0** mirror and `teqstars.com`); **a separate, accessible Teqstars source was found:** the Odoo Apps Store listing **https://apps.odoo.com/apps/modules/19.0/shopify** (HTTP 200). The verification pass **downgraded the docs from Partial→Blocked** (the prior "Partial" rested on search-index snippets, not direct page access).
- **Pages/sections reached:** Odoo Apps Store 19.0 listing (price/license/version/author/reviews + vendor feature list and 17 screenshot captions).
- **Pages/sections blocked:** All `docs.teqstars.com/19.0/...` and `/16.0/...` pages (403); `teqstars.com` blog (403).
- **Notes on authentication/gating:** **There is no login wall — it is a WAF/bot-block (403).** No bypass was attempted. Indexed search snippets were used only as explicitly-labelled, non-equivalent fallback and are **not** treated as 19.0 facts.

### Raw source observations
- **Price $326.20**, **License OPL-1**, author **"TeqStars"**, **v 19.0**, **83 reviews / 5.0 stars**, ~28,630 LOC, technical name **"shopify"**. — apps.odoo.com — `on-page fact`. *(EUR 399.99 is a conversion, NOT literally on the page — do not cite as on-page fact.)*
- "**GraphQL native (from v1)**" / "Built on Shopify's GraphQL API from v1". — apps.odoo.com — `on-page fact` (vendor positioning string is literally present) / `competitor claim` (as a technical guarantee).
- **Dual sync model**: "Real-time push. Requires HTTPS." (webhooks) + "Cron-based automation." — apps.odoo.com — `competitor claim` (literal strings present).
- **Smart product matching** "SKU, Barcode, or both". — apps.odoo.com — `competitor claim`.
- **Queue Manager**: "One bad record won't block 999 good ones" (per-record error retry). — apps.odoo.com — `competitor claim`.
- **Image dedup** "Avoids duplicate uploads via pHash" (perceptual hashing). — apps.odoo.com — `competitor claim`.
- **Payments**: "Map payment gateways to Odoo journals"; **payout report import**; "Auto reconciliation on Enterprise". — apps.odoo.com — `competitor claim` (edition-gating is a vendor statement).
- **Multi-store** "Unlimited stores. Each with own warehouse". — apps.odoo.com — `competitor claim`.
- Order import incl. **POS orders, gift cards, duties, tips, taxes**; refunds/partial refunds; cancellations; fulfillment + tracking export; metafields with conditions/transformations; Shopify Markets & B2B catalog pricing; fraud risk scoring; collections CRUD; Colorado special tax. — apps.odoo.com — `competitor claim`.
- Localized into **10 languages**; depends on Sales, Discuss, Invoicing, Inventory + a "Base Marketplace" community app. — apps.odoo.com — `on-page fact`.

### Important quotes or paraphrases
- "Odoo Shopify Connector (GraphQL Powered)" — https://apps.odoo.com/apps/modules/19.0/shopify
- "$ 326.20" / "OPL-1" / "TeqStars" / "v 19.0" — same
- "One bad record won't block 999 good ones" / "Avoids duplicate uploads via pHash" / "Unlimited stores. Each with own warehouse" — same
- Indexed snippet (non-equivalent, docs 403): "idempotency directives for inventory and refund operations, preventing duplicate inventory changes and double refunds when retrying" — docs.teqstars.com (UNVERIFIABLE; competitor claim only).

### Update/release/patch notes captured
- Listing access date 2026-06-30; current 19.0 edition rebuilt on Shopify GraphQL. **No directly-readable, dated 19.0 changelog** (docs 403). An indexed snippet claims a **2026-04 Shopify API** compliance update with idempotency directives — **unverifiable**, recorded as a competitor release claim only.

### Open questions from this source
- The entire `docs.teqstars.com` host (19.0 and 16.0) is 403-blocked — exact 19.0 docs text, field labels, and rendered screenshots remain unverifiable. A "PRO" variant appeared in search (`integration_shopify` is **VentorTech**, not Teqstars — possible search confusion); do not attribute "PRO" detail to this module. Rate-limit handling, Odoo permission model, and multi-company (vs multi-store) not establishable.

---

## R3 — Emipro: Shopify Odoo Connector documentation (v19)

### Access status
- **URL:** https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/installation.html (+ ~35 sub-pages)
- **Date accessed:** 2026-06-30
- **Access status:** **Accessible** (all v19 pages HTTP 200; "Just the Docs" static site; server-rendered HTML; no auth wall). **Richest, most demonstrative doc tree of the set.**
- **Pages/sections reached:** ~35 sub-pages incl. setup/token (Path A & B), product config/management (import/export/map/stock), order config + webhook-order config, stock information, operations (import customer/location, **queue**, scheduler), orders (unshipped/shipped/cancel/return-refund manual + webhook, grant-fulfillment-scopes), export-customer, export-sale-order, **webhooks**, **Markets**, **metafields**, channel/analytic mapping, sales report & log book, **payouts**, net profit report, release notes.
- **Pages/sections blocked:** None (docs-only — **no price/license/author** anywhere in the tree).
- **Notes on authentication/gating:** None.

### Raw source observations
- Setup uses a **custom Shopify app + access token**; Odoo wizard "Set Shopify Authorization Details" exchanges App URL + Callback/Redirect URL; "Any mismatch — including a trailing slash — will cause the authorization to fail." — `visible demonstrated workflow` (screenshots).
- Requires a **large fixed scope string** (read_all_orders, products, customers, fulfillments, inventory, locations, gift_cards, returns, shopify_payments_payouts, metaobject_definitions, order_edits). — `on-page fact` (scope screenshot).
- **Batch Data Queues**: "125 products … 50 orders per queue"; Draft/Failed/Cancelled/Done; "Process Queue Manually"; **Force Done is irreversible**; per-line **Log Lines**; processed ribbon. — `visible demonstrated workflow` (5 screenshots).
- **Automatic Scheduler** crons: Import Orders / Shipped / Cancel / Update Status / Payout Reports / Bank Statement / Export Stock; per-job Time/Execution/User. — `visible demonstrated workflow`.
- **Webhooks** for product create/update/delete, order create/update, customer create/update; **SSL required**; Shopify "5s timeout, **19 retries over 48h**, subscription deleted after 19 consecutive failures". — `visible demonstrated workflow`. ⚠️ **The 19/48h figure is the now-OUTDATED Shopify number** (our Tier-1 baseline: **8 retries / 4h** since some date — see DP-001). Recorded as a **competitor-doc accuracy gap**.
- Webhook order import "only imports the orders which are placed from Shopify Website and not from Shopify Admin Panel." — `on-page fact` (explicit limitation).
- **Import Stock** generates **Inventory Adjustment records that must be processed manually** ("You will have to process that Inventory Adjustment transaction record manually…"). — `visible demonstrated workflow` (friction point).
- **Customer export dedup**: links existing Shopify customer by **email** instead of creating a duplicate; no-email/child-address/already-linked skipped; requires GraphQL. — `visible demonstrated workflow`.
- **Shopify Markets**: per-market Company/Warehouse/Pricelist/Fiscal Position/Language/Credit-Note journal; order matched by **country → currency → fallback**; "Markets are created automatically by sync. You cannot create them manually."; "Delivery from multiple warehouses is currently not supported with Shopify Markets." — `visible demonstrated workflow`.
- **Metafields** (product/variant/order/customer) with Fetch Scope + Sync Direction Import/Export/Both; only custom-namespace auto-activated. — `visible demonstrated workflow`.
- **Payouts**: Shopify Payments only ("External or 3rd party payment service providers cannot be managed"); import → Generate Bank Statement → reconcile. — `visible demonstrated workflow`.
- **Net Profit report**: "applicable for the enterprice edition only." — `on-page fact`.
- **Log Book / Mismatch Log** (Processes » Log Lines) records failures with reasons (SKU not found, tax not found, auto-workflow not found, customer missing). — `visible demonstrated workflow`.
- Multi-payment order → two payment lines in a "Multi Payments" section. — `visible demonstrated workflow`.

### Important quotes or paraphrases
- "In each queue, there will be 125 products… for Sales Order, there will be 50 orders per queue." / "If you Force Done the queue… it cannot be processed further anymore." — queue.html
- "If there are 19 consecutive failures, then the Webhook subscription… is deleted." / "only instances having an SSL connection (HTTPS://) are permitted." — webhooks-configuration.html
- "You will have to process that Inventory Adjustment transaction record manually…" — import-stock.html
- "If a customer with the same email already exists in Shopify, the connector links the Odoo record…instead of creating a duplicate." — export-selected-customers.html
- "External or 3rd party payment service providers cannot be managed with this feature." — shopify-payouts.html

### Update/release/patch notes captured
- **Release Notes page on the /v19/ path lists entries only up to 17.0.3.2 (April 18, 2024)** — **no v18/v19-dated entries**; pre-17.0.0.3 directs to a support ticket. Path A note says "Shopify Connector version should be 19.0.3.0 or higher". 17.0.1.1 (Jan 9 2024) = "Updated to Shopify API version 2024-01". — `on-page fact` (a **maintenance/freshness signal**: the published changelog is stale on the v19 path).

### Open questions from this source
- **No price/license/author** in docs (Odoo Apps/Emipro shop not in R3 scope). No connector-side **rate-limit/throttle** handling described. **No automatic retry/backoff** for failed Odoo-side queue jobs (recovery is manual). B2B (company accounts/catalogs) not found. The interaction between "Is Delivery from Multiple warehouse?" and Markets' no-multi-warehouse limitation is unclarified.

---

## R4 — VentorTech: Shopify documentation (Confluence)

### Access status
- **URL:** https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify (R&D Products Documentation, space `pd`)
- **Date accessed:** 2026-06-30
- **Access status:** **Partial** (hub + 11 child articles loaded anonymously HTTP 200; persistent banner "You're viewing this with anonymous access, so some content might be blocked."). Verification confirmed Partial.
- **Pages/sections reached:** Hub (28-article tree visible) + **11 child articles read in full**: webhooks, multi-location, auto-update products, pricelists→catalogs, historical orders, fulfillments, metafields, POS, default-customer/PII, order-risk, cancel-orders.
- **Pages/sections blocked:** **17 of 28** listed child articles **not fetched this session** (recorded as **not-read, not gated** — e.g. order tags, SEO fields, compare-at price, taxes import, archived/draft products, business-entity order filtering, deliveries with e-commerce connectors, share-Shopify-access). The anonymous banner means some embedded content **may** be hidden, but no per-page sign-in wall was hit.
- **Notes on authentication/gating:** No auth bypassed. Hub author **Kirill Vorobey**, **Updated Nov 19, 2023** (predates Odoo 19). **Odoo version is NOT stated** anywhere on the accessed pages.

### Raw source observations
- **Webhook health traffic-light**: green = active; **yellow = callback URL mismatch (check `web.base.url`)**; red = inactive; "Create Webhooks"/"Delete Webhooks" (dev mode) recreate path. Events: Order Create/Paid/Cancel/Fulfill/Partially Fulfill + product create/update/delete. — `visible demonstrated workflow`.
- **Multi-location** via an "**External Location**" column (Odoo warehouse ↔ Shopify location); empty → Default Shopify Location. — `visible demonstrated workflow`.
- **Pricelists → Shopify Catalogs (Markets)**: Import Markets and Catalogs → map → **Preview/Report dry-run** → Send Prices (manual) or daily "Pricelist Prices Calculation & Export". "detect issues before sending data"; "Odoo to act as the single source of truth for pricing". — `visible demonstrated workflow`.
- **Historical orders**: filter by cut-off date, order/financial/fulfillment status; "Any order created before your cut-off date will never be imported."; **connector <1.13.2 = REST (read_orders); 2.0.0+ = GraphQL (read_all_orders for >60-day orders)**. — `visible demonstrated workflow` for the flow; the version/scope mapping treated as **competitor claim** (sub-page, not on hub).
- **Fulfillments**: e-Commerce Integration tab table (products/qty/carriers/tracking); "Fetch and Apply from external"; per-line manual Apply or auto "Apply External Fulfillments"; "Force Full Fulfillment"; per-line "internal info" diagnostic; "Enable Order Tracking Export Job"; per-warehouse transfers need `sale_sourced_by_line`. — `visible demonstrated workflow`.
- **Order risk** imported with order (Risk level, Sentiment, Action Recommended). — `visible demonstrated workflow`.
- **Cancel from Odoo→Shopify**: two-step (cancel in Odoo — irreversible — then push), with reason/staff-note/restock/refund/notify; paid+shipped can't cancel until fulfillments removed ("Cancel e-Commerce Fulfillments"). — `visible demonstrated workflow`.
- **PII honesty**: on Shopify **Basic** plan the API returns no PII → orders go to a default customer or raise a missing-customer error. "Limited data access (no PII)". — `visible demonstrated workflow` (honest platform-limitation disclosure).
- **POS** import requires enabling "Closed" status + a default customer. — `visible demonstrated workflow`.

### Important quotes or paraphrases
- "When product quantity will be synced from Odoo to Shopify — quantities will be synced based on individual locations." — pages/521732182
- "detect issues before sending data" / "Odoo to act as the single source of truth for pricing." — pages/2338914308
- "Any order created before your cut-off date will never be imported." — pages/2106916865
- "After completing the first step, the Odoo order will be cancelled and cannot be undone." — pages/776470531
- "Limited data access (no PII)" — pages/866943004

### Update/release/patch notes captured
- Article-level "Updated" dates span **Dec 2023 → Oct 22 2025** (per-author bylines). Hub last updated **Nov 19, 2023**. Connector versions referenced: **<1.13.2 (REST)** and **2.0.0+ (GraphQL)**. — `on-page fact` (article metadata). Full dated release notes are on the **ecosystem** site (see R7), not Confluence.

### Open questions from this source
- **Odoo version compatibility not stated** on any accessed Confluence page. Pricing not here (see R7). 17 child articles unread. No explicit idempotency/retry/rate-limit guarantee on accessed pages. Standalone refunds/returns (vs cancel), payouts, invoice creation, gift cards, B2B, full customer/address mapping, dashboard/reporting, and the initial credential/OAuth wizard were not on the 11 pages read.

---

## R5 — Project Google Doc ("E-commerce user documentation")

### Access status
- **URL:** https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit
- **Date accessed:** 2026-06-30
- **Access status:** **Blocked** (Google **sign-in wall**; only the document **title** is exposed; body gated). Unchanged from Sprint A/B.
- **Pages/sections reached:** None of the body. Only title metadata.
- **Pages/sections blocked:** Entire document body.
- **Notes on authentication/gating:** Private doc; **no authentication bypassed; no content inferred** beyond the visible title.

### Raw source observations
- Title: **"E-commerce user documentation"**. — `on-page fact` (title only).
- **Cross-source link (new in Sprint C):** the **R6 `ecommerce_shopify`** listing's "Get Started" CTA (`odoo.com/r/ecommerce-shopify`) **301-redirects to this same Google Doc**. — `inference` (strong): **R5 is the getting-started/setup guide for R6**. Still blocked; content not inferred.

### Important quotes or paraphrases
- "E-commerce user documentation" (title only) — https://docs.google.com/document/d/1zIwRxp7.../edit

### Update/release/patch notes captured
- None obtainable (blocked).

### Open questions from this source
- Owner must **grant view access or provide an export** (PDF/DOCX/HTML). Its content — likely the `ecommerce_shopify` (R6) setup guide given the redirect — is unknown and not inferred.

---

## R6 — Odoo Apps: ecommerce_shopify (19.0)

### Access status
- **URL:** https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify
- **Date accessed:** 2026-06-30
- **Access status:** **Accessible** (HTTP 200; purchase needs login). The "Get Started" link → **blocked Google Doc (= R5)**.
- **Pages/sections reached:** Full listing (price, license, author, version, dependencies, feature list, **version history**, comments) + author catalog page.
- **Pages/sections blocked:** The "Get Started" guide (Google Doc R5).
- **Notes on authentication/gating:** Listing tagged **"Third Party"**; **no interface screenshots or video** on the listing (icon + 6 cross-promo banners only).

### Raw source observations
- **Price $195.56**, **License OPL-1**, author **"Odoo IN Pvt Ltd"**, **v 19.0 only**, **3824 LOC**, **"There are no ratings yet!"**. — `on-page fact`.
- **PROVENANCE (open):** listing shows no "Odoo Partner" badge; third-party registries identify "Odoo IN Private Limited" as Odoo's **India entity** (CIN U72900GJ2007PTC050227) — this is an **inference**, NOT confirmed by the listing that it is Odoo S.A. official. **Do not treat as the official baseline.**
- Built on **GraphQL Admin API** + "OAuth-based as well as Self access Authentication"; tagline "Modern API. Secure Auth. Clean ERP Sync." — `competitor claim`.
- **Cron-based sync** (the listing's own automation section): "Orders — every 10 minutes; Pickings — every 10 minutes; Inventory — right after order sync; Products/Location — initial manual". — `on-page fact` (the actual mechanism). The marketing bullet "Real-time stock updates from Odoo to Shopify" was **verification-downgraded** as contradicting the cron section.
- **No webhooks** mentioned anywhere; failure handling = "Email notifications for failures/errors" + "Retry mechanism for failed sync" (no in-app queue/log UI). — `competitor claim` / `inference` (no webhooks).
- Dedup: "Automatic SKU-based product mapping" + "Avoid duplicate customer creation" (no order-level idempotency stated). — `competitor claim`.
- Returns/refunds **added v19.0.2.0 (2026-06-04)**; multi-ledger payments (Razorpay/Stripe) claimed. — `competitor claim`.
- Depends on Sales, Discuss, Invoicing, Inventory + community **"eCommerce Engine" (odoo_ecommerce)**. — `on-page fact`.

### Important quotes or paraphrases
- "Modern API. Secure Auth. Clean ERP Sync." / "Shopify's latest GraphQL Admin API and OAuth-based as well as Self access Authentication" — listing
- "Automatic SKU-based product mapping" / "Avoid duplicate customer creation" / "Retry mechanism for failed sync" / "Email notifications for failures/errors" — listing
- "There are no ratings yet!" / "Hi, is there any v18 version in the roadmap?" (commenter) — listing

### Update/release/patch notes captured (frequent, recent — a freshness positive)
- **19.0.2.1 (2026-06-16)** backorder-based fulfillment handling; location on picking; inventory synced right after order sync.
- **19.0.2.0 (2026-06-04)** return & refund functionality added.
- **19.0.1.3 (2026-06-02)** "Create Taxes" config; taxes auto-matched/created.
- **19.0.1.2 (2026-05-29)** date-range order fetch; fetch button moved under Developer Mode.
- **19.0.1.1 (2026-05-18)** consolidated failed-order emails into one. — all `on-page fact`.

### Open questions from this source
- Official-vs-partner provenance unresolved. No webhooks, Markets, metafields, gift cards, POS, B2B, price-lists, multi-store/company, reporting found. **Product export direction (Odoo→Shopify) not stated** (sync described Shopify→Odoo). No ratings, 2 comment threads → thin adoption signal. Small codebase (3824 LOC) vs peers.

---

## R7 — VentorTech: Odoo Shopify Connector PRO (website + ecosystem + Apps Store)

### Access status
- **URL:** https://ventor.tech/solutions/odoo-shopify-connector/ (+ ecosystem product/shop pages, **Odoo Apps `integration_shopify`**, dedicated **release-notes** page, install/why-choose FAQs)
- **Date accessed:** 2026-06-30
- **Access status:** **Accessible** (6 VentorTech-owned pages HTTP 200; no auth wall). The **Apps Store listing and the dated release-notes page are the authoritative, current sources**; the `ventor.tech` marketing page is thinner and slightly stale ("from v13 and higher").
- **Pages/sections reached:** marketing solution page; ecosystem product + shop pages; Apps Store `integration_shopify`; **release-notes 1.13.0 → 2.1.6**; install/config FAQ (queue_job/odoo.conf); why-choose FAQ.
- **Pages/sections blocked:** None (Confluence deep docs = R4; not re-fetched here).
- **Notes on authentication/gating:** None. **Source-attribution discipline applies** — several strong claims are on the Apps Store/ecosystem pages, **not** the marketing page; each is cited to its specific URL.

### Raw source observations
- **Odoo Shopify connector PRO**, by VentorTech, **"an Official Odoo partner"**; **EUR 499** (marketing/ecosystem subscription/yr, renewal discounts 20%/40%) vs **USD 569.16** (Apps Store one-time). Technical name **`integration_shopify`**, **v 2.1.6 (last updated 2026-06-23)**, OPL-1, **3411 LOC**, **300+ installs**, **20 reviews**, Odoo **13.0–19.0**, **NOT Odoo Online** (self-hosted/Odoo.sh only). — `on-page fact`.
- **GraphQL** since **v2.0.0 (2026-01-23)** (migrated from REST); **v2.1.4 complies with Shopify API 2026-04**. — `visible demonstrated workflow` (dated release notes).
- **Idempotency**: v2.1.4 "GraphQL idempotency directives… prevent duplicate inventory changes and double refunds when retrying"; v2.1.6 extended to inventory-item activation. — `visible demonstrated workflow` (matches Tier-1 @idempotent 2026-04).
- **Background job queue** (depends on Integration Queue Job / OCA `queue_job`); install requires `server_wide_modules` + `queue_job channels root:1` + ≥2 workers in `odoo.conf`; v2.1.1 "Run Now" on jobs; v1.13.0 "Failed Job Notifications". — `visible demonstrated workflow` (install FAQ + release notes).
- **Webhooks**: "8 webhook events"; "Webhook security: HMAC-SHA256 signature check"; release notes harden webhooks (respect cut-off date/import filters; fixed rejection after store-URL migration). — `competitor claim` (HMAC marketing) + `visible demonstrated workflow` (dated fixes).
- **Auto-workflow**: "Automate up to 5 steps: confirm → ship → invoice → send → pay"; each step a background job; "Visual pipeline shows the status of every step". — `competitor claim`.
- **Field-mapping engine**: per-field direction control + **custom Python transforms** + "Test field mappings against live data before applying". — `competitor claim`.
- **B2B mode** (companies vs individuals; VAT/VIES validation with 3× retry); **Markets & Catalogs**; **multi-company inventory**; **BoM-based stock**; **multi-location fulfillment**; fraud-score threshold. — mixed `competitor claim` + `visible demonstrated workflow` (release notes).
- **Reliability/correctness**: automatic retry of safe operations after network/server errors (v1.13.0); **two CRITICAL "orders silently skipped" fixes** (v2.1.6 paging/sorting; v2.1.2 timezone) — demonstrates prior defects now patched and transparent. Apps Store reviews praise logging + restartable failed jobs. — `visible demonstrated workflow`.

### Important quotes or paraphrases
- "Odoo Shopify connector PRO" / "Created by VentorTech, an Official Odoo partner" / "€499" — ventor.tech/solutions
- "OAuth authentication — no manual API tokens" / "Real-time import via webhooks — new orders arrive within seconds" / "Background job queue — sync runs without blocking Odoo" / "Failed steps are clearly shown with details — easy to fix and retry" / "Webhook security: HMAC-SHA256 signature check" / "Built on Shopify's modern GraphQL API" — apps.odoo.com/.../integration_shopify
- "the connector will try to find existing contacts using all available information (email, name, phone…) before creating a new Odoo contact" / "connect as many Shopify stores as you want with a single Odoo instance" / "only 3 steps to start using the connector" — ecosystem.ventor.tech

### Update/release/patch notes captured (most transparent of the set — dated)
- **2.1.6 (2026-06-23):** custom product metafields in field definitions; **CRITICAL** silent-skip paging fix; idempotency extended to inventory activation; B2B duplicate-contact prevention; payment-currency conversion.
- **2.1.4 (2026-05-27):** Shopify API **2026-04** compliance; idempotency directives (refunds/inventory); VIES retry 3×; fixed 250-variant import cap; Sales Channels mapping.
- **2.1.2 (2026-03-20):** **CRITICAL** timezone date-filter fix (orders silently missed); advance payments; MO real-time inventory.
- **2.0.0 (2026-01-23):** **REST→GraphQL migration** (backward-incompatible); Markets & Catalogs; new OAuth/Dev-Dashboard; field-mapping engine; log retention.
- **1.13.0 (2025-10-27):** unified Import Wizard; Failed Job Notifications; expanded automatic retry. — all `on-page fact` / `visible demonstrated workflow` (dated).

### Open questions from this source
- Marketing-page staleness ("v13 and higher") vs Apps Store (13–19). EUR/USD pricing-model reconciliation. **No named rate-limit/backoff** mechanism (closest: "avoid unnecessary API requests"). **POS, gift cards, payout reconciliation, RMA/returns-as-distinct-from-refunds** not found. Connector-specific Odoo permission/record-rule model not detailed (only credential masking + HMAC). Exact OAuth wizard screen labels defer to video tutorials. Confluence (R4) pairing needed for field-level config depth.

---

## R8 — Odoo Apps: sh_shopify_connector (19.0)

### Access status
- **URL:** https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector
- **Date accessed:** 2026-06-30
- **Access status:** **Accessible** (HTTP 200; full listing incl. **~125 sequential screenshot/figure blocks with captions** and verbatim step text). The Softhealer flagship product URL returned **404**; the Base-module store page was accessible.
- **Pages/sections reached:** Full marketplace listing (price/license/author/deps/LOC, extensive feature list, ~29 distinct screenshot groups, step-by-step instructions) + Softhealer Base store page.
- **Pages/sections blocked:** `softhealer.com/shop/product/shopify-odoo-connector` (HTTP 404).
- **Notes on authentication/gating:** **No star rating, review count, or download count shown**; **no dated changelog** on the listing.

### Raw source observations
- **Price $168.81**, **License OPL-1**, author **Softhealer Technologies**, technical name **`sh_shopify_connector`**, **Odoo 12.0–19.0**, **18,951 LOC**; depends on CRM, Contacts, Inventory, Invoicing, Sales, eCommerce, Discuss, Calendar, Website + community **Base Integration (`sh_integration_base`)** ($9.11 separately). — `on-page fact`.
- **Connection**: Shopify custom app (Settings › Apps › Develop apps) → credentials → Odoo Authenticate → instance status **Done** → Sync Logs confirm token; gated behind **"Shopify Configuration Manager" access right**. — `visible demonstrated workflow`.
- **Queue Dashboard Framework**: separate Contact/Product/Order/Checkout/Recommendation queues with **draft/completed/failed counts**, "Process Queues Manually"; **"Daily Queue Activity Tracking" chart** (day-wise draft/failed/completed); **Sync Logs / Export Log history** audit tables. — `visible demonstrated workflow`.
- **Payment Gateway Workflow Matrix** routes order processing per gateway; **Auto Sale Workflow** (auto-create invoice / validate delivery / register payment / force transfer). — `visible demonstrated workflow`.
- **Refunds/returns**: import → credit note; full/partial/restocking/multi-currency; export refund back to Shopify. — `visible demonstrated workflow`.
- **Fulfillment**: validate Odoo delivery → queue stage "done" with **fulfillment ID** → Shopify status updated. **"Needs Shopify Re-Export"** flag (recovery for updated/cancelled orders, auto-cleared after sync). — `visible demonstrated workflow`.
- **Breadth differentiators**: **gift cards** (import/export/disable-in-Shopify, masked code/balance/expiry), **abandoned checkouts → CRM leads** (recovery routing), **product recommendations** (alternative/accessory, GraphQL queue + batch), **Buy with Prime**, **metafields** (directional, per-entity, single + bulk), **publish/unpublish via sales channels**, **exclude-from-sync** toggle, **date-range filters**, **granular access-rights groups**. — `visible demonstrated workflow`.
- **Webhooks** created Shopify-side (Settings › Notifications › Webhooks) for products/contacts/orders/fulfillment; "Real time data update". — `visible demonstrated workflow` (config) + `competitor claim` ("real-time").
- **Multi-store** "within a single Odoo database" and **multi-location** confirmed on page; **multi-company NOT found** on re-fetch (verification-downgraded). — `competitor claim` / `not-found`.

### Important quotes or paraphrases
- "Real Time Inventory Sync" / "Webhook Automation (Real time data update)" / "GraphQL API Integration for efficient data sync" — listing
- "Verify the instance status changes to Done after successful Shopify authentication." / "The Order Queue dashboard displays draft, completed, and failed order synchronization counts." / "Stage moved to done with fulfillment ID." — listing
- "Import and export Shopify gift cards directly" / "Import Buy With Prime orders" / "Lines of code: 18951" — listing

### Update/release/patch notes captured
- **No dated release-notes/changelog/"Technical updates" block** on the listing; version support shown only as availability badges 12.0–19.0. — `on-page fact` (a transparency gap vs R6/R7's dated changelogs).

### Open questions from this source
- **No ratings/reviews/downloads** shown → adoption/satisfaction unquantifiable here (Base page "(0 review)"). No dated changelog. Idempotency/dedup keys, **rate-limit handling**, webhook reconciliation detail (HMAC/ordering/replay) not documented. **Markets, POS, B2B, payout reconciliation** not mentioned. Multi-company unverified. Flagship vendor product page 404 (couldn't cross-check). The "real-time" framing is marketing — core sync is **queue/cron + optional webhook**.

---

## Cross-source observations (factual, not conclusions)

- **R5 = R6's setup guide.** The blocked Google Doc (R5) is the `ecommerce_shopify` (R6) "Get Started" target (`odoo.com/r/ecommerce-shopify` → that doc). Still blocked; owner access/export needed.
- **Teqstars docs are still 403-blocked** (whole host), but the **Teqstars Odoo Apps listing is accessible** — net-new pricing ($326.20) and rich vendor claims vs Sprint B (which had only the 403 + snippets).
- **Pricing facts (2026-06-30, on-page):** Webkul $170 · Teqstars $326.20 · ecommerce_shopify $195.56 · sh_shopify_connector $168.81 · VentorTech €499 / $569.16. Emipro price not in its docs.
- **A competitor doc carries a stale Shopify figure:** Emipro's webhook page states "19 retries over 48h" — the **outdated** number vs the current Tier-1 "8 retries / 4h" (DP-001 pattern). Recorded as a competitor-accuracy gap, not adopted as fact.
- **All capability statements remain competitor claims** unless a documented step-by-step flow/screenshot demonstrates them; on-page price/license/version/author/LOC/review-count are on-page facts as of 2026-06-30. None is promoted to a Tier-1 technical fact.
