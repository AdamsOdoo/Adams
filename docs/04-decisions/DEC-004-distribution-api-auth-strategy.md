# DEC-004 — Distribution / API / Authentication Strategy (AR-002)

> **Accepted architecture decision record.** ChatGPT accepted this decision on
> **2026-07-02**, after PR #60 review (Fable's minor-change pass applied and merged in
> PR #60). It resolves **AR-002** in
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md), but does
> **not** by itself authorize implementation and does **not** change DEC-003.

## Status

**Accepted by ChatGPT.** Acceptance date: **2026-07-02**. Not implementation-
authorizing on its own — see *No implementation authorized* below.

## Date

2026-07-02.

## Scope

**AR-002 only** — Phase 1 / Early Access **distribution model**, **Shopify API
strategy**, and **authentication/token strategy**. Does **not** decide AR-003
(orchestration/queue — DEC-005), AR-005 (binding/dedup — DEC-006), AR-004 (module
boundaries), AR-006 (retry/idempotency taxonomy), AR-007 (inventory design), or AR-008
(fulfilment design). Does **not** change DEC-003 MVP product scope.

## Decision summary

Phase 1 / Early Access uses **non-public custom-app / Early Access distribution** — not
a public App Store listing — as the installation path; the **Shopify Admin GraphQL
API** as the primary/default API surface; and an **unattended/background (offline)
access model** with **masked storage, least-privilege scopes, and an inline
test-connection/readiness check** in the Odoo setup wizard. The **exact custom-app
creation surface** — a merchant Admin-created custom app, or a Partner/Dev-Dashboard
custom-distribution app — and its corresponding **token-acquisition mechanics** (an
Admin-generated token for the former; OAuth/token-exchange-style mechanics for the
latter) are an **implementation-planning sub-choice**, not fixed by this record. Public
App Store distribution, the public-app OAuth flow, and the Billing API are
**deferred**, not designed against, for Phase 1.

## Recommended option

**AR-002 Option B — custom/private app, offline token, GraphQL-first** (per
[`ar-002-distribution-api-framing.md`](../03-architecture/ar-002-distribution-api-framing.md)
and the RB-14 Part 2 narrowing in
[`rb14-decision-candidate-brief.md`](../03-architecture/rb14-decision-candidate-brief.md)).

- **Distribution:** **non-public custom-app / Early Access distribution**, installed
  to one store (single-store MVP, per DEC-003) — not a public App Store listing. The
  specific **creation surface** (a merchant Admin-created custom app, or a
  Partner/Dev-Dashboard custom-distribution app) is left to implementation planning —
  both are non-public and both satisfy this decision. `[Official fact]` custom/
  Admin-created apps get protected-customer-data access **"Always available"** — no
  App-Store review gate, no approval wait (`rb14-part2-open-question-resolution.md`,
  RQ-002-2).
- **API surface:** **GraphQL Admin API as the primary/default**, because `[Official
  fact]` REST is "legacy as of October 1, 2024" and `[Official limitation]` GraphQL is
  signalled as **"the only supported API over the long term"** — a **direction +
  longevity** case, **not** a prohibition (`[Official fact]` custom apps may still use
  REST product APIs under 100 variants, but this is **not** relied upon as a design
  basis here). GraphQL is required regardless for the `productSet` full-state
  export/update path, the new 2,048-variant product model, and the 17-mutation
  `@idempotent` surface that DEC-003's correctness spine depends on.
- **Auth/token model:** the **offline (unattended/service-to-service) access model**,
  stored **masked** behind Odoo access rights and **field-level `groups`** on the
  credential field(s), with **least-privilege scope selection** surfaced in the setup
  wizard. The **token-acquisition mechanics follow whichever custom-app creation
  surface implementation planning selects**: an **Admin-generated token, installed on
  generation**, for a merchant Admin-created custom app; or **OAuth/token-exchange-
  style mechanics** if the Partner/Dev-Dashboard custom-distribution path is chosen
  instead — both stay within the offline/unattended model this record fixes, including
  any non-expiring-vs-expiring-with-90-day-rotation sub-choice. **AR-002 fixes the
  offline/unattended access model and masked/least-privilege storage; it does not need
  to decide the exact token-acquisition mechanics yet.**
- **Bulk Operations:** used only as an **internal mechanism** (never user-facing, per
  DEC-003) for safe/resumable large backfills where a single GraphQL request would
  exceed practical size/time limits; exact triggering thresholds are left to
  implementation planning, not decided here.

## Rejected / deferred options

| Option | Disposition | Why |
| --- | --- | --- |
| **A — Public App Store app, OAuth-first, GraphQL-first** | **Deferred to a later, ChatGPT-gated phase** — not rejected outright, but **not** a Phase 1 architecture target | Carries the full App-Store burden (3 mandatory compliance webhooks, protected-data **"Requires review"**, Billing API, Built-for-Shopify performance thresholds) that DEC-003 explicitly defers; going public is a distribution decision this record does not make |
| **C — GraphQL + REST hybrid** | **Rejected as the Phase 1 default** (proposed; see `rejected-approaches-log.md`) | `[Official fact]` REST is legacy and GraphQL is signalled sole-long-term; a hybrid adds GID↔numeric-ID reconciliation cost (feeds AR-005) for no durable benefit, and is a dead end if distribution ever goes public (GraphQL-only) |
| **D — REST-heavy** | **Rejected** (proposed; see `rejected-approaches-log.md`) | No current evidence for it; the 2,048-variant product model degrades off the GraphQL product APIs; the only real-world precedent (VentorTech) migrated **away** from REST |

## Evidence used

All dated **2026-07-01** (RB-14 Part 1/2) unless noted; no new Shopify page was
re-fetched this sprint (see
[`ar002-ar003-ar005-evidence-refresh.md`](../03-architecture/ar002-ar003-ar005-evidence-refresh.md)).

- `[Official fact]` "The REST Admin API is a legacy API as of October 1, 2024" +
  "Starting April 1, 2025, all new public apps must be built exclusively with the
  GraphQL Admin API" (mandate scoped to **new public apps**) —
  `shopify.dev/docs/api/admin-rest`.
- `[Official fact]` "Custom apps built on REST that do not need to support more than
  100 variants can continue to use the deprecated REST product APIs," alongside
  `[Official limitation]` "the GraphQL API will be the only supported API over the
  long term" — `shopify.dev/changelog/deprecation-timelines-related-to-new-graphql-product-apis`.
- `[Official fact]` protected-customer-data access matrix: public **"Requires
  review"**; custom / Admin-created custom **"Always available"** —
  `shopify.dev/docs/apps/launch/protected-customer-data`.
- `[Official fact]` the three mandatory compliance webhooks are required **"for apps
  listed on the Shopify App Store"** — `.../apps/build/compliance/privacy-law-compliance`.
  `[Open question — not assumed absent]` whether custom apps must implement them or
  are bound by Level 1/2 obligations regardless of distribution.
- `[Official fact]` two token-acquisition paths (token exchange / authorization code
  grant); offline tokens are **non-expiring** (until uninstall/secret revocation) or
  **expiring** (1h access + 90-day rotating refresh) — `.../access-tokens/offline-access-tokens`.
- `[Official limitation]` `productSet` **reconciles list fields by deleting omitted
  entries** (full-state write) —
  `shopify.dev/docs/api/admin-graphql/latest/mutations/productSet`.
- `[Official fact]`/`[Official limitation]` `inventorySetQuantities` /
  `inventoryAdjustQuantities` / `refundCreate` require `@idempotent` as of 2026-04; the
  supporting set is a **fixed list of 17 mutations**; server-side dedup **TTL = 24
  hours**; **no general/all-mutation idempotency** —
  `.../usage/implementing-idempotency`.
- `[Competitor demonstrated]` every studied connector uses a custom Shopify app;
  VentorTech migrated REST→GraphQL (v2.0.0, 2026-01-23) and shipped 2026-04
  `@idempotent` compliance (v2.1.4) — competitor evidence, an **input**, not a fact.
- **Below-Tier-1 / not relied upon:** any claim that admin-created custom apps are
  auto-granted `read_all_orders` — not used as a decision input; stays an open
  question in `ar-002-distribution-api-framing.md`.

## Risks

1. **Custom-app privacy/compliance obligations are genuinely unconfirmed** — the
   review *gate* is removed for custom apps, but substantive Level 1/2 obligations and
   webhook duties are **not stated as absent**. Risk: building as if "custom = no
   obligations" and being wrong later.
2. **`productSet` is delete-on-omit** — a missing/incorrect diff on export/update is a
   **data-loss** risk, not a UX inconvenience.
3. **Token security** — an offline token is long-lived (non-expiring variant) or needs
   rotation (expiring variant); mishandled storage/logging is a credential-leak risk.
4. **GraphQL cost/throttling** — calculated-cost model + bulk-operation needs add
   operational complexity the setup/health UX must reflect honestly.
5. **REST-under-100-variants latitude could be misread as "REST is fine"** and pull
   the implementation back toward a REST-heavy design by accretion.

## Mitigations

1. Treat custom-app privacy/data-subject obligations as **conservatively applicable**
   (not exempt) until Shopify officially states otherwise; design credential/consent
   handling defensively rather than assuming the review gate implies no duty.
2. **Mandatory preview/dry-run diff before any `productSet` write** (already a DEC-003
   guardrail) — this record reaffirms it as an AR-002 API-mechanism requirement, not
   optional polish.
3. Store the token **masked**, behind **field-level `groups`**, never logged; plan a
   reconnect/rotation UX path regardless of which token variant implementation
   planning ultimately selects.
4. Surface GraphQL cost/throttle state as an **honest, named** health indicator (not a
   raw error) in the command center (AR-003/DEC-005 territory, noted here as a shared
   requirement).
5. Treat the REST product-API allowance as a **narrow, documented exception**, not a
   general license — GraphQL remains the default for every operation that has a
   GraphQL path.

## UX implications

- Setup wizard is a **multi-step custom-app credential/scope flow** (not one-click
  OAuth): guided app creation, masked token entry, inline scope validation, and a
  **test connection / pre-flight readiness check** (scopes, HTTPS/`web.base.url`,
  webhook reachability) before the store is marked connected.
- Because access is **"Always available"** for custom apps, the friction is **wizard
  steps, not approval latency** — the wizard should say so, not imply a review wait.
- The controlled product export/update path must render a **preview/dry-run diff**
  before any full-state write, keyed off the binding (DEC-006) so the operator sees
  exactly what `productSet` will create/update/delete-by-omission.
- If an expiring offline token is later selected, the reconnect-on-refresh-failure
  path must be a **named, first-class** flow, not a silent failure.

## Security implications

- Least-privilege scope selection at setup time; token stored masked, never logged, in
  a field protected by **field-level `groups`** (not general employee visibility).
- No AR-002 credential-handling design may rely on `sudo()` to cross store/record-rule
  boundaries — `[Official source-code fact]` `sudo()` "could cause data access to
  cross the boundaries of record rules" (feeds DEC-006's per-store isolation rule too).
- Because custom-app compliance-webhook/L1-L2 obligations are **open, not absent**,
  security/privacy design should not assume they can be skipped.

## Data-safety implications

- `productSet` delete-on-omit makes the **preview/dry-run + reliable binding
  (DEC-006)** a correctness requirement for every controlled export/update.
- The 17-mutation `@idempotent` surface + 24-hour dedup TTL must be used for every
  inventory/location/refund write in scope; everything else needs
  connector-designed idempotency (feeds AR-006, not decided here).
- Bulk Operations, if used internally, must be resumable/safe for partial failure —
  an internal mechanism requirement, not a user-facing feature (DEC-003 unchanged).

## Performance implications

- GraphQL calculated-cost model (points; ≤1,000/query) requires cost-aware batching
  and honest throttle-state surfacing; large reads/writes may need Bulk Operations
  internally.
- REST's leaky-bucket + `429`/`Retry-After` is **not** the primary design target since
  GraphQL is the default surface, but any narrow REST usage (product APIs <100
  variants, if ever used) must respect it too.

## What this unlocks

- Implementation planning (once ChatGPT authorizes the phase-exit, per
  `../05-qa/quality-feedback-loop.md` §10) for: the store-connection/credential setup
  wizard, the GraphQL client + `productSet` preview/diff mechanism, and least-privilege
  scope selection.
- AR-003 (DEC-005) and AR-005 (DEC-006) can proceed on a settled API/auth/distribution
  premise (custom app, GraphQL-first, offline token) instead of framing against an
  open fork.
- The Phase 1 / Early Access product narrative (setup UX, docs) can be written against
  a fixed distribution model.

## What remains blocked

- **Public App Store packaging, OAuth authorization-code public-app flow, and the
  Billing API** — explicitly deferred, not designed against.
- **Whether custom apps must implement the compliance webhooks / are bound by Level
  1/2 obligations** — open; must be resolved or conservatively handled before any
  compliance-relevant code is written.
- **Exact custom-app creation surface** (merchant Admin-created vs. Partner/
  Dev-Dashboard custom-distribution) **and its corresponding token-acquisition
  mechanics** (Admin-generated token vs. OAuth/token-exchange-style, and any
  non-expiring-vs-expiring-with-rotation variant) — left to implementation planning
  within the non-public/offline access model this record fixes.
- **Module boundaries (AR-004), binding data model (AR-005/DEC-006), orchestration
  substrate (AR-003/DEC-005), and retry/idempotency taxonomy (AR-006)** — separate
  decisions.
- **All implementation** — no code, no Odoo module, until ChatGPT opens the
  implementation gate (`CLAUDE.md` §5; `quality-feedback-loop.md` §10).

## Revisit triggers

- Shopify officially states the GraphQL-only mandate (or a REST EOL date) extends to
  custom/private apps.
- Shopify officially states custom apps **must** implement the compliance webhooks or
  are bound by Level 1/2 obligations regardless of distribution (would sharpen, not
  reverse, this decision).
- Product strategy decides to pursue public App Store distribution for Phase 2+ (routes
  through a new decision record, not a silent amendment here).
- Any Tier-1 evidence that materially changes the `productSet`/`@idempotent` surface
  this record relies on.

## No implementation authorized

**Acceptance of this architecture decision does not by itself authorize
implementation.** This record does not create code, an Odoo module, or any file
outside `docs/03-architecture/**` and `docs/04-decisions/**`. The no-code gate
(`CLAUDE.md` §4–§5) remains in force until ChatGPT approves the Phase 1 research-phase
exit (AR-002/003/005 acceptance is one of several required criteria —
`../05-qa/quality-feedback-loop.md` §10) and opens a dedicated implementation gate.
