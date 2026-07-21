# Wave 4 — Official Shopify FulfillmentOrder Source Refresh (Gate A)

> **Status: CANDIDATE — Gate A Phase 2 output, pending control-room acceptance.**
> Current official Shopify Admin GraphQL evidence for Wave 4 fulfillment, verified
> against **Admin API version 2026-07** (the current stable version), **accessed
> 2026-07-21**, from `shopify.dev` only (no blogs, community, or model memory).
> Where a fact is inferred or a source could not be isolated, it is marked. This
> file authorizes no implementation.

**Method.** Each Layer-A enum, the FulfillmentOrder/Fulfillment objects, the
create/track mutations, the idempotency directive, the fulfillment scopes + staff
permission, and the rate-limit model were fetched from their `shopify.dev`
reference pages. Every claim carries its exact URL. Verified independently of the
in-repo captures.

---

## 1. API version discipline

- **[Fact, 2026-07]** The current stable Admin API version is **2026-07**;
  every fulfillment reference page renders under `2026-07` and the endpoint form
  is `https://{store}.myshopify.com/admin/api/2026-07/graphql.json`.
  `https://shopify.dev/docs/api/admin-graphql/latest` → 2026-07.
- **[Fact]** Versions are date-based `YYYY-MM`, released quarterly (Jan/Apr/Jul/
  Oct 1, 17:00 UTC); each stable version is supported ≥12 months with ≥9 months
  overlap; unsupported-resource calls after an upgrade deadline risk App-Store
  delisting. `https://shopify.dev/docs/api/usage/versioning`.
- **Implication (Wave 4):** pin the connector to an explicit version string
  (`2026-07`), **not `latest`**; schedule annual re-validation before the pinned
  version's window closes; monitor deprecation warnings. Enum sets
  (`FulfillmentOrderStatus`, `FulfillmentOrderAction`) can gain values across
  versions — the unknown-future-value contract (status model §7) is required.

---

## 2. Access scopes + staff permission (D-014-2 / DEC-033 confirmed)

- **[Fact]** The merchant-managed scopes are exactly
  **`read_merchant_managed_fulfillment_orders`** and
  **`write_merchant_managed_fulfillment_orders`**; all fulfillment-order scopes
  govern the single Access resource `FulfillmentOrder`.
  `https://shopify.dev/docs/api/usage/access-scopes`.
- **[Fact]** Reading a `FulfillmentOrder` requires **one of**
  `read_assigned_fulfillment_orders`, `read_merchant_managed_fulfillment_orders`,
  `read_third_party_fulfillment_orders`, or `read_marketplace_fulfillment_orders`
  (object "Access" note). `read_merchant_managed_fulfillment_orders` alone
  suffices to read merchant-managed FOs.
  `https://shopify.dev/docs/api/admin-graphql/latest/objects/FulfillmentOrder`.
- **[Fact]** `fulfillmentCreate` requires **one of**
  `write_assigned_fulfillment_orders`, `write_merchant_managed_fulfillment_orders`,
  or `write_third_party_fulfillment_orders` — **which one depends on the FO's
  assigned location**. Hence `write_merchant_managed_fulfillment_orders` is
  **conditionally required**: only when the connector creates fulfillments at
  merchant-managed locations (the Odoo-as-source case). A read-only sync needs no
  write scope. `https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentCreate`.
- **[Fact — distinct authorization axis]** `fulfillmentCreate` **also** requires
  the acting user to hold the Shopify **staff permission `fulfill_and_ship_orders`**
  — separate from, and additional to, the OAuth access scope. A scope-only
  checklist is insufficient for fulfillment writes. (Same page.) The full
  staff-permission definition lives in the Shopify Help Center, outside
  `shopify.dev` — recorded as an **open item** (not fetched under the
  shopify.dev-only rule).
- **[Fact]** Legacy `read_fulfillments`/`write_fulfillments` map to the
  **`FulfillmentService`** resource (registering/operating a fulfillment service),
  **not** the FulfillmentOrder object — confirming DEC-033 §6 / D-014-2. They also
  act as the prerequisite that unlocks the granular FO scopes
  (`migrate-to-fulfillment-orders`).
- **[Fact]** Missing a fulfillment-order scope **does not error** — it silently
  omits those FOs from results. **Implication:** if a merchant routes some orders
  to third-party/service locations, holding only `read_merchant_managed_*` yields
  a partial FO set; reconciliation must account for this (surface, do not treat as
  "no fulfillment orders"). As of **2024-10**, `write_third_party_fulfillment_orders`
  no longer lets order-management apps create fulfillments for FOs assigned to a
  different fulfillment-service app — further isolating `write_merchant_managed_*`
  as the connector's write scope.

**Reconciliation:** D-014-2 / DEC-033 §6 scope correction is **confirmed exact**.
Add the `fulfill_and_ship_orders` **staff-permission** axis to the readiness and
test contract (it is distinct from the API scope — a Gate A addition).

---

## 3. FulfillmentOrder object, states, line items

- **[Fact]** Identifiers: `id: ID!`, `orderId: ID!`, `order: Order!`. One Order →
  **many** FulfillmentOrders. The object groups items "expected to be fulfilled
  from the same location," and **"There can be more than one fulfillment order for
  an order at a given location."**
  `.../objects/FulfillmentOrder`, `.../objects/Order` (`fulfillmentOrders`
  connection).
  - **Reconciliation note:** the modes/packet phrasing "one FO per fulfilling
    location" is a **simplification** — Shopify permits **>1 FO per location**.
    Wave 4 must iterate over **all** of an order's FulfillmentOrders and never
    assume one-FO-per-location (strengthens RA-023). → DEC-038.
- **[Fact]** `FulfillmentOrder.status: FulfillmentOrderStatus!` — exactly **7**
  values (EXACT-MATCH to status-model A2): `OPEN` ("ready for fulfillment"),
  `IN_PROGRESS` ("being processed"), `ON_HOLD` ("can't be initiated until the hold
  is released"), `SCHEDULED` ("deferred… after `fulfill_at`"), `INCOMPLETE`
  ("cannot be completed as requested"), `CLOSED` ("completed and closed"),
  `CANCELLED` ("cancelled by the merchant"). `.../enums/FulfillmentOrderStatus`.
- **[Fact]** `requestStatus: FulfillmentOrderRequestStatus!` — **8** values
  (EXACT-MATCH to A3). For merchant-managed FOs not assigned to a fulfillment
  service, `requestStatus` is always **`UNSUBMITTED`** — so **fulfillment
  eligibility must key off `status` (OPEN/IN_PROGRESS), not `requestStatus`**.
  `.../enums/FulfillmentOrderRequestStatus`.
- **[Fact]** `assignedLocation: FulfillmentOrderAssignedLocation!` — its
  `location: Location` field **is nullable** (location may be deleted/altered
  after the FO was taken into work); it also carries snapshot fields
  (`name: String!`, `address1/2`, `city`, `countryCode: CountryCode!`, `province`,
  `zip`, `phone`). `.../objects/FulfillmentOrderAssignedLocation`.
  - **Reconciliation note:** DEC-011/D-014-5 treat the live `assignedLocation`
    read as authoritative; Gate A adds that **`assignedLocation.location` can be
    null** and the resolver must fall back to the snapshot fields → DEC-038.
- **[Fact]** The FO line-item connection field is **`lineItems`**
  (`FulfillmentOrderLineItemConnection!`) — **not** `fulfillmentOrderLineItems`
  (that is REST-resource style). Node type = `FulfillmentOrderLineItem`.
  `.../objects/FulfillmentOrder`.
- **[Fact]** `FulfillmentOrderLineItem`: `id: ID!`, `lineItem: LineItem!`,
  `remainingQuantity: Int!` ("units remaining to be fulfilled"),
  `totalQuantity: Int!`, plus `inventoryItemId`, `sku`, `productTitle`.
  **Partial fulfillment is driven by `remainingQuantity`** (not `totalQuantity`).
  `.../objects/FulfillmentOrderLineItem`.
- **[Fact]** `supportedActions: [FulfillmentOrderSupportedAction!]!` — the
  authoritative, state-derived set of legal actions. `FulfillmentOrderAction`
  includes `CREATE_FULFILLMENT`, `REQUEST_FULFILLMENT`, `HOLD`, `RELEASE_HOLD`,
  `MOVE`, `MERGE`, `SPLIT`, `CANCEL_FULFILLMENT_ORDER`, `MARK_AS_OPEN`,
  `REPORT_PROGRESS`, `REQUEST_CANCELLATION`, `EXTERNAL`. The enum text still names
  `CREATE_FULFILLMENT`'s mutation as `fulfillmentCreateV2` (doc-lag; the current
  mutation is `fulfillmentCreate`). `.../enums/FulfillmentOrderAction`.
  - **Gate A recommendation:** gate `fulfillmentCreate` on **`supportedActions`
    containing `CREATE_FULFILLMENT`** (runtime-authoritative), in addition to the
    client-side `status ∈ {OPEN, IN_PROGRESS}` filter — defense-in-depth beyond
    the status whitelist. No single official page prints a status-eligibility
    table, so `supportedActions` is the correct gate. → DEC-038.
- **[Fact]** Fetch query: `order(id){ fulfillmentOrders(first:N, query:"…"){ … } }`
  with `displayable`/`query` (`status`, `assigned_location_id`, `updated_at`) args;
  a root-level `fulfillmentOrders` query returns the app-scoped paginated set.
  `.../objects/Order`.

### 3.1 FO lifecycle mutations relevant to eligibility (read-only posture)

- **[Fact]** `SCHEDULED → OPEN` is time-driven at `fulfillAt` (auto);
  `fulfillmentOrderOpen` forces it open. `fulfillmentOrderClose` (IN_PROGRESS →
  INCOMPLETE, requestStatus CLOSED) returns control to the merchant — INCOMPLETE
  is **not a dead end** (a successor OPEN FO may appear). `fulfillmentOrderCancel`
  (SUBMITTED/CANCELLATION_REQUESTED) creates a **replacement OPEN FO** for the
  remaining work. `.../mutations/fulfillmentOrderOpen|Close|Cancel`.
  - **Implication:** the connector's reconciliation must **follow successor/
    replacement FOs** and re-read `status`, not infer terminal state from a status
    snapshot. Holds are **read-only** in Wave 4 (D-014-5) — `fulfillmentHolds`
    (`reason`, `displayReason`, `heldByRequestingApp`) are surfaced, not written.

---

## 4. Mutations: create / tracking + idempotency

- **[Fact]** `fulfillmentCreate(fulfillment: FulfillmentInput!, message: String)`
  is the **current, non-deprecated** create mutation; payload = `{ fulfillment,
  userErrors: [UserError!]! }`. It "creates a fulfillment for one or more
  FulfillmentOrder objects associated with the **same Order and Location**."
  `.../mutations/fulfillmentCreate`.
- **[Fact]** `FulfillmentInput` = `{ lineItemsByFulfillmentOrder:
  [FulfillmentOrderLineItemsInput!]!, trackingInfo: FulfillmentTrackingInput,
  notifyCustomer: Boolean (default false), originAddress:
  FulfillmentOriginAddressInput }`. `.../input-objects/FulfillmentInput`.
- **[Fact]** `FulfillmentOrderLineItemsInput = { fulfillmentOrderId: ID!,
  fulfillmentOrderLineItems: [FulfillmentOrderLineItemInput!] }`. **Omitting
  `fulfillmentOrderLineItems` fulfills ALL line items** of that FO; **max 512**
  line items. `FulfillmentOrderLineItemInput = { id: ID!, quantity: Int! }` where
  `id` is the **FulfillmentOrderLineItem GID** (NOT the order LineItem id, NOT the
  variant id). `.../input-objects/FulfillmentOrderLineItemsInput`,
  `.../input-objects/FulfillmentOrderLineItemInput`.
  - **Reconciliation:** validates RA-023 + D-014-4 — always send **explicit**
    `fulfillmentOrderLineItems`; the matching chain must resolve each Odoo move
    line to a **FulfillmentOrderLineItem GID** (not just the order-line GID).
    Note the **512-line cap per FO input** AND the **general GraphQL input-array
    max of 250 / 1000-point query-cost cap** (§6) — batch to the smaller effective
    limit for very large orders. → DEC-038.
- **[Fact]** `FulfillmentTrackingInput = { company: String, number: String,
  numbers: [String!], url: URL, urls: [URL!] }` — **`url`/`urls` are the `URL`
  scalar**, not String; RFC-valid URLs required.
  `.../input-objects/FulfillmentTrackingInput`.
- **[Fact]** `fulfillmentTrackingInfoUpdate(fulfillmentId: ID!, trackingInfoInput:
  FulfillmentTrackingInput!, notifyCustomer: Boolean)` is the current,
  non-deprecated tracking-update mutation; payload has `userErrors: [UserError!]!`.
  `notifyCustomer` governs this and future updates.
  `.../mutations/fulfillmentTrackingInfoUpdate`.
- **[Fact]** `fulfillmentCreateV2` and `fulfillmentTrackingInfoUpdateV2` **still
  exist** in 2026-07 but are **DEPRECATED** ("Use `fulfillmentCreate` instead" /
  "Use `fulfillmentTrackingInfoUpdate` instead") — callable but must not be used
  by new code (RA-022 static guard target). Their scheduled removal version is not
  published. `.../mutations/fulfillmentCreateV2|fulfillmentTrackingInfoUpdateV2`.
- **[Fact]** `UserError = { field, message }`. Business-rule failures return in
  `userErrors` (empty = success), **not** as GraphQL transport errors — the result
  handler must treat a non-empty `userErrors` as a failed operation.

### 4.1 Idempotency — decision-critical (RA-014 / RA-017 / DEC-011 / D-014-7)

- **[Fact — page last updated 2026-02-02]** The `@idempotent` directive applies to
  a list of **17** mutations, and **neither `fulfillmentCreate` nor
  `fulfillmentTrackingInfoUpdate` is on it**. The 17 are all inventory /
  location / `refundCreate`. `https://shopify.dev/docs/api/usage/implementing-idempotency`.
  Corroborated independently by the 2026-01 changelog (same set, no fulfillment
  mutation). `https://shopify.dev/changelog/adding-idempotency-for-inventory-adjustments-and-refund-mutations`.
- **[Fact]** As of **2026-04**, supplying an `@idempotent` key became **mandatory**
  for those covered inventory/refund mutations — this does **not** add fulfillment
  mutations to the set. `https://shopify.dev/docs/api/usage/idempotent-requests`.
- **Reconciliation of the "17" question:** the "17-mutation `@idempotent` list"
  wording in DEC-011 / RA-014 / RA-017 / AR-008 is **still accurate as of
  2026-07-21** (17, fulfillment absent) — it is **not stale**; only a clarifying
  refresh is warranted (add that idempotency became *mandatory* 2026-04 for those
  17). **This corrects Phase-1 inventory contradiction #1**, which mis-flagged the
  count as stale. The decision-critical consequence is **confirmed and unchanged**:
  `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` have **no native
  idempotency**, so the connector's **verify-before-retry + operation-scope
  serialization under Layer 2** (D-014-7 / DEC-011 / DEC-036) remains the **primary
  duplicate-prevention control** — RA-014/RA-017 unaffected. → DEC-038.

---

## 5. Fulfillment object, tracking, events

- **[Fact]** `Fulfillment.status: FulfillmentStatus!` — 4 active
  (`SUCCESS`/`CANCELLED`/`ERROR`/`FAILURE`) + deprecated `OPEN`/`PENDING`
  (EXACT-MATCH A4). `.../enums/FulfillmentStatus`. Mode 2 condition 2 gate =
  `SUCCESS`.
- **[Fact]** `Fulfillment.displayStatus: FulfillmentDisplayStatus` (nullable) — 18
  values (EXACT-MATCH A7), incl. `CANCELED` (one "L", distinct from A4 `CANCELLED`).
  **Display only; never an automation input** (status-model §4.1). Nullable → must
  handle null. `.../enums/FulfillmentDisplayStatus`.
- **[Fact]** Fulfillment fields: `status`, `displayStatus`, `trackingInfo:
  [FulfillmentTrackingInfo]!`, `service: FulfillmentService`, `events`,
  `fulfillmentLineItems`, `fulfillmentOrders`, `totalQuantity: Int!`,
  `deliveredAt`, `inTransitAt`, `estimatedDeliveryAt`, `location`, `order`,
  `originAddress`, `name`, `legacyResourceId`. `.../objects/Fulfillment`.
  `FulfillmentTrackingInfo` (output) = `{ company, number, url }`.
- **[Fact]** Carrier/company → URL matching priority: explicit `url` (highest);
  else recognized `company` name auto-builds the URL; else number-only may
  pattern-match and **can yield an invalid URL** — Shopify "highly recommends"
  sending **both** company and url. `.../objects/FulfillmentTrackingInfo`.
  - **Reconciliation:** refines D-014-6 — the connector should send
    `carrier_tracking_url` (`url`) whenever present (it already maps
    `carrier_tracking_url → trackingInfo.url`), and pass `carrier_id.name` as
    `company`; a client-side carrier table remains unnecessary but sending the
    explicit URL is preferred over relying on Shopify's number pattern-match.
- **[Fact]** `FulfillmentEvent` = `{ status: FulfillmentEventStatus!, happenedAt,
  message, address/geo, timestamps, id }` — **no quantity field**; 11
  `FulfillmentEventStatus` values (EXACT-MATCH A5). Events are read-only carrier
  telemetry; **[Inference, schema-grounded]** they **do not change fulfilled
  quantities** — validating status-model §8 (carrier `DELIVERED` never writes Odoo
  stock). `.../objects/FulfillmentEvent`, `.../enums/FulfillmentEventStatus`.
- **[Fact/Inference]** There is **no app-attribution field** on `Fulfillment` or
  `FulfillmentService` (Order has app attribution; fulfillments do not).
  `FulfillmentService.handle: String!` is the stable origin key. → validates modes
  §3 evidence-stacked classification with the **own-GID ledger as the primary /
  authoritative** signal (Shopify cannot tell the connector "my app made this").
  `.../objects/Fulfillment`, `.../objects/FulfillmentService`.

---

## 6. Rate limits, throttling, request IDs (Layer 2 transport already owns this)

- **[Fact]** GraphQL Admin API is **cost-based** (points), not request-count:
  objects cost 1, connections scale with `first`/`last`, mutations default 10; a
  single query may not exceed **1,000 points**; **input arrays max 250**; restore
  rates Standard 100 / Advanced 200 / Plus 1000 / Enterprise 2000 points/sec
  (leaky bucket). `https://shopify.dev/docs/api/usage/limits`.
- **[Fact]** Cost/throttle state is in `extensions.cost`
  (`requestedQueryCost`, `actualQueryCost`, `throttleStatus{ maximumAvailable,
  currentlyAvailable, restoreRate }`). Throttling on GraphQL surfaces as **HTTP
  200 with a `THROTTLED` error** in `errors[]` (not HTTP 429); `MAX_COST_EXCEEDED`
  (>1000 pts) is **non-retryable** (split the query). Per-request **Request ID**
  is surfaced for support/debugging (exact header spelling unverified).
- **Reconciliation:** these are already owned by the merged core API client /
  Layer 2 transport (see the code audit); Wave 4 fulfillment reuses that transport
  and must **not** re-implement raw throttling. Batch FO line inputs under the
  250/512/1000-point envelope.

---

## 7. Unresolved items (carried; none is a Gate A blocker)

1. Full definition of the `fulfill_and_ship_orders` **staff permission** lives in
   the Shopify Help Center (outside `shopify.dev`); only its requirement on
   `fulfillmentCreate` is verifiable here.
2. Whether `fulfillmentOrderReleaseHold` returns a future-`fulfillAt` FO to
   `SCHEDULED` vs `OPEN` is not stated on that page (examples show OPEN only).
3. Exact scheduled **removal** version of `fulfillmentCreateV2` /
   `fulfillmentTrackingInfoUpdateV2` is not published (deprecated but callable).
4. Exact per-plan GraphQL bucket capacity (`maximumAvailable`) vs restore rate;
   exact `X-Request-Id` header spelling; whether `displayStatus` is derived from
   the latest event — all display/telemetry-only, not decision-critical.
5. All field types/nullability were read from rendered reference pages, not a raw
   introspection dump — re-verify against introspection pinned to `2026-07` before
   Gate B **code freeze**.

**Phase 2 (Shopify) completion criterion met:** every version-sensitive proposed
fulfillment behavior is either **supported** by current official evidence (all 7
Layer-A enums exact-match; FO/Fulfillment/mutation shapes confirmed; no native
fulfillment idempotency confirmed; scopes + staff permission confirmed) or
**explicitly unresolved** (§7) — none blocking.
