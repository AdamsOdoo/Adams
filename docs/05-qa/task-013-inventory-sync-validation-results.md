# Task 013 — Inventory Synchronization: Implementation Validation Results

- **Status: CORRECTED IMPLEMENTATION CANDIDATE FROZEN FOR INDEPENDENT
  REVIEW — NOT RUNTIME-PROVEN. Draft PR unmerged, not marked ready.**
- **Repository:** `AdamsOdoo/Adams`
- **Branch:** `claude/wave-3-task-013-2g0ul0`
- **Draft PR:** [#182](https://github.com/AdamsOdoo/Adams/pull/182) →
  `mvp/program-integration`
- **Exact base SHA:** `mvp/program-integration` @
  `8f5f421e2110c2e805460ea75fb519e48013e0f7` (PR #181's merge commit)
- **This is the second correction cycle on the same draft PR.** The first
  cycle (head `eb85ea43e73df2a0e1c1667b687f838f31058f81`) responded to PR
  #182 comments
  [`5025765389`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5025765389)
  (REVISE) and its addendum
  [`5025803697`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5025803697).
  **This cycle** responds to the control-room re-review at
  [`5028910116`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5028910116)
  ("REVISE — NOT ACCEPTED FOR ODOO.SH, DEV-STORE, EXTERNAL-CONCURRENCY,
  READY-FOR-REVIEW, OR MERGE"), which found 13 remaining implementation
  defects in the corrected code and required one further pre-runtime
  correction batch plus a full same-pattern audit before the next
  freeze. Both prior amendments (`inventory_mutation_reconcile`, the
  fail-closed integral-quantity rule) are **accepted in principle** by
  this review and were **not** reopened.
- **Implementation worker for this correction cycle:** Claude Code —
  the explicit Task 013/PR #182-only exception is re-affirmed by comment
  `5028910116`'s own framing ("Do not stop again on this point" from the
  first cycle's ruling still applies). This does not change Claude's
  default role for later tasks and does not authorize self-acceptance or
  self-merge.
- **Acceptance authority:** ChatGPT (product-owner control room). This
  session did not accept its own work, did not mark the PR ready, and did
  not merge.
- **Commits this cycle:** `3706d19c021cfdf60e037a5d11882453c0d0c12c`
  (model corrections) and `76aaf4d8ce61715c535e77b7093ac9bde0be4a30`
  (test corrections), on top of the seven commits already on the branch
  from the identity-gate-verified starting head
  `eb85ea43e73df2a0e1c1667b687f838f31058f81`.

## 1. Implemented scope (as corrected this cycle)

`addons/shopify_connector_inventory` (Full edition, LGPL-3; depends
`shopify_connector_core`, `shopify_connector_product`, `stock`). Only
`models/shopify_connector_inventory_service.py` and the six test files
changed this cycle — every other module file (`__init__.py`,
`__manifest__.py`, `shopify_connector_inventory_level_binding.py`,
`shopify_connector_location_mapping.py`, `shopify_connector_store_settings.py`,
`ir.model.access.csv`, `shopify_connector_inventory_cron.xml`) is
byte-identical to the prior cycle's frozen candidate; no governing
document was touched (none was authorized or required this cycle).

Corrected this cycle, all in `shopify_connector_inventory_service.py`
(full detail in §2):

- Missing-InventoryItem identity now fails closed through the existing
  `binding_conflict` review route in the orchestration handler, the
  set-quantities pre-C2 precondition read, and both mutation domains'
  reconciliation reads — never treated as an absent InventoryLevel and
  never routed to activation.
- `shopify.connector.inventory.level.binding.shopify_gid` now always
  holds the real Shopify InventoryLevel GID, captured from the pair
  read, activation direct-success evidence, activation reconciliation,
  the set-quantities pre-C2 read, and set-quantities reconciliation — a
  synthetic `<item_gid>:<location_gid>` composite is never constructed
  anywhere in the module again (source-level guard confirms this). A
  conflicting already-recorded GID fails closed pre-C2, or flags the
  binding `status='review'` when observed only after an already-terminal
  success.
- The pre-C2 fail-closed helper (`_fail_closed_pre_c2`) no longer writes
  to the job or commits — it only raises a new domain-owned
  `InventoryPreC2FailClosedError`. The domain's own blocked disposition
  is now written and committed exclusively by an inherited
  `_recover_pre_c2_failure` override on the job-dispatch abstract model,
  which runs only after core's own rollback/reset (LL-005 compliant, §4
  below).
- Shopify-returned quantity evidence (`available`, `changeFromQuantity`,
  `quantityAfterChange`, activation `available`) is now validated by a
  new `_strict_shopify_int` helper that accepts only a genuine, non-bool
  Python `int` — `int(...)` is never used as a permissive coercion on
  transport-returned data anywhere in the module. Set-quantities success
  additionally requires exactly one `available` change (never a
  duplicate or an extra quantity-name change) and an exact match on the
  requested `reason`/`referenceDocumentUri`; a response carrying both
  `userErrors` and a non-null adjustment group is classified `uncertain`/
  `data_shape_schema_mismatch`, never a clean rejection.
- The scheduled push-scan handler now distinguishes "never successfully
  pushed" (`last_pushed_at` unset) from "successfully pushed a confirmed
  zero" — a never-pushed pair is always admitted to orchestration, even
  at a zero target.
- The shared `inventory_mutation_reconcile` job's durable identity now
  includes the store and mutation domain
  (`reconcile:{store}:{mutation_domain}:{attempt_token}`), via an
  inherited `_ensure_reconciliation_job` override scoped to the two
  inventory mutation domains only; every non-inventory domain is
  unchanged.
- `_handoff_supersede` no longer accepts a caller-supplied
  `cas_retry_ordinal` — the parameter does not exist on its signature.
  For a CAS replacement (`is_cas_replacement=True`), the ordinal is
  always derived from a freshly row-locked read of the exact predecessor
  job; every other handoff (reconciliation-not-applied, manual-review
  release) always creates its replacement at ordinal 0, regardless of
  the predecessor's own ordinal. The prior cycle's disclosed procedural
  limitation is resolved (§5).
- CAS-exhaustion review-release eligibility now additionally requires
  the final attempt's persisted, sanitized `user_error_codes` evidence
  to actually contain `CHANGE_FROM_QUANTITY_STALE` — ordinal 3 alone is
  no longer sufficient.
- `_handle_inventory_mutation_reconcile` now separates execution of the
  reconciliation read from validation of its returned structure into two
  distinct `try`/`except` blocks (LL-013): a `JobHandlerError`, a
  genuine PostgreSQL concurrency failure, or any other transient
  read-execution exception now retries through the ordinary read-safe
  job path; only a result the strategy actually returns, but that fails
  schema validation, blocks the original job. The same PG-concurrency
  re-raise correction was applied to the orchestration read wrapper and
  the reconciliation handler's final atomic-apply block (same-pattern
  audit finding, §2 item 14).
- `_handle_inventory_location_sync` now validates the complete GraphQL
  response/connection/pagination shape through a new
  `_validate_locations_response` helper — a malformed or partial page
  now raises `JobHandlerError(data_shape_schema_mismatch)` and follows
  the ordinary read-safe retry path, never silently succeeding as an
  empty store.
- The review-release reason is now passed through the binding mixin's
  PII-safe `_audit_safe_reason` helper (already used by
  `action_override_binding`), not the secret-only `redact()`.
- Both `_handle_inventory_push_sync` orchestration→mutation handoff
  branches (DEC-037 §5.4 handoff A) now acquire the binding's row lock
  before terminalizing the orchestration job and creating the child; all
  handoff logs (A–D and manual-review release) now record both
  `predecessor_job_id` and `successor_job_id`.
- `enqueue_first_push_preview`/`enqueue_location_sync` are now private
  (`_enqueue_first_push_preview`/`_enqueue_location_sync`) and require
  explicit Operator/Administrator authority.
  `create_or_update_location_mapping` no longer silently replaces an
  existing mapping's Shopify GID or silently moves an already-mapped GID
  to a different Odoo location — either case now fails closed with a
  clear `UserError`.

## 2. Correction batch applied this cycle — full audit trail

Every item traces to PR #182 comment
[`5028910116`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5028910116),
numbered as in that comment, except item 14, a same-pattern-audit finding
beyond the 13 named items.

1. **Missing InventoryItem never routed to activation.**
   `_handle_inventory_push_sync` previously checked only `tracked is
   False`, so `item_exists=False` (`tracked=None`) fell through to the
   `not read['level_exists']` branch and enqueued `inventory_activate`.
   Fixed by adding an explicit `not read['item_exists']` check —
   routed to `blocked_manual_review`/`binding_conflict` — before the
   `tracked`/`level_exists` checks, in the orchestration handler, the
   set-quantities pre-C2 precondition read, and both mutation domains'
   reconciliation reads.
2. **Real InventoryLevel GID identity.** The read query already
   requested InventoryLevel `id`, but `_read_shopify_inventory_pair`
   never extracted or returned it. Added `inventory_level_gid` to the
   returned structure (validated non-empty when a level exists);
   persisted from the pair read (pre-C2, opportunistic capture),
   activation direct-success evidence, activation reconciliation, and
   set-quantities reconciliation. The synthetic
   `'%s:%s' % (item_gid, location_gid)` fallback is removed from both
   `_apply_consequence_set_quantities` and `_apply_consequence_activate`
   (confirmed absent by a static guard). A conflicting already-recorded
   GID fails closed pre-C2 (no commit has occurred yet) or is flagged
   `status='review'` post-success (the mutation itself already
   succeeded and the job is already terminal, so the disposition itself
   cannot block).
3. **Pre-C2 fail-closed helper no longer commits.** `_fail_closed_pre_c2`
   previously called `self.env.cr.commit()` directly inside a domain
   `prepare_preconditions` path — a `TransactionCase` test calling
   `_prepare_preconditions_set_quantities` directly would execute that
   commit-bearing path (LL-005). Replaced with a domain-owned
   `InventoryPreC2FailClosedError` (carrying `error_class`/`subreason`/
   `message`) that is raised, never written or committed. A new
   `ShopifyConnectorJobDispatchInventoryExtension._recover_pre_c2_failure`
   override (an inherited dispatcher recovery seam, no core-file edit)
   applies the domain's blocked disposition only for this exception
   type, after replicating core's own rollback/reset/re-lock sequence;
   every other exception delegates unchanged to `super()`. Full detail
   §4.
4. **Strict integer evidence.** Replaced every permissive `int(...)`
   coercion of transport-returned quantity data with a new
   `_strict_shopify_int(value)` helper (rejects `bool`, float, numeric
   string, `None`) in `_read_shopify_inventory_pair` (`available`),
   `_is_valid_set_quantities_success` (`quantityAfterChange`), and
   `_is_valid_activate_success` (activation `available`).
   `_is_valid_set_quantities_success` also now requires exactly one
   `changes` entry named `available` (rejecting duplicates/extra
   quantity-name changes) and an exact match on the requested
   `reason`/`referenceDocumentUri`. `_classify_direct_set_quantities`
   now classifies a response carrying both `userErrors` and a non-null
   adjustment group as `uncertain`/`data_shape_schema_mismatch`, never a
   clean rejection. Sanitized `user_error_codes` (never raw message
   text) are now persisted in evidence whenever `userErrors` is
   non-empty.
5. **Never-pushed-zero scan admission.** `_handle_inventory_push_scan`
   previously skipped whenever `target == last_pushed_available`, and
   the Float field defaults to `0.0` — so a confirmed, never-pushed pair
   with a zero target was skipped forever. Fixed by additionally
   checking `last_pushed_at`: a never-pushed pair (`last_pushed_at`
   unset) is always admitted regardless of target value; only a pair
   with a recorded prior push and an unchanged target is skipped.
6. **Shared reconciliation identity includes the mutation domain.** A
   new `_ensure_reconciliation_job` override on
   `ShopifyConnectorJobDispatchInventoryExtension`, scoped to
   `inventory_activate`/`inventory_set_quantities` only, builds
   `payload_hash='reconcile:{store_id}:{mutation_domain}:{attempt_token}'`
   instead of core's bare `'reconcile:{attempt_token}'` — every
   non-inventory domain still delegates to `super()` unchanged.
7. **CAS ordinal lineage — no arbitrary jump, no non-CAS inheritance.**
   `_handoff_supersede`'s signature no longer has a `cas_retry_ordinal`
   parameter at all (replaced by a boolean `is_cas_replacement`). When
   `True`, the method row-locks the exact predecessor job itself and
   derives `cas_retry_ordinal = locked_job.cas_retry_ordinal + 1`
   in-place, rejecting the call with `ValidationError` if the
   predecessor is not an `inventory_set_quantities` job already below
   the bounded ceiling. Every other handoff always passes
   `is_cas_replacement=False` (the default), so the replacement is
   always created at ordinal 0 — never inheriting a nonzero predecessor
   ordinal. This resolves the prior cycle's disclosed procedural
   limitation (§5).
8. **CAS-exhaustion release requires the stale-code evidence.**
   `_recheck_inventory_pair`'s CAS-exhaustion eligibility branch now
   also reads the blocked job's mutation attempt's persisted
   `remote_evidence_refs['direct']['user_error_codes']` and requires
   `'CHANGE_FROM_QUANTITY_STALE'` to be present, in addition to
   `cas_retry_ordinal == 3` — an ordinal-3 job whose final attempt never
   actually recorded the stale code is no longer eligible.
9. **Reconciliation exception ordering (LL-013).**
   `_handle_inventory_mutation_reconcile` previously wrapped both
   `strategy['reconcile'](attempt)` and
   `Dispatch._validate_reconciliation_result(result)` in one broad
   `except Exception`, misclassifying a transient read failure as
   malformed evidence and blocking the original job. Split into two
   `try`/`except` blocks: the read-execution block re-raises
   `JobHandlerError` and `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` unchanged,
   and wraps any other exception as `JobHandlerError(
   shopify_temporary_server_network, ...)` for the ordinary retry path;
   only the separate result-validation block's failure blocks the
   original job as `data_shape_schema_mismatch`.
10. **Location-sync response/pagination-shape validation.** A new
    `_validate_locations_response(result)` helper requires `data`,
    `locations`, `edges` (list), `pageInfo` (dict), `hasNextPage`
    (bool), each edge/node shape, and a non-empty string GID, raising
    `JobHandlerError(data_shape_schema_mismatch)` on any defect —
    including a missing/malformed page cursor when `hasNextPage` is
    true. `_handle_inventory_location_sync` now routes every page
    through this validator instead of defaulting absent
    `data`/`locations`/`edges` to empty structures. The inaccurate "sole
    sudo() site" docstring wording is also corrected — the module has
    several other narrow, named `sudo()` elevations.
11. **PII-safe review-reason redaction.** `_recheck_inventory_pair` now
    calls `locked_binding._audit_safe_reason(reason)` (the binding
    mixin's existing secrets-plus-PII helper, already used by
    `action_override_binding`) instead of the secret-only `redact()` —
    email addresses and phone numbers are now redacted from the
    `_logger.info` release-audit line, not just credentials/tokens.
12. **Orchestration handoff row lock + complete lineage logging.** Both
    `_handle_inventory_push_sync` handoff-A branches (activation-required
    and set-quantities) now call `binding.try_lock_for_update()` before
    writing `state='succeeded'` on the orchestration job and creating
    the child — never terminalizing before the lock is confirmed held.
    Every handoff log entry (A, both branches; B via
    `_handoff_succeed_to_fresh_orchestration`; C/D via
    `_handoff_supersede`; manual-review release, which reuses
    `_handoff_supersede`) now includes both `predecessor_job_id=` and
    `successor_job_id=` in its message text.
13. **Backend admission hardening.** `enqueue_first_push_preview`/
    `enqueue_location_sync` are renamed to
    `_enqueue_first_push_preview`/`_enqueue_location_sync` and now
    require explicit Operator/Administrator group membership (mirroring
    the two sibling sanctioned services). `create_or_update_location_mapping`
    now rejects (rather than silently applying) a differing Shopify GID
    for an already-mapped Odoo location, and a differing Odoo location
    for an already-mapped Shopify GID — both fail closed with a
    `UserError` directing the caller to the reviewed binding-override
    path; only non-identity controls (`push_enabled`) may still be
    updated on an exact-identity match.
14. **[Same-pattern audit finding, not one of the 13 named items]
    PG-concurrency exception masking in two additional broad-catch
    sites.** Beyond the reconciliation-handler fix required by item 9,
    the same masking risk existed in `_handle_inventory_push_sync`'s
    own read wrapper and in `_handle_inventory_mutation_reconcile`'s
    final atomic-apply `except Exception` block: wrapping a genuine
    PostgreSQL concurrency failure into `JobHandlerError` would route it
    through `_invoke_handler`'s `except JobHandlerError` branch (which
    performs an ORM write) instead of its dedicated
    `except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY: raise` branch — exactly
    the "write inside an already-aborted transaction" hazard core's own
    comment at that call site warns against. Both sites now re-raise
    `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` unchanged before the generic
    `except Exception` fallback.

## 3. Same-pattern audit — findings and disposition

A full re-scan of `addons/shopify_connector_inventory/**` for every
pattern listed in comment `5028910116`'s own checklist, beyond the 13
named items:

| Pattern | Finding |
| --- | --- |
| Missing remote identity treated as absent child resource | Item 1 above; no other occurrence found. |
| Synthetic GIDs | Item 2 above; no other synthetic-identity construction found. |
| Response coercion | Item 4 above (quantities); the transport-layer catch-all in `_transport_set_quantities`/`_transport_activate` is an intentional, unchanged, already-accepted DEC-037 pattern (any transport-shape exception becomes `uncertain`/reconcile, never trusted) — not a coercion defect. |
| Response data plus errors | Item 4 above (set-quantities ambiguous case); `_classify_direct_activate`'s existing ambiguous-shape fallback (userErrors alongside a non-null level) was already correct and unchanged. |
| Direct commits in domain callbacks | Item 3 above; confirmed by AST guard that no `self.env.cr.commit` appears in `_fail_closed_pre_c2`, `_prepare_preconditions_set_quantities`, or `_prepare_preconditions_activate`. |
| TransactionCase commit masking | Item 3 above; new tests prove `job.state` is unchanged after a direct `prepare_preconditions` call (no commit occurs), separate from the durable genuine-connection recovery-seam proof. |
| Missing pair locks | Item 12 above; `_apply_consequence_set_quantities`/`_apply_consequence_activate` already locked via `_lock_binding_for_pair` (unchanged, correct); the missing lock was specifically the two orchestration handoff-A branches. |
| Omitted successor IDs in logs | Item 12 above; all handoffs now log both IDs. |
| Broad exception swallowing | Items 9 and 14 above; no other broad `except Exception` site found that could route a PG-concurrency exception through an ORM-writing branch. |
| Default-empty false success | Item 10 above; no other default-empty pattern found. |
| First-run values confused with successful-zero values | Item 5 above; no other occurrence. |
| Shared-job identity missing mutation domain | Item 6 above; the only shared-identity job type in this module. |
| Arbitrary protected lineage values | Item 7 above; `cas_retry_ordinal` is the only domain-owned lineage field. |
| Release eligibility inferred without structured evidence | Item 8 above; the other two eligibility branches (`inventory_location_missing`, ordinary `shopify_user_errors_validation`) do not depend on a specific structured code and were already correct. |
| Secret-only redaction where PII redaction is required | Item 11 above; the only free-text user input logged anywhere in the module is the release reason. |
| Public-named service methods lacking authorization | Item 13 above; `create_or_update_location_mapping`/`ensure_inventory_level_binding` already required Operator/Administrator authority from the prior cycle and were unaffected. |

No known implementation limitation remains from this audit, except the
already-declared external evidence classes in §9–§12 that genuinely
require a later environment.

## 4. The pre-C2 fail-closed seam — corrected, non-committing design

Comment `5028910116` item 3 found that the prior cycle's
`_fail_closed_pre_c2` violated LL-005 by committing directly from a
domain `prepare_preconditions` path. The corrected design:

1. `_fail_closed_pre_c2(job_id, error_class, subreason, message)` now
   only raises `InventoryPreC2FailClosedError(error_class, subreason,
   message)` — no write, no commit.
2. `ShopifyConnectorJobDispatchInventoryExtension._recover_pre_c2_failure`
   (an override of the existing dispatcher seam, `_inherit`-based, no
   core-file edit) intercepts only this exception type. For it: performs
   the same `self.env.cr.rollback()` / `self.env.transaction.reset()` /
   fresh row-lock re-acquisition core's own version performs, confirms
   no mutation attempt exists and the job is still the exact owner
   (`current_attempt_token == token and state == 'running'`), then calls
   `_block_original_job` with the domain's own `error_class`/`subreason`
   and commits — mirroring exactly the cursor-boundary discipline core's
   own `_recover_pre_c2_failure`/`_recover_layer2_owner` already use
   (proven precedent: `test_mutation_concurrency.py`'s own genuine
   independent-connection tests exercise this same core method the same
   way). Every other exception delegates unchanged to `super()`.
3. A genuine independent-PostgreSQL-connection test
   (`TestInventoryPreC2RecoverySeam` in `test_inventory_push_mechanics.py`,
   tagged `post_install`/`-at_install`, mirroring core's own
   `TestMutationConcurrency._durable_fixture` pattern exactly — a
   `TransactionCase`'s own uncommitted transaction is never visible to a
   separate `db_connect` connection, so the fixture is created and
   committed through its own independent connection) proves the seam
   durably applies the domain's blocked disposition, and that an
   unrelated exception still receives core's own generic bounded-retry
   recovery.

No core file was touched. This is proof-of-implementation of the
corrected, non-committing design, not a hard-stop.

## 5. Prior-cycle limitation — resolved

The prior cycle's disclosed procedural limitation (`cas_retry_ordinal`'s
"replacement = predecessor + 1, no direct jump" guarantee was enforced
only by the single call site, not a DB constraint) is **resolved** this
cycle by item 7 above: `_handoff_supersede` no longer accepts an ordinal
argument at all, so no caller — sanctioned service or otherwise — can
request an arbitrary jump through the module's own API surface. The
ordinal is always derived, in-process, from a freshly row-locked read of
the exact predecessor. **No known implementation limitation remains.**

## 6. D-013-1 .. D-013-9 traceability (unchanged structurally this
cycle; corrected implementations only)

| Decision | Implemented in | Tests |
| --- | --- | --- |
| D-013-1(a) location mapping + sanctioned creation service (identity-conflict fail-closed this cycle) | `shopify_connector_location_mapping.py`, `create_or_update_location_mapping` (service) | `test_location_mapping.py` |
| D-013-1(b) inventory-level binding + sanctioned ensure service + SEC-1 company check + real-GID persistence this cycle | `shopify_connector_inventory_level_binding.py`, `ensure_inventory_level_binding` (service) | `test_inventory_level_binding.py`, `test_inventory_push_mechanics.py` |
| D-013-2 quantity source + clamp + fail-closed integral gate + strict-integer evidence this cycle | `_refresh_pending_target`, `_integral_quantity_or_none`, `_strict_shopify_int`, `_prepare_preconditions_set_quantities` (service) | `test_inventory_triggers.py`, `test_inventory_push_mechanics.py` |
| D-013-3 push mutation mechanics (this cycle: strict-integer/exact-request/no-duplicate success evidence, ambiguous-shape classification, non-committing pre-C2 seam, real-GID capture) | `_prepare_preconditions_set_quantities`, `_transport_set_quantities`, `_classify_direct_set_quantities`, `_apply_consequence_set_quantities` (service) | `test_inventory_push_mechanics.py` |
| D-013-4 first-push guard | `first_push_state`/`action_confirm_first_push` (binding), `_handle_inventory_push_sync` gate, `_enqueue_first_push_preview` (service, hardened this cycle) | `test_inventory_first_push_guard.py` |
| D-013-5 location cache + readiness + sanctioned location-sync admission (response-shape validation + hardened admission this cycle) | `_handle_inventory_location_sync`, `_validate_locations_response`, `_check_mapped_location` override, `_enqueue_location_sync` (service, hardened this cycle) | `test_inventory_location_cache_sync.py` |
| D-013-6 job granularity + triggers + typed scan cron + corrected drift matrix + never-pushed-zero scan fix this cycle | `_enqueue_from_stock_moves`, `run_inventory_push_scan`, `_handle_inventory_push_scan`, `action_push_inventory_now` (service) | `test_inventory_triggers.py` |
| D-013-7 concurrency + exact operation_scope_key literal + protected cas_retry_ordinal + resolved ordinal-lineage limitation this cycle | `_compute_operation_scope_key` override, `create()`/`write()` overrides (job extension), `_handoff_supersede` | `test_inventory_push_mechanics.py` (unit-level); genuine concurrency proof pending, §9 below |
| D-013-8 baseline import split out | Not implemented (Task 013B scope; zero Task 013B code in this diff) | N/A |
| D-013-9 Layer 2 integration + core enqueue-service adoption + corrected coalescing + exact reconciliation identity + row-locked handoffs this cycle | `_get_reconciliation_strategies`/`_get_handlers`/`_get_replay_policies` extensions, `_create_inventory_job`, `_try_enqueue_push_sync`, `_ensure_reconciliation_job` override, `_recover_pre_c2_failure` override | `test_inventory_push_mechanics.py` |

## 7. DEC-037 §4/§9 matrix traceability

Every row of DEC-037 §4 (both mutation domains) and §9 (the
job/mutation-consequence contract) is implemented in
`_classify_direct_set_quantities`, `_classify_direct_activate`,
`_reconcile_set_quantities`, `_reconcile_activate`,
`_apply_consequence_set_quantities`, and `_apply_consequence_activate`,
all corrected further this cycle for strict-integer evidence, exact
request-matching, ambiguous-shape classification, missing-item routing,
and real-GID capture. No cell is left "TBD." The nine-value fixed
`error_class` vocabulary (DEC-037 §7) is used exclusively; the four
withdrawn Revision-2 values never appear (static/AST-verified).

## 8. Static and AST validation — EXECUTED (pure Python, no Odoo required)

| Check | Result |
| --- | --- |
| `python3 -m py_compile` on every `.py` file in the module | EXECUTED — PASS |
| `python3 -m pyflakes` on the whole module (no unused imports/names beyond expected package `__init__.py` re-exports) | EXECUTED — PASS |
| XML well-formedness on the cron data file | EXECUTED — PASS |
| CSV row-shape check on `ir.model.access.csv` | EXECUTED — PASS |
| Manifest parses as a valid Python dict literal | EXECUTED — PASS |
| `git diff --check` (no whitespace errors) | EXECUTED — PASS |
| Allowed-file audit: only the 22 files this correction batch is authorized to touch were changed (exactly 6 touched this cycle: the service model and the six-file — five modified — test suite) | EXECUTED — PASS |
| No `self.env.cr.commit` inside `_fail_closed_pre_c2`, `_prepare_preconditions_set_quantities`, or `_prepare_preconditions_activate` | EXECUTED — PASS |
| No synthetic `'%s:%s'` InventoryLevel-GID pattern anywhere in the module | EXECUTED — PASS |
| Exact reconciliation identity format `'reconcile:%s:%s:%s' % (` present | EXECUTED — PASS |
| `_handoff_supersede`'s signature has no `cas_retry_ordinal` parameter and has `is_cas_replacement` | EXECUTED — PASS |
| `_handle_inventory_location_sync` routes every page through `_validate_locations_response`; no default-empty `.get(...) or {}`/`or []` shape coercion remains in that handler | EXECUTED — PASS |
| `_recheck_inventory_pair` uses `_audit_safe_reason`, never bare `redact(` | EXECUTED — PASS |
| `_handle_inventory_push_sync` calls `binding.try_lock_for_update()` exactly twice (both handoff-A branches) | EXECUTED — PASS |
| `_handle_inventory_mutation_reconcile`'s `except JobHandlerError`/`except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` re-raise branches appear textually before its generic transient-wrap branch | EXECUTED — PASS |
| Pair read uses `inventoryItem(id: $itemId) { inventoryLevel(locationId: $locationId) }`; no `inventoryLevel(inventoryItemId:` root call anywhere (prior cycle, re-verified unchanged) | EXECUTED — PASS |
| `@idempotent(key: $idempotencyKey)` appears exactly twice; `changeFromQuantity` present, `compareQuantity` absent (prior cycle, re-verified unchanged) | EXECUTED — PASS |
| No `inventoryAdjustQuantities`/`'committed'`/`onHand` string anywhere in the module | EXECUTED — PASS |
| No withdrawn `error_class` literal anywhere in the module | EXECUTED — PASS |
| No `inventoryActivate` call site in any `*_set_quantities` strategy method, and vice versa | EXECUTED — PASS |
| No message-text (`.get('message')`/`['message']`) read in `_classify_direct_activate` | EXECUTED — PASS |

These checks were run directly against the corrected committed source in
this workspace (plain Python 3.11; no Odoo installation is available
here), both as standalone verification scripts and as the equivalent
assertions now encoded in the six test files' own static/AST guard tests.

## 9. Odoo/PostgreSQL-dependent tests — IMPLEMENTED, EXECUTION PENDING EXTERNAL ENVIRONMENT

No Odoo or PostgreSQL runtime is available in this implementation
workspace. The following were **implemented but not executed** here (all
six test files extended this cycle with new coverage for every
correction in §2, plus one new tagged test class), and must not be
represented as passed until a genuine Odoo.sh or local-Odoo session runs
them:

- Every `TransactionCase`-based test in the six test files, including
  the new coverage for: missing-InventoryItem routing at all three call
  sites, real-InventoryLevel-GID capture and conflict handling, the
  non-committing pre-C2 fail-closed path, strict-integer/duplicate/
  ambiguous-evidence rejection for both mutations, the never-pushed-zero
  scan distinction (5 scenarios), the exact shared-reconciliation
  identity, CAS ordinal-lineage denial/derivation (0→1→2→3, no-jump,
  non-CAS-reset), CAS-exhaustion stale-code evidence requirement,
  reconciliation exception-ordering (transient-retries vs.
  malformed-blocks), location-sync malformed-response fixtures (6
  scenarios), PII-safe review-reason redaction (email/phone/token/
  ordinary-text fixtures), orchestration handoff row-lock/duplicate-
  handoff/rollback/lineage-log proof, and the hardened backend admission
  services (private rename, authorization, no silent identity
  replacement/move).
- `TestInventoryPreC2RecoverySeam` (tagged `post_install`, `-at_install`):
  the genuine independent-PostgreSQL-connection proof that the recovery
  seam durably commits the domain's blocked disposition, and that an
  unrelated exception still receives core's generic recovery.
- Module installation and same-SHA update.
- Full connector regression (all existing Stage 0/product/sale suites)
  to confirm zero regression from this cycle's changes, specifically
  that the `_ensure_reconciliation_job`/`_recover_pre_c2_failure`
  dispatcher overrides do not regress any non-inventory job type's
  reconciliation or pre-C2 recovery path.
- Lifecycle/uninstall behavior (`_reassign_to_historic_job_type`,
  unchanged this cycle).
- The genuine independent-PostgreSQL-connection concurrency proof for
  pair-serialization admission and atomic-handoff replacement-job
  creation (DEC-037 §5.3/§5.4) — the unit-level equivalent exists in
  `test_inventory_push_mechanics.py`, but the genuine separate-OS-process,
  independent-registry version (LL-006/LL-007) requires the
  child-process-capable runner this workspace does not have.

## 10. Odoo.sh evidence — PENDING (not available in this workspace)

Fresh clean installation, same-SHA update, the focused Task 013 suite,
full connector regression, and residue inspection all require a
dedicated Odoo.sh session and are not claimed here. Per the review's own
instruction, this correction cycle did not begin any Odoo.sh run.

## 11. Dev-store evidence — PENDING (not available in this workspace)

This implementation session has no dev-store credentials or Shopify
runtime authorization. Dev-store validation plan scenarios 1–12, 17–19
are not executed. No real Shopify mutation, and no new Shopify read,
occurred during this correction cycle.

## 12. External child-process concurrency proof — PENDING (not available in this workspace)

Per `docs/05-qa/runtime-lessons-learned.md` LL-006/LL-007/LL-014, the
genuine separate-OS-process, independent-Odoo-registry concurrency proof
requires a child-process-capable runner this workspace does not provide.
This remains mandatory before Task 013 final merge authorization.

## 13. Residue audit

No Odoo/PostgreSQL runtime executed in this session, so there is no
live-process residue to inspect. A source-level residue check was
performed instead: no test fixture inserts raw SQL outside the ORM
except the genuine independent-connection fixtures'
setup/teardown DELETE statements in `TestInventoryPreC2RecoverySeam`
(scoped to only the rows that same test created, mirroring core's own
`TestMutationConcurrency._cleanup_fixture` pattern); no credential,
access token, or PII literal appears anywhere in the module; the
`_handle_inventory_location_sync` `sudo()` elevation is now correctly
described as one of several narrow, named elevations this module uses
(the prior cycle's "sole sudo() site" docstring wording was inaccurate
and is corrected).

## 14. Remaining external evidence required before final merge authorization

1. Odoo.sh: fresh install, same-SHA update, focused Task 013 suite, full
   connector regression, residue inspection.
2. Genuine independent-registry, separate-process concurrency proof
   (DEC-037 §5.3/§5.4) on a child-process-capable runner.
3. Dev-store mutation evidence for scenarios 1–12, 17–19 of the
   validation plan, or an explicit, recorded control-room disposition
   for any scenario found genuinely not-executable.

**No known implementation-level limitation remains** (§5): every item in
comment `5028910116` was corrected in this same batch (§2), the full
same-pattern audit found and corrected one additional defect beyond the
13 named items (§3), and the prior cycle's disclosed procedural
limitation is resolved (§5) — the next candidate has zero known
implementation limitation except the external evidence classes above,
which genuinely require a later environment.

## 15. Explicit confirmations

- This PR remains **draft**, **unmerged**, and was **not marked ready
  for review** by this session.
- **No self-acceptance** occurred.
- **No self-merge** occurred.
- **No protected reference** (`main`, `Shopify-connector`,
  `checkpoint/core-r2-readonly-uat-2026-07-15`,
  `checkpoint/wave-2-order-import-2026-07-18`, `mvp/program-integration`
  prior to this PR's own eventual merge) was changed by this session.
- **No Task 013B work** occurred.
- **No Odoo.sh run** occurred.
- **No live Shopify mutation** occurred — no Odoo/Odoo.sh process ran in
  this workspace, so no live transport call of any kind (read or
  mutation) was possible.
