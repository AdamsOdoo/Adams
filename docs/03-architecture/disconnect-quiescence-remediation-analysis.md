# Disconnect Quiescence & In-Flight Job Contract — Remediation Analysis (CORE-R2)

> **Status: Proposed for ChatGPT review. NOTHING here is accepted, decided,
> or an opened gate.** Design-only. No addon/code/test/XML/migration change
> accompanies this document. Authorized by the CORE-R2 design gate (PR #153
> comment `4950413650`, docs-only). Verified base:
> `Shopify-connector` @ `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f`
> (PR #153 merged).
>
> **Claim discipline (CLAUDE.md §8).** Every load-bearing statement is
> tagged: **[Fact-Runtime]** = observed in the merged PR #153 evidence;
> **[Fact-Source]** = confirmed by reading Odoo 19 / PostgreSQL 16 source or
> official docs (citation inline); **[Inference]** = our deduction from the
> evidence; **[Recommendation]** = a proposed course of action, subject to
> ChatGPT review; **[Open]** = unresolved. No **[Recommendation]** in this
> file is a Decision. SRR-03 remains **OPEN** regardless of what this file
> proposes.

---

## 1. Executive conclusion

**[Fact-Runtime]** The merged concurrency validation (PR #153,
`docs/05-qa/sync-engine-concurrency-validation-results.md` §10/§14;
`docs/05-qa/evidence/sync-engine-concurrency/scenario-06-real-timeline.md`)
proved with the **real merged `store.action_disconnect()`** that a
concurrent operator disconnect **does not stop an already in-flight business
handler**. The disconnect's cancellation sweep blocks on the running job's
row lock, the handler runs to completion and the job succeeds, and the
disconnect then either serialization-fails (library path, rolled back) or is
retried by Odoo's service layer and completes having cancelled **zero**
running jobs. This is **DEF-PB-1 / SRR-03**, and it is **latent only because
every shipped handler is a no-op today** — it becomes a live-write defect the
moment a domain handler performs a real Shopify mutation.

**[Inference]** The root cause is **two independent facts combining**, not a
bug in `action_disconnect()`:
1. The drain runs the whole batch in **one REPEATABLE READ transaction**, so
   the dispatcher's checkpoint-3 store-state re-check reads a snapshot fixed
   *before* the disconnect could commit — it structurally cannot see a
   disconnect that arrives after the job was claimed.
2. There is **no cross-transaction coordination** between `action_disconnect`
   and the drain, so their only interaction is an incidental PostgreSQL row
   lock on the job record — which orders them *after* the handler has already
   run, exactly the wrong order.

**[Recommendation]** Adopt a **hybrid remediation (Option E)**: an explicit
`disconnecting`/quiescing store state carrying a monotonic
**disconnect generation token** (Option A), a **cooperative pre-side-effect
checkpoint that reads the generation in a fresh transaction** so an in-flight
handler aborts *before* its next external call (Option C, made snapshot-proof),
and a **store-scoped coordination primitive plus a two-phase disconnect**
(Option B) so the credential is cleared only after in-flight work has
quiesced — with a **bounded timeout and operator escalation** for a handler
that never returns. This is prepared as the CORE-R2 implementation packet
(`../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`)
but **its code gate is not opened by this document**.

---

## 2. Accepted runtime evidence

All items are **[Fact-Runtime]** from the merged, control-room-accepted
PR #153 package (final decision: PR #153 comment `4950408383`).

| Evidence ID | Observation |
| --- | --- |
| E-R6-1 | Worker A ran the real single-transaction dispatch (`_claim_for_dispatch` → `_start_running` → hold → `_invoke_handler` → commit), holding the claimed job's row lock at `running` across a controlled pause. |
| E-R6-2 | Worker B called the **real merged `store.action_disconnect()`** (no `store.write` substitute, no monkeypatch, no test hook) — in two variants: a raw library transaction and an XML-RPC call through Odoo's service layer. |
| E-R6-3 | Worker B **blocked** on the running job's row (pg `wait_event_type='Lock'`, `transactionid`; FK `KEY SHARE` contention on `shopify_connector_job`) — captured from `pg_stat_activity` before A was released. |
| E-R6-4 | Worker A's checkpoint-3 probe read `store.state = connected` even though B had already issued its disconnect — the disconnect was *blocked/uncommitted and, under A's snapshot, invisible*. Handler ran; job → `succeeded`; A committed. |
| E-R6-5 (LIB) | On unblock, B raised `could not serialize access due to concurrent update` and rolled back: **store stayed `connected`, job `succeeded`, 0 cancelled, no audit job.** |
| E-R6-6 (RPC) | On unblock, the server logged `SERIALIZATION_FAILURE, 4 tries left…` and `retrying()` re-ran the whole call; on retry the job was already terminal → **store `disconnected`, job `succeeded` (NOT cancelled), audit job "Store disconnected (0 non-terminal business job(s) cancelled)".** |
| E-R6-7 | The earlier direct-`store.write({'state':'disconnected'})` experiment is retained **only** as a narrow REPEATABLE READ snapshot-visibility observation, **not** as the lifecycle result. |
| E-S8 | Two-instance (Topology C, single host) drain of 40 jobs (5 probe + 35 concurrent) showed disjoint claims, no double-processing, no deadlock — the claim mechanism itself is sound; the defect is specifically the disconnect/in-flight interaction. |

**[Inference]** E-R6-4 is the crux: checkpoint-3 is not merely "too late", it
is **snapshot-blind** — it cannot ever see a disconnect committed after the
drain's snapshot opened, no matter when in the handler it reads.

---

## 3. Current transaction sequence (as merged)

**[Fact-Source]** Reconstructed from the merged addon and Odoo 19 source.

**Drain worker (cron → `run_drain`), one REPEATABLE READ transaction:**
1. `shopify_connector_job_dispatch.py::run_drain(limit)` →
   `Job._claim_for_dispatch(limit)`.
   `_claim_for_dispatch` (`shopify_connector_job.py:307`) searches `queued` /
   due `retry_waiting` rows, then `candidates.try_lock_for_update()`.
   **[Fact-Source]** `try_lock_for_update` (`odoo/orm/models.py:5592`) issues
   `SELECT … FOR UPDATE SKIP LOCKED` — a **strong row lock** on each claimed
   job row, held to end of transaction.
2. For each claimed job, `_dispatch_one` → `_start_running` (checkpoint-2):
   `job.write({'state':'running', …})`. `job.write` (`shopify_connector_job.py:221`)
   re-checks the store-state gate for business jobs (`store.state != 'connected'`
   → raise) — but reads the store under the **same snapshot**.
3. `_invoke_handler` (checkpoint-3, `shopify_connector_job_dispatch.py:207`):
   `store.invalidate_recordset(); if job.job_source in BUSINESS_JOB_SOURCES
   and store.state != 'connected': _transition_skipped(...)`.
   **[Fact-Source]** `invalidate_recordset()` clears the ORM cache but **not**
   the PostgreSQL snapshot — the re-read still returns the REPEATABLE READ
   value fixed in step 1.
4. Handler runs (today a no-op); job → `succeeded`.
5. **[Fact-Source]** No `env.cr.commit()` occurs inside `run_drain`; the single
   commit is at the cron callback boundary (`ir_cron.py::_callback:691`,
   `self.env.cr.commit()`), i.e. **one transaction for the whole batch**.

**Operator disconnect (`store.action_disconnect`), RPC → `retrying()`:**
1. **[Fact-Source]** Odoo dispatches the button call through
   `service/model.py::retrying()` (`:160`), which re-runs the entire call on a
   concurrency error, up to `MAX_TRIES_ON_CONCURRENCY_FAILURE = 5`, rolling
   back and `env.transaction.reset()` between tries
   (`PG_CONCURRENCY_EXCEPTIONS_TO_RETRY = (LockNotAvailable,
   SerializationFailure, DeadlockDetected)`).
2. `action_disconnect` (`shopify_connector_store.py:343`): clears the
   credential → `self.write({'state':'disconnected'})` → searches non-terminal
   business jobs → `job.write({'state':'cancelled', …})` per job (+ log) →
   `_create_lifecycle_audit_job(...)`. All in **one transaction**.
3. **[Fact-Runtime]** The per-job cancellation `UPDATE` collides with the
   drain's `FOR UPDATE` lock on the running job row → **blocks** (E-R6-3);
   on the drain's commit, the disconnect's transaction (older snapshot) gets
   `serialization_failure` (E-R6-5/6).

**[Inference]** The two transactions meet **only** at the job row, and PG's
lock ordering there resolves the disconnect *after* the handler has already
executed — the opposite of the operator's intent.

---

## 4. Desired operator contract (target)

**[Recommendation]** Pressing **Disconnect** must mean, precisely:

- **Immediate:** the store is placed in a durable, visible `disconnecting`
  intent state; from that instant **no new business job may be claimed or
  started** for the store, and **no in-flight handler may begin a new external
  Shopify call**.
- **While waiting:** in-flight handlers are given the chance to abort
  cooperatively at their next pre-side-effect checkpoint; queued / retry /
  manual-review business jobs are cancelled; the operator sees a
  "disconnecting…" state, not a silent hang.
- **After the method/flow returns success:** the credential is cleared, the
  store is `disconnected`, and the guarantee is: **no business handler will
  make any further Shopify call for this store under the cleared credential**,
  and every non-terminal business job is in a terminal state
  (`cancelled`/`skipped`) or explicitly escalated.
- **Honest boundary:** a handler that had **already** issued an external write
  *before* the disconnect intent was observable cannot be un-done; the contract
  bounds *new* side effects to zero and relies on the existing idempotency /
  duplicate-prevention substrate for the at-most-one already-issued call.

---

## 5. Required safety invariants

**[Recommendation]** The remediation must hold all of:

- **INV-1 (no post-intent claim/start):** once `disconnecting` is committed,
  no business job for that store transitions into `running`.
- **INV-2 (no post-intent external call):** no business handler for that store
  begins a *new* Shopify call after it can observe the disconnect intent.
- **INV-3 (credential-after-quiesce):** the credential is cleared only after
  in-flight handlers have quiesced (aborted at a checkpoint or terminated), or
  after a bounded timeout with explicit escalation — never leaving a handler
  believing it still holds a valid, uncleared credential mid-call.
- **INV-4 (bounded):** disconnect completes in bounded time; a hung handler
  cannot block it forever.
- **INV-5 (store-local):** the mechanism serializes only operations on the
  *same* store; disconnecting store X never blocks store Y.
- **INV-6 (multi-server):** every guarantee holds across multiple Odoo
  application servers sharing one PostgreSQL database (no reliance on
  in-process state).
- **INV-7 (no unsafe commit / retry-safe):** no explicit `cr.commit()` inside
  an RPC-dispatched model method; every step is atomic and safe under
  `retrying()`.
- **INV-8 (no global serialization / no starvation / no new deadlock):** the
  coordination primitive must not linearize all stores, must not starve the
  drain, and must not introduce a lock-ordering deadlock with the existing
  `FOR UPDATE` job-claim.
- **INV-9 (auditable & idempotent):** every outcome is logged through the
  existing `_system_append` path; a repeated disconnect is a safe audited
  no-op.

---

## 6. Option A — Explicit `disconnecting` state + generation/cancellation token

**Shape.** Add a store state `disconnecting` and a monotonic
`disconnect_generation` (Integer). `action_disconnect` bumps the generation and
sets `disconnecting`; the claim/start gate treats anything other than
`connected` as non-claimable; a running job records the generation it was
claimed under and (in some variant) compares.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | Gives an authoritative, durable, operator-visible **intent flag** and a fail-closed claim/start gate (INV-1). |
| Residual race | **On its own, does not stop an in-flight handler**: a running handler in its REPEATABLE READ snapshot still cannot *see* the new generation committed after its claim — so INV-2 is **not** met by Option A alone. |
| Transaction behavior | One fast store-row write; no job-row contention if it does not sweep jobs in the same step. |
| External API calls | No effect unless paired with a checkpoint that actually reads the flag freshly. |
| Odoo writes | Minimal (one store write + generation bump). |
| Multi-store | Fully store-local (INV-5). |
| Multi-server | Flag is in the DB → visible cross-server **once committed and once re-read in a fresh snapshot** (INV-6 with the Option-C read). |
| Starvation/deadlock | None added. |
| Performance | Negligible. |
| UX | Strong: a real `disconnecting` state to show the operator. |
| Compatibility | Additive to the job/state contract; no change to error taxonomy. |
| Verdict | **Necessary but not sufficient.** Adopted as the *intent-carrying component* of the hybrid; rejected as a standalone fix because it cannot defeat the REPEATABLE READ snapshot by itself. |

---

## 7. Option B — Store-scoped row-lock / lease / quiescence barrier

**Shape.** Drains hold a **shared** store lease while running a job for that
store; `action_disconnect` takes the **exclusive** store lock and thereby
**waits** for in-flight drains to finish before clearing the credential.
Candidate primitives: a transaction-scoped PostgreSQL advisory lock keyed by
store id (`pg_advisory_xact_lock`), or a store-row lock.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | Deterministic **ordering barrier**: credential-clear happens strictly after in-flight handlers release (INV-3), and concurrent disconnect/reconnect requests serialize per store. |
| Residual race | A barrier that only *waits* lets the in-flight handler **complete its live write** (same as today) — so B **alone** satisfies INV-3 but not INV-2. It bounds torn-credential state, not the extra external call. |
| Transaction behavior | Disconnect blocks until drains release; must be bounded (timeout) to satisfy INV-4. |
| External API calls | Does not by itself prevent the in-flight call; prevents *new* claims from starting during the barrier. |
| Odoo writes | Adds a lock acquire per drain pass and per disconnect. |
| Multi-store | Store-keyed → store-local (INV-5) **if** the key is per store, never global. |
| Multi-server | **[Fact-Source]** Advisory locks and row locks live in PostgreSQL → cross-server (INV-6). |
| Starvation/deadlock | **[Open/Risk]** A blocking exclusive lock can **starve** disconnect under a steady stream of drains; combining a store lock with the existing `FOR UPDATE` job lock introduces a **lock-ordering** concern (SRR-09). **[Fact-Source]** transaction-scoped advisory locks auto-release on commit/rollback (avoids the SRR-09 *session*-advisory-lock leak hazard); the `LIMIT`-ordering hazard applies to advisory-lock **function calls embedded in a `SELECT … LIMIT`**, which this design avoids. |
| Performance | One extra lock round-trip per drain pass; acceptable. |
| UX | Enables a truthful "waiting for in-flight sync to stop" state. |
| Compatibility | Neutral to the retry taxonomy; must respect the whole-drain transaction (and future PERF-1 per-job commit). |
| Verdict | **Necessary for the ordering/quiesce guarantee, insufficient for "no new external call".** Adopted as the *coordination component*, with the transaction-scoped advisory lock recommended over a session lock, and the barrier expressed as a **bounded** wait. |

---

## 8. Option C — Fresh-transaction state check immediately before side effects

**Shape.** Immediately before each external Shopify call (and each committing
Odoo write), the handler re-reads the store's state/generation **in a fresh
transaction/cursor** (new snapshot), and aborts cooperatively if a disconnect
has been requested.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | This is the **only** mechanism that lets an in-flight handler *see* a disconnect committed after its claim — because **[Fact-Source]** a new cursor gets a new REPEATABLE READ snapshot (`odoo/sql_db.py:373`), defeating the snapshot-blindness of checkpoint-3. Satisfies INV-2 up to the check→call window. |
| Residual race | A non-zero window between the fresh check and the actual HTTP call: a disconnect committing *inside* that window is not caught for this one call. Making the check the **last** step before the call bounds it to ~microseconds, but it is not literally zero (no cross-system atomicity is possible). |
| Transaction behavior | Requires a short, read-only side transaction (new cursor) — **[Fact-Source]** safe as a read; must **not** be an explicit `commit()` of the main cursor (INV-7). |
| External API calls | Directly gates them: no new call after the check observes disconnect. |
| Odoo writes | The handler's own post-call write still occurs under its main snapshot; needs care so a committed disconnect + a stale-snapshot write don't serialization-fail unproductively. |
| Multi-store | Read is store-scoped. |
| Multi-server | Fresh read sees any server's committed disconnect (INV-6). |
| Starvation/deadlock | None (read-only side txn, no lock held). |
| Performance | One extra lightweight `SELECT` per side effect; negligible next to a network call. |
| UX | Invisible to the operator; realized as fast cooperative cancellation. |
| Compatibility | Additive; needs a documented handler contract ("check before every external effect"), so it must land in core **before** the first domain handler is written. |
| Verdict | **The decisive component for INV-2.** Adopted; but must be paired with an authoritative flag (Option A) to read and a barrier (Option B) so credential-clear waits for handlers that are *past* their check. |

---

## 9. Option D — Per-job transaction / commit-boundary redesign

**Shape.** Replace the whole-drain single transaction with a per-job
transaction (commit after each job), e.g. via Odoo 19's sanctioned
`ir.cron._commit_progress()` (**[Fact-Source]** `ir_cron.py:846`, the
per-batch commit API; the current `run_drain` does **not** use it). This is
the **PERF-1** topic.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | Shrinks each job's snapshot to that one job, so a disconnect committed *between jobs* is visible to the *next* job — narrows the window. |
| Residual race | **Does not stop the job currently running**: within a single job's own transaction the snapshot is still fixed, so a disconnect during that job is still invisible to it. D alone does **not** satisfy INV-2 for the in-flight job. |
| Transaction behavior | Major: per-job commit changes crash/restart semantics and interacts with Q7 (checkpoint/resume ownership, still open). |
| External API calls | No direct effect on the in-flight call. |
| Odoo writes | Each job durable on its own commit — good for idempotency, but see Q7. |
| Multi-store | Neutral. |
| Multi-server | Neutral. |
| Starvation/deadlock | Shorter transactions *reduce* lock-hold time (helps), but do not remove the disconnect race. |
| Performance | The PERF-1 driver (throughput PB-19); not primarily a correctness fix. |
| UX | None directly. |
| Compatibility | **Owned by PERF-1**; CORE-R2 must be *compatible* with it but must not depend on it, and must not pre-empt Q7. |
| Verdict | **Complementary, not a remediation on its own.** CORE-R2 is designed to hold under both the current whole-drain transaction and a future per-job-commit model; the correctness fix is A+B+C, not D. |

---

## 10. Option E — Hybrid (recommended)

**Shape.** Combine the *intent* of A, the *cooperative stop* of C, and the
*ordering/quiesce barrier* of B, structured as a **two-phase, retry-safe,
state-machine disconnect** that never commits explicitly inside an
RPC-dispatched method:

1. **Phase 1 — Request (atomic, fast, `retrying`-safe).** `action_disconnect`
   acquires the store-scoped coordination lock, writes `state='disconnecting'`,
   bumps `disconnect_generation`, stamps the request, and **enqueues a core
   `core_disconnect_quiesce` maintenance job** for the store. It does **not**
   sweep job rows in this phase (so it never queues behind a running job's
   `FOR UPDATE` lock — eliminating the E-R6-3 block and the E-R6-5/6
   serialization failure). Returns immediately; the store now shows
   "disconnecting".
2. **Phase 2 — Quiesce (dispatcher-run, one transaction per pass,
   rescheduled ASAP).** The quiesce job: cancels `queued`/`retry_waiting`/
   `blocked_manual_review` business jobs (not locked by any drain → no block);
   checks whether any `running` business job remains for the store; if yes and
   the timeout is not exceeded, re-schedules itself ASAP; in-flight handlers,
   at their **fresh-transaction pre-side-effect checkpoint (Option C)**, read
   `disconnecting` for a newer generation and abort to `skipped` **before** any
   new Shopify call.
3. **Phase 3 — Finalize.** Once no `running` business job remains (quiesced),
   the quiesce job clears the credential, writes `state='disconnected'`, and
   records an accurate audit (cancelled + skipped + completed-before-checkpoint
   counts). If the **timeout** elapses with a job still `running`, it
   finalizes `disconnected` + credential-clear anyway and **escalates** the
   stuck job (operator-visible alert / `blocked_manual_review` marker),
   satisfying INV-4 without pretending the handler stopped.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | INV-1 (state gate), INV-2 (fresh-txn checkpoint), INV-3 (finalize after quiesce), INV-4 (timeout+escalation), INV-5 (store-keyed), INV-6 (DB-visible), INV-7 (no in-method commit — phases are separate transactions via the dispatcher), INV-8 (store-scoped lock, no job-row lock in phase 1), INV-9 (audited). |
| Residual race | The Option-C check→call microsecond window (bounded, not zero); an already-issued external call cannot be un-done (relies on idempotency); timeout path leaves an escalated stuck job. All stated explicitly in §24. |
| Transaction behavior | Three short transactions instead of one long synchronous method; each atomic and retry-safe; integrates with the cron/dispatch substrate already merged. |
| External API calls | Bounded to at-most-one already-in-flight per running handler; zero new calls after intent is observable. |
| Odoo writes | Store intent write (phase 1), per-job cancels (phase 2), credential-clear + finalize (phase 3) — none contend with a running job's row lock. |
| Multi-store / multi-server | Store-keyed lock + DB flag → store-local and cross-server. |
| Starvation/deadlock | Phase 1 avoids the job-row lock entirely; the store lock is transaction-scoped and released each pass; no lock-ordering cycle with the drain's `FOR UPDATE`. |
| Performance | One extra lightweight read per handler side effect; one short quiesce job per disconnect (usually 1–2 passes). |
| UX | A real, honest `disconnecting → disconnected` progression with an accurate final count and an escalation surface. |
| Compatibility | Works under the current whole-drain transaction **and** a future PERF-1 per-job-commit model; adds one core `job_type` and one state, extends (never breaks) the DEC-009 taxonomy and the DEC-022 lifecycle. |
| Verdict | **Recommended.** It is the minimal combination that satisfies every invariant; no single option does. |

---

## 11. Recommended architecture (proposal)

**[Recommendation]** Implement **Option E** with these concrete elements
(full detail in the CORE-R2 packet; nothing here is a Decision):

- **Store state** gains `disconnecting` (between `connected` and
  `disconnected`); `reconnect`/`activate` clear it.
- **Store fields** `disconnect_generation` (Integer, monotonic),
  `disconnect_requested_at` (Datetime), `disconnect_requested_by`
  (`res.users`, non-secret audit).
- **Coordination primitive:** a **transaction-scoped PostgreSQL advisory lock
  keyed by store id** (`pg_advisory_xact_lock`) — chosen over a session-scoped
  advisory lock (auto-released on commit/rollback → no SRR-09 leak) and over a
  raw blocking `SELECT … FOR UPDATE` on the store row (which would need raw
  SQL and could starve). Used **only** to serialize disconnect/reconnect/
  quiesce for one store — never held across a Shopify network call, never
  combined with a `LIMIT`-bounded query.
- **Claim/start gate:** `_claim_for_dispatch` and the `write→running` gate
  treat `state != 'connected'` as non-startable for business jobs (already
  true for `disconnected`; `disconnecting` is added to the non-startable set).
- **Handler cooperative-cancel contract (core seam, no domain code yet):** a
  core helper `store._is_quiescing(generation)` that reads the store's current
  state/generation **in a fresh cursor**; the future handler protocol calls it
  immediately before each external side effect and raises a
  `JobQuiescedError` → routed to `skipped`. Shipped as a **documented core
  contract + the read helper**, so the first domain handler is born compliant.
- **Two-phase disconnect** via a new core `job_type='core_disconnect_quiesce'`
  driven by the existing dispatcher, with a `DISCONNECT_QUIESCE_TIMEOUT`
  constant and escalation on timeout.

---

## 12. Rejected alternatives

**[Recommendation]** Recorded here and proposed for the rejected-approaches
log **only after ChatGPT review** (not auto-logged by this session):

- **R-1: "Make checkpoint-3 read the store in a fresh transaction and skip"
  (Option C only).** Rejected as a *complete* fix: it stops handlers still
  before their check, but does nothing for the credential-clear ordering or
  for a handler already past its check, and leaves `action_disconnect` still
  colliding on the job-row lock. Kept as a *component*.
- **R-2: "Have `action_disconnect` take `FOR UPDATE` on the running job and
  force-cancel it."** Rejected: it still orders *after* the handler (the lock
  is only granted once the drain commits), reproduces the serialization
  failure, and can force-cancel a job whose external write already happened —
  worsening the torn state.
- **R-3: "Global disconnect lock."** Rejected: violates INV-5/INV-8 (serializes
  all stores; starvation).
- **R-4: "Session-scoped advisory lock."** Rejected: **[Fact-Source]** not
  released by a transaction rollback (SRR-09 hazard) → a failed disconnect can
  leak the lock.
- **R-5: "Explicit `cr.commit()` inside `action_disconnect` to publish the
  intent mid-method."** Rejected: violates INV-7; **[Fact-Source]** breaks
  `retrying()` (it cannot roll back past a commit) and Odoo's atomicity
  guidance.
- **R-6: "Per-job commit (Option D) alone."** Rejected as a correctness fix (it
  cannot stop the currently-running job); deferred to PERF-1 as a throughput
  concern, with CORE-R2 kept compatible.

---

## 13. State-transition proposal

**[Recommendation]** Store lifecycle (extends DEC-022, does not break it):

```
setup_incomplete ──activate──▶ connected
connected ──action_disconnect (phase 1)──▶ disconnecting
disconnecting ──quiesce complete OR timeout (phase 3)──▶ disconnected
disconnecting ──(operator cancels? out of scope; see §25 Q-QS-4)
disconnected ──action_reconnect──▶ connected | reconnect_needed
connected/disconnecting ──auth failure──▶ reconnect_needed (unchanged)
```

- `disconnecting` is **non-startable** for business jobs (claim + `write→running`
  gates) and **non-enqueueable** for business jobs (the `create()` gate already
  requires `connected`).
- A second `action_disconnect` while `disconnecting` is an audited no-op that
  bumps nothing (idempotent, INV-9).

---

## 14. Lock / lease proposal

**[Recommendation]**
- **Primitive:** `pg_advisory_xact_lock(key)` where `key =
  hashtext('shopify.connector.store:' || store_id)` (or a two-int key domain
  reserved for this connector to avoid collisions). Transaction-scoped.
- **Phase 1** acquires it, writes intent, releases on commit. **Phase 2/3**
  passes re-acquire it per pass. Drains do **not** need to take the store lock
  (they already hold the job-row `FOR UPDATE`); instead the *ordering* that
  matters — "credential-clear after in-flight handlers" — is enforced by
  phase 3 waiting on **"no `running` business job for this store"**, a query,
  not a lock. The advisory lock's job is only to serialize *disconnect vs
  reconnect vs quiesce* for the same store.
- **[Open]** Whether to additionally have drains take a **shared** store
  advisory lock so phase 3 can block-wait instead of poll is an open
  refinement (§25 Q-QS-2); the recommended baseline is **poll-for-quiesce**
  (simpler, no shared-lock starvation), with the advisory lock only for the
  narrow serialize-mutations role.

---

## 15. Credential lifecycle

**[Recommendation]**
- The credential is **not** cleared in phase 1. It is cleared in phase 3, after
  quiescence, through the **existing Task 002 `action_clear_token` service**
  (no second clear path) — preserving INV-3 and the DEC-022 credential-history
  guarantee.
- Between phase 1 and phase 3 the credential is still present but **unusable by
  new work** (no business job can start; in-flight handlers abort at their
  checkpoint). This is deliberate: it keeps an in-flight, already-authorized
  call from losing its credential mid-request.
- On the timeout path, the credential is cleared at finalize regardless; the
  escalated stuck job is flagged so an operator knows a handler outlived the
  quiesce window.

---

## 16. Job lifecycle

**[Recommendation]**
- **Queued / retry_waiting / blocked_manual_review** business jobs → `cancelled`
  in phase 2 (as today), reason `Store disconnected.` (audited).
- **Running** business jobs → the handler aborts cooperatively to `skipped`
  (new reason "Store disconnecting — aborted before side effect") when it
  observes the intent at its fresh-txn checkpoint; a job already past its
  checkpoint runs to its natural terminal state and phase 3 waits for it
  (bounded).
- **Timed-out running** job → left in `running` but **escalated**: a
  `state_change` log + an operator-visible marker; **[Open]** whether to add a
  `blocked_manual_review`-style terminal or a dedicated `interrupted`
  sub-state is Q-QS-3.
- No job is ever **deleted**; history is preserved (DEC-022 invariant).

---

## 17. External-side-effect boundary

**[Recommendation]** The core contract every future domain handler must honor:

> Before **each** outbound Shopify call **and** before **each** committing
> Odoo write that reflects a Shopify effect, call `store._is_quiescing(...)`
> (fresh-cursor read). If it returns true, raise `JobQuiescedError` and make
> no further external call.

- This makes the external-effect boundary **the** enforcement point for INV-2.
- Handlers must be written so that the fresh check is the **last** action
  before the call (minimizing the residual window, §24).
- Idempotency keys / `operation_scope_key` remain the safety net for the
  at-most-one already-issued call.

---

## 18. Failure / retry behavior

**[Recommendation]**
- **`JobQuiescedError`** is a cooperative abort, **not** an error class — it
  routes to `skipped`, never to the retry taxonomy, and never counts as a
  handler failure.
- **Serialization failures** in the quiesce job's own writes are handled by
  the existing `retrying()` layer (RPC) or, for the cron-run quiesce passes,
  by the dispatcher's normal transaction boundary; because phase 1 no longer
  contends on the running job's row, the E-R6-5/6 serialization failure is
  **structurally avoided**, not merely retried.
- **[Fact-Source]** `retrying()` classifies `LockNotAvailable /
  SerializationFailure / DeadlockDetected`; the design deliberately avoids
  generating these on the disconnect path, and never adds a `NOWAIT`/`FOR
  UPDATE` on the job row from the disconnect side.

---

## 19. Multi-worker and multi-server behavior

**[Recommendation] / [Fact-Source]**
- All coordination state (store state, generation, advisory lock) lives in
  PostgreSQL → correct across multiple `--workers` and multiple Odoo servers on
  one DB (INV-6). This is the one axis the merged validation could **not**
  fully exercise (Scenario 8 was single-host, two-instance) — so the packet
  mandates a genuine two-server test.
- Multiple concurrent drains on different servers each abort their own in-flight
  handler via the same fresh-txn checkpoint; the quiesce job (whichever server
  runs it) polls the shared `running` count, so it converges regardless of which
  server holds which job.
- **[Open]** True multi-node (multi-host) proof remains SRR-09's residual; the
  packet requires at least a two-server test and names multi-host as follow-up.

---

## 20. Performance implications

**[Recommendation] / [Inference]**
- Steady-state cost: **one extra lightweight `SELECT`** (fresh-cursor state/gen
  read) per handler side effect — negligible beside a Shopify network round-trip.
- Disconnect cost: one fast phase-1 write + typically 1–2 quiesce passes; no
  long synchronous wait on the operator's RPC thread.
- No global serialization → no throughput cliff for other stores (INV-5).
- Interaction with **SRR-01** (>64 savepoints) and **PB-19** (≥600 jobs/h):
  CORE-R2 adds no savepoints and no per-record locks; it is compatible with the
  PERF-1 `_commit_progress` per-job-commit model and does not change batch size.

---

## 21. UI implications

**[Recommendation]** (UI is **not** built here — U-track owns it.)
- A new `disconnecting` state needs an operator-visible label/badge
  ("Disconnecting — stopping in-flight sync…") and a completion signal.
- The final audit message should report the accurate counts (cancelled /
  skipped / completed-before-checkpoint) and any escalation.
- The Disconnect button should reflect the two-phase flow (returns immediately;
  the store shows progress) rather than appearing to hang.

---

## 22. Migration / backward compatibility

**[Recommendation]**
- Adding a `disconnecting` state value and three store fields is **additive**;
  existing rows default cleanly (`disconnect_generation=0`, nulls).
- No existing job state, error class, or `job_source` changes; one new core
  `job_type='core_disconnect_quiesce'` is added (diagnostic/core source, never
  business-gated), consistent with `core_manual_maintenance`.
- The new `LC-1` historic-job-type reassignment (master-plan step 4) must be
  compatible: `core_disconnect_quiesce` is a core type and should be registered
  before/with LC-1 so it participates in that lifecycle from day one
  (sequencing noted in §26 and the packet).
- Rollback = revert the CORE-R2 PR; because the states/fields are additive and
  no data is destroyed, revert is clean (stores fall back to the old
  `connected → disconnected` path).

---

## 23. Required tests (specified, not implemented)

**[Recommendation]** The packet mandates (all using the **real merged
`action_disconnect()`**, no monkeypatch, no test hook):

1. **T-1 genuine race, handler-before-checkpoint:** two independent
   processes — a drain holding a business job at `running` *before its
   external-effect checkpoint*, and a real `action_disconnect()`. Assert the
   handler aborts to `skipped`, **no external call is made**, credential cleared
   after quiesce, store `disconnected`, accurate audit.
2. **T-2 genuine race, handler-past-checkpoint:** handler already committed its
   (mock) external effect. Assert phase 3 waits, job reaches its natural
   terminal, credential cleared after, no double effect.
3. **T-3 timeout/escalation:** a handler that never returns. Assert bounded
   finalize + escalation marker + audit.
4. **T-4 two-server (Topology C):** two `odoo-bin` instances, one DB; disconnect
   on server 1 while server 2 drains. Assert INV-2/INV-3 hold cross-server.
5. **T-5 multi-store isolation:** disconnect store X does not block a drain for
   store Y (INV-5).
6. **T-6 idempotent re-disconnect** and **T-7 reconnect after disconnecting**
   (state-machine correctness).
7. **T-8 no-serialization-failure:** assert the disconnect path no longer
   produces `serialization_failure` against the running job (regression vs
   E-R6-5/6).
8. **Odoo.sh runtime green** for the whole `shopify_connector_core` suite
   (per SRR-06: concurrency fixes are only trusted after live runtime proof).

---

## 24. Residual risks

**[Recommendation] / [Open]** Stated honestly:

- **RR-1 (check→call window):** the Option-C fresh check cannot be atomic with
  the external HTTP call; a disconnect committing in that microsecond window is
  not caught for that one call. Mitigation: check is the last step before the
  call; window is bounded, not zero.
- **RR-2 (already-issued call):** a call issued *before* the intent was
  observable cannot be un-done; relies on idempotency/duplicate-prevention.
- **RR-3 (timeout path):** a truly hung handler is escalated, not stopped;
  credential is cleared regardless. This is a deliberate INV-4 trade.
- **RR-4 (multi-host):** two-server test is single-host; true multi-node
  remains SRR-09 residual.
- **RR-5 (advisory-lock hygiene):** transaction-scoped lock chosen to avoid the
  session-lock leak; must never be combined with a `LIMIT`-bounded query
  (SRR-09 hazard) — enforced by keeping the lock call standalone.
- **RR-6 (SRR-06 class):** this is a concurrency/timing fix — untrusted until
  live Odoo.sh proof; static review alone is insufficient (PR #121 precedent).

---

## 25. Open questions

**[Open]** For ChatGPT to resolve at review / in the gate:

- **Q-QS-1:** Is the target contract "cooperatively cancel in-flight handlers
  before their next side effect" (recommended) or "let in-flight handlers
  complete, only guarantee credential-after-quiesce" (weaker)? The
  recommendation assumes the former.
- **Q-QS-2:** Poll-for-quiesce (recommended baseline) vs a shared/exclusive
  store-advisory-lock block-wait barrier (§14).
- **Q-QS-3:** Timeout escalation target for a stuck job — reuse
  `blocked_manual_review`, add an `interrupted` sub-state, or a marker-only
  approach (§16).
- **Q-QS-4:** Should an operator be able to **cancel** a `disconnecting`
  (abort the disconnect) or is it one-way? (Recommend one-way for MVP.)
- **Q-QS-5:** Exact `DISCONNECT_QUIESCE_TIMEOUT` default (proposed: a small
  bounded value, e.g. one or two drain intervals) — a tuning constant, not an
  architecture choice.
- **Q-QS-6:** Ownership boundary vs **Q7 (checkpoint/resume)** and **PERF-1**:
  CORE-R2 must not pre-decide per-job-commit; confirm the seam.
- **Q-QS-7:** Whether the handler cooperative-cancel contract ships as a
  documented core seam **now** (recommended, so domain handlers are born
  compliant) or is deferred to the first domain task.

---

## 26. ChatGPT decisions required

**[Open]** This document requests, at review:

1. **D-CR2-A:** Accept/revise the **target operator contract** (§4) and the
   safety invariants (§5).
2. **D-CR2-B:** Accept/revise the **recommended architecture = Option E**
   (§10/§11), or select a named alternative (§12).
3. **D-CR2-C:** Accept/revise the **coordination primitive** choice
   (transaction-scoped store advisory lock + poll-for-quiesce; §14).
4. **D-CR2-D:** Accept/revise the **new store state + fields + `job_type`**
   (§13/§22) and the **handler cooperative-cancel core seam** timing (Q-QS-7).
5. **D-CR2-E:** Confirm the **critical-path placement** — CORE-R2 must merge
   **before any live Shopify mutation task** (013 inventory, 014 fulfillment,
   015 product export) and before UAT; recommendation on its ordering vs
   012/010B/011B (see the master-plan insert and the packet §Critical path).
6. **D-CR2-F:** Confirm **SRR-03 stays OPEN**, **SRR-04/09 stay REDUCED
   (not closed)**, and that **no implementation gate is opened** by accepting
   this analysis — only by a later, explicit CORE-R2 gate act on the packet.

> **Nothing above is accepted.** These are proposals and recommendations for
> the control room. The CORE-R2 code gate remains **closed** until ChatGPT
> issues an explicit gate act on the implementation packet.
