# DEC-010 — Inventory Architecture Strategy

> Proposed **architecture** decision record for **AR-007** (inventory
> architecture), for the premium Odoo 19 ↔ Shopify Connector. Companion
> evidence-backed brief:
> [`../03-architecture/ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md).

## Status

**Proposed for ChatGPT review.**

- **Sprint:** AR-007 + AR-008 Decision Preparation (after DEC-008/DEC-009
  acceptance, PR #65 merged into `Shopify-connector`).
- **Date:** 2026-07-02.
- **This record does not self-accept.** It becomes an accepted architecture
  decision only after ChatGPT (with Fable's advisory review) formally accepts
  it, mirroring the DEC-004/005/006/007/008/009 acceptance pattern.

## Scope

**AR-007 inventory architecture only.** This record decides the Phase 1
inventory **source-of-truth posture**, the **Shopify/Odoo inventory mapping**
concept, the **location mapping** posture, the **first-push guard** posture
(as an application of the already-accepted DEC-007 guard, not a
re-statement), the **sync trigger** posture, the **idempotency/retry**
posture (as an application of the already-accepted DEC-009 rules), and
**user-facing log/audit** requirements for inventory. It does **not** decide
exact Odoo model fields, exact computed quantity fields, exact mutation
choice where not verified, exact cron cadence, exact feature-flag UI, or the
exact first-push confirmation record schema (all routed to the Master
Blueprint, §"What remains open"). It does **not** modify DEC-003/004/005/006/
007/008/009.

## Accepted context

- **DEC-003 (MVP scope):** inventory write-back (Odoo→Shopify) is in MVP;
  multi-location-aware; `committed` never written; initial Shopify stock
  import is controlled/reviewed; auto-apply not accepted as default MVP
  behaviour.
- **DEC-006 (binding/dedup/identity):** dedicated, store-scoped bindings;
  inventory identity needs `inventory_item_id` + `location_id`; match
  priority existing binding → SKU/internal reference → barcode → manual; no
  name-only automatic matching.
- **DEC-007 (Phase 1 scope clarifications):** the first-inventory-push guard
  (mapped location + preview + operator confirmation + recorded
  source-of-truth + skip/manual-match option), required at a granularity no
  coarser than per-store.
- **DEC-008 (module boundaries):** `shopify_connector_inventory` depends on
  `core` + `product` only (sibling of `sale`); `shopify_connector_fulfillment`
  does not depend on it.
- **DEC-009 (error/retry/idempotency):** the 16-error-class taxonomy
  (including "inventory location missing"); the ambiguous-outcome rule for
  non-`@idempotent` writes; layered idempotency including a "first-inventory-
  push confirmation record."
- **DEC-005 (sync orchestration):** layered sync (webhooks + scheduled +
  manual + reconciliation), never one mechanism alone.

## Decision proposed

Adopt the Phase 1 inventory architecture set out in
[`ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md):
Odoo is the ongoing source of truth for Shopify inventory (Odoo→Shopify
write-back), with a controlled one-time/first-sync import establishing the
initial Odoo baseline from Shopify where relevant; inventory identity keys on
`(store, inventory_item_id, location_id)`; an explicit, non-inferred Odoo-
location↔Shopify-Location mapping gates every write; the DEC-007 first-push
guard is honored in full; sync is layered (webhook where verified + scheduled
+ manual + event-driven enqueue + reconciliation); `inventorySetQuantities`
(compare-and-set) is the preferred default operation with a persisted
`@idempotent` key; and the DEC-009 ambiguous-outcome rule governs any
inventory-adjacent write outside the 17-mutation `@idempotent` surface.

## Inventory source-of-truth posture

- **Ongoing:** Odoo is the source of truth. The Phase 1 **default write
  target is Shopify's `available` field**; `on_hand` is an allowed/writable
  field (fact #4) but is **not** an equally-weighted default — using
  `on_hand` instead requires the Master Blueprint to explicitly choose and
  justify that mapping, because `on_hand` is a sum across multiple states
  (`available + committed + reserved + damaged + safety_stock +
  quality_control`, fact #2) with materially different semantics than a
  single sellable-quantity figure. `committed` is **never** written, under
  any circumstance.
- **First-sync:** a controlled, reviewed one-time import from Shopify may
  establish the initial Odoo baseline (DEC-003), not a standing bidirectional
  sync.
- **No autonomous bidirectional conflict resolution in Phase 1** — rejected
  (RA-020); ambiguous cases route to manual review (DEC-009), consistent with
  DEC-003's exclusion of unrestricted autonomous bidirectional catalog
  ownership for the closely analogous product domain.
- Odoo's **"Free to Use"** quantity concept is the directionally recommended
  Phase 1 **semantic** source, conceptually corresponding to Shopify's
  `available`. This decides the **quantity concept, not the exact Odoo ORM
  source** — whether that concept is computed from `stock.quant`, a product
  quantity helper method, a stock-report/ORM method, or another
  Odoo-supported mechanism is **not verified and not decided here**; the
  Master Blueprint must verify the exact implementation source (and exact
  field/formula) before any code is written.

## Shopify/Odoo inventory mapping posture

- Chain: ProductVariant → InventoryItem (1:1) → InventoryLevel (per Location)
  → Location `[Official fact]`.
- Inventory binding keys on `(store, inventory_item_id, location_id)`,
  distinct from the product/variant binding, extending DEC-006's deferred
  inventory-identity shape.
- Per-store uniqueness on `(store, inventory_item_id, location_id)`.
- No name-only automatic matching, ever (DEC-006, unchanged).

## Location mapping posture

- At least one explicitly mapped Odoo location ↔ Shopify Location pair is
  required before any write; the mapping mechanism must be structurally
  multi-location-capable even for a single-location Phase 1 merchant.
- Each Odoo location maps to exactly one Shopify Location; no inferred/
  name-based mapping.
- No mapping → block, "inventory location missing" (DEC-009), never guessed.
- Ambiguous multi-mapping candidates → "ambiguous match," manual review.
- **Clarified (not an open DEC-008 contradiction, not a DEC-008 amendment):**
  this record does **not** decide the exact Odoo↔Shopify location-mapping
  schema, and does **not** change DEC-008's dependency direction.
  `shopify_connector_inventory` remains the sole owner of the Odoo-location
  ↔ Shopify-Location **mapping** used for inventory push decisions.
  `shopify_connector_fulfillment` must not depend on
  `shopify_connector_inventory` and must not read that mapping table. A
  **minimal Shopify Location *reference*** (not a mapping) — the store's
  Shopify Location GID(s), name(s), active/status where available, and
  last-synced/seen metadata if later needed — may live in
  `shopify_connector_core` as shared substrate. **Attribution corrected (PR
  #66 Fable review):** `core` owning this reference is a **proposed
  clarification/extension of DEC-008's `core`-owns list**, not something
  DEC-008 already explicitly decided — DEC-008 names `core`'s cross-cutting
  substrate (transport, queue, binding abstraction, error registry, setup
  wizard, dashboard/log center) but does not itself say `core` owns
  Shopify-object reference data. This clarification is **proposed by
  DEC-010/DEC-011** and would be **ratified against DEC-008 only if ChatGPT
  accepts DEC-010/DEC-011** — it does not change DEC-008's dependency
  direction, does not create a new module, and does not require a full
  DEC-008 amendment cycle. `shopify_connector_inventory` remains the sole
  owner of Odoo-location ↔ Shopify-Location mapping for inventory push
  decisions regardless. See the matching clarification in
  [`DEC-011`](./DEC-011-fulfillment-architecture-strategy.md#fulfillmentorder-posture)
  and the AR-007 brief §4/§9 — the exact mechanism by which fulfillment
  confirms a picking's source location against the Shopify fulfillment
  location remains **open for the Master Blueprint**.
- **Core Location reference invariants / open questions [not a decision to
  create fields/models]:** the proposed core Shopify Location reference is
  **Shopify-side reference data only** — it must **never** store
  Odoo-location IDs or any Odoo↔Shopify mapping decision, or it becomes a
  second, competing mapping table; Odoo↔Shopify mapping remains
  inventory-owned. Exact stale-cache handling, precedence between the cache
  and a live Shopify FulfillmentOrder `assignedLocation` read, and refresh
  cadence remain **open for the Master Blueprint**; for a specific
  fulfillment operation, a live `assignedLocation` read should be treated as
  authoritative unless the Master Blueprint proves otherwise.

## First-push guard posture

- The DEC-007 guard applies in full, unweakened: mapped location, preview of
  SKU/variant/location quantities, explicit operator confirmation, a
  recorded source-of-truth decision, and the ability to skip or manually
  match ambiguous items — required before the first Odoo→Shopify write at
  the configured first-push granularity. **Wording corrected (PR #66 Fable
  review):** DEC-007 requires this granularity no coarser than per-store;
  this record does **not** decide the exact granularity (per-store /
  per-binding / per-variant-location binding remain open, not decided here).
- **Open:** the exact granularity of "first" (per-store / per-binding /
  per-variant-location-binding) and whether ongoing (post-first-push) writes
  also require preview/confirmation (apply-mode: auto-apply vs.
  review-then-apply, C-INV-04) — **not decided here**, remains open for the
  Master Blueprint.

## Sync trigger posture

- Layered: scheduled reconciliation (cadence: implementation-planning
  default) + manual sync (enqueued, never inline) + event-driven enqueue from
  relevant Odoo stock changes.
- Shopify inventory-webhook-driven import: candidate, but the webhook topic
  is unverified in repo docs — **flagged open question, not asserted or
  relied upon exclusively**.
- Never webhook-only (DEC-005, unchanged).

## Idempotency/retry posture

- `inventorySetQuantities` (compare-and-set) preferred default;
  `inventoryAdjustQuantities` a candidate for narrower delta pushes — exact
  choice per trigger type open.
- Both mutations require `@idempotent` as of API 2026-04 and are within the
  17-mutation fixed list — a persisted, reused idempotency key within the
  24-hour dedup window makes retry safe (DEC-009 case 2).
- If a targeted API version or a future inventory-adjacent mutation falls
  outside the `@idempotent` surface, the DEC-009 **ambiguous-outcome rule**
  applies in full: safe verification read before retry, or
  `blocked_manual_review` — no blind retry.

## User-facing log/audit requirements

Every inventory write log entry shows: old (last-known) quantity, intended
quantity, Shopify location, source-of-truth, binding (SKU/variant/location
identity), the mutation used, the idempotency key, and — for first-push
writes — the operator-confirmation record. No technical-only errors; every
failure carries a human-readable reason and a suggested fix (extends DEC-009
§8, unchanged).

## What remains open

- Exact Odoo model/field names (binding model, mapping model, log/audit
  fields).
- Exact computed quantity field/formula behind "Free to Use," and whether a
  configurable default (Forecast/On-Hand/Free-to-Use) is offered.
- Exact mutation choice per trigger type beyond the directional preference.
- Exact cron cadence for scheduled reconciliation.
- Exact feature-flag/configuration UI.
- Exact first-push confirmation record schema.
- Exact granularity of "first" for the DEC-007 guard.
- Whether ongoing syncs require preview/confirmation on every write or only
  the first (apply-mode, C-INV-04) — explicitly **not decided here**.
- Verification of the Shopify inventory-webhook topic string(s) (see
  [`ar007-ar008-evidence-refresh.md`](../03-architecture/ar007-ar008-evidence-refresh.md)).
  **Corrected (PR #66 Fable review):** the literal 17-mutation list is
  already itemized in `rb14-part2-open-question-resolution.md` (RQ-005-2) —
  not an open item here; only `@idempotent` key-uniqueness scope (per-shop/
  app/global) and any API-version-specific implementation detail remain
  open.
- The exact Odoo-side implementation source for the "Free to Use" quantity
  concept (`stock.quant`, a product quantity helper, a stock-report/ORM
  method, or another Odoo-supported mechanism) and its exact field/formula —
  **not verified, not decided here**; this record decides the semantic
  concept only.
- Whether `on_hand` is ever used as an alternative Phase 1 write target
  instead of `available` — **not decided here**; `available` is the default;
  an `on_hand` mapping requires explicit Master Blueprint justification given
  its multi-state-sum semantics.
- The exact mechanism by which `shopify_connector_fulfillment` confirms an
  Odoo picking's source location against the Shopify fulfillment location
  (core Shopify-Location reference vs. live FulfillmentOrder
  `assignedLocation` fetch, or both) — the **ownership principle** is
  clarified above; the **exact confirmation mechanism** is a Master Blueprint
  item, shared with AR-008/DEC-011.
- The feature-flag/per-store capability-configuration mechanism (already
  routed to UX/operator-flow and Master Blueprint per DEC-008).

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Overwriting live Shopify stock on the first write | DEC-007 first-push guard (mapped location + preview + confirmation + source-of-truth + skip option), unweakened here |
| Double-decrementing multi-location SKUs | Inventory identity keyed on `(store, inventory_item_id, location_id)`, not SKU alone (RA-019) |
| Writing the read-only `committed` field | Structurally never offered as a write target under any circumstance (RA-018) |
| Treating `on_hand` as equally default to `available`, mis-mapping a multi-state sum | `available` is the Phase 1 default target; `on_hand` requires explicit Master Blueprint justification before use |
| Silent duplicate/ambiguous writes on retry | DEC-009 ambiguous-outcome rule + compare-and-set + persisted idempotency key |
| Guessing a location mapping that doesn't exist | Block + "inventory location missing" error class; never inferred from name |
| Autonomous bidirectional conflict causing silent data loss | Rejected in Phase 1 (RA-020); ambiguous cases always route to manual review |
| Fulfillment silently depending on inventory's location-mapping table, contradicting DEC-008 | Clarified: `inventory` keeps mapping ownership, `fulfillment` never depends on `inventory`; a minimal shared Shopify-Location reference may live in `core` instead — exact confirmation mechanism left open for the Master Blueprint, not silently resolved |

## No implementation authorized

**This record does not authorize implementation.** It proposes an
architecture posture for ChatGPT (and Fable's advisory) review only.
Implementation of any inventory sync code, Odoo module, model, field,
mutation call, or test remains blocked until: (1) ChatGPT accepts this
record (or a revised version of it), and (2) ChatGPT separately opens the
implementation gate per the Phase 1 research-phase-exit criteria
(`../05-qa/quality-feedback-loop.md` §10) and `CLAUDE.md` §5. Acceptance of
this record alone does not open that gate.

## Review / change control

- **This record proposes AR-007 architecture only.** No API strategy,
  binding-schema-shape, module-boundary, or MVP-scope decision is
  re-litigated (all already decided by DEC-003/004/005/006/007/008).
- **Related:** AR-007 (`../05-qa/architecture-review-log.md`); the companion
  evidence-backed brief
  (`../03-architecture/ar007-inventory-architecture-decision-brief.md`); the
  small evidence refresh
  (`../03-architecture/ar007-ar008-evidence-refresh.md`); DEC-006/007/008/009
  (accepted context, unmodified).
- **Changes** to this proposal require ChatGPT review; if accepted, a future
  acceptance-patch note updates this Status field and the linked RA rows
  (RA-018 through RA-021), mirroring the DEC-004/005/006/007/008/009
  acceptance pattern.
