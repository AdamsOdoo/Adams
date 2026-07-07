# Shopify Admin API Token-Acquisition Research

> **Research-phase document. No architecture decision or implementation choice is
> made here.** This is a factual inventory of what official Shopify documentation
> currently says about Admin API access-token acquisition, gathered to unblock the
> Task 003 validation follow-up (VAL-B2) and to inform
> [`../03-architecture/shopify-token-acquisition-options.md`](../03-architecture/shopify-token-acquisition-options.md)
> and
> [`../04-decisions/shopify-token-acquisition-decision-brief.md`](../04-decisions/shopify-token-acquisition-decision-brief.md).
> Per `CLAUDE.md` §8, every statement below is labelled **[Fact]** (verifiable on an
> official page, cited), **[Inference]** (our deduction from facts), or **[Open
> question]** (unverified/unknown). No **Decision** is recorded in this file.

## Status

- **Sprint:** Shopify Admin API token-acquisition research (session dated
  **2026-07-07**).
- **Trigger:** PR #107 recorded Task 003 manual validation as partially complete —
  VAL-B2 (the valid-token positive-connection test) is **BLOCKED** because no real
  Shopify Admin API access token compatible with the connector's current
  `token_variant='offline_custom_app'` credential shape was obtainable from the
  Shopify Dev Dashboard app used during that session.
- **Method:** Every claim below was independently fetched **live on 2026-07-07**
  from official Shopify sources (primarily `shopify.dev`, plus `help.shopify.com`
  and, where flagged, `changelog.shopify.com`), using a fan-out of nine
  topic-scoped research passes followed by an independent, adversarial re-fetch
  verification pass per topic (a second, skeptical reviewer re-fetched every
  cited URL and checked the quote/claim against the live page). Corrections
  surfaced by verification (misattributed quotes, paraphrases presented too
  strongly as verbatim text, quote-splicing across two pages) have been applied
  below — the facts stated here reflect the **corrected, re-verified** wording,
  not the first-pass draft.
- **This document does not rely on training-data memory of Shopify's platform.**
  Where official docs were silent, ambiguous, or contradictory, this is stated
  explicitly as an open question rather than filled in from assumption.

## How to read the citations

Each fact cites the exact URL, notes whether the text is a **direct quote** or a
**paraphrase**, and records **access status** (Accessible / Partial / Blocked) as
of **2026-07-07**. `shopify.dev` is Shopify's primary developer-documentation
domain (Tier 1). `help.shopify.com` is Shopify's merchant-facing Help Center
(Tier 1, official, but written for merchants rather than developers).
`changelog.shopify.com` is flagged separately below — it is Shopify's own
product-changelog site (a first-party, official source) but is a **distinct
domain** from `shopify.dev`, and in one case supplies a fact (the exact
custom-app-creation cutoff date) that does not appear on the `shopify.dev` page
it corroborates.

---

## 1. Source inventory

| # | Source | URL | Access status | Access date |
| --- | --- | --- | --- | --- |
| 1 | Access tokens overview | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens | Accessible | 2026-07-07 |
| 2 | Authentication/authorization overview | https://shopify.dev/docs/apps/build/authentication-authorization | Accessible | 2026-07-07 |
| 3 | Token exchange | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/token-exchange | Accessible | 2026-07-07 |
| 4 | Authorization code grant | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant | Accessible | 2026-07-07 |
| 5 | Client credentials grant | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant | Accessible | 2026-07-07 |
| 6 | Generate access tokens for custom apps in the Shopify admin | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin | Accessible | 2026-07-07 |
| 7 | Offline access tokens | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/offline-access-tokens | Accessible | 2026-07-07 |
| 8 | Online access tokens | https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/online-access-tokens | Accessible | 2026-07-07 |
| 9 | Client secrets | https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets | Accessible | 2026-07-07 |
| 10 | Rotate/revoke client credentials | https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets/rotate-revoke-client-credentials | Accessible | 2026-07-07 |
| 11 | App installation / Shopify managed installation | https://shopify.dev/docs/apps/build/authentication-authorization/app-installation | Accessible | 2026-07-07 |
| 12 | Uninstall app (API request) | https://shopify.dev/docs/apps/build/authentication-authorization/app-installation/uninstall-app-api-request | Accessible | 2026-07-07 |
| 13 | Dev Dashboard overview | https://shopify.dev/docs/apps/build/dev-dashboard | Accessible | 2026-07-07 |
| 14 | Create apps using the Dev Dashboard | https://shopify.dev/docs/apps/build/dev-dashboard/create-apps-using-dev-dashboard | Accessible | 2026-07-07 |
| 15 | Get API access tokens (Dev Dashboard) | https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens | Accessible | 2026-07-07 |
| 16 | Migrate from Partners (Dev Dashboard) | https://shopify.dev/docs/apps/build/dev-dashboard/migrate-from-partners | Accessible | 2026-07-07 |
| 17 | Shopify CLI for apps | https://shopify.dev/docs/apps/build/cli-for-apps | Accessible | 2026-07-07 |
| 18 | `shopify app dev` reference | https://shopify.dev/docs/api/shopify-cli/app/app-dev | Accessible | 2026-07-07 |
| 19 | `shopify app deploy` reference | https://shopify.dev/docs/api/shopify-cli/app/app-deploy | Accessible | 2026-07-07 |
| 20 | Scaffold an app (tutorial) | https://shopify.dev/docs/apps/build/scaffold-app | Accessible | 2026-07-07 |
| 21 | App distribution overview | https://shopify.dev/docs/apps/launch/distribution | Accessible | 2026-07-07 |
| 22 | Select a distribution method | https://shopify.dev/docs/apps/launch/distribution/select-distribution-method | Accessible | 2026-07-07 |
| 23 | Protected customer data | https://shopify.dev/docs/apps/launch/protected-customer-data | Accessible | 2026-07-07 |
| 24 | Shopify App Store requirements | https://shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements | Accessible | 2026-07-07 |
| 25 | Integrating with Shopify (standalone/ERP note) | https://shopify.dev/docs/apps/build/integrating-with-shopify | Accessible | 2026-07-07 |
| 26 | Development stores (API docs) | https://shopify.dev/docs/api/development-stores/index | Accessible | 2026-07-07 |
| 27 | Development stores (apps/tools, legacy path) | https://shopify.dev/docs/apps/tools/development-stores | Accessible (content overlaps #26 — flagged, see §8) | 2026-07-07 |
| 28 | Generated test data | https://shopify.dev/docs/api/development-stores/generated-test-data | Accessible | 2026-07-07 |
| 29 | GraphQL Admin API rate limits | https://shopify.dev/docs/api/usage/limits | Accessible (no dev-store-specific content — negative result) | 2026-07-07 |
| 30 | Token-length changelog (`shpat_`/`shpca_` prefixes) | https://shopify.dev/changelog/length-of-the-shopify-access-token-is-increasing | Accessible | 2026-07-07 |
| 31 | App-secret-key-length changelog (`shpss_` prefix) | https://shopify.dev/changelog/app-secret-key-length-has-increased | Accessible | 2026-07-07 |
| 32 | Expiring offline tokens introduced | https://shopify.dev/changelog/offline-access-tokens-now-support-expiry-and-refresh | Accessible | 2026-07-07 |
| 33 | Expiring offline tokens mandatory — new public apps | https://shopify.dev/changelog/expiring-offline-access-tokens-required-for-public-apps-april-1-2026 | Accessible | 2026-07-07 |
| 34 | Expiring offline tokens mandatory — all public apps | https://shopify.dev/changelog/expiring-offline-access-tokens-required-for-all-public-apps-as-of-january-1-2027 | Accessible | 2026-07-07 |
| 35 | Legacy custom-app creation cutoff (product changelog) | https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026 | Accessible — **different domain** (`changelog.shopify.com`), flagged per citation policy; still an official first-party Shopify source | 2026-07-07 |
| 36 | Custom apps (Help Center) | https://help.shopify.com/en/manual/apps/app-types/custom-apps | Accessible | 2026-07-07 |
| 37 | Install/set up apps (Help Center) | https://help.shopify.com/en/manual/apps/install-setup-apps | Accessible | 2026-07-07 |
| 38 | Uninstalling apps (Help Center) | https://help.shopify.com/en/manual/apps/uninstalling-apps | Accessible (Cloudflare bot-check blocked a raw-`curl` cross-check; confirmed via two independent fetches instead) | 2026-07-07 |
| 39 | Development stores (Partner-facing, Help Center) | https://help.shopify.com/en/partners/dashboard/managing-stores/development-stores | Accessible | 2026-07-07 |

No source in this inventory returned a hard block (401/403 at the fetch layer) except transient Cloudflare bot-challenge pages on `help.shopify.com` for two URLs, which were resolved via an alternate fetch path (noted in the table). `https://shopify.dev/docs/apps/tools/dev-dashboard` and `https://shopify.dev/docs/apps/launch/deployment/app-distribution` — both guessed from older documentation-path conventions — returned live HTTP 404s and are **not** current URLs; the correct current paths are rows 13 and 21 above respectively.

---

## 2. What Shopify currently supports for Admin API access tokens

**[Fact]** An Admin API access token authenticates requests via the
`X-Shopify-Access-Token` HTTP header. (Source 3)

**[Fact]** Shopify's docs describe **four** separately-documented token-acquisition
mechanisms, spread across four different pages — there is no single page listing
all four together:

1. **Token exchange** — the recommended method for apps rendered/embedded in the
   Shopify admin; converts an App-Bridge session token into an access token.
   (Source 1, 3)
2. **Authorization code grant** — the classic OAuth redirect flow, for standalone
   apps and legacy apps not using Shopify-managed installation. (Source 1, 4)
3. **Client credentials grant** — an OAuth 2.0 machine-to-machine exchange of an
   app's Client ID + Client Secret directly with a store, with no end-user
   interaction; **explicitly restricted** to "apps developed by your own
   organization and installed in stores that you own" — "Public or custom apps
   must use token exchange or authorization code grant" instead. (Source 5, direct
   quote)
4. **Admin-generated (legacy)** — a token generated and installed directly inside
   the Shopify admin when creating/installing a custom app the old way. (Source 6)

**[Fact]** The top-level access-tokens overview page frames the platform as
offering only "two ways for apps to acquire an access token: token exchange and
authorization code grant" (Source 1, direct quote) — this sentence does not
mention client credentials grant or the admin-generated path at all; those two
live on separate, sibling pages. There is no single official page presenting all
four mechanisms as one unified list.

**[Fact]** Token/secret prefixes (Sources 30, 31): `shpat_` denotes a **public
app** access token; `shpca_` denotes a **custom app** access token (per the
original 2020 length-increase changelog). `shpss_` is **not** an access-token
prefix — it is the prefix for an app's **client secret** (Source 31). `shprt_`
denotes a **refresh token** issued alongside an expiring offline access token
(Source 4).

**[Open question]** Whether `shpca_` is still actually issued/documented as
current in 2026 could not be independently reconfirmed on any live page fetched
this session — the only source for it is the original 2020 changelog (Source
30, still accessible); every current (2026) page that illustrates an example
Admin API token uses the generic `shpat_` form and does not mention `shpca_` at
all. This is inconclusive — it may reflect doc simplification rather than
deprecation — and should not be asserted either way.

**[Fact]** Online access tokens are scoped to a specific staff user and expire
"either when the user logs out or after 24 hours" (Source 8, direct quote),
whichever comes first; after expiry, Shopify returns HTTP 401. No refresh-token
mechanism exists for online tokens.

---

## 3. Custom apps: is the old admin-created token path still available?

**This is the central factual finding of this research, and it directly explains
why VAL-B2 was blocked.**

**[Fact, independently re-confirmed verbatim across every one of nine separate
research passes today]**

> "You can no longer create new custom apps in the Shopify admin. Existing
> admin-created custom apps continue to work. To create a new custom app, use
> the Dev Dashboard or Shopify CLI."
> — Source 6 (direct quote)

**[Fact]** The exact cutoff date is **January 1, 2026** — stated on Shopify's
official product changelog (Source 35, flagged as a distinct domain from
`shopify.dev`, but still an official first-party source):

> "Starting January 1, 2026, you can no longer create new custom apps in the
> Shopify admin. This affects merchants and developers who create custom apps
> directly from the admin. Existing custom apps aren't affected and will
> continue to work. To create a new custom app after this date, use the Dev
> Dashboard to build the app, then install it on your store."
> — Source 35 (direct quote)

The `shopify.dev` page itself (Source 6) does **not** state this exact date —
searching its live text for "2026" and "January" found no match beyond unrelated
API-version strings. The date is corroborated independently, in substance, by
Shopify's Help Center:

> "If you have legacy custom apps created before January 1, 2026, you can manage
> them from your Shopify admin. ... You create and manage custom apps using the
> Dev Dashboard."
> — Source 36 (direct quote)

**Answer to "is the old path available for newly created apps, existing apps, or
both":** **[Fact]** the admin-created custom-app token path is available **only
for apps that already existed before January 1, 2026** ("legacy custom apps").
It is **not** available for any app created after that date — a merchant signing
up today cannot obtain a token this way. It remains fully functional for
pre-existing legacy apps, with one caveat below.

**[Fact]** Admin-created custom app tokens **cannot be rotated in place**:

> "You can't rotate API credentials for custom apps created in the Shopify
> admin. You need to delete the app and create a new custom app which has new
> API credentials. To create new access tokens for a custom app that was
> created in the Shopify admin, you need to uninstall and reinstall your app.
> Your app's requests and webhooks are disrupted until you update your app's
> code with the new API credentials or access token."
> — Source 6 (direct quote)

Practically: a legacy admin-created custom app's token can only be replaced by
(a) deleting the app and creating an entirely new custom app — which, per the
Jan-1-2026 cutoff above, is **no longer possible** for an admin-created app — or
(b) uninstalling and reinstalling the *same* app, which disrupts the connection
until the new token is re-entered.

**[Open question]** The historical "reveal token once" / "only the last 4
characters shown afterward" behavior some third-party sources describe for the
admin-created custom-app token UI was searched for exhaustively (raw-HTML greps
for "reveal", "once", "last 4/four characters", "hidden", "masked" across every
one of nine independent fetches of Source 6 today) and was **not found on any
live official `shopify.dev` or `help.shopify.com` page**. It appears only in
third-party blogs and Shopify Community forum posts, which this project's
citation policy excludes as authoritative. This must be logged as **unverified**
— neither confirmed nor denied as current product behavior — not asserted
either way.

**[Fact]** "Private apps" are **not** a current Shopify app type. They were
deprecated in January 2022 and all were automatically migrated to custom apps by
January 20, 2023 (Source 21, direct quote). The connector's own documentation
should not use the term "private app" going forward — "custom app" is the
correct, current term.

---

## 4. Dev Dashboard / CLI app token acquisition path

**[Fact]** New custom apps (post-2026-01-01) are created via the **Dev
Dashboard** or **Shopify CLI** (Source 6). The Dev Dashboard is positioned by
Shopify itself as best "for quick integrations, such as connecting an existing
system to Shopify" (Source 14, direct quote) — language that directly describes
this connector's use case.

**[Fact]** Shopify's own worked tutorial for "building apps for your own store"
via the Dev Dashboard (Source 14, 15) demonstrates **only** the client
credentials grant:

> "This tutorial demonstrates how to use the client credentials grant—the
> simplest authentication option for merchants building apps for their store.
> ... With a client credentials grant, you won't see a token in the Shopify
> admin. Instead, you request tokens programmatically when you need them."
> — Source 15 (direct quote)

Mechanics: copy the app's Client ID + Client Secret from the Dev Dashboard →
Settings, then `POST https://{shop}.myshopify.com/admin/oauth/access_token` with
`client_id`, `client_secret`, `grant_type=client_credentials`. The resulting
token is valid for exactly **86399 seconds (24 hours)** and must be refreshed by
repeating the same request — no token is ever visible in the Shopify admin for
this flow (Source 5, 15).

**[Fact]** The client credentials grant is explicitly restricted by ownership,
not by creation tool:

> "Client credentials is only available for apps developed by your own
> organization and installed in stores that you own. ... The client credentials
> grant only works when the app and the store belong to the same Shopify
> organization. 'Same organization' means both appear under the same org in the
> Dev Dashboard. Owning a store or having it installed doesn't automatically
> place it in your org."
> — Source 5, 15 (direct quote, two sources)

Attempting it across organizations returns a specific OAuth error:
`shop_not_permitted` (Source 15).

**[Fact]** Shopify draws an explicit fork based on *who the app is for*, not
which tool built it:

> "If you're building apps for other merchants, use Shopify CLI, which handles
> authentication automatically."
> — Source 15 (direct quote)

**[Fact]** Shopify CLI (Source 17, 18, 19, 20): `shopify app dev` scaffolds an
app, auto-creates its Dev Dashboard app record, provisions a local tunnel, and
walks the developer through installing the app on a development store (an
install-consent screen must still be clicked through in a browser). `shopify app
deploy` publishes the app's configuration/extensions as a version but
**explicitly does not deploy the app's own web server** — that must be hosted
separately. The CLI's default starter app targets apps **rendered in the
Shopify admin** ("You should use this starter app unless you need to scaffold a
standalone app" — Source 2, direct quote); CLI-scaffolded apps use **token
exchange** (if embedded, via Shopify-managed installation) or **authorization
code grant** (if standalone) — **not** client credentials grant.

**[Fact — the central open architectural question]** The platform-wide
app-type/flow comparison table (Source 2) lists exactly three rows: "App
rendered in the Shopify admin" (token exchange, or authorization code grant),
"Standalone app" (authorization code grant), and "Admin-created custom app"
(generate in the Shopify admin — the legacy, now-frozen-for-new-apps path).
**There is no fourth row for a Dev-Dashboard-created custom app used as a
standalone integration.**

**[Inference, not a Shopify statement]** Because this table's only restriction on
authorization-code-grant eligibility is *rendering style* (admin-embedded vs.
standalone), not *creation tool*, a Dev-Dashboard-built app that is architected
as a standalone integration should, by the general rules, be eligible for the
standard OAuth authorization code grant — which, unlike client credentials
grant, is **not** restricted to same-organization/own-store deployments (Source
5: "Public or custom apps must use token exchange or authorization code grant").
By default (the `expiring` parameter omitted, i.e. `0`), authorization code
grant yields a **non-expiring offline token** (Source 4) — the same long-lived
single-secret shape the connector's current credential model already expects.

**[Open question — unresolved by any official worked example]** No official page
fetched today gives an explicit, worked example of running the standard OAuth
authorization-code-grant flow against a Dev-Dashboard-created "own store" custom
app. Shopify's own tutorial for exactly that scenario (Source 14, 15) shows only
the client-credentials path and routes the "other merchants"/OAuth scenario to
Shopify CLI instead. Whether the three-row table (Source 2) is simply stale
relative to the 2026-01-01 custom-app-creation change, or whether a
Dev-Dashboard custom app used as a standalone integration is meant to be read as
falling under the table's "Standalone app" row, **is not stated anywhere
official**. **This is the single most decision-critical unresolved fact in this
research** — it determines whether a non-expiring, drop-in-compatible offline
token can be obtained for a new custom app without building a client-credentials
refresh mechanism.

**[Fact]** Building any Dev Dashboard app requires creating an app **version**
(app URL, webhook API version, scopes) before install. A non-embedded
(standalone) app version may use Shopify's placeholder default URL
(`https://shopify.dev/apps/default-app-home`) if the app has no admin-embedded
UI (Source 14) — but running an actual OAuth authorization-code-grant flow still
requires a real, reachable, HMAC-verifiable redirect URI registered in the Dev
Dashboard (Source 4), which a placeholder URL does not provide. Standing up
OAuth is therefore not merely a documentation/UI difference from the legacy
admin-created flow — it requires hosting a small redirect/callback endpoint.

---

## 5. OAuth authorization code grant (high level)

**[Fact]** The flow (Source 4): (1) the merchant's browser is redirected to
`https://{shop}.myshopify.com/admin/oauth/authorize` with `client_id`, `scope`,
`redirect_uri`, and a `state` nonce; (2) Shopify shows the merchant a permission
grant screen; (3) on approval, Shopify redirects to the app's `redirect_uri` with
an authorization `code` plus other query parameters; (4) the app **must verify**
the callback's `hmac` parameter — "the `hmac` parameter must match the
HMAC-SHA256 hash of the remaining parameters in the query string" (direct quote)
— before trusting it; (5) the app exchanges the code for a token via `POST
https://{shop}.myshopify.com/admin/oauth/access_token` with `client_id`,
`client_secret`, `code`.

**[Fact]** The `redirect_uri` "must be added to your app as an allowed
redirection URL, as configured in the Dev Dashboard" (Source 4, direct quote) —
it must be pre-registered, not arbitrary.

**[Fact]** Online vs. offline is controlled at the *first* redirect via
`grant_options[]` (omit for offline, `per-user` for online); expiring vs.
non-expiring offline is controlled at the *token-exchange* step via an optional
`expiring` body parameter — "the default (`0`) requests an offline token that
does not have an expiry" (Source 4, paraphrase of a table cell; the underlying
meaning is unchanged from the page's literal wording).

**[Fact]** Source 4 explicitly scopes this guide away from admin-embedded apps:
"Apps rendered in the Shopify admin should use token exchange to acquire access
tokens... This guide is only relevant to standalone apps and legacy apps that
aren't using Shopify managed installation" (direct quote).

**[Fact]** Shopify separately, and explicitly, names **ERP integrations** as a
canonical example of an app that does not need to be admin-embedded:

> "Apps that contain more functionality than can be reasonably integrated into
> the Shopify admin do not have to integrate all of their primary workflows
> into the Shopify admin. For example, apps that handle ad buying or enterprise
> resource planning (ERP) require a standalone site to enable access to their
> functionality in a user-friendly manner."
> — Source 25 (direct quote)

**[Inference]** Combining this with Source 4's own scoping, an Odoo↔Shopify
connector — an external, non-admin-embedded, ERP-side integration — most
plausibly falls into Shopify's "standalone app" category for OAuth-flow-
selection purposes, which would make the authorization code grant (not client
credentials grant, not token exchange) the applicable non-legacy mechanism. This
is our synthesis across two pages, not a single explicit Shopify statement
naming ERP/Odoo connectors as "standalone apps."

---

## 6. Offline vs. online access tokens

**[Fact]** Two access modes exist when creating an Admin API access token:
**offline** (service-to-service, no user interaction) and **online** (tied to a
logged-in staff user) (Source 7, 8).

**[Fact]** Prior to December 2025, non-expiring offline tokens were the **only**
offline option:

> "Prior to December 2025, non-expiring offline tokens were the default and
> only option for offline access. These tokens grant permanent access to a
> shop's data and can only be revoked through app uninstallation or secret
> revocation, making them less secure than expiring tokens."
> — Source 7 (direct quote)

This is the shape the connector's current `token_variant='offline_custom_app'`
already uses. Note that Shopify's own current-page wording no longer asserts, in
blanket present tense, that offline tokens "do not expire" — it frames
non-expiring behavior as the historical default, still fully available, rather
than the sole current option.

**[Fact]** In December 2025, Shopify introduced an **opt-in** "expiring offline
tokens" model: a 60-minute (3600-second) access token paired with a 90-day
refresh token; refreshing does not require merchant re-authorization (Sources 7,
32). Obtaining a new expiring token retires the previous one for the same
app+store — the retired token stays valid until its own expiry (so in-flight
requests finish), but its refresh token is invalidated immediately (Source 7).
This change was additive/non-breaking at introduction — "existing perpetual
offline tokens will continue to function" (Source 32, direct quote).

**[Fact]** This new model becomes **mandatory on a two-stage timeline — for
public apps only**:

- New public apps created on/after **April 1, 2026** must use expiring tokens
  from creation (Source 33).
- **All** public apps, including those created before April 1, 2026, must
  migrate to expiring tokens by **January 1, 2027**, after which non-expiring-
  token Admin API calls from public apps receive authentication errors (Source
  34).

**[Fact, verified independently across six separate research passes today]**
Both deadlines **explicitly and identically exempt custom apps and
merchant-created apps**:

> "These requirements don't apply to custom apps or apps created by merchants."
> — Source 7 (direct quote)

The two dated changelogs each restate this with a bulleted exemption list naming
"Custom apps created at any time" and "Apps created by merchants either in the
Dev Dashboard or in the admin" as unaffected (Sources 33, 34).

**[Inference]** Because custom apps and merchant-created apps are exempt from
both deadlines, the connector's current single-token model
(`token_variant='offline_custom_app'`, a non-expiring long-lived secret, no
OAuth) remains a fully supported, non-deprecated option today — it is not at
risk of forced migration under this specific Shopify policy, regardless of which
acquisition path (legacy admin-created, or a future OAuth-based custom-app flow)
produces the token.

**[Fact]** Re-acquiring an offline token for the same shop and app installation
**returns the same token each time**, not a fresh one (Source 7) — relevant if a
future re-authorization flow expects a new value.

**[Fact]** Online tokens expire "either when the user logs out or after 24
hours" (Source 8, direct quote), returning HTTP 401 afterward; no refresh-token
mechanism exists for them.

---

## 7. Token rotation / revocation implications

**[Fact]** Legacy admin-created custom app tokens: **no in-place rotation.**
Only remedy is to delete-and-recreate the app (blocked for new creation since
2026-01-01) or uninstall/reinstall the same app — either way, "Your app's
requests and webhooks are disrupted until you update your app's code with the
new API credentials or access token" (Source 6, direct quote, §3 above).

**[Fact]** Client **secret** rotation (the Dev Dashboard / client-ID+secret
model — a distinct mechanism from the admin-created custom-app token) is a
documented, deliberate six-step process: generate a new secret → deploy it to
production → **only then** revoke the old one.

> "Remember that revoking any secret will also remove the access tokens
> associated with it. ... Don't delete your old client secret until you've
> requested new access tokens for every token stored by your app. Users might
> not be able to open your app if you delete a client secret that still has
> tokens associated with it."
> — Source 10 (direct quote)

Rotating (i.e., generating a new secret) does **not** by itself invalidate old
tokens — only explicitly *revoking* a secret does. This is a materially
different, softer rotation model than the admin-created custom app's
all-or-nothing behavior.

**[Fact]** Uninstalling an app is documented as irreversible: "Uninstalling an
app is an irreversible operation" (Source 12, direct quote). It triggers cleanup
(deletes registered webhooks, script tags, and admin links). "If an app is
uninstalled during key rotation, then both the old and new access tokens will
become unusable" (Source 12, direct quote).

**[Open question]** No official page states the precise **latency** of token
invalidation following a merchant-initiated uninstall via the Shopify admin UI
(as distinct from the `appUninstall` API mutation). The word "immediately"
appears on Source 7 only in the context of a *refresh token* being invalidated
during expiring-token rotation, not in connection with uninstall-triggered
invalidation generally. Treat "instant revocation on uninstall" as a reasonable
but **unconfirmed** assumption for the connector's error-handling design, not a
sourced fact.

**[Fact]** Non-expiring (legacy) offline tokens remain valid indefinitely until
app uninstallation or secret revocation — no automatic expiry, no scheduled
rotation requirement (Source 7).

---

## 8. Development store testing implications

**[Fact]** Development stores are created via the **Dev Dashboard**, not the
Partner Dashboard: "The Dev Dashboard replaces the Partner Dashboard for all
development workflows" (Source 16, direct quote). They are free, with a
selectable plan tier (e.g. Basic/Grow/Advanced/Plus) and optional auto-generated
test data at creation (Sources 26, 28).

**[Fact]** Up to **10 custom apps** can be installed on a development store for
testing; separately, App-Store-distributed apps installable on a dev store are
restricted to "free apps and Partner-friendly apps" (Source 26, both direct
quotes). **[Inference]** these are two different install categories on the same
page (custom/private-integration apps vs. App-Store-listed apps) — the page
does not state this distinction in so many words, so it is logged as an
inference, not a verbatim fact.

**[Fact]** No real payment transactions are possible on a development store —
only the Bogus test gateway or a payment provider's test mode; shipping labels
generated on a dev store are for testing only and are not functional; the
storefront password page cannot be removed (Sources 26, 39).

**[Fact]** Installing custom/draft apps, enabling developer feature previews, or
seeding generated test data all block that store from later being transferred to
a real merchant/client (Sources 26, 28). Stores seeded with generated test data
specifically "can't be transferred to a merchant due to their unique
configuration and the use of Shopify Plus features" (Source 28, direct quote).

**[Open question]** No official page fetched today states an automatic expiry
date or a scheduled data-reset policy for a development store itself. This
should be treated as unverified, not assumed absent.

**[Fact — negative result]** No documented Admin API rate-limit or behavioral
difference between development stores and production stores was found beyond
the payment/checkout and shipping-label restrictions above (Source 29 ties rate
limits to plan tier, not store type/environment). **[Inference]** Since a dev
store's plan tier is selectable at creation, a dev store can be provisioned at
the same rate-limit tier (including Plus) as a production store if that plan is
chosen — this is a deduction from combining Sources 26 and 29, not a single
explicit statement.

**Implication for Task 003 validation:** the existing
`task-003-manual-validation-checklist.md` precondition of testing against "a
Shopify development store (Shopify Partner test store)" is confirmed appropriate
and sufficient for the connector's read-only `action_test_connection()` call —
no Admin API restriction specific to development stores was found that would
affect a read-only `shop` / `currentAppInstallation.accessScopes` query, beyond
the commerce/checkout-transaction restrictions that are out of scope for that
call.

---

## 9. Requirements/limitations by app type (public / custom / legacy private)

**[Fact]** **Private apps are not a current Shopify app type.** Deprecated
January 2022; all were automatically migrated to custom apps by January 20, 2023
(Source 21).

**[Fact]** **Public apps** ("Public distribution"): installable on multiple
Shopify stores; require Shopify app review before distribution; must sync
certain data with Shopify; must use Shopify App Pricing or the Billing API for
all charges; Level 2 protected-customer-data access requires Shopify review
(Sources 21, 22, 23, 24).

**[Fact]** **Custom apps** ("Custom distribution" — the current Dev-Dashboard
path): installable on a single Shopify store, **or** on multiple stores in the
same Plus organization, **or** on transfer-disabled development stores; no
Shopify approval/review required; explicitly **cannot use the Billing API** to
charge merchants (Source 21, direct quote of the comparison table).

**[Fact]** A separate table row, "Shopify admin" (the legacy admin-created
custom app path), is further restricted: single store only, no review required,
and — on top of no Billing API access — **cannot use Shopify App Bridge** or
**app extensions** (Source 21).

**[Fact — nuance not to collapse]** The protected-customer-data access matrix
(Source 23) has **three** columns, not two: "Public app" (Level 2 — name,
address, phone, email — "Requires review"), "Custom app" (Level 2 "Always
available"), and **"Admin created custom app"** (Level 2 **"Varies by plan"** —
*not* unconditionally "Always available" the way a general Dev-Dashboard custom
app is). This distinction matters specifically for Option A's legacy
admin-created path, discussed further in
[`../03-architecture/shopify-token-acquisition-options.md`](../03-architecture/shopify-token-acquisition-options.md).

**[Fact]** Accessing "Custom Level 2 PII" apps requires the store to be on the
Grow plan or higher (Source 36).

**[Open question]** No official page states in so many words that custom apps
"cannot be listed on / discovered via the Shopify App Store" — this is a
reasonable **[Inference]** from the distribution table's "Approval required: No"
rows for both custom-app variants, combined with the public-app-only App-Store
review language, not a directly quotable fact.

---

## 10. Explicit unknowns / inaccessible details

The following remain genuinely open after this research pass and must not be
asserted as settled in any downstream document:

1. **[Open question, decision-critical]** Whether a Dev-Dashboard-created custom
   app, built for a merchant's own store and architected as a standalone
   integration, can use the standard OAuth authorization-code-grant flow to
   obtain a non-expiring offline token — no official worked example confirms
   this combination; Shopify's own "own store" tutorial shows only the
   client-credentials path. (§4)
2. **[Open question]** Whether the `shpca_` custom-app token prefix is still
   current in 2026 — unconfirmed on any live page; only in a 2020 changelog.
   (§2)
3. **[Open question]** Whether the historical "reveal token once" /
   last-4-characters admin-created-custom-app UI behavior still exists —
   unconfirmed on any official page; only third-party sources describe it,
   which this project's citation policy excludes. (§3)
4. **[Open question]** The precise latency of token invalidation on a
   merchant-initiated uninstall via the Shopify admin UI. (§7)
5. **[Open question]** Whether a development store has an automatic expiry date
   or scheduled data-reset policy. (§8)
6. **[Open question]** Whether custom apps are explicitly, in Shopify's own
   words, excluded from Shopify App Store listing (only inferable from table
   structure). (§9)

Nothing in this document should be read as a recommendation or a decision — see
the companion architecture options and decision-brief documents for that
analysis, both of which are subject to ChatGPT review per `CLAUDE.md` §2/§6.
