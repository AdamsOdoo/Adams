# DEC-026 — Distribution / Auth Strategy for MBQ-05 Branch B (Proposal)

## Status

**Accepted by ChatGPT as the strategic branch-B distribution/auth
direction — implementation gated separately.** Prepared 2026-07-10 by a
dedicated MBQ-05 branch B research/decision-preparation session (Fable
acting as strategic auditor / architecture decision researcher, not as
implementation worker); **accepted by ChatGPT on 2026-07-10** — see
"Acceptance note" immediately below. This acceptance does **not** resolve
MBQ-05 for implementation purposes, does **not** authorize any
OAuth/wizard/billing/webhook implementation, does **not** weaken DEC-023's
accepted branch A scope or RA-003's rejection, and does **not** affect
Task 011 (or any other implementation task) in any way.

**Acceptance note (2026-07-10):**

- **Accepted:** this proposal's hybrid recommendation as the strategic
  branch-B distribution/auth direction —
  1. **DEC-023 branch A stays unchanged**, exactly as already accepted in
     its limited scope (one-store/same-Plus-org/private-customer/
     VAL-B2-evidence purposes only).
  2. **Public distribution with Limited Visibility (candidate B-1) is
     designated the target scalable architecture** for the
     many-unrelated-commercial-customer use case, with the B-1-vs-B-2
     (limited vs. fully visible) choice deferred to a later, separate
     go-to-market decision.
  3. **B-3 (per-customer Custom Distribution) is *not* adopted** as the
     standing, sole answer at commercial scale.
  4. **This is Phase 2+ scope**, evaluated strictly under RA-003's own
     stated revisit condition.
- **Implementation gated separately — no implementation authorized by
  this acceptance.** No OAuth, token-exchange, setup wizard, UI, App
  Store packaging, billing integration, or compliance-webhook code of any
  kind is authorized. The "Non-authorizations" and "No implementation
  authorized" sections below remain fully in force, unchanged.
- **RA-003 is not lifted.** This acceptance exercises RA-003's own stated
  revisit condition (evaluating public distribution for Phase 2+); it
  does not weaken, reopen, or supersede RA-003's rejection of public App
  Store distribution as a Phase 1 requirement.
- **Five prerequisites remain open**, each requiring its own separate,
  explicit ChatGPT act before any implementation surfaces this direction
  might eventually unlock: (i) a dedicated DEC resolving the MBQ-04
  encryption-posture tension; (ii) ChatGPT's answer to OP-23/Q27
  (Lite/Full packaging mechanism); (iii) an explicit scope clarification
  of DEC-023 branch A (OP-46 — single vs. multiple simultaneous pilot
  customers); (iv) a separate ChatGPT act lifting RA-003's Phase-1
  deferral for the specific engineering surfaces this direction
  eventually unlocks; (v) sourcing the Partner Program Agreement's fee
  schedule and the "Enforcement of Shopify's Partner Program Policies"
  page (OP-45).
- **MBQ-05 branch B register status:** moves from "Partially routed /
  Open" to **"Accepted strategic direction; implementation gated
  separately"** — **not** "Resolved," since no code, wizard, or billing
  mechanism is authorized by this acceptance. See the MBQ-05 row in
  [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  and the AR-041 row in
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md).
- This acceptance record is itself a Markdown-only, docs-only patch; it
  creates no code, no Odoo module, no OAuth flow, no webhook, and no
  billing integration.

## Date

2026-07-10.

## Scope

**MBQ-05 branch B only** — the scalable, many-unrelated-customer /
commercial-product Shopify distribution and authentication architecture.
Does **not** decide or reopen: DEC-004 (Phase 1 distribution/API/auth
strategy — unchanged), DEC-023 (branch A, accepted in limited scope —
unchanged), RA-003 (public App-Store-distribution rejection for Phase 1 —
respected via its own stated revisit condition, not reopened), MBQ-04
(credential encryption/storage posture — a genuine tension this proposal
names but does not resolve, §6), or OP-23/Q27 (Lite/Full packaging
mechanism — named as a dependency, not decided).

## Decision context

DEC-023 (§3.2, Accepted in limited scope, 2026-07-08) split the
token-acquisition/distribution question into two branches: **branch A**
(Custom Distribution, accepted for one-store/same-Plus-org/private-
customer/VAL-B2-evidence purposes only) and **branch B** (the scalable,
many-unrelated-customer architecture, explicitly left open: "Public
distribution, or another officially-supported scalable route, must be
separately evaluated and accepted by ChatGPT before any implementation
work assumes a specific multi-customer distribution mechanism"). The
2026-07-10 AR-039 session confirmed branch B does not block Task 011 and
recommended a dedicated evaluation task. This proposal is the output of
that task: a full evidence-based evaluation of the four candidates
(B-1/B-2/B-3/B-4) named in
[`mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md),
refreshed and gap-filled with new 2026-07-10 official-source research and
an adversarial verification pass, presented in full in
[`mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md).

## Proposed decision

**[Recommendation — proposed, not decided]** Adopt, as the eventual
answer to MBQ-05 branch B, a hybrid trajectory functionally equivalent to
candidate B-4:

1. **Branch A unchanged.** DEC-023's accepted Custom Distribution scope
   (one-store/same-Plus-org/private-customer/VAL-B2-evidence only) stays
   exactly as accepted. This proposal does not widen it.
2. **Designate Public distribution, Limited Visibility (candidate B-1),
   as the target scalable architecture** for the many-unrelated-
   commercial-customer use case, with the B-1-vs-B-2 (limited vs. fully
   visible) choice deferred to a separate go-to-market decision that does
   not require new architecture research.
3. **Do not adopt B-3 (per-client Custom Distribution) as the standing,
   sole answer at commercial scale** — its scalability ceiling is
   officially undocumented, it has no Shopify-native billing mechanism,
   and its per-client operational burden is unquantified.
4. **This is Phase 2+ scope**, evaluated strictly under RA-003's own
   stated revisit condition. Nothing in this proposal authorizes
   implementation of any kind.

See
[`mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md)
§1 for the full recommendation text and §1.1 for the five prerequisites
that remain separately gated even if this proposal is accepted in full.

## Alternatives considered

| Alternative | Disposition in this proposal | Why |
| --- | --- | --- |
| **B-1 alone** (public, limited visibility, no continuing branch-A use) | Not proposed as stated — folded into the hybrid recommendation instead | Would require abandoning the already-working, already-accepted DEC-023 branch-A path for existing/pilot customers with no technical need to do so; the two are not mutually exclusive |
| **B-2 alone** (public, fully visible) | Not proposed as the initial visibility setting; left as a later, separate GTM decision | B-1 and B-2 carry an identical compliance/review bar (confirmed this session — "Shopify's app requirements are the same for both fully visible and limited visibility public apps"); the choice between them is a marketing/discoverability call, not an architecture one, and does not need to be made now |
| **B-3 as the standing, sole answer at commercial scale** | **Rejected as the standing answer** (though retained, unchanged, for its already-accepted branch-A/pilot scope) | Officially undocumented scalability ceiling (no source proves it safe or unsafe at "dozens to hundreds" of clients); zero Shopify-native billing mechanism; unquantified per-client operational burden; the Partner Program Agreement's anti-duplication clause carries an unresolved interpretive risk at scale |
| **B-4 exactly as originally framed** (implying a "phase 1 then phase 2" migration) | **Corrected in this proposal** — reframed as *permanent, additive coexistence*, not a temporary bridge | Distribution method is permanent per app with no migration path; a custom-app customer never automatically "graduates" to a public app. Presenting B-4 as sequential/temporary would misstate the evidence (confirmed: "You can't change the distribution method after you select it") |
| **Deferring this decision entirely (no recommendation now)** | Not proposed | The 2026-07-10 research pass closed enough of the prior brief's open items (Built for Shopify, Partner Program Agreement accessibility/limits, OAuth mechanics, Billing API detail) that a specific, evidence-backed recommendation is now supportable — deferring further would leave ChatGPT without an actionable starting point despite the evidence being largely in hand |

## Why rejected or deferred

- **B-3 as the sole standing answer is rejected for the commercial-scale
  use case** (not for its existing, accepted branch-A/pilot use) because
  its two most decision-critical facts — the scalability ceiling and the
  per-client operational burden — are both officially undocumented and
  unquantified. Adopting it as the standing answer would bet the
  project's entire commercial-scale distribution architecture on an
  absence-of-evidence finding, which this proposal treats as
  insufficient grounds for a load-bearing architecture decision.
- **Immediate implementation of B-1/B-2 is deferred**, not adopted for
  action now, because RA-003's Phase-1 deferral has not been lifted by
  this proposal (that is a distinct ChatGPT act, §9), and because the
  MBQ-04 encryption-posture tension (§6) is unresolved — adopting a
  public-app path today, before that tension is resolved, risks either
  failing PCD review later or silently weakening an accepted decision
  record.
- **A pure B-2 (fully visible) recommendation is deferred to a later,
  separate GTM decision** because the evidence shows B-1 and B-2 share an
  identical compliance/review bar — the choice is not an architecture
  question this proposal is positioned to answer, and forcing it now
  would exceed this proposal's evidence base (the project's actual
  go-to-market motion is not established in the reviewed corpus).

## Consequences

If this proposal is accepted:

1. MBQ-05's register row moves from "Partially routed / Open" to
   "Recommendation accepted; implementation gated separately" — **not**
   to "Resolved," since no code, wizard, or billing mechanism is
   authorized by acceptance alone (see Non-authorizations, §8).
2. RA-003 remains **unchanged and unreopened** — accepting this proposal
   exercises RA-003's own stated revisit condition (evaluating public
   distribution for Phase 2+), it does not weaken or supersede RA-003's
   rejection of public distribution *as a Phase 1 requirement*.
3. DEC-023 remains **unchanged** — branch A's accepted limited scope is
   untouched.
4. A future, separately-gated implementation chain becomes describable
   (not authorized) — see
   [`../07-implementation-plan/mbq-05-branch-b-next-implementation-implications.md`](../07-implementation-plan/mbq-05-branch-b-next-implementation-implications.md)
   for the full list of tasks this would unlock or continue to block.
5. Five follow-up items become ChatGPT's own next acts (§9).

If this proposal is rejected or revised: MBQ-05 branch B remains exactly
as open as it is today; DEC-023 branch A continues to be the only
accepted distribution/auth path of any kind; nothing in the current
implementation chain (Tasks 011–015) is affected either way, since none
of them depend on this decision (confirmed unchanged by this session).

## Risks

Carried in full from
[`mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md)
§9:

1. **B-3-alone risk** — treating an undocumented-ceiling mechanism as a
   commercial-scale standing answer on the strength of "no cap exists
   today," an absence-of-evidence finding Shopify could close at any
   time (precedent: the 2026-01-01 legacy-custom-app change).
2. **B-1/B-2 compliance-debt risk** — pulling forward OAuth, 3 compliance
   webhooks, PCD Level 2 review posture, Shopify billing, and ongoing
   quality-check operations before the MBQ-04 encryption-posture tension
   is resolved.
3. **B-4 additive-burden risk** — the hybrid's two obligation regimes run
   permanently in parallel, not sequentially; this proposal must not be
   read as implying either regime retires.
4. **Scope-generalization risk** — conflating DEC-023's singular "a
   single pilot customer" acceptance with routine multi-customer
   branch-A practice.
5. **Unquantified financial risk** — Shopify's Billing API/Managed
   Pricing revenue-share is undocumented in any source found.
6. **Legal-review risk** — the Partner Program Agreement's fee schedule
   and the "Enforcement of Shopify's Partner Program Policies" page have
   not been reviewed.

## Follow-up tasks (not authorized by this proposal)

1. A dedicated DEC resolving the MBQ-04 encryption-posture tension
   before any PCD-Level-2-relevant implementation.
2. ChatGPT's answer to OP-23/Q27 (Lite/Full packaging mechanism).
3. An explicit scope clarification of DEC-023 branch A (single vs.
   multiple simultaneous pilot customers).
4. A separate ChatGPT act lifting RA-003's Phase-1 deferral for the
   specific engineering surfaces this proposal eventually unlocks.
5. A narrowly-scoped research task to source the Partner Program
   Agreement's fee schedule, the "Enforcement of Shopify's Partner
   Program Policies" page, and the exact extension-type list that
   triggers mandatory app-version re-review — if/when needed before a
   commercial model is finalized.
6. A future, separate B-1-vs-B-2 (limited vs. fully visible) GTM
   decision, once/if the hybrid recommendation is accepted.

Full task-by-task implementation-chain implications (what becomes
possible or stays blocked under each outcome) are detailed in
[`../07-implementation-plan/mbq-05-branch-b-next-implementation-implications.md`](../07-implementation-plan/mbq-05-branch-b-next-implementation-implications.md).

## Non-authorizations

This proposal explicitly does **not**:

- Authorize any OAuth, token-exchange, or authorization-code-grant
  implementation of any kind.
- Authorize a setup wizard, any UI, any XML/view/menu/action file.
- Authorize any compliance-webhook code (`customers/data_request`,
  `customers/redact`, `shop/redact`).
- Authorize any Shopify Billing API / App Pricing integration code.
- Authorize any App Store listing submission or Partner Dashboard
  configuration action.
- Change DEC-004's accepted offline/unattended access model.
- Change DEC-023's accepted branch-A limited scope in any way.
- Weaken, reopen, or supersede RA-003's rejection of public App Store
  distribution as a Phase 1 requirement — this proposal operates
  strictly inside RA-003's own stated revisit condition.
- Resolve MBQ-04, MBQ-09, OP-23/Q27, or any other open point named
  above as a dependency.
- Affect Task 011, Task 012, Task 013, Task 014, Task 015, or any other
  implementation task's scope, files, or gate status in any way.
- Mark MBQ-05 "Resolved." Acceptance of this proposal, if it occurs,
  changes MBQ-05's status to "Recommendation accepted; implementation
  gated separately" at most — never "Resolved," since no implementation
  mechanism exists or is authorized.
- Constitute a decision. This document remains **Proposed for ChatGPT
  review** until ChatGPT explicitly accepts it; the acceptance act itself
  must be a distinct, recorded event (mirroring how DEC-023 and DEC-004
  were accepted), not inferred from this document's existence or from
  any PR merge.

## Evidence / references

- [`../03-architecture/mbq-05-branch-b-final-decision-brief.md`](../03-architecture/mbq-05-branch-b-final-decision-brief.md)
  — full evidence, candidate comparison table, compliance/billing
  analysis, adversarial verification record, and open questions
  underlying this proposal. All official-source citations live there.
- [`../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md`](../03-architecture/mbq-05-branch-b-distribution-auth-decision-brief.md)
  (2026-07-10, AR-039 session) — the prior brief this proposal completes.
- [`DEC-023-token-acquisition-and-val-b2.md`](./DEC-023-token-acquisition-and-val-b2.md)
  §3.2, §8–§9 — branch A/B framing, accepted limited scope (unchanged by
  this proposal).
- [`DEC-004-distribution-api-auth-strategy.md`](./DEC-004-distribution-api-auth-strategy.md)
  — Phase 1 distribution/API/auth strategy (unchanged).
- [`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md)
  RA-003 (respected via its own stated revisit condition, not reopened).
- [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
  MBQ-05, MBQ-04, MBQ-09 rows.
- [`../08-release-readiness/open-points-closure-register.md`](../08-release-readiness/open-points-closure-register.md)
  OP-05, OP-40, OP-23.
- Official Shopify sources, all fetched/re-verified 2026-07-10 — full
  citations in the final decision brief §3/§6; excerpt captures in
  [`../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md`](../00-source-materials/shopify-customer-odoo19-partner-task-011-captures.md).

## No implementation authorized

**Acceptance of this proposal, if and when it occurs, does not by itself
authorize implementation of any kind.** This record creates no code, no
Odoo module, no OAuth flow, no webhook, no billing integration, and no
file outside `docs/03-architecture/**`, `docs/04-decisions/**`,
`docs/07-implementation-plan/**`, and the registers named in this
session's scope. The no-code gate (`CLAUDE.md` §4–§5) remains in force.
Every follow-up item in §9 requires its own separate, explicit ChatGPT
act before any implementation work may begin.
