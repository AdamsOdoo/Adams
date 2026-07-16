# Shopify Official Captures — Orders/COD, Abandoned Checkouts, Fulfillment State Models, Inventory/Product Mutations, Limits (2026-07-16)

> **Capture file** per `docs/00-source-materials/README.md` rules: raw
> Tier-1 evidence (quotes/paraphrases with citation headers). Conclusions live
> in `docs/01-research/**` and `docs/02-product/**`. All sources accessed
> **2026-07-16** against the **latest stable Admin GraphQL API version
> 2026-07** (version confirmed on the pages themselves). Access status is
> recorded per source. Quotes are marked; everything else is close paraphrase.
> Produced by the Fable gap-closure mission (three parallel research passes,
> each verifying enum values on live pages — no memory-derived enums).
> This capture closes gaps R-1, R-2, R-3, R-5 of
> `../01-research/mvp-remaining-gap-inventory.md`.

## 1. Order financial states — `OrderDisplayFinancialStatus`

Source: https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderDisplayFinancialStatus — Accessible, 2026-07-16.

Complete current list (8 values; **no deprecated values on the page**):

| Value | Official definition [quote] |
|---|---|
| `AUTHORIZED` | "The payment provider has validated the customer's payment information. This status appears only for manual payment capture" — capture before the authorization period expires. |
| `EXPIRED` | "Payment wasn't captured before the payment provider's deadline on an authorized order. Some payment providers use this status to indicate failed payment processing." |
| `PAID` | "Payment was automatically or manually captured, or the order was marked as paid." |
| `PARTIALLY_PAID` | "A payment was manually captured for the order with an amount less than the full order value." |
| `PARTIALLY_REFUNDED` | "The amount refunded to a customer is less than the full amount paid for an order." |
| `PENDING` | "Orders have this status when the payment provider needs time to complete the payment, or when manual payment methods are being used." — the status COD orders carry. |
| `REFUNDED` | "The full amount paid for an order was refunded to the customer." |
| `VOIDED` | "An unpaid (payment authorized but not captured) order was manually canceled." |

[Fact] `Order.displayFinancialStatus` is nullable (Order object page).

## 2. Transactions and COD / manual-gateway identification

Sources (all Accessible, 2026-07-16):
- https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderTransactionKind
- https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderTransactionStatus
- https://shopify.dev/docs/api/admin-graphql/latest/objects/OrderTransaction

- [Fact] `OrderTransactionKind` (8, none deprecated): `AUTHORIZATION`, `CAPTURE`, `CHANGE` [quote: "money returned to the customer when they've paid too much during a cash transaction" — cash/COD-relevant], `EMV_AUTHORIZATION`, `REFUND` [quote: "can happen only after a capture is processed"], `SALE` [quote: "authorization and capture performed together in a single step"], `SUGGESTED_REFUND`, `VOID`.
- [Fact] `OrderTransactionStatus` (6, none deprecated): `AWAITING_RESPONSE`, `ERROR`, `FAILURE`, `PENDING`, `SUCCESS`, `UNKNOWN`.
- [Fact] `OrderTransaction` key fields (paraphrase): `kind`, `status`, `gateway` (payment service name), `formattedGateway`, `amountSet` (MoneyBag shop+presentment), `manuallyCapturable`, `paymentId`, `errorCode`, `authorizationExpiresAt` (Shopify Plus only), `parentTransaction`, `test`, and **`manualPaymentGateway: Boolean`**.
- **COD discrimination [Fact + Inference]:** `OrderTransaction.manualPaymentGateway = true` is the direct manual-gateway signal; manual transactions surface `gateway: "manual"` or the configured manual method name (e.g. "Cash on Delivery (COD)"); `Order.paymentGatewayNames` lists gateways used. A pending *card* transaction is a gateway-processed transaction (e.g. Shopify Payments) with `status: PENDING` and `manualPaymentGateway: false`. [Inference] A connector must therefore key manual-payment policy off `manualPaymentGateway`/gateway identity, never off `displayFinancialStatus: PENDING` alone.
- [Fact — Partial source] `orderMarkAsPaid` is "useful for orders created with manual payment methods like cash on delivery, bank deposit, and money order" [paraphrase] — https://shopify.dev/docs/api/admin-graphql/latest/mutations/ordermarkaspaid — Partial (search excerpt), 2026-07-16. `orderCreateManualPayment` also exists for recording manual payments. [Open question] Exact input shapes to re-verify on the raw pages before Wave 2 implementation.
- [Fact — Partial source] REST PaymentGateway historically shows COD as type `ManualPaymentGateway`, `processing_method: "manual"` — https://shopify.dev/docs/api/admin-rest/latest/resources/paymentgateway — Partial (search summary), 2026-07-16.

## 3. Order import surface

Source: https://shopify.dev/docs/api/admin-graphql/latest/queries/orders and .../objects/Order — Accessible, 2026-07-16.

- [Fact] `orders` query args: `first/last`, `after/before`, `query`, `sortKey` (default `PROCESSED_AT`), `reverse`, `savedSearchId`. Query filters verified: `created_at`/`updated_at` ranges (e.g. `updated_at:>2019-12-01`); `financial_status:` `paid|pending|authorized|partially_paid|partially_refunded|refunded|voided|expired`; `status:` `open|closed|cancelled|not_closed`; `fulfillment_status:` `unshipped|shipped|fulfilled|partial|scheduled|on_hold|unfulfilled|request_declined`; `test:true|false`; plus cart token, customer id, email, discount code, risk level, return status, SKU. Cursor pagination via `pageInfo { hasNextPage endCursor }`.
- [Fact] Order fields (paraphrase): `lineItems` (connection); `discountApplications` (paginated, "excluding order edits and refunds"); `shippingLines`/`shippingLine`; `taxLines` (per rate+title, before returns); `taxesIncluded`; `currencyCode` (shop currency) vs `presentmentCurrencyCode`; `*Set` money fields are `MoneyBag` (both currencies): `totalPriceSet` (after returns), `subtotalPriceSet` (after discounts, before returns), `totalTaxSet` (after returns/refunds); `cancelledAt` (null when not cancelled), `cancelReason`; `closed`, `closedAt`; `test`; `paymentGatewayNames`; `transactions`; `refunds`; `edited: Boolean`; `risk` (OrderRiskSummary) — **deprecated: `riskLevel`, `risks`**.
- [Fact] Order editing: `orderEditBegin` → staged **`CalculatedOrder`** (`orderEditSetQuantity`, `orderEditAddVariant`, discount/shipping edits) → `orderEditCommit`; commit fires the **`orders/edited` webhook**; only unfulfilled line items are editable; edits can create outstanding balances. Source: https://shopify.dev/docs/apps/build/orders-fulfillment/order-management-apps/edit-orders — Accessible, 2026-07-16. [Note] No `OrderEditSession` object exists in current docs — `CalculatedOrder` is the mechanism. [Inference] Importers must re-fetch on `orders/edited`/`orders/updated`; line items and totals are mutable post-import.
- [Open question] Full `OrderSortKeys` enum values (page confirms enum + default `PROCESSED_AT`; individual values not fetched). Incremental sync should use `query: "updated_at:>…"` + cursors regardless.

## 4. 60-day order window and scopes

- [Fact] Order object banner [quote]: "Only the last 60 days' worth of orders from a store are accessible from the Order object by default." Older orders require **`read_all_orders`** combined with `read_orders` or `write_orders`.
- [Fact — Partial sources] Request path: Partner Dashboard → Apps → (app) → API access → "Read all orders" card → Request access with justification; Shopify approval required. Access-scopes doc [quote]: Shopify "will restrict access to scopes for apps that don't have a legitimate use for the associated data." Sources: https://shopify.dev/changelog/apps-now-need-shopify-approval-to-read-orders-older-than-60-days and https://shopify.dev/docs/api/usage/access-scopes — Partial (search summaries), 2026-07-16.
- [Fact] Fulfillment-order scopes exist: `read_assigned_fulfillment_orders`, `read_merchant_managed_fulfillment_orders`, `read_third_party_fulfillment_orders` (access-scopes page). [Blocked] `docs/apps/build/orders-fulfillment/order-management-apps/manage-order-permissions` returned 404 on 2026-07-16 — per-scope semantics for orders re-verified instead via §8 below and the 2026-07-15 Wave-0 capture.

## 5. Abandoned checkouts

Sources: https://shopify.dev/docs/api/admin-graphql/latest/objects/AbandonedCheckout and .../queries/abandonedCheckouts — both Accessible, 2026-07-16.

- [Fact] **`AbandonedCheckout` object exists in 2026-07.** Fields: `abandonedCheckoutUrl` (recovery URL, non-null), `completedAt` [quote: "The date and time when the buyer completed the checkout. Null if the checkout hasn't been completed."] — non-null ⇒ converted to an order; `lineItems` (connection); `totalPriceSet` (includes discounts, shipping, taxes, tips); `customer` (nullable).
- [Fact] **`abandonedCheckouts` query exists.** Filters: `created_at`, `updated_at`, `id`, `email_state` (`sent|not_sent|scheduled|suppressed`), `recovery_state` (`recovered|not_recovered`), `status` (`open|closed`). Sort key: `ID` (default). Scope: `read_orders` (admin-UI parity additionally needs the `manage_abandoned_checkouts` staff permission).
- [Fact] Abandoned-checkout data is protected customer data (PCD) — see the 2026-07-10 capture §7.
- [Open question] No documented direct AbandonedCheckout→Order object reference beyond `completedAt`/`recovery_state`; `abandonedCheckoutsCount` unconfirmed. [Inference] Conversion linking must be done by the connector (e.g. by cart token/customer/time correlation is NOT reliable; the safe design keys on the resulting Order webhook/scan, never on the checkout).

## 6. Fulfillment state models (all four families)

### 6.1 Order-level summary — `OrderDisplayFulfillmentStatus`

Source: https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderDisplayFulfillmentStatus — Accessible, 2026-07-16. 10 values, 3 deprecated:

| Value | Definition [quote] | Status |
|---|---|---|
| `UNFULFILLED` | "None of the items in the order have been fulfilled." | Active |
| `PARTIALLY_FULFILLED` | "Some of the items in the order have been fulfilled." | Active |
| `FULFILLED` | "All the items in the order have been fulfilled." | Active |
| `IN_PROGRESS` | "All of the items in the order have had a request for fulfillment sent to the fulfillment service or all of the items have been marked as in progress." | Active |
| `ON_HOLD` | "All of the unfulfilled items in this order are on hold." | Active |
| `SCHEDULED` | "All of the unfulfilled items in this order are scheduled for fulfillment at later time." | Active |
| `REQUEST_DECLINED` | "Some of the items in the order have been rejected for fulfillment by the fulfillment service." | Active |
| `OPEN` | "None of the items in the order have been fulfilled." | **Deprecated → UNFULFILLED** |
| `PENDING_FULFILLMENT` | request awaits fulfillment-service response | **Deprecated → IN_PROGRESS** |
| `RESTOCKED` | "All the items in the order have been restocked." | **Deprecated → UNFULFILLED** |

[Fact] The field description directs detailed processing state to `FulfillmentOrder`.

### 6.2 FulfillmentOrder

Sources (Accessible, 2026-07-16): objects/FulfillmentOrder, enums/FulfillmentOrderStatus, enums/FulfillmentOrderRequestStatus, enums/FulfillmentOrderAction, objects/FulfillmentHold, enums/FulfillmentHoldReason, objects/FulfillmentOrderAssignedLocation.

- [Fact] `FulfillmentOrderStatus` (7, none deprecated): `OPEN` ("ready for fulfillment"), `SCHEDULED` (deferred until `fulfillAt`), `ON_HOLD`, `IN_PROGRESS`, `INCOMPLETE` ("cannot be completed as requested"), `CLOSED`, `CANCELLED`.
- [Fact] `FulfillmentOrderRequestStatus` (8, none deprecated): `UNSUBMITTED`, `SUBMITTED`, `ACCEPTED`, `REJECTED`, `CANCELLATION_REQUESTED`, `CANCELLATION_ACCEPTED`, `CANCELLATION_REJECTED`, `CLOSED`.
- [Fact] `FulfillmentHold`: `id`, `reason` (FulfillmentHoldReason!), `reasonNotes`, `displayReason`, `heldByApp` (App), `heldByRequestingApp` (Boolean!), `handle` (app-scoped unique). Reasons: `AWAITING_PAYMENT`, `AWAITING_RETURN_ITEMS`, `HIGH_RISK_OF_FRAUD`, `INCORRECT_ADDRESS`, `INVENTORY_OUT_OF_STOCK`, `ONLINE_STORE_POST_PURCHASE_CROSS_SELL`, `UNKNOWN_DELIVERY_DATE`, `OTHER`. Multiple apps can hold the same FO.
- [Fact] `assignedLocation` is a snapshot (name/address fields + live `location` reference that "might be different… if the location's attributes were updated after the fulfillment order was taken into work or canceled"). Assigned location can change (move) only in OPEN/SCHEDULED/ON_HOLD; frozen once IN_PROGRESS/CLOSED/CANCELLED/INCOMPLETE.
- [Fact] `lineItems` carry per-item remaining (unfulfilled) quantities; other fields: `fulfillAt`, `deliveryMethod`, `merchantRequests`, `order`.
- [Fact] `supportedActions` (12, none deprecated): `CREATE_FULFILLMENT`, `REQUEST_FULFILLMENT`, `CANCEL_FULFILLMENT_ORDER`, `REQUEST_CANCELLATION`, `HOLD`, `RELEASE_HOLD`, `MARK_AS_OPEN`, `MOVE`, `MERGE`, `SPLIT`, `EXTERNAL` ("Opens an external URL to initiate the fulfillment process"), `REPORT_PROGRESS`.
- [Fact] `fulfillmentOrderSplit` (input: FO id + line items/quantities; returns new FO + remaining FO + userErrors) and `fulfillmentOrderMove` (`id!`, `newLocationId!`, optional line items → partial move implies split; returns `movedFulfillmentOrder`, `originalFulfillmentOrder`, `remainingFulfillmentOrder` [deprecated field]; fails if FO closed, has manually reported progress, destination lacks inventory, or requestStatus in SUBMITTED/ACCEPTED/CANCELLATION_REQUESTED/CANCELLATION_REJECTED). Scopes: `write_merchant_managed_fulfillment_orders` OR `write_third_party_fulfillment_orders` + fulfill-and-ship permission.
- [Fact] Multi-location: Shopify order routing creates one FO per fulfilling location — multi-location = multiple FOs per order.

### 6.3 Fulfillment

Sources (Accessible, 2026-07-16): objects/Fulfillment, enums/FulfillmentStatus, objects/FulfillmentTrackingInfo.

- [Fact] `FulfillmentStatus`: Active — `SUCCESS`, `CANCELLED`, `ERROR` ("error with the fulfillment request"), `FAILURE` ("the fulfillment request failed"). **Deprecated — `OPEN`, `PENDING`** (legacy pre-FulfillmentOrder values).
- [Fact] Fields (paraphrase): `status`, `displayStatus`, `name` (order-scoped identifier, e.g. #1001.1), `createdAt`/`updatedAt`, `deliveredAt`/`inTransitAt`/`estimatedDeliveryAt`, `trackingInfo` (list: `company`, `number`, `url`; Shopify auto-generates URLs + status updates for 100+ recognized carriers), `fulfillmentLineItems` (links fulfilled quantities to order line items and, via `fulfillmentOrders`, to FO line items), `fulfillmentOrders`, `events`, `service` (FulfillmentService), `location`, `originAddress` ("for tax calculation purposes"), `requiresShipping`, `totalQuantity`, `order`.

### 6.4 FulfillmentEvent (carrier milestones)

Source: enums/FulfillmentEventStatus + mutations/fulfillmentEventCreate — Accessible, 2026-07-16.

- [Fact] `FulfillmentEventStatus` — **11 values, none deprecated**: `LABEL_PURCHASED`, `LABEL_PRINTED`, `READY_FOR_PICKUP`, `CONFIRMED` ("default value when no other information is available"), `CARRIER_PICKED_UP`, `IN_TRANSIT`, `OUT_FOR_DELIVERY`, `ATTEMPTED_DELIVERY`, `DELIVERED`, `DELAYED`, `FAILURE`.
- [Fact] `fulfillmentEventCreate` (scope `write_fulfillments` + fulfill-and-ship permission): requires `fulfillmentId`; optional `status`, `happenedAt`, `estimatedDeliveryAt`, location fields, `message`. Read via `Fulfillment.events`.

### 6.5 Outbound mutations

All Accessible, 2026-07-16:

- [Fact] **`fulfillmentCreate`** is the current recommended mutation. Args: `fulfillment: FulfillmentInput!` (`lineItemsByFulfillmentOrder` — FO id + line items/quantities; [quote] "If you don't specify line items, then the mutation fulfills all items in the fulfillment order"; `trackingInfo`; `notifyCustomer`; `originAddress`) + optional `message`. Scopes: one of `write_assigned_fulfillment_orders` / `write_merchant_managed_fulfillment_orders` / `write_third_party_fulfillment_orders`, plus "fulfill and ship orders" permission. **No idempotency key documented on this page** — [Open question] retry safety is undocumented; connector must dedupe by reading FO line-item remaining quantities before create (feeds DEC-031 Layer 2).
- [Fact] **`fulfillmentCreateV2` is deprecated** [quote: "Deprecated. Use fulfillmentCreate instead."].
- [Fact] `fulfillmentTrackingInfoUpdate` — `fulfillmentId!`, `trackingInfoInput!` (`company`, single `number`/`url` or multi-package `numbers`/`urls`), `notifyCustomer`. Same three write scopes.
- [Fact] `fulfillmentCancel(id!)` — [quote] "When you cancel a fulfillment, the system creates new fulfillment orders for the cancelled items so they can be fulfilled again." [Open question] scopes not listed on the fetched page.
- [Fact] `assignedFulfillmentOrders` query (scope `read_assigned_fulfillment_orders`) covers FOs "set to be fulfilled from locations managed by fulfillment services that are registered by the app" [quote]; merchant-managed FOs (merchant's own locations) need the `*_merchant_managed_fulfillment_orders` pair; third-party FOs need `*_third_party_fulfillment_orders`. [Recommendation] For this connector acting on merchant locations: `read/write_merchant_managed_fulfillment_orders` + `write_fulfillments` (consistent with the 2026-07-15 Wave-0 scope correction).

### 6.6 Fulfillment origin detection (external vs connector-created)

- [Fact — absence] The Fulfillment object has **no app-attribution field** (objects/Fulfillment page, 2026-07-16).
- [Fact] **Order events carry attribution**: `BasicEvent` exposes `attributeToApp` (Boolean!), `attributeToUser` (Boolean!), `appTitle` (String — "The name of the app that created the event."), `author`, `action`, `message`. Source: objects/BasicEvent — Accessible, 2026-07-16.
- [Fact] `FulfillmentHold.heldByApp`/`heldByRequestingApp` give direct hold attribution.
- [Inference] Reliable self-detection = the connector's own durable ledger of fulfillment GIDs returned by its `fulfillmentCreate` calls (primary), plus `Fulfillment.service.handle` (`manual` vs registered service) and order-event attribution (secondary). [Open question] Whether fulfillment webhooks expose the originating API client — not found on fetched pages; verify against a live webhook payload before relying on it.

### 6.7 Fulfillment webhook topics

Source: https://shopify.dev/docs/api/webhooks?reference=toc — Accessible, 2026-07-16 (paraphrase): `fulfillments/create`, `fulfillments/update`; `fulfillment_events/create`, `fulfillment_events/delete`; `fulfillment_holds/added`, `fulfillment_holds/released`; `fulfillment_orders/*` incl. `order_routing_complete`, `placed_on_hold`, `hold_released`, `rescheduled`, `scheduled_fulfillment_order_ready`, `moved`, `split`, `merged`, `cancelled`, `fulfillment_request_submitted/accepted/rejected`, `cancellation_request_submitted/accepted/rejected`, `fulfillment_service_failed_to_complete`, `line_items_prepared_for_local_delivery`, `line_items_prepared_for_pickup`, `progress_reported`, `manually_reported_progress_stopped`. [Open question] Per-topic payload schemas not individually fetched.

## 7. Webhooks vs polling (orders)

Source: https://shopify.dev/docs/apps/build/webhooks — Accessible, 2026-07-16. Quotes:
- "Webhook delivery isn't always guaranteed, and your app can miss or mishandle events for other reasons, such as handler failures or downtime."
- "Shopify doesn't guarantee ordering within a topic, or across different topics for the same resource. For example, it's possible that a `products/update` webhook might be delivered before a `products/create` webhook."
- "Your app shouldn't rely on receiving data from Shopify webhooks" — use "reconciliation jobs to periodically fetch data from Shopify so that your app stays consistent with Shopify's data."
- Dedupe on `X-Shopify-Webhook-Id` (paraphrase). Topics: `orders/create`, `orders/updated`, `orders/edited`.
- [Open question] Current retry schedule not re-verified on the fetched page (the repo's earlier Tier-1 figure is 8 retries/4h; Emipro's 19/48h is outdated — see DP-001).

## 8. Refunds (COD refund visibility)

Source: https://shopify.dev/docs/api/admin-graphql/latest/objects/Refund — Accessible, 2026-07-16.
[Fact] `Refund` = "a financial record of money returned to a customer from an order" [quote]. Fields: `refundLineItems`, `transactions` (OrderTransaction connection — the actual money movement), `totalRefundedSet` (MoneyBag), `note`, `createdAt`, `order` (non-null), `return`, `duties`, `orderAdjustments`. Doc caution: a Refund's existence does not guarantee funds reached the customer — check transaction statuses. [Inference] COD refunds appear as transactions against the manual gateway (`manualPaymentGateway: true`); Odoo-side reconciliation must key off Refund.transactions, not `displayFinancialStatus` alone.

## 9. Inventory model and mutations

Sources (Accessible, 2026-07-16): https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps; objects/InventoryLevel; objects/Location; mutations/inventorySetQuantities; mutations/inventoryAdjustQuantities; mutations/inventoryActivate; mutations/inventoryBulkToggleActivation.

- [Fact] InventoryItem = stockable unit (1:1 ProductVariant); InventoryLevel = quantities of one item at one Location. All **8 quantity names verified current**: `incoming` ("on its way… isn't available to sell until it has been received"), `on_hand` ("total number of units that are physically at a location"), `available` ("inventory that a merchant can sell… isn't committed to any orders"), `committed` ("units that are part of a placed order but aren't fulfilled"), `reserved` ("on-hand units that are temporarily set aside"), `damaged`, `safety_stock`, `quality_control` (all quotes). [Inference] `on_hand = available + committed + reserved + damaged + safety_stock + quality_control`.
- [Fact] InventoryLevel: `quantities(names: [...])`, `item`, `location`, `isActive`, `canDeactivate`; `scheduledChanges` **deprecated** in 2026-07. Scope `read_inventory`.
- [Fact] Location: `isActive`, `activatable`, `deactivatable`, `deactivatedAt`, `fulfillsOnlineOrders`, `hasActiveInventory`, `hasUnfulfilledOrders`, `fulfillmentService`; `shipsInventory` legacy. Scopes: any of `read_locations`/`read_inventory`/`read_markets_home`. Lifecycle mutations: `locationAdd/Edit/Activate/Deactivate`.
- [Fact] **`inventorySetQuantities`** (absolute set; scope `write_inventory`): input `name`, `reason`, `referenceDocumentUri`, `quantities[]` (`inventoryItemId`, `locationId`, `quantity`, optional `compareQuantity`), `ignoreCompareQuantity`. Optimistic concurrency [quotes]: "the mutation will only update the quantity if the persisted quantity matches the `compareQuantity` value"; ignoring it "can lead to inaccurate inventory quantities if multiple requests are made concurrently"; "recommended to always include the `compareQuantity` value." Doc guidance: use only "if calling on behalf of a system that acts as the source of truth for inventory quantities" — else `inventoryAdjustQuantities`. [Note] The repo's 2026-07-10 capture records the CAS field as `compareQuantity`, having replaced `changeFromQuantity` semantics — the live 2026-07 page confirms `compareQuantity` is current.
- [Fact] `inventoryAdjustQuantities` — delta-based (`changes[].delta`), returns `InventoryAdjustmentGroup`.
- [Fact] **Mandatory idempotency:** as of API **2026-04** the `@idempotent` directive with a UUID idempotency key is required at runtime for `inventoryAdjustQuantities`, `inventorySetQuantities`, `inventoryMoveQuantities`, `inventorySetOnHandQuantities`, refund mutations, and inventory shipment/transfer mutations. **Keys retained 24 hours**; duplicates within the window return the cached response without re-executing. Sources: https://shopify.dev/changelog/making-idempotency-mandatory-for-inventory-adjustments-and-refund-mutations and https://shopify.dev/docs/api/usage/idempotent-requests — Accessible, 2026-07-16.
- [Fact] `inventoryActivate(inventoryItemId, locationId, available?, onHand?)` creates an InventoryLevel; `@idempotent` required since 2026-04. `inventoryBulkToggleActivation` — one item across many locations. `inventoryDeactivate(inventoryLevelId)` — semantics corroborated via the bulk page (individual page not fetched).
- [Inference] `inventorySetQuantities` + `compareQuantity` is retry-safe (replay converges or fails compare); `inventoryAdjustQuantities` is inherently non-idempotent (hence the mandatory key); activate/deactivate converge by state.

## 10. Product model and export mutations

Sources (Accessible, 2026-07-16): mutations/productSet; mutations/productCreate; mutations/productVariantsBulkCreate; mutations/publishablePublish.

- [Fact] **`productSet`**: `synchronous` arg (default true); async returns **`ProductSetOperation`** polled via `productOperation`; inside bulk operations `synchronous` is ignored. **Upsert by `identifier`** (`ProductSetIdentifiers`: `id`, `handle`, or `customId`) — built-in duplicate prevention. **List-field semantics [quote]:** "Creates new entries, updates existing entries, and deletes existing entries that aren't included in the mutation's input" (variants/collections/metafields) — declarative/destructive for omitted list entries; omitted non-list fields unchanged. Media via `files`. **Variant limit 2048 per product** (confirmed on productSet and productVariantsBulkCreate pages). [Open question] Synchronous-mode variant threshold (historic 100) not surfaced this pass.
- [Fact] `productCreate` (`ProductCreateInput` + separate `media`): creates only the initial/default variant; products **unpublished by default**; publish via `publishablePublish` (scope `write_publications`; scheduled publishing only for online store). **Variant-creation throttle:** beyond 50,000 store variants, max "1,000 new product variants … per day" [quote]. [Open question] Handle-uniqueness/auto-suffix behavior not verified this pass.
- [Fact] `productVariantsBulkCreate(productId, variants, media?, strategy)` — "By default, stores have a limit of 2048 product variants for each product" [quote]. Companions: `productVariantsBulkUpdate`, `productOptionsCreate/Update/Reorder/Delete`. [Open question] Full strategy enum; `productCreateMedia` vs `fileCreate` deprecation status in 2026-07.
- [Fact] ProductStatus `ACTIVE / DRAFT / ARCHIVED` (referenced via publishablePublish: active status required for visibility).

## 11. Rate limits, bulk operations, API versioning

Sources (Accessible, 2026-07-16): https://shopify.dev/docs/api/usage/limits; /docs/api/usage/bulk-operations/queries; /docs/api/usage/bulk-operations/imports; /docs/api/usage/versioning; /docs/api/admin-graphql (index).

- [Fact] Cost-based leaky bucket: objects 1, connections sized by `first`/`last`, **mutations 10**; both `requestedQueryCost` and `actualQueryCost` computed, actual charged. **Restore rates:** Standard "100 points/second", Advanced "200 points/second", Plus "1000 points/second", Enterprise/Commerce Components "2000 points/second" [quotes]. **Single-query cap [quote]:** "A single query may not exceed a cost of 1,000 points, regardless of plan limits." Throttle: error code `THROTTLED` with `extensions.cost.throttleStatus { maximumAvailable, currentlyAvailable, restoreRate }`; "The recommended backoff time is one second" [quote]. [Open question] Bucket capacities not explicitly quoted this fetch (historically 20× restore rate — do not assert).
- [Fact] Bulk queries: auto-pagination; ≥1 and ≤5 connections, nesting ≤2, no top-level `node/nodes`; since 2026-01 up to **5 concurrent bulk query operations per shop**; completion via `bulk_operations/finish` webhook (delivery not guaranteed — also poll `bulkOperation(id:)`; `currentBulkOperation` deprecated); JSONL with `__parentId`; result URLs "will expire after one week" [quote].
- [Fact] Bulk mutations: JSONL of inputs → `stagedUploadsCreate` → `bulkOperationRunMutation`; one connection field max; per-row validation/errors; 5 concurrent since 2026-01; `@idempotent` in bulk "is applied per row rather than per the entire bulk operation" [quote].
- [Fact] Versioning: quarterly releases (YYYY-01/04/07/10); each stable version supported "a minimum of 12 months" with "at least nine months of overlap"; **unsupported-version behavior [quote]: "If your app targets an inaccessible version, Shopify falls forward and responds using the oldest accessible stable version."** — a silent-behavior-change risk; [Recommendation] pin 2026-07 and monitor the response's API-version header (header name to re-verify). **Latest stable = 2026-07** (endpoint `https://{store}.myshopify.com/admin/api/2026-07/graphql.json`). [Note] One fetch summary produced an implausible "2027-01" artifact — overridden by the reference index page; re-read raw page when this capture is next refreshed.

## 12. Customer/PII essentials (delta to Task-011 capture)

Sources (Accessible, 2026-07-16): objects/Customer; https://shopify.dev/docs/apps/launch/protected-customer-data; https://shopify.dev/docs/apps/build/privacy-law-compliance.

- [Fact] Customer: `email`, `phone`, `firstName/lastName`, `defaultAddress`, `addressesV2`; `state` `ENABLED/INVITED/DISABLED/DECLINED`; `verifiedEmail`, `taxExempt`, `dataSaleOptOut`, `mergeable`, `multipassIdentifier`; lookup via `customerByIdentifier` (email/phone). [Open question] Hard uniqueness enforcement on email/phone not documented on the object page.
- [Fact] PCD: protected fields = name, address, email, phone (Level 2); Level 1 = other customer data. Level 2 adds encrypted backups, test/prod separation, DLP, access logging, incident response; public apps need approval.
- [Fact] Privacy webhooks mandatory for App Store apps: `customers/data_request`, `customers/redact`, `shop/redact`; `shop/redact` "48 hours after" uninstall; `customers/redact` 10 days after request if no order in past six months (else after six months); must 2xx, verify HMAC (401 if invalid), "complete the action within 30 days" [quotes/paraphrase].

## 13. Consolidated open questions from this capture

1. Full `OrderSortKeys` enum values. 2. `orderMarkAsPaid`/`orderCreateManualPayment` exact input shapes (Partial sources). 3. Webhook retry schedule re-verification. 4. AbandonedCheckout→Order linkage beyond `completedAt`. 5. `fulfillmentTrackingInfoUpdateV2` deprecation status; `fulfillmentCancel` scopes. 6. Fulfillment webhook origin/API-client attribution. 7. Per-topic fulfillment webhook payload schemas. 8. Rate-limit bucket capacities per plan. 9. productSet synchronous variant threshold; handle uniqueness; `productCreateMedia` status; variant-bulk strategy enum. 10. customerCreate duplicate email/phone error behavior. 11. fulfillmentCreate retry-safety statement (none exists — design must assume none; DEC-031 Layer 2 input).
