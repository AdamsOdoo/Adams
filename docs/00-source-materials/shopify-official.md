# Captured Source Material — Official Shopify Documentation

> High-value excerpts from official Shopify developer documentation
> (`shopify.dev`), captured so the research survives link rot. **All captured
> 2026-06-30.** Each block marks **quote** vs **paraphrase** and cites the exact
> URL. These are **Tier-1 facts** (per `../01-research/research-methodology.md`
> §1). Analysis lives in
> [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md);
> this file is evidence only. Excerpts may be lightly trimmed; verify verbatim
> against the live page before quoting in a legal/compliance context.

## REST vs GraphQL strategy

- **[quote]** "All apps and integrations should be built with the GraphQL Admin
  API. The REST Admin API is a legacy API as of October 1, 2024."
  — https://shopify.dev/docs/apps/build/graphql/migrate
- **[quote]** "The REST Admin API is in maintenance mode and receives only
  critical updates, and new Shopify features and improvements are released in
  GraphQL first." — https://shopify.dev/docs/apps/build/graphql/migrate
- **[quote]** "Starting April 1 2025, all new public apps submitted to the App
  Store after this date must only use GraphQL." (Changelog published 2024-10-01.)
  — https://shopify.dev/changelog/starting-april-2025-new-public-apps-submitted-to-shopify-app-store-must-use-graphql

## API versioning

- **[quote]** "Shopify releases a new API version every three months at the
  beginning of the quarter, at 5pm UTC."
  — https://shopify.dev/docs/api/usage/versioning
- **[quote]** "Version names are date-based (for example, `2026-04`)."
  — https://shopify.dev/docs/api/usage/versioning
- **[quote]** "Each stable version is supported for a minimum of 12 months, with
  at least nine months of overlap between consecutive versions."
  — https://shopify.dev/docs/api/usage/versioning
- **[quote]** "If your app targets an inaccessible version, Shopify falls forward
  and responds using the oldest accessible stable version. For example, requests
  to a retired 2026-10 are served as 2027-01."
  — https://shopify.dev/docs/api/usage/versioning
- **[quote]** "Deprecated fields or types are removed in a subsequent
  release—for example, something deprecated in `2026-10` might be removed in
  `2027-01`." — https://shopify.dev/docs/api/usage/versioning
- **[quote]** "If your app continues to use unsupported resources after the
  upgrade deadline, it's delisted from the Shopify App Store."
  — https://shopify.dev/docs/api/usage/versioning
- **[paraphrase]** The API health report shows deprecated calls and the deadline
  to update them; it monitors a rolling 14-day window and reads OK when no
  deprecated calls were made in the last 14 days.
  — https://shopify.dev/docs/api/usage/versioning/api-health

## Authentication and scopes

- **[quote]** "Authorization is the process of giving permissions to apps. When
  an app user installs a Shopify app they authorize the app, enabling the app to
  acquire an access token."
  — https://shopify.dev/docs/apps/build/authentication-authorization
- **[paraphrase]** Apps rendered in the Shopify admin should use token exchange;
  standalone apps use the authorization code grant. Whenever possible, build
  admin-rendered apps using Shopify managed installation and token exchange.
  — https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens
- **[paraphrase]** A session token's lifetime is one minute; session tokens are
  for authentication and can't be used to make authenticated requests to Shopify
  APIs.
  — https://shopify.dev/docs/apps/build/authentication-authorization/session-tokens
- **[paraphrase]** Apps should request only the minimum data necessary. By
  default apps have no access to protected customer data; `read_customers`,
  `read_orders`, `read_all_orders` require meeting the protected-customer-data
  requirements. — https://shopify.dev/docs/api/usage/access-scopes

## Rate limits and throttling

- **[quote]** "GraphQL Admin API | Calculated query cost | 100 points/second |
  200 points/second | 1000 points/second | 2000 points/second" (Standard /
  Advanced / Plus / Enterprise restore rates).
  — https://shopify.dev/docs/api/usage/limits
- **[quote]** "A single query may not exceed a cost of 1,000 points, regardless
  of plan limits. This limit is enforced before a query is executed based on the
  query's requested cost." — https://shopify.dev/docs/api/usage/limits
- **[paraphrase]** Standard plan REST Admin API bucket size is 40 requests per
  app per store with a leak rate of 2/second; Shopify Plus increases this 10× to
  400 requests with a leak rate of 20/second; 429 responses include `Retry-After`
  and `X-Shopify-Shop-Api-Call-Limit` (e.g. `32/40`).
  — https://shopify.dev/docs/api/admin-rest/usage/rate-limits
- **[quote]** "Each combination of app and store is given a bucket size and
  restore rate based on API and plan tier."
  — https://shopify.dev/docs/api/usage/limits
- **[paraphrase]** The example `extensions.cost` payload shows `requestedQueryCost:
  101, actualQueryCost: 46, throttleStatus { maximumAvailable: 1000,
  currentlyAvailable: 954, restoreRate: 50 }` — these are illustrative example
  values, **not** declared per-plan bucket sizes/restore rates.
  — https://shopify.dev/docs/api/usage/limits

## GraphQL query cost

- **[paraphrase]** Field costs by return type: Scalar = 0, Enum = 0, Object = 1,
  Interface/Union = maximum of possible selections, Connection = sized by `first`/
  `last`, Mutation = 10. Shopify reserves the right to set manual costs on fields.
  — https://shopify.dev/docs/api/usage/limits
- **[quote]** "Before execution begins, an app's bucket must have enough capacity
  for the requested cost of a query. When execution is complete, the bucket is
  refunded the difference between the requested cost and the actual cost of the
  query." — https://shopify.dev/docs/api/usage/limits

## Bulk operations

- **[paraphrase]** Before API version 2026-01 you can run only one bulk operation
  of each type at a time per shop; in 2026-01+ apps can run up to five bulk query
  and five bulk mutation operations at a time per shop.
  — https://shopify.dev/docs/api/usage/bulk-operations/imports
- **[quote]** "The URL that points to the response data in JSONL format. The URL
  expires 7 days after the operation completes."
  — https://shopify.dev/docs/api/admin-graphql/latest/objects/BulkOperation
- **[paraphrase]** A bulk query must complete within 10 days; a bulk import JSONL
  can't exceed 100 MB and must complete within 24 hours, or it is marked failed.
  — https://shopify.dev/docs/api/usage/bulk-operations/queries

## Webhooks and reconciliation

- **[quote]** "Webhook delivery isn't always guaranteed, and your app can miss or
  mishandle events for other reasons, such as handler failures or downtime. Your
  app shouldn't rely on receiving data from Shopify webhooks; for redundancy, use
  reconciliation jobs to periodically fetch data from Shopify so that your app
  stays consistent with Shopify's data."
  — https://shopify.dev/docs/apps/build/webhooks/best-practices
- **[quote]** "Shopify has a one-second connection timeout and a five-second
  timeout for the entire request. If delivery fails, it retries 8 times over the
  next 4 hours. After eight consecutive failures, the subscription is
  automatically deleted if it was configured using the Admin API."
  — https://shopify.dev/docs/apps/build/webhooks/subscribe/https
- **[paraphrase]** Each HTTPS delivery includes a base64 HMAC in the
  `X-Shopify-Hmac-SHA256` header; verify by computing HMAC-SHA256 of the **raw**
  request body using the app's client secret, always before processing; use
  `X-Shopify-Webhook-Id` to deduplicate.
  — https://shopify.dev/docs/apps/build/webhooks/verify-deliveries
- **[paraphrase]** App-Store apps must implement `customers/data_request`,
  `customers/redact`, `shop/redact`, verify HMAC (401 if invalid), respond 2xx,
  and complete the action within 30 days; `shop/redact` is sent 48 hours after
  uninstall. — https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance

## Products and variants

- **[quote]** "By default, stores have a limit of 2048 product variants for each
  product." — https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant
- **[quote]** "It is now possible for all Shopify merchants to create products
  with up to 2,048 variants, exceeding our historical variant limit of 100."
  (Effective October 15, 2025.)
  — https://shopify.dev/changelog/the-product-variant-limit-is-now-2048-for-all-merchants
- **[paraphrase]** `productSet` creates/updates a whole product in one request;
  for list fields (variants, collections, metafields) it creates new entries,
  updates existing ones, and **deletes omitted entries**; `synchronous: false`
  returns a `ProductSetOperation` polled via `productOperation`.
  — https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet

## Inventory, locations, levels

- **[quote]** "The on_hand state equals the sum of inventory quantities in the
  following states: available, committed, reserved, damaged, safety_stock,
  quality_control."
  — https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states
- **[quote]** "You can't use the Admin API to adjust or move inventory quantities
  in the committed state. Inventory quantities in the committed state are only
  affected by the creation and fulfillment of a merchant's orders."
  — https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states
- **[paraphrase]** `inventorySetQuantities` sets `available`/`on_hand` to an
  absolute value and by default only updates if the persisted quantity matches
  `compareQuantity`; setting `ignoreCompareQuantity: true` skips the check and can
  produce inaccurate quantities under concurrency. As of 2026-04, set/adjust
  mutations require an idempotency key via `@idempotent`.
  — https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities

## Orders and protected data

- **[quote]** The `read_all_orders` scope grants access to "All relevant orders
  rather than the default window of orders created within the last 60 days," and
  "You need to request permission for this access scope from your Partner
  Dashboard before adding it to your app."
  — https://shopify.dev/docs/api/usage/access-scopes
- **[paraphrase]** Orders, draft orders, abandoned checkouts, refunds, and
  transactions are protected customer data; protected fields requiring individual
  approval are Name, Address, Email, and Phone; Shopify approves the minimum data
  required for the app's functionality.
  — https://shopify.dev/docs/apps/launch/protected-customer-data

## Fulfillment and tracking

- **[paraphrase]** By API version 2023-07 all apps should use the FulfillmentOrder
  object; using the Order and Fulfillment objects is a legacy workflow no longer
  supported as of API version 2022-07.
  — https://shopify.dev/docs/apps/build/orders-fulfillment/migrate-to-fulfillment-orders
- **[quote]** "Creates a fulfillment for one or more FulfillmentOrder objects. Use
  this mutation to mark items as fulfilled when they're ready to ship. If you
  don't specify line items, then the mutation fulfills all items in the
  fulfillment order."
  — https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentcreate

## Refunds and returns

- **[paraphrase]** The existence of a Refund object doesn't guarantee money was
  returned; the actual status is determined through the refund's transactions
  (pending/processing/successful/failed).
  — https://shopify.dev/docs/api/admin-graphql/latest/objects/Refund
- **[paraphrase]** `returnCreate` creates an already-approved OPEN return;
  `returnApproveRequest` sets a REQUESTED return's status to OPEN. `Return.status`
  ∈ {REQUESTED, OPEN, CLOSED, DECLINED, CANCELED}.
  — https://shopify.dev/docs/api/admin-graphql/latest/objects/Return

## Transactions and payouts

- **[quote]** "AUTHORIZATION: An amount reserved against the cardholder's funding
  source. … CAPTURE: A transfer of the money that was reserved by an
  authorization. SALE: An authorization and capture performed together in a single
  step. REFUND: A partial or full return of captured funds … A refund can happen
  only after a capture is processed. VOID: A cancelation of an authorization
  transaction." — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderTransactionKind
- **[quote]** "A transfer of funds between a merchant's Shopify Payments balance
  and their ShopifyPaymentsBankAccount. Requires: the user must have access to
  payouts." — https://shopify.dev/docs/api/admin-graphql/latest/objects/shopifypaymentspayout

## App Store / review readiness

- **[quote]** "Your app must immediately authenticate using OAuth before any
  other steps occur, even if the merchant has previously installed and then
  uninstalled your app."
  — https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements
- **[quote]** "As of April 1, 2025 all new public apps must be built exclusively
  with the GraphQL Admin API."
  — https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements
- **[paraphrase]** Built for Shopify admin performance (75th percentile / 28 days,
  min 100 calls): LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms; checkout needs ≥1,000
  requests over 28 days with p95 ≤ 500ms and a 0.1% failure rate.
  — https://shopify.dev/docs/apps/launch/built-for-shopify/requirements
