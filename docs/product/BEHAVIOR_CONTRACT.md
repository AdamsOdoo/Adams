# Behavior Contract

> Skeleton only. Goal 1 fills verified behavior, deltas, and decisions.

Do not treat blank skeleton fields as specified behavior. Preserve open questions until evidence resolves them.

## Setup

- Trigger: User opens and completes the Shopify onboarding wizard or directly configures a `shopify.backend`.
- Preconditions: Shop URL and Admin API token are available; optional webhook secret, company, warehouse, and pricelist may be entered.
- Happy path: Wizard tests the connection, creates a backend in `connected` state, optionally registers webhooks, initializes field mappings, and runs selected initial imports.
- Ownership: Current setup is wizard-supported but not wizard-enforced; backend settings remain normal editable model fields.
- Failure modes: Connection test catches exceptions and displays a failure message in the wizard. Webhook registration exceptions during setup are swallowed with `pass`, so setup can continue without surfacing that webhook registration failed. Initial import exceptions are logged and summarized in a `shopify.sync.log` plus notification.
- Idempotency: Creating a backend through the wizard always creates a new backend; import idempotency is delegated to individual importers/bindings.
- Money rules, if applicable: Setup chooses company, warehouse, pricelist, invoice/payment behavior, currency mode, and tax behavior, but current code does not lock or validate all money-affecting settings after go-live.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:55-73` — tests temporary connection and stores failure text.
  - `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:79-100` — creates backend, registers webhooks, initializes mappings.
  - `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:109-133` — runs selected imports and logs import errors.
  - `addons/shopify_connector_pro/models/shopify_backend.py:80-119` — backend exposes sync directions and currency mode settings.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decided: wizard-first locked setup with validation gate (DEC-020). Current: wizard creates/configures a backend, but settings are not locked after go-live in the inspected backend fields. Gap: implement lock/unlock/validation behavior in later goals.
- Status: DELTA
## Initial product import

- Trigger: Product import runs via ProductSync/importer batch or single-product webhook refresh.
- Preconditions: Backend can create Shopify API client; Shopify product GraphQL nodes include product, variant, option, image, and inventory item data.
- Happy path: Import maps Shopify product fields to Odoo product template fields, applies import mappings, matches by first variant SKU if possible, creates/updates product template, creates product binding, imports variants and images, and marks checksum/last sync.
- Ownership: Current code imports Shopify → Odoo and can update existing Odoo products; this is DELTA against DEC-018 because Odoo should become product master after initial import.
- Failure modes: Base importer uses savepoints per node; non-test failures become warning logs, error counts, sync-log details, and backend warning activity. Image download failures are warning-only and do not fail product import.
- Idempotency: Existing bindings are found by backend/shopify_id and skipped if checksum matches; SKU matching prevents duplicate product creation when importing an unbound Shopify product.
- Money rules, if applicable: First variant price is copied to `list_price` on import; current code does not make DEC-018 post-import Odoo price ownership explicit.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/product_sync.py:263-309` — imports product node, creates/updates product and binding.
  - `addons/shopify_connector_pro/sync/product_sync.py:327-353` — maps title, description, price, SKU, barcode, weight, image.
  - `addons/shopify_connector_pro/sync/product_sync.py:355-366` — matches existing Odoo product by first variant SKU.
  - `addons/shopify_connector_pro/sync/product_sync.py:440-475` — creates variant bindings using options then index fallback.
  - `addons/shopify_connector_pro/sync/base_importer.py:35-101` — batch savepoint, checksum skip, error activity.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Positional/index fallback for variant matching needs review: current code tries selected options, then falls back to variant index; decide whether index fallback is safe enough for public v1 or must be replaced by stricter SKU/option matching.
- Status: DELTA
## Product update Odoo → Shopify

- Trigger: Product export processes pending/error product bindings, or automatic export marks bindings when Odoo product records change.
- Preconditions: Product binding exists for backend; binding is pending/error with retry count below 5 and not `no_sync`; Shopify API client can execute product mutations.
- Happy path: Export creates Shopify product with `productSet` when no Shopify ID exists, updates product fields with `productUpdate` when it does, bulk-updates variant SKU/price/barcode, applies export field mappings, then marks binding synced with checksum.
- Ownership: Current code supports Odoo → Shopify export and bidirectional product direction; this aligns with DEC-018 only after initial import, but current backend default is `both`.
- Failure modes: Export exceptions are logged, classified permanent when applicable, written to binding error state, accumulated in sync log, and counted as errors.
- Idempotency: Export skips bindings whose computed checksum equals stored checksum; binding state/retry domain prevents unlimited retry in one batch.
- Money rules, if applicable: Exported variant prices come from configured pricelist if present, otherwise `lst_price`.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/product_sync.py:70-112` — create/update dispatch and productSet create.
  - `addons/shopify_connector_pro/sync/product_sync.py:114-154` — productUpdate and variant bulk update fields.
  - `addons/shopify_connector_pro/sync/product_sync.py:60-68` — export price comes from pricelist or list price.
  - `addons/shopify_connector_pro/sync/base_exporter.py:20-70` — pending/error export domain, checksum skip, error marking.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decided: Odoo is product master after initial Shopify import (DEC-018). Current: backend default allows bidirectional product sync. Gap: later goals must align defaults/UX/guards with DEC-018.
- Status: DELTA
## Inventory sync

- Trigger: Inventory export/sync runs for variant bindings with Shopify inventory item IDs across mapped locations/warehouses.
- Preconditions: Backend has active Shopify locations mapped to warehouses, or legacy single location plus warehouse; variant bindings have inventory item IDs.
- Happy path: Code resolves location/warehouse pairs, reads Odoo `free_qty` or `qty_available` per warehouse, batches up to Shopify's 100 limit, calls `inventorySetQuantities`, and creates/updates inventory binding `last_pushed_qty`.
- Ownership: Current code makes Odoo inventory the exported source for Shopify inventory quantities.
- Failure modes: Batch mutation exceptions are warning logs and error details; compare-quantity stale failures are not forced through, so next cron can retry.
- Idempotency: Location batch skips inventory bindings where `last_pushed_qty` equals current Odoo quantity; Shopify compareQuantity protects against external drift.
- Money rules, if applicable: none.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/inventory_sync.py:87-100` — resolves active location/warehouse pairs or legacy fallback.
  - `addons/shopify_connector_pro/sync/inventory_sync.py:119-153` — reads warehouse quantity, skips unchanged, batches pushes.
  - `addons/shopify_connector_pro/sync/inventory_sync.py:155-214` — calls `inventorySetQuantities`, updates bindings, records errors.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none under current code; later behavior contract may need exact quantity field/product availability policy if product decides between free vs on-hand.
- Status: SPECIFIED
## New paid Shopify order

- Trigger: Shopify order import receives an order whose financial status is `paid`.
- Preconditions: Customer can be resolved; backend has company/warehouse; order currency/rate checks pass; order lines can be created.
- Happy path: Creates a Shopify-channel sale order, creates line and shipping lines, confirms the order, creates/posts invoice when auto-invoice is enabled, stamps Shopify total on binding, and registers payment when paid.
- Ownership: Shopify is source for inbound order capture; Odoo owns accounting documents once created, protected by the total-check guard.
- Failure modes: Customer resolution failure returns no order with warning. Currency/rate failures create error-state order binding without sale order. Auto-invoice failures are isolated in savepoints and surfaced by warning/activity paths.
- Idempotency: Existing order bindings are reused; paid auto-invoice skips if non-cancelled invoice already exists; total stamp supports retry-safe guard behavior.
- Money rules, if applicable: Never post invoice automatically when total-check guard mismatches Shopify total; currency policy refuses missing/invalid rates instead of booking foreign amounts as company currency.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/order_sync.py:185-205` — creates sale order values from Shopify order.
  - `addons/shopify_connector_pro/sync/order_sync.py:207-275` — enforces currency/rate policy before order creation.
  - `addons/shopify_connector_pro/sync/order_sync.py:339-351` — confirms paid order and auto-creates invoice.
  - `addons/shopify_connector_pro/sync/order_sync.py:371-380` — skips auto-invoice when invoice already exists.
  - `addons/shopify_connector_pro/sync/order_sync.py:401-415` — total guard blocks before posting on mismatch.
  - `addons/shopify_connector_pro/sync/order_sync.py:164-183` — creates binding with stamped total and registers payment.
  - TEST: `addons/shopify_connector_pro/tests/test_total_guard.py::TestTotalGuardAutoInvoice::test_auto_invoice_match_posts` — matching paid auto-invoice posts.
- Decisions needed: none for current behavior.
- Status: SPECIFIED
## Unpaid/pending Shopify order

- Trigger: Shopify order import or status update sees financial status `pending`, `authorized`, or later transition to paid/partially paid.
- Preconditions: Order binding exists or can be created; payment transition handler can find related Odoo order/invoice.
- Happy path: Import creates a sale order and confirms it for `authorized`; pending orders remain tracked by status. Later status transitions can post a draft invoice or create one depending on backend settings.
- Ownership: Shopify financial status drives inbound status updates; Odoo posting is guarded by local invoice/accounting rules.
- Failure modes: Unknown or unsupported payment transitions are handled by the payment status handler with activity/log visibility per existing audit trail; posting failures schedule activity on the sale order.
- Idempotency: Handler compares old/new status and only processes changes; binding status does not advance when guarded posting fails.
- Money rules, if applicable: Pending/authorized orders must not become posted invoices unless configured/transitioned and guard passes.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/order_sync.py:122-140` — detects financial status changes and invokes handler.
  - `addons/shopify_connector_pro/sync/order_sync.py:339-358` — confirms authorized/paid/partial orders and flags partial payment.
  - `addons/shopify_connector_pro/sync/payment_status_sync.py:145-158` — payment transition blocks posting on total mismatch.
  - `addons/shopify_connector_pro/sync/payment_status_sync.py:656-670` — schedules manual-review activity for payment problems.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: AUD-014 remains the reference for unknown payment transitions; Goal 1 does not redesign the transition table.
- Status: SPECIFIED
## Missing product on order import

- Trigger: Order line import cannot find a matching Shopify variant binding or SKU/product for a line item.
- Preconditions: Shopify order line item exists with variant/SKU/product data but local product mapping may be missing.
- Happy path: Current code tries to resolve a product and creates a normal sale order line when found.
- Ownership: Current order import relies on existing product/variant mappings or fallback product resolution; missing product policy is not fully product-specified.
- Failure modes: When no product is resolved, order-line behavior must be verified in `_create_order_line`; current broad evidence found product-resolution paths but this section needs follow-up line-level confirmation before being SPECIFIED.
- Idempotency: Missing product handling is tied to order import idempotency by binding; unresolved line policy needs Goal 2/QA coverage.
- Money rules, if applicable: Missing products can affect invoice lines and totals; total-check guard backstops posted invoice mismatch.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/order_sync.py:312-320` — iterates Shopify line and shipping lines into Odoo order.
  - `addons/shopify_connector_pro/sync/order_sync.py:401-415` — total guard blocks posting if unresolved lines change totals.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decide whether missing product lines should create placeholder products, note lines, block order import, or create a visible error-state binding. Owner: standing principles unless Ahmed wants merchant-facing missing-product policy.
- Status: DECISION-NEEDED
## Abandoned cart → quotation

- Trigger: Abandoned cart import stores Shopify abandoned checkout data; user action creates quotation from the abandoned cart.
- Preconditions: Abandoned cart has customer email/name or existing customer binding; backend/company/warehouse are set; line item JSON exists.
- Happy path: Import creates/updates abandoned cart record. Manual action resolves/creates partner, creates draft Shopify-channel sale order with recovery URL note, creates quotation lines from variant binding or SKU, writes `sale_order_id`, and leaves unresolved products as note lines.
- Ownership: Shopify abandoned checkout is source; Odoo quotation is created manually from internal abandoned cart record. DEC-019 says abandoned carts create tagged quotations, but current code creates quotations without an explicit tag taxonomy found in this session.
- Failure modes: No customer raises UserError on manual action; quote creation logs warning and returns none if partner cannot be resolved. Missing product creates an unresolved note line instead of blocking quotation. Missing currency pricelist logs warning and uses default pricelist.
- Idempotency: If `sale_order_id` already exists, action opens existing quotation instead of creating another.
- Money rules, if applicable: Quotation prices are copied from cart line item price; no posted accounting document is created at this stage.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/abandoned_cart_sync.py:40-150` — imports abandoned checkouts into records.
  - `addons/shopify_connector_pro/models/shopify_abandoned_cart.py:123-143` — action opens existing quotation or creates one.
  - `addons/shopify_connector_pro/models/shopify_abandoned_cart.py:145-200` — creates draft quotation and links it to cart.
  - `addons/shopify_connector_pro/models/shopify_abandoned_cart.py:202-247` — creates product lines or unresolved note lines.
  - `addons/shopify_connector_pro/models/shopify_abandoned_cart.py:249-288` — resolves existing or new partner.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decided: abandoned carts create tagged quotations (DEC-019). Current: quotations are created and linked, but no explicit quotation tag was found. Gap: define and implement tag taxonomy.
- Status: DELTA
## Odoo delivery → Shopify fulfillment

- Trigger: Odoo outgoing picking validation for a Shopify sale order with reverse sync enabled.
- Preconditions: Picking reaches done state, sale order is Shopify-channel, order has Shopify binding, backend connected, and sale order reverse sync is enabled.
- Happy path: Stock picking hook calls fulfillment sync, fetches Shopify fulfillment orders, matches done picking move quantities by SKU, builds fulfillment line items, includes tracking info when present, and calls Shopify fulfillmentCreate.
- Ownership: Odoo delivery validation pushes fulfillment/tracking to Shopify for Shopify-channel orders.
- Failure modes: Missing Shopify ID logs a warning and returns. Fulfillment push exceptions are caught by stock picking hook and logged as warnings; no activity is scheduled there.
- Idempotency: Shopify remainingQuantity and fulfillment-order status prevent fulfilling closed or zero-remaining lines; SKU quantity map only fulfills quantities from the current picking.
- Money rules, if applicable: none.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/stock_picking.py:11-32` — hooks picking validation and filters Shopify orders.
  - `addons/shopify_connector_pro/models/stock_picking.py:34-59` — calls fulfillment push and logs failures.
  - `addons/shopify_connector_pro/sync/fulfillment_sync.py:156-221` — matches SKU quantities and calls fulfillmentCreate.
  - TEST: `addons/shopify_connector_pro/tests/test_fulfillment_sync.py::TestFulfillmentSync::test_push_skips_without_shopify_id` — no Shopify ID skip path.
- Decisions needed: Decide whether outbound fulfillment push failure should be escalated to activity/sync log rather than warning-only. Owner: standing principles.
- Status: SPECIFIED
## Shopify fulfillment → Odoo delivery

- Trigger: Fulfillment webhook/import invokes inbound fulfillment handler.
- Preconditions: Order binding has linked Odoo order; backend external fulfillment handling is `ignore`, `activity`, or `auto_validate`; current Shopify fulfillment status can be fetched or fallback status exists.
- Happy path: Updates binding and sale order fulfillment status. In `ignore` mode it stops after status update; in `activity` mode it schedules manual activity; in `auto_validate` mode it validates pending outgoing pickings with all demanded quantities.
- Ownership: Shopify can drive Odoo delivery handling only according to backend external fulfillment handling setting.
- Failure modes: Missing Odoo order logs warning and returns. Fetch status failure logs warning and reuses previous status. Auto-validation failure logs warning and creates fulfillment activity. Historical BUG-F1 notes partial receipt is not fully handled.
- Idempotency: If fetched fulfillment status equals old status, handler logs unchanged and returns. Already done/cancelled pickings are excluded.
- Money rules, if applicable: none.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/fulfillment_sync.py:230-263` — updates statuses and skips unchanged status.
  - `addons/shopify_connector_pro/sync/fulfillment_sync.py:264-288` — applies ignore/activity/auto-validate modes.
  - `addons/shopify_connector_pro/sync/fulfillment_sync.py:329-350` — fetches status with fallback on error.
  - `addons/shopify_connector_pro/sync/fulfillment_sync.py:352-401` — auto-validates or schedules activity on failure.
  - `docs/archive/LEGACY_NOTES.md:123-126` — BUG-F1 documents partial receipt limitation.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decide whether partial external fulfillment should create partial pickings/backorders or remain manual activity. Owner: standing principles unless merchant promise requires Ahmed.
- Status: DELTA
## Shopify refund → Odoo credit note

- Trigger: Refund import sees Shopify refund data for an imported order.
- Preconditions: Sale order exists; refund is not already bound/booked; sales journal and income accounts/fallbacks can be resolved; refund currency matches invoice/order currency.
- Happy path: Creates itemized out_refund credit note, stamps Shopify refund GID, balances to Shopify `totalRefundedSet`, posts it, creates refund binding/lines, and schedules tax verification activity if tax reversal fallback was needed.
- Ownership: Shopify refund is source of truth for refund amount; Odoo owns posted credit note after verified creation.
- Failure modes: Existing credit note with same refund GID is reused. Missing journal/account/currency mismatch/over-refund creates warning/activity and returns without credit note. Zero lines/zero amount logs warning and skips.
- Idempotency: Refund binding plus `shopify_refund_gid` recovery guard prevents duplicate credit notes if binding creation fails or is lost. Cumulative over-refund guard prevents posting beyond invoice total.
- Money rules, if applicable: Credit note currency follows posted invoice/order; refund amount is matched to Shopify total; over-refund and currency mismatch degrade visibly without posting.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/refund_sync.py:181-201` — refund GID recovery guard reuses existing credit note.
  - `addons/shopify_connector_pro/sync/refund_sync.py:216-242` — missing journal/accounts create warning activity and skip.
  - `addons/shopify_connector_pro/sync/refund_sync.py:405-431` — currency mismatch creates activity and skips.
  - `addons/shopify_connector_pro/sync/refund_sync.py:433-472` — cumulative over-refund guard blocks credit note.
  - `addons/shopify_connector_pro/sync/refund_sync.py:474-535` — creates/posts credit note and balances to Shopify amount.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current refund import behavior.
- Status: SPECIFIED
## Odoo credit note → Shopify refund

- Trigger: Odoo `account.move.action_post()` posts an outbound refund/credit note linked to a Shopify order.
- Preconditions: Move is `out_refund`, sale order is Shopify-channel, sale order reverse sync is enabled, binding/backend connected, and backend `reverse_sync_refund` is enabled.
- Happy path: Code converts credit note amount to order currency when needed, builds Shopify `refundCreate` input with manual refund transaction, executes mutation, and logs success.
- Ownership: Odoo posted credit note can push a Shopify refund when reverse-sync refund is enabled.
- Failure modes: API/mutation exception is caught, warning logged, and a warning activity is scheduled explaining that Odoo credit note is posted but Shopify refund was not created.
- Idempotency: No explicit Shopify refund idempotency key was found in this reverse path; repeated posting is naturally limited because action_post runs once per draft move, but retry semantics are not specified.
- Money rules, if applicable: This is a money-path capability that can create real Shopify refunds; per DEC-027 it is not a v1 core promise and should default OFF / not be marketed until idempotency and approval controls exist.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/account_move.py:108-132` — filters posted credit notes for Shopify reverse refund sync.
  - `addons/shopify_connector_pro/models/account_move.py:138-170` — converts amount and calls Shopify refundCreate.
  - `addons/shopify_connector_pro/models/account_move.py:177-198` — schedules visible activity on Shopify refund failure.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none after DEC-027, but keep AUD-029 as implementation/idempotency risk. Decided: not a v1 core promise and should default OFF / not marketed until idempotency and approval controls exist. Current: code can push refundCreate when reverse_sync_refund is enabled. Gap: capability exists, but v1 product policy is conservative due to AUD-029.
- Status: DELTA
## Payouts

- Trigger: Payout import fetches Shopify payouts and payout transactions.
- Preconditions: Backend API client can query payouts; Odoo currency record exists for payout net currency.
- Happy path: Import creates/updates `shopify.payout`, stores status/net/gross/fees/summary amounts, imports transaction lines, and keeps a unique backend+payout ID.
- Ownership: Current code imports payout data for reconciliation/reporting; accounting-entry automation is not implemented despite a `journal_entry_id` field.
- Failure modes: Import loop logs warnings and increments errors for failed payout nodes. Unknown transaction/source types are warning-only and stored as empty selection values. Missing currency leaves currency false on monetary rows.
- Idempotency: Existing payout is found by backend and Shopify payout ID; transaction import updates existing transaction rows by payout and transaction ID.
- Money rules, if applicable: Payout data is visibility/reconciliation only in v1; no automatic payout journal entries are created (DEC-026).
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/payout_sync.py:67-112` — creates/updates payout amounts and imports transactions.
  - `addons/shopify_connector_pro/sync/payout_sync.py:147-190` — creates/updates payout transaction rows and warns unknown types.
  - `addons/shopify_connector_pro/models/shopify_payout.py:34-38` — defines journal-entry link field.
  - `addons/shopify_connector_pro/models/shopify_payout.py:47-50` — enforces unique backend+payout ID.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none after DEC-026.
- Status: SPECIFIED
## Reconciliation

- Trigger: Reconciliation cron/action runs for a backend.
- Preconditions: Recent order bindings exist with Shopify financial/fulfillment/refund status and linked Odoo orders/invoices/pickings/refund bindings.
- Happy path: Code scans recent paid/refunded/pending/fulfilled bindings, compares Shopify status to Odoo invoices/refund bindings/pickings, writes partial sync logs for mismatches, and returns error counts.
- Ownership: Reconciliation is a visibility/checking layer; it does not itself fix accounting or fulfillment mismatches.
- Failure modes: Mismatches become warnings and `shopify.sync.log` partial entries. Stale/error retry reconciliation resets stuck binding errors to pending with incremented retry count.
- Idempotency: Reconciliation searches bounded windows and creates log entries; retry reset only applies to bindings under retry limit.
- Money rules, if applicable: Paid-without-posted-invoice, refund-count mismatch, and pending-with-posted-invoice are surfaced rather than silently accepted.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/shopify_reconciliation.py:169-220` — logs paid Shopify orders missing posted invoice.
  - `addons/shopify_connector_pro/models/shopify_reconciliation.py:222-265` — logs refund binding count mismatches.
  - `addons/shopify_connector_pro/models/shopify_reconciliation.py:267-310` — logs pending/authorized Shopify orders with posted invoices.
  - `addons/shopify_connector_pro/models/shopify_reconciliation.py:128-165` — resets retryable stale error bindings.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current visibility behavior.
- Status: SPECIFIED
## Gift cards

- Trigger: Gift card import fetches Shopify gift cards.
- Preconditions: Backend can query `FETCH_GIFT_CARDS`; Shopify returns gift card nodes with masked code, values, currency, enabled status, customer/order links.
- Happy path: Creates or updates `shopify.gift.card` by backend/shopify_id, stores masked code, initial amount, balance, currency code, status, expiry, and optional customer/order binding links.
- Ownership: Shopify is source of gift-card records; Odoo stores mirror records only.
- Failure modes: Per-card import exception is warning logged, counted, and included in sync log finalization; no accounting liability entry is created.
- Idempotency: Existing gift cards are found by backend/shopify_id and updated; new records store checksum as Shopify ID.
- Money rules, if applicable: Gift card amounts are mirrored/reference only in v1; no automatic gift-card liability accounting entries are created or implied (DEC-025).
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/gift_card_sync.py:19-31` — fetches gift cards and creates sync log.
  - `addons/shopify_connector_pro/sync/gift_card_sync.py:34-96` — creates/updates gift-card records and records errors.
  - `addons/shopify_connector_pro/models/shopify_gift_card.py:11-27` — stores masked code, amounts, status, links, expiry.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none after DEC-025.
- Status: SPECIFIED
## Promoters/discounts

- Trigger: Discount export/import sync runs for promoter discount codes and Shopify discount nodes.
- Preconditions: Promoter/discount binding exists for export or Shopify discount data exists for import; backend API client can execute discount mutations/queries.
- Happy path: Export creates basic or free-shipping discount codes using promoter name/code/value/limits and stores Shopify ID; import stores Shopify discount codes and usage metadata.
- Ownership: Current code supports Odoo/promoter-driven discount export and Shopify discount import; promoters are first-class product decision for v1 (DEC-022).
- Failure modes: Discount export uses base exporter error handling; import catches per-node errors, warning logs, and increments error counts.
- Idempotency: Export checksums skip unchanged discount bindings; import searches existing discount codes by backend/shopify_id/code before create/update.
- Money rules, if applicable: Discounts affect order totals; imported order totals remain protected by total-check guard when invoicing.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/discount_sync.py:28-76` — dispatches create/update and creates basic discount code.
  - `addons/shopify_connector_pro/sync/discount_sync.py:77-130` — creates free-shipping discount code.
  - `addons/shopify_connector_pro/sync/discount_import_sync.py:50-150` — imports discount nodes into Odoo records.
  - `addons/shopify_connector_pro/models/shopify_promoter.py:1-130` — defines promoter model and related fields/actions.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current high-level behavior; Goal 2 may decide flagging/staging for advanced discount types.
- Status: SPECIFIED
## Metafields

- Trigger: Metafield import/export sync runs for configured owners/mappings.
- Preconditions: Backend API client can query/mutate metafields; owner records and mapping records exist where required.
- Happy path: Code imports Shopify metafields into `shopify.metafield`, and export builds metafield mutation inputs for mapped Odoo values.
- Ownership: Current code treats metafields as auxiliary synchronized data; ownership depends on import/export path/mapping.
- Failure modes: Metafield sync catches API/record exceptions through sync-specific/base logging and marks errors depending on path; no product decision on conflict behavior was found.
- Idempotency: Existing metafields are matched by backend/shopify ID/owner/key where implemented; checksum/binding patterns reduce duplicates.
- Money rules, if applicable: none unless a future metafield maps money-affecting data; no such verified mapping is specified here.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/metafield_sync.py:35-140` — imports/metafield-maps Shopify metafield data.
  - `addons/shopify_connector_pro/models/shopify_metafield.py:1-120` — defines stored metafield owner/key/value/type fields.
  - `addons/shopify_connector_pro/models/shopify_metafield_mapping.py:1-120` — defines mapping configuration.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decide conflict/ownership behavior for bidirectional metafields before claiming full v1 behavior. Owner: standing principles.
- Status: DECISION-NEEDED
## Multi-store

- Trigger: Any sync operation runs for a specific backend/store.
- Preconditions: One or more `shopify.backend` records exist, each with shop URL/token/company/warehouse configuration.
- Happy path: Binding models carry `backend_id`; searches and unique constraints generally scope records by backend; API clients are created per backend.
- Ownership: Each backend represents a Shopify store; sync operations are backend-scoped.
- Failure modes: Misconfigured shop URL/token prevents API client creation or connection. Webhook shop-domain mismatch returns accepted/skipped response to avoid processing against the wrong backend.
- Idempotency: Backend+Shopify ID binding scopes prevent collisions across stores where implemented.
- Money rules, if applicable: Backend company/currency/journal settings determine accounting context per store.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/shopify_binding.py:9-12` — abstract bindings require backend ID and Shopify ID.
  - `addons/shopify_connector_pro/models/shopify_backend.py:10-40` — backend model stores shop configuration.
  - `addons/shopify_connector_pro/shopify_api/client.py:95-115` — API client validates shop URL and token per backend.
  - `addons/shopify_connector_pro/controllers/webhook.py:96-110` — rejects/mutes webhook shop-domain mismatch.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current backend-scoped behavior.
- Status: SPECIFIED
## Multi-company

- Trigger: Backend, sync, health, or binding operations run in an Odoo multi-company database.
- Preconditions: Backend has `company_id`; users have allowed-company access; sync code uses backend company context where needed.
- Happy path: Backend is company-scoped, sale order import uses backend company context, health endpoint searches without sudo so record rules apply, and binding data is scoped through backend.
- Ownership: Odoo company owns accounting/warehouse context for each backend.
- Failure modes: If company/warehouse/chart settings are incomplete, downstream order/invoice/payment sync paths fail visibly via their specific error handling.
- Idempotency: Backend-scoped binding uniqueness prevents cross-company/backend duplicate collisions where constraints exist.
- Money rules, if applicable: Company context determines currency, chart, warehouse, journals, taxes, and accounting moves.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/shopify_backend.py:49-78` — backend has company, warehouse, pricelist, location fields.
  - `addons/shopify_connector_pro/sync/order_sync.py:289-295` — sale order creation uses backend company context.
  - `addons/shopify_connector_pro/controllers/webhook.py:241-249` — health endpoint uses non-sudo search for record rules.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current company scoping.
- Status: SPECIFIED
## Shopify Markets/B2B

- Trigger: Shopify order import uses presentment currency or company/customer data associated with Markets/B2B scenarios.
- Preconditions: Backend `import_currency_mode` may be `presentment`; Shopify order payload includes presentment currency/money fields.
- Happy path: Presentment mode uses presentment currency code/money, resolves/activates currency and rate, and sets order currency/pricelist.
- Ownership: Current code supports currency side of Markets through presentment money; no verified B2B company/location-specific contract was found.
- Failure modes: Missing presentment currency, missing currency record, or missing rate blocks import through visible error-state binding.
- Idempotency: Same as order import: binding reuse and retryable error-state binding.
- Money rules, if applicable: Presentment currency must not be silently booked as company currency; rate must be usable.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/shopify_backend.py:115-120` — backend exposes presentment currency import mode.
  - `addons/shopify_connector_pro/sync/order_sync.py:216-227` — chooses presentment or shop currency code.
  - `addons/shopify_connector_pro/sync/order_sync.py:247-275` — resolves currency/rate and pricelist for non-company modes.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decide B2B-specific ownership/behavior beyond currency handling, including company/contact mapping and Shopify Markets/B2B claims. Owner: standing principles unless listing claims require Ahmed.
- Status: DECISION-NEEDED
## Duplicate webhook

- Trigger: Webhook controller receives an event with Shopify webhook ID or, if absent, duplicate topic/resource/updated_at fingerprint.
- Preconditions: Backend ID route, topic header, HMAC, and payload are available; webhook logging model can search/create rows.
- Happy path: Controller validates HMAC, parses payload, deduplicates per backend+webhook_id, rejects stale payloads, computes fallback fingerprint, creates log, and pending cron processes it.
- Ownership: Webhook delivery is Shopify → Odoo; processing is asynchronous through `shopify.webhook.log`.
- Failure modes: Duplicate webhook returns `{status: ok}` without reprocessing. Stale payload returns ok/skipped. Processing failures increment retry count and eventually dead-letter in webhook log.
- Idempotency: Unique constraint is backend+webhook_id; fallback fingerprint catches duplicates without ID. AUD-024 notes prior global dedup concern; current code comments mark per-backend scope.
- Money rules, if applicable: Duplicate order/refund/payment webhooks must not duplicate financial work; webhook log idempotency is the first guard before sync-specific idempotency.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/controllers/webhook.py:141-149` — deduplicates webhook ID per backend.
  - `addons/shopify_connector_pro/controllers/webhook.py:150-170` — skips stale payloads and computes fallback fingerprint.
  - `addons/shopify_connector_pro/models/shopify_webhook_log.py:48-54` — unique webhook ID constraint scoped by backend.
  - `addons/shopify_connector_pro/models/shopify_webhook_log.py:107-130` — cron processes pending/error logs and records failures.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current per-backend dedup behavior; keep AUD-024 history as regression reference.
- Status: SPECIFIED
## API throttling

- Trigger: Any Shopify GraphQL query/mutation is executed through `ShopifyClient`.
- Preconditions: Backend has valid canonical Shopify shop URL and decrypted access token.
- Happy path: Client validates shop host, configures session headers, waits for estimated cost through adaptive rate limiter, posts GraphQL request, updates limiter from Shopify throttle response, records circuit-breaker success, and returns parsed body.
- Ownership: Connector owns client-side rate limiting/retry/circuit breaker; Shopify remains source of actual throttle status.
- Failure modes: Circuit breaker open raises API error. Network and retryable HTTP errors back off/retry and eventually record failure. Non-200 and GraphQL errors raise sanitized API errors.
- Idempotency: Throttling does not provide business idempotency; it protects request pacing. Business idempotency remains in sync bindings/checksums.
- Money rules, if applicable: API failures in money paths must be handled by the caller visibly; client raises errors rather than silently swallowing them.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/shopify_api/client.py:95-115` — validates host/token and initializes limiter/circuit breaker.
  - `addons/shopify_connector_pro/shopify_api/client.py:136-175` — checks circuit breaker, waits for rate budget, retries network failures.
  - `addons/shopify_connector_pro/shopify_api/client.py:177-219` — handles retryable HTTP, non-200, GraphQL errors, throttle update.
  - `addons/shopify_connector_pro/shopify_api/rate_limiter.py:25-57` — reserves estimated cost and adapts from response.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current throttling behavior.
- Status: SPECIFIED
## Missing tax mapping

- Trigger: Order import sees Shopify tax lines/rates that cannot be mapped to Odoo tax records.
- Preconditions: Shopify order line or shipping line contains tax data; backend/company tax mapping may be absent or incompatible with price-included/excluded mode.
- Happy path: Tax resolution attaches mapped/resolved Odoo taxes to order lines and shipping lines so invoices compute expected totals.
- Ownership: DEC-013 says missing required tax flavor degrades visibly and directs merchant to tax mapping; never auto-create fiscal tax records.
- Failure modes: Current code accumulates dropped tax information and schedules a visible activity after creating all lines; total-check guard prevents wrong posted totals if missing tax mapping changes invoice total.
- Idempotency: Re-import/checksum behavior prevents duplicate orders; tax mapping repair followed by retry can rerun import for failed/error bindings where applicable.
- Money rules, if applicable: Never auto-create account.tax; never silently post wrong totals; use visible mapping instruction and guard.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/order_sync.py:297-323` — accumulates dropped taxes and schedules one activity.
  - `addons/shopify_connector_pro/sync/order_sync.py:401-415` — total guard blocks posting after tax resolution mismatch.
  - `docs/architecture/DECISIONS.md:17` — DEC-013 forbids auto-created taxes and requires visible degradation.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current DEC-013 policy.
- Status: SPECIFIED
## Currency/rate missing

- Trigger: Order import receives non-company or presentment currency requiring currency activation, pricelist, or exchange rate.
- Preconditions: Backend `import_currency_mode` is company/shopify/presentment and Shopify money fields carry currency codes/amount pairs.
- Happy path: Code uses Shopify money-pair conversion in company mode when possible, activates inactive currencies visibly, verifies/creates needed rate/pricelist paths, and sets order currency/pricelist.
- Ownership: FINALIZE currency policy/AUD-020 governs: do not book foreign amounts as company currency without usable conversion.
- Failure modes: Missing currency or unusable rate creates a visible error-state binding with actionable message and no sale order.
- Idempotency: `_order_import_error` reuses existing order binding and leaves it retryable; pending retry path can later create the sale order after configuration is fixed.
- Money rules, if applicable: Never book foreign amounts as company currency without derivable/order or Odoo rate; visibly activate known inactive currencies.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/order_sync.py:207-275` — selects currency mode and blocks missing rates/currencies.
  - `addons/shopify_connector_pro/sync/order_sync.py:629-657` — creates/reuses visible error-state order binding.
  - `addons/shopify_connector_pro/sync/order_sync.py:659-698` — activates inactive currencies visibly or returns false.
  - `addons/shopify_connector_pro/sync/order_sync.py:520-535` — converts Shopify money amounts when company conversion is prepared.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: none for current AUD-020 policy.
- Status: SPECIFIED
## Product deleted/archived

- Trigger: Product import sees Shopify product status, or export writes a product status to Shopify.
- Preconditions: Shopify product node includes `status`, or Odoo export creates a Shopify product.
- Happy path: Import stores Shopify status lowercased on the product binding; export create sends Shopify `status: ACTIVE`.
- Ownership: Current code records Shopify status but does not specify a full deletion/archive lifecycle in Odoo.
- Failure modes: No dedicated delete/archive branch was found in inspected product sync code; deleted/archived product behavior therefore depends on generic import/export error handling or status storage.
- Idempotency: Existing binding checksum and Shopify ID prevent duplicate binding creation, but there is no verified tombstone/archival idempotency path for deleted Shopify products.
- Money rules, if applicable: none.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/sync/product_sync.py:296-306` — stores lowercased Shopify product status on binding.
  - `addons/shopify_connector_pro/sync/product_sync.py:84-91` — product export create sends Shopify status ACTIVE.
  - `addons/shopify_connector_pro/sync/base_importer.py:35-101` — generic import error/log behavior only.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decide whether archived/deleted Shopify products should archive Odoo products, set binding status only, or require manual review. Owner: standing principles unless product removal behavior is considered high-risk for merchants.
- Status: DECISION-NEEDED
## Settings changed after go-live

- Trigger: Admin edits backend settings after a backend exists or after onboarding is complete.
- Preconditions: A `shopify.backend` record exists.
- Happy path: Current backend fields are normal editable model fields; no verified lock/unlock/validation gate was found in the inspected model code.
- Ownership: Product decision DEC-020 says settings should lock after setup/go-live with admin unlock and validation gate. Current code does not implement that behavior.
- Failure modes: Unsafe edits are not blocked by a generic go-live lock in code found during this session; downstream sync failures would surface through individual sync paths/logs.
- Idempotency: Not applicable to settings edits; current code does not provide a staged pending-settings state for validation before taking effect.
- Money rules, if applicable: Changing currency, tax, payment, invoice, warehouse, pricelist, and reverse-sync settings can affect future financial documents; no global post-go-live validation gate was found.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/shopify_backend.py:80-119` — product/customer/order/currency settings are normal fields.
  - `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:79-100` — wizard creates backend but does not lock future edits.
  - TEST: none found — flagged as coverage debt (T4).
- Decisions needed: Decided: locked settings with validation gate (DEC-020). Current: no lock found. Gap: later implementation must add lock/unlock and validation semantics.
- Status: DELTA
## Total-check guard

- Trigger: Before automatic invoice posting from Shopify paid/payment-transition flows or paid-order auto-invoice import, the connector checks the draft invoice total against the Shopify total stamped on the order binding.
- Preconditions: A draft customer invoice exists for a Shopify order binding. `shopify_total_amount` contains the Shopify `totalPriceSet` amount stamped during import, or `0.0` for legacy/no-stamp bindings.
- Happy path: If the stamp is absent/zero, the guard skips for upgrade compatibility. If present and the computed invoice `amount_total` differs from the stamped Shopify amount by no more than `2 * move.currency_id.rounding`, automatic posting continues.
- Ownership: Current code enforces DEC-011/DEC-012 in the connector before Odoo posts accounting documents; DEC-024 is closed by verification row `DEC-024-CLOSE`.
- Failure modes: If the difference exceeds tolerance, automatic posting is blocked, the invoice remains draft, the payment transition returns failure or auto-invoice import returns without posting, and a warning activity is scheduled on the sale order.
- Idempotency: A mismatch leaves the binding/order retryable instead of advancing to a posted accounting state; a zero/no-stamp binding is intentionally treated as compatible legacy data.
- Money rules, if applicable: Never wrong money — mismatched invoices must not be posted automatically. The tolerance is exactly 2 × invoice currency rounding.
- Feature flags: none yet — Goal 2
- Evidence:
  - `addons/shopify_connector_pro/models/shopify_order_binding.py:43-51` — stores Shopify total stamp and documents zero-stamp skip.
  - `addons/shopify_connector_pro/sync/order_sync.py:164-169` — stamps `totalPriceSet` on new order binding.
  - `addons/shopify_connector_pro/sync/accounting.py:124-140` — compares `move.amount_total` to expected total with 2× rounding tolerance.
  - `addons/shopify_connector_pro/sync/accounting.py:143-167` — schedules visible warning activity stating invoice stays draft.
  - `addons/shopify_connector_pro/sync/order_sync.py:401-415` — auto-invoice path returns before posting on mismatch.
  - `addons/shopify_connector_pro/sync/payment_status_sync.py:145-158` — payment transition path returns false before posting on mismatch.
  - TEST: `addons/shopify_connector_pro/tests/test_total_guard.py::TestTotalGuardPaymentPath::test_mismatch_blocks_posting` — block path keeps invoice draft and creates activity.
  - TEST: `addons/shopify_connector_pro/tests/test_total_guard.py::TestTotalGuardPaymentPath::test_no_stamp_posts_normally` — zero stamp skip path posts normally.
  - TEST: `addons/shopify_connector_pro/tests/test_total_guard.py::TestTotalGuardAutoInvoice::test_auto_invoice_mismatch_stays_draft_with_activity` — auto-invoice mismatch stays draft and records activity.
- Decisions needed: none.
- Status: SPECIFIED
