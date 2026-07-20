# Task 013 — Inventory Synchronization: Implementation Validation Results

- **Status: CORRECTED IMPLEMENTATION CANDIDATE FROZEN FOR INDEPENDENT
  REVIEW — NOT RUNTIME-PROVEN. Draft PR unmerged, not marked ready.**
- **Repository:** `AdamsOdoo/Adams`
- **Branch:** `claude/wave-3-task-013-2g0ul0` (harness-provisioned; see PR
  #182 body for the session-naming note against the locked prompt's
  `sol/wave-3-task-013-inventory-sync` name)
- **Draft PR:** [#182](https://github.com/AdamsOdoo/Adams/pull/182) →
  `mvp/program-integration`
- **Exact base SHA:** `mvp/program-integration` @
  `8f5f421e2110c2e805460ea75fb519e48013e0f7` (PR #181's merge commit)
- **This is a correction cycle on the same draft PR**, per the binding
  control-room review at PR #182 comments
  [`5025765389`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5025765389)
  (REVISE) and its addendum
  [`5025803697`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5025803697),
  both issued against the previously-frozen head
  `2c6c551391cc00602ca74ebebb7b20c39ab58a74`.
- **Implementation worker for this correction cycle:** Claude Code —
  explicitly re-affirmed for **Task 013 / PR #182 only** by comment
  `5025765389`'s binding governance disposition 1, as the accepted
  exception permitted by `CLAUDE.md` §13. This does not change Claude's
  default role for later tasks and does not authorize self-acceptance
  or self-merge.
- **Acceptance authority:** ChatGPT (product-owner control room). This
  session did not accept its own work, did not mark the PR ready, and
  did not merge.

## 1. Implemented scope (as corrected)

`addons/shopify_connector_inventory` (Full edition, LGPL-3; depends
`shopify_connector_core`, `shopify_connector_product`, `stock`):

- `shopify.connector.location.mapping` (D-013-1(a)): explicit
  Shopify-Location ↔ Odoo-internal-`stock.location` mapping, dual
  uniqueness, ancestor/descendant-overlap guard, internal-only domain
  (enforced server-side), company-consistency check, `push_enabled`
  control, plus (new this cycle) a sanctioned service-level creation/
  update path (`ShopifyConnectorInventoryService.
  create_or_update_location_mapping`).
- `shopify.connector.inventory.level.binding` (D-013-1(b)): per
  (product-variant-binding, location-mapping) pair identity, dual
  uniqueness, the first-push preview/confirmation record,
  informational-only last-pushed/last-known/pending-target fields, the
  public `action_recheck_inventory_pair(reason)` review-release action,
  a new server-side SEC-1 composite-binding company-consistency
  constraint, and a sanctioned service-level ensure/create path
  (`ensure_inventory_level_binding`).
- `shopify.connector.inventory.service` (D-013-9, DEC-037 §4/§5/§9): the
  three central pair-execution jobs (`inventory_push_sync`,
  `inventory_activate`, `inventory_set_quantities`) plus the shared,
  read-only `inventory_mutation_reconcile` reconciliation job type
  (ratified this cycle, §3 below) — seven registered `job_type` values
  in total. Corrected this cycle:
  - the pair read (`_read_shopify_inventory_pair`) now uses the official
    2026-07 nested `inventoryItem(id:) { inventoryLevel(locationId:) }`
    shape, distinguishing item-missing/untracked/level-absent/malformed
    cases explicitly and failing closed on any ambiguous shape;
  - both mutation documents now declare `$idempotencyKey: String!` and
    apply `@idempotent(key: $idempotencyKey)`;
  - `inventorySetQuantities` now sends `changeFromQuantity` (never
    `compareQuantity`), an actual integer quantity gated by a fail-closed
    integrality check, and a `referenceDocumentUri` built from the
    database UUID (`ir.config_parameter` `database.uuid`), never the raw
    database name;
  - direct-success evidence for both mutations now requires more than an
    empty `userErrors` list — matching `quantityAfterChange`/item/
    location/zero-`available` evidence is mandatory before `succeeded`;
  - reconciliation freshness/ABA evidence is now parsed as real
    timezone-aware datetimes, never compared as raw differently-formatted
    strings;
  - every genuinely unsafe precondition the fresh pre-C2 read discovers
    (store-identity mismatch, missing/inactive level, untracked item, a
    non-integral target, a missing required GID) now fails closed via a
    new `_fail_closed_pre_c2` seam **before** C2/transport, with no
    `mutation.attempt` row created;
  - ordinary job admission is now routed through the core's sanctioned
    `shopify.connector.job.enqueue` service, never a direct
    `shopify.connector.job.sudo().create()`;
  - push-sync admission coalescing now swallows only the exact
    operation-scope-key collision, re-verified by an independent query,
    never any other `ValidationError`;
  - `operation_scope_key` now equals the exact frozen literal
    `inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}`
    for the three pair-execution job types (an inheritance override of
    core's computed field), never core's longer composite string, and
    never applied to the shared reconciliation type;
  - `cas_retry_ordinal` is now protected against non-`sudo()` create/write
    and range/domain-validated (0–3, non-zero only for
    `inventory_set_quantities`);
  - the scheduled push-scan cron now enqueues one typed
    `inventory_push_scan` job per eligible store through the core enqueue
    service, and that job's own handler (not the cron thread) performs
    the per-store scan;
  - drift classification now uses the corrected three-way matrix: Shopify
    already equal to the current Odoo target is never drift, even when it
    also differs from `last_pushed_available`;
  - a genuine pre-existing sequencing defect in `_handle_inventory_push_sync`
    (found and fixed during this cycle, not named by either review
    comment — §2 item 15 below) that would have made every
    orchestration→mutation handoff collide on the pair's own
    `operation_scope_key`.
- `shopify.connector.store.settings` extension (unchanged this cycle):
  `inventory_scheduled_sync_enabled`, `inventory_last_push_scan_at`.
- `security/ir.model.access.csv`, `data/shopify_connector_inventory_cron.xml`
  (unchanged this cycle).
- Six test files, all extended this cycle with new coverage for every
  correction above (§6/§7 below).

**Zero core (`shopify_connector_core`), `shopify_connector_product`, or
`shopify_connector_sale` files were created or modified**, this cycle or
the previous one. Every extension still uses only the existing,
unmodified seams.

## 2. Correction batch applied (this cycle) — full audit trail

Every item below traces to PR #182 comment `5025765389` (numbered as in
that comment) or its addendum `5025803697` (numbered 20–22), except item
15, which is a defect this session found and fixed while implementing
item 11 and was not named by either review comment.

1. **Read-query schema fix.** `_read_shopify_inventory_pair` no longer
   calls the root `inventoryLevel(inventoryItemId:, locationId:)` field
   (invalid on the 2026-07 schema); it now reads through
   `inventoryItem(id:) { inventoryLevel(locationId:) }`, returning a
   structured `item_exists`/`tracked`/`level_exists`/`available`/
   `updated_at` shape and raising `JobHandlerError(data_shape_schema_mismatch)`
   on any malformed/ambiguous response — never defaulting a missing item
   to `tracked=True` or a malformed response to "no level."
2. **Idempotency directive.** Both `inventorySetQuantities` and
   `inventoryActivate` now declare `$idempotencyKey: String!` and apply
   `@idempotent(key: $idempotencyKey)`, with the same UUID threaded into
   `variables` and persisted on the attempt at C2 (`shopify_idempotency_key`,
   unchanged core mechanism).
3. **CAS field name.** `inventorySetQuantities` now sends
   `changeFromQuantity` (an actual integer); `compareQuantity` no longer
   appears anywhere in the module (source-level guard confirms this).
4. **Freshness/ABA parsing.** `_reconcile_set_quantities` now parses
   `InventoryQuantity.updatedAt` and `attempt.transport_at` into
   timezone-aware `datetime` objects and compares them properly — never
   a raw-string comparison of differently-formatted timestamps. A
   same-value read with a later `updatedAt` (a possible ABA) remains
   `inconclusive`; a same-value read with no later evidence, and only
   when freshness evidence is genuinely usable, supports `not_applied`;
   missing or unparsable freshness evidence never defaults to
   `not_applied`.
5. **Reference document URI.** Built as
   `odoo://<database-uuid>/shopify.connector.job/<id>`, where
   `<database-uuid>` is resolved from `ir.config_parameter`'s
   `database.uuid` (never `env.cr.dbname`); if unresolvable, the job
   fails closed pre-C2 rather than building a URI with a missing UUID.
6. **Set-quantities direct-success evidence.** An empty `userErrors`
   list is no longer sufficient. `_is_valid_set_quantities_success` now
   requires a non-null `inventoryAdjustmentGroup` with a matching
   `available` change whose `quantityAfterChange` equals the requested
   target; any null/missing/mismatched shape becomes `uncertain` /
   `data_shape_schema_mismatch`, action `reconcile` — never a false
   `succeeded`.
7. **Activate direct-success evidence.** `_is_valid_activate_success`
   now requires a non-null `InventoryLevel` whose returned item/location
   IDs match what was requested and whose `available` quantity is
   exactly zero; the existing payload-shape-only clean-rejection/
   ambiguous-shape classifications are otherwise unchanged (still no
   message-text routing).
8. **Source/AST + unit test coverage** for items 1–7 added to
   `test_inventory_push_mechanics.py` (§6 below).
9. **Core enqueue-service adoption.** `_create_inventory_job` now routes
   every ordinary job creation through `shopify.connector.job.enqueue`
   (the core's sole sanctioned domain enqueue service) instead of a
   direct `shopify.connector.job.sudo().create()`. The domain-owned
   `cas_retry_ordinal` field (outside that service's signature) is
   applied through one narrow, same-transaction `sudo()` write
   immediately after enqueueing, only when non-zero — no second
   transaction, no parallel enqueue mechanism.
10. **Coalescing correction.** `_try_enqueue_push_sync` now catches a
    `ValidationError` only when its message matches the exact declared
    `_store_operation_scope_key_uniq` constraint text, and only after
    independently re-querying for an actual non-terminal job on the
    precise pair; every other `ValidationError` (store-state,
    domain-disabled, company, invalid fields, illegal transitions,
    security, unrelated constraints, malformed identity) now propagates.
11. **Exact `operation_scope_key` literal.** A new
    `_compute_operation_scope_key` override (calling `super()` first)
    sets the stored value to the exact frozen literal
    (`job.shopify_target_gid`, verbatim) for the three pair-execution
    job types only, while non-terminal and not superseded; every other
    job type (including the shared reconciliation type) keeps core's
    original composite behavior unchanged.
12. **`cas_retry_ordinal` protection.** `create()`/`write()` overrides on
    the job model now deny any non-`sudo()` attempt to supply or modify
    `cas_retry_ordinal` (mirroring core's own `PROTECTED_JOB_FIELDS`
    pattern exactly), and a new `@api.constrains` enforces it is 0 for
    every job_type other than `inventory_set_quantities`, and within
    [0, 3] always.
13. **Typed scan-job cron.** `run_inventory_push_scan` (the cron entry
    point) now only enqueues one `inventory_push_scan` job per eligible
    connected store, through the core enqueue service; the actual
    per-store scan logic moved into that job's own handler
    (`_handle_inventory_push_scan`), never inline on the cron thread.
14. **Corrected three-way drift matrix.** Shopify already equal to the
    current Odoo target is never drift, even when it also differs from
    `last_pushed_available`; unexplained drift is now recognized only
    when Shopify differs from **both** the last-pushed value and the
    current target.
15. **[Self-discovered, not named by either review comment] Orchestration
    → mutation handoff sequencing defect.** `_handle_inventory_push_sync`
    previously created its child mutation job (`inventory_activate` or
    `inventory_set_quantities`) for the same pair **before**
    terminalizing itself. Since `operation_scope_key` never varies by
    `job_type` (it is keyed on the pair alone), the still-`running`
    orchestration job's own scope key was identical to the child's
    about-to-be-inserted one, so the child's insert would collide on the
    `_store_operation_scope_key_uniq` constraint — the entire
    push_sync→mutation handoff would never actually succeed at runtime.
    Fixed by reordering both branches to terminalize the orchestration
    job (`state='succeeded'`) and flush **before** creating the child,
    mirroring the exact ordering `_handoff_supersede` already used
    elsewhere in this same file. Found while building the
    `operation_scope_key` exact-literal tests (item 11); not part of
    either review comment's explicit list.
16. **Fail-closed integral-quantity gate.** A new
    `_integral_quantity_or_none` helper accepts a target only when it is
    integral within an accepted floating-point-noise tolerance
    (`1e-4`), returning an actual Python `int`; a genuine fraction fails
    closed pre-C2 as `data_shape_schema_mismatch`/`binding_conflict`,
    with no mutation-attempt row created. Negative-to-zero clamping
    (existing D-013-2 behavior) is unchanged and still logs the true
    negative value.
17. **Backend creation/admission services (comment `5025803697` item
    22).** Four new sanctioned service methods, all authorization-checked,
    all resolving/validating referenced records in the caller's own
    environment before a narrow `sudo()` for the protected-field
    create/write itself, none adding a public action or UI:
    `create_or_update_location_mapping`, `ensure_inventory_level_binding`,
    `enqueue_first_push_preview`, `enqueue_location_sync`. The latter two
    make the previously dead `inventory_first_push_preview`/
    `inventory_location_sync` handlers reachable through something other
    than direct protected-field job creation.
18. **SEC-1 composite-binding company consistency (comment `5025803697`
    item 21).** A new `@api.constrains` on the inventory-level binding
    enforces that any non-empty product-variant company and mapped-
    location company both equal `env.company`, and equal each other when
    both are non-empty; company-neutral records remain valid.
19. **Fresh pre-C2 fail-closed conditions (comment `5025803697` item
    20).** `_prepare_preconditions_set_quantities` no longer converts a
    missing/inactive level's `available: None` to `0.0` and proceeds. A
    new `_fail_closed_pre_c2` seam (§4 below) lets this domain-owned
    callback reach the accepted `blocked_manual_review`/
    `inventory_location_missing` disposition — not core's generic
    `shopify_temporary_server_network` retry — with no mutation-attempt
    row ever created. Applied to: store-identity mismatch, missing/
    inactive level, item gone untracked, a non-integral target, and a
    missing required GID.

## 3. Governing-document amendments applied (control-room ratified)

Exactly the two amendments the control room authorized (comment
`5025765389` disposition 2 and item 16) were applied, and only those
two, to the three newly-authorized governing files — no other Gate B
decision was reopened:

- **`docs/04-decisions/DEC-037-wave-3-inventory-gate-b.md` §7:** the
  registered Task 013 job-type count is corrected from six to seven,
  listing `inventory_mutation_reconcile` alongside the other six; the
  pair-serialization identity bullet and domain-enable-flag bullet are
  updated to match; a new bullet documents the shared reconciliation
  type's read-only/attempt-linked/lifecycle behavior; a new bullet
  documents the fail-closed integral-quantity rule. The superseded "No
  new job type is added for reconciliation reads" sentence is struck
  through and retained only for history.
- **`docs/07-implementation-plan/task-013-inventory-sync-implementation-packet.md`:**
  D-013-2 gains the fail-closed integral-quantity rule; the job-type →
  domain-flag map (§4) is corrected from six to seven types; the §5 test
  list gains two narrowly-scoped annotations (the integral-quantity gate
  and the reconciliation job type's read-only/attempt-linked behavior)
  for `test_inventory_push_mechanics.py`, and the drift-matrix/typed-
  scan-cron correction is reflected in the existing
  `test_inventory_triggers.py` entry without expanding its scope beyond
  what it already covered.
- **`docs/06-prompts/sol-wave-3-task-013-locked-prompt.md`:** the
  service-model annotation gains the reconciliation job-type
  registration description; HARD CONSTRAINTS gains the fail-closed
  integral-quantity rule; the `test_inventory_push_mechanics.py`
  annotation gains the same two narrowly-scoped items as the packet.
  The locked prompt's issuance history is not altered or marked
  executed.

No other product or architecture decision was reopened in any of the
three files.

## 4. The pre-C2 fail-closed seam — proof, not a gap

Per comment `5025803697` item 20's instruction to report an exact seam
gap if Stage 0 cannot express this without a forbidden core change: a
working seam **was** found and used, entirely within this domain
module's own `prepare_preconditions` callback — no core file was
touched. `_fail_closed_pre_c2(job_id, error_class, subreason, message)`
calls the existing, already-used-elsewhere cross-model method
`shopify.connector.job.dispatch._block_original_job(...)` (the same
method this module's own `_handle_inventory_mutation_reconcile` already
calls) to write `blocked_manual_review` plus the domain's own
error_class/subreason, commits immediately (mirroring the commit-
after-state-transition pattern core's own `_drain_mutation_one` already
uses between C1 and `prepare_preconditions`), and then raises. Because
`job.state != 'running'` by the time core's `_recover_pre_c2_failure`
re-acquires the job, its generic bounded-retry branch is a no-op and
the domain-specific blocked disposition is what survives — no
mutation-attempt row is ever created, and no Shopify transport occurs.
This is proof-of-implementation, not a hard-stop.

## 5. Known, honestly-disclosed limitation (procedural, not structural)

`cas_retry_ordinal`'s "a replacement always equals the predecessor's
ordinal + 1, no direct jump" guarantee is enforced **procedurally** — by
the single call site (`_apply_consequence_set_quantities`'s CAS-stale
branch always passes `job.cas_retry_ordinal + 1`) — not by a database-
level constraint verifying the predecessor/successor relationship,
because the predecessor's `superseded_by_job_id` link is only written
*after* the successor is created (`_handoff_supersede`'s existing,
unchanged ordering), so a `@api.constrains` on the new job's own
creation cannot yet see that link. The range/domain constraint (0–3,
non-zero only for `inventory_set_quantities`, §2 item 12 above) **is**
DB-enforced. This is disclosed here rather than silently assumed; it
does not allow an unauthorized Shopify mutation or a fifth replacement
job (the ordinal-3 exhaustion check in `_apply_consequence_set_quantities`
remains the actual admission guard).

## 6. D-013-1 .. D-013-9 traceability (updated)

| Decision | Implemented in | Tests |
| --- | --- | --- |
| D-013-1(a) location mapping + sanctioned creation service | `shopify_connector_location_mapping.py`, `create_or_update_location_mapping` (service) | `test_location_mapping.py` |
| D-013-1(b) inventory-level binding + sanctioned ensure service + SEC-1 company check | `shopify_connector_inventory_level_binding.py`, `ensure_inventory_level_binding` (service) | `test_inventory_level_binding.py` |
| D-013-2 quantity source + clamp + fail-closed integral gate | `_refresh_pending_target`, `_integral_quantity_or_none`, `_prepare_preconditions_set_quantities` (service) | `test_inventory_triggers.py`, `test_inventory_push_mechanics.py` |
| D-013-3 push mutation mechanics (corrected: schema, idempotent directive, changeFromQuantity, reference URI, direct-success evidence, pre-C2 fail-closed) | `_prepare_preconditions_set_quantities`, `_transport_set_quantities`, `_classify_direct_set_quantities`, `_apply_consequence_set_quantities` (service) | `test_inventory_push_mechanics.py` |
| D-013-4 first-push guard | `first_push_state`/`action_confirm_first_push` (binding), `_handle_inventory_push_sync` gate, `enqueue_first_push_preview` (service) | `test_inventory_first_push_guard.py` |
| D-013-5 location cache + readiness + sanctioned location-sync admission | `_handle_inventory_location_sync`, `_check_mapped_location` override, `enqueue_location_sync` (service) | `test_inventory_location_cache_sync.py` |
| D-013-6 job granularity + triggers + typed scan cron + corrected drift matrix | `_enqueue_from_stock_moves`, `run_inventory_push_scan`, `_handle_inventory_push_scan`, `action_push_inventory_now` (service) | `test_inventory_triggers.py` |
| D-013-7 concurrency + exact operation_scope_key literal + protected cas_retry_ordinal | `_compute_operation_scope_key` override, `create()`/`write()` overrides (job extension) | `test_inventory_push_mechanics.py` (unit-level); genuine concurrency proof pending, §9 below |
| D-013-8 baseline import split out | Not implemented (Task 013B scope; zero Task 013B code in this diff) | N/A |
| D-013-9 Layer 2 integration + core enqueue-service adoption + corrected coalescing | `_get_reconciliation_strategies`/`_get_handlers`/`_get_replay_policies` extensions, `_create_inventory_job`, `_try_enqueue_push_sync` (service) | `test_inventory_push_mechanics.py` |

## 7. DEC-037 §4/§9 matrix traceability

Every row of DEC-037 §4 (both mutation domains) and §9 (the
job/mutation-consequence contract) is implemented in
`_classify_direct_set_quantities`, `_classify_direct_activate`,
`_reconcile_set_quantities`, `_reconcile_activate`,
`_apply_consequence_set_quantities`, and `_apply_consequence_activate`,
all corrected this cycle for direct-success evidence and freshness/ABA
parsing (§2 items 4/6/7 above). No cell is left "TBD." The nine-value
fixed `error_class` vocabulary (DEC-037 §7) is used exclusively; the
four withdrawn Revision-2 values never appear (static/AST-verified).

## 8. Static and AST validation — EXECUTED (pure Python, no Odoo required)

| Check | Result |
| --- | --- |
| `python3 -m py_compile` on every `.py` file in the module | EXECUTED — PASS |
| `python3 -m pyflakes` on the whole module (no unused imports/names beyond expected package `__init__.py` re-exports) | EXECUTED — PASS |
| XML well-formedness on the cron data file | EXECUTED — PASS |
| CSV row-shape check on `ir.model.access.csv` | EXECUTED — PASS |
| `git diff --check` (no whitespace errors) | EXECUTED — PASS |
| Allowed-file audit: only the 22 files this correction batch is authorized to touch were changed | EXECUTED — PASS |
| Pair read uses `inventoryItem(id: $itemId) { inventoryLevel(locationId: $locationId) }`; no `inventoryLevel(inventoryItemId:` root call anywhere | EXECUTED — PASS |
| `@idempotent(key: $idempotencyKey)` appears exactly twice (once per mutation); `$idempotencyKey: String!` declared | EXECUTED — PASS |
| `changeFromQuantity` present; `compareQuantity` absent, module-wide | EXECUTED — PASS |
| No `inventoryAdjustQuantities` string anywhere in the module | EXECUTED — PASS |
| No `'committed'` string anywhere in the module | EXECUTED — PASS |
| No `onHand` string anywhere in the module | EXECUTED — PASS |
| No withdrawn `error_class` literal anywhere in the module | EXECUTED — PASS |
| No `inventoryActivate` call site in any `*_set_quantities` strategy method, and vice versa | EXECUTED — PASS |
| No message-text (`.get('message')`/`['message']`) read in `_classify_direct_activate` | EXECUTED — PASS |

These checks were run directly against the corrected committed source in
this workspace (plain Python 3.11; no Odoo installation is available
here) — reproduced independently of the six test files' own equivalent
guard tests, and their exact commands/output are reproducible from this
document's own git history.

## 9. Odoo/PostgreSQL-dependent tests — IMPLEMENTED, EXECUTION PENDING EXTERNAL ENVIRONMENT

No Odoo or PostgreSQL runtime is available in this implementation
workspace. The following were **implemented but not executed** here (all
six test files were extended this cycle with new coverage for every
correction in §2), and must not be represented as passed until a
genuine Odoo.sh or local-Odoo session runs them:

- Every `TransactionCase`-based test in the six test files, including
  the new coverage for: the corrected GraphQL read/mutation shapes, the
  idempotency-directive/key threading, the CAS-field rename, the
  integral-quantity gate boundaries, the reference-document-URI shape,
  direct-success-evidence rejection of malformed payloads, freshness/ABA
  parsing (including missing/malformed-timestamp fixtures), the exact
  `operation_scope_key` literal and its lifecycle, `cas_retry_ordinal`'s
  non-`sudo()` denial and range/domain constraint, the typed scan-job
  cron and its handler, the corrected three-way drift matrix, the
  sanctioned backend creation/admission services, the SEC-1
  company-consistency constraint, the unrelated-`ValidationError`
  propagation through coalescing, and the fresh pre-C2 fail-closed
  conditions.
- Module installation and same-SHA update.
- Full connector regression (all existing Stage 0/product/sale suites)
  to confirm zero regression from this addon's registration on the
  shared seams, and specifically that the `job.create()`/`write()`
  override added this cycle does not regress any existing core job
  creation path.
- Lifecycle/uninstall behavior (`_reassign_to_historic_job_type` via the
  seven `job_type` `ondelete` callables, including the new
  `inventory_mutation_reconcile` value).
- The genuine independent-PostgreSQL-connection concurrency proof for
  pair-serialization admission and atomic-handoff replacement-job
  creation (DEC-037 §5.3/§5.4) — the unit-level equivalent (asserting
  the DB-level admission/handoff behavior through the ORM directly, now
  including the exact-literal `operation_scope_key` assertions) exists
  in `test_inventory_push_mechanics.py`, but the genuine separate-
  OS-process, independent-registry version (LL-006/LL-007) requires the
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
performed instead: no test fixture inserts raw SQL outside the ORM; no
credential, access token, or PII literal appears anywhere in the module;
the module still introduces exactly one new `sudo()` site
(`_handle_inventory_location_sync`) for elevated writes plus the narrow,
explicitly-scoped `sudo()` calls the new sanctioned service methods use
only for the mixin's protected-field create/write (never for validation
or authorization, which always run in the caller's own environment
first) — consistent with D-013-5's "one named elevation-for-mutation
sudo" intent and not a new unscoped elevation pattern.

## 14. Remaining external evidence required before final merge authorization

1. Odoo.sh: fresh install, same-SHA update, focused Task 013 suite, full
   connector regression, residue inspection.
2. Genuine independent-registry, separate-process concurrency proof
   (DEC-037 §5.3/§5.4) on a child-process-capable runner.
3. Dev-store mutation evidence for scenarios 1–12, 17–19 of the
   validation plan, or an explicit, recorded control-room disposition
   for any scenario found genuinely not-executable.

No genuine implementation-level blocker remains: every P0/P1 item in
both review comments was corrected in this same batch (§2), the one
procedural-not-structural limitation is disclosed transparently (§5),
and the one seam the review flagged as a possible hard-stop was
resolved, not left open (§4).

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
