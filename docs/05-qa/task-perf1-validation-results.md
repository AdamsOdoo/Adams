# Task PERF-1 — Core Queue Throughput Calibration: validation results

> **Status: implementation evidence record. Docs-only claims below are
> labelled. NOT an acceptance, NOT Odoo.sh runtime, NOT a PB-19
> measurement.** Produced 2026-07-26 on `fable/wave-5-completion` under the
> control-room continuation ruling of 2026-07-26, which opens G5-4 and
> accepts the PERF-1 objectives and the PB-19 provisional target of ≥ 600
> jobs/hour **subject to the source-rebase corrections that ruling requires**.

---

## 1. The source rebase — what the packet said, and what the code actually is

`[Fact — read at the bound base 87f1763a, before any edit]`

The packet
([`task-perf1-core-queue-throughput-calibration-packet.md`](../07-implementation-plan/task-perf1-core-queue-throughput-calibration-packet.md))
was written on 2026-07-11 against a dispatcher that claimed N jobs and looped
over them **inside one uncommitted transaction**, holding every claimed row's
lock for the whole pass. Its central deliverable (D-PERF1-1) was to replace
that with a per-job claim/dispatch/commit loop.

**That rework is already merged.** At the bound base:

| Packet assumption (2026-07-11) | Actual code at `87f1763a` |
| --- | --- |
| `run_drain()` claims 20 rows in one `_claim_for_dispatch(20)` | `run_drain()` loops `_drain_one()`, which calls `_claim_for_dispatch(1)` |
| All claimed locks held for the whole pass | Only the in-flight job's row is locked |
| No commit between jobs | `_drain_one` commits each job on its own transaction |
| One handler error rolls back the entire pass | Per-job boundary; a genuine 40001/40P01/55P03 is caught and recovered |
| No recovery model described | `_recover_after_concurrency_conflict` re-locks, re-validates under the lock, and routes once through the DEC-031 Layer 1 replay policy without replaying the handler; Layer 2 adds C1/C2/NET/C3 with `_recover_pre_c2_failure` / `_recover_layer2_owner` |

**Inference (high confidence):** implementing D-PERF1-1 as written would have
**replaced a hardened, independently reviewed recovery path with a weaker
description of it** — the exact outcome the continuation ruling forbids
("do not replace the hardened per-job recovery model with the packet's stale
claim-N description"). It was therefore not implemented as written. The
packet has been corrected to describe current truth; see its §0 rebase note.

### 1.1 What was genuinely missing, and is delivered here

`[Fact]`

1. **No cron progress and no time budget.** `run_drain(limit)` ran a fixed
   `range(limit)` with no knowledge of how much of its cron slot remained,
   and reported nothing to `ir.cron.progress`. A long queue could overrun its
   slot; an operator saw a silent cron.
2. **The per-pass cap was a hardcoded constant** (`DISPATCH_BATCH_SIZE = 20`),
   so the *one lever that actually closes the PB-19 gap* was not adjustable
   without a code change.
3. **No backpressure.** Nothing deferred a store already being throttled by
   Shopify.

## 2. Build-time API verification (packet §7 — mandatory, STOP on drift)

`[Fact — verified against the pinned Odoo source, not from memory]`

```
odoo/addons/base/models/ir_cron.py @ 30bde9ff758834a4912c5ae55843d3a7dad849f1
_commit_progress(self, processed: int = 0, *, remaining: int | None = None,
                 deactivate: bool = False) -> float
```

Matches the packet's stated signature exactly — **no drift, no STOP
condition triggered**. Two behaviours from the body matter and are relied on:

- it **commits on every path**, including the outside-a-cron path
  (`if not progress: self.env.cr.commit(); return float('inf')`);
- inside a cron it returns `max(cron_end_time - time.monotonic(), 0)` — the
  seconds of slot left, reaching exactly `0` when the budget is spent.

This verification is not left as a session note: `test_commit_progress_
signature_matches_the_pinned_odoo_19_contract` asserts the signature, the
keyword-only markers and the return annotation on **every suite run**, so a
future Odoo bump that changes the contract fails the build instead of
silently changing drain behaviour.

## 3. What changed in code

`[Fact]`

| File | Change |
| --- | --- |
| `models/shopify_connector_job_dispatch.py` | `run_drain()` gains the cron-progress + time-budget loop, the configurable per-pass cap, and pre-claim backpressure; returns the processed count. `_drain_one()` gains an `exclude_store_ids` pass-through |
| `models/shopify_connector_job.py` | `_claimable_domain()` / `_claimable_count()` extracted; `_claim_for_dispatch` gains optional `exclude_store_ids`, **narrowing only the candidate search** |
| `data/shopify_connector_config_params.xml` (NEW) | seeds `shopify_connector.drain_batch_size = 20`, `noupdate="1"` |
| `data/shopify_connector_cron_drain.xml` | comment only — documents cadence as an admin data lever; the 5-minute default is unchanged |
| `__manifest__.py` | data entry + version `19.0.1.14.0` |
| `tests/test_dispatch_throughput.py` (NEW) | 15 tests + the tagged benchmark |

### 3.1 The one deviation, declared

`[Fact]` The packet forbids editing `shopify_connector_job.py`, keeping
`try_lock_for_update()` and the under-lock re-check "verbatim". Backpressure
(D-PERF1-4) defers a store **before claiming**, and the merged claim takes
only a `limit` — so with no way to narrow it, a deferred store's job would be
re-selected by `id asc` on every iteration and the pass would livelock.

`_claim_for_dispatch` therefore gained an **optional** `exclude_store_ids`
argument that is ANDed into the **candidate `search` only**. The lock call,
the empty-result early return, the `invalidate_recordset()` and the
under-lock `filtered()` re-check are untouched, and
`test_claim_lock_and_recheck_unchanged` asserts that against the AST —
including that the lock still precedes the re-check. **This is offered for
the control room to ratify or reject**; it is the minimum edit that makes
D-PERF1-4 implementable at the current base.

## 4. Invariants explicitly preserved

`[Fact — none of these files or behaviours were modified]`

Per-job claim under `try_lock_for_update()`; per-job commit; per-job
savepoint isolation; ownership/`owner_worker_ref`/`current_attempt_token`
handling; the DEC-031 Layer 1 replay-policy routing; Layer 2
C1/C2/NET/C3 mutation safety and its three recovery entry points; the job
state machine, error registry and retry constants; claim ordering. The
existing `test_job_dispatch.py`, `test_job_retry_scheduling.py`,
`test_mutation_concurrency.py` and the genuine independent-connection
lifecycle tests remain the proof of those, and all stay green (§6).

**`max_in_flight` was not implemented** — the packet itself withdrew it to
the topology-B multi-worker plan (D-PERF1-3).

## 5. Backpressure — the signal, and why it is safe

`[Fact]` The signal is `shopify.connector.store.api_health_state`, a durable
readonly field with the fixed vocabulary `normal` / `throttled` / `degraded`,
already maintained by the merged store lifecycle. Reading it costs **no
Shopify call and no credential read**, which is what makes it testable and
what keeps this batch inside the no-Shopify constraint.

Three properties, each asserted:

- **It can only narrow.** `_claimable_count()` with an exclusion is strictly
  less than without (`test_backpressure_can_only_narrow_the_claimable_set`).
  There is no code path by which backpressure raises the drain rate.
- **A deferred store's jobs are untouched** — not claimed, started, retried,
  failed or re-scheduled; they stay `queued` with `started_at` and
  `retry_count` unchanged (`test_throttled_store_jobs_are_deferred_and_left_
  untouched`). Deferral is a narrowed search, never a state write, and a
  source guard asserts the helper calls no `write`/`create`/`unlink`.
- **It recovers by itself** when health returns to `normal`
  (`test_backpressure_recovers_when_health_returns_to_normal`).

**Not `sudo()`** `[Inference]`: deferral only needs to cover stores whose
jobs this pass could claim, and the claim runs as the same user. Elevating
would read across the SEC-3 store scope for no gain — and the cron user is
root, which already sees every store.

## 6. Test results

`[Fact — local Odoo 19 @ pinned `30bde9ff`, PostgreSQL 16.14. DEC-041 D8
supporting evidence, NOT Odoo.sh acceptance.]`

| Suite | Result |
| --- | --- |
| `TestDispatchThroughput` + `TestJobDispatch` + `TestJobRetryScheduling` | **0 failed, 0 errors of 61** |
| `TestDispatchThroughputBenchmark` (tag `shopify_connector_drain_throughput`) | **0 failed, 0 errors of 1** |
| Full connector suite (fresh / warm / non-standard) | see [`wave-5-completion-validation-results.md`](wave-5-completion-validation-results.md) |

## 7. Throughput measurement — and exactly what it does not prove

### 7.1 The honest scope limit, stated first

`[Fact]` The packet asks for a "representative handler-duration profile",
ideally dev-store read latency. **No Shopify store is provisioned and no
Shopify credential exists in this environment**, and the governing
instruction forbids fabricating dev-store latency. There is therefore
nothing real to calibrate against.

The benchmark runs a **declared synthetic latency profile** and says so in
its own output. **No claim is made here that any store achieves PB-19's
≥ 600 jobs/hour.** PB-19 stays **provisional**, exactly as the packet's
"provisional → measured YYYY-MM-DD" rule requires, and the measurement that
would discharge it belongs to the provisioned-store campaign in
[`shopify-live-validation-package.md`](shopify-live-validation-package.md).

### 7.2 What was measured

`[Fact — 40 jobs per point, one fresh store per point, per-pass cap 40]`

| Synthetic per-job latency | Jobs | Elapsed | Implied jobs/hour |
| --- | --- | --- | --- |
| 0.000 s (dispatcher overhead only) | 40 | 0.2295 s | 627,355 |
| 0.005 s | 40 | 0.4503 s | 319,791 |
| 0.020 s | 40 | 1.1010 s | 130,788 |

**Dispatcher overhead is ~5.7 ms per job** (0.2295 s ÷ 40) — claim, lock,
dispatch, state transition, log append and commit included.

The benchmark asserts only a **machine-independent property**: throughput
falls monotonically as per-job latency rises. An absolute jobs/hour
assertion would be an assertion about the test machine, not the product.

### 7.3 The PB-19 gap, re-derived at the current base

`[Inference — arithmetic from §7.2 and the merged cron data, not a measurement]`

The original gap was `20 jobs/pass × 12 passes/hour = 240 claims/hour`
against PB-19's 600. The binding constraint was never the loop — it was the
**hardcoded cap**. With the cap now configurable and the pass bounded by the
cron time budget rather than by a fixed iteration count:

```
5-minute cadence            = 12 passes/hour  = 300 s of slot per pass
600 jobs/hour ÷ 12 passes   = 50 jobs per pass
300 s ÷ 50 jobs             = 6.0 s of budget available per job
dispatcher overhead         ≈ 0.0057 s per job  (measured, §7.2)
                            → ~5.99 s per job left for the handler itself
```

**So `drain_batch_size = 50` at the unchanged 5-minute cadence meets PB-19
provided per-job handler latency stays under ~6 s** — an ample margin for a
Shopify GraphQL read, though *how* ample is precisely the unmeasured
quantity. The default is deliberately left at **20**: raising it is an
operator decision made against measured latency, and picking 50 for every
store on the strength of a synthetic profile would be inventing exactly the
kind of product policy this batch must not invent.

## 8. Rollback

`[Fact]` Revert the commit. `run_drain()` returns to the fixed-`range(limit)`
loop with the hardcoded cap and no progress reporting; `_claim_for_dispatch`
returns to its single-argument form. Per-job commit, ownership, replay
policy, Layer 2 and concurrency recovery are unaffected either way — this
batch never owned them. The seeded `ir.config_parameter` row may remain inert
(a code revert does not drop data rows; no destructive cleanup is assumed).
No business, job or audit data is touched. The cron interval is whatever the
administrator last set — data, not code.

## 9. Not done and not claimed

- **No Odoo.sh runtime**, no independent review, no acceptance.
- **No Shopify credential, request, mutation or webhook.** No dev-store
  latency was measured, and none is fabricated.
- **PB-19 is not claimed as met.** §7.3 is arithmetic showing the target is
  now *reachable by configuration*; it is not evidence that it is achieved.
- **No multi-worker / topology-B claim.** Overlap and parallelism remain with
  the concurrency plan §13.2, as the packet's own D-PERF1-3 withdrawal says.
- **No exactly-once claim** is made or implied anywhere in the drain.
