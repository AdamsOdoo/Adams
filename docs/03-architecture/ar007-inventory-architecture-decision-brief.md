# AR-007 — Inventory Architecture Decision Brief

> Evidence-backed decision brief prepared for **AR-007** (inventory
> architecture) during the **AR-007 + AR-008 Decision Preparation** sprint
> (2026-07-02), after DEC-008/DEC-009 acceptance (PR #65 merged into
> `Shopify-connector`). This brief **proposes** a Phase 1 inventory
> architecture for ChatGPT/Fable review — it does **not** itself accept a
> decision. The corresponding proposed decision record is
> [`../04-decisions/DEC-010-inventory-architecture-strategy.md`](../04-decisions/DEC-010-inventory-architecture-strategy.md)
> (`Status: Proposed for ChatGPT review`). **No implementation is authorized
> by this brief.**

## Claim classification (used throughout this brief)

- **[Accepted decision]** — already decided by DEC-003/004/005/006/007/008/009; cited by section, not re-litigated.
- **[Accepted clarification]** — carried by the accepted DEC-007 Phase 1 scope-clarification addendum.
- **[Official fact]** — a verified Shopify/Odoo platform fact, cited with URL + access date.
- **[Official limitation]** — a verified platform constraint/boundary (e.g. a fixed mutation list, a read-only field).
- **[Competitor claim]** — what a vendor says about their own product; never treated as proven.
- **[Inference]** — our reasoning drawn from cited evidence; not itself a decision.
- **[Recommendation]** — what this brief proposes for AR-007; carried into [`DEC-010`](../04-decisions/DEC-010-inventory-architecture-strategy.md) if this brief is accepted, but this brief alone authorizes nothing.
- **[Implementation-planning default]** — a conceptual number/behaviour proposed for later implementation planning, explicitly not a verified constant.
- **[Open question]** — unresolved; routed to the Master Blueprint sprint or flagged "must be verified before implementation."

## Scope

This brief covers **Phase 1 inventory architecture only**: quantity
source-of-truth posture, Shopify inventory-object mapping, the safe Odoo
quantity concept, location architecture, sync direction/trigger, inventory
operation style, conflict handling, user-facing logs, and module boundaries.
It does **not** decide exact Odoo model fields, exact computed quantity
fields, exact mutation choice (where not verified), exact cron cadence, exact
feature-flag UI, or the exact first-push confirmation record schema — all
routed to the Master Blueprint / implementation-planning sprint (§10). It does
**not** revisit DEC-003/004/005/006/007/008/009, which are treated as fixed
context.

## Accepted context this brief must respect

- **[Accepted decision — DEC-003]** Inventory write-back (Odoo→Shopify) is in
  MVP; must be multi-location-aware; `committed` must never be written; write
  only allowed Shopify quantity fields; initial Shopify stock import is
  controlled/reviewed; auto-apply is **not** accepted as default MVP
  behaviour (explicitly routed to AR-007, an [Inference], DP-006).
- **[Accepted clarification — DEC-007]** A **first-inventory-push guard**
  applies before the first Odoo→Shopify inventory write per binding, at a
  granularity no coarser than per-store: a mapped Shopify location, a preview
  of SKU/variant/location quantities, explicit operator confirmation, a
  recorded source-of-truth decision, and the ability to skip or manually
  match ambiguous items. This brief may decide the quantity-field default,
  the multi-location mapping mechanism, ongoing apply-mode, and the exact
  granularity of "first" — but must not weaken any of the five required
  guard elements.
- **[Accepted decision — DEC-006]** Bindings are dedicated, store-scoped,
  explicit-GID + explicit-Odoo-record, uniqueness-constrained; inventory
  identity specifically needs `inventory_item_id` **+** `location_id`, not a
  plain product GID (exact schema deferred to this brief). Match priority:
  existing binding → SKU/internal reference → barcode → email/customer keys
  → manual; no name-only automatic matching, ever.
- **[Accepted decision — DEC-008]** `shopify_connector_inventory` depends on
  `core` + `product` only (a sibling of `sale`, not a dependency of it);
  binding **table shape** (polymorphic vs. per-domain) is not decided by
  DEC-008 — this brief places binding *responsibility*, not table shape, with
  `shopify_connector_inventory`. `shopify_connector_fulfillment` does **not**
  depend on `shopify_connector_inventory` (§9, §4 below).
- **[Accepted decision — DEC-009]** Job-source/state/16-error-class taxonomy
  applies; "inventory location missing" is an existing named error class
  routed to `blocked_manual_review`; the **ambiguous-outcome rule** applies to
  any write outside Shopify's `@idempotent` surface whose outcome is unknown
  after dispatch — no blind retry, either a safe verification read before
  retry or `blocked_manual_review`.
- **[Accepted decision — DEC-005]** Layered sync (webhooks + scheduled +
  manual + reconciliation, never one mechanism alone) is the accepted Phase 1
  substrate.

## Official facts (Shopify side — grounded in `../01-research/shopify-official-api-notes.md`)

1. **[Official fact]** The Shopify inventory object chain is **ProductVariant
   → InventoryItem (1:1) → InventoryLevel (one per Location) → Location**.
   Source: `shopify.dev/docs/api/admin-graphql/latest/objects/InventoryItem`
   (+ `InventoryLevel`, `Location`), access date 2026-06-30 (Sprint B
   baseline, reconfirmed unchanged 2026-07-01 RB-14 refresh).
2. **[Official fact]** Quantity states are `available, on_hand, committed,
   incoming, reserved, damaged, safety_stock, quality_control`, where
   **`on_hand = available + committed + reserved + damaged + safety_stock +
   quality_control`**. Source:
   `shopify.dev/docs/apps/build/orders-fulfillment/inventory-management-apps/manage-quantities-states`,
   access date 2026-06-30.
3. **[Official limitation]** `committed` is **API-read-only** — it changes
   only via order creation/fulfillment, never via the Admin API. Same source
   as #2.
4. **[Official fact]** `available`/`on_hand` are writable: `inventorySetQuantities`
   sets them absolutely with **compare-and-set** via `compareQuantity`;
   `inventoryAdjustQuantities` applies deltas (adjusting `available` also
   moves `on_hand`); `inventoryActivate` creates an InventoryLevel so a
   location can stock an item. Source: manage-quantities-states page +
   `.../mutations/inventorySetQuantities` + `.../mutations/inventoryAdjustQuantities`,
   access date 2026-06-30.
5. **[Official fact]** As of **API version 2026-04**, `inventorySetQuantities`
   and `inventoryAdjustQuantities` **require an idempotency key via the
   `@idempotent` directive** (optional as of 2026-01). Source: same mutation
   pages; version-sensitive delta reconfirmed in the RB-14 refresh, access
   date 2026-07-01.
6. **[Official fact]** Shopify's idempotency-key server dedup window is **24
   hours from the original request**; the `@idempotent` directive applies
   only to a **fixed list of 17 mutations** (inventory/location mutations +
   `refundCreate`); `IDEMPOTENCY_CONCURRENT_REQUEST` fires on concurrent
   duplicates; there is **no general/all-mutation idempotency** and no
   `clientMutationId`. Source: `/docs/api/usage/implementing-idempotency`,
   `/docs/api/usage/idempotent-requests`, access date 2026-07-01 (RB-14 Part
   2). **[Open question]** the literal 17-mutation list is not itemized in
   repo docs, and `@idempotent` key uniqueness scope (per-shop/app/global)
   remains open.

## Official facts (Odoo side — grounded in the small evidence refresh, `ar007-ar008-evidence-refresh.md`)

7. **[Official fact]** Odoo 19.0's Stock report defines **On Hand** ("current
   quantity of products") and **Free to Use** ("on-hand quantity that are not
   reserved for delivery or manufacturing orders, and are available to sell
   or use"); the Forecasted report additionally defines **Forecasted**
   ("projected stock levels based on confirmed and planned operations") and
   confirms reservation is tied to confirmed sales/manufacturing orders.
   Sources cited in full in `ar007-ar008-evidence-refresh.md`, access date
   2026-07-02.
8. **[Official fact]** Odoo location types include vendor, virtual, internal,
   customer, inventory loss, production, and transit locations. Same source
   as #7.
9. **[Open question] — must be verified before implementation.** The exact
   `stock.quant` ORM field names underlying the "On Hand"/"Free to Use"/
   "Forecasted" report concepts, and Shopify's webhook topic strings for
   inventory-level changes (`inventory_levels/update` or equivalent), are
   **not** confirmed in repo docs or the small evidence refresh — see
   `ar007-ar008-evidence-refresh.md` "Gaps that remain open."

## 1. Phase 1 inventory source-of-truth modes

### Options considered

| Option | Description | Disposition |
| --- | --- | --- |
| **A — Odoo as ongoing source, Shopify as one-time import source** (recommended) | Odoo is the ongoing source of truth for Shopify inventory (Odoo→Shopify write-back, per DEC-003); a controlled, reviewed, one-time/first-sync import establishes the starting Odoo position from existing Shopify stock where useful, per DEC-003's "initial Shopify stock import is controlled/reviewed." | **Recommended** |
| B — Shopify as ongoing source for Odoo | Odoo inventory driven by Shopify. | **Rejected** — contradicts DEC-003's accepted "inventory write-back" (Odoo→Shopify) primary direction; no evidence supports flipping the accepted direction. |
| C — Autonomous bidirectional conflict ownership | Both systems can independently change quantities; the connector reconciles/merges automatically. | **Rejected** — see RA-020 below. |
| D — No source-of-truth statement (ad hoc per sync) | Whichever system syncs "last" wins implicitly. | **Rejected** — see RA-021 below; violates DEC-007's requirement for a *recorded* source-of-truth decision. |

### Recommended approach [Recommendation]

- **Ongoing direction (ordinary operation):** Odoo is the source of truth;
  the connector pushes Odoo quantities to Shopify's **`available`** field as
  the Phase 1 **default** target (never `committed` — fact #3). `on_hand` is
  also a writable field (fact #4) but is **not** an equally-weighted default
  — see §3's disposition of Option B. This matches the already-accepted
  DEC-003 "Odoo → Shopify (write-back): inventory write-back" primary
  direction.
- **Controlled one-time / first-sync import (Shopify → Odoo):** where a store
  already has live Shopify stock when the connector is first configured, a
  **controlled, reviewed** import establishes an initial Odoo quantity
  baseline — this is the accepted DEC-003 "initial Shopify stock import is
  controlled/reviewed" statement, not a standing bidirectional sync. Whether
  apply is automatic or review-then-apply is explicitly **open** (C-INV-04,
  DP-006) — see §6.
- **After the first-sync baseline is established**, the connector operates in
  the ongoing Odoo→Shopify direction, guarded by the DEC-007 first-push guard
  at whatever point that guard's granularity (§1 "first" scoping, decided in
  §6 below) is first crossed for a given binding.

### Why autonomous bidirectional conflict ownership is not Phase 1 [Inference]

- **[Accepted decision — DEC-003]** MVP explicitly excludes "unrestricted
  autonomous bidirectional catalog ownership" (automatic two-way conflict
  resolution across fields, a complex field-ownership matrix) for the
  *product* domain — the same reasoning applies with equal or greater force
  to inventory, where an incorrect automatic merge directly risks overselling
  or underselling live stock, a customer-facing failure mode with no
  "draft/unpublished" safety net (unlike products).
- **[Accepted decision — DEC-009]** The ambiguous-outcome rule and the
  `blocked_manual_review` state exist precisely because Shopify write
  outcomes cannot always be safely inferred; an autonomous conflict-resolution
  engine would have to guess in exactly the cases DEC-009 already routes to
  manual review.
- **[Inference]** No competitor evidence in the repo demonstrates a safe
  autonomous bidirectional inventory-conflict engine; the demonstrated market
  pattern (Emipro, VentorTech) is single-direction write-back with a
  controlled import step (`common-patterns.md`, `best-in-class-observations.md`).
- See **RA-020** (rejected-approaches-log.md) for the formal rejection.

## 2. Shopify inventory object mapping

- **[Official fact]** Chain: ProductVariant → InventoryItem (1:1) →
  InventoryLevel (per Location) → Location (fact #1).
- **[Recommendation]** The **inventory binding** (per DEC-006, which
  explicitly defers the exact inventory-identity shape to this brief) keys
  on **`(store, inventory_item_id, location_id)`**, distinct from the
  product/variant binding (`(store, Shopify GID)` for the ProductVariant).
  This is consistent with DEC-006's own statement that "inventory needs
  `inventory_item_id` + `location_id`, not just a product GID."
- **Store-scoped uniqueness [Recommendation]:** a per-store uniqueness
  constraint on `(store, inventory_item_id, location_id)`, mirroring DEC-006's
  `(store, GID)` / `(store, Odoo model, Odoo record)` pattern extended to the
  inventory-specific identity tuple.
- **Location mapping requirement [Recommendation]:** a separate, explicit
  **Odoo location ↔ Shopify Location** mapping record (not inferred from
  name matching) must exist before any inventory write for that Odoo
  location; see §4.
- **[Open question]** The exact binding table shape (dedicated
  `inventory_binding` model vs. a field on a shared per-domain binding
  pattern) is left to the Master Blueprint, consistent with DEC-008's
  statement that binding *responsibility*, not table shape, is decided at
  the module-boundary level.

## 3. Odoo inventory source

### Options considered

| Option | Description | Disposition |
| --- | --- | --- |
| **A — Odoo "Free to Use" concept as the Phase 1 source** (recommended) | Conceptually maps to Shopify's `available` (sellable, unreserved stock). | **Recommended (directional)** |
| B — Odoo "On Hand" concept | Conceptually closer to Shopify's `on_hand`, but Shopify's `on_hand` is a **sum including committed/reserved/damaged/safety-stock/QC** (fact #2) — pushing Odoo's on-hand-only figure as Shopify's `on_hand` risks a semantic mismatch since Shopify's `on_hand` is not independently settable as a clean input in the same way. | **Weakened** — see below. |
| C — Odoo "Forecasted" concept | Includes future incoming/outgoing not yet physically at the warehouse. | **Weakened** — forecasted stock is a projection, not a present sellable quantity; risks pushing quantities Shopify customers cannot actually receive today. |
| D — Let the operator pick per store, no default | No default; all merchants configure from scratch. | **Rejected in part** — a default is required per MVP UX ("essential mappings only," inline help, US-E5-02); a *configurable* default with inline help is compatible with Option A and is not mutually exclusive. |

### Recommended approach [Recommendation]

- **[Recommendation]** Odoo's **"Free to Use"** report-level concept ("on-hand
  quantity that are not reserved for delivery or manufacturing orders, and
  are available to sell or use," fact #7) is the **directionally safest
  Phase 1 candidate**, because it conceptually corresponds to what Shopify's
  `available` is meant to represent (sellable stock, excluding what is
  already committed elsewhere) — writing it to Shopify's `available` (fact
  #4) keeps the connector inside Shopify's writable-field surface (fact #3)
  without needing to reconstruct Shopify's own `on_hand` summation (fact #2)
  on the Odoo side.
- **[Open question] — exact implementation source, not just field/computation.**
  This brief chooses the **semantic quantity concept only** ("Free to Use")
  — it does **not** verify or decide the exact Odoo ORM/implementation
  source behind it. Fact #7 verifies the **report-level UI concept**
  ("Free to Use" as documented on Odoo's official Stock report page); it
  does **not** verify that `stock.quant` is the underlying model, field, or
  computation. Candidate implementation sources include `stock.quant`, a
  product quantity helper method, the stock-report/ORM method itself, or
  another Odoo-supported mechanism — **none of these is confirmed** (gap #9
  above). The Master Blueprint must verify the exact source, model, and
  field/formula against official Odoo 19.0 docs or source before any code is
  written; whether a configurable default (per C-INV-02, US-E5-02) should
  offer Forecast/On-Hand/Free-to-Use as alternatives is likewise
  **implementation-planning / Master Blueprint** work.
- **[Recommendation, conceptual only]** Whether `product.product`, a stock
  location/warehouse concept, or picking data is the *conceptual* source: a
  **location-scoped Odoo quantity concept** (whatever its exact underlying
  model turns out to be — see above) is the conceptually correct source,
  aggregated per the Odoo-location-to-Shopify-location mapping (§4) — not
  `product.product` alone (which has no location dimension) and not picking
  data directly (which represents movement events, not a point-in-time
  quantity). This is a statement about *which concept* is correct, not a
  claim that `stock.quant` specifically has been verified as that concept's
  Odoo implementation.
- **Reserved/forecast/on-hand/available treatment [Recommendation]:**
  reserved and forecast quantities are **not** pushed to Shopify as separate
  fields in Phase 1 (Shopify has no equivalent write target for them);
  `available` is the Phase 1 default write target, `on_hand` is allowed but
  not default (see §1), and `committed` is never written (fact #4). Reserved/
  forecast figures remain **Odoo-internal bookkeeping concepts** informing
  which single number is exported. Any future need to surface reserved/
  forecast distinctly on the Shopify side is out of scope for Phase 1.
- **[Open question]** whether Odoo's "Free to Use" and Shopify's `available`
  are numerically equivalent in every edge case (e.g. Odoo reservations tied
  to manufacturing vs. Shopify's `committed`) is **not verified** — flagged
  for the Master Blueprint / a dedicated Odoo Inventory-app deep read before
  implementation.

## 4. Location architecture

- **[Accepted decision — DEC-003]** Multi-location-awareness is mandatory in
  MVP; a single-location design is a demonstrated anti-pattern (avoid-list
  A-INV-2, Webkul).
- **Single-location minimum vs. multi-location mapping [Recommendation]:**
  Phase 1 requires **at least one explicitly mapped** Odoo location ↔
  Shopify Location pair before any write; the *mapping mechanism* must be
  structurally capable of more than one pair (no schema/logic that
  hard-codes "one location") even if a given merchant only uses one location
  at launch — satisfying "multi-location-aware enough to avoid a wrong
  single-location design" (DEC-003) without requiring every Phase 1 merchant
  to configure multiple locations.
- **Odoo warehouse/location → Shopify location mapping [Recommendation]:** an
  explicit mapping record (Odoo `stock.location`/warehouse identifier ↔
  Shopify `Location` GID), owned by `shopify_connector_inventory` (§9), never
  inferred from name similarity (consistent with DEC-006's "no name-only
  automatic matching, ever").
- **If no mapping exists [Recommendation]:** the write is **blocked**, not
  guessed — routed to the DEC-009 `blocked_manual_review` state under the
  already-named **"inventory location missing"** error class. This is also
  the DEC-007 first-push-guard behaviour ("a mapped Shopify location — or an
  explicit 'no location mapped yet, cannot push' block").
  See **RA-019** below.
- **If multiple mappings are possible [Recommendation]:** each Odoo location
  maps to **exactly one** Shopify Location (no one-to-many); if an Odoo
  location could plausibly map to more than one Shopify Location, that is an
  **ambiguous match**, routed to manual review (DEC-009 "ambiguous match"
  class) — never resolved by picking the first/default candidate silently.
- **Interaction with fulfillment, without a forbidden dependency
  [Clarified — not an open DEC-008 contradiction, not a DEC-008 amendment]:**
  `shopify_connector_fulfillment` must **not** depend on
  `shopify_connector_inventory` (DEC-008, unchanged). This brief does **not**
  decide the exact Odoo↔Shopify location-mapping schema and does **not**
  change DEC-008's dependency direction.
  `shopify_connector_inventory` **remains the sole owner** of the
  Odoo-location ↔ Shopify-Location *mapping* used for inventory push
  decisions — that ownership is unchanged by this clarification.
  `shopify_connector_fulfillment` must not read that mapping table.
  Instead, a **minimal Shopify Location *reference*** — not a mapping — may
  live in `shopify_connector_core` as shared substrate: conceptually, the
  store, the Shopify Location GID, the Shopify Location name, active/status
  where available, and last-synced/seen metadata if later needed. This is
  **not** a decision to create exact fields or models; it is an
  **interpretation** consistent with the existing DEC-008 boundary (`core`
  owns cross-cutting reference data; domain modules own business mappings),
  not an amendment to DEC-008. `shopify_connector_fulfillment` may resolve
  location identity from (a) Shopify FulfillmentOrder `assignedLocation` data
  fetched live from Shopify, and/or (b) this core reference — it does **not**
  need `shopify_connector_inventory`'s mapping table for either path. The
  **exact mechanism** by which fulfillment confirms a picking's source
  location against the Shopify fulfillment location remains **open for the
  Master Blueprint** — see the matching clarification in the AR-008 brief
  §2/§9 and DEC-010/DEC-011.

## 5. Sync direction and trigger

- **[Accepted decision — DEC-005]** Layered sync (webhooks + scheduled +
  manual + reconciliation) is the accepted Phase 1 substrate; webhook-only is
  not acceptable.
- **Scheduled reconciliation [Recommendation]:** a periodic `ir.cron` job
  reconciles Odoo-computed quantities against last-known-pushed Shopify
  quantities for every mapped `(inventory_item_id, location_id)` pair,
  correcting drift. Exact cadence is an **[Implementation-planning default]**,
  not decided here.
- **Manual sync [Recommendation]:** an operator-triggered "sync inventory now"
  action, enqueued (never run inline), reusing the same write path and guard
  logic as scheduled sync.
- **Event-driven enqueue [Recommendation]:** relevant Odoo stock changes
  (e.g. a `stock.move` affecting a mapped location's quantity) enqueue a
  targeted sync job for the affected `(inventory_item_id, location_id)` pair,
  rather than waiting for the next scheduled run — safe because it flows
  through the same guarded write path (first-push guard, idempotency,
  ambiguous-outcome rule) as any other trigger.
- **Shopify webhook-driven inventory import [Open question]:** an
  `inventory_levels/update`-style Shopify webhook (if it exists — **not**
  confirmed in repo docs, see gap #9/evidence-refresh) could import
  Shopify-side changes for reconciliation/drift-detection purposes. This
  brief does **not** assert this webhook topic as fact and does **not**
  decide to build on it until the topic name and payload are officially
  verified — flagged **"Open question / must be verified before
  implementation."**
- **Avoiding webhook-only reliance [Recommendation]:** regardless of whether
  an inventory webhook exists, scheduled reconciliation + manual sync remain
  mandatory per the already-accepted DEC-005 layered-sync policy — inventory
  sync must never depend on webhook delivery alone.

## 6. Inventory operation style

- **Set vs. adjust [Recommendation]:** prefer **`inventorySetQuantities`**
  (absolute value with `compareQuantity` compare-and-set, fact #4) as the
  **default** operation style for pushing a known-correct Odoo-computed
  quantity, because compare-and-set structurally guards against clobbering a
  concurrent Shopify-side change that the connector has not yet observed.
  `inventoryAdjustQuantities` (delta-based) is a candidate for narrower,
  event-driven "this stock.move changed quantity by N" pushes where a delta
  is the more natural unit — the **exact choice per trigger type** is an
  **[Open question]** for the Master Blueprint, not decided here.
- **Idempotency implications [Accepted decision — DEC-009]:** both mutations
  require `@idempotent` as of API 2026-04 (fact #5) and are **on** the
  17-mutation fixed list (fact #6) — so a persisted idempotency key reused
  within the 24-hour dedup window makes a retry **safe** (DEC-009's case 2:
  "writes using a Shopify `@idempotent` mutation" — automatic retry is safe
  using the same persisted key).
- **Ambiguous-outcome retry handling [Accepted decision — DEC-009,
  Recommendation for the edge case]:** if the connector ever targets a
  Shopify API version where `@idempotent` is unavailable/not required for
  these mutations (e.g. a pinned pre-2026-01 version), or if a future
  inventory-adjacent mutation used by the connector is **not** on the
  17-mutation list, the DEC-009 **ambiguous-outcome rule applies in full**:
  no blind retry after a timeout/connection-loss with an unknown outcome —
  either a safe verification read (re-fetch the InventoryLevel and compare)
  before retry, or route to `blocked_manual_review`. This brief recommends
  the connector's Master Blueprint **always target an API version with
  `@idempotent` support for these two mutations** so the safer case 2 path
  applies by default.
- **Preferred safety approach [Recommendation]:** compare-and-set
  (`compareQuantity`) plus a persisted idempotency key together are the
  Phase 1 safety baseline for every inventory write, first-push or ongoing.
- **Audit requirements [Recommendation, extends DEC-009 §8 below]:** every
  inventory write logs the **old (last-known) quantity**, the **intended
  quantity**, the **mutation used**, the **idempotency key**, and — for
  first-push writes — the **confirmation record** (§ DEC-007 guard).

## 7. Conflict handling

| Conflict | Recommended handling | DEC-009 error class |
| --- | --- | --- |
| Missing SKU / missing binding | Block; do not guess; surface for manual match | "mapping missing" |
| Ambiguous match (SKU/variant/location) | Block; route to manual review | "ambiguous match" |
| Missing location mapping | Block; "no location mapped yet, cannot push" | "inventory location missing" |
| Shopify variant inactive/deleted | Mark the binding stale (per DEC-006's stale-binding handling), do not silently recreate or drop | "binding conflict" (stale) |
| Odoo product archived/deleted | Suspend inventory sync for that binding; do not delete the binding silently | "binding conflict" |
| Quantity mismatch beyond expected drift | Surface in reconciliation output for operator review, do not auto-force-correct without the same guard as a first push if it is effectively re-establishing trust in a diverged binding | "data shape/schema mismatch" or reconciliation-specific handling (exact threshold: implementation-planning) |
| Attempted write of `committed` | Structurally impossible — never offered as a write target (fact #3; RA-018) | "destructive-write guard blocked" |
| Manual override / skip / retry | Operator can skip an item in a preview (DEC-007), or retry a `blocked_manual_review` job after resolving the underlying cause (DEC-009 recovery-first UX) | n/a (recovery path) |

## 8. User-facing inventory logs

- **[Accepted decision — DEC-009 §8]** Logs must show: what was attempted;
  what was actually written (never assume attempted implies written); what
  was skipped and by whom/what rule; who confirmed destructive/first-push
  actions; the source-of-truth record for first-sync/first-push decisions;
  before/after values for destructive operations.
- **[Recommendation, inventory-specific]** Every inventory write log entry
  shows: **old quantity** (last known), **intended quantity**, **Shopify
  location**, **source-of-truth** (which system's number was authoritative
  for this write), **binding** (SKU/variant/location identity), and —
  where relevant — the **operator-confirmation record** (first-push guard).
- **[Accepted decision — DEC-009 / product-vision.md]** No technical-only
  errors: every failure carries a human-readable reason, a suggested fix, and
  a retry action where applicable (US-E7-01/02) — raw stack traces are not
  the primary UX (RA-016).

## 9. Boundaries

- **`shopify_connector_inventory` owns [Recommendation, consistent with
  DEC-008's Phase 1 addon table]:** inventory quantity sync engine (push +
  reconciliation); Odoo-location ↔ Shopify-Location mapping; inventory
  binding responsibility (`inventory_item_id` + `location_id` identity
  shape); the DEC-007 first-inventory-push guard implementation; the
  quantity-field default/configuration surface.
- **`shopify_connector_core` owns [Accepted decision — DEC-008]:** store/
  connection config; GraphQL transport + rate-limit pacing; webhook receiver
  + HMAC + dedup; queue/job abstraction + `ir.cron` worker(s); the binding
  **abstraction/shared contract** (store-scoping, audit/status fields,
  uniqueness principles) that the inventory binding must satisfy; the
  error-class registry (including "inventory location missing"); the
  recovery-first log/error-center dashboard. Per §4's clarification, `core`
  is also where a minimal shared Shopify-Location *reference* (not a
  mapping) may live so `fulfillment` never needs to depend on `inventory` —
  exact fields/models remain open for the Master Blueprint.
- **`shopify_connector_product` owns [Accepted decision — DEC-008]:**
  product/variant identity and its own binding — inventory keys off the
  variant's `inventory_item_id`, but `inventory_item_id`/`location_id`
  binding responsibility itself lives in `inventory`, not `product`.
- **Must not depend on `shopify_connector_fulfillment` [Accepted decision —
  DEC-008]:** confirmed by the dependency DAG — `inventory` and `sale` are
  siblings under `product`; `fulfillment` depends on `core` + `sale`, not on
  `inventory`. Since the DAG is one-directional and `inventory` has no edge
  toward `sale` or `fulfillment`, `shopify_connector_inventory` has **no**
  dependency on `shopify_connector_fulfillment` by construction — this brief
  does not need to add a rule, only confirm the existing DAG already
  satisfies it.

## 10. What remains open for Master Blueprint / implementation planning

- Exact Odoo model/field names (binding model(s), mapping model, log/audit
  fields).
- The exact Odoo-side implementation source and field/formula behind "Free
  to Use" (`stock.quant`, a product quantity helper, a stock-report/ORM
  method, or another Odoo-supported mechanism — **not verified, not decided
  here**; this brief chooses the semantic concept only), and the exact
  default vs. configurable quantity-field choice, C-INV-02.
- Whether `on_hand` is ever used as an alternative Phase 1 write target
  instead of `available` — not decided here; `available` is the default and
  an `on_hand` mapping requires explicit Master Blueprint justification
  given its multi-state-sum semantics (fact #2).
- Exact mutation choice per trigger type (`inventorySetQuantities` vs.
  `inventoryAdjustQuantities`) beyond the directional preference in §6.
- Exact cron cadence for scheduled reconciliation.
- Exact feature-flag / configuration UI for enabling inventory sync per
  store and choosing the quantity-field default.
- Exact first-push confirmation record schema (what fields capture the
  operator's confirmation, timestamp, and source-of-truth choice).
- The exact granularity of "first" for the DEC-007 guard (per store / per
  binding / per variant-location binding) — DEC-007 requires no coarser than
  per-store; the exact unit is left open.
- Whether ongoing (post-first-push) syncs require preview/confirmation on
  every write or only the first (apply-mode: auto-apply vs. review-then-apply,
  C-INV-04) — an explicit **[Open question]**, not decided by this brief
  (see DEC-010 §"What remains open").
- Verification of the Shopify inventory-webhook topic string(s), the literal
  17-mutation `@idempotent` list, `@idempotent` key-uniqueness scope, and the
  exact `stock.quant` field/tracking-reference gaps noted in
  `ar007-ar008-evidence-refresh.md`.
- The exact mechanism by which `shopify_connector_fulfillment` confirms a
  picking's source location against the Shopify fulfillment location (core
  Shopify-Location reference vs. live FulfillmentOrder `assignedLocation`
  fetch, or both) — the **ownership principle** is clarified in §4/§9 (shared
  with AR-008); the **exact confirmation mechanism and any exact
  fields/models** remain a Master Blueprint item.

## Rejected or weakened alternatives

- **Blind first Odoo→Shopify inventory push (no preview, no confirmation, no
  mapped-location check).** Already a **binding final rejected approach** —
  see **RA-008** (`rejected-approaches-log.md`, tied to the accepted
  DEC-007). Not re-logged.
- **Writing Shopify's `committed` quantity.** **Rejected** — see **RA-018**
  (new, PROPOSED this sprint; formalizes avoid-list A-INV-3 now that AR-007
  is under formal review).
- **Single-location-only design / SKU-only writes without per-location
  binding identity.** **Rejected** — see **RA-019** (new, PROPOSED this
  sprint; formalizes avoid-list A-INV-2 and the SKU-only double-decrement
  risk now that AR-007 is under formal review).
- **Autonomous bidirectional inventory conflict resolution in Phase 1.**
  **Rejected** — see **RA-020** (new, PROPOSED this sprint).
- **Treating Shopify and Odoo inventory quantities as directly equivalent
  without an explicit source-of-truth and documented quantity-field
  semantics.** **Rejected** — see **RA-021** (new, PROPOSED this sprint).
- **Webhook-only inventory sync without reconciliation.** **Weakened, not a
  new rejected approach** — already governed by the accepted DEC-005 layered-
  sync policy ("never one mechanism alone"); no new RA row added, to avoid
  restating an already-accepted principle as if it were a fresh AR-007
  rejection.
- **Inventory adjustment without location mapping.** Folded into **RA-019**
  above (same root cause: no per-location identity/mapping).
- **Inventory sync by SKU only without binding/location identity.** Folded
  into **RA-019** above.
- **Relying on the binding alone for operation idempotency.** Already a
  **binding final rejected approach** — see **RA-017**. Not re-logged;
  §6/§7 above apply it (compare-and-set + persisted idempotency key, not
  binding identity alone).

## What this brief does not decide

- Does not accept DEC-010.
- Does not decide exact model fields, database constraints, or Python/ORM
  design.
- Does not create Odoo modules, code, or tests.
- Does not decide the feature-flag/config-model mechanism (routed to
  UX/operator-flow and Master Blueprint, per DEC-008's existing deferral).
- Does not authorize implementation.
- Does not alter DEC-003/004/005/006/007/008/009.
