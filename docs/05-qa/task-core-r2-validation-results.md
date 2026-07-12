# CORE-R2 — Foundation Slice 1 — Validation Results

> **Status: draft implementation record for control-room review.** CORE-R2
> **implementation** gate OPENED by control-room comment `4952145926`
> (authorized base `Shopify-connector` @
> `ce504f42824807e215ee21df3dfd4eed9bb9a275`, ratifying D-CR2-A…F). This slice
> implements a **strict subset** of the merged packet
> ([`../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`](../07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md))
> / analysis ([`../03-architecture/disconnect-quiescence-remediation-analysis.md`](../03-architecture/disconnect-quiescence-remediation-analysis.md)),
> AR-047. **SRR-03 remains OPEN. No remediation and no runtime-green is claimed.**
> Branch `claude/core-r2-implementation-foundation`; draft PR into
> `Shopify-connector`; base `ce504f42824807e215ee21df3dfd4eed9bb9a275`.

This record deliberately separates: (1) implemented facts; (2) static evidence
actually produced this session; (3) tests authored but **not** executed; (4)
runtime status; (5) intentionally deferred Slice 2/3 items; (6) residual risks;
(7) rollback.

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
7. Focused tests (authored, not executed).
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

## 3. Tests authored but NOT executed `[Fact — authored] / [Open — unexecuted]`

`addons/shopify_connector_core/tests/test_disconnect_quiescence.py` (new), plus
minimal regressions in `test_api_client.py` and `test_job_enqueue.py`. **These
were NOT run — there is no Odoo runtime in this session.** They are authored to
pass on a real Odoo 19 runtime and are the control-room's to execute (SRR-06).

Two deliberate test styles:

- **`TransactionCase`** tests drive the **real** `execute_business`/`_admit`/
  `_send`/`_release_lease` path. Under Odoo test mode the `_admit` side cursor
  (`registry.cursor()`) is a `TestCursor` sharing the single test connection, so
  these prove admission *logic* (gate, ordering, token-once, release) but not
  genuine cross-connection independence.
- **`TestGenuineConcurrencyPrimitives`** opens **genuine independent PostgreSQL
  connections** via `odoo.sql_db.db_connect` (never `registry.cursor()`), commits
  a store fixture, and exercises the exact PostgreSQL sequence `_admit` relies on
  (store-row `FOR SHARE`, lease `INSERT`, independent `COMMIT`) with bounded
  `statement_timeout` and durable, fail-loud cleanup.

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
| 13 | Caller rollback cannot erase the committed lease | `test_committed_lease_survives_caller_rollback` (genuine connections) |
| 14 | Two concurrent admissions both commit | `test_two_concurrent_admissions_commit_distinct_leases` (genuine connections) |
| 15 | Concurrent leases have distinct keys | same |
| 16 | `_send` receives the captured token | `test_token_read_once_and_passed_to_send` |
| 17 | `_send` does not reread credentials | `test_send_reads_credential_only_when_token_absent` |
| 18 | Token never in lease rows | `test_token_never_appears_in_lease_rows` |
| 19 | Enqueue captures `connection_generation` | `test_enqueue_captures_connection_generation` (`test_job_enqueue.py`) |
| 20 | Existing public execute callers operational | `test_execute_preserves_two_arg_send_seam` + all pre-existing api-client/test-connection tests (unchanged) |
| 21 | No advisory lock | `test_no_advisory_lock_in_client_source` |
| 22 | No request/main cursor commit | `test_no_main_cursor_commit_in_client_source` |

**Known test-framework limitation (honest):** proofs 13/14/15 are genuine
cross-connection properties. Odoo's `TestCursor` makes the production `_admit`'s
side commit share the test transaction, so those three are proven at the
PostgreSQL-primitive level via real `db_connect` connections (the identical
sequence `_admit` performs), **not** through the production `_admit` call. The
full two-server, production-path proof (packet T-19) remains the deferred Odoo.sh
runtime item (RR-4 / SRR-09).

---

## 4. Runtime status `[Open]`

**No Odoo runtime was exercised.** No test was run; no Odoo.sh green summary
exists. Per SRR-06 the full `shopify_connector_core` suite (including these new
tests) must be captured verbatim on Odoo.sh by the control-room before any
runtime claim. **This session makes no runtime/green/live claim.**

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
- **Noted as future-slice (not defects here):** no missing-credential pre-check on
  the dormant `execute_business` path; a caller that already holds a conflicting
  store-row update lock on its main cursor before entering `execute_business`
  could self-block — both belong to the later call-site/lifecycle slice.
- **Two runtime assumptions the tests rest on (documented, both expected to
  hold):** (a) the `TestBusinessAdmission` class opens a nested side
  `registry.cursor()` while the test cursor is live — this relies on Odoo's
  `test_lock` being **reentrant** (`RLock`), the established pattern Odoo core
  itself uses to commit a side transaction inside a `TransactionCase`; (b) the
  genuine-connection statement-timeout bound was hardened from a session `SET`
  to `SET LOCAL statement_timeout` so it covers each cursor's single transaction
  and auto-resets at commit — no leak onto the pooled connection. Both are the
  control-room's to confirm at Odoo.sh runtime along with the rest of the suite.

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
- **RR-B (runtime unproven):** no Odoo runtime; tests unexecuted (SRR-06 / RR-7).
- **RR-C (genuine two-server proof deferred):** proofs 13/14/15 are shown at the
  PG-primitive level with real connections; the production-path two-server proof
  is the deferred T-19 / SRR-09 / RR-4 item.
- **RR-D (dormant ACL/user-identity):** the lease ACL is admin-only; when a
  production call site activates `execute_business`, the drain's actual execution
  identity must be re-checked against this ACL (later slice).
- **RR-E (empty-credential on dormant path):** `_admit` does not pre-check a
  missing token (unlike `execute()`); harmless while dormant, to be handled when
  `execute()` is privatized.

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
- **SRR-03 remains OPEN.** No remediation claimed. No runtime/green/live claim.
- Draft PR only — not marked ready, not merged; Slice 2 not begun.
