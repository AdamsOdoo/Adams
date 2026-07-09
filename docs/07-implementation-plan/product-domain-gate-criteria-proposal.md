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

- **Accepted by ChatGPT, as criteria only** — via control-room review,
  GitHub comment ID `4924917266`, on PR #136.
- **Does not open the product-domain implementation gate.** Accepting the
  criteria list in §3 as the correct criteria is a distinct act from
  confirming those criteria are satisfied, which is itself distinct from
  the gate-opening act. Opening the gate remains a future, separate,
  explicit ChatGPT act, performed only once every criterion in §3 is
  confirmed satisfied — this acceptance does not itself perform that act.
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

**Accepted by ChatGPT as the correct criteria** (control-room review, PR
#136, comment ID `4924917266`). Accepting this list as the correct
criteria is **not** the same as every criterion being satisfied —
satisfaction status is marked per criterion below, and is accurate as of
this revision, not permanently fixed: several criteria are already
satisfied; several remain unsatisfied. **The gate remains closed** because
not every criterion is yet satisfied, and because no separate, explicit
ChatGPT gate-opening act has occurred.

1. **PR #135 (the master implementation-readiness checkpoint) merged and its
   conclusions explicitly reviewed and accepted by ChatGPT.** PR #135 is
   confirmed **merged** into `Shopify-connector` (merge commit
   `308e9cb96b71861f774f1904aeb40f489cff867f`) — a git/process fact. Its
   *conclusions* (the blocker classification table, the Option 2 "not ready"
   finding) are now recorded as accepted — AR-033 was corrected to
   **Accepted** (control-room comment ID `4924290291`, PR #135 merge).
   **Status: Satisfied.**
2. **MBQ-55 (product-template/product-variant portion) accepted/closed.**
   [`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
   is now **Accepted by ChatGPT** for the product-template/product-variant
   portion (same PR #136 acceptance, comment ID `4924917266`). The
   customer-binding and order-binding portions of MBQ-55 remain open, but
   this criterion names only the product-template/product-variant portion.
   **Status: Satisfied.**
3. **Task 010's final implementation prompt has exact file/model/field
   names.** `task-010-product-import-proposed.md` itself states it "does not
   reach the exact file/field precision of the `CLAUDE.md` §9 template
   because MBQ-55... is still open" — criterion 2's acceptance makes this
   now satisfiable, but a future final-prompt-drafting session still has to
   convert the accepted naming into an actual `CLAUDE.md` §9 prompt.
   **Status: Not yet satisfied.**
4. **Exact allowed files and forbidden files defined** in that same future
   final prompt — depends on criterion 3. **Status: Not yet satisfied.**
5. **Product first-sync dedup thresholds fixed, or explicitly scoped as an
   in-task decision, in the final Task 010 prompt.** Per
   `mbq-55-product-binding-naming-schema-proposal.md` §12, that document
   does not fix them; the future final-prompt session must either fix the
   exact eligibility-check/match-confidence thresholds or explicitly declare
   them a narrow, named in-task design decision the implementation session
   itself may make (per `CLAUDE.md` §9's own allowance for this).
   **Status: Not yet satisfied.**
6. **No export/update scope.** Already true of
   `task-010-product-import-proposed.md` (explicit exclusion, ChatGPT
   REVISE on PR #93) — this criterion is satisfied today and must remain so;
   any future revision that reintroduces export/update scope into Task 010
   would need its own separate ChatGPT decision, not a silent expansion.
   **Status: Satisfied.**
7. **No customer/order/inventory/fulfillment scope.** Already true of
   `task-010-product-import-proposed.md` — same standing requirement.
   **Status: Satisfied.**
8. **No UI/wizard/webhook/OAuth scope.** Already true — Task 010's own
   document requires the UI implementation gate only for its Matching Center
   (S6) screen, which is not part of the backend-only boundary this gate
   would authorize; the UI gate remains separately closed and unaffected by
   this proposal. **Status: Satisfied.**
9. **Tests defined.** The future final implementation prompt must name exact
   test files/fixtures. `mbq-55-product-binding-naming-schema-proposal.md`
   §4 proposes starting-point test file names
   (`test_product_template_binding.py`, `test_product_variant_binding.py`,
   `test_product_import_matching.py`, `test_product_duplicate_prevention.py`)
   — the future final prompt confirms or revises these, it does not have to
   invent them from nothing. **Status: Not yet satisfied** — starting-point
   names proposed and now carried by an accepted document, but not yet
   confirmed by a final implementation prompt.
10. **Rollback plan defined.** `task-010-product-import-proposed.md` already
    carries a Rollback section (single-PR revert; reverting drops the two
    binding models; already-imported product/variant Odoo records remain as
    ordinary, simply un-bound, Odoo data) — the future final prompt must
    restate this precisely, not invent a new plan. **Status: Satisfied.**
11. **Runtime/live Shopify dependency explicitly stated as absent or
    controlled.** Already true of `task-010-product-import-proposed.md`
    ("fake client tests allowed" per this session's own constraints; no live
    Shopify call beyond the existing, already-gated Task 003 API client) —
    must remain explicitly stated in the future final prompt, not silently
    assumed. **Status: Satisfied.**
12. **Open blockers listed and classified as non-blocking for Task 010.**
    `master-implementation-readiness-checkpoint.md` §4 already provides this
    classification (VAL-B2, MBQ-05, TD-002, the fulfillment API model,
    checkpoint/resume ownership, the multi-server concurrency proof
    requirement, Lite/Full packaging — all classified B/C/D, none blocking
    Task 010's own narrow scope). This criterion requires that
    classification to be explicitly reconfirmed as still accurate at the
    time the gate is actually opened, not silently assumed unchanged
    indefinitely. **Status: Not yet satisfied** — reconfirmation is a
    point-in-time act to be performed when the gate-opening act itself is
    considered, not before.

## 4. Gate closure rule

- **This criteria proposal is now Accepted** (PR #136, comment ID
  `4924917266`). **The gate itself still opens only** by a distinct,
  future, explicit ChatGPT gate-opening act confirming that every
  criterion in §3 is satisfied at that time — not by this acceptance, and
  not by any individual criterion being satisfied in isolation.
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
- Mark any criterion as satisfied that is not. §3 states each criterion's
  actual satisfaction status as of this revision: criteria 1, 2, 6, 7, 8,
  10, and 11 are satisfied; criteria 3, 4, 5, 9, and 12 remain unsatisfied.
  Satisfying every remaining criterion does not, by itself, open the gate —
  only a separate, explicit, future ChatGPT gate-opening act does that.
- Mark MBQ-55 as fully Accepted or Resolved — only its
  product-template/product-variant portion is Accepted (see the companion
  naming/schema proposal); the customer-binding and order-binding portions
  remain open.
- Claim ChatGPT accepted anything beyond what is explicitly recorded above:
  the criteria list in §3 as the correct criteria, and (via the companion
  document) the MBQ-55 product-template/product-variant portion. This does
  not claim the product-domain gate is open, that Task 010 is authorized,
  or that any code is authorized.

## 6. Task 010 gate proposal linkage — not a gate opening

**Added 2026-07-09, docs-only. Proposed only. Does not open the
product-domain implementation gate.**

A future-session pairing —
[`task-010-product-import-final-implementation-prompt.md`](./task-010-product-import-final-implementation-prompt.md)
(the file-exact `CLAUDE.md` §9 prompt, converting criteria 3/4/5/9's
requirements into exact model/field/file names and dedup thresholds) and
[`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md)
(the proposal that criteria 3, 4, 5, 9, and 12 above are now satisfied, and
that reconfirms criteria 1/2/6/7/8/10/11 are unchanged) — has been drafted
against this document's §3 criteria.

**Both linked documents are proposed only, not accepted.** Drafting them
does not itself satisfy any criterion by assertion — the gate-opening
proposal states its own evidence for each criterion, subject to ChatGPT's
own review. **The product-domain implementation gate remains closed** until
ChatGPT explicitly accepts
[`task-010-product-import-gate-opening-proposal.md`](./task-010-product-import-gate-opening-proposal.md)
as the distinct, explicit gate-opening act §4 above requires. This section
does not itself perform that act, does not mark any criterion in §3 above
as ChatGPT-confirmed satisfied, and does not authorize Task 010 or any
code of any kind.

**Revision note (2026-07-09, PR #137 control-room review, comment ID
`4925370944`):** ChatGPT reviewed the linked pairing and required revision
before merge — five precision gaps in the final prompt (manifest
dependency, exact field types, exact `_name`/`_inherit` declarations, a
required product-domain enablement gating seam, and tests covering it)
were fixed; both linked documents were revised accordingly. This does not
change the criteria in §3 above, does not open the gate, and does not mark
either linked document Accepted.

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
- GitHub comment ID `4924917266` on PR #136 (`AdamsOdoo/Adams`) —
  control-room acceptance of this criteria proposal (as criteria only) and
  of the MBQ-55 product-template/product-variant naming/schema proposal —
  access: Accessible, 2026-07-09.

**Next step:** this criteria proposal and the companion
[`mbq-55-product-binding-naming-schema-proposal.md`](./mbq-55-product-binding-naming-schema-proposal.md)
(product-template/product-variant portion) are now Accepted. The
product-domain implementation gate itself remains closed, and Task 010
remains unauthorized, until every criterion in §3 is confirmed satisfied
and a distinct, explicit ChatGPT gate-opening act occurs.
