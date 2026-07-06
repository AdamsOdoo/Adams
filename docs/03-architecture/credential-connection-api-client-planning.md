# Credential, Connection, and API Client Planning

> Implementation-planning package for the Odoo 19 ↔ Shopify Connector
> credential storage, connection lifecycle, test connection, readiness
> checks, API-client boundary, and redaction/no-logging foundation.
> Prepared 2026-07-06 on branch
> `claude/credential-connection-foundation-planning`, from
> `Shopify-connector` at PR #91's merge commit
> `143108585e802ee3e91d9f0c61f1828538734f47` (PR #90 and PR #91 both
> confirmed merged before starting). Companion documents:
> [`mbq-04-credential-persistence-decision-proposal.md`](./mbq-04-credential-persistence-decision-proposal.md)
> (the accepted MBQ-04 posture this builds on),
> [`../01-research/odoo-credential-storage-official-notes.md`](../01-research/odoo-credential-storage-official-notes.md)
> (the accepted Odoo evidence base),
> [`../07-implementation-plan/credential-connection-foundation-task-plan.md`](../07-implementation-plan/credential-connection-foundation-task-plan.md)
> (the future-task sequencing built from this document), and
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-024**, this package's own review-log row).

## Acceptance

- **Accepted by ChatGPT on 2026-07-06, at implementation-planning level
  only** (PR #92 acceptance patch; [`AR-024`](../05-qa/architecture-review-log.md)).
- **Option C — the dedicated Admin-only `shopify.connector.store.credential`
  model — is accepted at planning level**, explicitly as **a justified
  post-AR-022 addition to the previously accepted AR-019 six-core-model
  plan** (AR-019 §11 named exactly this revisit condition: "a future
  MBQ-04 decision may add a credential model later" — met by AR-022).
- **The redaction/no-logging contract is accepted at planning level.**
- **Task 002 is accepted as the recommended next coding task — not
  authorized by this acceptance.**
- **Task 003 is accepted as the proposed follow-up task — not authorized
  by this acceptance.**
- **No implementation gate is opened. No code is authorized.**
- **The following seven decision points remain open** and must be
  resolved before or inside the relevant future final `CLAUDE.md` §9 task
  prompt(s): the compute-blank no-read-back hardening variant;
  `token_variant` vocabulary and the MBQ-05 acquisition-path direction;
  scope-snapshot placement; the `core_test_connection` job-type value;
  the `SHOP_INACTIVE`/402/423/403-fraudulent error-class mapping; the
  job-log system-append write path vs. ACL widening; the per-run
  `payload_hash` nonce for repeat target-less jobs.
- See [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  (AR-024) for the full acceptance record and
  [`./master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
  (MBQ-04/05/06/44/51/52/08) for the applied register impact.

## Status

- **Docs-only.**
- **No implementation.** No code of any kind is created by this document.
- **Does not open any gate.** The only open implementation gate remains the
  limited core-only zero-UI gate (AR-021), which explicitly forbids
  credentials, external API calls, setup wizard, and test connection.
- **Does not create fields/models/views/code.** Every model/field/access
  name below is a *proposal* for a future, separately authorized task.
- **Builds on the AR-022 / MBQ-04 Option B posture** (accepted by ChatGPT
  2026-07-06, posture level only) **and the AR-023 UI/UX acceptance**
  (Premium Simplicity Standard and the UI/UX design package, accepted
  2026-07-06 at design-specification level).
- Per `CLAUDE.md` §8, statements below are labelled **Fact** (official
  source cited), **Inference**, **Recommendation**, or **Open question**
  where ambiguity is possible. Nothing here is a Decision.

## Scope

**Covers (planning level only):**

- Credential storage planning within the accepted MBQ-04 Option B posture.
- Connection lifecycle (`setup_incomplete` / `connected` /
  `reconnect_needed` / `disconnected`).
- Disconnect/reconnect behavior.
- Token replacement/rotation behavior.
- Test connection design.
- Readiness-check design.
- API client boundary (the future transport layer's contract).
- Redaction / no-logging contract.
- The proposed future implementation tasks (Task 002 onward — specified in
  the companion task plan and the two proposed task specs).

**Out of scope:**

- Product/customer/order/inventory/fulfillment sync logic of any kind.
- Webhooks (receiver, HMAC handling, topic registration).
- Setup wizard code or any UI implementation (the UI gate remains closed).
- Domain modules.
- External secret manager implementation (MBQ-04 Options D/E remain
  deferred, not rejected, per AR-022 — see §Credential storage options).
- The public App Store OAuth flow (deferred by DEC-004/RA-003; noted below
  only where an official Shopify change affects future planning).

## Accepted constraints inherited

This package does not re-litigate any of the following; it designs inside
them:

1. **MBQ-04 / AR-022 (accepted 2026-07-06, posture level):** Option B — a
   dedicated Odoo-managed credential field (or tightly coupled field set),
   plain storage using standard Odoo field/access controls, restricted with
   a connector admin-equivalent `groups=`, view-level password masking
   wherever exposed, and a **mandatory no-logging/redaction rule**. No
   field-level encryption claim may be made anywhere; `sudo()` bypasses
   field-level `groups` (confirmed in 19.0 source); the Odoo Cloud AES-256
   claim is infrastructure-level with unconfirmed hosting scope and must
   not be used as a guarantee. Options D/E deferred, not rejected.
2. **DEC-004 (accepted):** non-public custom-app distribution; GraphQL
   Admin API primary; offline (unattended/service-to-service) access
   model; token "stored masked behind Odoo access rights and field-level
   `groups` on the credential field(s)", never logged; least-privilege
   scope selection surfaced in the wizard; reconnect-on-failure is a named,
   first-class flow; "No AR-002 credential-handling design may rely on
   `sudo()` to cross store/record-rule boundaries."
3. **UI/UX package / AR-023 (accepted 2026-07-06, design level):** Premium
   Simplicity Standard; credential entry is one masked field, **never read
   back on any surface, for any role** (including Admin); copy may say
   "stored with restricted access and never shown again" and **must not
   say "encrypted"**; token status shown as "present / last verified —
   never the value"; test connection = named pass/fail + reason, never a
   silent spinner, never a raw HTTP code as primary copy; readiness =
   essential ("must pass") vs warning ("good to fix") split per DEC-018
   MBQ-06.
4. **Core model planning / AR-019 (accepted):** the six core models and
   their exact fields; the four groups
   `group_shopify_connector_auditor/_operator/_reviewer/_admin`; the
   job/log split; `idempotency_key` vs `operation_scope_key`; the 16-class
   error registry and 10-state job vocabulary as implemented.
5. **Limited core gate / AR-021 (accepted):** exactly Task 001 authorized;
   credentials, API client, test connection, setup wizard, webhooks,
   controllers, cron, UI all explicitly forbidden until each future gate
   is separately opened by ChatGPT.
6. **Task 001 scaffold (merged; QA-closed by Task 001A):**
   `addons/shopify_connector_core` exists with the six models, four
   groups, and 20 ACL rows. The store model already carries
   `api_version`, `api_health_state/api_health_reason`,
   `last_test_connection_result/at/reason`, and
   `last_readiness_result/at` — this package designs *against* those
   fields, it does not re-propose them.
7. **PR #90 and PR #91 (both merged 2026-07-06):** the MBQ-04 acceptance
   patch and the accepted UI/UX design package are the immediate basis for
   this sprint; the task map's Group 4 (credentials) explicitly requires
   "the dedicated MBQ-04 implementation-planning task" — this document —
   "written and accepted first."
8. **DEC-009:** the fixed 16 error classes (no 17th), the retry taxonomy
   (auto-retry only safe/transient classes; ambiguous outcomes take a
   verification read or `blocked_manual_review`), and the structurally
   read-only `setup_readiness_check` / `export_preview_dry_run` job
   sources.
9. **Rejected approaches checked** (`../05-qa/rejected-approaches-log.md`,
   RA-001–RA-023): nothing below reintroduces a rejected approach. Most
   relevant here: RA-002 (no REST-heavy strategy), RA-003 (no public
   OAuth/App Store flow in Phase 1), RA-013 (no per-domain duplication of
   the transport/job substrate — the API client lives once in `core`),
   RA-014/RA-015 (no retry-everything, no never-retry), RA-016 (no raw
   technical detail as primary error copy). No rejected approach's
   revisit condition is invoked by this document.

## Official source findings

All findings below were verified live against official sources on
**2026-07-06** (access date for every citation in this section unless
stated otherwise). Shopify facts: `shopify.dev` only. Odoo facts:
`odoo.com/documentation/19.0` and the `odoo/odoo` GitHub branch `19.0`
only. Facts already captured in
[`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)
(access dates 2026-06-30 / 2026-07-01) and
[`../01-research/odoo-credential-storage-official-notes.md`](../01-research/odoo-credential-storage-official-notes.md)
(access date 2026-07-05) are reused with their original citations and not
re-listed except where re-verified or changed.

### Confirmed facts — Shopify

1. **Fact — GraphQL Admin API endpoint and auth header.** GraphQL queries
   are executed by sending POST requests to
   `https://{store_name}.myshopify.com/admin/api/{version}/graphql.json`,
   and "All GraphQL Admin API requests require a valid Shopify access
   token … include your token as a `X-Shopify-Access-Token` header on all
   GraphQL requests" (direct quotes; the page's example shows version
   `2026-07`). Accessible.
   (https://shopify.dev/docs/api/admin-graphql)
2. **Fact — API versioning.** Versions are date-named `YYYY-MM`; a new
   version releases every 3 months at the start of the quarter (5pm UTC);
   each stable version is supported ≥12 months with ≥9 months overlap;
   Shopify officially recommends always pinning a version and updating
   quarterly. Requests to a retired/inaccessible version "fall forward" to
   the oldest accessible stable version, and every response carries an
   `X-Shopify-API-Version` header showing the version actually used — a
   mismatch versus the requested version is the documented signal that
   fall-forward occurred. Accessible.
   (https://shopify.dev/docs/api/usage/versioning)
3. **Fact — latest stable version on 2026-07-06.** The reference's version
   picker shows `2026-07` as "latest" (released July 1, 2026; accessible
   until July 16, 2027 15:00 UTC), with `2026-10` as release candidate.
   Accessible. (https://shopify.dev/docs/api/admin-graphql)
4. **Fact — custom-app token acquisition (admin-created).** For a custom
   app created in the Shopify admin, the Admin API access token is
   generated by creating and installing the app in the Shopify admin.
   **"You can no longer create new custom apps in the Shopify admin"**
   (direct quote) — new custom apps are created via the Dev Dashboard —
   and custom apps already created in the admin **keep working**. API
   credentials for admin-created custom apps **cannot be rotated**: "To
   create new access tokens for a custom app that was created in the
   Shopify admin, you need to uninstall and reinstall your app," and
   requests/webhooks are disrupted until the app is updated with the new
   credentials. Accessible.
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin)
5. **Fact — Dev Dashboard app token acquisition.** Apps created in the Dev
   Dashboard do not show an access token in the Shopify admin; the app
   exchanges client ID + client secret programmatically via the **client
   credentials grant** at
   `POST https://{shop}.myshopify.com/admin/oauth/access_token`
   (`grant_type=client_credentials`), and those access tokens are **valid
   for 24 hours** (`expires_in` always `86399`). The grant is restricted
   to apps developed by your own organization and installed in stores you
   own. Official storage guidance for these credentials: keep the client
   secret out of frontend code and repositories; store credentials in a
   `.env` file excluded from version control; store the access token
   securely. Accessible.
   (https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens;
   https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant)
6. **Fact — offline tokens; expiring-token model does not cover custom
   apps.** Legacy offline access tokens have no expiration ("Tokens remain
   valid indefinitely until app is uninstalled or secret revocation");
   access tokens begin with the prefix `shpat_` and refresh tokens with
   `shprt_`. The December 2025 *expiring* offline-token requirements apply
   to **public apps only** (mandatory for public apps created on/after
   April 1, 2026; earlier public apps must migrate by January 1, 2027);
   **custom apps and merchant-created apps are explicitly exempt**.
   Revoking a client secret "will also remove the access tokens associated
   with it." Accessible.
   (https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/offline-access-tokens;
   https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets/rotate-revoke-client-credentials)
7. **Fact — scope verification query.** The official access-scopes page
   says granted scopes can be checked via a GraphQL app-installation
   query; API version 2026-07 provides both `appInstallation` (optional
   `id` argument; defaults to the currently authenticated app) and
   `currentAppInstallation` on `QueryRoot`, with the official example:
   `query AccessScopeList { currentAppInstallation { accessScopes { handle } } }`.
   `AppInstallation.accessScopes` is `[AccessScope!]!` ("the scopes granted
   by the merchant during installation"); `AccessScope` has `handle:
   String!` and `description: String!`; scope handles follow
   `{read_|write_}{resource}` (e.g. `read_products`). Accessible.
   (https://shopify.dev/docs/api/usage/access-scopes;
   https://shopify.dev/docs/api/admin-graphql/latest/queries/currentAppInstallation;
   https://shopify.dev/docs/api/admin-graphql/latest/queries/appInstallation;
   https://shopify.dev/docs/api/admin-graphql/latest/objects/AppInstallation;
   https://shopify.dev/docs/api/admin-graphql/latest/objects/AccessScope)
8. **Fact — shop identity query.** The GraphQL Admin API `shop` query
   returns `Shop!`, "the Shop resource corresponding to the access token
   used in the request." Confirmed 2026-07 `Shop` fields include
   `id: ID!`, `name: String!`, `myshopifyDomain: String!`,
   `primaryDomain: Domain!`, `currencyCode: CurrencyCode!`,
   `plan: ShopPlan!`. Neither the `shop` query page nor the `Shop` object
   page displayed an access-scope requirements section (see Not confirmed
   #6). Accessible.
   (https://shopify.dev/docs/api/admin-graphql/latest/queries/shop;
   https://shopify.dev/docs/api/admin-graphql/latest/objects/Shop)
9. **Fact — GraphQL error behavior.** "The GraphQL API can return a 200
   OK response code in cases that would typically produce 4xx or 5xx
   errors in REST" (direct quote from the GraphQL Admin API reference).
   Errors appear in an `errors` array whose entries carry
   `message` plus an `extensions` object including a `code`. Documented
   `extensions.code` values: `THROTTLED` ("similar to 429"),
   `ACCESS_DENIED` ("similar to 401"), `SHOP_INACTIVE`,
   `INTERNAL_SERVER_ERROR` (sample body includes `extensions.requestId`),
   plus `MAX_COST_EXCEEDED` in the sample body for a query exceeding the
   single-query cost cap (extensions carry `code`, `cost`, `maxCost`). The
   GraphQL reference's HTTP status section lists 200, 400, 402 (frozen
   shop), 403 ("the store has been marked as fraudulent"), 404, 423
   (locked shop), and 5xx — it lists **neither 401 nor 429** as direct
   GraphQL HTTP responses. Mutations report validation problems via a
   `userErrors` field the client must select. Accessible.
   (https://shopify.dev/docs/api/admin-graphql;
   https://shopify.dev/docs/api/usage/response-codes)
10. **Fact — rate limiting / cost.** The GraphQL Admin API uses calculated
    query cost (leaky bucket): restore rates 100 pts/s (Standard), 200
    (Advanced), 1000 (Plus), 2000 (Enterprise/Commerce Components); a
    single query may not exceed 1,000 points; the bucket must fit the
    *requested* cost before execution and is refunded requested−actual
    afterwards. Every response reports `extensions.cost` with
    `requestedQueryCost`, `actualQueryCost`, and `throttleStatus`
    (`maximumAvailable`, `currentlyAvailable`, `restoreRate` — verbatim
    field names). Default field costs: Scalar/Enum = 0, Object = 1,
    Connection sized by its `first`/`last` arguments, Mutation = 10.
    Per-plan bucket size is **not** published; the actual bucket size is
    observable at runtime via the documented
    `throttleStatus.maximumAvailable` field (**Recommendation:** the
    client reads it at runtime and never hard-codes bucket sizes). The generic
    "Avoiding rate limit errors" guidance recommends waiting before
    retrying, with a recommended backoff time of one second (generic
    Shopify guidance, not labelled Admin-API-specific). Accessible.
    (https://shopify.dev/docs/api/usage/limits)
11. **Fact — REST status.** The REST Admin API is legacy as of October 1,
    2024; new public apps must be GraphQL-only since April 1, 2025
    (re-confirmed; matches the repo's existing notes). Accessible.
    (https://shopify.dev/docs/api/admin-rest)

### Confirmed facts — Odoo 19

12. **Fact — field `groups` semantics.** The ORM reference documents the
    Field parameter `groups` as a "comma-separated list of group xml ids"
    restricting field access "to the users of the given groups only"; the
    security reference documents three enforcement effects: restricted
    fields are removed from requested views, removed from `fields_get()`,
    and explicit read/write attempts raise an access error. Accessible.
    (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html;
    https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
13. **Official source-code fact — enforcement and `sudo()` bypass.** In
    `odoo/orm/models.py` (branch `19.0`), `_has_field_access()` returns
    True immediately when the environment is superuser — so
    `sudo()`/superuser bypasses field-level `groups` (including the
    source-only `NO_ACCESS = '.'` sentinel); `write()`/`create()` check
    field access per field; `fields_get()` omits inaccessible fields;
    view postprocessing strips restricted fields from the arch
    (`ir_ui_view.py`). `has_groups()` over a comma-separated list is OR
    semantics with `!`-prefixed exclusion
    (`odoo/addons/base/models/res_users.py`). Accessible.
    (https://github.com/odoo/odoo/blob/19.0/odoo/orm/models.py;
    https://github.com/odoo/odoo/blob/19.0/odoo/orm/fields.py;
    https://github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_ui_view.py;
    https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/res_users.py)
14. **Fact — `password` view attribute is display-only.** The 19.0 view
    architecture reference documents `password` as a boolean `<field>`
    attribute (Char fields) whose effect is that the data "should not be
    displayed"; the `Char` field class itself has no `password` parameter
    (`odoo/orm/fields_textual.py` documents only `size`, `trim`,
    `translate`). No claim of encryption exists in either source; no
    occurrence of "encrypt" exists in `fields.py`, `fields_textual.py`,
    or `models.py` on branch 19.0. This re-confirms the accepted AR-022
    evidence; it is **not** an encryption mechanism. Accessible.
    (https://www.odoo.com/documentation/19.0/developer/reference/user_interface/view_architectures.html;
    https://github.com/odoo/odoo/blob/19.0/odoo/orm/fields_textual.py)
15. **Fact — access rights / record rules / sudo warnings.**
    `ir.model.access` is model-level, default-deny, additive across
    groups; `ir.rule` is record-level, default-allow, global rules
    intersect / group rules unify; `sudo()` "does not change the current
    user, and simply bypasses access rights checks," with official
    warnings that it can cross record-rule boundaries and must be used
    with extreme care; raw SQL bypasses Odoo security rules entirely; the
    19.0 developer security page contains **no guidance on storing
    secrets/credentials in fields** (its pitfalls sections cover unsafe
    public methods, ORM bypass, SQL injection, etc.). Accessible.
    (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html;
    https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html;
    https://www.odoo.com/documentation/19.0/developer/tutorials/restrict_data_access.html)

### Not confirmed (open — must be verified before or during the affected task)

1. **Open question — THROTTLED response body shape.** No official sample
   JSON body with `extensions.code = "THROTTLED"` exists on the GraphQL
   reference (checked in HTML and `.txt` mirror forms) or the limits page.
   Whether a throttled response's `errors[].extensions` carries
   cost/throttle data, and the exact message text, must be verified
   empirically on a development store when implementation is authorized.
2. **Open question — invalid/expired token HTTP status.** No official page
   states whether an invalid token on the GraphQL Admin API yields HTTP
   401 or HTTP 200 + `ACCESS_DENIED`; the GraphQL reference lists neither
   401 nor 429 as direct HTTP responses and describes `ACCESS_DENIED` only
   as "similar to 401." The client boundary must handle **both** shapes.
3. **Open question — GraphQL throttling as HTTP 429.** The limits page's
   429 sentence is scoped to "Resource-based rate limits"; treating
   GraphQL Admin throttling as always HTTP 200 + `THROTTLED` is an
   **Inference**, not a verbatim official statement. The client must
   tolerate both.
4. **Open question — missing-scope error shape.** The only official
   description of the missing-scope GraphQL error ("Access denied for
   <field-name>. Required access: <scope> access scope") is a June 2020
   changelog entry that names neither the `extensions.code` nor the HTTP
   status. Treat as historical; verify the current shape empirically.
   (https://shopify.dev/changelog/new-error-messages-for-graphql-operations-without-necessary-access-scopes)
5. **Open question — write-implies-read.** The access-scopes page does
   **not** state that `write_{resource}` implies `read_{resource}`. The
   connector's requested scope list must name explicit `read_` handles (or
   verify empirically per resource); no design below assumes implication.
6. **Open question — scope requirements of `shop` /
   `currentAppInstallation`.** Neither reference page surfaced an
   access-requirements section; absence of a stated requirement is not
   proof of none. The test-connection design below treats "works with any
   authenticated token" as an expectation to verify empirically, not a
   fact.
7. **Open question — one-time token reveal.** The historical
   "Reveal token once" / last-4-characters behavior for admin-created
   custom apps appears on **no live official page** (checked both the
   Help Center custom-apps page and the token-generation page). It must
   be treated as unverified-historical and must not be asserted in any
   copy or design.
8. **Open question — Odoo RPC read-back of `password`-masked fields.**
   Whether a Char field rendered with `password="1"` still returns its
   plaintext value in `web_read`/RPC responses is not stated in the 19.0
   docs (the accepted AR-022 research confirmed the masking is
   client-side display logic; the conservative design assumption below is
   that **any readable stored field is RPC-readable by a user with field
   access**).
9. **Open question — `NO_ACCESS = '.'` sentinel stability.** The
   field-`groups` "deny all except superuser" sentinel exists in 19.0
   source but is undocumented in the rendered reference; its stability as
   a public contract is unknown. The design below does **not** rely on it.
10. **Open question — Odoo Online/Odoo.sh/on-premise encryption
    coverage.** Unchanged from AR-022: not separately sourced; no claim is
    made here.

### Implications

- **The connector must authenticate with `X-Shopify-Access-Token` against
  the versioned GraphQL endpoint** — this is now fully confirmed and
  stable across three independent official pages. (Fact)
- **A single tiny GraphQL query can prove identity + auth + scopes in one
  read-only round trip** (`shop` + `currentAppInstallation.accessScopes`)
  — the test-connection design below uses it. (Fact-based design;
  per-query scope requirements remain Open question #6.)
- **MBQ-05's landscape has materially changed:** new custom apps can no
  longer be created in the Shopify admin. Existing admin-created custom
  apps (non-expiring `shpat_` token; the historical one-time-reveal
  behavior is unverified — Open question #7) keep
  working, but a merchant starting fresh today creates a Dev Dashboard
  app whose tokens are obtained programmatically via the client
  credentials grant and **expire every 24 hours**. This does not break
  the accepted DEC-004 offline/unattended model (the client credentials
  grant *is* server-to-server), but it means the credential *field set*
  must be able to grow from "one long-lived token" to "client ID + client
  secret + short-lived token cache" without a disruptive migration —
  which §Recommended decision below designs for. The choice of supported
  acquisition path(s) is MBQ-05's decision, for ChatGPT, not made here.
  (Fact + Inference; routed to MBQ-05 in §Proposed register impact.)
- **Shopify-side rotation for admin-created custom apps is
  uninstall/reinstall** — the connector's "replace token" flow must
  therefore treat replacement as an ordinary, expected operation and warn
  that the old token stops working at Shopify's side, not the
  connector's. (Fact + design implication.)
- **Error normalization must be signal-driven, not status-driven:** the
  same failure class can arrive as an HTTP status (transport layer) or as
  a 200-OK GraphQL `errors[]` entry (`extensions.code`); the client
  boundary must normalize both paths into the fixed 16-class registry.
  (Fact + Inference.)
- **No Odoo mechanism has appeared that would change the accepted MBQ-04
  posture** — the 2026-07-06 re-verification found the same
  access-control-only reality AR-022 recorded, now additionally confirmed
  at the 19.0 source level for the read/write/view enforcement paths.
  (Fact)

## Credential storage options

The accepted MBQ-04 Option B posture fixes the *mechanism class* (dedicated
Odoo-managed field(s), plain storage + `groups=` + masking + redaction) but
explicitly left open *where the field lives*. The options below are
sub-variants **within** the accepted posture (A–C), plus the two mechanisms
already evaluated by AR-022 (D–E), re-listed for completeness because the
task requires them. Labels: the evaluations are **Inference /
Recommendation** built on the cited facts.

### Option A — Token field directly on `shopify.connector.store`

- **Pros:** No new model or ACL surface; matches the Odoo core precedent
  of secrets living directly on the business record (`ir.mail_server.
  smtp_pass`, `payment.provider` keys — AR-022 evidence); status fields
  and secret live together; simplest possible Task 002.
- **Cons:** `store` is the busiest, most-read record in the connector —
  every dashboard/health/job surface reads it, and all four roles have
  model-level read. The secret's invisibility then rests **only** on
  field-level `groups` and on every future view/report/export authoring
  discipline (the accepted AR-022 research explicitly flags
  view-authoring discipline as "a real, ongoing risk, not a one-time
  setup task"). Credential writes and routine status writes mix in one
  model, blurring the audit trail. Extending later to a second credential
  shape (client ID/secret + cached short-lived token — see MBQ-05
  implication above) would keep adding sensitive fields to the shared
  store record.
- **Security implications:** identical at-rest exposure to every option
  (plain column, `sudo()` bypass, backup exposure — accepted facts);
  larger *accidental-exposure* surface because the host model is
  routinely read/rendered everywhere.
- **UX implications:** neutral — the UI reads status mirrors either way.
- **Access-control implications:** field `groups=` only; the model itself
  must stay readable to all roles, so no model-level defense exists.
- **Testability:** access tests must prove field stripping on a model
  every role can read — doable but every future store-view change
  re-opens the risk.
- **Future extensibility:** weakest — schema growth lands on the shared
  store record.
- **Verdict: rejected for this proposal** (not a permanent architecture
  rejection — a revisit would be routine if ChatGPT prefers maximal
  simplicity; recorded here as the runner-up).

### Option B — Token field on `shopify.connector.store.settings`

- **Pros:** Reuses an existing one-row-per-store model; no new model.
- **Cons:** `store.settings` is the **domain-extension seam** — domain
  modules `_inherit` it to add their own flag fields (AR-019 §5), and
  operators/reviewers/auditors all have model-level read because settings
  are legitimately visible configuration. Putting the secret on the model
  that every future domain module extends and every role reads is the
  worst of both worlds semantically (a secret is not a feature flag) and
  practically (maximum accidental-exposure surface growth over time).
- **Security / access-control / testability / extensibility:** as Option
  A but worse, because the model is designed to be extended by future
  modules outside this package's control.
- **Verdict: rejected for this proposal.**

### Option C — Separate credential model linked to store

A new, minimal, one-row-per-store model (proposed name
`shopify.connector.store.credential`) holding **only** the secret value
and secret-lifecycle metadata, with **no ACL row for any group except the
connector Admin group**, plus field-level `groups=` on the secret field as
a second, independent layer. Non-secret status mirrors (present /
last-verified / last-replaced / failure summary) live on `store`, written
by the same internal service that writes the credential.

- **Pros:**
  - **Two independent access layers** (model-level default-deny ACL for
    non-admin roles + field-level `groups=` on the value) instead of one.
    A future view/export/report of `store` or `store.settings` *cannot*
    leak the token because the token is not on those models at all —
    the accidental-exposure risk AR-022 flagged is structurally reduced,
    not just disciplined away.
  - **Clean audit boundary:** every write to the credential model *is* a
    credential event (entry/replacement/clear), giving the who/when audit
    trail the blueprint §B.2 requires without filtering it out of general
    store edits.
  - **Extensible without migration pain:** if ChatGPT's MBQ-05 decision
    later requires the Dev Dashboard client-credentials variant (client
    ID + client secret + 24-hour cached token), the fields land on the
    dedicated credential model, not on `store`.
  - **Testable in isolation:** one small model; access tests are "every
    non-admin role gets `AccessError` on any operation," which is crisp
    and provable.
  - Matches the accepted blueprint §B.2 concept list (masked token
    storage, token variant marker, scopes snapshot, last-validated,
    status) almost one-to-one.
- **Cons:** One more model than Option A (AR-019 was deliberately
  conservative about model count); needs one new ACL row and a service
  accessor; the status mirrors on `store` must be kept consistent by the
  writing service (single-writer rule below).
- **Security implications:** same at-rest reality as A/B (plain column;
  `sudo()` bypass; backup exposure — no encryption claim is or may be
  made); strictly better accidental-exposure and least-privilege posture.
- **UX implications:** none negative — the UI never renders the value
  anywhere in any option; status mirrors on `store` serve every accepted
  surface (connection band, wizard, dashboard).
- **Access-control implications:** model-level deny for
  Operator/Reviewer/Auditor (no ACL row); Admin-only CRU (no unlink,
  matching the connector-wide no-unlink rule); field `groups=` on the
  value restricted to the Admin group.
- **Testability / future extensibility:** strongest of A–C, as above.
- **Note on precedent:** AR-019's revision *removed* a
  `shopify.connector.store.credential` model from slice 1 — that was an
  explicit **descope** pending MBQ-04 evidence (AR-019 §11: "a future
  MBQ-04 decision may add a credential model later"), not a rejection;
  it does not appear in `rejected-approaches-log.md`. The revisit
  condition AR-019 named — MBQ-04 evidence reviewed and a mechanism
  direction accepted by ChatGPT — has been met by AR-022.
- **Verdict: recommended** (see next section).

### Option D — `ir.config_parameter`

- **Pros:** None found that a dedicated field lacks (AR-022's own
  conclusion, re-confirmed: no superiority on any axis checked).
- **Cons:** Conflates the credential with unrelated system
  configuration; no natural home for lifecycle metadata (a parallel
  model would be needed anyway); Odoo's own core stores
  `database.secret` there with no extra protection, so it sets no better
  precedent.
- **Security implications:** identical plain-`Text` storage and `sudo()`
  bypass as any field; **not** secure secret storage and must not be
  described as such (accepted AR-022 evidence; nothing found on
  2026-07-06 changes it).
- **UX implications:** none positive — status/mirror fields would still
  have to live on a model.
- **Access-control implications:** strictly **coarser** — one shared
  `group_system`-only ACL for the entire system-parameters table, no
  per-key granularity, and outside the connector's own group family.
- **Testability:** poor — access tests would assert behavior of a shared
  base-module table the connector does not own.
- **Future extensibility:** poor — key-value strings cannot grow into
  the MBQ-05 client-credentials shape cleanly.
- **Verdict: rejected for this proposal, consistent with the accepted
  AR-022 evaluation** ("do not adopt as the primary mechanism").

### Option E — External secret manager / hybrid

- **Pros:** Would remove the token from the Odoo database/backup
  exposure surface (the strongest posture in principle); aligns with the
  OWASP guidance Odoo's own External API doc points to.
- **Cons:** Rests on the official-evidence gap AR-022 recorded (no
  confirmed, supported Odoo mechanism for a module to read a
  deployment-level secret at runtime); would require revisiting
  DEC-004's storage-location wording; adds a second moving part
  (Odoo metadata + external secret) beyond Phase 1's scope.
- **Security implications:** unverifiable until the evidence pass
  happens; no claim can honestly be made either way today.
- **UX implications:** setup could no longer be completed inside Odoo
  alone (deployment-level configuration step), which cuts against the
  accepted calm, self-contained wizard.
- **Access-control implications / testability:** undefined pending the
  evidence pass — not designable now without inventing Odoo behavior.
- **Future extensibility:** the Option C model shape deliberately keeps
  this path open — the secret field could later hold a reference/handle
  instead of the value without changing the model boundary.
- **Verdict: remains deferred, unchanged** — AR-022's acceptance
  explicitly deferred (did not reject) Options D/E as a possible future
  stronger-posture path, routed as its own follow-up architecture-review
  row with its own evidence pass if ChatGPT wants it evaluated. Not
  designed further here.

## Recommended implementation-planning decision

**Recommendation (proposed only — not accepted until ChatGPT review):**
adopt **Option C** — a dedicated, Admin-only
`shopify.connector.store.credential` model holding the secret and its
lifecycle metadata, with non-secret status mirrors on
`shopify.connector.store`, an internal-only accessor for the future API
client, and a mandatory redaction utility enforced at every logging choke
point.

- **Proposed model name:** `shopify.connector.store.credential`
  (concrete, `shopify_connector_core`, one row per store, `store_id`
  unique — mirroring the `store.settings` linkage pattern).
- **Proposed field names/types:** see §Credential field proposal (full
  table).
- **Proposed helper/status fields:** on `store` —
  `credential_present`, `credential_last_verified_at`,
  `credential_last_replaced_at`, `credential_last_failure_reason`,
  `granted_scopes`, `granted_scopes_checked_at` (all six readonly,
  system-written; see table).
- **Proposed access groups:** model ACL row **only** for
  `shopify_connector_core.group_shopify_connector_admin`
  (read/write/create, **no unlink**); no ACL row for auditor, operator,
  or reviewer (Odoo default-deny — Fact #15); field-level
  `groups='shopify_connector_core.group_shopify_connector_admin'` on the
  secret value field as a second layer.
- **Proposed access behavior:** Admin enters/replaces/clears the value
  through dedicated service methods (future wizard/settings-band calls
  them); Operator/Reviewer/Auditor cannot read, write, create, or even
  `fields_get()` the model; the future API client reads the value only
  through an internal accessor (§API client boundary) that never returns
  it to callers, never logs it, and never includes it in exceptions.
- **Proposed no-read-back behavior:** no form/list/search view is ever
  defined for the credential model; the value field is written via
  service method and never rendered on any surface; ORM-level reads by
  Admin-group users remain technically possible (consistent with Odoo's
  own credential-field precedent and the blueprint §J scoping of
  no-read-back as "a connector surface guarantee, not an absolute
  database-level claim") — documented honestly as a residual, with an
  optional compute-blank hardening variant offered to ChatGPT (§No-read-back
  and masking rules).
- **Proposed masking behavior:** the only surface that ever contains the
  value is the future entry widget (wizard step 3 / settings-band
  replacement), which must use the view-arch `password` attribute
  (display masking only — Fact #14) and submit-and-clear semantics; every
  other surface shows status fields only.
- **Proposed redaction behavior:** a core redaction utility +
  `SENSITIVE_KEYS`/value-pattern rules applied at every log/exception
  choke point (§Redaction and no-logging contract).
- **Proposed rotation/replacement behavior:** "Replace token" is an
  ordinary Admin service action (overwrite value, stamp
  `credential_last_replaced_at`, reset verification state, require a new
  test connection before `connected` is re-asserted); Shopify-side
  regeneration for admin-created custom apps is uninstall/reinstall
  (Fact #4) and the future copy must say so plainly.
- **Proposed disconnect/reconnect behavior:** disconnect **clears the
  value** (never unlinks the row, never deletes history — MBQ-08),
  flips `credential_present = False`, sets `store.state = 'disconnected'`;
  reconnect = re-enter value → test connection → readiness re-run →
  `connected` (§Connection lifecycle).
- **Proposed audit metadata:** in Task 002 — standard
  `create_uid/write_uid/create_date/write_date` on the credential model
  plus the explicit `credential_last_replaced_at`/`..._verified_at`
  stamps (who/when, **never the value**). Job-log-anchored credential
  events (`shopify.connector.job.log` rows, event_type `manual_action`/
  `note`) begin only once the core job-log writing choke point exists
  (Task 003), because the merged ACL deliberately grants **no group
  create on `job.log`** (system-appended rows, AR-019 §10) — the write
  path for system-appended log rows is a named decision point (§Security
  and permissions), and `job.log.job_id` is required, so credential
  events also need parent-job mechanics fixed there.
- **Proposed rollback behavior:** Task 002's rollback is a revert of its
  PR before anything depends on it (same single-module DAG position as
  Task 001); at data level, uninstalling/reverting drops the credential
  model — tokens are re-enterable by the Admin, and no business data
  depends on them; a failed/partial credential entry leaves the store in
  `setup_incomplete`/`reconnect_needed` with the previous state
  recoverable by re-entry (no partial token writes: the service method
  writes atomically).

**Marked as: Proposed only. Not accepted until ChatGPT review.**

## Credential field proposal

**No field below is created by this document.** Every row is a proposal
for Task 002 (or later, where noted). "Displayed?" means rendered on any
connector surface; "Redacted?" means covered by the redaction contract's
key/value rules.

### New model: `shopify.connector.store.credential` (Task 002)

| Field | Type | Required | Readonly/editable | Groups/access | Displayed? | Redacted? | Audit | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `store_id` | Many2one → `shopify.connector.store`, `ondelete='restrict'`, unique, index | Yes | Readonly after create | Model ACL: Admin-only | No (model has no views) | n/a | Standard fields | One credential record per store; mirrors the `store.settings` linkage pattern (AR-019 §4.2) |
| `access_token` | Char | No (empty = cleared/absent) | Written only via service method | Field `groups=` Admin **and** model ACL Admin-only (two layers) | **Never** | **Yes — always** | Write events logged (never the value) | The Shopify Admin API access token (`shpat_…` — Fact #6). Not `required`: disconnect clears the value while preserving the row/history (MBQ-08) |
| `token_variant` | Selection, one core value `offline_custom_app` (extensible via `selection_add`) | No, default `offline_custom_app` | Editable by Admin (service-set) | Model ACL Admin-only | No | No (non-secret) | Standard | Blueprint §B.2's "token variant marker". One value now; the MBQ-05 decision may add e.g. a client-credentials variant later without migration |
| `credential_state` | Selection (`absent`/`present`/`invalid`) | Yes, default `absent` | Readonly (system/service-written) | Model ACL Admin-only | No (mirrored to `store`) | No | State changes logged | Lifecycle state of the secret itself: `invalid` is set when a test connection / API call proves the token rejected (drives `reconnect_needed`) |

*Explicitly not proposed:* a "last 4 characters" field (would invite
display and rests on unverified-historical Shopify behavior — Open
question #7); a client ID/secret pair (belongs to a future MBQ-05
decision, accommodated by `token_variant` + this model's boundary);
`active`/unlink semantics (history is never deleted).

### Status mirrors added to `shopify.connector.store` (Task 002)

All are non-secret, system-written by the credential/connection service
(single-writer rule: only the Task 002 service methods and the future
Task 003 test-connection path write them), readable by all four roles
(the store model's existing ACL), readonly in any future UI.

| Field | Type | Required | Readonly | Displayed? | Redacted? | Audit | Rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `credential_present` | Boolean | No, default False | Yes (system-written) | Yes — the "token status: present" indicator (AR-023 store form band) | Non-secret | Changes logged | UI needs presence without any access to the credential model |
| `credential_last_verified_at` | Datetime | No | Yes | Yes — "last verified" | Non-secret | n/a | The accepted "present / last verified — never the value" status display |
| `credential_last_replaced_at` | Datetime | No | Yes | Yes (Admin surfaces) | Non-secret | n/a | Replacement audit surface without exposing the credential model |
| `credential_last_failure_reason` | Char | No | Yes | Yes — plain-language summary only | **Content rule: must be written through the redaction utility; plain-language, no token, no raw response** | n/a | Powers the reconnect/error copy ("Shopify didn't accept this credential…") honestly |
| `granted_scopes` | Text (serialized JSON array of scope handles, e.g. `["read_products"]`) | No | Yes | Yes — behind the technical-detail expand / scope-comparison UI (AR-023 error type 11) | Non-secret (scope handles are permission names, not secrets) | Refresh logged | Snapshot of `currentAppInstallation.accessScopes[].handle` captured at each successful test connection/readiness run (Fact #7); powers the granted-vs-required scope comparison and the scopes readiness check |
| `granted_scopes_checked_at` | Datetime | No | Yes | Yes (with the snapshot) | Non-secret | n/a | Honest freshness for the scope snapshot — the UI must never imply a live scope view |

*Existing store fields reused, not re-proposed:* `api_version` (the
MBQ-52-pinned version the client sends), `api_health_state/_reason`,
`last_test_connection_result/_at/_reason`, `last_readiness_result/_at`,
`state`.

*Open sub-question (flagged, not decided):* whether `granted_scopes` +
`granted_scopes_checked_at` belong on `store` (proposed here for UX
reachability, since scope handles are non-secret) or on the credential
model (stricter grouping, but then every readiness/scope surface needs a
mirror anyway). Proposed: `store`, for the reason given; ChatGPT may
overrule at review.

### Explicitly deferred fields (not in Task 002)

- Client-credentials-grant fields (`client_id`, `client_secret`, cached
  token + expiry) — blocked on the MBQ-05 decision; the model boundary
  above is designed to absorb them later.
- Any webhook-secret field — webhooks are out of scope for this
  foundation entirely.
- Any per-check readiness result model/fields beyond the existing
  `last_readiness_*` mirrors — see §Readiness-check contract.

## No-read-back and masking rules

- **Who can enter/replace the token:** connector Administrators only
  (`group_shopify_connector_admin`), via dedicated service methods —
  matching the accepted role model (AR-023: "Admin-only for
  settings/credentials/mappings") and DEC-004.
- **Who can see token status:** all four roles see
  `credential_present`/`credential_last_verified_at` on the store's
  connection surfaces (status is deliberately non-secret and
  trust-building).
- **Who can never see the token value:** **every role, on every connector
  surface — including Admin.** After save, no connector view, wizard,
  band, log, error, export, or report ever renders the value (AR-023
  binding honesty rule; blueprint §J).
- **Is the token ever read back in forms?** No. The credential model gets
  **no views at all** in Task 002 (core remains zero-UI); the future
  entry widget (wizard step 3 / settings-band replacement — UI-gated,
  Group 4) is **write-only**: masked input (`password` view attribute —
  display masking only, Fact #14), value submitted to the service method,
  input cleared, never re-populated from storage.
- **Honest residual, stated plainly (Fact-based):** field-level `groups=`
  is access control, not encryption; `sudo()`/superuser bypasses it
  (Fact #13); an Admin-group user with generic ORM/RPC access could read
  the stored field outside connector surfaces, and database/backup access
  reads it regardless. This is exactly the accepted Option B posture —
  the same residual every official Odoo credential field carries (AR-022)
  — and must never be papered over in copy or docs.
- **Optional hardening variant (offered, not required):** a
  compute-blank read pattern on `access_token` (compute returns empty;
  inverse stores the entered value), analogous to `res.users.password`'s
  officially-precedented compute-blank mechanism (AR-022 research), would
  close the *generic-RPC read-back* path for everyone including Admin
  while keeping the value internally retrievable via the accessor.
  Trade-offs: slightly more machinery in Task 002; the raw column is
  still `sudo()`/DB-readable (no encryption claim either way). **ChatGPT
  should accept or drop this variant at review; Task 002's spec carries
  it as an explicit decision point.**
- **How copy must describe security honestly** (accepted AR-023 wording
  constraints, restated as binding for every future task):
  - Allowed: "stored with restricted access and never shown again";
    descriptions of masking and access restriction.
  - **Exact forbidden copy phrases/patterns:** "encrypted", "encryption",
    "bank-level encryption", "encrypted at rest", any at-rest security
    claim, padlock iconography implying encryption, any claim that
    Odoo.sh/Odoo Online/on-premise hosting encrypts the value (hosting
    scope unconfirmed — AR-022), any reveal/preview toggle, any display
    of full or partial token value (including "last 4" — Open question
    #7).

## Redaction and no-logging contract

**Principle (inherited, mandatory):** the accepted MBQ-04 posture makes a
no-logging/redaction rule a *component* of the storage decision, not an
optional extra; Odoo's own payment module treats log redaction
(`SENSITIVE_KEYS`) as a separate duty from storage/access control (AR-022
evidence). The connector's rule:

**The token value must never appear in:** job logs (`message`,
`technical_detail`, `payload_snapshot`), exception messages/args (any
exception raised by the client, the credential service, or readiness/test
code), request/response technical detail (headers included —
`X-Shopify-Access-Token` is a header, so raw request-header dumps are
categorically forbidden), chatter (core models have no `mail.thread`
today; the rule pre-commits any future adoption), Python `logging` output
at any level (including DEBUG), test-connection failure output,
`credential_last_failure_reason`, cron/queue error records,
rollback/error-handling paths (e.g. a constraint-violation message must
not echo submitted values), and any future telemetry.

**Proposed redaction utility (Task 002; names proposed, not created):**

- Location: `shopify_connector_core/tools/redaction.py` — one module-level
  function `redact(value)` accepting str/dict/list and returning the same
  shape with sensitive content replaced by `***`; plus
  `SENSITIVE_KEYS` and `SENSITIVE_VALUE_PATTERNS` constants.
- **Sensitive key patterns (case-insensitive substring match on
  dict/header keys):** `access_token`, `token`, `secret`, `password`,
  `authorization`, `x-shopify-access-token`, `api_key`, `apikey`,
  `client_secret`, `refresh_token`, `hmac`.
- **Sensitive value patterns (regex on string content):**
  `shpat_[A-Za-z0-9]+` and `shprt_[A-Za-z0-9]+` (officially confirmed
  token prefixes — Fact #6), plus the currently-stored token value itself
  (exact-match scrub) whenever the redaction context can access it
  internally. *Open question:* other historical prefixes (`shpca_`,
  `shppa_`) surfaced only in non-official sources and are **not** encoded
  as facts; the pattern list is extensible and the exact-match scrub
  covers unknown formats.
- **Safe to show:** shop domain, API version, scope handles, HTTP status
  codes, GraphQL `extensions.code` values, `extensions.requestId`
  (Shopify support explicitly asks for it — Fact #9), cost/throttle
  numbers in *technical detail only* (never primary copy — AR-023),
  plain-language reasons, check names, timestamps.
- **Unsafe to show:** anything matching the key/value rules above; raw
  request headers; full raw request bodies of credential-bearing calls;
  stack traces as primary copy (RA-016 — allowed only inside
  `technical_detail` after redaction).
- **Enforcement points (belt and braces):** (1) at source — the API
  client and credential service pass every outbound log/exception payload
  through `redact()` before raising/writing; (2) at sink — the core
  job-log writing helper (the single choke point every job/log row goes
  through) defensively applies `redact()` to `message`,
  `technical_detail`, and `payload_snapshot`. Both layers are required;
  neither alone is sufficient.
- **Test cases required later (Task 002/003 test plans):** token never in
  any `job.log` field after a simulated failure; exception raised by the
  client with a token-bearing fake response contains no token; header
  dump redaction; `shpat_` regex hit; dict-key hit (`access_token`,
  `Authorization`); nested dict/list redaction; exact-value scrub of an
  arbitrary-format token; `credential_last_failure_reason` never contains
  the value; redaction is idempotent (`redact(redact(x)) == redact(x)`).

## Connection lifecycle

The store `state` field and its four values already exist (Task 001).
This section fixes the planning-level semantics and transitions; exact
state-machine field mechanics remain the MBQ-01/02 residual noted by the
accepted flows document.

| State | How entered | Sync/jobs allowed | UI shows (accepted design) | Actions allowed | Audit written | Recovery |
| --- | --- | --- | --- | --- | --- | --- |
| `setup_incomplete` | Default at store creation; wizard exit before Activate | **No business sync/write jobs** (enforced in the queue substrate at enqueue *and* execution time — blueprint §E.5); `setup_readiness_check` / `export_preview_dry_run` jobs allowed (structurally read-only — §E.6) | "Setup incomplete — N steps remain," listing them | Resume wizard (Admin); credential entry/replace (Admin); test connection (Admin) | Wizard step completions; test/readiness runs as jobs | Complete the wizard → Activate |
| `connected` | Wizard step 11 "Activate" with all essential readiness checks passing; or reconnect flow completing (credential → test pass → readiness re-run pass) | All (per enabled domains and their guards) | Health band: state + API health + token status | Normal operation; disconnect (Admin); re-run test/readiness (Admin) | Activation timestamped; who/when | n/a |
| `reconnect_needed` | System-set when auth fails mid-operation (error class `shopify_permission_scope_auth` on a previously connected store, e.g. `ACCESS_DENIED`/401 — token revoked/expired/secret rotated) | **No new business jobs enqueued or executed**; in-flight handling per Part A §I.4 (cancel with audit reason or hold blocked — never silently dropped; exact disposition = open item) | Error type 5: "Shopify no longer accepts this store's credentials" + Reconnect | Reconnect (Admin): replace/re-enter token → test connection → readiness re-run | Pause + reconnect + readiness re-run all logged (AR-023 type 5) | Reconnect flow → `connected` |
| `disconnected` | Explicit Admin disconnect with consequence-stating confirmation | None enqueued/executed; webhooks not processed for the store | Error type 9: "This store is disconnected" + retained-history reassurance | Reconnect (Admin); view history (all roles) | Disconnect who/when; job cancellations with reasons | Reconnect flow (explicit, audited, never automatic) → `connected` |

- **Disconnect clears the credential value** (`access_token` emptied,
  `credential_present = False`, `credential_state = 'absent'`) and
  **preserves everything else** — store record, credential row (emptied),
  settings, bindings, jobs, logs, audit, mapping/error history (MBQ-08,
  accepted).
- **Reconnect re-runs readiness before business sync resumes** (MBQ-08,
  accepted) — a reconnect that skips readiness is a defect by definition.
- **No paused/disabled state is added:** per-domain disable is a
  `store.settings` flag concern, not a fifth connection state; the
  accepted four-value vocabulary is not extended by this proposal.
- **Transition writer:** all state transitions are system/service-written
  (the field is `readonly=True` system-managed today); the future
  lifecycle service (Task 005 in the companion plan) is their single
  writer, each transition writing a `job.log`-anchored audit trail
  (readiness/test runs) plus who/when stamps.

## Test connection contract

- **Trigger:** explicit Admin action — wizard step 5, the store form
  connection band, and the reconnect flow (all accepted surfaces);
  re-runnable at will. Never automatic/scheduled in this foundation (a
  scheduled credential health probe is a possible later readiness
  extension — open item).
- **Required preconditions:** `credential_present` (the only
  runtime-checkable precondition — `shop_domain` and `api_version` are
  both `required=True` on the merged store model, so they are satisfied
  by construction on any persisted store; the service still guards them
  defensively).
- **Official API call (candidate, Fact-based):** one GraphQL POST to
  `https://{shop_domain}/admin/api/{api_version}/graphql.json` with header
  `X-Shopify-Access-Token` (Facts #1, #7, #8):

  ```graphql
  query ConnectorTestConnection {
    shop { id name myshopifyDomain }
    currentAppInstallation { accessScopes { handle } }
  }
  ```

  All selected fields are confirmed in the 2026-07 reference (`Shop.id`,
  `Shop.name`, `Shop.myshopifyDomain`;
  `currentAppInstallation.accessScopes.handle`). The query is read-only,
  costs a trivial number of points (scalar-heavy — Fact #10), and
  deliberately omits `email`/`plan` (not needed; potentially more
  sensitive). Whether these root fields require any scope is Open
  question #6 — the Task 003 spec requires empirical verification on a
  development store as an acceptance step.
- **What success proves:** DNS/TLS reachability of the shop domain; the
  domain resolves to a live Shopify shop; the token is accepted for this
  shop; the pinned API version is being served (compare the
  `X-Shopify-API-Version` response header to `store.api_version` — a
  mismatch means fall-forward occurred and must surface as a warning, not
  silent success — Fact #2); the store identity matches
  (`shop.myshopifyDomain` vs `store.shop_domain` — the accepted "store
  identity confirmed" readiness check); the granted scope handles are
  retrievable (snapshot written to `granted_scopes`).
- **What success does not prove:** that granted scopes are *sufficient*
  for the enabled domains (that is the separate scopes readiness check,
  comparing `granted_scopes` to the required list); webhook
  reachability; cron/queue health; write permissions actually working;
  sustained rate headroom; anything about business data.
- **Failure classes → existing 16-class registry (proposed mapping;
  no 17th class is introduced):**

  | Observed signal | Error class | Notes |
  | --- | --- | --- |
  | DNS/TLS/connect/timeout errors; HTTP 5xx; `INTERNAL_SERVER_ERROR` | `shopify_temporary_server_network` | Include `extensions.requestId` in technical detail when present (Fact #9) |
  | HTTP 401 (if it occurs) or `ACCESS_DENIED` | `shopify_permission_scope_auth` | Invalid/revoked token — drives error type 5 copy; on a connected store also flips `reconnect_needed`. Client must handle both shapes (Open questions #2) |
  | `THROTTLED` or HTTP 429 (if it occurs) | `shopify_throttling_rate_limit` | Rate-limit copy ("Shopify is asking us to slow down"); both shapes handled (Open question #3) |
  | HTTP 402 (frozen shop), 423 (locked shop), `SHOP_INACTIVE`, 403-fraudulent | `shopify_permission_scope_auth` | Proposed as the least-bad fit of the fixed 16 ("access to this shop is not currently permitted"), with the plain-language reason naming the shop-state cause distinctly. **Flagged for ChatGPT confirmation** — the alternative is `shopify_user_errors_validation`; no new class may be invented |
  | `shop.myshopifyDomain` ≠ `store.shop_domain` | `odoo_validation_configuration` | Merchant configuration error (wrong domain entered); wizard keeps the operator on the step with a named fix |
  | Missing scope detected at the comparison step | `shopify_permission_scope_auth` | Error type 11 ("A permission is missing: [scope]") with granted-vs-required comparison in the expand |
  | Malformed/unparseable response; `MAX_COST_EXCEEDED` on this tiny query; anything unclassifiable | `unknown_system_error` | Single safety-net path per DEC-009 |

- **Does test connection create a job?** Yes — `job_source =
  'setup_readiness_check'` (the accepted, structurally read-only source),
  so every run is visible, logged, and auditable like everything else.
  **Job type:** proposed new core-owned value `core_test_connection`,
  added to the base `job_type` selection list in
  `shopify_connector_core` itself (the `selection_add` seam remains the
  extension mechanism for *domain modules*, not for core-owned values) —
  flagged explicitly because AR-019 accepted exactly two core `job_type`
  values; adding a third is a vocabulary extension ChatGPT must accept
  with Task 003 (the fallback, reusing `core_readiness_check` with a
  distinguishing log, is workable but muddies the job list's honesty).
  **Repeat-run key collision (design point, flagged):** the merged job
  model computes the required, `(store_id, …)`-unique `idempotency_key`
  from `store_id|job_type|res_model|res_id|shopify_target_gid|
  payload_hash`; a target-less test-connection/readiness job leaves the
  last four components empty, so a **second run of the same job type on
  the same store would collide with the unique constraint** as merged.
  Proposed resolution (touches accepted AR-019 key semantics, so ChatGPT
  must confirm it with Task 003): target-less interactive check jobs
  populate `payload_hash` with a per-run nonce (e.g. a UUID), preserving
  the key's uniqueness contract for real operations while making
  re-runs first-class. This latent collision also affects the existing
  `core_readiness_check` job type and is carried in §Open items.
- **Does test connection write business data?** **No — never.** Read-only
  at Shopify (pure query, no mutation); Odoo-side it writes only: the
  job + job.log rows, the store status mirrors
  (`last_test_connection_result/_at/_reason`,
  `credential_last_verified_at`, `granted_scopes(_checked_at)`,
  `api_health_state/_reason` where applicable), and `credential_state`.
  No webhook setup, no domain writes, no product/customer/order/
  inventory/fulfillment logic.
- **What is logged:** one job per run; `job.log` rows for the attempt and
  result; `message` = plain-language outcome ("Connection verified with
  <shop name>" / named failure + fix); `technical_detail` = redacted
  response/status excerpt (never headers-with-token, never the token).
- **What is redacted:** everything per the redaction contract — the
  request's auth header is never logged at all; response excerpts pass
  through `redact()`.
- **What the UI should say (design-level, copy = MBQ-22):** named
  pass/fail with a reason; failure keeps the operator on the step with a
  named cause + fix; "never a silent spinner … never a raw HTTP code"
  (accepted AR-023 wording).
- **Retry behavior:** interactive, single-attempt — **no automatic retry
  loop** (the operator re-runs explicitly; the wizard keeps everything
  entered). A throttled result advises waiting briefly (the DEC-009
  auto-retry policy applies to queued business jobs, not to an
  interactive pre-flight check; this narrowing is deliberate and flagged
  for review).

## Readiness-check contract

Planning-level design for the accepted DEC-018 MBQ-06 split; thresholds
and copy remain that decision's residual (open).

- **Must-pass (essential) checks — the accepted set, with proposed
  owner/mechanics:**

  | Check | Mechanism (planning level) | Owner |
  | --- | --- | --- |
  | Credential validity / test connection | The test-connection contract above (its result is this check) | `core` |
  | Required scopes granted | Compare `granted_scopes` snapshot against the required-scope list computed from enabled domains (explicit `read_`/`write_` handles per domain — no write-implies-read assumption, Open question #5); the exact per-domain scope list is a domain-module contribution via seam, with `core` owning the comparison | `core` + domain seams |
  | API-version health | `X-Shopify-API-Version` response header equals `store.api_version` (no fall-forward — Fact #2); version still in its support window | `core` |
  | Store identity confirmed | `shop.myshopifyDomain` equals `store.shop_domain` (from the test-connection query) | `core` |
  | `web.base.url` reachability | Odoo-side configuration check (needed for future webhooks); mechanics = implementation detail of Task 004 | `core` |
  | Webhook HMAC secret (only if webhooks enabled) | Deferred entirely — webhooks out of scope for this foundation; the check slot exists in the accepted set but its implementation belongs to the future webhook task | future webhook task |
  | Cron/queue health | Odoo-side check that the connector's queue-drain mechanism is alive; mechanics = Task 004 detail (no cron is created by this foundation) | `core` |
  | ≥1 mapped Location (where inventory/fulfillment enabled) | Domain-contributed check via seam; not implementable before the inventory domain exists | domain seams |
  | Intentional domain enablement | Pure Odoo-side settings validation | `core` |

- **Warning-only checks:** everything else — warn, never block (accepted).
  Initial warning-tier candidates (proposal): scope *surplus* (granted
  scopes exceeding the required list — least-privilege nudge); API
  version approaching end-of-support window; `granted_scopes_checked_at`
  staleness.
- **Per-check owner:** as tabled — `core` owns the engine, the
  scope-comparison, and all connection-shaped checks; domain modules
  contribute domain checks through a registration seam (mirroring the
  accepted job-type seam pattern; no domain import in `core`).
- **Per-check fix link concept:** each check definition carries a
  fix-target reference (accepted navigation-map concept: "readiness check
  failure → the fixing surface"); at this foundation's level that is a
  named action slot resolved when the UI ships (XML IDs = MBQ-03).
- **Persisted result fields or job/log pattern:** proposed — **no new
  readiness-result model** (avoids over-fragmentation, RA-012 pattern).
  Each run is one `setup_readiness_check` job (`job_type =
  'core_readiness_check'`, which exists); per-check results are recorded
  as structured JSON in the run's `job.log.payload_snapshot`
  (`[{check, tier, result, reason}]`, redacted), with the summary
  mirrored to the existing `store.last_readiness_result/_at`. A dedicated
  per-check result model is named as a deferred option if the dashboard
  later needs per-check querying at scale. (Log rows are written through
  the same system-append choke point as everything else — see the
  job-log write-path decision point in §Security and permissions.)
- **Dashboard impact:** feeds the existing accepted connection-health
  card and readiness surfaces; warnings are "carried to the dashboard"
  (accepted); no new card is proposed (the nine-card set is fixed).
- **UI wording constraints (accepted, restated):** status word + check
  name + one-line result + inline fix hint on failure; two tiers visually
  and behaviourally distinct; named reasons, never raw HTTP codes; a
  failed essential check must block `connected`/Activate.
- **Open implementation details:** exact per-check thresholds and copy
  (MBQ-06 residual / MBQ-22); cron/queue-health check mechanics before
  any cron exists; the required-scope list per domain (each domain's own
  naming pass); scheduled re-runs (nothing scheduled in this foundation).

## API client boundary

The future transport layer (Task 003 shell; **no code now**). Blueprint
§A.2 already fixes its home; this section fixes its contract.

- **Where it lives:** `shopify_connector_core` — "the single place any
  connector module talks to Shopify" (accepted; RA-013 forbids
  per-domain duplicates). Proposed shape: an `AbstractModel` service,
  `shopify.connector.api.client`
  (`models/shopify_connector_api_client.py`), stateless, no table.
- **One client per store?** No persistent client objects: service methods
  take the store record as their first argument
  (`execute(store, query, variables=None)`); all per-store state (domain,
  version, health mirrors) lives on `store` where it already is.
- **How the token is retrieved internally:** via a private accessor on
  the credential model (proposed `_get_access_token()`), called only
  inside the client; it may use a **narrow, documented `sudo()`** scoped
  to reading the single credential row of the store already being
  operated on — consistent with DEC-004's constraint (this elevation
  never *crosses* store/record-rule boundaries; it reads the one store's
  own secret for a caller already authorized to act on that store) and
  with the accepted MBQ-04 analysis (background jobs run elevated;
  operator-triggered syncs run as users who must not read the credential
  model directly). Every use is code-review-flagged; the accessor never
  returns the token to anything outside the client, never logs it, and
  never places it in an exception.
- **How the API version is pinned/read:** the client sends
  `store.api_version` in the URL (MBQ-52 accepted policy: one pinned
  stable version per connector release, stored per store); it compares
  the `X-Shopify-API-Version` response header and surfaces fall-forward
  as a health/readiness warning (Fact #2). The module-pinned default for
  the first release is proposed as **`2026-07`** (latest stable on
  2026-07-06 — Fact #3), an adjustable planning default in the MBQ-16
  pattern, finalized in Task 003's spec at coding time.
- **How requests are made:** HTTPS POST, JSON body
  (`{"query": …, "variables": …}`), headers `Content-Type:
  application/json` + `X-Shopify-Access-Token` (Fact #1); bounded
  timeouts (constants = adjustable planning defaults in Task 003);
  GraphQL-only (DEC-004/RA-002 — no REST path).
- **How errors are normalized:** one normalized exception family
  (proposed `ShopifyClientError` with subclasses per transport/GraphQL
  signal), each carrying: the mapped DEC-009 `error_class` (from the
  test-connection mapping table above, which is the client-wide mapping),
  a plain-language safe message, and a **redacted** technical-detail
  payload (status, `extensions.code`, `requestId`, cost data). Dual-path
  normalization is mandatory: HTTP-status signals and 200-OK
  `errors[].extensions.code` signals map into the same classes (Fact #9 +
  Open questions #2/#3).
- **How throttling/cost info is surfaced:** the client parses
  `extensions.cost.throttleStatus` (verbatim officially-documented field
  names — Fact #10) and returns it as structured metadata on every
  response object; it **never hard-codes bucket sizes** (officially
  unpublished — reads `maximumAvailable` at runtime); pacing *policy*
  (budgets, backpressure thresholds, `api_health_state` writing rules) is
  MBQ-51 and stays out of the shell — the shell only *exposes* the
  signal.
- **How redaction wraps every error/log:** every exception constructor
  and every log write inside the client passes through `redact()`; the
  client never logs request headers; DEBUG logging of bodies is
  redaction-wrapped or absent.
- **What it must not do:** no domain sync methods; no mutations in Task
  003 (the shell + test connection are read-only; the mutation path —
  including `@idempotent` key handling — is designed when the first
  domain needs it); no retry loops (retry policy belongs to the job
  layer per DEC-009 — the client raises normalized errors exactly once
  per call); no webhook registration; no cron; no bulk operations; no
  REST; no `ir.config_parameter` reads for secrets; no token in any
  return value, log, or exception.
- **How domain modules call it later:** only from job handlers registered
  through the accepted job-type seam — handler code calls
  `env['shopify.connector.api.client'].execute(store, …)`; domain modules
  never construct requests, read credentials, or parse raw errors
  themselves.
- **Test doubles/mocks future tests need:** a transport-injection seam
  (proposed: the lowest-level HTTP call isolated in one overridable
  private method, e.g. `_send(request)`) so tests can inject canned
  responses without network; fixture set: success (shop +
  accessScopes), `ACCESS_DENIED`, `THROTTLED` (fixture shape marked
  *unofficial/configurable* — Open question #1), `MAX_COST_EXCEEDED`
  (official sample exists), `INTERNAL_SERVER_ERROR` (+`requestId`), HTTP
  401/429/402/423/5xx, timeout, malformed JSON, fall-forward
  (`X-Shopify-API-Version` mismatch), and a token-bearing error body for
  redaction tests.

## Security and permissions

- **Groups:** the four existing groups only; no new group is proposed.
  Credential authority sits with `group_shopify_connector_admin`
  exclusively.
- **ACL implications (proposed Task 002 rows, MBQ-44-residual
  territory):** `shopify.connector.store.credential` — one row:
  Admin `1,1,1,0`; **no rows** for auditor/operator/reviewer
  (default-deny — Fact #15). No unlink for anyone, ever (history rule).
- **Record-rule implications:** none for Phase 1 (single store, no record
  rules — AR-019 §10 unchanged); the credential model carries `store_id`
  so a future multi-store rule needs no schema change.
- **Sudo risks (stated, minimized, justified):** exactly **two**
  sanctioned elevations are proposed, both landing in Task 003: (1) the
  client's internal credential read (above); (2) the core job-log
  writing choke point's **system-append write** — necessary because the
  merged ACL deliberately grants no group create on `job.log` (rows are
  "system-appended, not user-authored", AR-019 §10), so an Admin- or
  operator-context action that must record log rows needs a narrow,
  documented elevation inside the single log-writing helper (the
  alternative — widening the `job.log` ACL — would let users author
  audit rows and is **not** recommended; ChatGPT picks at review: this
  is a named decision point). Everything else runs as the acting user.
  `sudo()` bypasses ACLs, record rules, *and* field `groups` (Fact #13),
  so every `sudo()` in the credential/client/lifecycle code paths is a
  review-checklist item (§credential-security checklist) requiring
  written justification.
- **Least privilege:** Operator/Reviewer/Auditor have **zero** access to
  the credential model (not read, not `fields_get`); they see only the
  non-secret store mirrors. Scope requests to Shopify follow
  least-privilege (DEC-004): the required-scope list is exactly what
  enabled domains need, explicit `read_` handles included (Open question
  #5).
- **Admin-only actions:** credential entry/replacement/clear; test
  connection; disconnect/reconnect; activation. (Accepted role model.)
- **Auditor visibility:** read-only on store mirrors, jobs, logs — full
  history including credential *events* (who/when), never values.
- **Operator restrictions:** operators trigger syncs (job create) but
  cannot see or touch credentials; an operator-triggered sync's token
  access happens only inside the client's internal accessor — the
  operator never gains read access.
- **Reviewer restrictions:** as operator (minus job create, plus
  manual-review resolution); no credential access.
- **Pre-existing ACL gaps surfaced (not fixed here):** the merged Task
  001 CSV grants (1) **no group `perm_create` on
  `shopify.connector.store` or `shopify.connector.store.settings`**
  (Admin has `1,1,0,0`) — store creation is currently impossible for any
  connector role; fine for the zero-UI scaffold, but the future wizard
  requires a decided store/settings creation posture (widen Admin ACL
  vs. a service-method elevation); and (2) **no group create on
  `shopify.connector.job.log`** (all four groups `1,0,0,0`) — correct
  for its system-appended design intent, but it means every log-writing
  path (test connection, readiness, credential events, future syncs)
  depends on the sanctioned system-append elevation above. Both gaps are
  routed to the MBQ-44 residual (and Task 005 / Task 003 planning
  respectively); **neither is changed by Task 002.**

## UX alignment

How this foundation serves the accepted Premium Simplicity Standard
("clarity, confidence, polish, guidance, recovery — never more
screens/colors/charts/complexity"):

- **Calm credential entry:** one field, one model, one service call —
  the storage design imposes nothing extra on the accepted one-masked-
  field step; status mirrors give the wizard its "Credential saved — next
  we'll test it" verified moment without ever re-reading the secret.
- **Honest security copy:** the design *makes the honest copy true* —
  "stored with restricted access and never shown again" is literally what
  the model does (Admin-only model + no views + write-only entry), and
  nothing in the schema tempts an encryption claim.
- **Setup trust:** test connection proves rather than promises — named
  checks (reachability, identity, auth, scopes, version) each map to a
  concrete verified fact from one read-only query.
- **Recoverable auth errors:** `reconnect_needed` + error type 5 routing
  gives auth failure a first-class, Admin-owned recovery path (re-enter →
  test → readiness → resume) with history untouched — recovery, not
  blame.
- **No generic technical connector feel:** raw HTTP codes,
  `extensions.code` tokens, cost numbers, and stack traces are confined
  to the redacted technical-detail expand (RA-016); primary copy is
  plain-language with a named fix, every time.
- **Dashboard/readiness clarity:** readiness results feed the existing
  accepted cards and status fields — no new card, no chart, no vanity
  metric; warnings carry forward honestly with timestamps
  (`granted_scopes_checked_at` prevents implied-live-data dishonesty).

## Open items

1. MBQ-05 — supported credential acquisition path(s) after Shopify's
   custom-app-creation deprecation (admin-created legacy vs Dev Dashboard
   client-credentials; whether the connector must support the 24-hour
   client-credentials variant at MVP). **Needs a ChatGPT direction before
   Task 002's `token_variant` vocabulary is final** (the proposed single
   value `offline_custom_app` is safe either way).
2. Whether the compute-blank no-read-back hardening variant is adopted
   (ChatGPT decision at review; Task 002 carries it as a decision point).
3. `SHOP_INACTIVE`/402/423/403-fraudulent → error-class mapping
   confirmation (proposed `shopify_permission_scope_auth`).
4. The proposed third core `job_type` value `core_test_connection`
   (vocabulary extension vs. reusing `core_readiness_check`).
5. Scope-snapshot placement (`store` as proposed vs. credential model).
6. THROTTLED body shape; invalid-token HTTP status; missing-scope error
   shape; `shop`/`currentAppInstallation` scope requirements —
   **empirical verification steps in Task 003's acceptance criteria.**
7. Store/settings `perm_create` ACL gap (wizard-blocking; Task 005 /
   MBQ-44 residual).
7a. Job-log write path for system-appended rows: sanctioned
   system-append elevation in the core log choke point (recommended) vs.
   `job.log` ACL widening (not recommended) — ChatGPT decision with Task
   003; until it lands, Task 002's credential audit uses standard
   fields + stamps only.
7b. Latent `idempotency_key` collision for repeat runs of target-less
   core jobs (`core_readiness_check` today; `core_test_connection`
   proposed): per-run `payload_hash` nonce proposed — ChatGPT
   confirmation required with Task 003 since it touches accepted AR-019
   key semantics.
8. Cron/queue-health and `web.base.url` check mechanics (Task 004
   detail); per-domain required-scope lists (domain naming passes).
9. Exact readiness thresholds and all user-facing copy (MBQ-06 residual;
   MBQ-22).
10. In-flight job disposition at disconnect (Part A §I.4 open item,
    unchanged).
11. Scheduled/periodic credential health probe (not designed; possible
    later readiness extension).
12. Source-material capture: this sprint's official excerpts are embedded
    here with citations; copying high-value excerpts into
    `/docs/00-source-materials` was outside this sprint's allowed files —
    a small follow-up capture pass is recommended (same pattern AR-020
    logged).

## Proposed register impact

**This sprint does not edit `master-blueprint-open-questions.md`.** If
ChatGPT accepts this package, a future acceptance patch should apply:

- **MBQ-04:** remains **Partially resolved**, upgraded from posture level
  to **implementation-planning level**: record that the exact model
  (`shopify.connector.store.credential`), field set, access posture
  (Admin-only ACL + field `groups`), no-read-back/masking rules,
  redaction contract, rotation/replacement, disconnect/reconnect, audit
  metadata, and rollback behavior are accepted as planned (per this
  document), with only the coding task (Task 002) and its listed decision
  points outstanding. MBQ-04 closes fully when Task 002's implementation
  is reviewed and accepted.
- **MBQ-05:** record the 2026-07-06 official findings (admin custom-app
  creation deprecated; existing apps unaffected; Dev Dashboard
  client-credentials grant with 24-hour tokens; expiring-offline model
  explicitly excludes custom apps; one-time-reveal wording absent from
  live official pages) and either (a) decide the supported acquisition
  path(s) for MVP, or (b) explicitly hold MBQ-05 open with the
  `token_variant` seam as containment. Until then MBQ-05 continues to
  block the setup-wizard slice only.
- **MBQ-06:** no status change; note that the essential set now has a
  planning-level mechanics table (this document) and that the
  test-connection check is designed; residual (thresholds/copy)
  unchanged.
- **MBQ-44:** extend the AR-019 row-shape plan with the credential
  model's Admin-only row (and no-row-for-others posture); record the
  store/settings `perm_create` gap as a named residual for the lifecycle/
  wizard task.
- **MBQ-51:** no status change; note the client shell deliberately
  exposes `throttleStatus` without pacing policy, and that bucket sizes
  are officially unpublished (runtime `maximumAvailable` reads only).
- **MBQ-52:** no status change; note the planning default pin `2026-07`
  and the fall-forward detection mechanism (response-header comparison)
  as the health surface's input.
- **MBQ-08:** no status change; note the credential-clear-on-disconnect
  mechanics are now planned at field level (this document), residual
  state-machine mechanics unchanged.
