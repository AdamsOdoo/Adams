# DEC-014 — Master Blueprint Sprint B: Product, Customer, and Sale/Order Domain Blueprint

> **Proposed decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared in **Master Blueprint Sprint B** after DEC-013
> acceptance (2026-07-03) closed Master Blueprint Part A. Proposes
> accepting the **product, customer, and sale/order domain blueprint**
> (Part B). Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-011**, Proposed for ChatGPT review).

## Status

**Proposed for ChatGPT review.** Not accepted. Not implementation-
authorizing under any outcome — see *No implementation authorized* below.

> **Revision note (2026-07-03, PR #72 review — REVISE before Fable
> review).** ChatGPT reviewed PR #72 and requested revision before
> routing to Fable. Fixed: (1) withdrew the reading that retrospective
> sync-center/dashboard visibility satisfies the "no blind create" /
> preview requirement for automated product/customer imports — replaced
> with an explicit, proposed **pre-create duplicate check + six-condition
> auto-create gate** policy (Part B §A.2/§A.9/§B.2/§B.9), tracked as new
> row **MBQ-59**; interactive/batch create-bind/write is unaffected and
> still requires a blocking preview. (2) Corrected §A.4's wording so it no
> longer implies ordinary Odoo record writes autonomously queue Shopify
> update jobs — an update job requires an explicit operator action (or a
> later accepted controlled trigger, still open). (3) Generalized the
> §I error-mapping table's order-domain "Shopify permission/scope/auth"
> cell — replaced the specific `read_all_orders` claim with generalized
> wording, since exact scope requirements were not verified this sprint
> (already covered by MBQ-06/MBQ-09; no new row added). (4) Verified
> `productVariantsBulkUpdate` against its official reference page
> (accessed 2026-07-03) and cited it directly, replacing the earlier
> under-cited claim. This revision does **not** change DEC-014's status —
> still **Proposed for ChatGPT review**, not accepted — and does not
> change DEC-003 through DEC-013, start Sprint C, or start the UI/UX
> Screen Design Blueprint.

## Date

2026-07-03.

## Scope

**Master Blueprint Sprint B only** — the product, customer, and
sale/order **domain blueprints**: product import/export/update (variants,
options, media, price, preview/diff, draft-first, publish mechanism);
customer import/matching (no export); order import + financial-evidence
capture + the total-check guard; cross-domain sequencing; and the
Sprint-B-owned open-questions register rows (MBQ-23 through MBQ-31, plus
five newly added rows MBQ-55 through MBQ-59 — MBQ-59 added in the PR #72
revision). Does **not** cover
inventory or fulfillment (Sprint C, not started), the UI/UX Screen Design
Blueprint (Part D, not started), exact GraphQL operation bodies beyond
what is explicitly cited and verified, exact Python method design, Odoo
XML/CSV artifacts, tests, or implementation tickets. Does **not** modify
DEC-003 through DEC-013.

## Accepted context

- **DEC-003 through DEC-013 are all Accepted by ChatGPT** (DEC-013 on
  2026-07-03, after PR #70; PR #71 acceptance patch merged as merge
  commit `283a38f26ef90fca2a53c18ff6faf4775da4a2ee`).
- **AR-002 through AR-010 are all Accepted**
  (`../05-qa/architecture-review-log.md`).
- **RA-001 through RA-023 are binding rejected approaches**
  (`../05-qa/rejected-approaches-log.md`); this sprint checked the log and
  reintroduces none of them.
- **PR #71 merged into `Shopify-connector`**, merge commit
  `283a38f26ef90fca2a53c18ff6faf4775da4a2ee` — confirmed as this sprint's
  required base before editing.
- **Master Blueprint Part A (core/common substrate) is accepted via
  DEC-013** — the job/log/error/retry abstraction, binding contract
  (per-domain concrete models on a core abstract contract, resolving
  MBQ-11), operator surfaces (setup wizard/dashboard/sync center/error
  center), feature-flag mechanism direction, and access blueprint are all
  reused, not re-derived, by this sprint.
- **Master Blueprint Part B was not started** before this sprint —
  confirmed before editing.
- **MBQ-23 through MBQ-31 exist and are routed to Sprint B** — confirmed
  before editing.
- **MBQ-53 remains open** and still blocks operator-facing screen
  implementation — confirmed before editing, unaffected by this sprint.
- **Implementation is still blocked** — confirmed before editing,
  unaffected by this sprint.

## Proposed decision

Accept **Master Blueprint Part B — Product, Customer, and Sale/Order
Domain Blueprint**
([`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md))
as the blueprint-level design for the product, customer, and sale/order
domains, namely:

1. **Product domain** — product-template and product-variant binding
   ownership under `shopify_connector_product` (Part B §A.1/§A.8); the
   import/export/update flow structure (§A.2–§A.4), including the
   corrected §A.4 wording that an update job requires an explicit
   operator action (or a later accepted controlled trigger), never an
   ordinary Odoo write alone; variant/option handling bounded to DEC-007
   §1 (§A.5), including the **proposed mutation-strategy direction**
   (prefer `productVariantsBulkCreate`/`productVariantsBulkUpdate` for
   variant-only updates, `productSet` for first-time combined export/full
   resync, §A.5.2, both mutations now cited against their official
   reference pages); SKU/barcode matching (§A.6); template-vs-variant
   identity separation (§A.7); duplicate-prevention preview, including
   the **proposed automated import create/bind policy** (§A.2/§A.9,
   extended to Customer §B.2/§B.9 — a pre-create duplicate check plus a
   six-condition auto-create gate, new open question **MBQ-59**,
   explicitly **not** an already-accepted interpretation of DEC-003/
   DEC-006); the **proposed draft/publish mechanism** (`Product.status` +
   unpublished-by-default `productCreate` + `publishablePublish`, §A.10);
   the destructive-write guard (§A.11); source-of-truth choices (§A.12);
   media (§A.13) and price/compare-at (§A.14) handling per DEC-007 §2/§3;
   publish/draft safety (§A.15); preview/review states (§A.16); product
   job types (§A.17); and the error/retry mapping (§A.18, consolidated in
   §I).
2. **Customer domain** — customer import/matching folded into
   `shopify_connector_sale` (§B.1/§B.8); import flow and the **proposed
   automated import create/bind policy** applied to the customer domain
   (§B.2, mirroring §A.2, MBQ-59); the customer-specific match-key
   ordering restated from DEC-006/DEC-012 (§B.3); the unchanged no-export
   and no-name-only-matching deferrals (§B.4/§B.5); the no-PII/missing-
   email posture (§B.6); the **proposed default-customer fallback
   direction** (single flagged fallback partner per store, §B.7);
   duplicate-prevention preview (§B.9); privacy/protected-data
   minimization (§B.10); customer job types (§B.12); and the **proposed
   MBQ-31 resolution recommendation** (email-only automatic match key,
   §B.13).
3. **Sale/order domain** — order binding ownership under
   `shopify_connector_sale` (§C.1); the layered order-import flow (§C.2);
   order identity/duplicate prevention (§C.3); order line mapping (§C.4);
   the **proposed whole-order-hold rule** for an unmatched product line
   (§C.5); the **proposed two-path customer-resolution rule** for order
   import (§C.6); financial-evidence capture (§C.7); the **proposed
   total-check guard definition** (computed evidence sum vs. Shopify
   order total, tolerance TBD, routed to the existing `financial total
   mismatch` error class, §C.8); tax/shipping/discount/payment evidence
   handling per DEC-007 §6 (§C.9); the **proposed gateway → journal
   mapping concept** (§C.10); the unchanged no-invoice/payment-automation
   and deferred-refund/cancellation postures (§C.11/§C.12); manual-review
   trigger mapping (§C.13); the **proposed MBQ-26 resolution
   recommendation** (existing error/sync-center surfaces, extended, no
   dedicated screen, §C.14); order job types (§C.15); and the
   error/retry mapping (§C.16, consolidated in §I).
4. **Cross-domain sequencing** — product-binding-before-order-line,
   customer-binding-before-order-assignment, total-check-guard-before-
   finalize, uniform manual-review routing, shared reconciliation
   backstop, and the manual/scheduled/webhook/reconciliation trigger table
   (Part B §D).
5. **The consolidated error-class/retry mapping** (Part B §I) — no new
   error class is added to the fixed Part A §D.4 16-class registry; every
   product/customer/order failure mode maps into an existing class.
6. **The open-questions register updates** — MBQ-23 through MBQ-31
   updated with proposed resolutions/partial resolutions/carried-forward
   status (Part B §J); five new rows added, MBQ-55 through MBQ-59
   (MBQ-59 added in the PR #72 revision).

## Explicit acceptance points (for ChatGPT's review)

**A. Mutation-strategy direction (MBQ-23).** Proposes preferring
`productVariantsBulkCreate`/`productVariantsBulkUpdate` for variant-only
updates after first export, and `productSet` for first-time combined
product+variant export or an explicit full-state resync — both gated by
the same destructive-write preview regardless of which is chosen. Grounded
in official `productSet`/`productVariantsBulkCreate` documentation
(accessed 2026-07-03). Exact implementation choice remains open
(**MBQ-23 stays partially resolved, not fully resolved**).

**B. Draft/publish mechanism (MBQ-25).** Proposes `Product.status`
(`DRAFT`) plus withholding `publishablePublish` as the two composable
safety levers for draft-first export, grounded in official Shopify
documentation (accessed 2026-07-03: `status` enum, `productCreate`
unpublished-by-default behaviour, `publishablePublish` mutation).
Exact channel-selection UX remains open (**MBQ-25 stays partially
resolved**).

**C. Order-import operator touchpoints (MBQ-26).** Proposes that the
existing error-center/sync-center surfaces (Part A §G/§H), extended with
an inline financial-evidence breakdown and direct matching-flow links, are
sufficient — **no dedicated order-import screen is proposed.** This is the
one row where the register's stated decision owner is explicitly
"ChatGPT (Sprint B)" — this section is a **recommendation for ChatGPT's
direct decision**, not a self-accepted resolution.

**D. Default-customer fallback (MBQ-29).** Proposes a single, clearly-
flagged fallback partner per store for genuine no-PII orders only — never
for ordinary matching failures, which follow the normal customer-import
creation path instead. Whether one shared fallback partner per store is
sufficient, or per-order anonymous identity is needed, remains open
(**MBQ-29 stays partially resolved**).

**E. Final customer match-key set (MBQ-31).** Proposes **email as the
sole automatic match key** (beyond an existing binding); phone and name
stay advisory/manual-only. This is the second row where the register's
decision owner is explicitly "ChatGPT (Sprint B)" — a **recommendation for
ChatGPT's direct decision**, not a self-accepted resolution.

**F. Total-check guard definition (new blueprint-level detail, not a
prior MBQ row by itself).** Proposes the concrete comparison mechanism
(computed evidence sum vs. Shopify order total) that operationalizes the
already-accepted DEC-007 §6 "totals must reconcile" requirement, routing
any mismatch to the already-accepted `financial total mismatch` error
class (Part A §D.4/§D.5.5, "conservative, never silent"). Exact tolerance
and exact Shopify total field remain open (new row **MBQ-56**).

**H. Automated import create/bind policy (MBQ-59 — added in the PR #72
revision, an open decision, not an already-accepted interpretation).**
Proposes that for automated (webhook/scheduled/reconciliation-triggered)
product/customer import, "no blind create" is satisfied by a **pre-create
duplicate check** plus a **six-condition auto-create gate** (setup
complete; domain enabled; source strategy permits import-side creation;
confident, unambiguous match; no duplicate-risk/binding-conflict/
destructive-write-guard condition triggered; fully logged before/after/
audit detail) — never by the sync-center/dashboard's later, retrospective
display of the outcome, which is audit/log visibility only. This
explicitly **withdraws** this document's earlier wording, which had read
retrospective visibility as satisfying the preview requirement. Interactive/
batch create-bind/write (a manual matching session, a bulk onboarding
pass, or any operator-triggered export/update) is unaffected and still
requires a blocking, synchronous preview before the operator confirms.
This is a **proposed policy, pending ChatGPT's acceptance at this DEC-014
review** — not a self-decided resolution of the underlying DEC-003/
DEC-006 "no blind create" tension with DEC-005's layered automation model
(**MBQ-59 stays open, not resolved, by this proposal alone**).

**I. Still open.** This proposal does not resolve every MBQ. Kept open
where appropriate: **MBQ-04, MBQ-08, MBQ-53, MBQ-54** (unchanged, not
addressed by this sprint), **MBQ-24** (media delete-on-omit — checked,
not resolved), **MBQ-27** (Odoo-side tax-representation mechanism —
official-doc check attempted, inconclusive), **MBQ-28** (Domain 9
draft-artifact guard — not triggered), **MBQ-30** (gateway→journal
mapping — concept proposed, exact schema open), **MBQ-59** (automated
import create/bind policy — proposed, not resolved, see point H), and the
five new rows **MBQ-55 through MBQ-59**.

**What this acceptance (if granted) would NOT do:**

- Does **not authorize implementation** under any circumstance (see *No
  implementation authorized* below).
- Does **not start Sprint C** — Master Blueprint Sprint C (Inventory and
  Fulfillment Domain Blueprint) is the next recommended sprint, not
  started.
- Does **not start the UI/UX Screen Design Blueprint** (Part D, MBQ-53
  stays open).
- Does **not change** DEC-003 through DEC-013.
- Does **not** finalize MBQ-26 or MBQ-31 beyond what ChatGPT explicitly
  confirms — both are recommendations, named as such throughout.
- Does **not** finalize MBQ-59 (automated import create/bind policy) —
  it is a proposed policy pending this review, not a self-decided
  resolution.

## What this decides (if accepted)

- The blueprint-level design of the product, customer, and sale/order
  domains (items 1–6 above) as the binding basis for later implementation
  planning, subject to the "Explicit acceptance points" above.
- The proposed resolutions/partial resolutions for MBQ-23, MBQ-25,
  MBQ-29, and MBQ-30 (direction-level, exact detail still open).
- The proposed recommendations for MBQ-26 and MBQ-31 (both explicitly
  ChatGPT-decision-owner rows).
- The proposed automated import create/bind policy (MBQ-59) — open,
  pending this review, not self-decided (see Explicit acceptance point H).

## What this does NOT decide

- **No implementation authorization** — under any outcome of this review.
- No inventory or fulfillment **domain blueprint** (Sprint C, not
  started).
- No UI/UX Screen Design Blueprint (Part D, not started; MBQ-53 stays
  open).
- No exact Odoo model/field names, view/menu XML IDs, security groups,
  access CSV rows, or record rules (Part B is concept/contract-level
  only).
- No exact GraphQL mutation body, Python method design, retry/backoff
  constants, cron cadence, or reconciliation cadence/scope.
- No change to DEC-003 through DEC-013, to any AR row, or to any RA row.
- No resolution of any open-question row except by explicitly recording
  it as resolved/partially resolved/carried forward (the register
  routes; it does not silently decide).

## Open questions

Centralized in
[`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
Headline rows for this record's review: **MBQ-23** (variant-write
mutation strategy — partially resolved), **MBQ-24** (media delete-on-omit
— carried forward), **MBQ-25** (draft/publish mechanism — partially
resolved), **MBQ-26** (order-import operator touchpoints — proposed
resolution, ChatGPT decision), **MBQ-27** (tax representation — carried
forward), **MBQ-28** (Domain 9 guard — not triggered), **MBQ-29**
(default-customer fallback — partially resolved), **MBQ-30**
(gateway→journal mapping — partially resolved), **MBQ-31** (customer
match-key set — proposed resolution, ChatGPT decision), **MBQ-59**
(automated import create/bind policy — proposed, open, added in the PR
#72 revision), **MBQ-55 through MBQ-59** (new rows, all open).

## Risks and mitigations

1. **Risk:** the mutation-strategy proposal (MBQ-23) could be read as a
   final implementation choice. **Mitigation:** explicitly labelled
   `[Blueprint proposal]`, direction only; MBQ-23 stays "partially
   resolved," not "resolved"; the destructive-write guard applies
   regardless of which mutation implementation planning eventually picks.
2. **Risk:** the whole-order-hold rule for unmatched products (§C.5)
   could be seen as overly conservative, blocking legitimate order
   volume if product sync lags order sync. **Mitigation:** the rule is
   explicitly tied to the mandatory, permanent total-check guard — a
   partial order cannot pass that guard either, so the alternative
   (partial creation) was evaluated and rejected as introducing a second,
   duplicate total-check path; **MBQ-57** is added so this rule can be
   revisited in a future review if evidence emerges that it is too
   conservative in practice.
3. **Risk (confirmed and fixed in the PR #72 revision):** an earlier draft
   of §A.2/§B.2 read retrospective sync-center/dashboard visibility as
   satisfying the "no blind create" / preview requirement for confident,
   automated creates — ChatGPT correctly flagged this as weakening
   DEC-003/DEC-006's guard, since retrospective visibility is audit, not
   preview. **Mitigation (applied):** that reading is explicitly
   withdrawn; §A.2/§A.9/§B.2/§B.9 now require a **pre-create** duplicate
   check plus a six-condition auto-create gate before any automated
   create/bind, with `blocked_manual_review` as the fallback for any
   failed condition — tracked as new open question **MBQ-59**, labelled
   `[Blueprint proposal, pending DEC-014]` throughout, not an
   already-accepted interpretation. Synchronous confirmation for every
   ambiguous/binding-conflict/duplicate-risk state (DEC-009) is
   unchanged and unweakened; interactive/batch create-bind/write
   continues to require a blocking preview.
4. **Risk:** MBQ-26 and MBQ-31 recommendations could be mistaken for
   already-decided outcomes since they appear inside an otherwise
   detailed blueprint. **Mitigation:** both are labelled
   "recommendation to ChatGPT" everywhere they appear (Part B §C.14/§B.13,
   this record's Explicit acceptance points C/E, and the register rows
   themselves), and both name their register-recorded decision owner as
   "ChatGPT (Sprint B)" explicitly.
5. **Risk:** the two targeted official-doc checks that returned
   inconclusive results (MBQ-24 media; MBQ-27 Odoo tax mechanism) could
   be silently dropped as "checked and fine." **Mitigation:** both are
   explicitly recorded as "carried forward, open" in the register and in
   Part B, with the exact check performed and its inconclusive result
   stated, per `CLAUDE.md` §7's "no unsupported claims" rule.

## No implementation authorized

**This record does not authorize implementation.** Acceptance, if
granted, is a documentation-level blueprint acceptance only. No code,
Odoo module, model, view, controller, security file, manifest, test, or
CI change is created or permitted by this record, and none may be created
until ChatGPT separately opens the implementation gate per the Phase 1
research-phase-exit criteria (`../05-qa/quality-feedback-loop.md` §10)
and `CLAUDE.md` §5 — **and, for any operator-facing screen/view/UI flow,
the accepted Part D — UI/UX Screen Design Blueprint** (see
`../03-architecture/master-blueprint.md` "Criteria for when implementation
may later be opened"). **Acceptance of this record alone would not open
that gate.**

## Next sprint recommendation

**Master Blueprint Sprint C — Inventory and Fulfillment Domain Blueprint**
(Part C): convert DEC-010/DEC-011 into the inventory and fulfillment
domain blueprints, resolving or routing the Sprint-C-owned open-questions
register rows (§5/§6). **Not started — this is the next recommended
sprint only after ChatGPT/Fable review and any required revision/
acceptance process for this record (DEC-014).** Sprint D (UI/UX Screen
Design Blueprint, resolving MBQ-53) and Sprint E (implementation-planning
bridge) remain the proposed sequence after Sprint C, per
`master-blueprint.md`'s "this is not an exhaustive or final list"
caveat.

## Review / change control

- **This record proposes accepting Master Blueprint Part B only.** No
  accepted decision is re-litigated; no rejected approach is
  reintroduced.
- **Related:** AR-011 (`../05-qa/architecture-review-log.md`, Proposed
  for ChatGPT review); the companion Part B blueprint document above;
  DEC-003 through DEC-013 (accepted context, unmodified).
- **Changes** to this record require ChatGPT review, mirroring the
  DEC-004 through DEC-013 change-control pattern.
