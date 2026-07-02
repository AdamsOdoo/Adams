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
three **proposed, not-yet-accepted** architecture decision records added
2026-07-02 (Evidence Refresh + Combined AR-002/003/005 Decision Preparation):
[`DEC-004-distribution-api-auth-strategy.md`](./DEC-004-distribution-api-auth-strategy.md)
(AR-002), [`DEC-005-sync-orchestration-strategy.md`](./DEC-005-sync-orchestration-strategy.md)
(AR-003), and
[`DEC-006-binding-dedup-identity-strategy.md`](./DEC-006-binding-dedup-identity-strategy.md)
(AR-005). **Each is explicitly `Status: Proposed for ChatGPT review` — none is
accepted, and none authorizes implementation.** No **accepted** architecture
decision (ADR) exists yet; the first architecture ADR is created only after one
of these (or a future AR-004/006/007/008 proposal) is reviewed and accepted by
ChatGPT. *(Naming note: `DEC-003`/`DEC-004`/`DEC-005`/`DEC-006` **follow the
existing `DEC-003` naming precedent** rather than the stated
`ADR-NNNN-<slug>.md` convention above — they do not predate that convention,
they deliberately continue the `DEC-003` numbering instead of introducing a
second scheme mid-sprint; this numbering/naming inconsistency **remains
flagged, not resolved**, in `../05-qa/documentation-residue-sweep.md` — do not
invent missing entries or rename existing ones.)*
