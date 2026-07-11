# Task 014 — Fulfillment & Tracking Write-Back: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §8 is NOT usable.** Produced 2026-07-10 (AR-042 candidate).
> Closes OP-20 (naming + criteria + **exact scope set**, which also
> routes the TD-002 fix) at proposal level. Evidence: captures §4/§8/§9;
> ARCH §3–§7. API 2026-07 (ARCH PD-6). The write model is already
> decided (DEC-011: FulfillmentOrder-based mutations exclusively;
> RA-022 bans legacy endpoints — `fulfillmentCreateV2` confirmed
> deprecated, `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`
> confirmed current, captures §4).

## 1. Objective, scope, non-goals

Create `shopify_connector_fulfillment` (new module, Full edition;
depends `['shopify_connector_core', 'shopify_connector_sale',
'stock_delivery', 'sale_stock']` — MBQ-60 decided for
stock_delivery; **`sale_stock` red-team-added**: `picking.sale_id`,
`move.sale_line_id`, and confirmation-time picking generation all
live in that bridge module, and relying on it transitively would be
luck, not architecture): validated outgoing pickings
become Shopify fulfillments with tracking, exactly once, notification
off by default. Includes its own triggers (picking-validation
`odoo_event` hook, tracking-update hook, reconciliation scan, manual
retry surface) per the revised Area-6 split. **Non-goals:** no
inventory logic and no read of the location-mapping table
(structural: no dependency on `shopify_connector_inventory`); no
refunds/returns/RMA; no FULFILLMENT_ORDERS_* lifecycle subscriptions
(MBQ-61 exclusion unchanged; holds handled read-only per D-014-5); no
`fulfillmentOrderMove` in MVP (location mismatch → review, never a
move — flagged decision D-014-6); no UI; no webhooks.

## 2. Decision closures (D-014-1 … D-014-8) — each Proposed

**D-014-1 — Binding (MBQ-55-adjacent; keying refinement flagged).**
`shopify.connector.fulfillment.binding`
(`shopify_connector_fulfillment_binding.py`) on the mixin —
**`shopify_gid` = the created Fulfillment GID** (not the
FulfillmentOrder GID: a backorder chain fulfills one FO through
several pickings, so FO-GID uniqueness would break; ARCH §3 explains
the refinement, carried here for explicit ChatGPT review). Fields:
`picking_id` (M2o `stock.picking`, required, index, restrict),
`order_binding_id` (M2o `shopify.connector.order.binding`, required,
index, restrict — store-consistency checked),
`shopify_fulfillment_order_gids` (Text ro — JSON list, audit),
`tracking_numbers_snapshot` (Text ro), `tracking_company_snapshot`
(Char ro), `notify_customer_sent` (Boolean ro — the enqueue-time
persisted decision), `shopify_status_snapshot` (Char ro),
`shopify_last_synced_at` (Datetime ro). Constraints:
`UNIQUE(store_id, shopify_gid)` + `UNIQUE(store_id, picking_id)` —
each validated picking is exactly one fulfillment event (DEC-011).

**D-014-2 — Exact scope set + the TD-002 fix (OP-20/OP-03).**
Task scopes: **`read_merchant_managed_fulfillment_orders` +
`write_merchant_managed_fulfillment_orders`** (the FulfillmentOrder
family governs the FO object; `read_orders` alone covers the
Fulfillment object but NOT FulfillmentOrder traversal — captures §4;
`read_assigned_*`/`third_party_*` are fulfillment-service-app scopes,
not this connector's case). **TD-002 fix (the sanctioned narrow core
edit):** in `shopify_connector_readiness_check.py`,
`REQUIRED_MVP_SCOPES` replaces `read_fulfillments` (governs
FulfillmentService only — verbatim scopes-table capture §9) with
`read_merchant_managed_fulfillment_orders`; plus a new
seam-appended essential check (active only when
`fulfillment_domain_enabled`): `write_merchant_managed_fulfillment_orders`
present. One-line constant change + its updated core test — explicitly
named in the allowlist; TD-002 → Resolved on merge.

**D-014-3 — Trigger picking identification (closes the unnumbered
open item).** Eligible picking: `picking_type_code == 'outgoing'` AND
`location_dest_id.usage == 'customer'` AND `state == 'done'` AND
`sale_id` resolves to an order binding of a connected store with the
domain enabled. In multi-step delivery flows only the final
customer-bound leg satisfies `location_dest usage='customer'` — the
blueprint's "goods actually leave the warehouse" rule made mechanical.
Each backorder picking meeting the rule is its own independent event.
Hook: `stock.picking._action_done` override enqueues
`fulfillment_create_sync` (`job_source='odoo_event'`,
`trigger_origin='fulfillment_picking_validation'` — DEC-019;
`res_model/res_id` = the picking, since the binding does not exist
yet — a documented deviation from the bind-row targeting precedent).

**D-014-4 — Matching chain (consumes D-012's line GIDs).** picking →
`sale_id` → order binding → order GID → query
`order.fulfillmentOrders(first: 10)` **without a server-side status
filter** (red-team-fixed: `query:"status:open"` would exclude
IN_PROGRESS FOs, which are exactly the state of a partially-fulfilled
backorder chain), selecting `status ∈ {OPEN, IN_PROGRESS}`
client-side → for each
picking move line: `move.sale_line_id.shopify_line_item_gid` → the FO
line item whose `lineItem.id` matches; quantity = the move's done
`quantity` (19.0 field — captures §8), must be ≤ `remainingQuantity`
else `blocked_manual_review`/`ambiguous_match`. Lines that cannot
resolve (no `shopify_line_item_gid` — e.g. manually-added SO lines, or
no matching FO line) → `mapping_missing`/`failed_retryable` (RA-023:
never fulfill by guess). Mutation:
`fulfillmentCreate(fulfillment: {lineItemsByFulfillmentOrder:
[{fulfillmentOrderId, fulfillmentOrderLineItems: [{id, quantity}]}],
trackingInfo, notifyCustomer, originAddress: omitted})` — explicit
line lists always (never the fulfill-everything default), ≤512 lines
per FO input (captures §4).

**D-014-5 — Location & holds (single-location Phase 1).** All matched
FOs must share one `assignedLocation.location.id` (live read
authoritative — MBQ-43); a mismatch between FOs, or an FO
`status == ON_HOLD`/`SCHEDULED`/`INCOMPLETE`, →
`blocked_manual_review`/`ambiguous_match` (the accepted blueprint-level
widening). The connector never places/releases holds and never calls
`fulfillmentOrderMove` (D-014-6): with no inventory-mapping dependency
allowed, it cannot know the "right" location — operator resolves in
Shopify admin, then retries. Flagged alternative for ChatGPT: allow
`fulfillmentOrderMove` when exactly one candidate location exists —
rejected here as an unnecessary write surface for MVP.

**D-014-6 — Tracking mapping (exact).** `carrier_tracking_ref` →
`trackingInfo.number` (if it contains commas/semicolons, split into
`numbers[]` — position-matched `urls[]` only when a URL list of equal
length exists, else omit urls); `carrier_id.name` →
`trackingInfo.company` **as-is** (exact-match against Shopify's
carrier list is capitalization-sensitive and unvalidated client-side
in MVP — no client-side carrier table is shipped);
`carrier_tracking_url` → `trackingInfo.url` (a supplied URL renders
regardless of company recognition — captures §4). Missing tracking ref
entirely → fulfillment is still created without trackingInfo (goods
shipped is the fact being recorded), with a job-log note.
**Tracking-update path:** post-fulfillment writes to
`carrier_tracking_ref`/`carrier_tracking_url` on a bound picking →
`fulfillment_tracking_update` job → `fulfillmentTrackingInfoUpdate
(fulfillmentId, trackingInfoInput, notifyCustomer: persisted
decision)` — updates in place, never a second fulfillment (captures
§4). **Job classification (red-team-added — the merged
`trigger_origin` vocabulary has no value for this event):**
`job_source='odoo_event'` with a **third trigger-origin value
`fulfillment_tracking_change`, added via `selection_add` on the core
`trigger_origin` Selection from this module** (the same field-extension
pattern as `job_type`; no core file edit). Because DEC-019 accepted
exactly two trigger-origin concepts at decision level, this third
value is a **proposed DEC-019 vocabulary extension**, flagged as its
own review item (master plan §1 call 7) — not silently assumed.

**D-014-7 — Idempotency & ambiguous outcomes (RA-014 mechanics).**
`fulfillmentCreate` is **NOT `@idempotent`** (verified — the 17-entry
list is inventory/location/refund only, captures §4), so:
(1) duplicate prevention — stated honestly (red-team-corrected): the
binding row cannot exist before the mutation (its `shopify_gid` is
the created Fulfillment GID and the mixin requires it), so
**pre-send** protection is the `operation_scope_key`
(store|stock.picking|id) serialization alone — a mechanism whose
behavior under real concurrent workers is explicitly unproven (ARCH
§5.12 caveat applies with full force here); `UNIQUE(store_id,
picking_id)` catches any duplicate **after** the first success, and
the verification read (below) is the recovery net between the two;
(2) ambiguous outcome (timeout/unknown): **verification read before
any retry** — re-query the order's `fulfillments(first: 50)` +
FO `remainingQuantity`; a fulfillment whose `trackingInfo.number`
matches ours, or whose creation is corroborated by the FO's
`remainingQuantity` having decreased by exactly our quantities, is
adopted (binding created from the read, job succeeds); definitively
absent → one re-send per retry cycle; inconclusive (no tracking to
match AND ambiguous quantities) → `blocked_manual_review` /
`duplicate_risk`. Both the operation key and the verification read are
required together (accepted rule). `notifyCustomer` is persisted at
enqueue (`notification_default_enabled`, default False) and **never
re-read at retry** (RA-009); absent explicit enablement no
notification is ever sent — `fulfillment notification confirmation
missing` review class applies when a per-store confirmation is
required but absent (settings flag `fulfillment_notification_confirmed`
must be True when `notification_default_enabled` is True).

**D-014-8 — Reconciliation & readiness.** Scan job
(`fulfillment_reconciliation_check`, cron 60 min default;
`job_source='reconciliation'`; per-run `payload_hash` uuid4 nonce —
the repeat-run rule, as Task 013's scan): for bound
pickings, re-read Fulfillment `status`/`trackingInfo` → snapshot
updates + drift notes (status CANCELLED on Shopify side →
`blocked_manual_review`/`binding_conflict`; nothing auto-changes in
Odoo). Readiness (seam): `stock_delivery` installed is implied by the
manifest; check = write scope present + (if notification enabled)
confirmation flag set — `stock_delivery` absence is impossible at
runtime (hard dependency), satisfying MBQ-60's "named blocker, never
silent degradation" via install-time enforcement (documented).

## 3. Gate criteria (fulfillment domain, 15-pattern)

1 Task 012 closed runtime-green (prerequisite: order bindings + line
GIDs exist); 2 naming accepted (=D-014-1 incl. the keying refinement);
3 exact names ✅; 4 files ✅(§8); 5 dedup/ambiguous-outcome mechanics
fixed ✅(D-014-7); 6 no inventory scope ✅ (structural); 7 no
product/order-import scope ✅; 8 no UI/webhook/OAuth ✅; 9 tests
✅(§5); 10 rollback ✅ (single-PR revert; created Shopify fulfillments
remain — no auto-unfulfill; inventory unaffected); 11 live-dependency
controlled (mutations exist — dev-store evidence or recorded waiver,
as Task 013); 12 gate-act reconfirmation; 13 notification
default-off + persisted-decision boundary explicit ✅(D-014-7); 14
scope set + TD-002 fix explicit ✅(D-014-2); 15 unmatched/mismatch
handling explicit ✅(D-014-4/5).

## 4. Store settings added

`fulfillment_notification_confirmed` (Boolean default False),
`fulfillment_last_reconciliation_at` (Datetime ro, domain checkpoint).

Job-type → flag map (exhaustive): `fulfillment_create_sync`,
`fulfillment_tracking_update`, `fulfillment_reconciliation_check` all
map to `fulfillment_domain_enabled`. Logging: all free text routes
through `_system_append` (core redaction); tracking numbers and
carrier names are operational data, not PII — but recipient names
never appear in fulfillment log messages (source-guard test).

## 5. Tests (exact files)

`test_fulfillment_binding.py` (schema, dual uniqueness incl.
backorder-chain non-collision: two pickings/two bindings/one FO GID in
both rows' JSON); `test_fulfillment_trigger.py` (eligibility rule
matrix incl. multi-step legs, backorder independence, domain gating,
hook enqueue with odoo_event/trigger_origin);
`test_fulfillment_matching.py` (line-GID chain, quantity ≤ remaining,
unmatched → mapping_missing, multi-location/hold/scheduled →
ambiguous_match, explicit-line-list guard [source-level: the literal
omission-of-fulfillmentOrderLineItems path must not exist]);
`test_fulfillment_idempotency.py` (verification-read-adopt /
absent-resend / inconclusive-review paths; no blind retry
[source-level: creation call unreachable without a preceding
verification read on retry]; notifyCustomer persisted-at-enqueue
including retry-preserves-decision; second validate on same picking
blocked by constraints); `test_fulfillment_tracking_update.py`
(in-place update path, multi-number split, company passthrough,
missing-ref creation with note); `test_fulfillment_readiness_td002.py`
(REQUIRED_MVP_SCOPES contains read_merchant_managed_fulfillment_orders
and not read_fulfillments; seam check behavior). Runtime: Odoo.sh
green (SRR-06) + dev-store evidence or recorded ChatGPT waiver
(mutation task, as Task 013). TD-002 core-test update runs inside the
core suite.

## 6. Acceptance criteria / DoD / rollback

Every validated eligible picking → exactly one fulfillment (never
double, never merged across backorders); no blind retry anywhere;
notification default-off proven incl. retry; RA-022 respected
(source-level: only `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`
mutations exist, no V2/REST); zero inventory/refund/payout logic;
TD-002 resolved with tests; suites + Odoo.sh green; validation record +
AR row + handoff; draft PR; gate closes on draft-open.

## 7. Register impacts on acceptance

OP-20 → Resolved-by-packet (naming + criteria + scope set); OP-03 /
TD-002 → fix routed here, Resolved on merge; MBQ-40/42/43 residuals →
Resolved at packet level (backorder linkage used for audit labeling;
live-location-read rule; mismatch → review); MBQ-61 exclusion restated.

## 8. Locked final implementation prompt (Task 014)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE FULFILLMENT-DOMAIN GATE, VERIFIES THE CURRENT
BASE SHA, AND ISSUES THIS PROMPT.

Implement Task 014 — fulfillment/tracking write-back — as the NEW
module addons/shopify_connector_fulfillment, exactly per
docs/07-implementation-plan/task-014-fulfillment-tracking-implementation-packet.md
(D-014-1..8 binding) and ARCH §3–§7. Branch from the verified current
Shopify-connector tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive): addons/shopify_connector_fulfillment/**
(NEW: __init__.py, __manifest__.py [depends shopify_connector_core,
shopify_connector_sale, stock_delivery, sale_stock], models/{__init__.py,
shopify_connector_fulfillment_binding.py,
shopify_connector_fulfillment_service.py [service + seams + hooks],
shopify_connector_store_settings.py}, security/ir.model.access.csv,
data/shopify_connector_fulfillment_cron.xml [reconciliation cron,
noupdate=1], tests/{__init__.py + the six §5 files});
addons/shopify_connector_core/models/shopify_connector_readiness_check.py
(THE ONE NAMED CORE EDIT: REQUIRED_MVP_SCOPES swaps read_fulfillments
-> read_merchant_managed_fulfillment_orders — nothing else in the
file); addons/shopify_connector_core/tests/test_readiness_check.py
(the matching assertion update only);
docs/05-qa/task-014-fulfillment-tracking-validation-results.md (NEW);
docs/05-qa/technical-debt-register.md (TD-002 row: Resolved note);
docs/05-qa/architecture-review-log.md (append row);
docs/01-research/research-handoff.md (top entry).
FORBIDDEN: every other core file; every product/sale/inventory file;
any read of shopify.connector.location.mapping (must not even import
it); fulfillmentOrderMove/Hold/ReleaseHold and every FULFILLMENT_ORDERS_*
subscription; legacy fulfillment endpoints; refunds/returns; UI/
webhooks/OAuth/CI; adams_base.

HARD CONSTRAINTS: FulfillmentOrder-based mutations exclusively
(fulfillmentCreate / fulfillmentTrackingInfoUpdate); explicit line
lists always; FO selection client-side over OPEN+IN_PROGRESS (no
server status filter — D-014-4); the tracking-update job uses
odoo_event + the selection_add-extended trigger_origin
'fulfillment_tracking_change' (D-014-6, a flagged DEC-019 vocabulary
extension); verification-read-before-retry, never blind (RA-014);
operation key + serialization via operation_scope_key; notifyCustomer
persisted at enqueue, default off, never re-read (RA-009); unmatched
picking never fulfilled by guess (RA-023); single-location Phase 1
(mismatch/hold -> ambiguous_match review); concurrency caveat restated
not resolved; Odoo.sh green before merge review (verbatim quote) plus
dev-store evidence or a recorded explicit ChatGPT waiver. Stop
condition: draft PR "Task 014: Shopify fulfillment/tracking write-back
(shopify_connector_fulfillment)"; gate closes on draft-open; no Task
015/UI/webhook work.
```
