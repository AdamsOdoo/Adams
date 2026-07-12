# Disconnect Quiescence & In-Flight Job Contract — Remediation Analysis (CORE-R2)

> **Status: Proposed for ChatGPT review. NOTHING here is accepted, decided,
> or an opened gate.** Design-only. No addon/code/test/XML/migration change
> accompanies this document. Authorized by the CORE-R2 design gate (PR #153
> comment `4950413650`, docs-only). Verified base:
> `Shopify-connector` @ `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f`
> (PR #153 merged).
>
> **Revision 2 (2026-07-12) — control-room review `4951115877`.** Re-evaluated
> Option E rather than defending revision 1. Nine load-bearing corrections are
> folded in: (1) a complete in-flight taxonomy incl. **claimed-but-not-started
> (row-locked) jobs**; (2) **request-accepted ≠ disconnect-completed**;
> (3) enforcement moved to the **central API-client boundary** + a persisted
> **connection epoch**; (4) a **dedicated, non-starving quiesce controller**
> with an exact state machine; (5) **timeout escalation that never writes the
> locked job row**; (6) a **bounded** coordination decision (advisory lock
> demoted/dropped); (7) critical path broadened to **any Shopify call incl.
> reads**; (8) a **Phase A/B/C side-effect contract** that does not abort local
> reconciliation of an admitted call; (9) an **executable** INV-2 test strategy
> against the real production gate.
>
> **Claim discipline (CLAUDE.md §8).** Tags: **[Fact-Runtime]** = observed in
> merged PR #153 evidence; **[Fact-Source]** = confirmed by reading Odoo 19 /
> PostgreSQL 16 source or official docs (citation inline); **[Inference]** =
> deduction; **[Recommendation]** = proposed, subject to ChatGPT review;
> **[Open]** = unresolved. No **[Recommendation]** is a Decision. SRR-03 stays
> **OPEN** regardless.

---

## 1. Executive conclusion

**[Fact-Runtime]** PR #153 proved with the **real merged
`store.action_disconnect()`** that a concurrent operator disconnect **does not
stop an already in-flight business handler**: the disconnect blocks behind the
running job's row lock, the handler runs to completion, the job succeeds, and
the disconnect then serialization-fails (library, rolled back) or is retried by
Odoo's service layer and completes cancelling **zero** running jobs. This is
**DEF-PB-1 / SRR-03**, latent only because every shipped handler is a no-op.

**[Inference]** Root cause = two facts combining: the drain runs the whole batch
in **one REPEATABLE READ transaction** (so the dispatcher's checkpoint-3 store
re-check is snapshot-blind), and there is **no cross-transaction coordination**
between disconnect and the drain (so their only interaction is an incidental
job-row lock, which orders them *after* the handler has already run).

**[Recommendation]** The remediation's **enforcement point is the central
Shopify API client** (`shopify.connector.api.client.execute()`), made
**fail-closed** against a **persisted per-store connection epoch** — because a
voluntary per-handler checkpoint is too easy for a future domain module to
omit. Around that enforcement point sits a lifecycle state machine: a
`disconnecting` store state; a monotonic **`connection_generation`**; a
persisted **`job.expected_connection_generation`**; a **dedicated,
high-priority, trigger-driven quiesce controller** (its own `ir.cron`, not a
drained business job — so it cannot starve); **non-blocking** job cancellation
via `try_lock_for_update()` + `SKIP LOCKED` + bounded polling; and **timeout
escalation recorded on independently-writable store-level fields** that never
touch a locked job row. The store-row state+generation update (under Odoo's
`retrying()`) is the coordination primitive; **the advisory lock is dropped**
from the recommended design (demoted to a bounded, rejected-unless-needed
alternative). This is prepared as the CORE-R2 packet
(`../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`);
**its code gate is not opened by this document.**

---

## 2. Accepted runtime evidence

**[Fact-Runtime]** from the merged, control-room-accepted PR #153 (final
decision `4950408383`).

| ID | Observation |
| --- | --- |
| E-R6-1 | Worker A ran the real single-transaction dispatch (`_claim_for_dispatch` → `_start_running` → hold → `_invoke_handler` → commit), holding the claimed job's row lock at `running`. |
| E-R6-2 | Worker B called the **real merged `store.action_disconnect()`** (no substitute, no monkeypatch, no test hook), library and XML-RPC variants. |
| E-R6-3 | Worker B **blocked** on the running job's row (pg `wait_event_type='Lock'`, `transactionid`; FK `KEY SHARE` contention on `shopify_connector_job`). |
| E-R6-4 | Worker A checkpoint-3 read `store.state = connected` (disconnect blocked/uncommitted and, under A's snapshot, invisible). Handler ran; job → `succeeded`; A committed. |
| E-R6-5 (LIB) | On unblock, B raised `could not serialize access due to concurrent update`, rolled back: store stayed `connected`, job `succeeded`, 0 cancelled. |
| E-R6-6 (RPC) | On unblock, `retrying()` re-ran the whole call; job already terminal → store `disconnected`, job `succeeded` (NOT cancelled), audit "0 … cancelled". |
| E-S8 | Two-instance (Topology C, single host) drain of 40 jobs (5 probe + 35 concurrent): disjoint claims, no double-processing, no deadlock — the claim mechanism itself is sound. |

---

## 3. Current transaction sequence (as merged) — and the complete in-flight taxonomy

### 3.1 Current sequence

**[Fact-Source]** Reconstructed from the merged addon + Odoo 19 source.

- **Drain (`run_drain`), one REPEATABLE READ transaction:**
  `_claim_for_dispatch(limit)` (`shopify_connector_job.py:307`) searches
  `queued`/due `retry_waiting` rows `order='id asc' limit=limit`, then
  `candidates.try_lock_for_update()`. **[Fact-Source]** `try_lock_for_update`
  (`odoo/orm/models.py:5592`) issues `SELECT … FOR UPDATE SKIP LOCKED` — a
  **strong row lock on each claimed job row, held to end of the drain
  transaction** — and **skips** rows another worker already locked. Then per
  job: `_start_running` (checkpoint-2, `write→running`) and `_invoke_handler`
  (checkpoint-3 store re-check). **[Fact-Source]** No `commit()` inside
  `run_drain`; the single commit is at the cron boundary (`ir_cron.py:691`).
- **Disconnect (`action_disconnect`), RPC → `retrying()`:** clears credential →
  `store.write('disconnected')` → cancels non-terminal business jobs (per-job
  `UPDATE`) → audit job. **[Fact-Runtime]** the per-job `UPDATE` collides with
  the drain's `FOR UPDATE` on the running row → blocks → serialization-fails.

### 3.2 Complete in-flight taxonomy (corrects review point 1)

**[Fact-Source] / [Inference]** A business job for the disconnecting store is in
exactly one of these states at the instant of disconnect. Revision 1's claim
that "queued/retry/manual jobs are not locked by any drain" was **false** — row
`C` below is the counterexample.

| # | Sub-state | Locked by a drain? | Why it matters | How the design handles it |
| --- | --- | --- | --- | --- |
| **A** | `queued`, **unlocked** | No | Cancellable now | Phase-2 non-blocking sweep locks it via `try_lock_for_update()` and cancels it. |
| **B** | `retry_waiting`, **unlocked** | No | Cancellable now (only if due it would be claimable, but any non-terminal retry row is cancellable) | Same as A. |
| **C** | **claimed & row-locked, still `queued`/`retry_waiting`** | **Yes** (`_claim_for_dispatch` locked it; `_start_running` not yet called) | **A `running`-only poll can finalize while this row later becomes `running`.** A cancellation `UPDATE` on it **blocks** exactly like PR #153. | Phase-2 sweep **skips it** (SKIP LOCKED — no block, no serialization failure). It cannot be force-cancelled now; instead the **central API gate** guarantees that even if the drain later starts it, it makes **no Shopify call** (fresh state/epoch mismatch). It converges to terminal later: either the drain aborts it at the gate (→ `skipped`), or the drain crashes and the lock releases and a later poll cancels it. |
| **D** | `running`, **before its next Shopify call** | Yes (own drain) | Could still call Shopify | At its `execute()` the **central gate fresh-reads** and fail-closes → `skipped`, **no call**. |
| **E** | `running`, **a Shopify call already issued** | Yes | Call cannot be un-done | Phase-B contract (§6): the call stands; the handler completes its **local Odoo reconciliation**; the controller waits (bounded). |
| **F** | `running`, **completing local Odoo reconciliation** | Yes | Must not be aborted | Allowed to finish (§6 Phase B). |
| **G** | terminal (`succeeded`/`failed_*`/`skipped`/`cancelled`) | No | Nothing to do | Ignored. |

**[Recommendation]** The five answers the review demanded:

1. **How Phase 2 avoids blocking on claimed-but-not-started rows (C):** it
   never issues a bare cancellation `UPDATE`. It runs
   `candidates.try_lock_for_update()` (SKIP LOCKED) and cancels **only the rows
   it could lock**; locked rows are skipped and retried on the next bounded poll
   pass. No wait, no serialization failure.
2. **How finalization detects them (C):** finalization does **not** require
   "all jobs terminal". It requires the **safety** invariant (no post-epoch
   Shopify call), which the central gate already guarantees for C/D. The
   controller polls the count of **`running`** business jobs as a *courtesy*
   wait for admitted calls (E/F); C rows are handled by the gate, not by the
   wait.
3. **How C is prevented from calling Shopify after it later starts:** the
   central API gate — the drain that owns C carries a **stale snapshot** and may
   `_start_running` it, but the gate's **fresh-cursor** read of
   `state`/`connection_generation` fail-closes the call.
4. **How C ultimately reaches terminal:** the owning drain aborts it at the gate
   (→ `skipped`) on this pass, or (crash case) the lock releases and a later
   Phase-2 poll cancels it.
5. **How the disconnect flow avoids recreating the PR #153 serialization
   failure:** Phase 1 performs **no** blocking write to any running/claimed job
   row; the sweep uses SKIP LOCKED; the store-row state/generation write does
   not touch job rows. The disconnect path therefore never queues behind the
   drain's `FOR UPDATE`.

---

## 4. Desired operator contract (target) — request vs completion

**[Recommendation]** (corrects review point 2 / §7)

- **Pressing Disconnect (Phase-1 RPC return) means ONLY:** *request accepted;
  the store is now `disconnecting`.* It does **not** mean the credential is
  cleared, that all work is terminal, or that quiescence is complete.
- **Immediately guaranteed on Phase-1 commit:** no business job may be
  claimed/started for the store, and — via the central gate + epoch bump — **no
  business Shopify call can be admitted** (new or from any in-flight handler).
- **Disconnect is *completed* only when ALL hold:** `state == 'disconnected'`;
  credential cleared; final lifecycle audit written; and **no old-generation
  business job can make another Shopify call** (guaranteed structurally by the
  epoch gate, so this is true the moment the generation is bumped, and the
  terminal audit records it).
- **Honest boundary:** a Shopify call **already issued** before the epoch bump
  was observable cannot be un-done; the contract bounds *new* calls to zero and
  relies on the existing idempotency / duplicate-prevention substrate.

---

## 5. Required safety invariants

**[Recommendation]**

- **INV-1 (no post-intent claim/start):** once `disconnecting` commits, no
  business job for the store transitions into `running` **and successfully
  calls Shopify**. (A drain may still *start* a stale-snapshot row — INV-2 is
  what actually protects the external world.)
- **INV-2 (no post-epoch external call):** no business Shopify call is admitted
  by the central client once the store's committed `connection_generation` no
  longer matches the calling job's `expected_connection_generation` (or the
  store is not `connected`). **This is the load-bearing invariant.**
- **INV-3 (credential-after-admitted-work, bounded):** the credential is cleared
  after a **bounded** wait for `running` business jobs to drain (so admitted
  calls' local reconciliation can finish), or on timeout — never blocking
  indefinitely.
- **INV-4 (bounded):** disconnect completes in bounded time; a hung handler
  cannot block it.
- **INV-5 (store-local):** only same-store operations serialize.
- **INV-6 (multi-server):** all guarantees hold across multiple Odoo servers on
  one PostgreSQL DB (no in-process state).
- **INV-7 (retry-safe / no unsafe commit):** no explicit `cr.commit()` inside an
  RPC-dispatched model method; every step atomic under `retrying()`.
- **INV-8 (no starvation / no global serialization / no new deadlock):** the
  quiesce controller cannot starve behind the business backlog; no primitive
  linearizes all stores; no lock-ordering cycle with the drain's `FOR UPDATE`.
- **INV-9 (auditable, idempotent, non-blocking escalation):** every outcome is
  logged; a repeated disconnect is a safe no-op; timeout escalation writes only
  independently-writable surfaces.

---

## 6. Side-effect phase contract (corrects review point 8)

**[Recommendation]** Replaces the vague "check before every committing Odoo
write." The handler protocol has three phases:

- **Phase A — before a Shopify call:** the central client runs the fresh
  state+epoch gate. If the store is `disconnecting`/`disconnected` or the epoch
  no longer matches → **fail closed**, raise `ShopifyQuiescedError`, route the
  job to `skipped`. **No external call is made.**
- **Phase B — a Shopify call is admitted / already issued:** disconnect **cannot
  undo** it. The handler **completes the corresponding local Odoo
  reconciliation** (write the binding/result/idempotency record for the call
  that already happened). The design **must not** roll back or abandon the local
  record merely because a disconnect was requested after the call began —
  otherwise the local state diverges from the real Shopify state (a worse bug
  than the one being fixed).
- **Phase C — before another Shopify call:** run the Phase-A gate again; abort to
  `skipped` if quiescing/stale. So a multi-call handler makes **at most the one
  call already in flight** after a disconnect, and **zero** further calls.

**What `action_disconnect` completion guarantees:** no *new* Shopify call for the
store; every non-terminal business job converges to terminal or is escalated;
credential cleared; store `disconnected`. **What it cannot undo:** a single
call already in flight at the instant the epoch was bumped (idempotency net).

---

## 7. Option A — Explicit `disconnecting` state + connection epoch (revised)

**Shape.** Add store state `disconnecting` and a monotonic
`connection_generation`; persist `job.expected_connection_generation`; the
central gate compares fresh store epoch to the job's expected epoch.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | Durable, operator-visible intent + a **persisted epoch** that survives a disconnect→reconnect cycle (an old job's expected epoch never matches a *new* connected epoch — §8). |
| Residual race | The epoch is only *enforced* where it is read; a flag alone doesn't stop a handler that never reads it → must be paired with **central enforcement (Option C-central, §9)**. |
| Transaction behavior | One fast store-row write + epoch bump; no job-row contention. |
| External calls | No effect until the enforcement point reads it. |
| Multi-store / multi-server | Store-local; DB-visible cross-server. |
| Verdict | **Necessary intent+epoch carrier.** Adopted; insufficient alone. |

---

## 8. Connection-epoch contract (corrects review point 4/§4 of the review)

**[Recommendation]** Replaces the underspecified `disconnect_generation`.

- **Store field:** `connection_generation` (Integer, default `0`, readonly,
  non-secret). Semantics: the identity/validity epoch of the store's current
  Shopify connection.
- **Increments on every lifecycle transition that changes connection identity or
  validity:** (a) disconnect **request** (Phase 1); (b) **credential
  replacement** (`action_replace_token`/`action_set_token`); (c) **successful
  reconnect** (`action_reconnect` → connected); (d) **activation**
  (`action_activate` → connected). Each bump is a single store-row write.
- **Job field:** `expected_connection_generation` (Integer, persisted, readonly).
  **Captured at enqueue (`create`) time** — a business job is created only for a
  `connected` store (existing gate), so it records that store's current
  `connection_generation`. Persisting on the job (not re-reading later) is what
  makes a **rapid disconnect→reconnect** safe: the old job keeps its old
  expected epoch; the reconnected store has a **higher** epoch; the fresh state
  is `connected` again but the epochs **differ**, so the gate rejects the old
  job. Relying on current state alone would wrongly admit it.
- **Business-call admission rule (central gate, §9):** a business Shopify call
  proceeds **only when both** hold, read in a **fresh cursor**: (1) fresh
  `store.state == 'connected'`; **and** (2) fresh
  `store.connection_generation == job.expected_connection_generation`.
- **Diagnostic/setup calls differ:** `action_test_connection`, readiness, and
  `action_reconnect` are **lifecycle** calls — they establish/verify the
  connection and are Admin-invoked directly (no dispatched business job, no
  expected epoch). They run under an explicit **lifecycle exemption** (§9), not
  the business-epoch match, so setup can proceed while state is not yet
  `connected`. They can never be reached by a drained business handler.

---

## 9. Option C-central — Central API-client fail-closed enforcement (corrects review point 3/5)

**Shape.** Enforce INV-2 inside the one method every Shopify request already
crosses — `shopify.connector.api.client.execute()` — rather than in a voluntary
per-handler checkpoint.

**[Fact-Source]** `execute(self, store, query, variables=None)` is the sole
public entry; `_send(self, store, body)` is the only method with the HTTP call
and is the **transport-injection seam** tests already override
(`shopify_connector_api_client.py`). No mutation method exists yet; the gate
must cover reads and any future mutation identically.

**Three enforcement options compared:**

| Option | Omission risk | Verdict |
| --- | --- | --- |
| **A. voluntary per-handler checkpoint** | A future domain handler simply forgets to call it → INV-2 silently lost. | **Rejected as the primary control.** |
| **B. central API-client fail-closed gate** | Cannot be bypassed without deliberately stripping the dispatcher-set context; covers every current and future call site. | **Recommended.** |
| **C. central gate + optional handler convenience helper** | Same structural guarantee as B, plus a handler-friendly early-exit helper for good UX. | **Recommended (B + a thin helper).** |

**[Recommendation]** Adopt **B (+ optional helper) = C**. Pinned mechanics:

- **How a business call presents its epoch:** the **dispatcher** sets a
  business-call context when it invokes a business handler — e.g.
  `handler(job)` is called on an env carrying
  `shopify_business_job_id = job.id` (and the captured
  `expected_connection_generation`). The handler inherits that context, so its
  `execute()` calls are business calls **by construction**; the handler does not
  opt in.
- **Fail-closed default:** `execute()` classifies the call from context:
  - **business context present** → run the fresh state+epoch gate (§8); block on
    mismatch.
  - **explicit lifecycle context** (`shopify_lifecycle_call=True`, set **only**
    by `action_test_connection`/readiness/`action_reconnect`) → allowed under
    the lifecycle contract (no epoch match).
  - **neither** → **fail closed** (raise): a business Shopify call outside a
    dispatched-job context is not permitted. Omitting the context does not
    *disable* the gate; it *blocks* the call. This is what makes omission
    structurally hard.
- **Fresh-cursor read mechanism:** the gate reads `state`/`connection_generation`
  in a **new cursor** (`self.env.registry.cursor()`), because the handler runs
  inside the drain's REPEATABLE READ transaction whose snapshot cannot see a
  post-claim disconnect. **[Fact-Source]** a new cursor gets a new snapshot
  (`odoo/sql_db.py:373`).
- **Cursor/environment ownership & close/rollback:** the gate **owns** the new
  cursor via a `with` block (or try/finally), reads two non-secret columns, and
  **always rolls back and closes** it — it never commits, never writes, never
  leaks a connection (INV-7).
- **Security/ACL & secrets:** the fresh read touches only `state` and
  `connection_generation` (non-secret). The access **token** is still obtained
  only through the existing sanctioned `_get_access_token` path — the gate reads
  no secret and logs none. No new `sudo()` beyond a read-only superuser read of
  two non-secret fields (respecting the CORE-R1 three-site sudo inventory — the
  gate must not add a *model-layer* mutating `sudo()`; if a read helper needs
  elevated read it is a read-only, non-mutating call, and the packet pins the
  exact guard).
- **Error / cooperative-skip routing:** a blocked business call raises
  `ShopifyQuiescedError` (a cooperative-abort signal, **not** an error class);
  the dispatcher routes the job to `skipped`, never to the retry taxonomy.

| Dimension | Assessment |
| --- | --- |
| Exact guarantee | INV-2 for **every** call site, present and future, structurally. |
| Residual race | The fresh read → `_send` window (bounded, not zero, §24 RR-1). |
| Transaction behavior | One short read-only side cursor per call; no commit; no lock held. |
| Multi-store / multi-server | Fresh read sees any server's committed disconnect/epoch. |
| Performance | One lightweight `SELECT` per Shopify call — negligible beside the network round-trip. |
| Verdict | **The decisive enforcement layer.** Adopted; the API client joins the CORE-R2 allowlist. |

---

## 10. Option B/D — coordination & transaction-boundary (revised)

- **Option B (store-scoped barrier / lock):** **[Recommendation]** the credential
  clear is ordered after admitted work by a **bounded poll** for `running`
  business jobs to reach zero (or timeout), **not** by a blocking lock. The
  disconnect never needs a blocking wait on a job row. See §14 for why an
  advisory lock is **not** required.
- **Option D (per-job commit / PERF-1):** **[Recommendation]** complementary,
  not a remediation. **[Inference]** it shrinks the stale-snapshot window but
  cannot stop the currently-running job; INV-2 is delivered by the central gate
  regardless of the commit model. CORE-R2 must be **compatible** with the future
  PERF-1 `_commit_progress` per-job commit and must not pre-decide Q7
  (checkpoint/resume ownership).

---

## 11. Recommended architecture (proposal)

**[Recommendation]** **Option E (revised hybrid):**

1. **Store state** `disconnecting` (between `connected` and `disconnected`);
   `activate`/`reconnect` clear it and bump the epoch.
2. **Store fields:** `connection_generation` (Integer, monotonic);
   `disconnect_status` (Selection: `none`/`requested`/`quiescing`/`completed`/
   `timed_out`); `disconnect_status_reason` (Char); `disconnect_stuck_job_id`
   (**Integer**, plain — see §16); `disconnect_requested_at`/`_by`;
   `disconnect_completed_at`. All non-secret, all written on the **store row**.
3. **Job field:** `expected_connection_generation` (Integer, persisted at
   enqueue).
4. **Central API gate** (§9) — the INV-2 enforcement point; the API client joins
   the CORE-R2 allowlist.
5. **Dedicated, high-priority, trigger-driven quiesce controller** (§13) — its
   own `ir.cron`, servicing all `disconnecting` stores; not a drained business
   job (so it cannot starve).
6. **Two-phase disconnect:** Phase 1 (RPC, atomic) sets `disconnecting` + bumps
   epoch + `disconnect_status='requested'` + one non-blocking cancellation sweep
   + `controller_cron._trigger()`; Phases 2–3 run in the controller.
7. **Coordination = store-row optimistic state+generation under `retrying()`**
   (§14); **advisory lock dropped** from the recommended path.

---

## 12. Rejected alternatives

**[Recommendation]** (logged to the rejected-approaches log only after ChatGPT
review):

- **R-1 voluntary per-handler checkpoint as the primary control** — too easy to
  omit (review point 3); replaced by central enforcement.
- **R-2 force `FOR UPDATE`-cancel the running job** — orders after the handler,
  reproduces the serialization failure, and can corrupt an admitted call's local
  state.
- **R-3 global disconnect lock** — violates INV-5/INV-8.
- **R-4 session-scoped advisory lock** — **[Fact-Source]** not released on
  rollback (SRR-09 leak).
- **R-5 explicit `cr.commit()` inside `action_disconnect`** — breaks `retrying()`
  (INV-7).
- **R-6 per-job commit alone (Option D)** — cannot stop the running job; PERF-1.
- **R-7 `disconnect_generation` re-read from current state only** — a rapid
  reconnect makes an old job see `connected` again; replaced by the **persisted
  expected epoch** (§8).
- **R-8 a `core_disconnect_quiesce` *drained business job* as the controller** —
  starves behind the `id asc` business backlog, and a self-rescheduling handler
  is wrongly marked `succeeded` by `_invoke_handler` (review point 4); replaced
  by the dedicated cron (§13).
- **R-9 `running`-only finalize poll as the safety mechanism** — a
  claimed-but-not-started (C) row can later become `running`; safety is provided
  by the epoch gate, not the poll (review point 1).
- **R-10 unbounded `pg_advisory_xact_lock`** — blocks without a stated bound
  (review point 6); see §14.

---

## 13. Quiesce controller — scheduling & starvation prevention (corrects review point 4)

**[Recommendation]** Mechanism = **Option A: a dedicated, high-priority
scheduled action** (its own `ir.cron`, `core`-owned), servicing every store in
`disconnecting`. Rationale and exact state machine:

- **Why it cannot starve behind an `id asc` backlog:** it is **not** claimed
  through `_claim_for_dispatch`; it is a **separate cron** with its own worker
  slot. **[Fact-Source]** cron selection orders by `failure_count, priority, id`
  (`ir_cron.py:303`) and a dedicated cron with `priority=0` runs independently of
  the business drain. The business backlog cannot consume its slot.
- **Prompt response without a busy loop:** **[Fact-Source]** `ir.cron._trigger(at)`
  (`ir_cron.py:735`) schedules a run "soon" (or at given times, precision ~1 min)
  by inserting an `ir_cron_trigger` row — no polling spin. Phase 1 calls
  `controller._trigger()`; each controller pass that is **not yet done** calls
  `_trigger(now + POLL_DELAY)` to schedule the next pass, then returns. This is
  event/trigger-driven, not a `while` loop.
- **One controller per store/generation:** the **store row itself** is the
  controller state — a store is in `disconnecting` at exactly one
  `connection_generation`. There is no per-store controller record to duplicate;
  the cron simply `search([('state','=','disconnecting')])` each pass. Idempotent
  by construction (re-scanning a `disconnected` store does nothing).
- **Exact state transition per pass (no "reschedule self ASAP" hand-wave):** each
  pass, for each `disconnecting` store, in its **own** short transaction:
  1. run one **non-blocking** cancellation sweep (A/B rows; SKIP LOCKED);
  2. count `running` business jobs (C/D/E/F that reached `running`);
  3. **if** count == 0 → **finalize** (Phase 3): clear credential, `state =
     'disconnected'`, `disconnect_status='completed'`, `disconnect_completed_at`,
     write the lifecycle audit job; **stop** (no re-trigger);
  4. **elif** within `DISCONNECT_QUIESCE_TIMEOUT` → set
     `disconnect_status='quiescing'`, `_trigger(now + POLL_DELAY)`, return;
  5. **else** (timeout) → **finalize with escalation** (§16), `_trigger` **not**
     re-armed.
  The controller **never writes a running/claimed job row** (steps 3/5 write
  only the store row + a **new** audit job). Because it is a cron method (not a
  dispatched job), there is no `_invoke_handler` to mark it `succeeded` — the
  "reschedule-self-marked-succeeded" defect (R-8) cannot occur.
- **Maximum polling cadence:** bounded by `POLL_DELAY` (a named constant; the
  trigger precision floor is ~1 min per `_trigger`), so at most one pass per
  `POLL_DELAY`; never a spin.
- **Crash/restart recovery:** the controller holds **no in-memory state** — on
  restart the cron re-scans `disconnecting` stores and resumes. A store stuck in
  `disconnecting` after a crash is re-serviced on the next cron wake (the
  standard cron `nextcall` also covers it even if the trigger row was lost).

---

## 14. Coordination primitive — bounded decision (corrects review point 6)

**[Recommendation]** Re-evaluated whether an advisory lock is needed. **It is
not**, and is **dropped** from the recommended design.

- **What actually closes the call race (INV-2):** the **central API gate +
  persisted epoch** (§8/§9) — **not** any lock. The review's caution is
  decisive: "since drains do not take this lock, it serializes lifecycle
  commands only and does not itself close the call race." An advisory lock would
  therefore be theatre for the invariant that matters.
- **What lifecycle-command serialization needs:** only that two concurrent
  lifecycle commands on the **same store** (disconnect vs reconnect vs a second
  disconnect) don't interleave incoherently. **[Fact-Source]** any two writers
  to the same store row serialize at PostgreSQL's row-lock level; under
  REPEATABLE READ the loser gets `serialization_failure` and **[Fact-Source]**
  Odoo's `retrying()` (`odoo/service/model.py:160`) re-runs the whole RPC (5
  tries). So **store-row optimistic state+generation under `retrying()`** is a
  bounded, sufficient serializer: each lifecycle command re-reads state/epoch on
  retry and behaves idempotently (a second disconnect on an already-
  `disconnecting`/`disconnected` store is an audited no-op).
- **Comparison (simplest that proves the invariant):**

| Candidate | Bounded? | Closes call race? | Serializes lifecycle? | Verdict |
| --- | --- | --- | --- | --- |
| **Store-row optimistic state+generation + `retrying()`** | Yes (single-row UPDATE; 5 retries) | No (the gate does) | Yes | **Recommended** |
| `pg_try_advisory_xact_lock` loop / `lock_timeout` | Yes (non-blocking try + bounded retry) | No | Yes | Rejected-unless-needed (adds a primitive for no extra guarantee) |
| `pg_advisory_xact_lock` (blocking) | **No** (unbounded) | No | Yes | **Rejected** (review point 6) |
| unique controller-per-store row | Yes | No | Yes (via unique key) | Unnecessary — the store row already is the controller (§13) |

- **If a future need ever justifies an explicit lock,** the packet pins the
  bounded contract: `pg_try_advisory_xact_lock(CONNECTOR_NS, store_id)` (a
  reserved two-int namespaced key to avoid collisions), acquired **only** by
  lifecycle commands (never by drains), with bounded retry/backoff and a fixed
  acquisition ceiling; on failure the command returns "busy, retry" rather than
  blocking; released at transaction end; **explicitly documented as serializing
  lifecycle commands only, not closing the call race.** This is the *rejected-
  unless-needed* fallback, not the recommended path.

---

## 15. Credential lifecycle

**[Recommendation]** Cleared **only** at finalize (Phase 3), via the existing
Task 002 `action_clear_token` (no second path), after the bounded `running→0`
wait or timeout. Never in Phase 1. **[Inference]** clearing the credential row
does **not** abort an already-issued in-flight HTTP request (the handler already
read the token via `_get_access_token` before `_send`), so an admitted call
(Phase B/E) is not corrupted by a slightly-early clear; the bounded wait is a
courtesy to let local reconciliation finish, and the timeout path clears
regardless. Credential history preserved (DEC-022).

---

## 16. Job lifecycle & timeout escalation without touching a locked job (corrects review point 5)

**[Recommendation]**
- **A/B (unlocked queued/retry) →** `cancelled` in the non-blocking sweep.
- **C (claimed-but-not-started) →** skipped by the sweep; converges to `skipped`
  (gate) or `cancelled` (later pass) — never force-written while locked.
- **D (running, pre-call) →** `skipped` at the gate.
- **E/F (running, admitted call) →** natural terminal after local reconciliation.
- **Timeout with a still-`running` job →** the controller **must not** write the
  running job row, its job-log, or set `blocked_manual_review` on it (any of
  which can block behind the drain's `FOR UPDATE` and defeat the bounded
  timeout). Instead it records escalation on the **store row** — an
  independently-writable surface:
  - `disconnect_status = 'timed_out'`, `disconnect_status_reason` (Char),
  - `disconnect_stuck_job_id` = the stuck job's id **as a plain Integer**
    (**not** a Many2one — **[Fact-Source]** a Many2one write would take a FK
    `KEY SHARE` lock on the referenced job row, which conflicts with the drain's
    `FOR UPDATE` and could block; a plain Integer write to the store row takes no
    lock on the job row),
  - plus a **new** `core_manual_maintenance` audit job (a fresh row, safe to
    write).
- The timeout path stays **bounded**, clears the credential under the accepted
  contract, **exposes the stuck job id safely**, **preserves the original
  running row unchanged** (it is still locked; its handler will resolve it —
  succeeded or gate-skipped), and **permits later reconciliation** when that
  transaction returns. `blocked_manual_review` is **not** overloaded for an
  infrastructure interruption.
- No job is ever deleted (DEC-022).

---

## 17. External-side-effect boundary

**[Recommendation]** The enforcement boundary is the **central API client**
(§9). The optional handler convenience helper (`store._connection_epoch_ok(job)`
early-exit) is a UX affordance only; the client gate is the guarantee. See the
Phase A/B/C contract (§6): fail-closed before a call; complete local
reconciliation for an admitted call; re-gate before the next call.

---

## 18. Failure / retry behavior

**[Recommendation]**
- `ShopifyQuiescedError` = cooperative abort → `skipped`; never an error class,
  never retried, never a handler failure.
- The disconnect path generates **no** `serialization_failure` against a running
  job (Phase 1 does no blocking job-row write; the sweep uses SKIP LOCKED) —
  T-8 asserts this as a regression vs E-R6-5/6.
- **[Fact-Source]** `retrying()` classifies `LockNotAvailable /
  SerializationFailure / DeadlockDetected`; the design avoids generating these
  on the disconnect path and adds no `NOWAIT`/raw `FOR UPDATE` on the job row.

---

## 19. Multi-worker and multi-server behavior

**[Recommendation] / [Fact-Source]** All state (store state/epoch/status fields,
job expected epoch) lives in PostgreSQL → correct across `--workers` and across
Odoo servers on one DB (INV-6). Every drain, on any server, is gated by the same
central client reading the same committed epoch. The controller cron may run on
any server and converges via the store row. **[Open]** true multi-host proof
remains SRR-09 residual; the packet mandates a two-server (Topology C) test and
names multi-host as follow-up.

---

## 20. Performance implications

**[Recommendation] / [Inference]** One lightweight fresh-cursor `SELECT` per
Shopify call (negligible beside the network round-trip); one fast Phase-1 write
+ a trigger; a dedicated controller cron that runs only while some store is
`disconnecting`. No global serialization (INV-5). No added savepoints or
per-record locks → compatible with SRR-01 and the PERF-1 `_commit_progress`
model; batch size unchanged.

---

## 21. UI implications

**[Recommendation]** (UI built by the U-track, not here.) The operator surface is
driven by `state` + `disconnect_status`: `requested`/`quiescing` → "Disconnecting
— stopping in-flight sync…"; `completed` → "Disconnected"; `timed_out` →
"Disconnected, but a job did not stop in time (job #N) — review". The Disconnect
button returns immediately on Phase-1 acceptance; the store shows live status;
the final audit reports accurate counts. **The UI must not present Phase-1 return
as completed disconnection** (review point 2).

---

## 22. Migration / backward compatibility

**[Recommendation]** Additive: new `disconnecting` state value; new store fields
(default `connection_generation=0`, `disconnect_status='none'`, nulls); new
`job.expected_connection_generation` (default `0` — pre-existing rows read as
epoch 0, matching a never-cycled store); a dedicated controller `ir.cron`; the
central gate in the existing `execute()`. One new exception class. No existing
job state/error-class/`job_source` changes. LC-1 compatibility: register the new
state/fields/cron with/before LC-1 so they participate in that lifecycle from day
one. **Rollback:** revert the CORE-R2 PR — additive schema, no data destroyed;
stores fall back to the merged `connected → disconnected` path.

---

## 23. Required tests (executable; corrects review point 9)

**[Recommendation]** The enforcement point is the **real production `execute()`
gate**; tests exercise it through the existing `_send` transport-injection seam
(fake transport, **no live Shopify**). **No monkeypatch of the lifecycle/state
mechanism; no test-only timing hook.** Genuine concurrency uses independent
processes + `pg_stat_activity` evidence (PR #153 method) and a two-`odoo-bin`
instance for the cross-server case.

- **T-1 stale epoch blocks before `_send`:** a business job whose
  `expected_connection_generation` no longer matches the store → `execute()`
  raises before `_send` is reached; job → `skipped`; assert `_send` not called.
- **T-2 `disconnecting` blocks before `_send`.**
- **T-3 reconnect with a new epoch does not revive an old job:** disconnect→
  reconnect (epoch +2); the old queued job stays blocked at the gate.
- **T-4 diagnostic path intact:** `action_test_connection` (lifecycle context)
  still calls `_send` while state ≠ `connected`.
- **T-5 admitted-first-call reconciliation:** first `execute()` admitted (fake
  transport returns data); disconnect requested; handler completes its local
  reconciliation (Phase B) and is not rolled back.
- **T-6 second call blocked:** after disconnect, the same handler's next
  `execute()` is blocked (Phase C).
- **T-7 claimed-but-not-started later starts but cannot call Shopify:** genuine
  race — a drain holds a C row; disconnect commits; the drain `_start_running`s
  it, but `execute()` fail-closes → `skipped`, `_send` not called.
- **T-8 no serialization failure:** the disconnect path produces no
  `serialization_failure` against the running/claimed job (regression vs
  E-R6-5/6).
- **T-9 controller cannot starve:** a large `id asc` business backlog present;
  the dedicated controller still finalizes the disconnect (separate cron slot).
- **T-10 timeout completes without writing the locked running job:** a handler
  that holds its row past `DISCONNECT_QUIESCE_TIMEOUT`; finalize sets store-level
  `timed_out` + `disconnect_stuck_job_id` (Integer) + a new audit job, clears the
  credential, and **does not** write the locked job row/log.
- **T-11 two-server (Topology C):** disconnect on server 1 while server 2 drains;
  INV-2/INV-3 cross-server.
- **T-12 multi-store isolation:** disconnect X does not block a drain for Y.
- **T-13 idempotent re-disconnect; T-14 reconnect after `disconnecting`.**
- **Odoo.sh runtime green** for the full `shopify_connector_core` suite (SRR-06).

---

## 24. Residual risks

**[Recommendation] / [Open]**
- **RR-1 (gate→`_send` window):** the fresh read cannot be atomic with the HTTP
  call; a disconnect committing in that sub-millisecond window is not caught for
  that one call. Bounded (the read is the last step before `_send`), not zero.
- **RR-2 (already-issued call):** cannot be un-done; idempotency net.
- **RR-3 (timeout):** a hung handler is escalated on the store surface, not
  stopped; credential cleared regardless (deliberate INV-4 trade).
- **RR-4 (multi-host):** two-server test is single-host; multi-node = SRR-09
  residual.
- **RR-5 (context-stripping):** a future handler could deliberately strip the
  dispatcher-set business context to dodge the gate; a **source-level test**
  asserts the dispatcher sets it and that `execute()` fail-closes without it —
  making this conscious sabotage, not accidental omission.
- **RR-6 (SRR-06 class):** concurrency/timing fix — untrusted until live Odoo.sh
  proof.

---

## 25. Open questions

**[Open]**
- **Q-QS-1:** cooperative-cancel before next call (recommended) vs let-complete.
- **Q-QS-2:** `POLL_DELAY` / `DISCONNECT_QUIESCE_TIMEOUT` defaults (trigger floor
  ~1 min) — tuning constants.
- **Q-QS-3:** exact `disconnect_status` vocabulary and whether a dedicated alert
  model is in scope (recommend store-level fields only for MVP).
- **Q-QS-4:** one-way `disconnecting` vs operator-cancelable (recommend one-way).
- **Q-QS-5:** business-call context carrier — `shopify_business_job_id` in
  `env.context` (recommended) vs an explicit `execute(..., job=job)` parameter;
  and how strictly `execute()` fail-closes when neither marker is present.
- **Q-QS-6:** seam vs Q7/PERF-1 ownership (no per-job-commit pre-decision).
- **Q-QS-7:** whether `action_reconnect`/`action_activate` bump the epoch on
  *every* success or only when identity changed (recommend every success — the
  simplest safe rule).

---

## 26. ChatGPT decisions required

**[Open]**
1. **D-CR2-A:** target contract (§4, request vs completion) + invariants (§5).
2. **D-CR2-B:** recommended architecture = revised Option E (§11), or a named
   alternative (§12).
3. **D-CR2-C:** **enforcement at the central API client** (§9) and **dropping the
   advisory lock** in favour of store-row optimistic state+epoch (§14).
4. **D-CR2-D:** the **connection-epoch model** (§8), new store/job fields, state,
   controller cron, and the business-call context carrier (Q-QS-5).
5. **D-CR2-E:** **critical-path placement** — CORE-R2 runtime-green before
   enabling/live-validating **any** Shopify-calling handler incl. reads
   (010B/011B/012 live validation, 013–015, UAT), development in parallel
   allowed (see master plan §2.1 and packet §Critical path).
6. **D-CR2-F:** confirm **SRR-03 OPEN**, **SRR-04/09 REDUCED (not closed)**, and
   that accepting this analysis opens **no** gate — only a later explicit CORE-R2
   gate act on the packet does.

> **Nothing above is accepted.** The CORE-R2 code gate remains **closed** until
> ChatGPT issues an explicit gate act on the implementation packet.
