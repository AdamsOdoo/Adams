# Locked Sol Wave 3 Task 013 Implementation Prompt — Inventory Synchronization

> **ISSUED-NOT-EXECUTED: NO**
> **LOCKED: YES**
> **NOT USABLE UNTIL SEPARATE CONTROL-ROOM ISSUANCE.** This prompt is a
> draft, ready-to-copy template prepared during the Wave 3 Gate B session
> (2026-07-19; corrected to Revision 2, same date, per control-room
> comment `5015619162` on PR #179 — the job model below is now three
> standalone job types, not one job owning two sequential attempts), per
> [DEC-037](../04-decisions/DEC-037-wave-3-inventory-gate-b.md) and the
> corrected
> [Task 013 packet](../07-implementation-plan/task-013-inventory-sync-implementation-packet.md).
> It has not been issued to any Sol session. It must not be issued until
> **all** of the following are true:
>
> 1. This Gate B package (DEC-037 and its companion document corrections)
>    is **accepted and merged** by the product owner + ChatGPT control
>    room — not by the session that authored it.
> 2. **Wave 3 Stage 0** (the DEC-036 Layer 2 core substrate) is **merged
>    into `mvp/program-integration` and runtime-proven** (all four
>    DEC-036 D38 proof-environment layers green, per the Stage 0 packet
>    §18 Definition of Done) — per the sequencing guard in PR #177
>    comment `5015174971`: "Task 013 implementation remains forbidden
>    until Gate B is accepted **and** Stage 0 is merged and
>    runtime-proven."
> 3. The exact base SHA below is re-verified live immediately before
>    issuance, on the post-Stage-0-merge `mvp/program-integration` tip.
> 4. Independent Claude control-room verification of this prompt's
>    file-list/sequence against the then-current Task 013 packet and
>    DEC-037 text is recorded complete (the packet or DEC-037 may have
>    been further revised between this prompt's authoring and its
>    issuance).
>
> **Do not run this prompt in the same session that authored it. Do not
> run it now, regardless of how complete it reads.**

---

## Paste-ready prompt (draft — not issued)

```text
REPOSITORY: AdamsOdoo/Adams

EXACT STARTING SHA (mvp/program-integration): <EXACT_POST_STAGE0_SHA_AT_ISSUANCE>
(fill this placeholder with the exact live mvp/program-integration tip,
verified AFTER Wave 3 Stage 0 has merged, at the moment this prompt is
actually handed to a Sol session — verify it live from GitHub immediately
before issuance; do not reuse any SHA recorded in this document's own
authoring session, and do not let any repository commit occur between
that verification and issuance)

WORKING BRANCH TO CREATE: sol/wave-3-task-013-inventory-sync

PULL REQUEST: open one early DRAFT pull request from
sol/wave-3-task-013-inventory-sync into mvp/program-integration, titled
"Task 013: Shopify inventory synchronization (shopify_connector_inventory)".

======================================================================
ROLE
======================================================================

You are GPT-5.6 Sol, the primary autonomous research/implementation
worker for this MVP program (DEC-032). Claude is the control room and
the only party authorized to merge your wave PR, and independently
verifies your runtime evidence after you freeze your candidate. You do
not merge your own PR. You do not mark this PR ready for review.

======================================================================
IDENTITY GATE (verify before writing any code)
======================================================================

1. This prompt's own issuance checklist (below) is fully satisfied —
   if you were handed this prompt without that checklist being visibly
   satisfied, STOP and report it as a hard stop; do not proceed on the
   assumption that issuance implies the checklist passed.
2. mvp/program-integration points exactly to the SHA above.
3. Wave 3 Stage 0 is merged into mvp/program-integration (search the
   commit history for the Stage 0 merge commit; confirm
   shopify.connector.mutation.attempt and the C1/C2/NET/C3 wrapper exist
   in addons/shopify_connector_core/models/).
4. DEC-037 and this prompt's own file list agree with the current
   docs/07-implementation-plan/task-013-inventory-sync-implementation-packet.md
   and docs/04-decisions/DEC-037-wave-3-inventory-gate-b.md text — if
   either has been revised since this prompt was authored, STOP and
   report the discrepancy rather than silently reconciling it yourself.
5. Branch sol/wave-3-task-013-inventory-sync does not already exist.
6. No open Task 013 PR already exists.
7. Protected refs (main, Shopify-connector,
   checkpoint/core-r2-readonly-uat-2026-07-15, and every prior wave
   checkpoint) are unchanged from their recorded values.

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

Implement Task 013 — Shopify inventory synchronization — as the NEW
module addons/shopify_connector_inventory, exactly per
docs/07-implementation-plan/task-013-inventory-sync-implementation-packet.md
(D-013-1..9 binding, including the Gate B corrections: changeFromQuantity
CAS throughout, attempt-owned Layer 2 idempotency never binding-owned,
review-case-first drift handling, bounded 3-retry CAS-stale routing, and
D-013-9's Layer 2 integration) and
docs/04-decisions/DEC-037-wave-3-inventory-gate-b.md (the complete
inventorySetQuantities/inventoryActivate mutation-domain matrix, the
three-job model — §5 — and the consequence contract — §9).
**Revision 2 job model, binding:** `inventory_push_sync` is an
orchestration/read-only job (no Shopify mutation, no `mutation.attempt`
row); `inventory_activate` and `inventory_set_quantities` are each their
own standalone mutation job (`job_type == mutation_domain`). No job may
execute two Shopify mutations.

======================================================================
ALLOWED FILES (exhaustive)
======================================================================

addons/shopify_connector_inventory/** (NEW module):
  __init__.py
  __manifest__.py (depends: shopify_connector_core,
    shopify_connector_product, stock; LGPL-3)
  models/__init__.py
  models/shopify_connector_location_mapping.py (NEW — D-013-1(a))
  models/shopify_connector_inventory_level_binding.py (NEW — D-013-1(b),
    Gate B-corrected schema: NO last_push_idempotency_key,
    NO last_push_params_hash fields — those are retired, superseded by
    Layer 2's attempt-owned idempotency; only last_pushed_available,
    last_pushed_at, last_known_shopify_available as informational fields)
  models/shopify_connector_inventory_service.py (NEW — orchestration
    (inventory_push_sync)/preview service, job seams, hooks,
    location-cache sync with the ONE named sudo per D-013-5; the Layer 2
    wrapper integration per D-013-9 and DEC-037 §4/§5/§9 lives here —
    inventory_set_quantities and inventory_activate are each registered
    as their OWN standalone mutation job type (job_type ==
    mutation_domain), never combined; inventory_push_sync itself issues
    no Shopify mutation and enqueues at most one mutation job per
    dispatch; the fresh changeFromQuantity read into
    preconditions_snapshot at each mutation job's own C2; the
    pair-serialization admission/handoff mechanics per DEC-037 §5.3)
  models/shopify_connector_store_settings.py (the two new store settings
    per Task 013 §4: inventory_scheduled_sync_enabled,
    inventory_last_push_scan_at)
  security/ir.model.access.csv
  data/shopify_connector_inventory_cron.xml (NEW — push-scan cron,
    noupdate="1")
  tests/__init__.py
  tests/test_location_mapping.py (NEW)
  tests/test_inventory_level_binding.py (NEW)
  tests/test_inventory_first_push_guard.py (NEW)
  tests/test_inventory_push_mechanics.py (NEW — extended per DEC-037
    §4/§5/§9: CAS bounded-3-retry test (same-job redispatch, never a new
    job), fresh-CAS-pre-read-per-retry test, activation/set-quantities
    distinct-JOB test (distinct job_type/job ID/attempt_token/idempotency
    key, connected only by a fresh orchestration handoff — never two
    attempts inside one job), static/AST guard that no
    inventory_set_quantities code path calls inventoryActivate (and vice
    versa), job_type==mutation_domain invariant test, genuine
    independent-PostgreSQL-connection concurrency test proving duplicate
    phase jobs cannot be created for one pair, THROTTLED classification
    test, reconciliation applied/not-applied/inconclusive tests for BOTH
    mutation domains INCLUDING an ABA/freshness fixture (value changes
    away and back with a later updatedAt -> inconclusive, never
    not_applied), static/AST guard that no code path matches on
    UserError.message text for inventoryActivate classification,
    store-identity-mismatch test, explicit available:0 activation test,
    no-quantities-array-length->1 static guard)
  tests/test_inventory_triggers.py (NEW)
  tests/test_inventory_location_cache_sync.py (NEW)

docs/05-qa/task-013-inventory-sync-validation-results.md (NEW)
docs/05-qa/architecture-review-log.md (append one AR row)
docs/01-research/research-handoff.md (top entry)

======================================================================
FORBIDDEN FILES
======================================================================

Everything outside the list above. Specifically: every
shopify_connector_core/** file except through the existing, unmodified
_get_replay_policies()/_get_reconciliation_strategies() extension seams
(inheritance-only — do not modify shopify_connector_job.py,
shopify_connector_job_dispatch.py, shopify_connector_mutation_attempt.py,
shopify_connector_api_client.py, or any other Stage 0 file directly);
shopify_connector_product/**, shopify_connector_sale/** (except the
existing _get_checks()/_check_mapped_location inheritance seams named in
D-013-5); adams_base/**; views/UI/webhooks/OAuth/CI files; any
fulfillment or sale reference; inventoryAdjustQuantities (never
registered, never called); any Shopify->Odoo stock write (Task 013B's
scope, not this task's); any Shopify mutation call site outside the
Layer 2 wrapper (enforced by the existing repo-wide AST guard, DEC-036
D16/D37); protected references.

======================================================================
HARD CONSTRAINTS
======================================================================

- Write target 'available' only; 'committed' never (source-guard test).
- Every mutation passes through the Layer 2 wrapper (C1 claim already
  exists at job level; C2 attempt-intent on a side cursor; NET; C3
  outcome commit) — no direct API-client mutation call anywhere in this
  module.
- THREE job types, not two attempts in one job: inventory_push_sync
  (orchestration/read-only, remote_read_replay_safe, no Shopify mutation,
  no mutation.attempt row, enqueues at most one mutation job per
  dispatch) and two STANDALONE mutation job types, inventory_set_quantities
  and inventory_activate (DEC-037 §4/§5) — job_type == mutation_domain
  for each. NEVER combined into one job or one attempt; each mutation job
  has its own job record, own attempt_token, own idempotency key, own
  fingerprints. A mutation job may only enqueue nothing; only
  inventory_push_sync enqueues mutation jobs, and only after its own
  fresh read.
- changeFromQuantity is captured FRESH immediately before each mutation
  job's own C2 — never read from the binding's last_known_shopify_available
  field (informational/display only).
- CHANGE_FROM_QUANTITY_STALE -> bounded re-read/re-derive, exactly 3
  retries, each a REDISPATCH of the SAME inventory_set_quantities job
  (not a new job) with a new attempt (new fingerprints, new key, a fresh
  narrow CAS pre-read of available/updatedAt, and a fresh read of the
  binding's coalesced pending target); the 4th mismatch ->
  blocked_manual_review/binding_conflict, never a further silent retry.
- ITEM_NOT_STOCKED_AT_LOCATION observed by inventory_set_quantities is a
  race/contract exception, NOT an inline activation trigger -> routes
  failed_clean/inventory_location_missing, blocked_manual_review; this
  job issues NO inventoryActivate call, inline or otherwise, in any form
  (static/AST-guarded). The pending target stays coalesced; only a
  LATER, separate, fresh inventory_push_sync orchestration dispatch may
  find the level genuinely absent and enqueue a new inventory_activate
  job (DEC-037 §5.2 step 8).
- inventory_activate always sends explicit available:0 (never omitted or
  nonzero); after its effective disposition is applied, it does NOT
  enqueue inventory_set_quantities itself — the pending target stays
  coalesced and only a fresh, independently-admitted inventory_push_sync
  orchestration dispatch (after the activation job has gone terminal) may
  re-read Shopify and enqueue inventory_set_quantities (DEC-037 §5.2 step
  7).
- inventoryActivate's userErrors carry NO error code (field+message
  only) -> classify by payload shape only (non-empty userErrors + null
  inventoryLevel = failed_clean/blocked_manual_review/binding_conflict;
  non-empty userErrors + non-null inventoryLevel = uncertain). NEVER
  match on UserError.message text to select an error class, retry
  decision, or manual-review subreason for any mutation in this module
  (DEC-037 §4 row 2) — message text may be captured as redacted
  diagnostic evidence only.
- Unexplained Shopify-side drift -> review case, BLOCKS the pending push
  for that pair, NEVER an automatic or silent overwrite (DEC-037 §1 item
  C6 — this replaces any "log then push over" design in the packet's own
  2026-07-10 history, which must not be implemented).
- Reconciliation not-applied verdict for inventory_set_quantities
  requires freshness evidence (updatedAt not later than transport_at)
  before concluding not-applied; if updatedAt is later, or freshness is
  unavailable and attribution is ambiguous, the verdict is inconclusive,
  NEVER not-applied (DEC-037 §4 row 1 — an ABA round-trip must not be
  read as proof of no effect).
- One (inventory_item_id, location_id) pair per mutation request/attempt
  — NO multi-entry quantities[] array of length > 1 anywhere (DEC-036 D4;
  static/AST test required).
- Coalescing: one pending-update target (pending_target_available) per
  pair, last-value-wins; operation_scope_key = the frozen pair-serialization
  literal inventory_pair:{store_id}:{inventory_item_gid}:{shopify_location_gid}
  (DEC-037 §5.3) serializes ALL THREE job types per pair — only one
  non-terminal inventory job per pair at a time; terminalization and next
  -phase-job enqueue are atomic, under a row lock on the binding; a
  genuine concurrent-transaction test is required proving duplicate phase
  jobs cannot be created.
- First-push guard per pair with recorded confirmation (actor/time/preview
  qty), checked by inventory_push_sync at enqueue time; no write for an
  unconfirmed row (destructive_write_guard_blocked); activation never
  creates an unreviewed nonzero stock state.
- Job-source/job-type/manual-review-subreason/pair-serialization-identity
  vocabulary is FROZEN per DEC-037 §7 — do not invent additional values.
- Every mutation outcome resolves to a row in DEC-037 §9's consequence
  contract (observed_outcome/error_class/manual_review_subreason/retry
  eligibility/reconciliation requirement/next orchestration behavior);
  unknown or malformed consequence data NEVER defaults to automatic
  retry — fail closed to uncertain/manual review.
- Reconnect: no push/activation admitted for a pair until that pair's
  post-reconnect reconciliation read (store-identity check first,
  DEC-036 D18) has completed; this gate is enforced by inventory_push_sync
  alone — no mutation job performs reconnect classification itself.
- Negative free_qty -> clamp to 0 + divergence warning carrying the true
  value; never send a negative available.
- Unmapped items/locations -> skipped with surfaced counts, never a
  silent drop.
- No flag bypasses any guard above.
- Odoo.sh green before merge review (verbatim quote) — genuine
  PostgreSQL concurrency proof for the coalescing/operation_scope_key
  dedup and the two-sequential-attempt sequencing (not same-process
  simulation).
- Dev-store mutation-validation plan
  (docs/05-qa/wave-3-dev-store-mutation-validation-plan.md) scenarios
  1-8, 9 (activation, its own job), 10-12, 17-19 (17: throughput; 18:
  ABA/freshness; 19: ITEM_NOT_STOCKED_AT_LOCATION race, fail-closed)
  executed with redacted evidence, OR a recorded, explicit control-room
  waiver for any scenario found genuinely not-executable (state the
  reason, never silently skip).
- Zero scope expansion: no Task 014/015/UI/webhook work; no
  reconciliation-strategy-registry mechanism changes beyond registering
  this module's two domains through the existing seam.
- No self-merge; do not mark this PR ready for review; stop after the
  draft PR and your own validation-results/AR/handoff commits.

======================================================================
RESIDUE AUDIT
======================================================================

Zero idle-in-transaction connections after any activation-to-set-
quantities handoff (across the orchestration re-dispatch between the two
standalone jobs); zero orphaned locks; zero stray workers; zero leaked
credentials/tokens in preconditions_snapshot/remote_mutation_intent/
remote_evidence_refs (this module's own allowlist declarations, alongside
its D-015 reconciliation-strategy registration); zero duplicate mutation
attempts recorded for a single successful Shopify effect across the CAS-
retry and reconciliation test matrix; zero cases of two mutation jobs
non-terminal for the same pair-serialization identity simultaneously.

======================================================================
ROLLBACK NOTES
======================================================================

Single-PR revert; drops the location-mapping/inventory-level-binding
tables; live Shopify stock is not touched by a revert; fulfillment
(Task 014) never depends on this task's internals, so a revert does not
strand it. Post-ship (after at least one real mutation has run), rollback
requires BOTH: (a) inventory_domain_enabled=False, blocking new jobs; AND
(b) confirming the inventory_set_quantities/inventory_activate
replay-policy registry entries remain remote_effect_not_replay_safe
(their permanent class) so no in-flight retry auto-fires. Attempt
evidence (on shopify.connector.mutation.attempt, core-owned) is retained
per DEC-036 D32 regardless of this module's own rollback.

======================================================================
DEFINITION OF DONE
======================================================================

- Every D-013-1..9 decision implemented exactly as specified in the
  corrected packet and DEC-037.
- Both mutation-domain matrix rows (DEC-037 §4) implemented exactly,
  including every classification cell (no TBD, no invented behavior for
  a cell this record left unresolved without also implementing its
  stated fail-closed default).
- Static, unit, and genuine-concurrency tests green (Stage 0's proven
  multi-connection technique, extended to this module's pair-serialization
  claims and the three-job-type handoff/admission mechanics, DEC-037
  §5.3).
- Odoo.sh fresh-install + focused-class + full regression + residue
  audit green.
- Dev-store validation plan scenarios executed (or explicitly,
  recorded-ly waived) with redacted evidence in
  docs/05-qa/task-013-inventory-sync-validation-results.md.
- mvp-program-state.md, mvp-acceptance-matrix.md, and
  research-handoff.md updated.
- Zero Task 014/015/UI/webhook code anywhere in the diff.

======================================================================
STOP CONDITIONS (hard stops — consolidate and report, do not proceed
past any of these)
======================================================================

1. Wave 3 Stage 0 is found not actually merged/runtime-proven at
   issuance time, despite this prompt asserting it is.
2. Any DEC-037 matrix cell you find, during implementation, does not
   match the live 2026-07 Shopify schema — STOP and re-report; do not
   silently re-derive the matrix yourself.
3. Any code path found that would combine the activation and
   set-quantities mutations into one job or one attempt, that enqueues
   inventory_set_quantities directly from inventory_activate (or vice
   versa) without an intervening fresh inventory_push_sync dispatch, or
   that constructs a multi-entry quantities[] array.
4. Any code path that matches on UserError.message text to select an
   error class, retry decision, or manual-review subreason.
5. Any attempted change to a forbidden file.
6. Any attempted change to a protected reference.
7. Genuine dev-store mutation evidence proves unobtainable for a
   scenario not already flagged as possibly-not-executable (scenario 8)
   — escalate, do not substitute simulation.
8. Every Wave-3-DoR program-level hard stop (1-10) applies verbatim.
```

---

## Issuance checklist (for the control-room session that eventually issues this)

- [ ] This Gate B package (DEC-037) is ACCEPTED and MERGED (not
      PROPOSED or CANDIDATE).
- [ ] Wave 3 Stage 0 is MERGED into `mvp/program-integration` and its
      four DEC-036 D38 proof-environment layers are green.
- [ ] `<EXACT_POST_STAGE0_SHA_AT_ISSUANCE>` is replaced with a
      live-verified `mvp/program-integration` tip taken **after** the
      Stage 0 merge, not any SHA recorded during this prompt's authoring
      or during Gate B's own session.
- [ ] This prompt's file list/sequence still matches the then-current
      Task 013 packet and DEC-037 text (re-diff before use).
- [ ] The issuing session is not the session that authored or corrected
      this prompt.
- [ ] Independent Claude verification of the matrix/sequencing design is
      recorded complete.
