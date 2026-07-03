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
**AR-007 and AR-008 are now also accepted by ChatGPT**, via DEC-010 and
DEC-011 respectively (below — see the third "Also accepted" section),
**accepted 2026-07-02** after PR #66 merged into `Shopify-connector` and
Fable's minor-change review was applied. **All architecture decisions
AR-002 through AR-008 are now accepted.** DEC-003/004/005/006/007/008/009
remain unchanged. **Implementation remains blocked; DEC-008, DEC-009,
DEC-010, and DEC-011 do not authorize implementation.** RA-018 through
RA-023 are now binding rejected approaches (`../05-qa/rejected-approaches-log.md`).
Recommended next: a **UX/operator-flow sprint**, then the **Master
Blueprint**, then **implementation only after a separate ChatGPT gate**.
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
the time of this acceptance** (AR-007/AR-008 were later proposed via DEC-010/DEC-011 and
are **now accepted by ChatGPT on 2026-07-02** via DEC-010/DEC-011 — see the third "Also
accepted" section below) — neither edits DEC-003/004/005/006/007 (all remain unchanged),
and **neither authorizes implementation.** This acceptance makes **RA-011 through RA-017**
(`../05-qa/rejected-approaches-log.md`) binding rejected approaches. See
[`../03-architecture/ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md)
and
[`../03-architecture/ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md)
for the evidence-backed briefs behind each decision.

**Also accepted:**
[`DEC-010-inventory-architecture-strategy.md`](./DEC-010-inventory-architecture-strategy.md)
and
[`DEC-011-fulfillment-architecture-strategy.md`](./DEC-011-fulfillment-architecture-strategy.md)
— proposed 2026-07-02 (AR-007 + AR-008 Decision Preparation sprint, after DEC-008/DEC-009
acceptance, PR #65 merged into `Shopify-connector`) and **accepted by ChatGPT on
2026-07-02** after PR #66 merged into `Shopify-connector` and Fable's minor-change review
(**ACCEPT WITH MINOR CHANGES**) was applied. **Each is now explicitly `Status: Accepted by
ChatGPT`, acceptance date 2026-07-02 — no longer proposed.** DEC-010 resolves **AR-007
inventory architecture** (Odoo as ongoing source of truth for Shopify inventory
write-back, a controlled first-sync import, inventory identity keyed on `(store,
inventory_item_id, location_id)`, an explicit non-inferred location mapping, the DEC-007
first-push guard honored in full, layered sync, and the DEC-009 ambiguous-outcome retry
rule applied to inventory writes); DEC-011 resolves **AR-008 fulfillment architecture**
(validated `stock.picking` as the trigger, FulfillmentOrder-based mutations only, matched
order/FulfillmentOrder/line/quantity, the DEC-007 no-notification-by-default guard
honored in full, single-fulfillment-location Phase 1 posture with multi-package/
multi-location deferred, and the DEC-009 ambiguous-outcome retry rule applied to
fulfillment writes). **Neither decides implementation details, neither edits
DEC-003/004/005/006/007/008/009, and neither authorizes implementation.** This
acceptance also ratifies the shared Shopify Location reference clarification against
DEC-008: `shopify_connector_core` may hold a minimal Shopify-side Location reference
(never Odoo-location IDs or mapping decisions); `shopify_connector_inventory` keeps
owning Odoo↔Shopify mapping; `shopify_connector_fulfillment` never depends on
`shopify_connector_inventory`; DEC-008's dependency direction is unchanged and no new
module is created. The six proposed-rejection rows tied to these DEC files
(`rejected-approaches-log.md` RA-018 through RA-023) **became binding final rejected
approaches** on this same acceptance — see that log's own acceptance note. See
[`../03-architecture/ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md)
and
[`../03-architecture/ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md)
for the evidence-backed briefs behind each decision, and
[`../03-architecture/ar007-ar008-evidence-refresh.md`](../03-architecture/ar007-ar008-evidence-refresh.md)
for the small targeted Odoo-side official-source check performed to ground them. **All
architecture decisions AR-002 through AR-008 are now accepted.** DEC-012 (UX/operator-flow
strategy, resolving AR-009) is **now also accepted** — see the "Also accepted" entry
below. Recommended next: the **Master Blueprint**, then **implementation only after a
separate ChatGPT gate**.

**Also accepted:**
[`DEC-012-ux-operator-flow-strategy.md`](./DEC-012-ux-operator-flow-strategy.md) —
proposed 2026-07-02 (UX / Operator-Flow Decision Preparation sprint, after PR #67
merged into `Shopify-connector`; PR #68) and **accepted by ChatGPT on 2026-07-03**
after PR #68 merged into `Shopify-connector` (merge commit
`7d01617fdd0fd70d6a1d83d57918b045296550ac`) and Fable's minor-change review
(**ACCEPT WITH MINOR CHANGES**) was applied. **Each is now explicitly `Status:
Accepted by ChatGPT`, acceptance date 2026-07-03 — no longer proposed.** DEC-012
resolves **AR-009 UX/operator-flow strategy**: ten operator flows (initial setup
wizard, store settings, dashboard/command center, sync center/job monitor, error
center/recovery, matching/duplicate-prevention, product import/export/update,
inventory, fulfillment, and a conceptual permissions/roles model), each built
directly on the already-accepted DEC-003 through DEC-011 "UX implications" sections.
**Does not decide** exact Odoo views/menus/widgets, exact field names, exact security
groups/access CSVs, exact copy/wording, or the feature-flag/per-store
capability-configuration mechanism (DEC-008 routes the mechanism itself to the Master
Blueprint; this record proposes only the operator-facing experience). **DEC-003
through DEC-011 remain unchanged, and DEC-012 does not authorize implementation.**
See [`../02-product/ux-operator-flow.md`](../02-product/ux-operator-flow.md) for the
full proposal and
[`../03-architecture/ux-operator-flow-architecture-bridge.md`](../03-architecture/ux-operator-flow-architecture-bridge.md)
for the traceability mapping to DEC-003 through DEC-011. This acceptance satisfies the
last-named Phase 1 research-phase-exit criterion in
`../05-qa/quality-feedback-loop.md` §10 ("a UX/operator-flow sprint accepted, or
explicitly parallelized") — acceptance of DEC-012 alone does **not** open the
implementation gate; the **Master Blueprint** is next, and a separate ChatGPT
implementation-gate approval remains required before any implementation.

**Also accepted:**
[`DEC-013-master-blueprint-core-substrate.md`](./DEC-013-master-blueprint-core-substrate.md) —
proposed 2026-07-03 (Master Blueprint Sprint A, prepared after PR #69 merged
into `Shopify-connector`, merge commit
`305f396bcbd2656a4282ed18c5983540503b5502`) and **accepted by ChatGPT on
2026-07-03** after PR #70 merged into `Shopify-connector` (merge commit
`5c44971d1df84d5657da0164bf874b1125aee64f`), following Fable's review
(**ACCEPT WITH MINOR CHANGES**) and the Fable revision + tiny consistency fix
applied before merge. **Status: Accepted by ChatGPT, acceptance date
2026-07-03 — no longer proposed.** Accepts the **Master Blueprint index**
and the **core/common substrate blueprint (Part A)**:
[`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
[`../03-architecture/master-blueprint-core-substrate.md`](../03-architecture/master-blueprint-core-substrate.md),
and the central open-questions register
[`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md)
(MBQ-01–MBQ-54). Covers the `shopify_connector_core` module boundary, core
configuration-object concepts, the binding abstraction (accepting the
per-domain-concrete-on-core-contract schema-shape direction, resolving the
fork DEC-006/DEC-008 explicitly routed to the Master Blueprint — MBQ-11), the
job/log/error/retry abstraction, setup-wizard/dashboard/sync-center/
error-center blueprints, the DEC-008-routed feature-flag mechanism direction
(resolving MBQ-07 at blueprint-direction level), a blueprint-level four-role
access design (no CSVs, proposed names only; role hierarchy accepted,
resolving MBQ-45 partially and MBQ-47 fully), and cross-module extension
rules. This acceptance also confirms that **Part D — UI/UX Screen Design
Blueprint — remains required before implementation of any operator-facing
screen** (MBQ-53 stays open). **Resolves AR-010** in
`../05-qa/architecture-review-log.md`. **Does not authorize implementation
under any outcome; does not start any product/customer/sale/inventory/
fulfillment domain blueprint (routed to Master Blueprint Sprint B, next
recommended but not started); DEC-003 through DEC-012 are unchanged.**
MBQ-04, MBQ-08, MBQ-53, and MBQ-54 remain open.

**Also present (not yet accepted):**
[`DEC-014-master-blueprint-product-customer-sale.md`](./DEC-014-master-blueprint-product-customer-sale.md) —
proposed 2026-07-03 (Master Blueprint Sprint B, prepared after PR #71
merged into `Shopify-connector`, merge commit
`283a38f26ef90fca2a53c18ff6faf4775da4a2ee`; revised twice on PR #72 — once
after ChatGPT review, once after Fable review returned REVISE). **Status:
Proposed for ChatGPT review — not accepted.** Proposes accepting the
**Part B — Product, Customer, and Sale/Order Domain Blueprint**
(`../03-architecture/master-blueprint-product-customer-sale.md`):
product import/export/update (variant-mutation-strategy direction citing
both `productVariantsBulkCreate` and `productVariantsBulkUpdate` official
docs, draft/publish mechanism, media/price handling); customer import/
matching (default-customer-fallback direction, proposed email-only
match-key recommendation); order import (whole-order-hold rule for
unmatched products, total-check guard definition, proposed order-import
operator-touchpoint recommendation, gateway→journal mapping concept,
narrowed order-edit/`ORDERS_UPDATED` posture); and the **proposed
automated import create/bind policy** (MBQ-59, routed via accepted Part A
per-class mechanisms — not a single collapsed `blocked_manual_review`
state). Proposes resolutions/partial resolutions for **MBQ-23/25/29/30**,
recommendations for **MBQ-26/31** (both ChatGPT-decision-owner rows), and
carries forward **MBQ-24/27/28/59** unresolved (MBQ-59 remains fully
open, not partially resolved, not accepted); adds **MBQ-55 through
MBQ-59**. **Does not authorize implementation; does not start Sprint C;
does not start the UI/UX Screen Design Blueprint; DEC-003 through DEC-013
are unchanged.** MBQ-04, MBQ-08, MBQ-53, and MBQ-54 remain open,
untouched by this proposal.
