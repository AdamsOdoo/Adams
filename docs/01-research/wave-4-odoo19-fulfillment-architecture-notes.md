# Wave 4 — Official Odoo 19 Delivery & Tracking Architecture Notes (Gate A)

> **Status: CANDIDATE — Gate A Phase 2 output, pending control-room acceptance.**
> Verified against the authoritative **Odoo 19.0 FINAL** source
> (`github.com/odoo/odoo@19.0`, HEAD `b4f01111807a12977991d28acb3bf482bc05d248`;
> `odoo/release.py` `version_info = (19, 0, 0, FINAL, 0, '')`), read 2026-07-21.
> Every behavior below is **verified-in-Odoo-19-source** with `file : symbol :
> lines`. Odoo 17/18 behavior is never used as proof. This file authorizes no
> implementation.

**Evidence class key:** all findings here are `verified-in-odoo19-source` unless
marked `[inferred]`. Line numbers are valid for the pinned HEAD above.

---

## 1. Quantity semantics — DECISION-CRITICAL (rejects `qty_done`)

- **Done/executed quantity on a move line = `stock.move.line.quantity`.**
  `addons/stock/models/stock_move_line.py : StockMoveLine.quantity : L37-39`
  (`fields.Float('Quantity', digits='Product Unit', compute='_compute_quantity',
  store=True, readonly=False)`).
- **The obsolete `qty_done` / `quantity_done` field does NOT exist in Odoo 19.**
  A field-definition search (`qty_done = fields.` / `quantity_done = fields.`)
  across the whole `addons/` tree returns **zero** matches. In
  `stock_move_line.py` the token `qty_done` is only a local variable
  (`qty_done_float_compared`, L621-622) and `quantity_done` only a comment
  (L546). Method/UI names retain legacy terminology (`_set_quantity_done`
  `stock_move.py:2551`, `is_quantity_done_editable` `stock_move.py:182`) but
  **operate on the `quantity` field** — none is a data field. Stale
  `field_stock_move_line__qty_done` entries survive only in i18n `.po` catalogs.
- **Move-level done quantity = `stock.move.quantity`**
  (`stock_move.py : StockMove.quantity : L171-172`), a stored **computed sum** of
  its move lines' `quantity` (`_compute_quantity` `L409-438`,
  `@api.depends('move_line_ids.quantity',…)`), writable via inverse
  `_set_quantity`. **Source of truth = per-line `stock.move.line.quantity`.**
- **Demand (ordered, planned) = `stock.move.product_uom_qty`**
  (`stock_move.py : L58-64`, `'Demand'`).

**Reconciliation:** validates **Task 014 D-014-4** ("quantity = the move's done
`quantity` (19.0 field)") and **modes condition 7** (`stock.move.product_uom_qty`
demand vs done `quantity`). Gate A **hard-rejects** any `qty_done`/`quantity_done`
mapping (would raise). A static source-guard for `qty_done`/`quantity_done` in the
fulfillment addon is warranted (Phase 6). → DEC-038.

---

## 2. Picking validation lifecycle & the correct hook point (D-014-3)

- **`button_validate()` is re-entrant and NOT a reliable completion signal.**
  `stock_picking.py : StockPicking.button_validate : L1399-1459` — it may **return
  the backorder-confirmation wizard action** (`ir.actions.act_window`) instead of
  completing. Do **not** hook the Shopify push here.
- **`_action_done()` is the canonical completion method** — invoked **exactly once
  per completed validation** (both backorder and no-backorder branches):
  `stock_picking.py : StockPicking._action_done : L1256-1281`. It marks moves done,
  stamps `date_done`, and returns `True`. **This is the correct override/attach
  point** (`super()` first, then act on pickings guaranteed done) — exactly what
  **D-014-3** specifies. ✅
- **Picking `state`** = `draft / waiting / confirmed(label "Waiting") /
  assigned(label "Ready") / done / cancel` (`stock_picking.py : state : L575-589`),
  **computed from moves** (`_compute_state` `L816-862`), never written directly. A
  picking reaches `done` only when every move is `done`/`cancel`. Filter on the
  **technical** values (`assigned`/`done`), not labels.
- **Direction:** `picking_type_code` (related `picking_type_id.code`) =
  `outgoing`/`incoming`/`internal` (`stock_picking.py : L625-627`); customer-bound
  detection also via move/picking `location_dest_id.usage == 'customer'`. **D-014-3
  eligibility** (`picking_type_code=='outgoing'` AND `location_dest usage=='customer'`
  AND `state=='done'`) is **confirmed correct** against 19.0. ✅

---

## 3. Backorders & partial delivery (decision-critical for Mode 2 §4.1 + COD)

- **`create_backorder` policy lives on `stock.picking.type`**, not `stock.picking`:
  `stock_picking.py : StockPickingType.create_backorder : L133-139`, Selection
  `ask`/`always`/`never`, default `ask`. (`ask` → interactive wizard; `always` →
  auto backorder; `never` → remaining cancelled.)
- **Deterministic, non-interactive validation** (no wizard) is achieved via the
  wizard's own mechanism: context `skip_backorder=True` plus
  `picking_ids_not_to_backorder=[ids]`
  (`stock/wizard/stock_backorder_confirmation.py : process /
  process_cancel_backorder : L49-75`). The single boolean **`cancel_backorder`**
  decides at `_action_done` time: **False → backorder created**, **True →
  remaining cancelled**.
  - **Implication:** Mode 2 auto-application (modes §4.1 "force `create_backorder`
    explicitly, never the `ask` wizard") and COD remainder cancellation (COD doc)
    map directly onto `cancel_backorder`. The connector must drive these context
    keys rather than invoking `button_validate` and hoping no wizard appears.
- **Backorder creation happens inside `stock.move._action_done`**, which calls
  `picking._create_backorder()` (`stock_move.py : _action_done : L2241-2309`, call
  at ~L2302; `stock_picking.py : _create_backorder / _create_backorder_picking :
  L1568-1603`). The backorder picking carries **`backorder_id` → origin picking**
  and inherits `return_id`; remaining moves/lines are re-parented (`picked=False`);
  the origin keeps only done moves and flips to `done`.
  - **Implication:** each backorder picking is **its own independent fulfillment
    event** (validates **D-014-3** "each backorder picking meeting the rule is its
    own event"), and the connector **must follow `backorder_id`** when correlating
    Odoo transfers to Shopify FulfillmentOrders, to avoid treating a backorder as a
    new unrelated shipment. Maps to Shopify `remainingQuantity` decrementing across
    sequential fulfillments.

---

## 4. SO ↔ picking ↔ move linkage and the dependency set (D-014-1 / DEC-018)

- **`stock.move.sale_line_id` is defined in `sale_stock`, NOT base `stock`:**
  `addons/sale_stock/models/stock.py : StockMove(_inherit).sale_line_id : L15-17`
  (`Many2one('sale.order.line', index='btree_not_null')`).
- **`stock.picking.sale_id` is in `sale_stock`** (`sale_stock/models/stock.py :
  StockPicking.sale_id / _compute_sale_id : L183-194`) — a **stored computed**
  field derived from `move_ids.sale_line_id.order_id`, resolving to a **single SO
  (the first)**. A picking spanning multiple SOs exposes only the first via
  `sale_id` (edge case for matching).
- **`sale.order.line.move_ids`** = One2many to `stock.move` via `sale_line_id`
  (`sale_stock/models/sale_order_line.py : L12-17`). Canonical fulfillment
  traversal: **SO line → `move_ids` → picking**, and back via
  `move.sale_line_id.order_id`.
- `sale_stock` auto-links/creates SO lines from warehouse moves (`_action_synch_order`,
  `sale_stock/models/stock.py : L36-89, 236-281`) — **SO lines can appear
  post-delivery**; reconciliation must not assume the SO-line set is fixed at
  order confirmation.

**Module-name verification (corrects a common trap):**
- **`delivery`** (`addons/delivery/__manifest__.py`, `depends=['sale','payment_custom']`)
  adds carriers to **sale orders**.
- **`stock_delivery`** (`addons/stock_delivery/__manifest__.py`,
  `depends=['sale_stock','delivery']`) is the **bridge that adds the carrier
  fields to pickings**.
- **`sale_stock`** (`depends=['sale','stock_account']`) adds `sale_id` /
  `sale_line_id`.
- **Conclusion:** the Task 014 packet dependency
  `['shopify_connector_core','shopify_connector_sale','stock_delivery','sale_stock']`
  is **correct and precise**: `stock_delivery` supplies the picking carrier fields,
  `sale_stock` supplies the SO linkage. (`stock_delivery` already depends on
  `sale_stock`, so listing both is redundant-but-harmless; Odoo dedups the graph.)
  Both are `auto_install:True` and pull a large transitive graph (`sale`, `stock`,
  `stock_account`, `delivery`, `payment_custom`, `account`…) — CI/DB setup must
  install the full graph. ✅ validates D-014-1 / DEC-018 / modular-arch §2.3.

---

## 5. Carrier / tracking fields & the send_to_shipper collision RISK (D-014-6)

- **Carrier/tracking fields are on `stock.picking` via `stock_delivery`:**
  `stock_delivery/models/stock_picking.py` — `carrier_id`
  (`Many2one('delivery.carrier')`), **`carrier_tracking_ref` (`Char`, `copy=False`)**,
  `carrier_tracking_url` (**computed, non-stored**, `_compute_carrier_tracking_url`
  L40-43 → `carrier_id.get_tracking_link(picking)` only when both `carrier_id` and
  `carrier_tracking_ref` are set). (`L11-27`.)
  - `carrier_tracking_ref` `copy=False` → **not carried to backorder/return
    pickings**; each picking's tracking is independent (fits per-picking fulfillment
    binding, D-014-1). `carrier_tracking_url` may hold a JSON list for multi-package.
- **`send_to_shipper()`** (`stock_delivery/models/stock_picking.py : L125-158`)
  books a shipment via `carrier_id.send_shipping()` and **sets
  `carrier_tracking_ref` from the carrier API response** (comma-appending across
  chained pickings).
- **⚠ RISK (new, Gate A):** `send_to_shipper()` is **auto-invoked on delivery
  validation** when `carrier_id.integration_level == 'rate_and_ship'` (default),
  `picking_type_code != 'incoming'`, and no `carrier_tracking_ref` yet
  (`_send_confirmation_email` trigger, `stock_delivery/models/stock_picking.py :
  L94-123`; `integration_level` default `'rate_and_ship'`,
  `delivery/models/delivery_carrier.py:52`). For a **Shopify-driven fulfillment
  where tracking originates in Shopify/Odoo import**, a carrier configured
  `rate_and_ship` would try to **book its own shipment and overwrite
  `carrier_tracking_ref` at validation time**, colliding with the connector's
  tracking model. **Gate A recommendation:** the DoR / packet must require that
  fulfillment operates with a **`rate`-only (non-`rate_and_ship`) carrier** or
  writes `carrier_tracking_ref` directly, and the tests must cover this collision.
  → DEC-038 + risk register (SRR).

**Reconciliation with D-014-6:** the tracking mapping (`carrier_tracking_ref` →
`trackingInfo.number`, split on delimiters; `carrier_id.name` →
`trackingInfo.company`; `carrier_tracking_url` → `trackingInfo.url`) is sound; add
the `integration_level` collision guard above.

---

## 6. Returns boundary (Wave-4 forward-sync boundary only)

- **`stock.return.picking` is a `TransientModel` (wizard)** in
  `addons/stock/wizard/stock_picking_return.py` (`StockReturnPicking` L7-10;
  `_create_return` L86-101). It creates a **new reverse picking** (swapped
  source/dest locations) whose moves carry **`origin_returned_move_id` →
  original move** — returns are modelled as new pickings, never by mutating the
  original delivery.
- `_can_return` requires the source picking `state == 'done'` (base
  `stock_picking.py : L2113-2115`), relaxed by `sale_stock` to also allow any
  SO-linked picking (`sale_stock/models/stock.py:321-323`).
- **Reconciliation:** confirms the accepted boundary — Odoo return pickings are
  researched only to define the **safe forward-fulfillment boundary**;
  **Shopify-side returns / reverse-fulfillment sync are OUT of Wave 4 scope**
  (prompt §7; COD PD-COD-2 uses `stock.return.picking` as the only stock-restoration
  path, Administrator-gated). The `origin_returned_move_id` link is how returned
  quantity is reconciled.

---

## 7. Company / warehouse / location consistency (duplicate-prevention & scoping)

- **`stock.picking.company_id`** is a **stored related** field
  (`related='picking_type_id.company_id'`, `stock_picking.py : L634-636`) — not
  directly writable; company is chosen via `picking_type_id`.
- **Company consistency is enforced at confirm/validate, not create-time:**
  explicit `_check_company()` calls in `action_confirm` (`L1188`) and `_action_done`
  (`L1266`); layered picking → move (`stock_move.py` `_check_company` at `L1736`,
  `L2263`) → move-line (`stock_move_line.py:677`). A picking can be *created* in a
  company-inconsistent state and only raise at validation. **Implication:** the
  connector should validate company/location consistency **up front**, not rely on
  create-time enforcement (fits the packet's store-consistency checks).
- **`stock.warehouse.company_id`** is required, one company per warehouse
  (`_check_company_auto=True`; `unique(name, company_id)` / `unique(code,
  company_id)`, `stock_warehouse.py:27,37-40,92-97`). **`stock.location.company_id`
  may be empty** ("shared between companies", `stock_location.py:60-63`) — a
  company-less shared location is compatible with any company; the mapping must
  handle `company_id=False`.
- **Picking name is unique per company** (`_name_uniq = unique(name, company_id)`,
  `stock_picking.py:710-713`). → any external reference/idempotency key the
  connector derives must be **company-scoped**.

---

## 8. Transactions, locking, concurrency (informs the Phase 6 concurrency plan)

- **`_action_done` takes NO explicit picking/move row locks.** DB-level
  concurrency control lives in the **quant layer**:
  `stock.quant._update_available_quantity` locks the first available quant via
  `try_lock_for_update(allow_referencing=True, limit=1)` before writing
  quantity/reserved (`stock_quant.py : L1078-1090`, lock at L1082). Parallel
  connector-driven validations touching the **same product/location/lot quant**
  contend/serialize — chunk work and expect lock waits / serialization failures.
- The ORM `try_lock_for_update` (returns lockable subset) vs `lock_for_update`
  (raises `LockError`) primitives are exercised in
  `odoo/addons/base/tests/test_orm.py : L155-210`. (Their definitions live in
  `odoo/orm`, **not present in the partial clone** — usages/tests are citable, the
  core method bodies are `[inferred]` from tests.)
- **Cron pattern** (for the D-014-8 reconciliation-scan cron): the stock scheduler
  cron is `state='code'`, runs as superuser (`base.user_root`), `use_new_cursor`,
  **chunked mid-run `cr.commit()`** and `ir.cron._commit_progress` for
  restartability (`stock_rule.py : run_scheduler / _run_scheduler_tasks :
  L690-741`; cron record `stock/data/stock_sequence_data.xml:46-57`). Worker
  acquisition uses `FOR NO KEY UPDATE SKIP LOCKED` (`odoo/addons/base/models/
  ir_cron.py:353-366`) — one worker per job, partial jobs re-acquired, must be
  **idempotent / restart-safe**. The connector's reconciliation cron should follow
  this pattern. **Note:** the merged Stage 0 Layer 2 already provides the durable
  job/dispatch substrate (see code audit) — the fulfillment mutations run under it,
  not a bespoke cron loop.

---

## 9. Unresolved / carried (none is a Gate A blocker)

1. ORM core (`odoo/orm`, `odoo/models.py`) not in the partial clone — lock-primitive
   bodies inferred from `base/tests/test_orm.py`; re-verify against a full checkout
   before Gate C if a bespoke lock is ever needed (it should not be — reuse Layer 2).
2. Per-provider `send_shipping` / `get_tracking_link` behavior is delegated to
   `<delivery_type>_*` methods in separate carrier modules (e.g.
   `delivery_ups_rest`) — not needed for a Shopify-sourced-tracking connector, but
   the `integration_level` risk (§5) must be handled.
3. Full backorder move-splitting quantity math (`stock.move._create_backorder`,
   `stock_move.py:2314+`) read at the invocation level only — sufficient for Gate A;
   line-level re-read deferred to Gate B if the split algorithm is mirrored.

**Phase 2 (Odoo) completion criterion met:** every version-sensitive Odoo behavior
the fulfillment design relies on is **verified in Odoo 19 source** (done-quantity =
`stock.move.line.quantity`; `_action_done` hook; backorder/`backorder_id`; SO
linkage in `sale_stock`; carrier fields in `stock_delivery`; return-picking wizard;
company/quant/cron behavior) or **explicitly unresolved** (§9) — none blocking. Two
new integration items (the `send_to_shipper` `rate_and_ship` collision §5; the
`sale_id` single-SO resolution §4) are escalated to DEC-038.
