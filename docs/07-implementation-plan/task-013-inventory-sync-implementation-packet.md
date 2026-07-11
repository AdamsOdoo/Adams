# Task 013 — Inventory Synchronization: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §8 is NOT usable.** Produced 2026-07-10 (AR-042 candidate).
> Closes OP-18/OP-19 (naming pass + gate criteria + MBQ-32 residual)
> and MBQ-38 at proposal level. Evidence: captures §3/§8/§9; ARCH
> §3–§7 (shared contracts not restated). API 2026-07 (ARCH PD-6).
> MBQ-33 (per-mapped-pair first-push granularity) and MBQ-34
> (review-then-apply default) verified **Decided — DEC-018** against
> the live register this session; this packet carries them as settled.

## 1. Objective, scope, non-goals

Create `shopify_connector_inventory` (new module, Full edition; depends
`['shopify_connector_core', 'shopify_connector_product', 'stock']`):
explicit location mapping, per-location inventory-level bindings,
first-push guard, and the Odoo→Shopify `available`-quantity push via
`inventorySetQuantities` — Odoo is the standing source of truth
(DEC-010). Includes the module's own trigger surfaces (stock-change
`odoo_event` hook, scheduled push-scan cron, manual service methods)
per the revised Area-6 split
(`area-6-sync-triggers-implementation-packet.md` D-A6-1). **Non-goals:** no fulfillment logic or reads of anything
fulfillment-owned; no product import/export; no standing Shopify→Odoo
inventory pull (one-time reviewed baseline import is **deferred out of
Task 013** to a future explicitly-gated 013B — flagged decision
D-013-8); no webhooks (MBQ-63 exclusion unchanged); no `committed`
writes ever (RA-018); no UI (S10–S12 are UI-phase).

## 2. Decision closures (D-013-1 … D-013-8) — each Proposed

**D-013-1 — Models (MBQ-55-adjacent naming, OP-18).**
(a) `shopify.connector.location.mapping`
(`shopify_connector_location_mapping.py`) on the binding mixin
(`shopify_gid` = Shopify Location GID; `match_key='manual'` always —
no name inference, DEC-010): `odoo_location_id` (Many2one
`stock.location`, required, index, `ondelete='restrict'`, domain
`usage='internal'`), `shopify_location_name_snapshot` (Char ro),
`push_enabled` (Boolean default True). Constraints:
`UNIQUE(store_id, odoo_location_id)` + `UNIQUE(store_id, shopify_gid)`.
Validation constraint: for one store, no mapped location may be an
ancestor or descendant of another mapped location (prevents
double-counting via subtree aggregation).
(b) `shopify.connector.inventory.level.binding`
(`shopify_connector_inventory_level_binding.py`) on the mixin
(`shopify_gid` = InventoryLevel GID, set on activation/first read; may
be empty before — **which requires an explicit field override
`shopify_gid = fields.Char(required=False, readonly=True, index=True)`
in this model, red-team-added: the mixin declares it `required=True`,
and this is the one deliberate deviation, called out in ARCH §3**):
`product_variant_binding_id` (M2o, required, index,
restrict), `location_mapping_id` (M2o, required, index, restrict),
`shopify_inventory_item_gid` (Char required index ro — from
`variant.inventoryItem`, the 1:1 direction that remains non-null,
captures §3), `last_pushed_available` (Float ro), `last_pushed_at`
(Datetime ro), `last_push_idempotency_key` (Char ro),
`last_known_shopify_available` (Float ro), and the **MBQ-38
first-push confirmation record**, kept on the row (per-mapped-pair
granularity = per binding row, exactly DEC-018's MBQ-33 decision):
`first_push_state` (Selection pending/previewed/confirmed, default
pending, readonly), `first_push_preview_qty` (Float ro),
`first_push_confirmed_at` (Datetime ro), `first_push_confirmed_by_uid`
(M2o res.users ro). Constraints:
`UNIQUE(store_id, shopify_inventory_item_gid, location_mapping_id)`
(the accepted RA-019 identity) +
`UNIQUE(store_id, product_variant_binding_id, location_mapping_id)`.

**D-013-2 — Quantity source (MBQ-32 residual, OP-19).** The pushed
quantity is **`product.product.free_qty` evaluated with the location
context** (`with_context(location=odoo_location_id.id)`), which
aggregates over the mapped location's internal subtree — verified 19.0
source semantics (captures §8): without the `with_expiration` context
key the expired term is zero, so `free_qty ≡ Σ
stock.quant.available_quantity` over the subtree, dissolving the C1
divergence for this code path; the packet's tests must include the
expired-unreserved acceptance case proving the equality holds without
the context key. No configurable Forecast/On-Hand source in MVP
(`on_hand` exposure already excluded, MBQ-35). Negative values are
**clamped to 0** with a job-log note (the Shopify negative-set
question is officially ambiguous — captures §3 open question; 0 is
the safe anti-oversell floor). Write target: Shopify **`available`**
only (accepted; `InventorySetQuantitiesInput.name` accepts only
available/on_hand — captures §3).

**D-013-3 — Push mutation mechanics.** `inventorySetQuantities` with
`name: "available"`, `reason: "correction"` (documented vocabulary),
`referenceDocumentUri: "odoo://<db-uuid>/shopify.connector.job/<id>"`,
one item per job (D-013-6): `quantities: [{inventoryItemId,
locationId, quantity, changeFromQuantity}]` — **`changeFromQuantity` =
`last_known_shopify_available`** (fresh-read value; the 2026-07 CAS
shape — `compareQuantity`/`ignoreCompareQuantity` no longer exist,
captures §3), and the mutation carries the **mandatory
`@idempotent(key: "<uuid4>")` directive** (required as of 2026-04).
**Key storage (red-team-corrected):** the `@idempotent` key lives on
the **binding** only (`last_push_idempotency_key`), paired with a
`last_push_params_hash` (hash of item|location|qty|changeFrom) — it is
NOT stored in the job's `payload_hash` (whose merged contract reserves
the nonce use for target-less job types and which feeds the job's
immutable `idempotency_key`). At each dispatch attempt the handler
compares the current computed params-hash with the stored one: equal →
**reuse the stored key verbatim** (the safe ambiguous-outcome retry —
the accepted `@idempotent`-eligible auto-retry path, DEC-009);
different (e.g. after a CAS-stale fresh read) → generate + persist a
new key/params pair. The job's own `payload_hash` is the content hash
of the enqueue-time outbound payload (qty + CAS value), per the merged
contract; the 5→3→5 same-payload edge is covered because the scan
enqueues only deltas against `last_pushed_available` and an identical
payload re-push is by definition redundant (collision = correct dedup).
Error routing: `CHANGE_FROM_QUANTITY_STALE` →
`concurrency_race_conflict` (auto-retry; the handler's params-hash
comparison yields the fresh CAS value and a new key on that attempt);
`ITEM_NOT_STOCKED_AT_LOCATION` → run `inventoryActivate(item,
location)` (available defaults 0) then re-set — activation is
performed only for `first_push_state='confirmed'` rows;
`INVALID_QUANTITY_NEGATIVE` cannot occur (clamped);
`IDEMPOTENCY_CONCURRENT_REQUEST` → `concurrency_race_conflict`;
`NON_MUTABLE_INVENTORY_ITEM` (bundles) → `blocked_manual_review` /
`binding_conflict`. `InventoryItem.tracked = false` → job `skipped`
with note via the `JobPolicySkip` dispatcher seam that Task 012 adds
(sequencing guarantees it exists; the connector never mutates
`tracked`).

**D-013-4 — First-push guard flow (backend-only until UI).**
Per-pair (per binding row): a preview run (`job_source =
export_preview_dry_run`, job type `inventory_first_push_preview`)
computes and stores `first_push_preview_qty` + sets
`first_push_state='previewed'` and writes the full preview to the job
log; explicit confirmation via service method
`action_confirm_first_push()` (reviewer/admin groups only) records
who/when and sets `confirmed`; the push handler refuses any write for
a row not `confirmed` → `destructive_write_guard_blocked`
(`blocked_manual_review` — one of the six accepted sub-reasons).
Recorded source-of-truth decision = the store-settings
`price_source_of_truth`-analogous field is NOT reused; the
confirmation record itself (who/when/preview) is the recorded
decision, per MBQ-38's closure above. The S11 UI screen later drives
these same methods (PD-2).

**D-013-5 — Location cache population + readiness seam.** New job type
`inventory_location_sync` reads the `locations` query
(`includeInactive: false`, paginated ≤100) and upserts the **core**
`shopify.connector.location` cache rows. The core ACL deliberately
gives no group create/write on the cache; the handler performs the
upsert via a **named, narrow `sudo()` elevation** (the third sanctioned
sudo in the codebase — explicitly flagged for ChatGPT approval as part
of this packet; justification: system-populated cache by design,
AR-019 §10 pattern). Readiness (red-team-corrected — the append seam cannot replace a core
check, and the merged `_check_mapped_location` placeholder returns
essential/NOT_PROVEN unconditionally): this module (a) **overrides
`_check_mapped_location` via `_inherit`** — returning PASS when
`inventory_domain_enabled` is False (not applicable) and the real
mapped-pair verification when True — building on the Area-6 core
rework that first makes the placeholder not-applicable-pass for
stores without the inventory domain (Area-6 packet D-A6-7); and (b)
**appends** one additional essential check via the `_get_checks()`
seam, active only when the domain is enabled: `write_inventory`
present in `granted_scopes`. `REQUIRED_MVP_SCOPES` is untouched by
this task; its TD-002 fix belongs to Task 014.

**D-013-6 — Job granularity & triggers.** One push job per
level-binding change (`res_model`/`res_id` → the binding row;
`operation_scope_key` serializes per pair; `job_type =
'inventory_push_sync'`, gated `inventory_domain_enabled`).
Triggers shipped in-module: (a) **odoo_event hook** — override
`stock.move._action_done` to enqueue push jobs for affected
(variant-binding × mapped-location) pairs (`job_source='odoo_event'`,
`trigger_origin='inventory_stock_change'` — the accepted DEC-019
value); (b) **scheduled push-scan** — ir.cron (15 min default,
noupdate) job `inventory_push_scan` per store
(`job_source='scheduled_sync'`; per-run `payload_hash` **uuid4 nonce**
— red-team-added: scan jobs are repeat-run jobs like the merged
readiness pattern, and without a nonce the second run would collide
on the never-cleared `idempotency_key`; the enqueued per-pair push
jobs inherit `scheduled_sync`) comparing current free_qty vs
`last_pushed_available` and enqueueing deltas; (c) **manual** —
`action_push_inventory_now()` on the store (operator+;
`job_source='manual_sync'`, propagated to the enqueued push jobs),
and per-mapping selective push (`manual_sync`). Reconciliation (accepted backstop):
the scan doubles as drift detection — before pushing, the fresh read's
`available` is compared with `last_pushed_available`; unexplained
Shopify-side drift (differs from both last push and current Odoo) is
pushed over **only after** being logged as a drift note (Odoo-SoT), so
drift is visible in logs while the standing direction is preserved.
Throughput note: per-pair jobs at batch 20/5 min are an accepted MVP
simplification; batching is a named release-hardening candidate, not
in-scope.

**D-013-7 — Concurrency.** CAS + mandatory `@idempotent` +
`operation_scope_key` collectively make the push race-safe **at the
API layer**; the local claim/dispatch caveat (ARCH §5.12) still
applies and is restated in the prompt.

**D-013-8 — Baseline import deferred.** The one-time reviewed
Shopify→Odoo baseline import (accepted as an allowed exception,
DEC-010) is **not** in Task 013: it needs its own preview/apply UX and
would widen this task's write surface into Odoo stock
(`stock.quant.inventory_quantity` adjustments). Routed as future task
candidate 013B, gated separately. Flagged for ChatGPT (alternative:
fold into 013 — rejected here for scope control).

## 3. Gate criteria (inventory domain, 15-pattern)

1 Task 010 runtime-green ✅; 2 naming portion accepted (=D-013-1);
3 exact names ✅; 4 files ✅(§8); 5 thresholds/CAS/idempotency fixed
✅(D-013-3); 6 no product-import/export scope ✅; 7 no
order/fulfillment scope ✅ (structural: no dependency on sale); 8 no
UI/webhook/OAuth ✅; 9 tests ✅(§5); 10 rollback ✅ (single-PR revert;
fulfillment never depends on inventory; live Shopify stock unaffected
by revert); 11 live-dependency controlled (mutations exist —
first-push guard + preview + dev-store validation plan §6); 12 gate-act
reconfirmation (ChatGPT); 13 first-push guard + confirmation record
explicit ✅(D-013-4); 14 quantity source + clamp + tracked-false
scoped ✅(D-013-2/3); 15 ambiguous/unmapped handling ✅ (unmapped →
`inventory_location_missing`; ancestor-overlap constraint; bundle →
`binding_conflict`).

## 4. Store settings added (module's `_inherit` extension)

`inventory_scheduled_sync_enabled` (Boolean default False),
`inventory_last_push_scan_at` (Datetime ro — domain-owned checkpoint,
ARCH PD-5).

Job-type → domain-flag map (red-team-added, exhaustive): all four
job types this module registers (`inventory_push_sync`,
`inventory_push_scan`, `inventory_first_push_preview`,
`inventory_location_sync`) map to `inventory_domain_enabled` via
`_domain_flag_for_job_type()`. Logging: all free text this module
composes routes through `_system_append` (core redaction); payloads
carry GIDs/quantities/location names only — no customer PII exists in
this domain (note recorded to satisfy the cross-packet redaction
check).

## 5. Tests (exact files)

`test_location_mapping.py` (uniqueness both ways, internal-only
domain, ancestor/descendant overlap constraint, no-inference
[creation requires explicit GID], push_enabled);
`test_inventory_level_binding.py` (schema, dual uniqueness, RA-019
identity, confirmation-record fields);
`test_inventory_first_push_guard.py` (blocked before confirm
per-pair; preview records qty; confirm permission matrix; guard
class = destructive_write_guard_blocked);
`test_inventory_push_mechanics.py` (CAS value threading; idempotency
key persisted + reused on same-attempt retry + regenerated on CAS
refresh; stale → race class; activation path; clamp-to-0;
tracked-false skip; reason/referenceDocumentUri; **source-level guard:
the string `committed` never appears as a quantity name, and only
`inventorySetQuantities`/`inventoryActivate` mutations exist in the
module** — no `inventoryAdjustQuantities`, keeping set-semantics
only); `test_inventory_triggers.py` (move-done hook enqueues correct
pairs only for mapped locations + enabled domain; scan enqueues
deltas only; drift note logged; manual action permission);
`test_inventory_location_cache_sync.py` (upsert via the named sudo,
read-only ACL intact, pagination). Runtime: Odoo.sh green mandatory
(SRR-06). **Dev-store validation (new for this task — first mutation
task):** before merge review, a human-operated run against the
existing dev store must execute one confirmed first push + one CAS
round-trip and record redacted evidence in the validation record
(prerequisite: VAL-B2 credentials path — if unavailable, ChatGPT
explicitly waives at gate time and the fact is recorded; the waiver
option is flagged, not assumed).

## 6. Acceptance criteria / DoD / rollback

No write without a confirmed first-push row + mapped location; RA-018
(`committed`) source-guard green; RA-020 respected (no autonomous
bidirectional logic anywhere — the only Shopify-read is the CAS fresh
read + location cache); zero fulfillment/product-export logic; suites
green + Odoo.sh green; validation record + AR row + handoff; draft PR;
gate closes on draft-open. Rollback: single-PR revert; drops
mapping/binding tables; Shopify stock untouched by the revert.

## 7. Register impacts on acceptance

OP-18/OP-19 → Resolved-by-packet; MBQ-32 residual → Resolved (free_qty
+ location context + clamp); MBQ-38 → Resolved (confirmation record on
binding row); MBQ-63 exclusion restated unchanged.

## 8. Locked final implementation prompt (Task 013)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE INVENTORY-DOMAIN GATE, VERIFIES THE CURRENT BASE
SHA, AND ISSUES THIS PROMPT.

Implement Task 013 — inventory synchronization — as the NEW module
addons/shopify_connector_inventory, exactly per
docs/07-implementation-plan/task-013-inventory-sync-implementation-packet.md
(D-013-1..8 binding) and ARCH §3–§7. Branch from the verified current
Shopify-connector tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive): addons/shopify_connector_inventory/**
(NEW: __init__.py, __manifest__.py [depends shopify_connector_core,
shopify_connector_product, stock; LGPL-3], models/{__init__.py,
shopify_connector_location_mapping.py,
shopify_connector_inventory_level_binding.py,
shopify_connector_inventory_service.py [importer/push service, job
seams, hooks, location-cache sync with the ONE named sudo],
shopify_connector_store_settings.py}, security/ir.model.access.csv,
data/shopify_connector_inventory_cron.xml [push-scan cron,
noupdate=1], tests/{__init__.py + the six §5 test files});
docs/05-qa/task-013-inventory-sync-validation-results.md (NEW);
docs/05-qa/architecture-review-log.md (append row);
docs/01-research/research-handoff.md (top entry).
FORBIDDEN: every core/product/sale file (readiness integration is
inheritance-only: the _get_checks append seam for the write_inventory
check PLUS the _inherit override of _check_mapped_location per
D-013-5 — REQUIRED_MVP_SCOPES is NOT touched, that fix is Task
014's); adams_base; views/UI/webhooks/OAuth/CI; any fulfillment or
sale reference; inventoryAdjustQuantities; any Shopify->Odoo stock
write (baseline import is deferred 013B).

HARD CONSTRAINTS: write target 'available' only; 'committed' never
(source-guard test); every mutation carries @idempotent(key: uuid4)
stored on the binding with its params-hash and reused/regenerated per
D-013-3 (2026-04+ requirement) and changeFromQuantity CAS (2026-07
shape); scan jobs carry a per-run payload_hash nonce; job sources per
D-013-6 (scheduled_sync/manual_sync/odoo_event+trigger_origin); first-push guard per pair with
recorded confirmation; unmapped -> inventory_location_missing;
negative -> clamp 0 + note; no flag bypasses any guard; concurrency
caveat (SRR-03/04/09) restated not resolved; Odoo.sh green before
merge review (verbatim quote), plus the §5 dev-store evidence or a
recorded explicit ChatGPT waiver. Stop condition: draft PR "Task 013:
Shopify inventory synchronization (shopify_connector_inventory)",
gate closes on draft-open; no Task 014/015/UI/webhook work.
```
