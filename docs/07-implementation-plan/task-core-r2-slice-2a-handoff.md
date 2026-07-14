# CORE-R2 — Foundation Slice 2A — Session Handoff

> **Session-specific handoff (per the Slice-2A gate §9).** Docs-only handoff for
> the disconnect lifecycle / quiescence controller / timeout finalization /
> credential-clear-ordering slice. This file does **not** update the shared
> `research-handoff.md`, `architecture-review-log.md`, or
> `sync-engine-risk-register.md` (forbidden in this parallel session).

## 1. Identity

- **Task:** CORE-R2 Foundation Slice 2A — two-phase disconnect lifecycle,
  quiescence controller, direction-C timeout finalization, credential-clear
  ordering.
- **Architecture:** AR-047. **Foundation validation:** AR-047 (Slice 1, PR #156).
- **Base SHA:** `Shopify-connector` @
  `912801508155c6358e8f5f1a7a0aaf01ae573675` (merge of PR #156). Verified equal
  to the local `HEAD`, `origin/Shopify-connector` tip, and the base of open
  draft PRs #150/#151.
- **Branch:** `claude/core-r2-foundation-slice-2a-mr7uwq` (environment-assigned;
  the gate's preferred `claude/core-r2-slice-2a-disconnect-controller` is
  superseded by the assigned branch, per the gate's "remain on that assigned
  branch" clause).
- **Final head:** the tip of the above branch after push — recorded exactly in
  the draft PR body and the session final report (this handoff is committed
  within that same commit, so it cannot embed its own SHA).
- **Merged predecessor:** PR #156 (Slice 1). **Related frozen PRs:** #150
  (Task 011B), #151 (Task 010B) — untouched, still draft/unmerged.
- **Separate issue:** #157 (base `res_users.notification_type` fixture artifact) —
  out of scope, untouched.

## 2. Implementation summary

The lifecycle/controller half of CORE-R2 on top of the merged admission-lease
foundation, **without activating any product/customer business call site**:

- **Store (`shopify_connector_store.py`):** new `disconnecting` state; the
  `disconnect_status`/`_status_reason`/`_open_lease_count`/`_oldest_admitted_at`/
  `_requested_at`/`_by`/`_completed_at` fields; the generation-changing lifecycle
  lock `_lock_store_for_lifecycle` (blocking `FOR NO KEY UPDATE`, `store→credential`
  order, no `SKIP LOCKED`, no main-cursor commit) applied to disconnect /
  activation / reconnect with a single epoch bump each; two-phase
  `action_disconnect` (request-only: lock → bump → `disconnecting`/`requested` →
  one non-blocking A/B sweep → wake controller → return; no credential clear, no
  wait, no locked-job write, audited idempotent no-op on repeat); the
  `_run_disconnect_quiesce` controller (one store per invocation via
  `try_lock_for_update(limit=1)`); `_process_disconnect_quiesce` (direction-C
  count of all leases, escalation snapshot, completed/quiescing/timed_out branch);
  `_finalize_disconnect_completed` / `_finalize_disconnect_timed_out` (credential
  clear under the held store lock; timed_out is distinct and cleans residual
  leases only after finalization); the delayed `_trigger(at=now+POLL_DELAY)`
  re-poll; and the `disconnecting` refusals on test-connection / activation /
  reconnect.
- **API client (`shopify_connector_api_client.py`):** new `execute_lifecycle`
  (plain, purpose→state matrix; refuses any lifecycle call while `disconnecting`);
  `action_test_connection` migrated to `execute_lifecycle(purpose='test_connection')`.
- **Dispatcher (`shopify_connector_job_dispatch.py`):** `DISCONNECT_QUIESCE_TIMEOUT`
  (15 min) and `POLL_DELAY` (1 min) constants only.
- **Cron (`data/shopify_connector_cron_disconnect.xml`, new):** the priority-0
  controller `ir.cron` running as `base.user_root`. Registered in `__manifest__.py`
  (version `19.0.1.7.0`).
- **Tests (`tests/test_disconnect_quiescence.py`):** +30 Slice-2A tests
  (4 classes) covering all 24 required scenarios; genuine `db_connect` tests for
  controller selection (locked-first / all-locked).

Full behavioral + static evidence: `docs/05-qa/task-core-r2-validation-results.md`
§S2A.

## 3. Runtime command / test plan (for the Odoo.sh exact-head session)

Run inside the authorized Odoo.sh dev build for the exact pushed head:

```
# Fresh install with tests (canonical clean-DB result):
odoo-bin --stop-after-init -i adams_base,shopify_connector_core,\
  shopify_connector_product,shopify_connector_sale \
  --test-enable --log-level=test \
  --test-tags /adams_base,/shopify_connector_core,\
  /shopify_connector_product,/shopify_connector_sale

# Focused Slice-2A classes:
odoo-bin --stop-after-init -u shopify_connector_core --test-enable --no-http \
  --test-tags /shopify_connector_core:TestDisconnectPhase1,\
  /shopify_connector_core:TestQuiescenceController,\
  /shopify_connector_core:TestDisconnectSourceGuards,\
  /shopify_connector_core:TestDisconnectControllerSelectionGenuine

# Regression on the two migrated files:
#   /shopify_connector_core:TestConnectionLifecycle
#   /shopify_connector_core:TestJobDispatch
```

## 4. Odoo.sh exact-head validation requirements (before any runtime-green)

- Fresh install fully green (`0 failed, 0 error(s)`), excluding the known base
  `res_users.notification_type` post-init-rerun artifacts tracked in issue #157.
- All four Slice-2A classes green, including the genuine-connection selection
  tests (no deadlock, zero residue, no leaked backend/cursor).
- The two migrated files (`TestConnectionLifecycle`, `TestJobDispatch`) green
  under the two-phase contract.
- Leak scan: no token / `Authorization` / GraphQL body / credential value in any
  log; no synthetic residue (`call_lease`, `store`, `job`, `job_log`, trigger).
- Capture a verbatim green summary into
  `docs/05-qa/task-core-r2-validation-results.md`.

## 5. Lifecycle-race correction (review 4690639375) — now part of Slice 2A

The control-room review required these correctness fixes **before** Odoo.sh
runtime; they are implemented and are **not** deferred:

- **Activation/reconnect TOCTOU:** `action_activate` and `action_reconnect`
  finalize the state transition **under** `_lock_store_for_lifecycle`, consuming
  the locked `(state, generation)` and refusing to overwrite a one-way disconnect
  (`disconnecting`, or a changed epoch during the reconnect probe); single epoch
  bump on success. `action_mark_reconnect_needed` is likewise TOCTOU-safe.
- **Reconnect probe:** `action_reconnect` now uses the internal
  `'reconnect_probe'` purpose (permits `disconnected`, so reconnect after a
  completed disconnect works); `action_test_connection` keeps `'test_connection'`
  (still refused from `disconnected`). Both route through the shared private
  `_run_connection_probe`; `execute_lifecycle` is now the **private**
  `_execute_lifecycle` (no RPC-exposed purpose; public surface again
  `{execute, execute_business}`).
- **Credential mutation lock order:** `action_set_token`/`action_replace_token`
  share the private `_mutate_token`, which locks the **store row first**, refuses
  set/replace while `disconnecting`, and bumps the epoch exactly once on a
  connected replacement — `store → credential` order, no new `sudo()`.

## 5b. Probe-snapshot + credential-clear correction (reviews 4690804619 + 4690807427) — now part of Slice 2A

A second control-room pass (on head `415c05c`) required two further correctness
fixes before Odoo.sh runtime; they are implemented and are **not** deferred:

- **One-snapshot lifecycle probe.** The probe binds to exactly one credential
  snapshot via the private client helper `_admit_lifecycle` (single token read +
  credential id/version + store generation + purpose matrix) and issues the
  request through `_send_lifecycle(store, query, token)` with that exact token
  (`_send(store, body, token)` — no transport credential re-read). After the
  network result (success **or** failure), `store._lifecycle_probe_superseded`
  acquires the **store → credential** locks and revalidates state, generation, and
  credential id/version/**value**; a change → the response is discarded and the
  probe job is audited `cancelled` ("superseded"), writing **no** mirror or
  credential state. `_execute_lifecycle` is removed; the public client surface
  stays `{execute, execute_business}`. **No lock spans the network call.**
- **Public/controller credential-clear split.** The controller-only
  `_clear_token_under_store_lock` primitive (no state change, no bump, caller holds
  the lock) is what `_finalize_disconnect_completed`/`_timed_out` call under the
  held store `FOR UPDATE`. Public `action_clear_token` now locks the store first
  and routes: `disconnecting` → refused; `connected`/`reconnect_needed` → the
  accepted two-phase `action_disconnect` request (shared
  `_request_disconnect_locked`, one epoch bump, **nothing cleared now**;
  clarification 4690807427); `setup_incomplete`/`disconnected` → direct clear.
- **Disconnect generation.** `action_disconnect` and the clear routing share
  `_request_disconnect_locked`, which writes `connection_generation =
  locked_generation + 1` from the value returned under the lock (review §11).

Files touched by this correction: `api_client.py`, `store.py`,
`store_credential.py`, `tests/test_disconnect_quiescence.py`,
`tests/test_api_client.py`, `tests/test_credential_service.py`,
`tests/test_connection_lifecycle.py`, `__manifest__.py` (version
`19.0.1.7.1`), `tests/test_api_client.py` (client-unit tests; already in the
Round-2 allow-list), and — as packet-§4 minimal transport-seam regressions flagged
for ratification — `tests/test_test_connection.py` and
`tests/test_readiness_slot_closure.py` (their `_send` fakes now accept the token
argument; no assertion changed). Net PR scope: 15 files. Full evidence:
`docs/05-qa/task-core-r2-validation-results.md` §S2A-C2.

## 5c. Atomic lifecycle admission + genuine race tests (review 4691182306)

A third control-room pass (on head `756684d`) required two further correctness
fixes before Odoo.sh runtime; both are implemented and **not** deferred:

- **Atomic lifecycle admission (defect 1).** `_admit_lifecycle` no longer takes a
  plain main-cursor/cached snapshot. It now captures the snapshot in one short
  **owned side transaction** — the same accepted mechanism as business `_admit`,
  minus any lease: open `registry.cursor()`, `SELECT state, connection_generation
  … FOR SHARE` on the store row (the linearization lock, conflicts with the
  lifecycle `FOR NO KEY UPDATE`), re-check the purpose→state matrix on the locked
  value, read the token exactly once and capture the credential id/version, then
  `commit`/`close` **before** the network call. So a disconnect that wins before
  the `FOR SHARE` is refused under the lock (no transport issued — the exact hole
  the review named), and one that wins after is caught by the unchanged
  post-network `_lifecycle_probe_superseded` revalidation. `_run_connection_probe`
  routes an under-lock `UserError` to *superseded* and a missing-credential
  `ShopifyClientError` to *failure*, both without any network. No lock spans the
  network call; no `call.lease` is created; no main-cursor commit.
- **Genuine independent-transaction race tests (defect 2).** Added
  `TestLifecycleAdmissionSourceGuards` (source guards for the side-transaction
  admission), `TestLifecycleAdmissionRaceGenuine` (both orders across distinct
  backend PIDs: disconnect-first → zero transport; admission-first → old token
  then superseded, no mirror; a store-row lock-attribution proof; and a threaded
  genuine-simultaneity proof via the accepted `Registry._lock` bounded-window
  pattern), and `TestPublicClearAdmissionRaceGenuine` (business-admission-first →
  clear deferred, credential cleared only at controller `completed`, one
  generation bump; public-clear-first → old-generation admission fails closed,
  no lease, no transport, credential preserved until finalization). The prior
  `TransactionCase` supersession/clear tests are retained and re-documented as
  **controlled seam-injection** tests (not genuine concurrency).
- **Test-mode seam-compat (packet §4, control-room-approved).** Because the
  atomic admission opens an owned `registry.cursor()` side transaction, every
  probe-driving test class enters **registry test mode** (the mechanism
  `TestBusinessAdmission` uses for business `_admit`) so the production side cursor
  sees the fixture — **no assertion changed**. This extends the ratified §4
  seam-compat class to `test_connection_lifecycle.py` (approved for this round)
  plus the test-mode line on the two already-ratified seam-compat files.
  `test_readiness_check.py` is untouched (it never drives the probe).

Files touched by this correction: `models/shopify_connector_api_client.py`,
`models/shopify_connector_store.py`, `__manifest__.py` (version `19.0.1.7.2`),
`tests/test_disconnect_quiescence.py`, `tests/test_api_client.py`,
`tests/test_test_connection.py`, `tests/test_readiness_slot_closure.py`,
`tests/test_connection_lifecycle.py`, and the two docs. **No new file** enters the
PR; `store_credential.py`/`job_dispatch.py` were not needed (the existing
`_lifecycle_credential_version` serves the side-transaction snapshot). Net PR
scope stays **15** files. Base re-aligned to `Shopify-connector`
`1494b97d0e2117af05b954dabde92a9e497ac2c3` via a normal merge commit. Full
evidence: `docs/05-qa/task-core-r2-validation-results.md` §S2A-C3.

## 6. Remaining Slice-2B work (NOT authorized here)

- Product importer call-site migration to `with execute_business(job, …)` around
  its call **and** reconciliation (`shopify_connector_product`).
- Customer importer call-site migration (`shopify_connector_sale`).
- Removal/privatization of public `execute()`; collapse of its double token read.
- Genuine two-server / deployed multi-worker linearization proof (T-19; SRR-09).
- Live/dev-store Shopify validation (still gated).

## 7. Rollback notes

Because no production business call site is activated, no real lease holder can
exist yet, so a **plain code revert of this slice is safe** (like Slice 1). If a
later slice has activated `execute_business`, follow the packet §17 **ordered,
zero-holders** rollback instead:

1. disable new disconnect requests (feature-guard `action_disconnect`);
2. disable new business admissions (`execute_business.__enter__` fail-closed);
3. stop/drain the drain + controller crons; let every admitted handler finish
   (its `__exit__` releases its lease), including any `timed_out` holder still
   finishing with an in-memory token;
4. prove zero holders (`count(call.lease) == 0` **and** no worker inside an
   `execute_business` context); if non-zero, return to step 3;
5. normalize store states (cleared-credential → `disconnected`; else →
   `connected`/`reconnect_needed`); no unsupported `state` value remains;
6. preserve audit history (lifecycle audit jobs / logs — never deleted);
7. only then remove/deactivate the controller cron, the `disconnecting` state
   and `disconnect_*` fields, and the lifecycle lock/controller code.

A normal code revert must **not** assume destructive column/table cleanup — the
additive columns and the `call.lease` table may remain inert; drop them only by a
later migration, never as a prerequisite of the revert.

## 8. Explicit stop condition

Slice 2A is complete when the draft PR is opened against `Shopify-connector` with
the evidence above. **Stop after opening the draft PR and reporting.** Do **not**:
mark the PR ready; merge it; begin Slice 2B (call-site migration); remove public
`execute()`; touch product/sale; run live Shopify validation; or modify the
shared handoff / architecture-review-log / risk-register. **SRR-03 remains OPEN**
and no runtime-green is claimed. Await ChatGPT control-room review — including
ratification of the two migrated test files (§S2A.3 of the validation record).

## 9. Exact-head Odoo.sh runtime validation — session 2026-07-14 `[Fact]`

Full runtime record: `docs/05-qa/task-core-r2-validation-results.md` §RT.0–RT.14.

- **Validated code SHA:** `79dbfc00428802da8c98c97d3e6d7eb6025ea74e` (tree clean;
  base `1494b97…` is the merge's 2nd parent). **Build 34872373**, DB
  `adamsmen-…-34872373`, Odoo 19.0 / PostgreSQL 16.14 / ORM cursor **REPEATABLE READ**.
- **Docs-only evidence commit:** this handoff + the RT section are committed **after**
  the validated SHA and are **not themselves runtime-tested** (evidence only).
- **Scope:** exactly the 15 accepted files; no product/sale/010B/011B/#157 change; no
  live token in the diff.
- **Fresh install (build `install.log`, authoritative):** core `4 failures / 0 errors
  of 282` + `19 post-tests, 0 failed`. The **4 failures are TEST DEFECTS** — naive
  `assertNotIn(token, getsource(...))` source-guards matching the method's own
  **docstring** (`sudo(`, `SKIP LOCKED`, `action_clear_token`, `call.lease`); a
  non-invasive AST proof shows `ALL_PRODUCTION_CODE_CLEAN = True` (tokens only in
  docstrings). Production behaviour is correct.
- **Genuine `post_install` classes ×3 (all green):** `TestGenuineRealAdmission` (9),
  `TestCredentialReplacementRaceGenuine` (2), `TestDisconnectControllerSelectionGenuine`
  (2), `TestLifecycleAdmissionRaceGenuine` (4), `TestPublicClearAdmissionRaceGenuine`
  (2) — 15 distinct processes, `0 failed, 0 errors` each. Sections 7/8/10/11 race,
  controller/timeout, and registry test-mode assertions verified as non-vacuous.
- **Issue #157 confirmed, NOT a PR #160 defect:** the `res.users.notification_type`
  NOT-NULL errors seen only on the `-u` at-install re-run are exactly the known
  **issue #157** base-fixture / post-init-rerun artifact (§1, §4). Proven: fresh `-i`
  build had 0 such errors; `odoo-bin shell` creates users fine; it strikes **non-PR**
  classes (`test_credential_access`, `test_job_log_system_append`) identically.
  **Not fixed** (out of scope, per the task).
- **Section 9 (isolation/retry):** REPEATABLE READ proven at runtime; the deterministic
  READ COMMITTED supersession test is green ×3; Odoo 19's `service/model.py:retrying`
  (SERIALIZATION_FAILURE, MAX_TRIES=5) verified from **official source**. Open: no
  connector test forces a REPEATABLE READ 40001 + framework retry (b/c/e) — a
  narrowly-scoped test in `tests/test_disconnect_quiescence.py` would close it.
- **Cleanup/leak:** zero store/credential/lease/job/job_log residue; 0 idle-in-tx
  backends; 0 connector cron-trigger residue; disconnect+drain crons active once;
  secret scan of all logs clean.
- **Base→head genuine upgrade:** NOT performed — single-DB container, restricted role
  (no `CREATEDB`), 1 GB cap; additive-safety analysis provided instead (not a
  substitute). REMAINING GATE.

**Remaining gates (control-room-gated; none producible this session — webhook held):**
(1) test-only fix of the 4 source-guard docstring false-positives; (2) genuine base→head
upgrade on a multi-DB runtime; (3) optional Section-9 REPEATABLE READ/40001 retry test;
(4) optional Section 7/8 assertion tightening + stale `_admit` docstring.

**SRR-03 remains OPEN.** PR #160 stays **draft/unmerged**; Slice 2B not begun; no live
Shopify request; issue #157 untouched. Await control-room decision.

## 10. Test-only source-guard + service-retry correction (review 4692156428) `[Fact — NOT runtime-tested this session]`

Control-room **runtime** review `4692156428` (after static acceptance
`4691652645`) required a narrow **test-only** correction of the RT.0–RT.14
exact-head record. Full detail:
`docs/05-qa/task-core-r2-validation-results.md` §S2A-C.0–C.4.

- **Historical evidence preserved.** Build **34872373** remains the exact-head
  runtime evidence for the **production** SHA `79dbfc0`. The add-on tree at the
  corrected head is **byte-identical** to `79dbfc0`; the RT record is unchanged.
- **The four RT.3 fresh-install failures were TEST DEFECTS** (naive
  `assertNotIn(token, getsource(method))` guards matching the method's own
  docstring — `sudo(`, `SKIP LOCKED`, `action_clear_token`, `call.lease`). Each
  guard is now **executable-AST**, docstring-robust, with **every original safety
  assertion preserved** (no always-pass weakening). A new `TestSourceGuardDetectors`
  class proves each detector both FIRES on real unsafe executable code and IGNORES
  a docstring-only mention.
- **Genuine service-retry proof (closes the RT.8 gap).** New opt-in `post_install`
  `TestLifecycleServiceRetryGenuine.test_repeatable_read_serialization_retry_issues_one_transport`
  drives the **real** `odoo.service.model.retrying(func, env)` at the normal
  REPEATABLE READ isolation: a concurrent `action_disconnect` committed on an
  independent backend forces the post-network `FOR NO KEY UPDATE` revalidation to
  raise a **genuine SQLSTATE 40001**, which the real retry handles; the retried
  attempt is matrix-refused before transport, so **exactly one** transport occurs.
  No injected serialization, no fake retry loop, production isolation not weakened,
  no main-cursor commit; only the retry backoff is patched.
- **Files changed (test-only):** `tests/test_credential_service.py`,
  `tests/test_disconnect_quiescence.py` (+ this handoff and the validation record).
  **No production / XML / manifest / security / cron file changed.**
- **A new committed head requires a new Odoo.sh build.** The corrected head is a
  **new commit**, so the RT record does not transfer to it; a **new exact-head
  Odoo.sh build + full revalidation from RT.1** is REQUIRED. **This correction is
  NOT runtime-tested in this session.**
- **Static (this session):** `py_compile` + `compileall` OK; exact changed-file
  inventory; conflict-marker scan clean; AST detector self-tests pass (verified
  with the file-defined helpers against the real production source); no new
  token/PII literal; no live Shopify URL/request; synchronous adversarial review
  found no confirmed defect in the allowed files.
- **Base→head genuine upgrade remains OPEN** (RT.4). **Issue #157 remains
  separate and untouched.** **SRR-03 remains OPEN.** PR #160 stays
  **draft/unmerged**; Slice 2B not begun. No runtime-green of the corrected head
  is claimed. Await control-room review.
