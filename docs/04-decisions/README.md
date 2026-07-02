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
that full exit and opens a dedicated implementation/blueprint phase. AR-004/006/
007/008 remain **not decided** — future architecture ADRs for those rows are
created only after their own proposal is reviewed and accepted by ChatGPT.
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
