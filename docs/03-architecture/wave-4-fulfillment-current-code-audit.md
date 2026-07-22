# Wave 4 — Actual Merged-Code Integration Audit (Gate A)

> **Status: CANDIDATE — Gate A Phase 3 output, pending control-room acceptance.**
> A symbol-level audit of the **actual merged code** at the required base
> `mvp/program-integration@ab4f12f5a6857b2f3318ffc3b3f5f371307938bc`, so the Wave 4
> fulfillment architecture is traced to real current code — not designed from
> documents. Every material claim carries `file : symbol : line`. This file
> authorizes no implementation.
>
> **Governance note.** Reading merged implementation code for a Gate A audit is
> permitted governance work; **authoring the fulfillment transport/reconcile code
> is Gate B implementation**, gated on explicit ChatGPT/product-owner
> authorization. Nothing here is unlocked by the presence of the Layer 2 selftest
> scaffold.

**Merged addons at base:** `adams_base`, `shopify_connector_core`,
`shopify_connector_product`, `shopify_connector_sale`, `shopify_connector_inventory`.
**No `shopify_connector_fulfillment` exists** — fulfillment is greenfield.

---

## 1. Core Stage 0 Layer 2 substrate — the mutation spine fulfillment plugs into

The accepted Layer 2 protocol (DEC-031/DEC-036) is fully implemented in
`shopify_connector_core`. A fulfillment write **reuses this spine verbatim** by
supplying 7 strategy callables — it does **not** re-implement it.

| Component | Location | Reuse for fulfillment |
|---|---|---|
| Job model / 10-state machine, legal transitions, `PROTECTED_JOB_FIELDS` | `shopify_connector_job.py : ShopifyConnectorJob : L6-54,100-512` | A fulfillment write **is this exact model**; it adds a `job_type`, not a new state. |
| `job_type` Selection (extend via `selection_add`) | `shopify_connector_job.py : job_type : L142-169` | Add `fulfillment_create` (+ `*_reconcile`, + `fulfillment_tracking_update`) mirroring `mutation_dispatch_selftest`/`…_reconcile`. |
| `job_source`/`trigger_origin`; `trigger_origin='fulfillment_picking_validation'` **already exists** | `shopify_connector_job.py : L119-141,750-760` | Enqueue with `job_source='odoo_event'`, `trigger_origin='fulfillment_picking_validation'` (L136) — already business-gated. |
| `idempotency_key` = `store|job_type|res_model|res_id|shopify_target_gid|payload_hash`, `UNIQUE(store_id, idempotency_key)`; `operation_scope_key` = `store|res_model|res_id|shopify_target_gid` (while non-terminal), `UNIQUE` | `shopify_connector_job.py : _compute_idempotency_key/_compute_operation_scope_key : L207-257,701-748` | **Pre-send dedup + single-in-flight-per-target serialization for free** — no new dedup mechanism. |
| `_claim_for_dispatch` (`FOR UPDATE SKIP LOCKED`) | `shopify_connector_job.py : L518-572` | Fulfillment jobs claimed by the same drain. *(Docstring: multi-worker not proven by `TransactionCase`.)* |
| Dispatcher drain + per-job txn + concurrency recovery | `shopify_connector_job_dispatch.py : run_drain/_drain_one/_recover_after_concurrency_conflict : L166-437` | On PG 40001/40P01/55P03: rollback + route **once by replay policy without replaying the handler** — what makes a non-idempotent fulfillment write safe under concurrency. |
| **C1/C2/NET/C3 mutation protocol** | `shopify_connector_job_dispatch.py : _drain_mutation_one/_commit_attempt_intent_c2/_commit_mutation_outcome_c3 : L1047-1370` | C1 claim+`current_attempt_token`+commit; **C2 durable attempt on an INDEPENDENT side cursor** (`transport_attempted=True`)+commit; NET transport (exceptions→uncertain); C3 re-lock+revalidate token/state+immutable outcome+identity check+consequence+commit. **The at-most-once + reconciliation-convergence spine** (never a claimed exactly-once remote effect; §7.1 P0). |
| Mutation-domain strategy registry (7 keys) | `shopify_connector_job_dispatch.py : _get_reconciliation_strategies/MUTATION_STRATEGY_KEYS : L117-125,443-483` | **PRIMARY EXTENSION SEAM** — `_inherit` dispatch, add-merge a `{7 callables}` dict; `_validated_mutation_strategy` fails closed on any missing key. Only `mutation_dispatch_selftest` registered today. |
| Reconciliation handler + `INCONCLUSIVE_RECONCILIATION_CAP=3` → `duplicate_risk` block; `observed_store_identity==expected` | `shopify_connector_job_dispatch.py : _handle_…_reconcile/_validate_reconciliation_result : L852-1045` | **The true dedup/at-most-once backstop for fulfillment** (since `@idempotent` is unavailable). **Reconcile-only after `transport_attempted=true`; read absence = INCONCLUSIVE, never resend** (§7.1 P0). |
| Replay-policy registry (`local_only`/`remote_read_replay_safe`/`remote_effect_not_replay_safe`; fail-closed default) | `shopify_connector_job_dispatch.py : _get_replay_policies : L102-115,1471-1506` | Fulfillment write = `remote_effect_not_replay_safe`; reconcile = `remote_read_replay_safe`. |
| DEC-009 retry/failure routing (16 fixed error classes; bounded backoff 30s×2, cap 30min, ±20% jitter, max 12, 24h) | `shopify_connector_job_dispatch.py : _route_failure/_schedule_retry_or_fail : L26-160,1660-1748` | Handlers raise `JobHandlerError(error_class,…)`; routing/backoff/manual-review free. **No 17th class may be added.** |
| **Mutation-attempt evidence model** (immutable; `attempt_token`, `business_intent_fingerprint`, `exact_request_fingerprint`, `shopify_idempotency_key`, `idempotency_valid_until≈now+23h`, `observed_outcome`); **one-attempt-per-job `UniqueIndex`** | `shopify_connector_mutation_attempt.py : L35-306` | A fulfillment retry after a clean failure needs a **NEW (replacement) job** — attempt reuse is forbidden. `shopify_idempotency_key` will be **null/unused** for fulfillment. |
| Fingerprints (`canonical_sha256`), `business_intent_fingerprint`, `exact_request_fingerprint` | `shopify_connector_mutation_attempt.py : L15,60-65,231-282` + `dispatch.py:1272-1296` | `business_intent_fingerprint` = connector-side stable identity of a fulfillment intent (independent of Shopify idempotency). |
| API client `execute_business` + `_admit_mutation` + `_validate_graphql_operation` (re-checks `exact_request_fingerprint == canonical_sha256({operation,variables})` before send); `_send` = only HTTP path | `shopify_connector_api_client.py : L106-116,353-816` | The **only** sanctioned mutation entry point; ties the wire request to the durable attempt. Payload must be **byte-identical** to the C2 fingerprint. |
| Call-lease quiescence (in-flight call blocks disconnect finalization) | `shopify_connector_call_lease.py : L4-68` | An in-flight fulfillment write holds disconnect open until released/timeout. |
| Store lifecycle: monotonic `connection_generation`; two-phase disconnect on lease count **AND** Layer-2 blockers (pending attempts + open reconcile jobs) | `shopify_connector_store.py : L111-153,623-1065` | Unreconciled fulfillment mutation holds disconnect open; stale-generation calls refused. |
| Readiness: `REQUIRED_MVP_SCOPES` = **6 read scopes incl. `read_fulfillments`** (the OLD scope); `_get_checks` add-only seam; `fulfillment_domain_enabled` flag exists | `shopify_connector_readiness_check.py : L53-72,170-190,227-269` | **The D-014-2/DEC-033 swap is NOT yet applied** — Wave 4 replaces `read_fulfillments`→`read_merchant_managed_fulfillment_orders` and appends a conditional `write_merchant_managed_fulfillment_orders` check via `_get_checks`. |
| Manual-review: 9 subreasons incl. **`fulfillment_notification_confirmation_missing`** (reserved, **no emitter yet**), `destructive_write_guard_blocked`, `inventory_location_missing`; mutation-evidence jobs forced through admin resolution | `shopify_connector_job.py : L70-83,356-400` + `shopify_connector_job_actions.py : L7-114` | The reserved fulfillment subreason must get an emitter (block_manual_review path). |
| Job log + redaction `_system_append` (strips `shpat_`/`shprt_`, PII) | `shopify_connector_job_log.py : L40-95` + `tools/redaction.py : L3-56` | All fulfillment audit auto-redacted. |
| Stale-owner sweep (crash recovery → reconciliation if C2 committed, else requeue) | `shopify_connector_stale_owner_sweep.py : L14-108` | Crash-safety net for fulfillment writes. |
| Security: 4 groups (auditor/operator/reviewer/admin); **`mutation.attempt` READ-ONLY for all incl. admin** (service-writable only); `PROTECTED_JOB_FIELDS` | `security/shopify_connector_security.xml`, `ir.model.access.csv` | Fulfillment attempt evidence inherits read-only-to-users; no new ACL for the Abstract services. |
| Domain-flag start gate `_domain_flag_for_job_type` (returns `None` today) | `shopify_connector_job.py : L449-512` | Map fulfillment `job_type`→`fulfillment_domain_enabled` so it refuses to start unless enabled. |
| **Core Shopify-Location cache** (`shopify.connector.location`; Shopify-side-only; "never stores Odoo-location IDs") | `shopify_connector_core/models/shopify_connector_location.py : L4-30` | **The sanctioned cross-domain Location reference fulfillment MAY read** (read-only) — never `location_mapping`. *(Currently populated by the inventory location-sync job — a shared-ownership item, see §4/§6.)* |

### 1.1 The 10 fulfillment integration seams (exact code evidence)

1. **Registry seam:** `_inherit 'shopify.connector.job.dispatch'`, add-merge `_get_reconciliation_strategies()` a dict keyed by fulfillment `job_type` with the 7 `MUTATION_STRATEGY_KEYS` (`dispatch.py:117-125,443-460`).
2. **Job-type seam:** `selection_add` write + `*_reconcile` types (`job.py:142-165`); register in `_get_handlers()` + `_get_replay_policies()` (build-time completeness invariant).
3. **Enqueue seam:** `env['shopify.connector.job.enqueue'].enqueue(store, 'odoo_event', '<fulfillment_create>', payload_hash=…, res_model='stock.picking', res_id=…, shopify_target_gid=<order/FO GID>, trigger_origin='fulfillment_picking_validation')` (`enqueue.py:22-66`).
4. **Transport seam:** `strategy['transport']` → real `fulfillmentCreate` via `client.execute_business(job, store, mutation_query, variables, mutation_context={job_id,attempt_id,attempt_token,mutation_domain})` (`api_client.py:353-472`).
5. **Reconcile seam:** `strategy['reconcile']` → read-only Shopify query (order's `fulfillmentOrders`/`fulfillments`) returning `{verdict, observed_store_identity, …}`; identity must equal `expected_store_identity` (`dispatch.py:894-968`).
6. **Replay-policy seam:** write = `REMOTE_EFFECT_NOT_REPLAY_SAFE`, reconcile = `REMOTE_READ_REPLAY_SAFE` (`dispatch.py:1471-1493`).
7. **Consequence seam:** `classify_direct_result` → consequence dict (`_validate_job_consequence('direct')`, DIRECT_ACTIONS `dispatch.py:126-129`); `apply_consequence` → write fulfillment binding/mirror.
8. **Connection-epoch seam:** admission refuses stale `connection_generation`; C3 re-checks `shop_domain`+generation+`job_type` (`dispatch.py:1345-1359`).
9. **Domain-flag start-gate seam:** override `_domain_flag_for_job_type` → `fulfillment_domain_enabled` (`job.py:489-512`).
10. **Readiness seam:** override `_get_checks(store)` to add the write-scope check (`readiness_check.py:170-190`).

---

## 2. Order domain (`shopify_connector_sale`) — matching input + anchor + company scope

| Finding | Location | Fulfillment relevance |
|---|---|---|
| **Order binding** (`shopify.connector.order.binding`), `sale_order_id` M2O(restrict), `UNIQUE(store_id, shopify_gid)` + `UNIQUE(store_id, sale_order_id)`; no PII snapshot | `shopify_connector_order_binding.py : L5-113` | **Anchor**: locate the Odoo `sale.order` from a Shopify Order GID; `sale_order_id` is the picking-creation target. At most one `sale.order` per Order GID per store. |
| **`sale.order.line.shopify_line_item_gid`** (the D-014-4 matching input) — `Char, index=True, readonly=True`; populated on **product lines only** (`importer:1339`); **currently WRITE-ONLY — written once, read by NO matching logic** | `shopify_connector_sale_order_line.py : L9` | **Fulfillment is the first consumer.** The matching **input** exists and is populated; the matching **algorithm does not exist yet**. Shipping/rounding/discount lines carry **no** GID (matcher must skip null-GID lines). Not uniquely constrained. |
| Quantity gate: refuses orders where `quantity != currentQuantity` (refunded/removed) | `shopify_connector_order_importer.py : _precreation_gates : L722-738` | `currentQuantity` excludes refunded/removed but **NOT fulfilled** units → partial fulfillment does not trip this gate. `product_uom_qty` = the delivery-move demand. |
| Cancellation evidence: pre-cancelled orders skipped; `shopify_cancelled_at`/`shopify_cancel_reason` on binding; post-import cancellation **only routes to review**, does not cancel/unlink a delivery | `importer : L606-612,2255,2398` | Fulfillment must honor the cancel snapshot; **gap:** no seam cancels/unlinks a delivery on Shopify cancellation. |
| COD/transaction evidence import (`is_cod`, `cod_commercial_state`, `cod_collection_state`, `cod_*_value_amount`) | `importer : L2092-2290` + `order_binding.py:77-104` | `cod_fulfillment_state`/`cod_collection_state` are the COD read-model a delivery/collection flow extends; `_manual_collected_amount` = collected-cash basis for COD-on-delivery reconciliation. |
| **Duplicate prevention** template: search `(store_id, shopify_gid)`→refresh; savepoint + `IntegrityError`→`concurrency_race_conflict`; scan `payload_hash=updatedAt` dedup | `importer : L466-471,528-542` + `order_scan.py:394-437` | **Idempotency template to mirror** for a fulfillment importer/scan. |
| Company scope: `settings.order_company_id` + `with_company` redispatch + **immutable-after-first-binding lock** | `importer : L456-464` + `store_settings.py:62-67,147-164` | Fulfillment picking/warehouse resolution **must run inside `order_company_id`**. |
| **Delivery/picking linkage ABSENT** — only inert snapshots: `shopify_fulfillment_status_snapshot` (from `displayFulfillmentStatus`), `cod_fulfillment_state` (single hardcoded `'not_dispatched'`) | `order_binding.py : L26,88-90` + `importer:2252,2284` | Pre-declared **inert** seams a fulfillment domain widens; **no picking is created/tracked here today** — fulfillment linkage is greenfield. |

**⚠ Order-domain risk — `action_confirm()` auto-pickings:** the importer confirms
the SO (`importer:515,2355,2390`), but `shopify_connector_sale` declares **no
`sale_stock` dependency** and neither tracks nor reconciles pickings. If
`sale_stock` is installed (it is `auto_install:True` and pulled transitively by
the fulfillment addon's `stock_delivery`+`sale_stock` deps), `action_confirm()`
**auto-creates delivery pickings** the connector does not currently own. **Gate A
decision (→ DEC-038):** Wave 4 must explicitly decide that fulfillment **drives /
adopts these auto-created pickings** (its trigger `_action_done` fires on their
validation) rather than creating parallel pickings — and test the coexistence.

---

## 3. Odoo stock/delivery seam (cross-reference)

Traced in `docs/01-research/wave-4-odoo19-fulfillment-architecture-notes.md`:
`stock.picking._action_done` is the once-per-validation hook (D-014-3 ✓);
done-qty = `stock.move.line.quantity`; `backorder_id` chains; `sale_id`/`sale_line_id`
from `sale_stock`; carrier fields from `stock_delivery`; the `send_to_shipper`
`rate_and_ship` collision risk (§5 there); company via `picking_type_id`; quant-layer
concurrency; return-picking wizard boundary.

---

## 4. Inventory domain (`shopify_connector_inventory`) — the reusable Layer 2 template

The inventory domain is the **exact, reviewed template** the fulfillment mutation
domain mirrors (by imitation — **there is no shared base class**).

| Template component | Location | How fulfillment mirrors it |
|---|---|---|
| Strategy registry (`_get_reconciliation_strategies`, add-only merge) | `shopify_connector_inventory_service.py : L560-582` | Same pattern; register the fulfillment domain key → 7 callables. |
| `prepare_local` (C1 immutable-id snapshot, hashable) | `…_service.py : _prepare_local_set_quantities : L2193-2206` | Return immutable ids + `expected_connection_generation` + `expected_store_identity`. |
| **`prepare_preconditions`** (fresh pre-C2 read, fail-closed, request builder) | `…_service.py : _prepare_preconditions_set_quantities : L2208-2380` | Build the `fulfillmentCreate` operation+variables here; fail closed on every unsafe precondition; **OMIT the `@idempotent` directive** (fulfillment has none) — inventory embeds `@idempotent(key:$idempotencyKey)` at L2327-2336, **fulfillment must not**. |
| `transport` (`execute_business` context-manager) | `…_service.py : _transport_set_quantities : L2382-2425` | Mirror verbatim; on any exception return `{outcome:'uncertain', error_class:…}`, never re-raise past C2; never default missing `userErrors` to `[]`. |
| **`classify_direct_result`** (+ positive-success gate) | `…_service.py : _classify_direct_set_quantities/_is_valid_set_quantities_success : L2427-2640` | `fulfillmentCreate` returns **base `UserError` (no `code`)** → fulfillment uses the **`code_required=False` / payload-shape-only** branch (like `_classify_direct_activate` L3059-3162), **not** the code-routing branch. Require **positive success evidence (a real fulfillment id)** before treating empty-`userErrors` as applied. |
| `reconcile` (read-only verdict; freshness vs `transport_at`; fail-closed) | `…_service.py : _reconcile_set_quantities : L2642-2750` | Read the order's `fulfillmentOrders`/`fulfillments` read-only; return `applied|not_applied|inconclusive`; never guess; bounded by `INCONCLUSIVE_RECONCILIATION_CAP`. |
| `apply_consequence` (domain callback; must terminalize/handoff) | `…_service.py : _apply_consequence_set_quantities : L2752-2829` | Persist the returned fulfillment id onto the fulfillment binding on succeed; use `domain_callback` + a handoff primitive for resend/chain. **Do NOT copy the CAS branch** (inventory-only). |
| Job-type + `operation_scope_key` override (own literal) | `…_service.py : L124-128,311-418` | Define fulfillment's **own** scope literal (per FulfillmentOrder / per picking); override `_compute_operation_scope_key` for its own types only; leave others to `super()`. **Do not reuse `pair_scope_key`/`cas_retry_ordinal`.** |
| Enqueue via sanctioned service (fresh uuid `payload_hash`) | `…_service.py : _create_inventory_job : L798-834` | Same; never `job.sudo().create()`. |
| Atomic handoff primitives (flush-before-insert to avoid scope-key collision) | `…_service.py : _handoff_supersede/_block_pair : L2069-2187` | Reuse the terminalize+flush-then-insert ordering for job chaining. |
| Review-release (public action on binding → private service helper) | `…_level_binding.py:211-223` + `…_service.py:3434-3552` | Public action on the fulfillment binding → private helper; Reviewer/Admin, exactly-one-blocked-job, audit-safe reason, handoff release. |
| First-push confirmation gate (preview→confirm→execute) | `…_level_binding.py:70-80,175-209` | Optional model for the notification-confirmation gate (`fulfillment_notification_confirmation_missing`). |
| Readiness `_check_mapped_location` (pure read-only, domain-flag + scope) | `…_service.py:425-473` | Template for the fulfillment write-scope readiness check. |
| Security ACL matrix (Auditor r / Operator r+c / Reviewer r+w / Admin r+w+c; no unlink; sanctioned-service creation) | `security/ir.model.access.csv:1-9` | Mirror the group matrix + protected-mixin + group-checked service creation. |

**Module boundary (hard):** `shopify.connector.location.mapping`
(`shopify_connector_location_mapping.py:18`) is **inventory-domain-private**;
**fulfillment MUST NOT read/import/query it**. Fulfillment resolves Shopify
Location from the FulfillmentOrder `assignedLocation` and/or the **core
`shopify.connector.location` cache** (read-only). Evidence it doesn't need it:
`fulfillmentCreate` assigns fulfillment **through** the FulfillmentOrder's location,
not a supplied `locationId`.

---

## 5. Reusable vs missing vs cross-module changes

### 5.1 Reusable (no new code)
The entire Layer 2 spine (§1): job model, dispatcher, C1/C2/NET/C3, mutation-attempt
evidence, fingerprints, reconciliation cap, replay policies, retry taxonomy, admission
guard, call-lease quiescence, connection-generation, stale-owner sweep, redaction,
security groups, `trigger_origin='fulfillment_picking_validation'`,
`fulfillment_domain_enabled` flag, and the `fulfillment_notification_confirmation_missing`
subreason. The order binding + `shopify_line_item_gid` + company-scope invariants (§2).
The inventory 7-callback pattern + scope-serialization + handoff + review-release (§4).

### 5.2 Missing seams fulfillment must build (Gate B)
- The concrete **fulfillment binding model** (inherits `binding_mixin`; maps
  FulfillmentOrder/Fulfillment GID ↔ Odoo picking; per D-014-1).
- The **matching algorithm** consuming `shopify_line_item_gid` (write-only today) →
  FulfillmentOrder-line GIDs (RA-023).
- The **7 real callbacks** for `fulfillment_create` (+ `fulfillment_tracking_update`)
  — re-implemented, not inherited (no shared base → **behavioral-drift risk**;
  tests must re-copy the fail-closed/positive-evidence invariants).
- An **emitter** for `fulfillment_notification_confirmation_missing`.
- Re-implemented private helpers (`_read_shopify_*`, `_strict_shopify_int`,
  `_fail_closed_pre_c2` equivalents) — inventory's are private.
- The **inbound** models (evidence records, origin classification, review cases) and
  the **Mode 2** engine — entirely greenfield in the sale/inventory domains.

### 5.3 Cross-module changes that ARE necessary (narrow)
- **`shopify_connector_core/models/shopify_connector_readiness_check.py`** — the one
  named core edit: `REQUIRED_MVP_SCOPES` swap `read_fulfillments` →
  `read_merchant_managed_fulfillment_orders` (D-014-2/TD-002) + its test. *(All other
  fulfillment needs — write-scope check, domain flag map, job-type/strategy/handler/
  replay registration — are add-only via `_inherit`/`selection_add`/`_get_*` override,
  **zero core edits**, proven by the inventory domain doing exactly this.)*

### 5.4 Cross-module changes that are NOT necessary (avoid)
- No edit to `shopify_connector_sale` internals beyond **reading** the order binding +
  `shopify_line_item_gid` and **widening** `cod_fulfillment_state`/adding fulfillment
  fields *(a schema addition on the binding — decide owning module in Phase 5)*.
- **No** dependency on / read of `shopify_connector_inventory` or `location_mapping`.
- No new core job state, no 17th error class, no parallel mutation framework.

---

## 6. Architecture risks (traced to code) → feed DEC-038 + risk register

1. **No native fulfillment `@idempotent`** (`dispatch.py` selftest embeds it;
   fulfillment cannot) → **at-most-once** (never a claimed exactly-once remote effect)
   rests **entirely** on C1/C2/NET/C3 + `business_intent_fingerprint` + the **reconcile
   verdict**; eventual consistency between write and `fulfillmentOrders` read can cycle
   to `INCONCLUSIVE_RECONCILIATION_CAP=3` → `duplicate_risk` admin block (operator load,
   not silent dup). **Reconcile-read determinism is the single most important
   fulfillment design risk.** Once `transport_attempted=true` the job is
   **reconcile-only**; **read absence is INCONCLUSIVE, never a resend** (§7.1 P0 —
   DEC-038 §7.1).
2. **Selftest classifier branch `'IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED'`
   (`dispatch.py:566-568`) is NOT a documented Shopify code** — a real fulfillment
   classifier must not copy it; documented codes are `IDEMPOTENCY_CONCURRENT_REQUEST`,
   `IDEMPOTENCY_KEY_PARAMETER_MISMATCH` (both idempotency-only, irrelevant to
   fulfillment). Fulfillment classifies on `userErrors` (no code) + positive evidence.
3. **Concurrency of the mutation path is not unit-provable** (needs real commit
   boundaries; `_claim_for_dispatch` multi-worker "not proven by any unit test") →
   the Phase 6 plan needs **genuine independent-transaction/process** concurrency
   tests (not savepoints).
4. **`exact_request_fingerprint` must be byte-identical** between C2 and the wire
   (`api_client.py:738-758`) → fulfillment payload building must be **deterministic**
   (sorted keys, stable serialization).
5. **`action_confirm()` auto-picking coexistence** (§2) — environment-dependent
   deliveries the connector must adopt, not duplicate.
6. **`send_to_shipper` `rate_and_ship` collision** (Odoo notes §5) — validating a
   delivery with a `rate_and_ship` carrier auto-books a shipment and overwrites
   `carrier_tracking_ref`.
7. **Core Location-cache shared ownership** — `shopify.connector.location` is
   populated by the **inventory** location-sync job; if the inventory domain is
   disabled, the cache may be empty. Fulfillment reads it read-only but must not
   assume inventory populated it — a **cross-domain population owner** question for
   Phase 5 (fulfillment may need to trigger/refresh the cache via a core-owned seam,
   never via `location_mapping`).
8. **Per-store API version** (`store.api_version` Char; not pinned in code) → Wave 4
   must verify the fulfillment GraphQL shapes against the **store's actual version**,
   and the unknown-value contract (status-model §7) must hold.

---

## 7. Unsupported document assumptions corrected by the code

- "D-014-4 matching is already wired" — **false**; only the input column exists,
  no matcher (`shopify_line_item_gid` has zero production read sites).
- "The order domain already links to deliveries/pickings" — **false**; entirely
  greenfield (no `stock.picking`/`fulfillmentOrder` code in `shopify_connector_sale`).
- "`cod_fulfillment_state` models real dispatch" — **false**; single hardcoded
  `'not_dispatched'` snapshot; widening it is a live-table schema/migration change.
- "A shared Layer 2 mutation base exists to inherit" — **false**; the template is by
  imitation (inventory), not inheritance — drift risk to guard with tests.
- "`REQUIRED_MVP_SCOPES` authorizes fulfillment writes" — **false**; it lists read
  scopes only and still contains the **old `read_fulfillments`**.

**Phase 3 completion criterion met:** the later architecture (Phase 5) can be traced
to real current code — every proposed integration point (registry/enqueue/transport/
reconcile/consequence/scope/readiness/binding/matching) has an exact seam or a named
missing seam with code evidence, and eight code-grounded risks are escalated to
DEC-038.
