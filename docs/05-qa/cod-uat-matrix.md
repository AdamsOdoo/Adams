# COD UAT Matrix — 16 Executable Scenarios + Negative Cases

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. Planning only;
> no test executed; no gate opened.** Companion QA deliverable of
> [`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md)
> (the COD doc); the 16 UAT cases below are one-to-one with its §3 scenarios
> (UAT-COD-01…16). Executable only in Wave 6 (COD import layer lands Wave 2,
> fulfillment interplay Wave 4, workspace UI Wave 5 — COD doc §9). All state
> names, ledger values, and role gates are the COD doc's; nothing is
> re-decided here.

## Shared conventions

- **Environment:** Odoo.sh branch build + Shopify dev store with a manual
  payment method configured as COD (yields `manualPaymentGateway: true`
  transactions — [Fact], COD doc §1/§5) and a bound test product catalog.
- **Shared preconditions (every case):** store `connected`; order domain
  enabled; confirmation policy configured so the COD order confirms (approved
  manual gateway + `manual_gateway_policy` per case, defaults per the
  [sales-order policy](../02-product/sales-order-lifecycle-and-confirmation-policy.md) §7);
  two test users provisioned: one **Connector User**, one **Connector
  Administrator** (two-role model).
- **Expected end state** is always expressed in the three dimensions
  *Commercial / Fulfillment / Collection* (PD-COD-1) — a case fails if any
  screen collapses them into one status.
- **Ledger expectations** name the five values *Original / Fulfilled /
  Collected / Outstanding / Cancelled* (PD-COD-3).
- **Evidence to capture (every case):** screenshot of the three-dimension
  display; the five ledger values; the relevant Odoo picking/return records;
  the connector audit trail entries; Shopify admin order screenshot
  (financial + fulfillment status).
- **Shared pass criterion (every case, from COD doc §8):** dimensions equal
  the scenario's trajectory endpoint; ledger matches hand-computed
  expectations; stock on hand matches physical reality; Administrator-only
  actions are refused for the User; the audit trail contains the mandated
  entries. Per-case criteria below are additive.
- **Reference order:** 10 units of product A at 10.00 (shop currency),
  original value 100.00, unless a case says otherwise.

## UAT cases

### UAT-COD-01 — Full delivery + full collection (scenario 3.1)

- **Preconditions:** COD order imported and confirmed; stock available.
- **Steps:** reserve + validate the delivery picking at full demand (User);
  record one collection event of 100.00, source "Odoo User" (User); with
  Administrator mark-as-paid policy ON, observe the connector's
  `orderMarkAsPaid` job.
- **End state:** confirmed / fully-delivered / fully-collected.
- **Ledger:** 100 / 100 / 100 / 0 / 0.
- **Pass:** order leaves the actionable queue; Shopify shows `PAID` (policy
  on) or legitimately stays `PENDING` (policy off); mark-as-paid job carries
  Layer 2 attempt evidence.

### UAT-COD-02 — Cancellation before dispatch (scenario 3.2)

- **Preconditions:** COD order confirmed; no picking validated.
- **Steps:** cancel the SO (Odoo `action_cancel`); re-scan.
- **End state:** cancelled-full / not-dispatched / nothing-collected.
- **Ledger:** 100 / 0 / 0 / 0 / 100.
- **Pass:** all non-done pickings cancelled automatically; **no return
  picking exists**; order excluded from the active collection queue but
  visible in history; cancellation origin recorded in audit.

### UAT-COD-03 — Cancellation after reservation (scenario 3.3)

- **Preconditions:** picking `assigned` (reserved), not validated.
- **Steps:** cancel the SO; verify free stock.
- **End state:** cancelled-full / not-dispatched / nothing-collected.
- **Ledger:** as UAT-COD-02.
- **Pass:** reservation released back to free stock (on-hand unchanged,
  free qty restored); audit notes "reservation existed and was released";
  no receipt expected.

### UAT-COD-04 — Full rejection at the door (scenario 3.4)

- **Preconditions:** delivery picking validated (`done`); courier reports
  full refusal, zero cash.
- **Steps:** User records the rejection report; do **not** run any return.
- **End state:** confirmed / return-to-origin-in-transit (via
  failed-delivery) / nothing-collected.
- **Ledger:** 100 / 100 / 0 / 100 / 0 (fulfilled per validated picking;
  nothing yet returned).
- **Pass:** picking stays `done`; **stock is NOT restored**; UI shows the
  "Rejected at door — goods with courier, stock NOT restored" banner; order
  enters the return-tracking queue; audit carries the evidence source and an
  explicit "stock not restored" marker.

### UAT-COD-05 — Failed delivery, retry expected (scenario 3.5)

- **Preconditions:** as UAT-COD-04, but courier plans redelivery.
- **Steps:** User annotates attempt 1 (+ next-attempt date); wait/redeliver.
- **End state:** confirmed / failed-delivery (persists) / nothing-collected.
- **Pass:** zero Odoo stock action; "Failed delivery — attempt 1" chip;
  case ages into the attention list after the configured attempts/days;
  transition out requires new evidence (delivered → UAT-COD-01/08 path,
  RTO → UAT-COD-06).

### UAT-COD-06 — RTO in progress (scenario 3.6)

- **Preconditions:** failed-delivery state from UAT-COD-05.
- **Steps:** User records the courier RTO declaration.
- **End state:** confirmed / return-to-origin-in-transit / nothing-collected.
- **Pass:** **no return picking created or validated from the claim**
  (PD-COD-2); "awaiting warehouse receipt" with explicit "stock not yet
  restored"; aging indicator active; non-receipt past the configured window
  escalates to a review case.

### UAT-COD-07 — Physical warehouse return + stock restoration (scenario 3.7)

- **Preconditions:** UAT-COD-06 end state; goods physically arrive.
- **Steps:** warehouse User runs the Odoo return wizard on the done picking
  (`to_refund = true`), receives, validates the return picking;
  Administrator confirms commercial cancellation.
- **End state:** cancelled-full / returned-validated / nothing-collected.
- **Ledger:** 100 / 0 / 0 / 0 / 100 (fulfilled value reduced by the
  validated `to_refund` return; cancelled value now carries the returned
  value).
- **Pass:** stock back on hand **only after** return validation
  (`origin_returned_move_id` set); ledger updates on validation, not on the
  RTO claim; audit carries return-picking reference, quantities,
  `to_refund`, actor.

### UAT-COD-08 — Partial delivery + partial collection (scenario 3.8)

- **Preconditions:** COD order confirmed; customer will accept 6 of 10.
- **Steps:** validate the picking with move quantity 6; choose backorder
  (ask→yes or `always`); record collection event 60.00.
- **End state:** confirmed / partially-delivered / partially-collected.
- **Ledger:** 100 / 60 / 60 / 0 / 0, backorder open for 4.
- **Pass:** entry form pre-fills 60.00 (fulfilled-value due), override
  demands a reason; **no mark-as-paid affordance exists** (rule L-3);
  Shopify shows `PARTIALLY_FULFILLED`; backorder reference in audit.

### UAT-COD-09 — Remainder delivered later (scenario 3.9)

- **Preconditions:** UAT-COD-08 end state.
- **Steps:** reserve + validate the backorder (4 units); record collection
  event 40.00.
- **End state:** confirmed / fully-delivered / fully-collected.
- **Ledger:** 100 / 100 / 100 / 0 / 0; two collection events visible with
  dates/actors.
- **Pass:** first picking's quantities untouched; `orderMarkAsPaid`
  eligibility appears only now (never at the UAT-COD-08 stage); both
  pickings + events linked in one timeline.

### UAT-COD-10 — Remainder cancelled (scenario 3.10)

- **Preconditions:** UAT-COD-08 end state (60 collected, backorder for 4).
- **Steps:** User attempts remainder cancellation → must be refused;
  Administrator cancels the backorder with reason.
- **End state:** cancelled-partial-remainder / partially-delivered (final) /
  fully-collected relative to reduced scope.
- **Ledger:** 100 / 60 / 60 / 0 / 40 — cancelled value displayed distinctly
  from outstanding.
- **Pass:** Administrator confirmation mandatory; delivered quantities never
  reversed; SO not cancelled as a whole; **`orderMarkAsPaid` remains
  disallowed** (OQ-COD-3 posture: Shopify total still includes the
  remainder); confirmation actor + reason + cancelled quantities audited.

### UAT-COD-11 — Partial collection without cancellation (scenario 3.11)

- **Preconditions:** order fully delivered; courier remits in two tranches.
- **Steps:** record collection event 70.00; verify queue state; later record
  30.00.
- **Intermediate state:** confirmed / fully-delivered / partially-collected;
  ledger 100 / 100 / 70 / 30 / 0 with outstanding aging indicator.
- **End state:** fully-collected; ledger 100 / 100 / 100 / 0 / 0.
- **Pass:** each remittance is a separate append-only event; **no UI action
  can round a partial collection up to paid**; order sorted by outstanding
  age while open; configured outstanding window escalates to discrepancy if
  left unresolved.

### UAT-COD-12 — Backorder creation + later completion (scenario 3.12)

- **Preconditions:** stock covers only 7 of 10 (supply-side shortage).
- **Steps:** validate 7 with backorder; deliver + collect 70.00; restock;
  reserve + validate the backorder; collect 30.00.
- **End state:** confirmed / fully-delivered / fully-collected.
- **Ledger:** converges to 100 / 100 / 100 / 0 / 0.
- **Pass:** no Administrator gate needed (no demand destroyed); picking
  chain (`backorder_id` links) visible in the order timeline; collections
  follow deliveries.

### UAT-COD-13 — Backorder cancellation (scenario 3.13)

- **Preconditions:** UAT-COD-12 mid-state (7 delivered/collected, backorder
  open); stock never arrives.
- **Steps:** Administrator cancels the backorder, reason `stock-shortage`.
- **End state:** cancelled-partial-remainder / partially-delivered (final) /
  collection per shipped part (fully-collected relative to reduced scope).
- **Ledger:** 100 / 70 / 70 / 0 / 30.
- **Pass:** as UAT-COD-10, plus the audit reason taxonomy distinguishes
  `stock-shortage` from `customer-cancelled`.

### UAT-COD-14 — Collection discrepancy (scenario 3.14)

- **Preconditions:** order fully delivered, due 100.00; courier remittance
  feed (non-authoritative source) reports 80.00 while the authoritative
  source shows nothing.
- **Steps:** record the non-authoritative event; observe the review case;
  User attempts resolution → refused; Administrator resolves (accept
  adjusted amount with reason).
- **End state:** (unchanged commercial/fulfillment) / discrepancy → resolved
  per the Administrator decision.
- **Pass:** non-authoritative evidence never auto-applies (PD-COD-4);
  discrepancy **freezes** `orderMarkAsPaid` while open; resolution is a
  recorded decision, not an edit — original events intact, losing evidence
  marked superseded; case shows expected vs recorded amounts and both
  evidence trails.

### UAT-COD-15 — Refunded COD collection (scenario 3.15)

- **Preconditions:** UAT-COD-07-style return after full collection (100.00
  collected, goods returned); merchant refunds in Shopify against the manual
  gateway.
- **Steps:** create the Shopify refund; let the scan import the refund
  evidence; verify the ledger.
- **End state:** (per case) / returned-validated / refunded.
- **Ledger:** collected shows gross 100 and net-after-refund 0; outstanding
  0.
- **Pass:** refund recorded as a negative-direction collection event sourced
  from `Refund.transactions` with transaction `status = SUCCESS` checked —
  a Refund object alone is not treated as money moved ([Fact], COD doc
  §2.3/§3.15); **no Odoo credit note or payment reversal is created**;
  refund GID + transaction statuses in audit, linked to the return picking.

### UAT-COD-16 — Reconnect with incomplete COD lifecycles (scenario 3.16)

- **Preconditions:** at least three open COD orders mid-lifecycle (one
  dispatched-uncollected, one RTO-pending, one partially collected);
  disconnect the store; while disconnected, in Shopify: mark one order as
  paid and cancel another; reconnect.
- **Steps:** run reconnect; observe catch-up; open the post-reconnect banner
  and review queue.
- **End state:** unchanged by reconnect itself; divergent orders →
  discrepancy/review cases; non-divergent orders resume normally.
- **Pass:** re-read refreshes evidence only; **zero duplicate collection
  events** after the disconnect/reconnect cycle (ledger event count
  unchanged for untouched orders — the COD doc §8's explicit UAT-COD-16
  criterion); each divergence (remote `PAID` vs connector outstanding;
  remote cancel) opens a review case rather than auto-applying either side;
  banner shows "n re-read, m divergences"; re-read snapshot hash/timestamp
  audited per order.

## Negative cases (mandated, beyond the 16)

| ID | Case | Steps | Pass criteria |
| --- | --- | --- | --- |
| UAT-COD-N1 | **Courier claim must not restock** | From UAT-COD-04/06 state, attempt every plausible path to restock from the claim (courier feed entry, User action, re-scan) | No stock movement occurs by any path other than a validated Odoo return picking; UI offers no "restock from report" affordance (PD-COD-2) |
| UAT-COD-N2 | **Partial collection must not mark paid** | From UAT-COD-08/11 partial state, search the workspace, order form, and RPC surface for any mark-as-paid/mark-fully-collected action | No such action exists or succeeds for a partially collected order; a forced RPC call is rejected server-side (rule L-3) |
| UAT-COD-N3 | **Discrepancy blocks mark-as-paid** | From UAT-COD-14 open state with policy ON and collection completed to 100 | `orderMarkAsPaid` is not attempted while the discrepancy is unresolved; resolves + collects → becomes eligible |
| UAT-COD-N4 | **User cannot perform Administrator acts** | As Connector User: attempt remainder cancellation, discrepancy resolution, mark-as-paid policy change, authoritative-source change | Every attempt refused server-side (not just hidden); refusals visible in test evidence |
| UAT-COD-N5 | **Non-authoritative source never advances state** | Record a non-authoritative full-collection event with no authoritative corroboration | Collection dimension does not advance; review case opens on divergence (PD-COD-4) |

## Open items

- [Open question] UAT-COD-01/09's mark-as-paid step depends on OQ-COD-2
  (exact `orderMarkAsPaid` input shape) being verified before the Wave 5+
  packet; until then those steps execute with policy OFF and the mutation
  assertion is deferred.
- [Open question] Currency handling of collection events on
  presentment≠shop-currency stores (OQ-COD-6) — the reference order here is
  same-currency by construction.
