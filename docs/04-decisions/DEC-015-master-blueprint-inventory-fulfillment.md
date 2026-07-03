# DEC-015 — Master Blueprint Sprint C: Inventory and Fulfillment Domain Blueprint

> **Proposed decision record** for the premium **Odoo 19 ↔ Shopify
> Connector**, prepared in **Master Blueprint Sprint C** after DEC-014
> acceptance (2026-07-03) closed Master Blueprint Part B. Proposes
> acceptance of the **inventory and fulfillment domain blueprint**
> (Part C). Companion documents:
> [`../03-architecture/master-blueprint.md`](../03-architecture/master-blueprint.md),
> [`../03-architecture/master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md),
> [`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
> Companion review-log entry:
> [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md)
> (**AR-012**, Proposed for ChatGPT review).

## Status

**Proposed for ChatGPT review. Not accepted.** Not implementation-
authorizing under any outcome — see *No implementation authorized* below.
Starting point: PR #73 merged into `Shopify-connector`, merge commit
`09829a804eef9c4099960f5604729f3a775793d1` (Accept DEC-014 Master
Blueprint Sprint B), confirmed as the base before editing.

## Date

2026-07-03.

## Scope

**Master Blueprint Sprint C only** — the inventory and fulfillment
**domain blueprints**: inventory module boundary and location-mapping
posture, quantity source/meaning, first-push guard, update direction,
sync posture, idempotency/retry, mapping-failure handling, multi-location
posture, product/variant binding dependency, and safety guards; fulfillment
module boundary, FulfillmentOrder posture, `stock.picking` trigger,
order/line/quantity/location matching, tracking handling, customer-
notification posture, partial/backorder/cancellation/return/refund/
multi-package posture, location-mismatch guard, idempotency/retry, and
webhook/reconciliation posture; cross-domain sequencing; and the
Sprint-C-owned open-questions register rows (§5/§6). Does **not** cover
the UI/UX Screen Design Blueprint (Part D, not started), exact GraphQL
mutation bodies beyond what is explicitly cited and verified, exact
Python method design, Odoo XML/CSV artifacts, tests, or implementation
tickets. Does **not** modify DEC-003 through DEC-014.

## Accepted context

- **DEC-003 through DEC-014 are all Accepted by ChatGPT** (DEC-014 on
  2026-07-03, after PR #72; PR #73 acceptance patch merged as merge
  commit `09829a804eef9c4099960f5604729f3a775793d1`).
- **AR-002 through AR-011 are all Accepted**
  (`../05-qa/architecture-review-log.md`).
- **RA-001 through RA-023 are binding rejected approaches**
  (`../05-qa/rejected-approaches-log.md`); this sprint checked the log and
  reintroduces none of them.
- **PR #73 merged into `Shopify-connector`**, merge commit
  `09829a804eef9c4099960f5604729f3a775793d1` — confirmed as this sprint's
  required base before editing.
- **Master Blueprint Part A (core/common substrate) is accepted via
  DEC-013**, and **Part B (product/customer/sale-order) is accepted via
  DEC-014** — both reused, not re-derived, by this sprint.
- **Master Blueprint Part C was not started** before this sprint —
  confirmed before editing.
- **MBQ-32 through MBQ-43 exist and are routed to Sprint C** — confirmed
  before editing.
- **MBQ-53 remains open** and still blocks operator-facing screen
  implementation — confirmed before editing, unaffected by this sprint.
- **Implementation is still blocked** — confirmed before editing,
  unaffected by this sprint.

## Proposed decision

Accept **Master Blueprint Part C — Inventory and Fulfillment Domain
Blueprint**
([`master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md))
as the blueprint-level design for the inventory and fulfillment domains,
namely:

1. **Inventory domain** — inventory-level binding ownership under
   `shopify_connector_inventory` (§A.1); Shopify Location reference /
   Odoo location-mapping posture (§A.2); the ongoing Odoo-source-of-truth
   posture with a controlled one-time baseline import (§A.3); **two
   verified but non-equivalent candidate quantity sources**
   (`product.product.free_qty` and `stock.quant.available_quantity`,
   both newly cited against official Odoo 19.0 source, §A.4, proposing to
   partially resolve **MBQ-32** — Fable finding C1 corrected the earlier
   draft's over-claim that the two sources were equivalent; the source
   choice is substantive and not decided by this record); the
   first-push guard and confirmation-record concept, including a
   **proposed granularity recommendation** for ChatGPT's decision on
   **MBQ-33** and a **proposed confirmation-record concept** partially
   resolving **MBQ-38** (§A.5); the update-direction split (Odoo→Shopify
   ongoing, controlled Shopify→Odoo baseline only, §A.6); manual/
   scheduled/event-driven sync posture (§A.7); idempotency/retry posture
   applying Part A's job/log/error abstraction (§A.8); mapping-failure
   handling, including the **newly verified `INVENTORY_LEVELS_UPDATE`
   webhook topic**, proposing to resolve **MBQ-37** (§A.9); multi-location/
   multi-warehouse posture (§A.10); the product/variant binding
   dependency (§A.11); the consolidated safety-guard statement (§A.12);
   inventory job types (§A.13); and the error/retry mapping (§A.14,
   consolidated in §D).
2. **Fulfillment domain** — FulfillmentOrder/Fulfillment binding
   ownership under `shopify_connector_fulfillment` (§B.1); the
   FulfillmentOrder-exclusive posture restated from DEC-011 (§B.2); the
   validated-`stock.picking`-trigger posture, including a newly cited
   Odoo delivery-workflow official fact (§B.3); order/FulfillmentOrder/
   line/quantity matching via `lineItemsByFulfillmentOrder` (§B.4); the
   **proposed tracking-field resolution** (`stock.picking.
   carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id`, newly cited
   against official Odoo 19.0 source, §B.5, proposing to resolve
   **MBQ-39** and surfacing new open question **MBQ-60**); the customer-notification
   posture restated from DEC-007/DEC-011, with a **proposed
   recommendation** for ChatGPT's decision on **MBQ-41** (§B.6); the
   partial/backorder/cancellation/return/refund/multi-package posture,
   including a newly cited Odoo `backorder_id`/`backorder_ids` official
   fact partially resolving **MBQ-40** (§B.7); the **proposed
   location-mismatch-guard mechanism** partially resolving **MBQ-42** and
   **MBQ-43** (§B.8); idempotency/duplicate-prevention posture (§B.9);
   retry/error handling applying Part A's classes (§B.10); the
   webhook/reconciliation posture, including newly cited Shopify
   `FULFILLMENTS_*`/`FULFILLMENT_ORDERS_*` webhook topics and new open
   question **MBQ-61** (§B.11); fulfillment job types (§B.12); and the
   error/retry mapping (§B.13, consolidated in §D).
3. **Cross-domain sequencing** — the never-depends-on-inventory rule for
   fulfillment, shared product/variant-binding reuse, order-import-before-
   fulfillment-matching sequencing, domain independence between inventory
   push and fulfillment creation, uniform manual-review routing, shared
   reconciliation backstop, and the manual/scheduled/webhook/event-
   driven/reconciliation trigger table (Part C §C).
4. **The consolidated error-class/retry mapping** (Part C §D) — no new
   error class is added to the fixed Part A §D.4 16-class registry; every
   inventory/fulfillment failure mode maps into an existing class,
   including the two classes ("inventory location missing," "fulfillment
   notification confirmation missing") that Part A/B could only name, not
   instantiate, until this sprint.
5. **The open-questions register updates** — MBQ-32 through MBQ-43
   updated with proposed-resolved/proposed-partially-resolved/carried-
   forward status (Part C §G); four new rows added, MBQ-60 through
   MBQ-63 (MBQ-62/MBQ-63 added in a Fable-review revision, point M
   below).

## Explicit acceptance points (for ChatGPT's review)

**A. Quantity-source direction (MBQ-32) — proposed partially resolved,
pending this record's acceptance.** **Fable finding C1, corrected:** an
earlier draft of this point over-claimed that `product.product.free_qty`
and `stock.quant.available_quantity` were equivalent ("or, equivalently
at the per-location level..."). They are not. Proposes that the two
candidate Odoo ORM sources behind DEC-010's "Free to Use" semantic
concept are `product.product.free_qty` (context-scoped by
location/warehouse; compute `product.uom_id.round(qty_available −
reserved_quantity − expired_unreserved_qty)`, i.e. it also nets out
expired unreserved stock and applies UoM rounding) and, at the
per-location level, `stock.quant.available_quantity` (`quantity −
reserved_quantity`, with neither the expired-unreserved netting nor a
shown UoM-rounding step) — both grounded in official Odoo 19.0 source
code (`github.com/odoo/odoo`, `19.0` branch, accessed 2026-07-03). **The
two diverge whenever expired unreserved stock exists**, so the choice
between them is **substantive, not cosmetic**; this record does not
choose a final implementation source. This is the first time this
sprint (or any prior sprint) has cited the exact field/formula for
either candidate; DEC-010 had left the concept semantic only. Exact
source-selection/aggregation mechanism (context-based `free_qty` vs.
direct quant iteration, and how the latter would need to net out
expired-unreserved stock to match `free_qty`'s semantics if chosen) and
whether a configurable Forecast/On-Hand/Free-to-Use default is offered
remain open for implementation planning.

**B. First-push guard granularity (MBQ-33) — a recommendation for
ChatGPT's direct decision, not a self-accepted resolution.** Proposes
that the first-push guard fire per **mapped Odoo-location ↔ Shopify-
Location pair**, satisfying DEC-007's "no coarser than per-store" floor
while avoiding both under-granularity (one confirmation covering a
merchant's whole multi-warehouse operation) and over-granularity
(guard fatigue at the per-variant-location level).

**C. Ongoing apply-mode (MBQ-34) — a recommendation for ChatGPT's direct
decision, not a self-accepted resolution.** Proposes review-then-apply as
the Phase 1 default for ongoing (post-first-push) inventory writes,
consistent with DEC-003's "auto-apply not accepted as default MVP
behaviour."

**D. Mutation choice per trigger (MBQ-36) — proposed partially resolved, pending this record's acceptance.**
Proposes `inventorySetQuantities` (compare-and-set) as the default
mutation for all trigger types, given its concurrency-safety properties;
`inventoryAdjustQuantities` remains a candidate for narrower single-delta
event-driven pushes, not decided here.

**E. Shopify inventory webhook topic (MBQ-37) — proposed resolved, pending this record's acceptance.** Confirms
`INVENTORY_LEVELS_UPDATE` (plus `INVENTORY_LEVELS_CONNECT`/
`INVENTORY_LEVELS_DISCONNECT`) as the exact Shopify
`WebhookSubscriptionTopic` enum values for inventory-level changes,
grounded in official Shopify documentation (accessed 2026-07-03). This
was previously "unverified in repo docs." The underlying fact is
verified regardless of this record's outcome; the row itself formally
closes only if/when this record is accepted.

**F. First-push confirmation record concept (MBQ-38) — proposed
partially resolved, pending this record's acceptance.** Proposes a
blueprint-level confirmation-record concept
extending Part A's guard/audit record shape (preview snapshot, confirming
operator + timestamp, recorded source-of-truth, scope). Exact schema/
field names remain open for implementation planning.

**G. Tracking-field source (MBQ-39) — proposed resolved, pending this record's acceptance.** Confirms
`stock.picking.carrier_tracking_ref` (Char), `carrier_tracking_url`
(computed Char, via `carrier_id.get_tracking_link(picking)`), and
`carrier_id` (Many2one to `delivery.carrier`) as the exact Odoo 19.0
fields, defined in the `stock_delivery` module, grounded in official Odoo
19.0 source code (accessed 2026-07-03). This was previously unconfirmed
in repo docs (only a "no field name confirmed" open item existed). The
underlying fact is verified regardless of this record's outcome; the row
itself formally closes only if/when this record is accepted.
**Surfaces a new question (MBQ-60):** whether `shopify_connector_
fulfillment` requires `stock_delivery` (or `delivery`) as an Odoo
dependency, not previously considered by DEC-008 or DEC-011.

**H. Backorder-to-picking linkage (MBQ-40) — proposed partially resolved, pending this record's acceptance.**
Confirms `stock.picking.backorder_id`/`backorder_ids` as the exact Odoo
19.0 linkage fields, grounded in official Odoo 19.0 source code (accessed
2026-07-03). The delivery-specific backorder-wizard UX/copy nuance
flagged by `ar007-ar008-evidence-refresh.md` was not independently
re-verified this sprint and remains open.

**I. Notification-UI granularity (MBQ-41) — a recommendation for
ChatGPT's direct decision, not a self-accepted resolution.** Proposes
that a global/per-store notification default is sufficient for Phase 1
MVP, with a per-order override deferred to a later phase.

**J. Fulfillment location-confirmation mechanism (MBQ-42) — proposed
partially resolved, mechanism pending ChatGPT acceptance of this record.**
Proposes: a
live Shopify FulfillmentOrder `assignedLocation` read is treated as
authoritative for a specific fulfillment operation; the core Shopify
Location reference (Part A §B.4) is used only for naming/display and
mismatch-detection, never as an override authority. **Fable minor finding
2 — made explicit:** AR-006/DEC-009's accepted registry (Part A §D.4),
together with DEC-006's matching context, defines `ambiguous match` as
**multiple plausible matching candidates**. A fulfillment-location
mismatch is a **different**, deterministic scenario (exactly one
determined answer that disagrees with expectation, not multiple
candidates). This record proposes **reusing/widening `ambiguous match`**
for that scenario anyway, because the **operator outcome is identical**
(confirmation-required, routed to manual review) — this widening of an
already-accepted class's applicability is **part of what ChatGPT would be
accepting by accepting this record**, not an already-settled reading of
AR-006/DEC-009. No 17th top-level error class is added either way. If
ChatGPT judges this widening unsafe, the alternative is a dedicated new
open question for a location-mismatch sub-reason instead of reusing
`ambiguous match` — not adopted here, but named so it is not foreclosed.

**K. Core Location reference cache policy (MBQ-43) — proposed partially
resolved, pending this record's acceptance.** Proposes the precedence rule (live read always wins over the
cache for a specific operation) as fixed; exact refresh cadence/mechanism
remains open for implementation planning.

**L. New open questions (MBQ-60, MBQ-61).** MBQ-60 (whether
`shopify_connector_fulfillment` requires the `stock_delivery`/`delivery`
Odoo module) and MBQ-61 (whether/how the connector reacts to Shopify
FulfillmentOrder hold/cancellation-request/merge/split/reschedule
lifecycle events, newly confirmed as real webhook topics this sprint) are
proposed as new register rows — both genuinely new questions this
sprint's official-doc verification surfaced, neither previously
considered by DEC-010 or DEC-011.

**M. New open questions from Fable review (MBQ-62, MBQ-63) — added in a
Fable-review revision on the same PR, not part of the original
proposal.** **MBQ-62 (Fable finding C2):** the original draft of §A.7/
§A.13/§B.12/§C item 7 silently listed "event-driven enqueue" as if it
were a Part A §D.2 job-source enum value; DEC-010 accepted the Odoo-side
event trigger only as a **sync-trigger layer**, and this record does
**not** extend Part A's fixed job-source vocabulary. Which existing
source (if any) an Odoo-event-triggered inventory push or fulfillment
creation should record — or whether a DEC-level vocabulary extension is
needed — is routed to MBQ-62, new and open. **MBQ-63 (Fable minor
finding 4):** MBQ-37's verification covered only the
`INVENTORY_LEVELS_UPDATE` topic **string**; the webhook's payload shape,
subscription mechanics, and whether webhook-driven inventory import is
implemented in Phase 1 at all (versus left as a drift-detection
candidate only) remain a separate, broader open question, routed to
MBQ-63, new and open.

**What this acceptance (if granted) would NOT do:**

- Does **not authorize implementation** under any circumstance (see *No
  implementation authorized* below).
- Does **not start** the UI/UX Screen Design Blueprint (Part D, MBQ-53
  stays open) or Part E (implementation-planning bridge).
- Does **not change** DEC-003 through DEC-014.
- Does **not** finalize MBQ-33, MBQ-34, or MBQ-41 beyond what ChatGPT
  explicitly confirms — all three are recommendations, named as such
  throughout.
- Does **not** finalize MBQ-42's mechanism beyond what ChatGPT explicitly
  accepts.
- Does **not** authorize a new Odoo module dependency (`stock_delivery`/
  `delivery`) — MBQ-60 stays open, routed for ChatGPT's decision.
- Does **not** authorize any webhook subscription to, or handling logic
  for, the `FULFILLMENT_ORDERS_*` lifecycle family beyond ordinary
  creation/tracking — MBQ-61 stays open.

## What this decides (if accepted)

- The blueprint-level design of the inventory and fulfillment domains
  (items 1–5 above) as the binding basis for later implementation
  planning, subject to the "Explicit acceptance points" above.
- The proposed resolutions/partial resolutions for MBQ-32, MBQ-36,
  MBQ-37, MBQ-38, MBQ-39, MBQ-40, MBQ-42, and MBQ-43 (direction/fact
  level, exact residual detail still open where stated).
- The proposed recommendations for MBQ-33, MBQ-34, and MBQ-41 (all three
  explicitly ChatGPT-decision-owner rows).
- The four new open questions MBQ-60 through MBQ-63 (MBQ-60 and MBQ-61
  from the original proposal, point L; MBQ-62 and MBQ-63 added in the
  Fable-review revision, point M).

## What this does NOT decide

- **No implementation authorization** — under any outcome of this review.
- No UI/UX Screen Design Blueprint (Part D, not started; MBQ-53 stays
  open).
- No exact Odoo connector-side model/field names, view/menu XML IDs,
  security groups, access CSV rows, or record rules (Part C is
  concept/contract-level only; the Odoo-core/Odoo-module field names
  cited in this record are existing Odoo fields, not connector-proposed
  names).
- No exact GraphQL mutation body, Python method design, retry/backoff
  constants, cron cadence, or reconciliation cadence/scope beyond what is
  explicitly cited.
- No change to DEC-003 through DEC-014, to any AR row, or to any RA row.
- No resolution of any open-question row except by explicitly recording
  it as resolved/partially resolved/carried forward/new (the register
  routes; it does not silently decide).

## Open questions

Centralized in
[`../03-architecture/master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).
Headline rows for this record's review — **every "proposed
resolved"/"proposed partially resolved" outcome below is pending this
record's acceptance and remains formally `open` until then:**
**MBQ-32** (quantity source —
proposed partially resolved), **MBQ-33** (first-push granularity — recommendation, ChatGPT
decision), **MBQ-34** (ongoing apply-mode — recommendation, ChatGPT
decision), **MBQ-36** (mutation choice — proposed partially resolved), **MBQ-37**
(inventory webhook topic — proposed resolved), **MBQ-38** (confirmation-record
concept — proposed partially resolved), **MBQ-39** (tracking field source —
proposed resolved), **MBQ-40** (backorder linkage — proposed partially resolved), **MBQ-41**
(notification-UI granularity — recommendation, ChatGPT decision),
**MBQ-42** (location-confirmation mechanism — proposed partially resolved,
pending acceptance, including a proposed widening of `ambiguous match`,
Fable minor finding 2), **MBQ-43** (Location reference cache policy —
proposed partially resolved), **MBQ-60** through **MBQ-63** (new rows,
all open — MBQ-62/MBQ-63 added in a Fable-review revision, point M).

## Risks and mitigations

1. **Risk:** citing Odoo/GitHub source code directly (rather than
   Odoo's user-facing documentation pages) for exact field names could be
   read as a lower-tier source. **Mitigation:** this mirrors the
   already-accepted RB-14 Part 2 precedent of reading `odoo/odoo` source
   directly for `ir.cron`/`ir.model.data` facts when Odoo's documentation
   pages describe only reporting-level concepts, not ORM field names;
   each citation names the exact file path, branch (`19.0`), and access
   date.
2. **Risk (confirmed and fixed — Fable finding C1):** an earlier draft
   of the quantity-source finding (MBQ-32) over-claimed that
   `product.product.free_qty` and `stock.quant.available_quantity` were
   equivalent ("or, equivalently at the per-location level..."). Fable
   flagged this — they are not equivalent; `free_qty` additionally nets
   out `expired_unreserved_qty` and applies UoM rounding, so the two
   diverge whenever expired unreserved stock exists. **Mitigation
   (applied):** Part C §A.4, the §G table, the register, and point A
   above were all corrected to state the exact relationship, quote the
   formulas exactly (including the UoM-rounding wrapper), and state
   explicitly that the source choice is substantive, not cosmetic; MBQ-32
   remains "proposed partially resolved," not fully resolved, and this
   record does not choose a final implementation source.
3. **Risk:** the `stock_delivery` module-dependency finding (MBQ-60)
   could be silently absorbed into the fulfillment blueprint as an assumed
   dependency without surfacing it as a genuinely new question.
   **Mitigation:** explicitly named as "new, surfaced by this sprint,"
   not previously considered by DEC-008/DEC-011, and routed to the
   register rather than asserted as settled.
4. **Risk:** the newly confirmed `FULFILLMENT_ORDERS_*` lifecycle webhook
   family (holds, cancellation requests, merges, splits, reschedules)
   could be silently ignored now that it is known to exist, leaving a
   real gap (e.g. a hold silently blocking a `fulfillmentCreate` call)
   undocumented. **Mitigation:** explicitly named as MBQ-61, a new, open
   question — not decided, not ignored, not silently deferred without a
   register entry.
5. **Risk:** proposing recommendations for MBQ-33/34/41 could be mistaken
   for already-decided outcomes. **Mitigation:** each is labelled
   `[Recommendation]` throughout Part C, names ChatGPT as the decision
   owner, and this record's own "Explicit acceptance points" repeat that
   framing.
6. **Risk:** the location-confirmation mechanism proposed for MBQ-42
   could be read as reintroducing a location-mapping dependency between
   `fulfillment` and `inventory`. **Mitigation:** the proposed mechanism
   explicitly uses only the core Shopify Location reference and/or a live
   Shopify read — never `inventory`'s Odoo-location mapping table — and
   Part C §C.1 restates and checks the never-depends-on-inventory rule
   explicitly against DEC-008/DEC-010/DEC-011.
7. **Risk (confirmed and fixed — Fable finding C2):** an earlier draft
   silently listed "event-driven enqueue" in §A.7/§A.13/§B.12/§C item 7
   as if it were a value in Part A §D.2's fixed job-source enum, which
   Fable flagged as an unauthorized, silent vocabulary extension — DEC-010
   accepted the Odoo-side event trigger only as a sync-trigger layer, and
   fulfillment creation's own trigger (a `stock.picking` Validate action)
   had no stated Part A source classification at all. **Mitigation
   (applied):** all four sections now explicitly distinguish the
   sync-trigger layer from the Part A job-source value recorded on the
   job; no job-source vocabulary extension is asserted; the classification
   question is routed to new, open **MBQ-62**, not silently resolved.
8. **Risk (confirmed and fixed — Fable minor finding 2):** §B.8's
   proposed location-mismatch mechanism reused the accepted `ambiguous
   match` class for a fulfillment-location mismatch without stating that
   this **widens** the class's accepted meaning (AR-006/DEC-009:
   multiple plausible matching candidates) to a different, deterministic
   scenario (one determined answer disagreeing with expectation).
   **Mitigation (applied):** §B.8 and point J above now state the
   accepted definition explicitly, name the widening as a widening (on
   operator-outcome-parity grounds), and make clear ChatGPT would be
   accepting that widening specifically by accepting this record — not
   that it is already an accepted reading.
9. **Risk:** MBQ-37/MBQ-39's "Blocks implementation" register cells read
   as overly optimistic ("No... resolved") before this record is
   accepted, and MBQ-37's payload-shape/subscription-mechanics residual
   (beyond the topic string) was not separately captured. **Mitigation
   (applied):** both cells restored to conservative, Yes-leading wording
   pending DEC-015 acceptance; the broader MBQ-37 residual routed to new,
   open **MBQ-63**.

## No implementation authorized

**This record does not authorize implementation.** Acceptance, if
granted, would be a documentation-level blueprint acceptance only. No
code, Odoo module, model, view, controller, security file, manifest,
test, or CI change is created or permitted by this record, and none may
be created until ChatGPT separately opens the implementation gate per the
Phase 1 research-phase-exit criteria
(`../05-qa/quality-feedback-loop.md` §10) and `CLAUDE.md` §5 — **and, for
any operator-facing screen/view/UI flow, the accepted Part D — UI/UX
Screen Design Blueprint** (see
`../03-architecture/master-blueprint.md` "Criteria for when
implementation may later be opened"). **Acceptance of this record alone,
if granted, would not open that gate.**

## Next sprint recommendation

**Master Blueprint Part D — UI/UX Screen Design Blueprint** (Sprint D),
resolving MBQ-53, or **Part E — implementation-planning bridge**
(Sprint E), per ChatGPT's preference. **Neither is started by this
sprint.**

## Review / change control

- **This record proposes Master Blueprint Part C only.** No accepted
  decision is re-litigated; no rejected approach is reintroduced; checked
  against `rejected-approaches-log.md` before drafting.
- **Related:** AR-012 (`../05-qa/architecture-review-log.md`, Proposed
  for ChatGPT review); the companion Part C blueprint document above;
  DEC-003 through DEC-014 (accepted context, unmodified).
- **Changes** to this record, and its acceptance or rejection, require
  ChatGPT review, mirroring the DEC-004 through DEC-014 change-control
  pattern.
