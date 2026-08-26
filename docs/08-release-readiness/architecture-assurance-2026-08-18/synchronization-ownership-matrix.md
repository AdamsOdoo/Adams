# Synchronization ownership matrix

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

This matrix records the code-level contract found in the checkout. “Near-real-
time” is deliberately not claimed: the inbound fallback today is polling and
reconciliation. Webhook columns are **not implemented** unless explicitly
marked otherwise.

## Contract vocabulary

- **Binding identity:** stable Shopify GID scoped to the Odoo store and company.
- **Snapshot/watermark:** stored remote identity, updated timestamp/cursor,
  expected connection generation or last-pushed value used to avoid blind
  replay.
- **Uncertain:** transport outcome may have occurred remotely; the attempt is
  reconciled by remote read before any replacement operation.
- **Unsupported:** the current product does not implement the requested
  direction/workflow; this must be shown to an operator, not inferred as a
  successful no-op.
- **Ambiguous:** code has a conservative path but the merchant-facing contract
  needs clarification before UAT.

## Ownership and direction

| Entity / field | Authority and supported direction | Trigger / latency target | Webhook and polling fallback | Conflict, idempotency and recovery | Binding, boundary and operator evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Store identity / domain | Shopify identity is authoritative; Odoo stores an immutable verified mirror | Admin setup probe, reconnect; synchronous probe | No webhook; explicit connection/readiness probe | Remote `shop.myshopifyDomain` must equal local domain; mismatch fails closed | `store.shop_domain` unique globally; company-owned store; probe job/log | **Implemented in code; live unproven** |
| API version / scopes | Shopify response and granted scopes are authoritative; Odoo stores verified evidence | Test connection/readiness | No webhook; probe/readiness evidence | API version is fixed to `2026-07`; mismatch fails closed | Store fields + connection job/log | **Implemented in code; live unproven** |
| Locations | Shopify authoritative read cache; Odoo administrator owns mapping to internal stock location | Setup/manual `inventory_location_sync`; paginated read | No webhook; refresh/reconciliation | No name guessing; missing/foreign GID blocks inventory work | Store-scoped location cache and explicit mapping; readiness/review | **Implemented in code; live unproven** |
| Product template / title | Shopify→Odoo import; optional explicit Odoo→Shopify export for export-enabled records | Product scan hourly; export preview/apply, not immediate | No webhook; cursor scan with overlap | Binding first, then SKU/barcode/manual review; export reads remote state before write | Template binding unique by store + Shopify GID and Odoo template; preview/attempt/reconciliation | **Direction explicit; freshness not near-real-time** |
| Product description | Shopify→Odoo import; Odoo→Shopify only when export-owned and present | Same as product | No webhook; scan/export read-back | Omitted optional value is not an implicit clear; stale preview blocked | Template binding + export plan/attempt | **Implemented conservatively; live unproven** |
| Vendor | Shopify→Odoo import if mapped by importer; no documented outbound vendor ownership | Product scan | No webhook; scan fallback | Matching/review rules; no name identity guessing | Template binding and import evidence | **Supported inbound; outbound contract not supported** |
| Variant identity | Shopify→Odoo import and optional export of explicitly mapped variant | Product scan/export plan | No webhook; cursor scan | Stable ProductVariant GID; no guessed identity; duplicate binding rejected | Variant binding unique by store + GID, Odoo variant and InventoryItem GID; parent same-store check | **Implemented in code; live unproven** |
| SKU | Shopify value imported; Odoo value exported only in explicit export scope | Product scan/export | No webhook; scan plus remote apply read | SKU may assist matching but is not sole identity; stale export preview blocked | Variant binding + snapshot/preview | **Supported with explicit ownership limits** |
| Barcode | Shopify value imported; Odoo value exported only in explicit export scope | Product scan/export | No webhook; scan plus remote apply read | Barcode is secondary match key; ambiguity routes to review | Variant binding + match decision | **Supported with explicit ownership limits** |
| Price | Shopify→Odoo import; Odoo→Shopify only when `odoo_authoritative` | Product scan; reviewed export | No webhook; scan/reconciliation | Export omits unmanaged price; remote identity/freshness checked | Template/variant binding, preview and attempt | **Implemented conservatively; live unproven** |
| Compare-at price | Shopify→Odoo import; outbound only when export contract explicitly owns it | Product scan/export | No webhook; scan/reconciliation | Omission-safe; no blind clear or resend | Binding + export preview/attempt | **Supported only when explicitly managed** |
| InventoryItem GID | Shopify authoritative; Odoo stores exact variant InventoryItem identity | Product/variant binding and inventory bootstrap | No webhook; location/inventory read refresh | Foreign item/location blocks; no identity guessing | Variant binding unique by store + InventoryItem GID | **Implemented in code; live unproven** |
| Inventory available quantity | Odoo is authoritative after onboarding; Odoo→Shopify only | Stock-move `odoo_event` enqueue plus 15-minute scan; queue drain ≤5 minutes nominal | No webhook; outbound scan and Shopify read reconciliation | Expected-before CAS; `inventorySetQuantities`/activation carry `@idempotent`; stale value creates review/replacement job | Inventory level binding `(store,item,location)`; preview/attempt/reconciliation/release action | **Outbound implemented; Shopify inbound write unsupported** |
| Inventory committed quantity | Neither side is written by connector | Not applicable | Not applicable | Explicitly never written | Evidence is code/manifest guard | **Unsupported** |
| Customer identity | Shopify→Odoo import | Order scan; no stated near-real-time target | No webhook; 15-minute order scan with overlap | Existing binding/email/manual review; no outbound customer mutation | Customer binding store-scoped; import/review evidence | **Inbound supported; live unproven** |
| Customer address | Shopify→Odoo order/customer import into Odoo partner/order addresses | Order import | No webhook; order scan overlap | Mapping/validation; ambiguous data reviewed | Customer/order binding and import logs | **Inbound supported; live unproven** |
| Orders | Shopify→Odoo import only | 15-minute scan, `updatedAt` overlap, cursor checkpoint | No webhook; scan is fallback and current primary trigger | Binding uniqueness; duplicate imports coalesce; divergent lifecycle routes review | Sale order binding unique by store + Shopify GID/Odoo order; job/log/review | **Direction explicit; not near-real-time** |
| Order lines / variants | Shopify authoritative read; Odoo order lines derived from mapped variants | During order import | No webhook; paginated child reads | Unknown product/variant/malformed page fails/reviews; no partial false success | Order binding + product/variant binding | **Inbound supported; live unproven** |
| Taxes | Shopify order tax data plus configured Odoo tax decisions | Order import and tax decision wizard | No webhook; scan/replay | Divergent currency/tax mapping blocks/reviews; no outbound mutation | Order/tax decision evidence | **Conservative inbound** |
| Discounts | Shopify discount applications/allocations imported into supported Odoo representation | Order import | No webhook; paginated discount reads | Unsupported forms/shape errors route to review; no outbound mutation | Order binding/import log | **Supported kernel only; live unproven** |
| Payments / gateways | Shopify payment/gateway observations imported; Odoo commercial settlement remains local | Order import and manual gateway decisions | No webhook; scan | Ambiguous gateway/COD state requires review; no outbound payment mutation | Order/payment decision evidence | **Conservative inbound** |
| Cancellations | Shopify observation→Odoo review/lifecycle evidence; existing sales are not blindly rewritten | Order scan overlap and review | No webhook; overlap scan | Divergent local lifecycle blocks; no outbound cancellation | Order binding, job/log/review | **Inbound observation supported; live unproven** |
| Refunds | Shopify observation→Odoo review/evidence where supported; no outbound refund mutation | Order/reconciliation path where implemented | No webhook; scheduled reconciliation only | Unsupported/refund ambiguity blocks; no false commercial success | Order binding/review | **Contract requires explicit live proof** |
| Fulfillment orders / lines | Shopify read authority for fulfillment-order state and lines | Fulfillment reader/reconciliation | No webhook; hourly reconciliation and reconnect catch-up | Incomplete pagination is not treated as absence; read error blocks | Fulfillment/order/picking bindings; snapshots | **Inbound read implemented; live unproven** |
| Fulfillments | Mode 1 Odoo picking→Shopify; Mode 2 Shopify→Odoo reconciliation for eligible existing records | Picking operation; Mode 2 hourly scan | No webhook; full read/reconcile fallback | Create uses intent fingerprint/operation scope/reconcile; no blind replay; Mode 2 applies conservatively | Fulfillment GID unique by store + picking; attempt/read evidence | **Implemented code; setup wording ambiguous** |
| Partial fulfillment | Odoo picking/fulfillment lines→Shopify as a bounded fulfillment; Shopify reads multiple fulfillment orders | Picking and reconciliation | No webhook; reader pagination | Exact line quantities and binding; uncertain create reconciles before replacement | Fulfillment binding per picking and order binding | **Code path exists; live unproven** |
| Backorders | Odoo stock/picking state remains local authority; Shopify fulfillment-order reads inform review | Picking/reconciliation | No webhook; hourly/reconnect scans | Unsupported mismatch blocks/reviews; no automatic commercial rewrite | Picking/order/fulfillment evidence | **Requires explicit acceptance case** |
| Tracking | Odoo→Shopify in-place `fulfillmentTrackingInfoUpdate` in Mode 1; Shopify read in Mode 2 | Picking/tracking action; reconciliation | No webhook; hourly read fallback | Mutation has no `@idempotent` directive; intent scope + read reconciliation prevent duplicate fulfillment | Fulfillment binding + attempt/read-back | **Code path exists; live unproven** |
| Returns | No complete independent return entity/mutation contract identified | Not defined | No webhook; no defined fallback | Must remain unsupported/review-only until product decision and live proof | No accepted return binding contract | **Unsupported / product decision required** |
| Configuration / mappings | Odoo administrator and company context authoritative | Setup, settings, location mapping, mode switch | No webhook; readiness/local checks | Protected fields, admin boundaries, company rules; generation fencing on lifecycle changes | Store/settings/mapping records and readiness evidence | **Implemented in code; runtime isolation unproven** |

## Global policy and unresolved decisions

1. Every supported mutation must record a durable attempt before network
   transport. Definitely-not-applied failures may retry; possibly-applied
   outcomes require remote read/reconciliation before replacement.
2. Shopify webhook topics, delivery IDs and watermarks are not currently part of
   any row. The proposed hybrid contract is specified in
   [`webhook-reconciliation-decision.md`](./webhook-reconciliation-decision.md).
3. Product/order scan caps are hard fail-closed limits, not evidence of
   supported merchant capacity. See [`scalability-report.md`](./scalability-report.md).
4. “Implemented” means source behavior was inspected; it does not mean a live
   Shopify execution passed.
