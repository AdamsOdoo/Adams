# Task PERF-1 — Core Queue Throughput Calibration: Implementation-Ready Planning Packet

> **Status: Proposed for ChatGPT review. NOT accepted. The locked
> prompt in §9 is NOT usable.** Produced 2026-07-11 by the PR #148
> revision session, implementing **re-review comment `4945129824`
> item 5**: PB-19 requires ≥ 600 jobs/hour while the accepted merged
> defaults (5-min drain cron × batch 20) cap throughput at ~240/hour —
> a *mathematically known* planning gap with, until now, **no gated
> task, allowed files, or tests to close it**. This packet creates that
> task rather than silently lowering PB-19 to fit the defaults (the
> stated onboarding objective — a 5k-customer import inside one working
> day — requires it). Evidence: merged core dispatcher re-read
> 2026-07-11 (`shopify_connector_job_dispatch.py` `run_drain()`;
> `data/shopify_connector_cron_drain.xml` `interval_number=5`,
> `interval_type=minutes`; the `FOR UPDATE SKIP LOCKED` claim primitive
> in `shopify_connector_job.py`), performance budgets
> (`../03-architecture/performance-budgets.md` PB-19/PB-18) and the
> concurrency plan (`../05-qa/sync-engine-concurrency-validation-plan.md`
> §13.2). API version posture 2026-07.

## 1. Why this task exists (the known gap)

**[Fact — merged repository state]** The drain cron
(`ir_cron_shopify_connector_job_dispatch_drain`) fires every **5
minutes** and calls `run_drain()`, whose default batch is **20**
claimed-and-processed jobs per pass. Sustained ceiling =
`20 jobs / 5 min = 240 jobs/hour` on topology A (single worker).
**[Fact — budgets]** PB-19 sets ≥ **600 jobs/hour** so a 5k-job
onboarding import (customers + products) finishes inside one working
day (~8.3 h at 600/h). 240/h ⇒ ~20.8 h — two working days for the same
onboarding, which fails the operator-experience bar. This is arithmetic,
not an external unknown; it must be owned by a gated task with exact
allowed files, tests, and acceptance budgets.

## 2. Objective, scope, non-goals

Make dispatch **cadence and batch configurable**, prove a configuration
that sustains ≥ 600 jobs/hour on topology A **without** lock contention,
double-claim, unbounded pass overlap, or Shopify throttle breach, and
record the concurrency/backpressure evidence. **Non-goals:** no change
to the `FOR UPDATE SKIP LOCKED` claim semantics (kept — it is the
correctness primitive); no new worker topology (topology B / multi-worker
is a Phase-2 concurrency item, RA-020-adjacent — named, out of scope);
no error-registry, retry-constant, or state-machine change; no per-job
business logic; no UI (settings UI is UI-phase — config is read from
`ir.config_parameter` here); no webhook/OAuth surface; no domain-module
edits.

## 3. Decision closures (D-PERF1-1 … D-PERF1-6) — each Proposed

**D-PERF1-1 — Configurable batch (system parameter, safe default).**
`run_drain()` reads its batch from `ir.config_parameter`
`shopify_connector.drain_batch_size` (Integer, **default 20** — the
merged value, so behavior is unchanged until an admin tunes it), seeded
by a NEW `noupdate=1` data record. Bounds: clamped to `[1, 500]`
(a malformed/oversized value falls back to the default with one logged
warning — never an unbounded claim). The cron passes no literal;
`run_drain()` resolves the parameter each pass.

**D-PERF1-2 — Configurable cadence (documented lever).** The drain
cadence is the `ir.cron` `interval_number`/`interval_type` on the drain
record — an admin-adjustable field. This packet documents the two
supported calibration levers (batch × cadence) and their product of
`batch / interval_minutes × 60 = jobs/hour` ceiling; it does **not**
hardcode a new interval (leaving the merged 5-min default), so the
recommended reference configuration to reach PB-19 is stated as
**batch 50 @ 5 min** *or* **batch 10 @ 1 min** (both = 600/h), selected
at the calibration run and recorded. Changing the cron interval is an
`ir.cron` data edit, not a code path — the packet's code change is the
batch parameter + backpressure only.

**D-PERF1-3 — Lock-safety & no double-claim (invariant preserved).**
The claim loop keeps `FOR UPDATE SKIP LOCKED` (merged primitive), so
two concurrent drain passes (possible when a pass runs longer than the
cadence) **never** claim the same job — the second simply skips locked
rows. A NEW `max_in_flight` guard (system parameter
`shopify_connector.drain_max_in_flight`, default 0 = unbounded/off)
caps the number of jobs a single pass will claim while a prior pass is
still running, preventing runaway overlap on slow Shopify responses;
when 0, behavior is exactly the merged single-pass claim. No lock is
held across a Shopify network call (claim → release-to-`running` →
process), preserving the merged non-blocking posture.

**D-PERF1-4 — Shopify throttling / backpressure interaction.** Raising
the batch must not breach Shopify's cost budget. The merged API client
already paces on `throttleStatus` (SRR-adjacent); PERF-1 adds a
**backpressure rule**: before claiming a batch, the drain reads the
store's most recent recorded throttle head-room and reduces the
effective batch toward 1 when head-room is low (a documented linear
back-off), so throughput self-limits under throttle pressure instead of
forcing 429s. Backpressure never *raises* the batch above the configured
value; it only lowers the effective claim. Stores with no recent
throttle signal use the full configured batch.

**D-PERF1-5 — Benchmark procedure (the acceptance evidence).** On a
seeded queue of ≥ 1,000 `queued` stub jobs (no live Shopify call —
handler stubbed to a fixed cost, mirroring `test_job_dispatch`'s
no-live-call harness), run repeated drains over a ≥ 5-minute wall-clock
window and record sustained jobs/hour at: (a) the merged default
(20 @ 5 min → ~240/h, the regression baseline); (b) the reference PB-19
configuration (≥ 600/h); (c) a two-concurrent-passes run proving zero
double-claim; (d) a throttle-limited fake-client run proving the D-PERF1-4
back-off engages and no 429 is forced. Evidence (numbers + config) in
the validation record and fed back to PB-19 (its "provisional" →
"measured YYYY-MM-DD" recalibration rule).

**D-PERF1-6 — Sequencing.** PERF-1 is a **core** task sequenced **after
the domain tasks are mergeable and before performance UAT** (master
plan §2), so the calibration runs against realistic job shapes and the
UAT performance scenarios (27–28) assert an already-tuned dispatcher.
It may run in parallel with the P-B concurrency-plan execution (they
share the same runtime evidence surface). Prerequisite: merged core
dispatcher runtime-green (fact) — no domain dependency in the code, only
in the realism of the benchmark corpus.

## 4. Allowed / forbidden files (exhaustive)

**Allowed:**
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (batch parameter resolution in `run_drain()`; the `max_in_flight`
  guard; the D-PERF1-4 backpressure read — nothing else)
- `addons/shopify_connector_core/data/shopify_connector_config_params.xml`
  (NEW, `noupdate=1` — seeds `drain_batch_size=20` and
  `drain_max_in_flight=0`)
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

**Forbidden:** the `FOR UPDATE SKIP LOCKED` claim semantics (kept
verbatim); the job state machine, error registry, retry constants,
readiness, store lifecycle, and every other core file/line; all domain
modules; ACL/CSV; views/UI; webhooks/OAuth/CI; `adams_base`; `main`;
plain `dev`.

## 5. Tests (`test_dispatch_throughput.py`)

1. `run_drain()` reads `drain_batch_size` from `ir.config_parameter`;
   unset → default 20 (merged behavior preserved); a raised value
   claims-and-processes more per pass; out-of-range value clamps to
   `[1,500]` with a logged warning.
2. **No double-claim under concurrency:** two overlapping drain passes
   over one queue claim disjoint job sets (SKIP LOCKED invariant); the
   `max_in_flight` guard caps overlap when set.
3. **Backpressure (D-PERF1-4):** a fake client reporting low throttle
   head-room reduces the effective batch toward 1; full head-room uses
   the configured batch; back-off never raises the batch.
4. **Throughput regression/target:** the seeded-queue harness records
   ~240/h at 20 @ 5 min and ≥ 600/h at the reference configuration
   (numbers asserted against the wall-clock-normalized model, no live
   Shopify call — the merged no-live-call guard reused).
5. All pre-existing dispatch/retry suites stay green
   (`test_job_dispatch.py`, `test_job_retry_scheduling.py`) — the batch
   parameter and backpressure must not change claim ordering or retry
   scheduling.
Source guards: no Shopify call added to the drain; the claim SQL is
unchanged (string/AST scan asserts `SKIP LOCKED` intact).

## 6. Gate criteria (15-pattern, abbreviated)

1 merged core runtime-green ✅(fact); 2–3 exact names ✅(§3); 4 files
✅(§4); 5 batch/max-in-flight/clamp thresholds fixed ✅(D-PERF1-1/3);
6–8 no domain/UI/webhook scope ✅; 9 tests ✅(§5); 10 rollback ✅(§7);
11 no live-Shopify dependency in code (benchmark uses stubbed handler)
✅; 12 gate-act reconfirmation; 13 the flagged calls explicit:
cadence-as-`ir.cron`-lever (D-PERF1-2), backpressure back-off design
(D-PERF1-4), `max_in_flight` default-off (D-PERF1-3); 14 the PB-19
acceptance number bound to measured evidence ✅(D-PERF1-5); 15
lock-safety invariant preserved ✅(D-PERF1-3).

## 7. Odoo.sh + validation / acceptance budgets / rollback

Odoo.sh: full suites green (verbatim quote, OP-43). **Acceptance
budgets:** the D-PERF1-5 benchmark demonstrates ≥ 600 jobs/hour
sustained (PB-19) at the recorded reference configuration on topology A,
zero double-claim under two concurrent passes, and backpressure
engaging under simulated throttle — all in the validation record, fed
back to PB-19's recalibration line. **Rollback:** revert the single PR
— `run_drain()` returns to the hardcoded batch 20 (240/h ceiling,
documented); the seeded `ir.config_parameter` rows and the cron comment
may **remain inert/orphaned** (a normal code revert does **not** drop
them — no destructive schema cleanup is assumed; any cleanup is a
separately tested migration); no business, job, or audit data is
removed; the cron interval is whatever the admin last set (data, not
code).

## 8. Register impacts on acceptance

PB-19 gains a named implementation owner (this packet) and its
provisional number is bound to measured evidence; master plan §2 gains
Task PERF-1 before performance UAT (steps re-sequenced this revision);
the concurrency plan §13.2 references PERF-1 as the throughput-tuning
task; UAT performance scenarios 27–28 assume a PERF-1-calibrated
dispatcher. New review call: **B11 — accept the Task PERF-1 packet**
(master plan §1).

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
    (batch parameter in run_drain(); max_in_flight guard; backpressure
    read — nothing else; SKIP LOCKED claim SQL unchanged)
  addons/shopify_connector_core/data/shopify_connector_config_params.xml
    (NEW, noupdate=1 — drain_batch_size=20, drain_max_in_flight=0)
  addons/shopify_connector_core/data/shopify_connector_cron_drain.xml
    (comment only — cadence lever documented; 5-min default unchanged)
  addons/shopify_connector_core/__manifest__.py (data entry + version bump)
  addons/shopify_connector_core/tests/test_dispatch_throughput.py (NEW)
  addons/shopify_connector_core/tests/__init__.py (one import line)
  docs/05-qa/task-perf1-validation-results.md (NEW)
  docs/05-qa/architecture-review-log.md (append one AR row)
  docs/01-research/research-handoff.md (top entry)
FORBIDDEN: the FOR UPDATE SKIP LOCKED claim semantics (keep verbatim);
the job state machine, error registry, retry constants, readiness,
store lifecycle, and every other core file/line; all domain modules;
ACL/CSV; views/UI; webhooks/OAuth/CI; adams_base; main; plain dev.

IMPLEMENT exactly: D-PERF1-1 run_drain() resolves drain_batch_size from
ir.config_parameter (default 20, clamp [1,500], warn+default on bad
value); D-PERF1-3 keep SKIP LOCKED (no double-claim) + a
drain_max_in_flight cap (default 0 = off); D-PERF1-4 pre-claim
backpressure that lowers the effective batch toward 1 under low Shopify
throttle head-room (never raises it); D-PERF1-2 leave the cron 5-min
default and document batch×cadence as the two levers; D-PERF1-5 the
seeded-queue benchmark harness (no live Shopify call — stubbed handler)
recording ~240/h at 20@5min and >=600/h at the reference config, zero
double-claim under two concurrent passes, and backpressure engaging.
All Section 5 tests; pre-existing dispatch/retry suites stay green.

Runtime: full Odoo.sh run green before merge review (verbatim quote;
OP-43). Stop condition: open the PR as DRAFT titled "Task PERF-1: core
queue throughput calibration", update handoff + validation record + AR
row, record the measured jobs/hour, and stop. The PERF-1 gate closes
the moment the draft PR opens. Do not start any other task under any
circumstance.
```
