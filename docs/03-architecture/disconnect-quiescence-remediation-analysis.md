# Disconnect Quiescence & In-Flight Job Contract — Remediation Analysis (CORE-R2)

> **Status: Proposed for ChatGPT review. NOTHING here is accepted, decided,
> or an opened gate.** Design-only. No addon/code/test/XML/migration change
> accompanies this document. Authorized by the CORE-R2 design gate (PR #153
> comment `4950413650`, docs-only). Base after normal-merge of the current
> integration tip: `Shopify-connector` @
> `65e915aada32930a19a14c94d23dc9bd5e6fb517` (PR #152/U0 merged; U0 artifacts
> preserved).
>
> **Revision 3 (2026-07-12) — control-room review `4951237871`.** Rev 2's
> quiescence signal was **broken**: `run_drain` sets `running` and executes the
> handler and commits in **one** transaction, so `running` is **not committed
> while the handler runs** — a separate controller sees the stale committed
> `queued`/`retry_waiting`, the SKIP-LOCKED sweep skips the locked row, and
> `count(state='running')` returns zero. Rev 3 replaces that signal with an
> **independently-committed admission-lease** mechanism and freezes the nine
> load-bearing items: (1) transaction-visibility model; (2) atomic
> admission + single token snapshot; (3) a bounded **set** of admitted calls;
> (4) an exact one-store-per-cron-transaction controller; (5) an explicit
> `execute_business`/`execute_lifecycle` contract + full call-site inventory;
> (6) the complete lifecycle state matrix; (7) lease-based timeout/escalation;
> (8) an ordered rollback; (9) base re-aligned by normal merge.
>
> **Claim discipline (CLAUDE.md §8):** **[Fact-Runtime]** = merged PR #153
> evidence; **[Fact-Source]** = Odoo 19 / PostgreSQL 16 source or official docs
> (citation inline); **[Inference]**; **[Recommendation]** (subject to review);
> **[Open]**. No **[Recommendation]** is a Decision. SRR-03 stays **OPEN**.

---

## 1. Executive conclusion

**[Fact-Runtime]** PR #153 proved with the real `store.action_disconnect()`
that a concurrent disconnect does not stop an in-flight business handler
(DEF-PB-1 / SRR-03).

**[Inference]** The correct fix has two independent halves:
1. **Admission enforcement (INV-2):** every Shopify call is admitted only
   through an explicit **`execute_business(job, …)`** entry point on the central
   API client, fail-closed against a **persisted connection epoch**
   (`store.connection_generation` vs the job's captured
   `expected_connection_generation`), read in a **fresh cursor**.
2. **Quiescence detection (INV-3):** because job `running` state is invisible
   across transactions (§3), the controller cannot use it. Admitted work is made
   visible by a **committed admission-lease record** written on a **side cursor**
   *before* each call and cleared *after* local reconciliation, with expiry-based
   crash recovery. The disconnect controller finalizes (clears the credential,
   sets `disconnected`) only when the store has **zero live leases**, or on a
   bounded timeout with lease-based escalation.

**[Recommendation]** Adopt this as CORE-R2. It requires a small central-model
change set plus **minimal, named call-site threading** in the two existing
domain importers (§9). The **advisory lock stays dropped**; the lease record is
the load-bearing, observable, crash-safe coordination surface. **This document
opens no gate.**

---

## 2. Accepted runtime evidence

**[Fact-Runtime]** from merged PR #153 (final decision `4950408383`).

| ID | Observation |
| --- | --- |
| E-R6-1 | Worker A held the claimed job's row lock at `running` across a pause. |
| E-R6-2 | Worker B called the real merged `action_disconnect()` (no substitute/monkeypatch). |
| E-R6-3 | Worker B **blocked** on the running job's row (pg `Lock`/`transactionid`, FK `KEY SHARE`). |
| E-R6-4 | A's checkpoint-3 read `store.state = connected` (disconnect blocked/uncommitted, snapshot-invisible). Handler ran; job succeeded; A committed. |
| E-R6-5/6 | On unblock, B serialization-failed (library, rolled back) / was retried (RPC) and cancelled **zero** jobs. |
| E-S8 | Two-instance (Topology C, single host) drain of 40 jobs: disjoint claims, no double-processing, no deadlock. |

---

## 3. Transaction-visibility model (corrected — review point 1)

**[Fact-Source]** The single most important correction. In the merged code:

- `run_drain` → `_claim_for_dispatch` (`FOR UPDATE SKIP LOCKED` row lock,
  `odoo/orm/models.py:5592`) → `_start_running` (`write→running`) →
  `_invoke_handler` (the handler, which for a domain job calls Shopify) → job
  terminal — **all inside one drain transaction**, with the **single commit at
  the cron boundary** (`ir_cron.py:691`). There is **no commit** between
  `running` and the handler's Shopify call.

**[Inference]** Therefore, explicitly:

- **`_start_running`, handler execution, local reconciliation, and the terminal
  transition all occur inside the same drain transaction.**
- **Another connection cannot rely on seeing `state='running'` before that drain
  commits.** Until the drain commits, other transactions see the row's last
  *committed* value.
- **A row locked by the drain may still appear committed as `queued` or
  `retry_waiting` to another connection while its handler is actively calling
  Shopify.** (It was locked at `queued`/`retry_waiting`; `running` is
  uncommitted.)
- **A separate controller therefore MUST NOT use `job.state='running'` as its
  authoritative in-flight-work signal.**

**Consequently the following rev-2 claims are removed as false:**

- ~~running-count polling proves admitted work has drained~~ — it cannot; the
  count reads stale committed state and returns zero mid-handler.
- ~~committed job state can identify every active handler~~ — it cannot; an
  active handler's row is committed as `queued`/`retry_waiting`.
- ~~`disconnect_stuck_job_id` can be derived from running rows alone~~ — it
  cannot; the in-flight job is invisible in committed state.

**In-flight taxonomy (unchanged rows A–G), re-stated against this model:**
A queued/unlocked and B retry_waiting/unlocked → cancellable by the non-blocking
sweep. **C claimed-and-row-locked (committed as `queued`/`retry_waiting`, handler
may be running uncommitted)** → invisible as `running`; the SKIP-LOCKED sweep
skips it; it is made visible and safe only by its **admission lease** (§10). D/E/F
running (pre-call / call-issued / reconciling) → the lease represents them; the
central gate blocks any *new* call. G terminal → ignored. **The lease, not job
state, is the cross-transaction signal for C–F.**

---

## 4. Desired operator contract (request vs completion; bounded admitted set)

**[Recommendation]**

- **Phase-1 RPC return means ONLY:** *request accepted; the store is
  `disconnecting`.* Not credential-cleared, not quiesced, not complete.
- **Immediately guaranteed on Phase-1 commit:** the epoch is bumped, so **no new
  business Shopify call can be admitted** (the gate refuses any call whose job
  epoch no longer matches), and no business job can start.
- **A bounded set of pre-intent admitted calls may still be in flight** across
  workers/servers — each admitted before the epoch bump was visible to it. The
  contract is store-wide: **at most one currently-admitted call per handler; a
  bounded set across all handlers/workers.** These complete; the controller waits
  for their leases to release.
- **Disconnect is *completed* only when:** `state=='disconnected'`, credential
  cleared, final audit written, epoch bumped, and **the store has zero live
  leases** (or timeout, §16).
- **Cannot be undone:** any call already admitted before the epoch bump; the
  idempotency substrate is the net.

---

## 5. Required safety invariants

**[Recommendation]**
- **INV-1:** once `disconnecting` commits, no business job starts *and admits a
  call* for the store.
- **INV-2 (load-bearing):** a business Shopify call is admitted only via
  `execute_business`, only when a fresh-cursor read shows `state=='connected'`
  AND `store.connection_generation == job.expected_connection_generation`.
- **INV-3 (load-bearing):** the credential is cleared / store finalized only when
  there are **zero live admission leases** for the store, or on a **bounded
  timeout** with honest escalation.
- **INV-4:** disconnect completes in bounded time (timeout ⇒ finalize).
- **INV-5:** store-local; only same-store operations coordinate.
- **INV-6:** holds across `--workers` and multiple servers on one DB (all
  coordination state is committed in PostgreSQL).
- **INV-7:** no `cr.commit()` on the **request/main cursor**; independently
  committed state uses an owned **side cursor** (the sanctioned Odoo pattern).
- **INV-8:** no unbounded blocking, no global serialization, no new deadlock, no
  reliance on cross-transaction `running` visibility.
- **INV-9:** auditable; idempotent; escalation and lease writes never touch a
  drain-locked job row.

---

## 6. Side-effect phase contract (A/B/C)

**[Recommendation]**
- **Phase A — before a call:** `execute_business` admits (fresh epoch gate +
  lease commit). If the gate fails → `ShopifyQuiescedError` → job `skipped`; **no
  call, no lease.**
- **Phase B — call admitted/issued:** cannot be undone; the handler **completes
  its local Odoo reconciliation** (write the binding/result). Do **not** roll it
  back because disconnect arrived after admission. The lease is released **after**
  reconciliation.
- **Phase C — before another call:** re-admit via `execute_business`; fail-closed
  if quiescing/stale. At most the one currently-admitted call per handler; zero
  further calls after the gate observes the disconnect.

---

## 7. Connection-epoch (Option A component)

**[Recommendation]** `store.connection_generation` (Integer, monotonic) +
persisted `job.expected_connection_generation` (captured at enqueue). Necessary
intent+epoch carrier; enforced at the central gate (§9). Insufficient alone
(needs the gate + the lease). See §8 for the full matrix of when it bumps.

---

## 8. Lifecycle state matrix (frozen — review point 6 / §8 of the prompt)

**[Recommendation]** `state` adds `disconnecting`. `connection_generation` bumps
on every lifecycle transition that changes connection identity/validity.
**Disconnect is one-way once accepted (Q-QS-4 resolved: one-way).** **Generation
bumps on every successful activation/reconnect (Q-QS-7 resolved: every
success — the simplest safe rule; identity-change-only is rejected as fragile).**

| Trigger / current state | Behavior (frozen) | Generation |
| --- | --- | --- |
| Disconnect while `connected` | → `disconnecting`, Phase 1 (bump epoch, sweep A/B, `_trigger` controller) | +1 |
| Disconnect while `disconnecting` | audited no-op (already in progress) | no change |
| Disconnect while `disconnected` | audited no-op | no change |
| Test Connection while `disconnecting` | **refused** — `execute_lifecycle(purpose='test_connection')` is not permitted in `disconnecting` (matrix §9); returns a UserError-style "disconnect in progress" | no change |
| Credential replacement while `disconnecting` | **refused** until finalize (disconnect is one-way; replace after it completes) | no change |
| Reconnect while `disconnecting` | **refused** until finalize; then Reconnect from `disconnected` | no change |
| Activation while `disconnecting` | **refused** | no change |
| Reconnect after completed `disconnected` | allowed → runs test/readiness substrate → `connected`/`reconnect_needed` | +1 on success |
| Credential replacement while `connected` | allowed (existing) | +1 |
| Activation success | → `connected` | +1 |

**[Inference]** Refusing lifecycle mutations *during* `disconnecting` keeps the
state machine linear and makes the epoch monotonic, so an old job can never see a
matching epoch after a cycle. T-13 (idempotent re-disconnect) and T-14 (reconnect
after completed disconnect) now map to exact rows above.

---

## 9. Central enforcement, atomic admission & the business/lifecycle contract (review points 2, 3, 5)

### 9.1 Explicit two-entry contract (freezes Q-QS-5)

**[Recommendation]** The load-bearing carrier is an **explicit argument**, not
`env.context`:

- **`execute_business(job, store, query, variables=None)`** — the **only** entry
  for domain-handler Shopify calls. `job` is **mandatory and positional**; the
  epoch and identity come from it and **cannot be lost** through recordset/env
  reconstruction. Performs Phase-A admission (§9.2).
- **`execute_lifecycle(store, query, variables=None, purpose=...)`** — the
  **only** entry for setup/diagnostic calls. `purpose` is a fixed enum, each with
  an **allowed state matrix** (not a generic bypass):

  | purpose | allowed store states |
  | --- | --- |
  | `test_connection` | `setup_incomplete`, `connected`, `reconnect_needed` |
  | `readiness_probe` | `setup_incomplete`, `connected`, `reconnect_needed` |
  | `reconnect_probe` | `reconnect_needed`, `disconnected` |

  A lifecycle call outside its matrix fails closed. **No `disconnecting` lifecycle
  call is permitted** (see §8).
- The current public `execute()` is **removed / made private** so a future domain
  handler **cannot** reach `_send` outside the two guarded entries. An
  unidentified/unsupported call **fails closed**.

### 9.2 Atomic admission + single token snapshot (review point 2)

**[Fact-Source]** Today `execute()` reads the token, and `_send()` reads it
**again** — two lookups. **[Recommendation]** Fix the admission to be a single
linearized step:

1. Open an owned **side cursor** (`registry.cursor()`), fresh snapshot.
2. Read `store.state` + `store.connection_generation` and (for business) compare
   to `job.expected_connection_generation`. On mismatch → close side cursor →
   raise `ShopifyQuiescedError` (no lease, no call).
3. Read the access token **once** into memory (via the sanctioned
   `_get_access_token`), and **INSERT + COMMIT** an admission-lease row (§10) — in
   the **same side transaction**. **The lease commit is the admission
   linearization point.**
4. Close the side cursor. Call **`_send(store, body, token)`** — passing the
   **one** in-memory token snapshot; **no second credential lookup**.
5. On completion (Phase B done), **release the lease** (side cursor: DELETE +
   COMMIT). On exception, release in a `finally`; a crash leaves the lease to
   expire (§10).

- **Disconnect committing after step 2's snapshot but before step 3's commit** →
  a *pre-intent admitted* lease (bounded window = snapshot age); the controller
  sees the committed lease and **waits** for it (INV-3). Disconnect committing
  before step 2's snapshot → the gate sees it → refused.
- **The credential row cannot be cleared out from under an admitted call:** INV-3
  gates credential-clear on zero live leases, and even on the timeout path the
  already-captured in-memory token completes the in-flight HTTP (clearing the row
  does not invalidate sent bytes).
- **Token is memory-only, never persisted** (never in the lease, never logged;
  redacted in any error). The packet authorizes the **minimal `_send` signature
  change** to accept the pre-read token (removing the second lookup) — this
  supersedes rev 2's "no `_send` change" restriction where it prevented a safe
  single snapshot.

### 9.3 Exhaustive current call-site inventory (review point 5)

**[Fact-Source]** Every production caller of the API client today
(`grep '.execute(' addons/**/*.py`, excluding tests):

| # | File:line | Kind | Migration |
| --- | --- | --- | --- |
| 1 | `shopify_connector_core/models/shopify_connector_store.py:121` (`action_test_connection`) | lifecycle | → `execute_lifecycle(store, query, purpose='test_connection')` |
| 2 | `shopify_connector_product/models/shopify_connector_product_importer.py:213` (`import_product_sync` ← handler `_handle_product_import_sync(job)`) | **business** | → `execute_business(job, store, query, variables=…)`; **thread `job`** from the handler through `import_product_sync` (job identity is currently dropped) |
| 3 | `shopify_connector_sale/models/shopify_connector_customer_importer.py:113` (customer importer ← its dispatch handler) | **business** | → `execute_business(job, store, query, …)`; **thread `job`** likewise |

**[Inference]** Sites 2 and 3 live in **domain modules** (`shopify_connector_product`,
`shopify_connector_sale`). Making INV-2 real therefore requires **minimal,
named call-site changes in those two files** — threading the already-in-scope
`job` to the guarded entry. The CORE-R2 future allowlist (packet §4) names exactly
these two files as **call-site-only** changes; everything else in them stays
forbidden. This cross-module touch is *why* CORE-R2 must land before those
handlers are live-validated (§ critical path). Alternatives that avoid editing
them (context-carrier, wrapper) are rejected (review point 5: identity must not be
lost through env reconstruction, and a generic bypass is forbidden).

---

## 10. SELECTED quiescence mechanism — committed admission-lease record (review points 1, 3, 7)

**[Recommendation]** One exact mechanism, independently visible and crash-safe,
supporting multiple simultaneous holders per store.

**Options compared:**

| Option | Linearization | Protected lifetime | DB-conn cost | Multi-worker/server | Crash | Timeout | Deadlock/starvation | Observability | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A. shared/exclusive `pg_advisory_xact_lock` on a side cursor** | lock grant | side-txn open for whole call | **1 connection held open per in-flight call** | correct (DB-wide) | auto-release on txn end (elegant) | controller bounded exclusive try-lock | after epoch bump no new shared holders → exclusive succeeds (no starvation) | **none** (no count/ids/timestamps) | **Rejected** — no escalation observability; holds a connection for the whole call |
| **B. committed admission-lease record (side cursor)** | lease **commit** | insert→(call+reconcile)→delete | 2 short side-txns/call (cheaper) | correct (committed rows) | expiry + controller reaper | controller reads live-lease count | after epoch bump no new leases → count →0 | **full** (count, opaque ids, `admitted_at`, `expires_at`) | **SELECTED** |
| C. store-level counter/lease | increment | decrement after call | cheap | needs exact decrement | **cannot recover** (crashed worker leaves counter skewed; no ids) | ambiguous | — | none | **Rejected** (review's own caveat) |

**Selected = Option B.** Precise design:

- **New concrete model `shopify.connector.call.lease`** (core-owned; needs one ACL
  row). Fields (all non-secret): `store_id` (M2o **to the store**, never to the
  job — so no FK `KEY SHARE` lock on a drain-locked job row), `lease_key` (Char,
  opaque UUID), `job_id` (**plain Integer**, for diagnostics only — not an FK),
  `worker_ref` (Char: server/pid/db tag), `admitted_at` (Datetime),
  `expires_at` (Datetime = `admitted_at` + `MAX_CALL_LIFETIME`). **No token, ever.**
- **Admission** (§9.2 step 3): INSERT + COMMIT on a side cursor **before** `_send`.
- **Release:** DELETE + COMMIT on a side cursor **after** local reconciliation.
- **Multiple holders:** many lease rows per store → the bounded set of admitted
  calls; one currently-admitted call per handler.
- **Crash recovery:** `MAX_CALL_LIFETIME` must exceed the client's
  connect+read timeout (`_CONNECT_TIMEOUT_SECONDS`+`_READ_TIMEOUT_SECONDS` = 30s)
  plus a reconciliation budget, so a live call is never falsely reaped. The
  controller **reaps** (deletes) leases past `expires_at`, logging the reap.
- **Controller quiescence check:** `count(live leases for store where now <
  expires_at) == 0` → all admitted work drained → finalize; `> 0` → wait; expired
  → reap (crash recovery). This is the committed, cross-transaction signal that
  `running` state cannot provide.

---

## 11. Recommended architecture (proposal)

**[Recommendation]**
1. Store state `disconnecting`; fields `connection_generation`, `disconnect_status`
   (`none/requested/quiescing/completed/timed_out`), `disconnect_status_reason`,
   `disconnect_requested_at/by`, `disconnect_completed_at`,
   `disconnect_open_lease_count` + `disconnect_oldest_admitted_at` (escalation
   snapshot, written by the controller).
2. Job field `expected_connection_generation` (persisted at enqueue).
3. New `shopify.connector.call.lease` model (§10) + its ACL row.
4. Central API client: `execute_business`/`execute_lifecycle`; `execute()` removed
   from the public surface; `_send(store, body, token)`.
5. Two domain-importer call sites threaded to `execute_business(job, …)`.
6. Two-phase disconnect; **one-store-per-invocation controller cron** (§14).
7. Coordination = the committed lease (§10) + store-row epoch under `retrying()`;
   **advisory lock stays dropped**.

---

## 12. Rejected alternatives

**[Recommendation]** (logged after review): R-1 voluntary handler checkpoint;
R-2 force-`FOR UPDATE`-cancel; R-3 global lock; R-4 session advisory lock; R-5
in-method main-cursor `cr.commit()`; R-6 per-job-commit alone (PERF-1); R-7
current-state-only epoch (revived by fast reconnect); R-8 drained-job controller
(starves; marked `succeeded`); **R-9 `running`-count quiescence signal (invisible
across transactions — §3);** **R-10 shared/exclusive advisory lock as the
quiescence signal (no escalation observability; holds a connection per call);**
**R-11 `env.context` business-call carrier (identity lost on env reconstruction);
R-12 store-counter lease (no crash recovery).**

---

## 13. State-transition proposal

**[Recommendation]** `setup_incomplete → connected → disconnecting → disconnected`;
`disconnected → connected|reconnect_needed` (reconnect); auth-failure →
`reconnect_needed` (unchanged). `disconnecting` is **non-startable** and
**non-enqueueable** for business jobs and **refuses lifecycle mutations** (§8).
Full matrix frozen in §8.

---

## 14. Controller transaction & scheduling model (review point 4)

**[Recommendation]** **Exact shape = one store per cron invocation/transaction.**

- The controller `ir.cron` fires and processes **exactly one** `disconnecting`
  store per invocation, in that invocation's single transaction — so there is
  **one transaction per processed store with no explicit `cr.commit()`**.
- **Non-blocking selection:** `store = Store.search([('state','=','disconnecting')],
  order='disconnect_requested_at, id', limit=1).try_lock_for_update()` — the
  store-row `FOR UPDATE SKIP LOCKED` ensures **only one controller invocation
  processes a given store**; a concurrent invocation skips it and selects the
  next (or none → no-op). This is the duplicate-finalization guard.
- **Per-pass state machine:** reap expired leases; non-blocking sweep of A/B jobs;
  read live-lease count; write `disconnect_open_lease_count` +
  `disconnect_oldest_admitted_at`; **if 0** → finalize (clear credential,
  `disconnected`, `completed`, audit); **elif within `DISCONNECT_QUIESCE_TIMEOUT`**
  → `quiescing`; **else** → timeout-finalize (§16). Then, if any `disconnecting`
  store remains, `_trigger()` again.
- **Trigger dedup:** duplicate triggers are harmless — each invocation re-selects a
  store under SKIP LOCKED; extra triggers are no-op wakeups. **[Fact-Source]**
  `ir_cron._trigger` (`ir_cron.py:735`) inserts `ir_cron_trigger` rows consumed on
  the next wake.
- **Crash/restart recovery:** the store stays `disconnecting` (durable); the
  cron's regular `nextcall` interval re-fires even if trigger rows were lost;
  leases expire independently.

**Honest scheduler wording (review point 4):** **[Fact-Source]** a separate
`ir.cron` record with `priority=0` gives **prioritization** in the cron
selection order (`ORDER BY failure_count, priority, id`, `ir_cron.py:303`), **not
a dedicated worker slot**. Absolute wall-clock completion is **not** guaranteed
when the cron service itself has no free worker. What **is** immediate is the
**epoch/admission safety guarantee** the moment Phase-1 commits — a stale-epoch
call is refused by the gate regardless of controller latency. **Completion**
(credential clear, `disconnected`) has an **operational SLA under a healthy cron
scheduler**, exposed honestly via `disconnect_status` + `disconnect_requested_at`
(a monitor can see a controller that has not progressed). The absolute "cannot
starve / completes in bounded time" claim from rev 2 is **removed**; INV-4's
"bounded" is the timeout-to-finalize once the controller *runs*, not a wall-clock
guarantee that it runs.

---

## 15. Credential lifecycle

**[Recommendation]** Cleared only at finalize (Phase 3), via the existing
`action_clear_token`, when live-lease count is zero **or** on timeout. Never in
Phase 1. **[Inference]** an admitted call holds its own in-memory token snapshot
(§9.2), so a finalize clear never empties an in-flight request's token. History
preserved (DEC-022).

---

## 16. Timeout & escalation via leases (review point 7)

**[Recommendation]** Timeout uses the **lease surface**, never committed
`job.state`. On `DISCONNECT_QUIESCE_TIMEOUT` with live leases remaining:

- Finalize to `disconnected` + `disconnect_status='timed_out'`, clear credential
  (**Option A of the prompt §10**): the bounded set of already-admitted holders
  may **finish** their in-flight calls using their **already-captured in-memory
  token**; their leases are reaped on `expires_at`. Bounded completion (INV-4).
- Record on the **store row** (independently writable; never a job row):
  `disconnect_status_reason`, `disconnect_open_lease_count`,
  `disconnect_oldest_admitted_at`, and the **opaque `lease_key`s / plain-Integer
  `job_id`s** of outstanding holders (safe identifiers) + a new
  `core_manual_maintenance` audit job.
- **Operator contract & security trade-off (stated exactly):** after a timeout,
  the operator sees `disconnected`/`timed_out`, but a **bounded set of pre-timeout
  admitted Shopify calls may still complete** against Shopify shortly after, using
  tokens already in memory. Alternative B (stay `disconnecting` until holders
  release) is **rejected** because a hung holder would make disconnect unbounded
  (violates INV-4). **No token/secret is ever stored** in the lease or escalation
  fields.
- Zero / one / many holders are all representable (`disconnect_open_lease_count`).

---

## 17. External-side-effect boundary

**[Recommendation]** `execute_business` is the single guarded boundary (§9); the
lease is created there and released after Phase-B reconciliation. Handlers never
call `_send` directly (it is private) and never see the token.

---

## 18. Failure / retry behavior

**[Recommendation]** `ShopifyQuiescedError` → `skipped`, never an error class,
never retried. The disconnect path (Phase 1 + sweep + controller) issues **no**
blocking write to a running/claimed job row → no `serialization_failure` against
it (T-8). `retrying()` remains the RPC serializer for lifecycle-command writes.

---

## 19. Multi-worker and multi-server behavior

**[Recommendation] / [Fact-Source]** Epoch, leases, and store fields are committed
in PostgreSQL → correct across `--workers` and servers on one DB (INV-6). Multiple
workers may each hold one admitted lease for a store (bounded set); the controller
(on any server) reads the committed lease count. **[Open]** true multi-host proof
is SRR-09 residual; the packet mandates a two-server (Topology C) test.

---

## 20. Performance implications

**[Recommendation] / [Inference]** Per Shopify call: one fresh-cursor gate read +
one lease insert/commit + one lease delete/commit = **two short side
transactions** (cheaper than holding a connection open, as an advisory lock
would). Negligible beside the network round-trip. **Connection-pool
consideration:** each admitted call briefly uses a side connection; at high
concurrency the pool must accommodate the drain workers plus brief side cursors —
noted as a tuning input (not a correctness issue), compatible with PERF-1.

---

## 21. UI implications

**[Recommendation]** (U-track owns UI; U0 artifacts merged, untouched here.)
Operator surface = `state` + `disconnect_status`; show `requested`/`quiescing`
("stopping in-flight sync — N calls outstanding" from
`disconnect_open_lease_count`), `completed`, or `timed_out` (with the outstanding
count + oldest-admitted age). Phase-1 return shows "disconnecting", never
"disconnected".

---

## 22. Migration / backward compatibility

**[Recommendation]** Additive schema: `disconnecting` state value; new store/job
fields; the new `call.lease` model + ACL; the controller cron; the two guarded
entry points; `_send` gains a token param; two domain call sites rethreaded.
Pre-existing rows: `connection_generation=0`, `expected_connection_generation=0`
(match a never-cycled store). Land with/before **LC-1**. See §23 for the **ordered
rollback** (a plain revert is unsafe because a persisted `disconnecting` value has
no home in the old `state` selection).

---

## 23. Ordered rollback contract (review point 8)

**[Recommendation]** Replaces the simple-revert claim. Required ordered
procedure:

1. **Disable/stop** the quiesce-controller `ir.cron` (deactivate the record).
2. **Prevent new `disconnecting` transitions** (disable the new
   `action_disconnect` path / feature guard) so the set is frozen.
3. **Normalize every store** in `disconnecting`/`timed_out` to a state supported
   by the old code: those with a cleared credential → `disconnected`; those still
   credentialed and not yet finalized → back to `connected` (or `reconnect_needed`
   per evidence). No store may retain an unsupported `state` value.
4. **Resolve/expire active leases:** delete all `shopify.connector.call.lease`
   rows (in-flight calls will have completed or will fail closed on their own).
5. **Preserve/archive** lifecycle audit jobs (normal job rows; kept — DEC-022).
6. **Revert** code/data declarations (state value, fields, cron record, lease
   model, guarded entries, `_send` param, the two domain call-site edits).
7. **Verify** no unsupported `state` value remains, no active controller trigger
   (`ir_cron_trigger`) references the removed cron, and no orphan lease rows.

Record whether the added columns/lease table are **retained inertly** (safer;
recommended) or dropped by a **later** migration. A revert must not run before
steps 1–5.

---

## 24. Required tests (executable; review point 9 / prompt §12)

**[Recommendation]** Prove the **real mechanism** (leases + guarded entry),
through the real production admission boundary, with the existing `_send`
transport-injection seam (fake transport, **no live Shopify, no monkeypatch of
lifecycle/state, no timing hook**). Genuine concurrency = independent processes +
`pg_stat_activity`; two `odoo-bin` for cross-server.

- **T-1** disconnect commits **before** admission → `execute_business` gate fails
  → **no `_send`**, no lease.
- **T-2** admission commits **before** disconnect → the request may finish; its
  lease blocks finalize until released.
- **T-3** **two or more** handlers admitted concurrently on **one** store →
  controller does not finalize until **every** lease releases (or timeout rule).
- **T-4** claimed-but-not-started (C) row cannot admit (no lease) and later starts
  but `execute_business` fail-closes → `skipped`, no `_send`.
- **T-5** one admitted call finishes local reconciliation; a **second** call from
  the same handler is blocked (Phase C).
- **T-6** token read **once**; no second credential lookup after admission
  (assert `_get_access_token` call count / that a mid-call credential clear does
  not empty the admitted request's token).
- **T-7** worker-crash: a lease past `expires_at` is reaped by the controller;
  finalize proceeds; crash does not wedge the store.
- **T-8** disconnect path produces **no** `serialization_failure` against the
  running/claimed job.
- **T-9** multi-store isolation (disconnect X ≠ block drain Y).
- **T-10** two-server (Topology C) INV-2/INV-3.
- **T-11** **one-store-per-controller-transaction**: two concurrent controller
  invocations do not both finalize the same store (store-row SKIP LOCKED).
- **T-12** duplicate controller trigger is idempotent (no double finalize).
- **T-13/T-14** lifecycle-matrix cases (idempotent re-disconnect; reconnect after
  completed disconnect; refused lifecycle during `disconnecting`).
- **T-15** cron-delay/operator-health: with the controller delayed, the **epoch
  gate still blocks** new calls (safety immediate), and `disconnect_status`
  reflects `quiescing`.
- **T-16** ordered-rollback preconditions where testable (no store left in
  `disconnecting`; no orphan leases).
- **Odoo.sh runtime green** for the full `shopify_connector_core` suite (SRR-06).

---

## 25. Residual risks

**[Recommendation] / [Open]**
- **RR-1 (admission window):** a disconnect committing between the gate snapshot
  and the lease commit yields a pre-intent admitted lease (bounded by snapshot
  age); the controller waits for it — correct, not a leak.
- **RR-2 (already-admitted call):** cannot be un-done; idempotency net.
- **RR-3 (timeout):** the bounded pre-timeout admitted set may complete after the
  operator sees `disconnected` (security trade-off, §16, stated).
- **RR-4 (multi-host):** two-server test is single-host; multi-node = SRR-09.
- **RR-5 (connection pressure):** side-cursor leases add brief connections; a tuning
  input, not correctness.
- **RR-6 (SRR-06):** concurrency/timing fix — untrusted until live Odoo.sh proof.

---

## 26. Open questions (non-load-bearing tuning only) & ChatGPT decisions

**[Open — tuning only]** `MAX_CALL_LIFETIME`, `DISCONNECT_QUIESCE_TIMEOUT`,
`POLL_DELAY` default values; the exact `worker_ref` composition; whether the
escalation snapshot also mirrors into a dedicated alert model later. **No
load-bearing mechanism remains open** (admission, quiescence, token snapshot,
call identity, lifecycle matrix, controller transaction, timeout, rollback are all
frozen above).

**[Open — ChatGPT decisions]**
1. **D-CR2-A** contract (§4) + invariants (§5).
2. **D-CR2-B** recommended architecture (§11) or a named alternative (§12).
3. **D-CR2-C** the **committed admission-lease** mechanism (§10) and keeping the
   advisory lock dropped.
4. **D-CR2-D** the explicit **`execute_business`/`execute_lifecycle`** contract,
   the `_send` token-snapshot change, and the **two domain call-site edits** in
   the future allowlist (§9).
5. **D-CR2-E** critical-path placement (before any Shopify-calling handler,
   incl. reads).
6. **D-CR2-F** confirm **SRR-03 OPEN**, **SRR-04/09 REDUCED**, and that no gate is
   opened by accepting this analysis.

> **Nothing above is accepted.** The CORE-R2 code gate remains **closed** until
> ChatGPT issues an explicit gate act on the packet.
