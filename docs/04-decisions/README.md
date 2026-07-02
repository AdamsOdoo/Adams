# 04 — Decisions (ADRs)

**Purpose:** finalized, **accepted** architecture/product decision records. One
file per decision.

**What belongs here:** ADRs created from
[`decision-record-template.md`](./decision-record-template.md), named
`ADR-NNNN-<slug>.md`, each recording context (with cited, classified evidence),
the decision, consequences, and alternatives considered.

**What does not belong here yet:** speculative ideas or proposals under
discussion — those live in `../05-qa/architecture-review-log.md` until accepted.
Rejected alternatives must also be logged in
`../05-qa/rejected-approaches-log.md`.

**Current status:** Contains [`DEC-003-mvp-scope.md`](./DEC-003-mvp-scope.md) —
the accepted **MVP product-scope** decision (ChatGPT, 2026-07-01, RB-13) — plus
three **accepted architecture decision records**, proposed 2026-07-02 (Evidence
Refresh + Combined AR-002/003/005 Decision Preparation, PR #60) and **accepted by
ChatGPT on 2026-07-02** after PR #60 merged into `Shopify-connector` and Fable's
minor-change review was applied:
[`DEC-004-distribution-api-auth-strategy.md`](./DEC-004-distribution-api-auth-strategy.md)
(AR-002), [`DEC-005-sync-orchestration-strategy.md`](./DEC-005-sync-orchestration-strategy.md)
(AR-003), and
[`DEC-006-binding-dedup-identity-strategy.md`](./DEC-006-binding-dedup-identity-strategy.md)
(AR-005). **Each is now explicitly `Status: Accepted by ChatGPT`, acceptance date
2026-07-02 — no longer proposed or not-yet-accepted.** These are the **first
accepted architecture ADRs** in this repository, resolving AR-002/AR-003/AR-005 in
`../05-qa/architecture-review-log.md`. **Acceptance of these architecture
decisions does not, by itself, automatically authorize implementation** —
per `../05-qa/quality-feedback-loop.md` §10, AR-002/AR-003/AR-005 acceptance is one
of several Phase 1 research-phase-exit criteria (alongside Phase 1 domain-model
briefs, a DEC-003 scope-hole amendment, and a UX/operator-flow sprint), and the
no-code gate (`CLAUDE.md` §4–§5) remains in force until ChatGPT separately approves
that full exit and opens a dedicated implementation/blueprint phase. **AR-002,
AR-003, AR-004, AR-005, and AR-006 are now all accepted** (AR-004 via DEC-008
and AR-006 via DEC-009, below — see the second "Also accepted" section).
**AR-007 and AR-008 are now proposed for ChatGPT review** via DEC-010 and
DEC-011 respectively (below — see "Also present (not yet accepted)") —
**neither is accepted yet**; both stay "Proposed for ChatGPT review" until
ChatGPT formally accepts them. **Implementation remains blocked; DEC-008,
DEC-009, DEC-010, and DEC-011 do not authorize implementation.**
*(Naming note: `DEC-003`/`DEC-004`/`DEC-005`/`DEC-006` **follow the existing
`DEC-003` naming precedent** rather than the stated `ADR-NNNN-<slug>.md`
convention above — they do not predate that convention, they deliberately
continue the `DEC-003` numbering instead of introducing a second scheme
mid-sprint; this numbering/naming inconsistency **remains flagged, not
resolved**, in `../05-qa/documentation-residue-sweep.md` — do not invent missing
entries or rename existing ones.)*

**Also accepted:**
[`DEC-007-phase1-scope-clarifications.md`](./DEC-007-phase1-scope-clarifications.md) —
**accepted by ChatGPT on 2026-07-02** after PR #62 merged into `Shopify-connector` and
Fable's minor-change review (**ACCEPT WITH MINOR CHANGES**) was applied. DEC-007 is the
**Phase 1 scope-clarification addendum to DEC-003**: it **clarifies** five DEC-003
scope-hole wordings (variant export/update; image/media and price/compare-at handling; a
first-inventory-push guard; a fulfilment customer-notification default; and
tax/shipping/discount/payment-evidence treatment) — it does **not** rewrite DEC-003 and
does **not** authorize implementation. DEC-003/DEC-004/DEC-005/DEC-006 remain unchanged.
This acceptance makes **RA-008/RA-009/RA-010** (`../05-qa/rejected-approaches-log.md`)
binding rejected approaches. Per `../05-qa/quality-feedback-loop.md` §10, this acceptance
satisfies one of several Phase 1 research-phase-exit criteria — it does not, by itself,
open the implementation gate.

**Also accepted:**
[`DEC-008-module-boundary-strategy.md`](./DEC-008-module-boundary-strategy.md) and
[`DEC-009-error-retry-idempotency-strategy.md`](./DEC-009-error-retry-idempotency-strategy.md)
— proposed 2026-07-02 (AR-004 + AR-006 Decision Preparation sprint, after PR #63 merged
into `Shopify-connector`) and **accepted by ChatGPT on 2026-07-02** after PR #64 merged
into `Shopify-connector` and Fable's minor-change review (**ACCEPT WITH MINOR CHANGES**)
was applied. **Both are now explicitly `Status: Accepted by ChatGPT`, acceptance date
2026-07-02 — no longer proposed.** DEC-008 resolves **AR-004 module boundaries** (a
layered, domain-aligned addon family — `shopify_connector_core`/`product`/`sale`/
`inventory`/`fulfillment` for Phase 1, with a strict dependency DAG and no `adams_base`
dependency found justified); DEC-009 resolves **AR-006 error/retry/idempotency strategy**
(a classified error/retry taxonomy and layered idempotency strategy built on the accepted
DEC-005/006 substrate). Neither decides AR-007 or AR-008 — both were **not yet decided at
the time of this acceptance** (AR-007/AR-008 have since moved to **"Proposed for ChatGPT
review"** via DEC-010/DEC-011 — see "Also present (not yet accepted)" below; **still not
accepted**) — neither edits DEC-003/004/005/006/007 (all remain unchanged), and **neither
authorizes implementation.** This acceptance makes **RA-011 through RA-017**
(`../05-qa/rejected-approaches-log.md`) binding rejected approaches. See
[`../03-architecture/ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md)
and
[`../03-architecture/ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md)
for the evidence-backed briefs behind each decision.

**Also present (not yet accepted):**
[`DEC-010-inventory-architecture-strategy.md`](./DEC-010-inventory-architecture-strategy.md)
and
[`DEC-011-fulfillment-architecture-strategy.md`](./DEC-011-fulfillment-architecture-strategy.md)
— proposed 2026-07-02 (AR-007 + AR-008 Decision Preparation sprint, after DEC-008/DEC-009
acceptance, PR #65 merged into `Shopify-connector`). **Each is explicitly `Status:
Proposed for ChatGPT review` — not accepted.** DEC-010 proposes **AR-007 inventory
architecture** (Odoo as ongoing source of truth for Shopify inventory write-back, a
controlled first-sync import, inventory identity keyed on `(store, inventory_item_id,
location_id)`, an explicit non-inferred location mapping, the DEC-007 first-push guard
honored in full, layered sync, and the DEC-009 ambiguous-outcome retry rule applied to
inventory writes); DEC-011 proposes **AR-008 fulfillment architecture** (validated
`stock.picking` as the trigger, FulfillmentOrder-based mutations only, matched order/
FulfillmentOrder/line/quantity, the DEC-007 no-notification-by-default guard honored in
full, single-fulfillment-location Phase 1 posture with multi-package/multi-location
deferred, and the DEC-009 ambiguous-outcome retry rule applied to fulfillment writes).
**Neither decides implementation details, neither edits DEC-003/004/005/006/007/008/009,
and neither authorizes implementation.** A small number of options were explicitly
proposed-rejected as part of these DEC files — logged in `rejected-approaches-log.md` as
**PROPOSED** (RA-018 through RA-023), pending the same ChatGPT review as the DEC files
themselves. See
[`../03-architecture/ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md)
and
[`../03-architecture/ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md)
for the evidence-backed briefs behind each proposal, and
[`../03-architecture/ar007-ar008-evidence-refresh.md`](../03-architecture/ar007-ar008-evidence-refresh.md)
for the small targeted Odoo-side official-source check performed to ground them.
