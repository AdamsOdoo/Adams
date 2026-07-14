# CORE-R2 — Foundation Slice 1 — Validation Results

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
