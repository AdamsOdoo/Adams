# Domain E2E Test Matrix

> End-to-end test-planning matrix for the connector's domain sync flows,
> part of the [MVP QA and Test Strategy](./mvp-qa-test-strategy.md)
> package. Baseline: `Shopify-connector` at
> `f74aaf204745ce0087733870fe56bdda74bfa79a`. **Docs-only. No
> implementation. No gate opened.** None of the domains below have an open
> implementation gate today — this matrix plans the tests their future
> implementation tasks must satisfy, sourced from the accepted
> [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
> and [`DEC-015`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)
> blueprints and their underlying
> [`master-blueprint-product-customer-sale.md`](../03-architecture/master-blueprint-product-customer-sale.md)
> and
> [`master-blueprint-inventory-fulfillment.md`](../03-architecture/master-blueprint-inventory-fulfillment.md)
> architecture documents. This document does not resolve any open MBQ row
> and does not modify
> [`master-blueprint-open-questions.md`](../03-architecture/master-blueprint-open-questions.md).

## Status

**Proposed for ChatGPT review. Docs-only. No implementation. No gate
opened. Does not create tests. Does not resolve any MBQ row.**

## Fixed vocabulary used throughout this matrix

Reused verbatim from the accepted register (not re-decided here):

- **Job sources (7):** `webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation`, `setup_readiness_check`, `export_preview_dry_run`
  (DEC-009) + `odoo_event` with a required `trigger_origin`
  sub-classification (DEC-019).
- **Job states (10):** `draft`, `queued`, `running` (non-terminal);
  `succeeded`, `failed_final`, `skipped`, `cancelled` (terminal);
  `retry_waiting`, `failed_retryable`, `blocked_manual_review` (recovery
  loop).
- **Error classes (16, fixed, no 17th):** Shopify throttling/rate-limit;
  Shopify temporary/server/network; Shopify permission/scope/auth;
  Shopify userErrors/validation; Odoo validation/configuration; mapping
  missing; ambiguous match; binding conflict; duplicate risk;
  destructive-write guard blocked; inventory location missing;
  fulfillment notification confirmation missing; financial total
  mismatch; data shape/schema mismatch; concurrency/race conflict;
  unknown/system error.
- **Manual-review sub-reasons (6, the `blocked_manual_review` confirmation-
  required classes):** ambiguous match; binding conflict; duplicate risk;
  destructive-write guard blocked; inventory location missing;
  fulfillment notification confirmation missing.
- **Retry UI cases (4):** auto-retry in progress; safe to retry now; fix
  first; verify before retry.

---

## 1. Product import (Shopify → Odoo)

- **Happy path.** Trigger via webhook (enqueue-only + follow-up
  authoritative read), `scheduled_sync`, `manual_sync`, or
  `reconciliation` — never webhook-only. Matching runs binding-first, then
  SKU/internal reference, then barcode; a confident match links to the
  existing product/variant, a confident no-match candidate is eligible to
  create a new product template + variant(s), gated by the MBQ-59
  eligibility (setup complete; domain enabled; source-strategy permits
  import creation) and match-quality (unambiguous match/no-match; no
  ambiguous-match/binding-conflict/duplicate-risk/destructive-write-guard
  trigger) two-tier gate. Job reaches `succeeded`.
- **Duplicate/idempotency path.** Re-processing the same Shopify product
  (repeated webhook, reconciliation pass) matches the existing
  product-template/product-variant binding (independent Shopify GIDs held
  as separate bindings) and updates rather than re-creates. A binding
  whose Shopify counterpart was deleted/recreated is marked stale/routed
  to review, never silently re-created or hijacked.
- **Missing-dependency path.** Not a documented import-side scenario in
  the current architecture (missing-dependency handling is primarily an
  **export**-path concern — a stale export-target binding maps to
  `mapping missing` → `failed_retryable`). A future test suite should
  confirm this asymmetry explicitly rather than assume an import-side
  analog exists.
- **Mapping-conflict path.** More than one plausible SKU/barcode candidate
  → `ambiguous match` → `blocked_manual_review`; a stale/recreated Shopify
  product ID or a create that would likely duplicate an existing product →
  `binding conflict`/`duplicate risk` → `blocked_manual_review`.
- **API-failure path.** Shopify throttling/rate-limit → auto-retry with
  backoff; Shopify temporary/server/network → auto-retry (reads/
  `@idempotent`) or the ambiguous-outcome rule otherwise; missing
  product-write scope → manual fix then retry; invalid SKU/option/price
  payload (userErrors/validation) → manual fix then retry.
- **Retry path.** Exactly one of the four accepted retry UI cases per
  error class — never a blanket retry button, never a never-retry
  deadlock.
- **Manual-review path.** `ambiguous match`, `binding conflict`,
  `duplicate risk`, and `destructive-write guard blocked` (the last for a
  `productSet`/bulk-variant write that would delete/omit data without a
  rendered, confirmed preview) route to `blocked_manual_review` with the
  specific sub-reason; `mapping missing` and `data shape/schema mismatch`
  route to `failed_retryable` instead ("manual fix then retry"), **not**
  to the manual-review queue.
- **Rollback/recovery path.** No explicit rollback mechanic beyond the
  generic stale-binding handling and the job-state recovery loop — a
  future test suite should confirm this is a deliberate architecture
  choice (idempotent re-processing substitutes for rollback) rather than
  an undocumented gap.
- **Audit/log proof.** Create/bind actions log full before/after detail
  via the job/log audit trail plus binding audit fields (matched-by,
  matched-at, source strategy, match key used, status); retrospective
  sync-center/dashboard visibility is audit/log visibility only, **never**
  a substitute for the required blocking preview on interactive/batch
  operations.
- **MVP acceptance criteria.** No blind create (gate/preview enforced on
  every automated create/bind path); match-key priority holds; the six
  manual-review sub-reasons route correctly and exclusively; job types
  `product_import`, `product_export_create`, `product_export_update`,
  `product_export_preview` are exercised distinctly.

## 2. Variant import

- **Happy path.** Options/option values map to Odoo attribute/attribute
  values, imported together with the variant; scope bounded to the
  current Shopify product/variant model (up to 2,048 variants per
  product), no legacy variant model support. Variants are created
  together with the template on a confident no-match.
- **Duplicate/idempotency path.** A separate product-variant binding model
  keyed to an independent Shopify GID from its parent template — a
  template binding never stands in for its variants' bindings.
- **Missing-dependency path.** No variant-specific missing-dependency
  scenario is documented (e.g. a variant referencing an unresolved
  option) — not asserted as impossible, just not yet specified; flagged
  for the future product-domain task spec to confirm or define.
- **Mapping-conflict path.** Same ambiguous-match/binding-conflict/
  duplicate-risk classes as product; the variant-specific destructive-
  write risk is real and documented as an **official fact**: `productSet`
  reconciles list fields by "creating, updating, and deleting entries not
  included in the mutation's input," explicitly naming `variants` as a
  common example — a `productSet` write omitting a variant **deletes it**.
  This is the destructive-write-guard's primary variant-domain trigger.
- **API-failure path.** No separate variant row in the error-class
  table — variant mutations fall under the product-instance error-class
  mapping (e.g. "invalid SKU/option/price payload" for userErrors/
  validation).
- **Retry path.** Same four-case retry taxonomy as product; no
  variant-specific retry class exists.
- **Manual-review path.** `destructive-write guard blocked` names
  variants explicitly: a `productSet`/bulk-variant write that would
  delete/omit data without a rendered, confirmed preview is blocked
  pending confirmation.
- **Rollback/recovery path.** No variant-specific rollback mechanic beyond
  the shared stale/binding handling.
- **Audit/log proof.** Same binding audit fields as product bindings, by
  extension of the shared binding contract.
- **MVP acceptance criteria.** The export/update diff must be rendered at
  the **variant level**, not only the template level, so an operator sees
  exactly which variants would be deleted/updated/created before
  confirming.

## 3. Customer import / matching

- **Happy path.** Import/matching only (Shopify → Odoo); never pushes
  partner data back to Shopify. Most commonly arrives embedded in order
  import, but may run standalone. Matching priority: existing binding →
  email (the **sole** automatic match key, MBQ-31) → manual review; phone
  and name are advisory hints only, **never** automatic. Same MBQ-59
  two-tier gate as product, substituting the customer domain.
- **Duplicate/idempotency path.** Customer binding (Shopify Customer ↔
  Odoo `res.partner`) owned directly by the sale domain, not routed
  through the product domain. An interactive/batch matching session
  always shows a blocking "will create N, link M, N ambiguous" preview
  before any create/bind action.
- **Missing-dependency path — three distinct paths (§C.6):**
  1. Genuinely no PII available → the single, deliberately-created,
     clearly-flagged fallback partner per store is used; the order
     imports normally, visibly marked ("no customer data available —
     fallback used"); **never** used for an ordinary matching failure.
  2. PII available, confident automatic match or confident no-match
     creation candidate → creates/matches via the ordinary MBQ-59-gated
     "customer import" capability — this is **not** a fallback or an
     error state.
  3. PII available, ambiguous (multiple plausible candidates) → only the
     customer-**assignment** step is held (`ambiguous match`,
     `blocked_manual_review`) — this does **not** block the rest of order
     import, because an ambiguous customer does not affect the order's
     total-check math the way an unmatched product line does.
- **Mapping-conflict path.** `ambiguous match` = multiple email/customer-
  key candidates; `binding conflict` = stale/recreated Shopify customer
  ID; `duplicate risk` = a create that would likely duplicate an existing
  partner; `data shape/schema mismatch` = malformed customer payload
  (e.g. missing email on a non-no-PII store — a data-quality signal, not
  a no-PII case).
- **API-failure path.** Missing protected-customer-data approval →
  manual fix then retry; invalid partner-field payload → manual fix then
  retry; Odoo-side partner validation failure → manual fix then retry;
  "mapping missing" is not applicable to the customer instance (no
  export path exists for customers in Phase 1).
- **Retry path.** Same four-case taxonomy; no destructive customer write
  exists in Phase 1 (import-only domain).
- **Manual-review path.** `ambiguous match`, `binding conflict`,
  `duplicate risk`, `data shape/schema mismatch` — job type
  `customer_match_review` is the Reviewer-role resolution action.
- **Rollback/recovery path.** Isolation only: "a failed customer import is
  isolated and reason-coded; the linked order still reconciles via
  matching" — one bad customer record never blocks order import as a
  whole.
- **Audit/log proof.** Fallback-partner visible marker on the order/
  binding record; generic binding audit fields (matched-by/at/strategy/
  key/status) apply by extension of the shared binding contract.
- **MVP acceptance criteria.** Email is provably the sole automatic match
  key; the fallback partner is provably used only for genuine no-PII
  orders; no customer export path exists; PII minimization holds (only
  fields the accepted matching/order-representation requirements actually
  need are imported).

## 4. Order import

- **Happy path.** Layered trigger (webhook `ORDERS_CREATE`/`ORDERS_UPDATED`,
  scheduled, manual, or reconciliation — never webhook-only). Sequencing:
  (1) product binding must exist before order-line creation, enforced by
  the whole-order-hold rule; (2) customer binding/import resolves before
  order finalization; (3) the total-check guard is evaluated **before**
  the order is marked complete, not as a post-hoc audit. Order line items
  map to `sale.order.line` records carrying the matched product/variant
  reference, quantity, unit price, and tax/discount evidence contribution.
- **Duplicate/idempotency path.** The order binding (Shopify Order ↔ Odoo
  `sale.order`) is the **sole idempotency anchor** for order creation — a
  re-processed webhook or reconciliation pass matches the existing binding
  and updates, never re-creates.
- **Missing-dependency path.**
  - **Unmatched product line** → the **whole order import is held**
    (never a silent placeholder product, never a silently dropped line):
    error class `mapping missing`, state `failed_retryable` (not
    `blocked_manual_review`), naming the specific unmatched SKU/product,
    until the product is bound, at which point the job returns to
    `queued` and resumes/retries through the normal job path. Rationale:
    any partial order cannot pass the mandatory total-check guard either.
  - **Unmatched customer** → per the three-path rule in §3 above; only an
    ambiguous customer holds (and only the assignment step, not the whole
    order).
- **Mapping-conflict path.** Duplicate order risk → `blocked_manual_review`;
  binding conflict (stale/recreated Shopify order ID) →
  `blocked_manual_review`; unsupported data shape → `failed_retryable`;
  missing gateway → journal mapping → `failed_retryable`.
- **API-failure path.** Missing required order read scope or protected-
  customer-data approval → manual fix then retry; invalid order-line
  payload → manual fix then retry; Odoo-side sale-order validation
  failure → manual fix then retry; **financial total mismatch → its own
  "conservative, never silent — always manual" posture**, distinct from
  every other order-domain retry row.
- **Retry path.** Four-case taxonomy applies; a held order (whole-order
  hold or total mismatch) resumes via the "fix first" case — never an
  automatic timer-driven re-queue for these two classes.
- **Manual-review path.** Only `ambiguous match` (customer), `binding
  conflict` (duplicate order ID), and `duplicate risk` route to
  `blocked_manual_review`; `mapping missing` (unmatched product) and
  `data shape/schema mismatch` route to `failed_retryable`; `financial
  total mismatch` keeps its own distinct posture, not one of the six
  confirmation-required sub-reasons.
- **Rollback/recovery path.** The total-check guard is **mandatory and
  permanent — no flag may bypass it**. A mismatch beyond tolerance
  (exact tolerance = open, MBQ-56) routes to `financial total mismatch`,
  held in `failed_retryable`, never silently re-queued by a timer/backoff.
  Reconciliation re-verifies a previously-imported order's total against
  Shopify's current state using the same class, not a new mechanism. Order
  edits, cancellations, refunds, and returns all remain **deferred** —
  see the explicit MVP-out-of-scope confirmation below.
- **Audit/log proof.** Financial-evidence fields (tax/shipping/discount/
  payment) travel with the order-import job payload so a partial/failed
  import can be retried without re-deriving totals; the accepted MBQ-26
  error-center extensions require `financial total mismatch` entries to
  render an inline evidence breakdown (Shopify total vs. computed Odoo
  total, per component) and `mapping missing` entries to link directly to
  the matching flow.
- **MVP acceptance criteria.** The whole-order-hold rule holds without
  exception; the total-check guard is unbypassable; the same-currency-only
  rule and the enqueue-only product-webhook rule (both detailed below)
  hold without exception; no invoice/payment posting automation exists
  anywhere in the flow.

### Same-currency-only order import (DEC-020 / MBQ-64) — explicit test requirement

- **Accepted rule.** Phase 1 automatic order import is **same-currency
  only**: same-currency means `Order.presentmentCurrencyCode ==
  Order.currencyCode`. For a same-currency order, `sale.order.currency_id`
  follows the connector's normal configured Odoo pricelist/company
  currency, aligned to the shop currency.
- **Divergent-currency behavior (mandatory test).** For
  `Order.presentmentCurrencyCode != Order.currencyCode`, the connector
  **must not** silently create/import a normal Odoo sale order in shop
  currency, under any circumstance. The order is **blocked from
  automatic sale-order creation**, **before** SO creation, and routed to
  manual review / treated as an explicit unsupported-scope case. This
  block is **independent of the total-check guard's outcome** — a
  reconciling shop-currency total is explicitly **not** evidence that a
  divergent order is safe to import.
- **Evidence-capture requirement (mandatory test).** Both `shopMoney` and
  `presentmentMoney` amounts, plus `Order.presentmentCurrencyCode`, must
  be captured as audit/reconciliation evidence **in every case**, whether
  or not a sale order is created.
- **Explicitly open (do not assert as decided in any test's pass
  criteria):** the exact final error-class/sub-reason mapping for a
  blocked divergent-currency order, and the exact enforcement mechanism
  (a dedicated manual-review queue entry vs. a harder unsupported-scope
  block), remain implementation planning per DEC-020 — a future test
  suite must confirm *that* the order is blocked before SO creation and
  that evidence is captured, without presupposing which specific class
  or mechanism the order-import task ultimately picks.
- **Non-MVP confirmation.** Presentment-currency-denominated Odoo orders
  remain explicitly **non-MVP** unless and until a later, separately
  authorized scope expansion designs currency/pricelist provisioning.

### `ORDERS_UPDATED` / order-edit posture — explicit test requirement

An `ORDERS_UPDATED` webhook (or an equivalent reconciliation-detected
change) for an already-imported order may refresh Shopify-side evidence/
audit data **only**. It must **never** silently update the existing Odoo
sale order's line quantities, prices, taxes, shipping, discounts,
invoices, payments, refunds, or fulfillment state, under any trigger. Any
divergence between refreshed evidence and the existing representation
routes through the same total-check guard / `financial total mismatch` /
human-review posture — the webhook path and the reconciliation path must
behave **identically** for the same underlying Shopify-side change. A
future test suite must assert both paths converge to the same outcome
for the same input.

## 5. Inventory sync

- **Happy path — ongoing direction.** Odoo → Shopify is the ongoing MVP
  write-back direction (Odoo is the source of truth). A one-time,
  controlled Shopify → Odoo baseline import may establish the initial
  Odoo baseline at first-sync only — never a standing bidirectional sync.
  Data chain: ProductVariant → InventoryItem (1:1) → InventoryLevel (per
  Location) → Location. Every write requires an explicit, non-inferred
  Odoo-location ↔ Shopify-Location mapping (exactly one Shopify Location
  per Odoo location, no name-based inference); at least one mapped pair
  is required before any write.
- **Duplicate/idempotency path.** The inventory-level binding `(store,
  inventory_item_id, location_id)` is the sole identity anchor — a
  re-processed event matches the existing binding and updates, never
  duplicates. A separate operation-level idempotency concept
  (conceptually `(store, inventory_write, inventory_item_id, location_id,
  payload_hash)`) distinguishes a retried write of the *same* intended
  quantity from a genuinely new operation. Both `inventorySetQuantities`
  and `inventoryAdjustQuantities` are on Shopify's `@idempotent`-eligible
  mutation list as of API version 2026-04 (a 24-hour dedup window makes
  retry safe). Operations against the same `(store, inventory_item_id,
  location_id)` are serialized while a prior operation is unresolved.
  "Duplicate risk" as an error class is not applicable to inventory
  (writes update, never create duplicate records).
- **Missing-dependency path.** No mapping → block, **never guessed**:
  `inventory location missing` (one of the six confirmation-required
  classes). Ambiguous multi-mapping candidates → `ambiguous match`. A
  `INVENTORY_LEVELS_DISCONNECT` event for a mapped location routes to the
  same handling as an unmapped location, never a silent skip. A missing
  or stale product-variant binding on the inventory side routes to
  `mapping missing` → `failed_retryable`, **not** `blocked_manual_review`.
- **Mapping-conflict path.** Same `ambiguous match`/`inventory location
  missing` handling as above; a compare-and-set write's `compareQuantity`
  no longer matching Shopify's current value → `concurrency/race
  conflict` → auto-retry with backoff after a fresh read.
- **API-failure path.** Same throttling/temporary-network/permission/
  validation rows as other domains; the ambiguous-outcome rule applies to
  any mutation falling outside the `@idempotent` surface — a safe
  verification read before retry, or `blocked_manual_review`, never a
  blind retry.
- **Retry path.** Four-case taxonomy; compare-and-set races auto-retry
  with backoff after a fresh read.
- **Manual-review path.** `inventory location missing` and `ambiguous
  match` are the inventory-domain manual-review triggers.
- **Rollback/recovery path.** No "rollback"/"recovery" mechanic is
  separately documented for inventory beyond the job-state recovery loop
  and the reconciliation backstop (below) — flagged as a deliberate
  architecture choice pending confirmation in the domain's own future
  task spec.
- **Audit/log proof.** The source-of-truth decision is persisted and
  auditable; the first-push confirmation record persists a preview
  snapshot, confirming operator, timestamp, source-of-truth decision, and
  scope (mapped-location-pair coverage).
- **MVP acceptance criteria.** `committed` is **never** a write target,
  under any circumstance; `available` is the sole Phase 1 write target
  (`on_hand` allowed but not default); `inventorySetQuantities`
  (compare-and-set) is the preferred default mutation; no flag bypasses
  any of the consolidated safety guards.

### Inventory first-push safety (DEC-018 MBQ-33) — explicit test requirement

The first-push guard requires **all** of: a mapped Shopify location; a
preview of SKU/variant/location quantities that will be written; explicit
operator confirmation of that preview; a recorded source-of-truth
decision; and the ability to skip or manually match ambiguous items
rather than forcing a guess. Granularity is fixed at **no coarser than
store + mapped Odoo Location ↔ Shopify Location pair + product/variant
binding** (DEC-018) — the guard is satisfied once per mapped pair, and a
newly-added mapped location later re-enters its own first-push guard. A
future test suite must assert: (a) no write occurs for a mapped pair
before its own confirmation record exists; (b) an ambiguous SKU/variant/
location combination at first push is skipped or manually matched, never
guessed; (c) the confirmation record (preview snapshot, confirming
operator + timestamp, source-of-truth decision, scope) persists
correctly; (d) no flag/setting/configuration combination can bypass the
guard (Part A §I.5).

## 6. Fulfillment / tracking update

- **Happy path.** The **only** trigger is a validated `stock.picking`
  (the Validate action) — including a backorder-split picking, which is
  its own fulfillment event. Regardless of a one/two/three-step Odoo
  warehouse workflow, the trigger is the **final** `stock.picking` in the
  chain whose Validate action represents goods actually leaving the
  warehouse. Matching: Odoo picking → its sale order → the bound Shopify
  order (via the order binding) → that order's open FulfillmentOrder(s) →
  matched line items/quantities via `lineItemsByFulfillmentOrder`. The
  notification decision (default off, per-store) is read and **persisted
  on the job at enqueue time**, never re-read at retry time. Tracking
  fields (`carrier_tracking_ref`, `carrier_tracking_url`, `carrier_id`,
  from Odoo's `stock_delivery` module) are written after fulfillment
  creation; tracking may also be updated afterward via
  `fulfillmentTrackingInfoUpdate` without creating a second fulfillment.
- **Duplicate/idempotency path.** The FulfillmentOrder/Fulfillment binding
  is keyed `(store, Shopify FulfillmentOrder GID)` (and the Fulfillment
  GID once created) — the sole identity anchor. A tracking-only update is
  a visibly distinct event and never creates a second fulfillment
  (operation-level idempotency key). Operations against the same
  `(store, picking, Shopify target)` are serialized while a prior
  operation is unresolved.
- **Missing-dependency path.** A picking whose lines cannot be resolved to
  Shopify order line items (missing order or product-variant binding) is
  **unmatched and blocks for manual review** — never fulfilled by guess.
- **Mapping-conflict path.** A live Shopify FulfillmentOrder
  `assignedLocation` read is authoritative per-operation; a mismatch
  between the picking's expected location and the live read is an
  accepted **widening of `ambiguous match`** (not a new error class) —
  routed to confirmation-required manual review because the operator
  outcome is identical.
- **API-failure path.** Neither `fulfillmentCreate` nor
  `fulfillmentTrackingInfoUpdate` is on Shopify's `@idempotent`-eligible
  mutation list — any ambiguous-outcome failure (timeout/connection loss
  with unknown result) requires a safe verification read (re-query the
  order's Fulfillments/FulfillmentOrder status) before retry, or
  `blocked_manual_review` if inconclusive; never a blind retry.
- **Retry path.** Four-case taxonomy; the verification-read case is the
  fulfillment domain's dominant retry path given the non-`@idempotent`
  mutation surface.
- **Manual-review path.** An unmatched picking (RA-023); a widened
  `ambiguous match` location mismatch; a missing notification
  confirmation (`fulfillment notification confirmation missing`) — all
  route to `blocked_manual_review`, resolved by the Reviewer role.
- **Rollback/recovery path.** Order cancellations, returns, and refunds
  are explicitly **deferred** — a cancelled Odoo picking (before
  validation) simply never becomes a fulfillment event; a Shopify-side
  fulfillment cancellation or a return/refund affecting an already-
  fulfilled order is **out of scope** for this sprint's domain.
- **Audit/log proof.** Every fulfillment log entry shows the related sale
  order, picking, Shopify order, Shopify FulfillmentOrder/Fulfillment ID,
  tracking number/carrier, and the notification setting (requested/
  suppressed); blocked/failed entries carry a human-readable reason and a
  suggested next action — no raw stack trace as primary UX.
- **MVP acceptance criteria.** Fulfillment never depends on the
  `inventory` domain's Odoo-location mapping table (uses only the core
  Shopify Location reference and/or a live Shopify read); no new error
  class is added to the fixed 16-class registry; `FULFILLMENT_ORDERS_*`
  lifecycle events beyond ordinary creation/tracking are **not**
  subscribed to in Phase 1 (MBQ-61).

### Fulfillment Odoo-event trigger (DEC-019) — explicit test requirement

Per DEC-019, `job_source = odoo_event` is the accepted seventh job-source
value, used for exactly two in-scope cases, named at the decision level
as "inventory push enqueued by a relevant Odoo stock change" and
"fulfillment creation triggered by a validated `stock.picking`." DEC-019
itself explicitly leaves the exact trigger-origin field/model/Selection-
value implementation as open, undecided implementation planning. The
literal snake_case Selection values `inventory_stock_change` and
`fulfillment_picking_validation` are recorded at the later,
implementation-planning-level
[`core-naming-schema-planning.md`](../07-implementation-plan/core-naming-schema-planning.md)
(AR-019) and restated in the current
`master-blueprint-open-questions.md` register's MBQ-62 row — this matrix
cites AR-019 as the source of the exact identifiers, and DEC-019/MBQ-62
as the source of the underlying two-case decision, rather than treating
either alone as authoritative for both. A future test suite must assert:
(a) a fulfillment creation triggered by a validated picking is classified
`job_source='odoo_event'` with trigger-origin
`fulfillment_picking_validation`; (b) `odoo_event` is never used for a
webhook, manual sync, scheduled sync, reconciliation, setup-readiness, or
export-preview-dry-run job; (c) the originating Odoo event's identity
(the specific picking) and its own timestamp (distinct from enqueue time)
are recorded, extending the standard audit shape.

## 7. Manual sync

- **Happy path.** An explicit operator action (`job_source='manual_sync'`)
  for any domain — product, customer, order, inventory (ongoing writes),
  or fulfillment tracking updates. Interactive/batch operations always
  show a blocking preview ("will create N, link M, N ambiguous," or the
  inventory preview shape) before any create/bind/write action — this
  gate is **not** satisfied by retrospective sync-center visibility.
- **Duplicate/idempotency path.** Identical binding/idempotency rules as
  the domain being manually synced — manual trigger does not relax any
  guard.
- **Missing-dependency / mapping-conflict / API-failure / retry / manual-
  review paths.** Identical to the domain's own rows above — a manual
  trigger changes *who* initiated the job, not *how* the job is
  evaluated.
- **Rollback/recovery path.** Same as the domain's own row.
- **Audit/log proof.** The job/log record must show `job_source =
  'manual_sync'` and the initiating user, distinguishing it from an
  automated trigger in every audit surface.
- **MVP acceptance criteria.** A manual sync is never granted a bypass of
  any gate (pre-create check, first-push guard, total-check guard) that
  an automated trigger would also have to satisfy.

## 8. Scheduled sync

- **Happy path.** A timer-driven job (`job_source='scheduled_sync'`) for
  any domain, using the same layered-trigger posture as webhook/manual/
  reconciliation ("layered, never webhook-only" — DEC-005).
- **Duplicate/idempotency / missing-dependency / mapping-conflict / API-
  failure / retry / manual-review / rollback paths.** Identical to the
  domain's own rows above.
- **Audit/log proof.** The job/log record shows `job_source =
  'scheduled_sync'`, distinguishing scheduled runs from manual/webhook/
  reconciliation runs in every audit surface; cron/queue health is one of
  the nine accepted essential readiness checks, so a scheduled sync must
  never silently run against an unhealthy queue substrate.
- **MVP acceptance criteria.** Reconciliation cadence/scope is per-store/
  per-domain with a configurable conservative default (MBQ-17) — never
  one global cross-domain job; exact intervals/batch sizes remain
  implementation planning, not asserted here.

## 9. Dashboard / sync / error-center behavior

- **Happy path.** The dashboard renders a lead plain-language answer band
  ("All systems normal" / "N items need your attention") above exactly
  the **nine accepted cards** (connection health; last successful sync per
  domain; failed jobs by severity; manual-review count by sub-reason;
  retry-waiting count; first-push-pending count; inventory exceptions;
  fulfillment exceptions; duplicate/matching exceptions) plus a recent-
  activity timeline with quick actions and reconciliation status — no
  tenth card, no chart, in MVP.
- **Duplicate/idempotency path.** Not applicable to the dashboard itself
  (a read/aggregation surface); a future test should confirm dashboard
  counts reconcile against the underlying job/log data without
  double-counting a job across two cards.
- **Missing-dependency path.** An empty/first-run dashboard shows a
  guided empty state ("Connect your store to begin," or post-setup "Your
  first sync hasn't run yet") with one concrete next action — never a
  bare zero with no guidance.
- **Mapping-conflict path.** The duplicate/matching-exceptions card routes
  to the same filtered manual-review queue as the underlying `ambiguous
  match`/`binding conflict`/`duplicate risk` classes.
- **API-failure path.** An overdue-sync or API-throttled state surfaces as
  an exception card with an explanation — never a silent stale count.
- **Retry path.** The error center's retry affordance is exactly one of
  the four accepted retry UI cases per entry — never an unconditional
  retry button, and a terminal row (e.g. `failed_final` after exhaustion)
  carries no retry control, only an explicit re-trigger path clearly
  labelled as a new job. **No flag, setting, role, or "force" affordance
  may bypass a class's assigned retry case** — e.g. an Admin cannot force
  an immediate retry of a "fix first" or "verify before retry" case
  without the blocking condition actually being resolved first; a future
  test suite must include a negative test attempting exactly this bypass
  and asserting it is rejected.
- **Manual-review path.** The manual-review count card routes to the
  Reviewer queue; every entry shows the specific sub-reason (never a
  generic "needs review" label).
- **Rollback/recovery path.** Not applicable directly — the dashboard/
  error center is a read/action surface over the domains' own recovery
  mechanics.
- **Audit/log proof.** No raw technical logs render as the dashboard's
  primary experience — human-readable activity lines only, with detail
  living in the sync-center/error-center's own filtered views; every
  error type leads with plain-language reason + fix + owner, with
  technical detail (HTTP status, `extensions.code`, raw response) confined
  to an explicit expand.
- **MVP acceptance criteria.** Honest freshness everywhere (mechanism
  named — webhook/scheduled/manual/reconciliation — never a "real-time"
  claim); high-signal only (every element informs, reassures, or guides
  action, never a vanity metric); a first-time viewer can answer "is
  anything wrong, where do I click" within one screenful.
- **Open item (flagged, not filled in here).** This matrix's dashboard
  rows above concretely exercise the Premium Simplicity Standard's "no
  clutter" and "business-user-friendly copy" gates; the remaining four
  gates (smooth guided flows, clean visual hierarchy, minimal cognitive
  load, progressive disclosure —
  [`ui-ux-design-review-checklist.md`](./ui-ux-design-review-checklist.md)
  §L items 1–4) have no dashboard-specific test row in this sprint,
  since the dashboard's own screen-level implementation task has not yet
  been scoped. The eventual dashboard/UI implementation task's own §9
  spec must define concrete tests for those four gates rather than
  inheriting only the wizard-focused Task 006 checklist reference in
  [`foundation-test-matrix.md`](./foundation-test-matrix.md).

---

## Explicit MVP scope confirmations (must be reflected in every domain test suite)

- **Same-currency-only order import (DEC-020 / MBQ-64).** See §4 above —
  a divergent-currency order is never auto-imported as a normal Odoo sale
  order in shop currency; the block is independent of the total-check
  guard's numeric outcome.
- **No automated presentment-currency Odoo orders in MVP.** Presentment-
  currency-denominated Odoo orders (the alternative to the accepted
  same-currency-only posture) remain explicitly non-MVP, per DEC-020.
- **Product delete webhook never directly deletes/archives (DEC-020 /
  MBQ-65).** `PRODUCTS_CREATE`, `PRODUCTS_UPDATE`, and `PRODUCTS_DELETE`
  are implemented in Phase 1 as **enqueue-only triggers** — a received
  webhook never writes directly to Odoo. Each product webhook job
  performs a **follow-up authoritative read** before any create, update,
  or delete is applied. A `PRODUCTS_DELETE` webhook **never directly
  deletes or archives** the bound Odoo product on receipt; ambiguous or
  unconfirmable cases route to manual review, reusing existing
  vocabulary — none invented. The existing layered-sync reconciliation
  pass remains the required backstop **regardless of webhook health**. A
  future test suite must assert both the enqueue-only behavior and the
  mandatory follow-up read for all three product webhook topics, not
  just delete.
- **Inventory first-push safety.** See §5 above — the guard (mapped
  location, preview, explicit confirmation, recorded source-of-truth,
  skip/manual-match for ambiguous items) is mandatory before any pair's
  first write and unbypassable by any flag.
- **Fulfillment Odoo-event trigger (DEC-019).** See §6 above —
  fulfillment creation is triggered exclusively by a validated
  `stock.picking`, classified `job_source='odoo_event'` with a
  trigger-origin sub-classification, never any other trigger.
- **Manual review for ambiguity.** Every domain above routes a genuinely
  ambiguous outcome (multiple plausible matches, an unresolvable
  location, an unconfirmable delete) to `blocked_manual_review` with a
  specific, named sub-reason — never a silent best-guess resolution and
  never a generic "needs review" label without the sub-reason.
- **No payout/refund/Markets/metafields/subscriptions/POS/B2B scope.**
  Confirmed absent from the accepted DEC-014/DEC-015 decision text by
  direct search of both documents: "Markets," "metafield(s)," "POS," and
  "B2B" have zero occurrences in either file. "Subscription" **does**
  appear in DEC-015 (six times), but every occurrence refers to
  Shopify's `WebhookSubscriptionTopic` webhook-registration mechanism
  (e.g. subscribing to `INVENTORY_LEVELS_UPDATE`), never to a
  commerce/recurring-billing subscription feature — a future reader
  should not mistake this for evidence of commerce-subscription scope.
  Payout reconciliation and automatic invoice/payment posting are
  explicitly named as **not authorized** by the accepted gateway →
  journal classification mapping (MBQ-30); refunds, returns, and
  order-edit automation are explicitly **deferred**, unchanged from
  DEC-003. No future domain test suite should assume any of these seven
  areas are in scope without a new, separately accepted decision.
