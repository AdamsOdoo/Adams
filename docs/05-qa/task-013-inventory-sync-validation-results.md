# Task 013 — Inventory Synchronization: Implementation Validation Results

- **Status: IMPLEMENTATION CANDIDATE FROZEN FOR INDEPENDENT REVIEW — NOT
  RUNTIME-PROVEN. Draft PR unmerged, not marked ready.**
- **Repository:** `AdamsOdoo/Adams`
- **Branch:** `claude/wave-3-task-013-2g0ul0` (harness-provisioned; see PR
  #182 body for the session-naming note against the locked prompt's
  `sol/wave-3-task-013-inventory-sync` name)
- **Draft PR:** [#182](https://github.com/AdamsOdoo/Adams/pull/182) →
  `mvp/program-integration`
- **Exact base SHA:** `mvp/program-integration` @
  `8f5f421e2110c2e805460ea75fb519e48013e0f7` (PR #181's merge commit)
- **Implementation worker for this session:** Claude Code. Both cited
  authority comments (PR #179 `5024473959`, `5024617526`) name GPT-5.6
  Sol as the implementation worker; this session's task prompt directed
  Claude Code to implement instead, which conflicts with `CLAUDE.md` §13
  / DEC-032. The conflict was raised and the requesting user explicitly
  confirmed proceeding before any code was written — recorded here for
  the control room's visibility, not a self-authorized role change.
- **Acceptance authority:** ChatGPT (product-owner control room). This
  session did not accept its own work, did not mark the PR ready, and
  did not merge.

## 1. Implemented scope

`addons/shopify_connector_inventory` (Full edition, LGPL-3; depends
`shopify_connector_core`, `shopify_connector_product`, `stock`):

- `shopify.connector.location.mapping` (D-013-1(a)): explicit
  Shopify-Location ↔ Odoo-internal-`stock.location` mapping, dual
  uniqueness, ancestor/descendant-overlap guard, internal-only domain
  (enforced server-side, not only as a UI field domain),
  company-consistency check, `push_enabled` control.
- `shopify.connector.inventory.level.binding` (D-013-1(b)): per
  (product-variant-binding, location-mapping) pair identity, dual
  uniqueness (the RA-019 identity plus the variant/location pair), the
  first-push preview/confirmation record, informational-only
  last-pushed/last-known/pending-target fields (no binding-owned
  idempotency key or params hash), and the public
  `action_recheck_inventory_pair(reason)` review-release action.
- `shopify.connector.inventory.service` (D-013-9, DEC-037 §4/§5/§9): the
  three-job model —
  - `inventory_push_sync`: read-only orchestration (no mutation, no
    `mutation.attempt` row), first-push/push-enabled/store-identity/
    tracked/drift gates, target derivation with negative-clamp, and
    enqueue of at most one mutation job per dispatch;
  - `inventory_activate` and `inventory_set_quantities`: each a
    standalone Layer 2 mutation job type (`job_type == mutation_domain`)
    registered on the existing `_get_reconciliation_strategies()` seam,
    each making at most one `mutation.attempt` for its entire lifetime;
  - the bounded 3-replacement CAS-stale chain and the reconciliation
    `not_applied` replacement, both implemented via the framework's
    `domain_callback` consequence action (atomic with the predecessor's
    `cancelled` transition, inside the same C3/reconciliation-consequence
    transaction Stage 0 already commits);
  - the review-release private helper (`_recheck_inventory_pair`),
    delegated to by the binding's public action;
  - the Shopify location-cache sync via the one named `sudo()`
    elevation this module introduces;
  - the `_check_mapped_location` readiness override;
  - the `odoo_event` (`stock.move._action_done`), `scheduled_sync`
    (`run_inventory_push_scan`, ir.cron), and `manual_sync`
    (`action_push_inventory_now`) trigger surfaces, plus coalescing via
    `pending_target_available`.
- `shopify.connector.store.settings` extension:
  `inventory_scheduled_sync_enabled`, `inventory_last_push_scan_at`.
- `security/ir.model.access.csv`, `data/shopify_connector_inventory_cron.xml`.
- Six test files (`tests/test_location_mapping.py`,
  `tests/test_inventory_level_binding.py`,
  `tests/test_inventory_first_push_guard.py`,
  `tests/test_inventory_push_mechanics.py`,
  `tests/test_inventory_triggers.py`,
  `tests/test_inventory_location_cache_sync.py`) — the exact six named
  in the locked prompt's allowed-file list.

**Zero core (`shopify_connector_core`), `shopify_connector_product`, or
`shopify_connector_sale` files were created or modified.** Every
extension uses the existing, unmodified seams: `job_type`
`selection_add` + `ondelete={... : lambda recs:
recs._reassign_to_historic_job_type()}`; `_domain_flag_for_job_type`;
`_get_handlers`/`_get_replay_policies`/`_get_reconciliation_strategies`
on `shopify.connector.job.dispatch`; `_check_mapped_location` on
`shopify.connector.readiness.check`; `_action_done` on `stock.move`
(a standard Odoo model, not a connector core file).

## 2. Pre-freeze audit correction applied

The pre-freeze completeness audit (locked prompt §31/task instructions
§31) found one genuine correctness gap, corrected in this same batch
before freezing: `_transport_set_quantities`/`_transport_activate`
originally read a caught `ShopifyClientError`'s `.error_class`
attribute directly and passed it straight through into the returned
transport result. `ShopifyClientError` carries the full core-wide
16-value `error_class` registry (e.g. `shopify_permission_scope_auth`),
which core's own generic consequence validator (`REGISTERED_ERROR_CLASSES`)
would have accepted, but which is **not** one of this domain's fixed
nine-value vocabulary (DEC-037 §7/§9) — an unlikely-but-possible auth
failure mid-mutation would otherwise have leaked an out-of-vocabulary
value past this module's own governing contract undetected by the
static AST guard (which only scans for literal string constants, not
values read dynamically off an exception attribute). Fixed by adding
`_normalize_transport_error_class(exc)`, the single point both
transport methods now go through: it maps any exception's `error_class`
onto this module's fixed set, defaulting any value outside it to
`shopify_temporary_server_network` (uncertain, reconcile-first) —
never silently passed through, never defaulted to an automatic retry.

## 3. One implementation-level judgment call

DEC-037 §7 states "No new job type is added for reconciliation reads."
However, `shopify.connector.job`'s existing
`_check_reconciliation_attempt_link` constraint structurally requires
every mutation domain's `reconciliation_job_type` to resolve to a real,
dispatchable `job_type`, and the two existing core reconciliation-shaped
values (`mutation_dispatch_selftest`, `mutation_dispatch_selftest_reconcile`)
are explicitly commented "core/diagnostic-only... never a template for a
future domain job_type." Given that, this implementation adds exactly
**one** new shared `job_type`, `inventory_mutation_reconcile`, used by
both `inventory_activate` and `inventory_set_quantities`; its handler
dispatches purely on the attempt's own `mutation_domain`, mirroring
core's own generic reconciliation-handler shape exactly (no
domain-specific logic is baked into the job_type itself). This is a
documentation-vs-code precision gap, not a re-opened architecture
decision, and stays entirely within this module's own allowed files. It
is called out here per the pre-freeze audit requirement, not treated as
a silent deviation.

## 4. Known limitation carried from the existing Stage 0 architecture

`shopify.connector.job`'s `PROTECTED_JOB_FIELDS` frozenset (core file,
not modified by this task) does not include `cas_retry_ordinal`, the one
new field this task adds via `_inherit`. This means a user holding the
existing `Operator` role's generic `job` create permission could in
principle set `cas_retry_ordinal` directly through a bare `create()`
call rather than through this module's own sanctioned job-creation path.
This module never itself creates a job that way, and the value only
affects the bounded-replacement counter/review-release eligibility (it
is never transport-replay or idempotency authority — that remains
exclusively `shopify.connector.mutation.attempt`, unaffected). Extending
`PROTECTED_JOB_FIELDS` itself would require modifying the core job
model file, which is forbidden for this task. Flagged here as an
inherited architecture characteristic, not a defect introduced by this
implementation, and not exploitable to cause an unauthorized Shopify
mutation.

## 5. D-013-1 .. D-013-9 traceability

| Decision | Implemented in | Tests |
| --- | --- | --- |
| D-013-1(a) location mapping | `shopify_connector_location_mapping.py` | `test_location_mapping.py` |
| D-013-1(b) inventory-level binding | `shopify_connector_inventory_level_binding.py` | `test_inventory_level_binding.py` |
| D-013-2 quantity source + clamp | `_refresh_pending_target` (service) | `test_inventory_triggers.py`, `test_inventory_push_mechanics.py` |
| D-013-3 push mutation mechanics (Gate B corrected) | `_prepare_preconditions_set_quantities`, `_apply_consequence_set_quantities` (service) | `test_inventory_push_mechanics.py` |
| D-013-4 first-push guard | `first_push_state`/`action_confirm_first_push` (binding), `_handle_inventory_push_sync` gate (service) | `test_inventory_first_push_guard.py` |
| D-013-5 location cache + readiness | `_handle_inventory_location_sync`, `_check_mapped_location` override (service) | `test_inventory_location_cache_sync.py` |
| D-013-6 job granularity + triggers (Gate B corrected) | `_enqueue_from_stock_moves`, `run_inventory_push_scan`, `action_push_inventory_now` (service) | `test_inventory_triggers.py` |
| D-013-7 concurrency | `operation_scope_key` pair-serialization (existing core mechanism, this domain's value) | `test_inventory_push_mechanics.py` (unit-level); genuine concurrency proof pending, §7 below |
| D-013-8 baseline import split out | Not implemented (explicitly Task 013B scope; zero Task 013B code in this diff) | N/A |
| D-013-9 Layer 2 integration (Gate B corrected) | `_get_reconciliation_strategies`/`_get_handlers`/`_get_replay_policies` extensions, three-job model (service) | `test_inventory_push_mechanics.py` |

## 6. DEC-037 §4/§9 matrix traceability

Every row of DEC-037 §4 (both mutation domains) and §9 (the
job/mutation-consequence contract) is implemented in
`_classify_direct_set_quantities`, `_classify_direct_activate`,
`_reconcile_set_quantities`, `_reconcile_activate`,
`_apply_consequence_set_quantities`, and `_apply_consequence_activate`.
No cell is left "TBD." The nine-value fixed `error_class` vocabulary
(DEC-037 §7) is used exclusively; the four withdrawn Revision-2 values
never appear (verified by a static/AST test in
`test_inventory_push_mechanics.py`).

## 7. Static and AST validation — EXECUTED (pure Python, no Odoo required)

| Check | Result |
| --- | --- |
| `python3 -m py_compile` on every new `.py` file | EXECUTED — PASS |
| `python3 -m pyflakes` on the whole module (no unused imports/names beyond expected package `__init__.py` re-exports) | EXECUTED — PASS |
| XML well-formedness (`xml.etree.ElementTree.parse`) on the cron data file | EXECUTED — PASS |
| CSV row-shape check (every access row has 8 fields matching the header) on `ir.model.access.csv` | EXECUTED — PASS |
| Allowed-file audit: `find addons/shopify_connector_inventory -type f` matches the locked prompt's exhaustive file list exactly, no extra file | EXECUTED — PASS |
| No `inventoryAdjustQuantities` string anywhere in the module | EXECUTED — PASS (standalone AST/substring check reproduced from the `test_inventory_push_mechanics.py` guard) |
| No `'committed'` string anywhere in the module | EXECUTED — PASS |
| No withdrawn `error_class` literal (`remote_validation_rejected`/`remote_precondition_mismatch`/`transport_ambiguous`/`clean_rejection`) anywhere in the module | EXECUTED — PASS |
| No `inventoryActivate` call site in any `*_set_quantities` strategy method, and no `inventorySetQuantities` call site in any `*_activate` strategy method | EXECUTED — PASS |
| No message-text (`.get('message')`/`['message']`) read in `_classify_direct_activate` | EXECUTED — PASS |

These checks were run directly against the committed source in this
workspace (a plain Python 3.11 interpreter; no Odoo installation is
available here) and their exact commands/output are reproducible from
this document's own git history.

## 8. Odoo/PostgreSQL-dependent tests — IMPLEMENTED, EXECUTION PENDING EXTERNAL ENVIRONMENT

No Odoo or PostgreSQL runtime is available in this implementation
workspace (confirmed at pre-edit audit; this is the environment
condition the binding continuation ruling, PR #179 comment `5024617526`,
explicitly says does not block implementation start). The following
were **implemented but not executed** here, and must not be represented
as passed until a genuine Odoo.sh or local-Odoo session runs them:

- Every `TransactionCase`-based test in the six test files (module
  installation, ORM-level assertions, ACL matrix, constraint
  enforcement, the CAS bounded-replacement chain, the review-release
  positive/negative matrix, reconciliation verdicts, trigger behavior,
  location-cache sync).
- Module installation and same-SHA update.
- Full connector regression (all existing Stage 0/product/sale suites)
  to confirm zero regression from this addon's registration on the
  shared `job_type`/`_get_handlers`/`_get_replay_policies`/
  `_get_reconciliation_strategies`/`_domain_flag_for_job_type` seams.
- Lifecycle/uninstall behavior (`_reassign_to_historic_job_type` via
  the seven new `job_type` `ondelete` callables).
- The genuine independent-PostgreSQL-connection concurrency proof for
  pair-serialization admission and atomic-handoff replacement-job
  creation (DEC-037 §5.3/§5.4) — this domain's proof extends Stage 0's
  own proven multi-connection technique onto the existing
  `_store_operation_scope_key_uniq` constraint this domain's
  `operation_scope_key` values (the `inventory_pair:{store}:{item}:
  {location}` literal, carried through `shopify_target_gid`) rely on;
  the harness/test code for this exists in `test_inventory_push_mechanics.py`
  at the unit level (asserting the DB-level admission/handoff behavior
  through the ORM directly) but the genuine separate-OS-process,
  independent-registry version (LL-006/LL-007) requires the
  child-process-capable runner this workspace does not have.

## 9. Odoo.sh evidence — PENDING (not available in this workspace)

Fresh clean installation, same-SHA update, the focused Task 013 suite,
full connector regression, and residue inspection all require a
dedicated Odoo.sh session and are not claimed here.

## 10. Dev-store evidence — PENDING (not available in this workspace)

This implementation session has no dev-store credentials or Shopify
runtime authorization. Dev-store validation plan scenarios 1–12, 17–19
(`docs/05-qa/wave-3-dev-store-mutation-validation-plan.md`) are not
executed. No real Shopify mutation, and no new Shopify read, occurred
during this implementation session.

## 11. External child-process concurrency proof — PENDING (not available in this workspace)

Per `docs/05-qa/runtime-lessons-learned.md` LL-006/LL-007/LL-014, the
genuine separate-OS-process, independent-Odoo-registry concurrency proof
requires a child-process-capable runner (writable `/dev/shm`,
multiprocessing semaphore/spawn support). This workspace does not
provide one. This remains mandatory before Task 013 final merge
authorization — no infrastructure waiver is claimed or implied.

## 12. Residue audit

No Odoo/PostgreSQL runtime executed in this session, so there is no
live-process residue to inspect (no idle-in-transaction connections, no
orphaned locks, no stray workers were possible to create here). A
source-level residue check was performed instead: no test fixture in
this module inserts raw SQL outside the ORM; no credential, access
token, or PII literal appears anywhere in the module (`grep`-equivalent
manual review of every new file); the module introduces exactly one new
`sudo()` site (`_handle_inventory_location_sync`), matching D-013-5's
"one named sudo" requirement and not increasing the existing
three-site core sudo inventory (this is a fourth site, but it lives in
this domain module, not in `shopify_connector_core`, so it is additive
to — not a violation of — the core-file sudo-site count core's own
tests enforce).

## 13. Remaining external evidence required before final merge authorization

1. Odoo.sh: fresh install, same-SHA update, focused Task 013 suite, full
   connector regression, residue inspection.
2. Genuine independent-registry, separate-process concurrency proof
   (DEC-037 §5.3/§5.4) on a child-process-capable runner.
3. Dev-store mutation evidence for scenarios 1–12, 17–19 of the
   validation plan, or an explicit, recorded control-room disposition
   for any scenario found genuinely not-executable.

## 14. Explicit confirmations

- This PR remains **draft**, **unmerged**, and was **not marked ready
  for review** by this session.
- **No self-acceptance** occurred.
- **No self-merge** occurred.
- **No protected reference** (`main`, `Shopify-connector`,
  `checkpoint/core-r2-readonly-uat-2026-07-15`,
  `checkpoint/wave-2-order-import-2026-07-18`, `mvp/program-integration`
  prior to this PR's own eventual merge) was changed by this session.
- **No Task 013B work** occurred (no baseline-import code, no
  Shopify→Odoo stock write, zero files under any Task 013B naming).
- **No unauthorized Shopify mutation** occurred — no Odoo/Odoo.sh
  process ran in this workspace, so no live transport call of any kind
  (read or mutation) was possible.
