# Task CORE-R2 — Disconnect Quiescence & In-Flight Job Contract (Implementation Packet)

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

- **DB-CR2-1:** INV-2 at `execute_business(job, store, query, …)` (fail-closed vs
  persisted epoch); `execute_lifecycle(store, query, purpose=…)` with a
  purpose→state matrix; public `execute()` removed.
- **DB-CR2-2:** persisted `store.connection_generation` (matrix §7) vs
  enqueue-captured `job.expected_connection_generation`; fresh-cursor gate.
- **DB-CR2-3:** quiescence via a **committed `shopify.connector.call.lease`**
  written on a side cursor before admission, released after reconciliation,
  expiry+reaper for crash recovery; **multiple leases per store**.
- **DB-CR2-4:** atomic admission (gate + token read + lease commit in one side
  txn); **single in-memory token snapshot** passed to `_send(store, body, token)`.
- **DB-CR2-5:** **one-store-per-cron-invocation** controller (store-row SKIP
  LOCKED selection), no explicit main-cursor `cr.commit()`; `_trigger` the next.
- **DB-CR2-6:** timeout finalizes + clears credential while admitted holders
  finish with their in-memory token; escalation on store fields + audit job;
  never write a locked job row.
- **DB-CR2-7:** disconnect is **one-way**; generation bumps on every successful
  activation/reconnect.
- **DB-CR2-8:** ordered rollback (§17); SRR-03 OPEN, SRR-04/09 REDUCED.

> Proposals only.

## 4. Exhaustive future allowed files (implementation session — NOT this one)

When the gate opens, the implementation session may create/modify **only**:

**`shopify_connector_core` (module of record):**
- `models/shopify_connector_api_client.py` — `execute_business`/`execute_lifecycle`
  entry points; remove/privatize public `execute()`; `_send(store, body, token)`
  (single token snapshot); the fresh-cursor gate; `ShopifyQuiescedError`.
- `models/shopify_connector_call_lease.py` — **new** `shopify.connector.call.lease`
  model (store_id M2o, lease_key Char, job_id **Integer**, worker_ref Char,
  admitted_at, expires_at; no secret); create/release/reap helpers on a side cursor.
- `models/shopify_connector_store.py` — `disconnecting` state; `connection_generation`
  + `disconnect_status`/`_status_reason`/`_open_lease_count`/`_oldest_admitted_at`/
  `_requested_at`/`_by`/`_completed_at`; epoch bump on disconnect/reconnect/activate/
  credential-replace; two-phase `action_disconnect`; controller method
  `_run_disconnect_quiesce()`; lifecycle-matrix refusals during `disconnecting`;
  migrate `action_test_connection` to `execute_lifecycle`.
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
  the in-scope `job` and swap `execute(...)` → `execute_business(job, …)` at the
  one call site (`import_product_sync` ← `_handle_product_import_sync`).
- `shopify_connector_sale/models/shopify_connector_customer_importer.py` — the
  same one-line-scope migration at its business call site.

**Docs:** `docs/05-qa/task-core-r2-validation-results.md` (new) + closure updates.

**The exact allowlist is re-frozen in the gate act.** The two domain edits are
**call-site-only**; no other line in those modules may change.

## 5. Forbidden files (implementation session)

Every path not in §4; all other domain logic in the product/sale modules beyond
the one call site each; other modules; `.claude/**`; CI; `main`; plain `dev`; U0
files. No live Shopify call/credential/token in tests. **No monkeypatch of the
lifecycle/state mechanism, no test-only timing hook** — use the real
`execute_business` gate + the `_send` transport seam.

## 6. Precise state & transaction behavior

- **Phase 1 (`action_disconnect`, RPC, atomic):** if `connected` → `disconnecting`,
  bump epoch, `disconnect_status='requested'`, stamp, one non-blocking A/B sweep,
  `controller._trigger()`, return "request accepted". No job-row blocking write; no
  main-cursor commit. Refuse if already `disconnecting`/`disconnected` (audited
  no-op).
- **Admission (`execute_business`):** side cursor → fresh gate read → token read
  once → lease INSERT+COMMIT (linearization) → `_send(store, body, token)` →
  Phase-B reconciliation → lease DELETE+COMMIT (finally: release/expire).
- **Controller (`_run_disconnect_quiesce`, one store/invocation):** select one
  `disconnecting` store under store-row SKIP LOCKED; reap expired leases; A/B
  sweep; count live leases; write escalation snapshot; finalize (0) / `quiescing`
  (within timeout) / timeout-finalize; `_trigger` if more stores remain.

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
`job`; only business entry. `execute_lifecycle(store, query, variables=None,
purpose=...)` — fixed purpose enum with an allowed-state matrix (analysis §9.1).
Public `execute()` removed/private. Call-site inventory + migrations: analysis
§9.3 (core store test-connection → lifecycle; product + customer importers →
business, threading `job`).

## 10. Single token snapshot

Token read **once** during admission (in the side txn), held in memory, passed to
`_send(store, body, token)`; no second lookup; never persisted (not in lease/log);
redacted in errors. `_send` signature change is authorized (supersedes the rev-2
no-change restriction).

## 11. Lifecycle state matrix

Frozen in analysis §8: disconnect one-way; lifecycle mutations refused during
`disconnecting`; generation bumps on every successful activation/reconnect. T-13/
T-14 map to exact rows.

## 12. Timeout / escalation

Lease-based (§16 analysis): timeout finalizes + clears credential; admitted holders
finish with in-memory token; escalation snapshot (`disconnect_open_lease_count`,
`disconnect_oldest_admitted_at`, opaque lease_keys / Integer job_ids) + audit job;
never write a locked job row; no secret stored.

## 13. Controller transaction & scheduling

One store per cron invocation/transaction (store-row SKIP LOCKED selection); no
explicit main-cursor commit; `_trigger` next store; duplicate triggers idempotent;
crash recovery via durable `disconnecting` + `nextcall` + lease expiry.
`priority=0` = prioritization, **not** a dedicated slot; completion is an SLA under
a healthy scheduler, **not** a wall-clock guarantee; safety (epoch gate) is
immediate; controller health exposed via `disconnect_status`.

## 14. Source-level guards

- No `cr.commit()` on the request/main cursor; side-cursor writes via a `with`
  block, always committed/closed, no leak.
- Lease `store_id` is a store M2o; `job_id` is a plain **Integer** (no job FK →
  no `KEY SHARE` lock on a drain-locked job row).
- Timeout writes only store fields + a new audit job; never a running/claimed job
  row or its log; `blocked_manual_review` not overloaded.
- No advisory lock. No new model-layer mutating `sudo()` beyond what the lease
  create/read requires under an explicit ACL (respect the CORE-R1 three-site
  inventory; the lease writes go through normal ACL, not a broad `sudo()`).
- Token memory-only; `_send` receives the snapshot; no second `_get_access_token`.
- Source-level test asserts public `execute()` is gone and that a business call
  without a valid `job`/epoch fails closed.

## 15. Genuine concurrent tests (real mechanism, real gate)

T-1…T-16 (analysis §24): disconnect-before-admission → no `_send`; admission-
before-disconnect finishes; **≥2 concurrent admitted calls on one store**;
claimed-but-not-started cannot admit; second call blocked; **token read once**;
worker-crash lease reaped; no serialization failure; multi-store isolation;
two-server; one-store-per-controller-transaction; duplicate-trigger idempotency;
lifecycle matrix; cron-delay safety; rollback preconditions. Real `execute_business`
gate + `_send` transport seam; no live Shopify; no monkeypatch; no timing hook.

## 16. Odoo.sh validation

Per SRR-06, capture a verbatim green summary of the full `shopify_connector_core`
suite in `docs/05-qa/task-core-r2-validation-results.md`.

## 17. Ordered rollback (replaces simple revert)

1. Disable/stop the controller `ir.cron`.
2. Prevent new `disconnecting` transitions (guard the new path).
3. Normalize every `disconnecting`/`timed_out` store to a supported old state
   (cleared-credential → `disconnected`; else → `connected`/`reconnect_needed`).
4. Delete active `call.lease` rows.
5. Preserve/archive lifecycle audit jobs.
6. Revert code/data (state value, fields, cron, lease model, guarded entries,
   `_send` param, the two domain call-site edits).
7. Verify no unsupported `state` value, no orphan controller trigger, no orphan
   leases remain.

Retain the added columns/lease table **inertly** (recommended) or drop by a later
migration; never revert before steps 1–5.

## 18. Definition of done

- All §15 tests pass, incl. ≥2-concurrent-admitted, token-read-once,
  crash-lease-reap, one-store-per-controller-transaction, and no-serialization-
  failure; Odoo.sh green captured.
- INV-1…INV-9 demonstrated; INV-2 proven at the real `execute_business` gate; INV-3
  proven via committed leases (not `running` count).
- Only §4 files changed; the two domain edits are call-site-only; no forbidden
  file/line touched.
- No main-cursor `cr.commit()`; no advisory lock; token memory-only; no secret in
  lease/log; timeout writes no locked job row.
- Ordered rollback documented and its preconditions tested where feasible.
- Validation record + register/handoff/AR updates written; SRR-03 recorded as
  *remediated (pending residual multi-host proof)* only after green; SRR-04/09
  unchanged.
- Draft PR; not merged/ready without ChatGPT review.

## 19. Future PR requirements

The implementation PR body must include: the gate act id; verified base SHA; exact
changed files (incl. the two named domain call sites); the lease mechanism +
atomic-admission + single-token design; the invariant→test mapping incl.
multiple-admitted-calls, token-read-once, crash-reap, and controller-transaction
cases; the two-server evidence; the verbatim Odoo.sh green summary; residual risks
(RR-1…RR-6); the ordered rollback; confirmation SRR-03 is only *remediated pending
live proof*, SRR-04/09 REDUCED, and no other gate opened. Draft until review.

---

> **Gate status: CLOSED.** This packet plans the work; it does not authorize it.
> No `addons/**` file may change until ChatGPT issues the CORE-R2 gate act naming
> the base SHA and re-freezing the allowed-file list.
