# Execution method — sync-engine concurrency validation (auditable, sanitized)

> Reproducibility record for the P-B concurrency validation and its
> Scenario-6 faithful rerun. No executable driver is committed (governance
> forbids committing runtime scripts); this document records the exact
> commands, transaction boundaries, barrier/lock points, and the **merged
> ORM methods** invoked, so the run is independently auditable. **No
> credential or secret appears here.** All work ran in a disposable,
> ephemeral container against a local disposable PostgreSQL cluster; every
> database was dropped at cleanup.

## 1. Runtime provisioning (commands)

```
# Odoo 19 source (public branch, shallow)
git clone --depth 1 --branch 19.0 --single-branch https://github.com/odoo/odoo.git /opt/odoo
# -> odoo/odoo @ c5f1a963... , release version_info (19,0,0,'final',0)

# Python deps (venv)
python3 -m venv /opt/odoo-venv
/opt/odoo-venv/bin/pip install -r /opt/odoo/requirements.txt        # pinned for py3.11

# PostgreSQL 16 (disposable local cluster, non-root owner)
initdb -D /opt/pgdata -E UTF8 --locale=C                            # run as unprivileged 'odoo' OS user
# pg_hba.conf: local + 127.0.0.1/32 = trust (local disposable only)
pg_ctl -D /opt/pgdata -o "-p 5433 -c listen_addresses=127.0.0.1 -k /tmp" -l /opt/pgdata/pg.log start
createuser -s odoo ; createdb -O odoo <DBNAME>                      # <DBNAME> in {pbtest, pbscen, pbscen6}
```

Odoo config (`/opt/odoo.conf`, no secrets):
```
[options]
db_host=127.0.0.1
db_port=5433
db_user=odoo
db_password=False
addons_path=/opt/odoo/addons,/opt/odoo/odoo/addons,/home/user/Adams/addons
data_dir=/opt/odoo-data
```

## 2. Baseline install + test (command)

```
odoo-bin -c /opt/odoo.conf -d pbtest -i shopify_connector_core \
  --test-enable --test-tags /shopify_connector_core \
  --without-demo=all --stop-after-init --workers=0 --max-cron-threads=0 --log-level=test
```
Only `shopify_connector_core` tests run; no branch/domain module installed.

## 3. Scenario harness — driver model

The harness is a single Python file (`driver.py`, **not committed**) run as
**separate OS processes**. It uses Odoo strictly as a library:

```
config.parse_config(['-c','/opt/odoo.conf','-d', DB])
registry = odoo.modules.registry.Registry(DB)          # loads registry from DB
cr  = registry.cursor()                                # ONE PostgreSQL connection per process (REPEATABLE READ)
env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
```

Each concurrent worker is therefore an **independent Odoo-library process
with its own PostgreSQL connection** against one shared database
(process-level concurrency; B-like, **not** a deployed Odoo `--workers`
topology). Scenario 8 additionally uses two real `odoo-bin` server daemons
(Topology C, single host).

**Only merged ORM methods are invoked** — no monkeypatch, no test hook, no
production-code edit. The methods used, verbatim from the merged addon:

- `env['shopify.connector.job']._claim_for_dispatch(limit)`
- `env['shopify.connector.job.dispatch']._dispatch_one(job)` / `_start_running(job)` / `_invoke_handler(job)` / `run_drain(limit)`
- `env['shopify.connector.job.enqueue'].enqueue(store, source, 'core_dispatch_selftest', ...)`
- `env['shopify.connector.store'].action_disconnect()`   (Scenario 6 — the real lifecycle method)
- `recordset.try_lock_for_update()` (Odoo 19 primitive)

Test-data setup writes (allowed, disposable DB only, not production code):
`store.write({'state':'connected'})` to establish the connected gate;
direct `state`/`next_retry_at`/`manual_review_subreason` writes on synthetic
job records. These are **test setup**, never represented as readiness
activation.

`run_drain(limit)` body reproduced verbatim where per-worker claimed-id
capture was needed:
```
claimed = Job._claim_for_dispatch(limit)   # prints claimed.ids for evidence
for job in claimed: Dispatch._dispatch_one(job)
env.cr.commit()                            # commit at the request/transaction boundary (as the cron/RPC framework does)
```

## 4. Barrier & lock points

- **File barrier** (for simultaneous claims, Scenarios 2/8): each worker
  writes `ready_<tag>`, then spins until a coordinator creates `go`; the
  coordinator waits for all `ready_*` then `touch go`. This releases
  competing workers within ~1–2 ms.
- **Held-lock partition** (Scenario 2b): one worker runs
  `_claim_for_dispatch` then holds its transaction open (`time.sleep`) so a
  second worker's `SKIP LOCKED` claim lands on the complement rows.
- **Row-lock probe** (Scenario 3): one worker calls `try_lock_for_update()`
  on one job and holds the transaction; a third psql connection runs
  `SELECT ... FOR UPDATE SKIP LOCKED` to prove the row is locked/unlocked.

## 5. Scenario 6 faithful method (the corrected run)

Two independent transactions/connections; **commit points are explicit**.

**Worker A (library, one transaction, NO intermediate commit):**
```
claimed = Job._claim_for_dispatch(20)      # <-- takes A's REPEATABLE READ snapshot; locks the job row
job = claimed[<target>]
Dispatch._start_running(job)               # checkpoint 2 -> state 'running' (UNCOMMITTED)
signal 'started'; wait 'go_handler'        # A holds the job row lock across this pause
probe = job.store_id.invalidate_recordset(); job.store_id.state   # record checkpoint-3 view
Dispatch._invoke_handler(job)              # checkpoint 3 + no-op handler
env.cr.commit()                            # <-- A's ONLY commit (job -> 'succeeded')
```

**Worker B (independent process/connection) — the REAL lifecycle method:**
- LIB variant (raw): `store.action_disconnect(); env.cr.commit()` inside a
  library transaction (NO `retrying()` wrapper). Serialization errors
  propagate raw and are caught/reported.
- RPC variant (production path): `execute_kw(DB, uid, <pwd>, 'shopify.connector.store', 'action_disconnect', [[store_id]])`
  via XML-RPC to a running `odoo-bin` server — so Odoo's service-layer
  `retrying()` wraps the call.

**Coordination (deterministic, no fixed sleeps to force the result):**
1. Launch A; wait for `started` (A holds the job row lock at `running`).
2. Launch B; B signals `b_start`, then calls the real `action_disconnect()`.
3. Poll `pg_stat_activity` until B's backend shows `wait_event_type='Lock'`
   (B is genuinely blocked on the job row) — captured as pg-locks evidence.
4. `touch go_handler` -> A runs checkpoint-3 + handler + commit.
5. `wait` for both; capture B's return/error/retry and all final states.

RPC-server start (for Worker B):
```
odoo-bin -c /opt/odoo.conf -d pbscen6 --http-port 8171 --workers=0 \
  --max-cron-threads=0 --no-database-list --log-level=info
```
A test-only admin password (not recorded here) and membership in the
shipped `group_shopify_connector_admin` were set in the disposable DB so
XML-RPC could invoke the Admin-only `action_disconnect`; both vanished when
the DB was dropped.

## 6. Scenario 8 (Topology C) method

```
# two independent application-server daemons, one shared DB:
odoo-bin -c /opt/odoo.conf -d pbscen --http-port 8169 --workers=0 --max-cron-threads=0
odoo-bin -c /opt/odoo.conf -d pbscen --http-port 8170 --workers=0 --max-cron-threads=0
# concurrent drain: barrier-synchronized XML-RPC run_drain(20) to BOTH ports.
```
An initial single-server probe (`run_drain(5)` on one port) processed the
first 5 jobs; the subsequent barrier-synchronized rounds against BOTH
servers processed the remaining 35 concurrently (see corrected counts in
the results doc).

## 7. Evidence capture & cleanup

- Job/log rows dumped via `env['shopify.connector.job'(.log)].search(...).read`
  to CSV; worker JSON printed to stdout; PostgreSQL lock/serialization
  evidence from `pg_stat_activity` and the PostgreSQL/server logs.
- Cleanup: stop all servers, release/rollback held locks, drop every
  disposable DB (`pb%` count -> 0). No synthetic store/token remains in any
  persistent DB; no real Shopify credential/token/API call was ever made.

## 8. Integrity confirmations

- Only merged ORM methods were invoked; no addon/test/production file was
  modified, monkeypatched, or given a test hook.
- No credential, token, real shop domain, customer data, or private DB URL
  appears in this document or any evidence file (only synthetic `PB-*` /
  `pb-*.myshopify.com` / `gid://pb/...`, and the local `127.0.0.1:5433`
  trust socket).
- The temporary `driver.py` / XML-RPC client scripts are intentionally
  **not committed**; §3–§6 record their exact behavior for audit.
