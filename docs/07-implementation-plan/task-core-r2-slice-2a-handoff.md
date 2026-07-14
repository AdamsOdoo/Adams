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

## 5. Remaining Slice-2B work (NOT authorized here)

- Product importer call-site migration to `with execute_business(job, …)` around
  its call **and** reconciliation (`shopify_connector_product`).
- Customer importer call-site migration (`shopify_connector_sale`).
- Removal/privatization of public `execute()`; collapse of its double token read.
- Wiring `execute_lifecycle(purpose='reconnect_probe')` for reconnect **from the
  `disconnected` state** — the test-connection matrix (faithful to analysis §9.1)
  excludes `disconnected`, so reconnecting a re-credentialed disconnected store
  should use `reconnect_probe` (a reconnect change, deferred; see the known
  limitation below).
- Credential-**replacement** refusal during `disconnecting` — the matrix (§8)
  refuses it, but enforcing it requires a change to
  `shopify_connector_store_credential.py` beyond the Slice-2A "clear-ordering
  only" authorization; deferred (safe meanwhile: the epoch gate fail-closes all
  business admission during `disconnecting`, and any credential set during
  `disconnecting` is cleared at finalize).
- Genuine two-server / deployed multi-worker linearization proof (T-19; SRR-09).
- Live/dev-store Shopify validation (still gated).

## 6. Known limitation carried into Slice 2B

`action_reconnect` still probes via `action_test_connection`
(`purpose='test_connection'`), whose accepted matrix excludes `disconnected`.
After a completed disconnect the credential is cleared, so a plain reconnect
early-returns (no probe); but a store that had a credential re-entered while
`disconnected` would now be refused at the probe (previously it made the call
via `execute()`). This is faithful to the analysis matrix (reconnect from
`disconnected` should use `reconnect_probe`), untested by the existing suite, and
deferred to the reconnect/call-site slice above. Flagged, not silently shipped.

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
