# Research Handoff (rolling)

### Master implementation-readiness checkpoint — Task 010 gate assessment — compact handoff (2026-07-09)

- **Branch / PR:** `claude/task-010-readiness-checkpoint-jrx96i`, based on
  latest `Shopify-connector` tip `51628f77a7da1e47cfdb30d17559b496c4c45a1d`
  (PR #134 merge commit, confirmed via `git merge-base` = branch HEAD = origin
  tip this session); docs-only checkpoint PR into `Shopify-connector`,
  **draft**.
- **What happened:** PR #131, #132, #133, #134 confirmed **merged** via
  `pull_request_read` (all four `merged: true`, `state: closed`). Ran a full
  post-Task-006C implementation-readiness consolidation: read every file
  named in this session's required-reading list plus the `docs/04-decisions/`,
  `docs/03-architecture/`, and `docs/02-product/` cross-references relevant to
  Task 010, and directly inspected (read-only) `addons/shopify_connector_core/models/`
  and `/tests/` to confirm current module state (core substrate only; no
  product/customer/order/inventory/fulfillment code exists).
- **Readiness conclusion: NOT READY.** Created
  [`../07-implementation-plan/master-implementation-readiness-checkpoint.md`](../07-implementation-plan/master-implementation-readiness-checkpoint.md),
  concluding **Option 2 — not ready to open a Task 010 gate**. Two explicit
  preconditions named in `task-010-product-import-proposed.md` itself remain
  unmet: (1) the "product domain gate" (`ui-ux-implementation-task-map.md`
  Group 10) has never been opened and its own trigger conditions are
  undefined anywhere in the repository; (2) MBQ-55 (exact Odoo model/field
  names for the product-template and product-variant binding models) remains
  open, confirmed unresolved across every cross-reference checked (including
  the DEC-014 acceptance patch, which explicitly lists MBQ-55 as still open).
  This conclusion is consistent with, not a reversal of, PR #133's own
  recommendation (Product MVP Task 010 preparation explicitly "not
  recommended as the immediate next task") and PR #134's own stated fallback
  (MBQ-05 planning, absent a live runtime — still absent).
- **Recommended first build task: none.** No build task is recommended.
  Recommended next docs-only steps: (1) a dedicated documentation-only domain
  naming/schema planning pass resolving MBQ-55 for the product-template/
  variant binding models (primary — most directly closes one of Task 010's
  own two named preconditions); (2) MBQ-05 branch B auth-distribution
  planning as a non-competing parallel candidate; (3) a separate ChatGPT act
  defining the product domain gate's own opening criteria, since no document
  anywhere specifies them.
- **Task 010 final implementation prompt: NOT drafted.** Per this session's
  own phase-gating rule, the prompt is drafted only if the readiness decision
  is "ready" — it was not.
- **Task 010 gate-opening proposal: NOT drafted**, for the same reason.
- **Architecture review log:** added row **AR-033** — status **Proposed /
  Under review**, explicitly **not** Accepted, explicitly not claiming
  ChatGPT accepted anything in this session, and explicitly not authorizing
  any implementation gate.
- **Files changed:** created
  [`../07-implementation-plan/master-implementation-readiness-checkpoint.md`](../07-implementation-plan/master-implementation-readiness-checkpoint.md);
  added AR-033 to
  [`../05-qa/architecture-review-log.md`](../05-qa/architecture-review-log.md);
  this handoff entry. No `task-010-product-import-final-implementation-prompt.md`
  or `task-010-product-import-gate-opening-proposal.md` file was created (not
  applicable — see readiness conclusion above). No addon/code, test,
  manifest, XML/security, migration, or CI file touched.
- **Open blockers preserved, none resolved by this session:** multi-server/
  concurrent-worker runtime proof (SRR-03/SRR-04/SRR-09), VAL-B2, MBQ-05,
  MBQ-55, TD-002, the fulfillment API model, product first-sync dedup
  thresholds, token acquisition for many unrelated customers, Lite/Full
  packaging, checkpoint/resume ownership, and the two Task-010-specific
  preconditions named above (product domain gate; MBQ-55).
- **No code touched.** No implementation authorized by this document or this
  session. No implementation gate opened, extended, or reinterpreted.
- **Learning feedback loop:** no new issues discovered; no new repeated-issue
  pattern; no rule/checklist change needed; no new rejected approach (checked
  `rejected-approaches-log.md` for relevance — none applicable to a
  readiness-checkpoint session); no new technical debt.
- **Quality gate confirmation:** handoff updated (this block) · feedback loop
  checked · learning captured (above) · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Stop condition:** checkpoint document created; AR-033 logged; this
  handoff entry written; all open blockers preserved as open, none claimed
  resolved; only the allowed docs files changed; PR left **draft/unmerged**;
  no merge performed; no implementation gate opened; no Task 010 code
  written. **Next step: ChatGPT review.**

---

### Sync-engine concurrency validation plan drafted — compact handoff (2026-07-09)

- **Branch / PR:** `claude/sync-engine-concurrency-plan-bq6ech`, based on
  latest `Shopify-connector` tip
  `c0a0bb3787947bba746f865a02883efa4e1c921d` (PR #133 merge commit);
  docs-only planning PR into `Shopify-connector`, **draft**.
- **What happened:** PR #133 (post-Task 006C next-task recommendation
  checkpoint) confirmed **merged** via `pull_request_read`. Per its
  recommendation (Candidate 1), drafted
  [`sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md):
  purpose/scope; SRR-03/SRR-04/SRR-09 risk mapping (current status, what
  Task 006C already does, what remains unproven, sufficient evidence);
  required runtime topology (A single-instance multi-worker, B
  multi-worker single-DB, C multi-server — preferred/strongest for
  SRR-09); code-free test-data setup using the shipped `core_dispatch_
  selftest` no-op handler and existing enqueue service; nine validation
  scenarios (single drain, concurrent workers, locked-row skip, retry-
  due filtering, three disconnect-race variants, multi-server drain,
  crash/interruption observation); evidence-to-collect and pass/fail
  matrix; explicit "what this plan can/cannot prove" section; a
  recommended execution order; the required future results-document
  spec (`sync-engine-concurrency-validation-results.md`); and a closing
  recommendation (execute only if a runtime is available; otherwise
  parallel-track MBQ-05 planning).
- **Files changed:** created
  [`../05-qa/sync-engine-concurrency-validation-plan.md`](../05-qa/sync-engine-concurrency-validation-plan.md);
  this handoff entry. No addon/code, test, manifest, XML/security,
  migration, or CI file touched. No live runtime, Odoo.sh, or Shopify
  access was used or available to this session — the plan was grounded
  by directly reading (never modifying) the merged Task 006C code
  (`shopify_connector_job.py`, `_dispatch.py`, `_log.py`, `_enqueue.py`,
  `_store.py`) to cite exact field/method names, not by inventing
  behavior.
- **Does not claim concurrency is proven; does not authorize
  implementation.** SRR-03/SRR-04/SRR-09 remain exactly as open as the
  risk register and DEC-025 state them; the plan explicitly states that
  even a fully green future execution would not mean concurrency is
  proven "for all time or all conditions." No implementation gate is
  opened, extended, or reinterpreted.
- **Recommended next step:** execute this plan only when a live
  Odoo/Odoo.sh runtime becomes available (topology A minimum, C
  preferred). If no runtime is available, proceed to MBQ-05 token
  acquisition/auth-distribution planning as a parallel docs-only track.
- **Open blockers preserved, none resolved by this session:** multi-
  server/concurrent-worker runtime proof (SRR-03/SRR-04/SRR-09), VAL-B2,
  MBQ-05, TD-002, the fulfillment API model, product first-sync dedup
  thresholds, token acquisition for many unrelated customers, Lite/Full
  packaging, checkpoint/resume ownership.
- **No code touched.** No implementation authorized by this document or
  this session.
- **Learning feedback loop:** no new issues discovered; no new
  repeated-issue pattern; no rule/checklist change needed; no new
  rejected approach (checked `rejected-approaches-log.md` for relevance
  — none applicable to a validation-plan draft); no new technical debt.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (above) · no new rejected approach ·
  no new technical debt · no repeated-issue escalation needed.
- **Stop condition:** validation plan created; this handoff entry
  written; all open blockers preserved as open; only the two allowed
  docs files changed; PR left **draft/unmerged**; no merge performed;
  no implementation gate opened. Next step: ChatGPT review.

---

### Post-Task 006C — next-task recommendation checkpoint — compact handoff (2026-07-09)

- **Branch / PR:** `claude/task-006c-next-recommendation-n1lp91`, based on
  latest `Shopify-connector` tip `b97df00a4dc6aa109e0485df881efac343feccdb`
  (merge-base confirmed equal to branch HEAD this session); docs-only
  checkpoint PR into `Shopify-connector`, **draft**.
- **What happened:** PR #132 (Task 006C closure/validation-results docs)
  confirmed **merged** via `pull_request_read`. Task 006C is now **fully
  closed** — sync-engine core skeleton (enqueue, `ir.cron` claim/drain
  dispatch, handler registry, retry scheduler, state-transition helpers)
  merged and validated per the user-provided Odoo.sh green-build report;
  no domain sync implemented.
- **Files changed:** created
  [`../07-implementation-plan/next-task-recommendation-after-task-006c.md`](../07-implementation-plan/next-task-recommendation-after-task-006c.md)
  (next-task recommendation doc, comparing five candidate next tasks and
  recommending one); this handoff entry. No addon/code, test, manifest,
  XML/security, migration, or CI file touched.
- **Recommended next step:** a docs-only **multi-server/concurrent-worker
  concurrency validation *plan*** for the Task 006C job-claim mechanism
  (`_claim_for_dispatch()`/`try_lock_for_update()`), mirroring
  `val-b2-closure-plan.md`'s pattern — not code, not the live test itself.
  Token acquisition/auth-distribution planning (MBQ-05 branch B) is named
  as a strong parallel/second candidate. Product MVP Task 010 preparation
  and setup/config UX planning are explicitly **not** recommended next —
  see the recommendation doc §E for the rework risk of starting either
  ahead of the concurrency-proof and distribution-architecture questions.
- **Open blockers preserved, none resolved by this session:** multi-server/
  concurrent-worker runtime proof, VAL-B2, MBQ-05, TD-002, the fulfillment
  API model, product first-sync dedup thresholds, token acquisition for
  many unrelated customers, Lite/Full packaging, checkpoint/resume
  ownership.
- **No code touched.** No implementation authorized by this document or
  this session — the recommendation doc explicitly lists its own
  non-authorizations.
- **Learning feedback loop:** no new issues discovered; no new repeated-
  issue pattern; no rule/checklist change needed; no new rejected
  approach (checked `rejected-approaches-log.md` RA-003 for relevance to
  Lite/Full packaging — not re-proposed, only cited as context); no new
  technical debt.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (above) · no new rejected approach ·
  no new technical debt · no repeated-issue escalation needed.
- **Stop condition:** recommendation doc created; this handoff entry
  written; all open blockers preserved as open; only the two allowed docs
  files changed; PR left **draft/unmerged**; no merge performed. Next
  step: ChatGPT review.

---

### Task 006C — PR #131 merged, closure/validation-results docs — compact handoff (2026-07-09)

- **Branch / PR:** `claude/task-006c-validation-docs-g4yj8s`; docs-only
  closure PR into `Shopify-connector`, **draft**. PR #131 itself
  (`claude/sync-engine-skeleton-10hd4p` → `Shopify-connector`) is
  **merged** — merge commit `152b1553fe10c6efcbad75b4eba9cfcd2f101385`
  (head before merge `e68a5319bb7a7602bb8cc72568ef0c022551f542`; base
  `6e482ec60b3601c3c77cba257f97b64cc889aae1`), 2026-07-09T08:32:33Z.
- **Files changed:** `docs/05-qa/task-006c-sync-engine-skeleton-validation-results.md`
  (new closure/validation record), `docs/05-qa/architecture-review-log.md`
  (new row AR-032), `docs/01-research/research-handoff.md` (this entry).
  No addon/code, test, manifest, XML/security, migration, or CI file
  touched.
- **What changed / residue fixed:** Task 006C's sync-engine core
  skeleton (job enqueue, `ir.cron` claim/drain dispatch, handler
  registry, retry scheduler, state-transition helpers, diagnostic
  `core_dispatch_selftest` job type, and the approved
  `action_disconnect()`/`manual_review_subreason` one-file exception)
  is now formally closed out with a dedicated validation-results
  document and an architecture-review-log entry (AR-032), recording the
  two real-runtime defects found and fixed (test-only fake-handler
  signature bug; real production `action_disconnect()` bug, fixed via
  approved exception, review artifact `4923059289`) and the honest state
  of Odoo.sh verification: GitHub `get_status`/`get_check_runs` for the
  merged head still return `pending`/empty as of this session — merge
  rests on user-provided green-build confirmation, not on independently
  observed CI evidence.
- **Items deferred:** unchanged and explicitly preserved as open —
  multi-server/concurrent-worker runtime proof for
  `try_lock_for_update()`, VAL-B2, MBQ-05, TD-002, the fulfillment API
  model, product first-sync dedup thresholds, token acquisition for many
  unrelated customers, Lite/Full packaging, checkpoint/resume ownership.
  No domain sync implementation exists yet.
- **Learning feedback loop:** no new issues discovered this session; no
  new repeated-issue pattern; no rule/checklist change needed. No new
  rejected approach. No new technical debt (Task 006C's own debt items
  are unchanged, not newly introduced). No architecture concern beyond
  what AR-031/AR-032 already record. Should future prompts change? No —
  the docs-only closure pattern (validation-results doc + AR log row +
  compact handoff) worked cleanly for a post-merge task and should
  remain the default for future task closures.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (above) · no new rejected approach ·
  no new technical debt · no repeated-issue escalation needed.
- **Next recommended session:** decide the next controlled task.
  Recommended: Task 006D/006E closure review if numbering requires it,
  then proceed to the next core prerequisite or Product MVP Task 010
  only after ChatGPT issues a separate implementation prompt.
- **Stop condition:** docs-only closure complete — validation-results
  doc created, AR-032 logged, this handoff entry written; all open
  blockers preserved as open, none claimed resolved; no addon/code/test/
  manifest/XML/security/migration/CI file touched; no claim of
  independent Odoo.sh verification; no claim of proven multi-server
  concurrency; PR left **draft/unmerged**; no merge performed. Next
  step: ChatGPT review.

---

### Task 006C — PR #131 approved one-file exception: `action_disconnect()` clears `manual_review_subreason` — compact handoff (2026-07-09)

- **Branch / PR:** `claude/sync-engine-skeleton-10hd4p` → PR #131 into
  `Shopify-connector` (**draft**, unmerged), starting from head
  `f0a246a9152805f1b55124080579830a9a99c80a`. Applies the control-room-
  approved one-file exception (GitHub review artifact/comment ID
  `4923059289`) to fix the real production bug reported in the prior
  session's real-runtime validation.
- **Files changed:** `addons/shopify_connector_core/models/
  shopify_connector_store.py` (the approved one-file exception --
  exactly one write-vals key added, nothing else in the file touched),
  `addons/shopify_connector_core/tests/test_job_dispatch.py` (one
  assertion added to an already-existing, unmodified-otherwise test),
  `docs/01-research/research-handoff.md` (this entry). No other file.
- **What changed / why required:** `action_disconnect()`'s cancellation
  loop now writes `'manual_review_subreason': False` alongside the
  existing `state: 'cancelled'` / `cancel_reason` / `finished_at` vals.
  Required because `action_disconnect()` already deliberately searches
  for and cancels every non-terminal business job -- `blocked_manual_
  review` is not in `TERMINAL_JOB_STATES`, so it is correctly included
  -- but a job in `blocked_manual_review` legitimately carries a
  `manual_review_subreason` (required by that state's own constraint).
  Cancelling it without clearing the subreason left it set while
  `state` became `cancelled`, violating the job model's own
  `_check_manual_review_subreason_required` constraint (`manual_review_
  subreason must be empty unless state is 'blocked_manual_review'`) and
  aborting `action_disconnect()` with a `ValidationError` -- exactly the
  1 error the real Odoo 19/PostgreSQL runtime reported. **No other
  disconnect semantics changed**: `TERMINAL_JOB_STATES` untouched,
  credential clearing untouched, reconnect/activate/test-connection
  untouched, the API client untouched, no new sudo/ACL/migration/UI/
  webhook/OAuth file. `test_disconnect_cancels_business_jobs_in_new_
  dispatch_states` (already correct, already covering all three
  scenarios -- `retry_waiting`, `failed_retryable`, `blocked_manual_
  review`) now also asserts `self.assertFalse(job.manual_review_
  subreason, state)` after cancellation for every scenario, proving the
  field is cleared regardless of the job's originating state, and (by
  the test completing without error) that no `ValidationError` is
  raised.
- **Status of the other patch-#3 item:** the fake-handler-signature fix
  (4 retry-routing test failures, fixed in the prior session, commit
  `f0a246a`) remains **pending a live runtime re-run** -- it was
  committed on static-correctness grounds only and has not yet been
  re-confirmed against a real Odoo/PostgreSQL registry.
- **Static validation (all pass):** `py_compile` on both changed Python
  files; `git diff` of `shopify_connector_store.py` confirms exactly one
  key (`'manual_review_subreason': False`) added to one `write()` call,
  nothing else in the file changed; zero new `sudo()` sites (diff-only
  check); zero new direct `job.log.create()`/`JobLog.create()` calls;
  zero new Shopify API client/`.execute(` references introduced in any
  Task 006C changed production file; `git status`/`git diff --stat`
  confirm only the three allowed files changed.
- **Runtime re-run:** **not performed by this session** -- no `odoo`
  package, no `psycopg2`, no responding PostgreSQL server in this
  sandboxed environment (unchanged from every prior session on this
  PR). This fix is committed on static-correctness grounds only. A
  fresh external Odoo.sh runtime re-run is required to confirm: (a) the
  single previously-failing disconnect test now passes; (b) the four
  retry-routing tests (fixed in the prior session) now pass; (c) the
  full `shopify_connector_core` suite passes beyond the prior 122-test
  halt point, with no newly-surfaced failure.
- **Items deferred:** unchanged -- VAL-B2, MBQ-05, TD-002 (untouched),
  the fulfillment API model, product first-sync dedup thresholds, token
  acquisition, Lite/Full packaging, checkpoint/resume ownership, and the
  multi-server runtime concurrency proof requirement remain exactly as
  open as before. The `action_disconnect()`/`manual_review_subreason`
  blocker named in the prior entry is now **resolved** (statically) and
  removed as an open blocker, pending the same live re-run every other
  static-only fix on this PR still awaits.
- **Learning feedback loop:** this closes out the two-part real-runtime
  validation failure from the prior session (4 test-fake-signature
  failures + 1 real production bug) with a clean split: the test-only
  defect was fixed directly within the session's own authority: the
  production defect was correctly escalated, not worked around, and
  fixed only after an explicit one-file exception was granted -- this
  is the intended, working shape of the "stop and request the minimal
  exception" pattern this project's governance model calls for, so no
  new process gap to log. New rejected approaches: none. New technical
  debt: none (the bug is fixed, not deferred). Should future prompts
  change? Recommend a standing project-level note: when a Task 006C-
  family (or any) session identifies a real production bug outside its
  allowed-file scope, the stop-and-report-with-a-proposed-minimal-fix
  pattern (used here) is confirmed to work end-to-end across two
  sessions and should remain the default, rather than being treated as
  a one-off improvisation.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (pattern-confirmation note above) ·
  no new rejected approach · no new technical debt · no repeated-issue
  count change (this is a distinct issue category from the manifest-
  truthfulness pattern, still at 2 occurrences, unchanged).
- **Next recommended session:** a fresh external Odoo.sh runtime
  re-run of `test_disconnect_cancels_business_jobs_in_new_dispatch_
  states`, the four retry-routing tests, and then the full
  `shopify_connector_core` suite -- the first full live confirmation
  this PR has ever received, and the last outstanding item before this
  PR can be considered ready for ChatGPT's merge-readiness decision.
- **Stop condition:** approved one-file exception applied exactly as
  scoped (one write-vals key, nothing else); test extended with the
  minimal required assertion; no broader disconnect semantics touched;
  no forbidden file touched; PR left draft/unmerged; no merge
  performed. Next step: fresh Odoo.sh runtime re-run.

---

### Task 006C — PR #131 real-runtime validation failure + fake-handler-signature fix — compact handoff (2026-07-09)

- **Branch / PR:** `claude/sync-engine-skeleton-10hd4p` → PR #131 into
  `Shopify-connector` (**draft**, unmerged). A real Odoo 19/PostgreSQL
  runtime validation (external Odoo.sh runtime, not this session's
  environment) reported **4 failures, 1 error, of 122 tests loaded
  before halt**, starting from head
  `3e6edd8347560ed5e31bd60bb4296053bfa18c99`.
- **Files changed this session:** `addons/shopify_connector_core/tests/
  test_job_retry_scheduling.py`, `addons/shopify_connector_core/tests/
  test_job_dispatch.py`, `docs/01-research/research-handoff.md` (this
  entry). No production model/dispatch file touched -- inspection
  proved production routing correct; only test fakes were wrong.
- **Root cause 1 (fixed) -- fake-handler signature mismatch (4 test
  failures):** `_invoke_handler()` retrieves `handler = self.
  _get_handlers().get(job.job_type)` from a plain dict -- a dict lookup
  never triggers Python's descriptor/binding protocol, so the retrieved
  callable is never bound. The dispatcher then calls it as `handler(job)`
  (one argument). Production's real handler (`self.
  _handle_core_dispatch_selftest`) already went through attribute access
  before being placed in the dict, so it's correctly bound and works.
  The test fakes in `_run_with_handler_error()` (`test_job_retry_
  scheduling.py`), `test_generic_exception_from_handler_treated_as_
  unknown_system_error`, and `test_secrets_redacted_in_dispatch_failure_
  path` (`test_job_dispatch.py`) were defined as `def _raise(self, job):`
  -- an unused, incorrect extra `self` parameter. Calling `handler(job)`
  against that 2-arg function raises `TypeError: missing 1 required
  positional argument`, caught by `_invoke_handler`'s fail-safe
  `except Exception` boundary and reclassified as `unknown_system_error`
  -- masking every intended `error_class`/state outcome the retry tests
  asserted. Fixed by dropping the stray `self` parameter from all three
  fake handlers (`_raise`, `_raise_plain`, `_raise_with_secret`) so they
  match the dispatcher's real one-argument `handler(job)` contract --
  the same contract two other, already-correct fakes in `test_job_
  dispatch.py` (`lambda job: calls.append(job.id)`, used twice) already
  followed. **Production dispatch/routing code was inspected and proven
  correct -- not modified.**
- **Root cause 2 (NOT fixed -- real production bug, out of this
  session's allowed-file scope) -- `action_disconnect()` /
  `manual_review_subreason`:** `test_disconnect_cancels_business_jobs_
  in_new_dispatch_states` (`test_job_dispatch.py`, unmodified this
  session) puts a job in `blocked_manual_review` with `manual_review_
  subreason='ambiguous_match'` set (required by the job model's own
  `_check_manual_review_subreason_required` constraint), then calls
  `self.store.action_disconnect()`. `action_disconnect()`
  (`shopify_connector_store.py`, **not modified this session, per the
  original final implementation prompt's explicit "action_disconnect
  remains unmodified" instruction**) deliberately searches for
  non-terminal business jobs to cancel -- `blocked_manual_review` is
  correctly included, since it is not in `TERMINAL_JOB_STATES` -- but
  its cancellation `job.write({'state': 'cancelled', 'cancel_reason':
  ..., 'finished_at': ...})` never clears `manual_review_subreason`.
  For a job coming from `blocked_manual_review`, the leftover subreason
  with the new `state='cancelled'` violates the same constraint
  (`manual_review_subreason must be empty unless state is
  'blocked_manual_review'`), raising `ValidationError` and aborting
  `action_disconnect()` entirely. **This is a real, pre-existing latent
  production bug in `action_disconnect()`, only now reachable because
  Task 006C is the first code path that ever sets `blocked_manual_
  review`** -- today, any store with a job stuck in `blocked_manual_
  review` cannot be disconnected at all. The test is correct and was
  left unmodified; narrowing it to skip `blocked_manual_review` would
  hide this real bug, which the session prompt explicitly forbade.
  **Proposed minimal one-file exception** (not applied this session):
  in `shopify_connector_store.py::action_disconnect()`'s cancellation
  loop, add `'manual_review_subreason': False` to the `job.write({...})`
  vals dict (harmless no-op for jobs where it's already empty; clears it
  for jobs coming from `blocked_manual_review`). Requires explicit
  ChatGPT approval to touch `shopify_connector_store.py`, a file outside
  this session's allowed-file list.
- **Static validation (all pass):** `py_compile` on both changed test
  files; `xml.dom.minidom` parse of the cron XML; manifest parses via
  `ast.literal_eval`; zero `numbercall`; zero direct `job.log.create()`
  calls in dispatch; `job_enqueue.py`'s only `.create(` call targets
  `shopify.connector.job`; zero Shopify API client / `.execute(`
  references in the three changed production files; zero new `sudo()`
  sites. `git status`/`git diff --stat` confirm only the two allowed
  test files changed.
- **Runtime re-run:** **not performed by this session** -- no `odoo`
  package, no `psycopg2`, no responding PostgreSQL server, no CI/Docker
  daemon in this sandboxed environment (unchanged from every prior
  session on this PR). The narrow fake-handler-signature fix is
  committed on static-correctness grounds only; the external Odoo.sh
  runtime must re-run the focused `test_job_retry_scheduling.py` /
  `test_job_dispatch.py` classes, then the full `shopify_connector_core`
  suite, to confirm the fix actually resolves the 4 reported failures
  and to determine whether `test_disconnect_cancels_business_jobs_in_
  new_dispatch_states` (the reported error) is now the *only* remaining
  failure, or whether further tests beyond the 122-test halt point
  surface new issues once these are cleared.
- **Items deferred:** unchanged -- VAL-B2, MBQ-05, TD-002 (untouched),
  the fulfillment API model, product first-sync dedup thresholds, token
  acquisition, Lite/Full packaging, checkpoint/resume ownership, and the
  multi-server runtime concurrency proof requirement remain exactly as
  open as before. New: the `action_disconnect()`/`manual_review_
  subreason` production bug above is now an open, named blocker on this
  PR pending an explicit one-file exception.
- **Learning feedback loop:** new issue class discovered: a fake
  test-double stored directly in a dict (not accessed via attribute
  lookup) is never bound by Python's descriptor protocol -- a `self`
  parameter on such a fake silently breaks its call arity, and if the
  code under test has a fail-safe `except Exception` boundary, the
  resulting `TypeError` can be silently reclassified into a *valid*-
  looking but wrong outcome rather than an obvious crash, delaying
  detection until a real runtime actually asserts the specific value.
  Worth a standing checklist item: whenever a handler/callback is
  registered via a plain dict (not `self.method`), any test fake
  replacing it must match the *unbound* call signature exactly. First
  occurrence of this category on this PR -- log only, no rule/checklist
  update yet (below escalation threshold). Second, unrelated issue
  discovered: `action_disconnect()`'s cancellation write path doesn't
  clear `manual_review_subreason` -- first occurrence of this category;
  logged as an open blocker above, not yet a rejected-approach or
  technical-debt entry (pending ChatGPT's decision on the one-file
  exception). New rejected approaches: none. Should future prompts
  change? Recommend a future Task 006C-family prompt authorize the
  `manual_review_subreason` clear as a pre-approved one-line exception
  in `shopify_connector_store.py`, scoped exactly to that field in that
  one write() call, rather than requiring a fresh stop-and-report cycle.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (two new issue-class notes above) ·
  no new rejected approach · new technical-debt-shaped item logged
  (disconnect/manual_review_subreason bug, pending exception approval,
  not yet added to `docs/05-qa/technical-debt-register.md` since that
  file is outside this session's allowed-file list) · repeated-issue
  count: manifest-truthfulness pattern remains at 2 (unchanged this
  session; these are two different, unrelated issue categories).
- **Next recommended session:** either (a) an explicit ChatGPT-approved
  one-file exception authorizing the minimal `manual_review_subreason`
  clear in `shopify_connector_store.py::action_disconnect()`, or (b) a
  fresh external Odoo.sh runtime re-run confirming the fake-handler fix
  resolves failures #2-#5 and re-confirming failure #1 (the disconnect
  error) is still the one open, named, unfixed item.
- **Stop condition:** narrow fake-handler-signature fix complete and
  committed; production `action_disconnect()`/`manual_review_subreason`
  bug identified, NOT fixed (outside allowed-file scope), reported with
  an exact proposed minimal exception instead; no unrelated change made;
  PR left draft/unmerged; no merge performed. Next step: ChatGPT review
  of this runtime-validation-failure fix and decision on the proposed
  `shopify_connector_store.py` exception.

---

### Task 006C — PR #131 manifest truthfulness patch — compact handoff (2026-07-09)

- **Branch / PR:** `claude/sync-engine-skeleton-10hd4p` → PR #131 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place --
  no new PR opened). Applies a narrow manifest-truthfulness fix per
  control-room re-review (GitHub review artifact/comment ID
  `4922068739`), starting from head
  `b28c1849a19ee63c828d13e42a65b172475ab1e6`.
- **Files changed:** `addons/shopify_connector_core/__manifest__.py`
  (wording only -- no key added/removed/reordered), `docs/01-research/
  research-handoff.md` (this entry). No other file touched.
- **What changed / residue fixed:** fixed stale "no Shopify API client" /
  "no external API calls" **module-level** wording in the manifest --
  the module has carried a working, callable Shopify API client
  (`shopify_connector_api_client.py`) and its test-connection/readiness
  call path since Task 003/004, well before this PR; claiming "no
  Shopify API calls" for the whole module was false and predates this
  session (the prior corrective patch fixed the narrower "no cron
  execution" claim but left this one, in the same paragraph,
  unaddressed). Both the `description` and the `summary` fields carried
  the same category of false claim (the `summary` field said "No
  Shopify API calls, no webhooks, no UI" in slightly different wording
  than the `description` field's "no Shopify API client, no external
  API calls") -- fixed both, since both are in the one allowed file and
  both are the identical defect; only `description` was explicitly named
  by the review, so this is flagged here as a small, disclosed,
  same-file consistency fix, not a silent scope expansion. New wording
  in both fields: states the module now includes the credential/
  redaction foundation, the API-client/test-connection foundation, and
  the core job enqueue/dispatch/cron drain skeleton; states plainly that
  the **Task 006C sync-engine skeleton itself** performs no Shopify API
  calls and implements no domain sync logic (a narrower, accurate claim,
  distinct from the false whole-module claim it replaces); keeps "no
  webhook handling," "no setup wizard," and "no operator-facing UI"
  verbatim in meaning. **No code behavior changed anywhere** -- this is
  a documentation/wording-only patch; no Python, XML, security, test, or
  model file was touched. **No implementation scope expanded** -- no
  new capability, field, method, or file was added or authorized.
- **Items deferred:** unchanged -- VAL-B2, MBQ-05, TD-002 (untouched),
  the fulfillment API model, product first-sync dedup thresholds, token
  acquisition, Lite/Full packaging, checkpoint/resume ownership, and the
  multi-server runtime concurrency proof requirement remain exactly as
  open as before. **Odoo/PostgreSQL runtime validation is still not run
  this session** -- no `odoo` package, no `psycopg2`, no responding
  Postgres server in this environment; `py_compile` was not needed since
  no Python file changed (the manifest is a plain Python dict literal,
  validated by `eval()`-parsing it directly instead).
- **Learning feedback loop:** new issues discovered: a stale-wording
  defect can hide in more than one manifest field at once (`summary` and
  `description` both claimed "no Shopify API calls" in different words)
  -- worth a standing reminder that a manifest truthfulness sweep should
  grep the whole file for the flagged claim's synonyms, not just the
  one field a reviewer happened to quote. Repeated issue pattern: this
  is the **second** manifest-truthfulness finding on this same PR (the
  prior patch fixed "no cron execution"; this one fixes "no Shopify API
  client"/"no external API calls") -- both are the same root-cause
  category (manifest prose drifting stale as the module gains real
  capability across tasks), now at 2 occurrences; not yet at the
  3rd-occurrence pause threshold (`quality-feedback-loop.md` §4), but
  worth naming explicitly here so a third recurrence is recognized
  immediately rather than treated as a fresh, unrelated issue. Rules/
  checklists updated: none this session (below escalation threshold).
  New rejected approaches: none. New technical debt: none. Architecture
  concerns: none beyond what prior entries already flagged. Should
  future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (repeated-pattern note above) · no
  new rejected approach · no new technical debt · repeated-issue count
  noted (2nd occurrence, below 3rd-occurrence escalation).
- **Next recommended session:** unchanged -- a live Odoo.sh
  runtime-validation pass for this PR remains the first outstanding
  item; still not performed by any session on this PR.
- **Stop condition:** manifest-truthfulness patch complete per the exact
  allowed-files list and required-fix scope named in this session's
  prompt; no unrelated change made; PR left draft/unmerged; no merge
  performed. Next step: ChatGPT final re-review.

---

### Task 006C — PR #131 corrective patch — compact handoff (2026-07-09)

- **Branch / PR:** `claude/sync-engine-skeleton-10hd4p` → PR #131 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place --
  no new PR opened). Applies a narrow corrective patch per control-room
  review (GitHub review artifact/comment ID `4921925802`), starting from
  head `c51c16e5f68e3b0a57d4bc8bb0f003f3bfbc39e9`.
- **Files changed:** `addons/shopify_connector_core/__manifest__.py`
  (description fix only), `addons/shopify_connector_core/data/
  shopify_connector_cron_drain.xml` (removed the invalid `numbercall`
  field; also fixed a second, previously-undetected defect found while
  validating -- the record's own XML comment contained a literal `--`,
  which is invalid inside an XML comment per spec and made the whole
  file fail to parse), `addons/shopify_connector_core/models/
  shopify_connector_job.py` (`_transition_failed_final()` gained an
  optional `retry_count` kwarg, written only when explicitly provided),
  `addons/shopify_connector_core/models/shopify_connector_job_
  dispatch.py` (the retry-exhaustion branch now passes the exhausted
  attempt count through; `_start_running()` now routes a blocked start
  to `failed_retryable`/`odoo_validation_configuration` instead of
  silently returning `False`), `addons/shopify_connector_core/tests/
  test_job_dispatch.py` (two new tests for start-gating visibility; the
  no-live-Shopify source-level guard now scans `shopify_connector_
  job.py` too, via a new `_changed_production_files()` helper),
  `addons/shopify_connector_core/tests/test_job_retry_scheduling.py`
  (added `retry_count` assertions to the two auto-retry exhaustion
  tests -- the `unknown_system_error` safety-net exhaustion test already
  asserted the count and was the one the reviewer's own example cited
  as mismatched against the pre-fix code), `docs/01-research/
  research-handoff.md` (this entry). No new files created -- every fix
  applied to an existing allowed file.
- **What changed / residue fixed:**
  1. **Cron XML install risk** -- `numbercall` is not a field on Odoo
     19's `ir.cron` model (confirmed by fetching the actual 19.0
     `ir_cron.py` source: the model's fields are `active`,
     `interval_number`, `interval_type`, `nextcall`, `lastcall`,
     `priority`, `failure_count`, `first_failure_date`, `user_id`, plus
     fields delegated from `ir.actions.server` via `ir_actions_server_id`
     -- no `numbercall`/`doall`); removed. Confirmed `model_id`/`state`/
     `code` remain valid on `ir.cron` via that same delegation
     mechanism, so no other field in the record needed to change.
     Separately found and fixed a genuine XML well-formedness bug in the
     same file's own comment (a literal `--` inside `<!-- -->`), which
     would have failed module installation outright regardless of the
     `numbercall` question.
  2. **Manifest description** -- the "no cron execution" claim was
     false as of this PR; narrowly reworded to state the module now
     includes a core job enqueue/dispatch and cron drain skeleton, while
     still explicitly stating no Shopify API calls, no webhooks, no
     setup wizard, no operator-facing UI, and no domain sync logic. No
     other manifest content changed.
  3. **Retry exhaustion count** -- `_transition_failed_final()` did not
     persist `retry_count`, so a job routed to `failed_final` via
     exhaustion kept its pre-attempt count, contradicting the fact that
     it did attempt and fail one more time. Fixed additively (an
     optional kwarg, written only when passed) without weakening bounded
     -retry behavior or touching DEC-009 classification; the
     max-attempts and retry-window exhaustion tests now assert the
     persisted count too, not only the safety-net test that already did.
  4. **Silent start-gating failures** -- `_start_running()` previously
     caught a blocked-start `ValidationError` and returned `False` with
     no state change and no log, so a gated job could remain
     `queued`/`retry_waiting` indefinitely with no visible outcome. Now
     routes to `failed_retryable`/`odoo_validation_configuration` (the
     same DEC-009 "manual fix then retry" class this error_class already
     maps to via `_route_failure()`), logged exclusively through the
     existing `_transition_failed_retryable()` helper -- no new
     `job.log.create()` call, no bypass of either gate, no claim that
     SRR-03 is closed (this fix is entirely about checkpoint 2, not
     checkpoint 3).
  5. **No-live-Shopify source guard scope** -- the guard previously
     scanned only the two new files; now scans all three changed
     production files (`shopify_connector_job.py` included) via a new
     `_changed_production_files()` helper, kept separate from the
     sudo-site guard's own (intentionally unchanged, still two-file)
     scope.
- **Items deferred:** unchanged from the prior entry -- VAL-B2, MBQ-05,
  TD-002 (untouched), the fulfillment API model, product first-sync
  dedup thresholds, token acquisition, Lite/Full packaging, and every
  named runtime-validation item (§I) remain exactly as open/undone as
  before this patch. No live Odoo.sh run was performed this session
  either -- see below.
- **Learning feedback loop:**
  - New issues discovered: (a) an XML comment containing a literal `--`
    is invalid per the XML spec and breaks parsing outright -- worth a
    standing reminder for any future `<!-- -->` comment in this repo's
    data/view XML to avoid double-hyphens; (b) `numbercall`/`doall` are
    legacy `ir.cron` fields no longer present in Odoo 19 -- confirmed by
    fetching the actual 19.0 source this session (not merely inferred
    from older-version memory), now recorded here for any future cron
    record in this project to avoid repeating.
  - Repeated issue patterns: none (both are first occurrences).
  - Rules/checklists updated: none this session (below the
    repeated-issue escalation threshold).
  - New rejected approaches: none.
  - New technical debt: none -- every fix here closes a genuine defect
    rather than accepting a compromise; `technical-debt-register.md` is
    unmodified.
  - Architecture concerns: none beyond what the original PR already
    flagged (SRR-03 narrowed-not-closed; claim-mechanism concurrency
    safety unproven by unit tests; batch-size/interval defaults
    unvalidated at realistic volume) -- unchanged by this patch.
  - Tests or review gates needed: the same separate, later, live
    Odoo.sh validation session named in the original PR entry --
    unchanged, still not performed.
  - Should future prompts change? No.
  - **Self-verification performed this session (no live Odoo
    available):** `python3 -m py_compile` on every changed Python file;
    `xml.dom.minidom` parse confirming the cron XML is now well-formed
    (it was not, before this patch, due to the comment defect); a
    repo-wide scan confirming no other XML file in this addon has the
    same double-hyphen-in-comment defect; a live fetch of the actual
    Odoo 19.0 `ir_cron.py` source confirming `numbercall`'s absence
    (not asserted from memory alone); a standalone Python script
    replicating every updated AST-based source-level test (sudo-site
    count unchanged at 2, `job_dispatch.py` still zero `.create(` calls,
    `job_enqueue.py`'s sole `.create(` target still `shopify.connector.
    job`, no Shopify-API-client reference in any of the three changed
    production files); a full manual trace of the retry-exhaustion math
    and the two new start-gating tests against the updated production
    code.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next recommended session:** unchanged -- a live Odoo.sh
  runtime-validation pass for this PR, now against the corrected code
  (this is the first session where the cron XML would actually load
  without an install-time error).
- **Stop condition:** corrective patch complete per the exact allowed-
  files list and required-fixes scope named in this session's prompt;
  no unrelated change made; PR left draft/unmerged; no merge performed.
  Next step: ChatGPT re-review.

---

### Task 006C — sync-engine skeleton implementation — compact handoff (2026-07-09)

- **Branch / PR:** `claude/sync-engine-skeleton-10hd4p` → PR into
  `Shopify-connector` (**draft**, to be opened this session). First
  **code** session of this project (`CLAUDE.md` §5 no-code gate lifted
  for this task only, per the Task 006C gate-opening act -- confirmed
  merged at `6e482ec60b3601c3c77cba257f97b64cc889aae1`, the exact SHA
  cited in this session's issued final prompt, and confirmed via `git
  log`/`git rev-parse HEAD` before any edit). No Odoo/Postgres runtime
  is available in this session's execution environment (no `odoo`
  package, no vendored Odoo source, no running Postgres) -- every test
  below is written and verified by careful manual control-flow tracing
  plus AST/py_compile-level static self-checks (see Learning feedback
  loop), not by an actual Odoo test-runner execution. This mirrors, not
  substitutes for, the project's own established Odoo.sh live-validation
  practice (Tasks 001-005) -- see "Items deferred" below.
- **Files changed:** `addons/shopify_connector_core/models/
  shopify_connector_job.py` (modify -- new `core_dispatch_selftest`
  `job_type` value; `_domain_flag_for_job_type()`; the domain-flag
  branch added inside `write()` alongside the unmodified store-state
  re-check; `_claim_for_dispatch()`; five state-transition helpers --
  `_transition_retry_waiting`/`_failed_retryable`/`_failed_final`/
  `_blocked_manual_review`/`_skipped`, plus a shared `_log_transition`
  private helper), `addons/shopify_connector_core/models/
  shopify_connector_job_enqueue.py` (new, `AbstractModel`),
  `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (new, `AbstractModel` -- `_get_handlers()` seam, `run_drain()`,
  dispatch/checkpoint-3 logic, `JobHandlerError`, the DEC-009 retry-class
  routing tables, `_schedule_retry_or_fail`/`_retry_delay_seconds`),
  `addons/shopify_connector_core/data/shopify_connector_cron_drain.xml`
  (new -- one `ir.cron` record, no view/menu/action),
  `addons/shopify_connector_core/models/__init__.py` (two new import
  lines), `addons/shopify_connector_core/tests/test_job_enqueue.py`
  (new), `addons/shopify_connector_core/tests/test_job_dispatch.py`
  (new), `addons/shopify_connector_core/tests/
  test_job_retry_scheduling.py` (new, kept as its own file rather than
  folded into `test_job_dispatch.py` -- retry-scheduling has enough
  distinct scenarios, per the final prompt's own either/or option, to
  warrant separation), `addons/shopify_connector_core/tests/__init__.py`
  (three new import lines), `addons/shopify_connector_core/__manifest__.py`
  (version `19.0.1.4.0` -> `19.0.1.5.0`; one new `data` entry for the
  cron file), `docs/01-research/research-handoff.md` (this entry).
  **Not modified:** `shopify_connector_job_log.py` (the existing five
  `event_type` values -- `attempt`/`state_change`/`verification_read`/
  `manual_action`/`note` -- fully covered every log write this task
  needed; no sixth value was genuinely required), `shopify_connector_
  store.py`, `shopify_connector_store_credential.py`, `shopify_connector_
  store_settings.py`, `shopify_connector_location.py`, `shopify_connector_
  binding_mixin.py`, `shopify_connector_api_client.py`, `tools/
  redaction.py` (all read/called, never modified, exactly as forbidden),
  no security/ACL file (both new models are `AbstractModel`s, mirroring
  `shopify_connector_readiness_check.py`), no view/menu/action/wizard/
  webhook/OAuth/domain-module file of any kind.
- **What changed / residue fixed:** implemented the core sync-engine
  skeleton exactly per the issued final prompt's six accepted gate-
  opening decisions: **(A)** `_claim_for_dispatch()` on the job model
  uses `try_lock_for_update()` per candidate row, silently skipping a
  row it cannot lock, re-checking claimability under the lock (mirrors
  Odoo's own official "Writing cron functions" worked example) -- never
  a raw SQL `SKIP LOCKED` reimplementation, never a PostgreSQL advisory
  lock. **(B)** `shopify.connector.job.dispatch._get_handlers()` is a
  `job_type -> handler` dict-lookup registry seam, adapted (not copied)
  from the `_get_checks()` inheritance-append precedent -- a job routes
  to exactly one handler, a missing handler fails safely to
  `failed_final`/`unknown_system_error`, never hangs, never silently
  drops. **(C)** retry scheduling uses named, tunable constants (12 max
  attempts, 30s base, x2 multiplier, 30-minute cap, +/-20% jitter,
  24-hour window) plus a distinct 1-attempt "safety net" budget for
  `unknown_system_error` (architecture gate §E's own framing) -- bounded
  retries only, no infinite retries under any circumstance. **(D)** the
  enqueue/dispatch file split matches the accepted default exactly, both
  `AbstractModel`s, no `services/` package, no concrete model, no ACL
  file. **(E)** batch size 20 / cron interval 5 minutes, both named
  constants. **(F)** `core_dispatch_selftest` added inline to the
  existing static `job_type` selection list, used only by this task's
  own tests, never dispatched to a live Shopify call. Beyond the six
  decisions: the enqueue service is a thin `Job.create()` wrapper adding
  no new idempotency/scope-key mechanism (the existing `idempotency_key`/
  `operation_scope_key` unique constraints do the work, reused verbatim
  and proven via two collision tests each, using the established
  `mute_logger('odoo.sql_db')` + `cr.savepoint()` pattern); the DEC-009
  error-class taxonomy is fully and exhaustively mapped (all 16 fixed
  `ERROR_CLASS_SELECTION` values, cross-checked programmatically --
  see Learning feedback loop) across four routing buckets (auto-retry,
  manual-fix-then-retry, conservative-never-silent -> `failed_retryable`
  since `financial_total_mismatch` is not one of the six
  `manual_review_subreason` values, and the six operator-confirmation-
  required classes -> `blocked_manual_review` with a matching
  subreason); a new domain-enabled execution-time-only gating hook
  (`_domain_flag_for_job_type()`, DEC-013 §I.3) was added inside
  `write()`'s existing `state -> 'running'` branch, alongside (never
  replacing) the unmodified store-state re-check -- maps every job_type
  shipped in this repo to `None` today (a true no-op in production),
  tested only via a patched synthetic mapping, and proven never to run
  at `create()` time (so it cannot alter an enqueue-time decision); a
  third store-state checkpoint (`_invoke_handler`'s immediate pre-
  dispatch re-check) narrows -- and is documented everywhere as **not
  closing** -- the SRR-03 disconnect/in-flight-job race, exactly per
  Decision A's own explicit framing; `action_disconnect()`
  (`shopify_connector_store.py`) is untouched and proven (by test) to
  already cancel jobs reaching the three new non-terminal states this
  task makes reachable (`retry_waiting`/`failed_retryable`/
  `blocked_manual_review`), since none of the three was ever in
  `TERMINAL_JOB_STATES`.
- **Items deferred:** every item the gate-opening proposal/gate document
  named as preserved remains exactly as open as before this task --
  VAL-B2 (deferred/not passed), MBQ-05 (Partially routed/Open), **TD-002
  (confirmed still Open before any edit, not touched)**, the fulfillment
  API model, product first-sync dedup thresholds, token acquisition for
  many unrelated customers, Lite/Full packaging, the 16-vs-17
  `@idempotent` mutation-count and OCA `queue_job` worker-count wording
  discrepancies, checkpoint/resume ownership. **Live Odoo.sh runtime
  validation (§I of the implementation-scope document) is not performed
  by this session** -- cron drain firing in real Odoo runtime,
  concurrency behavior under multiple `--max-cron-threads`, a live
  SRR-03 reproduction, retry scheduling over real wall-clock time,
  failed-job visibility in a live registry, a live server-log token-leak
  grep, and savepoint/batch behavior at realistic volumes are all
  **explicitly named as a separate, later, follow-up validation pass**
  in this session's own PR body -- none is claimed as passed here. No
  claim is made anywhere in code, tests, or docs that the claim
  mechanism (Decision A) is proven safe under real concurrent-worker or
  multi-server execution.
- **Learning feedback loop:**
  - New issues discovered: none rising to a defect-pattern-log entry.
    One design subtlety worth naming for a future session: constructing
    a genuine two-real-transaction concurrency test for the claim
    mechanism is impractical inside Odoo's own `TransactionCase` harness
    (test-mode cursors share the enclosing transaction's sandbox, so a
    second `registry.cursor()` cannot observe uncommitted fixture data
    from the first) -- the claim-guard tests in
    `test_job_dispatch.py` therefore use `unittest.mock.patch.object` on
    `try_lock_for_update()` itself to prove the code-level "skip an
    already-locked row" contract, exactly as the gate-opening proposal's
    own §4 anticipated ("a test proving ... is a code-level proof, not a
    concurrent-worker proof") -- not a gap, but worth stating explicitly
    so a future session does not mistake the mock-based test for a
    stronger claim than it is.
  - Repeated issue patterns: none.
  - Rules/checklists updated: none this session (no repeated-issue
    threshold reached).
  - New rejected approaches: none.
  - New technical debt: none -- no compromise was knowingly accepted;
    `technical-debt-register.md` is unmodified (TD-002 confirmed Open,
    not touched, per this task's own explicit instruction).
  - Architecture concerns: none beyond what DEC-025/the gate-opening
    proposal already flagged (SRR-03 narrowed-not-closed; the claim
    mechanism's real concurrency safety unproven by unit tests; the
    batch-size/interval defaults unvalidated at realistic volume) --
    all restated, not resolved, by this task, exactly as required.
  - Tests or review gates needed: a **separate, later, live Odoo.sh
    validation session** (mirroring Task 004/005's own
    `task-00X-validation-results.md` precedent) is the concrete next
    gate this task's own PR body names but does not itself satisfy.
  - Should future prompts change? No.
  - **Self-verification performed this session (no live Odoo available):**
    `python3 -m py_compile` on every new/modified file; a standalone
    Python script replicating each new AST-based source-level test
    (sudo-site count, `job_dispatch.py` zero-`.create(`-calls,
    `job_enqueue.py`'s sole `.create(` target, no Shopify-API-client
    reference in either new production file) -- all passed; an
    independent numerical re-derivation of the retry backoff/jitter
    formula against every bound assertion in
    `test_job_retry_scheduling.py` (attempt 0, attempt 3, the 30-minute
    cap, and the deterministic `random.uniform`-patched case) -- all
    passed; a full manual line-by-line trace of every new test's control
    flow against the production code for correctness (state
    transitions, gating order, constraint interactions).
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next recommended session:** a live Odoo.sh runtime-validation pass
  for this PR (mirroring `task-004-validation-results.md`/
  `task-005-validation-results.md`) -- install the module fresh, run the
  full `shopify_connector_core` test suite (must show all pre-existing
  tests plus this task's new tests passing, zero domain modules
  installed), then exercise the §I runtime-validation checklist items
  this session's PR body names as not yet performed.
- **Stop condition:** implementation complete per the issued final
  prompt's exact allowed-files list; no domain-module task, no further
  Task 006 sub-slice, and no other next-feature work started in this
  session. Stopping here to open the PR as **draft** and await ChatGPT's
  own review, per the final prompt's own closing instruction.

---

### Task 006D — PR #130 consistency patch — compact handoff (2026-07-09)

- **Branch / PR:** `claude/task-006d-sync-engine-gate-opening-fp33xo` →
  PR #130 into `Shopify-connector` (**draft**, unmerged; same PR, revised
  in place — no new PR opened). Applies a narrow consistency patch per
  control-room review (GitHub review artifact/comment ID `4921331441`),
  following up on the prior acceptance-status patch (review artifact/
  comment ID `4658949628`).
- **Problem fixed:** the prior acceptance patch was directionally correct
  but left stale pre-acceptance wording inside two repo documents.
- **Files changed:**
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-gate.md`
  (§A rewritten to state plainly that ChatGPT accepted this gate document
  and the six gate-opening choices, that the gate is accepted but not yet
  effective because PR #130 has not merged, and that implementation still
  requires a separate post-merge prompt issuance; §B's final-prompt and
  gate-opening-proposal status lines updated from stale
  "Final draft / Pending gate acceptance" and "Proposed for ChatGPT
  gate-opening review" to their actual accepted statuses; §D's "if
  accepted and merged" / stale-status wording fixed to reflect the prompt
  is already accepted, only merge is pending),
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`
  (the two "DEFAULT proposal" mentions, in the allowed-files entries for
  `shopify_connector_job_enqueue.py`/`shopify_connector_job_dispatch.py`,
  replaced with "accepted file split, Decision D" — merge-commit-SHA
  placeholder untouched, prompt not issued),
  `docs/05-qa/task-006d-gate-opening-review-checklist.md` (§19 updated —
  no longer says "No revisions required"; records that a consistency
  patch was required and has been applied), `docs/01-research/
  research-handoff.md` (this entry). **Not modified:**
  `task-006c-sync-engine-gate-opening-proposal.md`,
  `architecture-review-log.md`,
  `task-006c-sync-engine-skeleton-implementation-scope.md` (all
  forbidden this session); no `addons/**` file.
- **No code.** No implementation authorized. This patch fixes wording
  only — it does not select, revise, or reopen any of the six accepted
  gate-opening decisions.
- **Final prompt not issued.** Status remains **Accepted final prompt /
  Not issued**; the `<TASK_006D_GATE_MERGE_COMMIT_SHA>` placeholder
  remains unresolved and untouched by this patch.
- **Gate document remains accepted, still not effective** — the gate
  becomes effective only once PR #130 merges into `Shopify-connector`,
  and implementation still requires ChatGPT to separately paste the
  finalized prompt (merge-commit SHA filled in) into a new Claude Code
  session.
- **Every preserved open item remains exactly as open as before:** VAL-B2
  deferred/not passed; MBQ-05 Partially routed/Open; TD-002 Open;
  fulfillment API model unresolved; product first-sync dedup thresholds
  still domain-design work; token acquisition for many unrelated
  customers unresolved; Lite/Full packaging not finalized; checkpoint/
  resume ownership still undecided; multi-server/Odoo.sh runtime
  concurrency proof still explicitly required. None of these is touched
  by this wording fix.
- **Items deferred:** none new.
- **Learning feedback loop:** new issue discovered: stale pre-acceptance
  wording can survive an acceptance-status patch if only the header/status
  lines are updated and cross-referenced body prose is not swept for the
  same phrases — captured as a review discipline for future
  acceptance-status patches (re-grep the whole document for "if and when,"
  "would authorize," "DEFAULT," "Pending," and "Proposed" after any status
  flip, not just the header). Repeated issue pattern: this is the second
  Task 006D control-room round to catch stale wording (the first
  acceptance patch itself already fixed several such phrases; this round
  catches ones it missed) — worth treating status-flip patches as
  requiring a full-document grep sweep, not a targeted header edit, going
  forward. Rules/checklists updated:
  `task-006d-gate-opening-review-checklist.md` §19. New rejected
  approaches: none. New technical debt: none. Architecture concerns: none.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · repeated-issue pattern noted above (not yet
  escalation-worthy — two occurrences, same root cause, now named).
- **Next step:** ChatGPT's final merge review of PR #130.
- **Stop condition:** docs-only consistency patch, no code touched, no
  implementation authorized, no gate opened, no prompt issued, no merge
  commit SHA filled in. Stopped after pushing to the same PR #130 branch
  and updating the PR body. No merge performed. PR remains draft/unmerged,
  awaiting ChatGPT's final merge review.

---

### Task 006D — PR #130 acceptance-status patch — compact handoff (2026-07-09)

- **Branch / PR:** `claude/task-006d-sync-engine-gate-opening-fp33xo` →
  PR #130 into `Shopify-connector` (**draft**, unmerged; same PR, revised
  in place — no new PR opened). Applies ChatGPT's content-level acceptance
  of the Task 006D gate-opening decision package, per control-room review
  (GitHub review artifact/comment ID `4658949628`).
- **Task 006D gate-opening package accepted by ChatGPT (2026-07-09).**
- **Six choices accepted** (the Task 006C implementation basis, per
  gate-opening proposal §6):
  - **A:** `try_lock_for_update()` per candidate job row, skip
    locked/unavailable rows, never raw SQL `SKIP LOCKED`, never a
    PostgreSQL advisory lock.
  - **B:** new `_get_handlers()` registry seam on a
    `shopify.connector.job.dispatch` `AbstractModel`, adapting (not
    copying) the `_get_checks()` precedent.
  - **C:** retry defaults — 12 attempts / 30s base / ×2 multiplier /
    30-minute cap / ±20% jitter / 24-hour window.
  - **D:** enqueue + dispatch `AbstractModel` split
    (`shopify_connector_job_enqueue.py` +
    `shopify_connector_job_dispatch.py`).
  - **E:** batch size 20 / cron interval 5 minutes.
  - **F:** core diagnostic `job_type` — `core_dispatch_selftest`.
- **Files changed:**
  `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`
  (Status → Accepted by ChatGPT, 2026-07-09; new Acceptance note; §9
  conditions 1–2 marked satisfied),
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-gate.md`
  (Status → Accepted by ChatGPT, 2026-07-09; new Acceptance note; §K
  conditions 1–2 marked satisfied), `docs/07-implementation-plan/
  task-006c-sync-engine-skeleton-final-prompt.md` (Status → **Accepted
  final prompt / Not issued**; new Acceptance note; merge-commit-SHA
  placeholder `<TASK_006D_GATE_MERGE_COMMIT_SHA>` deliberately left
  unresolved), `docs/05-qa/architecture-review-log.md` (AR-031 → Status
  **Accepted**), `docs/05-qa/task-006d-gate-opening-review-checklist.md`
  (§18/§19 completed — Overall decision: Accepted), `docs/01-research/
  research-handoff.md` (this entry). **Not modified:**
  `task-006c-sync-engine-skeleton-implementation-scope.md` (forbidden this
  session); no `addons/**` file.
- **Gate-opening proposal accepted.** **Gate document accepted.** **Final
  prompt accepted but not issued** — it must still not be pasted/run.
  **Merge-commit-SHA placeholder remains unresolved** — this PR has not
  merged, so the value cannot be known yet, and this patch does not fill
  it.
- **No implementation yet.** This acceptance patch does not create,
  modify, or imply any addon/Python/XML/CSV/security/manifest/migration/
  CI file. **No implementation gate is open** — the gate becomes effective
  only once PR #130 merges into `Shopify-connector`, and implementation
  starts only once ChatGPT separately pastes the finalized final prompt
  (merge-commit SHA filled in) into a **new** Claude Code session.
- **Every preserved open item remains exactly as open as before:** VAL-B2
  deferred/not passed; MBQ-05 Partially routed/Open; TD-002 Open;
  fulfillment API model unresolved; product first-sync dedup thresholds
  still domain-design work; token acquisition for many unrelated customers
  unresolved; Lite/Full packaging not finalized; checkpoint/resume
  ownership still undecided; multi-server/Odoo.sh runtime concurrency
  proof still explicitly required. None of these is touched, resolved, or
  narrowed by accepting the six choices above.
- **Items deferred:** none new.
- **Learning feedback loop:** new issues discovered: none — this patch
  applies a clean content-level acceptance outcome, with every
  non-implementation guardrail restated, not weakened. Repeated issue
  patterns: none. Rules/checklists updated:
  `task-006d-gate-opening-review-checklist.md` §18/§19 completed to
  reflect the recorded acceptance outcome. New rejected approaches: none.
  New technical debt: none. Architecture concerns: none beyond what
  DEC-025/the scope package already flagged (carried forward unchanged).
  Should future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** ChatGPT's final merge review of PR #130. After it merges,
  ChatGPT pastes the finalized final prompt (merge-commit SHA filled in)
  into a **new** Claude Code session, as its own turn, to start the Task
  006C implementation session — **not started, not performed, and not
  authorized by this patch.**
- **Stop condition:** docs-only acceptance-status patch, no code touched,
  no implementation authorized, no gate opened, no prompt issued, no
  merge commit SHA filled in. Stopped after pushing to the same PR #130
  branch. No merge performed. PR remains draft/unmerged, awaiting
  ChatGPT's final merge review.

---

### Task 006D — sync-engine skeleton gate-opening decision package — compact handoff (2026-07-09)

- **Branch / PR:** `claude/task-006d-sync-engine-gate-opening-fp33xo` → PR
  into `Shopify-connector` (**draft**, to be opened this session). Based
  on `origin/Shopify-connector` HEAD
  `241871b70f8151d8b796dbb4fb7bcb69cc3b2db3` (PR #129 merge commit),
  confirmed the tip of that branch before any edit.
- **Files changed:**
  `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`
  (revised — Status: Proposed for ChatGPT gate-opening review / Does not
  open gate yet; added §6 "Proposed gate-opening decisions"),
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`
  (revised — Status: Final draft / Pending gate acceptance / Not issued;
  all placeholders except the merge-commit SHA resolved),
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-gate.md`
  (new — Status: Proposed / Pending ChatGPT review),
  `docs/05-qa/task-006d-gate-opening-review-checklist.md` (new),
  `docs/05-qa/architecture-review-log.md` (AR-031 row added, Status:
  Proposed, mirroring the AR-026/AR-029 Task 002/003 gate-opening-note
  convention), `docs/01-research/research-handoff.md` (this entry).
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-
  implementation-scope.md` was **not** modified (explicitly forbidden
  this session). No addon file was modified — the five named model files
  were read for decision accuracy only.
- **Proposed concrete choices for the six open items** (gate-opening
  proposal §6, all **[Recommendation]**, not yet ChatGPT-accepted): (A)
  concurrency mechanism — `try_lock_for_update()` per candidate job row,
  skip locked/unavailable rows, no raw SQL `SKIP LOCKED`, no PostgreSQL
  advisory locks; (B) handler-registry seam — new `_get_handlers()` seam
  on a `shopify.connector.job.dispatch` `AbstractModel`, adapting (not
  copying) `_get_checks()`, safe missing-handler failure; (C) retry
  defaults — 12 attempts / 30s base / ×2 / 30-minute cap / ±20% jitter /
  24-hour window, named/tunable; (D) file split —
  `shopify_connector_job_enqueue.py` + `shopify_connector_job_dispatch.py`,
  both `AbstractModel`s, no services package, no ACL file; (E) cron
  batch/interval — batch size 20, interval 5 minutes, conservative
  pending runtime validation; (F) diagnostic `job_type` —
  `core_dispatch_selftest`, core/diagnostic-only, never calls Shopify,
  never a domain-sync template.
- **No code was authorized. No implementation gate was opened.** The
  gate-opening proposal reads "Proposed for ChatGPT gate-opening review /
  Does not open gate yet"; the new gate document reads "Proposed /
  Pending ChatGPT review"; the final prompt reads "Final draft / Pending
  gate acceptance / Not issued" (still not issued; merge-commit-SHA
  placeholder `<TASK_006D_GATE_MERGE_COMMIT_SHA>` deliberately left
  unresolved, since this PR has not merged).
- **AR-031 added** to `architecture-review-log.md`, Status **Proposed**
  (not Accepted) — mirroring the repo's own established convention that a
  gate-opening act is recorded as its own AR row (confirmed by inspecting
  the AR-026/AR-029 Task 002/003 gate-opening-note precedent before
  drafting).
- **Every preserved open item remains exactly as open as before:**
  VAL-B2 deferred/not passed; MBQ-05 Partially routed/Open; TD-002 Open;
  fulfillment API model unresolved; product first-sync dedup thresholds
  still domain-design work; token acquisition for many unrelated
  customers unresolved; Lite/Full packaging not finalized; the 16-vs-17
  `@idempotent` mutation-count and OCA `queue_job` worker-count wording
  discrepancies both still open/non-blocking; checkpoint/resume ownership
  still undecided; multi-server/Odoo.sh runtime concurrency proof still
  explicitly required. None of these is touched, resolved, or narrowed by
  this package — every one is restated unchanged in §7 of the revised
  gate-opening proposal and §J of the new gate document.
- **Self-correction (red-team) passes run this session:** authorization-
  leakage grep across all changed files (no "gate is open"/"implementation
  authorized"/"Claude may begin"/unqualified "issued" wording found
  outside quoted/negated context); open-choice consistency across the
  four decision-bearing documents (gate-opening proposal, final prompt,
  gate document, QA checklist — no conflicting default found); scope-creep
  check (no domain sync, no UI/wizard, no webhook controller, no OAuth, no
  live Shopify call anywhere in the package); architecture-consistency
  check (every choice traces back to DEC-025/PR #129; OCA `queue_job`
  remains reference-only; no rejected approach reintroduced; no claim that
  `try_lock_for_update()` is proven safe under real workers); final-prompt
  readiness check (copy-ready except the merge-commit SHA; allowed/
  forbidden files and tests match the accepted scope document exactly).
- **Items deferred:** none new.
- **Learning feedback loop:** new issues discovered: none. Repeated issue
  patterns: none. Rules/checklists updated: new
  `task-006d-gate-opening-review-checklist.md` created for this package.
  New rejected approaches: none. New technical debt: none. Architecture
  concerns: none beyond what DEC-025/the scope package already flagged
  (carried forward unchanged). Should future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** ChatGPT review of this gate-opening decision package
  (`docs/05-qa/task-006d-gate-opening-review-checklist.md`) — accept,
  revise, or reject. **If accepted and this PR merges, implementation
  still does not start automatically** — ChatGPT must separately paste
  the finalized final-prompt text (merge-commit SHA filled in) into a
  **new** Claude Code session, as its own turn. **This is not a coding
  session; no gate is opened by this patch.**
- **Stop condition:** docs-only gate-opening decision package, no code
  touched, no implementation authorized, no gate opened, no merge
  commit SHA filled in (this PR has not merged). Stopped after opening
  this PR as draft against `Shopify-connector`. No merge performed.

---

### Task 006C — PR #129 acceptance-status patch — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006c-sync-engine-scope-pmj6ta` → PR #129
  into `Shopify-connector` (**draft**, unmerged; same PR, revised in
  place — no new PR opened). Applies ChatGPT's content-level acceptance
  of the Task 006C implementation-scope package, per control-room review
  (GitHub review artifact/comment ID `4920363287`).
- **Files changed:**
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md`
  (Status → Accepted by ChatGPT as planning/scope package, acceptance
  date 2026-07-08; new Acceptance note added), `docs/05-qa/task-006c-pre-
  implementation-review-checklist.md` (§14 Overall review decision
  recorded as accepted-as-planning/scope-package-only), `docs/01-research/
  research-handoff.md` (this entry). **Not modified:**
  `task-006c-sync-engine-skeleton-final-prompt.md`,
  `task-006c-sync-engine-gate-opening-proposal.md`,
  `architecture-review-log.md`.
- **What changed / residue fixed:** the Task 006C **implementation-scope
  package is now accepted, content-wise, as a planning/scope package
  only** — the underlying scope document's substance (§A–§L) is
  unchanged by this patch; only its status block and a new Acceptance
  note were added. **No code was authorized. No implementation gate was
  opened. The final prompt was not issued or accepted — it remains
  Draft only / Not issued, unmodified. The gate-opening proposal was not
  accepted — it remains Proposed only / Does not open the gate,
  unmodified.** No placeholder in the final-prompt draft was filled. The
  execution-time claim/concurrency mechanism (§F item 1) and the
  handler-registry seam shape (§F item 4) both remain undecided
  candidates requiring ChatGPT approval in a future, separate
  gate-opening act — this acceptance does not select either.
- **Open choices preserved, unchanged by this acceptance:** the
  execution-time claim/concurrency mechanism; the handler-registry seam
  shape; the retry-default constants; the enqueue/dispatch file split;
  the cron batch-size default — none is confirmed or selected by this
  patch, all remain for a future gate-opening act.
- **Every preserved open item remains exactly as open as before:**
  VAL-B2 deferred/not passed; MBQ-05 Partially routed/Open; TD-002 Open;
  fulfillment API model unresolved; product first-sync dedup thresholds
  still domain-design work; token acquisition for many unrelated
  customers unresolved; Lite/Full packaging not finalized; the 16-vs-17
  `@idempotent` mutation-count and OCA `queue_job` worker-count wording
  discrepancies both still open/non-blocking; multi-server/Odoo.sh
  runtime concurrency proof still explicitly required. None of these was
  touched by this patch.
- **`architecture-review-log.md` was not modified** — unchanged from the
  prior session; this acceptance patch proposes no new architecture
  decision and records no new AR row.
- **Items deferred:** none new.
- **Learning feedback loop:** new issues discovered: none — this patch
  applies a clean content-level acceptance outcome, with every
  non-implementation guardrail restated, not weakened. Repeated issue
  patterns: none. Rules/checklists updated: `task-006c-pre-
  implementation-review-checklist.md` §14 updated to reflect the
  recorded acceptance outcome. New rejected approaches: none. New
  technical debt: none. Architecture concerns: none beyond what DEC-025
  already flagged (carried forward unchanged). Should future prompts
  change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** a future, separately-scoped, separately-authorized
  Task 006C gate-opening-decision session (to fix the still-open
  candidates and separately accept the gate-opening proposal and issue
  the final prompt) or a distinct future Task 006D — **neither is
  started, selected, or authorized by this patch.** **This is not a
  coding session.**
- **Stop condition:** docs-only acceptance-status patch, no code
  touched, no implementation authorized, no gate opened. Stopped after
  pushing to the same PR #129 branch. No merge performed. PR remains
  draft/unmerged, awaiting ChatGPT's final merge review.

---

### Task 006C — sync-engine skeleton implementation-scope package — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006c-sync-engine-scope-pmj6ta` → PR into
  `Shopify-connector` (**draft**, to be opened this session). Based on
  `origin/Shopify-connector` HEAD `a45e0a6` (PR #128 merge commit),
  confirmed an ancestor before any edit.
- **Files changed:**
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-implementation-scope.md`
  (new — Status: Proposed / Pending ChatGPT review),
  `docs/07-implementation-plan/task-006c-sync-engine-skeleton-final-prompt.md`
  (new — Status: Draft only / Not issued),
  `docs/07-implementation-plan/task-006c-sync-engine-gate-opening-proposal.md`
  (new — Status: Proposed only / Does not open the gate),
  `docs/05-qa/task-006c-pre-implementation-review-checklist.md` (new),
  `docs/01-research/research-handoff.md` (this entry).
  `docs/05-qa/technical-debt-register.md` was **not** modified — no new
  technical debt was discovered this session.
- **What changed / residue fixed:** Task 006C did not exist before this
  session. This session created the full **future-implementation-scope
  package** for a controlled core sync-engine skeleton inside
  `shopify_connector_core` — mapping DEC-025's seven accepted architecture
  decisions to a proposed enqueue service, `ir.cron` drain/claim loop,
  handler-registry seam, retry scheduler, duplicate-running guards
  (creation- and execution-time), permanent-failure/blocked-manual-review
  transitions, sanctioned job-log integration with existing redaction, a
  new domain-enabled execution-time gating hook (no domain module), and
  lifecycle handling building on the existing `action_disconnect()`
  sweep. Every open implementation choice is labeled selected / candidate
  requiring ChatGPT approval / deferred (scope document §F) — most
  notably, the execution-time job-claiming concurrency mechanism is left
  as a **candidate requiring ChatGPT approval**, not selected, since
  DEC-025 explicitly withheld that selection. No domain sync logic, no
  live Shopify call, no webhook controller, and no UI/setup-wizard work
  is proposed anywhere in the package. `addons/shopify_connector_core/`
  code (all five named model files plus the eight existing test files)
  was **read in full for planning only and not modified**.
- **No implementation was authorized. No implementation gate was
  opened.** The implementation-scope document reads "Proposed / Pending
  ChatGPT review"; the final prompt reads "Draft only / Not issued" (its
  concurrency-mechanism and merge-commit-SHA placeholders remain
  unresolved); the gate-opening proposal reads "Proposed only / Does not
  open the gate."
- **Every preserved open item remains exactly as open as before:**
  VAL-B2 deferred/not passed; MBQ-05 Partially routed/Open; TD-002 Open;
  fulfillment API model unresolved; product first-sync dedup thresholds
  still domain-design work; token acquisition for many unrelated
  customers unresolved; Lite/Full packaging not finalized; the 16-vs-17
  `@idempotent` mutation-count and OCA `queue_job` worker-count wording
  discrepancies both still open/non-blocking; multi-server/Odoo.sh
  runtime concurrency proof still explicitly required. None was
  resolved, narrowed, or silently decided by this package.
- **`architecture-review-log.md` was not modified.** This package
  proposes no new architecture decision (it scopes future implementation
  work against the already-accepted DEC-025/gate, it does not propose a
  new AR-numbered architecture question) — flagged explicitly here per
  the task's own instruction to raise this for ChatGPT's judgment if
  uncertain.
- **Items deferred:** the exact enqueue/dispatch file split, the exact
  concurrency mechanism, the retry-default constants, and the cron
  batch-size default are all named as open implementation-time choices
  for ChatGPT's gate-opening act to fix (scope document §F, gate-opening
  proposal §6) — none is fixed by this session.
- **Learning feedback loop:** new issues discovered: the session's own
  mandatory 4-pass red-team self-correction loop (run before commit, via
  four independent review lenses) found and fixed one blocking and three
  should-fix issues in the first draft, all self-caught, none surviving
  to this commit: (1) **blocking** — the drafted §H tests for "handler
  registry dispatch" had no allowed-files-compliant way to construct a
  dispatchable job, since `job_type` is a closed Selection with zero
  domain values registered and the draft never authorized adding one;
  fixed by explicitly authorizing exactly one new core/diagnostic
  `job_type` value (`core_dispatch_selftest`) scoped to this task's own
  tests. (2) The handler-registry seam shape was mislabeled "selected"
  when DEC-025 itself lists it as one of three brand-new open
  architecture questions the gate surfaces; relabeled "candidate
  requiring ChatGPT approval," consistent with how the concurrency
  mechanism and checkpoint/resume ownership are already treated. (3) A
  cross-reference pointed the SRR-03-narrowing store-state re-check at
  the wrong `§F` item (item 5, "domain-enabled gating hook," an unrelated
  mechanism); fixed by adding a correctly-labeled new item 9 and
  repointing every reference. (4) The final-prompt draft hard-coded the
  enqueue/dispatch file split as settled when the gate-opening proposal
  itself still lists it as open; fixed by adding an explicit
  "File-split note" hedge. Repeated issue patterns: none (first Task
  006C session). Rules/checklists updated: the new
  `task-006c-pre-implementation-review-checklist.md` now includes an
  explicit allowed-files cross-list-consistency check and a
  placeholder-completeness check, added directly in response to findings
  (3)/(4) above. New rejected approaches: none (checked
  `rejected-approaches-log.md` before drafting, per `CLAUDE.md` §10 — no
  approach proposed here has been rejected; none is reintroduced). New
  technical debt: none — every finding was fixed in this same session,
  before commit, not deferred. Architecture concerns: none beyond what
  DEC-025 already flagged (carried forward unchanged). Should future
  prompts change? No — the self-correction loop caught these before
  commit, exactly as `CLAUDE.md`'s red-team-pass instruction intends.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** ChatGPT reviews this package against
  `docs/05-qa/task-006c-pre-implementation-review-checklist.md` and
  either accepts, requests revision, or rejects it. **This is not a
  coding session** and does not itself open the Task 006C implementation
  gate — that requires the separate act described in the gate-opening
  proposal's §5.
- **Stop condition:** docs-only implementation-scope package, no code
  touched, no implementation authorized, no gate opened. Stopped after
  opening a draft PR against `Shopify-connector`. No merge performed.

---

### Task 006B — PR #128 acceptance patch — DEC-025 / AR-030 accepted — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006b-sync-engine-gate-865mw5` → PR #128 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened). Applies ChatGPT's acceptance of the sync-engine
  architecture gate, per control-room review, after the prior revisions'
  governance fixes (direct baseline-file inspection; the `AR-030` addition;
  the stale-wording consistency fix).
- **Files changed:** `docs/04-decisions/DEC-025-task-006-sync-engine-gate.md`
  (Status → Accepted by ChatGPT, 2026-07-08; new Acceptance note added),
  `docs/05-qa/architecture-review-log.md` (`AR-030` row → Accepted by
  ChatGPT, Status → Accepted; only this one row touched, no other AR row
  altered), `docs/05-qa/task-006b-architecture-gate-review-checklist.md`
  (overall review decision recorded as accepted; DEC-025/`AR-030`
  acceptance confirmed), `docs/01-research/research-handoff.md` (this
  entry).
- **What changed / residue fixed:** **DEC-025 is now `Accepted by
  ChatGPT`** (acceptance date 2026-07-08) — the architecture gate itself
  (`docs/03-architecture/sync-engine-architecture-gate.md`, unchanged by
  this patch) is accepted as the architecture-level shape for the future
  domain-neutral sync engine. **`AR-030` is now `Accepted`**, mirroring
  DEC-025 exactly, with its Follow-up action column stating explicitly that
  future Task 006C implementation-scope drafting may be proposed in a
  separate session but no implementation is authorized by `AR-030`/DEC-025
  itself. Every internally-contradictory "Proposed" framing left over from
  the pre-acceptance drafting (top blockquote, Status section, "Proposed
  architecture decisions" heading, Consequences/Follow-ups wording, the
  Architecture-review-log note, and the "No implementation authorized"
  section) was updated for tense consistency with the new Accepted status,
  while preserving every non-implementation guardrail verbatim in substance.
- **No implementation was authorized. No implementation-scope file was
  created.** No addon file, Python, XML, CSV, manifest, security,
  migration, CI/workflow, controller, view, wizard, OAuth, or domain-sync
  code was created or modified. `docs/07-implementation-plan/
  task-006-sync-engine-implementation-scope.md` and `docs/07-
  implementation-plan/task-006c-sync-engine-implementation-scope.md` do not
  exist and were not created.
- **Every Task 006A open item remains preserved, exactly as open as
  before:** VAL-B2 deferred/not passed; MBQ-05 Partially routed/Open (token
  acquisition for many unrelated customers unresolved); TD-002 Open;
  fulfillment API model unresolved; product first-sync dedup thresholds
  still domain-design work; Lite/Full packaging not finalized; the
  16-vs-17 `@idempotent` mutation-count and OCA `queue_job` worker-count
  wording discrepancies both still open/non-blocking; multi-server/Odoo.sh
  runtime concurrency proof still explicitly required before any future
  implementation relies on a concurrency assumption named in the gate. None
  of these was resolved, narrowed, or silently decided by this acceptance
  patch.
- **Items deferred:** none new.
- **Learning feedback loop:** new issues discovered: none — this patch
  applies a clean acceptance outcome, with no new governance gap found.
  Repeated issue patterns: none. Rules/checklists updated:
  `task-006b-architecture-gate-review-checklist.md`'s DEC-025-status,
  AR-log, and overall-review-decision sections updated to reflect
  acceptance. New rejected approaches: none. New technical debt: none.
  Architecture concerns: none beyond what Task 006A already flagged
  (carried forward unchanged, per DEC-025's Acceptance note). Should future
  prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** a future Task 006C implementation-scope proposal — a
  **separately-scoped, separately-authorized** session, not started, not
  drafted, and not implied by this acceptance patch. **This is not a coding
  session** and does not itself open the implementation gate
  (`../05-qa/quality-feedback-loop.md` §10, `CLAUDE.md` §5/§9 both still
  apply).
- **Stop condition:** docs-only acceptance patch, no code touched, no
  implementation authorized, no implementation-scope file created. Stopped
  after pushing to the same PR #128 branch. No merge performed. PR remains
  draft/unmerged, awaiting ChatGPT's final merge review.

---

### Task 006B — PR #128 revision — governance corrections (AR-log row + direct baseline inspection) — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006b-sync-engine-gate-865mw5` → PR #128 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened). Revises the initial version per control-room review
  (GitHub review artifact/comment ID `4918187862`), which found the PR
  directionally strong but not yet acceptable on two points.
- **Files changed:** `docs/03-architecture/sync-engine-architecture-gate.md`
  (revised), `docs/04-decisions/DEC-025-task-006-sync-engine-gate.md`
  (revised), `docs/05-qa/task-006b-architecture-gate-review-checklist.md`
  (revised), `docs/05-qa/architecture-review-log.md` (new `AR-030` row
  added), `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:**
  1. **Directly read, in full, the two pre-006A baseline sources** —
     `docs/01-research/shopify-official-api-notes.md` (917 lines) and
     `docs/01-research/odoo-official-architecture-notes.md` (803 lines) —
     which the initial PR version had cited only via the Task 006A synthesis
     layer, not independently. Direct inspection **confirmed, rather than
     changed**, this gate's proposed architecture content: every fact the
     gate cites from these two baselines is present and unchanged in the
     baseline text, and every fact the gate cites that goes beyond the
     baselines (GraphQL HTTP-200/`THROTTLED`-body behavior, `SKIP LOCKED`/
     `lock_for_update()` precedent, the >64-savepoint warning, `retrying()`'s
     RPC-layer retry, the 16-vs-17 `@idempotent` count discrepancy) is
     correctly attributed to Task 006A's own deeper source-level research,
     not to these baselines. One genuine sharpening was found and named
     explicitly in the gate document's new "Revision note": the baseline
     describes `ir.cron`'s deactivation as notifying "the DB admin," while
     Task 006A's source-level reading found the base `_notify_admin()` is a
     log-line-only no-op by default — already correctly cited at the sharper
     level in this gate's §C/§E via `O7`/SRR-05, so no content change was
     needed there. **No material architecture change was required** by this
     direct inspection.
  2. **Added `AR-030`** to `docs/05-qa/architecture-review-log.md` for this
     proposal, after inspecting the log's complete existing `AR-0##`
     sequence (highest prior: `AR-029`, 2026-07-07) to confirm `030` is the
     correct next number. `AR-030`'s Review decision and Status both read
     "Proposed for ChatGPT review — NOT YET ACCEPTED" / "Proposed,"
     mirroring DEC-025's own status exactly — **not** marked Accepted.
  3. Updated DEC-025's "Architecture-review-log note" to state the row is
     now added (replacing the prior version's explanation of why no row was
     added), and added the two baseline sources to DEC-025's evidence list,
     noting they were directly read this revision.
  4. Updated `docs/05-qa/task-006b-architecture-gate-review-checklist.md`'s
     architecture-review-log and Task-006A-coverage items so a reviewer can
     confirm: the `AR-030` row exists, it is not marked Accepted, DEC-025
     remains Proposed/Pending, and the two baseline files were directly
     read.
- **No new rejected approach was created; no implementation was
  authorized; no implementation-scope file was created.** DEC-025's
  `Status` remains **"Proposed / Pending ChatGPT review"** — not Accepted.
  `AR-030`'s Status remains **"Proposed"** — not Accepted. Every Task 006A
  open blocker (VAL-B2, MBQ-05, TD-002, fulfillment API model, product
  first-sync dedup thresholds, Lite/Full packaging, the 16-vs-17 mutation
  count and OCA `queue_job` worker-count discrepancies, multi-server/
  Odoo.sh runtime concurrency proof) remains exactly as open as the prior
  revision left it — none was silently resolved by this revision.
- **Items deferred:** none new; the `architecture-review-log.md` gap
  flagged in the prior revision's handoff entry is now resolved (row
  added), not deferred further.
- **Learning feedback loop:** new issues discovered: two governance gaps
  from the initial PR version (missing `architecture-review-log` row;
  baseline files not independently re-read) — both fixed this revision, both
  logged here rather than silently corrected. Repeated issue patterns: none
  (first occurrence of both categories for this task). Rules/checklists
  updated: `task-006b-architecture-gate-review-checklist.md` gained explicit
  checks for both. New rejected approaches: none. New technical debt: none.
  Architecture concerns: none beyond what Task 006A already flagged (carried
  forward unchanged). Should future prompts change? No — the original task
  prompt already listed both baseline files as required inputs; the gap was
  in how the first pass satisfied that requirement (synthesis-layer citation
  instead of direct read), not in the prompt itself.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** ChatGPT re-review of PR #128 (revised) and its `AR-030` /
  DEC-025 proposal.
- **Stop condition:** docs-only revision, no code touched, no implementation
  authorized, DEC-025 and `AR-030` both left Proposed/Pending, not Accepted.
  Stopped after pushing to the same PR #128 branch. No merge performed. PR
  remains draft/unmerged.

---

### Task 006B — sync engine architecture gate proposal — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006b-sync-engine-gate-865mw5` (harness-
  designated session branch, based on `origin/Shopify-connector` HEAD
  `3207791412ebedbc83eceaf70592df8c8df0d97a` — the PR #127 merge commit,
  confirmed an ancestor before any edit) → target `Shopify-connector`,
  **draft**, opened this session. Note: the task prompt's suggested branch
  name (`claude/task-006b-sync-engine-architecture-gate`) was not used — the
  harness had already assigned and checked out
  `claude/task-006b-sync-engine-gate-865mw5` per this session's Git
  Development Branch Requirements, and per governance this session developed
  on the harness-assigned branch rather than creating a second one.
- **Files changed:** `docs/03-architecture/sync-engine-architecture-gate.md`
  (new), `docs/04-decisions/DEC-025-task-006-sync-engine-gate.md` (new),
  `docs/05-qa/task-006b-architecture-gate-review-checklist.md` (new),
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** converted the accepted Task 006A
  research package (PR #123 competitor/common-pattern research, PR #124
  Odoo/repo substrate research, PR #126 queue/idempotency/retry/backoff/
  dead-letter research, PR #125 final synthesis/evidence map, PR #127
  completeness audit — all confirmed merged and ancestor-verified) into a
  **proposed architecture gate** for the future domain-neutral sync engine.
  Synthesized: architecture principles (domain-neutrality, no duplicate
  domain queue/retry/log engines, trigger convergence, webhook
  enqueue-only, core/domain ownership split, extension seams); a proposed
  core-engine shape (job creation/enqueue, drain loop, dispatcher, handler
  registry, retry scheduling, idempotency/duplicate-running guardrails,
  manual-review surface, checkpoint/resume, audit trail, redaction, gating,
  disconnect/reconnect lifecycle); a job-trigger model (manual/scheduled/
  webhook/reconciliation/`odoo_event`, all converging on one job mechanism,
  trigger source kept distinct from job type); a retry/failure policy
  (DEC-009's classified taxonomy, Shopify REST 429/`Retry-After` and GraphQL
  HTTP-200/`THROTTLED`-body handling, MBQ-16 planning-default backoff
  constants); a layered idempotency/duplicate-prevention architecture
  (core-owned job key + serialization guard + webhook dedup vs.
  domain-owned `@idempotent`/binding rules); the Odoo execution substrate
  (`ir.cron` as Phase 1 primitive, OCA `queue_job` reference-only/RA-004
  unchanged, savepoint performance constraint, three-shard-corroborated
  concurrency open questions); Shopify API implications (GraphQL-preferred,
  cost/rate-limit awareness, cursor/bulk-operation checkpoint trade-offs,
  non-guaranteed webhook delivery); a core-vs-domain responsibility table;
  and an MVP-implication section stating explicitly that no implementation,
  Task 006C, or implementation-scope file is authorized by this gate.
- **Items deferred:** this session did not modify
  `docs/05-qa/architecture-review-log.md` — despite an observed repo
  convention of adding a "Proposed for ChatGPT review" row for each proposed
  DEC, this session judged the risk of mis-numbering/mis-formatting a row in
  that 1,600+-line log too high for a docs-synthesis session to take on
  unprompted; flagged explicitly in DEC-025's own "Architecture-review-log
  note" and in this session's final report, per the task's "if uncertain, do
  not modify it" instruction.
- **Learning feedback loop:** new issues discovered: none (synthesis-only
  session; no code, no defects possible). Repeated issue patterns: none.
  Rules/checklists updated: none (a new checklist file was created, not an
  existing rule modified). New rejected approaches: none — checked
  `rejected-approaches-log.md` before drafting; no approach proposed here
  meets or conflicts with any existing RA row. New technical debt: none.
  Architecture concerns: none beyond what Task 006A already flagged as open
  (carried forward in DEC-025 §Open questions and §Risks, not newly
  introduced). Should future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **DEC-025 status:** **Proposed / Pending ChatGPT review** — not Accepted.
  No decision in this session's output is marked Accepted; no implementation
  is authorized; no Task 006C or implementation-scope file was created.
- **Preserved blockers (confirmed unchanged by this session):** VAL-B2
  deferred/not passed; MBQ-05 Partially routed/Open; TD-002 Open; fulfillment
  API model unresolved; product first-sync dedup thresholds still domain
  design; Lite/Full packaging not finalized; the 16-vs-17 `@idempotent`
  mutation-count discrepancy and the OCA `queue_job` `--workers > 0` vs.
  `> 1` wording discrepancy both still open/non-blocking; multi-server/
  Odoo.sh runtime concurrency proof still required before any future
  implementation relies on a concurrency assumption named in this gate.
- **Next step:** ChatGPT review of this architecture gate and DEC-025 (see
  `docs/05-qa/task-006b-architecture-gate-review-checklist.md`). If
  accepted, the recommended next session is a separately-scoped, separately-
  authorized Task 006C implementation-scope drafting session — not started
  here.
- **Stop condition:** docs-only session, no code touched, no implementation
  authorized, no Task 006C/implementation-scope file created, DEC-025 left
  as Proposed/Pending, not Accepted. Stopped after opening a draft PR
  against `Shopify-connector`. Awaiting ChatGPT review.

---

### Task 006A completeness audit — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006a-completeness-audit-ptq56q` → target
  `Shopify-connector`, **draft**, opened this session.
- **Files changed:** `docs/05-qa/task-006a-completeness-audit.md` (new),
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** audit-only session verifying Task 006A
  research completeness after PR #123, #124, #125 (revision 2), and #126 all
  merged into `Shopify-connector` (all four merge/head commits confirmed
  ancestors of current HEAD `b39096e`). Confirmed
  `docs/01-research/sync-engine-shopify-source-notes.md` was never created;
  found its intended content is covered-by-synthesis across PR #125's
  `sync-engine-source-inventory.md` §4 (S1–S16, all official `shopify.dev`,
  Primary-graded) plus PR #126's cross-referenced `SH-` sources — all 9
  required protocol/mechanics topics (GraphQL overview, cost/rate limits,
  cursor pagination, bulk operations, webhooks, HMAC/dedup, idempotency,
  REST 429+Retry-After, GraphQL 200+THROTTLED) have at least one official
  citation; the 10th (domain API surfaces) is intentionally scoped light,
  deferred to Tasks 010–014. Confirmed PR #125's five synthesis outputs
  exist and are internally consistent (26-claim evidence map, fully cited;
  43 open questions; 9 risk-register rows). Confirmed VAL-B2
  (deferred/not passed), MBQ-05 (partially routed/open), TD-002 (Open),
  fulfillment scope/API model, product first-sync dedup, and
  many-unrelated-customers token acquisition all remain open, each with a
  direct citation. Confirmed no architecture decision, no `DEC-025`, no
  implementation-scope file, and no sync-engine/domain code exists anywhere
  in the repo.
- **Items deferred:** the 16-vs-17 `@idempotent` mutation-count discrepancy
  and the OCA `queue_job` `--workers > 0` vs. `> 1` discrepancy (both
  pre-existing, immaterial, carried forward as tracked open items, not
  re-researched by this audit).
- **Learning feedback loop:** new issues discovered: none (audit-only, no
  defects found). Repeated issue patterns: none. Rules/checklists updated:
  none. New rejected approaches: none. New technical debt: none. Architecture
  concerns: the "engine-requirement level only" domain-API-surface scoping
  boundary is followed in practice but not written down explicitly anywhere
  — flagged as a documentation-clarity recommendation for a future session,
  not a defect. Should future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Recommendation (this audit, not a decision):** **Proceed to Task 006B**
  without a separate Shopify-shard backfill session — the missing standalone
  file is an organizational/naming gap, not a research/coverage gap. See
  `docs/05-qa/task-006a-completeness-audit.md` §9 for the full reasoning and
  the conditions under which ChatGPT might instead select the backfill
  alternative (Recommendation B).
- **Next step:** ChatGPT review of this audit and its recommendation.
- **Stop condition:** audit-only session, docs-only, no code touched, no
  architecture decision made, no DEC-025 created, no implementation-scope
  file created, no implementation authorized. Stopped after opening a draft
  PR against `Shopify-connector`. Awaiting ChatGPT review.

---

### Task 006A — PR #125 revision 2 — incorporated merged PR #126 queue/idempotency/retry/backoff/dead-letter research — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006a-sync-engine-research-zj7pmv` → PR #125
  into `Shopify-connector` (**draft**, unmerged; same PR, revised in place —
  no new PR opened; this is the second revision, following revision 1
  below). **Full base progression:** PR #125's initial branch was created
  **before PR #124 and PR #126 were merged**, from the PR #122-era base
  (`9247fea3c36afdb761a82678f3e5e66e8ef42e87`). **Revision 1** (below)
  incorporated PR #124 (`3735ae2292d1fcf926c83034ac8513906c9f5020`). **This
  revision** incorporates PR #126 — "Task 006A-3 queue/idempotency/retry/
  backoff/dead-letter source notes" — after merging latest
  `origin/Shopify-connector`, confirmed to include the PR #126 merge commit
  `3c9fad896f996c19d4978e5aca58b39674b7b35a` (clean merge, no conflicts).
  **PR #123, PR #124, and PR #126 are all now merged sibling Task 006A
  shards.**
- **What changed / residue fixed:** control-room review found PR #125 was
  not ready to merge because it predated PR #126 and therefore did not
  incorporate the now-accepted
  `docs/01-research/sync-engine-queue-idempotency-source-notes.md` (PR #126
  — the canonical queue/idempotency/retry/backoff/dead-letter reference
  shard for this task family: a 52-source, 9-topic, adversarially-verified
  treatment). This revision:
  - Establishes and documents the full **synthesis hierarchy** across all
    four Task 006A shards: `R31`/PR #124 canonical for Odoo/repo substrate;
    `R33`/PR #126 canonical for queue/idempotency/retry/backoff/dead-letter
    reference patterns; `R32`/PR #123 canonical for competitor/common sync
    patterns; PR #125 (this package) as the cross-cutting synthesis and
    evidence-map, not a fifth independent research pass replacing any of
    the three.
  - Cross-references PR #126's document throughout the source inventory,
    source notes, evidence map, open questions, and risk register, rather
    than duplicating its content.
  - Incorporates several genuinely new findings PR #126 surfaced that this
    package had not independently researched: a throttled Shopify
    **GraphQL** call can return **HTTP 200** with a `THROTTLED` body code
    rather than a 4xx status; dead-letter-queue visibility is everywhere an
    **opt-in alarm/metric**, not a default push notification, and can
    trigger on a single failed attempt; PostgreSQL advisory locks carry
    documented hazards (a `LIMIT`-ordering danger, session-vs-transaction
    scope) not previously researched; a specific, corrected AWS jitter
    formula; and a more specific open question about multi-server/
    load-balanced `ir.cron` coordination.
  - Strengthens three existing findings from single-shard to
    multi-shard-corroborated: the "requires live Odoo.sh runtime proof"
    conclusion for `ir.cron` locking/duplicate-execution (now confirmed
    independently by three shards — this package, `R31`, and `R33`); the
    bulk-operations non-resumability finding; and the GraphQL-cursor-
    durability open question (with a new, related REST-specific fact:
    `page_info` cursor URLs are explicitly documented as temporary).
  - Notes one new, unreconciled, immaterial discrepancy: this package's
    pre-006A baseline cites OCA `queue_job`'s Jobrunner precondition as
    `--workers > 0`; PR #126 cites `--workers > 1`. Not resolved; does not
    affect RA-004 (`queue_job` remains reference-only either way).
  - All prior corrections from revision 1 are preserved unchanged: existing
    Tasks 001–005 substrate provides *primitives*, not the full sync engine;
    the savepoint warning is a performance constraint, not a hard cap; the
    cron-retry conclusion remains a labeled source-backed inference; the
    dead-letter wording remains scoped to sources inspected.
- **No architecture decision. No implementation.** No addon file, Python,
  XML, CSV, manifest, security, migration, CI, controller, view, wizard,
  OAuth, or domain-sync code was created or modified in this revision. No
  architecture-decision file, no DEC-025, no implementation-scope file was
  created. VAL-B2 remains deferred/not passed; MBQ-05 remains partially
  routed/open; TD-002 remains Open — all unmodified by this revision.
- **Next step:** ChatGPT re-review of this revised Task 006A research
  package.
- **Stop condition:** docs-only revision, stopped after pushing to the same
  PR #125 branch. No code touched. No merge performed. PR remains draft/
  unmerged.

---

### Task 006A — PR #125 revision — incorporated merged PR #124 Odoo/repo substrate research — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006a-sync-engine-research-zj7pmv` → PR #125
  into `Shopify-connector` (**draft**, unmerged; same PR, revised in place —
  no new PR opened). **PR #125's initial branch was created from the PR
  #122-era base** (`9247fea3c36afdb761a82678f3e5e66e8ef42e87`). **PR #123 and
  PR #124 are now merged** (`aeaf7eb7782178b260edd452c9075a8dd1df323a` and
  `3735ae2292d1fcf926c83034ac8513906c9f5020` respectively); this revision
  merges latest `origin/Shopify-connector` (confirmed to include the PR #124
  merge commit) into the PR #125 branch, a clean merge with no conflicts.
- **What changed / residue fixed:** control-room review found PR #125 was
  not ready to merge because it predated PR #124 and therefore did not
  incorporate the now-accepted `docs/01-research/sync-engine-odoo-repo-source-notes.md`
  (PR #124, "Task 006A-2 sync engine Odoo/repo substrate research" — the
  canonical Odoo/repo substrate shard for this task family). This revision:
  - Cross-references PR #124's document throughout the source inventory,
    source notes, and evidence map as an accepted/merged source, rather than
    duplicating its content. Where this PR's own independent Odoo research
    reached the same facts (e.g. the `retrying()` mechanism, the >64-savepoint
    coding-guideline warning, `lock_for_update()`/`try_lock_for_update()`),
    that overlap is now marked as corroboration between two independently
    produced shards, not restated as if newly discovered by this PR alone.
  - Softens four overclaim/underclaimed-uncertainty wordings the control-room
    review flagged: (1) "Tasks 001–005 already satisfies most mandatory
    claims" → clarified that only specific *primitives* are implemented, not
    the full sync-engine requirement set; (2) "Odoo caps savepoints at ~64" →
    reworded as a performance-constraint warning, not a hard functional cap
    (also now corroborated by PR #124's independent finding that core
    `create()`/`write()` do not wrap themselves in a savepoint by default —
    savepoints are used selectively); (3) the cron-retry-does-not-extend
    conclusion → relabeled explicitly as a source-backed **inference**
    requiring runtime proof, not a directly-quoted single-source conclusion;
    (4) "Odoo `ir.cron` has no dead-letter concept at all" → scoped to "no
    such mechanism was found in the sources inspected," not an absolute
    whole-codebase claim.
  - Updates the stale "based on latest Shopify-connector at PR #122" wording
    in the original entry below to accurately describe the PR #122 → PR #124
    base progression.
- **No architecture decision. No implementation.** No addon file, Python,
  XML, CSV, manifest, security, migration, CI, controller, view, wizard,
  OAuth, or domain-sync code was created or modified in this revision. No
  architecture-decision file, no DEC-025, no implementation-scope file was
  created. VAL-B2 remains deferred/not passed; MBQ-05 remains partially
  routed/open; TD-002 remains Open — all unmodified by this revision.
- **Next step:** ChatGPT re-review of this revised Task 006A research
  package.
- **Stop condition:** docs-only revision, stopped after pushing to the same
  PR #125 branch. No code touched. No merge performed. PR remains draft/
  unmerged.

---

### Task 006A — sync engine source research and evidence map — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-006a-sync-engine-research-zj7pmv` → target
  `Shopify-connector`, **draft**, opened this session. **Correction (see the
  revision entry above this one):** this PR's initial branch was created
  from PR #122; that is a historical starting point, not this PR's current
  base — the branch was subsequently updated against latest
  `Shopify-connector` after PR #123 and PR #124 merged.
- **Files created (all docs-only, per the allowed-files list):**
  - `docs/01-research/sync-engine-source-inventory.md` — 60-source reliability-graded inventory.
  - `docs/01-research/sync-engine-source-notes.md` — detailed source-backed notes across all required sections.
  - `docs/01-research/sync-engine-evidence-map.md` — the 18 mandatory claims plus 6 supplementary findings, each mapped to graded evidence.
  - `docs/05-qa/sync-engine-open-questions.md` — 39 open questions, categorized per the required section structure.
  - `docs/05-qa/sync-engine-risk-register.md` — 7 evidence-backed risks (created; judged warranted given the volume of concurrency/performance findings).
  - `docs/01-research/research-handoff.md` — this entry.
- **Source categories researched:** repo code (job/log/store/credential/
  readiness models, tests), repo governance/decision docs (DEC-005, DEC-009,
  AR-003/AR-006 acceptance status, core-naming-schema-planning §8/§9,
  master-blueprint-core-substrate §A.5/§I/§K.2, MBQ register, rejected-
  approaches log), existing repo research syntheses (Shopify/Odoo official-
  source notes), fresh official Shopify docs (cursor pagination/connections,
  bulk operations incl. cancellation/error-handling, webhooks, idempotency —
  re-verified 2026-07-08), fresh official Odoo 19.0 docs/source (transactions/
  rollback/savepoints, concurrency/locking, `ir.cron` failure model — a
  genuine prior gap), OCA `queue_job` (first full source read this project
  has done — reference pattern only, RA-004 unchanged), and reputable
  engineering references (Stripe idempotency, AWS Builders' Library,
  Google SRE book, AWS SQS DLQ docs, OWASP Logging Cheat Sheet).
- **Key high-confidence findings (corrected wording, see the revision entry
  above this one):**
  - The existing Tasks 001–005 substrate already provides implemented
    primitives for several mandatory sync-engine claims — idempotency keys,
    the operation-scope serialization guard, append-only redacted logs, and
    store-state gating — but this does not mean the full sync engine
    requirements are complete. Actual sync operation execution, retry
    scheduling, checkpoint/resume, domain deduplication, and handler
    dispatch remain unbuilt (independently corroborated by PR #124's
    "Current gaps" section: no sync operation abstraction, no retry
    scheduling engine, no domain-neutral handler registry for operations, no
    checkpoint/resume model, no first-sync dedup implementation).
  - Odoo's coding guidelines warn that PostgreSQL performance degrades when a
    transaction uses more than 64 savepoints, so future per-record-savepoint
    loops must treat this as a performance constraint, not a hard functional
    cap — independently corroborated by PR #124's Odoo/repo substrate
    research (same source, same quote), which additionally notes core
    `create()`/`write()` do not wrap themselves in a savepoint by default;
    savepoints are used selectively by higher-level code.
  - Source-level review indicates this as a synthesis/inference, not a
    directly-quoted single-source conclusion: Odoo's RPC-layer `retrying()`
    behavior is source-confirmed for RPC/HTTP dispatch, while the reviewed
    `ir.cron` job-processing path did not show an equivalent automatic retry
    around each domain record-processing step. This remains a source-backed
    inference requiring runtime proof before implementation relies on it.
    PR #124 independently confirms the `retrying()` RPC/HTTP mechanism and
    separately documents `ir.cron`'s own job-*acquisition* locking
    (`_acquire_one_job`, `FOR NO KEY UPDATE SKIP LOCKED`) — a related but
    distinct finding (job acquisition, not domain-record-processing retry)
    that does not itself settle this inference either way.
  - The Shopify 25,000-object pagination cap is **Liquid/Storefront-only**,
    not Admin GraphQL — corrects an ambiguity the pre-006A baseline had left
    open.
  - No documented or reviewed Odoo `ir.cron` dead-letter/redrive mechanism
    was found in the sources inspected (by this session or independently by
    PR #124); the connector must not rely on `ir.cron` for permanent-failure
    visibility — this repo's own job state machine is the actual
    operator-visible failure surface.
- **Key low-confidence/uncertain areas:**
  - **Discrepancy, not resolved:** existing DEC-009/AR-006 research cites
    "17" `@idempotent` mutations; this session's fresh fetch counts 16 named
    mutations on Shopify's own (self-dated) list. Flagged for
    re-verification, does not block core-engine research.
  - Whether the Task-005 disconnect-cancellation sweep fully closes the race
    against a job already `running` at the instant of disconnect —
    unproven by any source, requires live Odoo.sh proof.
  - Cursor-pagination resumability across a paused sync of unspecified
    length is undocumented by Shopify.
  - "Lite/Full" packaging has **no existing concept** in this repo beyond
    the already-accepted per-domain-enablement-flag mechanism — flagged as
    a genuine gap between the task's framing and current repo state.
- **No implementation performed.** No addon file, Python, XML, CSV,
  manifest, security, migration, CI, controller, view, wizard, OAuth, or
  domain-sync code was created or modified. No architecture-decision file
  (`docs/03-architecture/sync-engine-architecture-gate.md`) or
  implementation-scope file was created. No DEC-025 was created. VAL-B2
  remains deferred/not passed; MBQ-05 remains partially routed/open; TD-002
  remains Open — all unmodified by this session.
- **Learning feedback loop:**
  - New issues discovered: the 16-vs-17 `@idempotent` mutation-count
    discrepancy (see open-questions #4); the Liquid/Storefront-only scope
    of the 25,000-object pagination cap (a correction, not a defect).
  - Repeated issue patterns: none — this was a research-only session, no
    code to regress.
  - Rules/checklists updated: none (outside this session's allowed-files
    scope).
  - New rejected approaches: none — RA-004 (OCA `queue_job` not the Phase 1
    default) checked and confirmed unchanged by this session's full source
    read of `queue_job` (kept as reference pattern only).
  - New technical debt: none logged by this session (research-only; any
    future debt is for the implementation task that eventually acts on this
    research).
  - Architecture concerns: whether the future job-drain concurrent-
    acquisition mechanism should reuse Odoo's `lock_for_update()`/`SKIP
    LOCKED` pattern (open, routed to a future architecture gate, not this
    session).
  - Should future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured · no new rejected approach · no new
  technical debt · no repeated-issue escalation needed.
- **Next step:** ChatGPT review of this Task 006A research package. If
  accepted, a separate Task 006B architecture-gate session (not this one)
  would be the next place any sync-engine design decision could be proposed
  — this session proposes none.
- **Stop condition:** docs-only research session, stopped after opening a
  draft PR against `Shopify-connector`. No code touched. No merge performed.
  Awaiting ChatGPT review.

---

### Task 005 closure — connection lifecycle merged (PR #121) — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-closure-docs-s5d9mf` (docs-only closure) →
  target `Shopify-connector`, **draft**. Closes out PR #121, which is
  **merged** into `Shopify-connector`, merge commit
  `8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82` (PR #121 head commit before
  merge: `f2ce29c0422258f92877f6464b1746455d28dcb5`, confirmed against this
  repository's own git history).
- **Files changed:** this file (new top entry, this session only);
  `../05-qa/task-005-validation-results.md` (new);
  `../04-decisions/DEC-024-task-005-closure.md` (new). No code, manifest,
  XML, CSV, security, migration, CI, controller, view, or wizard file
  touched by this closure session.
- **What changed / residue fixed:** Task 005 ("Connection lifecycle
  actions", scoped by DEC-022) is now merged and closed out at
  documentation/control-room level. Delivered: `action_activate()`,
  `action_disconnect()`, `action_reconnect()`,
  `action_mark_reconnect_needed()`; business-job enqueue-time gating and
  execution-time gating on store connection state; credential-service
  state invalidation on token set/replace/clear (`action_set_token()` /
  `action_replace_token()` move a `connected` store to
  `reconnect_needed`; `action_clear_token()` moves a `connected` or
  `reconnect_needed` store to `disconnected`); lifecycle and
  credential-service tests (`test_connection_lifecycle.py`,
  `test_credential_service.py`). Live Odoo.sh runtime validation (real
  Odoo 19 + PostgreSQL registry, not static/`py_compile`-only) passed
  both the focused `TestConnectionLifecycle` class (**0 failed, 0
  error(s) of 41 tests**) and the full `shopify_connector_core` module
  suite (**0 failed, 0 error(s) of 123 tests**) at the merged head commit
  — see
  [`task-005-validation-results.md`](../05-qa/task-005-validation-results.md)
  for the full evidence record, including the two rounds of runtime
  failures found and fixed before merge.
- **Runtime lessons learned** (carried forward from the pre-merge PR #121
  revision entries below, restated here as the closure-level summary):
  - **Static review missed a real Odoo ORM timestamp-behavior defect.**
    The `credential.write_date > credential_last_verified_at` freshness
    guard passed `py_compile` and every static/adversarial review across
    three PR revisions, but failed live on Odoo.sh (5 activation test
    failures) because it depended on actual Postgres `write_date`
    write-timing behavior that no static check exercises.
  - **The `credential.write_date` freshness guard was brittle and was
    removed** — replaced by clearing `credential_last_verified_at`
    directly at its real source (`action_set_token()` /
    `action_replace_token()`), which does not depend on ORM timestamp-
    column write timing.
  - **Credential mutation must invalidate both the verification evidence
    and the derived `store.state`.** A second, separate runtime failure
    (1 test) showed that clearing `credential_last_verified_at` alone was
    not enough: `action_replace_token()` left a `connected` store's
    `state` unchanged, which would have let business-job gating (keyed on
    `state == 'connected'`) treat an unverified changed credential as
    still connected. Fixed by adding lifecycle state invalidation inside
    the credential service itself.
- **Current open items (unchanged by this closure):**
  - **VAL-B2 remains deferred / not passed** — no live Shopify Admin API
    connection evidence exists; this closure supplies none
    (`DEC-021-val-b2-deferral-for-task-004.md`).
  - **MBQ-05 remains partially routed / open** — the scalable
    many-unrelated-customer distribution/auth architecture is still
    undecided (`../03-architecture/master-blueprint-open-questions.md`
    MBQ-05 row; `DEC-023-token-acquisition-and-val-b2.md`).
  - **TD-002 remains Open** — the `read_fulfillments` readiness-scope
    correctness concern, routed to the fulfillment domain's own task spec
    once the fulfillment API model is decided
    (`../05-qa/technical-debt-register.md` TD-002 row).
- **No scope expansion.** This session is docs-only: no OAuth, no setup
  wizard, no UI, no product/customer/order/inventory/fulfillment sync, no
  security/ACL change. See
  [`DEC-024-task-005-closure.md`](../04-decisions/DEC-024-task-005-closure.md)
  for the full accepted-outcome/non-decision record.
- **Learning feedback loop:**
  - New issues discovered: none in this closure session (docs-only; the
    two runtime defects were found and fixed in the pre-merge PR #121
    revisions, already logged below).
  - Repeated issue patterns: none new.
  - Rules/checklists updated: none in this session's allowed-files scope.
  - New rejected approaches: none new (the `write_date`-as-freshness-guard
    rejection was already logged in the pre-merge revision entry below).
  - New technical debt: none new.
  - Architecture concerns: none new.
  - Tests or review gates needed: none new — see "Current open items"
    above for the pre-existing, still-open items.
  - Should future prompts change? No.
- **Quality gate confirmation:** handoff updated (this block) · feedback
  loop checked · learning captured (restated from PR #121's own revision
  entries; no new learning this session) · no new rejected approach · no
  new technical debt · no repeated-issue escalation needed.
- **Next recommended session:** control room (ChatGPT) reviews this
  closure package and decides the next gated task — candidates listed in
  [`DEC-024-task-005-closure.md`](../04-decisions/DEC-024-task-005-closure.md)
  §"Next task candidates" (not selected by this session).
- **Stop condition:** docs-only closure session, stopped after opening a
  draft PR against `Shopify-connector`. No code touched. No merge
  performed. Awaiting ChatGPT review.

---

### Task 005 PR #121 revision — Odoo.sh runtime failure fix (lifecycle state invalidation gap) — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-lifecycle-actions-k3ixq5` → PR #121 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store_credential.py`,
  `addons/shopify_connector_core/tests/test_connection_lifecycle.py`,
  `addons/shopify_connector_core/tests/test_credential_service.py`,
  `docs/01-research/research-handoff.md` (this entry). No other file
  touched.
- **What changed:** Odoo.sh runtime re-validation after Revision 4 found
  **1 remaining failure**:
  `TestConnectionLifecycle.test_activate_rejects_stale_evidence_after_credential_replace`
  (`AssertionError: 'connected' == 'connected'`). **Root cause:**
  `action_replace_token()` cleared `credential_last_verified_at` (correctly
  invalidating the verification evidence) but left `store.state` as
  `'connected'` — a real product risk, since Task 005 business-job gating
  keys off `store.state == 'connected'`, so a connected store left
  connected after its credential changed could let sync jobs run against
  an unverified changed credential. **Fixed** by adding lifecycle state
  invalidation inside the credential service itself (no jobs/logs
  created, no `sudo()`, no `access_token` read):
  - `action_set_token()` / `action_replace_token()`: a `'connected'` store
    also moves to `'reconnect_needed'`.
  - `action_clear_token()`: a `'connected'` or `'reconnect_needed'` store
    also moves to `'disconnected'`. `action_disconnect()`'s own follow-up
    `state='disconnected'` write remains a fine, idempotent no-op on top
    of this.
  Tests updated: `test_activate_rejects_stale_evidence_after_credential_replace`
  and `test_activate_rejects_stale_evidence_after_action_set_token_update`
  now assert `store.state == 'reconnect_needed'` after the credential
  mutation (the latter no longer manually moves state before calling
  `action_set_token()` — the service does it); a new
  `test_credential_service_clear_token_sets_state_disconnected_directly`
  test calls `action_clear_token()` directly (not via
  `action_disconnect()`) and asserts `state == 'disconnected'` with no
  job/log rows created. `test_credential_service.py` gained four focused
  tests covering the same three transitions plus the no-job/no-log
  guarantee under a `'connected'`/`'reconnect_needed'` starting state
  (the existing `test_no_job_or_job_log_rows_written` was left unchanged,
  not weakened). **No scope expansion** — no OAuth/setup wizard/UI/
  sync/domain implementation, no security/ACL change, no new job state/
  type/source, no new `sudo()`, no new schema field, no `access_token`
  read/log. Revision 4's `action_activate()` requirements and the
  Revision 1 `action_reconnect()` missing-credential fix remain
  untouched and confirmed intact.
- **Local validation performed:** `python -m py_compile` on all three
  changed Python files — passes. **No Odoo runtime is available in this
  session's container**, so the updated test suite was not re-executed
  here — stated honestly; Odoo.sh validation is requested again via the
  same command:
  `odoo-bin -d <db> -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --log-level=test`
  (focused: `--test-tags /shopify_connector_core:TestConnectionLifecycle`).
- **VAL-B2 remains deferred / not passed. MBQ-05 remains partially routed /
  open. TD-002 remains open.** Unchanged by this revision.

---

### Task 005 PR #121 revision — Odoo.sh runtime failure fix (brittle write_date guard) — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-lifecycle-actions-k3ixq5` → PR #121 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/models/shopify_connector_store_credential.py`,
  `addons/shopify_connector_core/tests/test_connection_lifecycle.py`,
  `docs/01-research/research-handoff.md` (this entry). No other file
  touched.
- **What changed:** Odoo.sh runtime validation (the first actual
  in-Odoo test run of this PR) **failed 5 tests**, all for the same
  reason: `action_activate()`'s `credential.write_date >
  credential_last_verified_at` freshness guard (added in the prior
  revision) raised "Cannot activate: the stored credential changed
  after the last verification" even on legitimately fresh evidence --
  `test_activate_succeeds_with_pass_and_pass`,
  `_succeeds_with_pass_and_warning`, and all three
  `_rejects_stale_evidence_after_*` tests. **Root cause**: comparing a
  credential row's own `write_date` against a manually/test-seeded
  `credential_last_verified_at` is brittle against real DB write timing
  under Odoo.sh -- a purely static/unit-test-level guard that never ran
  in an actual Odoo runtime until now. **Fixed** by removing the
  `write_date` comparison entirely and instead closing the same
  stale-evidence path at its real source: `action_set_token()` (in
  `shopify_connector_store_credential.py`) now clears
  `credential_last_verified_at` on every token set/update -- including
  updating an *existing* credential row -- exactly mirroring
  `action_replace_token()`'s existing behavior, so a token silently
  overwritten via `action_set_token()` can no longer activate on
  pass/pass evidence recorded for the value it replaced. `action_
  activate()` also gained a readiness-freshness requirement:
  `last_readiness_at` must be truthy and not older than
  `credential_last_verified_at` -- otherwise a readiness pass recorded
  *before* the current credential was verified could incorrectly count
  as evidence for it. Full accepted check order: `credential_present` →
  credential row exists → `credential_last_verified_at` truthy →
  `last_test_connection_result == 'pass'` → `last_readiness_result in
  ('pass', 'warning')` → `last_readiness_at` truthy and `>=
  credential_last_verified_at`. Raises `UserError` before any write on
  any failure; no audit job on rejection; no Shopify call; no readiness
  run. Tests updated: all successful-activation setups now seed
  `last_readiness_at` (via a new `_seed_verified_evidence()` helper that
  stamps both `credential_last_verified_at`/`last_readiness_at` from the
  same timestamp, deterministically satisfying `>=`); the
  `action_set_token`-stale-evidence test was rewritten to prove
  `credential_last_verified_at` clears (not `write_date` comparison);
  two new tests added --
  `test_activate_rejects_stale_readiness_evidence_before_verification`
  (10-minute deterministic gap) and
  `test_activate_rejects_missing_readiness_at`. The prior
  `action_reconnect()` missing-credential transaction-safety fix
  (Revision 1) remains untouched and confirmed intact. **No scope
  expansion** -- no OAuth/setup wizard/UI/sync/domain implementation, no
  security/ACL change, no new job state/type/source, no new `sudo()`, no
  new schema field, no `access_token` read/log.
- **Local validation performed:** `python -m py_compile` on all three
  changed Python files -- passes. **No Odoo runtime is available in this
  session's container**, so the updated test suite was not re-executed
  here -- stated honestly; Odoo.sh validation is requested again via the
  same command:
  `odoo-bin -d <db> -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --log-level=test`
  (focused: `--test-tags /shopify_connector_core:TestConnectionLifecycle`).
- **VAL-B2 remains deferred / not passed. MBQ-05 remains partially routed /
  open. TD-002 remains open.** Unchanged by this revision.
- **Learning feedback loop:**
  - New issues discovered: the `credential.write_date` freshness guard
    was a genuine runtime defect (not merely a style nit) -- it passed
    every static review and `py_compile` check across three prior
    revisions, and only Odoo.sh's actual test execution exposed it. This
    is the first defect in this PR's history that a static-only review
    process (including the earlier adversarial-review workflow) could
    not have caught, since it depended on real Postgres `write_date`
    timestamp-column write timing, not reproducible via source
    inspection alone.
  - Repeated issue patterns: the credential-service stale-evidence
    pattern (flagged across Revisions 2–3) is now closed at its actual
    source (`action_set_token`/`action_replace_token` both clear
    `credential_last_verified_at`) rather than via a derived-timestamp
    comparison -- a more robust fix than the one it replaces.
  - Rules/checklists updated: none (out of this revision's allowed-files
    scope) -- flagged for a future docs-scoped session: **any freshness
    guard comparing ORM-managed timestamp fields (`write_date`,
    `create_date`) against manually-stamped fields should be treated as
    requiring actual Odoo-runtime validation before being trusted, not
    just `py_compile`/static review** -- this is the concrete lesson
    from this failure.
  - New rejected approaches: comparing `credential.write_date` to
    `credential_last_verified_at` as an activation freshness gate is now
    a rejected mechanism for this codebase (superseded by clearing
    `credential_last_verified_at` at the credential-service source plus
    the new `last_readiness_at` freshness check) -- not logged to
    `rejected-approaches-log.md` since that file is out of this
    revision's allowed-files scope; flagged here for a future
    docs-scoped session to formalize if warranted.
  - New technical debt: none.
  - Tests or review gates needed: **runtime validation (Odoo.sh or a
    local Odoo instance) should run at least once before any future
    "static review accepted" milestone is treated as sufficient for
    merge** -- this failure is the concrete evidence for that gate,
    consistent with the "prepare for runtime validation" session that
    immediately preceded this one.
  - Should future prompts change? Yes, for future timestamp-comparison
    guards specifically: prefer clearing/invalidating a dependent field
    at its mutation source over deriving freshness from a second,
    independently-managed timestamp field, per the lesson above.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (noted above, not yet
  formalized in the log file -- out of scope) · technical debt logged
  (n/a) · repeated-issue escalation applied (noted above) — all YES.
- **Next step:** re-run Odoo.sh runtime validation against this revised
  commit; report the result back for ChatGPT re-review.
- **Stop condition:** stopped at the scoped boundary — exactly the three
  allowed files touched; no merge; PR remains draft, not marked ready for
  review.

### Task 005 PR #121 revision — stale activation evidence after action_set_token() update — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-lifecycle-actions-k3ixq5` → PR #121 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/tests/test_connection_lifecycle.py`,
  `docs/01-research/research-handoff.md` (this entry). No other file
  touched — the credential model (`shopify_connector_store_credential.py`)
  was explicitly not edited, per this session's instructions.
- **What changed:** ChatGPT's re-review of PR #121 found a remaining
  stale-evidence path in `action_activate()`, distinct from the one
  fixed in the prior revision: `action_set_token()` can update an
  *existing* credential row (re-entering/correcting a token) without
  clearing `credential_last_verified_at` at all — unlike
  `action_replace_token()`, which does clear it. So the truthy-only
  `credential_last_verified_at` check added in the previous revision was
  not enough: a token silently overwritten via `action_set_token()`
  could still activate on pass/pass evidence recorded for the credential
  value it replaced. **Fixed** by adding a credential-row-freshness
  check to `action_activate()`, in order: `credential_present` →
  credential row exists (searched via the normal ORM, no `sudo()`, no
  `access_token` read) → `credential_last_verified_at` truthy →
  credential row's `write_date` not newer than
  `credential_last_verified_at` → `last_test_connection_result == 'pass'`
  → `last_readiness_result in ('pass', 'warning')`. Raises `UserError`
  before any write on any failure; leaves state unchanged; creates no
  audit job on rejection; no Shopify call; no readiness run; no
  credential mutation. Added
  `test_activate_rejects_stale_evidence_after_action_set_token_update`
  (activates once with fresh verified evidence, moves state away from
  `connected`, deterministically backdates `credential_last_verified_at`
  by 10 minutes to avoid same-second flakiness, overwrites the
  credential via `action_set_token()`, confirms the mirrors stay
  stale/`credential.write_date` is newer than `credential_last_verified_at`,
  confirms the second `action_activate()` raises and does not connect,
  confirms no new audit job). All existing activate tests already seed
  `credential_last_verified_at` via `fields.Datetime.now()` called
  strictly after the credential's creation in the same test method, so
  each already satisfies the new freshness check without modification
  (verified by inspection, not assumed). The prior
  `action_reconnect()`/`action_activate()` fixes (Revisions 1–2) are
  untouched and confirmed intact. **No scope expansion** — no OAuth/
  setup wizard/UI/sync/domain implementation, no security/ACL change, no
  new job state/type/source, no new `sudo()`, no credential-model edit.
- **Local validation performed:** `python -m py_compile` on both changed
  Python files — passes. **No Odoo runtime is available in this session's
  container**, so the test suite was not executed here — stated honestly;
  the same Odoo.sh/manual validation command from the original PR #121
  handoff entry still applies:
  `odoo-bin -d <db> -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --log-level=test`.
- **VAL-B2 remains deferred / not passed. MBQ-05 remains partially routed /
  open. TD-002 remains open.** Unchanged by this revision.
- **Learning feedback loop:**
  - New issues discovered: the `action_set_token()`-update stale-
    evidence path above, found by ChatGPT's re-review — a third instance
    of the same defect class as the two prior stale-evidence fixes
    (credential-service writes that leave a pass/pass evidence mirror
    behind without clearing whatever presence/verification signal
    `action_activate()` relies on).
  - Repeated issue patterns: **yes, now a confirmed third occurrence** —
    (1) `action_disconnect` clears `credential_present` but not the
    evidence mirrors; (2) `action_replace_token` clears
    `credential_last_verified_at` but not the evidence mirrors; (3)
    `action_set_token` clears *neither* `credential_last_verified_at`
    nor the evidence mirrors when updating an existing row. The standing
    rule flagged in the prior handoff entry ("any credential-service
    write that clears a presence/verification field must be checked
    against every consumer of the evidence mirrors it does not clear")
    should be broadened: also check credential-service writes that clear
    *nothing new* but still change the underlying credential identity
    (e.g. `write_date` freshness, not just an explicit cleared field).
  - Rules/checklists updated: none (out of this revision's allowed-files
    scope) — flagged above for a future docs-authorized session.
  - New rejected approaches: none.
  - New technical debt: none.
  - Tests or review gates needed: none beyond the regression test added.
  - Should future prompts change? Worth a dedicated, docs-scoped session
    to audit the full credential-service surface
    (`action_set_token`/`action_replace_token`/`action_clear_token`)
    against every consumer of `credential_present`/
    `credential_last_verified_at`/the test-connection/readiness evidence
    mirrors, now that three related-but-distinct instances have surfaced
    across three review rounds — not actioned here, out of scope.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a) · technical debt
  logged (n/a) · repeated-issue escalation applied (noted above as a
  now-third-occurrence pattern; no rule file updated, out of scope) —
  all YES.
- **Next step:** ChatGPT re-review of the revised PR #121.
- **Stop condition:** stopped at the scoped boundary — exactly the three
  allowed files touched; credential model untouched; no merge; PR
  remains draft, not marked ready for review.

### Task 005 PR #121 revision — stale activation evidence after credential replace — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-lifecycle-actions-k3ixq5` → PR #121 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/tests/test_connection_lifecycle.py`,
  `docs/01-research/research-handoff.md` (this entry). No other file
  touched.
- **What changed:** ChatGPT's re-review of PR #121 found that
  `action_activate()`'s existing checks (`credential_present` +
  `last_test_connection_result == 'pass'` + `last_readiness_result in
  ('pass', 'warning')`) were not enough after a credential replacement:
  `shopify.connector.store.credential.action_replace_token()` clears
  `credential_last_verified_at` on every token swap but does not reset
  `last_test_connection_result`/`last_readiness_result`, so a replaced
  token could activate on pass/pass evidence recorded for the *previous*
  token — violating the Task 005 "never infer connection success" rule.
  **Fixed** by adding a `credential_last_verified_at` truthy check to
  `action_activate()`, in the required order: `credential_present` →
  `credential_last_verified_at` → `last_test_connection_result == 'pass'`
  → `last_readiness_result in ('pass', 'warning')`. Raises `UserError`
  before any write when missing; leaves state unchanged; creates no
  audit job on rejection; calls no Shopify API; runs no readiness check.
  Added `test_activate_rejects_stale_evidence_after_credential_replace`
  (activates once with fresh verified evidence, replaces the token via
  the existing credential service, confirms the mirrors go stale
  relative to the new credential, confirms the second `action_activate()`
  raises `UserError`, confirms state does not become `connected`, and
  confirms no new lifecycle audit job is created). Updated every existing
  test that expects a successful (or evidence-specific-failure)
  `action_activate()` call to also seed `credential_last_verified_at`
  via a direct store write alongside the other evidence-mirror fields
  (`last_test_connection_result`/`last_readiness_result`) — this matches
  the file's existing convention of seeding those mirrors directly for
  unit-level activate/reconnect tests, since no dedicated credential-
  service method stamps `credential_last_verified_at` outside a live/
  mocked `action_test_connection()` run. The prior `action_reconnect()`
  missing-credential transaction-safety fix (PR #121's previous revision)
  is untouched and confirmed intact. **No scope expansion** — no OAuth/
  setup wizard/UI/sync/domain implementation, no security/ACL change, no
  new job state/type/source.
- **Local validation performed:** `python -m py_compile` on both changed
  Python files — passes. **No Odoo runtime is available in this session's
  container**, so the test suite was not executed here — stated honestly;
  the same Odoo.sh/manual validation command from the original PR #121
  handoff entry still applies:
  `odoo-bin -d <db> -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --log-level=test`.
- **VAL-B2 remains deferred / not passed. MBQ-05 remains partially routed /
  open. TD-002 remains open.** Unchanged by this revision.
- **Learning feedback loop:**
  - New issues discovered: the stale-activation-evidence-after-credential-
    replace issue above, found by ChatGPT's re-review — a second instance
    of the same defect class as the earlier stale-evidence-after-
    disconnect fix (credential-service writes that clear a presence/
    verification mirror without also clearing the pass/fail evidence
    mirrors that were computed against the old credential).
  - Repeated issue patterns: **yes** — this is the second "credential-
    service mutation leaves a stale pass/pass evidence mirror behind"
    defect found in this PR (first: `action_disconnect` vs.
    `action_activate`'s `credential_present` check; second:
    `action_replace_token` vs. `action_activate`'s
    `credential_last_verified_at` check). Worth a standing rule for
    future lifecycle/credential work: any credential-service write that
    clears a presence/verification field must be checked against every
    consumer of the evidence mirrors it does *not* clear.
  - Rules/checklists updated: none (out of this revision's allowed-files
    scope) — flagged above for a future docs-scoped session to formalize.
  - New rejected approaches: none.
  - New technical debt: none.
  - Tests or review gates needed: none beyond the regression test added.
  - Should future prompts change? Worth considering, for a future
    docs-authorized session, adding an explicit "stale-mirror" check to
    whatever future review checklist covers this connector's credential/
    lifecycle surface — not actioned here since it is out of this
    revision's allowed-files scope.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a) · technical debt
  logged (n/a) · repeated-issue escalation applied (noted above as a
  pattern; no rule file updated, out of scope) — all YES.
- **Next step:** ChatGPT re-review of the revised PR #121.
- **Stop condition:** stopped at the scoped boundary — exactly the three
  allowed files touched; no merge; PR remains draft, not marked ready for
  review.

### Task 005 PR #121 revision — reconnect transaction-safety fix — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-lifecycle-actions-k3ixq5` → PR #121 into
  `Shopify-connector` (**draft**, unmerged; same PR, revised in place — no
  new PR opened).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/tests/test_connection_lifecycle.py`,
  `docs/01-research/research-handoff.md` (this entry). No other file
  touched — `shopify_connector_job.py`, `__manifest__.py`,
  `tests/__init__.py`, and every XML/CSV/security/migration/CI/domain/UI
  file remain untouched by this revision.
- **What changed:** ChatGPT's review of PR #121 found a transaction-safety
  issue in `action_reconnect()`'s missing-credential branch: it wrote
  `state='reconnect_needed'` and created the lifecycle audit job, then
  raised `UserError` — in normal Odoo RPC/service execution a raised
  exception can roll back ORM writes made earlier in the same call, so the
  state/audit write this branch exists to guarantee might never actually
  persist. **Fixed** by removing the `raise` after the write: the
  missing-credential branch now only writes `state='reconnect_needed'`,
  creates the audit job, and `return`s `None` — no Shopify call, no
  readiness run, no credential clear, no auto-reconnect, unchanged
  otherwise. The existing `test_reconnect_missing_credential_does_not_connect`
  test was updated to no longer expect `UserError`, and now asserts the
  call returns `None`, the state persists as `reconnect_needed`,
  `credential_present` stays `False`, exactly one lifecycle audit job is
  created, and no `core_test_connection`/`core_readiness_check` job is
  created. `action_activate()`'s existing `UserError`-on-rejected-evidence
  tests are unchanged — that method intentionally leaves state untouched
  on rejection rather than writing first, so it has no equivalent
  transaction-safety issue. PR #121's body was updated to match (the
  `action_reconnect()` bullet no longer says "raises `UserError`").
  **No scope expansion** — no OAuth/setup wizard/UI/sync/domain
  implementation, no security/ACL change, no new job state/type/source.
- **Local validation performed:** `python -m py_compile` on both changed
  Python files — passes. **No Odoo runtime is available in this session's
  container**, so the test suite was not executed here — stated honestly;
  the same Odoo.sh/manual validation command from the original PR #121
  handoff entry below still applies:
  `odoo-bin -d <db> -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --log-level=test`.
- **VAL-B2 remains deferred / not passed. MBQ-05 remains partially routed /
  open. TD-002 remains open.** Unchanged by this revision.
- **Learning feedback loop:**
  - New issues discovered: the reconnect missing-credential
    transaction-safety issue above, found by ChatGPT's review (not by
    this session's own prior adversarial-review pass) — logged here as a
    gap in that pass's coverage (it checked for duplicate writes/audits
    but not for a write-then-raise rollback risk).
  - Repeated issue patterns: none.
  - Rules/checklists updated: none (out of this revision's allowed-files
    scope).
  - New rejected approaches: none.
  - New technical debt: none.
  - Tests or review gates needed: worth noting for future sessions —
    "does this method write state/audit and then raise?" is now a
    pattern to check for across all four lifecycle actions, not just
    `reconnect`; `action_disconnect`/`action_mark_reconnect_needed` do
    not raise at all (no issue), and `action_activate` raises *before*
    any write (no issue) — confirmed by inspection, not newly changed.
  - Should future prompts change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a) · technical debt
  logged (n/a) · repeated-issue escalation applied (n/a) — all YES.
- **Next step:** ChatGPT re-review of the revised PR #121.
- **Stop condition:** stopped at the scoped boundary — exactly the three
  allowed files touched; no merge; PR remains draft, not marked ready for
  review.

### Task 005 Connection Lifecycle Actions — implementation — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-lifecycle-actions-k3ixq5`, branched from
  latest `origin/Shopify-connector` (includes PR #120 merge commit
  `69b67ece38ea1db27144f7eaa92f9d37076e0593`) → **draft** PR into
  `Shopify-connector` (this session's PR; not merged, not marked ready for
  review). First code-implementation session in this project (gated by
  `task-005-connection-lifecycle-gate.md` and `DEC-022-task-005-scope.md`,
  both merged via PR #120).
- **Files changed:** `addons/shopify_connector_core/__manifest__.py`
  (version `19.0.1.3.0` → `19.0.1.4.0` only),
  `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `addons/shopify_connector_core/tests/__init__.py`,
  `addons/shopify_connector_core/tests/test_connection_lifecycle.py` (new),
  `docs/01-research/research-handoff.md` (this entry). No XML/CSV/security/
  migration/CI/controller/webhook/UI/wizard file touched; no domain-module
  file touched; no other docs file touched.
- **What changed:** implemented the four Task 005 connection-lifecycle
  actions on `shopify.connector.store` — `action_activate()`,
  `action_disconnect()`, `action_reconnect()`,
  `action_mark_reconnect_needed(reason=False)` — plus a shared
  `_create_lifecycle_audit_job()` helper that records every transition as
  an audited `core_manual_maintenance` job/log row (reusing the existing
  `_system_append` path, no new job type/log path). Added
  `BUSINESS_JOB_SOURCES` and store-state gating to
  `shopify_connector_job.py`: `create()` blocks business-job creation
  unless the store is `connected`; `write()` blocks a business job's move
  to `running` unless the store is `connected` at that moment (the
  create→execute race guard). `action_test_connection()`'s existing
  `ShopifyClientError` handler now also calls
  `action_mark_reconnect_needed()` on any auth/permission/scope-
  invalidation signal (`credential_invalid` or
  `error_class == 'shopify_permission_scope_auth'`), not only a
  genuine token-invalid one. `disconnect` reuses the existing Task 002
  `action_clear_token` service (no second clear path) and cancels
  non-terminal business jobs via the existing `TERMINAL_JOB_STATES`
  import, never a re-typed literal.
- **Self-review / independent adversarial review (Workflow tool, 3
  parallel review lenses + synthesis) found and this session fixed three
  real issues before commit:**
  1. `action_activate()` did not check `credential_present`, so a stale
     `last_test_connection_result`/`last_readiness_result` pass mirror
     left over from *before* a `disconnect` could silently re-activate a
     credential-less store. Fixed: `action_activate()` now also requires
     `credential_present`.
  2. `Job.write()`'s execution-time gate read the job's *pre-write*
     cached `job_source`/`store_id`, so a single `write()` call that also
     changed `job_source`/`store_id` alongside `state='running'` could
     bypass the gate (both fields are UI-`readonly` only, not
     ORM-enforced). Fixed: the gate now evaluates the effective
     post-write values (`vals` when present, current value otherwise).
  3. `action_reconnect()` double-wrote `state='reconnect_needed'` and
     created two audit jobs for one logical attempt whenever the nested
     `action_test_connection()` call itself already auto-transitioned via
     an auth-classified failure. Fixed: `action_reconnect()` now detects
     this (via the freshly created `core_test_connection` job's
     `error_class`) and skips the redundant re-write/audit; every other
     failure path (identity mismatch, temporary/throttle/unknown errors,
     readiness-only failure) still audits exactly once, unaffected.
  All three fixes are covered by new, explicit tests (see below).
  Two lower-confidence items were considered and consciously **not**
  changed: (a) `create()`'s per-call batch atomicity (a failing business
  entry in a hypothetical future multi-record `Job.create([...])` call
  would collaterally block a sibling core entry in the same call) — no
  current caller batches heterogeneous job sources in one `create()`
  call; (b) no `FOR UPDATE` row lock closes the narrow TOCTOU window
  between the state check and the guarded write under concurrent
  disconnect — the gate document's own §11 "Open risks" already frames
  the two-checkpoint (enqueue + execution) re-check as the required
  mechanism, not full transactional exclusivity, so a row lock would be
  scope creep beyond this task's "service/model layer only" scope.
- **Tests added:** `tests/test_connection_lifecycle.py` — one
  `TransactionCase`, ~40 tests covering: activate (pass/pass,
  pass/warning, missing evidence, failing evidence, fail test-connection,
  missing credential, stale-evidence-after-disconnect); disconnect
  (credential clear, credential-row preservation, state transition,
  business-job cancellation with reason/log, core-job/terminal-job
  non-interference, idempotency); business-job create-time gating (all
  three non-connected states × all five business sources blocked;
  connected succeeds; core sources always creatable); business-job
  execution-time gating (blocked when disconnected mid-flight, succeeds
  when connected, the two same-call bypass-attempt tests, cancel-while-
  disconnected allowed, core jobs never gated); `action_mark_reconnect_
  needed` (state set, credential kept, idempotent);
  `action_test_connection`'s auto-transition wiring (credential-invalid
  path, shop-state-failure path, success path does not auto-activate);
  reconnect (missing credential, connects on pass/pass, connects on
  pass/warning, remains `reconnect_needed` on readiness failure, on
  test-connection failure, on credential-invalid failure, on identity-
  mismatch failure — the last three each assert exactly one audit job,
  proving the double-audit fix); and a no-secret-leakage sweep across
  activate+disconnect. All Shopify API calls are mocked at the existing
  `_send`/`run_for_store` seams — no live network, no real credentials.
- **Local validation performed:** `python -m py_compile` on every changed
  Python file — passes. **No Odoo runtime/CI is available in this
  session's container** (`python3 -c "import odoo"` fails — module not
  installed; no `odoo-bin` on `PATH`), so the test suite itself was
  **not executed** in this session — this is stated honestly, not
  claimed as passing. Manual/Odoo.sh validation command for a future
  session or reviewer with a runtime:
  `odoo-bin -d <db> -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --log-level=test`.
- **Docs/code boundary confirmed respected:** only the allowed files
  listed above changed (verified via `git diff --stat` against the PR
  #120 merge-base, plus an independent governance-compliance review
  agent's 10/10-pass audit); no XML/CSV/security/migration/CI file; no
  domain-module file (`shopify_connector_product/_customer/_sale/
  _inventory/_fulfillment/_accounting/_refund/_payout/_multi_store`); no
  `perm_create` grant added anywhere (`security/ir.model.access.csv` is
  untouched); no OAuth/setup-wizard/UI/controller/webhook file; no new
  job state, job type, or job source added to
  `shopify_connector_job.py`'s selections (only a new plain-Python
  `BUSINESS_JOB_SOURCES` tuple over the existing source values); exactly
  the same two `sudo()` call sites as before this session
  (`shopify_connector_job_log.py`, `shopify_connector_store_credential.py`
  — confirmed by the existing AST-based guard tests, which still pass by
  inspection since no new file adds a `sudo()` call).
- **VAL-B2 remains deferred / not passed.** No live Shopify connection
  was attempted or claimed this session; `activate`/`reconnect` still
  report the existing Task 003/004 unknown/not-proven fail-closed state
  whenever real evidence is absent — unchanged.
- **MBQ-05 remains partially routed / open**, not fully resolved.
  Unchanged by this session — `reconnect` calls the existing Task 003/004
  substrate exactly as-is, independent of the eventual token-acquisition
  direction.
- **TD-002 remains open**, not fixed — out of this task's scope, not
  touched.
- **TD-001 remains Resolved.** Unchanged by this session.
- **Learning feedback loop:**
  - New issues discovered: the three real defects listed above (stale-
    evidence activate bypass; write()-gate stale-value bypass; reconnect
    duplicate-audit) — all found by an independent adversarial review
    pass before commit, all fixed in this same session, all now covered
    by explicit regression tests.
  - Repeated issue patterns: none new; this session's UUID4-nonce
    `payload_hash` pattern for `_create_lifecycle_audit_job` follows the
    same TD-001-avoidance convention already established by
    `action_test_connection`/`run_for_store` — no new instance of that
    class of defect was introduced.
  - Rules/checklists updated: none this session (docs-only rule changes
    are out of this task's allowed-files scope).
  - New rejected approaches: none — `rejected-approaches-log.md` was
    checked; nothing in this implementation revisits a logged rejection.
  - New technical debt: none logged. The two lower-confidence review
    items (batch-create atomicity; TOCTOU row-locking) are design
    tradeoffs explicitly within the gate document's own accepted risk
    framing (§11), not undisclosed shortcuts, so they are recorded here
    in this handoff rather than as a new technical-debt register row —
    flagged for ChatGPT review to confirm that treatment is correct.
  - Architecture concerns: none beyond what's already recorded in the
    gate document's own "Open risks" §11.
  - Tests or review gates needed: an Odoo runtime run of
    `--test-tags /shopify_connector_core` is still needed before this can
    be called fully verified — flagged above, not hidden.
  - Should future prompts change? No process change recommended; the
    adversarial-review-before-commit step this session added (via the
    Workflow tool) caught real bugs that a single-pass implementation
    would have shipped — worth keeping as a standing practice for future
    code-implementation sessions, not a prompt-template change.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a, none reintroduced) ·
  technical debt logged (n/a, no new debt; two accepted design tradeoffs
  recorded above for reviewer visibility) · repeated-issue escalation
  applied (n/a) — all YES.
- **Next step:** ChatGPT code review of this draft PR — in particular the
  three self-found-and-fixed issues above, and the two consciously-not-
  fixed lower-confidence items (batch-create atomicity, TOCTOU row
  locking), to confirm the "not fixed" calls are correct or to direct a
  follow-up.
- **Stop condition:** stopped at the scoped boundary — exactly the
  allowed files touched; no XML/CSV/security/migration/CI/domain/UI/OAuth
  file created or modified; no `perm_create` grant; no new job state/
  type/source; VAL-B2 remains deferred, not passed; MBQ-05 remains
  partially routed/open; TD-002 remains open; tests added but not run
  (no Odoo runtime available, stated honestly); PR opened as **draft
  only**, not marked ready for review, not merged.

### Task 005 Connection Lifecycle Gate Opening — compact handoff (2026-07-08)

- **Branch / PR:** `claude/task-005-gate-opening-jr5a9i`, branched from
  latest `origin/Shopify-connector` (includes PR #118 merge commit
  `440b9beec108bf1cf7617688f1e32ba60b6a661f` and PR #119 merge commit
  `eb5d8d91b46c4b3e21c1387eee03bc9688b773e6`) → **draft** PR into
  `Shopify-connector` (this session's PR; not merged).
- **Files changed:** `docs/07-implementation-plan/task-005-connection-lifecycle-gate.md`
  (new), `docs/04-decisions/DEC-022-task-005-scope.md` (edited),
  `docs/01-research/research-handoff.md` (this entry). **No `addons/`
  file, no Python/XML/CSV/manifest/security/test/migration/CI file
  touched. No code changed.**
- **What changed:** the Task 005 gate-opening document created;
  **DEC-022 accepted at gate-opening level** — status changed from
  "Proposed, not accepted" to "Accepted — Task 005 gate opened for final
  implementation prompt." **Task 005 scope:** connection lifecycle actions
  (`activate`, `disconnect`, `reconnect`, `reconnect_needed`
  auto-transition, business-job enqueue/execution gating by store
  connection state) — service/model layer only, no UI.
- **Key decisions recorded** (full text in
  `task-005-connection-lifecycle-gate.md` §4):
  - **Disconnect cancels non-terminal business jobs**, preserving history —
    no job record deleted; core maintenance/readiness jobs and
    terminal-state jobs unaffected.
  - **Store/settings `perm_create` remains closed** — no grant on
    `shopify.connector.store` or `shopify.connector.store.settings`.
  - **Business job enqueue/execution requires store state `connected`** —
    gated at both enqueue time and execution time (defense in depth); a
    store-state change after enqueue must fail closed before any Shopify
    operation.
  - `activate`/`reconnect` semantics: never infer connection success; only
    transition to `connected` on actual Task 003/004 evidence; never claim
    VAL-B2 passed; no OAuth/setup-wizard logic.
  - `reconnect_needed`: auto-transition on auth/permission/scope-
    invalidation signal; no automatic reconnect; human/admin action
    required to leave the state.
- **No code changed.** No OAuth, setup wizard, UI, or sync implementation
  of any kind was created or authorized — this document opens the gate for
  a separate, later `CLAUDE.md` §9 final implementation task prompt only.
- **VAL-B2 remains deferred / not passed.** Unchanged by this session — no
  live Shopify connection was attempted or claimed.
- **MBQ-05 remains partially routed / open**, not fully resolved. Unchanged
  by this session (PR #119's routing note stands as-is).
- **TD-002 remains open**, not fixed. Unchanged by this session.
- **TD-001 remains Resolved.** Unchanged by this session.
- **Learning feedback loop:** no new defect pattern in shipped code (no
  code was touched); no new rejected approach (this session does not
  reintroduce any entry from `rejected-approaches-log.md`); no new
  technical debt (docs-only, decisions recorded, not implemented).
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a, none reintroduced) ·
  technical debt logged (n/a, no new debt) · repeated-issue escalation
  applied (n/a) — all YES.
- **Next step:** ChatGPT review of this gate-opening PR; if accepted, a
  separate, explicit `CLAUDE.md` §9 final Task 005 implementation task
  prompt, naming exact allowed/forbidden files (mirroring
  `task-004-final-implementation-prompt.md`), issued by ChatGPT in chat
  after this PR merges. Task 005 remains not implemented until that
  prompt is issued and a later, separate coding session executes it.
- **Stop condition:** stopped at the scoped boundary — docs-only session;
  exactly the 3 allowed files touched (2 new/edited plus this handoff), no
  other file created or modified; no code, test, manifest, security, XML,
  CSV, migration, or CI file touched; VAL-B2 remains deferred, not passed;
  MBQ-05 remains partially routed/open, not fully resolved; TD-002 remains
  open; Task 005 is not implemented; PR not merged, not marked ready for
  review.

### DEC-023 Limited Acceptance / MBQ-05 Routing — compact handoff (2026-07-08)

- **Branch / PR:** new branch off latest `origin/Shopify-connector` (which
  includes PR #117's merge commit
  `1436ca8efbb9daca1766d5c1774e1ced40869079`) → **draft** PR into
  `Shopify-connector` (this session's PR; not merged).
- **Files changed:** `docs/04-decisions/DEC-023-token-acquisition-and-val-b2.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/technical-debt-register.md`,
  `docs/01-research/research-handoff.md` (this entry). **No `addons/` file, no
  Python/XML/CSV/manifest/security/test/migration/CI file touched. No code
  changed.**
- **What changed:** records ChatGPT's **limited acceptance of DEC-023 as a
  routing decision only** — accepted: the staged VAL-B2 closure plan as the
  next evidence path, and Custom Distribution/manual-OAuth use restricted to
  one-store / same-Plus-org / private-customer / VAL-B2-evidence-gathering
  purposes only. Not accepted: Custom Distribution as a scalable
  multi-customer architecture. Not resolved: the many-unrelated-customer
  commercial-distribution architecture (Public distribution or another
  official scalable route remains a separate, gated research/decision task).
  MBQ-05's register row is updated with this same routing note (status:
  "Partially routed / Open"), preserving its full prior history. The
  `read_fulfillments` correctness concern is logged as **TD-002** in the
  technical debt register (Open, Medium severity) — not fixed.
- **DEC-023 status:** changed from "Proposed, not accepted" to **"Accepted in
  limited scope — routing decision only."** This is not a full acceptance of
  a final token-acquisition strategy.
- **VAL-B2 still deferred/not passed.** This acceptance is a routing
  decision, not evidence — no live Shopify connection was attempted; VAL-B2
  remains BLOCKED per `task-003-validation-results.md` and DEC-021's
  deferral is unchanged.
- **MBQ-05 partially routed but still open/not fully resolved.** The register
  row is explicitly **not** marked `Resolved` — it carries a new "Partially
  routed / Open" status note alongside its preserved history.
- **No OAuth, no setup wizard, no UI, no sync implementation** — none exist in
  this PR's scope, and none were added by this docs session.
- **Learning feedback loop:** No new defect pattern in shipped code beyond the
  already-flagged `read_fulfillments` concern, now formally logged as TD-002
  (new technical debt this session). No new rejected approach — this session
  does not adopt Custom Distribution as a scalable architecture, consistent
  with the existing `rejected-approaches-log.md` (RA-003) revisit condition.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a, none reintroduced) ·
  technical debt logged (TD-002, new) · repeated-issue escalation applied
  (n/a) — all YES.
- **Recommended next control-room step:** ChatGPT review of this routing
  patch; separately, authorize a future session with real Shopify Partner/Dev
  Dashboard access to execute `val-b2-closure-plan.md`, and/or authorize a
  dedicated research/decision task for DEC-023 §3.2 branch B (scalable
  many-unrelated-customer distribution).
- **Stop condition:** stopped at the scoped boundary — docs-only session;
  exactly the 4 allowed files touched, no new file created; no code, test,
  manifest, security, XML, CSV, migration, or CI file touched; VAL-B2 remains
  deferred, not passed; MBQ-05 remains open (partially routed), not fully
  resolved; no OAuth/setup wizard/UI/sync implementation.

### Token Acquisition / VAL-B2 / MBQ-05 Closure-Path Proposal — revision (second pass) — compact handoff (2026-07-08)

- **Branch / PR:** `claude/token-acquisition-val-b2-5zi8bg`, same branch as
  the original session below → PR #117 into `Shopify-connector`, **still
  draft, unmerged**. This entry documents a revision commit on the same PR,
  not a new PR.
- **Files changed:** `docs/01-research/shopify-token-acquisition-notes.md`,
  `docs/04-decisions/DEC-023-token-acquisition-and-val-b2.md`,
  `docs/05-qa/val-b2-closure-plan.md`, `docs/01-research/research-handoff.md`
  (this entry) — the same 4 allowed files as the original session, edited in
  place. **No code changed. No `addons/` file, no
  Python/XML/CSV/manifest/security/test/migration/CI file touched.**
- **Reason for revision:** ChatGPT reviewed PR #117 and found one material
  issue — the proposal **overstated Custom Distribution as a scalable future
  MVP architecture for many unrelated customers**. Official Shopify docs are
  explicit that Custom distribution is scoped to "one store or multiple
  stores on the same Plus organization using a link," while Public
  distribution is the documented route to "distribute or sell your app to
  many merchants through the Shopify App Store"
  (https://shopify.dev/docs/apps/launch/distribution/select-distribution-method
  — Accessible — 2026-07-08).
- **What changed:** all three docs now clearly separate (a) the **one-store
  VAL-B2 evidence path** — a cross-organizational Custom Distribution app may
  be valid for a single pilot customer or purely for closing VAL-B2 — from
  (b) **scalable multi-customer/commercial distribution**, which Custom
  Distribution's documented scope does not cover and which now requires its
  own separate, gated evaluation of Public distribution or another
  officially-supported route (not performed by this session). DEC-023's
  former "vendor-owned Custom Distribution app, installed per customer"
  recommendation is withdrawn and replaced with a candidate-architecture
  split (branch A / branch B). The community-forum staff evidence is
  unchanged and still cited, but is now explicitly labelled as supporting
  OAuth token-flow mechanics only, never as evidence about distribution
  scale. The `read_fulfillments` least-privilege correctness concern (from
  the original session) is unchanged and still flagged, not fixed.
- **VAL-B2 still deferred, not passed.** Unchanged by this revision — no live
  Shopify connection was attempted.
- **MBQ-05 still open, not resolved.** Unchanged by this revision — DEC-023
  remains **Proposed, not accepted**.
- **PR #117 remains draft and unmerged** — not marked ready for review by
  this revision.
- **Learning feedback loop:** the overstatement is treated as a correction to
  this session's own not-yet-accepted proposal, not a new defect pattern in
  shipped code, and not a new rejected approach (no alternative was rejected
  — Custom Distribution's one-store use remains proposed for that narrow
  scope; only the many-customer claim was withdrawn). No new technical debt.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a) · technical debt logged
  (n/a) · repeated-issue escalation applied (n/a) — all YES.
- **Recommended next control-room step:** ChatGPT re-review of the revised
  DEC-023, `shopify-token-acquisition-notes.md`, and `val-b2-closure-plan.md`
  on PR #117.
- **Stop condition:** stopped at the scoped boundary — docs-only revision;
  exactly the 4 allowed files edited, no new file created; no code, test,
  manifest, security, XML, CSV, migration, or CI file touched; VAL-B2 remains
  deferred, not passed; MBQ-05 remains open, not resolved; PR #117 remains
  draft, unmerged, not marked ready for review.

### Token Acquisition / VAL-B2 / MBQ-05 Closure-Path Proposal — compact handoff (2026-07-08)

- **Branch / PR:** `claude/token-acquisition-val-b2-5zi8bg`, branched from
  `Shopify-connector` at PR #116's merge commit
  `f4a6ace519bed1073d9b76e0fd91823e03ab7a59` (independently confirmed as an
  ancestor before this session started) → **draft** PR into
  `Shopify-connector` (this session's PR; not merged).
- **Files changed:** `docs/01-research/shopify-token-acquisition-notes.md`
  (new), `docs/04-decisions/DEC-023-token-acquisition-and-val-b2.md` (new),
  `docs/05-qa/val-b2-closure-plan.md` (new),
  `docs/01-research/research-handoff.md` (this entry). **No `addons/` file, no
  Python/XML/CSV/manifest/security/test/migration/CI file touched. No code
  changed.**
- **What changed / research produced:** a research-and-proposal package for
  how the connector should acquire Shopify Admin API access for MVP, and how
  VAL-B2 should be closed, built on a 10-agent research fan-out (6 external
  Shopify-doc re-verification agents, 4 internal governance/code-reading
  agents) authorized under `CLAUDE.md`'s official-API-verification allowance.
  Re-verified live today: the January 1, 2026 legacy-custom-app creation
  cutoff, the Dev Dashboard/CLI client-credentials-only own-store path, and
  the custom-app exemption from the December 2025 expiring-offline-token
  mandate — **no material change since the 2026-07-07 research**. New this
  session: (a) Shopify Developer Community staff replies clarifying that the
  decision-critical "does OAuth work for a Dev-Dashboard custom app" question
  turns on **which organization owns the app relative to the store** —
  same-org (merchant's own store) routes to client-credentials-grant only
  (24h token); cross-org (vendor-owned app installed on a different
  organization's store) supports authorization-code-grant with a non-expiring
  offline token — evidence-backed but not yet empirically tested end-to-end;
  (b) exact current Admin API scope names for the MVP baseline, plus a
  **correctness finding** (not fixed, code untouched) that the shipped
  `REQUIRED_MVP_SCOPES` constant's `read_fulfillments` entry does not, per
  official docs, gate `Fulfillment`/`FulfillmentOrder` reads the way its name
  implies; (c) official OAuth security guidance (mandatory HMAC verification,
  pre-registered redirect URI, `state`/CSRF requirement, client-secret
  rotation sequence) for whenever a setup wizard is later built.
- **VAL-B2 still deferred/not passed.** Untouched by this session — no live
  Shopify connection was attempted or available; this remains true unless a
  future session with real Shopify Partner/Dev Dashboard access executes
  [`../05-qa/val-b2-closure-plan.md`](../05-qa/val-b2-closure-plan.md) and
  records live evidence.
- **MBQ-05 remains proposed/not fully resolved** — DEC-023 is a **decision
  proposal only** (Status: Proposed, not accepted); MBQ-05's register row is
  unchanged by this session (that file is outside this session's allowed-files
  list) and remains open until ChatGPT explicitly accepts DEC-023 and applies
  a corresponding register update.
- **No OAuth, no setup wizard, no UI, no sync implementation** — none exist in
  this PR's scope, and none were added by this docs session.
- **Items deferred:** the empirical cross-organizational OAuth exchange
  (DEC-023 §2/§3.1) remains unexecuted; the `read_fulfillments` scope-naming
  correctness finding (§5) remains unfixed; whether this project's own Shopify
  Partner account already holds a usable pre-2026 legacy custom app is
  unknown (requires a human operator to check).
- **Learning feedback loop:** No new defect pattern in this project's own
  code (the `read_fulfillments` finding is a pre-existing correctness question
  in already-shipped code, surfaced not introduced, by this docs-only
  session). No new rejected approach — checked `rejected-approaches-log.md` in
  full; the only on-topic entry (RA-003, public App Store distribution) is not
  reintroduced by this proposal's cross-org **Custom** Distribution direction.
  No new technical debt logged by this session (the scope-naming finding is
  flagged in DEC-023 §5 and the notes file, not filed as a TD entry, since
  `technical-debt-register.md` is outside this session's allowed files —
  logging it there is left for ChatGPT/a future session to do explicitly).
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a, none reintroduced) ·
  technical debt logged (n/a this session — flagged for a future session, not
  filed) · repeated-issue escalation applied (n/a) — all YES.
- **Recommended next control-room step:** ChatGPT review of DEC-023 — either
  accept, reject, or request revision of the §3.2 vendor-owned
  cross-organizational OAuth direction; separately, authorize (or decline) a
  future session with real Shopify Partner/Dev Dashboard access to execute
  `val-b2-closure-plan.md` and attempt to actually close VAL-B2.
- **Stop condition:** stopped at the scoped boundary — docs-only session;
  exactly the 4 allowed files touched (3 newly created); no code, test,
  manifest, security, XML, CSV, migration, or CI file touched; VAL-B2 remains
  deferred, not passed; MBQ-05 remains open, not resolved; no OAuth/setup
  wizard/UI implementation.

### Task 004 Acceptance / TD-001 Closure — compact handoff (2026-07-08)

- **Docs-only session.** This entry records post-merge acceptance for
  Task 004 — **no code changed in this documentation session.** Allowed
  files touched: `docs/05-qa/technical-debt-register.md`,
  `docs/05-qa/task-004-validation-results.md` (new),
  `docs/05-qa/task-004-manual-validation-checklist.md`,
  `docs/05-qa/task-004-quality-gates.md`,
  `docs/01-research/research-handoff.md` (this entry). No `addons/` file,
  no Python/XML/CSV/manifest/security/test/migration/CI file touched.
- **PR #115 merged** into `Shopify-connector` — merge commit
  `4145faf69ae6c1d541006890fc2b997fe4c07238` (head SHA before merge:
  `ddecd9d28ac543145e9b4ec303e84e2afbbd2b15`).
- **Task 004 readiness-check substrate accepted.** See
  [`../05-qa/task-004-validation-results.md`](../05-qa/task-004-validation-results.md)
  (new) for the full evidence record: environment, commands, results,
  evidence interpretation, what it does not prove, and the final
  acceptance decision.
- **TD-001 resolved.** `technical-debt-register.md`'s TD-001 row `Status`
  is now `Resolved`, with a resolution note citing PR #115, the merge
  commit, the fix (fresh UUID4 `payload_hash` for
  `core_readiness_check`), and the live regression-test evidence. The
  original TD-001 context (why it existed, how it was routed) is
  preserved, not deleted.
- **Live validation passed**, run against a real Odoo 19 + PostgreSQL
  registry on Odoo.sh (branch database
  `adamsmen-claude-task-004-readiness-substrate-me21qg-34601850`,
  commit `ddecd9d28ac543145e9b4ec303e84e2afbbd2b15`):
  - Full `shopify_connector_core` suite: `0 failed, 0 error(s) of 78
    tests`.
  - Focused `TestReadinessCheck`: `0 failed, 0 error(s) of 31 tests`.
- **`task-004-manual-validation-checklist.md`** updated with a top
  status note: PR #115 exists and has merged; automated/live Odoo.sh
  validation has passed; the checklist is now partially superseded by
  `task-004-validation-results.md`; the few steps not covered by the
  automated suite (literal server-log grep, literal UI/menu/cron-row
  inspection, literal revert-and-reinspect) remain optional future
  hardening, not an acceptance blocker, unless ChatGPT reopens them. The
  original checklist body is preserved as reference, not deleted.
- **`task-004-quality-gates.md`** updated with an "Acceptance status"
  block marking the implementation gate passed/accepted for the
  readiness-check substrate scope, plus targeted updates to the
  TD-001-tied checkboxes (§1, §3, §5) and the ChatGPT review gate (§10)
  — all citing PR #115 and the live-validation evidence.
- **VAL-B2 remains deferred, not passed.** Untouched by this session —
  the credential/test-connection check still only reads stored evidence
  and never asserts a live connection.
- **MBQ-05 remains deferred for Task 004 only, not resolved** as a final
  token-acquisition strategy. Untouched by this session.
- **No OAuth, no setup wizard, no UI, no lifecycle action, no
  product/customer/order/inventory/fulfillment/domain sync** — none
  exist in PR #115's scope, and none were added by this docs session.
- **Task 005 not started.**
- **Learning feedback loop:** No new defect pattern, no new rejected
  approach, no new technical debt introduced by this session (TD-001 is
  *closed*, not newly opened). This session's own discipline — preserving
  original document context while adding superseding status blocks,
  rather than deleting history — follows the standing DP-007 "sweep
  status lines without erasing history" lesson.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged (n/a) · technical debt
  logged (TD-001 resolution recorded) · repeated-issue escalation applied
  (n/a) — all YES.
- **Recommended next control-room step:** decide the next gated task —
  either Task 005 planning, or a small documentation/governance gate
  before any setup-wizard/OAuth work — per the open MBQ register and
  this project's phase-gate discipline. No task is self-authorized to
  start by this entry.
- **Stop condition:** stopped at the scoped boundary — docs-only session;
  exactly the 5 allowed files touched (one newly created); no code, test,
  manifest, security, XML, CSV, migration, or CI file touched; TD-001
  marked `Resolved`; VAL-B2 remains deferred, not passed; MBQ-05 remains
  deferred for Task 004 only, not resolved; Task 005 not started.

### Task 004 Implementation — Readiness-Check Substrate + TD-001 Fix — compact handoff (2026-07-07)

- **Branch / PR:** `claude/task-004-readiness-substrate-me21qg`, branched
  from `Shopify-connector` at PR #114's merge commit
  `a4dbbb44c765a6341491f7e572e5fb705c70c1cc` → **draft** PR into
  `Shopify-connector` (this session's PR; not merged, not marked ready).
  PR #114 (gate acceptance / TD-001 route selection) was confirmed merged
  before this session started coding — its head SHA
  (`e0214857df559d422b785e4574fbe7c8132b803e`), base
  (`0848b8cde5720162b795936161e884678ae52c71`), and 6-file allowed-files
  diff were independently re-verified against `origin/Shopify-connector`
  before this branch was created.
- **Revision (ChatGPT review, same PR, 2026-07-07).** ChatGPT's review of
  PR #115 found two correctness issues and returned it for a targeted
  fix, not acceptance:
  1. `_check_required_scopes()` previously passed on **any non-empty**
     `granted_scopes` JSON list (e.g. a single `read_products` scope
     alone was enough) — it did not verify the actual scopes needed for
     Phase 1. **Fixed:** a new `REQUIRED_MVP_SCOPES` constant (the six
     Phase-1 read scopes — `read_products`, `read_customers`,
     `read_orders`, `read_inventory`, `read_locations`,
     `read_fulfillments`) is now checked; the result is `fail` (not
     `not_proven`) with a reason naming every missing scope if one or
     more required scopes is absent, `pass` only when all six are
     present (extra granted scopes are still allowed), and unchanged
     `not_proven` behavior for an absent/malformed/empty snapshot.
  2. `_check_domain_flag_enablement()` previously passed merely because
     a `shopify.connector.store.settings` record **existed** for the
     store, even if every domain flag on it was `False` (i.e., no sync
     domain would actually run). **Fixed:** a new
     `ACCEPTED_DOMAIN_FLAGS` constant (the four DEC-008 domain flags)
     is now checked; the result is `fail` with the reason "No sync
     domain is enabled." when a settings record exists but every
     accepted flag is `False` (confirmed `notification_default_enabled`
     alone still does not pass, since it is not one of the four
     accepted flags), `pass` only when at least one accepted flag is
     `True`, and unchanged `not_proven` behavior when no settings
     record exists at all.
  - Both fixes stayed inside
    `addons/shopify_connector_core/models/shopify_connector_readiness_check.py`
    — no forbidden file was touched, no new file was needed.
  - **Tests added/updated:** 14 new test methods in
    `test_readiness_check.py` (7 for the required-scopes fix — all
    required present passes; missing one fails and names it; extra
    scope still passes; a single scope is not enough; malformed JSON /
    empty list / absent snapshot are all `not_proven`; and 7 for the
    domain-flag fix — no settings record is `not_proven`; all-flags-False
    is `fail`, not `pass`; `notification_default_enabled` alone does not
    pass; each of the four accepted flags passes on its own). Every
    pre-existing test — the TD-001 regression pair, the aggregation
    unit tests, the credential/VAL-B2 tests, the payload-snapshot/
    mirror/seam/read-only/redaction tests, and both AST-level structural
    scans — is unchanged and still present. Test-method count:
    **17 → 31** (this corrects a stale count: the prior handoff entry
    said "20," which was already inaccurate against the actual
    17-method file committed at PR-open time — confirmed by
    `git show HEAD:...test_readiness_check.py \| grep -c 'def test_'`
    before writing this note).
  - **Tests run this revision:** `python3 -m py_compile` on both
    changed files (pass); the same throwaway, uncommitted dry-run
    harness used in the original session (updated to match the new
    scope/flag semantics) — 50/50 assertions pass, zero defects in the
    model file itself; both AST-level structural regression checks
    manually replayed and still pass (2 `sudo()` sites, unchanged; zero
    mutating calls in any `_check_*` method). No Odoo/PostgreSQL
    runtime is available in this environment (same as the original
    session), so the live `TransactionCase` suite was still not
    executed — stated honestly, not silently skipped.
  - VAL-B2 remains deferred, not passed; MBQ-05 remains deferred for
    Task 004 only, not resolved; TD-001's fix and regression test are
    unchanged and intact; no OAuth/setup-wizard/UI/lifecycle/domain-sync
    work was added. PR #115 remains **draft** and **unmerged**.
- **Task 004 implementation summary.** Implemented the readiness-check
  substrate for `shopify_connector_core` exactly per the finalized
  [`task-004-final-implementation-prompt.md`](../07-implementation-plan/task-004-final-implementation-prompt.md)
  and the MBQ-06/DEC-018 essential/warning split: a new
  `shopify.connector.readiness.check` `models.AbstractModel` service
  (`shopify_connector_readiness_check.py`) providing `run_for_store(store)`,
  a domain-extension registration seam (`_get_checks(store)`, overridable
  via classic `_inherit` + `super()` from a future domain module, tested
  with a `patch.object` seam test that proves a check can be injected
  without modifying any core file), fail-closed aggregation (`_aggregate`:
  any essential check not `pass` — including `not_proven` — forces overall
  `fail`; all essential `pass` + any warning not `pass` yields overall
  `warning`; all `pass` yields overall `pass`), and the nine core-owned
  essential checks accepted by MBQ-06 (credential/test-connection stored
  evidence, required scopes, API-version health, store identity,
  `web.base.url` HTTPS reachability, and three registered-pending-slot
  checks — webhook HMAC, mapped Location, cron/queue health — plus a
  domain-flag-enablement presence check). Each `run_for_store` call
  creates one `core_readiness_check` job, appends exactly two
  `job.log` rows via the existing `_system_append` path (an `attempt`
  start row, and a `verification_read` completion row carrying the
  per-check JSON array in `payload_snapshot`), mirrors the summary onto
  `store.last_readiness_result`/`_at` (both fields already existed on
  `shopify.connector.store` — no field addition was needed), and marks
  the job `succeeded` regardless of whether the readiness result itself
  is pass/fail/warning (the job records that the *evaluation* completed,
  not that it passed). **By design, a fresh/current-state store always
  computes overall `fail`** — the three registered-pending-slot checks
  (webhook HMAC, mapped Location, cron/queue health) are essential per
  MBQ-06 and have no real signal to read yet (no webhook, domain, or cron
  implementation exists), so fail-closed aggregation correctly withholds
  `pass`/`warning` until those future tasks exist. This is intentional,
  not a defect, and is exactly what DEC-021 §4 requires ("no
  customer-facing readiness pass ... based on an unproven live
  connection" / no inferred pass from absent data) — confirmed by both a
  dry-run harness and `test_fresh_store_never_passes_readiness`.
- **TD-001 fix implemented, pending ChatGPT review.** `core_readiness_check`
  job creation inside `run_for_store` now uses its own fresh UUID4
  `payload_hash` nonce, exactly mirroring the already-accepted
  `action_test_connection`/`core_test_connection` pattern in
  `shopify_connector_store.py` (Task 003) — the fix lives entirely inside
  the new file's own job-creation call, as required; **neither
  `shopify_connector_job.py` nor `shopify_connector_store.py` was
  touched**, so `core_test_connection`'s own behavior is unchanged (a
  focused test, `test_core_test_connection_repeat_run_still_does_not_collide`,
  confirms the shared idempotency-key substrate still yields distinct
  keys for two `core_test_connection` creations). The mandatory
  regression test (`test_td001_repeated_readiness_job_does_not_collide`)
  proves two `core_readiness_check` job-creation attempts for the same
  store both succeed with distinct `payload_hash`/`idempotency_key`
  values — no `store_idempotency_key_uniq` collision. **TD-001 remains
  `Open` in `technical-debt-register.md`** — per the accepted prompt, its
  Status is intentionally left for ChatGPT to mark `Resolved` after this
  PR is reviewed and accepted, not changed unilaterally in this PR (that
  file is not in this task's allowed-files list).
- **Files changed (exactly, confirmed by `git diff --name-only` against
  `origin/Shopify-connector`):**
  - `addons/shopify_connector_core/models/shopify_connector_readiness_check.py`
    (new)
  - `addons/shopify_connector_core/models/__init__.py` (one import line
    added)
  - `addons/shopify_connector_core/tests/test_readiness_check.py` (new)
  - `addons/shopify_connector_core/tests/__init__.py` (one import line
    added)
  - `addons/shopify_connector_core/__manifest__.py` (version
    `19.0.1.2.3` → `19.0.1.3.0` only)
  - `docs/01-research/research-handoff.md` (this entry)
- **Tests run.** `python3 -m py_compile` on every changed `.py` file
  (pass, no syntax errors). **No Odoo runtime or PostgreSQL is installed
  in this execution environment** (`python3 -c "import odoo"` fails;
  no `odoo-bin`; no `pyflakes`/`flake8`/`pylint` available either), so
  the 17 `TransactionCase` tests in `test_readiness_check.py` (the count
  at PR-open time — see the revision note above for the corrected count
  after this same PR's later revision) were
  **not** executed against a live Odoo registry — mirroring the Task
  001A precedent, this is stated honestly, not silently skipped or
  claimed as run. As additional, stronger-than-`py_compile` diligence
  (not a substitute for a real Odoo test run), a throwaway, uncommitted
  dry-run harness (minimal hand-written `odoo.api`/`fields`/`models`
  stub, scratchpad-only, never touches the repo) imported the actual
  `shopify_connector_readiness_check.py` module unmodified and exercised
  every `_check_*` method, `_aggregate`, `_get_checks`, and
  `run_for_store` against fake store/job/job.log/env objects covering
  every branch named in the acceptance criteria (all passed, 41/41
  assertions) — this caught zero defects in the model file itself, giving
  moderate additional confidence the logic is correct beyond syntax
  validity, but it is **not** a substitute for the real `TransactionCase`
  suite against a
  live Odoo/PostgreSQL registry. The two AST-level structural regression
  checks — the pre-existing `test_source_level_two_sudo_sites_total`
  (`test_job_log_system_append.py`) and this task's new
  `test_source_level_no_check_method_mutates_state`
  (`test_readiness_check.py`) — were manually replayed standalone against
  the real files and both pass: the new file adds **zero** `sudo()` call
  sites (the existing two-site inventory is unchanged), and no
  `_check_*` method contains a `write`/`create`/`unlink`/`execute`/`sudo`
  call. **One test-file-only defect was found and fixed during the
  self-review loop** (not a model-logic defect): the first draft of
  `test_readiness_check_only_writes_its_own_mirror_fields` compared a
  store's full `read()` dict before/after `run_for_store` and excluded
  only `__last_update`, which would have made the test fail against a
  real Odoo registry (`write_date`/`write_uid` change on every `write()`
  call, unrelated to this task's own mirror fields) — corrected by also
  excluding `write_date`/`write_uid` before this PR was opened.
- **Tests not run and why:** the full `test_readiness_check.py` suite
  (17 test methods at PR-open time; 31 after this same PR's later
  ChatGPT-review revision — see the revision note above) and the two
  pre-existing test files that share the `models/` directory scan were
  not executed as live Odoo `TransactionCase` runs — no Odoo/PostgreSQL
  runtime exists in this container. `docs/05-qa/task-004-manual-validation-checklist.md`
  (already prepared by the PR #114 gate-acceptance session) remains the
  mandatory live-validation evidence for a future session with a real
  Odoo instance, per that document's own preconditions.
- **No OAuth / setup wizard / domain sync / UI / lifecycle work:**
  confirmed. Zero XML, view, menu, action, wizard, controller, cron, or
  webhook file exists anywhere in this diff; zero
  `shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment` file
  touched; zero activation/disconnect/reconnect code added.
  `shopify_connector_store_credential.py` and every file under
  `security/` are untouched.
- **No Shopify API call:** confirmed. Every check reads only
  already-stored core evidence (`store.last_test_connection_result`,
  `.granted_scopes`, `.api_health_state`/`_reason`, `.shop_domain`) or
  `ir.config_parameter` (`web.base.url`) — never
  `shopify.connector.api.client`. Both
  `test_readiness_check_never_calls_shopify_api_client` (patches
  `execute` to raise if called) and the AST read-only scanner enforce
  this structurally, not just behaviorally.
- **No secrets:** confirmed. Zero new `sudo()` call site (AST-verified
  against both this file and the whole `models/` directory); no
  credential/token value is read by any check; `_system_append`'s
  existing redaction contract still covers the new `payload_snapshot`
  writes, and `test_no_secret_leakage_in_job_or_log` confirms a dummy
  token embedded in a stored `last_test_connection_reason` never
  surfaces in any job/job.log field.
- **No customer-facing readiness claim:** confirmed — see the "by
  design, a fresh store always computes overall fail" note above; the
  credential/test-connection check reports `not_proven` (never `pass`)
  whenever `store.last_test_connection_result` has never recorded a
  pass, per DEC-021 §4, exactly as `test_credential_check_unproven_without_val_b2_evidence`
  requires.
- **VAL-B2 / MBQ-05 unchanged by this session:** VAL-B2 remains
  deferred, not passed, not failed, not waived. MBQ-05 remains deferred
  for Task 004 only, not resolved as a final token-acquisition strategy.
  Neither is touched by this diff.
- **Learning feedback loop:** New issues / repeated patterns: none new.
  `defect-pattern-log.md`, `rejected-approaches-log.md`, and
  `architecture-review-log.md` were checked before implementation (per
  `pr-review-checklist.md` §"Before reviewing") — no rejected approach
  was reintroduced; no new defect pattern was introduced (the two
  AST-level structural regression tests reuse, rather than duplicate,
  the existing `test_source_level_two_sudo_sites_total` convention from
  Task 003, consistent with RA-013's "no forked per-domain
  logging"/single-substrate discipline extended to "no forked readiness
  logging"). Rejected approaches: none new — no design option was
  evaluated and rejected this session. Technical debt: TD-001's fix is
  implemented and regression-tested but its register `Status` column is
  intentionally left `Open` pending ChatGPT's review of this PR, per the
  final implementation prompt's own instruction; no new technical debt
  introduced (the three registered-pending-slot essential checks are
  the accepted MBQ-06 design, not a shortcut — they are explicitly
  documented as such, not silently stubbed). Architecture concerns:
  none new — no MBQ-06 residual beyond "exact copy/XML IDs remain open
  for implementation planning" was hit, and this task adds no UI/XML.
  Tests or review gates needed: a future session with a live Odoo
  runtime must execute `test_readiness_check.py` for real and complete
  `task-004-manual-validation-checklist.md`. Should future prompts
  change? No.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (n/a — none
  this session) · technical debt logged (TD-001 fix status recorded
  here; register file itself intentionally left for ChatGPT's
  post-review update, not this task's allowed-files list) ·
  repeated-issue escalation applied (n/a) — all YES.
- **Next recommended session:** ChatGPT reviews this Task 004
  implementation PR (readiness-check substrate + TD-001 fix). On
  acceptance: (1) mark TD-001 `Resolved` in
  `technical-debt-register.md`, (2) decide whether/when to run
  `task-004-manual-validation-checklist.md` against a live Odoo
  instance, (3) do not start Task 005, OAuth, the setup wizard, or any
  UI/domain-sync work without a separate, explicit gate-opening act.
- **Stop condition:** stopped at the scoped boundary — exactly the six
  allowed files changed; no forbidden file touched; the implementation
  PR is opened as **DRAFT** and is **not merged**; TD-001 is fixed and
  regression-tested but not marked `Resolved`; VAL-B2 remains deferred,
  not passed; MBQ-05 remains deferred for Task 004 only, not resolved;
  no OAuth/setup-wizard/UI/lifecycle/domain-sync work of any kind was
  started; Task 005 was not started.

### Task 004 Gate Acceptance / TD-001 Route Selected — compact handoff (2026-07-07)

- **Branch / PR:** `claude/task-004-gate-acceptance-338b3a`, branched from
  `Shopify-connector` at PR #113's merge commit
  `0848b8cde5720162b795936161e884678ae52c71` → draft PR into
  `Shopify-connector` (this session's PR). Docs-only session — no code,
  test, manifest, security, XML, CSV, migration, or CI file of any kind
  changed. **No addons/ file touched. No Task 004 implementation. No
  OAuth. No setup wizard.**
- **Gate accepted for Task 004 implementation planning.** ChatGPT's
  control-room decision records **acceptance** of
  [`task-004-readiness-check-substrate-gate.md`](../07-implementation-plan/task-004-readiness-check-substrate-gate.md)
  — status changed from "Proposed, not yet accepted" to "Accepted by
  ChatGPT, pending PR review/merge." This acceptance opens Task 004
  implementation *planning* only, and only once this PR is merged; Task
  004 implementation itself must still be run as a separate, later coding
  session, using
  [`task-004-final-implementation-prompt.md`](../07-implementation-plan/task-004-final-implementation-prompt.md),
  issued by ChatGPT in chat.
- **TD-001 route selected: fix inside Task 004.** ChatGPT chose option
  (a) from the gate document's TD-001 route section: TD-001 is fixed
  inside Task 004's own scope, as the **first mandatory implementation
  acceptance criterion** — not deferred to a separate "Task 001B" patch
  (that candidate is now retired). The fix must be minimal, scoped
  exclusively to target-less readiness jobs (`core_readiness_check`),
  must not alter the already-accepted `core_test_connection` behavior
  without explicit justification, and must include a mandatory regression
  test proving two `core_readiness_check` runs for the same store do not
  collide. **TD-001 remains `Open`** in `technical-debt-register.md` —
  this session records the routing decision, not a fix.
- **Files changed:**
  - `docs/07-implementation-plan/task-004-readiness-check-substrate-gate.md`
    — status changed to Accepted; TD-001 route section rewritten from an
    open (a)/(b) choice to the decided fix-inside-Task-004 disposition;
    acceptance-criteria/test-expectation/explicit-acceptance-requirement
    sections updated to match; all non-goals and constraints (no OAuth, no
    setup wizard, no UI, no lifecycle, no domain sync, no live-connection
    pass claim from unproven VAL-B2) preserved unchanged.
  - `docs/07-implementation-plan/task-004-final-implementation-prompt.md`
    — converted from a draft with unfilled `<PLACEHOLDER>`s into a
    finalized, ready-for-later-use prompt: exact allowed-files list
    (proposed after repo inspection — one new core model file, one new
    test file, two one-line `__init__.py` additions, a manifest version
    bump, and the research-handoff update), TD-001 disposition filled in
    as the first mandatory acceptance criterion with its regression-test
    requirement, forbidden files kept strict. Still marked "DO NOT RUN
    UNTIL THIS GATE-ACCEPTANCE PR IS MERGED AND CHATGPT ISSUES THIS
    PROMPT IN CHAT" — not executed by this session.
  - `docs/05-qa/task-004-manual-validation-checklist.md` — the "Repeated
    readiness job behavior / TD-001 regression check" item rewritten from
    a two-branch expectation to a single expected outcome (second job
    succeeds, no collision), removing the "TD-001 may remain unchanged"
    ambiguity.
  - `docs/05-qa/task-004-quality-gates.md` — pre-start-gate preamble and
    the TD-001 routing checkbox updated to record the decided route; the
    test-gate and retry/idempotency-gate TD-001 items updated from a
    branching expectation to a mandatory regression-test requirement.
  - `docs/05-qa/technical-debt-register.md` — TD-001's Owner column
    updated with "ROUTE SELECTED" wording (fix inside Task 004); Target
    resolution phase column updated to "Task 004 implementation." **TD-001
    is not marked fixed and not closed — Status remains `Open`.**
  - `docs/01-research/research-handoff.md` (this entry).
- **No code changed:** confirmed. This session touched only the six
  allowed Markdown files; `addons/`, and every
  `*.py`/`*.xml`/`*.csv`/manifest/security/test/migration/CI file, are
  unchanged.
- **Task 004 implementation still not started.** No readiness-check
  registry/service model, no TD-001 fix, and no test file exists in the
  repository as of this branch. This session records a planning-gate
  acceptance and a routing decision — it does not write code, and it does
  not run the finalized implementation prompt.
- **VAL-B2 / MBQ-05 unchanged by this session:** VAL-B2 remains deferred,
  not passed, not failed, not waived (per DEC-021). MBQ-05 remains
  deferred for Task 004 only, not resolved as a final token-acquisition
  strategy.
- **Learning feedback loop:** New issues / repeated patterns: none.
  Rules/checklists updated: none beyond the files listed above. Rejected
  approaches: the "Task 001B — job-framework target-less idempotency
  patch" candidate route is retired in favor of fixing TD-001 inside Task
  004 — recorded in `technical-debt-register.md`'s Owner column and the
  gate document, not in `rejected-approaches-log.md` (this is a routing
  choice between two previously-open options, not a rejected architecture
  approach). Technical debt: TD-001 unchanged in substance (still `Open`),
  only its routing note and target resolution phase updated. Architecture
  concerns: none new. Tests or review gates needed: the future Task 004
  implementation PR must include the mandatory TD-001 regression test.
  Should future prompts change? No — the finalized implementation prompt
  is now ready for ChatGPT to issue as-is once this PR merges.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (n/a — routing choice, not
  a rejected approach) · technical debt logged (routing note only, not a
  fix) · repeated-issue escalation applied (n/a) — all YES.
- **Next recommended session:** run the finalized
  [`task-004-final-implementation-prompt.md`](../07-implementation-plan/task-004-final-implementation-prompt.md)
  after ChatGPT review — but only once this PR is merged into
  `Shopify-connector` and ChatGPT explicitly issues that exact prompt text
  in chat as its own turn. No other Task 004, Task 005, or next-feature
  work should start before then.
- **Stop condition:** stopped at the scoped boundary — docs-only session;
  no code, test, manifest, security, XML, CSV, migration, or CI file
  touched; no addons/ file touched; Task 004 not marked implemented; the
  finalized implementation prompt was not run; VAL-B2 remains deferred,
  not passed; MBQ-05 remains deferred for Task 004 only, not resolved.

### VAL-B2 Deferral / Task 004 Gate-Opening Package — compact handoff (2026-07-07)

- **Branch / PR:** `claude/task-004-gate-opening-w3f1zg`, branched from
  `Shopify-connector` at PR #111's merge commit
  `43f3b2a923a420e523cd2ec2662a46e2a9abed26` → draft PR into
  `Shopify-connector` (this session's PR, not merged, not marked ready).
  Docs-only session — no code, test, manifest, security, XML, CSV,
  migration, or CI file of any kind changed. **No addons/ file touched. No
  OAuth implementation. No setup-wizard implementation. No lifecycle
  activation/disconnect/reconnect implementation. No product/customer/
  order/inventory/fulfillment implementation.**
- **Decision recorded:** ChatGPT's control-room decision that **VAL-B2 is
  deferred for the Task 003 → Task 004 gate only** — recorded in the new
  [`DEC-021`](../04-decisions/DEC-021-val-b2-deferral-for-task-004.md).
  VAL-B2 is **not passed, not failed, and not waived**. MBQ-05 (the
  token-acquisition direction) is **deferred for Task 004 only, not
  resolved** as a final MVP strategy. This deferral permits Task 004 to
  proceed to **gate-opening review only** — it does not authorize Task 004
  implementation.
- **Files changed:**
  - `docs/04-decisions/DEC-021-val-b2-deferral-for-task-004.md` (new) —
    the formal deferral decision record.
  - `docs/05-qa/task-003-validation-results.md` — §5 Go/No-Go updated from
    "not yet determined" to conditional acceptance for Task 004
    gate-opening review only, per DEC-021; §7 Handoff updated to match. No
    existing evidence, and no PR #109/#110 addendum content, was deleted
    or weakened.
  - `docs/04-decisions/shopify-token-acquisition-decision-brief.md` — new
    §11 "ChatGPT deferral decision for Task 004 gate" appended; §§1–10
    unchanged.
  - `docs/03-architecture/master-blueprint-open-questions.md` — MBQ-05 row
    updated to record the DEC-021 deferral ("Deferred for Task 004 / still
    required before customer-facing setup"); not marked resolved; open
    substance preserved.
  - `docs/05-qa/technical-debt-register.md` — TD-001's Owner/Target
    resolution columns updated with an explicit Task-004-gate routing
    note; TD-001 not marked fixed, not closed, still `Open`.
  - `docs/07-implementation-plan/task-004-readiness-preflight.md`,
    `task-004-dependency-map.md`, `docs/05-qa/task-004-quality-gates.md`,
    `docs/06-prompts/task-004-candidate-claude-prompts.md` — updated from
    "Task 004 remains blocked pending VAL-B2/MBQ-05" to: Task 004
    implementation is still not started; Task 004 may proceed to
    gate-opening review because VAL-B2 is formally deferred by ChatGPT via
    DEC-021; Task 004 still requires its own separate gate-opening act and
    final implementation prompt; TD-001 routing remains a hard pre-start
    condition; no customer-facing readiness/activation/wizard/domain-sync
    claim may depend on the unproven VAL-B2. Candidate prompts remain
    draft-only, not runnable, now with a prominent "do not use until
    DEC-021 is merged and the Task 004 gate is accepted by ChatGPT"
    warning on every candidate.
  - `docs/07-implementation-plan/task-004-gate-opening-proposal.md` (new)
    — the Task 004 gate-opening proposal (readiness-check-substrate
    objective, included/excluded scope, gate conditions).
  - `docs/07-implementation-plan/task-004-readiness-check-substrate-gate.md`
    (new) — the proposed gate document itself (exact constraints,
    non-goals, TD-001 route, MBQ-05 deferral conditions, acceptance
    criteria, test/rollback expectations, definition of done). **PROPOSED,
    NOT YET ACCEPTED** — does not open the gate.
  - `docs/07-implementation-plan/task-004-final-implementation-prompt.md`
    (new) — a draft future Claude Code prompt for Task 004 implementation,
    marked "DRAFT — DO NOT RUN UNTIL CHATGPT EXPLICITLY APPROVES AFTER
    REVIEW," with `<PLACEHOLDER>`s for exact allowed files and TD-001
    disposition.
  - `docs/05-qa/task-004-manual-validation-checklist.md` (new) — a future
    manual validation checklist for Task 004, marked not executed (no Task
    004 code exists yet).
  - `docs/01-research/research-handoff.md` (this entry).
- **What changed:** ChatGPT's VAL-B2 deferral decision is now recorded in
  writing (DEC-021) and threaded consistently through every file that
  previously stated Task 004 was blocked pending VAL-B2/MBQ-05. A complete
  Task 004 gate-opening *review* package now exists (proposal, gate
  document, draft final implementation prompt, future manual validation
  checklist) for ChatGPT to review. TD-001 is routed — named explicitly as
  a hard pre-start condition for the Task 004 gate — but not fixed.
- **What remains unresolved:**
  - **VAL-B2** — still not passed, not failed, not waived; still requires
    a real, valid Shopify Admin API token to actually execute.
  - **MBQ-05** — still open; deferred for Task 004 gate-opening review
    only, not resolved as a final token-acquisition strategy.
  - **OAuth/token acquisition** — still not attempted since PR #109's
    blocked-before-execution record; no Fable-equivalent tool or Shopify
    Dev Dashboard credentials were available to this session either (not
    re-attempted this session — this was a docs-governance session, not a
    token-acquisition session).
  - **Customer-facing setup readiness** — still not ready; the connector
    must not claim customer-facing setup readiness until VAL-B2 or an
    accepted replacement validation passes, per DEC-021 §4.
  - **TD-001** — routed explicitly to the Task 004 gate, but **not
    fixed**; its disposition (fixed-in-scope vs. separate pre-Task-004
    patch) remains an open choice for ChatGPT's review of the gate
    document.
- **Task 004 status after this PR:** ready for **gate-opening review
  only**, and only after ChatGPT accepts/merges this PR (and, separately,
  reviews and accepts
  `task-004-readiness-check-substrate-gate.md`). **Not
  implementation-started.** **No code authorized** by this PR, by DEC-021,
  or by any document in this package.
- **No code changed:** confirmed. This session touched only the Markdown
  files listed above; `addons/`, and every `*.py`/`*.xml`/`*.csv`/manifest/
  security/test/migration/CI file, are unchanged.
- **No secret exposed / no Shopify or Odoo side effects:** confirmed
  (vacuously) — no Shopify, Odoo, or credential interaction of any kind
  occurred this session.
- **Learning feedback loop:** New issues / repeated patterns: none this
  session — this was a straightforward decision-recording and
  gate-package-preparation session, not a research or validation session.
  Rules/checklists updated: none beyond the files listed above. Rejected
  approaches: none — no approach was rejected this session; nothing in
  `rejected-approaches-log.md` was re-proposed. Technical debt: TD-001
  unchanged in substance (still `Open`), only its routing note updated.
  Architecture concerns: none new. Tests or review gates needed: ChatGPT's
  own review and explicit acceptance of
  `task-004-readiness-check-substrate-gate.md` is the next required gate,
  per its own "Explicit acceptance requirement" section. Should future
  prompts change? Yes — any future Task 004 implementation prompt must be
  issued only after that acceptance, with TD-001's disposition filled in
  exactly as ChatGPT names it.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (routing note only, not a fix) · repeated-issue escalation
  applied (n/a) — all YES.
- **Next recommended session:** ChatGPT reviews this Task 004 gate-opening
  package — `DEC-021`, the updated Task 003 Go/No-Go, the updated MBQ-05
  row, the TD-001 routing note, and the three new gate-opening documents.
  **Only if ChatGPT explicitly accepts and merges
  `task-004-readiness-check-substrate-gate.md`** should a separate,
  future session issue the Task 004 final implementation prompt (filling
  in its remaining `<PLACEHOLDER>`s, including TD-001's disposition) as
  its own scoped coding session.
- **Stop condition:** stopped at the scoped boundary — docs-only session;
  no code, test, manifest, security, XML, CSV, migration, or CI file
  touched; no addons/ file touched; Task 004 not marked implemented; no
  claim that VAL-B2 passed or that MBQ-05 is resolved; this session did
  not merge its own PR.

### Task 003 Static/Offline Validation Sweep — compact handoff (2026-07-07)

- **Branch / PR:** `claude/task-003-static-validation-cszl88` → **PR #110**,
  draft into `Shopify-connector`, not merged, not marked ready. Docs-only
  session — no code, test, manifest, security, XML, or CSV change of any
  kind. **No Task 004 work of any kind in this session. No OAuth
  implementation. No setup-wizard change.**
- **Files changed:** `docs/05-qa/task-003-static-validation-sweep.md` (new),
  `docs/05-qa/task-003-server-log-redaction-check.md` (new),
  `docs/05-qa/task-003-no-side-effect-baseline.md` (new),
  `docs/05-qa/task-003-validation-results.md` (static/offline addendum
  appended; four summary-table rows annotated with static evidence, none of
  the prior live-session findings overwritten), `docs/01-research/research-handoff.md`
  (this entry; corrected the PR #108 entry's stale "draft PR, not merged"
  wording, which this session confirmed is merged, merge commit
  `76cd74e7cf585e1925c3ac280bd6ca97c55df7ab`; that correction was
  independently also made by PR #109, which merged first — this entry has
  since been rebased onto that merged state, so both PR #109's entry and the
  already-corrected PR #108 entry appear below, unmodified).
- **What changed / residue fixed:** This session ran a static/offline-only
  validation pass over the `task-003-manual-validation-checklist.md` items
  that do not require a valid Shopify Admin API token. This session was
  originally run in parallel with the OAuth/Fable attempt, which is now
  recorded in merged PR #109 (entry below) as blocked before execution — no
  Fable-equivalent browser-automation tool and no Shopify Dev Dashboard
  credentials were available to that session. This session did not touch
  that attempt. Confirmed by direct repo/source inspection: **VAL-A4** —
  Task 003 (PR #101, merge commit
  `e27f10e55f3504d1a9b8871a207b3d9762a3c783`) introduced no XML file, menu,
  action, wizard, controller, route, cron, or server/scheduled action of any
  kind; the module's only XML file
  (`security/shopify_connector_security.xml`) predates Task 003 and defines
  only `ir.module.category`/`res.groups.privilege`/`res.groups` records; no
  `controllers/` or `wizards/` directory exists anywhere in the addon; a
  repo-wide grep for `ir.cron`, `ir.actions.server`, `ir.ui.menu`, and
  `ir.actions.act_window` returns zero hits. This is a **static repo check**,
  not an `ir.model.data`/live-registry DB inspection — no live Odoo instance
  was available this session. **VAL-C3** — confirmed exactly **2** `sudo()`
  call sites in production code: `_get_access_token`
  (`shopify_connector_store_credential.py:158`) and `_system_append`
  (`shopify_connector_job_log.py:85`) — matching the governance-documented
  expectation; a static source count, not a live-installed-module
  re-verification. **VAL-D1** — confirmed the `TEST_CONNECTION_QUERY` GraphQL
  string (`shopify_connector_store.py:15-18`) is exactly `query
  ConnectorTestConnection { shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } } }`, and a repo-wide grep
  for the `mutation` GraphQL keyword found no mutation operation string
  anywhere in the module (only a docstring/comment noting its absence, and
  the pre-existing regression test that asserts this by regex). Static
  read-only-query evidence only — no live Shopify Admin store was inspected.
  **VAL-D2** — confirmed `action_test_connection()` and its helpers
  (`_get_access_token`, `_system_append`,
  `ShopifyConnectorApiClient.execute`) write only to
  `shopify.connector.store`, `shopify.connector.store.credential`
  (`credential_state` field only), `shopify.connector.job`, and
  `shopify.connector.job.log` — no product/customer/order/inventory/stock/
  accounting/sale/purchase model reference anywhere in the code path. Static
  code-path evidence only — no live Odoo database was inspected. **VAL-C1
  (server-log half)** — this container/session has no live Odoo runtime and
  no server log files anywhere on the filesystem (confirmed by filesystem
  search); the dummy token
  `shpat_INVALID_INVALID_INVALID0000000000000000` could not be grepped
  against any log because none exist here. Recorded as **not testable in
  this session — logs unavailable**, not pass/fail. **VAL-G1–G4** — left
  **not tested**; no empirical API behavior was observed or invented this
  session.
- **Items deferred:** Everything requiring a live Odoo instance, a live
  Shopify connection, or real server logs remains deferred to a future live
  session: VAL-A1 (fresh install re-run), VAL-A4's DB/`ir.model.data`-level
  half, VAL-B2/B4–B7, VAL-C1's server-log half, VAL-D1/D2's live-observation
  halves, VAL-E1, VAL-G1–G4. The separate manual-OAuth-token-acquisition
  experiment, now recorded in merged PR #109 (entry below) as blocked before
  execution, is untouched by this session.
- **Recommended decision:** None — this session makes no recommendation and
  reaches no go/no-go conclusion; it only adds static evidence for items that
  were previously entirely untested.
- **Risks:** None newly identified. Static evidence narrows, but does not
  close, the remaining live-validation gap; a future live session must still
  confirm the DB/registry-level half of VAL-A4, the live-observation halves
  of VAL-D1/D2, and VAL-C1's server-log half before Task 003 validation can
  be considered complete.
- **What remains blocked:** Task 003 manual validation **remains
  incomplete**. Task 004 **remains blocked**. VAL-B2 remains blocked/not
  attempted. The OAuth/token-acquisition experiment remains not executed —
  PR #109 (merged, entry below) already records that attempt as blocked
  before execution; this session does not duplicate or second-guess that
  record. This PR (#110) does not unblock Task 004.
- **Learning feedback loop:** New issues / repeated patterns: none. Rules/
  checklists updated: none (checklist wording unchanged this session).
  Rejected approaches: none. Technical debt: none added; `TD-001` unchanged.
  Architecture concerns: none new. Tests or review gates needed: a future
  live session must still execute VAL-A1 (fresh re-run), VAL-A4 (DB/registry
  half), VAL-B2/B4–B7, VAL-C1 (server-log half), VAL-D1/D2 (live-observation
  halves), VAL-E1, VAL-G1–G4. Should future prompts change? Yes — a future
  static/offline continuation should note this session confirmed no live
  Odoo runtime or log files exist in the current execution environment, so
  VAL-C1's server-log half and any DB/registry-level check will require a
  session with actual live-environment access, not just repo/source
  inspection.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new) · repeated-issue escalation applied (n/a) — all YES.
- **Next recommended session:** ChatGPT reviews this static/offline sweep
  alongside PR #109's (merged) OAuth-experiment-blocked findings; a future
  live session (with an actual Odoo 19 instance, PostgreSQL, live Shopify
  dev store, and server-log access) is still required to close VAL-A1,
  VAL-A4's DB half, VAL-B2, VAL-B4–B7, VAL-C1's server-log half, VAL-D1/D2's
  live halves, VAL-E1, and VAL-G1–G4 before Task 003 can be marked complete.
- **Stop condition:** stopped at the scoped boundary — docs-only static/
  offline validation sweep; no code, test, manifest, security, XML, or CSV
  file touched; Task 003 not marked complete; Task 004 not unblocked; no
  OAuth work performed or claimed; no secrets used.

### Task 003 Validation / Task 004 Prep — Continuation Session, Blocked at Empirical OAuth Experiment (2026-07-07)

- **Branch / PR:** `claude/task-003-validation-task-004-prep-fbq3qd`, branched
  from `Shopify-connector` at its current tip (PR #108's merge commit
  `76cd74e7cf585e1925c3ac280bd6ca97c55df7ab`) → draft PR into
  `Shopify-connector` (this session's PR). Docs-only session — no code, test,
  manifest, security, or addon file changed. **No Task 004 work of any kind
  in this session.**
- **Files changed:** `docs/01-research/research-handoff.md` (this entry, plus
  a correction to the PR #108 entry's stale "draft/not merged" wording, fixed
  below it), `docs/05-qa/task-003-validation-results.md` (continuation-session
  section recording the blocked experiment attempt),
  `docs/04-decisions/shopify-token-acquisition-decision-brief.md`
  (continuation-session note recording the same blocker against the
  brief's own §4–5 recommended next step).
- **Session objective (per the assigning prompt):** this session was scoped
  as the "future, separately-scoped Task-003-continuation session" that PR
  #108's decision brief (§5) called for — its sole deliverable was to run the
  manual OAuth authorization-code-grant experiment described in the decision
  brief §4, using a browser-automation tool referred to as "Fable" for
  Shopify Dev Dashboard / Shopify Admin interaction, and generic tooling
  outside the Odoo codebase for the token exchange, then (only if a
  compatible token was obtained) re-attempt VAL-B2 in Odoo.
- **What was tested / attempted:**
  1. **Phase 0 (repo state check) — completed.** Confirmed `Shopify-connector`
     HEAD is PR #108's merge commit `76cd74e7cf585e1925c3ac280bd6ca97c55df7ab`
     (verified via `git merge-base --is-ancestor`); confirmed `main` is
     untouched (still at the pre-Shopify-connector-project commit `a5d4543`,
     no Shopify-related history); read all files listed in the assigning
     prompt's Phase 0 step 4 (this handoff, the token-acquisition research
     doc, the token-acquisition options doc, the decision brief, the Task 003
     checklist and results docs, the master blueprint open-questions doc's
     MBQ-05 row); found and corrected the stale PR #108 "draft/not merged"
     wording noted above.
  2. **Phase 1 (plan the empirical token experiment) — completed as a plan
     only.** The store (`mqiu21-yz.myshopify.com`), app surface
     (Dev-Dashboard-created custom app), flow (OAuth authorization-code
     grant, offline non-expiring token, no client-credentials fallback as
     the primary path), and explicit success/failure criteria from the
     assigning prompt were reviewed and found consistent with the decision
     brief's own §4 plan — no changes needed.
  3. **Phase 2 (use Fable to configure/inspect Shopify) — blocked before any
     Shopify interaction.** This execution session has **no "Fable" tool,
     connector, or MCP server of any kind available** — checked via
     `ToolSearch` (queries for "fable browser shopify" and "browser computer
     use playwright screenshot navigate" returned no matching tool),
     `ListConnectors` (only Gmail, Google Calendar, and Google Drive are
     installed for this account, none enabled in this chat, none relevant to
     Shopify/browser automation), and `ListPlugins`/`ListSkills` (both
     returned zero results for "fable"/"browser"/"shopify" keywords). This
     session also has **no Shopify Dev Dashboard credentials of any kind**
     — checked the process environment for any `SHOPIFY_*`/`FABLE_*`/
     `CLIENT_ID`/`CLIENT_SECRET`/`OAUTH_*`-shaped variable; none found. There
     is therefore no way for this session to open the Shopify Dev Dashboard,
     inspect or configure the app used in the prior blocked session, register
     a redirect URI, or begin an OAuth authorization request.
  4. **Phases 3–5 (OAuth exchange, direct Shopify token validation, Odoo
     VAL-B2 re-attempt) — not attempted.** Each is explicitly gated on Phase
     2 succeeding; since Phase 2 could not start, none of these were run.
     No Odoo instance is reachable from this execution environment either
     (confirmed no `odoo` process/binary present), which would have blocked
     Phase 5 independently even had Phases 2–4 succeeded.
- **Result:** **Case 4 (per the assigning prompt's Phase 6) — blocked by
  missing Fable/Shopify access, not a platform or OAuth failure.** No OAuth
  attempt was made; no claim is made about whether Shopify's OAuth
  authorization-code-grant flow does or does not work for a
  Dev-Dashboard-created custom app. That question, raised in PR #108's
  research and decision brief, remains exactly as open as it was before this
  session.
- **Remaining blockers (exact, per the assigning prompt's instruction to
  report exactly what is missing):**
  1. No Fable (or equivalent authenticated browser-automation) tool/connector
     is enabled for this Claude Code execution session. This must be
     provisioned (e.g. via this session's connector settings, or by running
     the experiment from a session that has such a tool available) before
     the Shopify Dev Dashboard / Shopify Admin steps in decision-brief §4 can
     be attempted.
  2. No Shopify Dev Dashboard app Client ID / Client Secret, and no Shopify
     Partner/store-owner login/2FA path, is available to this session. These
     are secrets and must **not** be pasted into chat, docs, or environment
     dumps per this project's secret-handling rules — they must be supplied
     through a secure, session-scoped channel (e.g. the human operator
     completing the Shopify consent/login step interactively in an actual
     browser session, with only the resulting redacted outcome reported
     back) in a session that has both Fable/browser access and that secure
     channel available.
- **Task 003 status:** **Still incomplete — unchanged from the PR #107/#108
  state.** VAL-B2, VAL-E1, VAL-A4, VAL-B4–B7, VAL-C1's server-log-grep half,
  VAL-C3, VAL-D1–D2, and VAL-G1–G4 remain blocked or not tested, for exactly
  the same reason recorded in PR #107: no valid Shopify Admin API access
  token. This session neither improves nor worsens that state.
- **Task 004 status:** **Still blocked — not ready for ChatGPT review to
  unblock.** No new evidence was gathered this session (the empirical
  experiment recommended in the PR #108 decision brief could not be run), so
  there is no basis to change the brief's existing "Task 004 remains blocked"
  conclusion (§9). This is explicitly **not** a claim that Task 004 is
  "unblocked automatically" — it is not.
- **No code changed — confirmed.** This session touched only the docs files
  listed above; `addons/`, and every `*.py`/`*.xml`/`*.csv`/manifest/
  security/test file, are unchanged.
- **No secret exposed — confirmed.** No Shopify token, client secret,
  authorization code, or credential of any kind was obtained, handled, or
  recorded by this session, because Phase 2 never started.
- **No Shopify or Odoo side effects — confirmed (vacuously).** No Shopify or
  Odoo interaction of any kind occurred this session.
- **Learning feedback loop:** New issues / repeated patterns: **this
  project's session-assignment process should confirm tool/connector
  availability (e.g. "is a Fable-equivalent browser tool enabled for this
  session") before scoping a session around it**, the same way it already
  confirms branch/PR state — this is the second consecutive Shopify
  token-acquisition session blocked short of its main deliverable (the first
  by an unavailable admin-UI token path, this one by an unavailable
  browser-automation tool and unavailable Shopify credentials). Rules/
  checklists updated: none (no file in `/docs/05-qa` was identified as
  needing a new rule from this specific blocker — it is an environment/
  tooling-provisioning gap, not a process defect). Rejected approaches:
  none — no approach was attempted or rejected; the session stopped before
  reaching a point where an approach could be tried. Technical debt: none
  added. Architecture concerns: none new — the decision-critical open
  question already tracked in the decision brief and MBQ-05 is unchanged.
  Tests or review gates needed: the same empirical OAuth-exchange experiment
  recommended in the decision brief §4–5, now additionally conditioned on a
  future session actually having Fable/browser access and a secure channel
  for Shopify Dev Dashboard credentials. Should future prompts change?
  **Yes** — see "Next recommended session" below.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none — none occurred) ·
  technical debt logged (none) · repeated-issue escalation applied (yes —
  flagged above as a second consecutive blocked-before-deliverable session)
  — all YES.
- **Next recommended session:** ChatGPT reviews this entry and confirms
  whether to (a) provision a Fable-equivalent browser-automation tool and a
  secure Shopify-credential channel for a future Claude Code session and
  re-run this same scoped experiment, (b) have a human operator run the
  manual OAuth authorization-code-grant exchange themselves (following the
  decision brief §4's exact steps) and report back only the redacted
  result for Claude to record, or (c) skip the empirical step entirely and
  commit directly to Option A or Option B per the decision brief §10's
  standing offer. Whichever is chosen, the next session's prompt should
  explicitly confirm tool/credential availability in Phase 0 before
  attempting Phase 2.
- **Stop condition:** stopped at the scoped boundary — blocked at Phase 2
  (Fable/Shopify access) per the assigning prompt's own explicit instruction
  not to proceed, guess, or continue with assumptions when such access is
  missing; no code, test, manifest, or security file touched; Task 003 not
  marked complete; Task 004 not unblocked; a draft, unmerged PR opened
  recording this blocker for ChatGPT review.

### Shopify Token-Acquisition Research — compact handoff (2026-07-07)

- **Branch / PR:** `claude/shopify-token-acquisition-research-lpi7jt` →
  **PR #108**, merged into `Shopify-connector` (merge commit
  `76cd74e7cf585e1925c3ac280bd6ca97c55df7ab`). **Correction (added during the
  2026-07-07 continuation session below): this entry originally described PR
  #108 as a draft, not-merged PR; that wording was stale — PR #108 has since
  merged.** Docs-only session — no code, test, manifest, or security-file
  change. **No Task 004 work of any kind in this session.**
- **Files changed:** `docs/01-research/shopify-token-acquisition-research.md`
  (new), `docs/03-architecture/shopify-token-acquisition-options.md` (new),
  `docs/04-decisions/shopify-token-acquisition-decision-brief.md` (new),
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** Independently re-verified, live on
  2026-07-07 (nine topic-scoped research passes plus an adversarial re-fetch
  verification pass per topic, all against `shopify.dev`/`help.shopify.com`/
  `changelog.shopify.com`), the prior day's MBQ-05 findings recorded in
  `../03-architecture/credential-connection-api-client-planning.md`
  (2026-07-06). **Key finding, confirmed and sharpened:** admin-created custom
  apps can no longer be newly created as of **January 1, 2026** (exact date now
  cited, from Shopify's product changelog); existing legacy apps keep working
  but cannot be rotated except by uninstall/reinstall. New custom apps go
  through the Dev Dashboard or Shopify CLI; Shopify's own tutorial for
  "building apps for your own store" shows only the 24-hour client-credentials
  grant, but the client-credentials mechanism is explicitly restricted to
  same-organization/own-store apps — "public or custom apps must use token
  exchange or authorization code grant" instead, and that OAuth flow, by
  default, still yields a **non-expiring** offline token compatible with the
  connector's shipped `token_variant='offline_custom_app'` shape. **No official
  worked example confirms this exact combination** (Dev-Dashboard custom app +
  authorization code grant) — this is the single decision-critical open
  question this session could not resolve from documentation alone. Custom
  apps and merchant-created apps are also confirmed explicitly exempt from
  Shopify's new (Dec 2025) mandatory expiring-offline-token model, so the
  connector's non-expiring single-secret model remains fully supported,
  not deprecated.
- **Items deferred:** the one open question above (whether the manual
  authorization-code-grant exchange actually works against a Dev-Dashboard
  custom app) requires an empirical attempt in a future session — not resolved
  by documentation research alone. VAL-B2 and Task 003's other
  blocked/not-tested items are unchanged by this session.
- **Recommended decision:** Option C (dual path) — keep the shipped
  offline/custom-app token storage as-is for MVP; treat "how does a new
  merchant mint a compatible token today" as a research-validation step (attempt
  the manual OAuth exchange, outside the Odoo codebase, against the same
  blocked development store) before committing to build a full OAuth
  implementation (Option B) or accepting the new-merchant onboarding gap
  indefinitely (Option A alone). Full detail:
  `../04-decisions/shopify-token-acquisition-decision-brief.md`.
- **Risks:** if the manual OAuth-exchange experiment fails, this signals real
  new-merchant-onboarding-architecture work (Option B, or a client-credentials
  schema extension) is required before MVP can claim self-serve setup — a
  larger scope than currently assumed. Two research-only nuances also flagged
  for future attention: the protected-customer-data table has a **third**
  column ("Admin created custom app" = Level 2 "Varies by plan," not
  unconditionally "Always available" the way a general custom app is); and the
  historical "reveal token once" admin-UI behavior remains unconfirmed on any
  official page.
- **What remains blocked:** Task 003 manual validation remains incomplete
  (VAL-B2 and others unchanged from the prior entry below). Task 004 remains
  blocked. MBQ-05 remains open, not resolved — this session's findings feed
  ChatGPT's review, they do not close it.
- **Learning feedback loop:** New issues / repeated patterns: none beyond the
  already-tracked MBQ-05 gap. Rules/checklists updated: none. Rejected
  approaches: none. Technical debt: none added. Architecture concerns: the
  decision-critical open question in this entry should be resolved empirically
  before Task 004 planning begins. Tests or review gates needed: the manual
  OAuth-exchange validation step recommended in the decision brief. Should
  future prompts change? Yes — a future Task-003-continuation session should
  explicitly scope the manual OAuth-exchange experiment as its sole
  deliverable, docs/QA-only, no code.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt logged
  (none) · repeated-issue escalation applied (n/a) — all YES.
- **Next recommended session:** ChatGPT reviews this brief and the two
  companion documents; if accepted, a narrow docs/QA-only session runs the
  manual OAuth-exchange experiment described in the decision brief §4–5 and
  records the result. **No code was changed in this session — confirmed.**
- **Stop condition:** stopped at the scoped boundary (research + decision-prep
  documentation only); no code, test, manifest, or security file touched; Task
  003 not marked complete; Task 004 not unblocked.

### Task 003 Manual Validation — Live Partial Results Recorded (2026-07-07)

- **Branch / PR:** `claude/task-003-validation-docs-7tl074` → **PR #107**,
  a **draft** PR into `Shopify-connector`; not merged, not marked ready.
  Docs-only session — no code, test, or module-behavior change. **No Task
  004 work of any kind in this session.**
- **Files changed:** `docs/05-qa/task-003-validation-results.md` (live
  partial-validation results recorded, with a new validation summary table
  and a condensed-evidence appendix), `docs/05-qa/task-003-manual-validation-checklist.md`
  (VAL-C1 wording revised to distinguish intended credential storage from
  unexpected leakage — no step, scope, or expectation changed beyond that
  clarification), `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** A live Odoo shell session was run
  (outside this repository) against Odoo 19.0, database/branch prompt
  `adamsmen-shopify-connector-34582665 [dev/19.0]`, with
  `shopify_connector_core` installed at `19.0.1.2.3` (post-green-gate
  hotfix), targeting the Shopify development store
  `mqiu21-yz.myshopify.com` (API version `2026-07`). This session
  transcribed that live session's results into
  `task-003-validation-results.md` per
  `task-003-manual-validation-checklist.md`. **Task 003 manual validation
  is partially completed, not fully complete.** Every testable item that
  did not require a genuine, valid Shopify Admin API access token
  **passed**: VAL-A1 (installed-module / registry-load observation — the
  session confirmed `shopify_connector_core` installed at `19.0.1.2.3`
  with the registry loaded and no traceback; it did **not** re-execute a
  fresh clean install/upgrade command), VAL-A2 (model registry — including
  confirming no database table exists for the abstract
  `shopify.connector.api.client` model), VAL-A3 (exactly 3 `job_type`
  values), VAL-B1 (invalid-token failure path — correct `error_class`,
  reason, and `credential_state` flip), VAL-B3 (repeat-run idempotency —
  no collision, a fresh job row created), VAL-C1's **DB/ORM scan half**
  (token redaction — **zero unexpected leaks across the ORM/
  database-visible surfaces scanned** once the intentional
  `store.credential.access_token` storage field is correctly excluded;
  the Odoo **server log grep half of VAL-C1 was not tested** this
  session, so VAL-C1 overall is **PARTIAL**, not fully passed), VAL-C2
  (ACL — direct `job.log` create by an Operator-group user correctly
  denied with `AccessError`), VAL-E2
  (fail-path row accounting — two independent fail-path jobs each show
  exactly 1 job row + 2 job.log rows), and VAL-F1 (confirms `TD-001` is
  **still open** — a second `core_readiness_check` job for the same store
  still collides on `shopify_connector_job_store_idempotency_key_uniq`).
  **VAL-B2 (the valid-token positive-connection test) is recorded as
  BLOCKED, not passed and not failed** — no real Shopify Admin API access
  token was obtainable from the Dev Dashboard app used for this session;
  the Dev Dashboard did not expose the older admin-created custom-app
  Admin API token issuance path the connector currently expects (per Task
  002's `token_variant='offline_custom_app'`). Everything that depends on
  a successful connection (VAL-E1 pass-path row accounting, and the
  B-series cross-checks VAL-B4/B5/B6/B7) is therefore also BLOCKED or not
  tested, not failed. VAL-A4, VAL-C3, VAL-D1, VAL-D2, and VAL-G1–G4 were
  **not tested** this session (not exercised in the transcribed shell
  session). **No encryption claim is made anywhere in this update** —
  `access_token` remains stored in plain text on
  `shopify.connector.store.credential`, protected only by Odoo ACLs; this
  is an explicit, documented residual, not a defect introduced or
  resolved by this session.
- **Items deferred:** VAL-B2 and everything depending on it remain blocked
  pending a decision on token acquisition (see next bullet). VAL-A4,
  VAL-C3, VAL-D1, VAL-D2, and VAL-G1–G4 remain not tested and must be
  executed in a future live session before Task 003 validation can be
  called complete. VAL-C1's **Odoo server log grep** was not performed
  this session and remains not tested — only the DB/ORM scan half of
  VAL-C1 passed. A fresh clean install/upgrade re-run of VAL-A1 was also
  not re-executed this session — only an installed-module / registry-load
  observation was made. `TD-001` remains open, untouched, and unresolved
  by this session — no fix proposed or attempted, per this session's
  docs-only, no-code scope.
- **Open follow-up (routed to ChatGPT):** Decide whether the MVP continues
  with **offline/custom-app Admin API token only** (accepting that setup
  requires a customer/partner to create a custom app via the legacy
  Admin-created path) or whether **OAuth-based token acquisition** (or
  another Dev-Dashboard/CLI-app-compatible token flow) must be designed
  and introduced **before** customer-facing setup can ship — the current
  Shopify Dev Dashboard app path used in this validation session did not
  offer a way to obtain a token compatible with the connector's current
  `token_variant='offline_custom_app'` assumption, which blocked VAL-B2
  and is a genuine open product/architecture question, not merely a
  test-environment inconvenience.
- **Learning feedback loop:** New issues / repeated patterns: none beyond
  the already-logged `TD-001` (re-confirmed open, not newly discovered).
  Rules/checklists updated: `task-003-manual-validation-checklist.md`'s
  VAL-C1 wording revised only to distinguish intended credential storage
  (`store.credential.access_token`) from unexpected leakage — no scope,
  step, or expectation changed beyond that clarification. Rejected
  approaches: none. Technical debt: none added; `TD-001` unchanged (still
  open). Architecture concerns: the token-acquisition open follow-up
  above is a genuine gap that should be evaluated before Task 004 or any
  customer-facing setup work. Tests or review gates needed: none in this
  docs-only session; a future live session must complete VAL-A4, VAL-B2
  (or formally accept the offline/custom-app-only path and re-scope
  VAL-B2), VAL-B4–B7, VAL-C3, VAL-D1–D2, and VAL-G1–G4 before Task 003
  validation is complete. Should future prompts change? Yes — future
  validation sessions should confirm token-acquisition tooling
  availability as a **precondition** (alongside the existing
  preconditions in `task-003-manual-validation-checklist.md`), since its
  absence blocked a core checklist item in this session.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new, `TD-001` unchanged) · repeated-issue escalation
  applied (n/a, no repeat this session) — all YES.
- **Next recommended session:** ChatGPT reviews and accepts (or requests
  revisions to) this validation documentation. **Task 004 remains
  blocked** until that review/acceptance happens **and** the open
  token-acquisition follow-up above is resolved and the remaining
  not-tested/blocked checklist items (VAL-A4, VAL-B2, VAL-B4–B7, VAL-C3,
  VAL-D1–D2, VAL-G1–G4) are executed in a future live validation session.

### Odoo 19 Green-Gate Hotfix — compact handoff (2026-07-07)

- **Branch / PR:** current session branch (`claude/odoo-shopify-test-failures-9scudd`);
  PR → opened as **draft** into `Shopify-connector`, not merged, not marked
  ready. **No Task 004 work of any kind in this session.**
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_job_log.py`,
  `addons/shopify_connector_core/tests/test_credential_access.py`,
  `addons/shopify_connector_core/tests/test_credential_service.py`,
  `addons/shopify_connector_core/tests/test_job_log_system_append.py`,
  `addons/shopify_connector_core/tests/test_test_connection.py`,
  `addons/shopify_connector_core/__manifest__.py` (version bump only),
  `docs/05-qa/odoo-19-green-gate-failures.md` (new),
  `docs/05-qa/task-003-validation-results.md`,
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** PR #105 (merge commit `f915211`) fixed
  the `job.idempotency_key` NOT NULL issue and three test-expectation
  defects, and merged into `Shopify-connector`. Live validation was
  re-run afterward and reached all 39 tests, then reported
  `1 failed, 4 error(s) of 39 tests` (halted again after the
  max-failed-tests threshold). Full detail in the new
  `docs/05-qa/odoo-19-green-gate-failures.md`; in summary, three distinct
  issues surfaced: **(a) a real Odoo 19 production runtime issue** —
  `shopify.connector.job.log.store_id` was declared
  `related='job_id.store_id', store=True, required=True`; identical
  ordering defect class to the `idempotency_key` issue fixed in PR #105
  (Odoo 19 populates stored-related fields *after* the initial row
  INSERT), so every `_system_append()` call failed with a `store_id` NOT
  NULL violation, surfacing as four errors across
  `test_job_log_system_append.test_non_admin_indirect_append_succeeds_but_direct_create_denied`,
  `test_job_log_system_append.test_redaction_of_message_technical_detail_payload_snapshot`,
  `test_job_log_system_append.test_system_append_creates_one_row`, and
  `test_test_connection.test_auth_failure_sets_credential_invalid`;
  **(b) a residual test-expectation defect** —
  `test_credential_access.test_non_admin_roles_denied_all_crud_and_search`'s
  PR #105-era `fields_get()`-disjoint assertion still failed, because
  `fields_get()` is a schema call not gated by `ir.model.access` CRUD
  rows in Odoo (only by each field's own `groups=` attribute) — not a
  security regression, since the test's five actual-operation
  `AccessError` assertions already prove the access-denial property; and
  **(c) SQL log-hygiene noise** — the already-passing intentional
  duplicate-credential-row test still caused Odoo's `odoo.sql_db` logger
  to emit an avoidable `ERROR`-level line for the expected unique-
  constraint violation. **Fix applied:** removed `required=True` from
  `job.log.store_id` (kept `related`, `store=True`, `index=True`,
  `readonly=True`; `_system_append()` itself untouched, no new `sudo()`,
  no ACL change); added `row.store_id == job.store_id` /
  `job.log` store_id regression assertions to the `_system_append()`-
  exercising tests in `test_job_log_system_append.py` and to the
  success/failure paths in `test_test_connection.py`. Removed the
  `fields_get()`-disjoint assertion from
  `test_non_admin_roles_denied_all_crud_and_search` entirely (the five
  real-operation `AccessError` assertions in the same test are
  unaffected); reviewed every other `fields_get()` call site in the
  allowed test files and added justifying comments to the three that
  remain (`test_field_groups_independent_of_model_acl`'s field-`groups=`
  check, and two schema-enumeration-for-value-scanning uses in
  `test_credential_service.py`/`test_test_connection.py`) — none of them
  is used as a model-ACL security oracle. Added
  `@mute_logger('odoo.sql_db')` (from `odoo.tools`) to the two tests that
  intentionally trigger a raw database unique-constraint violation
  (`test_credential_service.test_duplicate_credential_row_for_same_store_raises`
  and `test_test_connection.test_core_readiness_check_untouched_still_collides`)
  — both already ran under `self.env.cr.savepoint()` from prior hotfixes;
  this only quiets the expected-failure log line, no assertion changed,
  TD-001 remains open and untouched. Manifest version bumped
  `19.0.1.2.2` → `19.0.1.2.3` (production model behavior changed). No
  credential-service production behavior changed; no ACL/security XML
  changed; no Shopify API/behavior changed; no Task 004 work.
- **Items deferred:** No Odoo runtime/PostgreSQL exists in this
  repository, so live test execution could not be re-run here —
  `python3 -m py_compile` passed on all six changed Python files; repo
  grep confirms no test skip marker was added, `def test_` counts are
  unchanged in all four changed test files (4 / 11 / 4 / 9), no CRUD/
  security assertion was removed without an equal-or-stronger
  replacement, no ACL/security XML/CSV or API-client file changed, no
  product/customer/order/inventory/fulfillment logic added, exactly two
  sanctioned `sudo()` sites remain, and no stored computed/related field
  in `shopify_connector_core` remains `required=True`. `mute_logger`'s
  own availability in this Odoo 19 build could not be confirmed without
  a runtime — if it is unavailable, the live run will surface an
  `ImportError` on the two files it was added to, and the tester must
  report that back. **This PR must remain draft. Do not merge until a
  live Odoo 19 install/test run against this exact code path is
  green** — the tester must re-run the four affected test classes first
  (`test_credential_access`, `test_credential_service`,
  `test_job_log_system_append`, `test_test_connection`), then the full
  `shopify_connector_core` suite, record results in
  `task-003-validation-results.md`, and only then resume
  `task-003-manual-validation-checklist.md` from VAL-A1 — Task 003 live
  validation remains blocked until that clean, fully green run.
- **Learning feedback loop:** New issues / repeated patterns: this is the
  second stored-related/computed field found `required=True` under Odoo
  19's insert-then-populate ordering (`idempotency_key` in PR #105,
  `job.log.store_id` here) — confirms the flagged rule from the PR #105
  handoff entry (any new `compute=...`/`related=...` `store=True` field
  should default to *not* `required=True` unless it also has a
  non-dependent default) should be escalated from an observation to a
  binding review checklist item for this module going forward, since it
  has now recurred once. Separately, the `fields_get()`-as-security-proxy
  pattern recurred a second time even after the PR #105 hotfix attempted
  to correct it (narrowing the assertion rather than removing the
  premise) — flag for a future rule: `fields_get()` should never be
  asserted against for model-ACL-denial proof, only for field-level
  `groups=` proof or for schema/value enumeration, and this should be a
  named anti-pattern in any future test-writing guidance for this
  module. Rules/checklists updated: none this session (routing both
  observations to ChatGPT rather than unilaterally amending a gate
  checklist). Rejected approaches: none. Technical debt: none added;
  TD-001 unchanged. Architecture concerns: none — this is a scoped
  runtime/test-compatibility fix, no design change. Tests or review
  gates needed: live re-run of the four affected test classes plus the
  full `shopify_connector_core` suite before this PR can be marked
  ready; confirm `mute_logger` import succeeds live. Should future
  prompts change? Yes — consider adding an explicit pre-commit/review
  checklist item for "no new `store=True` field is `required=True`
  unless independently defaulted" and "no test asserts `fields_get()`
  content as proof of model-ACL denial," given both defect classes have
  now recurred.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new, TD-001 unchanged) · repeated-issue escalation applied
  (both recurrences flagged above, routed to ChatGPT) — all YES.
- **Next recommended session:** Live tester re-runs the Odoo 19
  install/test-execution command for `shopify_connector_core` after this
  PR is reviewed, confirms `1 failed, 4 error(s) of 39 tests` no longer
  occurs and the full suite is green, records results in
  `task-003-validation-results.md`, and only then resumes
  `task-003-manual-validation-checklist.md` from VAL-A1 onward. Only
  after that clean live run should ChatGPT consider marking this PR
  ready and merging it — no Task 004 work until Task 003 live validation
  passes and is signed off.

### Odoo 19 Runtime Test-Failure Hotfix — compact handoff (2026-07-07)

- **Branch / PR:** current session branch; PR → to be opened as draft into
  `Shopify-connector`, not yet merged.
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `addons/shopify_connector_core/tests/test_credential_access.py`,
  `addons/shopify_connector_core/tests/test_credential_service.py`,
  `addons/shopify_connector_core/tests/test_job_log_system_append.py`,
  `addons/shopify_connector_core/__manifest__.py` (version bump only),
  `docs/05-qa/odoo-19-runtime-test-failures.md` (new),
  `docs/05-qa/task-003-validation-results.md`,
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** PR #104 (merge commit `867074c`) fixed
  the `res.users.groups_id` → `group_ids` blocker and merged into
  `Shopify-connector`. Live validation was re-run afterward and progressed
  through registry load and all 36 test loads, then reported
  `2 failed, 3 error(s) of 36 tests` (Odoo halted after its max-failed-tests
  threshold, so additional failures beyond these five may still be hidden —
  `test_test_connection.py` was not confirmed reached). Full root-cause
  detail and classification is in the new
  `docs/05-qa/odoo-19-runtime-test-failures.md`; in summary, two distinct
  defect classes surfaced: **(a) a real Odoo 19 production runtime issue** —
  `shopify.connector.job.idempotency_key` was declared
  `compute=..., store=True, required=True`; in Odoo 19 a new record's
  stored-computed fields are evaluated *after* its initial row INSERT, so
  every `shopify.connector.job.create()` call inserted `NULL` into a
  `NOT NULL` column before `_compute_idempotency_key` ever ran, failing job
  creation for any caller (surfaced as errors in
  `test_job_log_system_append.test_non_admin_indirect_append_succeeds_but_direct_create_denied`
  and `test_redaction_of_message_technical_detail_payload_snapshot`); and
  **(b) three test-expectation defects**, none a security regression —
  `test_credential_access.test_non_admin_roles_denied_all_crud_and_search`
  asserted `fields_get()` returns exactly `{}` for a non-admin role, which
  is stricter than Odoo 19's actual behavior (it may return the model's
  schema without exposing any record data);
  `test_credential_service.test_duplicate_credential_row_for_same_store_raises`
  used the shared class-level store (isolation risk) and expected a Python
  `ValidationError` for what Odoo 19 raises as a raw database integrity
  error for `models.Constraint` violations, un-savepointed (transaction-
  poisoning risk); and
  `test_credential_service.test_empty_or_non_string_value_raises_without_echoing`
  contained a logically-impossible assertion
  (`assertNotIn('', str(exception))`, which can never pass since `''` is a
  substring of every string) for the `bad_value == ''` case, unrelated to
  Odoo 19 itself.
  **Fix applied:** removed `required=True` from `idempotency_key` (kept
  `compute`, `store=True`, `index=True`, `readonly=True`;
  `_compute_idempotency_key` and the `(store_id, idempotency_key)` unique
  constraint untouched — `store_id` is always required, so the computed key
  is always non-empty once the row exists, and the uniqueness guarantee is
  unchanged). `test_credential_access` now asserts `access_token` and every
  other credential business field (`store_id`, `token_variant`,
  `credential_state`) are absent from whatever `fields_get()` returns,
  accepting either an `AccessError` or a returned schema, while every CRUD/
  search `AccessError` assertion in the same test is unchanged.
  `test_duplicate_credential_row_for_same_store_raises` now creates its own
  fresh, test-local store and wraps the expected-to-fail second `create()`
  in `self.env.cr.savepoint()`, asserting a broad `Exception` — mirroring
  the pre-existing, unmodified `test_test_connection.test_core_readiness_check_untouched_still_collides`
  pattern already in this codebase for the identical class of job-model
  `models.Constraint` violation.
  `test_empty_or_non_string_value_raises_without_echoing` now asserts the
  exact generic message (`"A non-empty credential value is required."`,
  which `action_set_token`/`action_replace_token` already raised
  unmodified) via `assertEqual`, for both actions and all three bad values,
  which is strictly stronger than the old `assertNotIn` and not
  logically broken for `''`. `test_job_log_system_append._create_job()`
  now asserts `self.assertTrue(job.idempotency_key)` immediately after
  creation, guarding the production fix for every test that uses the
  helper. Manifest version bumped `19.0.1.2.1` → `19.0.1.2.2` (production
  model behavior changed). No credential-service or job-log
  **production** behavior was changed (only the job model's field
  definition); no ACL/security XML changed; no Shopify API/behavior
  changed; TD-001 (`core_readiness_check`'s target-less duplicate-collision
  exposure) remains open and untouched, as required; no Task 004 work.
- **Items deferred:** No Odoo runtime/PostgreSQL exists in this
  repository, so live test execution could not be re-run here —
  `python3 -m py_compile` passed on all five changed Python files; repo
  grep confirms no test skip marker was added, `def test_` counts are
  unchanged in all three test files (4 / 11 / 4), exactly one
  `assertRaises` type was changed (justified and mirrored against existing
  precedent, not removed), no new `.sudo()` site was added, and no other
  computed-stored-required field remains in `addons/shopify_connector_core/models/`.
  The tester must re-run, after this PR merges: the three affected test
  classes first (`test_credential_access`, `test_credential_service`,
  `test_job_log_system_append`), then the full `shopify_connector_core`
  suite (watching specifically for any new failure in
  `test_test_connection.py`, which the previous halted run may not have
  reached), record results in `task-003-validation-results.md`, and only
  then resume `task-003-manual-validation-checklist.md` from VAL-A1 — Task
  003 live validation remains blocked until that clean run.
- **Learning feedback loop:** New issues / repeated patterns: this is the
  third Odoo-19-compatibility-class defect found only via an actual live
  install/test run this sprint (after `res.groups.category_id` and
  `res.users.groups_id`), and the first that is a genuine **production**
  runtime defect rather than a pure test/registry-load issue — a
  `compute=..., store=True, required=True` field is unsafe under Odoo 19's
  insert-then-compute ordering for any *new* stored-computed field in this
  module going forward; flag for a future rule: any new
  `compute=..., store=True` field should default to *not* `required=True`
  unless the field also has an explicit, non-compute-dependent default,
  and any existing one should be reviewed the same way. Separately, two of
  the three test-expectation defects (`fields_get() == {}`,
  `assertNotIn('', ...)`) were static-review-catchable — both are exactly
  the sort of "test asserts a Python-logic-impossible or overly strict
  condition" class flagged as a residual risk in earlier reviews.
  Rules/checklists updated: none this session (routing this observation to
  ChatGPT rather than unilaterally amending a gate checklist). Rejected
  approaches: none. Technical debt: none added; TD-001 unchanged.
  Architecture concerns: none — this is a scoped runtime/test-compatibility
  fix, no design change; idempotency semantics (compute inputs, unique
  constraint) are unchanged. Tests or review gates needed: re-run the three
  affected test classes plus the full `shopify_connector_core` suite live
  after merge. Should future prompts change? Possibly — consider requiring
  a documented Odoo-19 insert-vs-compute-ordering check for any new
  `compute=..., store=True` field, alongside the already-recommended
  Odoo-19-core-rename static audit.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new, TD-001 unchanged) · repeated-issue escalation applied
  (flagged above, routed to ChatGPT) — all YES.
- **Next recommended session:** Live tester re-runs the Odoo 19
  install/test-execution command for `shopify_connector_core` after this PR
  merges, confirms `2 failed, 3 error(s) of 36 tests` no longer occurs and
  no new failure appears (especially in `test_test_connection.py`), records
  results in `task-003-validation-results.md`, and only then resumes
  `task-003-manual-validation-checklist.md` from VAL-A1 onward. No Task 004
  session until that full checklist passes and ChatGPT reviews the
  results.
- **Stop condition:** Scoped runtime hotfix only; no Task 004 work, no
  setup wizard/UI/menu/action/wizard/controller/webhook/cron, no product/
  customer/order/inventory/fulfillment logic, no credential-service or
  job-log **production** behavior change, no ACL widening, no Shopify API
  behavior change, TD-001 untouched; no test skipped, deleted, or weakened;
  PR left as draft, not merged; live validation not started/resumed by
  this session.

---

### Odoo 19 Test-Compatibility Hotfix + Compatibility Audit — `res.users` `group_ids` — compact handoff (2026-07-07)

- **Branch / PR:** `claude/odoo19-test-groups-id-7v35ym`; PR #104, opened as
  draft into `Shopify-connector` in this session's first commit, still not
  merged. **F1 revision pushed as a second commit to this same branch/PR**,
  adding the module-wide compatibility audit below and updating the PR
  body — the first commit contained only the four-file `groups_id` →
  `group_ids` rename plus the two docs updates; this F1 revision expands
  the scope to a full module audit per follow-up instruction, without
  touching the original four-file test fix.
- **Files changed:** `addons/shopify_connector_core/tests/test_credential_access.py`,
  `addons/shopify_connector_core/tests/test_credential_service.py`,
  `addons/shopify_connector_core/tests/test_job_log_system_append.py`,
  `addons/shopify_connector_core/tests/test_test_connection.py`,
  `docs/05-qa/odoo-19-compatibility-audit.md` (new, this F1 revision),
  `docs/05-qa/task-003-validation-results.md`,
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** PR #103 (`claude/odoo19-install-blocker-fnm5ro`,
  merge commit `7361fbc`, fix commit `99fc84d`) merged into `Shopify-connector`
  and resolved the prior `res.groups.category_id` / `_sql_constraints`
  registry-load blocker. Live validation was re-run afterward and progressed
  past registry load into actual Odoo 19 test execution for
  `shopify_connector_core`, then errored out before completing, in four test
  classes: `test_credential_access.TestCredentialAccess`,
  `test_credential_service.TestCredentialService`,
  `test_job_log_system_append.TestJobLogSystemAppend`, and
  `test_test_connection.TestTestConnection`. Observed error:
  `ValueError: Invalid field 'groups_id' in 'res.users'`. Root cause: each of
  these four test classes shares an identical `_create_group_user(cls, label,
  group_xmlid)` classmethod helper that created a `res.users` record with
  `'groups_id': [(6, 0, [group.id])]` — Odoo 19 renamed this field to
  `group_ids` (the same class of Odoo-19 field-rename breakage already seen
  once this sprint on `res.groups.category_id` → `privilege_id`). This hotfix
  renames the dict key in all four occurrences (one per file, in the shared
  helper pattern) from `groups_id` to `group_ids`, preserving the exact `(6,
  0, [group.id])` command tuple, the same four group XML IDs
  (`group_shopify_connector_auditor/_operator/_reviewer/_admin`), the same
  test users, and the same test intent. No assertion, test method, or test
  class was changed, removed, skipped, or weakened. No production
  model/service/security/manifest/API-client/credential/job code was
  touched.
  **F1 audit addendum:** rather than stop at the four stack-trace files,
  this revision also audits the entire `addons/shopify_connector_core/`
  module for sibling Odoo 19 compatibility risks and records the result in
  the new `docs/05-qa/odoo-19-compatibility-audit.md`. Patterns searched
  module-wide: `groups_id`, `category_id`, `_sql_constraints`, old
  `res.groups` category assignment, direct `res.users.create` group
  assignment, test helpers creating users, other deprecated ORM patterns
  (`@api.one`/`@api.multi`/`@api.cr`/`osv.`/`orm.Model`/`fields.function`/
  `track_visibility`/`_inherits`), other `.sudo()` sites, and stale
  docs/comments referencing obsolete fields. Result: no sibling risk found
  anywhere else in the module — `category_id` appears exactly once,
  correctly on the `res.groups.privilege` record (not on any `res.groups`
  record); `_sql_constraints` is fully absent, with `models.Constraint`
  still in place on all six PR #103 conversions; the only
  `res.users.create` call sites in the whole module are the four now-fixed
  test helpers; `test_api_client.py` and `test_redaction.py` create no
  users and need no change; no other deprecated-API pattern exists; the
  module's two production `.sudo()` sites are unchanged and match the
  count the module's own guard tests assert; and no inline comment or docs
  file misleads a future reader into re-introducing the obsolete field
  names (the only doc references to `groups_id`/`category_id` are
  historical root-cause narrative for the two already-fixed failures).
- **Items deferred:** No Odoo runtime/PostgreSQL exists in this repository, so
  live test execution could not be re-run here — `python3 -m py_compile`
  passed cleanly on all four changed files, and repo-wide grep confirms zero
  remaining occurrences of `groups_id` anywhere in the repository (not just
  the tests directory) and `group_ids` present in exactly the four affected
  `_create_group_user` helpers. The tester must re-run the live Odoo 19
  install/test-execution command for `shopify_connector_core` after this PR
  merges, confirm `ValueError: Invalid field 'groups_id' in 'res.users'` no
  longer occurs, record any newly surfaced error separately (do not fix an
  unrelated new error in this same PR without ChatGPT authorization), and
  only then continue `task-003-manual-validation-checklist.md` from VAL-A1 —
  validation remains blocked pending both this PR and PR #103 being reflected
  in a clean live run.
- **Learning feedback loop:** New issues / repeated patterns: two Odoo 19
  breaking field renames surfaced back-to-back in the same module
  (`res.groups.category_id` → `privilege_id`, and now `res.users.groups_id` →
  `group_ids`), both only caught by an actual live install/test run rather
  than static review — flag for a future rule: before the next live
  validation attempt, do a static pass of every `res.users`/`res.groups`
  field reference (production **and** test code) against the Odoo 19 core
  rename list, rather than discovering renames one live-run failure at a
  time. Rules/checklists updated: none this session (routing this
  observation to ChatGPT rather than unilaterally amending a gate checklist).
  Rejected approaches: none. Technical debt: none added; TD-001 unchanged.
  Architecture concerns: none — this is a test-only compatibility fix, no
  design or production-behavior change. Tests or review gates needed: re-run
  the four affected test classes plus the full `shopify_connector_core` test
  suite live after merge. Should future prompts change? Possibly — consider
  requiring a documented Odoo-19-core-rename audit (covering both production
  and test code) before any "re-run live validation" step, given this is the
  second such rename found this sprint. **F1 addendum:** this revision acts
  on that exact flag — `docs/05-qa/odoo-19-compatibility-audit.md` is the
  first instance of that requested audit, run module-wide rather than
  file-by-file, and found no third sibling rename this sprint. Recommend to
  ChatGPT that a module-wide Odoo-19-rename static audit become a standing
  pre-live-validation step for this connector going forward (routed here as
  a recommendation, not unilaterally adopted as a gate).
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new, TD-001 unchanged) · repeated-issue escalation applied
  (flagged above, routed to ChatGPT) — all YES.
- **Next recommended session:** Live tester re-runs the Odoo 19
  install/test-execution command for `shopify_connector_core` after this PR
  merges, confirms the four previously-erroring test classes now execute
  without the `groups_id` `ValueError`, records results in
  `task-003-validation-results.md`, and only then resumes
  `task-003-manual-validation-checklist.md` from VAL-A1 onward. No Task 004
  session until that full checklist passes and ChatGPT reviews the results.
- **Stop condition:** Scoped test-compatibility hotfix only; no production
  model/service/security/manifest/API-client/credential/job/UI/controller
  code touched; no test skipped, deleted, renamed, or weakened; no Task 004
  work; PR left as draft, not merged; live validation not started/resumed by
  this session.

---

### Odoo 19 Install-Compatibility Hotfix — compact handoff (2026-07-07)

- **Branch / PR:** `claude/odoo19-install-blocker-fnm5ro`; PR → to be opened
  as draft into `Shopify-connector`, not yet merged.
- **Files changed:** `addons/shopify_connector_core/security/shopify_connector_security.xml`,
  `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/models/shopify_connector_store_credential.py`,
  `addons/shopify_connector_core/models/shopify_connector_store_settings.py`,
  `addons/shopify_connector_core/models/shopify_connector_location.py`,
  `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `addons/shopify_connector_core/__manifest__.py` (version bump only),
  `docs/05-qa/task-003-validation-results.md`,
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** Live validation of the Task 003 package
  (PR #101 merge commit `e27f10e5...`, PR #102 merge commit `f4437a80...`)
  started and failed immediately at VAL-A1 install/upgrade: Odoo 19 raised
  `ValueError: Invalid field 'category_id' in 'res.groups'` while loading
  `shopify_connector_security.xml`, a fatal registry-load failure. Root
  cause: Odoo 19 removed the direct `category_id` field from `res.groups`
  (confirmed against `github.com/odoo/odoo` at the `19.0` tag,
  `odoo/addons/base/models/res_groups.py` and the new
  `odoo/addons/base/models/res_groups_privilege.py`) — groups now carry a
  `privilege_id` Many2one to the new `res.groups.privilege` model, and
  `category_id` (Many2one to `ir.module.category`) moved onto that
  privilege record instead. This hotfix adds one
  `res.groups.privilege` record (`privilege_shopify_connector`, keeping
  the existing `module_category_shopify_connector` category) and points
  all four existing group XML IDs
  (`group_shopify_connector_auditor/_operator/_reviewer/_admin`) at it via
  `privilege_id`, preserving the exact implied-group hierarchy
  (Operator/Reviewer imply Auditor; Administrator implies both) and every
  ACL CSV row unchanged. Separately, Odoo 19 also deprecated
  `_sql_constraints`; this hotfix converts all five affected constraints
  (store `shop_domain` uniqueness, store-credential and store-settings
  one-per-store uniqueness, location `(store_id, shopify_location_gid)`
  uniqueness, and job's two constraints —
  `(store_id, idempotency_key)` and `(store_id, operation_scope_key)`) to
  the Odoo 19 `models.Constraint(sql, message)` class-attribute style,
  preserving the exact SQL intent and exact error messages verbatim.
  Manifest version bumped `19.0.1.2.0` → `19.0.1.2.1`. No compute logic,
  idempotency behavior, `operation_scope_key` behavior, API client,
  `_system_append`, or Shopify call behavior was touched.
  `core_readiness_check`'s duplicate-collision exposure (TD-001,
  `docs/05-qa/technical-debt-register.md`) remains open and untouched, as
  required — this hotfix does not fix it.
- **Items deferred:** No Odoo runtime/PostgreSQL exists in this repository,
  so the install/upgrade regression (VAL-A1) could not be re-executed here
  — `py_compile` passed on every changed Python file, the security XML
  parses cleanly, and source-level grep checks confirm no `category_id`
  remains on any `res.groups` record, `privilege_id` is used on all four,
  the `res.groups.privilege` record exists, no `_sql_constraints` remains
  in `addons/shopify_connector_core/models/`, and the ACL CSV is
  byte-for-byte unchanged — but the tester must re-run the actual Odoo 19
  install log after this PR merges and confirm no fatal error, then
  restart `task-003-manual-validation-checklist.md` from VAL-A1. No
  VAL-B credential/API steps should resume until VAL-A1–VAL-A4 pass.
- **Learning feedback loop:** New issues / repeated patterns: Odoo 19
  removed `res.groups.category_id` (now `privilege_id` →
  `res.groups.privilege.category_id`) and deprecated `_sql_constraints`
  (now `models.Constraint`); neither breaking change was caught before
  Task 003 merged because no live Odoo 19 install was run pre-merge — flag
  for a future rule: any module-install-affecting file (security XML,
  manifest, model constraints) should get at least one static Odoo-19-API
  compatibility pass even in a no-runtime environment. Rules/checklists
  updated: none this session (routing this observation to ChatGPT rather
  than unilaterally amending a gate checklist). Rejected approaches: none.
  Technical debt: none added; TD-001 unchanged. Architecture concerns:
  none — this is a pure Odoo-19-API compatibility fix, no design change.
  Tests or review gates needed: re-run VAL-A1–VAL-A4 live after merge
  before any VAL-B step. Should future prompts change? Possibly — consider
  requiring a documented Odoo 19 core-source citation check for any XML
  `res.groups`/model-constraint change, given this defect class.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new, TD-001 unchanged) · repeated-issue escalation applied
  (flagged above, routed to ChatGPT) — all YES.
- **Next recommended session:** Live tester re-runs Odoo 19 install/upgrade
  of `shopify_connector_core` after this PR merges, confirms VAL-A1–VAL-A4
  pass cleanly, records results in `task-003-validation-results.md`, then
  resumes VAL-B onward per `task-003-manual-validation-checklist.md`. No
  Task 004 session until that full checklist passes and ChatGPT reviews
  the results.
- **Stop condition:** Scoped hotfix only; no Task 004 work, no setup
  wizard/UI/menu/action/wizard/controller/webhook/cron, no product/
  customer/order/inventory/fulfillment logic, no API/credential/job
  behavior change, no ACL widening, TD-001 untouched; PR left as draft,
  not merged; live validation not started/resumed by this session.

---

### Task 003 Manual Validation Package — compact handoff (2026-07-07)

- **Branch / PR:** `claude/task-003-validation-checklist-bf63ox`; PR → to be
  opened as draft into `Shopify-connector`, not yet merged.
- **Files changed:** `docs/05-qa/task-003-manual-validation-checklist.md`
  (new), `docs/05-qa/task-003-validation-results.md` (new),
  `docs/01-research/research-handoff.md` (this entry).
- **What changed / residue fixed:** Created the mandatory manual-validation
  package for Task 003 (PR #101, merge commit
  `e27f10e55f3504d1a9b8871a207b3d9762a3c783`, merged into
  `Shopify-connector`). PR #101 itself states its 32 new tests were written
  and `py_compile`/`pyflakes`-validated but **not executed** — no Odoo
  runtime/PostgreSQL/CI exists in this repository — and that live manual
  validation against a development store was not performed. This session
  does not perform that validation; it produces the checklist
  (`task-003-manual-validation-checklist.md`, covering module
  install/upgrade, model registry + three `job_type` values, absence of any
  XML/menu/action/wizard/controller/cron, invalid-token and valid-token
  test-connection runs, the repeat-run idempotency/collision proof,
  identity-mismatch behavior, shop-state-failure behavior,
  `credential_state` flip-only-on-genuine-token-invalid-signal, token
  redaction across store/job/job.log/server logs,
  `job.log` direct-create-vs-`_system_append` ACL check, exact
  pass/fail job/log row accounting, the `core_readiness_check`/TD-001
  regression check, and empirical capture of the previously-open behavioral
  questions) and the blank results template
  (`task-003-validation-results.md`) a live tester must fill in.
- **Items deferred:** The actual live-runtime validation run itself (this
  session has no Odoo/PostgreSQL/Shopify-dev-store access) — that is the
  explicit next action once this package is reviewed and a live environment
  is available. `TD-001` (`core_readiness_check` idempotency collision)
  remains open and untouched, as required.
- **Learning feedback loop:** New issues / repeated patterns: none beyond
  the already-recorded Task 001A/PR #101 no-runtime caveat. Rules/checklists
  updated: none (this package is new, it does not amend an existing gate
  checklist). Rejected approaches: none. Technical debt: none added (TD-001
  unchanged). Architecture concerns: none. Tests or review gates needed: the
  live execution of this checklist itself, before Task 004 (or any next
  feature) starts. Should future prompts change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (none) · technical debt
  logged (none new) · repeated-issue escalation applied (n/a) — all YES.
- **Next recommended session:** Execute
  `task-003-manual-validation-checklist.md` against a live Odoo 19 +
  PostgreSQL instance and a Shopify development store, recording results in
  `task-003-validation-results.md`, then route the resulting go/no-go
  recommendation to ChatGPT before any Task 004 session is authorized.
- **Stop condition:** Docs-only session; no addon/Python/XML/security/
  manifest/test/CI/migration file created or modified; no next task
  (Task 004 or otherwise) started; PR left as draft for ChatGPT review; no
  code executed against any real Shopify store.

---

> Continuity lives in GitHub, not chat. The **current entry
> (Task 003 — API Client Shell and Test Connection implemented, coded
> 2026-07-07 on branch `claude/task-003-api-client-test-connection-8wsvlc`
> from latest `Shopify-connector` at PR #100's merge commit
> `984df4d1b08e873282d0c1d70bdf678c13553475` (confirmed an ancestor
> before starting): the read-only `shopify.connector.api.client`
> AbstractModel (`execute`/`_send`, dual-path error normalization, no
> mutation-capable method); `action_test_connection()` on
> `shopify.connector.store` (no field changes); the `core_test_connection`
> `job_type` addition plus a `payload_hash` dual-use comment; the single
> sanctioned `_system_append` job-log system-append method (the diff's
> only new `sudo()` site — exactly two sudo() sites exist in the whole
> diff); the per-run UUID4 `payload_hash` nonce for `core_test_connection`
> job creation only; 32 tests across three new test files, issued
> verbatim from `task-003-final-implementation-prompt.md` per the
> AR-029-opened gate. `core_readiness_check`/`TD-001` untouched, proven
> still colliding by its own test. No Odoo runtime in this repository, so
> all 32 tests are written and `py_compile`-validated, not executed. A
> known conflict is flagged, not silently resolved: the new sanctioned
> `sudo()` site makes the pre-existing Task 002 test
> `test_credential_service.py::test_source_level_single_sudo_guard`
> factually stale (it hard-codes a single-site list); that file is
> outside this task's allowed-files list and was deliberately left
> untouched. Draft PR opened into `Shopify-connector`, not merged, not
> marked ready)** is immediately below, in the **compact handoff format**
> (`../06-prompts/session-handoff-template.md`); **AR-029 — Task 003
> API-Client / Test-Connection Implementation Gate, the actual
> gate-opening act, opening exactly one future Task 003 coding session
> via the already-prepared `task-003-final-implementation-prompt.md`,
> effective once merged into `Shopify-connector` (PR #100, merge commit
> `984df4d1b08e873282d0c1d70bdf678c13553475`); also applied the AR-028
> acceptance patch in the same document (history)**, **AR-028 — Task 003
> Final Implementation Prompt and Gate-Opening Proposal, prepared
> 2026-07-07 on branch `claude/task-003-gate-opening-no0tw4`, merged via
> PR #99 (merge commit `756b88eca79f2ef56ff752b6ba82ab266a782724`) while
> still marked Proposed — accepted only later, by the AR-029 act
> immediately above (history)**, **PR #98 — ChatGPT F1
> Revision to Task 003 Decision Closure — AR-027 accepted with a
> scope-narrowing revision to Decision 4: decisions 1–3
> (`core_test_connection` job-type value; `SHOP_INACTIVE`/402/423/
> 403-fraudulent → `shopify_permission_scope_auth`; job-log system-append
> `sudo()` method) accepted as proposed; the per-run `payload_hash` UUID4
> nonce accepted for `core_test_connection` job creation only —
> `core_readiness_check`'s identical latent idempotency-collision
> exposure is explicitly excluded from Task 003's scope and logged as
> `TD-001` (technical-debt-register.md's first real entry);
> `shopify_user_errors_validation` logged as rejected (`RA-024`); AR-019
> amended to three core-owned `job_type` values; MBQ-44 noted; docs-only,
> no code, no gate opened, no external network call; Task 003 remains
> not started (history)**, **Task 003 Decision
> Closure — AR-027 originally proposed (2026-07-07), the four Task
> 003-specific decision points addressed at recommendation level, via
> `../07-implementation-plan/task-003-decision-closure.md` and companion
> QA checklist/amendment note; superseded in part by the F1 revision
> immediately above, same PR #98 (history)**, **PR #97 —
> ChatGPT F1 Revision — `_get_access_token` decorator fix, stale
> "no credential storage" wording corrected, AST decorator-guard test
> added (history)**, **Task 002 — Credential Storage, Masking, and Redaction Foundation
> implemented: the Admin-only `shopify.connector.store.credential`
> model, six store status mirrors, the redaction utility, the four
> credential service methods, one Admin-only ACL row, and 21 tests
> across three test files, executed per the AR-026-opened gate and the
> binding `task-002-final-implementation-prompt.md`, issued verbatim;
> zero API calls, zero UI, zero webhooks/controllers/cron; Task 003 not
> started; no Odoo runtime in this repository so most tests are written
> and syntax-validated, not executed — except the redaction utility's 7
> tests, which have zero Odoo dependency and were actually run and
> passed (history)**, **Task 002
> Credential-Storage Gate-Opening Act — AR-026 accepted — gate opened
> only once merged into `Shopify-connector`; authorized exactly one
> future coding session, Task 002, via the already-accepted
> `task-002-final-implementation-prompt.md`; no code in that PR
> (history)**, **PR #94 Acceptance
> Patch — AR-025 accepted by ChatGPT on 2026-07-07 at
> decision/gate-preparation level only — compute-blank rejected for
> Task 002; `token_variant` = `offline_custom_app` only; scope snapshot
> on `store`; final Task 002 implementation prompt accepted as
> gate-ready and binding but not issued; gate-opening proposal accepted
> as proposed scope but the gate is not opened; MBQ-04 still Partially
> resolved; MBQ-05 still open; MBQ-44 unchanged; no code authorized;
> Task 002/003 not started (history)**, **Task 002 Decision Closure &
> Gate-Preparation Sprint — AR-025
> proposed; the three Task 002-specific decision points closed at
> proposal level; gate-ready final prompt prepared, not issued; narrow
> credential-storage gate proposed, not opened; official Shopify/Odoo
> facts re-verified 2026-07-06; docs-only (history)**, **PR #92 Acceptance
> Patch — AR-024 accepted by ChatGPT on 2026-07-06 at
> implementation-planning level only; Option C credential model and
> redaction contract accepted at planning level; Task 002 recommended
> next but not authorized; seven decision points left open; no
> implementation gate opened (history)**, **Credential/Connection/API
> Foundation Planning Sprint — proposed AR-024 implementation-planning
> package — credential storage, redaction, connection lifecycle, test
> connection, readiness checks, API-client boundary, plus
> proposed-not-authorized Task 002/003 specs and a credential-security
> review checklist; fresh official Shopify/Odoo verification 2026-07-06;
> docs-only, no code, no gate opened, Task 002 not started (history)**,
> **PR #91 Acceptance
> Patch — AR-023 accepted; UI/UX Final Design Specification package
> accepted at design-specification level; Premium Simplicity Standard
> accepted as the UI/UX quality bar; UI implementation task map accepted
> as planning guidance only; no UI implementation gate opened
> (history)**, **UI/UX Final Design
> Sprint — docs-only implementation-ready UI/UX design specification
> package created; Premium Simplicity Standard defined; screen-by-screen
> specs, screen inventory/navigation map, MVP flows/state models, QA
> design-review checklist, and future UI implementation task map; no
> implementation, no code, no credentials/API/setup-wizard/test-connection
> artifacts; draft PR #91 into `Shopify-connector` for ChatGPT review
> (history)**, **MBQ-04 Acceptance Patch
> — PR #90 accepted by ChatGPT on 2026-07-06 (history)**, **MBQ-04 — Credential
> Persistence Research and Decision Proposal, including its PR #90 F1/F2
> revision (history)**, **Task 001A — Core Runtime
> Readiness & QA Closure (history)**, **Task 001 — F1
> fix (operation_scope_key not cleared on supersede) (history)**, **Task
> 001 — Core Module Scaffold implemented (history)**, **Limited Core
> Implementation Gate accepted — AR-021 accepted by ChatGPT, AR-018
> criterion-5 confirmed for this limited gate only (history)**,
> **Limited Core Implementation Gate proposed — AR-021 (proposal
> history)**,
> **Final MBQ Closure Plan accepted — AR-020 (history)**,
> **Final MBQ Closure Plan proposed — AR-020 (proposal history)**,
> **Core Naming and Schema Planning accepted — AR-019 (history)**,
> **Core Naming and Schema Planning — revised after ChatGPT REVISE (history,
> superseded by the acceptance)**,
> **Core Naming and Schema Planning — AR-019 proposed, original version
> (history, superseded by the revision)**,
> **Implementation Gate Readiness Audit Acceptance Patch — AR-018 accepted**,
> **Implementation Gate Readiness Audit — AR-018 proposed (history)**,
> **DEC-020 Acceptance Patch — MBQ-64/MBQ-65 resolved at decision/posture
> level**,
> **DEC-020 Revision — MBQ-64 corrected after ChatGPT REVISE (history)**,
> **Proposed MBQ-64/MBQ-65 Currency and Product-Webhook Residual Decisions
> (proposal history, superseded)**,
> **DEC-019 Acceptance Patch — MBQ-62 resolved at semantic-classification
> level**,
> **MBQ-62 Decision Proposal (proposal history)**,
> **DEC-018 Acceptance Patch — MBQ Decision Batch 1 accepted except MBQ-62**,
> **Proposed MBQ Decision Batch 1 (proposal history)**,
> **DEC-017 Acceptance Patch — Master Blueprint Part E accepted**,
> **Master Blueprint Part E — Implementation-Planning Bridge (proposal
> history)**,
> **Part D Blueprint Status Alignment**,
> **Master Blueprint Integrity & Competitor Advantage Audit**,
> **DEC-016 Acceptance Patch**,
> **Master Blueprint Sprint D (proposal history)**,
> **DEC-015 Acceptance Patch**,
> **Master Blueprint Sprint C (proposal history)**,
> **DEC-014 Acceptance Patch**, **Master
> Blueprint Sprint B (proposal history)**, **DEC-013
> Acceptance Patch**, **Master Blueprint Sprint A**,
> **DEC-012 Acceptance Patch**,
> **UX / Operator-Flow Decision
> Preparation**, **DEC-010/DEC-011 Acceptance
> Patch**, **AR-007 + AR-008 Decision Preparation**,
> **DEC-008/DEC-009 Acceptance Patch**,
> **AR-004 + AR-006 Decision Preparation**,
> **DEC-007 Acceptance Patch**, **Phase 1 Domain Model + DEC-003 Scope-Hole Closure**,
> **DEC-004/005/006 Acceptance Patch**, **Evidence Refresh + Combined AR-002/003/005
> Decision Preparation**, **Control-Room Reset Sprint 1**, **RB-14 Architecture Preparation
> — Part 2**, **RB-14 Part 1**, **Research Sprint C2**, **Product Sprint G**, **Sprint F**,
> **Sprint E**, **Sprint D**, **Sprint C**, **Sprint B**, and **Sprint A** handoffs are
> retained underneath as history. The running **Sprint checkpoint log** (one note per
> stage, all sprints) is at the very bottom. The **product-side** handoff lives at
> [`../02-product/product-research-handoff.md`](../02-product/product-research-handoff.md).

---

### Task 003 — API Client Shell and Test Connection implemented — compact handoff (2026-07-07)

> **Task 003 coding session — the one session authorized by the
> AR-029-opened gate.** Confirmed before starting: latest
> `Shopify-connector` contains PR #100's merge commit
> `984df4d1b08e873282d0c1d70bdf678c13553475` (`git merge-base
> --is-ancestor` confirmed). Working branch
> `claude/task-003-api-client-test-connection-8wsvlc` was already
> checked out at that exact commit (harness-assigned; no separate branch
> creation needed). Read `task-003-final-implementation-prompt.md`,
> `task-003-api-client-test-connection-gate.md`,
> `architecture-review-log.md`, `research-handoff.md`,
> `task-003-decision-closure.md`,
> `task-003-api-client-test-connection-proposed.md`,
> `credential-connection-api-client-planning.md`,
> `credential-security-redaction-review-checklist.md`,
> `task-003-pre-implementation-review-checklist.md`,
> `technical-debt-register.md` (`TD-001`), and every existing file under
> `addons/shopify_connector_core/` before writing anything.

- **Branch / PR:** `claude/task-003-api-client-test-connection-8wsvlc` →
  draft PR into `Shopify-connector` (opened this session; remains
  draft, not merged, not marked ready).
- **Files changed:**
  `addons/shopify_connector_core/models/shopify_connector_api_client.py`
  (new); `shopify_connector_store.py` (added `action_test_connection()`
  only, no field changes); `shopify_connector_job.py` (added
  `core_test_connection` to the base `job_type` Selection, plus a
  `payload_hash` dual-use comment; no other change); `shopify_connector_job_log.py`
  (added `_system_append` only; no field change); `models/__init__.py`
  (one import line); `__manifest__.py` (version `19.0.1.1.0` →
  `19.0.1.2.0`); `tests/test_api_client.py`, `tests/test_test_connection.py`,
  `tests/test_job_log_system_append.py` (new, 32 tests total);
  `tests/__init__.py` (three import lines — a mechanical addition
  needed for Odoo to discover the three new test files at all; not
  listed by name in the final prompt's allowed-files list, but approved
  as an F1 exception by ChatGPT's review and now documented in-file —
  see the F1 revision note below); `test_credential_service.py` (F1
  revision — one stale test renamed/updated, see below);
  `docs/01-research/research-handoff.md` (this entry, plus the F1
  revision note). **No view/menu/action/wizard/XML file, no controller/webhook/cron/data
  file, no `shopify_connector_store_credential.py`,
  `security/ir.model.access.csv`, `security/shopify_connector_security.xml`,
  `shopify_connector_location.py`, `shopify_connector_binding_mixin.py`,
  `shopify_connector_store_settings.py`, `adams_base`, domain module, CI
  file, or migration touched.**
- **What changed / residue fixed:** Implemented Task 003 exactly per
  `task-003-final-implementation-prompt.md`, issued verbatim after the
  AR-029 gate merged. The read-only `shopify.connector.api.client`
  AbstractModel: `execute()`/`_send()`, dual-path error normalization
  (HTTP status **and** 200-OK `errors[].extensions.code`) into the fixed
  16-class registry (only 4 classes ever raised by the client;
  `odoo_validation_configuration` is interpreted by
  `action_test_connection()` from a successful response, not raised by
  the client); `ShopifyClientError` with `credential_invalid` gating;
  throttle metadata (`extensions.cost.throttleStatus`) surfaced
  verbatim, never acted on (MBQ-51 untouched); version fall-forward
  detected via the `X-Shopify-API-Version` header. Structurally
  read-only — no mutation-capable method, no retry loop, proven by a
  dedicated test (source-scan for a GraphQL `mutation` operation string
  plus a minimal-public-surface assertion). `action_test_connection()`
  on `shopify.connector.store`: precondition guard, job creation with a
  per-run UUID4 `payload_hash` nonce, the exact
  `ConnectorTestConnection` query, identity check
  (`shop.myshopifyDomain` vs `store.shop_domain`), the five distinct
  `shopify_permission_scope_auth` reasons (402/423/403/`SHOP_INACTIVE`/
  `ACCESS_DENIED`-or-401, verified pairwise distinct by test),
  `credential_state` gated to genuine token-invalid signals only, and
  the version-fallforward warning mirror. `_system_append` on
  `shopify.connector.job.log`: the one new sanctioned `sudo()` site in
  the whole diff (confirmed by an AST source scan — exactly two sites
  total, the other being the untouched, pre-existing Task 002
  `_get_access_token`); redacts every free-text argument. `core_test_connection`
  added as the base `job_type`'s third value (amends AR-019 per AR-027).
  `core_readiness_check` is untouched — a dedicated test proves it still
  collides on `store_idempotency_key_uniq` on a second run, documenting
  rather than fixing `TD-001`. Manifest bumped to `19.0.1.2.0`.
- **Items deferred:** Manual validation against a live Odoo 19 +
  PostgreSQL + development store was **not performed** — no Odoo
  runtime exists in this repository (Task 001A precedent, still
  unchanged). All 32 tests were written and `python3 -m py_compile`-validated
  (all files compile cleanly; `pyflakes` run with only the expected,
  harmless `__init__.py` "imported but unused" registration warnings),
  not executed. The empirical open behavioral questions this task's
  acceptance criteria name (actual invalid-token HTTP status; actual
  `THROTTLED` body shape; whether `shop`/`currentAppInstallation` need
  any scope; actual missing-scope shape) remain unanswered pending that
  manual validation — not asserted as confirmed anywhere in code, tests,
  or this entry.
- **F1 revision applied (ChatGPT review of PR #101, resolved same PR):**
  ChatGPT reviewed PR #101 with result **REVISE** and explicitly
  authorized a narrow F1 patch, still on this same branch/PR: (1)
  `tests/__init__.py`'s three import lines are **kept**, now documented
  in-file as an approved Odoo test-discovery scaffolding exception
  (comment cites this F1 review); (2) the stale pre-existing test
  `test_credential_service.py::test_source_level_single_sudo_guard` —
  which hard-coded `sudo_call_sites == ['shopify_connector_store_credential.py']`,
  no longer true once Task 003's second sanctioned `_system_append`
  `sudo()` site landed — is renamed
  `test_source_level_sanctioned_sudo_sites_guard` and now asserts the
  sorted two-site list (`shopify_connector_job_log.py`,
  `shopify_connector_store_credential.py`), with an updated comment
  explaining the two sanctioned sites; the guard is strengthened (now
  order-independent via `sorted()`), never weakened. No production code
  changed in this F1 patch — re-validated: `core_readiness_check`
  remains untouched, exactly two `sudo()` sites exist (AST-confirmed),
  all files `py_compile`-clean, `pyflakes`-clean (same expected
  `__init__.py` warnings only). PR #101 remains draft, not merged, not
  marked ready.
- **Learning feedback loop:**
  - New issues discovered: a task prompt's allowed-files list can miss
    a file that the task's own authorized change necessarily makes
    stale (the sudo-count-test conflict, resolved via ChatGPT's F1
    review above); an allowed-files list can also omit a mechanical
    scaffolding file a newly-authorized test file needs to be
    discoverable at all (`tests/__init__.py` was not named even though
    three new test files were mandated — resolved via the same F1
    review).
  - Repeated issue patterns: this is the second task (after Task 002)
    with no Odoo runtime available — tests are written and
    `py_compile`-validated but not executed; the Task 001A applicability
    rule continues to hold.
  - Rules/checklists updated: none this session.
  - New rejected approaches: none.
  - New technical debt: none new; `TD-001` remains open, unaffected,
    and confirmed still colliding by a dedicated test.
  - Architecture concerns: future final implementation prompts should
    explicitly check whether their own authorized change (e.g., a new
    sanctioned `sudo()` site) invalidates an existing test's hard-coded
    assertion, and name that file in Allowed files if so, rather than
    leaving it for the implementer to discover and flag mid-session; the
    same check should cover `__init__.py`/registration files any new
    module or test file needs in order to load/run at all.
  - Tests or review gates needed: none outstanding — the flagged
    `test_credential_service.py` conflict was resolved in the same PR
    via ChatGPT's F1 review (see above).
  - Should future prompts change? Yes — future final implementation
    prompts should audit for (a) existing tests their own authorized
    change will make stale, and (b) registration/`__init__.py` files
    any newly-authorized file needs, and name both explicitly in Allowed
    files rather than leaving them implicit.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged — N/A, none · technical
  debt logged — N/A, `TD-001` unaffected and unmodified · repeated-issue
  escalation applied — noted above (no-runtime pattern) — all YES. The
  previously-flagged `test_credential_service.py` conflict is now
  resolved (F1 revision, same PR, ChatGPT-authorized) — no item remains
  open.
- **Next recommended session:** ChatGPT re-review of this draft PR
  (post-F1) against `task-003-pre-implementation-review-checklist.md`
  §B and `credential-security-redaction-review-checklist.md`. No next
  task starts until this PR is reviewed and accepted (per the gate's
  closure rule — the gate authorized exactly one coding session, now
  consumed).
- **Stop condition:** stopped immediately after pushing the F1 revision
  to the same draft PR — no merge, no ready-for-review, no manual
  validation (no runtime), no other task started, `main`/plain `dev`
  untouched.

**Exact next-session prompt:**

> After ChatGPT re-reviews the Task 003 draft PR
> (`claude/task-003-api-client-test-connection-8wsvlc`, post-F1) against
> `task-003-pre-implementation-review-checklist.md` §B and
> `credential-security-redaction-review-checklist.md` and either
> requests further fixes or accepts it, the next session applies that
> feedback (or, if accepted, performs the manual-validation step against
> a live Odoo 19 + development store once a runtime is available,
> recording the empirically-observed answers to the open behavioral
> questions). No new task (including any `core_readiness_check`/`TD-001`
> follow-up) starts before this PR is reviewed and accepted.

---

### Task 003 API-Client / Test-Connection Implementation Gate — compact handoff (2026-07-07)

> **Docs-only gate-opening act — not Task 003, not code, not a research
> sprint.** Confirmed before starting: PR #99 merged into
> `Shopify-connector` (merge commit
> `756b88eca79f2ef56ff752b6ba82ab266a782724`, confirmed an ancestor of
> latest `Shopify-connector`); PR #98 merge commit
> `2e51cf02cd54527ff9dc817b6be1e1189f001a83` also confirmed an ancestor;
> AR-027 Accepted (with the F1 revision); the final Task 003 prompt and
> gate-opening proposal (AR-028) present in the repository but still
> marked Proposed in their own text; Task 002 implemented and merged
> (PR #97); Task 003 not started; working branch created from latest
> `Shopify-connector`.

- **Branch / PR:** `claude/task-003-gate-act-92cfd7` → draft PR into
  `Shopify-connector` (opened this session; remains draft, not merged).
- **Files changed:**
  `docs/07-implementation-plan/task-003-api-client-test-connection-gate.md`
  (new — the gate-opening act itself), `docs/05-qa/architecture-review-log.md`
  (AR-028 row → **Accepted**; new AR-029 row, **Accepted**; AR-029
  gate-opening note appended), `docs/07-implementation-plan/task-003-final-implementation-prompt.md`
  and `docs/07-implementation-plan/task-003-gate-opening-proposal.md`
  (short acceptance callouts added to each Status section, mirroring
  the AR-025/PR #94 precedent — original proposal text preserved below,
  unedited, as history), `docs/01-research/research-handoff.md` (this
  entry). **No addon/code file touched. No Python/XML/CSV/manifest/
  test/CI file created or modified. No API client, test-connection
  mechanism, credential-model change, or external/Shopify network call
  of any kind created or made. No webhook/controller/cron/domain module
  created.**
- **What changed:** **AR-028 accepted** (its package having merged via
  PR #99 while still marked Proposed) **and AR-029 accepted — the
  narrow Task 003 API-client/test-connection implementation gate is
  opened, effective once this PR merges into `Shopify-connector`.** The
  gate authorizes exactly one future coding session — Task 003 (API
  Client Shell and Test Connection) — using the exact contracts already
  accepted in `task-003-final-implementation-prompt.md` (referenced by
  path, not restated/duplicated). **This is the first conscious
  widening of the AR-021 no-external-API-call rule** — read-only
  outbound GraphQL calls only. **This PR does not implement Task 003,
  does not create the API client or any model/field, and does not
  create any code, and makes no external network call** — the final
  prompt is not issued inside this PR.
- **Still forbidden:** `core_readiness_check`/`TD-001` fix (unless a
  future gate names it explicitly); setup wizard; UI/views/menus/
  actions/wizards; webhooks/controllers/cron; product/customer/order/
  inventory/fulfillment; domain modules; migrations (none justified);
  credential-model changes; ACL/security-file changes; mutations; Bulk
  Operations; REST calls; any `sudo()` beyond the two sanctioned sites;
  any second task before ChatGPT reviews Task 003's implementation PR.
- **AR-028 / AR-029:** Both Accepted. **No implementation gate is open
  until this PR merges. Task 003 is not started.**
- **Learning feedback loop:** new issues: none. Repeated patterns: none
  new. Rules updated: none. Rejected approaches: none reintroduced.
  Technical debt: none new — `TD-001` referenced, not modified, and
  explicitly kept out of this gate's scope. Architecture concerns: none
  new — this act stays strictly inside the AR-027/AR-028-accepted
  scope; the one process note worth flagging is that AR-028's package
  (PR #99) merged before its own acceptance patch was applied (unlike
  the AR-025/PR #94 convention of applying the patch before merge) —
  this act closes that gap by applying the AR-028 acceptance patch and
  the AR-029 gate-opening act together, in the same document.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (N/A) ·
  technical debt logged (N/A, `TD-001` already logged via AR-027, only
  referenced here) · repeated-issue escalation applied (N/A) — all YES.
- **Stop condition:** stopped immediately after opening the draft PR —
  no merge, no ready-for-review, no implementation, Task 003 not
  started.
- **Recommended next step:** ChatGPT reviews this gate-opening act; if
  accepted and merged into `Shopify-connector`, the gate is open and
  `task-003-final-implementation-prompt.md` is issued verbatim, in its
  own session, as the Task 003 coding session (that session's PR must
  remain draft until ChatGPT reviews it).

**Exact next-session prompt:**

> After this gate-opening act (AR-029) is merged into
> `Shopify-connector`, issue
> `docs/07-implementation-plan/task-003-final-implementation-prompt.md`
> verbatim as the Task 003 coding session — create the read-only
> `shopify.connector.api.client` shell, the `action_test_connection()`
> entry point, the `core_test_connection` `job_type` addition, the
> `_system_append` job-log system-append method, the per-run UUID4
> `payload_hash` nonce for `core_test_connection` job creation only, the
> enumerated tests, and the manifest version bump, exactly as specified,
> with zero deviation from the accepted contracts. Keep the resulting PR
> draft until ChatGPT reviews it.

---

### Task 003 Final Implementation Prompt & Gate-Opening Proposal — compact handoff (2026-07-07)

> **Docs-only gate-preparation sprint for Task 003 — not Task 003
> itself; no code; no new decision.** Confirmed before starting: PR #98
> merged into `Shopify-connector` (merged 2026-07-07; merge commit
> `2e51cf02cd54527ff9dc817b6be1e1189f001a83` = latest
> `origin/Shopify-connector`); AR-027 Accepted (with the F1 revision to
> Decision 4); Task 002 merged and implemented (PR #97); Task 003
> recommended (AR-024) and decision-closed (AR-027) but not authorized;
> working branch created from that merge commit.

- **Branch / PR:** `claude/task-003-gate-opening-no0tw4` → not opened as
  a PR by this session (per task scope — commit and push only; PR
  number to be assigned when opened for ChatGPT review).
- **Files created:**
  `docs/07-implementation-plan/task-003-final-implementation-prompt.md`
  (complete copy-paste final §9 prompt applying the four AR-027
  decisions — **not issued, not authorized**),
  `docs/07-implementation-plan/task-003-gate-opening-proposal.md`
  (proposed narrow gate act for the first outbound-API-call
  authorization — **opens nothing**).
  **Files updated:** `docs/05-qa/architecture-review-log.md` (new
  AR-028 row, **Proposed for ChatGPT review — NOT YET ACCEPTED**, plus a
  narrative note at the top of the notes section),
  `docs/07-implementation-plan/task-003-api-client-test-connection-proposed.md`
  (dated gate-preparation note added to §Status, pointing at the two new
  documents — no contract content changed), `docs/01-research/research-handoff.md`
  (this entry + header pointer). **No addon/code file touched. No
  Python/XML/CSV/manifest/test/CI file created or modified. No API
  client, test-connection mechanism, credential-model change, or
  external/Shopify network call of any kind created or made. No
  webhook/controller/cron/domain module created. No implementation gate
  opened. Task 003 remains not started.
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/task-003-pre-implementation-review-checklist.md`,
  DEC-003 through DEC-020, `docs/04-decisions/README.md`, and
  `defect-pattern-log.md` all unchanged — no new decision is made this
  session, so no register-status change is due.**
- **What this session did:** applied the four already-accepted AR-027
  decisions into a single, complete, copy-paste-ready final Task 003
  implementation prompt (`job_type` gains `core_test_connection`;
  `SHOP_INACTIVE`/402/423/403-fraudulent → `shopify_permission_scope_auth`
  with `credential_state` gating and five mandatory, pairwise-distinct
  plain-language reasons; a new `_system_append` job-log system-append
  method as the single new sanctioned `sudo()` site, no ACL change;
  `payload_hash` populated with a per-run UUID4 nonce for
  `core_test_connection` job creation only), specified the
  `shopify.connector.api.client` AbstractModel contract and
  `action_test_connection()` entry point in full, and enumerated 32
  exact required tests. Packaged a companion gate-opening proposal
  scoping exactly that implementation boundary as the **first**
  conscious widening of the AR-021 no-external-API-call rule.
  `core_readiness_check`'s identical latent collision defect
  (`TD-001`) is explicitly named as excluded from the proposed gate,
  not silently folded in.
- **AR-028:** Proposed. **No implementation. No gate opened.** The
  final prompt explicitly requires, before execution: AR-028 accepted
  **and** a separate, explicit ChatGPT gate-opening act merged (a third
  document, not created by this session, mirroring
  `task-002-credential-storage-gate.md` for AR-026).
- **Learning feedback loop:** new issues: none. Repeated patterns: none
  new (checked `defect-pattern-log.md` categories — no unsupported-claim
  or scope-creep occurrence; every platform statement reuses the
  already-authoritative `task-003-api-client-test-connection-proposed.md`
  or the AR-027-accepted decisions). Rules updated: none. Rejected
  approaches: none reintroduced (RA-001–RA-024 not re-litigated).
  Technical debt: none new — `TD-001` referenced, not modified, and
  explicitly kept out of this task's proposed scope. Architecture
  concerns: none new — this package stays inside AR-024/AR-027.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (N/A, none new)
  · technical debt logged (N/A, `TD-001` already logged via AR-027, only
  referenced here) · repeated-issue escalation applied (N/A) — all YES.
- **Stop condition:** stopped after committing and pushing the branch —
  no PR opened by this session, no merge, no implementation, no gate
  opened, Task 003 not started.
- **Recommended next step:** ChatGPT reviews AR-028 (this entry, the
  final implementation prompt, and the gate-opening proposal); then
  either (a) accept AR-028 and separately perform the explicit Task 003
  gate-opening act (its own merged document), after which the final
  prompt is issued verbatim as the Task 003 coding session; or (b)
  request revision of this package.

**Exact next-session prompt:**

> Apply ChatGPT's review decision for the Task 003 final-implementation
> -prompt-and-gate-proposal package (AR-028). If accepted: apply the
> acceptance patch (AR-028 row → Accepted; handoff entry) and — only if
> ChatGPT also performs the separate, explicit Task 003 gate-opening act
> in `task-003-gate-opening-proposal.md` (its own new, merged document,
> mirroring `task-002-credential-storage-gate.md` for AR-026) — record
> that act; still no code in that session. If revision is requested:
> apply the requested revisions to the AR-028 package only. Task 003
> implementation starts only afterwards, in its own session, via the
> verbatim `task-003-final-implementation-prompt.md`.

---

### PR #98 — ChatGPT F1 Revision to Task 003 Decision Closure — compact handoff (2026-07-07)

> **Applies ChatGPT's F1 revision decision for PR #98 (accept
> decisions 1–3; accept Decision 4 with a scope-narrowing revision) —
> not new code, not a gate-opening act.** Confirmed before editing: PR
> #98 (branch `claude/task-003-decisions-xx7u85`) was open, draft, with
> the decision-closure package from the immediately-preceding session;
> working tree clean; no additional files changed since that commit.

- **Branch / PR:** `claude/task-003-decisions-xx7u85` → PR #98 into
  `Shopify-connector` (https://github.com/AdamsOdoo/Adams/pull/98;
  remains draft, not merged, not marked ready for review).
- **Files changed:** `docs/07-implementation-plan/task-003-decision-closure.md`
  (Acceptance section added; Decision 4's body corrected to scope the
  nonce to `core_test_connection` only; Register/next-step sections
  updated to reflect acceptance), `docs/07-implementation-plan/task-003-api-client-test-connection-proposed.md`
  (F1 acceptance-patch note appended to §Status), `docs/05-qa/task-003-pre-implementation-review-checklist.md`
  (Status updated to Accepted; gate items updated to reflect the
  accepted, scope-narrowed outcome), `docs/05-qa/architecture-review-log.md`
  (AR-027 row flipped to **Accepted**; AR-027 Acceptance Patch narrative
  note and an AR-019 amendment note added), `docs/03-architecture/master-blueprint-open-questions.md`
  (one note appended to MBQ-44 — status unchanged), `docs/05-qa/rejected-approaches-log.md`
  (new **RA-024** — `shopify_user_errors_validation` as the rejected
  error-class alternative), `docs/05-qa/technical-debt-register.md`
  (new **TD-001** — the `core_readiness_check` follow-up; the register's
  first real entry), this handoff entry. **No Python/XML/CSV/manifest/
  test/CI file touched. No `addons/` file of any kind touched. No
  unrelated MBQ/DEC/AR row touched.**
- **What changed (the F1 fix itself):** Decision 4 originally implied
  Task 003 should populate the per-run `payload_hash` nonce "for every
  target-less job type," which would have silently pulled a fix to the
  already-merged Task 001 `core_readiness_check` job type into Task
  003's implementation boundary. Corrected so the accepted nonce
  mechanism applies to **`core_test_connection` job creation only**;
  `core_readiness_check`'s identical latent collision exposure is now
  explicitly out of Task 003's scope, recorded as `TD-001`, and routed
  to either a future explicitly-named gate inclusion or its own separate
  tiny follow-up patch (candidate name: "Task 001B — job-framework
  target-less idempotency patch").
- **Decisions 1–3:** accepted exactly as proposed — `core_test_connection`
  confirmed (amends AR-019 to three core-owned `job_type` values);
  `SHOP_INACTIVE`/402/423/403-fraudulent confirmed mapped to
  `shopify_permission_scope_auth` (mandatory distinct plain-language
  reasons; `credential_state`-gating refinement preserved; behavioral
  shapes not already cited remain `[Requires external validation before
  implementation]`); the sanctioned internal `sudo()`-wrapped job-log
  system-append method confirmed over ACL widening (no security-file
  change).
- **Register convention used:** proposal and acceptance patch applied
  within the **same PR/branch**, before merge — matching the
  AR-025/PR #94 precedent (confirmed this session by diffing that file's
  pre-acceptance and current versions: both the original decision-closure
  commit and its later "accept" commit are ancestors of PR #94's merge
  commit). Chose **"Accepted by ChatGPT — with F1 revision"** for
  AR-027's status rather than "Proposed — F1 revision applied for
  ChatGPT re-review," since the instruction directing this patch already
  stated the acceptance decision explicitly (not merely "revise and
  I'll look again").
- **Learning feedback loop:**
  - New issues discovered: none new this session (the `core_readiness_check`
    collision risk was already surfaced in the prior session; this
    session corrects the routing, it does not discover a new defect).
  - Repeated issue patterns: none at count ≥ 2.
  - Rules/checklists updated: none — existing templates already
    accommodated an F1-style acceptance patch (PR #97 precedent).
  - New rejected approaches: **RA-024** logged (see above).
  - New technical debt: **TD-001** logged (see above) — the register's
    first real entry.
  - Architecture concerns: none new beyond what AR-027/TD-001 already
    capture.
  - Tests or review gates needed: the future Task 003 implementation PR
    must prove `core_readiness_check` is **untouched** unless a gate
    names it explicitly — added to
    `task-003-pre-implementation-review-checklist.md` §B.
  - Should future prompts change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged (RA-024) · technical
  debt logged (TD-001) · repeated-issue escalation applied (N/A) — all
  YES.
- **Stop condition:** stopped immediately after this handoff update — no
  merge, no ready-for-review transition, no code, no gate opened, no
  external network call.
- **Recommended next step:** ChatGPT (or the control room) schedules
  `TD-001`'s resolution (folded into a future Task 003 gate by name, or
  its own "Task 001B"-style patch), then a separate future session
  prepares the final Task 003 `CLAUDE.md` §9 implementation prompt and a
  narrow gate-opening proposal.

---

### Task 003 Decision Closure — compact handoff (2026-07-07)

> **Docs-only decision-closure sprint — not Task 003 code, not a
> gate-opening act.** Confirmed before starting: `Shopify-connector` tip
> was PR #97's merge commit `7498ba181a01e571204e471d6880ea0c2068fd87`
> (`git diff origin/Shopify-connector..HEAD --stat` empty at session
> start); Task 002 merged and implemented; Task 003 not started (no API
> client/test-connection code, no `job_type` change, no `payload_hash`
> change existed anywhere in the addon). **Session constraint: no
> external network access** — no new Shopify/Odoo official-source
> research was performed or claimed; every platform statement below
> reuses an already-cited repo document or is explicitly labelled as
> requiring future external validation.

- **Branch / PR:** `claude/task-003-decisions-xx7u85` → draft PR into
  `Shopify-connector` (not yet opened at the time of this handoff entry;
  opened immediately after this commit per the session's push step).
- **Files changed:** `docs/07-implementation-plan/task-003-decision-closure.md`
  (new — the four-decision closure package),
  `docs/07-implementation-plan/task-003-api-client-test-connection-proposed.md`
  (dated amendment note appended to §Status only — no other content
  changed), `docs/05-qa/task-003-pre-implementation-review-checklist.md`
  (new — companion QA/acceptance checklist for the future Task 003 PR),
  `docs/05-qa/architecture-review-log.md` (new **AR-027** row, **Proposed
  for ChatGPT review** — not accepted), this handoff entry. **No Python/
  XML/CSV/manifest/test/CI file touched. No `addons/` file of any kind
  touched. No `master-blueprint-open-questions.md` edit** (the proposed
  MBQ-44/AR-019 register-impact wording is described inside the
  decision-closure document itself, to be applied only by a future
  acceptance patch, per the AR-025 convention). **No
  `rejected-approaches-log.md` edit** (the `shopify_user_errors_validation`
  rejected alternative is named and reasoned about in the decision
  document but is logged there only upon acceptance, per the ADR
  template).
- **Decisions addressed (recommendations only, none accepted):**
  (1) `core_test_connection` recommended as the `job_type` value, added
  directly to the base selection (amends AR-019's fixed-at-two-values
  statement to three, if accepted); (2) `SHOP_INACTIVE`/402/423/
  403-fraudulent recommended mapped to `shopify_permission_scope_auth`
  — the underlying HTTP-status/error-code facts are already cited in
  `../03-architecture/credential-connection-api-client-planning.md`
  (accessed 2026-07-06), but the mapping choice itself and several named
  behavioral shapes (exact `THROTTLED` body; 401 vs. 200+`ACCESS_DENIED`;
  missing-scope shape; `shop`/`currentAppInstallation` scope
  requirements) remain `[Requires external validation before
  implementation]`; `credential_state` recommended to flip to `invalid`
  only for a genuine token-invalid signal, never for a shop-account-state
  condition; (3) a single, internal, documented `sudo()`-wrapped job-log
  system-append write method recommended over ACL widening — no
  `security/ir.model.access.csv` or `shopify_connector_security.xml`
  change; (4) a per-run UUID4 nonce in `payload_hash` recommended for
  every target-less job, with no schema/field change needed (the field
  already exists as a plain stored Char).
- **New finding this session (not a defect in this PR — a latent defect
  in already-merged schema):** the target-less-idempotency-collision
  reasoning behind Decision 4 applies equally to the pre-existing
  `core_readiness_check` `job_type` (AR-019, merged in Task 001) — a
  second job of that type for the same store would collide on
  `store_idempotency_key_uniq` today, since `idempotency_key` never
  clears on terminal state. Recorded in the decision-closure document,
  the AR-027 row, and the QA checklist so it is not lost; not fixed by
  this docs-only session.
- **Learning feedback loop:**
  - New issues discovered: one — the `core_readiness_check` target-less
    idempotency-collision latent defect above (category: missing test
    coverage / duplicate-prevention risk on already-merged schema,
    surfaced by analysis, not by a failing test in this no-runtime
    repository).
  - Repeated issue patterns: none at count ≥ 2 this session.
  - Rules/checklists updated: none this session (the existing redaction
    checklist's sanctioned-elevations gate already anticipated Decision
    3; no new rule was needed).
  - New rejected approaches: none logged yet — `shopify_user_errors_validation`
    as the error-class mapping is named as the considered-and-not-recommended
    alternative in the decision document, to be logged in
    `rejected-approaches-log.md` only if/when ChatGPT accepts Decision 2.
  - New technical debt: one item proposed for
    `../05-qa/technical-debt-register.md` if Decision 4 is accepted — the
    `payload_hash` field's dual semantics (real payload fingerprint for
    domain jobs vs. per-run nonce for target-less jobs) is a naming
    overload that a future generic job-framework revision should
    consider cleaning up; not logged as a register entry by this
    docs-only session (that register file was not in this session's
    allowed-files scope) — flagged here for ChatGPT to route.
  - Architecture concerns: the `core_readiness_check` collision defect
    above; recorded in `architecture-review-log.md`'s AR-027 row.
  - Tests or review gates needed: the future Task 003 PR must prove "a
    second test-connection run on the same store succeeds" by test, per
    `task-003-pre-implementation-review-checklist.md` §B (already
    written into this session's QA checklist).
  - Should future prompts change? No — the existing implementation-task
    template and decision-closure precedent (AR-025/Task 002) already
    fit this pattern; this session followed it directly.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged (N/A — none accepted
  yet) · technical debt logged (N/A — flagged for future routing, not
  yet in the register) · repeated-issue escalation applied (N/A) — all
  YES.
- **Stop condition:** stopped immediately after this handoff update and
  pushing the branch — no PR merge, no gate-opening act, no final Task
  003 implementation prompt, no code, no external network call, no
  Shopify API call. Task 003 remains not started and not authorized.
- **Recommended next step:** ChatGPT reviews AR-027
  (`task-003-decision-closure.md`) and its companion QA checklist; on
  acceptance (in full or with corrections), a separate future session
  prepares the final Task 003 `CLAUDE.md` §9 implementation prompt and a
  narrow Task 003 gate-opening proposal — the first conscious widening
  of the no-external-API-call rule — mirroring the AR-025 → AR-026
  sequence for Task 002. The `core_readiness_check` collision defect
  should be routed by ChatGPT to either this same future Task 003 PR or
  its own tiny, separately-scoped patch.

**Exact next-session prompt:**

> Apply ChatGPT's review decision for AR-027 (Task 003 decision
> closure). If accepted in full or with corrections: prepare the final
> Task 003 `CLAUDE.md` §9 implementation prompt and a narrow
> gate-opening proposal restricted to the read-only API-client shell and
> test-connection service (mirroring `task-002-final-implementation-prompt.md`
> and `task-002-gate-opening-proposal.md`), fixing the pinned API-version
> default, timeout constants, and — per ChatGPT's routing choice — either
> folding in or separately scoping the `core_readiness_check`
> idempotency-collision fix. Do not open the gate or write code in that
> same session unless ChatGPT's prompt explicitly says so. If revision is
> requested on any of the four decisions: apply exactly the requested
> changes to `task-003-decision-closure.md` and its companion documents,
> without expanding into implementation-prompt or gate-opening material.

---

### PR #97 — ChatGPT F1 Revision — compact handoff (2026-07-07)

> **Applies ChatGPT's F1 revision decision for PR #97 (REVISE, not
> reject) — not a new task, not Task 003.** Confirmed before editing:
> PR #97 head `342427dd07ddb576e0af6b87b66cd3d297082cf0`; only the
> five files this patch is scoped to were touched.

- **Branch / PR:** `claude/task-002-credential-storage` → PR #97 into
  `Shopify-connector` (still draft, still open, not merged).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store_credential.py`
  (`@api.model` added to `_get_access_token`),
  `addons/shopify_connector_core/models/shopify_connector_store.py`
  (docstring only — no field/method change),
  `addons/shopify_connector_core/__manifest__.py` (summary/description
  wording only — version unchanged at `19.0.1.1.0`),
  `addons/shopify_connector_core/tests/test_credential_service.py` (new
  AST-based decorator-guard test added; existing single-`sudo()` guard
  unchanged), `docs/01-research/research-handoff.md` (this entry). **No
  new file added. No XML touched. No API/test-connection/setup-wizard/
  UI/webhook/controller/cron/domain-logic content added.**
- **Findings addressed:** (1) `_get_access_token` was missing
  `@api.model` — added, no behavior change. (2) The store model's
  docstring and the manifest's summary/description still said
  "credential persistence... descoped" / "no credential storage",
  false after Task 002's own model exists — corrected to state plainly
  that `shopify.connector.store` holds only non-secret status mirrors,
  the secret lives on the dedicated credential model, and the module
  now includes the credential-storage/redaction foundation while still
  excluding the API client, external calls, webhooks, cron, setup
  wizard, and UI. No encryption claim, no marketing language.
- **Test coverage added:** a new AST-based test proves
  `action_set_token`, `action_replace_token`, `action_clear_token`, and
  `_get_access_token` are all decorated with `@api.model` (parses the
  credential model file, checks each `FunctionDef`'s `decorator_list`
  for an `Attribute(attr='model')` on `Name(id='api')` — not a text
  grep, for the same false-positive-avoidance reason as the existing
  sudo guard). The existing single-`sudo()` AST guard is unchanged and
  was not weakened.
- **Verification performed this session:** both AST-based guards
  (single-`sudo()` and all-four-`@api.model`) were extracted and run
  standalone against the actual fixed files — both pass. All four
  changed Python files `py_compile`-validated cleanly. The redaction
  utility's 7 pure-Python tests were re-run standalone and still pass
  (unaffected by this patch). Manifest re-parsed:
  `version == '19.0.1.1.0'` confirmed unchanged.
- **Test execution status (unchanged honesty):** this repository still
  has no Odoo runtime/psycopg2/PostgreSQL/CI. The 14 ORM-dependent
  tests (`test_credential_access.py`, `test_credential_service.py`)
  remain **written and syntax-validated only, not executed**; the
  manual validation checklist remains the mandatory review-evidence
  path. `test_redaction.py`'s 7 tests remain **actually executed and
  passing** (zero Odoo dependency).
- **Learning feedback loop:** new issue: none (this was ChatGPT's own
  finding, not a self-discovered defect). Repeated patterns: none new.
  Rejected approaches: none reintroduced. Technical debt: none new.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (N/A) ·
  technical debt logged (N/A) · repeated-issue escalation applied
  (N/A) — all YES.
- **Stop condition:** stopped immediately after pushing this patch and
  refreshing the PR body — no merge, no ready-for-review, no Task 003.
- **Recommended next step:** ChatGPT re-reviews PR #97 with the F1
  fixes applied.

---

### Task 002 — Credential Storage, Masking, and Redaction Foundation — compact handoff (2026-07-07)

> **Implementation session — the first coding PR under the AR-026-opened
> Task 002 gate.** Issued verbatim from
> `docs/07-implementation-plan/task-002-final-implementation-prompt.md`
> (the `BEGIN FINAL TASK PROMPT` … `END FINAL TASK PROMPT` block, no
> reinterpretation). Confirmed before starting: latest `Shopify-connector`
> contains PR #92 merge commit `f74aaf204745ce0087733870fe56bdda74bfa79a`,
> PR #94 merge commit `03ffcb4dc949cd5137b589a6cdc33da9105de31d`, and PR
> #96 merge commit `02b159a39c58a3396c1c249e80896a05c97bb757`; AR-026
> Accepted and the gate open; Task 002 not already implemented (no
> credential/token field existed anywhere in the addon); Task 003 not
> started (no API client/test-connection code existed).

- **Branch / PR:** `claude/task-002-credential-storage` → draft PR #97
  into `Shopify-connector`
  (https://github.com/AdamsOdoo/Adams/pull/97; remains draft, not
  merged; stop condition per the final prompt).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_store_credential.py`
  (new — the credential model + four service methods),
  `addons/shopify_connector_core/models/shopify_connector_store.py`
  (six mirror fields added only), `addons/shopify_connector_core/models/__init__.py`
  (one import line), `addons/shopify_connector_core/tools/__init__.py`
  (new), `addons/shopify_connector_core/tools/redaction.py` (new),
  `addons/shopify_connector_core/security/ir.model.access.csv` (one
  credential ACL row appended), `addons/shopify_connector_core/__manifest__.py`
  (version bump `19.0.1.0.0` → `19.0.1.1.0`),
  `addons/shopify_connector_core/tests/__init__.py`,
  `test_credential_access.py`, `test_redaction.py`,
  `test_credential_service.py` (new — 21 enumerated tests), this
  handoff entry. **No XML file touched. No controller/webhook/cron/data
  file. `security/shopify_connector_security.xml` unchanged. No other
  core model file (`job`, `job_log`, `location`, `binding_mixin`,
  `store_settings`) touched. No `adams_base`/domain/CI/migration file.**
- **What was built:** exactly the AR-025-accepted contracts, applied
  with zero deviation — the Admin-only `shopify.connector.store.credential`
  model (`store_id`, `access_token` with `copy=False` + Admin-only
  `groups=`, `token_variant` = single value `offline_custom_app`,
  `credential_state`, one SQL unique constraint); six readonly status
  mirrors on `shopify.connector.store` (`credential_present`,
  `credential_last_verified_at`, `credential_last_replaced_at`,
  `credential_last_failure_reason`, `granted_scopes`,
  `granted_scopes_checked_at` — the last two created with no writer,
  per Decision 3); the four service methods (`action_set_token`,
  `action_replace_token`, `action_clear_token`, `_get_access_token`),
  every write path running as the calling user with **zero** `sudo()`
  except the single sanctioned occurrence inside `_get_access_token`;
  the `tools/redaction.py` utility (`SENSITIVE_KEYS`,
  `SENSITIVE_VALUE_PATTERNS`, `redact()`); one Admin-only ACL row
  (`1,1,1,0`, no unlink, no rows for auditor/operator/reviewer).
- **Compute-blank rejected, as decided:** `access_token` is a plain
  stored Char, no compute/inverse/raw SQL/hand-managed column/companion
  field. The model docstring states the honest residual (Admin-group
  ORM/RPC read technically possible; `sudo()`/DB/backup reads the
  plaintext; no encryption claim) and the deliberate absence of
  `client_id`/`client_secret`/token-cache/expiry fields pending MBQ-05.
- **Tests (21 enumerated, across 3 files):** written exactly to the
  final prompt's list — access/denial matrix + independent field-`groups`
  layer + `display_name` safety (`test_credential_access.py`, 4 tests);
  redaction key/value/exact-scrub/nesting/idempotence/passthrough/
  no-mutation (`test_redaction.py`, 7 tests); service behavior +
  duplicate-row + validation-message-safety + stamps-audit + leak-sweep
  + no-job-log-writes + internal-accessor-vs-write-path-denial +
  AST-based single-`sudo()` source guard (`test_credential_service.py`,
  10 tests).
- **Test execution status (stated honestly, per the Task 001A
  precedent):** this repository still has **no Odoo runtime, no
  `psycopg2`, no PostgreSQL, no `odoo-bin`, no CI** (re-confirmed this
  session). `test_credential_access.py` and `test_credential_service.py`
  (14 tests) require the Odoo ORM and were **written and
  `py_compile`-validated only — not executed.** `test_redaction.py` (7
  tests) targets a pure-Python utility with **zero Odoo dependency**;
  its test bodies were **extracted and actually executed directly
  against `tools/redaction.py` outside any Odoo harness — all 7
  passed** (this is real execution evidence, not just a compile check,
  though it is not the same as running the file as an installed Odoo
  test). The manual validation checklist in the final prompt is
  mandatory review evidence for the 14 ORM-dependent tests.
- **Source-level `sudo()` guard:** the naive literal-substring
  version of this test would have false-positived on the model
  docstring's own required prose explaining `sudo()` (the final
  prompt mandates that prose) — rewritten to an AST-based scan
  (`ast.Call`/`ast.Attribute(attr='sudo')`) that only counts real
  method-call sites; manually re-run standalone and confirmed exactly
  one real `.sudo()` call, inside `_get_access_token`.
- **No `job.log` writes; no encryption claim; no real token anywhere**
  (dummy tokens only, e.g. `shpat_DUMMYDUMMYDUMMY0000000000000000`);
  no `ir.config_parameter`; no raw SQL; zero API/UI/webhook/controller/
  cron/domain-logic content in the diff (grep-swept and confirmed).
- **Learning feedback loop:** new issue found and fixed in-session: the
  originally-drafted source-level `sudo()` guard test would have been a
  false-positive trap against this task's own mandatory docstring
  content — caught before commit, corrected to an AST-based check, not
  logged as a repeated defect-pattern-log category (design correction
  within the same task, not a recurring pattern). Rejected approaches:
  none reintroduced. Technical debt: none new — the redaction utility
  has no consumer inside Task 002's own shipped code (by design; its
  sink-side wiring is a named Task 003 concern per the accepted
  architecture).
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (N/A) ·
  technical debt logged (N/A, none new) · repeated-issue escalation
  applied (N/A) — all YES.
- **Stop condition:** stopped immediately after opening the draft PR,
  exactly as the final prompt requires — no merge, no ready-for-review,
  no Task 003, no further task.
- **Recommended next step:** ChatGPT reviews the Task 002 implementation
  PR against `credential-security-redaction-review-checklist.md` and
  `task-002-pre-implementation-review-checklist.md` §B. Task 003
  remains blocked until that review is accepted.

**Exact next-session prompt:**

> Apply ChatGPT's review decision for the Task 002 implementation PR.
> If accepted: this closes MBQ-04 fully (pending the acceptance patch)
> and unblocks preparing a Task 003 decision-closure package (API
> client shell, test connection) — its own separate gate-opening act
> is still required before any Shopify API call is authorized. If
> revision is requested: apply the requested fixes on the same PR,
> re-run the same validation sweep, and keep the PR draft.

---

### Task 002 Credential-Storage Gate-Opening Act — compact handoff (2026-07-07)

> **Docs-only gate-opening act — not Task 002, not code, not a research
> sprint.** Confirmed before starting: PR #94 merged into
> `Shopify-connector` (merge commit
> `03ffcb4dc949cd5137b589a6cdc33da9105de31d`, confirmed an ancestor of
> latest `Shopify-connector`); AR-025 Accepted (2026-07-07); the final
> Task 002 prompt accepted as gate-ready but not issued; the gate
> proposal accepted as proposed scope but not opened; Task 002/003 not
> started; working branch created from latest `Shopify-connector`.

- **Branch / PR:** `claude/task-002-gate-opening-act` → draft PR #96
  into `Shopify-connector`
  (https://github.com/AdamsOdoo/Adams/pull/96; remains draft, not
  merged).
- **Files changed:**
  `docs/07-implementation-plan/task-002-credential-storage-gate.md`
  (new — the gate-opening act itself),
  `docs/05-qa/architecture-review-log.md` (new AR-026 row, **Accepted**;
  gate-opening note appended), `docs/01-research/research-handoff.md`
  (this entry). **No addon/code file touched. No Python/XML/CSV/
  manifest/test/CI file created or modified. No credential/token/secret
  field, model, API client, setup wizard, or test-connection
  implementation created. No webhook/controller/cron/domain module
  created. PR #93's 8 files untouched.**
- **What changed:** **AR-026 accepted — the narrow Task 002
  credential-storage implementation gate is opened, effective once
  this PR merges into `Shopify-connector`.** The gate authorizes
  exactly one future coding session — Task 002 (Credential Storage,
  Masking, and Redaction Foundation) — using the exact contracts
  already accepted via AR-025 in
  `task-002-final-implementation-prompt.md` (referenced by path, not
  restated/duplicated). **This PR does not implement Task 002, does
  not create the credential model or any token field, and does not
  create any code** — the final prompt is not issued inside this PR.
- **Still forbidden:** API client; test connection; setup wizard;
  UI/views/menus/actions/wizards; webhooks/controllers/cron; product/
  customer/order/inventory/fulfillment; domain modules; external
  network calls; Task 003 (its four decision points remain open); any
  second task before ChatGPT reviews Task 002's implementation PR.
- **AR-026:** Accepted. **No implementation gate is opened until this
  PR merges. Task 002 is not started. Task 003 is not started.**
- **Learning feedback loop:** new issues: none. Repeated patterns: none
  new. Rules updated: none. Rejected approaches: none reintroduced.
  Technical debt: none new. Architecture concerns: none new — this act
  stays strictly inside the AR-025-accepted scope.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (N/A) ·
  technical debt logged (N/A) · repeated-issue escalation applied
  (N/A) — all YES.
- **Stop condition:** stopped immediately after opening the draft PR —
  no merge, no ready-for-review, no implementation, Task 002/003 not
  started.
- **Recommended next step:** ChatGPT reviews this gate-opening act; if
  accepted and merged into `Shopify-connector`, the gate is open and
  `task-002-final-implementation-prompt.md` is issued verbatim, in its
  own session, as the Task 002 coding session (that session's PR must
  remain draft until ChatGPT reviews it).

**Exact next-session prompt:**

> After this gate-opening act (AR-026) is merged into
> `Shopify-connector`, issue
> `docs/07-implementation-plan/task-002-final-implementation-prompt.md`
> verbatim as the Task 002 coding session — create
> `shopify.connector.store.credential`, the six store mirrors, the
> redaction utility, the four service methods, the one Admin-only ACL
> row, the enumerated tests, and the manifest version bump, exactly as
> specified, with zero deviation from the accepted contracts. Keep the
> resulting PR draft until ChatGPT reviews it.

---

### PR #94 Acceptance Patch — compact handoff (2026-07-07)

> **Applies ChatGPT's acceptance of PR #94 — not a new research
> session, not Task 002, not a gate opening.** Confirmed before
> editing: PR #94 head commit
> `4a243941f3542eb29664d5b9ee5bb0af2190cc39`; DEC-003 through DEC-020,
> `docs/04-decisions/README.md`, and `defect-pattern-log.md` untouched.

- **Branch / PR:** `claude/task-002-decision-gate-pack-0mlsgf` → draft
  PR #94 into `Shopify-connector`
  (https://github.com/AdamsOdoo/Adams/pull/94; remains draft, not
  merged).
- **Files changed:** the seven AR-025 package files only —
  `task-002-decision-closure.md` (new Acceptance section),
  `task-002-final-implementation-prompt.md` (acceptance note: binding,
  not issued), `task-002-gate-opening-proposal.md` (acceptance note:
  proposed scope accepted, gate not opened),
  `task-002-pre-implementation-review-checklist.md` (Status →
  Accepted), `architecture-review-log.md` (AR-025 row → **Accepted**;
  acceptance-patch note added),
  `master-blueprint-open-questions.md` (MBQ-04/05/44 AR-025 notes
  converted from proposed to accepted wording; **statuses unchanged**),
  `research-handoff.md` (this entry). **No addon/code file touched. No
  Python/XML/CSV/manifest/test/CI file created or modified. No
  credential/API/setup-wizard/test-connection implementation created.
  No webhook/controller/cron/domain module created.**
- **What changed:** **AR-025 is now Accepted by ChatGPT (2026-07-07),
  at decision/gate-preparation level only.** Decision 1: compute-blank
  no-read-back hardening **rejected for Task 002** — `access_token`
  stays a plain stored Char (`copy=False`, Admin-only `groups=`,
  Admin-only default-deny model ACL; no compute/inverse/raw SQL/
  hand-managed column/companion field; honest residual documented — no
  encryption claim). Decision 2: exactly one `token_variant` value
  (`offline_custom_app`) and one secret value (`access_token`); no
  client-credentials fields or refresh machinery; **MBQ-05 stays open**
  for the MVP acquisition-path decision and wizard copy. Decision 3:
  `granted_scopes` + `granted_scopes_checked_at` on
  `shopify.connector.store`, readonly mirrors, created by Task 002 with
  no writer, written by Task 003 later. The final Task 002
  implementation boundary is accepted; the **final prompt is accepted
  as gate-ready and binding but not issued**; the **gate proposal is
  accepted as the proposed scope but the gate is not opened**.
- **Still forbidden/not authorized:** API client, test connection,
  setup wizard, UI/views/menus/actions/wizards, webhooks/controllers/
  cron, product/customer/order/inventory/fulfillment, domain modules,
  external network calls, Task 003. The four Task 003-only decision
  points remain open. **No implementation gate opened. Task 002 not
  started. Task 003 not started. No code authorized.**
- **Register impact applied:** MBQ-04 remains **Partially resolved**
  (three Task 002 points decided; coding + four Task 003-round points
  outstanding); MBQ-05 remains **open** (containment accepted only);
  MBQ-44 status unchanged (ACL row text accepted for the final prompt;
  both residuals still open).
- **Learning feedback loop:** new issues: none. Repeated patterns:
  none new (no unsupported-claim or scope-creep occurrence). Rules
  updated: none. Rejected approaches: the Task-002-scoped compute-blank
  rejection is now ChatGPT-accepted with a named revisit condition
  (recorded in the decision-closure document and AR-025; scoped to
  Task 002, not a permanent architecture rejection). Technical debt:
  none new. Architecture concerns: none new.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (Task-002-
  scoped, recorded via AR-025 with revisit condition) · technical debt
  logged (N/A, none new) · repeated-issue escalation applied (N/A) —
  all YES.
- **Stop condition:** stopped immediately after pushing the acceptance
  patch and refreshing the PR body — no merge, no ready-for-review, no
  gate opened, no implementation.
- **Recommended next step:** the separate, explicit ChatGPT Task 002
  gate-opening act (per the accepted
  `task-002-gate-opening-proposal.md`), merged into
  `Shopify-connector`; only then is
  `task-002-final-implementation-prompt.md` issued verbatim as the
  Task 002 session.

**Exact next-session prompt:**

> Perform the Task 002 gate-opening act, if and only if ChatGPT has
> explicitly decided to open the gate: create the gate-opening document
> per the accepted
> `docs/07-implementation-plan/task-002-gate-opening-proposal.md`
> (AR-021 pattern — restating the seven gate conditions and the exact
> allowed/forbidden scope), docs-only, on a fresh branch from latest
> `Shopify-connector`, as a draft PR for ChatGPT confirmation. Still no
> code in that session. Task 002 implementation starts only after that
> gate PR is merged, in its own session, via the verbatim
> `task-002-final-implementation-prompt.md`.

---

### Task 002 Decision Closure & Gate-Preparation Sprint — compact handoff (2026-07-06)

> **Docs-only decision-closure and gate-preparation sprint for Task 002
> — not Task 002 itself; no code.** Confirmed before starting: PR #92
> merged into `Shopify-connector` (merged 2026-07-06; merge commit
> `f74aaf204745ce0087733870fe56bdda74bfa79a` = latest
> `origin/Shopify-connector`); AR-024 Accepted; Task 002 recommended
> but not authorized; working branch created from that merge commit.

- **Branch / PR:** `claude/task-002-decision-gate-pack-0mlsgf` → draft
  PR #94 into `Shopify-connector`
  (https://github.com/AdamsOdoo/Adams/pull/94; draft, not merged).
- **Files created:**
  `docs/07-implementation-plan/task-002-decision-closure.md` (AR-025
  decision package),
  `docs/07-implementation-plan/task-002-final-implementation-prompt.md`
  (complete copy-paste final §9 prompt — **not issued, not
  authorized**),
  `docs/07-implementation-plan/task-002-gate-opening-proposal.md`
  (proposed narrow gate act — **opens nothing**),
  `docs/05-qa/task-002-pre-implementation-review-checklist.md`.
  **Files updated:** `docs/05-qa/architecture-review-log.md` (new
  AR-025 row, **Proposed**),
  `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-04/
  05/44: explicitly *proposed* notes only, **no status changes**),
  `docs/01-research/research-handoff.md` (this entry). **No addon/code
  file touched. No Python/XML/CSV/manifest/test/CI file created or
  modified. No credential/token/secret field, model, API client, setup
  wizard, or test-connection implementation created. No webhook/
  controller/cron/domain module created. No implementation gate opened.
  Task 002/003 not started. DEC-003 through DEC-020,
  `docs/04-decisions/README.md`, and `defect-pattern-log.md` all
  unchanged.**
- **Decisions proposed (AR-025 — Proposed for ChatGPT review, not
  accepted):** (1) **compute-blank no-read-back hardening: reject for
  Task 002** — `access_token` stays a plain stored Char behind the two
  accepted access layers (Admin-only default-deny model ACL +
  field-level `groups=`), `copy=False`, service-written only; honest
  residual stated (Admin-group ORM/RPC read technically possible;
  `sudo()`/DB/backup read regardless; no encryption exists or is
  claimed); the full `res.users`-style variant is recorded with a
  revisit condition, and the watered-down companion-field variant is
  named as never acceptable. (2) **`token_variant`/MBQ-05: Option 2C**
  — Task 002 stores exactly one secret value with the single Selection
  value `offline_custom_app`; no `client_id`/`client_secret`/token
  cache/expiry; the dedicated credential model is the seam; the MVP
  acquisition-path decision stays open with ChatGPT (MBQ-05 not
  resolved). (3) **Scope snapshot on `shopify.connector.store`** —
  `granted_scopes` + `granted_scopes_checked_at` created in Task 002 as
  readonly mirrors with no writer until Task 003.
- **Official re-verification (2026-07-06, high-power mode per the task
  prompt):** three parallel official-source research passes
  (shopify.dev/help.shopify.com custom-app + client-credentials +
  expiring-token pages; odoo.com 19.0 ORM/security references;
  odoo/odoo 19.0 `res_users.py`/`base_data.sql` source) plus an
  adversarial re-fetch verification pass — 22 of 22 executed
  verification verdicts confirmed the claims verbatim; 3 verifier
  agents could not run (session limit) and their claims are
  independently corroborated by the accepted AR-022 notes and the other
  verifiers. New facts beyond AR-024: the legacy custom-app creation
  cutoff is officially dated ("Starting from January 1, 2026…",
  help.shopify.com) and admin-created custom-app credentials cannot be
  rotated (delete-and-recreate / uninstall-reinstall only); the
  December 2025 expiring-offline-token model (1-hour tokens + 90-day
  refresh tokens) is public-apps-only with custom/merchant apps
  exempt per two official changelogs.
- **AR-025:** Proposed. **No implementation. No gate opened.** The
  final prompt explicitly requires, before execution: AR-025 accepted
  **and** a separate, explicit ChatGPT gate-opening act merged.
- **Learning feedback loop:** new issues: none. Repeated patterns:
  none new (checked `defect-pattern-log.md` categories — no
  unsupported-claim or scope-creep occurrence; every platform statement
  in the package is officially cited or labelled an open question).
  Rules updated: none. Rejected approaches: none reintroduced
  (RA-001–RA-023 re-checked; the compute-blank rejection is a
  *proposed* Task-002-scoped rejection with a named revisit condition,
  routed through AR-025 for ChatGPT to log on acceptance). Technical
  debt: none new. Architecture concerns: none new — this package stays
  inside AR-022/AR-023/AR-024.
- **Quality gate confirmation:** handoff updated · feedback loop
  checked · learning captured · rejected approach logged (N/A — none
  reintroduced; proposed rejection routed via AR-025) · technical debt
  logged (N/A, none new) · repeated-issue escalation applied (N/A) —
  all YES.
- **Stop condition:** stopped immediately after opening the draft PR —
  no merge, no ready-for-review, no implementation, no gate opened,
  Task 002/003 not started.
- **Recommended next step:** ChatGPT reviews AR-025 (the decision
  closure, the final prompt, the gate proposal, and the checklist);
  then either (a) an acceptance patch (AR-025 → Accepted; register
  notes per the decision-closure §Register impact proposal) **plus a
  separate, explicit gate-opening act**, after which the final prompt
  is issued verbatim as the Task 002 session; or (b) revision of this
  package.

**Exact next-session prompt:**

> Apply ChatGPT's review decision for the Task 002 decision-closure and
> gate-preparation PR (AR-025). If accepted: apply the acceptance patch
> (AR-025 row → Accepted; MBQ-04/05/44 notes converted from proposed to
> accepted wording per `task-002-decision-closure.md` §Register impact
> proposal; handoff entry), and — only if ChatGPT also performs the
> separate, explicit gate-opening act in
> `task-002-gate-opening-proposal.md` — record that act; still no code
> in that session. If revision is requested: apply the requested
> revisions to the AR-025 package only. Task 002 implementation starts
> only afterwards, in its own session, via the verbatim
> `task-002-final-implementation-prompt.md`.

---

### PR #92 Acceptance Patch — compact handoff (2026-07-06)

> **Applies ChatGPT's acceptance of PR #92 — not a new research session,
> not Task 002.** Confirmed before editing: PR #92 branch
> `claude/credential-connection-foundation-planning` head commit
> `9cab4e60d7b402622eeee32fe4a0e3ede0c6950f`. DEC-003 through DEC-020
> confirmed unedited; `docs/04-decisions/README.md` and
> `defect-pattern-log.md` confirmed unedited/untouched.

- **Branch / PR:** `claude/credential-connection-foundation-planning` →
  draft PR #92 into `Shopify-connector` (not merged; remains draft).
- **Files changed:**
  `docs/03-architecture/credential-connection-api-client-planning.md`
  (new "Acceptance" section near the top),
  `docs/05-qa/architecture-review-log.md` (AR-024 row → Accepted; new
  "AR-024 Acceptance Patch" note appended),
  `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-04
  upgraded to implementation-planning level, still Partially resolved;
  MBQ-05/06/44/51/52/08 notes appended, no status change on those six),
  `docs/07-implementation-plan/task-002-credential-storage-redaction-proposed.md`
  (new Status/Acceptance note),
  `docs/07-implementation-plan/task-003-api-client-test-connection-proposed.md`
  (new Status/Acceptance note),
  `docs/05-qa/credential-security-redaction-review-checklist.md` (new
  Status note),
  `docs/07-implementation-plan/credential-connection-foundation-task-plan.md`
  (new Status note),
  `docs/01-research/research-handoff.md` (this entry). **No addon/code
  file touched. No Python/XML/CSV/manifest/test/CI file created or
  modified. No credential/token/secret field, model, API client, setup
  wizard, or test-connection implementation created. No
  webhook/controller/cron/domain module created. No implementation gate
  opened. Task 002/003 remain proposed only, not authorized. DEC-003
  through DEC-020 and `docs/04-decisions/README.md` unchanged.
  `defect-pattern-log.md` unchanged.**
- **What changed:** applied ChatGPT's acceptance decision for PR #92 —
  **AR-024 is now Accepted** (2026-07-06), at **implementation-planning
  level only**. The **credential/connection/API-client foundation
  planning package is accepted at implementation-planning level**:
  **Option C** — a dedicated Admin-only
  `shopify.connector.store.credential` model (one row per store, secret
  value on the credential model, non-secret status mirrors on `store`,
  Admin-only ACL with no rows for auditor/operator/reviewer, field-level
  `groups=` as a second layer, no unlink, no connector-surface read-back
  for any role including Admin) — **is accepted at planning level**,
  explicitly as **a justified post-AR-022/MBQ-04 addition to the
  previously accepted AR-019 six-core-model plan**. The
  **redaction/no-logging contract** (shared `redact()` utility,
  `SENSITIVE_KEYS`, `shpat_`/`shprt_` value patterns, exact-value scrub,
  source- and sink-side enforcement) **is accepted at planning level**.
  **Task 002 is accepted as the recommended next coding task — not
  authorized.** **Task 003 is accepted as the proposed follow-up task —
  not authorized**, including its planning-level API-client constraints
  (one core-owned GraphQL client boundary; read-only test-connection
  query; no mutations; no domain sync; no webhooks; no cron; no setup
  wizard UI). **No implementation gate is opened by this acceptance.**
- **Seven decision points remain explicitly open** (not decided by this
  acceptance): the compute-blank no-read-back hardening variant;
  `token_variant` vocabulary and the MBQ-05 acquisition-path direction;
  scope-snapshot placement; the `core_test_connection` job-type value;
  the `SHOP_INACTIVE`/402/423/403-fraudulent error-class mapping; the
  job-log system-append write path vs. ACL widening; the per-run
  `payload_hash` nonce for repeat target-less jobs.
- **Register impact applied:** MBQ-04 upgraded from posture level to
  **implementation-planning level**, **remaining Partially resolved, not
  fully resolved** — full closure requires Task 002's implementation to
  be reviewed and accepted; MBQ-05 records the official Shopify findings
  (new custom apps can no longer be created in the Shopify admin;
  existing admin-created apps continue to work; Dev Dashboard
  client-credentials grant returns 24-hour tokens) **without being
  prematurely resolved**; MBQ-06/44/51/52/08 receive planning-level notes
  with **no status change**.
- **No implementation gate opened by this acceptance.** No code, XML,
  view, model, field, credential, API client, test-connection, webhook,
  controller, cron, or domain module is authorized. Task 002/003 are not
  started.
- **Learning feedback loop:** new issues: none. Repeated patterns: none
  new (checked `defect-pattern-log.md` categories — no unsupported-claim
  or scope-creep occurrence). Rules updated: none. Rejected approaches:
  none reintroduced. Technical debt: none new. Architecture concerns:
  none new — this is an implementation-planning-level acceptance patch,
  not a new architecture decision.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged (N/A — none
  reintroduced) · technical debt logged (N/A, none new) ·
  repeated-issue escalation applied (N/A) — all YES.
- **Stop condition:** stopped immediately after pushing the acceptance
  patch — no merge, no implementation, no gate opened; PR #92 remains
  draft/open/not merged.
- **Recommended next step:** a separate, explicit ChatGPT gate-opening
  act and final `CLAUDE.md` §9 task prompt for Task 002 — not started by
  this acceptance.

**Exact next-session prompt:**

> Continue from the accepted PR #92 credential/connection/API-client
> foundation planning package (AR-024, accepted at implementation-planning
> level, 2026-07-06). Prepare a separate, explicit ChatGPT
> gate-opening act and final `CLAUDE.md` §9 task prompt for Task 002
> (credential storage, masking, redaction foundation), resolving its
> named decision points first (compute-blank hardening; `token_variant`
> vocabulary vs. MBQ-05; scope-snapshot placement) — still no code until
> that gate is explicitly opened.

---

### Credential/Connection/API Foundation Planning Sprint — compact handoff (2026-07-06)

> **Docs-only implementation-planning sprint for the credential /
> connection / test-connection / API-client / readiness foundation — the
> exact planning task AR-022 and the accepted UI/UX task map (Group 4)
> named as the required precursor to any credential code. Not Task 002;
> no code.** Confirmed before starting: PR #90 and PR #91 both merged;
> latest `Shopify-connector` includes PR #91 merge commit
> `143108585e802ee3e91d9f0c61f1828538734f47`; branch created from it.

- **Branch / PR:** `claude/credential-connection-foundation-planning` →
  draft PR #92 into `Shopify-connector`
  (https://github.com/AdamsOdoo/Adams/pull/92; draft, not merged).
- **Files changed:**
  `docs/03-architecture/credential-connection-api-client-planning.md`
  (new), `docs/07-implementation-plan/credential-connection-foundation-task-plan.md`
  (new), `docs/07-implementation-plan/task-002-credential-storage-redaction-proposed.md`
  (new), `docs/07-implementation-plan/task-003-api-client-test-connection-proposed.md`
  (new), `docs/05-qa/credential-security-redaction-review-checklist.md`
  (new), `docs/05-qa/architecture-review-log.md` (AR-024 row, Proposed),
  `docs/01-research/research-handoff.md` (this entry). **No addon/code
  file touched. No credential/token/secret field, model, API client,
  setup wizard, or test-connection implementation created. No
  webhook/controller/cron/domain module created. No gate opened. Task
  002 not started. DEC-003 through DEC-020, `docs/04-decisions/README.md`,
  `defect-pattern-log.md`, and `master-blueprint-open-questions.md` all
  untouched.**
- **What changed / produced:** (1) the architecture planning package —
  five storage options evaluated inside the accepted MBQ-04 Option B
  posture; **recommended (proposed only): a dedicated Admin-only
  `shopify.connector.store.credential` model** with non-secret status
  mirrors on `store`, no-read-back + masking rules, a
  `SENSITIVE_KEYS`/`shpat_`-pattern redaction contract, lifecycle
  semantics for the four store states, a read-only test-connection
  contract (`shop` + `currentAppInstallation.accessScopes` in one
  officially-cited GraphQL query), readiness mechanics for the accepted
  MBQ-06 essential set, and the `core`-owned API-client boundary
  (dual-path error normalization into the fixed 16 classes,
  throttle-signal surfacing, no pacing policy); (2) the foundation task
  plan (Tasks 002→005 sequenced, Task 006 wizard horizon behind the UI
  gate); (3) proposed-not-authorized §9-style Task 002 and Task 003
  specs; (4) the credential-security/redaction review checklist; (5)
  AR-024 (Proposed).
- **Official sources checked (access 2026-07-06, cited in the planning
  doc):** shopify.dev — admin-graphql reference, usage/versioning,
  usage/access-scopes, usage/limits, usage/response-codes,
  access-tokens (admin custom apps / offline / client-credentials /
  client-secret rotation), Dev Dashboard token guide,
  `currentAppInstallation`/`appInstallation`/`shop`/`Shop`/`AppInstallation`/`AccessScope`
  reference pages, and the 2020 missing-scope changelog; odoo.com 19.0
  developer docs (orm, security, view_architectures,
  restrict_data_access tutorial, on_premise/deploy) and odoo/odoo branch
  19.0 source (orm/models.py, orm/fields.py, orm/fields_textual.py,
  base/ir_ui_view.py, base/res_users.py). **Notable new facts:** Shopify
  has deprecated creating new custom apps in the Shopify admin (existing
  ones keep working; admin-created tokens rotate only by
  uninstall/reinstall); Dev Dashboard apps use a client-credentials
  grant with 24-hour tokens; the expiring-offline-token model explicitly
  excludes custom apps — all routed to MBQ-05, not decided here. Every
  unconfirmed behavior (THROTTLED body shape, invalid-token HTTP status,
  missing-scope shape, `shop`/`currentAppInstallation` scope
  requirements) is logged open, never asserted.
- **Items deferred:** the named ChatGPT decision points (compute-blank
  no-read-back variant; `token_variant` vocabulary vs MBQ-05;
  scope-snapshot placement; `core_test_connection` job-type value;
  `SHOP_INACTIVE`/402/423 class mapping; the job-log system-append
  write path — no group may create `job.log` rows under the merged ACL;
  the per-run `payload_hash` nonce for target-less jobs — repeat-run
  `idempotency_key` collision touching accepted AR-019 key semantics);
  the store/settings `perm_create` ACL gap (wizard-blocking, Task
  005/MBQ-44 residual); in-flight-job disposition at disconnect (Part A
  §I.4, unchanged); MBQ-06 thresholds/copy; a
  `/docs/00-source-materials` capture pass for this sprint's excerpts
  (outside allowed files).
- **Learning feedback loop:** new issues — (1) the merged Task 001 ACL
  grants no `perm_create` on store/settings to any group (surfaced,
  routed to MBQ-44 residual/Task 005; not a defect in Task 001's zero-UI
  scope); (2) the merged ACL grants no group create on `job.log`
  (correct for its system-appended intent, but every future log-writing
  path needs a decided write mechanism — surfaced as a named decision
  point); (3) a latent `(store_id, idempotency_key)` collision blocks
  repeat runs of target-less core jobs (`core_readiness_check`) —
  surfaced with a proposed per-run-nonce resolution; repeated patterns —
  none new (evidence-consistency gate honored: all platform facts cited
  or logged open); rules/checklists updated — new
  credential-security/redaction checklist proposed; new rejected
  approaches — none (options rejected here are proposal-level
  evaluations recorded in the planning doc, not RA-log rejections);
  technical debt — none created (docs-only); architecture concerns —
  AR-024 filed (Proposed); tests/review gates needed — the checklist's
  gates plus both task specs' test plans; future prompts — Yes: the
  exact next-session prompt is provided at the end of this entry. A
  six-lens adversarial self-review ran before commit and its findings
  (an unverified-historical one-time-reveal phrase inside a Fact bullet;
  a mislabelled docs-attribution on bucket-size reads; a quote-fidelity
  slip; the job.log and idempotency-key gaps above; assorted
  consistency/completeness fixes) were all patched before this PR.
- **Quality gate confirmation:** handoff updated YES · feedback loop
  checked YES · learning captured YES · rejected approach logged n/a
  (none) · technical debt logged n/a (none) · repeated-issue escalation
  applied n/a (none) — all satisfied.
- **Next recommended session:** ChatGPT review of PR (AR-024). If
  accepted: an acceptance-patch session applying the proposed register
  impact (MBQ-04 → implementation-planning level; MBQ-05 findings
  recorded/decided; MBQ-44 credential row shape + `perm_create`
  residual) and flipping AR-024 to Accepted; then, as a separate act, the
  Task 002 gate-opening + final §9 task prompt. If revised: a patch
  session on this branch.
- **Stop condition:** stopped after opening the draft PR. No code, no
  fields, no models, no views, no API client, no test connection, no
  wizard, no webhook/controller/cron/domain module; no gate opened; Task
  002/003 remain proposed-not-authorized; awaiting ChatGPT review.
- **Exact next-session prompt:**

  > ChatGPT has reviewed the Credential/Connection/API Foundation
  > Planning PR (AR-024, branch
  > `claude/credential-connection-foundation-planning`). Outcome:
  > **[ACCEPTED / ACCEPTED WITH CORRECTIONS / REVISE — paste ChatGPT's
  > decision and its resolutions of the named decision points:
  > compute-blank no-read-back variant; `token_variant` vocabulary /
  > MBQ-05 direction; scope-snapshot placement; `core_test_connection`
  > job-type value; `SHOP_INACTIVE`/402/423 class mapping; job-log
  > system-append write path; per-run `payload_hash` nonce]**. If
  > ACCEPTED: apply the acceptance patch on this same branch/PR —
  > update `docs/05-qa/architecture-review-log.md` (AR-024 row →
  > Accepted + acceptance-patch note), apply the planning document's
  > "Proposed register impact" wording to
  > `docs/03-architecture/master-blueprint-open-questions.md` (MBQ-04,
  > MBQ-05, MBQ-06, MBQ-44, MBQ-51, MBQ-52, MBQ-08 — exactly as accepted,
  > no other row), add Status/acceptance notes to the five new package
  > documents, and update `docs/01-research/research-handoff.md`.
  > Docs-only; no code; **this acceptance does not open the Task 002
  > gate** — the gate-opening act and the final Task 002 §9 prompt
  > remain separate, later ChatGPT acts. If REVISE: apply exactly the
  > requested corrections on this branch, update the handoff, and stop.
  > Allowed files: the seven files this sprint touched plus
  > `master-blueprint-open-questions.md` (accepted branch only). Do not
  > touch DEC-003–DEC-020, `docs/04-decisions/README.md`,
  > `defect-pattern-log.md`, addon code, `main`, or plain `dev`. Stop
  > after pushing and updating the PR; await ChatGPT.

---

### PR #91 Acceptance Patch — compact handoff (2026-07-06)

> **Applies ChatGPT's acceptance of PR #91 — not a new research session, not
> Task 002.** Confirmed before editing: PR #91 branch
> `claude/ui-ux-final-design-spec-6m44ux` head commit
> `e552a757db23bfae484c700599ad1b7a8602bdf0`. DEC-003 through DEC-020
> confirmed unedited; `docs/04-decisions/README.md`, `defect-pattern-log.md`,
> and `master-blueprint-open-questions.md` confirmed unedited/untouched.

- **Branch / PR:** `claude/ui-ux-final-design-spec-6m44ux` → draft PR #91
  into `Shopify-connector` (not merged; remains draft).
- **Files changed:** `docs/02-product/ui-ux-final-design-spec.md` (new
  "Acceptance" section near the top), `docs/05-qa/architecture-review-log.md`
  (new AR-023 row → Accepted; new "AR-023 Acceptance Patch" note appended),
  `docs/05-qa/ui-ux-design-review-checklist.md` (new "Status" note),
  `docs/07-implementation-plan/ui-ux-implementation-task-map.md` (new
  "Status" note), `docs/01-research/research-handoff.md` (this file). **No
  addon/module/code file touched. No DEC file changed. No
  `docs/04-decisions/README.md` change. No `defect-pattern-log.md` change.
  No `master-blueprint-open-questions.md` change. No Task 002 started. No
  credential/token/secret field, credential model, API client, setup
  wizard, test-connection code, webhook/controller/cron/domain-module code
  created.**
- **What changed:** applied ChatGPT's acceptance decision for PR #91 —
  **AR-023 is now Accepted** (2026-07-06); the **UI/UX Final Design
  Specification package is accepted at design-specification level**; the
  **Premium Simplicity Standard is accepted as the project's UI/UX quality
  bar** (clarity, confidence, polish, guidance, recovery — never more
  screens/colors/charts/complexity; no generic technical connector feel;
  errors must feel recoverable; dashboards must be high-signal and not
  cluttered); the **screen inventory/navigation map is accepted as the
  design-level screen map**; the **MVP user flows/state models are accepted
  as the design-level flow map**; the **UI/UX design-review checklist is
  accepted as the review checklist for future UI implementation review**;
  the **UI/UX implementation task map is accepted as planning guidance
  only, not task authorization**. The 7±2 visible field budget, the
  one-primary-action discipline, and the 10-second dashboard rule **remain
  proposal-level design disciplines**, not hard implementation gates,
  unless a later, separate ChatGPT act promotes them.
- **No UI implementation gate opened by this acceptance.** No code, XML,
  view, menu, action, wizard, field, model, credential, API client,
  test-connection, webhook, controller, cron, or domain module is
  authorized. Task 002 is not started. The only open gate remains the
  limited, core-only, zero-UI gate (Task 001).
- **Remaining open items (unchanged by this acceptance):** MBQ-03 (exact
  XML IDs); MBQ-22 (exact final copy); MBQ-44 residual (exact access
  rows); the MBQ-04 credential implementation-planning task (exact
  credential model/field/access-group/redaction/rotation/test-connection/
  rollback detail); whether the field/action-budget disciplines and the
  10-second dashboard rule become hard implementation gates; all Later
  premium candidates (activity chart, health score, audit timeline,
  recovery assistant) remain deferred unless separately accepted.
- **Learning feedback loop:** new issues: none. Repeated patterns: none
  new (checked `defect-pattern-log.md` categories — no unsupported-claim
  or scope-creep occurrence). Rules updated: none. Rejected approaches:
  none reintroduced. Technical debt: none new. Architecture concerns: none
  new — this is a design-specification-level acceptance patch, not a new
  architecture decision.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (N/A — none reintroduced) ·
  technical debt logged (N/A, none new) · repeated-issue escalation
  applied (N/A) — all YES.
- **Stop condition:** stopped immediately after pushing the acceptance
  patch — no merge, no implementation, no UI gate opened; PR #91 remains
  draft/open/not merged.
- **Recommended next step:** either (1) the MBQ-04 credential
  implementation-planning task (§9 template), or (2) a separate, explicit
  ChatGPT decision on when/whether to open a UI implementation gate for
  Group 1 (menu shell) per the accepted task map — neither is started by
  this acceptance.

**Exact next-session prompt:**

> Continue from the accepted PR #91 UI/UX Final Design Specification
> package (AR-023, accepted at design-specification level, 2026-07-06).
> Either (1) prepare the MBQ-04 credential implementation-planning task
> (exact model/field/access-group/redaction/rotation/test-connection/
> rollback detail, written to the `CLAUDE.md` §9 template, still no code),
> or (2) prepare a UI-implementation-gate-opening proposal for ChatGPT's
> review (Group 1 — menu shell — per the accepted task map), whichever
> ChatGPT directs. Do not start Task 002 or any code without a separate,
> explicit ChatGPT gate-opening act.

---

### UI/UX Final Design Sprint — compact handoff (2026-07-06)

> **Docs-only UI/UX design sprint — no implementation, no gate change, not
> Task 002.** Confirmed before starting: PR #90 merged into
> `Shopify-connector` (merge commit `ffe3500`, 2026-07-06) so the accepted
> MBQ-04 credential posture (Option B) informs the setup/credential/
> test-connection UX; branch started from latest `Shopify-connector`
> (`ffe3500`). DEC-003 through DEC-020 unedited;
> `docs/04-decisions/README.md` and `docs/05-qa/defect-pattern-log.md`
> unedited; `master-blueprint-open-questions.md` untouched.

- **Branch / PR:** `claude/ui-ux-final-design-spec-6m44ux` → draft PR into
  `Shopify-connector` (PR number/URL in the PR itself; remains draft,
  awaiting ChatGPT review).
- **Files created:**
  `docs/02-product/ui-ux-final-design-spec.md` (the main spec: Premium
  Simplicity Standard; UX principles; roles/surfaces; ~20 screen specs
  with full state models; 11-step setup wizard detail; dashboard design;
  error/recovery UX for 11 error types; illustrative microcopy; premium
  opportunities MVP-vs-Later; open items),
  `docs/02-product/screen-inventory-and-navigation-map.md` (24-row
  inventory; menu hierarchy; placeholder action assumptions; navigation
  paths; cross-links; role visibility matrix; combine-vs-separate
  rationale),
  `docs/02-product/mvp-user-flows-and-state-models.md` (nine MVP flows
  with happy/exception paths, terminal states, guards, audit events),
  `docs/05-qa/ui-ux-design-review-checklist.md` (strict gate checklist,
  §A–§M, incl. the per-screen premium-simplicity gate item),
  `docs/07-implementation-plan/ui-ux-implementation-task-map.md` (15
  future task groups with prerequisites/risk/must-not-dos/acceptance
  criteria/premium requirements + proposed sequencing). Plus this handoff
  update. **No addon/module/code file touched. No DEC file changed. No
  register row changed. No credential/API/setup-wizard/test-connection
  implementation created. No Task 002 started.**
- **Scope:** docs-only; translates DEC-012–DEC-020 + Master Blueprint
  Parts A–E + the MBQ-04 posture into implementation-ready screen specs.
  New design detail is labelled **[Design proposal — this spec]**; all
  copy is **[Illustrative — MBQ-22 open]**; nothing open is asserted as
  decided; the accepted vocabularies (7 sources / 10 states / 16 classes
  / 6 sub-reasons / 4 retry cases / 9 dashboard cards / 11 wizard steps /
  S1–S14) are reused verbatim and unextended.
- **Premium Simplicity Standard added** (design-spec §2): premium =
  clarity, confidence, polish, guidance, recovery — never more screens/
  colors/charts/complexity; includes field/action-budget disciplines,
  the 10-second dashboard rule, calm-error rules, and progressive
  disclosure tiers; enforced via the new QA checklist §L.
- **High-power mode note:** this sprint used a parallel multi-lens
  self-review workflow (governance/no-code, DEC-traceability, MBQ-status
  accuracy, premium-simplicity, deliverable-completeness lenses) over the
  five deliverables before commit; findings were patched in-session (see
  PR body self-review summary).
- **Key open items (recorded, not decided):** MBQ-03 XML IDs; MBQ-22
  final copy; MBQ-44 residual access rows; the MBQ-04
  implementation-planning task (credential internals); MBQ-05; MBQ-06
  residual thresholds; MBQ-32 quantity-**read mechanics** (the source
  itself is decided — `free_qty` semantics, AR-020) and MBQ-38
  confirmation-record schema; MBQ-56/27 (total-check detail); DEC-020
  residual (divergent-currency class mapping); MBQ-61; job/log retention
  policy; whether the field/action-budget disciplines become hard gates;
  Later premium candidates (activity chart, health score, audit
  timeline, recovery assistant) each need their own decision.
- **Learning feedback loop:** new issues: none. Repeated patterns: none
  new (checked `defect-pattern-log.md` categories — no unsupported-claim
  or scope-creep occurrence; per-class routing discipline from DEC-014
  point I applied throughout). Rules updated: none. Rejected approaches:
  none reintroduced (RA-006/008/009/013–023 checked; encoded as negative
  checks in the new QA checklist). Technical debt: none new.
  Architecture concerns: none new — the spec consumes decisions; the one
  tension worth ChatGPT's attention is that Part D §7 predates DEC-018,
  so the spec (not Part D) is now the most current UI reference for the
  decided items; Part D remains authoritative where they overlap.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (N/A — none reintroduced) ·
  technical debt logged (N/A, none new) · repeated-issue escalation
  applied (N/A) — all YES.
- **Stop condition:** stopped immediately after opening the draft PR, per
  the sprint instruction — no merge, no implementation, no gate change;
  awaiting ChatGPT review.
- **Recommended next step:** ChatGPT strict review of the draft PR
  (against `docs/05-qa/ui-ux-design-review-checklist.md`). After
  acceptance: (1) the MBQ-04 credential implementation-planning task
  (§9 template), and (2) a decision on when/whether to open the UI
  implementation gate for Group 1 (menu shell) per the task map — neither
  is started.

**Exact next-session prompt:**

> Review the UI/UX Final Design Specification draft PR (branch
> `claude/ui-ux-final-design-spec-6m44ux` into `Shopify-connector`)
> against `docs/05-qa/ui-ux-design-review-checklist.md` §A–§M. Verify:
> traceability of every screen statement to DEC-003–DEC-020 / Parts A–E /
> the MBQ-04 posture; correct open-vs-decided status for every MBQ cited;
> no implementation authorization; no invented API behaviour; MVP-vs-Later
> separation; and the Premium Simplicity Standard per screen. Return
> ACCEPT / ACCEPT WITH MINOR CHANGES / REVISE with findings. Do not open
> any implementation gate in the same act.

---

### MBQ-04 Acceptance Patch — compact handoff (2026-07-06)

> **Applies ChatGPT's acceptance of PR #90 — not a new research session, not
> Task 002.** Confirmed before editing: PR #90 branch
> `claude/mbq-04-credential-persistence-research` head commit
> `f8a353d8bc79954996ae31745a5f4b586352c1f0` (the F1/F2 REVISE-fix commit).
> DEC-003 through DEC-020 confirmed unedited; `docs/04-decisions/README.md`
> and `defect-pattern-log.md` confirmed unedited; only the MBQ-04 row (plus
> one new dated acceptance-patch note, no other row) changed in
> `master-blueprint-open-questions.md`.

- **Branch / PR:** `claude/mbq-04-credential-persistence-research` → draft PR
  #90 into `Shopify-connector` (not merged; remains draft).
- **Files changed:** `docs/03-architecture/mbq-04-credential-persistence-decision-proposal.md`
  (Status → Accepted; new "Acceptance" section; "Recommended decision" and
  "MBQ-04 classification" sections updated to reflect acceptance),
  `docs/05-qa/architecture-review-log.md` (AR-022 row → Accepted; new
  "AR-022 Acceptance Patch" note appended), `docs/03-architecture/master-blueprint-open-questions.md`
  (MBQ-04 row only, plus one new dated acceptance-patch note — no other MBQ
  row touched), `docs/01-research/research-handoff.md` (this file). **No
  addon/module/code file touched. No DEC file changed. No
  `docs/04-decisions/README.md` change. No `defect-pattern-log.md` change.
  No Task 002 started. No credential/token/secret field, credential model,
  API client, setup wizard, test-connection code, webhook/controller/cron/
  domain-module code created.**
- **What changed:** applied ChatGPT's acceptance decision for PR #90 —
  **AR-022 is now Accepted** (2026-07-06); **MBQ-04 is now Partially
  resolved**: the official-evidence blocker is resolved for the official
  Community/core Odoo 19 docs/source reviewed (no official Odoo 19
  Community/core field-level or ORM encryption-at-rest mechanism was found;
  every real official Odoo credential-field example uses plain storage with
  `groups=` access control and no field-level encryption; UI masking and
  access control are both confirmed not encryption; `sudo()`/superuser mode
  bypasses field-level `groups`; Odoo's corporate "Odoo Cloud" AES-256
  statement is infrastructure/platform-level, with its exact Odoo
  Online/Odoo.sh/on-premise applicability remaining an unconfirmed
  hosting-scope question); **Option B is accepted as the Phase 1/MVP
  credential-persistence posture** — a dedicated Odoo-managed credential
  field (or tightly coupled field set), plain storage + standard Odoo
  field/access controls, connector admin-equivalent `groups=`, view-level
  password masking, mandatory no-logging/redaction rule, no field-level
  encryption claim, no confirmed Odoo.sh/on-premise infrastructure-parity
  claim; Options D/E deferred, not rejected, as a possible future
  stronger-posture path. **This acceptance is posture-level only — no code,
  module, credential field, API client, setup wizard, or test-connection
  mechanism is created or authorized.** Exact model name, field name/type,
  access group, audit metadata, rotation/revocation behavior, test-connection
  behavior, redaction implementation, and rollback behavior all remain open,
  routed to a future implementation-planning task written to the
  `CLAUDE.md` §9 template.
- **Items deferred:** the future implementation-planning task itself (exact
  credential model/field/access-group/redaction/rotation/test-connection/
  rollback details) — not started this session; whether Odoo Enterprise/
  third-party/custom-encryption/external-secret-manager options exist
  (still out of scope, unchanged); whether Odoo's "Odoo Cloud" AES-256 claim
  specifically covers Odoo Online/Odoo.sh (still an open hosting-scope
  question, unchanged).
- **Learning feedback loop:** new issues: none. Repeated patterns: none new.
  Rules updated: none. Rejected approaches: none (checked
  `rejected-approaches-log.md`; Options D/E are named deferred, not
  rejected, so no new row logged). Technical debt: none new. Architecture
  concerns: none new beyond what the decision proposal already names.
  Tests/review gates needed: none (docs-only). Should future prompts
  change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (N/A) · technical debt logged
  (N/A, none new) · repeated-issue escalation applied (N/A) — all YES.
- **Next recommended session:** a separate, scoped implementation-planning
  task naming the exact credential model name, field name/type, access
  group XML ID, audit metadata, rotation/revocation behavior, test-connection
  behavior, and redaction implementation — written to the `CLAUDE.md` §9
  template, ChatGPT-reviewed before any code starts. Not Task 002 in the
  sense of coding; a planning-only session, same discipline as AR-019's
  core-naming-schema-planning precedent.
- **Stop condition:** stopped immediately after refreshing the PR body, per
  instruction. No merge performed. No implementation task started. No file
  outside the allowed list touched. PR #90 remains draft/open/not merged.

---

### MBQ-04 — Credential Persistence Research and Decision Proposal — compact handoff (2026-07-05)

> **Docs-only research and proposal session — not Task 002, not implementation.**
> Confirmed before editing: branch `claude/mbq-04-credential-persistence-research`
> created from `Shopify-connector` at merge commit
> `d27b836dcf2463438137446c5abe0fe61ef53793` (PR #89 merged). DEC-003 through
> DEC-020 confirmed unedited; `docs/04-decisions/README.md` and
> `defect-pattern-log.md` confirmed unedited; `master-blueprint-open-questions.md`
> deliberately left untouched (outside this session's allowed-files scope).

- **Branch / PR:** `claude/mbq-04-credential-persistence-research` → draft PR
  into `Shopify-connector` (not merged).
- **Files changed:** `docs/01-research/odoo-credential-storage-official-notes.md`
  (new), `docs/03-architecture/mbq-04-credential-persistence-decision-proposal.md`
  (new), `docs/05-qa/architecture-review-log.md` (AR-022 added, status
  **Proposed**), `docs/01-research/research-handoff.md` (this file). **No
  addon/module/code file touched. No DEC file changed. No
  `docs/04-decisions/README.md` change. No `defect-pattern-log.md` change. No
  `master-blueprint-open-questions.md` change. No Task 002 started. No
  credential/token/secret field, credential model, API client, setup wizard,
  test-connection code, webhook/controller/cron/domain-module code created.**
- **What changed / research completed:** ran a five-workstream official-source
  research pass (parallel agents, each independently adversarially
  re-verified) against Odoo 19.0 documentation and source
  (`odoo.com/documentation/19.0/**`, `raw.githubusercontent.com/odoo/odoo`
  branch `19.0`) covering: the `password` field/view attribute (found to be a
  **view-architecture UI-masking attribute, not an ORM storage/encryption
  mechanism**); `ir.config_parameter` (plain, unencrypted key-value storage,
  single `group_system`-only ACL, no official "secure secret store"
  characterization found); field-level `groups`/`ir.model.access`/`ir.rule`
  (access control only, explicitly **bypassed by `sudo()`/superuser mode even
  at the field-`groups` level**, per source); five real official Odoo
  credential-field examples (`ir.mail_server.smtp_pass`;
  Stripe/Adyen/Authorize.Net payment-provider secret keys;
  `iap.account.account_token`) — all identical plain-`Char` +
  `groups='base.group_system'`, no encryption; and encryption-at-rest (**no
  official Community/core Odoo 19 field-level mechanism found**; the only
  claim found anywhere is **infrastructure-level, AES-256, scoped by Odoo's
  corporate page to "Odoo Cloud"** — exact Odoo Online/Odoo.sh/on-premise
  applicability not separately confirmed, not field-level; Enterprise-only/
  third-party/custom-encryption/external-secret-manager options remain
  outside this evidence base unless separately researched). Wrote
  the full findings to `odoo-credential-storage-official-notes.md`
  (Fact/Official-source-code-fact/Inference/Open-question labelled throughout,
  per `CLAUDE.md` §8) and a decision proposal
  (`mbq-04-credential-persistence-decision-proposal.md`) evaluating five
  options (full descope; standard Odoo field + `groups`; `ir.config_parameter`;
  external secret manager; hybrid metadata-in-Odoo/secret-outside), **proposing
  (not deciding) Option B** — matching every real official Odoo credential-field
  example and DEC-004's already-accepted posture, no DEC-004 amendment needed —
  while naming Options D/E as a possible stronger-posture follow-up that would
  need its own separate evidence pass. Added AR-022 (`Proposed`, not
  `Accepted`) to `architecture-review-log.md`.
- **Official sources searched:** full list in
  `odoo-credential-storage-official-notes.md` "Sources searched" — headline
  pages: `developer/reference/backend/orm.html`,
  `developer/reference/user_interface/view_architectures.html`,
  `developer/reference/backend/security.html`,
  `developer/reference/external_api.html`, `administration/odoo_sh.html` (+9
  subpages), `administration/odoo_online.html`,
  `administration/on_premise/deploy.html`; official 19.0 source files
  `odoo/orm/fields.py`, `odoo/orm/models.py`,
  `odoo/addons/base/models/ir_config_parameter.py`,
  `odoo/addons/base/models/ir_mail_server.py`,
  `odoo/addons/base/models/res_users.py`, `ir.model.access.csv`, and the
  Stripe/Adyen/Authorize.Net/IAP/`auth_oauth` provider modules; plus Odoo's
  official corporate `odoo.com/security` and `odoo.com/gdpr` pages (first-party,
  not versioned developer docs, distinguished as such throughout). Access date
  2026-07-05 for every source.
- **Items deferred:** exact credential model/field names, access groups,
  rotation/revocation design, audit-metadata design, and test-connection
  behavior — all explicitly listed as "Required follow-up before coding" in
  the decision proposal, not decided this session; whether Odoo Enterprise,
  third-party modules, or custom application-side encryption offer any
  field-level encryption unavailable in the official Community/core docs/
  source reviewed (not checked, out of scope); whether Odoo's corporate "Odoo
  Cloud" AES-256 claim specifically covers Odoo Online, Odoo.sh, both, or
  on-premise (hosting-scope question, not confirmed either way).
- **Learning feedback loop:** new issues: none. Repeated patterns: none new —
  this session was itself the corrective action for the "unsupported
  assumption / weak research" pattern (DP-003/004/006) as it specifically
  applies to MBQ-04, closing the exact evidence gap AR-019/AR-020 named,
  through direct official-source fetches plus an independent adversarial
  verification pass on every risk-flagged (encryption/security/password)
  claim before inclusion. Rules updated: none. Rejected approaches: none
  (checked `rejected-approaches-log.md`; nothing in scope revisits a logged
  rejection; no new rejection logged this session either, since no option
  proposed here is being rejected outright — Options C/D/E are named
  "not recommended as primary" or "needs a further evidence pass," not
  rejected). Technical debt: none new. Architecture concerns: the credential
  storage/access-control-vs-encryption distinction from this session should
  inform DEC-004 implementation planning and any future App Store security
  review. Tests/review gates needed: none (docs-only). Should future prompts
  change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (N/A) · technical debt logged
  (N/A, none new) · repeated-issue escalation applied (N/A — this session
  closed the relevant gap rather than repeating it) — all YES.
- **Next recommended session:** ChatGPT review of this research and decision
  proposal — specifically whether to accept Option B (or another option) for
  MBQ-04, and whether to apply the proposed "Partially resolved" classification
  to `master-blueprint-open-questions.md` via an acceptance patch. No Task 002,
  no credential-model implementation, until that review completes.
- **Stop condition:** stopped immediately after opening the draft PR, per
  instruction. No merge performed. No second task started. No file outside
  the allowed list touched.

_**PR #90 Revision (2026-07-05) — ChatGPT returned REVISE, not Reject.** Two
precision issues (F1, F2) were fixed in `odoo-credential-storage-official-notes.md`
and `mbq-04-credential-persistence-decision-proposal.md` (and in this handoff
entry, above): **F1** — narrowed every "Odoo 19 provides no built-in
field-level encryption-at-rest" / "definitive answer" / "evidence resolved in
full" style absolute claim to "no official Odoo 19 **Community/core**
field-level or ORM encryption-at-rest mechanism was found in the official
docs/source **reviewed**," with an explicit statement that Enterprise-only
modules, third-party modules, custom application-side encryption, and
external secret managers remain outside this evidence base unless separately
researched (this gap was already named in "What is not confirmed"/Open
questions but the headline conclusions did not consistently carry the same
caveat — now fixed throughout). **F2** — removed every gloss asserting
"Odoo Cloud (Odoo Online/Odoo.sh)" coverage or "Odoo.sh/Odoo Online get the
AES-256 claim"; the corporate `odoo.com/security` page's own scope is the
umbrella term "Odoo Cloud (the platform)," and the versioned Odoo.sh/Odoo
Online administration docs checked contain **no** encryption-at-rest
statement of their own — exact Odoo Online/Odoo.sh/on-premise applicability
is now stated as an open hosting-scope question throughout, not asserted
either way. **No scope/structure/evidence-base change** — ChatGPT explicitly
did not reject the research; only these two wording precisions were applied.
AR-022 remains `Proposed` (not changed to `Accepted`); `master-blueprint-
open-questions.md` remains untouched; PR #90 remains draft. Commit: "docs:
narrow MBQ-04 credential evidence claims."**_

---

### Task 001A — Core Runtime Readiness & QA Closure — compact handoff (2026-07-05)

> **Post-merge QA closure of Task 001 — not Task 002, not new code.**
> Confirmed before editing: branch `claude/task-001a-core-runtime-readiness`
> created from `Shopify-connector` at merge commit
> `b55490743fb1f5c9ea33831b94605b9ead4229c0` (PR #88, "Task 001: Add
> Shopify connector core scaffold", merged). DEC-003 through DEC-020
> confirmed unedited; `docs/04-decisions/README.md` and
> `defect-pattern-log.md` confirmed unedited.

- **Branch / PR:** `claude/task-001a-core-runtime-readiness` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:** `docs/05-qa/task-001-core-runtime-readiness.md` (new),
  `docs/01-research/research-handoff.md` (this file). **No module file
  under `addons/shopify_connector_core/` changed. No DEC file changed. No
  `docs/04-decisions/README.md` change. No `defect-pattern-log.md` change.
  No Task 002 started. No credential/token/secret field, Shopify API/
  webhook/controller code, cron data, or menu/action/view/wizard XML
  added.**
- **What changed / residue fixed:** re-validated the merged
  `shopify_connector_core` scaffold as a QA closure of Task 001: re-ran
  Python compile, manifest `ast.literal_eval` parse, security-XML
  well-formedness parse, and a CSV structural/referential check on
  `ir.model.access.csv` (20 rows = 5 concrete models × 4 groups, all
  resolving correctly, abstract `binding.mixin` correctly excluded); ran a
  targeted grep sweep for credential/token/secret/API/webhook/controller/
  cron/menu/view/wizard content — no matches beyond doc-string prose and
  the pre-existing schema-only `job_source='webhook'` label and
  `webhook_ready` boolean (both already accepted in the Task 001 entry
  below). Confirmed no Odoo runtime, test framework, or CI exists anywhere
  in this repository (no `odoo` package, no `psycopg2`, no `odoo-bin`, no
  Docker/CI config, empty `addons/requirements.txt`) — unchanged from Task
  001. Wrote `docs/05-qa/task-001-core-runtime-readiness.md` recording all
  of the above plus a 20-step manual Odoo 19 validation checklist for a
  reviewer with a live instance.
- **Tests:** **none added.** No `tests/` directory or Odoo test convention
  exists anywhere in this repo (checked `shopify_connector_core` and the
  only other module, `adams_base`, which is an empty scaffold); no Odoo
  runtime exists to execute a `TransactionCase` against; inventing a
  non-Odoo test harness is explicitly out of scope. This matches the same
  conclusion already recorded in the Task 001 entry below — nothing has
  changed on the runtime/CI front since then.
- **Items deferred:** live `-i shopify_connector_core` install and
  ORM-level constraint verification (still blocked on no Odoo runtime in
  this environment — same item already deferred at Task 001); the
  write-time-immutability-vs-`readonly=True` gap (same item already
  deferred at Task 001, unchanged).
- **Learning feedback loop:** new issues: none. Repeated patterns: "no Odoo
  runtime available in this environment" recurs for a second consecutive
  session (Task 001, now Task 001A) — logged here as a repeated pattern
  per `quality-feedback-loop.md` §4, but not escalated further since it is
  an environment-provisioning gap outside this session's authority to fix,
  not a defect in the work itself. Rules updated: none. Rejected
  approaches: none (checked `rejected-approaches-log.md`; nothing in this
  session's scope revisits a logged rejection). Technical debt: none new
  beyond what Task 001 already flagged. Architecture concerns: none new.
  Tests/review gates needed: same as Task 001 — real Odoo-runtime tests
  once a test framework/CI is authorized and provisioned. Should future
  prompts change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked ·
  learning captured · rejected approach logged (N/A) · technical debt
  logged (N/A, none new) · repeated-issue escalation applied (noted, not
  escalated — see above) — all YES.
- **Next recommended session:** ChatGPT review of this QA closure and of
  Task 001's runtime-readiness recommendation. No Task 002 until that
  review completes.
- **Stop condition:** stopped immediately after opening the draft PR, per
  instruction. No merge performed. No second task started. No file outside
  the allowed list touched.

---

### Task 001 — F1 fix (operation_scope_key not cleared on supersede) — compact handoff (2026-07-05)

> **Revision commit on PR #88, per ChatGPT REVISE review.** Confirmed
> before editing: PR #88 head commit `811c168f8d4bbed1de5660b16272ee38c2712ffc`
> (branch `claude/task-001-core-module-scaffold-coesxy`, based on
> `Shopify-connector` at PR #87 merge commit
> `dad9bfd6be5d1c7db939bb5132875ce6e8674368`).

- **Branch / PR:** `claude/task-001-core-module-scaffold-coesxy` → PR #88
  into `Shopify-connector` (**draft, not merged**).
- **Files changed:** `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `docs/01-research/research-handoff.md` (this file). **No other file
  touched. No DEC file changed. No `docs/04-decisions/README.md` change.
  No `defect-pattern-log.md` change. No Task 002 started. No credential/
  token/secret field, Shopify API/webhook/controller code, cron data, or
  menu/action/view/wizard XML added.**
- **What changed / residue fixed:** **F1** — ChatGPT's review found that
  `_compute_operation_scope_key()` cleared `operation_scope_key` on
  reaching a terminal state or on a missing `res_model`, but not when a
  job is superseded (`superseded_by_job_id` set), contradicting the
  accepted AR-019 §8 rule ("populated while the job is non-terminal...
  set to NULL on reaching a terminal state **or being superseded**").
  Fixed by adding `superseded_by_job_id` to the method's `@api.depends`
  and to the clearing condition, so a superseded job's
  `operation_scope_key` is set to `False`/NULL exactly like a terminal
  job's, freeing the `(store_id, operation_scope_key)` unique constraint
  for the superseding job. Terminal-state clearing and missing-`res_model`
  clearing behavior are unchanged; the docstring comment was updated to
  say "terminal state or being superseded."
- **Items deferred:** none new — the two known limitations already noted
  in the prior Task 001 entry (no live Odoo runtime in this environment;
  `payload_hash`'s own hashing/normalization algorithm remains an open,
  implementation-time detail) still stand.
- **Learning feedback loop:** new issues: F1 (operation_scope_key not
  cleared on supersede) was caught by ChatGPT review, not by this
  session's own static checks, since no Odoo runtime exists here to
  exercise the compute method against a live `superseded_by_job_id`
  write — logged as a gap in what static verification alone can catch on
  this repository. Repeated patterns: none. Rules updated: none.
  Rejected approaches: none. Technical debt: none new. Architecture
  concerns: none new. Tests/review gates needed: same as before — a
  future session should add a real Odoo-runtime test for this exact
  supersede-clears-scope-key behavior once a test framework/CI is
  authorized. Should future prompts change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged (N/A) · technical debt
  logged (N/A) · repeated-issue escalation applied (N/A) — all YES.
- **Next recommended session:** ChatGPT re-review of PR #88 for F1
  resolution. No Task 002 until this PR is accepted.
- **Stop condition:** stopped after pushing the F1 fix commit and
  refreshing the PR body/head SHA. No merge performed. PR #88 remains
  draft.

---

### Task 001 — Core Module Scaffold implemented — compact handoff (2026-07-05)

> **First coding PR for this project.** Confirmed before editing: branch
> based on `Shopify-connector` at merge commit
> `dad9bfd6be5d1c7db939bb5132875ce6e8674368` (PR #87, "Limited core
> implementation gate — accepted"); limited core-only zero-UI gate open
> for exactly Task 001
> (`docs/07-implementation-plan/limited-core-implementation-gate.md`,
> `docs/07-implementation-plan/task-001-core-module-scaffold.md`); schema
> source of truth `docs/07-implementation-plan/core-naming-schema-planning.md`
> (AR-019, accepted) and `docs/05-qa/architecture-review-log.md` (AR-019,
> AR-021, both accepted). DEC-003 through DEC-020 confirmed unedited;
> `docs/04-decisions/README.md` unedited.

- **Branch / PR:** `claude/task-001-core-module-scaffold-coesxy` → PR #88
  into `Shopify-connector` (**draft, not merged**).
- **Files changed:** `addons/shopify_connector_core/__init__.py`,
  `addons/shopify_connector_core/__manifest__.py`,
  `addons/shopify_connector_core/models/__init__.py`,
  `addons/shopify_connector_core/models/shopify_connector_store.py`,
  `addons/shopify_connector_core/models/shopify_connector_store_settings.py`,
  `addons/shopify_connector_core/models/shopify_connector_location.py`,
  `addons/shopify_connector_core/models/shopify_connector_binding_mixin.py`,
  `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `addons/shopify_connector_core/models/shopify_connector_job_log.py`,
  `addons/shopify_connector_core/security/ir.model.access.csv`,
  `addons/shopify_connector_core/security/shopify_connector_security.xml`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003
  through DEC-020 file changed. No `docs/04-decisions/README.md` change.
  No `defect-pattern-log.md` change. No second implementation task
  started. No credential/token/secret field, Shopify API/webhook/
  controller code, cron data, or menu/action/view/wizard XML created.**
- **What changed / residue fixed:** created the minimal installable
  `shopify_connector_core` module scaffold with exactly the six
  AR-019-accepted core models — `shopify.connector.store`,
  `.store.settings`, `.location`, `.binding.mixin` (abstract), `.job`,
  `.job.log` — implementing only the AR-019 §3/§4/§6/§7/§8/§12 field
  schema, uniqueness/FK/selection constraints, and the four
  `group_shopify_connector_*` access groups + `ir.model.access.csv` rows
  from §10. `idempotency_key` and `operation_scope_key` are implemented
  as distinct computed+stored fields (kept from colliding by design, per
  §8). No views/menus/actions, no Shopify API/webhook/controller code, no
  cron data, no credential field.
- **Tests:** none added — this repository has no existing Odoo test
  framework, CI, or runnable Odoo instance (`addons/adams_base` is an
  empty scaffold with no `tests/` directory; no `odoo-bin`, no
  `psycopg2`, no Odoo package installed in this environment), so per the
  task's explicit instruction no test structure was invented. Manual
  verification performed instead: `python3 -m py_compile` on every
  `.py` file; `ast.literal_eval` parse of `__manifest__.py` confirming a
  valid dict with `installable=True` and `depends=['base']`;
  `xml.dom.minidom` well-formedness parse of the security XML plus a
  cross-check that its four `res.groups` records match every
  `group_id:id` referenced in `ir.model.access.csv`; a CSV structural
  check confirming exactly 20 rows, one per (accepted model × group),
  permission bits restricted to `0`/`1`, and every `model_id:id` matching
  one of the five concrete accepted models (the abstract
  `binding.mixin` correctly has no access row); a targeted grep sweep for
  credential/token/secret/password/API-key patterns, HTTP/GraphQL/
  webhook-controller code, `ir.cron`, and menu/action/view/wizard XML —
  none found (the only hits are the `job_source` Selection value
  `'webhook'` and the `webhook_ready` readiness boolean, both schema-only
  labels, not implementation).
- **Items deferred:** live `-i shopify_connector_core` install/ORM
  smoke test (no Odoo runtime available in this environment); stricter
  "immutable after first save" write-time enforcement for fields AR-019
  marks "readonly after create" (implemented only as the Odoo field-level
  `readonly=True` attribute, since AR-019 §12's explicit required-
  constraints list names uniqueness/FK/selection-consistency only, not
  immutability guards — flagged for a future architecture pass if
  stricter enforcement is wanted); the exact `payload_hash`
  hashing/normalization algorithm (AR-019 §8 leaves this an
  implementation-time detail for whichever domain module first needs
  it — `idempotency_key`/`operation_scope_key` themselves are
  implemented as deterministic pipe-joined string composition per the
  AR-019 §8 component tuples).
- **Learning feedback loop:** new issues: none. Repeated patterns: none.
  Rules updated: none. Rejected approaches: none newly logged (checked
  `rejected-approaches-log.md`; RA-011/RA-012/RA-013 already cover the
  module-boundary reasoning this scaffold follows). Technical debt: the
  two deferred items above should be logged in
  `technical-debt-register.md` if ChatGPT wants them tracked formally.
  Architecture concerns: none new. Tests/review gates needed: a future
  session should add real Odoo-runtime tests once a test framework/CI is
  authorized. Should future prompts change? No.
- **Quality gate confirmation:** handoff updated · feedback loop checked
  · learning captured · rejected approach logged (none new; N/A) ·
  technical debt logged (not yet — flagged above for ChatGPT/next
  session) · repeated-issue escalation applied (N/A) — all other items
  YES.
- **Next recommended session:** ChatGPT review of this PR against
  `task-001-core-module-scaffold.md`'s acceptance criteria. No Task 002
  (or any other task) may start until this review completes
  (`limited-core-implementation-gate.md` §5).
- **Stop condition:** stopped immediately after opening the draft PR, per
  instruction. No merge performed. No second task started. No file
  outside the allowed list touched.

---

### Limited Core Implementation Gate accepted — compact handoff (2026-07-05)

> **Documentation-only acceptance patch — not implementation, not code.**
> Confirmed before editing: PR #87 head commit
> `a43b6cbe8ce479ecb08628022dd5fe9ea4fbe9b4` (branch
> `claude/open-limited-core-gate-bidt3v`, based on `Shopify-connector` at
> PR #86 merge commit `c9698a70374e5f735f51c1de623c079dc5fd8697`);
> DEC-003 through DEC-020 confirmed Accepted and unedited; AR-021
> confirmed previously Proposed for ChatGPT review.

- **Branch / PR:** `claude/open-limited-core-gate-bidt3v` → PR #87 into
  `Shopify-connector` (**draft, not merged** — kept draft per instruction).
- **Files changed:**
  `docs/07-implementation-plan/limited-core-implementation-gate.md`
  (Status → Accepted; Acceptance section added; §2/§6 marked
  accepted/merge-gated), `docs/07-implementation-plan/task-001-core-module-scaffold.md`
  (Status → authorized after PR #87 merge, start gated on merge),
  `docs/05-qa/architecture-review-log.md` (AR-021 row and note moved to
  Accepted; AR-002 through AR-020 untouched),
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (compact note updated to accepted), `docs/01-research/research-handoff.md`
  (this file). **No DEC-003 through DEC-020 file changed. No
  `docs/04-decisions/README.md` change. No `defect-pattern-log.md`
  change. No Python/XML/manifest/security CSV/test/CI file created or
  changed. No Odoo module directory created. No second implementation
  task created.**
- **What changed:** **ChatGPT accepted the limited core implementation
  gate substance on 2026-07-05. AR-021 is now Accepted.** The limited,
  core-only, zero-UI implementation gate (scoped to
  `shopify_connector_core` only) **opens once PR #87 is merged into
  `Shopify-connector`** — it is not open before that merge. **AR-018's
  criterion 5 is confirmed for this limited gate only**: the
  `defect-pattern-log.md` DP-003/004/006 occurrence-counter row's
  recorded evidence-consistency gate satisfies the prevention-rule
  requirement for this gate; this does not apply project-wide and does
  not waive evidence requirements for later gates (product/customer/sale,
  inventory, fulfillment, UI, credentials/API). **Task 001 — Core Module
  Scaffold — is authorized as the only implementation task, starting only
  after PR #87 is merged.** No second task is authorized. **No code
  created in this PR. Implementation itself is not started in this PR.**
  No credentials, external API calls, operator-facing UI, or
  product/customer/order/inventory/fulfillment domain logic is
  authorized.
- **Gate state:** accepted, opens on merge of PR #87 — not open yet.
  No implementation task has started coding; no code, module, view,
  controller, security file, manifest, test, or CI file exists.
- **Learning feedback loop:** **New issues discovered:** none new this
  session. **Repeated issue patterns:** none triggered. **Rules/checklists
  updated:** none (out of allowed-files scope; `defect-pattern-log.md` is
  not edited — its DP-003/004/006 row is cited, not relabeled). **New
  rejected approaches:** none. **New technical debt:** none (no code).
  **New open questions:** none — no MBQ row is touched by this session.
  **Architecture concerns:** none — no accepted DEC/AR/blueprint design
  content changed; this is a status/acceptance patch.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured · rejected approaches checked, none
  added · technical debt logged (none applicable) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** once PR #87 is merged, run Task 001's own
  coding PR (the `shopify_connector_core` module scaffold implementation),
  scoped exactly to `task-001-core-module-scaffold.md`'s allowed files,
  forbidden files, acceptance criteria, and required tests. **Not
  performed by this session; PR #87 remains open/draft/not merged.**
- **Stop condition:** stopped after pushing this acceptance patch to the
  existing PR #87 branch (kept draft, not merged). `main` and plain `dev`
  untouched; only the five allowed files changed.

---

### Limited Core Implementation Gate proposed — compact handoff (2026-07-05)

> **Documentation-only gate-opening proposal — not implementation, not
> yet accepted.** Confirmed before editing: branch created from
> `Shopify-connector` at PR #86 merge commit
> `c9698a70374e5f735f51c1de623c079dc5fd8697`; DEC-003 through DEC-020
> confirmed Accepted and unedited; AR-020 confirmed Accepted at
> planning-closure level with zero MBQ rows blocking the limited
> core-only zero-UI gate; implementation confirmed still blocked prior to
> this session.

- **Branch / PR:** `claude/open-limited-core-gate-bidt3v` → draft PR into
  `Shopify-connector` (draft, not merged).
- **Files changed:**
  `docs/07-implementation-plan/limited-core-implementation-gate.md`
  (new), `docs/07-implementation-plan/task-001-core-module-scaffold.md`
  (new), `docs/05-qa/architecture-review-log.md` (AR-021 row + note
  added; AR-001 through AR-020 untouched),
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (compact status note appended), `docs/01-research/research-handoff.md`
  (this file). **No DEC-003 through DEC-020 file changed. No
  `docs/04-decisions/README.md` change. No Python/XML/manifest/security
  CSV/test/CI file created or changed. No Odoo module directory created.**
- **What changed:** Limited core gate-opening proposal prepared. AR-021
  proposed. Task 001 spec created. Proposes, pending ChatGPT review: (1)
  confirming AR-018's criterion-5 ambiguity — the DP-003/004/006
  `ESCALATED` occurrence-counter row's recorded evidence-consistency gate
  is confirmed to satisfy the prevention-rule requirement, for this
  limited core gate only; (2) opening a limited, core-only, zero-UI
  implementation gate scoped to `shopify_connector_core` (module
  scaffold, the six AR-019-accepted core models, groups/access CSV, core
  constraints/indexes, core tests; no credentials, no external API calls,
  no webhooks, no setup wizard, no test connection, no domain logic, no
  dashboard/sync-center/error-center UI); (3) authorizing exactly one
  implementation task, Task 001 (Core Module Scaffold), written to the
  `CLAUDE.md` §9 template. **No code created. Implementation not started
  in this PR.**
- **Gate state:** proposed, pending ChatGPT review/merge of this PR — the
  gate is only genuinely open once this PR is accepted. No implementation
  task has been authorized to start coding yet; no code, module, view,
  controller, security file, manifest, test, or CI file exists.
- **Learning feedback loop:** **New issues discovered:** none new this
  session. **Repeated issue patterns:** none triggered. **Rules/checklists
  updated:** none (out of allowed-files scope; `defect-pattern-log.md` is
  not touched by this session — its DP-003/004/006 row is read and cited,
  not edited). **New rejected approaches:** none. **New technical debt:**
  none (no code). **New open questions:** none — no MBQ row is touched by
  this session (`master-blueprint-open-questions.md` is out of this
  session's allowed-files scope). **Architecture concerns:** none — no
  accepted DEC/AR/blueprint design content changed; this is a
  gate-opening proposal plus one task specification.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured · rejected approaches checked, none
  added · technical debt logged (none applicable) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** after ChatGPT accepts/merges this PR, run
  Task 001's own coding PR (the `shopify_connector_core` module scaffold
  implementation), scoped exactly to
  `task-001-core-module-scaffold.md`'s allowed files, forbidden files,
  acceptance criteria, and required tests. **Not performed by this
  session.**
- **Stop condition:** stopped after opening this draft PR against
  `Shopify-connector`. `main` and plain `dev` untouched; only the five
  allowed files changed; awaiting ChatGPT's review/acceptance of the gate
  proposal and AR-021.

---

### Final MBQ Closure Plan accepted — compact handoff (2026-07-05)

> **Documentation-only acceptance patch — not implementation, not a
> gate-opening act.** Confirmed before editing: PR #86 head commit
> `4d0e1fddb36736e88281232d0f8b285c11b2dc3d` (branch
> `claude/odoo-shopify-planning-closure-ri64vv`, based on
> `Shopify-connector` at PR #85 merge commit `2e6842b`); DEC-003 through
> DEC-020 confirmed Accepted and unedited; AR-020 confirmed previously
> Proposed for ChatGPT review; implementation confirmed still blocked.

- **Branch / PR:** `claude/odoo-shopify-planning-closure-ri64vv` → PR #86
  into `Shopify-connector` (draft, not merged).
- **Files changed:**
  `docs/07-implementation-plan/final-mbq-closure-plan.md` (Status →
  Accepted; Acceptance section added; §4/§7/§8/§11 marked accepted/
  applied), `docs/05-qa/architecture-review-log.md` (AR-020 row and note
  moved to Accepted; AR-002 through AR-019 untouched),
  `docs/03-architecture/master-blueprint-open-questions.md` (plan §7
  wording applied to exactly the 50 reviewed rows + top acceptance-patch
  note — **no other row touched**),
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (status note updated to accepted), `docs/01-research/research-handoff.md`
  (this file). **No DEC-003 through DEC-020 file changed. No
  `docs/04-decisions/README.md` change. No code/Python/XML/manifest/
  security/test/CI file changed. No implementation task created. No
  module scaffolding created.**
- **What changed:** **ChatGPT accepted the Final MBQ Closure Plan on
  2026-07-05, at planning-closure level only. AR-020 is now Accepted.**
  The MBQ register is updated for all 50 reviewed rows: **2 Resolved**
  (MBQ-29, MBQ-35), **27 Partially resolved** with named task-spec
  residuals (MBQ-06/08/09/14/17/18/23/24/25/30/32/33/34/36/38/40/41/42/
  43/44/52/53/54/59/60/64/65), **17 descoped from MVP / first gate**
  (MBQ-03/04/05/10/13/15/22/27/46/48/49/51/55/56/57/61/63), **4
  accepted-open risks with containment** (MBQ-12/28/50/58). **Zero MBQ
  rows remain blocking the limited, core-only, zero-UI implementation
  gate.**
- **Gate state:** **the implementation gate remains closed;
  implementation remains blocked; no code was created; no implementation
  task was created; nothing is authorized by this acceptance.** Register
  closure is planning closure, not a gate act.
- **Learning feedback loop:** **New issues discovered:** none new this
  session (the `/docs/00-source-materials` capture follow-up from the
  proposal session remains logged, plan §10 risk 10 — still pending, now
  assignable to any next documentation session). **Repeated issue
  patterns:** none triggered. **Rules/checklists updated:** none (out of
  allowed-files scope). **New rejected approaches:** none. **New
  technical debt:** none (no code). **New open questions:** none — the
  two MBQ-09 residuals were already recorded in the applied §7 wording.
  **Architecture concerns:** none — no accepted DEC/AR/blueprint design
  content changed; this is a status/acceptance patch.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured · rejected approaches checked, none
  added · technical debt logged (none applicable) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** the **separate, explicit ChatGPT acts**
  the accepted plan names, in order: (1) confirm AR-018's criterion-5
  reading (DP-003/004/006 prevention-rule status), (2) the limited
  core-only, zero-UI gate-opening act (`shopify_connector_core` only —
  module skeleton, manifest/init, the six accepted core models,
  groups/access CSV, core constraints, core tests; no webhooks, no
  external API calls, no credential persistence, no setup wizard, no
  domain logic), (3) only then, the first implementation task written to
  the `CLAUDE.md` §9 template. **None of these was performed this
  session.**
- **Stop condition:** stopped after pushing this acceptance patch to the
  existing PR #86 branch (kept draft, not merged). `main` and plain `dev`
  untouched; only the five allowed files changed; awaiting the separate
  ChatGPT gate decision.

---

### Final MBQ Closure Plan proposed — compact handoff (2026-07-05)

> **Documentation-only, planning-closure-only proposal — not
> implementation, not a gate-opening act.** Confirmed before starting:
> PR #85 merged into `Shopify-connector` at merge commit `2e6842b`;
> DEC-003 through DEC-020 all Accepted and unedited; AR-018/AR-019
> Accepted; implementation confirmed still blocked, gate confirmed still
> closed.

- **Branch / PR:** `claude/odoo-shopify-planning-closure-ri64vv` → draft
  PR into `Shopify-connector` (not merged).
- **Files changed:**
  `docs/07-implementation-plan/final-mbq-closure-plan.md` (new — the
  closure package, AR-020 companion),
  `docs/05-qa/architecture-review-log.md` (AR-020 row + note added;
  AR-002 through AR-019 untouched),
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (compact status note added),
  `docs/01-research/research-handoff.md` (this entry). **The MBQ register
  (`master-blueprint-open-questions.md`) is NOT edited. No DEC-003
  through DEC-020 file changed. No `docs/04-decisions/README.md` change.
  No code/Python/XML/manifest/security/test/CI file changed. No
  implementation task created. No module scaffolding created.**
- **What was done:** prepared the **Final MBQ Closure Plan** (AR-020,
  Proposed for ChatGPT review). All **50** MBQ rows not fully closed
  after AR-019 reviewed with one explicit proposed final status each:
  **2 proposed resolved** (MBQ-29, MBQ-35), **27 proposed partially
  resolved** with residuals reclassified as `CLAUDE.md` §9 task-spec
  detail, **17 explicitly descoped from MVP / first gate** (incl.
  MBQ-27 tax mechanism → blocks order-import task only; MBQ-63
  webhook-driven inventory import → not in Phase 1; MBQ-24 automated
  media overwrite → disabled in MVP), **4 accepted-open risks with
  containment** (MBQ-12/28/50/58), **0 still blocking the limited core
  gate**. Official-doc verification performed and cited (2026-07-05):
  Shopify compliance-webhook mandate is App-Store-scoped +
  protected-data levels for custom apps officially tabled (MBQ-09);
  `@idempotent` required as of API 2026-04, 24h retention, scope
  undocumented → UUID-per-operation default (MBQ-14); `productSet`
  media omission still officially unconfirmed, documented
  reference-vs-guide tension (MBQ-24); Odoo 19 has **no** documented
  externally-computed-tax mechanism on `sale.order`; official Amazon
  connector documents recompute + write-off (MBQ-27). High-power
  research mode used as authorized: five parallel evidence agents (two
  repo extraction, three official-doc verification), single-pass stop
  condition, all claims cited or logged as open.
- **Gate state:** **AR-020 is Proposed, not accepted. The MBQ register
  is not edited (plan §7 holds the proposed wording for a future
  acceptance patch). The implementation gate remains closed.
  Implementation remains blocked. No code was created. No implementation
  task was created.**
- **Learning feedback loop:** **New issues discovered:** the
  `/docs/00-source-materials` capture rule (CLAUDE.md §7.4) conflicts
  with a strict allowed-files list when new official research happens in
  a closure session — excerpts embedded in the plan; full-page capture
  logged as follow-up (plan §10 risk 10). **Repeated issue patterns:**
  none triggered; the evidence-consistency gate was applied (no
  unsupported claim asserted; four unverifiable points logged as open).
  **Rules/checklists updated:** none (out of allowed-files scope).
  **New rejected approaches:** none — every proposed default is stricter
  than the accepted baseline; RA-001–RA-023 checked, none reintroduced.
  **New technical debt:** none (no code). **New open questions:** none
  added as register rows; two narrow residuals recorded inside MBQ-09's
  proposed wording (voluntary compliance-topic delivery; Level-2
  "varies by plan" matrix). **Architecture concerns:** none — no
  accepted DEC/AR/blueprint content changed.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured · rejected approaches checked, none
  added · technical debt logged (none applicable) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** ChatGPT reviews the closure package
  (accept / accept with changes / revise / reject). On acceptance: a
  small acceptance-patch session applies plan §7 to
  `master-blueprint-open-questions.md`, flips AR-020 to Accepted, and
  captures the cited official pages under `/docs/00-source-materials`;
  then ChatGPT's criterion-5 confirmation and the **separate, explicit,
  limited core-only gate-opening act** — none of which is performed by
  this session.
- **Stop condition:** stopped after opening the draft PR. `main` and
  plain `dev` untouched; only the four allowed files changed; awaiting
  ChatGPT review.

---

### Core Naming and Schema Planning accepted — compact handoff (2026-07-05)

> **Documentation-only acceptance patch, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #85 head
> commit `c3e5b68845fed2390b2de35f759e93b6b8ee0317` (branch
> `claude/core-schema-naming-plan-actnaz`, based on `Shopify-connector` at PR
> #84 merge commit `4bf692dceec4190705f522bc2d32851af4c79e37`); DEC-003
> through DEC-020 confirmed Accepted by ChatGPT and unedited; the revised
> `core-naming-schema-planning.md` and AR-019 confirmed previously Proposed
> for ChatGPT review, not accepted; implementation confirmed still blocked.

- **Branch / PR:** `claude/core-schema-naming-plan-actnaz` → PR #85 into
  `Shopify-connector` (draft, not merged).
- **Files changed:** `docs/07-implementation-plan/core-naming-schema-planning.md`
  (Status → Accepted; Acceptance section added; §14/§16 updated to reflect
  acceptance), `docs/05-qa/architecture-review-log.md` (AR-019 row and
  footnote updated to Accepted), `docs/03-architecture/master-blueprint-open-questions.md`
  (MBQ-01/02/04/07/16/19/20/21/44/45/62 rows updated; acceptance-patch note
  added — **no other MBQ row touched**), `docs/01-research/research-handoff.md`
  (this file). **No DEC-003 through DEC-020 file changed. No
  `docs/04-decisions/README.md` change. No code file changed. No
  Python/XML/manifest/security/test/CI file changed. No implementation task
  created. No module scaffolding created.**
- **What changed / residue fixed:** ChatGPT accepted the revised core
  naming/schema planning document on 2026-07-05, **at implementation-planning
  level only.** Accepted core model list (six models): `shopify.connector.store`,
  `.store.settings`, `.location`, `.binding.mixin` (abstract), `.job`,
  `.job.log`. Applied the document's §14 register-impact wording to
  `master-blueprint-open-questions.md` for exactly eleven rows: **MBQ-01,
  MBQ-02, MBQ-07, MBQ-16, MBQ-19, MBQ-20, MBQ-21, and the MBQ-45/MBQ-62
  residuals — each now Resolved**; **MBQ-44 — Partially resolved** (planned
  CSV row shapes only, no CSV file created); **MBQ-04 — confirmed NOT
  resolved, explicitly and fully descoped from the first core-only slice**
  (no credential model, credential metadata model, or secret/token field of
  any kind is accepted; real credential persistence and the credential
  lifecycle schema both remain fully open). Job+log split accepted;
  `idempotency_key`/`operation_scope_key` accepted as distinct concepts;
  retry constants accepted as adjustable planning defaults only;
  `enqueue_decisions` as serialized JSON accepted for now, subject to future
  implementation review. AR-019 moved from "Proposed for ChatGPT review —
  NOT YET ACCEPTED" to **Accepted**, at implementation-planning level only.
- **Items deferred:** the domain-scope MBQ rows this pass does not touch
  (MBQ-03/05/09/14/23–43/46/48–61/63–65); real credential persistence and any
  credential-lifecycle schema (MBQ-04 remains fully open); the setup wizard/
  test-connection flow; the transport/API client; every product/customer/
  order/inventory/fulfillment domain model; webhooks; the explicit
  implementation-gate-opening act; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated
  issue patterns:** none newly triggered. **Rules/checklists updated:** none
  this session (out of allowed-files scope). **New rejected approaches:**
  none — no new architecture direction was introduced by this acceptance.
  **New technical debt:** none (no code). **New open questions:** none
  added — no new MBQ row was created; eleven existing rows were updated with
  the document's own pre-drafted register-impact wording, applied exactly as
  written. **Architecture concerns:** none — no accepted DEC (DEC-003–020) or
  Part A–E design content was changed; this acceptance is a documentation-
  level, implementation-planning-level acceptance only.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (none new) · rejected approaches checked, none
  added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none triggered) — all **YES**.
- **Next recommended session:** a separate, explicit ChatGPT
  implementation-gate-opening act (not performed by this acceptance), or the
  next domain-scope MBQ session (e.g. the ChatGPT-owned MBQ rows this pass
  does not touch) — **not a coding session**, and not itself the
  gate-opening act.
- **Stop condition:** stopped after pushing this acceptance patch to the
  existing PR #85 branch (not merged, still draft). DEC-003 through DEC-020
  not edited; `docs/04-decisions/README.md` not edited; only the eleven named
  MBQ rows changed in `master-blueprint-open-questions.md`; no code files
  changed; no implementation task or module scaffolding created; this
  document and AR-019 are both **Accepted by ChatGPT (2026-07-05), at
  implementation-planning level only**; implementation remains **blocked**;
  the implementation gate remains **closed**; `main` and plain `dev`
  untouched. Awaiting further instruction.

---

### Core Naming and Schema Planning — revised after ChatGPT REVISE — compact handoff (2026-07-05)

> **Documentation-only revision, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #85 head
> commit `938066d47f8f7fd3b4a1d54b50096c356f6fcee6` (branch
> `claude/core-schema-naming-plan-actnaz`, based on `Shopify-connector` at PR
> #84 merge commit `4bf692dceec4190705f522bc2d32851af4c79e37`); DEC-003
> through DEC-020 confirmed Accepted by ChatGPT and unedited;
> `master-blueprint-open-questions.md` confirmed unedited; ChatGPT's review
> of the original PR #85 proposal confirmed as **REVISE**, not accepted;
> implementation confirmed still blocked.

- **Branch / PR:** `claude/core-schema-naming-plan-actnaz` → PR #85 into
  `Shopify-connector` (draft, not merged).
- **Files changed:** `docs/07-implementation-plan/core-naming-schema-planning.md`
  (revised), `docs/05-qa/architecture-review-log.md` (AR-019 row updated +
  revision footnote added), `docs/01-research/research-handoff.md` (this
  file). **No DEC-003 through DEC-020 file changed. No
  `docs/04-decisions/README.md` change. No `master-blueprint-open-questions.md`
  change — no MBQ row status changed. No code file changed. No
  Python/XML/manifest/security/test/CI file changed. No implementation task
  created. No module scaffolding created.**
- **What changed / residue fixed:** applied all five corrections from
  ChatGPT's REVISE review of the original proposal. (1) **Removed
  `shopify.connector.store.credential` entirely** — no credential model,
  credential metadata model, or secret field of any kind is proposed for the
  first slice; MBQ-04 is now "proposed not resolved / explicitly, fully
  descoped for slice 1," not "partially resolved." Proposed model count
  moves from seven to **six**. (2) **Fixed the `store.settings_id`/One2many-
  named-singular contradiction** by removing the reverse field from `store`
  entirely; `shopify.connector.store.settings.store_id` is the sole,
  authoritative link. (3) **Changed `shopify.connector.job.log.job_id` from
  `ondelete='cascade'` to `ondelete='restrict'`**, so a job's log/audit
  history can never be silently cascade-deleted through its parent — 
  reconciled with the access plan (§10), which already grants no group
  Unlink on either model. (4) **Gave `job_type` two core-owned starting
  values** (`core_readiness_check`, `core_manual_maintenance`) so the
  required Selection is never contradictorily empty before any domain
  module installs, while remaining extensible via `selection_add`.
  (5) **Made the serialization guard DB-backed and race-safe** — added
  `operation_scope_key` (computed from `store_id`+`res_model`+`res_id`+
  `shopify_target_gid`, populated only while a job is non-terminal, cleared
  to `NULL` on reaching a terminal state) under a unique constraint on
  `(store_id, operation_scope_key)`, explicitly kept distinct from
  `idempotency_key` (which persists for the job's life and answers a
  different question). (6) **Removed the `mail.thread`/tracking commitment**
  for settings-change history, leaving that choice to a future
  implementation task's own manifest dependency decision. Updated AR-019
  (row text + a revision footnote) and this handoff accordingly; §13/§14/§16
  of the planning document and the PR's model-count/MBQ-impact summaries
  were all updated to match.
- **Items deferred:** ChatGPT's actual re-review/acceptance of the revised
  document and AR-019; if accepted, applying §14's drafted register-impact
  wording to `master-blueprint-open-questions.md`; the two judgment calls
  the document still flags for scrutiny (§16: the job+log split, the generic
  `enqueue_decisions` JSON field — neither was named in the REVISE feedback);
  real credential persistence and any credential-lifecycle schema (MBQ-04
  remains fully open, not merely the secret value); the setup wizard/
  test-connection flow; the transport/API client; every product/customer/
  order/inventory/fulfillment domain model; webhooks; the explicit
  implementation-gate-opening act; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none beyond what
  ChatGPT's REVISE already named — this session corrected exactly those five
  items, no additional defect found while doing so. **Repeated issue
  patterns:** none newly triggered. **Rules/checklists updated:** none this
  session (out of allowed-files scope). **New rejected approaches:** none —
  `rejected-approaches-log.md` was not re-checked this session since no new
  architecture direction was introduced, only schema corrections within the
  existing proposal's own boundaries. **New technical debt:** none (no
  code). **New open questions:** none added — no new MBQ row was created;
  MBQ-04's draft wording was corrected from "partially resolved" to
  "not resolved / explicitly descoped," applied only upon a future
  acceptance, same as every other row here. **Architecture concerns:** none
  — no accepted DEC (DEC-003–020) or Part A–E design content was changed;
  this revision only corrects schema-level defects within the already-
  proposed, not-yet-accepted planning document.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new beyond the named REVISE items)
  · rejected approaches checked, none added · technical debt logged (none
  applicable — no code) · repeated-issue escalation applied (none
  triggered) — all **YES**.
- **Next recommended session:** ChatGPT's re-review of the revised document
  and AR-019 — accept as revised, accept with changes (the document's own
  §16 names two remaining candidates), request further revision, or reject.
  If accepted: apply §14's register-impact wording to the MBQ register,
  record the acceptance in `architecture-review-log.md` and
  `../04-decisions/README.md`, and update this handoff — not implementation,
  and not the gate-opening act.
- **Stop condition:** stopped after pushing the revision to the existing
  PR #85 branch (not merged, still draft). DEC-003 through DEC-020 not
  edited; `docs/04-decisions/README.md` not edited;
  `master-blueprint-open-questions.md` not edited; no MBQ row status
  changed; no code files changed; no implementation task or module
  scaffolding created; this document and AR-019 are both **Proposed for
  ChatGPT review — NOT YET ACCEPTED**; implementation remains **blocked**;
  the implementation gate remains **closed**; `main` and plain `dev`
  untouched. Awaiting further instruction.

---

### Core Naming and Schema Planning — AR-019 proposed — compact handoff (2026-07-05)

> **Documentation-only implementation-planning proposal, not implementation,
> not an implementation-gate opening.** Confirmed before editing: PR #84
> merge commit `4bf692dceec4190705f522bc2d32851af4c79e37` into
> `Shopify-connector`; DEC-003 through DEC-020 confirmed Accepted by
> ChatGPT and unedited; the implementation gate readiness audit and AR-018
> confirmed previously Accepted by ChatGPT; the accepted next session
> (a documentation-only naming/core-schema implementation-planning pass for
> MBQ-01/02/04/07/16/19/20/21/44/45(residual)/62(residual)) confirmed not yet
> started; implementation confirmed still blocked.

- **Branch / PR:** `claude/core-schema-naming-plan-actnaz` → PR into
  `Shopify-connector` (draft, not merged).
- **Files changed:** `docs/07-implementation-plan/core-naming-schema-planning.md`
  (new), `docs/05-qa/architecture-review-log.md` (AR-019 added),
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-020 file changed. No `docs/04-decisions/README.md` change. No MBQ row
  status changed in `master-blueprint-open-questions.md`. No code file
  changed. No Python/XML/manifest/security/test/CI file changed. No
  implementation task created. No module scaffolding created.**
- **What changed / residue fixed:** prepared
  `core-naming-schema-planning.md`, proposing (not deciding) exact Odoo
  model names for a first core-only slice (`shopify.connector.store`,
  `.store.settings`, `.store.credential`, `.location`, `.binding.mixin`
  (abstract), `.job`, `.job.log`) and field schemas for each; a store-scoped
  `store.settings` model as the MBQ-07 feature-flag/settings shape; a
  job+log split resolving MBQ-19, with error/manual-review fields folded
  onto the job model rather than a separate model; an operation-level
  idempotency key schema (MBQ-20) and a query-time serialization guard
  (MBQ-21), both owned by the job model, not separate models; retry-count
  ceilings and a backoff schedule by error-class family (MBQ-16); four
  proposed group XML IDs plus planned (not created) `ir.model.access.csv`
  row shapes (MBQ-44, MBQ-45's residual); and the `odoo_event`
  `job_source`/`trigger_origin` field mechanics resolving MBQ-62's residual.
  For MBQ-04, adopted the explicit slice-1 descope (Option A) — no official
  Odoo encryption-at-rest evidence was reviewed this session, so a
  `store.credential` model is proposed for lifecycle metadata only, with no
  field, type, or mechanism proposed for the actual secret/token value.
  Added **AR-019** to `architecture-review-log.md`, Status **Proposed for
  ChatGPT review — NOT YET ACCEPTED**, without altering AR-002 through
  AR-018.
- **Items deferred:** ChatGPT's actual review/acceptance of this document
  and AR-019; if accepted, applying §14's drafted register-impact wording to
  `master-blueprint-open-questions.md` for MBQ-01/02/04/07/16/19/20/21/44/
  45(residual)/62(residual) (not performed by this session); the three
  judgment calls the document itself flags for scrutiny (§16: the job+log
  split, the generic `enqueue_decisions` JSON field, and creating
  `store.credential` ahead of MBQ-04's real resolution); real credential
  persistence (MBQ-04 remains open); the setup wizard/test-connection flow;
  the transport/API client; every product/customer/order/inventory/
  fulfillment domain model; webhooks; the explicit implementation-gate-
  opening act; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated
  issue patterns:** none newly triggered. **Rules/checklists updated:** none
  this session (out of allowed-files scope). **New rejected approaches:**
  none — `rejected-approaches-log.md` was checked in full before drafting;
  no proposal here reintroduces a binding rejected approach (in particular,
  no destructive uninstall/disable behavior, no blind first-write posture,
  no bypass of the DEC-009 retry/idempotency taxonomy). **New technical
  debt:** none (no code). **New open questions:** none added — no new MBQ
  row was created; this session only proposes draft resolution wording for
  eleven already-open rows, applied only upon a future acceptance.
  **Architecture concerns:** none — no accepted DEC (DEC-003–020) or Part
  A–E design content was changed; this document converts already-accepted
  blueprint *directions* into exact names/schema without introducing new
  architecture.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none triggered) — all **YES**.
- **Next recommended session:** ChatGPT's review of this document and
  AR-019 — accept as proposed, accept with changes (the document's own §16
  names three specific candidates), request revision, or reject. If
  accepted: apply §14's register-impact wording to the MBQ register, record
  the acceptance in `architecture-review-log.md` and
  `../04-decisions/README.md`, and update this handoff — not implementation,
  and not the gate-opening act.
- **Stop condition:** stopped after opening the draft PR for
  `core-naming-schema-planning.md`/AR-019 against `Shopify-connector` (not
  merged, still draft). DEC-003 through DEC-020 not edited;
  `docs/04-decisions/README.md` not edited; no MBQ row status changed; no
  code files changed; no implementation task or module scaffolding created;
  this document and AR-019 are both **Proposed for ChatGPT review — NOT YET
  ACCEPTED**; implementation remains **blocked**; the implementation gate
  remains **closed**; `main` and plain `dev` untouched. Awaiting further
  instruction.

---

### Implementation Gate Readiness Audit Acceptance Patch — AR-018 accepted — compact handoff (2026-07-05)

> **Documentation-only acceptance patch, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #84 head
> commit `553a595cad0c9e18d3105850b3cd48f4535841eb` (branch
> `claude/gate-readiness-audit-qz9x2k`, based on `Shopify-connector` at PR
> #83 merge commit); DEC-003 through DEC-020 confirmed Accepted by
> ChatGPT and unedited; the implementation-gate readiness audit and
> AR-018 confirmed previously Proposed for ChatGPT review, not accepted;
> implementation confirmed still blocked.

- **Branch / PR:** `claude/gate-readiness-audit-qz9x2k` → PR #84 into
  `Shopify-connector` (not merged, still draft).
- **Files changed:**
  `docs/05-qa/implementation-gate-readiness-audit.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003
  through DEC-020 file changed. No `docs/04-decisions/README.md` change.
  No MBQ row status changed. No code file changed. No
  Python/XML/manifest/security/test/CI file changed. No implementation
  task created. No module scaffolding created.**
- **Audit acceptance patch applied.** ChatGPT reviewed the
  implementation-gate readiness audit and **accepted it on 2026-07-05.**
  **AR-018 is now Accepted by ChatGPT.** **Accepted verdict, unchanged:
  READY ONLY FOR A VERY LIMITED IMPLEMENTATION-PLANNING SPRINT, NOT
  CODE.** ChatGPT confirmed the audit's Criterion 2/3/4 findings (eleven
  rows — MBQ-01/02/04/07/16/19/20/21/44/45/62 — still block even the
  narrowest core-substrate-only first slice; the explicit gate-opening
  act has not occurred; no implementation task has been written to the
  CLAUDE.md §9 template) and accepted the audit's own strict,
  conservative reading of **Criterion 1 as non-blocking** for this scope
  — the decisive blockers remain Criteria 2, 3, and 4, not Criterion 1.
  **Accepted next session:** a single, documentation-only naming/
  core-schema implementation-planning artifact addressing MBQ-01 (model
  names), MBQ-02 (field names/types), MBQ-04 (credential storage
  decision or explicit slice-1 descope), MBQ-07 (feature-flag/settings
  schema), MBQ-16 (retry-count/backoff constants), MBQ-19 (job/log model
  shape), MBQ-20 (operation-level idempotency key schema), MBQ-21
  (serialization-guard mechanism), MBQ-44 (core access CSV/record-rule
  planning), MBQ-45's residual (group XML IDs), and MBQ-62's residual
  (`odoo_event` trigger-origin implementation mechanics) — **this next
  session is not code and not the gate-opening act.** **No MBQ row
  status is changed by this acceptance. No implementation task is
  created. No DEC-003 through DEC-020 is changed.**
- **Items deferred:** the accepted next-session naming/core-schema
  implementation-planning pass itself (not started); confirming or
  re-labelling the DP-003/004/006 quality-gate escalation row (criterion
  5's ambiguity, left open, does not block the next session); the
  documentation-currency fixes to `master-blueprint.md`/
  `master-blueprint-core-substrate.md` (still a named future
  documentation-maintenance item, not performed); the
  implementation-gate-opening act itself; all implementation; all
  implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session mechanically applied ChatGPT's acceptance of the audit's
  findings and verdict, precisely scoping what was and was not decided
  (the audit's own reading is accepted; no MBQ row status changes; no
  gate-opening act performed). **Repeated issue patterns:** none newly
  triggered. **Rules/checklists updated:** none this session (out of
  allowed-files scope). **New rejected approaches:** none. **New
  technical debt:** none (no code). **New open questions:** none added —
  no MBQ row was resolved or added by this acceptance. **Architecture
  concerns:** none — no accepted DEC (DEC-003–020) or Part A–E content
  was changed; only the audit's own and AR-018's acceptance status were
  updated.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added · technical debt logged (none applicable — no
  code) · repeated-issue escalation applied (none triggered) — all
  **YES**.
- **Next recommended session:** the accepted documentation-only
  naming/core-schema implementation-planning pass for MBQ-01/02/04/07/
  16/19/20/21/44/45(residual)/62(residual) — **not a coding session, and
  not the gate-opening act.**
- **Stop condition:** stopped after committing and pushing this
  acceptance patch to the existing PR #84 branch (not merged, still
  draft). DEC-003 through DEC-020 not edited; `docs/04-decisions/README.md`
  not edited; no MBQ row status changed; no code files changed; no
  implementation task or module scaffolding created; the audit and AR-018
  are now **Accepted by ChatGPT**; implementation remains **blocked**; the
  implementation gate remains **closed**; `main` and plain `dev`
  untouched. Awaiting further instruction.

---

### Implementation Gate Readiness Audit — AR-018 proposed — compact handoff (2026-07-05)

> **Audit-only session, NOT implementation, NOT an implementation-gate
> opening, NOT a MBQ resolution.** Confirmed before editing: PR #83
> confirmed merged into `Shopify-connector` at merge commit
> `b27f842425043e6320d8e168a1208345f6fcab12`; DEC-003 through DEC-020
> confirmed Accepted by ChatGPT and unedited; AR-002 through AR-017
> confirmed Accepted; MBQ-62 confirmed resolved at decision/semantic-
> classification level (DEC-019); MBQ-64/MBQ-65 confirmed resolved at
> decision/posture level (DEC-020); implementation confirmed still
> blocked.

- **Branch / PR:** `claude/gate-readiness-audit-qz9x2k` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:**
  `docs/05-qa/implementation-gate-readiness-audit.md` (new),
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003
  through DEC-020 file changed. No `docs/04-decisions/README.md` change.
  No MBQ row status changed. No code file changed. No
  Python/XML/manifest/security/test/CI file changed. No implementation
  task created. No module scaffolding created.**
- **Audit prepared, not accepted.** Read `master-blueprint.md` in full
  and extracted its five gate-opening criteria verbatim; read the full,
  current `master-blueprint-open-questions.md` register (all 65 rows) and
  classified each into: blocks the first core-only implementation slice,
  blocks a later domain slice, blocks release readiness only, is a
  non-blocking residual, or needs a ChatGPT decision before any gate
  opening; read `quality-feedback-loop.md` §8/§10/§11 and
  `defect-pattern-log.md`'s occurrence-counter table for criterion 5;
  spot-verified `master-blueprint-core-substrate.md` §D.2/§I.3/§J.1
  directly against the register's own citations. **Finding: zero of five
  gate criteria are unambiguously satisfied project-wide.** Criterion 1
  (blueprint parts accepted) passes only for a scope with zero
  operator-facing UI. Criterion 2 (implementation-blocking questions
  resolved/accepted) fails — eleven rows (MBQ-01/02/04/07/16/19/20/21/
  44/45/62) block even the narrowest possible first slice
  (`shopify_connector_core` substrate alone). Criterion 3 (explicit
  ChatGPT gate-opening act) fails — has not occurred. Criterion 4 (tasks
  written to the CLAUDE.md §9 template) is vacuously unmet — no task
  exists. Criterion 5 (no open quality-gate escalation without a
  prevention rule) is ambiguous — the "unsupported assumption/weak
  research" category sits at 3rd-occurrence `ESCALATED` status with a
  recorded prevention gate, but the row's own Status field was never
  updated to `Mitigated`/`Closed`. Also flagged (not corrected, out of
  this sprint's allowed-files scope) that `master-blueprint.md` and
  `master-blueprint-core-substrate.md` §D.2 are stale — they predate
  DEC-018/019/020 and the accepted seventh `odoo_event` job-source value.
  **Verdict: READY ONLY FOR A VERY LIMITED IMPLEMENTATION-PLANNING
  SPRINT, NOT CODE.** Added **AR-018** to `architecture-review-log.md`
  (Proposed for ChatGPT review, not accepted), stating the same finding
  and verdict.
- **Items deferred:** ChatGPT's review/acceptance of the audit itself; the
  recommended naming/core-schema implementation-planning pass (MBQ-01/02/
  04/07/16/19/20/21/44/45(residual)/62(residual)); confirming or
  re-labelling the DP-003/004/006 quality-gate escalation row; the
  documentation-currency fixes to `master-blueprint.md`/
  `master-blueprint-core-substrate.md` (named as a future
  documentation-maintenance item, not performed here); the
  implementation-gate-opening act itself; all implementation; all
  implementation tasks.
- **Learning feedback loop:** **New issues discovered:** one — no prior
  session had performed a full, current, row-by-row read of the register
  against the five gate criteria since DEC-018/019/020 landed; the Part E
  bridge document's own MBQ decision plan table was correctly left
  unedited (per its own stated maintenance rule) but that means it no
  longer reflects current status, which this audit's §4 table now
  supersedes for readiness-classification purposes specifically (not as
  an edit to Part E itself). **Repeated issue patterns:** none newly
  triggered. **Rules/checklists updated:** none this session (out of
  allowed-files scope). **New rejected approaches:** none — no new
  architecture proposed. **New technical debt:** none (no code). **New
  open questions:** none added — this audit classifies existing rows, it
  does not add new ones. **Architecture concerns:** none — no accepted
  DEC/AR/Part A–E content changed; the two documentation-currency
  findings (`master-blueprint.md`, `master-blueprint-core-substrate.md`
  §D.2) are logged as a future maintenance item, per
  `quality-feedback-loop.md` §11.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (one: no prior full post-DEC-020 gate
  audit existed until now) · rejected approaches checked, none added ·
  technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** produce the naming/core-schema
  implementation-planning artifact named in the audit's §7 (MBQ-01/02/04/
  07/16/19/20/21/44/45(residual)/62(residual)) — still documentation-only,
  still not a gate-opening act. **Not a coding session.**
- **Stop condition:** stopped after committing and pushing this audit to
  a new branch and opening one **draft** PR into `Shopify-connector` (not
  merged, not marked ready for review). DEC-003 through DEC-020 not
  edited; `docs/04-decisions/README.md` not edited; no MBQ row status
  changed; no code files changed; no implementation task or module
  scaffolding created; AR-018 is **Proposed for ChatGPT review — NOT
  accepted**; implementation remains **blocked**; the implementation gate
  remains **closed**; `main` and plain `dev` untouched. Awaiting ChatGPT
  review.

---

### DEC-020 Acceptance Patch — MBQ-64/MBQ-65 resolved at decision/posture level — compact handoff (2026-07-04)

> **Documentation-only acceptance patch, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #83 head
> commit `6fecde7fad882e6d22c928628e45244ce4e04a2c` (branch
> `claude/mbq-64-65-decision-ux352n`, based on `Shopify-connector` at PR
> #82 merge commit); DEC-003 through DEC-019 confirmed Accepted by ChatGPT
> and unedited; DEC-020 confirmed previously Proposed for ChatGPT review
> (revised once for MBQ-64, MBQ-65 unchanged), not yet accepted;
> implementation confirmed still blocked.

- **Branch / PR:** `claude/mbq-64-65-decision-ux352n` → PR #83 into
  `Shopify-connector` (not merged, still draft).
- **Files changed:**
  `docs/04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-019 file changed. No `docs/04-decisions/README.md` change. No MBQ
  row other than MBQ-64/MBQ-65 edited. No code file changed. No
  Python/XML/manifest/security/test/CI file changed.**
- **DEC-020 acceptance patch applied.** ChatGPT reviewed the revised
  `DEC-020` and **accepted it on 2026-07-04, at decision/posture level for
  both MBQ-64 and MBQ-65.** **AR-017 is now Accepted by ChatGPT.**
  **MBQ-64 is resolved at decision/posture level**: Phase 1 automatic
  order import is same-currency only
  (`Order.presentmentCurrencyCode == Order.currencyCode`); for
  same-currency orders, `sale.order.currency_id` follows the connector's
  normal configured pricelist/company currency, aligned to Shopify shop
  currency; for a divergent order, the connector never silently creates a
  normal Odoo sale order in shop currency — the job is blocked from
  automatic SO creation and routed to manual review / treated as an
  explicit unsupported-scope case before SO creation, independent of the
  total-check guard's outcome; both `shopMoney`/`presentmentMoney` and
  `presentmentCurrencyCode` are captured as audit/reconciliation evidence
  in every case; presentment-currency Odoo orders remain non-MVP unless a
  later, explicit scope expansion designs currency/pricelist provisioning.
  **MBQ-56's own tolerance mechanics remain their own open residual**,
  unchanged, and are explicitly not relied upon as the mechanism that
  catches the currency-model divergence. **The exact final error-class/
  sub-reason mapping and enforcement mechanism for a blocked
  divergent-currency order remain implementation planning.** **MBQ-65 is
  resolved at decision/posture level**: `PRODUCTS_CREATE`/
  `PRODUCTS_UPDATE`/`PRODUCTS_DELETE` are implemented in Phase 1 as
  enqueue-only triggers, never a direct write, each job performing a
  follow-up authoritative read before any create/update/delete, with
  DEC-005 reconciliation as the required backstop; `PRODUCTS_DELETE` never
  directly deletes/archives the bound Odoo product; ambiguous cases route
  to manual review via existing error-class vocabulary. **MBQ-65's exact
  controller/job/query/subscription mechanics, and the still-unconfirmed
  variant-count payload-truncation claim, remain implementation
  planning.** Both rows' register-impact wording (DEC-020 §9) has been
  **applied** to `master-blueprint-open-questions.md`, dated **2026-07-04**.
  **No other MBQ row touched. MBQ-62's accepted state (DEC-019) is not
  reopened or weakened. No implementation started.**
- **Items deferred:** MBQ-56's own tolerance/comparison mechanism value;
  the exact final error-class/sub-reason mapping and enforcement mechanism
  for a blocked MBQ-64 divergent-currency order; MBQ-65's exact
  controller/job/query/subscription implementation mechanics; independent
  verification of the still-unconfirmed variant-count payload-truncation
  claim; logging MBQ-64 Option B / MBQ-65 Option D in
  `rejected-approaches-log.md` (recommended as a future follow-up, not
  performed — out of this sprint's allowed-files scope); the
  implementation-gate-opening act; all implementation; all implementation
  tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session mechanically applied ChatGPT's acceptance decision to the
  repository, precisely scoping what was and was not decided (decision/
  posture level only; exact implementation mechanics explicitly excluded),
  continuing the same discipline DEC-017/018/019 applied. **Repeated issue
  patterns:** none newly triggered. **Rules/checklists updated:** none
  this session (out of allowed-files scope). **New rejected approaches:**
  none formally logged (`rejected-approaches-log.md` out of scope) — MBQ-64
  Option B and MBQ-65 Option D remain named, not-adopted options within
  DEC-020 itself, with a standing recommendation to log them formally in a
  future session. **New technical debt:** none (no code; nothing to
  compromise). **New open questions:** none added — MBQ-64 and MBQ-65 are
  now resolved at decision/posture level, each still carrying its own
  named implementation-planning residual (not a new MBQ row); MBQ-56
  remains open, unchanged. **Architecture concerns:** none — no accepted
  DEC (DEC-003–019), AR (AR-002–016), or Part A–E design content was
  changed; only DEC-020/AR-017's own acceptance status and MBQ-64/MBQ-65's
  own rows were updated.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added (two candidates named for future logging) ·
  technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** a **gate-readiness audit** against
  `master-blueprint.md`'s five gate-opening criteria (§3 of the Part E
  bridge document) — confirming which criteria are now satisfied given
  MBQ-64/MBQ-65's resolution, and what (if anything) remains before
  ChatGPT could consider an explicit, separate implementation-gate-opening
  act. **Not implementation itself, and not a gate-opening act on its
  own.**
- **Stop condition:** stopped after committing and pushing this acceptance
  patch to the existing PR #83 branch (not merged, still draft). DEC-003
  through DEC-019 not edited; no MBQ row other than MBQ-64/MBQ-65 modified;
  no code files changed; DEC-020 and AR-017 are now **Accepted by
  ChatGPT** (at decision/posture level); implementation remains
  **blocked**; the implementation gate remains **closed**; `main` and
  plain `dev` untouched. Awaiting further instruction.

---

### DEC-020 Revision — MBQ-64 corrected after ChatGPT REVISE, still not accepted — compact handoff (2026-07-04)

> **Revision session, NOT implementation, NOT an implementation-gate
> opening, NOT a MBQ resolution.** Confirmed before editing: PR #83 head
> commit `feb6d53ac7d67ca96073e62d8f20b7c81922288e` (branch
> `claude/mbq-64-65-decision-ux352n`, based on `Shopify-connector` at PR
> #82 merge commit); DEC-003 through DEC-019 confirmed Accepted by ChatGPT
> and unedited; DEC-020/AR-017 confirmed previously Proposed for ChatGPT
> review, not accepted; ChatGPT's review of `DEC-020` confirmed as
> **REVISE for MBQ-64** (MBQ-65 found directionally acceptable,
> unchanged); implementation confirmed still blocked.

- **Branch / PR:** `claude/mbq-64-65-decision-ux352n` → draft PR #83 into
  `Shopify-connector` (not merged).
- **Files changed:**
  `docs/04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-019 file changed. No `docs/04-decisions/README.md` change. No MBQ
  row resolved (MBQ-64 and MBQ-65 remain formally `open`). No other MBQ
  row edited. No code file changed. No
  Python/XML/manifest/security/test/CI file changed.**
- **What changed — MBQ-64 corrected, not accepted.** ChatGPT's review
  found the original MBQ-64 posture **not safe enough**: shop currency
  drove `sale.order.currency_id` for every Phase 1 order, and a
  shop/presentment divergence was caught only if the numeric total-check
  guard happened to fail — but Shopify's own already-cited research shows
  a divergent order's shop-currency total is itself a back-converted
  approximation ("might not sum perfectly to totals"), so it could
  reconcile within tolerance while still misrepresenting the
  customer-facing order currency. `DEC-020` §4 (options table) and §5
  (proposed decision) are corrected: **Phase 1 automatic order import is
  now same-currency only** — for orders where
  `Order.presentmentCurrencyCode == Order.currencyCode`,
  `sale.order.currency_id` follows the connector's normal configured
  pricelist/company currency, aligned to Shopify shop currency; for a
  divergent order, the connector **never** silently creates a normal Odoo
  sale order in shop currency, regardless of the total-check guard's
  outcome — the job is blocked from automatic SO creation and routed to
  manual review / treated as an explicit unsupported-scope case **before**
  SO creation, independent of that guard. Both `shopMoney`/
  `presentmentMoney` amounts and `Order.presentmentCurrencyCode` remain
  captured as audit/reconciliation evidence in every case.
  Presentment-currency-denominated Odoo orders (Option B) remain non-MVP
  unless and until a later, explicit scope expansion designs
  currency/pricelist provisioning. `financial total mismatch` is now
  evaluated explicitly as a *candidate* classification for the blocked
  case rather than forced onto it — §5 explains that forcing it without a
  named, deliberate broadening would risk the same loose-routing pattern
  DEC-014's Fable review (finding B1) already flagged once; the exact
  final error-class/sub-reason mapping for a blocked divergent-currency
  order **remains implementation planning**, while the decision posture
  itself — **no silent SO creation for divergent currencies** — is fixed
  now. **MBQ-56's total-check tolerance mechanics remain their own open
  residual, unchanged, and are explicitly not relied upon as the (sole)
  mechanism that catches a currency-model divergence.** §9's draft MBQ-64
  register wording, AR-017's table row, and the compact status notes in
  `master-blueprint-open-questions.md` were all updated to match — none of
  them mark MBQ-64 resolved. **MBQ-65 is unchanged** — still Option A
  (enqueue-only triggers, mandatory follow-up authoritative read, never a
  direct write), found directionally acceptable by this same review.
- **Items deferred:** ChatGPT's next review of the revised `DEC-020`;
  applying §9's drafted register-impact wording to MBQ-64/MBQ-65's own
  rows (only after acceptance); deciding the exact final error-class/
  sub-reason mapping for a blocked divergent-currency order (explicitly
  left to implementation planning); MBQ-56's own tolerance mechanics;
  independently verifying the still-unconfirmed variant-count payload-
  truncation claim; the implementation-gate-opening act; all
  implementation.
- **Learning feedback loop:** **New issues discovered:** one — the
  original MBQ-64 proposal conflated "the numeric total-check guard
  passed" with "the order is safe to import automatically," when Shopify's
  own already-cited research shows the shop-currency total being compared
  is itself an approximation whenever presentment diverges; corrected by
  making the currency-equality check independent of, and prior to, the
  total-check guard's outcome. **Repeated issue patterns:** none newly
  triggered — the discipline of evaluating an existing error class's fit
  explicitly rather than forcing it (per §5's `financial total mismatch`
  discussion) continues the same rigor DEC-018/019 applied to MBQ-62.
  **Rules/checklists updated:** none this session (out of allowed-files
  scope). **New rejected approaches:** none formally logged
  (`rejected-approaches-log.md` out of scope) — the original,
  now-superseded MBQ-64 posture (shop-currency-only with guard-only
  divergence handling) is not separately logged as a rejected approach
  since it was corrected within the same still-unaccepted proposal, not
  adopted and later reversed. **New technical debt:** none (no code).
  **New open questions:** none added to the register — MBQ-64/MBQ-65
  remain the only rows touched, only by an unapplied draft note; the
  exact final error-class/sub-reason mapping for a blocked
  divergent-currency order is named as a residual within `DEC-020` itself,
  not a new MBQ row. **Architecture concerns:** none — no accepted DEC
  (DEC-003–019) or AR (AR-002–016) was changed; only the still-proposed,
  still-unaccepted DEC-020/AR-017 were revised.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (one issue found and corrected within
  the same unaccepted proposal) · rejected approaches checked, none newly
  logged (out of scope) · technical debt logged (none applicable — no
  code) · repeated-issue escalation applied (none triggered) — all
  **YES**.
- **Next recommended session:** ChatGPT's re-review of the revised
  `DEC-020` — accept as proposed, accept with change, reject and revise,
  or defer one or both decisions (`DEC-020` §11). Not implementation.
- **Stop condition:** stopped after committing and pushing this revision
  to the existing PR #83 branch (not merged, still draft). DEC-003 through
  DEC-019 not edited; `docs/04-decisions/README.md` not edited; no MBQ row
  resolved (MBQ-64 and MBQ-65 remain formally open); no code files
  changed; DEC-020 and AR-017 remain **Proposed for ChatGPT review — NOT
  accepted**; implementation remains **blocked**; the implementation gate
  remains **closed**; `main` and plain `dev` untouched. Awaiting ChatGPT
  review.

---

### Proposed MBQ-64/MBQ-65 Currency and Product-Webhook Residual Decisions — DEC-020, not yet accepted — compact handoff (2026-07-04)

> **Decision-preparation session, NOT implementation, NOT an
> implementation-gate opening, NOT a MBQ resolution.** Confirmed before
> editing: PR #82 head commit `94e3458e9ff6511f34f9abfe8944b4e0660c02b2`
> (branch `claude/mbq-64-65-decision-ux352n`, based on `Shopify-connector`
> at the same PR #82 merge commit — PR #82 accepted DEC-019); DEC-003
> through DEC-019 confirmed Accepted by ChatGPT and unedited; MBQ-64 and
> MBQ-65 confirmed still open, excluded from DEC-018/DEC-019 per DEC-018 §6;
> implementation confirmed still blocked.

- **Branch / PR:** `claude/mbq-64-65-decision-ux352n` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:**
  `docs/04-decisions/DEC-020-mbq-64-65-currency-webhook-residuals.md` (new),
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/shopify-official-api-notes.md`,
  `docs/01-research/odoo-official-architecture-notes.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-019 file changed. No `docs/04-decisions/README.md` change. No MBQ row
  other than MBQ-64/MBQ-65 edited (and those two only by an unapplied,
  drafted note — see below). No code file changed. No
  Python/XML/manifest/security/test/CI file changed.**
- **DEC-020 proposed, not accepted.** Prepared the dedicated
  currency/webhook residual decision sprint DEC-017 anticipated and
  DEC-018 §6 explicitly routed MBQ-64/MBQ-65 to. Reviewed the existing
  repository corpus in full (Part E bridge document, open-questions
  register, `master-blueprint-product-customer-sale.md` §A.4/§A.14/§C.7–
  §C.9, DEC-007 §3, DEC-017/018/019, AR-014–016, `rejected-approaches-log.md`
  RA-001–023), then performed targeted fresh official-doc research: Shopify's
  "About Shopify Markets" page (presentment currency named the checkout/
  refund/order-edit "source of truth"; shop currency described as a
  back-converted analytics reference that "might not sum perfectly to
  totals" whenever the two diverge); the `Order` object's
  `presentmentCurrencyCode` field, re-verified against raw page source to
  include a sentence not previously cited in this corpus ("This may differ
  from the shop's base currency when serving international customers or
  using multi-currency pricing"); the official `odoo/odoo` 19.0
  `sale_order.py` source, newly confirming `currency_id` is compute-only
  (reachable only via `pricelist_id`/`company_id`, not directly settable)
  and that `amount_untaxed`/`amount_tax`/`amount_total` are computed via
  `AccountTax._get_tax_totals_summary` in exactly the order's one currency;
  and Shopify's "About webhooks" page (delivery not guaranteed, cross-topic
  ordering not guaranteed, "your app shouldn't rely on receiving data from
  Shopify webhooks," reconciliation jobs recommended, `X-Shopify-Webhook-Id`
  dedup, `X-Shopify-Triggered-At`/`updated_at` staleness ordering). One
  claimed fact (per-product variant-count webhook payload truncation) could
  **not** be confirmed against a primary `shopify.dev` page fetched this
  session and is logged as inconclusive, not asserted.
  **Proposes, for MBQ-64:** Shopify shop currency drives
  `sale.order.currency_id` in Phase 1 (Option A); both `shopMoney`/
  `presentmentMoney` amounts and `presentmentCurrencyCode` are captured as
  audit/reconciliation evidence only, never as the Odoo order currency; a
  shop/presentment divergence is never silently accepted — the total-check
  guard runs as normal and any resulting discrepancy is classified under
  the existing `financial total mismatch` class (Part A §D.5.5), reusing
  vocabulary rather than inventing it (Option C, as a companion guard, not
  standalone); presentment-currency-denominated Odoo orders (Option B) are
  explicitly non-MVP, consistent with DEC-007 §3's existing Markets/
  currency-specific-pricing exclusion (Option D, as the scope statement).
  **Proposes, for MBQ-65:** `PRODUCTS_CREATE`/`PRODUCTS_UPDATE`/
  `PRODUCTS_DELETE` are implemented in Phase 1 as enqueue-only triggers
  (Option A) — never a direct write — each job performing a follow-up
  authoritative read before any create/update/delete is applied to Odoo,
  with DEC-005 reconciliation as the required backstop; a `PRODUCTS_DELETE`
  webhook never directly deletes/archives the bound Odoo product, routing
  ambiguous cases to manual review via existing error-class vocabulary.
  MBQ-64 Option B and MBQ-65 Option D (direct webhook-driven product
  mutation) are both evaluated and explicitly rejected for Phase 1, for the
  same root reason RA-008/RA-020 already reject elsewhere in this project:
  writing/committing without a confirming read or guard. **No MBQ row is
  resolved.** Draft (not applied) register-impact wording for MBQ-64 and
  MBQ-65 is recorded in DEC-020 §9, to be applied only by a future,
  separate ChatGPT acceptance patch. Added **AR-017** to
  `architecture-review-log.md` (Proposed for ChatGPT review, not accepted)
  and compact, non-resolving notes to `master-blueprint-open-questions.md`
  and `master-blueprint-implementation-planning-bridge.md` stating DEC-020
  is proposed and neither MBQ-64 nor MBQ-65 is resolved until ChatGPT
  accepts it.
- **Items deferred:** ChatGPT's acceptance/change/rejection/deferral
  decision on DEC-020 itself; applying DEC-020 §9's drafted register-impact
  wording to MBQ-64/MBQ-65's own rows (only happens after acceptance);
  logging MBQ-64 Option B / MBQ-65 Option D in `rejected-approaches-log.md`
  (recommended as a future follow-up in DEC-020 §9, not performed — that
  file is outside this sprint's allowed-files scope); independently
  verifying the unconfirmed variant-count payload-truncation claim against
  a primary source; the implementation-gate-opening act; all
  implementation; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session performed the scoped, dedicated technical-treatment research
  DEC-018 §6 explicitly called for, without reopening or weakening any
  accepted DEC/AR/Part A–E content. **Repeated issue patterns:** none newly
  triggered; the discipline of reusing an existing accepted error-class
  vocabulary (`financial total mismatch`) rather than inventing a new one
  for the MBQ-64 divergence guard continues the same pattern DEC-018/019
  already applied for MBQ-62. **Rules/checklists updated:** none this
  session (out of allowed-files scope). **New rejected approaches:** none
  formally logged this session (`rejected-approaches-log.md` is out of
  scope) — MBQ-64 Option B and MBQ-65 Option D are rejected within DEC-020
  itself, with a recommendation to log them formally after acceptance.
  **New technical debt:** none (no code; nothing to compromise). **New open
  questions:** none added to the register by this session — MBQ-64 and
  MBQ-65 remain the only rows touched, and only by an unapplied draft note;
  two narrower sub-questions were resolved by fresh research (presentment
  currency can diverge without an explicit "Markets" toggle;
  `currency_id` is compute-only, reachable only via `pricelist_id`), and one
  new narrower sub-question was logged inconclusive (variant-count payload
  truncation, not confirmed). **Architecture concerns:** none — no accepted
  DEC (DEC-003–019), AR (AR-002–016), or Part A–E design content was
  changed; only a new DEC-020 (proposed) and AR-017 (proposed) were added.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new; one inconclusive fact logged,
  not asserted) · rejected approaches checked in full, none reintroduced,
  two candidates named for future logging · technical debt logged (none
  applicable — no code) · repeated-issue escalation applied (none
  triggered) — all **YES**.
- **Next recommended session:** ChatGPT's review of DEC-020 — accept as
  proposed, accept with change, reject and revise, or defer one or both
  decisions (DEC-020 §11). Not implementation.
- **Stop condition:** stopped after committing and pushing this proposal to
  a new branch and opening one **draft** PR into `Shopify-connector` (not
  merged, not marked ready for review). DEC-003 through DEC-019 not edited;
  `docs/04-decisions/README.md` not edited; no MBQ row resolved (MBQ-64 and
  MBQ-65 remain formally open); no code files changed; DEC-020 and AR-017
  are **Proposed for ChatGPT review — NOT accepted**; implementation
  remains **blocked**; the implementation gate remains **closed**; `main`
  and plain `dev` untouched. Awaiting ChatGPT review.

---

### DEC-019 Acceptance Patch — MBQ-62 resolved at semantic-classification level — compact handoff (2026-07-04)

> **Documentation-only acceptance patch, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #82 head
> commit `5a6ada7b6671844e75568b57b3b4fa7cef0bd31d` (branch
> `claude/mbq-62-decision-proposal-o8l7pz`, based on `Shopify-connector` at
> PR #81 merge commit `31d6732c9558c04bac49f4c84feba3bd5f90dec8`); DEC-003
> through DEC-018 confirmed Accepted by ChatGPT and unedited; DEC-019
> confirmed previously Proposed for ChatGPT review, not accepted (two prior
> clarification patches applied on the same PR); implementation confirmed
> still blocked.

- **Branch / PR:** `claude/mbq-62-decision-proposal-o8l7pz` → PR #82 into
  `Shopify-connector` (not merged).
- **Files changed:**
  `docs/04-decisions/DEC-019-mbq-62-odoo-event-job-source.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-018 file changed. No `docs/04-decisions/README.md` change. No MBQ row
  other than MBQ-62 edited. No code file changed. No
  Python/XML/manifest/security/test/CI file changed.**
- **DEC-019 acceptance patch applied.** ChatGPT reviewed and **accepted
  DEC-019 on 2026-07-04, at decision/semantic-classification level.**
  **AR-016 is now Accepted by ChatGPT.** **MBQ-62 is resolved at
  decision/semantic-classification level** — Part A §D.2's job-source
  vocabulary is extended with a seventh accepted semantic value,
  **`odoo_event`** (a job enqueued because an Odoo-side business event
  occurred — not a webhook, not manual sync, not scheduled sync, not
  reconciliation, not setup readiness, not export preview dry run). Every
  `odoo_event` job must conceptually carry a trigger-origin
  sub-classification — the accepted trigger-origin concepts for MBQ-62 are
  **"inventory stock-change trigger"** and **"fulfillment
  picking-validation trigger."** An inventory push enqueued by a relevant
  Odoo stock change is classified as `job_source = odoo_event` +
  "inventory stock-change trigger"; a fulfillment creation triggered by a
  validated `stock.picking` is classified as `job_source = odoo_event` +
  "fulfillment picking-validation trigger." **Exact implementation
  mechanics remain implementation planning**: Odoo model names, field
  names, Python constant names, XML IDs, storage/Selection-field
  mechanics, trigger-origin field/model implementation, and MBQ-16
  retry-count/backoff constants. **MBQ-64 and MBQ-65 are unchanged.** **No
  other MBQ row touched. No implementation started.**
- **Items deferred:** the separate MBQ-64/MBQ-65 currency/webhook residual
  decision sprint; the implementation-gate-opening act; all implementation;
  all implementation tasks; every exact implementation-mechanics item named
  above (model/field/constant/XML-ID/storage/trigger-origin-field naming;
  MBQ-16 constants).
- **Learning feedback loop:** **New issues discovered:** none — this
  session mechanically applied ChatGPT's acceptance decision to the
  repository, precisely scoping what was and was not decided (semantic
  classification only; implementation mechanics explicitly excluded).
  **Repeated issue patterns:** none newly triggered. **Rules/checklists
  updated:** none this session (out of allowed-files scope). **New
  rejected approaches:** none — no new architecture proposed or reopened.
  **New technical debt:** none (no code; nothing to compromise). **New
  open questions:** none added — MBQ-62 resolved at semantic-classification
  level only; no other MBQ row changed; MBQ-64/MBQ-65 untouched.
  **Architecture concerns:** none — no accepted DEC (DEC-003–018), AR
  (AR-002–015), or Part A–E design content was changed; only DEC-019/AR-016's
  own acceptance status and MBQ-62's own row were updated.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none triggered) — all **YES**.
- **Next recommended session:** the separate **MBQ-64/MBQ-65
  currency/webhook residual decision sprint**. Not implementation.
- **Stop condition:** stopped after committing and pushing this acceptance
  patch to the existing PR #82 branch (not merged). DEC-003 through DEC-018
  not edited; no MBQ row other than MBQ-62 modified; no code files changed;
  DEC-019 and AR-016 are now **Accepted by ChatGPT** (at
  decision/semantic-classification level); implementation remains
  **blocked**; the implementation gate remains **closed**; `main` and
  plain `dev` untouched. Awaiting further instruction.

---

### MBQ-62 Decision Proposal — DEC-019 prepared, not accepted — compact handoff (2026-07-04)

> **Decision-preparation session, NOT implementation, NOT an
> implementation-gate opening, NOT a MBQ resolution.** Confirmed before
> editing: current branch based on `Shopify-connector` at PR #81 merge
> commit `31d6732c9558c04bac49f4c84feba3bd5f90dec8`; DEC-003 through DEC-018
> confirmed Accepted by ChatGPT and unedited; implementation confirmed still
> blocked.

- **Branch / PR:** `claude/mbq-62-decision-proposal-o8l7pz` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:**
  `docs/04-decisions/DEC-019-mbq-62-odoo-event-job-source.md` (new),
  `docs/05-qa/architecture-review-log.md` (AR-016 added),
  `docs/03-architecture/master-blueprint-open-questions.md` (compact note
  near the top + a proposal-citation note added to MBQ-62's own row only),
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (compact note only), `docs/01-research/research-handoff.md` (this file).
  **No DEC-003 through DEC-018 file changed. No `docs/04-decisions/README.md`
  change. No MBQ row other than MBQ-62 edited. MBQ-62 not marked resolved.
  No code file changed. No Python/XML/manifest/security/test/CI file
  changed.**
- **MBQ-62 decision proposal prepared.** DEC-019 evaluates MBQ-62's two named
  Odoo-side event-trigger use cases (an inventory push enqueued by a
  relevant Odoo stock change; a fulfillment creation triggered by a
  validated `stock.picking`) against four options — add a seventh Part A
  §D.2 job-source value; classify under an existing source plus
  trigger-origin metadata; a separate trigger-origin dimension with no
  seventh value; defer Odoo-side event triggers from Phase 1 — and
  **proposes** extending the vocabulary with a seventh value, `odoo_event`,
  paired with a required trigger-origin sub-classification naming the
  specific Odoo event, rejecting a weak mapping onto any of the six existing
  values (re-confirming DEC-018's own strict per-value analysis) and
  rejecting deferral (incompatible with DEC-011's accepted fulfillment
  trigger design). **DEC-019 is proposed, not accepted.** **AR-016 is
  proposed, not accepted.** **MBQ-62 is not resolved** — only a short
  proposal-citation note was added to its register row; its substance is
  unchanged. **MBQ-64 and MBQ-65 are unchanged**, out of scope for this
  session. **No implementation started.**
- **Items deferred:** ChatGPT's actual review/acceptance of DEC-019/AR-016;
  if accepted, the register-impact wording DEC-019 §6 pre-drafted (not
  applied by this session) for MBQ-62's row; the separate MBQ-64/MBQ-65
  currency/webhook residual decision sprint; the implementation-gate-opening
  act; all implementation; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session's only judgment call was MBQ-62's own classification analysis,
  performed with the same strictness DEC-018 applied, and transparently
  documented in DEC-019 §4/§8 rather than asserted. **Repeated issue
  patterns:** none newly triggered. **Rules/checklists updated:** none this
  session (out of allowed-files scope). **New rejected approaches:** none —
  no new architecture proposed; checked against `rejected-approaches-log.md`
  in full before drafting DEC-019, confirmed no row addresses job-source
  vocabulary and nothing is reintroduced. **New technical debt:** none (no
  code; nothing to compromise). **New open questions:** none added — MBQ-62's
  own text and status are unchanged; only a proposal-citation note was added
  to its row, and a compact top-of-register note was added; no other MBQ row
  touched. **Architecture concerns:** none — no accepted DEC (DEC-003–018),
  AR (AR-002–015), or Part A–E design content was changed; DEC-019 proposes
  a narrow vocabulary extension for ChatGPT's own review, not a self-accepted
  resolution.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (none new) · rejected approaches checked, none
  added · technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** ChatGPT's review of DEC-019/AR-016. If
  accepted: (1) apply DEC-019 §6's pre-drafted register-impact wording to
  `master-blueprint-open-questions.md`'s MBQ-62 row as its own
  acceptance-patch session (mirroring the DEC-013–018 pattern); (2) the
  separate MBQ-64/MBQ-65 currency/webhook residual decision sprint. If
  rejected or revised: rework DEC-019 per ChatGPT's specific feedback before
  any register change. Neither path is implementation.
- **Stop condition:** stopped after opening the draft PR for DEC-019/AR-016
  against `Shopify-connector` (not merged). DEC-003 through DEC-018 not
  edited; AR-002 through AR-015 not edited; no MBQ row other than MBQ-62
  touched, and MBQ-62 not marked resolved; MBQ-64/MBQ-65 unchanged; no code
  files changed; DEC-019 and AR-016 are both **Proposed for ChatGPT review —
  NOT accepted**; implementation remains **blocked**; the implementation
  gate remains **closed**; `main` and plain `dev` untouched. Awaiting
  ChatGPT review.
- **DEC-019 clarification patch (2026-07-04, same PR #82):** ChatGPT's
  REVISE review flagged one ambiguity — DEC-019 proposed `odoo_event` as the
  seventh job-source value but then said "the exact Selection-field/enum
  identifier string remains implementation planning," which could be read
  as leaving `odoo_event` itself unresolved. Clarified in DEC-019 §5/§6 and
  in AR-016's risk/mitigation wording: `odoo_event` is the **proposed
  semantic job-source value** (settled if DEC-019 is accepted, not an open
  question), and only its Odoo **implementation mechanics** (model/field
  names, Python constants, XML IDs, storage/Selection-field mechanics,
  trigger-origin field/model implementation, MBQ-16 retry constants) remain
  implementation planning. **DEC-019 is still Proposed for ChatGPT review —
  NOT accepted; AR-016 unchanged in status; MBQ-62 not resolved; MBQ-64/65
  unchanged; no code files changed; implementation remains blocked; the
  implementation gate remains closed.**
- **Final odoo_event ambiguity cleanup (2026-07-04, same PR #82):**
  ChatGPT's follow-up REVISE flagged one leftover sentence in DEC-019 §3
  ("Out of scope") still describing `odoo_event` as "a conceptual
  vocabulary label, not a committed code identifier" — read together with
  the earlier clarification, this could still be misread as leaving
  `odoo_event` itself undecided. Corrected: `odoo_event` is **no longer
  described as only a conceptual placeholder** — §3 now states plainly
  that, if accepted, `odoo_event` is the accepted semantic Part A §D.2
  job-source value, and only its Odoo implementation mechanics (model/field
  placement, Python constant naming, XML IDs, storage/Selection-field
  mechanics, trigger-origin field/model implementation, MBQ-16 retry
  constants) remain implementation planning. **DEC-019 is still Proposed
  for ChatGPT review — NOT accepted; MBQ-62 still unresolved; MBQ-64/65
  unchanged; no MBQ row edited; no code files changed; implementation
  remains blocked; the implementation gate remains closed.**

---

### DEC-018 Acceptance Patch — MBQ Decision Batch 1 accepted except MBQ-62 — compact handoff (2026-07-04)

> **Documentation-only acceptance patch, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #81 head
> commit `eaceb7f1591d1612207a0ae49246408223da7273` (branch
> `claude/mbq-decision-batch-1-51hysj`, based on `Shopify-connector` at PR
> #80 merge commit `403d17fc16c6854b0bd9f3ce3161ff61cc0e1570`); DEC-003
> through DEC-017 confirmed Accepted by ChatGPT and unedited; DEC-018
> confirmed previously Proposed for ChatGPT review, not accepted;
> implementation confirmed still blocked.

- **Branch / PR:** `claude/mbq-decision-batch-1-51hysj` → PR #81 into
  `Shopify-connector` (not merged).
- **Files changed:** `docs/04-decisions/DEC-018-mbq-decision-batch-1.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-017 file changed. No `docs/04-decisions/README.md` change. No code
  file changed. No Python/XML/manifest/security/test/CI file changed.**
- **What changed:** ChatGPT reviewed proposed DEC-018/AR-015 and **accepted
  Batch 1 except MBQ-62** on 2026-07-04. **DEC-018 is now Accepted by
  ChatGPT.** **AR-015 is now Accepted by ChatGPT.** Ten MBQ rows were
  updated in `master-blueprint-open-questions.md` with the accepted
  register-impact wording (dated 2026-07-04): **MBQ-06** (readiness-check
  essential-vs-nice-to-have split), **MBQ-08** (disconnect data-retention
  posture), **MBQ-17** (reconciliation posture only), **MBQ-33** (first-push
  guard granularity), **MBQ-34** (ongoing apply-mode default), **MBQ-41**
  (notification-UI granularity), **MBQ-45** (roles→groups mapping/surface
  split), **MBQ-52** (API-version pinning policy only), **MBQ-54**
  (uninstall/disable posture only), **MBQ-60** (`stock_delivery`/`delivery`
  dependency). **MBQ-62 was split to a dedicated follow-up DEC** — its row
  received only a short split-note citation, its substance is unchanged and
  it remains open. **MBQ-64 and MBQ-65 remain unchanged/excluded**, reserved
  for a separate currency/webhook residual decision sprint. **No other MBQ
  row was touched.** **No implementation started.**
- **Items deferred:** a dedicated follow-up DEC for MBQ-62's job-source
  vocabulary question; the separate MBQ-64/MBQ-65 currency/webhook residual
  decision sprint; the implementation-gate-opening act; all implementation;
  all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session mechanically applied ChatGPT's acceptance decision to the
  repository, precisely scoping what was and was not decided (MBQ-62
  explicitly excluded from the accepted set). **Repeated issue patterns:**
  none newly triggered. **Rules/checklists updated:** none this session
  (out of allowed-files scope). **New rejected approaches:** none — no new
  architecture proposed or reopened. **New technical debt:** none (no
  code; nothing to compromise). **New open questions:** none added — only
  the ten accepted rows' status wording and MBQ-62's split-note were
  updated; MBQ-64/MBQ-65 untouched. **Architecture concerns:** none — no
  accepted DEC (DEC-003–017), AR (AR-002–014), or Part A–E design content
  was changed; only DEC-018/AR-015's own acceptance status and the ten
  MBQ rows' wording were updated.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none triggered) — all **YES**.
- **Next recommended session:** a **dedicated follow-up DEC for MBQ-62**
  (Odoo-side event-triggered job-source classification), then the
  **separate MBQ-64/MBQ-65 currency/webhook residual decision sprint**.
  Neither is implementation.
- **Stop condition:** stopped after committing and pushing this acceptance
  patch to the existing PR #81 branch (not merged). DEC-003 through
  DEC-017 not edited; no MBQ row other than the ten accepted rows (plus
  MBQ-62's split-note) modified; no code files changed; DEC-018 and AR-015
  are now **Accepted by ChatGPT** (Batch 1 except MBQ-62); implementation
  remains **blocked**; the implementation gate remains **closed**; `main`
  and plain `dev` untouched. Awaiting further instruction.

---

### Proposed MBQ Decision Batch 1 — DEC-018 prepared, not accepted — compact handoff (2026-07-04)

> **Decision-preparation session, NOT implementation, NOT an
> implementation-gate opening, NOT a MBQ resolution.** Confirmed before
> editing: current branch based on `Shopify-connector` at PR #80 merge
> commit `403d17fc16c6854b0bd9f3ce3161ff61cc0e1570`; DEC-003 through
> DEC-017 confirmed Accepted by ChatGPT and unedited; AR-002 through AR-014
> confirmed Accepted; implementation confirmed still blocked.

- **Branch / PR:** `claude/mbq-decision-batch-1-51hysj` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:**
  `docs/04-decisions/DEC-018-mbq-decision-batch-1.md` (new),
  `docs/05-qa/architecture-review-log.md` (AR-015 added),
  `docs/03-architecture/master-blueprint-open-questions.md` (compact note
  only), `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (compact note only), `docs/01-research/research-handoff.md` (this file).
  **No DEC-003 through DEC-017 file changed. No `docs/04-decisions/README.md`
  change. No MBQ row edited or marked resolved. No code file changed. No
  Python/XML/manifest/security/test/CI file changed.**
- **MBQ Decision Batch 1 prepared.** DEC-018 proposes recommended decisions,
  with evidence/options/risk/register-impact wording, for **MBQ-06, MBQ-08,
  MBQ-17 (posture), MBQ-33, MBQ-34, MBQ-41, MBQ-45 (mapping/surface split),
  MBQ-52, MBQ-54, and MBQ-60** — each adopting a direction an already-
  accepted Master Blueprint part (mostly DEC-013/DEC-015) already carried as
  a ChatGPT-owned recommendation. **DEC-018 is proposed, not accepted.**
  **AR-015 is proposed, not accepted.** **MBQ-62** is deliberately **not**
  forced into this batch — checked against all six fixed Part A §D.2
  job-source values, none found defensible, recommended for its own
  follow-up DEC instead of repeating Fable's already-corrected finding-C2
  failure mode. **MBQ-64 and MBQ-65 remain excluded**, reserved for a
  separate currency/webhook residual decision sprint per this session's own
  scope instruction. **No MBQ row is resolved.** **No implementation
  started.**
- **Items deferred:** ChatGPT's actual review/acceptance of DEC-018/AR-015;
  if accepted, the register-impact wording drafted in DEC-018 §5 (not
  applied by this session); MBQ-62's own follow-up DEC; the separate
  MBQ-64/MBQ-65 currency/webhook residual sprint; the implementation-gate-
  opening act; all implementation; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session's only judgment call was MBQ-62's strict mapping analysis, which
  concluded (transparently, in DEC-018 §4) that no existing Part A job-source
  value fits and recommended a split rather than asserting a weak answer.
  **Repeated issue patterns:** none newly triggered. **Rules/checklists
  updated:** none this session (out of allowed-files scope). **New rejected
  approaches:** none — no new architecture proposed; checked against
  `rejected-approaches-log.md` (RA-008, RA-009, full RA-001–023 list) before
  drafting DEC-018, none reintroduced. **New technical debt:** none (no
  code; nothing to compromise). **New open questions:** none added — no MBQ
  row's own text or status was changed by this session; DEC-018 only
  proposes wording that would apply if and when accepted. **Architecture
  concerns:** none — no accepted DEC (DEC-003–017), AR (AR-002–014), or
  Part A–E design content was changed; only a compact, non-substantive
  cross-reference note was added to the open-questions register and to the
  Part E bridge document.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (none new) · rejected approaches checked, none
  added · technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none triggered) — all **YES**.
- **Next recommended session:** ChatGPT's review of DEC-018/AR-015. If
  accepted: (1) apply DEC-018 §5's drafted register-impact wording to
  `master-blueprint-open-questions.md` as its own acceptance-patch session
  (mirroring the DEC-013–017 pattern); (2) a dedicated follow-up DEC for
  MBQ-62's job-source-vocabulary question; (3) a separate MBQ-64/MBQ-65
  currency/webhook residual decision sprint. None of these is implementation.
- **Stop condition:** stopped after opening the draft PR for DEC-018/AR-015
  against `Shopify-connector` (not merged). DEC-003 through DEC-017 not
  edited; AR-002 through AR-014 not edited; no existing MBQ row modified or
  marked resolved; no code files changed; DEC-018 and AR-015 are both
  **Proposed for ChatGPT review — NOT accepted**; implementation remains
  **blocked**; the implementation gate remains **closed**; `main` and plain
  `dev` untouched. Awaiting ChatGPT review.

---

### DEC-017 Acceptance Patch — Master Blueprint Part E accepted — compact handoff (2026-07-04)

> **Documentation-only acceptance patch, not implementation, not an
> implementation-gate opening.** Confirmed before editing: PR #80 head
> commit `e4e1fd5b2d2c4fafdaa57c4b025d5234611b44b6` (branch
> `claude/master-blueprint-part-e-ia05hx`, based on `Shopify-connector` at
> PR #79 merge commit `77ee511036a98db36262bdbc9b4ae4371a2d85f8`); DEC-003
> through DEC-016 confirmed Accepted by ChatGPT and unedited; Part E
> confirmed previously Proposed for ChatGPT review, not accepted;
> implementation confirmed still blocked.

- **Branch / PR:** `claude/master-blueprint-part-e-ia05hx` → PR #80 into
  `Shopify-connector` (not merged).
- **Files changed:** `docs/04-decisions/DEC-017-master-blueprint-implementation-planning-bridge.md`
  (new), `docs/04-decisions/README.md`,
  `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`,
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC-003 through
  DEC-016 file changed. No code file changed. No Python/XML/manifest/
  security/test/CI file changed. No `shopify-official-api-notes.md` or
  `odoo-official-architecture-notes.md` change (facts already cited;
  acceptance touches status/cross-reference wording only, in the allowed
  files).**
- **What changed / residue fixed:** ChatGPT reviewed PR #80 and accepted its
  substance via new decision record **DEC-017**. This patch carries that
  acceptance into the repository: **Master Blueprint Part E** is now
  **Accepted by ChatGPT via DEC-017**, as a **documentation-only
  implementation-planning bridge** — the MBQ decision plan, proposed
  implementation sequence, first-safe-implementation-slice recommendation,
  and test/rollback strategy are accepted **as planning guidance only**,
  not as decisions or authorizations. **AR-014** moves to **Accepted by
  ChatGPT**. **MBQ-64** is now **partially resolved at fact-verification
  level** — Shopify's `MoneyBag`/`shopMoney`/`presentmentMoney` order-money
  model and Odoo's single computed `sale.order.currency_id` are accepted as
  verified facts; the design/selection mechanism (which money field is
  compared against `currency_id`, and how a mismatch is classified/guarded)
  **remains open**. **MBQ-65**'s topic strings (`PRODUCTS_CREATE`/
  `PRODUCTS_UPDATE`/`PRODUCTS_DELETE`) are now **resolved at
  fact-verification level only** — the payload-shape/subscription-scope/
  Phase-1-implementation-scope residual **remains open**, mirroring MBQ-63.
  **No ChatGPT-batch MBQ item (MBQ-06/08/17/33/34/41/45/52/54/60/62) is
  decided by this acceptance.** `master-blueprint.md`'s Part E references
  (Status section, sprint-structure table row, "Domain blueprints still
  pending" section, DEC/AR range mentions) all moved from "Proposed for
  ChatGPT review — NOT accepted" to "Accepted by ChatGPT via DEC-017" —
  **no accepted Part A–D status was touched or weakened.**
  `docs/04-decisions/README.md` gained a DEC-017 entry in the decision
  index.
- **Items deferred:** the MBQ decision plan's own ChatGPT-batch decisions
  (MBQ-06/08/17/33/34/41/45/52/54/60/62, roughly) — a dedicated decision
  session is the recommended next step; MBQ-64's design/selection
  mechanism; MBQ-65's payload/subscription/scope residual; a separate,
  explicit ChatGPT implementation-gate-opening act; all implementation; all
  implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session mechanically applied ChatGPT's acceptance decision to the
  repository, with no new judgment calls beyond precisely scoping what the
  acceptance does and does not cover. **Repeated issue patterns:** none
  newly triggered. **Rules/checklists updated:** none this session (out of
  allowed-files scope). **New rejected approaches:** none — no new
  architecture proposed or reopened. **New technical debt:** none (no
  code; nothing to compromise). **New open questions:** none added — only
  MBQ-64/MBQ-65's existing status wording updated to reflect DEC-017's
  fact-verification-level acceptance; both remain open for their own
  residual questions. **Architecture concerns:** none — no accepted DEC
  (DEC-003–016), AR (AR-002–013), or Part A–D design content was changed;
  only Part E's own acceptance status and the two new MBQ rows' status
  wording were updated.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none triggered) — all **YES**.
- **Next recommended session:** the **MBQ decision plan's ChatGPT-batch
  decisions** (Part E document §4) — the largest remaining lever before the
  implementation gate can meaningfully be considered for opening. Not
  implementation code.
- **Stop condition:** stopped after committing and pushing this acceptance
  patch to the existing PR #80 branch (not merged). DEC-003 through
  DEC-016 not edited; no existing MBQ row (other than MBQ-64/65's own
  status wording) modified; no code files changed; Part E is now
  **Accepted by ChatGPT via DEC-017**, documentation-only; implementation
  remains **blocked**; the implementation gate remains **closed**; `main`
  and plain `dev` untouched. Awaiting further instruction.

### Master Blueprint Part E — Implementation-Planning Bridge — compact handoff (2026-07-04)

> **Documentation-only planning bridge, not implementation, not an
> implementation-gate opening.** Confirmed before editing: branch
> `claude/master-blueprint-part-e-ia05hx` based on `Shopify-connector` at
> merge commit `77ee511036a98db36262bdbc9b4ae4371a2d85f8` (PR #79, Part D/
> `master-blueprint.md` residue-alignment cleanup); DEC-003 through DEC-016
> confirmed Accepted by ChatGPT and unedited; Part E confirmed previously
> Not started; implementation confirmed still blocked.

- **Branch / PR:** `claude/master-blueprint-part-e-ia05hx` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:** `docs/03-architecture/master-blueprint-implementation-planning-bridge.md`
  (new), `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/01-research/shopify-official-api-notes.md`,
  `docs/01-research/odoo-official-architecture-notes.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No DEC file changed.
  No code file changed. No Python/XML/manifest/security/test/CI file
  changed.**
- **What changed / residue fixed:** opened the first Part E session,
  directly executing the PR #78 audit's own §10 "Required Part E focus
  areas" as scoped work — (1) an **MBQ decision plan** in the new Part E
  document routing every "Blocks implementation: Yes" row (MBQ-01 through
  MBQ-63) to a decision owner, decision type, and recommended timing, none
  resolved or closed by the table itself; (2) **official-doc research**
  closing two of the three currently-untracked gaps the PR #78 audit
  flagged: Shopify's `MoneyBag`/presentment-currency order-money model
  (`shopMoney`/`presentmentMoney`, verified against `shopify.dev`) and
  Odoo's single computed `sale.order.currency_id` (verified against
  official 19.0 source), both added to the research notes and folded into
  new register row **MBQ-64** (a design/selection question, not resolved);
  Shopify's product-domain webhook topic strings (`PRODUCTS_CREATE`/
  `PRODUCTS_UPDATE`/`PRODUCTS_DELETE`, verified against the official
  `WebhookSubscriptionTopic` enum) folded into new register row **MBQ-65**
  (topic strings **proposed resolved at fact-verification level only**,
  pending ChatGPT acceptance; payload/subscription/scope residual stays
  open, mirroring MBQ-63); (3) a **proposed module-by-module implementation
  sequence** following the already-accepted DEC-008 dependency DAG; (4) a
  **first-safe-implementation-slice recommendation** (the job/log/error
  abstraction skeleton, MBQ-19/20/21 — not authorized); (5) test-strategy
  and rollback-strategy notes at planning level; (6) a restated no-code-to-
  code gate checklist confirming **2 of 5 criteria currently satisfied**.
  `master-blueprint.md` was updated with a minimal Part E status
  reference only (Proposed for ChatGPT review, not accepted; implementation
  remains blocked) — no accepted Part A–D status was touched.
  `master-blueprint-open-questions.md` gained the two new rows above plus a
  compact Sprint E note; **no existing MBQ row was modified, resolved, or
  silently changed.** `architecture-review-log.md` gained **AR-014**,
  logged **Proposed for ChatGPT review**, not accepted.
- **Items deferred:** the ~45 implementation-blocking MBQ rows themselves
  (routed, not resolved, by the decision plan); the actual ChatGPT-batch
  decisions the plan recommends (MBQ-06/08/17/33/34/41/45/52/54/60/62,
  roughly); the separate, explicit ChatGPT implementation-gate-opening act;
  all implementation; all implementation tasks.
- **Learning feedback loop:** **New issues discovered:** none — this
  session applied the PR #78 audit's own recommended scope without new
  judgment calls beyond the two official-doc checks it specified.
  **Repeated issue patterns:** none newly triggered. **Rules/checklists
  updated:** none this session (out of allowed-files scope). **New rejected
  approaches:** none — no new architecture proposed, only a planning/
  sequencing bridge over already-accepted architecture. **New technical
  debt:** none (no code; nothing to compromise). **New open questions:**
  MBQ-64 (currency) and MBQ-65 (product webhook topics), both logged
  Proposed/Open per `CLAUDE.md` §7/§8. **Architecture concerns:** none — no
  accepted decision, MBQ resolution, or Part A–D design content was
  changed; only planning/sequencing/research content was added.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (MBQ-64/65 logged) · rejected approaches
  checked, none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none triggered) — all **YES**.
- **Next recommended session:** the **MBQ decision plan's ChatGPT-batch
  decisions** (Part E document §4) — a cheap, high-leverage next step since
  those rows already carry a recommendation and only need ChatGPT's actual
  decision, not new research — followed by, only once ChatGPT is ready, a
  separate, explicit implementation-gate-opening act. Not implementation
  code.
- **Stop condition:** stopped after opening one draft PR into
  `Shopify-connector` (not merged, not marked ready for review). DEC-003
  through DEC-016 not edited; no existing MBQ row modified/resolved; no
  code files changed; Part E remains **Proposed for ChatGPT review, not
  accepted**; implementation remains **blocked**; the implementation gate
  remains **closed**; `main` and plain `dev` untouched. Awaiting further
  instruction.

### Part D Blueprint Status Alignment — compact handoff (2026-07-04)

> **Documentation-only residue cleanup, not implementation, not Part E.**
> Confirmed before editing: `Shopify-connector` at merge commit
> `b3e2274ff4c3f70a61664a3b12753e5e69b9bf6b` (PR #78, Master Blueprint
> Integrity & Competitor Advantage Audit); DEC-003 through DEC-016
> confirmed Accepted by ChatGPT and unedited; Part E confirmed Not started;
> implementation confirmed still blocked. This session applies exactly the
> cleanup PR #78's audit identified as required before Part E: the Part D
> blueprint document's own stale status residue, and two one-line stale
> DEC/AR ranges in `master-blueprint.md` itself.

- **Branch / PR:** `claude/part-d-blueprint-status-alignment` → draft PR
  into `Shopify-connector` (not merged).
- **Files changed:** `docs/03-architecture/master-blueprint-ui-ux-screen-design.md`,
  `docs/03-architecture/master-blueprint.md`, `docs/01-research/research-handoff.md`
  (this file). **No DEC file changed. No MBQ register row changed. No code
  file changed.**
- **What changed / residue fixed:**
  - `master-blueprint-ui-ux-screen-design.md` (Part D): its own `## Status`
    section, top summary blockquote, claim-label legend, §20 open-questions
    intro, and §22 "Implementation remains blocked" section all still read
    "Proposed for ChatGPT review — NOT accepted" (or equivalent
    "unless/until DEC-016 is accepted" / "if later accepted, accepted"
    phrasing), even though its companion DEC-016 was accepted by ChatGPT on
    2026-07-04. All five spots corrected to state: Part D is **Accepted by
    ChatGPT via DEC-016**, acceptance date 2026-07-04, **accepted at
    screen-design blueprint level only**, not implementation-authorizing,
    not a pixel-level UI/final-wireframe approval; MBQ-53 is **partially
    resolved at screen-design blueprint level only**, with sibling rows
    MBQ-03/MBQ-22/MBQ-44/MBQ-45/MBQ-06 and open recommendations
    MBQ-33/MBQ-34/MBQ-41/MBQ-35/MBQ-32 and MBQ-60 through MBQ-63 all
    explicitly still open; the `sh_shopify_connector` "Daily Queue Activity
    Tracking" chart idea remains an explicitly deferred, not-adopted
    candidate; Part E remains Not started; implementation remains blocked
    pending a separate, explicit ChatGPT implementation-gate approval. No
    screen-design content (specs, tables, checklists) was changed — only
    status/label wording.
  - `master-blueprint.md`: fixed the two one-line staleness spots the PR
    #78 audit identified — the intro blockquote's "converts the accepted
    decision records (DEC-003 through DEC-015)" corrected to "DEC-003
    through DEC-016," and "AR-002 through AR-012 are all Accepted"
    corrected to "AR-002 through AR-013 are all Accepted." No other line in
    this file was touched.
- **Items deferred:** the ~45 implementation-blocking open MBQs (unchanged,
  none resolved by this cleanup); the two small currency-research items and
  the product-webhook-topic MBQ row the PR #78 audit recommended (§10);
  Part E (implementation-planning bridge); all implementation.
- **Learning feedback loop:** **New issues discovered:** none — this
  session mechanically applied the exact residue fixes PR #78's audit
  specified, with no new judgment calls. **Repeated issue patterns:** the
  Part D status-residue defect is now fixed at its source; no further
  occurrence expected unless a future acceptance patch repeats the pattern
  of not touching the blueprint document's own Status header. **Rules/
  checklists updated:** none this session (out of allowed-files scope).
  **New rejected approaches:** none — no design content changed. **New
  technical debt:** none (no code; this was a documentation-residue fix,
  not a compromise). **New open questions:** none — no MBQ row added,
  resolved, or modified. **Architecture concerns:** none — no accepted
  decision, MBQ resolution, or design content changed; only status/label
  wording was aligned to already-accepted fact.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new) · rejected approaches
  checked, none added · technical debt logged (none applicable — no code)
  · repeated-issue escalation applied (defect fixed at source) — all
  **YES**.
- **Next recommended session:** **Master Blueprint Part E —
  implementation-planning bridge**, starting with the MBQ decision plan and
  the two small currency-research/product-webhook-topic items (PR #78
  audit §10) — not implementation code; implementation only after a
  separate, explicit ChatGPT gate.
- **Stop condition:** stopped after one commit on a new draft PR into
  `Shopify-connector` (not merged, not marked ready for review). DEC-003
  through DEC-016 not edited; `master-blueprint-open-questions.md` not
  edited; no code files changed; Part E remains **Not started**;
  implementation remains **blocked**; `main` and plain `dev` untouched.
  Awaiting further instruction.

### Master Blueprint Integrity & Competitor Advantage Audit — compact handoff (2026-07-04)

> **Documentation-only audit, not implementation, not Part E.** Confirmed
> before editing: branch `claude/master-blueprint-audit-ngu1k9` based on
> `Shopify-connector` at merge commit
> `747bee86b4b1687afbbf1d150c6f808ece411670` (PR #77, DEC-016 acceptance);
> DEC-003 through DEC-016 confirmed Accepted by ChatGPT and unedited; Part E
> confirmed Not started; implementation confirmed still blocked.

- **Branch / PR:** `claude/master-blueprint-audit-ngu1k9` → draft PR into
  `Shopify-connector` (not merged).
- **Files changed:** `docs/05-qa/master-blueprint-integrity-competitor-advantage-audit.md`
  (new), `docs/01-research/research-handoff.md` (this file). **No DEC, no
  architecture blueprint, no code files changed.**
- **What changed / residue fixed:** ran a strict pre-Part-E integrity audit
  across accepted decisions (DEC-003–016), the MBQ open-questions register,
  competitor research, and the rejected-approaches log. **Verdict: READY FOR
  PART E WITH CONDITIONS.** No contradiction found between DEC-003 through
  DEC-016; no accepted decision authorizes implementation or silently
  resolves an MBQ that should stay open; DEC-016's screen-design-only scope
  boundary for Part D is correctly and consistently stated everywhere it
  appears. All 23 rejected approaches (RA-001–023) checked against Parts
  A–D — none reintroduced, none drifting; the 9 named guardrail themes all
  map cleanly to specific RA rows. Competitor advantage assessed:
  idempotency + reconciliation + rate-limit-aware throttling, the unified
  command-center + recovery-first error center, and per-location inventory
  identity are confirmed accepted-architecture differentiators no competitor
  combines; the `sh_shopify_connector` "Daily Queue Activity Tracking" chart
  is confirmed **explicitly deferred, not adopted**; the pixel-level
  screenshot-inspection limitation is confirmed and restated precisely (page→
  markdown/caption/alt-text only, never pixel-rendered — a same-session
  headless-browser attempt was abandoned rather than disable TLS
  verification). **One documentation defect found and logged, not fixed
  this session** (out of this audit's allowed-files scope):
  `docs/03-architecture/master-blueprint-ui-ux-screen-design.md`'s own
  `## Status` section and claim-label legend still read "Proposed for
  ChatGPT review — NOT accepted" (dated 2026-07-03) even though its
  companion DEC-016 was accepted 2026-07-04 and every other document in the
  chain was correctly updated — the DEC-016 acceptance-patch commit's file
  list never included this file. This is the same defect pattern already
  caught and fixed once for Part C (see the "DEC-015 Acceptance Patch — Part
  C blueprint document alignment" entry below); the identical alignment step
  was never performed for Part D. Full findings, the MBQ routing table, and
  the RA guardrail table are in the audit file itself.
- **Update (same session, after the PR's first commit):** the parallel
  7-agent Workflow cross-check mentioned above **completed successfully on
  a resume** after the session limit reset (7/7 agents, 0 errors), and its
  findings were read, verified, and folded into the audit file as a second
  commit on the same PR before this note. It **independently corroborated
  every finding** already in the audit (the Part D status-header defect was
  independently found by 5 of the 7 agents without their reading each
  other's output) and added a small number of new, independently-verified
  items: two one-line staleness spots in `master-blueprint.md` itself (line
  5's "DEC-003 through DEC-015," line 72's "AR-002 through AR-012," both
  missing their DEC-016/AR-013 update); a procedural-ambiguity note that
  `quality-feedback-loop.md` §10/§11 are still bracketed
  "`[Recommendation — becomes binding when this PR is merged by ChatGPT]`"
  even though `master-blueprint.md`'s gate-opening criterion 3 relies on
  §10 as settled; two previously-untracked official-doc gaps (Shopify/Odoo
  multi-currency handling, which underpins the "mandatory and permanent"
  order total-check guard, with no MBQ row yet); and a missing MBQ row for
  the product-domain webhook-topic-string gap. None of these changes the
  verdict or reopens Parts A/B/C; all are folded into the audit file's §3,
  §5, §6, §7, §9, and §10 as "cross-check addendum" items.
- **Items deferred:** all ~45 implementation-blocking open MBQs (per the
  audit's §4 routing table); the Part D document-alignment fix (§9 of the
  audit; requires a separate small session since the file is outside this
  audit's allowed-files scope); a later pixel-level visual-design pass
  (where the deferred `sh_shopify_connector` activity-chart idea can be
  reconsidered); Part E (implementation-planning bridge); all
  implementation.
- **Learning feedback loop:** **New issues discovered:** the Part D status-
  residue defect above (one instance — logged, not yet fixed). A planned
  7-agent parallel research fan-out (Workflow tool) to independently cross-
  check every audit dimension failed on an account-level session usage
  limit on all 7 runs; a resume after the limit reset completed
  successfully (7/7 agents, 0 errors), and its findings were read,
  independently re-verified, and folded into the audit file as cross-check
  addendum items (see the Update bullet above and the audit file §1, §3,
  §5, §6, §7, §9, and §10). The audit still discloses that the largest
  competitor-research files were spot-checked rather than read line-by-line
  (see the audit file §11). **Repeated issue patterns:** the Part D status-
  residue defect is a recurrence of the same "blueprint acceptance patch
  doesn't always touch the blueprint document's own Status header" pattern
  already seen once for Part C — worth a checklist addition (see below).
  **Rules/checklists updated:** none this session (a checklist addition for
  future acceptance patches — "verify the blueprint document's own Status
  header, not just the DEC/index/register/log/handoff — was updated" — is
  recommended but not applied here, since `pr-review-checklist.md` is
  outside this audit's allowed-files scope). **New rejected approaches:**
  none — `rejected-approaches-log.md` checked in full; nothing reintroduced.
  **New technical debt:** none (no code; the Part D residue is a
  documentation defect, not a deferred implementation compromise, so it is
  not logged in `technical-debt-register.md`). **Architecture concerns:**
  none new — no accepted decision, MBQ resolution, or rejected-approach
  status was found to be wrong; the one defect found is cosmetic/status-
  label only and does not change what is actually accepted (DEC-016 itself,
  the MBQ register, the index, and the AR-log are all correct).
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured · rejected approaches checked, none added ·
  technical debt logged (none applicable — no code, and the one defect found
  is a documentation-label residue, not accepted technical debt) ·
  repeated-issue escalation applied (noted as a first recurrence, below the
  2nd-occurrence checklist-update threshold since the underlying documents
  it would touch are outside this session's allowed files) — all **YES**.
- **Next recommended session:** 1) a small, separate documentation-only
  session to fix the Part D status-header/claim-label residue in
  `master-blueprint-ui-ux-screen-design.md` (mirroring the Part C alignment
  fix); 2) **Master Blueprint Part E — implementation-planning bridge**,
  starting with the MBQ decision plan (audit §10), not implementation code;
  3) implementation only after a separate, explicit ChatGPT gate.
- **Stop condition:** stopped after committing the audit file and this
  handoff entry on the audit branch, opening one draft PR into
  `Shopify-connector` (not merged). DEC-003 through DEC-016 not edited; no
  architecture blueprint file edited; no code files changed; no MBQ register
  row modified; Part E remains **Not started**; implementation remains
  **blocked**. Awaiting ChatGPT review.

---

### Master Blueprint Sprint D — UI/UX Screen Design Blueprint — compact handoff (2026-07-03)

> **Documentation-only proposal sprint, not implementation.** Confirmed
> before editing: base commit `b6199f78064ae4e1934bccee630a14b3d7eef438`
> (Accept Master Blueprint Sprint C Inventory and Fulfillment — DEC-015,
> PR #74); DEC-003 through DEC-015 confirmed still **Accepted by ChatGPT**
> and unedited; Master Blueprint Part D confirmed **Not started** before this
> sprint; DEC-012's ten operator flows and Part A/B/C confirmed accepted and
> reused, not re-derived; implementation confirmed still blocked; Part E
> confirmed not started; `rejected-approaches-log.md` checked, no rejected
> approach reintroduced. Branch
> `claude/master-blueprint-sprint-d-screen-3jmyd0`.
>
> **Note on duplicate-PR reconciliation.** A duplicate Sprint D proposal did
> exist on a separate branch, `claude/master-blueprint-sprint-d-ui-ux-screen-design`
> (head `27d521e`), opened as **PR #75** — open, draft, unmerged, based on the
> same DEC-015 base (`b6199f7`). PR #75 was superseded because this branch's
> PR #77 was confirmed canonical after ChatGPT-directed status cleanup and the
> capability-audit strengthening described below. A small salvage audit then
> compared PR #75 against PR #77; four safe, additive completeness items
> found only in PR #75 (a persistent connection-health indicator note in the
> navigation section, an operation-key/MBQ-20/21 citation on the sync-center
> operation-reference field, a missing Open-MBQ-deps bullet on the
> order-import touchpoints screen, and an MBQ-09 citation on the customer
> screen) were salvaged into PR #77 in commit `17912cd6`. PR #75 was then
> **closed as superseded by PR #77, not merged**. PR #77 remains
> **canonical, open, draft, not merged**; DEC-016 / AR-013 / Part D remain
> Proposed, not accepted; Part E remains Not started; implementation remains
> blocked. (This corrects an earlier version of this handoff, which
> incorrectly stated that PR #75, its branch, and its head commit did not
> exist.) Flagged for ChatGPT.

- **Branch / PR:** `claude/master-blueprint-sprint-d-screen-3jmyd0`
  → **draft PR #77** into `Shopify-connector`, **not merged**, **not** marked
  ready for review (five commits: the proposal commit, the pre-review
  strengthening commit, the duplicate-PR salvage-reconciliation commit, the
  duplicate-PR-history-correction commit, and this session's screenshot-audit +
  Fable-fixes commit — corrects an earlier version of this bullet that was left
  reading "proposal commit + one pre-review strengthening commit" after the
  chain had already grown to four commits).
- **Files changed (cumulative across all 5 commits):**
  `docs/03-architecture/master-blueprint-ui-ux-screen-design.md` (new),
  `docs/04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md` (new),
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/01-research/ux-ui-benchmark.md` (added this session — screenshot audit
  section). **No code files changed. `docs/04-decisions/README.md`
  deliberately not touched** — per the established pattern, proposals do not
  get a README entry until acceptance.
- **What changed:** proposed **Master Blueprint Part D — UI/UX Screen Design
  Blueprint** (`master-blueprint-ui-ux-screen-design.md`, 22 sections):
  screen inventory under the single-shared-surface rule (RA-013); navigation/
  information architecture (proposed menu tree + inter-screen routing +
  role-gated visibility); Odoo-native interaction patterns (reused vs custom,
  blueprint level); a global empty/loading/success/error/manual-review state
  model; blueprint-level screen specs for the setup wizard (11 steps), store
  settings, dashboard (9 cards), sync center (4 filters / 5 actions / 4 retry
  cases), error center + manual-review queue (9 elements / 6 sub-reasons),
  matching center (3 states), product diff (5 states), customer review,
  order-import touchpoints (no dedicated screen — delivering the two DEC-014/
  MBQ-26 error-center extensions), inventory location-mapping/first-push/
  settings, fulfillment log/notification/mismatch, and conceptual permissions/
  roles; a UX-copy/error-message **style guide** (not final copy); cross-screen
  consistency rules; and a premium UI/UX acceptance checklist. Every statement
  labelled per `CLAUDE.md` §8; the fixed 6 job sources / 10 job states / 16
  error classes / 6 manual-review sub-reasons / 4 roles reused **verbatim**;
  **no identifier invented**. Companion **DEC-016** created
  (Status: **Proposed for ChatGPT review — not accepted**). `master-blueprint.md`
  Part D row moved to **Proposed via DEC-016**, Status section and Part D
  detail-section updated, Part E preserved **Not started**.
  `master-blueprint-open-questions.md` **MBQ-53** marked **Proposed partially
  resolved by DEC-016** (stays open until accepted); a Sprint D note added; **no
  other MBQ row changed and no new MBQ added.** `architecture-review-log.md`
  gained **AR-013** (Status: **Proposed**). Grounding was gathered via a
  parallel context-extraction pass over the six accepted context docs
  (Part A/B/C, DEC-012 flows, setup-ux-principles, product-vision) with a
  completeness critic; the critic caught and prevented three Accepted-vs-
  Recommendation attribution slips before drafting (order-import screen status,
  inventory apply-mode, `on_hand` exposure).
- **Pre-review strengthening (2026-07-04, 2nd commit on the same draft PR #77):**
  ran a **capability audit** (discovered the enabled `ui-ux-pro-max` / `design` /
  `product-management` plugins — none docs-critique-applicable under the no-code
  gate, being artifact/code-production oriented; used compensating **six-lens
  expert-review agents** instead: premium design, Odoo-native UX, operator,
  error-recovery, accessibility, adversarial governance) and applied
  documentation-only improvements. Corrected **two Accepted-vs-proposal
  attribution slips** (the sync-center 7-value status grouping §4.1 and the
  connection-status band §6 — now labelled Screen blueprint proposals; the
  grouping also fixed to expose `draft`/`skipped`, no longer narrowing the
  accepted 10-state filter); tightened all MBQ-53 wording to **"proposes to
  partially resolve"**; added **accessibility** rules (never-colour-alone,
  plain-label-not-token, keyboard action order, new §19-H checklist);
  **Odoo-native** affordances (smart buttons + bidirectional routing §3/§2.2;
  activities-based manual-review routing removing the role-gated dead end);
  **recovery/sync-center** strengthening (default "needs attention" filter,
  class-conditional bulk recovery, root-cause grouping, terminal-state/
  `failed_final` affordance); dashboard lead-answer, wizard confidence
  statement, overdue-freshness signal, disconnect-consequence disclosure; and
  **stale-range fixes** in `master-blueprint.md` (accepted range now DEC-003–
  DEC-015 and AR-002–AR-012; AR-013 remains Proposed). **No architecture
  substance changed; no open MBQ decided; no new MBQ added; DEC-016 / AR-013 /
  Part D remain Proposed; Part E not started; implementation blocked.**
- **Screenshot UX benchmark audit + Fable Sprint D review fixes (2026-07-04,
  5th commit on the same draft PR #77):** ChatGPT raised a concern that Part D
  did not visibly show that competitor screenshots were inspected and used to
  make the UI/UX better than public connectors. Ran a **focused competitor
  screenshot UX benchmark audit** (not a full re-collection — the Sprint C/C2
  evidence in `competitor-screenshot-inventory.md`/`ux-ui-benchmark.md` was
  already extensive and dated 2026-06-30/07-01): re-verified six of the eight
  minimum-audit sources today (Webkul, Emipro, VentorTech, `sh_shopify_connector`,
  `ecommerce_shopify` reconfirmed consistent and current; Teqstars docs
  reconfirmed still 403 to the default fetcher user-agent, unchanged); found
  one new, previously-unrecorded detail (`ecommerce_shopify`'s "Live Preview"
  external demo link, not followed — logged as an open item). **Finding:**
  Part D is **transitively** grounded in the screenshot evidence (via
  `setup-ux-principles.md`/`product-vision.md`, both of which are extensively
  screenshot-cited) but carried **no direct citation** of the benchmark or any
  competitor by name — the exact visibility gap ChatGPT flagged. **Decision:**
  a targeted, documentation-only patch was warranted (not a redesign). Added a
  dated audit section to `ux-ui-benchmark.md` (re-verification + a
  rule-by-rule traceability mapping) and a new "Screenshot-evidence lineage"
  note to `master-blueprint-ui-ux-screen-design.md` citing `ux-ui-benchmark.md`
  and `competitor-screenshot-inventory.md` directly, plus a short DEC-016
  addendum (§F) recording the citation as a documentation-traceability
  correction, not a new decision. One gap was identified —
  `sh_shopify_connector`'s demonstrated "Daily Queue Activity Tracking" chart
  has no counterpart in Part D's accepted nine-card dashboard — and was
  **explicitly logged as deferred to a later pixel-design pass (Part E)**, not
  added to the accepted card set (would have changed accepted architecture
  substance, out of scope). Then applied the seven Fable Sprint D review
  findings (F1–F7): **F1** relabelled the "never colour/icon alone" rule (§17
  rule 8) as a Screen blueprint proposal, not Accepted; **F2** corrected six
  places where `setup-ux-principles.md`/`product-vision.md` citations were
  bundled inside an `[Accepted — ...]` bracket (§4 table ×2, §5, §7 ×2, §9,
  §17 header) — split so only the genuine DEC citation stays Accepted and the
  setup-ux/vision reference is explicitly marked recommendation-level, not
  accepted; **F3** corrected this handoff's stale "two commits" wording (the
  **Branch/PR** and **Stop condition** bullets above) to the actual commit
  chain; **F4** fixed `master-blueprint.md`'s stale "Part D ... remain Not
  started" sentence (§"Domain blueprints still pending") to state Part D is
  now Proposed via DEC-016, only Part E remains Not started; **F5** fixed two
  `§2` cross-references that pointed to `§14` (Inventory screens) instead of
  `§16` (Permissions/roles visibility); **F6** added the two missing rejected
  approaches, **RA-017** (no connector-designed idempotency key / binding-alone
  reliance) and **RA-021** (treating Shopify/Odoo quantities as directly
  equivalent without a recorded source-of-truth decision), to the RA guardrail
  list; **F7** reworded the Reviewer role's capability cell (§16) to lead with
  plain language ("Resolve items awaiting manual review"), with
  `blocked_manual_review` moved into a parenthetical, matching the doc's own
  stated labelling rule. Optional Fable findings **N1–N4 were not applied** —
  the screenshot audit did not independently prove any of them necessary as a
  documentation-only addition. **No architecture substance changed; no open
  MBQ decided; no MBQ row added or renumbered; DEC-016 / AR-013 / Part D
  remain Proposed, not accepted; Part E not started; implementation blocked;
  DEC-003 through DEC-015 untouched; `docs/04-decisions/README.md` untouched;
  no code files changed.**
- **Items deferred:** MBQ-53's full closure (awaits DEC-016 acceptance +
  sibling rows MBQ-03/22/44/45/06); the open recommendations MBQ-33/34/41/35/32
  (screens accommodate either resolution, none decided); MBQ-04/05/07/08/13/54/
  55/56/60/61/62/63 (screen-relevant, owned elsewhere, routed not decided);
  primary MVP persona (RB-13); Part E (implementation-planning bridge); all
  implementation.
- **Learning feedback loop:** **New issues discovered:** a duplicate Sprint D
  proposal existed unreconciled for a time — **PR #75** (branch
  `claude/master-blueprint-sprint-d-ui-ux-screen-design`, head `27d521e`,
  open/draft/unmerged) alongside this **PR #77**, both proposing the same
  Part D content; an earlier version of this handoff incorrectly stated that
  PR #75, its branch, and its head commit did not exist. Corrected: PR #75
  **did** exist; it was reconciled via a small salvage audit (four safe,
  additive completeness items merged into PR #77 at commit `17912cd6`) and
  then **closed as superseded by PR #77, not merged**; PR #77 remains
  canonical, open, draft, not merged — reinforces `CLAUDE.md` §3 "if it is
  not in GitHub it does not exist" by verifying actual GitHub PR/branch
  state rather than relying on an in-session assumption. **Repeated issue
  patterns:** the Accepted-vs-Recommendation over-attribution risk (Fable
  findings B3/C1/C2 in Sprints B/C) recurred as a latent drafting risk; mitigated
  proactively via the completeness-critic pass and strict per-statement labels.
  **Rules/checklists updated:** none new (existing label discipline applied).
  **New rejected approaches:** none — log checked, nothing reintroduced. **New
  technical debt:** none (no code). **New open questions:** none — Part D adds no
  MBQ row; it consumes existing ones. **Architecture concerns:** Part D is a
  screen-design proposal only; MBQ-45 (surface split) and the open
  recommendations remain ChatGPT-owned and are accommodated, not decided.
  **Screenshot-audit addendum (2026-07-04):** **new issue discovered:** a
  document can be substantively grounded in cited evidence yet still read as
  ungrounded to a reviewer if the citation chain is one hop removed (Part D
  cited `setup-ux-principles.md`/`product-vision.md` but not the screenshot
  benchmark behind them) — mitigated by adding a direct traceability note
  rather than re-deriving the design. **Repeated issue pattern:** this is a
  new instance of the same Accepted-vs-Recommendation labelling-discipline
  family noted above, applied to evidence *citation depth* rather than
  decision status. **New rejected approaches:** none. **New technical debt:**
  none (no code). **New open questions:** none (the SH activity-chart idea
  was logged as an explicitly deferred idea, not an MBQ row). **Architecture
  concerns:** none new — no accepted card set, screen spec, or DEC changed.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured · rejected approaches checked, none added ·
  technical debt logged (none applicable — no code) · repeated-issue escalation
  applied (label-discipline mitigation, twice) — all **YES**.
- **Next recommended session:** 1) **ChatGPT review of DEC-016 / Part D** (accept,
  revise, or reject); 2) on acceptance, **Master Blueprint Part E —
  implementation-planning bridge**; 3) a future, separate ChatGPT decision on the
  open recommendations MBQ-33/34/41/45/06/35/32; 4) **implementation only after a
  separate ChatGPT gate**, and for any operator-facing screen only after Part D
  is accepted.
- **Stop condition:** stopping after the five-commit chain described in the
  **Branch/PR** bullet above, on the same **draft PR #77** into
  `Shopify-connector` (not merged, not marked ready for review). DEC-003
  through DEC-015 not edited; `docs/04-decisions/README.md` not edited; no
  code files changed; Part D is **Proposed, not accepted**; Part E not
  started; implementation still not authorized; MBQ-53 remains Proposed
  partially resolved / open pending DEC-016 acceptance; MBQ-60 through MBQ-63
  remain open; PR #75 remains closed, not merged; `main` and plain `dev`
  untouched. Awaiting ChatGPT review.

---

### DEC-016 Acceptance Patch — compact handoff (2026-07-04)

> **Documentation acceptance patch, not implementation.** Confirmed
> before editing: PR #77 head at commit
> `b1f1ac9da3893b0d62fb803f0e588f889f8c1ab5` (Sprint D proposal,
> pre-review strengthening, duplicate-PR salvage reconciliation,
> duplicate-PR-history correction, and the screenshot-audit + Fable
> Sprint D review-fixes commits, all on the same branch/PR); DEC-016
> confirmed `Proposed for ChatGPT review`; AR-013 confirmed `Proposed for
> ChatGPT review`; Master Blueprint Part D (UI/UX Screen Design
> Blueprint) confirmed present on PR #77; DEC-003 through DEC-015
> confirmed still **Accepted by ChatGPT** and unedited; implementation
> confirmed still blocked; Part E confirmed not started; PR #75
> confirmed **closed, not merged** (superseded by PR #77, per the
> duplicate-PR reconciliation recorded above). Branch
> `claude/master-blueprint-sprint-d-screen-3jmyd0`.

- **Branch / PR:** `claude/master-blueprint-sprint-d-screen-3jmyd0`
  → draft PR #77 into `Shopify-connector`, **not merged**, **not** marked
  ready for review.
- **Files changed:**
  `docs/04-decisions/DEC-016-master-blueprint-ui-ux-screen-design.md`,
  `docs/04-decisions/README.md`,
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No code files
  changed.**
- **What changed:** **DEC-016 accepted by ChatGPT**, acceptance date
  **2026-07-04**, **at screen-design blueprint level only**, after PR
  #77's duplicate-PR reconciliation (PR #75 closed as superseded, not
  merged), competitor screenshot UX benchmark traceability audit, and
  Fable Sprint D review fixes (F1–F7) — all already applied to this
  branch before this acceptance patch. DEC-016 got a new *Accepted
  decision* section recording the accepted Master Blueprint Part D
  UI/UX Screen Design Blueprint package (items 1–4) and seven explicit
  acceptance points **A–G**: **(A)** single-shared-surface screen
  inventory accepted; **(B)** MBQ-53 partially resolved at screen-design
  level only, sibling rows MBQ-03/22/44/45/06 remain open; **(C)**
  order-import screen-less posture (MBQ-26, DEC-014) restated, not
  re-decided; **(D)** open recommendations MBQ-33/34/41/35/32/45/06
  remain open, not decided; **(E)** no new MBQ row added, confirmed;
  **(F)** premium acceptance checklist and the competitor screenshot
  audit accepted as sufficient traceability for blueprint-level
  acceptance; **(G)** pixel-level visual design / final wireframe
  polish explicitly **not** accepted here, and the `sh_shopify_connector`
  "Daily Queue Activity Tracking" chart idea logged as a **deferred**
  premium candidate, not adopted into the accepted dashboard card set.
  **No implementation-authorizing language anywhere; Part E-not-started
  language preserved throughout.** `architecture-review-log.md`'s
  AR-013 table row moved from "Proposed for ChatGPT review" to "Accepted
  by ChatGPT," with a compact acceptance-patch note appended; AR-002
  through AR-012 rows untouched. `docs/04-decisions/README.md` gained a
  new "Also accepted: DEC-016" entry; DEC-003 through DEC-015 entries
  untouched. `master-blueprint-open-questions.md` updated: its Sprint D
  note superseded by a DEC-016 acceptance note; the MBQ-53 row marked
  **partially resolved by DEC-016 at screen-design blueprint level**
  (stays open/partial, sibling rows MBQ-03/22/44/45/06 explicitly still
  open); MBQ-33/34/41/35/32 rows kept **open recommendations, not decided
  by this acceptance**; MBQ-60 through MBQ-63 left untouched (new and
  open); MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-54 through MBQ-58
  untouched, no question deleted or renumbered, no new MBQ row added.
  `master-blueprint.md`'s status moved to accepted-through-DEC-016
  wording (Part D table row now reads "Accepted by ChatGPT via DEC-016";
  accepted at screen-design blueprint level only); Part E preserved as
  "Not started."
- **Items deferred:** MBQ-03/MBQ-22/MBQ-44/MBQ-45/MBQ-06 (MBQ-53's
  sibling rows, all still open); MBQ-33/34/41/35/32 (recommendations
  noted, not decided by this acceptance); MBQ-60 through MBQ-63
  (untouched, open); MBQ-04, MBQ-08, MBQ-54 through MBQ-58 (untouched,
  open); **pixel-level visual design / final wireframe polish**
  (explicitly deferred, not accepted here — recommended for a later
  pixel-design pass); the `sh_shopify_connector` activity-chart idea
  (deferred premium candidate, not adopted); Part E
  (implementation-planning bridge); all implementation.
- **Learning feedback loop:** **New issues discovered:** none — this
  patch mechanically applied ChatGPT's explicit, itemized acceptance
  scope (accept DEC-016/AR-013/Part D at screen-design level; partially
  resolve MBQ-53; keep every named sibling/detail MBQ open; keep the
  pixel-level and competitor-screenshot-audit caveats explicit; keep
  implementation blocked and Part E not started); no ambiguity required
  a judgment call beyond what the task specified. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new.
  **New rejected approaches:** none — `rejected-approaches-log.md`
  checked, nothing reintroduced. **New technical debt:** none (no code).
  **New open questions:** none — this patch partially resolves MBQ-53
  and confirms every other named row remains open; it adds no new MBQ
  row. **Architecture concerns:** AR-013 is now **Accepted by ChatGPT**
  — Master Blueprint Part D is accepted at screen-design blueprint
  level, with MBQ-53's sibling rows and MBQ-33/34/41/35/32/06/45 and
  MBQ-60 through MBQ-63 explicitly still open; Part E
  (implementation-planning bridge) remains the next recommended sprint,
  not started; implementation remains blocked pending a separate,
  explicit ChatGPT gate.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new this patch) · rejected
  approaches checked, none added · technical debt logged (none
  applicable — no code) · repeated-issue escalation applied (none at
  threshold) — all **YES**.
- **Next recommended session:** 1) **Master Blueprint Part E —
  implementation-planning bridge**, the next recommended sprint; 2) a
  future, separate ChatGPT decision on the open recommendations
  MBQ-33/34/41/45/06/35/32; 3) a later, dedicated **pixel-level
  visual-design pass** (recommended for Part E or a follow-on sprint),
  where the deferred `sh_shopify_connector` activity-chart idea can be
  reconsidered against the accepted nine-card dashboard; 4)
  **Implementation only after a separate ChatGPT gate**, and, for any
  operator-facing screen, only after Part D's screen-design blueprint
  (now accepted) is also carried into exact Odoo IDs/copy/groups via its
  still-open sibling rows.
- **Stop condition:** stopped after one commit on the existing **draft**
  PR #77 into `Shopify-connector` (not merged, not marked ready for
  review). DEC-003 through DEC-015 not edited; no code files changed;
  Part D is **Accepted by ChatGPT via DEC-016, at screen-design
  blueprint level only**; pixel-level visual design not claimed as
  accepted; Part E not started; implementation still not authorized;
  PR #75 remains closed, not merged; `main` and plain `dev` untouched.
  Awaiting further instruction.

---

### DEC-015 Acceptance Patch — compact handoff (2026-07-03)

> **Documentation acceptance patch, not implementation.** Confirmed
> before editing: PR #74 head at commit
> `d7f7eca4bd5de36aca7d9a513cfbb4e0c1a676cf` (Sprint C proposal, Fable
> review fixes, and a consistency patch, all on the same branch/PR);
> DEC-015 confirmed `Proposed for ChatGPT review`; AR-012 confirmed
> `Proposed for ChatGPT review`; Master Blueprint Part C (Inventory and
> Fulfillment Domain Blueprint) confirmed present, revised twice on PR
> #74 (Fable-review fix, then a consistency patch); DEC-003 through
> DEC-014 confirmed still **Accepted by ChatGPT** and unedited;
> implementation confirmed still blocked; UI/UX Screen Design Blueprint
> (Part D) confirmed not started; Part E confirmed not started. Branch
> `claude/master-blueprint-sprint-c-inventory-fulfillment`.

- **Branch / PR:** `claude/master-blueprint-sprint-c-inventory-fulfillment`
  → draft PR #74 into `Shopify-connector`, **not merged**.
- **Files changed:**
  `docs/04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/04-decisions/README.md`,
  `docs/01-research/research-handoff.md` (this file). **No code files
  changed.**
- **What changed:** **DEC-015 accepted by ChatGPT**, acceptance date
  **2026-07-03**, after PR #74's Fable review (**REVISE**, no redesign —
  finding C1 corrected the earlier over-claim that
  `product.product.free_qty` and `stock.quant.available_quantity` are
  equivalent; finding C2 corrected the earlier silent treatment of
  "event-driven enqueue" as a Part A job-source value; seven minor
  findings fixed) and a same-PR consistency patch aligning the new-MBQ
  summary wording, both already applied to this branch before this
  acceptance patch. DEC-015 got a new *Accepted decision* section
  recording the accepted Master Blueprint Sprint C inventory and
  fulfillment domain blueprint package (items 1–5) and eleven explicit
  acceptance points **A–M**: **(A)** MBQ-32 partially resolved (quantity-
  source direction — the two candidate sources accepted as verified but
  **not equivalent**, per Fable finding C1); **(B)** MBQ-33 **still
  open** — first-push guard granularity recommendation noted, not
  decided; **(C)** MBQ-34 **still open** — ongoing apply-mode
  recommendation noted, not decided; **(D)** MBQ-36 partially resolved
  (mutation-choice-per-trigger direction); **(E)** MBQ-37 **resolved at
  fact-verification level** (inventory webhook topic); **(F)** MBQ-38
  partially resolved (first-push confirmation-record concept); **(G)**
  MBQ-39 **resolved at fact-verification level** (tracking-field source);
  **(H)** MBQ-40 partially resolved (backorder-to-picking linkage);
  **(I)** MBQ-41 **still open** — notification-UI granularity
  recommendation noted, not decided; **(J)** MBQ-42 partially resolved
  (fulfillment location-confirmation mechanism), **including an accepted
  widening of the `ambiguous match` class** (AR-006/DEC-009: multiple
  candidates) to also cover a deterministic fulfillment-location
  mismatch, per Fable minor finding 2, accepted at blueprint level only;
  **(K)** MBQ-43 partially resolved (Location reference cache policy);
  **(L)** MBQ-60/MBQ-61 confirmed new and open; **(M)** MBQ-62/MBQ-63
  (added in the Fable-review revision) confirmed new and open. **No
  implementation and Part D/E-not-started language preserved
  throughout.** `architecture-review-log.md`'s AR-012 table row moved
  from "Proposed for ChatGPT review" to "Accepted by ChatGPT," with a
  compact acceptance-patch note appended; AR-002 through AR-011 rows
  untouched. `docs/04-decisions/README.md` gained a new "Also accepted:
  DEC-015" entry; DEC-003 through DEC-014 entries untouched.
  `master-blueprint-open-questions.md` updated: its Sprint C note
  superseded by a DEC-015 acceptance note; MBQ-37/MBQ-39 rows marked
  **resolved by DEC-015 acceptance**; MBQ-32/MBQ-36/MBQ-38/MBQ-40/
  MBQ-42/MBQ-43 rows marked **partially resolved by DEC-015 acceptance**;
  MBQ-33/MBQ-34/MBQ-41 rows marked **carried forward, open — DEC-015
  acceptance does not itself decide this row**; MBQ-35 and MBQ-60
  through MBQ-63 left untouched (carried forward unchanged / new and
  open respectively); MBQ-04, MBQ-08, MBQ-24, MBQ-27, MBQ-28, MBQ-53
  through MBQ-58 untouched, no question deleted. `master-blueprint.md`'s
  status moved to accepted-through-DEC-015 wording (Part C table row now
  reads "Accepted by ChatGPT via DEC-015"); Part D/E preserved as "Not
  started."
- **Items deferred:** MBQ-33, MBQ-34, MBQ-41 (recommendations noted, not
  decided by this acceptance); MBQ-60 through MBQ-63 (new, open, not
  resolved by this acceptance); MBQ-04, MBQ-08, MBQ-53 through MBQ-58
  (untouched, open); the Part D UI/UX Screen Design Blueprint sprint
  (MBQ-53, still not started); Part E (implementation-planning bridge);
  all implementation.
- **Learning feedback loop:** **New issues discovered:** none — this
  patch mechanically applied ChatGPT's explicit, itemized acceptance
  scope; no ambiguity required a judgment call beyond what the task
  specified. **Repeated issue patterns:** none at threshold. **Rules/
  checklists updated:** none new. **New rejected approaches:** none —
  `rejected-approaches-log.md` checked, nothing reintroduced. **New
  technical debt:** none (no code). **New open questions:** none — this
  patch resolves/partially resolves existing rows and confirms MBQ-60
  through MBQ-63 remain new/open; it adds no new MBQ row. **Architecture
  concerns:** AR-012 is now **Accepted by ChatGPT** — Master Blueprint
  Part C is accepted at blueprint level, with MBQ-33/34/41 and MBQ-60
  through MBQ-63 explicitly still open; Part D (UI/UX Screen Design
  Blueprint) remains the next recommended sprint, alongside Part E
  (implementation-planning bridge), per ChatGPT's preference; neither is
  started.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (none new this patch) · rejected
  approaches checked, none added · technical debt logged (none
  applicable — no code) · repeated-issue escalation applied (none at
  threshold) — all **YES**.
- **Next recommended session:** 1) **Master Blueprint Part D — UI/UX
  Screen Design Blueprint** (resolving MBQ-53) or **Part E —
  implementation-planning bridge**, per ChatGPT's preference; 2) a
  future, separate ChatGPT decision on MBQ-33 (first-push granularity),
  MBQ-34 (apply-mode), and MBQ-41 (notification-UI granularity), each
  still open with a recommendation only; 3) **Implementation only after
  a separate ChatGPT gate**, and, for any operator-facing screen, only
  after the Part D UI/UX Screen Design Blueprint is also accepted.
- **Stop condition:** stopped after one commit on the existing **draft**
  PR #74 into `Shopify-connector` (not merged, not marked ready for
  review). DEC-003 through DEC-014 not edited; no code files changed;
  Part D (UI/UX Screen Design Blueprint) not started; Part E not
  started; implementation still not authorized; `main` and plain `dev`
  untouched. Awaiting further instruction.

---

### Master Blueprint Sprint C — compact handoff (2026-07-03)

> **Documentation-only proposal sprint, not implementation.** Confirmed
> before editing: PR #73 merged into `Shopify-connector` (merge commit
> `09829a804eef9c4099960f5604729f3a775793d1`); DEC-003 through DEC-014
> confirmed still **Accepted by ChatGPT** and unedited; Master Blueprint
> Part C confirmed **Not started** before this sprint; implementation
> confirmed still blocked; UI/UX Screen Design Blueprint (Part D)
> confirmed not started; `rejected-approaches-log.md` checked, no rejected
> approach reintroduced. Branch
> `claude/master-blueprint-sprint-c-inventory-fulfillment`.

- **Branch / PR:** `claude/master-blueprint-sprint-c-inventory-fulfillment`
  → draft PR into `Shopify-connector`, opened immediately after this
  handoff commit, **not merged**.
- **Files changed:**
  `docs/03-architecture/master-blueprint-inventory-fulfillment.md` (new),
  `docs/04-decisions/DEC-015-master-blueprint-inventory-fulfillment.md`
  (new), `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file). **No code files
  changed.**
- **What changed:** Proposed **Master Blueprint Part C — Inventory and
  Fulfillment Domain Blueprint** via new companion decision record
  **DEC-015** (Status: Proposed for ChatGPT review, not accepted) and
  review-log entry **AR-012** (Status: Proposed for ChatGPT review, not
  accepted). The new blueprint document converts the **accepted** DEC-010
  (inventory) and DEC-011 (fulfillment) architecture into domain-level
  blueprint detail, reusing the accepted Part A core substrate (DEC-013)
  and Part B product/order binding posture (DEC-014) without
  modification. Six small, targeted official-doc checks were performed
  (all accessed 2026-07-03): the Shopify `WebhookSubscriptionTopic` enum
  (confirming `INVENTORY_LEVELS_UPDATE` and the full
  `FULFILLMENT_ORDERS_*`/`FULFILLMENTS_*` topic family), and Odoo 19.0
  official source code (`github.com/odoo/odoo`, `19.0` branch) for
  `product.product.free_qty`, `stock.quant.available_quantity`,
  `stock.picking.backorder_id`/`backorder_ids`, and the `stock_delivery`
  module's `stock.picking.carrier_tracking_ref`/`carrier_tracking_url`/
  `carrier_id`. No fact was found inconclusive; no source was
  inaccessible. `master-blueprint.md` updated: Part C moved from "Not
  started" to "Proposed for ChatGPT review via DEC-015, not accepted";
  Part D (UI/UX Screen Design Blueprint) and Part E
  (implementation-planning bridge) explicitly preserved as "Not started."
  `master-blueprint-open-questions.md` updated: a new Sprint C note added
  (superseding nothing, additive to the existing DEC-014 acceptance
  note); MBQ-32/36/38/40/42/43 marked **proposed partially resolved**,
  pending DEC-015 acceptance; MBQ-37/39
  marked **proposed resolved**, pending DEC-015 acceptance; MBQ-33/34/41 kept **carried forward, open**, each
  with a named **recommendation** for ChatGPT's direct decision (not
  self-accepted); MBQ-35 kept **carried forward, open, unchanged**; four
  new rows added, **MBQ-60** (whether `shopify_connector_fulfillment`
  requires the Odoo `stock_delivery`/`delivery` module) and **MBQ-61**
  (whether/how the connector reacts to Shopify FulfillmentOrder
  hold/cancellation-request/merge/split/reschedule lifecycle events,
  newly confirmed as real webhook topics this sprint but not discussed by
  DEC-011), plus **MBQ-62** and **MBQ-63**, added in a later Fable-review
  revision on this same PR (see the follow-up checkpoint note below) —
  **MBQ-62** (exact Part A job-source classification for Odoo-event-
  triggered inventory push and fulfillment creation; "event-driven
  enqueue" is a sync-trigger-layer description, not a Part A §D.2 job-
  source value) and **MBQ-63** (the broader Shopify inventory-webhook
  payload-shape/subscription-mechanics/Phase-1-implementation-scope
  residual MBQ-37 did not cover). Every MBQ-32/36/37/38/39/40/42/43 row remains formally
  **open** in the register — the "proposed resolved"/"proposed partially
  resolved" labels describe this sprint's proposal only and become final
  only if/when ChatGPT accepts DEC-015. No existing MBQ ID or question
  text was deleted or altered beyond its proposed-resolution-status note.
  `architecture-review-log.md`:
  AR-012 added, Status **Proposed for ChatGPT review**, not accepted;
  AR-002 through AR-011 rows untouched.
- **Items deferred:** every MBQ row not explicitly proposed-resolved/proposed-
  partially-resolved above, all of which remain formally open pending
  DEC-015 acceptance (notably MBQ-04, MBQ-08, MBQ-33, MBQ-34, MBQ-41,
  MBQ-53–59 unchanged, MBQ-60 through MBQ-63); the Part D UI/UX Screen Design
  Blueprint sprint (MBQ-53, still not started); Part E
  (implementation-planning bridge); all implementation.
- **Learning feedback loop:** **New issues discovered:** ChatGPT review of
  PR #74 correctly flagged that this handoff (and the companion register/
  blueprint/DEC-015/AR-012 wording) used accepted-sounding labels
  ("Resolved by Sprint C," "Partially resolved by Sprint C") before
  DEC-015 acceptance — corrected in a follow-up commit on this same PR to
  "Proposed resolved"/"Proposed partially resolved" throughout, with every
  affected row/section stating explicitly that it remains open pending
  DEC-015's acceptance. This session's own pre-commit check confirmed no
  DEC-003–014 edits, no
  RA-row reintroduction, no code files touched, and no MBQ row marked
  fully "Resolved" where a genuine residual sub-question remained (MBQ-32
  corrected from an initial over-claim to "partially resolved," then
  further corrected to "proposed partially resolved" per the ChatGPT
  review above, once the compound nature of its question text
  was re-checked against Sprint B's own "partially resolved" precedent
  for similarly compound rows). **Repeated issue patterns:** none at
  threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none — this sprint checked `rejected-approaches-log.md`
  before drafting and reintroduces nothing from it; no new approach was
  evaluated to rejection. **New technical debt:** none (no code). **New
  open questions:** MBQ-60 through MBQ-63 — MBQ-60 and MBQ-61 surfaced by
  this sprint's original official-doc verification, not previously
  considered by DEC-008/DEC-010/DEC-011; MBQ-62 and MBQ-63 added in a
  later Fable-review revision on the same PR (job-source classification
  for Odoo-event-triggered jobs, and the inventory-webhook payload/
  subscription/Phase-1-scope residual, respectively). **Architecture concerns:** AR-012 is
  **Proposed for ChatGPT review** — Master Blueprint Part C is proposed
  at blueprint level; Part D (UI/UX Screen Design Blueprint) remains the
  next recommended sprint after ChatGPT review, alongside Part E
  (implementation-planning bridge), per ChatGPT's preference; neither is
  started.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (the status-language correction noted
  above, applied) · rejected approaches checked, none added
  · technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of this Part C
  proposal and DEC-015** — in particular the three ChatGPT-decision-owner
  recommendations (MBQ-33 first-push granularity, MBQ-34 apply-mode,
  MBQ-41 notification-UI granularity), the proposed location-confirmation
  mechanism (MBQ-42), and the four new open questions (MBQ-60 through
  MBQ-63); 2)
  if accepted, **Master Blueprint Part D — UI/UX Screen Design Blueprint**
  (resolving MBQ-53) or **Part E — implementation-planning bridge**, per
  ChatGPT's preference; 3) **Implementation only after a separate ChatGPT
  gate**, and, for any operator-facing screen, only after the Part D
  UI/UX Screen Design Blueprint is also accepted.
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #73 merge confirmed first.
  DEC-003 through DEC-014 not edited; no code files changed; Part D
  (UI/UX Screen Design Blueprint) not started; Part E not started;
  implementation still not authorized; `main` and plain `dev` untouched.
  Awaiting further instruction.

---

### DEC-014 Acceptance Patch — compact handoff (2026-07-03)

> **Documentation acceptance patch, not implementation.** Confirmed
> before editing: PR #72 merged into `Shopify-connector` (merge commit
> `e27c21f328436bc734539dd9169a95d79deaadd1`); DEC-014 confirmed
> `Proposed for ChatGPT review`; AR-011 confirmed `Proposed for ChatGPT
> review`; Master Blueprint Part B (Product, Customer, and Sale/Order
> Domain Blueprint) confirmed present, revised twice on PR #72; DEC-003
> through DEC-013 confirmed still **Accepted by ChatGPT** and unedited;
> implementation confirmed still blocked; Sprint C confirmed not
> started; UI/UX Screen Design Blueprint confirmed not started. Branch
> `claude/dec-014-acceptance-patch-5bml33` (harness-assigned; preferred
> branch name per the task prompt was `claude/dec-014-acceptance-patch`
> — discrepancy recorded here per the session rule; the harness-assigned
> branch was based exactly on the PR #72 merge commit, so it was used
> as-is, no re-basing needed).

- **Branch / PR:** `claude/dec-014-acceptance-patch-5bml33` → draft PR
  into `Shopify-connector`, opened immediately after this handoff
  commit, **not merged**.
- **Files changed:**
  `docs/04-decisions/DEC-014-master-blueprint-product-customer-sale.md`,
  `docs/05-qa/architecture-review-log.md`, `docs/04-decisions/README.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-product-customer-sale.md`,
  `docs/01-research/research-handoff.md` (this file).
- **What changed:** **DEC-014 accepted by ChatGPT**, acceptance date
  **2026-07-03**, after PR #72 merged into `Shopify-connector` (merge
  commit `e27c21f328436bc734539dd9169a95d79deaadd1`), carrying both the
  PR #72 ChatGPT-requested revision and the PR #72 Fable-requested B1/B2/
  B3 revision. DEC-014 got a new *Accepted decision* section recording
  the accepted Master Blueprint Sprint B product/customer/sale-order
  domain blueprint package (items 1–6) and eleven explicit acceptance
  points **A–K**: **(A)** MBQ-23 partially resolved (variant-mutation-
  strategy direction); **(B)** MBQ-25 partially resolved (draft/publish
  mechanism); **(C)** MBQ-26 **accepted at blueprint level** (existing
  error-center/sync-center surfaces sufficient for Phase 1 order-import
  operator touchpoints, conditioned on the inline financial-evidence
  breakdown and direct matching-flow links already specified in Part B
  §C.14); **(D)** MBQ-29 partially resolved (default-customer fallback
  direction); **(E)** MBQ-31 **accepted at blueprint level** (email is
  the sole automatic customer match key); **(F)** the total-check guard
  definition accepted (MBQ-56 stays open, tolerance TBD); **(G)** MBQ-30
  partially resolved (gateway → Odoo journal mapping concept accepted —
  classification/routing input only, no accounting automation/invoice/
  payment/payout write authorized; exact schema/fields remain open);
  **(H)** MBQ-59 **accepted at blueprint-policy level** (automated import
  create/bind policy — pre-create duplicate check + two-tier eligibility/
  match-quality gate, routed via accepted Part A per-class mechanisms;
  exact implementation detail remains open); **(I)** the **Fable B1
  route accepted** — accepted Part A per-class routing throughout, Part A
  §D.8's `blocked_manual_review` vocabulary **not widened**; **(J)** the
  **Fable B2 route accepted** — `ORDERS_UPDATED`/order-edit handling is
  **evidence-refresh only**, no silent Odoo sale-order line/price/tax/
  shipping/discount/payment/refund/fulfillment update under any trigger;
  **(K)** still-open confirmation — MBQ-04/08/24/27/28/53/54/55/56/57/58
  unaffected, remain open. No-implementation and Sprint-C/UI-UX-Blueprint-
  not-started language preserved throughout.
  `architecture-review-log.md`'s AR-011 table row moved from "Proposed
  for ChatGPT review" to "Accepted by ChatGPT," with a compact
  acceptance note appended; AR-002 through AR-010 rows untouched.
  `docs/04-decisions/README.md`'s DEC-014 entry moved from "Also present
  (not yet accepted)" to "Also accepted," citing the 2026-07-03
  acceptance date and PR #72 merge commit; DEC-003 through DEC-013
  entries untouched. `master-blueprint-open-questions.md` updated: its
  Sprint B note superseded by a DEC-014 acceptance note; MBQ-23/25/29/30
  rows marked **partially resolved by DEC-014**; MBQ-26/31/59 rows marked
  **accepted at blueprint(-policy) level by DEC-014**; MBQ-04/08/24/27/
  28/53/54/55/56/57/58 rows left untouched, no question deleted.
  `master-blueprint.md`'s status moved to accepted-through-DEC-014
  wording (Part B table row now reads "Accepted by ChatGPT via DEC-014");
  Parts C/D/E preserved as "Not started." `master-blueprint-product-
  customer-sale.md`'s status moved to accepted-via-DEC-014 wording, with
  the specific paragraphs corresponding to acceptance points A/B/C/D/E/G/
  H/I/J (§A.2, §A.5.2, §A.9, §A.10, §A.19, §B.2, §B.7, §B.9, §B.13, §C.6,
  §C.10, §C.12, §C.13, §C.14, §J) re-labelled `[Accepted — DEC-014]` —
  the rest of the ~1,400-line document was deliberately **not**
  mechanically rewritten, mirroring the DEC-013 acceptance-patch
  precedent for Part A.
- **Items deferred:** every MBQ row not explicitly resolved/partially
  resolved/accepted above (notably MBQ-04, MBQ-08, MBQ-24, MBQ-27,
  MBQ-28, MBQ-53, MBQ-54, MBQ-55, MBQ-56, MBQ-57, MBQ-58); Master
  Blueprint Sprint C — Inventory and Fulfillment Domain Blueprint; the
  Part D UI/UX Screen Design Blueprint sprint; Sprint E
  (implementation-planning bridge); all implementation.
- **Learning feedback loop:** **New issues discovered:** none — this
  session's own pre-commit check confirmed no DEC-003–013 edits, no
  RA-row reintroduction, no code files touched, and no MBQ row marked
  fully "Resolved" outside the explicitly authorized blueprint(-policy)-
  level acceptances (MBQ-26/31/59, all explicitly scoped as "accepted at
  blueprint(-policy) level," not "fully resolved," with any named
  residual detail left open). **Repeated issue patterns:** none at
  threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none — this patch finalizes no new RA row; DEC-014's
  acceptance reintroduces nothing from `rejected-approaches-log.md`
  (checked before editing). **New technical debt:** none (no code).
  **Architecture concerns:** AR-011 now **Accepted by ChatGPT** — Master
  Blueprint Part B is accepted at blueprint level; Sprint C is the next
  recommended step, still gated by a separate ChatGPT implementation-gate
  approval and, for operator-facing screens, the not-yet-started Part D
  UI/UX Screen Design Blueprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (no new issues) · rejected approaches
  checked, none added · technical debt logged (none applicable — no
  code) · repeated-issue escalation applied (none at threshold) — all
  **YES**.
- **Next recommended session:** 1) **Master Blueprint Sprint C —
  Inventory and Fulfillment Domain Blueprint** (convert DEC-010/DEC-011
  into the inventory and fulfillment domain blueprints); 2)
  **Implementation only after a separate ChatGPT gate**, and, for any
  operator-facing screen, only after the Part D UI/UX Screen Design
  Blueprint is also accepted.
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #72 merge confirmed first.
  DEC-003 through DEC-013 not edited; no code files changed; Master
  Blueprint Sprint C not started; UI/UX Screen Design Blueprint not
  started; implementation still not authorized; `main` and plain `dev`
  untouched. Awaiting further instruction.

---

### Master Blueprint Sprint B — compact handoff (2026-07-03)

> **Documentation-only proposal sprint, not implementation.** Confirmed
> before editing: PR #71 merged into `Shopify-connector` (merge commit
> `283a38f26ef90fca2a53c18ff6faf4775da4a2ee`); DEC-013/AR-010 confirmed
> **Accepted by ChatGPT**; DEC-003 through DEC-013 confirmed accepted and
> unedited; Master Blueprint Part A confirmed accepted; Master Blueprint
> Part B confirmed **not started**; MBQ-23 through MBQ-31 confirmed
> present and routed to Sprint B; MBQ-53 confirmed open; implementation
> confirmed still blocked. Branch
> `claude/master-blueprint-sprint-b-7zrvji` (harness-assigned; preferred
> name was `architecture/master-blueprint-product-customer-sale` —
> discrepancy recorded here per the session rule).

- **Branch / PR:** `claude/master-blueprint-sprint-b-7zrvji` → draft PR
  into `Shopify-connector`, opened immediately after this handoff commit,
  **not merged**.
- **Files changed:**
  `docs/03-architecture/master-blueprint-product-customer-sale.md` (new),
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/04-decisions/DEC-014-master-blueprint-product-customer-sale.md`
  (new), `docs/04-decisions/README.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/06-prompts/master-blueprint-product-customer-sale-prompt.md`
  (new, archive).
- **What changed:** Created the **product, customer, and sale/order
  domain blueprint**
  (`master-blueprint-product-customer-sale.md`) converting the accepted
  DEC-003/006/007/012 (and the accepted DEC-013 core substrate) into
  domain-level flows: product import/export/update (variant/option
  handling, SKU/barcode matching, template-vs-variant identity, binding
  responsibility, duplicate-prevention preview, draft-first export,
  destructive-write guard, source-of-truth choices, media/price handling,
  publish/draft safety, preview/review states, job types, error/retry
  touchpoints); customer import/matching (matching priority, no export,
  no name-only matching, no-PII handling, default-customer-fallback
  direction, binding responsibility under `shopify_connector_sale`,
  duplicate-prevention preview, privacy minimization, job types); order
  import (binding responsibility, identity/duplicate prevention, line
  mapping, product/customer binding prerequisites with proposed
  fallback rules, financial-evidence capture, the total-check guard
  definition, tax/shipping/discount/payment evidence handling, gateway→
  journal mapping concept, no invoice/payment automation, deferred
  edits/cancellations/refunds, manual-review triggers, proposed
  order-import operator-touchpoint recommendation, job types); and
  cross-domain sequencing (product/customer binding before order line/
  assignment, preview before create, manual review routing, reconciliation
  backstop, core-substrate job/log/error/binding usage, trigger-type
  table). Performed **two small, targeted official-doc checks** (per the
  sprint's "no broad research" instruction): Shopify `productSet`/
  `productVariantsBulkCreate`/`Product` (`status` enum)/`publishablePublish`
  reference pages (accessed 2026-07-03) — informing the proposed
  variant-mutation-strategy direction (MBQ-23, partially resolved) and the
  proposed draft/publish mechanism (MBQ-25, partially resolved); and Odoo
  19 accounting/taxes documentation (accessed 2026-07-03) — inconclusive,
  MBQ-27 stays open. Updated `master-blueprint.md`'s status/Part-B-table/
  "Domain blueprints still pending" section to reflect Part B **Proposed
  for ChatGPT review**; Parts C/D/E remain **Not started**; Part A
  acceptance wording unchanged. Updated
  `master-blueprint-open-questions.md`: MBQ-23/25/29/30 marked **proposed
  partially resolved**; MBQ-26/31 marked **proposed resolution
  (recommendation to ChatGPT)**; MBQ-24/27/28 marked **carried forward,
  open** (checked, not resolved); added **MBQ-55 through MBQ-58** (new);
  MBQ-04/08/53/54 left untouched. Created proposed
  [`DEC-014`](../04-decisions/DEC-014-master-blueprint-product-customer-sale.md)
  (`Status: Proposed for ChatGPT review`) and proposed **AR-011** in
  `architecture-review-log.md` (`Status: Proposed for ChatGPT review`).
  Added DEC-014 to `04-decisions/README.md` as "Also present (not yet
  accepted)" — DEC-003 through DEC-013 entries untouched.
- **Items deferred:** MBQ-04, MBQ-08, MBQ-53, MBQ-54 (untouched, still
  open); MBQ-24, MBQ-27, MBQ-28 (checked this sprint, still open);
  MBQ-55–58 (new, all open); Master Blueprint Sprint C (inventory/
  fulfillment domain blueprint, not started); the Part D UI/UX Screen
  Design Blueprint (not started); Sprint E (implementation-planning
  bridge); all implementation.
- **Learning feedback loop:** **New issues discovered:** none — this
  session's own pre-commit check confirmed no DEC-003–013 edits, no
  RA-row reintroduction, no code files touched, and no MBQ row marked
  fully "Resolved" outside the two ChatGPT-decision-owner rows (MBQ-26/31,
  both explicitly labelled recommendations, not self-decided). **Repeated
  issue patterns:** none at threshold. **Rules/checklists updated:** none
  new. **New rejected approaches:** none — no approach was evaluated to
  rejection this sprint; the whole-order-hold rule for unmatched products
  (§C.5) and the automated-vs-interactive duplicate-prevention-preview
  clarification (§A.2/§B.2) are **blueprint proposals**, not rejections,
  and neither reintroduces a binding RA row (checked against RA-001
  through RA-023 before drafting). **New technical debt:** none (no
  code). **Architecture concerns:** AR-011 now **Proposed for ChatGPT
  review** — Master Blueprint Part B awaits ChatGPT/Fable review before
  any acceptance; Sprint C remains the next recommended step after that
  review, still gated by a separate ChatGPT implementation-gate approval
  and, for operator-facing screens, the not-yet-started Part D UI/UX
  Screen Design Blueprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback
  loop checked · learning captured (no new issues) · rejected approaches
  checked, none added · technical debt logged (none applicable — no
  code) · repeated-issue escalation applied (none at threshold) — all
  **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of DEC-014 /
  AR-011** (this sprint's proposal); 2) if accepted, **Master Blueprint
  Sprint C — Inventory and Fulfillment Domain Blueprint**; 3)
  **Implementation only after a separate ChatGPT gate**, and, for any
  operator-facing screen, only after the Part D UI/UX Screen Design
  Blueprint is also accepted.
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #71 merge confirmed first.
  DEC-003 through DEC-013 not edited; no code files changed; Master
  Blueprint Sprint C not started; UI/UX Screen Design Blueprint not
  started; implementation still not authorized; `main` and plain `dev`
  untouched. Awaiting further instruction.

**PR #72 revision (2026-07-03) — REVISE before Fable review.** ChatGPT
reviewed PR #72 and requested revision before Fable review. Fixed on the
same branch/PR (no new PR opened): (1) automated create/preview semantics
— withdrew the reading that retrospective sync-center/dashboard
visibility satisfies the "no blind create"/preview requirement for
confident automated product/customer imports; replaced with an explicit,
proposed pre-create duplicate check + six-condition auto-create gate
policy (Part B §A.2/§A.9/§B.2/§B.9), tracked as new open question
**MBQ-59**; interactive/batch create-bind/write is unaffected and still
requires a blocking preview. (2) Product export/update trigger wording
corrected (§A.4) so it no longer implies ordinary Odoo record writes
autonomously queue Shopify update jobs — an update job now requires an
explicit operator action (or a later accepted controlled trigger,
still open). (3) Order-scope wording in the §I error-class table
generalized — replaced the specific `read_all_orders` claim with
"missing required order read scope / protected-customer-data approval"
since exact scope requirements were not verified this sprint; already
covered by MBQ-06/MBQ-09, no new row added for this item. (4)
`productVariantsBulkUpdate` claim verified against its official reference
page (accessed 2026-07-03) and cited directly (§A.5.2), replacing the
earlier under-cited claim. MBQ-59 added to the register (§4); DEC-014 and
AR-011 updated to reference MBQ-55 through MBQ-59 and to call out the
automated import create/bind policy as a proposed, open decision, not an
already-accepted interpretation. **DEC-014 remains Proposed for ChatGPT
review — not accepted. AR-011 remains Proposed for ChatGPT review — not
accepted.** DEC-003 through DEC-013 untouched; no code files changed;
implementation remains blocked; Sprint C not started; UI/UX Screen Design
Blueprint not started; MBQ-04/08/53/54 remain open, untouched. Same
branch (`claude/master-blueprint-sprint-b-7zrvji`), same PR (#72) —
pushed as a new commit, no new PR opened, no merge. Next: stop for
Fable review.

**PR #72 Fable review — REVISE (2026-07-03):** Fable reviewed PR #72 at
head `e4146b948e3177878cb86b554e8a354c2edada0a` and returned **REVISE**.
Governance was clean and Sprint B's substance did not require redesign.
Revision applied B1/B2/B3 per ChatGPT's routing decisions: **B1** —
corrected Part A/Part B routing semantics so `mapping missing`,
`financial total mismatch`, `data shape/schema mismatch`, and MBQ-59 gate
failures use **accepted Part A per-class routing** instead of collapsing
into `blocked_manual_review` (§A.2/§B.2/§C.5/§C.8/§C.13/§G/§I) — Part A
§D.8's confirmation-required sub-reason vocabulary was **not widened**.
**B2** — narrowed §C.12: `ORDERS_UPDATED`/order-edit handling now only
refreshes Shopify-side evidence, never silently applies to Odoo sale
order line quantities/prices/taxes/shipping/discounts/invoices/payments/
refunds/fulfillment state; any divergence routes through the total-check
guard; webhook and reconciliation paths behave identically. **B3** —
fixed MBQ-59 acceptance-status labels (§A.2 Flow bullet/heading, §C.6.2)
so the accepted import capability is separated from the proposed,
pending-DEC-014 automated create/bind mechanism; MBQ-59 remains fully
open, never resolved or partially resolved. Also applied Fable's twelve
minor issues (README MBQ-55–59 range; DEC-014 acceptance-point lettering
A–H, no more gap; §B.10 MBQ-02/55 typo; §A.13 MBQ-24 "carried forward,
open" wording; §B.6 attribution + §B.7 fallback "proposed, not accepted"
wording; product-webhook-topic citation softened; customer-import webhook
wording no longer implies an unverified standalone topic; §C.6 "three
distinct paths" + ambiguous-customer reconciled with the domain-brief
"one bad customer record does not block order import" posture;
MBQ-59 gate condition 4 restated to cover confident-match and
confident-no-match-creation; gate condition 6 citation split between Part
A §D.10 and §C.4; `productVariantsBulkUpdate` citation consistency in
DEC-014/register; original MBQ question text restored for
MBQ-23–27/29–31/59; DEC-014's MBQ-59 point now names the DEC-003/006 vs.
DEC-005 vs. Part A/DEC-013 tension and the Part A §I.5 no-bypass rule).
**DEC-014 remains Proposed for ChatGPT review — not accepted. AR-011
remains Proposed for ChatGPT review — not accepted. MBQ-59 remains
proposed/open pending DEC-014.** DEC-003 through DEC-013 untouched; no
code files changed; implementation remains blocked; Sprint C not started;
UI/UX Screen Design Blueprint not started. Same branch
(`claude/master-blueprint-sprint-b-7zrvji`), same PR (#72) — pushed as a
new commit, no new PR opened, no merge. Next: stop for Fable re-review.

---

### DEC-013 Acceptance Patch — compact handoff (2026-07-03)

> **Documentation acceptance patch, not implementation.** Confirmed before
> editing: PR #70 merged into `Shopify-connector` (merge commit
> `5c44971d1df84d5657da0164bf874b1125aee64f`); DEC-013 confirmed `Proposed for
> ChatGPT review`; AR-010 confirmed `Proposed for ChatGPT review`; Master
> Blueprint Part A confirmed present; MBQ-53/MBQ-54 confirmed present;
> DEC-003 through DEC-012 confirmed still **Accepted by ChatGPT** and
> unedited; implementation confirmed still blocked; Sprint B confirmed not
> started. Preferred branch name was
> `product/accept-dec013-master-blueprint-core`; the harness had already
> checked out `claude/accept-dec013-master-blueprint-nh6ouq` based exactly on
> the PR #70 merge commit — this branch-name discrepancy is recorded here per
> the session rule; the existing branch was used as-is, no re-basing needed.

- **Branch / PR:** `claude/accept-dec013-master-blueprint-nh6ouq` → draft PR
  into `Shopify-connector`, opened immediately after this handoff commit,
  **not merged**.
- **Files changed:**
  `docs/04-decisions/DEC-013-master-blueprint-core-substrate.md`,
  `docs/03-architecture/master-blueprint.md`,
  `docs/03-architecture/master-blueprint-core-substrate.md`,
  `docs/03-architecture/master-blueprint-open-questions.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/06-prompts/accept-dec013-master-blueprint-core-prompt.md` (new,
  archive).
- **What changed:** **DEC-013 accepted by ChatGPT**, acceptance date
  **2026-07-03**, after PR #70 merged into `Shopify-connector` (merge commit
  `5c44971d1df84d5657da0164bf874b1125aee64f`), following Fable's **ACCEPT
  WITH MINOR CHANGES** review and the Fable revision + tiny consistency fix
  applied before merge. DEC-013 got a new *Accepted decision* section
  recording the accepted Master Blueprint Sprint A core/common substrate
  package (index/structure; Part A blueprint; `shopify_connector_core`
  boundary/seams; core configuration-object concepts; binding abstraction;
  job/log/error/retry abstraction; setup-wizard/dashboard/sync-center/
  error-center blueprints; feature-flag mechanism direction; blueprint-level
  permissions/access design; cross-module extension rules; open-questions
  register MBQ-01–MBQ-54; the Part D UI/UX Screen Design Blueprint
  requirement) and the five explicit acceptance points: **(A)** binding
  schema shape — per-domain concrete binding models on a core abstract
  contract, with a cross-domain enumeration/registration seam and a
  binding-granularity bound (resolves MBQ-11; does not reintroduce RA-005 or
  RA-013); **(B)** feature-flag mechanism — store-scoped core settings
  record, domain-extended, not `ir.config_parameter`/`res.config.settings`
  storage/per-domain ad hoc models; execution-time re-check scoped to
  fail-safe enablement gating only; no flag bypasses a safety guard
  (resolves MBQ-07 at blueprint-direction level); **(C)** roles/access —
  the proposed hierarchy accepted (Administrator ⊃ Operator/Reviewer ⊃
  Auditor; Operator and Reviewer siblings); no access CSVs/XML IDs decided;
  no connector UI/API surface exposes the stored credential secret after
  entry (resolves MBQ-47; partially resolves MBQ-45); **(D)** UI/UX — Part D
  — UI/UX Screen Design Blueprint — required before operator-facing
  implementation, MBQ-53 remains open until that sprint is accepted;
  **(E)** still open — MBQ-04, MBQ-08, MBQ-53, MBQ-54, exact
  model/field/view/security identifiers, implementation-planning detail,
  and Sprint B/C domain questions all remain open. No-implementation and
  Sprint-B-not-started language preserved throughout. `master-blueprint.md`'s
  status moved to accepted-through-DEC-013 wording (Index/Part A/
  open-questions-register rows in the part table now read "Accepted by
  ChatGPT via DEC-013"); Parts B/C/D/E preserved as "Not started."
  `master-blueprint-core-substrate.md`'s status moved to accepted-through-
  DEC-013 wording, with only the specific proposals DEC-013 explicitly
  accepted (§C.8 binding shape, §I.3 feature-flag direction, §J.1 role
  hierarchy) re-labelled `[Accepted — DEC-013]` — the rest of the document
  was deliberately **not** mechanically rewritten. `master-blueprint-open-
  questions.md` rows updated only where DEC-013 resolves or partially
  resolves them: **MBQ-07** (resolved at blueprint-direction level),
  **MBQ-11** (resolved), **MBQ-45** (partially resolved), **MBQ-47**
  (resolved); MBQ-04/MBQ-08/MBQ-53/MBQ-54 and all other rows left untouched,
  no question deleted. `docs/04-decisions/README.md`'s DEC-013 entry moved
  from "Also present (not yet accepted)" to "Also accepted," citing the
  2026-07-03 acceptance date and PR #70 merge commit; DEC-003 through
  DEC-012 entries untouched. `architecture-review-log.md`'s AR-010 table row
  moved from "Proposed for ChatGPT review" to "Accepted by ChatGPT," with a
  compact acceptance note appended; AR-002 through AR-009 rows untouched.
- **Items deferred:** every MBQ row not explicitly resolved/partially
  resolved above (notably MBQ-04, MBQ-08, MBQ-53, MBQ-54, and every
  Sprint-B/C-routed row); Master Blueprint Sprint B — Product, Customer, and
  Sale/Order Domain Blueprint; Master Blueprint Sprint C (inventory/
  fulfillment); the Part D UI/UX Screen Design Blueprint sprint; Sprint E
  (implementation-planning bridge); all implementation.
- **Learning feedback loop:** **New issues discovered:** none — this
  session's own pre-commit check confirmed no DEC-003–012 edits, no RA-row
  reintroduction, no code files touched, and no MBQ row silently resolved
  outside the five explicitly authorized (MBQ-07/11/45/47, plus the
  MBQ-04/08/53/54 stay-open confirmation). **Repeated issue patterns:** none
  at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none (this patch finalizes no new RA row; the single
  polymorphic binding table remains not-chosen-but-not-rejected, unchanged
  by this acceptance). **New technical debt:** none (no code). **Architecture
  concerns:** AR-010 now **Accepted** (via DEC-013) — Master Blueprint Part A
  is accepted; Sprint B is the next recommended step, still gated by a
  separate ChatGPT implementation-gate approval and, for operator-facing
  screens, the not-yet-started Part D UI/UX Screen Design Blueprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (no new issues) · rejected approaches checked,
  none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** 1) **Master Blueprint Sprint B — Product,
  Customer, and Sale/Order Domain Blueprint**, now that DEC-013 is accepted;
  2) **Implementation only after a separate ChatGPT gate**, and, for any
  operator-facing screen, only after the Part D UI/UX Screen Design
  Blueprint is also accepted.
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #70 merge confirmed first.
  DEC-003/004/005/006/007/008/009/010/011/012 not edited; no code files
  changed; Master Blueprint Sprint B not started; implementation still not
  authorized; `main` and plain `dev` untouched. Awaiting further
  instruction.

**PR #71 tiny acceptance-label cleanup (2026-07-03):**
- ChatGPT reviewed PR #71 and requested one tiny acceptance-state cleanup
  before merge.
- Open Questions Register status updated to accepted-through-DEC-013 while
  preserving every unresolved MBQ row.
- Claim-label definition (`[Blueprint proposal]`) updated to reflect that
  design details remain proposed unless explicitly accepted by DEC-013 or
  a later accepted decision.
- Accepted DEC-013 items relabeled `[Accepted — DEC-013]` where needed in
  the core-substrate blueprint (§C.8 cross-domain enumeration seam and
  binding-granularity bound; §I.3 feature-flag execution-time re-check
  scoping; §J.2 no-read-back credential connector-surface guarantee).
- MBQ-04, MBQ-08, MBQ-53, and MBQ-54 remain open.
- DEC-013 remains accepted.
- AR-010 remains accepted.
- DEC-003 through DEC-012 untouched.
- No code files changed.
- Implementation remains blocked.
- Sprint B not started.
- Same branch/PR — no new PR opened, no merge.

---

### Master Blueprint Sprint A — Core/Common Substrate — compact handoff (2026-07-03)

> **Documentation / blueprint sprint, not implementation.** Confirmed before
> editing: PR #69 merged into `Shopify-connector` (merge commit
> `305f396bcbd2656a4282ed18c5983540503b5502`); DEC-003 through DEC-012 all
> **Accepted by ChatGPT** (DEC-012 accepted 2026-07-03; AR-009 accepted);
> AR-002 through AR-009 all **Accepted**; RA-001 through RA-023 binding;
> implementation still blocked; Master Blueprint not previously started.
> Branch `claude/master-blueprint-core-substrate-azhp4s` (harness-assigned;
> the sprint's preferred name was
> `architecture/master-blueprint-core-substrate`, so this branch-name
> discrepancy is recorded here per the session rule) was already checked out
> based exactly on that merge commit — no re-basing needed.

- **Branch / PR:** `claude/master-blueprint-core-substrate-azhp4s` → draft PR
  into `Shopify-connector`, opened immediately after this handoff commit,
  **not merged**.
- **Files changed:** `docs/03-architecture/master-blueprint.md` (new),
  `docs/03-architecture/master-blueprint-core-substrate.md` (new),
  `docs/03-architecture/master-blueprint-open-questions.md` (new),
  `docs/04-decisions/DEC-013-master-blueprint-core-substrate.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/06-prompts/master-blueprint-core-substrate-prompt.md` (new, archive).
- **What changed:** **Master Blueprint Sprint A started** — created the first
  Master Blueprint package for the connector's **core/common substrate**:
  the top-level index (blueprint scope, part/sprint structure A–D, module
  family overview, implementation-gate criteria); the Part A core-substrate
  blueprint (`shopify_connector_core` boundary + six extension seams; seven
  core configuration-object concepts incl. credential no-read-back posture
  and the DEC-010/011 core Shopify Location reference invariants; the
  binding abstraction with a **proposed** per-domain-concrete-on-core-
  contract schema-shape direction (MBQ-11, the fork DEC-006/DEC-008 routed
  here); the job/log/error/retry abstraction (6 sources / 10 states /
  16-class core-owned registry, generalized operation-level idempotency key
  + serialization guard); setup-wizard/dashboard/sync-center/error-center
  blueprints applying DEC-012; the DEC-008-routed feature-flag mechanism
  with a **proposed** store-scoped, domain-extended direction (MBQ-07) and
  the structural "no flag bypasses a safety guard" rule; a blueprint-level
  four-role access matrix (no CSVs, proposed names only); ten cross-module
  extension rules); and the central open-questions register (**MBQ-01
  through MBQ-52**, grouped, each with source/owner/blocking status).
  Proposed **DEC-013** (`Status: Proposed for ChatGPT review`) and added
  **AR-010** (Proposed for ChatGPT review) to the architecture review log.
  `docs/04-decisions/README.md` got an "Also present (not yet accepted)"
  entry indexing DEC-013 as Proposed.
- **Items deferred:** product/customer/sale-order domain blueprints (Sprint
  B); inventory/fulfillment domain blueprints (Sprint C); the
  implementation-planning bridge (Sprint D); every MBQ row (notably
  MBQ-04 credential storage, MBQ-07 feature-flag confirmation, MBQ-08
  disconnect retention, MBQ-11 binding-shape confirmation, MBQ-26
  order-import touchpoints, MBQ-45/47 roles mapping); all implementation.
- **Learning feedback loop:** **New issues discovered:** three minor
  claim-label precision issues, caught by this session's own pre-commit
  adversarial verification pass and **fixed before commit** (two
  [Accepted]-over-labels in Part A — an illustrative health-state
  vocabulary and an Inference-sourced setup rule — and one open-question
  owner/summary drift in §L vs MBQ-17); no reviewer-found defect, so no
  `defect-pattern-log.md` row was added (that file is also outside this
  sprint's allowed files). The verification pass otherwise confirmed: no
  status errors, no DEC-003–012 contradictions, no RA-001–023
  reintroduction, exact DEC-009/008/006 taxonomy fidelity, no broken
  links. **Repeated issue patterns:** none at threshold.
  **Rules/checklists updated:** none
  new. **New rejected approaches:** none (checked RA-001–RA-023 before
  drafting; the polymorphic-binding-table option is *not chosen* at
  blueprint level but deliberately **not** entered as a rejected approach —
  DEC-006 kept it viable and ChatGPT may still select it at DEC-013
  review). **New technical debt:** none (no code). **Architecture
  concerns:** AR-010 added (Proposed); one residue observation — the
  `docs/03-architecture/README.md` status paragraph still describes the
  pre-DEC-004/005/006 state ("AR-002/003/005 … still Not decided") and
  predates the AR/DEC/blueprint files added since; it was **not** edited
  because it is outside this sprint's allowed-files list — flagged for a
  future residue sweep.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (no new issues) · rejected approaches checked,
  none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of
  DEC-013/AR-010** (headline items MBQ-04/07/08/11/45/47); 2) if accepted,
  **Master Blueprint Sprint B — Product, Customer, and Sale/Order Domain
  Blueprint**; 3) **implementation only after a separate ChatGPT gate**.
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #69 merge confirmed first. DEC-003
  through DEC-012 not edited; no code files changed; no domain blueprint
  started; DEC-013 and AR-010 proposed only, not accepted; implementation
  still not authorized; `main` and plain `dev` untouched. Awaiting ChatGPT
  review.

**PR #70 Fable revision (2026-07-03):**
- Fable reviewed PR #70 and returned **ACCEPT WITH MINOR CHANGES**.
- Required revisions applied:
  - UI/UX Screen Design Blueprint added to Master Blueprint sequence and
    gate criteria (new Part D, `master-blueprint.md`).
  - MBQ-53 added for screen-level UI/UX design.
  - MBQ-54 added for module-uninstall / disable data lifecycle.
  - Feature-flag execution-time re-check scoped to enablement gating only
    (never alters enqueue-time notification/source-of-truth decisions).
  - Binding enumeration seam and binding granularity bound added (§C.8).
  - Claim labels corrected (§C.4, §D.13; also added §D.5's `skipped`/
    `failed_final` any-class-outcome rule).
  - `ir.cron` wording clarified (§D.1).
  - Credential no-read-back wording clarified as a connector-surface
    guarantee, not a database-level claim (§J.2).
  - Webhook-topic registration seam added (§A.5).
- DEC-013 remains **Proposed for ChatGPT review**, not accepted.
- AR-010 remains proposed only, not accepted.
- DEC-003 through DEC-012 untouched.
- No code files changed.
- Implementation remains blocked.
- Sprint B not started.
- Same branch/PR — no new PR opened, no merge.

**PR #70 tiny consistency fix (2026-07-03):**
- ChatGPT reviewed the Fable revision and requested one tiny consistency
  cleanup.
- Updated AR-010 to reference MBQ-01–MBQ-54 after MBQ-53 and MBQ-54 were
  added.
- AR-010 remains Proposed for ChatGPT review.
- DEC-013 remains Proposed for ChatGPT review.
- DEC-003 through DEC-012 untouched.
- No code files changed.
- Implementation remains blocked.
- Sprint B not started.
- Same branch/PR — no new PR opened, no merge.

---

### DEC-012 Acceptance Patch — compact handoff (2026-07-03)

> **Documentation acceptance patch, not implementation.** Confirmed PR #68 merged
> into `Shopify-connector` (merge commit
> `7d01617fdd0fd70d6a1d83d57918b045296550ac`) before editing; DEC-003 through
> DEC-011 confirmed **Accepted by ChatGPT**; DEC-012 confirmed `Proposed for
> ChatGPT review`; AR-009 confirmed proposed only, not accepted; implementation
> confirmed still blocked. Branch `product/accept-dec012-ux-operator-flow` was
> already checked out based exactly on that merge commit — no re-basing needed.

- **Branch / PR:** `product/accept-dec012-ux-operator-flow` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-012-ux-operator-flow-strategy.md`,
  `docs/02-product/ux-operator-flow.md`,
  `docs/03-architecture/ux-operator-flow-architecture-bridge.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/quality-feedback-loop.md`, `docs/01-research/research-handoff.md`
  (this file).
- **What changed:** DEC-012 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-03**; the record got an
  acceptance note recording the PR #68 merge (merge commit
  `7d01617fdd0fd70d6a1d83d57918b045296550ac`) and Fable's **ACCEPT WITH MINOR
  CHANGES** review, while preserving every documented open question unchanged
  (exact Odoo views/menus/wizards/widgets/field names; exact security
  groups/access CSVs; exact copy/wording; the feature-flag/per-store capability
  mechanism; readiness-check details; first-push guard granularity;
  notification-UI granularity; whether `on_hand` is ever exposed as a Phase 1 UI
  choice; the draft/publish mechanism; order-import operator touchpoints; and the
  store-disconnect data-retention posture). `ux-operator-flow.md` and the
  architecture bridge had their "DEC-012 is Proposed, not accepted" wording
  updated to reflect the accepted status, without rewriting any of the ten
  operator flows. `docs/04-decisions/README.md`'s DEC-012 entry moved from "Also
  present (not yet accepted)" to "Also accepted," citing the 2026-07-03
  acceptance date. `architecture-review-log.md`'s AR-009 table row moved from
  "Proposed for ChatGPT review" to "Accepted by ChatGPT," with a compact
  acceptance note appended; AR-002 through AR-008 rows were not touched.
  `quality-feedback-loop.md` §10 criterion 5 ("A UX/operator-flow sprint
  accepted...") was marked `(Done — 2026-07-03, via DEC-012...)`, consistent with
  criterion 1's existing pattern; no other QA content was rewritten.
- **Items deferred:** every open question preserved in DEC-012's *Acceptance
  note* above; the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New
  rejected approaches:** none (DEC-012 finalizes no new RA row). **New technical
  debt:** none (no code). **Architecture concerns:** AR-009 now **Accepted** (via
  DEC-012) — all Phase 1 research-phase-exit criteria in
  `quality-feedback-loop.md` §10 are now satisfied; the Master Blueprint is the
  next step, still gated by a separate ChatGPT implementation-gate approval.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (no new issues) · rejected approaches checked,
  none added · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** 1) **Master Blueprint**, now that all Phase 1
  research-phase-exit criteria are satisfied; 2) **Implementation only after a
  separate ChatGPT gate.**
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #68 merge confirmed first.
  DEC-003/004/005/006/007/008/009/010/011 not edited; no code files changed;
  implementation still not authorized; Master Blueprint not started; `main` and
  plain `dev` untouched. Awaiting further instruction.

**PR #69 tiny fix (2026-07-03):**
- ChatGPT reviewed PR #69 and requested tiny accepted-status wording cleanup
  before merge.
- Updated `ux-operator-flow.md` so `[Proposed UX decision]` is no longer
  described as "not yet binding" after DEC-012 acceptance.
- Renamed DEC-012 "Decision proposed" section to "Accepted decision."
- DEC-012 remains accepted.
- AR-009 remains accepted.
- DEC-003 through DEC-011 untouched.
- No code files changed.
- Implementation remains blocked.
- Master Blueprint not started.

---

### UX / Operator-Flow Decision Preparation — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR
> #67 merged into `Shopify-connector` (merge commit
> `8798a2454924fd241c8052e2556ea8bca21a7c20`) before editing; DEC-003 through
> DEC-011 confirmed **Accepted by ChatGPT**; AR-002 through AR-008 confirmed
> **Accepted**; RA-001 through RA-023 confirmed **binding**; implementation
> confirmed still blocked. Branch `claude/ux-operator-flow-prep-d12g04`
> (harness-assigned; the sprint's preferred name was
> `product/ux-operator-flow-decision-prep`, so this branch-name discrepancy is
> recorded here per the session rule) was already checked out based exactly on
> that merge commit — no re-basing needed.

- **Branch / PR:** `claude/ux-operator-flow-prep-d12g04` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/02-product/ux-operator-flow.md` (new),
  `docs/03-architecture/ux-operator-flow-architecture-bridge.md` (new),
  `docs/04-decisions/DEC-012-ux-operator-flow-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md`
  (this file), `docs/06-prompts/ux-operator-flow-decision-prep-prompt.md` (new,
  archive).
- **What changed:** authored
  [`ux-operator-flow.md`](../02-product/ux-operator-flow.md) — the Phase 1
  UX/operator-flow proposal covering ten operator flows (initial setup wizard,
  store settings, dashboard/command center, sync center/job monitor, error
  center/recovery, matching/duplicate-prevention, product import/export/update,
  inventory, fulfillment, and a conceptual permissions/roles model), each labelled
  **[Accepted]**/**[Proposed UX decision]**/**[Inference]**/**[Open question]** and
  cited directly to the DEC-003 through DEC-011 "UX implications" sections and the
  accepted `setup-ux-principles.md`/`product-vision.md` product inputs it builds
  on. Authored
  [`DEC-012-ux-operator-flow-strategy.md`](../04-decisions/DEC-012-ux-operator-flow-strategy.md)
  (Status: **Proposed for ChatGPT review**) as the proposed decision record for
  that strategy. Authored
  [`ux-operator-flow-architecture-bridge.md`](../03-architecture/ux-operator-flow-architecture-bridge.md)
  mapping each of the ten flows to its source DEC-003 through DEC-011 sections,
  naming what routes to the Master Blueprint per flow, and naming what must not be
  implemented yet. `docs/04-decisions/README.md` got a new "Also present (not yet
  accepted)" entry indexing DEC-012 as Proposed. `architecture-review-log.md` got a
  new **AR-009** row ("UX/operator-flow strategy," Status: Proposed for ChatGPT
  review) plus a compact note. `rejected-approaches-log.md` got a note recording
  that **no new RA rows were added** — every UX-facing anti-pattern the ten flows
  guard against was checked against the existing log and is already covered by a
  binding RA row (RA-006, RA-008, RA-009, RA-014 through RA-023) or an already-
  accepted DEC guardrail; no near-duplicate was introduced.
- **Items deferred:** exact Odoo views/menus/widgets/field names; exact security
  groups/access CSVs; exact copy/wording; the feature-flag/per-store
  capability-configuration mechanism (DEC-008, routed to Master Blueprint); all
  other "What remains open" items listed in DEC-012 and the architecture bridge;
  the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New
  rejected approaches:** none (checked against the existing log; all UX-facing
  anti-patterns already covered). **New technical debt:** none (no code).
  **Architecture concerns:** none new — DEC-012/AR-009 synthesize already-accepted
  DEC-003 through DEC-011 architecture into operator-facing UX; no new Tier-1
  platform-fact claim was introduced.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (no new issues) · rejected approaches checked, none
  added · technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT review of DEC-012/AR-009**; 2) the
  **Master Blueprint**, after that review; 3) **Implementation only after a
  separate ChatGPT gate.**
- **Stop condition:** stopped after two commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #67 merge confirmed first.
  DEC-003/004/005/006/007/008/009/010/011 not edited; no code files changed;
  implementation still not authorized; `main` and plain `dev` untouched. Awaiting
  further instruction.

**PR #68 Fable revision (2026-07-02):**
- Fable reviewed PR #68 and returned **ACCEPT WITH MINOR CHANGES**.
- Clarified that readiness/test-connection/preview jobs
  (`setup_readiness_check`, `export_preview_dry_run`) may run during setup
  and are not business sync runs.
- Reworded scope-list UX to avoid implying the wizard grants Shopify scopes.
- Added a customer email/customer-key matching step (binding → email/
  customer keys → manual, name advisory only), distinct from product/variant
  matching (binding → SKU/internal reference → barcode → manual).
- Added two Master Blueprint open questions: order-import operator
  touchpoints, and store-disconnect data-retention posture.
- DEC-012 remains **Proposed for ChatGPT review**.
- AR-009 remains proposed only, not accepted.
- DEC-003 through DEC-011 untouched.
- No code files changed.
- Implementation remains blocked.

---

### DEC-010/DEC-011 Acceptance Patch — compact handoff (2026-07-02)

> **Documentation acceptance patch, not implementation.** Confirmed PR #66 merged into
> `Shopify-connector` (merge commit `14af2fb3becb47ba7c32a50715d85f6eaab0d855`) before
> editing; DEC-010 and DEC-011 confirmed `Proposed for ChatGPT review`; AR-007 and AR-008
> confirmed proposed only, not accepted; RA-018 through RA-023 confirmed `PROPOSED`;
> DEC-003 through DEC-009 confirmed accepted/unchanged; implementation confirmed still
> blocked. Branch `claude/accept-dec010-dec011-dxkuzi` (harness-assigned; the sprint's
> preferred name was `architecture/accept-dec010-dec011`, so this branch-name discrepancy
> is recorded here per the session rule) was already checked out based exactly on that
> merge commit — no re-basing needed.

- **Branch / PR:** `claude/accept-dec010-dec011-dxkuzi` → draft PR into `Shopify-connector`,
  opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-010-inventory-architecture-strategy.md`,
  `docs/04-decisions/DEC-011-fulfillment-architecture-strategy.md`,
  `docs/03-architecture/ar007-inventory-architecture-decision-brief.md`,
  `docs/03-architecture/ar008-fulfillment-architecture-decision-brief.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file).
- **What changed:** DEC-010 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; DEC-011 Status changed the
  same way, same acceptance date. Both records got an acceptance note recording the PR #66
  merge and the Fable **ACCEPT WITH MINOR CHANGES** review, while preserving every
  documented caveat unchanged (exact Odoo ORM source for "Free to Use," exact first-push
  guard granularity, exact mutation choice per trigger, exact cron cadence, unverified
  webhook topic strings, feature-flag/config UI routing, `available` as the Phase 1
  default target with `on_hand` requiring Master Blueprint justification, `committed`
  never written; exact tracking field source, exact backorder linkage, exact notification
  UI granularity, exact retry constants, exact fulfillment location-confirmation
  mechanism, exact operation-level idempotency key schema, and the multi-package/
  multi-location deferral). Both records also got a compact **shared Shopify Location
  reference clarification** note recording that ChatGPT's acceptance ratifies the
  clarification against DEC-008: `shopify_connector_core` may hold a minimal Shopify-side
  Location reference/cache/list (never Odoo-location IDs or mapping decisions);
  `shopify_connector_inventory` keeps owning the Odoo↔Shopify mapping;
  `shopify_connector_fulfillment` never depends on inventory; DEC-008's dependency
  direction is unchanged and no new module is created. The AR-007 and AR-008 decision
  briefs were updated to state that AR-007/AR-008 are now accepted through DEC-010/DEC-011,
  while remaining evidence-backed briefs that authorize no implementation.
  `docs/04-decisions/README.md`'s DEC-010/DEC-011 entry moved from "Also present (not yet
  accepted)" to "Also accepted," citing the 2026-07-02 acceptance date and noting RA-018
  through RA-023 are now binding, and recording that all architecture decisions AR-002
  through AR-008 are now accepted. `architecture-review-log.md`'s AR-007 and AR-008 table
  rows moved from "Proposed for ChatGPT review" to "Accepted by ChatGPT," and a compact
  acceptance note was appended confirming the shared Location reference clarification is
  ratified against DEC-008, DEC-003/004/005/006/007/008/009 are unchanged, and
  implementation remains blocked. RA-018 through RA-023 in `rejected-approaches-log.md`
  had the `PROPOSED:` prefix removed and their "Related decision record" cells updated to
  cite DEC-010/DEC-011's `Accepted by ChatGPT, 2026-07-02` status — **these six rows are
  now binding final rejected approaches** (`CLAUDE.md` §10 applies in full).
- **Items deferred:** exact Odoo ORM sources, exact schemas, exact operation-key schema,
  exact fulfillment location-confirmation mechanism, exact feature-flag/config UI, exact
  notification UI, exact retry constants, and all Master Blueprint items; UX/operator-flow
  sprint; the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none new (RA-018–023 finalized, not created). **New technical debt:** none
  (no code). **Architecture concerns:** AR-007/AR-008 now **Accepted** (via DEC-010/
  DEC-011) — all of AR-002 through AR-008 are now accepted; the shared Shopify Location
  reference clarification is ratified against DEC-008.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches finalized (RA-018–023) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **UX/operator-flow sprint**; 2) **Master Blueprint**,
  after that gate; 3) **Implementation only after a separate ChatGPT gate.**
- **Stop condition:** stopped after one commit + one **draft** PR into `Shopify-connector`
  (not merged). PR #66 merge confirmed first. DEC-003/DEC-004/DEC-005/DEC-006/DEC-007/
  DEC-008/DEC-009 not edited; no code files changed; implementation still not authorized;
  `main` and plain `dev` untouched. Awaiting further instruction.

**PR #67 tiny fix (2026-07-02):**
- ChatGPT reviewed PR #67 and requested tiny README cleanup before merge.
- Fixed stale DEC-008/DEC-009 README wording that still described AR-007/AR-008 as
  proposed/not accepted.
- DEC-010/DEC-011 remain accepted.
- AR-007/AR-008 remain accepted.
- RA-018 through RA-023 remain finalized.
- DEC-003/004/005/006/007/008/009 untouched.
- No code files changed.
- Implementation remains blocked.

---

### AR-007 + AR-008 Decision Preparation — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR #65
> merged into `Shopify-connector` (merge commit
> `dfb0199c9588ae600216ef549d160d0ced15034f`) before editing; DEC-003/004/005/006/007/008/009
> confirmed **Accepted by ChatGPT**; RA-001 through RA-017 confirmed **binding**;
> AR-002/AR-003/AR-004/AR-005/AR-006 confirmed **Accepted**; AR-007/AR-008 confirmed **Not
> decided**; implementation confirmed still blocked. Branch
> `claude/ar007-ar008-decision-prep-5tdwfv` (harness-assigned; the sprint's preferred name
> was `architecture/ar007-ar008-decision-prep`, so this branch-name discrepancy is recorded
> here per the session rule) was already checked out based exactly on that merge commit — no
> re-basing needed.

- **Branch / PR:** `claude/ar007-ar008-decision-prep-5tdwfv` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/ar007-inventory-architecture-decision-brief.md`
  (new), `docs/03-architecture/ar008-fulfillment-architecture-decision-brief.md` (new),
  `docs/03-architecture/ar007-ar008-evidence-refresh.md` (new),
  `docs/04-decisions/DEC-010-inventory-architecture-strategy.md` (new),
  `docs/04-decisions/DEC-011-fulfillment-architecture-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file), `docs/06-prompts/ar007-ar008-decision-prep-prompt.md` (new, archive).
- **What changed:** authored
  [`ar007-inventory-architecture-decision-brief.md`](../03-architecture/ar007-inventory-architecture-decision-brief.md)
  — Phase 1 inventory source-of-truth posture (Odoo as ongoing source, controlled
  first-sync import from Shopify, no autonomous bidirectional conflict resolution),
  Shopify inventory-object mapping (`(store, inventory_item_id, location_id)` binding
  identity), the Odoo quantity concept (Odoo's "Free to Use" as the directional Phase 1
  candidate, exact field open), location architecture (explicit non-inferred mapping;
  block on missing/ambiguous mapping; a clarified ownership principle — `core` may hold
  a minimal Shopify Location reference, `inventory` keeps owning the Odoo↔Shopify
  location mapping, `fulfillment` never depends on `inventory` — not a DEC-008
  amendment), sync trigger (layered:
  scheduled + manual + event-driven enqueue; webhook import flagged unverified), inventory
  operation style (`inventorySetQuantities` compare-and-set preferred, DEC-009 idempotency/
  ambiguous-outcome rules applied), conflict handling, user-facing log requirements, and
  module boundaries — and
  [`ar008-fulfillment-architecture-decision-brief.md`](../03-architecture/ar008-fulfillment-architecture-decision-brief.md)
  — validated `stock.picking` as the fulfillment trigger, FulfillmentOrder-based mutations
  only (`fulfillmentCreate`/`fulfillmentTrackingInfoUpdate`), matching via
  `lineItemsByFulfillmentOrder`, the DEC-007 no-notification-by-default guard applied with
  the setting persisted per job at enqueue time, single-fulfillment-location Phase 1
  posture with multi-package/multi-location deferred (existing C-FUL-02 boundary, not a new
  rejection), the DEC-009 ambiguous-outcome rule applied to both fulfillment mutations
  (neither is on Shopify's 17-mutation `@idempotent` list), and the same clarified
  shared-Shopify-Location-reference ownership principle mirrored from the AR-007 brief
  (not a DEC-008 amendment). Ran a **small,
  targeted official-source check** (`ar007-ar008-evidence-refresh.md`, access date
  2026-07-02) against official Odoo 19.0 documentation for inventory-quantity report
  concepts (On Hand / Free to Use / Forecasted), warehouse/location types, and third-party
  carrier tracking — needed because a repo-local extraction pass found
  `../01-research/odoo-official-architecture-notes.md` had **zero coverage** of
  `stock.quant`/`stock.picking`/delivery-carrier models; several gaps (exact `stock.quant`
  field names, exact tracking-reference field name, exact delivery-order backorder-wizard
  text, Shopify inventory/fulfillment webhook topic strings, the literal 17-mutation
  `@idempotent` list) remain **explicitly marked "Open question / must be verified before
  implementation"** rather than asserted. Proposed
  [`DEC-010`](../04-decisions/DEC-010-inventory-architecture-strategy.md) (AR-007) and
  [`DEC-011`](../04-decisions/DEC-011-fulfillment-architecture-strategy.md) (AR-008), both
  `Status: Proposed for ChatGPT review`. Updated `architecture-review-log.md`: AR-007 and
  AR-008 rows move from "Not decided / Evidence pending" to "Proposed for ChatGPT review,"
  with a compact note confirming AR-002–AR-006 are unchanged and implementation remains
  blocked. Updated `rejected-approaches-log.md`: added **RA-018** (writing Shopify's
  read-only `committed` quantity), **RA-019** (single-location-only/SKU-only inventory
  writes without per-location binding identity), **RA-020** (autonomous bidirectional
  inventory conflict resolution in Phase 1), **RA-021** (treating Shopify/Odoo inventory
  quantities as equivalent without an explicit source-of-truth) tied to DEC-010, and
  **RA-022** (legacy fulfillment API flow), **RA-023** (fulfillment creation without
  FulfillmentOrder/line/quantity/location matching) tied to DEC-011 — all six tagged
  **PROPOSED**, non-binding until DEC-010/DEC-011 are accepted (checked against RA-001–017
  first; blind first inventory push, hidden/default-on notification, blind-retry-everything,
  and binding-alone idempotency were **not** re-logged — already RA-008/RA-009/RA-014/
  RA-017 respectively; multi-package/multi-location fulfillment automation was **not**
  logged — it is an existing deferral, not a rejection, under DEC-003/C-FUL-02).
  Updated `../04-decisions/README.md` to index DEC-010/DEC-011 as "Also present (not yet
  accepted)" and corrected the stale "AR-007 and AR-008 remain not decided" current-status
  line. Archived this sprint's prompt to `../06-prompts/ar007-ar008-decision-prep-prompt.md`.
- **Items deferred:** exact Odoo model/field/constraint design for inventory and
  fulfillment bindings/mappings/logs; exact computed quantity field/formula; exact
  `inventorySetQuantities`-vs-`inventoryAdjustQuantities` choice per trigger; exact cron
  cadence; exact feature-flag/config-model mechanism (already routed to UX/operator-flow
  and Master Blueprint per DEC-008); exact fulfillment mutation parameters; exact tracking
  field source; exact notification-UI granularity (DEC-007's own open fork); exact retry
  constants; the exact fulfillment location-confirmation mechanism (the ownership
  principle — `core` may hold a minimal Shopify Location reference, `inventory` keeps
  the mapping, `fulfillment` never depends on `inventory` — is clarified in DEC-010/
  DEC-011 as an interpretation consistent with DEC-008, not a DEC-008 amendment; only
  the exact mechanism/fields/models remain open); the Master Blueprint; all
  implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** RA-018 through RA-023 added (PROPOSED, non-binding). **New technical
  debt:** none (no code). **Architecture concerns:** AR-007 and AR-008 move to "Proposed
  for ChatGPT review" (not yet accepted); AR-002/AR-003/AR-004/AR-005/AR-006 unchanged
  ("Accepted"). A module-boundary ownership question was clarified (a minimal shared
  Shopify-Location reference may live in `core`; `inventory` keeps owning the Odoo↔
  Shopify location mapping; `fulfillment` never depends on `inventory`) as an
  **interpretation consistent with DEC-008**, not a DEC-008 amendment and not a
  contradiction — only the exact fulfillment location-confirmation mechanism remains
  open for the Master Blueprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches logged (RA-018–023, PROPOSED) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of DEC-010/DEC-011** (including
  verifying the clarified shared-Shopify-Location-reference ownership interpretation);
  2) **UX/operator-flow sprint**; 3) **Master Blueprint**, after those gates;
  4) **Implementation only after a separate ChatGPT gate.**
- **Stop condition:** stopped after three focused commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #65 merge confirmed first. DEC-003/DEC-004/
  DEC-005/DEC-006/DEC-007/DEC-008/DEC-009 not edited; no code files changed; AR-007 and
  AR-008 are **proposed only, not accepted**; implementation still not authorized; `main`
  and plain `dev` untouched. Awaiting further instruction.

**PR #66 minor revision (2026-07-02):**
- ChatGPT reviewed PR #66 and requested minor cleanup before Fable review.
- Clarified shared Shopify Location reference ownership: `core` may own a
  minimal Shopify Location reference/cache; `inventory` keeps owning the
  Odoo↔Shopify inventory mapping; `fulfillment` must not depend on
  `inventory`; the exact fulfillment location-confirmation mechanism remains
  a Master Blueprint item.
- Strengthened the fulfillment operation-level idempotency key (conceptually)
  to include operation type, Shopify target ID, and a payload/version hash —
  not just the picking ID.
- De-overstated Odoo `stock.quant` wording — AR-007 chooses the semantic
  quantity concept ("Free to Use"), not a verified Odoo ORM source; the exact
  implementation source remains open.
- Clarified Shopify `available` as the Phase 1 default inventory write target;
  `on_hand` requires explicit Master Blueprint justification before use;
  `committed` is never written.
- Fixed the architecture-review-log wording ("Proposed for ChatGPT review").
- DEC-010/DEC-011 remain `Proposed for ChatGPT review`, not accepted.
- AR-007/AR-008 remain proposed only, not accepted.
- RA-018 through RA-023 remain PROPOSED, not finalized.
- DEC-003/004/005/006/007/008/009 untouched.
- No code files changed.
- Implementation remains blocked.

**PR #66 Fable revision (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES):**
- Fable reviewed PR #66 and returned ACCEPT WITH MINOR CHANGES.
- Corrected DEC-008 attribution for the core Shopify Location reference: now
  framed as a proposed clarification/extension of DEC-008's `core`-owns list,
  ratified only if ChatGPT accepts DEC-010/DEC-011 — not something DEC-008
  already explicitly decided.
- Added dated official Shopify verification (access date 2026-07-02) for
  `FulfillmentInput.lineItemsByFulfillmentOrder` and FulfillmentOrder
  `assignedLocation`, recorded in `ar007-ar008-evidence-refresh.md`.
- Corrected the false "17-mutation list not itemized in repo docs" claim —
  the list is already itemized in `rb14-part2-open-question-resolution.md`
  (RQ-005-2); narrowed the remaining open item to `@idempotent`
  key-uniqueness scope and API-version-specific detail.
- Aligned DEC-010's first-push guard granularity wording so it no longer
  reads as deciding "per binding" — granularity remains open (per-store /
  per-binding / per-variant-location binding), no coarser than per-store.
- Added a fulfillment operation-serialization guard: a new/corrected
  operation must not dispatch while a prior ambiguous operation against the
  same `(store, picking, Shopify target)` is unresolved.
- Added core Location-reference invariants: no Odoo-location IDs or mapping
  decisions in the core reference; staleness/precedence vs. live
  `assignedLocation` left to the Master Blueprint.
- Cleaned small `04-decisions/README.md` residue, an RA-018 avoid-list
  citation, and RA-021/RA-023 revisit-condition wording.
- DEC-010/DEC-011 remain `Proposed for ChatGPT review`, not accepted.
- AR-007/AR-008 remain proposed only, not accepted.
- RA-018 through RA-023 remain PROPOSED, not finalized.
- DEC-003/004/005/006/007/008/009 untouched.
- No code files changed.
- Implementation remains blocked.

---

### DEC-008/DEC-009 Acceptance Patch — compact handoff (2026-07-02)

> **Documentation acceptance patch, not implementation.** Confirmed PR #64 merged into
> `Shopify-connector` (merge commit `e4c74abf0e3b4ad32e66413d27b40287ed4c5822`) before
> editing; DEC-008 and DEC-009 confirmed `Proposed for ChatGPT review`; RA-011 through
> RA-017 confirmed `PROPOSED`; AR-004 and AR-006 confirmed proposed only, not accepted;
> AR-007 and AR-008 confirmed not decided; DEC-003/004/005/006/007 confirmed
> accepted/unchanged; implementation confirmed still blocked. Branch
> `claude/accept-dec008-dec009-4aca6v` (harness-assigned; the sprint's preferred name was
> `architecture/accept-dec008-dec009`, so this branch-name discrepancy is recorded here per
> the session rule) was already checked out based exactly on that merge commit — no
> re-basing needed.

- **Branch / PR:** `claude/accept-dec008-dec009-4aca6v` → draft PR into `Shopify-connector`,
  opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-008-module-boundary-strategy.md`,
  `docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md`,
  `docs/03-architecture/ar004-module-boundary-decision-brief.md`,
  `docs/03-architecture/ar006-error-retry-idempotency-decision-brief.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file).
- **What changed:** DEC-008 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; DEC-009 Status changed the
  same way, same acceptance date. Both records got an acceptance note recording the PR #64
  merge and the Fable **ACCEPT WITH MINOR CHANGES** review, while preserving every
  documented caveat unchanged (DEC-008 does not decide AR-007/AR-008, concrete Odoo schema,
  or the DEC-006 polymorphic-vs-per-domain binding-schema fork, and does not decide the
  feature-flag/per-store capability-configuration mechanism; DEC-009 does not decide
  AR-007/AR-008, exact retry/backoff constants, exact reconciliation cadence/scope, or
  exact schema, and keeps the ambiguous-outcome non-`@idempotent` write rule as part of the
  accepted decision). The AR-004 and AR-006 decision briefs were updated to state that
  AR-004/AR-006 are now accepted through DEC-008/DEC-009, while remaining evidence-backed
  briefs that authorize no implementation and leave AR-007/AR-008 not decided.
  `docs/04-decisions/README.md`'s DEC-008/DEC-009 entry moved from "Also present (not yet
  accepted)" to "Also accepted," citing the 2026-07-02 acceptance date and noting RA-011
  through RA-017 are now binding. `architecture-review-log.md`'s AR-004 and AR-006 table
  rows moved from "Proposed for ChatGPT review" to "Accepted by ChatGPT," and a compact
  acceptance note was appended confirming AR-007/AR-008 remain not decided, DEC-003/004/
  005/006/007 are unchanged, and implementation remains blocked. RA-011 through RA-017 in
  `rejected-approaches-log.md` had the `PROPOSED:` prefix removed and their "Related
  decision record" cells updated to cite DEC-008/DEC-009's `Accepted by ChatGPT,
  2026-07-02` status — **these seven rows are now binding final rejected approaches**
  (`CLAUDE.md` §10 applies in full).
- **Items deferred:** AR-007 full inventory architecture; AR-008 full fulfilment
  architecture; the feature-flag / per-store capability-configuration mechanism (routed to
  UX/operator-flow and Master Blueprint / implementation planning); exact retry/backoff
  constants and reconciliation cadence/scope (implementation-planning defaults); exact Odoo
  model/field/constraint schema; the DEC-006 polymorphic-vs-per-domain binding-schema fork;
  the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none new (RA-011–017 finalized, not created). **New technical debt:** none
  (no code). **Architecture concerns:** AR-007/AR-008 remain **Not decided / Evidence
  pending** — DEC-008/DEC-009 accept the module-boundary and error/retry/idempotency
  strategies but decide neither AR-007 nor AR-008 internal design; AR-002/AR-003/AR-005
  unchanged (**Accepted**); AR-004/AR-006 now **Accepted**.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches finalized (RA-011–017) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **AR-007 + AR-008 decision sprint**; 2) **UX/operator-
  flow sprint**; 3) **Master Blueprint**, after those gates; 4) **Implementation only after
  a separate ChatGPT gate.**
- **Stop condition:** stopped after one commit + one **draft** PR into `Shopify-connector`
  (not merged). PR #64 merge confirmed first. DEC-003/DEC-004/DEC-005/DEC-006/DEC-007 not
  edited; no code files changed; AR-007/AR-008 remain **not decided**; implementation still
  not authorized; `main` and plain `dev` untouched. Awaiting further instruction.

**PR #65 tiny revision (2026-07-02):**
- ChatGPT reviewed PR #65 and requested tiny cleanup before merge.
- Fixed decisions README current-status residue so AR-004/AR-006 are no longer described as
  not decided.
- Fixed AR-004/AR-006 brief classification wording so recommendation labels no longer imply
  DEC-008/DEC-009 are still not decisions.
- DEC-008/DEC-009 remain accepted.
- AR-004/AR-006 remain accepted.
- AR-007/AR-008 remain not decided.
- DEC-003/004/005/006/007 untouched.
- No code files changed.
- Implementation remains blocked.

---

### AR-004 + AR-006 Decision Preparation — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR #63
> merged into `Shopify-connector` (merge commit `3ca0cdec168b60cae6c4b1004fa6f7532333a0f9`
> per the session prompt; verified as commit `3ca0cde` present in `origin/Shopify-connector`
> history) before editing; DEC-003/DEC-004/DEC-005/DEC-006/DEC-007 confirmed **Accepted by
> ChatGPT**; RA-001 through RA-010 confirmed **binding**; AR-002/AR-003/AR-005 confirmed
> **Accepted**; AR-004/AR-006/AR-007/AR-008 confirmed **Not decided**; implementation
> confirmed still blocked. Branch `claude/ar004-ar006-decision-prep-y9t8j2`
> (harness-assigned; the sprint's preferred name was
> `architecture/ar004-ar006-decision-prep`, so this branch-name discrepancy is recorded here
> per the session rule) was already checked out based exactly on that merge commit — no
> re-basing needed.

- **Branch / PR:** `claude/ar004-ar006-decision-prep-y9t8j2` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/ar004-module-boundary-decision-brief.md` (new),
  `docs/03-architecture/ar006-error-retry-idempotency-decision-brief.md` (new),
  `docs/04-decisions/DEC-008-module-boundary-strategy.md` (new),
  `docs/04-decisions/DEC-009-error-retry-idempotency-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file), `docs/06-prompts/ar004-ar006-decision-prep-prompt.md` (new, archive). No
  `docs/03-architecture/ar004-ar006-evidence-refresh.md` was created — repo-local evidence
  (already-cited Tier-1 Shopify/Odoo facts) was sufficient for every AR-004/AR-006 claim;
  no fresh external fetch was performed.
- **What changed:** authored
  [`ar004-module-boundary-decision-brief.md`](../03-architecture/ar004-module-boundary-decision-brief.md)
  — options considered (one giant module, per-feature micro-module explosion,
  domain-per-Odoo-app mirroring, layered domain family with link modules), a recommended
  Phase 1 addon family (`shopify_connector_core`/`product`/`sale`/`inventory`/
  `fulfillment`), a strict dependency DAG (`core` → `product`; `sale` and `inventory` are
  siblings depending on `core` + `product`; `fulfillment` depends on `core` + `sale`, not
  on `inventory`), a link-module strategy (none needed yet for Phase 1), and an evaluated
  answer on customer/dashboard/payment-evidence placement (folded into `sale`/`core`/`sale`
  respectively for Phase 1, each with a revisit condition) — and
  [`ar006-error-retry-idempotency-decision-brief.md`](../03-architecture/ar006-error-retry-idempotency-decision-brief.md)
  — a classified retry policy (Option C: auto-retry only safe/transient error classes),
  a 6-job-source taxonomy, a 10-job-state machine, a 16-error-class table with default
  retry behaviour, an 11-layer idempotency mapping (platform `@idempotent` surface +
  connector-designed keys), and user-facing log/audit requirements. Proposed
  [`DEC-008`](../04-decisions/DEC-008-module-boundary-strategy.md) (AR-004) and
  [`DEC-009`](../04-decisions/DEC-009-error-retry-idempotency-strategy.md) (AR-006), both
  `Status: Proposed for ChatGPT review`. Updated `architecture-review-log.md`: AR-004 and
  AR-006 rows move from "Not decided / Evidence pending" to "Proposed for ChatGPT review,"
  with a compact note confirming AR-007/AR-008 are untouched and implementation remains
  blocked. Updated `rejected-approaches-log.md`: added **RA-011** (one giant module),
  **RA-012** (per-feature micro-module explosion), **RA-013** (duplicated queue/job/log/
  binding abstractions per domain) tied to DEC-008, and **RA-014** (retry-everything
  automatically), **RA-015** (never-retry-automatically/manual-only recovery), **RA-016**
  (user-facing stack traces as primary error UX), **RA-017** (no connector-designed
  idempotency key / binding-alone retry strategy) tied to DEC-009 — all seven tagged
  **PROPOSED**, non-binding until DEC-008/DEC-009 are accepted (checked against RA-001–010
  first; no duplicates). Updated `../04-decisions/README.md` to index DEC-008/DEC-009 as
  "Also present (not yet accepted)." Archived this sprint's prompt to
  `../06-prompts/ar004-ar006-decision-prep-prompt.md`.
- **Items deferred:** AR-007 full inventory architecture; AR-008 full fulfilment
  architecture; exact Odoo model/field/constraint design for jobs/bindings/mappings; exact
  later-module names/boundaries (accounting/refund/payout/multi-store/markets/metafield/
  POS/B2B/app-store); exact retry-count/backoff constants (flagged
  `[Implementation-planning default]`); the Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** RA-011 through RA-017 added (PROPOSED, non-binding). **New technical
  debt:** none (no code). **Architecture concerns:** AR-004 and AR-006 move to "Proposed
  for ChatGPT review" (not yet accepted); AR-007/AR-008 unchanged ("Not decided"); AR-002/
  AR-003/AR-005 unchanged ("Accepted").
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches logged (RA-011–017, PROPOSED) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **ChatGPT/Fable review of DEC-008/DEC-009**; 2) **AR-007
  + AR-008 decision sprint**, once AR-004/AR-006 are reviewed; 3) **UX/operator-flow
  sprint**; 4) **Master Blueprint**, after those gates.
- **Stop condition:** stopped after three focused commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #63 merge confirmed first. DEC-003/DEC-004/
  DEC-005/DEC-006/DEC-007 not edited; no code files changed; AR-004 and AR-006 are
  **proposed only, not accepted**; AR-007/AR-008 remain **not decided**; implementation
  still not authorized; `main` and plain `dev` untouched. Awaiting further instruction.

**PR #64 minor revision (2026-07-02):**
- ChatGPT reviewed PR #64 and requested minor cleanup before Fable review.
- Corrected AR-006 taxonomy count from 15 to 16 error classes.
- Clarified AR-004 dependency notation so fulfillment depends on core + sale, not inventory.
- Normalized RA-011–RA-017 proposed formatting to keep stable RA IDs.
- DEC-008/DEC-009 remain Proposed for ChatGPT review.
- AR-004/AR-006 remain proposed only, not accepted.
- AR-007/AR-008 remain not decided.
- DEC-003/004/005/006/007 untouched.
- No code files changed.
- Implementation remains blocked.

**PR #64 Fable revision (2026-07-02):**
- Fable reviewed PR #64 and returned ACCEPT WITH MINOR CHANGES.
- Added DEC-006 binding-shape reconciliation so DEC-008 does not foreclose polymorphic vs per-domain binding schema.
- Added ambiguous-outcome non-idempotent-write retry rule to DEC-009 / AR-006.
- Corrected evidence/citation attributions: enable/disable attribution; customer fold-in quote/source; `committed` attribution; temporary/server/network evidence wording.
- Routed residual feature-flag/config-model scope to UX/operator-flow and Master Blueprint / implementation planning.
- Acknowledged reconciliation cadence handoff from DEC-005 and routed exact cadence to implementation planning.
- Cleaned small state-machine wording.
- Tightened RA-014 revisit condition.
- Added missing sprint checkpoint log line.
- DEC-008/DEC-009 remain Proposed for ChatGPT review.
- AR-004/AR-006 remain proposed only, not accepted.
- AR-007/AR-008 remain not decided.
- DEC-003/004/005/006/007 untouched.
- No code files changed.
- Implementation remains blocked.

---

### DEC-007 Acceptance Patch — compact handoff (2026-07-02)

> **Documentation acceptance patch, not implementation.** Confirmed PR #62 merged into
> `Shopify-connector` (merge commit `0d45d38bfe25d45a9d98bceb677fed2eab3c1e96`) before
> editing; DEC-007 confirmed `Proposed for ChatGPT review`; RA-008/RA-009/RA-010 confirmed
> `PROPOSED`; DEC-003/004/005/006 confirmed accepted/unchanged. Branch
> `claude/accept-dec007-2pjo9b` (harness-assigned; preferred branch name was
> `product/accept-dec007`, so this branch-name discrepancy is recorded here per the session
> rule) was already based exactly on that merge commit. Recorded ChatGPT's formal
> acceptance of DEC-007.

- **Branch / PR:** `claude/accept-dec007-2pjo9b` → draft PR into `Shopify-connector`,
  opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-007-phase1-scope-clarifications.md`,
  `docs/04-decisions/README.md`, `docs/03-architecture/phase1-domain-model-brief.md`,
  `docs/02-product/mvp-scope.md`, `docs/02-product/non-mvp-and-later-phases.md`,
  `docs/02-product/user-stories.md`, `docs/05-qa/rejected-approaches-log.md`,
  `docs/05-qa/architecture-review-log.md`, `docs/01-research/shopify-official-api-notes.md`,
  `docs/01-research/research-handoff.md` (this file).
- **What changed:** DEC-007 Status changed from `Proposed for ChatGPT review` to
  **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; added an acceptance note
  recording the PR #62 merge, the Fable **ACCEPT WITH MINOR CHANGES** review, and the
  explicit caveat that DEC-007 also accepts three **Phase 1 safety guardrails** (price
  source-of-truth before export/update; first Odoo→Shopify inventory push guard;
  fulfilment customer-notification visibility/control) — not hidden as pure wording
  cleanup. "Proposed"/"if accepted"/"if not accepted"/"candidate"/"proposed for review"
  wording updated to reflect the accepted status throughout DEC-007, while historical
  proposal notes are preserved as history. Domain-model brief labels changed from
  `[Proposed clarification — DEC-007]` to `[Accepted clarification — DEC-007]`
  throughout; its status section now records the DEC-007 acceptance. Product docs
  (`mvp-scope.md`, `non-mvp-and-later-phases.md`, `user-stories.md`) DEC-007 notes updated
  from proposed to accepted, without rewriting DEC-003 or the surrounding product text.
  `docs/04-decisions/README.md` DEC-007 entry updated from "Also present (not yet
  accepted)" to "Also accepted," citing the 2026-07-02 acceptance date and noting
  RA-008/009/010 are now binding. RA-008/RA-009/RA-010 in `rejected-approaches-log.md`
  had the `PROPOSED:` prefix removed and their "Related decision record" cells updated to
  cite DEC-007's `Accepted by ChatGPT, 2026-07-02` status — **these three rows are now
  binding final rejected approaches** (`CLAUDE.md` §10 applies in full). Added a compact
  acceptance note to `architecture-review-log.md` confirming DEC-007 feeds AR-006/AR-007/
  AR-008 without deciding them, AR-004 is untouched, and AR-004/006/007/008 remain "Not
  decided / Evidence pending." Propagated the two newly verified Shopify fact groups from
  DEC-007 (Order tax/shipping/discount fields; `FulfillmentInput.notifyCustomer` /
  `fulfillmentTrackingInfoUpdate.notifyCustomer` defaults) into a new dated section of
  `shopify-official-api-notes.md`, citing the same URLs and access date (2026-07-02)
  already used in DEC-007 — no new external research performed.
- **Items deferred:** AR-004/AR-006/AR-007/AR-008 full architecture decisions; exact Odoo
  model/field/constraint design; exact GraphQL mutation strategy for variant writes; the
  Master Blueprint; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** none new (RA-008–RA-010 finalized, not created). **New technical debt:**
  none (no code). **Architecture concerns:** AR-006/AR-007/AR-008 remain **Not decided /
  Evidence pending** — DEC-007's guardrails remain scope-level statements, not
  AR-007/AR-008 mechanism decisions; AR-002/AR-003/AR-005 unchanged (**Accepted**);
  AR-004 unchanged (**Not decided**).
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches finalized (RA-008–RA-010) ·
  technical debt logged (none applicable — no code) · repeated-issue escalation applied
  (none at threshold) — all **YES**.
- **Next recommended session:** 1) **AR-004 + AR-006 decision sprint**; 2) **AR-007 +
  AR-008 decision sprint**; 3) **UX/operator-flow sprint**; 4) **Master Blueprint** after
  those gates.
- **Stop condition:** stopped after one commit + one **draft** PR into `Shopify-connector`
  (not merged). PR #62 merge confirmed first. DEC-003/DEC-004/DEC-005/DEC-006 not edited;
  no code files changed; AR-004/AR-006/AR-007/AR-008 remain **not decided**;
  implementation still not authorized; `main` and plain `dev` untouched. Awaiting further
  instruction.

---

### Phase 1 Domain Model + DEC-003 Scope-Hole Closure — compact handoff (2026-07-02)

> **Documentation / decision-preparation sprint, not implementation.** Confirmed PR #61
> merged into `Shopify-connector` (merge commit
> `26dc30109530e2566755fd93bd974284083c3922`) before editing; DEC-004/DEC-005/DEC-006
> confirmed **Accepted by ChatGPT**; AR-002/AR-003/AR-005 confirmed **Accepted**;
> AR-004/AR-006/AR-007/AR-008 confirmed **not decided**. Branch created from that exact
> commit (verified via `git merge-base`). Produced a Phase 1 domain-model brief and a
> proposed DEC-007 scope-clarification addendum closing five known DEC-003 scope holes.

- **Branch / PR:** `claude/domain-model-scope-closure-nv8ah9` (harness-assigned; the
  sprint's preferred name `product/domain-model-scope-closure` was not used — per the
  session's hard git rule, work proceeded on the harness-assigned branch, confirmed based
  exactly on `Shopify-connector`'s PR #61 merge commit before any edit; flagged as the
  branch-name discrepancy) → draft PR into `Shopify-connector`, opened immediately after
  this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/phase1-domain-model-brief.md` (new),
  `docs/04-decisions/DEC-007-phase1-scope-clarifications.md` (new),
  `docs/02-product/mvp-scope.md`, `docs/02-product/non-mvp-and-later-phases.md`,
  `docs/02-product/user-stories.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/01-research/research-handoff.md` (this
  file).
- **What changed:** authored
  [`phase1-domain-model-brief.md`](../03-architecture/phase1-domain-model-brief.md) — a
  documentation-level (not schema-level) Phase 1 concept map across eight domains (store/
  connection, binding/identity, product, customer, order/sale, inventory, fulfilment,
  queue/log/error), each statement labelled accepted decision / proposed clarification /
  inference / open question. Proposed
  [`DEC-007`](../04-decisions/DEC-007-phase1-scope-clarifications.md)
  (`Status: Proposed for ChatGPT review`) closing five DEC-003 scope-hole wordings: (1)
  variant export/update is included, not optional, wherever product export/update is in
  MVP; (2) image/media "where feasible" replaced with an explicit
  included/excluded/deferred split (basic image sync in; advanced dedup/alt-text/CDN/
  media-governance out); (3) price/compare-at "where feasible" replaced the same way, plus
  an explicit price source-of-truth requirement; (4) a **first-inventory-push guard**
  (mapped location + preview + operator confirmation + recorded source-of-truth + skip/
  manual-match option) before any first Odoo→Shopify inventory write; (5) a **fulfilment
  customer-notification default** of "no notification unless explicitly enabled," grounded
  in newly verified Shopify API defaults; (6) a tax/shipping/discount/payment-evidence
  clarification requiring evidence preservation sufficient for reconcilable totals, with
  conservative-by-default invoice/payment creation (no silent accounting automation). Ran a
  **small, targeted official-source check** (per the sprint's external-research rule, since
  the tax-line/shipping-line/discount-line fields and the fulfilment notification defaults
  were not already grounded in repo docs): verified `Order.taxLines`/`shippingLines`/
  `discountApplications` and `FulfillmentInput.notifyCustomer` (defaults `false`) /
  `fulfillmentTrackingInfoUpdate`'s `notifyCustomer` (defaults to no notification) against
  `shopify.dev` official pages, access date 2026-07-02 — cited with URL in DEC-007 and the
  domain-model brief; **not** propagated into `../01-research/shopify-official-api-notes.md`
  (outside this sprint's allowed-files list — flagged as a follow-up). Added five new Phase
  1 user stories tied to the clarifications (`US-E2-07` variant export/update, `US-E2-08`
  product/variant export preview/dry-run, `US-E4-07` financial evidence mapping, `US-E5-06`
  first inventory push guard, `US-E6-04` fulfilment notification control) to
  `user-stories.md`. Added pointer notes (not rewrites, not acceptance claims) to
  `mvp-scope.md` and `non-mvp-and-later-phases.md` referencing the proposed DEC-007.
  Added a non-decision note to `architecture-review-log.md` confirming AR-006/AR-007/
  AR-008 stay "Not decided / Evidence pending" and are **fed, not decided**, by this
  sprint's guardrail-level clarifications; AR-002/AR-003/AR-005 remain **Accepted**,
  untouched. Added **RA-008** (blind first inventory push), **RA-009** (hidden/default-on
  fulfilment notification), and **RA-010** (automatic full accounting/payment
  reconciliation by default) to `rejected-approaches-log.md`, each tagged **PROPOSED**
  (non-binding until DEC-007 is accepted, mirroring the RA-002–RA-007 precedent);
  automatic name-only matching was **not** re-logged (already covered by the binding
  RA-006).
- **Items deferred:** AR-004/AR-006/AR-007/AR-008 full architecture decisions; exact Odoo
  model/field/constraint design; exact GraphQL mutation strategy for variant writes; the
  Master Blueprint; propagating the two newly verified Shopify facts into
  `shopify-official-api-notes.md`; all implementation.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new. **New rejected
  approaches:** RA-008/RA-009/RA-010, tagged **PROPOSED** (see
  `rejected-approaches-log.md`). **New technical debt:** none (no code). **Architecture
  concerns:** AR-006/AR-007/AR-008 remain **Not decided / Evidence pending** — this
  sprint's first-inventory-push guard and fulfilment-notification default are explicitly
  **scope-level guardrail statements**, not AR-007/AR-008 mechanism decisions; AR-002/
  AR-003/AR-005 unchanged (**Accepted**).
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (no new issues) · rejected approaches logged (RA-008–RA-010, tagged
  PROPOSED) · technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** **ChatGPT/Fable review of DEC-007 and the Phase 1
  domain-model brief; if DEC-007 is accepted, a Master Blueprint sprint** (and/or a
  dedicated AR-006/AR-007/AR-008 architecture-decision sprint) **can follow.**
- **Stop condition:** stopped after three staged commits + one **draft** PR into
  `Shopify-connector` (not merged). PR #61 merge confirmed first. DEC-003/DEC-004/
  DEC-005/DEC-006 not edited; no code files changed; AR-002/AR-003/AR-005 remain
  **Accepted**; AR-004/AR-006/AR-007/AR-008 remain **not decided**; implementation still
  not authorized; `main` and plain `dev` untouched. Branch-name discrepancy flagged above.
  Awaiting ChatGPT/Fable review.

#### PR #62 revision (2026-07-02, ChatGPT review — REVISE MINOR before Fable review)

- ChatGPT reviewed PR #62 and requested minor wording cleanup before Fable review.
- Fixed five-vs-six clarification wording in DEC-007 (six clarification sections covering
  five known scope-hole themes; image/media and price split into separate sections).
- Made DEC-007 "What this unlocks" conditional on ChatGPT acceptance.
- Clarified that the phase-exit criterion is not satisfied until DEC-007 is accepted.
- Reworded the domain brief's schema-design deferral to "Master Blueprint /
  implementation-planning sprint."
- **DEC-007 remains `Proposed for ChatGPT review`.** No implementation authorized.
  DEC-003/004/005/006 untouched. No code files touched. Only
  `DEC-007-phase1-scope-clarifications.md`, `phase1-domain-model-brief.md`, and this
  handoff were edited — product docs, `architecture-review-log.md`, and
  `rejected-approaches-log.md` were not touched in this revision.

#### PR #62 Fable fix-up (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES)

- Fable reviewed PR #62 and returned **ACCEPT WITH MINOR CHANGES**.
- Applied small fix-up: fixed `architecture-review-log.md` markdown italics (missing
  closing underscore on the DEC-004/005/006 acceptance-patch note; stray double
  underscore on the PR #62 sprint note); corrected/qualified the `shippingLines` quote
  (no longer presented as a complete verbatim quote) in DEC-007 and the domain-model
  brief; indexed DEC-007 in `docs/04-decisions/README.md` as `Proposed for ChatGPT
  review`, not accepted; added an open question for first-push-guard granularity
  (per-store vs. per-binding vs. another AR-007 unit) to DEC-007 and the domain-model
  brief; added an open question for how Shopify-computed tax is represented in Odoo
  without recomputation to DEC-007 and the domain-model brief; clarified wording so
  "AR-002 implementation planning" reads as "implementation planning under the accepted
  DEC-004 / AR-002 decision" (AR-002 itself is accepted; only mechanics remain open).
- **DEC-007 remains `Proposed for ChatGPT review`, not accepted.** DEC-003/004/005/006
  untouched. `rejected-approaches-log.md` untouched. Product docs untouched. No code
  files touched. No implementation authorized.

---

### DEC-004/005/006 Acceptance Patch — compact handoff (2026-07-02)

> **Architecture acceptance patch, not implementation.** Confirmed PR #60 merged into
> `Shopify-connector` (merge commit `7eb875e4ca29b80c4745bd8f5354450aa1e4d37b`) before
> editing. Branch created from latest `Shopify-connector` using the preferred name
> `architecture/accept-dec004-dec005-dec006` (no harness override observed this
> session). Recorded ChatGPT's formal acceptance of DEC-004, DEC-005, and DEC-006.

- **Branch / PR:** `architecture/accept-dec004-dec005-dec006` → draft PR into
  `Shopify-connector`, opened immediately after this handoff commit, **not merged**.
- **Files changed:** `docs/04-decisions/DEC-004-distribution-api-auth-strategy.md`,
  `docs/04-decisions/DEC-005-sync-orchestration-strategy.md`,
  `docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md`,
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`,
  `docs/01-research/research-handoff.md` (this file).
- **What changed:** DEC-004/005/006 Status changed from `Proposed for ChatGPT review`
  to **`Accepted by ChatGPT`**, acceptance date **2026-07-02**; opening notes reworded
  from "proposal, not an acceptance" to "accepted architecture decision record";
  no-implementation clauses kept but reworded (acceptance ≠ automatic implementation
  authorization — the separate Phase 1 research-phase-exit + implementation gate
  still applies, `../05-qa/quality-feedback-loop.md` §10). AR-002/AR-003/AR-005 Review
  decision + Status cells in `architecture-review-log.md` changed to **"Accepted by
  ChatGPT"** / **"Accepted"**, linked to the now-accepted DEC files. RA-002 through
  RA-007 in `rejected-approaches-log.md` had the `PROPOSED:` prefix removed and their
  "Related decision record" cells updated to cite each DEC file's `Accepted by
  ChatGPT` status — **these six rows are now binding final rejected approaches**
  (`CLAUDE.md` §10 applies in full); the prior "non-binding until acceptance"
  governance note is superseded, not deleted. `docs/04-decisions/README.md` now
  describes DEC-004/005/006 as accepted (the first accepted architecture ADRs in the
  repo), keeps the DEC-vs-ADR-NNNN naming note, and states implementation is not
  automatically authorized until the next implementation-gate/blueprint phase.
- **Items deferred:** none new this patch (decision-substance unchanged; only
  status/acceptance wording updated, per this sprint's explicit scope).
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new.
  **New rejected approaches:** none new (RA-002–RA-007 finalized, not created).
  **New technical debt:** none (no code). **Architecture concerns:** AR-002/AR-003/
  AR-005 now **Accepted**; AR-004/AR-006/AR-007/AR-008 **still not decided**.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked
  · learning captured (no new issues) · rejected approaches finalized (RA-002–RA-007)
  · technical debt logged (none applicable — no code) · repeated-issue escalation
  applied (none at threshold) — all **YES**.
- **Next recommended session:** **Phase 1 Domain Model + DEC-003 Scope-Hole
  Closure.**
- **Stop condition:** stopped after one commit + one **draft** PR into
  `Shopify-connector` (not merged). PR #60 merge confirmed first. DEC-003 untouched;
  no code files changed; AR-004/006/007/008 not decided; implementation still not
  authorized; `main` and plain `dev` untouched. Awaiting further instruction.

---

### Evidence Refresh + Combined AR-002/003/005 Decision Preparation — compact handoff (2026-07-02)

> **Decision-preparation sprint, not implementation.** Confirmed PR #59 merged into
> `Shopify-connector` (tip `85a230a`) before editing; the harness-assigned branch
> `claude/ar-decision-prep-p2wpo7` is based directly on that commit (the sprint's
> preferred name, `architecture/ar002-ar003-ar005-decision-prep`, was not used — the hard
> git rule designates the harness branch; flagged per instruction). Ran a **small,
> targeted official-source refresh** (Odoo.sh docs + OCA `queue_job` community evidence
> only — no broad web research, no competitor research redone) and produced **three
> proposed** (not accepted) architecture decision records for AR-002, AR-003, and AR-005.

- **Branch / PR:** `claude/ar-decision-prep-p2wpo7` (harness-assigned; preferred name
  `architecture/ar002-ar003-ar005-decision-prep` not available — see branch-name
  discrepancy note below) → draft PR into `Shopify-connector`, opened immediately after
  this handoff commit, **not merged**.
- **Files changed:** `docs/03-architecture/ar002-ar003-ar005-evidence-refresh.md` (new),
  `docs/01-research/odoo-official-architecture-notes.md`,
  `docs/04-decisions/DEC-004-distribution-api-auth-strategy.md` (new),
  `docs/04-decisions/DEC-005-sync-orchestration-strategy.md` (new),
  `docs/04-decisions/DEC-006-binding-dedup-identity-strategy.md` (new),
  `docs/04-decisions/README.md`, `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/rejected-approaches-log.md`, `docs/05-qa/defect-pattern-log.md`,
  `docs/01-research/research-handoff.md` (this file).
  `docs/01-research/shopify-official-api-notes.md` was **not** edited — no new Shopify
  fact needed re-verification (the RB-14 Part 1/2 refresh, 2026-07-01, remains current
  one day later; re-fetching the same pages would be token waste, DP category 17).
- **What changed / evidence refreshed:** targeted external check of **official Odoo.sh
  docs** — `server_wide_modules`/external-Jobrunner support is **not addressed** in any
  fetched page (absence of documentation, not a documented denial); production
  scheduled actions run on a **"best effort," ≥5-minute-interval, execution-time-limited**
  basis (new, sharper than the previously-known "staging crons disabled" fact); plus a
  **community-tier** check of **OCA `queue_job`** (repo renamed `OCA/queue`) confirming a
  19.0 PyPI release exists, its Jobrunner now runs as an Odoo **worker process** (not a
  separate external daemon) but still needs `server_wide_modules` + `--workers > 0`. Full
  record: `docs/03-architecture/ar002-ar003-ar005-evidence-refresh.md`.
- **Proposed decisions created (each `Status: Proposed for ChatGPT review`, none
  accepted, none implementation-authorizing):**
  - **DEC-004** (AR-002) — custom/Admin-created Shopify app (Early Access, no App
    Store), GraphQL Admin API primary/default, offline-token auth with masked
    storage/least-privilege scopes; public App Store/OAuth/Billing deferred.
  - **DEC-005** (AR-003) — HMAC-verified fast-ack webhook receiver + webhook-ID dedup →
    internal Odoo queue/job model → `ir.cron`-driven batch processing, on **Odoo.sh or
    on-premise** (not Odoo Online); manual sync + scheduled reconciliation always on;
    per-record isolation + retry counters + dead/final-failed state; **OCA `queue_job`
    deferred/optional, not the Phase 1 default** (Odoo.sh jobrunner feasibility
    unconfirmed).
  - **DEC-006** (AR-005) — dedicated/hybrid per-store connector binding model as the
    source of truth (Shopify GID + Odoo model/record stored explicitly, per-store
    uniqueness constraints); `ir.model.data` **rejected as the primary** mechanism (not
    for all uses); match priority existing-binding → SKU/internal-reference → barcode →
    email/customer keys → manual; **no name-only automatic matching**.
- **Rejected/deferred approaches logged (all tagged PROPOSED, tied to the DEC files'
  own "Proposed for ChatGPT review" status — not final rejections):** RA-002 REST-heavy
  API strategy; RA-003 public App Store/OAuth/Billing as a Phase 1 architecture
  requirement; RA-004 OCA `queue_job` as the Phase 1 **default** substrate (not rejecting
  `queue_job` itself); RA-005 `ir.model.data` as the **primary** binding mechanism (not
  rejecting all use of `ir.model.data`); RA-006 name-only automatic matching.
- **Items deferred:** exact binding/queue-table schema and field design (a future
  domain-model sprint); AR-006/007/008 (explicit non-goals this sprint); AR-004 module
  boundaries; the OAuth-vs-plain-token and token-expiry-variant sub-choice within
  DEC-004's offline-token model; MVP-scale throughput validation under
  `--max-cron-threads=2`; Odoo.sh `server_wide_modules` confirmation (open — carried
  forward as a DEC-005 revisit trigger).
- **Branch-name discrepancy (flagged per instruction):** the sprint's preferred branch
  name was `architecture/ar002-ar003-ar005-decision-prep`; per the session's hard git
  rule (never push to a different branch without explicit permission), work proceeded
  on the harness-assigned `claude/ar-decision-prep-p2wpo7`, which was confirmed based
  exactly on `Shopify-connector`'s PR #59 merge tip (`85a230a...`) before any edit.
- **Learning feedback loop:** **New issues discovered:** none. **Repeated issue
  patterns:** none at threshold. **Rules/checklists updated:** none new — DP-006
  (evidence-consistency gate) applied, not re-triggered (Odoo.sh silence kept as an
  open question, not read as denial; OCA evidence kept community-tier, never promoted
  to Odoo official fact). **New rejected approaches:** RA-002–RA-006 (see above),
  explicitly tagged **PROPOSED** — see the framing note added to
  `rejected-approaches-log.md` explaining why they precede full ChatGPT acceptance
  (per this sprint's explicit instruction) rather than following the RA-001 precedent
  of logging only after acceptance. **New technical debt:** none (no code). **Architecture
  concerns:** AR-002/AR-003/AR-005 move to **"Proposed for ChatGPT review"** in
  `architecture-review-log.md` — explicitly **not** "Accepted"; AR-004/006/007/008
  untouched.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop checked ·
  learning captured (DP-log note, no new row) · rejected approaches logged (RA-002–
  RA-006, tagged PROPOSED) · technical debt logged (none applicable — no code) ·
  repeated-issue escalation applied (none at threshold) — all **YES**.
- **Next recommended session:** **ChatGPT/Fable review of proposed DEC-004/005/006,
  then Phase 1 Domain Model + DEC-003 Scope-Hole Closure sprint if accepted.**
- **Stop condition:** stopped after three staged commits + one **draft** PR into
  `Shopify-connector` (not merged). No connector code, no Odoo module, no forbidden
  files touched. DEC-003 body not edited; MVP scope unchanged; AR-002/003/005 marked
  **Proposed for ChatGPT review**, not Accepted; AR-004/006/007/008 not decided; `main`
  and plain `dev` untouched. Awaiting ChatGPT/Fable review.

#### PR #60 revision (2026-07-02, ChatGPT + Fable review — ACCEPT WITH MINOR CHANGES)

- Fable reviewed PR #60 and returned **ACCEPT WITH MINOR CHANGES**.
- Applied the required fixes and nits: added **RA-007** for external worker as the
  Phase 1 substrate (fixing DEC-005's dangling rejected-approaches pointer);
  reconciled DEC-004's non-public custom-app / app-creation-surface /
  token-acquisition wording (creation surface + token mechanics left to
  implementation planning, not hard-fixed); clarified RA-002–RA-007 are
  non-binding until the linked DEC is accepted (`rejected-approaches-log.md`
  governance clarifier); fixed the `04-decisions/README.md` naming wording
  (DEC-004/005/006 **follow** the DEC-003 precedent, do not **predate** the
  ADR-NNNN convention); changed DEC-005 Option 5's disposition to **"Weakened"**
  (no RA row exists for it).
- **DEC-004/005/006 remain `Proposed for ChatGPT review`** — not accepted by this
  revision.
- **No implementation authorized. DEC-003 untouched. No code files touched.**

---

### Control-Room Reset Sprint 1 — compact handoff (2026-07-02)

> **Documentation residue sweep, convergence gates, and anti-bloat maintenance
> rule.** A mechanical cleanup/convergence sprint (not research) run after PR #58
> (RB-14 Part 2) merged into `Shopify-connector`. No high-power mode used (repo-
> local reading/grep only). Full detail:
> [`../05-qa/documentation-residue-sweep.md`](../05-qa/documentation-residue-sweep.md).

- **Branch / PR:** `claude/ready-check-nb2y99` (harness-assigned) → draft PR
  into `Shopify-connector`, **not merged**.
- **Files changed:** `docs/04-decisions/README.md`, `docs/03-architecture/README.md`,
  `docs/05-qa/pr-review-checklist.md`, `docs/02-product/mvp-scope.md`,
  `docs/02-product/feature-taxonomy.md`, `docs/02-product/product-vision.md`,
  `docs/02-product/setup-ux-principles.md`,
  `docs/00-source-materials/screenshots/teqstars/README.md`,
  `docs/00-source-materials/source-access-notes.md`,
  `docs/01-research/research-backlog.md`,
  `docs/05-qa/rejected-approaches-log.md`,
  `docs/05-qa/documentation-residue-sweep.md` (new),
  `docs/05-qa/quality-feedback-loop.md`, `CLAUDE.md`,
  `docs/06-prompts/session-handoff-template.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/05-qa/architecture-review-log.md`, `docs/05-qa/defect-pattern-log.md`.
- **What changed / residue fixed:** stale "MVP not finalized" / "Proposed —
  pending ChatGPT acceptance" statements corrected against the accepted
  DEC-003 baseline (`mvp-scope.md`, `feature-taxonomy.md`, `product-vision.md`,
  `setup-ux-principles.md`); TeqStars/TQ 403-blocked residue corrected against
  the Sprint C2 rebaseline (teqstars screenshot README, `source-access-notes.md`);
  `docs/04-decisions/README.md` and `docs/03-architecture/README.md` "Empty"
  claims corrected; `pr-review-checklist.md`'s MVP-finalization checkbox
  reworded (still blocks unauthorized architecture/implementation);
  `research-backlog.md`'s "Not started"/"Blocked" statuses corrected to `Done`
  for completed items (R5 / RB-02.6 correctly stays `Blocked`); DEC-003's
  Option C rejection logged as **RA-001** in `rejected-approaches-log.md`;
  added phase-exit criteria + a documentation-maintenance rule
  (`quality-feedback-loop.md` §10–§11, `[Recommendation — becomes binding when
  merged by ChatGPT]`, pointed to from `CLAUDE.md`); aligned
  `session-handoff-template.md` to a compact default (this entry uses it).
- **Items deferred:** off-allowed-list files with likely-already-fixed
  TeqStars residue (`ux-ui-benchmark.md`, `common-patterns.md`,
  `best-in-class-observations.md`, `avoid-list.md`, `competitor-deep-dives.md`,
  `competitor-screenshot-inventory.md` — not verified or edited this sprint);
  two stale TeqStars references inside **DEC-003 itself** (read-only this
  sprint — flagged for a future dated post-decision note, not added here); the
  `DEC-003` vs `ADR-NNNN-<slug>.md` naming/numbering inconsistency (flagged for
  ChatGPT, not resolved/invented).
- **Learning feedback loop:** new issue — **documentation residue: stale
  current-truth statements not updated when a later decision supersedes them,
  plus append-only handoff growth** — logged as **DP-007**
  (`defect-pattern-log.md`, category: unclear handoff #16, 1st occurrence;
  prevention = this sprint's phase-exit + documentation-maintenance rules).
  No repeated pattern at threshold. Rules updated:
  `quality-feedback-loop.md` §10–§11 (new). New rejected approach: RA-001
  (Option C, sourced from the existing DEC-003 decision, not newly rejected
  this sprint). No new technical debt (no code). Architecture concerns: none —
  no AR row touched; all stay "Not decided / Evidence pending" (non-decision
  note added to `architecture-review-log.md`). Should future prompts change?
  **Yes, minor** — future research/product sprints should correct a
  Status/Governance line **at the time** a later decision supersedes it,
  rather than leaving it for a dedicated cleanup sprint.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (DP-007) · rejected approach logged (RA-001) ·
  technical debt logged (none applicable — no code) · repeated-issue
  escalation applied (none at threshold) — all **YES**.
- **Compact handoff deviation:** authorized by this sprint's prompt
  (Control-Room Reset Sprint 1, "Compact handoff authorization"); recorded per
  that authorization.
- **Next recommended sprint:** **Evidence Refresh + Combined AR-002/003/005
  Decision Preparation**, after ChatGPT/Fable review of this PR.
- **Stop condition:** stopped after one draft PR into `Shopify-connector`
  (not merged). No connector code, no Odoo module, no forbidden files touched.
  DEC-003 body not edited; MVP scope unchanged; no AR row decided. `main` and
  plain `dev` untouched. Awaiting ChatGPT/Fable review.

### Control-Room Reset Sprint 1 — PR #59 revision (2026-07-02, ChatGPT REVISE)

> ChatGPT reviewed PR #59: **REVISE** — stayed in scope, but the first pass
> missed several current-truth stale residues in allowed files. Full detail:
> [`../05-qa/documentation-residue-sweep.md`](../05-qa/documentation-residue-sweep.md)
> ("PR #59 revision" section).

- **Files updated (this revision only):** `docs/02-product/feature-taxonomy.md`,
  `docs/02-product/capability-evidence-map.md`,
  `docs/02-product/setup-ux-principles.md`, `docs/03-architecture/README.md`,
  `docs/05-qa/rejected-approaches-log.md`,
  `docs/05-qa/documentation-residue-sweep.md`,
  `docs/01-research/research-handoff.md` (this file),
  `docs/05-qa/defect-pattern-log.md` (addendum note, no new row).
- **Residue fixed:** missed TeqStars/TQ 403/claim-only wording in
  `feature-taxonomy.md` (evidence-weighting + "weak or blocked evidence"
  section, routing language, no new per-cell claims) and
  `capability-evidence-map.md` (competitor-keys line + `C-DOCS-01/02` rows,
  corrected against already-merged Sprint C2 evidence only); stale
  single-store/multi-store "not decided" wording in `feature-taxonomy.md`
  (3 locations) corrected against DEC-003; stale Odoo Online
  compatibility "open question" in `setup-ux-principles.md` (2 locations)
  corrected against RB-14 Part 2 (PR #58); `rejected-approaches-log.md`'s
  historical notes still implying no rejection existed, now marked
  superseded by RA-001; `docs/03-architecture/README.md`'s "What belongs
  here" line still naming the phantom `architecture-preparation.md`.
- **Learning feedback loop:** addendum to **DP-007** (`defect-pattern-log.md`)
  — same category/root cause, not a new occurrence; reinforces that a residue
  sweep must grep a pattern across *every* allowed file, not stop at the first
  hit per file. No new rejected approach; no new technical debt; no AR row
  touched.
- **Quality gate confirmation:** handoff updated (this note) · feedback loop
  checked · learning captured (DP-007 addendum) · no new rejected approach ·
  no new technical debt · no repeated-issue escalation needed — all **YES**.
- **Stop condition:** stopped after pushing one commit to the same PR #59
  branch (not merged, no new PR opened). DEC-003 body untouched; MVP scope
  unchanged; no architecture decision made; `main`/plain `dev` untouched.
  Awaiting ChatGPT/Fable re-review.

---

# RB-14 Architecture Preparation — Part 2 Handoff

> **RB-14 Part 2 — High-risk open-question resolution and decision-candidate refinement.** The
> architecture-preparation sprint after PR #57 (RB-14 Part 1) merged into `Shopify-connector`.
> Re-checked **only** the high-risk open questions from Part 1 against **official Shopify docs**,
> **official Odoo 19.0 docs**, and **official Odoo 19.0 source code** (`odoo/odoo` 19.0); resolved/
> narrowed **only where official evidence supports it**; kept the rest open. Produced a **decision-
> candidate brief** and narrowed **AR-002/AR-003/AR-005** — **deciding none**. No-code and
> no-architecture-decision gates in force (`CLAUDE.md` §4–§5). Session date 2026-07-01.

## Session summary

Confirmed the pre-conditions (PR #55/#56/#57 merged into `Shopify-connector` — the branch is at
`ec6f494`, the PR #57 merge; AR-002/003/005 framed-not-decided; DEC-003 unchanged; implementation
unauthorized), then ran a **scoped, documented high-power verification** of the ten enumerated
high-risk questions. **Four source-code / GID questions were verified directly** by reading the
official `odoo/odoo` 19.0 source (`ir_cron.py`, `ir_model.py`, `odoo/orm/models.py`) and the
Shopify GID page; **six official-doc questions were verified by a fan-out** (6 verifiers + 6
adversarial cross-verifiers). **All six cross-verifiers confirmed their verifier's status** with
no surviving overclaim (two minor quote fixes applied). **AR-002/AR-003/AR-005 are refined but
NOT decided**; no REST/GraphQL, distribution, OAuth/token, queue-framework, binding/data-model,
or module-boundary choice was made; DEC-003 and MVP scope unchanged.

## Branch and commits

**Working branch:** `claude/rb-14-architecture-part-2-ey2a69` (the harness-designated branch;
based on `Shopify-connector` @ `ec6f494`, the merged **PR #57** tip). **Branch-name note for
ChatGPT (flagged):** the RB-14 Part 2 prompt named
`architecture/rb14-part2-risk-resolution-decision-candidates`, but the session's hard git rule
designates the harness branch (`claude/rb-14-architecture-part-2-ey2a69`) and forbids pushing to
a different branch without explicit permission, so work proceeded on the harness-designated
branch; **the PR targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `7e69111` | docs: resolve rb14 high-risk open questions |
| `fb00082` | docs: refine rb14 decision candidates |
| _(this commit)_ | docs: update rb14 part2 handoff and qa gates |

## High-power research mode used

**Yes — scoped to official-source / source-code verification only** (authorized by the prompt's
capability instruction + `CLAUDE.md` high-power section). **Plan (documented before launch):**
(a) **Why:** training cutoff is Jan 2026; the ten high-risk questions need live 2026-07-01
verification, four against actual 19.0 source. (b) **Workstreams:** four source-code/GID reads
done directly in the main loop; a 6-verifier + 6-adversarial-cross-verifier fan-out for the
remaining official-doc questions, each fetching a fixed official page set and returning
verbatim-quoted, claim-classified facts. (c) **Sources:** `shopify.dev` + official changelog;
`odoo.com/documentation/19.0` + official 19.0 raw RST; official `odoo/odoo` 19.0 source. **No
competitor/blog/forum.** (d) **Stop condition:** each question resolved only where official
evidence literally supports it; else kept open. (e) **Synthesis/verification:** worker-owned
classification + adversarial cross-verify (default to the more conservative status); source
findings labelled `[Official source-code fact]`; two quote-transcription fixes applied. (f)
**Unsupported-claim prevention:** absence ≠ opposite; negatives (e.g. "no async queue in core")
stay inferences; nothing promoted to a decision. **Result:** all statuses upheld by cross-verify;
~280k subagent tokens + the direct source reads.

## Files created or updated

**Architecture (`docs/03-architecture/`) — new:** `rb14-part2-open-question-resolution.md`,
`rb14-decision-candidate-brief.md`. **Updated:** `architecture-decision-framing.md`,
`ar-002-distribution-api-framing.md`, `ar-003-sync-orchestration-framing.md`,
`ar-005-binding-dedup-framing.md` (RB-14 Part 2 notes; Part 1 preserved; rows stay `[Not
decided]`).

**Research (`docs/01-research/`) — updated:** `shopify-official-api-notes.md` (RB-14 Part 2
section), `odoo-official-architecture-notes.md` (RB-14 Part 2 section incl. source-code facts),
`research-handoff.md` (this file).

**QA (`docs/05-qa/`) — updated:** `architecture-review-log.md` (RB-14 Part 2 non-decision note),
`defect-pattern-log.md` (RB-14 Part 2 no-new-defect note; no counter change).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker; no
`addons/**`; no `docs/04|06|07|08`; no `.claude/**`). **DEC-003 not modified; MVP scope
unchanged.**

## Questions resolved / narrowed (official evidence)

- **Resolved (from source):** RQ-003-3 (`ir.cron` signatures + failure constants 3/5/7d);
  RQ-005-3 (`ir.model.data` fields + `UniqueIndex('(module, name)')`); RQ-005-4 (`sudo()`
  bypasses access rights **and** record rules).
- **Materially narrowed (Shopify docs):** RQ-005-2 (**24-hour** idempotency dedup TTL + fixed
  **17-mutation** `@idempotent` set; no general mechanism / `clientMutationId`); RQ-003-1 (**Odoo
  Online incompatible with custom modules** → substrate Odoo.sh/on-prem); RQ-002-1 (custom apps
  **not categorically forbidden from REST**; GraphQL sole long-term API; no REST EOL); RQ-002-2
  (protected-data access **"Always available"** for custom apps vs **"Requires review"** for
  public; compliance webhooks App-Store-scoped); RQ-002-3 (offline token model + 90-day rotating
  refresh).
- **Re-confirmed open:** RQ-005-1 (GID permanence **not asserted**); RQ-003-2 (`[Official
  source-code fact]` reviewed source confirms `ir.cron` + signatures/constants + `with_delay`
  absent; `[Inference]` a general async queue was not found in the reviewed docs/source; `[Open
  question]` whole-repo absence; OCA `queue_job` community).

## Questions still open (blocking a confident decision)

- **AR-002:** blanket custom/private GraphQL-mandate scope + REST EOL; whether custom apps **must
  implement** the compliance webhooks / are bound by L1/L2 obligations (**not assumed absent**).
- **AR-003:** Odoo.sh/on-prem `server_wide_modules` + jobrunner support (gates `queue_job`);
  MVP-scale throughput under `--max-cron-threads=2`.
- **AR-005:** `@idempotent` key-uniqueness scope; bulk-op idempotency; GID permanence/non-reuse;
  the per-store binding data-model decision itself.

## Candidate-narrowing summary (inputs, not decisions)

- **AR-002 [Decision candidate]:** custom app + GraphQL-first + offline token (lead); public app
  later; hybrid weak; REST-heavy avoid-candidate.
- **AR-003 [Decision candidate]:** internal cron-queue **or** `queue_job` (turnkey) primary;
  cron-only floor; external-worker + per-tier-hybrid weakened (Odoo Online excluded).
- **AR-005 [Decision candidate]:** dedicated per-domain **or** hybrid binding model primary;
  generic table viable; `ir.model.data` reuse weak/avoid; ID-on-record convenience-only.
- **All labelled `[Recommendation]`/`[Decision candidate]`; every AR row stays `[Not decided]`.**

## Learning feedback loop

- **New issues discovered:** none. **No new defect pattern; no new DP row; no counter change**
  (`../05-qa/defect-pattern-log.md` RB-14 Part 2 note). The sprint **applied** DP-001 (re-read the
  source — went to actual 19.0 source), DP-003/DP-004 (competitor evidence excluded from this
  official-only pass), DP-005 (options/candidates are inputs, not decisions), and the DP-006
  evidence-consistency gate (official fact / source-code fact / inference / open question kept
  distinct; conditional/absent items kept conditional/open, e.g. custom-app compliance obligations
  **not assumed absent**; the async-queue absence **kept an inference**).
- **Repeated issue patterns:** none at threshold.
- **Rules/checklists updated:** none new; reinforced (a) **verify load-bearing facts against
  actual source**, not just docs, when the docs are silent (four questions resolved this way);
  (b) the **adversarial cross-verify** default-to-conservative rule caught nothing to downgrade
  but confirmed no overclaim — a DP-003 application.
- **New rejected approaches:** none (narrowing only; weak/avoid-candidates are **not** formal
  rejections — `../05-qa/rejected-approaches-log.md` unchanged; formal rejection needs ChatGPT,
  `CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** AR-002/003/005 refined-not-decided; AR-004/006/007/008 remain
  later — non-decision note in `../05-qa/architecture-review-log.md`.
- **Should future prompts change? Minor:** architecture-prep prompts should keep authorizing
  **reading official source code** for load-bearing facts the docs don't state, and keep every
  narrowing an **input/`[Recommendation]`/`[Decision candidate]`** (never a decision). Branch
  reality remains the harness `claude/...` branch while the PR targets `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; official facts +
  source-code facts cited + dated + classified; competitor evidence excluded from this pass;
  every candidate `[Not decided]`; DEC-003 and MVP scope unchanged; handoff + learning loop
  updated.

## What ChatGPT should review

1. **Open questions are resolved only where official evidence supports it** — spot-check the
   verbatim quotes + URLs/source paths in `rb14-part2-open-question-resolution.md`.
2. **Open questions remain open where evidence is missing** (custom-app compliance obligations;
   `@idempotent` key scope; bulk-op idempotency; GID permanence; whole-repo async-queue absence).
3. **Source-code facts are not turned into architecture decisions** — labelled `[Official
   source-code fact]`, routed as inputs.
4. **Decision candidates are not presented as decisions** — all `[Recommendation]`/`[Decision
   candidate]`; every AR row `[Not decided]`.
5. **No REST/GraphQL, queue, binding, data-model, module, or distribution choice is made.**
6. **MVP scope and DEC-003 remain unchanged; implementation remains blocked.**
7. **UX skill usage stays at the implications level** (no screens/wireframes).

## Stop condition

Stopped at the RB-14 Part 2 boundary: three stage commits on the harness-designated branch + one
**draft** PR targeting **`Shopify-connector`**, **not merged**. **No** connector code, Odoo
module, architecture decision, ADR, implementation plan, module boundary, or REST/GraphQL/
queue-framework/data-model/distribution choice. **DEC-003 and MVP scope unchanged.** `main` and
plain `dev` untouched; only RB-14 Part 2 allowed files changed. Awaiting ChatGPT review.

## Recommended next session

**RB-14 Part 3 — Architecture Decision Sprint for AR-002** (distribution + API + auth), **only if
ChatGPT accepts Part 2.** AR-002 is the most narrowed (custom + GraphQL-first + offline-token lead
candidate) and constrains AR-003 (hosting) and AR-005 (idempotency surface); then AR-003 + AR-005
in parallel, then AR-006/007/008, with AR-004 last. Keep the no-code gate; one scoped objective
per session. **The Part 3 prompt is not written here (not requested).**

## Quality gate confirmation (RB-14 Part 2)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (RB-14 Part 2 no-new-defect note in
  `defect-pattern-log.md`; RB-14 Part 2 non-decision note in `architecture-review-log.md`).
- [x] Any rejected approach logged (none — narrowing only; weak/avoid-candidates are not formal
  rejections).
- [x] Any accepted technical debt logged (none — no code).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-001/003/004/005/006
  applied, not re-triggered).

---

# RB-14 Architecture Preparation — Part 1 Handoff

> **RB-14 Part 1 — Official-source refresh and architecture decision framing.** The first
> architecture-preparation sprint after the research + MVP-scope baselines merged (PR #55 DEC-003,
> PR #56 TeqStars rebaseline). Produced the **first documents under `docs/03-architecture/`** — a
> current **official-source refresh** and **decision framing** for **AR-002** (distribution/API),
> **AR-003** (sync orchestration/queue), and **AR-005** (binding/dedup/identity). **Frames the
> decisions; decides none.** No-code gate and no-architecture-decision gate in force
> (`CLAUDE.md` §4–§5). Session date 2026-07-01.

## PR #57 revision (2026-07-01, ChatGPT review — REVISE)

ChatGPT reviewed PR #57 and returned **REVISE** for **source-classification and evidence-date
consistency** (the framing substance was accepted directionally — AR-002/003/005 framed-not-decided;
no code; no architecture decision; no implementation authorization). Corrected on the same branch
(`docs: clean rb14 classification and date caveats`) **without changing architecture scope or any
decision**: (1) the Shopify/Odoo official-notes "Source hierarchy and access date" sections now
distinguish the **Sprint B baseline (2026-06-30)** from the **RB-14 refresh (2026-07-01)** and
record GraphQL `latest` moving `2026-04`→`2026-07` (version-sensitive facts use the RB-14 refresh);
(2) **"Odoo core has no async job queue"** downgraded from **[Official fact] → [Inference from
official fact]** (docs document only `ir.cron`; `queue_job` community, not core; verify vs 19.0
source if load-bearing); (3) **secret/config storage** (`ir.config_parameter`/config-model/
encrypted-field) no longer implied as an official recommendation — **[Open question] + [Inference]**;
(4) **`ir.model.data` column list + `(module,name)` uniqueness** kept **[Open question]**;
(5) **custom-app compliance-webhook** wording made conservative — App-Store *review gate* may not
apply, but **non-App-Store privacy/data-deletion obligations left [Open question], not assumed
absent** (dropped "sidesteps"). **No architecture decision; DEC-003 and MVP scope unchanged; no
code; implementation still blocked.** Logged as a no-new-defect note in
`../05-qa/defect-pattern-log.md` (no counter change).

## Session summary

Confirmed the pre-conditions (PR #55 + PR #56 merged into `Shopify-connector`; DEC-003 accepts
controlled product import/export/update in MVP; customer export + full autonomous bidirectional
catalog management remain later; architecture undecided; implementation unauthorized), then ran a
**scoped, documented high-power official-source refresh** (13 Tier-1 verifiers, ~40 `shopify.dev`
/ `odoo.com/19.0` pages, verbatim-quoted and claim-classified, competitor sources excluded) and
authored the RB-14 framing set. **AR-002/AR-003/AR-005 are framed with candidate options,
evidence-for/against, risks, UX implications, required-evidence-before-decision, and recommended
decision criteria — every option labelled `[Not decided]`.** **AR-004/AR-006/AR-007/AR-008 remain
not framed and not decided.** No connector code, no Odoo module, no ADR, no implementation plan,
no module boundary, and **no REST/GraphQL, queue-framework, binding/data-model, or distribution
choice** was produced. DEC-003 and MVP scope are unchanged.

## Branch and commits

**Working branch:** `claude/rb-14-architecture-prep-lwaeeq` (the harness-designated branch; based
on `Shopify-connector` @ `5c27e60`, the merged **PR #56** tip, which includes the **PR #55**
DEC-003 baseline). **Branch-name note for ChatGPT (flagged):** the RB-14 prompt named
`architecture/rb14-part1-official-refresh-decision-framing`, but the session's hard git rule
designates the harness branch (`claude/rb-14-architecture-prep-lwaeeq`) and forbids pushing to a
different branch without explicit permission, so work proceeded on the harness-designated branch;
**the PR targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| _(commit 1)_ | docs: refresh official architecture sources |
| _(commit 2)_ | docs: frame rb14 architecture decisions |
| _(commit 3)_ | docs: update rb14 handoff and qa gates |

## High-power research mode used

**Yes — focused and scoped to official-source verification only** (authorized by the prompt's
token-control instruction and `CLAUDE.md` high-power section). **Plan (documented before launch):**
(a) **Why:** training cutoff is Jan 2026, so a genuine 2026-07-01 refresh across ~40 official pages
for AR-002/003/005 requires live fetch. (b) **Workstreams:** 8 Shopify + 5 Odoo topic verifiers,
each fetching a fixed page set and returning classified facts with verbatim quotes. (c) **Sources:**
`shopify.dev` and `odoo.com/documentation/19.0` (+ the official `odoo/documentation` 19.0 raw RST
where the HTML was JS-nav-only) — **no competitor/blog/forum**. (d) **Stop condition:** load-bearing
facts re-verified current, deltas surfaced, framing written, no decisions. (e) **Synthesis/
verification:** worker-owned classification; not-on-page → open question; competitor evidence never
promoted. **Result:** 13/13 verifiers returned; facts largely **confirmed unchanged**, with a few
**version-sensitive deltas** flagged and several facts **conservatively downgraded to open
questions** (no over-claiming). ~300k subagent tokens; 102 tool calls.

## Files created or updated

**Architecture (`docs/03-architecture/`) — new:** `rb14-official-source-refresh.md`,
`architecture-decision-framing.md`, `ar-002-distribution-api-framing.md`,
`ar-003-sync-orchestration-framing.md`, `ar-005-binding-dedup-framing.md`.

**Research (`docs/01-research/`) — updated:** `shopify-official-api-notes.md` (RB-14 refresh
section + version-sensitive deltas), `odoo-official-architecture-notes.md` (RB-14 refresh section
+ sharpened caveats), `research-handoff.md` (this file).

**QA (`docs/05-qa/`) — updated:** `architecture-review-log.md` (RB-14 Part 1 non-decision note —
AR-002/003/005 framed-not-decided; AR-004/006/007/008 not framed/not decided; refresh completed;
implementation blocked), `defect-pattern-log.md` (RB-14 no-new-defect note; no counter change).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker; no
`addons/**`; no `docs/04|07|08`; no `.claude/**`). **DEC-003 not modified; MVP scope unchanged.**

## Official sources refreshed (2026-07-01)

Shopify: API strategy/versioning; products/`productSet`/variants; inventory + `@idempotent`;
orders + protected customer data; webhooks + HMAC + reconciliation; rate limits + bulk ops; auth +
distribution + compliance webhooks; GIDs/identity. Odoo: `ir.cron` reliability; **async-queue
absence as an [Inference from official fact]** (docs document only `ir.cron`; `queue_job` is
community, not core); `--max-cron-threads`; ORM/external IDs/`ir.model.data`; security (access
rights/record rules); Odoo.sh
/on-prem hosting. **Confirmed unchanged** except the deltas below; full dated record in
`docs/03-architecture/rb14-official-source-refresh.md`.

## High-risk facts (for ChatGPT verification)

1. **Custom-vs-public GraphQL mandate** — GraphQL-only "must" is stated only for *new public
   apps*; custom/private scope is an open question (AR-002).
2. **GID permanence NOT asserted** — do not treat GID as an immutable uniqueness invariant yet
   (AR-005; deleted/recreated handling).
3. **No general mutation idempotency** beyond `@idempotent` — outbound write idempotency must be
   connector-designed (AR-005/AR-006).
4. **`@idempotent` required now** on inventory set/adjust (2026-04; `latest`=2026-07) — key-scope
   + dedup-TTL unstated (AR-005).
5. **`ir.model.data` `(module,name)` uniqueness/columns unconfirmed** in official docs — verify vs
   19.0 source before reusing it as a binding store (AR-005).
6. **`sudo()` bypass not literally on `security.rst`** — re-source before a credential-security
   design relies on it (AR-002/AR-005).
7. **Odoo Online feasibility open** — SaaS custom-module/worker support uncovered; gates the
   AR-003 substrate. **Hosting not finalized.**

## AR-002 / AR-003 / AR-005 framing status

- **AR-002 (distribution/API)** — **framed, not decided.** Options: public/OAuth/GraphQL-first;
  custom-app/GraphQL-first; hybrid; REST-heavy. Special attention: REST legacy + public-app
  GraphQL-only rule; `productSet` delete-on-omit (list fields); orders/inventory; bulk ops;
  protected customer data; custom-vs-public distribution; setup simplicity.
- **AR-003 (orchestration/queue)** — **framed, not decided.** Options: `ir.cron`-only; webhook +
  cron + internal queue model; webhook + OCA `queue_job`; webhook + external worker; hybrid by
  hosting tier. Special attention: no heavy sync inline; fast ack; per-record isolation; manual
  retry; reconciliation; idempotency hooks; user-friendly logs.
- **AR-005 (binding/dedup/identity)** — **framed, not decided.** Options: dedicated per-domain
  tables; generic binding table; `ir.model.data` reuse; Shopify-ID-on-record; hybrid. Special
  attention: per-store uniqueness; template-vs-variant; SKU/barcode changes; first-sync conflict;
  deleted/recreated Shopify records; manual override; multi-store future; auditability; no
  name-only auto-matching.
- **AR-004/AR-006/AR-007/AR-008** — **not framed, not decided** (AR-006/007/008 depend on
  AR-002/003/005; AR-004 recommended to wait). **Recommended decision order (a recommendation,
  not a decision):** AR-002 → AR-003 + AR-005 → AR-006/007/008; AR-004 last.

## Learning feedback loop

- **New issues discovered:** none. **No new defect pattern; no new DP row; no counter change**
  (`../05-qa/defect-pattern-log.md` RB-14 note). The refresh **applied** DP-001 (re-read the
  source — surfaced version deltas), DP-003/DP-004 (competitor evidence not promoted to official
  fact), DP-005 (options/order are inputs, not decisions), and the DP-006 evidence-consistency
  gate (facts/evidence/inference/recommendation/open-question kept distinct; conditional
  requirements stay conditional).
- **Repeated issue patterns:** none at threshold.
- **Rules/checklists updated:** none new; reinforced that **an official platform fact important
  to an architecture decision should be re-verified live before that decision** (the refresh
  found the `latest` alias moved and sharpened the `@idempotent` timeline within one day of the
  baseline) — a DP-001 application, not a new rule.
- **New rejected approaches:** none (framing only; `../05-qa/rejected-approaches-log.md` unchanged).
  Avoid-list items tagged "Arch review: YES" remain seeded against AR rows and become formal
  rejections **only after ChatGPT review** (`CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** AR-002/003/005 now framed (not decided); AR-004/006/007/008 not
  framed/not decided — non-decision note in `../05-qa/architecture-review-log.md`.
- **Tests or review gates needed:** none active; DP-006 evidence-consistency gate remains the
  standing pre-architecture review gate.
- **Should future prompts change? Minor:** architecture-framing prompts should keep every option
  and the decision order an **input/recommendation** (never a decision), and should **re-verify
  load-bearing official facts live** even against a recent baseline (version aliases + dated
  requirements drift). Branch reality remains the harness `claude/...` branch while the PR targets
  `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; official facts cited +
  dated + classified; competitor evidence not promoted; every option `[Not decided]`; DEC-003 and
  MVP scope unchanged; handoff + learning loop updated.

## What ChatGPT should review

1. **Official facts are cited, current (2026-07-01), and classified** — spot-check the verbatim
   quotes + URLs in `rb14-official-source-refresh.md` and the version-sensitive deltas.
2. **Competitor evidence is not promoted to official fact** — the framing docs label
   `[Competitor demonstrated]`/`[Competitor claim]` separately from `[Official fact]`.
3. **AR-002/AR-003/AR-005 are framed but not decided** — no REST/GraphQL, queue, binding, data
   model, module, or distribution choice; every option carries evidence-for/against + open
   questions + required-evidence-before-decision.
4. **The recommended decision order is a recommendation, not a decision.**
5. **MVP scope and DEC-003 remain unchanged; implementation remains blocked.**
6. **UX implications stay at the implications level** (no screens/wireframes designed).
7. **High-risk open questions** (custom-vs-public GraphQL; GID permanence; mutation idempotency;
   `ir.model.data` uniqueness; `sudo()` bypass sourcing; Odoo Online feasibility) are surfaced for
   direction, not resolved.

## Stop condition

Stopped at the RB-14 Part 1 boundary: three stage commits on the harness-designated branch + one
**draft** PR targeting **`Shopify-connector`**, **not merged**. **No** connector code, Odoo module,
architecture decision, ADR, implementation plan, module boundary, or REST/GraphQL/queue-framework/
data-model/distribution choice. **DEC-003 and MVP scope unchanged.** `main` and plain `dev`
untouched; only RB-14 allowed files changed. Awaiting ChatGPT review.

## Recommended next session

**RB-14 Architecture Preparation — Part 2: ChatGPT review-driven revision or decision-candidate
refinement** (depending on ChatGPT's review of this framing) — e.g. resolving the high-risk open
questions (custom-vs-public distribution, Odoo Online feasibility, `ir.model.data`/GID
verification) and narrowing AR-002/AR-003/AR-005 candidate options toward decision candidates,
**still gated** (no decision, no code, until ChatGPT approves an architecture-decision sprint).
Keep the no-code gate; one scoped objective per session. **The Part 2 prompt is not written here
(not requested).**

## Quality gate confirmation (RB-14 Part 1)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (RB-14 no-new-defect note in
  `defect-pattern-log.md`; RB-14 non-decision note in `architecture-review-log.md`).
- [x] Any rejected approach logged (none — framing only).
- [x] Any accepted technical debt logged (none — no code).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-001/003/004/005/006
  applied, not re-triggered).

---

# Research Sprint C2 Handoff — TeqStars Rebaseline and Evidence Correction

> **Research Sprint C2 — TeqStars rebaseline and evidence correction.** A scoped research
> **correction** sprint after PR #55: the TeqStars competitor docs, recorded **403-blocked
> in Sprint C (2026-06-30)**, were **re-checked accessible on 2026-07-01** and rebaselined.
> Research/documentation only; **no-code gate in force** (`CLAUDE.md` §4–§5); **architecture
> stays blocked**, **implementation stays blocked**. Focused high-power research (one
> capture-already-done + a compact adversarial-verification workflow) used **only** for
> TeqStars documentation review — no unrelated competitors crawled. Session date 2026-07-01.

## Session summary

Re-accessed the **TeqStars Odoo 19.0 Shopify documentation** (blocked in Sprint C by an
HTTP-403 **bot/UA filter**, since found to return **HTTP 200 with a browser user-agent** —
**no login wall, no auth bypassed, public content**) and read **all 31 Shopify doc pages**
(~98 embedded screenshots) inside step-by-step procedures. Corrected the TeqStars source
status from **blocked/claim-only → accessible, page-classified evidence**, and propagated the
correction into the source notes, resource inventory, screenshot inventory, competitor deep
dive, feature matrix, and the research synthesis (UX benchmark, common patterns,
best-in-class, gaps/opportunities, avoid-list) **only where the new evidence materially
changes conclusions**. Evidence was gathered with **evidence discipline preserved**
(demonstrated ✅ vs vendor claim 🟨 vs implied ➖ vs not-found ⬜ vs blocked 🔒) and an
**adversarial capture→verify pass** (17 high-stakes items) that **downgraded 3 proposed
upgrades** (automatic-retry/backoff, first-class cross-object reconciliation, and a
metrics/chart dashboard → **⬜ not found**), so **nothing was over-upgraded**. Product docs
received a **reinforcing note only** (TeqStars now demonstrates the accepted controlled
product import/export/update baseline and corroborates "customer export = later"); **DEC-003
and the accepted MVP scope are unchanged**. QA logs received a source-availability note (no
new defect row) and an architecture non-decision note (all AR rows stay Not decided). **No
connector code, no Odoo module, no architecture doc/ADR, no implementation plan, no module
boundary, no REST/GraphQL/queue-framework/data-model/distribution decision** was produced.

## Branch and commits

**Working branch:** `claude/teqstars-evidence-rebaseline-2nppgq` (the harness-designated
branch; based on `Shopify-connector` @ `6d32412`, the merged **PR #55** MVP-scope baseline).
**Branch-name note for ChatGPT (flagged):** the Sprint C2 prompt named
`research/sprint-c2-teqstars-rebaseline`, but the session's hard git rule designated the
harness branch `claude/teqstars-evidence-rebaseline-2nppgq` ("never push to a different
branch without explicit permission"), so work proceeded on the harness-designated branch;
**the PR targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `0aad508` | docs: start teqstars rebaseline correction |
| `f969df8` | docs: update teqstars competitor evidence |
| `5f49395` | docs: align research synthesis with teqstars evidence |
| _(this commit)_ | docs: finalize teqstars rebaseline handoff |

## High-power research mode used

**Yes — focused and scoped to TeqStars only** (per the prompt's token-control instruction:
"focused high-power research only where useful for TeqStars documentation review; do not
crawl unrelated competitors"). **Plan (documented before launch, `CLAUDE.md` high-power
section):** (a) **Why:** 31 TeqStars doc pages + ~33 required evidence checks had to be read
and classified from real primary-source evidence with over-upgrade the named hazard.
(b) **Capture:** the worker fetched all 31 pages (browser-UA curl → HTML→text) and read them
in full — capture stayed worker-owned so claim classification is centrally governed.
(c) **Verify:** a compact `parallel()` workflow of **17 adversarial verifiers** (one per
high-stakes/contested classification) re-read the local primary-source text and tried to
**downgrade** each proposed symbol (default to the more conservative symbol when uncertain).
(d) **Sources:** only `docs.teqstars.com/19.0/applications/shopify/*` (no other competitors).
(e) **Stop condition:** all 31 pages classified + high-stakes items verified + allowed docs
updated + handoff/QA updated. (f) **Unsupported-claim prevention:** strict claim symbols;
a comparison-table checkmark or marketing sentence is **not** demonstrated; the Sprint C
idempotency search-snippet stayed **unverified**. **Result:** 17/17 verified; **3 downgrades**
(auto-retry, cross-object reconciliation, metrics dashboard → ⬜); all other upgrades
confirmed by verbatim quote. **Reuses the DP-003 capture→verify discipline.**

## Source status correction (audit trail preserved)

- **Previous Sprint C status (2026-06-30):** TeqStars **docs 403-blocked** (whole
  `docs.teqstars.com` host, 19.0 + 16.0); deep dive was **Apps-listing claim-only**.
  **Retained as history** in `../00-source-materials/competitor-source-notes.md` (R2
  "Sprint C historical" subsections), `resource-inventory.md`, and the screenshot inventory.
- **Current re-check (2026-07-01):** **Accessible** — the 31 pages return **HTTP 200** with a
  browser UA (the proxy fetcher's default UA is still 403-filtered — a WAF/bot UA sniff,
  **not** a login wall; **no auth bypassed; public content**). This satisfies the Sprint C
  unblock path ("a browser-UA fetch of the 19.0 docs — no auth to bypass").
- **Framing:** a **source-availability correction**, **not** a criticism of Sprint C (whose
  refusal to treat blocked content as fact was correct). The historical **Blocked** fact and
  the 2026-06-30 Apps-listing facts are **not** erased.

## Files created or updated

**Source materials (`docs/00-source-materials/`)** — `competitor-source-notes.md`
(R2 restructured: Sprint C historical + Sprint C2 accessible subsections + verbatim quotes),
`competitor-screenshot-inventory.md` (TeqStars real per-page screenshot inventory; no
binaries saved; Sprint C captions retained as history).

**Research (`docs/01-research/`)** — `resource-inventory.md` (Sprint C2 access-change
section), `competitor-deep-dives.md` (TeqStars section rebuilt + cross-competitor row +
headline inference), `competitor-feature-matrix.md` (TQ column rebaselined + caveats),
`ux-ui-benchmark.md`, `common-patterns.md`, `best-in-class-observations.md`,
`gaps-opportunities.md`, `avoid-list.md` (synthesis aligned where TQ materially changes
conclusions), `research-handoff.md` (this file).

**Product (`docs/02-product/`)** — `mvp-scope.md` (Sprint C2 reinforcing evidence note),
`product-research-handoff.md` (Sprint C2 note). **No DEC-003 change; no scope change.**

**QA (`docs/05-qa/`)** — `defect-pattern-log.md` (Sprint C2 source-availability note; no new
row, no counter change), `architecture-review-log.md` (Sprint C2 non-decision note; all AR
rows stay Not decided).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker; no
`addons/**`; no `docs/03|04|07|08`; no `.claude/**`). **DEC-003 not modified.**

## Key evidence corrections (page-classified)

- **Now demonstrated (✅):** store connection + OAuth custom-app + **Test Connection**;
  instance configuration (tabbed, toggle-dense); **product import/export/update**;
  **product matching** ("Sync Listings Based On" = SKU/Barcode/both); **duplicate
  prevention** (customer multi-field dedup + Create-Odoo guard + webhook link-existing +
  Skip-Sync); Listing/Listing-Item binding; **product webhooks create/update/delete**
  (fast-ack background thread); image sync; price import/export; inventory import/export;
  **multi-location** (combine + third-party exclusion); customer import + address;
  orders + workflow + **click&collect**; refunds; cancellations; **returns** (webhook
  lifecycle + Force-Restock); mark-as-paid; **payouts** (Shopify-Payments-only);
  metafields (Product/Variant bidirectional; Customer/Order import-only); collections;
  **catalogs/Markets/B2B pricing**; queue + typed logs + activity-on-failure;
  **controlled, draft-safe product export** (channels-optional = unpublished).
- **Vendor claim only (🟨):** pHash image dedup (comparison-table + `imagehash`/`PyWavelets`
  dependency; no workflow); "Centralized hub"/Reporting-Analytics (no metrics dashboard);
  GraphQL wire behaviour (doc-stated, not independently verified).
- **Implied (➖):** idempotency (adjacent guards only — no explicit `@idempotent`);
  permissions/security (scopes + access-rights mentioned; no role/record-rule model).
- **Not found (⬜):** **customer export** (import-only), **HMAC/webhook signature**,
  **rate-limit/GraphQL-cost throttling**, **automatic-retry/backoff taxonomy**, **first-class
  cross-object reconciliation**, **metrics/chart dashboard**, **multi-company** (vs
  multi-store). *(The Sprint C idempotency search-snippet stays unverified.)*

## Evidence discipline

**No over-upgrade.** Breadth is now demonstrated, but **reliability depth is scored
separately** and kept conservative: the 3 verifier downgrades (auto-retry, cross-object
reconciliation, dashboard) were honored; pHash and GraphQL-wire stayed claims; idempotency
stayed implied; rate-limit/HMAC/customer-export/multi-company stayed not-found. A page title
or a comparison-table checkmark was **never** treated as a demonstrated workflow (DP-003/
DP-004). The **whitespace claims are reinforced, not closed**: TeqStars **confirms** the
idempotency + reconciliation + automatic-retry + rate-limit gaps; it **narrows only the
payout-reconciliation** add-on (EM + TQ, both Shopify-Payments-only).

## Product impact (reinforces the accepted baseline; no scope change)

TeqStars now **demonstrates** the accepted **controlled product import/export/update** MVP
baseline (match key + create-guard + draft-safe export + publish/unpublish + per-listing
sync toggle) and **corroborates "customer export = later"** (no customer export; import-only).
**DEC-003 unchanged; MVP scope unchanged; customer export not moved into MVP.** No serious
contradiction to DEC-003 was found → **no open review note for ChatGPT required.**

## Architecture inputs, not decisions

The rebaseline adds **competitor inputs** to AR-002 (GraphQL doc-stated; controlled draft-safe
export pattern; `productSet`/REST-vs-GraphQL still open), AR-003 (webhooks + scheduled + manual
+ **cron-processed per-op queues** — a data point alongside VT's `queue_job`; framework open),
AR-005 (Listing/Listing-Item binding + SKU/Barcode match keys + create-guard; data model open),
AR-006 (adjacent guards only — reinforces the idempotency/retry/reconciliation/throttle
whitespace), AR-007 (multi-location + quantity-field choice + controlled apply), AR-008
(Update-in-Marketplace + tracking + click&collect). **No AR row is decided** — see the Sprint
C2 non-decision note in `../05-qa/architecture-review-log.md`.

## Open questions

Is TeqStars' **pHash** dedup real at runtime (dependency declared, no workflow)? Does any
**`@idempotent`-style directive** exist in code (not on the docs)? Is there a **monitoring
dashboard** beyond the Operations launcher (none documented)? **Multi-company** vs
multi-store? **HMAC / webhook-signature** verification (HTTPS only)? How are **rate limits**
handled at scale (no throttle documented)? (Unchanged field-wide whitespace: how competitors
surface rate-limit + first-class reconciliation to users — still none, TeqStars included.)

## Learning feedback loop

- **New issues discovered:** none. **No new defect pattern**; **no new DP row; no counter
  change.** Sprint C2 is a **source-availability correction**, logged as a note in
  `../05-qa/defect-pattern-log.md`.
- **Repeated issue patterns:** none at threshold. The **DP-003 capture→verify discipline was
  applied** to the new evidence (17-item adversarial pass → 3 downgrades), and **DP-004** (a
  config field / comparison checkmark ≠ demonstrated support) was **applied, not
  re-triggered** — no capability was over-upgraded.
- **Rules/checklists updated:** reinforced (not new) the standing rule that **an important
  source recorded Blocked must be re-checked before a final scope/architecture decision
  leans on it** — access can change (WAF/bot rules, vendor doc releases). Refines DP-001
  (re-read the source) and DP-003 (blocked-source handling); noted in the defect log and the
  resource inventory. The **browser-UA fetch** is now the recorded unblock method for
  UA-filtered (non-auth) docs.
- **New rejected approaches:** none (research-only).
- **New technical debt:** none (no code).
- **Architecture concerns:** TeqStars now **informs** AR-002…AR-008 (non-decision note in
  `architecture-review-log.md`); **all rows stay Not decided / Evidence pending.**
- **Tests or review gates needed:** none active (research). The DP-006 evidence-consistency
  gate remains the standing pre-MVP/architecture review gate.
- **Should future prompts change? Minor:** competitor-research prompts should state that a
  **UA/bot 403 is not an auth wall** and a **browser-UA re-fetch** is the correct,
  non-bypassing unblock for such sources; and that **blocked/weak sources important to a
  decision should be re-checked before that decision is finalized** (now encoded in the
  defect log + resource inventory + avoid-list). Branch reality remains the harness
  `claude/...` branch while the PR targets `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; handoffs +
  learning loop updated; evidence page-classified and adversarially verified; DEC-003 and
  MVP scope unchanged; no architecture decided.

## What ChatGPT should review

1. **TeqStars is no longer globally blocked/claim-only** — the source-status correction is
   a source-availability change with the Sprint C blocked record preserved as audit trail.
2. **Evidence upgrades are justified by accessible page-level workflows/screenshots** — spot
   check the verbatim quotes in `competitor-source-notes.md` (R2 Sprint C2).
3. **Capabilities are not over-upgraded** — the 3 verifier downgrades (auto-retry,
   reconciliation, dashboard → ⬜) and the kept 🟨/➖/⬜ items (pHash, idempotency, HMAC,
   rate-limit, customer export, multi-company).
4. **MVP scope and DEC-003 remain unchanged** (product docs carry a reinforcing note only).
5. **No architecture row is decided** (Sprint C2 non-decision note; all AR rows Not decided).

## Recommended next session

Return to the gated **RB-14 architecture preparation** (AR-002 distribution/API, AR-003
orchestration/queue, AR-005 binding/dedup) with the TeqStars evidence now firmed up. Keep the
no-code gate; one scoped objective per session; **do not start RB-14 in this sprint.**

### Exact next-session prompt

> **Research Sprint (RB-14 framing — Part 1): Architecture decision framing and
> official-source refresh — DO NOT DECIDE.** Read `CLAUDE.md`, the latest
> `docs/01-research/research-handoff.md` (Sprint C2), and
> `docs/05-qa/architecture-review-log.md`. Confirm the no-code gate and that all AR rows are
> "Not decided / Evidence pending." Frame — **without deciding** — the evidence still needed
> to resolve **AR-002** (distribution/API strategy), **AR-003** (sync orchestration/queue),
> and **AR-005** (binding/dedup model), citing Tier-1 Shopify/Odoo facts and the now-complete
> competitor evidence (incl. the TeqStars Sprint C2 rebaseline). Allowed files:
> `docs/03-architecture/**` (framing docs only, if the folder is authorised) **or**
> `docs/01-research/**` synthesis + `docs/05-qa/architecture-review-log.md` if not; update the
> handoff. **Do not** write code, create modules, decide REST/GraphQL/queue/data-model/
> distribution, or open a PR into `main`/`dev`. Branch from `Shopify-connector`; PR into
> `Shopify-connector`. Stop after framing + handoff and await ChatGPT review.

## Stop confirmation

Stopped at the Sprint C2 boundary: four stage commits on the harness-designated branch + one
draft PR targeting **`Shopify-connector`**, **not merged**. **No** connector code, Odoo
module, architecture decision, architecture doc/ADR, implementation plan, module boundary, or
REST/GraphQL/queue-framework/data-model/distribution choice. **DEC-003 and MVP scope
unchanged.** `main` and plain `dev` untouched; only Sprint C2 allowed files changed. Awaiting
ChatGPT review.

## Quality gate confirmation (Sprint C2)

- [x] Session handoff updated (this block + product-research-handoff.md Sprint C2 note).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (source-availability note in
  `defect-pattern-log.md`; no new DP row / counter change).
- [x] Any rejected approach logged (none — research-only).
- [x] Any accepted technical debt logged (none — no code).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-003/DP-004 applied,
  not re-triggered; 3 over-upgrades caught and downgraded).

---

# Product Sprint G Handoff

> **Product Sprint G — MVP Scope Acceptance and Decision Baseline.** Records ChatGPT's
> accepted **RB-13 MVP scope** in GitHub and aligns the product documents to that accepted
> baseline. **Documentation/decision-recording sprint only** — no new sources, no research
> agents, no architecture. **No-code gate in force** (`CLAUDE.md` §4–§5). Maps to backlog
> item **RB-13 (MVP scope — now accepted as product scope)**, feeding RB-14 (architecture
> prep) — still gated. Session date 2026-07-01.

## Sprint G revision (PR #55 review — 2026-07-01)

ChatGPT reviewed PR #55 and returned **REVISE** — the first draft **over-deferred product
export**. Corrected on the same branch (`docs: revise mvp baseline for controlled product
export`), a **product-scope correction only** (no architecture, no code):

- **Controlled product export/update is now IN MVP** (Shopify→Odoo import **and**
  Odoo→Shopify export/update, with matching, binding, preview/dry-run, duplicate
  prevention, and draft/unpublished/channel-controlled safety) — **controlled bidirectional
  product onboarding**, not import-first.
- **Full autonomous bidirectional catalog management remains later**; **customer export
  remains later.**
- **Evidence:** product import/export/update is **market-baseline** (EM/VT/WK/SH
  demonstrated). **TeqStars docs** (403-blocked in Sprint C on 2026-06-30) were **re-checked
  by ChatGPT on 2026-07-01 and found accessible**; a **full TeqStars rebaseline is pending a
  later research sprint** and was **not** done here.
- **No architecture finalized; no implementation authorized.** Binding/data model → AR-005;
  API/destructive-apply → AR-002.

*(The Session summary and sections below were authored for the initial Sprint G recording;
apply the correction above — "import-first" is superseded by "controlled bidirectional
product onboarding," and product export is in MVP.)*

## Session summary

Recorded ChatGPT's RB-13 MVP scope decisions as the accepted baseline. Created
**`docs/04-decisions/DEC-003-mvp-scope.md`** (accepted MVP **product-scope** decision:
Option A correctness-core **with controlled bidirectional product onboarding**; product
import **and** controlled export/update + write-back direction; Domain 9
minimal-financial-evidence-only; refunds/cancellations deferred; bulk ops not user-facing;
single-store/single-company; P1-primary/P2-secondary; explicit "no architecture decided /
implementation blocked"). Aligned `mvp-scope.md`, `non-mvp-and-later-phases.md`, and
`user-stories.md` to the accepted baseline (former `open` forks resolved; deferrals with
revisit conditions; persona priority set). Updated both handoffs; applied the **DP-006
evidence-consistency gate**; added non-decision notes to the QA logs. **No connector code,
no Odoo module, no architecture doc/ADR, no implementation plan, no module boundary, no
REST/GraphQL/queue-framework/data-model/distribution decision** was produced.

## Files created or updated

- `docs/04-decisions/DEC-003-mvp-scope.md` (**new**).
- `docs/02-product/mvp-scope.md`, `docs/02-product/non-mvp-and-later-phases.md`,
  `docs/02-product/user-stories.md` (**updated** — aligned to accepted scope).
- `docs/02-product/product-research-handoff.md`, `docs/01-research/research-handoff.md`
  (**updated** — Sprint G sections + checkpoints).
- QA logs (non-decision notes only): `docs/05-qa/defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`, `technical-debt-register.md`.

## MVP acceptance summary

Accepted **Option A** — a correct, observable, recoverable **single-store** sync loop
across the core commerce objects with **controlled bidirectional product onboarding**
(product import **and** controlled export/update), plus **inventory + fulfilment/tracking
write-back**. **Not** unrestricted autonomous bidirectional catalog ownership.
Product-scope acceptance only; every *mechanism* stays gated (RB-14).

## Accepted MVP decisions

- **Direction:** Shopify→Odoo import (products, variants/options, basic images, base
  price/compare-at, customers + matching, orders, order status/lifecycle); **Odoo→Shopify
  controlled product export/update** (matched, bound, previewed, draft/channel-safe);
  Odoo→Shopify write-back (inventory multi-location-aware/idempotent; fulfilment +
  tracking). **Deferred:** customer export; unrestricted autonomous bidirectional catalog
  ownership.
- **Domain 9:** minimal financial **evidence** only (status/labels/references/flags-as-
  source-info/totals/tax/shipping/discount/currency + basic gateway-journal mapping as
  config input) — **no accounting automation.**
- **Inventory:** write-back in MVP; multi-location-aware; **never `committed`**; allowed
  quantity fields only; controlled initial-stock import; **auto-apply not default
  (AR-007).**
- **Reliability spine:** layered sync (webhooks + scheduled + manual + reconciliation);
  HMAC; webhook-ID dedup; fast ack; idempotency; duplicate prevention; per-record
  isolation; reason-coded logs; safe manual retry; retry classification concept; rate-limit
  awareness; resumable jobs; honest freshness.
- **UX:** guided setup; credential masking; test connection; readiness/self-test; basic
  command center; recovery-first error center (MVP); enqueue quick actions; essential
  mappings only; admin/functional roles; open docs + dated changelog + self-test.
- **Store/company:** single-store, single-company; architecture-safe keys.
- **Persona:** P1 primary; P2 secondary; P3/P4 important buyer/deployer personas.

## Deferred scope

**Unrestricted autonomous bidirectional catalog ownership** (all-field two-way conflict
resolution; field-ownership matrix; advanced publish/channel campaign management);
**customer export**; refund sync; cancellation reflection; returns/RMA; full Domain 9
accounting automation; payout/bank reconciliation; multi-package fulfilment; complex tax;
Markets/B2B/POS/gift cards/metafields/subscriptions/abandoned-checkout/recommendations/
Buy-with-Prime;
multi-store/multi-company logic; custom transforms; advanced analytics; public App-Store +
demo packaging + billing/compliance webhooks. **Bulk Operations = not a user-facing MVP
feature** (internal RB-14/AR-002 assessment only). *(**Controlled** product export/update —
matched, bound, previewed, draft/channel-safe — **is in MVP**, not deferred.)* Revisit
conditions in `non-mvp-and-later-phases.md`. **Mandatory future rule:** idempotent-refund /
no-double-refund regression is mandatory if refunds are later included.

## Architecture dependencies still open

AR-002…AR-008 all **Not decided / Evidence pending** (distribution/API + **destructive-apply
(`productSet`) mechanics** for controlled export + internal bulk; orchestration/queue +
Odoo-Online; module boundaries/config; binding/dedup data model + **product match keys
(SKU/barcode) + first-sync source strategy**; error/retry taxonomy + idempotency mechanism +
reconciliation cadence; inventory design + apply mode; fulfilment design). Also **later &
architecture-gated:** full autonomous bidirectional catalog management (all-field two-way
conflict resolution + field-ownership matrix). Plus the **Domain 9 draft-artifact exception**
(returns to ChatGPT if RB-14 finds a draft invoice/payment artifact is required). **DEC-003
feeds these; it decides none.**

## Evidence-consistency gate

**DP-006 gate applied; none discovered.** No claim→fact promotion; weak/claim-only evidence
stayed out of scope; WK Company field stayed a config field (DP-004); auto-apply stayed an
[Inference] → AR-007 (DP-006); "real-time" never asserted; scope acceptance kept separate
from any mechanism decision. **No new DP row; no counter change.**

## No-code / no-architecture confirmation

No connector code; no Odoo module; no `*.py`/`*.xml`/`*.csv`/manifest/controller/security/
data/migration/test files; no CI/Docker; no architecture doc; no architecture ADR; no
implementation-plan doc; no module boundary; no REST/GraphQL/queue-framework/data-model/
distribution decision. Only allowed docs changed. **Implementation remains blocked.**

## Branch reality

Prompt requested `product/sprint-g-mvp-acceptance`; the harness designated
`claude/sprint-g-mvp-scope-jxisgm`, and the session's hard git rule requires working on the
harness-designated branch ("never push to a different branch without explicit permission").
Work proceeds on `claude/sprint-g-mvp-scope-jxisgm`; **the PR still targets
`Shopify-connector`**; `main` and plain `dev` untouched.

## Recommended next sprint

**RB-14 Architecture Preparation — Part 1: Architecture decision framing and
official-source refresh**, starting with **AR-002** (distribution/API strategy), **AR-003**
(sync orchestration/queue), and **AR-005** (binding/dedup model). Keep the no-code gate;
one scoped objective per session. **Do not start RB-14 in this sprint.**

## Stop confirmation

Stopped at the Sprint G boundary. **No** connector code, Odoo module, architecture
decision, architecture doc/ADR, implementation plan, module boundary, or
REST/GraphQL/queue-framework/data-model/distribution choice. MVP **product scope accepted**
(DEC-003); architecture gated; implementation blocked. `main` and plain `dev` untouched;
only Sprint G allowed files changed. Awaiting ChatGPT review.

---

# Product Sprint F Handoff

> **Product Sprint F — MVP Scope Proposal, Non-MVP Boundaries, and User Stories.**
> MVP-proposal synthesis only; **no-code gate in force** (`CLAUDE.md` §4–§5). High-power
> mode **not required** (focused MVP synthesis of already-merged repo evidence — no new
> competitor crawling, no research fan-out). Maps to backlog item **RB-13 (MVP scope
> implications — not finalized)**, feeding RB-14 (architecture prep) — all gated.

## Sprint F revision (PR #54 review — 2026-07-01)

ChatGPT review returned **REVISE** — a small consistency patch (no new research, no scope
change). Corrected on the same branch (`docs: clarify refund acceptance principle in
sprint f`):

- **Refund sync remains open / lean defer** (C-RET-01, US-E4-06) — **not** turned into
  MVP.
- The **MVP acceptance principles** (`mvp-scope.md`) and the user-stories acceptance
  principles now clarify that the **idempotent-refund / no-double-refund regression
  scenario (A-IMP-4) applies only if refund handling is included in MVP; if refunds are
  deferred, it is carried forward as a mandatory acceptance principle for the first
  refund/refund-sync sprint** (never dropped).
- **No MVP scope finalized; no architecture decision made.** Consistency correction only
  (Sprint F revision note added to `../05-qa/defect-pattern-log.md`; not a new defect
  occurrence, no counter change). MVP remains **proposed, not final**.

## Session summary

Produced the **evidence-based MVP scope proposal**: `docs/02-product/mvp-scope.md` (main
deliverable), `docs/02-product/non-mvp-and-later-phases.md` (strict boundaries), and
`docs/02-product/user-stories.md` (10 MVP epics + 6 later-phase epics), consuming the
Sprint D taxonomy/evidence map and the Sprint E vision + setup/UX principles. Recommends
**Option A — "correctness core, import-first"**: a **single-store** connector that
imports products (variants + basic images + base price), customers (deduped), and orders
(basic lifecycle + minimal payment/journal representation), and writes back inventory
(multi-location-aware, idempotent) and fulfilment/tracking — on a full correctness engine
(layered webhooks + scheduled + first-class reconciliation + manual; idempotency; GID↔Odoo
binding + documented dedup keys; per-record isolation; retry classification with safe
manual retry; rate-limit awareness; resumable jobs) — with an operator experience
(guided setup + readiness self-test; command center; recovery-first error center; honest
freshness), role-based access, and open docs. Excludes/defers export, refunds/returns
lifecycle, payouts, Markets/B2B/POS/gift cards/metafields, multi-store & multi-company,
pricelists/per-market, custom transforms, bulk-ops-as-a-feature, and advanced analytics.
The **DP-006 evidence-consistency gate** (8 checks) was applied to every capability.
**No connector code, no Odoo module, no MVP finalization, no architecture decisions, no
ADRs, no implementation plan, no module boundaries, no queue/API/distribution/data-model
choices.** Synthesis was **worker-owned** (no fan-out).

## Branch and commits

**Working branch:** `claude/mvp-scope-user-stories-dms7s8` (the harness-designated
branch; based on `Shopify-connector` @ `6e73f82`, the merged **PR #53** Sprint E
baseline). **Branch-name note for ChatGPT (flagged):** the Sprint F prompt body named
`product/sprint-f-mvp-scope-proposal`, but the session's hard git rule designated the
harness branch `claude/mvp-scope-user-stories-dms7s8` ("never push to a different branch
without explicit permission"), so work proceeded on the harness-designated branch; **the
PR still targets `Shopify-connector`**; `main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `880dda8` | docs: start sprint f mvp scope proposal |
| `1dbea92` | docs: add mvp scope proposal |
| `103a638` | docs: add non-mvp and later-phase boundaries |
| `fd4d131` | docs: add mvp user stories |
| _(this commit)_ | docs: finalize sprint f mvp handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `mvp-scope.md` (new — main deliverable), `non-mvp-and-later-phases.md` (new),
  `user-stories.md` (new), `product-research-handoff.md` (updated — Sprint F section).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint F section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — Sprint F note: DP-006 gate applied, not
  re-triggered; no new occurrence), `architecture-review-log.md` (updated — Sprint F
  non-decision note), `rejected-approaches-log.md` (updated — nothing rejected),
  `technical-debt-register.md` (updated — no debt).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/Docker;
no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## MVP proposal summary

- **Thesis:** *small but excellent = a correct, observable, recoverable single-store
  sync loop across the core objects — proven, not just claimed — wrapped in an operator
  experience a non-developer can run.* Win on demonstrated correctness + operator
  experience at the demonstrated object baseline for one store.
- **Recommended option:** Option A (correctness core, import-first), over Option B
  (bidirectional catalog — doubles complexity, forces destructive-apply safety +
  AR-002/005 early) and Option C (thin import-only pilot — violates correctness
  non-negotiables; small but not excellent).

## Recommended MVP scope

**Proposed for ChatGPT review — not final until accepted.** Store connection + creds +
guided setup + test-connection + readiness self-test (C-CONN-01…06, C-FUL-03);
product/variant/basic-image/base-price import + exclude-from-sync (C-PROD-01/04,
C-VAR-01/02, C-PRICE-01); customer import + multi-key matching + basic address
(C-CUST-01/03/04); order import + backfill (60-day gate) + status map + basic workflow
(C-ORD-01…04); inventory write-back (multi-location-aware, idempotent) + quantity default
+ controlled stock import (C-INV-01…04); fulfilment + tracking write-back (C-FUL-01/03);
layered sync + reconciliation + HMAC + id-dedup + freshness (C-SYNC-01…07); queue/job +
retry classification + safe retry + idempotency + rate-limit + resumable (C-JOB-01…05/07);
reason-coded logs + audit + recovery-first error center + notifications (C-OBS-01…04);
command center (C-DASH-01…06); essential mappings + binding/dedup keys + routing
(C-MAP-01…04); role-based access + multi-store-safe keys (C-MULTI-03, C-MULTI-01); open
docs + changelog + self-test (C-DOCS-01…03). **Open (ChatGPT direction call):**
product/customer export (C-PROD-02/05, C-CUST-02), Domain 9 minimum (C-PAY-01/02/03),
refunds/cancellations (C-RET-01/03), bulk ops (C-JOB-06).

## Recommended exclusions

Advanced refunds/returns lifecycle (C-RET-02), payouts (C-POUT-01/02), Markets/B2B/POS/
gift cards/metafields/extended (C-ADV-01…06), multi-company (C-MULTI-02), full multi-store
(C-MULTI-01), pricelists/per-market (C-PRICE-02/03), SEO/taxonomy + BoM/kit (C-VAR-03/04),
order risk (C-ORD-05), multi-package fulfilment (C-FUL-02), custom transforms (within
C-MAP-03), dedicated analytics/financial reporting (C-RPT-01/02), App-Store/Built-for-
Shopify + public demo packaging (C-DOCS-04; within C-DOCS-03 — distribution-gated).

## User story summary

10 MVP epics (store setup & readiness; product/catalog; customer import & matching; order
import & lifecycle; inventory & freshness; fulfilment & tracking; logs/errors/retries/
recovery; command center; mapping & configuration; permissions & roles) — persona-driven
(P1–P4), testable, product-level, each traced to capability IDs + evidence + AR gate —
plus 6 later-phase epics (bidirectional; financial depth; payouts; premium breadth;
multi-tenancy; scale & analytics). **Stories are not implementation tasks.**

## Evidence discipline

The **DP-006 evidence-consistency gate** was **applied, not re-triggered** (8 checks in
`mvp-scope.md`). Tier-1 facts labelled **[Fact]**; EM/VT-demonstrated weighted over
SH/WK/EC/TQ claims; competitor-claim-only items kept out or flagged (pHash image dedup,
TQ breadth); improvement opportunities labelled **[Inference]** (command center, error
center, freshness, empty states, **auto-apply C-INV-04 → AR-007, not decided**);
conditional items kept conditional (OAuth/distribution/queue/binding/taxonomy/inventory/
fulfilment/module-boundaries); WK multi-company stays a config field (➖, DP-004), WK
import-stock stays ⬜; "real-time" never asserted (C-SYNC-07 honesty). No claim was
promoted to a fact; no capability entered MVP as a decision; no weak evidence became
scope.

## MVP inputs, not final decisions

The scope, options, include/exclude/defer/open calls, MVP-critical spine, and acceptance
principles are **inputs for RB-13 acceptance**, not commitments. Every inclusion is
marked **"Proposed MVP inclusion — pending ChatGPT acceptance."** Documents are
banner-marked **proposed, not final**.

## Architecture inputs, not decisions

MVP commits **requirements/intent**, never mechanism. Architecture-dependent items map to
**AR-002…AR-008** (all Not decided / Evidence pending): AR-002 (distribution/API/bulk/
App-Store), AR-003 (orchestration/queue framework), AR-004 (module boundaries/config
model/feature flags), AR-005 (binding/dedup data model/keys), AR-006 (error-retry
taxonomy/idempotency/reconciliation cadence), AR-007 (inventory/apply mode), AR-008
(fulfilment). **No AR row is decided, proposed for active review, or re-litigated** —
logged as a Sprint F non-decision note in `architecture-review-log.md`.

## Open questions

Primary MVP persona (P1 vs P2); **direction** (export in MVP or Phase 2); **Domain 9
minimum**; **refunds/cancellations** (basic idempotent or deferred); **distribution
(AR-002)**; single- vs multi-store/company at MVP (proposed single-store, multi-store-safe
keys); reconciliation cadence + freshness granularity (AR-003/006); error/retry taxonomy
depth + auto-retry set (AR-006); essential mappings + dedup/match keys (AR-005); bulk-ops
need (C-JOB-06); readiness/self-test check set; Odoo edition/hosting (Odoo Online?
edition-gated report disclosure).

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**: no competitor claim promoted to a fact, no capability entered MVP as a
  decision, weak/claim-only evidence kept out of scope, no architecture finalized.
  DP-003/DP-004/DP-005 applied throughout.
- **Repeated issue patterns:** none at threshold (no new occurrence added to any
  category).
- **Rules/checklists updated:** none required — existing rules sufficed and were applied.
  QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none — MVP exclusions are recommendations-against-MVP,
  **not** rejected architecture approaches (`CLAUDE.md` §10).
- **New technical debt:** none (no code).
- **Architecture concerns:** MVP proposal supplies capability-scope inputs to
  AR-002…AR-008 — non-decision note; all rows stay Not decided / Evidence pending.
- **Tests or review gates needed:** none active. The DP-006 gate remains the standing
  pre-MVP/architecture review gate; MVP acceptance principles reference the seeded
  regression scenarios (A-IMP-4).
- **Should future prompts change? No** (beyond Sprints D/E) — MVP-synthesis prompts
  should keep every scope call an **input** (MVP=RB-13 / architecture=RB-14 gated), keep
  synthesis worker-owned, keep conditional items conditional (DP-006), and keep
  exclusions as recommendations-against-MVP. Branch reality remains the harness `claude/…`
  branch while the PR targets `Shopify-connector`.
- **Quality gate:** satisfied — allowed-files-only; no forbidden files; handoffs +
  learning loop updated; DP-006 gate applied; MVP marked proposed-not-final.

## What ChatGPT should review

1. **Thesis & option choice** — is Option A right over B and C?
2. **Evidence-consistency gate (DP-006)** — 8-check review holds; nothing weak became
   scope; auto-apply (C-INV-04) stays inference.
3. **Include/exclude/defer/open** — especially the open direction forks (export, Domain 9
   minimum, refunds/cancellations, bulk ops).
4. **Architecture-dependent table** — MVP commits intent only; no AR row decided.
5. **MVP-critical spine + acceptance principles** — endorse/amend.
6. **Boundaries & stories** — boundaries strict enough; stories not implementation tasks.

## Recommended next session

Await ChatGPT's **RB-13 MVP acceptance/revision**. On acceptance, **RB-14 (architecture
preparation)** against AR-002…AR-008 — starting with **distribution (AR-002)** (unblocks
OAuth/GraphQL/App-Store), then **orchestration/queue (AR-003)** and **binding/dedup model
(AR-005)** that the correctness core depends on — all gated and ChatGPT-reviewed.
Optionally firm up weak/blocked evidence (TQ 403; EC/R5; 17 unread VT Confluence). Keep
the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint F boundary as instructed. **No** connector code, **no** Odoo
module, **no** MVP finalization, **no** architecture decisions, **no** ADRs, **no**
implementation plan, **no** module boundaries, **no** REST/GraphQL/queue-framework/
distribution/data-model choices. MVP scope marked **proposed, not final**. `main` and
plain `dev` untouched; only the Sprint F allowed files changed. Awaiting ChatGPT review.

---

# Product Sprint E Handoff

> **Product Sprint E — Product Vision, Quality Bar, UX Principles, and
> Differentiation Strategy.** Product strategy / synthesis only; **no-code gate in
> force** (`CLAUDE.md` §4–§5). High-power mode **not required** (synthesis of
> already-merged repo evidence — no new competitor crawling, no research fan-out).
> Maps to backlog item **RB-11 (product vision draft)**, feeding RB-13 (MVP
> implications) and RB-14 (architecture prep) — all gated.

## Session summary

Created the **product vision** (`docs/02-product/product-vision.md`) and the
**setup/UX principles** (`docs/02-product/setup-ux-principles.md`) for the Odoo 19 ↔
Shopify Connector, consuming the Sprint C research baseline and the Sprint D
canonical feature taxonomy + capability evidence map. The vision positions the
connector as **correctness-first, UX-first, recovery-first, observable, honest,
modular/customizable, performance-aware, evidence-based, upgrade-safe, and premium
but not bloated** (simple for normal users, powerful for advanced users). It states
the product thesis, target personas (inference-level P1–P4), core customer problems,
ten product principles, a premium quality bar, a five-theme differentiation strategy,
per-domain strategies (UX / reliability / modularity / performance / security /
docs-trust), seven product non-negotiables, and explicit **MVP / later / architecture
inputs (not decisions)**. The UX doc defines a UX north star and 12 principles plus
per-area principle sets. **No connector code, no Odoo module, no MVP finalization, no
architecture decisions, no ADRs, no implementation plan, and no module boundaries**
were produced. Synthesis was **worker-owned** (no fan-out).

## Branch and commits

**Working branch:** `claude/sprint-e-product-strategy-gd2kfs` (the harness-designated
branch; based on `Shopify-connector` @ `9a744f7`, the merged **PR #52** Sprint D
baseline). **Branch-name note for ChatGPT (flagged):** the Sprint E prompt body named
`product/sprint-e-product-vision-quality-bar`, but the session's hard git rule
designated `claude/sprint-e-product-strategy-gd2kfs` ("never push to a different
branch without explicit permission"), so work proceeded on the harness-designated
branch; **the PR still targets `Shopify-connector`**; `main` and plain `dev`
untouched.

| Hash | Message |
| --- | --- |
| `ce36ffc` | docs: start sprint e product vision |
| `d3da053` | docs: add product vision |
| `5561db3` | docs: add setup ux principles |
| _(this commit)_ | docs: finalize sprint e product handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `product-vision.md` (new — main deliverable), `setup-ux-principles.md` (new),
  `product-research-handoff.md` (updated — Sprint E section).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint E section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — Sprint E note: DP-006 gate applied, not
  re-triggered; no new occurrence), `architecture-review-log.md` (updated — Sprint E
  non-decision note), `rejected-approaches-log.md` (updated — nothing rejected),
  `technical-debt-register.md` (updated — no debt).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## Product vision summary

- **What:** a best-in-class, modular, reliable Odoo 19 ↔ Shopify connector — a
  correct, observable sync core wrapped in an operator experience, delivered as an
  isolated, upgrade-safe addon family.
- **Positioning:** *correct by design, honest by default — and can prove both to the
  operator.*
- **Thesis:** breadth is table stakes; win on **demonstrated correctness** and the
  **operator experience**, ship the demonstrated breadth as a clean baseline, and
  offer premium breadth as **optional add-ons** on an honest, modular core.
- **Premium quality bar** = correctness / experience / trust, **not** feature count;
  seven **non-negotiables** form the quality contract.
- **Differentiation (inputs):** (1) demonstrated correctness (idempotency +
  reconciliation + rate-limit awareness), (2) command center + recovery-first errors
  together, (3) easy onboarding with real reliability, (4) honesty/transparency, (5)
  premium breadth as clean add-ons.

## UX principles summary

- **North star:** the operator always knows *is everything OK / what failed and why /
  what do I do next* and can act without reading source or filing a ticket.
- **12 principles:** guided setup; prove readiness before sync; progressive
  disclosure; honest status & freshness; command center over scattered menus;
  recovery-first errors; safe-by-default actions; human-readable logs; guided
  mappings; role-aware UX; modular feature visibility; documentation mirrors the
  product — plus per-area principle sets. **No screens or menus are designed.**

## Evidence discipline

- **DP-003 applied:** competitor UX/product statements stay claims; TQ (docs 403) and
  EC (no screenshots) stay claim-only/weak; SH ✅ rest on captions; EM/VT-demonstrated
  evidence is weighted highest.
- **DP-004 applied:** WK multi-company kept **config-field-only (➖)**; market promises
  not treated as demonstrated bidirectionality.
- **DP-005 applied:** every principle/candidate is an **input**, not a decision;
  MVP=RB-13 and architecture=RB-14/AR-002…AR-008 stay gated.
- **DP-006 evidence-consistency gate applied:** conditional platform items (OAuth,
  distribution, queue framework, REST/GraphQL, multi-company, module boundaries,
  payouts, data models) stay conditional/open; improvement opportunities (auto-apply,
  unified command center, freshness) labelled **inference**, not demonstrated
  competitor capability. **No claim promoted to a fact; no on-page detail invented.**

## MVP inputs, not decisions

Candidate core (input): connect+prove; core object sync at the demonstrated baseline;
the sync+correctness engine (webhooks + reconciliation + scheduled + manual,
idempotency, dedup/binding, retry/recovery); operator UX (command center +
recovery-first errors + honest freshness); role-based access. Explicitly later
(input): advanced breadth, payouts, financial reporting, per-market pricing,
custom-Python transforms, multi-company. **MVP is not finalized** — candidates for
**RB-13** only. Open: single/multi-store; single/multi-company; core vs optional
add-on grouping; **primary MVP persona (P1 vs P2)**.

## Architecture inputs, not decisions

The vision/UX principles supply **product-intent inputs** to **AR-002…AR-008** — all
remain **"Not decided / Evidence pending."** No distribution model, OAuth mandate,
REST/GraphQL choice, queue framework, binding data model, module boundary/name, or
inventory/fulfilment design is decided. A **non-decision note** was added to
`architecture-review-log.md`.

## Open questions

Distribution model (AR-002); primary MVP persona + single/multi-store & company
(RB-13); core vs add-on grouping / feature-flag model (RB-13/AR-004); reconciliation
cadence + per-object vs global freshness (AR-003/006); error/retry taxonomy (AR-006);
binding model + deleted-binding handling (AR-005); queue framework + Odoo-Online
(AR-003); non-Shopify-Payments payout modelling; Odoo edition gating disclosure;
whether firming up weak/blocked evidence (TQ 403, EC/R5, 17 unread VT Confluence)
changes any product framing; demo/docs hosting + self-test scope.

## Learning feedback loop

- **New issues discovered:** none. No new defect pattern emerged. The **DP-006
  evidence-consistency gate** (3rd-occurrence, ESCALATED) was **applied, not
  re-triggered**; DP-003/DP-004/DP-005 prevention rules were applied throughout (no
  claim-as-fact; config field ≠ demonstrated support; classification = input, not
  decision).
- **Repeated issue patterns:** none at threshold; no new occurrence added to any
  category. Escalation gates remain honoured by the no-code gate.
- **Rules/checklists updated:** none required — existing rules were sufficient and
  applied. QA logs received non-decision / no-new-issue notes only.
- **New rejected approaches:** none (nothing evaluated to rejection; noted in
  `rejected-approaches-log.md`).
- **New technical debt:** none (no code; noted in `technical-debt-register.md`).
- **Architecture concerns:** vision/UX principles now supply product-intent inputs to
  AR-002…AR-008 — recorded as a **non-decision note** in `architecture-review-log.md`;
  **all rows stay Not decided / Evidence pending.**
- **Tests or review gates needed:** none active (synthesis). The DP-006
  evidence-consistency gate remains the standing pre-MVP/architecture review gate.
- **Should future prompts change? No** (beyond what Sprint D encoded) — keep every
  principle/candidate an **input** with MVP=RB-13 / architecture=RB-14 gating, keep
  synthesis worker-owned, keep conditional platform items conditional (DP-006). Branch
  reality remains the harness-designated `claude/...` branch while the PR targets
  `Shopify-connector`.

## What ChatGPT should review

1. **Positioning & thesis** — is "correct by design, honest by default, prove both to
   the operator" right, and are the five differentiation themes correctly prioritised
   as inputs?
2. **Evidence discipline (DP-003/004/006)** — no claim-as-fact; EM/VT weighted over
   SH/WK/EC/TQ; conditional items stay conditional/open.
3. **No premature MVP/architecture (DP-005 guard)** — confirm nothing reads as a
   decision or final UI/menus; flag any hardening.
4. **Personas** — are P1–P4 reasonable inference-level inputs, with "primary MVP
   persona" left open?
5. **Non-negotiables** — endorse/amend the seven-item quality contract.
6. **Sequencing** — confirm RB-13 next, then RB-14, consuming this vision + UX
   principles.
7. **Branch-name discrepancy** — confirm working on
   `claude/sprint-e-product-strategy-gd2kfs` (PR → `Shopify-connector`) is acceptable.

## Recommended next session

**RB-13 (MVP scope implications — not finalized)** consuming this vision + UX
principles + the Sprint D taxonomy/evidence map under the DP-006 evidence-consistency
gate, then **RB-14 (architecture preparation)** against AR-002…AR-008 — all gated and
ChatGPT-reviewed. Optionally firm up weak/blocked evidence (TQ 403; EC/R5; 17 unread
VT Confluence). Keep the no-code gate; one scoped objective per session.

## Stop confirmation

Stopped at the Sprint E boundary as instructed: three stage commits on the
harness-designated working branch plus this handoff commit, **one draft PR** targeting
**`Shopify-connector`**, **not merged**. **No** code, **no** Odoo module, **no** MVP
finalization, **no** architecture decisions, **no** ADRs, **no** implementation plan,
**no** module boundaries. `main` and plain `dev` untouched. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint E)

- [x] Session handoff updated (this block + product-research-handoff.md Sprint E).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (no new issue; DP-006 gate applied —
  noted in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-006 gate
  applied, not re-triggered).

---

# Research/Product Sprint D Handoff

> **Research/Product Sprint D — Canonical Feature Taxonomy and Evidence-Based
> Capability Model.** Research/synthesis-only; no-code gate in force (`CLAUDE.md`
> §4–§5). High-power mode **not required** (focused synthesis of already-merged
> Sprint C evidence — no new competitor crawling). Maps to backlog item **RB-12
> (canonical feature taxonomy)**, feeding RB-11 (vision), RB-13 (MVP implications),
> and RB-14 (architecture prep) — all gated.

## Session summary

Converted the Sprint C competitor research into a **canonical feature taxonomy**
(`docs/02-product/feature-taxonomy.md`) and a **capability evidence map**
(`docs/02-product/capability-evidence-map.md`) for the Odoo 19 ↔ Shopify Connector,
and wrote the product-side handoff (`docs/02-product/product-research-handoff.md`).
The taxonomy normalizes the messy competitor feature matrix into **20 canonical
domains** and ≈90 **canonical capabilities**, each classified by evidence
status/strength, capability type (product-UX / reliability / configuration /
architecture), candidate class (baseline / premium / advanced-later / optional
add-on / unknown), MVP relevance (candidate / later / unknown), and
architecture-review dependency (AR-002…AR-008). Every classification is an
**input**, not a decision. **No connector code, no Odoo module, no MVP
finalization, no architecture decisions, no ADRs, no implementation plan, and no
module boundaries** were produced. No new competitor sources were crawled — the
sprint synthesises **already-merged repo evidence only**, preserving per-claim
classification and DP-003/DP-004 discipline. Synthesis was **worker-owned** (main
thread), not fanned out, so claim classification stayed centrally governed.

### Sprint D revision (PR #52 review — 2026-07-01)

ChatGPT review returned **REVISE** (small taxonomy precision patch); corrected on
the same branch (`docs: correct sprint d taxonomy precision`), logged as **DP-006**:

- **Removed the `SH` abbreviation collision** — `SH` = **only** sh_shopify_connector
  / Softhealer; Shopify official docs are keyed **SHOPIFY-OFFICIAL** (Odoo official
  = **ODOO-OFFICIAL**).
- **OAuth-first (C-CONN-01) official-platform dependency made conditional** — strong
  UX/security direction, competitor-demonstrated (VT), but a platform *requirement*
  **only if public/App-Store distribution is chosen**; custom/private flows may use
  token/custom-app access. AR-002 open; not a finalized decision. Evidence strength
  `A` → `B / A-if-public`.
- **Stock import (C-INV-04) reframed** as "Stock import with controlled apply/review"
  — auto-apply is an **improvement/inference, not demonstrated**; AR-007 still applies.
- **Webkul import-stock coverage corrected** to **⬜ (not found)** per matrix §3 (was
  ✅); matrix-consistent coverage EM✅ VT✅ SH✅ TQ🟨 EC🟨 WK⬜.
- **Escalation:** unsupported-assumption/weak-research reaches its **3rd occurrence**
  (DP-003, DP-004, DP-006) → an **evidence-consistency gate** was recorded in
  `defect-pattern-log.md` (implementation stays paused by the existing no-code gate;
  no capability may enter MVP/architecture as a decision until its evidence strength,
  conditionality, and competitor coverage are ChatGPT-reviewed). **No implementation
  task is set.**

## Branch and commits

**Working branch:** `claude/feature-taxonomy-sprint-d-t8d2t0` (the
harness-designated branch; based on `Shopify-connector` @ `e18ba8e`, the merged
**PR #51** Sprint C baseline). **Branch-name note for ChatGPT (flagged):** the
Sprint D prompt body named `product/sprint-d-feature-taxonomy`, but the session's
hard git rule designated `claude/feature-taxonomy-sprint-d-t8d2t0` ("never push to
a different branch without explicit permission"), so work proceeded on the
harness-designated branch; **the PR still targets `Shopify-connector`**; `main` and
plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `2e297ba` | docs: start sprint d feature taxonomy |
| `70391b9` | docs: add canonical feature taxonomy |
| `aa5d2c4` | docs: add capability evidence map |
| _(this commit)_ | docs: finalize sprint d taxonomy handoff |

## Files created or updated

**Product (`docs/02-product/`)**
- `feature-taxonomy.md` (new — main deliverable), `capability-evidence-map.md`
  (new), `product-research-handoff.md` (new).

**Research (`docs/01-research/`)**
- `research-handoff.md` (this file — Sprint D section + checkpoints).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — DP-005 + counter), `architecture-review-log.md`
  (updated — Sprint D non-decision note), `rejected-approaches-log.md` (updated —
  Sprint D "nothing rejected" note), `technical-debt-register.md` (updated —
  Sprint D "no debt" note).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/03|04|07|08`; no `.claude/skills|agents`).

## Taxonomy summary

- **20 domains:** (1) connection/auth/setup, (2) dashboard/command center, (3)
  product catalog, (4) variants/media, (5) pricing, (6) inventory/locations, (7)
  customers/companies/addresses, (8) orders/lifecycle, (9) invoices/payments/
  journals, (10) fulfillment/tracking, (11) refunds/returns/cancellations, (12)
  payouts/reconciliation, (13) webhooks/scheduled/manual/reconciliation, (14)
  queue/jobs/retries, (15) logs/errors/observability, (16) mapping/matching/dedup,
  (17) multi-store/company/permissions, (18) advanced Shopify (Markets/B2B/POS/gift
  cards/metafields), (19) reporting/analytics, (20) docs/support/demo.
- **≈90 canonical capabilities**, each with the required attribute block; **8
  cross-cutting groups** (idempotency-by-default, recovery-first ops, honesty/
  transparency, safe-by-default destructive actions, progressive disclosure,
  feature flags, modularity/extension points, multi-tenancy/permissions).
- **Required canonical capabilities represented:** idempotency, duplicate
  prevention, GID binding, HMAC verification, webhook-id dedup, fast-ack, scheduled
  + manual reconciliation, retry classification, auto-retry, manual retry,
  rate-limit/GraphQL-cost throttling, bulk ops, per-record isolation, resumable
  jobs, reason-coded logs, audit trail, recovery-first error center; setup wizard,
  OAuth-first, credential masking, test connection, scope/readiness check, health
  indicators, named-cause diagnostics, command center, activity timeline, queue
  status, failure counts, quick actions, dry-run/preview, guided mapping,
  progressive disclosure, inline help, empty states, recovery actions, sync
  freshness; feature flags, optional add-ons, domain-isolated/per-store config,
  per-company isolation, role-based access, extension points, mapping/transport
  extensibility (architecture inputs); payouts, advanced refunds, Markets, B2B, POS,
  gift cards, metafields, abandoned-checkout→CRM, recommendations, Buy-with-Prime,
  advanced analytics, app-store packaging, public demo/docs/changelog.

## Evidence discipline

- **DP-003 applied:** competitor claims stay claims; TQ (docs 403) and EC (no
  screenshots) support is marked **claim-only / weak**; SH ✅ marks rest on captions
  (medium-behaviour, low-trust).
- **DP-004 applied:** WK multi-company kept as a **config field only (➖)**; SH
  multi-company kept **not-found**; EC product export kept **not-found**; `✅`/
  "demonstrated" used only with a specific demonstrated workflow/screenshot/dated
  release note/explicit doc.
- **Evidence strength scale (A–E)** in the evidence map: **A** official-platform
  requirement (≈22 caps), **B** strong competitor demonstration (EM/VT-led, ≈45),
  **C** mixed/partial (≈8), **E** whitespace/inference (freshness, empty states,
  plus platform-required-but-undemonstrated items: reconciliation surface,
  rate-limit throttling, webhook-id dedup).
- **No competitor claim promoted to a Tier-1 fact; no on-page detail invented.**

## MVP inputs, not decisions

Capabilities tagged **MVP relevance: candidate** cluster around a **correct,
observable core** (connect+prove; core object sync; sync+correctness engine;
operator command center + recovery-first errors; role-based access). Advanced
breadth (Domain 18), payouts, financial reporting, per-market pricing, custom-Python
transforms, and multi-company are tagged **later**. **MVP is not finalized** — these
are candidates for **RB-13** review only. Open MVP-shaping questions: single- vs
multi-store; single- vs multi-company; core vs optional add-on grouping.

## Architecture inputs, not decisions

The taxonomy maps capabilities to **AR-002…AR-008** (API/distribution; sync
orchestration/queue; module boundaries; binding/dedup; error/retry/idempotency;
inventory; fulfillment) — **all remain "Not decided / Evidence pending."** No
queue framework, REST/GraphQL choice, data model, or module boundary/name is
decided. A **non-decision evidence note** was added to
`architecture-review-log.md`.

## Open questions

Distribution model (public vs custom → AR-002); single/multi-store & single/multi-
company at MVP (RB-13); reconciliation cadence/scope + per-object vs global
freshness; error/retry taxonomy; binding model (`ir.model.data` vs dedicated;
deleted-binding handling — AR-005); queue framework (`ir.cron` vs `queue_job`;
Odoo-Online implications — AR-003); core vs optional add-on grouping; firming up
weak/blocked evidence (Teqstars 403, EC/R5 setup guide, 17 unread VT Confluence);
non-Shopify-Payments payout modelling; Odoo edition gating disclosure.

## Learning feedback loop

- **New issues discovered:** one — **DP-005** (premature-decision risk, category
  #4 premature architecture): a feature taxonomy's *candidate / premium / later*
  labels and *architecture-dependency* tags could be **misread as MVP or
  architecture decisions**. **Prevented/Mitigated** by explicit "inputs, not
  decisions" framing throughout, dedicated "MVP-candidate inputs, not decisions"
  and "Capabilities requiring architecture review" sections, per-field gating
  language, and closing "decides nothing" notes; MVP=RB-13 and architecture=RB-14/
  AR-002…AR-008 remain gated.
- **Repeated issue patterns:** DP-005 is the **1st** occurrence of category #4
  (premature architecture) in the defect-pattern log — no 2×/3× escalation. The
  existing unsupported-assumption/weak-research thread (DP-003, DP-004) was **not**
  re-triggered: DP-004's prevention rule (config field ≠ demonstrated support;
  market promise ≠ demonstrated bidirectionality) was **applied throughout** this
  synthesis (WK multi-company ➖, SH multi-company not-found, EC export not-found,
  TQ claim-only), which is the intended anti-repetition behaviour.
- **Rules/checklists updated:** added **DP-005** + prevention rule to
  `defect-pattern-log.md` (a normalized taxonomy must label every candidate/
  classification as an **input**, not a decision; MVP and architecture stay gated).
- **New rejected approaches:** none (synthesis-only; noted in
  `rejected-approaches-log.md`).
- **New technical debt:** none (no code; noted in `technical-debt-register.md`).
- **Architecture concerns:** the taxonomy now supplies **capability-level inputs**
  to AR-002…AR-008 — recorded as a **non-decision note** in
  `architecture-review-log.md`. **All rows stay "Not decided / Evidence pending."**
- **Tests or review gates needed:** none active (synthesis). For implementation
  (gated), the regression-test set seeded in A-IMP-4 (duplicate orders,
  multi-location double-decrement, missed-webhook reconciliation, idempotent
  refunds, timezone/paging) now maps to specific capability IDs.
- **Should future prompts change? Yes** — product-synthesis prompts should (1)
  require every capability classification to be labelled an **input/candidate** with
  MVP=RB-13 / architecture=RB-14 gating stated (now encoded via DP-005), and (2)
  keep synthesis **worker-owned** (not fanned out) so claim classification stays
  centrally governed. Branch reality remains the harness-designated `claude/...`
  branch while the PR targets `Shopify-connector`.

## What ChatGPT should review

1. **Taxonomy completeness & naming** — are the 20 domains + ≈90 capabilities the
   right canonical decomposition (nothing missing/duplicated/mis-placed)?
2. **Evidence discipline** — spot-check DP-003/DP-004: no claim-as-fact; `✅` only
   where demonstrated; WK multi-company ➖, SH multi-company not-found, EC export
   not-found, TQ claim-only all reflected in both product files.
3. **Classification calibration** — are baseline/premium/advanced-later/optional
   and MVP candidate/later/unknown reasonable **as inputs**? Flag anything reading
   like a premature decision (DP-005 guard).
4. **Architecture routing** — confirm AR-002…AR-008 mapping is correct and that
   **no architecture is decided** (no queue framework, no REST/GraphQL, no module
   boundaries/names, no data models).
5. **Whitespace priorities** — endorse/re-rank the correctness whitespace
   (reconciliation, idempotency, rate-limit throttling, webhook-id dedup) and the
   operator-UX whitespace (command center + recovery-first errors) as leading
   differentiation inputs for RB-13/RB-14 — **without** locking MVP.
6. **Branch-name discrepancy** — confirm working on `claude/feature-taxonomy-sprint-d-t8d2t0`
   (PR → `Shopify-connector`) is acceptable.
7. **Next-sprint sequencing** — confirm RB-11 (vision) / RB-13 (MVP implications) as
   the next gated step, then RB-14 (architecture prep).

## Recommended next session

**RB-11 (product vision draft)** and/or **RB-13 (MVP scope implications — not
finalized)**, consuming this taxonomy + evidence map, then feeding **RB-14
(architecture preparation)** against AR-002…AR-008 — all gated and ChatGPT-reviewed.
Optionally firm up weak/blocked evidence (Teqstars 403; EC/R5 setup guide; 17 unread
VT Confluence) if ChatGPT wants firmer classification. Keep the no-code gate; one
scoped objective per session.

## Stop confirmation

Stopped at the Sprint D boundary as instructed: four stage commits on the
harness-designated working branch, **one draft PR** targeting **`Shopify-connector`**,
**not merged**. **No** code, **no** Odoo module, **no** MVP finalization, **no**
architecture decisions, **no** ADRs, **no** implementation plan, **no** module
boundaries. `main` and plain `dev` untouched. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint D)

- [x] Session handoff updated (this block + product-research-handoff.md).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (DP-005 in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-005 1st occurrence of #4; DP-004 prevention applied, not re-triggered).

---

# Research Sprint C Handoff

> **Research Sprint C — High-Power Competitor Deep Dives, Screenshot/UX Evidence,
> and Workflow Extraction.** Research-only; no-code gate in force (`CLAUDE.md`
> §5). High-power research mode **explicitly authorized** for this sprint. Maps to
> backlog items **RB-02.* (competitor deep dives)**, **RB-03.1 (feature matrix)**,
> **RB-04.1 (UX/UI benchmark)**, **RB-07.1 (common patterns)**, **RB-08.1
> (best-in-class)**, **RB-09.1 (gaps/opportunities)**, and **RB-10.1 (avoid-list)**.

## Session summary

Studied the **eight user-provided competitor resources (R1–R8)** from real
evidence and produced the full Sprint C research set: **source notes + an
analysed screenshot/visual inventory**, **six competitor deep dives** (Webkul,
Teqstars, Emipro, VentorTech, ecommerce_shopify, sh_shopify_connector + a
blocked-source record for the Google Doc), a **first cross-competitor feature
matrix**, a **UX/UI benchmark**, and the **common-patterns / best-in-class /
gaps-opportunities / avoid-list** synthesis. Evidence was gathered with a
**controlled high-power capture→verify fan-out** (one capture agent + one
adversarial verifier per source) and synthesised by the worker so claim
classification and the no-code/no-MVP/no-architecture gate stayed owned centrally.
**Every claim is cited and classified**; competitor capability statements remained
**competitor claims** unless a documented workflow/screenshot demonstrated them;
**no competitor claim was promoted to a Tier-1 fact**; blocked sources were
recorded, **never bypassed**. **No connector code, no Odoo module, no MVP scope,
and no architecture decisions** were produced.

## Branch and commits

**Working branch:** `claude/research-sprint-c-competitors-hgoo8t` (the
harness-designated branch; based on `Shopify-connector` @ `d6fbcdb`, the merged
**PR #50** Sprint B baseline). **Branch-name note for ChatGPT (flagged):** the
Sprint C prompt body named `research/sprint-c-competitor-deep-dives-ux-evidence`,
but the session's hard git rule designated `claude/research-sprint-c-competitors-hgoo8t`
("never push to a different branch without explicit permission"), so work proceeded
on the harness-designated branch; **the PR still targets `Shopify-connector`**;
`main` and plain `dev` untouched.

| Hash | Message |
| --- | --- |
| `6b07fad` | docs: start sprint c high-power competitor research |
| `e1c5ec4` | docs: capture competitor source and screenshot evidence |
| `1e027a0` | docs: add competitor deep dives |
| `da93ba9` | docs: add competitor matrix and ux benchmark |
| `890ce0b` | docs: synthesize competitor patterns and opportunities |
| _(this commit)_ | docs: finalize research sprint c handoff |

## High-power research mode used

**Yes — explicitly authorized and documented before launch** (the
**Sprint C high-power research plan** below was committed in `6b07fad` before any
agent ran). **Workstreams:** a `pipeline()` workflow of **one capture agent per
source (R1–R8)** returning structured, cited, claim-classified evidence (access
status, feature claims, reconstructed workflows, visuals, reliability signals,
release notes, quotes, open questions), each followed by **one adversarial
verifier** that re-read the source and **downgraded anything not literally
supported** (16 agents, 137 tool calls). **Synthesis/verification:** the worker
read every source digest and wrote all deliverables, preserving per-claim
classification and citations. **Unsupported-claim prevention:** strict claim
classes on every line; competitor claims never elevated to facts; blocked/unknown
stated as such; no hidden-feature guessing. **Result:** all 8 sources captured;
the verifier produced material corrections (e.g. **R2 Teqstars Partial→Blocked**;
**ecommerce_shopify "real-time"→cron**; **sh_shopify_connector multi-company→
not-found**), logged as **DP-003**.

### Sprint C high-power research plan (as committed pre-launch)

- **Why high-power mode is needed:** eight competitor resources, several
  multi-page (Emipro ~35 sub-pages; VentorTech 28-article Confluence hub) and two
  previously gated (R2 403; R5 login wall), had to be studied from real evidence
  with verification in one controlled pass.
- **Workstreams / agents:** one capture agent per source (R1–R8) + one adversarial
  verifier per source; worker-owned synthesis.
- **Sources:** R1 Webkul · R2 Teqstars docs (+Apps listing) · R3 Emipro tree ·
  R4 VentorTech Confluence · R5 Google Doc · R6 ecommerce_shopify · R7 VentorTech
  site/ecosystem/Apps · R8 sh_shopify_connector. Tier-1 grounding only from the
  existing official baselines.
- **Screenshots / UI evidence:** analysed markdown inventory (proxy fetcher returns
  markdown/alt-text, not pixels); binaries not forced (sprint rule allows the
  fallback); no auth bypass for any visual.
- **Files to update:** the Sprint C allowed-files set only (listed below).
- **Stop condition:** all accessible sources captured+verified; blocked sources
  documented without bypass; nine deliverables + evidence written, cited,
  classified; QA logs + handoff updated; quality gate satisfied — then stop.
- **Verification method:** two-pass capture→verify; downgrade anything not literally
  on the page; reuse the DP-001 verification gate.
- **Unsupported-claim prevention:** strict claim classification; no claim→fact
  elevation; blocked/unknown stated; no hidden-feature guessing.

## Files created or updated

**Source materials (`docs/00-source-materials/`)**
- `competitor-source-notes.md` (new), `competitor-screenshot-inventory.md` (new),
  `screenshots/README.md` + `screenshots/{webkul,teqstars,emipro,ventortech,odoo-apps}/README.md` (new).

**Research (`docs/01-research/`)**
- `competitor-deep-dives.md` (new), `competitor-feature-matrix.md` (new),
  `ux-ui-benchmark.md` (new), `common-patterns.md` (new),
  `best-in-class-observations.md` (new), `gaps-opportunities.md` (new),
  `avoid-list.md` (new), `resource-inventory.md` (updated — Sprint C access
  changes), `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `defect-pattern-log.md` (updated — DP-003 + counter), `architecture-review-log.md`
  (updated — non-decision Sprint C evidence note), `rejected-approaches-log.md`
  (updated — avoid-list-is-not-rejection note), `technical-debt-register.md`
  (updated — Sprint C no-debt note).

**No forbidden files touched** (no `*.py`/`*.xml`/`*.csv`/manifests/modules/CI/
Docker; no `addons/**`; no `docs/02|03|04|07|08`; no `.claude/skills|agents`).

## Source access results

No auth was bypassed. **Accessible (5):** R1 Webkul, R3 Emipro, R6
ecommerce_shopify, R7 VentorTech site/ecosystem/Apps, R8 sh_shopify_connector —
**plus the Teqstars Odoo Apps listing** as an accessible R2 surrogate. **Partial
(1):** R4 VentorTech Confluence (anonymous banner; 11 of 28 child articles read).
**Blocked (2):** **R2 Teqstars docs host** (HTTP 403 bot-block on the whole
`docs.teqstars.com`, 19.0 **and** 16.0 — verifier downgraded R2 from Partial to
**Blocked**), **R5 Google Doc** (sign-in wall). **New cross-source findings:**
(a) the Teqstars **Apps Store listing is accessible** ($326.20, OPL-1, 83×5.0) and
supplied the R2 evidence; (b) **R5 is the "Get Started" guide for R6
`ecommerce_shopify`** (R6's CTA 301-redirects to that exact doc). Full evidence:
`docs/00-source-materials/competitor-source-notes.md` and the Sprint C section of
`resource-inventory.md`.

## Screenshots / UI evidence captured

Analysed visual inventory in `competitor-screenshot-inventory.md` (no binary files
saved — proxy fetcher returns markdown/alt-text; sprint rule allows the markdown
fallback). **Most demonstrative:** **Emipro** (~29 **real `.png`** screenshots of
queues/Log Book/config) and **VentorTech R4** (traffic-light webhook health,
External-Location mapping, Preview/Report dry-run). **Caption-only/weak:**
Teqstars (17 captions; **docs screenshots 403-blocked**), VentorTech R7 (alt-text
flows). **None:** **ecommerce_shopify (no UI screenshots at all)**; Google Doc
(blocked). sh_shopify_connector has the broadest caption walkthrough (~29 groups)
but no rendered-image verification.

## Competitor deep dives completed

All six in `competitor-deep-dives.md`: **Webkul, Teqstars, Emipro, VentorTech,
ecommerce_shopify, sh_shopify_connector**, plus a **blocked-source record** for the
Google Doc. Each separates competitor claims from facts and from demonstrated
workflows, with per-area feature classification, workflow reconstruction, UX,
reliability, maintenance, strengths/weaknesses, learn/do-better/avoid, and open
questions.

## Key feature findings

- **GraphQL is the converging API** (VentorTech migrated REST→GraphQL Jan 2026;
  all position on it) — consistent with Tier-1.
- **Webhooks + scheduled + manual** is the table-stakes sync shape; **staging/
  queues** are near-universal — **except ecommerce_shopify (cron-only, no
  webhooks, email-only errors)** and Webkul (no webhooks; Feeds staging).
- **Feature-breadth leaders:** sh_shopify_connector (gift cards, abandoned-
  checkout→CRM, recommendations, Buy-with-Prime), Teqstars-on-paper (Markets/B2B/
  payouts/queue — unverified), Emipro (payouts/Markets/metafields/analytic,
  demonstrated).
- **Whitespace (no competitor demonstrates well):** **named rate-limit/cost-aware
  throttling** (none), **first-class user-visible reconciliation** (none),
  **automatic retry** (only VentorTech), **B2B** (only VentorTech), **payout
  reconciliation** (only Emipro demonstrated).
- **Pricing (on-page 2026-06-30):** WK $170 · TQ $326.20 · EC $195.56 · SH
  $168.81 · VT €499 / $569.16; EM price not in docs.

## Key UX/UI findings

- **Best diagnostics — VentorTech:** traffic-light webhook health with a **named
  cause + fix hint**; Preview/Report dry-run; Failed-Job Notifications;
  irreversible-action warnings; honest PII disclosure.
- **Best observability — Emipro:** state-coloured queues + per-line reason-coded
  Log Lines + Log Book.
- **Best monitoring — sh_shopify_connector:** Integration Dashboard + **daily
  activity chart** + failure counts + re-export recovery flag; access-right-gated
  setup.
- **Frustrations to avoid:** "real-time" mislabelling (WK/EC/SH); raw cron
  internals exposed (WK); manual stock-adjustment (EM); email-only errors (EC);
  technical install (VT odoo.conf/queue_job; not Odoo Online); toggle-dense config;
  gated/blocked docs (EC/TQ).
- **No connector has a unified command center + recovery-first error center
  together** — a clear UX differentiator.

## Key reliability findings

- **VentorTech leads (demonstrated by dated release notes):** GraphQL
  **`@idempotent`** directives (Shopify 2026-04), **automatic retry** of safe
  ops, a real **`queue_job`** async queue, HMAC-SHA256 webhooks, and openly
  disclosed **CRITICAL silent-data-loss fixes** (paging, timezone).
- **Emipro:** strong observability (Log Book), email/SKU dedup, stored-reference
  re-export blocking, manual missed-webhook recovery — **but manual-only retry**
  and a **stale v19 changelog**, and its docs cite the **outdated Shopify
  "19 retries/48h"** figure (Tier-1: 8/4h).
- **Across the field:** idempotency is mostly implicit; **rate-limit handling is
  absent**; reconciliation is implicit; "real-time" is overstated. These map onto
  Tier-1 (webhook delivery not guaranteed → reconcile; `@idempotent` from 2026-04).

## Common patterns

Strongly common (≥2 demonstrate): custom-app connect; bidirectional core sync;
**staging/queue before commit**; scheduled + manual sync; SKU/barcode + email
dedup + Shopify-ID write-back; auto-workflow; fulfillment/tracking write-back;
reason-coded in-app logs; per-record failure isolation; GraphQL. Rare/
differentiating: automatic retry, idempotency directives, real job queue,
traffic-light health, dry-run, payouts, gift cards, B2B, abandoned-checkout→CRM.
**Missing across the field:** rate-limit/cost throttling, first-class
reconciliation, a unified command center, honest latency, documented HMAC.
(`common-patterns.md`.)

## Best-in-class observations

Onboarding (VT OAuth + scope/connection test; WK Test Connection), product sync
(EM incremental + CSV fallback; VT testable directional mapping), order flow (VT
auto-workflow pipeline; EM multi-payment fidelity), inventory (VT quantity-field
choice + multi-company; EM deterministic export), fulfillment (EM Put-in-Pack),
logs/errors (EM Log Book; VT diagnostics; SH monitoring), docs/maintenance (EM
honesty; VT dated changelog), security (SH access groups). (`best-in-class-observations.md`.)

## Gaps and opportunities

Top differentiation themes (recommendations, gated): **demonstrated correctness**
(idempotency + reconciliation + rate-limit throttling — the biggest whitespace and
Tier-1-mandated); **best operator UX** (unified command center + recovery-first
errors + named diagnostics + dry-runs); **effortless install with real
reliability** (the combo nobody has); **honesty/transparency** (latency labels,
dated changelog disclosing fixes, open docs/demo); **premium breadth as clean
add-ons** (payouts, B2B, gift cards, Markets). MVP-relevance is tagged
candidate/later/unknown per item — **not finalized**. (`gaps-opportunities.md`.)

## Avoid-list highlights

Webhook-only/cron-only sync; no reconciliation; `ir.cron`-as-a-queue; heavy work
in the webhook request; no rate-limit handling; skipping HMAC; email-only errors;
manual-only recovery; irreversible "Force Done"; single-location inventory;
writing `committed`; legacy fulfillment endpoints; non-idempotent refunds;
assuming payouts exist for all gateways; bot-blocked/gated/stale docs; one-giant-
module / `_inherits` delegation; `productSet` delete-on-omit as partial update.
Items tagged **"Arch review: YES"** route through AR-002…AR-008. (`avoid-list.md`.)

## What is still blocked

- **R2 Teqstars docs** (`docs.teqstars.com`, 19.0 + 16.0) — HTTP **403**
  bot-block on the whole host; no workflow/screenshot evidence. *(The Apps Store
  listing substituted as accessible vendor-claim evidence.)* **Unblock:** a
  browser-UA fetch of the 19.0 docs (no auth to bypass), **or** ChatGPT accepts the
  Apps-listing evidence as sufficient.
- **R5 Google Doc** — sign-in wall; **owner view-access or export required**; it
  is specifically **R6's setup guide**.
- **R4 VentorTech Confluence** — 17 of 28 child articles unread (not gated, just
  not fetched); optional for fuller coverage.

## Inferences, not decisions

All strengths/weaknesses, "do better", gaps/opportunities, avoid-list items, and
the architecture-evidence note are **inferences/recommendations**. **No MVP scope
and no architecture is decided.** Competitor claims are **claims**, not facts;
on-page price/license/version are **facts about the listing on 2026-06-30**. The
AR-002…AR-008 rows remain **"Not decided / Evidence pending."**

## Open questions

Teqstars: are the idempotency/queue-retry/Markets claims real (docs blocked)?
ecommerce_shopify: official vs partner provenance; does product export exist; what
is in the blocked setup doc (R5)? VentorTech: can install be Odoo-Online-friendly;
payout/POS/gift-card roadmap; connector permission model? sh_shopify_connector:
real adoption (no ratings) and currency (no changelog); multi-company; idempotency/
HMAC details? Field-wide: how do competitors surface rate-limit and reconciliation
to users (none observed)? (Per-source lists in the deep dives.)

## Risks

- **Evidence asymmetry:** TQ (docs blocked) and EC (no screenshots) are
  **vendor-claim-heavy** — their real capabilities may differ from the matrix;
  EM/VT carry the most demonstrated evidence (weight accordingly).
- **Vendor-claim drift:** marketing "real-time"/idempotency/queue claims can
  overstate; mitigated by classification + verification (DP-003).
- **Source volatility:** competitor pricing/pages/changelogs change; re-date on
  re-visit. Teqstars 403 may persist.
- **Synthesis temptation:** keep MVP/architecture gated; do not let
  gaps/opportunities harden into decisions before ChatGPT review.

## Learning feedback loop

- **New issues discovered:** one — **DP-003** (unsupported assumption #3 / weak
  research #1): competitor capability statements, **especially from a blocked docs
  site (Teqstars 403) or a screenshot-free listing (ecommerce_shopify)**, risk
  being recorded as facts; "real-time" marketing risks masking a cron/queue model.
  **Prevented** by the capture→verify two-pass + strict claim classification
  (which produced concrete downgrades: R2 Partial→Blocked, EC "real-time"→cron,
  SH multi-company→not-found).
- **Repeated issue patterns:** none at threshold. DP-003 is the **1st** occurrence
  of category #3/#1. Separately, Sprint C found **external confirmation of the
  DP-001 risk** — Emipro's docs cite the stale Shopify "19 retries/48h" figure
  (Tier-1: 8/4h); **not adopted** (the verification gate held). No 2×/3× escalation.
- **Rules/checklists updated:** added **DP-003** + its prevention rule (classify
  every line; never elevate a competitor claim to a fact; run an adversarial
  verifier that downgrades anything not literally on the page) and the occurrence
  counter in `defect-pattern-log.md`. The **per-cell evidence symbol +
  evidence-note** convention in the feature matrix is now the standard for future
  competitor matrices.
- **New rejected approaches:** none (research-only). The **avoid-list** holds
  competitor anti-patterns as **recommendations**, explicitly **not** rejected
  decisions; `rejected-approaches-log.md` notes they route through architecture
  review before any formal rejection.
- **New technical debt:** none (no code). Blocked sources are research gaps, not
  debt (noted in `technical-debt-register.md`).
- **Architecture concerns:** competitor evidence now **informs** AR-002…AR-008 —
  recorded as a **non-decision note** in `architecture-review-log.md` (GraphQL
  convergence; webhooks+cron+queue with `queue_job` as a real data point; SKU/
  email/ID-write-back binding; `@idempotent`+retry; multi-location; FulfillmentOrder).
  **All rows stay "Not decided / Evidence pending."**
- **Tests or review gates needed:** none active (research). For implementation
  (gated): regression tests for duplicate orders, multi-location double-decrement,
  missed-webhook reconciliation, idempotent refunds, timezone/paging — seeded in
  the avoid-list (A-IMP-4) for the definition-of-done.
- **Should future prompts change? Yes** — (1) for blocked/screenshot-free sources,
  prompts should **mandate the capture→verify two-pass and the claim-class
  symbols** (now encoded via DP-003); (2) competitor-research prompts should state
  that the **branch reality is the harness-designated `claude/...` branch** while
  the **PR targets `Shopify-connector`**, to avoid the Sprint C branch-name
  ambiguity.

### Sprint C revision (PR #51 review — 2026-07-01)

ChatGPT review returned **REVISE** for two evidence-classification overstatements;
corrected on the same branch (`docs: correct sprint c evidence classifications`):

- **Correction 1 — Webkul multi-company.** The Webkul default **Company** field was
  initially classified too strongly as **demonstrated multi-company support** (✅).
  True multi-company support/isolation was **not demonstrated**; a visible config
  field is not evidence of multi-company routing or record-rule handling. Downgraded
  to `⬜/➖` in `competitor-deep-dives.md` and to `➖` in `competitor-feature-matrix.md`
  (with an evidence note; EM/VT remain the demonstrated multi-company evidence).
- **Correction 2 — "bidirectional core sync" common pattern.** The strongly-common
  pattern claiming **bidirectional product/order/inventory/customer sync across all**
  connectors was **narrowed**: broad core-object coverage is a common *market promise*,
  but **directionality varies by object and evidence strength** (EC product export not
  found; WK customer export not found; TQ listing-claim only; EM/VT strongest
  directional evidence). Updated in `common-patterns.md`.
- **Category:** unsupported assumption (#3) / weak research classification (#1) — logged
  as **DP-004** in `defect-pattern-log.md`.
- **Prevention rule:** configuration fields must **not** be treated as demonstrated
  feature support unless the workflow/behaviour is shown; common-pattern wording must
  distinguish a **market promise** from **demonstrated bidirectionality**.

## What ChatGPT should review

1. **Claim discipline** — spot-check that competitor claims are not presented as
   facts, especially TQ (docs blocked) and EC (no screenshots), and that the
   verifier's downgrades (R2→Blocked, EC→cron, SH multi-company→not-found) are
   reflected everywhere.
2. **Matrix evidence** — confirm the per-cell symbols + evidence notes are fair
   and that 🟨/🔒 are used where evidence is listing-only/blocked.
3. **Blocked-source handling** — endorse recording R2 docs as Blocked (with the
   Apps-listing surrogate) and R5 as Blocked (= R6's setup guide); decide the
   unblock path for each.
4. **Gaps/opportunities & avoid-list** — confirm these stay **recommendations**
   (no MVP/architecture lock-in) and which opportunities to prioritise for RB-13/
   RB-14.
5. **Branch-name discrepancy** — confirm working on the harness-designated branch
   `claude/research-sprint-c-competitors-hgoo8t` (PR → `Shopify-connector`) is
   acceptable, or instruct otherwise.
6. **DP-003 + verification gate** — endorse making the capture→verify two-pass the
   standing rule for competitor research.

## Recommended next session

With competitor evidence in place, proceed to **RB-12 (canonical feature
taxonomy)** to normalize the matrix rows, then **RB-11 (product vision draft)** and
**RB-13 (MVP scope implications — not finalized)**, feeding **RB-14 (architecture
preparation)** against AR-002…AR-008 — all gated and ChatGPT-reviewed. In parallel,
resolve the **R2/R5 unblocks** (browser-UA fetch decision for Teqstars 19.0 docs;
owner access/export for the Google Doc) and optionally finish the **17 unread
VentorTech Confluence** articles. Keep the no-code gate; one scoped objective per
session.

## Stop confirmation

Stopped at the Sprint C boundary as instructed: five stage commits on the
harness-designated working branch, **one draft PR** to be opened targeting
**`Shopify-connector`**, **not merged**. **No** code, **no** Odoo module, **no**
MVP scope, **no** architecture decisions, **no** ADRs. `main` and plain `dev`
untouched. Blocked sources documented without bypass. Awaiting ChatGPT review.

## Quality gate confirmation (Sprint C)

- [x] Session handoff updated (this block).
- [x] Quality feedback loop checked (this file + `../05-qa/` logs).
- [x] New learning captured in the correct file (DP-003 in `defect-pattern-log.md`).
- [x] Any rejected approach logged (none — avoid-list is recommendations, noted in `rejected-approaches-log.md`).
- [x] Any accepted technical debt logged (none — noted in `technical-debt-register.md`).
- [x] Any repeated issue pattern escalated per §4 (none at threshold; DP-003 1st occurrence).

## Sprint C high-power research plan

- **Why high-power mode is needed:** Eight user-provided competitor resources
  (R1–R8) must be studied from **real evidence** — full documentation trees,
  on-page screenshots, configuration/setup flows, feature claims, release notes,
  pricing/support, and UX — so the connector is designed from knowledge, not
  guesses. Several sources are multi-page (Emipro doc tree, VentorTech Confluence
  hub with ~27 children) and two were previously gated (R2 Teqstars 403; R5
  Google Doc login wall). Covering this breadth with verification in one pass
  justifies a controlled parallel fan-out (per `CLAUDE.md` → High-power research
  mode; the policy is a capability, not a cap).
- **Workstreams / agents:** One **source-capture agent per resource** (R1 Webkul,
  R2 Teqstars, R3 Emipro + sub-pages, R4 VentorTech Confluence hub + children, R5
  Google Doc, R6 ecommerce_shopify, R7 VentorTech site, R8 sh_shopify_connector),
  each returning **structured, cited, claim-classified evidence** (access status,
  visible sections, feature claims, visuals/screenshots described, workflow steps,
  version context). Then a **verification workstream** that re-checks the
  highest-stakes claims (pricing, sync model, key features, access status) against
  the captured evidence and flags anything unsupported. Synthesis into the
  deliverable docs is performed by the worker (main thread) so governance
  (citation + claim classification + no-MVP/no-architecture gate) is owned
  centrally.
- **Sources to inspect:** R1 https://webkul.com/blog/odoo-multichannel-shopify-connector/ ·
  R2 https://docs.teqstars.com/19.0/applications/shopify/overview.html ·
  R3 https://docs.emiprotechnologies.com/shopify-odoo-connector/v19/installation.html (+ tree) ·
  R4 https://ventortech.atlassian.net/wiki/spaces/pd/pages/482639953/Shopify (+ children) ·
  R5 https://docs.google.com/document/d/1zIwRxp7cvLYeyjl8P_mvsjC-v8Tsd_ugC1JbfTznHC8/edit ·
  R6 https://apps.odoo.com/apps/modules/19.0/ecommerce_shopify ·
  R7 https://ventor.tech/solutions/odoo-shopify-connector/ ·
  R8 https://apps.odoo.com/apps/modules/19.0/sh_shopify_connector#features.
  Tier-1 grounding only from the existing official Shopify/Odoo baselines (these
  competitor sources are Tier 2–5 → **competitor claims**, not facts).
- **Screenshots / UI evidence approach:** Primary evidence is the **screenshot
  inventory markdown** (`competitor-screenshot-inventory.md` + per-vendor
  `screenshots/*/README.md`) analysing what each visual/figure on the source
  pages demonstrates (fields, buttons, tabs, workflow step, status/log surfaces,
  UX). Actual binary image capture is **attempted only where practical and
  high-value**; where impractical (JS-gated, heavy, or auth-gated) it is recorded
  as "no file saved" with the reason — the analysis (not the file's existence) is
  the deliverable. No authentication wall is bypassed to obtain any visual.
- **Files to update:** (research) `competitor-deep-dives.md`,
  `competitor-feature-matrix.md`, `ux-ui-benchmark.md`, `common-patterns.md`,
  `best-in-class-observations.md`, `gaps-opportunities.md`, `avoid-list.md`,
  `resource-inventory.md`, `research-handoff.md`; (source materials)
  `competitor-source-notes.md`, `competitor-screenshot-inventory.md`,
  `screenshots/README.md` + `screenshots/{webkul,teqstars,emipro,ventortech,odoo-apps}/README.md`;
  (QA) `defect-pattern-log.md`, `architecture-review-log.md`,
  `rejected-approaches-log.md`, `technical-debt-register.md`. **No other files.**
- **Stop condition:** All accessible sources captured + verified; blocked sources
  (R2/R5 if still gated, R4 gated children) documented without bypass; the nine
  research deliverables + source/screenshot evidence written with every claim
  cited and classified; QA logs and handoff updated; quality gate satisfied. Then
  **stop** — no MVP scope, no architecture decisions, no code, no merge.
- **Verification method:** Two-pass — topic capture, then an independent
  verification agent (and worker spot-checks) re-reading the canonical source for
  the highest-stakes claims; any figure/feature not literally supported on the
  page is downgraded to **open question / vendor claim**, never asserted as fact
  (reuses the DP-001 verification-pass gate).
- **How unsupported claims will be prevented:** Strict claim classification on
  every line (Fact / Competitor claim / Inference / Open question — `CLAUDE.md`
  §8); vendor capability statements stay **competitor claims** unless a concrete
  documented workflow/screenshot demonstrates them (then **visible demonstrated
  workflow**); blocked/unknown is stated as such; no hidden-feature guessing; no
  competitor claim is promoted to a Tier-1 fact (those come only from the existing
  official baselines).

---

# Research Sprint B Handoff

> **Research Sprint B — Dedicated Branch Setup + Source Access Validation +
> Official Shopify/Odoo Baseline.** Research-only; no-code gate in force
> (`CLAUDE.md` §5). Maps to backlog items **RB-01.1** (source validation),
> **RB-05.1** (official Shopify notes), **RB-06.1** (official Odoo notes), and
> **seeds RB-14** architecture questions.

## Session summary

Established the **dedicated project integration branch** (corrected by ChatGPT to
**`Shopify-connector`** — see Base branch below), then produced a controlled
**Tier-1 research baseline**: re-validated access for the 8 competitor resources;
created the **official Shopify API** and **official Odoo 19 architecture** notes
(every factual claim cited to an exact official URL, accessed 2026-06-30, with
**Fact / Inference / Open question** labels and a clear "constraints are
inferences, not decisions" boundary); captured supporting excerpts under
`docs/00-source-materials/`; and seeded **seven evidence-pending architecture
questions** (AR-002…AR-008, all "Not decided"). **No connector code, no Odoo
module, no competitor deep dives, no MVP scope, and no architecture decisions**
were produced — all gated. Facts were gathered topic-by-topic and then
**independently verified** on the highest-stakes pages (rate limits, versioning,
webhooks, Odoo security/manifest).

## Branch and commits

**Working branch:** `research/sprint-b-source-access-official-baseline` (based on
`Shopify-connector` @ `a5d4543`, the merged PR #49 governance foundation).

| Hash | Message |
| --- | --- |
| `54bd6f1` | docs: sprint b governance checkpoint and branch setup |
| `d05ab49` | docs: validate initial source access |
| `468efb6` | docs: add official shopify api baseline |
| `08b4c75` | docs: add official odoo architecture baseline |
| `21c460b` | docs: seed architecture research questions |
| _(this commit)_ | docs: finalize research sprint b handoff |

## Base branch and PR target

- **Dedicated project integration branch: `Shopify-connector`.** The original
  Sprint B prompt named `dev/Shopify-connector`; that branch **cannot exist on
  the remote** because a plain `dev` branch already exists (Git directory/file
  ref conflict — the push was rejected with `directory file conflict`). The
  blocker was reported, **not** worked around. **ChatGPT corrected the policy** to
  use the existing **`Shopify-connector`** branch; plain `dev` was left untouched.
- Before acting, verified `origin/Shopify-connector` was at the old `68007a9`,
  had **no** unique commits beyond `origin/main`, and was a clean fast-forward; it
  was **fast-forwarded to `origin/main` `a5d4543` and pushed normally (no force)**.
- **PR target: `Shopify-connector`** — **not** `main`, **not** plain `dev`, **not**
  `dev/Shopify-connector`. **`main` was not modified; plain `dev` was not modified.**

## Files created or updated

- `docs/00-source-materials/source-access-notes.md` (new) — per-resource access
  evidence for the 8 sources.
- `docs/01-research/resource-inventory.md` (updated) — Sprint B re-validation
  section + unblock decisions for ChatGPT.
- `docs/01-research/shopify-official-api-notes.md` (new) — Tier-1 Shopify baseline.
- `docs/00-source-materials/shopify-official.md` (new) — captured Shopify excerpts.
- `docs/01-research/odoo-official-architecture-notes.md` (new) — Tier-1 Odoo 19
  baseline.
- `docs/00-source-materials/odoo-official.md` (new) — captured Odoo excerpts.
- `docs/05-qa/architecture-review-log.md` (updated) — seeded AR-002…AR-008
  (evidence-pending only).
- `docs/05-qa/defect-pattern-log.md` (updated) — DP-001 (prevented stale-figure
  issue) + occurrence counter.
- `docs/01-research/research-handoff.md` (this file).

## Source access results

No status changed from Sprint A (both checked 2026-06-30; no auth bypassed).
**Accessible (5):** R1 Webkul, R3 Emipro, R6 ecommerce_shopify, R7 VentorTech
site, R8 sh_shopify_connector. **Partial (1):** R4 VentorTech Confluence
(anonymous-access banner; child pages to test individually). **Blocked (2):** R2
Teqstars 19.0 (HTTP 403 bot-block — needs an alternate fetch UA, or a ChatGPT
decision on the non-equivalent 16.0 mirror), R5 Google Doc (login wall — needs
owner-granted access or export). Full evidence:
`docs/00-source-materials/source-access-notes.md`.

## Shopify official facts captured

GraphQL Admin API is the primary API (REST legacy since 2024-10-01; new public
apps GraphQL-only from 2025-04-01); quarterly date-based versioning (`YYYY-MM`,
min 12-month support, ≥9-month overlap, fall-forward); OAuth + token-exchange,
online/offline/session tokens, least-privilege scopes, protected customer data
(60-day order window / `read_all_orders` approval); rate limits (REST 40/2
standard, 400/20 Plus; GraphQL calculated-cost restore 100/200/1000/2000 pts/s,
1000-point single-query cap) and the query-cost model; bulk operations (async
JSONL, concurrency change at 2026-01); webhooks (HMAC-SHA256 on raw body,
**8 retries/4h**, auto-delete after 8 failures, **delivery not guaranteed →
reconciliation required**, mandatory compliance webhooks); products/variants
(2048-variant model, `productSet` delete-on-omit); inventory (variant→item→level→
location, `committed` read-only, `@idempotent` from 2026-04); orders; fulfillment
(FulfillmentOrder-based, legacy unsupported since 2022-07); refunds/returns;
transactions (gateway-agnostic) vs payouts (Shopify Payments only); App Store /
Built-for-Shopify readiness. Full notes + citations:
`docs/01-research/shopify-official-api-notes.md`.

## Odoo official facts captured

Module/manifest structure (`name` only required key; full key list); modularity
via `depends` + `auto_install` link modules; ORM extension (in-place `_inherit`
preferred; `_inherits` delegation discouraged; `@api.model_create_multi`,
`@api.ondelete`, always `super()`); security (`ir.model.access.csv` deny-by-
default, `ir.rule` global=intersect/group=unify, field `groups`, `sudo()`/
superuser bypass); **`ir.cron` is the only documented background primitive**
(poll-based, `--max-cron-threads` default 2; failure rules 3-consecutive /
5-over-7-days→deactivate); **no official built-in job queue — `queue_job` is
community (Open question)**; external IDs / `ir.model.data` (binding-key
inference); performance (prefetch, N+1 → `_read_group`, batch `create`, selective
indexes); testing (`TransactionCase`, `HttpCase`/tours, tags); upgrade scripts
(`migrations/$version/{pre,post,end}`); logging (`ir.logging`/CLI, **no built-in
metrics — Open question**); Odoo.sh deployment (worker/time/memory limits;
**crons disabled on staging/dev**). Full notes + citations:
`docs/01-research/odoo-official-architecture-notes.md`.

## Inferences and constraints, not decisions

The "Architecture constraints implied by …" sections in both baselines are
**inferences only**, and AR-002…AR-008 are **evidence-pending, not decided**.
Key framing (not choices): a new public-app connector effectively needs GraphQL;
webhooks cannot be the sole source of truth (need reconciliation + idempotency);
background sync on stock Odoo is `ir.cron`-bound (queue_job is an explicit
dependency question); modular addon family over a giant module; external IDs as a
candidate binding key; inventory `committed` is order-driven; fulfillment must use
FulfillmentOrder mutations. **None of these is a decision.**

## Open questions

Carried into the baselines and AR rows: REST sunset / GraphQL-only scope for
custom apps; per-plan GraphQL bucket size & throttle error shape; connection-cost
formula; current max product options; REST product/fulfillment deprecation dates;
payout scope string; Pub/Sub & EventBridge retry semantics. Odoo: whether any
official job queue exists beyond `ir.cron`; `ir.cron`/`ir.model.data`/`ir.logging`
field schemas; manifest defaults; `create`-override signature; `read_group`
deprecation; Odoo.sh per-stage quotas; built-in metrics. **Source unblocks for
ChatGPT:** R2 Teqstars (alternate fetch vs 16.0 mirror) and R5 Google Doc (owner
access/export).

## Risks

Commonly-cited API numbers can be stale (see DP-001); version-independent Shopify
policy can drift without a version bump; `productSet` delete-on-omit is a
data-loss footgun; webhook-only designs risk silent drift; treating `ir.cron` as
a job queue (or assuming `queue_job` is core) is a design trap; some JS-rendered
Odoo pages required RST-source recovery (re-verify load-bearing wording).

## Learning feedback loop

- **New issues discovered:** one — **DP-001** (incorrect Shopify API assumption,
  #6): commonly-cited/training-data API figures were **stale vs current official
  docs** (webhook "19/48h" → actual 8/4h; REST Plus "80" → 400; `/rate-limits`
  moved to `/limits`, now GraphQL-only). **Prevented** by the independent
  verification pass.
- **Repeated issue patterns:** none at threshold — DP-001 is the **1st**
  occurrence of category #6 (counter updated; no 2×/3× escalation).
- **Rules/checklists updated:** added the DP-001 **prevention rule** — for
  high-stakes numeric/policy API facts, re-read and cite the **exact** official
  page; if a figure is not literally on the page, mark it **Open question**, never
  assert a remembered/forum figure. The **independent-verification-pass** gate is
  now the recommended method for future official-API research (RB-05/RB-06-style).
- **New rejected approaches:** none (research-only; no approaches evaluated to
  rejection — `rejected-approaches-log.md` unchanged).
- **New technical debt:** none (no code; blocked sources R2/R5 are research gaps,
  not debt — `technical-debt-register.md` unchanged).
- **Architecture concerns:** captured as **AR-002…AR-008 (evidence-pending)**, not
  decisions; the big ones are sync orchestration (cron vs webhook+reconciliation
  vs queue) and duplicate-prevention/binding.
- **Tests or review gates needed:** none active (research phase). For future API
  research, keep the verification-pass gate. The connector-side test stance
  (`TransactionCase` for mapping, `HttpCase`/tours for webhooks/UI) is recorded in
  the Odoo notes for the implementation phase.
- **Should future prompts change? Yes** — official-API research prompts should
  explicitly require an **independent verification pass** on high-stakes numeric
  facts and the "mark Open question if not literally on the page" rule (now
  encoded via DP-001). Also: the branch-policy reality is **`Shopify-connector`**
  (not `dev/Shopify-connector`), which future Sprint prompts should state.

**Revision patch (ChatGPT REVISE — branch policy + high-power research rules):**

- Branch policy was promoted into permanent governance files: `Shopify-connector`
  is the dedicated integration branch; `main` and plain `dev` remain untouched
  unless explicitly approved.
- New issue discovered: high-power research fan-out needs a persistent governance
  rule so large Claude workflows remain intentional, scoped, synthesized, and
  reviewable.
- Category: token waste (#17) / unclear handoff, first occurrence (logged as
  **DP-002**, Mitigated).
- Prevention rule: high-power research mode is allowed and encouraged for major
  research and architecture work, but the fan-out plan, workstreams, sources,
  stop condition, synthesis method, and verification method must be documented.
- **This rule does not limit Claude's capabilities.** It is a *capability,
  not a cap* — there is **no** fixed agent/token limit. Claude is expected to use
  maximum capability when justified to produce a top-tier, state-of-the-art
  connector; the only requirement is that large research be intentional, scoped
  to allowed files, documented, and reviewable (and that small patch sessions
  stay lightweight).
- Rules/checklists updated in this patch: `CLAUDE.md` (new **Branch governance**
  and **High-power research mode** sections), `README.md` (branch-governance +
  high-power research summary), `docs/06-prompts/claude-learning-rules.md`
  (pre-session checklist item 8 + High-power research mode section),
  `docs/06-prompts/claude-session-prompts.md` (default branch policy + High-power
  research mode in the standard preamble and as a section),
  `docs/05-qa/pr-review-checklist.md` (branch-target + capability-use checks),
  `docs/05-qa/defect-pattern-log.md` (DP-002 reframed + counter), and this
  handoff.

## What ChatGPT should review

1. **Branch governance** — confirm `Shopify-connector` is the intended dedicated
   integration branch and that leaving plain `dev` untouched is correct.
2. **Citation/classification rigor** — spot-check that Shopify/Odoo facts cite
   exact official URLs and that constraints are labelled inference, not decision.
3. **High-stakes facts** — the rate-limit, versioning, and webhook numbers
   (incl. the corrected 8-retries/4-hours and REST-Plus-400), and the Odoo
   "no official job queue" finding.
4. **Open questions / unblocks** — decide R2 (Teqstars alternate fetch vs 16.0
   mirror) and R5 (Google Doc access/export).
5. **AR-002…AR-008** — confirm these are the right architecture questions to
   carry (still evidence-pending), and which to prioritise for RB-14.
6. **DP-001 + verification gate** — endorse making the independent-verification
   pass a standing rule for API research.

## Recommended next session

With Tier-1 baselines in place, proceed to **competitor deep dives**
(`RB-02.1 Webkul`, `RB-02.3 Emipro`, `RB-02.5 Odoo Apps listings` — all
unblocked), running **RB-12 feature taxonomy** early for grounding, and revisit
**R2/R5** once ChatGPT decides the unblock path. Keep the no-code gate; one scoped
session per deep dive; follow `research-methodology.md` §11.

## Stop confirmation

Stopped at the Sprint B boundary as instructed: working branch pushed, **one
draft PR** opened targeting **`Shopify-connector`**, **not merged**. **No** code,
**no** Odoo module, **no** competitor deep dives, **no** MVP scope, **no**
architecture decisions. `main` and plain `dev` untouched. Awaiting ChatGPT review.

---

# Research Sprint A Handoff (history)

> Continuity record for **Research Sprint A — Governance, Research Workspace,
> Source Inventory, and Research Backlog.** Continuity lives in GitHub, not chat.
> The running **Sprint checkpoint log** (one note per stage) is at the bottom.

## ChatGPT review decision (Research Sprint A)

> ChatGPT review decision: Research Sprint A is the canonical governance
> foundation after this revision patch is accepted. The earlier branch
> `claude/odoo-shopify-research-setup-fs4wzi` is non-canonical and must not be
> used unless ChatGPT explicitly reopens it.

The Sprint A review returned **REVISE — small governance patch required before
merge.** This patch addresses those findings (modular addon-family wording,
canonical research output filenames, feature-taxonomy sequencing, the
non-canonical-branch warning, and this learning-loop update). See the
revision-patch entry at the bottom of the checkpoint log and the updated
**Learning feedback loop** section below.

## Session summary

Research Sprint A established the GitHub-based **governance and research
foundation** for the premium Odoo 19 ↔ Shopify Connector project, so ChatGPT
can review the repo directly and direct the next sprint. Work was done in six
documentation-only stages on a clean branch off `main`: workspace setup →
governance contract & templates → learning feedback loop → research workspace
(inventory, methodology, backlog) → placeholder READMEs → finalization. **No
connector code, no Odoo module, and no forbidden files were created.** No
competitor deep dives, MVP finalization, or architecture decisions were made —
those are explicitly out of scope and gated.

## Branch and commits

**Branch:** `docs/research-sprint-a-governance-inventory` (based on `origin/main`
@ `68007a9`).

| Hash | Message |
| --- | --- |
| `2e4c276` | docs: create connector governance workspace |
| `d143086` | docs: add governance and review templates |
| `1aba406` | docs: add quality feedback loop |
| `f4f3e7d` | docs: add research inventory and backlog |
| `8aa536b` | docs: add product architecture and claude placeholders |
| _(final)_ | docs: finalize research sprint a handoff |

## Files created or updated

**Root governance**
- `CLAUDE.md` (new) — governance contract (roles, source-of-truth,
  research-first, no-code-until-approved, scoped sessions, citation rules, claim
  classification, future implementation-task requirements, allowed/forbidden
  files, do-not-repeat-rejected rule, mandatory handoff).
- `AGENTS.md` (new) — six **proposed** future agents, marked proposed only.
- `README.md` (updated) — preserved existing content; added the project
  workspace map.

**Research (`docs/01-research/`)**
- `resource-inventory.md`, `research-methodology.md`, `research-backlog.md`,
  `research-handoff.md` (this file).

**QA / quality memory (`docs/05-qa/`)**
- `quality-feedback-loop.md`, `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md`, `pr-review-checklist.md`.

**Prompts/templates (`docs/06-prompts/`)**
- `claude-session-prompts.md`, `claude-learning-rules.md`,
  `implementation-task-template.md`, `pr-review-template.md`,
  `session-handoff-template.md`.

**Decisions** — `docs/04-decisions/decision-record-template.md` + `README.md`.

**Placeholder READMEs** — `docs/00-source-materials/README.md`,
`docs/02-product`, `docs/03-architecture`, `docs/07-implementation-plan`,
`docs/08-release-readiness`, and `.claude`, `.claude/skills`, `.claude/agents`.

## What changed

The repository went from a bare Odoo SH scaffold (`addons/adams_base`,
`README.md`, `.gitignore`) to a full **research/governance workspace**: a
governance contract, a learning feedback loop with four logs, a research
methodology, a registered source inventory of 8 resources, a 14-section research
backlog, and review/handoff/decision templates — all documentation. The Odoo
addon scaffold under `/addons` was left untouched.

## Evidence and citations added

Initial **access status** for the 8 sources was verified on **2026-06-30** (no
auth bypass): **Accessible** — Webkul (R1), Emipro (R3), Odoo Apps
ecommerce_shopify (R6), VentorTech website (R7), Odoo Apps sh_shopify_connector
(R8); **Partial** — VentorTech Confluence (R4, anonymous-access banner);
**Blocked** — Teqstars docs (R2, HTTP 403 bot-block, not a login wall), project
Google Doc (R5, login wall). On-page pricing recorded as facts-on-date: R6
$195.56 (OPL-1), R8 $168.81 (OPL-1), R7 EUR 499. No detailed feature claims were
asserted — only registration/triage. Full detail in `resource-inventory.md`.

## Assumptions

- The connector must be **isolated from `adams_base`/customer code**; its final
  structure may be a **modular connector addon family** under `/addons` — exact
  module boundaries are **not final** and will be validated through research +
  architecture review. `adams_base` is unrelated company/base code (inference
  from repo layout + README).
- "Initial value" / "Evidence strength" in the inventory are **triage
  inferences**, not vendor facts.
- The default research order in the backlog is reasonable but adjustable once
  blocked sources are resolved.

## Open questions

- R2 Teqstars: will an alternate fetch (different UA / browser / cache) work, or
  is the 16.0 doc the fallback?
- R5 Google Doc: can the owner grant view access or provide an export? What is
  its actual content?
- R6 ecommerce_shopify: is the listing Odoo S.A. official or a partner module
  (author shown as "Odoo IN Pvt Ltd")?
- R4 VentorTech Confluence: which child pages/screenshots require login?

## Risks

- **Access risk:** two blocked + one partial source could delay specific deep
  dives (RB-02.2, RB-02.6); the backlog isolates these so they don't stall the
  rest.
- **Source bias:** all 8 sources are vendor-published; technical facts must come
  from official Shopify/Odoo docs (RB-05, RB-06), not competitor claims.
- **Scope creep risk:** strong guardrails (allowed/forbidden files, no-code
  gate) are in place; future sessions must honour them.
- **Pricing/feature drift:** vendor pages change; deep dives must re-date and
  capture excerpts.

## Learning feedback loop

- **New issue discovered:** Governance wording could **bias Claude toward one
  giant connector addon/module** — the "self-contained addon" phrasing in
  `CLAUDE.md` §9 and `README.md`. Surfaced by ChatGPT's Sprint A review (REVISE).
- **Category:** premature architecture / weak modularity (first occurrence;
  count = 1).
- **Repeated issue patterns:** None — this is the first occurrence of this
  category; no escalation threshold reached.
- **Prevention rule:** Use **"modular connector addon family"** language and
  state that exact module boundaries are **not final** until validated through
  research + architecture review; never imply a single giant module. Keep the
  isolation-from-`adams_base`/customer-code rule.
- **Rules/checklists updated:** (1) `CLAUDE.md` §9 and `README.md` reworded to
  the modular-family principle; (2) `research-backlog.md` and
  `claude-session-prompts.md` updated to the canonical research output filenames,
  single-file competitor deep dives (`competitor-deep-dives.md`), and the
  provisional→canonical feature-taxonomy sequencing rule; (3)
  `architecture-review-log.md` row **AR-001** added recording this branch as the
  canonical foundation. (No `defect-pattern-log.md` row: this was a pre-merge
  review finding on governance docs, not a shipped defect — captured here and in
  the architecture-review log.)
- **New rejected approaches:** None logged formally; the "one giant connector
  module" bias is prevented by wording. Revisit/log if it recurs.
- **New technical debt:** None.
- **Architecture concerns:** Module-boundary design is explicitly **deferred**
  to research + architecture review (RB-06, RB-14); do not pre-decide it.
- **Tests or review gates needed:** None active in the research phase; the
  implementation checklist (section C) is staged for later.
- **Should future prompts change? Yes/No:** **Yes** — prompt templates now use
  the canonical research output filenames and the modular-family wording, and
  encode the provisional→canonical taxonomy sequencing.
- **Final cleanup:** removed remaining "self-contained addon" wording from
  implementation-phase governance templates so future implementation prompts
  preserve modular addon-family language. Files updated:
  `docs/05-qa/pr-review-checklist.md` (§C) and
  `docs/06-prompts/implementation-task-template.md`.

## What ChatGPT should review

1. **Governance correctness** — does `CLAUDE.md` capture the intended
   Claude/ChatGPT operating model, gates, and claim-classification scheme?
2. **Learning loop sufficiency** — are the escalation thresholds (2×/3×), issue
   taxonomy, and log schemas adequate to prevent repeated mistakes?
3. **Research methodology** — is the source hierarchy, claim classification, and
   extraction method rigorous enough for trustworthy deep dives?
4. **Resource inventory** — accuracy of access triage; is the
   official-vs-partner provenance flag for R6 handled correctly?
5. **Research backlog** — are sequencing, dependencies, and acceptance criteria
   right? Anything missing before deep dives start?
6. **Proposed agents** — approve/adjust the six proposed agents (still inactive).
7. **Blocked sources** — decide the unblock path for R2 (Teqstars) and R5
   (Google Doc) before their backlog items.

## Recommended next session

**RB-01.1 — Validate and unblock sources** (resolve R2/R5 access), then begin
deep dives with **RB-02.1 — Webkul** (accessible, no blockers). Run
`RB-12` (feature taxonomy) early and `RB-05`/`RB-06` (official Shopify/Odoo
notes) in parallel. Use the prompts in `docs/06-prompts/claude-session-prompts.md`.

## Stop confirmation

Stopped at the Research Sprint A boundary as instructed: branch pushed, one
**draft** PR opened for ChatGPT review, not merged. **No** deep competitor
research, **no** architecture, **no** implementation was started. Awaiting
ChatGPT review.

## Sprint self-review

- **Scope respected:** Yes — governance/research documentation only.
- **No coding performed:** Yes — no `.py`/`.xml`/`.csv`, no module, no manifest.
- **Forbidden files untouched:** Yes — forbidden-pattern scan clean; `addons/`
  untouched (verified via `git diff --name-only origin/main`).
- **Research inventory complete:** Yes — all 8 resources registered with the
  required schema and verified access status.
- **Governance files complete:** Yes — CLAUDE.md, AGENTS.md, README, templates,
  checklist.
- **Learning loop complete:** Yes — feedback-loop doc + four logs + learning
  rules.
- **Handoff updated:** Yes — this file (all required sections + checkpoint log).
- **Ready for ChatGPT review:** Yes — draft PR opened.

---

## Sprint checkpoint log

> One short note per stage (most recent last).

- **Stage 1 — Repo inspection & safe setup (2026-06-30):** Confirmed remote
  default branch is `main` at `68007a9` (clean Odoo scaffold:
  `addons/adams_base`, `README.md`, `.gitignore`; no `docs/`, no `CLAUDE.md`).
  Created the clean branch `docs/research-sprint-a-governance-inventory` from
  `origin/main` (deliberately not from the prior research branch, so this PR
  contains exactly this governance foundation). Created the `/docs/00..08` and
  `/.claude/{skills,agents}` directory structure. No code touched. Next: Stage 2
  governance files.
- **Stage 2 — Governance files (2026-06-30):** Created `CLAUDE.md` (roles:
  Claude=execution/research/docs worker, ChatGPT=strategy/control-room/reviewer;
  GitHub source-of-truth; research-first; no-code-until-approved; small scoped
  sessions; mandatory handoff; citation rules; the fact/competitor-claim/
  inference/recommendation/decision/open-question classification; future
  implementation-task requirements incl. allowed/forbidden files, acceptance
  criteria, tests, rollback, definition of done; and the hard do-not-repeat-
  rejected-approaches rule). Created `AGENTS.md` listing six **proposed** agents
  (competitor-research, shopify-api-research, odoo-architecture-research,
  ux-benchmark, qa-review, prompt-control) — none active. Updated `README.md`
  (preserved existing title/description; added the project workspace map).
  Added `decision-record-template.md`, `pr-review-checklist.md`,
  `implementation-task-template.md`, `pr-review-template.md`, and
  `session-handoff-template.md`. Docs only; no forbidden files. Next: Stage 3
  learning feedback loop.
- **Stage 3 — Learning feedback loop (2026-06-30):** Created
  `quality-feedback-loop.md` (review-decision categories; 17-type issue
  taxonomy; 2×→update-rule / 3×→pause-implementation escalation; concrete-lesson
  rule; end-of-session review; quality + acceptance gates; routing table) and
  the four logs with the exact required columns — `defect-pattern-log.md`,
  `architecture-review-log.md`, `rejected-approaches-log.md`,
  `technical-debt-register.md` (all initialized empty with instructions). Created
  `claude-learning-rules.md` with the mandatory 7-item pre-session checklist
  (previous handoff, defect log, rejected log, architecture-review log, decision
  records, current phase, allowed/forbidden files). Next: Stage 4 research
  workspace + source inventory.
- **Stage 4 — Research workspace + source inventory (2026-06-30):** Created
  `00-source-materials/README.md` (capture rules; empty until deep dives).
  Created `resource-inventory.md` registering all 8 sources with the required
  schema (ID, name, URL, source type, competitor/category, initial value,
  evidence strength, current access status, what-to-extract-later, open
  questions, notes); access verified 2026-06-30 (5 Accessible, 1 Partial — R4
  VentorTech, 2 Blocked — R2 Teqstars 403/bot-block & R5 Google Doc login);
  Google Doc marked private/user-provided/access-dependent; no detailed feature
  claims asserted. Created `research-methodology.md` (source hierarchy; citation;
  competitor-evidence; claim-classification; screenshot/pricing/feature/UX/
  reliability/technical-risk extraction; deep-dive procedure; MVP/Phase2/Advanced/
  Optional/Avoid disposition rules). Created `research-backlog.md` (14 sections,
  RB-01..RB-14, each item with Objective/Inputs/Output file/Acceptance criteria/
  Dependencies/Status + sequencing). Next: Stage 5 placeholder READMEs.
- **Stage 5 — Placeholder READMEs (2026-06-30):** Created concise READMEs for
  `docs/02-product`, `docs/03-architecture`, `docs/04-decisions`,
  `docs/07-implementation-plan`, `docs/08-release-readiness`, and `.claude`,
  `.claude/skills`, `.claude/agents` — each stating purpose, what belongs, what
  does not belong yet, and current status. The `.claude/skills` and
  `.claude/agents` READMEs explicitly recommend **deferring** active skills/
  agents until the research workflow stabilizes (premature automation may encode
  weak assumptions). Next: Stage 6 final self-review, handoff, push, draft PR.
- **Stage 6 — Final self-review, handoff, push, draft PR (2026-06-30):** Added
  `claude-session-prompts.md` to complete the prompt library (whitelisted file;
  goal #7). Ran final checks: `git diff --name-only origin/main` shows only
  allowed docs/governance files; forbidden-pattern scan clean; `addons/`
  untouched. Filled all required handoff sections + the sprint self-review.
  Pushed the branch and opened one **draft** PR for ChatGPT review. Stopped.
- **Revision patch — address Sprint A review findings (2026-06-30):** ChatGPT
  returned **REVISE**. Applied a small governance patch to the same branch /
  PR #49 (no new PR, no merge): (1) replaced "self-contained addon" wording in
  `CLAUDE.md` §9 and `README.md` with the **modular connector addon family**
  principle (kept the isolation rule); (2) aligned future research output
  filenames in `research-backlog.md` and `claude-session-prompts.md` to the
  canonical names and consolidated competitor deep dives into one file
  `competitor-deep-dives.md` with per-competitor sections; (3) added the
  **provisional→canonical** feature-taxonomy sequencing rule (first 1–2 deep
  dives may use provisional groups; RB-12 normalizes); (4) added the
  non-canonical-branch warning + AR-001 in `architecture-review-log.md`; (5)
  updated this Learning feedback loop. Allowed files only; no code touched.
  **Deferred follow-up:** `docs/05-qa/pr-review-checklist.md` (§C) and
  `docs/06-prompts/implementation-task-template.md` still contain the phrase
  "self-contained addon"; both are **outside this patch's allowed-files scope**,
  so the reword to "modular connector addon family" is deferred to a future
  ChatGPT-approved patch rather than edited out of scope here. **(Resolved in the
  final cleanup patch — both files reworded.)**

### Research Sprint B checkpoints

- **Sprint B / Stage 0 — Dedicated branch setup + governance correction
  (2026-06-30):** Started Research Sprint B (research-only; no-code gate
  confirmed via `CLAUDE.md` §5; allowed/forbidden files reconfirmed). The
  original Sprint B prompt named `dev/Shopify-connector` as the dedicated project
  integration branch. **Blocker (fact):** that branch cannot be created on the
  remote — a plain `dev` branch already exists, and Git cannot hold both `dev`
  and `dev/Shopify-connector` (a directory/file ref conflict; the push was
  rejected with `directory file conflict`). The blocker was reported, not
  worked around (no `dev` deletion, no force-push). **ChatGPT branch-policy
  correction (decision, by ChatGPT):** use the existing remote branch
  **`Shopify-connector`** as the dedicated project integration branch; leave
  plain `dev` untouched; do not use `dev/Shopify-connector` or
  `dev-Shopify-connector`. Sprint branches now branch from `Shopify-connector`
  and Sprint PRs target `Shopify-connector` (not `main`, not `dev`). Verified
  before acting: `origin/Shopify-connector` was at the old commit `68007a9`, had
  **no** unique commits beyond `origin/main` (empty `main..Shopify-connector`),
  and `68007a9` is a direct ancestor of `origin/main` (clean fast-forward). Then
  fast-forwarded `Shopify-connector` to `origin/main` `a5d4543` (the merged PR
  #49 Sprint A governance foundation) and pushed normally (`68007a9..a5d4543`,
  no force). All seven governance-foundation files are present on the branch.
- **Sprint B / Stage 1 — Pre-session governance check (2026-06-30):** Read
  `CLAUDE.md`, this handoff, `claude-learning-rules.md`, `quality-feedback-loop.md`,
  `research-methodology.md`, `resource-inventory.md`, `research-backlog.md`.
  Confirmed: current phase is **research only**; the no-code gate applies; the
  Sprint B allowed/forbidden file lists are understood; `Shopify-connector` is
  the dedicated integration branch; the Sprint B working branch
  `research/sprint-b-source-access-official-baseline` is based on
  `Shopify-connector`; the Sprint B PR will target `Shopify-connector`; the old
  branch `claude/odoo-shopify-research-setup-fs4wzi` remains non-canonical.
  Sprint B maps to backlog items RB-01.1 (source validation), RB-05.1 (official
  Shopify notes), RB-06.1 (official Odoo notes), and seeds RB-14 architecture
  questions. Added this checkpoint note. Next: Stage 2 source validation.
- **Sprint B / Stage 2 — Source access validation (2026-06-30):** Re-ran a normal
  anonymous access check on all 8 resources (no auth bypass). No status changed
  from Sprint A: 5 Accessible, 1 Partial (R4), 2 Blocked (R2 403 bot-block, R5
  login wall). Created `docs/00-source-materials/source-access-notes.md`
  (per-resource: date, URL, result, visible sections, block reason, unblock
  action, extraction path, deep-dive readiness) and added a Sprint B
  re-validation section + ChatGPT unblock decisions to `resource-inventory.md`.
  Commit `d05ab49`. Next: Stage 3 Shopify baseline.
- **Sprint B / Stage 3 — Official Shopify API baseline (2026-06-30):** Created
  `docs/01-research/shopify-official-api-notes.md` (all required sections; every
  fact cited to an exact shopify.dev URL + access date; Fact/Inference/Open
  question labelled; "Architecture constraints implied" marked inference, no
  decisions) and `docs/00-source-materials/shopify-official.md` (captured
  quotes/paraphrases). Reconciled the verification pass: REST limits cited to the
  REST-specific page (40/2 std, 400/20 Plus), general `/usage/limits` is now
  GraphQL-only; webhook retry corrected to 8/4h. Commit `468efb6`. Next: Stage 4
  Odoo baseline.
- **Sprint B / Stage 4 — Official Odoo 19 baseline (2026-06-30):** Created
  `docs/01-research/odoo-official-architecture-notes.md` (all required sections;
  every fact cited to an exact odoo.com/19.0 URL; queue/async marked Open question
  — only `ir.cron` is official, `queue_job` is community; constraints marked
  inference, no decisions) and `docs/00-source-materials/odoo-official.md`. Commit
  `08b4c75`. Next: Stage 5 architecture seeds.
- **Sprint B / Stage 5 — Architecture review seeds (2026-06-30):** Added
  AR-002…AR-008 to `architecture-review-log.md` (API strategy, sync orchestration,
  module boundaries, mapping/dedup, error handling/retries, inventory,
  fulfillment) — all Review decision "Not decided", Status "Evidence pending",
  with evidence-required/risks/follow-up; updated the log's explanatory note.
  Commit `21c460b`. Next: Stage 6 handoff + learning loop.
- **Sprint B / Stage 6 — Handoff + quality loop (2026-06-30):** Wrote the full
  Sprint B handoff (above) with the learning feedback loop; logged **DP-001**
  (prevented stale-figure issue, category #6, Mitigated) and updated the
  occurrence counter in `defect-pattern-log.md`; `rejected-approaches-log.md` and
  `technical-debt-register.md` left unchanged (none warranted). Ran the
  end-of-session quality gate (all items satisfied). Next: push branch, open one
  draft PR targeting `Shopify-connector`, then stop.

### Research Sprint C checkpoints

- **Sprint C / Stage 1 — Setup + high-power plan (2026-06-30):** Started Research
  Sprint C (research-only; no-code gate confirmed via `CLAUDE.md` §5; high-power
  mode **explicitly authorized** in the prompt). Fetched remote branches and
  verified preconditions: **PR #50 is merged into `Shopify-connector`** (the
  branch tip `d6fbcdb` *is* the PR #50 merge commit), the working branch is based
  on `Shopify-connector` (identical to it at start), and all seven required files
  are present. **Branch-name note (flagged for ChatGPT):** the harness designated
  the working branch **`claude/research-sprint-c-competitors-hgoo8t`** (already
  checked out, based on `Shopify-connector`), whereas the Sprint C prompt body
  named `research/sprint-c-competitor-deep-dives-ux-evidence`; per the
  session's hard git rule ("never push to a different branch without explicit
  permission") the work proceeds on the harness-designated branch and the **PR
  still targets `Shopify-connector`** — `main`/`dev` untouched. Read the required
  governance/research files (CLAUDE.md, this handoff, learning rules, methodology,
  resource inventory, backlog, both official baselines, all QA logs). Wrote the
  **Sprint C high-power research plan** (above) and committed it. Next: Stage 2
  source + screenshot evidence capture (controlled parallel fan-out).
- **Sprint C / Stage 2 — Source + screenshot evidence (2026-06-30):** Ran the
  documented capture→verify fan-out (16 agents, 137 tool calls) over R1–R8;
  verified each source adversarially. Wrote `competitor-source-notes.md`,
  `competitor-screenshot-inventory.md`, and the `screenshots/` READMEs (root +
  webkul/teqstars/emipro/ventortech/odoo-apps); updated `resource-inventory.md`
  with Sprint C access changes (**R2 docs still 403-blocked but Teqstars Apps
  listing accessible; R5 = R6's setup guide; pricing resolved**). No binaries saved
  (proxy returns markdown/alt-text; sprint rule allows the fallback). No auth
  bypassed. Commit `e1c5ec4`. Next: Stage 3 deep dives.
- **Sprint C / Stage 3 — Competitor deep dives (2026-06-30):** Wrote
  `competitor-deep-dives.md` — six competitors (Webkul, Teqstars, Emipro,
  VentorTech, ecommerce_shopify, sh_shopify_connector) + a blocked-source record
  for the Google Doc; each with feature classification, workflow reconstruction,
  UX, reliability, maintenance, strengths/weaknesses, learn/do-better/avoid, open
  questions; verifier downgrades reflected (R2→Blocked, EC→cron, SH multi-company→
  not-found). Commit `1e027a0`. Next: Stage 4 matrix + UX benchmark.
- **Sprint C / Stage 4 — Matrix + UX benchmark (2026-06-30):** Wrote
  `competitor-feature-matrix.md` (grouped tables, per-cell ✅/🟨/⬜/🚫/🔒 symbols +
  evidence notes + implications) and `ux-ui-benchmark.md` (evidence base, per-area
  comparisons, best patterns, gaps, principles — benchmark only, no UI designed).
  Commit `da93ba9`. Next: Stage 5 synthesis.
- **Sprint C / Stage 5 — Patterns/best-in-class/gaps/avoid (2026-06-30):** Wrote
  `common-patterns.md`, `best-in-class-observations.md`, `gaps-opportunities.md`
  (candidate/later/unknown MVP relevance — not finalized), `avoid-list.md` (each
  item with evidence/risk/prevention/arch-review flag). Updated QA logs:
  **DP-003** + counter (`defect-pattern-log.md`); a non-decision competitor-
  evidence note (`architecture-review-log.md`); avoid-list-is-not-rejection note
  (`rejected-approaches-log.md`); Sprint C no-debt note
  (`technical-debt-register.md`). Commit `890ce0b`. Next: Stage 6 handoff + PR.
- **Sprint C / Stage 6 — Handoff + quality loop (2026-06-30):** Wrote the full
  Sprint C handoff (above) with the learning feedback loop (DP-003; external
  DP-001 confirmation; future-prompt updates) and the quality-gate confirmation
  (all items satisfied). Ran final allowed/forbidden-file checks. Next: push the
  working branch and open one draft PR targeting `Shopify-connector`, then stop.

### Research/Product Sprint D checkpoints

- **Sprint D / Stage 1 — Setup + evidence read (2026-07-01):** Started
  Research/Product Sprint D (canonical feature taxonomy + capability evidence
  map). Research/synthesis-only; **no-code gate confirmed** (`CLAUDE.md` §4–§5);
  high-power mode **not required** for this sprint (focused synthesis of
  already-merged Sprint C evidence — no new competitor crawling). Fetched remote
  branches and verified preconditions: **PR #51 is merged into `Shopify-connector`**
  (branch tip `e18ba8e` *is* the PR #51 merge commit); the working branch is based
  on `Shopify-connector` (identical to it at start); all required Sprint C outputs
  present (`competitor-deep-dives.md`, `competitor-feature-matrix.md`,
  `ux-ui-benchmark.md`, `common-patterns.md`, `best-in-class-observations.md`,
  `gaps-opportunities.md`, `avoid-list.md`, `competitor-source-notes.md`,
  `competitor-screenshot-inventory.md`). **Branch-name note (flagged for ChatGPT):**
  the harness designated the working branch **`claude/feature-taxonomy-sprint-d-t8d2t0`**
  (already checked out, based on `Shopify-connector`), whereas the Sprint D prompt
  body named `product/sprint-d-feature-taxonomy`; per the session's hard git rule
  ("never push to a different branch without explicit permission") the work
  proceeds on the harness-designated branch and the **PR still targets
  `Shopify-connector`** — `main`/plain `dev` untouched. Read the required
  governance/research files (CLAUDE.md, README, this handoff, learning rules,
  methodology, resource inventory, both official baselines, all Sprint C evidence,
  all QA logs). Confirmed DP-003/DP-004 prevention rules (competitor claim ≠ fact;
  configuration field ≠ demonstrated support; market promise ≠ demonstrated
  bidirectionality; ✅ requires demonstrated workflow/explicit evidence). Next:
  Stage 2 — draft the canonical feature taxonomy in `docs/02-product/feature-taxonomy.md`.
- **Sprint D / Stage 2 — Canonical taxonomy (2026-07-01):** Wrote
  `docs/02-product/feature-taxonomy.md` — the main deliverable: 20 canonical
  domains, ≈90 canonical capabilities (each with the required attribute block:
  ID/name/description/user-value/evidence-status/evidence-references/competitor-
  examples/UX/reliability/config implications/architecture-dependency/candidate-
  classification/MVP-relevance/notes), 8 cross-cutting groups, a classification
  summary, MVP-candidate + later-phase inputs (not decisions), a capabilities-
  requiring-architecture-review map to AR-002…AR-008, a weak/blocked-evidence
  register, open questions, and ChatGPT review notes. DP-003/DP-004 discipline
  applied throughout (claims stay claims; WK multi-company ➖; SH multi-company
  not-found; EC export not-found; `✅` only where demonstrated). Synthesis was
  worker-owned (no fan-out). Commit `70391b9`. Next: Stage 3 evidence map.
- **Sprint D / Stage 3 — Capability evidence map (2026-07-01):** Wrote
  `docs/02-product/capability-evidence-map.md` — compact per-capability
  traceability with evidence strength (A official / B strong-competitor / C
  mixed / D single-claim / E open-whitespace), strongest evidence, per-competitor
  coverage (WK/TQ/EM/VT/EC/SH with ✅/🟨/⬜/🚫/🔒/➖), official-platform dependency,
  architecture-review need (AR-002…AR-008), and MVP-review relevance. Grouped by
  domain for readability (no giant unreadable table). Commit `aa5d2c4`. Next:
  Stage 4 handoffs + QA loop.
- **Sprint D / Stage 4 — Product handoff + QA loop (2026-07-01):** Wrote
  `docs/02-product/product-research-handoff.md` (product-side handoff); wrote the
  full Sprint D section of this rolling handoff (above) with the learning feedback
  loop (DP-005 premature-decision risk, Mitigated) and the quality-gate
  confirmation; updated QA logs (**DP-005** + counter in `defect-pattern-log.md`;
  Sprint D non-decision note in `architecture-review-log.md`; nothing-rejected note
  in `rejected-approaches-log.md`; no-debt note in `technical-debt-register.md`).
  Ran final allowed/forbidden-file checks. Next: push the working branch and open
  one draft PR targeting `Shopify-connector`, then stop.

### Product Sprint E checkpoints

- **Sprint E / Stage 1 — Setup + evidence read (2026-07-01):** Started **Product
  Sprint E** (product vision, premium quality bar, differentiation strategy, and
  setup/UX principles). Product strategy / synthesis only; **no-code gate confirmed**
  (`CLAUDE.md` §4–§5); high-power mode **not required** (focused product synthesis of
  already-merged repo evidence — no new competitor crawling, no research fan-out).
  Fetched remote branches and verified preconditions: **PR #52 is merged into
  `Shopify-connector`** (confirmed via GitHub API — `merged: true`, merged 2026-07-01;
  branch tip `9a744f7` *is* the PR #52 merge commit); the working branch is based on
  `Shopify-connector` (identical to it at start); all required Sprint D outputs present
  (`feature-taxonomy.md`, `capability-evidence-map.md`, `product-research-handoff.md`);
  the **DP-006 evidence-consistency gate** is present in `defect-pattern-log.md`.
  **Branch-name note (flagged for ChatGPT):** the harness designated the working branch
  **`claude/sprint-e-product-strategy-gd2kfs`** (already checked out, based on
  `Shopify-connector`), whereas the Sprint E prompt body named
  `product/sprint-e-product-vision-quality-bar`; per the session's hard git rule
  ("never push to a different branch without explicit permission") the work proceeds on
  the harness-designated branch and the **PR still targets `Shopify-connector`** —
  `main`/plain `dev` untouched. Read the required governance/product/research files
  (CLAUDE.md, README, this handoff, research methodology, both official baselines,
  competitor deep dives + matrix, UX/UI benchmark, common patterns, best-in-class,
  gaps/opportunities, avoid-list, feature taxonomy, capability evidence map, product
  handoff, all QA logs, learning rules). Confirmed the phase is still **no-code**, that
  Sprint E is **product vision / strategy only** (no MVP finalization, no architecture
  finalization, no ADRs, no module boundaries), and the **DP-003/DP-004/DP-006**
  prevention + evidence-consistency rules (competitor claim ≠ fact; config field ≠
  demonstrated support; market promise ≠ demonstrated bidirectionality; conditional
  platform requirements stay conditional; improvement opportunities are inference, not
  demonstrated evidence; no capability enters MVP/architecture as a decision until
  ChatGPT-reviewed). Next: Stage 2 — draft `docs/02-product/product-vision.md`.
- **Sprint E / Stage 2 — Product vision (2026-07-01):** Wrote
  `docs/02-product/product-vision.md` — the main deliverable: status/purpose/evidence
  base, what we are building, product thesis, target personas (P1–P4, inference-level),
  core customer problems, ten product principles, premium quality bar, five-theme
  differentiation strategy, per-domain strategies (UX / reliability & correctness /
  modularity & customizability / performance / security & permissions / docs-support-
  trust), what we do better than competitors, what we avoid, seven product
  non-negotiables, and explicit **MVP / later / architecture inputs (not decisions)** +
  open questions + ChatGPT review notes. Claim labels ([Fact]/[Competitor claim]/
  [Demonstrated]/[Inference]/[Recommendation]/[Open question]) applied throughout;
  competitor claims kept as claims (EM/VT-demonstrated weighted over SH/WK/EC/TQ);
  conditional items (OAuth, distribution, queue, REST/GraphQL, multi-company, module
  boundaries, payouts, data models) kept conditional/open (DP-006). Worker-owned (no
  fan-out). Commit `d3da053`. Next: Stage 3 — setup/UX principles.
- **Sprint E / Stage 3 — Setup & UX principles (2026-07-01):** Wrote
  `docs/02-product/setup-ux-principles.md` — a UX north star + 12 principles (guided
  setup; prove readiness; progressive disclosure; honest status & freshness; command
  center over scattered menus; recovery-first errors; safe-by-default actions;
  human-readable logs; guided mappings; role-aware UX; modular feature visibility;
  docs mirror the product) + per-area principle sets (setup flow, config screens,
  dashboard, sync operations, logs/retries/recovery, mapping screens,
  multi-store/permissions, advanced features) + anti-patterns + open questions +
  ChatGPT review notes. Grounded in Sprint C UX benchmark / best-in-class / avoid-list
  + Sprint D taxonomy; DP-003/004/006 discipline applied; **no screens or menus
  designed**. Commit `5561db3`. Next: Stage 4 — handoffs + QA loop.
- **Sprint E / Stage 4 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint E section
  of `docs/02-product/product-research-handoff.md` and of this rolling handoff (above),
  each with the learning feedback loop (no new issue; DP-006 gate applied, not
  re-triggered) and, here, the quality-gate confirmation. Updated QA logs with
  non-decision / no-new-issue notes: `defect-pattern-log.md` (Sprint E note — DP-006
  gate applied, not re-triggered, no counter change), `architecture-review-log.md`
  (Sprint E non-decision note — vision/UX principles supply product-intent inputs to
  AR-002…AR-008, all still Not decided / Evidence pending), `rejected-approaches-log.md`
  (nothing rejected), `technical-debt-register.md` (no debt). Ran final allowed/
  forbidden-file checks. Next: push the working branch and open one draft PR targeting
  `Shopify-connector`, then stop.

### Product Sprint F checkpoints

- **Sprint F / Stage 1 — Setup + evidence read (2026-07-01):** Started **Product
  Sprint F** (MVP scope proposal, non-MVP/later-phase boundaries, and user stories —
  backlog item **RB-13**). MVP-proposal synthesis only; **no-code gate confirmed**
  (`CLAUDE.md` §4–§5); high-power mode **not required** (focused product/MVP synthesis
  of already-merged repo evidence — no new competitor crawling, no research fan-out).
  Fetched remote branches and verified preconditions: **PR #53 is merged into
  `Shopify-connector`** (confirmed via GitHub API — `merged: true`, merged 2026-07-01
  10:17Z; branch tip `6e73f82` *is* the PR #53 merge commit); the working branch
  `claude/mvp-scope-user-stories-dms7s8` is based on `Shopify-connector` (identical to
  it at start, merge-base `6e73f82`). All required inputs present:
  `feature-taxonomy.md`, `capability-evidence-map.md`, `product-vision.md`,
  `setup-ux-principles.md`, `product-research-handoff.md`, and the **DP-006
  evidence-consistency gate** in `defect-pattern-log.md`. **Branch-name note for
  ChatGPT (flagged):** the Sprint F prompt body named
  `product/sprint-f-mvp-scope-proposal`, but the session's hard git rule designated
  the harness branch `claude/mvp-scope-user-stories-dms7s8` ("never push to a
  different branch without explicit permission"), so work proceeds on the
  harness-designated branch; **the PR still targets `Shopify-connector`**; `main` and
  plain `dev` untouched. Read `CLAUDE.md`, the required research/product/QA files, and
  confirmed: current phase is still no-code; Sprint F is MVP **proposal** only;
  architecture stays gated (AR-002…AR-008 all Not decided / Evidence pending);
  implementation stays gated; DP-003/004/005/006 prevention rules understood. Added
  this checkpoint. Commit `880dda8`. Next: Stage 2 — draft `docs/02-product/mvp-scope.md`.
- **Sprint F / Stage 2 — MVP scope proposal (2026-07-01):** Wrote
  `docs/02-product/mvp-scope.md` — the main deliverable: status/purpose/evidence base,
  a scope decision rule, MVP thesis (*small but excellent = a correct, observable,
  recoverable single-store loop, import-first*), MVP quality bar, the recommended scope,
  a full **MVP-scope-by-domain** with per-item blocks (Capability ID / Recommendation
  include·exclude·defer·open / Evidence strength / Evidence source / User value / Risk if
  included / Risk if excluded / Architecture dependency / MVP rationale / ChatGPT decision
  needed) for all 20 domains (~90 capabilities), the MVP-critical reliability/UX/config/
  security lists, **three options considered** (A correctness-core-import-first
  [recommended], B bidirectional catalog, C thin import-only pilot), excluded
  capabilities, an **Architecture-dependent MVP items** table (AR-002…AR-008, intent not
  mechanism), the **DP-006 evidence-consistency review** (8 checks), MVP acceptance
  principles, and open questions/review notes. Every inclusion marked *Proposed MVP
  inclusion — pending ChatGPT acceptance*; architecture-sensitive items marked
  *Architecture-dependent — must be resolved in RB-14 before implementation*. Worker-owned
  (no fan-out). Commit `1dbea92`. Next: Stage 3 — non-MVP/later boundaries.
- **Sprint F / Stage 3 — Non-MVP/later boundaries (2026-07-01):** Wrote
  `docs/02-product/non-mvp-and-later-phases.md` — a strict non-MVP rule; explicitly
  non-MVP items (export, full payments/refunds/returns/cancellations, payouts,
  multi-package fulfilment, order risk, SEO/BoM/pricelists/per-market, analytics) with
  per-item blocks (Capability ID / Category / Why not MVP / Evidence / Risk of including
  too early / What must be true before including); later-phase candidates (Phase 2–4);
  optional premium add-ons (Markets/B2B/POS/gift cards/metafields/extended); architecture-
  dependent later items; items blocked by weak evidence (pHash, TQ/EC/SH breadth, WK
  multi-company ➖ DP-004), by the distribution decision (App-Store/demo, C-DOCS-04), and
  by Odoo edition/hosting (Enterprise-only reports; Odoo Online / staging cron
  constraints); and a **"what not to accidentally pull into MVP"** anti-bloat contract.
  Exclusions framed as recommendations-against-MVP, not rejected approaches. Commit
  `103a638`. Next: Stage 4 — user stories.
- **Sprint F / Stage 4 — User stories (2026-07-01):** Wrote
  `docs/02-product/user-stories.md` — persona assumptions (P1–P4, primary MVP persona
  left open), a story format, **10 MVP epics** (store setup & readiness; product/catalog;
  customer import & matching; order import & lifecycle; inventory & freshness; fulfilment
  & tracking; logs/errors/retries/recovery; command center; mapping & configuration;
  permissions & roles) with persona-driven, testable, product-level stories (each: Persona
  / Story / Capability IDs / MVP relevance proposed·later·open / Evidence strength /
  Acceptance notes / Failure-recovery notes / Architecture dependency / Open questions),
  **6 later-phase epics**, product-level acceptance principles, and open questions/review
  notes. **No implementation tasks, no code-level acceptance criteria, no screens/
  modules.** Commit `fd4d131`. Next: Stage 5 — handoffs + QA loop.
- **Sprint F / Stage 5 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint F section of
  `docs/02-product/product-research-handoff.md` and of this rolling handoff (above), each
  with the learning feedback loop (no new issue; DP-006 gate applied, not re-triggered)
  and, here, the branch/commit table and quality-gate confirmation. Updated QA logs with
  non-decision / no-new-issue notes: `defect-pattern-log.md` (Sprint F — DP-006 gate
  applied, not re-triggered; no counter change; MVP proposal did not finalize architecture
  or turn weak evidence into scope), `architecture-review-log.md` (Sprint F non-decision
  note — MVP proposal supplies capability-scope inputs to AR-002…AR-008, all still Not
  decided / Evidence pending), `rejected-approaches-log.md` (nothing rejected; MVP
  exclusions are recommendations-against-MVP), `technical-debt-register.md` (no debt). Ran
  final allowed/forbidden-file checks. Next: push the working branch and open one draft PR
  targeting `Shopify-connector`, then stop.
- **Sprint G / Stage 1 — Setup & start handoff (2026-07-01):** Confirmed **PR #54 merged**
  into `Shopify-connector` (merge commit `1d5e774`, merged 2026-07-01); confirmed the
  latest `Shopify-connector` contains `docs/02-product/{mvp-scope,non-mvp-and-later-phases,
  user-stories,product-research-handoff}.md` and the **DP-006 evidence-consistency gate** in
  `docs/05-qa/defect-pattern-log.md`. Working branch is the **harness-designated**
  `claude/sprint-g-mvp-scope-jxisgm` (the prompt requested `product/sprint-g-mvp-acceptance`;
  branch-name discrepancy recorded here and in the Sprint G handoff), based on latest
  `Shopify-connector` (HEAD `1d5e774`, clean base); **PR targets `Shopify-connector`**;
  `main` and plain `dev` untouched. Read `CLAUDE.md`, the required research/product/QA files,
  and the decision-record template; confirmed: current phase is still **no-code**; Sprint G
  records **MVP acceptance only** (product scope, not architecture); architecture stays gated
  (AR-002…AR-008 all Not decided / Evidence pending); implementation stays gated;
  DP-003/004/005/006 prevention rules and the evidence-consistency gate understood; allowed/
  forbidden files understood. Added this checkpoint. Next: Stage 2 — create
  `docs/04-decisions/DEC-003-mvp-scope.md` recording ChatGPT's accepted RB-13 MVP baseline.
- **Sprint G / Stage 2 — MVP decision record (2026-07-01):** Created
  `docs/04-decisions/DEC-003-mvp-scope.md` — the **accepted MVP product-scope baseline** with
  the prompt-specified structure (Status accepted 2026-07-01; **Decision type: product scope,
  not architecture**; Context; Decision; Accepted MVP option = Option A correctness-core/
  import-first; Accepted MVP scope; Deferred from MVP; Domain 9 minimal-financial-evidence
  decision; Refund/cancellation deferral; Bulk-ops not-user-facing decision; Store/company
  single-store/single-company decision; P1-primary/P2-secondary persona decision; Architecture
  dependencies feeding AR-002…AR-008 with none decided; Evidence basis; Consequences;
  Non-goals; Open architecture questions; and a **Review/change-control** clause stating no
  architecture/API/queue/data-model/module-boundary decision is made and implementation stays
  blocked). Recorded ChatGPT's accepted decisions exactly. Commit `595c4c9`. Next: Stage 3 —
  align the product scope docs.
- **Sprint G / Stage 3 — Product doc alignment (2026-07-01):** Updated `mvp-scope.md`
  (title/status → **accepted baseline**; added a **ChatGPT RB-13 acceptance** section near the
  top; resolved every former `open` fork inline as **RB-13 accepted/decision** — product/
  customer export DEFERRED, Domain 9 INCLUDE-minimal-evidence-only, refunds/cancellations
  DEFERRED, bulk ops NOT-user-facing/internal-only, single-store/single-company CONFIRMED,
  App-Store OUT; split Open questions into resolved vs still-open; updated the
  evidence-consistency review check #8, options, excluded list, acceptance principle #1, and
  the closing banner), `non-mvp-and-later-phases.md` (status → **accepted boundary**;
  export/customer-export/refunds-cancellations/Domain-9-accounting/bulk-ops/App-Store/
  multi-store-company confirmed non-MVP with revisit conditions; resolved Open questions), and
  `user-stories.md` (persona → P1-primary/P2-secondary; US-E2-05/US-E3-04/US-E4-06 → **later**;
  US-E4-05 Domain 9 → **MVP minimal-evidence-only**; bulk-ops mentions → internal-only; later
  epics + acceptance principle #2 + Open questions aligned). Kept architecture-dependent items
  marked architecture-dependent; did not pretend architecture is solved. Commit `16ec244`.
  Next: Stage 4 — handoffs + QA loop.
- **Sprint G / Stage 4 — Handoffs + QA loop (2026-07-01):** Wrote the Sprint G section of
  `docs/02-product/product-research-handoff.md` and of this rolling handoff (above), each with
  the required subsections (session summary; files; MVP acceptance summary; accepted decisions;
  deferred scope; architecture dependencies still open; evidence-consistency gate; no-code/
  no-architecture confirmation; recommended next sprint = **RB-14 Architecture Prep Part 1**
  (AR-002/AR-003/AR-005); stop confirmation) plus the learning feedback loop and branch-reality
  note. Updated QA logs with non-decision / no-new-issue notes: `architecture-review-log.md`
  (**required** Sprint G non-decision note — DEC-003 accepts product MVP scope only, feeds
  AR-002…AR-008, no AR row decided), `defect-pattern-log.md` (Sprint G — DP-006 gate applied,
  not re-triggered; no new row, no counter change; product-scope acceptance kept separate from
  architecture), `rejected-approaches-log.md` (none — deferrals are product-scope boundary
  decisions, not rejected approaches), `technical-debt-register.md` (none — no code). Ran final
  allowed/forbidden-file checks. Next: push the working branch and open one draft PR targeting
  `Shopify-connector`, then stop.
- **Sprint G / revision — controlled product export into MVP (PR #55 review, 2026-07-01):**
  ChatGPT reviewed PR #55 and returned **REVISE**: the first draft **over-deferred product
  export**. Corrected on the same branch/PR (no new PR, no merge). **Product-scope correction
  only** — **controlled product export/update is now IN MVP** (Shopify→Odoo import **and**
  Odoo→Shopify export/update, with first-sync matching, binding, preview/dry-run, duplicate
  prevention, and draft/unpublished/channel-controlled safety = **controlled bidirectional
  product onboarding**); **full autonomous bidirectional catalog management** and **customer
  export** stay later. Updated only the 10 PR #55 files: `DEC-003-mvp-scope.md` (revised
  Decision/Accepted-option/direction/Deferred/Non-goals + new **Product direction decision**
  section + AR-002/005 rows + Status revision note), `mvp-scope.md` (RB-13 acceptance corrected
  + new **Product onboarding and duplicate-prevention baseline** section + C-PROD-02/03/05
  blocks + options + excluded + evidence-consistency + TeqStars accessibility correction),
  `non-mvp-and-later-phases.md` (product export removed from non-MVP; new **Full autonomous
  bidirectional catalog management** boundary; customer export kept later), `user-stories.md`
  (US-E2-05 → controlled MVP export/update; new **US-E2-06** first-sync matching; customer
  export later), both handoffs (this revision note), and QA logs (`defect-pattern-log.md`
  Sprint G revision note — over-deferral corrected, TQ source availability changed, product-scope
  correction not an implementation defect, no new DP row; `architecture-review-log.md` — controlled
  product export/update now feeds AR-002/AR-005, full bidirectional conflict-resolution later, no
  AR row decided). **TeqStars docs re-checked accessible 2026-07-01; full rebaseline pending a
  later sprint.** No rejected approaches; no technical debt; no architecture decided; no
  implementation authorized. Commit `docs: revise mvp baseline for controlled product export`.
  Next: push the same branch/PR #55; do not merge; await ChatGPT re-review.
- **Phase 1 Domain Model + DEC-003 Scope-Hole Closure (2026-07-02):** confirmed PR #61
  merged into `Shopify-connector` (merge commit `26dc30109530e2566755fd93bd974284083c3922`)
  and DEC-004/005/006 Accepted / AR-002/003/005 Accepted / AR-004/006/007/008 not decided
  before editing. Authored `phase1-domain-model-brief.md` (eight Phase 1 domains, concept
  level only) and proposed `DEC-007-phase1-scope-clarifications.md`
  (`Status: Proposed for ChatGPT review`) closing five DEC-003 scope holes: variant
  export/update, image/media + price "where feasible" wording, a first-inventory-push
  guard, a fulfilment customer-notification default (grounded in a small, targeted
  official-source check of `FulfillmentInput.notifyCustomer`/
  `fulfillmentTrackingInfoUpdate`, both defaulting to no notification), and
  tax/shipping/discount/payment-evidence treatment. Added five new user stories and
  pointer-only notes to `mvp-scope.md`/`non-mvp-and-later-phases.md`; added a non-decision
  note to `architecture-review-log.md` (AR-006/007/008 fed, not decided); added
  RA-008/009/010 (tagged PROPOSED) to `rejected-approaches-log.md`. No code; no DEC-003/
  004/005/006 edit; no AR row decided. Next: push branch, open one draft PR into
  `Shopify-connector`, stop for ChatGPT/Fable review.
- **AR-004 + AR-006 Decision Preparation (2026-07-02):** confirmed PR #63 merged into
  `Shopify-connector` (merge commit `3ca0cde`) and DEC-003/004/005/006/007 Accepted /
  RA-001–010 binding / AR-002/003/005 Accepted / AR-004/006/007/008 not decided before
  editing. Authored `ar004-module-boundary-decision-brief.md` and
  `ar006-error-retry-idempotency-decision-brief.md`; proposed `DEC-008-module-boundary-
  strategy.md` and `DEC-009-error-retry-idempotency-strategy.md` (both
  `Status: Proposed for ChatGPT review`), moving AR-004/AR-006 from "Not decided" to
  "Proposed for ChatGPT review" in `architecture-review-log.md`. Added RA-011–017 (tagged
  PROPOSED) to `rejected-approaches-log.md`. Opened draft PR #64 into `Shopify-connector`.
  Two follow-up revision rounds on the same PR (not a new PR): a minor self-revision
  (error-class count 15→16, DAG notation clarity, RA formatting), then a Fable
  ACCEPT-WITH-MINOR-CHANGES round (DEC-006 binding-schema-fork reconciliation,
  ambiguous-outcome non-idempotent-write retry rule, evidence-wording and citation-
  attribution corrections, feature-flag/config-model scope routed onward, DEC-005
  reconciliation-cadence handoff acknowledged, state-machine wording cleanup, RA-014
  revisit condition tightened). No code; no DEC-003/004/005/006/007 edit; AR-007/AR-008
  untouched. Next: push branch, keep PR #64 open (not merged), await ChatGPT/Fable
  re-review.
- **DEC-008/DEC-009 Acceptance Patch (2026-07-02):** confirmed PR #64 merged into
  `Shopify-connector` (merge commit `e4c74abf0e3b4ad32e66413d27b40287ed4c5822`) and
  DEC-003/004/005/006/007 Accepted / RA-001–010 binding / AR-002/003/005 Accepted /
  DEC-008/DEC-009 Proposed / AR-004/AR-006 proposed-only / AR-007/AR-008 not decided before
  editing. Changed DEC-008 and DEC-009 Status from `Proposed for ChatGPT review` to
  `Accepted by ChatGPT`, acceptance date 2026-07-02, citing the PR #64 merge and Fable's
  ACCEPT WITH MINOR CHANGES review while preserving every documented caveat. Updated the
  AR-004 and AR-006 decision briefs, `04-decisions/README.md`, and
  `architecture-review-log.md` (AR-004/AR-006 rows move to "Accepted by ChatGPT"; AR-007/
  AR-008 untouched). Removed the `PROPOSED:` prefix from RA-011–017 and cited each DEC
  file's accepted status — now binding final rejected approaches. No code; no
  DEC-003/004/005/006/007 edit; AR-007/AR-008 remain not decided; implementation remains
  blocked. Next: push branch, open one draft PR into `Shopify-connector`, stop for ChatGPT
  review.
- **AR-007 + AR-008 Decision Preparation (2026-07-02):** confirmed PR #65 merged into
  `Shopify-connector` (merge commit `dfb0199c9588ae600216ef549d160d0ced15034f`) and
  DEC-003/004/005/006/007/008/009 Accepted / RA-001–017 binding / AR-002/003/004/005/006
  Accepted / AR-007/AR-008 not decided before editing. Authored
  `ar007-inventory-architecture-decision-brief.md` and
  `ar008-fulfillment-architecture-decision-brief.md`; ran a small, targeted official-source
  check (`ar007-ar008-evidence-refresh.md`) against Odoo 19.0 docs (On Hand/Free to Use/
  Forecasted, location types, carrier tracking) since the existing Odoo research notes had
  zero coverage of `stock.quant`/`stock.picking`/delivery-carrier models; proposed
  `DEC-010-inventory-architecture-strategy.md` and
  `DEC-011-fulfillment-architecture-strategy.md` (both `Status: Proposed for ChatGPT
  review`), moving AR-007/AR-008 from "Not decided" to "Proposed for ChatGPT review" in
  `architecture-review-log.md`. Added RA-018–023 (tagged PROPOSED) to
  `rejected-approaches-log.md`; checked against RA-001–017 first, referenced RA-008/009/
  014/017 instead of duplicating, and treated multi-package/multi-location fulfillment as
  an existing deferral (not a rejection). Flagged one open architecture issue (a shared
  Shopify-Location reference for `inventory`/`fulfillment` without violating DEC-008's
  no-inventory-dependency rule for `fulfillment`) and routed it to architecture review
  rather than deciding it unilaterally. No code; no DEC-003/004/005/006/007/008/009 edit;
  AR-007/AR-008 are proposed only, not accepted; implementation remains blocked. Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT/Fable review.
- **DEC-010/DEC-011 Acceptance Patch (2026-07-02):** confirmed PR #66 merged into
  `Shopify-connector` (merge commit `14af2fb3becb47ba7c32a50715d85f6eaab0d855`) and
  DEC-003/004/005/006/007/008/009 Accepted / RA-001–017 binding / AR-002/003/004/005/006
  Accepted / DEC-010/DEC-011 Proposed / AR-007/AR-008 proposed-only / RA-018–023 PROPOSED
  before editing. Changed DEC-010 and DEC-011 Status from `Proposed for ChatGPT review` to
  `Accepted by ChatGPT`, acceptance date 2026-07-02, citing the PR #66 merge and Fable's
  ACCEPT WITH MINOR CHANGES review while preserving every documented caveat, and recorded
  the shared Shopify Location reference clarification as ratified against DEC-008. Updated
  the AR-007 and AR-008 decision briefs, `04-decisions/README.md`, and
  `architecture-review-log.md` (AR-007/AR-008 rows move to "Accepted by ChatGPT"; all of
  AR-002 through AR-008 now accepted). Removed the `PROPOSED:` prefix from RA-018–023 and
  cited each DEC file's accepted status — now binding final rejected approaches. No code;
  no DEC-003/004/005/006/007/008/009 edit; implementation remains blocked. Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT review.
- **UX / Operator-Flow Decision Preparation (2026-07-02):** confirmed PR #67 merged
  into `Shopify-connector` (merge commit
  `8798a2454924fd241c8052e2556ea8bca21a7c20`) and DEC-003 through DEC-011 Accepted /
  AR-002 through AR-008 Accepted / RA-001–023 binding before editing. Authored
  `ux-operator-flow.md` (ten operator flows: setup wizard, store settings,
  dashboard, sync/job monitor, error center, matching/dedup, product
  import/export/update, inventory, fulfillment, conceptual permissions/roles),
  each cited to the DEC-003 through DEC-011 "UX implications" sections and the
  accepted `setup-ux-principles.md`/`product-vision.md` inputs. Proposed
  `DEC-012-ux-operator-flow-strategy.md` (`Status: Proposed for ChatGPT review`)
  and authored `ux-operator-flow-architecture-bridge.md` mapping each flow to its
  source decisions and to what routes to the Master Blueprint. Added AR-009
  ("UX/operator-flow strategy," Proposed for ChatGPT review) to
  `architecture-review-log.md`; indexed DEC-012 as Proposed in
  `04-decisions/README.md`; checked `rejected-approaches-log.md` and added no new
  RA row (every UX-facing anti-pattern already covered by RA-006/008/009/014–023).
  No code; no DEC-003/004/005/006/007/008/009/010/011 edit; DEC-012/AR-009 are
  proposed only, not accepted; implementation remains blocked. Next: push branch,
  open one draft PR into `Shopify-connector`, stop for ChatGPT/Fable review.
- **DEC-012 Acceptance Patch (2026-07-03):** confirmed PR #68 merged into
  `Shopify-connector` (merge commit
  `7d01617fdd0fd70d6a1d83d57918b045296550ac`) and DEC-003 through DEC-011
  Accepted / DEC-012 Proposed / AR-009 proposed-only before editing. Changed
  DEC-012 Status from `Proposed for ChatGPT review` to `Accepted by ChatGPT`,
  acceptance date 2026-07-03, citing the PR #68 merge and Fable's ACCEPT WITH
  MINOR CHANGES review, while preserving every open question unchanged. Updated
  `ux-operator-flow.md`, the architecture bridge, `04-decisions/README.md`, and
  `architecture-review-log.md` (AR-009 row moves to "Accepted by ChatGPT";
  AR-002 through AR-008 untouched); marked `quality-feedback-loop.md` §10
  criterion 5 done via DEC-012. No code; no DEC-003/004/005/006/007/008/009/
  010/011 edit; implementation remains blocked; Master Blueprint not started.
  Next: push branch, open one draft PR into `Shopify-connector`, stop for
  ChatGPT review.
- **Master Blueprint Sprint A — Core/Common Substrate (2026-07-03):**
  confirmed PR #69 merged into `Shopify-connector` (merge commit
  `305f396bcbd2656a4282ed18c5983540503b5502`) and DEC-003 through DEC-012 /
  AR-002 through AR-009 all Accepted before editing. Created the first
  Master Blueprint package: `master-blueprint.md` (index), the Part A
  `master-blueprint-core-substrate.md`, and
  `master-blueprint-open-questions.md` (MBQ-01–MBQ-52). Proposed
  `DEC-013-master-blueprint-core-substrate.md` (`Status: Proposed for
  ChatGPT review`) and added AR-010 (Proposed) to
  `architecture-review-log.md`; indexed DEC-013 as Proposed in
  `04-decisions/README.md`. PR #70 opened as draft into `Shopify-connector`,
  branch `claude/master-blueprint-core-substrate-azhp4s`. No code; no
  DEC-003 through DEC-012 edit; DEC-013/AR-010 proposed only, not accepted;
  implementation remains blocked; Sprint B not started. Next: ChatGPT/Fable
  review of PR #70.
- **PR #70 Fable revision (2026-07-03):** Fable reviewed PR #70 and returned
  **ACCEPT WITH MINOR CHANGES**. Applied within the same PR/branch (no new
  PR): added Master Blueprint Part D — UI/UX Screen Design Blueprint — to
  `master-blueprint.md`'s sequence and to implementation-gate criterion 1;
  added MBQ-53 (screen-level UI/UX design) and MBQ-54 (domain-module
  uninstall/disable data lifecycle) to `master-blueprint-open-questions.md`;
  scoped the §I.3 feature-flag execution-time re-check to fail-safe
  enablement gating only (never altering enqueue-time notification/
  source-of-truth decisions); reworded §I.4 to use only accepted DEC-009
  job-state vocabulary (no new `held` state); added a cross-domain
  binding-enumeration seam and a binding-granularity bound to §C.8; added a
  webhook-topic registration seam to §A.5; corrected two claim labels
  (§C.4 manual-override extension, §D.13 source-of-truth-persistence
  generalization) and added §D.5's `skipped`/`failed_final`
  any-class-outcome rule; clarified `ir.cron` wording (§D.1) and the
  credential no-read-back rule as a connector-surface guarantee, not a
  database-level claim (§J.2); minimal consistency updates to DEC-013 (MBQ count,
  Part D/E sequence, no-exhaustive-list caveat). DEC-013 remains Proposed
  for ChatGPT review, not accepted; AR-010 remains proposed only; DEC-003
  through DEC-012 untouched; no code files changed; implementation remains
  blocked; Sprint B not started. Next: push the same branch, no new PR,
  stop for further ChatGPT/Fable review.
- **PR #70 tiny consistency fix (2026-07-03):** ChatGPT requested one tiny
  cleanup after the Fable revision — the AR-010 row in
  `architecture-review-log.md` still cited `MBQ-01–MBQ-52`, stale since the
  Fable revision added MBQ-53/MBQ-54. Updated AR-010's open-questions
  reference to `MBQ-01–MBQ-54` and added MBQ-53/MBQ-54 to its headline
  review items; MBQ-53/MBQ-54 themselves unchanged. AR-010 remains
  Proposed for ChatGPT review, not accepted; DEC-013 remains Proposed;
  DEC-003 through DEC-012 untouched; no code files changed; implementation
  remains blocked; Sprint B not started. Same branch/PR — no new PR opened,
  no merge. Next: stop for further ChatGPT/Fable review.
- **DEC-013 Acceptance Patch (2026-07-03):** confirmed PR #70 merged into
  `Shopify-connector` (merge commit
  `5c44971d1df84d5657da0164bf874b1125aee64f`) and DEC-013/AR-010 confirmed
  `Proposed for ChatGPT review` before editing. **ChatGPT accepted DEC-013**
  (acceptance date 2026-07-03), recording the PR #70 merge, Fable's ACCEPT
  WITH MINOR CHANGES review, and the Fable revision + tiny consistency fix
  applied before merge. Resolved MBQ-11 (binding schema shape), MBQ-07
  (feature-flag mechanism, blueprint-direction level), and MBQ-47 (Reviewer
  boundary); partially resolved MBQ-45 (role hierarchy); left MBQ-04,
  MBQ-08, MBQ-53, MBQ-54 open. Updated `master-blueprint.md` and
  `master-blueprint-core-substrate.md` status wording to accepted-through-
  DEC-013 (without adding new architecture substance); moved AR-010 to
  Accepted in `architecture-review-log.md`; moved DEC-013 to "Also accepted"
  in `04-decisions/README.md`. Branch
  `claude/accept-dec013-master-blueprint-nh6ouq` (harness-assigned; preferred
  name was `product/accept-dec013-master-blueprint-core`). No code; no
  DEC-003 through DEC-012 edit; implementation remains blocked; Sprint B not
  started. Next: push branch, open one draft PR into `Shopify-connector`,
  stop for ChatGPT review.
- **PR #71 tiny acceptance-label cleanup (2026-07-03):** ChatGPT requested
  one tiny cleanup before merge — the open-questions register status still
  said `Proposed for ChatGPT review`, and several DEC-013-accepted design
  details in the core-substrate blueprint still carried the stale
  `[Blueprint proposal]` tag. Updated the register status to
  accepted-through-DEC-013 (unresolved MBQ rows, incl. MBQ-04/08/53/54,
  preserved); refined the `[Blueprint proposal]` claim-label definition;
  relabeled §C.8's enumeration seam and granularity bound, §I.3's
  execution-time re-check scoping, and §J.2's no-read-back connector-surface
  guarantee to `[Accepted — DEC-013]`. DEC-013 and AR-010 remain accepted;
  DEC-003 through DEC-012 untouched; no code files changed; implementation
  remains blocked; Sprint B not started. Same branch/PR — no new PR opened,
  no merge.
- **Master Blueprint Sprint B (2026-07-03):** confirmed PR #71 merged into
  `Shopify-connector` (merge commit
  `283a38f26ef90fca2a53c18ff6faf4775da4a2ee`) and DEC-013/AR-010 confirmed
  **Accepted by ChatGPT** before editing. Created the **product, customer,
  and sale/order domain blueprint**
  (`master-blueprint-product-customer-sale.md`), converting accepted
  DEC-003/006/007/012 plus the accepted DEC-013 core substrate into
  domain-level flows, job types, binding ownership, and error/retry
  mappings for product, customer, and order. Two small, targeted
  official-doc checks performed (Shopify `productSet`/
  `productVariantsBulkCreate`/`Product.status`/`publishablePublish`,
  accessed 2026-07-03; Odoo 19 accounting/taxes docs, accessed
  2026-07-03, inconclusive) — no broad research, per the sprint's scoped
  instruction. Proposed partial resolutions for MBQ-23/25/29/30;
  recommendations (not self-decided) for MBQ-26/31; carried MBQ-24/27/28
  forward unresolved; added MBQ-55–58. Created proposed **DEC-014**
  (`Status: Proposed for ChatGPT review`) and proposed **AR-011**
  (`Status: Proposed for ChatGPT review`). Updated `master-blueprint.md`
  (Part B → Proposed for ChatGPT review; Parts C/D/E remain Not started)
  and `04-decisions/README.md` (DEC-014 added as not-yet-accepted).
  DEC-003 through DEC-013 unedited; no code files changed; implementation
  remains blocked; Sprint C not started; UI/UX Screen Design Blueprint not
  started. Branch `claude/master-blueprint-sprint-b-7zrvji`
  (harness-assigned; preferred name was
  `architecture/master-blueprint-product-customer-sale`). Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT/
  Fable review.
- **Master Blueprint Sprint B — PR #72 revision (2026-07-03):** ChatGPT
  requested REVISE before Fable review. Fixed automated create/preview
  semantics (retrospective sync-center/dashboard audit no longer treated
  as satisfying "no blind create"; replaced with an explicit pre-create
  duplicate check + six-condition auto-create gate, new MBQ-59);
  corrected §A.4 so product export/update no longer implies autonomous
  Odoo-write-triggered Shopify pushes; generalized unverified
  `read_all_orders` wording in the error-class table; verified and cited
  `productVariantsBulkUpdate` against its official reference page. MBQ-59
  added; DEC-014/AR-011 updated to MBQ-55–59 and to call out the
  automated-import policy as proposed/open, not accepted. DEC-014 and
  AR-011 remain Proposed for ChatGPT review, not accepted; DEC-003
  through DEC-013 untouched; no code files changed; implementation
  remains blocked; Sprint C not started; UI/UX Screen Design Blueprint
  not started. Same branch/PR (#72) — no new PR, no merge. Next: stop
  for Fable review.
- **Master Blueprint Sprint B — PR #72 Fable revision (2026-07-03):**
  Fable returned REVISE (no redesign needed). Applied B1 (Part A
  per-class routing — `mapping missing`/`data shape mismatch` →
  `failed_retryable`, `financial total mismatch` → its own §D.5.5
  posture, only the four Sprint-B-relevant confirmation-required classes
  → `blocked_manual_review`; Part A §D.8 vocabulary not widened), B2
  (§C.12 narrowed — `ORDERS_UPDATED` refreshes evidence only, never
  silently writes sale-order lines/totals/fulfillment state, divergence
  routed to the total-check guard, webhook/reconciliation consistent),
  and B3 (MBQ-59 labels fixed — accepted import capability separated
  from the proposed, pending-DEC-014 automated mechanism; MBQ-59 stays
  fully open). Applied 12 minor issues (README range, DEC-014 lettering,
  MBQ typos, §B.6/§B.7 attribution, webhook-topic citations, §C.6
  three-path reconciliation, gate-condition precision, citation
  consistency, original MBQ question text restored). DEC-014 and AR-011
  remain Proposed for ChatGPT review, not accepted; MBQ-59 remains
  proposed/open; DEC-003 through DEC-013 untouched; no code files
  changed; implementation remains blocked; Sprint C not started; UI/UX
  Screen Design Blueprint not started. Same branch/PR (#72) — no new PR,
  no merge. Next: stop for Fable re-review.
- **DEC-014 Acceptance Patch (2026-07-03):** after PR #72 merged into
  `Shopify-connector` (merge commit
  `e27c21f328436bc734539dd9169a95d79deaadd1`), ChatGPT formally accepted
  DEC-014. Accepted Master Blueprint Part B in full; accepted the Fable
  B1 route (Part A per-class routing, §D.8 vocabulary not widened) and
  the Fable B2 route (`ORDERS_UPDATED` evidence-refresh only, no silent
  Odoo writes) as final; accepted MBQ-59 (automated import create/bind
  policy) at blueprint-policy level; accepted MBQ-26 (order-import
  operator touchpoints, with inline financial-evidence breakdown and
  direct matching-flow links) and MBQ-31 (email-only customer match key)
  at blueprint level; partially resolved MBQ-23/25/29/30. MBQ-04/08/24/
  27/28/53/54/55/56/57/58 remain open, untouched. AR-011 moved to
  Accepted. DEC-003 through DEC-013 unedited; no code files changed;
  implementation remains blocked; Sprint C not started; UI/UX Screen
  Design Blueprint not started. Branch
  `claude/dec-014-acceptance-patch-5bml33` (harness-assigned). Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT
  review.
- **Master Blueprint Sprint C (2026-07-03):** after PR #73 merged into
  `Shopify-connector` (merge commit
  `09829a804eef9c4099960f5604729f3a775793d1`), proposed Master Blueprint
  Part C — Inventory and Fulfillment Domain Blueprint
  (`master-blueprint-inventory-fulfillment.md`) and companion **DEC-015**
  (Proposed for ChatGPT review, not accepted) and **AR-012** (Proposed
  for ChatGPT review, not accepted). Converted accepted DEC-010/DEC-011
  into blueprint-level detail, reusing Part A (DEC-013) and Part B
  (DEC-014) unmodified. Six targeted official-doc checks performed
  (accessed 2026-07-03): Shopify `WebhookSubscriptionTopic` enum
  (`INVENTORY_LEVELS_UPDATE`, `FULFILLMENT_ORDERS_*`/`FULFILLMENTS_*`);
  Odoo 19.0 official source (`product.product.free_qty`,
  `stock.quant.available_quantity`, `stock.picking.backorder_id`/
  `backorder_ids`, `stock_delivery`'s `carrier_tracking_ref`/
  `carrier_tracking_url`/`carrier_id`). Proposed resolved MBQ-37/39;
  proposed partially resolved MBQ-32/36/38/40/42/43 — all pending DEC-015
  acceptance, remaining formally open until then; proposed recommendations (not
  self-accepted) for the three ChatGPT-decision-owner rows MBQ-33/34/41;
  added two new rows MBQ-60 (`stock_delivery` module dependency) and
  MBQ-61 (FulfillmentOrder lifecycle webhook events). `master-blueprint.md`
  Part C moved to "Proposed for ChatGPT review via DEC-015"; Part D/E
  preserved as "Not started." DEC-003 through DEC-014 unedited; no code
  files changed; implementation remains blocked; UI/UX Screen Design
  Blueprint not started. Branch
  `claude/master-blueprint-sprint-c-inventory-fulfillment`. Next: push
  branch, open one draft PR into `Shopify-connector`, stop for ChatGPT
  review.
- **Sprint C status-language correction (2026-07-03):** ChatGPT reviewed
  PR #74 and flagged that the MBQ register and related handoff/summary
  wording used accepted-sounding labels ("Resolved by Sprint C,"
  "Partially resolved by Sprint C") before DEC-015 acceptance. Corrected
  `master-blueprint-open-questions.md`, `master-blueprint-inventory-
  fulfillment.md` (§A.4/§A.9/§A.13/§A.15/§B.5/§B.7/§B.8/§B.14/§G),
  `DEC-015-master-blueprint-inventory-fulfillment.md` (Explicit acceptance
  points A/D/E/F/G/H/J/K, Open questions headline), and
  `architecture-review-log.md` (AR-012) to use "Proposed resolved"/
  "Proposed partially resolved" throughout, each explicitly stating the
  row remains formally `open` pending DEC-015 acceptance. No substantive
  technical conclusion, MBQ ID, or MBQ-60/61 content changed; no
  recommendation status changed (MBQ-33/34/41 remain recommendations for
  ChatGPT's direct decision); DEC-003 through DEC-014 untouched; no code
  files changed; implementation remains blocked; Part D/E remain not
  started. Same branch/PR (#74) — no new PR, no merge. Next: stop for
  ChatGPT review.
- **Sprint C Fable review fixes (2026-07-03):** Fable reviewed PR #74 and
  returned **REVISE — no redesign** (architecture sound; two substantive
  findings plus several wording/status fixes required before ChatGPT
  acceptance review). **C1 (over-claim):** an earlier draft claimed
  `product.product.free_qty` and `stock.quant.available_quantity` were
  equivalent quantity sources; corrected in
  `master-blueprint-inventory-fulfillment.md` §A.4/§G, the register's
  MBQ-32 row, and DEC-015 point A to state the exact, non-equivalent
  relationship (`free_qty` additionally nets out `expired_unreserved_qty`
  and applies UoM rounding via `product.uom_id.round(...)`, quoted
  exactly) and that the source choice is substantive, not decided by this
  sprint; MBQ-32 stays "proposed partially resolved." **C2 (job-source
  vocabulary):** an earlier draft silently listed `event-driven enqueue`
  in §A.7/§A.13/§B.12/§C item 7 as if it were a Part A §D.2 job-source
  enum value, and fulfillment creation's own source classification was
  unstated; corrected to distinguish the sync-trigger layer from Part A's
  fixed job-source vocabulary throughout, with no vocabulary extension
  asserted; new open question **MBQ-62** added (Odoo-event-triggered job
  source classification, covering both inventory push and fulfillment
  creation). **Minor fixes:** §A.14's destructive-write-guard bullet
  collapsed to a direct `destructive-write guard blocked` mapping citing
  AR-006/DEC-009 (minor finding 1); §B.8/DEC-015 point J now state
  explicitly that AR-006/DEC-009 defined `ambiguous match` as multiple
  candidates and that Sprint C proposes *widening* that class for a
  deterministic location mismatch, framed as part of what DEC-015
  acceptance would decide (minor finding 2); MBQ-37/MBQ-39's
  "Blocks implementation" register cells restored to conservative,
  Yes-leading wording pending DEC-015 acceptance (minor finding 3); new
  open question **MBQ-63** added (Shopify inventory-webhook payload
  shape/subscription mechanics/Phase-1-implementation-scope residual,
  minor finding 4); the MBQ-34 review-then-apply recommendation sentence
  added directly to §A.7, where §A.15/§G already referenced it (minor
  finding 5); a truncated `FULFILLMENTS_CREATE`/`FULFILLMENTS_UPDATE`
  Shopify-topic quote marked as an excerpt (minor finding 6); the two
  remaining "resolving MBQ-37"/"resolving MBQ-39" instances in DEC-015's
  Proposed-decision items and in AR-012 changed to "proposing to resolve"
  (minor finding 7). DEC-015 and AR-012 updated to reference MBQ-62/63 as
  new/open; this handoff updated to match. No technical conclusion
  outside the C1/C2 corrections changed; no MBQ ID renumbered; DEC-003
  through DEC-014 untouched; no code files changed; implementation
  remains blocked; Part D/E remain not started; DEC-015 and AR-012 remain
  Proposed for ChatGPT review, not accepted. Same branch/PR (#74) — no
  new PR, no merge. Next: stop for ChatGPT acceptance review.

### DEC-015 Acceptance Patch — Part C blueprint document alignment (2026-07-03)

ChatGPT review of PR #74 found that the earlier DEC-015 acceptance-patch
commit correctly updated DEC-015, AR-012, `master-blueprint.md`, the MBQ
register, the decisions README, and the handoff, but left the primary
Part C blueprint document (`master-blueprint-inventory-fulfillment.md`)
itself still using proposal-era status wording ("Proposed for ChatGPT
review, not accepted," "proposed resolved"/"proposed partially
resolved," "pending DEC-015 acceptance") throughout its header, Status
section, claim-label section, §A.15, §B.14, §G, §H, and §I. Corrected in
a follow-up commit: the companion-DEC line and Status section now read
"Accepted by ChatGPT via DEC-015, 2026-07-03"; the claim-label section no
longer says the whole document is pending review; MBQ-37/MBQ-39 now read
"resolved at fact-verification level," MBQ-32/36/38/40/42/43 now read
"partially resolved" (MBQ-42 including the accepted, blueprint-level-only
widening of `ambiguous match`), and MBQ-33/34/41/35/60–63 remain
explicitly open, unchanged in substance; §I's implementation-blocked
statement now correctly shows condition (1) — ChatGPT acceptance of
Part C — as satisfied at blueprint level, while conditions (2)–(4)
remain unsatisfied, so implementation stays blocked overall. No
architecture substance changed; no MBQ row added, deleted, or
renumbered; DEC-003 through DEC-014 untouched; no code files changed.
Same branch/PR (#74) — no new PR, no merge, PR stays draft. Next: stop
for ChatGPT's next direction (Part D or Part E).
- **Credential/Connection/API Foundation Planning Sprint (2026-07-06):**
  proposed the AR-024 implementation-planning package (credential
  storage on a dedicated Admin-only `shopify.connector.store.credential`
  model within the accepted MBQ-04 Option B posture; redaction
  contract; lifecycle/test-connection/readiness/API-client planning;
  proposed-not-authorized Task 002/003 specs; credential-security
  checklist) with fresh official Shopify/Odoo verification (2026-07-06);
  docs-only, no code, no gate opened; draft PR into
  `Shopify-connector`. Next: ChatGPT review of AR-024. (Note: the
  2026-07-04/05 sprints logged their checkpoints in their compact
  entries above rather than here.)
