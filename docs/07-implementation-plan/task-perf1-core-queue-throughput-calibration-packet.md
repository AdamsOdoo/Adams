# Task PERF-1 — Core Queue Throughput Calibration: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing **re-review comment `4945129824`
> item 5** (PB-19 has no gated implementation owner) and **final-
> convergence comment `4947866018` item 1** (the packet's transaction/
> lock model was false and did not follow Odoo 19's cron-progress
> contract). PB-19 requires ≥ 600 jobs/hour while the accepted merged
> defaults (5-min drain cron × batch 20) *schedule* at most ~240
> claims/hour — a *mathematically known* planning gap with, until now,
> **no gated task, allowed files, or tests to close it**. This packet
> creates that task, and — per comment `4947866018` — makes PERF-1 own
> **transaction isolation and the official `ir.cron._commit_progress()`
> batching pattern**, not merely batch/cadence parameters.
>
> **Merged reality (re-read 2026-07-11, corrected):** the claim
> primitive is **`try_lock_for_update()`** (Odoo 19's official
> row-locking primitive — `shopify_connector_job.py`
> `_claim_for_dispatch()` lines 307–352), **not** a raw
> `FOR UPDATE SKIP LOCKED` string; and `run_drain()`
> (`shopify_connector_job_dispatch.py` lines 114–120) claims a whole
> recordset then loops `_dispatch_one` over it **inside one uncommitted
> cron transaction with no `_commit_progress` call**. PostgreSQL row
> locks are transaction-scoped, so every claimed row's lock is held for
> the *entire* pass — including across each future handler's Shopify
> network call. The prior packet's claim "no lock is held across a
> Shopify network call" was therefore **false** and is withdrawn.
>
> Evidence: merged core dispatcher/claim re-read 2026-07-11
> (`shopify_connector_job_dispatch.py` `run_drain()`/`_dispatch_one()`;
> `shopify_connector_job.py` `_claim_for_dispatch()` using
> `try_lock_for_update()`; `data/shopify_connector_cron_drain.xml`
> `interval_number=5`, `interval_type=minutes`); official Odoo 19 cron
> contract (`odoo/odoo` branch `19.0`,
> `odoo/addons/base/models/ir_cron.py`: `_commit_progress(self,
> processed=0, *, remaining=None, deactivate=False) -> float` returns
> the remaining cron time in seconds, "If called from outside the cron
> job, the progress function call will just commit"; `_notify_progress`
> is `@api.deprecated("Since 19.0, use _commit_progress")`); performance
> budgets (`../03-architecture/performance-budgets.md` PB-19/PB-18) and
> the concurrency plan
> (`../05-qa/sync-engine-concurrency-validation-plan.md` §13.2). API
> version posture 2026-07.

## 1. Why this task exists (the known gap)

**[Fact — merged repository state]** The drain cron
(`ir_cron_shopify_connector_job_dispatch_drain`) fires every **5
minutes** and calls `run_drain()`, which claims up to **20** jobs via
`Job._claim_for_dispatch(20)` (`try_lock_for_update()` on the
candidate rows) and then loops `_dispatch_one` over the whole claimed
set **in one transaction, with no commit between jobs**. The *claim
ceiling* is `20 jobs / 5 min = 240 claims/hour` on topology A (single
worker). **[Fact — budgets]** PB-19 sets ≥ **600 jobs/hour** so a
5k-job onboarding import (customers + products) finishes inside one
working day (~8.3 h at 600/h). 240/h ⇒ ~20.8 h — two working days for
the same onboarding, which fails the operator-experience bar.

**[Fact — transaction model, corrected per `4947866018`]** Because the
claimed rows are locked with `try_lock_for_update()` and the pass never
commits until the cron transaction returns, **all** claimed locks are
held for the full pass, and a single unexpected SQL/ORM error inside
any handler would roll back the *entire* pass. Raising the batch under
this model would make both problems worse. The throughput gap is
therefore not a pure "batch number" tuning; it must be owned together
with the transaction/lock model. This is arithmetic and a known
platform-contract gap, not an external unknown; it must be owned by a
gated task with exact allowed files, tests, and acceptance budgets.

## 2. Objective, scope, non-goals

Make the drain loop follow **Odoo 19's official cron-progress
contract** — process one job at a time inside a per-job savepoint,
`_commit_progress()` after each, re-claim after each commit, and return
when the cron time budget is exhausted — so that (a) no row lock is
held across another job's network call, (b) a completed job survives a
later job's failure or a crash, (c) an unexpected error in one job
cannot poison the rest of the pass, and (d) throughput becomes
latency-bound rather than a fixed 240/h scheduling ceiling. Then prove
a configuration that sustains ≥ 600 jobs/hour on topology A against a
representative handler-duration profile, with Shopify backpressure and
recorded concurrency evidence. **Non-goals:** no change to the
`try_lock_for_update()` claim/re-check semantics (kept — it is the
correctness primitive; only *when the transaction commits* changes);
**no overlapping-execution / multi-worker topology** (topology B is a
Phase-2 concurrency item, RA-020-adjacent — named, out of scope; the
withdrawn `max_in_flight` idea moves there, §3); no error-registry,
retry-constant, or state-machine change; no per-job business logic; no
UI (settings UI is UI-phase — config is read from `ir.config_parameter`
here); no webhook/OAuth surface; no domain-module edits.

## 3. Decision closures (D-PERF1-1 … D-PERF1-6) — each Proposed

**D-PERF1-1 — `_commit_progress`-driven drain loop (the transaction
model, `4947866018` item 1).** `run_drain()` is reworked from
"claim-N-then-loop-in-one-transaction" to the official Odoo 19
cron-progress pattern:

1. It **claims one job at a time** (`_claim_for_dispatch(1)` — the
   merged `try_lock_for_update()` + under-lock state re-check, unchanged),
   so at any instant only the in-flight job's row is locked.
2. It **dispatches that job inside a dispatch-level savepoint**
   (`with self.env.cr.savepoint():` around `_dispatch_one(job)`), so an
   unexpected SQL/ORM error rolls back only that job and is routed to
   the existing failure path — it can never poison the rest of the pass.
3. It calls `remaining = self.env['ir.cron']._commit_progress(1,
   remaining=<claimable_count>)` **after each job** (the official 19.0
   API — verified signature `_commit_progress(processed=0, *,
   remaining=None, deactivate=False) -> float`). The commit **releases
   the job's row lock** (transaction-scoped) *before* the next claim,
   and **durably persists** the completed job's state/retry/audit writes.
4. It **re-claims after each commit** (loop back to step 1).
5. It **returns immediately** when `_commit_progress()` reports no
   remaining cron time (`<= 0`), when the queue is drained
   (`_claim_for_dispatch(1)` returns empty — a final `_commit_progress`
   commits and stops), or when the per-pass cap `drain_batch_size` is
   reached (defense-in-depth alongside the time budget).

`drain_batch_size` (`ir.config_parameter`
`shopify_connector.drain_batch_size`, Integer, **default 20** — the
merged value, seeded by a NEW `noupdate=1` record; clamped to
`[1, 500]`, malformed/oversized → default + one logged warning) is thus
redefined as the **per-pass job cap** (how many single-job
claim→process→commit cycles one invocation runs before yielding), *not*
a single locked claim of 20 rows. **Out-of-cron behavior (explicit):**
per the official docstring, `_commit_progress()` "called from outside
the cron job … will just commit" and returns effectively unlimited
time, so a manual/`test` invocation of `run_drain()` drains the queue
committing per job (no time-budget early return) — recorded and tested.

**D-PERF1-2 — Configurable cadence (documented lever, ceiling only).**
The drain cadence is the `ir.cron` `interval_number`/`interval_type` on
the drain record — an admin-adjustable field. `batch_cap × passes/hour`
is the **claim/scheduling ceiling**, **not** actual throughput: with
the per-job-commit loop a single pass now processes jobs until its cron
time budget is spent, so real throughput is bounded by **per-job
handler latency**, not by a fixed 20-per-pass number. This packet
documents the two calibration levers (per-pass cap × cadence) and
their ceiling; it does **not** hardcode a new interval (leaving the
merged 5-min default). Because the loop is latency-bound, the reference
configuration to reach PB-19 is **the 5-min cron with a per-pass cap
raised enough that the cron time budget, not the cap, is the limit**
(recorded at the calibration run); a shorter cadence is the alternative
lever. Changing the cron interval is an `ir.cron` data edit, not a code
path — the packet's code change is the drain-loop rework + the batch
parameter + backpressure only.

**D-PERF1-3 — Lock-safety, atomicity, and crash-survival (invariants,
corrected).** With the D-PERF1-1 loop:
- **Lock release between jobs (proven):** claim-one + `_commit_progress`
  per job means only the current job's row is ever locked, and its lock
  is released at its own commit before the next claim — **no lock is
  held across another job's Shopify network call** (the corrected,
  now-true statement; the prior "no lock across a network call at all"
  claim is withdrawn — the current job *does* hold its own row lock
  across its own handler, which is correct and bounded).
- **No double-claim:** `try_lock_for_update()` (merged primitive, kept)
  plus the under-lock state re-check means a concurrent claimer skips a
  locked/already-moved row; after a commit the row is `running`/terminal,
  so the under-lock re-check (`state == 'queued'` / due `retry_waiting`)
  rejects re-claim — a committed job is never re-processed.
- **Per-job atomicity:** each job's state/retry/`error_class`/audit
  writes happen inside its savepoint and are committed together by that
  job's `_commit_progress`, or rolled back together — never a half-written
  job.
- **Crash survival:** because progress commits after each job, a crash
  or a later job's hard failure **cannot undo already-completed jobs**
  (they are committed); the next cron pass resumes from the queue with
  no re-processing of committed work.

**`max_in_flight` is withdrawn from topology A (`4947866018` item 1).**
A single sequential cron with per-job commit has no overlapping
in-flight execution to cap, and any "overlap cap" spanning committed
per-job states would be a multi-worker concurrency control that Odoo's
same-cron scheduler does not provide. Overlap/parallelism is therefore
**deferred to the separate multi-worker concurrency plan** (topology B,
`../05-qa/sync-engine-concurrency-validation-plan.md` §13.2), not
claimed here. The `drain_max_in_flight` parameter is removed from this
packet's scope.

**D-PERF1-4 — Shopify throttling / backpressure interaction.** Raising
the effective drain rate must not breach Shopify's cost budget. The
merged API client already paces on `throttleStatus` (SRR-adjacent);
PERF-1 adds a **backpressure rule** evaluated per store **before
claiming the next job**: when the store's most recent recorded throttle
head-room is low, the drain **defers** that store's jobs for the rest
of the pass (a documented linear back-off toward "process none of that
store this pass"), so throughput self-limits under throttle pressure
instead of forcing 429s. Backpressure never *raises* the rate; it only
skips/defers claims. Stores with no recent throttle signal are
processed normally.

**D-PERF1-5 — Benchmark procedure (the acceptance evidence, revised
`4947866018` item 1).** `batch ÷ cadence` arithmetic against a stub
handler is **not** accepted as throughput evidence. The benchmark runs
against a **representative handler-duration profile**:
- (a) the merged default cadence with the merged cap (regression
  baseline) and the reference PB-19 configuration, each measured as
  **sustained jobs/hour completed** over a ≥ 5-minute wall-clock window
  with handlers stubbed to a **calibrated per-job latency drawn from a
  dev-store representative read profile** (product/customer/order read
  latency measured on the dev store, or an explicit evidence-backed
  latency profile recorded in the validation record — not a
  zero-cost stub);
- (b) a **per-job-commit proof**: after processing K jobs the run is
  interrupted; the first K jobs are committed and survive, the queue
  resumes with no re-processing (crash-survival + lock-release evidence);
- (c) a **savepoint-isolation proof**: one job raising an unexpected
  SQL/ORM error is routed to failure while the surrounding jobs commit
  normally;
- (d) a **throttle-limited fake-client run** proving the D-PERF1-4
  back-off engages and no 429 is forced.
Evidence (numbers + config + the latency profile used) goes in the
validation record and feeds PB-19's "provisional → measured
YYYY-MM-DD" recalibration rule. **≥ 600 jobs/hour stays the provisional
product target** unless the measured latency profile justifies a
recorded recalibration (which is then reflected in PB-19, not silently
lowered here).

**D-PERF1-6 — Sequencing.** PERF-1 is a **core** task sequenced **after
the domain tasks are mergeable and before performance UAT** (master
plan §2), so the calibration runs against realistic job shapes and the
UAT performance scenarios (27–28) assert an already-tuned dispatcher.
It may run in parallel with the P-B concurrency-plan execution (they
share the same runtime evidence surface). Prerequisite: merged core
dispatcher runtime-green (fact) — no domain dependency in the code, only
in the realism of the benchmark latency profile.

## 4. Allowed / forbidden files (exhaustive)

**Allowed:**
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (the `run_drain()` `_commit_progress`-driven per-job-savepoint loop;
  batch-cap parameter resolution; the D-PERF1-4 backpressure read —
  nothing else; the `try_lock_for_update()` claim/re-check in
  `shopify_connector_job.py` is **not** edited)
- `addons/shopify_connector_core/data/shopify_connector_config_params.xml`
  (NEW, `noupdate=1` — seeds `drain_batch_size=20`)
- `addons/shopify_connector_core/data/shopify_connector_cron_drain.xml`
  (comment only — documents the cadence lever; the merged 5-min default
  is unchanged)
- `addons/shopify_connector_core/__manifest__.py` (data entry + version
  bump)
- `addons/shopify_connector_core/tests/test_dispatch_throughput.py` (NEW)
  + `addons/shopify_connector_core/tests/__init__.py` (one import line)
- `docs/05-qa/task-perf1-validation-results.md` (NEW)
- `docs/05-qa/architecture-review-log.md` (append one AR row)
- `docs/01-research/research-handoff.md` (top entry)

**Forbidden:** the `try_lock_for_update()` claim/re-check semantics in
`shopify_connector_job.py` (kept verbatim); the job state machine,
error registry, retry constants, readiness, store lifecycle, and every
other core file/line; all domain modules; ACL/CSV; views/UI;
webhooks/OAuth/CI; `adams_base`; `main`; plain `dev`.

## 5. Tests (`test_dispatch_throughput.py`)

1. **Per-job commit + lock release (D-PERF1-1/3):** `run_drain()`
   processes claimed jobs one at a time, calling `_commit_progress`
   after each (patched/observed); after a job commits, its row is no
   longer locked and its state is durable — asserted by a second
   claimer seeing the committed job as non-claimable and the remaining
   queue as claimable.
2. **Savepoint isolation (D-PERF1-3):** a job whose handler raises an
   unexpected `Exception`/SQL error is routed to `unknown_system_error`
   failure while the jobs before and after it commit successfully — one
   poisoned job never aborts the pass.
3. **Crash/failure survival (D-PERF1-3/5b):** interrupting the loop
   after K committed jobs leaves those K durable; a fresh `run_drain()`
   resumes the rest with no re-processing of the committed K.
4. **Time-budget return (D-PERF1-1):** with `_commit_progress` stubbed
   to report no remaining time, `run_drain()` returns after the current
   job (does not drain the whole queue in one pass).
5. **Out-of-cron behavior (D-PERF1-1):** invoked outside a cron context,
   `_commit_progress` "just commits" and `run_drain()` drains the queue
   with per-job commits and no early time-budget return.
6. **Batch-cap parameter (D-PERF1-1):** `drain_batch_size` read from
   `ir.config_parameter`; unset → default 20; a raised value processes
   more single-job cycles per pass; out-of-range clamps to `[1,500]`
   with a logged warning.
7. **Backpressure (D-PERF1-4):** a fake client reporting low throttle
   head-room defers that store's jobs for the pass; full head-room
   processes normally; back-off never raises the rate.
8. **Throughput target (D-PERF1-5):** the representative-latency-profile
   harness records sustained jobs/hour at the merged default and at the
   reference configuration (≥ 600/h), with the latency profile recorded
   — no zero-cost-stub arithmetic asserted as throughput.
9. All pre-existing dispatch/retry suites stay green
   (`test_job_dispatch.py`, `test_job_retry_scheduling.py`) — the
   drain-loop rework and batch parameter must not change claim ordering,
   routing, or retry scheduling.
Source guards: no Shopify call added to the drain; the
`try_lock_for_update()` claim/re-check in `shopify_connector_job.py` is
unchanged (string/AST scan asserts the claim method body is untouched).

## 6. Gate criteria (15-pattern, abbreviated)

1 merged core runtime-green ✅(fact); 2–3 exact names ✅(§3, incl.
`_commit_progress`, `try_lock_for_update`); 4 files ✅(§4); 5
batch-cap/clamp thresholds fixed ✅(D-PERF1-1); 6–8 no domain/UI/webhook
scope ✅; 9 tests ✅(§5); 10 rollback ✅(§7); 11 no live-Shopify
dependency in code (benchmark uses a recorded latency profile, not a
live call) ✅; 12 gate-act reconfirmation; 13 the flagged calls
explicit: cadence-as-`ir.cron`-lever (D-PERF1-2), per-job-commit loop
adopting `ir.cron._commit_progress` (D-PERF1-1), backpressure defer
design (D-PERF1-4), `max_in_flight` withdrawal to the multi-worker plan
(D-PERF1-3); 14 the PB-19 acceptance number bound to a representative-
latency-profile measurement ✅(D-PERF1-5); 15 lock-release / savepoint-
isolation / crash-survival invariants preserved and tested
✅(D-PERF1-3/5).

## 7. Odoo.sh + validation / acceptance budgets / rollback

Odoo.sh: full suites green (verbatim quote, OP-43). **Build-time
verification (named):** the exact 19.0 `ir.cron._commit_progress`
signature and return contract are verified against the 19.0 source
in-session before use; STOP-and-report if the signature differs (no
improvisation; same rule as the domain packets' API-verification gate).
**Acceptance budgets:** the D-PERF1-5 benchmark demonstrates ≥ 600
jobs/hour sustained (PB-19) at the recorded reference configuration on
topology A against the recorded representative latency profile, per-job
commit / lock-release / savepoint-isolation proven, and backpressure
engaging under simulated throttle — all in the validation record, fed
back to PB-19's recalibration line. **Rollback:** revert the single PR
— `run_drain()` returns to the merged claim-N-then-loop-in-one-
transaction form (240/h ceiling, single-transaction pass, documented);
the seeded `ir.config_parameter` row and the cron comment may **remain
inert/orphaned** (a normal code revert does **not** drop them — no
destructive schema cleanup is assumed; any cleanup is a separately
tested migration); no business, job, or audit data is removed; the cron
interval is whatever the admin last set (data, not code).

## 8. Register impacts on acceptance

PB-19 gains a named implementation owner (this packet) and its
provisional number is bound to a representative-latency-profile
measurement; master plan §2 gains Task PERF-1 before performance UAT
(steps re-sequenced this revision); the concurrency plan §13.2
references PERF-1 as the throughput/transaction-model task and receives
the withdrawn `max_in_flight`/overlap concern as topology-B scope; UAT
performance scenarios 27–28 assume a PERF-1-calibrated dispatcher. New
review call: **B11 — accept the Task PERF-1 packet** (master plan §1).

## 9. Locked final implementation prompt (Task PERF-1)

```text
DO NOT USE UNTIL CHATGPT REVIEWS AND ACCEPTS THIS PLANNING PACKAGE,
EXPLICITLY OPENS THE PERF-1 GATE, VERIFIES THE CURRENT BASE SHA, AND
ISSUES THIS PROMPT. (Prerequisite: merged core dispatcher
runtime-green; sequenced before performance UAT.)

Implement Task PERF-1 — core queue throughput calibration — exactly per
docs/07-implementation-plan/task-perf1-core-queue-throughput-calibration-packet.md
(D-PERF1-1..6 binding). Branch from the verified current
Shopify-connector tip (STOP on drift). One session; draft PR; stop.

ALLOWED FILES (exhaustive):
  addons/shopify_connector_core/models/shopify_connector_job_dispatch.py
    (run_drain() reworked to the _commit_progress per-job-savepoint
    loop; batch-cap parameter; backpressure read — nothing else; the
    try_lock_for_update() claim/re-check in shopify_connector_job.py is
    NOT edited)
  addons/shopify_connector_core/data/shopify_connector_config_params.xml
    (NEW, noupdate=1 — drain_batch_size=20)
  addons/shopify_connector_core/data/shopify_connector_cron_drain.xml
    (comment only — cadence lever documented; 5-min default unchanged)
  addons/shopify_connector_core/__manifest__.py (data entry + version bump)
  addons/shopify_connector_core/tests/test_dispatch_throughput.py (NEW)
  addons/shopify_connector_core/tests/__init__.py (one import line)
  docs/05-qa/task-perf1-validation-results.md (NEW)
  docs/05-qa/architecture-review-log.md (append one AR row)
  docs/01-research/research-handoff.md (top entry)
FORBIDDEN: the try_lock_for_update() claim/re-check in
shopify_connector_job.py (keep verbatim); the job state machine, error
registry, retry constants, readiness, store lifecycle, and every other
core file/line; all domain modules; ACL/CSV; views/UI;
webhooks/OAuth/CI; adams_base; main; plain dev.

IMPLEMENT exactly: D-PERF1-1 rework run_drain() to the official Odoo 19
cron-progress pattern — claim ONE job at a time (_claim_for_dispatch(1),
the merged try_lock_for_update() + under-lock re-check unchanged),
dispatch it inside a per-job savepoint (env.cr.savepoint()), then call
self.env['ir.cron']._commit_progress(1, remaining=<claimable_count>)
after each job, re-claim after each commit, and RETURN when
_commit_progress reports no remaining time (<=0), the queue is empty, or
the drain_batch_size per-pass cap is reached; verify the 19.0
_commit_progress signature against source before use — STOP and report
if it differs; drain_batch_size from ir.config_parameter (default 20,
clamp [1,500], warn+default on bad value) as the per-pass job cap;
out-of-cron invocation just commits per job with no early return.
D-PERF1-3 keep try_lock_for_update()/re-check (no double-claim); per-job
savepoint isolation (one job's error never poisons the pass); commit
releases the row lock before the next claim; committed jobs survive a
later failure/crash; DO NOT implement max_in_flight/overlap (withdrawn
to the multi-worker concurrency plan). D-PERF1-4 pre-claim backpressure
that defers a store's jobs under low Shopify throttle head-room (never
raises the rate). D-PERF1-2 leave the cron 5-min default and document
per-pass-cap × cadence as ceiling-only levers. D-PERF1-5 the benchmark
uses a representative handler-latency profile (dev-store read latency or
a recorded evidence-backed profile — never zero-cost stub arithmetic
asserted as throughput), recording sustained jobs/hour at the merged
default and >=600/h at the reference config, plus the per-job-commit /
lock-release / savepoint-isolation / crash-survival proofs and the
backpressure proof. All Section 5 tests; pre-existing dispatch/retry
suites stay green.

Runtime: full Odoo.sh run green before merge review (verbatim quote;
OP-43). Stop condition: open the PR as DRAFT titled "Task PERF-1: core
queue throughput calibration", update handoff + validation record + AR
row, record the measured jobs/hour and the latency profile used, and
stop. The PERF-1 gate closes the moment the draft PR opens. Do not start
any other task under any circumstance.
```
