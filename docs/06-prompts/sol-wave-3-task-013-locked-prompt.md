# Locked Sol Wave 3 Task 013 Implementation Prompt — Inventory Synchronization

> **ISSUED-NOT-EXECUTED: NO**
> **LOCKED: YES**
> **NOT USABLE UNTIL SEPARATE CONTROL-ROOM ISSUANCE.** This prompt is a
> draft, ready-to-copy template prepared during the Wave 3 Gate B session
> (2026-07-19; corrected to Revision 2, same date, per control-room
> comment `5015619162` on PR #179 — the job model below is now three
> standalone job types, not one job owning two sequential attempts;
> further corrected to Revision 3, same date, per control-room comment
> `5015830229` — every mutation job now makes at most one attempt for
> its entire lifetime, CAS/`not_applied` retries create a **new** job
> rather than redispatching the old one, the activation→orchestration
> handoff is atomic, `blocked_manual_review` is not terminal, the error
> vocabulary is fixed, and the ROLE section below is corrected to the
> current role model), per
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
execute two Shopify mutations. **Revision 3 job-lifetime and handoff
corrections, binding (control-room comment `5015830229`):** no mutation
job may own more than one `mutation.attempt` row for its entire
lifetime — a CAS-stale or reconciliation-`not_applied` outcome
transitions that job to the existing terminal state `cancelled` and
creates a **new**, separate job (never a same-job redispatch); the
activation→fresh-orchestration handoff is
**atomic** (same transaction as the activation job's own
terminalization, never dependent on a later scan/manual trigger);
`blocked_manual_review` is not terminal and is released only by
`action_recheck_inventory_pair(reason)`; every `error_class` value is
one of the fixed set in DEC-037 §7/§9.

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
    last_pushed_at, last_known_shopify_available as informational fields;
    OWNS the public review-release RPC/action method
    action_recheck_inventory_pair(reason) (Reviewer/Administrator only)
    per DEC-037 §5.5 and §1C item 7 — the public action surface lives on
    THIS binding model exclusively; it may delegate to a private helper on
    shopify_connector_inventory_service.py, but the service never exposes
    or owns the public method)
  models/shopify_connector_inventory_service.py (NEW — orchestration
    (inventory_push_sync)/preview service, job seams, hooks,
    location-cache sync with the ONE named sudo per D-013-5; the Layer 2
    wrapper integration per D-013-9 and DEC-037 §4/§5/§9 lives here —
    inventory_set_quantities and inventory_activate are each registered
    as their OWN standalone mutation job type (job_type ==
    mutation_domain), each making at most one mutation.attempt for its
    entire lifetime, never combined; inventory_push_sync itself issues
    no Shopify mutation and enqueues at most one mutation job per
    dispatch; the fresh changeFromQuantity read into
    preconditions_snapshot at each mutation job's own C2; the
    pair-serialization admission/atomic-handoff mechanics per DEC-037
    §5.3/§5.4 (handoffs A-D, cas_retry_ordinal/superseded_by_job_id/
    cancel_reason job-lineage fields); a PRIVATE review-release helper
    only — the PUBLIC action_recheck_inventory_pair(reason) method is
    owned exclusively by shopify_connector_inventory_level_binding.py
    (DEC-037 §5.5/§1C item 7); this service may host a private delegate
    the binding calls, but MUST NEVER expose or own the public RPC/action
    surface)
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
    §4/§5/§9: CAS bounded-3-replacement test asserting FOUR DISTINCT job
    records (cas_retry_ordinal 0->1->2->3, connected only by
    superseded_by_job_id) -- NEVER a redispatch of any prior job -- then
    blocked_manual_review with no replacement on the 4th mismatch,
    fresh-CAS-pre-read-per-replacement test, activation/set-quantities
    distinct-JOB test (distinct job_type/job ID/attempt_token/idempotency
    key, connected only by a fresh, ATOMIC orchestration handoff -- never
    two attempts inside one job, never a same-job redispatch), static/AST
    guard that no inventory_set_quantities code path calls
    inventoryActivate (and vice versa), job_type==mutation_domain
    invariant test, a reconciliation not_applied verdict (either domain)
    creates a NEW same-domain job test (never redispatches the resolved
    one), a blocked_manual_review job creates no automatic child test,
    action_recheck_inventory_pair release test (authorized reason
    required, creates exactly one fresh inventory_push_sync job, never
    rewrites observed_outcome/resolution_disposition), genuine
    independent-PostgreSQL-connection concurrency test proving duplicate
    phase jobs (including a CAS/not_applied replacement job) cannot be
    created for one pair, THROTTLED classification test, reconciliation
    applied (asserting NO updatedAt condition)/not-applied/inconclusive
    tests for BOTH mutation domains INCLUDING an ABA/freshness fixture
    (value changes away and back with a later updatedAt -> inconclusive,
    never not_applied), static/AST guard that no code path matches on
    UserError.message text for inventoryActivate classification, a
    static/AST guard that no error_class value outside the fixed
    vocabulary (DEC-037 §7/§9) appears anywhere in the module (in
    particular none of remote_validation_rejected/
    remote_precondition_mismatch/transport_ambiguous/clean_rejection),
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
- ONE MUTATION JOB OWNS EXACTLY ONE mutation.attempt FOR ITS ENTIRE
  LIFETIME (DEC-037 §5.1/§9, control-room comment `5015830229` binding
  correction 1). A mutation job is NEVER redispatched to make a second
  attempt. Every CAS-stale retry and every reconciliation not_applied
  retry creates a NEW, separate job of the same domain — the old job's
  attempt keeps its failed_clean or resolved not_applied outcome
  unchanged while the job itself transitions to the existing terminal
  state cancelled, and is never reused for a further attempt.
- changeFromQuantity is captured FRESH immediately before each mutation
  job's own C2 — never read from the binding's last_known_shopify_available
  field (informational/display only).
- CHANGE_FROM_QUANTITY_STALE -> observed_outcome=failed_clean,
  error_class=concurrency_race_conflict; bounded re-read/re-derive,
  exactly 3 replacement jobs (cas_retry_ordinal 0->1->2->3), EACH A NEW,
  SEPARATE inventory_set_quantities job — NEVER a redispatch of the job
  whose attempt just failed. The failing job's own single attempt keeps
  observed_outcome=failed_clean unchanged; the JOB ITSELF transitions
  atomically to the EXISTING CORE JOB STATE cancelled (never a new
  state) — superseded_by_job_id set on it, cancel_reason=
  'cas_stale_bounded_replacement', DEC-037 §5.4 handoff C — in the same
  transaction that creates the new job (new fingerprints, new key, a
  fresh narrow CAS pre-read of available/updatedAt, and a fresh read of
  the binding's coalesced pending target); the 4th mismatch (ordinal 3)
  creates NO replacement job -> that job instead transitions to the
  EXISTING NON-TERMINAL blocked_manual_review state (binding_conflict),
  which continues to hold operation_scope_key until an authorized
  action_recheck_inventory_pair release, never a further silent retry.
- A reconciliation not_applied verdict (either mutation domain) follows
  the identical pattern: the resolved job's attempt keeps its uncertain/
  not_applied outcome unchanged while the JOB ITSELF transitions to the
  existing core job state cancelled (superseded_by_job_id set,
  cancel_reason='reconciliation_not_applied_replacement', DEC-037 §5.4
  handoff D) and a NEW same-domain job is created for the next attempt —
  never a same-job redispatch.
- ITEM_NOT_STOCKED_AT_LOCATION observed by inventory_set_quantities is a
  race/contract exception, NOT an inline activation trigger -> routes
  failed_clean, error_class=inventory_location_missing, to the
  EXISTING NON-TERMINAL blocked_manual_review state; this job issues NO
  inventoryActivate call, inline or otherwise, in any form
  (static/AST-guarded). The pending target stays coalesced; the pair's
  operation_scope_key remains held and NO new job of any of the three
  inventory job types is admitted for it — no scan or manual trigger
  admits one automatically — until an authorized
  action_recheck_inventory_pair release; only then does the resulting
  fresh inventory_push_sync orchestration dispatch find the level
  genuinely absent and enqueue a new inventory_activate job (DEC-037
  §5.2 step 8/§9/§5.5).
- inventory_activate always sends explicit available:0 (never omitted or
  nonzero); when its own reconciliation read confirms applied, it does
  NOT enqueue inventory_set_quantities itself — in the SAME transaction
  that terminalizes inventory_activate as succeeded, a fresh
  inventory_push_sync job is enqueued ATOMICALLY (DEC-037 §5.2 step
  7/§5.4 handoff B) — this does NOT wait for an unrelated later scan or
  manual trigger. The pending target stays coalesced; the
  atomically-enqueued fresh inventory_push_sync job still performs its
  own full fresh Shopify read and gates before, in turn, enqueueing
  inventory_set_quantities.
- blocked_manual_review is NOT a terminal state for pair admission: a
  blocked inventory job retains the pair's operation_scope_key,
  preventing any new job (of any of the three types) from being admitted
  for the same pair, and preventing any automatic child job. It is
  released ONLY by action_recheck_inventory_pair(reason) — Reviewer or
  Administrator only, mandatory non-empty reason, allowed only when the
  blocked job's attempt has observed_outcome=failed_clean AND
  effective_disposition() == 'not_applied' (the effective-disposition
  helper, DEC-036 D10 — NOT a requirement that the raw
  resolution_disposition field itself be populated) with subreason
  inventory_location_missing or an enumerated-safe binding_conflict case
  (never uncertain, duplicate_risk, idempotency_contract_violation,
  unresolved reconciliation, or store_identity_mismatch — those remain
  resolvable only through the Stage 0 Administrator-only manual
  resolution path). This action never rewrites observed_outcome or
  resolution_disposition; it atomically transitions the blocked job from
  blocked_manual_review to the EXISTING CORE JOB STATE cancelled
  (cancel_reason='manual_review_release', superseded_by_job_id set) and
  enqueues exactly one fresh inventory_push_sync job, logging
  actor/reason/old-job-ID/new-job-ID (DEC-037 §5.5). The generic core job
  manual-retry/manual-review actions remain forbidden for any
  mutation-evidence-linked job.
- Job-lineage fields: cas_retry_ordinal (Integer, default 0,
  inventory_set_quantities only) is the ONLY NEW, domain-owned field this
  task introduces. superseded_by_job_id (Many2one, nullable) and
  cancel_reason (Char, nullable, fixed vocabulary:
  cas_stale_bounded_replacement / reconciliation_not_applied_replacement
  / manual_review_release) are EXISTING CORE shopify.connector.job
  fields, reused here, not new domain schema. None of the three adds a
  new value to the job model's core state Selection — no new core job
  state is introduced anywhere in this module (DEC-037 §5.4).
- error_class is FIXED VOCABULARY ONLY (DEC-037 §7/§9):
  shopify_user_errors_validation, inventory_location_missing,
  concurrency_race_conflict, shopify_throttling_rate_limit,
  shopify_temporary_server_network, data_shape_schema_mismatch,
  idempotency_contract_violation, no_reconciliation_strategy,
  store_identity_mismatch. NEVER produce
  remote_validation_rejected/remote_precondition_mismatch/
  transport_ambiguous/clean_rejection (Revision 2 values, withdrawn) or
  any other value not in this list.
- inventoryActivate's userErrors carry NO error code (field+message
  only) -> classify by payload shape only (non-empty userErrors + null
  inventoryLevel = failed_clean, error_class=shopify_user_errors_validation,
  blocked_manual_review/binding_conflict; non-empty userErrors + non-null
  inventoryLevel = uncertain, error_class=data_shape_schema_mismatch).
  NEVER match on UserError.message text to select an error class, retry
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
  non-terminal inventory job per pair at a time (a job in
  blocked_manual_review is NOT terminal for this purpose and continues to
  hold the pair); terminalization and next-phase-job enqueue (including a
  CAS/not_applied replacement job) are atomic, under a row lock on the
  binding (DEC-037 §5.4 handoffs A-D); a genuine concurrent-transaction
  test is required proving duplicate phase jobs cannot be created.
- First-push guard per pair with recorded confirmation (actor/time/preview
  qty), checked by inventory_push_sync at enqueue time; no write for an
  unconfirmed row (destructive_write_guard_blocked); activation never
  creates an unreviewed nonzero stock state.
- Job-source/job-type/error-class/manual-review-subreason/
  pair-serialization-identity/job-lineage-field vocabulary is FROZEN per
  DEC-037 §7 — do not invent additional values; action_recheck_inventory_pair
  is the only new domain action.
- Every mutation outcome resolves to a row in DEC-037 §9's consequence
  contract (observed_outcome/error_class/manual_review_subreason/retry
  eligibility/reconciliation requirement/next orchestration behavior);
  unknown or malformed consequence data NEVER defaults to automatic
  retry — fail closed to uncertain/manual review. Every CAS-stale and
  not_applied retry in that table creates a NEW job, never a same-job
  redispatch.
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
  dedup and the atomic phase-handoff/replacement-job sequencing (DEC-037
  §5.4, not same-process simulation).
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
replacement and reconciliation test matrix; zero jobs anywhere in the
test matrix that own more than one mutation.attempt row over their
lifetime; zero cases of two mutation jobs non-terminal for the same
pair-serialization identity simultaneously; zero cases of an orphaned
replacement job (superseded_by_job_id set with no corresponding new job,
or a new job created with no superseded predecessor terminalized in the
same transaction).

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
  claims and the three-job-type atomic handoff/admission/replacement-job
  mechanics, DEC-037 §5.3/§5.4/§5.5).
- Odoo.sh fresh-install + focused-class + full regression + residue
  audit green.
- Dev-store validation plan scenarios executed (or explicitly,
  recorded-ly waived) with redacted evidence in
  docs/05-qa/task-013-inventory-sync-validation-results.md.
- research-handoff.md updated.
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
9. Any code path found that would redispatch a mutation job to make a
   second mutation.attempt (a CAS-stale or not_applied retry must create
   a NEW job, never reuse the old one); any activation-to-orchestration
   handoff found NOT atomic with the activation job's own
   terminalization (e.g. dependent on a later scan/manual trigger); any
   automatic child job created from a blocked_manual_review job; any
   error_class value produced outside the fixed vocabulary (DEC-037
   §7/§9); or any Stage 0 extension found to require modifying Stage 0's
   own architecture, schema, or protocol rather than using the existing
   seam (report as a DEC-037 §13A prerequisite gap, do not work around
   it).
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
