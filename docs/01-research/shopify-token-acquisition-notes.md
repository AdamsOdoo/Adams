# Shopify Token-Acquisition Notes — 2026-07-08 Refresh & Gap-Fill

> **Research-phase document. No architecture decision or implementation choice is
> made here.** This is a **follow-up** to
> [`shopify-token-acquisition-research.md`](./shopify-token-acquisition-research.md)
> (39-source inventory, fetched live 2026-07-07). It does **not** repeat that
> file's full source table or restate every fact — it (a) re-verifies the
> load-bearing 2026-07-07 findings against live Shopify sources fetched again
> today, (b) fills three gaps that file left open (exact MVP scope names, OAuth
> security guidance for a future setup wizard, and the "who owns the Shopify
> app" question behind the single most decision-critical open item), and (c)
> flags one new correctness finding in the connector's own shipped code. Per
> `CLAUDE.md` §8, every statement below is labelled **[Fact]**, **[Inference]**,
> or **[Open question]**. No **Decision** is recorded here — see
> [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md).

## Status

- **Session date:** 2026-07-08.
- **Trigger:** VAL-B2/MBQ-05 closure-path research session (this session), per
  the task prompt's research questions 1–7.
- **Method:** A 10-agent research fan-out (6 external, 4 internal), authorized
  under `CLAUDE.md`'s "official API verification" high-power-mode allowance —
  6 agents independently re-fetched the load-bearing 2026-07-07 Shopify URLs
  live today via WebFetch/WebSearch (not from memory/training data) and
  targeted three specific gaps; 4 agents read this repository's own governance
  files and shipped code (read-only, no edits). Stop condition: one
  verification pass per topic, cross-checked against the 2026-07-07 file;
  anything not confirmed live today is logged as an open question, not
  asserted.
- **Source tiers (reminder, per `CLAUDE.md` §7):** `shopify.dev` and
  `help.shopify.com` are Tier 1 (official documentation). `changelog.shopify.com`
  is a distinct, official first-party domain (Tier 1, flagged separately per
  citation policy). **New in this document:** `community.shopify.dev` (the
  Shopify Developer Community forum) is used twice below for named-Shopify-staff
  replies. This is **not** a primary documentation page — it is a
  Shopify-operated support forum where Shopify employees post informally. It is
  cited here as the best available evidence for an otherwise-undocumented
  platform behavior, but is explicitly **not** given the same evidentiary weight
  as a `shopify.dev` page, and every claim sourced from it is labelled
  accordingly.

---

## 1. Re-verification of the 2026-07-07 load-bearing facts — no change detected

All three pages below were re-fetched live today (2026-07-08). Each confirms
the 2026-07-07 finding verbatim; nothing has changed.

- **[Fact]** "You can no longer create new custom apps in the Shopify admin.
  Existing admin-created custom apps continue to work." / "To create a new
  custom app, use the Dev Dashboard or Shopify CLI." — direct quotes, re-fetched
  today.
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin
  — Accessible — 2026-07-08.
- **[Fact]** Admin-created custom app tokens still cannot be rotated in place:
  "You can't rotate API credentials for custom apps created in the Shopify
  admin. You need to delete the app and create a new custom app which has new
  API credentials." — same page, re-confirmed today. Deleting-and-recreating is
  still impossible for new admin-created apps (frozen since 2026-01-01); the
  only remaining remedy for a legacy app is uninstall/reinstall, which disrupts
  requests/webhooks until the code is updated.
- **[Fact]** The January 1, 2026 legacy-custom-app creation cutoff is unchanged.
  "Starting January 1, 2026, you can no longer create new custom apps in the
  Shopify admin. ... Existing custom apps aren't affected and will continue to
  work." https://changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026
  — Accessible — 2026-07-08 (published 2025-10-30, no later edit date found).
  Corroborated on https://help.shopify.com/en/manual/apps/app-types/custom-apps
  — Accessible — 2026-07-08.
- **[Fact]** The December 2025 expiring-offline-token model, and its
  April 1, 2026 / January 1, 2027 mandatory-migration dates **for public apps
  only**, are unchanged, and the custom-app/merchant-created-app exemption is
  unchanged and re-quoted verbatim today: "These requirements don't apply to
  custom apps or apps created by merchants."
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/offline-access-tokens
  — Accessible — 2026-07-08. Both dated changelogs
  (https://shopify.dev/changelog/expiring-offline-access-tokens-required-for-public-apps-april-1-2026,
  https://shopify.dev/changelog/expiring-offline-access-tokens-required-for-all-public-apps-as-of-january-1-2027)
  re-confirmed — Accessible — 2026-07-08. **[Inference]** The connector's
  current non-expiring, single-secret model (`token_variant='offline_custom_app'`)
  remains a fully supported, non-deprecated shape today, unchanged from
  2026-07-07's conclusion.
- **[Fact]** The Dev Dashboard's own tutorial for a merchant building an app for
  their own store still demonstrates only the client-credentials grant (24-hour
  token, no admin-UI reveal, same-organization restriction). Re-confirmed today
  on https://shopify.dev/docs/apps/build/dev-dashboard/create-apps-using-dev-dashboard
  and https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens
  — both Accessible — 2026-07-08. **Citation-precision correction:** the
  2026-07-07 file paraphrased Shopify's guidance to developers building for
  other merchants as "building apps for other merchants" and presented it as a
  direct quote from the Dev Dashboard tutorial. Re-checked today: that exact
  phrase is **not** verbatim on any of the four re-fetched pages. The actual
  verbatim callout is: "Creating an app for the app store? Build using Shopify
  CLI instead." (same tutorial page). This is a wording-precision correction,
  not a substantive reversal — the underlying guidance (use CLI, not the Dev
  Dashboard, when the app is not solely for your own store) is unchanged.
  https://shopify.dev/docs/apps/build/dev-dashboard/create-apps-using-dev-dashboard
  — Accessible — 2026-07-08.

No official Shopify source dated after 2026-07-07 was found (via WebSearch
sweeps of `changelog.shopify.com` and targeted queries) that alters any of the
above.

---

## 2. New evidence: the "who owns the app" resolution of the OAuth token-flow question (token-flow mechanics only — not a distribution-scale finding)

The 2026-07-07 file flagged, as **the single most decision-critical open
question**, whether a Dev-Dashboard-created custom app — built for a merchant's
own store, architected as a standalone (non-embedded) integration — can use the
standard OAuth authorization-code-grant flow to obtain a non-expiring offline
token, since no official worked example covered that exact combination.

Today's re-verification pass surfaced new evidence that **substantially
narrows, though does not 100% officially close, this question** — and the
narrowing turns on an axis the 2026-07-07 file did not fully separate out:
**which organization owns the Shopify app relative to which organization owns
the store.** **This entire section is about which OAuth grant type an
app+store pairing is routed to — it is a token-flow finding, not a
distribution-scale finding.** It must not be read as evidence that Custom
Distribution can serve many unrelated merchant organizations; the official,
separate limit on that is stated as its own **[Fact]** below and is not
overridden or widened by the community-forum evidence that follows.

- **[Fact]** Official docs state the client-credentials/OAuth split by
  organizational ownership, not by custom-vs-public app type: "Client
  credentials is only available for apps developed by your own organization and
  installed in stores that you own." / "Public or custom apps must use token
  exchange or authorization code grant."
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant
  — Accessible — 2026-07-08 (re-confirms 2026-07-07).
- **[Fact — new, Shopify Developer Community, staff reply, 2026-01-20]** A named
  Shopify staff member answered this exact scenario directly: "merchants
  creating apps for their own stores through the Dev Dashboard need to exchange
  their client ID and secret via an API call to get a token, and that token
  expires after 24 hours." He explicitly contrasted this with a **different**
  scenario: "this only applies to merchants creating apps for their own stores
  via the Dev Dashboard. Custom and public apps created by partners through the
  Partner Dashboard still use OAuth (token exchange or authorization code
  grant), nothing has changed there."
  https://community.shopify.dev/t/custom-app-access-token-with-oauth-flow/28525
  — Accessible — 2026-07-08. **This is a community-forum staff reply, not a
  `shopify.dev` documentation page** — cited as the best available evidence,
  not as formal documentation.
- **[Fact — same thread]** When developers asked Shopify staff for a
  non-expiring token in the own-store/Dev-Dashboard scenario, staff did **not**
  offer authorization-code-grant as an alternative for that case; they
  reiterated a deliberate security rationale ("Long-lived tokens that never
  expire carry higher security risk. If one gets leaked ..., it grants
  indefinite access to the store.") and pointed toward the public-app pathway
  instead. Same URL — Accessible — 2026-07-08.
- **[Fact — different Shopify Developer Community thread]** A separate Shopify
  staff reply confirms the **opposite** organizational scenario — an app built
  by one organization (e.g. a connector vendor) for installation on a
  **different** organization's store — does support authorization-code-grant
  yielding a permanent, non-expiring offline token (`expiring` omitted/`0`):
  "Client credentials won't work for your case because it only works when the
  app and store are owned by the same organization."
  https://community.shopify.dev/t/custom-app-credentials/27460/9 — Accessible —
  2026-07-08. Community-forum staff reply, same caveat as above.
- **[Fact — official distribution-method limit, verified live 2026-07-08]**
  Shopify's own distribution-method page scopes **Custom distribution**
  explicitly by store count/organization, not by merchant count: "Select this
  method if you've built a custom app that you want to distribute to one store
  or multiple stores on the same Plus organization using a link." **Public
  distribution** is Shopify's documented route for reaching many unrelated
  merchants: "Select this method to make your app public. You can distribute
  or sell your app to many merchants through the Shopify App Store using this
  method." https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
  — Accessible — 2026-07-08 (re-confirms and sharpens
  `shopify-token-acquisition-research.md` §9's distribution table). **This is
  a distribution-method/store-count limit, entirely separate from the
  token-flow evidence above** — the community-forum staff replies describe
  which OAuth grant an app+store *pair* is routed to; they say nothing about,
  and do not widen, how many unrelated merchant organizations one Custom
  Distribution app may officially serve.
- **[Inference — scoped to one store (or same-Plus-org stores); NOT a
  scalable multi-customer finding]** Combining the two community threads with
  the official client-credentials scoping fact and the distribution-method
  limit immediately above: for **a single customer/pilot store, or purely for
  gathering VAL-B2 evidence**, a Custom Distribution app registered by a
  *different* organization than the one that owns that one store sits in the
  cross-organizational scenario the second thread confirms supports
  authorization-code-grant with a non-expiring offline token, matching the
  connector's already-shipped credential shape
  (`token_variant='offline_custom_app'`) with **zero schema change** — **for
  that one store**. **This is a one-store (or same-Plus-org) evidence path.
  It must not be read as, and this document does not claim it is, an
  officially-supported mechanism for installing one vendor-owned Custom
  Distribution app across many unrelated customer stores** — Custom
  Distribution's own documented scope (the Fact immediately above) excludes
  that.
- **[Open question, distinct from the one-store token-flow question above]**
  Whether and how the connector could be distributed as a commercial product
  to many unrelated customers at all — via Public distribution (App Store
  review, compliance webhooks, Billing API — see
  `shopify-token-acquisition-research.md` §9), via some other officially
  supported route, or via a materially different technical arrangement — is
  **not answered by this session's research** and is a separate,
  separately-gated architecture question from the one-store finding above.
  This session did not verify how any specific competitor connector is
  actually distributed; it only confirms, from Shopify's own documentation,
  that Custom Distribution's documented scope does not cover many unrelated
  merchant organizations.
- **[Open question, narrowed but not closed — one-store scenario only]** No
  official `shopify.dev` tutorial or worked example — as of 2026-07-08 —
  shows this specific cross-organizational combination end-to-end (a Custom
  Distribution app registered by one organization, installed on one different
  organization's store, completing standalone authorization-code-grant for a
  non-expiring offline token). The evidence above is strong circumstantial
  support (official scoping rule + two independent staff replies covering each
  half of the ownership axis), but it is **not a single official page
  confirming the full combination**. This residual should be treated as
  **plausible, evidence-backed, but still empirically unverified** until an
  actual authorization-code-grant exchange is run against a real
  cross-organizational app+store pair and observed to succeed.
- **[Open question]** Whether it is technically *possible* (as opposed to
  officially documented) for a **same-organization** own-store Dev-Dashboard
  custom app to still be manually driven through `/admin/oauth/authorize` is
  unconfirmed either way — no explicit server-side prohibition was found in the
  docs, but no staff reply or documentation confirms it works. This is now a
  narrow residual question, not the load-bearing one.

---

## 3. New evidence: exact Admin API scope names for the MVP baseline

Fetched live today from Shopify's official access-scopes reference:
https://shopify.dev/docs/api/usage/access-scopes — Accessible — 2026-07-08.

- **[Fact]** `read_products`, `read_customers`, `read_orders`, `read_inventory`,
  and `read_locations` are current, correctly-named scopes, and each maps to
  the object the connector's MVP domain scope needs (Product/ProductVariant;
  Customer; Order/Fulfillment/OrderTransaction; InventoryLevel/InventoryItem;
  Location respectively) — confirmed both on the access-scopes table and on
  each object's own reference page's "Requires ... access scope" line.
- **[Fact — correctness finding, not a change since 2026-07-07, but not
  previously checked]** `read_fulfillments` is a real, current scope, but per
  the official access-scopes table it governs only the `FulfillmentService`
  resource (third-party fulfillment-service registration/config) — **not**
  read access to the `Fulfillment` object (an order's fulfillment/tracking
  data). The `Fulfillment` object's own reference page states its requirement
  as one of `read_orders`, `read_marketplace_orders`,
  `read_assigned_fulfillment_orders`, `read_merchant_managed_fulfillment_orders`,
  `read_third_party_fulfillment_orders`, or `read_marketplace_fulfillment_orders`
  — `read_fulfillments` does not appear in that list. The same is true of the
  `FulfillmentOrder` object's reference page.
  https://shopify.dev/docs/api/usage/access-scopes ;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/Fulfillment ;
  https://shopify.dev/docs/api/admin-graphql/latest/objects/FulfillmentOrder
  — all Accessible — 2026-07-08.
- **[Fact]** The connector's already-shipped `shopify_connector_readiness_check.py`
  `REQUIRED_MVP_SCOPES` constant (lines 53–60) currently checks exactly these
  six values: `read_products`, `read_customers`, `read_orders`,
  `read_inventory`, `read_locations`, `read_fulfillments`.
- **[Inference — correctness flag, not corrected by this docs-only session]**
  Per the two Facts above, `read_fulfillments`'s presence in
  `REQUIRED_MVP_SCOPES` does not, per official Shopify documentation, gate read
  access to order fulfillment data the way its name suggests — that access is
  actually governed by `read_orders` (already in the same required-scopes set)
  and/or the `FulfillmentOrder`-family scopes, depending on which fulfillment
  API model (legacy `Fulfillment` object vs. `FulfillmentOrder`-based flow) the
  connector's future fulfillment domain ultimately adopts (an open question
  this project's own MBQ/DEC register already routes to the fulfillment task
  spec — see `master-blueprint-inventory-fulfillment.md`/DEC-011). **This
  session does not modify any code** — this is flagged here as a factual
  correction for ChatGPT/a future task to weigh, not resolved or fixed by this
  document.
- **[Fact]** The shop-identity query/resource used by the connector's existing
  `action_test_connection()` (`shop { id name myshopifyDomain }` /
  `GET /admin/api/shop.json`) carries **no** "Requires ... access scope"
  statement on its official reference page, unlike every other scoped
  object/query checked. https://shopify.dev/docs/api/admin-graphql/latest/queries/shop
  ; https://shopify.dev/docs/api/admin-rest/latest/resources/shop — both
  Accessible — 2026-07-08. **[Inference]** A bare shop-identity read therefore
  proves token *validity* (the token is accepted and not revoked) but not scope
  *sufficiency* — which is exactly why the connector's existing design keeps
  these as two separate readiness checks (`_check_credential_test_connection`
  vs. `_check_required_scopes`), rather than one.
- **[Fact]** Write-scope counterparts (`write_products`, `write_customers`,
  `write_orders`, `write_inventory`) exist and are named consistently with
  their read counterparts, for future post-MVP reference only — MVP itself
  authorizes read-only scope usage (per `mvp-scope.md`'s accepted domain
  direction, §4 below), except where MVP's own accepted write-back domains
  (inventory, fulfillment, product export) require the corresponding write
  scope, which is unchanged from DEC-004's already-accepted least-privilege
  posture and is not re-decided here.
- **[Fact]** No dedicated "tax" scope exists in Shopify's documented
  authenticated access-scopes table. Pricing/discount-adjacent scopes that do
  exist: `read_draft_orders`/`write_draft_orders`, `read_price_rules`/
  `write_price_rules`, `read_discounts`/`write_discounts` — documented for
  reference only, not required by MVP's accepted read/write-back scope (order
  import already covers Shopify-computed tax/discount/shipping evidence per
  `mvp-scope.md` and MBQ-27's DEC-020-adjacent posture).

---

## 4. New evidence: official OAuth security guidance for a future setup wizard

All fetched live today, all Accessible — 2026-07-08.

- **[Fact]** HMAC verification is mandatory, not optional: "The `hmac`
  parameter must match the HMAC-SHA256 hash of the remaining parameters in the
  query string." "If any of the checks fail, then your app must reject the
  request with an error and not continue."
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant
- **[Fact]** The redirect URI is not arbitrary: "The complete URL specified
  here must be added to your app as an allowed redirection URL, as configured
  in the Dev Dashboard." Same page. The `shop` query parameter must also be
  validated (must end in `myshopify.com`, restricted character set) as part of
  the same mandatory check sequence.
- **[Fact]** A `state` parameter is required for CSRF protection: "a randomly
  selected value provided by your app that is unique for each authorization
  request"; "During the OAuth callback, your app must check that this value
  matches the one you provided during authorization." Same page. Shopify's own
  example implementation persists this value via a signed cookie during the
  redirect (the code sample's variable naming calls it "nonce" — flagged as
  the same mechanism under two names on the same page, not two separate
  mechanisms).
- **[Fact]** The client secret must be kept out of source code (Shopify's own
  example stores it as an environment variable "to prevent exposing it in
  code") and must be rotated on a defined, deliberate schedule: generate a new
  secret → deploy it → **re-request access tokens for every stored token** →
  only then revoke the old secret ("Don't delete your old client secret until
  you've requested new access tokens for every token stored by your app" —
  revoking a secret immediately deletes every access token associated with
  it). Immediate revocation is required on a suspected breach, before
  generating a replacement.
  https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets ;
  https://shopify.dev/docs/apps/build/authentication-authorization/client-secrets/rotate-revoke-client-credentials
- **[Fact]** Shopify expects apps to defend against the OWASP Top 10 generally
  (app-review criterion), and requires least-privilege scope requests: "Apps
  should request only the minimum amount of data that's necessary."
  https://shopify.dev/docs/apps/build/security/protect-against-common-vulnerabilities ;
  https://shopify.dev/docs/api/usage/access-scopes
- **[Fact]** For protected customer data (PII), Shopify's own review
  requirements mandate encrypting data at rest and in transit, and encrypting
  backups — but this requirement is explicitly scoped to PII fields, not to
  Admin API access tokens/client secrets.
  https://shopify.dev/docs/apps/launch/protected-customer-data
- **[Open question — negative result, checked across 8 official pages]** No
  `shopify.dev` page found (checked: authorization-code-grant, client-secrets,
  rotate-revoke-client-credentials, protect-against-common-vulnerabilities,
  protected-customer-data, access-scopes, the authentication-authorization
  overview, and the access-tokens overview) states an explicit requirement to
  encrypt Admin API access tokens/client secrets at rest, or to use a secrets
  manager, or to mask them in logs, specifically. **This means the connector's
  own existing "masking + ACL, never claim encryption" posture
  (`credential-connection-api-client-planning.md`, accepted 2026-07-06) is not
  contradicted by any official Shopify requirement** — it is this project's own
  conservative choice, not a Shopify mandate, and should continue to apply
  identically to any future OAuth-acquired token (no different, weaker, or
  stronger claim for an OAuth-sourced token than for a manually-pasted one).
- **[Open question]** No specific rotation cadence (e.g. "every 90 days") is
  stated anywhere official — only "regularly"/"on a regular basis."

---

## 5. What changed from older private/custom app assumptions (recap)

Unchanged from the 2026-07-07 file, restated briefly for readers who have not
read it: "private apps" are not a current Shopify concept (deprecated January
2022, migrated to custom apps by January 20, 2023); the pre-2026 assumption
that "an Admin can create a custom app and immediately reveal a token in the
Shopify admin UI" is now closed to any newly-created app (frozen 2026-01-01);
new custom apps go through the Dev Dashboard or CLI and, per §2 above, land in
one of two materially different mechanics depending on **which organization
owns the app relative to the store** — a distinction the project's earlier
research surfaced the symptoms of (client-credentials-only for the Dev
Dashboard's own tutorial) but did not fully separate from the store-ownership
axis until this session's community-forum evidence.

## 6. Risks and assumptions

- **Conflation risk (corrected this revision):** the §2 token-flow evidence
  (which OAuth grant an app+store pair is routed to) must not be conflated
  with distribution scale (how many unrelated merchant stores one app may
  serve). Custom Distribution's official scope is one store, or multiple
  stores in the same Plus organization — never many unrelated organizations.
  An earlier draft of this document risked exactly this conflation by
  describing a vendor-owned Custom Distribution app as a general
  install-per-customer mechanism; that wording has been corrected in §2.
- The community-forum evidence in §2 is the best currently-available signal on
  the one-store token-flow question, but it is **not** a `shopify.dev` page and
  carries the evidentiary weight of an informal staff reply, not formal
  documentation. Shopify could clarify or change this informally-stated
  behavior without a changelog entry. It says nothing about, and does not
  widen, Custom Distribution's separate, officially documented store-count
  limit.
- The `read_fulfillments` scope-name finding (§3) is a correctness risk in
  already-shipped code (`shopify_connector_readiness_check.py`), not something
  this docs-only session may fix. If left unaddressed, the readiness check's
  required-scopes gate may pass or fail on a scope that does not actually
  control the resource its name implies.
- No live Shopify API call was made by this session (no code, no addon change,
  no OAuth attempt) — every finding above is a documentation/community-source
  read, not an empirical test of the connector against a real Shopify store.

## 7. Unanswered / open questions carried forward

1. Whether a cross-organizational (vendor-owned app, one customer-owned store)
   Custom Distribution app can complete authorization-code-grant end-to-end
   for a non-expiring offline token has strong circumstantial support (§2) but
   no single official worked example — genuinely unverified until attempted.
   **This is a one-store question; it does not address multi-customer
   distribution scale (see item 6 below).**
2. Whether a same-organization own-store app can still be manually driven
   through `/admin/oauth/authorize` (§2, narrow residual) is unconfirmed either
   way.
3. Whether the connector's own `REQUIRED_MVP_SCOPES` should be corrected to
   drop or supplement `read_fulfillments` (§3) is an open question for
   ChatGPT/a future task — not decided or fixed here.
4. Whether this project's existing Shopify Partner/Dev Dashboard organization
   already holds any pre-2026-01-01 legacy custom app that could close VAL-B2
   immediately with zero OAuth work is unknown to this session — it requires a
   human operator to check the actual Partner/Dev Dashboard account, which no
   session so far has had access to (see
   [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md)).
5. No numeric client-secret rotation cadence is stated anywhere official (§4).
6. **Whether/how the connector could be distributed to many unrelated
   customers at all** — via Public distribution, a per-customer Custom
   Distribution app, or another officially-supported route — is unresolved
   and is a separate, separately-gated architecture question from the
   one-store token-flow finding in §2. This session's research does not
   answer it.

## 8. Explicit non-claims

This document does not claim: that OAuth authorization-code-grant has been
tested against this connector's actual Shopify development store; that VAL-B2
has passed; that MBQ-05 is resolved; that any token-acquisition direction is
accepted; that the `read_fulfillments` finding has been corrected in code; or
that Custom Distribution is an officially-supported mechanism for installing
one vendor-owned app across many unrelated customer stores (it is not — see
§2's distribution-method limit, which scopes Custom Distribution to one store
or multiple stores in the same Plus organization only).
See [`../04-decisions/DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md)
for the decision proposal this research feeds, and
[`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) for the
evidence plan to actually close VAL-B2.
