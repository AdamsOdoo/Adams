# DEC-027 — DEC-023 Branch-A Pilot/Private-Customer Scope (OP-46)

> **Wave 0 control-room review (2026-07-15, PR #169):** explicitly kept
> Proposed/Deferred — not accepted and not rejected. See
> [`DEC-033`](DEC-033-mvp-wave-0-reconciliation.md) §4. Revisit condition:
> before onboarding a second simultaneous production private customer or
> proposing public distribution; not required for a single dev-store MVP/UAT.

## Status

**Proposed for ChatGPT review. NOT accepted.** Drafted 2026-07-10 by the
MVP planning-completion session (AR-042 candidate). Nothing below is
binding until ChatGPT explicitly accepts this record. This proposal does
not lift RA-003, does not modify DEC-023 or DEC-026, does not authorize
any implementation, OAuth, wizard, App Store, billing, or webhook work,
and does not touch VAL-B2's blocked status.

## Question being decided (OP-46)

DEC-023 §3.1 accepted Custom Distribution's evidence path for "**a
single pilot customer**" (singular). DEC-026's B-4-style hybrid
acceptance surfaced that treating "early/pilot/private customers"
(plural, ongoing practice) as covered by DEC-023 is a broader claim than
DEC-023 actually made. The question: how many simultaneous high-touch
pilot/private customers may operate under DEC-023 branch A (per-customer
custom-distribution apps + manual token entry) before the accepted rule
that "branch A is not the scalable commercial architecture" is violated
in practice?

## Evidence (all official, accessed 2026-07-10; captures in `../00-source-materials/shopify-orders-inventory-fulfillment-product-partner-captures-2026-07-10.md` §6)

1. **[Fact]** Custom distribution installs on "a single Shopify store,
   on multiple stores that belong to the same Plus organization or any
   transfer-disabled development stores"; the distribution choice is
   permanent; custom-distribution apps "Can't use the Billing API to
   charge merchants" (https://shopify.dev/docs/apps/launch/distribution).
2. **[Fact]** The Partner Program Agreement prohibits "Create multiple
   Applications that offer substantially the same services"
   (https://www.shopify.com/partners/terms, raw-text-verified). A fleet
   of near-identical per-customer connector apps is textually exposed to
   this prohibited-activities clause. How Shopify applies the clause to
   per-client custom apps is **not** documented — this is the clause's
   plain text, not an enforcement prediction.
3. **[Fact]** Shopify's documented enforcement actions for policy
   violations include revoking API access, suspending submission
   rights, pausing payouts, and terminating the Partner Account
   (https://help.shopify.com/en/partners/help-support/faq/removal).
4. **[Open question]** No official page documents a numeric limit on
   custom apps per partner (checked 2026-07-10: distribution pages,
   revenue-share page, help custom-apps manual). Absence of a documented
   limit is not evidence that unlimited fleets are acceptable.
5. **[Fact]** Billing for branch-A customers must be off-platform
   (invoicing outside Shopify), since custom-distribution apps cannot
   use the Billing API — commercially workable for a handful of
   high-touch customers, and exactly the property DEC-026 cited when it
   declined B-3 as the commercial-scale answer.

## Alternatives considered

| Option | Description | Consequences |
| --- | --- | --- |
| A — One pilot only | DEC-023 read literally: exactly one pilot customer, ever | Safest legally; commercially paralyzing — blocks any second high-touch customer until the Phase-2+ B-1 public app ships; probably stricter than DEC-023's intent (its purpose was VAL-B2 evidence + early value) |
| B — Unbounded "pilot" practice | Treat any number of private customers as branch-A pilots | De-facto adopts B-3 as the commercial architecture — directly contradicts DEC-026's accepted point (3); accumulating near-identical apps raises the PPA anti-duplication exposure with no offsetting benefit |
| C — Explicit small numeric cap | e.g. ≤3 simultaneous branch-A customers, hard cap | Predictable; but any specific number is arbitrary (no official basis exists for choosing 3 vs 5), and a hard cap invites treating the cap as an entitlement |
| **D — Case-by-case ChatGPT approval with a soft ceiling (recommended)** | Every branch-A customer beyond the first requires its own explicit, recorded ChatGPT approval; a standing soft ceiling of **three** simultaneous branch-A customers triggers a mandatory review of whether the B-1 public-app work (Phase 2+, RA-003 lift) must be prioritized before any further approval | Preserves DEC-023's evidence-first intent; keeps each expansion a deliberate, revocable act; the soft ceiling forces the strategic conversation at a defined point instead of by drift; consistent with DEC-026 ("B-3 is not the standing commercial-scale answer") |

## Proposed decision (Recommendation — becomes binding only on ChatGPT acceptance)

1. DEC-023 branch A covers **one pilot customer by default** (its
   original wording stands).
2. Each **additional** simultaneous branch-A pilot/private customer
   requires its own explicit, recorded ChatGPT approval **before** any
   per-customer custom app is registered, naming the customer and the
   reason branch A (not waiting for B-1) is justified.
3. A **soft ceiling of three** simultaneous branch-A customers applies:
   reaching it triggers a mandatory strategic review (prioritize the
   Phase-2+ B-1 path, or explicitly extend the ceiling with reasons)
   before any further approval may be granted.
4. Every branch-A per-customer app must be registered under the same
   Partner organization with an honest, distinct app name/description
   (no cloaking), so the anti-duplication exposure is assessable and the
   estate is auditable/wind-downable.
5. Branch-A customers must be contractually informed (commercial layer,
   outside this repo) that their integration path is a supported early
   program, with migration to the public app (B-1) when available.
6. Nothing in this decision lifts RA-003, alters DEC-026's Phase-2+
   gating, or authorizes any OAuth/wizard/App-Store/billing/webhook
   implementation.

## What becomes binding if accepted

Points 1–6 above become the operating rule for branch-A scope. The
OP-46 register row moves to "Resolved by DEC-027" and DEC-023 gains a
dated cross-reference note (no rewrite of its historical text).

## What remains unauthorized regardless of acceptance

All implementation surfaces (Tasks 012–015, UI, OAuth, webhooks,
packaging, billing); VAL-B2 execution (still human/live-gated); any
public-app work (RA-003 unchanged, Phase 2+ per DEC-026).
