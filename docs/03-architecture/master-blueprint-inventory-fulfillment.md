# Master Blueprint — Part C: Inventory and Fulfillment Domain Blueprint

> **Master Blueprint Sprint C deliverable** for the premium **Odoo 19 ↔
> Shopify Connector**. Detailed domain blueprint for the inventory and
> fulfillment domains — still **documentation only, no code**. Companion
> index: [`master-blueprint.md`](./master-blueprint.md). Companion Part A
> (core substrate):
> [`master-blueprint-core-substrate.md`](./master-blueprint-core-substrate.md).
> Companion Part B (product/customer/sale-order):
> [`master-blueprint-product-customer-sale.md`](./master-blueprint-product-customer-sale.md).
> Companion open-questions register:
> [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).
> Companion decision record:
> [`../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md`](../04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md)
> (Status: **Proposed for ChatGPT review**, not accepted).

## Status

**Proposed for ChatGPT review. Not accepted.** Documentation only — the
no-code gate (`CLAUDE.md` §4–§5) is in force. **This document does not
authorize implementation** under any outcome. Starting point for this
sprint: PR #73 merge commit `09829a804eef9c4099960f5604729f3a775793d1`
(Accept DEC-014 Master Blueprint Sprint B), confirmed as the base before
editing. Part A (core substrate, DEC-013) and Part B (product/customer/
sale-order, DEC-014) remain **Accepted by ChatGPT** and are reused,
unmodified, throughout this document. **Part D (UI/UX Screen Design
Blueprint) and Part E (implementation-planning bridge) remain Not
started.** Implementation remains blocked.

## Claim labels used throughout

Same discipline as Part A/Part B (see
`master-blueprint-core-substrate.md` "Claim labels used throughout"):

- **[Accepted — DEC-0XX]** — restates an already-accepted decision, cited.
  Not re-litigated here.
- **[Blueprint proposal]** — a design detail this sprint introduces,
  converting the accepted DEC-010/DEC-011 architecture into blueprint-level
  detail. **Proposed, not yet accepted** — this whole document is pending
  ChatGPT review via DEC-015.
- **[Official fact]** — a verified Shopify/Odoo platform fact, cited with a
  URL and access date. New facts verified for this sprint are dated
  **2026-07-03**.
- **[Recommendation]** — a proposed course of action for a row whose
  register-recorded decision owner is **ChatGPT**; named as such
  everywhere it appears, never self-accepted.
- **[Inference]** — reasoning from cited accepted decisions/evidence.
- **[Open question — MBQ-nn]** — unresolved; carried in
  [`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md).

**Naming discipline (unchanged from Part A/B):** all model/field/group
names below are **proposed naming directions only** — not committed Odoo
identifiers. Exact model/field names remain **[Open question —
MBQ-01/02]** for implementation planning. Odoo ORM field names quoted from
official Odoo 19.0 source (e.g. `free_qty`, `carrier_tracking_ref`) are
**existing Odoo-core/Odoo-module fields being read/written by the
connector**, not connector-proposed names — that distinction is preserved
throughout.

---

## Scope and non-goals

**In scope:** the inventory and fulfillment domain blueprints — detailed
enough for later implementation planning, converting the **accepted**
DEC-010 (inventory architecture) and DEC-011 (fulfillment architecture)
into domain-level flows, concepts, job types, and error/retry mappings,
reusing the **accepted** Part A core substrate (DEC-013) without
modification. Uses Part B (DEC-014) only where inventory/fulfillment
depends on product/variant bindings (owned by `product`) and the order
import/binding posture (owned by `sale`).

**Explicit non-goals (per the sprint prompt and `CLAUDE.md` §5):**

- No connector code, Odoo module, model, view, controller, security file,
  manifest, test, or CI file.
- No screen-level UI/UX design or wireframes — Part D (UI/UX Screen
  Design Blueprint, MBQ-53) remains a separate, not-started sprint.
  Operator surfaces are described here only at blueprint level, reusing
  the already-accepted sync-center/error-center concepts (Part A §G/§H);
  no new dashboard or screen is introduced.
- No exact Odoo model/field/view/security identifiers beyond what is
  already an existing Odoo-core/Odoo-module field (e.g. `free_qty`,
  `carrier_tracking_ref`) — connector-side names remain **[Open question —
  MBQ-01/02]**.
- No exact GraphQL mutation parameters beyond what is explicitly cited and
  verified this sprint.
- No re-litigation of DEC-010/DEC-011's accepted architecture — this
  document converts it to blueprint detail, it does not change it.
- No implementation authorization under any outcome.

## Relation to accepted decisions

| Accepted record | What it fixed | How this blueprint uses it |
| --- | --- | --- |
| [DEC-003](../04-decisions/DEC-003-mvp-scope.md) | Inventory write-back (Odoo→Shopify) in MVP, multi-location-aware, `committed` never written; fulfillment/tracking write-back in MVP; multi-package/multi-location fulfillment (C-FUL-02) deferred | Scope boundary for §A/§B below |
| [DEC-006](../04-decisions/DEC-006-binding-dedup-identity-strategy.md) | Store-scoped binding source of truth; no name-only matching | Inventory-level and FulfillmentOrder binding identity (§A.1/§B.1) |
| [DEC-007](../04-decisions/DEC-007-phase1-scope-clarifications.md) | First-inventory-push guard (mapped location + preview + confirmation + recorded source-of-truth + skip/manual-match option), no coarser than per-store; fulfillment customer-notification default off unless explicitly enabled/confirmed | §A.5 (first-push guard); §B.6 (notification posture) |
| [DEC-008](../04-decisions/DEC-008-module-boundary-strategy.md) | `shopify_connector_inventory` depends on `core` + `product` (sibling of `sale`); `shopify_connector_fulfillment` depends on `core` + `sale`, never on `inventory` | Module boundary and dependency statements throughout |
| [DEC-009](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) | 16-class error taxonomy (incl. "inventory location missing", "fulfillment notification confirmation missing"); classified retry; ambiguous-outcome rule; layered idempotency | §A.8/§A.14 and §B.9/§B.10/§B.13 error/retry mapping |
| [DEC-010](../04-decisions/DEC-010-inventory-architecture-strategy.md) | Phase 1 inventory architecture: Odoo ongoing source of truth, inventory identity `(store, inventory_item_id, location_id)`, explicit location mapping, first-push guard applied in full, layered sync, `inventorySetQuantities` preferred default | Primary source for §A |
| [DEC-011](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) | Phase 1 fulfillment architecture: validated `stock.picking` trigger, FulfillmentOrder-based mutations exclusively, matching via `lineItemsByFulfillmentOrder`, notification default off, operation-level idempotency key concept | Primary source for §B |
| [DEC-013](../04-decisions/DEC-013-master-blueprint-core-substrate.md) | Accepted Part A core substrate: binding contract (§C.8), job/log/error abstraction (§D), 16-class registry, operator surfaces (§E–§H), feature-flag mechanism (§I), access blueprint (§J), cross-module rules (§K), core Shopify Location reference invariants (§B.4) | Every section below builds on, and does not duplicate, this substrate |
| [DEC-014](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md) | Product/variant binding under `shopify_connector_product`; order binding under `shopify_connector_sale` | §A.11 (product/variant binding dependency); §B.4 (order/product binding prerequisite for fulfillment matching) |

AR-002 through AR-011 are all **Accepted**
([`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md));
RA-001 through RA-023 are **binding rejected approaches**
([`../05-qa/rejected-approaches-log.md`](../05-qa/rejected-approaches-log.md))
— checked before drafting; none is reintroduced by this blueprint.

## Module ownership (restated for orientation, DEC-008-authoritative)

Per the accepted DEC-008 module family, restated at
[`master-blueprint.md`](./master-blueprint.md) "Module family overview"
**[Accepted — DEC-008; DEC-013]**:

- **`shopify_connector_inventory`** — quantity write-back; Odoo↔Shopify
  location mapping (**sole owner**); first-push guard; inventory binding
  identity. Depends on `core` + `product` (sibling of `sale`).
- **`shopify_connector_fulfillment`** — fulfillment/tracking write-back;
  notification guard. Depends on `core` + `sale`. **Never depends on
  `inventory`** and must not read `inventory`'s location-mapping table
  **[Accepted — DEC-008; DEC-010; DEC-011]**.

Neither module depends on the other; both resolve product/variant
bindings **through** `product` (Part A §K.9) rather than duplicating
product-matching logic, and `fulfillment` resolves order bindings through
`sale`.

---

## A. Inventory domain blueprint

### A.1 Module boundary and dependency on core/product/order substrate

`shopify_connector_inventory` owns quantity write-back, Odoo↔Shopify
location mapping (exclusively), the first-push guard, and inventory
binding identity **[Accepted — DEC-008; DEC-010]**. It depends on `core` +
`product` only, is a sibling of `sale`, and is never depended on by
`fulfillment` **[Accepted — DEC-008]**. Per the accepted Part A binding
shape (§C.8, MBQ-11), `inventory` defines **one** concrete binding model
extending the core abstract binding contract: the **inventory-level
binding**, keyed on `(store, inventory_item_id, location_id)`, distinct
from and layered on top of the product-variant binding `product` owns
(§A.11 below) **[Accepted — DEC-006; DEC-010; Part A §C.8]**. Exact Odoo
model/field names: **[Open question — MBQ-01/02]**.

### A.2 Shopify store/location reference usage and Odoo location/warehouse mapping posture

- **Chain:** ProductVariant → InventoryItem (1:1) → InventoryLevel (per
  Location) → Location **[Official fact —
  `../01-research/shopify-official-api-notes.md`, citing
  `https://shopify.dev/docs/api/admin-graphql/latest/objects/InventoryItem`
  and `.../objects/InventoryLevel`]**, restated from DEC-010.
- **Core Shopify Location reference:** `shopify_connector_core` may hold a
  minimal, shared, Shopify-side Location reference/cache (store; Shopify
  Location GID; name; active/status where available; last-synced/seen
  metadata) — Shopify-side reference data **only**, never Odoo-location
  IDs or any Odoo↔Shopify mapping decision (Part A §B.4)
  **[Accepted — DEC-010/DEC-011 acceptance note, ratified against
  DEC-008]**.
- **Odoo location/warehouse mapping (inventory-owned, exclusively):**
  `shopify_connector_inventory` owns an explicit, non-inferred
  Odoo-location ↔ Shopify-Location mapping — each Odoo location maps to
  **exactly one** Shopify Location, no name-based inference
  **[Accepted — DEC-010]**. At least one mapped pair is required before
  any write; the mapping mechanism must be structurally multi-location-
  capable even for a single-location Phase 1 merchant
  **[Accepted — DEC-010]**.
- **Odoo location-type scope [Official fact]:** Odoo 19.0's Inventory
  management documentation enumerates location types **vendor, virtual,
  internal, customer, inventory loss, production, transit**
  (`https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management.html`,
  access date **2026-07-02**, propagated from `ar007-ar008-evidence-refresh.md`).
  **[Blueprint proposal]** the Odoo↔Shopify location mapping is meaningful
  only for **internal** stock locations (the locations a warehouse
  actually stores sellable stock in) — vendor/customer/virtual/transit
  locations are never offered as mapping candidates, since a Shopify
  Location represents a physical/fulfillment location, not a virtual
  ledger location. Exact mapping-candidate filtering mechanism: **[Open
  question — implementation planning]**.
- **No mapping → block.** Missing mapping is the `inventory location
  missing` error class (Part A §D.4), never guessed
  **[Accepted — DEC-009; DEC-010]**. Ambiguous multi-mapping candidates →
  `ambiguous match`, manual review **[Accepted — DEC-010]**.
- **Fulfillment never depends on this mapping** — `shopify_connector_
  fulfillment` uses the core Location reference and/or a live
  FulfillmentOrder `assignedLocation` read instead (§B.8 below)
  **[Accepted — DEC-008/DEC-010/DEC-011]**.

### A.3 Inventory source of truth for Phase 1

- **Ongoing:** Odoo is the source of truth for Shopify inventory
  (Odoo→Shopify write-back) **[Accepted — DEC-010]**.
- **First-sync:** a controlled, reviewed one-time import from Shopify may
  establish the initial Odoo baseline where relevant — not a standing
  bidirectional sync **[Accepted — DEC-003; DEC-010]**.
- **No autonomous bidirectional conflict resolution** — rejected
  (**RA-020**); ambiguous cases route to manual review
  **[Accepted — DEC-010]**. This sprint does not revisit RA-020; its
  revisit condition (a demonstrated, safe conflict-resolution algorithm
  with an accepted field-ownership model) is not met.
- The recorded inventory source-of-truth decision is persisted per Part A
  §B.6 (core source-of-truth settings) and is auditable per Part A §D.10
  **[Accepted — DEC-007 §4; Part A §B.6]**.

### A.4 Quantity source and exact quantity meaning (partially resolving MBQ-32)

- **Phase 1 default write target:** Shopify `available`. `on_hand` is
  allowed but **not** an equally-weighted default (requires explicit
  justification, not exercised by this sprint — see MBQ-35). `committed`
  is **never** written, under any circumstance **[Accepted — DEC-010;
  RA-018]**.
- **[Official fact — partially resolving MBQ-32, accessed 2026-07-03]** Odoo
  19.0's `product.product` model defines a `free_qty` field, labelled
  **"Free To Use Quantity"**, computed by `_compute_quantities`/
  `_compute_quantities_dict`:

  ```python
  free_qty = fields.Float(
      'Free To Use Quantity ', compute='_compute_quantities', search='_search_free_qty',
      digits='Product Unit', compute_sudo=False,
      help="Available quantity (computed as Quantity On Hand "
           "- reserved quantity)\n"
           "In a context with a single Stock Location, this includes "
           "goods stored in this location, or any of its children...")
  ```

  with the computation `free_qty = qty_available - reserved_quantity -
  expired_unreserved_qty` (per-product, context-scoped by `location`/
  `warehouse` via Odoo's context mechanism). Source:
  `https://github.com/odoo/odoo/blob/19.0/addons/stock/models/product.py`,
  access date **2026-07-03**, access status **Accessible**.
- **[Official fact, same access]** At the per-location record level,
  `stock.quant` defines `quantity` (on-hand, per quant/location/lot) and
  `reserved_quantity`, with a computed `available_quantity`:

  ```python
  @api.depends('quantity', 'reserved_quantity')
  def _compute_available_quantity(self):
      for quant in self:
          quant.available_quantity = quant.quantity - quant.reserved_quantity
  ```

  Source:
  `https://github.com/odoo/odoo/blob/19.0/addons/stock/models/stock_quant.py`,
  access date **2026-07-03**, access status **Accessible**.
- **[Blueprint proposal, partially resolving MBQ-32 at blueprint level]** The
  Odoo-side ORM source for the semantic concept DEC-010 calls "Free to
  Use" is `product.product.free_qty` (evaluated with an Odoo location/
  warehouse context matching the mapped Odoo location, §A.2) for a
  per-location push, or equivalently the per-location `stock.quant.
  available_quantity` (`quantity − reserved_quantity`) summed across the
  relevant quants at that location. Both resolve to the same underlying
  arithmetic (on-hand minus reserved), which is the Odoo-side concept that
  corresponds to Shopify's `available` (a single sellable-quantity
  figure) **[Inference — the "on hand minus reserved" shape matches
  Shopify's `available` semantics more closely than `on_hand`, which sums
  `available + committed + reserved + damaged + safety_stock +
  quality_control`, per DEC-010's already-accepted evidence]**.
- **What remains open:** whether the connector reads `product.product.
  free_qty` via context (simpler, product-level) or aggregates
  `stock.quant.available_quantity` directly (more explicit control over
  which quants/locations are summed, e.g. excluding a specific sub-
  location), and whether a configurable Forecast/On-Hand/Free-to-Use
  default is offered to the operator, remain **[Open question — MBQ-32,
  proposed partially resolved, pending DEC-015 — see the register]**; the
  source field/formula question itself is now supported by the
  official-fact citation above, subject to DEC-015's acceptance.

### A.5 First inventory push guard and confirmation posture

- **Guard (unweakened) [Accepted — DEC-007 §4; DEC-010]:** before the
  first Odoo→Shopify inventory write for a given store/binding, the
  connector requires **all** of: a mapped Shopify location; a preview of
  SKU/variant/location quantities that will be written; explicit operator
  confirmation of that preview; a recorded source-of-truth decision; and
  the ability to skip or manual-match ambiguous items rather than
  forcing a guess.
- **Granularity (MBQ-33 — ChatGPT decision, not resolved here)
  [Recommendation]:** this sprint proposes, for ChatGPT's decision, that
  the first-push guard fire at the granularity of **(Odoo location ↔
  Shopify Location mapped pair)** — i.e. the guard is satisfied once, per
  mapped location pair, the first time any inventory-level binding under
  that pair is about to be written — rather than per-store (too coarse
  for a merchant activating a second warehouse later) or per-variant-
  location-binding (guard fatigue: hundreds of confirmations for one
  location activation). Adding a **new** mapped location pair later
  re-enters its own first-push guard (mirroring Part A §I.4's "re-enabling
  a domain re-enters that domain's own guard" pattern) — a location
  activated after the initial setup does not inherit the original
  location's already-confirmed state. This is a **proposed recommendation
  for ChatGPT's direct decision**, not a self-accepted resolution; DEC-007
  requires no coarser than per-store, and this proposal satisfies that
  floor.
- **First-push confirmation record (MBQ-38 — proposed partially resolved,
  pending DEC-015) [Blueprint proposal]:** the confirmation record extends
  the Part A guard/audit shape (§D.10) with: the preview snapshot
  (SKU/variant/location/quantity rows shown), the confirming operator +
  timestamp, the recorded source-of-truth decision in force at
  confirmation time, and the scope (which mapped location pair(s) this
  confirmation covers, per the granularity above). Exact field
  names/schema remain **[Open question — MBQ-38, proposed partially
  resolved, pending DEC-015 — concept fixed, schema open]**.
- **Skip/manual-match:** an ambiguous SKU/variant/location combination at
  first push is skipped or manually matched, never guessed — consistent
  with the ordinary product-matching flow (Part B §A.6) applied to the
  inventory-level binding **[Accepted — DEC-007 §4]**.

### A.6 Inventory update direction: MVP vs later

- **MVP (Phase 1):** **Odoo → Shopify** write-back is the ongoing,
  ordinary direction **[Accepted — DEC-003; DEC-010]**. A **controlled,
  reviewed** Shopify → Odoo import may run **once**, at first-sync, to
  establish the initial Odoo baseline where relevant (§A.3) — this is not
  a standing bidirectional sync and does not repeat on an ongoing basis
  **[Accepted — DEC-003; DEC-010]**.
- **Not in Phase 1:** an ongoing, standing Shopify → Odoo inventory sync
  (beyond the one-time controlled baseline import) and any autonomous
  bidirectional conflict resolution are both out of scope — the former is
  a **new capability this sprint does not introduce** (DEC-010 names only
  the controlled first-sync import as the Shopify → Odoo direction), the
  latter is **RA-020**, unweakened.
- **Later phases:** whether a later phase ever offers a standing,
  reviewed Shopify → Odoo reconciliation-only read (distinct from a write
  path) for drift **detection** (not correction) is **[Open question —
  implementation planning, not decided here]** — the existing DEC-005
  reconciliation mechanism already re-verifies Odoo's last-pushed value
  against Shopify's current state and flags drift (§A.8 below); this is
  not a new bidirectional-write capability.

### A.7 Manual sync and scheduled sync posture

- **Layered, never webhook-only [Accepted — DEC-005; DEC-010]:**
  - **Manual sync** — an explicit operator-triggered action, enqueued
    (never inline).
  - **Scheduled sync** — reconciliation cadence, implementation-planning
    default (**[Open question — MBQ-17]**, shared with every domain).
  - **Event-driven enqueue** — a relevant Odoo stock change (e.g. a stock
    move affecting a mapped location's quantity) enqueues an inventory
    push job.
  - **Webhook-driven import candidate** — `INVENTORY_LEVELS_UPDATE`
    (§A.9 below, new official fact this sprint) is a candidate trigger
    for detecting Shopify-side inventory drift, but is never the sole
    mechanism.
- **Reconciliation is the mandatory correctness backstop** — a scheduled
  reconciliation pass re-verifies a previously-pushed inventory-level
  binding's last-known-pushed quantity against Shopify's current state
  and flags drift, the same pattern Part B §C.8 applies to order totals
  **[Accepted — DEC-005; Blueprint proposal for stating it explicitly for
  inventory]**.

### A.8 Duplicate/idempotency/retry posture (Part A job/log/error/retry concepts)

- **Binding as identity anchor:** the inventory-level binding
  `(store, inventory_item_id, location_id)` is the sole idempotency anchor
  for *identity* — a re-processed event matches the existing binding and
  updates, never duplicates **[Accepted — DEC-006; DEC-010]**.
- **Operation-level idempotency (distinct from identity)
  [Blueprint proposal, applying Part A §D.6]:** conceptually
  `(store, inventory_write, inventory_item_id, location_id, payload_hash)`
  — so a retried write of the *same* intended quantity is detected
  connector-side, while a *different* intended quantity (e.g. a
  superseding stock move) is a new operation, not conflated with the
  prior one. Exact key schema: **[Open question — MBQ-20, shared with
  every domain]**.
- **Mutation choice and idempotency [Official fact, restated from
  DEC-010]:** `inventorySetQuantities` and `inventoryAdjustQuantities` are
  both on Shopify's 17-mutation `@idempotent`-eligible list and require
  `@idempotent` as of API version 2026-04 — a persisted, reused
  idempotency key within the 24-hour dedup window makes retry safe
  (DEC-009 case 1) **[Accepted — DEC-009; DEC-010]**.
- **Ambiguous-outcome rule:** if a targeted API version or a future
  inventory-adjacent mutation ever falls outside the `@idempotent`
  surface, DEC-009's ambiguous-outcome rule applies in full — a safe
  verification read before retry, or `blocked_manual_review`, never a
  blind retry **[Accepted — DEC-009; DEC-010]**.
- **Serialization guard:** operations against the same
  `(store, inventory_item_id, location_id)` are serialized while a prior
  operation against that target is unresolved (Part A §D.7), generalizing
  DEC-011's fulfillment-specific serialization guard to inventory as well
  **[Blueprint proposal, applying Part A §D.7]**.

### A.9 Mapping failure behavior

- **No mapping → `inventory location missing`** (Part A §D.4), one of
  the six confirmation-required `blocked_manual_review` sub-classes
  (Part A §D.5.4/§D.8) — the write is held, never guessed
  **[Accepted — DEC-009; DEC-010]**.
- **Ambiguous mapping candidates → `ambiguous match`**, same routing
  **[Accepted — DEC-010]**.
- **[Official fact, proposing to resolve MBQ-37, pending DEC-015]** Shopify's
  `WebhookSubscriptionTopic` enum includes `INVENTORY_LEVELS_UPDATE`
  ("Occurs whenever an inventory level is updated. Requires the
  `read_inventory` scope."), plus `INVENTORY_LEVELS_CONNECT` and
  `INVENTORY_LEVELS_DISCONNECT` (an inventory item being connected to, or
  disconnected from, a location). Source:
  `https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic`,
  access date **2026-07-03**, access status **Accessible**. A
  `INVENTORY_LEVELS_DISCONNECT` event for a mapped location is itself a
  mapping-adjacent failure mode — it means Shopify no longer stocks that
  inventory item at that location — and routes to the same `inventory
  location missing`/`ambiguous match` handling as an unmapped location,
  not a silent skip **[Blueprint proposal]**.

### A.10 Multi-location / multi-warehouse posture

- **Structurally multi-location-capable from Phase 1**, even for a
  single-location merchant — the mapping mechanism never assumes exactly
  one location **[Accepted — DEC-003; DEC-010]**.
- **Per-location identity, never SKU-alone:** inventory identity keys on
  `(store, inventory_item_id, location_id)` specifically to avoid
  double-decrementing a multi-location SKU (**RA-019**, unweakened)
  **[Accepted — DEC-006; DEC-010]**.
- **Each Odoo location maps to exactly one Shopify Location** (§A.2); a
  Shopify Location may, in principle, receive pushes originating from at
  most one mapped Odoo location under this connector's Phase 1 model —
  whether Shopify allows (and whether the connector should ever support)
  **multiple** Odoo locations mapping to the **same** Shopify Location
  (e.g. two Odoo sub-locations both feeding one Shopify warehouse) is
  **[Open question — implementation planning, not decided here]**; no
  posture is asserted either way.
- **Warehouse vs. location:** Odoo's warehouse concept (a container for
  multiple internal locations, e.g. stock/input/output/pack) is not
  itself the mapping unit — the mapping is Odoo **location** ↔ Shopify
  **Location** (§A.2's location-type-scope note); a warehouse with several
  internal locations may need its own aggregation rule (e.g. which
  internal location's `free_qty` counts toward the mapped location's
  pushed quantity) — **[Open question — implementation planning]**, tied
  to the same aggregation-mechanism question in §A.4.

### A.11 Product/variant binding dependency

- Inventory identity is **layered on top of** the product-variant binding
  `shopify_connector_product` owns (Part B §A.1) — an inventory-level
  binding cannot exist for a Shopify ProductVariant that has no resolvable
  Odoo product-variant binding **[Accepted — DEC-006; DEC-008 "Sibling
  reuse via `product`"]**.
- **Resolution order:** an inventory push for a given Odoo product
  variant resolves the product-variant binding **first** (via `product`,
  never duplicated in `inventory`, Part A §K.9), then resolves/creates the
  inventory-level binding for the relevant `(inventory_item_id,
  location_id)` pair.
- **Unmatched product/variant:** if the underlying product-variant
  binding is missing (stale, never-exported, or ambiguous), the inventory
  write cannot proceed — routed as `mapping missing` (Part A §D.5.3,
  "manual fix then retry," `failed_retryable`, **not**
  `blocked_manual_review`, mirroring Part B §C.5's "manual fix then
  retry" routing for an unmatched order line) **[Blueprint proposal,
  applying Part A's accepted per-class routing]**, until the product is
  bound via the ordinary product-matching flow (Part B §A.6).

### A.12 Safety guards to avoid pushing wrong quantity to wrong Shopify location

Consolidated statement (each guard already introduced above, restated
together per the sprint's explicit requirement) **[Blueprint proposal,
synthesizing §A.2/§A.5/§A.8/§A.9/§A.10]**:

1. **No inferred/name-based location mapping** — an explicit, non-inferred
   Odoo-location ↔ Shopify-Location pair is required before any write
   (§A.2).
2. **No write without a mapping** — `inventory location missing`, never
   guessed (§A.9).
3. **Compare-and-set as the preferred default mutation**
   (`inventorySetQuantities`, §A.13) — reduces the risk of a stale-read
   race silently overwriting a quantity another actor changed between read
   and write.
4. **Per-location identity, never SKU-alone** — prevents double-decrementing
   a multi-location SKU (§A.10, RA-019).
5. **First-push guard** — mandatory preview + explicit confirmation before
   the very first write per mapped location pair, so a bad mapping or a
   wrong source-of-truth assumption surfaces before it reaches a live
   storefront (§A.5).
6. **No autonomous bidirectional conflict resolution** — ambiguous
   drift always routes to manual review, never an automatic merge/guess
   (§A.3, RA-020).
7. **`committed` is never a write target, under any circumstance**
   (§A.4, RA-018) — the one Shopify quantity field structurally excluded
   regardless of configuration.
8. **No flag bypasses any of the above** — Part A §I.5's structural rule
   applies to the first-push guard, the location-mapping requirement, and
   every guard above; no feature flag or setting combination may skip
   them **[Accepted — Part A §I.5]**.

### A.13 Inventory job types

Per Part A §A.5.2 (domain modules register job types against the fixed
job-source list, Part A §D.2), `shopify_connector_inventory` registers, at
blueprint level **[Blueprint proposal]**:

- `inventory_first_push` — the guarded, confirmed first Odoo→Shopify
  write for a given mapped location pair (§A.5); maps to the core
  `export_preview_dry_run` job source for its preview step, and to
  `manual_sync` once confirmed.
- `inventory_push` — an ongoing Odoo→Shopify quantity write for an
  already-first-pushed inventory-level binding, any source
  (`webhook`/`scheduled_sync`/`manual_sync`/`event-driven enqueue`/
  `reconciliation`).
- `inventory_baseline_import` — the one-time, controlled Shopify → Odoo
  baseline import (§A.6), source `manual_sync` or `setup_readiness_check`-
  adjacent (exact source classification: **[Open question —
  implementation planning]**).
- `inventory_reconciliation_check` — the reconciliation-pass verification
  described in §A.7, distinct from a fresh push.

Exact job/log Odoo model shape: **[Open question — MBQ-19, unchanged,
shared with every domain]**.

### A.14 Inventory logs, errors, retry, and manual-review touchpoints

Every inventory job flows through the Part A §D job/log/error abstraction
— no parallel inventory-specific error system is created (Part A §K.2;
RA-013). Headline touchpoints, consolidated in §D below:

- **`inventory location missing`** — no mapped Shopify Location for the
  target Odoo location (§A.2/§A.9).
- **`ambiguous match`** — multiple plausible mapping candidates, or a
  first-push item with more than one plausible SKU/variant candidate.
- **`mapping missing`** — the underlying product-variant binding is
  absent (§A.11).
- **`destructive-write guard blocked`** — not directly applicable to
  ordinary inventory pushes (compare-and-set writes are not "destructive"
  in the product-export sense), but **does** apply to the first-push guard
  itself, which is structurally a confirmation-required guard of the same
  shape (Part A §D.5.4/§D.8) even though its dedicated class is the
  first-push guard concept itself, not a generic destructive-write
  finding — **[Blueprint proposal]** the first-push guard's unmet-
  confirmation state routes as its own confirmation-required case, using
  the existing `inventory location missing`/`ambiguous match` classes
  where the guard's specific blocker is a mapping or match issue, and
  otherwise as a guard-specific "first push not yet confirmed" state that
  is structurally the same as `destructive-write guard blocked` (a
  confirmation-required state, not a new top-level class) — this does
  **not** widen Part A §D.8's six-sub-class vocabulary; it maps the
  first-push-pending condition onto the existing `destructive-write guard
  blocked` sub-class, consistent with Part A §F.1.6's "first-push-pending
  count" dashboard metric already treating first-push as its own
  guard-pending category.
- **`Shopify userErrors/validation`** — a Shopify GraphQL inventory
  mutation returns `userErrors`.
- **`data shape/schema mismatch`** — an unexpected/malformed inventory
  payload shape (e.g. an `INVENTORY_LEVELS_UPDATE` webhook with an
  unrecognized structure).
- **`concurrency/race conflict`** — a compare-and-set write's
  `compareQuantity` no longer matches Shopify's current value (a
  concurrent change happened between read and write) — auto-retry with
  backoff after a fresh read, per Part A §D.5.1.

### A.15 Inventory-specific open questions

See §G for the consolidated proposed-resolved/proposed-partially-resolved/
carried-forward table — **all outcomes below are proposed, pending
DEC-015 acceptance, not final.** Headline: **MBQ-32** (quantity
source/formula) — **proposed partially resolved** this sprint: the
source field/formula is now cited against official Odoo 19.0 source
(§A.4); the aggregation-mechanism and configurable-default sub-questions
stay open, and the row itself stays open until DEC-015 is accepted.
**MBQ-33** (first-push granularity) — ChatGPT decision, **recommendation
proposed** (§A.5), not resolved. **MBQ-34** (ongoing apply-mode) —
ChatGPT decision, **recommendation proposed** (§A.7/§G), not resolved.
**MBQ-36** (mutation choice per trigger) — **proposed partially
resolved**, default direction proposed (§A.13/§G), pending DEC-015.
**MBQ-37** (Shopify inventory webhook topic) — **proposed resolved** this
sprint (§A.9), pending DEC-015 acceptance. **MBQ-38** (first-push
confirmation record schema) — **proposed partially resolved**, concept
fixed (§A.5), pending DEC-015.

---

## B. Fulfillment domain blueprint

### B.1 Module boundary and dependency on core/sale/inventory substrate

`shopify_connector_fulfillment` owns fulfillment/tracking write-back and
the notification guard **[Accepted — DEC-008; DEC-011]**. It depends on
`core` + `sale` only and **never** on `inventory` — it must not read
`inventory`'s Odoo-location ↔ Shopify-Location mapping table
**[Accepted — DEC-008; DEC-010; DEC-011]**. Per the accepted Part A
binding shape (§C.8, MBQ-11), `fulfillment` defines a concrete
**FulfillmentOrder/Fulfillment binding** model extending the core abstract
binding contract, keyed on `(store, Shopify FulfillmentOrder GID)` (and
the Fulfillment GID once created) **[Accepted — DEC-006; DEC-011; Part A
§C.8]**. Exact Odoo model/field names: **[Open question — MBQ-01/02]**.

### B.2 Shopify FulfillmentOrder-based posture (DEC-011)

- **Target:** Shopify FulfillmentOrder-based mutations **exclusively**
  (`fulfillmentCreate`); the legacy Order/Fulfillment endpoints are
  **never** used (**RA-022**, unweakened) **[Accepted — DEC-011]**.
- **Shopify IDs stored/fetched:** Order GID (existing `sale` order
  binding, Part B §C.1), FulfillmentOrder GID(s), Fulfillment GID once
  created **[Accepted — DEC-011]**.
- **A FulfillmentOrder is scoped to one Shopify Location**; Phase 1
  targets the single-fulfillment-location case; a mismatch or
  multi-location spread routes to manual review (§B.8)
  **[Accepted — DEC-011]**.

### B.3 Odoo `stock.picking` trigger posture (DEC-011)

- **Source:** a validated `stock.picking` (delivery order) — the
  **Validate** action is the trigger. Each validated picking, **including
  a backorder-split picking**, is its own fulfillment event
  **[Accepted — DEC-011]**.
- **Invoice/payment state is not a fulfillment trigger condition**
  (DEC-003 Domain 9 separation of financial evidence from operational
  actions) **[Accepted — DEC-003; DEC-011]**.
- **[Official fact]** Odoo 19.0 documentation confirms delivery
  processing is organised into named workflows — **One-step**,
  **Two-step**, and **Three-step** receipt/delivery — and that on
  sales-order confirmation a delivery order is generated, accessible via
  the order's "Delivery" smart button; the three-step flow explicitly
  separates **pick → pack → ship**. Sources:
  `https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/daily_operations/delivery_three_steps.html`,
  `.../receipts_delivery_two_steps.html`, `.../receipts_delivery_one_step.html`,
  access date **2026-07-02** (propagated from `ar007-ar008-evidence-refresh.md`).
  **[Blueprint proposal]** regardless of which workflow (one/two/three
  -step) a merchant uses, the fulfillment trigger is the **final**
  `stock.picking` in the chain whose **Validate** action represents goods
  actually leaving the warehouse (the "ship" step in a three-step flow,
  the single delivery step in a one-step flow) — an intermediate pick/pack
  step's validation does **not** itself trigger a Shopify fulfillment.
  Exact per-workflow trigger-picking identification mechanism: **[Open
  question — implementation planning]**.

### B.4 Matching order, FulfillmentOrder, line, quantity, and location

- **Matching chain:** Odoo picking's sale order → bound Shopify order
  (via the `sale` order binding, Part B §C.1) → that order's open
  FulfillmentOrder(s) → matched line items/quantities via
  `lineItemsByFulfillmentOrder` **[Accepted — DEC-011]**.
- **[Official fact, restated from DEC-011/`ar007-ar008-evidence-refresh.md`]**
  `FulfillmentInput.lineItemsByFulfillmentOrder` — "Pairs of
  `fulfillment_order_id` and `fulfillment_order_line_items` that represent
  the fulfillment order line items that have to be fulfilled for each
  fulfillment order." If line items are omitted for a pair, all items
  associated with that fulfillment order are fulfilled. Source:
  `shopify.dev/docs/api/admin-graphql/latest/input-objects/FulfillmentInput`,
  access date **2026-07-02**.
- **An unmatched picking is never fulfilled by guess** — it blocks for
  manual review (**RA-023**, unweakened) **[Accepted — DEC-011]**.
- **Product/order binding prerequisite (§B.1 above; also depends on Part
  B):** matching requires both the order binding (`sale`, Part B §C.1)
  and, at the line-item level, the product-variant binding (`product`,
  Part B §A.1) to already resolve the Odoo picking's stock move lines
  back to the correct Shopify order line items — a picking whose lines
  cannot be resolved to Shopify order line items (e.g. a stale/never-
  exported product binding) is unmatched and blocks for manual review,
  the same `mapping missing`/`failed_retryable` routing as Part B §C.5's
  unmatched-product-line rule, applied here to the fulfillment side
  **[Blueprint proposal, extending Part B §C.5's routing pattern]**.

### B.5 Tracking number/carrier/url handling (proposing to resolve MBQ-39)

- **[Official fact — proposing to resolve MBQ-39, pending DEC-015, accessed 2026-07-03]** Odoo
  19.0's `stock_delivery` module (Inventory Delivery Management) defines,
  on `stock.picking`:

  ```python
  carrier_id = fields.Many2one("delivery.carrier", string="Carrier",
      domain="[('id', 'in', allowed_carrier_ids)]", check_company=True)
  carrier_tracking_ref = fields.Char(string='Tracking Reference', copy=False)
  carrier_tracking_url = fields.Char(string='Tracking URL',
      compute='_compute_carrier_tracking_url')

  @api.depends('carrier_id', 'carrier_tracking_ref')
  def _compute_carrier_tracking_url(self):
      for picking in self:
          picking.carrier_tracking_url = picking.carrier_id.get_tracking_link(
              picking) if picking.carrier_id and picking.carrier_tracking_ref else False
  ```

  Source:
  `https://github.com/odoo/odoo/blob/19.0/addons/stock_delivery/models/stock_picking.py`,
  access date **2026-07-03**, access status **Accessible**.
- **[Blueprint proposal, new consideration surfaced by this fact]**
  these fields belong to the **`stock_delivery`** Odoo module (an
  installable Inventory app module distinct from the base `stock`
  module), **not** to core `stock`. Whether `shopify_connector_
  fulfillment` requires `stock_delivery` (or the lighter `delivery`
  module) as an Odoo dependency, and what tracking write-back does if a
  merchant's database does not have it installed, is a genuinely new
  question this sprint surfaces — **not decided here**; tracked as
  **[Open question — MBQ-60, new]**.
- **Shopify side [Accepted — DEC-011]:** tracking may be set at
  fulfillment creation (`fulfillmentCreate`) or updated afterward
  (`fulfillmentTrackingInfoUpdate`); a tracking-only update never creates
  a second fulfillment.
- **Field mapping (blueprint direction, not implementation-final)
  [Blueprint proposal]:** `carrier_tracking_ref` maps to Shopify's
  tracking number; `carrier_id` (resolved to a carrier/company name)
  maps to Shopify's tracking company; `carrier_tracking_url` (Odoo's
  computed tracking URL, when the carrier integration supports it) maps
  to Shopify's tracking URL, with Shopify's own tracking-URL-guessing
  behavior as a fallback if Odoo's computed URL is unavailable for a given
  carrier — exact mapping/precedence: **[Open question — implementation
  planning]**.

### B.6 Customer notification default posture (DEC-007 §5/DEC-011)

- **Default: no notification** unless explicitly enabled/confirmed by the
  operator **[Accepted — DEC-007 §5; DEC-011; RA-009]**, grounded in
  Shopify's own `FulfillmentInput.notifyCustomer` defaulting to `false`
  and `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` sending no
  notification if left blank (already-verified facts, DEC-007).
- **Configuration surface:** a global, per-store default at minimum
  (Part A §B.7); per-order override granularity remains **[Open question
  — MBQ-41]**.
- **Persistence:** the notification decision is persisted on the
  job/log record **at enqueue time**, never re-read at retry time — a
  retry preserves the original decision (Part A §D.13)
  **[Accepted — DEC-011]**.
- **Audit:** every fulfillment log entry records whether notification was
  requested or suppressed; a write-back that never reached Shopify never
  sends a notification **[Accepted — DEC-011]**.
- **MBQ-41 recommendation [Recommendation, ChatGPT decision, not resolved
  here]:** this sprint proposes that a **global/per-store** default is
  **sufficient for Phase 1 MVP** and that a **per-order override** is
  deferred to a later phase — grounded in the observation that DEC-003's
  MVP scope does not name per-order notification control as a required
  capability, and the store-level default already satisfies DEC-007 §5's
  "visible and operator-controllable" requirement. This is a
  recommendation for ChatGPT's decision, not a self-accepted resolution.

### B.7 Partial fulfillment, backorder, cancellation, return, refund, and multi-package posture

- **Partial/backorder [Accepted — DEC-011]:** fulfill exactly the
  delivered quantities of one validated picking via
  `lineItemsByFulfillmentOrder`; a partially-delivered order with a
  resulting backorder picking is handled as **two independent, sequential
  fulfillment events** — Shopify's FulfillmentOrder model natively
  supports this.
- **[Official fact — proposing to partially resolve MBQ-40, pending DEC-015, accessed 2026-07-03]** Odoo
  19.0's `stock.picking` model defines a `backorder_id` field linking a
  split picking back to its origin, plus a reverse `backorder_ids` field:

  ```python
  backorder_id = fields.Many2one(
      'stock.picking', 'Back Order of',
      copy=False, index='btree_not_null', readonly=True,
      check_company=True,
      help="If this shipment was split, then this field links to the shipment which contains the already processed part.")
  backorder_ids = fields.One2many('stock.picking', 'backorder_id', 'Back Orders')
  ```

  The `_create_backorder` method generates the new picking when a
  transfer is partially completed, and the new picking's `backorder_id`
  points back to the original. Source:
  `https://github.com/odoo/odoo/blob/19.0/addons/stock/models/stock_picking.py`,
  access date **2026-07-03**, access status **Accessible**.
- **[Blueprint proposal, applying the official fact above]** each picking
  in a `backorder_id` chain is matched and fulfilled **independently**
  through the ordinary matching flow (§B.4) — the backorder linkage is
  used only to label/relate the two fulfillment events in the log/audit
  trail (Part A §D.10), never to merge them into one Shopify fulfillment
  operation or to infer a quantity without re-matching via
  `lineItemsByFulfillmentOrder`. The exact wizard-level UX/copy Odoo shows
  when creating a backorder for a **delivery** order specifically (as
  opposed to a receipt) was not independently re-verified this sprint —
  carried forward from `ar007-ar008-evidence-refresh.md`'s existing open
  item, **[Open question — MBQ-40, partially resolved — field-level
  linkage now cited; wizard-level behavior/copy for deliveries remains
  open]**.
- **Cancellation, return, refund [Accepted — DEC-003; unchanged,
  deferred]:** order cancellations, returns, and refunds all remain
  **deferred** — this sprint does not build any cancellation/return/
  refund-triggered fulfillment reversal, adjustment, or reconciliation
  logic. A cancelled Odoo picking (before validation) simply never
  becomes a fulfillment event; a Shopify-side fulfillment cancellation or
  a return/refund affecting an already-fulfilled order is **out of
  scope**, mirroring Part B §C.12's unchanged order-edit/refund deferral.
  **[Official fact, surfaced by this sprint's webhook-topic verification,
  §B.11]** Shopify's `WebhookSubscriptionTopic` enum includes
  `FULFILLMENT_ORDERS_CANCELLATION_REQUEST_SUBMITTED/ACCEPTED/REJECTED`
  and `FULFILLMENT_ORDERS_CANCELLED` topics — these exist on the Shopify
  side regardless of whether the connector subscribes to them; this
  sprint does **not** propose subscribing to or acting on them (see
  MBQ-61, new).
- **Multi-package fulfillment [Accepted — DEC-003; DEC-011; unchanged,
  deferred]:** true multi-package "Put-in-Pack" shipment splitting within
  one delivery event, and multi-location fulfillment automation
  (C-FUL-02), remain deferred to a later phase — an existing accepted
  deferral, not a new rejection.

### B.8 Multi-location / fulfillment-location mismatch guard (proposing a direction for MBQ-42/MBQ-43)

- **Ownership principle [Accepted — DEC-008/DEC-010/DEC-011]:**
  `shopify_connector_fulfillment` never depends on `inventory`'s
  Odoo-location ↔ Shopify-Location mapping table; it uses (a) a live
  Shopify FulfillmentOrder `assignedLocation` read, and/or (b) the core
  Shopify Location reference (§A.2), instead.
- **[Official fact, restated from DEC-011/`ar007-ar008-evidence-refresh.md`]**
  `FulfillmentOrder.assignedLocation` (type
  `FulfillmentOrderAssignedLocation!`, non-null): "The fulfillment order's
  assigned location. This is the location where the fulfillment is
  expected to happen." This can change while the fulfillment order is
  `OPEN`/`SCHEDULED`/`ON_HOLD`. Source:
  `shopify.dev/docs/api/admin-graphql/latest/objects/FulfillmentOrder`,
  access date **2026-07-02**.
- **[Blueprint proposal, proposing to partially resolve MBQ-42, pending DEC-015]** the blueprint-level
  mechanism: at the time a fulfillment operation is about to be created, a
  **live** `assignedLocation` read is fetched and treated as
  **authoritative** for that specific operation. The core Shopify Location
  reference (§A.2), if populated, is used only for **naming/display**
  (showing a human-readable location name in the preview/log, Part A §B.4)
  and as a **mismatch-detection aid** (flagging when a picking's expected
  Odoo-side fulfillment location does not correspond to any known Shopify
  Location) — it never overrides the live read, and it never substitutes
  for the live read when the two are unavailable/stale. A mismatch (the
  picking's expected location does not correspond to the FulfillmentOrder's
  live `assignedLocation`) routes to manual review — never auto-guessed —
  reusing the existing `ambiguous match`/`inventory location missing`-
  adjacent pattern; because this is a fulfillment-domain concern (not an
  inventory write), **[Blueprint proposal]** this sprint proposes the
  fulfillment-side equivalent surfaces as a new use of the existing
  `ambiguous match` class (a location mismatch is a specific case of "this
  operation's target is ambiguous/inconsistent with expectation"), **not**
  a new top-level error class — Part A §D.4's fixed registry is not
  widened. This direction is **proposed, pending ChatGPT acceptance**, not
  self-accepted — MBQ-42 stays open at the "ChatGPT accepts this
  mechanism" level even though the mechanism itself is now proposed in
  detail.
- **[Blueprint proposal, proposing to partially resolve MBQ-43, pending DEC-015]** core Location
  reference cache policy: refreshed on setup-readiness checks and on the
  same reconciliation cadence shared with other domains (MBQ-17); for any
  **specific** fulfillment operation, the live `assignedLocation` read
  always wins over the cached reference — the cache is never treated as
  authoritative for an in-flight operation, only for naming/display
  between operations. Exact refresh cadence/mechanism (push-based via
  webhook vs. pull-based on a schedule): **[Open question — MBQ-43,
  proposed partially resolved, pending DEC-015 — precedence rule
  proposed; cadence/mechanism open]**.
- **Phase 1 scope:** single-fulfillment-location matching; genuinely
  multi-location fulfillment (more than one Shopify Location fulfilling
  one order) is deferred (C-FUL-02, DEC-003) **[Accepted — DEC-011]**.

### B.9 Idempotency and duplicate prevention for fulfillment operations

- **Binding key:** `(store, Shopify FulfillmentOrder GID)` and the
  Fulfillment GID once created (§B.1) **[Accepted — DEC-011]**.
- **Operation-level idempotency key (conceptual, exact schema open)
  [Accepted — DEC-011]:**

  > `(store, operation type, picking_id, Shopify target ID where known,
  > payload version/hash)`

  e.g. `(store, fulfillment_create, picking_id, fulfillment_order_gid,
  payload_hash)` and `(store, tracking_update, picking_id, fulfillment_gid,
  payload_hash)` — distinguishing a tracking update from fulfillment
  creation, and supporting a safe **corrected** tracking update (a
  different payload hash for the same picking/Fulfillment) without
  bypassing the ambiguous-outcome rule (§B.10). Exact field names/types:
  **[Open question — MBQ-20 (shared, generalized key) — the
  fulfillment-specific conceptual shape is already fixed by DEC-011 and
  restated here, not newly decided]**.
- **Both required together:** the operation-level idempotency key
  (prevents connector-side re-processing of the *same* operation) and the
  verification-read rule (§B.10, prevents a Shopify-side double
  fulfillment on ambiguous outcomes) are required together — neither
  alone is sufficient **[Accepted — DEC-011]**.

### B.10 Retry and error handling using Part A classes

- **`fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` are not on
  Shopify's 17-mutation `@idempotent` list** — any ambiguous-outcome
  failure (timeout/connection loss with unknown result) falls under
  DEC-009's ambiguous-outcome rule: no blind retry (**RA-014**); a safe
  verification read (re-query the order's Fulfillments/FulfillmentOrder
  status) before retry, or `blocked_manual_review` if inconclusive
  **[Accepted — DEC-009; DEC-011]**.
- **Serialization guard [Accepted — DEC-011]:** operations against the
  same `(store, picking, Shopify target)` are serialized while a prior
  operation against that target is unresolved — a corrected tracking
  update or a new fulfillment operation must first verify/match current
  Shopify state or remain blocked/manual-review until the earlier
  operation resolves. Exact mechanism (queue-level lock / DB constraint /
  job-state check): **[Open question — MBQ-21, shared with every
  domain]**.
- **Error-class mapping (consolidated in §D):** `mapping missing`
  (unresolved order/product binding, §B.4), `ambiguous match` (unmatched
  picking, §B.4; location mismatch, §B.8), `binding conflict`
  (stale/recreated FulfillmentOrder/Fulfillment GID), `fulfillment
  notification confirmation missing` (a store/order requiring explicit
  notification confirmation that has not been given, DEC-009's dedicated
  class), `Shopify userErrors/validation`, `data shape/schema mismatch`.

### B.11 Webhook/reconciliation posture

- **Layered, never webhook-only [Accepted — DEC-005; DEC-011]:**
  fulfillment creation is Odoo-triggered (§B.3), but Shopify-side
  fulfillment/FulfillmentOrder state changes may still need to be
  observed for reconciliation/drift detection.
- **[Official fact — new this sprint, accessed 2026-07-03]** Shopify's
  `WebhookSubscriptionTopic` enum includes, beyond the already-cited
  `ORDERS_CREATE`/`ORDERS_UPDATED` (Part B §C.2): `FULFILLMENTS_CREATE`
  ("Occurs whenever a fulfillment is created"), `FULFILLMENTS_UPDATE`
  ("Occurs whenever a fulfillment is updated"), and a large
  `FULFILLMENT_ORDERS_*` topic family covering hold placement/release,
  cancellation-request lifecycle, merges, splits, moves, reschedules, and
  routing completion (e.g. `FULFILLMENT_ORDERS_PLACED_ON_HOLD`,
  `FULFILLMENT_ORDERS_HOLD_RELEASED`, `FULFILLMENT_ORDERS_MERGED`,
  `FULFILLMENT_ORDERS_SPLIT`, `FULFILLMENT_ORDERS_MOVED`,
  `FULFILLMENT_ORDERS_RESCHEDULED`). Source:
  `https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic`,
  access date **2026-07-03**, access status **Accessible**.
- **[Blueprint proposal]** this sprint does **not** propose subscribing
  to the full `FULFILLMENT_ORDERS_*` lifecycle family — Phase 1's
  reconciliation backstop (a scheduled pass re-verifying a fulfillment
  binding's last-known Shopify state) already covers drift detection
  without requiring every lifecycle webhook. Whether/how the connector
  should react to a **hold** being placed on a FulfillmentOrder (which
  would mean an Odoo-triggered `fulfillmentCreate` call is rejected or
  delayed by Shopify even though the picking was validated) is a
  genuinely new question this sprint surfaces but does not resolve —
  tracked as **[Open question — MBQ-61, new]**.
- **Reconciliation:** the same DEC-005 layered-sync reconciliation pass
  that covers other domains also covers fulfillment — re-verifying a
  previously-created Fulfillment's tracking/state against Shopify's
  current state and flagging drift, using the existing error-class
  registry, not a new mechanism **[Accepted — DEC-005; Blueprint proposal
  for applying it to fulfillment explicitly]**.

### B.12 Fulfillment job types

Per Part A §A.5.2, `shopify_connector_fulfillment` registers, at
blueprint level **[Blueprint proposal]**:

- `fulfillment_create` — the FulfillmentOrder-matched, guarded creation of
  a Shopify fulfillment from a validated `stock.picking`.
- `fulfillment_tracking_update` — a tracking-only update to an existing
  Fulfillment (`fulfillmentTrackingInfoUpdate`), including a corrected
  tracking update.
- `fulfillment_reconciliation_check` — the reconciliation-pass
  verification described in §B.11, distinct from a fresh creation.

Exact job/log Odoo model shape: **[Open question — MBQ-19, unchanged,
shared with every domain]**.

### B.13 Fulfillment logs, errors, retry, and manual-review touchpoints

Every fulfillment job flows through the Part A §D job/log/error
abstraction — no parallel fulfillment-specific error system is created
(Part A §K.2; RA-013). User-facing log shape restated from DEC-011
**[Accepted]**: every fulfillment log entry shows the related sale order,
picking, Shopify order, Shopify FulfillmentOrder/Fulfillment ID, tracking
number/carrier, and the notification setting (requested/suppressed);
blocked/failed entries carry a human-readable reason and a suggested next
action; no raw stack trace as the primary UX.

### B.14 Fulfillment-specific open questions

See §G for the consolidated table — **all outcomes below are proposed,
pending DEC-015 acceptance, not final.** Headline: **MBQ-39** (tracking
field source) — **proposed resolved** this sprint via official Odoo 19.0
source citation (§B.5), pending DEC-015 acceptance; new residual question
surfaced (MBQ-60, `stock_delivery` module dependency). **MBQ-40**
(backorder linkage) — **proposed partially resolved** (field-level
linkage cited; wizard-level delivery-specific behavior/copy stays open),
pending DEC-015. **MBQ-41** (notification-UI granularity) — ChatGPT
decision, **recommendation proposed** (§B.6), not resolved. **MBQ-42**
(location-confirmation mechanism) — **proposed partially resolved**,
mechanism proposed (§B.8), pending ChatGPT acceptance of DEC-015.
**MBQ-43** (Location reference cache policy) — **proposed partially
resolved**, precedence rule proposed (§B.8), cadence open, pending
DEC-015.

---

## C. Cross-domain sequencing and dependency rules (inventory/fulfillment/core)

1. **Fulfillment never depends on inventory, structurally** — restated
   from Part A §K.5/§K.6/§K.7 and DEC-008/010/011, checked and not
   violated anywhere in §A/§B above: `fulfillment` never reads
   `inventory`'s location-mapping table; both use the core Shopify
   Location reference and/or live Shopify reads independently
   **[Accepted — DEC-008; DEC-010; DEC-011]**.
2. **Both resolve product/variant bindings through `product`, never
   duplicated** (Part A §K.9) — inventory's per-location identity layers
   on the product-variant binding (§A.11); fulfillment's line matching
   resolves through the order binding (`sale`) and, transitively, the
   product-variant binding, without either domain re-implementing
   product-matching logic **[Accepted — DEC-008]**.
3. **Order import before fulfillment matching.** A picking cannot be
   matched to a FulfillmentOrder until the underlying sale order has an
   existing order binding (Part B §C.1) — an order still blocked on
   product/customer resolution (Part B §C.5/§C.6) has no fulfillable
   picking yet in the ordinary flow, since Odoo would not normally have
   validated a delivery for an order that has not yet been created/
   confirmed **[Blueprint proposal, restated from Part B §D.1/§D.2's
   cross-domain sequencing pattern]**.
4. **Inventory push and fulfillment creation are independent, siblings.**
   Neither domain gates the other — an inventory push for a product does
   not wait on any fulfillment event, and a fulfillment creation does not
   wait on an inventory push having occurred for the same product (the
   product's product-variant binding, not its inventory-level binding, is
   the only shared prerequisite, §A.11/§B.4) **[Blueprint proposal,
   restated from DEC-008's sibling-module structure]**.
5. **Manual review if mapping/matching is missing.** Uniformly routed
   through the existing Part A §D.4 error-class registry (§A.14/§B.13) —
   no domain-specific manual-review mechanism is invented for either
   domain.
6. **Reconciliation backstop through accepted core substrate.** Inventory
   and fulfillment reconciliation both use the same DEC-005 layered-sync
   reconciliation mechanism (Part A §D.1) as product/customer/order
   (Part B §D.5) — no new mechanism.
7. **Which actions are manual, scheduled, webhook-driven, or
   reconciliation-driven:**

   | Domain action | Manual | Scheduled | Webhook | Event-driven | Reconciliation |
   | --- | --- | --- | --- | --- | --- |
   | Inventory baseline import (one-time) | Yes | No | No | No | No |
   | Inventory push (ongoing) | Yes (manual sync) | Yes | Candidate (`INVENTORY_LEVELS_UPDATE`, drift-detection only) | Yes (Odoo stock move) | Yes |
   | Inventory reconciliation check | No (system-triggered) | Yes | No | No | Yes (this *is* the reconciliation action) |
   | Fulfillment creation | No (Odoo-triggered by picking validation) | No | No | Yes (`stock.picking` Validate) | No |
   | Fulfillment tracking update | Yes (explicit action) | No | No | Yes (Odoo tracking field change, if a later controlled trigger accepts it — **[Open question — implementation planning]**) | No |
   | Fulfillment reconciliation check | No (system-triggered) | Yes | No | No | Yes (this *is* the reconciliation action) |
   | Manual-review resolution (either domain) | Yes (Reviewer role, Part A §J.2) | No | No | No | No |

   **[Blueprint proposal, synthesizing §A/§B's individual trigger
   statements into one table, mirroring Part B §D.7]**.

---

## D. Job/log/error/retry usage through core

No inventory- or fulfillment-specific job, log, error, or retry system is
introduced — every job type registered in §A.13/§B.12 flows through the
single Part A §D abstraction (queue posture §D.1, job sources §D.2, job
states §D.3, the fixed error-class registry §D.4, retry-eligibility
concept §D.5, operation-level idempotency §D.6, ambiguous-outcome/
serialization rules §D.7, manual-review state §D.8, cancellation/supersede
§D.9, audit requirements §D.10, log shapes §D.11–§D.12, retry safety rules
§D.13) **[Accepted — DEC-013; Blueprint proposal only for the
domain-specific job-type names themselves, §A.13/§B.12]**. This satisfies
Part A §K.2 ("no domain module may implement its own job/queue, log,
error-class registry, or binding-audit system," RA-013 binding) — checked
and not violated by this sprint.

Consolidated error-class/retry mapping (no new error class is added to
the fixed Part A §D.4 16-class registry):

| Error class (Part A §D.4) | Inventory instance | Fulfillment instance | Retry posture (Part A §D.5) |
| --- | --- | --- | --- |
| Shopify throttling/rate-limit | Any inventory mutation/query | Any fulfillment mutation/query | Auto-retry with backoff |
| Shopify temporary/server/network | Transient inventory API failure | Transient fulfillment API failure | Auto-retry (reads/`@idempotent`); ambiguous-outcome rule otherwise |
| Shopify permission/scope/auth | Missing `read_inventory`/write-inventory scope | Missing fulfillment read/write scope | Manual fix then retry |
| Shopify userErrors/validation | Invalid quantity/location payload | Invalid fulfillment/tracking payload | Manual fix then retry |
| Odoo validation/configuration | Odoo-side stock validation failure | Odoo-side picking validation failure | Manual fix then retry |
| Mapping missing | Unresolved product-variant binding (§A.11) | Unresolved order/product binding for a picking's lines (§B.4) | Manual fix then retry |
| Ambiguous match | Multiple mapping candidates for a location (§A.9); ambiguous first-push item | Unmatched picking (§B.4, RA-023); location mismatch (§B.8) | Operator confirmation required |
| Binding conflict | Stale/recreated Shopify Location or inventory-item ID | Stale/recreated FulfillmentOrder/Fulfillment GID | Operator confirmation required |
| Duplicate risk | — (not applicable; inventory writes update, never create duplicate records) | — (not applicable; fulfillment matching prevents duplicate fulfillment by design, §B.4/§B.9) | n/a to this sprint |
| Destructive-write guard blocked | First-push guard not yet confirmed (§A.5/§A.14) | — (no destructive fulfillment write; fulfillment creation is additive) | Operator confirmation required |
| **Inventory location missing** | **§A.2/§A.9 mapping-missing case** | — | Operator confirmation required |
| **Fulfillment notification confirmation missing** | — | **§B.6 notification-confirmation case** | Operator confirmation required |
| Financial total mismatch | — (not applicable) | — (not applicable) | n/a to this sprint |
| Data shape/schema mismatch | Malformed inventory-webhook/API payload | Malformed fulfillment/FulfillmentOrder payload | Manual fix then retry |
| Concurrency/race conflict | Compare-and-set mismatch (§A.14) | Two concurrent writes to same FulfillmentOrder | Auto-retry with backoff |
| Unknown/system error | Any unclassified failure | Any unclassified failure | Single safety-net auto-retry, then human |

**Only** "Operator confirmation required" rows are `blocked_manual_review`
cases (Part A §D.5.4/§D.8's six confirmation-required sub-classes — all
six are now relevant across the connector once inventory/fulfillment are
included: ambiguous match, binding conflict, duplicate risk,
destructive-write guard blocked, inventory location missing, fulfillment
notification confirmation missing); "Manual fix then retry" rows sit in
`failed_retryable` (§D.3); this document does not widen Part A §D.8's
six-sub-class vocabulary **[Accepted — DEC-013; Blueprint proposal for
the consolidated table, mirroring Part B §I's format and discipline]**.

## E. Binding/dedup usage through core

The inventory-level binding and the FulfillmentOrder/Fulfillment binding
are each a **concrete model extending the core abstract binding contract**
(Part A §C.8) — store-scoped uniqueness (§C.2 of Part A), explicit GID +
Odoo record identity (§C.3), status/audit fields (§C.4), the fixed
match-key priority per domain shape (§C.5 — inventory keys on `(store,
inventory_item_id, location_id)`, not a match-key search at all, since
identity is structurally derived from the already-resolved product-variant
binding + location mapping, not searched for; fulfillment keys on `(store,
FulfillmentOrder GID)`, resolved via the matching chain in §B.4, not a
search either), and stale/recreated handling (§C.6) apply uniformly. No
new binding shape, no polymorphic table, and no per-domain audit variant
is introduced — this sprint reuses MBQ-11's accepted direction (Part A
§C.8, DEC-013) without modification, adding exactly **two** new concrete
binding models to the model-count, both within DEC-013's accepted
"one concrete binding model per synchronized root entity" granularity
bound (inventory level; FulfillmentOrder/Fulfillment) — no additional
sub-entity binding model is proposed **[Accepted — DEC-013]**.

## F. Newly verified official facts this sprint (index)

All accessed **2026-07-03**, access status **Accessible** unless noted.
Full citations appear inline at first use above; this is a consolidated
index for review convenience, per `CLAUDE.md` §7:

1. Shopify `WebhookSubscriptionTopic` enum — `INVENTORY_LEVELS_UPDATE`,
   `INVENTORY_LEVELS_CONNECT`, `INVENTORY_LEVELS_DISCONNECT` (§A.9).
2. Shopify `WebhookSubscriptionTopic` enum — `FULFILLMENTS_CREATE`,
   `FULFILLMENTS_UPDATE`, and the `FULFILLMENT_ORDERS_*` topic family
   (§B.11).
   Source (1, 2): `https://shopify.dev/docs/api/admin-graphql/latest/enums/WebhookSubscriptionTopic`.
3. Odoo 19.0 `product.product.free_qty` field definition and
   `_compute_quantities_dict` formula (§A.4). Source:
   `https://github.com/odoo/odoo/blob/19.0/addons/stock/models/product.py`.
4. Odoo 19.0 `stock.quant.quantity`/`reserved_quantity`/
   `available_quantity` field definitions and compute method (§A.4).
   Source: `https://github.com/odoo/odoo/blob/19.0/addons/stock/models/stock_quant.py`.
5. Odoo 19.0 `stock.picking.backorder_id`/`backorder_ids` field
   definitions (§B.7). Source:
   `https://github.com/odoo/odoo/blob/19.0/addons/stock/models/stock_picking.py`.
6. Odoo 19.0 `stock_delivery` module `stock.picking.carrier_id`/
   `carrier_tracking_ref`/`carrier_tracking_url` field definitions and
   compute method (§B.5). Source:
   `https://github.com/odoo/odoo/blob/19.0/addons/stock_delivery/models/stock_picking.py`.

**Verification method note:** facts 3–6 were verified against the
official `odoo/odoo` GitHub repository's `19.0` branch — the same
verification method RB-14 Part 2 used for `ir.cron`/`ir.model.data`
source-code facts, and consistent with treating Odoo's own published
source code as a Tier-1 official source for exact field names not covered
by Odoo's user-facing documentation pages (which describe reporting
concepts, not ORM field names). No competitor/vendor/forum source was
used for any of the six facts above. No fact in this list was found
inconclusive; where a related question remains genuinely open (e.g. the
`stock_delivery` module-dependency question, or delivery-specific
backorder-wizard copy), it is routed to the open-question register (§G)
rather than asserted.

## G. Open questions: proposed resolved / proposed partially resolved / carried forward / new

Full register:
[`master-blueprint-open-questions.md`](./master-blueprint-open-questions.md)
§5 (inventory) / §6 (fulfillment). **This sprint's outcomes are proposed
only, pending ChatGPT's review and acceptance of DEC-015 — no row below
is final, and every row remains formally `open` in the register until
DEC-015 is accepted:**

| MBQ | Sprint C outcome (proposed, pending DEC-015 acceptance) | Where |
| --- | --- | --- |
| MBQ-32 | **Proposed partially resolved** — exact Odoo ORM source/formula identified and cited (`product.product.free_qty`; equivalently `stock.quant.available_quantity` = `quantity − reserved_quantity`); the aggregation-mechanism and configurable-default sub-questions remain implementation planning | §A.4 |
| MBQ-33 | **Carried forward, open** — ChatGPT decision; Sprint C proposes a recommendation (guard fires per mapped Odoo-location↔Shopify-Location pair) | §A.5 |
| MBQ-34 | **Carried forward, open** — ChatGPT decision; Sprint C proposes a recommendation (review-then-apply by default for Phase 1, consistent with DEC-003's "auto-apply not accepted as default") | §A.7 |
| MBQ-35 | **Carried forward, open, unchanged** — no new evidence this sprint changes the existing `available`-default / `on_hand`-needs-justification / `committed`-never posture | §A.4/§A.12 |
| MBQ-36 | **Proposed partially resolved** — direction proposed: `inventorySetQuantities` (compare-and-set) as the default for all trigger types; exact per-trigger choice/batching/error handling remains implementation planning | §A.13 |
| MBQ-37 | **Proposed resolved** — exact Shopify webhook topic confirmed and cited (`INVENTORY_LEVELS_UPDATE`, plus `INVENTORY_LEVELS_CONNECT`/`DISCONNECT`); fact verification is complete, but the row formally closes only on DEC-015 acceptance | §A.9 |
| MBQ-38 | **Proposed partially resolved** — blueprint-level confirmation-record concept fixed (extends Part A guard/audit shape); exact schema/fields remain implementation planning | §A.5 |
| MBQ-39 | **Proposed resolved** — exact Odoo tracking field source confirmed and cited (`stock.picking.carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id`, `stock_delivery` module); fact verification is complete, but the row formally closes only on DEC-015 acceptance | §B.5 |
| MBQ-40 | **Proposed partially resolved** — exact backorder-linkage field confirmed and cited (`stock.picking.backorder_id`/`backorder_ids`); delivery-specific wizard UX/copy remains open (carried from `ar007-ar008-evidence-refresh.md`) | §B.7 |
| MBQ-41 | **Carried forward, open** — ChatGPT decision; Sprint C proposes a recommendation (global/per-store default sufficient for Phase 1 MVP; per-order override deferred) | §B.6 |
| MBQ-42 | **Proposed partially resolved** — blueprint-level mechanism proposed (live `assignedLocation` read authoritative per-operation; core Location reference for naming/mismatch-detection only); pending ChatGPT acceptance of the mechanism itself | §B.8 |
| MBQ-43 | **Proposed partially resolved** — precedence rule proposed (live read always wins over cache for a specific operation); exact refresh cadence/mechanism remains open | §B.8 |

**New rows added (next available number after MBQ-59):**

| MBQ | Open question | Source | Why it matters | Decision owner | Blocks implementation |
| --- | --- | --- | --- | --- | --- |
| MBQ-60 | Whether `shopify_connector_fulfillment` requires the Odoo `stock_delivery` (or `delivery`) module as a dependency for the `carrier_tracking_ref`/`carrier_tracking_url`/`carrier_id` fields this sprint identifies (§B.5), and what tracking write-back does if a merchant's database does not have that module installed | Sprint C (`master-blueprint-inventory-fulfillment.md` §B.5), newly surfaced by this sprint's official-doc verification — not previously discussed by DEC-008's module family or DEC-011 | These fields live in an installable Odoo module distinct from core `stock`; if that module is not installed, the connector's tracking write-back has no field to write to, and DEC-008's module-family dependency list did not previously name any standard Odoo module dependency beyond core/base | ChatGPT (whether to require it) + Implementation planning (manifest dependency mechanics) | Yes (fulfillment tracking write-back) |
| MBQ-61 | Whether/how the connector must react to Shopify-side FulfillmentOrder lifecycle events beyond simple creation — holds (`FULFILLMENT_ORDERS_PLACED_ON_HOLD`/`HOLD_RELEASED`), cancellation-request lifecycle, merges, splits, moves, and reschedules — newly confirmed as real Shopify webhook topics this sprint (§B.11) but not discussed by DEC-011 at all | Sprint C (`master-blueprint-inventory-fulfillment.md` §B.11), newly surfaced by this sprint's official-doc verification of the full `WebhookSubscriptionTopic` enum | A FulfillmentOrder placed on hold by Shopify (e.g. a risk/fraud hold) could silently reject or delay an Odoo-triggered `fulfillmentCreate` call if the connector has no visibility into hold state before attempting fulfillment; DEC-011 did not consider these lifecycle events at all | ChatGPT (whether/how to react) + Implementation planning | No for MVP correctness-core fulfillment creation (the existing ambiguous-outcome/manual-review handling already catches a rejected `fulfillmentCreate` call, just without a specific "on hold" reason); Yes if a dedicated hold-aware UX is later required |

**MBQ-33, MBQ-34, MBQ-35, MBQ-41 remain open** — ChatGPT-decision-owner
rows; this sprint's proposals are recommendations, not self-accepted
resolutions. **MBQ-32, MBQ-36, MBQ-37, MBQ-38, MBQ-39, MBQ-40, MBQ-42,
and MBQ-43 also remain formally `open`** in the register — their
"proposed resolved"/"proposed partially resolved" labels above describe
this sprint's proposal, not a final outcome; each becomes final only
if/when ChatGPT accepts DEC-015. **MBQ-60 and MBQ-61 are new, open.** No
MBQ row from any other section (§1–§4, §7–§9) is touched by this sprint.

---

## H. What this does not decide

- No exact Odoo model/field/view/security identifiers for any inventory
  or fulfillment **connector** concept (**MBQ-01/02/03/44**, implementation
  planning) — the Odoo-core/Odoo-module field names cited in §A.4/§B.5/
  §B.7 (`free_qty`, `carrier_tracking_ref`, `backorder_id`, etc.) are
  **existing Odoo fields being read/written**, not connector-proposed
  names, and do not resolve those rows.
- No final GraphQL mutation body or exact batching/error-handling detail
  for inventory writes or fulfillment creation beyond what is explicitly
  cited and verified this sprint (**MBQ-36**, direction proposed only).
- No screen-level UI/UX design, wireframe, or navigation structure (Part
  D, **MBQ-53**, unchanged, not started).
- No resolution of the four ChatGPT-decision-owner rows this sprint
  touches (**MBQ-33, MBQ-34, MBQ-41**) beyond a named recommendation, and
  no resolution of **MBQ-42**'s mechanism-acceptance question beyond a
  proposed mechanism.
- No new Odoo module dependency is authorized (**MBQ-60** is routed as an
  open question, not decided as "required").
- No subscription to, or handling logic for, any `FULFILLMENT_ORDERS_*`
  lifecycle webhook topic beyond creation/tracking (**MBQ-61**, new,
  open).
- No change to DEC-003 through DEC-014, to any accepted AR row, or to any
  RA row.
- No implementation authorization under any outcome of this review.

## I. Implementation remains blocked

**This document's proposal status does not authorize implementation
under any outcome.** No code, Odoo module, model, view, controller,
security file, manifest, test, or CI file is created or permitted by this
document. The no-code gate (`CLAUDE.md` §4–§5) remains in force. Per
`master-blueprint.md`'s "Criteria for when implementation may later be
opened," implementation of the inventory/fulfillment domains additionally
requires: (1) ChatGPT acceptance of this Part C blueprint (via a future
DEC-015 acceptance patch) — **not satisfied, this document and DEC-015
are Proposed, not accepted**; (2) resolution or conscious acceptance of
every "Blocks implementation: Yes" row this sprint touches — **not
satisfied**, several such rows remain open (MBQ-04, MBQ-08, MBQ-33,
MBQ-34, MBQ-38 detail, MBQ-41, MBQ-53–59 unchanged, MBQ-60); (3) a
separate, explicit ChatGPT implementation-gate approval — **not
satisfied**; (4) every implementation task written to the `CLAUDE.md` §9
template — **not applicable, no implementation task written**; (5) no
open quality-gate escalation. **None of conditions (1)–(5) is satisfied
by this document alone.**

## Next recommended sprint after ChatGPT review

**Master Blueprint Part D — UI/UX Screen Design Blueprint** (Sprint D):
screen inventory, navigation/information architecture, Odoo-native
interaction patterns, screen-level wireframe specs, and states, resolving
MBQ-53 — **not started by this sprint**, and this sprint does not
silently resolve MBQ-53 or begin any screen-level work. Alternatively,
**Master Blueprint Part E — implementation-planning bridge** (Sprint E) if
ChatGPT prefers to consolidate before Part D. Neither is started by this
sprint.
