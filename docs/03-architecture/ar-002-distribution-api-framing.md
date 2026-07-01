# AR-002 — Distribution & API Strategy (Decision Framing)

> **RB-14 Architecture Preparation — Part 1.** This document **frames** the AR-002
> decision; it **does not decide it.** No choice is made between REST / GraphQL /
> hybrid, or between public-app / custom-app distribution, or between OAuth / token.
> AR-002 stays **[Not decided] / Evidence pending** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
>
> **Classification:** `[Official fact]` · `[Official limitation]` ·
> `[Competitor demonstrated]` · `[Competitor claim]` · `[Inference]` ·
> `[Recommendation]` · `[Open question]` · `[Decision — existing]` · `[Not decided]`.
> Competitor evidence is never an official fact; official facts do not decide our
> architecture; options and recommendations are not decisions.

## Decision question

**How should the connector talk to Shopify, and how should it be distributed?**
Concretely, three coupled sub-questions:

1. **Distribution:** public Shopify App Store app vs **custom/private app** (per-store
   or partner-installed) — and whether both must be supported eventually.
2. **API strategy:** GraphQL Admin API only, a **REST-where-simpler hybrid**, or
   REST-heavy — including how the controlled product **export/update** path performs
   full-state writes (`productSet`) safely, and whether **Bulk Operations** are needed
   internally for backfills.
3. **Authentication:** OAuth (token exchange / authorization-code grant) vs
   custom-app admin access token, and offline vs online token strategy.

## Why it matters

- **[Inference]** AR-002 is the **root dependency** of the whole architecture (see
  [`architecture-decision-framing.md`](./architecture-decision-framing.md) §6): it
  fixes the API surface, cost model, idempotency surface, auth model, and
  compliance burden that AR-003/005/006/007/008 all inherit.
- **[Inference]** The distribution choice is **not merely packaging** — it changes
  hard platform constraints (a new **public** app is GraphQL-only and OAuth-mandatory;
  a **custom** app has more latitude but no App-Store reach), so it must be framed
  **before** the API and auth details are settled.
- **[Official fact]** The controlled product export/update path DEC-003 puts in MVP
  relies on `productSet`, which **reconciles list fields by deleting omitted entries**
  — a full-state write. Getting the API/safety model wrong here is a **data-loss**
  risk, not a style choice.

## MVP scope inputs from DEC-003 (`[Decision — existing]`)

- **Controlled bidirectional product onboarding** in MVP → the API must support
  product import **and** safe export/update with **preview/dry-run before any
  destructive/full-state write** (DEC-003; `productSet` guardrail is **mandatory**,
  mechanism gated here).
- **Store connection + guided setup + test connection + credential masking** →
  auth-style and scope handling are in scope.
- **Order/customer import + inventory/fulfilment write-back** → the API must cover
  orders (60-day window / `read_all_orders`), protected customer data, inventory
  set/adjust, and FulfillmentOrder-based fulfilment.
- **Bulk Operations** are **not** a user-facing feature; whether they are needed
  **internally** for safe/resumable large backfills is **explicitly an AR-002
  question** (DEC-003 "Bulk operations decision").
- **Single-store / single-company** MVP, but **architecture-safe** (must not block
  future multi-store or a future public-app path).
- **Deferred:** customer export; unrestricted autonomous bidirectional catalog
  ownership; public App-Store packaging/billing/compliance-webhook work "unless
  distribution is later decided."

## Shopify official constraints (`[Official fact]` / `[Official limitation]`)

Refreshed 2026-07-01 (see [`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md);
citations in [`../01-research/shopify-official-api-notes.md`](../01-research/shopify-official-api-notes.md)).

- **[Official fact]** "All apps and integrations should be built with the GraphQL
  Admin API." (shopify.dev/docs/apps/build/graphql/migrate)
- **[Official fact]** "The REST Admin API is a legacy API as of October 1, 2024,"
  in maintenance mode; new features ship in GraphQL first.
  (shopify.dev/docs/api/admin-rest; …/graphql/migrate)
- **[Official limitation]** **New public apps** submitted to the App Store **must be
  built exclusively with the GraphQL Admin API as of April 1, 2025.**
  (shopify.dev/docs/api/admin-rest; changelog)
- **[Open question]** Whether the GraphQL-only mandate binds **custom/private apps**
  (vs only public apps), and the final/last-supported **REST version / sunset date**,
  are **not stated** on the fetched pages. This directly affects a REST-heavy or
  hybrid option for custom-app deployments.
- **[Official fact]** REST and GraphQL use **different ID formats**; REST numeric IDs
  must be converted to the GraphQL **global ID (GID)**; some features are GraphQL-only
  and some REST resources have no exact GraphQL equivalent. (…/graphql/migrate)
- **[Official limitation]** **`productSet`** creates/updates a whole product in one
  request and **reconciles list fields (variants, collections, metafields) by deleting
  omitted entries** (supports `synchronous: false` for large inputs). Treating it as a
  partial update is a **data-loss footgun**.
  (shopify.dev/docs/api/admin-graphql/latest/mutations/productSet)
- **[Official fact]** New product model supports **up to 2,048 variants** per product;
  apps not on the in-support GraphQL product APIs degrade above 100.
  (changelog: variant-limit-2048)
- **[Official fact]** Auth uses **OAuth 2.0**; **token exchange** (embedded apps,
  recommended) and **authorization code grant** (standalone). **Offline** tokens don't
  expire by default; **online** tokens expire (~24h). Requests send
  `X-Shopify-Access-Token`. (shopify.dev/docs/apps/build/authentication-authorization
  + /access-tokens)
- **[Official limitation]** Apps have **no access to protected customer data** by
  default; orders/customers require meeting protected-customer-data requirements
  (**Level 1** / **Level 2**) + Shopify approval; order access defaults to the **last
  60 days**, and all orders needs **`read_all_orders` + Shopify approval**.
  (shopify.dev/docs/apps/launch/protected-customer-data; …/usage/access-scopes)
- **[Official limitation]** App Store apps must implement the **three mandatory
  compliance webhooks** (`customers/data_request`, `customers/redact`, `shop/redact`),
  authenticate **OAuth-first**, serve over **TLS**, and (new public apps) be
  GraphQL-only + use the **Billing API**.
  (shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements)
- **[Official fact]** GraphQL uses a **calculated query-cost** model (points; single
  query ≤ 1,000 points; `extensions.cost` + `throttleStatus`); REST uses a
  **leaky-bucket** with **429 + `Retry-After`**. Large reads/writes can move to
  **Bulk Operations** (async JSONL; concurrency raised to up to 5 of each in 2026-01).
  (shopify.dev/docs/api/usage/limits; …/admin-rest/usage/rate-limits;
  …/usage/bulk-operations/queries)
- **[Official fact]** **`inventorySetQuantities` / `inventoryAdjustQuantities` and
  `refundCreate` require an idempotency key (`@idempotent`) as of API 2026-04** — the
  API surface itself enforces idempotency for these writes.
  (shopify.dev/docs/api/admin-graphql/latest/mutations/inventorySetQuantities)

## Odoo constraints (`[Official fact]` / `[Official limitation]` / `[Open question]`)

Citations in [`../01-research/odoo-official-architecture-notes.md`](../01-research/odoo-official-architecture-notes.md).

- **[Official fact]** Odoo integrates external systems through standard addons that
  extend `sale`/`stock`/`product`/`account`/`delivery`; there is **no Shopify-specific
  transport in core** — the connector owns the HTTP/GraphQL client.
- **[Official fact]** Secrets/config are typically stored as records (e.g.
  `ir.config_parameter` or dedicated config models) behind **access rights / groups**;
  field-level `groups` can restrict credential fields. (security.rst)
- **[Open question]** Whether **Odoo Online (SaaS)** permits the outbound HTTPS,
  external Python libraries, `server_wide_modules`, and long-running workers a given
  API/queue design needs — **hosting is not finalized here** and constrains AR-002 ↔
  AR-003 jointly. (administration/on_premise/deploy; odoo_sh/branches)
- **[Official fact]** Odoo.sh **staging/development crons are disabled** (neutralized
  duplicates), so any sync verification must trigger runs manually — a **testing**
  constraint for whichever API/orchestration path is chosen.

## Competitor evidence inputs (`[Competitor demonstrated]` / `[Competitor claim]`)

From the Sprint C/C2 matrix and deep dives (evidence, not facts):

- **[Competitor demonstrated]** Every studied connector connects via a **custom
  Shopify app**; **VentorTech (VT)** and **TeqStars (TQ)** use **OAuth** (TQ also
  supports manual token / legacy password); WK/EM/SH paste credentials.
- **[Competitor demonstrated]** **VentorTech migrated REST→GraphQL in v2.0.0
  (2026-01-23)** and shipped **Shopify API 2026-04 compliance (v2.1.4)** — a
  real-world convergence on GraphQL + idempotency.
- **[Competitor claim]** **TeqStars docs state** sync/webhooks/refunds/cancel/payouts
  all use the **Shopify GraphQL Admin API** (a vendor doc statement, not independently
  verified wire behaviour).
- **[Competitor demonstrated]** **Emipro (EM)** documents **both REST and GraphQL**
  (GraphQL required for customer export, SO export, Markets, returns import) — a
  hybrid in practice, and a **trailing-slash auth footgun** on the token wizard.
- **[Competitor demonstrated]** **TeqStars controlled, draft-safe product export** —
  "Add to Listings" → Export Listings with **sales-channels-optional = unpublished**,
  Publish/Unpublish, per-listing **Skip-Sync** badge — a concrete pattern for the
  DEC-003 controlled-onboarding path (directly relevant, but **not** a decision).
- **[Competitor demonstrated]** **VT draft-export-for-review** + **Preview/Report
  dry-run** before export; **[Inference]** aligns with the DEC-003 preview/dry-run
  guardrail before destructive apply.
- **[Inference]** No competitor demonstrates a **named rate-limit / GraphQL-cost
  throttling** strategy (TQ confirmed ⬜; VT closest with "avoid unnecessary API
  requests") — a **whitespace** for AR-002/AR-006, not a competitor capability we can
  cite as a fact.

## Candidate options (framing only — none selected)

> These are **[Not decided]** options for ChatGPT to weigh, not a shortlist we have
> narrowed. Each is stated with evidence for/against, risks, and implications.

### Option A — Public App Store app, OAuth-first, GraphQL-first

- **Evidence for:** `[Official fact]` GraphQL is the primary/recommended API and the
  **only** allowed API for new public apps; `[Official fact]` OAuth + token exchange is
  the platform-standard install; `[Competitor demonstrated]` VT/TQ prove OAuth-first
  works.
- **Evidence against:** `[Official limitation]` public apps carry the **full App-Store
  burden** (compliance webhooks, Built-for-Shopify performance thresholds,
  protected-customer-data Level 1/2 approval, Billing API); DEC-003 explicitly
  **defers** public App-Store packaging.
- **Risks:** heaviest compliance/maintenance surface; approval latency; performance
  budgets (LCP/CLS/INP) that couple app UX to Shopify review.
- **UX implications:** embedded-admin App Bridge + session tokens; smoothest merchant
  install (OAuth click-through) but the connector UI must meet Shopify performance
  budgets.
- **Implementation implications:** GraphQL-only client; Billing API; mandatory
  compliance webhooks; embedded session-token handling.
- **App-Store implications:** **maximal** — this *is* the App-Store path.
- **Odoo hosting implications:** the Odoo side still needs reachable HTTPS webhooks +
  OAuth callback; Odoo-Online feasibility is an open question (AR-003).
- **Open questions:** is public distribution even in scope for MVP (DEC-003 defers it)?
  Does the added burden justify GraphQL-only regardless of distribution?

### Option B — Custom/private app, token or OAuth, GraphQL-first

- **Evidence for:** `[Decision — existing]` matches the DEC-003 single-store,
  no-App-Store MVP; `[Competitor demonstrated]` the common market shape (custom app +
  token/OAuth); GraphQL-first still aligns with `[Official fact]` GraphQL-primary and
  future-proofs toward a later public path.
- **Evidence against:** `[Open question]` whether GraphQL-only binds custom apps is
  unconfirmed — a custom app *could* use REST where simpler, but that risks a dead-end
  if the app later goes public; no App-Store reach.
- **Risks:** per-store setup friction (custom app creation, scope grant, token); if
  built REST-heavy, a costly later migration (VT's REST→GraphQL migration is the
  cautionary precedent).
- **UX implications:** guided custom-app setup wizard + credential masking + test
  connection (DEC-003); more setup steps than public OAuth, so the wizard must
  pre-empt known failures (EM trailing-slash footgun).
- **Implementation implications:** offline token storage behind Odoo groups; GraphQL
  client + `productSet` full-state safety + `@idempotent` writes.
- **App-Store implications:** none now, but **keep GraphQL-first** to preserve a future
  public option.
- **Odoo hosting implications:** works on Odoo.sh / on-prem; Odoo-Online outbound-HTTPS
  feasibility open (AR-003).
- **Open questions:** OAuth vs plain admin token for a custom app; offline-token refresh
  strategy; per-store scope minimization.

### Option C — Hybrid API (GraphQL primary + REST where strictly simpler)

- **Evidence for:** `[Competitor demonstrated]` EM ships a de-facto hybrid; some
  operations historically simpler in REST.
- **Evidence against:** `[Official fact]` REST is **legacy** and new features are
  GraphQL-first; `[Official fact]` dual ID formats (numeric vs GID) add conversion +
  binding complexity; new public apps **cannot** use REST at all.
- **Risks:** two client stacks; GID/numeric-ID reconciliation bugs (ties to AR-005);
  REST endpoints deprecating under the app.
- **UX implications:** largely invisible to users; risk surfaces as inconsistent
  behaviour/latency between REST- and GraphQL-backed operations.
- **Implementation implications:** maintain + test two transports; a clear rule for
  when REST is used; GID↔numeric mapping in the binding layer.
- **App-Store implications:** **incompatible** with a future public app (GraphQL-only).
- **Odoo hosting implications:** neutral.
- **Open questions:** are there operations still materially simpler/cheaper in REST as
  of 2026-07-01, or has GraphQL closed the gap?

### Option D — REST-heavy

- **Evidence for:** none current — included only for completeness/traceability.
- **Evidence against:** `[Official fact]` REST is legacy; `[Official limitation]` new
  public apps are GraphQL-only; `[Official fact]` the 2,048-variant product model
  degrades badly off the GraphQL product APIs; `[Competitor demonstrated]` VT
  **migrated away** from REST.
- **Risks:** near-certain dead-end; data-model degradation; rework.
- **UX / implementation / App-Store / hosting:** strictly worse than A–C on the
  platform-direction axis.
- **Open questions:** none that would revive it absent a major Shopify reversal.
- **[Inference]** This option looks like an **avoid-list candidate** (A-SYNC-adjacent),
  but it is **not** rejected here — rejection routes through ChatGPT/architecture review
  and `rejected-approaches-log.md` (`CLAUDE.md` §10).

## UX implications (support only — no screens designed)

Grounded in [`../02-product/setup-ux-principles.md`](../02-product/setup-ux-principles.md)
and [`../01-research/gaps-opportunities.md`](../01-research/gaps-opportunities.md):

- **Setup friction:** distribution choice drives the **setup wizard** shape — public
  OAuth is a near-one-click install; custom-app is a multi-step credential/scope flow
  that must **validate inline**, mask secrets, run a **test connection**, and pre-empt
  known failures (trailing-slash, missing scopes). `[Recommendation]` a **pre-flight
  readiness check** (scopes, HTTPS/`web.base.url`, webhook reachability) regardless of
  option.
- **Destructive-action safeguards:** because `productSet` is delete-on-omit, the
  export/update UX **must** surface a **preview/dry-run diff** before any full-state
  write (DEC-003 mandatory guardrail; VT/EM/TQ show the pattern). This is a
  **first-sync-confidence** and **data-safety** requirement the API choice must support.
- **Admin/operator clarity:** GraphQL cost/429 behaviour should surface as **honest,
  named** throttle/health status (generalized traffic-light), not opaque failures.
- **Error recovery:** protected-customer-data / scope failures must produce a
  **named-cause** message with the fix, not a raw API error.
- **First-sync confidence:** the matching + duplicate-prevention preview (AR-005) plus
  a dry-run export together let a non-developer trust the first bidirectional product
  sync — the API path must make both cheap to render.

## Required evidence before an AR-002 decision

- **[Open question]** Confirm whether the **GraphQL-only mandate binds custom/private
  apps** and any **REST sunset date** (Tier-1 open question).
- **[Open question]** Confirm the **intended distribution** (public App-Store vs
  custom) with ChatGPT — this gates OAuth-mandatory / GraphQL-only / App-Store
  readiness and the internal-bulk need.
- **[Open question]** Confirm **`productSet` full-state semantics** and the minimal
  safe-diff/preview mechanics for the controlled export path.
- **[Open question]** Confirm whether **Bulk Operations are required internally** for
  safe/resumable backfills (concurrency/JSONL/time limits).
- **[Open question]** Confirm **protected-customer-data Level 1/2** obligations for the
  MVP order/customer scopes and any approval lead time.
- **[Open question]** Confirm **offline vs online token** strategy for a custom app and
  scope minimization for MVP.

## Recommended decision criteria (recommendation, not a decision)

- **[Recommendation]** Prefer the option that **future-proofs toward GraphQL** (avoids
  a REST dead-end) **without** taking on the full App-Store burden before DEC-003
  authorizes public distribution.
- **[Recommendation]** Require any chosen option to make the **`productSet` preview/
  dry-run** and **`@idempotent` writes** cheap and mandatory (correctness > breadth).
- **[Recommendation]** Keep **binding/GID handling** (AR-005) explicit so a future
  distribution/API change does not corrupt identity.
- **[Recommendation]** Treat **distribution** and **API strategy** as **two linked
  decisions**, deciding distribution first because it changes the API constraints.

> **No decision is made in this document.** AR-002 remains **[Not decided] / Evidence
> pending**. The options, criteria, and open questions above are **inputs** for a
> future ChatGPT-approved architecture-decision sprint (`CLAUDE.md` §4–§5; RB-14).
