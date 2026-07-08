# DEC-023 — Token Acquisition Path and VAL-B2 Closure (Proposal)

## Status

**Proposed, not accepted.** Prepared 2026-07-08. Does not resolve MBQ-05. Does
not pass VAL-B2. Does not authorize OAuth implementation, a setup wizard, or
any code change. Requires explicit ChatGPT review and acceptance before any
part of it becomes binding, per `CLAUDE.md` §2/§6/§8.

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

## 2. What is newly known: the "who owns the app" axis

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
- **[Inference]** The connector's real choice is not "manual token vs. OAuth"
  in the abstract — it is **who registers the Shopify app**. A Custom
  Distribution app registered **once, by the connector vendor's own
  organization**, and installed by each customer on *their own, different*
  organization's store, sits in the cross-organizational scenario that
  supports a non-expiring offline token compatible with the existing
  `token_variant='offline_custom_app'` storage shape, with **zero schema
  change**. This is also the shape most third-party Shopify connectors
  (including this project's own studied competitors) already use, and matches
  Shopify's own framing of ERP integrations as standalone-app-eligible.
- **This is evidence-backed, not officially demonstrated end-to-end.** No
  single `shopify.dev` page shows this exact combination (vendor-owned Custom
  Distribution app + standalone authorization-code-grant + non-expiring
  offline token) working, start to finish. It remains an **empirically
  unverified hypothesis**, materially stronger than the 2026-07-07 "genuinely
  unclear either way" status, but not yet a proven fact.

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

### 3.2 Later track — the real MVP token-acquisition architecture (Task 005+, separately gated)

**Recommend, for future implementation-planning review (not authorized by this
document):** build the standard OAuth authorization-code-grant flow into the
connector itself, using **one Shopify app definition registered by the
connector vendor's own organization** (Custom Distribution), installed by each
customer on their own store via an install link; each customer's own Odoo
instance hosts the redirect/callback controller at its own `web.base.url` (no
central Adams-hosted server required); a non-expiring offline token is
requested (`expiring` omitted/`0`), stored via the **existing**
`token_variant='offline_custom_app'` shape with no schema migration.

This is a refinement of Option B (from the 2026-07-07 decision brief), not a
new option — it resolves the "does OAuth even work for this shape of app"
ambiguity that made Option B's feasibility uncertain, by identifying the
specific app-ownership arrangement under which it is expected to work.

**Not decided by this proposal:** exact controller/hosting mechanics, exact
install-link distribution mechanism, the Shopify Partner organization
under which the vendor-owned app is registered, whether the vendor-owned app
is Custom or Public distribution, and the exact setup-wizard screens — all of
these remain Task 005+ implementation-task-spec detail, to be written using
`../06-prompts/implementation-task-template.md` once a separate ChatGPT gate
authorizes that work.

## 4. Options considered

| Option | Description | Recommended? |
| --- | --- | --- |
| **A — offline token only, status quo** | Merchant supplies a static token by whatever means available; connector implements no OAuth. | Not sufficient alone — no in-product path exists today for a new merchant without a pre-2026 legacy app (unchanged from 2026-07-07). Still used as the immediate-track storage mechanism (§3.1). |
| **B — OAuth before MVP, as originally framed** | Build OAuth without specifying who owns the app. | Superseded by the refined version in §3.2 — the original framing left the decision-critical ambiguity (§2) unresolved. |
| **C — dual path (2026-07-07 decision brief)** | Keep Option A's storage now; empirically test OAuth by hand later. | **Retained and extended** — this proposal is Option C's immediate track (§3.1), now with a sharper recommendation on *which* manual exchange to attempt first, informed by §2. |
| **B-refined (this proposal, §3.2)** | Vendor-owned Custom Distribution app + standard OAuth, non-expiring offline token, per-customer Odoo-hosted redirect. | **Proposed as the target MVP architecture**, gated on (a) ChatGPT acceptance of this direction and (b) a separate implementation-gate act before any code is written. |

No alternative is rejected outright; per `CLAUDE.md` §10, none of the options
above matches an existing `rejected-approaches-log.md` entry (checked — the
only on-topic entry, RA-003, rejects **public App Store distribution as a
Phase 1 architecture requirement**, which is not what §3.2 proposes — §3.2
proposes Custom Distribution, not Public — no rejected approach is
re-introduced here).

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
  reflect: (a) the "who owns the app" clarification is now the accepted
  framing for future implementation planning; (b) the exact vendor-organization
  registration, hosting, and wizard mechanics remain open, routed as
  task-spec detail per the existing MBQ-register convention (`TASK`/`SLICE`
  routing, matching how MBQ-05 was already routed by the 2026-07-05 final-MBQ
  closure plan); (c) VAL-B2 must still separately pass before any
  customer-facing "connected" claim, unchanged from DEC-021 §4's fail-closed
  requirement.
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
  warrant a corresponding correction to `REQUIRED_MVP_SCOPES`.

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
- Full inventory: [`../01-research/shopify-token-acquisition-notes.md`](../01-research/shopify-token-acquisition-notes.md)
  and [`../01-research/shopify-token-acquisition-research.md`](../01-research/shopify-token-acquisition-research.md).
