# Shopify Official API Notes

> Tier-1 technical baseline for the Shopify side of the Odoo 19 ↔ Shopify
> Connector. **Every factual claim here is sourced from official Shopify
> developer documentation (`shopify.dev`)** and carries its exact URL. This
> document **does not make architecture decisions** — the
> "Architecture constraints implied by Shopify facts" section is explicitly
> **inference**, and design choices (REST vs GraphQL, webhook vs cron vs queue,
> sync-engine shape) remain **gated** pending ChatGPT review (`CLAUDE.md` §4–§5).

## Status

- **Sprint:** Research Sprint B (RB-05.1). **Phase:** research only; no-code gate
  applies.
- **Classification key (per `CLAUDE.md` §8):** **Fact** = stated on an official
  Shopify page; **Inference** = our deduction from facts; **Open question** =
  not found / unverified on official docs. No **Decisions** are recorded here.
- **Confidence:** facts below were gathered by topic-specific passes and an
  **independent verification pass** re-reading the highest-stakes canonical pages
  (rate limits, versioning, webhooks). Where the two passes diverged or a number
  was not literally on the page, the claim is downgraded to **Open question**
  rather than asserted.

## RB-14 refresh (2026-07-01)

> **Architecture-prep refresh.** For the **RB-14 Part 1** sprint, the load-bearing
> facts below were **re-verified live on 2026-07-01** (one day after the Sprint B
> baseline) across the AR-002/AR-003/AR-005 topics, with verbatim quotes. The full
> dated delta lives in
> [`../03-architecture/rb14-official-source-refresh.md`](../03-architecture/rb14-official-source-refresh.md).
> **The Sprint B facts below remain valid** — this section records only the **status
> and the version-sensitive deltas**; nothing below is erased.
>
> - **Confirmed unchanged (2026-07-01):** REST legacy (2024-10-01) + GraphQL-primary
>   + new-public-apps-GraphQL-only (2025-04-01); versioning cadence/format/12-month-
>   min/9-month-overlap/fall-forward; webhook delivery-not-guaranteed → reconciliation,
>   1s/5s timeout, 8 retries/4h, auto-delete after 8 consecutive failures (Admin-API
>   subs), HMAC-SHA256 raw body, `X-Shopify-Webhook-Id` dedup; GraphQL cost model +
>   per-plan restore rates + 1,000-point single-query ceiling; REST leaky bucket +
>   429/`Retry-After`; bulk-ops JSONL/100MB/24h-10d + up-to-5-of-each (2026-01);
>   inventory quantity states + `on_hand` sum + `committed` read-only + compare-and-set
>   + `@idempotent`-required-2026-04; orders 60-day + `read_all_orders` approval +
>   protected-data Level 1/2; GID format + REST↔GID mapping.
> - **Version-sensitive deltas to flag:** (1) the GraphQL **`latest` alias now resolves
>   to `2026-07`** (Sprint B saw `2026-04`); the version table spans `2025-07`…`2027-01`.
>   (2) `@idempotent` on `inventorySetQuantities`/`inventoryAdjustQuantities` was
>   **optional as of 2026-01** and is **required as of 2026-04** (sharpens the Sprint B
>   "required 2026-04" note). (3) `productSet` **delete-on-omit applies to list fields
>   only** — "For all other field types … omitted fields will remain unchanged" (scalars
>   are safe-update). (4) **Offline tokens are dual** — legacy non-expiring **and** new
>   "Expiring offline tokens" (90-day refresh); "offline never expires" holds only for
>   the legacy variant. (5) API-health navigation now via the **Dev Dashboard**
>   (Apps → Monitoring → API health).
> - **New/sharpened open questions (architecture-relevant):** custom/private-app scope of
>   the GraphQL-only mandate (only "new public apps" stated); **GID permanence/non-reuse
>   is NOT asserted**; **no client-mutation-id / general mutation idempotency** beyond
>   `@idempotent`; `@idempotent` key-uniqueness scope + server dedup TTL unstated.
>   These route to AR-002/AR-005 framing, not to a decision.

## RB-14 Part 2 resolution (2026-07-01)

> **High-risk open-question resolution.** For the **RB-14 Part 2** sprint, the high-risk
> Shopify open questions from Part 1 were **re-checked against official `shopify.dev` pages
> and the official changelog** (access date 2026-07-01), with an adversarial cross-verify
> pass. Full dated record + verbatim quotes:
> [`../03-architecture/rb14-part2-open-question-resolution.md`](../03-architecture/rb14-part2-open-question-resolution.md).
> **Sprint B + Part 1 facts remain valid**; this records the **Part 2 resolutions/narrowings
> only.** No architecture decision is made.
>
> - **RQ-002-1 (GraphQL-only mandate scope) — Partially resolved.** `[Official fact]` the
>   binding "must" is scoped to **new public apps** only ("Starting April 1, 2025, all new
>   public apps must be built exclusively with the GraphQL Admin API" — `/docs/api/admin-rest`).
>   `[Official fact]` (new) custom apps are **not categorically forbidden from REST**: "Custom
>   apps built on REST that do not need to support more than 100 variants can continue to use
>   the deprecated REST product APIs" and `[Official limitation]` "Developers should expect that
>   the GraphQL API will be the only supported API over the long term"
>   (`/changelog/deprecation-timelines-related-to-new-graphql-product-apis`). `[Open question]`
>   the **blanket** custom/private scope + any **REST EOL date** stay unstated.
> - **RQ-002-2 (custom-app privacy / compliance) — Partially resolved.** `[Official fact]` the
>   three mandatory compliance webhooks are "callback methods that Shopify requires for apps
>   listed on the Shopify App Store" (`/docs/apps/build/compliance/privacy-law-compliance`).
>   `[Official fact]` **protected-customer-data access matrix**: Level 1 — public "Requires
>   review", custom "Always available", Admin-created custom "Always available"; Level 2 —
>   public "Requires review", custom "Always available", Admin-created "Varies by plan"
>   (`/docs/apps/launch/protected-customer-data`). `[Official fact]` L1/L2 **obligations attach
>   to the data kind** ("If you're using only protected customer data, then you must meet the
>   level 1 requirements"; name/address/phone/email → L1+L2). `[Open question]` whether custom
>   apps **must implement** the compliance webhooks, and whether the L1/L2 **obligations bind**
>   custom apps — **not stated; not assumed absent**.
> - **RQ-002-3 (custom-app token model) — Partially resolved.** `[Official fact]` two
>   acquisition paths (token exchange / authorization-code grant); online tokens expire
>   logout/24h; offline tokens **non-expiring** ("grant permanent access … revoked through app
>   uninstallation or secret revocation") **or expiring** (`expires_in: 3600` + a **90-day**
>   `refresh_token_expires_in: 7776000` that rotates, previous refresh invalidated after use).
>   `[Official fact — Part 1]` admin-created custom-app token installed on generation (Part 1
>   cite); `[Official fact — Sprint B]` least-privilege (access-scopes). `[Open question]` a
>   single cross-model rotation/revocation policy statement.
> - **RQ-005-1 (GID permanence) — Partially resolved / re-confirmed.** `[Official fact]` a GID
>   "uniquely identifies an object" and the Node/Product `id` is "A globally-unique ID"; `[Open
>   question]` **no** permanence / non-reuse / deleted-recreated statement — permanence is **not
>   asserted** (`/docs/api/usage/gids`, `/interfaces/Node`, `/objects/Product`).
> - **RQ-005-2 (general mutation idempotency) — Partially resolved (materially narrowed).**
>   `[Official fact]` (new) **"Shopify tracks idempotency keys for 24 hours from the original
>   request"** — server dedup **TTL = 24h** (resolves the Part 1 open item); `[Official
>   limitation]` the `@idempotent` directive "only applies to mutations that support the
>   `@idempotent` directive" — a **fixed list of 17** (inventory/location + `refundCreate`);
>   `[Official fact]` `IDEMPOTENCY_CONCURRENT_REQUEST` on concurrent duplicates; `[Official
>   limitation]` **no general/all-mutation idempotency and no `clientMutationId`**
>   (`/docs/api/usage/implementing-idempotency`, `/docs/api/usage/idempotent-requests`).
>   `[Open question]` key **uniqueness scope** (per-shop/app/global) + **bulk-op idempotency**.
>   *(Quote precision: `inventorySetQuantities` reads "As of 2026-01 …" without the word
>   "version"; the bulk page reads "These errors might be intermittent …".)*

## DEC-007 propagated facts (2026-07-02)

> **Propagation, not new research.** These facts were originally verified during the Phase 1
> Domain Model + DEC-003 Scope-Hole Closure sprint (2026-07-02) as part of
> [`DEC-007`](../04-decisions/DEC-007-phase1-scope-clarifications.md) (now **Accepted by
> ChatGPT**) and are propagated here, unchanged, per the DEC-007 Acceptance Patch
> (2026-07-02). No new external research was performed for this propagation. Access date for
> all facts below: **2026-07-02**.

- **Fact —** `Order.taxLines` = "A list of all tax lines applied to line items on the order,
  before returns." `Order.currentTaxLines` and `Order.totalTaxSet` are also exposed on
  `Order`.
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order)
- **Fact (paraphrase) —** `Order.shippingLines`/`shippingLine` represent the shipping
  methods applied to the order, including checkout shipping option / carrier / service /
  cost details. The fetched summary of this field was a **partial excerpt, not confirmed as
  the complete official field description** — treat the exact full wording as **[Open
  question — must be verified before implementation]** if a verbatim quote is needed.
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order)
- **Fact —** `Order.discountApplications` = "A list of discounts that are applied to the
  order, excluding order edits and refunds." `cartDiscountAmountSet` and
  `currentCartDiscountAmountSet` are also exposed on `Order`.
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order)
- **Fact —** `FulfillmentInput.notifyCustomer` — "Whether the customer is notified. If
  `true`, then a notification is sent when the fulfillment is created." — **defaults to
  `false`**.
  (https://shopify.dev/docs/api/admin-graphql/latest/input-objects/FulfillmentInput)
- **Fact —** `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` argument — "If this field is
  left blank, then notifications won't be sent to the customer when the fulfillment is
  updated."
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentTrackingInfoUpdate)

## Part E pre-implementation research patch (2026-07-04)

> **Master Blueprint Part E — implementation-planning bridge, documentation-only
> research patch.** These facts were verified to close two of the three
> currently-untracked gaps the PR #78 audit
> ([`../05-qa/master-blueprint-integrity-competitor-advantage-audit.md`](../05-qa/master-blueprint-integrity-competitor-advantage-audit.md)
> §6) flagged as missing from this corpus: Shopify's multi-currency/
> presentment-currency order model, and the product-domain webhook topic
> strings. Access date for every fact below: **2026-07-04**. **No architecture
> decision is made here** — see
> [`../03-architecture/master-blueprint-implementation-planning-bridge.md`](../03-architecture/master-blueprint-implementation-planning-bridge.md)
> §5/§6 for how these facts route to the open-questions register (new rows
> MBQ-64/MBQ-65, both logged **Proposed / Open**, not resolved).

### MoneyBag / presentment currency (Order money model)

- **Fact —** `MoneyBag` is the type Shopify uses for order-money fields; it
  has exactly two non-null fields: **`shopMoney`** ("Amount in shop
  currency.") and **`presentmentMoney`** ("Amount in presentment currency."),
  both typed `MoneyV2`.
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/MoneyBag)
- **Fact —** `Order.currencyCode` = "The shop currency when the order was
  placed. For example, 'USD' or 'CAD'." `Order.presentmentCurrencyCode` =
  "The currency used by the customer when placing the order. For example,
  'USD', 'EUR', or 'CAD'."
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order)
- **Fact —** Every order total/adjustment field is `MoneyBag`-typed and
  therefore carries **both** currencies simultaneously — confirmed for
  `totalPriceSet` ("The total price of the order, before returns, in shop and
  presentment currencies."), `currentTotalPriceSet`, `originalTotalPriceSet`,
  `totalOutstandingSet`, `totalDiscountsSet`, `totalTaxSet`,
  `totalShippingPriceSet`, `totalReceivedSet`, `totalRefundedSet`,
  `totalCapturableSet`, `totalTipReceivedSet`, `cartDiscountAmountSet`, and
  their `current*Set` equivalents — each is described as "...in shop and
  presentment currencies" (or the equivalent "after returns..." phrasing for
  the `current*` variants).
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order)
- **Inference —** A store's orders expose both `shopMoney` and
  `presentmentMoney` on every money field unconditionally — the fetched
  `Order`/`MoneyBag` pages do not state that `presentmentMoney` only
  populates (or only diverges from `shopMoney`) when Shopify Markets/
  multi-currency selling is explicitly enabled. Comparing an Odoo total
  (single document currency — see the Odoo notes below) against the wrong
  Shopify money field would silently mis-total whenever the two diverge.
- **Open question —** Whether `presentmentMoney` can ever diverge from
  `shopMoney` for a store that has not explicitly enabled Shopify Markets/
  multi-currency selling is **not stated** on the fetched `Order`/`MoneyBag`
  pages — routed to **MBQ-64** (`../03-architecture/master-blueprint-open-questions.md`)
  rather than assumed either way.

### Product-domain webhook topics

- **Fact —** `WebhookSubscriptionTopic` includes **`PRODUCTS_CREATE`**
  ("Occurs whenever a product is created. Requires the `read_products`
  scope."), **`PRODUCTS_UPDATE`** ("Occurs whenever a product is updated,
  ordered, or variants are added, removed or updated." Requires
  `read_products`), and **`PRODUCTS_DELETE`** ("Occurs whenever a product is
  deleted. Requires the `read_products` scope.") — the direct product-domain
  analogs of the already-verified `ORDERS_CREATE`/`INVENTORY_LEVELS_UPDATE`
  topics (MBQ-37).
  (https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic)
- **Fact —** The same enum also carries **`PRODUCT_LISTINGS_ADD`/`_REMOVE`/
  `_UPDATE`** (channel-listing events, `read_product_listings` scope),
  **`PRODUCT_PUBLICATIONS_CREATE`/`_DELETE`/`_UPDATE`** (publication events,
  `read_publications` scope), and **`SCHEDULED_PRODUCT_LISTINGS_ADD`/`_REMOVE`/
  `_UPDATE`** — none of these were previously verified in this corpus and none
  is required for Phase 1's product import/export scope (DEC-003; DEC-007
  §1); logged here for completeness, not as an implementation requirement.
  (https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic)
- **Open question —** As with the inventory-topic analog (MBQ-37/MBQ-63), only
  the **topic strings** were verified this session — the exact webhook
  **payload shape**, required subscription scopes beyond `read_products`, and
  whether webhook-driven product import is implemented in Phase 1 at all (vs.
  scheduled/manual/reconciliation-only, mirroring the already-accepted
  layered-sync posture for inventory) remain unverified — routed to
  **MBQ-65** (`../03-architecture/master-blueprint-open-questions.md`).

## MBQ-64/MBQ-65 residual research patch (2026-07-04)

> **Proposed [`DEC-020`](../04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md)
> residual research, documentation-only.** These facts close the two
> narrower sub-questions the Part E patch above left explicitly open, not
> asserted: whether Shopify presentment currency can diverge from shop
> currency outside an explicitly-enabled Shopify Markets/multi-currency
> setup (MBQ-64), and the product-webhook payload/subscription-mechanics
> residual beyond the topic strings (MBQ-65). Access date for every fact
> below: **2026-07-04**. **No architecture decision is made here** — see
> `DEC-020` §4–§8 for how these facts route to a proposed (not accepted)
> MBQ-64/MBQ-65 design decision.

### Money/order-currency facts used (MBQ-64)

- **Fact, verbatim (`https://shopify.dev/docs/apps/build/markets`, "About
  Shopify Markets") —** "The presentment currency is what store visitors
  see in checkout, what they agree to pay, and how their payment method is
  charged. These values are the source of truth." Also: "Presentment
  currency values are also displayed to the merchant as their source of
  truth on the order details page. Refunds and order edits are always based
  on the presentment currency. Shopify Functions are also provided monetary
  input values in the presentment currency."
- **Fact, verbatim (same page) —** "The shop currency is the merchant's
  common reference for their business on Shopify. If an order is placed in
  a different presentment currency, then shop currency values are
  back-converted from presentment values using the live exchange rate...
  Since the values are converted, intermediate shop currency values might
  not sum perfectly to totals, and shop currency values of corresponding
  transactions performed at different times (such as captures and refunds)
  might not match."
- **Fact, verbatim (same page) —** "The settlement currency is the currency
  of the merchant's payout. It might equal the shop currency or the
  presentment currency, but it's not guaranteed... These values are the
  most appropriate for accounting purposes. When a merchant is not using
  Shopify Payments, settlement currency values must be fetched and
  reconciled directly from their payment gateways."
- **Fact, verbatim (`https://shopify.dev/docs/api/admin-graphql/latest/objects/Order`,
  re-verified against the page's raw source, not only a summarized fetch)
  —** `presentmentCurrencyCode`: "The currency used by the customer when
  placing the order. For example, "USD", "EUR", or "CAD". This may differ
  from the shop's base currency when serving international customers or
  using multi-currency pricing." This second sentence extends what the
  Part E patch above cited (that patch quoted only the first sentence) —
  re-fetched and confirmed verbatim this session, not previously cited in
  this corpus.
- **Resolved open question (was open in the Part E patch above) —**
  presentment currency **can** diverge from shop currency without a
  merchant necessarily framing it as "enabling Shopify Markets" as a named
  feature — the `Order` object's own field description now names two
  independent triggers ("serving international customers," "using
  multi-currency pricing"), and "About Shopify Markets" confirms the
  back-conversion mechanism is automatic whenever the two differ. This does
  **not** mean every store diverges — same-currency stores still see
  `shopMoney == presentmentMoney` — it means the connector cannot assume
  divergence only occurs under an explicit "Markets" toggle.
- **Open question, not resolved this session —** whether Shopify exposes a
  single boolean/flag on the `Order` object stating "this order used
  Markets/multi-currency selling" (distinct from comparing
  `currencyCode`/`presentmentCurrencyCode` directly) was not searched for
  or found on the fetched pages; not required for `DEC-020`'s proposed
  mechanism (which compares the two currency codes directly), logged here
  only for completeness.

### Product webhook facts used (MBQ-65)

- **Fact, verbatim (`https://shopify.dev/docs/apps/build/webhooks/subscribe`,
  "Manage webhook subscriptions") —** two subscription mechanisms: an
  **app-config** subscription, "Defined in `shopify.app.toml` and applied
  uniformly across every shop that installs your app" (the page's
  recommended default), and a **shop-specific** subscription "created using
  GraphQL Admin API; configuration can differ per shop," via the
  `webhookSubscriptionCreate` mutation. "Each topic you subscribe to
  requires a corresponding access scope" — for the three product topics,
  `read_products` (already verified by the Part E patch above).
- **Fact, verbatim (`https://shopify.dev/docs/apps/build/webhooks`, "About
  webhooks," confirmed against the page's raw source) —** "Shopify doesn't
  guarantee ordering within a topic, or across different topics for the
  same resource. For example, it's possible that a `products/update`
  webhook might be delivered before a `products/create` webhook." Shopify
  "recommends using timestamps provided in the header
  (`X-Shopify-Triggered-At`) or in the payload itself (`updated_at`) to
  organize webhooks."
- **Fact, verbatim (same page) —** "Your app shouldn't rely on receiving
  data from Shopify webhooks. Webhook delivery isn't always guaranteed, and
  your app can miss or mishandle events for other reasons, such as handler
  failures or downtime. For redundancy, use reconciliation jobs to
  periodically fetch data from Shopify so that your app stays consistent
  with Shopify's data."
- **Fact, verbatim (same page) —** "Verify HMAC signatures and ignore
  duplicate deliveries using `X-Shopify-Webhook-Id`." Delivery headers
  confirmed to include `X-Shopify-Topic`, `X-Shopify-Webhook-Id`, and
  `X-Shopify-Hmac-Sha256`.
- **Fact (same page) —** the webhook payload is the **full resource by
  default**; a `fields`/`include_fields` parameter can restrict which
  fields are included ("If omitted, the full payload is sent.").
- **Fact (same page) —** "Events" is named as Shopify's "next-generation
  subscription mechanism, currently in developer preview for a subset of
  topics," able to run side by side with webhooks in the same
  `shopify.app.toml`. Not required for Phase 1 scope, logged for
  completeness only.
- **Inconclusive / not confirmed this session —** a claimed per-product
  **variant-count payload-truncation** behavior (that very-high-variant
  products' webhook payloads include full detail for only a subset of
  variants, with a `variant_ids`/`truncated_fields`-style residual pointer
  for the rest) was raised by third-party developer-aggregator sources
  surfaced via web search, but could **not** be confirmed against a primary
  `shopify.dev` page directly fetched this session. Two candidate pages
  were fetched (`https://shopify.dev/docs/apps/build/webhooks` and
  `https://shopify.dev/docs/apps/build/webhooks/customize/modify-payloads`)
  and neither page's retrieved content contained this claim. Per
  `CLAUDE.md` §7 rule 5, this is logged as an **open, unverified
  question**, not asserted as fact.

## Task 011 customer-object research patch (2026-07-10)

> **Customer-object section added by the AR-039 gate-readiness session**
> — closing the reader-confirmed Tier-1 gap routed as OP-44 (this corpus
> previously had no Customer-object section). All facts below were
> fetched from official `shopify.dev` pages on **2026-07-10** (the
> `latest` reference alias documented **API version 2026-07** at fetch
> time), each load-bearing claim additionally re-verified by an
> independent adversarial pass the same day. Full excerpts with quotes
> and access statuses:
> [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md).
> Facts only — no decision is recorded here.

### Customer object (Admin GraphQL API)

- **[Fact]** Reading `Customer` requires the `read_customers` access
  scope; the page cautions that Shopify "will restrict access to scopes
  for apps that don't have a legitimate use for the associated data"
  (`objects/Customer`, Accessible 2026-07-10).
- **[Fact]** **`Customer.email` and `Customer.phone` are deprecated**
  (2026-07): deprecation reasons read "Use
  `defaultEmailAddress.emailAddress` instead." and "Use
  `defaultPhoneNumber.phoneNumber` instead." `defaultEmailAddress` is a
  nullable `CustomerEmailAddress` (its `emailAddress` is `String!`);
  `defaultPhoneNumber` is a nullable `CustomerPhoneNumber` (its
  `phoneNumber` is `String!`). Both replacement objects themselves
  require `read_customers`.
- **[Fact]** **`Customer.addresses` is deprecated** ("Limited to 250
  addresses. Use `addressesV2` for paginated access to all addresses.");
  `addressesV2` is a `MailingAddressConnection!` with standard
  `first`/`after`/`last`/`before`/`reverse` cursor pagination.
  `defaultAddress` is a nullable `MailingAddress`.
- **[Fact]** Core fields relevant to import: `id` (`ID!`), `firstName`/
  `lastName` (`String`), `displayName` (`String!` — falls back to email,
  then phone, when names are absent), `createdAt`/`updatedAt`
  (`DateTime!`), `note`, `tags`, `verifiedEmail`, `state`
  (`CustomerState!` — only meaningful with Classic Customer Accounts),
  `numberOfOrders`, `amountSpent`, `locale`.
- **[Fact]** The Customer object has **no person/company flag** — the
  only company-adjacent signals are the free-text
  `MailingAddress.company` string and the B2B
  `companyContactProfiles` (`[CompanyContact!]!`; `CompanyContact` joins
  a B2B `Company` to a customer record; B2B API resources are
  plan/access-gated).
- **[Fact]** `MailingAddress` carries `address1`, `address2`, `city`,
  `zip`, `province`, `provinceCode`, `country`, `countryCodeV2`
  (`CountryCode` enum; the older `countryCode` is deprecated),
  `company`, `firstName`, `lastName`, `name`, `phone`, `formatted`.
- **[Fact]** `QueryRoot.customers` is a `CustomerConnection!` with
  arguments `first`/`after`/`last`/`before`/`query`/`reverse`/`sortKey`
  (`CustomerSortKeys`, default `ID`; values include `UPDATED_AT`,
  `CREATED_AT`, `ID`); the `query` filter supports `updated_at` with
  comparators (`:>`, `:>=`, …) and ISO 8601 timestamp examples; GraphQL
  cursor pagination retrieves at most 250 resources per request (usage/
  pagination-graphql page). **[Open question]** the `updated_at` filter
  description says "matching a whole day" while its own examples use
  full timestamps — sub-day granularity must be verified empirically by
  whichever future task implements enumeration.
- **[Fact]** Customer data is protected customer data: name, address,
  email, phone are **Level 2 protected customer fields**; public apps
  require review for Level 1 and Level 2, custom apps have both "Always
  available," admin-created custom apps' Level 2 "Varies by plan"
  (protected-customer-data page, Accessible 2026-07-10; distribution
  detail captured for MBQ-05 branch B in the capture file and
  [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md)).
- **[Fact]** Versioning/limits re-confirmed unchanged (2026-07-10):
  quarterly releases, ≥12-month support, latest stable **2026-07**
  (released July 1, 2026); GraphQL calculated-cost model with
  `THROTTLED` signalled in the response body and cost telemetry under
  `extensions` — consistent with this corpus's earlier sections.

## Source hierarchy and access date

- **Tier 1 (used here):** official Shopify developer documentation, `shopify.dev`
  (API reference, usage guides, app-build/launch guides, and the developer
  changelog).
- **Access dates (two-stage):** the historical body below is the **Sprint B baseline,
  access date 2026-06-30**; it **remains the Sprint B baseline unless superseded by the
  RB-14 refresh section above** (**RB-14 architecture refresh access date 2026-07-01**).
  **Version-sensitive facts must use the latest dated refresh** (the RB-14 section), not
  this Sprint B baseline. Shopify policy/limits pages are largely **version-independent**
  and can change without an API-version bump; treat numeric values as "as of the stated
  access date."
- **API version context:** during **Sprint B (2026-06-30)** the GraphQL `latest` alias
  resolved to the **2026-04** schema; it was **re-checked in the RB-14 refresh
  (2026-07-01) and now resolves to `2026-07`** (see the RB-14 refresh section above).
  Version-specific facts note the version they apply from; where this Sprint B body and
  the RB-14 refresh differ, **the RB-14 refresh supersedes**.

---

## Facts from official Shopify documentation

### API strategy: REST vs GraphQL

- **Fact —** Shopify presents the **GraphQL Admin API as the primary,
  recommended API**: "All apps and integrations should be built with the GraphQL
  Admin API."
  (https://shopify.dev/docs/apps/build/graphql/migrate)
- **Fact —** The **REST Admin API is a legacy API as of October 1, 2024**, and is
  in **maintenance mode receiving only critical updates**; new features ship in
  GraphQL first.
  (https://shopify.dev/docs/api/admin-rest;
  https://shopify.dev/docs/apps/build/graphql/migrate)
- **Fact —** **Starting April 1, 2025, all new public apps** submitted to the App
  Store **must be built exclusively with the GraphQL Admin API**.
  (https://shopify.dev/docs/api/admin-rest;
  https://shopify.dev/changelog/starting-april-2025-new-public-apps-submitted-to-shopify-app-store-must-use-graphql)
- **Fact —** REST and GraphQL use **different ID formats**; stored REST numeric
  IDs must be converted to the GraphQL **global ID (GID)** to run equivalent
  operations. Some newer platform features exist **only** in GraphQL, and some
  REST resources have **no exact GraphQL equivalent**.
  (https://shopify.dev/docs/apps/build/graphql/migrate)
- **Open question —** The **final/last-supported REST Admin API version** and any
  published REST end-of-life date are **not stated** on the fetched pages (only
  the legacy date 2024-10-01 and the standard 12-month support window). Whether
  the GraphQL-only mandate also binds **custom/private apps** (vs only public
  apps) is not stated.

### API versioning

- **Fact —** Shopify releases a **new API version every three months, at the
  start of the quarter, at 5pm UTC**; version names are **date-based `YYYY-MM`**
  (example on page: `2026-04`).
  (https://shopify.dev/docs/api/usage/versioning)
- **Inference —** The four release months are therefore **January, April, July,
  October** (deduced from "beginning of the quarter").
- **Fact —** Each **stable version is supported for a minimum of 12 months**,
  with **at least nine months of overlap** between consecutive versions. A stable
  version is **guaranteed not to change** for its supported lifetime.
  (https://shopify.dev/docs/api/usage/versioning)
- **Fact —** A **release candidate** is published on the same date as a stable
  release and may contain backwards-incompatible changes; an **unstable** version
  changes continuously. Neither is recommended for production.
  (https://shopify.dev/docs/api/usage/versioning)
- **Fact —** If an app targets an **inaccessible (retired) version, Shopify
  "falls forward"** and serves the **oldest accessible stable version** (example:
  a retired `2026-10` request is served as `2027-01`).
  (https://shopify.dev/docs/api/usage/versioning)
- **Fact —** Deprecated parts of the API are **deprecated across all supported
  stable versions** and **removed in a subsequent release** (page example:
  deprecated in `2026-10` → removed in `2027-01`). Responses carry the
  **`X-Shopify-API-Version`** header; REST returns
  **`X-Shopify-API-Deprecated-Reason`** when a deprecated behaviour is called.
  (https://shopify.dev/docs/api/usage/versioning;
  https://shopify.dev/docs/api/admin-rest/usage/versioning)
- **Fact —** The **API health report** (Dev Dashboard → Apps → Monitoring → API
  health) lists deprecated calls and an update deadline; it monitors a **rolling
  14-day window** and uses "Fix by" dates (yellow 30 days–9 months out, red
  < 30 days) and "Fix overdue" for unsupported-version calls. Continuing to use
  unsupported resources after the deadline leads to **App Store delisting**.
  (https://shopify.dev/docs/api/usage/versioning/api-health;
  https://shopify.dev/docs/api/usage/versioning)
- **Open question —** No **fixed maximum lifespan** for a version is published
  ("12 months" is a stated **minimum**, not a hard expiry); the page describes no
  scenario where an old-version request hard-errors instead of falling forward.

### Authentication and scopes

- **Fact —** All API requests must **authenticate**; apps acquire an **access
  token** when a merchant installs/authorizes the app. OAuth 2.0 is the
  underlying standard. Two token-acquisition methods: **token exchange**
  (for apps rendered in the Shopify admin — recommended, with Shopify managed
  installation) and the **authorization code grant** (for standalone apps).
  (https://shopify.dev/docs/apps/build/authentication-authorization;
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens)
- **Fact —** **Online access tokens** are tied to a logged-in user and **expire**
  (~`expires_in: 86399`, ≈24h). **Offline access tokens** have no user context
  and (by default) **do not expire**; an optional expiring-offline variant
  returns a 1-hour token plus a 90-day refresh token.
  (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant)
- **Fact —** **Session tokens** (JWT) authenticate an embedded app's frontend↔
  backend calls, **live ~1 minute**, must be fetched fresh per request via App
  Bridge, and **cannot themselves call the Admin API** (they are exchanged for an
  access token via token exchange). Authenticated Admin API requests send the
  token in the **`X-Shopify-Access-Token`** header.
  (https://shopify.dev/docs/apps/build/authentication-authorization/session-tokens;
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/token-exchange)
- **Fact —** **Access scopes** follow `{read_|write_}{resource}` (e.g.
  `read_orders`, `write_products`); apps must request **only the minimum data
  necessary** (least privilege). Scopes are declared in the app TOML as
  **required `scopes`** (granted at install) and **`optional_scopes`** (requested
  post-install, individually approvable/deniable).
  (https://shopify.dev/docs/api/usage/access-scopes;
  https://shopify.dev/docs/apps/build/authentication-authorization/app-installation/manage-access-scopes)
- **Fact —** By default apps have **no access to protected customer data**;
  scopes like `read_customers`, `read_orders`, `read_all_orders` require meeting
  Shopify's protected-customer-data requirements. **`read_all_orders` is
  restricted** — order access defaults to the **last 60 days**, and reading all
  orders needs `read_all_orders` **plus Shopify approval**.
  (https://shopify.dev/docs/api/usage/access-scopes)

### Rate limits and throttling

> **Important nuance (verified 2026-06-30):** the old `/docs/api/usage/rate-limits`
> slug now **301-redirects** to `/docs/api/usage/limits`, and that general page is
> now **GraphQL-only** — it no longer documents the REST leaky-bucket numbers.
> The REST figures below come from the **REST-specific** page,
> `/docs/api/admin-rest/usage/rate-limits`.

- **Fact —** Rate limiting uses the **leaky-bucket** algorithm: each app+store
  has a fixed-capacity bucket; requests add to it and capacity is restored each
  second; a full bucket throttles further requests.
  (https://shopify.dev/docs/api/usage/limits)
- **Fact (REST Admin API) —** request-count based. **Standard plan: 40-request
  bucket, 2 requests/second** restore. **Shopify Plus: 400-request bucket, 20
  requests/second** (10× standard). Exceeding it returns **HTTP 429** with a
  **`Retry-After`** header and an **`X-Shopify-Shop-Api-Call-Limit`** header
  (e.g. `32/40`).
  (https://shopify.dev/docs/api/admin-rest/usage/rate-limits)
  *(Note: the Plus bucket is 400, not the often-cited "80" — see Risks.)*
- **Fact (GraphQL Admin API) —** **calculated query cost** in points, restored
  per second by plan: **Standard 100, Advanced 200, Plus 1000, Enterprise
  (Commerce Components) 2000 points/second**. A **single query may not exceed
  1,000 points** regardless of plan (enforced before execution on requested
  cost).
  (https://shopify.dev/docs/api/usage/limits)
- **Fact —** Cross-API hard limits: array input arguments **max 250 elements**;
  pagination of object arrays capped at **25,000 objects** (a count over that
  returns `25001`). The **Storefront API** has no fixed per-request limit for
  real buyers (bots/crawlers are throttled).
  (https://shopify.dev/docs/api/usage/limits)
- **Open question —** The **per-plan GraphQL bucket size (`maximumAvailable`,
  points)** is **not published** as a per-plan value; only restore rates are
  given. The only bucket figure on the page (`maximumAvailable: 1000`,
  `restoreRate: 50`) is an **illustrative example** and even differs from the
  Standard 100 pts/s restore rate. The exact **GraphQL throttle error shape**
  (e.g. `THROTTLED` code; HTTP 200+errors vs 429) is not stated on the page.

### GraphQL query cost

- **Fact —** Field cost by return type: **Scalar = 0, Enum = 0, Object = 1,
  Interface/Union = max of possible selections, Connection = sized by `first`/
  `last`, Mutation = 10**. Shopify may set **manual costs** on individual fields.
  (https://shopify.dev/docs/api/usage/limits)
- **Fact —** **Requested cost** is computed **before execution** from the
  selected fields; **actual cost** (≤ requested) is computed from results. The
  bucket must hold the **requested** cost before execution and is **refunded the
  difference** afterward.
  (https://shopify.dev/docs/api/usage/limits)
- **Fact —** Each response includes **`extensions.cost`** with
  `requestedQueryCost`, `actualQueryCost`, and a `throttleStatus`
  (`maximumAvailable`, `currentlyAvailable`, `restoreRate`). The header
  **`Shopify-GraphQL-Cost-Debug: 1`** returns a per-field cost breakdown.
  (https://shopify.dev/docs/api/usage/limits)
- **Open question —** The exact arithmetic that converts a connection's
  `first`/`last` into requested cost is **not published** ("sized by `first` and
  `last`" only).

### Bulk operations

- **Fact —** Bulk operations are **asynchronous**; Shopify handles pagination and
  throttling server-side. **`bulkOperationRunQuery`** runs an async query;
  **`bulkOperationRunMutation`** runs a mutation **once per line of a JSONL file**
  uploaded via **`stagedUploadsCreate`** (the `file` must be the last multipart
  parameter).
  (https://shopify.dev/docs/api/usage/bulk-operations/queries;
  https://shopify.dev/docs/api/usage/bulk-operations/imports)
- **Fact —** Results are a **JSONL** file; nested child objects appear on
  separate lines with an auto-added **`__parentId`**. The download **URL expires
  7 days** after completion (`partialDataUrl` for partial failures).
  (https://shopify.dev/docs/api/usage/bulk-operations/queries;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/BulkOperation)
- **Fact —** **Concurrency is version-dependent:** **before 2026-01**, one bulk
  query **and** one bulk mutation at a time per shop; **2026-01+**, up to **five
  of each**. Poll via **`currentBulkOperation`** (deprecated in 2026-01+) or
  **`bulkOperation(id:)`** (2026-01+), or subscribe to the
  **`bulk_operations/finish`** webhook (delivery not guaranteed → poll as
  backup).
  (https://shopify.dev/docs/api/usage/bulk-operations/queries;
  https://shopify.dev/docs/api/usage/bulk-operations/imports)
- **Fact —** Limits: bulk **query** must finish within **10 days**; bulk
  **import** JSONL **≤ 100 MB** and must finish within **24 hours**. Bulk queries
  allow **max 5 connections**, **max 2 nesting levels**, require the `Node`
  interface, and forbid top-level `node`/`nodes`. The run/poll calls count
  against normal rate limits, but the **bulk execution itself does not**.
  (https://shopify.dev/docs/api/usage/bulk-operations/queries;
  https://shopify.dev/docs/api/usage/bulk-operations/imports)
- **Fact —** `BulkOperationStatus` enum: `CREATED, RUNNING, COMPLETED, FAILED,
  CANCELING, CANCELED` (schema values are uppercase; the finish-webhook payload
  uses lowercase).
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/BulkOperation)

### Webhooks and reconciliation

- **Fact —** Webhooks deliver near-real-time event data per **topic** to an
  **HTTPS URL, Google Pub/Sub URI, or Amazon EventBridge ARN**. Subscriptions are
  created in **`shopify.app.toml`** (app-specific, uniform across shops —
  recommended) or via the **GraphQL Admin API** (shop-specific, when topics/URIs/
  filters must vary). Each subscribed topic requires a corresponding access scope.
  (https://shopify.dev/docs/apps/build/webhooks;
  https://shopify.dev/docs/apps/build/webhooks/subscribe)
- **Fact —** **Verification:** each HTTPS delivery carries a base64 HMAC in the
  **`X-Shopify-Hmac-SHA256`** header; verify by computing **HMAC-SHA256 of the
  raw request body using the app's client secret** and comparing. Verification
  uses the **raw (unparsed) body** and must happen **before processing**. HMAC
  applies to **HTTPS only** (Pub/Sub and EventBridge don't require it). Use
  **`X-Shopify-Webhook-Id`** to **deduplicate**.
  (https://shopify.dev/docs/apps/build/webhooks/verify-deliveries)
- **Fact —** Shopify expects a **200** response (any non-2xx, incl. 3xx, is an
  error). Timeouts: **1-second connection, 5-second total**. On failure it
  **retries 8 times over the next 4 hours**; after **8 consecutive failures** the
  subscription is **automatically deleted if it was configured via the Admin
  API**.
  (https://shopify.dev/docs/apps/build/webhooks/subscribe/https)
- **Fact —** **Delivery is not guaranteed.** Shopify explicitly says apps
  **shouldn't rely on receiving webhook data** and should use **reconciliation
  jobs to periodically fetch data** (e.g. via `updated_at` filters) so state stays
  consistent. Duplicate deliveries are possible → handlers must be **idempotent**.
  (https://shopify.dev/docs/apps/build/webhooks/best-practices)
- **Fact —** **Mandatory compliance (privacy) webhooks** for App Store apps:
  **`customers/data_request`, `customers/redact`, `shop/redact`**. They must
  verify HMAC (return **401** if invalid), respond 2xx, and complete the action
  **within 30 days**. `shop/redact` arrives **48 hours after uninstall**;
  `customers/redact` is sent **10 days** after the deletion request (withheld up
  to **six months** if the customer has recent orders).
  (https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance)
- **Open question —** The retry/auto-delete numbers are documented on the
  **HTTPS-delivery subpage**, not the landing page; the equivalent retry
  semantics for **Pub/Sub and EventBridge** are not stated there. The widely
  repeated **"19 attempts over 48 hours"** figure is **outdated** — the current
  official figure is **8 retries over 4 hours** (see Risks).

### Products and variants

- **Fact —** A **Product** holds **options** (e.g. color/size, capped by
  `Shop.resourceLimits.maxProductOptions`), a **variants** connection
  (`variantsCount`, `hasOnlyDefaultVariant`), and **media**. A **ProductVariant**
  is a specific combination of option values (`selectedOptions`) with `sku`
  (case-sensitive), `price`, `inventoryItem`, `inventoryPolicy`,
  `inventoryQuantity`, etc.
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Product;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/ProductVariant)
- **Fact —** Under the **new product model (stable in 2024-04)**, the per-product
  variant limit rose from the historical **100** to **2,048**; **as of October
  15, 2025 all merchants** can create up to **2,048 variants**, and apps **not**
  on the in-support GraphQL product APIs get a **degraded/broken** experience
  above 100.
  (https://shopify.dev/changelog/the-product-variant-limit-is-now-2048-for-all-merchants;
  https://shopify.dev/changelog/new-graphql-product-apis-that-support-up-to-2000-variants-now-available-in-2024-04)
- **Fact —** Normal GraphQL connections page at **250 items**, but a single
  product's variants can be requested **up to 2,048** in one request, and
  **`productVariantsBulkCreate`** accepts up to **2,048** in one operation.
  **`productSet`** creates/updates a whole product in one request and
  **reconciles list fields (variants, collections, metafields) by deleting
  omitted entries** (supports `synchronous: false` for large inputs, polled via
  `productOperation`). `productSet`/`productVariantsBulkCreate`/
  `productVariantsBulkUpdate` enforce **max 50,000 inventory quantities** per
  mutation.
  (https://shopify.dev/docs/apps/build/product-merchandising/products-and-collections;
  https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet)
- **Open question —** Whether the **max options per product** is still hard-capped
  at **3** under the new model is **not confirmed** on a current reference page
  (only that `maxProductOptions` exists). Exact REST product-API deprecation
  deadlines were not confirmed on an official page (community figures unverified).

### Inventory, locations, and inventory levels

- **Fact —** The chain is **ProductVariant → InventoryItem (1:1) → InventoryLevel
  (one per Location) → Location**. An **InventoryItem** holds SKU, `tracked`,
  shipping/customs info; an **InventoryLevel** holds per-state quantities for one
  item at one location; a **Location** is any place inventory is stocked
  (`isActive`, `fulfillsOnlineOrders`, `shipsInventory`).
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/InventoryItem;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/InventoryLevel;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/Location)
- **Fact —** **Quantity states:** `available, on_hand, committed, incoming,
  reserved, damaged, safety_stock, quality_control`, where
  **`on_hand = available + committed + reserved + damaged + safety_stock +
  quality_control`**. `reserved/damaged/safety_stock/quality_control` show as
  "Unavailable."
  (https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states)
- **Fact —** **`committed` is API-read-only** — it changes **only** via order
  creation/fulfillment, not by the Admin API. **`inventorySetQuantities`** sets
  `available`/`on_hand` absolutely (with **compare-and-set** via
  `compareQuantity`); **`inventoryAdjustQuantities`** applies deltas (adjusting
  `available` also moves `on_hand`); **`inventoryActivate`** creates an
  InventoryLevel so a location can stock an item. Reading inventory needs
  `read_inventory`.
  (https://shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states;
  https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities;
  https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventoryAdjustQuantities)
- **Fact —** **As of API version 2026-04**, `inventorySetQuantities` and
  `inventoryAdjustQuantities` **require an idempotency key via the `@idempotent`
  directive**.
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities)

### Orders

- **Fact —** The **Order** object is the central hub linking customer, line
  items, transactions, and fulfillment. Key display fields:
  **`displayFinancialStatus`** (`AUTHORIZED, PAID, PARTIALLY_PAID,
  PARTIALLY_REFUNDED, PENDING, REFUNDED, VOIDED, EXPIRED`) and the non-null
  **`displayFulfillmentStatus`** (`FULFILLED, IN_PROGRESS, ON_HOLD,
  PARTIALLY_FULFILLED, UNFULFILLED, …`). Reading orders needs `read_orders` (or
  `read_marketplace_orders`).
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/Order)
- **Fact —** Apps see orders from the **last 60 days** by default; **all orders**
  requires the **`read_all_orders`** scope **and Shopify approval** (requested in
  the Partner Dashboard).
  (https://shopify.dev/docs/api/usage/access-scopes;
  https://shopify.dev/changelog/apps-now-need-shopify-approval-to-read-orders-older-than-60-days)
- **Fact —** Orders (and draft orders, abandoned checkouts, refunds,
  transactions) are **protected customer data**. Accessing name/address/email/
  phone needs **Shopify approval** plus data-protection controls — **Level 1** for
  any protected data, **Level 2** for the protected fields. Without approval,
  production stores return no such data.
  (https://shopify.dev/docs/apps/launch/protected-customer-data)
- **Fact —** Order webhook topics include **`ORDERS_CREATE`** (requires
  `read_orders`/`read_marketplace_orders`) and **`ORDERS_UPDATED`**; the
  slash/lowercase `orders/create` form is the webhook-topic string for the enum.
  (https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic)

### Fulfillment and tracking

- **Fact —** A **FulfillmentOrder** groups items to fulfill from one location; a
  **Fulfillment** is a shipment with tracking. The **legacy Order/Fulfillment
  workflow is unsupported as of API version 2022-07**, and **all apps should use
  the FulfillmentOrder object by 2023-07**.
  (https://shopify.dev/docs/apps/build/orders-fulfillment/fulfillment-service-apps;
  https://shopify.dev/docs/apps/build/orders-fulfillment/migrate-to-fulfillment-orders)
- **Fact —** **`fulfillmentCreate`** creates a fulfillment for FulfillmentOrders
  of the **same order and location** (fulfills all items if none specified) and
  can carry tracking. **`fulfillmentTrackingInfoUpdate`** updates carrier/numbers/
  URLs; if a **supported carrier name** is given, Shopify **auto-generates
  tracking URLs**. Tracking can be set at creation or later.
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentcreate;
  https://shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmenttrackinginfoupdate)
- **Fact —** A **fulfillment service** maps to a Location and handles its assigned
  fulfillment orders; it **accepts/rejects** requests
  (`fulfillmentOrderAcceptFulfillmentRequest`/`…RejectFulfillmentRequest`) and
  receives notifications at `<callback_url>/fulfillment_order_notification`
  (`kind` = `FULFILLMENT_REQUEST`/`CANCELLATION_REQUEST`); an optional
  `/fetch_tracking_numbers` endpoint is polled hourly. Writes need the
  assigned/merchant-managed/third-party fulfillment-order scopes.
  (https://shopify.dev/docs/apps/build/orders-fulfillment/fulfillment-service-apps/build-for-fulfillment-services)

### Refunds and returns

- **Fact —** **`refundCreate`** refunds an order (line items with `restockType`,
  shipping, duties); the **Refund** exists independently of money movement — the
  **actual money status is on the refund's transactions** (pending/processing/
  successful/failed). **`Order.suggestedRefund`** computes a suggested refund. As
  of **2026-04**, `refundCreate` **requires `@idempotent`**.
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/refundcreate;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/Refund;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/SuggestedRefund)
- **Fact —** Two return-entry paths: **`returnCreate`** makes an already-approved
  **OPEN** return; **`returnRequest`** makes a **REQUESTED** return needing
  **`returnApproveRequest`** (→ OPEN). **Return.status** enum: `REQUESTED, OPEN,
  CLOSED, DECLINED, CANCELED`. **`returnRefund`** refunds OPEN/CLOSED returns and
  is **deprecated in 2026-04 in favour of `returnProcess`**.
  **`RefundLineItem.restockType`**: `NO_RESTOCK, CANCEL, RETURN, LEGACY_RESTOCK`.
  Return mutations need `write_returns`/`write_marketplace_returns`.
  (https://shopify.dev/docs/api/admin-graphql/latest/mutations/returnCreate;
  https://shopify.dev/docs/api/admin-graphql/latest/mutations/returnApproveRequest;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/Return;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/RefundLineItem)

### Transactions and payouts

- **Fact —** **`OrderTransaction`** is **gateway-agnostic** (exists for all
  gateways); `OrderTransactionKind` = `AUTHORIZATION, CAPTURE, SALE, REFUND, VOID,
  CHANGE, EMV_AUTHORIZATION, SUGGESTED_REFUND` (a REFUND can happen only after a
  CAPTURE). **`orderCapture`** captures an authorization. Reading transactions
  needs `read_orders`/`read_marketplace_orders`.
  (https://shopify.dev/docs/api/admin-graphql/latest/objects/OrderTransaction;
  https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderTransactionKind)
- **Fact —** **Payouts/balance/disputes are Shopify Payments only**, surfaced via
  **`shopifyPaymentsAccount`** (`balance`, `payouts`, `disputes`,
  `balanceTransactions`, `activated`). `ShopifyPaymentsPayout.status` =
  `SCHEDULED, PAID, FAILED, CANCELED` (`IN_TRANSIT` deprecated). Disputes need
  **`read_shopify_payments_disputes`**; payout reads require the merchant
  permission "**access to payouts**".
  (https://shopify.dev/docs/api/admin-graphql/latest/queries/shopifypaymentsaccount;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/shopifypaymentspayout;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/ShopifyPaymentsDispute)
- **Inference —** For shops on **non-Shopify-Payments gateways**, **no payout/
  balance/dispute data exists**, so cross-gateway financial reconciliation must
  use **`OrderTransaction`** as the common ledger.
  (from the Shopify-Payments-only scoping above)
- **Open question —** Whether payout/balance reads are exposed as a literal OAuth
  **scope string** (e.g. `read_shopify_payments_payouts`) or only as the admin
  user permission is **not stated** on the fetched object pages.

### App Store / app review readiness notes

> Captured as **future-readiness** facts only; no product decision is implied.

- **Fact —** Apps must implement the **three mandatory compliance webhooks**
  (above), authenticate with **OAuth first** (before any UI), request **only
  necessary scopes** (proof may be required; high-risk scopes like
  `read_all_orders` need demonstrated need), serve everything over **TLS**, and
  (embedded) work **without third-party cookies/local storage** using **App
  Bridge + session tokens**.
  (https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements;
  https://shopify.dev/docs/apps/build/compliance/privacy-law-compliance)
- **Fact —** **New public apps must be GraphQL-Admin-only as of April 1, 2025**;
  all app charges must use **Shopify App Pricing / Billing API**.
  (https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements)
- **Fact —** **Built for Shopify** (badge tier) performance thresholds (75th
  percentile / 28 days): admin **LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms**; checkout
  **p95 ≤ 500ms** with **0.1%** failure over ≥1,000 requests; storefront must not
  drop Lighthouse by **> 10 points**. These are **stricter than baseline
  approval**.
  (https://shopify.dev/docs/apps/launch/built-for-shopify/requirements)

---

## Architecture constraints implied by Shopify facts

> **These are inferences** (our interpretation of the facts above), **not
> decisions.** They frame questions for later architecture review (seeded in
> `../05-qa/architecture-review-log.md`); they do **not** choose an approach.

- **Inference —** A new, App-Store-distributable connector effectively **must use
  the GraphQL Admin API** (REST is legacy; new public apps are GraphQL-only from
  2025-04-01; new features are GraphQL-first). A REST-based design would be a
  dead end for new public apps. *(REST-vs-GraphQL remains an open decision for
  custom/non-public deployments — see open questions.)*
- **Inference —** Webhooks **cannot be the sole source of truth** — delivery is
  not guaranteed, Admin-API subscriptions self-delete after 8 consecutive
  failures, and duplicates occur. A correct sync therefore implies **webhooks +
  a reconciliation/backfill path** (`updated_at` polling) **and idempotent,
  deduplicated** processing keyed on `X-Shopify-Webhook-Id`.
- **Inference —** The **5-second webhook timeout** implies the receiver should
  **ack fast and process out-of-band** (queue/cron), not do heavy sync work in
  the webhook request.
- **Inference —** Rate limits imply **two different throttling strategies**
  (REST request-count vs GraphQL point-cost). On GraphQL, the client should pace
  off **live `throttleStatus`** (requested cost, not actual) and prefer **smaller
  connection page sizes**; large reads/writes should move to **Bulk Operations**
  (subject to its concurrency, JSONL, and time/size limits).
- **Inference —** **Idempotency is becoming mandatory** for key writes
  (`@idempotent` on inventory set/adjust and `refundCreate` from 2026-04),
  implying the connector must **generate and persist idempotency keys** and
  handle retries.
- **Inference —** **Inventory writes** must target `inventory_item_id` +
  `location_id` per state; **`committed` is order-driven and not writable**, so
  the connector adjusts `available`/`on_hand` and lets orders drive `committed`.
- **Inference —** **Fulfillment must go through FulfillmentOrder-based
  mutations** (legacy order-based fulfillment is unsupported), and a single
  fulfillment is **per order + per location** (multi-location orders → multiple
  fulfillments).
- **Inference —** Handling **orders/customers implies a protected-customer-data
  compliance burden** (approval + Level 1/2 controls) and the **60-day window /
  `read_all_orders` approval** gate for historical backfills.
- **Inference —** **Versioning forces a maintenance cadence:** pin a **stable**
  version, monitor `X-Shopify-API-Version` and the API health report, and **plan
  an upgrade within the ~9-month overlap** to avoid fall-forward surprises and
  delisting.

## Open questions

1. Final/last-supported **REST Admin API version** and any REST sunset date; does
   the **GraphQL-only mandate** bind custom/private apps or only public apps?
2. **Per-plan GraphQL bucket size** (`maximumAvailable` points) — published only
   as restore rates; bucket capacity is unconfirmed.
3. Exact **GraphQL throttle error shape** (`THROTTLED` code; HTTP status) and
   whether GraphQL ever returns `Retry-After`.
4. Exact **connection-cost formula** from `first`/`last`.
5. Current **max options per product** under the 2024-04 model (still 3?).
6. **REST product/fulfillment API deprecation deadlines** (community dates
   unverified on official pages).
7. Whether **payout/balance reads** have a literal OAuth scope string.
8. **Retry semantics for Pub/Sub & EventBridge** webhook delivery (vs the HTTPS
   8-retries/4-hours figure).
9. The full enumerated value lists for several enums
   (`OrderDisplayFinancialStatus`, `BulkOperationErrorCode`, `DisputeType/Status`)
   were not read field-by-field.

## Risks for future architecture

- **Stale/outdated figures:** widely repeated numbers can be wrong against the
  *current* official docs — e.g. the webhook retry policy is **8 retries / 4
  hours** (not "19/48h"), and the Plus **REST bucket is 400** (not "80"). Always
  cite the live page; mark unconfirmed numbers as open questions.
- **Version-independent policy drift:** limits, retry counts, and review
  thresholds can change **without an API-version bump**; cached numbers may drift.
- **Breaking version changes:** the `@idempotent` requirement (2026-04) and the
  bulk-operation concurrency change (2026-01) show that pinning a version and
  tracking the changelog is essential.
- **`productSet` delete-on-omit** of list fields is a **data-loss footgun** if
  treated as a partial update.
- **Webhook-only designs risk silent data drift**; a missing reconciliation job
  is a correctness bug, not an optimization.

## Research gaps

- GraphQL **enum value lists** and several **mutation input schemas** were
  summarized, not read field-by-field; confirm via the reference pages or schema
  introspection before implementation.
- **REST/legacy deprecation timelines** (products, fulfillment) need a directly
  fetched official deadline page.
- **Storefront API**, **Payments Apps API**, and **Customer Account API** limits
  and cost models were noted only incidentally; deeper Tier-1 notes are out of
  this sprint's scope.

## Sources

All accessed **2026-06-30**, all `shopify.dev` (Tier 1):

- API overview / strategy: `/docs/api/admin`, `/docs/apps/build/graphql/migrate`,
  `/docs/api/admin-rest`,
  `/changelog/starting-april-2025-new-public-apps-submitted-to-shopify-app-store-must-use-graphql`
- Versioning: `/docs/api/usage/versioning`,
  `/docs/api/admin-rest/usage/versioning`, `/docs/api/usage/versioning/api-health`
- Auth & scopes: `/docs/apps/build/authentication-authorization` (+ `/access-tokens`,
  `/access-tokens/authorization-code-grant`, `/access-tokens/token-exchange`,
  `/session-tokens`), `/docs/api/usage/access-scopes`,
  `/docs/apps/build/authentication-authorization/app-installation/manage-access-scopes`
- Limits / cost: `/docs/api/usage/limits` (canonical; `/usage/rate-limits`
  redirects here), `/docs/api/admin-rest/usage/rate-limits`
- Bulk ops: `/docs/api/usage/bulk-operations/queries`, `/…/imports`,
  `/docs/api/admin-graphql/latest/objects/BulkOperation`
- Webhooks: `/docs/apps/build/webhooks` (+ `/subscribe`, `/subscribe/https`,
  `/verify-deliveries`, `/best-practices`),
  `/docs/apps/build/compliance/privacy-law-compliance`
- Products/variants: `/docs/api/admin-graphql/latest/objects/Product`,
  `/…/ProductVariant`, `/…/mutations/productSet`, `/…/mutations/productVariantsBulkCreate`,
  `/docs/apps/build/product-merchandising/products-and-collections`,
  `/changelog/the-product-variant-limit-is-now-2048-for-all-merchants`
- Inventory: `/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states`,
  `/docs/api/admin-graphql/latest/objects/InventoryItem` (+ `/InventoryLevel`,
  `/Location`), `/…/mutations/inventorySetQuantities`, `/…/inventoryAdjustQuantities`
- Orders: `/docs/api/admin-graphql/latest/objects/Order`,
  `/docs/apps/launch/protected-customer-data`,
  `/changelog/apps-now-need-shopify-approval-to-read-orders-older-than-60-days`
- Fulfillment: `/docs/apps/build/orders-fulfillment/migrate-to-fulfillment-orders`,
  `/…/fulfillment-service-apps`, `/…/mutations/fulfillmentcreate`,
  `/…/mutations/fulfillmenttrackinginfoupdate`
- Refunds/returns: `/…/mutations/refundcreate`, `/…/objects/Refund`,
  `/…/objects/Return`, `/…/mutations/returnCreate`, `/…/mutations/returnApproveRequest`,
  `/…/objects/RefundLineItem`
- Transactions/payouts: `/…/objects/OrderTransaction`, `/…/enums/OrderTransactionKind`,
  `/…/queries/shopifypaymentsaccount`, `/…/objects/shopifypaymentspayout`,
  `/…/objects/ShopifyPaymentsDispute`
- App review: `/docs/apps/launch/shopify-app-store/app-store-requirements`,
  `/docs/apps/launch/built-for-shopify/requirements`

**DEC-007 propagated facts, accessed 2026-07-02** (see that section above):
`/docs/api/admin-graphql/latest/objects/Order` (tax/shipping/discount fields),
`/docs/api/admin-graphql/latest/input-objects/FulfillmentInput`,
`/docs/api/admin-graphql/latest/mutations/fulfillmentTrackingInfoUpdate`.

**Part E pre-implementation research patch, accessed 2026-07-04** (see that
section above): `/docs/api/admin-graphql/latest/objects/MoneyBag`,
`/docs/api/admin-graphql/latest/objects/Order` (currency/money fields),
`/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic`
(product-domain topics).

Captured excerpts: [`../00-source-materials/shopify-official.md`](../00-source-materials/shopify-official.md).

---

## Delta refresh — 2026-07-16 (Fable gap-closure mission)

A targeted Tier-1 refresh against API version **2026-07** was captured in
[`../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md).
Net-new evidence relative to this file's baseline: complete
`OrderDisplayFinancialStatus` (8 values) with COD-relevant `PENDING`
semantics; `OrderTransaction.manualPaymentGateway` as the COD/manual-gateway
discriminator; `orderMarkAsPaid`/`orderCreateManualPayment` (Partial);
**AbandonedCheckout object + abandonedCheckouts query verified to exist in
2026-07** (recovery_state, completedAt); complete four-family fulfillment
state model incl. `FulfillmentEventStatus` (11 values) and deprecations
(`OPEN`/`PENDING` on Fulfillment; `OPEN`/`PENDING_FULFILLMENT`/`RESTOCKED`
on order summary); `fulfillmentCreateV2` deprecation confirmed; fulfillment
origin-attribution surface (`BasicEvent.attributeToApp`/`appTitle`,
`FulfillmentHold.heldByApp`; no app field on Fulfillment itself);
order-edit `CalculatedOrder` flow + `orders/edited`; current rate-limit
restore rates and the "falls forward to oldest accessible version"
unsupported-version behavior. Open questions are consolidated in the capture
§13. No prior claim in this file was found contradicted; the 2026-07-10
capture remains valid.
