# Inventory Operating Model — Odoo 19 ↔ Shopify Connector (MVP)

> **Status: Proposed — Fable gap-closure mission, 2026-07-16.** This document
> consolidates and closes the MVP inventory model on top of accepted
> [DEC-010](../04-decisions/DEC-010-inventory-architecture-strategy.md) and the
> Part-C blueprint
> ([master-blueprint-inventory-fulfillment.md](../03-architecture/master-blueprint-inventory-fulfillment.md));
> it feeds the revised Task 013/013B packets (Wave 3). Acceptance authority:
> product owner + Claude control room. **No implementation authorized.**
> Inventory *mutation* implementation stays unauthorized until DEC-031 Layer 2
> is accepted AND implemented (see §7).

Labels follow [CLAUDE.md](../../CLAUDE.md) §8: [Fact], [Inference],
[Recommendation], [Proposed product decision], [Open question].

---

## 1. Operating model statement

- **[Fact — accepted decision]** Odoo is the source of truth for the quantity
  the connector writes to Shopify `available`. Accepted in
  [DEC-010](../04-decisions/DEC-010-inventory-architecture-strategy.md)
  (accepted 2026-07-02); this document layers operational detail on top of it
  and changes nothing in DEC-010.
- **[Proposed product decision — export figure]** The exported figure is
  **Odoo `free_qty` computed with an explicit per-mapped-location context**
  (`with_context(location=<odoo_location_id>)` semantics, exact API per Task
  013 D-013-2). Basis: [Fact] Odoo 19's `free_qty` = "Quantity On Hand −
  reserved quantity" and all five quantity fields are non-stored,
  **context-scoped** computes — reading them **without** a warehouse/location
  context silently aggregates across **all** internal locations, the critical
  per-Shopify-location pitfall — per the official source capture
  ([odoo19-sale-stock-security-captures-2026-07-16.md §3](../00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md)).
- **[Proposed product decision — forecast mode]** `virtual_available`
  ("Forecasted") is offered only as an **explicit opt-in "sell on forecast"
  mode**, never the default. [Inference] It counts planned incoming receipts
  and double-counts outgoing demand once Shopify orders import into Odoo
  (same capture §3); `qty_available` is likewise rejected as the default
  because it ignores reservations and oversells.
- **[Fact — binding rejection]** Shopify `committed` is **never written**
  ([RA-018](../05-qa/rejected-approaches-log.md)) — it is API-read-only and
  changes only via order creation/fulfillment. Shopify `on_hand` writes
  require explicit blueprint justification (DEC-010 preserved caveat); MVP
  writes only `available`.
- **[Fact]** Shopify's model: InventoryItem (1:1 variant) × Location →
  InventoryLevel with 8 named quantity states (`incoming`, `on_hand`,
  `available`, `committed`, `reserved`, `damaged`, `safety_stock`,
  `quality_control`)
  ([shopify captures §9](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
  [Fact — binding rejection] Odoo and Shopify quantity fields are never
  treated as directly equivalent without this recorded source-of-truth model
  ([RA-021](../05-qa/rejected-approaches-log.md)) — this document *is* that
  recorded model for `free_qty` → `available`.

## 2. Identity and mapping

- **[Fact — binding rejection]** Write identity is
  **`inventory_item_id` + `location_id`**, never SKU-only and never
  single-location ([RA-019](../05-qa/rejected-approaches-log.md)). Every push
  targets exactly one (item, location) pair.
- **[Proposed product decision — location mapping]** An explicit mapping model
  (Task 013 D-013-1: `shopify.connector.location.mapping`) binds one Odoo
  stock location (or warehouse root location) to one Shopify Location per
  store. The Shopify side references the existing **read-only
  `shopify.connector.location` cache** owned by core (DEC-010's ratified
  shared-Location-reference clarification: the cache stores no Odoo IDs; the
  inventory module owns the mapping).
- **[Proposed product decision — conflicting-mapping prevention]** Uniqueness
  is enforced twice: (a) SQL unique constraints per store on the Shopify
  location and on the Odoo location (no two mappings may claim the same side),
  and (b) model-level validation rejecting overlapping Odoo locations (e.g. a
  warehouse root *and* one of its children both mapped for the same store),
  because both would compute overlapping `free_qty` scopes and race each
  other. [Inference] Constraint + validation together prevent the
  double-decrement / double-push class RA-019 exists for.
- **[Proposed product decision — inactive Shopify locations]** If the cached
  Shopify Location becomes `isActive = false` (or disappears from the cache
  refresh), the mapping is **flagged `needs_review` and its pushes are
  suspended** — no writes to a deactivated location — until an operator
  remaps or re-confirms. [Fact] `Location.isActive` / `deactivatedAt` and
  activate/deactivate lifecycle are official surface
  ([shopify captures §9](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
- **[Proposed product decision — level activation]** Pushing to an (item,
  location) pair with no InventoryLevel uses `inventoryActivate` (itself
  `@idempotent`-keyed) before/instead of a set, per the official lifecycle;
  the connector never assumes a level exists.

## 3. Initial baseline (Task 013B layer)

- **[Fact — accepted]** No blind first push
  ([RA-008](../05-qa/rejected-approaches-log.md)); the first-push guard is
  accepted at **per-mapped-pair granularity (MBQ-33,
  [DEC-018](../04-decisions/DEC-018-mbq-decision-batch-1.md))**: mapped
  location verified + **preview** + explicit operator **confirmation** +
  **recorded source-of-truth** choice before the first live write.
- **[Proposed product decision — controlled first read]** Baseline begins with
  a **read**: per store, fetch InventoryLevels (`quantities(names:
  ["available"])`, plus `on_hand`/`committed` for context) for all bound items
  at mapped locations, and compute the Odoo per-location `free_qty` for the
  same pairs.
- **[Fact — accepted]** The apply step defaults to **review-then-apply
  (MBQ-34, DEC-018)**: the operator sees Shopify-current vs Odoo-computed vs
  push-target per pair, then applies; auto-apply is a deliberate opt-out, not
  the default. The Task 013B packet
  ([task-013b-initial-inventory-baseline-packet.md](../07-implementation-plan/task-013b-initial-inventory-baseline-packet.md))
  details the preview semantics (D-013B-2) and drift-abort (D-013B-4); this
  document layers on those closures without reopening them.

## 4. Ongoing Odoo→Shopify updates

### 4.1 Triggers

- **[Proposed product decision]** Two triggers, per Task 013 D-013-6:
  (a) **`odoo_event`** — Odoo stock changes (quant/reservation writes) enqueue
  per-(item, location) push intents; (b) a **scheduled reconciliation sweep**
  (cron) that recomputes and enqueues pairs whose Odoo value differs from the
  last confirmed pushed value, catching anything the event hook missed.

### 4.2 Coalescing — last-value-wins

- **[Proposed product decision]** One **pending-update record per (item,
  location)** pair. New stock events **overwrite** the pending record's target
  rather than appending: at push time the connector recomputes/uses only the
  **latest absolute `free_qty`**.
- **[Inference — why absolute, not delta]** Because the export is an absolute
  set of a fully recomputable figure, intermediate values carry no
  information: pushing 5 then 7 and pushing 7 directly end in the same state.
  A delta queue (`inventoryAdjustQuantities`) would require every delta to be
  applied exactly once in order — lost or duplicated deltas permanently skew
  stock — whereas last-value-wins is self-healing (the next push or sweep
  converges). [Fact] Shopify itself directs systems that "act as the source
  of truth" to `inventorySetQuantities`, not the delta mutation
  ([shopify captures §9](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
- **[Proposed product decision — active-job dedup]** While a push job for a
  pair is queued/running, its `operation_scope_key` (per Task 013 D-013-6/7)
  prevents a second concurrent job for the same pair; new events only refresh
  the pending target consumed by the next run.

### 4.3 Batching

- **[Proposed product decision]** Pushes use `inventorySetQuantities` with a
  multi-entry `quantities[]` input where several pairs are due for the same
  store, within batch-size limits (§9); per-entry `userErrors` keep batching
  compatible with per-record failure routing (§10). Task 013's one-pair-per-job
  baseline (D-013-6) remains valid as the conservative floor; batching is the
  revised-packet refinement.

### 4.4 compareQuantity CAS

- **[Fact]** `inventorySetQuantities` supports per-entry `compareQuantity`:
  "the mutation will only update the quantity if the persisted quantity
  matches the `compareQuantity` value", and omitting it "can lead to
  inaccurate inventory quantities if multiple requests are made concurrently"
  ([shopify captures §9](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
- **[Proposed product decision — flow]** Every push is **read → compare →
  set**: read the current Shopify `available` (or use the reconciliation-read
  value), send it as `compareQuantity` with the Odoo target. On CAS mismatch:
  **re-read, re-derive the Odoo target, retry** with bounded attempts
  (proposed: 3). Persistent divergence after retries → **review case** (§5),
  never `ignoreCompareQuantity`.

### 4.5 Mandatory idempotency key

- **[Fact]** Since API version **2026-04**, the `@idempotent` directive with a
  **UUID idempotency key** is mandatory at runtime for
  `inventorySetQuantities` / `inventoryAdjustQuantities` /
  `inventoryActivate` and related mutations; keys are **retained 24 hours**
  and duplicates within the window return the cached response without
  re-executing
  ([shopify captures §9](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)).
- **[Proposed product decision]** One fresh UUID **per mutation attempt**,
  persisted on the attempt record *before* the call (see §6), so a network
  retry replays the same key while a deliberate new attempt uses a new key.
  [Inference] The 24-hour window bounds how long a stored key is replayable;
  after 24h a stale attempt must go through reconciliation (§6), not key
  replay.

## 5. Shopify→Odoo behavior (MVP)

- **[Proposed product decision]** MVP is **read/verify only** in this
  direction: reconciliation reads compare Shopify `available` against the
  connector's last-pushed value and the current Odoo figure, and **surface
  divergence**. **No automatic Odoo stock writes from Shopify data** —
  autonomous bidirectional conflict resolution is rejected
  ([RA-020](../05-qa/rejected-approaches-log.md)).
- **[Proposed product decision]** Each divergence produces a **review case**
  carrying the three values and a proposed explanation ([Inference]-labelled
  in the UI, e.g. "Shopify order committed stock between pushes", "manual
  Shopify adjustment"). The operator resolves by triggering a fresh
  Odoo→Shopify push or acting in Odoo; the connector never guesses.

## 6. Uncertainty after mutation + reconciliation before replay

- **[Fact — current behavior]** Under accepted
  [DEC-031](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md),
  a mutation job whose outcome is uncertain (timeout, ambiguous response) is
  **not auto-replayed**: it fails closed as `remote_effect_not_replay_safe`
  and waits for review.
- **[Proposed product decision — Layer 2 contract]** When DEC-031 Layer 2 is
  accepted and implemented, each mutation attempt is preceded by a persisted
  **attempt record** (pair identity, target value, `compareQuantity` basis,
  idempotency UUID, timestamp). After an uncertain outcome, a
  **reconciliation read** (`InventoryLevel.quantities` query) decides
  **applied / not-applied** *before* any retry: if Shopify already shows the
  target, the attempt is marked applied and closed; if not, a retry may be
  issued (same key within 24h, else fresh CAS cycle). Design detail lives in
  the Layer 2 design doc:
  [dec-031-layer-2-mutation-safety-design.md](../03-architecture/dec-031-layer-2-mutation-safety-design.md)
  (companion gap-closure deliverable). [Inference] For an absolute CAS set,
  the reconciliation read is decisive — the observed quantity either equals
  the attempted target or the attempt cannot have been the last write.
- **Gate:** inventory mutation implementation (Task 013/013B code) remains
  **unauthorized until DEC-031 Layer 2 is accepted AND implemented**.

## 7. Edge cases

- **Negative quantities.** [Fact] Odoo `free_qty` can be negative (on-hand
  minus reservations). [Recommendation] Default policy: **clamp to 0 on push
  and raise a divergence warning** carrying the true negative value.
  Justification: a negative storefront `available` communicates nothing
  useful to buyers, and clamping keeps the store non-sellable while the
  operator fixes Odoo; the warning prevents the clamp from silently hiding a
  stock problem. Pushing the raw negative is the documented alternative
  (config option candidate). [Open question] Whether Shopify formally accepts
  and meaningfully renders negative `available` via `inventorySetQuantities`
  is not verified in the captures — verify before offering push-negative.
- **Unmapped inventory items.** [Proposed product decision] Items with no
  binding, or bindings whose location has no mapping, are **skipped**, with a
  **surfaced count** per store ("N items not synced: unmapped") — never a
  silent drop, per DEC-010's audit posture and Task 013's unmapped handling.
- **Inactive locations.** Mapping flagged, pushes suspended, review required
  (§2).
- **Conflicting mappings.** Prevented structurally (§2); if data predating the
  constraint is detected on upgrade, all conflicting mappings suspend until
  resolved.
- **Product archived / binding stale.** [Proposed product decision] If the
  Shopify variant/item behind a binding is gone or archived, pushes for that
  binding suspend and a review case opens; the connector never re-creates
  catalog objects from the inventory path.

## 8. Manual and scheduled sync UX

- **[Proposed product decision — manual]** Per-store and per-selection
  (selected products/mappings) manual push, always **preview-first**: the
  operator sees pair, current Shopify value, target value, and delta before
  confirming enqueue. Consistent with MBQ-34's review-then-apply default and
  the operator-flow doc ([ux-operator-flow.md](ux-operator-flow.md)).
- **[Proposed product decision — scheduled]** Per-store schedule
  configuration for the reconciliation sweep (cadence within DEC-010's
  cron-cadence caveat, exact default to Task 013 revision); event-driven
  pushes need no schedule.
- **[Proposed product decision — audit]** Every push leaves job-log evidence:
  pair identity, **old value → new value**, the `compareQuantity` basis, the
  idempotency key, trigger origin (odoo_event / scheduled_sync / manual_sync),
  and outcome — enough to reconstruct any storefront quantity after the fact.

## 9. Large-catalog performance

- **[Fact — budget]** The accepted inventory throughput budget is **PB-20: ≥
  300 level-pushes/hour sustained within the Shopify throttle budget**
  ([performance-budgets.md](../03-architecture/performance-budgets.md)).
  (Note: the mission brief cited PB-22/PB-23; in the budgets file those cover
  media export and the 011B backfill — the inventory row is **PB-20**. This
  document aligns to the file.)
- **[Proposed product decision]** Batch sizing: multi-entry
  `inventorySetQuantities` batches sized to stay under GraphQL cost limits
  (start conservative, e.g. 25–50 entries; tune in the Task 013 dev-store
  run). Reads paginate with cursor-based pagination. The client's existing
  `throttleStatus` pacing governs send rate.
- **[Proposed product decision — backlog behavior]** Under backlog,
  last-value-wins coalescing (§4.2) means the queue depth is bounded by the
  number of *pairs*, not the number of stock events; the sweep re-verifies
  convergence. Backlog age is surfaced per store.

## 10. Partial failures

- **[Proposed product decision]** `inventorySetQuantities` returns per-entry
  `userErrors`: a failed entry routes **only that pair's record** to
  retry/review with the error captured; the rest of the batch's successes are
  committed and logged normally. Store-level failures (auth, throttle
  exhaustion) fail the batch as one unit into the standard job retry path.

## 11. Reconnect catch-up

- **[Proposed product decision]** After a store reconnects (or resumes from
  suspension/quiescence — see
  [disconnect-quiescence-remediation-analysis.md](../03-architecture/disconnect-quiescence-remediation-analysis.md)
  and the reconnection lifecycle in [mvp-scope.md](mvp-scope.md)), the
  connector performs a **reconciliation read of all mapped InventoryLevels
  before resuming any pushes**: stale pending targets are recomputed against
  fresh Shopify values so the first post-reconnect writes carry valid
  `compareQuantity` bases. No stored pre-disconnect mutation is replayed
  blind (§6).

## 12. Test/UAT hooks, wave allocation, decisions, open questions

### Test/UAT hooks

- CAS mismatch → bounded retry → review case (simulated concurrent change).
- Idempotency: duplicate attempt with same UUID within 24h returns cached
  response, no double write.
- Context pitfall regression: `free_qty` for a mapped child location must not
  equal the all-locations aggregate in a multi-location fixture.
- Negative `free_qty` → clamp-to-0 push + divergence warning.
- Inactive Shopify location → mapping flagged, push suspended.
- Unmapped-item count surfaced; conflicting mapping rejected at create.
- Baseline preview/confirm flow per MBQ-33/34; drift-abort per D-013B-4.
- PB-20 throughput run (≥ 300 pushes/hr) on the dev store.
- Reconnect: reconciliation read precedes first post-reconnect push.

### Wave allocation

- **Wave 3 = revised Task 013 + 013B**, runnable only after DEC-031 Layer 2 is
  **accepted and implemented** (Layer 2 itself is a prior wave's deliverable).
  Program state: [mvp-program-state.md](../07-implementation-plan/mvp-program-state.md).

### Proposed product decisions in this document (for acceptance)

1. Export figure = per-mapped-location `free_qty`; `virtual_available` opt-in only (§1).
2. Location-mapping uniqueness constraints + overlap validation (§2).
3. Inactive-location suspension + review (§2, §7).
4. Coalesced absolute last-value-wins pending-update design (§4.2).
5. Read→compare→set CAS flow, bounded retries, no `ignoreCompareQuantity` (§4.4).
6. Per-attempt UUID persisted before the call (§4.5, §6).
7. Shopify→Odoo = read/verify + review cases only (§5).
8. Layer 2 attempt-record + reconciliation-before-replay contract (§6).
9. Negative-quantity clamp+warn default (§7).
10. Manual preview-first push, per-store schedule, old→new audit evidence (§8).
11. Batched multi-entry sets with per-entry error routing (§9, §10).
12. Reconnect reconciliation-read-before-push (§11).

### Open questions

- [Open question] Does Shopify accept/render negative `available` via
  `inventorySetQuantities`? Verify before offering the push-negative option (§7).
- [Open question] Exact batch size vs GraphQL cost for multi-entry
  `inventorySetQuantities` — measure in the Task 013 dev-store run (§9).
- [Open question] Expiry-date (`with_expiration`) interaction with `free_qty`
  (carried from the Odoo capture §3).
- [Open question] Default reconciliation-sweep cadence (DEC-010 caveat;
  Task 013 revision to propose).

---

*Sources relied on: [DEC-010](../04-decisions/DEC-010-inventory-architecture-strategy.md)
(Accepted), [DEC-018](../04-decisions/DEC-018-mbq-decision-batch-1.md) (MBQ-33/34),
[DEC-031](../04-decisions/DEC-031-core-r2-job-execution-replay-safety.md),
[Shopify captures 2026-07-16 §9](../00-source-materials/shopify-orders-cod-abandoned-fulfillment-captures-2026-07-16.md)
(Accessible, 2026-07-16),
[Odoo captures 2026-07-16 §3](../00-source-materials/odoo19-sale-stock-security-captures-2026-07-16.md)
(Accessible, 2026-07-16),
[Task 013](../07-implementation-plan/task-013-inventory-sync-implementation-packet.md) /
[Task 013B](../07-implementation-plan/task-013b-initial-inventory-baseline-packet.md) packets,
[rejected-approaches-log](../05-qa/rejected-approaches-log.md) (RA-008/018/019/020/021),
[performance-budgets](../03-architecture/performance-budgets.md) (PB-20).*
