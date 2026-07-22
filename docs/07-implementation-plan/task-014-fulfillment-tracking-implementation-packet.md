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
become Shopify fulfillments with tracking — duplicate-prevented and, per
DEC-031 Layer 2, at-most-once with reconciliation convergence (never a
claimed exactly-once remote effect; wording corrected 2026-07-16, Fable
gap-closure, to match D-014-7/§9.5) — notification
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
`sale_id` → order binding → order GID → query the order's
`fulfillmentOrders` **cursor-paginated to completion** (`pageInfo.hasNextPage`/
`endCursor`, fail-closed safety cap — §11.4 pagination contract **supersedes** any
fixed `first: N` window) **without a server-side status
filter** (red-team-fixed: `query:"status:open"` would exclude
IN_PROGRESS FOs, which are exactly the state of a partially-fulfilled
backorder chain), selecting `status ∈ {OPEN, IN_PROGRESS}`
client-side (each FO's line items likewise cursor-paginated to completion) → for each
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
(2) ambiguous outcome (timeout/unknown): **reconcile-only, never a
second send** *(P0-corrected 2026-07-22 — §11.1 supersedes the earlier
"absent → resend" wording)*. Once C2 commits `transport_attempted=true`
the job **transitions to reconciliation** and re-queries the order's
`fulfillments`/`fulfillmentOrders` **cursor-paginated to completion**
(§11.4) + FO `remainingQuantity`. Post-C2 the verdict has only **two
actionable outcomes**: **APPLIED** — a fulfillment whose
`trackingInfo.number` matches ours, or whose creation is corroborated by
`remainingQuantity` having decreased by **exactly** our quantities — is
adopted (binding created from the read, job succeeds); **INCONCLUSIVE**
for **everything else**. Under the currently researched Shopify contract
**no request-specific signal proves an already-attempted mutation was not
applied**, so **post-C2 `NOT_APPLIED` is not an actionable Wave 4 verdict
and never authorizes a replacement mutation**. **Read absence is
INCONCLUSIVE, never `not_applied`, and never authority to resend**; after
`INCONCLUSIVE_RECONCILIATION_CAP=3` → `duplicate_risk` manual review.
Only a **pre-C2 / `transport_attempted=false`** failure (nothing sent) or
a **synchronous `userErrors` clean rejection** uses a normal bounded
replacement job (new `payload_hash`). Both the operation-scope key and the
reconcile read are required together (accepted rule). `notifyCustomer` is persisted at
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
controlled (mutations exist — dev-store evidence **required**; any exception is a
specific product-owner ruling on the record, **not a routine waiver** — §11.8);
12 gate-act reconfirmation (**control-room acceptance, not draft-open — §11.8**);
13 notification
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
`test_fulfillment_idempotency.py` (reconcile-only after
`transport_attempted=true`: post-C2 has only **APPLIED→adopt / INCONCLUSIVE**
(**no post-C2 `NOT_APPLIED` replacement**); a replacement is reachable **only**
from pre-C2/`transport_attempted=false` or a synchronous `userErrors` clean
rejection; the shared `fulfillment_mutation_reconcile` **cannot enqueue another
mutation**; **read-absence→INCONCLUSIVE→`duplicate_risk`** — never a
second mutation from absence [source-level: no second `fulfillmentCreate`/
`fulfillmentTrackingInfoUpdate` is reachable from a mere read miss];
no-tracking uncertain outcome fails closed; **possible-`notifyCustomer`
uncertainty fails closed** (never repeated from absence); notifyCustomer
persisted-at-enqueue including retry-preserves-decision; second validate on
same picking blocked by constraints); `test_fulfillment_tracking_update.py`
(in-place update path, multi-number split, company passthrough,
missing-ref creation with note); `test_fulfillment_readiness_td002.py`
(REQUIRED_MVP_SCOPES contains read_merchant_managed_fulfillment_orders
and not read_fulfillments; seam check behavior). Runtime: Odoo.sh
green (SRR-06) + dev-store evidence **required** (any exception = a specific
product-owner ruling on the record, **not a routine ChatGPT waiver** — §11.8). TD-002 core-test update runs inside the
core suite.

## 6. Acceptance criteria / DoD / rollback

Every validated eligible picking → exactly one fulfillment (never
double, never merged across backorders); no blind retry anywhere;
notification default-off proven incl. retry; RA-022 respected
(source-level: only `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`
mutations exist, no V2/REST); zero inventory/refund/payout logic;
TD-002 resolved with tests; suites + Odoo.sh green; validation record +
AR row + handoff; draft PR; ~~gate closes on draft-open~~ **[superseded — §11.8:
the gate needs control-room acceptance, not draft-open]**.

## 7. Register impacts on acceptance

OP-20 → Resolved-by-packet (naming + criteria + scope set); OP-03 /
TD-002 → fix routed here, Resolved on merge; MBQ-40/42/43 residuals →
Resolved at packet level (backorder linkage used for audit labeling;
live-location-read rule; mismatch → review); MBQ-61 exclusion restated.

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):** every new
fulfillment **`job_type`** `selection_add` `ondelete` uses the LC-1 job-type
sink `_reassign_to_historic_job_type` from the start (LC-1 precedes Task 012 —
DEC-030 / lifecycle §7). The **`fulfillment_tracking_change` `trigger_origin`**
value instead uses a **dedicated** callable
`_normalize_tracking_change_trigger_origin_on_uninstall` — the job-type sink
cleans `job_type` only and cannot remove a trigger-origin value, so it is not a
valid cleanup for the removed value (see §11.5).

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

---

## 9. Addendum (2026-07-16) — [Proposed] Fable gap-closure requirements

> **Status: Proposed — Fable gap-closure mission, 2026-07-16. NOT accepted.**
> Appended per the gap-closure mission; nothing above this line is rewritten.
> **Every D-014 closure (D-014-1..8) remains intact and binding** — this
> addendum adds requirements on top of them and maps the accepted-canon
> gap-closure documents onto this packet. **Re-acceptance required:** the
> packet + this addendum must be re-reviewed and re-accepted as one unit, and
> the §8 locked prompt re-issued against the amended packet, before Wave 4
> opens (see [`wave-4-definition-of-ready.md`](wave-4-definition-of-ready.md)
> gate G4-5). Sources mapped here:
> [`../02-product/fulfillment-operating-modes.md`](../02-product/fulfillment-operating-modes.md)
> ("Modes doc"),
> [`../02-product/shopify-fulfillment-status-model.md`](../02-product/shopify-fulfillment-status-model.md)
> ("State model"),
> [`../02-product/cod-lifecycle-and-reconciliation.md`](../02-product/cod-lifecycle-and-reconciliation.md)
> ("COD doc"), and
> [`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md)
> (Layer 2).

### 9.1 Operating modes (Modes doc §1–§2, §6–§8)

- New store setting `fulfillment_operating_mode` (Selection `mode1`/`mode2`,
  default `mode1`, Administrator-only via Python-level `groups=`), added to
  §4's settings list. **Wave 4 ships both Mode 1 and Mode 2 backend** — the
  mode field is live with both values selectable and effective; switching a
  store to Mode 2 follows the mode-switch state machine and its scan-gated
  prerequisites (Modes doc §6, §8), not a not-yet-available configuration hold.
  **Wave 4 cannot close until both Mode 1 and Mode 2 backend behavior is
  implemented, tested, and dev-store runtime-proven; Wave 5 owns only the
  premium mode UI, not the Mode 2 backend** (Modes doc §10).
  > **[Product-direction update — 2026-07-16]** This supersedes the earlier
  > "Wave 4 ships Mode 1 only / Mode 2 deferred to a Wave 5 allocation"
  > stance: per the binding product-owner ruling, both Mode 1 and Mode 2 are
  > mandatory Wave 4 backend scope and Wave 5 owns only the mode UI. Proposed —
  > re-acceptance required; authorizes no implementation.
- Mode 1 inbound posture: observe, classify, record, review — **zero
  automatic Odoo stock mutation** from inbound evidence. User actions from a
  review case: import tracking (non-stock write to
  `carrier_tracking_ref`/URL), acknowledge, or explicitly validate the exact
  proposed action (Modes doc §2.2). The proposal engine is the §4-checklist
  evaluator shared with Mode 2.
- Mode-switch state machine, audit, never-replays-history, scan-gated,
  idempotent, rollback-safe (Modes doc §6) — **both Mode 1 and Mode 2 backend
  behavior lands and is dev-store runtime-proven in Wave 4.**

### 9.2 Inbound reconciliation data model (Modes doc §3, §5)

New models (naming per the merged mixin conventions; exact names a
re-acceptance item):

- **Own-GID create ledger:** the D-014-1 binding rows plus a create-attempt
  ledger covering adopted-by-verification-read fulfillments — the primary
  origin-classification evidence (Modes doc §3 row 1).
- **Per-fulfillment inbound evidence record** (unique per store +
  Fulfillment GID): order/FO identities, origin class
  (`connector`/`external_merchant`/`external_service`/`carrier_event_only`),
  location snapshot + mapped display, tracking snapshot, remote state
  (raw + normalized per the State model), reconciliation state
  (`observed`→`under_review`/`auto_matched`→`applied`/`acknowledged`/
  `rejected`/`superseded`).
- **Per-line evidence record** with the reconciled-quantity ledger
  (over-fulfillment guard) and lot/serial evidence.

The D-014-8 reconciliation scan generalizes to the fulfillment watermark
catch-up (Modes doc §7): reconnect re-scan, and **every disconnected-period
external fulfillment lands as a review case**.

### 9.3 State-model storage and display (State model §1–§10)

- Store all seven Shopify fulfillment enum families (State model Layer A)
  **raw, verbatim**, with normalized
  labels/badges per the State model tables; deprecated values stored-raw +
  normalized (§6); the **unknown-future-value contract (§7)** implemented in
  full (preserve raw, display unknown, never silently success, halt unsafe
  automation, raise schema warning).
- The **carrier-Delivered inconsistency rule (§8)**: milestones never write
  stock; Delivered-with-picking-not-done raises the defined high-visibility
  critical review case.
- The four-layer taxonomy's badge separation (§1) is the data contract Wave 5
  UI consumes; Wave 4 owns the fields, not the screens.

### 9.4 COD interplay (COD doc §3, §9)

Wave 4 owns the COD ↔ fulfillment mechanics for scenarios 2–13: partial
validation quantities, backorder ask/always/never semantics with
Administrator-gated remainder cancellation, `stock.return.picking` as the
**only** stock-restoration path (PD-COD-2 — never on courier/report
evidence), and derivation of the COD fulfillment dimension from picking/
return state. `orderMarkAsPaid` remains out of this packet (Wave 5+, Layer
2-gated — COD doc §9).

### 9.5 Layer 2 supersession note on D-014-7

D-014-7's mechanics (verification-read-before-retry, operation-key
serialization) are retained but now execute **under the accepted DEC-031
Layer 2 protocol**: durable attempt record before every mutation,
`fulfillmentCreate`/`fulfillmentTrackingInfoUpdate` rows in the Layer 2
reconciliation matrix, and reconciliation reads as first-class jobs. The
D-014-7 concurrency caveat is answered by Layer 2's ownership design rather
than restated-unresolved; Wave 4 must not ship these mutations outside
Layer 2 (program hard-stop 4).

### 9.6 New settings, acceptance rows, test families (delta to §4–§6)

- **Settings added (beyond §4):** `fulfillment_operating_mode` (§9.1);
  the mode-switch prerequisite/config-hold flags the Modes doc §8 names.
- **Acceptance rows added (beyond §6):** external-fulfillment detection +
  review cases; state-model raw storage + unknown-value contract;
  Delivered-inconsistency case; COD scenarios 4–13 state derivation;
  reconnect catch-up review-landing; Layer 2 compliance (source-level: no
  mutation path outside Layer 2). See
  [`wave-4-definition-of-ready.md`](wave-4-definition-of-ready.md) §4 for
  the consolidated wave-level list.
- **Test families added (beyond §5):** `test_fulfillment_inbound_evidence`
  (record layers, uniqueness, ledger), `test_fulfillment_origin_classification`
  (evidence stack incl. own-GID precedence and unknown→external default),
  `test_fulfillment_state_model` (the State model §10 fixture inventory:
  56 fixtures incl. `dep_*` and `unknown_*`), `test_fulfillment_review_cases`
  (tracking import / acknowledge / explicit validation; Delivered
  inconsistency), `test_fulfillment_cod_interplay` (scenarios 4–13),
  `test_fulfillment_mode_switch` (state machine, idempotency, rollback),
  `test_fulfillment_reconnect_catchup`. Exact file names fixed at
  re-acceptance.

### 9.7 What this addendum does NOT change

Module boundary (no inventory dependency — location display via core's
cache, [`../03-architecture/modular-architecture-recommendation.md`](../03-architecture/modular-architecture-recommendation.md)
§2.3); the D-014-2 scope set + TD-002 fix; RA-009/014/022/023 constraints;
the §8 prompt's hard constraints (which must be re-issued, extended with
§9.1–§9.6, not weakened).

---

## 10. Addendum (2026-07-21) — [Proposed] Wave 4 Gate A reconciliation contract

> **Status: Proposed — Wave 4 Gate A, 2026-07-21. NOT accepted.** Appended per the
> Gate A session; nothing above this line is rewritten. **Every D-014 closure and
> the §9 addendum remain intact and binding.** This addendum records the exact
> base, the modular architecture contract, the Layer 2 integration contract, and
> the Mode 1 / Mode 2 contracts, reconciled against current official Shopify
> (Admin API 2026-07, accessed 2026-07-21), Odoo 19.0 FINAL source, and the merged
> code at the required base. Full basis + dispositions:
> [`../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md`](../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md).
> The §8 "locked final implementation prompt" above **targets the wrong base
> (`Shopify-connector`) and is SUPERSEDED**; the re-issued candidate is
> [`../06-prompts/sol-wave-4-fulfillment-locked-prompt.md`](../06-prompts/sol-wave-4-fulfillment-locked-prompt.md)
> (`LOCKED CANDIDATE — NOT ISSUED`). **Re-acceptance required** as one unit (DoR
> G4-5) before Wave 4 opens.

### 10.1 Exact base (corrects §8)
Required base: **`mvp/program-integration@ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`**
(the PR #182 / Task 013 merge commit), **not** `Shopify-connector`. The merged
Stage 0 Layer 2 substrate (DEC-036/DEC-031, Accepted 2026-07-19) is present and the
fulfillment mutations run under it (program hard-stop 4).

### 10.2 Modular architecture contract — `shopify_connector_fulfillment`
A **modular addon family member**, not a giant module; split by responsibility.
Depends on `['shopify_connector_core', 'shopify_connector_sale', 'stock_delivery',
'sale_stock']` (verified module names — Odoo notes §4; `stock_delivery` supplies the
picking carrier fields, `sale_stock` supplies `sale_id`/`sale_line_id`). **No
dependency on `shopify_connector_inventory`; never reads `location.mapping`** (audit
§4). Proposed structure (exact file list frozen in the locked prompt / Phase 6):

- **Models / bindings:**
  - `shopify.connector.fulfillment.binding` (inherits core `binding.mixin`;
    `shopify_gid` = **Fulfillment GID**; `picking_id` M2O(`stock.picking`, restrict,
    index); `order_binding_id` M2O(store-consistency); the D-014-1 fields;
    `UNIQUE(store_id, shopify_gid)` + `UNIQUE(store_id, picking_id)`). **Transport
    idempotency/request-hash never on the binding** — they live on
    `mutation.attempt` (audit §4).
  - **Inbound evidence records** (per-fulfillment: unique `store+Fulfillment GID`;
    per-line: reconciled-quantity ledger) — modes §5 / §9.2.
  - Store-settings extension: `fulfillment_operating_mode` (Selection `mode1`/`mode2`,
    default `mode1`, Admin-only via Python `groups=`), `fulfillment_notification_confirmed`,
    `fulfillment_last_reconciliation_at`, and the mode-switch state fields.
- **Fields / state taxonomy:** store all 7 Layer-A Shopify enum families **raw +
  normalized** with the unknown-future-value contract (status model §7) and the
  Delivered-inconsistency case (§8); Layer-C connector-derived states.
- **Services / handlers / job types:** register via **add-only** `_inherit` seams
  (zero core edits except the one named readiness edit): `job_type` `selection_add`
  the frozen **ten** types (§11.2) — the two mutations `fulfillment_create` +
  `fulfillment_tracking_update`, **one shared** `fulfillment_mutation_reconcile`, and
  the local admission/scan/observation/Mode-2 types; mutation-domain strategies
  (§10.3); handlers/replay policies; `_domain_flag_for_job_type` →
  `fulfillment_domain_enabled`; readiness `_get_checks` write-scope check (§10.4).
- **Cron / manual backend:** `fulfillment_reconciliation_check` cron (60 min,
  `job_source='reconciliation'`, per-run uuid nonce); manual retry surface — under
  Layer 2 (Odoo cron pattern, Odoo notes §8).
- **Permissions / ACL / record rules / protected fields:** mirror the inventory
  group matrix (Auditor r / Operator r+c / Reviewer r+w / Admin r+w+c; no unlink);
  sanctioned-service creation; binding attempt evidence read-only to users.
- **Error vocabulary / log events / manual-review actions:** DEC-009's 16 fixed
  classes (no 17th); emit `fulfillment_notification_confirmation_missing`;
  review-release = public action on the binding → private service helper.
- **Lifecycle / uninstall:** `original_job_type` retyping; full bridge-stack
  install/upgrade/uninstall/reinstall; zero residue.
- **Extension seams for later Wave 5 UI:** fields owned here; screens are Wave 5.

### 10.3 Layer 2 integration contract (the fulfillment mutation domain)
Reuse the merged Stage 0 Layer 2 substrate **verbatim**; supply the 7-callback
strategy (inventory `service.py` is the exact template — audit §4). Freeze:
- **Domain-registry values / job types** — the two mutation types
  `fulfillment_create` + `fulfillment_tracking_update` and **one shared**
  `fulfillment_mutation_reconcile` (dispatched strictly by the linked attempt's
  mutation domain; owns no attempt, no remote-effect scope), registered add-only (§11.2).
- **One job → at most one attempt for the job lifetime** (one-attempt-per-job
  `UniqueIndex`); a retry after a **pre-C2 failure or a synchronous `userErrors` clean
  rejection** = a **freshly enqueued replacement job** (new `payload_hash`) — no attempt
  reuse, **never from a post-C2 read result** (audit §1, DEC-038 #25).
- **C1 intent persistence; C2 durable attempt on the dedicated side cursor; NET
  transport; C3 outcome persistence** — inherited unchanged.
- **Fresh pre-C2 read** = the **primary duplicate-prevention control** for these
  non-idempotent mutations (verify-before-**send**, adopt-if-already-present). **Once
  C2 commits `transport_attempted=true` the job is reconcile-only — no second
  mutation** (§11.1). The reconcile read (order's `fulfillmentOrders`/`fulfillments`,
  **cursor-paginated to completion** — §11.4) returns only **APPLIED** or
  **INCONCLUSIVE** post-C2; **APPLIED** only on positive authoritative evidence;
  **read absence = INCONCLUSIVE**; **post-C2 `NOT_APPLIED` is not an actionable Wave 4
  verdict and never authorizes a replacement** (no accepted request-specific
  non-application proof exists); `INCONCLUSIVE_RECONCILIATION_CAP=3` →
  `duplicate_risk` block. A replacement send is reachable **only** from a proven
  `transport_attempted=false` (nothing sent) or a synchronous `userErrors` clean
  rejection — never from a post-C2 read result.
- **NO `@idempotent` directive** in the fulfillment operation string (fulfillment
  mutations are not on Shopify's still-17 `@idempotent` list — Shopify notes §4.1);
  `shopify_idempotency_key` stays null for fulfillment. Dedup = `business_intent_
  fingerprint` + `operation_scope_key` serialization + the reconcile read.
- **`exact_request_fingerprint`** must be byte-identical between C2 and the wire —
  deterministic payload building (audit §6).
- **Operation-scope serialization (Q1 RULED)** — `fulfillment_create` per
  `(store, picking, FulfillmentOrder GID)`; `fulfillment_tracking_update` per
  `(store, binding/picking, Fulfillment GID)`; the shared
  `fulfillment_mutation_reconcile` owns **no** remote-effect scope (reconciles via its
  `mutation.attempt` link). Overrides `_compute_operation_scope_key` for the two
  mutation types only.
- **`classify_direct_result`** uses the **`code_required=False` + positive-success-
  evidence** branch (fulfillment `userErrors` carry no `code`; require a real
  Fulfillment id before treating empty `userErrors` as applied — audit §4).
- **Store identity + connection generation** — reused verbatim; **reconciliation-
  before-retry; replacement-job behavior; manual-review routing/release; bounded
  retry; no raw transport; no false success; no unsupported exactly-once claim**
  (at-most-once + reconciliation convergence only).
- **Do not invent a parallel fulfillment mutation framework.**

### 10.4 Readiness / scope contract
The **one named core edit**: `shopify_connector_core/models/shopify_connector_readiness_check.py`
`REQUIRED_MVP_SCOPES` swap `read_fulfillments` → `read_merchant_managed_fulfillment_orders`
(+ its test). A conditional **`write_merchant_managed_fulfillment_orders`** check is
appended via the `_get_checks` seam (active when `fulfillment_domain_enabled`). **Add
the staff-permission axis** `fulfill_and_ship_orders` (distinct from the API scope —
Shopify notes §2) to the readiness/UAT contract.

### 10.5 Mode 1 contract (Odoo-controlled; default)
- **Purpose:** Odoo delivery validation drives Shopify fulfillment; external
  fulfillments observed → review, never auto stock mutation.
- **Admission event:** `stock.picking._action_done` (once-per-validation; not
  re-entrant `button_validate` — Odoo notes §2), eligible per D-014-3
  (`picking_type_code=='outgoing'` AND `location_dest usage=='customer'` AND
  `state=='done'` AND bound order + `fulfillment_domain_enabled`). Adopt the
  `sale_stock`-auto-created pickings (Q2), do not duplicate.
- **Eligibility:** FO `status ∈ {OPEN, IN_PROGRESS}` **AND
  `supportedActions` contains `CREATE_FULFILLMENT`** (DEC-038 #41).
- **Fulfillable quantity:** per-line done `stock.move.line.quantity`, ≤ FO line
  `remainingQuantity` (fresh pre-C2 read).
- **Location resolution:** FO `assignedLocation` (`.location` nullable → snapshot
  fallback) + core location cache; never `location_mapping`.
- **Matching:** move → `sale_line_id` → `shopify_line_item_gid` → FO line
  (`lineItem.id`) → FO-line-item `id`; explicit `lineItemsByFulfillmentOrder` always;
  skip null-GID lines; unmatched → `mapping_missing` review (RA-023).
- **Mutation sequence:** `fulfillmentCreate` (notifyCustomer persisted at enqueue,
  default off); later tracking → `fulfillmentTrackingInfoUpdate` in place.
- **Success / clean-rejection / uncertain / reconcile / retry / duplicate-prevention:**
  the §10.3 Layer 2 contract.
- **Inbound:** observe every fulfillment; origin-classify (own-GID ledger primary);
  external → review case (import tracking / acknowledge / explicit validate).
- **COD / scheduled / manual / disconnect / reconnect / logs:** per §9 + DEC-038.

### 10.6 Mode 2 contract (bidirectional exact reconciliation; opt-in, Wave 4 backend)
- Everything Mode 1 does **plus** auto-validate the Odoo delivery from an external
  Shopify fulfillment **only when all 16 conditions pass** (the reconciled engine —
  DEC-038 §3: 12 preserve, 4 refine); **first failure → named review reason**; any
  ambiguity → review, **no partial automation, no auto stock mutation on
  ambiguity**.
- **Deterministic picking selection** (modes §4.1): drive `cancel_backorder`
  explicitly (never the `ask` wizard — Odoo notes §3); any allocation choice →
  `picking_ambiguous`.
- **Mode switch** (Admin-only, audited, never-replays, scan-gated, idempotent,
  rollback-safe — modes §6): in-flight Layer 2 jobs complete under Layer 2 and are
  not cancelled by the switch (DEC-038 #19).
- **Disconnected-period external fulfillments → review in BOTH modes** (the stricter
  modes §7 rule; DEC-038 #20).

### 10.7 New / corrected test families (delta to §5 / §9.6)
Add: `supportedActions`/status eligibility; `assignedLocation.location`-null
fallback; `>1 FO per location`; the FO-line-item-GID 2-hop matching; the
no-`@idempotent` **source-guard** (the fulfillment operation string must not contain
`@idempotent`); the `code_required=False` positive-success-evidence classifier;
`action_confirm()` auto-picking coexistence; the `send_to_shipper` `rate_and_ship`
collision; staff-permission (`fulfill_and_ship_orders`) tests distinct from API-scope
tests; and a `qty_done`/`quantity_done` static source-guard (the field does not exist
in Odoo 19). Exact file names frozen in the locked prompt (Phase 6).

---

## 11. Addendum (2026-07-22) — [Proposed] Bounded control-room correction

> **Status: Proposed — bounded control-room correction, 2026-07-22. NOT accepted.**
> Applied per PR #188 comment `5041620950` / issue #186 comment `5041623758`. Nothing
> above is deleted; where earlier wording conflicts (the "absent → resend" path,
> `first: N` fixed windows, `over_fulfillment`, a single giant service file, a
> fulfillment-only `2026-07` pin, **the "gate closes on draft-open" wording, and the
> "recorded waiver" shortcut for dev-store evidence** — §3 #11 / §5 / §6 / §8),
> **this section supersedes it** (corrected in place or via §11.8). Decision basis:
> [`../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md`](../04-decisions/DEC-038-wave-4-fulfillment-gate-a-reconciliation.md)
> §4 (Q1–Q8 rulings) + §7.
>
> **Final control-room micro-correction (2026-07-22)** — per PR #188 comment `5042183642`
> / issue #186 comment `5042185019`, §11.1/§11.2/§11.5 are further tightened:
> **post-C2 `NOT_APPLIED` never authorizes a resend** (post-C2 reconciliation is
> **APPLIED / INCONCLUSIVE** only); the taxonomy is frozen at **exactly ten job types**
> with **one shared `fulfillment_mutation_reconcile`** that inherits **no** remote-effect
> operation scope (the two per-domain `*_reconcile` types are removed);
> **`fulfillment_review_release` is not a job type** (sanctioned-helper release);
> **`webhook` is removed as a Wave 4 source** (webhooks forbidden this wave); and the
> `fulfillment_tracking_change` trigger-origin uses the **dedicated**
> `_normalize_tracking_change_trigger_origin_on_uninstall` callable (not the job-type
> sink). The frozen names carry no "validated/consolidated at Gate B" caveat.

### 11.1 P0 — uncertain remote outcome is reconcile-only (no post-C2 resend)
Binding contract (DEC-038 §7.1): (A) before C2 / proven `transport_attempted=false` →
normal bounded replacement job; (B) a **synchronous** structured `userErrors` clean
rejection (no success object) is a **direct clean failure** — **not** a post-C2 uncertain
verdict — and may be corrected via a new replacement job; (C) once C2 commits
`transport_attempted=true`, an unknown outcome (timeout/network/crash/malformed) is
**reconcile-only — the mutation is never sent again** (via the shared
`fulfillment_mutation_reconcile` job); (D) post-C2 reconciliation has only **two
actionable outcomes** — **APPLIED** (positive authoritative evidence of the exact
effect) / **INCONCLUSIVE** (**everything else**: read absence, unchanged FO quantities,
old/unchanged tracking, a fully paginated read with no match, missing tracking,
concurrent external activity). Under the currently researched Shopify contract **no
request-specific proof of non-application exists**, so **post-C2 `NOT_APPLIED` is not an
actionable Wave 4 verdict and never authorizes a replacement mutation** (a future path
needs new official evidence + a control-room amendment + tests); (E) **no automatic
second `fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`** from any post-C2 read
result — after `INCONCLUSIVE_RECONCILIATION_CAP=3` → `duplicate_risk` review; the **same
rule binds notification side effects** (a possible prior `notifyCustomer=true` is never
repeated from absence). Source-guard/behavior tests: C2-committed unknown cannot reach a
second mutation; read absence→INCONCLUSIVE; **no post-C2 read result authorizes a
replacement** (only `transport_attempted=false` or a synchronous `userErrors` clean
rejection may); the shared reconcile job **cannot enqueue another mutation**; no-tracking
uncertainty fails closed; possible-notification uncertainty fails closed.

### 11.2 Complete Wave 4 job / replay taxonomy (frozen)

Every backend job — **exactly ten frozen job types**. Mutation jobs own **at most one**
`mutation.attempt` for their lifetime (DEC-036); a retry is a **freshly enqueued
replacement job** (new `payload_hash`) reachable **only** from a pre-C2/no-transport
failure or a synchronous `userErrors` clean rejection — never attempt reuse, never from a
post-C2 read result. Reconcile/read/local jobs own **no** attempt. Replay policies are the
merged core values (`local_only` / `remote_read_replay_safe` /
`remote_effect_not_replay_safe`). There is **one shared** reconcile type,
`fulfillment_mutation_reconcile`, linked to exactly one `mutation_attempt_id` and
**dispatched strictly from that attempt's `mutation_domain`**; it owns no attempt and
**neither owns nor inherits** a remote-effect operation-scope literal. **Webhooks are
forbidden in Wave 4** — no job admits from `webhook`. **`fulfillment_review_release` is
not a job type.** **No 17th error class; no unregistered subreason.**

| # | `job_type` | Class | `job_source` | `trigger_origin` | Domain flag | `res_model` / identity | Operation-scope literal | Replay policy | Owns attempt | Lineage (pred → succ) | Terminal / review disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `fulfillment_picking_admission` | local orchestration | `odoo_event` | `fulfillment_picking_validation` | `fulfillment_domain_enabled` | `stock.picking` | `(store, picking)` | `local_only` | no | `_action_done` → N× `fulfillment_create` (per FO) | succeeded (children enqueued) / `mapping_missing` / `ambiguous_match` review |
| 2 | `fulfillment_create` | Shopify mutation | `odoo_event` (or `manual_sync` on replacement) | `fulfillment_picking_validation` | `fulfillment_domain_enabled` | `stock.picking` + `shopify_target_gid`=FO GID | `(store, picking, FulfillmentOrder GID)` **(Q1)** | `remote_effect_not_replay_safe` | **yes** | admission → `fulfillment_mutation_reconcile` (post-C2 uncertain) / replacement `fulfillment_create` (**pre-C2 / synchronous clean rejection only**) | succeeded (binding written) / `duplicate_risk` / mapped error class |
| 3 | `fulfillment_tracking_admission` | local orchestration | `odoo_event` | `fulfillment_tracking_change` **(Q4)** | `fulfillment_domain_enabled` | `stock.picking` / fulfillment binding | `(store, binding)` | `local_only` | no | tracking-change hook → `fulfillment_tracking_update` | succeeded / `binding_conflict` review |
| 4 | `fulfillment_tracking_update` | Shopify mutation | `odoo_event` (or `manual_sync` on replacement) | `fulfillment_tracking_change` | `fulfillment_domain_enabled` | fulfillment binding + `shopify_target_gid`=Fulfillment GID | `(store, binding, Fulfillment GID)` **(Q1)** | `remote_effect_not_replay_safe` | **yes** | admission → `fulfillment_mutation_reconcile` (post-C2 uncertain) / replacement `fulfillment_tracking_update` (**pre-C2 / synchronous clean rejection only**) | succeeded / `duplicate_risk` / mapped error class |
| 5 | `fulfillment_mutation_reconcile` | reconciliation (read; **shared, both domains**) | `reconciliation` | — | `fulfillment_domain_enabled` | linked `mutation_attempt_id`; dispatch by `mutation_domain` ∈ {`fulfillment_create`, `fulfillment_tracking_update`}; attempt link = reconciliation identity | **none — owns/inherits no remote-effect operation scope** | `remote_read_replay_safe` | no | `fulfillment_create` / `fulfillment_tracking_update` (post-C2 uncertain) → APPLIED-adopt or INCONCLUSIVE; **no replacement mutation** | APPLIED→adopt / INCONCLUSIVE cap→`duplicate_risk`; **never a second mutation** |
| 6 | `fulfillment_inbound_observation` | read + local classify | `scheduled_sync` / `reconciliation` | — | `fulfillment_domain_enabled` | inbound-evidence / order binding + Fulfillment GID | `(store, Fulfillment GID)` (read) | `remote_read_replay_safe` | no | → `fulfillment_mode2_evaluation` (Mode 2) | evidence recorded; external → Mode 1 review case |
| 7 | `fulfillment_reconciliation_check` | read (scan) | `reconciliation` | — | `fulfillment_domain_enabled` | store (watermark) + per-run uuid nonce | per-run nonce | `remote_read_replay_safe` | no | cron | snapshot/drift notes / review |
| 8 | `fulfillment_reconnect_catchup` | read (scan) | `reconciliation` | — | `fulfillment_domain_enabled` | store + per-run nonce | per-run nonce | `remote_read_replay_safe` | no | reconnect | every disconnected-period external fulfillment → review (**both modes**) |
| 9 | `fulfillment_mode_switch_scan` | read + local (admin) | `manual_sync` / `scheduled_sync` | — | `fulfillment_domain_enabled` | store + per-run nonce | per-run nonce | `remote_read_replay_safe` | no | admin switch request → enables Mode 2 | scan-clean → switch; blockers → abort to Mode 1 |
| 10 | `fulfillment_mode2_evaluation` | local (Odoo write) | `odoo_event` / `reconciliation` | — | `fulfillment_domain_enabled` | inbound-evidence / `stock.picking` | `(store, Fulfillment GID)` | `local_only` | no | observation → (16/16) validate picking | 16/16 pass → validate (local); any fail → **named review reason** (§7.2 map); **fails closed before validation if carrier flow would book/charge — Q6** |

**These exact ten `job_type` spellings are frozen; no Gate B rename or consolidation
without a control-room allowlist/decision amendment.** Gate B only runs the build-time
`_get_handlers`/`_get_replay_policies` completeness invariant against these exact names;
it never re-opens the freeze. **Review release is not a job type**: a public action on the fulfillment
binding calls a **private sanctioned service helper** that releases the exact blocked job
or admits a permitted **pre-C2 / synchronous-clean-rejection** replacement under lineage.

**Reconciliation handoff ordering (no operation-scope collision).** Before the shared
`fulfillment_mutation_reconcile` job is inserted: (1) **lock** the uncertain mutation
job; (2) **transition/supersede** it through the sanctioned path; (3) **flush** it so its
remote-effect operation scope is released; (4) **create** the reconciliation job linked to
the committed `mutation.attempt`; (5) **commit** per the accepted Layer 2 handoff pattern.
No reconciliation child is inserted while its predecessor still holds a conflicting
operation scope. The shared reconcile job may run while a disconnect is quiescing under
the accepted Layer 2 rules, and may conclude only: applied/adopted; inconclusive +
rescheduled within the cap; `duplicate_risk` manual review after the cap; or a mapped
final/auth/configuration failure where supported — **never a replacement mutation from a
post-C2 read result**. Required tests (folded into the frozen files, §11.3):
predecessor terminalize/supersede-then-flush before the reconciliation insert; no
operation-scope collision; one shared reconcile type for both mutation domains;
attempt-domain dispatch; duplicate-reconciliation admission prevention; concurrent
handoff; rollback injection; post-C2 reconciliation cannot enqueue another mutation.

### 11.3 Modular file / exact-test allowlist → frozen in the locked prompt
The giant `shopify_connector_fulfillment_service.py` is **replaced by an enumerated
modular production file map**, and **every exact test filename is frozen**, in
[`../06-prompts/sol-wave-4-fulfillment-locked-prompt.md`](../06-prompts/sol-wave-4-fulfillment-locked-prompt.md)
§2/§5 (the implementation-worker authority). The §5, §9.6 and §10.7 **test families**
above are the behavior families those exact filenames must cover; the frozen filename
list is exhaustive (no additional production or test file without a control-room
allowlist amendment). The `[service + seams + hooks]` single-file wording in §8's old
prompt is **superseded** by that modular map.

### 11.4 Cursor-pagination contract (frozen)
Every decision-critical read paginates with **`pageInfo.hasNextPage` + `endCursor`** to
completion, with: deterministic page ordering where available; an explicit
**fail-closed** maximum-page/node safety cap; duplicate-node detection; repeated-cursor
detection; malformed-page handling. Applies to **all** FulfillmentOrders for an order;
**all** required line items for **every** candidate FO; fulfillment
reconciliation/adoption reads; inbound periodic scans; reconnect catch-up; Mode 2
evidence reads. A partial page set may **never** prove absence, select a unique target,
prove mapping completeness, authorize a mutation, or authorize a resend; when the safety
cap is reached before completeness, route to a data-shape/manual-review disposition
(`data_shape_schema_mismatch` / `ambiguous_match`) — never continue on a partial set.
This replaces `fulfillmentOrders(first: 10)`, `fulfillments(first: 50)`, and any
"first page of FO line items" assumption.

### 11.5 Lifecycle `ondelete` (frozen)
**Job types.** Every new fulfillment `job_type` (§11.2) is added via `selection_add` with
an **explicit LC-1-compatible `ondelete`** using the job-type sink
`_reassign_to_historic_job_type` (→ `historic_domain_job`), preserving `original_job_type`
(cancels/retypes the job; the historic row is never re-interpreted as active work).

**Trigger origin.** The new `trigger_origin` value `fulfillment_tracking_change` (Q4) uses
a **dedicated, fulfillment-owned** `ondelete` callable —
`_normalize_tracking_change_trigger_origin_on_uninstall`, defined in
`addons/shopify_connector_fulfillment/models/shopify_connector_job.py` — **not**
`_reassign_to_historic_job_type` (which cleans `job_type` only and cannot remove a
trigger-origin value, so it can neither clear the removed value nor prove zero residue).
On uninstall, for every record carrying `trigger_origin='fulfillment_tracking_change'`
the callable: (1) appends **one** sanitized audited manual-action log recording that the
original trigger origin was `fulfillment_tracking_change` and is being normalized because
the domain capability is uninstalling (provenance preserved in the immutable job log);
(2) replaces the removed value with the permanent **core** value
`fulfillment_picking_validation`; (3) **does not clear `trigger_origin` while
`job_source='odoo_event'`** (that would violate the merged core `job_source`/
`trigger_origin` constraint); (4) **does not change `job_source`**; (5) leaves **no**
record carrying `fulfillment_tracking_change` after uninstall; (6) reinstall does not
re-interpret the historic row as active fulfillment work. The two `ondelete` callbacks are
order-independent (trigger-origin before job-type, or job-type before trigger-origin).

**Tests:** queued tracking-admission job; running/retry/review tracking job (where the
lifecycle permits the uninstall fixture); terminal tracking job; trigger-origin callback
before job-type callback and vice-versa; core `job_source`/`trigger_origin` constraint
still valid; **exactly one** provenance-normalization audit per affected job; no removed
trigger-origin value remains; no active fulfillment job remains; reinstall produces **zero
active-domain residue** and **no orphan** `mutation.attempt`/evidence record. (Extends §7's
LC-1 note to the full job set; folds into `test_fulfillment_lifecycle.py`.)

### 11.6 Staff-permission readiness (Q8)
`fulfill_and_ship_orders` (staff permission) is a **separate axis** from API scopes; no
official introspection mechanism is demonstrated. Readiness carries it as **manually
confirmed / NOT_PROVEN**, never inferred from `currentAppInstallation.accessScopes`; a
real Shopify auth failure is preserved as sanitized runtime evidence
(`shopify_permission_scope_auth`); live-mutation qualification is blocked until it is
operator-confirmed and dev-store-validated (CV-013 / #185).

### 11.7 API-version policy (Q7)
Calls go through the core API client and **`store.api_version`**; **no fulfillment-only
version override**, **never `latest`**. `2026-07` is the present verified contract;
readiness records whether the store's configured version is in the **accepted
compatibility set** and fails/blocks otherwise; the GraphQL-shape/source-guard suite
runs against every version in that set; expansion requires current official research +
control-room acceptance.

### 11.8 Corrected gate / acceptance posture (supersedes §3 #11 / §6 / §8 wording)
The **gate does not close merely on draft-open**. Gate A and Gate B each require explicit
**control-room acceptance** (ChatGPT), never self-acceptance; the PR stays draft/unmerged
until then. Dev-store fulfillment mutation evidence is **required** for both Mode 1 and
Mode 2; any exception is a **specific product-owner ruling recorded on GitHub**, **not a
routine control-room/"recorded waiver"**. **Wave 4 cannot receive final acceptance, enter
a release candidate, or begin UAT while CV-013 (#185) is open** — both the fulfillment
dev-store campaign **and** CV-013 must execute green (DoR criterion 11; UAT §E). This
replaces the earlier "gate closes on draft-open" / "dev-store evidence or recorded
(ChatGPT) waiver" phrasing in §3 #11, §5, §6, and the superseded §8 prompt.
