# Source Captures — Orders / Inventory / FulfillmentOrders / Product Mutations / Partner Program / PCD & Webhooks / Odoo 19 / Versioning (2026-07-10)

> **Status: source-material capture per `CLAUDE.md` §7.4. Docs-only.**
> Captured by the 2026-07-10 MVP planning-completion session (AR-042
> candidate) to ground the Task 012–015, Area 6, UI, webhook, UAT, and
> release planning packets. Every claim carries its exact URL, access
> date, and (where version-sensitive) the Shopify Admin API version the
> page rendered. Unless noted otherwise, pages were **Accessible** on
> 2026-07-10 and the API version was **2026-07** (the `latest` alias
> resolved to 2026-07 on every reference page fetched that day).
> Research method: parallel official-source researchers with an
> adversarial verification pass; the session lead independently re-fetched
> the raw HTML of the highest-stakes pages (Partner Program Agreement,
> `InventoryQuantityInput`, `fulfillmentCreate`, `productSet`) and
> confirmed the quoted text/absences by grep. One WebFetch-summarizer
> hallucination ("thirty percent (30%)" in the PPA) was caught and
> disproven against raw text during research — recorded here as a
> methodology caution: load-bearing quotes must be raw-text-verified.

## 1. API versioning baseline

- **[Fact]** Latest stable Admin API version on 2026-07-10 is
  **2026-07**. Quarterly release cadence; "Each stable version is
  supported for a minimum of 12 months, with at least nine months of
  overlap between consecutive versions."
  (https://shopify.dev/docs/api/usage/versioning — 2026-07-10)
- **[Fact]** Supported stable versions on 2026-07-10: 2025-07, 2025-10,
  2026-01, 2026-04, 2026-07. The docs' version pickers additionally list
  2026-10 as release-candidate; 2025-07 reference URLs now serve latest
  content. (same page + version pickers on reference pages — 2026-07-10)
- **[Fact]** "The REST Admin API is a legacy API as of October 1, 2024.
  Starting April 1, 2025, all new public apps must be built exclusively
  with the GraphQL Admin API."
  (https://shopify.dev/docs/api/admin-rest/latest/resources/order — 2026-07-10)
- **[Fact]** GraphQL connections return at most **250** resources per
  page (`first`/`last`); further pages via `pageInfo.hasNextPage` +
  `endCursor` → `after`.
  (https://shopify.dev/docs/api/usage/pagination-graphql — 2026-07-10)

## 2. Orders API (Task 012 load-bearing facts, API 2026-07)

Object page: https://shopify.dev/docs/api/admin-graphql/2026-07/objects/Order (2026-07-10)

- **[Fact]** Identity: `id` (`ID!`), `legacyResourceId`
  (`UnsignedInt64!`, "The ID of the corresponding resource in the REST
  Admin API"), `name` (`String!`, "The unique identifier for the order
  that appears on the order page in the Shopify admin and the Order
  status page").
- **[Fact]** Timestamps: `createdAt`, `processedAt`, `updatedAt` all
  `DateTime!` (ISO 8601). "createdAt … is set when the customer
  completes checkout."
- **[Fact]** Currency: `currencyCode` (`CurrencyCode!` — "The shop
  currency when the order was placed"); `presentmentCurrencyCode`
  (`CurrencyCode!` — "The currency used by the customer when placing the
  order").
- **[Fact]** **Guest orders:** `customer` is nullable — "Returns null if
  an order was created through checkout without customer
  authentication." `email` is nullable — "Returns null if no email was
  provided."
- **[Fact]** `billingAddress` and `shippingAddress` are both nullable
  `MailingAddress` (shipping null for e.g. digital orders).
- **[Fact]** `note` (String, nullable), `tags` (`[String!]!`),
  `sourceName` (String, nullable — "web", "pos", …), `test`
  (`Boolean!` — Bogus Gateway test orders), `taxesIncluded` (`Boolean!`
  — "Whether taxes are included in the subtotal price of the order"),
  `confirmed` (`Boolean!` — "Whether inventory has been reserved"),
  `closed` (`Boolean!`) + `closedAt` (nullable), `cancelledAt`/
  `cancelReason` (nullable).
- **[Fact]** Money (all MoneyBag = shop + presentment amounts):
  `totalPriceSet` (`MoneyBag!`, includes taxes and discounts, before
  returns), `totalShippingPriceSet` (`MoneyBag!`),
  `totalTipReceivedSet` (`MoneyBag!`); `subtotalPriceSet`,
  `totalTaxSet`, `totalDiscountsSet`, `currentTotalDutiesSet`,
  `originalTotalDutiesSet` nullable. Duties are null when not
  applicable; duties arise on international shipments (per-line at
  `LineItem.duties`)
  (https://shopify.dev/docs/apps/build/orders-fulfillment/returns-apps/view-and-refund-duties — 2026-07-10).
- **[Fact]** `taxLines` `[TaxLine!]!`; `TaxLine`: `title` (`String!`),
  `rate`/`ratePercentage` (Float, nullable), `priceSet` (`MoneyBag!` —
  "after discounts and before returns"), `channelLiable` (nullable),
  `source` (nullable).
  (https://shopify.dev/docs/api/admin-graphql/2026-07/objects/TaxLine)
- **[Fact]** `shippingLines` is a paginated `ShippingLineConnection!`;
  `shippingLine` (nullable) is "a summary of all shipping costs".
  `ShippingLine`: `title` (`String!`), `custom` (`Boolean!`), `code`/
  `source`/`carrierIdentifier` nullable, `originalPriceSet` (without
  discounts), `discountedPriceSet` (after discounts),
  `currentDiscountedPriceSet` (after refunds+discounts), own
  `taxLines`/`discountAllocations`.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/objects/ShippingLine)
- **[Fact]** `discountApplications` (`DiscountApplicationConnection!`),
  `discountCodes` (`[String!]!`). Interface fields: `allocationMethod`,
  `index` (`Int!` — precedence), `targetSelection`, `targetType` ("line
  items or shipping lines"), `value` (`PricingValue!`).
  (https://shopify.dev/docs/api/admin-graphql/2026-07/interfaces/DiscountApplication)
- **[Fact]** `displayFinancialStatus` **nullable**; enum values:
  AUTHORIZED, EXPIRED, PAID, PARTIALLY_PAID, PARTIALLY_REFUNDED,
  PENDING, REFUNDED, VOIDED.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/enums/OrderDisplayFinancialStatus)
- **[Fact]** `displayFulfillmentStatus` **non-null**; values: FULFILLED,
  IN_PROGRESS, ON_HOLD, OPEN, PARTIALLY_FULFILLED, PENDING_FULFILLMENT,
  REQUEST_DECLINED, RESTOCKED, SCHEDULED, UNFULFILLED — OPEN,
  PENDING_FULFILLMENT, RESTOCKED documented as replaced/legacy values.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/enums/OrderDisplayFulfillmentStatus)
- **[Fact]** `LineItem`
  (https://shopify.dev/docs/api/admin-graphql/2026-07/objects/LineItem):
  `id` (`ID!`), `name`/`title` (`String!`), `quantity` (`Int!` —
  "including refunded and removed units"), `currentQuantity` (`Int!` —
  "excluding refunded and removed units"), `sku` (nullable), `variant`
  (nullable `ProductVariant`), `product` (nullable `Product`),
  `variantTitle`/`vendor` (nullable), `originalUnitPriceSet`
  (`MoneyBag!` — before discounts), `discountedUnitPriceSet`
  (`MoneyBag!` — "includes line-level discounts … doesn't include
  order-level or code-based discounts"), `discountAllocations`
  (`[DiscountAllocation!]!` — order-level discounts land here),
  `taxLines` (`[TaxLine!]!`), `taxable` (`Boolean!`),
  `customAttributes` (`[Attribute!]!`), `isGiftCard` (`Boolean!`),
  `requiresShipping` (`Boolean!`).
- **[Inference — flagged, not asserted]** A null `variant`/`product`
  most plausibly means a custom line item or a later-deleted
  product/variant; no current GraphQL page states this explicitly. The
  legacy REST Order doc confirms the deletion case ("Can be null if the
  original product … is deleted at a later date"). Must be confirmed
  empirically at implementation time.
- **[Fact]** `orders` query
  (https://shopify.dev/docs/api/admin-graphql/2026-07/queries/orders):
  args `first/last/after/before`, `query` (search syntax), `sortKey`
  (`OrderSortKeys`, default `PROCESSED_AT`; `UPDATED_AT` exists),
  `reverse`, `savedSearchId`. Documented query filters include
  `updated_at`/`created_at` (time comparators, e.g.
  `updated_at:>2019-12-01`), `status` (open/closed/cancelled/not_closed),
  `financial_status`, `fulfillment_status`, `email`, `customer_id`.
- **[Fact]** **60-day window:** "Only the last 60 days' worth of orders
  from a store are accessible from the Order object by default. If you
  want to access older records, then you need to request access to all
  orders … add the `read_all_orders`, `read_orders`, and `write_orders`
  scopes." `read_all_orders` requires an explicit access request via
  the Partner Dashboard (Apps → app → API access → "Read all orders
  scope" → Request access).
  (Order object page + https://shopify.dev/docs/api/usage/access-scopes)
- **[Fact]** `read_orders` governs AbandonedCheckout, **Fulfillment**,
  Order, OrderTransaction, DeliveryCarrierService.
  (https://shopify.dev/docs/api/usage/access-scopes — 2026-07-10)
- **[Fact]** Order also exposes `refunds` (`[Refund!]!`), `returns`
  (connection), `returnStatus`, `totalRefundedSet` — awareness only;
  out of Task 012 scope.
- **[Open question]** No official GraphQL surface identifies an
  individual tip **line item**; `Order.totalTipReceivedSet` is the only
  official aggregate. Treat tip line items as an empirical check.

## 3. Inventory API (Task 013 load-bearing facts, API 2026-07)

- **[Fact]** `ProductVariant.inventoryItem` is `InventoryItem!` — one
  variant → exactly one inventory item. The reverse field
  `InventoryItem.variant` is **deprecated** ("Use `variants` instead" —
  a paginated connection).
  (https://shopify.dev/docs/api/admin-graphql/2026-07/objects/InventoryItem, /objects/ProductVariant)
- **[Fact]** `InventoryItem`: `id` (`ID!`), `sku` (String — "Inventory
  item SKU. Case-sensitive string."), `tracked` (`Boolean!`),
  `unitCost`, `requiresShipping`, `measurement.weight`;
  `inventoryLevel(locationId:)` and paginated `inventoryLevels`.
- **[Fact]** `InventoryLevel` connects exactly one item to one
  location; `quantities(names: [String!]!)` returns the named
  quantities. (https://shopify.dev/docs/api/admin-graphql/2026-07/objects/InventoryLevel)
- **[Fact]** **Eight quantity states:** incoming, available, committed,
  reserved, damaged, safety_stock, quality_control, on_hand.
  `available` = "The inventory that a merchant can sell. Available
  inventory isn't committed to any orders and isn't part of incoming
  transfers." `committed` = "The number of units that are part of a
  placed order but aren't fulfilled."
  **`on_hand` = available + committed + reserved + damaged +
  safety_stock + quality_control** (incoming is NOT part of on_hand).
  `committed` **cannot** be adjusted via the Admin API.
  (https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps
  and …/manage-quantities-states — 2026-07-10)
- **[Fact]** `inventorySetQuantities` sets absolute values with
  compare-and-set; "Only use this mutation if calling on behalf of a
  system that acts as the source of truth for inventory quantities" —
  the correct primary mutation when Odoo is stock master.
  `InventorySetQuantitiesInput.name` accepts **only `available` or
  `on_hand`**; also `reason` (`String!`, documented reason vocabulary)
  and `referenceDocumentUri`.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventorySetQuantities, /input-objects/InventorySetQuantitiesInput)
- **[Fact — version-critical]** In 2026-07,
  `InventoryQuantityInput = {changeFromQuantity: Int, inventoryItemId:
  ID!, locationId: ID!, quantity: Int!}`. `changeFromQuantity` is the
  CAS check — mismatch fails `CHANGE_FROM_QUANTITY_STALE`; **pass null
  to skip**. The older `compareQuantity` + `ignoreCompareQuantity`
  mechanism was deprecated in 2026-01 and **removed in 2026-04**.
  Raw-HTML-verified by the session lead: `changeFromQuantity` present,
  `compareQuantity` absent on the 2026-07 input page.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/input-objects/InventoryQuantityInput;
  legacy: …/2026-01/input-objects/InventorySetQuantitiesInput)
- **[Fact — version-critical]** `inventorySetQuantities` and
  `inventoryAdjustQuantities` support an idempotency key via the
  `@idempotent(key:)` directive as of 2026-01 and **REQUIRE it as of
  2026-04** ("As of 2026-04, the idempotency key is required and must
  be provided using the `@idempotent` directive."). UUID keys
  recommended; key reuse with different parameters fails
  `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`; concurrent duplicates return
  `IDEMPOTENCY_CONCURRENT_REQUEST`.
  (mutation pages + https://shopify.dev/docs/api/usage/idempotent-requests — 2026-07-10)
- **[Fact]** `InventorySetQuantitiesUserErrorCode` (2026-07) includes:
  CHANGE_FROM_QUANTITY_STALE, IDEMPOTENCY_CONCURRENT_REQUEST,
  IDEMPOTENCY_KEY_PARAMETER_MISMATCH, INVALID_INVENTORY_ITEM,
  INVALID_LOCATION, INVALID_NAME, INVALID_QUANTITY_NEGATIVE ("The
  quantity can't be negative."), INVALID_QUANTITY_TOO_HIGH/TOO_LOW
  (±1,000,000,000 bounds), INVALID_REASON, INVALID_REFERENCE_DOCUMENT,
  ITEM_NOT_STOCKED_AT_LOCATION, NON_MUTABLE_INVENTORY_ITEM (e.g. parent
  bundle items).
  (https://shopify.dev/docs/api/admin-graphql/2026-07/enums/InventorySetQuantitiesUserErrorCode)
- **[Open question]** Whether a negative `available` set succeeds
  (INVALID_QUANTITY_NEGATIVE vs the −1B lower bound — which names each
  applies to is undocumented). Dev-store empirical check required.
- **[Fact]** `inventoryAdjustQuantities` applies **deltas**
  (`InventoryChangeInput.delta`), with per-change `changeFromQuantity`
  CAS in 2026-07 and `ledgerDocumentUri` audit refs; recommended when
  the caller is NOT the source of truth.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/mutations/inventoryAdjustQuantities)
- **[Fact]** `inventoryActivate(inventoryItemId!, locationId!,
  available, onHand, …)` creates the InventoryLevel (defaults 0);
  setting quantities at a non-stocked location fails
  `ITEM_NOT_STOCKED_AT_LOCATION`. `inventoryDeactivate(inventoryLevelId!)`
  removes them (check `canDeactivate`/`deactivationAlert` first);
  `inventoryBulkToggleActivation` toggles many locations per item.
  (mutation pages — 2026-07-10)
- **[Fact]** `locations` query: cursor-paginated; active-only by
  default; `includeInactive` / `includeLegacy` (both default false);
  `query` filter and `sortKey` (default NAME). `Location`: `id`,
  `name`, `isActive`, `activatable`, `deactivatable`,
  `fulfillsOnlineOrders`, `hasActiveInventory`, `isFulfillmentService`.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/queries/locations, /objects/Location)
- **[Fact]** Scopes: `read_inventory`/`write_inventory` govern
  InventoryLevel + InventoryItem; `read_locations`/`write_locations`
  govern Location. All five inventory mutations above require
  `write_inventory`. No documented statement that write implies read.
  (https://shopify.dev/docs/api/usage/access-scopes — 2026-07-10)
- **[Fact]** Webhook topics: `INVENTORY_LEVELS_UPDATE`
  (`read_inventory`), `INVENTORY_ITEMS_UPDATE` (`read_inventory` or
  `read_products`), plus LEVELS_CONNECT/DISCONNECT and
  ITEMS_CREATE/DELETE.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/enums/WebhookSubscriptionTopic)
- **[Fact]** Overselling control: `ProductVariant.inventoryPolicy`
  (`ProductVariantInventoryPolicy!`): CONTINUE ("Customers can buy this
  product variant after it's out of stock.") / DENY.
  (https://shopify.dev/docs/api/admin-graphql/2026-07/enums/ProductVariantInventoryPolicy)

## 4. FulfillmentOrders API (Task 014 load-bearing facts, API 2026-07)

- **[Fact]** `FulfillmentOrderStatus` has exactly 7 values: OPEN,
  IN_PROGRESS, SCHEDULED, ON_HOLD, INCOMPLETE, CANCELLED, CLOSED.
  (https://shopify.dev/docs/api/admin-graphql/latest/enums/FulfillmentOrderStatus — rendered 2026-07)
- **[Fact]** `FulfillmentOrderRequestStatus`: UNSUBMITTED is "the only
  valid request status for fulfillment orders that aren't assigned to a
  fulfillment service" (i.e. merchant-managed).
  (…/enums/FulfillmentOrderRequestStatus)
- **[Fact]** `FulfillmentOrder` exposes `assignedLocation`
  (`FulfillmentOrderAssignedLocation!` — snapshot + nullable `location`
  for the live ID; snapshot may diverge once work has begun),
  `lineItems` (paginated; each `FulfillmentOrderLineItem` has `id!`,
  `totalQuantity!`, `remainingQuantity!`, `lineItem!` → order
  LineItem), `supportedActions`, `fulfillmentHolds`. Reading
  FulfillmentOrder requires one of the four fulfillment-order scopes.
  (…/objects/FulfillmentOrder, /objects/FulfillmentOrderAssignedLocation, /objects/FulfillmentOrderLineItem)
- **[Fact]** `Order.fulfillmentOrders` connection supports `displayable`
  (default false; true excludes FOs hidden from merchants) and `query`
  (`id`, `status`, `assigned_location_id`, `updated_at`).
- **[Fact]** **`fulfillmentCreate`** is the current mutation
  (`fulfillmentCreateV2`/`fulfillmentTrackingInfoUpdateV2` deprecated
  as of 2024-10 — "Deprecated. Use fulfillmentCreate instead.").
  `FulfillmentInput`: `lineItemsByFulfillmentOrder`
  (`[FulfillmentOrderLineItemsInput!]!` — pairs of `fulfillmentOrderId`
  + optional `fulfillmentOrderLineItems` `[{id!, quantity!}]`, max 512
  entries; omitting the line list fulfills ALL remaining items; the
  `id` is the **FulfillmentOrder line item ID**, not the order line
  item ID), `trackingInfo` (`FulfillmentTrackingInput`),
  `notifyCustomer` (Boolean, **default false**), `originAddress`.
  Scopes: `write_assigned_fulfillment_orders` OR
  `write_merchant_managed_fulfillment_orders` OR
  `write_third_party_fulfillment_orders` (+ staff permission
  `fulfill_and_ship_orders`).
  (…/mutations/fulfillmentCreate, /input-objects/FulfillmentInput, /input-objects/FulfillmentOrderLineItemsInput, /input-objects/FulfillmentOrderLineItemInput;
  changelog https://shopify.dev/changelog/removing-v2-suffix-from-fulfillmentcreatev2-and-fulfillmenttrackinginfoupdatev2)
- **[Fact]** **Multiple tracking numbers per fulfillment** are
  supported: `FulfillmentTrackingInput.numbers` (`[String!]`) +
  `urls` (`[URL!]`), position-matched; do not combine `number` with
  `numbers` (nor `url` with `urls`). `company` must **exactly match
  (capitalization-sensitive)** Shopify's supported tracking-companies
  list (published on the FulfillmentTrackingInfo reference page,
  anchor `#supported-tracking-companies`) for automatic tracking-URL
  generation; otherwise pass explicit `url`/`urls`.
  (…/input-objects/FulfillmentTrackingInput, /objects/FulfillmentTrackingInfo)
- **[Fact]** `fulfillmentTrackingInfoUpdate(fulfillmentId!,
  trackingInfoInput!, notifyCustomer)` updates tracking on an
  **existing** fulfillment — never creates a second fulfillment. Same
  scopes as fulfillmentCreate.
  (…/mutations/fulfillmentTrackingInfoUpdate)
- **[Fact]** `FulfillmentStatus` active values: SUCCESS, CANCELLED,
  ERROR, FAILURE (OPEN/PENDING deprecated). `Fulfillment.trackingInfo`
  returns company/number/url; the Fulfillment object is readable with
  `read_orders`. (…/enums/FulfillmentStatus, /objects/Fulfillment)
- **[Fact]** **Same-location constraint:** all fulfillment orders in
  one `fulfillmentCreate` must belong to the same order AND be assigned
  to the same location; fulfilling from a different merchant-managed
  location first requires `fulfillmentOrderMove(id!, newLocationId!,
  …)` ("Line items which have already been fulfilled can't be
  re-assigned").
  (https://shopify.dev/docs/apps/fulfillment/order-management-apps/manage-fulfillments; …/mutations/fulfillmentOrderMove)
- **[Fact]** Holds: `fulfillmentOrderHold` → ON_HOLD (since 2025-01 up
  to 10 active holds per app per FO); `fulfillmentOrderReleaseHold`
  releases — omitting `holdIds` releases ALL holds (docs recommend
  explicit ids). (…/mutations/fulfillmentOrderHold, /fulfillmentOrderReleaseHold)
- **[Fact]** Scope semantics: an API client "will only receive a subset
  of the fulfillment orders which belong to an order" without the
  matching scopes. For a merchant-managed store app creating
  fulfillments the core need is
  `read_merchant_managed_fulfillment_orders` +
  `write_merchant_managed_fulfillment_orders`;
  `read_assigned_fulfillment_orders` is for FOs assigned to the app's
  own fulfillment-service locations; since 2024-10
  `write_third_party_fulfillment_orders` no longer allows creating
  fulfillments for FOs assigned to a different fulfillment service app.
  `read_fulfillments`/`write_fulfillments` map to the
  **FulfillmentService** object — confirming TD-002.
  (…/objects/FulfillmentOrder; https://shopify.dev/docs/api/usage/access-scopes)
- **[Fact]** **`fulfillmentCreate` is NOT `@idempotent`.** The
  implementing-idempotency page's supported-mutation list (17
  mutations, page last updated 2026-02-02) contains only inventory*/
  location*/refundCreate mutations — no fulfillment mutation. The
  connector must implement its own duplicate prevention (verification
  read + operation key), exactly as DEC-011/RA-014 already require.
  (https://shopify.dev/docs/api/usage/implementing-idempotency — 2026-07-10)

## 5. Product write mutations (Task 015 load-bearing facts, API 2026-07)

- **[Fact]** `productSet` is a declarative upsert: for **list fields
  (variants, collections, metafields)** it "Creates new entries,
  updates existing entries, and deletes existing entries that aren't
  included in the mutation's input"; omitted **non-list** fields remain
  unchanged. Raw-HTML-verified 2026-07-10.
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet)
- **[Fact]** `productSet` has `synchronous: Boolean` (default true;
  async returns a `ProductSetOperation` to poll via `productOperation`)
  and an `identifier` argument (`ProductSetIdentifiers { customId:
  UniqueMetafieldValueInput, handle: String, id: ID }`). The 2026-07
  page documents **no fixed sync-mode variant-count threshold** (the
  historical "100 variants" wording is absent; guidance is
  timeout-based) — grep-verified. Since 2025-10 productSet enforces a
  max of **50,000 inventory quantities** per call
  (INVENTORY_QUANTITIES_LIMIT_EXCEEDED).
  (same page; https://shopify.dev/changelog/productset-limit-for-inventory-quantities)
- **[Fact]** `productSet` is **not** marked `@idempotent`
  (grep-verified: "idempotent" appears only in nav links). **Zero
  product write mutations** examined (productSet, productCreate,
  productUpdate, productVariantsBulk*, productOptions*, media, publish,
  metafieldsSet, productDelete) carry `@idempotent` — export
  idempotency must come from bindings + declarative semantics.
  (per-mutation pages + https://shopify.dev/docs/api/usage/idempotent-requests — 2026-07-10)
- **[Fact]** `productCreate` creates only the initial/default variant;
  multiple variants require `productVariantsBulkCreate`; products are
  created unpublished — publishing needs `publishablePublish`
  (**`write_publications`**, a separate scope). "For products to be
  visible in a channel, they must have an active ProductStatus."
  (…/mutations/productCreate, /mutations/publishablePublish)
- **[Fact]** `productUpdate` "doesn't support updating product
  variants" — variant writes go through `productVariantsBulkUpdate`
  (per-variant `id` required; `allowPartialUpdates` default false) /
  `productVariantsBulkCreate` / `productVariantsBulkDelete`.
  (…/mutations/productUpdate, /mutations/productVariantsBulkUpdate)
- **[Fact]** `ProductVariantsBulkInput` has price, compareAtPrice,
  barcode, optionValues, mediaId, metafields, inventoryItem,
  inventoryPolicy, inventoryQuantities, taxable — **no direct `sku`
  field**: SKU is written via `inventoryItem.sku`
  (`InventoryItemInput`), weight via `inventoryItem` measurement
  (`InventoryItem.measurement.weight`). On read, `ProductVariant.sku`/
  `barcode` remain non-deprecated.
  (…/input-objects/ProductVariantsBulkInput, /objects/ProductVariant, /objects/InventoryItem)
- **[Fact]** Limits: max **3 options** per product
  (OPTIONS_OVER_LIMIT); **2,048 variants** per product for all
  merchants (changelog 2025-10-15; historical limit 100); ≤250 media
  per product; after a store passes 50,000 variants, ≤1,000 new
  variants/day. No documented per-option value cap.
  (…/mutations/productOptionsCreate;
  https://shopify.dev/changelog/the-product-variant-limit-is-now-2048-for-all-merchants;
  https://help.shopify.com/en/manual/products/variants/add-variants)
- **[Fact]** `ProductStatus`: ACTIVE / DRAFT / ARCHIVED (+ UNLISTED
  from 2025-10). `productChangeStatus` is **deprecated** ("Use
  productUpdate instead."); `productCreateMedia` is **deprecated**
  ("Use productUpdate or productSet instead.") — current media path is
  `fileCreate` (+ `productVariantAppendMedia`/`productVariantDetachMedia`,
  both current). `productDelete` is irreversible; has
  `synchronous:false` mode; docs recommend archive/unpublish instead.
  (…/enums/ProductStatus, /mutations/productChangeStatus, /mutations/productCreateMedia, /mutations/fileCreate, /mutations/productDelete)
- **[Fact]** `metafieldsSet` is an atomic upsert, max 25 metafields per
  call, 10 MB payload, `compareDigest` CAS support.
  (…/mutations/metafieldsSet)

## 6. Partner Program / commercial evidence (OP-45, accessed 2026-07-10)

Primary source: https://www.shopify.com/partners/terms ("Last updated
February 27, 2026") — Accessible, no login wall; **raw HTML re-fetched
and grep-verified by the session lead** (percent inventory: 0%, 15%,
20%, 80%, 200%, 5% — no other percentage figures exist in the
agreement).

- **[Fact]** Registered App Developers owe Shopify **15% of App
  Revenues** (Section C.2.2.1.A): "An App Developer owes Shopify
  fifteen percent (15%) of the total revenues from the sale of,
  subscription to or charges relating to or passing through the App
  Developer's Public Applications."
- **[Fact]** **0% on the first USD $1M lifetime** (earned on/after
  2025-01-01), conditional on prior-calendar-year App Store revenue
  < USD $20M and gross company revenue (with affiliates) < USD $100M;
  "The calculation of App Revenues will not reset annually."
- **[Fact]** One-time non-refundable **USD $19** App Store Registration
  Fee per Partner Account; accepted App Store apps pay a **2.9%
  Processing Fee**.
- **[Fact]** Unregistered developers fall under an **80/20** split
  (Shopify keeps 20% from the first dollar).
- **[Fact]** **Billing obligation is contractual:** "if a Developer
  will create and issue charges to Merchants relating to the Merchants'
  use or installation of the Developer's Application … Developer must
  use the Shopify Billing Resource," unless Shopify agrees otherwise in
  writing (exempted developers remit monthly by wire/ACH and report to
  operationalbilling@shopify.com; audits apply). App Store requirement
  1.2.1: "Your app must use Shopify App Pricing or the Shopify Billing
  API for any app charges."
  (PPA Part C; https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements;
  https://shopify.dev/docs/apps/launch/billing)
- **[Fact]** **Custom-distribution apps cannot use the Billing API**:
  the distribution comparison table states verbatim "Can't use the
  Billing API to charge merchants" for custom-distribution and
  admin-created custom apps; the distribution choice is permanent.
  (https://shopify.dev/docs/apps/launch/distribution — raw-verified)
- **[Official-source finding]** "Managed Pricing" has been renamed
  **Shopify App Pricing**; it is the default for new public apps
  (plans defined in the app submission form, no Billing API code);
  opting in blocks creating new recurring charges via the Billing API;
  direct Billing API use is now filed under "Manual pricing (legacy)"
  but "still supported for existing apps and outlier pricing models."
  (https://shopify.dev/docs/apps/launch/billing/managed-pricing, …/manual-pricing)
- **[Official-source finding]** Enforcement page
  (https://help.shopify.com/en/partners/help-support/faq/removal):
  graduated actions — revoke API access; delist the app (temporarily or
  permanently); suspend app-submission rights; zero out referral
  revenue share; pause payouts; terminate the Partner Account. Notices
  from ecosystem-governance@shopify.com; appeal per the notification.
- **[Fact]** **Anti-duplication:** the PPA prohibits "Create multiple
  Applications that offer substantially the same services" (raw-verified);
  App Store requirement 1.1.5: "App must not be identical to other apps
  you've published to the Shopify App Store."
- **[Official-source finding]** PCD gating recap (distribution-facing):
  public apps request Level 1/Level 2 protected-customer-data access in
  the Partner Dashboard; unapproved fields are redacted; custom apps:
  Level 1 and Level 2 "Always available" (admin-created custom apps
  vary by plan). (https://shopify.dev/docs/apps/launch/protected-customer-data)
- **[Open question]** No official page documents a numeric limit on the
  number of custom apps a partner may create (checked distribution,
  select-distribution-method, revenue-share, help custom-apps pages).
  Do not assert a limit; if load-bearing, confirm via Partner Support.
- **[External validation required]** Partner Dashboard itself is
  login-walled (not accessed, per `CLAUDE.md` §7.6); no dashboard-only
  fee display is believed to exist for the app fee schedule (fully
  public across PPA + shopify.dev + help), but the review-turnaround
  SLA remains undocumented anywhere official.

## 7. Protected customer data + compliance webhooks + webhook mechanics (MBQ-04/OP-40/OP-27, accessed 2026-07-10)

PCD page: https://shopify.dev/docs/apps/launch/protected-customer-data;
compliance: https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance;
webhook mechanics: https://shopify.dev/docs/apps/build/webhooks (+ /subscribe, /verify-deliveries, /delivery-structure).

- **[Fact]** PCD levels: Level 1 = "Customer data excluding name,
  address, phone, and email fields"; Level 2 = customer data including
  any of those four field groups (each Level 2 field needs its own
  field-level request); Level 0 (no customer data) = no action.
- **[Fact — supersedes older repo phrasing]** **"Encrypt data at rest
  and in transit" is a LEVEL 1 requirement** — it applies to any use of
  protected customer data, not only Level 2. Level 2 additionally
  requires: encrypted backups, test/prod data separation, staff-access
  limits, strong staff passwords, an access log to protected customer
  data, and a security incident response policy. (Earlier repo notes
  attributed encryption obligations to Level 2 specifically; the
  current page's own text places encryption at Level 1. Older
  statements should be read as superseded by this capture.)
- **[Fact]** Access by app type: public apps — **requires review** for
  both levels (Partner Dashboard request; unapproved fields are
  redacted; data minimization is the approval gate: "Shopify will
  approve your app to use protected customer data if the requested data
  is the minimum amount required"); **custom apps — "Always available"
  at both levels**; admin-created custom apps — Level 2 "Varies by
  plan". Development-store-only apps need no review submission.
- **[Fact]** Mandatory compliance webhooks (`customers/data_request`,
  `customers/redact`, `shop/redact`) are required for **apps
  listed/distributed through the Shopify App Store** — "Every app
  that's distributed through the Shopify App Store must subscribe" —
  regardless of whether the app collects personal data. Response
  contract: 200-series ack; complete the action within 30 days; return
  **401** on invalid HMAC; missing URLs/behavior → App Store rejection.
  `shop/redact` fires **48 hours after uninstall** (shop_id +
  shop_domain); `customers/redact` fires 10 days after the deletion
  request (withheld until 6 months since last order). Compliance topics
  are configured via the app TOML/Dev Dashboard and **cannot** be
  subscribed via the Admin API.
- **[Inference — flagged]** The compliance mandate's applicability
  wording is exclusively App-Store-scoped; no clause extends it to
  custom apps. A custom-distribution connector is therefore not
  documented as required to implement them — but Shopify "encourages
  all apps to meet protected customer data requirements," and any
  future App Store listing makes them mandatory.
- **[Fact]** Webhook mechanics: HMAC-SHA256 of the **raw body** with
  the app client secret, delivered in `X-Shopify-Hmac-SHA256` (HTTPS
  deliveries only; after client-secret rotation the new secret can take
  up to an hour to be used). Delivery = HTTP POST; 200-range ack
  required (3xx counts as error); **1-second connection / 5-second
  total timeout**; process asynchronously.
- **[Fact]** Retry policy (current): "If Shopify receives no response
  or an error, it retries **8 times over the next 4 hours**. After 8
  consecutive failures, the subscription is automatically deleted **if
  it was configured using the Admin API**" (shop-specific); TOML/
  app-specific subscriptions "will not be deleted by Shopify." The
  older "19 consecutive failures" wording no longer appears anywhere in
  current docs — treat it as legacy.
- **[Fact]** Duplicates are possible ("your app might receive the same
  webhook more than once"); dedupe on `X-Shopify-Webhook-Id` (unique
  per delivery); correlate on `X-Shopify-Event-Id` (shared across
  deliveries from one merchant action). **Ordering is not guaranteed**
  ("it's possible that a products/update webhook might be delivered
  before a products/create webhook") — order by `X-Shopify-Triggered-At`
  or payload timestamps.
- **[Fact]** Reconciliation mandate (verbatim): "Your app shouldn't
  rely on receiving data from Shopify webhooks. Webhook delivery isn't
  always guaranteed … For redundancy, use reconciliation jobs to
  periodically fetch data from Shopify" — the official confirmation of
  the accepted DEC-005 layered posture.
- **[Fact]** Subscription methods: app-specific (TOML
  `[[webhooks.subscriptions]]`, recommended, uniform per install) vs
  shop-specific (`webhookSubscriptionCreate`, SCREAMING_CASE topics,
  per-shop). Payloads are versioned (`[webhooks].api_version` /
  creation-URL version; `X-Shopify-API-Version` header per delivery).
  Google Pub/Sub / EventBridge exist as delivery alternatives.
- **[Fact]** `app/uninstalled` topic: "Occurs whenever a shop has
  uninstalled the app." (https://shopify.dev/docs/api/webhooks?reference=toml)

## 8. Odoo 19 source facts (Tasks 012/013/014 Odoo side; github.com/odoo/odoo branch 19.0, accessed 2026-07-10)

Stock quantities (`addons/stock/models/product.py`, `stock_quant.py`):

- **[Fact]** `product.product`: `qty_available` ("Quantity On Hand"),
  `virtual_available` ("Forecasted Quantity"), `free_qty` ("Free To Use
  Quantity"), `incoming_qty`, `outgoing_qty` — all non-stored computes
  (`_compute_quantities`, `compute_sudo=False`, per-field search
  methods). **`free_qty = qty_available - reserved_quantity -
  expired_unreserved_qty`** (expired term active only with the
  `with_expiration` context); `virtual_available = qty_available +
  incoming_qty - outgoing_qty (- expired)`. `qty_available` sums
  `stock.quant.quantity` over context-resolved internal locations;
  context keys `warehouse_id`/`location` scope it to a subtree
  (recursive-CTE descendants).
- **[Fact]** `stock.quant.available_quantity` is computed exactly as
  `quantity - reserved_quantity` (no expired netting, no UoM rounding
  step) — confirming DEC-015 finding C1's non-equivalence with
  `free_qty`.
- **[Fact]** `stock.warehouse.lot_stock_id` (required, internal usage)
  is the warehouse's main stock location; `view_location_id` is the
  root of its location subtree; per-warehouse aggregation ≙
  `read_group` on `stock.quant` with `('location_id', 'child_of', …)`.
  `stock.location.usage` ∈ supplier/view/internal/customer/inventory/
  production/transit; quants live on non-view leaf locations.

Picking/fulfillment (`stock_picking.py`, `sale_stock/models/stock.py`,
`stock_delivery/models/stock_picking.py`):

- **[Fact]** `stock.picking.state` ∈ draft/waiting/confirmed/assigned/
  done/cancel (stored compute). `button_validate` runs sanity checks,
  returns the `stock.backorder.confirmation` wizard when under-delivered
  (per `picking_type_id.create_backorder` ∈ never/always/ask), then
  `_action_done`. Backorder = copied picking with `backorder_id` set,
  not-done moves transferred.
- **[Fact]** `stock.picking.picking_type_code` related to
  `picking_type_id.code` ∈ incoming/outgoing/internal — deliveries are
  `outgoing`. `sale_id` is a **stored compute** in
  `sale_stock/models/stock.py` (depends `reference_ids.sale_ids` +
  `move_ids.sale_line_id.order_id`) — resolve picking→SO via `sale_id`,
  never via `origin` text.
- **[Fact]** Odoo 19 `stock.move` has `product_uom_qty` ("Demand"),
  `quantity` (done/actual, stored compute with inverse), `product_qty`
  (in product UoM), `picked` Boolean; `stock.move.line.quantity` is the
  done-quantity field — **there is no `qty_done` field in 19.0**.
- **[Fact]** `stock_delivery` adds `carrier_id`
  (Many2one `delivery.carrier`), `carrier_tracking_ref` (Char),
  `carrier_tracking_url` (computed), `delivery_type`, `weight` to
  `stock.picking` — the fields the connector reads for tracking
  write-back (confirming MBQ-39/MBQ-60's basis).

Sale order (`sale/models/sale_order.py`, `sale_order_line.py`,
`sale_stock/models/sale_order.py`):

- **[Fact]** `SALE_ORDER_STATE` = draft ("Quotation"), sent, sale
  ("Sales Order"), cancel — **no `done` state in 19.0**; locking is the
  separate `locked` Boolean (`action_lock`).
- **[Fact]** `partner_id` required; `partner_invoice_id`/
  `partner_shipping_id` are stored, **editable** (`readonly=False`),
  precomputed computes via `partner_id.address_get(['invoice'])` /
  `(['delivery'])` — a connector may write them directly.
  `res.partner.address_get()` DFS-searches typed children
  (type ∈ contact/invoice/delivery/other) and falls back to the partner
  itself when no typed child exists.
- **[Fact]** `currency_id` is a stored compute:
  `pricelist_id.currency_id or company_id.currency_id` — **not
  directly settable**; order currency is controlled by choosing the
  pricelist. `fiscal_position_id`, `team_id`, `warehouse_id`
  (sale_stock) are stored editable computes; `company_id` required.
- **[Fact]** `action_confirm` requires state ∈ {draft, sent}, errors if
  any non-display_type/non-downpayment line lacks `product_id`, writes
  `state='sale'` + `date_order=now`; `sale_stock._action_confirm`
  launches stock rules → creates the delivery picking(s).
- **[Fact]** `sale.order.line`: tax field is **`tax_ids`** (Many2many,
  stored editable compute, domain `type_tax_use='sale'`); UoM field is
  **`product_uom_id`**; `price_unit` is a stored editable compute
  (`readonly=False` — connector-written prices persist); `discount`
  (%) likewise; product-less lines allowed **only** for
  `display_type` ∈ line_section/line_subsection/line_note or
  downpayments (SQL CHECK constraints).
- **[Fact — MBQ-27 core evidence]** `sale.order.amount_tax` is a
  stored compute and `sale.order.tax_totals` is **compute-only (no
  inverse)** — Odoo 19 has **no supported mechanism to force an
  externally-computed tax amount on a sale order**. On **invoices**,
  `account.move.tax_totals` **has an inverse** (`_inverse_tax_totals`)
  that writes a delta onto the first tax line's `amount_currency` —
  i.e. exact Shopify tax amounts are enforceable at invoice level, and
  at order level only indirectly (via matching `account.tax` records).
- **[Fact]** `account.tax.amount_type` ∈ group/fixed/percent/division;
  in 19.0 `price_include` is a **non-stored compute** derived from the
  writable `price_include_override` (∈ tax_included/tax_excluded) and
  the company default — configuration writes must target
  `price_include_override`.
- **[Fact]** `res.currency`: `name` (ISO 4217, size 3), `active`
  Boolean, `rounding` (default 0.01); activation = toggling Active
  (Accounting → Configuration → Currencies).

Platform:

- **[Fact]** `ir.cron` 19.0: `interval_number`/`interval_type`/
  `nextcall`/`priority`; **no `numbercall`/`doall` fields**;
  `_trigger(at=None)` schedules an immediate or at-time run (the
  supported "wake the drain now" mechanism); `failure_count` +
  `first_failure_date` **auto-deactivate a job after ≥5 consecutive
  failures spanning >7 days** — connector cron entry points must never
  raise repeatedly.
- **[Fact]** `uom.uom` 19.0 has **no `category_id`** (and no
  `uom_type`/`factor_inv`): units chain via `relative_uom_id` +
  `relative_factor`; `_compute_quantity(qty, to_unit)` converts by
  factor ratio; all UoMs share the "Product Unit" rounding precision.
- **[Fact]** `res.config.settings` is a TransientModel (persists only
  via config_parameter/defaults/groups/modules) — per-store persistent
  settings require a dedicated model, confirming the merged
  `shopify.connector.store.settings` design.

## 9. Versioning / scopes / rate limits / bulk operations sweep (accessed 2026-07-10)

- **[Fact]** Released, accessible stable versions today: 2025-07
  (inaccessible after **July 16, 2026** — six days from capture),
  2025-10, 2026-01, 2026-04, **2026-07** (latest; supported until July
  16, 2027). 2026-10 is the current release candidate. Requests to
  retired versions "fall forward" to the oldest accessible stable;
  `X-Shopify-API-Version` reports the served version.
  (https://shopify.dev/docs/api/usage/versioning)
- **[Fact]** Shopify **no longer publishes per-version release notes**
  — the developer changelog is the authoritative record
  (https://shopify.dev/docs/api/release-notes: "We're no longer
  publishing API release notes.").
- **[Fact]** Changelog items material to this connector: 2026-01 —
  `@idempotent` optional on refundCreate + inventory mutations;
  `changeFromQuantity` CAS redesign; `InventoryItem.variant`
  deprecation; CalculatedOrder no longer returned for committed order
  edits. 2026-04 — `@idempotent` **mandatory** (Action Required);
  `fulfillmentOrderReportProgress` added; typed user errors on
  fulfillmentOrderCancel/Move. 2026-07 — new multi-source Collection
  model (collections using new features are **filtered out** of
  pre-2026-07 API versions); Order.channelInformation deprecated.
  2026-10 (RC) — `OrderDisplayFulfillmentStatus` gains
  `FULFILLMENT_NOT_REQUIRED` (exhaustive status handling must update);
  `ITEM_NOT_STOCKED_AT_LOCATION` removed from inventory APIs.
  (individual changelog posts, all fetched 2026-07-10)
- **[Fact]** GraphQL rate limiting: calculated query cost; leaky
  bucket per app+store; restore rates **100 / 200 / 1000 / 2000
  points/s** (Standard / Advanced / Plus / Enterprise); **single-query
  hard cap 1,000 points** (MAX_COST_EXCEEDED in a 200 body); costs:
  scalar/enum 0, object 1, connection sized by first/last, mutation 10;
  requested-vs-actual cost refund; response `extensions.cost.
  throttleStatus {maximumAvailable, currentlyAvailable, restoreRate}`;
  **THROTTLED surfaces in the body with HTTP 200** ("Similar to 429");
  recommended backoff 1 second. **Per-plan bucket maxima are not
  published** — read `maximumAvailable` at runtime (settles the OP-34/
  Q15 documentation question as "officially unpublished by design").
  (https://shopify.dev/docs/api/usage/limits;
  https://shopify.dev/docs/api/admin-graphql/latest)
- **[Fact]** Input arrays max **250 items**; connection pages max 250;
  variant-creation throttle: >50,000 store variants → ≤1,000 new
  variants/day (not on Plus).
- **[Fact]** Scope catalogue confirmations
  (https://shopify.dev/docs/api/usage/access-scopes):
  `read_orders`/`write_orders` → AbandonedCheckout, Fulfillment, Order,
  OrderTransaction, DeliveryCarrierService; `read_all_orders` → lifts
  the 60-day window, Partner-Dashboard approval required;
  `read_products`/`write_products` → Product, ProductVariant,
  Collection, ResourceFeedback, SellingPlan;
  `read_customers`/`write_customers` → Customer, Segment, Company,
  CompanyLocation; `read_inventory`/`write_inventory` → InventoryLevel,
  InventoryItem; `read_locations`/`write_locations` → Location;
  **`read_fulfillments`/`write_fulfillments` → FulfillmentService
  (verbatim table row — the definitive TD-002 confirmation)**; the
  `*_fulfillment_orders` family → FulfillmentOrder.
  `write_publications` is required by `publishablePublish` although
  absent from the catalogue table.
- **[Fact]** Bulk operations: from 2026-01, up to **five concurrent
  bulk query operations** per shop (pre-2026-01: one per type — the
  page's own "Rate limits" section still carries the stale one-per-type
  wording, an internal doc inconsistency); poll via `bulkOperation(id:)`
  (`currentBulkOperation` deprecated); execution exempt from rate
  limits; JSONL results with `__parentId`; `bulk_operations/finish`
  webhook (lowercase payload status); 10-day completion limit; max five
  connections / two nesting levels.
  (https://shopify.dev/docs/api/usage/bulk-operations/queries)

## 10. Verification record

Twenty-four load-bearing claims across all eight research areas were
adversarially re-verified by independent fact-checkers on 2026-07-10
(each instructed to refute the claim against a fresh fetch of the
official source): **24/24 CONFIRMED, zero refuted, zero unverifiable.**
The session lead additionally raw-fetched and grep-verified: the
Partner Program Agreement percentage inventory (0/15/20/80/200/5 — no
other percentages exist in the document), `InventoryQuantityInput`
(2026-07: `changeFromQuantity` present, `compareQuantity` absent),
`fulfillmentCreate` (three write fulfillment-order scopes named;
`fulfillmentCreateV2` present only as a nav link), and `productSet`
(list-field delete-on-omit wording present; "idempotent" present only
in nav links). Known residual gaps are recorded inline above as
[Open question] / [Inference] / [External validation required] items —
none is load-bearing for the Phase C/D planning decisions without being
flagged in the consuming packet.
