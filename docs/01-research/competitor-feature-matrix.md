# Competitor Feature Matrix (Research Sprint C — first research matrix)

> **First research matrix, not a final MVP or feature taxonomy.** Rows = feature
> areas; columns = the six competitor connectors. Every non-empty cell is backed
> by a citation in
> [`competitor-deep-dives.md`](./competitor-deep-dives.md) /
> [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md).
> **Access dates:** original Sprint C competitor evidence access date **2026-06-30**;
> **TeqStars (TQ) Sprint C2 rebaseline access date 2026-07-01** — the **TQ cells now
> reflect the Sprint C2 page-classified evidence**, while **all other competitor
> cells (WK/EM/VT/EC/SH) remain based on the 2026-06-30 Sprint C evidence unless
> otherwise noted**. This consolidates competitor evidence only; it
> **draws no MVP or architecture conclusions** (gated — `CLAUDE.md` §4–§5). The
> canonical feature taxonomy (RB-12) will normalize these rows later.
>
> **Symbols:**
> `✅` Demonstrated / visible workflow (step-by-step flow and/or screenshot) ·
> `🟨` Vendor claim only (stated, not demonstrated) ·
> `⬜` Not found on accessed pages ·
> `🚫` Explicitly absent (vendor states it is not supported) ·
> `🔒` Blocked / unknown due to access.
>
> **Columns:** **WK** = Webkul (R1) · **TQ** = Teqstars (R2) · **EM** = Emipro (R3)
> · **VT** = VentorTech PRO (R4+R7) · **EC** = ecommerce_shopify (R6, "Odoo IN
> Pvt Ltd") · **SH** = sh_shopify_connector (R8, Softhealer).
>
> **Cross-cutting evidence caveats (apply to every TQ/EC/SH cell):**
> **TQ** — *(Sprint C2, 2026-07-01)* the Teqstars **docs are now accessible**
> (the Sprint C 403 was a bot/UA filter, since cleared); TQ cells were
> **rebaselined per page** from ~98 screenshot-backed, step-by-step doc pages, so
> most TQ cells are now **✅ demonstrated** — **but** a few reliability items
> (idempotency, automatic-retry, cross-object reconciliation, rate-limit, HMAC,
> metrics dashboard) stay **➖/⬜** because the docs assert or omit rather than
> show them (adversarially verified — 3 proposed upgrades were downgraded to ⬜).
> A comparison-table checkmark (e.g. pHash "Exclusive") is **not** treated as
> demonstrated → stays 🟨. **EC** — listing has **no screenshots**, so all EC
> capability cells are 🟨 vendor claims (cron-based). **SH** — cells marked ✅
> rest on a **captioned walkthrough** (pixels not inspected) and **no ratings/
> changelog** corroborate them. **EM/VT/TQ** now carry the most demonstrated (✅)
> evidence (real screenshots / dated release notes / step-by-step docs).

---

## 1. Setup, connection & configuration

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Store / instance connection | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | All connect via a custom Shopify app. **VT & TQ** use OAuth (TQ also supports manual token / legacy password); WK/EM/SH paste credentials. *Impl.:* offer **OAuth-first**, low-friction connect. |
| Credential / auth flow | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | EM warns a **trailing-slash URL mismatch fails auth**; **TQ** documents the full Admin API scope list with an "enable all scopes" warning. *Impl.:* validate credentials inline; mask secrets. |
| Test connection | ✅ | ✅ | ⬜ | 🟨 | ⬜ | ✅ | WK & **TQ** have an explicit **Test Connection** step; VT runs a connection test + scope check; SH verifies via Sync Logs. *Impl.:* explicit pass/fail connection test. |
| Dashboard / command center | 🟨 | 🟨 | 🟨 | 🟨 | ⬜ | ✅ | **SH** = strongest (Integration Dashboard + **daily activity chart**); **TQ docs show only an Operations launcher + Queues/Logs + Smart-Notification alerts — no metrics/chart dashboard** (the Sprint C "two dashboards" caption is **not** substantiated by the docs → 🟨/⬜); VT has an auto-workflow "visual pipeline"; EC has none. *Impl.:* a real monitoring dashboard differentiates. |
| Configuration / settings IA | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | WK tab-segments (Basic/Sales/Product); **TQ/EM/SH are config-dense** (TQ instance form has 10+ order toggles, several dev-mode-gated). *Impl.:* group config, add inline help, **progressive disclosure** (TQ is a toggle-density cautionary example). |

## 2. Catalog: products, variants, media, pricing

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Product import | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | EM & **TQ**: Create/Update date ranges + "update existing" + draft-only import + ID list; **TQ auto-creates missing products during collection/order import**. *Impl.:* incremental, filterable imports. |
| Product export (Odoo→Shopify) | ✅ | ✅ | ✅ | ✅ | ⬜ | ✅ | **EC export direction unstated**. VT exports as **draft for review**; **TQ = draft-safe** (Add-to-Listings → Export Listings; "leave Sales Channels empty → not published to any channel"). *Impl.:* bidirectional + draft-first export. |
| Variants / options | ⬜ | ✅ | ✅ | ✅ | 🟨 | 🟨 | VT fixed a **250-variant import cap** (v2.1.4); **TQ syncs variants via Listing Items** (+ per-variant HS Code/Country-of-Origin rules). **WK: not found.** *Impl.:* support the 2048-variant model. |
| Images / media | ⬜ | ✅ | ✅ | ✅ | 🟨 | 🟨 | **TQ image sync ✅** (Sync-Listing-Images toggle; image on listing/item) but **pHash dedup stays 🟨** (comparison-table + `imagehash`/`PyWavelets` dependency; no workflow shown); EM imports + Odoo-side update; VT bidirectional. **WK: not found.** *Impl.:* media sync with dedup. |
| Price lists / pricing | 🟨 | ✅ | ✅ | ✅ | ⬜ | ⬜ | EM: Pricelist + **Compare-At Pricelist**; VT & **TQ**: pricelists + **per-market via Catalogs** (TQ Catalogs carry quantity rules + volume/tier pricing). *Impl.:* pricelist + compare-at + per-market. |
| Publish / unpublish | ⬜ | ✅ | ✅ | ✅ | ⬜ | ✅ | EM (Web/Web+POS); SH (sales-channel membership); **TQ Manage-Sales-Channels Publish/Unpublish per channel** (product, listing item, collection). *Impl.:* channel-based publish control. |

## 3. Inventory & locations

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Inventory sync | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | "Real-time" is **overstated** by WK/EC/SH (actually cron/queue). VT & **TQ** do real-time-on-stock-move (optional push) **or** scheduled + manual. *Impl.:* be honest about latency; reconcile. |
| Stock quantity-field choice | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ | EM (Forecast vs Free-to-Use), VT & **TQ** (Free-to-Use / On-Hand / Forecasted, "Stock Based On"), WK (on-hand/forecasted). *Impl.:* let users pick the source quantity. |
| Multi-location | ⬜ | ✅ | ✅ | ✅ | 🟨 | 🟨 | **EM/VT/TQ demonstrated** (locations↔warehouses; **TQ export combines multiple locations** + **third-party location excluded**; VT "External Location" grid). **WK single location only.** *Impl.:* multi-location is table-stakes; map per-location (Tier-1: write per `inventory_item_id`+`location_id`). |
| Import stock | ⬜ | ✅ | ✅ | ✅ | 🟨 | ✅ | EM creates an **Inventory Adjustment to process manually**; **TQ Import Inventory with "Validate Inventory Adjustment?"** (auto-validate optional; lot/serial skipped). *Impl.:* controlled apply of imported stock. |

## 4. Customers & addresses

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Customer import | 🟨 | ✅ | ✅ | ✅ | 🟨 | ✅ | VT documents the **Basic-plan "no PII" limitation** honestly; **TQ** imports name/email/phone/address via queue + webhook (customer/create). *Impl.:* handle PII-gated plans gracefully. |
| Customer export | ⬜ | ⬜ | ✅ | ➖ | ⬜ | ✅ | **EM: email-dedup links instead of duplicating**. **WK/EC/TQ: import only** (TQ has **no customer-export page** and customer metafields are import-only — reinforces the DEC-003 "customer export = later" baseline). *Impl.:* dedupe-by-email on export. |
| Address handling | ⬜ | ✅ | ➖ | ➖ | 🟨 | ➖ | **TQ** imports address + dedups on Street/Street2/City/State/Country/Zip; others mostly implied via contact fields. *Impl.:* explicit billing/shipping mapping + country/state matching. |
| Customer dedup / matching | 🟨 | ✅ | ✅ | ✅ | 🟨 | 🟨 | **VT**: email/name/phone (normalized); **EM**: email link; **TQ**: multi-field search (Name/City/State/Country/Zip/Street/Street2/Email/Parent-Id) "to avoid duplicating" + webhook link-existing. *Impl.:* multi-key normalized matching. |

## 5. Orders, payments, refunds, fulfillment

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Order import | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | VT: **real-time via webhook**; EM & **TQ**: manual/scheduler/webhook (queue-processed; TQ per gateway+financial-status workflow, fulfillment-status filter, stock-move if fulfilled, POS/gift-card/duties/tips lines). *Impl.:* webhook + scheduled backfill. |
| Order status mapping | 🟨 | ✅ | 🟨 | ✅ | 🟨 | ✅ | SH **Payment Gateway Workflow Matrix**; EM & **TQ** per gateway+financial status; **TQ also demonstrates click&collect** (Ready-for-Pickup / Picked-Up). *Impl.:* configurable status/workflow mapping. |
| Invoice creation | ⬜ | ✅ | 🟨 | ✅ | 🟨 | ✅ | Driven by an **auto-workflow** (VT "up to 5 steps"; SH & **TQ** confirm/create-invoice/validate/register-payment per gateway+financial status). *Impl.:* rule-based auto-workflow. |
| Payment handling | ⬜ | ✅ | ➖ | ✅ | 🟨 | ✅ | **TQ/SH** map **gateway→Odoo journal** (TQ also Mark-as-Paid write-back + 3 tax systems); VT applies Shopify payments to invoices + currency conversion. *Impl.:* gateway→journal mapping. |
| Payout reconciliation | ⬜ | ✅ | ✅ | ⬜ | ⬜ | ⬜ | **EM & TQ demonstrate** (both **Shopify-Payments-only** → Bank Statement → Auto/Manual Reconcile; TQ per-line warnings: Order/Invoice-not-found, amount-mismatch). *Impl.:* robust payout reconciliation is still rare (whitespace narrows but stays SP-only). |
| Refunds / returns / cancellations | ⬜ | ✅ | ✅ | ✅ | 🟨 | ✅ | EM/VT/SH/**TQ** demonstrate refunds + cancellations + returns. **TQ**: refund from credit note (**amount-match guard**), cancel (reason/notify/restock/refund), **full returns lifecycle** (`returns/*` webhooks + create-from-Odoo + **Force Restock** + credit-note link). *Impl.:* idempotent refunds; conditional returns. |
| Fulfillment / tracking export | 🟨 | ✅ | ✅ | ✅ | 🟨 | ✅ | EM **Put-in-Pack multi-package**; VT carrier tracking; SH fulfillment-ID write-back; **TQ** deliver→Update-in-Marketplace (status+tracking) + import-shipped→stock-moves. *Impl.:* FulfillmentOrder-based (Tier-1), multi-package, tracking write-back. |

## 6. Sync infrastructure

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Webhooks | ⬜ | ✅ | ✅ | ✅ | 🚫 | ✅ | **EC has none (cron-poll only).** VT: 8 events + HMAC-SHA256 + dated hardening. **TQ**: order/product(create/update/delete)/customer/returns events + Fetch/Delete Webhook + **background-thread processing** (fast-ack), HTTPS required — **but HMAC ⬜ not documented**. *Impl.:* webhooks **+ reconciliation + HMAC** (Tier-1: delivery not guaranteed). |
| Scheduled / cron sync | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | EC = cron-only (orders 10 min). EM & **TQ** per-process scheduler (TQ "Automatic Jobs" per operation + Last-Processed cursors). *Impl.:* scheduled backfill alongside webhooks. |
| Manual sync | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | Universal (on-demand wizards); **TQ** "Operations" popup per object + single-record "Sync to Odoo/Shopify". *Impl.:* always offer manual run. |
| Queue / job processing | ⬜ | ✅ | ✅ | ✅ | ⬜ | ✅ | **VT = real async job queue (`queue_job`)**; EM = batch Data Queues; SH = Queue Dashboard Framework; **TQ = per-op queues** (Product/Customer/Order/Return) + Queue Batch Limit (100), **cron-processed** (framework not named). **WK = Feeds staging; EC = none.** *Impl.:* a real job/queue layer (Tier-1: Odoo core has only `ir.cron`; `queue_job` is community → AR-003). |

## 7. Reliability & observability

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Logs (audit / sync history) | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | **EM Log Book/Mismatch Log (reason-coded)** leads; **TQ** = Queues‣Logs, log levels (ALL/SUCCESS/ERROR), per-record error messages + metafield-error tagging (**typed logs, not a formal reason-code taxonomy**); VT "every action logged". **EC email-only.** *Impl.:* in-app, reason-coded logs. |
| Error handling | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | EM isolates Failed/Cancelled queue lines; VT batches valid records; **TQ** per-op queues + **Activity-on-failure** (Responsible + due date). *Impl.:* per-record isolation. |
| Retry / recovery | 🟨 | ➖ | 🟨 | ✅ | 🟨 | ✅ | **Only VT = automatic retry** (safe ops after network/server errors); EM/SH = manual re-run / re-export flag; **TQ = queue re-processing + collection "retried next run" + manual re-run — no automatic-retry/backoff taxonomy** (verified ⬜ for that). *Impl.:* automatic retry/backoff is a differentiator. |
| Duplicate prevention / idempotency | 🟨 | ✅ / ➖ | ✅ | ✅ | 🟨 | 🟨 | **VT = explicit GraphQL idempotency directives (Shopify 2026-04)**; EM = email/SKU + re-export block; **TQ dedup ✅** (customer multi-field + product match-key + Create-Odoo guard + webhook link-existing) but **idempotency ➖ implied only** — adjacent guards (refund amount-match, already-cancelled), **no explicit `@idempotent` directive** on the docs; the Sprint C snippet stays unverified. *Impl.:* `@idempotent` writes + binding keys (AR-005/AR-006). |
| Webhook reconciliation | ⬜ | ➖ | ✅ | ✅ | ⬜ | 🟨 | EM provides **manual import to recover missed webhooks**; VT traffic-light health + dated fixes; **TQ = incremental Last-Processed cursors + per-return Resync + Fetch-Webhook config-reconcile — no first-class missed-record reconciliation surface** (verified ⬜ for that). *Impl.:* reconciliation job is mandatory, not optional (Tier-1). |
| Rate-limit / throttle handling | ⬜ | ⬜ | ⬜ | 🟨 | ⬜ | ⬜ | **No competitor names a rate-limit/cost strategy** — **TQ confirmed ⬜** (only "gap your schedules" operator guidance); VT closest ("avoid unnecessary API requests"). *Impl.:* **clear whitespace** — GraphQL cost-aware throttling. |
| Permissions / security model | ⬜ | ➖ | ✅ | ➖ | ⬜ | ✅ | **EM** (Odoo user rights + explicit Shopify scopes) and **SH** (granular access-rights groups) lead; **TQ ➖** (full Admin API scope list + "sufficient access rights" + HTTPS webhooks, but **no dedicated access-group/record-rule model** and **no HMAC**). *Impl.:* ship `ir.model.access.csv` + groups + record rules (Tier-1). |

## 8. Advanced / breadth

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Mappings (field / gateway / location) | ✅ | ✅ | ✅ | ✅ | 🟨 | ✅ | **VT** = per-field directional + **custom Python transforms + test-against-live-data** (most advanced); **TQ** = gateway→journal workflow + location→warehouse + metafield→Odoo-field mapping. *Impl.:* configurable, testable mappings. |
| Multi-store | ⬜ | ✅ | ➖ | ✅ | ⬜ | 🟨 | VT "as many stores as you want"; **TQ = one instance per store** (documented model). *Impl.:* multi-store with per-store config. |
| Multi-company | ➖ | ⬜ | ✅ | ✅ | ⬜ | ⬜ | **WK shows a default Company field only.** Demonstrated multi-company = EM (Markets per-market company) and VT (multi-company inventory). **TQ ⬜** (instance has a Company field but **multi-company not distinguished from multi-store**); SH unverified. *Impl.:* multi-company isolation via record rules. |
| Shopify Markets | ⬜ | ✅ | ✅ | ✅ | ⬜ | ⬜ | **EM/VT/TQ** demonstrate Markets & Catalogs; **TQ Catalogs** (Market/Company-Location/App) carry **quantity rules + volume/tier pricing**. *Impl.:* Markets is a premium differentiator. |
| Metafields | ⬜ | ✅ | ✅ | ✅ | ⬜ | ✅ | EM/VT/SH/**TQ** = directional mapping; **TQ** Product/Variant import+export, Customer/Order import-only, status badges, wipe-on-missing. *Impl.:* directional metafield mapping. |
| Gift cards | ⬜ | ➖ | 🟨 | ⬜ | ⬜ | ✅ | **Only SH demonstrates full mgmt** (import/export/disable-in-Shopify); **TQ ➖** = gift-card **order-line** import via a Gift Card Product (not gift-card management). *Impl.:* niche but a breadth differentiator. |
| POS | ⬜ | ✅ | 🟨 | ➖ | ⬜ | ⬜ | **TQ demonstrates POS order import** (Default POS Customer + POS order lines); EM claims it; VT via "Closed" status. *Impl.:* POS-order import (Tier-1 order topics). |
| B2B | ⬜ | ➖ | ⬜ | ✅ | ⬜ | ⬜ | **VT** = full B2B (company detection, VAT/VIES); **TQ ➖** = B2B/wholesale **pricing** via Catalogs (Company-Location + quantity/volume), no VAT/VIES company detection shown. *Impl.:* B2B is differentiating whitespace. |
| Abandoned checkout / recommendations / Buy-with-Prime | ⬜ | ⬜ | ➖ | ⬜ | ⬜ | ✅ | **SH-unique breadth** (abandoned-checkout→CRM, recommendations, Buy-with-Prime); **TQ ⬜** (not in docs). *Impl.:* optional add-on candidates. |
| Reporting / analytics | ⬜ | 🟨 | ✅ | ⬜ | ⬜ | ✅ | EM (Sales Analysis; Net-Profit Enterprise), SH (dashboard + activity chart); **TQ 🟨** = "Reporting and Analytics" + "Odoo native sales analysis" claims + payout records, **no reporting dashboard demonstrated**. *Impl.:* operational + financial reporting. |

## 9. Maintenance, trust & UX

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Release notes / maintenance | 🟨 | ⬜ | 🟨 | ✅ | ✅ | ⬜ | **VT = dated, mechanism-level changelog (best)**; EC = recent dated cadence; **EM stale on v19 path**; **TQ docs now readable but carry no dated changelog** (support policy = 60-day free bug-fix); **SH none on listing**. *Impl.:* publish a dated, honest changelog (trust signal). |
| Support / troubleshooting | ✅ | ✅ | ✅ | ✅ | 🟨 | 🟨 | WK (UV Desk), EM (Helpdesk + honest limitation docs), VT (priority support + FAQ); **TQ = documented Support Policy** (scope/exclusions/channels/required-info + 24h target) + FAQ. *Impl.:* ticketing + troubleshooting docs. |
| Ratings / adoption signal | 🟨 | 🟨 | ⬜ | ✅ | ⬜ | ⬜ | **TQ 83×5.0** (Apps listing, not re-fetched), **VT 300+ installs / 20 reviews**; **EC "no ratings"; SH none shown**. *Impl.:* social proof matters for evaluability. |
| Public docs + screenshots | ✅ | ✅ | ✅ | ✅(partial) | 🚫 | ✅(captions) | **EM & TQ best** (readable + real screenshots; **TQ now accessible — ~98 doc screenshots in step-by-step pages**); **EC none**. *Impl.:* readable, screenshot-rich, non-gated docs. |
| UX quality (inferred) | Med | Med–High/broad | High/expert | High | Low/unknown | High/broad | VT best diagnostics; EM best observability; **TQ = comprehensive + screenshot-rich but toggle-dense config, no metrics dashboard**; EC unknown (no shots). See `ux-ui-benchmark.md`. |

---

## How to read this matrix (caveats)

- **🟨 now dominates only the EC column** (a **screenshot-free listing**). *(Sprint C2:
  the **TQ column was rebaselined** from the now-accessible docs — most TQ cells are
  **✅ demonstrated**; the ones that stay 🟨/➖/⬜ are the reliability items the docs
  assert or omit rather than show: pHash 🟨, idempotency ➖, automatic-retry ⬜,
  cross-object reconciliation ⬜, rate-limit ⬜, HMAC ⬜, metrics dashboard ⬜,
  multi-company ⬜, customer export ⬜.)*
- **✅ now concentrates in EM, VT, and TQ** because they expose **real screenshots /
  dated release notes / step-by-step docs**. This reflects **evidence quality**, not
  necessarily a total capability ranking — and for TQ, **breadth is demonstrated while
  deep reliability/idempotency is only partly proven** (score the two separately).
- **Empty whitespace rows (rate-limit handling, automatic retry, first-class
  reconciliation, unified metrics dashboard) remain opportunities even after the TQ
  rebaseline** — TQ narrowed the **payout-reconciliation** whitespace (EM + TQ now
  demonstrate it, both Shopify-Payments-only) but did **not** close the correctness
  whitespace. Developed in [`gaps-opportunities.md`](./gaps-opportunities.md).
- **No cell implies a build decision.** MVP scope and architecture remain gated
  (`CLAUDE.md` §4–§5); the canonical taxonomy + matrix are finalized later
  (RB-12/RB-03) after ChatGPT review.

---

## Delta refresh — 2026-07-16 (Fable gap-closure mission)

Listing-level re-verification (pricing/versions/reviews and COD, fulfillment
modes, reconnect/backfill coverage) is captured in
[`../00-source-materials/competitor-refresh-2026-07-16.md`](../00-source-materials/competitor-refresh-2026-07-16.md).
Matrix symbols are unchanged; the refresh adds no demonstrated (✅)
capability upgrades — new capability statements are vendor claims (🟨)
pending screenshot-capable verification. COD: 🟨 EM (gateway-mapping only),
🟨 TQ (inference), 🟨 VT (claimed), 🟨 EC (journal mapping), 🟨 SH; ⬜ WK.
Backfill any-date: 🟨 VT, 🟨 EC/SH (date-range), ⬜ others. Inbound/3PL
fulfillment reconciliation: ⬜ across all six.
