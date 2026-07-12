# Sync-Engine Concurrency Validation — Results

> **Evidence-only runtime validation record.** Produced by the P-B
> parallel session executing
> [`sync-engine-concurrency-validation-plan.md`](./sync-engine-concurrency-validation-plan.md)
> against a disposable local Odoo 19 runtime. **This document changes no
> addon/code, opens no implementation gate, and claims no risk closed.**
> Every scenario is classified exactly one of PASS / FAIL / NOT EXECUTED /
> OBSERVATION ONLY. ChatGPT performs the final risk classification after
> reviewing the PR.

---

## 1. Status

**Executed. Baseline green. 9/9 scenarios classified.**

> **Revision (2026-07-12, control-room review comment `4950314052`).**
> Scenario 6 was **rerun faithfully using the real merged
> `store.action_disconnect()`** (the first submission used a direct
> `store.write({'state':'disconnected'})` substitute). Topology labels for
> the process-level scenarios (2/3/6) and the Scenario 8 concurrent count
> were corrected, and an `execution-method.md` reproduction record was
> added. See §10 Scenario 6, §14, and the change log at the end of §10.

- **7 PASS** (Scenarios 1, 2, 3, 4, 5, 7, 8)
- **1 FAIL vs the plan's expected result** (Scenario 6: an in-flight
  business job is **not skipped/cancelled** when an operator calls the real
  `action_disconnect()` concurrently — the disconnect **blocks on the job's
  row lock**, the no-op handler runs to completion, the job `succeeds`, and
  the disconnect then hits a serialization conflict and, via the RPC
  `retrying()` layer, completes without cancelling the now-terminal job).
  **This confirms SRR-03 remains open.** The originally-submitted
  "checkpoint-3 fails to observe a *committed* disconnect" framing does
  **not** hold for the real lifecycle method and has been corrected. No
  code was changed to fix anything (forbidden this session).
- **1 OBSERVATION ONLY** (Scenario 9: crash/interruption).

This is not a project decision. It is runtime evidence for ChatGPT review.

## 2. Authorization

- Gate comment: **PR #148 comment `4948925313`** — *"P-B concurrency
  validation execution gate — OPEN for one parallel evidence-only
  session."*
- The gate authorizes exactly: branch from the verified base, run the
  merged plan's nine scenarios against the strongest safely available
  disposable Odoo 19 runtime, record evidence only, open one draft PR,
  claim no risk closed.

## 3. Verified base SHA

- Required `Shopify-connector` tip: **`f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`**
- `origin/Shopify-connector` at session start: `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d` ✅ (no drift)
- Working branch `claude/sync-engine-concurrency-validation-92r4nc` HEAD:
  `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d` ✅ (branched exactly from the verified base)
- Merged implementation inspected read-only; it does **not** contradict
  the validation plan (the plan's cited mechanism —
  `_claim_for_dispatch()` / `try_lock_for_update()` / `run_drain()` /
  checkpoint-3 — is present exactly as described).

Evidence: [`evidence/sync-engine-concurrency/environment.txt`](./evidence/sync-engine-concurrency/environment.txt)

## 4. Environment

| Property | Value |
| --- | --- |
| Runtime | Disposable local install in this session's ephemeral container (NOT production, NOT staging, NO customer data) |
| Odoo source | `odoo/odoo` branch `19.0` @ `c5f1a963e6c65cf67b56b7ca2d4b77de66140e78` (shallow clone) |
| Python | 3.11.15 (venv) |
| PostgreSQL | 16.14 (Ubuntu), single local cluster, `127.0.0.1:5433`, initdb'd this session |
| Host | Linux 6.18.5, `nproc = 4` |
| Databases | `pbtest` (baseline suite), `pbscen` (scenarios), `pbscen6` (Scenario-6 faithful rerun) — all freshly created disposable DBs, dropped at cleanup |
| Shopify | **None.** No real credential, no token, no shop connection, no Admin API call anywhere. |

## 5. Odoo version

**Odoo Server 19.0** (`odoo.release.version_info = (19, 0, 0, 'final', 0, '')`),
confirmed via `odoo-bin --version` and the XML-RPC `common.version()`
handshake on both Scenario-8 servers (`server_version: "19.0"`).

## 6. Runtime topology

> **Terminology correction (review `4950314052`).** The process-level
> scenarios did **not** use a deployed Odoo `--workers` topology. They used
> **independent Odoo-library processes against one shared DB** — genuine
> process-level concurrency (separate OS processes, separate PostgreSQL
> connections), described below as a **process-level concurrency harness
> (B-like, not a deployed Topology B)**. Only Scenario 8 uses genuine
> deployed application-server instances (Topology C, single host).

- **Topology A** — single Odoo instance, in-process. Used for baseline
  scenarios (1, 4, 5, 7) and as one arm of the concurrent scenarios.
- **Process-level concurrency harness (B-like, NOT a deployed `--workers`
  Topology B)** — multiple genuinely separate OS **processes**, each an
  independent Odoo-library process with its own PostgreSQL connection,
  against one shared database. Each invokes **only merged methods**
  (`_claim_for_dispatch`, `_dispatch_one`, `run_drain`,
  `try_lock_for_update`, `action_disconnect`) — no repo code modified,
  monkeypatched, or mutated. Used for Scenarios 2, 3, 6. This is real
  process-level concurrency, but it is not the plan's literal Topology B
  (one deployed Odoo server with `--workers > 0` HTTP/cron worker
  processes), and is not labelled as such.
- **Topology C** — **two independent `odoo-bin` application-server
  daemons** (distinct PIDs, distinct HTTP ports 8169/8170, independently
  restartable — they *were* restarted independently mid-session) against
  **one shared** PostgreSQL database `pbscen`, drained concurrently via
  barrier-synchronized XML-RPC. Used for Scenario 8. **Single physical
  host / single code checkout** — see §17 Limitations.

Genuine concurrency was enforced with a file barrier (all workers signal
"ready", then are released together) so competing workers hit
`_claim_for_dispatch` within ~1–2 ms of each other. No scenario used
sequential shell calls, a single transaction, or `TransactionCase` thread
simulation as concurrency evidence. The exact commands, transaction
boundaries, and merged methods are recorded in
[`evidence/sync-engine-concurrency/execution-method.md`](./evidence/sync-engine-concurrency/execution-method.md).

## 7. Database isolation proof

- The PostgreSQL cluster was `initdb`'d into `/opt/pgdata` **this
  session**; it contained no data before this session and no external
  client connected to it.
- Both databases (`pbtest`, `pbscen`) were `createdb`'d this session,
  contained only synthetic `PB-*` records, and were **dropped at cleanup**
  (`SELECT count(*) … WHERE datname LIKE 'pb%'` → `0`).
- Trust auth is local-socket / `127.0.0.1` only; the cluster is not
  reachable off-host and is discarded with the ephemeral container.
- No persistent or shared business database was touched.

Evidence: [`environment.txt`](./evidence/sync-engine-concurrency/environment.txt),
[`cleanup.txt`](./evidence/sync-engine-concurrency/cleanup.txt)

## 8. Baseline automated-test result

Command (exact):

```
/opt/odoo-venv/bin/python /opt/odoo/odoo-bin -c /opt/odoo.conf -d pbtest \
  -i shopify_connector_core --test-enable --test-tags /shopify_connector_core \
  --without-demo=all --stop-after-init --workers=0 --max-cron-threads=0 \
  --log-level=test
```

Result (exact log lines):

```
odoo.tests.stats: shopify_connector_core: 209 tests 1.75s 4045 queries
odoo.tests.result: 0 failed, 0 error(s) of 187 tests when loading database 'pbtest'
```

- **0 failed, 0 error(s), 0 skipped**; process exit code `0`.
- Only `shopify_connector_core` tests executed (`--test-tags
  /shopify_connector_core`); 187 test methods ran.
- Installed modules were `base` + `shopify_connector_core` + the standard
  Odoo auto-install core modules (`web`, `bus`, `base_setup`, …).
  **No branch/domain code was installed** — `shopify_connector_product`,
  `shopify_connector_sale`, and `adams_base` all remained `uninstalled`.
- No install or registry failure.

The baseline is green; concurrency scenarios proceeded.

Evidence: [`baseline-summary.txt`](./evidence/sync-engine-concurrency/baseline-summary.txt)

## 9. Synthetic test-data setup

All data uses **only already-merged models, fields, and services**, and
the shipped **no-op** handler `core_dispatch_selftest`. No new handler,
model, or field was created.

- **Connected store(s)** — `shopify.connector.store` created via the ORM,
  then `state='connected'` written **directly in the disposable DB as
  explicit test setup**. This establishes the enqueue/execution gate only;
  it is **not** a readiness activation and is not represented as one.
  Synthetic names/domains: `PB-CONCURRENCY-TEST-STORE`
  (`pb-concurrency-test.myshopify.com`) plus per-scenario `PB-S5..S7`,
  `PB-S6A..C`, all `*.myshopify.com` synthetic.
- **Business jobs** — enqueued via
  `shopify.connector.job.enqueue.enqueue(store, 'manual_sync',
  'core_dispatch_selftest', …)` with synthetic
  `res_model='pb.synthetic.model'`, per-scenario `res_id` ranges, and
  synthetic `shopify_target_gid='gid://pb/…'`.
- **Core (non-business) jobs** — `job_source='setup_readiness_check'`.
- **Distinct vs colliding scope keys** — distinct `res_id` → distinct
  `operation_scope_key`; a per-scenario `res_id` allocation
  (1000/2000/…/9000) prevents cross-scenario scope-key collisions.
- **`retry_waiting` due / future** — `state='retry_waiting'` with
  `next_retry_at` in the past / future.
- **`blocked_manual_review`** — `state='blocked_manual_review'`,
  `manual_review_subreason='ambiguous_match'`.
- No real Shopify credential, token, order, product, email, or shop
  domain was used.

For the XML-RPC scenarios (Scenario 8 `run_drain`; Scenario 6 RPC-variant
`action_disconnect`), the disposable DB's `admin` user was given a
test-only password and added to the shipped
`group_shopify_connector_admin` group so XML-RPC could invoke the
Admin-only methods. These changes lived only in the disposable DBs
(`pbscen` / `pbscen6`) and were destroyed when they were dropped. No
password value is recorded in any committed file.

## 10. Scenario-by-scenario results

### Scenario 1 — Single drain baseline — **PASS** (topology A)

- **Setup:** 5 queued `core_dispatch_selftest` jobs (3 `manual_sync` +
  2 `setup_readiness_check`), store connected.
- **Action:** `run_drain(20)` once, via the real `run_drain()` entry point.
- **Observation:** all 5 jobs `queued → running → succeeded`; each has
  exactly **2** job-log rows (`attempt queued→running` "Dispatch attempt
  started.", `attempt running→succeeded` "Dispatch succeeded."); 10 log
  rows for 5 jobs, no duplicates; `started_at`/`finished_at` set. A
  re-drain immediately after claimed **`[]`** (no unexpected claimable job
  remained).
- **Expected:** each job processed once, correct transitions and logs.
- **Pass reasoning:** exact match, including the terminal-state release of
  `operation_scope_key` (shipped `_compute_operation_scope_key` clears the
  key once a job is terminal — expected, not a defect).
- **Evidence:** `scenario-01-jobs-before.csv`, `scenario-01-drain.json`,
  `scenario-01-jobs-after.csv`, `scenario-01-job-logs.csv`,
  `scenario-01-redrain-empty.json`.

### Scenario 2 — Concurrent cron workers, same DB — **PASS** (process-level concurrency harness, B-like)

- **Setup:** 30 queued business jobs (ids 7–36), store connected.
- **Action (a) — 3 simultaneous workers:** three separate OS processes
  (independent Odoo-library processes, one PostgreSQL connection each)
  (`wA`, `wB`, `wC`), barrier-released together, each running
  `run_drain`'s exact body (`_claim_for_dispatch(20)` then
  `_dispatch_one` per claimed job).
- **Observation (a):** `wC` (barrier release ~1.2 ms ahead) claimed the
  full first-20 window `[7..26]`; `wA` and `wB` claimed **`[]`** — they
  correctly `SKIP LOCKED`-skipped every row `wC` had locked. **No job
  double-claimed.** The 20 processed jobs each have exactly 2 log rows.
  The 10 jobs beyond the batch window (27–36) remained `queued` (not lost)
  and were drained to `succeeded` by a follow-up pass.
- **Action (b) — genuine disjoint partition:** worker A `claim_hold(10)`
  locked `[37..46]` and **held its transaction open**; concurrently
  (while A still held its locks) worker B `run_drain(20)` claimed exactly
  the complement `[47..56]` via `SKIP LOCKED`, committed, and finished
  **before** A committed.
- **Observation (b):** A∩B = ∅, A∪B = `{37..56}`; all 20 `succeeded`
  exactly once (2 log rows each, none with 4); no deadlock.
- **Expected:** each job processed at most once; disjoint claimed sets; no
  claimable job lost.
- **Pass reasoning:** the core SRR-04 safety property (no double-claim
  under genuine concurrency) holds in both the "one worker wins the batch"
  case and the "genuine disjoint non-empty partition" case. Observed
  nuance (reported honestly, not a defect): because every worker's
  `search(limit=N, order='id asc')` surfaces the **same** front-N window,
  simultaneous workers do not naturally split a single batch — one wins
  the whole window and the others get nothing that pass; disjoint
  non-empty partitioning requires one worker's lock set to be a strict
  prefix of the others' window (Action b). Leftovers are never lost.
- **Evidence:** `scenario-02-worker-wA/wB/wC.json`,
  `scenario-02-jobs-before.csv`, `scenario-02-jobs-after-pass1.csv`,
  `scenario-02-job-logs-pass1.csv`, `scenario-02-leftover-drain.json`,
  `scenario-02-partition-workerA/B.json`,
  `scenario-02-partition-jobs-after.csv`, `scenario-02-partition-logs.csv`.

### Scenario 3 — Skipped locked rows — **PASS** (process-level concurrency harness, B-like)

- **Setup:** 3 queued jobs (57, 58, 59); a separate independent
  Odoo-library process holds a real uncommitted row lock on job **58** via
  `try_lock_for_update()`.
- **Action:** while the lock is held, a second process runs `run_drain`.
- **Observation:** PostgreSQL confirmed the holder backend `idle in
  transaction`; a probe `SELECT id … WHERE id=58 FOR UPDATE SKIP LOCKED`
  returned **empty** (locked), while the same probe on an unlocked id
  returned the row. The claimer claimed **`[57, 59]`** (skipped 58) and
  returned in ~15 ms (**no hang, no exception**). Job 58 stayed `queued`.
  After the holder released (rollback), a later drain claimed **`[58]`**
  and it `succeeded`. Each job ends with exactly 2 log rows (58 was
  **not** double-claimed).
- **Expected:** locked row silently excluded, others processed, no
  error/hang, no duplicate claim, locked row processed on a later pass.
- **Pass reasoning:** exact match.
- **Evidence:** `scenario-03-holder.json`, `scenario-03-pg-locks.txt`,
  `scenario-03-claimer.json`, `scenario-03-final-drain.json`,
  `scenario-03-jobs-after.csv`, `scenario-03-job-logs.csv`.

### Scenario 4 — `retry_waiting` due jobs — **PASS** (topology A)

- **Setup:** one due `retry_waiting` job (60, `next_retry_at` in the
  past), one future (61, `next_retry_at` +6 h).
- **Action:** `run_drain(20)`.
- **Observation:** claimed **`[60]`** → `succeeded`; job 61 remained
  `retry_waiting`, untouched, `next_retry_at` **unchanged**
  (`2026-07-12 04:30:01.892923` before and after).
- **Expected:** only the due job claimed; future job untouched.
- **Pass reasoning:** exact match.
- **Evidence:** `scenario-04-jobs-before.csv`, `scenario-04-drain.json`,
  `scenario-04-jobs-after.csv`.

### Scenario 5 — Disconnect before claim — **PASS** (topology A)

- **Setup:** 2 business jobs (62, 63) enqueued while connected.
- **Action:** `action_disconnect()`; then attempt a **new** business
  enqueue; then `run_drain`.
- **Observation:** 62 & 63 → `cancelled`, `cancel_reason='Store
  disconnected.'`; the new business enqueue was **rejected**
  (`ValidationError`, `created:false`); `run_drain` claimed **`[]`**
  (cancelled jobs are terminal, not dispatched).
- **Expected:** new business enqueue rejected; pre-existing jobs cancelled
  and not reprocessed.
- **Pass reasoning:** exact match.
- **Evidence:** `scenario-05-jobs-before.csv`,
  `scenario-05-disconnect.json`, `scenario-05-try-enqueue.json`,
  `scenario-05-drain.json`, `scenario-05-jobs-after.csv`.

### Scenario 6 — Disconnect between start and handler — **FAIL vs plan expectation** (process-level concurrency harness, B-like)

> **Reran faithfully with the real merged `store.action_disconnect()`**
> (review `4950314052`, blocking issue 1). The competing transaction calls
> the actual lifecycle method — not a `store.write()` substitute, not an
> "equivalent" helper, not a monkeypatch. **The faithful result is
> materially different from — and corrects — the first submission's
> framing.** SRR-03 remains OPEN. No fix was applied (forbidden).

**Setup:** one synthetic connected store; one queued business
`core_dispatch_selftest` job; two genuinely independent transactions/
connections. **Worker A** runs the real single-transaction dispatch
(`_claim_for_dispatch(20)` → `_start_running` (checkpoint 2, `running`) →
hold → `_invoke_handler` (checkpoint 3 + handler) → commit), holding the
job row lock across the pause with **no intermediate commit**. **Worker
B** calls the real `store.action_disconnect()` while A is paused.

**What actually happens (both variants — see the timeline evidence):**

`action_disconnect()` does far more than set the store state: it clears the
credential, writes the store to `disconnected`, **searches every
non-terminal business job and writes them to `cancelled`**, appends
cancellation logs, and creates a lifecycle audit job. Under this race,
Worker B's snapshot sees the job as `queued` (A's `running` is
uncommitted), so B tries to cancel it — and **blocks on the job's row
lock** held by Worker A (PostgreSQL evidence: B's backend
`wait_event_type='Lock'`, `transactionid`, on a `FOR KEY SHARE` of
`shopify_connector_job`). Worker A therefore reaches checkpoint-3 and reads
the store as `connected` **because the disconnect has not committed — it is
blocked**, not because a committed disconnect is invisible. A's handler
runs, the job `succeeds`, A commits. Only then does B unblock — into a
**serialization conflict**:

- **Variant LIB** (Worker B = library call, **no** `retrying()` wrapper):
  `action_disconnect()` raises `psycopg2 SerializationFailure` ("could not
  serialize access due to concurrent update") and **rolls back**. Final
  committed: **store `connected`** (disconnect discarded), **job
  `succeeded`**, 2 log rows, **no cancellation, no audit job**. Raw
  behavior: the operator's disconnect *fails* and must be retried.
- **Variant RPC** (Worker B = `action_disconnect` via XML-RPC → Odoo's
  service-layer `retrying()`): the server logs
  `SERIALIZATION_FAILURE, 4 tries left, try again in 1.4222 sec...` and
  **retries the whole call**; on the retry the job is already `succeeded`
  (terminal), so the cancellation sweep finds nothing. Final committed:
  **store `disconnected`**, **job `succeeded` (handler ran, NOT
  cancelled)**, 2 log rows, lifecycle audit job = **"Store disconnected (0
  non-terminal business job(s) cancelled)."** `action_disconnect` returned
  HTTP 200.

**Timeline (RPC variant):** A running `07:15:23.617` → B disconnect
requested `07:15:24.090` → B blocked on job row → A checkpoint-3 observes
`connected` `07:15:24.551` → A handler done / job `succeeded` / A commit
`07:15:24.560` → B serialization failure + `retrying()` retry `07:15:24.560`
→ B `action_disconnect` completes (0 cancelled) `07:15:25.001`. **The live
handler runs before the disconnect completes; "disconnect requested" ≠
"disconnect committed".**

- **Expected (per plan):** job routed to `skipped`; handler never invoked.
- **Actual (real `action_disconnect`):** the in-flight job is **not
  skipped and not cancelled**; the handler runs; the job `succeeds`; the
  disconnect is serialized *behind* the running job (blocks → serialization
  → library raises / RPC retries and cancels nothing). → **FAIL vs the
  plan's expected result.**
- **Corrected mechanism:** the plan's "skip" is unreachable here. Under
  single-transaction REPEATABLE READ dispatch, checkpoint-3 reads the same
  snapshot as checkpoint-2, so it can never see a store-state change from a
  concurrent transaction; additionally, the real disconnect cannot even
  cancel the in-flight job (row-lock blocked) until the job commits. The
  first submission's "checkpoint-3 fails to observe a *committed*
  disconnect (probe read `connected` 1.1 s after commit)" describes only
  the **direct-`store.write()` observation** (§ retained below), **not** the
  real lifecycle path, and is no longer used to call any defect
  runtime-confirmed.
- **Consequence today:** none in practice (no-op handler; no live Shopify
  write). **Once a real domain handler performs a live write:** the
  in-flight job's live write completes even though an operator pressed
  disconnect during it, and the disconnect only lands afterward. That
  residual window is exactly SRR-03, which **remains OPEN**.
- **Severity:** Medium, latent. **No fix applied**; remediation requires a
  separate ChatGPT-controlled gate (§14, §18).
- **Evidence:** `scenario-06-real-timeline.md`,
  `scenario-06-real-lib-workerA.json` / `-workerB.json` / `-pglocks.txt` /
  `-final-state.txt`, `scenario-06-real-rpc-workerA.json` / `-workerB.json`
  / `-pglocks.txt` / `-server-retry.txt` / `-final-state.txt`.

**Retained narrow observation (NOT the lifecycle result).** The earlier
direct-`store.write({'state':'disconnected'})` experiment is kept only as a
labelled **OBSERVATION** about REPEATABLE READ snapshot visibility: a drain
transaction can continue to read its earlier snapshot (`connected`) after
another transaction **directly commits** the store state to `disconnected`.
That is a true statement about snapshot isolation, but it is **not** how the
real `action_disconnect()` behaves (which blocks rather than commits ahead
of checkpoint-3), and it must not be presented as the lifecycle-method
result. Evidence: `scenario-06-variantA.json`, `scenario-06-variantB.json`
(+ logs), `scenario-06-variantC.json` (+ logs),
`scenario-06-odoo-isolation-level.txt`, `scenario-06b-workerA-probe.json`.
Variant B (same-transaction self-write) and Variant C (pre-snapshot
disconnect → checkpoint-2 `failed_retryable`) remain valid source/behavior
controls.

### Scenario 7 — `blocked_manual_review` disconnect cancellation — **PASS** (topology A)

- **Setup:** job 71 in `blocked_manual_review`,
  `manual_review_subreason='ambiguous_match'`.
- **Action:** `action_disconnect()`.
- **Observation:** job → `cancelled`; `cancel_reason='Store
  disconnected.'`; `finished_at` set; `manual_review_subreason` **cleared
  (empty)**; **no constraint error**
  (`_check_manual_review_subreason_required` not violated); log
  `state_change blocked_manual_review→cancelled`.
- **Expected:** clean cancel, subreason cleared, no constraint violation,
  expected log.
- **Pass reasoning:** exact match (confirms the PR #131 one-file exception
  holds under a live runtime, as the plan noted).
- **Evidence:** `scenario-07-jobs-before.csv`,
  `scenario-07-disconnect.json`, `scenario-07-jobs-after.csv`,
  `scenario-07-job-logs.csv`.

### Scenario 8 — Multi-server drain — **PASS** (topology C, single host)

- **Setup:** 40 queued business jobs (ids 73–112); **two independent
  `odoo-bin` server daemons** (PIDs restarted mid-session to 3884/3885),
  HTTP ports 8169/8170, `--max-cron-threads=0`, both against the **one**
  shared `pbscen` database.
- **Action:** an initial **single-server probe** (`run_drain(5)` on port
  8169) processed the first **5** jobs (ids 73–77, succeeded at 22:45:42);
  then barrier-synchronized XML-RPC `run_drain(20)` fired at **both
  servers simultaneously** (`t_before` within ~1.4 ms) across 2 concurrent
  rounds, processing the remaining **35** jobs (ids 78–112, succeeded at
  22:46:27).
- **Observation (corrected counts — review `4950314052`, blocking issue
  3):** **40 total pool jobs succeeded**; of these, **5 (73–77) were the
  single-server probe** and **35 (78–112) were exercised by the successful
  concurrent two-server rounds**. Across all 40 (and specifically across
  the 35 concurrent jobs): **0** stuck in `running`; **every** job has
  exactly **2** job-log rows (no cross-server double-processing) and
  exactly **1** `queued→running` claim-attempt row (claimed once); **0**
  `deadlock detected` anywhere in the PostgreSQL log. The concurrent
  population that proves the cross-server no-double-processing property is
  the **35**, not all 40.
- **Expected:** no duplicate processing across servers; no deadlock; no
  stuck `running`; no duplicate `attempt` logs.
- **Pass reasoning:** exact match. **Note on the PostgreSQL log:** the
  `ERROR: argument of LIMIT must be type bigint …` lines at 22:44 are from
  the executor's **own earlier XML-RPC client bug** (a malformed
  `run_drain` argument, since fixed) — the server rejected the malformed
  call; they are **not** connector or concurrency errors. The `ir_sequence`
  lock line at 22:17 is from the **baseline test suite** window, not
  Scenario 8. No `deadlock detected` line exists at any time.
- **Evidence:** `scenario-08-topology.md`,
  `scenario-08-drain-rounds.txt`, `scenario-08-jobs-after.csv`,
  `scenario-08-job-logs.csv`, `scenario-08-pg-deadlock-scan.txt`.

### Scenario 9 — Crash/interruption — **OBSERVATION ONLY** (process-level concurrency harness, B-like)

Two transaction-boundary cases, both run by claiming + `_start_running`,
then `kill -9` of the worker process:

- **9a — killed AFTER the `running` transition committed:** job 113 stayed
  **`running` indefinitely**; the next `run_drain` claimed **`[]`** and did
  **not** reclaim it (`_claim_for_dispatch` only selects `queued`/due
  `retry_waiting` — never `running`). **No automatic recovery exists.**
- **9b — killed BEFORE commit (mid-transaction):** the uncommitted
  `running` write **rolled back**; job 114 stayed **`queued`**; the next
  `run_drain` reclaimed **`[114]`** → `succeeded`. Safe, no loss.

Honest characterization (no invented recovery): under the **current**
single-transaction `run_drain` (claim + all `_dispatch_one` calls + commit
at the request boundary, **no intermediate commit**), a crash mid-drain
rolls back the whole batch — the 9b outcome is the norm and no job is
stranded in `running`. The 9a "stuck `running`" state only arises if the
`running` state is committed **independently** of `succeeded` — which the
current code does not do, but which a **future per-job-commit design**
(e.g. the `ir.cron._commit_progress()` rework named "Task PERF-1" in the
plan §13.2) **would** introduce. This directly informs open question
**Q7** ("checkpoint/resume ownership … undesigned"): a stuck-`running`
recovery/timeout mechanism is **not implemented** and would be needed
before per-job commits are adopted.

- **Evidence:** `scenario-09a-worker.json`,
  `scenario-09a-next-drain.json`, `scenario-09a-jobs-after.csv`,
  `scenario-09b-worker.json`, `scenario-09b-next-drain.json`,
  `scenario-09b-jobs-after.csv`, `scenario-09-job-logs.csv`.

### Result matrix

| # | Scenario | Result | Concurrency method used |
| --- | --- | --- | --- |
| 1 | Single drain baseline | **PASS** | A (single in-process) |
| 2 | Concurrent cron workers | **PASS** | process-level harness, B-like (3 concurrent + staggered 2-worker) |
| 3 | Skipped locked rows | **PASS** | process-level harness, B-like (2 concurrent + PG lock probe) |
| 4 | `retry_waiting` due jobs | **PASS** | A (single in-process) |
| 5 | Disconnect before claim | **PASS** | A (single in-process) |
| 6 | Disconnect between start & handler | **FAIL vs plan expectation** (real `action_disconnect`) | process-level harness, B-like (2 txns; LIB + RPC/`retrying()`) |
| 7 | `blocked_manual_review` cancellation | **PASS** | A (single in-process) |
| 8 | Multi-server drain | **PASS** | C — two `odoo-bin` instances, single host (5 probe + 35 concurrent) |
| 9 | Crash/interruption | **OBSERVATION ONLY** | process-level harness, B-like |

### Revision change log (2026-07-12, review `4950314052`)

- **Scenario 6 rerun faithfully with the real `store.action_disconnect()`**
  (library + RPC variants). Finding corrected: the in-flight job is not
  skipped; the disconnect **blocks on the job row**, the handler completes,
  and the disconnect serialization-retries (RPC) or fails (library),
  cancelling nothing. The prior "checkpoint-3 misses a committed disconnect"
  framing is retained only as a narrow snapshot OBSERVATION. Result stays
  **FAIL vs plan expectation**; SRR-03 stays **OPEN**.
- **Topology labels corrected:** Scenarios 2/3/6/9 relabelled "process-level
  concurrency harness (B-like)", not deployed Topology B.
- **Scenario 8 counts corrected:** 40 total = 5 single-server probe (ids
  73–77) + 35 concurrent two-server (ids 78–112).
- **Added** `evidence/.../execution-method.md` (reproducible, sanitized
  method) and the Scenario-6 faithful-rerun evidence files.
- No unrelated scenario's accepted evidence was changed except terminology.

## 11. Evidence index

All under [`evidence/sync-engine-concurrency/`](./evidence/sync-engine-concurrency/):

- **Method (reproducibility):** `execution-method.md` — exact commands,
  transaction/commit boundaries, barrier/lock points, and the merged ORM
  methods invoked.
- **Environment / baseline / cleanup:** `environment.txt`,
  `baseline-summary.txt`, `cleanup.txt`, `all-jobs-final-snapshot.csv`,
  `cleanup-scenario6-rerun.txt`.
- **Scenario 1:** `scenario-01-*` (before/drain/after/logs/redrain).
- **Scenario 2:** `scenario-02-*` (3 workers, before/after/logs, leftover
  drain, partition workers A/B + after + logs).
- **Scenario 3:** `scenario-03-*` (holder, pg-locks probe, claimer, final
  drain, after, logs).
- **Scenario 4:** `scenario-04-*` (before/drain/after).
- **Scenario 5:** `scenario-05-*` (before, disconnect, try-enqueue, drain,
  after).
- **Scenario 6 (faithful real `action_disconnect` rerun):**
  `scenario-06-real-timeline.md`, `scenario-06-real-lib-workerA.json` /
  `-workerB.json` / `-pglocks.txt` / `-final-state.txt`,
  `scenario-06-real-rpc-workerA.json` / `-workerB.json` / `-pglocks.txt` /
  `-server-retry.txt` / `-final-state.txt`.
- **Scenario 6 (retained narrow snapshot OBSERVATION, not the lifecycle
  result):** `scenario-06-variantA/B/C*`,
  `scenario-06-odoo-isolation-level.txt`, `scenario-06b-workerA-probe.json`.
- **Scenario 7:** `scenario-07-*` (before, disconnect, after, logs).
- **Scenario 8:** `scenario-08-topology.md`, `scenario-08-drain-rounds.txt`,
  `scenario-08-jobs-after.csv`, `scenario-08-job-logs.csv`,
  `scenario-08-pg-deadlock-scan.txt`.
- **Scenario 9:** `scenario-09a-*`, `scenario-09b-*`, `scenario-09-job-logs.csv`.
- Small provenance helpers: `s*-ids.txt`, `s*-enqueue*.json`, `s4-*.json`,
  `s7-blocked.json`.

## 12. Cleanup

- All `odoo-bin` server daemons stopped (original Scenario-8 pair, and the
  Scenario-6-rerun RPC server); no `odoo-bin` process remains.
- All temporary worker processes ended; the deliberately held row locks
  (Scenario 3, and the Scenario-6 rerun) were released via rollback/commit;
  crash workers (Scenario 9) were killed; **0** idle-in-transaction
  backends remained.
- The shipped drain cron was **never modified**; servers ran with
  `--max-cron-threads=0` so it never auto-fired; all databases were then
  dropped, so **no scheduled job remains armed**.
- All three disposable databases dropped (`pb%` count → `0`), removing
  every synthetic store/job/log and the test-only admin password + group
  grant.
- No synthetic store, token, or credential remains in any persistent or
  shared database (none was ever used).

Evidence: [`cleanup.txt`](./evidence/sync-engine-concurrency/cleanup.txt),
[`cleanup-scenario6-rerun.txt`](./evidence/sync-engine-concurrency/cleanup-scenario6-rerun.txt)

## 13. Deviations from the plan

- **Runtime was a locally-built disposable Odoo 19**, not Odoo.sh (no
  Odoo.sh access this session). This satisfies the plan's "topology A
  minimum, C preferred" and the gate's "strongest safely available
  disposable Odoo 19 runtime."
- **Scenario 2** additionally ran a staggered "hold-and-claim" variant to
  demonstrate a genuine disjoint **non-empty** partition (the plain
  3-worker simultaneous run degenerates to one winner per batch window —
  reported honestly, §10 Scenario 2).
- **Scenario 6** was **rerun (2026-07-12) with the real merged
  `store.action_disconnect()`** in the competing transaction — via a
  library call (raw serialization behavior) and via XML-RPC (the
  production `retrying()` path). The first submission's direct-`store.write`
  experiment is retained only as a narrow snapshot-visibility OBSERVATION
  (§10 Scenario 6). Two additional controls (same-transaction self-write;
  pre-snapshot disconnect) remain.
- **Scenario 8** used two same-host `odoo-bin` server instances (single
  host); not a multi-VM/Odoo.sh topology (§17). Concurrent population was
  35 jobs (the other 5 were a single-server probe).
- The plan's performance-capture addendum (§13.2) was recorded only
  qualitatively (drain durations are in the per-worker JSON timestamps);
  no throughput target was measured (out of this session's scope; PB-19 /
  Task PERF-1 owns throughput).

## 14. Defects observed

**DEF-PB-1 (Scenario 6, CORRECTED) — a concurrent operator
`action_disconnect()` does not skip or cancel an in-flight business job;
the disconnect is serialized behind the running job and the handler runs to
completion.**

- **Faithful reproduction (real `store.action_disconnect()`):** Worker A
  runs the real single-transaction drain and holds the job row lock at
  `running`; Worker B calls the real `action_disconnect()`. B's snapshot
  sees the job as `queued`, so its cancellation sweep tries to write the
  job to `cancelled` and **blocks on A's row lock** (PostgreSQL
  `wait_event_type='Lock'`, `FOR KEY SHARE` on `shopify_connector_job`). A
  reaches checkpoint-3 (store reads `connected` — the disconnect is
  *blocked, not committed*), the no-op handler runs, the job `succeeds`, A
  commits. On unblock B hits `could not serialize access due to concurrent
  update`: the **library** call raises + rolls back (store stays
  `connected`); the **RPC** call is retried by `retrying()`
  (`SERIALIZATION_FAILURE, 4 tries left…`) and then completes, disconnecting
  the store and **cancelling 0 jobs** (the job is already terminal). Both
  variants: **handler ran, job `succeeded`, in-flight job not cancelled.**
- **Correction to the first submission:** the earlier claim — "checkpoint-3
  fails to observe a *committed* disconnect (probe read `connected` 1.1 s
  after commit)" — was produced with a **direct `store.write`** substitute,
  not the lifecycle method, and does **not** describe real behavior. It is
  retained only as a narrow snapshot-visibility OBSERVATION (§10 Scenario
  6). The lifecycle method **blocks** rather than committing ahead of
  checkpoint-3.
- **Affected scenario:** 6. **Related risk:** SRR-03.
- **Severity:** Medium, **latent** — no live-write handler exists yet, so
  no external effect today (no-op handler). Becomes real once a domain
  handler performs a live Shopify write: that write completes even though
  an operator pressed disconnect during it, and the disconnect only lands
  afterward.
- **Not a contradiction of merged code claims:** `_invoke_handler`'s
  docstring says checkpoint-3 *"narrows, but … never claims to close"* the
  race; SRR-03 is already open. Source-level inference (separate from the
  runtime result): under single-transaction REPEATABLE READ dispatch,
  checkpoint-3 reads the same snapshot as checkpoint-2 and so cannot fire
  for any concurrent disconnect; combined with the row-lock blocking above,
  the plan's "skip" outcome is unreachable for a real concurrent
  `action_disconnect()`.
- **Action:** evidence preserved; **no code changed**; no fix commit; not
  broadened. Remediation (if any) requires a separate ChatGPT-controlled
  implementation gate.

No other defect was observed. Scenario 9a's stuck-`running` behavior is
**not** a current-code defect (current `run_drain` never commits `running`
independently) but a **design gap for a future per-job-commit model** — an
input to Q7, not a bug in merged code.

## 15. Security / redaction check

- No real Shopify credential, token (`shpat_…`), shop domain, order,
  product, customer name, or email exists in any evidence file — only
  synthetic `PB-*` / `pb-*.myshopify.com` values and synthetic
  `gid://pb/…` targets.
- No database password, host secret, session cookie, or private URL is
  present. The only connection detail is the local disposable
  `127.0.0.1:5433` trust-auth socket; the string "password" appears only
  as descriptive prose in `cleanup.txt` (no value).
- Technical values required to verify concurrency (synthetic job ids,
  states, timestamps, worker PIDs, ports) are intentionally retained.
- Job-log `message`/`technical_detail` fields observed carry no secret;
  the merged `redact()` path was exercised by the green baseline
  (`test_secrets_redacted_in_dispatch_failure_path` passed).

## 16. Risk assessment proposal

> Proposals only. **ChatGPT performs the final classification.** No risk
> is claimed closed.

- **SRR-04 (cron job-acquisition concurrency under real load): propose
  REDUCED.** Scenarios 2 and 3 (independent Odoo-library processes, one
  shared DB — a process-level concurrency harness, **not** a deployed
  `--workers` Topology B) and Scenario 8 (two `odoo-bin` instances, single
  host) provide genuine concurrent-process evidence that
  `_claim_for_dispatch` / `try_lock_for_update` (SKIP LOCKED) produces
  disjoint claimed sets, no double-processing, no duplicate attempt logs,
  and no deadlock. Not proposed closed: no deployed multi-`--workers`
  server, only two same-host instances, a 4-CPU host, and no sustained
  load were exercised.
- **SRR-03 (disconnect / in-flight-job race): remains OPEN.** The faithful
  real-`action_disconnect()` rerun (Scenario 6) shows the in-flight
  business job is **not** stopped by a concurrent operator disconnect: the
  disconnect blocks on the job's row lock, the handler runs to completion,
  and the disconnect then serialization-retries (RPC) or fails (library),
  cancelling nothing. checkpoint-3 provides no protection here. Propose
  SRR-03 stay **open** with this session's corrected evidence attached;
  ChatGPT to decide whether it warrants a remediation gate before the first
  live-write domain handler. (Note: the disconnect being *serialized behind*
  a running no-op job is arguably acceptable today; the risk is the future
  live-write handler.)
- **SRR-09 (multi-server / load-balanced coordination): propose REDUCED
  (single-host two-instance evidence only), NOT closed.** Scenario 8 is
  genuine two-`odoo-bin`-instance topology C against one shared DB, but on
  a single host / single checkout — not a multi-VM/Odoo.sh deployment.
  ChatGPT to decide whether true multi-node proof is still required.

A fully green run would still authorize no implementation. This run is not
fully green (Scenario 6 FAIL).

## 17. Limitations

- **Process-level harness, not a deployed `--workers` topology.** The
  concurrency for Scenarios 2/3/6/9 came from independent Odoo-library
  processes (separate OS processes, separate PostgreSQL connections)
  against one shared DB — genuine process-level concurrency, but **not**
  the plan's literal Topology B (one deployed Odoo server with
  `--workers > 0`). The DB-level claim/lock/serialization semantics are the
  same, but a deployed multi-worker HTTP/cron server was not run for these
  scenarios. Only Scenario 8 used deployed application-server instances.
- **Single physical host.** Scenario 8's "two servers" are two processes
  on one machine sharing one local cluster — not independent VMs/nodes,
  not a load balancer, not Odoo.sh. It exercises the DB-coordination
  semantics of SRR-09 but not network partitions, cross-node clock skew,
  or independent-node failure.
- **Small scale.** 4 CPUs; batches of ≤40 jobs (35 concurrent in Scenario
  8); up to 3 concurrent library processes / 2 server instances. No
  sustained-load or savepoint-ceiling (SRR-01) stress; no throughput/PB-19
  measurement.
- **No live Shopify surface.** Every handler is the shipped no-op; the
  disconnect-race consequence (Scenario 6) is therefore latent, not
  demonstrated end-to-end against a real write.
- **Concurrency timing** is barrier-coordinated to force overlap; it does
  not enumerate every possible interleaving, only the ones each scenario
  targets.
- **Locally-built Odoo 19** from the public `19.0` branch, not the exact
  Odoo.sh build; behavior is expected to match but was not cross-checked
  against Odoo.sh.

## 18. ChatGPT decisions required

1. **SRR-03 / DEF-PB-1 (corrected):** accept the faithful
   `action_disconnect()` Scenario 6 finding — an in-flight job is not
   stopped by a concurrent operator disconnect (the disconnect blocks on
   the job row, the handler completes, the disconnect then
   serialization-retries/fails and cancels nothing). Decide whether a
   remediation gate is required (and its scope) **before** any live-write
   domain handler is built. Design directions to weigh (not authorized
   here): make the drain re-check the store in a fresh short transaction
   outside its snapshot, put the disconnect guard at the handler-commit
   boundary, or have `action_disconnect` explicitly signal/await in-flight
   jobs rather than silently losing the cancellation on serialization.
   **Do not treat this session as authorizing any such change.**
2. **SRR-04:** accept/adjust the proposed **REDUCED**, or require higher-
   scale/load evidence first.
3. **SRR-09:** accept the single-host two-instance evidence as **REDUCED**,
   or require genuine multi-node/Odoo.sh proof before any reduction.
4. **Scenario 9 / Q7:** decide whether a stuck-`running` recovery/timeout
   task must precede any per-job-commit (`_commit_progress` / PERF-1)
   rework.
5. Confirm no implementation gate is opened by this evidence.

---

## Non-authorizations

This document does not authorize any domain-sync task, setup wizard,
OAuth/token code, packaging, or any code change (including a fix for
DEF-PB-1). It opens no implementation gate. Every risk remains exactly as
open as ChatGPT classifies it after reviewing this PR.
