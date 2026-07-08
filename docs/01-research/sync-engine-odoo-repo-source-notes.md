# Sync Engine Odoo and Repo Source Notes

## Scope

This document is **Odoo 19 / existing-repository substrate research for Task
006A-2** ("Odoo and Existing Repository Substrate Research for the Sync
Engine"). It is **research only**: it inspects what the merged Task 005
codebase already provides, and what official Odoo 19 documentation/source
says about the mechanisms a future sync engine would sit on
(scheduled actions, transactions, constraints, locking, logging). It:

- makes **no architecture decision** and creates **no DEC file**,
- proposes **no implementation scope** and authorizes **no code**,
- does not modify `docs/01-research/research-handoff.md` (forbidden for this
  session) or any `addons/**` file,
- separates **Fact** / **Inference** / **Open question** throughout, per
  `CLAUDE.md` §8.

Baseline confirmed before writing: `origin/Shopify-connector` HEAD is
`9247fea3c36afdb761a82678f3e5e66e8ef42e87` (PR #122 merge — "Task 005
closure: docs-only record of PR #121 merge"), and this session's branch is
built directly on that commit (`git merge-base --is-ancestor` confirmed
ancestry; no divergent commits before this session's own).

## Repository source inventory

### Required files

| Path | Relevant models/classes/functions | Current behavior | Sync-engine relevance | Confidence |
| --- | --- | --- | --- | --- |
| `addons/shopify_connector_core/models/shopify_connector_job.py` | `ShopifyConnectorJob` (`_name='shopify.connector.job'`); module constants `JOB_STATE_SELECTION` (L6-17, 10 states), `TERMINAL_JOB_STATES` (L19, 4 states), `BUSINESS_JOB_SOURCES` (L28-30, 5 sources), `MANUAL_REVIEW_SUBREASON_SELECTION` (L35-45), `ERROR_CLASS_SELECTION` (L47-59, 16-class registry); `create()` (L191-213), `write()` (L215-248), `_compute_idempotency_key` (L250-269), `_compute_operation_scope_key` (L271-297), two `@api.constrains` (L299-323) | `create()` gates any `job_source` in `BUSINESS_JOB_SOURCES` on `store.state == 'connected'`; `write()` re-gates the same set at the moment `state` transitions to `'running'`, evaluating the *effective* post-write `job_source`/`store_id` (incoming `vals` value if present, else current), not a stale pre-write read — closes a same-call identity-change bypass. Two `models.Constraint` UNIQUE rows (L171-178): `(store_id, idempotency_key)` and `(store_id, operation_scope_key)`. `operation_scope_key` computes to `False` once a job is terminal or superseded (L282-287), so the scope-key uniqueness only ever blocks a second *non-terminal* job for the same target. | The literal job/state-machine substrate a sync engine's orchestration layer would enqueue/execute against. `idempotency_key`/`operation_scope_key` are a real, working single-active-operation guard, not a general checkpoint/resume or first-sync-dedup mechanism (see Current gaps). `job_source` already anticipates domain sync sources (`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`, `odoo_event`) that **no code creates jobs with yet** (confirmed by grep: no caller in `addons/` creates a job with any of those five sources). | High (verbatim source read) |
| `addons/shopify_connector_core/models/shopify_connector_job_log.py` | `ShopifyConnectorJobLog` (`_name='shopify.connector.job.log'`); `_system_append()` (L65-95) | Append-only child of `job`, `ondelete='restrict'` (never `cascade` — log rows are audit history, not disposable children). `_system_append()` is the **sole sanctioned write path**: no ACL group holds `perm_create` on this model by design, so every row is written via this method's one `sudo()` call (the only `sudo()` in this file); every free-text argument (`message`/`technical_detail`/`payload_snapshot`) is redacted before `create()`. | The audit/observability substrate future sync jobs will log `attempt`/`state_change`/`verification_read`/`manual_action`/`note` events to. No batching, streaming, retention, or size-bounding design exists yet for `payload_snapshot`/`technical_detail` (both plain `Text`). | High |
| `addons/shopify_connector_core/models/shopify_connector_store.py` | `ShopifyConnectorStore`; `action_test_connection()` (L87-211), `_create_lifecycle_audit_job()` (L217-249), `action_activate()` (L251-326), `action_disconnect()` (L328-366), `action_reconnect()` (L368-446), `action_mark_reconnect_needed()` (L448-464) | `store.state` selection: `setup_incomplete` / `connected` / `reconnect_needed` / `disconnected`. `action_activate()` raises `UserError` **before any write** if any of a six-step evidence chain fails (credential present → credential row exists → `credential_last_verified_at` truthy → last test-connection `pass` → last readiness in `pass`/`warning` → readiness not older than verification) — no partial-write risk on that path. `action_disconnect()` is idempotent, cancels every non-terminal business job (never deletes), leaves core/terminal jobs untouched. `action_reconnect()`'s missing-credential branch was specifically revised during PR #121 review to **not** `raise` after writing `state='reconnect_needed'` and creating the audit job — because (per `docs/01-research/research-handoff.md`'s PR #121 "reconnect transaction-safety fix" entry, not modified by this session but read for context) "in normal Odoo RPC/service execution a raised exception can roll back ORM writes made earlier in the same call." | `store.state` is the exact gate a future sync engine's job creation/execution must keep honoring. `_create_lifecycle_audit_job()`'s fresh-UUID4-nonce-per-audit-job idiom is the same anti-collision pattern TD-001 fixed for `core_readiness_check` — any new "system-generated, target-less" job type will need the same treatment. The `action_reconnect()` revision is a **repo-evidenced, not independently-Odoo-doc-cited** transaction-safety lesson (write-then-return, not write-then-raise) — see Odoo official/source facts §Transactions for the independently-verified general rule this lesson is consistent with. | High |
| `addons/shopify_connector_core/models/shopify_connector_readiness_check.py` | `ShopifyConnectorReadinessCheck` (`models.AbstractModel`, no table); `run_for_store()` (L78-126), `_aggregate()` (L132-157), `_get_checks()` (L163-183), nine `_check_*` methods (L193-386) | Stateless registry/service. `run_for_store()` creates one `core_readiness_check` job per run with a fresh UUID4 `payload_hash` nonce (the TD-001 fix, scoped only to this job type). `_aggregate()` is fail-closed: any essential check not `pass` (incl. `not_proven`) → overall `fail`; all essential pass but any warning-tier not `pass` → `warning`; else `pass`. `_get_checks()` is an explicit, already-tested domain-extension seam (`test_extension_seam_registers_check_without_modifying_core`) via classic Odoo `_inherit` + `super()._get_checks(store)` + append. Three of the nine checks are literally, in their own docstrings, "registered pending slot only": `_check_webhook_hmac` (L321-327, "not implemented yet"), `_check_mapped_location` (L329-343, "requires a future domain module"), `_check_cron_queue_health` (L345-352, "not implemented yet"). | `_check_cron_queue_health`'s own docstring is direct repo evidence that no cron/queue implementation exists anywhere yet. `_get_checks()`'s inheritance-append-only pattern is a proven precedent for how a future "domain-neutral handler registry" (a named gap below) could be shaped — though it registers *checks*, not *sync operations*, so the pattern needs adaptation, not reuse verbatim. | High |
| `addons/shopify_connector_core/models/shopify_connector_store_credential.py` | `ShopifyConnectorStoreCredential`; `action_set_token()` (L68-108), `action_replace_token()` (L110-145), `action_clear_token()` (L147-173), `_get_access_token()` (L175-190) | Admin-only ACL model; `access_token` additionally carries field-level `groups=`. `action_set_token()`/`action_replace_token()` both clear `credential_last_verified_at` on every set/update and, if the store is `connected`, move it to `reconnect_needed`. `action_clear_token()` moves a `connected`/`reconnect_needed` store to `disconnected`, preserving the credential row and its history (MBQ-08 posture — never deletes). `_get_access_token()` is the sole sanctioned `sudo()` in this file, never logs/returns the token, and per its own docstring is "invoked only by the future API client" outside tests. | Establishes the pattern that any credential mutation must fan out to invalidate *dependent derived state* (`store.state`), not just its own verification mirror — a pattern a sync engine's own credential-dependent caches (e.g. a cached scope/health check) would need to replicate if it ever caches evidence derived from the credential. | High |
| `addons/shopify_connector_core/tests/` (9 files, 2,410 lines, ~100 `def test_*` methods, all `TransactionCase` except `test_redaction.py`'s plain `unittest.TestCase`) | `TestCredentialService`, `TestCredentialAccess`, `TestJobLogSystemAppend`, `TestApiClient`, `TestTestConnection`, `TestRedaction`, `TestConnectionLifecycle` (largest, L17-759, ~50 methods), `TestReadinessCheck` (L12-423, ~30 methods) | `docs/05-qa/task-005-validation-results.md` records a **live Odoo.sh** run (real Odoo 19 + PostgreSQL registry, not local/simulated) at the merged PR #121 head commit: `0 failed, 0 error(s) of 41 tests` for the focused `TestConnectionLifecycle` class, and `0 failed, 0 error(s) of 123 tests` for the full `shopify_connector_core` suite. This session did **not** re-execute the suite (no Odoo runtime available in this session's container either) — the "0 failed / 123 tests" figure is reported here strictly as repo-documented evidence, not independently re-verified. `TestConnectionLifecycle` covers activation gate ordering and every stale-evidence rejection path (L127-350), disconnect job-cancellation scoping (L401-482), business-job enqueue/execution gating including same-write `job_source`/`store_id` identity-change edge cases (L484-585), and reconnect evidence-based transitions incl. a no-double-audit edge case (L606-742). `TestReadinessCheck` covers the TD-001 regression (`test_td001_repeated_readiness_job_does_not_collide`, L33-55), fail-closed aggregation (L81-114), and the extension seam (L184-212). `TestJobLogSystemAppend` proves the sole-write-path/`sudo()`-count/redaction guarantees. | A future sync engine's own test suite would need the same live-runtime validation discipline — `docs/04-decisions/DEC-024-task-005-closure.md` §4 records that **static review and `py_compile` across three PR revisions missed two real runtime defects** that only live Odoo.sh execution caught (see Odoo official/source facts §Transactions and §Constraints for the independently-verified mechanisms behind both). | High for repo content; the pass/fail result itself is repo-documented, not re-executed this session |
| `docs/04-decisions/DEC-022-task-005-scope.md` | — | **Status: Accepted** (gate-opening level, 2026-07-08). Scopes Task 005 as "Connection lifecycle actions." Explicit (L5-10): "Does not authorize any code by itself. Does not fully resolve MBQ-05. Does not pass VAL-B2. Does not fix TD-002." Disconnect cancels non-terminal business jobs, preserving history (§Acceptance note); `perm_create` remains closed for Task 005. | Confirms the exact scope boundary Task 005 delivered — nothing about a sync engine, retry scheduler, or domain sync was in scope. | High |
| `docs/04-decisions/DEC-024-task-005-closure.md` | — | **Status: Accepted.** Records Task 005 complete/merged: PR #121, merge commit `8f2d7846fb70ecb62d2353c3f18ca3bbcbb96e82`. §3 "Explicit non-decisions": no OAuth, no setup wizard, no UI, no domain sync, **VAL-B2 not passed**, **MBQ-05 not resolved**, **TD-002 not closed**, no security/ACL change. §4 "Lessons learned from runtime failures": (a) a `credential.write_date > credential_last_verified_at` freshness guard passed all static review but failed live on Odoo.sh because it depended on real Postgres `write_date` write-timing behavior no static check exercises — the guard was removed; (b) credential mutation must invalidate **both** verification evidence and derived `store.state`, not just the mirror. §5 names four **unselected** next-task candidates, including verbatim "**Task 006 — sync engine skeleton gate.**" | Directly the closest prior document to this task's subject; explicitly leaves "sync engine skeleton" as one of four undecided candidate next tasks — this document does not treat any of them as chosen, and neither does this research. | High |
| `docs/05-qa/task-005-validation-results.md` | — | Live Odoo.sh runtime validation record: "Runtime: Odoo.sh branch shell (live Odoo 19 + PostgreSQL registry, not a local or simulated environment)"; commands used (L54-70); results (L72-84, "0 failed, 0 error(s)" for both runs); "Earlier failures and final fixes" (L86-124) — the same two real defects DEC-024 §4 summarizes, described here with the specific failing test names; "What this does not prove" (L126-147) explicitly disclaims VAL-B2/MBQ-05/TD-002/OAuth/wizard/UI/domain-sync/security-change claims. | The authoritative source for "existing tests and what they prove" above; also the clearest repo statement that **live-runtime testing, not static review, is what actually validated Task 005** — directly relevant to how a sync engine's own correctness claims should eventually be evidenced. | High |
| `docs/05-qa/technical-debt-register.md` | TD-001, TD-002 rows | **TD-001: Resolved** (PR #115) — `core_readiness_check` job creation now uses its own fresh UUID4 `payload_hash` nonce, mirroring the `core_test_connection` pattern, so a second readiness job for the same store no longer collides on `store_idempotency_key_uniq`. **TD-002: Open** — `REQUIRED_MVP_SCOPES` includes `read_fulfillments`, but current official Shopify docs indicate that scope governs only the `FulfillmentService` resource, not `Fulfillment`/`FulfillmentOrder` read access (which `read_orders` and/or `FulfillmentOrder`-family scopes actually cover); routed to the future fulfillment domain task once the fulfillment API model (`FulfillmentOrder` vs. legacy `Fulfillment`) is decided. | TD-001's fix pattern (per-job-type fresh nonce, not a general dedup redesign) is a precedent worth naming explicitly for any new target-less job type a sync engine introduces. TD-002 is a live, still-open readiness-check correctness gap a future fulfillment sync module inherits. | High |
| `docs/03-architecture/master-blueprint-open-questions.md` | MBQ-05 row (L458) | **"Status: Partially routed / Open — not Resolved."** The custom-app-creation-surface / token-acquisition-mechanics question. DEC-023 (2026-07-08) accepted only a limited routing: the staged VAL-B2 closure plan, and a Custom Distribution + manual OAuth path for one-store/private/evidence-gathering use only — **not** as a scalable multi-customer architecture. "Blocks implementation: Yes (setup wizard, OAuth, UI, sync); ... still Yes until VAL-B2 passes with live evidence and branch B's scalable-distribution architecture is separately decided." Note: this session read the register's header/status framing and the full MBQ-01 through MBQ-16 rows (the file is 569 lines; only the first ~460 lines plus the MBQ-05 row itself were read in full — the remainder was not re-read this session). | Confirms MBQ-05's open status independently of DEC-022/DEC-024's own restatement of it, with the added detail that it blocks "sync" implementation by name, not just the setup wizard/OAuth. | High for the rows actually read; the register's remaining ~110 lines (MBQ-17 onward) were not re-inspected this session |
| `docs/01-research/research-handoff.md` | — | Rolling log, **11,957 lines / ~755 KB — exceeds this tool's single-read size limit**; inspected via targeted offsets and `grep`, not read in full. Structure is **newest-entry-first** (the top entry, L1-98, is "Task 005 closure — connection lifecycle merged (PR #121) — compact handoff (2026-07-08)"), not strictly chronological-append. That top entry confirms the PR #121 merge commit, restates VAL-B2/MBQ-05/TD-002 as still-open, and points to DEC-024's "Next task candidates." A separate entry (L454-519, "Task 005 PR #121 revision — reconnect transaction-safety fix") records the exact `action_reconnect()` write-then-raise lesson cited above. Earlier sections (~L8432-8517, ~L8720-8789) record prior official-Odoo-source research on `ir.cron`/async-queue-absence/`sudo()`-bypass topics, which `docs/01-research/odoo-official-architecture-notes.md` (below) already consolidates with full citations — this session cross-references rather than re-deriving those. | Confirms this session's understanding of "what Task 005 gives / doesn't give" matches the project's own most recent self-assessment, and surfaces the one directly on-topic transaction-safety lesson cited above. **Not modified by this session** (forbidden file). | Medium-High — read via targeted sampling of an 11,957-line file, not exhaustively |

### Additional files inspected (not in the required list, read for direct-import context only)

| Path | Why inspected | Key fact | Confidence |
| --- | --- | --- | --- |
| `addons/shopify_connector_core/models/shopify_connector_binding_mixin.py` | Directly relevant to "no first-sync dedup design yet" | `ShopifyConnectorBindingMixin` (`AbstractModel`, no table) defines a **shape-only** contract per DEC-013: `store_id`, `shopify_gid`, `status` (`active`/`stale`/`manually_overridden`/`review`), `match_key` (`existing_binding`/`sku_reference`/`barcode`/`email`/`manual`), `matched_by_uid`/`matched_at`, `override_*`. Docstring: "carries no `res_model`/`res_id` pair... Composite uniqueness on `(store_id, shopify_gid)` is enforced per concrete model, not here, since an abstract model has no table of its own." **No concrete binding model exists anywhere in `addons/` yet.** | High |
| `addons/shopify_connector_core/models/shopify_connector_api_client.py` | Directly relevant to "no retry scheduling engine yet" | `ShopifyConnectorApiClient` (`AbstractModel`) is read-only (no mutation-capable method) and explicitly has **no retry loop**, per its own class docstring (L84-88): "no retry loop (retry policy belongs to the job layer, DEC-009)." This is the repo's own explicit statement that retry policy is deferred, by name, to a "job layer" that does not exist in any file inspected. | High |

## Existing substrate facts

- **Job model behavior.** `shopify.connector.job` enforces store-state gating at both **enqueue time** (`create()`) and **execution time** (`write()` to `state='running'`) for a named, closed set of "business" job sources (`BUSINESS_JOB_SOURCES`); core/diagnostic sources (`setup_readiness_check`, `export_preview_dry_run`) are exempt by design, since gating them on `connected` would be circular. Two DB-level UNIQUE constraints back this: `(store_id, idempotency_key)` (permanent, since `idempotency_key` never clears) and `(store_id, operation_scope_key)` (clears to `False` on terminal/superseded state, so it only ever blocks a second concurrent *non-terminal* job for the same target).
- **Job log behavior.** Append-only, single sanctioned write path (`_system_append`), `sudo()`-gated because no role holds `perm_create`, every free-text field redacted before persistence.
- **Store lifecycle/state behavior.** Four states (`setup_incomplete`/`connected`/`reconnect_needed`/`disconnected`); `action_activate()` is evidence-only (never infers from credential presence alone) and fails closed with no partial write; `action_disconnect()` is idempotent and history-preserving; `action_reconnect()` re-runs the existing Task 003/004 substrate and was specifically revised to avoid a write-then-raise transaction-safety risk.
- **Credential lifecycle behavior.** Any token set/replace/clear operation invalidates both the store's verification mirror and, where applicable, its derived `state` — closing the class of bug DEC-024 §4 records as found only via live-runtime testing.
- **Readiness behavior.** Fail-closed aggregation over a fixed, `_inherit`-extensible check registry; three of the nine registered checks are explicit not-yet-implemented placeholders (webhook HMAC, mapped Location, cron/queue health).
- **Existing tests and what they prove.** 123 tests across 9 files, live-validated on Odoo.sh (0 failed/0 errors) at the PR #121 merge commit per `task-005-validation-results.md` — this session did not re-run them. They prove the lifecycle/credential/readiness/job-log/API-client behavior described above at that commit; they do not exercise anything related to a sync engine, cron, retries, or domain sync, none of which exists yet.
- **Current limitations** (repo-confirmed, expanded on in Current gaps below): no `ir.cron`/scheduled-action reference exists anywhere under `addons/` (confirmed by `grep -r 'ir.cron|ir_cron' addons/` returning no matches); no concrete binding/dedup table exists; the API client has no retry loop by explicit design; `job_source` values for business sync (`webhook`, `manual_sync`, `scheduled_sync`, `reconciliation`, `odoo_event`) are declared in the selection field but created by no code path.

## Odoo official/source facts

Facts already verified and dated in this repo's own
`docs/01-research/odoo-official-architecture-notes.md` are **relied upon, not
re-fetched, in this session** — their original access dates (2026-06-30
through 2026-07-04) are preserved below rather than restated as today's date.
Facts newly verified in this session (transactions, constraints, concurrency)
were fetched **2026-07-08** via a dedicated research workflow against
`github.com/odoo/odoo` (branch `19.0`) and `odoo.com/documentation/19.0` /
its raw RST mirror at `raw.githubusercontent.com/odoo/documentation/19.0`.

### Scheduled actions / cron

- **Fact** — Scheduled actions are backed by `ir.cron`; failure handling
  auto-skips after 3 consecutive failures and auto-deactivates (notifying the
  DB admin) after 5 failures spanning ≥7 days; cron functions must batch and
  commit after each batch via `ir.cron._commit_progress(...)`, never
  reschedule themselves.
  (`https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html`,
  accessed 2026-06-30/2026-07-01, per `odoo-official-architecture-notes.md`.)
- **Fact** — The **only** documented background/deferred-execution primitive
  in Odoo 19 core is `ir.cron`; it is poll-based (minute-level precision),
  bounded by `--max-cron-threads` (default 2). The community `OCA queue_job`
  module is **not** part of official Odoo. (Same source, accessed
  2026-06-30/2026-07-02.)
- **Fact** — On **Odoo.sh**, scheduled actions run on a "best effort" basis
  even in production ("we cannot guarantee an exact running time... Do not
  expect any scheduled action to be run more often than every 5 min"), and
  are **disabled entirely on staging/development** branches.
  (`https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html`,
  accessed 2026-07-02.)
- **Fact (new this session, official doc)** — The official "Writing cron
  functions" section of the Scheduled Actions reference gives a worked
  example recommending `record.try_lock_for_update().filtered_domain(domain)`
  as the per-record pattern for a cron batch function to lock a record
  before processing it and re-check it hasn't changed underneath the lock.
  (`raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/backend/actions.rst`,
  §"Writing cron functions"; corresponds to
  `https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#writing-cron-functions`;
  accessed 2026-07-08. `access_status`: Accessible.)
- **Fact (new this session, official source)** — `ir.cron`'s own job
  dispatcher avoids two workers processing the same job simultaneously via
  `IrCron._acquire_one_job(cr, job_id)`, whose query ends in
  `FOR NO KEY UPDATE SKIP LOCKED` — a weaker lock than plain `FOR UPDATE`,
  chosen (per an explicit source comment) because it still conflicts with
  every other lock type except the `KEY SHARE` lock foreign keys implicitly
  take, and cron jobs are never deleted so that conflict is safe to allow.
  `_get_all_ready_jobs()` does the unlocked candidate `SELECT`; only
  `_acquire_one_job()` takes the row lock, one job at a time.
  (`github.com/odoo/odoo/blob/19.0/odoo/addons/base/models/ir_cron.py`,
  `_get_all_ready_jobs` L297, `_acquire_one_job` L308, lock clause L365,
  comment block L324-348; accessed 2026-07-08. `access_status`: Accessible.)
- **Fact (new this session)** — `_acquire_one_job`'s own docstring
  documents that a `psycopg2.errors.SerializationFailure` can legitimately
  occur if another worker already processed the job, and the caller is
  expected to roll back and move on; `_process_jobs_loop` catches exactly
  this. (Same file, docstring L309-321, catch site referencing
  `psycopg2.extensions.TransactionRollbackError` around L216-232; accessed
  2026-07-08.)

### Transactions / rollback

- **Fact (source)** — A cursor obtained via `Registry.cursor()` is itself a
  context manager: `with cr:` commits **only if the block exits without an
  exception**, and always closes the cursor in a `finally` regardless of
  outcome. `Cursor.commit()` flushes pending ORM changes then issues SQL
  `COMMIT`; `Cursor.rollback()` issues SQL `ROLLBACK`; **closing an open
  cursor unconditionally calls `rollback()` first** — i.e. any uncommitted
  work is discarded when a cursor closes, committed or not.
  (`github.com/odoo/odoo/blob/19.0/odoo/sql_db.py`, `BaseCursor.__enter__`/
  `__exit__` L228-245, `Cursor.commit` L560-568, `Cursor.rollback` L570-577,
  `Cursor.close`/`_close` L526-549; accessed 2026-07-08. `access_status`:
  Accessible.)
- **Fact (source)** — Both classic XML-RPC dispatch
  (`odoo/service/model.py:dispatch`, L109-138, `with registry.cursor() as
  cr: ...`) and ordinary HTTP/JSON-RPC controller requests
  (`odoo/http.py`, `Request._serve_db`, L2267-2342) run the actual call
  through the **same** `odoo.service.model.retrying()` function, which only
  calls `env.cr.commit()` after the wrapped function returns successfully —
  i.e. **one request/RPC call = one transaction**, committed at the end on
  success, and the cursor is always closed in a `finally` when the request
  ends. (Same locations; accessed 2026-07-08. `access_status`: Accessible.)
- **Fact (source)** — Odoo automatically **retries** a request on specific
  PostgreSQL serialization/concurrency errors
  (`LockNotAvailable`, `SerializationFailure`, `DeadlockDetected`), up to
  `MAX_TRIES_ON_CONCURRENCY_FAILURE = 5` times, rolling back the
  transaction and waiting `random.uniform(0.0, 2**i)` seconds between
  attempts (randomized exponential backoff) — a database-serialization
  retry loop, not an application-level `write_date` comparison.
  `IntegrityError` is **never retried**: it is converted straight to a
  `ValidationError`. (`github.com/odoo/odoo/blob/19.0/odoo/service/model.py`,
  constants L28-30, `retrying()` L160-236; accessed 2026-07-08.
  `access_status`: Accessible. **Open question**: no official *prose* doc
  page documenting this retry mechanism was found for end users/module
  developers — only source docstrings/comments; if a user-facing citation is
  required later, this should be re-checked, not assumed absent.)
- **Fact (source)** — `cr.savepoint(flush=True)` (default) is the sanctioned
  way to isolate a risky sub-operation: on a clean exit it flushes and
  releases the savepoint; on an exception it rolls back to the savepoint
  (not the whole transaction) and clears the environment cache. Core
  `create()`/`write()` do **not** wrap themselves in a savepoint by default;
  savepoints are used **selectively** by higher-level code (e.g.
  `Model.load()`'s per-record retry-on-batch-failure) and throughout
  business-logic try/except blocks across many addons.
  (`github.com/odoo/odoo/blob/19.0/odoo/sql_db.py`, `Savepoint` class
  L87-129, `_FlushingSavepoint`/`BaseCursor.savepoint` L132-151/217-226;
  `odoo/orm/models.py`, `Model.load` L920-1064; accessed 2026-07-08.
  `access_status`: Accessible.)
- **Fact (official doc)** — The official contributor coding guidelines are
  explicit and load-bearing: *"The Odoo framework is in charge of providing
  the transactional context for all RPC calls... a new database cursor is
  opened at the beginning of each RPC call, and committed when the call has
  returned... If any error occurs during the execution of the RPC call, the
  transaction is rolled back atomically."* They further state application
  code must **never** call `cr.commit()`/`cr.rollback()` directly unless it
  opened its own separate cursor, and any `cr.commit()` outside the
  framework "must have an explicit comment explaining why... Otherwise they
  can and will be removed!" — recommending `cr.savepoint()` instead for
  isolating a block, with a documented warning that >64 savepoints in one
  transaction slows PostgreSQL, and savepoints carry "huge overhead" when
  the server runs replicas.
  (`https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html`,
  §"Never commit the transaction"; raw source
  `raw.githubusercontent.com/odoo/documentation/19.0/content/contributing/development/coding_guidelines.rst`
  L662-779; accessed 2026-07-08. `access_status`: Partial — the live
  odoo.com HTML page for this specific guidelines page did render body
  content via WebFetch, but the ORM/testing pages below did not, so the RST
  source was used as the verified text for consistency; see caveat below.)
- **Fact (official doc)** — Test code must never call `cr.commit()`
  ("this is usually done by the test framework by doing a rollback...
  you must never call `cr.commit` in a test (nor anywhere else in the
  business code)"), and `TransactionCase` runs each test method inside a
  savepoint sub-transaction with the outer cursor "always closed without
  committing." (`https://www.odoo.com/documentation/19.0/developer/tutorials/unit_tests.html`
  and `.../developer/reference/backend/testing.html`; raw sources
  `content/developer/tutorials/unit_tests.rst` L205-212 and
  `content/developer/reference/backend/testing.rst`; accessed 2026-07-08 for
  the unit_tests page — the testing.html page's `TransactionCase` fact was
  already recorded in `odoo-official-architecture-notes.md`, accessed
  2026-06-30. `access_status`: Partial for the live-rendered HTML, per the
  caveat below.)
- **Open question / caveat** — WebFetch of the live rendered
  `developer/reference/backend/orm.html` and `.../testing.html` pages
  returned only navigation/table-of-contents text rather than full article
  bodies in this session (the same JS-rendering caveat
  `odoo-official-architecture-notes.md` already flagged in its own Status
  section). All exact quotes above were therefore verified against the raw
  RST source on `github.com/odoo/documentation` (branch `19.0`) rather than
  the rendered HTML; `access_status` is recorded as **Partial** for those
  specific pages to reflect that the RST-to-HTML rendering itself was not
  independently diffed, even though the RST is the direct input that builds
  the published page.
- **Inference (repo-consistency check, not a new architecture claim)** —
  The repo's own PR #121 lesson ("a raised exception can roll back ORM
  writes made earlier in the same call," `research-handoff.md`, not
  modified this session) is **consistent with** the source-verified fact
  above that a request's transaction only commits at the very end, on
  success, and that closing an uncommitted cursor always rolls back. The
  repo's stated lesson does not itself carry an independent official-Odoo
  citation; it is presented here as an internally-consistent inference, not
  a second, separately-sourced fact.

### Constraints

- **Fact (official doc + source)** — `@api.constrains(*field_names)` marks a
  method invoked **only on records where one of the declared fields was
  actually part of the `create()`/`write()` call**; it must raise
  `ValidationError`. Internally, `BaseModel._validate_fields(field_names,
  excluded_names)` runs exactly the constraint methods whose declared field
  set intersects the written fields; both `create()`'s internal flow and
  `write()` call `_validate_fields` with **no surrounding try/except**, so a
  raised `ValidationError` propagates straight out of `create()`/`write()`
  uncaught at that layer — it is then handled by the outer RPC-call
  transaction machinery described above (rollback, not retry, since
  `ValidationError` is not one of the retried exception types).
  (`https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#odoo.api.constrains`;
  `github.com/odoo/odoo/blob/19.0/odoo/orm/decorators.py` `constrains`
  L88-123; `odoo/orm/models.py` `_validate_fields` L1253-1268, internal
  create-flow call ~L4948-4951, `write()` calls L4489-4514; accessed
  2026-07-08. `access_status`: Accessible for source; Accessible for the
  doc page's `@api.constrains` text specifically — this sub-page rendered
  correctly under WebFetch unlike the general ORM page body.)
- **Fact (official doc + source)** — The modern SQL-constraint API is
  `models.Constraint(definition, message)` (plus `Index`/`UniqueIndex`),
  declared as a model attribute whose name starts with `_` — **exactly the
  pattern this repo already uses**, e.g.
  `shopify_connector_job.py`'s `_store_idempotency_key_uniq =
  models.Constraint('UNIQUE(store_id, idempotency_key)', '...')`.
  `definition` is raw SQL used verbatim in `ALTER TABLE ... ADD CONSTRAINT`
  (examples given: `CHECK (x > 0)`, `FOREIGN KEY (...) REFERENCES ...`,
  `UNIQUE (user_id)`). **The legacy `_sql_constraints` list-of-tuples
  attribute (and legacy `_constraints`) is no longer supported in Odoo 19**
  — the model-class builder only logs a warning and otherwise ignores it.
  (`https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html#constraints-and-indexes`;
  raw source `content/developer/reference/backend/orm.rst` L507-529;
  `github.com/odoo/odoo/blob/19.0/odoo/orm/table_objects.py` `class
  Constraint` L79-107; `odoo/orm/model_classes.py` L159-164 (warning
  emission); accessed 2026-07-08. `access_status`: Accessible for source;
  Partial for the general orm.html live page per the caveat above, RST used.)
- **Fact (source)** — SQL constraints are (re)applied to the live table by
  `BaseModel._add_sql_constraints()`, called from `_auto_init()` (registry/
  schema setup, run on module install/update) only when `self._auto` is
  true; `Constraint.apply_to_database()` diffs the declared definition
  against the current Postgres constraint definition and only issues DDL
  (`odoo.tools.sql.add_constraint()` → a plain `ALTER TABLE ... ADD
  CONSTRAINT ...` with no `DEFERRABLE` clause) when they differ.
  (`github.com/odoo/odoo/blob/19.0/odoo/orm/models.py` `_auto_init` ~L3170,
  `_add_sql_constraints` L3243-3267; `odoo/orm/table_objects.py`
  `apply_to_database` L109-122; `odoo/tools/sql.py` `add_constraint`
  L451-463; accessed 2026-07-08. `access_status`: Accessible.)
- **Fact (source + official PostgreSQL doc)** — At runtime, a violated
  Postgres constraint raises `psycopg2.IntegrityError`, which the
  `retrying()` RPC wrapper catches, rolls back for, and converts via
  `BaseModel._sql_error_to_message(exc)` into a translated, model-aware
  message, re-raised as `ValidationError(message) from exc` — the raw
  `IntegrityError` never reaches calling code. (The mechanism is named
  `_sql_error_to_message`/`_sql_error_to_message_generic` in Odoo 19, not
  `_process_exception` as originally guessed in this session's research
  prompt — noted so the correct name is used in any future citation.)
  Because `odoo.tools.sql.add_constraint()` issues its `ALTER TABLE ADD
  CONSTRAINT` with no `DEFERRABLE`/`INITIALLY DEFERRED` clause, and
  PostgreSQL's own documented default for constraints not explicitly marked
  `DEFERRABLE` is `NOT DEFERRABLE` / checked "immediately after every
  command," a `models.Constraint`-declared `UNIQUE`/`CHECK`/`FK` constraint
  (such as this repo's `store_idempotency_key_uniq`) is enforced **per
  statement, not deferred to `COMMIT`**, unless a future Odoo version adds
  an explicit `DEFERRABLE` clause. This specific deferred-vs-immediate
  conclusion is labeled **Inference** (combining the source fact and the
  official Postgres default), not a directly-stated Odoo fact.
  (`github.com/odoo/odoo/blob/19.0/odoo/service/model.py` IntegrityError
  branch L184-236 esp. L192-214; `odoo/orm/models.py`
  `_sql_error_to_message`/`_generic` ~L3269-3325;
  `https://www.postgresql.org/docs/current/sql-createtable.html` §DEFERRABLE;
  accessed 2026-07-08. `access_status`: Accessible.)
- **Open question** — Whether the legacy `_sql_constraints` tuple syntax is
  fully inert beyond the warning log, or partially processed by some
  compatibility shim, was not traced past the warning-emission point.
  Whether a repo-wide (not just targeted-file) search would find
  `DEFERRABLE` used anywhere in Odoo core was not performed.

### Concurrency / locking

- **Fact (source)** — Odoo 19 exposes two `@api.private` recordset methods
  for taking an explicit PostgreSQL row lock: `lock_for_update()` (raises
  `LockError` if any requested row can't be locked) and
  `try_lock_for_update()` (silently skips unlockable rows via `SKIP LOCKED`
  and returns only the successfully-locked subset). Both live on
  `BaseModel` in `odoo/orm/models.py` — the file that now (Odoo 19)
  actually defines `BaseModel`/`Model`/`AbstractModel`; `odoo/models.py` no
  longer exists as a single file (404) and `odoo/models/__init__.py` is a
  thin re-export package "to avoid merge conflicts on `odoo/models.py`."
  (`github.com/odoo/odoo/blob/19.0/odoo/orm/models.py`, `lock_for_update`
  L5564, `try_lock_for_update` L5592-5622; `odoo/models/__init__.py`;
  accessed 2026-07-08. `access_status`: Accessible.)
- **Fact (source)** — `lock_for_update()`'s own docstring/comment explains
  the choice of `FOR UPDATE SKIP LOCKED` (or `FOR NO KEY UPDATE SKIP
  LOCKED` when `allow_referencing=True`) over `NOWAIT`: *"the later aborts
  the transaction and we do not want to use SAVEPOINTS."* This is the same
  lock flavor `ir.cron`'s own `_acquire_one_job()` uses for its job-claiming
  query (cross-referenced under Scheduled actions / cron above).
  (Same file/lines; accessed 2026-07-08.)
- **Fact (official doc)** — The **only** place `lock_for_update`/
  `try_lock_for_update` is actually documented in the fetched official
  pages is the "Writing cron functions" example under the Scheduled Actions
  reference (cross-referenced above) — i.e. Odoo's own official guidance
  for row-level locking is framed specifically as a **cron-batch-processing
  pattern**, not as general application-level concurrency guidance. A
  full-text search of the ORM reference doc's RST source and the security
  reference doc's RST source (624 lines) for "lock", "FOR UPDATE",
  "concurrency", "write_date"/"__last_update", "race condition" found no
  genuine matches in either (the one `write_date` hit in the ORM doc is the
  unrelated audit-log field, documented only as "Stores when the record was
  last updated," with no concurrency framing).
  (`raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/backend/orm.rst`
  and `.../security.rst`; accessed 2026-07-08. `access_status`: Accessible
  for the negative-search result on the RST source; Partial for the live
  HTML pages per the general rendering caveat.)
- **Fact (source, resolves a prior repo open question)** — No
  `_check_concurrency` method, no `CONCURRENCY_CHECK_FIELD` constant, and no
  `__last_update`-based optimistic-lock check exist anywhere in
  `odoo/orm/models.py` (19.0) — a full-text search of the 7,130-line file
  for all three strings returned zero matches. A `ConcurrencyError`
  exception class still exists in `odoo/exceptions.py`, but its docstring
  frames it purely as a low-level signal for the automatic
  transaction-retry mechanism described above ("should only be used if all
  alternatives are deemed worse"), **not** as a client-submitted
  write_date-comparison check. The actual mechanism Odoo 19 core uses to
  protect against two near-simultaneous conflicting writes is the
  database-serialization retry loop (`retrying()`, cross-referenced under
  Transactions above), not an application-level optimistic-concurrency
  field comparison.
  (`github.com/odoo/odoo/blob/19.0/odoo/orm/models.py` (full-file search);
  `odoo/exceptions.py` `ConcurrencyError` L128; accessed 2026-07-08.
  `access_status`: Accessible.)
- **Open question** — Whether a `write_date`-based optimistic check exists
  anywhere else in the 19.0 codebase (legacy shims, web client JS, other
  addons) beyond the specific files checked was **not** exhaustively
  ruled out: a full repository code-search API call
  (`api.github.com/search/code`) returned a 403 in this session's
  environment ("GitHub access to this repository is not enabled for this
  session"), so only targeted per-file checks were possible. This is
  recorded as an open question, not asserted as a whole-repo negative fact.
  Whether `lock_for_update`/`try_lock_for_update` are new in 19.0 or a
  rename of a prior mechanism was not researched (out of this task's Odoo
  19-only scope).

### Logging / observability

- **Fact** — Odoo code logs via the standard Python `logging` module
  (`_logger = logging.getLogger(__name__)`); default INFO/WARNING/ERROR to
  stderr; CLI-tunable via `--logfile`, `--syslog`, `--log-db <db>` (writes
  to the `ir.logging` model), `--log-handler`, `--log-level`. Odoo 19 core
  has **no documented built-in metrics/telemetry endpoint** (Prometheus,
  OpenTelemetry) — an absence-of-documentation open question, not a
  documented denial.
  (`https://www.odoo.com/documentation/19.0/developer/reference/cli.html`,
  accessed 2026-06-30/2026-07-01, per `odoo-official-architecture-notes.md`;
  not re-fetched this session.)
- **Fact (repo cross-check)** — This repo's own audit trail
  (`shopify.connector.job.log`) is entirely separate from Odoo's core
  `ir.logging`/`--log-db` mechanism — job/attempt/state-change/audit
  records are application-level rows in a dedicated model, not core Odoo
  log entries, and carry no relationship to `--log-db` at all.

### Test/runtime implications

- **Fact** — `TransactionCase` runs each test method inside a savepoint
  sub-transaction with the outer cursor "always closed without committing"
  (cross-referenced under Transactions above; also independently recorded
  in `odoo-official-architecture-notes.md`, accessed 2026-06-30).
- **Fact (Odoo.sh, repo-evidenced)** — `task-005-validation-results.md` and
  `DEC-024-task-005-closure.md` both record that **live Odoo.sh runtime
  testing found two real defects that static review and `py_compile` missed
  across three PR revisions** — a `write_date`-timing-dependent freshness
  guard, and a credential-mutation-must-invalidate-derived-state gap. This
  is the strongest evidence in the repo that Odoo.sh's actual PostgreSQL
  write-timing/transaction behavior can diverge from what static analysis
  predicts, reinforcing the official "best effort"/non-guaranteed cron
  timing fact above as a general theme: **runtime behavior on Odoo.sh must
  be evidenced, not inferred from source reading alone**, for anything a
  future sync engine's own correctness claims depend on.

## Sync-engine implications

For each implication: **source-backed fact** → **implication for core
engine** → **implication for future domain modules** → **open caveat**.
All implications below are inferences drawn from the facts above; none is
an architecture decision.

1. **Fact**: `ir.cron` is Odoo 19's only official background-execution
   primitive, poll-based, `--max-cron-threads`-bounded (default 2), and on
   Odoo.sh runs "best effort," never more than every ~5 minutes in
   production, and is **disabled entirely** on staging/development.
   → **Core engine**: any retry/dispatch cadence layer must be one or more
   `ir.cron` scheduled actions, batched and idempotent per Odoo's own
   guidance — it cannot assume sub-5-minute latency on Odoo.sh production.
   → **Domain modules**: no domain sync path should assume near-real-time
   cron dispatch; the `webhook` job source is the only path that could ever
   have sub-cron latency, and even that still needs a follow-up job to
   actually execute (webhooks are enqueue-only per prior accepted MBQ
   rows, not directly executed inline).
   → **Open caveat**: whether Odoo.sh's managed `odoo.conf`/build pipeline
   supports `server_wide_modules` (gating OCA `queue_job` as an
   alternative) remains an open question in the repo's own prior research
   — not re-verified this session.

2. **Fact**: `ir.cron`'s own job-claiming query uses
   `FOR NO KEY UPDATE SKIP LOCKED`, and the official "Writing cron
   functions" doc recommends `try_lock_for_update()` for per-record locking
   inside a cron batch, both explicitly to let concurrent workers skip
   rows another worker already claimed rather than blocking or erroring.
   → **Core engine**: a future job-claiming/dispatch query (however it
   selects the next `shopify.connector.job` row(s) to run) has a
   directly-precedented, official pattern to follow — `SKIP LOCKED`-style
   claiming, not `NOWAIT` (which the source comment explicitly says is
   avoided because it "aborts the transaction").
   → **Domain modules**: none directly — this is a core-engine-only
   concern once a job-runner/dispatcher exists.
   → **Open caveat**: this is a **pattern precedent**, not a decision that
   the future engine must literally reuse `try_lock_for_update()`; whether
   the existing `operation_scope_key` UNIQUE-constraint approach (already
   shipped) or an explicit row-lock approach (or both) is the right
   dispatch-safety mechanism is unresolved and out of this research's
   scope to decide.

3. **Fact**: `shopify.connector.job` already enforces `UNIQUE(store_id,
   idempotency_key)` and `UNIQUE(store_id, operation_scope_key)`, with the
   latter clearing to `False` on terminal/superseded state.
   → **Core engine**: a real, working per-store single-active-operation
   serialization guard already exists for job **creation** — but it is
   scoped to one store + one `(res_model, res_id, shopify_target_gid)`
   tuple while non-terminal, and `idempotency_key` is never reused to
   detect "was this exact operation already completed successfully in a
   past terminal run" (TD-001's fix was a per-job-type nonce specifically
   to *avoid* an unwanted collision, not to build reuse-detection).
   → **Domain modules**: any future business job creation must still
   generate a correct `payload_hash`/`shopify_target_gid` — the existing
   constraints only protect once those values are computed correctly; they
   do not themselves compute or validate them.
   → **Open caveat**: whether `idempotency_key` should ever be
   deliberately reused across separate retry attempts of "the same logical
   operation" (vs. always generating a fresh key per attempt, as
   `core_test_connection`/`core_readiness_check` currently do) is not
   decided anywhere inspected in this session — a genuinely open design
   question for retry-scheduling, not resolved by the existing schema.

4. **Fact**: `shopify_connector_api_client.py`'s own docstring states "no
   retry loop (retry policy belongs to the job layer, DEC-009)" — i.e.
   retry policy is explicitly named as deferred to a "job layer" that does
   not exist in any file inspected this session.
   → **Core engine**: retry/backoff is a clean, not-yet-built layer with an
   already-named home (per the code comment) but no implementation.
   → **Domain modules**: no domain module can rely on any retry behavior
   existing today; every domain sync call through the API client is
   currently single-attempt.
   → **Open caveat**: `master-blueprint-open-questions.md`'s MBQ-16 row
   (referenced, not read in full this session — outside the required file
   list) reportedly already named retry-count/backoff constants as
   "adjustable planning defaults" per its own summary text seen elsewhere
   in this session's reading; this session does **not** assert the content
   of that document's retry-constant specifics, since it was not directly
   opened and verified here.

5. **Fact**: `shopify_connector_readiness_check.py`'s `_get_checks()` is a
   working, tested, inheritance-based extension seam (`_inherit` +
   `super()` + append, never mutate).
   → **Core engine / domain modules**: this is a directly-validated,
   already-shipped precedent for how a future "domain-neutral handler
   registry" (a named gap below) could be shaped.
   → **Open caveat**: it is a registry of readiness **checks** (each
   independently evaluated, aggregated fail-closed), not sync
   **operations** (which would need dispatch, ordering, and per-operation
   error/retry semantics) — the pattern needs real adaptation, not
   verbatim reuse.

6. **Fact (repo-evidenced + source-consistent)**: the repo's own
   `action_reconnect()` revision avoided writing state/audit then raising,
   because (per the repo's own stated reasoning, consistent with this
   session's independently source-verified fact that a request's
   transaction commits only at the very end on success) a later raise in
   the same call can roll back earlier writes in that call.
   → **Core engine**: any future job-execution method that must durably
   record partial progress (e.g. "attempted, here's what happened so far")
   before signaling final failure needs the same discipline — write, then
   `return`, don't write-then-raise, if that specific write must survive
   the call.
   → **Domain modules**: the same discipline applies to any future
   domain-sync job handler that logs intermediate progress before a
   terminal failure.
   → **Open caveat**: Odoo does provide `cr.savepoint()` as the officially
   sanctioned way to isolate a sub-operation's failure without discarding
   the whole call's other writes (per the coding-guidelines fact above) —
   whether a future sync engine should use savepoints per job-execution
   step, rather than (or in addition to) the write-then-return discipline
   the repo currently uses, is an open design question, not decided here.

7. **Fact**: `shopify.connector.job.write()` re-checks store-state gating
   at the moment of the `state -> 'running'` transition, explicitly using
   the *effective* post-write `job_source`/`store_id`, not a stale
   pre-write read.
   → **Core engine**: this enqueue-time-plus-execution-time
   defense-in-depth pattern (not a single check) is the model a sync
   engine's own future job-claim/execution step should replicate for any
   new gating condition (e.g., a domain-enablement flag), since a business
   condition can change between enqueue and execution.
   → **Domain modules**: any future domain-specific gating (e.g., "only
   sync if `product_domain_enabled`") should follow the same two-checkpoint
   shape, not rely on an enqueue-time check alone.
   → **Open caveat**: none identified — this is a directly demonstrated,
   already-tested pattern (`test_business_job_running_blocked_when_*` in
   `test_connection_lifecycle.py`).

8. **Fact**: no `ir.cron`/`ir_cron` reference exists anywhere under
   `addons/` (confirmed by direct grep across the whole tree).
   → **Core engine**: the entire retry-scheduling/dispatch-cadence layer is
   unbuilt — `_check_cron_queue_health`'s own docstring says as much.
   → **Domain modules**: none can be scheduled today; every existing job
   type executes synchronously, inline, at the moment its creating method
   runs.
   → **Open caveat**: none — this is the clearest, most direct "gap" fact
   in the whole inventory.

9. **Fact**: `shopify_connector_binding_mixin.py` defines an
   already-agreed field vocabulary (`status`, `match_key`, audit fields)
   but "carries no `res_model`/`res_id` pair" and enforces no uniqueness of
   its own; no concrete binding model exists anywhere in the repo.
   → **Core engine**: none directly — binding/dedup is domain-owned by
   design (per the mixin's own docstring, DEC-013).
   → **Domain modules**: first-sync dedup has an agreed-upon shared
   vocabulary already, but **zero working implementation** — every future
   concrete domain module must independently add its own
   `(store_id, shopify_gid)` uniqueness constraint and its own matching
   logic; there is no shared "first sync" service method anywhere in core
   to call.
   → **Open caveat**: whether a shared *service method* (not just a shared
   *field shape*) for first-sync matching belongs in core or per-domain is
   not decided anywhere inspected — an open design question for whichever
   task eventually specs the binding/dedup mechanics.

## Current gaps

- **No sync operation abstraction.** `job.job_type` today has exactly three
  values, all core/diagnostic (`core_readiness_check`,
  `core_manual_maintenance`, `core_test_connection`); `job_source`'s five
  business values (`webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation`, `odoo_event`) are declared in the selection field and
  gated by `create()`/`write()`, but **no code anywhere creates a job with
  any of them** (confirmed by inspection of every required file plus a
  targeted grep for each source string across `addons/`).
- **No retry scheduling engine yet.** Confirmed by
  `shopify_connector_api_client.py`'s own docstring ("no retry loop...
  belongs to the job layer") and by the total absence of `ir.cron`/scheduled
  actions anywhere in the repo.
- **No domain-neutral handler registry yet.** The readiness-check
  `_get_checks()` extension seam is a real, tested precedent for
  inheritance-based registration, but it registers checks, not sync
  operations; nothing analogous exists for job execution/dispatch.
- **No checkpoint/resume model yet.** `operation_scope_key` is a
  single-active-operation lock (Boolean-like presence/absence via a cleared
  text key), not a pagination cursor, resume token, or multi-step-progress
  field; no field on `job` records anything like "resume from here."
- **No first-sync dedup design yet.** `shopify_connector_binding_mixin.py`
  is a shape-only abstract contract; zero concrete binding tables or
  matching-service code exist anywhere in the repo.
- **No domain sync modules yet.** `addons/` contains exactly two module
  directories: `shopify_connector_core` (this substrate) and `adams_base`
  (an unrelated pre-existing customer base module, not part of this
  connector). No `shopify_connector_product`/`_customer`/`_order`/
  `_inventory`/`_fulfillment` or similarly-named domain module exists.
- **VAL-B2 remains deferred/not passed** — no live Shopify Admin API
  connection evidence exists anywhere in the repo
  (`DEC-021-val-b2-deferral-for-task-004.md`, restated unchanged by
  DEC-022 §Acceptance note and DEC-024 §3).
- **MBQ-05 remains partially routed/open** — the scalable
  many-unrelated-customer distribution/auth architecture is undecided
  (`master-blueprint-open-questions.md` MBQ-05 row; `DEC-023`).
- **TD-002 remains Open** — the `read_fulfillments` readiness-scope
  correctness concern, routed to the future fulfillment domain task once
  the fulfillment API model is decided (`technical-debt-register.md`
  TD-002 row).

## Unsupported claims removed

The following were considered while drafting this document and were
**removed or downgraded** because they lacked a concrete citation:

- A draft claim that `operation_scope_key` "could serve as a
  checkpoint/resume cursor" was struck — the field is a cleared text lock,
  not a cursor/pagination-position value; asserting cursor-like semantics
  would have been an unsupported architectural leap beyond what the source
  actually shows.
- A draft claim asserting the exact retry-count/backoff constants named in
  `master-blueprint-open-questions.md`'s MBQ-16 row was removed — that file
  was outside this session's required-inspection list and was not opened
  to verify; the implication section above explicitly flags this as
  not-independently-verified rather than asserting specific numbers.
- A draft claim that Odoo 19 "has no job queue anywhere in core" was kept
  as an **inference**, not restated as a fact — `odoo-official-architecture-notes.md`
  itself already labels this a negative-proof-from-absence inference, and
  this session's own fresh source search (targeted files, not a full
  repository code search — the GitHub code-search API returned a 403 in
  this session) does not strengthen it to a proven fact.
- A draft claim that Odoo's `ConcurrencyError`/optimistic-locking mechanism
  is "the" concurrency-safety mechanism for two conflicting writes was
  corrected after source verification: the actual mechanism is the
  database-serialization `retrying()` retry loop, not an application-level
  `write_date` comparison (no such comparison exists in `odoo/orm/models.py`
  per this session's full-file search) — the earlier, more generic draft
  wording was replaced with the source-verified mechanism name.
- A guessed method name, `_process_exception`, used in this session's own
  research prompt for the SQL-error-to-message conversion mechanism, was
  **not** found anywhere in the 19.0 codebase; it was replaced with the
  actual verified name, `_sql_error_to_message`/`_sql_error_to_message_generic`,
  rather than left uncorrected.
- A draft claim that live-rendered `odoo.com/documentation/19.0` HTML pages
  were fetched and quoted directly was corrected to disclose that several
  pages (ORM reference, security reference, actions reference,
  testing/unit-tests) rendered only navigation/table-of-contents text under
  WebFetch in this session, and the raw RST source on
  `github.com/odoo/documentation` was used as the verified text instead —
  recorded honestly as `access_status: Partial` rather than claimed as a
  clean `Accessible` live-page fetch.

## Handoff

- **Branch**: `claude/task-006a-odoo-repo-sync-research-1nusjq` (the
  harness-designated branch for this session's task; built directly on
  `origin/Shopify-connector`'s HEAD, `9247fea3c36afdb761a82678f3e5e66e8ef42e87`
  — PR #122's merge commit — confirmed via `git merge-base
  --is-ancestor` before any edit).
- **Files changed**: exactly one —
  `docs/01-research/sync-engine-odoo-repo-source-notes.md` (new). No
  `addons/**`, manifest, XML, CSV, security, migration, CI, or other
  governance file touched. `docs/01-research/research-handoff.md` was read
  for context but **not modified**, per this task's explicit forbidden-file
  list (this document's own "Handoff" section stands in for the normal
  `CLAUDE.md` §12 rolling-handoff update for this specific session, since
  that file was placed off-limits by the task instructions).
- **Top findings**:
  - Task 005's job/log/store/credential/readiness substrate already
    provides real, tested enqueue-time-plus-execution-time gating,
    per-store single-active-operation uniqueness constraints, an
    inheritance-based check-registry precedent, and a repo-evidenced
    transaction-safety lesson (write-then-return, not write-then-raise) —
    but provides **no** sync-operation abstraction, retry engine, handler
    registry for operations, checkpoint/resume model, or first-sync dedup
    implementation.
  - Fresh Odoo 19 source research this session directly confirms: one
    request/RPC call = one transaction, committed only at the end on
    success; automatic retry only on specific PostgreSQL
    serialization/lock/deadlock errors (max 5 tries, exponential backoff),
    never on `IntegrityError`; and Odoo 19 ships official, source-level
    row-locking methods (`lock_for_update`/`try_lock_for_update`) whose only
    official documented use case is exactly the cron-batch-processing
    pattern a future sync engine's dispatcher would need. Separately, the
    modern `models.Constraint` API is used by this repo; based on Odoo's
    generated `ALTER TABLE ADD CONSTRAINT` behavior and PostgreSQL's default
    `NOT DEFERRABLE` behavior when `DEFERRABLE` is not specified, the
    immediate per-statement enforcement conclusion is an inference, not a
    directly stated Odoo documentation claim (see Odoo official/source
    facts §Constraints).
  - `ir.cron`'s own job-claiming query (`FOR NO KEY UPDATE SKIP LOCKED`) is
    a directly reusable, official-source-backed precedent for a future
    job-claiming design.
- **Weak/uncertain areas**:
  - `research-handoff.md` (11,957 lines) and
    `master-blueprint-open-questions.md` (569 lines, only ~460 read) were
    sampled/targeted, not read in full — some detail beyond what this
    document cites may exist in the unread portions.
  - Several official `odoo.com/documentation/19.0` live HTML pages
    rendered only navigation text under WebFetch this session; all quotes
    from those pages were instead verified against the raw RST source
    mirror, which is authoritative but was not independently diffed
    against the final rendered HTML.
  - A true whole-repository GitHub code search (for e.g. a residual
    `write_date`-based concurrency check outside the specific files
    checked) was not possible in this session's environment (403 from the
    GitHub code-search API) — the relevant negative findings are scoped to
    the specific files searched, not the entire `odoo/odoo` repository.
- **Exact next step**: **ChatGPT review of this research document** (and,
  if useful, later synthesis into an architecture/scope document by a
  separate, future session) — per `CLAUDE.md` §2/§6, this session does not
  self-authorize any next step beyond stopping for review. This document
  does not select or recommend which of DEC-024 §5's four unselected
  "next task candidates" (including "Task 006 — sync engine skeleton
  gate") should be pursued next; that remains a control-room decision.
