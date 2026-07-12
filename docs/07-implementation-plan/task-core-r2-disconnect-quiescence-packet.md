# Task CORE-R2 — Disconnect Quiescence & In-Flight Job Contract (Implementation Packet)

> **Status: Proposed packet for ChatGPT review. THE CODE GATE IS NOT OPEN.**
> This is a *locked future prompt*, not implementation authorization. It
> becomes usable **only** when ChatGPT performs an explicit CORE-R2
> implementation-gate act and issues the prompt verbatim in a new session with
> a stated base SHA. Producing or accepting this packet does **not** authorize
> any code change (CLAUDE.md §5/§9, CHATGPT.md §4/§7).
>
> Companion analysis (read first):
> [`../03-architecture/disconnect-quiescence-remediation-analysis.md`](../03-architecture/disconnect-quiescence-remediation-analysis.md).
> Design base verified at authoring: `Shopify-connector` @
> `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f` (PR #153 merged; gate comment
> `4950413650`). The implementation session must re-verify the *then-current*
> `Shopify-connector` tip stated in the gate act.

---

## 1. Objective

Remediate **DEF-PB-1 / SRR-03**: a concurrent operator `store.action_disconnect()`
must **stop already in-flight business work** for that store — preventing any
*new* Shopify side effect once disconnect is requested, clearing the credential
only after in-flight handlers have quiesced (or a bounded timeout with
escalation) — across multiple workers and multiple Odoo servers, without global
serialization, unsafe explicit commits, starvation, or new deadlocks.

## 2. Exact accepted problem (runtime-confirmed)

From PR #153 (control-room accepted, comment `4950408383`): with the real
`action_disconnect()`, a disconnect **blocks behind the running job's row
lock**, the handler **completes**, the job **succeeds**, and the disconnect
then **serialization-fails (library) or retries and completes cancelling zero
jobs (RPC)**. The dispatcher's checkpoint-3 store re-check is **snapshot-blind**
(single REPEATABLE READ transaction; `odoo/sql_db.py:373`) and cannot see a
disconnect committed after the job was claimed. Latent only because all shipped
handlers are no-ops. **SRR-03 stays OPEN until this packet is implemented and
proven live.**

## 3. Proposed binding decisions (to be ratified at the gate — NOT yet binding)

- **DB-CR2-1:** Adopt the **hybrid (Option E)** remediation: `disconnecting`
  state + generation token + cooperative fresh-transaction pre-side-effect
  checkpoint + store-scoped coordination + two-phase disconnect with timeout
  escalation.
- **DB-CR2-2:** Coordination primitive = **transaction-scoped PostgreSQL
  advisory lock keyed by store id** (`pg_advisory_xact_lock`), used only to
  serialize disconnect/reconnect/quiesce per store; quiescence detection is by
  **polling "no `running` business job for this store"**, not a block-wait
  barrier. No session-scoped advisory lock; never combined with a
  `LIMIT`-bounded query (SRR-09 hazard).
- **DB-CR2-3:** Disconnect becomes **two-phase** and never calls
  `cr.commit()` inside an RPC-dispatched method: phase 1 sets intent + enqueues
  a core `core_disconnect_quiesce` job; phases 2–3 run under the existing
  dispatcher (one transaction per pass), reschedule ASAP until quiesced.
- **DB-CR2-4:** Ship the **handler cooperative-cancel contract as a core seam
  now** (a read helper + documented protocol), so the first domain handler is
  born compliant. No domain handler is written by this task.
- **DB-CR2-5:** SRR-03 moves to OPEN → *remediated (pending live proof)* only
  after Odoo.sh green; SRR-04/09 remain REDUCED (not closed).

> These are **proposals**. ChatGPT accepts/revises them at the gate; until
> then they carry no authority.

## 4. Exhaustive future allowed files (for the implementation session — NOT this one)

When the gate opens, the implementation session may create/modify **only**:

- `addons/shopify_connector_core/models/shopify_connector_store.py`
  (two-phase `action_disconnect`; `disconnecting` state; generation/requested-at/
  requested-by fields; `_is_quiescing`/`_quiesce_key` read helpers;
  advisory-lock acquire helper).
- `addons/shopify_connector_core/models/shopify_connector_job.py`
  (`core_disconnect_quiesce` `job_type`; `disconnecting` added to the
  non-startable set in the `write→running` and claim gates; any state marker
  for escalation).
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  (a `core_disconnect_quiesce` handler + the cooperative-cancel plumbing seam;
  `JobQuiescedError`/routing to `skipped`; `DISCONNECT_QUIESCE_TIMEOUT`).
- `addons/shopify_connector_core/models/shopify_connector_store_credential.py`
  **only if** the credential-clear ordering needs a call-site change (no new
  clear path; reuse `action_clear_token`).
- `addons/shopify_connector_core/security/ir.model.access.csv` **only if** the
  new `job_type`/state requires an ACL row (expected: none — both models exist).
- `addons/shopify_connector_core/data/shopify_connector_cron_drain.xml` **only
  if** the quiesce job needs a trigger/rescheduling hook (prefer reusing the
  existing drain cron; change only if unavoidable).
- Tests (new/modified): `addons/shopify_connector_core/tests/test_disconnect_quiescence.py`
  (+ any existing dispatch/store lifecycle test files strictly for regressions).
- `addons/shopify_connector_core/__manifest__.py` **only if** a new data file
  must be registered.
- Docs: this packet's validation record
  `docs/05-qa/task-core-r2-validation-results.md` (new); the risk register,
  handoff, and AR log updates that closure requires.

**The exact allowed-file list is re-frozen in the gate act.** Anything outside
it is forbidden and is scope-creep.

## 5. Forbidden files (implementation session)

Every `addons/**` path **not** listed in §4; all other modules
(`shopify_connector_product`/`_sale`/`_inventory`/`_fulfillment`/…); any
domain handler; Task 010B / 011B / 012 / 013 / 013B / 014 / 015 / 015B /
Area-6 / SEC-1 / LC-1 / U0 files (except a one-line compatibility touchpoint
explicitly authorized in the gate act); `.claude/**`; CI; `main`; plain `dev`.
No live Shopify call, credential, or token in any test. No monkeypatch of
production behavior and no test-only hook to force timing — tests use **real**
`action_disconnect()` and genuine concurrency (per PR #153 method).

## 6. Precise state & transaction behavior

- **Phase 1 (`action_disconnect`, RPC, atomic, `retrying`-safe):** acquire the
  store advisory lock; if `state == 'connected'` → write `state='disconnecting'`,
  `disconnect_generation += 1`, `disconnect_requested_at/by`; enqueue one
  `core_disconnect_quiesce` job (core source, never business-gated); return. If
  `state in ('disconnecting','disconnected')` → audited no-op. **No job-row
  writes in phase 1** (this is what removes the E-R6-3 block and E-R6-5/6
  serialization failure). No `cr.commit()` in the method.
- **Phase 2 (`core_disconnect_quiesce` handler, dispatcher, one txn/pass):**
  cancel `queued`/`retry_waiting`/`blocked_manual_review` business jobs for the
  store; count remaining `running` business jobs; if `>0` and within
  `DISCONNECT_QUIESCE_TIMEOUT`, reschedule ASAP; else proceed to phase 3.
- **Phase 3 (finalize):** clear credential via `action_clear_token`; write
  `state='disconnected'`; create the lifecycle audit job with accurate counts;
  if finalized on timeout with a job still `running`, escalate that job
  (operator-visible marker/log) — never silently.
- **In-flight handler (future domain code, contract only here):** before each
  external side effect, `store._is_quiescing(claimed_generation)` (fresh
  cursor); if true → raise `JobQuiescedError` → dispatcher routes to `skipped`.

## 7. New field / model / state proposal

- **State:** `shopify.connector.store.state` adds `disconnecting`.
- **Fields (store):** `disconnect_generation` (Integer, default 0, readonly),
  `disconnect_requested_at` (Datetime, readonly), `disconnect_requested_by`
  (Many2one `res.users`, readonly). All non-secret.
- **`job_type`:** add `core_disconnect_quiesce` (core/diagnostic; never a
  business source; mirrors `core_manual_maintenance` gating exemption).
- **Constant:** `DISCONNECT_QUIESCE_TIMEOUT` (named, tunable; default proposed
  as a small bounded multiple of the drain interval — final value is D-CR2 /
  Q-QS-5).
- **Exception:** `JobQuiescedError` (cooperative abort; **not** an error class;
  routes to `skipped`, never to the retry taxonomy).

## 8. No-new-job rules (during `disconnecting`)

- `create()` business-job gate already requires `connected` → business enqueue
  blocked while `disconnecting`. **Add** `disconnecting` to the non-startable
  set so `_claim_for_dispatch` and `write→running` never start a business job
  for a `disconnecting` store.
- Core/diagnostic jobs (incl. `core_disconnect_quiesce` itself) remain allowed —
  they are how quiescence completes.

## 9. Running-job behavior

- A running handler that reaches its checkpoint **before** its external effect →
  aborts to `skipped` (audited, no external call).
- A running handler already **past** its external effect → completes naturally;
  phase 3 waits (bounded).
- Timed-out running handler → finalize + escalate (INV-4).
- No running job is deleted; history preserved.

## 10. Credential-clearing behavior

- Cleared **only** in phase 3, via the existing `action_clear_token` (no second
  path), after quiesce or timeout. Never in phase 1. Credential-history
  preserved (DEC-022).

## 11. Timeout / escalation behavior

- `DISCONNECT_QUIESCE_TIMEOUT` bounds phase 2. On expiry with a job still
  `running`: finalize `disconnected` + clear credential, and escalate the stuck
  job with an operator-visible marker + `_system_append` log. **[Open Q-QS-3]:**
  reuse `blocked_manual_review` vs a new `interrupted` marker — resolved at the
  gate.

## 12. Serialization & retry handling

- Phase 1 avoids the running-job row lock, so the disconnect path **does not
  generate** the E-R6-5/6 `serialization_failure` (regression asserted by T-8).
- Quiesce-job writes rely on the normal dispatcher/`retrying()` boundaries.
- `JobQuiescedError` never enters the retry taxonomy.
- No `NOWAIT`/raw `FOR UPDATE` on the job row from the disconnect side.

## 13. Source-level guards (to keep in the implementation)

- No `cr.commit()` inside any RPC-dispatched model method (INV-7).
- Advisory lock is transaction-scoped (`pg_advisory_xact_lock`), standalone,
  never inside a `LIMIT`-bounded query (SRR-09).
- The fresh-cursor read helper opens, reads, and closes its own cursor; it does
  not mutate; it must not leak connections.
- Reuse `_system_append` for all logs; reuse `action_clear_token` for the
  credential; no new `sudo()` beyond the sanctioned inventory (respect the
  CORE-R1 three-site sudo guard — do not add a model-layer `sudo()`).
- Keep the store-state advisory key in a reserved key domain to avoid collision
  with any other advisory-lock use.

## 14. Genuine concurrent tests using the real `action_disconnect()`

Mandatory (no monkeypatch, no timing hook; real method; genuine processes):

- **T-1** race, handler-before-checkpoint → `skipped`, no external call,
  credential cleared after quiesce, accurate audit.
- **T-2** race, handler-past-checkpoint → natural terminal, no double effect.
- **T-3** timeout/escalation → bounded finalize + escalation marker.
- **T-4** two-server (Topology C) → INV-2/INV-3 cross-server.
- **T-5** multi-store isolation → disconnect X doesn't block Y (INV-5).
- **T-6** idempotent re-disconnect; **T-7** reconnect after `disconnecting`.
- **T-8** regression: disconnect path produces **no** `serialization_failure`
  against the running job.
- Reuse the PR #153 harness method (independent Odoo-library processes +
  `pg_stat_activity` lock evidence + a two-`odoo-bin` instance for T-4);
  record it in the validation doc, no committed executable driver (governance).

## 15. Multi-process and two-server tests

- At least one **two-`odoo-bin`-instance, one-DB** test (Topology C, single
  host) proving cross-server INV-2/INV-3 (T-4).
- Multi-process (independent library processes) for T-1/T-2/T-3/T-5.
- **[Open]** True multi-host remains SRR-09 residual; name it as follow-up, do
  not claim it.

## 16. Odoo.sh validation

- Per SRR-06, the change is concurrency/timing-sensitive → **not trusted until
  live Odoo.sh green**. The implementation session must capture a green Odoo.sh
  build of the full `shopify_connector_core` suite (verbatim summary) in
  `docs/05-qa/task-core-r2-validation-results.md`, exactly as CORE-R1 did.

## 17. Rollback

- Revert the CORE-R2 PR. States/fields/`job_type` are **additive**; no data is
  destroyed; a reverted store falls back to the merged `connected → disconnected`
  path. No migration to undo (a `disconnect_generation` column left behind is
  inert; document a follow-up drop if desired). No external effect to reverse.

## 18. Definition of done

- All §14 tests exist and pass; T-8 regression green; Odoo.sh green captured.
- INV-1…INV-9 demonstrably held by the tests.
- Only §4 files changed; no domain code; no forbidden file touched.
- No `cr.commit()` in an RPC-dispatched method; no session advisory lock; no new
  model-layer `sudo()`; no live Shopify call/credential/token in tests.
- Validation record + risk-register/handoff/AR updates written.
- SRR-03 recorded as *remediated (pending any residual multi-host proof)* only
  after green; SRR-04/09 unchanged (REDUCED, not closed).
- Draft PR into `Shopify-connector`; **not** merged, **not** marked ready
  without ChatGPT review.

## 19. Future PR requirements

The eventual implementation PR body must include: the CORE-R2 gate act id; the
verified base SHA; the exact changed files; the two-phase behavior and the
invariant→test mapping; the genuine-concurrency method and the two-server
evidence; the verbatim Odoo.sh green summary; the residual risks (RR-1…RR-6);
confirmation that SRR-03 is only *remediated pending live proof* and
SRR-04/09 stay REDUCED; and confirmation that no other gate is opened. Draft
until ChatGPT review.

---

> **Gate status: CLOSED.** This packet plans the work; it does not authorize
> it. No file under `addons/**` may change until ChatGPT issues the CORE-R2
> implementation-gate act naming the base SHA and re-freezing the allowed-file
> list.
