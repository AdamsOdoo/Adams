# Locked Sol Wave 3 Task 013B Implementation Prompt — Controlled Initial Inventory Baseline

> **ISSUED-NOT-EXECUTED: NO**
> **LOCKED: YES**
> **NOT USABLE UNTIL SEPARATE CONTROL-ROOM ISSUANCE.** This prompt is a
> draft, ready-to-copy template prepared during the Wave 3 Gate B session
> (2026-07-19; a Revision 2 cross-reference-only correction, same date,
> reflects Task 013's corrected three-job model — this task's own
> content and Layer-2-non-applicability are unaffected; a Revision 3
> cross-reference/role-model-only correction, same date, per control-room
> comment `5015830229` — the ROLE section below is corrected to the
> current role model; this task's own content is otherwise unaffected),
> per
> [DEC-037](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) §8 and the
> corrected
> [Task 013B packet](../07-implementation-plan/task-013b-initial-inventory-baseline-packet.md).
> It has not been issued to any Sol session. It must not be issued until
> **all** of the following are true:
>
> 1. This Gate B package (DEC-037) is **accepted and merged**.
> 2. **Task 013 itself is merged into `mvp/program-integration` and
>    runtime-proven** (D-013B-8: "After Task 013 (needs its models,
>    mappings, and first-push guard vocabulary)") — Task 013B may not be
>    issued before Task 013's own wave review is complete.
> 3. The exact base SHA below is re-verified live immediately before
>    issuance, on the post-Task-013-merge `mvp/program-integration` tip.
> 4. Independent Claude control-room verification that Task 013B still
>    carries no contradiction against the (by-then-implemented) Task 013
>    module is recorded complete.
>
> **Do not run this prompt in the same session that authored it. Do not
> run it now, regardless of how complete it reads.**

---

## Paste-ready prompt (draft — not issued)

```text
REPOSITORY: AdamsOdoo/Adams

EXACT STARTING SHA (mvp/program-integration): <EXACT_POST_TASK013_SHA_AT_ISSUANCE>
(fill this placeholder with the exact live mvp/program-integration tip,
verified AFTER Task 013 has merged, at the moment this prompt is actually
handed to a Sol session — verify it live from GitHub immediately before
issuance; do not reuse any SHA recorded in this document's own authoring
session, and do not let any repository commit occur between that
verification and issuance)

WORKING BRANCH TO CREATE: sol/wave-3-task-013b-inventory-baseline

PULL REQUEST: open one early DRAFT pull request from
sol/wave-3-task-013b-inventory-baseline into mvp/program-integration,
titled "Task 013B: controlled initial inventory baseline import".

======================================================================
ROLE
======================================================================

You are GPT-5.6 Sol, the primary autonomous research/implementation
worker for this MVP program (DEC-032). ChatGPT is the strategic control
room and the acceptance authority for this wave. Claude is the planner,
independent reviewer, and Odoo.sh runtime verifier — Claude reviews your
diff and independently verifies your runtime evidence after you freeze
your candidate, and may perform a controlled merge of your wave PR only
after explicit ChatGPT authorization; Claude is not the control room and
is not the sole or default merge authority (corrected, Revision 3,
control-room comment `5015830229` binding correction 6 — every prior
statement to the contrary is withdrawn). You do not merge your own PR.
You do not mark this PR ready for review.

======================================================================
IDENTITY GATE (verify before writing any code)
======================================================================

1. This prompt's own issuance checklist (below) is fully satisfied.
2. mvp/program-integration points exactly to the SHA above.
3. Task 013 (shopify_connector_inventory: location mapping, level
   binding, first-push guard, inventory_set_quantities/inventory_activate
   push mechanics) is merged and runtime-proven at this SHA.
4. DEC-037 §8 and this prompt's own file list agree with the current
   docs/07-implementation-plan/task-013b-initial-inventory-baseline-packet.md
   text — if either has been revised since this prompt was authored,
   STOP and report the discrepancy.
5. Branch sol/wave-3-task-013b-inventory-baseline does not already exist.
6. No open Task 013B PR already exists.
7. Protected refs unchanged from their recorded values.

======================================================================
MANDATORY PRE-EDIT CLAUSE (verbatim — do not paraphrase or skip)
======================================================================

"Before editing, perform a complete code, dependency, caller, test,
source-guard, migration, security and runtime-access preflight for the
entire wave. Resolve all implementation-level issues before coding. If a
genuine product decision is required, report all known blockers together
in one consolidated hard stop. Do not stop repeatedly for isolated issues
that could have been discovered during the initial audit."

======================================================================
OBJECTIVE
======================================================================

Implement Task 013B — controlled initial Shopify->Odoo inventory
baseline — exactly per
docs/07-implementation-plan/task-013b-initial-inventory-baseline-packet.md
(D-013B-1..8 binding, including new §0's explicit Layer-2-non-applicability
statement).

======================================================================
EXPLICIT LAYER-2-NOT-APPLICABLE STATEMENT (verbatim — do not deviate)
======================================================================

This task issues ZERO Shopify mutations. Its only Shopify calls are
READS (inventoryLevel.quantities), classified remote_read_replay_safe
under the existing, UNCHANGED Layer 1 replay-policy registry. DEC-036's
mutation-attempt model, C1/C2/NET/C3 protocol, and reconciliation
contract DO NOT APPLY to this task — do not create a mutation.attempt
row, do not register a mutation_domain, do not call the Layer 2 wrapper
anywhere in this task's code. Do not add a Layer 2 mutation wrapper
"for symmetry" with Task 013 — this task has no Shopify-mutation risk
for Layer 2 to manage. This task's safety contract is entirely a LOCAL
Odoo transaction/locking concern (database-backed row locking, re-read
under lock, drift/topology abort, post-write verification) — unrelated
to Shopify Layer 2 reconciliation.

======================================================================
ALLOWED FILES (exhaustive)
======================================================================

addons/shopify_connector_inventory/models/shopify_connector_inventory_baseline.py
  (NEW — run model + preview/confirm/apply services + job seams)
addons/shopify_connector_inventory/models/shopify_connector_inventory_level_binding.py
  (the two stamp fields only: baseline_applied_at, baseline_run_id)
addons/shopify_connector_inventory/models/__init__.py (import line)
addons/shopify_connector_inventory/security/ir.model.access.csv
  (run-model rows only)
addons/shopify_connector_inventory/tests/test_inventory_baseline_preview.py (NEW)
addons/shopify_connector_inventory/tests/test_inventory_baseline_guard.py (NEW)
addons/shopify_connector_inventory/tests/test_inventory_baseline_apply.py (NEW)
addons/shopify_connector_inventory/tests/test_inventory_baseline_run_model.py (NEW)
addons/shopify_connector_inventory/tests/__init__.py (import lines)
docs/05-qa/task-013b-validation-results.md (NEW)
docs/05-qa/architecture-review-log.md (append one AR row)
docs/01-research/research-handoff.md (top entry)

======================================================================
FORBIDDEN FILES
======================================================================

Every core/product/sale/fulfillment/product_export file; every existing
Task 013 push/mapping/first-push file beyond the two named stamp fields
above; any Shopify mutation call site anywhere (this task is read-only
toward Shopify — enforced by a source guard); any standing pull/cron for
baseline (one-time, per-pair, replay-guarded only); lot/serial adjustment
logic; UI/webhooks/OAuth/CI; adams_base; main; plain dev; protected
references. Any shopify_connector_core/** file (this task does not touch
Layer 2 at all — there is nothing in core for it to extend).

======================================================================
HARD CONSTRAINTS
======================================================================

- preview -> explicit reviewer/admin confirmation -> apply, no other
  path, no auto-apply, no bypass.
- One baseline per pair, with recorded re-inclusion override only.
- Verify the exact 19.0 stock.quant counted-quantity/apply API and the
  exact 19.0 try_lock_for_update() equivalent against source before use
  — STOP and report if either differs from this packet's assumption (no
  improvisation).
- Clamp negative remote Shopify available values to 0 with a note before
  computing desired_free.
- Lot-tracked products (tracking != 'none') -> blocked_manual_review;
  never adjusted.
- Multiple quants at one [product, location], or any quant with a
  non-empty owner_id/package_id -> fail closed (blocked_manual_review),
  never a guessed split or an adjustment of third-party/packaged stock.
- Prior on-hand + reserved quantities recorded for every write (the
  documented manual-undo path).
- Quantity semantics: Shopify 'available' == Odoo location-context
  free_qty (never on-hand); because an inventory adjustment sets COUNTED
  ON-HAND, the target is
  target_on_hand = desired_shopify_available + current_reserved_quantity,
  verified after write by resulting free_qty == desired_shopify_available
  (else roll back to blocked_manual_review/binding_conflict with the
  full quantity breakdown).
- The apply step takes a DATABASE ROW LOCK (try_lock_for_update() —
  verify the exact 19.0 method against source before use) on every
  dependent stock.quant / inventory.level.binding / location.mapping /
  variant.binding row BEFORE the final re-read; fails closed
  (destructive_write_guard_blocked) if any required row cannot be
  locked; then re-reads on-hand/reserved/mapping/binding UNDER THE LOCK
  and ABORTS on any value or quant-topology drift from the confirmed
  preview snapshot (re-reading alone is NOT a race guard —
  operation_scope_key serializes only connector jobs, not ordinary Odoo
  stock moves).
- No-existing-quant case: lock the existing binding/mapping rows and
  create the quant via the standard adjustment API — never pre-insert a
  bare quant row to lock.
- A REAL concurrent-transaction test proves a competing
  reservation/quant change is either serialized correctly or aborted —
  never a silently wrong free_qty.
- 'committed' never written or read for writing (RA-018 source guard
  re-run over this module too).
- No autonomous or standing baseline import — one operator-confirmed run
  per pair, ever; no replay after a successful apply (stamp-checked,
  destructive_write_guard_blocked on mismatch).
- Concurrency caveat (SRR-03/04/09-class) restated, not newly resolved.
- Exact interaction with Task 013 (verbatim, DEC-037 §8, cross-reference
  updated Revision 2): Task 013 must already be installed and accepted; a
  baseline apply for a pair blocks any concurrent Task 013 job for that
  same pair — now any of Task 013's three inventory job types
  (inventory_push_sync, inventory_activate, inventory_set_quantities),
  since Revision 2 gives all three the same pair-serialization
  operation_scope_key (DEC-037 §5.3); after a successful baseline, Odoo
  becomes the standing authority for that pair and the next Task 013
  push begins from the accepted baseline state.
- No Layer 2 mutation wrapper is added to this task for symmetry with
  Task 013 (restated from the explicit statement above — do not deviate
  even if it looks more "consistent" to add one).
- No self-merge; do not mark this PR ready for review; stop after the
  draft PR and your own validation-results/AR/handoff commits.

======================================================================
RESIDUE AUDIT
======================================================================

Zero orphaned row locks after any apply sequence (success, abort, or
drift-detected path); zero partially-applied baselines (either the full
target_on_hand write and its verification both complete, or nothing is
written); zero duplicate applies for a stamped pair without an explicit,
recorded re-inclusion override.

======================================================================
ROLLBACK NOTES
======================================================================

Technical: revert the single PR (schema: run model + two stamp fields —
additive, no data migration). Operational (documented in the run record
and release plan): every adjustment is reversible by a counter-adjustment
from the recorded prior quantities — the run record contains the exact
per-pair prior values, so "undo the baseline" is a documented manual
procedure with complete data, never an automatic write.

======================================================================
DEFINITION OF DONE
======================================================================

- Every D-013B-1..8 decision implemented exactly as specified.
- The explicit Layer-2-not-applicable statement holds: zero
  mutation.attempt rows, zero mutation_domain registrations, zero Layer 2
  wrapper calls anywhere in this task's diff.
- Static, unit, and a REAL (genuine independent-connection) concurrency
  test proving the row-lock + drift-abort contract, green.
- Odoo.sh fresh-install + focused-class + full regression + residue
  audit green.
- Dev-store validation plan
  (docs/05-qa/wave-3-dev-store-mutation-validation-plan.md) scenarios
  13-16 executed with redacted evidence in
  docs/05-qa/task-013b-validation-results.md, OR a recorded, explicit
  control-room waiver with reason stated.
- mvp-program-state.md, mvp-acceptance-matrix.md, and
  research-handoff.md updated.
- Zero code touching shopify_connector_core/** anywhere in the diff.

======================================================================
STOP CONDITIONS (hard stops — consolidate and report, do not proceed
past any of these)
======================================================================

1. Task 013 is found not actually merged/runtime-proven at issuance
   time, despite this prompt asserting it is.
2. Any code path found that would call a Shopify mutation, register a
   mutation_domain, or create a mutation.attempt row — this task must
   never do any of these.
3. The exact 19.0 stock.quant adjustment API or row-locking primitive
   differs from this packet's assumption.
4. Any attempted change to a forbidden file (including any
   shopify_connector_core/** file).
5. Any attempted change to a protected reference.
6. Genuine dev-store baseline evidence proves unobtainable — escalate,
   do not substitute simulation.
7. Every Wave-3-DoR program-level hard stop (1-10) applies verbatim.
```

---

## Issuance checklist (for the control-room session that eventually issues this)

- [ ] This Gate B package (DEC-037) is ACCEPTED and MERGED.
- [ ] Task 013 is MERGED into `mvp/program-integration` and
      runtime-proven (both mutation domains' dev-store evidence
      accepted).
- [ ] `<EXACT_POST_TASK013_SHA_AT_ISSUANCE>` is replaced with a
      live-verified `mvp/program-integration` tip taken **after** the
      Task 013 merge.
- [ ] This prompt's file list still matches the then-current Task 013B
      packet text (re-diff before use).
- [ ] The issuing session is not the session that authored or corrected
      this prompt.
- [ ] Independent Claude verification that Task 013B remains free of any
      contradiction against the now-implemented Task 013 module is
      recorded complete.
