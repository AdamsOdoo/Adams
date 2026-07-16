# COD Lifecycle and Reconciliation — Product Definition

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** This document
> defines the Cash-on-Delivery (COD) lifecycle, reconciliation, and value-ledger
> product design for the Odoo 19 ↔ Shopify connector. Acceptance authority:
> product owner + Claude control room. **No implementation authorized** by this
> document; it feeds the wave packets listed in §9.

Evidence base (Tier-1 captures, both accessed 2026-07-16):

- Shopify: [`../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md`](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md) (§1 financial states, §2 transactions/`manualPaymentGateway`/`orderMarkAsPaid`, §8 `Refund.transactions`).
- Odoo 19: [`../00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md`](../00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md) (§1 SO lifecycle/cancellation, §2 pickings/backorders/returns/`to_refund`, §4 payments/AR boundary).
- Binding rejection: **RA-010** — automatic full accounting/payment reconciliation as default behaviour is a rejected approach ([`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md), bound by [`../04-decisions/DEC-007-phase1-scope-clarifications.md`](../04-decisions/DEC-007-phase1-scope-clarifications.md)). Nothing below re-proposes it.
- Mutation gating: [`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md) (Layer 2 replay-safety controls for outbound mutations).

---

## 1. Why COD needs its own model

[Fact] Shopify represents a COD order's payment as `displayFinancialStatus: PENDING` — "when manual payment methods are being used" — and the money-movement truth lives in `OrderTransaction` records where `manualPaymentGateway: true` identifies the manual/COD gateway (capture §1–2). [Fact] Odoo 19's `sale.order` has **no payment_state of its own**; invoice `payment_state` exists only once an invoice exists, and `account.payment.register` immediately posts and reconciles journal entries (Odoo capture §4). [Inference] Neither system natively answers the operational COD questions — *was the cash collected at the door, how much, by whom, and does it match what was delivered?* — without either premature accounting postings (rejected by RA-010) or connector-owned records.

**[Proposed product decision PD-COD-1 — three independent state dimensions.]**
A COD order is always described by **three independent state dimensions**, never
collapsed into one status field:

1. **Commercial state** — the Shopify order + Odoo sales order lifecycle.
2. **Fulfillment state** — the physical movement of goods (Odoo pickings + Shopify fulfillment evidence).
3. **Payment/collection state** — cash actually collected, from the configured evidence source.

Every screen, API surface, log line, and test that reports COD status must
report all three dimensions (or an explicit subset with the others reachable),
because real COD scenarios occupy combinations a single status cannot express
(e.g. *fully delivered + nothing collected* = a discrepancy case, not "done";
*cancelled remainder + partially collected* = a legitimate closed state).

**[Proposed product decision PD-COD-2 — stock-restoration rule.]**
Stock is **never** restored because a courier, a Shopify webhook, or any
external party *reports* refusal or return-to-origin. Stock re-enters
inventory **only** when the warehouse physically receives the goods and a user
validates the return through the accepted Odoo return-picking workflow.
[Fact] This matches Odoo's own design: `stock.return.picking` creates a
reversed-location picking and quantities re-enter stock only when that return
picking is validated; `to_refund` on the return move is what decreases the
SO delivered quantity (Odoo capture §2). Any design that auto-restores stock
on a courier claim would corrupt on-hand accuracy and is out of scope.

---

## 2. The three-dimension state model

The states below are **connector-design states**: a read model layered over
Odoo and Shopify facts, not new writable fields on core Odoo models. Each
state names its evidence source. [Inference] labels apply to the derivations;
the underlying enum/field facts are cited to the captures.

### 2.1 Dimension 1 — Commercial state

| State | Meaning | Evidence source |
|---|---|---|
| `imported` | Shopify order ingested; connector binding exists; Odoo record not yet (or just) created. | Connector binding record + Shopify `Order` (webhook `orders/create` or reconciliation scan). |
| `quotation` | Odoo `sale.order` exists in `draft`/`sent` (import policy created it unconfirmed). | [Fact] `sale.order.state` ∈ `draft`, `sent` (Odoo capture §1). |
| `confirmed` | Odoo SO confirmed; procurement/pickings launched. | [Fact] `state = 'sale'` after `action_confirm()`; `sale_stock` launches stock rules (Odoo capture §1). |
| `cancelled-full` | Entire order cancelled commercially. | [Fact] Odoo `state = 'cancel'` (cancels non-done pickings only, preserves done ones); Shopify `cancelledAt`/`cancelReason` non-null (Shopify capture §3). |
| `cancelled-partial-remainder` | Delivered portion stands; the undelivered remainder is commercially cancelled. | Connector state: SO stays `sale`; remainder cancellation evidenced by validated-with-`skip_backorder` picking or cancelled backorder picking ([Fact] Odoo capture §2 backorder wizard semantics) + connector audit event. |

[Open question OQ-COD-1] Whether Odoo 19's `sale.order.cancel` confirmation
wizard fires in the connector's flows is unverified (Odoo capture §1 open
question); the Wave 4 packet must confirm before automating any cancel call.

### 2.2 Dimension 2 — Fulfillment state

| State | Meaning | Evidence source |
|---|---|---|
| `not-dispatched` | No delivery picking validated; goods in warehouse. | [Fact] Picking states `draft`/`waiting`/`confirmed` (Odoo capture §2). |
| `reserved` | Stock reserved for the delivery, not yet shipped. | [Fact] Picking `assigned` ("Ready"); reservation per `stock.picking.type.reservation_method` (Odoo capture §2). |
| `dispatched` | Delivery picking validated; goods left the warehouse with the courier. | [Fact] Delivery picking `done`; per-move `quantity` records shipped quantities (Odoo capture §2). Optional Shopify `Fulfillment` created (read or, when write-back enabled, connector-created). |
| `partially-delivered` | Some order lines/quantities delivered and accepted; remainder not. | [Fact] Validated picking with `quantity < product_uom_qty` on some moves + backorder or cancelled remainder (Odoo capture §2); Shopify `PARTIALLY_FULFILLED` where write-back applies (Shopify capture §6.1). |
| `fully-delivered` | All ordered quantities delivered and accepted. | [Fact] All delivery moves done at full demand; Shopify `FULFILLED` / `FulfillmentEventStatus: DELIVERED` as corroborating evidence (Shopify capture §6). |
| `failed-delivery` | Courier attempted delivery and failed; goods still with courier. | External/courier report; Shopify `FulfillmentEventStatus: ATTEMPTED_DELIVERY` / `FAILURE` (Shopify capture §6.4) or user entry. **No Odoo stock action.** |
| `return-to-origin-in-transit` | Courier reports goods coming back; not yet received. | Courier/user report; connector flag only. **No Odoo stock action** (PD-COD-2). |
| `returned-validated` | Warehouse physically received the goods and validated the Odoo return picking. | [Fact] Validated `stock.return.picking`-generated picking with `origin_returned_move_id` set; `to_refund` controls delivered-qty decrease (Odoo capture §2). This is the only state in which stock is back on hand. |

### 2.3 Dimension 3 — Payment/collection state

| State | Meaning | Evidence source |
|---|---|---|
| `nothing-collected` | No collection evidence recorded. | Absence of connector collection-event records; Shopify `displayFinancialStatus: PENDING` with only pending manual transactions ([Fact] Shopify capture §1–2). |
| `partially-collected` | Collected amount > 0 and < outstanding-eligible amount. | Connector collection-event records (§4) summing below fulfilled value; Shopify `PARTIALLY_PAID` where a partial manual capture exists ([Fact] §1). |
| `fully-collected` | Collected amount equals the amount due for the delivered goods. | Collection events covering the due amount; Shopify `PAID` / successful manual `SALE`/`CAPTURE` transaction, or `orderMarkAsPaid` effect ([Fact] §1–2). |
| `discrepancy` | Collection evidence conflicts with delivery facts or with the authoritative source (e.g. delivered but courier remittance short; non-authoritative evidence diverges). | Connector comparison of value ledger (§4) vs collection events; always produces a review case. |
| `refunded` | Money returned to the customer (full or partial). | [Fact] Shopify `Refund.transactions` against the manual gateway (`manualPaymentGateway: true`); `REFUNDED`/`PARTIALLY_REFUNDED` financial status; a Refund's existence does not guarantee funds moved — transaction statuses are the truth (Shopify capture §8). Odoo-side: connector record only in MVP. |

[Inference] Because `displayFinancialStatus: PENDING` also covers non-COD
gateway-processing delays, the connector classifies an order as COD by
`OrderTransaction.manualPaymentGateway = true` / manual gateway identity, never
by `PENDING` alone (Shopify capture §2).

---

## 3. The lifecycle matrix — 16 mandated scenarios

Conventions for every scenario below:

- **Trajectory** lists the three dimensions as *Commercial / Fulfillment / Collection*.
- **Odoo actions** name only accepted Odoo mechanisms: picking validation, the backorder wizard's ask/always/never semantics, and `stock.return.picking` for physical returns ([Fact] Odoo capture §2). The connector never invents parallel stock mechanics.
- **Shopify effect**: in MVP the connector's only permitted COD-financial mutation is **`orderMarkAsPaid` on full collection, when Administrator policy allows** — gated as a DEC-031 Layer 2 mutation (§6). Refunds are **read-only visibility**. Everything else Shopify-side is evidence, not action.
- **Roles**: *User* = operational connector role (record collections, validate pickings per Odoo rights); *Administrator* = connector admin (policy, discrepancy resolution, remainder cancellation, mark-as-paid policy). The two-role model with Administrator implying User rides on Odoo group implication ([Fact] Odoo capture §5).
- **Audit**: every scenario writes connector audit events (actor, timestamp, before/after states, evidence source, amounts). Listed per scenario only where specific extras apply.

### 3.1 Scenario 1 — Full delivery + full collection (happy path)

- **Trigger:** courier delivers all goods; customer pays full COD amount.
- **Trajectory:** confirmed / not-dispatched → reserved → dispatched → fully-delivered / nothing-collected → fully-collected.
- **Odoo actions:** confirm SO (per import policy); reserve; validate delivery picking at full demand quantities. No backorder arises. No accounting action (§6).
- **Shopify evidence/effect:** `FULFILLED`; optional `DELIVERED` fulfillment event. On full collection and if the Administrator enabled the policy, connector calls `orderMarkAsPaid` → `PAID` ([Fact] mutation "useful for orders created with manual payment methods like cash on delivery" — Shopify capture §2). Otherwise the order legitimately stays `PENDING` in Shopify.
- **Roles:** User validates picking and records the collection event; Administrator sets the mark-as-paid policy.
- **UX:** order leaves the COD queue as *Delivered / Fully collected*; ledger shows outstanding = 0.
- **Audit:** collection event with amount, source, actor; mark-as-paid mutation logged with Layer 2 idempotency evidence.

### 3.2 Scenario 2 — Cancellation before dispatch

- **Trigger:** customer/merchant cancels before any picking is validated.
- **Trajectory:** confirmed → cancelled-full / not-dispatched (stays; no goods moved) / nothing-collected (stays).
- **Odoo actions:** SO `action_cancel` — [Fact] cancels all non-done pickings automatically; nothing is `done`, so all demand is released and reservations lift (Odoo capture §1–2). **No return picking** — goods never left.
- **Shopify evidence:** `cancelledAt` set; financial status remains `PENDING`/becomes `VOIDED`-adjacent only per Shopify's own handling — connector reads, never mutates cancellation finances.
- **Roles:** User may cancel per Odoo rights; connector policy may require Administrator for connector-initiated cancels. No collection to reconcile.
- **UX:** row shows *Cancelled / Not dispatched / Nothing collected*; excluded from the active collection queue, visible in history.
- **Audit:** cancellation origin (Shopify webhook vs Odoo user) recorded.

### 3.3 Scenario 3 — Cancellation after reservation, before departure

- **Trigger:** cancel arrives while picking is `assigned` (reserved) but not validated.
- **Trajectory:** confirmed → cancelled-full / reserved → not-dispatched / nothing-collected.
- **Odoo actions:** identical to 3.2 — [Fact] cancelling the SO cancels non-done pickings; cancelling a reserved picking releases the reservation back to free stock (Odoo capture §1–2). No stock adjustment beyond reservation release; **no return picking**.
- **Shopify/roles/UX/audit:** as 3.2, plus the audit event notes reservation existed and was released (stock never physically moved, so no receipt is expected — this distinguishes it from 3.6).

### 3.4 Scenario 4 — Full rejection at the door

- **Trigger:** courier reaches the customer; customer refuses the entire parcel; no cash collected.
- **Trajectory:** confirmed (→ cancelled-full only after warehouse return + explicit decision) / dispatched → failed-delivery → return-to-origin-in-transit / nothing-collected.
- **Odoo actions:** **none on stock at this point.** The delivery picking is already `done` and stays done ([Fact] done pickings are preserved even by SO cancel — Odoo capture §1). The connector flags the order; the return-picking workflow runs only when goods physically arrive (scenario 3.7). Cancelling the SO now is allowed commercially but must not pretend stock is back.
- **Shopify evidence:** `ATTEMPTED_DELIVERY` / `FAILURE` fulfillment events where present ([Fact] Shopify capture §6.4); courier/user report otherwise. Read-only.
- **Roles:** User records the rejection report; Administrator decides commercial cancellation and any customer follow-up.
- **UX:** prominent *Rejected at door — goods with courier, stock NOT restored* banner; enters the return-tracking queue.
- **Audit:** rejection evidence source (courier feed vs user entry) + explicit "stock not restored" marker.

### 3.5 Scenario 5 — Failed delivery (retry expected)

- **Trigger:** courier fails an attempt (absent customer, address issue); redelivery planned.
- **Trajectory:** confirmed / dispatched → failed-delivery (remains until retry outcome) / nothing-collected.
- **Odoo actions:** none. Goods remain with courier; picking stays `done`.
- **Shopify evidence:** `ATTEMPTED_DELIVERY`, `DELAYED` events; read-only.
- **Roles:** User annotates attempt count/next attempt; no Administrator action required.
- **UX:** *Failed delivery — attempt n* status chip; ages into an attention list after a configurable number of attempts/days.
- **Audit:** each attempt recorded; transition out of `failed-delivery` requires new evidence (delivered → 3.1/3.8, or RTO → 3.6).

### 3.6 Scenario 6 — Return-to-origin (RTO) in progress

- **Trigger:** courier declares the shipment is returning to the warehouse.
- **Trajectory:** confirmed / failed-delivery → return-to-origin-in-transit / nothing-collected.
- **Odoo actions:** **none** (PD-COD-2). The connector may *prepare* (draft) nothing stock-side; it only tracks expectation of receipt. Explicitly forbidden: creating or validating a return picking from the courier claim.
- **Shopify evidence:** courier feed / user report; possibly `IN_TRANSIT` events on a return tracking number. Read-only.
- **Roles:** User records RTO notice. Administrator sees it in the RTO-expected queue.
- **UX:** *Return to origin — awaiting warehouse receipt*; countdown/aging indicator; explicit "stock not yet restored".
- **Audit:** RTO declaration source + declared date; divergence (RTO declared but never received) escalates to a review case after a configurable window.

### 3.7 Scenario 7 — Physical warehouse return + stock restoration

- **Trigger:** goods physically arrive back; warehouse inspects and accepts them.
- **Trajectory:** confirmed → cancelled-full (or stays confirmed if re-delivery is intended) / return-to-origin-in-transit → returned-validated / nothing-collected (or refunded if money had moved — see 3.15).
- **Odoo actions — the only stock-restoration path:** warehouse user runs the Odoo return wizard on the done delivery picking ([Fact] `stock.return.picking` reverses locations and sets `origin_returned_move_id` — Odoo capture §2), receives the physical goods, validates the return picking. [Fact] Only this validation puts stock back on hand. `to_refund` is checked when the SO delivered quantity should decrease ([Fact] it triggers "a decrease of the delivered… quantity in the associated Sale Order" — Odoo capture §2); for a pure RTO with intended commercial cancellation, `to_refund = true` is the default recommendation.
- **Shopify effect:** none automatic. Any Shopify refund/restock is a merchant action the connector reads (§8 refund visibility).
- **Roles:** warehouse User validates the return; Administrator confirms the linked commercial outcome (cancel vs redeliver).
- **UX:** state flips to *Returned — stock restored*; ledger's cancelled value updates; item leaves the RTO queue.
- **Audit:** return-picking reference, validated quantities, `to_refund` flag, inspecting actor.

### 3.8 Scenario 8 — Partial delivery + partial collection

- **Trigger:** customer accepts part of the parcel and pays only for what was accepted.
- **Trajectory:** confirmed / dispatched → partially-delivered / nothing-collected → partially-collected.
- **Odoo actions:** validate the delivery picking with move `quantity` set to **exactly the accepted quantities** ([Fact] Odoo 19: `stock.move.quantity` = processed sum of move lines; demand stays `product_uom_qty` — Odoo capture §2). The shortfall triggers backorder handling per the picking type's `create_backorder` setting: **ask** → user chooses; **always** → backorder auto-created; **never** → remainder demand cancelled ([Fact] quoted semantics, Odoo capture §2). Default recommendation for COD operations: `ask` or `always` — a backorder is **retained whenever a remainder is still expected**. Never adjust already-validated quantities afterwards.
- **Shopify evidence:** `PARTIALLY_FULFILLED`; partial manual capture may appear as `PARTIALLY_PAID` ([Fact] §1). **No `orderMarkAsPaid`** — it is full-payment-only in this design (§4 rule L-3).
- **Roles:** User validates quantities and records the partial collection event (amount + source). Administrator resolves any mismatch between accepted-goods value and collected cash (→ discrepancy, 3.14).
- **UX:** ledger shows original / fulfilled / collected / outstanding / cancelled side by side; partial-collection entry form pre-fills the fulfilled-value due amount but allows override with mandatory reason.
- **Audit:** per-line accepted quantities; collection event; backorder reference.

### 3.9 Scenario 9 — Partial delivery, remainder delivered later

- **Trigger:** the backorder from 3.8 (or a split shipment) is delivered on a second trip; remaining cash collected.
- **Trajectory:** confirmed / partially-delivered → fully-delivered / partially-collected → fully-collected.
- **Odoo actions:** validate the backorder picking ([Fact] backorder carries the not-done moves and links `backorder_id` — Odoo capture §2). Quantities on the first picking are untouched.
- **Shopify effect:** `FULFILLED` once all quantities fulfilled; `orderMarkAsPaid` becomes eligible only now (full collection + Administrator policy), never at the 3.8 stage.
- **Roles:** User validates and records the second collection event; no Administrator action if amounts net to zero outstanding.
- **UX:** ledger converges: outstanding → 0; two collection events visible with dates/actors.
- **Audit:** both pickings and both collection events linked to one order timeline.

### 3.10 Scenario 10 — Partial delivery, remainder cancelled

- **Trigger:** customer/merchant decides the undelivered remainder will not ship.
- **Trajectory:** confirmed → cancelled-partial-remainder / partially-delivered (final) / partially-collected → fully-collected *relative to the reduced scope* (collected = fulfilled value ⇒ outstanding 0, cancelled value > 0).
- **Odoo actions:** cancel the remainder **only after explicit confirmation** — either cancel the backorder picking, or at validation time choose the no-backorder path ([Fact] wizard `process_cancel_backorder()` validates with `skip_backorder=True`, dropping remaining demand — Odoo capture §2). **Never reverse quantities already delivered**; the done picking stands. Do not cancel the whole SO (that is scenario semantics for cancelled-full).
- **Shopify effect:** none automatic in MVP; Shopify-side line cancellation/refund of the remainder is read as evidence. `orderMarkAsPaid` remains disallowed here even if collected = fulfilled value, because Shopify's order total still includes the cancelled remainder — see OQ-COD-3.
- **Roles:** **Administrator confirmation is mandatory** for remainder cancellation (it destroys demand); User cannot silently trigger `never`-style demand drops from connector UI.
- **UX:** cancelled value becomes non-zero and is displayed distinctly from outstanding; order closes as *Partially delivered — remainder cancelled*.
- **Audit:** explicit confirmation actor + reason; cancelled quantities per line.

### 3.11 Scenario 11 — Partial collection without cancellation

- **Trigger:** goods fully (or partially) delivered but cash collected is less than due, with the shortfall expected later (e.g. courier remits in tranches, or customer pays balance on invoice terms).
- **Trajectory:** confirmed / fully-delivered (or partially-delivered) / partially-collected (persists) → fully-collected when the balance arrives.
- **Odoo actions:** none stock-side. Each remittance is a **separate collection event** (§4). No accounting registration (§6). **No full "mark as paid" action exists for partial collection** — the UI must not offer a shortcut that rounds a partial collection up to paid.
- **Shopify evidence:** possibly `PARTIALLY_PAID` if the merchant records partial manual captures ([Fact] §1); otherwise stays `PENDING`.
- **Roles:** User records each event; the order stays in the *outstanding* queue.
- **UX:** aging indicator on outstanding amount; sorted by outstanding age in the workspace queue.
- **Audit:** each event with amount/source/actor; automatic escalation to discrepancy after a configurable outstanding window.

### 3.12 Scenario 12 — Backorder creation + later completion

- **Trigger:** warehouse can only ship part of the demand (stock shortage), independent of customer acceptance.
- **Trajectory:** confirmed / reserved → dispatched(partial) → partially-delivered → fully-delivered / collections follow deliveries as in 3.8–3.9.
- **Odoo actions:** validate available quantities; per `create_backorder` semantics, create the backorder (`ask` answered yes, or `always`); the backorder auto-assigns when reservation is `at_confirm` ([Fact] Odoo capture §2). Later, reserve + validate the backorder.
- **Shopify effect:** where fulfillment write-back is enabled, partial fulfillments mirror the two shipments; each collection follows its delivery.
- **Roles:** standard warehouse User flow; no Administrator gate (no demand destroyed).
- **UX:** fulfillment dimension shows *Partially delivered — backorder open*; ledger's fulfilled value tracks each validation.
- **Audit:** picking chain (`backorder_id` links) surfaced in the order timeline.

### 3.13 Scenario 13 — Backorder cancellation

- **Trigger:** the open backorder from 3.12 will not ship (stock never arrives / customer withdraws remainder).
- **Trajectory:** confirmed → cancelled-partial-remainder / partially-delivered (final) / collection state per what was collected on the shipped part.
- **Odoo actions:** cancel the backorder picking after **explicit confirmation** (same guard as 3.10). [Fact] Cancelling a non-done picking is Odoo-native; delivered quantities on the done picking are never reversed (Odoo capture §1–2).
- **Roles/UX/audit:** as 3.10 — Administrator confirmation, cancelled value shown separately, reason recorded. Distinction from 3.10: trigger is supply-side, and the audit reason taxonomy records `stock-shortage` vs `customer-cancelled`.

### 3.14 Scenario 14 — Collection discrepancy

- **Trigger:** any mismatch: courier remittance ≠ recorded due amount; two evidence sources disagree; collection recorded with no matching delivery; delivered long ago with nothing collected.
- **Trajectory:** (any commercial) / (any fulfillment) / → discrepancy.
- **Odoo actions:** none automatic — a discrepancy **freezes** connector-initiated financial effects for the order (in particular `orderMarkAsPaid` is blocked while unresolved). Stock actions remain the normal Odoo flows.
- **Shopify evidence:** whatever conflicting transactions/statuses exist, displayed side-by-side.
- **Roles:** only the **Administrator** resolves a discrepancy: accept an adjusted amount (with reason), reassign the authoritative evidence, or write off — every resolution is a recorded decision, not an edit of the original events (append-only, §4).
- **UX:** discrepancy queue with red highlighting; each case shows expected vs recorded amounts, both evidence trails, and one-click resolution actions with mandatory reason.
- **Audit:** the review case itself is the audit artifact: creation cause, all evidence snapshots, resolution decision, actor, timestamp.

### 3.15 Scenario 15 — Refunded COD collection

- **Trigger:** money previously collected is returned to the customer (full or partial), typically after a return (3.7) or a pricing correction.
- **Trajectory:** (commercial per case) / (fulfillment per case, usually returned-validated) / fully- or partially-collected → refunded.
- **Odoo actions:** **none automatic in MVP** — no credit notes, no payment reversals (§6). If the merchant processes an Odoo-side refund manually, the connector reads invoice `payment_state: reversed`/`partial` as corroboration only ([Fact] value list — Odoo capture §4).
- **Shopify evidence (read-only):** [Fact] `Refund` object with `transactions` (the actual money movement), `totalRefundedSet`, `refundLineItems`; COD refunds appear as transactions on the manual gateway; a Refund's existence does not guarantee funds reached the customer — transaction `status` must be `SUCCESS` (Shopify capture §8). The connector records a negative-direction collection event sourced from the Shopify refund evidence.
- **Roles:** User sees refund state; Administrator confirms the ledger effect when the refund source is not the authoritative one.
- **UX:** collected amount shows gross collected and net-after-refund; refunded orders leave the outstanding queue but stay in history with the refund trail.
- **Audit:** refund evidence (Refund GID, transaction statuses) captured; linkage to the return picking when one exists.

### 3.16 Scenario 16 — Reconnect while a COD lifecycle is incomplete

- **Trigger:** the store connection was disconnected/suspended and is reconnected while COD orders sit mid-lifecycle (goods with courier, cash uncollected, RTO pending).
- **Trajectory:** unchanged by reconnect itself — reconnect is an evidence-refresh event, not a state transition.
- **Behaviour (per the reconnect/backfill policy — see [`reconnect-and-backfill-policy.md`](reconnect-and-backfill-policy.md), a sibling deliverable of this mission):**
  1. **State re-read:** the connector re-fetches each open COD order's current Shopify facts (order status, transactions, refunds, fulfillments) and re-derives dimensions 1–2 evidence.
  2. **No replay of collection evidence:** collection events recorded in the connector are **never** re-created, re-applied, or inferred again from re-read Shopify data — the connector-owned ledger is append-only and reconnect appends nothing on its own.
  3. **Review case on divergence:** if re-read Shopify state disagrees with connector state (e.g. Shopify now `PAID` or `REFUNDED` while the connector shows outstanding; order cancelled remotely; fulfillment appeared externally), the connector opens a **discrepancy/review case** (3.14) instead of auto-applying either side.
- **Odoo actions:** none automatic; frozen orders resume normal flows only after divergences are resolved.
- **Roles:** Administrator works the post-reconnect review queue; Users resume normal operations on non-divergent orders immediately.
- **UX:** post-reconnect banner: *n COD orders re-read, m divergences pending review*.
- **Audit:** reconnect event records the re-read snapshot hash/timestamp per order, so later disputes can show what Shopify said at reconnect time.

---

## 4. Value ledger design

**[Proposed product decision PD-COD-3 — five-value ledger.]** Every COD order
carries five separately displayed monetary values. None is ever collapsed into
another, and no synthetic "percent complete" replaces them.

| Value | Definition | Computation source |
|---|---|---|
| **Original value** | Total order value at import (shop currency; presentment shown secondarily). | [Fact] Shopify `totalPriceSet` (MoneyBag, shop + presentment — Shopify capture §3), snapshotted at import; re-snapshotted on `orders/edited` with the prior value retained in history. |
| **Fulfilled value** | Value of quantities actually delivered and accepted. | [Inference] Σ over delivery moves in state `done` of `move.quantity` × line unit price (after line discounts, tax treatment per store config), **minus** validated return-move quantities where `origin_returned_move_id` is set and `to_refund` is true — mirroring [Fact] Odoo's own delivered-qty compute (Odoo capture §2). |
| **Collected amount** | Cash actually received, net of refunds. | Σ of connector **collection-event records** (below); refund-direction events subtract. |
| **Outstanding amount** | Fulfilled value − collected amount (floored at 0 for display; a negative raw value is itself a discrepancy trigger). | Derived; recomputed on every picking validation and collection event. |
| **Cancelled value** | Value of quantities whose demand was cancelled (full cancel, remainder cancel, backorder cancel) plus returned-and-not-redelivered value. | [Inference] Σ of (demand `product_uom_qty` − done `quantity`) × unit price over cancelled moves, + validated `to_refund` return value when the commercial decision is cancellation. |

**Partial-collection recording design.** Collections are **per-event records**,
not a single mutable "amount paid" field. Each collection event stores at
minimum: amount (+currency), **evidence source** (§5), **actor** (Odoo user or
system identity), timestamp, direction (collection vs refund), optional
courier/remittance reference, and free-text note. Events are **append-only**;
corrections are compensating events, never edits — this is what makes the
reconnect no-replay rule (3.16) and discrepancy audit (3.14) possible.

**Rule L-3 — no full mark-as-paid for partial collection.** There is **no**
action anywhere in the connector that marks a partially collected COD order as
paid — neither an Odoo-side status shortcut nor a Shopify `orderMarkAsPaid`
call. `orderMarkAsPaid` eligibility requires: collection state
`fully-collected`, no open discrepancy, and Administrator policy enabled
(§6). [Inference] This is also the safe reading of the mutation itself, which
marks the whole order paid with no documented partial semantics (Shopify
capture §2; input shape verification pending — OQ-COD-2).

---

## 5. Evidence-source policy

**[Proposed product decision PD-COD-4 — four evidence sources, one
authoritative per store.]** Collection evidence can originate from exactly
four source types:

1. **Shopify manual-payment transactions** — `OrderTransaction` records on the manual gateway (`manualPaymentGateway: true`, kinds `SALE`/`CAPTURE`/`REFUND`/`CHANGE` — [Fact] Shopify capture §2), including effects of merchant-side `orderCreateManualPayment`/mark-as-paid done outside the connector.
2. **An Odoo User** — manual entry in the connector's collection form (the default MVP source for door-step cash).
3. **External courier integration** — remittance feeds from courier APIs. **[Open question OQ-COD-4] Future scope**; the evidence-source enum reserves the value now so the data model needs no migration later.
4. **Manual reconciliation process** — batch entry from an offline reconciliation (e.g. courier settlement spreadsheet), recorded as a distinct source so batch-derived events are distinguishable from live entries.

**Administrator per-store choice.** The Administrator designates, per store,
which source is **authoritative** for collection state. Only authoritative
evidence moves the collection dimension (§2.3) forward automatically.

**Conflict rule.** Evidence from a **non-authoritative** source never
auto-applies. It is recorded (append-only) and, when it diverges from the
authoritative picture — different amount, collection claimed where the
authoritative source shows none, or vice versa — the connector opens a
**review case** (scenario 3.14). The Administrator's resolution decides which
evidence stands; the losing evidence remains in the trail, marked superseded.
[Inference] This mirrors the connector's accepted no-autonomous-conflict-
resolution posture (cf. RA-020's rejection of autonomous bidirectional
conflict resolution in the inventory domain — same principle applied to money).

---

## 6. Accounting boundary

This section is binding product direction and is deliberately conservative.

**What MVP does (operational reconciliation and visibility):**

- Maintains the connector-owned value ledger (§4) and collection-event records.
- Derives and displays the three-dimension state everywhere (§2, §7).
- Reads Shopify financial/refund facts (§1–2, §8 of the Shopify capture) as evidence.
- **One optional outbound mutation:** `orderMarkAsPaid` on full collection, per-store Administrator opt-in, blocked by open discrepancies (rule L-3). This is a Shopify-side mutation and is therefore **gated as a DEC-031 Layer 2 replay-safe mutation** ([`../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md`](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md)): pre-flight state read (skip if already `PAID`), connector idempotency ledger, and post-call verification. [Open question OQ-COD-2] The exact `orderMarkAsPaid` input shape is a Partial source (Shopify capture §2) and must be verified on the raw page before the Wave 5+ packet.

**What stays disabled (RA-010 alignment — not re-proposed here):**

- **No automatic `account.payment` creation or posting.** [Fact] `account.payment.register.action_create_payments()` immediately posts and auto-reconciles journal entries whose correctness depends on journal, payment-method line, grouping, write-off handling, currency, and partner-bank configuration (Odoo capture §4). [Inference] A connector guessing these produces posted financial records that require reversals to undo — exactly the harm RA-010 rejects.
- **No automatic journal entries, no automatic invoicing**, no automatic credit notes for refunds (3.15), no bank-statement matching, no advanced financial reconciliation.
- No writing to invoice `payment_state` or any accounting field; [Fact] `paid` anyway requires zero residual and full matching, and "Paid" arrives only after bank reconciliation in Odoo's own flow (Odoo capture §4) — states a connector cannot honestly synthesize.

**Acceptance preconditions for ever enabling accounting automation** (all
required, as a separately accepted decision — none may be waived):

1. A **separately accepted accounting scope** decision record (which documents, which direction, which triggers).
2. An explicit **journal mapping** design (per store: journal, payment method line, partial/write-off policy) configured by the Administrator, never defaulted.
3. **Company and currency controls** — multi-company record targeting rules and shop-vs-presentment currency policy ([Fact] Shopify money fields are dual-currency MoneyBags — capture §3).
4. An accepted **test plan** covering posting, partial payments, refund reversal, and rollback.

Until such a decision exists, any prompt asking Claude or a worker to "just
register the payment in Odoo" conflicts with RA-010 and must be raised, not
executed.

---

## 7. UX specification summary — COD reconciliation workspace

Full visual and interaction design is deferred to the premium UX master
specification ([`premium-ux-master-specification.md`](premium-ux-master-specification.md),
sibling mission deliverable; see also the existing
[`ui-ux-final-design-spec.md`](ui-ux-final-design-spec.md)). Binding functional
requirements:

- **Queue of COD orders by collection state:** filterable by the §2.3 states, defaulting to actionable ones (nothing-collected + dispatched, partially-collected, discrepancy); sortable by outstanding amount and outstanding age; per-store scoping.
- **Three-dimension display:** each row shows all three dimension chips; no single merged status anywhere (PD-COD-1).
- **Discrepancy highlighting:** review cases visually distinct (top-of-queue, red accent), showing expected vs recorded amounts and both evidence trails; resolution actions Administrator-only with mandatory reason.
- **Partial-collection entry:** amount + source + reference + note; pre-filled with the current due amount; override requires a reason; creates an append-only event (§4); **no "mark fully paid" shortcut on partial amounts** (rule L-3).
- **Value ledger display:** the five §4 values always shown together on the order's COD panel, with the collection-event and picking timeline beneath.
- **Stock-truth messaging:** failed-delivery/RTO states must carry explicit "stock not restored — awaiting warehouse return validation" language (PD-COD-2), with a deep link to the Odoo return-picking flow for warehouse users.
- **Reconnect banner:** post-reconnect divergence count with one click into the review queue (3.16).

---

## 8. Test matrix and UAT summary

Full QA matrices live in [`../05-qa/cod-uat-matrix.md`](../05-qa/cod-uat-matrix.md)
(companion deliverable; this section is the summary and the pointer).

**Test families (unit / integration):**

| Family | Covers scenarios | Focus |
|---|---|---|
| State-derivation unit tests | all | Each §2 state derives correctly from fixture Odoo/Shopify facts; no dimension collapses another. |
| Ledger computation unit tests | 1, 8–13, 15 | Five values from move quantities + events; return `to_refund` subtraction; negative-outstanding → discrepancy. |
| Collection-event unit tests | 8, 9, 11, 14, 15 | Append-only enforcement; compensating events; source typing; L-3 (no partial mark-as-paid path exists). |
| Picking/backorder integration tests | 2, 3, 8–13 | ask/always/never behaviours; backorder chain; remainder-cancel confirmation gate; delivered quantities never reversed. |
| Return-picking integration tests | 4, 6, 7 | No stock movement on courier reports; stock restored only on validated return; `origin_returned_move_id`/`to_refund` effects. |
| Evidence-policy integration tests | 11, 14 | Authoritative-source application; non-authoritative → review case, never auto-apply. |
| Shopify read-model tests | 1, 15, 16 | COD classification via `manualPaymentGateway`; refund via `Refund.transactions` with `SUCCESS` check; financial-status mapping. |
| `orderMarkAsPaid` gating tests (Wave 5+) | 1, 9, 14 | Full-collection + policy + no-discrepancy preconditions; Layer 2 pre-read/idempotency/verify; blocked on partial (8, 11) and discrepancy (14). |
| Reconnect tests | 16 | Re-read without event replay; divergence → review case; append-only ledger untouched. |

**UAT:** the 16 scenarios in §3 are the UAT cases, one-to-one (UAT-COD-01 …
UAT-COD-16). Pass criterion pattern for each: *given the scenario's trigger
executed on a live pilot/staging pair, the three dimensions read exactly the
§3 trajectory endpoint, the five ledger values match hand-computed expectations,
stock on hand matches physical reality (restored only via validated return for
4/6/7), the required role gates held (Administrator-only actions refused for
User), and the audit trail contains the scenario's mandated entries.*
UAT-COD-16 additionally requires demonstrating zero duplicate collection
events after a disconnect/reconnect cycle.

---

## 9. Wave allocation

Per the MVP program structure ([`../07-implementation-plan/mvp-program-state.md`](../07-implementation-plan/mvp-program-state.md)):

| Deliverable | Wave | Justification |
|---|---|---|
| **COD import policy** (COD classification via manual-gateway signals, financial-status read model, connector COD flag + ledger snapshot at import) | **Wave 2 — Task 012 addendum** ([`../07-implementation-plan/task-012-order-import-implementation-packet.md`](../07-implementation-plan/task-012-order-import-implementation-packet.md)) | [Inference] COD identity must be captured at order import or every later wave re-derives it inconsistently; it is pure read-model work, fitting Wave 2's import scope with no new mutation surface. |
| **COD ↔ fulfillment interplay** (partial validation, backorder semantics, return-picking linkage, fulfillment-dimension derivation, scenarios 2–13 mechanics) | **Wave 4** | [Inference] Depends on the fulfillment/stock integration that Wave 4 owns (Task 014 family); shipping it earlier would duplicate picking logic, later would block reconciliation UI on untested state derivation. |
| **COD reconciliation workspace UI** (queue, ledger display, collection entry, discrepancy review) | **Wave 5** | [Inference] UI consumes Wave 2 + Wave 4 read models; Wave 5 is the program's UI wave, and the workspace is meaningless before the states it displays exist. |
| **`orderMarkAsPaid` outbound** | **Wave 5+ behind DEC-031 Layer 2** | [Inference] It is the design's only COD financial mutation; it needs the Layer 2 replay-safety machinery, the resolved input-shape verification (OQ-COD-2), and the Administrator policy surface from the Wave 5 workspace — and it is strictly optional, so it must never gate earlier waves. |

---

## 10. Proposed product decisions (consolidated)

| ID | Decision | Where defined |
|---|---|---|
| PD-COD-1 | Three independent state dimensions; never collapsed. | §1, §2 |
| PD-COD-2 | Stock restored only via validated Odoo return picking; never on courier/report evidence. | §1, §3.4–3.7 |
| PD-COD-3 | Five-value ledger computed from move quantities + append-only collection events; no partial mark-as-paid (rule L-3). | §4 |
| PD-COD-4 | Four evidence sources; Administrator picks the authoritative one per store; non-authoritative divergence → review case, never auto-apply. | §5 |
| PD-COD-5 | MVP accounting boundary: operational ledger + optional Layer-2-gated `orderMarkAsPaid` only; Odoo accounting automation disabled pending the four §6 acceptance preconditions. | §6 |
| PD-COD-6 | Wave allocation as per §9. | §9 |

All are **Proposed** until accepted by the product owner + control room; none
authorizes implementation.

## 11. Open questions

| ID | Question | Blocking |
|---|---|---|
| OQ-COD-1 | Odoo 19 `sale.order.cancel` wizard trigger conditions (capture §1 open question) — affects automated-cancel design in Wave 4. | Wave 4 packet |
| OQ-COD-2 | Exact `orderMarkAsPaid` (and `orderCreateManualPayment`) input shapes — current evidence is a Partial source; verify raw pages before any mutation packet. | Wave 5+ packet |
| OQ-COD-3 | Whether `orderMarkAsPaid` is appropriate after a remainder cancellation (3.10) where Shopify's order total still includes cancelled lines — likely requires a Shopify-side order edit/refund first; needs live verification. | Wave 5+ packet |
| OQ-COD-4 | Courier-integration evidence source: which couriers, feed formats, and matching keys — **future scope**; only the enum value is reserved now. | Post-MVP decision |
| OQ-COD-5 | Whether Odoo's built-in COD payment provider (`payment_custom`) populates `sale.order.amount_paid` (Odoo capture §4 open question) — determines if that field can corroborate the connector ledger. | Wave 4 packet |
| OQ-COD-6 | Currency policy for collection events on presentment≠shop currency stores (ties to §6 precondition 3 even for the operational ledger's display). | Wave 2 addendum |

---

*End of document. Companion deliverables referenced: [`reconnect-and-backfill-policy.md`](reconnect-and-backfill-policy.md), [`premium-ux-master-specification.md`](premium-ux-master-specification.md), [`../05-qa/cod-uat-matrix.md`](../05-qa/cod-uat-matrix.md) — created/updated by this mission's sibling tasks.*
