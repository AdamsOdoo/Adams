# Common Patterns Across Competitors (Research Sprint C)

> What the six competitor connectors **commonly do** (and commonly skip), derived
> from [`competitor-deep-dives.md`](./competitor-deep-dives.md) and
> [`competitor-feature-matrix.md`](./competitor-feature-matrix.md). A pattern is
> "strongly common" only when **≥2 connectors demonstrate (✅)** it; "weakly
> evidenced" when it is mostly vendor-claimed (🟨). **Inference/recommendation
> only — no MVP/architecture decided** (`CLAUDE.md` §4–§5). Access date
> 2026-06-30. Connector keys: WK, TQ, EM, VT, EC, SH (see the matrix legend).

## Strongly common patterns (≥2 connectors demonstrate)

1. **Custom Shopify app + token/OAuth connection.** All six connect via a custom
   app; credentials are entered/authorized in Odoo. (WK✅, EM✅, VT✅, SH✅,
   **TQ✅** OAuth + token + Test Connection; EC🟨) — *grounded by Tier-1: OAuth/
   token-exchange is the Shopify model.*
2. **Broad core-object sync is a common market promise, but directionality varies
   by object and evidence strength.** Product/order/inventory/customer coverage is
   commonly claimed; true bidirectionality is **not consistently demonstrated**
   across all objects or all competitors. Examples: **ecommerce_shopify (EC)
   product export is not found**; **Webkul (WK) customer export is not found**;
   ***(Sprint C2)* Teqstars (TQ) now demonstrates controlled bidirectional
   *product* (import + draft-safe export/update) + bidirectional inventory/price/
   collections, but customer is import-only (customer export not found)**;
   **Emipro (EM) and VentorTech (VT) carry the strongest demonstrated directional
   evidence.** (all claim broad coverage; per-object directionality varies)
3. **Staging/queue before commit.** Inbound data is staged then processed:
   **EM Data Queues (125 products/50 orders)**, **SH Queue Dashboard**, **WK
   Feeds**, **VT background jobs**, **TQ per-op queues** (Product/Customer/Order/
   Return + Queue Batch Limit 100, **cron-processed**; framework not named). Only
   **EC** has no staging (cron + email). (EM✅, SH✅, WK✅, VT✅, **TQ✅**)
4. **Scheduled (cron) sync + manual on-demand sync** coexist everywhere. (all)
5. **SKU/barcode product matching + customer email matching** for
   dedup/linking. (EM✅, VT✅, **TQ✅** "Sync Listings Based On" SKU/Barcode/both +
   multi-field customer dedup; EC🟨, SH🟨, WK🟨)
6. **External-ID / Shopify-ID write-back** to link Odoo records to Shopify
   objects (idempotent upsert handle). (EM✅, SH✅ "Shopify ID write-back", VT✅,
   **TQ✅** Listing/Listing-Item binding to Shopify products/variants)
7. **Auto-workflow on order import** (confirm → invoice → deliver → register
   payment), configurable per payment gateway / financial status. (VT✅, SH✅,
   **TQ✅** (per gateway + financial status); EM🟨, EC🟨)
8. **Payment-gateway → Odoo journal mapping.** (SH✅, **TQ✅** (payout Transaction-
   type→Account + workflow per gateway); EM🟨)
9. **Fulfillment + tracking write-back Odoo→Shopify** on delivery validation.
   (EM✅, VT✅, SH✅, **TQ✅** (Update-in-Marketplace + click&collect pickup); EC🟨)
10. **In-app, reason-coded error logs** (mismatch/sync logs). (EM✅ Log Book,
    SH✅ Sync Logs, VT✅; WK✅ Feeds; **TQ✅ typed logs** (Queues‣Logs, ALL/SUCCESS/
    ERROR + per-record error messages — *not* a formal reason-code taxonomy)) —
    **EC is the outlier (email-only)**.
11. **Per-record / per-line failure isolation** (one bad record doesn't block the
    batch). (EM✅, SH✅, VT✅, **TQ✅** (per-op queue lines + Activity-on-failure))
12. **GraphQL Admin API** adoption/positioning. (VT✅ since v2.0.0; **TQ✅ (doc-
    stated** — sync/webhooks/refunds/cancel/payouts via GraphQL Admin API; a vendor
    doc statement, not independently verified wire); EC🟨, SH🟨, WK🟨) — *aligns
    with Tier-1: GraphQL is the primary API; new public apps GraphQL-only from
    2025-04.*

## Common but weakly evidenced patterns (mostly 🟨 claims)

- **"Real-time" sync** — claimed by WK/EC/SH but actually **cron/queue + optional
  webhook**; genuine webhook-driven near-real-time is demonstrated mainly by VT
  (and EM for website orders). *The "real-time" label is routinely overstated.*
- **Multi-location inventory** — claimed widely (EC🟨, SH🟨) but **demonstrated**
  by EM✅/VT✅ **and now TQ✅** (map locations; export combines multiple; third-party
  location excluded).
- **Retry/recovery** — claimed by most (WK🟨, EM🟨 manual, EC🟨, SH🟨 re-export,
  **TQ** queue re-processing + collection "retried next run" + manual re-run) but
  **automatic retry with a classified/backoff taxonomy is demonstrated only by
  VT✅** (TQ shows **no** automatic-retry taxonomy — verified ⬜).
- **Idempotency / duplicate prevention** — **duplicate prevention** is now
  demonstrated by EM✅/VT✅/**TQ✅** (SKU/barcode + multi-field customer dedup +
  Create-Odoo guard + webhook link-existing) and others key on SKU/email/ID; but
  **explicit idempotency is mechanized only by VT** (GraphQL `@idempotent`, Shopify
  2026-04). **TQ has only adjacent guards** (refund amount-match, already-cancelled)
  — **no explicit `@idempotent` directive on the docs (➖)**; the Sprint C snippet
  stays unverified.
- **Metafields, Markets, multi-company** — metafields + Markets/Catalogs now
  demonstrated by EM✅/VT✅/**TQ✅** (TQ: bidirectional Product/Variant metafields;
  Market/Company-Location/App catalogs with quantity + volume pricing). **Multi-
  company** stays demonstrated only by EM/VT (**TQ ⬜** — not distinguished from
  multi-store).

## Rare / differentiating patterns (1 connector, or scarce)

- **Automatic retry of safe operations after network/server errors** — VT only.
- **GraphQL idempotency directives (Shopify 2026-04)** — VT (explicit); **TQ has
  no explicit directive on the docs** (adjacent guards only; the Sprint C snippet
  stays unverified).
- **Real async job queue (OCA `queue_job`)** — VT only (others use `ir.cron`
  batches/staging tables).
- **Traffic-light webhook health with a named cause** — VT only.
- **Dry-run / Preview-Report before export** — VT only (catalogs).
- **Payout reconciliation (Shopify Payments → bank statement)** — EM **and now
  TQ✅** demonstrated (both **Shopify-Payments-only**; TQ adds Auto/Manual Reconcile
  + reason-coded per-line warnings). No longer single-competitor.
- **Gift cards** (import/export/disable) — SH only (demonstrated).
- **Abandoned-checkout → CRM lead recovery / product recommendations / Buy-with-
  Prime** — SH only.
- **B2B mode (company detection + VAT/VIES validation)** — VT only.
- **Daily activity time-series chart** — SH only.
- **CSV/XLSX product-mapping fallback** — EM only.
- **Net-Profit / analytic-account-per-channel reporting** — EM only.
- **Custom Python field-transform mapping + test-against-live-data** — VT only.

## Patterns that appear MISSING across competitors (whitespace)

- **Named Shopify rate-limit / GraphQL-cost-aware throttling** — **none** of the
  six describes a rate-limit/backoff strategy (VT closest: "avoid unnecessary API
  requests"). *Tier-1 says this matters (leaky-bucket REST; calculated-cost
  GraphQL).* **Clear whitespace.**
- **User-visible reconciliation runs** — reconciliation is mostly implicit
  (manual re-import to recover missed webhooks); no competitor surfaces a
  first-class "reconcile now / last reconciled" control. *Tier-1 mandates
  reconciliation (delivery not guaranteed).*
- **A unified command center** that fuses connection health + queue status +
  activity timeline + quick actions — SH and VT each have half; none has all.
- **Effortless install + real reliability together** — VT has the reliability but
  a heavy install; the easy-install products lack the reliability.
- **Honest latency labelling** — most overstate "real-time".
- **Connector-specific permission/record-rule model** documented — only EM/SH
  show access control; most don't detail it.
- **Webhook HMAC verification** described — only VT claims HMAC-SHA256; *Tier-1
  requires HMAC verification on raw body.* Under-addressed across the field.

## Common UX patterns

- Tab/section-segmented configuration (WK, SH); **toggle-dense** config screens
  (EM, SH, WK).
- **Stage → inspect → process → verify (open record) → log** confidence loop
  (EM, SH; WK via Feeds).
- Per-object **import wizards with filters** (all/ID/date-range) (WK, EM, SH).
- Status surfaced via **counts/queues** (EM, SH) or a **pipeline/traffic-light**
  (VT).
- **Jargon-heavy labels** with uncertain inline help (WK, EM).

## Common reliability patterns

- **Queue/staging + per-record isolation + in-app logs** (EM, SH, VT, WK, **TQ**).
- **Manual recovery** as the default (re-run / re-evaluate / re-import / re-export)
  — automatic retry is the exception (VT); **TQ** relies on queue re-processing +
  manual re-run (no automatic-retry taxonomy).
- **Keying for dedup**: SKU/barcode (products), email/multi-field (customers),
  Shopify-ID / Listing binding (linking). (EM, VT, SH, **TQ**)
- **Missed-webhook recovery via manual import** (EM explicit; **TQ** via
  incremental Last-Processed cursors + per-return Resync + re-import) — but
  reconciliation is **not** a first-class, scheduled, user-visible job anywhere
  (**TQ confirms this gap** — no missed-record reconciliation surface).

## Common configuration patterns

- Per-instance configuration record holding credentials + sync toggles.
- **Quantity-field choice** (Forecast / Free-to-Use / On-Hand) (EM, VT, WK, **TQ** "Stock Based On").
- **Per-gateway / per-financial-status workflow** mapping (EM, SH, **TQ** — now demonstrated).
- **Per-location** (warehouse↔Shopify location) mapping (EM, VT, **TQ** — with third-party-location exclusion).
- **Scheduler per process** with intervals (EM, WK, **TQ** "Automatic Jobs"); EC uses fixed 10-min crons.
- **Access-right gating** of connector settings (SH; EM via user rights).

## Common support / documentation patterns

- Ticket/helpdesk support (WK UV Desk, EM Helpdesk, VT/SH/TQ portals/email).
- **Documentation quality varies widely:** EM (rich, screenshot-heavy, honest
  about limits), VT (dated release notes + Confluence KB), **and now TQ** (~98
  screenshots in step-by-step pages + a documented Support Policy) lead; **EC has
  no screenshots and a sign-in-gated setup guide**, **SH has no dated changelog/
  ratings**. *(Sprint C2: TQ docs are no longer bot-blocked; TQ still lacks a
  **dated changelog**.)*
- **On-page pricing on Apps/marketplace** is standard (TQ $326.20, EC $195.56,
  SH $168.81, VT $569.16/€499, WK $170); **EM shows no price in its docs**.
- **Dated changelogs** present for VT (best) and EC; **stale on EM's v19 path**;
  **absent for SH**; **unreadable for TQ**.

## Implications for our connector (inference — gated)

1. **Match the demonstrated baseline** (custom-app connect, bidirectional
   product/order/inventory/customer, staging/queue, scheduled+manual sync,
   reason-coded logs, SKU/email/ID-write-back dedup, auto-workflow, fulfillment
   write-back) — anything less is below market.
2. **Win on the whitespace** the market misses: **named rate-limit/cost-aware
   throttling**, **first-class user-visible reconciliation**, **automatic retry +
   idempotency by default**, **HMAC verification**, **a unified command center**,
   **honest latency**, and **effortless install with real reliability**.
3. **Adopt the rare/differentiating bests** where they fit (VT's idempotency/retry/
   diagnostics, EM's observability/payouts, SH's monitoring/breadth) — see
   [`best-in-class-observations.md`](./best-in-class-observations.md).
4. **These patterns inform — do not decide — the open architecture questions**
   (AR-002 API strategy: GraphQL convergence; AR-003 sync orchestration: webhooks
   + cron + queue is the market pattern, VT validates `queue_job`; AR-005 binding:
   SKU/email/ID-write-back; AR-006 idempotency: VT ships `@idempotent`). All
   remain **evidence-pending** in
   [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
