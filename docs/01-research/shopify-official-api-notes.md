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

Captured excerpts: [`../00-source-materials/shopify-official.md`](../00-source-materials/shopify-official.md).
