# Task CORE-R2 — Disconnect Quiescence & In-Flight Job Contract (Implementation Packet)

> **Status: Proposed packet for ChatGPT review. THE CODE GATE IS NOT OPEN.**
> A *locked future prompt*, not implementation authorization. It becomes usable
> only when ChatGPT performs an explicit CORE-R2 implementation-gate act and
> issues the prompt verbatim in a new session with a stated base SHA. Producing
> or accepting this packet does **not** authorize any code change (CLAUDE.md
> §5/§9, CHATGPT.md §4/§7).
>
> **Revision 2 (2026-07-12) — control-room review `4951115877`.** Enforcement
> moved to the **central API client**; **connection epoch** persisted on the
> job; complete in-flight taxonomy incl. **claimed-but-not-started** rows;
> **dedicated trigger-driven controller**; **store-level timeout escalation**;
> **advisory lock dropped**; critical path broadened to **any Shopify call**;
> **executable** INV-2 tests. Companion analysis (read first):
> [`../03-architecture/disconnect-quiescence-remediation-analysis.md`](../03-architecture/disconnect-quiescence-remediation-analysis.md).
> Design base verified at authoring: `Shopify-connector` @
> `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f`.

---

## 1. Objective

Remediate **DEF-PB-1 / SRR-03**: a concurrent operator `store.action_disconnect()`
must guarantee that **no business Shopify call is admitted** once disconnect is
requested — enforced at the **central API-client boundary** against a **persisted
connection epoch** — clearing the credential only after a **bounded** quiesce
wait (or timeout with non-blocking escalation), across multiple workers and
servers, with **no starvation**, **no unsafe explicit commit**, **no write to a
locked job row**, and **no unbounded lock**.

## 2. Exact accepted problem (runtime-confirmed)

PR #153 (accepted `4950408383`): with the real `action_disconnect()`, the
disconnect blocks behind the running job's row lock, the handler completes, the
job succeeds, and the disconnect serialization-fails (library) or is retried and
completes cancelling zero jobs (RPC). Checkpoint-3 is **snapshot-blind** (one
REPEATABLE READ transaction). Latent only because handlers are no-ops. **SRR-03
stays OPEN until this packet is implemented and proven live.**

## 3. Proposed binding decisions (ratified at the gate — NOT yet binding)

- **DB-CR2-1:** INV-2 (no post-epoch Shopify call) is enforced at the **central
  API client** `execute()`, **fail-closed** — not by a voluntary per-handler
  checkpoint.
- **DB-CR2-2:** A persisted **`connection_generation`** (store) +
  **`expected_connection_generation`** (job, captured at enqueue) is the epoch
  contract; a business call proceeds only when a **fresh-cursor** read shows
  `state=='connected'` AND generations match.
- **DB-CR2-3:** The quiesce controller is a **dedicated, high-priority,
  trigger-driven `ir.cron`** servicing `disconnecting` stores — **not** a drained
  business job (no starvation; no "reschedule-self-marked-succeeded").
- **DB-CR2-4:** Job cancellation is **non-blocking** (`try_lock_for_update()` +
  SKIP LOCKED + bounded polling); the disconnect path performs **no** blocking
  write to any running/claimed job row.
- **DB-CR2-5:** Timeout escalation is recorded on **independently-writable
  store-level fields** (incl. `disconnect_stuck_job_id` as a plain **Integer**) +
  a new audit job — **never** on the locked running job row / its log, and
  **never** by overloading `blocked_manual_review`.
- **DB-CR2-6:** **Coordination = store-row optimistic state+generation under
  `retrying()`**; the **advisory lock is dropped** (bounded
  `pg_try_advisory_xact_lock` documented only as a rejected-unless-needed
  fallback).
- **DB-CR2-7:** Phase-1 RPC return = **request accepted**; completion =
  `disconnected` + credential cleared + audit + epoch bumped.
- **DB-CR2-8:** SRR-03 → OPEN → *remediated (pending live proof)* only after
  Odoo.sh green; SRR-04/09 remain REDUCED (not closed).

> Proposals only. ChatGPT accepts/revises at the gate.

## 4. Exhaustive future allowed files (implementation session — NOT this one)

When the gate opens, the implementation session may create/modify **only**:

- `addons/shopify_connector_core/models/shopify_connector_api_client.py`
  — **the central enforcement point**: a fail-closed business-call gate in
  `execute()` (fresh-cursor state+epoch read; lifecycle exemption;
  `ShopifyQuiescedError`); no change to `_send`'s transport contract; no secret
  read/log added.
- `addons/shopify_connector_core/models/shopify_connector_store.py`
  — `disconnecting` state; `connection_generation` + `disconnect_status`/
  `_status_reason`/`_stuck_job_id` (Integer)/`_requested_at`/`_by`/
  `_completed_at` fields; epoch bump in `action_disconnect`/`action_reconnect`/
  `action_activate`/credential-replace; two-phase `action_disconnect`; the
  dedicated-cron controller method `_run_disconnect_quiesce()`; a read-only
  `_connection_epoch_ok(job)`/`_fresh_connection_epoch()` helper.
- `addons/shopify_connector_core/models/shopify_connector_job.py`
  — `expected_connection_generation` field captured at enqueue; `disconnecting`
  added to the non-startable set in the claim + `write→running` gates.
- `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`
  — set the **business-call context** (`shopify_business_job_id`) before invoking
  a business handler; route `ShopifyQuiescedError` → `skipped`; the non-blocking
  cancellation sweep helper; `DISCONNECT_QUIESCE_TIMEOUT`/`POLL_DELAY` constants.
- `addons/shopify_connector_core/models/shopify_connector_job_enqueue.py`
  — capture `expected_connection_generation` at enqueue (thin).
- `addons/shopify_connector_core/models/shopify_connector_store_credential.py`
  — **only if** the credential-clear call-site ordering needs a change (reuse
  `action_clear_token`; no new clear path).
- `addons/shopify_connector_core/data/shopify_connector_cron_*.xml`
  — one new `ir.cron` record for the dedicated quiesce controller (high
  priority). Prefer a new file registered in the manifest over editing the drain
  cron.
- `addons/shopify_connector_core/security/ir.model.access.csv` — **only if** a
  new record type requires an ACL row (expected: none).
- `addons/shopify_connector_core/__manifest__.py` — **only if** a new data file
  must be registered.
- Tests: `addons/shopify_connector_core/tests/test_disconnect_quiescence.py`
  (+ minimal regressions in existing dispatch/store/api-client test files).
- Docs: `docs/05-qa/task-core-r2-validation-results.md` (new); the risk-register/
  handoff/AR updates closure requires.

**The exact allowed-file list is re-frozen in the gate act.** Anything outside it
is scope-creep.

## 5. Forbidden files (implementation session)

Every `addons/**` path **not** in §4; all other modules; any domain handler; Task
010B/011B/012/013/013B/014/015/015B/Area-6/SEC-1/LC-1/U0 files (except a one-line
compatibility touchpoint explicitly authorized in the gate act); `.claude/**`;
CI; `main`; plain `dev`. No live Shopify call/credential/token in tests. **No
monkeypatch of the lifecycle/state mechanism and no test-only timing hook** — use
the real `execute()` gate and the existing `_send` transport seam.

## 6. Precise state & transaction behavior

- **Phase 1 (`action_disconnect`, RPC, atomic, `retrying`-safe):** if
  `state=='connected'` → write `state='disconnecting'`, `connection_generation +=
  1`, `disconnect_status='requested'`, `disconnect_requested_at/by`; run **one**
  non-blocking cancellation sweep (A/B rows; SKIP LOCKED); `controller_cron
  ._trigger()`; return "request accepted". Idempotent no-op if already
  `disconnecting`/`disconnected`. **No** job-row blocking write; **no**
  `cr.commit()` in the method.
- **Controller pass (`_run_disconnect_quiesce`, dedicated cron, one txn/pass,
  per `disconnecting` store):** non-blocking sweep; count `running` business
  jobs; **if 0** → finalize (clear credential, `state='disconnected'`,
  `disconnect_status='completed'`, `disconnect_completed_at`, audit job); **elif
  within timeout** → `disconnect_status='quiescing'`, `_trigger(now+POLL_DELAY)`;
  **else** → finalize + escalation (§9). Writes only the **store row** + a **new**
  audit job — never a running/claimed job row.
- **Central gate (`execute()`):** business context → fresh-cursor read of
  `state`+`connection_generation`; block on non-`connected` or epoch mismatch
  (`ShopifyQuiescedError`); lifecycle context → allowed; neither → fail closed.
- **In-flight handler (future domain code, contract only here):** Phase A gate
  before each call; Phase B complete local reconciliation for an admitted call;
  Phase C re-gate before the next call.

## 7. New field / model / state proposal

- **State:** store `state` adds `disconnecting`.
- **Store fields:** `connection_generation` (Integer, default 0, readonly);
  `disconnect_status` (Selection `none/requested/quiescing/completed/timed_out`,
  default `none`); `disconnect_status_reason` (Char); `disconnect_stuck_job_id`
  (**Integer**); `disconnect_requested_at`/`disconnect_completed_at` (Datetime);
  `disconnect_requested_by` (Many2one `res.users`). All non-secret, written on the
  store row.
- **Job field:** `expected_connection_generation` (Integer, default 0, readonly,
  captured at enqueue).
- **Cron:** one dedicated high-priority (`priority=0`) `ir.cron` for the quiesce
  controller.
- **Constants:** `DISCONNECT_QUIESCE_TIMEOUT`, `POLL_DELAY` (named, tunable).
- **Exception:** `ShopifyQuiescedError` (cooperative abort → `skipped`; not an
  error class).
- **Context key:** `shopify_business_job_id` (set by the dispatcher; read by the
  gate).

## 8. No-new-job rules (during `disconnecting`)

- `create()` business gate already requires `connected` → business enqueue
  blocked while `disconnecting`. **Add** `disconnecting` to the non-startable set
  so `_claim_for_dispatch` + `write→running` never start a business job for a
  `disconnecting` store. Core/diagnostic jobs and the controller cron remain
  allowed.

## 9. Running-job behavior & timeout escalation

- A/B → `cancelled` (non-blocking sweep). C → skipped-by-sweep, resolved by the
  gate (`skipped`) or a later pass (`cancelled`). D → `skipped` at the gate. E/F →
  natural terminal after local reconciliation.
- **Timeout:** finalize + escalate on the **store row** only —
  `disconnect_status='timed_out'`, `disconnect_status_reason`,
  `disconnect_stuck_job_id` (Integer; **not** a Many2one, to avoid an FK KEY
  SHARE lock on the job row) + a new `core_manual_maintenance` audit job. **Never**
  write the locked running job row/log; **never** overload
  `blocked_manual_review`. Bounded; credential cleared per contract; stuck job id
  exposed; original running row preserved for later reconciliation.

## 10. Credential-clearing behavior

Cleared only at finalize, via existing `action_clear_token`, after the bounded
`running→0` wait or timeout. Never in Phase 1. Credential history preserved.

## 11. Timeout / escalation behavior

`DISCONNECT_QUIESCE_TIMEOUT` bounds the controller. On expiry with a running job:
finalize `disconnected` + clear credential + store-level escalation (§9). No
re-trigger after finalize.

## 12. Serialization & retry handling

Phase 1 and the sweep never block on a job row → the disconnect path produces no
`serialization_failure` against the running/claimed job (T-8). Lifecycle-command
serialization is by the store-row write under `retrying()`. `ShopifyQuiescedError`
never enters the retry taxonomy. No `NOWAIT`/raw `FOR UPDATE` on job rows from the
disconnect side.

## 13. Source-level guards (to keep in the implementation)

- No `cr.commit()` in any RPC-dispatched model method (INV-7).
- The gate's fresh cursor is opened via a `with` block, read-only (two non-secret
  columns), always rolled back + closed, never committed, no connection leak.
- The gate reads **no secret**; the token stays on the `_get_access_token` path.
  No new **model-layer mutating** `sudo()` (respect the CORE-R1 three-site
  inventory); any elevated read is read-only and pinned by a guard/test.
- `disconnect_stuck_job_id` is a plain Integer; the timeout path writes no job
  row/log.
- Advisory lock **not** used; if ever added, only bounded
  `pg_try_advisory_xact_lock(CONNECTOR_NS, store_id)`, lifecycle-only, released at
  txn end, never inside a `LIMIT` query, documented as not closing the call race.
- Reuse `_system_append` for logs; reuse `action_clear_token` for the credential.
- A **source-level test** asserts the dispatcher sets `shopify_business_job_id`
  and that `execute()` fail-closes for a business call without it (RR-5).

## 14. Genuine concurrent tests using the real `action_disconnect()` and the real `execute()` gate

Mandatory (real method + real gate; `_send` transport seam; no live Shopify; no
monkeypatch of lifecycle/state; no timing hook):

- **T-1** stale epoch blocks before `_send`.
- **T-2** `disconnecting` blocks before `_send`.
- **T-3** reconnect (epoch +2) does not revive an old job.
- **T-4** diagnostic `action_test_connection` still reaches `_send` when
  intended.
- **T-5** admitted first call completes local reconciliation (Phase B).
- **T-6** second call blocked after disconnect (Phase C).
- **T-7** genuine race: claimed-but-not-started (C) later starts but `execute()`
  fail-closes → `skipped`, `_send` not called.
- **T-8** no `serialization_failure` on the disconnect path (regression).
- **T-9** controller does not starve behind a large `id asc` business backlog.
- **T-10** timeout finalizes without writing the locked running job row/log
  (asserts store-level escalation surface only).
- **T-11** two-server (Topology C) cross-server INV-2/INV-3.
- **T-12** multi-store isolation.
- **T-13** idempotent re-disconnect; **T-14** reconnect after `disconnecting`.

Record the sanitized method in the validation doc (no committed executable
driver; governance).

## 15. Multi-process and two-server tests

At least one two-`odoo-bin`-instance, one-DB test (Topology C, single host) for
cross-server INV-2/INV-3 (T-11); independent-process races for T-7/T-9/T-10/T-12.
**[Open]** true multi-host remains SRR-09 residual — name it, do not claim it.

## 16. Odoo.sh validation

Per SRR-06, the change is concurrency/timing-sensitive → **not trusted until live
Odoo.sh green**. Capture a verbatim green summary of the full
`shopify_connector_core` suite in `docs/05-qa/task-core-r2-validation-results.md`,
as CORE-R1 did.

## 17. Rollback

Revert the CORE-R2 PR. States/fields/`job_type`-free additions are **additive**;
no data destroyed; a reverted store falls back to the merged `connected →
disconnected` path. Inert leftover columns (e.g. `connection_generation`) are
harmless; document an optional follow-up drop. No external effect to reverse.

## 18. Definition of done

- All §14 tests exist and pass; T-7/T-8/T-9/T-10 green; Odoo.sh green captured.
- INV-1…INV-9 demonstrated by the tests; INV-2 proven at the **real production
  `execute()` gate** (not a documented seam alone).
- Only §4 files changed; no domain handler; no forbidden file touched.
- No `cr.commit()` in an RPC-dispatched method; no advisory lock; no new
  model-layer mutating `sudo()`; no secret read/log; no live Shopify call in
  tests; no monkeypatch/timing hook.
- The timeout path writes no locked job row/log; escalation is store-level.
- Validation record + risk-register/handoff/AR updates written.
- SRR-03 recorded as *remediated (pending any residual multi-host proof)* only
  after green; SRR-04/09 unchanged.
- Draft PR into `Shopify-connector`; not merged/ready without ChatGPT review.

## 19. Future PR requirements

The implementation PR body must include: the CORE-R2 gate act id; verified base
SHA; exact changed files; the central-enforcement + epoch design; the
invariant→test mapping incl. the claimed-but-not-started and timeout-without-
locked-write cases; the genuine-concurrency method + two-server evidence; the
verbatim Odoo.sh green summary; residual risks (RR-1…RR-6); confirmation SRR-03 is
only *remediated pending live proof* and SRR-04/09 stay REDUCED; and confirmation
no other gate is opened. Draft until ChatGPT review.

---

> **Gate status: CLOSED.** This packet plans the work; it does not authorize it.
> No file under `addons/**` may change until ChatGPT issues the CORE-R2
> implementation-gate act naming the base SHA and re-freezing the allowed-file
> list.
