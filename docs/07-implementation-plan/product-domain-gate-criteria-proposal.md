# Product-Domain Implementation Gate — Criteria Proposal

> **Documentation-only proposal. Does not open the product-domain
> implementation gate.** Prepared alongside
> [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md),
> after
> [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md)
> (PR #135, merged) found that the "product domain gate" named as a
> precondition in
> [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md)
> has never been opened, and that no document anywhere in this repository
> specifies what would need to be true to open it. This document proposes
> exactly that — the criteria — mirroring the structural pattern of
> [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md)
> and the Task 003/006C gate documents, but as a **criteria proposal only**,
> not a gate-opening act itself.

## 1. Status

- **Proposed / Under review.**
- **Not accepted.** No ChatGPT acceptance of this document exists anywhere in
  this repository as of this session.
- **Does not open the product-domain implementation gate.** Opening that
  gate remains a distinct, separate, explicit ChatGPT act — this document
  only proposes what that act should require before it happens.
- **Does not authorize Task 010, any other domain-sync task, or any code of
  any kind.**

## 2. Purpose

`task-010-product-import-proposed.md` names *"the product domain gate...
explicitly opened by ChatGPT"* as one of its own preconditions, citing
`ui-ux-implementation-task-map.md` Group 10. Neither that document, nor any
other document in this repository, states **what must be true** before
ChatGPT can perform that opening act. This gap was identified as a hard
blocker in `master-implementation-readiness-checkpoint.md` §1/§4/§5 (item 4).

This document proposes a concrete, checkable list of criteria for that
future act — nothing more. It does not itself satisfy any of the criteria it
lists, and it does not perform the act.

## 3. Proposed gate-opening criteria

**[Recommendation]** — proposed for ChatGPT's review and acceptance or
revision. Until accepted, none of the following is binding.

1. **PR #135 (the master implementation-readiness checkpoint) merged and its
   conclusions explicitly reviewed and accepted by ChatGPT.** PR #135 is
   confirmed **merged** into `Shopify-connector` (merge commit
   `308e9cb96b71861f774f1904aeb40f489cff867f`) — a git/process fact. Its
   *conclusions* (the blocker classification table, the Option 2 "not ready"
   finding) have **not** yet been recorded anywhere in this repository as
   formally accepted by ChatGPT — AR-033 remains **Proposed / Under
   review**, not Accepted. This criterion requires both: the PR merged
   (done) **and** an explicit ChatGPT acceptance of its findings (not yet
   done).
2. **MBQ-55 (product-template/product-variant portion) accepted/closed.**
   [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
   (this session's companion document) — or a revision of it — explicitly
   accepted by ChatGPT. Not yet accepted (proposed only, by this session's
   own design).
3. **Task 010's final implementation prompt has exact file/model/field
   names.** `task-010-product-import-proposed.md` itself states it "does not
   reach the exact file/field precision of the `CLAUDE.md` §9 template
   because MBQ-55... is still open" — this criterion is not satisfiable
   until criterion 2 is accepted, and a future final-prompt-drafting session
   converts the accepted naming into an actual `CLAUDE.md` §9 prompt.
4. **Exact allowed files and forbidden files defined** in that same future
   final prompt — depends on criterion 3.
5. **Product first-sync dedup thresholds fixed, or explicitly scoped as an
   in-task decision, in the final Task 010 prompt.** Per
   `mbq-55-product-binding-naming-schema-proposal.md` §12, this document
   does not fix them; the future final-prompt session must either fix the
   exact eligibility-check/match-confidence thresholds or explicitly declare
   them a narrow, named in-task design decision the implementation session
   itself may make (per `CLAUDE.md` §9's own allowance for this).
6. **No export/update scope.** Already true of
   `task-010-product-import-proposed.md` (explicit exclusion, ChatGPT
   REVISE on PR #93) — this criterion is satisfied today and must remain so;
   any future revision that reintroduces export/update scope into Task 010
   would need its own separate ChatGPT decision, not a silent expansion.
7. **No customer/order/inventory/fulfillment scope.** Already true of
   `task-010-product-import-proposed.md` — same standing requirement.
8. **No UI/wizard/webhook/OAuth scope.** Already true — Task 010's own
   document requires the UI implementation gate only for its Matching Center
   (S6) screen, which is not part of the backend-only boundary this gate
   would authorize; the UI gate remains separately closed and unaffected by
   this proposal.
9. **Tests defined.** The future final implementation prompt must name exact
   test files/fixtures. `mbq-55-product-binding-naming-schema-proposal.md`
   §4 proposes starting-point test file names
   (`test_product_template_binding.py`, `test_product_variant_binding.py`,
   `test_product_import_matching.py`, `test_product_duplicate_prevention.py`)
   — the future final prompt confirms or revises these, it does not have to
   invent them from nothing.
10. **Rollback plan defined.** `task-010-product-import-proposed.md` already
    carries a Rollback section (single-PR revert; reverting drops the two
    binding models; already-imported product/variant Odoo records remain as
    ordinary, simply un-bound, Odoo data) — the future final prompt must
    restate this precisely, not invent a new plan.
11. **Runtime/live Shopify dependency explicitly stated as absent or
    controlled.** Already true of `task-010-product-import-proposed.md`
    ("fake client tests allowed" per this session's own constraints; no live
    Shopify call beyond the existing, already-gated Task 003 API client) —
    must remain explicitly stated in the future final prompt, not silently
    assumed.
12. **Open blockers listed and classified as non-blocking for Task 010.**
    `master-implementation-readiness-checkpoint.md` §4 already provides this
    classification (VAL-B2, MBQ-05, TD-002, the fulfillment API model,
    checkpoint/resume ownership, the multi-server concurrency proof
    requirement, Lite/Full packaging — all classified B/C/D, none blocking
    Task 010's own narrow scope). This criterion requires that
    classification to be explicitly reconfirmed as still accurate at the
    time the gate is actually opened, not silently assumed unchanged
    indefinitely.

## 4. Gate closure rule

- **The gate opens only by explicit ChatGPT acceptance** of this criteria
  proposal (or a revision of it) **and** confirmation that every criterion
  in §3 is satisfied — not by this document's existence, and not by any
  individual criterion being satisfied in isolation.
- **The gate closes once the future Task 010 implementation PR is opened as
  draft.** Mirroring the pattern already used for Task 003
  (AR-029: "the gate closes again once the future Task 003 implementation
  PR is opened as draft") and Task 006C (AR-031), opening the gate
  authorizes **exactly one** future implementation session — Task 010 — not
  a standing mandate for further product-domain work.
- **The future Task 010 implementation PR must remain draft until ChatGPT
  reviews it.** No session may mark it ready for review or merge it without
  a distinct, explicit ChatGPT review act, consistent with every prior
  implementation PR in this project's history (Tasks 002–006C).

## 5. Non-authorizations

This document does not:

- Open the product-domain implementation gate, or any other implementation
  gate.
- Authorize Task 010, any other domain-sync task, a setup wizard, OAuth/
  token-acquisition code, or any Lite/Full packaging implementation.
- Authorize any code, module, model, view, controller, security file,
  manifest, test, or CI file of any kind.
- Mark any of its own proposed criteria as satisfied — every criterion in
  §3 is stated exactly as open or not-yet-satisfied as of this session.
- Mark MBQ-55 as Accepted or Resolved (see the companion naming/schema
  proposal for MBQ-55's own status).
- Claim ChatGPT accepted anything in this session.

---

## Evidence / references

- [`task-010-product-import-proposed.md`](./task-010-product-import-proposed.md)
  §Preconditions — access: Accessible, this repository, observed
  2026-07-09.
- [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
  Group 10 — access: Accessible, this repository, observed 2026-07-09.
- [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md),
  [`task-003-api-client-test-connection-gate.md`](./task-003-api-client-test-connection-gate.md),
  [`task-006c-sync-engine-skeleton-gate.md`](./task-006c-sync-engine-skeleton-gate.md) —
  structural pattern this document mirrors — access: Accessible, this
  repository, observed 2026-07-09.
- [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  AR-029, AR-031 (gate closure-on-draft-PR pattern) — access: Accessible,
  this repository, observed 2026-07-09.
- GitHub PR #135 (`AdamsOdoo/Adams`) — retrieved via `pull_request_read`,
  confirmed `merged: true`, merge commit
  `308e9cb96b71861f774f1904aeb40f489cff867f` — access: Accessible, 2026-07-09.

**Next step:** ChatGPT review of this proposal and the companion
[`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md).
