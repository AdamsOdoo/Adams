# Task 014 — Fulfillment / Tracking Update (Proposed)

> **Superseded (2026-07-16, Fable gap-closure mission):** this early scope
> proposal is retained as history only. The canonical, decision-closed
> specification is `task-014-fulfillment-tracking-implementation-packet.md` (plus its dated
> gap-closure addendum). Do not use this file as an implementation source.

> Planning-only future implementation task spec, part of the MVP domain
> implementation-slicing sequence
> ([`mvp-domain-implementation-sequence.md`](./mvp-domain-implementation-sequence.md),
> Area 5). Describes scope/boundary/approach only.

## Status

**Proposed only. Not authorized.** Depends on Task 012 (order import)
existing — fulfillment resolves order bindings through `sale` and
product/variant bindings through `product`, and structurally never
depends on `inventory` (Part C, module-ownership section) — plus
foundation Tasks 002/003 and the not-yet-defined "fulfillment domain
gate" (`ui-ux-implementation-task-map.md` Group 14). This document does
not authorize, start, or imply authorization of any of the above.

## Objective

Create Shopify fulfillments and update tracking information from
validated Odoo `stock.picking` records — using FulfillmentOrder-based
mutations exclusively, never guessing an unmatched picking's fulfillment
target, and never silently double-fulfilling due to a non-idempotent
mutation.

## Preconditions

- Task 012 merged and reviewed (order binding must already resolve, and
  product-variant binding from Task 010 must resolve the picking's
  stock-move lines to Shopify order line items).
- Foundation Tasks 002/003 merged and gate-opened.
- The fulfillment domain gate explicitly opened.
- MBQ-60 (whether `shopify_connector_fulfillment` requires Odoo's
  `stock_delivery`/`delivery` module) — **Decided, DEC-018:** required;
  absence is a named readiness/health blocker, never silently degraded —
  confirmed as the design baseline for this task's own final §9 prompt.

## Fulfillment/tracking update boundary

`shopify_connector_fulfillment` owns fulfilment/tracking write-back and
the customer-notification guard (Decision — DEC-008; DEC-011). Depends on
`core` + `sale` only, plus Odoo's own `stock`/`delivery`-family apps
directly — never on `inventory`; it must not read `inventory`'s
Odoo-location ↔ Shopify-Location mapping table (a repeatedly restated
boundary rule, Part C §C.1). Phase 1 scope is single-fulfillment-location
matching; genuinely multi-location fulfillment is deferred.

## Odoo picking validation trigger dependency

The source/trigger is a validated `stock.picking` (delivery order) —
specifically the Validate action (Decision — DEC-011, Part C §B.3). Each
validated picking, including a backorder-split picking, is its own
independent fulfillment event. Invoice/payment state is explicitly not a
fulfillment trigger condition (DEC-003 Domain 9). Regardless of
one/two/three-step delivery workflow, the trigger is the final
`stock.picking` in the chain whose Validate action represents goods
actually leaving the warehouse — exact per-workflow trigger-picking
identification mechanism remains an implementation-planning open item,
not a numbered MBQ. Matching chain: Odoo picking's sale order → bound
Shopify order (via the `sale` order binding) → that order's open
FulfillmentOrder(s) → matched line items via
`FulfillmentInput.lineItemsByFulfillmentOrder`. An unmatched picking is
never fulfilled by guess (RA-023, unweakened) — it blocks for manual
review.

## Job-source / odoo_event dependency (DEC-019)

A fulfillment creation triggered by a validated `stock.picking` is one of
the two accepted use cases for the `odoo_event` job-source value (the
seventh accepted value added to Part A §D.2's vocabulary by
[DEC-019](../04-decisions/DEC-019-mbq-62-odoo-event-job-source.md)):
`job_source = odoo_event`, `trigger_origin =
'fulfillment_picking_validation'`. This exists specifically so the job's
source can be recorded honestly for the dashboard's "last successful sync
per domain with mechanism label" card and the sync-center trigger/source
filter — it is not a new top-level job-source enum invention (the earlier
Fable-corrected error, DEC-019 §2). Retry eligibility is governed by
error class, not job source, but job source affects which
retry-count/backoff bucket a job draws from and which dashboard label it
displays under.

## Tracking number/carrier handling

Odoo 19's `stock_delivery` module defines `carrier_id` (Many2one →
`delivery.carrier`), `carrier_tracking_ref` (Char), and
`carrier_tracking_url` (computed, populated only if both `carrier_id` and
`carrier_tracking_ref` are set) — Official fact, verified against
`github.com/odoo/odoo` 19.0 source, access date 2026-07-03. Proposed
field-mapping direction (not implementation-final): `carrier_tracking_ref`
→ Shopify tracking number; `carrier_id` (resolved to carrier/company
name) → Shopify tracking company; `carrier_tracking_url` → Shopify
tracking URL, with Shopify's own tracking-URL-guessing behavior as
fallback. Exact mapping/precedence remains open for this task's own final
§9 prompt.

## Shopify write requirements

Confirmed by accepted docs (Decision — DEC-011, Part C §B.5): tracking
may be set at fulfillment creation (`fulfillmentCreate`) or updated
afterward (`fulfillmentTrackingInfoUpdate`); a tracking-only update never
creates a second fulfillment. FulfillmentOrder-exclusive posture: Shopify
FulfillmentOrder-based mutations exclusively; legacy Order/Fulfillment
endpoints are never used (RA-022, unweakened).

## Manual review/error cases

- Unmatched picking (lines can't resolve to an order/product binding) →
  `mapping missing` → `failed_retryable`.
- Fulfillment-location mismatch (the live `assignedLocation` disagrees
  with the picking's expected location) → `ambiguous match` →
  `blocked_manual_review` (an accepted widening of this error class at
  blueprint level only, Fable minor finding 2, Part C §B.8 — not a
  settled prior interpretation, no 17th error class added).
- Stale/recreated FulfillmentOrder/Fulfillment GID → `binding conflict` →
  `blocked_manual_review`.
- A store/order requiring explicit notification confirmation not yet
  given → `fulfillment notification confirmation missing` →
  `blocked_manual_review`.
- `stock_delivery` module absent → named readiness/health blocker
  (MBQ-06/MBQ-60), tracking write-back disabled, never silently degraded.

## Retry behavior

Fulfillment mutations are **not** on Shopify's `@idempotent` mutation
list (unlike inventory's `inventorySetQuantities`) — so any
ambiguous-outcome failure (timeout/connection loss with unknown result)
triggers the ambiguous-outcome rule: no blind retry (RA-014); instead a
safe verification read (re-query the order's Fulfillments/FulfillmentOrder
status) before retry, or `blocked_manual_review` if inconclusive. Both an
operation-level idempotency key (conceptually `(store, operation type,
picking_id, Shopify target ID where known, payload version/hash)`) and
the verification-read rule are required together — neither alone is
sufficient. Operations against the same `(store, picking, Shopify
target)` are serialized while a prior operation is unresolved (exact
mechanism open, MBQ-21, shared across domains). Customer-notification
default is no notification unless explicitly enabled (Decision — DEC-007
§5; DEC-011; RA-009), persisted at enqueue time and never re-read at
retry.

## Tests required

Non-idempotent-mutation handling via verification-read-before-retry
(never a blind retry); backorder/partial-fulfillment sequencing (each
picking in a chain fulfilled independently, never merged);
notification-suppression-by-default correctness including
retry-preserves-original-decision; FulfillmentOrder-location-mismatch
handling; `stock_delivery` absence handling (readiness-blocked, not
silently degraded). Exact fixtures for this task's own final §9 prompt.
If no Odoo runtime exists at coding time, tests must still be written and
syntax-validated per the Task 001A precedent.

## Manual validation

On a live Odoo 19 + PostgreSQL instance once a runtime exists: validate a
picking and confirm a fulfillment is created only once even under a
simulated ambiguous-outcome retry; confirm a backorder-split picking
produces two independent fulfillment events; confirm no notification is
sent when the default is off; confirm the readiness/health surface
reports `stock_delivery` absence as a named blocker rather than degrading
silently.

## Rollback

Single-PR revert; fulfillment never gates inventory or vice versa
(independent siblings), so a revert of this task does not affect Task
013. Reverting drops the FulfillmentOrder/Fulfillment binding model;
already-created Shopify fulfillments are unaffected (no automatic
un-fulfillment is triggered).

## Acceptance criteria

- Only allowed files changed (per this task's own future final §9
  prompt).
- No fulfillment mutation is retried blindly; every ambiguous outcome is
  verified by a safe read first.
- Every validated picking maps to exactly one fulfillment event; a
  backorder chain never merges into one.
- Customer notification defaults to off and is never re-decided at
  retry.
- `stock_delivery` absence is reported as a named readiness blocker,
  never silently degraded.
- Zero inventory/refund/payout logic in the diff.

## Definition of done

Per `CLAUDE.md` §9 / `implementation-task-template.md` §7: code + tests
written (and passing where a runtime exists); `pr-review-checklist.md` §C
satisfied; only allowed files changed; handoff updated; ChatGPT reviews
and accepts before any next task starts.

## Explicit exclusions

- **No inventory adjustment** (fulfillment never reads or writes
  inventory's location-mapping table or quantities).
- **No refund.**
- **No payout.**
- **No returns/RMA.**
- **No fulfillment-order advanced lifecycle unless already accepted** —
  MBQ-61: Phase 1 does not subscribe to the `FULFILLMENT_ORDERS_*`
  lifecycle family (holds, cancellation-request lifecycle, merges,
  splits, moves, reschedules are all decided-by-conservative-exclusion
  and out of this task's scope).
