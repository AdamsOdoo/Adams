# Disconnect Quiescence & In-Flight Job Contract — Remediation Analysis (CORE-R2)

> **Status: Proposed for ChatGPT review. NOTHING here is accepted, decided,
> or an opened gate.** Design-only. No addon/code/test/XML/migration change
> accompanies this document. Authorized by the CORE-R2 design gate (PR #153
> comment `4950413650`, docs-only). Base after normal-merge of the current
> integration tip: `Shopify-connector` @
> `cfdb05703a65f82b34a9a11364aab6fc960cca9d` (control-room base-sync
> amendment; supersedes `65e915a`; PR #152/U0 and PR #155/U0-closure merged;
> U0 artifacts preserved).
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
> **Revision 4 (2026-07-12) — control-room review `4680299311`.** Rev 3 froze
> the *right mechanism* (a committed lease) but was **not yet
> implementation-safe**. Rev 4 closes six blocking corrections: **(1)** admission
> is made **atomic with disconnect/finalization** by one exact PostgreSQL
> **store-row lock protocol** — admission holds a shared `FOR SHARE` row lock while
> it reads state/generation, reads the token, and commits the lease; every
> generation-changing lifecycle transition takes the conflicting update lock
> (`FOR NO KEY UPDATE`/`FOR UPDATE`) — so a stale gate read can **never** commit a
> lease after finalization, while concurrent admissions still proceed (§9.2);
> **(2)** `execute_business` is frozen as a **context manager** whose protected
> lifetime wraps the HTTP request **and** its local Odoo reconciliation, so the
> lease cannot end before reconciliation and there is no manual release (§9.1);
> **(3)** the expired-lease rule is **direction C** — an expired-but-unreleased
> lease is treated as **unknown/live**, never reaped into a normal `completed`
> finalize; `completed` requires **zero** lease rows, a crashed worker resolves via
> the **`timed_out`** path, and `timed_out` stays **distinct** from `completed`
> (§10/§16); **(4)** the controller selection is corrected to a real ordered
> `FOR UPDATE SKIP LOCKED LIMIT 1` that **can pick the next unlocked store**, with a
> bounded **`POLL_DELAY`** cadence via a **delayed** `_trigger(at=…)` (no busy loop)
> (§14); **(5)** the **ordered rollback** refuses to remove code/model while any
> admitted holder is still live — workers are drained and **zero holders** verified
> first (§23); **(6)** the CORE-R2 architecture-review row is renumbered
> **AR-045 → AR-047** (AR-044 = U0, AR-045 = Task 011B/PR #150, AR-046 =
> Task 010B/PR #151, AR-047 = CORE-R2/PR #154).
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
1. **Admission enforcement (INV-2), serialized by a store-row lock:** every
   Shopify call is admitted only through an explicit **`execute_business(job, …)`**
   context manager on the central API client, fail-closed against a **persisted
   connection epoch** (`store.connection_generation` vs the job's captured
   `expected_connection_generation`). The gate read, the token read, and the lease
   commit all happen **under a shared `FOR SHARE` lock on the store row** held for
   one side transaction; every generation-changing lifecycle transition
   (disconnect, credential replacement, activation, reconnect) takes the
   **conflicting** update lock on that same row. The lock — not the bare lease
   commit — is the linearization primitive (§9.2), so a stale gate read can never
   commit a lease after finalization, while concurrent admissions (shared holders)
   still proceed.
2. **Quiescence detection (INV-3):** because job `running` state is invisible
   across transactions (§3), the controller cannot use it. Admitted work is made
   visible by a **committed admission-lease record** written on the same locked
   side transaction *before* each call and cleared *after* local reconciliation.
   The disconnect controller finalizes as **`completed`** (clears the credential,
   sets `disconnected`) only when the store has **zero lease rows**; an
   expired-but-unreleased lease is treated as **unknown/live** and is **never**
   reaped into `completed` (direction C, §10). A crashed holder resolves through
   the bounded **`timed_out`** path, which stays **distinct** from `completed`.

**[Recommendation]** Adopt this as CORE-R2. It requires a small central-model
change set plus **named, structural call-site changes** in the two existing
domain importers — each wraps its call **and** the reconciliation that follows in
a `with execute_business(job, …)` block (§9.1/§9.3), not a one-line swap. The
**advisory lock stays dropped**; coordination is a **native store-row lock**
(shared for admission, exclusive for lifecycle) plus the **committed lease** —
together the load-bearing, observable, crash-safe surface. **This document opens
no gate.**

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
  cleared, final audit written, epoch bumped, and **the store has zero lease rows**
  (expired rows still block `completed` — direction C); otherwise it ends as
  **`timed_out`** (§16).
- **Cannot be undone:** any call already admitted before the epoch bump; the
  idempotency substrate is the net.

---

## 5. Required safety invariants

**[Recommendation]**
- **INV-1:** once `disconnecting` commits, no business job starts *and admits a
  call* for the store.
- **INV-2 (load-bearing):** a business Shopify call is admitted only via
  `execute_business`, only when — **while holding a `FOR SHARE` lock on the store
  row** — a fresh read shows `state=='connected'` AND
  `store.connection_generation == job.expected_connection_generation`; the lease
  is committed under that same lock (§9.2).
- **INV-2L (lock protocol, load-bearing):** admission takes a **shared** store-row
  lock (`FOR SHARE`); every generation-changing lifecycle transition (disconnect,
  credential replacement, activation, reconnect) and every finalize takes a
  **conflicting** store-row update lock (`FOR NO KEY UPDATE`/`FOR UPDATE`). Shared
  holders do not conflict with each other (concurrent admissions proceed) but do
  conflict with the update lock, so admission and lifecycle **linearize** on that
  row. Any writer that also touches the credential row locks **store first, then
  credential** — a single global order → deadlock-free (§9.2).
- **INV-3 (load-bearing):** the credential is cleared / store finalized as
  `completed` only when the store has **zero lease rows**. An
  **expired-but-unreleased** lease is treated as **unknown/live** and is **never**
  counted as drained (direction C, §10); a crashed holder is resolved by the
  **bounded timeout** to `timed_out` (distinct from `completed`), never by reaping
  a live lease into `completed`.
- **INV-4:** disconnect completes in bounded time (timeout ⇒ `timed_out`
  finalize).
- **INV-5:** store-local; only same-store operations coordinate.
- **INV-6:** holds across `--workers` and multiple servers on one DB (all
  coordination state — the store-row lock, the epoch, and the leases — is committed
  in PostgreSQL).
- **INV-7:** no `cr.commit()` on the **request/main cursor**; independently
  committed state uses an owned **side cursor** (the sanctioned Odoo pattern).
- **INV-8:** no unbounded blocking (the shared lock is held only for the
  no-network admission bookkeeping, released before `_send`), no global
  serialization, no new deadlock, no reliance on cross-transaction `running`
  visibility.
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
**Every row below that changes `state` or `connection_generation` executes under
the store-row update lock of §9.2** (`FOR NO KEY UPDATE`/`FOR UPDATE`), which
conflicts with admission's `FOR SHARE` — so admission and *any* generation-changing
transition linearize on the store row. This is the single serialization primitive
shared by admission, disconnect, credential replacement, activation, and reconnect.

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

### 9.1 Explicit two-entry contract, business entry is a context manager (freezes Q-QS-5; review point 2)

**[Recommendation]** The load-bearing carrier is an **explicit argument**, not
`env.context`; and the business entry is a **structurally enforced context
manager**, not a value-returning call:

- **`execute_business(job, store, query, variables=None)`** — the **only** entry
  for domain-handler Shopify calls, used **exclusively** as a context manager:

  ```python
  with api_client.execute_business(job, store, query, variables) as result:
      payload = normalize(result)
      return apply_import(store, payload)   # local Odoo reconciliation
  ```

  `job` is **mandatory and positional**; the epoch and identity come from it and
  **cannot be lost** through recordset/env reconstruction.
  - **`__enter__`** performs the **atomic admission** of §9.2 (store-row `FOR
    SHARE` lock → fresh gate read → single token read → lease `INSERT`+`COMMIT` →
    lock released) **and then** issues the HTTP request via
    `_send(store, body, token)`, yielding the transport `result`. If the gate
    fails, `__enter__` raises `ShopifyQuiescedError` **before** any lease or call.
  - **the `with` body** performs normalization **and** the local reconciliation
    (`apply_import`) — the reconciliation the current importers do *after* the
    call. The lease is **still held** throughout the body.
  - **`__exit__`** releases the lease (side-cursor `DELETE`+`COMMIT`) on **both**
    normal and exception exit — there is **no manual release** to forget.
  - A **process crash** inside the body runs no `__exit__`, so the **committed
    lease persists** for the direction-C timeout path (§10/§16).
  - The caller **cannot obtain a normal `result` without entering the protected
    lifetime** (the value is yielded by `__enter__`), so the lease provably
    outlives reconciliation. **Every additional Shopify call requires a new
    `with` block** = a new admission + new lease (Phase C).

  Implementation shape (design intent): a `@contextlib.contextmanager` generator
  — `token = self._admit(job, store)` (§9.2, may raise `ShopifyQuiescedError`);
  `try: result = self._send(store, body, token); yield result` `finally:
  self._release_lease(lease_key)`. `_admit` and `_release_lease` each own a short
  side transaction; `_send` runs **after** the admission side-txn has committed and
  released the row lock (the lock never spans the network call).
- **`execute_lifecycle(store, query, variables=None, purpose=...)`** — the
  **only** entry for setup/diagnostic calls. It is an **ordinary method** (no
  lease, no context manager): a lifecycle *call* is a diagnostic, not a
  generation-changing transition. It is guarded by the `purpose`→state matrix
  below; the generation-changing write that may *follow* a successful probe
  (activation / reconnect success) is what takes the store-row **update** lock and
  bumps the epoch (§8, §9.2). `purpose` is a fixed enum, each with an **allowed
  state matrix** (not a generic bypass):

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

### 9.2 Atomic admission via a store-row lock + single token snapshot (review points 1, 2)

**[Fact-Source]** Rev 3 claimed "the lease commit is the admission linearization
point." **That is false**, exactly as the review shows: a side transaction that
reads `connected`/gen N, then `INSERT`s + `COMMIT`s a lease **without locking the
store row**, can interleave as — admission reads `connected`/gen N; disconnect
commits `disconnecting`/gen N+1; the controller sees **zero** committed leases and
finalizes (clears the credential); *then* the stale admission commits its lease
and `_send`s with the captured token → a **post-disconnect admission** (violates
INV-1/2/3). **The bare lease commit is not atomic with disconnect.** The fix adds
one exact serialization primitive.

**[Fact-Source] PostgreSQL row-lock conflict matrix** (the load-bearing fact):
`FOR SHARE` **does not** conflict with another `FOR SHARE`, but **does** conflict
with `FOR NO KEY UPDATE` and `FOR UPDATE`; a plain `UPDATE` of a non-key column
acquires `FOR NO KEY UPDATE`. Odoo's `lock_for_update` issues `FOR UPDATE SKIP
LOCKED`, and `lock_for_update(allow_referencing=True)` issues `FOR NO KEY UPDATE
SKIP LOCKED` (`odoo/orm/models.py:5564`–5589); there is no built-in **shared**
helper, so admission takes `FOR SHARE` with one raw statement on its side cursor.

**[Recommendation] Admission side transaction (`_admit`, shared lock):**

1. Open an owned **side cursor** (`registry.cursor()`), fresh snapshot.
2. **`SELECT id FROM shopify_connector_store WHERE id = %s FOR SHARE`** on the
   side cursor — a **shared** row lock. It coexists with other admissions'
   `FOR SHARE` (concurrent admissions proceed) but **blocks, and is blocked by**,
   any lifecycle update lock on that row.
3. **Under that held lock**, read `store.state` + `store.connection_generation`
   and (for business) compare to `job.expected_connection_generation`. On mismatch
   (`state != 'connected'` or epoch differs) → `ROLLBACK` (releases the lock) →
   close side cursor → raise `ShopifyQuiescedError` (**no lease, no call**).
4. Still under the lock, read the access token **once** into memory (via the
   sanctioned `_get_access_token`) and **`INSERT`** the admission-lease row (§10).
5. **`COMMIT`** the side transaction. The commit **atomically** persists the lease
   **and** releases the `FOR SHARE` lock. Close the side cursor. Return the token.
6. `execute_business.__enter__` then calls **`_send(store, body, token)`** with the
   **one** in-memory snapshot (**no second credential lookup**); the row lock is
   **already released**, so the network call never holds a lock.

**[Recommendation] Lifecycle transition transaction (disconnect / credential
replacement / activation / reconnect — every generation-changing write):**

1. On the request/main cursor under `retrying()`, acquire the **conflicting**
   store-row update lock — the ORM `write({'state': 'disconnecting',
   'connection_generation': N+1})` acquires a **blocking** `FOR NO KEY UPDATE` on
   the row (a plain `UPDATE` waits for conflicting locks; unlike `lock_for_update`
   it does not `SKIP LOCKED`), so it **waits** for any in-flight admission's brief
   `FOR SHARE` to release, then proceeds.
2. Change `state`/`connection_generation` (and, only at finalize, the credential).
3. Commit at the RPC/cron boundary.

**Linearization — the two lock orders (the required proof):**

- **Admission acquires the lock first.** The admission holds `FOR SHARE`; the
  disconnect's `FOR NO KEY UPDATE` **waits**. Admission reads `connected`/gen N
  (still true — the conflicting disconnect cannot have committed), commits the
  lease, releases `FOR SHARE`. **Only now** does disconnect proceed and commit gen
  N+1. Because the lease committed **before** disconnect could commit, the
  controller (which, at selection, holds `FOR UPDATE` on the same row — §14)
  **must** observe the committed lease and **waits** for it. **No stale lease is
  left after finalization.** ✓
- **Disconnect (or the controller's finalize) acquires the lock first.**
  Disconnect holds the update lock; the admission's `FOR SHARE` **blocks** until
  disconnect commits. Admission then reads `disconnecting`/gen N+1, sees the
  mismatch, and **refuses** (no lease, no `_send`). ✓
- **Two concurrent admissions.** Both hold `FOR SHARE`; `FOR SHARE` does not
  conflict with `FOR SHARE`, so both read, both commit their leases, both send —
  **admission concurrency is preserved.** ✓
- **No stale gate read commits a lease after finalization.** The gate read **and**
  the lease insert happen **under the same held `FOR SHARE`**; the finalize's
  update lock cannot be granted while that `FOR SHARE` is held, and the lease is
  committed before the `FOR SHARE` releases. The rev-3 counter-example window is
  therefore closed. ✓
- **Lock ordering with the credential row is exact and deadlock-safe.** Admission
  only **reads** the credential (no row lock) and locks **only** the store row.
  Finalize/credential-replacement lock the **store row first, then the credential
  row** (`store → credential`, one global order). Since no path ever takes them in
  the opposite order and admission never write-locks the credential, **no lock
  cycle exists**; any residual serialization failure is retried by `retrying()`.

**Consequences preserved from rev 3:**

- **The credential row cannot be cleared out from under an admitted call:** INV-3
  gates the `completed` clear on **zero lease rows** under the controller's held
  `FOR UPDATE` (no new admission can slip in), and even on the `timed_out` path the
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
| 1 | `shopify_connector_core/models/shopify_connector_store.py:121` (`action_test_connection`) | lifecycle | → `execute_lifecycle(store, query, purpose='test_connection')` — plain call (no lease); one call site, no surrounding restructure |
| 2 | `shopify_connector_product/models/shopify_connector_product_importer.py:213` (`import_product_sync` ← handler `_handle_product_import_sync(job)`) | **business** | **Structural** (review point 2): thread the already-in-scope `job` into `import_product_sync`, then wrap the existing `execute(...)` **and the normalize/apply reconciliation that currently follows it** in `with execute_business(job, store, query, variables=…) as result:` so the lease spans reconciliation. **Not** a one-line swap — the `with` block encloses the post-call reconciliation lines. |
| 3 | `shopify_connector_sale/models/shopify_connector_customer_importer.py:113` (customer importer ← its dispatch handler) | **business** | Same **structural** `with execute_business(job, …) as result:` wrap around its call **and** its `_apply_import` reconciliation; thread `job` likewise. |

**[Inference]** Sites 2 and 3 live in **domain modules** (`shopify_connector_product`,
`shopify_connector_sale`). Making INV-2 real therefore requires **named,
call-site-scoped structural changes in those two files** — threading the
already-in-scope `job` and re-indenting the existing call-plus-reconciliation
region under a `with execute_business(...)` block so the lease provably outlives
reconciliation (review point 2). The CORE-R2 future allowlist (packet §4) names
exactly these two files as **call-site-only** changes (the one business call site
each, plus the reconciliation region it already owns and the `job` thread-through);
everything else in them stays forbidden. This cross-module touch is *why* CORE-R2
must land before those handlers are live-validated (§ critical path). Alternatives
— a context-carrier, a wrapper, or a value-returning `execute_business` with a
manual release — are rejected (review point 2: the lease must not be releasable
before reconciliation, and identity must not be lost through env reconstruction).

---

## 10. SELECTED quiescence mechanism — committed admission-lease record (review points 1, 3, 7)

**[Recommendation]** One exact mechanism, independently visible and crash-safe,
supporting multiple simultaneous holders per store.

**Options compared:**

| Option | Linearization | Protected lifetime | DB-conn cost | Multi-worker/server | Crash | Timeout | Deadlock/starvation | Observability | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A. shared/exclusive `pg_advisory_xact_lock` on a side cursor** | lock grant | side-txn open for whole call | **1 connection held open per in-flight call** | correct (DB-wide) | auto-release on txn end (elegant) | controller bounded exclusive try-lock | after epoch bump no new shared holders → exclusive succeeds (no starvation) | **none** (no count/ids/timestamps) | **Rejected** — no escalation observability; holds a connection for the whole call |
| **B. committed admission-lease record (side cursor) + store-row lock** | **store-row `FOR SHARE`/update lock** (§9.2), lease commit under it | insert→(call+reconcile)→delete | 2 short side-txns/call (cheaper) | correct (committed rows) | direction C: expired = unknown/live; timeout→`timed_out`, then cleanup (no reap-into-`completed`) | `completed` at 0 rows; else `timed_out` at timeout | after epoch bump no new leases → rows →0 | **full** (count, opaque ids, `admitted_at`, `expires_at`) | **SELECTED** |
| C. store-level counter/lease | increment | decrement after call | cheap | needs exact decrement | **cannot recover** (crashed worker leaves counter skewed; no ids) | ambiguous | — | none | **Rejected** (review's own caveat) |

**Selected = Option B.** Precise design:

- **New concrete model `shopify.connector.call.lease`** (core-owned; needs one ACL
  row). Fields (all non-secret): `store_id` (M2o **to the store**, never to the
  job — so no FK `KEY SHARE` lock on a drain-locked job row), `lease_key` (Char,
  opaque UUID), `job_id` (**plain Integer**, for diagnostics only — not an FK),
  `worker_ref` (Char: server/pid/db tag), `admitted_at` (Datetime),
  `expires_at` (Datetime = `admitted_at` + `MAX_CALL_LIFETIME`). **No token, ever.**
- **Admission** (§9.2): `INSERT` under the held `FOR SHARE` lock, then `COMMIT`
  (which persists the lease **and** releases the lock) on the side cursor
  **before** `_send`.
- **Release:** DELETE + COMMIT on a side cursor **after** local reconciliation, in
  `execute_business.__exit__` (§9.1).
- **Multiple holders:** many lease rows per store → the bounded set of admitted
  calls; one currently-admitted call per handler.
- **Expired-lease rule = direction C (review point 3).** `expires_at` is **not** a
  reap-into-`completed` trigger. A slow-but-live reconciliation can legitimately
  exceed `MAX_CALL_LIFETIME` while still holding its lease; reaping it would let the
  controller observe zero and finalize `completed` while reconciliation is still
  running. Therefore:
  - An **expired-but-unreleased** lease is treated as **unknown/live** — it still
    **counts** and still **blocks** a `completed` finalize.
  - `expires_at`/`MAX_CALL_LIFETIME` are used only as **operator diagnostics**
    (oldest-holder age) and as the **post-`timed_out` cleanup boundary** — never to
    manufacture a normal completion.
- **Crash recovery (direction C):** a crashed holder's committed lease persists and
  keeps the store out of `completed`; it does **not** wedge forever — at
  `DISCONNECT_QUIESCE_TIMEOUT` the controller finalizes the store as **`timed_out`**
  (distinct status, §16) and **then** cleans up the remaining lease rows. Optional
  future hardening (heartbeat, or PID+backend-start liveness) can shorten recovery,
  but is **not required** for safety and is out of MVP scope.
- **Controller quiescence check (direction C):** under the controller's held
  `FOR UPDATE` on the store (§14) — which blocks any new `FOR SHARE` admission —
  `count(all lease rows for store)`: **`== 0`** → **`completed`** finalize
  (every admitted holder actually released); **`> 0` and within timeout** → wait
  (`quiescing`); **`> 0` and past `DISCONNECT_QUIESCE_TIMEOUT`** → **`timed_out`**
  finalize, then clean up the outstanding rows. `completed` therefore provably
  means *all holders released*; `timed_out` provably means *some did not*. This is
  the committed, cross-transaction signal that `running` state cannot provide.

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
4. Central API client: `execute_business` (**context manager**, §9.1) /
   `execute_lifecycle`; `execute()` removed from the public surface;
   `_send(store, body, token)`.
5. Two domain-importer call sites wrapped in `with execute_business(job, …)`
   around call **and** reconciliation (§9.3).
6. Two-phase disconnect; **one-store-per-invocation controller cron** with the
   corrected `try_lock_for_update(limit=1)` selection + `POLL_DELAY` cadence (§14).
7. Coordination = the **store-row lock protocol** (shared `FOR SHARE` for
   admission, `FOR NO KEY UPDATE`/`FOR UPDATE` for lifecycle/finalize, §9.2) + the
   committed lease (§10) + the persisted epoch, all under `retrying()`; **advisory
   lock stays dropped**.

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
R-12 store-counter lease (no crash recovery); R-13 unlocked admission relying on
the bare lease commit as the linearization point (not atomic with disconnect — the
review's post-disconnect-admission counter-example; superseded by the store-row
`FOR SHARE` lock, §9.2); R-14 value-returning `execute_business` with a manual
lease release (release can be forgotten / can precede reconciliation; superseded by
the context manager, §9.1); R-15 expiry-based reaping of live leases into
`completed` (a slow-but-live reconciliation would be mislabelled drained;
superseded by direction C, §10); R-16 `search(limit=1).try_lock_for_update()`
controller selection (returns empty on a locked first row, cannot pick the next;
superseded by `search(...).try_lock_for_update(limit=1)`, §14); R-17 immediate
same-store `_trigger()` re-poll (busy-loop; superseded by delayed
`_trigger(at=now+POLL_DELAY)`, §14); R-18 rollback that deletes active leases then
reverts the model while holders may still return (superseded by the zero-holders
ordered rollback, §23).**

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
- **Corrected selection (review point 4).** Rev 3's
  `search(limit=1).try_lock_for_update()` is **wrong**: **[Fact-Source]** `search`
  narrows to the single first row *before* locking, and `try_lock_for_update`
  (`odoo/orm/models.py:5592`) then applies `FOR UPDATE SKIP LOCKED` to **that one
  id** — if it is locked, it returns an **empty** recordset and does **not** fall
  through to the next store. The corrected selection passes the **full ordered
  set** and lets SKIP LOCKED choose the first *unlocked* row:
  ```python
  stores = Store.search([('state', '=', 'disconnecting')],
                        order='disconnect_requested_at, id')
  store  = stores.try_lock_for_update(limit=1)   # FOR UPDATE SKIP LOCKED LIMIT 1
  ```
  **[Fact-Source]** `try_lock_for_update(limit=1)` builds `self.browse(ids)
  ._as_query(ordered=True)` with `query.limit = 1` and emits `FOR UPDATE SKIP
  LOCKED` (`models.py:5603`–5619), so it returns the **first lockable** store,
  skipping any a concurrent controller already holds. If **all** matching rows are
  locked it returns empty → this pass is a **documented no-op** and a later pass
  handles them. The held `FOR UPDATE` also conflicts with admission's `FOR SHARE`,
  so no new lease can commit for this store while the controller checks and
  finalizes it — this is both the duplicate-finalization guard **and** the
  count-stability guarantee (§9.2).
- **Per-pass state machine (direction C):** non-blocking sweep of A/B queued/
  retry_waiting jobs; `count(all lease rows)` for the store; write
  `disconnect_open_lease_count` + `disconnect_oldest_admitted_at`; **if 0** →
  finalize `completed` (clear credential, `disconnected`, audit); **elif elapsed <
  `DISCONNECT_QUIESCE_TIMEOUT`** → `quiescing` (leave leases untouched — expired
  ones still count, direction C); **else** → `timed_out` finalize **then** clean up
  the remaining rows (§16). No pre-emptive reap of expired leases into the
  `completed` path.
- **Cadence / `POLL_DELAY` (review point 4).** When a store is still `quiescing`,
  the controller **does not** immediately re-`_trigger()` the same store (that
  would busy-loop). **[Fact-Source]** `ir_cron._trigger(at=…)` (`ir_cron.py:735`)
  accepts a datetime to **delay** the next run (precision down to **1 minute**), so
  the controller schedules the next poll via **`self._trigger(at=now + POLL_DELAY)`**
  — one bounded poll per `POLL_DELAY` per still-quiescing store (`POLL_DELAY ≥ 1
  minute`, the trigger's own granularity). A `completed`/`timed_out` finalize needs
  no re-trigger for that store. If **other** `disconnecting` stores remain, a single
  `_trigger()` (or the same delayed trigger) wakes the next pass; each pass handles
  one store, so N stores drain over ≤ N polls plus their own quiesce times — every
  disconnecting store makes progress.
- **Trigger dedup:** duplicate triggers stay harmless — each invocation re-selects
  under SKIP LOCKED and finalize is idempotent; extra `ir_cron_trigger` rows are
  no-op wakeups (`ir_cron.py:735`).
- **Crash/restart recovery:** the store stays `disconnecting` (durable); the cron's
  regular `nextcall` interval re-fires even if trigger rows were lost; the
  direction-C timeout still bounds completion.

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
`action_clear_token`, when the **lease-row count is zero** (`completed`) **or** on
the `timed_out` path — under the controller's held `FOR UPDATE` on the store row so
no admission can slip in during the clear. Never in Phase 1. **[Inference]** an admitted call holds its own in-memory token snapshot
(§9.2), so a finalize clear never empties an in-flight request's token. History
preserved (DEC-022).

---

## 16. Timeout & escalation via leases (review point 7)

**[Recommendation]** Timeout uses the **lease surface**, never committed
`job.state`, and is the **only** path that resolves a lease the holder did not
release (direction C — expiry alone never finalizes `completed`). On
`DISCONNECT_QUIESCE_TIMEOUT` with **any** lease rows remaining (expired or not):

- Finalize to `disconnected` + `disconnect_status='timed_out'` — a status
  **distinct from `completed`** — and clear the credential (**Option A of the
  prompt §10**): the bounded set of already-admitted holders may **finish** their
  in-flight calls using their **already-captured in-memory token**. **Then** clean
  up the outstanding lease rows (the only sanctioned cleanup point, since the store
  is now `timed_out`, not `completed`). Bounded completion (INV-4).
- **`completed` vs `timed_out` are provably different outcomes:** `completed` is
  reached **only** at zero lease rows (every holder released); `timed_out` is
  reached **only** when rows still exist at the deadline (some holder did not
  release — whether slow-but-live or crashed). A slow-but-live reconciliation is
  therefore never mislabelled as a clean drain; a crashed holder cannot wedge the
  store past the timeout.
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

**[Recommendation]** `execute_business` is the single guarded boundary (§9); as a
context manager it creates the lease in `__enter__` and releases it in `__exit__`
**after** the `with` body's Phase-B reconciliation — structurally, with no manual
release. Handlers never call `_send` directly (it is private) and never see the
token.

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

**[Recommendation] / [Inference]** Per Shopify call: one admission side
transaction (a `FOR SHARE` row lock + fresh gate read + token read + lease
insert, then commit) and one release side transaction (lease delete + commit) =
**two short side transactions**. The `FOR SHARE` lock is held only for the
no-network admission bookkeeping and released at the commit **before** `_send`, so
no connection or row lock spans the network round-trip (cheaper than an advisory
lock, which would hold a connection for the whole call). Negligible beside the
round-trip. **Connection-pool
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

**[Recommendation]** Replaces both the simple-revert claim and rev 3's
"delete active leases then revert" order — which the review correctly rejects: a
lease may still have a **live holder** that will return, reconcile, and try to
release it, and a `timed_out` holder may still `_send` with an **in-memory token**.
Code/model removal must therefore come **last**, only after **zero holders** is
proven. Required ordered procedure (no step may be skipped or reordered):

1. **Disable new disconnect transitions** — feature-guard `action_disconnect` so no
   new store enters `disconnecting`; the in-flight set is now frozen.
2. **Disable new business admissions** — make `execute_business.__enter__`
   fail-closed (feature flag), so no new lease is created and no new `_send` starts.
3. **Stop or drain the relevant workers** — stop the drain/controller crons and let
   every currently-admitted handler run to completion (its `__exit__` releases its
   lease), **or wait** until every admitted holder exits. Any `timed_out` holder
   still finishing with an in-memory token is included in this wait — do **not**
   proceed while such a holder can still `_send`.
4. **Verify zero active/unreleased holders** — assert `count(shopify.connector.call
   .lease) == 0` **and** no worker is inside an `execute_business` context. This is
   the gate for everything below; if it is not zero, return to step 3.
5. **Normalize store states** — move every `disconnecting`/`timed_out` store to a
   state the old code supports (cleared credential → `disconnected`; still
   credentialed and not finalized → `connected`/`reconnect_needed` per evidence). No
   store may retain an unsupported `state` value.
6. **Preserve audit evidence** — keep/archive the lifecycle audit jobs (normal job
   rows — DEC-022); do not delete escalation history.
7. **Only now remove/deactivate code and data** — the controller `ir.cron`, the
   `shopify.connector.call.lease` model, the guarded entry points, the `_send`
   token param, and the two domain call-site edits. Because step 4 proved zero
   holders, no live handler can reference the removed model or entry points.

Record whether the added columns/lease table are **retained inertly** (safer;
recommended) or dropped by a **later** migration. **Removal (step 7) must never run
before zero-holders is verified (step 4).** Post-conditions to check: no unsupported
`state` value, no `ir_cron_trigger` row references the removed cron, no lease row or
in-context holder remains.

---

## 24. Required tests (executable; review point 9 / prompt §12)

**[Recommendation]** Prove the **real mechanism** (the store-row lock + leases +
guarded context-manager entry) through the real production admission boundary. The
fourteen required proofs (prompt §9) map one-to-one:

- **T-1 (req 1) admission lock wins first:** an admission holds `FOR SHARE` and
  commits its lease **before** a concurrent disconnect's update lock is granted →
  the controller (holding `FOR UPDATE` at selection) observes the committed lease
  and **waits** (no `completed`).
- **T-2 (req 2) disconnect lock wins first:** disconnect commits
  `disconnecting`/gen N+1 while the admission's `FOR SHARE` blocks → the admission
  then reads the new state/generation and **refuses** → **no `_send`**, no lease.
- **T-3 (req 3) no finalize between gate read and lease commit:** with the
  admission holding `FOR SHARE` mid-bookkeeping, a controller pass **cannot** take
  `FOR UPDATE` and finalize the store until the admission commits + releases →
  proves the counter-example window is closed.
- **T-4 (req 4) ≥ 2 concurrent admissions:** two handlers on **one** store both
  acquire `FOR SHARE`, both commit leases, both `_send` (shared lock does not
  self-conflict); the controller finalizes only after **both** release.
- **T-5 (req 5) lease live through real reconciliation:** inside a real
  `with execute_business(...) as result:` block, the lease row **exists**
  throughout `normalize` + `apply_import`; a controller pass during the body does
  **not** reach `completed`.
- **T-6 (req 6) context exit releases:** normal `with`-block exit deletes the lease
  (row count returns to zero); the next controller pass finalizes `completed`.
- **T-7 (req 7) context exception releases:** an exception raised inside the body
  still runs `__exit__` → the lease is released (no leak), the handler still errors.
- **T-8 (req 8) slow-but-live not falsely reaped:** a lease held past
  `MAX_CALL_LIFETIME` while reconciliation is still running **still blocks**
  `completed` (direction C) — the controller reports `quiescing`, never a clean
  drain.
- **T-9 (req 9) worker crash → `timed_out`:** a committed lease whose holder never
  returns keeps the store out of `completed`; at `DISCONNECT_QUIESCE_TIMEOUT` the
  store finalizes **`timed_out`** and the orphan row is cleaned up **afterwards** —
  the crash does not wedge the store forever and does not fake a completion.
- **T-10 (req 10) `completed` ⇒ all released:** a `completed` finalize is reachable
  **only** at zero lease rows (assert no `completed` occurs while any row exists).
- **T-11 (req 11) `timed_out` ≠ `completed`:** the two terminal statuses are
  distinct and set by disjoint conditions (zero-rows vs rows-at-deadline).
- **T-12 (req 12) POLL_DELAY, no busy-loop:** a still-quiescing store schedules its
  next poll via `_trigger(at=now+POLL_DELAY)` (assert the scheduled
  `ir_cron_trigger` time ≥ now+POLL_DELAY, and **no** immediate same-store
  re-trigger) — bounded cadence, no spin.
- **T-13 (req 13) locked first store doesn't block later ones:** with store A's row
  locked by a stalled controller, `try_lock_for_update(limit=1)` selects store B
  → B makes progress; A is handled on a later pass.
- **T-14 (req 14) ordered rollback refuses with active holders:** the rollback
  precondition check (step 4) **fails/blocks** while any lease row or in-context
  holder exists, and only proceeds to code/model removal at zero holders.

Additional (retained) coverage:

- **T-15** token read **once**; no second credential lookup after admission
  (assert `_get_access_token` call count; a mid-call credential clear does not empty
  the admitted request's captured token).
- **T-16** claimed-but-not-started (row C) cannot admit (no lease) and, when it
  later starts, `execute_business` fail-closes → `skipped`, no `_send`.
- **T-17** disconnect path produces **no** `serialization_failure` against the
  running/claimed job.
- **T-18** multi-store isolation (disconnect X ≠ block drain Y).
- **T-19** two-server (Topology C) INV-2/INV-3/INV-2L via two `odoo-bin` on one DB.
- **T-20** one-store-per-controller-transaction + duplicate-trigger idempotency.
- **T-21** lifecycle-matrix cases (idempotent re-disconnect; reconnect after
  completed disconnect; refused lifecycle during `disconnecting`).
- **T-22** cron-delay/operator-health: with the controller delayed, the **epoch
  gate still blocks** new calls (safety immediate), `disconnect_status` = `quiescing`.
- **Odoo.sh runtime green** for the full `shopify_connector_core` suite (SRR-06).

**Method (unchanged constraints):** exercise the **real production
`execute_business` boundary and the `_send` transport-injection seam** — fake
transport, **no live Shopify, no test-only timing hook, no lifecycle/state
monkeypatch**. Genuine concurrency = independent processes + `pg_stat_activity` to
observe the `FOR SHARE`/`FOR NO KEY UPDATE` waits; two `odoo-bin` for cross-server.

---

## 25. Residual risks

**[Recommendation] / [Open]**
- **RR-1 (admission window) — CLOSED by the lock:** rev 3's gate-snapshot→lease
  window no longer exists. The gate read and the lease commit are **atomic under
  the held `FOR SHARE`** (§9.2); a disconnect either commits before the admission's
  lock (admission then refuses) or after the admission released (its lease already
  committed and the controller waits). No pre-intent-after-finalize lease is
  possible. Retained only as a note that the primitive is a **native row lock**,
  not an advisory lock.
- **RR-2 (already-admitted call):** cannot be un-done; idempotency net.
- **RR-3 (timeout):** the bounded pre-timeout admitted set may complete after the
  operator sees `disconnected`/`timed_out` (security trade-off, §16, stated).
- **RR-4 (multi-host):** two-server test is single-host; multi-node = SRR-09.
- **RR-5 (connection pressure):** side-cursor admissions add brief connections that
  now also briefly hold a `FOR SHARE` row lock (no network held under it); a tuning
  input, not correctness.
- **RR-6 (crashed-holder latency):** under direction C a crashed holder blocks
  `completed` until `DISCONNECT_QUIESCE_TIMEOUT` (then `timed_out`); shortening that
  via heartbeat/backend-liveness is optional future hardening, not required for
  safety.
- **RR-7 (SRR-06):** concurrency/timing fix — untrusted until live Odoo.sh proof.

---

## 26. Open questions (non-load-bearing tuning only) & ChatGPT decisions

**[Open — tuning only]** `MAX_CALL_LIFETIME`, `DISCONNECT_QUIESCE_TIMEOUT`,
`POLL_DELAY` default values (`POLL_DELAY ≥ 1 minute`, the `_trigger` granularity);
the exact `worker_ref` composition; whether a heartbeat/backend-liveness hardening
is added later (direction C is safe without it); whether the escalation snapshot
also mirrors into a dedicated alert model later. **No load-bearing mechanism
remains open** (the store-row lock protocol, admission atomicity, the
context-managed reconciliation lifetime, direction-C expiry handling, quiescence,
token snapshot, call identity, lifecycle matrix, controller selection/cadence,
timeout, and ordered rollback are all frozen above).

**[Open — ChatGPT decisions]**
1. **D-CR2-A** contract (§4) + invariants (§5), including **INV-2L** the store-row
   lock protocol.
2. **D-CR2-B** recommended architecture (§11) or a named alternative (§12).
3. **D-CR2-C** the **committed admission-lease** mechanism (§10), the **store-row
   `FOR SHARE`/update lock** as the shared serialization primitive (§9.2), the
   **direction-C** expired-lease rule, and keeping the advisory lock dropped.
4. **D-CR2-D** the explicit **`execute_business` (context manager) /
   `execute_lifecycle`** contract, the `_send` token-snapshot change, and the **two
   structural domain call-site edits** (`with execute_business(...)` around call +
   reconciliation) in the future allowlist (§9).
5. **D-CR2-E** critical-path placement (before any Shopify-calling handler,
   incl. reads).
6. **D-CR2-F** confirm **SRR-03 OPEN**, **SRR-04/09 REDUCED**, and that no gate is
   opened by accepting this analysis.

> **Nothing above is accepted.** The CORE-R2 code gate remains **closed** until
> ChatGPT issues an explicit gate act on the packet.
