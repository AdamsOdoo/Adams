# PR #204 — Batch 1 consolidated security and operability correction

> **2026-07-30. Implementation record only.** NOT an acceptance, NOT a review,
> NOT a ready-mark, NOT a merge, NOT self-accepted, and NOT an Odoo.sh,
> live-Shopify, campaign or UAT claim. PR #204 stays **draft and open**.

| Item | Value |
| --- | --- |
| Starting head (control-room verified) | `0a15b176e60b77bf2f40195a9961591c788e14f8` |
| Base | `mvp/program-integration@87f1763a1ca699947d665c92bef614bd1fc3168d` (unchanged, verified ancestor, 0 behind) |
| Odoo pin | `30bde9ff758834a4912c5ae55843d3a7dad849f1`, verified on every run |
| History operation | **Additive only.** No rebase, reset, amend, squash or force-push |
| Shopify | **none** — no store, credential, request, mutation or webhook |

---

## 1. What the independent review found, and what was actually true

The reviewer failed the starting head and reproduced an obsolete-token race with
two genuine PostgreSQL connections. This session reproduced it independently
before changing the affected path, and the reproduction is preserved as a
regression test.

### 1.1 The P0, confirmed

`_refresh_access_token` performed the whole refresh in **one** side transaction:
read the client pair, POST to Shopify, write the cache. Odoo cursors run
REPEATABLE READ, so a rotation or a clear that committed **during** the network
call was invisible to that transaction — and when the cache row was absent (the
ordinary first-refresh case) the write was a plain `INSERT` that conflicted with
nothing. A token minted from secret pair A was committed, stamped current, and
served for up to 24 hours after the merchant had rotated to pair B.

`credential_id` did not catch it, exactly as the reviewer said: a rotation
updates that row **in place**, so the relation still pointed at it.

**Reproduced here, at the exact starting head.**
`addons/shopify_connector_core/tests/test_credential_provenance_race.py` is
written to run unchanged on the vulnerable head — it drives only public routes
and passes no argument that head lacks. Run against a worktree at `0a15b17`:

```
0 failed, 4 failed of 5 tests            # TestCredentialProvenanceRaceAtAnyHead
AssertionError: 'shpat_MINTEDFROMPAIRA…' == 'shpat_MINTEDFROMPAIRA…' :
  a token minted from the SUPERSEDED credential pair was cached;
  this is the reproduced obsolete-token defect
```

The fifth test (cache **present**) passed at the old head, and its log explains
why the other four are the dangerous shape:

```
ERROR: could not serialize access due to concurrent delete
WARNING …store_credential: Shopify access-token refresh failed for store 4;
        the current token is still valid and was used.
```

With a cache row present the ORM `UPDATE` hit a genuine serialization failure —
which the old code swallowed through a blanket `except Exception`. That is the
same raw-escape defect §9.3 closes, surfaced by the reproducer rather than
argued for.

### 1.2 The false migration claim, confirmed by measurement

The batch-1 records state *"warm `-u` update + standard suite (migration
`19.0.1.16.0` executed)"*. It did not execute and could not have. Pass 2 clones
the database pass 1 installed and runs `-u` against the **same** tree, so
`ir_module_module.latest_version` already equals the manifest version, and
Odoo's migration manager runs a script only when the installed version is
strictly lower (`odoo/modules/migration.py::migrate_module` → `compare()` at the
pin). Pass 2 executes **zero** upgrade scripts on every run, by construction.

A genuine `50b770a3` → candidate upgrade, run here, executes them and shows what
`19.0.1.16.0` actually does:

```
module shopify_connector_core: Running upgrade [19.0.1.16.0>] post-migrate
module shopify_connector_core: Running upgrade [19.0.1.17.0>] post-migrate
…19.0.1.16.0.post-migrate: Wave 5 credential migration: 0 row(s) stated
                           explicitly as the offline access-token mode.
```

**0 row(s)** — its predicate (`WHERE auth_mode IS NULL`) cannot be true, because
`auth_mode` is `required=True` with a default and Odoo's `_auto_init` backfills
and constrains it before any `post-migrate` runs. The script was harmless and it
was never evidence of anything.

---

## 2. The corrections

### 2.1 P0 — credential provenance is now structural

* **`credential_epoch`** on `shopify.connector.store.credential`: a monotonic
  identity version bumped **exactly once** per sanctioned set, replace, clear or
  mode switch, folded into the *same* statement as the values it describes and
  always under the store lifecycle lock. Neither the row id (unchanged by a
  rotation) nor `write_date` (transaction-fixed, and not advanced at all by a
  same-value write) is sufficient, which is why it is a counter.
* **`credential_epoch` + `auth_mode` on the cache row**, written from the
  identity the exchange was verified against.
* **One shared read predicate** (`_TOKEN_CACHE_PROVENANCE_SQL`) used by *every*
  committed read, refusing a row on stale epoch, wrong mode, absent/invalid
  credential, emptied client pair, quarantine, cross-store or cross-company
  disagreement, or expiry. An unprovable token is indistinguishable from no
  token.
* **The refresh is two transactions.** The lock cursor takes the advisory lock
  (always `pg_try_advisory_xact_lock`, never blocking), re-checks the committed
  cache, and captures the identity and lifecycle position. The network call runs
  holding no row lock. A **new** transaction — a fresh snapshot that can see what
  committed meanwhile — takes the store lock then the credential row lock,
  compares, and only then writes. A re-read in the first transaction would have
  returned its own stale snapshot, which is precisely why the original defect was
  invisible to the code meant to catch it.
* **40001/40P01/55P03 are caught and normalized** into the connector taxonomy,
  fail-closed, with the SQLSTATE only in `technical_detail`.
* **Upgrade does not bless an unprovable cache.** Migration `19.0.1.17.0`
  deletes pre-correction rows; the token is ephemeral, no Shopify request is made
  during the update, and no offline token or configured pair is touched.

### 2.2 P1 — lifecycle eligibility and disconnect quiescence

`_ensure_access_token` takes a `purpose` and checks a fresh **committed**
`(state, generation)` read holding no row lock:

| purpose | states | route |
| --- | --- | --- |
| `business` | `connected` | jobs, drains, Layer 2 (`_admit`, `_admit_mutation`) |
| `setup` | `setup_incomplete`, `connected`, `reconnect_needed` | `execute()`, Test Connection, readiness probe |
| `reconnect` | `reconnect_needed`, `disconnected` | the reconnect probe |

`disconnecting` appears in **no** matrix. `_token_exchange_in_flight` gives the
disconnect quiescence controller a window into the refresh through the same
advisory lock, so a disconnect cannot complete while a token is being minted.

A call-lease row was considered and rejected for that job: under direction C an
expired-but-unreleased lease is treated as live forever and is never reclaimed,
so a worker that died mid-exchange would strand the disconnect permanently and
starve every later refresher. A transaction-scoped advisory lock is released by
PostgreSQL when the backend goes away.

### 2.3 P1 — real coalescing, proved across sessions

The previous coalescing evidence was sequential-call evidence:
`pg_try_advisory_xact_lock` is **re-grantable within one PostgreSQL session**, so
on the shared in-test connection the leader branch was taken every time and the
waiter branch never executed at all.

`test_credential_provenance_race.py` uses genuine `db_connect` sessions with
asserted distinct backend PIDs, bounded `statement_timeout`/`lock_timeout`,
committed fixtures and provable teardown. The race is **stepped from inside the
patched exchange**, so it is deterministic without threads or sleeps.

### 2.4 P2 — authentication hardening

* **Closed credential-mutation surface.** The model had no `create`/`write`/
  `unlink` override at all, and the ACL grants an Administrator `create`/`write`
  — so a direct RPC, import or script skipped the cache discard, the epoch bump,
  the cleared verification stamp and the `connected` → `reconnect_needed`
  demotion. All three now route through a named surface guarded by a
  non-serializable sentinel (Odoo's RPC context is JSON, so it cannot be forged);
  `unlink` is refused outright. Deliberately **not** `env.su`-gated:
  `_mutate_token` runs as the calling user so the Administrator-only ACL stays
  live, and requiring `sudo()` would have replaced a live check with a bypass.
* **Redirects refused.** Requests enables redirect-following by default,
  including POST, and 307/308 preserve the body — the client secret would have
  been re-posted to whatever host the response named. `allow_redirects=False`,
  `verify=True`, and a 3xx is a sanitized `TEMPORARY` failure that records the
  status only, never the `Location`.
* **Cache/SEC-3 reads audited**, every shape through the one predicate.

### 2.5 Location search — the client half

Server continuation (`next_offset` + a token bound to store/company/side/query),
fail-closed offset validation, selection revalidation after every search, clear
and load-more **and again at submit**, the same `state.busy` discipline every
other wizard operation uses, per-identity deduplication, in-place row update
after a mapping instead of collapsing accumulated pages, and four distinguishable
empty states. The "indexed" claim is removed: `name` carries no index and no
btree index serves `ilike '%term%'` anyway.

### 2.6 TD-020 — operationally complete

The single-pair route stays for focused recovery, with `expected_state` now
**mandatory** at every public boundary (the wizard passed `or None`, so an empty
snapshot silently disabled the protection).

`withdraw_first_push_decisions_for_mapping` is the mapping-level route: one
mapping (never a caller-assembled recordset), Administrator-only, store/company
structural, no developer mode, a preview disclosing affected/previewed/confirmed
counts **and how many quantities are live on Shopify**, an explicit reason and one
consequence confirmation, mapping-then-bindings row locks in ascending id order,
a mandatory state signature covering added and removed pairs as well as changed
ones, every safety check on every pair before any write (all-or-nothing), audit
at both the mapping and the pair level, zero Shopify calls, and the D-013-4 gate
untouched so the full ceremony is required again. `_assert_remap_is_safe` is
unchanged — this is the governed route **to** the state it requires.

### 2.7 Evidence integrity

* Genuine version-to-version migration passes in the runner, from `50b770a3`
  and from `0a15b176`, each with an idempotency re-run.
* `verify_migration_evidence` fails a migration pass that ran no script;
  `verify_no_migration_ran` fails the warm pass if one ever appears there. Both
  directions asserted in `--self-test`, including the exact shape published
  before: a green pass with no marker.
* The location tour's `:contains('Mapped')` also matched "Not mapped"
  (hoot-dom's `:contains` is a case-insensitive substring match), so every
  mapped-state assertion passed whichever badge rendered — including the one
  meant to prove a mapping was created. Exact `data-mapped` attributes now, an
  eligible Odoo location chosen deterministically, and the database consequence
  asserted.
* The HOOT client-secret leak guard asserted `document.body.innerHTML`, which
  cannot contain a value set through the `.value` property at all — vacuous for
  the mechanism it named. It now asserts the secret reached the intended request
  (anti-vacuity first), then its absence from every other request, every own
  property of the component, every DOM attribute, every live input value and the
  rendered panel.
* The exchange test asserted an endpoint its own stand-in had just constructed.

---

## 2.8 The starting head's changed-path inventory, corrected

The Batch 1 records describe `50b770a3` → `0a15b176` without naming
**`.gitignore`**, which commit `cad932f` also changed (six lines: `.focused-bin/`
and `ci-artifacts-*/`). It is inert — both entries are local run artifacts and
neither is repository content — but an inventory that omits a changed path is
not an inventory. The complete list for that range is:

```
.gitignore
addons/shopify_connector_core/__manifest__.py
addons/shopify_connector_core/migrations/19.0.1.16.0/post-migrate.py
addons/shopify_connector_core/models/{__init__,shopify_connector_api_client,
  shopify_connector_setup_wizard,shopify_connector_store,
  shopify_connector_store_access_token,shopify_connector_store_credential}.py
addons/shopify_connector_core/security/shopify_connector_company_rules.xml
addons/shopify_connector_core/static/src/{js,scss,xml}/…            (5 files)
addons/shopify_connector_core/tests/…                                (8 files)
addons/shopify_connector_inventory/…                                 (9 files)
addons/shopify_connector_product_export/tests/test_u3_hoot_suite.py
tools/run_connector_suite.sh
```

— 36 files, 3701 insertions, 118 deletions.

## 3. What is NOT claimed

* **No Odoo.sh run.** Local/CI-grade supporting evidence only (DEC-041 D8).
* **No live-Shopify validation, no UAT, no campaign.** Zero Shopify contact of
  any kind; every test patches `_send`, `_send_lifecycle` and
  `_send_token_exchange`, and no real credential exists in the repository or the
  environment.
* **No independent review of this head.** This session implemented; it does not
  review, accept, ready-mark or merge its own work.
* TD-020 and the authentication path remain **"implemented, pending independent
  re-review"** — never "resolved".

## 4. Deferred, explicitly

Batch 2 is untouched: canonical Store Settings, the feature-to-scope catalogue,
product/customer import enumeration, order-scan enablement, the tax workspace,
export prepare, fulfillment settings, per-domain operating-mode declarations,
dashboard liveness, consolidated attention, and the remaining campaign journey
families. TD-004, TD-005 and TD-007 are retained byte-for-byte.

## 5. Remaining gates

1. Independent exact-head Batch 1 re-review.
2. Batch 2 only after control-room acceptance of Batch 1.
3. Later full-journey/security review.
4. Exact-head Odoo.sh qualification.
5. Controlled live-Shopify validation.
6. Business UAT.
7. Acceptance and merge authorization.
