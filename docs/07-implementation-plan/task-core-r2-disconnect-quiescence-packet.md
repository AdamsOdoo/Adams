# Task CORE-R2 — Disconnect Quiescence & In-Flight Job Contract (Implementation Packet)

> **Historical-status note (2026-07-16, Fable gap-closure mission):** the
> gate wording below predates Wave 1. This packet's work was implemented and
> **merged in Wave 1 (PR #172, merge `d18f9a9`)**; SRR-03 is **CLOSED**
> (build `34986844`, ruling `4988527547`). The packet is retained as the
> historical specification record; its locked prompt is exhausted and must
> not be reissued.

> **Status: Proposed packet for ChatGPT review. THE CODE GATE IS NOT OPEN.**
> A *locked future prompt*, not implementation authorization. Usable only when
> ChatGPT performs an explicit CORE-R2 implementation-gate act and issues it
> verbatim in a new session with a stated base SHA. Producing/accepting it
> authorizes **no** code change (CLAUDE.md §5/§9).
>
> **Revision 3 (2026-07-12) — control-room review `4951237871`.** Quiescence is
> now a **committed admission-lease**, not a `running` count; admission is
> atomic with a **single token snapshot**; a bounded **set** of admitted calls;
> explicit **`execute_business`/`execute_lifecycle`** entry points with a full
> call-site inventory (incl. two domain call sites); frozen lifecycle matrix;
> **one-store-per-cron-transaction** controller; lease-based timeout; **ordered
> rollback**. Companion analysis (read first):
> [`../03-architecture/disconnect-quiescence-remediation-analysis.md`](../03-architecture/disconnect-quiescence-remediation-analysis.md).
> Base after normal-merge of the integration tip: `Shopify-connector` @
> `cfdb05703a65f82b34a9a11364aab6fc960cca9d` (control-room base-sync
> amendment; supersedes `65e915a`; PR #152/U0 + PR #155/U0-closure preserved).
>
> **Revision 4 (2026-07-12) — control-room review `4680299311`.** Six
> implementation-safety corrections: **(1)** admission is atomic with disconnect
> via a **store-row lock protocol** — `FOR SHARE` for admission, `FOR NO KEY
> UPDATE`/`FOR UPDATE` for every generation-changing transition (analysis §9.2);
> **(2)** `execute_business` is frozen as a **context manager** wrapping the HTTP
> request **and** its local reconciliation (§9.1); **(3)** the expired-lease rule
> is **direction C** — expired = unknown/live, `completed` needs zero rows,
> crashed holders resolve via `timed_out` (distinct), cleanup only after
> `timed_out` (§10/§16); **(4)** controller selection corrected to
> `try_lock_for_update(limit=1)` that can pick the next unlocked store, with a
> **`POLL_DELAY`** cadence via delayed `_trigger(at=…)` (§14); **(5)** ordered
> rollback requires **zero holders** (drain workers first) before code/model
> removal (§17); **(6)** the CORE-R2 architecture-review row is **AR-047**
> (AR-044 = U0, AR-045 = Task 011B, AR-046 = Task 010B, AR-047 = CORE-R2).

---

## 1. Objective

Remediate **DEF-PB-1 / SRR-03**: guarantee that after `action_disconnect()` no
business Shopify call is admitted (INV-2, enforced at `execute_business`), and
that the store is finalized (credential cleared, `disconnected`) only when a
**committed admission-lease** count for the store is zero or a bounded timeout
fires (INV-3) — across workers and servers, with no reliance on cross-transaction
`running` visibility, no unsafe main-cursor commit, no write to a locked job row,
and a single in-memory token snapshot per admitted call.

## 2. Exact accepted problem (runtime-confirmed + visibility correction)

PR #153 (accepted `4950408383`): the disconnect blocks behind the running job's
row lock, the handler completes, the job succeeds, the disconnect
serialization-fails/retries cancelling zero jobs. **Visibility correction
(review `4951237871`):** `run_drain` sets `running`, runs the handler, and commits
in **one** transaction, so `running` is invisible to other transactions
mid-handler; a locked in-flight row appears committed as `queued`/`retry_waiting`;
a `running` count cannot detect admitted work. **SRR-03 stays OPEN.**

## 3. Proposed binding decisions (ratified at the gate — NOT yet binding)

- **DB-CR2-1:** INV-2 at `execute_business(job, store, query, …)` — a
  **context manager** (fail-closed vs persisted epoch) wrapping the call **and** its
  local reconciliation; `execute_lifecycle(store, query, purpose=…)` (plain, no
  lease) with a purpose→state matrix; public `execute()` removed.
- **DB-CR2-2:** persisted `store.connection_generation` (matrix §7) vs
  enqueue-captured `job.expected_connection_generation`; fresh-cursor gate.
- **DB-CR2-3:** quiescence via a **committed `shopify.connector.call.lease`**
  written on a side cursor before admission, released in the context-manager
  `__exit__` after reconciliation; **direction C** — an expired-but-unreleased
  lease is unknown/live (never reaped into `completed`); **multiple leases/store**.
- **DB-CR2-4:** atomic admission under a **store-row `FOR SHARE` lock** (lock →
  gate read → token read → lease commit, all in one side txn; lock released at
  commit before `_send`); **single in-memory token snapshot** passed to
  `_send(store, body, token)`.
- **DB-CR2-4L (lock protocol):** every generation-changing lifecycle transition
  (disconnect, credential replace, activation, reconnect, finalize) takes the
  **conflicting** store-row update lock (`FOR NO KEY UPDATE`/`FOR UPDATE`);
  concurrent admissions (shared) do not conflict; `store → credential` lock order
  is global (deadlock-free).
- **DB-CR2-5:** **one-store-per-cron-invocation** controller selecting via
  `search(...).try_lock_for_update(limit=1)` (`FOR UPDATE SKIP LOCKED LIMIT 1` —
  **picks the next unlocked store**, no-op if all locked), no explicit main-cursor
  `cr.commit()`; still-quiescing store re-polls via **delayed
  `_trigger(at=now+POLL_DELAY)`** (no busy loop).
- **DB-CR2-6:** on `completed` (zero lease rows) or `timed_out` (rows at the
  deadline) the finalize clears the credential while any admitted holder finishes
  with its in-memory token; `timed_out` is **distinct** from `completed`; escalation
  on store fields + audit job; never write a locked job row.
- **DB-CR2-7:** disconnect is **one-way**; generation bumps on every successful
  activation/reconnect (under the update lock).
- **DB-CR2-8:** **ordered rollback requiring zero holders** (§17); SRR-03 OPEN,
  SRR-04/09 REDUCED.

> Proposals only.

## 4. Exhaustive future allowed files (implementation session — NOT this one)

When the gate opens, the implementation session may create/modify **only**:

**`shopify_connector_core` (module of record):**
- `models/shopify_connector_api_client.py` — `execute_business` as a
  **`@contextlib.contextmanager`** (admission `__enter__` + lease-release `__exit__`,
  §9.1) and `execute_lifecycle` (plain); the `_admit` helper (store-row `FOR SHARE`
  + fresh gate read + single token read + lease commit) and `_release_lease` helper;
  remove/privatize public `execute()`; `_send(store, body, token)` (single token
  snapshot); `ShopifyQuiescedError`.
- `models/shopify_connector_call_lease.py` — **new** `shopify.connector.call.lease`
  model (store_id M2o, lease_key Char, job_id **Integer**, worker_ref Char,
  admitted_at, expires_at; no secret); create/release helpers on a side cursor;
  **direction-C** cleanup helper (deletes rows only after the store is `timed_out`).
- `models/shopify_connector_store.py` — `disconnecting` state; `connection_generation`
  + `disconnect_status`/`_status_reason`/`_open_lease_count`/`_oldest_admitted_at`/
  `_requested_at`/`_by`/`_completed_at`; **every generation-changing transition
  acquires the store-row update lock** (disconnect/reconnect/activate/credential-
  replace) and bumps the epoch; two-phase `action_disconnect`; controller method
  `_run_disconnect_quiesce()` with the corrected
  `try_lock_for_update(limit=1)` selection + delayed `_trigger(at=…)` cadence;
  lifecycle-matrix refusals during `disconnecting`; migrate `action_test_connection`
  to `execute_lifecycle`.
- `models/shopify_connector_job.py` — `expected_connection_generation`;
  `disconnecting` in the non-startable set.
- `models/shopify_connector_job_dispatch.py` — route `ShopifyQuiescedError` →
  `skipped`; non-blocking sweep helper; constants `MAX_CALL_LIFETIME`,
  `DISCONNECT_QUIESCE_TIMEOUT`, `POLL_DELAY`.
- `models/shopify_connector_job_enqueue.py` — capture `expected_connection_generation`.
- `models/shopify_connector_store_credential.py` — **only if** the clear call-site
  ordering needs a change (reuse `action_clear_token`).
- `security/ir.model.access.csv` — one ACL row for the new lease model.
- `data/shopify_connector_cron_*.xml` — one new controller `ir.cron` (priority 0).
- `__manifest__.py` — register the new data file/model.
- `tests/test_disconnect_quiescence.py` (+ minimal regressions in existing
  core dispatch/store/api-client tests).

**Domain-module call sites (named, CALL-SITE-ONLY — everything else forbidden):**
- `shopify_connector_product/models/shopify_connector_product_importer.py` — thread
  the in-scope `job` into `import_product_sync` and wrap the existing `execute(...)`
  **and the normalize/apply reconciliation that follows it** in
  `with execute_business(job, store, query, …) as result:` (analysis §9.3). This is
  a **structural** call-site change (re-indent the call-plus-reconciliation region
  under the `with`), **not** a one-line swap — required so the lease spans
  reconciliation (review point 2).
- `shopify_connector_sale/models/shopify_connector_customer_importer.py` — the same
  **structural** `with execute_business(job, …)` wrap around its call **and** its
  `_apply_import` reconciliation; thread `job` likewise.

**Docs:** `docs/05-qa/task-core-r2-validation-results.md` (new) + closure updates.

**The exact allowlist is re-frozen in the gate act.** The two domain edits are
**call-site-scoped** — the one business call site each, the reconciliation region it
already owns (re-indented under the `with`), and the `job` thread-through; **no other
logic in those modules may change.**

## 5. Forbidden files (implementation session)

Every path not in §4; all other domain logic in the product/sale modules beyond
the one call site each; other modules; `.claude/**`; CI; `main`; plain `dev`; U0
files. No live Shopify call/credential/token in tests. **No monkeypatch of the
lifecycle/state mechanism, no test-only timing hook** — use the real
`execute_business` gate + the `_send` transport seam.

## 6. Precise state & transaction behavior

- **Phase 1 (`action_disconnect`, RPC, atomic):** if `connected` → **take the
  store-row update lock** (blocking `FOR NO KEY UPDATE` via the ORM write) →
  `disconnecting`, bump epoch, `disconnect_status='requested'`, stamp, one
  non-blocking A/B sweep, `controller._trigger()`, return "request accepted". No
  job-row blocking write; no main-cursor commit. Refuse if already
  `disconnecting`/`disconnected` (audited no-op).
- **Admission (`execute_business.__enter__`):** side cursor → **`SELECT … FOR
  SHARE`** on the store row → fresh gate read (state + epoch) → token read once →
  lease `INSERT` → `COMMIT` (**releases the `FOR SHARE` and commits the lease
  atomically — the lock, not the bare commit, is the linearization point**) →
  `_send(store, body, token)` → yield `result`. The `with` body does Phase-B
  reconciliation; **`__exit__`** does lease `DELETE`+`COMMIT` on both normal and
  exception exit; a crash leaves the committed lease for the direction-C timeout.
- **Controller (`_run_disconnect_quiesce`, one store/invocation):** select one
  `disconnecting` store via `search(...).try_lock_for_update(limit=1)` (`FOR UPDATE
  SKIP LOCKED LIMIT 1` — next unlocked store, or no-op); the held `FOR UPDATE`
  blocks new admissions; A/B sweep; **count all lease rows** (expired rows count —
  direction C); write escalation snapshot; **0 → `completed` finalize** /
  **within timeout → `quiescing`** / **past timeout → `timed_out` finalize then
  clean up rows**; still-quiescing store re-polls via **`_trigger(at=now+POLL_DELAY)`**.

## 7. New field / model / state proposal

Store: `disconnecting` state; fields per §4. Job: `expected_connection_generation`.
New model `shopify.connector.call.lease` (§4; no secret). Cron: one controller
`ir.cron` (priority 0). Constants: `MAX_CALL_LIFETIME` (> 30s client timeout +
reconcile budget), `DISCONNECT_QUIESCE_TIMEOUT`, `POLL_DELAY`. Exception
`ShopifyQuiescedError`.

## 8. No-new-job / no-new-call rules during `disconnecting`

`create()` business gate already requires `connected`. Add `disconnecting` to the
non-startable set (claim + `write→running`). `execute_business` refuses (epoch
mismatch / not connected). `execute_lifecycle` refuses in `disconnecting` per the
matrix. Core/diagnostic jobs and the controller run.

## 9. Business/lifecycle API contract (frozen)

`execute_business(job, store, query, variables=None)` — mandatory positional
`job`; **used only as a context manager** (`with … as result:`) whose `__enter__`
performs atomic admission + the HTTP call and whose `__exit__` releases the lease
**after** the body's reconciliation (analysis §9.1) — no value-returning form, no
manual release. `execute_lifecycle(store, query, variables=None, purpose=...)` — a
plain method (no lease) with a fixed purpose enum + allowed-state matrix. Public
`execute()` removed/private. Call-site inventory + migrations: analysis §9.3 (core
store test-connection → lifecycle; product + customer importers → **structural
`with execute_business(job, …)`** around call + reconciliation).

## 10. Single token snapshot

Token read **once** during admission (in the side txn), held in memory, passed to
`_send(store, body, token)`; no second lookup; never persisted (not in lease/log);
redacted in errors. `_send` signature change is authorized (supersedes the rev-2
no-change restriction).

## 11. Lifecycle state matrix

Frozen in analysis §8: disconnect one-way; lifecycle mutations refused during
`disconnecting`; generation bumps on every successful activation/reconnect. T-13/
T-14 map to exact rows.

## 12. Timeout / escalation (direction C)

Lease-based (§16 analysis): `completed` requires **zero lease rows**; if any rows
(expired **or** live) remain at `DISCONNECT_QUIESCE_TIMEOUT` the store finalizes
**`timed_out`** (a **distinct** status), clears the credential while admitted
holders finish with their in-memory token, **then** cleans up the rows. Expiry
alone never manufactures `completed`. Escalation snapshot
(`disconnect_open_lease_count`, `disconnect_oldest_admitted_at`, opaque lease_keys /
Integer job_ids) + audit job; never write a locked job row; no secret stored.

## 13. Controller transaction & scheduling (corrected)

One store per cron invocation/transaction, selected via
`search([...],order=...).try_lock_for_update(limit=1)` — `FOR UPDATE SKIP LOCKED
LIMIT 1`, which **picks the next unlocked store** (a locked first row does not block
later ones; all-locked → documented no-op). The held `FOR UPDATE` conflicts with
admission's `FOR SHARE`, keeping the lease count stable through finalize. No explicit
main-cursor commit. A still-`quiescing` store re-polls via **delayed
`_trigger(at=now+POLL_DELAY)`** (`POLL_DELAY ≥ 1 min`, the `_trigger` granularity —
no immediate same-store re-trigger, no busy loop); duplicate triggers idempotent;
crash recovery via durable `disconnecting` + `nextcall` + the direction-C timeout.
`priority=0` = prioritization, **not** a dedicated slot; completion is an SLA under a
healthy scheduler, **not** a wall-clock guarantee; safety (epoch gate) is immediate.

## 14. Source-level guards

- No `cr.commit()` on the request/main cursor; side-cursor writes via a `with`
  block, always committed/closed, no leak.
- **Admission acquires the store-row `FOR SHARE`** with one raw statement on the
  side cursor (no built-in shared helper); it is released at the commit **before**
  `_send`, so no lock spans the network call. Every generation-changing transition
  takes the conflicting `FOR NO KEY UPDATE`/`FOR UPDATE`; `store → credential` lock
  order is global.
- Lease `store_id` is a store M2o; `job_id` is a plain **Integer** (no job FK →
  no `KEY SHARE` lock on a drain-locked job row).
- `completed`/`timed_out` finalize + credential clear run under the controller's
  held `FOR UPDATE`; timeout writes only store fields + a new audit job; never a
  running/claimed job row or its log; `blocked_manual_review` not overloaded.
- No advisory lock. No new model-layer mutating `sudo()` beyond what the lease
  create/read requires under an explicit ACL (respect the CORE-R1 three-site
  inventory; the lease writes go through normal ACL, not a broad `sudo()`).
- Token memory-only; `_send` receives the snapshot; no second `_get_access_token`.
- Source-level test asserts public `execute()` is gone, that `execute_business` is
  a context manager (no value-returning form), and that a business call without a
  valid `job`/epoch fails closed.

## 15. Genuine concurrent tests (real mechanism, real gate)

T-1…T-22 (analysis §24) map one-to-one to the **fourteen required proofs** of
review `4680299311` §9: **(1)** admission lock wins first → lease before disconnect,
controller waits; **(2)** disconnect lock wins first → admission refuses, no
`_send`; **(3)** no finalize between gate read and lease commit; **(4)** ≥2
concurrent admissions on one store; **(5)** lease live through real reconciliation;
**(6)** context exit releases; **(7)** context exception releases; **(8)**
slow-but-live not falsely reaped; **(9)** worker crash → `timed_out` + post-cleanup;
**(10)** `completed` ⇒ all released; **(11)** `timed_out` ≠ `completed`; **(12)**
POLL_DELAY, no busy-loop; **(13)** locked first store doesn't block later ones;
**(14)** ordered rollback refuses with active holders. Plus token-read-once,
no-serialization-failure, multi-store, two-server, one-store-per-controller-
transaction, duplicate-trigger idempotency, lifecycle matrix, cron-delay safety.
Real `execute_business` gate + `_send` transport seam; no live Shopify; no
monkeypatch; no test-only timing hook.

## 16. Odoo.sh validation

Per SRR-06, capture a verbatim green summary of the full `shopify_connector_core`
suite in `docs/05-qa/task-core-r2-validation-results.md`.

## 17. Ordered rollback — requires zero holders (review point 5)

Code/model removal is **last**, only after **zero holders** is proven (a lease may
still have a live holder that will return, reconcile, and release; a `timed_out`
holder may still `_send` with an in-memory token):

1. **Disable new disconnect transitions** (feature-guard `action_disconnect`).
2. **Disable new business admissions** (feature-flag `execute_business.__enter__`
   fail-closed → no new lease/`_send`).
3. **Stop or drain the workers** (stop drain/controller crons; let every admitted
   handler run to completion so its `__exit__` releases its lease), **or wait**
   until every holder — including any `timed_out` holder still finishing with an
   in-memory token — exits.
4. **Verify zero active/unreleased holders** (`count(call.lease) == 0` **and** no
   worker inside an `execute_business` context); if non-zero, return to step 3.
5. **Normalize store states** (cleared-credential → `disconnected`; else →
   `connected`/`reconnect_needed`); no unsupported `state` value remains.
6. **Preserve audit evidence** (keep/archive lifecycle audit jobs — DEC-022).
7. **Only now remove/deactivate** the controller `ir.cron`, the `call.lease` model,
   the guarded entries, the `_send` token param, and the two domain call-site edits.

Retain the added columns/lease table **inertly** (recommended) or drop by a later
migration; **never remove code/model (step 7) before zero-holders is verified
(step 4).**

## 18. Definition of done

- All §15 tests pass — the **fourteen required proofs** (admission-lock-first,
  disconnect-lock-first, no-finalize-mid-admission, ≥2-concurrent-admissions,
  lease-live-through-reconciliation, context-exit/exception release,
  slow-live-not-reaped, crash→`timed_out`, `completed`⇒all-released,
  `timed_out`≠`completed`, POLL_DELAY-no-busy-loop, locked-first-store-progresses,
  rollback-refuses-with-holders) plus token-read-once and no-serialization-failure;
  Odoo.sh green captured.
- INV-1…INV-9 + **INV-2L (store-row lock protocol)** demonstrated; INV-2 proven at
  the real `execute_business` context-manager gate; INV-3 proven via committed
  leases under direction C (not `running` count, not expiry-reap).
- Only §4 files changed; the two domain edits are call-site-scoped (call +
  reconciliation region + `job` thread-through); no forbidden file/line touched.
- No main-cursor `cr.commit()`; no advisory lock; the store-row `FOR SHARE`/update
  lock is the only serialization primitive; token memory-only; no secret in
  lease/log; timeout writes no locked job row.
- **Ordered rollback requires zero holders** (workers drained first); its
  preconditions are tested where feasible.
- Validation record + register/handoff/AR updates written; SRR-03 recorded as
  *remediated (pending residual multi-host proof)* only after green; SRR-04/09
  unchanged.
- Draft PR; not merged/ready without ChatGPT review.

## 19. Future PR requirements

The implementation PR body must include: the gate act id; verified base SHA; exact
changed files (incl. the two named domain call sites); the **store-row lock
protocol** + **context-managed** lease mechanism + single-token design; the
invariant→test mapping incl. the fourteen required proofs (both lock orders,
context exit/exception release, direction-C `completed`-vs-`timed_out`,
POLL_DELAY-no-busy-loop, locked-first-store-progresses, rollback-refuses-with-
holders); the two-server evidence; the verbatim Odoo.sh green summary; residual
risks (RR-1…RR-7); the **zero-holders ordered rollback**; confirmation SRR-03 is
only *remediated pending live proof*, SRR-04/09 REDUCED, and no other gate opened.
Draft until review.

---

> **Gate status: CLOSED.** This packet plans the work; it does not authorize it.
> No `addons/**` file may change until ChatGPT issues the CORE-R2 gate act naming
> the base SHA and re-freezing the allowed-file list.
