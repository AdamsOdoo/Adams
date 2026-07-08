# DEC-023 — Token Acquisition Path and VAL-B2 Closure (Proposal)

## Status

**Proposed, not accepted.** Prepared 2026-07-08; revised 2026-07-08 (second
pass, same day) after ChatGPT review. Does not resolve MBQ-05. Does not pass
VAL-B2. Does not authorize OAuth implementation, a setup wizard, or any code
change. Requires explicit ChatGPT review and acceptance before any part of it
becomes binding, per `CLAUDE.md` §2/§6/§8.

**Revision note (second pass):** ChatGPT's review of the first version found
one material issue — it overstated Custom Distribution as a scalable future
MVP architecture for many unrelated customers. Official Shopify docs are
explicit that Custom distribution is scoped to "one store or multiple stores
on the same Plus organization using a link," while Public distribution is
the documented route to "distribute or sell your app to many merchants
through the Shopify App Store."
(https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
— Accessible — 2026-07-08). A single vendor-owned Custom Distribution app is
therefore **not** a general install-per-customer mechanism for many unrelated
customer stores. §2 through §4 below are corrected accordingly, and §3.2 (the
"later track") is narrowed to a candidate-architecture split rather than a
single recommended architecture. This correction does not change VAL-B2's
status, MBQ-05's status, or this document's own Proposed-not-accepted status.

Builds on, and does not weaken or reopen:
[`DEC-004`](./DEC-004-distribution-api-auth-strategy.md) (accepted
offline/unattended access model, masked storage, least-privilege scopes —
unchanged), [`DEC-021`](./DEC-021-val-b2-deferral-for-task-004.md) (VAL-B2
deferred from the Task 003 → Task 004 gate only — unchanged, still in force),
[`shopify-token-acquisition-decision-brief.md`](./shopify-token-acquisition-decision-brief.md)
(2026-07-07, Option A/B/C framing — extended, not superseded), and Task 002's
already-shipped credential schema
(`shopify.connector.store.credential`, `token_variant='offline_custom_app'`,
one secret field — unchanged, no migration proposed).

Evidence base:
[`../01-research/shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md)
(2026-07-08 refresh) plus
[`../01-research/shopify-token-acquisition-research.md`](../01-research/shopify-token-acquisition-research.md)
(2026-07-07, 39-source inventory) plus this repository's own governance record
(MBQ-05 row in
[`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md),
`credential-connection-api-client-planning.md`, `mvp-scope.md`,
`setup-ux-principles.md`).

## 1. Context

- **VAL-B2** (the Task 003 valid-token positive-connection test) has been
  **BLOCKED, not passed, not failed**, since PR #107 — no real Shopify Admin
  API access token compatible with the connector's shipped
  `token_variant='offline_custom_app'` credential shape has ever been obtained
  in any session. DEC-021 formally deferred VAL-B2 from the Task 003 → Task
  004 *gate* only; it explicitly did not resolve VAL-B2 and remains in force
  unchanged by this proposal.
- **MBQ-05** ("exact custom-app creation surface ... and its token-acquisition
  mechanics") remains **open** in the master-blueprint-open-questions.md
  register, deferred for Task 004's gate-opening review only, not resolved as a
  final token-acquisition strategy.
- **Root cause, confirmed and re-verified live 2026-07-07 and 2026-07-08:**
  Shopify closed the "reveal a token in the admin UI" path for any custom app
  created after January 1, 2026. A merchant/customer starting today cannot
  obtain a compatible token the way the connector's setup story implicitly
  assumed when Task 002 was built.
- **New this session:** re-verification found no material change in the
  underlying Shopify facts since 2026-07-07, but surfaced two new pieces of
  evidence that sharpen the previously-unresolved central question (see §2),
  plus one correctness finding in already-shipped code (§5), plus concrete
  official security guidance for a future setup wizard (§6).

## 2. What is newly known: the "who owns the app" axis (token-flow mechanics only — not a distribution-scale finding)

The 2026-07-07 decision brief's single most decision-critical open question
was whether a Dev-Dashboard custom app, built for a merchant's own store, can
use OAuth authorization-code-grant to get a non-expiring offline token. This
session's research (full detail and citations in
[`shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md)
§2) found:

- **[Fact, Shopify staff, Developer Community, 2026-01-20]** A Dev-Dashboard
  custom app built by a merchant **for their own store** (same Shopify
  organization owns the app and the store) is routed to **client-credentials
  grant only** — a 24-hour token, no admin-UI reveal, requiring a programmatic
  refresh loop. Shopify staff, asked directly for a non-expiring alternative in
  this exact scenario, did not offer authorization-code-grant; they pointed to
  the public-app pathway instead.
- **[Fact, Shopify staff, Developer Community, separate thread]** An app built
  by a **different** organization than the one that owns the store it is
  installed on (the standard "vendor builds an app, merchant installs it"
  shape) **does** support OAuth (token exchange or authorization-code-grant),
  and authorization-code-grant can yield a non-expiring offline token
  (`expiring` omitted/`0`) in that scenario.
- **[Fact — official distribution-method limit, corrects the first version
  of this proposal]** Shopify's own distribution-method page scopes **Custom
  distribution** by store count/organization, not by merchant count: "Select
  this method if you've built a custom app that you want to distribute to one
  store or multiple stores on the same Plus organization using a link."
  **Public distribution** is the documented route for reaching many
  unrelated merchants: "Select this method to make your app public. You can
  distribute or sell your app to many merchants through the Shopify App
  Store using this method."
  https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
  — Accessible — 2026-07-08. **This is a separate, official limit that the
  token-flow evidence above does not override or widen** — the community
  replies describe which OAuth grant an app+store *pair* uses; they say
  nothing about how many unrelated merchant organizations one Custom
  Distribution app may serve.
- **[Inference — scoped to one store, or same-Plus-org stores; not a
  scalable multi-customer finding]** For **a single customer/pilot store, or
  purely for VAL-B2 evidence-gathering**, a Custom Distribution app
  registered by a *different* organization than the one that owns that one
  store sits in the cross-organizational scenario the second thread confirms
  supports authorization-code-grant with a non-expiring offline token,
  matching the existing `token_variant='offline_custom_app'` storage shape
  with **zero schema change** — **for that one store**. **This is not, and
  must not be read as, an officially-supported mechanism for installing one
  vendor-owned Custom Distribution app across many unrelated customer
  stores** — the distribution-method limit above excludes that.
- **[Open question — distinct from the one-store finding above]** Whether
  and how the connector could be distributed as a commercial product to many
  unrelated customers at all — via Public distribution (App Store review,
  compliance webhooks, Billing API), or another officially-supported route —
  is **not answered by this research** and is a separate, separately-gated
  architecture question. See §3.2's revised framing below.
- **The one-store finding is evidence-backed, not officially demonstrated
  end-to-end.** No single `shopify.dev` page shows the specific combination
  (one Custom Distribution app, registered by one organization, installed on
  one different organization's store, completing standalone
  authorization-code-grant for a non-expiring offline token) working, start
  to finish. It remains an **empirically unverified hypothesis**, materially
  stronger than the 2026-07-07 "genuinely unclear either way" status, but not
  yet a proven fact — and, independently of whether it is proven, it says
  nothing about distribution scale.

## 3. Decision proposal

**Proposed for ChatGPT review — a two-track approach:**

### 3.1 Immediate track — close VAL-B2 with zero code (evidence-gathering only)

Attempt to close VAL-B2 using whichever of the following is actually available
to a human operator with access to this project's real Shopify Partner/Dev
Dashboard account (**no session to date has had such access** — see
[`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) for the
exact preconditions and steps), in this preference order:

1. **A pre-existing legacy admin-created custom app** (created before
   2026-01-01), if this project's Shopify account already has one on any
   development store — reveal its token directly in the admin UI, zero OAuth,
   highest confidence, fastest.
2. **A manually-completed, one-time OAuth authorization-code-grant exchange**
   against a **cross-organizational** Custom Distribution app (registered
   under a *different* Shopify organization than the one that owns the test
   development store) — per §2's evidence, this is the combination most likely
   to succeed and to yield a non-expiring token.
3. **A manually-completed exchange against a same-organization, own-store**
   Dev-Dashboard app — per §2's evidence, this is now expected to route to
   client-credentials-grant (24-hour token) rather than a non-expiring token,
   and is **not recommended as the primary attempt**, though it is not
   forbidden to try opportunistically as a residual-question check.

Whichever token results (if any), it is pasted into the existing
`shopify.connector.store.credential.access_token` field exactly as Option A
already works — **no code change**, per
[`shopify-token-acquisition-options.md`](../03-architecture/shopify-token-acquisition-options.md)
Option C's original framing.

### 3.2 Later track — final MVP auth/distribution architecture remains a gated decision, not recommended here

**Corrected this revision:** the first version of this proposal recommended a
single "vendor-owned Custom Distribution app, installed by each customer"
architecture as the target MVP design. That recommendation is **withdrawn** —
it is factually incompatible with Shopify's own documented Custom Distribution
scope (§2's Fact: one store, or multiple stores in the same Plus
organization only — never many unrelated organizations). **This document does
not recommend a final MVP auth/distribution architecture.** It instead
proposes a **candidate-architecture split**, both branches of which remain
open and require their own separate, gated evaluation before any
implementation:

- **A — one-store / private-customer / VAL-B2-evidence scope.** For a single
  pilot customer, a private/custom deployment, or purely for gathering VAL-B2
  evidence, a Custom Distribution app **may be valid** — per §2's evidence, a
  Custom Distribution app registered by an organization different from the
  one store it serves supports authorization-code-grant with a non-expiring
  offline token, for that one store. This is the scope
  [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md)'s
  Path 2 already operates in.
- **B — many unrelated customers / commercial product scope.** If the
  connector is to be distributed as a product to many unrelated customer
  organizations, Custom Distribution's documented one-store/same-Plus-org
  limit means it is **not**, by itself, a valid general mechanism for that.
  **Public distribution, or another officially-supported scalable
  route, must be separately evaluated and accepted by ChatGPT before any
  implementation work assumes a specific multi-customer distribution
  mechanism.** This evaluation is not performed by this document — it is a
  distinct, not-yet-scoped research/decision task.

Whichever branch (or combination) is eventually accepted, the underlying
OAuth mechanics (authorization-code-grant, non-expiring offline token,
existing `token_variant='offline_custom_app'` storage shape, each customer's
own Odoo instance hosting its own redirect/callback controller at its own
`web.base.url`) are expected to be similar — but **which Shopify app
definition(s) get registered, under which distribution method, by whom, is
not decided here** and must not be assumed by any future task spec without a
separate ChatGPT decision.

**Not decided by this proposal:** which of A/B (or both) the project adopts;
exact controller/hosting mechanics; exact install-link distribution
mechanism; the Shopify Partner organization(s) under which any app is
registered; and the exact setup-wizard screens — all of these remain open,
and the B branch specifically requires its own dedicated research/decision
pass (Public distribution's app-review, compliance-webhook, and Billing API
obligations per `shopify-token-acquisition-research.md` §9 are not evaluated
by this document) before any Task 005+ implementation-task-spec assumes a
distribution architecture, per
`../06-prompts/implementation-task-template.md`.

## 4. Options considered

| Option | Description | Recommended? |
| --- | --- | --- |
| **A — offline token only, status quo** | Merchant supplies a static token by whatever means available; connector implements no OAuth. | Not sufficient alone — no in-product path exists today for a new merchant without a pre-2026 legacy app (unchanged from 2026-07-07). Still used as the immediate-track storage mechanism (§3.1). |
| **B — OAuth before MVP, as originally framed** | Build OAuth without specifying who owns the app. | Superseded by the refined version in §3.2 — the original framing left the decision-critical ambiguity (§2) unresolved. |
| **C — dual path (2026-07-07 decision brief)** | Keep Option A's storage now; empirically test OAuth by hand later. | **Retained and extended** — this proposal is Option C's immediate track (§3.1), now with a sharper recommendation on *which* manual exchange to attempt first, informed by §2. |
| **B-refined, branch A (§3.2)** | One-store/private-customer/VAL-B2-evidence: a Custom Distribution app registered by a different organization than the one store it serves, standard OAuth, non-expiring offline token. | **May be valid for a single customer or VAL-B2 evidence-gathering only** — not proposed or valid as a many-unrelated-customer mechanism (corrected this revision; see §3.2). |
| **B-refined, branch B (§3.2)** | Many-unrelated-customers/commercial-product scope: Public distribution, or another officially-supported scalable route. | **Not evaluated by this document.** Must be separately researched and accepted by ChatGPT before any implementation assumes a multi-customer distribution mechanism. |

**Corrected this revision:** the first version of this table proposed a
single "vendor-owned Custom Distribution app, installed per customer" row as
"the target MVP architecture." That framing has been withdrawn — Custom
Distribution's own documented scope (§2) does not support a many-unrelated-
customer reading, so no single "B-refined" architecture is recommended as
final; see the A/B split above and §3.2.

No alternative is rejected outright; per `CLAUDE.md` §10, none of the options
above matches an existing `rejected-approaches-log.md` entry (checked — the
only on-topic entry, RA-003, rejects **public App Store distribution as a
Phase 1 architecture requirement**; this proposal does not reintroduce that
rejected approach — branch B above proposes only that Public distribution be
*evaluated*, not adopted, for the many-unrelated-customer scope, which is
consistent with RA-003's still-open revisit condition, not a repeat of the
rejected approach itself).

## 5. New correctness finding (not fixed by this document)

**[Fact]** The already-shipped `shopify_connector_readiness_check.py`
`REQUIRED_MVP_SCOPES` constant includes `read_fulfillments`. Per Shopify's
official access-scopes documentation (re-verified 2026-07-08), `read_fulfillments`
governs only the `FulfillmentService` resource, not read access to an order's
`Fulfillment`/`FulfillmentOrder` data (which is actually gated by `read_orders`
— already in the required set — and/or the `FulfillmentOrder`-family scopes).
Full citations in
[`shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md)
§3. **This document does not modify any code.** It is flagged here so ChatGPT
can decide whether to route a correction through the existing MBQ/task-spec
process (e.g. alongside the fulfillment domain's own task spec, which already
must fix the exact fulfillment API model per DEC-011/MBQ-42/MBQ-60) — no fix is
proposed or authorized by this proposal.

## 6. Implications for the setup wizard (not authorized here)

Whenever a setup wizard is separately gated and built, per
[`setup-ux-principles.md`](../02-product/setup-ux-principles.md) and the
official security guidance gathered this session
(`shopify-token-acquisition-notes.md` §4), it must:

- Never claim encryption of the stored token or client secret (unchanged
  `credential-connection-api-client-planning.md` posture — no official Shopify
  requirement mandates it either, per this session's negative-result check).
- Verify the OAuth callback's `hmac` parameter and reject the request outright
  on any check failure (mandatory, not best-effort).
- Pre-register the redirect URI; never accept an arbitrary one.
- Generate and verify a unique `state` value per authorization request (CSRF
  protection).
- Keep the client secret out of source code and logs; follow Shopify's
  documented six-step rotation sequence (new secret → deploy → re-request every
  stored token → revoke old secret) if/when the vendor-owned app's secret is
  rotated.
- Offer guided in-product connect with credential masking, inline validation,
  and a first-class reconnect/disconnect flow — not a "paste a long scope
  string" as the only path (per `setup-ux-principles.md` Principle 1 and the
  setup-flow principles).
- Show a named pass/fail readiness result, never a silent spinner or raw HTTP
  code (per Principle 2 and the existing readiness-check design).

None of this is implemented, designed at the field/screen level, or authorized
by this document — it is a constraint list for whichever future task builds
the wizard.

## 7. Implications for VAL-B2

- **VAL-B2 is not passed by this document.** It remains BLOCKED per
  `task-003-validation-results.md` until the immediate track (§3.1) is actually
  executed and observed to succeed, per
  [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md)'s exact
  evidence requirements.
- **DEC-021's deferral of VAL-B2 from the Task 003 → Task 004 gate is
  unchanged and still in force.** This document does not touch that deferral.
- Once §3.1 evidence exists, VAL-B2 should be re-attempted and its result
  recorded in `task-003-validation-results.md` exactly as that file's existing
  structure expects — this document does not pre-record a pass.

## 8. Implications for MBQ-05

- **MBQ-05 is not resolved by this document.** It remains open in
  `master-blueprint-open-questions.md`, exactly as DEC-021 already states.
- If ChatGPT accepts this proposal, MBQ-05's register row should be updated to
  reflect: (a) the "who owns the app" token-flow clarification (§2) is now the
  accepted framing for the **one-store/branch-A** evidence scope only — it is
  **not** an accepted framing for many-unrelated-customer distribution
  (branch B, unresolved, §3.2); (b) the exact vendor-organization
  registration, hosting, and wizard mechanics remain open, routed as
  task-spec detail per the existing MBQ-register convention (`TASK`/`SLICE`
  routing, matching how MBQ-05 was already routed by the 2026-07-05 final-MBQ
  closure plan); (c) branch B's Public-distribution-or-other-route evaluation
  remains a separate, unscoped, open item; (d) VAL-B2 must still separately
  pass before any customer-facing "connected" claim, unchanged from DEC-021
  §4's fail-closed requirement.
- **This document does not edit `master-blueprint-open-questions.md`** — that
  file is outside this session's allowed-files list. Any register update is
  for ChatGPT/a future session to apply, exactly as `credential-connection-api-client-planning.md`'s
  own acceptance pattern (AR-024) did.

## 9. Explicit non-claims

This document does not:

- Pass, fail, or waive VAL-B2.
- Resolve MBQ-05.
- Authorize OAuth implementation, a setup wizard, or any code, XML, CSV,
  manifest, security, migration, or CI file.
- Assert that the cross-organizational authorization-code-grant hypothesis in
  §2 has been empirically tested — it has not, by this or any prior session.
- Change DEC-004's accepted offline/unattended access model, DEC-021's VAL-B2
  deferral, or Task 002's shipped credential schema.
- Fix the `read_fulfillments` scope-naming finding in §5 — that remains
  unmodified code, flagged only.
- Make the connector customer-ready for self-serve new-merchant setup.
- **This proposal does not prove that Custom Distribution is valid for
  selling the connector to many unrelated customers.** Custom Distribution's
  officially documented scope is one store, or multiple stores in the same
  Plus organization — not many unrelated merchant organizations. The
  many-unrelated-customer/commercial-product question (§3.2 branch B) remains
  a separate, unevaluated, gated decision.
- Recommend a final MVP auth/distribution architecture — §3.2 proposes a
  candidate split (branch A / branch B), not a recommended final design.

## 10. Rollback / revisit triggers

- **Rollback:** revert this docs PR. The project returns to the pre-existing
  state: VAL-B2 BLOCKED per DEC-021, MBQ-05 open per its current register row,
  no code/schema/runtime effect of any kind (this proposal touches Markdown
  documentation only).
- **Revisit if:** (a) the §3.1 immediate-track attempt is actually run and
  either succeeds or fails — either outcome should be recorded and may change
  this proposal's confidence level; (b) Shopify publishes an official worked
  example that confirms or denies the §2 cross-organizational hypothesis
  directly; (c) Shopify changes the client-credentials/authorization-code-grant
  organizational-ownership rule itself; (d) a future fulfillment-domain task
  spec resolves which scope actually governs fulfillment reads (§5), which may
  warrant a corresponding correction to `REQUIRED_MVP_SCOPES`; (e) ChatGPT
  authorizes a dedicated research/decision pass on §3.2 branch B (the
  many-unrelated-customer/commercial-product distribution question), which
  would produce its own separate DEC, not an amendment to this one.

## 11. Evidence / references

- Shopify, "Generate access tokens for custom apps in the Shopify admin" —
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/generate-app-access-tokens-admin
  — Accessible — 2026-07-08.
- Shopify, "Client credentials grant" —
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant
  — Accessible — 2026-07-08.
- Shopify, "Authorization code grant" —
  https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/authorization-code-grant
  — Accessible — 2026-07-08.
- Shopify Developer Community (staff reply) —
  https://community.shopify.dev/t/custom-app-access-token-with-oauth-flow/28525
  — Accessible — 2026-07-08 (informal, not primary documentation).
- Shopify Developer Community (staff reply) —
  https://community.shopify.dev/t/custom-app-credentials/27460/9 — Accessible
  — 2026-07-08 (informal, not primary documentation).
- Shopify, "Access scopes" —
  https://shopify.dev/docs/api/usage/access-scopes — Accessible — 2026-07-08.
- Shopify, "Select a distribution method" (Custom vs. Public distribution
  scope) —
  https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
  — Accessible — 2026-07-08.
- Full inventory: [`../01-research/shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md)
  and [`../01-research/shopify-token-acquisition-research.md`](../01-research/shopify-token-acquisition-research.md).
