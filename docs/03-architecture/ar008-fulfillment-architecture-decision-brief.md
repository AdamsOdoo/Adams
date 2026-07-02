# AR-008 — Fulfillment Architecture Decision Brief

> Evidence-backed decision brief prepared for **AR-008** (fulfillment
> architecture) during the **AR-007 + AR-008 Decision Preparation** sprint
> (2026-07-02), after DEC-008/DEC-009 acceptance (PR #65 merged into
> `Shopify-connector`). This brief **proposes** a Phase 1 fulfillment
> architecture for ChatGPT/Fable review — it does **not** itself accept a
> decision. The corresponding proposed decision record is
> [`../04-decisions/DEC-011-fulfillment-architecture-strategy.md`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md)
> (`Status: Proposed for ChatGPT review`). **No implementation is authorized
> by this brief.**

## Claim classification (used throughout this brief)

Same convention as
[`ar007-inventory-architecture-decision-brief.md`](./ar007-inventory-architecture-decision-brief.md#claim-classification-used-throughout-this-brief):
`[Accepted decision]`, `[Accepted clarification]`, `[Official fact]`,
`[Official limitation]`, `[Competitor claim]`, `[Inference]`,
`[Recommendation]`, `[Implementation-planning default]`, `[Open question]`.

## Scope

This brief covers **Phase 1 fulfillment architecture only**: the Odoo
fulfillment source and trigger, the Shopify FulfillmentOrder-based target,
fulfillment-creation-vs-tracking-update posture, customer-notification
control, location/line matching, partial/backorder/multi-package posture,
idempotency/retry, user-facing logs, and module boundaries. It does **not**
decide exact Odoo model fields, exact mutation parameters (where not
verified), exact tracking-field source, exact partial-fulfillment rules
beyond the general posture, exact notification UI, or exact retry constants —
all routed to the Master Blueprint / implementation-planning sprint (§10). It
does **not** revisit DEC-003/004/005/006/007/008/009.

## Accepted context this brief must respect

- **[Accepted decision — DEC-003]** Fulfillment and tracking write-back
  (Odoo→Shopify) is in MVP.
- **[Accepted clarification — DEC-007]** The **customer-notification
  default** is: **no notification unless explicitly enabled or confirmed by
  the operator** — grounded in, and consistent with, Shopify's own
  `FulfillmentInput.notifyCustomer` default (`false`) and
  `fulfillmentTrackingInfoUpdate`'s no-notification-if-blank behaviour. This
  brief may decide the exact configuration granularity (global default vs.
  per-store vs. per-order override) but must not change the default itself
  and must preserve operator visibility/control.
- **[Accepted decision — DEC-006]** Bindings are dedicated, store-scoped,
  explicit-GID + explicit-Odoo-record, uniqueness-constrained. Order/
  fulfillment identity gets "separate handling" from product/customer
  identity; DEC-006 does not fix the fulfillment-identity shape — deferred to
  this brief.
- **[Accepted decision — DEC-008]** `shopify_connector_fulfillment` depends
  on `core` + `sale` **only** (plus Odoo's own `stock`/`delivery` apps
  directly) — explicitly **not** on `shopify_connector_inventory`. Binding
  table shape is not decided by DEC-008; this brief places binding
  *responsibility*, not table shape, with `shopify_connector_fulfillment`.
- **[Accepted decision — DEC-009]** "Fulfillment notification confirmation
  missing" is an existing named error class routed to `blocked_manual_review`.
  The **ambiguous-outcome rule** applies to any write outside Shopify's
  `@idempotent` surface whose outcome is unknown after dispatch.
- **[Accepted decision — DEC-003, non-MVP boundaries]** Multi-package /
  multi-location fulfillment (C-FUL-02) is **deferred** to a later phase —
  not rejected, requires C-FUL-01 shipped + AR-008 design resolved first.

## Official facts (grounded in `../01-research/shopify-official-api-notes.md` and the small evidence refresh)

1. **[Official fact]** A **FulfillmentOrder** groups items to fulfill from
   one location; a **Fulfillment** is a shipment with tracking. The **legacy
   Order/Fulfillment workflow is unsupported as of API version 2022-07**, and
   all apps should use the FulfillmentOrder object by 2023-07. Sources:
   `shopify.dev/docs/apps/build/orders-fulfillment/fulfillment-service-apps`,
   `.../migrate-to-fulfillment-orders`, access date 2026-06-30.
2. **[Official fact]** `fulfillmentCreate` creates a fulfillment for
   FulfillmentOrders of the **same order and location** (fulfills all items
   if none specified; supports `lineItemsByFulfillmentOrder` for partial
   quantities) and can carry tracking at creation time. Source:
   `shopify.dev/docs/api/admin-graphql/latest/mutations/fulfillmentcreate`.
3. **[Official fact]** `fulfillmentTrackingInfoUpdate` updates carrier/
   numbers/URLs after creation; a supported carrier name auto-generates a
   tracking URL. Tracking can be set at creation or later. Source:
   `.../mutations/fulfillmenttrackinginfoupdate`.
4. **[Official fact]** `FulfillmentInput.notifyCustomer` — "Whether the
   customer is notified. If `true`, then a notification is sent when the
   fulfillment is created." — **defaults to `false`**. Source:
   `shopify.dev/docs/api/admin-graphql/latest/input-objects/FulfillmentInput`,
   access date 2026-07-02 (already verified for DEC-007, propagated here, no
   new fetch performed).
5. **[Official fact]** `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` —
   "If this field is left blank, then notifications won't be sent to the
   customer when the fulfillment is updated." Same source family, access
   date 2026-07-02.
6. **[Official limitation]** `fulfillmentCreate` and
   `fulfillmentTrackingInfoUpdate` are **not** on Shopify's 17-mutation
   `@idempotent` list (that list is "inventory/location mutations +
   `refundCreate`," per the AR-006 brief). **This means fulfillment-creation
   and tracking-update writes fall under DEC-009's ambiguous-outcome case 3
   (non-idempotent, unknown-outcome-after-dispatch), not the safer
   same-key-retry case 2** — see §7.
7. **[Official fact]** A fulfillment service maps to a Location and handles
   its assigned fulfillment orders; it accepts/rejects fulfillment requests
   and receives notifications at a callback URL; writes need the assigned/
   merchant-managed/third-party fulfillment-order scopes (C-FUL-03). Source:
   `shopify.dev/docs/apps/build/orders-fulfillment/fulfillment-service-apps/build-for-fulfillment-services`.
8. **[Official fact]** Odoo 19.0 organizes delivery into named workflows
   (one-step/two-step/three-step); confirming a sales order automatically
   generates a delivery order (`stock.picking`), reachable via the order's
   "Delivery" smart button; the three-step flow separates pick → pack → ship.
   A dedicated **Third-party shipping carriers** official doc page exists.
   Sources in `ar007-ar008-evidence-refresh.md`, access date 2026-07-02.
9. **[Open question] — must be verified before implementation.** The exact
   tracking-reference/URL field name(s) on `stock.picking`/`delivery.carrier`,
   and the exact backorder-wizard behaviour/model for **delivery** orders
   specifically (as opposed to receipts), are **not** confirmed verbatim from
   an official Odoo page this sprint — see `ar007-ar008-evidence-refresh.md`.

## 1. Odoo fulfillment source

- **[Recommendation]** The trigger is **validated `stock.picking`** (delivery
  order) — specifically, the **Validate** action on an outgoing delivery,
  which is the point at which Odoo has confirmed physical shipment of a
  known set of quantities (fact #8).
- **Carrier / tracking reference / tracking URL [Recommendation, subject to
  open question #9]:** the connector reads the Odoo delivery's carrier and
  tracking-reference fields (exact field names to be confirmed — gap #9) and
  passes them to `fulfillmentTrackingInfoUpdate`/`fulfillmentCreate`'s
  tracking input; if Shopify recognizes the carrier name it auto-generates a
  tracking URL (fact #3), so the connector does not need to construct
  tracking URLs itself for supported carriers.
- **Backorder / partial delivery posture [Recommendation]:** each validated
  `stock.picking` — including a picking created as a backorder split from an
  earlier partial delivery — is its **own fulfillment trigger event**, tied
  to its own quantities. The connector does not attempt to look ahead or
  aggregate a not-yet-validated backorder into the same Shopify fulfillment
  as its parent picking. This keeps the connector's fulfillment-creation
  logic simple (one validated picking → one Shopify `fulfillmentCreate` call
  with that picking's quantities) and avoids guessing whether/when a
  backorder will ultimately be delivered. Exact backorder-to-picking linkage
  fields are an **[Open question]** (gap #9).
- **Invoice/payment state relevance [Recommendation]:** invoice/payment state
  is **not** a fulfillment trigger condition — per the already-accepted
  DEC-003 Domain 9 rule keeping financial evidence separate from operational
  actions ("MVP preserves financial evidence and order actionability; it
  does not automate accounting"), fulfillment write-back is driven by
  physical delivery validation, independent of invoicing/payment status.

## 2. Shopify fulfillment target

- **[Accepted decision — Tier-1, fact #1]** FulfillmentOrder-based flow only;
  legacy Order/Fulfillment endpoints are unsupported and must not be used
  (see **RA-022** below).
- **Shopify IDs to store or fetch [Recommendation]:** the Shopify **Order
  GID** (already bound by `shopify_connector_sale` per DEC-008), the
  **FulfillmentOrder GID(s)** for that order (fetched from Shopify, since an
  order can have more than one FulfillmentOrder — one per location/routing
  rule), and the **Fulfillment GID** once created. These form the
  fulfillment-identity shape DEC-006 deferred to this brief (§9's binding
  responsibility).
- **Matching Shopify order / fulfillment order / line items / quantities
  [Recommendation]:** the connector matches the Odoo `stock.picking`'s sale
  order to its bound Shopify order (via the existing `sale` binding), fetches
  that order's open FulfillmentOrder(s), and matches the picking's
  delivered line quantities to the corresponding FulfillmentOrder line
  items — using `fulfillmentCreate`'s `lineItemsByFulfillmentOrder` (fact
  #2) to fulfill exactly the delivered quantities, not a blind "fulfill
  everything on the order." A picking that cannot be matched to a specific
  FulfillmentOrder/line-item set is **not** fulfilled — it is blocked for
  manual review (see **RA-023** below).
- **Handling Shopify location [Clarified — not an open DEC-008
  contradiction, not a DEC-008 amendment — mirrors AR-007 §4]:** a
  FulfillmentOrder is scoped to one Shopify Location (fact #1/#7). The
  connector must confirm the picking's source Odoo location corresponds to
  the FulfillmentOrder's assigned Shopify Location before fulfilling. This
  brief does **not** decide the exact Odoo↔Shopify location-mapping schema
  and does **not** change DEC-008's dependency direction: per DEC-008,
  `shopify_connector_fulfillment` must not depend on
  `shopify_connector_inventory`, and `shopify_connector_inventory` **remains
  the sole owner** of the Odoo-warehouse ↔ Shopify-Location *mapping* used
  for inventory push decisions (AR-007 brief §9) — `fulfillment` must not
  read that mapping table. `shopify_connector_fulfillment` may instead
  resolve location identity from (a) Shopify FulfillmentOrder
  `assignedLocation` data **fetched live from Shopify** (each FulfillmentOrder
  already carries its own assigned location, so no local Odoo-side mapping is
  strictly required to *select* the right FulfillmentOrder), and/or (b) a
  **minimal Shopify Location *reference*** (not a mapping) that may live in
  `shopify_connector_core` — conceptually the store, Shopify Location GID,
  name, active/status where available, and last-synced/seen metadata if
  later needed. This is **not** a decision to create exact fields or models;
  it is an **interpretation** consistent with `core` owning cross-cutting
  reference data while domain modules own business mappings (DEC-008), not
  an amendment to it. In Phase 1's single-location-fulfillment posture (§6),
  fulfillment only needs to confirm the picking's source location is the
  one, unambiguous, expected fulfillment location for that store; a mismatch
  or a genuinely multi-location order is routed to manual review (§5), not
  guessed. The **exact confirmation mechanism** remains **open for the
  Master Blueprint** — the same clarification appears in the AR-007 brief §4
  and DEC-010/DEC-011, as one shared item, not two independent ones.
- **Avoiding legacy fulfillment APIs [Accepted decision]:** enforced
  structurally by using only FulfillmentOrder-based mutations (fact #1) — see
  **RA-022**.

## 3. Fulfillment creation vs. tracking update

- **[Recommendation]** The connector **creates** the Shopify fulfillment at
  the point of the Odoo delivery-validation trigger (§1), using
  `fulfillmentCreate` with tracking info included where already known at
  that point (fact #2 — tracking can be set at creation).
- **[Recommendation]** The connector **updates tracking** via
  `fulfillmentTrackingInfoUpdate` (fact #3) when tracking information becomes
  available *after* the fulfillment was already created (e.g. a carrier
  tracking number assigned post-shipment) — tracking-only updates never
  create a second fulfillment.
- **Tracking can be updated after creation [Official fact, #3]:** confirmed;
  this is the basis for keeping creation and tracking-update as two distinct,
  idempotent-per-purpose operations rather than one combined action that must
  always carry final tracking data.
- **MVP vs. deferred [Recommendation]:** single fulfillment creation +
  tracking update per validated picking is **in MVP** (C-FUL-01); re-opening
  or splitting an already-created fulfillment, and multi-package "Put-in-Pack"
  style grouping, are **deferred** (C-FUL-02, already an accepted non-MVP
  boundary — DEC-003).

## 4. Customer notification control

- **[Accepted clarification — DEC-007]** Default: **no notification** unless
  explicitly enabled/confirmed by the operator (facts #4, #5).
- **Where the operator sees the setting [Recommendation, Phase 1 scope]:** a
  **global, per-store default** configuration surface (consistent with
  "essential mappings only," no custom transforms, per setup-ux-principles.md)
  is the Phase 1 minimum; a **per-order override** is a candidate but its
  exact granularity is explicitly left **[Open question]** by DEC-007 itself
  ("global default vs. per-store vs. per-order override") — this brief does
  not resolve that fork, consistent with the instruction to respect DEC-007
  as written.
- **How retry preserves the notification decision [Recommendation]:** the
  notification setting used for a given fulfillment job is **persisted on the
  job/log record at enqueue time**, not re-read from the current global
  default at retry time — so a retry of a `blocked_manual_review` or
  `failed_retryable` fulfillment job notifies (or does not) exactly as
  originally intended, even if the global default is changed in the
  meantime. This mirrors DEC-009's "manual retry safety (same code path as
  automatic retry)" idempotency layer.
- **How logs/audit show notification status [Accepted decision — DEC-007 /
  US-E6-04]:** every fulfillment/tracking write-back records **whether a
  customer notification was requested**, visible on the write-back's log
  entry; a failed write-back that never reached Shopify never sends a
  notification (US-E6-04 acceptance notes).

## 5. Location and line matching

- **One Shopify fulfillment location vs. multiple [Recommendation]:** Phase 1
  targets the **single-fulfillment-location** case per order/picking as the
  safe default (consistent with DEC-003's deferral of true multi-location
  fulfillment automation to C-FUL-02); a picking whose corresponding
  FulfillmentOrder set spans more than one Shopify Location is treated as an
  **ambiguous/ multi-location case** and routed to manual review rather than
  auto-split in Phase 1.
- **Mismatch between Odoo picking and Shopify fulfillment order
  [Recommendation]:** if the picking's location, order, or delivered
  quantities cannot be cleanly matched to exactly one FulfillmentOrder's
  open line items, the job blocks for manual review — it does **not** guess
  which FulfillmentOrder to fulfill or fulfill a superset/subset of the
  actual delivered lines.
- **Blocking manual review for ambiguous cases [Accepted decision —
  DEC-009]:** yes — ambiguous match and inventory/fulfillment-location
  mismatches route to `blocked_manual_review`, consistent with the existing
  taxonomy (§7 below reuses "ambiguous match" and adds no new class beyond
  what DEC-009 already names, since "fulfillment notification confirmation
  missing" and general "ambiguous match"/"binding conflict" already cover
  these cases).
- **Avoiding a forbidden dependency on `shopify_connector_inventory`
  [Clarified, not an open DEC-008 contradiction]:** see §2's location-
  handling paragraph above — restated here as the specific §5 concern: Phase
  1 fulfillment does **not** read `shopify_connector_inventory`'s
  Odoo-warehouse-to-Shopify-Location mapping table under any circumstance;
  it either uses a `core`-owned minimal Shopify-Location *reference* or
  resolves location identity directly against Shopify's own FulfillmentOrder
  `assignedLocation` data. Genuinely multi-location orders remain deferred
  (C-FUL-02) regardless of which option is eventually chosen; the exact
  confirmation mechanism is a Master Blueprint item, not decided here.

## 6. Partial / backorder / multi-package

- **Safe Phase 1 posture [Recommendation]:** fulfill **exactly the delivered
  quantities** of a single validated picking via `fulfillmentCreate`'s
  `lineItemsByFulfillmentOrder` (fact #2), which natively supports partial
  line quantities without requiring "multi-package" grouping logic. A
  partially-delivered order (with a resulting Odoo backorder picking) is
  handled as **two independent fulfillment events over time** — one per
  validated picking (§1) — which Shopify's FulfillmentOrder model already
  supports (an order's FulfillmentOrder can be fulfilled in more than one
  `fulfillmentCreate` call over time as quantities become available).
- **Which cases can be supported safely [Recommendation]:** single-location,
  single-or-sequential-partial delivery against one FulfillmentOrder.
- **Which cases must be blocked/deferred/manual review [Recommendation]:**
  true multi-package "Put-in-Pack" style shipment splitting within a single
  delivery event, and multi-location fulfillment automation (auto-routing
  across several FulfillmentOrders in one connector action) — both remain
  **Phase 2** per the already-accepted DEC-003/non-mvp-and-later-phases.md
  deferral of C-FUL-02 ("MVP ships single-package tracking write-back;
  split shipments add complexity beyond the common case... what must be true
  before including: C-FUL-01 shipped; AR-008 design resolved").
  **This is a deferral, not a new architecture rejection** — no new RA row
  is added for it (see "Rejected or weakened alternatives" below).
- **What remains Phase 2:** C-FUL-02 in full (multi-package/multi-location
  fulfillment automation).

## 7. Idempotency and retry

- **Binding key [Recommendation]:** the fulfillment binding keys on
  **`(store, Shopify FulfillmentOrder GID)`** (or, once created, the
  Fulfillment GID) tied to the originating **Odoo `stock.picking` ID**.
- **Operation-level idempotency key [Recommendation, conceptual — exact
  schema open]:** `(store, Odoo picking ID)` alone is **too narrow**, because
  a single picking can be the subject of more than one distinct operation
  type over time — fulfillment creation, a tracking update, a corrected
  tracking update, and a manual retry after verification are all different
  operations against the same picking. The operation-level key must
  therefore also carry the **operation type**, the **Shopify target ID**
  where known (FulfillmentOrder GID or Fulfillment GID), and a **payload
  version/hash** (or equivalent intent fingerprint). Conceptually:
  - `(store, fulfillment_create, picking_id, fulfillment_order_gid, payload_hash)`
  - `(store, tracking_update, picking_id, fulfillment_gid, payload_hash)`
  This prevents a tracking update from being treated as the same operation
  as fulfillment creation, and supports a **safe corrected tracking update**
  (a different payload hash for the same picking/Fulfillment) without
  bypassing the ambiguous-outcome rule below. This key is distinct from
  binding identity, consistent with DEC-009's point that the binding
  prevents *identity* duplication but not *operation* duplication (RA-017).
  Exact field names/types remain open for the Master Blueprint (§10).
- **Handling ambiguous outcome after fulfillment mutation [Accepted decision
  — DEC-009, applied here per fact #6]:** because `fulfillmentCreate` and
  `fulfillmentTrackingInfoUpdate` are **not** on the 17-mutation
  `@idempotent` list, a timeout/connection-loss with unknown outcome after
  dispatch is **DEC-009's case 3 (ambiguous, non-idempotent)** — no blind
  retry. The job must either perform a **safe verification read** (re-fetch
  the order's fulfillments/FulfillmentOrder status and compare against the
  intended write) before any re-attempt, or route to `blocked_manual_review`
  if the outcome cannot be safely verified this way.
- **Verification read before retry [Recommendation]:** a verification read
  for fulfillment means: re-query the Shopify order's Fulfillment(s) for the
  target FulfillmentOrder and check whether a Fulfillment matching the
  intended line items/quantities already exists before re-issuing
  `fulfillmentCreate`. If verification is inconclusive, `blocked_manual_review`.
- **Preventing double fulfillment [Recommendation]:** the combination of (a)
  the operation-type-scoped idempotency key (e.g.
  `(store, fulfillment_create, picking_id, fulfillment_order_gid,
  payload_hash)`) preventing the *connector* from re-processing the same
  fulfillment-creation operation twice, and (b) the verification-read-
  before-retry rule preventing a *Shopify-side* double fulfillment on an
  ambiguous outcome, together satisfy the "no double fulfillment"
  requirement — neither alone is sufficient (RA-017).
- **Preventing duplicate tracking updates [Recommendation]:** tracking
  updates are naturally closer to idempotent in effect (repeating the same
  carrier/number is a no-op from the customer's perspective), but since
  `fulfillmentTrackingInfoUpdate` is still outside the `@idempotent` surface
  (fact #6), the same ambiguous-outcome rule applies on a timeout: verify
  the current tracking info before re-sending, or block for manual review,
  rather than assuming a resend is harmless. Because the operation-level key
  is scoped by operation type (`tracking_update`, distinct from
  `fulfillment_create`) and by payload hash, a **corrected** tracking update
  (different carrier/number, hence a different payload hash) is correctly
  treated as a new operation, not a duplicate of the prior tracking update or
  of the original fulfillment creation.

## 8. User-facing fulfillment logs

- **[Recommendation, extends DEC-009 §8]** Every fulfillment log entry shows:
  the related **sale order**, **picking**, **Shopify order**, **Shopify
  FulfillmentOrder/Fulfillment ID**, **tracking number/carrier**, and the
  **notification setting** (requested / suppressed) — per US-E6-04's explicit
  requirement that the notification flag be visible on the log entry.
- **Suggested fix when blocked [Accepted decision — DEC-009 / product-vision.md]:**
  every blocked/failed entry carries a human-readable reason and a suggested
  next action (e.g. "map this delivery's location to a Shopify fulfillment
  location" or "confirm which FulfillmentOrder line items this delivery
  covers").
- **No raw stack trace as primary UX [Accepted decision — RA-016]:** technical
  detail remains available on demand, not as the primary error view.

## 9. Boundaries

- **`shopify_connector_fulfillment` owns [Recommendation, consistent with
  DEC-008's Phase 1 addon table]:** fulfillment/tracking write-back logic;
  fulfillment binding responsibility (FulfillmentOrder/Fulfillment identity
  tied to the order binding, per §2); the DEC-007 customer-notification
  guard implementation and its persisted-at-enqueue-time setting (§4).
- **`shopify_connector_sale` owns [Accepted decision — DEC-008]:** order
  import and order binding responsibility; fulfillment matches against the
  order binding `sale` already owns — fulfillment does not duplicate order
  identity, only extends it with FulfillmentOrder/Fulfillment identity.
- **`shopify_connector_core` owns [Accepted decision — DEC-008]:** transport,
  queue, webhook receiver, the binding abstraction/shared contract, the
  error-class registry (including "fulfillment notification confirmation
  missing"), and — per the clarification in §2/§5 — is where a minimal
  shared Shopify-Location *reference* (not a mapping) may live so
  `fulfillment` never needs to depend on `inventory`; exact fields/models
  remain open for the Master Blueprint.
- **Link-module need discovered? [Clarified — not needed]:** no. The
  location-reference-sharing question in §2/§5 is the shape of problem
  DEC-008 already anticipated ("a possible future glue module letting
  `shopify_connector_fulfillment` reuse `shopify_connector_inventory`'s
  location mapping"), but this brief resolves it **without** a link module
  and **without** either domain depending on the other: `core` already owns
  cross-cutting reference data under DEC-008, so a minimal Shopify-Location
  reference fits there as an **interpretation** of the existing boundary, not
  a new module and not a DEC-008 amendment.
- **DEC-008 not changed:** the dependency shape (`fulfillment` → `core` +
  `sale`, not `inventory`) is preserved exactly as DEC-008 states.
  `shopify_connector_inventory` still owns the Odoo-location ↔
  Shopify-Location *mapping* for inventory push decisions; only a minimal
  Shopify-Location *reference* is clarified as fitting inside `core`'s
  existing scope. The exact confirmation mechanism fulfillment uses remains
  open for the Master Blueprint — this is a clarification of ownership, not
  an amendment to DEC-008.

## 10. What remains open for Master Blueprint / implementation planning

- Exact Odoo model/field names (fulfillment binding model, log/audit fields).
- Exact fulfillment mutation parameters beyond the directional posture in
  §2–3 (e.g. exact `fulfillmentCreate` input shape used).
- Exact tracking field source on the Odoo side (gap #9 — tracking-reference
  field name(s) not yet confirmed).
- Exact partial-fulfillment rules beyond the general posture in §6 (e.g.
  exact backorder-to-picking linkage).
- Exact notification UI (global-default vs. per-store vs. per-order
  granularity — DEC-007's own open question, not resolved here).
- Exact retry constants (backoff timing, max-attempt counts before
  `blocked_manual_review`).
- Exact schema for the operation-level idempotency key (field names/types
  for operation type, Shopify target ID, and payload version/hash — see §7's
  conceptual shape).
- The exact mechanism by which fulfillment confirms a picking's source
  location against the Shopify fulfillment location (§2, §5, §9) — the
  **ownership principle** is clarified (shared with AR-007/DEC-010); the
  **exact confirmation mechanism and any exact fields/models** remain a
  Master Blueprint item, not decided here.
- Verification of the exact backorder-wizard behaviour for delivery orders
  and the exact Odoo tracking-reference field (`ar007-ar008-evidence-refresh.md`).

## Rejected or weakened alternatives

- **Fulfillment write-back with a hidden/default-on customer notification.**
  Already a **binding final rejected approach** — see **RA-009**
  (`rejected-approaches-log.md`, tied to the accepted DEC-007). Not re-logged.
- **Blind retry of fulfillment creation after ambiguous timeout.** Already
  covered by the **binding final rejected approach RA-014** (retry-everything
  automatically regardless of error class) and directly enforced here by the
  DEC-009 ambiguous-outcome rule (§7). Not re-logged, per this sprint's
  explicit instruction that RA-014 already covers it.
- **Legacy fulfillment API flow instead of FulfillmentOrder-based flow.**
  **Rejected** — see **RA-022** (new, PROPOSED this sprint; formalizes
  avoid-list A-FUL-1 now that AR-008 is under formal review).
- **Fulfillment creation by order ID only, without fulfillment-order/line/
  quantity/location matching (including treating every validated Odoo
  picking as automatically safe to fulfill without that matching).**
  **Rejected** — see **RA-023** (new, PROPOSED this sprint; covers both the
  "order-ID-only" pattern and the "every validated picking is automatically
  safe" pattern as the same underlying defect).
- **Multi-package/multi-location fulfillment automation in Phase 1 without
  explicit matching and review gates.** **Not a new rejected approach** —
  already an accepted, explicit **deferral** (not a rejection) via DEC-003 /
  `non-mvp-and-later-phases.md` C-FUL-02 ("deferred... not rejected, not
  technical debt"). No new RA row added, consistent with that existing
  deferred/not-rejected framing.

## What this brief does not decide

- Does not accept DEC-011.
- Does not decide exact model fields, database constraints, or Python/ORM
  design.
- Does not create Odoo modules, code, or tests.
- Does not decide the exact notification-configuration UI granularity
  (DEC-007's own open fork).
- Does not authorize implementation.
- Does not alter DEC-003/004/005/006/007/008/009.
- Does not change DEC-008's module boundaries — the shared Shopify-Location
  reference is clarified as an interpretation fitting within `core`'s
  existing scope, not an amendment; the exact confirmation mechanism and any
  exact fields/models remain open for the Master Blueprint.
