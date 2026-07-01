# Competitor Screenshot / Visual Inventory (Research Sprint C)

> **Purpose.** Track and **analyse** every screenshot/visual/workflow image
> reviewed across the competitor sources — what each shows about configuration,
> workflow, layout, labels, status indicators, logs, buttons, and errors — so
> the UX benchmark and deep dives rest on visual evidence, not "screenshots
> exist". Companion to
> [`competitor-source-notes.md`](./competitor-source-notes.md) and
> [`screenshots/`](./screenshots/).
>
> **Access date for all visuals:** **2026-06-30**, **except the Teqstars (R2)
> section, rebaselined 2026-07-01** (its docs became accessible — see the
> Sprint C2 note in that section). **No auth wall was bypassed.**
>
> **On saved binary files — decision and rationale.** Pages were read through the
> proxy fetcher, which returns **page→markdown / alt-text, not pixels**. For the
> two marketplace listings and the vendor marketing pages, screenshots are
> embedded as captioned images whose **captions and visible field labels are
> reliable but whose pixel layout was not directly inspected**. Saving dozens of
> third-party binary images would bloat the repo for little analytic gain over
> the captions, and one source (the Google Doc) remains unreachable. *(The
> Teqstars docs, unreachable in Sprint C, became accessible in Sprint C2 — their
> ~98 real doc screenshots are now inventoried below by page and alt text, still
> without saving binaries.)* Per the sprint rule ("if screenshot binary files are too heavy or
> impractical, do not force it"), **no binary image files were saved**
> (`Actual file saved: no` throughout); the **analysis below is the deliverable**.
> Emipro is the exception worth noting: its screenshots are real, addressable
> `.png` URLs (recorded per entry) and could be captured later if ChatGPT wants
> binaries. Allowed extensions if ever saved: `.png .jpg .jpeg .webp`.
>
> **Claim-class key:** `visible demonstrated workflow` = the screenshot/flow
> demonstrates the behaviour; `competitor claim` = a vendor caption/marketing
> graphic, not proven; `on-page fact` = listing metadata.

---

## Webkul (R1) — Odoo Multichannel Shopify Connector

> Source: https://webkul.com/blog/odoo-multichannel-shopify-connector/ (all
> visuals). 21 inline guide screenshots (S1–S21). Saved files: **no** (markdown
> extraction). Below: the UX-bearing groups; the full S1–S21 list is in the
> source notes / deep dive.

### WK-SETUP (S1–S7) — Shopify app creation → Odoo connection → Test Connection
- Competitor/source: Webkul R1 · Source URL: as above · Date: 2026-06-30 · Actual file saved: no
- Page/section: Setup walkthrough (Shopify side then Odoo side)
- What is visible: Shopify "Create an app" screen; Redirect URL field (`{ODOO-URL}/shopify_odoo_bridge/redirect`); API scopes ("Give the access"); Client ID + Secret ID; Odoo multichannel dashboard "Connect" button; channel credential form (URL/Client ID/Client Secret); **"Test Connection"** button.
- Visible fields: Redirect URL, Client ID, Secret ID, Store URL · Visible buttons: Connect, Test Connection · Visible tabs/menus: multi-channel app
- Workflow step: First-time store connection / credential exchange
- UX observations: Linear, screenshot-per-step; an explicit **Test Connection** validation step before configuration — a good guardrail. Credential entry is manual copy/paste (custom-app OAuth), not a one-click OAuth redirect.
- Reliability/logging/error-handling observations: A validation step exists; the exact success/failure message is **not** shown on the page.
- What we can learn: Provide an explicit, early connection test with a clear pass/fail signal.
- What we should avoid: Manual multi-field credential copy/paste with no inline validation of each field.
- Claim class: visible demonstrated workflow · Uncertainties: exact Test Connection result UI not shown.

### WK-CONFIG (S8–S10) — Basic / Sales / Product setting tabs
- Actual file saved: no · Page/section: channel configuration tabs
- What is visible: **Basic Configuration** (Auto-evaluate, Company, API Record Limit, Channel timezone, Advanced); **Sales Setting** (Payment Term, Sales Team, Salesperson, UTM Campaign/Medium/Source, Tax Type, E-Commerce Order Reference Sync, Discount Product, Shipping Product, Real-time Sales Order Status Sync); **Product Setting** (Category, Price list, Language, Channel Category, SKU Pattern, Product avoid duplicity, Auto Stock, Stock Action, Warehouse, Location).
- Visible tabs: Basic Configuration, Sales Setting, Product Setting · Workflow step: channel configuration
- UX observations: Configuration is **tab-segmented by domain** (basic/sales/product) — reasonable IA; but many fields per tab (sales tab is dense). "Auto-evaluate", "API Record Limit", "Stock Action" labels are jargon needing tooltips.
- What we can learn: Tab-segment configuration by domain; expose a batch-size ("API Record Limit") and a stock-quantity-type choice.
- What we should avoid: Dense single-screen config with unexplained jargon and no inline help.
- Claim class: visible demonstrated workflow · Uncertainties: tooltip/help presence not visible in extraction.

### WK-CRON (S11–S13) — Channel cron / import cron / global config
- Actual file saved: no · What is visible: cron config (Model, Scheduler User, Execute Every, Active, Next Execution Date) and global "Avoid Duplicity (Default Code)".
- Workflow step: scheduled import setup · UX: exposes raw Odoo `ir.cron`-style fields (Model, Scheduler User, Next Execution Date) to the user — powerful but **leaky/technical**.
- What we can learn: let users schedule per-object syncs. What to avoid: exposing raw cron internals (Model/Scheduler User) instead of a friendly "every N minutes" control.
- Claim class: visible demonstrated workflow.

### WK-FEEDS (S14) — Data Feeds list (staging + error feeds)
- Actual file saved: no · What is visible: incoming Shopify data staged as "Feeds" awaiting evaluation; problem records flagged as **error feeds**.
- Workflow step: import staging / error triage · UX: a **staging-before-commit** pattern with an error queue users can fix and re-evaluate — strong concept.
- Reliability: error feeds are the recovery surface; the re-evaluate action itself is described in text, not shown end-to-end.
- What we can learn: stage inbound data and expose a fixable error queue. What to avoid: leaving the retry/re-evaluate path undocumented/unshown.
- Claim class: visible demonstrated workflow (staging) + competitor claim (auto-evaluate behaviour).

### WK-OPS (S15–S21) — Mapping list, import/export wizards (product/order/category)
- Actual file saved: no · What is visible: product mapping list; data import dashboard; product/order/category **import wizards with filter options** (all / ID / Date updated after / Date created after); category & product **export** operations.
- UX: consistent **filtered import wizard** per object; mapping list shows synced records.
- What we can learn: a uniform filtered import wizard and visible mapping records. Claim class: visible demonstrated workflow.

---

## Teqstars (R2) — real documentation screenshots (Sprint C2 rebaseline, 2026-07-01)

> **Sprint C2 correction.** In Sprint C the `docs.teqstars.com` screenshots were
> **403-blocked** and only the 17 Apps-listing **captions** could be recorded (as
> vendor claims). On **2026-07-01** the docs became accessible (HTTP 200 with a
> browser UA; no auth bypassed). The 31 Odoo 19.0 Shopify doc pages carry
> **~98 embedded content screenshots** (`.jpg`/`.png` under
> `docs.teqstars.com/.../_images/`) inside **step-by-step procedures**. Per the
> sprint rule, **no binary image files were saved** (`Actual file saved: no`
> throughout) — the analysis below is the deliverable; image counts and alt-text
> are recorded per page. The Sprint C caption block is retained as history at the
> end of this section.

### TQ-SETUP-INSTANCE — Create Instance configuration (15 screenshots) ✅
- Source: `.../setup/create_instance.html` · Saved: no · Date: 2026-07-01
- Images (alt/src): Last Processed On, Configurations, Product Configurations, Stock Configurations, Orders Configurations, Payout Configurations, Customer Configurations, Metafield Configurations, Workflow Configurations, Webhook Configurations, Automatic Jobs Configurations, Notification & Alerts (×2 incl. import-order issue/success), Instance Confirmation (`shopify_configuration.jpg`, `shopify_products.jpg`, `shopify_stock.jpg`, `shopify_order.jpg`, `shopify_webhook.jpg`, `shopify_automatic_jobs.jpg`, `shopify_notification_and_alerts.jpg`, …).
- Workflow step: full instance configuration (log level, Queue Batch Limit, product/stock/order/payout/customer/metafield/workflow/webhook/automatic-jobs/notification config).
- UX observations: a **single long configuration form segmented by tab** (Product/Stock/Orders/Payout/Customer/Metafield/Workflow/Webhook/Automatic Jobs), several fields dev-mode-gated — powerful but toggle-dense (10+ order-config toggles). "Sync Listings Based On" (Barcode/SKU/both) and "Create Odoo Products?" are the key dedup controls; Real-Time Price/Inventory Sync toggles are visible.
- Reliability/logging: Activity-on-failure (Responsible + due date) and Smart Notification config are shown; Queues‣Logs is the review surface; log level ALL/SUCCESS/ERROR.
- Screenshot confirms **workflow** (config procedure), not just UI presence.
- What we can learn: expose match-key + create-guard + real-time toggles; surface an activity-on-failure. What to avoid: a very long, toggle-dense single config form without progressive disclosure.
- Claim class: **visible demonstrated workflow** · Uncertainties: pixels not inspected (alt-text + step text reliable).

### TQ-CREDENTIALS — OAuth custom-app token flow + Test Connection (7 screenshots) ✅
- Source: `.../setup/generate_credentials.html` · Saved: no
- Images: Create Custom App, Admin API Scopes Selection, Redirect URL (copy/paste), Client Secret (copy/paste), Generate Access Token (`shopify_create_shopify_app.png`, `shopify_admin_api_scopes.png`, `shopify_copy_redirect_url.png`, `shopify_generate_access_token.png`, …).
- Workflow step: 6-step credential generation (create app → scopes → redirect URL → client id/secret → generate token → **Test Connection**).
- UX observations: linear, screenshot-per-step OAuth flow with an explicit **Test Connection** validation step; full Admin API scope string shown with a warning to enable all scopes.
- Screenshot confirms **workflow** (step-by-step auth), not just UI presence.
- What we can learn: screenshot-per-step OAuth + an explicit connection test + a visible scope list with a "enable all" warning. Claim class: **visible demonstrated workflow**.

### TQ-PRODUCT — import (2) / export (5) / update (12) / matching config ✅
- Sources: `.../product_management/product_import.html`, `product_export.html`, `product_update.html` · Saved: no
- Images: Product Import Screen, Sync to Odoo Button; Product Export Screen, View listings, Export Listing Button/Popup; Product Update Screen, Update listings Button/Popup, **Sync to Shopify** Button, Update to Marketplace Button, Update Listing Item Popup, **Manage Sales Channels** Button, Listing **Allowed Sync** / **Not Allowed Sync** status badges.
- Workflow step: product import (filters, auto-create-if-missing), export (Add-to-Listings → Export Listings; sales-channels-optional = draft-safe), update (four methods; Set Price/Set Quantity; Publish/Unpublish), and **Skip-Sync** (green Allowed / red Not-Allowed badge excludes a listing from all sync ops).
- UX observations: consistent operation-popup + listing-form patterns; a green/red **sync-state badge** on the listing form; a Manage-Sales-Channels publish/unpublish dialog.
- Screenshot confirms **workflow** (import/export/update procedures + the sync-state badge), not just UI presence.
- What we can learn: a per-listing Allowed/Not-Allowed-Sync toggle with a colour badge is a clean exclude-from-sync/duplicate-safety control; sales-channels-optional gives draft-safe export. Claim class: **visible demonstrated workflow**.

### TQ-ORDERS — order status/tracking (10) / refund (2) / cancel (2) / returns (6) / payout (3) ✅
- Sources: `.../order_management/update_order_status.html`, `order_refund.html`, `cancel_order.html`, `order_return.html`, `payout_report.html` · Saved: no
- Images: Update Order Status (×10 incl. **Ready For Pick Up**, **Mark As Picked Up** success, before/after pickup); Refund in Shopify Button + Refund screen; Cancel In Shopify Button + Cancel Order screen; Import Returns Operation, Shopify Return form, Process-Return wizard, **Force Restock** button, Create-Return-in-Shopify Button + wizard; Payout Configuration, Payout Import Screen, Payout Record.
- Workflow step: fulfillment/tracking write-back (normal + **click & collect** pickup lifecycle); refund from credit note (amount-match guard); cancel (reason/notify/restock/refund); returns (import + create-from-Odoo + Force Restock + credit-note link); payout import + reconcile (Shopify-Payments-only).
- UX observations: dedicated buttons with propagate-to-Shopify options (Notify Customer / Restock / Refund); a two-path pickup flow (Ready-for-Pickup → Picked-Up); a Force-Restock button with an on-hand-divergence warning; payout list/form with Post/Auto-Reconcile/Reconcile actions and per-line warnings.
- Screenshot confirms **workflow** (order lifecycle write-backs), not just UI presence.
- What we can learn: pickup/click-and-collect as first-class order status; explicit propagate-to-marketplace checkboxes; a divergence-warning on force-restock; reason-coded payout-line warnings. Claim class: **visible demonstrated workflow**.

### TQ-COLLECTIONS/CATALOGS/METAFIELDS — collections (2+3+5) / catalogs (2+5) / metafields (1) ✅
- Sources: `.../product_management/import_collection.html`, `export_collection.html`, `update_collection.html`, `import_catalog.html`, `update_catalog.html`, `setup/shopify_metafields.html` · Saved: no
- Images: Collection Import/Smart-Manual, Collection Export/Update screens + **Update collection job**, Manage Sales Channels (collection); Catalog Import + Sync-to-Odoo, Update Catalog + list/form Sync-to-Shopify + **Add Listings to Catalog** + **Edit Quantity Rules and Volume Pricing**; Metafield Mapping List.
- Workflow step: collections (smart/manual import, export/update with publish control, background job every 15 min), catalogs (Market/Company-Location/App pricing incl. quantity rules + volume pricing), metafield mapping (Ready/Missing/Not-Found/Inactive badges).
- Screenshot confirms **workflow** (Markets/B2B pricing + metafield mapping), not just UI presence.
- What we can learn: Markets/Catalogs price tiers + quantity/volume rules in-Odoo; a status-badge-driven metafield mapping list. Claim class: **visible demonstrated workflow**.

### TQ-CUSTOMER/PRICE/INVENTORY — customer import (1) / price (1+3) / inventory (3+3) ✅
- Sources: `.../customer_management/customer_import.html`, `import_price.html`, `export_price.html`, `import_inventory.html`, `export_inventory.html`, `setup/shopify_location.html` · Saved: no
- Images: Customer Import Screen; Price Import Screen; Export Price screen + **Price Automatic Export** schedule; Import/Export Inventory screens + schedule actions; Locations Setting.
- Workflow step: customer import (multi-field dedup; **import-only** — no export screen exists); price/inventory import+export (manual + Automatic-Jobs + optional real-time); location mapping (multi-location combine + third-party exclusion).
- Screenshot confirms **workflow** (import/export + scheduling + location mapping), not just UI presence.
- What we can learn: per-operation manual + scheduled + real-time options; location mapping with a third-party-exclusion warning. Note the **absence** of any customer-export screen (import-only). Claim class: **visible demonstrated workflow** (import/export shown) / **not found** (customer export).

### TQ (Sprint C historical) — Odoo Apps listing captions (docs were 403-blocked)
> Source: https://apps.odoo.com/apps/modules/19.0/shopify (17 listing screenshot
> **captions**, 2026-06-30). Retained as audit trail; superseded by the
> now-accessible docs screenshots above. Class then: **competitor claim**
> throughout (caption-only; docs screenshots were 403-blocked).
- Captions implied: Credentials Setup; Product Sync Config (SKU/Barcode matching); Order Config (fraud/tax); Workflow Config (gateway→journal rows); Webhook Config (Name/Event/Active); Import/Export wizards; **Queue Manager** ("one bad record won't block 999"); Payout (Enterprise auto-reconcile); Refund/Cancel dialogs; Fulfillment ("Update in Marketplace"); **two dashboards** (operational + Analytics). **The "two dashboards" and "Queue Manager retry" captions are NOT substantiated by the now-accessible docs** — the docs show an Operations launcher + Queues/Logs but no metrics/chart dashboard and no per-record inline-retry control (only queue re-processing + manual re-run). Claim class then: competitor claim · Uncertainties then: high (captions only, docs 403).

---

## Emipro (R3) — real documentation screenshots (addressable .png URLs)

> Source: docs.emiprotechnologies.com/shopify-odoo-connector/v19/... — ~29
> screenshots with **real image URLs and descriptive alt text**. Saved files:
> **no** (could be captured later if binaries are wanted). The most
> evidence-rich, demonstrative visual set of the survey.

### EM-SETUP — Path A token wizard (3 screens)
- URLs: `.../setup-shopify-odoo-connector/images/token_custom_appv2_images/odoo_wizard_urls.png`, `shopify_version_urls.png`, `shopify_scopes.png` · Saved: no
- What is visible: Odoo "Set Shopify Authorization Details" wizard (App URL, Callback/Redirect URL); Shopify app Version screen (App URL, Redirection URL(s)); Shopify Access Scopes field with the full required scope string.
- Workflow step: credential/token generation (Path A) · Fields: App URL, Callback/Redirect URL, Access Scopes
- UX observations: doc explicitly warns "Any mismatch — including a trailing slash — will cause the authorization to fail" — a precise, honest gotcha. Scope string is long and pasted manually.
- Reliability: surfaces a real failure mode (URL/trailing-slash mismatch) up front.
- What we can learn: warn about exact-match URL pitfalls; show the required scopes explicitly. What to avoid: a long manual scope paste with a silent failure if wrong.
- Claim class: visible demonstrated workflow.

### EM-PRODUCT — product window, images tab, import wizard, CSV map (≈6 screens)
- URLs: `.../images/7-1.png`, `7-2.png`, `.../shopify-product-management/images/6-3-1-1.png`, `6-3-15.png` · Saved: no
- What is visible: Shopify Products window (Publish/Export status, Variants, Create/Update/Publish dates, "Sale out of stock products?" toggle, **"Shopify Unpublish"** button); Images tab (synced images, removal only here); Import Products wizard (Create vs Update Date, From/To range, "Do not update existing products", "Import Draft products"); Map Products window + the exported CSV columns (product_template_id, product_id, names, default_code, sku, description, instance_id).
- Workflow step: product management/import/mapping · UX: rich per-product status surface; **CSV/XLSX mapping fallback** for non-SKU matches; explicit incremental controls (date type + "do not update existing").
- What we can learn: surface publish/export status + variants + dates on the product; offer CSV mapping as a fallback to SKU matching; default the import "From Date" to last execution.
- Claim class: visible demonstrated workflow.

### EM-QUEUE — Data Queues (4 screens: list, manual process, log lines, processed ribbon)
- URLs: `.../shopify-odoo-operations/images/6-2-1.png … 6-2-4.png` · Saved: no
- What is visible: queue list with **Draft/Failed/Cancelled/Done** states; a queue with "Process Queue Manually" and "Force Done"; **Log Lines tab** with per-record mismatch reasons; a "processed" ribbon when complete.
- Workflow step: batch job processing & error inspection · Fields: queue state; buttons: Process Queue Manually, Force Done
- UX observations: a genuine **operational queue UI** — at-a-glance state counts, manual processing, per-line logs, completion ribbon. "Force Done" is irreversible (a footgun the docs flag).
- Reliability/logging: **best demonstrated job/queue + per-line error log surface** of the survey; failed lines isolated from done lines (partial-failure friendly).
- What we can learn: state-coloured queues + per-line log lines + a clear completion signal. What to avoid: an irreversible "Force Done" without strong confirmation.
- Claim class: visible demonstrated workflow.

### EM-SCHEDULER — Automatic Scheduler + Last Operation Details (2 screens)
- URLs: `.../shopify-odoo-operations/images/6-1-1.png`, `6-1-2.png` · Saved: no
- What is visible: scheduler screen listing cron-able processes (Import Orders/Shipped/Cancel/Update Status/Payout/Bank Statement/Export Stock) with Time interval; a **"Last Operation Details"** panel.
- UX: per-process scheduling + a last-run audit panel; doc advises staggering intervals to avoid resource contention.
- What we can learn: per-process schedules + a "last run" panel. Claim class: visible demonstrated workflow.

### EM-ORDER/RETURN/FULFILLMENT — import wizards, multi-payments, Put-in-Pack, return config (≈8 screens)
- URLs: `.../shopify-orders-management/images/8-1-1.png, 8-2-2.png, 8-6-2.png, 8-7-2.png, 1_return_refund_imag.png`; config `.../shopify-configurations-in-odoo/images/4-9-1.png, 4-2-1.png, 4-19-1.png` · Saved: no
- What is visible: import wizards (instance + start/end date); scheduler requiring **Time + Execution date/time + User**; **Multi Payments** section (two payment lines for gift-card+stripe); **Put in Pack** multi-package fulfillment; return/refund config toggles (Use GraphQL API, Auto Create Refund); Order Configuration screen (Import Order Status, sequence/prefix, Sales Team, Analytic Account, customer-visible currency, Import Customer as Company, multi-warehouse delivery, Buy with Prime); **Webhook Order Configuration** (Auto-Ship, Forceful Transfer Validation, Auto-Refund, Return, register payment for credit note, validate return, update customers/quantities, add new products).
- UX: deep, checkbox-rich configuration; multi-payment and multi-package are concrete, well-modelled edge cases.
- What we can learn: model multi-payment orders as multiple payment lines; support multi-package fulfillment; expose webhook-behaviour toggles. What to avoid: overwhelming a single Order Configuration screen with 10+ toggles and no grouping/help.
- Claim class: visible demonstrated workflow.

### EM-MARKETS/METAFIELDS/CHANNEL/PAYOUT/LOG (≈8 screens)
- URLs: `.../images/shopify_markets_images/1_markets-configuration.png, 3_sync-markets-success.png, 6_financial-status-market.png`; `.../images/metafield_images/2_perform_operation.png`; `.../images/shopify_channel_images/exclude-orders-queue-log.png`; `.../images/11-2.png` (payout); `.../images/10-2.png` (log book) · Saved: no
- What is visible: Markets enablement + "3 market(s) synced from Shopify" success toast + per-market **Financial Status Configurations** tab; metafield Perform-Operation (Fetch Scope + Metafield Keys); **excluded-channel queue Log Lines** (Shopify order ID + channel handle + app ID); imported Payout Report (Generate Bank Statement); **Mismatch Log / Log Book** listing failures with reasons.
- Reliability/logging: the **Log Book and excluded-channel queue log** give explicit, reason-coded failure visibility — strong observability.
- What we can learn: count-confirming success toasts; reason-coded failure logs; per-market config. Claim class: visible demonstrated workflow.

---

## VentorTech (R4 Confluence) — connector UI screenshots in how-to articles

> Source: ventortech.atlassian.net/wiki/spaces/pd/... (9 article screenshots,
> anonymous/partial). Saved files: no.

### VT-WEBHOOKS — Webhooks tab with traffic-light status
- URL: `.../pages/521928707/` · Saved: no · Date: 2026-06-30
- What is visible: Webhooks tab; **"Create Webhooks"** button; webhook rows with **green/yellow/red status indicators**; dev-mode "Delete Webhooks".
- Fields: webhook status (green/yellow/red) · Buttons: Create Webhooks, Delete Webhooks
- UX observations: **best status-indicator pattern of the survey** — a traffic-light webhook health view where **yellow specifically means "callback URL mismatch — check `web.base.url`"**, turning an opaque failure into a self-serve fix.
- Reliability: at-a-glance webhook health + a named, actionable diagnostic for the most common misconfig.
- What we can learn: traffic-light health + diagnostic-specific colours with a fix hint. What to avoid: binary on/off webhook status with no cause.
- Claim class: visible demonstrated workflow.

### VT-INVENTORY — Inventory tab "External Location" mapping grid
- URL: `.../pages/521732182/` · Saved: no
- What is visible: a grid pairing Odoo warehouse locations with an **"External Location"** column (Shopify location); empty → Default Shopify Location.
- UX: explicit, low-error multi-location mapping with a safe fallback. What we can learn: per-location mapping with a default fallback. Claim class: visible demonstrated workflow.

### VT-CATALOGS — Markets & Catalogs with Preview/Report dry-run
- URL: `.../pages/2338914308/` · Saved: no
- What is visible: "Import Markets and Catalogs"; mapping lines (Shopify Catalog / Odoo Pricelist / Compare At Pricelist); **Preview**, **Report**, **Send Prices** buttons; "Pricelist Prices Calculation & Export" toggle.
- UX observations: a **dry-run (Preview/Report) before export** — "detect issues before sending data" — a standout validation pattern.
- What we can learn: always offer a dry-run/preview before pushing data. Claim class: visible demonstrated workflow.

### VT-FULFILLMENT — e-Commerce Integration fulfillment table
- URL: `.../pages/777388068/` · Saved: no
- What is visible: fulfillment table (products/qty/carriers/tracking); "Fetch and Apply from external"; per-line **Apply**; "Apply External Fulfillments" / "Force Full Fulfillment in Shopify" checkboxes; a per-line **"internal info"** diagnostic for failed applies.
- Reliability: per-line internal-info for partial-failure diagnosis. Claim class: visible demonstrated workflow.

### VT-METAFIELDS / VT-RISK / VT-CANCEL
- URLs: `.../pages/664469537/`, `.../pages/2340126732/`, `.../pages/776470531/` · Saved: no
- What is visible: "Update Metafields" fetch-then-map tables; order-risk fields (**Risk level, Sentiment, Action Recommended**); cancellation dialog (reason/staff-note/restock/refund/notify + "Cancel e-Commerce Fulfillments"), with an explicit "the Odoo order…cannot be undone" warning.
- UX: consistent "Update X → map" pattern; risk surfaced on the order; native Shopify cancel options inside Odoo with an irreversibility warning.
- What we can learn: consistent fetch-then-map UIs; surface order risk; warn on irreversible actions. Claim class: visible demonstrated workflow.

---

## VentorTech (R7 marketing) — flow diagrams (alt-text only)

> Source: ventor.tech/solutions/odoo-shopify-connector/. 4 marketing flow figures
> parsed from **alt text only** (no pixels). Saved files: no. Class: competitor
> claim (marketing graphics).

### R7-FLOWS — Initial Import / Product Export / Order Import / Tracking
- Saved: no · What is visible (alt text): "Shopify Odoo Initial Import" (master data Shopify→Odoo); "odoo shopify product export" (Odoo→Shopify product/qty/price/images); "Shopify to Odoo orders"; "tracking number from Odoo to Shopify".
- UX: marketing direction diagrams, not product UI. What we can learn: communicate sync **direction** per data type clearly. Claim class: competitor claim · Uncertainties: high (alt text only; real UI screenshots not on this page).

---

## Odoo Apps listings — ecommerce_shopify (R6) & sh_shopify_connector (R8)

### R6-NOSHOTS — ecommerce_shopify has NO interface screenshots
- URL: https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify · Saved: no
- What is visible: only the 84×84 app icon + 6 author cross-promo banners; **no UI/workflow screenshots and no video** anywhere in the listing body.
- UX observations: **every capability is text-only** — no visual proof of any described workflow; weakest visual evidence of the survey.
- What we can learn: buyers get no visual proof of UX here. What to avoid (as a vendor): a feature listing with zero workflow screenshots undermines trust.
- Claim class: on-page fact (absence of screenshots) · Uncertainties: the actual UI is entirely unseen.

### R8-WALKTHROUGH (V01–V29) — sh_shopify_connector listing walkthrough (~29 groups)
- URL: https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector · Saved: no
- What is visible (caption groups, representative): access-rights gating (Shopify Configuration Manager); Shopify custom-app credential flow → Odoo Authenticate → status **Done** → Sync Logs; product/contact import config + **Queue dashboards** (draft/completed/failed counts) + "Manually Import"/"Open Record"; product export with **Shopify ID write-back**; **Payment Gateway Workflow Matrix**; order queue dashboard; **Auto Sales Workflow** (auto-invoice/validate/register/force); webhook setup (Settings›Notifications›Webhooks); refund flow (credit note ↔ Shopify, "Send to Shopify"); fulfillment (Validate delivery → **fulfillment ID**); **"Needs Shopify Re-Export"** recovery flag; **Shopify Integration Dashboard + "Daily Queue Activity Tracking" chart**; metafield directional mapping; **gift cards** (masked code/balance/expiry, Disable-in-Shopify); **abandoned checkouts → CRM leads**; **product recommendations** (GraphQL queue + Bulk Sync); **Buy with Prime**; publish/unpublish via sales channels; per-variant stock export.
- Workflow step: nearly end-to-end (setup → import/export → orders → fulfillment → refunds → monitoring → advanced)
- UX observations: a **dashboard-centric, queue-staged** model with explicit failure counts, an activity time-series chart, audit logs, and a re-export recovery flag; access-rights gate connector settings. The **breadth** (gift cards, abandoned-checkout→CRM, recommendations, Buy-with-Prime) is the widest of the survey.
- Reliability/logging: queue draft/failed/completed counts + daily activity chart + Sync/Export logs + re-export flag = strong **operational visibility** (but underlying durability/dedup not provable from captions).
- What we can learn: a monitoring dashboard with a daily activity chart and failure counts; a re-export recovery flag; access-rights gating; ID write-back linking.
- What we should avoid: "real-time" labelling for what is queue/cron + optional webhook; no dated changelog or ratings to back the breadth.
- Claim class: visible demonstrated workflow (captions describe concrete screens) · Uncertainties: pixel layout not inspected; "real-time" overstated; no ratings to corroborate.

---

## Inventory summary

| Source | Visuals reviewed | Real image URLs? | Binary saved | Strongest visual evidence |
| --- | --- | --- | --- | --- |
| Webkul (R1) | 21 (S1–S21) | markdown extraction | no | staging Feeds + filtered import wizards |
| Teqstars (R2) | **~98 real doc screenshots (2026-07-01)** | **yes (docs now accessible)** | no | setup/product/order **step-by-step** flows (create-instance ×15, product-update ×12, order-status ×10, returns ×6) |
| Emipro (R3) | ~29 (.png URLs) | **yes** | no | Data Queues + Log Book (real screens) |
| VentorTech (R4) | 9 article shots | partial | no | **traffic-light webhook health**; Preview/Report dry-run |
| VentorTech (R7) | 4 alt-text figures | no (alt only) | no | sync-direction flow diagrams |
| ecommerce_shopify (R6) | **0 UI shots** | n/a | no | — (none; text-only listing) |
| sh_shopify_connector (R8) | ~29 caption groups | no (captions) | no | dashboard + daily activity chart + queues |
| Google Doc (R5) | **0 (blocked)** | n/a | n/a | — (sign-in wall) |

**Net (updated Sprint C2):** the most demonstrative, verifiable UI evidence is now
**Emipro**, **VentorTech R4**, **and Teqstars** — Teqstars moved from
"unverifiable captions (docs blocked)" to **~98 real doc screenshots inside
step-by-step procedures** (create-instance config ×15, product-update ×12,
order-status/pickup ×10, returns ×6, OAuth credentials ×7). Emipro remains
strongest for **queue/log observability**; VentorTech R4 for **traffic-light
webhook health + Preview/Report dry-run**; Teqstars now covers the **widest
demonstrated breadth** (setup, product/price/inventory, orders/refunds/cancel/
returns/payouts, collections/catalogs, metafields). **ecommerce_shopify** still
has **no** UI screenshots; **Softhealer** still has the broadest *caption*
walkthrough but no rendered-image verification and no ratings/changelog. Two
prior Teqstars caption claims are **not** substantiated by the docs (a
metrics/chart dashboard, and a per-record inline-retry "Queue Manager").
