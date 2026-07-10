# Sync-Engine Concurrency Validation Plan

> **QA/evidence plan. Not an implementation task. Does not claim
> multi-server/concurrent-worker concurrency is proven.** This document
> defines, in advance, exactly how a future session (or human operator)
> with access to a live Odoo 19 runtime — ideally a multi-server/
> Odoo.sh-equivalent topology — should validate the Task 006C sync-engine
> job-claim mechanism (`_claim_for_dispatch()` / `try_lock_for_update()` /
> `run_drain()`) before any domain sync (product, customer, order,
> inventory, fulfillment) is built on top of it. It mirrors the structure
> of [`val-b2-closure-plan.md`](./val-b2-closure-plan.md): preconditions,
> exact steps, evidence to capture, and pass/fail criteria, written before
> execution. **This session does not execute any test, does not touch
> code, and does not open an implementation gate.**
>
> Prepared per the recommendation in
> [`../07-implementation-plan/next-task-recommendation-after-task-006c.md`](../07-implementation-plan/next-task-recommendation-after-task-006c.md)
> §D/§F, after PR #131 (Task 006C sync-engine core skeleton), PR #132
> (Task 006C closure/validation-results docs), and PR #133 (post-Task
> 006C next-task recommendation checkpoint) all merged into
> `Shopify-connector`, latest merge commit
> `c0a0bb3787947bba746f865a02883efa4e1c921d`. Every claim below is
> labelled **[Fact]** (verified in this repository's merged code, cited by
> file/line-level behavior), a restated **[Open question]** (cited from
> its own source), or this document's own **[Recommendation]** —
> per `CLAUDE.md` §8. Subject to ChatGPT review, revision, or rejection.

## Status

- **Proposed. Not yet executed by any session to date.** No Odoo/Odoo.sh
  runtime, no PostgreSQL instance, and no multi-server topology is
  reachable from this documentation-only session.
- Does not resolve, narrow, or silently decide SRR-03, SRR-04, or SRR-09
  (`sync-engine-risk-register.md`), or any other open item in
  `sync-engine-open-questions.md` or the "Open blockers" table in
  `next-task-recommendation-after-task-006c.md` §B.
- Does not authorize Task 010, any domain-sync task, a setup wizard,
  token-acquisition code, Lite/Full packaging, or any further
  implementation.
- Does not open, extend, or reinterpret the limited core-only, zero-UI
  gate (`limited-core-implementation-gate.md`), which Task 006C's own
  merged skeleton already exhausted.

---

## 1. Purpose

Task 006C (PR #131, merged) implemented the sync-engine's job-claim and
dispatch mechanism — `_claim_for_dispatch()`, `try_lock_for_update()`
per-candidate-row locking, and the `run_drain()` `ir.cron` entry point —
and validated it **only** via `TransactionCase` unit tests (a single
Odoo transaction; no real concurrent worker, no real multi-server
topology) plus one live Odoo.sh run that exercised the *code paths*, not
concurrent execution itself. The Task 006C closure record
(`task-006c-sync-engine-skeleton-validation-results.md` §F) states this
explicitly: **"Multi-server/concurrent-worker safety is not proven."**
DEC-025's own acceptance note repeats the same position: *"no concurrency
claim is treated as proven, and live Odoo.sh/multi-server runtime proof
is still required before any implementation relies on one."*

This plan exists so that, once a live Odoo/Odoo.sh runtime is available,
that runtime proof can be gathered **before** any future domain-sync task
(product, customer, order, inventory, fulfillment — Task 010 onward)
starts dispatching real business jobs through this exact mechanism. Every
future job type, without exception, will be claimed and dispatched
through `_claim_for_dispatch()`/`run_drain()` — a defect discovered after
several domain modules already depend on it is far more expensive to
isolate than one discovered now, while only the core skeleton depends on
it (`next-task-recommendation-after-task-006c.md` §D, justification 1/4).

**[Recommendation]** This plan itself does not perform the validation —
it specifies exactly what a future execution session must do, mirroring
how `val-b2-closure-plan.md` was drafted before any live Shopify
connection was attempted.

---

## 2. Scope

**In scope** — runtime behavior of the Task 006C job-claim/dispatch
mechanism only:

- `shopify.connector.job._claim_for_dispatch()`
- `try_lock_for_update()` per-candidate-row locking behavior
- `shopify.connector.job.dispatch.run_drain()` (the `ir.cron` entry
  point, `shopify_connector_cron_drain.xml`, batch size 20 / 5-minute
  interval)
- Duplicate-running prevention at execution time (the claim mechanism
  itself, and the `(store_id, operation_scope_key)` unique constraint's
  interaction with concurrent claims)
- Cron drain behavior under concurrent workers (single-server,
  multi-worker, and — where possible — multi-server)
- The disconnect/in-flight-job race narrowing implemented by
  `_invoke_handler()`'s checkpoint-3 store-state re-check, and
  `action_disconnect()`'s cancellation sweep
- Multi-server / load-balanced behavior of the claim mechanism, where a
  suitable topology is available

**Explicitly out of scope** (unchanged, not implemented, not tested by
this plan):

- Product, customer, order, inventory, or fulfillment sync of any kind —
  no domain handler exists; every job type exercised by this plan is a
  core/diagnostic type (`core_dispatch_selftest`, optionally
  `core_test_connection`/`core_readiness_check`/`core_manual_maintenance`).
- Live Shopify API validation (VAL-B2) — no Shopify Admin API call is
  made by any scenario in this plan; only fake/no-op handlers and
  already-shipped core diagnostic job types are used.
- Token acquisition / OAuth (MBQ-05) — untouched.
- Setup wizard / UI — untouched; no operator-facing UI exists.
- Lite/Full packaging — untouched.
- Webhook implementation — untouched; no webhook controller exists.
- **Any code change.** This plan does not modify, and does not authorize
  modifying, any addon, test, manifest, XML/security, migration, or CI
  file. If live execution surfaces a defect, the fix is a separate,
  explicitly authorized implementation task — not part of this plan.

---

## 3. Risks being validated

Mapped to [`sync-engine-risk-register.md`](./sync-engine-risk-register.md)
and [`DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md)
§"Risks and required runtime validation."

### SRR-03 — Disconnect / in-flight-job race

- **Current status:** Open/unproven. Neither the Task 006A research
  package, `R31`, nor `R33` (three independently-produced shards) proves
  or disproves this race (`sync-engine-open-questions.md` Q17, Q30).
- **What Task 006C already does [Fact]:** `_invoke_handler()`
  (`shopify_connector_job_dispatch.py`) re-checks `store.state` (after
  `store.invalidate_recordset()`) immediately before invoking the
  registered handler ("checkpoint 3") and routes the job to `skipped` via
  `_transition_skipped()` if the store is no longer `connected` — the
  method's own docstring states this **"narrows, but... never claims to
  close,"** the race. Separately, `action_disconnect()`
  (`shopify_connector_store.py`) cancels every non-terminal business job
  for the store, including one in `blocked_manual_review`, clearing
  `manual_review_subreason` in the same `write()` (the PR #131 approved
  one-file exception, review artifact `4923059289`).
- **What remains unproven:** whether the timing between a concurrent
  `action_disconnect()` commit and an in-flight `ir.cron` drain worker's
  own checkpoint-3 re-check actually behaves as the code implies under
  real PostgreSQL transaction/commit timing — not merely as source
  reading suggests. Separately, and not mitigated by any existing
  checkpoint: the narrow window **after** checkpoint 3's re-check
  succeeds but **before or during** the handler call itself — today this
  window is empty of real risk only because every shipped handler
  (`core_dispatch_selftest`) is a no-op with no live Shopify write; once
  a real domain handler exists, this window is where an actual
  post-disconnect live write could occur, and no runtime evidence from
  this plan can pre-validate a handler that does not yet exist.
- **Evidence that would reduce/close this risk:** Scenarios 5, 6, and 7
  (§6) executed on a real Odoo/PostgreSQL runtime, with job-log rows
  (`from_state`/`to_state`/`event_type`/`message`) captured proving which
  path (skip vs. cancel vs. proceed) was actually taken for each timing
  variant tested.

### SRR-04 — Cron job-acquisition concurrency under real load

- **Current status:** Open/unproven — a "three-shard-corroborated open
  question" (`sync-engine-open-questions.md` Q18) that Odoo's RPC-layer
  automatic serialization retry (`retrying()`) does not appear to extend
  to `ir.cron`'s own domain-record-processing code.
- **What Task 006C already does [Fact]:** `_claim_for_dispatch()`
  (`shopify_connector_job.py`) selects candidate `queued`/due
  `retry_waiting` rows, calls `try_lock_for_update()` on the candidate
  recordset (a non-blocking, per-row PostgreSQL lock attempt — never a
  raw `SKIP LOCKED` reimplementation, never an advisory lock), then
  re-checks each successfully-locked row's actual `state`/`next_retry_at`
  under the lock via `.filtered(...)`, mirroring Odoo's own official
  cron-writing worked example. This is proven only via `TransactionCase`
  (single transaction, no real concurrent worker) — the method's own
  docstring states plainly: **"this method's behavior under actual
  multi-worker/multi-server execution is NOT proven by any unit test in
  this repository."**
- **What remains unproven:** whether two or more real concurrent
  `run_drain()` invocations against the same PostgreSQL database actually
  produce disjoint claimed sets with no double-claim, no deadlock, and no
  silent skip of a claimable row that should have been claimable.
- **Evidence that would reduce/close this risk:** Scenarios 2 and 3 (§6)
  executed with genuinely concurrent worker processes/threads against one
  database, with the resulting job `state`/`retry_count`/log rows proving
  each job was processed at most once.

### SRR-09 — Multi-server / load-balanced coordination

- **Current status:** Open/unproven — `R33` (PR #126) names this "a real
  operational pain point worth an explicit runtime test"
  (`sync-engine-open-questions.md` Q41/Q43); no source proves or
  disproves it for this project's actual deployment topology.
- **What Task 006C already does [Fact]:** the same
  `try_lock_for_update()`-based claim mechanism as SRR-04 — no
  additional cross-server coordination primitive (no advisory lock, no
  external coordinator) is implemented; DEC-025 §"Explicit non-decisions"
  states plainly that **no job-claiming concurrency mechanism selection
  beyond Task 006C's own stubbed-tested implementation is final.**
- **What remains unproven:** whether row-lock-only claiming, with no
  additional cross-server coordination, is sufficient when multiple Odoo
  application servers (not just multiple worker processes on one server)
  share one PostgreSQL database.
- **Evidence that would reduce/close this risk:** Scenario 8 (§6),
  requiring runtime topology C (§4) — the strongest evidence this plan
  can define; topology A or B evidence can only reduce, never close, this
  specific risk (see §9).

### Directly related risks (context, not separately re-tested by name)

- **SRR-01 (savepoint-count performance ceiling).** Relevant to Scenario
  2/8's batch size: PostgreSQL performance degrades past ~64 savepoints
  per transaction (`O8`). `DISPATCH_BATCH_SIZE = 20`
  (`shopify_connector_job_dispatch.py`) is already well below this
  ceiling, per Decision E's own stated rationale — this plan's scenarios
  should record the batch size actually used and confirm it stays at or
  below the shipped constant unless a future task deliberately revises
  it.
- **SRR-06 (repeat of the PR #121 failure pattern).** Not a technical
  hazard to test directly — it is the process justification for why this
  plan requires live-runtime evidence at all rather than accepting
  `TransactionCase`/static review as sufficient. Directly informs §10's
  execution order (never skip live proof in favor of static review
  alone).

---

## 4. Required runtime topology

Three topologies, in ascending order of evidentiary strength. **None is
available to this documentation-only session.**

### A. Single Odoo instance, multiple cron workers

One Odoo server process configured with `--max-cron-threads` ≥ 2 (or
multiple manually-triggered `run_drain()` calls launched concurrently
against the same running instance), one PostgreSQL database.

- Can validate: basic concurrent-claim behavior within one server
  process's own worker pool.
- **Cannot close SRR-09** — no second server process exists to prove
  cross-server coordination. **[Recommendation]** If only topology A is
  available, treat SRR-09 as *reduced in scope of concern for
  single-server deployments only*, never as closed.

### B. Multi-worker Odoo process against one PostgreSQL database

A single Odoo deployment (e.g. `--workers` > 0, multiple HTTP/cron
worker processes) against one shared PostgreSQL database — a stronger
variant of A, with genuinely separate OS processes (not just threads)
claiming rows concurrently.

- Can validate: concurrent worker behavior (SRR-04) with real
  process-level concurrency, not just thread-level.
- **Cannot fully validate multi-server/load-balanced behavior (SRR-09)**
  — still one Odoo deployment, one set of application-server code, not
  genuinely independent servers that could be provisioned, scaled, or
  restarted independently of each other.

### C. Two Odoo instances / Odoo.sh-equivalent multi-server topology (preferred / strongest)

Two independent Odoo application server instances (or an Odoo.sh
multi-instance-equivalent topology) both configured against the **same**
PostgreSQL database, both running `run_drain()` (via their own
`ir.cron` schedulers or manually triggered) concurrently.

- **This is the strongest evidence this plan can define for SRR-09** —
  the only topology that actually exercises "multiple Odoo application
  servers share one PostgreSQL database," which is SRR-09's own stated
  trigger condition.
- Still does not validate live Shopify API behavior (out of scope, §2).

**[Recommendation]** If topology C cannot be provisioned, execute
topology A and/or B and record explicitly, in the results document
(§11), which topology was actually used and which risk(s) it could and
could not address — never silently substitute a weaker topology's result
as evidence for a stronger topology's claim.

---

## 5. Test data setup

All test data below uses **only already-shipped models, fields, and
services** — no new field, model, or handler is created. `core_dispatch_
selftest` (Decision F's diagnostic job type, `_handle_core_dispatch_
selftest()`) is a **no-op** handler already registered in
`_get_handlers()` — it never calls Shopify and requires no new code to
exercise the drain loop safely.

1. **One connected Shopify store record** — a `shopify.connector.store`
   record with `state = 'connected'` (required for any business job to
   be created, per `Job.create()`'s enqueue-time gating). No real
   Shopify credential/token is required for this plan's scope — the
   store only needs to satisfy the `state == 'connected'` gate for job
   creation and the checkpoint-3 re-check.
2. **Several queued business jobs with same/different
   `operation_scope_key`** — created via `shopify.connector.job.enqueue.
   enqueue()` with `job_source` in `BUSINESS_JOB_SOURCES` (e.g.
   `'manual_sync'`), `job_type='core_dispatch_selftest'` (the no-op
   handler), and a synthetic `res_model`/`res_id`/`shopify_target_gid`
   combination. Two jobs sharing the same `(res_model, res_id,
   shopify_target_gid)` for the same store will collide on the
   `(store_id, operation_scope_key)` unique constraint while both remain
   non-terminal — use this deliberately to construct the "same scope
   key" case, and distinct target values for the "different scope key"
   case.
3. **`retry_waiting` jobs due now** — jobs with `state='retry_waiting'`
   and `next_retry_at` in the past (writable directly on the test
   record, since this is test-data setup, not production code).
4. **`retry_waiting` jobs not yet due** — same state, `next_retry_at` in
   the future.
5. **Core diagnostic jobs, if needed** — `core_dispatch_selftest` jobs
   with `job_source` outside `BUSINESS_JOB_SOURCES` (e.g. a core/
   maintenance source) if a scenario needs a non-business-gated job.
6. **A `blocked_manual_review` job** — a job with
   `state='blocked_manual_review'` and a valid `manual_review_subreason`
   (required by `_check_manual_review_subreason_required`), for Scenario
   7's disconnect-cancellation behavior.
7. **Fake/no-op handlers only; no Shopify API call** — every scenario in
   this plan uses `core_dispatch_selftest` (already a no-op) or
   already-shipped core job types (`core_test_connection`,
   `core_readiness_check`, `core_manual_maintenance`) exactly as merged.
   No new handler is written for this plan.

---

## 6. Validation scenarios

Each scenario below states its setup, the action to take, and the
expected result **as implied by currently merged code** — not an
aspirational or invented behavior. Where the current implementation does
not define a behavior (e.g. crash recovery), the scenario says so
explicitly rather than assuming one.

### Scenario 1 — Single drain baseline

- **Setup:** one drain worker, a handful of `queued` `core_dispatch_
  selftest` jobs (mixed business/core `job_source`).
- **Action:** call `run_drain()` once.
- **Expected result:** every claimed job transitions `queued` → `running`
  → `succeeded` exactly once; no duplicate processing; `job.log` rows
  exist for the `attempt`/`state_change` transitions with correct
  `from_state`/`to_state`.

### Scenario 2 — Concurrent cron workers on same database

- **Setup:** topology A or B (§4); two or more workers configured to
  call `run_drain()` at (as close to) the same time, against the same
  pool of eligible `queued` jobs.
- **Action:** trigger both/all workers concurrently (e.g. two manually
  triggered cron executions, or two `--workers` processes both running
  their own cron scheduler).
- **Expected result:** each job is claimed and processed **at most
  once** — the union of both workers' claimed sets is disjoint; no job
  ends in `succeeded` twice; no job is left unclaimed that should have
  been claimable.

### Scenario 3 — Skipped locked rows

- **Setup:** one worker manually holds a row lock on a candidate job
  (e.g. via `try_lock_for_update()` in an open, uncommitted transaction).
- **Action:** a second worker calls `_claim_for_dispatch()` /
  `run_drain()` while the first lock is still held.
- **Expected result:** the second worker's `try_lock_for_update()` call
  silently excludes the locked row from its returned recordset (per
  `_claim_for_dispatch()`'s own logic) and continues processing any
  other eligible, unlocked rows — no error, no hang, no duplicate claim
  once the first lock is released and the row is later reprocessed by a
  subsequent drain pass (if still eligible).

### Scenario 4 — `retry_waiting` due jobs

- **Setup:** test data items 3 and 4 (§5) — one `retry_waiting` job due
  now, one not yet due.
- **Action:** call `run_drain()`.
- **Expected result:** only the due job is claimed and processed
  (`_claim_for_dispatch()`'s domain filters on `next_retry_at <= now`);
  the not-yet-due job remains `retry_waiting`, untouched, with its
  `next_retry_at` unchanged.

### Scenario 5 — Disconnect before claim

- **Setup:** a store disconnected (`action_disconnect()` already run,
  `state='disconnected'`) before any drain attempt; any business job for
  that store that existed pre-disconnect has already been cancelled by
  `action_disconnect()`'s own sweep (§ code path, `shopify_connector_
  store.py`).
- **Action:** attempt to create a new business job for the disconnected
  store (via `enqueue()`); separately, call `run_drain()`.
- **Expected result, as implied by current code:** `Job.create()`'s
  enqueue-time gating (`_is_business_job_source` + `store.state !=
  'connected'`) raises `ValidationError` for a **new** business job
  attempt — no job is created. Any pre-existing business job is already
  `cancelled` (not reprocessed by `run_drain()`, since `cancelled` is a
  terminal state excluded from `_claim_for_dispatch()`'s candidate
  domain).

### Scenario 6 — Disconnect between claim/start and handler invocation

- **Setup:** a `queued` business job claimed and transitioned to
  `running` (`_start_running()` has committed); a concurrent
  `action_disconnect()` for that job's store commits **after** the
  `running` transition but **before** `_invoke_handler()`'s
  checkpoint-3 store-state re-check runs.
- **Action:** allow `_invoke_handler()` to proceed to its checkpoint-3
  re-check.
- **Expected result, as implied by current code:** `store.
  invalidate_recordset()` forces a fresh read; `store.state != 'connected'`
  is true; the job is routed to `skipped` via `_transition_skipped()`
  (`job.log` `event_type='state_change'`, `from_state='running'`,
  `to_state='skipped'`) — the handler is **never invoked**. This is the
  mechanism `_invoke_handler()`'s own docstring calls "checkpoint 3
  (SRR-03 narrowing)." **What this scenario cannot prove:** the narrower
  window after checkpoint 3 passes but before/during the handler call
  itself (see §3 SRR-03) — today empty of real risk only because
  `core_dispatch_selftest` is a no-op.

### Scenario 7 — `blocked_manual_review` disconnect cancellation

- **Setup:** test data item 6 (§5) — a job in `blocked_manual_review`
  with a populated `manual_review_subreason`.
- **Action:** call `action_disconnect()` for that job's store.
- **Expected result:** the job transitions to `cancelled`,
  `cancel_reason='Store disconnected.'`, `finished_at` set, and
  `manual_review_subreason` cleared (`False`) in the same `write()` —
  the PR #131 approved one-file exception. No `ValidationError` is
  raised by `_check_manual_review_subreason_required`. A `job.log` row
  (`event_type='state_change'`, `from_state='blocked_manual_review'`,
  `to_state='cancelled'`) is created. **Note:** this scenario is already
  covered by an existing `TransactionCase` unit test
  (`test_disconnect_cancels_business_jobs_in_new_dispatch_states`, per
  `task-006c-sync-engine-skeleton-validation-results.md` §B/§C) — its
  inclusion here is to confirm the same behavior holds under a live
  runtime, not because it is a genuinely untested code path.

### Scenario 8 — Multi-server drain

- **Setup:** topology C (§4) — two Odoo servers/instances sharing one
  PostgreSQL database, both with their own `ir.cron` scheduler (or both
  manually triggered) able to call `run_drain()`.
- **Action:** trigger both servers' drain passes concurrently against
  the same eligible job pool (mix of `queued` and due `retry_waiting`
  jobs).
- **Expected result:** no duplicate processing across servers (each job
  claimed by at most one server); no PostgreSQL deadlock; no job stuck
  in `running` with no server having actually invoked its handler; no
  duplicate `job.log` "attempt" rows for the same claim.

### Scenario 9 — Crash/interruption observation

- **Setup:** a `queued` job claimed and transitioned to `running`
  (`_start_running()`'s `write()` committed); the worker process is then
  killed/interrupted before the job reaches `succeeded` or any failure
  transition.
- **Action:** observe the job's state after the interruption, then
  attempt another `run_drain()` pass.
- **Expected observation — do not invent a recovery behavior not
  implemented:** **[Fact]** `_claim_for_dispatch()`'s candidate domain
  only selects `queued` or due `retry_waiting` jobs — `running` is
  never a candidate state. No code in `shopify_connector_job.py` or
  `shopify_connector_job_dispatch.py` re-claims, times out, or resets a
  job stuck in `running`. **This plan does not know, and must not
  assume, whether the interrupted transaction itself ever committed the
  `running` write** — that depends on Odoo's own cron transaction/commit
  granularity, which is exactly what this scenario must observe on a
  real runtime, not infer from source reading. Record plainly: (a)
  whether the job is left in `running` indefinitely after the
  interruption, (b) whether a subsequent `run_drain()` pass ever
  reclaims it, and (c) whether this indicates a future checkpoint/
  resume or stuck-job-recovery task is needed (`sync-engine-open-
  questions.md` Q7, "checkpoint/resume ownership... undesigned" —
  already an open question, not resolved or newly invented by this
  scenario).

---

## 7. Evidence to collect

For every scenario in §6, record:

- **Exact command / operational action** — e.g. `env['shopify.connector.
  job.dispatch'].run_drain()` invoked from an Odoo shell (`odoo-bin
  shell`), the exact number of concurrent processes/threads used, and
  (for topology B/C) the exact `--workers`/`--max-cron-threads` /
  server-count configuration in effect.
- **Logs to capture** — the full set of `shopify.connector.job.log` rows
  created during the scenario (ordered by `occurred_at`), and any
  PostgreSQL server log lines relevant to lock waits/deadlocks (e.g. from
  `pg_stat_activity`/`pg_locks` if inspected).
- **Database/job records to inspect** — the full `shopify.connector.job`
  row(s) involved, before and after the scenario.
- **Fields to verify**, where relevant to the scenario:
  - `state`
  - `retry_count`
  - `error_class`
  - `manual_review_subreason`
  - `started_at`
  - `finished_at`
  - `next_retry_at`
  - `operation_scope_key`
  - `idempotency_key`
  - `cancel_reason` (disconnect scenarios)
  - job log rows: `event_type`, `from_state`, `to_state`, `message`,
    `technical_detail` (confirm redaction — `redact()` applied, no raw
    secret/token ever present)
- **Pass criteria** — stated per scenario in §6 and summarized in the
  matrix (§8).
- **Fail criteria** — any deviation from the stated expected result
  (duplicate processing, unhandled exception/deadlock, a job claimable
  when it should not be or vice versa, an unexpected state transition).
- **Screenshots / log excerpts expected from Odoo.sh, if applicable** —
  the Odoo.sh backend's own build/log view for the branch database used,
  and (for topology C) evidence that two distinct server/branch
  processes were actually involved, not one process invoked twice.

---

## 8. Pass/fail matrix

| Scenario | Required topology | Pass criteria | Failure symptoms | Risk reduced/closed | Evidence artifact required |
| --- | --- | --- | --- | --- | --- |
| 1. Single drain baseline | Any (A minimum) | Each job processed exactly once; correct state transitions; log rows created | Job not claimed; job left in wrong state; missing log row | Establishes baseline only — no concurrency risk addressed | Job records + log rows before/after |
| 2. Concurrent cron workers, same DB | A or B | Each job processed at most once across all workers | Any job processed more than once; any job double-claimed | SRR-04 (reduced if A; reduced further if B) | Job/log records from both workers, timestamps correlated |
| 3. Skipped locked rows | A or B | Second worker excludes locked row silently, continues with others | Error/hang on second worker; duplicate claim once first lock releases | SRR-04 | Log/trace showing lock attempt outcome per worker |
| 4. `retry_waiting` due jobs | Any | Only due job claimed; future job untouched | Future job claimed early; due job not claimed | Not concurrency-specific; confirms claim-domain correctness under load | Before/after job records for both jobs |
| 5. Disconnect before claim | Any | New business job creation raises `ValidationError`; pre-existing jobs already cancelled, not reprocessed | New job created despite disconnect; cancelled job reprocessed | SRR-03 (partial — pre-claim case) | Exception evidence; job state before/after |
| 6. Disconnect between start and handler invocation | A or B (timing control needed) | Job routed to `skipped`; handler never invoked; log row `running`→`skipped` | Handler invoked despite disconnect; job proceeds to `succeeded` | SRR-03 (reduces; does not close — see §3/§9) | Log row with `from_state`/`to_state`; confirmation handler not invoked |
| 7. `blocked_manual_review` disconnect cancellation | Any | Job cancels cleanly; `manual_review_subreason` cleared; no `ValidationError` | Constraint violation raised; subreason left set | SRR-03 (confirms existing fix under live runtime) | Job record + log row `blocked_manual_review`→`cancelled` |
| 8. Multi-server drain | C (strongest); A/B cannot substitute | No duplicate processing; no deadlock; no stuck `running` jobs; no duplicate `attempt` logs | Duplicate processing across servers; deadlock; stuck job; duplicate logs | SRR-09 (only topology C evidence reduces/closes this) | Job/log records correlated across both servers' identities |
| 9. Crash/interruption observation | Any (A minimum) | Observation recorded honestly (no invented recovery) | N/A — this scenario has no pass/fail in the usual sense; the point is honest observation | Informs whether a future checkpoint/resume task (Q7) is needed — does not itself reduce/close SRR-03/04/09 | Job state immediately after interruption + after next drain pass |

---

## 9. What this plan can and cannot prove

- **Passing single-worker tests (Scenario 1) does not prove concurrency.**
  It only confirms the baseline state machine works when there is no
  contention at all.
- **Passing multi-worker single-server tests (Scenarios 2, 3) does not
  fully prove multi-server behavior.** Topology A/B evidence can reduce
  SRR-04 and partially reduce SRR-09 (by ruling out simple double-claim
  bugs within one server's own worker pool), but cannot close SRR-09 —
  SRR-09's own trigger condition is specifically *multiple Odoo
  application servers* sharing one database, which A/B do not exercise.
- **Passing multi-server tests (Scenario 8, topology C) reduces SRR-09
  but does not validate Shopify live API behavior.** No scenario in this
  plan makes a real Shopify Admin API call — VAL-B2 remains entirely
  separate and unaffected.
- **This plan does not close VAL-B2, MBQ-05, TD-002, product first-sync
  dedup thresholds, Lite/Full packaging, or checkpoint/resume ownership**
  unless a future session explicitly executes the relevant test and a
  decision-maker (ChatGPT) explicitly closes the corresponding item.
  Scenario 9's observation may **inform** whether a checkpoint/resume
  task is needed, but this plan does not itself decide that question.
- **Even a fully "green" run of every scenario in this plan does not
  mean concurrency is proven for all time or all conditions.** It means
  the specific scenarios executed, under the specific topology available
  at execution time, produced the recorded evidence — no more, no less.
  Any claim beyond that must not appear in the future results document
  (§11) or any handoff citing it.

---

## 10. Recommended execution order

1. **Baseline install / full core suite green** — confirm the existing
   `shopify_connector_core` automated test suite passes on the target
   runtime before starting any manual concurrency scenario (a regression
   here would invalidate any concurrency observation layered on top).
2. **Single drain baseline** (Scenario 1).
3. **Concurrent same-server workers** (Scenarios 2, 3, 4).
4. **Disconnect race scenarios** (Scenarios 5, 6, 7).
5. **Multi-server, if available** (Scenario 8) — the highest-value,
   highest-effort scenario; do not skip the earlier scenarios to reach
   this one, since a same-server defect would confound multi-server
   results.
6. **Crash/interruption observation** (Scenario 9) — run last, since it
   is destructive/disruptive to the runtime's normal operation.
7. **Final evidence review by ChatGPT** — the results document (§11) is
   reviewed and each risk's status (open/reduced/closed) is confirmed or
   corrected by ChatGPT before any next step is authorized.

---

## 11. Required result document

After live execution, a future session must create:

**`docs/05-qa/sync-engine-concurrency-validation-results.md`**

mirroring the evidence-record pattern already used by
`task-006c-sync-engine-skeleton-validation-results.md` and
`task-003-validation-results.md`. It must record:

- **Environment** — Odoo.sh branch (or equivalent), hosting details
  relevant to reproducibility.
- **Commands** — the exact commands/operations executed for each
  scenario.
- **Odoo version** — the exact Odoo version the runtime ran.
- **Worker/server topology** — which of A/B/C (§4) was actually used,
  and exact worker/process/server counts.
- **DB topology** — one shared PostgreSQL database confirmed (and its
  connection details redacted as this project's security rules require).
- **Test data** — the exact records created per §5, redacted of any
  real Shopify credential (none should exist in this plan's scope).
- **Results per scenario** — pass/fail per §8's matrix, with the actual
  observed field values (§7).
- **Logs/screenshots references** — pointers to captured evidence
  (stored per this project's existing evidence-capture convention,
  `/docs/00-source-materials` for external sources; job/log data can be
  quoted directly in the results document since it originates from this
  project's own database, not a third party).
- **Pass/fail conclusion** — stated per scenario, not as one aggregate
  verdict.
- **Whether each risk (SRR-03, SRR-04, SRR-09) remains open, reduced, or
  closed** — using the same three-state vocabulary this plan uses
  throughout, never asserting "proven" as a synonym for "closed."
- **ChatGPT review decision** — accepted / accepted with corrections /
  revise / reject, per `quality-feedback-loop.md` §2.

This plan does **not** create that results document — it defines what
the document must contain once live execution occurs.

---

## 12. Recommendation

**[Recommendation]** The next future session after this plan should
execute the validation described above **only if an Odoo/Odoo.sh runtime
is available** to that session (topology A at minimum; topology C
preferred). Executing against a topology this plan did not define (or
skipping the execution order in §10) risks producing evidence that
cannot be honestly mapped to this plan's pass/fail criteria.

**If no runtime is available**, the recommended parallel track is
**MBQ-05 token acquisition / auth-distribution planning** (Candidate 4 in
`next-task-recommendation-after-task-006c.md` §C/§D) — a fully
docs-only-executable research/decision task addressing the scalable,
many-unrelated-customer distribution/auth architecture question, which
does not compete for the same runtime-access constraint this plan
requires and has been "not yet scoped" across multiple prior sessions
(DEC-023 §3.2, DEC-025 "Explicit non-decisions").

---

## Explicit non-authorizations

This document does not:

- Authorize Task 010, any other domain-sync task, a setup wizard, OAuth/
  token-acquisition code, or any Lite/Full packaging implementation.
- Authorize the live concurrency test itself, or any code change that
  might result from a defect the future test discovers.
- Resolve VAL-B2, MBQ-05, TD-002, the fulfillment API model, product
  first-sync dedup thresholds, Lite/Full packaging, checkpoint/resume
  ownership, or SRR-03/SRR-04/SRR-09 — every one remains exactly as open
  as its own cited source states.
- Open, extend, or reinterpret any implementation gate. The only open
  gate remains the limited core-only, zero-UI gate
  (`limited-core-implementation-gate.md`), whose scope Task 006C's own
  already-merged skeleton already exhausted for the core sync-engine; no
  further gate is opened by this document.
- Claim that concurrency is proven, reduced-to-zero-risk, or otherwise
  settled. Every risk in §3 remains labelled exactly as open as the risk
  register and DEC-025 already state it.
- Create, modify, or imply authorization for any addon/code, test,
  manifest, XML/security/ACL, migration, CI/workflow, domain module, UI/
  view/menu/action/wizard/controller, webhook, or OAuth file.

---

## Evidence / references

- [`../07-implementation-plan/next-task-recommendation-after-task-006c.md`](../07-implementation-plan/next-task-recommendation-after-task-006c.md)
  — access: Accessible, this repository, observed 2026-07-09; the
  recommendation this plan implements.
- [`task-006c-sync-engine-skeleton-validation-results.md`](./task-006c-sync-engine-skeleton-validation-results.md)
  §F — access: Accessible, this repository, observed 2026-07-09.
- [`sync-engine-risk-register.md`](./sync-engine-risk-register.md) SRR-01,
  SRR-03, SRR-04, SRR-06, SRR-09 — access: Accessible, this repository,
  observed 2026-07-09.
- [`sync-engine-open-questions.md`](./sync-engine-open-questions.md) Q7,
  Q17, Q18, Q30, Q41, Q43 — access: Accessible, this repository, observed
  2026-07-09.
- [`../04-decisions/DEC-025-task-006-sync-engine-gate.md`](../04-decisions/DEC-025-task-006-sync-engine-gate.md)
  §"Risks and required runtime validation," §"Explicit non-decisions" —
  access: Accessible, this repository, observed 2026-07-09.
- [`../07-implementation-plan/limited-core-implementation-gate.md`](../07-implementation-plan/limited-core-implementation-gate.md)
  — access: Accessible, this repository, observed 2026-07-09.
- [`val-b2-closure-plan.md`](./val-b2-closure-plan.md) — structural
  pattern this document mirrors — access: Accessible, this repository,
  observed 2026-07-09.
- [`quality-feedback-loop.md`](./quality-feedback-loop.md) §2 (review
  decision categories) — access: Accessible, this repository, observed
  2026-07-09.
- [`technical-debt-register.md`](./technical-debt-register.md) — checked
  for relevance (TD-001 resolved, TD-002 open and unrelated to
  concurrency) — access: Accessible, this repository, observed
  2026-07-09.
- `addons/shopify_connector_core/models/shopify_connector_job.py`,
  `shopify_connector_job_dispatch.py`, `shopify_connector_job_log.py`,
  `shopify_connector_job_enqueue.py`, `shopify_connector_store.py` — read
  directly (not modified) this session to ground every field name,
  method behavior, and job-state transition cited above in the actual
  merged code, per `CLAUDE.md` §7's "cite it precisely" requirement —
  access: Accessible, this repository, observed 2026-07-09.

**Next step:** execute this plan only if a live Odoo/Odoo.sh runtime is
available; otherwise proceed to MBQ-05 token acquisition/auth-
distribution planning as a parallel docs-only track (§12). Either way,
ChatGPT review of this plan itself precedes both.

---

## 13. Planning-completion addendum (2026-07-10, AR-042 session — plan audit; scenarios above unchanged)

> Appended by the MVP planning-completion session after auditing this
> plan against the required concurrency-proof planning dimensions
> (same-job competing workers; multi-worker; multi-server; retry races;
> duplicate prevention; claim expiry; crash recovery; transaction
> boundaries; idempotency; deadlocks; lock contention; performance;
> harness; pass/fail; evidence template). Verdict: **the plan is
> execution-complete for every dimension except explicit performance
> capture, added below.** OP-22 / SRR-03 / SRR-04 / SRR-09 (and the
> runtime questions Q17/Q18/Q30/Q31/Q41/Q43) are hereby classified
> `[External validation required]` — live/runtime validation items, not
> planning gaps. Nothing below modifies §1–§12, executes anything, or
> claims any concurrency property is proven.

### 13.1 Dimension audit result

Covered by the existing plan: competing workers on the same job pool
(Scenarios 2/3/8), retry races (Scenario 4 + the retry-scheduling test
suite), duplicate prevention (claim mechanism + `(store_id,
operation_scope_key)` interplay, Scenarios 2/8), crash behavior
observation without invented recovery (Scenario 9 — explicitly feeds
the Q7 checkpoint/stuck-job question), disconnect/transaction-boundary
races (Scenarios 5–7), deadlock/lock-contention observation (§7's
`pg_locks`/`pg_stat_activity` capture; Scenario 8 fail symptoms),
idempotency (§5 test data + constraints), topology ladder A/B/C with
honest evidence-strength limits (§4/§9), execution order (§10), result
document contract (§11). **Gap found: no explicit performance-metric
capture was required.** Closed by §13.2.

### 13.2 Performance capture requirement (added)

For Scenarios 1, 2, and 8, the executing session must additionally
record, per drain pass: wall-clock duration of `run_drain()`; jobs
claimed/processed per pass (vs `DISPATCH_BATCH_SIZE = 20`); per-job
handler latency (from the `attempt`/`state_change` log-row
`occurred_at` deltas); PostgreSQL lock-wait counts observed during the
pass (`pg_stat_activity` sampled before/after); and, for topology B/C,
total throughput across all workers (jobs/minute) with the worker count
stated. These are **observations for the release-hardening baseline**
(SRR-01's savepoint-ceiling context), not pass/fail criteria — no
performance number in this addendum is a target.

### 13.3 Standing classification

Until a session with a live Odoo.sh (topology A minimum, C preferred)
runtime executes §6 and writes
`docs/05-qa/sync-engine-concurrency-validation-results.md` per §11, no
planning session may claim concurrency safety, and every Task 012–015
planning packet must continue to carry the "claim/dispatch mechanism is
not proven under real concurrent-worker/multi-server execution" caveat
verbatim.
