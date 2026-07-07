# Shopify Token-Acquisition Options — Comparison (AR/MBQ-05 Follow-Up)

> **Architecture options comparison. Not a decision record.** This document
> compares three candidate MVP directions for how a merchant obtains the Shopify
> Admin API access token the connector stores. It is built on the facts in
> [`../01-research/shopify-token-acquisition-research.md`](../01-research/shopify-token-acquisition-research.md)
> and feeds
> [`../04-decisions/shopify-token-acquisition-decision-brief.md`](../04-decisions/shopify-token-acquisition-decision-brief.md).
> No option here is adopted by this document — adoption requires ChatGPT review
> per `CLAUDE.md` §2/§6/§8. This closes the still-open **MBQ-05** row in
> [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)'s
> evidence base, but does not itself resolve MBQ-05 — only ChatGPT can.

## Status

- **Scope:** MVP token-acquisition path only. Does **not** reopen DEC-004
  (offline/unattended access model, masked storage, least-privilege scopes — all
  unchanged and assumed here), does not reopen Task 002's already-accepted
  credential schema (`shopify.connector.store.credential`, one row per store,
  `token_variant` seam), and does not authorize any code change.
- **Constraint carried forward from Task 002 (AR-025, accepted 2026-07-07):**
  the currently *implemented* schema stores exactly one secret value with
  `token_variant='offline_custom_app'` — no `client_id`/`client_secret`/
  token-cache/expiry fields exist in the shipped model today. Any option below
  that would require those fields is, by definition, **Task 004+ implementation
  work**, not something this document or session authorizes.

## The three options

- **Option A — Offline/custom-app Admin API token only.** The merchant obtains
  *some* long-lived, non-expiring Admin API access token (`shpat_`-shaped) by
  whatever means available to them today, and manually pastes it into the
  existing Admin-only credential field. The connector implements no OAuth
  handshake of any kind. This is what Task 002 already built and what the
  connector supports today.
- **Option B — OAuth/token acquisition before MVP customer-facing setup.** The
  connector (or a companion setup tool) implements the standard OAuth
  authorization-code-grant flow end-to-end — a hosted redirect/callback
  endpoint, HMAC verification, code-for-token exchange — so a merchant completes
  a normal "connect your store" consent screen instead of hand-typing a secret.
- **Option C — Dual path: offline token now, OAuth as a gated follow-up.**
  Ship/keep Option A's storage and setup copy as-is for MVP, but explicitly
  scope and schedule a real OAuth implementation (Option B) as a named,
  separately-gated follow-up task — and, as a **non-code, documentation-only**
  bridge for the gap between "legacy admin-created tokens are gone for new
  merchants" and "OAuth is built," validate whether a merchant can mint a
  compatible non-expiring token today via a manual, one-time authorization-
  code-grant exchange (using the merchant's own Dev-Dashboard custom app),
  performed with generic tooling (e.g. `curl`) entirely outside the Odoo
  codebase, then paste the resulting token into the existing field exactly as
  Option A already does.

---

## Comparison table

| Criterion | Option A — offline token only | Option B — OAuth before MVP | Option C — dual path |
| --- | --- | --- | --- |
| **User setup UX** | Merchant must obtain a token themselves outside Odoo, then paste it in. For a **legacy** (pre-2026-01-01) custom app this was a short admin-UI flow; for **any merchant signing up today**, no such admin-UI reveal exists — they must create a Dev-Dashboard app and either run the 24h client-credentials flow (requires ongoing programmatic refresh the connector doesn't implement) or a one-time OAuth exchange (requires tooling the connector doesn't ship). **As coded today, Option A alone does not give a new merchant a supported way to get a compatible token without outside help.** | Familiar "click to connect" consent-screen UX, matching what merchants expect from most SaaS integrations. Requires the connector vendor to host a public, reachable redirect URI and walk the merchant through installing a Dev-Dashboard/CLI app version first. | Same manual-paste UX as A in the near term, but with an explicit, honest interim recipe (a documented one-time OAuth exchange run by hand) to unblock new-merchant setup without waiting for B, plus a named path to the friendlier UX later. |
| **Security implications** | Long-lived static secret, masked at rest behind Odoo ACLs (unchanged from Task 002 — no encryption-at-rest, a known, documented residual). No token-refresh attack surface. Revocation only via Shopify-side uninstall/app-delete or secret revocation (research §7) — the connector has no rotation UX beyond re-entering a new value. | Adds a redirect/callback endpoint as new attack surface (must verify HMAC correctly, must protect the `state` nonce, must keep the client secret secure) but Shopify's own docs treat this as the standard, hardened path for standalone/ERP-style apps (research §5). No new token-lifetime risk if a non-expiring offline token is still requested (`expiring=0`, the default). | Inherits A's security posture until B ships; the interim manual-exchange recipe under C reduces (not eliminates) new-merchant onboarding friction without adding any new *code* attack surface, since it produces the same static-secret shape A already stores. |
| **Validation implications for Task 003** | VAL-B2 remains blocked for any merchant without a pre-2026-01-01 legacy custom app, unless the interim manual OAuth-exchange recipe (see Option C) is attempted and confirmed to work — that attempt is itself unvalidated today (research §4, "central open architectural question"). | Unblocks VAL-B2 by construction once built and tested against a real Dev Dashboard app — but building/testing it is Task-004-scale work, not achievable inside this docs-only session, and not started here. | Recommends the **next concrete, low-risk step**: attempt the manual authorization-code-grant exchange against the same failing development store, with no connector code change, to see whether it actually mints a working non-expiring token. If yes, VAL-B2 unblocks immediately under Option A's existing storage shape. If no, that is itself strong evidence Option B (or a client-credentials-based schema extension) is required. |
| **MVP speed** | Fastest — zero new code; already implemented. | Slowest — requires building and testing a real OAuth handshake (hosted endpoint, HMAC verify, token exchange, error handling) before any new customer can complete setup. | Fast for now (no new code required to keep Option A shipping); the interim validation step is a single manual research/QA action, not a coding task. |
| **Commercial/customer-readiness impact** | Not customer-ready for self-serve onboarding of *new* merchants today — every new customer would need hand-holding through a Dev-Dashboard app + manual token mint, which is not documented anywhere in the connector's own setup materials yet. Fine for a single, already-provisioned pilot merchant with a legacy app. | Customer-ready, "click to connect" experience once built — but delays MVP ship date and adds an ongoing hosting/maintenance obligation (the redirect endpoint must stay reachable). | Buys time: ship to early/pilot customers now (using the interim manual recipe or an existing legacy app), while the friendlier B experience is built for general availability, without over-promising either "OAuth is coming next sprint" or "manual tokens are fine forever." |
| **Support burden** | Every new-merchant setup likely generates a support ticket, since there is no in-product guidance today for how a merchant unfamiliar with Shopify's Dev Dashboard obtains a compatible token. Legacy-app merchants have low burden (short admin-UI flow) but that population only shrinks over time. | Lower per-merchant support burden once built (self-serve consent flow), but the redirect endpoint itself becomes a new operational/support surface (must diagnose HMAC/redirect-URI/scope mismatches). | Moderate near-term burden (setup docs must walk a merchant through the manual exchange precisely, and mistakes there are opaque to non-developers), decreasing once B ships. |
| **Compatibility with current Shopify docs** | Fully compatible — custom apps and merchant-created apps are explicitly, repeatedly exempt from the Dec-2025 expiring-token mandate (research §6), so a non-expiring static secret remains a fully supported model, not a deprecated one. | Fully compatible — Shopify's docs describe this exact mechanism (authorization code grant) for standalone/ERP-style apps (research §5); no evidence it is deprecated or restricted for custom apps. | Fully compatible — inherits both of the above; the interim recipe under C uses only documented, current Shopify mechanisms (Dev Dashboard app creation + standard OAuth grant), not anything unofficial. |
| **Odoo implementation complexity** | None beyond what already exists (Task 002 shipped). | Meaningful: a new controller/endpoint reachable from the public internet, HMAC verification, state-nonce handling, install-flow UX, and still needs to decide whether the resulting token is stored via the existing single-secret shape (if non-expiring offline is requested) or requires new fields entirely (if an expiring offline token or client-credentials model is chosen instead). | None required for MVP; the interim recipe is pure documentation/tooling outside the Odoo module. The future OAuth build is scoped identically to Option B whenever it is gated in. |
| **Risks** | New-merchant onboarding friction risks stalling adoption; relying on "the merchant already has a legacy app" is not a durable MVP assumption since that population is fixed and shrinking (no new legacy apps can be created after 2026-01-01). | Building OAuth against an unconfirmed combination (Dev-Dashboard custom app + authorization code grant — research §4's open question) risks discovering mid-implementation that Shopify does not actually support it as expected, wasting build effort; also risks scope creep into public-app-style compliance obligations if boundaries aren't held. | Requires discipline to actually schedule and gate the Option B follow-up rather than letting "dual path" quietly become "Option A forever"; the interim manual recipe is unvalidated until someone actually runs it (this document does not claim it works). |
| **Recommended conditions if selected** | Only defensible as MVP-only for a small, known set of pilot merchants who already hold (or can be given) a legacy admin-created custom app, **and** only if the setup docs explicitly disclose that new merchants need an out-of-band token-acquisition step. Must not be marketed as "self-serve" without that disclosure. | Should not be started without first empirically confirming (via the Option C interim step) that authorization-code-grant actually works against a Dev-Dashboard custom app, so the implementation isn't built against an unconfirmed assumption. | Requires: (1) immediately attempting the manual OAuth-exchange validation step in a future Task-003-continuation session (no code change); (2) an explicit ChatGPT-approved follow-up task scoping Option B once (1)'s result is known; (3) setup-wizard copy that is honest about the current manual step's complexity, not silent about it. |

---

## Narrative detail per option

### Option A — offline/custom-app Admin API token only

This is the status quo: Task 002 already implemented
`shopify.connector.store.credential` with `token_variant='offline_custom_app'`,
a single manually-entered secret, no OAuth. The open problem this research
surfaces is **not** whether this storage shape is sound (it is, and remains
Shopify-compliant per research §6) — it is that the **mechanism by which a new
merchant obtains a token to put into that field has materially changed**. Before
2026-01-01, a merchant (or an Admin acting on their behalf) could create a
custom app directly in the Shopify admin and be handed a token immediately, with
no code, no redirect, no OAuth. That path is now closed to any newly-created
app. A merchant starting today must go through the Dev Dashboard, and Shopify's
own tutorial for that exact "own store" scenario shows only the 24-hour
client-credentials grant — which is architecturally incompatible with "one
static secret, no refresh loop" unless a merchant is willing to run the
authorization-code-grant flow themselves, a path research §4 flags as
**plausible but not officially demonstrated**.

**Bottom line:** Option A's storage design is fine; Option A's *implicit setup
story* ("an Admin pastes in a token") quietly assumed a token-acquisition path
that Shopify has since closed off for new merchants. Selecting Option A alone,
without addressing that gap, means MVP setup is not actually self-serve for new
customers today.

### Option B — OAuth/token acquisition before MVP customer-facing setup

This would resolve the new-merchant onboarding gap identically to how most
Shopify integrations work today: an install link, a Shopify consent screen, a
redirect back with a code, a server-side exchange for a token. Research §5
confirms the mechanics are fully documented and current. The catch is scope and
sequencing, not feasibility:

- It requires hosting a public, reachable redirect endpoint — new Odoo-side
  attack surface and a new operational dependency (the endpoint must stay up).
- It requires deciding *which* token shape results (non-expiring offline,
  matching the current field; or the newer expiring-offline model with a
  refresh loop) — a decision this document does not make.
- Building it now, before confirming the underlying assumption (that
  authorization-code-grant actually works end-to-end against a Dev-Dashboard
  custom app used as a standalone integration) risks discovering a problem only
  after non-trivial implementation effort.

### Option C — dual path: offline token now, OAuth as a gated follow-up

This option does not require a different storage schema than Option A today —
it reframes the *near-term* problem as a **research/validation gap**, not an
implementation gap: attempt the standard OAuth authorization-code-grant flow, by
hand, with generic tooling (e.g. a `curl` recipe or a small standalone script
that is not part of the Odoo module), against a fresh Dev-Dashboard custom app
built for the same store used in Task 003's blocked validation session,
requesting a non-expiring offline token. If Shopify actually issues one, that
token is byte-for-byte compatible with the existing `access_token` field and
`token_variant='offline_custom_app'` value — VAL-B2 could be re-attempted and
very plausibly pass, with **zero code change**, only updated setup
documentation. If the attempt fails (e.g. Shopify silently forces
client-credentials-only behavior for Dev-Dashboard custom apps in practice
regardless of what the general docs imply), that is decisive evidence Option B
(a real OAuth implementation) or a client-credentials-based schema extension is
required before MVP can claim self-serve new-merchant setup.

This document does **not** assert that the manual exchange will succeed — that
is exactly the untested hypothesis behind VAL-B2, and asserting it works without
having observed it would violate `CLAUDE.md` §7's evidence rules. It is
presented as the lowest-risk, fastest way to convert an open question into a
decided fact.

---

## What this document does not decide

- Whether Option A, B, or C is adopted — routed to
  [`../04-decisions/shopify-token-acquisition-decision-brief.md`](../04-decisions/shopify-token-acquisition-decision-brief.md)
  for ChatGPT.
- Any change to Task 002's shipped credential schema.
- Whether Task 004 may start (addressed in the decision brief).
- Whether Task 003 validation is complete (it is not — see
  [`../05-qa/task-003-validation-results.md`](../05-qa/task-003-validation-results.md)).
