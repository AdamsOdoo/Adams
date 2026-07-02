# DEC-011 — Fulfillment Architecture Strategy

> Proposed **architecture** decision record for **AR-008** (fulfillment
> architecture), for the premium Odoo 19 ↔ Shopify Connector. Companion
> evidence-backed brief:
> [`../03-architecture/ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md).

## Status

**Proposed for ChatGPT review.**

- **Sprint:** AR-007 + AR-008 Decision Preparation (after DEC-008/DEC-009
  acceptance, PR #65 merged into `Shopify-connector`).
- **Date:** 2026-07-02.
- **This record does not self-accept.** It becomes an accepted architecture
  decision only after ChatGPT (with Fable's advisory review) formally accepts
  it, mirroring the DEC-004/005/006/007/008/009 acceptance pattern.

## Scope

**AR-008 fulfillment architecture only.** This record decides the Phase 1
fulfillment **source/target posture**, the **FulfillmentOrder posture**, the
**tracking-update posture**, the **customer-notification posture** (as an
application of the already-accepted DEC-007 default, not a re-statement),
**location/line matching**, **partial/backorder posture**, **idempotency/
retry** (as an application of DEC-009), and **user-facing log/audit**
requirements for fulfillment. It does **not** decide exact Odoo model fields,
exact mutation parameters where not verified, exact tracking field source,
exact partial-fulfillment rules beyond the general posture, exact
notification UI granularity, or exact retry constants (all routed to the
Master Blueprint, §"What remains open"). It does **not** modify DEC-003/004/
005/006/007/008/009.

## Accepted context

- **DEC-003 (MVP scope):** fulfillment and tracking write-back (Odoo→Shopify)
  is in MVP; multi-package/multi-location fulfillment (C-FUL-02) is deferred,
  not rejected.
- **DEC-006 (binding/dedup/identity):** dedicated, store-scoped bindings;
  order/fulfillment identity gets separate handling; exact fulfillment-
  identity shape deferred to this record.
- **DEC-007 (Phase 1 scope clarifications):** customer-notification default
  is no notification unless explicitly enabled/confirmed, grounded in
  Shopify's own `FulfillmentInput.notifyCustomer`/`fulfillmentTrackingInfoUpdate`
  defaults; exact configuration granularity left open.
- **DEC-008 (module boundaries):** `shopify_connector_fulfillment` depends on
  `core` + `sale` only — explicitly **not** on `shopify_connector_inventory`.
- **DEC-009 (error/retry/idempotency):** "fulfillment notification
  confirmation missing" error class; the ambiguous-outcome rule for
  non-`@idempotent` writes.

## Decision proposed

Adopt the Phase 1 fulfillment architecture set out in
[`ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md):
validated Odoo `stock.picking` (delivery) is the fulfillment trigger;
Shopify fulfillment is created exclusively via FulfillmentOrder-based
mutations (`fulfillmentCreate`), matched to the correct order, FulfillmentOrder,
line items, and quantities via `lineItemsByFulfillmentOrder`; tracking is set
at creation and updatable afterward via `fulfillmentTrackingInfoUpdate`; the
customer-notification default is off unless explicitly enabled/confirmed,
persisted per job at enqueue time; location/line mismatches route to manual
review rather than being guessed; multi-package/multi-location automation
remains deferred (DEC-003); and the DEC-009 ambiguous-outcome rule governs
retries of `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`, both of which
sit outside Shopify's 17-mutation `@idempotent` surface.

## Fulfillment source/target posture

- **Source:** validated `stock.picking` (delivery order) — the Validate
  action is the trigger. Each validated picking, including a backorder-split
  picking, is its own fulfillment event.
- **Target:** Shopify FulfillmentOrder-based flow exclusively; legacy Order/
  Fulfillment endpoints are never used (RA-022).
- **Invoice/payment state** is not a fulfillment trigger condition (DEC-003
  Domain 9 separation of financial evidence from operational actions).

## FulfillmentOrder posture

- Shopify IDs stored/fetched: Order GID (existing `sale` binding),
  FulfillmentOrder GID(s), Fulfillment GID once created.
- Matching: Odoo picking's sale order → bound Shopify order → that order's
  open FulfillmentOrder(s) → matched line items/quantities via
  `lineItemsByFulfillmentOrder`. An unmatched picking is never fulfilled by
  guess — it blocks for manual review (RA-023).
- Location handling: a FulfillmentOrder is scoped to one Shopify Location;
  Phase 1 targets the single-fulfillment-location case; a mismatch or
  multi-location spread routes to manual review.
- **Clarified (not an open DEC-008 contradiction, not a DEC-008 amendment) —
  mirrors DEC-010 §"Location mapping posture":** this record does **not**
  decide the exact Odoo↔Shopify location-mapping schema and does **not**
  change DEC-008's dependency direction. `shopify_connector_inventory`
  remains the sole owner of the Odoo-location ↔ Shopify-Location *mapping*
  used for inventory push decisions; `shopify_connector_fulfillment` must not
  depend on `shopify_connector_inventory` and must not read that mapping
  table. `shopify_connector_fulfillment` may instead use (a) Shopify
  FulfillmentOrder `assignedLocation` data fetched live from Shopify, and/or
  (b) a minimal Shopify Location *reference* (store, Shopify Location GID,
  name, active/status where available, last-synced/seen metadata if later
  needed — not a mapping) that may live in `shopify_connector_core` as shared
  substrate, consistent with `core` owning cross-cutting reference data while
  domain modules own business mappings (DEC-008). This is an
  **interpretation** of the existing DEC-008 boundary, not an amendment, and
  **not** a decision to create exact fields or models. The exact mechanism by
  which fulfillment confirms a picking's source location against the Shopify
  fulfillment location remains **open for the Master Blueprint**.

## Tracking update posture

- Tracking may be set at fulfillment creation (`fulfillmentCreate`) or
  updated afterward (`fulfillmentTrackingInfoUpdate`); a tracking-only update
  never creates a second fulfillment.
- Single fulfillment creation + tracking update per validated picking is in
  MVP; re-opening/splitting an already-created fulfillment is deferred.

## Customer notification posture

- Default: **no notification** unless explicitly enabled/confirmed by the
  operator (DEC-007, unweakened).
- Phase 1 configuration surface: a global, per-store default at minimum;
  per-order override granularity remains **open** (DEC-007's own fork, not
  resolved here).
- The notification setting is **persisted on the job/log record at enqueue
  time**, not re-read at retry time, so retries preserve the original
  notification decision.
- Every fulfillment log entry records whether notification was requested;
  a write-back that never reached Shopify never sends a notification.

## Location/line matching posture

- Phase 1 targets single-fulfillment-location matching; genuinely
  multi-location fulfillment is deferred (C-FUL-02, DEC-003).
- A picking that cannot be cleanly matched to exactly one FulfillmentOrder's
  open line items blocks for manual review — never auto-guessed.
- `shopify_connector_fulfillment` does not depend on
  `shopify_connector_inventory`'s location-mapping table (DEC-008,
  unweakened); the clarification above (a possible `core`-owned Shopify
  Location reference, distinct from inventory's mapping) is the only place
  this record touches that boundary, and it changes no dependency direction.

## Partial/backorder posture

- Safe Phase 1 posture: fulfill exactly the delivered quantities of one
  validated picking via `lineItemsByFulfillmentOrder`; a partially-delivered
  order with a resulting backorder picking is handled as two independent,
  sequential fulfillment events, which Shopify's FulfillmentOrder model
  natively supports.
- Deferred to Phase 2: true multi-package "Put-in-Pack" shipment splitting
  within one delivery event, and multi-location fulfillment automation
  (C-FUL-02) — an existing accepted deferral (DEC-003), not a new rejection.

## Idempotency/retry posture

- Binding key: `(store, Shopify FulfillmentOrder GID)` (and the Fulfillment
  GID once created).
- **Operation-level idempotency key (conceptual; exact schema open for the
  Master Blueprint):** `(store, Odoo picking ID)` alone is **too narrow** — a
  single picking can be the subject of more than one distinct operation type
  over time (fulfillment creation, a tracking update, a corrected tracking
  update, a manual retry after verification). The operation-level key must
  therefore also carry the **operation type**, the **Shopify target ID**
  where known (FulfillmentOrder GID or Fulfillment GID), and a **payload
  version/hash** (or equivalent intent fingerprint), so that two different
  operations against the same picking are never treated as the same
  operation. Conceptually:
  - `(store, fulfillment_create, picking_id, fulfillment_order_gid, payload_hash)`
  - `(store, tracking_update, picking_id, fulfillment_gid, payload_hash)`
  This distinguishes a tracking update from fulfillment creation, and
  supports a **safe corrected tracking update** (a different payload hash for
  the same picking/Fulfillment) without bypassing the DEC-009
  ambiguous-outcome rule below. This key is distinct from binding identity
  (RA-017); exact field names/types remain open (see "What remains open").
- `fulfillmentCreate` and `fulfillmentTrackingInfoUpdate` are **not** on
  Shopify's 17-mutation `@idempotent` list — any ambiguous-outcome failure
  (timeout/connection loss with unknown result) falls under DEC-009's case 3:
  no blind retry (RA-014); a safe verification read (re-query the order's
  Fulfillments/FulfillmentOrder status) before retry, or
  `blocked_manual_review` if inconclusive.
- Both the operation-level idempotency key (prevents connector-side
  re-processing of the *same* operation, while still distinguishing
  different operation types on the same picking) and the verification-read
  rule (prevents a Shopify-side double fulfillment on ambiguous outcomes) are
  required together — neither alone is sufficient.

## User-facing log/audit requirements

Every fulfillment log entry shows: the related sale order, picking, Shopify
order, Shopify FulfillmentOrder/Fulfillment ID, tracking number/carrier, and
the notification setting (requested/suppressed). Blocked/failed entries carry
a human-readable reason and a suggested next action. No raw stack trace as
the primary UX (extends DEC-009 §8, unchanged).

## What remains open

- Exact Odoo model/field names (fulfillment binding model, log/audit fields).
- Exact `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` mutation
  parameters beyond the directional posture above.
- Exact tracking field source on the Odoo side (tracking-reference field
  name not yet confirmed — see
  [`ar007-ar008-evidence-refresh.md`](../03-architecture/ar007-ar008-evidence-refresh.md)).
- Exact partial-fulfillment rules beyond the general posture (e.g. exact
  backorder-to-picking linkage fields).
- Exact notification UI granularity (global/per-store/per-order) — DEC-007's
  own open fork, not resolved here.
- Exact retry constants (backoff timing, max-attempt counts before
  `blocked_manual_review`).
- Exact schema for the operation-level idempotency key (field names/types
  for operation type, Shopify target ID, and payload version/hash) — the
  **conceptual shape** is set above; the exact schema is a Master Blueprint
  item.
- The exact mechanism by which `shopify_connector_fulfillment` confirms a
  picking's source location against the Shopify fulfillment location (core
  Shopify-Location reference vs. live FulfillmentOrder `assignedLocation`
  fetch, or both) — the **ownership principle** is clarified above (shared
  with AR-007/DEC-010); the **exact confirmation mechanism** is a Master
  Blueprint item.
- The feature-flag/per-store capability-configuration mechanism (already
  routed to UX/operator-flow and Master Blueprint per DEC-008).

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Using the unsupported legacy fulfillment API | FulfillmentOrder-based mutations only, structurally (RA-022) |
| Fulfilling the wrong order/lines/quantities | Matching required via FulfillmentOrder + `lineItemsByFulfillmentOrder`; unmatched pickings block for manual review (RA-023) |
| Surprise customer notification emails | Default off unless explicitly enabled/confirmed (DEC-007), persisted per job at enqueue time |
| Double fulfillment on a retried, ambiguous-outcome write | DEC-009 ambiguous-outcome rule (verification read or manual review) + an operation-type-scoped idempotency key (RA-014, RA-017) |
| A tracking update (or corrected tracking update) mistakenly treated as the same operation as fulfillment creation, or vice versa | Operation-level idempotency key includes operation type + Shopify target ID + payload version/hash, not just the picking ID |
| Duplicate tracking updates from a blind resend | Same ambiguous-outcome rule applied to `fulfillmentTrackingInfoUpdate`, keyed separately from fulfillment creation |
| Silently depending on `shopify_connector_inventory` for location data, contradicting DEC-008 | Clarified: `fulfillment` never depends on `inventory`'s mapping table; a minimal shared Shopify-Location reference may live in `core` instead — exact confirmation mechanism left open for the Master Blueprint, not silently resolved |
| Over-scoping multi-package/multi-location automation into Phase 1 | Explicitly deferred per the existing DEC-003/C-FUL-02 boundary, not attempted here |

## No implementation authorized

**This record does not authorize implementation.** It proposes an
architecture posture for ChatGPT (and Fable's advisory) review only.
Implementation of any fulfillment sync code, Odoo module, model, field,
mutation call, or test remains blocked until: (1) ChatGPT accepts this
record (or a revised version of it), and (2) ChatGPT separately opens the
implementation gate per the Phase 1 research-phase-exit criteria
(`../05-qa/quality-feedback-loop.md` §10) and `CLAUDE.md` §5. Acceptance of
this record alone does not open that gate.

## Review / change control

- **This record proposes AR-008 architecture only.** No API strategy,
  binding-schema-shape, module-boundary, or MVP-scope decision is
  re-litigated (all already decided by DEC-003/004/005/006/007/008).
- **Related:** AR-008 (`../05-qa/architecture-review-log.md`); the companion
  evidence-backed brief
  (`../03-architecture/ar008-fulfillment-architecture-decision-brief.md`);
  the small evidence refresh
  (`../03-architecture/ar007-ar008-evidence-refresh.md`); DEC-006/007/008/009
  (accepted context, unmodified).
- **Changes** to this proposal require ChatGPT review; if accepted, a future
  acceptance-patch note updates this Status field and the linked RA rows
  (RA-022, RA-023), mirroring the DEC-004/005/006/007/008/009 acceptance
  pattern.
