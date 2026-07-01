# Competitor Feature Matrix (Research Sprint C — first research matrix)

> **First research matrix, not a final MVP or feature taxonomy.** Rows = feature
> areas; columns = the six competitor connectors. Every non-empty cell is backed
> by a citation in
> [`competitor-deep-dives.md`](./competitor-deep-dives.md) /
> [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md)
> (access date **2026-06-30**). This consolidates competitor evidence only; it
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
> **TQ** — the Teqstars **docs are 403-blocked**; TQ cells are **listing
> claims** (`apps.odoo.com/.../shopify`), so 🟨 means "claimed on the Apps
> listing", never demonstrated. **EC** — listing has **no screenshots**, so all
> EC capability cells are 🟨 vendor claims (cron-based). **SH** — cells marked ✅
> rest on a **captioned walkthrough** (pixels not inspected) and **no ratings/
> changelog** corroborate them. **EM/VT** carry the most demonstrated (✅)
> evidence (real screenshots / dated release notes).

---

## 1. Setup, connection & configuration

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Store / instance connection | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | All connect via a custom Shopify app. **VT** uses OAuth (no manual tokens); WK/EM/SH paste credentials. *Impl.:* offer **OAuth-first**, low-friction connect. |
| Credential / auth flow | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | EM warns a **trailing-slash URL mismatch fails auth** (good honesty). VT masks credentials. *Impl.:* validate credentials inline; mask secrets. |
| Test connection | ✅ | 🟨 | ⬜ | 🟨 | ⬜ | ✅ | WK has an explicit **Test Connection**; VT runs a connection test + scope check; SH verifies via Sync Logs. *Impl.:* explicit pass/fail connection test. |
| Dashboard / command center | 🟨 | 🟨 | 🟨 | 🟨 | ⬜ | ✅ | **SH** = strongest (Integration Dashboard + **daily activity chart**); TQ claims two dashboards; VT has an auto-workflow "visual pipeline" (no dedicated dashboard); EC has none. *Impl.:* a real monitoring dashboard differentiates. |
| Configuration / settings IA | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | WK tab-segments (Basic/Sales/Product); EM/SH are config-dense (many toggles). *Impl.:* group config, add inline help, avoid overwhelming. |

## 2. Catalog: products, variants, media, pricing

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Product import | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | EM: Create/Update date ranges + "don't update existing" + draft import. *Impl.:* incremental, filterable imports. |
| Product export (Odoo→Shopify) | ✅ | 🟨 | ✅ | ✅ | ⬜ | ✅ | **EC export direction unstated** (only Shopify→Odoo). VT exports as **draft for review**. *Impl.:* bidirectional + draft-first export. |
| Variants / options | ⬜ | 🟨 | ✅ | ✅ | 🟨 | 🟨 | VT fixed a **250-variant import cap** (v2.1.4); relevant to Tier-1 2048-variant model. **WK: not found.** *Impl.:* support the 2048-variant model. |
| Images / media | ⬜ | 🟨 | ✅ | ✅ | 🟨 | 🟨 | TQ claims **pHash dedup**; EM imports + Odoo-side update; VT bidirectional (disableable). **WK: not found.** *Impl.:* media sync with dedup. |
| Price lists / pricing | 🟨 | 🟨 | ✅ | ✅ | ⬜ | ⬜ | EM: Pricelist + **Compare-At Pricelist**; VT: pricelists + **per-market via Catalogs**. *Impl.:* pricelist + compare-at + per-market. |
| Publish / unpublish | ⬜ | 🟨 | ✅ | ✅ | ⬜ | ✅ | EM (Web/Web+POS, "Shopify Unpublish"); SH (via sales-channel membership). *Impl.:* channel-based publish control. |

## 3. Inventory & locations

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Inventory sync | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | "Real-time" is **overstated** by WK/EC/SH (actually cron/queue). VT does real-time-on-stock-move **or** scheduled. *Impl.:* be honest about latency; reconcile. |
| Stock quantity-field choice | ✅ | ⬜ | ✅ | ✅ | ⬜ | ⬜ | EM (Forecast vs Free-to-Use, with formulas), VT (Free/On-Hand/Forecasted), WK (on-hand/forecasted). *Impl.:* let users pick the source quantity. |
| Multi-location | ⬜ | 🟨 | ✅ | ✅ | 🟨 | 🟨 | **EM/VT demonstrated** (locations↔warehouses; VT "External Location" grid + default fallback). **WK single location only.** *Impl.:* multi-location is table-stakes; map per-location (Tier-1: write per `inventory_item_id`+`location_id`). |
| Import stock | ⬜ | 🟨 | ✅ | ✅ | 🟨 | ✅ | EM creates an **Inventory Adjustment to process manually** (friction). *Impl.:* auto-apply imported stock. |

## 4. Customers & addresses

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Customer import | 🟨 | 🟨 | ✅ | ✅ | 🟨 | ✅ | VT documents the **Basic-plan "no PII" limitation** honestly (default-customer fallback). *Impl.:* handle PII-gated plans gracefully. |
| Customer export | ⬜ | 🟨 | ✅ | ➖ | ⬜ | ✅ | **EM: email-dedup links instead of duplicating** (best-practice). **WK/EC: import only.** *Impl.:* dedupe-by-email on export. |
| Address handling | ⬜ | 🟨 | ➖ | ➖ | 🟨 | ➖ | Mostly implied via contact fields; no deep multi-address mapping shown. *Impl.:* explicit billing/shipping mapping + country/state matching. |
| Customer dedup / matching | 🟨 | 🟨 | ✅ | ✅ | 🟨 | 🟨 | **VT**: match by email/name/phone (normalized) before create; **EM**: email link. *Impl.:* multi-key normalized matching. |

## 5. Orders, payments, refunds, fulfillment

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Order import | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | VT: **real-time via webhook "within seconds"**; EM: manual/scheduler/webhook (webhook = website orders only). *Impl.:* webhook + scheduled backfill. |
| Order status mapping | 🟨 | 🟨 | 🟨 | ✅ | 🟨 | ✅ | SH **Payment Gateway Workflow Matrix** routes per gateway; EM per gateway+financial status. *Impl.:* configurable status/workflow mapping. |
| Invoice creation | ⬜ | 🟨 | 🟨 | ✅ | 🟨 | ✅ | Driven by an **auto-workflow** (VT "up to 5 steps"; SH auto-create invoice/validate/register). *Impl.:* rule-based auto-workflow. |
| Payment handling | ⬜ | 🟨 | ➖ | ✅ | 🟨 | ✅ | TQ/SH map **gateway→Odoo journal**; VT applies Shopify payments to invoices + currency conversion. *Impl.:* gateway→journal mapping. |
| Payout reconciliation | ⬜ | 🟨 | ✅ | ⬜ | ⬜ | ⬜ | **Only EM demonstrates** (Shopify-Payments-only → Bank Statement → reconcile); TQ claims Enterprise auto-reconcile. *Impl.:* **whitespace** — robust payout reconciliation is rare. |
| Refunds / returns / cancellations | ⬜ | 🟨 | ✅ | ✅ | 🟨 | ✅ | EM/VT/SH demonstrate refunds + cancellations (credit notes). EM returns conditional (invoice-exists, restock, fulfilled-only). VT GraphQL refund **idempotency**. *Impl.:* idempotent refunds; conditional returns. |
| Fulfillment / tracking export | 🟨 | 🟨 | ✅ | ✅ | 🟨 | ✅ | EM **Put-in-Pack multi-package**; VT carrier tracking; SH fulfillment-ID write-back. WK: "shipping-method import **not available**". *Impl.:* FulfillmentOrder-based (Tier-1), multi-package, tracking write-back. |

## 6. Sync infrastructure

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Webhooks | ⬜ | 🟨 | ✅ | ✅ | 🚫 | ✅ | **EC has none (cron-poll only).** VT: 8 events + HMAC-SHA256 + dated hardening. EM: SSL required, behaviour toggles. *Impl.:* webhooks **+ reconciliation** (Tier-1: delivery not guaranteed). |
| Scheduled / cron sync | ✅ | 🟨 | ✅ | ✅ | ✅ | ✅ | EC = cron-only (orders 10 min). EM per-process scheduler + "Last Operation Details". *Impl.:* scheduled backfill alongside webhooks. |
| Manual sync | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | Universal (on-demand wizards). *Impl.:* always offer manual run. |
| Queue / job processing | ⬜ | 🟨 | ✅ | ✅ | ⬜ | ✅ | **VT = real async job queue (`queue_job`)**; EM = batch Data Queues (125/50 per queue); SH = Queue Dashboard Framework. **WK = Feeds staging; EC = none.** *Impl.:* a real job/queue layer (Tier-1: Odoo core has only `ir.cron`; `queue_job` is community → architecture question AR-003). |

## 7. Reliability & observability

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Logs (audit / sync history) | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | **EM Log Book/Mismatch Log (reason-coded)**, SH Sync/Export Logs, VT "every action logged". **EC email-only.** *Impl.:* in-app, reason-coded logs. |
| Error handling | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | EM isolates Failed/Cancelled queue lines; VT batches valid records despite errors. *Impl.:* per-record isolation. |
| Retry / recovery | 🟨 | 🟨 | 🟨 | ✅ | 🟨 | ✅ | **Only VT = automatic retry** (safe ops after network/server errors); EM/SH = manual re-run / re-export flag. *Impl.:* automatic retry/backoff is a differentiator. |
| Duplicate prevention / idempotency | 🟨 | 🟨 | ✅ | ✅ | 🟨 | 🟨 | **VT = explicit GraphQL idempotency directives (Shopify 2026-04)**; EM = email/SKU + re-export block; TQ claims idempotency (unverifiable). *Impl.:* `@idempotent` writes + binding keys (AR-005/AR-006). |
| Webhook reconciliation | ⬜ | 🟨 | ✅ | ✅ | ⬜ | 🟨 | EM provides **manual import to recover missed webhooks**; VT traffic-light health + dated fixes. *Impl.:* reconciliation job is mandatory, not optional (Tier-1). |
| Rate-limit / throttle handling | ⬜ | ⬜ | ⬜ | 🟨 | ⬜ | ⬜ | **No competitor names a rate-limit/cost strategy** (VT closest: "avoid unnecessary API requests"). *Impl.:* **clear whitespace** — GraphQL cost-aware throttling. |
| Permissions / security model | ⬜ | ⬜ | ✅ | ➖ | ⬜ | ✅ | **EM** (Odoo user rights + explicit Shopify scopes) and **SH** (granular access-rights groups) lead. *Impl.:* ship `ir.model.access.csv` + groups + record rules (Tier-1). |

## 8. Advanced / breadth

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Mappings (field / gateway / location) | ✅ | 🟨 | ✅ | ✅ | 🟨 | ✅ | **VT** = per-field directional + **custom Python transforms + test-against-live-data** (most advanced). *Impl.:* configurable, testable mappings. |
| Multi-store | ⬜ | 🟨 | ➖ | ✅ | ⬜ | 🟨 | VT "as many stores as you want"; TQ "unlimited"; *Impl.:* multi-store with per-store config. |
| Multi-company | ➖ | ⬜ | ✅ | ✅ | ⬜ | ⬜ | **WK shows a default Company field only; true multi-company support is not demonstrated.** Demonstrated multi-company evidence = EM (via Markets per-market company) and VT (multi-company inventory). **SH multi-company unverified.** *Impl.:* multi-company isolation via record rules. |
| Shopify Markets | ⬜ | 🟨 | ✅ | ✅ | ⬜ | ⬜ | **EM/VT** demonstrate Markets & Catalogs (per-market pricing/company). *Impl.:* Markets is a premium differentiator. |
| Metafields | ⬜ | 🟨 | ✅ | ✅ | ⬜ | ✅ | EM/VT/SH = directional mapping; VT "30+ types". *Impl.:* directional metafield mapping. |
| Gift cards | ⬜ | 🟨 | 🟨 | ⬜ | ⬜ | ✅ | **Only SH demonstrates** (import/export/disable-in-Shopify). *Impl.:* niche but a breadth differentiator. |
| POS | ⬜ | 🟨 | 🟨 | ➖ | ⬜ | ⬜ | TQ/EM claim POS order import; VT via "Closed" status. *Impl.:* POS-order import (Tier-1 order topics). |
| B2B | ⬜ | 🟨 | ⬜ | ✅ | ⬜ | ⬜ | **Only VT** (company detection, VAT/VIES validation). *Impl.:* B2B is differentiating whitespace. |
| Abandoned checkout / recommendations / Buy-with-Prime | ⬜ | ⬜ | ➖ | ⬜ | ⬜ | ✅ | **SH-unique breadth** (abandoned-checkout→CRM, recommendations, Buy-with-Prime). *Impl.:* optional add-on candidates. |
| Reporting / analytics | ⬜ | 🟨 | ✅ | ⬜ | ⬜ | ✅ | EM (Sales Analysis; Net-Profit Enterprise), SH (dashboard + activity chart), TQ (Analytics dashboard claim). *Impl.:* operational + financial reporting. |

## 9. Maintenance, trust & UX

| Feature area | WK | TQ | EM | VT | EC | SH | Evidence note / implication |
| --- | :--: | :--: | :--: | :--: | :--: | :--: | --- |
| Release notes / maintenance | 🟨 | 🔒 | 🟨 | ✅ | ✅ | ⬜ | **VT = dated, mechanism-level changelog (best)**; EC = recent dated cadence; **EM stale on v19 path**; **TQ docs blocked**; **SH none on listing**. *Impl.:* publish a dated, honest changelog (trust signal). |
| Support / troubleshooting | ✅ | 🟨 | ✅ | ✅ | 🟨 | 🟨 | WK (UV Desk), EM (Helpdesk + honest limitation docs), VT (priority support + FAQ). *Impl.:* ticketing + troubleshooting docs. |
| Ratings / adoption signal | 🟨 | 🟨 | ⬜ | ✅ | ⬜ | ⬜ | **TQ 83×5.0**, **VT 300+ installs / 20 reviews**; **EC "no ratings"; SH none shown**. *Impl.:* social proof matters for evaluability. |
| Public docs + screenshots | ✅ | 🔒 | ✅ | ✅(partial) | 🚫 | ✅(captions) | **EM best** (readable + real screenshots); **TQ blocked**; **EC none**. *Impl.:* readable, screenshot-rich, non-gated docs. |
| UX quality (inferred) | Med | 🔒 | High/expert | High | Low/unknown | High/broad | VT best diagnostics; EM best observability (expert-heavy); EC unknown (no shots). See `ux-ui-benchmark.md`. |

---

## How to read this matrix (caveats)

- **🟨 dominates the TQ and EC columns** because their evidence is, respectively,
  a **blocked docs site** (TQ — Apps-listing claims only) and a **screenshot-free
  listing** (EC). Their real capabilities may be higher or lower than claimed.
- **✅ concentrates in EM and VT** because they expose **real screenshots /
  dated release notes**. This reflects **evidence quality**, not necessarily a
  total capability ranking.
- **Empty whitespace columns (rate-limit handling, payout reconciliation, B2B,
  automatic retry) are opportunities**, developed in
  [`gaps-opportunities.md`](./gaps-opportunities.md).
- **No cell implies a build decision.** MVP scope and architecture remain gated
  (`CLAUDE.md` §4–§5); the canonical taxonomy + matrix are finalized later
  (RB-12/RB-03) after ChatGPT review.
