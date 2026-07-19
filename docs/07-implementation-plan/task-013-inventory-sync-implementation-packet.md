# Task 013 — Inventory Synchronization: Implementation-Ready Planning Packet

> **Status: GATE B ACCEPTANCE CANDIDATE (Revision 3) — NOT IMPLEMENTATION
> AUTHORIZED.** Corrected 2026-07-19 (Wave 3 Gate B session) per
> [`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md): CAS
> field name (`changeFromQuantity` throughout, §A.2/D-013-3), idempotency
> superseded from binding-owned to attempt-owned (D-013-1(b)/D-013-3),
> review-case-first drift handling (D-013-6/A.2), one-pair-per-request
> made binding (not batching), and the Layer 2 integration decision
> D-013-9. **Revision 2 (control-room comment `5015619162` on PR #179)
> corrects D-013-3/D-013-6/D-013-9: `inventory_activate` and
> `inventory_set_quantities` are each a standalone mutation job
> (`job_type == mutation_domain`), never two attempts inside
> `inventory_push_sync`, which is orchestration/read-only; see DEC-037
> §5/§9 for the corrected job model and consequence contract.**
> **Revision 3 (control-room comment `5015830229` on PR #179) further
> corrects D-013-3/D-013-6/D-013-9: a bounded CAS-stale retry and a
> reconciliation `not_applied` retry each create a **new**, separate
> mutation job (never a redispatch of the job whose attempt
> failed/resolved — every mutation job makes at most one attempt for its
> entire lifetime), the activation→orchestration handoff is atomic (not
> dependent on a later scan/manual trigger), `blocked_manual_review` is
> not terminal and is released only by the new
> `action_recheck_inventory_pair(reason)` action, and the `error_class`
> vocabulary is the fixed set in DEC-037 §7/§9 — see DEC-037 §5.4/§5.5/§9
> for the corrected atomic-handoff contract, review-release action, and
> consequence contract.** **The §8
> inline prompt is superseded — use
> [`../06-prompts/sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md)
> (LOCKED, unissued) instead.** Task 013 implementation requires Gate B
> accepted and merged **and** Stage 0 merged and runtime-proven. Original
> produced 2026-07-10 (AR-042 candidate).
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
(Datetime ro), `last_known_shopify_available` (Float ro) — **all three
informational/display/coalescing fields only, refreshed from a
reconciliation read or a `succeeded` attempt's evidence; never read as
transport-replay or idempotency authority** (Gate B correction,
DEC-037 §1 item C5) — and the **MBQ-38 first-push confirmation
record**, kept on the row (per-mapped-pair granularity = per binding
row, exactly DEC-018's MBQ-33 decision):
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

**D-013-3 — Push mutation mechanics [Gate B-corrected, Revision 2
2026-07-19, DEC-037 §1 item C8/§4 row 1/§5 — superseding this entry's
original 2026-07-10 text below].** `inventorySetQuantities` with `name:
"available"`, `reason: "correction"` (documented vocabulary),
`referenceDocumentUri: "odoo://<db-uuid>/shopify.connector.job/<id>"`,
one item per job (D-013-6, DEC-036 D4 — no batching): `quantities:
[{inventoryItemId, locationId, quantity, changeFromQuantity}]` —
`changeFromQuantity` is a **fresh Shopify read taken immediately before
this attempt's C2**, captured into `preconditions_snapshot` (DEC-036
D7; DEC-037 §4 row 1) — **never** read from the binding's informational
`last_known_shopify_available` field, which is display-only and may lag
the true current value. The mutation carries the **mandatory
`@idempotent(key: "<uuid4>")` directive** (required as of 2026-04).

**Job type and Layer 2 integration (Gate B-corrected, Revision 2 —
supersedes both the "key lives on the binding" design and Revision 1's
same-job activation design below).** `inventory_set_quantities` is its
**own standalone mutation job type** (`job_type == mutation_domain ==
'inventory_set_quantities'`, DEC-037 §4 row 1/§5 — corrected in Revision
2 from Revision 1's design, which folded this into `inventory_push_sync`).
Every dispatch of this job passes through the Stage 0 Layer 2 wrapper —
claim (C1, job-level) → domain-registration gate → precondition snapshot
capture → **C2** (side cursor: `mutation.attempt` row created,
`business_intent_fingerprint`/`exact_request_fingerprint`, the
idempotency key, `transport_attempted=true`) → **NET** → **C3** (outcome
commit). The Shopify idempotency key and both fingerprints live
**exclusively on `shopify.connector.mutation.attempt`** — request-level
and attempt-owned, **never** on the binding, and **never** the retry
authority via any binding field (DEC-036 D6; DEC-037 §1 item C5). This
job makes **at most one** mutation attempt for its entire lifetime
(Revision 3, DEC-037 §5.1/§9 — a job is never redispatched to make a
second attempt); a CAS-stale outcome transitions this job to the
existing terminal state `cancelled` and a **new**, separate
`inventory_set_quantities` job (own job ID,
`cas_retry_ordinal + 1`, own fresh fingerprints, own fresh key) is
created instead (DEC-037 §5.4 handoff C) — never a same-job redispatch
and never a key reuse. **This job is never enqueued directly by
`inventory_activate`** — it is enqueued only by a fresh `inventory_push_sync`
orchestration dispatch (DEC-037 §5.2). See DEC-037 §4 row 1 and §9 for
the complete matrix and consequence contract.

**Error routing (Gate B-corrected, Revision 3 — DEC-037 §4 row 1/§9):**
`CHANGE_FROM_QUANTITY_STALE` → `observed_outcome='failed_clean'`,
`error_class='concurrency_race_conflict'`; bounded re-read/re-derive,
**3** replacements maximum, each a **new, separate `inventory_set_quantities`
job** — **never a redispatch of the job whose attempt just failed**
(Revision 3 correction: Revision 2's "redispatch of this same job"
design is withdrawn — it left one job accumulating multiple
`mutation.attempt` rows, which the control room rejected as a
continuing violation of Gate A's one-job/one-attempt rule). The failing
job's own single attempt keeps `observed_outcome='failed_clean'`
unchanged; the **job itself** transitions to the existing core job state
`cancelled` (never a new state) — `superseded_by_job_id` set,
`cancel_reason='cas_stale_bounded_replacement'`; the new job carries an
incremented `cas_retry_ordinal` (0→1→2→3), its own fresh fingerprints, its
own fresh idempotency key, a narrow fresh CAS pre-read of the pair's
current `available`/`updatedAt`, and a fresh read of the binding's
coalesced pending target (DEC-037 §4 row 1/§5.4 handoff C); on the 4th
mismatch (`cas_retry_ordinal=3`) → no replacement job is created, that
job instead transitions to the existing **non-terminal**
`blocked_manual_review` state (`binding_conflict`), which continues to
hold `operation_scope_key` until an authorized `action_recheck_inventory_pair`
release (persistent divergence, review case, never a further silent
retry). **`ITEM_NOT_STOCKED_AT_LOCATION` →
Revision 2 correction: this is a race/contract exception, not an inline
activation trigger.** It routes `failed_clean`, `error_class=
'inventory_location_missing'` (Revision 3 — the fixed vocabulary value;
also the `manual_review_subreason`), the non-terminal
`blocked_manual_review` state — this job **never** issues
`inventoryActivate` inline, in any form, from any code path
(static/AST-guarded, §5 tests below). The pending target stays coalesced
on the binding; the pair's `operation_scope_key` remains held and no new
job of any of the three inventory job types is admitted for it until an
authorized `action_recheck_inventory_pair` release (DEC-037 §5.5); only
then does the resulting fresh `inventory_push_sync` orchestration
dispatch re-read Shopify and, finding the level genuinely absent for a
`first_push_state='confirmed'` row, enqueue a separate `inventory_activate`
job (DEC-037 §5.2 step 8/§9). Ordinary validation
errors (`INVALID_*`, `NO_DUPLICATE_...`, `NON_MUTABLE_INVENTORY_ITEM`) →
`error_class='shopify_user_errors_validation'` (Revision 3 — the fixed
vocabulary value), `manual_review_subreason='binding_conflict'`.
`INVALID_QUANTITY_NEGATIVE` cannot occur (clamped before send).
`IDEMPOTENCY_CONCURRENT_REQUEST` → `observed_outcome='uncertain'`,
`error_class='concurrency_race_conflict'` (reconcile-first, never
auto-retried directly). `IDEMPOTENCY_KEY_PARAMETER_MISMATCH`
/ `IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED` → `idempotency_contract_violation`
(`blocked_manual_review`, no automatic retry — DEC-036 D6). `THROTTLED`
→ `uncertain`, `error_class='shopify_throttling_rate_limit'`,
reconcile-first, never `failed_clean` (DEC-036 D9). Network
timeout/HTTP 5xx → `uncertain`, `error_class='shopify_temporary_server_network'`.
No `error_class` value outside this fixed set (DEC-037 §7) is ever
produced by this module. `InventoryItem.tracked = false` → job
`skipped` with note via the `JobPolicySkip` dispatcher seam that Task
012 adds (sequencing guarantees it exists; the connector never mutates
`tracked`).

**Superseded text (2026-07-10 original, retained for history only — do
not implement as written):** ~~the `@idempotent` key lives on the
**binding** only (`last_push_idempotency_key`), paired with a
`last_push_params_hash`... At each dispatch attempt the handler compares
the current computed params-hash with the stored one: equal → reuse the
stored key verbatim... `CHANGE_FROM_QUANTITY_STALE` →
`concurrency_race_conflict` (auto-retry; the handler's params-hash
comparison yields the fresh CAS value and a new key on that attempt)~~
— this entire mechanism is replaced by the attempt-owned Layer 2 design
above; the binding never stores an idempotency key or a params hash.

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
these same methods (PD-2). **Gate B addition, Revision 2 (DEC-037
§5/§6):** first push never bypasses Layer 2 — the confirmation gate is
checked by `inventory_push_sync` at enqueue time, and both
`inventory_activate` (when needed) and `inventory_set_quantities` run
through the full C1/C2/NET/C3 wrapper as their own standalone mutation
jobs (never as two attempts inside one job); activation always requests
an explicit `available: 0` and its own reconciliation read must show
`applied` before a fresh orchestration dispatch is permitted to enqueue
the set-quantities job, so first push can never create an unreviewed
nonzero stock state.

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
mapped-pair verification when True — building on the **Task CORE-R1**
baseline that first makes the placeholder not-applicable-pass for
stores without the inventory domain (D-R1-2,
`task-core-r1-readiness-correction-packet.md` — ownership moved from
Area-6 D-A6-7, 2026-07-11); and (b)
**appends** one additional essential check via the `_get_checks()`
seam, active only when the domain is enabled: `write_inventory`
present in `granted_scopes`. `REQUIRED_MVP_SCOPES` is untouched by
this task; its TD-002 fix belongs to Task 014.

**D-013-6 — Job granularity & triggers [Gate B-corrected, Revision 2,
DEC-037 §5].** One `inventory_push_sync` **orchestration/read-only** job
per level-binding change (`res_model`/`res_id` → the binding row;
`operation_scope_key` = the frozen pair-serialization identity
`inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`,
DEC-037 §5.3 — serializes per pair across all three inventory job types,
not `inventory_push_sync` alone; `job_type = 'inventory_push_sync'`,
gated `inventory_domain_enabled`). This job performs the fresh Shopify
read and all gates and, per dispatch, enqueues **at most one** mutation
job — `inventory_activate` or `inventory_set_quantities` (DEC-037 §5.2)
— it never issues a Shopify mutation itself. Triggers shipped in-module:
(a) **odoo_event hook** — override
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
and per-mapping selective push (`manual_sync`). Reconciliation (accepted
backstop): the scan doubles as drift detection — before pushing, the
fresh read's `available` is compared with `last_pushed_available` and
current Odoo `free_qty`. **Gate B correction (DEC-037 §1 item C6,
supersedes "pushed over only after being logged as a drift note"
below): unexplained Shopify-side drift (differs from both last-pushed
and current Odoo, with no attributable cause) creates a review case and
BLOCKS the pending push for that pair** — it is never auto-pushed-over,
silently or otherwise; the operator resolves by confirming a fresh push
or acting in Odoo. A **known** local change (Odoo changed, Shopify
unchanged) is not drift and resumes normally. **Superseded text
(2026-07-10, do not implement):** ~~unexplained Shopify-side drift...
is pushed over only after being logged as a drift note (Odoo-SoT), so
drift is visible in logs while the standing direction is preserved~~.
**Coalescing (Gate B addition, Revision 2, mechanics corrected Revision
3, DEC-037 §10):** one pending-update target (`pending_target_available`)
per (item, location) pair, held on the binding row; `operation_scope_key =
inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`
(DEC-037 §5.3) serializes concurrent inventory jobs for the same pair
across all three job types; while any inventory job for that pair is
non-terminal (orchestration, activation, set-quantities, **or a job
blocked in `blocked_manual_review`, which is not terminal for this
purpose, DEC-037 §5.5**), no new pair job is admitted and no second
mutation attempt is created for the pair — a bounded CAS-stale or
reconciliation `not_applied` retry is a **new, separate job**, created
atomically in the same transaction that terminalizes the job it
replaces (DEC-037 §5.4 handoffs C/D), never a second attempt on the
still-non-terminal job. The next `inventory_push_sync` dispatch, once
admitted, reads the latest coalesced `pending_target_available` rather
than a possibly-stale value. Throughput note: per-pair jobs at batch
20/5 min are an accepted MVP simplification; multi-entry batching is
explicitly **out of scope for Wave 3 MVP** (DEC-036 D4) — a future
separately-gated optimization, not a release-hardening detail to
assume.

**D-013-7 — Concurrency.** CAS + mandatory `@idempotent` +
`operation_scope_key` collectively make the push race-safe **at the
API layer**; the local claim/dispatch caveat (ARCH §5.12) still
applies and is restated in the prompt.

**D-013-8 — Baseline import split out (revised 2026-07-11).** The
one-time reviewed Shopify→Odoo baseline import (accepted as an
allowed exception, DEC-010) is **not** in Task 013 (scope control:
its own preview/apply flow and its own Odoo stock write surface) —
but it is **no longer an unnamed candidate**: it is fully planned as
**Task 013B** (`task-013b-initial-inventory-baseline-packet.md`,
locked packet, sequenced after this task and before final
UAT/release), per the PR #148 review item 3. The accepted DEC-003
scope is completed, not narrowed.

**D-013-9 — Layer 2 integration [Gate B, Revision 2, 2026-07-19, DEC-037
§4/§5/§7/§9 — supersedes Revision 1's same-job design].** Every Shopify
mutation this module issues passes through the Stage 0 Layer 2 wrapper —
no direct API-client mutation call exists anywhere in
`shopify_connector_inventory` (enforced by the repo-wide AST guard,
DEC-036 D16/D37, and the API-client runtime guard). Three distinct job
types are registered via `_inherit`+`super()` on
`shopify_connector_job_dispatch.py`'s `_get_replay_policies()` and, for
the two mutation job types, `_get_reconciliation_strategies()` seams:

- `inventory_push_sync` — orchestration/read-only, `remote_read_replay_safe`,
  never registered in the mutation-domain registry, issues no Shopify
  mutation, enqueues at most one mutation job per dispatch (DEC-037 §5).
- `inventory_set_quantities` — its **own standalone mutation job**
  (`job_type == mutation_domain`), the `inventorySetQuantities` push,
  exact contract in DEC-037 §4 row 1.
- `inventory_activate` — its **own standalone mutation job**
  (`job_type == mutation_domain`), the `inventoryActivate` call, enqueued
  only by a fresh `inventory_push_sync` dispatch that finds no existing
  level for a confirmed row, exact contract in DEC-037 §4 row 2. **Never
  combined with the set-quantities job** — own job record, own
  `attempt_token`, own idempotency key, own fingerprints; the handoff
  from activation to a set-quantities push always passes back through a
  fresh `inventory_push_sync` orchestration dispatch, created **atomically**
  in the same transaction that terminalizes the activation job
  (DEC-037 §5.2 step 7/§5.4 handoff B — Revision 3: this does not wait
  for a later scan or manual trigger) — it is never enqueued directly by
  the activation job.

**Pair serialization and atomic handoffs:** all three job types share one
`operation_scope_key` per pair (the frozen literal, DEC-037 §5.3); only
one of the three may be non-terminal for a given pair at a time — **a
job in `blocked_manual_review` is not terminal for this purpose and
continues to hold the pair (DEC-037 §5.5)**; handoff between phases,
including a bounded CAS-stale/`not_applied` replacement job's creation,
is atomic with the prior job's terminalization, under a row lock on the
binding (DEC-037 §5.4, four named handoffs A–D) — implementation must
include the named genuine concurrency test proving duplicate phase jobs
cannot be created. A blocked pair is released **only** by the new
`action_recheck_inventory_pair(reason)` domain action (Reviewer/Admin
only, DEC-037 §5.5) — never by a generic core manual-retry/manual-review
action.

**Job-lineage fields:** `cas_retry_ordinal` (Integer, default 0,
`inventory_set_quantities` only) is the **only new, domain-owned** field
this task introduces. `superseded_by_job_id` (Many2one, nullable) and
`cancel_reason` (Char, nullable, fixed vocabulary — DEC-037 §5.4/§5.5)
are **existing core** `shopify.connector.job` fields, reused here, not
new domain schema. None of the three adds a new core job state.

**Consequence contract:** every mutation outcome this module's Layer 2
wrapper reports must resolve to one of the rows in DEC-037 §9
(`observed_outcome`/`error_class`/`manual_review_subreason`/retry
eligibility/reconciliation requirement/next orchestration behavior) —
unknown or malformed consequence data must never default to automatic
retry; it routes fail-closed to `uncertain`/manual review. Every
`error_class` value is one of the fixed set in DEC-037 §7/§9
(`shopify_user_errors_validation`, `inventory_location_missing`,
`concurrency_race_conflict`, `shopify_throttling_rate_limit`,
`shopify_temporary_server_network`, `data_shape_schema_mismatch`,
`idempotency_contract_violation`, `no_reconciliation_strategy`,
`store_identity_mismatch`) — no other value is authorized. No domain code
writes job state outside the accepted Layer 2 consequence interface.

Frozen job contract (job_type/job_source/error-class/manual-review-subreason/
pair-serialization-identity/domain-enable-flag vocabulary, job-lineage
fields, `action_recheck_inventory_pair`): DEC-037 §7 — this module must
not invent additional values without a further Gate decision.
`shopify.connector.mutation.attempt` (core, Stage 0) is the sole holder
of the Shopify idempotency key and both fingerprints for every
push/activation attempt; the binding's `last_pushed_available`/
`last_pushed_at`/`last_known_shopify_available`/`pending_target_available`
are informational/coalescing only (D-013-1(b), D-013-3, DEC-037 §10).

## 3. Gate criteria (inventory domain, 15-pattern)

1 Task 010 runtime-green ✅ **and Task 010B merged (added 2026-07-11
— per-pair level bindings need the complete variant set to cover an
ordinary catalog)**; 2 naming portion accepted (=D-013-1);
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

Job-type → domain-flag map (red-team-added, exhaustive; **Revision 2,
DEC-037 §7 adds the two mutation job types**): all six job types this
module registers (`inventory_push_sync`, `inventory_push_scan`,
`inventory_first_push_preview`, `inventory_location_sync`,
`inventory_activate`, `inventory_set_quantities`) map to
`inventory_domain_enabled` via `_domain_flag_for_job_type()`. Of these,
only `inventory_activate` and `inventory_set_quantities` are mutation job
types (`job_type == mutation_domain`, registered in the reconciliation-
strategy registry); the other four are Layer 1 read/orchestration/scan
job types and carry no `mutation_domain`. Logging: all free text this module
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
`test_inventory_push_mechanics.py` (CAS value threading using a fresh
pre-attempt read, never the binding's informational field; idempotency
key persisted on `mutation.attempt` only, never on the binding;
same-attempt retry reuse vs. regenerated-on-CAS-refresh; 3-replacement
CAS-stale bounded sequence (`cas_retry_ordinal` 0→1→2→3) creates **four
distinct job records — never a redispatch of any prior one** — each with
its own job ID/`attempt_token`/idempotency key, connected only by
`superseded_by_job_id`, then `blocked_manual_review`/`binding_conflict`
on the 4th mismatch with no replacement job created [Gate B, Revision 3,
DEC-037 §4 row 1/§5.4 handoff C — corrects Revision 2's now-withdrawn
same-job-redispatch design]; **`inventory_activate` and
`inventory_set_quantities` are two distinct job records (`job_type`, job
ID, `attempt_token`, idempotency key each), never two attempts inside
one job — a static/AST guard asserts the `inventory_set_quantities`
handler contains no `inventoryActivate` call site, and vice versa**
[Gate B, Revision 2, DEC-037 §5]; the activation-to-set handoff always
passes through a fresh `inventory_push_sync` orchestration dispatch,
created **atomically** in the same transaction that terminalizes the
activation job, never a direct enqueue and never dependent on a later
scan/manual trigger [Gate B, Revision 3, DEC-037 §5.2/§5.4 handoff B];
`job_type == mutation_domain` invariant test for both mutation job types
[Gate B, Revision 2, DEC-037 §7]; activation always sends explicit
`available: 0` [Gate B, DEC-037 §4 row 2]; **no code path matches on
`UserError.message` text for `inventoryActivate` classification**
(static/AST guard) [Gate B, Revision 2, DEC-037 §4 row 2]; a reconciliation
`not_applied` verdict (either domain) creates a **new** same-domain job,
never redispatches the resolved one [Gate B, Revision 3, DEC-037 §4
rows 1–2/§5.4 handoff D]; a `blocked_manual_review` job creates no
automatic child job, and `action_recheck_inventory_pair` is the only
path that releases one, requiring an authorized reason and creating
exactly one fresh `inventory_push_sync` job [Gate B, Revision 3, DEC-037
§5.5]; `THROTTLED`/both idempotency-defect codes classified per DEC-036
D6/D9; **every `error_class` value observed anywhere in this module's
tests is one of the fixed set in DEC-037 §7/§9 — a static/AST guard
asserts none of `remote_validation_rejected`/`remote_precondition_mismatch`/
`transport_ambiguous`/`clean_rejection` (Revision 2, withdrawn) appears
in the module** [Gate B, Revision 3]; reconciliation-verdict tests
(applied/not-applied/inconclusive) for both mutation domains **including
an induced ABA/freshness fixture (value changes away and back with a
later `updatedAt`) asserting `inconclusive`, never `not_applied`, and
asserting the `applied` verdict never depends on `updatedAt`** [Gate B,
Revision 3, DEC-037 §4 row 1]; **genuine independent-PostgreSQL-
connection concurrency test proving two concurrent transactions cannot
both create the next phase job (including a CAS/`not_applied`
replacement job) for the same pair** [Gate B, Revision 3, DEC-037
§5.3/§5.4]; store-identity-mismatch routing; clamp-to-0;
tracked-false skip; reason/referenceDocumentUri; **source-level guard:
the string `committed` never appears as a quantity name, and only
`inventorySetQuantities`/`inventoryActivate` mutations exist in the
module** — no `inventoryAdjustQuantities`, keeping set-semantics
only; no call site constructs a `quantities[]` array with length > 1
[Gate B, DEC-036 D4]); `test_inventory_triggers.py` (move-done hook enqueues correct
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

**Lifecycle (LC-1) adoption (re-review `4945129824` item 7):**
`inventory_push_sync` / `inventory_first_push_preview` register their
`selection_add` `ondelete` with the LC-1 callable
`_reassign_to_historic_job_type` from the start (LC-1 precedes Task 012
— DEC-030 / lifecycle §7), so no later retrofit is needed.
**SEC-1 override seam (item 6):** `shopify.connector.location.mapping`
declares `_odoo_binding_field_name()` returning `odoo_location_id`;
`shopify.connector.inventory.level.binding` is non-overridable
(composite identity — mixin default `False`).

## 8. Locked final implementation prompt (Task 013)

> **SUPERSEDED (Gate B, 2026-07-19).** This inline prompt predates the
> Layer 2 correction (it still describes the binding-owned idempotency
> key/params-hash design D-013-3 retired above) and must **not** be used.
> The current locked prompt is
> [`../06-prompts/sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md)
> (`ISSUED-NOT-EXECUTED: NO`, `LOCKED: YES`). The text below is retained
> verbatim for history only.

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

## Fable gap-closure addendum (2026-07-16) — Layer 2 dependency + operating-model closures [Proposed]

> Appended by the Fable gap-closure mission, 2026-07-16. Additive only —
> nothing above is rewritten; D-013-1..8 remain intact as written.
> **Packet re-acceptance is required with this addendum.** Gate context:
> [`wave-3-definition-of-ready.md`](wave-3-definition-of-ready.md).

### A.1 Layer 2 dependency — now designed and accepted [Gate B update, 2026-07-19]

The DEC-031 Layer 2 (durable mutation-safety) dependency this packet's
domain triggers is now **ACCEPTED — CONTROL-ROOM GATE A**:
[`DEC-036`](../04-decisions/DEC-036-wave-3-layer-2-gate.md) (the complete
D1–D38 decision set), with the narrative design in
[`../03-architecture/dec-031-layer-2-mutation-safety-design.md`](../03-architecture/dec-031-layer-2-mutation-safety-design.md).
Wave 3 delivers it as **Stage 0** (attempt records + reconciliation
framework + sweep cron, in core, with its own allowed files and
runtime/concurrency proof) before any Task 013 mutation merges, is
enabled, or is live-validated. Task 013's push handler runs inside the
Stage 0 attempt wrapper: attempt intent persisted pre-network; uncertain
outcomes resolved by a reconciliation read (applied / not-applied /
inconclusive) before any retry. **D-013-3's key-reuse mechanics are now
fully superseded, not merely refined, by the accepted Layer 2 design** —
the idempotency key and both fingerprints are attempt-owned on
`shopify.connector.mutation.attempt`, never binding-owned (DEC-036 D6;
DEC-037 §1 item C5). The domain-specific application of DEC-036 to this
module's two mutations (`inventorySetQuantities`/`inventoryActivate`) is
fully specified in
[`DEC-037`](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) §4/§5 and
D-013-9 above.

### A.2 Inventory-operating-model closures folded in

Per [`../02-product/inventory-operating-model.md`](../02-product/inventory-operating-model.md)
(Proposed PDs 1–12):

- **Quantity source** — confirmed as this packet's D-013-2: per-mapped-
  location `free_qty` with location context; `on_hand`/`committed` read
  only for preview/divergence context, never written.
- **Coalescing — last-value-wins**: one pending-update target per
  (item, location) pair; new stock events overwrite the pending target;
  push consumes only the latest absolute value (bounds backlog by pair
  count). Extends D-013-6's delta-scan posture; one-pair-per-job remains
  the conservative floor, multi-entry batching is an accepted refinement
  candidate with per-entry `userErrors` routing.
- **CAS via `changeFromQuantity` [Gate B-corrected, 2026-07-19 — the
  naming conflict below is resolved, not open].** The operating model's
  read→compare→set flow with bounded retries (**3**, now binding — Gate
  B closes the "proposed" hedge, DEC-037 §1 item C7), each retry a
  **new, separate job** (Revision 3, DEC-037 §5.4 handoff C — never a
  redispatch of the job whose attempt failed), and never
  `ignoreCompareQuantity`, which does not exist as a current input field.
  **Superseded text (retained for history only):** ~~D-013-3 above
  records the 2026-07 CAS shape as `changeFromQuantity`
  ("compareQuantity … no longer exist"); the 2026-07-16 captures record
  `compareQuantity` as current. This is a direct evidence conflict —
  re-verify the live 2026-07 schema at Stage 1 packet re-acceptance...
  (hard-stop 2 applies if unresolved)~~ — this conflict is **resolved**:
  Gate A's official-source refresh
  ([`shopify-layer2-mutation-safety-refresh-2026-07-18.md`](../00-source-materials/shopify-layer2-mutation-safety-refresh-2026-07-18.md)
  §1) confirms `changeFromQuantity` is the sole current (2026-07) input
  field, with four independent official citations and no conflict
  between official Shopify sources — the only conflict was this
  project's own stale internal documents (the 2026-07-16 capture's
  `compareQuantity` reading), now corrected everywhere current-facing.
  Persistent divergence after 3 bounded retries → review case
  (`blocked_manual_review`/`binding_conflict`), never a further silent
  retry.
- **Mandatory `@idempotent` keys** — unchanged from D-013-3, tightened by
  the Layer-2 attempt contract: one UUID per attempt, persisted on the
  attempt record before the call; 24h replay window; >24h → reconciliation,
  never key replay.
- **Clamp + warn negatives** — D-013-2's clamp-to-0 stands, now with a
  mandatory divergence warning carrying the true negative value
  (push-negative remains an unverified, unoffered option).
- **Divergence review [Gate B-resolved, 2026-07-19]** — Shopify→Odoo
  stays read/verify only (RA-020); every divergence yields a review case
  with the three values (Shopify current / last-pushed / Odoo current);
  **the D-013-6 log-then-push-over drift posture is retired and replaced
  by review-case-first for unexplained drift, binding, not merely
  flagged** (DEC-037 §1 item C6) — the pending push blocks until the case
  clears; a known local Odoo-only change is not drift and is unaffected.
- **Reconnect** — reconciliation read of all mapped levels precedes the
  first post-reconnect push (PD-RB inventory slice); no stored
  pre-disconnect mutation replays blind; the store-identity check
  (DEC-036 D18) is the first step of that reconciliation read
  (DEC-037 §10).

### A.3 Re-acceptance

This addendum, together with the Gate B corrections above (D-013-9 and
the superseded-text markers throughout §2, now at Revision 3 per
DEC-037 — the one-job/one-attempt-lifetime job model, the atomic
handoff contract, the review-release action, and the fixed error
vocabulary), is the current `GATE B ACCEPTANCE CANDIDATE` — **NOT
IMPLEMENTATION AUTHORIZED**. Task
013 implementation requires both: (1) this Gate B package accepted and
merged, and (2) Stage 0 merged and runtime-proven and providing the
correction prerequisites DEC-037 §13A now records (per PR #177 comment
`5015174971`'s sequencing guard). The §8 inline prompt remains superseded
and unusable; the current locked prompt is
[`../06-prompts/sol-wave-3-task-013-locked-prompt.md`](../06-prompts/sol-wave-3-task-013-locked-prompt.md),
itself `LOCKED`/`ISSUED-NOT-EXECUTED: NO`. **Task 013B was checked
against the operating model and no contradiction was found**
(preview/confirm, drift-abort, and row-lock closures align with PDs
3–7); it requires the same two-part authorization (Gate B + Stage 0) and
carries its own explicit Layer-2-non-applicability statement (Gate B,
new §0 of its packet, DEC-037 §8).
