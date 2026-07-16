# CORE-R2 — Foundation Slice 1 — Validation Results


## Wave 1 final exact-head closure — build 34986844 (2026-07-16)

Odoo.sh 19 build `34986844` validated draft PR #172 at exact SHA
`05bb4631d3fdf3c6c8b54c09deb7e0b1dc72f723` on database
`adamsmen-sol-wave-1-readonly-foundation-34986844`. Identity matched at the
start and end of the session and the working tree remained clean.

- Targeted AST tests: `0 failed / 0 errors / 2`.
- Fresh all-module installation: `0 failed / 0 errors / 635`.
- Full standard suite with the reversible issue #157 accommodation:
  `0 failed / 0 errors / 635` (`core 352 + product 176 + sale 107`).
- Combined genuine SRR-03 smoke: all 11 independent-connection classes,
  `0 failed / 0 errors / 41`, exercising 10 real PostgreSQL `40001`
  serialization conflicts and one lock timeout.
- Residue audit: zero open leases, jobs, job logs, test stores, credentials,
  idle transactions, leaked sessions/cursors/workers, or connector/test cron
  triggers. The one `shopify_connector_attribute_lock` row is the expected
  installation singleton; the three connector crons are legitimate installed
  records.
- Security audit: no real tokens, authorization headers, persisted
  credentials, raw PII, or temporary-path leakage.
- Issue #157: temporary defaults for
  `res_users.notification_type='email'` and
  `res_users_settings.color_scheme='system'` were used only for the accepted
  base-Odoo fixture artifact, then both defaults were dropped and verified
  restored to their pre-run state with no NULLs introduced.

The exact-head run proves independent backend identities, exact-row re-lock,
zero handler replay, fail-closed replay policy, disconnect/admission ordering,
real conflict/timeout handling, and zero residue. Product-owner ruling
`4988527547` therefore authorizes **SRR-03 CLOSED**. This closure does not
claim exactly-once remote effects and does not implement or prove DEC-031 Layer
2. Wave 1 is implementation-complete and runtime-green; PR #172 remains draft
and unmerged pending final Claude control-room review.



## Wave 1 substantive runtime proof — build 34985521 (2026-07-16)

Odoo.sh 19 build `34985521` ran draft PR #172 at exact SHA
`d9d2dd018470054944db064cdd553160232713cd` on database
`adamsmen-sol-wave-1-readonly-foundation-34985521`. The fresh all-module run
reported `1 failed / 0 errors / 634 tests`; the sole failure was the stale
test-only AST helper in
`TestJobDispatch.test_source_level_job_enqueue_only_creates_job_model`.
Focused Wave 1 tests were `0/0/105`; product was `0/0/176`; sale was
`0/0/107`; lifecycle was `0/0/9`.

All 11 genuine independent-connection SRR-03 classes passed in each of three
distinct OS-process repetitions. Real PostgreSQL `40001` conflicts and lock
timeouts were exercised. Exact-job re-locking, no handler replay, fail-closed
replay policy, disconnect/admission ordering, and zero leaked leases, jobs,
workers, sessions, cursors, and cron triggers were proven. Residue and
credential/PII scans were clean. Issue #157 was limited to the accepted exact
`notification_type`/`color_scheme` base-Odoo post-init fixture artifact
under the documented reversible database-only accommodation.

Product-owner ruling `4988098888` accepts the substantive SRR-03 runtime
criteria as satisfied. The authoritative risk row remains **OPEN pending final
exact-head reconciliation only**. Test-only correction
`b42042d641ce2d02cad9559a03fcb268ceaac3bc` changes no production code and
does not require repeating the three-process matrix. Final closure requires the
targeted AST guard, fresh all-module run, full core suite after the documented
#157 accommodation, one combined genuine-class smoke run, final
residue/security audit, and restoration of both temporary database defaults at
the new exact head.



## Wave 1 runtime-correction checkpoint — build 34968318 (2026-07-16)

Odoo.sh 19 build `34968318` ran draft PR #172 at exact SHA
`62b2645f69280aadc68a56045a26bef2063c5821` on database
`adamsmen-sol-wave-1-readonly-foundation-34968318`. The genuine
`TestGenuineRealAdmission` (9 tests ×3) and
`TestLifecycleAdmissionRaceGenuine` (4 tests ×3) repetitions passed, but
`TestDrainOwnershipReplayGenuine` failed deterministically
(`1 failed / 4 errors / 6` ×3) and the scheduled-drain lifecycle-retry case
failed. The defect was not dispatcher replay or row-lock ownership: SEC-1's
legal-transition matrix omitted the committed-state recovery edges needed
after PostgreSQL rolls back the original transaction and its uncommitted
`running` transition.

Product-owner ruling PR #172 comment `4984719237` authorizes only the five
recovery edges now implemented in correction commit
`2b6d9d8259fada252abca19407d1df53bed9e66f`. Recovery continues to re-lock
the exact `queued` or due `retry_waiting` row, consult replay policy, and
route once without invoking the handler; `draft→running` and
`draft→retry_waiting` remain illegal. Residue/leak and security/log scans for
the completed diagnostic run were clean. Issue #157 was limited to its exact
known `notification_type`/`color_scheme` post-init fixture artifact.

This is failed-run diagnostic evidence, not closure evidence. No post-correction
runtime pass is claimed; **SRR-03 remains OPEN pending an exact-head rerun of
the complete genuine concurrency/disconnect matrix and stability repetitions.**

> **Status: runtime-validated implementation record for control-room review.**
> CORE-R2 **implementation** gate OPENED by control-room comment `4952145926`
> (authorized base `Shopify-connector` @
> `ce504f42824807e215ee21df3dfd4eed9bb9a275`, ratifying D-CR2-A…F). This slice
> implements a **strict subset** of the merged packet
> ([`../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`](../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md))
> / analysis ([`../03-architecture/disconnect-quiescence-remediation-analysis.md`](../03-architecture/disconnect-quiescence-remediation-analysis.md)),
> AR-047.
>
> **Exact-head runtime closure (2026-07-13).** The full runtime matrix was
> executed **inside the authorized Odoo.sh dev build for the exact validated
> code SHA `c0d455938b4a087407d6c712acbcc8bcf1b06feb`** (Odoo **19.0**, build
> **34818964**, DB `adamsmen-claude-core-r2-implementation-foundation-34818964`,
> baseline A/B SHA `ce504f42824807e215ee21df3dfd4eed9bb9a275`). The **fresh
> build-time install** of `adams_base` + the three connector modules with
> `--test-enable` (demo data loaded) is **fully green — `0 failed, 0 error(s) of
> 325 tests`**; every CORE-R2 class passes. The seven
> `res_users.notification_type` `setUpClass` errors observed on *post-init test
> re-runs* carry a **high-confidence baseline attribution** to a base Odoo-19
> `mail` computed-field artifact (not CORE-R2) — the seven fixture files are
> byte-identical on base `ce504f`, the CORE-R2 diff is causally disjoint, and the
> failing traceback stays entirely in the fixture/base Odoo `res.users` path; the
> fresh installation is green. A literal separate-database `ce504f` A/B run was
> **not executed** (**RR-F remains open**; **issue #157** tracks the literal
> reproduction and separate fix decision) — see §4.1/§4.3. **The
> Foundation-Slice-1 admission
> half is runtime-validated on `c0d4559`.** **SRR-03 remains OPEN — no
> remediation and no runtime-green of the end-to-end disconnect-quiescence fix
> is claimed** (the later slices that would close the linearization are deferred;
> §5). Branch `claude/core-r2-implementation-foundation`; PR **#156** kept
> **draft/unmerged** into `Shopify-connector`; base
> `ce504f42824807e215ee21df3dfd4eed9bb9a275`; docs-only evidence commit advances
> the branch head (§4.4) while the validated **code** SHA remains `c0d4559`.

This record separates: (1) implemented facts; (2) static evidence; (3) the
authored tests — **now executed & green on Odoo.sh `c0d4559`** (§4.1); (4)
runtime status — **runtime-validated on `c0d4559`**; (5) intentionally deferred
Slice 2/3 items; (6) residual risks; (7) rollback.

---

## 0.1 Correction pass — control-room review `4680664964`

Review `4680664964` (on head `3a8bfd5`) returned **REVISE** with three reliability
blockers. All three are corrected on the same branch (no new branch, no merge, PR
kept draft); only `models/shopify_connector_api_client.py` and
`tests/test_disconnect_quiescence.py` changed for the fix (plus these docs).

**Blocker 1 — `execute_business` did not preserve the API-client contract.** It
called `_send` and yielded the raw transport object, bypassing `execute()`'s
missing-config `UserError`, missing-token classification, `RequestException`
mapping, and `_normalize_response`. A missing token even committed a lease and
passed a false token to `_send`.
*Correction (api_client.py):* `execute_business` now (a) raises the **same**
`UserError` when `shop_domain`/`api_version` is missing, **before** admission/
lease/`_send`; (b) `_admit` raises the accepted `ShopifyClientError(ERROR_AUTH,
REASON_TOKEN_INVALID, credential_invalid=True)` on a missing/empty token **before**
the lease insert and before `_send`, with no second credential read (never a
`ShopifyQuiescedError`, never a lease); (c) maps `requests.RequestException` →
`ShopifyClientError(ERROR_TEMPORARY, REASON_TEMPORARY, redact(str(exc)))`;
(d) yields `_normalize_response(store, response)` — the **same normalized dict**
`execute()` returns — so a domain call site can swap `result = client.execute(…)`
for `with client.execute_business(job, store, …) as result:` with no contract
change. The legacy two-arg `_send(store, body)` seam and `execute()` are
unchanged; `execute_business` uses the explicit-token `_send(store, body, token)`.
The lease is held across `_send` **and** `_normalize_response` **and** the caller
`with`-body.

**Blocker 2 — genuine tests did not exercise the production admission boundary.**
The prior genuine-connection test class used raw `FOR SHARE` + raw lease
`INSERT`s, proving only PostgreSQL primitives.
*Correction (tests):* replaced by **`TestGenuineRealAdmission`**, which invokes the
**real** `execute_business`/`_admit`/lease-ORM/`_get_access_token`/`_release_lease`
from genuine independent `db_connect` connections. Each worker owns a real main
cursor + `Environment` created **after** fixtures commit; the production `_admit`'s
own `registry.cursor()` side transaction is made genuinely independent (real
pooled cursor → durable, cross-connection-observable commit) by patching the
registry cursor factory for the bounded test window. Raw SQL is retained **only**
for bounded observation and durable, fail-loud, zero-residue cleanup — never to
create the lease under test. Proven: real single-admission lease committed
**before** `_send` and visible in-context then released; **caller-rollback
independence** (the committed lease survives the worker's own main-txn rollback);
**two real concurrent admissions** committing two distinct-keyed leases with
correct `job_id`s, then releasing.

**Blocker 3 — a release failure could replace the caller/body exception.**
*Correction (api_client.py):* the unconditional `finally` is replaced with
deterministic precedence — `try: … yield …; except BaseException as primary_error:
release; on release failure `raise primary_error from release_error` (chained,
never substituted); re-raise primary; else: release`. So: admission failure →
no release (no lease); body/`_send`/normalize failure with successful release →
original propagates, release runs exactly once; successful body + release failure
→ release error propagates; body error + release error → body error stays
**primary**, release chained as `__cause__` (classification preserved). No double
release; KeyboardInterrupt/SystemExit still attempt release.

**Also fixed while correcting the tests (found by the synchronous review):** the
test fixtures created a `connected` store and then called `action_set_token()`,
which **demotes** a connected store to `reconnect_needed`
(`shopify_connector_store_credential.py:106-107`) — so business enqueue and
`_admit` would have refused. Both fixtures now re-assert `state='connected'` after
`action_set_token` (the canonical pattern the existing dispatch/retry tests use).

## 0.2 Hardening pass — control-room review `4681564744`

Review `4681564744` (on head `ac34c2b`) confirmed the three original blockers
resolved and returned **REVISE** for one final reliability-hardening pass. All
five items are corrected, limited to `api_client.py` + `test_disconnect_quiescence.py`
(+ these docs); PR kept draft/unmerged.

1. **Every genuine DB cursor is bounded.** A new `_open_bounded(dbname)` helper
   opens a real pooled cursor and applies **transaction-local**
   `statement_timeout` + `lock_timeout` via parameterized
   `set_config(..., true)` as the cursor's first statement, closing the cursor
   and re-raising if the bound setup fails (returning only after success). The
   patched `_real_registry_cursor` factory routes through it, so **every
   production `_admit`/`_release_lease` side cursor** is bounded, as are the
   fixture/worker-main/observer/cleanup/verifier cursors. No genuine cursor is
   left unbounded.
2. **Guaranteed thread termination before patch restore + cleanup.** In the
   two-worker test, an inner `try/finally` **inside** the `with patch(registry.
   cursor)` block unblocks (`release_gate.set()`), joins both workers (bounded),
   and calls `_assert_workers_dead(...)` — so a live worker never runs under the
   restored (shared test-cursor) factory. The outer `finally` re-joins and
   re-asserts dead **before** `_cleanup`, so cleanup never begins with a live
   worker. `daemon=True` is only a last-resort backstop; the bounded cursors +
   `release_gate` make a >bound wedge unreachable (every worker DB op is
   time-bounded and `_send` is unblocked).
3. **Fail-loud, sanitized worker diagnostics.** Removed the `except Exception:
   pass` teardown. Worker body, cursor rollback, and cursor close failures are
   each surfaced as **separate** findings on a thread-safe `queue.Queue` via
   `_sanitize` — **type-only**: `{phase, exception type name, safe connector
   error_class or None}`. No raw exception object, `str`/`repr`/`%r`, SQL, path,
   credential, payload, or token reaches the parent; the parent assertion uses
   only these sanitized findings, and a cleanup error cannot hide an earlier
   worker error.
4. **Hardened zero-residue verification.** `_assert_zero_residue` runs on a
   bounded cursor, uses `self.assertEqual` (not bare `assert`) with fixed
   non-sensitive messages, always closes the verifier cursor, and verifies zero
   **leases, stores, credentials, jobs, AND job-logs** for the synthetic job ids;
   `_cleanup` deletes job-logs before jobs (FK `ondelete='restrict'`).
5. **Original traceback preserved.** In `execute_business`'s outer handler the
   successful-release path now ends in a **bare `raise`** (re-raises the same
   in-flight exception with its original traceback + identity + classification,
   adding no new raise frame); the dual-failure path keeps `raise primary_error
   from release_error`. Release still runs exactly once.

New focused tests prove: both timeouts applied to bounded/factory cursors; a
setup failure closes the cursor; worker rollback+close failures surface as
separate sanitized type-only findings; `_sanitize` leaks nothing; the
termination guard fails loud on a live worker; the verifier checks job-logs;
and the bare re-raise preserves the caller object/traceback with release-once.
Synchronous adversarial review of this pass: **no confirmed defects.**

---

## 0. Scope of this slice (what the gate authorized vs. what this slice did)

The gate (`4952145926`) authorizes the whole CORE-R2. This **Foundation Slice 1**
implements only the **admission half** — the pieces that can be built and
committed while remaining **dormant in production** (no call site enters the new
path). Everything disconnect/lifecycle/controller-related is a later slice.

**Implemented (this slice):**

1. Persisted store connection generation (`store.connection_generation`).
2. Enqueue-time expected generation (`job.expected_connection_generation`).
3. An independently-committed admission-lease model
   (`shopify.connector.call.lease`) + one minimal admin ACL.
4. Atomic store-row-locked admission (`_admit`).
5. `execute_business` as a real context manager (`__enter__` admits + sends,
   `__exit__` releases on normal **and** exception exit).
6. Token-read-once transport (`_send(store, body, token)`).
7. Focused tests (authored; **executed & green on Odoo.sh `c0d4559`** — §4.1).
8. This validation record + shared AR-047/SRR-03/handoff updates.

**Deliberately NOT implemented (deferred — see §5):** disconnect controller;
`disconnecting` lifecycle; `action_disconnect` rewrite; the conflicting
lifecycle update-lock protocol; credential-clear finalization;
`timed_out`/`completed` transitions; controller cron; product/customer
call-site migration; public `execute()` removal.

---

## 1. Implemented facts

### 1.1 Store connection generation — `[Fact — static]`
`addons/shopify_connector_core/models/shopify_connector_store.py`:
`connection_generation = fields.Integer(default=0, required=True, readonly=True)`.
Additive; existing rows backfill to `0`. **No** lifecycle transition bumps it in
this slice; **no** state value or `action_disconnect`/`action_reconnect` behavior
changed.

### 1.2 Job expected generation, captured at enqueue — `[Fact — static]`
`shopify_connector_job.py`:
`expected_connection_generation = fields.Integer(default=0, readonly=True)`.
`shopify_connector_job_enqueue.py::enqueue` sets
`vals['expected_connection_generation'] = store.connection_generation` — captured
**at enqueue**, never inferred at dispatch. Directly-created (non-enqueued) jobs
default to `0`.

### 1.3 Call-lease model — `[Fact — static]`
New `shopify.connector.call.lease` (`shopify_connector_call_lease.py`). Fields:

| field | type | notes |
| --- | --- | --- |
| `store_id` | Many2one → `shopify.connector.store` | required, indexed, `ondelete='cascade'` |
| `lease_key` | Char | required, indexed, **UNIQUE** (`models.Constraint`), opaque (uuid4 hex at admission) |
| `job_id` | **Integer** | required — deliberately **not** a Many2one (a job FK would take `FOR KEY SHARE` on a drain-locked job row and block admission) |
| `worker_ref` | Char | opaque `<dbname>:<pid>` diagnostic tag; non-secret |
| `admitted_at` | Datetime | required |
| `expires_at` | Datetime | required, indexed (inert this slice; the controller that would consume it is deferred) |

`_rec_name = 'lease_key'`. **No** token, credential, secret, query, variables,
payload, or customer/product field. ACL: exactly one row
(`access_shopify_connector_call_lease_admin`, admin group,
`read=1,write=0,create=1,unlink=1` — leases are insert+delete only). No `sudo()`;
lease create/unlink go through normal ACL.

### 1.4 Atomic admission `_admit` — `[Fact — static]`
`shopify_connector_api_client.py::_admit(job, store)` — one owned side
transaction (see §6 for the exact sequence). Returns only `(lease_key, token)`.
Refusals raise `ShopifyQuiescedError` (new). No lock is held across the network
call (`_send` runs after the admission txn commits and releases the lock).

### 1.5 `execute_business` context manager — `[Fact — static]`
`@contextlib.contextmanager execute_business(job, store, query, variables=None)`.
`__enter__`: `_admit` → build body → `_send(store, body, token)` → `yield result`.
`__exit__` (`finally`): `_release_lease(lease_key)` on **both** normal and
exception exit; caller exceptions are **not** suppressed; a `_send` failure before
`yield` still releases the lease (generator `finally`); the lease is **not**
released until the caller's `with`-body finishes. No value-returning form, no
manual release.

### 1.6 Token-read-once `_send` — `[Fact — static]`
`_send(self, store, body, token=None)`. When `token` is provided (business path)
`_send` performs **no** credential read. When `token is None` (legacy `execute()`
path) it reads once — preserving the pre-existing two-arg transport seam that
tests patch as `_send(store, body)`. No token logging, persistence, or
interpolation into any raised error.

### 1.7 Legacy `execute()` unchanged — `[Fact — static]`
`execute()` still calls `self._send(store, body)` (two positional args) and is
otherwise byte-for-byte unchanged; it remains public and operational. The only
new public method is `execute_business`.

---

## 2. Static evidence produced this session `[Fact — verified this session]`

Run in this environment (no Odoo runtime; static tooling only):

- `python3 -m py_compile` on every changed/added Python file — **OK**.
- `python3 -m compileall -q addons/shopify_connector_core` — **OK**.
- Manifest parses via `ast.literal_eval`; version bumped `19.0.1.5.0` →
  `19.0.1.6.0`; `data` list unchanged (no new data file). — **OK**.
- `ir.model.access.csv` parses; 23 rows, 8 columns, no ragged rows; the one new
  lease ACL row present. — **OK**.
- Changed-file set == exactly the allowlist (12 addon files; see §8). No forbidden
  file touched. — **OK**.
- No real git conflict markers. — **OK**.
- Source guards: no `advisory`/`pg_advisory` in the client; `FOR SHARE` present;
  every `.commit()`/`.rollback()` in the client is on the owned `side_cr` (no
  `self.env.cr.commit`/`self._cr.commit`); no token interpolated into a raised
  message. — **OK**.

---

## 3. Tests authored — now EXECUTED & GREEN on Odoo.sh `[Fact — authored & executed]`

`addons/shopify_connector_core/tests/test_disconnect_quiescence.py` (new), plus
minimal regressions in `test_api_client.py` and `test_job_enqueue.py`. **These
were authored in the earlier static sessions and are now EXECUTED and GREEN on
the Odoo.sh dev build for the exact head `c0d4559` (build 34818964) — see
§4.1.** The design intent below (test styles + required-proof mapping) is
retained as the specification the passing tests satisfy.

Two deliberate test styles:

- **`TransactionCase`** tests drive the **real** `execute_business`/`_admit`/
  `_send`/`_release_lease` path. Under Odoo test mode the `_admit` side cursor
  (`registry.cursor()`) is a `TestCursor` sharing the single test connection, so
  these prove admission *logic* (gate, ordering, token-once, release) but not
  genuine cross-connection independence.
- **`TestGenuineRealAdmission`** invokes the **real** production boundary —
  `execute_business`, real `_admit`, the ORM `shopify.connector.call.lease`
  model, and real `_release_lease` — from **genuine independent PostgreSQL
  connections** (`odoo.sql_db.db_connect`), with the registry cursor factory
  patched for the bounded test window so `_admit`'s own side transaction is a
  real pooled cursor rather than a shared `TestCursor`. Raw SQL is used **only**
  for bounded observation and durable, fail-loud, zero-residue cleanup — never
  to create the lease under test. This proves genuine **in-process
  cross-connection** admission behavior: a committed lease visible before
  `_send`, caller-rollback independence, and two concurrent real admissions
  committing distinct leases.

Required-proof → test mapping (numbers are the gate/packet proof list):

| # | Proof | Test |
| --- | --- | --- |
| 1 | Lease has no token/credential/query/payload field | `test_lease_has_no_secret_or_payload_field` |
| 2 | `job_id` is Integer, not M2o | `test_job_id_is_integer_not_m2o` |
| 3 | Lease key unique + opaque | `test_lease_key_is_unique` + `test_lease_opaque_committed_before_send_and_visible_in_context` |
| 4 | Missing job refused | `test_missing_job_refused` |
| 5 | Wrong-store job refused | `test_wrong_store_job_refused` |
| 6 | Disconnected store refused | `test_disconnected_store_refused` |
| 7 | Generation mismatch refused | `test_generation_mismatch_refused` |
| 8 | Token read exactly once | `test_token_read_once_and_passed_to_send` |
| 9 | Lease commits before `_send` begins | `test_lease_opaque_committed_before_send_and_visible_in_context` (`count_at_send == 1`) |
| 10 | Lease independently visible inside the context | same (`count_in_body == 1`) |
| 11 | Normal exit releases | `test_normal_exit_releases_lease` |
| 12 | Exception exit releases + re-raises | `test_exception_exit_releases_and_reraises` |
| 13 | Caller rollback cannot erase the committed lease | `TestGenuineRealAdmission.test_real_admission_survives_caller_rollback` (**real** `execute_business`/`_admit`, genuine connections) |
| 14 | Two concurrent admissions both commit | `test_two_real_concurrent_admissions_commit_distinct_leases` (**real** path, two worker threads) |
| 15 | Concurrent leases have distinct keys | same |
| 16 | `_send` receives the captured token | `test_token_read_once_and_passed_to_send` |
| 17 | `_send` does not reread credentials | `test_send_reads_credential_only_when_token_absent` |
| 18 | Token never in lease rows | `test_token_never_appears_in_lease_rows` |
| 19 | Enqueue captures `connection_generation` | `test_enqueue_captures_connection_generation` (`test_job_enqueue.py`) |
| 20 | Existing public execute callers operational | `test_execute_preserves_two_arg_send_seam` + all pre-existing api-client/test-connection tests (unchanged) |
| 21 | No advisory lock | `test_no_advisory_lock_in_client_source` |
| 22 | No request/main cursor commit | `test_no_main_cursor_commit_in_client_source` |

**Additional API-contract + precedence tests (correction review `4680664964`):**
`TestBusinessAdmission` also proves — missing `shop_domain`/`api_version` → same
`UserError`, no lease, no `_send`; missing credential → accepted
`ShopifyClientError(ERROR_AUTH, REASON_TOKEN_INVALID, credential_invalid=True)`
with exactly one credential read and no lease; success → the same normalized dict
shape as `execute()` with the lease held through normalization and the body;
`RequestException` → `ERROR_TEMPORARY` with the lease released and no
token/header/body leak; GraphQL/auth error → `_normalize_response` taxonomy
preserved with the lease released; and the four precedence cases (release-once on
body failure; success + release failure propagates; body error + release error →
body primary with release chained as `__cause__`).

**Test-framework note (honest, updated for the correction):** Odoo's `TestCursor`
makes a `registry.cursor()` side commit share the test transaction, so it is not
cross-connection-observable. To exercise the **real** production
`execute_business`/`_admit` cross-connection boundary (review `4680664964`,
blocker 2), `TestGenuineRealAdmission` patches the registry cursor factory to hand
out real pooled cursors for the bounded test window, so the production `_admit`'s
own side transaction commits durably and is observed from independent
`db_connect` connections. Raw SQL is used only for observation/cleanup, never to
create the lease under test. The full **two-server** production-path proof
(packet T-19) remains the deferred Odoo.sh runtime item (RR-4 / SRR-09).

---

## 4. Runtime status `[Fact — runtime-validated on Odoo.sh @ c0d4559]`

**The full runtime matrix was exercised on the authorized Odoo.sh dev build for
the exact head `c0d4559` (build 34818964).** §4.1 is the exact-head matrix and
per-class evidence; §4.2 records the earlier test-only fixes that made these
tests green (authored into `c0d4559` itself); §4.3 is the base-vs-head
attribution of the seven `res_users.notification_type` post-init-rerun artifacts;
§4.4 is the evidence commit. **This closes RR-B for the Foundation admission
slice. SRR-03 (the end-to-end disconnect-quiescence remediation) remains OPEN —
the disconnect controller, the conflicting lifecycle update-lock/epoch bump, and
Direction-C finalization are deferred (§5), so admission-vs-disconnect
linearization is not closed end to end. No runtime-green of the remediation is
claimed.**

### 4.1 Exact-head runtime validation — Odoo.sh build 34818964 @ `c0d4559` `[Fact — verified this session, 2026-07-13]`

Executed the full matrix **inside the authorized Odoo.sh dev build for the exact
head** (SSH/browser auth not required — the session runs in the build itself;
`odoo-bin`, the injected DB, and `git` are all local to the build). This
**supersedes** the earlier runtime-operator numbers (build `34808200`, an earlier
branch head); those survive only as the §4.2 fix history.

**Build identity / build-to-commit proof.**

- Odoo version: **19.0** (`ODOO_VERSION`; `install.log` header).
- Validated **code** SHA (`git rev-parse HEAD` inside the build container):
  **`c0d455938b4a087407d6c712acbcc8bcf1b06feb`** — the current branch head. The
  four §4.2 test-only fixes are **contained in this very commit** (message
  "CORE-R2 foundation: runtime validation on Odoo.sh — test-only fixes +
  evidence"), not committed on top of it. Working tree clean; base
  `ce504f42824807e215ee21df3dfd4eed9bb9a275` is an ancestor; PR scope = the known
  **16 files** (12 addon + 4 docs); no Slice-2 / controller / cron / lifecycle /
  call-site work present.
- Build DB / build id:
  `adamsmen-claude-core-r2-implementation-foundation-34818964` (build
  **34818964**); `ODOO_BUILD_URL`
  (`https://adamsmen-claude-core-r2-implementation-foundation-34818964.dev.odoo.com`)
  and `PGDATABASE` tie the DB to branch `claude/core-r2-implementation-foundation`
  (branch ref → `c0d4559`).
- The build's own `install.log` records the fresh install command
  `odoo-bin --stop-after-init … -i adams_base,shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --log-level=test --test-tags /adams_base,/shopify_connector_core,/shopify_connector_product,/shopify_connector_sale,…` then `Initializing database … loading 47 modules …` and `Executed command: odoo-bin module force-demo` — i.e. the **fresh install ran at build time, with tests enabled and demo data** (§4.1-A).

**A. Fresh install (clean database) — GREEN.** The build-time `-i
adams_base,shopify_connector_core,shopify_connector_product,shopify_connector_sale
--test-enable` install on the freshly-initialized (demo) database is
**`0 failed, 0 error(s) of 325 tests`** — the canonical clean-DB result. All three
connector modules are `installed` (`shopify_connector_core 19.0.1.6.0`, `_product
19.0.1.0.0`, `_sale 19.0.1.0.0`); the `shopify.connector.call.lease` model+table
exist; the store `connection_generation` and job `expected_connection_generation`
columns exist; the lease ACL row loads (`ir_model_access` ext-id
`shopify_connector_core.access_shopify_connector_call_lease_admin`,
`read=1,write=0,create=1,unlink=1`, Administrator group); model + test
registration succeed. **On the fresh install every one of the "7 failing"
`setUpClass` classes runs and passes** (build-time `install.log`:
`TestConnectionLifecycle` 41 test-starts, `TestReadinessSlotClosure` 20,
`TestCustomerBinding` 7, …). No install/upgrade error.

**B. Standard suites — post-init re-run on `c0d4559`.** Re-running each module's
full suite against the already-built DB (`odoo-bin -u <module> --test-enable
--stop-after-init --no-http`; standalone `--test-tags /<module>` gives identical
counts). Verbatim per-module summaries on build 34818964:

| Suite | Result | Stats (this build) |
| --- | --- | --- |
| `shopify_connector_core` | `0 failed, 6 error(s) of 122 tests` (+9 post-tests = 131 total) | core loaded 1.22s (incl. 1.01s test), 194 queries (+1783 test); 9 post-tests 0.13–0.25s / 203 queries |
| `shopify_connector_product` | `0 failed, 0 error(s) of 53 tests` | 1.99s (incl. 1.77s test), +2472 test queries |
| `shopify_connector_sale` | `0 failed, 1 error(s) of 41 tests` | 0.93s (incl. 0.79s test), +873 test queries |

Combined cascade (`-u shopify_connector_core` updates its dependents):
`0 failed, 7 error(s) of 225 tests`. All **6 core + 1 sale errors are the base
Odoo-19 `res_users.notification_type` `setUpClass` artifacts of §4.3** — they do
**not** occur on the fresh install (§4.1-A: `0 of 325`), only on post-init
re-runs; none is a CORE-R2 test and none is in the 16-file PR.

**C. CORE-R2 classes — executed and GREEN on `c0d4559`.** Verified by targeted
per-class runs (`--test-tags /shopify_connector_core:<Class>`):
`TestCallLeaseModelSchema` **7/7**, `TestBusinessAdmission` **18/18**,
`TestApiClient` (api-client regressions) **20/20**, `TestJobEnqueue`
(enqueue-generation regressions) **10/10**, and `TestGenuineRealAdmission`
**9/9** — the concurrent-admission class was run **three times on clean state and
is stable** (9/9 each; 0.19s / 0.25s / 0.15s; 203 queries each; no deadlock,
no stray worker). Every per-method start is present in the run logs.

**D. Real admission (TestGenuineRealAdmission, genuine independent connections).**
Observed: lease committed **before** `_send` (cross-connection observer count = 1
during send); visible in the `with` body; **survives the caller's own
main-transaction rollback** (count still 1 after rollback); **two concurrent
admissions coexist** (2 committed leases, **distinct** 32-hex keys, correct job
ids); leases released on context exit (count → 0); **zero synthetic residue** on a
fresh independent verifier.

**E. API contract (TestBusinessAdmission).** Missing config → `UserError` before
any admission/lease/`_send`; missing token → `ShopifyClientError(ERROR_AUTH,
REASON_TOKEN_INVALID, credential_invalid=True)` **before** the lease and with
exactly one credential read; success yields the same normalized dict as
`execute()`; `requests.RequestException` → `ERROR_TEMPORARY` (token/body
redacted); GraphQL `ACCESS_DENIED` normalized to `ERROR_AUTH`; token read **once**
and handed to `_send`; legacy two-arg `_send(store, body)` still reads the
credential itself.

**F. Exception precedence (TestBusinessAdmission).** Caller-body error releases
and re-raises; successful body + release failure → the release error propagates;
body error + release failure → **body error stays primary, release chained as
`__cause__`**; on successful release a **bare** re-raise preserves the **same
exception object and its original traceback** (incl. the body raise site) and
releases **exactly once**.

**No live Shopify request** was made in any run — every test replaces the `_send`
transport seam (or `requests.post`) with an in-memory fake.

**Warnings / SQL-ERROR classification (LOOP 5).** **Zero `WARNING`-level lines**
in any suite (grep of the full logs returns 0). Every `ERROR`-level SQL line is
exactly one of:
- **(a) base artifact — 7× `res_users.notification_type` NOT-NULL** (`INSERT INTO
  "res_users" … RETURNING "id"`, with no `notification_type` column) — the seven
  `setUpClass` failures of §4.3; base Odoo-19 `mail`, not CORE-R2; post-init-rerun
  only.
- **(b) expected negative-test assertions — all in PASSING tests:** in
  `TestProductDuplicatePrevention`, 6× NOT-NULL on
  `shopify_connector_product_template_binding` (`product_template_id`,
  `shopify_gid`, `store_id`) and `…_product_variant_binding`
  (`product_template_binding_id`, `shopify_gid`, `store_id`); in
  `TestCustomerDuplicatePrevention`, 2× duplicate-key on
  `shopify_connector_customer_binding_store_shopify_gid_uniq` /
  `…_store_partner_uniq` (plus, at fresh-install time, the same suite's 3×
  required-field NOT-NULL on `shopify_connector_customer_binding`). Each is the DB
  rejecting a deliberately-invalid insert — i.e. the assertion itself.
- **No CORE-R2 (`call_lease`/admission) SQL error, and no unexpected SQL error.**

**Cleanup proof (LOOP 6).** After all suite/class runs, a fresh **bounded**
verifier reports **zero** rows in `shopify_connector_call_lease`, `…_job`,
`…_store`, `…_job_log`, `…_store_credential` — zero synthetic residue.
`pg_stat_activity` shows **0** stray Odoo backends, **no** idle-in-transaction
session, and no lingering `call_lease`/`FOR SHARE` cursor — no worker thread or
open test cursor leaked. A leakage scan of every run log finds **no** `shpat_`
token (incl. the test dummy), **no** `Authorization`/`X-Shopify-Access-Token`
header, **no** GraphQL query/mutation body, **no** credential value, and **no**
raw worker exception detail (the only `graphql`/`secret` log hits are test-method
*names*, not values; worker diagnostics are type-only as designed).

### 4.2 Runtime defects found and corrected `[Fact — this session]`

Four defects were found and corrected **on the earlier build `34808200`; all
four corrections are contained in the validated head `c0d4559`** and are
re-verified green by the §4.1 exact-head run. **All four are in the single
authorized test file `tests/test_disconnect_quiescence.py`; no production
model/transport code was changed, and no invariant (locking, generation gate,
token-read-once, lease durability, exception taxonomy, cursor bounds, thread
containment, cleanup) was weakened.**

1. **`TestBusinessAdmission` never entered registry test mode.** `_admit` opens a
   genuinely independent `self.env.registry.cursor()` (the durability invariant,
   proven cross-connection by `TestGenuineRealAdmission`). A plain
   `TransactionCase` does **not** patch the registry, so that cursor is a separate
   connection which cannot see the class's *uncommitted* fixture store → `_admit`'s
   `SELECT … FOR SHARE` finds `row is None` and fails closed with
   `ShopifyQuiescedError` → **12 errors**. Fix: a `setUp` that calls Odoo's
   sanctioned `registry_enter_test_mode()` so every `registry.cursor()` reuses the
   single test connection (the exact "TestCursor sharing the test connection" the
   module docstring already relies on). Production is unaffected (real stores are
   committed).
2. **Traceback assertion vs. `assertRaises`.**
   `test_body_exception_bare_reraise_…` asserted on
   `caught.exception.__traceback__`, but `unittest.assertRaises` stores the
   exception via `with_traceback(None)` — the traceback is always stripped, so the
   "body raise site kept" check saw `''` and could never pass. Fix: capture the
   **live** exception in its own `except` handler (a strictly stronger check of the
   bare-re-raise traceback-preservation invariant).
3. **Opacity assertion flaky on a random hex key.**
   `test_lease_opaque_…` asserted `assertNotIn(str(store.id), lease_key)` against a
   random `uuid4().hex`; a decimal id can appear in a 32-char hex by chance (`'15'`
   in `7c4c9ec0015e4c6c964e110b53bc6b5c`). Fix: a deterministic opacity proof —
   `uuid4` version == 4 and RFC-4122 variant, plus the (valid, long-token)
   non-containment of the token.
4. **Concurrent-admission test deadlock (framework-level).**
   `test_two_real_concurrent_admissions_…` spawns worker threads whose
   `api.Environment(wcr, …)` calls `Registry(cr.dbname)` →
   `Registry.__new__` → `with cls._lock:`. Odoo's `ThreadedServer.run()` holds the
   reentrant `Registry._lock` across the **whole** `preload_registries` /
   post_install phase (`service/server.py:706`), so a spawned thread can never
   acquire it → both workers hang, the admission code never runs, 120 s timeout,
   `worker thread still alive`. (The single-threaded genuine tests avoid this
   because they build the Environment on the **main** thread, reentrantly.) Fix:
   decouple the worker threads for the bounded window with a fresh registry lock
   (`patch.object(type(self.registry), '_lock', threading.RLock())`) — the registry
   is fully built and only read (cached `registries[db]` lookup), so this preserves
   real mutual exclusion among the test threads and weakens nothing; it is the same
   lock decoupling Odoo's own `_registry_test_mode_patches` performs. After the fix
   the two genuine concurrent admissions complete in ~0.1 s with distinct committed
   leases (3/3 stable reruns).

Additionally, synthetic DB residue (5 stores / 10 jobs / 3 leases) left by
**pre-fix** deadlocked concurrent runs — whose outer `finally` hit
`_assert_workers_dead` (raising on the still-alive workers) **before** reaching
`_cleanup` — was scrubbed. That residue was the sole cause of a transient
pre-existing `TestJobDispatch.test_extension_seam_…` pollution failure, which
passes once the DB is clean. With defect 4 fixed, the genuine tests reach
`_cleanup` normally and leave zero residue.

### 4.3 The seven `notification_type` errors — base-vs-head attribution (LOOP 3) `[Fact / Open]`

Seven `setUpClass` errors surface **only on post-init test re-runs** (both `-u
<module> --test-enable` and standalone `--test-tags /<module>` reproduce them
identically) and **never on the fresh install** (§4.1-A: `0 of 325`, with these
same classes running and passing). They are:

- Core (6): `TestConnectionLifecycle`, `TestCredentialAccess`,
  `TestCredentialService`, `TestJobLogSystemAppend`, `TestReadinessSlotClosure`,
  `TestTestConnection`.
- Sale (1): `TestCustomerBinding`.

**Cause (empirically confirmed).** Each class's shared `_create_group_user`
helper does `env['res.users'].create({name, login, group_ids})` **without
`notification_type`**. `res.users.notification_type` is a **base `mail`
computed-stored field** (`odoo/addons/mail/models/res_users.py:29-33`,
`compute='_compute_notification_type'`, no plain `default=`) whose value derives
from `group_ids`/`share`. It is populated correctly on a fresh `-i` install and
in ordinary operation (an `odoo-bin shell` `res.users.create` with the same vals
yields `notification_type='email'`), but the compute leaves it `NULL` for these
bare fixtures on a post-init test re-run → base `NOT NULL` violation on
`res_users.notification_type`. The **full traceback is 100% base Odoo**
(`test_*.py setUpClass → _create_group_user → res.users.create →
odoo/addons/base/models/res_users.py → odoo/orm/models.py:_create → cr.execute →
NotNullViolation`) with **zero CORE-R2 frames**.

**Base-vs-head A/B attribution.** A literal separate-DB `ce504f` suite run was
**not physically possible** in this environment (the injected PostgreSQL role has
no `createdb` privilege — `pg_roles`/`pg_database` are not even readable — and the
Odoo.sh container is bound to a single injected database per platform contract;
running `ce504f` code against the head DB would downgrade/corrupt the head schema
and destroy the evidence environment). Attribution is instead established
rigorously and variance-free by:

1. **Byte-identity:** all seven failing test files are **byte-identical** between
   `ce504f` and `c0d4559` (`git diff ce504f..c0d4559 -- <file>` empty for each;
   re-checked in a detached `ce504f` worktree).
2. **Causal disjointness:** the CORE-R2 production diff (`models/*.py`,
   `security/ir.model.access.csv`, `__manifest__.py`) **never references**
   `res.users` / `res_users` / `notification_type` / `_create_group_user` /
   `group_ids` (grep empty).
3. **Base mechanism:** the failing stack has zero CORE-R2 frames and the cause is
   a base `mail`/`res.users` computed field + a base DB `NOT NULL` constraint —
   present regardless of the branch.

Because the failing test code is byte-identical on `ce504f`, the CORE-R2 diff is
causally disjoint from the failure path, and the traceback stays entirely in the
fixture/base Odoo `res.users` path, this is a **high-confidence baseline
attribution**: the seven errors are treated as base/pre-existing, not a CORE-R2
regression. This is code-identity + empirical-base-mechanism attribution, not a
literal reproduction — **a literal separate-database `ce504f` A/B run was not
executed** (the single-DB, no-`createdb` Odoo.sh platform did not permit one
here). **RR-F remains open**; **issue #157** tracks the literal reproduction and
the separate fix decision. The files are **outside the 16-file PR and this
session's authorized files**, so they were left untouched and flagged for the
appropriate non-CORE-R2 owner (decide whether `_create_group_user` should pass
`notification_type`, or whether the base post-init-rerun behavior is accepted).

**SRR-03 remains OPEN.** Runtime-green of the *foundation-slice* admission tests
does not close SRR-03: the disconnect controller, the conflicting lifecycle
update-lock/epoch bump, and Direction-C finalization are still deferred (§5), so
the admission-vs-disconnect linearization is not closed end to end. No remediation
is claimed.

### 4.4 Evidence commit `[Fact]`

No CORE-R2 defect was exposed by the exact-head runs, so **no production or test
code was changed** in this closure session (LOOP 7 not triggered). The validated
**code** SHA is and remains `c0d455938b4a087407d6c712acbcc8bcf1b06feb`. This
closure commits **only the reconciled evidence documents** (this file, the AR-047
exact-head note, the research-handoff top entry, and the SRR-03 factual-staleness
correction); that docs-only commit advances the branch head but does **not** alter
the validated code SHA, and its creation required no runtime execution. PR
**#156** is kept **draft and unmerged**; Slice 2 is not started.

---

## 5. Intentionally deferred (Slice 2/3) `[Recommendation — later slices]`

Not in this slice (each explicitly forbidden by this session's scope):

- `disconnecting` state value and the two-phase `action_disconnect`.
- The conflicting lifecycle update-lock (`FOR NO KEY UPDATE`/`FOR UPDATE`) on
  disconnect / reconnect / credential-replace / activation, and the epoch bump.
  **Because this is deferred, the admission-vs-disconnect linearization is NOT
  yet closed end to end** — the admission (`FOR SHARE`) half exists; the
  conflicting lifecycle half does not.
- The disconnect controller `_run_disconnect_quiesce`, its cron, `POLL_DELAY`
  cadence, and `try_lock_for_update(limit=1)` selection.
- Direction-C `timed_out`/`completed` finalization, credential-clear at finalize,
  and lease cleanup; the `disconnect_*` escalation store fields.
- Product/customer importer call-site migration to `with execute_business(...)`
  and the store test-connection → `execute_lifecycle` migration.
- Removal/privatization of public `execute()` and the `execute_lifecycle` entry.
- `MAX_CALL_LIFETIME`/`DISCONNECT_QUIESCE_TIMEOUT`/`POLL_DELAY` dispatcher
  constants (only a local `_CALL_LEASE_LIFETIME_SECONDS = 300` foundation default
  is used to stamp `expires_at`, tuning-only, inert this slice).

---

## 6. Admission transaction sequence (as implemented) `[Fact — static]`

`_admit(job, store)`, one owned side transaction:

1. open an owned side cursor (`self.env.registry.cursor()`);
2. `SELECT state, connection_generation FROM shopify_connector_store WHERE id=%s
   FOR SHARE` — shared row lock + fresh read under the lock;
3. if the store row is gone → refuse;
4. validate a real job was supplied (`job`, `job.id`, `job.exists()`);
5. validate `job.store_id.id == store.id`;
6. validate `state == 'connected'`;
7. validate `connection_generation == job.expected_connection_generation`;
8. read the access token exactly once (`_get_access_token`, via the side env,
   under the lock);
9. generate an opaque `lease_key = uuid.uuid4().hex`;
10. insert the lease (ORM create on the side env, normal ACL);
11. `side_cr.commit()` — persists the lease **and** releases `FOR SHARE`
    together;
12/13. close the side cursor (`finally`); on any refusal/error the side txn is
    rolled back (releasing the lock) then closed, and the error re-raised.

Then `execute_business.__enter__` calls `_send(store, body, token)` with the one
in-memory snapshot — **no lock is held across the network call, no second
credential lookup.**

**Token-read-once proof (static):** the only `_get_access_token` call on the
business path is step 8; `_send` skips its read because `token is not None`.
Legacy `execute()` is unchanged (its pre-existing pre-check read + `_send`'s
`token is None` read — a pre-existing two-read behavior this slice does not alter;
it collapses to one read when `execute()` is privatized in a later slice).

---

## 7. Adversarial self-review `[Fact — this session]`

An independent four-lens adversarial review (transaction isolation & cursor
lifecycle; token-read-once & secret leakage; Odoo 19 / test-runtime correctness;
scope/allowlist/compatibility) was run against the actual diff. Outcome:

- **No confirmed in-scope defects.** Token-read-once holds (exactly one credential
  read per admitted call). Cursor lifecycle is leak-proof on success / refusal /
  exception / commit-failure. `@contextmanager` semantics correct (lease released
  on normal, exception, and pre-`yield` `_send` failure; caller exception not
  suppressed). Only the owned side cursor commits; no advisory lock; no
  main-cursor commit. Only allowlisted files changed; legacy `execute()` and the
  three forbidden-to-edit `_send`-patching test files remain compatible; slice is
  dormant (no production call site enters `execute_business`).
- **Verified (not a gap):** a missing/empty credential on the `execute_business`
  path raises the accepted `ShopifyClientError(ERROR_AUTH, REASON_TOKEN_INVALID,
  credential_invalid=True)` **before** lease creation and before `_send`
  (correction §0.1 blocker 1) — runtime-proven by
  `TestBusinessAdmission.test_missing_credential_raises_shopify_client_error`
  (§4.1.E). Production call-site activation remains deferred to a later slice.
- **Noted as future-slice (not a defect here):** a caller that already holds a
  conflicting store-row update lock on its main cursor before entering
  `execute_business` could self-block — belongs to the later
  call-site/lifecycle slice.
- **Two runtime assumptions the tests rest on (documented, both expected to
  hold):** (a) the `TestBusinessAdmission` class opens a nested side
  `registry.cursor()` while the test cursor is live — this relies on Odoo's
  `test_lock` being **reentrant** (`RLock`), the established pattern Odoo core
  itself uses to commit a side transaction inside a `TransactionCase`; (b) the
  genuine-connection statement-timeout bound was hardened from a session `SET`
  to `SET LOCAL statement_timeout` so it covers each cursor's single transaction
  and auto-resets at commit — no leak onto the pooled connection. Both are the
  control-room's to confirm at Odoo.sh runtime along with the rest of the suite.

**Correction-pass synchronous review (review `4680664964`).** Two independent
synchronous reviewers examined the correction diff. The API-contract/precedence
reviewer confirmed **all three blocker corrections correct** (store-config
`UserError` parity; missing-token `ShopifyClientError` before lease; `_send`
`RequestException` mapping; `_normalize_response` parity; and the precise
`raise primary_error from release_error` precedence that preserves contextlib's
`exc is value` identity so the caller's exception is never suppressed) — no
in-scope defects. The genuine-tests reviewer confirmed the real-boundary test
mechanics sound (registry-cursor patch scope, REPEATABLE-READ snapshot timing,
closure binding, caller-rollback independence, two-thread non-blocking
concurrency, FK-ordered fail-loud cleanup, imports/collection, no live network)
and found **one confirmed defect**: the fixtures created a `connected` store then
called `action_set_token`, which demotes it to `reconnect_needed`, so enqueue/
admission would refuse. **Fixed** by re-asserting `state='connected'` after
`action_set_token` in both fixtures (and a minor two-thread cleanup/join race was
hardened by joining workers before cleanup). Static validation (LOOP 6) re-run
green after the fixes.

**Hardening-pass synchronous review (review `4681564744`).** A synchronous
reviewer traced all nine hardening challenges (cursor timeout coverage;
cursor-open-failure cleanup; thread lifetime vs registry-patch lifetime; worker
cleanup-failure propagation; diagnostic leakage; zero-residue completeness;
traceback preservation + double-release; new-test correctness; scope drift) and
found **no confirmed defects** — every genuine cursor is transaction-locally
bounded, setup-failure closes the cursor, workers are joined + proven dead before
patch restore and before cleanup, diagnostics are strictly type-only, zero-residue
covers job-logs with unittest assertions, and the outer handler's successful
release uses a bare `raise` (identity + traceback preserved, release once,
`from`-chained only on dual failure). The one non-blocking note (a worker wedged
past the 20 s bound) is unreachable given the added cursor timeouts + the
`release_gate` unblock, and would be a fail-loud test failure (never a false pass)
if it somehow occurred.

---

## 8. Exact changed files (12 addon + 4 docs) `[Fact — static]`

Addon (allowlist):
`models/__init__.py`, `models/shopify_connector_api_client.py`,
`models/shopify_connector_call_lease.py` (new),
`models/shopify_connector_store.py`, `models/shopify_connector_job.py`,
`models/shopify_connector_job_enqueue.py`, `security/ir.model.access.csv`,
`__manifest__.py`, `tests/__init__.py`,
`tests/test_disconnect_quiescence.py` (new), `tests/test_api_client.py`
(minimal regression), `tests/test_job_enqueue.py` (minimal regression).

Docs: this file (new), `architecture-review-log.md` (AR-047 foundation note),
`sync-engine-risk-register.md` (SRR-03 update), `research-handoff.md`.

**Allowlist reconciliation note:** the gate/task named the regression files as
`test_shopify_connector_api_client.py` / `test_shopify_connector_job_enqueue.py`;
the repository's actual files are `test_api_client.py` / `test_job_enqueue.py`
(no `shopify_connector_` prefix). The real files were used — they are the only
existing api-client / job-enqueue test files, i.e. the "existing core
API-client/job-enqueue tests" the gate refers to.

---

## 9. Residual risks `[Recommendation] / [Open]`

- **RR-A (linearization not yet closed):** the conflicting lifecycle update-lock
  is a later slice, so end-to-end admission-vs-disconnect atomicity is **not**
  demonstrated by this slice. The admission half is correct in isolation.
- **RR-B (runtime — CLOSED for the admission slice):** the Foundation admission
  tests are **executed and green on Odoo.sh `c0d4559`** (build 34818964; §4.1),
  so RR-B no longer holds for this slice. The *remediation* runtime proof
  (end-to-end + genuine two-server) remains open under RR-A / RR-C / SRR-03.
- **RR-C (genuine two-server / multi-worker deployment proof deferred):** proofs
  13/14/15 were executed through the **real in-process production admission
  boundary** (`execute_business`/`_admit`/ORM lease/`_release_lease`) using
  **genuine independent PostgreSQL connections**, proving committed lease
  visibility before `_send` and two concurrent real admissions with distinct
  leases (§4.1.D). Only the genuine **two-server / deployed multi-worker**
  production proof remains deferred, under T-19 / SRR-09 / RR-4.
- **RR-D (dormant ACL/user-identity):** the lease ACL is admin-only; when a
  production call site activates `execute_business`, the drain's actual execution
  identity must be re-checked against this ACL (later slice).
- **RR-E (missing token on the business path — HANDLED):** `execute_business`
  raises the accepted `ShopifyClientError(ERROR_AUTH, REASON_TOKEN_INVALID,
  credential_invalid=True)` on a missing/empty token **before** any lease or
  `_send` (correction §0.1 blocker 1), runtime-proven by
  `TestBusinessAdmission.test_missing_credential_raises_shopify_client_error`
  (green, §4.1). The only residual is that this still-dormant path is not yet
  reached by a production call site (a later call-site slice).
- **RR-F (literal second-DB baseline run — OPEN):** the seven `notification_type`
  errors carry a **high-confidence baseline attribution** — byte-identical
  fixture files, a causally disjoint CORE-R2 diff, and a traceback confined to
  the fixture/base Odoo `res.users` path (§4.3) — but **a literal isolated
  `ce504f` A/B run was not executed**; the single-DB, no-`createdb` Odoo.sh
  platform did not permit one here. **RR-F remains open.** **Issue #157** tracks
  the literal reproduction and the separate fix decision; if a literal A/B is
  run, the six core + one sale `setUpClass` errors are expected to reproduce
  identically.

---

## 10. Rollback `[Recommendation]`

- **Revert the foundation commit** on `claude/core-r2-implementation-foundation`
  (single-commit revert). Because the slice is **dormant**, no production behavior
  changes on revert.
- **Current callers remain on the old execution path** regardless — `execute()`
  is unchanged and is the only live caller; `execute_business` has no production
  caller, so **no production lease holder can exist**.
- The **additive fields** (`store.connection_generation`,
  `job.expected_connection_generation`) and the **`call.lease` table** may safely
  remain **inert** if the code is reverted (they are read only by the reverted
  admission). Schema removal, if desired, requires a **later migration** — never
  a prerequisite of the code revert.
- No ordered zero-holders rollback is needed in this slice (that procedure,
  packet §17, applies once real holders can exist — i.e. after call-site
  activation, a later slice).

---

## 11. Confirmations

- Base `ce504f42824807e215ee21df3dfd4eed9bb9a275`; only allowlisted files changed;
  no product/sale file, no cron, no controller, no `disconnecting` state, no
  `action_disconnect` change, no live Shopify call.
- **SRR-03 remains OPEN.** No *remediation* runtime-green is claimed. The
  Foundation admission slice **is** runtime-validated on Odoo.sh `c0d4559` (build
  34818964; §4.1); the seven `res_users.notification_type` errors carry a
  **high-confidence baseline attribution** (not CORE-R2) — byte-identical
  fixtures, a causally disjoint diff, and a base-only traceback (§4.3). A
  literal separate-database `ce504f` A/B run was **not executed**; **RR-F
  remains open**; **issue #157** tracks the literal reproduction and separate
  fix decision.
- Draft PR only — not marked ready, not merged; Slice 2 not begun.

---

# CORE-R2 — Foundation Slice 2A implementation evidence — runtime pending

> **Status: static-validated implementation record for control-room review.
> NO Odoo runtime was available in this session — no runtime-green is claimed
> for Slice 2A (§8 of the Slice-2A gate: "When an Odoo runtime is unavailable,
> state that clearly. Do not claim runtime green").** This section records the
> lifecycle/controller half of CORE-R2 implemented on top of the merged
> Foundation Slice 1. It does **not** modify, weaken, or re-claim any Slice-1
> evidence above.

## S2A.0 Exact base / branch / gate

- **Base SHA:** `Shopify-connector` @
  `912801508155c6358e8f5f1a7a0aaf01ae573675` (the merge of PR #156 —
  Foundation Slice 1). Verified: local `HEAD`, `origin/Shopify-connector`
  tip, and the base of open draft PRs #150/#151 all equal this SHA.
- **Branch:** `claude/core-r2-foundation-slice-2a-mr7uwq` (environment-assigned;
  the gate's preferred name `claude/core-r2-slice-2a-disconnect-controller` was
  superseded by the assigned branch, per the gate's own "remain on that assigned
  branch" clause).
- **PR #150 / #151:** confirmed open, draft, unmerged — untouched.
- **Gate:** the CORE-R2 Slice-2A implementation prompt.

## S2A.1 Foundation Slice 1 inventory confirmed (not duplicated/redesigned)

Present and reused unchanged: the `shopify.connector.call.lease` model
(Integer `job_id`, indexed `expires_at`); `execute_business` context manager
(parity + deterministic exception precedence); `_admit` store-row `FOR SHARE`
admission; single-token `_send(store, body, token)`; `store.connection_generation`
(previously inert); `job.expected_connection_generation` (captured at enqueue);
`_release_lease`; and the Slice-1 test scaffolding. Slice 2A does **not** re-open,
alter, or weaken any of these.

## S2A.2 Implemented lifecycle/controller behavior `[Fact — static]`

- **Store state + fields.** New `disconnecting` state; new
  `disconnect_status` (`none`/`requested`/`quiescing`/`completed`/`timed_out`),
  `disconnect_status_reason`, `disconnect_open_lease_count`,
  `disconnect_oldest_admitted_at`, `disconnect_requested_at`,
  `disconnect_requested_by` (M2o `res.users`), `disconnect_completed_at`. All
  additive; existing rows backfill to `disconnect_status='none'` / empty / 0.
- **Generation-changing lifecycle lock** (`_lock_store_for_lifecycle`): a
  **blocking** `SELECT … FOR NO KEY UPDATE` on the store row (raw, main cursor),
  with `flush_recordset` before and `invalidate_recordset` after; conflicts with
  admission's `FOR SHARE`; never `SKIP LOCKED` (a lifecycle transition must
  wait); released at the natural RPC/cron-boundary commit (no explicit
  main-cursor commit). Applied to `action_disconnect`, `action_activate`, and the
  reconnect-success write; each bumps `connection_generation` **exactly once**.
- **Two-phase `action_disconnect`:** lock+fresh-read → bump epoch → `state`
  `disconnecting`, `disconnect_status='requested'`, stamp requester/time → one
  non-blocking A/B (queued/retry_waiting) sweep → wake controller → return. Does
  **not** clear the credential, wait for holders, write a locked running job row,
  or commit the main cursor. Repeated disconnect while
  `disconnecting`/`disconnected` = audited idempotent no-op.
- **Quiescence controller** (`_run_disconnect_quiesce`, cron): one store per
  invocation via `search(order='disconnect_requested_at, id').try_lock_for_update(limit=1)`
  (`FOR UPDATE SKIP LOCKED LIMIT 1`) — next unlocked store, all-locked → no-op.
- **Direction-C lease interpretation + finalization** (`_process_disconnect_quiesce`):
  counts **all** committed lease rows (expired = unknown/live, still counts);
  writes the escalation snapshot; **zero rows → `completed`** (credential cleared
  under the held store `FOR UPDATE`, store→credential order, `state=disconnected`);
  **rows before timeout → `quiescing`** (delayed re-poll); **rows at/past
  `DISCONNECT_QUIESCE_TIMEOUT` → `timed_out`** (bounded, secret-free escalation
  snapshot of ≤ 20 opaque `lease_key`s / Integer `job_id`s; credential cleared;
  `state=disconnected`; residual lease rows cleaned up **only after** the
  `timed_out` finalize). `completed` and `timed_out` are observably distinct.
- **Delayed repoll** (`_trigger_disconnect_controller(at=now+POLL_DELAY)`): a
  still-quiescing store schedules exactly one bounded delayed trigger; no
  immediate same-store re-trigger, no busy loop, no sleep.
- **Lifecycle request matrix during `disconnecting`:** business job create
  (existing connected-only gate) and start (existing write→running gate) and
  `execute_business` admission all already fail-closed for `disconnecting`
  (`state != 'connected'`); `action_test_connection`, `action_activate`, and
  `action_reconnect` are refused; `action_test_connection` is migrated through the
  new `execute_lifecycle(purpose='test_connection')` (purpose→state matrix:
  `setup_incomplete`/`connected`/`reconnect_needed`), which also refuses any
  lifecycle call while `disconnecting`.
- **Constants** (`shopify_connector_job_dispatch.py`): `DISCONNECT_QUIESCE_TIMEOUT
  = timedelta(minutes=15)` (> the 300 s admission lease lifetime),
  `POLL_DELAY = timedelta(minutes=1)` (≥ the `_trigger` 1-minute granularity).
  `MAX_CALL_LIFETIME` was **not** re-added: the lease lifetime already lives in
  `api_client._CALL_LEASE_LIFETIME_SECONDS = 300`; a second constant would be a
  forbidden alias.
- **Controller cron** (`data/shopify_connector_cron_disconnect.xml`): one
  `ir.cron` (priority 0, `user_id=base.user_root`, 5-minute recovery heartbeat)
  calling `model._run_disconnect_quiesce()`; registered in `__manifest__.py`
  (version `19.0.1.6.0` → `19.0.1.7.0`).

## S2A.3 Exact changed files

Allowed by the Slice-2A gate §3:
`models/shopify_connector_store.py`, `models/shopify_connector_api_client.py`
(execute_lifecycle + test-connection migration only),
`models/shopify_connector_job_dispatch.py` (two controller constants only),
`__manifest__.py`, `data/shopify_connector_cron_disconnect.xml` (new),
`tests/test_disconnect_quiescence.py`, and this document.

**Not needed / not touched (in-scope-allowed but unchanged):**
`models/shopify_connector_job.py` (the existing connected-only start gate already
makes `disconnecting` non-startable — no change required),
`models/shopify_connector_store_credential.py` (the finalize reuses
`action_clear_token` as-is under the store lock — no clear-ordering change was
needed), `tests/__init__.py` (no new test file, no import change).

**⚠️ Scope deviation flagged for control-room ratification.** The two-phase
`action_disconnect` (§5.C — non-negotiable accepted contract) necessarily
supersedes single-phase disconnect assertions in **two existing test files not
listed in the Slice-2A §3 allow-list**:
`tests/test_connection_lifecycle.py` and `tests/test_job_dispatch.py`. The merged
CORE-R2 **packet §4** allow-list explicitly authorized "`tests/test_disconnect_quiescence.py`
(+ **minimal regressions in existing core dispatch/store/api-client tests**)"; the
Slice-2A §3 re-frozen list dropped that clause. Because §5.C cannot be delivered
green without it, **minimal, surgical** migrations were applied to only the
obsolete single-phase disconnect assertions in those two files (state
`disconnecting` not `disconnected`; credential cleared at controller finalize not
in Phase 1; A/B sweep = queued/retry_waiting). Nothing else in those files
changed. This is flagged here, in the handoff, and in the PR body; the PR stays
draft. **Requested control-room action:** ratify these two files as the
packet-§4 "minimal regressions in existing tests," or reissue a corrected §3
list.

## S2A.4 Tests added (authored; NOT executed — no runtime this session)

`tests/test_disconnect_quiescence.py` gains 30 Slice-2A tests across four
classes, covering all 24 required scenarios:

- `TestDisconnectPhase1` (10): connected→disconnecting; generation +1 exactly
  once; repeated-disconnect audited no-op; A/B sweep scope; running-job never
  written; disconnecting non-startable; test-connection refused (action +
  execute_lifecycle); activate/reconnect refused; activation bumps generation.
- `TestQuiescenceController` (12): zero→completed→cleared→disconnected;
  credential-present-before-timeout; live-lease quiescing; expired-lease still
  quiescing (direction C); deadline→timed_out (≠ completed); timed_out clears
  credential; cleanup only after timed_out; completed requires zero rows; delayed
  repoll at ≥ now+POLL_DELAY with no immediate re-trigger; one store per
  invocation; duplicate-invocation idempotent; no secret in fields/snapshot/audit.
- `TestDisconnectSourceGuards` (6): no main-cursor commit; SKIP LOCKED LIMIT 1
  selection; blocking FOR NO KEY UPDATE (not SKIP LOCKED); delayed `_trigger(at=)`
  + no busy-loop/sleep; store→credential clear order; controller makes no Shopify
  call.
- `TestDisconnectControllerSelectionGenuine` (2, `post_install`, genuine
  `db_connect` connections): locked-first store doesn't block a later one;
  all-locked is a safe no-op.

Existing Slice-1 tests are **not** weakened. The two migrated test files' other
tests are unchanged.

## S2A.5 Static checks run this session `[Fact — verified]`

No Odoo runtime (Odoo not importable; no `odoo-bin`). Static tooling only:

- `py_compile` on every changed `.py` — **OK**.
- `compileall -q addons/shopify_connector_core` — **OK**.
- XML parse of both cron data files — **OK**.
- Manifest `ast.literal_eval`; version `19.0.1.7.0`; new data file registered — **OK**.
- Precise 7-char git conflict-marker scan — **none**.
- Circular-import check: `store → job_dispatch → job` is acyclic (nothing those
  depend on imports `store`) — **OK**.
- Source guards: no `self.env.cr.commit`/`self._cr.commit`/`.commit()` in
  `store.py`; no product/sale file changed; controller/finalize contain no
  `_send`/`requests`/`.execute(`/`execute_business`/`execute_lifecycle`; no
  `shpat_` literal in production models/data; `completed` gated on zero rows;
  `timed_out` distinct; `_trigger(at=` present; no `while True`/`time.sleep`/
  `import time`; no `architecture-review-log.md` / `research-handoff.md` /
  `sync-engine-risk-register.md` change — **all OK**.

## S2A.6 Unresolved runtime gates (deferred)

- **Odoo.sh exact-head runtime of the full `shopify_connector_core` suite**
  (fresh install + per-class) — **NOT run this session; required before any
  runtime-green claim.**
- Genuine **two-server / multi-worker** proof of admission↔disconnect
  linearization (T-19) — deferred (SRR-09 / RR-4).
- Live/dev-store Shopify validation — **not authorized, not performed.**
- The seven base `res_users.notification_type` post-init-rerun artifacts
  (issue #157) are pre-existing and out of scope.

## S2A.7 No call-site activation

The product and customer importers still call the legacy `execute()` and are
**unchanged**; `execute_business` remains dormant (no production business call
site). Public `execute()` is **not** removed (deferred). So the
admission↔disconnect linearization is now implemented on **both** halves
(admission `FOR SHARE` + lifecycle `FOR NO KEY UPDATE`/controller `FOR UPDATE`)
but is **not exercised end-to-end by a live domain handler** — activation is a
later slice.

## S2A.8 Confirmations

- **SRR-03 remains OPEN.** No remediation runtime-green is claimed; end-to-end
  disconnect-quiescence is not proven live.
- No live Shopify request; no real credential/token used.
- PR stays **draft**; not marked ready; not merged. Slice 2B not begun.

---

# CORE-R2 — Foundation Slice 2A — lifecycle-race correction (review 4690639375)

> **Status: static-validated correction record for control-room review. Still no
> Odoo runtime this session — no runtime-green claimed.** Applied on top of the
> Slice-2A head `b3d23cb` after control-room review **4690639375** (VERDICT:
> REVISE BEFORE ODOO.SH RUNTIME).

## S2A-C.0 Scope ratification (review 4690639375)

The two previously-flagged test files are **RATIFIED** as the CORE-R2 packet §4
"minimal regressions in existing core dispatch/store/api-client tests":
`tests/test_connection_lifecycle.py`, `tests/test_job_dispatch.py`. Commit
`ce4ab38` is **not** rejected for allow-list drift. The corrected allow-list for
this pass is `store.py`, `api_client.py`, `store_credential.py`,
`tests/test_disconnect_quiescence.py`, `tests/test_connection_lifecycle.py`,
`tests/test_job_dispatch.py`, `tests/test_credential_service.py`,
`tests/test_api_client.py`, and these two docs. **No cron/manifest/other file
was changed in this correction.**

## S2A-C.1 Defect 1 — activation/reconnect fresh-state TOCTOU (fixed)

**Root cause.** `action_activate` and successful `action_reconnect` validated
pre-lock, then took `_lock_store_for_lifecycle()` but **ignored** the locked
`(state, generation)` and wrote `connected` — so a disconnect winning before the
lock could be overwritten (one-way lifecycle violated) and the epoch mis-bumped.

**Correction (`store.py`).**
- `action_activate`: takes the lock **first**, consumes the locked
  `(state, generation)`, refuses if the fresh state is `disconnecting`/
  `disconnected`, re-validates every evidence precondition under the lock, and
  bumps `connection_generation = locked_generation + 1` exactly once only on
  success. No Shopify call is made while the lock is held.
- `action_reconnect`: captures the epoch at reconnect start; runs the probe +
  readiness **unlocked** (they call Shopify); then finalizes **under the lock**,
  refusing (never overwriting) if the fresh state is `disconnecting` **or** the
  epoch changed since start (a disconnect/activation/credential change won the
  race). A store already `disconnected` at start with an unchanged epoch is a
  *legitimate* reconnect and proceeds. Single epoch bump on success.
- `action_mark_reconnect_needed` (reachable from the probe's auth-failure
  handler): now also takes the lock and **never overwrites a one-way disconnect**
  (`disconnecting`/`disconnected` → audited no-op); no epoch bump (it is an
  auth-failure degradation, not a reconnect).

## S2A-C.2 Defect 2 — reconnect probe + private lifecycle entry (fixed)

**Root cause.** `action_reconnect` probed via public `action_test_connection`
(`purpose='test_connection'`, which excludes `disconnected`), so reconnect after
a completed disconnect was broken; and the b3d23cb `execute_lifecycle` was a
**public** method exposing a caller-controlled `purpose` over RPC (also breaking
the `{execute, execute_business}` public-surface guard).

**Correction (`store.py`, `api_client.py`).**
- Shared **private** `_run_connection_probe(purpose)` on the store is the single
  implementation behind `action_test_connection` (`'test_connection'`) and
  `action_reconnect` (`'reconnect_probe'`) — identical transport/normalization/
  mirror/audit; only the allowed-state matrix differs. `purpose` is internal to
  those two trusted callers, never RPC-controlled. The matrix is pre-checked
  before any audit job is created (no dangling job).
- `execute_lifecycle` → renamed **private** `_execute_lifecycle` (defense-in-depth
  transport guard). The public API-client surface is again exactly
  `{execute, execute_business}`.
- `reconnect_probe` permits `disconnected` (reconnect after completed disconnect);
  `test_connection` still excludes it (Test Connection from `disconnected`
  remains refused). Neither permits `disconnecting`.

## S2A-C.3 Defect 3 — credential mutation lock order (fixed)

**Root cause.** `action_set_token`/`action_replace_token` mutated the credential
row **before** linearizing on the store row, permitted replacement during
`disconnecting`, and did not bump `connection_generation` on a connected
replacement — so an admitted old-generation job could capture a newly-replaced,
unverified token.

**Correction (`store_credential.py`).** One shared private `_mutate_token(store,
value, is_replace)`: (1) value-validate before any write (unchanged
`ValidationError` message); (2) lock the **store row first**
(`store._lock_store_for_lifecycle`, `store → credential` global order) and
fresh-read state; (3) refuse all set/replace while `disconnecting` (no credential,
mirror, epoch, or token-bearing audit written); (4) create/update the credential
under the held store lock (normal ACL, **no `sudo()`**); (5) clear
`credential_last_verified_at`, stamp `credential_last_replaced_at` for replace;
(6) if the fresh state is `connected`, atomically move to `reconnect_needed` and
bump `connection_generation` **exactly once**. `action_set_token`/
`action_replace_token` keep `@api.model` and delegate to it — no second
credential path, no new `sudo()` site (the sudo guard still finds exactly three).

## S2A-C.4 Race regression tests added

- `tests/test_disconnect_quiescence.py`:
  - `TestLifecycleRaceCorrections` — activation refuses when a disconnect won
    (no 2nd bump, no audit); reconnect refuses when a disconnect wins **during
    the probe** (real `action_disconnect` injected at the `_send` seam); reconnect
    from `disconnected` connects.
  - `TestCredentialReplacementRaceGenuine` (`post_install`, genuine `db_connect`
    connections through the real `execute_business`/`_admit` + real
    `action_replace_token`): replacement-first → old-generation admission
    **fails closed** (no `_send`, no lease, cannot capture the new token);
    admission-first → uses its captured **old** token, replacement proceeds
    afterward, lease released.
  - `_execute_lifecycle` privacy + purpose→state matrix tests (updated).
- `tests/test_credential_service.py`: set/replace refused while `disconnecting`
  (original credential + mirrors + epoch unchanged); connected set/replace bump
  the epoch exactly once; non-connected set adds no bump; `store → credential`
  lock-order + no-`sudo` source guard.
- `tests/test_connection_lifecycle.py`: `_run_reconnect` parameterized with the
  reconnect entry state (reconnect_probe matrix); reconnect from completed
  `disconnected` connects; Test Connection from `disconnected` refused.

## S2A-C.5 Static checks (this correction, no Odoo runtime)

`py_compile` + `compileall` OK; conflict-marker scan clean; changed set = the 3
production + 3 test files above (no cron/manifest/product/sale change); source
guards OK — activate/reconnect **consume** the locked `(state, generation)` and
revalidate under the lock; `reconnect_probe` used only by reconnect; credential
set/replace refuse `disconnecting`, lock store before credential, bump the epoch
once on connected replacement, use no new `sudo()`; sudo call-sites still exactly
three; public API-client surface still `{execute, execute_business}`; no
main-cursor commit; no token literal in production.

## S2A-C.6 Corrected status

- **SRR-03 remains OPEN.** No runtime-green is claimed (no Odoo runtime this
  session). Exact-head Odoo.sh validation of the full `shopify_connector_core`
  suite is still required (handoff §3–4).
- The credential-replacement refusal during `disconnecting` and the
  `reconnect_probe` wiring are now **Slice-2A correctness (implemented)**, no
  longer deferred to Slice 2B.
- PR #160 stays **draft/unmerged**; Slice 2B not begun; no live Shopify request.

# CORE-R2 — Foundation Slice 2A — probe-snapshot + credential-clear correction (reviews 4690804619 + 4690807427)

> **Status: static-validated correction record for control-room review. Still no
> Odoo runtime this session — no runtime-green claimed.** Applied on top of head
> `415c05c` after control-room reviews **4690804619** ("two lifecycle/credential
> race paths remain open") and its clarification **4690807427** (clear must not
> substitute an immediate connected-state clear for quiescence).

## S2A-C2.0 Objective

Two open race paths, corrected before Odoo.sh runtime:

1. **Lifecycle probe not bound to one credential snapshot.** `_execute_lifecycle`
   delegated to public `execute()`, which pre-checked the credential and then let
   `_send(store, body)` **re-read** it; `_run_connection_probe` then wrote
   verification/failure mirrors **without** revalidating the store generation or
   the credential row — so a concurrent replacement could mark a newly-replaced
   token verified from an old-token response, or invalidate a new token from an
   old-token failure.
2. **Public `action_clear_token` bypassed two-phase disconnect.** It cleared
   without the lifecycle store lock, permitted clearing while `disconnecting`, and
   moved `connected`/`reconnect_needed` → `disconnected` with no epoch bump —
   breaking the invariant that credentials remain present until the controller
   reaches `completed`/`timed_out`.

Plus review §11: `action_disconnect` must write `connection_generation =
locked_generation + 1` from the value returned under the lock.

## S2A-C2.1 Defect 1 — one-snapshot lifecycle probe + post-network revalidation (fixed)

**Correction (`api_client.py`, `store.py`, `store_credential.py`).**

- `_execute_lifecycle` is **removed** and replaced by two private client helpers:
  - `_admit_lifecycle(store, purpose)` — the matrix gate + the **single**
    credential snapshot: one token read (via the sanctioned `_get_access_token`),
    the credential id + version (`write_date`), the store `connection_generation`,
    and the purpose's allowed-state matrix. Takes **no** lock (a probe must not
    hold a lock across the network); fails closed on a bad purpose/state
    (`UserError`) or a missing token (`ShopifyClientError(ERROR_AUTH,
    REASON_TOKEN_INVALID, credential_invalid=True)`).
  - `_send_lifecycle(store, query, token, variables=None)` — issues the request
    with **exactly** the snapshot token via `_send(store, body, token)`, so the
    transport re-reads **no** credential (closing the double-read window). Same
    config-`UserError` / `RequestException`→temporary / `_normalize_response`
    contract as `execute()`. The legacy two-arg `_send(store, body)` seam
    (`execute()`) is unchanged.
- `store._run_connection_probe` now: snapshots via `_admit_lifecycle`, sends via
  `_send_lifecycle`, then — for **success and failure alike** — calls
  `_lifecycle_probe_superseded(snapshot)`, which acquires the **store → credential**
  locks (`_lock_store_for_lifecycle` then the credential-row `FOR NO KEY UPDATE`
  via `store_credential._lifecycle_credential_version(lock=True)`) and rejects the
  result if the locked state left the matrix, the generation changed, or the
  credential id/version/**value** changed. A superseded probe is audited via
  `_audit_probe_superseded` (job → `cancelled`, reason "Connection probe
  superseded by a lifecycle or credential change; rerun it.") and writes **no**
  mirror or credential state. Non-superseded results apply the existing pass/fail
  mirrors under the held lock (TOCTOU-safe). **No lock spans the network call.**
- The credential **value** is compared in addition to id/`write_date` because
  PostgreSQL fixes `write_date` to the transaction timestamp within one
  transaction, so a same-transaction replacement is caught by the value change.
- `action_reconnect` aborts (no readiness, no finalize) when the probe returns
  `'superseded'`.

## S2A-C2.2 Defect 2 — public/controller credential-clear split (fixed)

**Correction (`store_credential.py`, `store.py`; clarification 4690807427).**

- New **controller-only** primitive `store_credential._clear_token_under_store_lock
  (store)`: clears the value + `credential_state` + non-secret store mirrors,
  performs **no** state transition and **no** epoch bump, and takes **no** lock of
  its own (the caller holds the store lock). Both `_finalize_disconnect_completed`
  and `_finalize_disconnect_timed_out` now call it under the controller's held
  store `FOR UPDATE` (they set `disconnected` themselves) — never the public
  `action_clear_token` (which would refuse a `disconnecting` store).
- Public `action_clear_token(store)` now locks the store first
  (`_lock_store_for_lifecycle`) and routes by the locked state:
  `disconnecting` → **refused** (`UserError`); `connected`/`reconnect_needed` →
  **routed** to the accepted two-phase disconnect via the shared
  `store._request_disconnect_locked` (state → `disconnecting`, one epoch bump,
  audited request) with **nothing cleared now** — the controller clears at
  finalize; `setup_incomplete`/`disconnected` → cleared directly under the lock.
  No public path manufactures a clear-before-quiescence.

## S2A-C2.3 Review §11 — `action_disconnect` uses the locked generation (fixed)

`action_disconnect` and the public clear routing share
`store._request_disconnect_locked(locked_state, locked_generation)`, which writes
`connection_generation = locked_generation + 1` from the value returned under the
lock (no indirect `self.connection_generation` re-read). The single-bump
idempotent-no-op contract is preserved.

## S2A-C2.4 Tests added / migrated

- `tests/test_disconnect_quiescence.py`:
  - `TestLifecycleProbeSupersession` (controlled, same-cursor injection at the
    `_send` seam): `_send_lifecycle` receives the exact snapshot token; a
    non-superseded probe applies the pass mirror; supersession by a credential
    **replace** (generation) and by a **disconnect** (state) → job `cancelled`,
    no mirror; an **auth-failure** result during a replace does **not** invalidate
    the replaced token (the named hazard); a `reconnect_needed` replace (no epoch
    bump — value-only supersede) aborts the reconnect **before** readiness.
  - `TestCredentialClearPolicy`: public clear on a `connected` store with an
    outstanding committed lease defers to the controller and does **not** clear
    until zero holders (no premature clear); refused while `disconnecting`; direct
    clear from `setup_incomplete`/`disconnected`; `action_disconnect` bumps the
    generation exactly once from the locked value.
  - Updated the `test_store_then_credential_clear_order` source guard: finalize
    calls `_clear_token_under_store_lock` (not the public `action_clear_token`),
    and `action_disconnect` clears nothing.
- `tests/test_api_client.py`: `_send_lifecycle` passes the snapshot token to
  `_send`; `_admit_lifecycle` reads the token exactly once and snapshots
  id/version/generation/matrix; refuses a state outside the matrix.
- `tests/test_credential_service.py`: connected/reconnect_needed public clear
  **requests two-phase disconnect** (credential still present, one epoch bump);
  refused while `disconnecting`; direct clear from `setup_incomplete`/
  `disconnected` (migrated from the obsolete immediate-`disconnected` contract).
- `tests/test_connection_lifecycle.py`: `_send` seam fakes accept the token
  snapshot; the direct-clear-on-connected test migrated to two-phase routing.

## S2A-C2.5 Scope note — transport-seam regressions (packet §4)

Binding the probe to `_send(store, body, token)` means the lifecycle transport
seam is now three-arg. Two existing tests that patch `_send` with a 2-arg fake and
then drive `action_test_connection` had to widen **only** their fake signatures
(`lambda self, store, body, token=None: …`); **no assertion changed** in either:

- `tests/test_test_connection.py` (api-client/test-connection behavior);
- `tests/test_readiness_slot_closure.py` (its `_run_test_connection` provisioning
  helper).

This is the same packet §4 "minimal regressions in existing core dispatch/store/
api-client tests" class the control room **ratified** for
`test_connection_lifecycle.py` / `test_job_dispatch.py` in review 4690639375, and
is **flagged here for the same ratification**. Net PR scope becomes **15**
addon+doc files: the 12 prior files, `tests/test_api_client.py` (already in the
Round-2 corrected allow-list; newly carries this correction's client-unit tests),
plus the two seam-compat test files above. `test_readiness_check.py` was
**not** touched — it patches `execute` (not `_send`) and never drives the probe.

## S2A-C2.6 Static checks (this correction, no Odoo runtime)

`py_compile` OK for all changed model + test files; AST guards re-verified:
sudo call-sites still exactly three (`job_log`, `readiness_check`,
`store_credential` — **no new `sudo()`**); public API-client surface still
`{execute, execute_business}` (`_admit_lifecycle`/`_send_lifecycle` are private,
`_execute_lifecycle` removed); the four credential service methods keep
`@api.model`; no `.commit()` anywhere in `store.py`; client commits only on
`side_cr`; both `_send(store, body)` and `_send(store, body, token)` seams present;
no token literal persisted or logged (snapshot token is in-memory only). Store →
credential lock order preserved on every clear/probe/mutation path; no lock spans
the network call.

## S2A-C2.7 Corrected status

- **SRR-03 remains OPEN.** No runtime-green claimed (no Odoo runtime this
  session). Exact-head Odoo.sh validation of the full `shopify_connector_core`
  suite is still required (handoff §3–4).
- PR #160 stays **draft/unmerged**; Slice 2B not begun; no live Shopify request;
  no product/sale/cron change in this correction.

# CORE-R2 — Foundation Slice 2A — atomic lifecycle admission + genuine race tests (review 4691182306)

Third control-room pass, at head `756684d`. Two blocking defects; both fixed.
`Fact`s below are static (source/AST) — **no Odoo runtime this session**.

## S2A-C3.0 Scope ratification applied (control-room ruling)

Per the ruling accompanying review 4691182306, the two prior seam-compat files
(`tests/test_test_connection.py`, `tests/test_readiness_slot_closure.py`) are
**ratified**. This round extends the **same packet-§4 transport-seam-compat class**
to every remaining test that drives a lifecycle probe, because defect 1 (below)
makes `_admit_lifecycle` capture its snapshot in an OWNED `registry.cursor()` side
transaction — under a plain `TransactionCase` that side cursor is a genuinely
independent connection that cannot see an uncommitted fixture, so each
probe-driving class must enter **registry test mode** (the sanctioned mechanism
`TestBusinessAdmission` already uses for business `_admit`). This adaptation adds
**no assertion change**; it only makes the production side cursor see the fixture.
The control room approved extending it to `tests/test_connection_lifecycle.py`
(outside the round's initial allowed-list) and adding the test-mode line to the two
ratified seam-compat files. `test_readiness_check.py` was **not** touched (it calls
`run_for_store`/creates jobs directly and never drives `_admit_lifecycle`).

## S2A-C3.1 Defect 1 — lifecycle admission is now atomic (independent FOR SHARE)

**Was** [Fact]: `_admit_lifecycle` performed a plain main-cursor/cached snapshot
with no store-row lock, so `action_disconnect` could win after the probe pre-check
but before `_send`; the probe could still issue an outbound Shopify request that
post-network supersession could only discard *after the fact*.

**Now** [Fact]: `_admit_lifecycle` captures the snapshot in one short **owned side
transaction** — the same accepted mechanism as business `_admit`, minus any lease:

1. `self.env.flush_all()` so the independent cursor observes the caller's state;
2. open `self.env.registry.cursor()` (the side transaction);
3. `SELECT state, connection_generation FROM shopify_connector_store WHERE id=%s
   FOR SHARE` — the linearization lock (conflicts with the lifecycle
   `FOR NO KEY UPDATE`);
4. **fresh** purpose→state matrix re-check on the value read under the lock (no
   purpose lists `disconnecting`);
5. read the access token **exactly once** (the one sanctioned `_get_access_token`);
6. capture the credential row id + `write_date`;
7. `side_cr.commit()` — persists **nothing**, releases the `FOR SHARE`, completes
   the admission linearization — **before** the network call;
8. `side_cr.close()`; return the non-persisted snapshot.

`_send_lifecycle` then runs (a separate call in `_run_connection_probe`) with the
exact snapshot token — **no lock spans the network call, no `call.lease` is
created**. A matrix refusal under the lock (a disconnect that won before the
`FOR SHARE`) raises `UserError`, which `_run_connection_probe` treats as a
**probe superseded before send** (audited `cancelled`, **no** network); a
missing/empty credential at admission raises the accepted `ShopifyClientError`
auth taxonomy (no network); any side-transaction failure rolls back and closes.
The post-network `_lifecycle_probe_superseded` revalidation is unchanged and still
catches a disconnect that wins *after* admission.

`action_disconnect` still writes `connection_generation = locked_generation + 1`
from the value returned under the lock (review 4690804619 §11, retained).

## S2A-C3.2 Defect 2 — genuine independent-transaction race tests authored

Added two opt-in `@tagged('post_install','-at_install')` genuine classes using
real independent `db_connect` connections (distinct backend PIDs; raw SQL only to
commit fixtures, observe, and clean up), plus source guards; the prior
`TransactionCase` supersession/clear tests are **retained and re-documented as
controlled seam-injection tests, not genuine concurrency**.

- **`TestLifecycleAdmissionSourceGuards`** — source guards proving the admission
  owns a side cursor, executes store `FOR SHARE`, re-checks the matrix under the
  lock, reads the token exactly once, commits/rolls back only on `side_cr`
  (never the main cursor), creates no lease, issues no transport call inside the
  admission (AST call-node inspection, so a docstring mention is no false
  positive), commits/closes before the transport, hands the exact snapshot token
  to `_send`, and keeps the post-network revalidation.
- **`TestLifecycleAdmissionRaceGenuine`** — (A) **disconnect-first**: the worker's
  pre-check passes on its stale `connected` snapshot, but the admission `FOR SHARE`
  (fresh, distinct backend) reads the committed `disconnecting` row and refuses
  UNDER the lock → **zero `_send` calls**, superseded, no lease. (B)
  **admission-first**: the admission captures the OLD token/generation, a
  disconnect commits on a distinct backend during the call, the probe finishes
  with **exactly** its captured OLD token, and the post-network revalidation
  discards the stale result (superseded) with **no mirror written**. Plus a
  **store-row lock-attribution** proof (the admission `FOR SHARE` blocks on a held
  `FOR NO KEY UPDATE` and hits its bounded lock_timeout, then succeeds once
  released) and a **threaded genuine-simultaneity** proof (a worker admits and
  parks at the transport seam on one backend while a disconnect commits on
  another; the accepted `Registry._lock` bounded-window pattern; bounded joins;
  worker terminated; distinct worker/disconnect PIDs).
- **`TestPublicClearAdmissionRaceGenuine`** — (A) **business-admission-first**:
  the committed lease outlives admission's brief `FOR SHARE`; a public
  `action_clear_token` on the connected store requests two-phase disconnect and
  clears **nothing**; the controller stays `quiescing` with the credential present
  while the lease is open; after the business call releases the lease, the next
  controller pass reaches `completed` and clears the credential — **exactly one
  generation bump**. (B) **public-clear-first**: the clear requests two-phase
  disconnect (gen +1, credential preserved); a later old-generation business
  admission **fails closed** (no lease, **no `_send`**), and the credential
  remains until the controller finalizes.

The single-shot genuine admission-first / threaded cases run their worker in
**READ COMMITTED** so the post-network `FOR NO KEY UPDATE` revalidation observes
the concurrently-committed disconnect deterministically without the production
request-level serialization-failure retry (production runs REPEATABLE READ + that
retry; both converge on discarding the stale probe result). This is documented in
the `_open_bounded` helper. Every genuine test closes every cursor (try/finally),
joins/asserts-dead every worker thread, and runs a fresh zero-residue verifier
(store / lease / credential / job) plus removes the disconnect + drain cron
triggers it scheduled.

## S2A-C3.3 Test-mode seam-compat (packet §4) — files touched

Registry-test-mode `setUp` added (no assertion changed) to every probe-driving
class: `test_disconnect_quiescence.py` (`TestDisconnectPhase1`,
`TestLifecycleRaceCorrections`, `TestLifecycleProbeSupersession`),
`test_api_client.py` (`TestApiClient`), `test_test_connection.py`
(`TestTestConnection`), `test_readiness_slot_closure.py`
(`TestReadinessSlotClosure`), and — control-room-approved for this round —
`test_connection_lifecycle.py` (`TestConnectionLifecycle`).
`TestCredentialClearPolicy` opens no side cursor (no `_admit_lifecycle`), so it
took **no** test-mode change — only a docstring clarifying it is controlled, not
genuine.

## S2A-C3.4 Static checks (this correction, no Odoo runtime)

`py_compile` + `compileall` OK for the whole module. AST/source guards
re-verified: `_admit_lifecycle` opens an owned side cursor, executes store
`FOR SHARE`, re-checks the matrix on the locked value, reads the token exactly
once, commits/rolls back **only** on `side_cr` (never main), creates **no** lease
(no `.create(`/`lease_key`), makes **no** transport call inside the admission, and
commits before returning the snapshot; `_run_connection_probe` calls
`_admit_lifecycle` before `_send_lifecycle`, routes an under-lock `UserError` to
superseded and a missing-credential `ShopifyClientError` to failure, and retains
the post-network `_lifecycle_probe_superseded` revalidation. Unchanged invariants:
public API-client surface `{execute, execute_business}`; **no new `sudo()`**
(still exactly three call-sites: `job_log`, `readiness_check`,
`store_credential`); the four credential methods keep `@api.model`; **no
`.commit()` in `store.py`**; client commits only on `side_cr`; both `_send`
seams present; store → credential order on every path; **no lock spans the network
call**; no token literal logged or persisted; no product/sale/cron change. Net PR
scope stays **15** addon+doc files (no new file added — `store_credential.py` and
`job_dispatch.py` were not needed this round; the existing
`_lifecycle_credential_version` serves the side-transaction snapshot as-is).

## S2A-C3.5 Corrected status

- **SRR-03 remains OPEN.** No runtime-green claimed. Exact-head Odoo.sh validation
  of the full `shopify_connector_core` suite (handoff §3–4), including the two new
  genuine `post_install` classes, is still required.
- PR #160 stays **draft/unmerged**; Slice 2B not begun; no live Shopify request;
  no product/sale change. Base re-aligned to `Shopify-connector`
  `1494b97d0e2117af05b954dabde92a9e497ac2c3` via a normal merge commit (docs
  histories preserved; no `addons/**` conflict).

# CORE-R2 — Foundation Slice 2A — EXACT-HEAD ODOO.SH RUNTIME VALIDATION (PR #160)

> `[Fact — verified at runtime on the Odoo.sh dev build for PR #160, session date
> 2026-07-14]`. This section is the authoritative exact-head runtime record. It
> was produced **after** the validated code SHA below; the docs commit that carries
> it is **evidence-only and is itself NOT runtime-tested** (Section 14).

## RT.0 Session identity & build-to-commit gate `[Fact]`

| Item | Value |
| --- | --- |
| Validated code SHA (checked out; tree clean) | `79dbfc00428802da8c98c97d3e6d7eb6025ea74e` |
| Branch (PR #160) | `claude/core-r2-foundation-slice-2a-mr7uwq` (local + `origin/…` decorate HEAD) |
| Required base ancestor | `1494b97d0e2117af05b954dabde92a9e497ac2c3` — **2nd parent** of the HEAD merge; `git merge-base --is-ancestor` → true |
| `git status --porcelain` | empty (clean) |
| Odoo | 19.0 |
| PostgreSQL | 16.14 |
| Odoo ORM cursor isolation | **REPEATABLE READ** (server default `read committed` overridden per-connection) |
| Build URL | `https://adamsmen-claude-core-r2-foundation-slice-2a-mr7uwq-34872373.dev.odoo.com` |
| Build ID | `34872373` |
| Database | `adamsmen-claude-core-r2-foundation-slice-2a-mr7uwq-34872373` |
| Installed module versions | `adams_base 19.0.1.0` · `shopify_connector_core 19.0.1.7.2` · `shopify_connector_product 19.0.1.0.0` · `shopify_connector_sale 19.0.1.0.0` |

Gate: **PASS**. `ls-remote` over SSH is unavailable in the webshell (no deploy key);
the remote tip is corroborated by the fetched `origin/claude/core-r2-foundation-slice-2a-mr7uwq`
ref decorating HEAD. Base at `1494b97` had `shopify_connector_core 19.0.1.6.0` → head
`19.0.1.7.2` (additive: adds `data/shopify_connector_cron_disconnect.xml`).

## RT.1 Scope audit — exactly the 15 accepted files `[Fact]`

`git diff --name-status 1494b97..79dbfc0` = 15 files: 6 production
(`__manifest__.py` M, `data/shopify_connector_cron_disconnect.xml` A, 4 models M),
7 tests (all M), 2 docs (`task-core-r2-validation-results.md` M,
`task-core-r2-slice-2a-handoff.md` A). **No** product/sale file, **no** Task 010B/011B
file, **no** issue-157 fixture, **no** live credential/token. Secret scan of the net
diff: the only `shpat_` strings are labelled `shpat_DUMMYDUMMYDUMMY…` test fixtures
+ one doc mention — no live token.

## RT.2 Fresh-install validation (authoritative = build `install.log`) `[Fact]`

The Odoo.sh build performed the sanctioned fresh install at the exact head:
`odoo-bin -i adams_base,shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable`.

- `shopify_connector_core`: **4 failures, 0 errors of 282 tests** (at_install) + **19 post-tests, 0 failed** (`19 post-tests in 0.95s, 792 queries`).
- Disconnect cron installed **once**; both crons present once; new fields + selections created (RT.11); no install/registry/XML/manifest/constraint failure; no duplicate cron/model record.
- The **4 failures are the only failures** and are TEST DEFECTS (RT.3). Fresh install is otherwise green — I quote the Odoo summary above rather than relying on process exit code.

## RT.3 The 4 fresh-install failures — root-caused as TEST DEFECTS (docstring false-positives) `[Fact]`

All four are naive `assertNotIn(<token>, inspect.getsource(<method>))` source-guards
that match the method's **own docstring**, not executable code:

| Test (file) | Token | Where it actually appears |
| --- | --- | --- |
| `TestCredentialService.test_mutate_token_locks_store_before_credential_source` (test_credential_service.py:227) | `sudo(` | docstring "normal ACL, **no `sudo()`**" |
| `TestDisconnectSourceGuards.test_lifecycle_lock_is_blocking_for_no_key_update` (test_disconnect_quiescence.py:1676) | `SKIP LOCKED` | docstring explaining it does *not* use `FOR UPDATE SKIP LOCKED` |
| `TestDisconnectSourceGuards.test_store_then_credential_clear_order` (~1699) | `action_clear_token` | `_finalize_disconnect_completed` docstring "never the public `action_clear_token`" |
| `TestLifecycleAdmissionSourceGuards.test_admit_lifecycle_creates_no_lease` (~2554) | `call.lease` | `_admit_lifecycle` docstring "no `call.lease` is created" |

**Non-invasive runtime proof** (AST strip of docstring+comments via `odoo-bin shell`,
no file modified): every token is present in the RAW source but ABSENT from the
executable code — `ALL_PRODUCTION_CODE_CLEAN = True`. The sibling test
`test_admit_lifecycle_commits_and_closes_before_transport` already uses `ast.parse`
"so a docstring mention … is NOT a false positive", proving the author knew the
failure mode but left these four naive scans. **Production behaviour is correct; the
four are pure test-suite hygiene defects.** They do not touch any connector code path
and do not affect any behavioural/genuine test.

Recommended (control-room-gated) fix: make the four `assertNotIn` guards
docstring-robust (strip the docstring/comments, or use AST like the sibling test),
in `tests/test_credential_service.py` + `tests/test_disconnect_quiescence.py` only.
Per Section 9/13 a test-only correction requires a focused commit + push + **new
exact-head build + full revalidation from Section 1** — which this session cannot
produce (webhook held; single-DB container). Left OPEN as a remaining gate.

## RT.4 Base-to-head genuine upgrade — EXACT LIMITATION (not performed) `[Fact / Open limitation]`

A genuine isolated base→head upgrade **could not be created** in this container:
(1) it is a single-database dev build — `odoo-bin` auto-injects `-d <the one DB>` and
the db-filter locks it (AGENTS.md: "never attempt to create a new one"); (2) the DB
role is restricted — `pg_roles`/`pg_database` are `permission denied`, so it has no
`CREATEDB`; (3) the 1 GB `/home/odoo`+PG disk cap. `-i` on an already-installed module
is a no-op (**0 tests**), so it cannot substitute. Per Section 4 I do **not** substitute
a fresh install or same-head `-u` and call it an upgrade.

Supporting additive-safety analysis (not a substitute): the base→head delta is
additive only — one `noupdate="1"` cron + 9 additive store fields; the two `required`
new columns carry defaults (`connection_generation = Integer(default=0)`,
`disconnect_status = Selection(default='none')` — source comments: "Existing rows
backfill to 0" / "…to 'none'"), the rest are nullable/`default=False`/`default=0`, so an
`ADD COLUMN … NOT NULL DEFAULT` backfills existing rows safely. **A genuine base→head
upgrade + `-u shopify_connector_core` remains a REMAINING GATE for a runtime that
supports a second database.**

## RT.5 Complete core suite at head + `notification_type` env-artifact `[Fact]`

Live reproduction: `odoo-bin -u shopify_connector_core --test-enable --test-tags /shopify_connector_core --stop-after-init --no-http`
(run twice: before and **after** the 15 genuine runs — byte-identical):

- `shopify_connector_core: 247 tests`, **`19 post-tests` all pass**, `3 failed, 6 error(s) of 197 tests`.
- The **3 failures** = the same source-guard defects (the 4th is masked because its class `setUpClass` errors first).
- The **6 errors** = `res.users.create()` `NotNullViolation: notification_type` in `setUpClass._create_group_user` of the 6 user-creating `at_install` `TransactionCase` classes — including **non-PR** classes (`test_credential_access`, `test_job_log_system_append`). This is exactly the known **issue #157** (`res_users.notification_type` post-init-rerun base-fixture artifact, tracked in the handoff §1/§4, and explicitly out of scope — the task says *do not fix #157*). It is an **`-u`-only test-harness env-artifact, NOT a PR #160 defect**, proven four ways: (a) the fresh `-i` build had 0 such errors; (b) `odoo-bin shell` creates a user fine (`default_get→'email'`, `create→'email'`); (c) it strikes non-PR classes identically; (d) it never touches connector code. Root cause: in the `-u` at_install phase `shopify_connector_core` (deps: `base` only) loads at position 4 while `mail` (which supplies the `notification_type` default) loads later; the fresh `-i` build assembles the full registry before the per-module test loop, so the default is present.
- All previously-existing test classes still execute (API client, connection lifecycle, credential service, test connection, readiness slot closure, job dispatch, Slice-1 admission/lease, Slice-2A disconnect/controller). Registry test-mode does not leak (RT.10).

## RT.6 Genuine `post_install` classes — ×3 distinct processes each (all green) `[Fact]`

Each run: `odoo-bin -u shopify_connector_core --test-enable --test-tags '/shopify_connector_core:<Class>' --stop-after-init --no-http`.

| Class | Runs | Tests/run | Result (all runs) |
| --- | --- | --- | --- |
| `TestGenuineRealAdmission` | 3 | 9 | 0 failed, 0 errors |
| `TestCredentialReplacementRaceGenuine` | 3 | 2 | 0 failed, 0 errors |
| `TestDisconnectControllerSelectionGenuine` | 3 | 2 | 0 failed, 0 errors |
| `TestLifecycleAdmissionRaceGenuine` | 3 | 4 | 0 failed, 0 errors |
| `TestPublicClearAdmissionRaceGenuine` | 3 | 2 | 0 failed, 0 errors |

15 distinct executions, all green. The genuine classes assert their invariants
(distinct `pg_backend_pid`, zero-transport, no lease, worker-join, cursor-close,
zero residue) internally; a pass = the invariants held. Only emitted SQL noise is the
**expected** `lock timeout` provocation in `TestLifecycleAdmissionRaceGenuine`
(Section 7.C); the other 12 isolated runs emit zero SQL errors.

## RT.7 Sections 7 & 8 — race assertions (source-mapped, adversarially verified) `[Fact / Inference]`

`TestLifecycleAdmissionRaceGenuine` (Section 7): core invariants **proven** —
disconnect-first zero transport via a real counting `_send` spy (`assertEqual(send_calls, [])`),
distinct backends (`assertGreaterEqual(len(set(pids)),2)`), lease=0; admission-first
uses the exact captured old token (`captured['token']==DUMMY_TOKEN`) with the disconnect
committing on a distinct backend *during* the simulated request, result discarded as
superseded (`job cancelled`+`'superseded'`, `store.state=='disconnecting'`), credential
not cleared; **lock attribution (C) rigorous** — a 500 ms `lock_timeout` (not
`statement_timeout`) fires only on the `FOR SHARE` lock wait, `assertRaises(OperationalError)`
wraps *only* `_admit_lifecycle`, ruling out `Registry._lock`/cursor-creation/other SQL,
and after `holder.rollback()` admission proceeds; threaded case parks at the transport
seam on a real second backend, joins the worker **inside** the `patch.object(_lock)`
window (join precedes lock restoration).

`TestPublicClearAdmissionRaceGenuine` (Section 8): **proven** — business-admission-first
commits one lease (`lease_during==1`) with the old token, credential preserved while the
lease is open, deferred clear until a later controller pass, and **exactly one generation
bump** (`final_gen == initial_gen + 1`); public-clear-first commits `disconnecting` first
and the later old-generation admission **fails closed** (`assertRaises(ShopifyQuiescedError)`,
`assertNotIn('token', captured)` → zero transport, `lease==0`), credential retained,
zero residue.

Narrow, non-blocking test-completeness observations (production behaviour is correct;
these are assertion-tightening notes, not defects): Section 7A does not itself assert
"no mirror" (proven in 7B); "no pass/**fail** mirror" excludes only `'pass'`; "exactly one
transport" is counter-asserted only in test A; "original `Registry._lock` object restored"
rests on `patch.object` restore semantics (no identity assertion). Section 8A's
"quiescing (not completed)" and 8B's "new generation (clear-first)" are proven by
`state`/lease/gen **proxies**, not by observing the `disconnect_status`/gen value directly.
Recommended (control-room-gated) minor assertion tightening in
`tests/test_disconnect_quiescence.py`.

## RT.8 Section 9 — isolation level + serialization-retry `[Fact / Inference / Open]`

- **Isolation proven at runtime**: Odoo ORM cursor = **REPEATABLE READ** (`show transaction_isolation` inside an Odoo cursor).
- **Deterministic READ COMMITTED path proven**: `test_admission_first_uses_old_token_then_disconnect_supersedes` (+ threaded sibling) open the worker cursor `READ COMMITTED` (`SET TRANSACTION ISOLATION LEVEL READ COMMITTED`) so the post-network `FOR NO KEY UPDATE` revalidation directly observes a concurrently-committed disconnect and supersedes it, writing **no mirror** (`last_test_connection_result != 'pass'`, `credential_last_verified_at` falsy). Green ×3.
- **Framework retry verified from official Odoo 19 source** (not from memory): `odoo/service/model.py` — `PG_CONCURRENCY_ERRORS_TO_RETRY` includes `SERIALIZATION_FAILURE` (SQLSTATE 40001), `MAX_TRIES_ON_CONCURRENCY_FAILURE = 5`, `def retrying(...)` retry loop (L185); `call_kw` (L150) and `odoo/http.py:2303/2329` wrap every RPC/HTTP request. So the production RPC path for `action_test_connection`/`action_reconnect` **is** wrapped by a real 40001 retry — the docstring's "REPEATABLE READ + retry converge" claim is architecturally sound.
- **GAP (Open)**: **no connector test** forces a REPEATABLE READ 40001 and drives Odoo's retry to prove "total transport across attempt+retry == exactly one" / "no unhandled serialization error escapes" (b/c/e). The tests deliberately use READ COMMITTED to observe deterministically; the convergence is an **Inference** backed by framework source, not a connector test. Per Section 9 a narrowly-scoped runtime test may be added **only** to `tests/test_disconnect_quiescence.py` — REMAINING GATE (test-only correction ⇒ commit + push + new exact-head build + full revalidation, out of scope this session; production isolation must NOT be weakened to pass).

## RT.9 Section 10 — controller & timeout: ALL PROVEN `[Fact]`

All 12 claims map to real, load-bearing assertions matching production: one unlocked
store per invocation; locked-first skipped for a later unlocked store and all-locked
no-op **proven with genuine second-connection `FOR UPDATE` locks** (`TestDisconnectControllerSelectionGenuine`,
distinct backends, not a monkeypatch); zero-leases→`completed`; live/expired-before-timeout
lease→`quiescing` (credential kept); leases-at-deadline→`timed_out` (never `completed`,
`assertNotEqual`); credential clear only in `completed`/`timed_out` finalization (source +
runtime + grep: primitive has exactly the two finalize call-sites); residual leases
unlinked only **after** `timed_out` recorded (snapshot count before, `lease_count==0`
after); delayed re-poll via future `_trigger(at=now+POLL_DELAY)` with `call_at` bounded to
`[before+POLL_DELAY, after+POLL_DELAY+5s]`; no busy loop (`no while True/time.sleep/import time`);
repeated execution idempotent (no double-finalize, zero extra audit jobs).

## RT.10 Section 11 — registry test-mode safety: ALL PROVEN `[Fact]`

Four controlled `TransactionCase` classes enter Odoo's **sanctioned** `registry_enter_test_mode()`
in `setUp` (default `register_cleanup=True` → auto `addCleanup(registry_leave_test_mode)`,
restoring `registry.cursor` + `Registry._lock` after **each** method; the "Can only patch
registry once" guard blocks any leaked double-entry) so each probe-driving case sees its
uncommitted fixture through the shared `TestCursor`; **no assertion weakened** (whole-file
grep: no `skipTest`/`assertTrue(True)`/`@skip`). The five genuine `post_install` classes
**never** enter test mode — they use real `db_connect(dbname).cursor()` backends (distinct
`pg_backend_pid` asserted) and, where production needs `registry.cursor()`, patch it with a
factory handing out **real bounded pooled cursors** (not `TestCursor`) inside auto-restoring
`with` blocks; threaded cases use a real `threading.RLock()` (not the test-mode `DummyRLock`).
No `TestCursor` or `Registry._lock` replacement survives a boundary. The RT.5 full-suite
re-run **after** all 15 genuine runs is byte-identical to the baseline → no leak.

## RT.11 Section 3 schema — fields, selections, cron `[Fact]`

- New store fields all present: `connection_generation, credential_present, disconnect_status, disconnect_open_lease_count, disconnect_oldest_admitted_at, disconnect_completed_at, disconnect_status_reason, credential_last_verified_at, credential_last_replaced_at`.
- `state` selection = `[setup_incomplete, connected, reconnect_needed, disconnecting, disconnected]`; `disconnect_status` = `[none, requested, quiescing, completed, timed_out]`.
- `shopify.connector.call.lease` model exists.
- Disconnect cron `ir_cron_shopify_connector_disconnect_quiesce`: installed **exactly once** (`active=t, interval=5 minutes, priority=0`); job-drain cron once; **no duplicate** cron/model/data rows.

## RT.12 Section 12 — cleanup / leak audit: CLEAN `[Fact]`

After all runs: `shopify_connector_store/store_credential/call_lease/job/job_log` = **0**
each; `idle in transaction` backends = **0**; `ir_cron_trigger` = 18 rows all on the
standard base cron (`cron_id=1`), **0** referencing the disconnect (id 4) or drain (id 3)
crons → zero connector-trigger residue. Disconnect + drain crons active exactly once.
Backend visibility is limited to the restricted role's own connection. **Secret scan** over
all 18 generated logs + `odoo.log`: no real `shpat_` token, no `Authorization`/`Bearer`
header, no real email/PII, no raw GraphQL body.

## RT.13 Section 16 — adversarial review: ALL PREVENTED `[Fact]`

All 11 production invariants have concrete guarding code (both admissions take a
side-tx `FOR SHARE`, refuse before `_send` if not `connected`/outside matrix/generation
mismatch, commit-release before the network; no retry loop; single token read in
`_admit_lifecycle`; no store lock across the network; no lease in lifecycle admission;
no mirror on superseded; completed-path clear only at zero leases; single generation
bump; no explicit main-cursor commit in STORE/CRED; one sanctioned `sudo()` in
`_get_access_token`; public surface exactly `{execute, execute_business}`). Three flags
are **by-design/doc, not runtime escapes**: (1) `timed_out` clears the credential with
bounded already-admitted holders present (direction-C; no NEW admission possible since
generation bumped at Phase 1); (2) stale `_admit` docstring says the lifecycle update-lock
is a later slice though Slice 2A ships it (code correct); (3) legacy `execute()` `_send`
re-reads on `token=None` (business/lifecycle pass non-None).

## RT.14 Warning / SQL-error inventory + remaining gates `[Fact]`

- **Warnings (connector-relevant): 0.**
- **SQL ERROR-level inventory**: `lock timeout` — expected Section-7.C provocation
  (1 per `TestLifecycleAdmissionRaceGenuine` run); `notification_type` NOT NULL —
  `-u`-only env-artifact (RT.5), not a defect. **Zero unexpected SQL errors.**
- **Remaining gates (all control-room-gated; none producible this session — webhook
  held / single-DB container):**
  1. Fix the 4 source-guard docstring false-positives (test-only) → new exact-head build + full revalidation.
  2. Genuine base→head upgrade in a runtime with a second database (RT.4).
  3. Optional narrowly-scoped REPEATABLE READ / 40001-retry connector test for Section 9(b/c/e) (RT.8).
  4. Optional minor assertion tightening for the Section 7/8 proxies + stale `_admit` docstring (RT.7/RT.13).
- **SRR-03 remains OPEN** pending control-room decision. PR #160 stays **draft/unmerged**;
  Slice 2B not begun; no live Shopify request. Validated code SHA = `79dbfc0`; this runtime
  evidence is carried by a later **docs-only, non-runtime-tested** commit.

---

# CORE-R2 — Foundation Slice 2A — TEST-ONLY source-guard + service-retry correction (review 4692156428)

> `[Fact — test-only correction; NOT runtime-tested in this GitHub session.]`
> Control-room **runtime** review `4692156428` (which read the RT.0–RT.14
> exact-head record above, itself following the earlier static acceptance
> `4691652645`) required a narrow **test-only** correction: make the four
> docstring false-positive source guards docstring-robust, and add the genuine
> default-REPEATABLE-READ / real-Odoo-service-retry proof that RT.8 left open.
> **No production, XML, manifest, security, or cron file changed.** The historical
> runtime evidence above is **preserved unchanged**.

## S2A-C.0 What this correction does and does not do `[Fact]`

- **Historical evidence preserved.** Build **34872373** remains the exact-head
  runtime evidence for the **production** code SHA
  `79dbfc00428802da8c98c97d3e6d7eb6025ea74e` (the add-on tree at the corrected
  head is **byte-identical** to `79dbfc0`; only test + doc files changed). The
  RT.0–RT.14 record is unaltered.
- **The four RT.3 fresh-install failures were TEST DEFECTS**, not production
  defects — naive `assertNotIn(<token>, inspect.getsource(<method>))` guards
  matching the inspected method's **own docstring**. RT.3 already root-caused
  them; this session fixes them.
- **A new committed head requires a new Odoo.sh build.** Because the corrected
  head is a **new commit**, the RT record does **not** transfer to it: a **new
  exact-head Odoo.sh build + full revalidation from RT.1** is REQUIRED before any
  runtime-green of the corrected head. **This correction is NOT runtime-tested in
  this normal GitHub session** (no Odoo runtime; single-DB webshell unavailable).
- **Scope frozen.** Only two test files changed:
  `addons/shopify_connector_core/tests/test_credential_service.py` and
  `addons/shopify_connector_core/tests/test_disconnect_quiescence.py`, plus this
  record and the handoff. **Issue #157 remains separate and untouched.**

## S2A-C.1 The four source-guard corrections — executable-AST, docstring-robust `[Fact — static-verified this session]`

Each guard was converted from a raw-source `assertNotIn`/`assertIn` substring
scan to inspection of the method's **executable AST** (docstring excluded, so a
docstring/comment mention is not a false positive). Reusable helpers
(`guard_fn_ast`, `guard_called_names`, `guard_execute_sql`, `guard_str_constants`,
`guard_identifiers`, `guard_has_call_with_const_kwarg`, `guard_min_call_lineno`)
live once in `test_disconnect_quiescence.py` and are imported into
`test_credential_service.py` (the existing `from .test_api_client import …`
convention). **Every original safety assertion is preserved** — evaluated against
real code, never weakened to an always-pass:

| # | Guard (test) | Token that matched the docstring | Corrected AST check (all prior assertions kept) |
| --- | --- | --- | --- |
| A | `TestCredentialService.test_mutate_token_locks_store_before_credential_source` | `sudo(` in `_mutate_token` docstring "no `sudo()`" | `_lock_store_for_lifecycle` call-lineno **<** `self.search(` call-lineno; `'disconnecting'` present as an executable string constant; **no** `sudo` call node in the executable body. |
| B | `TestDisconnectSourceGuards.test_lifecycle_lock_is_blocking_for_no_key_update` | `SKIP LOCKED` in `_lock_store_for_lifecycle` docstring | SQL string literal passed to `.execute(...)` **contains** `FOR NO KEY UPDATE` and **does not contain** `SKIP LOCKED`. |
| C | `TestDisconnectSourceGuards.test_store_then_credential_clear_order` | `action_clear_token` in `_finalize_disconnect_completed` docstring | both finalizers **call** `_clear_token_under_store_lock` and **do not call** `action_clear_token` (call nodes); controller **calls** `try_lock_for_update(limit=1)`; `action_disconnect` calls **neither** clear. |
| D | `TestLifecycleAdmissionSourceGuards.test_admit_lifecycle_creates_no_lease` | `call.lease` in `_admit_lifecycle` docstring | executable body has **no** `shopify.connector.call.lease` model-lookup constant, **no** `lease_key` identifier, and **no** `create` call. |

**Non-circular / anti-weakening proof.** A new `TestSourceGuardDetectors` class
(pure AST, no DB) proves each detector both **FIRES** on a deliberately-unsafe
executable example — a real `.sudo()` call, executable SQL containing
`SKIP LOCKED`, a real `action_clear_token()` invocation, and a real call-lease
model `create(...)` (model lookup + `lease_key` + `create`) — **and IGNORES** a
docstring-only mention of the same token. So the correction does not merely pass
against the current safe production source; a future weakening (reverting to a
substring scan, or a detector that can never fail) is caught by these self-tests.

Static verification this session (plain-Python AST, no Odoo runtime): the
file-defined helpers, run against the **real production source**, reproduce the
RT.3 raw-source false-positive (each token IS in the raw source) yet return the
correct safe verdict on the executable AST, and every detector self-test passes.

## S2A-C.2 Genuine REPEATABLE-READ service-retry test (closes the RT.8 gap) `[Fact — authored; runtime-pending]`

New opt-in `post_install` test
`TestLifecycleServiceRetryGenuine.test_repeatable_read_serialization_retry_issues_one_transport`
(in `tests/test_disconnect_quiescence.py`) exercises the **real** Odoo 19
`odoo.service.model.retrying(func, env)` boundary — **not** a fake local retry
loop:

- **Setup:** a committed connected-store fixture + credential; one **main retry
  cursor/env** on a genuine pooled `db_connect` connection at the **normal Odoo
  isolation (REPEATABLE READ)** — asserted via `SHOW transaction_isolation`,
  **never** forced to READ COMMITTED; one **independent** connection for the
  disconnect; the Shopify transport seam (`_send`) patched; a **dummy token only**;
  no live request.
- **Genuine 40001 (not injected):** the callable re-browses the store from the
  retry env on **every** attempt and runs `action_test_connection`. On attempt 1
  the REPEATABLE READ snapshot is established before the disconnect commits; the
  patched transport opens an independent connection, runs the **real**
  `action_disconnect`, and commits (on a **distinct backend PID**); the
  post-network `_lifecycle_probe_superseded` → `_lock_store_for_lifecycle`
  `SELECT … FOR NO KEY UPDATE` then **cannot serialize** against the concurrently
  committed disconnect and PostgreSQL raises **SQLSTATE 40001**. Odoo's `retrying`
  catches it (`SERIALIZATION_FAILURE` ∈ `PG_CONCURRENCY_ERRORS_TO_RETRY`), rolls
  back, resets, and re-invokes; attempt 2 sees the committed `disconnecting` row
  and is **matrix-refused before transport**. Only the retry **backoff**
  (`random.uniform`/`time.sleep`) is patched — never the retry decision or
  exception classification.
- **Assertions:** default isolation is REPEATABLE READ; **≥2** callable attempts;
  **exactly one** transport total (attempt 2 adds zero); the first transport used
  the captured dummy token; the first attempt's `OperationalError.pgcode` is
  `SERIALIZATION_FAILURE` (40001) and the service retry logged its retry; the
  disconnect committed on a distinct backend PID; final store state
  `disconnecting`; generation bumped **exactly once**; credential **present**;
  **no** `pass` mirror and **no** stale-first-attempt `fail` mirror written;
  `credential_last_verified_at` empty; **no** call lease; **no** raw serialization
  error escaped; all cursors close; zero residue.
- **Runtime status:** this is the **design** and the static (`py_compile`,
  `compileall`) proof only. Because no Odoo runtime exists in this session, the
  genuine 40001 path is **not executed here** — it is validated on the next
  exact-head Odoo.sh build. The complementary READ-COMMITTED supersession test
  (`TestLifecycleAdmissionRaceGenuine`, RT.6/RT.8) already proves — by using
  READ COMMITTED **specifically to avoid** this retry — that the REPEATABLE READ
  path is the one that raises the 40001 the retry handles.

## S2A-C.3 Static results (this GitHub session; no Odoo runtime) `[Fact]`

- `py_compile` + `compileall -q addons/shopify_connector_core` — **OK**.
- Changed-file inventory = exactly the two allowed test files (+ this record and
  the handoff) — **no production/XML/manifest/security/cron file changed**; no
  product/sale/010B/011B/#157 file touched.
- Conflict-marker scan — clean. No new token/PII literal (dummy fixtures only);
  no live Shopify URL or network request in the diff.
- AST detector self-tests — all pass (fire-on-unsafe **and** ignore-docstring),
  verified with the file-defined helpers against the real production source.
- **Adversarial review** (guard-weakening, detector coverage, fake-vs-genuine
  40001, real-vs-fake retry, second-transport, stale mirror, isolation, main
  cursor commit, cleanup leakage, production/#157 contamination, premature
  closure) — no confirmed defect in the allowed files.

## S2A-C.4 Remaining gates (unchanged; still control-room-gated) `[Open]`

1. **New exact-head Odoo.sh build + full revalidation from RT.1** of the corrected
   head (this correction is **not** runtime-tested here).
2. Genuine base→head upgrade on a runtime with a second database (RT.4) — still
   **open**.
3. (Now authored, runtime-pending) the Section-9 REPEATABLE READ / 40001-retry
   proof (RT.8) — awaits the new build.
4. Optional Section 7/8 assertion tightening + stale `_admit` docstring (RT.7/RT.13).

**Issue #157 remains a separate, out-of-scope item — untouched.** **SRR-03 remains
OPEN.** No runtime-green of the corrected head is claimed; the corrected head must
be validated by a **new** Odoo.sh build. PR #160 stays **draft/unmerged**; Slice 2B
not begun; no live Shopify request.

---

# CORE-R2 — Foundation Slice 2A — EXACT-HEAD ODOO.SH RUNTIME VALIDATION of the test-only correction (build 34879305 @ `6e89138`)

> `[Fact — runtime-verified 2026-07-14 inside the authorized Odoo.sh dev build for
> the exact corrected head.]` This section is the **new exact-head build + full
> revalidation from RT.1** that §S2A-C.0/§S2A-C.4(1) required for the test-only
> correction `4692156428`. It runs **inside the Odoo.sh build for the exact head**
> `6e89138712ba4fc3c7899db19a8d6629b177591a` (build **34879305**). The four RT.3
> fresh-install source-guard failures are now **GONE**, the RT.8 gap is **closed**
> by a genuine runtime-green service-retry proof, and all prior genuine classes
> remain green across three distinct processes each. **No production, XML, manifest,
> security, or cron file changed** (add-on tree byte-identical to `79dbfc0`).
> **Issue #157 is separated, not fixed. The base→head upgrade gate stays OPEN.
> SRR-03 stays OPEN. PR #160 stays open/draft/unmerged.** This evidence commit is
> **docs-only and is itself NOT runtime-tested.**

## RTX.0 Build-to-commit gate `[Fact]`

- `git rev-parse HEAD` = **`6e89138712ba4fc3c7899db19a8d6629b177591a`** (exact required head).
- Ref: detached HEAD; the commit is the tip of local + `origin/claude/core-r2-foundation-slice-2a-mr7uwq` (`git show-ref` → both at `6e89138`); branch belongs to **PR #160**.
- `git status --porcelain` — **clean** working tree.
- Ancestry: `git merge-base --is-ancestor 1494b97d… HEAD` → **yes** (merge-base == `1494b97d…`); previously-validated production SHA `79dbfc00…` is also an ancestor. Both objects present.
- Odoo **19.0**; PostgreSQL **16.14** (Ubuntu 16.14-0ubuntu0.24.04.1).
- `ODOO_BUILD_URL` = `https://adamsmen-claude-core-r2-foundation-slice-2a-mr7uwq-34879305.dev.odoo.com`; Odoo.sh build **34879305**; DB `adamsmen-claude-core-r2-foundation-slice-2a-mr7uwq-34879305`.
- Installed module versions: `adams_base 19.0.1.0`, `shopify_connector_core 19.0.1.7.2`, `shopify_connector_product 19.0.1.0.0`, `shopify_connector_sale 19.0.1.0.0` (all `installed`).
- (gh CLI + GitHub token are **unavailable** in this build, so the PR-body edit is provided as text for the control room — see RTX.13.)

## RTX.1 Test-only diff proof `79dbfc0 → 6e89138` `[Fact]`

`git diff --name-status 79dbfc0 6e89138` = exactly four files: `M
tests/test_credential_service.py` (+26/−6), `M tests/test_disconnect_quiescence.py`
(+497/−21), `M docs/05-qa/task-core-r2-validation-results.md` (+380/−0), `M
docs/07-implementation-plan/task-core-r2-slice-2a-handoff.md` (+91/−0). Proven
byte-identical (empty diff / equal blob or tree hashes):

- **Core production tree** `models/ + data/ + security/ + views/ + controllers/` → identical `sha256` of `git ls-tree -r` (`1aae155f…`).
- `__manifest__.py`, both cron XML (`shopify_connector_cron_drain.xml`, `…_disconnect.xml`), and the **issue-157 files** (`shopify_connector_job_dispatch.py`, `shopify_connector_job.py`, `tests/test_job_dispatch.py`) → identical blob hashes.
- `shopify_connector_product/**`, `shopify_connector_sale/**`, `adams_base/**` → **no** changed path.
- No product/sale file, no XML/manifest/security/cron data, no non-test `.py` changed.

## RTX.2 Fresh install (authoritative = build `install.log`) — GREEN `[Fact]`

The build DB was created by a **fresh `-i` install with tests** of the exact head.
Exact command (`install.log`):

```
odoo-bin --stop-after-init --log-db <db> --http-interface=127.0.0.1 \
  -i adams_base,shopify_connector_core,shopify_connector_product,shopify_connector_sale \
  --test-enable --log-level=test \
  --test-tags /adams_base,/shopify_connector_core,/shopify_connector_product,/shopify_connector_sale,<standard base-tour exclusions>
```

Result: **`0 failed, 0 error(s) of 408 tests`** (stats: core **361**, product **61**,
sale **56**; **20** post-tests). **The four RT.3 source-guard failures are GONE** —
each of the four guard methods
(`test_mutate_token_locks_store_before_credential_source`,
`test_source_level_sanctioned_sudo_sites_guard`,
`test_lifecycle_lock_is_blocking_for_no_key_update`,
`test_store_then_credential_clear_order`, `test_admit_lifecycle_creates_no_lease`)
**ran once and passed** on the fresh install, and `TestCredentialService` had **24**
clean method-starts with **0** `notification_type` errors (issue #157 does **not**
strike the fresh `-i` build). No install / XML / registry / manifest error.
**Connector crons installed exactly once** (see RTX.11).

## RTX.3 AST source-guard validation (in-session, build 34879305) `[Fact]`

Targeted per-class `-u … --test-tags /shopify_connector_core:<Class>`:

| Class | Result | Notes |
| --- | --- | --- |
| `TestSourceGuardDetectors` | **0 failed, 0 error(s) of 5** | detector self-tests: `sudo`, `SKIP LOCKED`, `clear`, `call.lease`, `limit=1`-kwarg — each **FIRES on real unsafe executable code** and **IGNORES a docstring-only mention** |
| `TestDisconnectSourceGuards` | **0 failed, 0 error(s) of 6** | guards B (`FOR NO KEY UPDATE`/no `SKIP LOCKED`) and C (`_clear_token_under_store_lock`, not `action_clear_token`; `try_lock_for_update(limit=1)`) |
| `TestLifecycleAdmissionSourceGuards` | **0 failed, 0 error(s) of 10** | guard D (`_admit_lifecycle` creates no lease) |
| `TestCredentialService` (guard A) | green on the **fresh `-i` build** (RTX.2); in-session `-u` shows only the issue-#157 `setUpClass` artifact (RTX.6), **not** a guard failure | guard A = `test_mutate_token_locks_store_before_credential_source` + `test_source_level_sanctioned_sudo_sites_guard` |

Detectors prove real unsafe examples are detected, docstring-only mentions ignored,
and **no guard was weakened to always-pass** (a substring-scan regression would fail
the detector self-tests). **All four historical false-positive failures are closed.**

## RTX.4 Genuine REPEATABLE-READ service-retry — three distinct processes `[Fact]`

`TestLifecycleServiceRetryGenuine.test_repeatable_read_serialization_retry_issues_one_transport`
(`post_install`), each a separate `odoo-bin` process:

| Run | PID | Elapsed | Result |
| --- | --- | --- | --- |
| 1 | 584 | 9 s | `0 failed, 0 error(s) of 1` |
| 2 | 601 | 10 s | `0 failed, 0 error(s) of 1` |
| 3 | 616 | 12 s | `0 failed, 0 error(s) of 1` |

Direct log evidence (every run): the post-network revalidation
`SELECT state, connection_generation FROM shopify_connector_store WHERE id=<n> FOR
NO KEY UPDATE` raises a **genuine SQLSTATE 40001** — `ERROR: could not serialize
access due to concurrent update` (not injected) — and the **real** Odoo service
retry logs `odoo.service.model: SERIALIZATION_FAILURE, 4 tries left, try again in
0.0000 sec…`. The connection pool closes cleanly (`ConnectionPool(…used=0/count=0):
Closed 3 connections`). The test's 18 in-body assertions (main cursor REPEATABLE
READ; ≥2 attempts; exactly one transport; first transport uses only the dummy
token; disconnect on a **distinct** backend PID; 40001 captured from
`OperationalError.pgcode`; second attempt matrix-refused with zero transport; final
state `disconnecting`; generation `+1`; no `pass`/`fail` mirror;
`credential_last_verified_at` empty; credential present; zero leases; all cursors
closed; zero residue; final safe `UserError`; no raw serialization escape) all hold
— a green result proves each. **Production isolation was not weakened; only the
retry backoff was patched.**

## RTX.5 Prior five genuine classes — three distinct processes each (15 executions, all green) `[Fact]`

| Class (tests/run) | run1 | run2 | run3 |
| --- | --- | --- | --- |
| `TestGenuineRealAdmission` (9) | ✓ pid635 | ✓ pid754 | ✓ pid897 |
| `TestCredentialReplacementRaceGenuine` (2) | ✓ pid661 | ✓ pid780 | ✓ pid946 |
| `TestDisconnectControllerSelectionGenuine` (2) | ✓ pid684 | ✓ pid803 | ✓ pid993 |
| `TestLifecycleAdmissionRaceGenuine` (4) | ✓ pid707 | ✓ pid826 | ✓ pid1033 |
| `TestPublicClearAdmissionRaceGenuine` (2) | ✓ pid731 | ✓ pid860 | ✓ pid1075 |

Every one of the 15 executions = **`0 failed, 0 error(s)`**. `TestLifecycleAdmissionRaceGenuine`
emits its intended **lock-timeout** SQL log (`FOR SHARE` vs lifecycle `FOR NO KEY
UPDATE` → `canceling statement due to lock timeout`) — an **expected
negative-constraint log**, not a defect (result stays 0/0).

## RTX.6 Complete core suite (before / after the isolated genuine tests) + issue-#157 separation `[Fact]`

- **BEFORE (pristine baseline = build `install.log` fresh `-i`):** `0 failed, 0 error(s) of 408` — the full suite (incl. every genuine `post_install` class) ran during the build, before any in-session isolated run.
- **AFTER (in-session `-u shopify_connector_core --test-enable --test-tags /shopify_connector_core`, run twice, identical):** **`0 failed, 6 error(s) of 203 tests`**; **0** source-guard `FAIL` lines; **20** post-tests green. Re-running gave the **identical** result → no residue accumulation.

**PR #160 result: GREEN (0 failures).** **Known issue #157 result: 6 `setUpClass`
errors**, on exactly `TestConnectionLifecycle`, `TestCredentialAccess`,
`TestCredentialService`, `TestJobLogSystemAppend`, `TestReadinessSlotClosure`,
`TestTestConnection` — the `res_users.notification_type` NOT-NULL base-fixture
artifact that appears **only** on the `-u` at_install re-run (the `mail`-supplied
default is not yet in the registry when `shopify_connector_core`'s at_install tests
run), **never** on the fresh `-i` build. This is the documented **issue #157**,
explicitly out of scope and **not fixed** here. **Combined raw Odoo summary: `0
failed, 6 error(s) of 203 tests`.** No registry-test-mode leak, no `Registry._lock`
leak, no cursor/worker leak (RTX.11).

## RTX.7 Controller & lifecycle regression `[Fact]`

`TestDisconnectPhase1` **11/11**, `TestQuiescenceController` **12/12**,
`TestLifecycleRaceCorrections` **3/3**, `TestLifecycleProbeSupersession` **6/6**
(all in-session `-u`, 0/0), plus the RTX.5 genuine classes. Coverage confirmed
green for: disconnect request; exactly-one generation bump; repeated-disconnect
idempotency; `completed` vs `timed_out`; live & expired lease handling; delayed
polling; one-store controller selection; all-locked safe no-op; credential clear
only at finalization; public-clear two-phase routing; activation/reconnect race
protection; lifecycle exact-token snapshot; post-network supersession.
`TestConnectionLifecycle` (activation/reconnect state machine; #157-masked under
`-u`) ran **43** method-starts green on the fresh `-i` build.

## RTX.8 Cleanup / leak / secret audit `[Fact]`

- Residue: **0** stores, **0** credentials, **0** call leases, **0** jobs, **0** job logs.
- Cron triggers: **0** connector triggers (the 6 `ir_cron_trigger` rows are all base `base.autovacuum_job` framework housekeeping).
- Backends: **1** active (the audit `psql`), **0** idle-in-transaction, **0** `odoo`-named backends → no worker/cursor leak.
- `Registry._lock`: no leak — no leak indicator in any run log; every subsequent run passes (the fresh RLock is restored after each bounded window).
- Crons active exactly once: id 3 `Shopify Connector: Job Dispatch Drain`, id 4 `Shopify Connector: Disconnect Quiescence Controller`.
- **Secret scan across all 28 in-session run logs:** **no** `shpat_` token (not even the dummy — it is never emitted), **no** `Authorization`/`Bearer`/`X-Shopify-Access-Token`, **no** raw GraphQL query/mutation body, **no** customer email/address PII.

## RTX.9 Warnings / SQL-error inventory (expected negatives separated from defects) `[Fact]`

Every `ERROR`-level SQL line during the runs is **expected**, none a defect:
- **(a) genuine SQLSTATE 40001** — `… FOR NO KEY UPDATE` → `could not serialize access due to concurrent update`, the **intended** retry driver of `TestLifecycleServiceRetryGenuine` (RTX.4).
- **(b) lock timeout** — `FOR SHARE` vs lifecycle `FOR NO KEY UPDATE` → `canceling statement due to lock timeout`, the intended conflict of `TestLifecycleAdmissionRaceGenuine` (RTX.5).
- **(c) NOT-NULL / duplicate-key** on product/customer binding tables — deliberately-invalid inserts in passing negative-constraint tests.
- **(d) `res_users.notification_type` NOT-NULL** — the `-u`-only issue-#157 env artifact (RTX.6), out of scope.
No CORE-R2 (`call_lease`/admission/lifecycle) SQL error, and no unexpected error.

## RTX.10 Base→head genuine upgrade — EXACT LIMITATION (not performed) `[Fact / Open]`

A genuine isolated base-installed second database is **not available**: the injected
PostgreSQL role gets `permission denied` for both `pg_database` and `pg_roles`
(cannot create or enumerate databases — `odoo-bin` itself logs "skipping
auto-creation: permission denied for table pg_database"), and the Odoo.sh dev build
is bound to a **single injected DB**. No substitute (same-head `-u`, fresh install,
schema inspection) was used. **The upgrade gate remains OPEN** (RT.4 / RR-F).

## RTX.11 Registry / lock / cron-once safety `[Fact]`

No registry-test-mode leak, no `Registry._lock` replacement leak, no cursor or
worker backend leak (RTX.8). The two connector crons remain active exactly once.

## RTX.12 Runtime defects / corrections `[Fact]`

**None.** No PR #160 defect was exposed by any run; **no production or test code was
changed** in this validation session (the §11 failure policy was not triggered).
Production files remain frozen. The only failure policy items observed are the
expected negative logs (RTX.9) and the out-of-scope issue #157 (RTX.6).

## RTX.13 Evidence commit, PR state, remaining gates `[Fact]`

- **Validated CODE SHA: `6e89138712ba4fc3c7899db19a8d6629b177591a`** (add-on tree byte-identical to `79dbfc0`). This section is a **docs-only evidence commit** that advances the branch head but does **not** alter the validated code SHA, and **is itself NOT runtime-tested**.
- **PR #160 stays open, draft, unmerged.** Not marked ready; not merged. gh CLI/token unavailable in the build → the PR-body update text is handed to the control room (mirrors this section's headline result).
- **Remaining gates (unchanged):** base→head genuine upgrade on a two-DB runtime (RTX.10) — **OPEN**; optional Section 7/8 assertion tightening + stale `_admit` docstring (RT.7/RT.13).
- **Issue #157 remains separate and untouched. Slice 2B not begun. No live Shopify request, no real credential. SRR-03 remains OPEN** — no end-to-end disconnect-quiescence remediation runtime-green is claimed.

---

# CORE-R2 Slice 2B — Runtime CORRECTION session (2026-07-14) `[Fact]`

> One controlled runtime-correction session on Odoo.sh build **34912503** (Odoo
> **19.0**, DB `adamsmen-claude-core-r2-slice-2b-integration-34912503`), from the
> accepted staging SHA **`63d10fb465a26189fa463f9c7ac580da6a931c5c`** on a
> dedicated correction branch **`claude/core-r2-slice-2b-runtime-correction`**.
> Closes the three control-room-adjudicated runtime findings from the preceding
> integrated-closure session. **Prompt E stays BLOCKED. SRR-03 stays OPEN. No
> final integration PR. No merge. No live Shopify request.**

## RTC.1 Root cause (adjudicated) `[Fact]`

The scheduled job-dispatch path (`ir.cron` → `run_drain`) had **no transaction
retry protection**, and the dispatcher **caught a raw PostgreSQL concurrency
failure (SQLSTATE 40001/40P01/55P03) and re-issued ORM writes inside the
already-aborted transaction** (`_invoke_handler`'s `except Exception` → job
`write()` → `InFailedSqlTransaction`). Confirmed from the runtime: `ir_cron.
_callback` runs the server action and on any exception rolls back and re-raises
with **no retry**; `odoo.service.model.retrying` (the real Odoo boundary,
`MAX_TRIES_ON_CONCURRENCY_FAILURE=5`) was never applied to `run_drain`. Under
the container's REPEATABLE READ isolation a concurrent committed disconnect made
the parked call-site reconciliation's binding `FOR KEY SHARE` on the store row
serialization-fail — reproduced deterministically as the customer-M18
`InFailedSqlTransaction` and product-M18 `SerializationFailure` findings.

## RTC.2 Production correction (smallest, common-layer) `[Fact]`

**Single production file:** `addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`.

1. `run_drain` now drains **one job at a time** through `_drain_one`, which wraps
   each dispatch in the **real** `odoo.service.model.retrying(func, env)` boundary:
   a genuine 40001/40P01/55P03 rolls the transaction back, resets the environment,
   **re-browses the job/store by id** and retries under the real Odoo policy;
   `retrying` commits each job on its own (batch integrity — a later job's
   rollback can never undo, or duplicate the transport of, an already-committed
   job). The bounded budget being exhausted routes the job **once, in a clean
   transaction**, to the existing `concurrency_race_conflict` auto-retry path.
2. `_invoke_handler` now **re-raises** `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY`
   unchanged instead of routing it through an ORM write in the aborted
   transaction (the bug). Classified handler conflicts still raise
   `JobHandlerError('concurrency_race_conflict', …)` and route as before.
3. `_concurrency_retry_supported()` detects the test runner's forbidden-commit
   guard so the standard `TransactionCase` suite dispatches directly (no real
   serialization can occur on its single shared connection), while production and
   the genuine independent-connection lifecycle tests (real pooled cursors) run
   the real boundary. No new API surface; no `.create(`/`.sudo(`/`shopify.
   connector.api.client`/`.execute(` introduced (existing AST/source guards stay
   green).

**On the retry contract:** the accepted-design outcome is **safe supersession** —
a superseded call retries and is **refused before any second transport** (an
already-disconnecting store fails the `write()`→`running` gate), landing the job
in `failed_retryable`. This is NOT "reconciliation completes after the disconnect".

## RTC.3 Test corrections (no weakening) `[Fact]`

- **Customer disconnect-first PID (finding #1)** —
  `test_race_a_disconnect_first_fails_closed_zero_transport`: the disconnect
  connection is now held **open** while the worker connection is opened, so the
  two backend PIDs are distinct **by construction** (not by LIFO-pool timing).
  The PID assertion is **strengthened** to a deterministic `assertNotEqual`, never
  removed; fail-closed + zero-residue preserved.
- **Customer M18 (finding #2)** — renamed
  `test_m18_lease_count_then_serialization_retry_refuses_after_disconnect`: drives
  the REAL `run_drain`; proves lease-count/controller-defer **and** the genuine
  40001 → retry → refuse contract (exactly one transport with `DUMMY_TOKEN`,
  `open_lease_count=1`, lease released, **zero binding**, `failed_retryable`,
  serialization evidenced from the real service-retry log, controller finalizes +
  clears credential only after release). The controller-vs-worker distinct-PID
  claim is scoped to the parked window (a post-release finalize pass may reuse the
  freed backend via the pool).
- **Product M18 (finding #2)** — renamed
  `test_race_b_terminal_reconciliation_retry_refuses_after_disconnect`: same
  contract via `run_drain` (one transport, zero binding, `failed_retryable`, 40001
  evidenced). Its fixture now enables `product_domain_enabled` so the real
  dispatch start-gate admits the job.
- **Product cron-trigger residue (finding #3)** — the product genuine class now
  owns its connector-cron `ir_cron_trigger` rows via a per-test baseline
  (`setUp`), deleting only `current − baseline` and asserting a zero delta
  (mirrors the accepted customer pattern). Independently verified: connector
  cron-trigger residue after the product lifecycle runs is **0** (was +4/run).
- **New Phase-5 core proof** —
  `TestLifecycleServiceRetryGenuine.test_scheduled_run_drain_serialization_retry_refuses_after_disconnect`:
  the shared core dispatcher retry-then-refuse proven once at the core layer via
  `run_drain` with a representative business handler (execute_business +
  `FOR NO KEY UPDATE` revalidation → genuine 40001).

## RTC.4 `notification_type` classification (Phase 9 — unchanged, non-blocking) `[Fact]`

Six isolated-core `res.users.notification_type` `setUpClass` `NotNullViolation`s
persist and were **accepted by the control room as a non-blocking partial-
registry / invocation artifact**, **not** touched by this correction:

- **Producing command (isolated):** `odoo-bin -u shopify_connector_core
  --test-enable --test-tags '/shopify_connector_core' --stop-after-init --no-http`.
- **Cause:** `notification_type` is a **`mail`-owned stored computed field**
  (`compute='_compute_notification_type'`, `default='email'`, `required=True`);
  `shopify_connector_core` depends only on `['base']` — not `mail` — so under an
  isolated partial upgrade of a mail-independent module the default is not
  applied. In the full registry `env['res.users'].default_get(['notification_type'])`
  returns `'email'`, and the connector never touches `res.users`.
- **Full-install (representative) command under which the same classes pass:**
  the Odoo.sh **build-time fresh install** of all modules with `--test-enable`
  (the canonical release-validation path) — at `63d10fb` that run was **`0 failed,
  0 error(s) of 574 tests`**, and all six user-fixture classes ran green.
- **Canonical connector validation** must load the representative dependency
  registry (the fresh full install), not an artificial core-only partial
  registry. Kept visible as an **invocation limitation, not a connector defect**.

## RTC.5 Runtime results — correction branch, build 34912503 `[Fact]`

_(exact commands: `odoo-bin -u <module> --test-enable --test-tags '<tag>'
--stop-after-init --no-http`; per-run logs under the build's session dir.)_

- **Core standard suite ×3:** `0 failed, 6 error(s) of 204` each (the 6 accepted
  `notification_type` artifacts only; the new Phase-5 test + all genuine
  admission/lease/disconnect/controller/SKIP-LOCKED/serialization-retry proofs
  green, repeatable).
- **Product standard suite:** `0 failed, 0 error(s) of 174`.
- **Sale (customer) standard suite:** `0 failed, 0 error(s) of 93`.
- **Customer callsite lifecycle tag ×3:** `0 failed, 0 error(s) of 6` each.
- **Product callsite lifecycle tag ×3:** `0 failed, 0 error(s) of 4` each.
- **Scheduled-dispatch serialization/retry proof ×3 per domain/path:** customer
  M18 (in the customer tag ×3), product M18 (in the product tag ×3), core
  `test_scheduled_run_drain_…` (in the core suite ×3) — all green.

## RTC.6 Independent residue / leak audit `[Fact]`

After every group and at the end (independent `psql`, not test assertions): all
connector data tables 0 (`call_lease`, customer/template/variant bindings, store,
credential, settings, job, job_log); `attribute_lock` singleton = 1; master
tables exactly at baseline (`res_partner`=44, `product_template`=34,
`product_product`=44, `product_attribute`=19, `product_attribute_value`=101);
**connector cron-trigger delta = 0** (finding #3 closed); 0 idle-in-transaction;
1 backend (self); no stray workers. **No live Shopify request** (only the
`shpat_DUMMYDUMMY…` sentinel; no `myshopify.com`/GraphQL/HTTP egress); no
credential/token/header/request-body leakage in any log.

## RTC.7 Governance state + push mechanism `[Fact / control-room decision needed]`

- **Push mechanism (platform-forced deviation from the separate-branch / draft-PR
  model):** the Odoo.sh dev container's only push mechanism is `odoosh-push`,
  which — by Odoo.sh security design — **forces the push onto the build's bound
  branch, `claude/core-r2-slice-2b-integration`** ("you are forced to push on the
  branch your build is currently linked to; you cannot deactivate this
  behavior"). A separate correction branch **cannot** be pushed from this
  container, and `gh` is unavailable to open a PR (the project's established
  pattern — prior sessions' "evidence commit advances the branch head"). The
  correction therefore landed as a **single, clean, fast-forward commit on
  `claude/core-r2-slice-2b-integration`** (`63d10fb…` → the correction head).
  **No force-push, no rebase, no amend.** It is one well-scoped reviewable unit
  (allowed-list files only) that the control room can review in place, branch a
  review PR from, or reset the integration head to `63d10fb…`. **This session did
  NOT promote onward to `Shopify-connector` and did not self-authorize any gate
  transition.**
- PR #150 (`10d0034…`) / PR #151 (`e4669aa…`): present, **not touched**.
- `Shopify-connector` unchanged (`dd6ecb8…`) — **no promotion**. `main` / plain
  `dev` untouched. Task 012 docs untouched.
- **Prompt E remains BLOCKED. SRR-03 remains OPEN pending control-room review.**

---

# CORE-R2 Slice 2B — Runtime CORRECTION session (2026-07-15): dispatch ownership/replay model `[Fact]`

> Control-room review `4699752673`. This session **corrects** the RTC.1–RTC.3
> dispatcher description above: the `retrying`-boundary drain was proven unsafe and
> is replaced by a per-job ownership/replay-safe boundary. Validated on Odoo.sh
> build **34923103**, PR #163 head branch
> `claude/core-r2-slice-2b-runtime-correction-review` (base
> `claude/core-r2-slice-2b-integration` @ `63d10fb`).

## RTC-2.1 Proven problem (control-room diagnosis, retained)

The prior `_drain_one()` claimed a job (a transaction-scoped `FOR UPDATE SKIP
LOCKED` row lock — **not** a durable state flag), stored only its id, then ran the
**complete** handler inside `odoo.service.model.retrying`. On a genuine PostgreSQL
concurrency failure `retrying` rolled the transaction back — which **released the
original claim and undid the `state→running` write** — then **re-invoked the whole
handler** by a bare `browse(job_id)` without reacquiring any claim; retry
exhaustion likewise routed the job by a bare id without a lock. Two unsafe
consequences: (1) a competing drain worker could claim the same job between
rollback and retry; (2) the handler could be **replayed after a Shopify transport
had already occurred** — the old disconnect test only avoided a second call because
the reset attempt observed `disconnecting` and was gate-refused, which does **not**
protect a still-connected job hitting an unrelated concurrency failure after
transport.

## RTC-2.2 Corrected facts (SUPERSEDE the earlier "retrying / failed_retryable / service-retry log" wording)

- **[Corrects claim] A rolled-back claim does NOT remain exclusive.** The claim is
  only a row lock; a rollback releases it. Every reset treats the claim as lost and
  re-locks before any dispatch or state transition.
- **[Corrects claim] Re-browsing by id is NOT equivalent to reacquiring a claim.**
  Recovery reacquires the exact job via the real `try_lock_for_update`
  (`FOR UPDATE SKIP LOCKED`) and revalidates its claimable state **under the lock**.
- **[Corrects claim] Wrapping the handler in `retrying()` does NOT inherently
  prevent duplicate transport.** `retrying` re-invokes the complete handler; the
  drain no longer uses it — the handler runs **at most once** per drain pass and is
  never automatically replayed after transport.
- **[Corrects claim] Retry exhaustion is NOT routed without a lock.** Exhaustion
  (and every conflict routing) occurs only after reacquiring the exact job lock.

## RTC-2.3 Selected design (conservative direction)

`_drain_one` runs the claimed job once under its held claim and **commits per job**
(batch integrity); it flushes inside the guard so a REPEATABLE-READ 40001 surfacing
at flush time is caught, never after commit. On a
`PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` (SQLSTATE 40001/40P01/55P03) it logs the
SQLSTATE and calls `_recover_after_concurrency_conflict(job_id)`: `cr.rollback()` +
`env.transaction.reset()` → `try_lock_for_update` the exact job → empty (another
worker owns it / row gone) ⇒ **do nothing** → else revalidate claimable state
(`queued`, or due `retry_waiting`) under the lock → non-claimable
(running/terminal/etc.) ⇒ **do nothing, never overwrite** → else route ONCE to
`concurrency_race_conflict` (`retry_waiting`, or `failed_final` once the bounded
budget is exhausted), **without replaying the handler**. Isolation unchanged
(REPEATABLE READ); no in-memory flag; PG concurrency errors still escape
`_invoke_handler` and are never caught inside the domain importers.

## RTC-2.4 Production changes (allowed file)

`addons/shopify_connector_core/models/shopify_connector_job_dispatch.py`: dropped
the `retrying` import/use; rewrote `run_drain`/`_drain_one` to the per-job
transaction boundary; added `_recover_after_concurrency_conflict`; added a module
`_logger` recording the SQLSTATE on recovery; updated `_invoke_handler`'s re-raise
comment and `_concurrency_retry_supported`'s docstring. No API-client,
store-lifecycle, credential, importer, manifest, XML, or security change.

## RTC-2.5 Tests (allowed files)

- `test_disconnect_quiescence.py`: updated
  `test_scheduled_run_drain_serialization_retry_refuses_after_disconnect` to the
  no-replay model (one transport, genuine 40001 pgcode captured, job
  `retry_waiting`, distinct PID); added class `TestDrainOwnershipReplayGenuine` —
  **Test A** (rollback/reclaim race: one owner, SKIP-LOCKED loser, one transport),
  **Test B** (still-connected post-transport 40001: one transport, no replay,
  routed once, store stays connected), **Test C** (conflict-exhaustion →
  `failed_final` after reacquire; and ownership-refusal — A does not overwrite a
  job Worker B completed), **Test D** (batch integrity: per-job commit survives a
  neighbour's rollback, later job still processed). Every 40001 is a REAL
  serialization failure (benign committed store-row `write_date` bump vs the real
  `_lock_store_for_lifecycle` `FOR NO KEY UPDATE`), on genuine pooled `db_connect`
  cursors with distinct backend PIDs.
- Customer/product M18 tests: the superseded job now ends **`cancelled`** (the
  disconnect controller sweeps the `retry_waiting` business job) and the 40001 is
  evidenced from the dispatcher concurrency-recovery log; all other assertions
  (one transport, zero binding, lease released, store finalized, credential
  cleared after release) unchanged.

## RTC-2.6 Runtime results (build 34923103)

| Group | Result |
| --- | --- |
| Exact-head upgrade (core+sale+product) | 47 modules loaded, **zero registry/module errors** |
| Product standard suite | `0 failed, 0 error of 174` |
| Sale standard suite | `0 failed, 0 error of 93` |
| Representative core suite | `0 failed, 6 error of 476` — the 6 = the **known `notification_type` `res.users` `setUpClass` artifact** (RR-F / issue #157, §11); the other 470 green |
| Customer lifecycle tag ×3 | `0 failed, 0 error of 6` (runs 1/2/3) |
| Product lifecycle tag ×3 | `0 failed, 0 error of 4` (runs 1/2/3) |
| Test A/B/C/D + updated disconnect (ownership class) ×3 | `0 failed, 0 error of 5` (runs 1/2/3) |
| Existing genuine CORE-R2 admission/lease/disconnect/controller classes | green (within the core suite) |

## RTC-2.7 `notification_type` artifact classification `[Fact]`

The 6 core-suite errors are `setUpClass` failures in six classes NOT touched by
this correction (`test_connection_lifecycle`, `test_credential_access`,
`test_credential_service`, `test_job_log_system_append`, `test_readiness_slot_closure`,
`test_test_connection`), each raising `null value in column "notification_type" of
relation "res_users" violates not-null constraint` while creating a test user
**before any test logic runs**. Proven invocation-invariant: running just these six
classes yields `0 failed, 6 error of 0 tests` (zero tests execute). This is exactly
the base-environment `res.users` artifact recorded in §4.3 / RR-F (the "six core …
`setUpClass` errors expected to reproduce identically", issue #157), independent of
the dispatch change (which touches neither `res.users` nor these classes).

## RTC-2.8 Independent zero-residue audit `[Fact]`

Fresh-connection SQL audit after the full matrix: call leases 0; jobs 0; job logs
0; stores 0; credentials 0; customer bindings 0; product template/variant bindings
0; test-pattern partners 0; test-marker product templates/variants/attributes/
values 0; connector cron-trigger delta 0; idle-in-transaction connections 0;
ungranted (blocking) locks 0; token/secret leakage in job logs 0 (only the
`shpat_DUMMYDUMMY…` sentinel is used; no `myshopify.com`/GraphQL/HTTP egress).

## RTC-2.9 Governance

Validated on the working tree of build 34923103, byte-identical to the PR #163 head
after this session's commit (Odoo.sh holds the dev-branch rebuild webhook during an
AI session, so the running build already contains the exact validated code). **No
live Shopify request. No merge. PR #163 kept draft. No Prompt E. SRR-03 remains
OPEN. `Shopify-connector` / `main` / plain `dev` unchanged. PR #150/#151 untouched.**

# CORE-R2 Slice 2B — DEC-031 Immediate Slice 2: exact-head Odoo.sh runtime validation (2026-07-15) `[Fact]`

Control-room refs: DEC-031 **Accepted**, AR-048 **Accepted**, implementation
authorization `4701810356`, runtime code-review acceptance `4702066051`. Session
type: Odoo.sh runtime validation only (Do-not-merge, do-not-mark-ready).

- **Build:** `34935129`  ·  **DB:** `adamsmen-claude-core-r2-slice-2b-runtime-correction-34935129`  ·  **Odoo:** `19.0`  ·  **Stage:** dev
- **Branch:** `claude/core-r2-slice-2b-runtime-correction-review`
- **Base head before this session:** `4b45d350317a6889c32777ab5b73e56124276142`
- **Validated code SHA (exact head):** `757a9680182f65c627a3880b9c7989d6c5d56035`

## IS2.0 Exactness corrections (commit `757a968`) `[Fact]`

Commit **`757a9680182f65c627a3880b9c7989d6c5d56035`** — *"Tighten DEC-031 runtime
validation proofs"* — 3 files, +72/−13, **no production logic change**:

- `shopify_connector_job_dispatch.py` — **comments/docstrings only** (5 stale
  locations). Reworded `run_drain`/`_drain_one` docstrings, the `_drain_one`
  except-block comment, the `_recover_after_concurrency_conflict` docstring point
  4, and the `_invoke_handler` re-raise comment so they no longer imply that every
  concurrency recovery routes to `concurrency_race_conflict` or that every
  recovered job auto-retries. Accurate wording now states: the recovery call
  itself never re-invokes the handler; `local_only`/`remote_read_replay_safe` jobs
  may be scheduled for a later **bounded** retry; `remote_effect_not_replay_safe`
  and undeclared jobs route to **manual review**; routing is **policy-gated**; **no
  exactly-once claim** is made. `git diff` confirms every changed line is inside a
  docstring or `#` comment — no executable line touched.
- `test_product_import_matching.py` / `test_customer_import_matching.py` —
  **test-strengthening only**. Retained the explicit `product_import_sync` /
  `customer_import_sync → remote_read_replay_safe` assertions and added
  `test_installed_scope_every_handler_has_replay_policy`, asserting in each
  installed scope that `set(_get_handlers()) - set(_get_replay_policies()) == ∅`
  with a failure message listing any missing handler keys. No generic registry
  framework; no production-mapping change.

Pushed via `odoosh-push` (`4b45d35..757a968`, no force). `odoo-bin` executes the
working tree, which is **byte-identical to `757a968`** (`git diff --quiet 757a968`
= clean); Odoo.sh holds the dev rebuild webhook in-session, so the platform build
number (`34935129`) was provisioned from `4b45d35` while the **code under test is
exactly `757a968`**.

## IS2.1 Install / upgrade — exact head `757a968` `[Fact]`

This build's DB was **empty (0 tables, no demo)**; validated by a **fresh exact-head
install** `odoo-bin -i shopify_connector_core,shopify_connector_product,shopify_connector_sale`:
registry loaded in 32.3 s, **exit 0**, all three modules `installed`
(`core 19.0.1.7.2`, `product 19.0.2.0.0`, `sale 19.0.1.0.0`). **Zero**
registry / module-load / Python-import / selection / constraint / XML / data /
security errors; **zero** migration requirement; **zero** shopify warnings. The
only log "error" substring is a standard-Odoo **`mail`** module docutils RST
render notice (`<string>:38 Unexpected indentation`, module 22/43) — unrelated,
not absorbed.

## IS2.2 Focused Layer 1 results (all green) `[Fact]`

Command form: `odoo-bin -u <module> --test-enable --test-tags '/<module>:<Class>.<method>' --stop-after-init --no-http`.

| Scope | Method / mapping | Result |
| --- | --- | --- |
| CORE `TestJobDispatch` | `core_dispatch_selftest → local_only` | ✅ |
| CORE `TestJobDispatch` | unexpected job type → `remote_effect_not_replay_safe` | ✅ |
| CORE `TestJobDispatch` | handler-policy completeness (`_get_handlers − _get_replay_policies = ∅`) | ✅ |
| CORE `TestJobDispatch` | synthetic missing-handler completeness proof (non-vacuous) | ✅ |
| CORE `TestJobDispatch` | read-safe retry eligibility (`local_only ∈ REPLAY_SAFE_RETRY_POLICIES`) | ✅ |
| CORE `TestJobDispatch` | existing missing-handler safe failure → `failed_final`/`unknown_system_error` | ✅ |
| PRODUCT `TestProductImportMatching` | `product_import_sync → remote_read_replay_safe` | ✅ |
| PRODUCT `TestProductImportMatching` | **installed-scope** handler-policy completeness (new) | ✅ |
| CUSTOMER `TestCustomerImportMatching` | `customer_import_sync → remote_read_replay_safe` | ✅ |
| CUSTOMER `TestCustomerImportMatching` | **installed-scope** handler-policy completeness (new) | ✅ |

CORE focused: `0 failed, 0 error(s) of 6 tests`. PRODUCT+CUSTOMER focused:
`0 failed, 0 error(s) of 4 tests`.

## IS2.3 Genuine concurrency proof — each ×3 on exact head `757a968` `[Fact]`

`odoo-bin -u shopify_connector_core --test-enable --test-tags '/shopify_connector_core:TestDrainOwnershipReplayGenuine.<method>'`, three separate processes.
Every 40001 is a **REAL PostgreSQL serialization failure** (benign committed
store-row `write_date` bump on a **distinct backend PID** vs the real
`_lock_store_for_lifecycle FOR NO KEY UPDATE`), on genuine bounded `db_connect`
cursors at REPEATABLE READ — never an injected Python exception. Runtime log shows
`ERROR: could not serialize access due to concurrent update` + dispatcher INFO
`Job N hit a PostgreSQL concurrency failure (SQLSTATE 40001) … the handler is not
replayed` for each attempt.

1. **Read-safe recovery** `test_b_still_connected_post_transport_serialization_routes_once`
   — green ×3 (jobs 2/4/6). Asserted: genuine SQLSTATE 40001; distinct backend PID;
   **exactly one transport** (handler not replayed); job → **`retry_waiting`**;
   **`retry_count == 1`** (one bounded increment); store stays `connected`; **lease
   count 0**; no raw `SerializationFailure`/`InFailedSqlTransaction` as the result.
2. **Conservative replay-policy recovery** `test_conservative_replay_policy_routes_to_blocked_manual_review_not_retry`
   — green ×3 (jobs 3/5/7). Same genuine 40001 + distinct PID + **exactly one
   transport**; recovery **does not re-invoke the handler**; final job state
   **`blocked_manual_review`**, `error_class` **`duplicate_risk`**,
   `manual_review_subreason` **`duplicate_risk`**; **never `retry_waiting`**; **lease
   count 0**. Each run: `0 failed, 0 error(s) of 2 tests`.

## IS2.4 Standard suites + lifecycle/ownership ×3 `[Fact]`

| Group | Command | Result |
| --- | --- | --- |
| Complete standard **core** suite | `-u shopify_connector_core --test-enable` | `0 failed, 6 error of 486` — the 6 = the known `notification_type` `res.users` `setUpClass` artifact (RR-F / issue #157); all other 480 green |
| Complete standard **product** suite | `-u shopify_connector_product --test-enable` | `0 failed, 0 error of 176` |
| Complete standard **sale/customer** suite | `-u shopify_connector_sale --test-enable` | `0 failed, 0 error of 95` |
| **Product lifecycle** `TestProductCallSiteLifecycleGenuine` ×3 | tag `shopify_connector_product_callsite_lifecycle` | `0 failed, 0 error of 4` (runs 1/2/3) |
| **Customer lifecycle** (LeaseVisibility + RaceA + RaceB Genuine) ×3 | tag `shopify_connector_customer_callsite_lifecycle` | `0 failed, 0 error of 6` (runs 1/2/3) |
| **PR #163 ownership/concurrency** `TestDrainOwnershipReplayGenuine` ×3 | `:TestDrainOwnershipReplayGenuine` | `0 failed, 0 error of 6` (runs 1/2/3; **6 genuine SQLSTATE-40001 recoveries logged each run**) |

Test-count deltas vs the prior build (34923103: core 476 / product 174 / sale 93)
reconcile exactly: +10 core = the DEC-031 Layer 1 tests added at `4b45d35`; +2
product / +2 sale = the declared-policy test (`4b45d35`) + this session's
installed-scope completeness test (`757a968`). **All Layer 1 and PR #163-owned
tests are green.**

## IS2.5 `notification_type` artifact classification `[Fact — unrelated pre-existing]`

The 6 core-suite errors are `setUpClass` failures — creating a test user **before
any test logic runs** — in six classes this session never touches
(`test_connection_lifecycle`, `test_credential_access`, `test_credential_service`,
`test_job_log_system_append`, `test_readiness_slot_closure`, `test_test_connection`),
each raising `null value in column "notification_type" of relation "res_users"
violates not-null constraint`. Root cause proven this session: standard Odoo 19
`res.users.notification_type` is a **stored computed** field (`mail`,
`_compute_notification_type`, `required=True`, **no plain default**) that only
*transitions* an existing value by `mail.group_mail_notification_type_inbox`
membership; a test user created with `group_ids:[(6,0,[shopify group])]` under a
**no-demo** build joins no inbox-notification group (verified:
`base.group_user` does **not** imply it here), so the column lands NULL. This is
the base-environment artifact RR-F / issue #157 ("six core `setUpClass` errors
expected to reproduce identically") — independent of the dispatch change (touches
neither `res.users` nor these classes; the DEC-031 `TestJobDispatch` class, which
creates only a store, passes). All 6 are the identical artifact (12 log lines, no
other exception type); **zero assertion failures**. Not absorbed into PR #163; not
fixed (the six classes are outside this session's authorized files).

## IS2.6 Independent zero-residue / leak audit `[Fact]`

Fresh-connection SQL audit after the full matrix: connector **jobs 0, job logs 0,
call leases 0, stores 0, credentials 0, store settings 0, customer bindings 0,
product template bindings 0, product variant bindings 0**; test-pattern
partners 0; test product templates 0. Non-test standard rows left intact
(ownership-scoped cleanup): 8 `product_attribute` = standard `product_barcodelookup`
xmlids; 18 `ir_cron_trigger` = standard *Base: Auto-vacuum internal data* (**0
shopify-owned trigger delta**); 29 `ir_attachment` = standard install assets (**0
shopify-model, 0 test-named**). Sessions: **1 active (this webshell psql), 0
idle-in-transaction, 0 leaked odoo backend cursors**; **0 leaked odoo processes**
(all `--stop-after-init` runs exited). No pre-existing row deleted.

## IS2.7 Security / transport audit `[Fact]`

Across all captured runtime logs and DB records: **no** access tokens (only the
`shpat_DUMMYDUMMYDUMMY0000000000000000` synthetic sentinel appears), **no**
Authorization / `X-Shopify-Access-Token` headers, **no** raw credentials, **no**
GraphQL request bodies with sensitive values, **no** GraphQL mutation
(`productUpdate`/`customerUpdate`/`productCreate`/…), **no** customer PII beyond
synthetic `example.com`/`myshopify.com` fixtures, **no** image bytes, **no**
connection strings, **no** sensitive `/tmp` path leaks. **No outbound HTTP** (all
`_send` patched → no real network), **no live Shopify mutation, no real merchant
data, no Task 012 execution, no outbound write to Shopify**.

## IS2.8 Warnings / errors classification `[Fact]`

| Item | Class |
| --- | --- |
| `mail` module docutils RST render notice (`Unexpected indentation`) at install | standard-Odoo cosmetic, **unrelated** |
| 6 core `setUpClass` `notification_type` errors | **unrelated pre-existing** (RR-F / #157) |
| Genuine `ERROR: could not serialize access due to concurrent update` (×N in genuine tests) | **expected** — the induced real 40001 the recovery path is proving |
| Layer 1 / PR #163-owned test errors or failures | **none** |

## IS2.9 Limitations `[Fact / Open]`

1. **No GitHub API/`gh`/git-fetch** from this container (private repo → 404). PR
   open/draft/unmerged flags and "no newer control-room review supersedes
   `4702066051`" were **not live-verified**; every required SHA was verified against
   remote-tracking refs captured at build provisioning and **all match** (head
   `757a968` pre-commit `4b45d35`, integration `80a8bbb`, PR #150 `10d0034e`, PR
   #151 `e4669aaf`, Shopify-connector `dd6ecb8f`); integration has not advanced
   past `80a8bbb`, so #163 is unmerged.
2. **Base→head genuine upgrade not performed** — this build shipped an empty
   no-demo DB, so validation used a fresh exact-head install (not a
   `4b45d35→757a968` migration). No schema/XML/data change exists between the two,
   so no migration path is exercised or required.
3. The `notification_type` artifact prevents 6 user-creating core classes from
   running their bodies in this no-demo environment (see IS2.5) — pre-existing,
   non-blocking for PR #163.

## IS2.10 SRR-03 status + merge recommendation `[Fact / Recommendation]`

- **SRR-03: OPEN (unchanged).** DEC-031 Layer 1 validation does not address, and
  makes no claim about, the SRR-03 disconnect/in-flight-job checkpoint-3 race
  closure criteria; none of those criteria are satisfied by this session.
- **Recommendation:** DEC-031 Layer 1 (AR-048) and the existing PR #163 dispatch
  ownership/replay correction are **fully green on exact head `757a968`** —
  focused, genuine-concurrency ×3, lifecycle ×3, ownership ×3, and the complete
  product/sale suites, with zero residue/leak and a clean security audit. **No
  blocking defect owned by PR #163.** Route to **control-room runtime review**;
  keep PR #163 **draft/unmerged**. Prompt E **BLOCKED**, Layer 2 **deferred**.

## IS2.11 Governance `[Fact]`

The **validated code SHA is `757a968`**; the docs-only evidence commit that records
this section is made **after** runtime validation and is itself **not
runtime-tested** (documentation-only, zero code change — it cannot alter the
validated behaviour). **No live Shopify request. No merge. PR #163 kept draft. No
Prompt E. Layer 2 deferred. SRR-03 remains OPEN. `Shopify-connector` / `main` /
plain `dev` unchanged. PR #150 / #151 untouched.**
