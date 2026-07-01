# RB-14 Part 2 — High-Risk Open-Question Resolution (Official-Source / Source-Code)

> **RB-14 Architecture Preparation — Part 2.** A **dated evidence-resolution** file that
> re-checks **only the high-risk open questions** surfaced by RB-14 Part 1 (PR #57) against
> **official Shopify docs**, **official Odoo 19.0 docs**, and **official Odoo 19.0 source
> code**. It **resolves or narrows** each question **where official evidence supports it**
> and **keeps unresolved items unresolved** where it does not. **It makes no architecture
> decision.** AR-002 / AR-003 / AR-005 remain **[Not decided] / Evidence pending**
> ([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)); the
> no-code and no-decision gates hold (`CLAUDE.md` §4–§5).
>
> **Companion documents:** the RB-14 Part 1 refresh
> ([`rb14-official-source-refresh.md`](./rb14-official-source-refresh.md)) remains the Part 1
> dated baseline; this file is the **Part 2 delta**. Narrowing feeds the decision-candidate
> brief ([`rb14-decision-candidate-brief.md`](./rb14-decision-candidate-brief.md)) and the
> AR framing docs (AR-002 / AR-003 / AR-005).

## Scope and date

- **Access date for this resolution pass:** **2026-07-01** (same session date; the Part 1
  refresh was also 2026-07-01, earlier in the day — this pass adds **source-code** evidence
  and **new official pages** not fetched in Part 1).
- **Scope:** **only** the ten high-risk questions the RB-14 Part 2 prompt enumerates —
  **RQ-002-1/2/3** (AR-002), **RQ-003-1/2/3** (AR-003), **RQ-005-1/2/3/4** (AR-005). No
  other topic was re-surveyed; non-listed facts keep their Part 1 / Sprint B status.
- **Method:** four source-code / doc questions were verified **directly** by reading the
  official Odoo 19.0 source (`github.com/odoo/odoo`, branch `19.0`) and the Shopify GID
  page; the six remaining **doc** questions were verified by a **scoped, documented
  high-power fan-out** (6 official-source verifiers + 6 adversarial cross-verifiers, one
  per question) that fetched fixed official page sets, returned **verbatim-quoted,
  claim-classified** facts, and re-checked every load-bearing quote. **All six
  cross-verifiers confirmed their verifier's status** with no surviving overclaim (two
  minor quote-transcription fixes were applied here). Competitor evidence was **excluded**.
- **Governance:** no-code gate and no-decision gate in force. Source-code facts are labelled
  **[Official source-code fact]** and are **not** turned into architecture decisions.

## Source rules

- **Shopify facts** → official `shopify.dev` developer documentation and the official
  `shopify.dev/changelog` (Tier-1). No competitor/blog/forum.
- **Odoo facts** → official `odoo.com/documentation/19.0`; where the HTML rendered
  navigation-only (the known JS-render caveat), the official **`odoo/documentation` 19.0
  raw RST** (`raw.githubusercontent.com/odoo/documentation/19.0/content/...`) — the
  sanctioned Sprint B/Part 1 fallback.
- **Odoo source-code facts** → official **`odoo/odoo` branch `19.0`**, read via the raw
  file. Per the sprint rule, **no source is copied into the repo** beyond short,
  legally-safe snippets; findings are **paraphrased with file/line references and short
  quotes**.
- **Classification (per `CLAUDE.md` §8 + the RB-14 Part 2 prompt):** `[Official fact]` ·
  `[Official limitation]` · `[Official source-code fact]` · `[Inference]` ·
  `[Recommendation]` · `[Decision candidate]` · `[Open question]` · `[Decision — existing]`
  · `[Not decided]`. Every factual claim carries **source URL/path**, **source type**,
  **access date (2026-07-01)**, and **claim class**.

## Questions reviewed

| Row | Question | Short title |
| --- | --- | --- |
| AR-002 | RQ-002-1 | GraphQL-only mandate scope (public vs custom/private) |
| AR-002 | RQ-002-2 | Custom/private privacy + compliance-webhook obligations |
| AR-002 | RQ-002-3 | Custom-app token/auth model + setup implications |
| AR-003 | RQ-003-1 | Odoo Online feasibility for a custom connector module |
| AR-003 | RQ-003-2 | Official Odoo core async-queue availability |
| AR-003 | RQ-003-3 | `ir.cron` operational signatures + failure constants |
| AR-005 | RQ-005-1 | Shopify GID permanence / deleted-recreated records |
| AR-005 | RQ-005-2 | General mutation idempotency beyond `@idempotent` |
| AR-005 | RQ-005-3 | `ir.model.data` fields / uniqueness / binding suitability |
| AR-005 | RQ-005-4 | `sudo()` bypass of access rights / record rules |

## Executive summary

Part 2 **resolved three source-code questions outright**, **materially narrowed three
Shopify-doc questions**, **resolved the core of the Odoo-Online question**, and **kept the
genuinely-unsupported items open** — with **no architecture decision**:

- **New, decision-relevant facts (changed since Part 1):**
  - **[Official fact]** Shopify **tracks idempotency keys for 24 hours** (server dedup TTL
    — a Part 1 open question **now resolved**), and the `@idempotent` directive is scoped to
    a **fixed list of 17 mutations** (inventory/location + `refundCreate`); **no general /
    all-mutation idempotency and no `clientMutationId`** exist (RQ-005-2).
  - **[Official limitation]** **"Odoo Online is incompatible with custom modules or modules
    from the Odoo Apps Store"** — the connector's **custom module cannot run on Odoo
    Online**; the hosting target is **Odoo.sh or on-premise** (RQ-003-1; a Part 1 open
    question **now resolved at its core**).
  - **[Official source-code fact]** `ir.model.data` enforces **`UniqueIndex('(module,
    name)')`** and exposes exactly `name/complete_name/model/module/res_id/noupdate/
    reference` (RQ-005-3 — Part 1 open question **now resolved**); **`sudo()` "simply
    bypasses access rights checks"** and its warning states it **"could cause data access to
    cross the boundaries of record rules"** (RQ-005-4 — Part 1 "not literally on
    `security.rst`" concern **now resolved from the ORM source**).
  - **[Official source-code fact]** Exact 19.0 `ir.cron` signatures — `_trigger(at=None)`,
    `method_direct_trigger`, `_commit_progress(processed=0, *, remaining=None,
    deactivate=False) -> float` — and the failure constants
    `CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3`, `MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5`,
    `MIN_DELTA_BEFORE_DEACTIVATION = 7 days` (RQ-003-3 — **resolved**).
  - **[Official fact]** Custom apps are **not categorically forbidden from REST** — a
    changelog permits REST product APIs for custom apps under 100 variants while signalling
    **"GraphQL … will be the only supported API over the long term"** with **no REST EOL
    date** (RQ-002-1 — **narrowed**, custom-app blanket scope still open).
  - **[Official fact]** **Protected-customer-data access matrix**: public apps **"Requires
    review"**, custom apps and Admin-created custom apps **"Always available"** (Admin L2
    "Varies by plan"); the **three compliance webhooks** are required **"for apps listed on
    the Shopify App Store"** (RQ-002-2 — **narrowed**; custom-app webhook/obligation scope
    still open, **not assumed absent**).
- **Confirmed unchanged (Part 1 findings re-verified):** **GID permanence is NOT asserted**
  (RQ-005-1); **Odoo core documents/ships only `ir.cron`** as the async primitive, with a
  general async job queue **not found** (RQ-003-2, stays an inference — a negative that
  cannot be proven from one file set).
- **Still open (kept open — no official statement):** custom/private blanket GraphQL-mandate
  scope + REST EOL date; whether custom apps must implement the compliance webhooks and
  whether Level 1/2 obligations bind them; `@idempotent` **key-uniqueness scope**
  (per-shop/app/global); **bulk-operation idempotency**; **GID permanence/non-reuse**; the
  proof that **no** async queue exists anywhere in Odoo core.

**No architecture decision is made.** Every narrowing below is an **input** labelled
`[Recommendation]` / `[Decision candidate]` in the companion brief; every AR row stays
`[Not decided]`.

---

## Resolution table

| Q ID | Row | Question | Status | Evidence found (class) | Evidence not found (stays open) | Architecture implication (input, not decision) | Decision-readiness impact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RQ-002-1 | AR-002 | GraphQL-only mandate: public vs custom | **Partially resolved** | Mandate scoped to **"new public apps"** (2025-04-01); REST **"legacy as of 2024-10-01"**; custom apps may keep REST product APIs **<100 variants**; **GraphQL "only supported … long term"** `[Official fact]`/`[Official limitation]` | No **blanket** custom-app REST prohibition/permission; **no REST EOL date**; existing-public-app migration deadline `[Open question]` | Custom-app API choice can't be justified as "REST is forbidden"; a GraphQL-first stance rests on *legacy/long-term* signals + the 2048-variant model, not a prohibition | AR-002 API sub-question **narrower**; distribution still the prior fork |
| RQ-002-2 | AR-002 | Custom/private privacy + compliance webhooks | **Partially resolved** | **Compliance webhooks required "for apps listed on the Shopify App Store"**; **protected-data access**: public "Requires review", custom/admin "Always available" (admin L2 "Varies by plan"); L1/L2 obligations attach to **data kind** `[Official fact]`/`[Official limitation]` | Whether **custom apps must implement** the 3 webhooks; whether L1/L2 **obligations bind** custom apps; general non-App-Store privacy duties `[Open question]` — **not assumed absent** | Custom distribution removes the **review gate** (no approval, access "Always available") but **cannot be documented as "no obligations"** | AR-002 distribution burden **clearer**; custom-app duty surface still open |
| RQ-002-3 | AR-002 | Custom-app token/auth model | **Partially resolved** | Two acquisition paths (**token exchange** / **authorization-code grant**); **online** expire logout/24h; **offline** non-expiring (until uninstall/secret-revocation) **or** expiring (**1h access + 90-day rotating refresh**) `[Official fact]`/`[Official limitation]`; admin-created custom-app token `[Official fact — Part 1]` | Exact current dev-doc wording of "token installed on generation" on the access-tokens **index**; a cross-model **rotation/revocation** policy statement `[Open question]` (least-privilege is `[Official fact]` from Sprint B access-scopes) | An unattended connector maps to the **offline** token model; non-expiring vs expiring-with-rotation is a real setup/credential-storage trade-off | AR-002 auth options **well-characterised**; OAuth-vs-token **not decided** |
| RQ-003-1 | AR-003 | Odoo Online feasibility | **Partially resolved (core resolved)** | **"Odoo Online is incompatible with custom modules or modules from the Odoo Apps Store"** `[Official limitation]`; Odoo.sh installs custom modules from branch, staging crons disabled; on-prem multi-worker + dedicated cron + reverse-proxy HTTPS `[Official fact]` | Odoo Online outbound-HTTPS / controllers / `server_wide_modules` / workers / jobrunner (moot but not literally stated); Odoo.sh jobrunner/`server_wide_modules` `[Open question]` | The custom connector module **cannot target Odoo Online**; substrate lives on **Odoo.sh / on-prem** | AR-003 hosting floor **resolved**; substrate still tied to Odoo.sh/on-prem capabilities |
| RQ-003-2 | AR-003 | Core async-queue availability | **Partially resolved** | `ir.cron` (models `IrCron`/`IrCronTrigger`/`IrCronProgress`) is the **only** documented/shipped async primitive in base; **no `with_delay`** in `ir_cron.py` or `odoo/orm/models.py` `[Official source-code fact]` | Positive proof that **no** general async queue exists **anywhere** in 19.0 core (cannot prove a negative from one file set) `[Inference]`/`[Open question]` | Background sync on stock Odoo 19 rests on `ir.cron`; a true queue = **community** `queue_job` (non-core dependency) | AR-003 substrate question **sharpened**, still a real decision |
| RQ-003-3 | AR-003 | `ir.cron` signatures + failure model | **Resolved** | `_trigger(self, at=None)`, `method_direct_trigger`, `_commit_progress(self, processed=0, *, remaining=None, deactivate=False) -> float`; consts `3` (timeout→failure), `5` + `7 days` (deactivate) `[Official source-code fact]`; `--max-cron-threads` + Odoo.sh staging neutralization re-confirmed `[Official fact]` | — (fully sourced) | Connector orchestration must own **per-record retry/backoff + isolation**; use `_trigger`/batch/`_commit_progress`; expect coarse deactivation | AR-003 mechanics **decision-ready** as inputs |
| RQ-005-1 | AR-005 | GID permanence / deletion | **Partially resolved (not asserted)** | GID = **"uniquely identifies an object"**; Node/Product id = **"A globally-unique ID"** `[Official fact]` | **No** statement of permanence / non-reuse / deleted-recreated behaviour `[Open question]` | Binding must **not assume GID permanence**; deleted/recreated handling is a design requirement | AR-005 confirms Part 1: **do not treat GID as immutable invariant** |
| RQ-005-2 | AR-005 | General mutation idempotency | **Partially resolved** | **24-hour** key retention; **17-mutation** `@idempotent` list; `IDEMPOTENCY_CONCURRENT_REQUEST`; **no general mechanism / no `clientMutationId`** `[Official fact]`/`[Official limitation]` | Key **uniqueness scope** (per-shop/app/global); **bulk-op idempotency** `[Open question]` | Outbound write idempotency **outside the 17 mutations** and cross-request dedup beyond 24h are **connector-designed** | AR-005/AR-006 idempotency surface **much clearer** |
| RQ-005-3 | AR-005 | `ir.model.data` fields / uniqueness | **Resolved** | Fields `name/complete_name/model/module/res_id/noupdate/reference`; **`UniqueIndex('(module, name)')`** + `Index('(model, res_id)')`; docstring = **third-party data integration AND module-data-origin**; `_allow_sudo_commands = False` `[Official source-code fact]` | — (fully sourced; suitability is a design judgement, not decided) | It **has** (module,name) uniqueness + db-id-independence but **no per-store dimension, no audit/binding-status fields**, and module-lifecycle semantics | AR-005 can weigh reuse-vs-dedicated on **facts**, not guesses (no decision) |
| RQ-005-4 | AR-005 | `sudo()` bypass semantics | **Resolved** | `sudo()` docstring: **"simply bypasses access rights checks"**; warning: **"could cause data access to cross the boundaries of record rules"** (multi-company isolation named) `[Official source-code fact]` | Precise field-level-`groups` × superuser read/write interaction `[Open question]` (minor) | Credential handling / per-store isolation must treat `sudo()` as a **deliberate, audited** bypass; record-rule isolation is defeated under sudo | AR-002/AR-005 security inputs **resolved** |

---

## Detailed notes

> Each fact carries **source URL/path**, **source type**, **access date 2026-07-01**, and
> **claim class**. Verbatim quotes are marked with quotation marks; everything else is
> paraphrase or inference.

### RQ-002-1 — GraphQL-only mandate scope

**Status: Partially resolved.**

- `[Official fact]` "Starting April 1, 2025, all new public apps must be built exclusively
  with the GraphQL Admin API." — `shopify.dev/docs/api/admin-rest` (official Shopify docs);
  repeated on `…/shopify-app-store/app-store-requirements` ("As of April 1, 2025 all new
  public apps must be built exclusively with the GraphQL Admin API."). **The binding "must"
  is scoped to *new public apps*.**
- `[Official limitation]` "The REST Admin API is a legacy API as of October 1, 2024." —
  `shopify.dev/docs/api/admin-rest`. This is the **only** stated status-change date; **no
  separate REST sunset/EOL date** is published.
- `[Official fact]` "The REST Admin API is a legacy API as of October 1, 2024. All apps and
  integrations should be built with the GraphQL Admin API." — `…/graphql/migrate`. This is
  **advisory ("should")**, not a prohibition, and does not scope a *mandate* to custom apps.
- `[Official fact]` (new in Part 2) "Custom apps built on REST that do not need to support
  more than 100 variants can continue to use the deprecated REST product APIs." and
  `[Official limitation]` "Developers should expect that the GraphQL API will be the only
  supported API over the long term." —
  `shopify.dev/changelog/deprecation-timelines-related-to-new-graphql-product-apis`
  (official changelog). So **custom apps are NOT categorically forbidden from REST**, but
  the only affirmative permission is **narrow** (product APIs, <100 variants) and carries a
  long-term-GraphQL-only warning.
- `[Official fact]` "If you create a custom app through the Shopify admin, then you can't
  change the app distribution method." and custom distribution "to one store or multiple
  stores on the same Plus organization using a link." —
  `…/apps/launch/distribution/select-distribution-method`.
- `[Open question]` **No official page states that custom/private/Admin-created apps are
  *forbidden* from — or *permanently permitted* to use — the REST Admin API in general**;
  the mandate wording ("new public apps") is silent on custom apps. **No REST EOL date**;
  **existing-public-app** migration obligation not literally stated.

**Adversarial cross-verify:** re-fetched all six pages; every quote confirmed verbatim; the
narrow custom-app REST permission was **not** over-read as a blanket permission; status
`Partially resolved` upheld (no grounds to upgrade to Resolved or downgrade to Still open).

**Architecture implication (input, not decision):** a custom-app API-surface choice cannot
be justified as "REST is officially forbidden"; a GraphQL-first stance rests on the
*legacy* + *only-supported-long-term* signals and the 2048-variant product model, not on a
prohibition. Distribution (public vs custom) remains the **prior** fork that sets the API
constraints. **[Not decided].**

### RQ-002-2 — Custom/private privacy + compliance-webhook obligations

**Status: Partially resolved.** Three sub-questions answered unevenly:

- **(a) App-Store review gate — resolved (public-scoped).**
  - `[Official fact]` "Mandatory compliance webhooks are callback methods that Shopify
    requires for apps listed on the Shopify App Store." and "Any app that you distribute
    through the Shopify App Store must respond to data subject requests, regardless of
    whether the app collects personal data." — `…/apps/build/compliance/privacy-law-compliance`.
  - `[Official fact]` "Public apps request access to protected customer data and protected
    customer fields through the Partner Dashboard." and only Public distribution submits to
    the app-review team — `…/apps/launch/protected-customer-data`,
    `…/distribution/select-distribution-method`.
  - `[Official fact]` **Protected-data access matrix** — Level 1: Public "Requires review",
    Custom "Always available", Admin-created custom "Always available"; Level 2: Public
    "Requires review", Custom "Always available", Admin-created "Varies by plan". "You don't
    need to submit a request for review for apps that are installed only on development
    stores." — `…/apps/launch/protected-customer-data`.
- **(b) Compliance-webhook obligation for custom apps — still open.**
  - `[Open question]` The privacy page scopes the webhook requirement **only** to App-Store
    apps and makes **no statement** — neither obligation nor exemption — about custom/
    private/Admin-created apps. **Absence is not proof of exemption**; do **not** record
    custom apps as webhook-exempt. — `…/privacy-law-compliance`.
- **(c) Substantive Level 1/2 obligations — partially / open.**
  - `[Official fact]` Obligations attach to the **kind** of data used: "If you're using only
    protected customer data, then you must meet the level 1 requirements"; name/address/
    phone/email fields trigger "all of the level 1 and 2 requirements." Level 1 = data
    minimization, transparency, purpose limitation, consent/opt-out, retention, "Encrypt
    data at rest and in transit." Level 2 adds encrypted backups, test/prod separation, DLP,
    staff-access limits, "Keep an access log to protected customer data," incident-response.
    — `…/apps/launch/protected-customer-data`.
  - `[Open question]` The page does **not** literally state whether these substantive
    obligations **bind custom/Admin-created apps** regardless of distribution — "Always
    available" speaks to **access**, not to obligation applicability. Kept open.

**Adversarial cross-verify:** re-fetched the three load-bearing pages; access matrix + webhook
scoping + data-kind obligations confirmed verbatim; the "Always available" cell was **not**
conflated with obligation-applicability; status upheld.

**Architecture implication (input, not decision):** distribution changes **which official
obligations are documented**. A public/App-Store connector carries hard, documented duties
(3 compliance webhooks, protected-data review at L1/L2, TLS, return-collected-data). A
custom/Admin-created connector **removes the review gate** (access "Always available", no
approval) **but cannot be documented as obligation-free** — the compliance-webhook and L1/L2
obligation questions are **open and must be resolved or conservatively assumed**, not assumed
absent. **[Not decided].**

### RQ-002-3 — Custom-app token/auth model + setup implications

**Status: Partially resolved.**

- `[Official fact]` "The Shopify platform provides two ways for apps to acquire an access
  token: token exchange and authorization code grant." — `…/authentication-authorization/access-tokens`.
  - **Token exchange** — "OAuth 2.0 token exchange allows apps to exchange a session token
    for an access token. The session token is only available for apps rendered in the
    Shopify admin and can be acquired using App Bridge." `requested_token_type` selects
    online vs **offline (default)**. — `…/access-tokens/token-exchange`.
  - **Authorization code grant** — "This guide is only relevant to standalone apps and
    legacy apps that aren't using Shopify managed installation." Online via
    `grant_options[]=per-user`; omit for offline; `expiring=1` for expiring offline; requests
    carry `X-Shopify-Access-Token`. — `…/access-tokens/authorization-code-grant`.
- `[Official fact]` **Online tokens**: "linked to an individual user … lifespan matches the
  lifespan of the user's web session"; "expire either when the user logs out or after 24
  hours"; "respect the user's individual permissions"; revoked on logout; expired → 401. —
  `…/access-tokens/online-access-tokens`.
- `[Official fact]` / `[Official limitation]` **Offline tokens**: "meant for
  service-to-service requests where no user interaction is involved." **Non-expiring** ones
  "grant permanent access to a shop's data and can only be revoked through app uninstallation
  or secret revocation." **Expiring** ones = **1-hour access token** (`expires_in: 3600`) +
  **90-day refresh token** (`refresh_token_expires_in: 7776000`); each refresh returns a new
  access **and** refresh token (fresh 90-day expiry); "Shopify invalidates the previous
  refresh token after use"; on refresh-token expiry "the app user needs to relaunch the app."
  — `…/access-tokens/offline-access-tokens`.
- `[Official fact — recorded Part 1]` **Admin-created custom app tokens are "installed upon
  generation in the Shopify admin"** — recorded in the Part 1 refresh (cited
  `…/authentication-authorization` + `/access-tokens`). Part 2's re-fetch of the
  access-tokens **index** did not independently restate that exact sentence, so its **exact
  current dev-doc location** is a **minor** `[Open question]`; the fact itself stands from
  Part 1.
- `[Official fact — Sprint B]` **Least-privilege** is official: apps "must request only the
  minimum data necessary" (`…/usage/access-scopes`, Sprint B). Part 2 did not re-fetch that
  page; the fact remains valid.
- `[Open question]` A single cross-model **rotation/revocation policy** statement was not
  located on the six fetched pages (online logout-revocation and offline
  uninstall/secret-revocation are each stated separately).

**Adversarial cross-verify:** re-fetched five pages; all token lifetimes/rotation quotes
confirmed verbatim; the two genuinely-open items (index-page "token on generation" wording;
explicit least-privilege on the fetched set) correctly left open; status upheld.

**Architecture implication (input, not decision):** an unattended connector maps naturally to
the **offline** token model; **non-expiring vs expiring-with-rotation** is a real setup /
credential-storage / refresh-scheduling trade-off, and **admin-created custom app vs OAuth
app** changes the setup-wizard shape. **OAuth-vs-token is NOT decided here.** **[Not decided].**

### RQ-003-1 — Odoo Online feasibility for a custom connector module

**Status: Partially resolved (core question resolved).**

- `[Official limitation]` **"Odoo Online is incompatible with custom modules or modules from
  the Odoo Apps Store."** — `odoo.com/documentation/19.0/administration/odoo_online.html`
  (confirmed verbatim on the rendered HTML **and** the official raw 19.0 RST,
  `…/content/administration/odoo_online.rst`). Context: Odoo Online "can be used for
  long-term production or to thoroughly test Odoo, including customizations that do not
  require custom code." **A connector module is custom code → it cannot run on Odoo Online.**
- `[Official fact]` **Odoo.sh**: "The installed modules are those included in the branch. You
  can change this list of modules to install in the project settings." + "When you push a new
  commit to this branch, the production server is updated with the revised code and
  restarted." Staging: "Scheduled actions … disabled" ("To test them, trigger them manually
  or re-enable them."); dev branches: "scheduled actions are not triggered as long as the
  database is not in use." — `…/content/administration/odoo_sh/getting_started/branches.rst`.
- `[Official fact]` **On-premise**: "The multi-processing server is opt-in. It is selected by
  setting the `--workers` option to a non-null integer"; a separate cron process is required
  ("must be configured to only process crons and not HTTP requests using the `--no-http` …
  or `http_enable = False`"); `max_cron_threads` appears in the config sample; HTTPS via
  reverse proxy + Odoo "proxy mode." — `…/content/administration/on_premise/deploy.rst`.
- `[Open question]` Odoo Online's **outbound-HTTPS / custom-controller / `server_wide_modules`
  / extra-worker / jobrunner** capabilities are **not literally addressed** (moot because
  custom modules are excluded, but not stated). Odoo.sh `server_wide_modules`/jobrunner
  support and on-prem `server_wide_modules` are **not** in the fetched pages. Do **not**
  assume from experience.

**Adversarial cross-verify:** re-fetched Odoo-Online RST, deploy.rst, Odoo.sh branches RST;
the incompatibility statement + all Odoo.sh/on-prem quotes confirmed verbatim; the moot Odoo
Online sub-capabilities correctly left open; status upheld.

**Architecture implication (input, not decision):** the connector's custom module **cannot
target Odoo Online**; the substrate lives on **Odoo.sh or on-premise**. This **removes** the
"must support Odoo Online" constraint that Part 1 left open — but the **substrate choice**
(cron-queue vs `queue_job` vs external worker) is still a real decision on Odoo.sh/on-prem,
where jobrunner/`server_wide_modules` support is not yet officially confirmed. **[Not decided].**

### RQ-003-2 — Official Odoo core async-queue availability

**Status: Partially resolved (strengthened inference).**

- `[Official source-code fact]` In `odoo/addons/base/models/ir_cron.py` (19.0) the only
  cron/async models are **`IrCron`**, **`IrCronTrigger`**, **`IrCronProgress`**;
  `ir.cron` is the documented scheduled/deferred-execution primitive (poll-based, minute
  precision). — `github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py`.
- `[Official source-code fact]` The symbol **`with_delay`** (the OCA `queue_job` dispatch
  API) does **not** appear in `ir_cron.py` **or** in `odoo/orm/models.py` (19.0). —
  `github.com/odoo/odoo/blob/19.0/odoo/orm/models.py`.
- `[Official fact]` (Part 1/Sprint B, re-confirmed) Odoo 19.0 **docs** document only
  `ir.cron` for background/scheduled work.
- `[Inference]` No general-purpose async job queue (named jobs, priorities, retry/backoff,
  dependency graphs) was found in the reviewed official docs/source. **This remains an
  inference, not an official fact — a negative cannot be proven from one file set.**
- `[Open question]` A whole-repo 19.0 confirmation that **no** internal queue/message-bus
  exists anywhere in core (Community/Enterprise) would be needed to promote this beyond
  inference. OCA `queue_job` remains **community, not core**.

**Architecture implication (input, not decision):** background sync on stock Odoo 19 rests on
`ir.cron`; a true async queue is a **community dependency** (`queue_job`), which — per
RQ-003-1 — **cannot run on Odoo Online** and needs its own jobrunner on Odoo.sh/on-prem. The
substrate is a genuine architecture decision with a community-dependency dimension. **[Not
decided].**

### RQ-003-3 — `ir.cron` operational signatures + failure model

**Status: Resolved (from official 19.0 source).**

Source: `github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py` (official
`odoo/odoo` 19.0). `[Official source-code fact]` for each:

- **`_trigger(self, at: datetime | Iterable[datetime] | None = None)`** — docstring:
  "Schedule a cron job to be executed soon independently of its `nextcall` field value. By
  default … the next time the cron worker wakes up, but the optional `at` argument may be
  given to delay … precision down to 1 minute." Delegates to `_trigger_list` (the
  "recommended method for overrides").
- **`method_direct_trigger(self)`** — "Run the CRON job in the current (HTTP) thread. The
  job is still ran as it would be by the scheduler: a new cursor is used for the execution of
  the job." (the sanctioned way to run a cron synchronously, e.g. in tests / a "run now"
  action).
- **`_commit_progress(self, processed: int = 0, *, remaining: int | None = None,
  deactivate: bool = False) -> float`** — "Commit and log progress for the batch from a cron
  function… If called from outside the cron job, the progress function call will just
  commit. :return: remaining time (seconds) for the cron run." Backed by the
  `ir.cron.progress` model (`done`/`remaining`); returns `float('inf')` when not inside a
  cron; a `deactivate` flag deactivates the cron after the run. *(This sharpens the Part 1
  paraphrase: the API takes a `processed` count and optional `remaining`, and exposes a
  `deactivate` flag.)*
- **Failure/deactivation constants** (module level): `CONSECUTIVE_TIMEOUT_FOR_FAILURE = 3`,
  `MIN_FAILURE_COUNT_BEFORE_DEACTIVATION = 5`, `MIN_DELTA_BEFORE_DEACTIVATION =
  timedelta(days=7)`, `MAX_FAIL_TIME = timedelta(hours=5)`. Field
  `failure_count = fields.Integer(default=0, help="The number of consecutive failures of
  this job. It is automatically reset on success.")`. In `_update_failure_count`, the cron is
  deactivated (`active = False`, counters reset, DB admin notified) **only when BOTH**
  `failure_count >= MIN_FAILURE_COUNT_BEFORE_DEACTIVATION (5)` **AND**
  `first_failure_date + MIN_DELTA_BEFORE_DEACTIVATION (7 days) < now`; a timed-out run counts
  toward failure at `timed_out_counter >= CONSECUTIVE_TIMEOUT_FOR_FAILURE (3)`. **This
  confirms the Part 1 doc-level model (3 → skip/failed; 5-over-7-days → deactivate+notify) at
  the source level.**
- `[Official fact]` (re-confirmed, doc) `--max-cron-threads` default 2 (`cli.rst`); Odoo.sh
  **staging crons disabled** (neutralized duplicate) — re-confirmed via the RQ-003-1 Odoo.sh
  branches fetch ("Scheduled actions … disabled").

**Architecture implication (input, not decision):** the connector's orchestration must own
**per-record retry/backoff + savepoint isolation** (cron's own deactivation is coarse:
5-failures-over-7-days), use `_trigger`/batched work/`_commit_progress` for near-term
dispatch + progress, and must **not** rely on cron-level retries. **[Not decided].**

### RQ-005-1 — Shopify GID permanence / deleted-recreated records

**Status: Partially resolved (permanence confirmed *not asserted*).**

- `[Official fact]` "A global ID is an application-wide uniform resource identifier (URI)
  that uniquely identifies an object." + "You can use a global ID to retrieve a specific
  Shopify object of any type." — `shopify.dev/docs/api/usage/gids`.
- `[Official fact]` Node interface: "An object with an ID field to support global
  identification, in accordance with the Relay specification." — `id` field described as **"A
  globally-unique ID."** — `…/admin-graphql/latest/interfaces/Node`,
  `…/admin-graphql/latest/objects/Product`.
- `[Open question]` **No** official page (gids, Node, Product, webhooks) asserts GID
  **permanence, stability over time, or non-reuse**, nor describes **deleted-then-recreated**
  behaviour. **Uniqueness is the only stated property.** GID permanence must **not** be
  over-read from "uniquely identifies."

**Adversarial cross-verify:** re-fetched all four pages; uniqueness quotes confirmed;
permanence/reuse/deletion returned "not mentioned/addressed" on every page; status upheld.

**Architecture implication (input, not decision):** the binding model must **not assume GID
permanence**; deleted/recreated-record handling (mark stale, do not silently recreate/hijack)
is a **design requirement**, not a platform guarantee. Confirms Part 1. **[Not decided].**

### RQ-005-2 — General mutation idempotency beyond `@idempotent`

**Status: Partially resolved (materially narrowed; TTL + list resolved).**

- `[Official fact]` (new in Part 2) **"Shopify tracks idempotency keys for 24 hours from the
  original request."** — `shopify.dev/docs/api/usage/implementing-idempotency`. **Resolves
  the Part 1 "server dedup TTL unstated" open question → 24 hours.**
- `[Official limitation]` The mechanism is **not general**: "… only applies to mutations that
  support the `@idempotent` directive." The supporting set is a **fixed list of 17
  mutations**: `inventoryActivate, inventoryAdjustQuantities, inventoryMoveQuantities,
  inventorySetOnHandQuantities, inventorySetQuantities, inventorySetScheduledChanges,
  inventoryShipmentAddItems, inventoryShipmentCreate, inventoryShipmentCreateInTransit,
  inventoryShipmentReceive, inventoryTransferCreate, inventoryTransferCreateAsReadyToShip,
  inventoryTransferDuplicate, inventoryTransferSetItems, locationActivate, locationDeactivate,
  refundCreate`. — `…/usage/implementing-idempotency`. "Mutations that accept an
  `@idempotent` directive specify that they do in their descriptions." — `…/usage/idempotent-requests`.
- `[Official fact]` Concurrency: "When multiple duplicate requests arrive in quick succession
  while the first request is still processing, Shopify returns `IDEMPOTENCY_CONCURRENT_REQUEST`
  to subsequent requests instead of processing them." — `…/usage/implementing-idempotency`.
- `[Official fact]` `@idempotent` timeline (re-confirmed): `inventorySetQuantities` — "As of
  2026-01, this mutation supports an optional idempotency key using the `@idempotent`
  directive. As of 2026-04, the idempotency key is required…"; `inventoryAdjustQuantities`
  uses the same wording with "As of version 2026-01 / 2026-04." *(Two quote-transcription
  fixes were applied here vs the first-pass draft: `inventorySetQuantities` omits the word
  "version"; the bulk page reads "These errors might be intermittent," not "timeouts.")*
- `[Official fact]` Key definition: "An idempotency key is a unique string identifier
  generated by your app." + "Each distinct request should have its own unique idempotency
  key." (UUID recommended). — `…/usage/idempotent-requests`, `…/implementing-idempotency`.
- `[Official fact]` Webhook dedup is a **separate** mechanism: "Verify HMAC signatures and
  ignore duplicate deliveries using `X-Shopify-Webhook-Id`." — `…/webhooks/best-practices`.
- `[Open question]` The key's **uniqueness scope** (per-shop / per-app / global) is **not
  defined**. **Bulk-operation idempotency** is **not stated** (the bulk page only offers
  "These errors might be intermittent, so you can try submitting the query again." / "You can
  retry canceled bulk operations by submitting the query again."). **No general/all-mutation
  idempotency and no `clientMutationId`** exist (confirmed absent).

**Adversarial cross-verify:** re-fetched the idempotency + mutation + webhook + bulk pages;
24h TTL, 17-mutation list, concurrency error, and the absence of `clientMutationId`/general
mechanism all confirmed; two quote fixes flagged and applied; status upheld.

**Architecture implication (input, not decision):** Shopify gives **per-mutation** idempotency
(17 mutations, 24h dedup) + webhook dedup; **everything else** — outbound writes outside those
17 mutations, cross-request dedup beyond 24h, ordering, bulk-op safety — is
**connector-designed** (feeds AR-005 binding keys and AR-006 retry/idempotency taxonomy).
**[Not decided].**

### RQ-005-3 — `ir.model.data` fields / uniqueness / binding suitability

**Status: Resolved (from official 19.0 source).**

Source: `github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_model.py`, class
`IrModelData` (official `odoo/odoo` 19.0). `[Official source-code fact]`:

- **Purpose (docstring):** "Holds external identifier keys for records in the database. This
  has two main uses: * allows easy data integration with third-party systems, making
  import/export/sync of data possible, as records can be uniquely identified across multiple
  systems * allows tracking the origin of data installed by Odoo modules themselves…" — so
  it is **explicitly designed for both** third-party data integration/sync **and**
  module-data-origin tracking (not module-data-only).
- **Fields:** `name` (Char "External Identifier", required), `complete_name` (compute),
  `model` (Char, required), `module` (Char, `default=''`, required), `res_id`
  (`Many2oneReference`, `model_field='model'`), `noupdate` (Boolean, default False),
  `reference` (Char, compute, `store=False`). Model attrs: `_order = 'module, model, name'`,
  **`_allow_sudo_commands = False`**.
- **Constraints (19.0 declarative form):**
  `_name_nospaces = models.Constraint("CHECK(name NOT LIKE '% %')", …)`;
  **`_module_name_uniq_index = models.UniqueIndex('(module, name)')`** — the **`(module,
  name)` uniqueness** Part 1 flagged is **confirmed** (a unique index);
  `_model_res_id_index = models.Index('(model, res_id)')` accelerates reverse lookups.
- **Lookup:** `_xmlid_lookup` is `ormcache`'d and resolves `SELECT model, res_id FROM
  ir_model_data WHERE module=%s AND name=%s`.

**Suitability observations (facts, not a decision):** `ir.model.data` **does** provide
`(module, name)` uniqueness and a **db-id-independent** handle, but it has **no per-store /
store-dimension column**, **no binding-status / audit fields** (who/when matched, source
strategy), and its `module`/`noupdate` semantics are tied to **module data lifecycle**
(records created by module install/update; `noupdate` governs update-time overwrite).
`_allow_sudo_commands = False` also constrains how it can be written.

**Per the RB-14 Part 2 prompt, this does not decide to use or reject `ir.model.data`.** It may
become an **avoid-candidate** for a runtime binding store, but any **formal rejection** needs
ChatGPT approval (`CLAUDE.md` §10) and is **not** recorded here. **[Not decided].**

### RQ-005-4 — `sudo()` bypass of access rights / record rules

**Status: Resolved (from official 19.0 ORM source).**

Source: `github.com/odoo/odoo/blob/19.0/odoo/orm/models.py`, `def sudo` (official `odoo/odoo`
19.0). `[Official source-code fact]`:

- Signature: `def sudo(self, flag: bool = True) -> Self:`. Docstring: "Return a new version of
  this recordset with superuser mode enabled or disabled, depending on `flag`. The superuser
  mode does not change the current user, and **simply bypasses access rights checks.**"
- `.. warning::` "Using `sudo` could cause **data access to cross the boundaries of record
  rules**, possibly mixing records that are meant to be isolated (e.g. records from different
  companies in multi-company environments). It may lead to un-intuitive results in methods
  which select one record among many…"
- Body: `sudo()` sets superuser mode via `with_env(self.env(su=flag))`; it **does not** change
  `self.env.user`.

**This resolves the Part 1 open question** ("`sudo()` bypass not literally on `security.rst`"):
the bypass of **both access rights and record rules** is stated **literally in the ORM source
docstring/warning** — `[Official source-code fact]`, no longer an inference. The
multi-company/isolation risk is named explicitly.

- `[Open question]` (minor) The precise interaction of **field-level `groups`** with
  superuser read/write (the Part 1 `security.rst` TODO) is not fully pinned; the field-level
  `groups` behaviour for normal users (removed from views/`fields_get`; explicit access
  raises) is the Sprint B fact.

**Architecture implication (input, not decision):** any credential handling or per-store
isolation design must treat `sudo()` as a **deliberate, audited** bypass — under `sudo()`,
**record-rule (incl. per-company/per-store) isolation is defeated**, so it must be scoped
narrowly and never used to route around store isolation. Feeds AR-002 (credential security)
and AR-005 (per-store binding isolation). **[Not decided].**

---

## Facts changed since RB-14 Part 1

1. **Server-side idempotency-key dedup TTL is now known: 24 hours** (Part 1: "server dedup
   TTL unstated" open question). `[Official fact]` — `…/usage/implementing-idempotency`.
2. **`@idempotent` scope is an explicit fixed list of 17 mutations** (Part 1 knew only the
   two inventory mutations + `refundCreate`); a dedicated idempotency doc page now exists.
   `[Official fact]`/`[Official limitation]`.
3. **Odoo Online is officially incompatible with custom modules** (Part 1: "Odoo Online
   feasibility open"). The connector's substrate is **Odoo.sh / on-premise**, not Odoo
   Online. `[Official limitation]`.
4. **`ir.model.data` `(module, name)` uniqueness is confirmed** as `UniqueIndex('(module,
   name)')`, with the full field list (Part 1: `[Open question]` "verify against 19.0
   source"). `[Official source-code fact]`.
5. **`sudo()` bypass of access rights + record rules is now literally sourced** from the ORM
   docstring/warning (Part 1: "not literally on `security.rst`" → was downgraded to
   re-verify). `[Official source-code fact]`.
6. **`ir.cron` signatures/constants pinned to source** — `_trigger(at=None)`,
   `_commit_progress(processed=0, *, remaining=None, deactivate=False) -> float`,
   `CONSECUTIVE_TIMEOUT_FOR_FAILURE=3`, `MIN_FAILURE_COUNT_BEFORE_DEACTIVATION=5`,
   `MIN_DELTA_BEFORE_DEACTIVATION=7 days` (Part 1: `_trigger` signature was an open
   `automethod` item). `[Official source-code fact]`.
7. **Custom-app REST is not categorically forbidden** — a changelog narrowly permits REST
   product APIs for custom apps <100 variants and states GraphQL is the "only supported …
   long term" with **no REST EOL date** (sharpens Part 1's open custom-app scope, without
   resolving the blanket question). `[Official fact]`/`[Official limitation]`.
8. **Protected-customer-data access matrix pinned**: custom/Admin-created custom apps
   **"Always available"** vs public **"Requires review"** (Part 1 had the App-Store gate but
   not the matrix). `[Official fact]`.

## Facts unchanged since RB-14 Part 1 (re-confirmed 2026-07-01)

- **GID permanence is NOT asserted** — only "uniquely identifies an object" / "globally-unique
  ID" (RQ-005-1).
- **GraphQL-only mandate is scoped to "new public apps"**; REST "legacy as of 2024-10-01";
  no REST EOL date (RQ-002-1).
- **Three mandatory compliance webhooks are App-Store-scoped** ("apps listed on the Shopify
  App Store"); custom-app obligation not stated (RQ-002-2).
- **Two token-acquisition paths** (token exchange / authorization-code grant); online 24h/
  logout; offline non-expiring vs expiring (1h + 90-day refresh) (RQ-002-3).
- **Odoo core documents/ships only `ir.cron`** as the async primitive; a general async job
  queue **not found** (stays an inference) (RQ-003-2).
- **Odoo.sh staging crons disabled**; **`--max-cron-threads` default 2** (RQ-003-3).

## Open questions still blocking a confident decision

- **AR-002:** the **blanket** custom/private GraphQL-mandate scope + any **REST EOL date**;
  whether **custom apps must implement** the compliance webhooks and whether **Level 1/2
  obligations bind** custom deployments; the exact current dev-doc statement of "admin-created
  token installed on generation."
- **AR-003:** whether **Odoo.sh** (and on-prem) support **`server_wide_modules` / an external
  jobrunner** (needed for `queue_job`); whole-repo proof that **no** async queue exists in
  Odoo core; MVP-scale throughput under `--max-cron-threads=2`.
- **AR-005:** `@idempotent` **key-uniqueness scope** (per-shop/app/global); **bulk-operation
  idempotency**; **GID permanence/non-reuse**; the **per-store binding data model** decision
  itself (facts now sufficient to *frame*, not to *decide*).

## Questions no longer blocking a decision (resolved as inputs)

- **`ir.cron` mechanics** (signatures, batching, failure/deactivation) — decision-ready
  inputs (RQ-003-3).
- **`ir.model.data` shape + `(module, name)` uniqueness** — known; a reuse-vs-dedicated
  binding judgement can now proceed on facts (RQ-005-3; not decided).
- **`sudo()` bypass semantics** — known and sourced; security design can rely on it
  (RQ-005-4).
- **Odoo-Online-as-a-required-substrate** — removed: the custom module cannot run there, so
  AR-003 no longer needs to keep Odoo Online in scope for the substrate (RQ-003-1).
- **Idempotency TTL + `@idempotent` mutation set** — known (24h; 17 mutations) (RQ-005-2).

## No architecture decisions made

This resolution pass **decides nothing**. It dates and classifies official-doc and
official-source-code facts, resolves/narrows the high-risk questions **only where official
evidence supports it**, and keeps the rest open. **AR-002 / AR-003 / AR-005 remain [Not
decided] / Evidence pending**; **no** REST/GraphQL, distribution, OAuth/token, queue-framework,
binding/data-model, or module-boundary choice is made; DEC-003 and MVP scope are unchanged;
implementation stays blocked (`CLAUDE.md` §4–§5; RB-14). Narrowing routes to
[`rb14-decision-candidate-brief.md`](./rb14-decision-candidate-brief.md) and the AR framing
docs as **inputs**, labelled `[Recommendation]` / `[Decision candidate]`.
