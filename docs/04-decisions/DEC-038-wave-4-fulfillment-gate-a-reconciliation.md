# DEC-038 — Wave 4 Fulfillment Gate A Decision & Contradiction Reconciliation

> **Status: PROPOSED — NOT ACCEPTED.** Candidate Gate A decision-reconciliation
> record, produced by Claude as the explicitly-assigned Wave 4 Gate A
> governance/research worker (issue #186 comment `5038326525`). **It authorizes no
> implementation and accepts nothing by itself.** Acceptance authority for Wave 4:
> **ChatGPT control room** (scope governor, acceptance, merge), with the product
> owner as ultimate business authority. Every "proposed disposition" below remains
> proposed until the control room accepts this record.
>
> **Base:** `mvp/program-integration@ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`.
> **Evidence:** the Gate A companions — resource inventory
> (`docs/01-research/wave-4-fulfillment-resource-inventory.md`), Shopify notes
> (`…/wave-4-shopify-official-fulfillment-notes.md`, Admin API 2026-07, accessed
> 2026-07-21), Odoo notes (`…/wave-4-odoo19-fulfillment-architecture-notes.md`,
> Odoo 19.0 FINAL), and the code audit
> (`docs/03-architecture/wave-4-fulfillment-current-code-audit.md`, base
> `ab4f12f5`). **Next unused decision id verified = DEC-038.**

## Date
2026-07-21.

## Scope
Reconcile the Wave 4 fulfillment decision surface against **current official
Shopify/Odoo evidence** and the **actual merged code**, preserving accepted
rulings (DEC-011, DEC-036/DEC-031 Layer 2, DEC-033 scope, DEC-008/DEC-015,
RA-009/014/017/022/023) and either **preserving, refining, or escalating** the
proposed candidates (Task 014 packet + addendum, the 16-condition Mode 2 engine,
the four-layer status model, COD, reconnect, DoR). It decides **no exact Odoo
field names or code**; those are Gate B. Where a product/commercial ruling cannot
be derived from accepted records, it is **escalated** (§4), never guessed.

**Disposition vocabulary:** **PRESERVE** (accepted/verified, carry forward
unchanged) · **REFINE** (carry forward with a precise, evidence-backed correction/
addition) · **ESCALATE** (needs an explicit control-room/product-owner ruling).

---

## 1. Authority-model reconciliation (contradiction resolved)

The DoR, modes doc, status model, COD doc, and program files cite the **DEC-032**
"product owner + Claude control room" acceptance model. **REFINE:** for Wave 4 and
the remaining MVP program, issue #186 comment `5038326525` supersedes DEC-032
**only** where DEC-032/issue #167/`CLAUDE.md` assign Claude sole control-room or
sole merge authority: **ChatGPT = strategic control room / scope governor / prompt
authority / acceptance / merge-authorizing authority; Claude = independent reviewer
and authorized runtime/governance worker when explicitly assigned (may merge only
after explicit ChatGPT authorization); GPT-5.6 Sol = primary execution worker;
product owner = ultimate business authority.** All worker-separation, independent-
review, source-of-truth, and no-self-acceptance safeguards remain binding. Wave 4
documents updated in Phase 5–7 use this model; the underlying DEC-032 record is not
rewritten (its §13 addendum in `CLAUDE.md` already points here). **Control-room
acceptance required:** yes (it is the governance frame for the whole package).

---

## 2. The 41-item Wave 4 fulfillment decision matrix

Legend for **CR?** (control-room acceptance required): **Y** = product/architecture
ruling; **v** = verification-only (evidence confirms an accepted posture).

| # | Topic | Verified facts (evidence) | Accepted ruling to preserve | Contradiction / gap | Proposed disposition | Test implication | CR? |
|---|---|---|---|---|---|---|---|
| 1 | **Fulfillable-quantity source of truth** | Shopify `FulfillmentOrderLineItem.remainingQuantity: Int!` drives partial fulfillment (Shopify notes §3); Odoo done-qty = `stock.move.line.quantity`, demand = `product_uom_qty` (Odoo notes §1) | DEC-011 (FO-based), D-014-4 (qty = move done `quantity`, ≤ `remainingQuantity`) | Modes cond.7 says `stock.move.product_uom_qty` vs done `quantity`; must be explicit which drives the create | **REFINE:** the **fulfilled quantity sent** = the picking's per-line **done `stock.move.line.quantity`**, and it must be **≤ the FO line's `remainingQuantity`** (re-read fresh pre-C2); `product_uom_qty` is demand only, never the sent quantity | pass: qty=done; fail-to-review: qty>remaining → `over_fulfillment` | v |
| 2 | **Odoo pickings/moves ↔ Shopify FOs** | One Order → **many** FOs; **>1 FO per location possible** (Shopify notes §3, corrects "one FO/location") | D-014-4 (picking→sale_id→order binding→order GID→FOs) | Modes §4.1 "one FO per fulfilling location" is a simplification | **REFINE:** map **per validated picking** to the FO(s) for that order+location; **iterate all FOs**, never assume one-per-location; `assignedLocation` groups them | test: order with 2 FOs at one location | Y |
| 3 | **Shopify FO line items ↔ Odoo lines** | `FulfillmentOrderLineItemInput.id` = the **FulfillmentOrderLineItem GID** (not order-LineItem, not variant); the FO connection field is **`lineItems`** (Shopify notes §3); `sale.order.line.shopify_line_item_gid` exists but is **read by no matcher** (audit §2) | D-014-4 matching via `shopify_line_item_gid` (RA-023) | Matching must resolve **order-LineItem GID → FO-line-item GID**, a 2-hop the docs require; matcher does not exist yet | **REFINE:** matching chain = Odoo move → `move.sale_line_id` → `sale.order.line.shopify_line_item_gid` (LineItem GID) → the FO line whose `lineItem.id` equals it → that FO-line-item's `id` (used in the mutation). Skip null-GID lines (shipping/discount/rounding) | pass: full map; fail: unresolved line → `mapping_missing` (RA-023) | Y |
| 4 | **Partial picking / partial fulfillment** | Odoo done-qty per line; Shopify `remainingQuantity` decrements; events carry no qty (Shopify notes §5) | DEC-011 partial posture (fulfill delivered qty; backorder = new event); D-014-4 | DEC-011 leaves exact partial rules OPEN | **REFINE:** each validated picking (incl. backorder) fulfills exactly its done quantities against `remainingQuantity`; no partial automation within one create; unresolved partials → review | pass: partial create; qty math | Y |
| 5 | **Multiple pickings / order** | Backorder chain via `backorder_id`; each `_action_done` is one event (Odoo notes §3) | D-014-3 (each backorder picking = own event) | — | **PRESERVE**; connector **must follow `backorder_id`** to avoid treating a backorder as unrelated | test: backorder-chain 2 pickings/2 fulfillments | v |
| 6 | **Multiple Shopify FOs / order** | >1 FO per order and per location (Shopify notes §3) | RA-023 (never fulfill by order-ID) | Simplification in modes | **REFINE:** decompose per-FO; each FO-scoped create passes the checklist independently or → `picking_ambiguous`/review | test: multi-FO decomposition | Y |
| 7 | **Multi-location fulfillment** | `fulfillmentCreate` = "same Order **and Location**"; location via FO `assignedLocation` (`.location` **nullable**, snapshot fallback) (Shopify notes §3) | DEC-011 (single-location Phase 1; multi-location C-FUL-02 **deferred**); D-014-5 | Modes wants Mode 2 to resolve location within Wave 4; C-FUL-02 defers **automation** | **PRESERVE deferral of multi-location _automation_**; **REFINE:** a single fulfillment spanning FOs at different locations **decomposes per-location or routes to review** (never one cross-location create). Location resolved from FO `assignedLocation` + core location cache, **never `location_mapping`** (audit §4) | test: mismatch/multi-location → review; null `location` fallback | Y |
| 8 | **Backorders (Odoo)** | `create_backorder` on `stock.picking.type` (ask/always/never); non-interactive via `skip_backorder`+`cancel_backorder` (Odoo notes §3) | Modes §4.1 (force backorder explicitly, no wizard) | — | **PRESERVE**; **REFINE:** automated validation must drive `cancel_backorder` deterministically (never the `ask` wizard) | test: deterministic split + backorder | v |
| 9 | **Cancelled Odoo pickings** | Picking `cancel` state move-driven; post-import Shopify cancellation only routes binding to review, does not cancel delivery (audit §2) | Modes §5 edge table (cancelled → never auto-reverse) | **Gap:** no seam cancels/unlinks a delivery on Shopify cancel | **REFINE:** a cancelled Odoo picking is **not** a fulfillment event (excluded by D-014-3 `state=='done'`); a Shopify-side cancel after Odoo `done` → high-visibility review (no auto-reverse); returns are manual | test: cancelled picking → no create | Y |
| 10 | **Cancelled Shopify FOs** | `CANCELLED` status = merchant-cancelled; `fulfillmentOrderCancel` (service FOs) creates a **replacement OPEN FO**; `INCOMPLETE` not a dead end (Shopify notes §3.1) | Modes/status model (CANCELLED never auto-reverses stock) | Must follow successor/replacement FOs | **REFINE:** exclude `CANCELLED`/`CLOSED`/`INCOMPLETE` FOs from selection; **follow replacement FOs**; connector-created fulfillment later cancelled + Odoo `done` → review | test: cancelled FO excluded; replacement followed | Y |
| 11 | **Returns / reverse transfers** | `stock.return.picking` = transient wizard, `origin_returned_move_id`, `_can_return` needs `done`/SO-linked (Odoo notes §6) | Prompt §7 (Shopify-side returns OUT of Wave 4); COD PD-COD-2 (`stock.return.picking` only stock-restoration path) | — | **PRESERVE**: Odoo returns researched only to define the forward boundary; **no Shopify-side return/reverse-fulfillment sync in Wave 4** | test: return does not create a Shopify fulfillment | v |
| 12 | **Initial tracking creation** | `fulfillmentCreate.trackingInfo` = `FulfillmentTrackingInput{company,number,numbers,url(URL scalar),urls}` (Shopify notes §4) | DEC-011 / D-014-6 (tracking at create) | `url`/`urls` are `URL` scalar (not String) | **REFINE:** emit RFC-valid `url`; carrier `company` as-is; multi-number → `numbers[]` | test: create with/without tracking | v |
| 13 | **Later tracking update** | `fulfillmentTrackingInfoUpdate(fulfillmentId, trackingInfoInput!, notifyCustomer)` current, in place (Shopify notes §4) | D-014-6 (update in place, never 2nd fulfillment; new `trigger_origin='fulfillment_tracking_change'`) | New trigger-origin value = a proposed DEC-019 vocabulary extension | **PRESERVE**; **ESCALATE** the DEC-019 `selection_add` third trigger-origin value for acceptance | test: in-place update; multi-number split | Y |
| 14 | **Carrier / URL normalization** | explicit `url` highest priority; recognized `company` auto-URL; number-only may yield invalid URL — send both (Shopify notes §5) | D-014-6 (`company` as-is, no client carrier table) | Docs recommend always sending `url` | **REFINE:** send `carrier_tracking_url` (`url`) whenever present; no client carrier table needed | test: URL passthrough; company passthrough | v |
| 15 | **Missing tracking data** | goods-shipped is the fact; create allowed without tracking | D-014-6 (create without trackingInfo + note) | — | **PRESERVE** | test: missing-ref create-with-note | v |
| 16 | **Mode 1 admission & behavior** | Odoo `_action_done` trigger (Odoo notes §2); outbound = create; inbound = observe/classify/review, **zero auto stock mutation** | Modes §2 (Mode 1 default, review-only inbound) | — | **PRESERVE**; Mode 1 = default | tests: outbound create; inbound review-only | Y |
| 17 | **Mode 2 admission & behavior** | Auto-validate Odoo delivery from external Shopify fulfillment only when all 16 conditions pass; fail-closed to Mode 1 | Modes §4 (16-condition engine) | Engine is **PROPOSED**, not settled (adjudication P1-2) | **RECONCILE** per §3; Mode 2 backend is Wave 4 scope; fails closed to review | tests: each condition pass + fail-to-review | Y |
| 18 | **The 16-condition Mode 2 engine** | See §3 (condition-by-condition) | Modes §4 conditions 1–16 | Proposed; some conditions need refinement vs current evidence | **RECONCILE** — preserve 12, refine 4, escalate 0 (see §3) | 16 pass + 16 fail-to-review tests | Y |
| 19 | **Mode switching w/ queued/running/uncertain/review jobs** | Mode switch = Admin-only, audited, never-replays, scan-gated, idempotent, rollback-safe (modes §6); Layer 2 jobs have durable state (audit §1) | Modes §6 state machine (+ PD-B4 scan boundary, 30-day default) | — | **PRESERVE**; **REFINE:** in-flight Layer 2 mutation/reconcile jobs are **not cancelled by a mode switch** (they complete under Layer 2); switching only stops **future** auto-application; pre-existing review cases persist | tests: switch with in-flight job; rollback | Y |
| 20 | **Disconnected-period reconciliation** | Reconnect re-scan since watermark; disconnect quiescence blocks on Layer-2 blockers (audit §1); reconnect policy §4.5 says "(Mode-dependent)", modes §7 says "review in both modes" | Modes §7 (disconnected external fulfillments → review in **both** modes) | **Contradiction:** reconnect policy wording | **REFINE:** adopt the **stricter, safer** modes §7 rule — disconnected-period external fulfillments **always land as review cases in both modes**; align reconnect policy §4.5 wording | test: gap-period fulfillment → review even in Mode 2 | Y |
| 21 | **COD interaction** | COD read-model on order binding (`is_cod`, `cod_*`); `_manual_collected_amount` (audit §2); PD-COD-1..6; `stock.return.picking` only restoration path | COD doc scenarios 4–13, PD-COD-2 | `cod_fulfillment_state` single hardcoded `'not_dispatched'` (schema widening needed) | **PRESERVE** COD scenarios 4–13 as Wave 4 scope; **REFINE:** widening `cod_fulfillment_state` is a live-table schema change (owning module decided Phase 5); `orderMarkAsPaid` stays **out of Wave 4** | tests: COD scenarios 4–13 state derivation | Y |
| 22 | **Non-COD interaction** | standard path; no financial gating | DEC-003 Domain 9 (finance separate from ops) | — | **PRESERVE** | test: non-COD create | v |
| 23 | **Manual-review cases** | 9 subreasons incl. `fulfillment_notification_confirmation_missing` (reserved, no emitter), `destructive_write_guard_blocked`, `inventory_location_missing` (audit §1); review-release template (audit §4) | DEC-009 review taxonomy; modes review reasons | Reserved subreason has no emitter | **REFINE:** fulfillment emits `fulfillment_notification_confirmation_missing` where a per-store confirmation is required but absent; other review reasons map to the named modes reasons | tests: each review reason + release | Y |
| 24 | **Mutation job types** | `job_type` `selection_add`; `mutation_dispatch_selftest`/`…_reconcile` shape (audit §1) | Layer 2 (job types via selection_add) | — | **REFINE:** register `fulfillment_create` + `fulfillment_create_reconcile` (+ `fulfillment_tracking_update` + its reconcile); register in `_get_handlers`/`_get_replay_policies` | test: build-time completeness invariant | Y |
| 25 | **One-job / one-attempt** | `mutation_attempt` one-attempt-per-job `UniqueIndex`; retry = NEW job (audit §1) | DEC-036 (one job → at most one attempt for lifetime) | No clone/replacement helper in core | **PRESERVE**; **REFINE:** a fulfillment retry after clean-fail/not-applied = a **freshly enqueued replacement job** (new `payload_hash`); the domain builds the replacement (no core helper) | test: replacement-job lineage | Y |
| 26 | **Operation-scope identity** | `operation_scope_key` `store|res_model|res_id|shopify_target_gid` (while non-terminal), `UNIQUE`; inventory overrides with its own literal (audit §1,§4) | DEC-036 (operation-scope serialization) | — | **REFINE:** fulfillment defines its **own scope literal** (per FulfillmentOrder or per picking; **decide granularity in Phase 5**) overriding `_compute_operation_scope_key` for its own types only | test: single-in-flight-per-scope | Y |
| 27 | **Idempotency identity** | fulfillment mutations **NOT `@idempotent`** (still-17 list, verified 2026-07-21); `business_intent_fingerprint`+`exact_request_fingerprint`; `shopify_idempotency_key` unused for fulfillment (audit §1,§6; Shopify notes §4.1) | DEC-011/D-014-7/RA-017 (connector-designed key + verify-before-retry); RA-014 | Phase-1 inventory mis-flagged the "17" as stale | **PRESERVE** (RA-014/RA-017 correct); **REFINE:** `prepare_preconditions` **omits the `@idempotent` directive**; dedup = `business_intent_fingerprint` + `operation_scope_key` + the **reconcile read**; correct the Phase-1 inventory "stale-17" note | test: no `@idempotent` in the fulfillment operation string (source-guard) | Y |
| 28 | **Retry & replacement lineage** | 16 fixed error classes; bounded backoff (max 12/24h); JobHandlerError (audit §1) | DEC-009 taxonomy (no 17th class) | — | **PRESERVE**; replacement lineage via `superseded_by_job_id` handoff pattern (audit §4) | test: retry backoff; lineage | v |
| 29 | **Uncertain-result reconciliation** | reconcile verdict `applied/not_applied/inconclusive`; `INCONCLUSIVE_RECONCILIATION_CAP=3` → `duplicate_risk` block; identity guard (audit §1) | DEC-036 reconciliation-before-retry | Reconcile-read determinism is the key risk (audit §6) | **PRESERVE**; **REFINE:** the fulfillment reconcile read = order's `fulfillmentOrders`/`fulfillments`; verdict from a matching fulfillment (own tracking/`business_intent`) or `remainingQuantity` having decreased by exactly our quantities (D-014-7) | test: verify-adopt / absent-resend / inconclusive-block | Y |
| 30 | **Clean rejection** | `userErrors` (base `UserError`, **no code**) → must require positive success evidence (audit §4) | DEC-009 (semantic errors → review) | Fulfillment can't use code-routing branch | **REFINE:** classify on `userErrors` presence + **positive success evidence (a real fulfillment id)**; empty `userErrors` alone ≠ success (`code_required=False` branch) | test: userErrors → fail/review; empty-but-no-id → reconcile | Y |
| 31 | **Store identity & connection generation** | `expected_store_identity=shop_domain`; admission refuses stale generation; C3 re-checks (audit §1) | DEC-036 store-identity/epoch | — | **PRESERVE** (reuse verbatim) | test: stale-generation refusal; identity mismatch | v |
| 32 | **Company consistency** | `settings.order_company_id` + `with_company` + immutable-after-binding lock; company via `picking_type_id`; picking name unique per company (audit §2; Odoo notes §7) | Order-domain company invariants | — | **PRESERVE**; **REFINE:** fulfillment picking/warehouse resolution runs in `order_company_id`; idempotency/scope keys company-scoped | test: cross-company refusal | Y |
| 33 | **Permissions & protected fields** | 4 groups; `mutation.attempt` read-only to all; `PROTECTED_JOB_FIELDS`; staff perm `fulfill_and_ship_orders` distinct from API scope (audit §1; Shopify notes §2) | Layer 2 security posture | Staff permission is a distinct axis not yet in readiness | **REFINE:** fulfillment binding inherits read-only-to-users; **add the `fulfill_and_ship_orders` staff-permission axis** to the readiness/UAT contract (distinct from API scope) | tests: ACL matrix; staff-perm vs scope distinct | Y |
| 34 | **Logging & secret/PII minimization** | `_system_append` redaction (strips token prefixes/PII); recipient names never logged; 2026-07-16 no-masking ruling (audit §1; security-pii §3) | Task 014 §4 logging posture | — | **PRESERVE**; tracking numbers/carrier = operational data (loggable); recipient names never in fulfillment log messages | source-guard test: no recipient name in logs | Y |
| 35 | **Scheduled & manual admission** | `job_source` webhook/manual_sync/scheduled_sync/reconciliation/odoo_event; reconciliation cron (D-014-8) follows the Odoo cron pattern (audit §1; Odoo notes §8) | D-014-8 reconciliation scan (cron 60min) | — | **PRESERVE**; the reconciliation-scan/manual-retry surfaces run under Layer 2 (superuser/new-cursor/chunked/`_commit_progress` pattern) | test: scan idempotency (uuid nonce) | Y |
| 36 | **Replay & duplicate prevention** | pre-send dedup via `UNIQUE(store_id, idempotency_key)`; `operation_scope_key` serialization; reconcile backstop (audit §1) | RA-017/D-014-7 (key + verify-read together) | — | **PRESERVE**; both controls required together | tests: duplicate admission blocked; replay prevention | v |
| 37 | **Readiness & scope checks** | `REQUIRED_MVP_SCOPES` still has old `read_fulfillments`; `_get_checks` seam; `fulfillment_domain_enabled` exists (audit §1) | DEC-033 §6 / D-014-2 (swap + conditional write) | Swap not yet applied (Wave 4 task) | **PRESERVE** the accepted swap; **REFINE:** the one named core edit = `REQUIRED_MVP_SCOPES` `read_fulfillments`→`read_merchant_managed_fulfillment_orders` + a `_get_checks`-appended conditional `write_merchant_managed_fulfillment_orders` check (active when `fulfillment_domain_enabled`) | tests: `REQUIRED_MVP_SCOPES` correct; write-scope seam check | Y |
| 38 | **Upgrade & uninstall behavior** | `original_job_type` retyping on uninstall; `stock_delivery`/`sale_stock` `auto_install:True`, `delivery.uninstall_hook`; large transitive graph (audit §1; Odoo notes §4) | DEC-030 lifecycle; MBQ-60 (stock_delivery hard dep) | — | **PRESERVE**; **REFINE:** install/upgrade/uninstall tests must exercise the **full bridge stack** (sale/stock/stock_account/delivery/…); zero residue | tests: install→upgrade→uninstall/reinstall, residue scan | Y |
| 39 | **Historical deliveries & reconnect** | reconnect re-scan; every disconnected-period external fulfillment → review (item 20) | Modes §7; reconnect policy | Wording alignment (item 20) | **REFINE:** never replay historic fulfillment; classify + dedup before any action; persisted past fulfillments stay review cases | test: reconnect catch-up | Y |
| 40 | **Dev-store resource cleanup** | CV-013 (#185) requires disposable resources + restoration; no live creds in Gate A | #185 / prompt §6 (missing creds not a Gate A blocker) | — | **PRESERVE**; dev-store campaign uses dedicated resources with cleanup/restoration; **no live mutation in Gate A** | (Phase 6 dev-store plan) | Y |
| 41 | **FO status/requestStatus eligibility (both modes)** | `FulfillmentOrderStatus` 7 values; **OPEN/IN_PROGRESS eligible**; **ON_HOLD/SCHEDULED = wait**; **INCOMPLETE/CLOSED/CANCELLED ineligible**; `requestStatus` `UNSUBMITTED` for merchant-managed; **`supportedActions.CREATE_FULFILLMENT` is the runtime-authoritative gate** (Shopify notes §3, §3.1) | D-014-4 (OPEN+IN_PROGRESS client-side); D-014-5 (ON_HOLD/SCHEDULED/INCOMPLETE → review) | Modes/D-014-4 use a status whitelist only | **REFINE:** gate `fulfillmentCreate` on `status ∈ {OPEN, IN_PROGRESS}` **AND `supportedActions` contains `CREATE_FULFILLMENT`** (defense-in-depth); treat ON_HOLD/SCHEDULED as defer, INCOMPLETE/CLOSED/CANCELLED as ineligible; for merchant-managed, key on `status` not `requestStatus` | tests: each FO status eligibility; supportedActions gate | Y |

---

## 3. The proposed 16-condition Mode 2 engine — reconciled condition-by-condition

Per adjudication P1-2 the engine is **PROPOSED, not settled law**. It is reconciled
against current Shopify (2026-07) + merged code without compressing, expanding, or
paraphrasing it. **Result: 12 PRESERVE, 4 REFINE, 0 supersede, 0 removed** — the
engine is sound; the refinements sharpen it, they do not weaken safety.

| # | Condition (as written, modes §4) | Disposition | Reconciliation note (evidence) |
|---|---|---|---|
| 1 | Exact order binding — fulfillment order GID resolves to exactly one connector order binding | **PRESERVE** | Order binding `UNIQUE(store_id, shopify_gid)` guarantees exactly-one (audit §2). |
| 2 | Exact fulfillment identity — Fulfillment GID captured; `status = SUCCESS` | **PRESERVE** | `FulfillmentStatus.SUCCESS` is the sole eligible value; A7 `displayStatus` never an automation input (Shopify notes §5). |
| 3 | Exact FulfillmentOrder identity — every `fulfillmentLineItems` entry traces to a known FO + FO-line GID | **REFINE** | The FO line-item id is the **FulfillmentOrderLineItem GID** via the FO `lineItems` connection (not `fulfillmentOrderLineItems` on the object); 2-hop from order-LineItem GID (Shopify notes §3, item 3). |
| 4 | Exact product + variant bindings — every Shopify line's variant has an active connector binding | **PRESERVE** | DEC-006 identity rules; product bindings exist in `shopify_connector_product`. |
| 5 | Exact line + quantity mapping — each fulfillment line maps 1:1 to an Odoo sale-order line via `shopify_line_item_gid`, matching UoM | **REFINE** | `shopify_line_item_gid` is populated on **product lines only**; **skip null-GID lines** (shipping/discount/rounding), and the field is not uniquely constrained → tolerate absent GIDs (audit §2). |
| 6 | No over-fulfillment — fulfilled qty ≤ ordered minus already fulfilled/reconciled on both sides | **PRESERVE** | Enforced by the per-line reconciled-quantity ledger + Shopify `remainingQuantity` (item 1). |
| 7 | Exact remaining Odoo quantity — candidate picking's pending demand equals/deterministically splits to the fulfillment's quantities | **REFINE** | Compare against done `stock.move.line.quantity` vs `product_uom_qty` (demand) — **not `qty_done`** (does not exist, Odoo notes §1). |
| 8 | Exact Shopify-location → Odoo-location mapping — FO `assignedLocation.location.id` maps to exactly one Odoo source location | **REFINE** | `assignedLocation.location` **can be null** (deleted/altered) → fall back to snapshot fields; location resolved via core `shopify.connector.location` cache, **never `location_mapping`** (audit §4). |
| 9 | One deterministic eligible picking or deterministic split — §4.1 yields exactly one answer | **PRESERVE** | §4.1 algorithm sound; any allocation choice → `picking_ambiguous`. |
| 10 | Valid reservations — picking `assigned` (or reservable) for the needed quantities | **PRESERVE** | `stock.picking.state=='assigned'` (Odoo notes §2). |
| 11 | Valid lot/serial info — tracked products: exact deterministic move-line lot/serial evidence | **PRESERVE** | `stock.move.line.lot_id/lot_name`; connector never chooses a lot (modes §5). |
| 12 | No duplicate application — this Fulfillment GID never applied; per-line reconciled quantities not exceeded | **PRESERVE** | Evidence-record unique GID + per-line ledger; mirrors Layer 2 dedup. |
| 13 | No conflicting fulfillment binding — candidate picking has no binding to a different Fulfillment GID | **PRESERVE** | D-014-1 binding uniqueness (`UNIQUE(store_id, picking_id)`). |
| 14 | Current Shopify state re-checked — live re-read confirms fulfillment still exists, `SUCCESS`, not `CANCELLED`, FO quantities corroborate | **PRESERVE** | The **fresh pre-C2 read** pattern is exactly the inventory `prepare_preconditions` template (audit §4); webhooks unordered → live re-read required. |
| 15 | Confirmed external — origin class is `external_*`, not `connector`/unknown | **PRESERVE** | Own-GID ledger is the primary/authoritative origin signal; **no app-attribution field** on Fulfillment (Shopify notes §5) → evidence-stacked classification stands. |
| 16 | Administrator has enabled Mode 2 (not suspended by switch/scan) | **PRESERVE** | `fulfillment_operating_mode` + mode-switch state machine (modes §6); maps to `fulfillment_domain_enabled` + a mode field. |

**Escalation on the 16-condition engine:** none of the four REFINEs changes a
condition's intent or safety bar; they align it to verified Shopify field names /
Odoo semantics / merged code. **The engine is preserved with 4 evidence-backed
sharpenings; no condition is superseded.** Control-room acceptance required (the
engine gates automated inbound stock mutation — the highest-risk surface).

---

## 4. Minimal control-room / product-owner question set (escalations)

Questions that **cannot be derived from accepted records** and need an explicit
ruling before Gate B implementation begins:

- **Q1 — `operation_scope_key` granularity (item 26):** should a fulfillment write
  serialize per **FulfillmentOrder GID** or per **Odoo picking**? (Recommendation:
  per **(store, picking, FulfillmentOrder GID)** — matches DEC-011's operation-level
  key intent; but confirm.)
- **Q2 — `action_confirm()` auto-picking coexistence (audit §2):** confirm that
  Wave 4 fulfillment **adopts** the `sale_stock`-auto-created delivery pickings (its
  `_action_done` trigger fires on their validation) rather than creating parallel
  pickings. (Recommendation: adopt.)
- **Q3 — Core Location-cache population owner (audit §6):** the
  `shopify.connector.location` cache is populated by the **inventory** location-sync
  job; if a store enables fulfillment but not inventory, may fulfillment trigger a
  **core-owned** cache refresh (never `location_mapping`)? (Recommendation: add a
  core/shared refresh seam; do not couple to inventory.)
- **Q4 — DEC-019 trigger-origin extension (item 13):** accept the proposed third
  `trigger_origin` value `fulfillment_tracking_change` via `selection_add`?
- **Q5 — COD-binding field ownership (item 21):** the widened `cod_fulfillment_state`
  + new fulfillment fields — do they live on the **sale** order binding (a schema
  addition to `shopify_connector_sale`, a cross-module edit) or on a **fulfillment**
  binding that references the order binding? (Recommendation: fulfillment-owned
  binding + read the sale COD read-model; avoid editing sale internals.)
- **Q6 — `send_to_shipper` `rate_and_ship` posture (Odoo notes §5):** confirm the
  operational rule that fulfillment stores use a `rate`-only carrier (or the
  connector writes `carrier_tracking_ref` directly) to avoid Odoo auto-booking a
  shipment on validation.
- **Q7 — API version pin (audit §6):** accept pinning the connector's fulfillment
  GraphQL to Admin API **`2026-07`** (vs the per-store negotiated version), with the
  unknown-future-value contract as the safety net?

None of Q1–Q7 blocks the Gate A **package** (each has a recommended default); each
must be **accepted or overruled** before the locked prompt is issued for Gate B.

---

## 5. Consequence for the DoR gates (feeds Phase 5)

- **G4-1 (Layer 2 accepted/implemented/proven):** ✅ satisfiable — DEC-036/DEC-031
  Layer 2 **Accepted** 2026-07-19; runtime-proven in Wave 3 (Task 013 PR #182).
- **G4-3 (state model):** ✅ content verified EXACT-MATCH vs 2026-07 (acceptance only).
- **G4-4 (scope correction):** ✅ accepted (DEC-033 §6); add the staff-permission axis.
- **G4-6 (Waves 2/3 merged):** ✅ order bindings + Layer 2 present at base.
- **G4-2/G4-5/G4-7/G4-8/G4-9:** require control-room acceptance of this record + the
  Q1–Q7 rulings; the technical contradictions are reconciled above.
- **CV-013 (#185):** carried forward as a **critical** Wave 4 obligation; Wave 4
  cannot receive final acceptance / enter RC / UAT while #185 is open. **Not
  downgraded.**

---

## Review / change control
- **This record decides no code and authorizes no implementation.** It is a
  **candidate** reconciliation pending ChatGPT control-room acceptance.
- Changes require control-room review. Accepted prior records (DEC-011, DEC-036,
  DEC-031, DEC-033, DEC-008, DEC-015, DEC-009, RA-009/014/017/022/023) are
  **preserved**, not re-litigated.
- On acceptance, the disposition set above becomes the binding input to the Wave 4
  DoR, the Task 014 packet re-acceptance (G4-5), and the locked implementation
  prompt.
