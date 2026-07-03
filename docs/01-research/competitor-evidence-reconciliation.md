# Competitor Evidence Reconciliation (Evidence & Blueprint Reconciliation Sprint)

> **Purpose.** A per-resource reconciliation of the competitor evidence
> **already captured in this repository** against the questions this sprint must
> answer before Part D (UI/UX Screen Design) begins. This file **reconciles and
> indexes existing evidence** — it does not re-fetch sources and does not draw
> MVP or architecture conclusions (the no-code / research-first gate,
> `CLAUDE.md` §4–§5, is in force). Its companions are the
> [`competitor-feature-screen-map.md`](./competitor-feature-screen-map.md) (the
> screen-pattern matrix) and the
> [`competitor-gap-analysis-against-blueprint.md`](./competitor-gap-analysis-against-blueprint.md)
> (the reconciliation against accepted decisions).
>
> **Evidence base (repo-first, per the sprint rule).** All observations below
> are taken from evidence **already saved in the repo**; no new external fetch
> was performed this sprint. Primary repo sources:
> - [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md)
>   (R1–R8 page-classified source notes)
> - [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md)
>   (visual/screenshot inventory)
> - [`../00-source-materials/source-access-notes.md`](../00-source-materials/source-access-notes.md)
>   (per-resource access validation)
> - [`./competitor-deep-dives.md`](./competitor-deep-dives.md),
>   [`./competitor-feature-matrix.md`](./competitor-feature-matrix.md),
>   [`./ux-ui-benchmark.md`](./ux-ui-benchmark.md)
>
> **Access dates (as recorded in those files):** all competitor evidence
> **2026-06-30**, **except Teqstars (R2), rebaselined 2026-07-01** (its docs
> became accessible on re-check). This sprint's reconciliation date is
> **2026-07-03**. **No authentication wall was bypassed** in the original
> captures, and none was attempted here.
>
> **Claim-class discipline (`CLAUDE.md` §7–§8) carried through.** Each
> observation keeps the class assigned in the source notes:
> `on-page fact` · `competitor claim` · `visible demonstrated workflow` ·
> `inference` · `blocked/unknown`. Where a competitor **documents a feature but
> no UI/screen is shown**, it is labelled **"feature/flow documented; UI not
> observed."** Where a screenshot exists, the screenshot inventory description is
> cited; where none exists, that is stated.

---

## Legend

- **Confidence** — reviewer confidence that the recorded observations reflect
  the product as documented: **High** (readable docs + real screenshots or dated
  release notes), **Medium** (readable listing/marketing, few or caption-only
  visuals), **Low** (thin/absent visuals or thin adoption signal),
  **Blocked** (source gated).
- **Evidence quality** — the strength of the underlying artifacts:
  demonstrated workflow > dated release notes > readable docs > marketing
  listing text > caption-only > blocked.
- **Screenshots available** — **yes** = real image assets or captioned image
  blocks exist in the source (pixels not necessarily inspected — see each
  entry); **no** = none in the accessed material.

---

## R1 — Webkul: Odoo Multichannel Shopify Connector

- **Source name:** Webkul — Odoo Multichannel Shopify Connector
- **Source type:** vendor blog/user-guide + store listing
- **URL / repo path:** https://webkul.com/blog/odoo-multichannel-shopify-connector/ ·
  store https://store.webkul.com/odoo-multichannel-shopify-connector.html ·
  repo: `../00-source-materials/competitor-source-notes.md` §R1;
  `../00-source-materials/competitor-screenshot-inventory.md` (Webkul)
- **Access date:** 2026-06-30 (Accessible; HTTP 200, no auth wall)
- **What was reviewed:** full blog user-guide (overview, key features, Shopify
  app setup, Odoo connection, Basic/Sales/Product settings, cron, Feeds,
  mappings, sync history) + store listing (price/version/license/deps/dates).
- **Features actually observed:** custom-app OAuth connect + **Test Connection**;
  category/product/order/customer import with filters (all / ID / date-updated /
  date-created); mandatory import order (categories » product » order); **Feeds**
  staging area with **error-feed** re-evaluation; duplicate prevention via
  Internal Reference (SKU) + Barcode + global "Avoid Duplicity" toggle;
  single-warehouse inventory with Stock Action (on-hand/forecasted) and optional
  real-time push; explicit **"Import of shipping method is not available."**
  (`on-page fact`, explicit absence).
- **Screens actually observed:** WK-SETUP (S1–S7 Shopify app → Odoo connect →
  Test Connection); WK-CONFIG (S8–S10 Basic/Sales/Product config tabs);
  WK-CRON (S11–S13, exposes raw `ir.cron`-style fields); WK-FEEDS (S14 staging +
  error feeds); WK-OPS (S15–S21 mapping list + filtered import/export wizards).
- **Flows actually observed:** first-time store connection; tab-segmented config;
  scheduled import setup; import staging/error-triage; per-object filtered import.
- **Screenshots available:** **yes** (21 inline guide screenshots S1–S21), but
  captured via markdown/alt extraction — **pixels not inspected**; no binaries
  saved.
- **Confidence:** Medium. **Evidence quality:** readable guide + captioned
  screenshots (workflow-level for setup/config/feeds).
- **Limitations / inaccessible areas:** version discrepancy (blog 1.0.0 vs store
  3.5.1) unresolved; variants/media/invoice/refunds/payouts/webhooks/multi-
  location/multi-store/permissions/reporting **not found** on accessed pages;
  customer **export** not found (import only); exact Test-Connection result UI
  not shown.
- **Evidence gaps for Part D:** config screens shown but tooltip/help presence
  not visible; cron UI is a **cautionary example** (raw internals exposed).

## R2 — Teqstars: Shopify Connector for Odoo (Odoo 19.0 docs + Apps listing)

- **Source name:** Teqstars — Shopify Connector for Odoo (GraphQL)
- **Source type:** vendor docs (19.0) + Odoo Apps listing
- **URL / repo path:** https://docs.teqstars.com/19.0/applications/shopify/ (31
  pages) · https://apps.odoo.com/apps/modules/19.0/shopify · repo:
  `competitor-source-notes.md` §R2 (Sprint C historical + **Sprint C2** current);
  `competitor-screenshot-inventory.md` (Teqstars, Sprint C2 rebaseline)
- **Access date:** Apps listing **2026-06-30**; **docs rebaselined 2026-07-01**
  (the Sprint C **HTTP 403** was a **bot/UA filter, not a login wall** — a
  browser-UA fetch returned HTTP 200; **no auth bypassed**). Sprint C Blocked
  record retained as audit trail.
- **What was reviewed:** 31 Odoo 19.0 doc pages (setup, product/customer/order
  management, collections/catalogs, metafields, payouts, FAQ, support policy)
  plus the Apps listing (price/license/version/reviews + vendor claims).
- **Features actually observed (demonstrated):** OAuth custom-app + **Test
  Connection**; instance config (log level, Queue Batch Limit 100, per-domain
  config); **"Sync Listings Based On"** match key (Barcode/SKU/both) + **"Create
  Odoo Products?"** create-guard; product import/export/update (draft-safe export
  via empty Sales Channels); **Listing / Listing-Item** model; product/order/
  customer/returns webhooks (background-thread fast-ack); price import/export
  (+ optional real-time); inventory import/export, multi-location mapping
  (combine locations; **third-party location excluded**); customer import
  (multi-field dedup; **customer export ⬜ not found**); orders (per gateway +
  financial status; **click & collect** pickup lifecycle); refunds/cancels/
  returns (amount-match guard, Force Restock); mark-as-paid + payout report
  (Shopify-Payments-only, per-line reason-coded warnings); metafields
  (directional); collections/catalogs (Markets/B2B pricing, quantity/volume
  rules); Queues‣Logs with **Activity-on-failure**.
- **Screens actually observed:** ~98 embedded doc screenshots inside step-by-step
  procedures — create-instance ×15, credentials/OAuth ×7, product update ×12,
  order status/pickup ×10, returns ×6, plus price/inventory/collections/catalogs/
  metafields (inventoried by page + alt-text in the screenshot file).
- **Flows actually observed:** end-to-end across setup → product/price/inventory
  → orders/refunds/cancel/returns/payouts → collections/catalogs → metafields.
- **Screenshots available:** **yes** (~98 real `.jpg`/`.png` doc assets; pixels
  not inspected; no binaries saved).
- **Confidence:** High for breadth (screenshot-backed step-by-step docs);
  **Medium/Low** for reliability internals. **Evidence quality:** widest
  demonstrated breadth of the set.
- **Limitations / inaccessible areas / downgrades:** **pHash image dedup 🟨**
  (comparison-table + `imagehash`/`PyWavelets` dependency only, no workflow);
  **idempotency ➖ implied** (adjacent guards only; the Sprint C indexed
  idempotency snippet is **UNVERIFIED** on the accessible docs — competitor
  claim, not demonstrated); **automatic-retry ⬜**, **cross-object reconciliation
  ⬜**, **rate-limit ⬜**, **HMAC/webhook-signature ⬜** (HTTPS only), **metrics/
  chart dashboard ⬜** (the Sprint C "two dashboards" and per-record "Queue
  Manager retry" **captions are NOT substantiated** by the docs — feature/flow
  claimed; UI not observed). Multi-company vs multi-store not distinguished.
- **Note:** "PRO" and `integration_shopify` are **VentorTech (R7)**, not
  Teqstars — do not cross-attribute.

## R3 — Emipro: Shopify Odoo Connector (v19 documentation)

- **Source name:** Emipro — Shopify Odoo Connector
- **Source type:** vendor documentation (v19)
- **URL / repo path:** https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/
  (~35 sub-pages) · repo: `competitor-source-notes.md` §R3;
  `competitor-screenshot-inventory.md` (Emipro)
- **Access date:** 2026-06-30 (Accessible; richest, most demonstrative doc tree).
- **What was reviewed:** ~35 sub-pages: setup/token (Path A & B), product config/
  management/stock, order + webhook-order config, operations (import customer/
  location, **queue**, scheduler), orders (unshipped/shipped/cancel/return-refund,
  grant-fulfillment-scopes), export-customer, export-sale-order, webhooks,
  Markets, metafields, channel/analytic mapping, sales report & **Log Book**,
  payouts, net-profit report, release notes.
- **Features actually observed (demonstrated):** custom-app token setup with an
  honest **trailing-slash URL-mismatch** warning + full scope string; **Batch
  Data Queues** (125 products / 50 orders per queue; Draft/Failed/Cancelled/Done;
  "Process Queue Manually"; **irreversible Force Done**; per-line Log Lines);
  **Automatic Scheduler** (per-process crons + Last-Operation panel); **webhooks**
  (product/order/customer; SSL required; states a **stale "19 retries/48h"**
  Shopify figure — a competitor-accuracy gap vs the current Tier-1 baseline);
  **Import Stock → manual Inventory Adjustment**; customer-export **email-dedup**
  (link, don't duplicate); **Shopify Markets** (per-market company/warehouse/
  pricelist/fiscal/journal; auto-created; no multi-warehouse); metafields
  (directional); payouts (Shopify-Payments-only → Bank Statement → reconcile);
  **Log Book / Mismatch Log** (reason-coded); multi-payment lines.
- **Screens actually observed:** EM-SETUP (3), EM-PRODUCT (~6 incl. CSV/XLSX map
  fallback), EM-QUEUE (4 — the strongest queue/log surface of the set),
  EM-SCHEDULER (2), EM-ORDER/RETURN/FULFILLMENT (~8 incl. multi-payment,
  Put-in-Pack), EM-MARKETS/METAFIELDS/CHANNEL/PAYOUT/LOG (~8).
- **Flows actually observed:** setup → product/import/mapping → batch queue
  processing + error inspection → scheduling → orders/returns/fulfillment →
  Markets/metafields/payouts/log book.
- **Screenshots available:** **yes** — **real addressable `.png` URLs** with
  descriptive alt text (~29); no binaries saved but capturable later.
- **Confidence:** High. **Evidence quality:** strongest for **queue/log
  observability** and honest limitation disclosure.
- **Limitations / inaccessible areas:** no price/license/author in docs; no
  connector-side rate-limit/throttle handling; **no automatic retry/backoff**
  (recovery is manual re-run); B2B not found; published v19 changelog is **stale**
  (entries stop at 17.0.3.2, Apr 2024).

## R4 — VentorTech: Shopify documentation (Confluence)

- **Source name:** VentorTech — Shopify documentation (R&D Products, space `pd`)
- **Source type:** vendor how-to docs (Confluence, anonymous/partial)
- **URL / repo path:** https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify
  · repo: `competitor-source-notes.md` §R4; `competitor-screenshot-inventory.md`
  (VentorTech R4)
- **Access date:** 2026-06-30 (**Partial** — hub + 11 child articles read
  anonymously; persistent "anonymous access" banner; 17 of 28 child articles
  **not read, recorded not-gated**).
- **What was reviewed:** hub + 11 child articles: webhooks, multi-location,
  auto-update products, pricelists→catalogs, historical orders, fulfillments,
  metafields, POS, default-customer/PII, order-risk, cancel-orders.
- **Features actually observed (demonstrated):** **webhook traffic-light health**
  (green/**yellow = callback-URL mismatch, check `web.base.url`**/red) — the best
  status-indicator pattern of the survey; multi-location via **"External
  Location"** grid with default fallback; pricelists→Catalogs with **Preview/
  Report dry-run** ("detect issues before sending"; Odoo = single source of truth
  for pricing); historical-orders cut-off import; fulfillments table (fetch/apply,
  per-line **"internal info"** diagnostic, Force Full Fulfillment); **order risk**
  (level/sentiment/action); two-step cancel-from-Odoo with irreversibility
  warning; **honest PII disclosure** (Basic plan → default customer / missing-
  customer error); POS import.
- **Screens actually observed:** VT-WEBHOOKS, VT-INVENTORY, VT-CATALOGS
  (Preview/Report), VT-FULFILLMENT, VT-METAFIELDS, VT-RISK, VT-CANCEL (9 article
  screenshots).
- **Flows actually observed:** webhook health/repair; location mapping; pricing
  dry-run → send; fulfillment fetch/apply; cancel-from-Odoo.
- **Screenshots available:** **yes** (9 article screenshots, anonymous/partial;
  pixels not inspected).
- **Confidence:** Medium (partial access; 17 articles unread). **Evidence
  quality:** high for the diagnostics/dry-run patterns actually read.
- **Limitations / inaccessible areas:** **Odoo version compatibility not stated**
  on any accessed Confluence page; pricing not here (R7); 17 child articles
  unread; initial OAuth wizard, standalone refunds/returns, payouts, dashboard/
  reporting not among the 11 pages read. Dated release notes live on R7, not here.

## R5 — Project Google Doc ("E-commerce user documentation") — internal resource

- **Source name:** Project Google Doc — "E-commerce user documentation"
- **Source type:** internal doc (private Google Doc)
- **URL / repo path:** https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit
  · repo: `competitor-source-notes.md` §R5; `source-access-notes.md` §R5
- **Access date:** 2026-06-30 — **BLOCKED (Google sign-in wall).** Only the title
  is exposed; body gated. **No authentication bypassed; no content inferred.**
- **What was reviewed:** title metadata only.
- **Features / screens / flows observed:** **none** (body gated).
- **Screenshots available:** **no** (blocked).
- **Confidence:** Blocked. **Evidence quality:** none beyond the title.
- **Limitations / inaccessible areas:** entire body. **Cross-source inference
  (strong):** the R6 `ecommerce_shopify` "Get Started" CTA
  (`odoo.com/r/ecommerce-shopify`) 301-redirects to this same doc, so R5 is
  **likely R6's setup guide** — still blocked; content not inferred.
- **Unblock action (ChatGPT-owned):** owner grants view access (e.g. to
  aysaadab@gmail.com) or exports PDF/DOCX/HTML.

## R6 — Odoo Apps: ecommerce_shopify (19.0)

- **Source name:** Shopify Connector for Odoo 19 (`ecommerce_shopify`, "Odoo IN
  Pvt Ltd")
- **Source type:** Odoo Apps listing
- **URL / repo path:** https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify ·
  repo: `competitor-source-notes.md` §R6; `competitor-screenshot-inventory.md`
  (R6-NOSHOTS)
- **Access date:** 2026-06-30 (Accessible listing; purchase needs login).
- **What was reviewed:** full listing (price $195.56, OPL-1, v19.0 only, 3824 LOC,
  **no ratings**) + version history + comments.
- **Features actually observed:** all **vendor claims / on-page facts only** —
  GraphQL + OAuth/self-access auth; **cron-based sync** (orders/pickings every
  10 min; inventory after order sync; the "real-time stock" bullet was
  **verification-downgraded** as contradicting the cron section); **no webhooks**;
  failure handling = email notifications + "retry mechanism" (no in-app queue/log
  UI); SKU dedup + avoid-duplicate-customer; returns/refunds added v19.0.2.0
  (2026-06-04); frequent recent dated changelog (a freshness positive).
- **Screens actually observed:** **none** — the listing has **no UI/workflow
  screenshots and no video** (icon + cross-promo banners only).
- **Flows actually observed:** none demonstrated — **feature/flow documented (as
  listing text); UI not observed.**
- **Screenshots available:** **no** (weakest visual evidence of the survey).
- **Confidence:** Low. **Evidence quality:** marketing listing text only;
  provenance (official vs India-entity partner) **unresolved** — do **not** treat
  as an "official" baseline.
- **Limitations / inaccessible areas:** product **export direction** unstated
  (sync described Shopify→Odoo); no webhooks/Markets/metafields/POS/B2B/multi-
  store found; thin adoption signal (no ratings).

## R7 — VentorTech: Odoo Shopify Connector PRO (`integration_shopify`, website + ecosystem + Apps)

- **Source name:** VentorTech — Odoo Shopify connector **PRO**
- **Source type:** vendor website + ecosystem pages + Odoo Apps listing +
  **dated release-notes** page
- **URL / repo path:** https://ventor.tech/solutions/odoo-shopify-connector/ ·
  https://apps.odoo.com/apps/modules/19.0/integration_shopify · repo:
  `competitor-source-notes.md` §R7; `competitor-screenshot-inventory.md`
  (VentorTech R7)
- **Access date:** 2026-06-30 (Accessible; Apps listing + dated release notes are
  the authoritative current sources).
- **Features actually observed:** OAuth (no manual tokens); **GraphQL since
  v2.0.0** with **v2.1.4 `@idempotent` directives** (refund/inventory, matching
  Tier-1 2026-04) + v2.1.6 extension — the **only competitor with demonstrated
  idempotency**; **background job queue** (OCA `queue_job`; `odoo.conf`
  prerequisites; "Run Now"; Failed-Job Notifications); webhooks ("8 events";
  **HMAC-SHA256** claim); **auto-workflow** ("up to 5 steps" with a visual
  pipeline); **field-mapping engine** (per-field direction + **custom Python
  transforms** + **test-against-live-data**); B2B (VAT/VIES 3× retry); Markets &
  Catalogs; multi-company inventory; **automatic retry** of safe ops after
  network/server errors; **two CRITICAL "orders silently skipped" fixes**
  (v2.1.6 paging, v2.1.2 timezone) — transparent defect history.
- **Screens actually observed:** **R7 marketing page = alt-text-only flow
  diagrams** (Initial Import / Product Export / Order Import / Tracking) — **not
  product UI**; deep UI screenshots are in **R4 Confluence**. So R7 = **feature/
  flow + dated release notes documented; product UI not observed here.**
- **Flows actually observed:** dated, mechanism-level release-note history
  (1.13.0 → 2.1.6) — the most transparent changelog of the set.
- **Screenshots available:** **no product-UI screenshots on R7** (4 alt-text
  marketing figures only; real UI is R4).
- **Confidence:** High for capabilities/reliability (dated release notes);
  Medium for screens (defer to R4). **Evidence quality:** best changelog +
  reliability evidence of the survey.
- **Limitations / inaccessible areas:** marketing-page staleness ("v13+") vs
  Apps (13–19); **no named rate-limit/backoff** ("avoid unnecessary API
  requests" is the closest); POS, gift cards, payout reconciliation, RMA-as-
  distinct-from-refund not found; connector-specific Odoo permission/record-rule
  model not detailed; OAuth wizard exact labels defer to video tutorials.

## R8 — Odoo Apps: sh_shopify_connector (19.0, Softhealer)

- **Source name:** Shopify-Odoo Connector (`sh_shopify_connector`, Softhealer)
- **Source type:** Odoo Apps listing (caption-rich walkthrough)
- **URL / repo path:** https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector ·
  repo: `competitor-source-notes.md` §R8; `competitor-screenshot-inventory.md`
  (R8-WALKTHROUGH)
- **Access date:** 2026-06-30 (Accessible; ~125 sequential screenshot/figure
  **caption** blocks with step text; flagship vendor product page 404).
- **Features actually observed:** custom-app connect gated behind **"Shopify
  Configuration Manager" access right** → status Done → Sync Logs; **Queue
  Dashboard Framework** (Contact/Product/Order/Checkout/Recommendation queues,
  draft/completed/failed counts, "Process Queues Manually"); **"Daily Queue
  Activity Tracking" chart**; **Payment Gateway Workflow Matrix** + Auto Sale
  Workflow; refunds/returns (credit note ↔ Shopify); fulfillment (validate →
  **fulfillment ID**; **"Needs Shopify Re-Export"** recovery flag); **widest
  breadth**: gift cards (import/export/disable), abandoned-checkout→CRM leads,
  product recommendations, Buy-with-Prime, directional metafields, publish/
  unpublish, exclude-from-sync, granular access-rights groups; webhooks
  (products/contacts/orders/fulfillment).
- **Screens actually observed:** ~29 caption groups (V01–V29) describing a
  near-end-to-end walkthrough incl. **Integration Dashboard + daily activity
  chart** — **captions only, pixels not inspected.**
- **Flows actually observed:** setup → import/export → orders → fulfillment →
  refunds → monitoring → advanced (per captions).
- **Screenshots available:** **yes but caption-only** (no rendered-image
  verification).
- **Confidence:** Low/Medium — breadth is broad but **no ratings/reviews/
  downloads and no dated changelog** corroborate it. **Evidence quality:**
  caption walkthrough; "real-time" framing is marketing (core = queue/cron +
  optional webhook).
- **Limitations / inaccessible areas:** multi-company **not found** on re-fetch;
  idempotency/dedup keys, rate-limit handling, webhook reconciliation detail
  (HMAC/ordering/replay) not documented; Markets/POS/B2B/payout reconciliation
  not mentioned; flagship product page 404 (no cross-check).

---

## Cross-source reconciliation summary (factual — no build conclusions)

- **Best demonstrated evidence:** **Emipro (R3)**, **VentorTech R4 Confluence**,
  and **Teqstars (R2, Sprint C2)** — real screenshots / step-by-step docs.
  **VentorTech R7** has the best **dated release-note + reliability** evidence.
- **Weakest evidence:** **ecommerce_shopify (R6)** — text-only listing, **no
  screenshots**; **sh_shopify_connector (R8)** — broad but caption-only, no
  ratings/changelog.
- **Blocked:** **Google Doc (R5)** — sign-in wall (owner access/export needed);
  **R5 is likely R6's setup guide** (redirect inference).
- **"Feature/flow documented; UI not observed" flags:** R6 (all capabilities,
  no screenshots); R7 product UI (marketing alt-text only — real UI is R4); R2
  pHash dedup, "two dashboards," and per-record "Queue Manager retry" (claimed
  but not shown in the accessible docs); R8 (captions, no rendered images).
- **Reliability whitespace confirmed across the set:** **rate-limit/cost-aware
  throttling** — no competitor demonstrates it (R2 confirmed ⬜; R7 closest as a
  claim); **automatic retry/backoff** — only R7 demonstrates it; **first-class
  missed-record reconciliation surface** — none demonstrates it (R3 offers manual
  re-import; R2 has cursors + per-return resync only); **`@idempotent` writes** —
  only R7 demonstrates them.
- **Pricing facts (on-page, 2026-06-30):** Webkul $170 · Teqstars $326.20 ·
  ecommerce_shopify $195.56 · sh_shopify_connector $168.81 · VentorTech
  €499 / $569.16; Emipro price not in its docs.
- **Competitor-accuracy caution:** Emipro's webhook doc carries the **outdated**
  "19 retries / 48h" Shopify figure vs the current Tier-1 "8 retries / 4h"
  (DP-001) — competitor docs are not Tier-1 and must not be adopted as fact.

> **What this reconciliation establishes for the sprint's questions:** *(1)–(4)*
> what competitors provided, expose, do well, and do poorly are answered here and
> in the [feature-screen map](./competitor-feature-screen-map.md); *(5)–(10)* what
> we cover/miss/can-do-better/should-avoid and any amendment candidates are in
> [`competitor-gap-analysis-against-blueprint.md`](./competitor-gap-analysis-against-blueprint.md)
> and [`../03-architecture/blueprint-amendment-candidates.md`](../03-architecture/blueprint-amendment-candidates.md).
