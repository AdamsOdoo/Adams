# RB-14 Official-Source Refresh (Architecture Topics Only)

> **RB-14 Architecture Preparation — Part 1.** A **current official-source refresh**
> of the Tier-1 Shopify/Odoo facts that bear on the three architecture rows framed
> this sprint — **AR-002** (distribution/API), **AR-003** (orchestration/queue), and
> **AR-005** (binding/dedup/identity). It **refreshes and dates** the platform facts;
> it makes **no architecture decision**. The Sprint B baselines
> ([`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md),
> [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md))
> remain the full technical record; this document is the **delta + dated
> confirmation** for the architecture topics.

## Scope and date

- **Access date for this refresh:** **2026-07-01** (one day after the Sprint B
  baseline of 2026-06-30).
- **Scope:** only the official facts needed to **frame** AR-002/AR-003/AR-005 — not
  a full re-survey. Non-architecture areas (full refund/return enums, payouts depth,
  App-Store performance budgets) were not re-fetched and keep their Sprint B status.
- **Method:** a scoped, documented high-power fan-out (13 official-source verifiers,
  ~40 pages, one topic each) fetched the pages live and returned **verbatim-quoted,
  claim-classified** facts. Classification and synthesis are **worker-owned** (central
  governance of claim class). Competitor evidence was **excluded** from this refresh.
- **Governance:** no-code gate and no-decision gate in force (`CLAUDE.md` §4–§5).

## Sources used (Tier-1 only)

- **Shopify:** `shopify.dev` — `/docs/apps/build/graphql/migrate`, `/docs/api/admin-rest`,
  `/docs/api/usage/versioning` (+ `/api-health`), `/docs/api/admin-graphql/latest/mutations/productSet`,
  `/objects/Product`, `/objects/ProductVariant`, `/docs/apps/build/product-merchandising/products-and-collections`,
  `/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states`,
  `/mutations/inventorySetQuantities`, `/mutations/inventoryAdjustQuantities`,
  `/objects/Order`, `/enums/OrderDisplayFinancialStatus`, `/enums/OrderDisplayFulfillmentStatus`,
  `/docs/apps/launch/protected-customer-data`, `/docs/api/usage/access-scopes`,
  `/docs/apps/build/webhooks` (+ `/subscribe/https`, `/verify-deliveries`, `/best-practices`),
  `/docs/api/usage/limits`, `/docs/api/admin-rest/usage/rate-limits`,
  `/docs/api/usage/bulk-operations/queries` (+ `/imports`),
  `/docs/apps/build/authentication-authorization` (+ `/access-tokens` + `/online-access-tokens`
  + `/offline-access-tokens`), `/docs/apps/launch/shopify-app-store/app-store-requirements`,
  `/docs/apps/build/privacy-law-compliance`, `/docs/api/usage/gids`.
- **Odoo:** `odoo.com/documentation/19.0` and, where the HTML rendered navigation-only
  (JS-render caveat), the **official `odoo/documentation` 19.0-branch raw RST source**
  (`raw.githubusercontent.com/odoo/documentation/19.0/content/...`) — the same sanctioned
  fallback used in Sprint B. Pages: `developer/reference/backend/{actions,orm,data,security}.rst`,
  `developer/reference/cli.rst`, `developer/glossary.html`,
  `administration/on_premise/deploy.rst`, `administration/odoo_sh/getting_started/branches.rst`.

> **Source-type note:** all Shopify claims are **official developer documentation**
> (Tier-1). All Odoo claims are **official 19.0 documentation** (Tier-1), read from
> odoo.com where it rendered and from the official 19.0 RST source where the HTML was
> JS-nav-only. **No competitor, blog, or forum source is used as a fact here.**

## Classification key (per `CLAUDE.md` §8 and the RB-14 prompt)

Every factual claim below carries: **source URL**, **source type** (official
Shopify / official Odoo), **access date** (2026-07-01), and **claim class** —
`[Official fact]`, `[Official limitation]`, `[Inference from official fact]`, or
`[Open question]`. (Competitor classes are **not** used in this refresh document.)

---

## Shopify official facts (refreshed 2026-07-01)

### AR-002 — API strategy, versioning, products/productSet, auth, distribution

- `[Official fact]` "All apps and integrations should be built with the GraphQL Admin
  API." — `shopify.dev/docs/apps/build/graphql/migrate`.
- `[Official fact]` "The REST Admin API is a legacy API as of October 1, 2024."
  (stated on both `…/graphql/migrate` and `…/docs/api/admin-rest`);
  `[Official limitation]` "The REST Admin API is in maintenance mode and receives only
  critical updates." — `…/graphql/migrate`.
- `[Official limitation]` "Starting April 1, 2025, all new public apps must be built
  exclusively with the GraphQL Admin API." — `…/docs/api/admin-rest` (also on
  `…/app-store-requirements`).
- `[Open question]` The GraphQL-only mandate is scoped to **"new public apps"**; no
  fetched page literally states it binds **custom/private apps**. A custom app is not
  officially *forbidden* from REST, but REST is legacy/maintenance-mode and all apps
  "should" use GraphQL. — `…/docs/api/admin-rest`.
- `[Official fact]` Versioning: "Shopify releases a new API version every three months
  at the beginning of the quarter, at 5pm UTC"; "Version names are date-based (for
  example, `2026-04`)"; "Each stable version is supported for a minimum of 12 months,
  with at least nine months of overlap between consecutive versions"; fall-forward —
  "If your app targets an inaccessible version, Shopify falls forward and responds
  using the oldest accessible stable version." — `…/docs/api/usage/versioning`.
- `[Official limitation]` API health / "Fix overdue": continuing to call unsupported
  APIs after the deprecation date can lead to "delisting the app from the Shopify App
  Store, blocking new installations, notifying users that the app doesn't work, or
  providing users with alternative app recommendations." — `…/versioning/api-health`.
- `[Official limitation]` **`productSet` is a full-state write for list fields:** "For
  list fields: Creates new entries, updates existing entries, and deletes existing
  entries that aren't included in the mutation's input." `[Official fact]` For scalars:
  "For all other field types: Updates only the included fields. Any omitted fields will
  remain unchanged." — `…/mutations/productSet`. (i.e. **delete-on-omit applies to list
  fields only** — variants/options/media/collections/metafields — not scalars.)
- `[Official fact]` `productSet` "synchronous" defaults to `true`; `synchronous:false`
  returns a `productSetOperation` and "should be used if you are experiencing
  timeouts." Default per-product limit is "2048 product variants for each product." —
  `…/mutations/productSet`; per-product options cap is shop-resource-limit-driven
  (`Shop.resourceLimits`), **not a fixed literal on these pages**. — `…/objects/Product`.
- `[Official fact]` Auth: "OAuth 2.0 is the industry-standard protocol"; "two ways for
  apps to acquire an access token: token exchange and authorization code grant"; token
  exchange uses a **session token** (embedded/App Bridge), authorization code grant is
  for **standalone apps**; **admin-created custom app tokens** are "installed upon
  generation in the Shopify admin." — `…/authentication-authorization` (+ `/access-tokens`).
- `[Official fact]` Token lifetimes: **online** tokens "expire either when the user logs
  out or after 24 hours"; **legacy offline** tokens "remain valid indefinitely until app
  is uninstalled or secret revocation"; **new "Expiring offline tokens"** rotate via a
  refresh token with a "90-day refresh token lifetime." — `…/access-tokens/online-access-tokens`,
  `…/access-tokens/offline-access-tokens`.
- `[Official limitation]` App-Store requirements: OAuth "immediately … before any other
  steps occur"; "valid TLS/SSL certificate without any errors"; new public apps
  GraphQL-only; "Shopify App Pricing or the Shopify Billing API for any app charges";
  latest App Bridge (`app-bridge.js`) "As of March 13th, 2024"; consistent embedded
  experience. — `…/app-store-requirements`.
- `[Official limitation]` App-Store apps "must respond to data subject requests,
  regardless of whether the app collects personal data" and implement the **three
  mandatory compliance webhooks** — `customers/data_request`, `customers/redact`,
  `shop/redact` (the last "48 hours after a store owner uninstalls your app"); ack
  200-series and "Complete the action within 30 days." — `…/privacy-law-compliance`.
- `[Official fact]` Shopify's fetched privacy/App-Store docs state the **mandatory
  compliance webhooks are required for apps listed/distributed through the Shopify App
  Store**. — `…/privacy-law-compliance`, `…/app-store-requirements`.
- `[Inference]` A custom/Admin-created app gets its token in the admin (no OAuth install
  flow) and is **outside the App-Store review path**, so the **App-Store submission gate
  itself** (OAuth-immediately / GraphQL-only / compliance-webhook *review* requirements)
  may not apply to it — framing input for the public-vs-custom AR-002 fork.
- `[Open question]` **Do not conclude that privacy / data-deletion obligations are absent
  for custom/private apps.** Whether (and which) non-App-Store privacy/GDPR obligations
  apply to a custom deployment is **unconfirmed** and must be verified before an AR-002
  distribution decision — the App-Store *review* gate not applying is **not** the same as
  privacy obligations being absent.

### AR-003 — webhooks, rate limits, bulk operations

- `[Official limitation]` "Webhook delivery isn't always guaranteed, and your app can
  miss or mishandle events"; `[Official limitation]` "Your app shouldn't rely on
  receiving data from Shopify webhooks"; `[Official fact]` "use reconciliation jobs to
  periodically fetch data from Shopify so that your app stays consistent." —
  `…/webhooks` (+ `/subscribe/https`).
- `[Official limitation]` "Shopify has a one-second connection timeout and a five-second
  timeout for the entire request"; ack with "200 OK"; `[Official fact]` "If Shopify
  receives no response or an error, it retries 8 times over the next 4 hours";
  `[Official limitation]` "After 8 consecutive failures, the subscription is
  automatically deleted if it was configured using the Admin API." — `…/webhooks/subscribe/https`.
- `[Official fact]` HMAC: "Each HTTPS delivery includes a base64-encoded HMAC signature
  in the `X-Shopify-Hmac-SHA256` header, generated using your app's client secret and
  the raw request body"; "Always verify HMAC before trusting payload contents"; compute
  "HMAC-SHA256 of the raw request body"; use a constant-time compare; reject mismatches.
  `[Official limitation]` "HMAC verification requires the raw request body" (a body
  parser like `express.json()` breaks it). — `…/webhooks/verify-deliveries`.
- `[Official fact]` "Shopify minimizes duplicate deliveries, but your app might receive
  the same webhook more than once"; "Process webhooks using idempotent operations"; "Use
  the `X-Shopify-Webhook-Id` header to detect and skip duplicates." `X-Shopify-Event-Id`
  correlates deliveries "from the same merchant action" (not the dedup key). —
  `…/webhooks/verify-deliveries`.
- `[Official fact]` GraphQL cost: "Every field in the schema has an integer cost value";
  mutations cost 10, objects 1, scalars/enums 0, connections sized by `first`/`last`;
  `[Official limitation]` "A single query may not exceed a cost of 1,000 points,
  regardless of plan limits." Restore rates per plan: Standard 100, Advanced 200, Plus
  1000, Enterprise (Commerce Components) 2000 points/second; live state in
  `extensions.cost.throttleStatus`. — `…/docs/api/usage/limits`.
- `[Official fact]` REST: "All Shopify APIs use a leaky bucket algorithm"; Standard 2
  req/s (bucket 40), Advanced 4 req/s, Plus 20 req/s (bucket 400), Enterprise 40 req/s;
  "a 429 Too Many Requests error and a Retry-After header are returned"; consumption via
  `X-Shopify-Shop-Api-Call-Limit` (e.g. `32/40`). Cross-API: array inputs max 250; object
  pagination capped at 25,000. — `…/docs/api/admin-rest/usage/rate-limits`; `…/usage/limits`.
- `[Official fact]` Bulk operations run async, deliver JSONL; "In API versions `2026-01`
  and higher apps can run up to five bulk query operations … and up to five bulk mutation
  operations at a time per shop" (prior: one at a time); import JSONL "can't exceed 100MB";
  mutation must finish within 24 hours, query within 10 days; the "`bulkOperationRunMutation`
  request isn't" subject to standard rate limits (only submit/poll/cancel cost quota). —
  `…/usage/bulk-operations/queries`, `/imports`.

### AR-005 — inventory identity, orders, GIDs, idempotency

- `[Official fact]` Quantity states: `incoming, on_hand, available, committed, reserved,
  damaged, safety_stock, quality_control`; "`on_hand` … equals the sum of … `available`,
  `committed`, `reserved`, `damaged`, `safety_stock`, `quality_control`" (incoming
  excluded). `[Official limitation]` "You can't use the Admin API to adjust or move
  inventory quantities in the `committed` state … only affected by the creation and
  fulfillment of a merchant's orders." — `…/manage-quantities-states`.
- `[Official fact]` `inventorySetQuantities` compare-and-set: "the mutation will only
  update the quantity if the persisted quantity matches the `compareQuantity` value";
  mismatch "will return an error"; `ignoreCompareQuantity:true` opts out but "can lead to
  inaccurate inventory quantities if multiple requests are made concurrently." Both
  set/adjust operate per `inventoryItemId` + `locationId`. `inventoryAdjustQuantities`
  applies "incremental changes … a delta value rather than setting an absolute amount." —
  `…/mutations/inventorySetQuantities`, `…/mutations/inventoryAdjustQuantities`.
- `[Official fact]` `[Official limitation]` **`@idempotent` timeline (material):** on
  both `inventorySetQuantities` and `inventoryAdjustQuantities` the idempotency key was
  "**optional**" as of `2026-01` and is "**required** … must be provided using the
  `@idempotent` directive" **as of `2026-04`**. — `…/mutations/inventorySetQuantities`,
  `…/mutations/inventoryAdjustQuantities`.
- `[Official fact]` Orders: "Only the last 60 days' worth of orders … accessible from the
  `Order` object by default"; `read_all_orders` grants all orders but "You need to request
  permission for this access scope from your Partner Dashboard." Reading orders requires
  `read_orders` (or `read_marketplace_orders`/`read_quick_sale`). — `…/objects/Order`,
  `…/usage/access-scopes`.
- `[Official fact]` Enums: `OrderDisplayFinancialStatus` = `AUTHORIZED, EXPIRED, PAID,
  PARTIALLY_PAID, PARTIALLY_REFUNDED, PENDING, REFUNDED, VOIDED` (8);
  `OrderDisplayFulfillmentStatus` = `FULFILLED, IN_PROGRESS, ON_HOLD, OPEN,
  PARTIALLY_FULFILLED, PENDING_FULFILLMENT, REQUEST_DECLINED, RESTOCKED, SCHEDULED,
  UNFULFILLED` (10; `OPEN` and `RESTOCKED` are noted "Replaced by 'UNFULFILLED'"). —
  `…/enums/OrderDisplayFinancialStatus`, `…/enums/OrderDisplayFulfillmentStatus`.
- `[Official fact]` Protected customer data fields requiring elevated handling: name,
  address (line1/line2/geolocation/zip, billing+shipping), email, phone; **Level 1** =
  minimization/transparency/consent/encryption-at-rest-and-in-transit; **Level 2** adds
  encrypted backups, separated test/prod data, DLP, staff-access limits, access log,
  incident-response policy. — `…/protected-customer-data`.
- `[Official fact]` Identity: "A global ID is an application-wide uniform resource
  identifier (URI) that uniquely identifies an object"; format `gid://shopify/{object_name}/{id}`
  (some parameterized, e.g. `gid://shopify/InventoryLevel/123?inventory_item_id=456`);
  REST↔GID mapping via `admin_graphql_api_id` (on "most" REST resources) and
  `legacyResourceId` (on "most" GraphQL objects). — `…/docs/api/usage/gids`.
- `[Official fact]` `ProductVariant.sku` is "A case-sensitive identifier for the product
  variant"; `ProductVariant.inventoryItem` is non-null (`InventoryItem!`) →
  `[Inference from official fact]` a **1:1 variant↔InventoryItem** relationship. —
  `…/objects/ProductVariant`.
- `[Open question]` The `/usage/gids` page makes **no statement that GIDs are stable /
  permanent / non-reused** — GID permanence is **not asserted**. — `…/docs/api/usage/gids`.
- `[Open question]` No fetched page documents a **client-mutation-id / general mutation
  idempotency** mechanism beyond the `@idempotent` directive on specific mutations; the
  required-uniqueness scope and server-side dedup retention of the `@idempotent` key are
  also not stated. — `…/webhooks/verify-deliveries`, `…/mutations/inventorySetQuantities`.

---

## Odoo official facts (refreshed 2026-07-01)

### AR-003 — cron reliability, queue absence, hosting

- `[Official limitation]` "If a scheduled action encounters an error or a timeout three
  consecutive times, it will skip its current execution and be considered as failed";
  "If a scheduled action fails its execution five consecutive times over a period of at
  least seven days, it will be deactivated and will notify the DB admin"; "A hard-limit
  exists for the cron execution at the database level after which the process executing
  cron jobs is killed." — `.../backend/actions.rst`.
- `[Official fact]` Batching: "split the processing so that each call makes progress";
  "A batch should process one or many records and should generally take no more than *a
  few seconds*"; "Work is committed by the framework after each batch. The framework will
  call the function as many times as necessary … Do not reschedule yourself the job";
  progress via `IrCron._commit_progress` (returns seconds remaining; 0 → return ASAP).
  Run via `method_direct_trigger` or `_trigger` (test via `method_direct_trigger`). —
  `.../backend/actions.rst`.
- `[Open question]` The exact `_trigger(at=None)` signature is rendered via
  `.. automethod::` (not literal in the RST) and could not be confirmed on the JS-rendered
  odoo.com HTML this pass — confirm against `ir_cron.py` if load-bearing.
- `[Official fact]` Queue substrate: `--max-cron-threads` "number of workers dedicated to
  cron jobs. Defaults to *2*"; cron workers are threads (multi-threading) or separate
  processes (multi-processing, "in addition to the HTTP worker processes"). —
  `.../reference/cli.rst`, `.../on_premise/deploy.rst`.
- `[Official limitation]` Under WSGI, "Odoo … can not setup cron or livechat workers";
  "Starting one of the built-in Odoo servers next to the WSGI server is required to
  process cron jobs"; "must be configured to only process crons and not HTTP requests
  using the `--no-http` … option." — `.../on_premise/deploy.rst`.
- `[Inference from official fact]` Odoo 19 **core documents only `ir.cron`** for
  background/scheduled execution and **no general-purpose async job queue**; the queue
  **absence is inferred from documented scope**, not a positive statement. Any durable
  async/retry queue (e.g. OCA `queue_job`) is **community, not official** — never cite it
  as core. — `.../backend/actions.rst`.
- `[Official limitation]` Odoo.sh **staging** is a "neutralized duplicate": neutralization
  disables "Scheduled actions, Outgoing emails, IAP services, Payment providers and
  shipping connectors"; "To test them, trigger them manually or re-enable them." Three
  stages: production (only one), staging, development. — `.../odoo_sh/getting_started/branches.rst`.
- `[Open question]` Whether **Odoo Online (SaaS)** supports custom modules,
  `server_wide_modules`, or external/background workers is **not covered** by the fetched
  on-prem/Odoo.sh pages — **hosting-tier feasibility remains open** and is not finalized.

### AR-005 / AR-002 — external IDs, ORM extension, security

- `[Official fact]` An external identifier (XML ID) is a "string identifier stored in
  `ir.model.data`, can be used to refer to a record regardless of its database identifier";
  form `module.name`; `noupdate` data is "applied only once"; `forcecreate` (update mode)
  "whether the record should be created if it doesn't exist … defaults to `True`." —
  `developer/glossary.html`, `.../backend/data.rst`.
- `[Official fact]` `[Official limitation]` Model extension: in-place `_inherit` "without
  … `_name`" replaces/extends the model in place; `_inherits` (delegation) is "has one …
  methods are *not* inherited, only fields," and "avoid it if you can; chained `_inherits`
  is essentially not implemented." — `.../backend/orm.rst`.
- `[Open question]` The **`ir.model.data` column list** (`name/module/model/res_id`) and
  the **`(module, name)` uniqueness constraint** are **not literally stated** on the
  glossary/data/orm pages — load-bearing for reusing `ir.model.data` as a binding store;
  **verify against the 19.0 base `ir_model.py` source** before any AR-005 decision.
- `[Official fact]` Security: `ir.model.access` **grants** model-level CRUD, is
  **additive (union across a user's groups)**, and all `perm_*` are **unset by default**
  (deny-by-default); an empty `group_id` grants to **every user**. `ir.rule` record rules
  are **default-allow**, evaluated record-by-record after access rights; **global rules
  intersect (AND)** ("adding global rules always restricts access further"), **group rules
  unify (OR)** ("cannot expand beyond … global rules"); "Creating multiple global rules is
  risky … non-overlapping rulesets … remove all access." Field-level `groups` removes
  restricted fields from views/`fields_get` and raises on explicit access. `company_ids`
  is available in rule domains for company scoping. — `.../backend/security.rst`.
- `[Open question]` **`sudo()` bypassing both access rights and record rules is NOT
  literally stated on `security.rst`** (it appears only in code examples; a TODO notes
  field `groups` apply to the Superuser in `fields_get` but "not in read/write"). The
  Sprint B note asserted the bypass citing the security page — **treat the bypass as a
  to-re-verify item** (likely on the ORM/Environment `sudo` docs) rather than an
  un-sourced fact.
- `[Open question]` **No official credential/secret storage recommendation** was found in
  the fetched Odoo docs — `ir.config_parameter` vs a dedicated config model vs an
  encrypted field is **not** presented as an official recommendation. `[Inference]` Any
  credential-storage design must be protected by access rights / groups (field-level
  `groups` on credential fields) and **verified before implementation**. — `.../backend/security.rst`.

---

## Version-sensitive facts (flag for architecture)

- `[Official fact]` The GraphQL Admin API **`latest` alias currently resolves to
  `2026-07`** (page metadata across productSet/Product/ProductVariant/inventory pages).
  The versioning table now spans **`2025-07` … `2027-01`**. **Version-sensitive:** any
  pinned version and the "current stable" differ over time; pin an explicit `YYYY-MM` and
  budget an upgrade inside the ≥9-month overlap.
- `[Official fact]` **`@idempotent` is required as of `2026-04`** (optional from
  `2026-01`) on `inventorySetQuantities` / `inventoryAdjustQuantities`; since `latest =
  2026-07`, an app on `latest` **must** send the directive on these writes.
- `[Official fact]` **Bulk-operation concurrency** rose to **up to 5 of each** in
  `2026-01` (was one at a time) — version-gated behaviour a backfill design must branch on.
- `[Official fact]` **Dual offline-token model** — legacy non-expiring **and** new
  "Expiring offline tokens" (90-day refresh) — so "offline tokens never expire" is only
  true for the legacy variant; the token-lifecycle design must not assume permanent tokens.
- `[Official fact]` App Bridge (`app-bridge.js`) required for App-Store apps **as of
  2024-03-13**; new public apps GraphQL-only **as of 2025-04-01** — dated obligations for
  the public-distribution option.

## Facts changed since Sprint B (2026-06-30)

- **`latest` alias moved 2026-04 → 2026-07** (Sprint B read `latest` = `2026-04`). No
  behavioural fact changed with it; the alias is simply current. **Flagged.**
- **`@idempotent` requirement detail sharpened:** Sprint B recorded "required as of
  2026-04"; the refresh **confirms** this and adds the **"optional as of 2026-01 →
  required as of 2026-04"** timeline. Not a contradiction — a sharpening.
- **`productSet` delete-on-omit scoped to list fields:** the refresh adds the explicit
  companion "For all other field types … omitted fields will remain unchanged," i.e.
  **scalars are safe-update; delete-on-omit is list-fields-only.** A refinement, not a
  reversal, of the Sprint B footgun note.
- **Offline tokens now explicitly dual** (legacy non-expiring + expiring-with-90-day-
  refresh) — Sprint B mentioned the expiring variant; the refresh confirms both are
  first-class and current.
- **API-health navigation** now described via the **Dev Dashboard** (Apps → Monitoring →
  API health); the "Partner Dashboard" wording the FOCUS anticipated was not on the page.
  Cosmetic/navigation only.
- **No other change observed** on the load-bearing facts.

## Facts unchanged since Sprint B (re-confirmed current 2026-07-01)

- REST legacy (2024-10-01) + "all apps should use GraphQL" + new-public-apps GraphQL-only
  (2025-04-01); versioning cadence/format/support-window/fall-forward.
- Webhook delivery not guaranteed → reconciliation required; 1s/5s timeout; 8 retries/4h;
  auto-delete after 8 consecutive failures (Admin-API subscriptions); HMAC-SHA256 raw
  body; `X-Shopify-Webhook-Id` dedup; idempotent handlers.
- Rate limits (GraphQL cost model + per-plan restore rates + 1,000-point single-query
  ceiling; REST leaky bucket + 429/`Retry-After`); bulk-ops JSONL/size/time model.
- Inventory quantity states + `on_hand` sum + `committed` API-read-only + compare-and-set;
  `InventoryItem → InventoryLevel (per Location)` chain; per-`(inventoryItemId, locationId)`
  writes; 1:1 variant↔InventoryItem.
- Orders 60-day window + `read_all_orders` approval; protected-customer-data Level 1/2.
- GID format + REST↔GID mapping fields; webhook-ID dedup procedure.
- Odoo: `ir.cron` failure model (3→skip; 5-over-7-days→deactivate+notify); batching +
  `_commit_progress`; only `ir.cron` documented in core (no general-purpose async queue
  documented — an [Inference from official fact]; `queue_job` is community); `--max-cron-threads`=2;
  WSGI separate cron process; external IDs in `ir.model.data`; in-place `_inherit` vs
  discouraged `_inherits`; access-rights/record-rules semantics; Odoo.sh staging
  neutralization.

## High-risk facts requiring ChatGPT verification

1. **Custom-vs-public GraphQL mandate** — the GraphQL-only "must" is stated only for
   **new public apps**; the custom/private-app scope is an **[Open question]** that
   changes whether a REST-hybrid is even permissible for a custom deployment (AR-002).
2. **GID permanence** — Shopify does **not** assert GID stability/non-reuse; AR-005
   should **not** treat GID as a hard immutable uniqueness invariant until verified
   (affects deleted/recreated-record handling).
3. **No general mutation idempotency** — beyond `@idempotent` on specific mutations,
   there is **no client-mutation-id**; outbound write idempotency must be **connector-
   designed** (AR-005/AR-006), not assumed from the platform.
4. **`@idempotent` required now** — inventory set/adjust writes on `latest`(=2026-07)
   **must** carry the directive; the required-uniqueness scope + server dedup TTL are
   **[Open question]** (AR-005/AR-006).
5. **`ir.model.data` uniqueness/columns unconfirmed** — the `(module,name)` uniqueness
   and column list are **not in the official docs**; verify against 19.0 source before
   any binding decision leans on reusing `ir.model.data` (AR-005).
6. **`sudo()` bypass not on `security.rst`** — the "bypasses access rights + record
   rules" fact needs re-sourcing (ORM/Environment docs) before a credential-security
   design relies on it (AR-002/AR-005).
7. **Odoo Online feasibility** — whether SaaS supports custom modules / server-wide
   modules / external workers is **[Open question]**; it gates the AR-003 substrate and
   the AR-002 hosting inputs. **Hosting is not finalized.**

## Open official-source questions (for a later verification pass)

- Custom/private-app binding of the GraphQL-only mandate; any REST **sunset** date
  beyond the 2024-10-01 legacy date.
- Exact retirement dates per listed version; whether a `latest`/`stable` **string alias**
  is officially supported vs always pinning `YYYY-MM`.
- Per-plan **GraphQL bucket capacity** (`maximumAvailable`) as a static table (only
  restore rates are published; capacity is runtime-only via `throttleStatus`).
- Numeric **per-product options cap** (delegated to `Shop.resourceLimits`).
- `@idempotent` **key-uniqueness scope + server dedup TTL**; GID **permanence** guarantee.
- Odoo **`ir.model.data`** column list + `(module,name)` uniqueness; official **`sudo()`
  bypass** statement; official **credential-storage** recommendation; the
  `howto/company/security` **multi-company record-rule** pattern.
- **Odoo Online** custom-module / worker / outbound-HTTPS support.

## Implications for AR-002 / AR-003 / AR-005 (framing, not decisions)

- **AR-002 (distribution/API):** the official record cleanly supports a **GraphQL-first**
  framing (REST legacy; "all apps should use GraphQL"; new public apps GraphQL-only) **but
  leaves the custom-app REST question open** — so distribution (public vs custom) should
  be framed as the **prior** decision that sets the API constraints. `productSet`
  delete-on-omit (list fields) makes a **preview/dry-run + reliable binding** a
  correctness requirement for the controlled export path. Public distribution imports a
  heavy, dated obligation bundle (OAuth-immediately, TLS, GraphQL-only, Billing API, App
  Bridge, 3 compliance webhooks, protected-data Level 2); a custom app is **outside the
  App-Store review path** so those *submission gates* may not apply — but **non-App-Store
  privacy/data-deletion obligations for custom apps are an [Open question], not assumed
  absent**. See [`ar-002-distribution-api-framing.md`](./ar-002-distribution-api-framing.md).
- **AR-003 (orchestration/queue):** webhooks-not-guaranteed → **reconciliation is
  mandatory, not optional**; the 5s timeout → **fast-ack + out-of-band processing**; the
  8-consecutive-failure auto-delete (Admin-API subs) + Odoo cron auto-deactivation (5/7d)
  mean the connector needs its **own durable job/queue state + external observability**;
  Odoo core provides **only `ir.cron`** (queue is a community dependency), and **Odoo
  Online feasibility is open** — so the substrate is a real, hosting-coupled decision.
  (**[Inference from official fact]** the async-queue absence is inferred from the
  documented scope — docs document only `ir.cron`; `queue_job` is community, not core.)
  See [`ar-003-sync-orchestration-framing.md`](./ar-003-sync-orchestration-framing.md).
- **AR-005 (binding/dedup/identity):** the **GID** is the natural canonical Shopify key
  (with REST↔GID mapping fields), **webhook-ID** is the per-delivery dedup key,
  **`@idempotent`** is now required on inventory writes, and **outbound write idempotency
  must be connector-designed** (no general mutation idempotency). **GID permanence** and
  **`ir.model.data` uniqueness** are unverified, so the binding model must not assume
  either; per-store isolation should use a **global record rule** (AND-intersect), not
  group rules. See [`ar-005-binding-dedup-framing.md`](./ar-005-binding-dedup-framing.md).

## No decisions made

This refresh **decides nothing**. It dates and confirms the official facts, flags the
version-sensitive and changed items, and routes the implications to the three framing
documents. AR-002/AR-003/AR-005 remain **[Not decided] / Evidence pending**; the no-code
and no-decision gates hold (`CLAUDE.md` §4–§5; RB-14).
