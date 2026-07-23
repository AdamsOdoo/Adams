# Shopify Fulfillment Status Model — Complete Odoo-Facing Mapping

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** Not accepted;
> acceptance authority: product owner + Claude control room; feeds the revised
> Task 014 packet (Wave 4). No implementation authorized. Purpose: the Odoo
> **User must understand the complete delivery/fulfillment condition of an
> order without opening Shopify.** Every enum value below is a [Fact] taken
> verbatim from
> [`../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)
> §6 (all seven Shopify fulfillment enum families — Layer A — re-verified
> value-for-value against API 2026-07 on 2026-07-16, including A7
> `FulfillmentDisplayStatus`); no values are invented. Labels/badges/behaviors are
> [Proposed product decision] unless marked otherwise. Companion:
> [`fulfillment-operating-modes.md`](fulfillment-operating-modes.md)
> (Modes 1/2, review-case and reconciliation semantics referenced throughout).

> **⚠ Superseded-vocabulary note (Wave 5 U1 Gate A, 2026-07-23 — non-destructive;
> this document remains `Proposed`, status unchanged).** The **Layer C
> (connector-derived)** vocabulary in §1 is **superseded by the shipped Wave 4
> `shopify_connector_fulfillment` code** (verified at exact head
> `2d9cff02dd5459f4ec7afee33c84fec5d00b0b8a`). The **Layer A** Shopify enums below
> are unaffected (they are verbatim Shopify values). U1 binds to the **code** Layer-C
> values; do not copy the superseded strings into any view/selection/test. The
> section text below is **left unchanged** pending a separate product-doc
> reconciliation (logged as **TD-003**; full reconciliation in
> [`../07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md`](../07-implementation-plan/wave-5-u1-gate-a/u1-backend-ui-contract-inventory.md)
> §10). **Pending edits** (anchored by section + context):
>
> | Section · anchor | Superseded value | Code-authoritative replacement |
> |---|---|---|
> | §1 "Layer C — connector-derived states", reconciliation-state enumeration | `under_review` / `auto_matched` / `rejected` | `review`; `auto_matched` and `rejected` are **absent** (not stored states); full set: `observed`/`review`/`acknowledged`/`applied`/`superseded` |
> | §1 "Layer C — connector-derived states", origin-classes enumeration | `external_service` / `carrier_event_only` | `external_app` / (removed origin — carrier milestones via `delivered_inconsistency` / status fields); full set: `connector`/`external_merchant`/`external_app`/`external_unknown` |
>
> **Not superseded — leave untouched (false positives):** the word "rejected" in the
> **Layer A** Shopify tables (`REQUEST_DECLINED` "a fulfillment service rejected some
> items"; `REJECTED` / `fo_req_rejected`; `CANCELLATION_REJECTED`) is a **Shopify**
> enum/prose value, **not** the Layer C reconciliation state.

---

## 1. Authoritative fulfillment-state taxonomy (four layers)

[Proposed product decision] The connector organizes fulfillment state into one
authoritative taxonomy of **four layers**. Each layer answers a different
question and carries its own badge — layers are never merged into a single
"status". This supersedes earlier loose wording ("four families" / "six
concepts"); use the layer names below everywhere.

**Layer A — Shopify enum families (7).** The official GraphQL enums, re-verified
value-for-value against Shopify Admin API **2026-07** on 2026-07-16 (all seven,
including A7 `FulfillmentDisplayStatus`). Stored raw, normalized for
display/logic, unknown values handled per §7.

| # | GraphQL enum | Active | Deprecated | Role | Detail |
|---|---|---|---|---|---|
| A1 | `OrderDisplayFulfillmentStatus` | 7 | 3 (`OPEN`, `PENDING_FULFILLMENT`, `RESTOCKED`) | order-level roll-up (display) | §2 |
| A2 | `FulfillmentOrderStatus` | 7 | 0 | FO work state (automation input, D-014-4) | §3.1 |
| A3 | `FulfillmentOrderRequestStatus` | 8 | 0 | fulfillment-service signal (display + gating) | §3.2 |
| A4 | `FulfillmentStatus` | 4 | 2 (`OPEN`, `PENDING`) | Fulfillment result (Mode 2 cond. 2 gate) | §4 |
| A5 | `FulfillmentEventStatus` | 11 | 0 | carrier milestone (display only) | §5 |
| A6 | `FulfillmentHoldReason` | 8 | 0 | hold detail (display only) | §3.3 |
| A7 | `FulfillmentDisplayStatus` | 18 | 0 | `Fulfillment.displayStatus` roll-up — **display only, never an automation input** | §4.1 |

**Layer B — Shopify non-enum status surfaces.** `trackingInfo`
(`company`/`number`/`url`); timestamps `inTransitAt` / `deliveredAt` /
`estimatedDeliveryAt` / `fulfillAt`; `FulfillmentHold.displayReason` /
`reasonNotes`; `assignedLocation`; remote `updatedAt`; booleans/flags.
Evidence/display; never standalone enum families.

**Layer C — connector-derived states.** Reconciliation state (`observed`,
`under_review`, `auto_matched`, `applied`, `acknowledged`, `rejected`,
`superseded`), origin classes (`connector`, `external_merchant`,
`external_service`, `carrier_event_only`), and the Delivered-inconsistency case
(§8). Connector states — **not** Shopify enums (evidence records, File A §5).

**Layer D — user-facing summary labels.** Not started, Ready to fulfill, In
progress, Partially shipped, Fulfilled, In transit, Delivered, On hold,
Scheduled, Exception, Failed, Cancelled, Manual review, Unknown. UX summaries —
**not** API values; the per-value tables in §2–§5 bind each raw Layer-A value to
its Layer-D label/badge.

**Odoo-side (not a Shopify layer) — Odoo delivery state:** `stock.picking.state`
(`draft`/`waiting`/`confirmed`/`assigned`/`done`/`cancel`; Odoo capture §2) —
what the warehouse has actually done, and the authority for real stock movement.

[Fact] Shopify itself directs detailed processing state away from the
order-level summary (A1) and to FulfillmentOrder (A2, capture §6.1). [Proposed
product decision] Layer A5 (carrier milestones) is informational only: **a
carrier milestone never changes the Odoo delivery state or a Layer-C
reconciliation state by itself** (§8).

**Column key for §2–§5 tables:** *Raw* = stored raw Shopify value (always
persisted verbatim). *Label* = simplified Odoo-facing label. *Badge/Icon* =
design-system badge token + icon (vocabulary §9). *Sev* = visual severity
(§9). *User may / blocked* = permitted vs blocked actions. *Outbound* =
connector Odoo→Shopify behavior. *Inbound* = reconciliation behavior (File A
§3–§5). *Retry* = connector retry behavior. *Review* = manual-review
behavior. *Odoo relation* = expected `stock.picking` correspondence.
*Fixture* = test fixture name (§10). Unknown future values in every family
follow §7 — never per-row improvisation.

---

## 2. Order-level summary — `OrderDisplayFulfillmentStatus` (7 active)

[Fact] Values and definitions: capture §6.1. Roll-up only — drives the order
list badge, never any stock action.

| Raw | Label | Badge/Icon | Sev | Description (for User) | User may | Blocked | Outbound | Inbound | Retry | Review | Odoo relation | Fixture |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `UNFULFILLED` | Not shipped | `badge-neutral` / `truck-outline` | calm | Nothing shipped yet. | validate Odoo pickings normally | — | fulfillment allowed when picking validates | expect no fulfillments; any found → re-scan | normal | none | picking `confirmed`/`assigned` open | `order_sum_unfulfilled` |
| `PARTIALLY_FULFILLED` | Partially shipped | `badge-info` / `truck-half` | info | Some items shipped. | validate remaining pickings; open review cases | — | remaining-quantity fulfillments allowed | reconcile per-line ledger vs done pickings | normal | only if ledger disagrees with Odoo done qty | some pickings `done`, backorder open | `order_sum_partial` |
| `FULFILLED` | Fully shipped | `badge-success` / `truck-check` | calm | Everything shipped. | acknowledge residual cases | further fulfillment sends (nothing remains) | no further creates; tracking updates still allowed | all lines should be reconciled; gaps → review | n/a | gap between Shopify=fulfilled and Odoo pickings not done → inconsistency case (§8 pattern) | all customer legs `done` | `order_sum_fulfilled` |
| `IN_PROGRESS` | Fulfillment in progress | `badge-info` / `progress-clock` | info | All items requested from a fulfillment service or marked in progress. | wait; inspect FO detail | Mode 2 auto-apply (no result yet) | creates typically originate elsewhere; connector sends still valid vs FO remaining | watch for resulting Fulfillments | normal | no | picking open (`assigned`) | `order_sum_in_progress` |
| `ON_HOLD` | On hold | `badge-warning` / `pause-circle` | warning | All unfulfilled items are on hold. | see hold reasons (§3.3); resolve in Shopify | connector fulfillment send (D-014-5: hold → review) | picking validation → `blocked_manual_review`/`ambiguous_match` | no auto-apply | held until state changes | yes — hold reason surfaced | picking open, do-not-ship flag surfaced | `order_sum_on_hold` |
| `SCHEDULED` | Scheduled for later | `badge-neutral` / `calendar-clock` | info | Unfulfilled items scheduled for a later `fulfillAt`. | view schedule | connector send (D-014-5 treats SCHEDULED as not-ready) | validation before `fulfillAt` → review | no auto-apply | until FO opens | yes if Odoo already shipped | picking open | `order_sum_scheduled` |
| `REQUEST_DECLINED` | Service declined | `badge-danger` / `alert-octagon` | critical | A fulfillment service rejected some items. | investigate in Shopify; reassign | Mode 2 auto-apply | sends blocked pending FO state review | no auto-apply | no auto-retry | always | picking open; operator decision needed | `order_sum_request_declined` |

Unknown future value → §7. Deprecated `OPEN`, `PENDING_FULFILLMENT`,
`RESTOCKED` → §6.

---

## 3. FulfillmentOrder family

### 3.1 `FulfillmentOrder.status` (7 active, none deprecated — capture §6.2)

This is the **work state** the connector's FO selection logic keys on
(D-014-4 selects `OPEN`+`IN_PROGRESS` client-side).

| Raw | Label | Badge/Icon | Sev | Description | User may | Blocked | Outbound | Inbound | Retry | Review | Odoo relation | Fixture |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `OPEN` | Ready to fulfill | `badge-success` / `play-circle` | calm | Ready for fulfillment at its location. | validate picking | — | eligible target for `fulfillmentCreate` | baseline | normal | no | picking `assigned` expected | `fo_open` |
| `IN_PROGRESS` | Being fulfilled | `badge-info` / `progress-clock` | info | Partially fulfilled / in work (state of a backorder chain mid-way). | validate remaining | — | eligible target (D-014-4) | per-line remaining reconciled | normal | no | partial `done` + open backorder | `fo_in_progress` |
| `SCHEDULED` | Deferred | `badge-neutral` / `calendar-clock` | info | Deferred until `fulfillAt`. | view date | connector send | send attempt → review (D-014-5) | no auto-apply | until OPEN | yes if Odoo shipped early | picking open | `fo_scheduled` |
| `ON_HOLD` | Held | `badge-warning` / `pause-circle` | warning | Held; see hold reasons §3.3. Multiple apps can hold one FO [Fact]. | view reasons; resolve in Shopify | connector send; connector never places/releases holds (D-014-5) | send attempt → review | no auto-apply | until released | yes, with `displayReason` | picking open, warn on validate | `fo_on_hold` |
| `INCOMPLETE` | Incomplete | `badge-danger` / `alert-triangle` | critical | "Cannot be completed as requested" [quote]. | investigate | connector send; Mode 2 apply | → review | no auto-apply | no | always | operator decision | `fo_incomplete` |
| `CLOSED` | Completed | `badge-neutral` / `check-circle-outline` | calm | All work done. | — | further sends against it | excluded from FO selection | fulfillments already reconciled | n/a | only on ledger mismatch | picking `done` | `fo_closed` |
| `CANCELLED` | Cancelled | `badge-neutral` / `cancel` | warning | FO cancelled. | check order/cancel context | sends; Mode 2 apply | excluded; pending picking → review | no apply | no | yes if Odoo picking still open | picking should be cancelled or reviewed | `fo_cancelled` |

### 3.2 `FulfillmentOrder.requestStatus` (8 active, none deprecated — capture §6.2)

Relevant only when a fulfillment service is involved; the connector displays
it and treats non-`UNSUBMITTED` transitions as external-service signals.

| Raw | Label | Badge/Icon | Sev | Description | User may / Blocked | Outbound / Inbound / Retry / Review | Odoo relation | Fixture |
|---|---|---|---|---|---|---|---|---|
| `UNSUBMITTED` | No service request | `badge-neutral` / `minus-circle` | calm | Merchant-managed default; no request sent. | normal ops / — | normal outbound; baseline inbound; normal retry; no review | any open state | `fo_req_unsubmitted` |
| `SUBMITTED` | Requested from service | `badge-info` / `send-clock` | info | Request sent to fulfillment service. | wait / connector send (service owns work; also blocks `fulfillmentOrderMove` [Fact §6.2]) | outbound blocked → review if picking validates; inbound: watch; no auto-retry; review on conflict | picking open | `fo_req_submitted` |
| `ACCEPTED` | Service accepted | `badge-info` / `check-decagram-outline` | info | Service accepted the request. | wait / connector send | as `SUBMITTED` | picking open | `fo_req_accepted` |
| `REJECTED` | Service rejected | `badge-danger` / `alert-octagon` | critical | Service rejected the request. | reassign in Shopify / Mode 2 apply | outbound held; inbound none; no retry; **always review** | operator decision | `fo_req_rejected` |
| `CANCELLATION_REQUESTED` | Cancel requested | `badge-warning` / `undo-variant` | warning | Merchant asked service to cancel. | wait / sends | hold everything; review if Odoo mid-flight | picking open | `fo_req_cancellation_requested` |
| `CANCELLATION_ACCEPTED` | Cancel accepted | `badge-neutral` / `undo` | info | Service accepted cancellation. | re-plan / — | FO returns to merchant control; re-evaluate normally | picking open | `fo_req_cancellation_accepted` |
| `CANCELLATION_REJECTED` | Cancel rejected | `badge-warning` / `undo-close` | warning | Service refused to cancel; work continues. | wait / connector send | as `SUBMITTED`; review on conflict | picking open | `fo_req_cancellation_rejected` |
| `CLOSED` | Request closed | `badge-neutral` / `check-circle-outline` | calm | Request lifecycle finished. | — / new sends via new FO state | follow `FulfillmentOrder.status` | per FO status | `fo_req_closed` |

### 3.3 Hold reasons — `FulfillmentHoldReason` (8 — capture §6.2)

Displayed verbatim-with-label inside any `ON_HOLD` case; connector is
read-only toward holds (D-014-5). All: severity **warning** (except
`HIGH_RISK_OF_FRAUD`: **critical**), badge `badge-warning` / icon
`pause-circle`, no outbound sends, no Mode 2 apply, review when Odoo has
shipped or wants to ship.

| Raw | Label |
|---|---|
| `AWAITING_PAYMENT` | Awaiting payment |
| `AWAITING_RETURN_ITEMS` | Awaiting returned items |
| `HIGH_RISK_OF_FRAUD` | High fraud risk (critical) |
| `INCORRECT_ADDRESS` | Address problem |
| `INVENTORY_OUT_OF_STOCK` | Out of stock at location |
| `ONLINE_STORE_POST_PURCHASE_CROSS_SELL` | Post-purchase offer window |
| `UNKNOWN_DELIVERY_DATE` | Unknown delivery date |
| `OTHER` | Other (see `reasonNotes`/`displayReason`) |

Fixtures: `fo_hold_<reason_lowercase>` (8). Unknown future reason → §7.

---

## 4. Fulfillment result — `FulfillmentStatus` (4 active — capture §6.3)

The **result record** of a concrete shipment. This is the family Mode 2
condition 2 gates on.

| Raw | Label | Badge/Icon | Sev | Description | User may | Blocked | Outbound | Inbound | Retry | Review | Odoo relation | Fixture |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `SUCCESS` | Shipped (confirmed) | `badge-success` / `check-circle` | calm | Fulfillment recorded successfully. | import tracking; acknowledge; validate exact proposal (Mode 1) | — | this is the expected result of our `fulfillmentCreate` | the only status eligible for Mode 2 auto-apply (File A §4 cond. 2) | n/a | external origin → Mode 1 review case | picking `done` (ours) or proposal to validate (external) | `ful_success` |
| `CANCELLED` | Cancelled | `badge-warning` / `cancel` | warning | Fulfillment cancelled; Shopify reopens FOs for the items [Fact §6.5]. | decide: re-ship / return flow | any automatic Odoo stock reversal (returns are manual — File A §5 edge table) | connector never cancels fulfillments in MVP | supersede evidence record; if Odoo `done` → **high-visibility review** (D-014-8: nothing auto-changes in Odoo) | no | always when Odoo validated | picking possibly `done` — mismatch case | `ful_cancelled` |
| `ERROR` | Error | `badge-danger` / `alert-circle` | critical | "Error with the fulfillment request" [quote]. | inspect; retry from case | Mode 2 apply | if ours: route DEC-009 taxonomy; verification read before any retry (D-014-7) | never reconciled as shipped | taxonomy-gated retry | yes | picking `done`, Shopify not — inconsistency | `ful_error` |
| `FAILURE` | Failed | `badge-danger` / `close-octagon` | critical | "The fulfillment request failed" [quote]. | as `ERROR` | Mode 2 apply | as `ERROR` | never reconciled as shipped | taxonomy-gated | yes | as `ERROR` | `ful_failure` |

Deprecated `OPEN`, `PENDING` → §6. Unknown future value → §7.

### 4.1 `Fulfillment.displayStatus` — `FulfillmentDisplayStatus` (A7; 18 active — verified 2026-07-16)

[Fact — verified against Shopify Admin API 2026-07 on 2026-07-16] The
`Fulfillment.displayStatus` field exposes a **display roll-up** enum with 18
values: `ATTEMPTED_DELIVERY`, `CANCELED` (one "L" — distinct from A4
`CANCELLED`), `CARRIER_PICKED_UP`, `CONFIRMED`, `DELAYED`, `DELIVERED`,
`FAILURE`, `FULFILLED`, `IN_TRANSIT`, `LABEL_PRINTED`, `LABEL_PURCHASED`,
`LABEL_VOIDED`, `MARKED_AS_FULFILLED`, `NOT_DELIVERED`, `OUT_FOR_DELIVERY`,
`PICKED_UP`, `READY_FOR_PICKUP`, `SUBMITTED`; **no deprecated values**. This
resolves the former open question about A7.

[Proposed product decision] A7 is **display only and is never an automation
input.** It combines fulfillment result (A4) and carrier-milestone (A5) signals
into a single merchant-facing label, so the connector may surface it as
supplementary display text on a fulfillment, but **all automation and
reconciliation logic keys on the authoritative families** — A4 `FulfillmentStatus`
(Mode 2 condition 2), A2 `FulfillmentOrderStatus` (FO selection), and the File A
§4 checklist — never on A7. A7 values not in this list follow the §7
unknown-value contract. No A7 value ever validates Odoo stock (§8).

---

## 5. Carrier milestones — `FulfillmentEventStatus` (11 active — capture §6.4) + tracking info

[Fact] Tracking display data: `trackingInfo` (`company`, `number`, `url`) and
timestamps `inTransitAt` / `deliveredAt` / `estimatedDeliveryAt` on the
Fulfillment (capture §6.3). [Proposed product decision] **Every** milestone is
Layer A5 (carrier-milestone) display only: outbound = none; inbound = update milestone timeline
on the evidence record; retry = n/a; **no milestone ever changes Odoo stock
or connector reconciliation state** (§8). Per-value specifics:

| Raw | Label | Badge/Icon | Sev | Description | Review behavior | Odoo relation | Fixture |
|---|---|---|---|---|---|---|---|
| `LABEL_PURCHASED` | Label purchased | `badge-neutral` / `barcode` | calm | Shipping label bought. | none | picking `done` or `assigned` | `evt_label_purchased` |
| `LABEL_PRINTED` | Label printed | `badge-neutral` / `printer` | calm | Label printed. | none | as above | `evt_label_printed` |
| `READY_FOR_PICKUP` | Ready for pickup | `badge-info` / `package-variant` | info | Parcel awaiting carrier/customer pickup. | none | picking `done` | `evt_ready_for_pickup` |
| `CONFIRMED` | Confirmed | `badge-neutral` / `check` | calm | "Default value when no other information is available" [quote]. | none | picking `done` | `evt_confirmed` |
| `CARRIER_PICKED_UP` | Carrier picked up | `badge-info` / `truck` | info | Carrier has the parcel. | none | picking `done` | `evt_carrier_picked_up` |
| `IN_TRANSIT` | In transit | `badge-info` / `truck-fast` | info | Moving through the carrier network. | none | picking `done` | `evt_in_transit` |
| `OUT_FOR_DELIVERY` | Out for delivery | `badge-info` / `truck-delivery` | info | On the last leg. | none | picking `done` | `evt_out_for_delivery` |
| `ATTEMPTED_DELIVERY` | Delivery attempted | `badge-warning` / `truck-alert` | warning | Attempt failed; carrier will retry/return. | optional operator attention flag | picking `done` | `evt_attempted_delivery` |
| `DELIVERED` | Delivered | `badge-success` / `package-check` | calm | Carrier reports delivered. **Never validates Odoo stock (§8).** | §8 inconsistency rule when picking not `done` | picking `done` expected | `evt_delivered` |
| `DELAYED` | Delayed | `badge-warning` / `clock-alert` | warning | Shipment delayed. | optional attention flag | picking `done` | `evt_delayed` |
| `FAILURE` | Delivery failed | `badge-danger` / `close-octagon` | critical | Carrier-level failure. | review case: decide return/re-ship (return flow is manual — Odoo capture §2) | picking `done`; possible return | `evt_failure` |

Unknown future value → §7 (timeline shows raw value, "unknown milestone").

---

## 6. Deprecated values (stored-as-raw + normalized)

[Proposed product decision] Deprecated values are **stored verbatim** (raw
evidence) and **normalized for display and logic** to their documented
replacement; the badge shows the normalized label with a "legacy value"
tooltip carrying the raw string. They can still appear on old data.

| Family | Deprecated raw | Normalized to | Basis [Fact] |
|---|---|---|---|
| OrderDisplayFulfillmentStatus | `OPEN` | `UNFULFILLED` | capture §6.1 |
| OrderDisplayFulfillmentStatus | `PENDING_FULFILLMENT` | `IN_PROGRESS` | capture §6.1 |
| OrderDisplayFulfillmentStatus | `RESTOCKED` | `UNFULFILLED` | capture §6.1 |
| FulfillmentStatus | `OPEN` | treated as non-final: display "Legacy: open", behave as unknown-not-success (§7 automation stop) | capture §6.3 (legacy pre-FulfillmentOrder value; no documented replacement) |
| FulfillmentStatus | `PENDING` | as `OPEN` above ("Legacy: pending") | capture §6.3 |

Fixtures: `dep_order_sum_open`, `dep_order_sum_pending_fulfillment`,
`dep_order_sum_restocked`, `dep_ful_open`, `dep_ful_pending`.

[Fact] `FulfillmentOrderStatus`, `FulfillmentOrderRequestStatus`,
`FulfillmentEventStatus`, and `FulfillmentHoldReason` list **no deprecated
values** on the 2026-07-16 pages.

---

## 7. Unknown-future-value contract

[Proposed product decision] Shopify adds enum values across quarterly API
versions, and unsupported-version fall-forward can silently change behavior
[Fact — capture §11]. For **any** value in **any** of these families not in
this document's tables:

1. **Preserve as raw evidence** — stored verbatim on the evidence record; never
   coerced to a known value.
2. **Display as unsupported/unknown** — label "Unknown status (RAW_VALUE)",
   badge `badge-unknown`, icon `help-circle`, severity **warning**.
3. **Never silently success** — an unknown value is never interpreted as
   completed/succeeded/delivered.
4. **Stop unsafe automation** — Mode 2 auto-apply, outbound sends against the
   affected FO, and any retry path that depends on the unknown field halt for
   that record; Mode 1 review-only behavior continues.
5. **Raise an actionable schema warning** — a connector health warning naming
   family, raw value, store, API version, and affected records, so the mapping
   table (this file) gets extended deliberately.

Fixture per family: `unknown_order_sum`, `unknown_fo_status`,
`unknown_fo_request_status`, `unknown_ful_status`, `unknown_evt_status`,
`unknown_hold_reason`.

---

## 8. The Delivered-inconsistency rule

[Proposed product decision — binding direction restated]

1. **A carrier `DELIVERED` milestone (or `Fulfillment.deliveredAt`) NEVER
   independently validates Odoo stock.** Layer A5 (carrier milestones) cannot write the Odoo delivery state.
   Rationale: carrier milestones are third-party display data with no line,
   lot, or location evidence — none of File A §4's conditions are satisfiable
   from a milestone.
2. **Defined inconsistency case:** Shopify (or the carrier) reports Delivered
   — `FulfillmentEventStatus = DELIVERED` or `deliveredAt` set — while the
   corresponding Odoo picking is **not** `done`. The connector raises a
   **high-visibility User review case**: severity **critical**, badge
   `badge-danger` / icon `alert-decagram`, label "Delivered per carrier —
   Odoo delivery not validated", pinned to the store dashboard and the order,
   listing the fulfillment, tracking, milestone timestamp, and the exact open
   picking(s). Resolution paths: User validates the proposal (Mode 1 explicit
   validation, File A §2.2), corrects the order linkage, or acknowledges with
   a reason. The case never auto-resolves by stock mutation; in Mode 2 it may
   auto-resolve **only** if the underlying external fulfillment independently
   passes the full §4 checklist of File A (the milestone itself contributes
   nothing to that evaluation).

---

## 9. Badge / severity vocabulary

[Recommendation] Consistent with the premium design-system tokens
([`../03-architecture/premium-ui-ux-design-system.md`](../03-architecture/premium-ui-ux-design-system.md),
[`ui-ux-final-design-spec.md`](ui-ux-final-design-spec.md)); token names
final-bound there, semantics bound here:

| Severity | Meaning | Badge token | Typical icons |
|---|---|---|---|
| **calm** | Normal, no attention needed | `badge-neutral` / `badge-success` | check-circle, truck-check |
| **info** | Activity in progress, informational | `badge-info` | progress-clock, truck-fast |
| **warning** | Needs awareness; automation paused | `badge-warning` | pause-circle, clock-alert |
| **critical** | Needs action; pinned visibility | `badge-danger` | alert-octagon, alert-decagram |
| *(unknown)* | Unrecognized value (§7) | `badge-unknown` | help-circle |

Rules: one badge per layer/family (§1); severities never downgrade by roll-up (an
order row shows the max severity across its layers); color is never the
only signal (icon + label always present — accessibility rule of the design
system).

---

## 10. Test-fixture inventory

One fixture per active value, per deprecated value, and per unknown-value
family, named in §2–§7: `order_sum_*` (7), `fo_*` (7), `fo_req_*` (8),
`fo_hold_*` (8), `ful_*` (4), `evt_*` (11), `dep_*` (5), `unknown_*` (6) —
**56 fixtures**. Each fixture asserts: raw persisted verbatim; label, badge,
severity per its table row; permitted/blocked actions enforced;
outbound/inbound/retry/review behavior; expected Odoo relation; and (for
`unknown_*`) all five §7 contract points. Cross-file fixtures for File A
scenarios (Mode 2 checklist, mode switching, Delivered-inconsistency) live in
`../05-qa/fulfillment-mode-uat-matrix.md` (companion deliverable).

## 11. Proposed decisions and open questions

**Proposed decisions.** 1. Four-layer taxonomy — Layer A (seven Shopify enum
families), Layer B (non-enum surfaces), Layer C (connector-derived states),
Layer D (user-facing labels) — one badge per layer (§1).
2. Per-value mapping tables §2–§5 (+ §4.1 A7) as the complete Odoo-facing vocabulary.
3. Deprecated values stored-raw + normalized (§6). 4. Unknown-value contract
(§7). 5. Carrier Delivered never validates stock + the defined
high-visibility inconsistency case (§8). 6. Severity/badge vocabulary (§9).

**Open questions.**
1. [Resolved 2026-07-16] `Fulfillment.displayStatus`
   (`FulfillmentDisplayStatus`, A7) was re-verified against API 2026-07 on
   2026-07-16 — 18 values, no deprecations (§4.1) — and mapped as display-only,
   never an automation input. No open item remains for this enum.
2. [Open question] Per-topic fulfillment webhook payload schemas (capture
   §13.7) — which fields of these families arrive in each payload vs require
   a follow-up read.
3. [Open question] Whether fulfillment webhooks expose the originating API
   client (capture §13.6) — affects File A §3 only, listed here for the
   evidence-record schema.
4. [Open question] Exact icon-set names must be reconciled with the design
   system's icon library at UI implementation time; icons above are semantic
   placeholders.
