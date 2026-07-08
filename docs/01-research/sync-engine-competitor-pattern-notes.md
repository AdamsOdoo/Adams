# Sync Engine Competitor / Common Pattern Notes

> **Task 006A-4.** Externally visible competitor/common connector **sync
> behaviour** only — manual sync, scheduled sync, import/export flow, failed-sync
> handling, queue/log screens, retry, error visibility, webhook use, duplicate
> prevention, mapping/configuration screens. Access date for the underlying
> evidence is **2026-06-30** (Sprint C) and **2026-07-01** (Sprint C2, Teqstars
> rebaseline); this synthesis document was assembled **2026-07-08**.

## Scope

This file is **external pattern research only**. It is **not** an architecture
decision, **not** a DEC, **not** an implementation-scope document, and **not**
an authorization to build anything. It groups already-gathered, cited,
claim-classified competitor evidence through a **sync-engine-specific lens**
(the cross-cutting mechanics of how data moves — sync triggers, queues, retries,
logs, dedup — rather than full feature breadth). No claim here overrides
`CLAUDE.md` §4–§5 (research-first, no-code gate) or §8 (claim classification).
Nothing in this file infers hidden implementation internals from marketing
text; it records only what each vendor's own pages/screenshots/docs show or
state (see "Dangerous assumptions to avoid" below).

### Why no new web fan-out was run this session

Per the task's own source-priority rule ("use existing repository competitor
research first if available, then current public competitor/vendor docs/pages
only where accessible") and `CLAUDE.md`'s high-power-mode guardrail ("for
small patch/revision sessions, do not launch large fan-out; use the minimum
research needed"), this session did **not** re-fetch the competitor sources.
Reasoning:

- All six named targets (Webkul, Teqstars, Emipro, VentorTech, `ecommerce_shopify`,
  `sh_shopify_connector`) were already researched in a dedicated, high-power,
  cited, claim-classified sprint (Research Sprint C, 2026-06-30, plus a Sprint C2
  rebaseline of Teqstars on 2026-07-01) — see
  [`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md),
  [`competitor-deep-dives.md`](./competitor-deep-dives.md),
  [`competitor-feature-matrix.md`](./competitor-feature-matrix.md),
  [`common-patterns.md`](./common-patterns.md),
  [`avoid-list.md`](./avoid-list.md),
  [`gaps-opportunities.md`](./gaps-opportunities.md),
  [`best-in-class-observations.md`](./best-in-class-observations.md), and
  [`../00-source-materials/competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md).
- That sprint already went through a **capture → adversarial-verify** pass per
  source (claims were actively downgraded where a workflow wasn't actually
  shown — e.g. Teqstars pHash, automatic-retry, and dashboard claims). Re-fetching
  the same pages 8 days later, with no signal that anything sync-relevant
  changed, would duplicate that work rather than add value.
- This document's job is to **re-cut** that existing evidence into the
  sync-engine-specific taxonomy the task asks for (manual/scheduled/logs/
  retry/queue/import-export/webhook/dedup/mapping/multi-store/first-sync),
  which is a different organizing lens than the full-feature deep dives — that
  re-cut is the value-add of this session, not new fact-finding.
- No source status has changed for these six targets since the last check
  (all still recorded as of 2026-06-30/07-01 in the files above); this session
  performed no new HTTP fetches and therefore records no new access-date
  changes. If ChatGPT wants a fresh re-check of a specific vendor page (e.g. to
  catch a mid-week release), that is flagged as a next-step candidate in the
  Handoff section, not performed here.

Every claim below carries its **original** vendor citation (URL) plus the
**existing repo file** it was captured in, per the task's citation rule.

---

## Source inventory

| # | Vendor/source | URL / repo path | Access date | Accessible | Reliability | Sync-engine topics covered |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | Webkul — Odoo Multichannel Shopify Connector | `https://webkul.com/blog/odoo-multichannel-shopify-connector/` + `https://store.webkul.com/odoo-multichannel-shopify-connector.html` | 2026-06-30 | Yes | competitor self-claim (blog/store; screenshot-illustrated user guide) | manual sync, scheduled (cron) sync, import/export, staging queue ("Feeds"), error visibility, retry (re-evaluate), duplicate prevention, config screens |
| R2 | Teqstars — Shopify Connector for Odoo, docs 19.0 | `https://docs.teqstars.com/19.0/applications/shopify/` (31 pages) + Odoo Apps listing `https://apps.odoo.com/apps/modules/19.0/shopify` | Sprint C: 2026-06-30 (docs Blocked, listing only) / Sprint C2: 2026-07-01 (docs Accessible) | Yes (docs), Yes (listing) | repo research (docs = screenshot-backed step-by-step procedures); listing = marketplace listing | manual sync, scheduled ("Automatic Jobs"), webhooks, queue+logs, retry (partial), duplicate prevention, mapping/config screens, import/export direction |
| R3 | Emipro — Shopify Odoo Connector docs v19 | `https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/...` (~35 pages) | 2026-06-30 | Yes | repo research (static doc site, screenshot-heavy) | manual sync, scheduled sync, webhooks, Data Queues, Log Book/Mismatch Log, retry (manual), duplicate prevention, mapping/config screens |
| R4 | VentorTech — Shopify documentation (Confluence) | `https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify` (11 of 28 child articles read) | 2026-06-30 | Partial (anonymous-access banner; 17 of 28 child articles not fetched) | repo research (Confluence KB, partial) | webhooks (health/traffic-light), multi-location, historical-order cut-off (first-sync-adjacent), fulfillment, cancel flow |
| R5 | Project Google Doc ("E-commerce user documentation") | `https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit` | 2026-06-30 | **No** — Blocked (Google sign-in wall; only the title is exposed) | unavailable | none (body inaccessible; inferred to be the `ecommerce_shopify` setup guide via a 301 redirect, not confirmed) |
| R6 | Odoo Apps — `ecommerce_shopify` (19.0) | `https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify` | 2026-06-30 | Yes (listing); "Get Started" guide → R5, Blocked | marketplace listing (no screenshots) | scheduled (cron) sync, error notification (email), retry claim, duplicate prevention claim, import/export direction |
| R7 | VentorTech — Odoo Shopify Connector PRO (marketing + ecosystem + Apps Store + release notes) | `https://ventor.tech/solutions/odoo-shopify-connector/` + ecosystem/shop pages + `https://apps.odoo.com/apps/modules/19.0/integration_shopify` + dated release-notes page | 2026-06-30 | Yes | competitor self-claim (marketing/ecosystem) + on-page fact (Apps Store, dated release notes) | webhooks, background job queue, scheduled + manual + real-time sync, retry/idempotency, mapping/config, import/export direction |
| R8 | Odoo Apps — `sh_shopify_connector` (19.0) | `https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector` | 2026-06-30 | Yes (flagship vendor product page 404'd) | marketplace listing (~29 captioned screenshot groups) | manual sync, scheduled sync, webhooks, Queue Dashboard Framework, Sync/Export Logs, retry (re-export flag), duplicate prevention (ID write-back), mapping/config screens |

All eight rows above are **existing repository research**, reused per the
task's stated source priority. Full per-claim citations (exact quotes, page
paths, screenshot alt-text) live in the linked files, primarily
[`../00-source-materials/competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md).
No new vendor pages were fetched in this session.

---

## Externally visible sync patterns

Competitor key: **WK**=Webkul(R1) · **TQ**=Teqstars(R2) · **EM**=Emipro(R3) ·
**VT**=VentorTech(R4+R7) · **EC**=`ecommerce_shopify`(R6) · **SH**=`sh_shopify_connector`(R8).
Claim-class tags follow the existing repo convention: **✅** demonstrated
(step-by-step flow/screenshot) · **🟨** vendor claim only · **➖** implied ·
**⬜** not found · **🚫** explicitly absent.

### Manual sync

- All six connectors document an **on-demand manual sync/run action** — WK✅
  (Operations wizards), TQ✅ ("Operations" popup per object + single-record
  "Sync to Odoo/Shopify"), EM✅ (Perform Operation), VT✅, EC🟨 (date-range
  fetch button, gated under Developer Mode), SH✅ ("Process Queues Manually").
  — [`competitor-feature-matrix.md`](./competitor-feature-matrix.md) §6.

### Scheduled sync

- All six document **scheduled/cron sync** coexisting with manual sync. WK✅
  exposes raw `ir.cron`-style fields (Model, Scheduler User, Next Execution
  Date) directly to end users. TQ✅ has per-operation "Automatic Jobs". EM✅ has
  a per-process scheduler + "Last Operation Details". EC✅-described (its own
  listing states fixed cadences: "Orders — every 10 minutes; Pickings — every
  10 minutes; Inventory — right after order sync; Products/Location — initial
  manual"). — [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md)
  R1/R2/R3/R6; [`common-patterns.md`](./common-patterns.md) item 4.

### Logs / error handling

- **EM's Log Book / Mismatch Log** is the most-cited example: reason-coded
  failures ("SKU not found", "tax not found", "customer missing") surfaced in
  a queue with per-line Log Lines and a Draft/Failed/Cancelled/Done state
  model. — [`competitor-deep-dives.md`](./competitor-deep-dives.md) (Emipro
  section, "Reliability and robustness analysis").
- **TQ** documents log levels (ALL/SUCCESS/ERROR, default ERROR), per-op
  queues (Product/Customer/Order/Return), and "Activity-on-failure"
  (Responsible + due date) — but this is **typed logging, not a formal
  reason-code taxonomy** like Emipro's. — `.../setup/create_instance.html`,
  cited in [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md) R2.
- **SH** documents Sync Logs + Export Log history audit tables plus a "Daily
  Queue Activity Tracking" chart. — R8, same file.
- **WK** uses a "Feeds" staging area; bad records become "error feeds",
  described as fixable/re-evaluable without a developer. — R1, same file.
- **EC is the outlier**: failure handling is **email notifications only**, no
  in-app queue/log screen documented. — R6, same file;
  [`avoid-list.md`](./avoid-list.md) item A-LOG-1.

### Retry / recovery

- **VT is the only connector that documents automatic retry**: "automatic
  retry of safe operations after network/server errors" (v1.13.0 release
  note), plus "Run Now" on stuck jobs and "Failed Job Notifications". — dated
  release notes, [`competitor-deep-dives.md`](./competitor-deep-dives.md)
  (VentorTech section).
- **EM, WK, EC, SH** document **manual-only recovery**: re-run a queue line,
  re-evaluate an error feed, re-export, or a "Needs Shopify Re-Export" flag
  (SH) that a user or a scheduled action clears. — same file, respective
  sections.
- **TQ** documents queue re-processing plus a collection-sync job that is
  "retried in the next run" automatically for that one operation, and manual
  re-run elsewhere — but **no general automatic-retry/backoff taxonomy** is
  shown; this was an explicit **verification downgrade** in the source sprint
  (a Sprint-C search-snippet claim of "idempotency directives... preventing
  duplicate inventory changes and double refunds when retrying" was **not**
  confirmed on the now-accessible docs and is recorded as unverified). —
  [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md)
  R2 Sprint C2 section, line "Idempotency ➖ / automatic-retry ⬜...".

### Queue / background-processing claims

- **EM** — "Batch Data Queues": documented batch sizes ("125 products… 50
  orders per queue"), Draft/Failed/Cancelled/Done states, "Process Queue
  Manually", an irreversible "Force Done" action. — `.../queue.html`,
  [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md) R3.
- **SH** — "Queue Dashboard Framework": separate Contact/Product/Order/
  Checkout/Recommendation queues with draft/completed/failed counts and a
  "Daily Queue Activity Tracking" chart. — R8, same file.
- **TQ** — per-operation queues (Product/Customer/Order/Return) with a
  configurable "Queue Batch Limit" (documented default 100). — `.../setup/create_instance.html`.
- **VT** — the only connector whose docs name an actual **background job
  queue dependency**: OCA `queue_job` (`server_wide_modules`, `queue_job
  channels root:1`, ≥2 workers required in `odoo.conf`). This is a **documented
  installation prerequisite**, not just a sync-behaviour claim. —
  [`competitor-deep-dives.md`](./competitor-deep-dives.md) (VentorTech,
  "Workflow reconstruction: Install").
- **WK** — no job queue; uses "Feeds" staging instead. **EC** — no queue/job
  screen documented at all (cron + email only). —
  [`competitor-feature-matrix.md`](./competitor-feature-matrix.md) §6 row
  "Queue / job processing".

### Import/export direction

- Product **import** is demonstrated by all six. Product **export**
  (Odoo→Shopify) is demonstrated by WK✅, TQ✅ (draft-safe: "If left empty, the
  listing will still be exported to Shopify but will not be published to any
  channel" — `.../product_management/product_export.html`), EM✅, VT✅
  (draft-for-review), SH✅ — but **EC's export direction is unstated** on its
  listing (its own automation section only describes Shopify→Odoo order/
  inventory flow). — [`competitor-feature-matrix.md`](./competitor-feature-matrix.md) §2.
- Customer **export**: EM✅ (email-dedup link-not-duplicate) and SH✅
  demonstrate it; **WK, TQ, EC show import only** — TQ's docs explicitly have
  **no customer-export page**, and customer metafields are documented as
  "import-only". — same file §4, and
  [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md) R2.

### Webhook claims

- **EC has none** — its own listing's automation section is cron-only (10-min
  orders/pickings); "no webhooks mentioned anywhere" was the sprint's explicit
  finding. — [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md) R6.
- **WK** documents no webhook mechanism on the pages read (absence noted as
  an inference from omission, not an explicit vendor denial). — R1, same file.
- **EM✅** documents webhooks for product/order/customer create-update-delete,
  requiring SSL, and states a Shopify retry figure of "19 retries over 48h" —
  flagged in our own research as an **outdated competitor-doc figure** (their
  own docs, not our claim) since Tier-1 current Shopify behaviour differs; not
  independently re-verified in this session. — `.../webhooks-configuration.html`, same file R3.
- **TQ✅** documents webhooks for product create/update/delete,
  `orders/create`, `order/updated`, `customer/create`, and a full `returns/*`
  lifecycle, explicitly stating "webhook processing runs in a background
  thread after Shopify calls your endpoint" (fast-ack pattern) — but **no HMAC
  /webhook-signature statement** is on the accessible pages (HTTPS required
  only). — `.../setup/create_instance.html`, same file R2.
- **VT✅** documents "8 webhook events" and states "Webhook security:
  HMAC-SHA256 signature check" (a vendor claim, not independently verified),
  plus a **traffic-light health indicator** (green/yellow/red) where yellow is
  captioned "callback URL mismatch — check `web.base.url`". — R4/R7, same file.
- **SH✅** documents webhooks configured Shopify-side for products/contacts/
  orders/fulfillment, captioned "Real time data update" (a vendor claim). — R8.

### Duplicate-prevention claims

- **WK🟨** — SKU + Barcode matching plus an "Avoid Duplicity (Default Code)"
  toggle (stated, not demonstrated end-to-end).
- **EM✅** — customer dedup by email (links instead of duplicating,
  demonstrated with screenshots); stored Shopify references block re-export
  ("order already exported").
- **TQ✅** — configurable product match key ("Sync Listings Based On":
  Barcode / SKU / Barcode-and-SKU) plus a documented multi-field customer
  search (Name/City/State/Country/Zip/Street/Street2/Email/Parent Id) "to
  avoid duplicating customer entries", and a webhook-triggered customer
  dedup that "avoids creating a duplicate and links the existing record".
- **VT✅** — customer dedup by email/name/phone before create (v1.13.0
  normalizes email/phone first).
- **SH🟨** — Shopify-ID write-back on export implies a linking mechanism; no
  explicit dedup-key statement found on the listing.
- **EC🟨** — "Automatic SKU-based product mapping" and "Avoid duplicate
  customer creation" are stated on the listing with no workflow shown.
- All citations: [`competitor-feature-matrix.md`](./competitor-feature-matrix.md)
  §4 ("Customer dedup / matching") and the per-vendor sections of
  [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md).

### Mapping / configuration screens

- **TQ✅** — a single tabbed "Create Instance" configuration form (Product/
  Stock/Orders/Payout/Customer/Metafield/Workflow/Webhook/Automatic-Jobs/
  Notification), documented across 15 screenshots; flagged in our own
  analysis as **toggle-dense** (10+ order-config toggles). — `.../setup/create_instance.html`.
- **WK✅** — tab-segmented config (Basic/Sales/Product settings).
- **EM✅** — dense, checkbox-rich configuration screens across many pages,
  plus a **CSV/XLSX product-mapping fallback** for non-SKU catalogs.
- **VT🟨/✅** — per-field directional mapping with **custom Python transforms**
  and "test field mappings against live data before applying" (a vendor
  claim on the Apps Store listing, not screenshot-demonstrated in the
  accessed material) plus a demonstrated Markets/Catalogs "Preview/Report"
  dry-run before sending prices (Confluence, R4).
- **SH✅** — tabbed config (Products/Contacts/Orders/Refunds/Gift Cards/
  Abandoned Checkouts/Recommendations) gated behind a documented Odoo access
  right ("Shopify Configuration Manager").
- Citations: [`competitor-screenshot-inventory.md`](../00-source-materials/competitor-screenshot-inventory.md)
  (WK-CONFIG, TQ-SETUP-INSTANCE groups);
  [`competitor-deep-dives.md`](./competitor-deep-dives.md) per-vendor "UX/UI analysis".

### Multi-store / multi-company hints

- **Multi-store** (multiple Shopify instances against one Odoo DB) is
  documented for TQ✅ (one connector "instance" per store), VT✅ ("as many
  Shopify stores as you want"), and claimed for SH🟨 ("multiple instances in
  one Odoo DB"); WK shows a single default Company field only.
- **Multi-company** is demonstrated for EM✅ (Shopify Markets map to
  per-market Company/Warehouse/Pricelist/Fiscal Position/Language) and VT✅
  (multi-company inventory with "correct company context", v2.1.3); **TQ has
  a Company field on its instance config but the docs do not distinguish
  multi-company from multi-store** (recorded as ⬜, not found, in the source
  sprint); **SH's multi-company claim was verification-downgraded to
  not-found** on re-fetch. — [`competitor-feature-matrix.md`](./competitor-feature-matrix.md)
  §8, rows "Multi-store" / "Multi-company".

### First-sync handling (if documented)

- **VT✅** documents a "unified Import Wizard" (v1.13.0 dated release note)
  that on initial setup imports products/variants/attributes/categories/
  payment methods/taxes/shipping/initial stock/languages, auto-maps by
  SKU/barcode, offers an optional historical-order backfill "from a chosen
  date", and runs a "validation test" that surfaces catalog issues before the
  live sync starts. — [`competitor-deep-dives.md`](./competitor-deep-dives.md)
  (VentorTech, "Workflow reconstruction").
- **TQ✅** documents a post-connect "Confirm" step that syncs locations, sales
  channels, and product categories as part of first-time setup, before
  regular sync operations are available. — `.../setup/create_instance.html`,
  [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md) R2.
- **VT (Confluence, R4)** documents a **historical-order cut-off date**:
  "Any order created before your cut-off date will never be imported" — a
  first-sync scoping control, not an automatic full-history backfill. —
  `pages/2106916865`, same file R4.
- **EC🟨** states its own automation is "Products/Location — initial manual"
  (i.e., the very first catalog/location sync is a manual step, distinct from
  its 10-minute recurring cron for orders). — same file R6.
- **EM** and **WK** do not document a distinct first-sync/onboarding-import
  step beyond their standard filtered import wizards (Create/Update date
  range, defaulting "From" to last execution) — no first-sync-specific
  behaviour beyond that was found on the accessed pages.

---

## What competitors appear to do well

*(Source-backed only — see citations. No inference beyond what is stated.)*

1. **Emipro's Log Book / Mismatch Log** — reason-coded, per-record failure
   visibility with isolated Draft/Failed/Cancelled/Done queue states. —
   [`best-in-class-observations.md`](./best-in-class-observations.md) "Best
   observed logs / error handling".
2. **VentorTech's traffic-light webhook health** with a named cause
   ("callback URL mismatch — check `web.base.url`") plus automatic retry of
   safe operations and a dated, transparent release-notes trail disclosing
   even CRITICAL bug fixes (a silent order-paging bug in v2.1.6, a timezone
   filter bug in v2.1.2). — same file, "Best observed logs / error handling"
   and "Best observed documentation".
3. **Teqstars' draft-safe, controlled product onboarding** — a configurable
   match key (SKU/Barcode/both), a "Create Odoo Products?" guard against
   accidental duplication, export that stays unpublished when no sales
   channel is set, and a per-listing Allowed/Not-Allowed-Sync toggle to
   exclude a record from all sync operations. —
   [`competitor-source-notes.md`](../00-source-materials/competitor-source-notes.md) R2 Sprint C2.
4. **Softhealer's monitoring dashboard** (activity chart + queue failure
   counts + a "Needs Shopify Re-Export" recovery flag) is the most visually
   instrumented operational surface in the set. —
   [`best-in-class-observations.md`](./best-in-class-observations.md) "Best
   observed UX/UI".
5. **Webkul's staged "Feeds" + error-feed model** gives non-developers a
   fixable inbound queue before anything commits. — same file, "Best observed
   setup / onboarding" (adjacent) and
   [`competitor-deep-dives.md`](./competitor-deep-dives.md) (Webkul, "What
   we can learn").

---

## Gaps/opportunities for our connector

*(Inference / recommendation — not a decision. Every item below is gated by
`CLAUDE.md` §4–§5; nothing here is authorized for build.)*

- **Recommendation** — a first-class, scheduled *and* on-demand
  reconciliation surface ("reconcile now / last reconciled / drift found") is
  not demonstrated by any of the six connectors; the closest is manual
  re-import to recover missed webhooks (Emipro) or per-return "Resync" +
  config-level "Fetch Webhook" (Teqstars) — neither is a general missed-record
  detector. — grounded in
  [`gaps-opportunities.md`](./gaps-opportunities.md) O-REL-1.
- **Recommendation** — automatic retry with a classified/backoff taxonomy is
  demonstrated only by VentorTech; the other five rely on manual re-run/
  re-evaluate/re-export. A retry taxonomy (which failures are safe to
  auto-retry vs which need a human) is real whitespace. — same file O-REL-3,
  [`avoid-list.md`](./avoid-list.md) A-RET-1.
- **Recommendation** — no competitor names a rate-limit/GraphQL-cost-aware
  throttling strategy; VentorTech's closest statement is "avoid unnecessary
  API requests". — same file O-REL-2, A-SYNC-5.
- **Recommendation** — honest, per-data-type latency labelling ("scheduled
  every N minutes" / "webhook-driven" / "last synced at ...") is missing
  everywhere; "real-time" is used loosely by Webkul, `ecommerce_shopify`, and
  `sh_shopify_connector` for what their own pages describe as cron/queue
  models. — same file O-UX-1, A-UX-1.
- **Recommendation** — no single connector combines an operational
  monitoring dashboard (Softhealer's strength) with diagnostic named-cause
  health indicators (VentorTech's strength) and reason-coded logs (Emipro's
  strength) in one place. — same file O-DASH-1.
- **Open question (not a recommendation)** — whether a documented HMAC
  webhook-signature check is something we should surface as a visible,
  user-facing status (only VentorTech claims HMAC-SHA256 at all, and it is a
  vendor claim, not demonstrated in the accessed material).

---

## Dangerous assumptions to avoid

*(Hidden internals that must NOT be inferred from any of the above —
marketing text and screenshots describe outward behaviour, not code.)*

- Do **not** assume a vendor's "GraphQL API" claim (Webkul, Teqstars,
  VentorTech, `ecommerce_shopify`, `sh_shopify_connector`) describes the
  actual wire protocol used for every operation — these are stated positioning
  claims, not independently verified network traces.
- Do **not** assume "webhook" claims imply guaranteed delivery, ordering, or
  idempotent processing on the vendor's side — none of the six documents
  webhook delivery guarantees, and our own Tier-1 baseline record (outside
  this file's scope) already treats Shopify webhook delivery as
  not-guaranteed.
- Do **not** assume "real-time" labels (Webkul, `ecommerce_shopify`,
  `sh_shopify_connector`) describe an actual event-driven architecture — in
  each case the vendor's own configuration/automation text describes a
  cron or queue-polling mechanism underneath.
- Do **not** assume Teqstars' or `sh_shopify_connector`'s "idempotency" /
  dedup wording implies a specific persisted idempotency-key mechanism —
  neither vendor's accessible pages state an explicit idempotency directive;
  only adjacent guards (amount-match, already-cancelled, ID write-back) are
  shown.
- Do **not** assume VentorTech's documented `queue_job` dependency, or any
  other vendor's "queue"/"Data Queue"/"Queue Dashboard" language, describes
  the same underlying job-processing implementation — each vendor names its
  own queue concept differently and no source-code detail was inspected by
  this research (docs/marketing only).
- Do **not** assume a vendor's stated Odoo version range, LOC count, or
  install-base numbers reflect current production reliability — these are
  on-page facts about the listing, not a code-quality signal.
- Do **not** promote any vendor's own comparison-table checkmark (e.g.
  Teqstars' "pHash — Exclusive ✓") to "demonstrated" status — a checkmark in
  a marketing comparison table is a claim, not a shown workflow, per the
  existing sprint's verification discipline.
- Do **not** treat any pattern in this file as validated against our own
  Tier-1 Shopify/Odoo technical facts — that comparison is out of scope for
  this document (see the official baselines in
  [`shopify-official-api-notes.md`](./shopify-official-api-notes.md) and
  [`odoo-official-architecture-notes.md`](./odoo-official-architecture-notes.md),
  not synthesized here).

---

## Evidence map

| Observed pattern | Competitor/source | Evidence quote/summary | Confidence | Implication for our sync engine | Caveat |
| --- | --- | --- | --- | --- | --- |
| Manual on-demand sync action | All six (WK/TQ/EM/VT/EC/SH) | Per-object "Perform Operation" / "Sync to Odoo" / "Process Queues Manually" buttons | High (✅ for 5 of 6; EC 🟨) | Manual trigger is table stakes | EC's manual trigger is gated under Developer Mode, not a first-class button |
| Scheduled cron sync | All six | WK exposes `ir.cron` fields directly; EC states fixed 10-min cadences | High | Scheduled sync is table stakes; raw cron internals should stay hidden from users | WK's UX approach (exposing cron fields) is a documented anti-pattern, not a pattern to copy |
| Staging/queue before commit | WK, EM, TQ, SH, VT | EM "125 products/50 orders per queue"; SH Queue Dashboard; WK Feeds; TQ per-op Queue Batch Limit 100 | High (✅) | A staged, inspectable queue is a strong reliability UX | EC has no staging at all (cron + email) |
| Reason-coded error logs | EM (Log Book), TQ (typed logs), SH (Sync/Export Logs) | "SKU not found", "tax not found" (EM); ALL/SUCCESS/ERROR levels (TQ) | High for EM (✅ reason-coded); Medium for TQ (typed, not reason-coded taxonomy) | In-app, reason-coded logs are a differentiator worth matching or beating | TQ's logging is real but not as granular as EM's; do not conflate the two |
| Automatic retry/backoff | VT only | "automatic retry of safe operations after network/server errors" (v1.13.0) | High (✅, dated release note) | Automatic retry is rare — a real whitespace opportunity | Only VT; all others manual-only |
| Real async job queue | VT only (`queue_job`) | `odoo.conf` prerequisites (`server_wide_modules`, `queue_job channels root:1`, ≥2 workers) | High (✅, install FAQ) | A real queue layer is a differentiator but not free (`queue_job` is OCA/community, not core) | Vendor-documented prerequisite; not independently verified as functioning |
| Webhook use | TQ, EM, VT, SH (✅) / WK, EC (⬜/🚫) | TQ: order/product/customer/returns webhooks + background-thread fast-ack; VT: 8 events + HMAC-SHA256 claim | High for presence; Low for HMAC (claim only) | Webhooks + a documented fast-ack pattern is common among richer connectors | EC explicitly has none; WK shows none on read pages (absence, not explicit denial) |
| Duplicate prevention (customer) | EM, TQ, VT (✅) | EM: email-dedup link-not-duplicate; TQ: multi-field search (Name/City/State/Country/Zip/Street/Street2/Email/Parent Id) | High (✅, screenshot/step-documented) | Multi-field, normalized dedup is the pattern to match | SH/EC/WK claims are 🟨, not demonstrated |
| Draft-safe/controlled product export | TQ (✅) | "If left empty, the listing will still be exported to Shopify but will not be published to any channel" | High (✅) | A safe-by-default export (unpublished until explicitly channeled) is a strong onboarding pattern | Specific to product export; not shown for other object types |
| First-sync/initial-import wizard | VT (✅), TQ (✅, partial) | VT: unified Import Wizard (v1.13.0) with validation test; TQ: post-connect "Confirm" syncs locations/channels/categories | Medium-High | A guided first-sync step (vs. relying on regular filtered import) reduces onboarding risk | Only VT documents a full initial-import wizard with validation; TQ's "Confirm" step is narrower (reference data only, not full catalog) |
| Multi-store support | TQ, VT (✅), SH (🟨) | TQ: one instance per store; VT: "as many Shopify stores as you want" | Medium (✅ TQ/VT; 🟨 SH) | Multi-store is common among the fuller-featured connectors | WK shows single-default-company only |
| "Real-time" latency claims | WK, EC, SH (🟨, downgraded) | EC automation section is cron-based (10 min) despite "real-time" marketing bullet | High confidence the label is **overstated** | Honest latency labelling is a trust opportunity | Do not repeat the same overstatement pattern |
| Idempotency directive | VT (✅, dated); TQ (➖, not confirmed) | VT release notes name "GraphQL idempotency directives" (v2.1.4/2.1.6); TQ Sprint-C search snippet re: idempotency was **not** found on the now-accessible docs | High for VT; Low/unconfirmed for TQ | An explicit idempotency mechanism is rare and a differentiator | The TQ snippet is explicitly flagged unverified in the source sprint — do not cite it as fact |

---

## Unsupported claims removed

The following claims were considered while assembling this document and are
**not** carried forward as demonstrated/reliable, consistent with the
verification downgrades already recorded in the source sprint:

- **Teqstars pHash image-dedup "Exclusive"** — a comparison-table checkmark
  plus a dependency list (`imagehash`, `PyWavelets`); no configured/executed
  workflow was ever shown. Kept as 🟨 vendor claim, not promoted to a
  demonstrated sync pattern.
- **Teqstars idempotency directive** — a Sprint-C search-index snippet
  claimed "idempotency directives for inventory and refund operations… when
  retrying"; this was actively checked against the now-accessible docs and
  **not found**. Removed from this document as a demonstrated pattern;
  recorded here only as a removed/unverified claim.
- **Teqstars automatic-retry/backoff taxonomy, cross-object reconciliation
  surface, rate-limit/cost throttling, HMAC verification, and metrics
  dashboard** — all four were proposed for upgrade during the source sprint's
  own adversarial verification pass and were **downgraded back to "not
  found"**. This document keeps them at ⬜/➖, not ✅.
- **`sh_shopify_connector` multi-company support** — claimed on an earlier
  read, downgraded to "not found" on re-fetch in the source sprint. Not
  carried forward as a demonstrated multi-company pattern here.
- **`ecommerce_shopify` "real-time stock updates from Odoo to Shopify"** —
  contradicted by the same listing's own automation section (cron-based,
  10-minute intervals); recorded only as an overstated marketing claim, not a
  sync-engine fact.
- **Emipro's "19 retries over 48h" webhook-retry figure** — this is the
  vendor's own (documented-as-outdated-elsewhere) number; it is recorded here
  only as "a claim on Emipro's docs", not adopted as a current fact about
  Shopify's platform behaviour, since verifying current Shopify retry
  behaviour is outside this document's competitor-pattern scope.
- **Any claim about internal code architecture, database schema, or specific
  API call sequences** for any of the six connectors — none was inferred;
  only outwardly visible screens, buttons, and vendor-stated behaviour are
  recorded (see "Dangerous assumptions to avoid").

---

## Handoff

- **Branch:** `claude/task-006a-competitor-sync-patterns-tijbp4` (created
  per the session's designated-branch requirement; based directly on
  `origin/Shopify-connector` at merge commit `9247fea3c36afdb761a82678f3e5e66e8ef42e87`,
  which includes PR #121 and PR #122).
- **Files changed:** `docs/01-research/sync-engine-competitor-pattern-notes.md`
  (new file, this document). No other file was created or modified in this
  session.
- **Top findings:**
  1. Every requested competitor already has externally visible manual +
     scheduled sync, and the market has converged on staging/queue-before-
     commit as the dominant reliability pattern (5 of 6 connectors).
  2. Automatic retry/backoff, a real async job queue, and named-cause health
     diagnostics are demonstrated by only **one** connector each (mostly
     VentorTech) — this is the clearest, most consistently evidenced
     whitespace across the set.
  3. "Real-time" labelling is routinely overstated relative to the vendor's
     own documented mechanism (cron/queue underneath); honest latency
     labelling is unclaimed territory.
  4. Teqstars presents the widest *demonstrated* sync-engine breadth
     (queues, logs, webhooks, draft-safe export, dedup) of the set, but its
     deeper reliability claims (idempotency, auto-retry, reconciliation,
     rate-limit, HMAC) are explicitly unconfirmed on its own accessible docs
     — breadth and reliability depth must be scored separately for this
     vendor.
- **Weak/uncertain areas:**
  - R4 (VentorTech Confluence) is only Partially read (11 of 28 child
    articles) — sync-relevant detail may exist in the 17 unread articles
    (e.g., order tags, taxes import, archived/draft products).
  - R5 (Google Doc, likely `ecommerce_shopify`'s setup guide) remains fully
    Blocked; its content is unknown and was not inferred.
  - No source in this set names a rate-limit/cost-throttling mechanism at
    all, so this document cannot report *any* competitor pattern there —
    only its absence.
  - This session performed no new HTTP fetches; if a vendor has changed its
    docs/site since 2026-06-30/07-01, that would not be reflected here.
- **Exact next step:** ChatGPT review of this file. No implementation, no
  architecture synthesis, and no DEC/architecture-review-log update should
  follow from this file directly — any of those require a separate,
  explicitly authorized session per `CLAUDE.md` §5/§9/§10.
