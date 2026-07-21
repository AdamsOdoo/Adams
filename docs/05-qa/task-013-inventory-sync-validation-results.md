# Task 013 — Inventory Synchronization: Implementation Validation Results

- **Status: SURGICALLY CORRECTED IMPLEMENTATION CANDIDATE FROZEN FOR
  INDEPENDENT REVIEW — NOT RUNTIME-PROVEN. Draft PR unmerged, not marked
  ready.**
- **Repository:** `AdamsOdoo/Adams`
- **Branch:** `claude/wave-3-task-013-2g0ul0`
- **Draft PR:** [#182](https://github.com/AdamsOdoo/Adams/pull/182) →
  `mvp/program-integration`
- **Exact base SHA:** `mvp/program-integration` @
  `8f5f421e2110c2e805460ea75fb519e48013e0f7` (PR #181's merge commit)
- **This is the third correction cycle on the same draft PR.** Cycle 1
  (head `eb85ea43e73df2a0e1c1667b687f838f31058f81`) responded to
  [`5025765389`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5025765389)/[`5025803697`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5025803697).
  Cycle 2 (head `7979134f76e275c3d60dfc30b2561b754f0b94c4`) responded to
  [`5028910116`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5028910116).
  **This cycle (cycle 3)** responds to the control-room re-review at
  [`5029906989`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5029906989)
  ("REVISE BEFORE RUNTIME"), which found direction-accepted progress from
  cycle 2 but ten remaining blocking implementation defects and
  false-green test gaps, organized into seven surgical correction groups.
  Both governing amendments (`inventory_mutation_reconcile`,
  fail-closed integral-quantity rule) remain accepted in principle and
  were not reopened this cycle; the synchronized-no-op bookkeeping
  ruling in comment `5029906989` item 5 is an implementation
  clarification using existing fields, not a new amendment.
- **Implementation worker for this correction cycle:** Claude Code — the
  Task 013/PR #182-only exception remains explicitly re-affirmed for
  this cycle's own prompt. This does not change Claude's default role
  for later tasks and does not authorize self-acceptance or self-merge.
- **Acceptance authority:** ChatGPT (product-owner control room). This
  session did not accept its own work, did not mark the PR ready, and did
  not merge.
- **Commits this cycle:** `de47c20` (production safety corrections) and
  `26f5af8` (regression tests), on top of the ten commits already on the
  branch from the identity-gate-verified starting head
  `7979134f76e275c3d60dfc30b2561b754f0b94c4`.

## 1. Implemented scope (as corrected this cycle)

Only `models/shopify_connector_inventory_service.py` and
`tests/test_inventory_push_mechanics.py` changed this cycle — every
other module file is byte-identical to cycle 2's frozen candidate; no
governing document was touched (none was authorized or required this
cycle — the scope for this cycle was explicitly narrower than cycle 2's,
limited to the seven groups in comment `5029906989`).

## 2. Correction groups applied this cycle — full audit trail

Each group traces to PR #182 comment
[`5029906989`](https://github.com/AdamsOdoo/Adams/pull/182#issuecomment-5029906989).

### Group A — Reconciliation error vocabulary

`_ensure_reconciliation_job`'s terminal-but-unresolved branch previously
called `_block_original_job` with `SUBREASON_DUPLICATE_RISK` in BOTH the
`error_class` and `subreason` positions — `duplicate_risk` is a valid
core registry value but outside Task 013's frozen nine-value
`error_class` vocabulary. Fixed to `ERROR_CLASS_DATA_SHAPE` (error_class)
+ `SUBREASON_DUPLICATE_RISK` (subreason). The method now reads
`locked_attempt` (not the pre-lock `attempt`) for every post-lock
identity/domain/token/generation/disposition access, and uses
`TERMINAL_JOB_STATES` (the complete accepted set, including `skipped`)
instead of a hard-coded three-value tuple.

The previously-false-green `test_no_error_class_value_outside_fixed_vocabulary`
(it only scanned string literals anywhere in the file, never resolving
what value an actual call site puts in the `error_class` argument
position, so it never would have caught the defect above) is replaced
with a receiver/argument-aware AST guard: it resolves the exact argument
node at every known error_class-emitting call site
(`_block_original_job`, `_block_pair`,
`_transition_blocked_manual_review`, `_transition_retry_waiting`,
`JobHandlerError`, `InventoryPreC2FailClosedError`) and proves it is
always one of the nine `ERROR_CLASS_*` constants (or the one accepted
pass-through shape, an already-validated exception's own `.error_class`
attribute). A companion self-test
(`test_error_class_vocabulary_guard_detects_subreason_misuse`) proves
the guard is not vacuous: it rejects a synthetic AST snippet reproducing
the exact original defect and an unrecognized literal, while still
accepting `duplicate_risk` in the subreason position.

### Group B — Activation fresh pre-C2 read

`_prepare_preconditions_activate` previously validated only local GIDs
and went straight to transport with no re-read of Shopify state. It now
performs the same fresh pair read `_prepare_preconditions_set_quantities`
already performed: a different store identity, a missing/recreated item,
an item gone untracked, or a conflicting already-recorded InventoryLevel
GID all fail closed via `_fail_closed_pre_c2` (no mutation-attempt row
created). When the fresh read instead finds a valid level already
exists, sending an activation mutation is never safe — a new
`InventoryActivationSupersededError` signals a dedicated
`_recover_activation_superseded` recovery seam (an extension of the
existing inherited `_recover_pre_c2_failure` override, LL-005 compliant:
no domain-side commit inside `prepare_preconditions` itself) that skips
the job (`state='skipped'`), opportunistically captures the observed GID
when the binding is still empty, and atomically hands off to exactly one
fresh `inventory_push_sync` under the binding's row lock, with
predecessor/successor IDs logged — mirroring every other handoff's
terminalize-then-create ordering so pair serialization is preserved.

Proven via `TestInventoryPreC2RecoverySeam` (genuine independent
PostgreSQL connections, LL-005), extended with a full new fixture chain
(`_durable_activation_fixture`) and
`test_activation_superseded_recovery_skips_and_hands_off`, plus five
plain-`TransactionCase` tests for the four fail-closed branches and the
raise-signal itself.

### Group C — Real InventoryLevel GID enforcement + review/stale admission gate

`_read_shopify_inventory_pair` now validates that the returned
InventoryItem identity equals the requested one, that the returned
InventoryLevel's nested `item`/`location` identity belongs to the
requested pair (the query now requests `item { id } location { id }` on
the nested level), and rejects a duplicate `available` quantity entry
instead of silently taking the last one.

`_handle_inventory_push_sync` now persists the real InventoryLevel GID
(or fails closed on a conflicting already-recorded one) *before* the
no-op/drift/child-admission decision, so a no-op equality path can no
longer leave `shopify_gid` empty forever.

A new `_binding_push_admission_blocked(binding)` helper (`status in
('review', 'stale')`) centrally gates every admission surface: it is
checked inside `_try_enqueue_push_sync` (covering stock-move event
admission, manual push, and scheduled scan in one place, since all three
route through it), independently re-checked at the top of
`_handle_inventory_push_sync` (the direct-dispatch race window), and
re-checked again *under the binding's row lock* immediately before each
of that handler's two handoff branches creates its child — closing a
narrow TOCTOU race where a concurrent writer could flag the binding
`review`/`stale` between the handler's initial unlocked check and the
handoff's own lock acquisition. It is also checked before either CAS
replacement (`_apply_consequence_set_quantities`) or reconciliation
replacement (`_apply_consequence_set_quantities`/`_apply_consequence_activate`)
creates a successor. `active` and `manually_overridden` remain eligible;
the mixin's own existing semantics for `manually_overridden` are
unchanged and never reinterpreted.

`_apply_consequence_activate`'s succeed branch previously called
`_handoff_succeed_to_fresh_orchestration` unconditionally, even when the
same call just flagged the binding `status='review'` for a GID conflict
— comment `5029906989` item 4's explicit complaint. Fixed: the handoff
now only fires when no conflict was flagged in this same write.

### Group D — Verified no-op baseline

When `_handle_inventory_push_sync`'s fresh, identity-validated read
proves Shopify `available` already equals the current Odoo target, the
handler now records `last_pushed_available`/`last_pushed_at` as the
accepted synchronized baseline (in addition to the already-existing
`last_known_shopify_available` write earlier in the same handler) before
succeeding — no Shopify mutation is sent and none is implied. Previously
`last_pushed_at` stayed unset in this branch, so the never-pushed-zero
admission fix from cycle 2 caused every later scan to re-admit the same
already-synchronized pair forever.

### Group E — CAS ordinal creation surface

`_create_inventory_job` no longer accepts a `cas_retry_ordinal`
parameter at all — the signature has no such argument, and every job it
creates is ordinal 0 (the field's model-level default). A new
`_create_cas_successor_job(locked_predecessor, binding)` is the sole
surface that can ever produce a nonzero ordinal: it requires an
already-row-locked `inventory_set_quantities` predecessor, derives the
successor ordinal exclusively from that locked object's own recorded
ordinal (never a caller-supplied value), permits only 1/2/3, and is
invoked exclusively from `_handoff_supersede`'s CAS-replacement branch.

### Group F — Structured Shopify user-error evidence

A new module-level `_validate_structured_user_errors(user_errors,
code_required)` strictly validates and sanitizes a Shopify `userErrors`
list into the frozen `[{code, field}]` shape — never persisting message
text — and is now used by both `_classify_direct_set_quantities`
(`code_required=True`) and `_classify_direct_activate`
(`code_required=False`, since inventoryActivate's 2026-07 schema exposes
no structured code). A malformed entry (non-list, non-dict entry,
missing/non-string `code`, non-string-list `field`) is classified
`uncertain`/`data_shape_schema_mismatch`, never a clean rejection, for
both mutations. The free-form `user_error_codes` evidence list is
removed entirely. CAS-exhaustion release eligibility
(`_recheck_inventory_pair`) now inspects the structured `user_errors`
list for an exact entry whose `code == 'CHANGE_FROM_QUANTITY_STALE'`,
never a substring or generic-container membership test on a free-form
list.

### Group G — Response and reconciliation fail-closed hardening

Covered by Group C's pair-read identity/duplicate-entry validation
above. In addition: `_is_valid_set_quantities_success` now requires
`expected_reason`/`expected_reference_uri`/the returned `reason`/
`referenceDocumentUri` to each be a non-empty string before comparing
them — two missing values comparing equal (`None == None`) is never
valid success evidence (this closes a false-green gap in two pre-existing
test fixtures, corrected this cycle — see §7). `_prepare_preconditions_set_quantities`
defensively re-validates `read['available']` through `_strict_shopify_int`
at the exact callback boundary immediately before it becomes
`changeFromQuantity`, so a mocked/overridden read can never let a
non-integer value reach the mutation request. `_reconcile_set_quantities`
now routes an absent InventoryLevel (while the item exists) to
`not_applied`/`inventory_location_missing`/`block_manual_review`
instead of falling through to a generic `current=None` comparison that
previously consumed the bounded inconclusive-retry budget by looping
`inconclusive` forever — a set-quantities effect cannot be applied to a
nonexistent level.

## 3. Static and AST validation — EXECUTED (pure Python, no Odoo required)

| Check | Result |
| --- | --- |
| `python3 -m py_compile` on the changed model and test files | EXECUTED — PASS |
| `python3 -m pyflakes` on the changed model and test files (no unused imports/names beyond expected package `__init__.py` re-exports) | EXECUTED — PASS |
| `git diff --check` (no whitespace errors) | EXECUTED — PASS |
| Allowed-file audit: only `shopify_connector_inventory_service.py` and `test_inventory_push_mechanics.py` changed this cycle (`git status --short` confirms exactly these two) | EXECUTED — PASS |
| Receiver/argument-aware `error_class` vocabulary guard: every emission site resolves to one of the frozen nine constants (51 call sites inspected) | EXECUTED — PASS (standalone script + encoded test) |
| Guard non-vacuity: the same resolution logic rejects a synthetic `SUBREASON_DUPLICATE_RISK`-as-error_class snippet and an unknown literal, while accepting `duplicate_risk` in the subreason position | EXECUTED — PASS |
| Every `_fail_closed_pre_c2` call site supplies one of the nine constants directly (14 call sites inspected) | EXECUTED — PASS |
| `_prepare_preconditions_activate` calls `_read_shopify_inventory_pair` and can raise `InventoryActivationSupersededError` | EXECUTED — PASS |
| No synthetic `'%s:%s'` InventoryLevel-GID pattern anywhere in the module | EXECUTED — PASS |
| `_binding_push_admission_blocked` referenced exactly 6 times (1 definition + 5 call sites: `_try_enqueue_push_sync`, `_handle_inventory_push_sync` top-of-handler, both handoff-A branches under lock, CAS-replacement branch, reconciliation-replacement branch ×2) | EXECUTED — PASS |
| `_handle_inventory_push_sync` calls `binding.try_lock_for_update()` exactly twice (unchanged from cycle 2; the new lock-time gate re-check adds no new lock acquisition) | EXECUTED — PASS |
| `_handle_inventory_push_sync`'s no-op branch writes both `last_pushed_available`/`last_pushed_at` | EXECUTED — PASS |
| `_create_inventory_job`'s signature has no `cas_retry_ordinal` parameter; `_create_cas_successor_job` exists | EXECUTED — PASS |
| No `user_error_codes` string appears as a functional evidence key anywhere in the module (only in two explanatory comments describing what was replaced) | EXECUTED — PASS |
| `_validate_structured_user_errors` used at both classification call sites | EXECUTED — PASS |
| `_is_valid_set_quantities_success` requires non-empty `expected_reason`/`expected_reference_uri` before comparison | EXECUTED — PASS |
| `_reconcile_set_quantities` has an explicit `not read['level_exists']` branch before the generic current/target comparison | EXECUTED — PASS |

These checks were run directly against the corrected committed source in
this workspace (plain Python 3.11; no Odoo installation is available
here), both as standalone verification scripts and as the equivalent
assertions now encoded in `test_inventory_push_mechanics.py`'s own
static/AST guard tests. All static/AST guards from cycle 2 were
re-verified unchanged/still green (not re-tabulated here to avoid
duplicating §8/§9 of the cycle-2 record, preserved in git history at
commit `7979134f76e275c3d60dfc30b2561b754f0b94c4`).

## 4. Adversarial self-review — findings and disposition

Every corrected path was reviewed against its adversarial branch
(malformed input, missing identity, duplicate evidence, conflicting
identity, concurrent/repeated recovery, unauthorized caller, no-op then
second scan, ordinal ceiling, malformed error container, absent level
during reconciliation):

| Correction | Adversarial case tested | Result |
| --- | --- | --- |
| Group A | Terminal-but-unresolved existing reconciliation job (new adversarial case beyond the direct fix) | `_ensure_reconciliation_job`'s existing-job branch now correctly emits `data_shape_schema_mismatch`/`duplicate_risk`; proven by the guard's non-vacuity self-test plus the pre-existing `test_shared_reconciliation_identity_idempotent_on_reuse` (unaffected, still passes). |
| Group B | Repeated/concurrent `_recover_activation_superseded` calls for the same job | Second call finds `job.state != 'running'` (already `skipped`) and returns without creating a duplicate successor — mirrors the sibling seam's own idempotency guard exactly. |
| Group B | Concurrent writer changes `binding.shopify_gid` between the pre-C2 read and the recovery seam's own fresh lock | Fails safe: the seam only captures the GID when the freshly re-locked binding is *still* empty at write time; a late-arriving conflict is simply not captured this pass (no incorrect data written, no corruption) — documented here as an accepted narrow race, not a defect. |
| Group C | Binding flagged `review` between the orchestration handler's initial unlocked gate check and the handoff's row lock (TOCTOU) | Closed this cycle: both handoff branches re-check `_binding_push_admission_blocked` on the freshly locked binding before terminalizing; proven by `test_review_flagged_after_unlocked_check_blocks_before_child_creation`, which flips status to `review` inside a patched `try_lock_for_update`. |
| Group C | Conflicting GID observed post-mutation-success (cannot block, mutation already happened) | Preserves the existing GID, flags `status='review'`, creates no successor, logs a warning — proven by `test_activate_success_conflicting_gid_flags_review_not_overwrite` (now also asserting no successor job exists) and the pre-existing set-quantities equivalent. |
| Group D | Second scan after the no-op baseline is recorded | `test_verified_noop_baseline_prevents_endless_rescan` proves exactly one `inventory_push_sync` job exists after two scan passes. |
| Group E | Ordinal ceiling (3→4 denied); wrong job_type (activate) | `test_create_cas_successor_job_denies_at_ceiling`, `test_create_cas_successor_job_requires_set_quantities_job_type`. |
| Group E | Generic creator cannot accept the removed parameter | `test_create_inventory_job_rejects_cas_ordinal_kwarg` (`TypeError`). |
| Group F | Malformed `code`/`field` entries (missing code, non-string field parts, non-dict entry, non-list container) for both mutations | `test_set_quantities_malformed_user_error_entry_is_ambiguous`, `test_set_quantities_user_errors_not_a_list_is_ambiguous`, `test_set_quantities_non_string_field_entry_is_ambiguous`, `test_activate_malformed_user_error_entry_is_ambiguous`. |
| Group F | CAS release with the stale code among *other* unrelated codes | `any(...)` matching (an exact entry, not exclusive membership) is intentional and correct per the review's own "an exact entry whose code equals" wording. |
| Group G | Duplicate `available` entries; item/location identity mismatch in the real (non-mocked) read path | `test_read_pair_rejects_duplicate_available_entries`, `test_read_pair_rejects_item_identity_mismatch`, `test_read_pair_rejects_level_location_identity_mismatch`, exercised through a mocked transport rather than mocking `_read_shopify_inventory_pair` itself, so the real validation logic runs. |
| Group G | Absent level during set-quantities reconciliation | `test_reconcile_set_quantities_absent_level_routes_location_missing`. |

No adversarial case surfaced an uncorrected defect except the one narrow,
fails-safe race documented under Group B above, which is not a
correctness defect (no incorrect state is ever written).

## 5. Claim verification

| Claim | Classification |
| --- | --- |
| All seven correction groups implemented | EXECUTED — PASS (static/AST-verified; see §3) |
| Adversarial self-review complete, table produced | EXECUTED — PASS (§4) |
| `python3 -m py_compile`/`pyflakes`/`git diff --check` on changed files | EXECUTED — PASS |
| Every `TransactionCase`-based test in `test_inventory_push_mechanics.py` (including ~50 new/corrected methods this cycle) | IMPLEMENTED — ODOO EXECUTION PENDING (no Odoo/PostgreSQL runtime in this workspace) |
| `TestInventoryPreC2RecoverySeam`'s genuine independent-connection tests (including the new activation-superseded fixture) | IMPLEMENTED — ODOO EXECUTION PENDING |
| Module installation, same-SHA update, full connector regression | NOT PROVEN — requires Odoo.sh |
| Genuine separate-process concurrency proof (DEC-037 §5.3/§5.4, LL-006/LL-007) | NOT PROVEN — requires a child-process-capable runner |
| Dev-store mutation evidence | NOT PROVEN — no dev-store credentials in this workspace |
| Zero known implementation defect in the corrected code | EXECUTED — PASS at the static/adversarial-review level for this cycle's seven groups; the prior cycle's five other named-defect corrections (missing-item routing, non-committing pre-C2, strict-integer evidence for direct-success cases already covered, shared reconciliation identity, PII redaction, location-sync validation) are unchanged and were not reopened this cycle. |

No claim in this document is asserted as "test passed" where only "test
written" is true. No single-transaction test is described as a
concurrency proof.

## 6. D-013-1 .. D-013-9 traceability

Unchanged structurally from cycle 2's record (git history at
`7979134f76e275c3d60dfc30b2561b754f0b94c4`), except: D-013-3 (push
mutation mechanics) and D-013-7 (concurrency/CAS lineage) now also
reflect this cycle's Group B/C/D/E/F/G corrections in
`_prepare_preconditions_activate`, `_handle_inventory_push_sync`,
`_create_cas_successor_job`, and `_classify_direct_set_quantities`/
`_classify_direct_activate`.

## 7. Test-quality cleanup this cycle

Corrected false-green fixtures directly related to the seven groups
(comment `5029906989` §7):

- Three `_prepare_preconditions_set_quantities` mocks used a float
  `available` (`3.0`) that fed unvalidated into `change_from_quantity`
  — now `3` (int), matching the new defensive strict-integer boundary
  check (Group G).
- `test_explicit_activation_available_zero` called
  `_prepare_preconditions_activate` with no mock of
  `_read_shopify_inventory_pair` at all — now mocks a `level_exists:
  False` fresh read, matching Group B's new fresh-read requirement.
- `test_set_quantities_success_rejects_mismatched_quantity_after_change`/
  `test_set_quantities_success_accepts_matching_evidence` had no
  `reason`/`referenceDocumentUri` keys at all (both effectively
  `None == None`) — the exact false-green pattern comment `5029906989`
  item 8 names. Corrected to supply matching non-empty values; a new
  `test_set_quantities_success_rejects_missing_reason_and_uri` covers
  the case those two tests previously left uncovered.
- Four CAS-exhaustion release fixtures used the removed free-form
  `evidence={'user_error_codes': [...]}` shape — corrected to the
  frozen structured `evidence={'user_errors': [{'code': ..., 'field':
  []}]}` shape.

## 8. Odoo/PostgreSQL-dependent tests — IMPLEMENTED, EXECUTION PENDING EXTERNAL ENVIRONMENT

No Odoo or PostgreSQL runtime is available in this implementation
workspace. `test_inventory_push_mechanics.py` (the only test file
changed this cycle) was extended with focused coverage for all seven
groups and the adversarial cases in §4; none of it was executed here.
Cycle 2's already-implemented coverage in the other five test files is
unaffected and remains equally execution-pending.

## 9. Odoo.sh evidence — PENDING (not available in this workspace)

Unchanged from cycle 2: fresh clean installation, same-SHA update, the
focused Task 013 suite, full connector regression, and residue
inspection all require a dedicated Odoo.sh session and are not claimed
here. This correction cycle did not begin any Odoo.sh run.

## 10. Dev-store evidence — PENDING (not available in this workspace)

Unchanged from cycle 2: no dev-store credentials or Shopify runtime
authorization in this session. No real Shopify mutation, and no new
Shopify read, occurred during this correction cycle.

## 11. External child-process concurrency proof — PENDING (not available in this workspace)

Unchanged from cycle 2: per `docs/05-qa/runtime-lessons-learned.md`
LL-006/LL-007/LL-014, the genuine separate-OS-process,
independent-Odoo-registry concurrency proof requires a
child-process-capable runner this workspace does not provide. This
remains mandatory before Task 013 final merge authorization.

## 12. Residue audit

No Odoo/PostgreSQL runtime executed in this session, so there is no
live-process residue to inspect. The new
`_durable_activation_fixture`/`_cleanup_activation_fixture` pair in
`TestInventoryPreC2RecoverySeam` mirrors the existing
fixture/cleanup pattern exactly (scoped DELETE statements against only
the rows that same test created); no credential, access token, or PII
literal appears anywhere in the diff.

## 13. Remaining external evidence required before final merge authorization

Unchanged from cycle 2:

1. Odoo.sh: fresh install, same-SHA update, focused Task 013 suite, full
   connector regression, residue inspection.
2. Genuine independent-registry, separate-process concurrency proof
   (DEC-037 §5.3/§5.4) on a child-process-capable runner.
3. Dev-store mutation evidence for the validation plan scenarios, or an
   explicit, recorded control-room disposition for any scenario found
   genuinely not-executable.

## 14. Explicit confirmations

- This PR remains **draft**, **unmerged**, and was **not marked ready
  for review** by this session.
- **No self-acceptance** occurred.
- **No self-merge** occurred.
- **No protected reference** (`main`, `Shopify-connector`,
  `checkpoint/core-r2-readonly-uat-2026-07-15`,
  `checkpoint/wave-2-order-import-2026-07-18`) was changed by this
  session.
- **No Task 013B work** occurred.
- **No Odoo.sh run** occurred.
- **No live Shopify mutation** occurred — no Odoo/Odoo.sh process ran in
  this workspace, so no live transport call of any kind (read or
  mutation) was possible.
