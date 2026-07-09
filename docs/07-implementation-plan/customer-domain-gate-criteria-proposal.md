# Customer-Domain Implementation Gate — Criteria Proposal (Task 011 Scope Only)

> **Documentation-only proposal. Does not open the customer-domain
> implementation gate.** Prepared alongside
> [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
> mirroring the structural pattern of
> [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md)
> (the accepted product-domain gate criteria, PR #136) and of
> [`limited-core-implementation-gate.md`](./limited-core-implementation-gate.md)
> and the Task 003/006C gate documents, but as a **criteria proposal only**,
> not a gate-opening act itself, and **not yet reviewed or accepted by
> ChatGPT** — unlike the product-domain document this one mirrors, which is
> already Accepted.

## 1. Status

> **Revision note (2026-07-09, ChatGPT control-room review, comment ID
> `4928244425`).** ChatGPT required revision before merge to
> [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)
> (an ambiguous customer match must not create a placeholder
> `shopify.connector.customer.binding` row, since `partner_id` is required
> and candidate selection would be an automatic guess) and to the fallback-
> partner boundary (must not drag order-import behavior into Task 011). This
> document adds a new criterion 15 requiring the future Task 011 final
> prompt to explicitly define ambiguous-match handling, and revises
> criterion 13 to state the fallback-partner Task 011/Task 012 boundary
> (Posture A) explicitly. **Still proposed only, not yet accepted; PR
> remains draft, unmerged; no implementation authorized.**

- **Proposed only. Not yet reviewed or accepted by ChatGPT.**
- **Does not open the customer-domain implementation gate.** Even a future
  acceptance of the criteria list in §3 as the correct criteria is a
  distinct act from confirming those criteria are satisfied, which is
  itself distinct from the gate-opening act — mirroring exactly the
  three-step separation `product-domain-gate-criteria-proposal.md` §1
  already established for the product domain.
- **Does not authorize Task 011, Task 012, or any other domain-sync task, or
  any code of any kind.**
- **Scoped to Task 011 (customer import/matching) only.** `shopify_connector_sale`
  is the accepted module home for **both** customer import/matching (Task
  011) **and** order import (Task 012) per DEC-008. This document proposes
  gate criteria for the **customer-import portion only** — it does not
  propose, define, or imply criteria for opening any gate covering order
  import. A separate future criteria proposal, informed by its own
  order-binding MBQ-55 naming pass, would be required before Task 012.

## 2. Purpose

[`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md)
and this session's
[`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md)
both name **"the 'sale domain gate' (`ui-ux-implementation-task-map.md`
Group 11's named prerequisite)"** as one of Task 011's own preconditions.
Neither that document, nor any other document in this repository, states
**what must be true** before ChatGPT can perform an opening act for the
customer-import portion of that gate — the same documentation gap
`master-implementation-readiness-checkpoint.md` identified for the "product
domain gate" before `product-domain-gate-criteria-proposal.md` closed it.

This document proposes a concrete, checkable list of criteria for that
future act, scoped to Task 011 only — nothing more. It does not itself
satisfy any of the criteria it lists, and it does not perform the act.

## 3. Proposed gate-opening criteria

**Not yet reviewed by ChatGPT.** Satisfaction status is marked per criterion
below, accurate as of this revision, not permanently fixed.

1. **Task 010 (product import/variant binding) closed and runtime-green.**
   PR #138 merged into `Shopify-connector` (merge commit
   `1f478032d8581a949fa7820847e5c1ab419586b4`); post-merge Odoo.sh runtime
   evidence is green (`shopify_connector_core` 187 tests,
   `shopify_connector_product` 61 tests, 0 failed, 0 error(s) of 220 tests);
   PR #139 (post-merge closure docs) also merged (merge commit
   `297f398da96d11d1f8f9e25a9d15570a66aed80a`). **Status: Satisfied.**
2. **MBQ-55 (customer-binding portion) accepted/closed.**
   [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md)
   proposes exact model/file/class/field names for the customer-binding
   model, but **is not yet accepted by ChatGPT.** **Status: Not yet
   satisfied.**
3. **Task 011's final implementation prompt has exact file/model/field
   names.** Depends on criterion 2's acceptance; a future final-prompt
   session would still have to convert the accepted naming into an actual
   `CLAUDE.md` §9 prompt. **Status: Not yet satisfied.**
4. **Exact allowed files and forbidden files defined** in that same future
   final prompt — depends on criterion 3. **Status: Not yet satisfied.**
5. **Customer first-sync dedup/match-confidence thresholds fixed, or
   explicitly scoped as an in-task decision, in the final Task 011 prompt.**
   Per `mbq-55-customer-binding-naming-schema-proposal.md` §12, that
   document does not fix them; a future final-prompt session must either
   fix the exact eligibility-check/match-confidence thresholds or
   explicitly declare them a narrow, named in-task design decision, per
   `CLAUDE.md` §9's own allowance for this. **Status: Not yet satisfied.**
6. **No order-import scope.** Already true of both
   `task-011-customer-import-matching-proposed.md` and this session's
   `task-011-customer-import-proposed.md` (explicit exclusion — "No order
   import (Task 012's scope)"). This criterion is satisfied today and must
   remain so; any future revision that reintroduces order-import scope into
   Task 011 would need its own separate ChatGPT decision, not a silent
   expansion. **Status: Satisfied.**
7. **No product/inventory/fulfillment scope.** Already true of both Task 011
   proposed-scope documents. **Status: Satisfied.**
8. **No UI/wizard/webhook/OAuth scope beyond a separately-gated screen.**
   Already true — Task 011's own documents require the UI implementation
   gate only for the Customer mapping screen (S8, Group 11), which is not
   part of the backend-only boundary this gate would authorize; the UI gate
   remains separately closed and unaffected by this proposal. **Status:
   Satisfied.**
9. **Tests defined.** The future final implementation prompt must name exact
   test files/fixtures.
   `mbq-55-customer-binding-naming-schema-proposal.md` §4 proposes
   starting-point test file names (`test_customer_binding.py`,
   `test_customer_import_matching.py`,
   `test_customer_duplicate_prevention.py`,
   `test_customer_fallback_partner.py`) — a future final prompt confirms or
   revises these, it does not have to invent them from nothing. **Status:
   Not yet satisfied** — starting-point names proposed, but not yet
   confirmed by an accepted document or a final implementation prompt.
10. **Rollback plan defined.** Both Task 011 proposed-scope documents already
    carry a Rollback section (single-PR revert; reverting drops the
    customer-binding model; any already-created `res.partner` records
    remain as ordinary, simply un-bound, Odoo data) — a future final prompt
    must restate this precisely, not invent a new plan. **Status:
    Satisfied.**
11. **Runtime/live Shopify dependency explicitly stated as absent or
    controlled.** Already true — "fake client tests allowed" per this
    project's own constraints; no live Shopify call beyond the existing,
    already-gated Task 003 API client. **Status: Satisfied.**
12. **Open blockers listed and classified as non-blocking for Task 011.**
    [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md)
    §5 provides this classification (MBQ-05, VAL-B2, TD-002, the fulfillment
    API model, the multi-server concurrency proof requirement, Lite/Full
    packaging — all classified non-blocking for Task 011's own narrow
    scope). This criterion requires that classification to be explicitly
    reconfirmed as still accurate at the time the gate is actually opened,
    not silently assumed unchanged indefinitely. **Status: Not yet
    satisfied** — reconfirmation is a point-in-time act to be performed when
    the gate-opening act itself is considered, not before (mirrors
    `product-domain-gate-criteria-proposal.md` criterion 12 exactly).
13. **Customer fallback-partner store-settings field proposed and reviewed,
    with an explicit Task 011/Task 012 boundary.**
    `mbq-55-customer-binding-naming-schema-proposal.md` §7.3 proposes
    `customer_fallback_partner_id` on `shopify.connector.store.settings` as
    the field's name and home model, and adopts **Posture A**: Task 011 may
    propose/implement only this config field as supporting substrate, with
    **zero order-resolution behavior, zero consumption of the field within
    Task 011's own flow, and zero coupling to order import** — the decision
    of when/how an order is actually routed to this partner, and its
    order-level audit marker, are entirely Task 012's own future scope. The
    future final implementation prompt must restate this boundary
    explicitly, not merely define the field. **Status: Not yet satisfied**
    — proposed only, not yet accepted or confirmed by a final implementation
    prompt.
14. **Address handling and company/person (`is_company`) classification
    explicitly scoped** (resolved, or explicitly excluded/deferred) in the
    final Task 011 prompt. Both remain **open, not yet decided anywhere in
    this repository** (restated unchanged from
    `task-011-customer-import-matching-proposed.md`). **Status: Not yet
    satisfied.**
15. **Ambiguous-customer-match handling explicitly defined in the final
    Task 011 prompt — added this revision, per ChatGPT control-room review
    (comment `4928244425`).** The future final implementation prompt must
    explicitly define: (a) that an ambiguous customer match (multiple
    plausible email/customer-key candidates) creates **no**
    `shopify.connector.customer.binding` row — `partner_id` is required, and
    a row cannot exist without one single confirmed candidate; (b) that the
    job/import attempt instead routes directly to `blocked_manual_review`
    with the `ambiguous match` sub-reason; (c) the exact job/log field(s)
    used to store candidate `res.partner` detail (never a binding row —
    `mbq-55-customer-binding-naming-schema-proposal.md` §9/§10/§12 item 7
    fixes the principle but not the exact field name(s)); and (d) that a
    binding row is created only once, and not before, an operator manually
    confirms exactly one candidate. **Status: Not yet satisfied** — the
    principle is now fixed by the naming proposal (this revision); the exact
    job/log field name(s) remain open for the final implementation prompt.

## 4. Gate closure rule

- **This criteria proposal is not yet Accepted.** Should ChatGPT accept it
  as criteria only, a future, distinct, explicit ChatGPT act would still be
  required to confirm every criterion in §3 satisfied before the gate
  itself opens — mirroring `product-domain-gate-criteria-proposal.md` §4's
  identical rule.
- **If opened, the gate would authorize exactly one future implementation
  session — Task 011 only** — mirroring the pattern already used for Task
  003 (AR-029), Task 006C (AR-031), and Task 010
  (`product-domain-gate-criteria-proposal.md` §7) — not a standing mandate
  for further customer- or sale-domain work, and **not** an authorization
  for Task 012 (order import), which would require its own separate
  criteria confirmation and its own separate gate-opening act, informed by
  its own order-binding MBQ-55 naming pass.
- **The gate would close again once the future Task 011 implementation PR
  is opened as draft.** That future PR must remain draft until ChatGPT
  reviews it — no session may mark it ready for review or merge it without
  a distinct, explicit ChatGPT review act.

## 5. Non-authorizations

This document does not:

- Open the customer-domain implementation gate, or any other implementation
  gate.
- Authorize Task 011, Task 012, any other domain-sync task, a setup wizard,
  OAuth/token-acquisition code, or any Lite/Full packaging implementation.
- Authorize any code, module, model, view, controller, security file,
  manifest, test, or CI file of any kind.
- Mark any criterion as satisfied that is not. §3 states each criterion's
  actual satisfaction status as of this revision: criteria 1, 6, 7, 8, 10,
  and 11 are satisfied; criteria 2, 3, 4, 5, 9, 12, 13, 14, and 15 remain
  unsatisfied. Satisfying every remaining criterion does not, by itself,
  open the gate — only a separate, explicit, future ChatGPT gate-opening act
  does that.
- Mark MBQ-55 as fully Accepted or Resolved — only its product-template/
  product-variant portion is Accepted; the customer-binding portion is
  proposed only (companion document, not yet accepted); the order-binding
  portion remains open.
- Propose, define, or imply criteria for opening any gate covering order
  import (Task 012) — that remains a separate, future, not-yet-scoped
  proposal.
- Claim ChatGPT accepted anything in this session. Nothing in this document
  is asserted as already accepted.

---

## Evidence / references

- [`product-domain-gate-criteria-proposal.md`](./product-domain-gate-criteria-proposal.md) —
  structural pattern this document mirrors — access: Accessible, this
  repository, observed 2026-07-09.
- [`task-011-customer-import-matching-proposed.md`](./task-011-customer-import-matching-proposed.md),
  [`task-011-customer-import-proposed.md`](./task-011-customer-import-proposed.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`ui-ux-implementation-task-map.md`](./ui-ux-implementation-task-map.md)
  Group 11 — access: Accessible, this repository, observed 2026-07-09.
- [`master-implementation-readiness-checkpoint.md`](./master-implementation-readiness-checkpoint.md) —
  access: Accessible, this repository, observed 2026-07-09.
- [`task-011-customer-import-gate-readiness.md`](./task-011-customer-import-gate-readiness.md) —
  companion readiness assessment, drafted this session — access:
  Accessible, this repository, observed 2026-07-09.
- [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
  AR-034 (product-domain gate-criteria acceptance pattern this proposal
  mirrors) — access: Accessible, this repository, observed 2026-07-09.

**Next step:** ChatGPT review of this criteria proposal alongside
[`mbq-55-customer-binding-naming-schema-proposal.md`](./mbq-55-customer-binding-naming-schema-proposal.md),
mirroring the PR #136 review pattern that accepted both the product-binding
naming proposal and the product-domain gate criteria together.
