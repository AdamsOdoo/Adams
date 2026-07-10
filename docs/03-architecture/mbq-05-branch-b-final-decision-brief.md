# MBQ-05 Branch B — Final Distribution / Auth Decision Brief

> **Status: [Recommendation] per `CLAUDE.md` §8 — Recommended for ChatGPT
> review, NOT accepted, NOT a distribution decision.** Docs-only. Prepared
> 2026-07-10 by a dedicated MBQ-05 branch B research/decision-preparation
> session (Fable acting as strategic auditor / architecture decision
> researcher, not as implementation worker), per the AR-039 session's own
> recommendation (§8 of
> [`mbq-05-branch-b-distribution-auth-decision-brief.md`](./mbq-05-branch-b-distribution-auth-decision-brief.md))
> and the "MBQ-05 branch B parallel authorization" item ChatGPT was asked
> to separately consider. This document supersedes nothing that brief
> already established (branch B does not block Task 011; RA-003 is
> respected, not revisited-by-stealth) — it **completes** that brief's own
> "recommended next action" by evaluating the full B-1…B-4 candidate set
> in the depth needed for a DEC-026 decision, using a fresh 2026-07-10
> official-source research pass (gap-fill on Built for Shopify, Partner
> Program Agreement app-count limits, App Store listing/quality-check
> obligations, OAuth mechanics, and Billing API details) plus an
> adversarial verification pass on the five highest-stakes claims.
>
> **This brief does not itself decide branch B, does not select a
> distribution method, does not authorize OAuth/wizard/billing/webhook
> code of any kind, does not weaken DEC-023's accepted branch A scope or
> RA-003's rejection, and does not affect Task 011 (or any other
> implementation task) in any way.** The companion proposal
> [`../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md`](../04-decisions/DEC-026-distribution-auth-branch-b-proposal.md)
> is explicitly **Proposed for ChatGPT review**, not accepted.

## 0. Relationship to prior work (read first)

This brief builds directly on, and does not contradict or duplicate:

- [`mbq-05-branch-b-distribution-auth-decision-brief.md`](./mbq-05-branch-b-distribution-auth-decision-brief.md)
  (2026-07-10, AR-039 session) — established that branch B does **not**
  block Task 011, defined the B-1/B-2/B-3/B-4 candidate set, and
  recommended authorizing a dedicated evaluation task. That brief's §1–§3
  and §9 (non-authorizations) remain the governing frame; this document
  is the "dedicated task" it recommended.
- [`DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md)
  (Accepted in limited scope, 2026-07-08) — accepted Custom Distribution
  **only** for one-store/same-Plus-org/private-customer/VAL-B2-evidence
  purposes ("branch A"), and explicitly left the many-unrelated-customer
  question ("branch B") as a separate, gated decision. Nothing here
  changes DEC-023's accepted scope.
- [`rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) RA-003
  — rejected public App Store distribution **as a Phase 1 architecture
  requirement**, with an explicit revisit condition ("a future,
  ChatGPT-approved decision to pursue public App Store distribution for
  Phase 2+"). This brief evaluates public distribution strictly as a
  Phase 2+ candidate under that revisit condition — it does not adopt it
  and does not reopen RA-003.
- [`shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)
  — the 2026-07-10 official-source capture file already contains the
  distribution/PCD/billing facts this brief's evidence rests on for the
  parts fetched by the prior session; §6 below captures the **new**
  gap-fill excerpts fetched by this session.

## 1. Executive recommendation

**[Recommendation — not a decision]** Based on the full evidence set
below, the following recommendation is offered to ChatGPT. It is a
recommendation, not a decision — only ChatGPT can promote it to Accepted
(per `CLAUDE.md` §8, §10).

> Adopt, as the eventual answer to MBQ-05 branch B, a **hybrid trajectory
> functionally equivalent to candidate B-4**, structured as follows:
>
> 1. **Keep DEC-023 branch A (Custom Distribution) exactly as already
>    accepted** — narrow, one-store/same-Plus-org/private-customer/
>    VAL-B2-evidence use only. Nothing about this recommendation widens
>    that acceptance.
> 2. **Designate Public distribution, with Limited Visibility as the
>    initial listing setting (candidate B-1), as the target scalable
>    architecture** for the many-unrelated-commercial-customer / MVP-later
>    use case that branch B was created to answer. The B-1-vs-B-2
>    (limited vs. fully visible) choice is a go-to-market/marketing
>    decision, not an architecture decision — it can be made later,
>    independent of this recommendation, without any new research.
> 3. **Do not adopt B-3 (one Custom Distribution app per client, at
>    commercial scale) as the standing, sole answer for many unrelated
>    customers.** Its scalability ceiling is officially undocumented (not
>    proven safe, not proven unsafe); it has zero Shopify-native billing
>    mechanism; and its per-client operational burden (manual app
>    registration + manually-completed OAuth exchange per customer) is
>    unquantified by any official or first-party data point. B-3 remains
>    valid only at the DEC-023 branch-A scale it is already accepted for.
> 4. **Treat this as Phase 2+ scope, per RA-003's own revisit condition —
>    not an MVP decision.** Adopting this recommendation authorizes
>    nothing by itself: no OAuth implementation, no setup wizard, no
>    billing integration, no compliance webhooks. It does not affect
>    Tasks 011–015, which are distribution-agnostic by construction (§5).
>
> This recommendation is offered because it is the only evaluated
> combination that (a) matches an officially-documented, Shopify-endorsed
> mechanism for "many unrelated merchants" (§2, §4), (b) does not ask
> ChatGPT to bet the commercial-scale architecture on an undocumented
> scalability ceiling (B-3 alone), and (c) does not require abandoning the
> already-accepted, working DEC-023 branch A path for existing/pilot
> customers. It is **not** a low-cost recommendation — §1.1 below states
> plainly what adopting it would require before implementation, and it is
> explicitly not ready for implementation authorization today.

### 1.1 What adopting this recommendation would still require before any code

Even if ChatGPT accepts this recommendation in full, the following remain
**separately gated, not authorized by this brief or by DEC-026**:

1. A dedicated DEC resolving the **MBQ-04 encryption-posture tension**:
   PCD Level 2's review-enforced obligations (encryption at rest/in
   transit/backups, retention limits, staff-access logging, incident
   response) versus the already-accepted MBQ-04/Task 002 credential
   posture (plain `Char` field behind `groups=` ACLs, explicit no-
   encryption-claim). This must be resolved by its own DEC, without
   silently weakening the accepted Task 002 record (`CLAUDE.md` §10).
2. ChatGPT's answer to **OP-23 / Q27** (Lite/Full packaging mechanism —
   per-store domain-enablement flags vs. separate module sets/licensing),
   so any Shopify `AppSubscription` plan mapping can be concretely
   designed rather than assumed.
3. An explicit **scope clarification of DEC-023's branch-A acceptance**:
   whether "a single pilot customer" (DEC-023's own singular language)
   is meant to extend to multiple simultaneous pilot/private customers as
   ongoing practice — a gap this session's candidate evaluations
   surfaced (§7.4) that is distinct from, and prerequisite to, treating
   the hybrid's near-term half as routine.
4. A separate ChatGPT act lifting RA-003's Phase-1 deferral for the
   specific engineering surfaces this recommendation eventually unlocks
   (OAuth implementation, setup wizard OAuth-connect step, compliance
   webhooks, Shopify billing integration) — this brief evaluates, it does
   not request that act.
5. Sourcing the Shopify Partner Program Agreement's fee schedule/revenue-
   share terms and the not-yet-fetched "Enforcement of Shopify's Partner
   Program Policies" page (§6.2, §9) before any commercial model is
   finalized.

## 2. Candidate comparison table

| Dimension | **B-1** Public, limited visibility | **B-2** Public, fully visible | **B-3** Per-customer Custom Distribution | **B-4** Hybrid (B-3 now + B-1/B-2 later) |
| --- | --- | --- | --- | --- |
| Officially designed for "many unrelated merchants" | **Yes** [Fact] | **Yes** [Fact] | **No** — documented scope is one store or same-Plus-org only [Fact] | Only via its B-1/B-2 half [Fact] |
| App review required | Yes [Fact] | Yes [Fact] | No [Fact] | No for near-term half; Yes once public half exists [Fact] |
| Distribution choice reversible | **No — permanent** [Fact] | **No — permanent** [Fact] | **No — permanent** [Fact] | **No — both halves permanent; no migration path between them** [Fact] |
| PCD Level 1 / Level 2 | Requires review / Requires review [Fact] | Requires review / Requires review [Fact] | Always available / Always available (true Custom-Distribution apps) [Fact] | Both regimes, permanently, once public half exists [Fact + Inference] |
| Mandatory compliance webhooks | Yes (3, 30-day response) [Fact] | Yes (3, 30-day response) [Fact] | No Shopify-mandated webhook duty [Fact] | Only for the public half, once it exists [Fact] |
| Shopify-provided billing available | Yes (App Pricing or Billing API) [Fact] | Yes (App Pricing or Billing API) [Fact] | **No — categorically barred, no carve-out** [Fact] | Yes for public half only; off-platform forever for the custom-app population [Fact] |
| Ongoing "quality check" regime (7-day/30-day) | Yes [Fact] | Yes [Fact] | No | Yes, for the public half, once it exists [Fact] |
| Built for Shopify eligible | Yes, after traction (optional) [Fact] | Yes, after traction (optional) [Fact] | No (denominated in App Store metrics it cannot accrue) [Inference] | Only via the public half, once launched [Inference] |
| Marginal operational cost per new customer | ~0 after launch [Inference] | ~0 after launch [Inference] | Linear — per-client app registration + manual OAuth [Fact + unquantified] | Linear for the custom-app population; ~0 for the public-app population [Inference] |
| Discoverability | Listing exists, not indexed/searchable [Fact] | Indexed/searchable (App Store search, category pages) [Fact] | None — no App Store presence [Fact] | Split between the two populations [Fact] |
| Scalability ceiling documented? | No ceiling stated [Fact] | No ceiling stated [Fact] | **Officially undocumented — neither proven safe nor unsafe** [Fact, absence-of-evidence] | Ceiling question only matters for the custom half; unresolved there too |
| Fits current MVP scope | No — Phase 2+ (RA-003) [Fact] | No — Phase 2+ (RA-003) [Fact] | Yes, at DEC-023's already-accepted scale only [Fact] | Near-term half: yes (already covered by DEC-023); public half: no |
| Does it block Task 011 / current implementation gate | No [Fact, per the prior brief §2/§6] | No | No | No |
| Decision readiness (this brief) | Evaluated, not ready for adoption alone — see §7.1 | Evaluated, not ready — B-1-vs-B-2 is a separate GTM call, see §7.2 | Evaluated, not ready as the sole/standing answer at commercial scale — see §7.3 | Evaluated; this brief's [Recommendation] — see §1, §7.4 |

## 3. Official-source evidence

All items below are re-verified or newly fetched **2026-07-10**, official
sources only (`shopify.dev`, `help.shopify.com`, `shopify.com/partners`),
unless marked otherwise. Full excerpt captures are in
[`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)
(prior session) and §6 below (this session's new gap-fill).

### 3.1 Distribution mechanics (re-confirmed, unchanged since 2026-07-08/10)

- **[Fact]** "You can't change the distribution method after you select
  it, so make sure that you understand the different capabilities and
  requirements of each type." — `shopify.dev/docs/apps/launch/distribution`,
  Accessible, 2026-07-10. Adversarially re-verified this session (§8,
  claim 1) — **CONFIRMED**, no self-service or Shopify-supported
  conversion path exists between Public and Custom distribution.
- **[Fact]** "Select this method to make your app public. You can
  distribute or sell your app to many merchants through the Shopify App
  Store using this method." vs. "Select this method if you've built a
  custom app that you want to distribute to one store or multiple stores
  on the same Plus organization using a link." —
  `shopify.dev/docs/apps/launch/distribution/select-distribution-method`,
  Accessible, 2026-07-10.
- **[Fact]** "Can't use the Billing API to charge merchants" is a stated
  limitation of Custom distribution (and of "Shopify admin"
  apps) — `shopify.dev/docs/apps/launch/distribution`, Accessible,
  2026-07-10. Adversarially re-verified this session (§8, claim 2) —
  **CONFIRMED**, no exception or carve-out found anywhere in official
  docs for custom/custom-distribution apps.
- **[Fact]** The legacy "unpublished app" type (a public app installable
  by many merchants with no review) was deprecated **2019-12-09**, not a
  recent change — "An unpublished app was a type of public app that one
  or many merchants could install and had all the same functionality as
  other public apps. However, the app didn't require any approval from
  Shopify." — `shopify.dev/docs/apps/launch/distribution`, Accessible,
  2026-07-10 (this corrects the existing brief's framing, which cited a
  help-center FAQ without the exact deprecation date; both sources now
  agree). Adversarially re-verified this session (§8, claim 3) —
  **CONFIRMED**: no review-free route to many unrelated merchants exists
  today.
- **[Fact]** Since **2026-01-01**, new custom apps can no longer be
  created directly in the Shopify admin ("legacy" custom apps); existing
  ones continue working; all new custom-app creation is now via the Dev
  Dashboard — `changelog.shopify.com/posts/legacy-custom-apps-can-t-be-
  created-after-january-1-2026`, Accessible, 2026-07-10 (official
  changelog, published 2025-10-30). This is unchanged from the AR-039
  session's finding, now sourced to the primary changelog entry directly.

### 3.2 Protected Customer Data (PCD) — refined this session

- **[Fact]** For **true Custom-Distribution apps** (built via
  Partner/Dev Dashboard, distributed via install link — the DEC-023
  branch-A shape), PCD Level 1 and Level 2 are both **"Always
  available"** — `shopify.dev/docs/apps/launch/protected-customer-data`,
  Accessible, 2026-07-10. Adversarially re-verified this session (§8,
  claim 5) — **CONFIRMED**, with one important nuance (below).
- **[Nuance, confirmed this session]** Shopify's PCD table distinguishes
  **three** app categories, not two: "Public app" / "Custom app"
  (= Custom Distribution) / "Admin created custom app" (legacy, built
  directly in a merchant's own admin). For "Admin created custom app,"
  Level 1 is "Always available" but **Level 2 "Varies by plan"** — per
  `help.shopify.com/en/manual/apps/app-types/custom-apps#custom-level2-
  pii-app`: "To access Custom Level 2 PII apps, your store must be on
  the Grow plan or higher." Because new admin-created custom apps can no
  longer be created (§3.1), this plan-gate applies only to a shrinking
  population of legacy apps, not to any new B-3/branch-A registration —
  but it must not be silently conflated with true Custom-Distribution
  apps, which have no such plan-gate.
- **[Fact]** For **Public apps**, both Level 1 and Level 2 "Require
  review" — Level 1 needs a Partner Dashboard access request; Level 2
  additionally requires "Participate in data protection reviews," plus
  the full obligations list (9 Level-1 items + 7 Level-2 items):
  encrypt data at rest/in transit, encrypted backups, retention limits,
  test/prod data separation, staff-access limits + an access log, a
  data-loss-prevention strategy, an incident-response policy —
  `shopify.dev/docs/apps/launch/protected-customer-data`, Accessible,
  2026-07-10 (unchanged from the prior session's capture).

### 3.3 App Store listing, review, and ongoing obligations — new this session

- **[Fact]** Mandatory App Store Listing content (§4 of the requirements
  checklist): accurate, complete pricing confined to the "Pricing
  details" section (never in images/icon); truthful copy with no false
  guarantees; unique, real-UI screenshots (no logo-only/desktop-chrome
  images); a demo screencast; working test credentials; and a **current
  emergency developer contact kept in the Partner Dashboard** —
  `shopify.dev/docs/apps/launch/shopify-app-store/app-store-requirements`,
  Accessible, 2026-07-10.
- **[Fact]** "Shopify's app requirements are the same for both fully
  visible and limited visibility public apps." — `shopify.dev/docs/apps/
  launch/app-store-review/review-process`, Accessible, 2026-07-10. **B-1
  and B-2 carry an identical compliance/review bar; they differ only in
  discoverability.**
  - **[Open question]** No official page states a numeric review-
    turnaround SLA — only the Draft → Submitted → Paused/Reviewed →
    Published status pipeline is documented, with no committed
    timeframe.
- **[Fact]** A **10-point maximum Lighthouse-score reduction** is a
  **baseline publishing requirement for all public apps** — not solely a
  Built for Shopify criterion, correcting a possible reading of the
  prior brief: "To be published in the Shopify App Store, your app must
  not reduce storefront Lighthouse performance scores by more than 10
  points." — `shopify.dev/docs/apps/best-practices/performance` and
  `shopify.dev/docs/apps/launch/shopify-app-store/best-practices`, both
  Accessible, 2026-07-10.
- **[Fact]** Recurring, **unannounced post-approval "app quality
  checks"** apply even to already-approved apps, checked against
  possibly-updated current requirements: 7 days to acknowledge a check
  notice (else demotion), 30 days total to remediate (else the app
  "might be unpublished") — `shopify.dev/docs/apps/launch/app-store-
  review/app-quality-checks`, Accessible, 2026-07-10. This is a standing
  compliance-monitoring obligation, not a one-time gate.
- **[Fact]** Feature/functionality drift from the originally-approved
  submission triggers **mandatory full re-review and resubmission**; a
  90-day API-deprecation rule blocks submissions using soon-to-expire
  APIs — `shopify.dev/docs/apps/launch/shopify-app-store/best-practices`,
  Accessible, 2026-07-10.
- **[Fact]** A mandatory support-email channel is always required
  (optional support-portal URL / display-only phone), with a qualitative
  "in a timely manner" obligation and **no numeric response-time or
  uptime SLA documented** — `shopify.dev/docs/apps/launch/distribution/
  support-your-customers`, Accessible, 2026-07-10.
- **[Open question]** The "Enforcement of Shopify's Partner Program
  Policies" page (referenced, not fetched this session) likely contains
  the graduated consequences for Partner Program Agreement/API License
  violations — needed for a complete ongoing-compliance picture, not yet
  captured.
- **[Open question]** The exact list of extension types that trigger a
  mandatory re-review on an app-version update (referenced from the
  Deploy App Versions page) was not fetched this session.

### 3.4 Built for Shopify (BFS) — new this session, resolves an open item from the prior brief

- **[Fact]** BFS is an **optional, voluntarily-applied-for recognition
  tier**, not a precondition for ordinary App Store publication: "Built
  for Shopify status is the highest level of recognition and achievement
  that an app can reach... You need to apply for Built for Shopify
  status." — `shopify.dev/docs/apps/launch/built-for-shopify`,
  Accessible, 2026-07-10. Confirmed by the App Store Requirements
  Checklist page, which never mentions "Built for Shopify" at all.
- **[Fact]** Prerequisites include: good Partner standing; ongoing
  compliance with baseline App Store requirements and the Partner
  Program Agreement/API License and Terms of Use; a minimum of **50 net
  installs from active shops on paid plans**; a minimum of **5 reviews**;
  and an undisclosed minimum recent app-rating threshold —
  `shopify.dev/docs/apps/launch/built-for-shopify/achievement-criteria`,
  Accessible, 2026-07-10.
- **[Fact]** Additional numeric performance thresholds apply only to BFS
  (not baseline publication): LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms
  (measured over a trailing 28-day window, ≥ 100-call minimum sample);
  checkout/carrier-rate calls p95 ≤ 500ms with ≤ 0.1% failure rate over
  ≥ 1,000 requests/28 days — same URL, Accessible, 2026-07-10.
- **[Fact]** BFS status is **not permanent once granted**: apps are
  reviewed annually, with a 60-day remediation window before status is
  revoked — `shopify.dev/docs/apps/launch/built-for-shopify/regain-lost-
  status`, Accessible, 2026-07-10.
- **[Inference]** BFS is effectively unreachable for Custom-Distribution
  apps, because its eligibility metrics (App Store installs and
  reviews) can only accrue on an App Store listing, which custom apps
  never have. No official page states this in one sentence naming both
  terms — logged as an inference, not a direct quote.
- **Relevance to the branch B decision:** BFS is **not** a decision input
  for whether to go public — it is a downstream, optional benefit
  reachable only after a public app (B-1 or B-2) exists and gains real
  traction. It should not be treated as part of the mandatory compliance
  cost of B-1/B-2, and it is not a reason, by itself, to prefer B-2 over
  B-1 (a fresh limited-visibility listing has zero installs/reviews on
  day one either way).

### 3.5 Partner Program Agreement / per-client custom-app scalability — new this session, closes a prior open item

- **[Fact]** The current Shopify Partner Program Agreement ("Last
  updated February 27, 2026") is **fully accessible** (fetched directly,
  HTTP 200, no login wall) — `shopify.com/partners/terms`, Accessible,
  2026-07-10. This corrects the prior brief's framing of the PPA as
  potentially inaccessible; it was reachable and reviewed this session.
- **[Fact]** The PPA contains **no numeric or categorical cap** on how
  many Applications (including custom-distribution apps) a
  Partner/Developer may create or register. The only related clause:
  "Developers will not... Create multiple Applications that offer
  substantially the same services" — a duplicate-**functionality** rule,
  not a per-client count limit, and not stated to apply to (or exempt)
  the pattern of one near-identical custom app per client serving
  different merchants.
- **[Fact]** No app-count cap or quota is stated on the Dev Dashboard
  documentation page either — `shopify.dev/docs/apps/build/dev-
  dashboard`, Accessible, 2026-07-10.
- Adversarially re-verified this session (§8, claim 4) — **CONFIRMED**:
  no official page states a numeric or policy limit. This is an
  **absence-of-evidence finding, not an affirmative safety guarantee**.
  Shopify has changed custom-app rules with limited advance notice
  before (the 2026-01-01 legacy-admin-app creation ban is a direct
  precedent) — the current absence of a cap is a snapshot, not a durable
  guarantee.
- **[Open question]** Whether the PPA's anti-duplication clause would be
  interpreted or enforced against dozens-to-hundreds of near-identical
  per-client custom apps serving different merchants is unresolved — no
  Shopify guidance found either way.
- **[Open question]** Whether undocumented Trust & Safety/fraud-
  detection systems impose a practical registration-volume threshold or
  scrutiny trigger on an organization registering unusually many custom
  apps is unknown and unverifiable from public documentation.
- A non-authoritative community forum thread (`community.shopify.com`,
  a regular-merchant "accepted answer," **not** a verified Shopify-staff
  account) states there is no specific numeric limit but recommends
  public distribution for multi-client reach — informal corroboration
  only, not treated as Fact.

### 3.6 OAuth / token-acquisition — refines DEC-023, new this session

- **[Fact]** Client-credentials-grant is officially restricted: "Client
  credentials is only available for apps developed by your own
  organization and installed in stores that you own." Tokens always
  expire at 86,399 seconds (24h), with no non-expiring variant, and are
  refreshed by repeating the same request (no separate refresh-token
  object) — `shopify.dev/docs/apps/build/authentication-authorization/
  access-tokens/client-credentials-grant`, Accessible, 2026-07-10. This
  is the first **primary** Shopify source (not a Developer Community
  reply) confirming the "same-organization" restriction DEC-023's §2
  rested on — upgrading that finding from informal to officially
  documented.
- **[Fact]** Authorization-code-grant and token-exchange are gated only
  by **rendering location** (standalone app vs. app rendered in the
  Shopify admin), never by distribution method or organizational
  ownership, per their own pages —
  `shopify.dev/docs/apps/build/authentication-authorization/access-
  tokens/authorization-code-grant` and `.../token-exchange`, both
  Accessible, 2026-07-10.
- **[Inference, by elimination — not a single direct quote]** Because
  client-credentials-grant is excluded for cross-organization app+store
  pairs, and authorization-code-grant/token-exchange carry no
  organizational-ownership restriction, a cross-organization Custom
  Distribution app (DEC-023 branch A's shape) must use authorization-
  code-grant (if standalone) or token-exchange (if admin-embedded) to
  acquire any token at all — Shopify's own three-row decision matrix
  offers no fourth path. **This strengthens DEC-023's central claim from
  community-sourced evidence to an officially-grounded inference, but it
  remains an inference by elimination across multiple pages, not a
  single directly-quoted Fact.** DEC-023 §2's cross-org claim should be
  read as confirmed-and-strengthened, not literally quoted, on this
  specific point.
- **[Fact]** Admin-created custom apps acquire their token by direct
  install-from-admin — no OAuth redirect, no HMAC callback, no
  state/nonce — and the only credential-rotation method is delete-and-
  recreate the app (no secret-rotation flow); token duration for this
  path is **not documented anywhere** on the official page —
  `shopify.dev/docs/apps/build/authentication-authorization/access-
  tokens/generate-app-access-tokens-admin`, Accessible, 2026-07-10.
- **[Fact]** Mandatory OAuth-callback security requirements (re-confirmed,
  unchanged): HMAC-SHA256 verification of alphabetically-sorted
  parameters; a unique per-request `state`/nonce value checked via a
  signed cookie (CSRF protection); pre-registered/allowlisted redirect
  URI (arbitrary URIs rejected) — same authorization-code-grant page.

### 3.7 Billing API mechanics — new this session

- **[Fact]** Two Shopify-provided billing paths for public apps: **Shopify
  App Pricing** (managed, default/recommended, supports recurring and
  usage-based charges via the App Events API) and **manual Billing API**
  (legacy/direct GraphQL mutations, "for apps that have specific
  requirements not covered by Shopify App Pricing yet, and for existing
  app developers who are using it" — still permitted, not phased out) —
  `shopify.dev/docs/apps/launch/billing`, Accessible, 2026-07-10.
- **[Fact]** `AppSubscription` = "a recurring billing agreement,"
  supporting recurring charges, usage-based pricing, or both, gated on
  mandatory merchant approval via a confirmation URL, with test-mode
  support — `shopify.dev/docs/api/admin-graphql/latest/objects/
  AppSubscription`, Accessible, 2026-07-10. `AppPurchaseOneTime` covers
  one-time charges (premium-feature unlocks, setup fees, one-time
  purchases) — `.../AppPurchaseOneTime`, Accessible, 2026-07-10.
- **[Fact]** A narrow carve-out exists for product-sourcing apps (cost-
  of-goods-sold via a PCI-compliant gateway) and donation apps (Billing
  API or PCI-compliant gateway) — but this carve-out **presupposes**
  Billing API access and is documented **only** within public-App-Store
  requirements; no official page extends it to custom/custom-
  distribution apps — `shopify.dev/docs/apps/launch/shopify-app-store/
  app-store-requirements` and `.../best-practices`, both Accessible,
  2026-07-10.
- **[Inference]** No Shopify-provided billing mechanism of any kind
  (Managed Pricing, direct Billing API, or the PCI-gateway carve-out) is
  documented as available to custom/custom-distribution apps — off-
  platform invoicing is the only documented option for such an app that
  needs to charge a merchant.
- **[Open question]** Shopify's revenue-share/transaction-fee percentage
  on Billing API or Managed Pricing charges was **not found** in any
  fetched official page — must be sourced (likely the Partner Program
  Agreement's fee schedule, not developer docs) before finalizing any
  commercial model built on B-1/B-2.

## 4. Compliance / protected-customer-data (PCD) analysis

| | Custom Distribution (branch A / B-3) | Public app (B-1 / B-2) |
| --- | --- | --- |
| PCD Level 1 | Always available | Requires review (Partner Dashboard access request; 9-item obligations list) |
| PCD Level 2 | Always available | Requires review (+ 7-item obligations list; "Participate in data protection reviews") |
| Compliance webhooks | Not Shopify-mandated | Mandatory: `customers/data_request`, `customers/redact`, `shop/redact`, 30-day response |
| Encryption/retention obligations enforced by Shopify? | No | Yes, as review requirements (encrypt at rest/in transit/backups; retention limits; test/prod separation; DLP strategy; staff-access limits + access log; incident-response policy) |

**The central tension for any eventual public-app adoption:** two of the
Level 1/Level 2 obligations — encryption at rest and retention/erasure
mechanics — interact directly with **already-accepted** decisions. MBQ-04
(via AR-024/PR #92 and AR-025/PR #94) accepted the Task 002 credential
posture as a **plain `Char` field behind `groups=` ACLs**, with an
explicit, honest no-encryption-claim residual ("Admin-group ORM/RPC read
technically possible... `sudo()`/DB/backup reads the plaintext, no
encryption claim"). Adopting B-1/B-2 without resolving this tension would
either fail PCD review or require **silently weakening an accepted
decision record**, which `CLAUDE.md` §10 and this brief both forbid — it
must be resolved through its own new DEC, explicitly, not implied by
adopting a distribution method. **This brief does not resolve it; it
names it as a prerequisite (§1.1 item 1).**

The three mandatory compliance webhooks are also currently kept
non-MVP under the accepted MBQ-09 posture — adopting a public-app branch
B outcome would, at whatever future point implementation is authorized,
reopen that deferral for a dedicated webhook-implementation task. This
brief does not authorize that.

Under the current DEC-023 branch-A evidence path (true Custom
Distribution, not an admin-created custom app), the connector faces
**no PCD review gate at all** for the customer fields Task 011/012
import (name, email, default address, phone) — this remains unchanged
and is not affected by anything in this brief.

## 5. Billing / commercial analysis

- **Custom Distribution (branch A / B-3):** zero Shopify-provided billing
  mechanism of any kind (§3.7). Any Lite/Full pricing, usage fees, or
  contract billing must be built and operated entirely off-platform
  (vendor invoicing, a PSP, or Odoo-side billing). This gives full
  pricing freedom (no Shopify take-rate, no forced self-serve plan-
  change UX rule) at the cost of 100% custom billing engineering, with no
  Shopify-native fallback — and this burden does not shrink as customer
  count grows; it is linear.
- **Public app (B-1 / B-2):** Shopify App Pricing (managed) or the
  Billing API (manual) natively supports recurring subscriptions, usage-
  based charges, and one-time charges, with mandatory merchant self-
  serve plan upgrade/downgrade and local-currency billing support. This
  removes the off-platform billing-engineering burden but (a) forecloses
  a single unified invoice if the project also sells Odoo-side licensing
  separately, (b) subjects all app-instance charges to an as-yet-
  unverified Shopify revenue-share/fee (§3.7 open question), and (c)
  structurally couples Lite/Full packaging to Shopify's `AppSubscription`
  schema rather than a purely Odoo-side mechanism, unless OP-23/Q27 is
  answered in a way that keeps them decoupled.
- **Hybrid (B-4):** both billing regimes run **permanently and in
  parallel** for their respective customer populations — this is
  additive, not transitional, because the distribution choice is
  permanent and no migration path exists between a customer's custom app
  and a future public app (§3.1). A customer never automatically
  "graduates"; moving one would require a full reinstall/reauthorization
  under a new app registration.

## 6. Setup wizard impact

None of this is authorized or specified in this docs-only phase
(`CLAUDE.md` §5). Forward-looking dependencies only:

- **Custom Distribution (branch A / B-3):** already-accepted DEC-004/
  DEC-023 framing stands — a multi-step credential/scope flow (guided
  app creation, masked token entry, inline scope validation, test-
  connection/readiness check), not one-click OAuth. B-3 at commercial
  scale adds an unresolved bootstrap question: does the vendor pre-
  provision each client's Dev Dashboard app (lower client friction,
  higher vendor ops burden), or does the client self-serve app creation
  (lower vendor burden, higher technical burden pushed onto a
  non-technical merchant)? Neither is decided here.
- **Public app (B-1 / B-2):** the wizard's OAuth-connect step (UI Group
  3 / OP-26) would implement authorization-code-grant (standalone) or
  token-exchange (admin-embedded) against **one** shared, vendor-owned
  app — architecturally simpler than B-3's N-apps-per-client model
  (single client ID/secret, single redirect-URL set). The wizard would
  also need a Shopify-hosted billing-approval interstitial (the
  `AppSubscription` confirmation URL) mid-onboarding, outside the
  connector's own UX control but still needing recovery-first design per
  DEC-012.
- **Hybrid (B-4):** the wizard needs a pluggable "connection method"
  step, not one fixed flow, since the two paths use structurally
  different transports (redirect/callback + HMAC for standalone
  authorization-code-grant vs. App Bridge session-token exchange for
  admin-embedded apps). Building only the branch-A flow today does not
  produce the public-app flow later "for free" — it is additive future
  work, not a relabeling of existing code. A worthwhile design principle
  for whichever future task specs the wizard: define the "connect" step
  as an abstraction over connection method now, even though only branch
  A is implemented today, so a later addition is additive rather than a
  rewrite. **This is a recommendation for a future task spec, not an
  authorization to build it.**

## 7. MVP impact and per-candidate decision readiness

**None of B-1/B-2/B-3(-at-scale)/B-4 is MVP scope.** RA-003 already
defers public App-Store packaging out of Phase 1; DEC-023's accepted
branch A already covers the MVP evidence path (VAL-B2, one pilot store);
and Tasks 011–015 are distribution-agnostic by construction (per the
prior brief §2/§6, re-confirmed unchanged by this session — no Task
011-015 file, test, or acceptance criterion references a distribution
method). This section states each candidate's own readiness, not an MVP
scope change.

### 7.1 B-1 (public, limited visibility) — decision readiness

Evidence base is now solid and current (2026-07-10). **Not ready for
adoption without**: (1) the RA-003 Phase-1-deferral-lift act for the
engineering surfaces it unlocks; (2) the MBQ-04 encryption-posture DEC
(§4); (3) OP-23/Q27 (Lite/Full mechanism); (4) an explicit B-1-vs-B-2
GTM call (a marketing/positioning decision this architecture evaluation
cannot make); (5) the Partner Program Agreement fee schedule and the
un-fetched "Enforcement" page; (6) the undocumented review-turnaround
SLA (launch-timeline risk).

### 7.2 B-2 (public, fully visible) — decision readiness

Identical compliance/review bar to B-1 (§3.3) — the B-1-vs-B-2 choice is
purely a discoverability/GTM/reputational-exposure question, not a
compliance-cost question. Not ready for the same six reasons as B-1,
plus an explicit open question on the project's actual intended go-to-
market motion (self-serve App-Store-led vs. high-touch direct/agency
sales), which is not established anywhere in the reviewed corpus and
materially affects how much weight B-2's discoverability benefit should
carry.

### 7.3 B-3 (per-customer Custom Distribution, at commercial scale) — decision readiness

**Not ready as the final, sole branch B answer.** Two load-bearing
unknowns block a confident verdict at "dozens to hundreds" scale: (1)
the scalability ceiling is officially undocumented (§3.5) — neither
proven safe nor unsafe; (2) the operational burden of manual per-client
app registration/OAuth completion at N customers is unquantified by any
official or first-party data point. At DEC-023's already-accepted scale
(one pilot customer), B-3 is mechanically identical to branch A and
introduces no new risk — that scale is not in question here.

### 7.4 B-4 (hybrid) — decision readiness

Ready only as a **bounded routing/sequencing confirmation**, not as a
final architecture pick, until: (a) ChatGPT confirms or denies that
DEC-023's branch-A acceptance ("a single pilot customer") extends to
multiple simultaneous pilot/private customers as ongoing practice — a
gap this evaluation surfaced that DEC-023's own singular language does
not resolve; (b) any migration mechanism, timeline, or customer-facing
promise about moving a custom-app customer to a future public app is
explicitly stated to not exist today (permanence, §3.1); (c) OP-23/Q27
resolution informs how a "Full" (custom/negotiated) vs. "Lite" (public/
self-serve) packaging split, if any, would actually work.

## 8. Adversarial verification record (this session)

Five load-bearing claims underlying this brief were independently
re-fetched and adversarially checked (attempting refutation, not merely
confirmation) against official sources on 2026-07-10:

| # | Claim | Verdict |
| --- | --- | --- |
| 1 | Distribution method (Public vs. Custom) is permanent once selected | **CONFIRMED** |
| 2 | Custom-distribution apps "Can't use the Billing API to charge merchants," no exception | **CONFIRMED** |
| 3 | The legacy "unpublished app" type is deprecated; no review-free multi-merchant route exists | **CONFIRMED** |
| 4 | No official page states a numeric/policy cap on custom-distribution apps per partner org | **CONFIRMED** (absence-of-evidence, not a guarantee) |
| 5 | PCD Level 1/2 = "Always available" for Custom apps, "Requires review" for Public apps | **CONFIRMED**, with the admin-created-custom-app Level-2 plan-gate nuance recorded (§3.2) |

No claim was refuted. Claim 5 surfaced a genuine nuance (the "Admin
created custom app" PCD Level 2 plan-gate) that must not be conflated
with true Custom-Distribution apps — recorded in §3.2 and carried into
DEC-026.

## 9. Risks (consolidated)

1. **B-3-alone risk:** treating an officially-undocumented, unquantified-
   burden mechanism as the standing answer for commercial scale, on the
   strength of "no official cap exists today" — an absence-of-evidence
   finding, not a safety guarantee, that Shopify could close at any time
   (precedent: the 2026-01-01 legacy-custom-app change).
2. **B-1/B-2 compliance-debt risk:** adopting a public-app branch B
   outcome pulls forward a large, currently-unauthorized engineering and
   governance surface (OAuth, 3 webhooks, PCD Level 2 review posture,
   Shopify billing, ongoing quality-check operations) that directly
   conflicts with the accepted MBQ-04/Task 002 credential posture unless
   a new DEC resolves the tension first (§4).
3. **B-4 additive-burden risk:** presenting the hybrid as "sequential" or
   "temporary" when the evidence shows it is **additive and permanent**
   — both obligation regimes run forever once a public half exists, with
   no way to retire the custom-app population's regime.
4. **Scope-generalization risk:** treating "early/pilot/private
   customers" (plural) as already covered by DEC-023's singular "a
   single pilot customer" acceptance — they are not the same claim (§7.4,
   §1.1 item 3).
5. **Unquantified financial risk:** Shopify's revenue-share/fee on
   Billing API/Managed Pricing charges is not documented in any source
   fetched — any Lite/Full commercial model assuming a specific margin
   under B-1/B-2 would be unsupported until this is sourced.
6. **Legal-review risk:** the Partner Program Agreement's fee schedule
   and the "Enforcement of Shopify's Partner Program Policies" page have
   not been reviewed — a real gap before any commercial commitment under
   any candidate.

## 10. Open questions (consolidated)

1. No official review-turnaround SLA for App Store submission is
   documented (only the status pipeline).
2. Shopify's revenue-share/transaction-fee percentage on Billing API /
   Managed Pricing charges is undocumented in any fetched source.
3. Whether a limited-visibility (B-1) listing can still accrue/display
   public merchant star ratings is unconfirmed.
4. Whether the PPA's anti-duplication clause applies to many near-
   identical per-client custom apps (B-3 at scale) is unresolved — no
   Shopify guidance found either way.
5. Whether undocumented Trust & Safety/fraud-detection thresholds
   constrain custom-app registration volume is unknown and unverifiable
   from public sources.
6. The cross-organization OAuth eligibility conclusion for Custom
   Distribution apps (DEC-023 §2) remains an elimination-based inference
   across multiple official pages, not a single directly-quoted Shopify
   statement.
7. The "Enforcement of Shopify's Partner Program Policies" page and the
   exact list of extension types that trigger mandatory app-version
   re-review were referenced but not fetched this session.
8. Whether the admin-created-custom-app PCD Level 2 plan-gate
   ("Grow plan or higher") applies in any form to partner-created Custom
   Distribution apps was not confirmed (evidence suggests no, since the
   PCD table lists them as separate rows with different values, but no
   page states the distinction explicitly in one sentence).
9. OP-23/Q27 (Lite/Full packaging mechanism) remains open at framing
   level — every fit_lite_full_packaging conclusion in the candidate
   evaluations is contingent on that unresolved question.
10. The project's actual intended go-to-market motion (self-serve App-
    Store-led vs. high-touch direct/agency sales) is not established
    anywhere in the reviewed corpus and materially affects the B-1-vs-B-2
    weighting.
11. Whether DEC-023's branch-A acceptance ("a single pilot customer")
    extends to multiple simultaneous pilot customers as ongoing practice
    is unresolved (§7.4, §1.1 item 3).

## 11. What ChatGPT must decide

This brief and the companion DEC-026 proposal decide nothing. The
following are ChatGPT's own, distinct acts:

1. **Accept, revise, or reject** this brief's recommendation (§1) and the
   companion DEC-026 proposal — including whether to adopt the B-1/B-4
   combination, a different combination, or none of the above.
2. If the recommendation is accepted in principle: **separately decide**
   whether/when to lift RA-003's Phase-1 deferral for the engineering
   surfaces it eventually unlocks (OAuth, wizard, billing, webhooks) —
   not requested or performed by this brief.
3. **Resolve the MBQ-04 encryption-posture tension** via its own DEC
   (§4, §1.1 item 1) before any PCD-Level-2-relevant implementation.
4. **Answer OP-23/Q27** (Lite/Full packaging mechanism) — needed before
   any `AppSubscription` plan mapping can be concretely designed.
5. **Clarify DEC-023's branch-A scope**: does "a single pilot customer"
   extend to multiple simultaneous pilot/private customers as ongoing
   practice? (§7.4, §1.1 item 3)
6. **Decide whether to authorize** a narrowly-scoped follow-up task to
   source the Partner Program Agreement fee schedule, the "Enforcement"
   page, and the extension-type re-review list, if these are needed
   before a commercial model is finalized.
7. If B-1/B-2 is eventually pursued: **separately decide** the B-1-vs-B-2
   visibility choice as a GTM/marketing call, not an architecture
   re-evaluation.

## Evidence / references

See §3 and §6 inline citations above; full excerpt captures in
[`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md)
(prior session's fetches) and this brief's own §3/§6 citations (this
session's new fetches, all dated 2026-07-10, Accessible unless noted).
Repository cross-references:
[`mbq-05-branch-b-distribution-auth-decision-brief.md`](./mbq-05-branch-b-distribution-auth-decision-brief.md),
[`DEC-023-token-acquisition-and-val-b2.md`](../04-decisions/DEC-023-token-acquisition-and-val-b2.md),
[`DEC-004-distribution-api-auth-strategy.md`](../04-decisions/DEC-004-distribution-api-auth-strategy.md),
[`rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md) (RA-003),
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
(MBQ-05, MBQ-04, MBQ-09 rows).
