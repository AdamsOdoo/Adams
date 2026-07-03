# Competitor Feature / Screen Map (Evidence & Blueprint Reconciliation Sprint)

> **Purpose.** A **screen- and flow-pattern** matrix (distinct from the
> feature-area
> [`competitor-feature-matrix.md`](./competitor-feature-matrix.md)): the rows are
> the setup/sync/operator **screens and flows** a connector exposes, and each
> cell records **whether that screen/flow was actually observed** in the captured
> evidence. It is a direct input to Part D (UI/UX Screen Design) — it says *which
> screens competitors expose*, not *what we should build* (the no-code /
> research-first gate, `CLAUDE.md` §4–§5, is in force; **no MVP or architecture
> conclusion is drawn here**).
>
> **Evidence base:** repo-saved only — [`competitor-feature-matrix.md`](./competitor-feature-matrix.md),
> [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md),
> [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md).
> Access dates: **2026-06-30** for all, **except Teqstars (TQ) 2026-07-01**
> (Sprint C2 rebaseline). Reconciliation date **2026-07-03**.

## How to read

**Cell values (this sprint's screen-observation vocabulary):**

| Symbol | Meaning |
| :--: | --- |
| **● Observed** | A screen/flow was demonstrated — step-by-step doc and/or screenshot shows it. |
| **◐ Implied** | Documented or claimed (listing/marketing/caption), **but UI not observed** ("feature/flow documented; UI not observed"). |
| **○ Not observed** | Not found on the accessed pages (absence of evidence, not evidence of absence). |
| **⊘ Explicitly absent** | The vendor states it is not supported. |
| **🔒 Inaccessible** | Blocked by access (gated source). |
| **— N/A** | Not applicable to that product's documented model. |

**Columns:** **WK** Webkul (R1) · **TQ** Teqstars (R2, Sprint C2) · **EM** Emipro
(R3) · **VT** VentorTech PRO (R4 Confluence + R7 release notes) · **EC**
ecommerce_shopify (R6) · **SH** sh_shopify_connector (R8).

> **Column caveats.** **EC** listing has **no screenshots** → its capability cells
> are ◐ at best (vendor claims, cron-based). **SH** cells rest on a **caption
> walkthrough** (pixels not inspected; no ratings/changelog). **TQ** rebaselined
> from ~98 real doc screenshots, but a few reliability items stay ◐/○ (asserted or
> omitted, not shown). **VT** UI evidence is R4 Confluence (partial, 11 of 28
> articles read) + R7 dated release notes (mechanism-level, not always a rendered
> screen). **R5 (Google Doc) is fully 🔒 blocked** and is **not** a column — it has
> no observable screens (likely R6's setup guide, per the redirect inference).

---

## A. Setup, connection & configuration screens

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Initial setup / connection wizard | ● | ● | ● | ◐ | ◐ | ● | WK S1–S7; TQ `setup/create_instance`+`generate_credentials`; EM Path-A token wizard; VT OAuth "3 steps" documented, exact wizard screens deferred to video (R7); EC claim (no shots); SH caption connect flow. |
| Credential / API setup | ● | ● | ● | ● | ◐ | ● | Custom-app credentials all round. EM warns **trailing-slash URL mismatch fails auth**; TQ shows full Admin API scope list + "enable all" warning; VT masks secrets. |
| Test connection | ● | ● | ○ | ◐ | ○ | ● | WK & TQ explicit **Test Connection** step; VT runs a connection+scope test (claimed); SH verifies via **Sync Logs**; EM/EC no explicit test screen observed. |
| Multi-store setup | ○ | ● | ◐ | ● | ○ | ◐ | TQ = one **instance per store** (documented model); VT "as many stores as you want"; EM implied via Markets; SH "within a single DB" (caption); WK single; EC not found. |
| Configuration / settings screen(s) | ● | ● | ● | ● | ◐ | ● | WK tab-segments (Basic/Sales/Product); **TQ/EM/SH config-dense** (TQ instance form 10+ order toggles, several dev-mode-gated) — a **toggle-density cautionary example** for Part D. |

## B. Catalog screens: products, variants, media, price

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Product import | ● | ● | ● | ● | ◐ | ● | EM & TQ: create/update date ranges + "update existing" + draft-only + ID list; TQ auto-creates missing during collection/order import. |
| Product export (Odoo→Shopify) | ● | ● | ● | ● | ○ | ● | VT exports as **draft for review**; TQ **draft-safe** (empty Sales Channels → not published); **EC export direction unstated**. |
| Product update | ◐ | ● | ● | ● | ◐ | ◐ | TQ product-update ×12 screenshots (four methods; Set Price/Set Quantity; Publish/Unpublish); VT auto-update-products (R4); EM update-existing + product window; WK/EC/SH implied. |
| Variant handling | ○ | ● | ● | ● | ◐ | ◐ | TQ via **Listing Items** (+HS-code/country rules); VT fixed a **250-variant cap**; EM variants column; WK **not found**. |
| Image / media sync | ○ | ● | ● | ● | ◐ | ◐ | TQ image sync ● but **pHash dedup ◐** (dependency + comparison-table only, no workflow); EM import + Odoo-side update; VT bidirectional; WK **not found**. |
| Price sync | ◐ | ● | ● | ● | ○ | ○ | EM Pricelist + **Compare-At**; VT & TQ pricelists + **per-market Catalogs** (TQ quantity/volume rules); WK claim; EC/SH not found. |

## C. Customers

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Customer import / sync | ◐ | ● | ● | ● | ◐ | ● | VT documents the **Basic-plan no-PII limitation** honestly; TQ queue + `customer/create` webhook; EM/SH import. |
| Customer matching / dedup | ◐ | ● | ● | ● | ◐ | ◐ | VT email/name/phone normalized; EM **email link (no duplicate)**; TQ multi-field search (Name/City/State/Country/Zip/Street/Street2/Email/Parent-Id) + webhook link-existing. |
| Customer export | ○ | ○ | ● | ◐ | ○ | ● | **EM email-dedup export**; SH export; **WK/EC/TQ import-only** (TQ has **no customer-export page**). |

## D. Orders, payments, refunds

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Order import | ● | ● | ● | ● | ◐ | ● | VT real-time via webhook; EM & TQ manual/scheduler/webhook (queue; TQ per gateway+financial-status, POS/gift-card/duties/tips lines). |
| Order status handling | ◐ | ● | ◐ | ● | ◐ | ● | SH **Payment Gateway Workflow Matrix**; EM & TQ per gateway+financial status; **TQ demonstrates click & collect** (Ready-for-Pickup → Picked-Up). |
| Invoice / payment handling | ○ | ● | ◐ | ● | ◐ | ● | Auto-workflow driven (VT "up to 5 steps"; SH & TQ confirm/invoice/validate/register per gateway+financial status); TQ/SH map **gateway→journal**; TQ Mark-as-Paid write-back. |
| Refund handling (refund/return/cancel) | ○ | ● | ● | ● | ◐ | ● | EM/VT/SH/TQ demonstrate. TQ: refund from credit note (**amount-match guard**), cancel (reason/notify/restock/refund), **full returns lifecycle** (`returns/*` webhooks + create-from-Odoo + **Force Restock** + credit-note link). |

## E. Inventory & fulfillment

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Inventory sync | ● | ● | ● | ● | ◐ | ● | "Real-time" **overstated** by WK/EC/SH (actually cron/queue). VT & TQ optional real-time-on-stock-move or scheduled+manual. Stock-source choice (Free-to-Use/On-Hand/Forecast) exposed by WK/TQ/EM/VT. |
| Location mapping | ○ | ● | ● | ● | ◐ | ◐ | TQ combines multiple locations + **excludes third-party**; VT **"External Location"** grid with default fallback; EM locations↔warehouses; WK single location. |
| Import stock (apply control) | ○ | ● | ● | ● | ◐ | ● | EM creates an **Inventory Adjustment to process manually**; TQ "Validate Inventory Adjustment?" (auto optional; lot/serial skipped). |
| Fulfillment / tracking update | ◐ | ● | ● | ● | ◐ | ● | EM **Put-in-Pack multi-package**; VT carrier tracking + per-line **"internal info"** diagnostic; SH **fulfillment-ID write-back** + **"Needs Shopify Re-Export"** flag; TQ deliver→Update-in-Marketplace. |

## F. Sync infrastructure & reliability screens

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Manual sync | ● | ● | ● | ● | ◐ | ● | Universal on-demand wizards; TQ "Operations" popup + single-record Sync-to-Odoo/Shopify. |
| Scheduled / cron sync | ● | ● | ● | ● | ● | ● | EC = cron-only (orders 10 min); EM & TQ per-process scheduler (TQ "Automatic Jobs" + Last-Processed cursors). |
| Queue / job monitor | ○ | ● | ● | ● | ○ | ● | **EM Data Queues** (Draft/Failed/Cancelled/Done + Log Lines) and **SH Queue Dashboard** (draft/completed/failed counts) are the richest; VT `queue_job` "Run Now"; TQ per-op queues; **WK = Feeds staging; EC = none**. |
| Logs / audit / sync history | ● | ● | ● | ● | ◐ | ● | **EM Log Book / Mismatch Log (reason-coded)** leads; TQ Queues‣Logs + log levels + **Activity-on-failure**; EC **email-only** (no in-app log UI). |
| Error handling (per-record isolation) | ● | ● | ● | ● | ◐ | ● | EM isolates Failed/Cancelled lines; VT batches valid records; TQ per-op queues + Activity-on-failure. |
| Retry failed jobs | ◐ | ◐ | ◐ | ● | ◐ | ◐ | **Automatic retry/backoff observed only for VT** (safe ops after network/server errors). WK error-feed re-evaluate, EM/TQ/SH manual re-run / re-export flag = **manual retry only** (no automatic-retry taxonomy — TQ verified ○ for that). |
| Webhooks | ○ | ● | ● | ● | ⊘ | ● | **EC has none (cron-poll only, ⊘)**; VT 8 events + **HMAC-SHA256** claim; TQ order/product/customer/returns events + background-thread fast-ack, **HMAC ○ not documented**. |
| Webhook / missed-record reconciliation | ○ | ◐ | ● | ● | ○ | ◐ | EM **manual import to recover missed webhooks**; VT traffic-light health + dated fixes; **TQ = Last-Processed cursors + per-return Resync only (no first-class reconciliation surface, verified ○)**. |
| Rate-limit / throttle handling | ○ | ○ | ○ | ◐ | ○ | ○ | **No competitor demonstrates a rate-limit/cost strategy** (TQ verified ○; VT closest as a claim "avoid unnecessary API requests"). Confirmed whitespace. |
| Idempotency / duplicate prevention | ◐ | ◐ | ● | ● | ◐ | ◐ | **VT = explicit GraphQL `@idempotent` directives (2026-04)** — only demonstrated case; EM email/SKU + re-export block; TQ dedup ● but idempotency **◐ implied** (adjacent guards; Sprint C snippet unverified). |

## G. Mapping, dashboard, permissions & multi-entity screens

| Screen / flow | WK | TQ | EM | VT | EC | SH | Source / note |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Mapping screens (field / gateway / location) | ● | ● | ● | ● | ◐ | ● | **VT most advanced** — per-field directional + **custom Python transforms + test-against-live-data**; TQ gateway→journal + location→warehouse + metafield→field; EM CSV/XLSX map fallback. |
| Dashboard / status overview | ◐ | ◐ | ◐ | ◐ | ○ | ● | **SH strongest** (Integration Dashboard + **daily activity chart**, caption-only); **TQ docs show only an Operations launcher + Queues/Logs — no metrics/chart dashboard** (Sprint C "two dashboards" caption **not** substantiated → ◐/○); EC none. |
| Permissions / access screen | ○ | ◐ | ● | ◐ | ○ | ● | **EM** (Odoo user rights + scopes) and **SH** (granular access-rights groups; "Shopify Configuration Manager" gate) lead; TQ ◐ (scope list + "sufficient access rights", **no access-group/record-rule model, no HMAC**). |
| Multi-company | ◐ | ○ | ● | ● | ○ | ○ | Demonstrated: EM (Markets per-market company) + VT (multi-company inventory). **TQ ○** (Company field, multi-company not distinguished from multi-store); WK default-Company field only; SH not found. |
| Payout / accounting reconciliation | ○ | ● | ● | ○ | ○ | ○ | **EM & TQ demonstrate** (both **Shopify-Payments-only** → Bank Statement → Auto/Manual Reconcile; TQ per-line reason-coded warnings). Still-rare capability. |

## H. Notable competitor-specific / breadth screens (Part D context)

| Pattern | Who exposes it | Class | Source / note |
| --- | --- | :--: | --- |
| Import **staging + error-feed** queue | WK | ● | Data staged as "Feeds"; bad records = error feeds, fixable + re-evaluable (WK-FEEDS S14). |
| **Preview / Report dry-run before push** | VT | ● | Markets & Catalogs Preview/Report — "detect issues before sending data" (VT-CATALOGS). A standout validation pattern. |
| **Traffic-light webhook health** with diagnostic colour | VT | ● | green/**yellow = callback-URL mismatch, check `web.base.url`**/red (VT-WEBHOOKS) — best status-indicator of the survey. |
| **Daily activity time-series chart** | SH | ◐ | "Daily Queue Activity Tracking" chart (caption-only). |
| **Click & collect** pickup lifecycle | TQ | ● | Ready-for-Pickup → Picked-Up order status (TQ order-status ×10). |
| **Force Restock / Force Done / Force Full Fulfillment** guards | EM, TQ, VT | ● | Irreversible/override actions with divergence warnings — a footgun UX to handle carefully in Part D. |
| **Shopify Markets & Catalogs** (per-market pricing) | EM, TQ, VT | ● | Premium differentiator; TQ Catalogs carry quantity/volume rules. |
| **Metafields** (directional mapping) | EM, TQ, VT, SH | ● | Product/variant/order/customer directional mapping with status badges (TQ). |
| **Gift cards** (import/export/disable) | SH | ● (caption) | Only SH demonstrates full gift-card management; TQ ◐ = gift-card order-line only. |
| **POS order import** | TQ (●), EM/VT (◐) | ● / ◐ | TQ Default POS Customer + POS lines; EM claim; VT via "Closed" status. |
| **B2B** (company detection, VAT/VIES) | VT | ● | Full B2B (VIES 3× retry); TQ ◐ = B2B **pricing** via Catalogs only. |
| **Abandoned-checkout→CRM / recommendations / Buy-with-Prime** | SH | ◐ | SH-unique breadth (caption-only). |
| **Order risk** (level/sentiment/action) on the order | VT | ● | Imported with the order (VT-RISK). |
| **Dated, mechanism-level changelog** (trust signal) | VT (●), EC (●) | ● | VT release notes 1.13.0→2.1.6 incl. two **CRITICAL "orders silently skipped" fixes** — transparent defect history; EC recent dated cadence. |

---

## Coverage read-out (what competitors expose — no build conclusion)

- **Table-stakes screens present across most competitors:** connection wizard,
  credential setup, product import/export, customer import, order import,
  inventory sync, location mapping, fulfillment/tracking, logs, manual +
  scheduled sync, mapping screens, refunds.
- **Differentiated screens present in only some:** queue/job monitor with
  failure counts (EM, SH, VT), reason-coded log book (EM, TQ), Preview/Report
  dry-run (VT), traffic-light webhook health (VT), payout reconciliation
  (EM, TQ), Markets/Catalogs (EM, TQ, VT), gift cards (SH), B2B (VT),
  daily-activity dashboard (SH).
- **Screens/flows no competitor clearly demonstrates (whitespace):** a unified
  **metrics/status dashboard** with correctness signals (SH caption only, TQ
  none); **first-class missed-record reconciliation** surface; **rate-limit/
  cost-aware throttling** UI or status; **automatic retry/backoff** (only VT);
  an explicit **first-push safety guard** screen before the first Odoo→Shopify
  push; a plain-language **"what will change / risks before sync"** preview
  beyond VT's pricing dry-run.
- **Inaccessible / unobserved caveats:** R5 fully blocked; EC has **no
  screenshots** (all ◐); SH is caption-only; several TQ reliability items and
  R7 product-UI are **documented but UI not observed**.

> These whitespace items and the strong patterns above are reconciled against the
> accepted blueprint in
> [`competitor-gap-analysis-against-blueprint.md`](./competitor-gap-analysis-against-blueprint.md);
> screen-design implications for Part D are collected there and in
> [`../03-architecture/blueprint-amendment-candidates.md`](../03-architecture/blueprint-amendment-candidates.md).
