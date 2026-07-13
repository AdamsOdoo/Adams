# Task 011B — Customer Matching Scalability: Validation Record

> **Partial runtime evidence — concurrency correction pending exact-head
> rebuild (2026-07-13, review `4687443143`):** the exact-head Odoo 19 runtime
> was first executed on the committed code SHA
> `9895919a6cc191cb24f694c1b601a0304fedda15` (build `34844515`) — fresh install,
> the full core/product/sale standard suites, the focused **32** standard
> methods, the **100,000-partner benchmark**, the indexed-lookup **EXPLAIN**
> evidence, and a genuine **single-DB module-upgrade backfill** all ran green
> (recorded verbatim in **§18**, accepted for that code SHA). **Correction to
> that record:** §18.6 initially **mis-classified** the deterministic 4/4
> concurrency-test failure as an Odoo.sh "environment/pooler limitation."
> Control-room review `4687443143` identified the true cause — the **same
> framework-level `Registry._lock` post_install deadlock already confirmed in
> CORE-R2 §4.2**: the spawned worker blocks inside `api.Environment(cr_w, …)` →
> `Registry.__new__` → `with cls._lock:` and never reaches the SQL race.
> **Bounded, sanitized phase instrumentation confirmed it** (last worker phase
> `before_api_environment`; `after_api_environment` never reached). A
> **test-only** correction (bounded-window `Registry._lock` decoupling, CORE-R2
> §4.2 pattern — real independent `db_connect` connections, `pg_blocking_pids`
> attribution, binding-INSERT predicate, and every route/uniqueness/cleanup
> assertion **preserved**) makes the genuine race pass **3/3 stable** in the
> working tree (~0.2 s each; see **§19**). **No Task 011B production/model code
> changed** — the fix touches only the test file. **These working-tree results
> are correction evidence only; final concurrency closure REQUIRES a new Odoo.sh
> build whose checked-out HEAD is the committed correction SHA.** The
> **fully-authoritative isolated base→head build backfill** gate remains
> **OPEN** (single linked DB). **Issue #157** (`res_users.notification_type`)
> stays separate — **not fixed**. **PR #150 stays open, draft, unmerged; no live
> Shopify request; SRR-03 remains OPEN.**
>
> **Latest session (2026-07-13):** a further isolated base-alignment session
> merged the branch (**one normal merge, no rebase/squash/force-push**) onto
> the current `Shopify-connector` tip
> `912801508155c6358e8f5f1a7a0aaf01ae573675` — **CORE-R2 Foundation Slice 1 /
> PR #156 merged** into that tip. Aligned head:
> `2316128d606e5e990ff6e2c026caf302d4146f7e`. **AR-045** (Task 011B)
> preserved unchanged; **AR-047** (CORE-R2) carries forward its Foundation
> Slice 1 revisions; **AR-046 still intentionally absent** — Task 010B / PR
> #151 remains open, draft, and unmerged. Net PR diff vs the new tip remains
> the same **8 Task 011B files**; production/test files remain byte-identical
> to the prior head. **No Odoo runtime executed this session; no
> runtime-green claimed on the new head; CORE-R2 full completion NOT
> claimed (SRR-03 remains OPEN).** See **§15** for the full session record.
>
> **Prior parallel session (2026-07-12, authorization `4952271013`):** the
> branch was **base re-aligned by a normal merge** onto the (then-current)
> `Shopify-connector` tip `ce504f42824807e215ee21df3dfd4eed9bb9a275` (**CORE-R2
> / PR #154** disconnect-quiescence design merged; **AR-047** added, **AR-045**
> Task 011B preserved, **AR-046** intentionally absent — Task 010B is still in
> its own PR); the two **opt-in classes' tags were corrected** to explicit
> `post_install` / `-at_install` / `-standard` (clearing Odoo's
> at_install-XOR-post_install warning); and the control-room-**accepted**
> standard Odoo.sh suite evidence (review `4680380669`) is carried forward.
> Still **no Odoo runtime** in this environment — the opt-in concurrency and
> 100k benchmark remain **execution-ready but PENDING**, with the exact
> invocations recorded. See **§14** for the full session record. No production
> code changed; no live Shopify request made. (**Superseded by the
> 2026-07-13 session above** — `ce504f` is no longer the current base.)
>
> **Status: implementation authored; static + AST checks executed;
> runtime tests, genuine concurrency proof, benchmark numbers, and the
> authoritative module-upgrade/backfill duration are all PENDING runtime
> execution (this environment has no Odoo runtime).** Produced 2026-07-11;
> **focused correction 2026-07-12** addressing ChatGPT review
> `4950230315` (genuine independent-transaction concurrency test;
> deterministic 100k corpus with exact counters; full matching-cost
> throughput probe; fail-loud backfill proxy; evidence wording no longer
> overstates unexecuted results); **second focused correction 2026-07-12**
> addressing ChatGPT review `4950353232` — execution-safety of the opt-in
> harness only: **worker-owned cursor** (the worker thread creates/owns/
> rolls-back/closes its own PostgreSQL connection; nothing crosses the
> thread boundary but `queue`/`Event` signals), an **attributed lock-wait
> proof** (`pg_blocking_pids(B)` contains A **and** B's blocked statement
> is the binding `INSERT`, both server-side booleans; the wait must clear
> after A commits), **bounded timeouts** everywhere with fail-closed
> termination, **durable cleanup that re-raises + a fresh-connection
> zero-rows verification**, **complete first-collision assertions**
> (`retry_count == 1`, `next_retry_at` populated, attempt + retry log rows),
> a **type-only redacted** backfill/worker diagnostic, and an **exact
> per-run marker** as the benchmark corpus identity (no id-range);
> **third focused correction 2026-07-12** addressing ChatGPT review
> `4951165587` — execution-safety of the opt-in harness only: the branch
> was **base-aligned** onto the current integration tip
> `fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f` (a normal merge commit that
> pulls in PR #153's concurrency-validation evidence, disjoint from every
> Task 011B file — all PR #153 evidence preserved); the block evidence now
> requires a **server-side `INSERT INTO` + binding-table regex** (not a bare
> table mention) with the raw query text still kept out of Python; the fresh
> **cleanup and verification connections apply transaction-local
> `lock_timeout` + `statement_timeout`** so they cannot hang; the worker is
> **daemonized** as a last-resort process-liveness guard; sanitized
> emergency cursor-teardown failures are recorded and asserted absent; and
> the diagnostic wording no longer claims an unredacted trace survives in
> host logs. The accepted Task 011B **production design is unchanged** by
> any correction — all three touch only the test file and the shared docs.
>
> **Nothing here claims a runtime pass.** Candidate-set equivalence, the
> concurrency route, the benchmark budgets, the backfill duration, and the
> Odoo.sh suites are **authored, not proven** — each is marked PENDING
> until it actually runs green. Odoo.sh is not run in this session; no
> live/dev-store Shopify fixture is authorized; live Shopify validation
> depends on CORE-R2.

---

## 1. Session identity

| Item | Value |
| --- | --- |
| Task | 011B — Customer Matching Scalability (indexed normalized-email lookup) |
| Original base SHA | `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d` (implementation + first two corrections) |
| Current base SHA | `912801508155c6358e8f5f1a7a0aaf01ae573675` (`Shopify-connector` tip after **CORE-R2 Foundation Slice 1 / PR #156** merged; base-aligned via a normal `--no-ff` merge commit **`2316128d606e5e990ff6e2c026caf302d4146f7e`** this base-alignment session, 2026-07-13). Prior alignments: `ce504f…` (CORE-R2 design / PR #154, merge `9bc224e`), `cfdb057…` (U0 / PR #155, merge `66b0023`), `65e915a…` (U0 / PR #152), `fcbbb0b…` (PR #153), original `f9c3c5f…`. |
| Aligned PR head | base-alignment merge **`2316128d606e5e990ff6e2c026caf302d4146f7e`** (`9128015…` is an ancestor; `merge-base(head, origin/Shopify-connector) == 9128015…`); the PR head then advances only by this session's documentation commit, if any (see §15). |
| Base verification | `origin/Shopify-connector` tip == `912801508155c6358e8f5f1a7a0aaf01ae573675` (no drift from the required integration tip). One conflict — `architecture-review-log.md` only (no `addons/**`/`tests/**`/Task 011B production/test conflict — CORE-R2 Foundation Slice 1 is confined to `addons/shopify_connector_core/**`, disjoint from Task 011B's `addons/shopify_connector_sale/**`), resolved by **preserving both sides completely** (git-verified **0 lines lost from either side**): the Task 011B **AR-045** row (ours) kept immediately followed by the updated CORE-R2 **AR-047** row (theirs) → order AR-043/044/045/047, **no AR-046**; `research-handoff.md` and `sync-engine-risk-register.md` auto-merged cleanly (disjoint insertion points, no conflict). PR diff vs `9128015…` = **exactly the 8 Task 011B files**; no CORE-R2 / U0 / Task 010B file appears as a PR change; production `models/**` + `tests/__init__.py` **byte-identical to `c234107`** (the merge added only docs). Full detail: **§15**. |
| Gate comment | `4948879507` (Task 011B gate-opening act on PR #149) |
| Branch | `claude/task-011b-customer-matching-k5ux9b` |
| Parallel task | Task 010B (`claude/task-010b-product-import-completeness`) — disjoint production module; **not read, copied, or modified** |
| Binding decisions | D-011B-1 … D-011B-7 |

## 2. Exact changed files (8 authorized, all within the allowlist)

| # | File | Change |
| --- | --- | --- |
| 1 | `addons/shopify_connector_sale/models/__init__.py` | one import line (`shopify_connector_res_partner`) |
| 2 | `addons/shopify_connector_sale/models/shopify_connector_res_partner.py` | **NEW** — `_inherit='res.partner'`, the `shopify_connector_email_normalized` field + its compute only |
| 3 | `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py` | **only** `_find_active_candidates` + `_find_archived_candidates` bodies, plus the class recall-safety docstring paragraph and both method docstrings that described the removed full scan |
| 4 | `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py` | **NEW** — field/compute, equivalence corpus, routing regression, concurrency, source guards, benchmark harness |
| 5 | `addons/shopify_connector_sale/tests/__init__.py` | one import line |
| 6 | `docs/05-qa/task-011b-validation-results.md` | **NEW** — this record |
| 7 | `docs/05-qa/architecture-review-log.md` | one appended AR row (AR-045; renumbered from AR-044 after the U0 acceptance closure was assigned AR-044) |
| 8 | `docs/01-research/research-handoff.md` | one new top entry |

No forbidden file changed: no `shopify_connector_core`/`shopify_connector_product` file, no customer-binding model, no store-settings, no other importer method, no matching-policy change, no partner uniqueness constraint, no migration/hook, no `*.xml`/`*.csv`/`__manifest__`/`security`/`data`/`.github/workflows`, no `adams_base`, no `main`, no plain `dev`.

## 3. Odoo 19 source-verification findings (primary source — official `odoo/odoo` @ `19.0`)

Because this environment has no Odoo runtime (`import odoo` → `ModuleNotFoundError`), semantics were verified against the official Odoo 19 source tree.

### 3.1 `odoo.tools.email_normalize` (`odoo/tools/mail.py`, branch 19.0)

- **[Fact]** Signature: `def email_normalize(text, strict=True):`. The **default is `strict=True`**; the merged importer and this task's field both pass `strict=False` explicitly.
- **[Fact]** Call chain: `email_normalize → email_split → email_split_tuples → email.utils.getaddresses`, then `_normalize_email`.
- **[Fact]** `email_split_tuples` guards falsy input: `if not text: return []`. So `email_normalize(False/None/'')` → `email_split` `[]` → returns `False`. **This makes the compute safe on the (majority) email-less partners at backfill — it never raises.**
- **[Fact]** With `strict=False`: if more than one address is found the **first** candidate is returned (docstring: `'tony@e.com, "Tony2" <tony2@e.com>'` → `'tony@e.com'`); with `strict=True` the same input returns `False`.
- **[Fact]** `_normalize_email`: `local_part.lower()` only when the local part encodes as ASCII (non-ASCII/SMTP-UTF8 local parts are preserved as-is); the domain is **always** `.lower()`. Wrapped `'Name <NaMe@DoMaIn.CoM>'` → `'name@domain.com'`.
- **[Inference]** The stored column and the importer's incoming path call the **identical function with the identical `strict=False`**, so for any given email string they produce the identical normalized value. This is what makes the indexed equality lookup recall-equivalent to the removed per-record Python compare, by construction.

### 3.2 Stored computed indexed field (`odoo/orm/fields.py`, branch 19.0; ORM reference 19.0)

- **[Fact]** `store` — "whether the field is stored in database (default: `True`, `False` for computed fields)". Setting `store=True` on a computed field materialises a real column.
- **[Fact]** `index` allowed values: `"btree"`/`True` (standard index), `"btree_not_null"`, `"trigram"`, `None`/`False`. D-011B-1 mandates `index=True` → a standard **btree** index. (`btree_not_null` would be marginally more compact here since most rows are NULL; it is **not** what the accepted decision specifies, so it is intentionally not used — noted only as a possible future optimisation.)
- **[Fact]** `readonly` — "only has an impact on the UI. Any field assignation in code will work (if the field is a stored field or an inversable one)." So `readonly=True` does **not** block the compute from writing the column.
- **[Fact]** A stored field is directly searchable — no `search=` method required.
- **[Fact/standard behaviour]** Stored computed fields are initialised for existing rows by Odoo's stored-compute initialisation at module install/upgrade (single pass, recompute-marked during `_auto_init`), and recomputed on every write to an `@api.depends` dependency. The **exact** 100k-partner upgrade duration is a runtime measurement — see §8 (OUTSTANDING).

### 3.3 Existing importer + binding (merged repo, re-read this session)

- **[Fact]** Current `_find_active_candidates` ran `Partner.search([('email', '!=', False)])` then a Python `email_normalize(strict=False)` compare; `_find_archived_candidates` did the same with `active_test=False` + `('active','=',False)`. Both are the O(n) full scan Task 011B removes.
- **[Fact]** `_normalize_incoming_email` (unchanged, out of scope) is `email_normalize(raw_email, strict=False) or False` — the exact normalizer the new stored column mirrors.
- **[Fact]** `shopify.connector.customer.binding` constraints (unchanged): `UNIQUE(store_id, shopify_gid)` and `UNIQUE(store_id, partner_id)` — the binding-layer duplicate-prevention backstop D-011B-6 relies on.
- **[Inference]** Odoo's `mail` module defines its own `email_normalized` field on partners. The connector deliberately does **not** reuse it (D-011B-1 mandates a connector-owned column, and mail's field is a different concept whose normalization semantics are not guaranteed to equal the importer's `strict=False` call). The connector field name is namespaced (`shopify_connector_email_normalized`) — **no collision**.

## 4. D-011B-1 — the indexed normalized field (as built)

`addons/shopify_connector_sale/models/shopify_connector_res_partner.py`:

```python
shopify_connector_email_normalized = fields.Char(
    string='Shopify Connector Normalized Email',
    compute='_compute_shopify_connector_email_normalized',
    store=True, index=True, readonly=True, help=...)

@api.depends('email')
def _compute_shopify_connector_email_normalized(self):
    for partner in self:
        partner.shopify_connector_email_normalized = email_normalize(
            partner.email, strict=False,
        ) or False
```

- `_inherit='res.partner'`, one field, one compute. **No** `create`/`write`/`unlink` override, **no** inverse, **no** search method, **no** uniqueness constraint, **no** `sudo()`, **no** company-dependent behaviour. Depends only on `email`.

## 5. D-011B-2 — the indexed lookup (old vs new)

| | Old (removed) | New (Task 011B) |
| --- | --- | --- |
| Active | `search([('email','!=',False)])` + Python `email_normalize` filter | `search([('shopify_connector_email_normalized','=',normalized_incoming)])` |
| Archived | `with_context(active_test=False).search([('email','!=',False),('active','=',False)])` + Python filter | `with_context(active_test=False).search([('shopify_connector_email_normalized','=',normalized_incoming),('active','=',False)])` |

Incoming-email normalization, candidate ordering (`_build_candidate_payload` still sorts by `id` asc, caps at 20, reports true `candidate_count`), ambiguity/archived/blind-create/binding-conflict routing, and the error taxonomy are **byte-untouched**. No new fallback key; no name/phone/address matching.

## 6. Equivalence corpus (D-011B-3) — authored, pending runtime execution

The new test retains the **old full-scan path as a test-only reference** and asserts, for every corpus probe with a truthy normalized value, `set(old_ids) == set(new_ids)` — independently for active and archived. Corpus (stored as active **and** archived partners): normal lowercase, mixed case, leading/trailing whitespace, wrapped display-name, quoted display name, plus-addressing, unicode local part, uppercase domain, malformed, empty string, `False`, multiple-email string, comma-separated, semicolon-separated, duplicated normalized email across partners, and active+archived copies of one normalized email. The equivalence assertion hard-codes **no** expected normalizer output — it compares the two paths — so it self-corrects to whatever the merged Odoo 19 normalizer actually produces.

## 7. Routing regression, concurrency, source guards

- **Routing (tests 15–21) — authored, pending runtime execution:** existing-binding shortcut; single active match binds `match_key='email'`; >1 active → `ambiguous_match` (no row); candidate-evidence cap = 20 with true `candidate_count`; archived-only → `duplicate_risk`; no-usable-email → blind-create block (`duplicate_risk`); single-candidate-already-bound → `binding_conflict`.
- **Concurrency (D-011B-6) — GENUINE independent-transaction test authored; result PENDING runtime execution (corrected per reviews `4950230315` and `4950353232`).** The prior two "concurrency" tests were sequential and are **no longer presented as a concurrency proof**: one is now an honestly-labeled DB constraint backstop (asserting a specific `psycopg2.IntegrityError`, no broad `Exception`), the other an honestly-labeled *sequential* stable-outcome test. The real proof is `TestCustomerMatchingConcurrency.test_genuine_independent_transaction_binding_race` (opt-in tag `shopify_connector_customer_matching_concurrency`, `-standard`). Execution-safety design (reviews `4950353232` and `4951165587`):
  - **Worker-owned, daemonized cursor.** The worker thread itself calls `db_connect(dbname).cursor()`, reports its backend PID to the parent through a `queue.Queue`, builds its own `Environment`, runs the real dispatcher, commits on the handled outcome, rolls back on an unexpected exception, and closes its cursor in its **own** `finally`. No Odoo cursor or `Environment` ever crosses the thread boundary (never `self.registry.cursor()`); parent↔worker signalling is `threading.Event`/`queue.Queue` only. The thread is created **`daemon=True`** — a last-resort process-liveness guard so a wedged worker can never keep the Python/Odoo process alive after the test fails; it does **not** replace the worker's own cursor rollback/close or the durable row cleanup, which still run and are still asserted (`worker_alive_final` must be false). Statically proven this session (AST): every `cr_w` reference is inside `run_b`, the thread is started with no cursor/Environment argument, and it is created `daemon=True`.
  - **Attributed lock-wait proof — now a proven INSERT (review `4951165587` item 1).** Synchronization does **not** accept "B is waiting on some lock", nor even "B's query mentions the binding table". A dedicated monitor connection records, server-side and as booleans only, that **`A_PID ∈ pg_blocking_pids(B_PID)`** *and* that B's active statement matches a case/quote-tolerant **`INSERT INTO` + binding-table regex** (`query ~* BINDING_INSERT_QUERY_REGEX`) — so a `SELECT`/`UPDATE`/`DELETE` of, or a bare mention of, the table cannot satisfy it. `_wait_until_blocked_by` requires **both** conditions before returning success, then proves the wait **clears** once A commits. The raw `pg_stat_activity.query` — which carries the row's email VALUES — is never selected out of PostgreSQL, so it never reaches Python or an assertion message. A **standard-CI** test (`test_binding_insert_predicate_matches_only_inserts`) evaluates the exact `query ~*` predicate against literal sample statements, proving an `INSERT INTO` the binding table matches while a `SELECT`/`UPDATE`/`DELETE` and a comment/other-statement mention do not.
  - **Bounded everything, fail closed — including cleanup SQL (review `4951165587` item 2).** Worker-start, PID-received, lock-wait, and join are each bounded by an explicit timeout; on a still-alive worker the test releases the lock barrier (rolls back A so B's `INSERT` fails out and the worker closes its own cursor), waits once more with a bounded emergency timeout, and **fails closed / inconclusive** rather than hanging. Both the fresh cleanup connection **and** the fresh verification connection now apply **transaction-local `lock_timeout` (`CLEANUP_LOCK_TIMEOUT_MS=5000`) and `statement_timeout` (`CLEANUP_STATEMENT_TIMEOUT_MS=15000`)** via `set_config(..., is_local => true)` before any ORM work, so a leaked/competing lock cancels the statement instead of hanging cleanup forever. No unbounded join, poll, **or cleanup/verification wait** exists (statically proven).
  - **Durable cleanup + verification.** The `finally` first ensures the worker exited, then rolls back/closes every parent-owned cursor **before** opening a fresh cleanup connection that deletes every synthetic row in FK-safe order; cleanup and verification **re-raise** on failure (incl. a lock/statement timeout — never swallow), and a second fresh connection asserts **zero** synthetic jobs/logs/bindings/settings/store/partner remain. Best-effort emergency cursor rollback/close failures are **captured as sanitized, type-only diagnostics** and asserted empty (never `str(exc)`), so a swallowed teardown failure cannot invalidate the cleanup claim. All race assertions still run after cleanup, so a failing assert never leaks committed rows.
  - **Expected (pending execution) two-stage route — NOT a direct `binding_conflict`:**
    1. **First collision** → transaction B passes its pre-create checks (it cannot see A's uncommitted binding), its `INSERT` blocks on `UNIQUE(store_id, partner_id)`, and once A commits it fails with a uniqueness violation; the importer savepoint rolls back and the dispatcher's fail-safe boundary routes the job to **`unknown_system_error` → `retry_waiting`** (`SAFETY_NET_ERROR_CLASSES`, one retry). The test asserts the **complete** route: `state == retry_waiting`, `error_class == unknown_system_error`, **`retry_count == 1`**, **`next_retry_at` populated**, and that both a dispatch-**attempt** log (`to_state='running'`) and a **retry** state-change log (`to_state='retry_waiting'`) exist. Verified from core source: `_invoke_handler`'s generic `except Exception` → `_route_failure('unknown_system_error', …)` → `_schedule_retry_or_fail` (`new_retry_count = 0+1`, `next_retry_at` set) → `_transition_retry_waiting`.
    2. **Forced clean-transaction retry** (A's binding now committed & visible) → a **deliberate, direct `_dispatch_one` re-invocation** — **not** the scheduler's due-time selection — makes the importer's app-level conflict guard raise **`binding_conflict` → `blocked_manual_review`** (`binding_conflict` is a `MANUAL_REVIEW_SUBREASON`); the test asserts `blocked_manual_review`, `manual_review_subreason == binding_conflict`, a `blocked_manual_review` state-change log, and **exactly one** surviving binding.
    3. **Exactly one binding survives** (A's, first GID); no duplicate partner or binding.
  - No new lock/constraint/bypass/error class is introduced. Two limits are stated, not hidden: the retry leg is a **forced** clean-transaction retry (it does **not** prove the scheduler's due-time selection), and the standing multi-server claim/dispatch concurrency caveat (SRR-03/04/09) is **restated, not resolved** — this test proves only the binding-layer duplicate-prevention route under one real two-transaction race.
- **Source guards (tests 24–30) — executed statically this session:** AST-level — neither candidate method contains the old `('email','!=',False)` full-scan domain; both search `shopify_connector_email_normalized`; `email_normalize(strict=False)` asserted on both compute and incoming sides; the field depends only on `email`; **only** the two candidate methods reference the indexed column; the new partner file contains no override/constraint/sudo and a single `_inherit='res.partner'`.

## 8. Benchmark method + numbers (D-011B-4 / D-011B-7) — corrected per review `4950230315`

The harness lives in `TestCustomerMatchingBenchmark`, tagged `post_install` + `-at_install` + `-standard` + `shopify_connector_customer_matching_benchmark` (post_install-only, excluded from the standard suite; see §14.3 for the `-at_install` correction), invoked explicitly:

```
odoo -d <db> -i shopify_connector_sale --test-enable --stop-after-init \
     --test-tags shopify_connector_customer_matching_benchmark
```

**Deterministic corpus with an exact run-marker identity (review `4950353232` item 6):** exactly **100,000** partners by index-based allocation — indices `0..1499` share one normalized email (**1,500 = 1.5% ≥ 1%**), `1500..11999` carry wrapped/display-name emails (`"Wrapped N" <wrapped.N@…>`, **10,500 = 10.5% ≥ 10%**), `12000..99999` carry unique ordinary emails (`user.N@…`); `active = (idx % 10) >= 3` yields **exactly 70,000 active / 30,000 archived (30%)**. Every generated row carries a **unique per-run marker** — a UUID-derived domain suffix `b011b-<marker>.example` (and the marker in the partner name) — so corpus identity is the marker, **never a `min_id..max_id` interval** a concurrent insert could fall inside. The three categories use distinct local-part prefixes (`shared`, `wrapped.`, `user.`) so each is countable in the DB by an exact marker pattern. The test **asserts exact counters both in-Python and in the DB (marker-scoped only)**: `total == 100000`, `active == 70000`, `archived == 30000`, `shared == 1500`, `wrapped == 10500`, `ordinary == 88000`, and `non-null normalized == 100000`. This composition is validated standalone (pure Python, emulating the `=like` marker predicates) this session: in-Python and DB-marker counts both `{total:100000, active:70000, archived:30000, shared:1500, wrapped:10500, ordinary:88000, non_null:100000}`.

**Matching-cost probe (not one SQL lookup):** a test-only `_matching_probe` runs the full customer-matching cost — `_normalize_incoming_email(raw)` (`email_normalize(strict=False)`), then `_find_active_candidates`, then `_find_archived_candidates` fallback when no active candidate — with no Shopify call and no partner/binding creation. A deterministic **1,000-probe mix**, scoped to the same run marker, exercises **700 active-unique hits, 150 archived-only hits, 100 clean misses, 50 shared/ambiguous** probes; the test **asserts each tally exactly** (proving the intended mix ran), emits the active-hit/archived-hit/miss/ambiguous counts, latency p50/p95/max, and customers/second. Host-dependent timing budgets are **emitted, never asserted** (a slow host cannot red the suite). Probe-mix classification is validated standalone this session (tally `700/150/100/50`; the shared email yields 1,050 active candidates → ambiguous).

**Backfill proxy integrity + sanitized diagnostic (review `4950353232` item 5):** `_measure_backfill_proxy` forces a full recompute (`modified(['email'])` + `flush_all()` + materialize) and returns `(seconds, None)` or `(None, sanitized_diagnostic)`. On failure the diagnostic is **type-only** — the module-level `_sanitized_exception_diagnostic(exc)` emits only `type(exc).__name__` plus a fixed generic sentence, then runs it through the connector `redact()` helper; it **never** includes `str(exc)`/`repr(exc)`, so partner emails, SQL `VALUES`, connection paths, or access tokens in a DB error message can never leak into the emitted line, an assertion message, or this record. A standard-CI test (`test_helper_diagnostic_strips_sensitive_sentinels`) proves a supplied sensitive sentinel (a fake email + token) is absent from the diagnostic while the exception type is still identified. The test emits `backfill_proxy.status=UNUSABLE` + the sanitized diagnostic and **asserts `backfill_seconds is not None`** — a failed proxy **fails the benchmark**, never a silent pass. The proxy is explicitly labeled `backfill_authoritative=PENDING`: the authoritative 100k module-upgrade/backfill duration must be measured by an actual upgrade on a runtime host.

| Measurement | Budget | Result |
| --- | --- | --- |
| Single-customer match p50 / p95 / max | p95 ≤ 50 ms | **PENDING — not run (no Odoo runtime this session)** |
| Matching-cost throughput (1,000-probe mix) | ≥ 20 cust/s | **PENDING — not run** |
| Stored-field recompute-pass proxy (100k) | ≤ 10 min | **PENDING — not run** |
| Module-upgrade/backfill duration (100k) | ≤ 10 min | **PENDING — authoritative measure is an actual module upgrade on a runtime host; the in-test proxy does not replace it** |

No evidence is invented; these remain PENDING and the PR stays draft. If the measured upgrade exceeds 10 minutes, the batched-post-init-hook fallback is **not** implemented here — it requires explicit ChatGPT approval with the numbers in hand.

## 9. Static / local checks actually executed

Implementation session (2026-07-11):
- `python3 -m py_compile` on all 5 changed/new Python files → **clean**.
- Standalone AST replication of every source guard (tests 24–30) against the real source files → **all 22 assertions PASS** (no full-scan domain in either method; both search the indexed column; `email_normalize(strict=False)` on compute + incoming; depends-only-on-email; only two methods touch the column; new partner file free of override/constraint/sudo; single `_inherit='res.partner'`).
- `git diff --stat` confirms the importer change is confined to the two methods + the recall-safety docstring paragraph.

Focused-correction session (2026-07-12, review `4950230315`):
- `python3 -m py_compile` on the rewritten `test_customer_matching_scalability.py` → **clean**.
- AST source guards re-run against the (unchanged) production files → **still all 22 PASS**; `git diff` confirms **no production/model file changed** since reviewed head `e8126ec` — the only change is the test file.
- Standalone simulation of the benchmark's deterministic allocation and probe-mix classification (pure Python, no Odoo) → counters `{total:100000, active:70000, archived:30000, shared:1500, wrapped:10500, ordinary:88000}`; probe tally `{active_hit:700, archived_hit:150, miss:100, ambiguous:50}` → **all assertions PASS**.
- Core-source verification of the concurrency taxonomy (`shopify_connector_job_dispatch.py` `_invoke_handler`/`_route_failure`/`_schedule_retry_or_fail`; `shopify_connector_job.py` `MANUAL_REVIEW_SUBREASON_SELECTION`) confirms the expected two-stage route (`unknown_system_error`→`retry_waiting`, then `binding_conflict`→`blocked_manual_review`).

Second focused-correction session (2026-07-12, review `4950353232`):
- `python3 -m py_compile` on the rewritten `test_customer_matching_scalability.py` → **clean**.
- **Race-safety AST guards** (standalone) over the concurrency test → **all PASS**: `cr_w` is referenced only inside `run_b` (worker-owned, never the parent); the thread is started with no cursor/Environment argument; every thread `join()` / `Event.wait()` / `queue.get()` is bounded by a `timeout`; `_durable_cleanup` re-raises (bare `raise`, no swallow); the worker closes `cr_w` in its own `finally`.
- **Marker-benchmark simulation** (standalone, emulating the `=like` marker predicates) → in-Python **and** DB-marker counts both `{total:100000, active:70000, archived:30000, shared:1500, wrapped:10500, ordinary:88000, non_null:100000}`; probe tally `{active_hit:700, archived_hit:150, miss:100, ambiguous:50}` → **all assertions PASS**.
- Targeted greps confirm: **0** broad `assertRaises(Exception)`, **0** `self.registry.cursor()`, **0** raw `str(exc)`/`repr(exc)` **emits** (the three residual matches are the helper docstring, a comment, and the sentinel test's `assertNotIn(str(exc), …)` proof), **3** `pg_blocking_pids` uses, **7** independent `db_connect(dbname).cursor()` connections, and no unbounded `join()`/`wait()`.
- `git diff --name-only e8126ec` confirms **no production/model/init/manifest file changed** since the implementation commit — the only code change across both corrections is the test file (+ the three shared docs).
- Core-source re-confirmation that `retry_waiting` carries `retry_count = 0+1` and a populated `next_retry_at` (`_schedule_retry_or_fail`), that `_start_running` appends an `attempt`/`to_state='running'` log and `_transition_retry_waiting`/`_transition_blocked_manual_review` each append a `state_change` log, and that the `write()` start-gate does **not** forbid `retry_waiting → running` (so the forced retry leg invokes the handler).

Third focused-correction session (2026-07-12, review `4951165587`):
- **Base-aligned** the branch onto the current integration tip via a normal merge commit: `git merge --no-ff origin/Shopify-connector` (`fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f`). The integration tip adds only PR #153's concurrency-validation evidence (87 files, all under `docs/05-qa/**` and disjoint from every Task 011B file), so the merge was **conflict-free**; all PR #153 evidence and history are preserved and the shared append-only docs retain both tasks' entries.
- `python3 -m py_compile` on the corrected `test_customer_matching_scalability.py` → **clean**.
- **Race-safety AST guards** (standalone, now 10 checks) → **all PASS**: the five prior checks, **plus** (6) the worker thread is created `daemon=True`; (7) both `_durable_cleanup` and `_verify_cleanup` call `_apply_cleanup_bounds(cr)` and re-raise; (8) `CLEANUP_LOCK_TIMEOUT_MS`/`CLEANUP_STATEMENT_TIMEOUT_MS` are finite positive ints and the helper sets both bounds transaction-local (`set_config(…, true)`); (9) `_blocking_evidence` SQL tests `query ~* BINDING_INSERT_QUERY_REGEX` and never selects the raw `query` column out; (10) `_wait_until_blocked_by` requires `blocked_by AND is_binding_insert` together.
- **Production-source AST guards** re-run against the (still byte-unchanged) production files → **all 22 PASS**.
- **Marker-benchmark simulation** re-run → unchanged: counts `{total:100000, active:70000, archived:30000, shared:1500, wrapped:10500, ordinary:88000, non_null:100000}`; probe tally `700/150/100/50` → **PASS**.
- Test-method count: **34** total — **32 standard** (`TestCustomerMatchingScalability`, incl. the new `test_binding_insert_predicate_matches_only_inserts` and the sanitized-diagnostic test) + **2 opt-in** (`TestCustomerMatchingBenchmark`, `TestCustomerMatchingConcurrency`, both `-standard`).
- Targeted greps confirm: **0** raw `str(exc)`/`repr(exc)` **emits** (residual matches are prose/comments + the sentinel proof), `daemon=True` present, `set_config('lock_timeout'…)` + `set_config('statement_timeout'…)` present, `query ~*` INSERT predicate present.
- `git diff` confirms the three production files (`shopify_connector_res_partner.py`, `shopify_connector_customer_importer.py`, `models/__init__.py`) and `tests/__init__.py` are **byte-identical to `e8126ec`** and to the pre-correction PR head — only `test_customer_matching_scalability.py` (+ the three shared docs) changed; **no new repository file added**.
- No runtime execution: Odoo.sh, the concurrency tag, the 100k benchmark, and the authoritative upgrade/backfill were **not** run (nor claimed) this session.

## 10. Odoo.sh runtime

### 10.1 Base-alignment session (2026-07-12, review `4680106356`)

Review `4680106356` **ACCEPTED** the third focused correction and set base-alignment onto the current integration tip as the mandatory prerequisite before the Odoo.sh runtime gate.

**Superseding base-synchronization amendment (2026-07-12):** `Shopify-connector` advanced again to **`cfdb05703a65f82b34a9a11364aab6fc960cca9d`** (U0 / PR #155 acceptance closure). Re-aligned via a normal merge commit **`66b0023`** (`cfdb057…` is an ancestor). Two shared append-only docs conflicted (no addon/test conflict): `research-handoff.md` (resolved preserving both sides — the new U0 acceptance-closure top entry + the Task 011B entry) and `architecture-review-log.md` (**AR-044 reassigned to the U0 acceptance closure; the Task 011B row renumbered to AR-045**, cross-references updated). All U0 / PR #155 files + history preserved. The `65e915a…` alignment below was the prior step.

The original base-alignment (review `4680106356`) performed **only** base alignment + evidence documentation (no code/test change):

- `git merge --no-ff origin/Shopify-connector` (`65e915aada32930a19a14c94d23dc9bd5e6fb517`, `Shopify-connector` after **U0 / PR #152** merged) → merge commit **`19c0911b13e8a4b98845f741fbede9da6055594e`** (the new PR head).
- **Conflict handling:** the only conflict was the shared append-only `docs/01-research/research-handoff.md` (both U0 and Task 011B prepend an entry). Resolved by **preserving both sides completely** — the Task 011B entry **and** the U0 entry, with the shared `CORE-R1` tail retained once; verified programmatically that **0 lines were lost from either side** and no section header is duplicated. **No `addons/**`, `tests/**`, or Task 011B production/test file conflicted or changed** (had one, this session would have stopped and reported without resolving).
- **Post-merge invariants (git-verified):** `65e915a…` is an ancestor of the new head; the PR diff vs `65e915a…` is **exactly the 8 Task 011B-owned files** (`models/__init__.py`, `shopify_connector_res_partner.py`, `shopify_connector_customer_importer.py`, `tests/__init__.py`, `tests/test_customer_matching_scalability.py`, `docs/01-research/research-handoff.md`, `docs/05-qa/architecture-review-log.md`, `docs/05-qa/task-011b-validation-results.md`); **no U0 / PR #152 artifact, no Task 010B file, and no CORE-R2 file appears as a PR change**. All U0 / PR #152 files and history are preserved.

### 10.2 Standard Odoo.sh suites — OUTSTANDING (not executable/observable from this environment)

**Not run this session.** This environment has **no Odoo runtime** (`import odoo` → `ModuleNotFoundError`, re-confirmed), so the standard suites cannot be executed locally. The aligned head was pushed (which is what triggers the operator's Odoo.sh build), but **no Odoo.sh commit status and no GitHub check run is posted for `19c0911`** (`get_status` → `state: pending, total_count: 0`; `get_check_runs` → `total_count: 0`), so **no build result is observable from this environment**. Consistent with the CORE-R1 and PR #153 precedent, Odoo.sh runtime evidence is **operator-provided** (the verbatim install log). No result is invented here.

Required before merge review (to be run on the operator's Odoo.sh for head `19c0911`, and the verbatim output quoted here — `0 failed, 0 error(s)` for each):

| Standard suite | Result |
| --- | --- |
| `shopify_connector_core` | **PENDING — operator Odoo.sh run (verbatim log)** |
| `shopify_connector_product` | **PENDING — operator Odoo.sh run (verbatim log)** |
| `shopify_connector_sale` (incl. the standard `test_customer_matching_scalability.py` tests: field/compute, equivalence, routing, source guards, INSERT-predicate + sanitized-diagnostic guards — **34** methods, of which the **2 opt-in** classes are `-standard`-excluded) | **PENDING — operator Odoo.sh run (verbatim log)** |

The two opt-in tags (`shopify_connector_customer_matching_concurrency`, `shopify_connector_customer_matching_benchmark`) were **not** invoked this session, and **no live/dev-store Shopify request was made** (no credential, token, or Admin API call).

## 11. Limitations (honest)

1. No Odoo runtime in this environment → the equivalence, routing, genuine-concurrency, and benchmark tests were **not executed** here. Every runtime result is marked **PENDING**; correctness so far is argued from primary-source verification + static/AST checks + standalone simulations + the self-validating equivalence design. None of these substitutes for the runtime closure.
2. The genuine concurrency test commits synthetic fixtures on independent connections, spawns a worker thread that owns its own cursor, and cleans up + verifies in `finally`; it is authored to run under its explicit tag on a runtime host and is **excluded from standard CI**. Its two-stage taxonomy is the **expected** route (verified from core source), **not yet observed** at runtime. Its second leg is a **deliberately forced clean-transaction retry** (a direct `_dispatch_one` re-invocation) — it proves the importer/dispatcher collision route, **not** the scheduler's due-time selection, and it makes **no** multi-server dispatch claim. If it proves unexecutable under the actual Odoo test runner, D-011B-6 must be reported as unproven — this record makes no claim that it is proven.
3. The benchmark's backfill figure is a recompute-pass **proxy**; the authoritative upgrade duration must be measured by an actual 100k module upgrade on a runtime host. A failed proxy fails the benchmark (never a silent pass).
4. D-011B-6 does not resolve the standing multi-server claim/dispatch concurrency caveat — restated only (the core `_claim_for_dispatch` docstring already notes `TransactionCase` cannot exercise real multi-worker execution).
5. `daemon=True` on the worker is a **last-resort process-liveness guard**, not a correctness mechanism — it only prevents a wedged worker from keeping the process alive after the test already failed; the worker's own cursor rollback/close and the durable row cleanup remain the real safety mechanisms and are still asserted.
6. The cleanup/verification `lock_timeout`/`statement_timeout` bounds only guarantee the opt-in test cannot hang; they are test-harness safety, not a production behaviour, and are asserted only via the AST guard here (their runtime effect is exercised only when the opt-in test actually runs).
7. **No live/dev-store Shopify fixture is authorized or run** in this session; the concurrency test uses a narrow in-process API-client stub, never a live Admin API call. **Live Shopify validation depends on CORE-R2** (the live-credential/readiness track) and remains a separate, later, explicitly-gated activity.

## 12. Rollback

Revert the single PR → the matching code path returns to the merged full-scan path (slow but correct). A normal revert/upgrade does **not** drop the additive `shopify_connector_email_normalized` column or its index; the column may remain inert. Any schema cleanup is a separate, tested migration — out of scope. No partner, binding, job, or business data is created or destroyed by the revert.

## 13. Definition-of-done checklist

Implemented / executed (this + prior sessions):
- [x] Base verified and **aligned to the current integration tip** (`fcbbb0b3fe3db9cba354a8a1c08e91036b70ec1f`, `Shopify-connector` after PR #153) via a normal merge commit; original base `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`; PR #149 merged; gate `4948879507` read.
- [x] Only the authorized files changed (implementation session: the 8-file allowlist; three correction sessions: the test file + the three shared docs, within the 4-file revision allowlist; **no new repository file added**).
- [x] **Production design implemented & accepted for the static pass:** D-011B-1 field, D-011B-2 indexed lookup — unchanged by the correction.
- [x] Field uses the exact merged normalizer `email_normalize(strict=False)` (static/AST verified).
- [x] No partner uniqueness constraint; no matching-policy change (static/AST verified).
- [x] Tests authored (equivalence, routing, genuine concurrency, deterministic benchmark, source guards); `py_compile` clean; AST source guards + benchmark simulation pass.

Authored, PENDING runtime execution (not claimed complete):
- [ ] Candidate-set equivalence proven — **authored; PENDING** the Odoo.sh run.
- [ ] Routing regression green — **authored; PENDING** runtime.
- [ ] Genuine independent-transaction concurrency route observed (`unknown_system_error`→`retry_waiting`, then `binding_conflict`) — **authored; PENDING** the opt-in runtime run.
- [ ] Benchmark budgets (p95 ≤ 50 ms; ≥ 20 cust/s) measured — **authored; PENDING** runtime numbers.
- [ ] Authoritative 100k module-upgrade/backfill duration measured — **PENDING** runtime.
- [ ] Existing sale/core/product suites green on Odoo.sh — **PENDING** runtime.

Documentation / PR:
- [x] Validation record updated (this file); AR-045 updated (renumbered); handoff top entry updated.
- [x] One draft PR into `Shopify-connector`, kept open/draft/unmerged; Task 010B untouched; all other gates closed.

## 14. Parallel base-alignment + opt-in tag/harness closure session (2026-07-12, authorization `4952271013`)

This isolated parallel session owns **PR #150, the Task 011B tests,
`task-011b-validation-results.md`, and the PR #150 body**. After the required
base-conflict resolution the shared global docs
(`architecture-review-log.md`, `research-handoff.md`,
`sync-engine-risk-register.md`, master plan) are **frozen** — no new global
closure note is appended in this parallel run; this validation record is the
session handoff.

### 14.1 Base alignment — DONE (LOOP 1)

- **Normal merge, no rebase/squash/force-push:** `git merge --no-ff
  origin/Shopify-connector` (`ce504f42824807e215ee21df3dfd4eed9bb9a275`,
  `Shopify-connector` after **CORE-R2 / PR #154** disconnect-quiescence design
  merged) → base-alignment merge commit **`9bc224e`** (starting head
  `b680e8a`).
- **Conflicts = exactly the two shared append-only docs** (CORE-R2 is
  docs-only, so **no `addons/**`/`tests/**` conflict**). Both resolved by
  **preserving both sides completely** (git-verified **0 lines lost from either
  side**):
  - `docs/05-qa/architecture-review-log.md` — kept **ours `AR-045`** (Task
    011B) *and* **theirs `AR-047`** (CORE-R2), both after **`AR-044`** (U0);
    resulting order **AR-043 → AR-044 → AR-045 → AR-047**. **`AR-046` is
    intentionally NOT present** (reserved for Task 010B / PR #151, still in its
    own PR — not fabricated here). Diff vs ours: 0 removed, +1 line (the AR-047
    row); diff vs theirs: 0 removed.
  - `docs/01-research/research-handoff.md` — kept **ours Task 011B entry** *and*
    **theirs CORE-R2 entry**, both below the shared **U0-acceptance-closure**
    top entry. Diff vs ours: 0 removed, +108 lines (the CORE-R2 entry block);
    diff vs theirs: 0 removed.
  - CORE-R2's own new files (`docs/03-architecture/disconnect-quiescence-
    remediation-analysis.md`, `docs/07-implementation-plan/task-core-r2-
    disconnect-quiescence-packet.md`) and its edits to
    `sync-engine-risk-register.md` + `implementation-ready-master-plan.md`
    merged cleanly.
- **Post-merge invariants (git-verified):** `ce504f` is an **ancestor** of the
  head; `merge-base(head, origin/Shopify-connector) == ce504f`; the PR **net
  diff vs `ce504f` = exactly the 8 Task 011B-owned files**; **no CORE-R2 /
  U0 / Task 010B file appears as a net PR change**; production `models/**` +
  `tests/__init__.py` are **byte-identical to `b680e8a`** (the merge changed
  only docs). Base merge committed **separately** from the opt-in correction.

### 14.2 Standard Odoo.sh suite evidence — ACCEPTED, carried forward (LOOP 2)

Recorded specifically as **operator-provided branch build evidence accepted by
the control room** (review `4680380669`) — a **control-room attribution
decision, NOT an independently cryptographically proven build-to-commit
mapping** (the log did not itself print the SHA). For head `b680e8a` on
database `adamsmen-claude-task-011b-customer-matching-k5ux9b-34795383`, Odoo
**19.0**, verbatim:

- `shopify_connector_core: 209 tests 1.70s 4046 queries`
- `shopify_connector_product: 61 tests 1.46s 2485 queries`
- `shopify_connector_sale: 90 tests 1.04s 1602 queries`
- `0 failed, 0 error(s) of 320 tests when loading database
  'adamsmen-claude-task-011b-customer-matching-k5ux9b-34795383'`

Confirmed: **32 standard `TestCustomerMatchingScalability` methods ran**; the
**benchmark class did not run**; the **concurrency class did not run**; the
**11 SQL ERROR-level entries are expected negative constraint-test evidence**,
not failures; **no standard failure** occurred.

**Applicability to the new head:** the base-alignment merge (`9bc224e`) changed
**only docs**, and the opt-in tag correction (§14.3) changes **only the two
`-standard`-excluded opt-in decorators** — **no standard test method changed**.
The 32-method standard suite is therefore behaviourally identical; a formal
re-run on the new head would re-confirm the same result (not run here — no Odoo
runtime). Only the STANDARD runtime gate is green; concurrency, benchmark,
authoritative backfill, and live Shopify remain separate, still-open gates.

### 14.3 Opt-in tag correction — DONE (LOOP 3)

- **Defect:** both opt-in classes were `@tagged('post_install', '-standard',
  <custom>)`. Odoo's `tagged` **unions** onto the class's inherited default
  `test_tags` (`odoo/tests/common.py`, 19.0 — `BaseCase.__init_subclass__`
  assigns `{'standard', 'at_install'}` when unset, and *"When using class
  inheritance, the tags ARE inherited"*), and the decorator **warns** when
  `not (at_install ^ post_install)`. So the effective set was
  `{at_install, post_install, <custom>}` — carrying **both** phases and
  tripping the *"A tests should be either at_install or post_install"* warning.
- **Fix (test file only):** `@tagged('post_install', '-at_install',
  '-standard', <custom>)` → effective set **exactly `{post_install, <custom>}`**
  = post_install-only, `-standard` (never in ordinary CI), custom tag retained
  and deliberately invocable, XOR warning cleared. **No test meaning changed.**
  Verified by replicating the exact Odoo-19 `tagged` union+XOR logic against the
  real decorators: both classes resolve to `{post_install, <custom>}` with the
  warning off. The un-decorated `TestCustomerMatchingScalability` stays
  `{standard, at_install}` — its **32 standard methods are unchanged (no
  standard test-count reduction)**.

### 14.4 Concurrency — preflight PASS; execution PENDING (LOOPS 4–5)

An independent preflight audit this session re-confirmed **every accepted
protection** with source line anchors (no defect found): worker **owns +
closes its own** cursor (`cr_w` referenced only inside `run_b`); nothing but
`threading.Event`/`queue.Queue` crosses the thread boundary; parent (A) and
worker (B) use **separate PostgreSQL backends** (independent
`db_connect(dbname).cursor()`, own `pg_backend_pid()`); A's first `INSERT` is
forced (`flush_all`) and **held** until the barrier `cr_a.commit()`; the
lock-wait proof requires **both** `A ∈ pg_blocking_pids(B)` **and** the
server-side `INSERT INTO`-binding predicate (`query ~*
BINDING_INSERT_QUERY_REGEX`), and the **raw `query` text never enters Python**;
all waits/joins/queue-gets and the cleanup/verification SQL are **bounded**
(finite timeouts + transaction-local `lock_timeout`/`statement_timeout`);
`daemon=True` is a **last-resort** liveness guard with `worker_alive_final`
asserted false; cleanup **re-raises** and a **fresh connection verifies zero
residue**; per-run **uuid** markers; **type-only sanitized** diagnostics; the
api-client `execute()` is **stubbed** (no live Shopify).

**No Odoo runtime here → NOT executed.** Exact invocation on a runtime host:

```
odoo -d <db> -i shopify_connector_sale --test-enable --stop-after-init \
     --test-tags shopify_connector_customer_matching_concurrency
```

Required observed sequence (asserted in the test; **still PENDING** runtime
observation): (1) A creates the winning binding and holds it open; (2) B enters
the real dispatcher; (3) B is attributed as blocked on its customer-binding
`INSERT`; (4) A commits; (5) B continues; (6) first collision classified via the
accepted safety-net retry path; (7) `retry_count == 1`; (8) `next_retry_at`
populated; (9) attempt log exists; (10) `retry_waiting` state-change log exists;
(11) forced clean-transaction retry reaches `binding_conflict`; (12) job becomes
`blocked_manual_review`; (13) exactly one binding survives (`gid_a`); (14)
durable cleanup leaves zero synthetic rows.

### 14.5 Benchmark — preflight PASS; execution + authoritative backfill PENDING (LOOPS 6–7)

Preflight audit + a standalone deterministic simulation this session
re-confirmed the **exact corpus** — in-Python **and** via DB marker `=like`
predicates (unique per-run marker domain; **no `min_id..max_id` range**):
`total=100000 / active=70000 / archived=30000 / shared=1500 / wrapped=10500 /
ordinary=88000 / non-null-normalized=100000`; the **exact 1,000-probe mix**
(`700` active-hit / `150` archived-hit / `100` miss / `50` ambiguous; the shared
email yields `1050` active candidates → ambiguous); a **full matching-cost**
probe (incoming normalize + active lookup + archived fallback) over the
**indexed** normalized column (no full scan); a **fail-loud** backfill proxy
with a type-only diagnostic; timing budgets **emitted, never asserted**; and
**no destructive cleanup** (the benchmark is a `TransactionCase` — its
transaction rolls back, so there is no whole-table delete). No defect found.

**No Odoo runtime here → NOT executed.** Exact invocation on a runtime host:

```
odoo -d <db> -i shopify_connector_sale --test-enable --stop-after-init \
     --test-tags shopify_connector_customer_matching_benchmark
```

**Authoritative 100k module-upgrade/backfill duration remains PENDING** — it
must be measured by an actual module upgrade on a runtime host; the in-test
recompute proxy does **not** replace it (and fails the benchmark loudly if it
cannot produce a usable measurement).

### 14.6 Static + adversarial checks — DONE (LOOPS 8–9)

`py_compile` + `compileall` **CLEAN**; **no conflict markers** anywhere; net PR
diff = **exactly the 8 Task 011B files**; production `models/**` +
`tests/__init__.py` **byte-identical to `b680e8a`**; **no new repository file**;
**32 standard** methods (no reduction) + **2 opt-in** (both explicit
`post_install`/`-at_install`/`-standard` + a unique custom tag); **349/349**
relative links in the edited docs resolve. One independent **adversarial
review** (41 protection checks across transaction independence, cursor
ownership, lock attribution, false-positive blocked-query detection, retry
taxonomy, cleanup reliability, daemon misuse, benchmark corpus/measurement
honesty, hidden O(n)/index usage, sensitive-diagnostic leakage, shared-doc
preservation, cross-branch contamination — plus the corpus/probe simulation) —
**all upheld, zero confirmed test-or-production defects**, so no correction loop
was required. **No live/dev-store Shopify request** was made.

### 14.7 No production change; two independent reverts (rollback)

**No production/model/core file changed this session** (byte-identical to
`b680e8a`). Two independent reverts:

1. **Base-alignment revert** — revert merge commit `9bc224e` → the branch
   returns to head `b680e8a` (pre-CORE-R2 alignment); the shared docs return to
   their prior (U0/PR-#155-aligned) state; the matching code path is unaffected.
2. **Opt-in tag/harness/evidence revert** — revert the opt-in correction commit
   → the two opt-in decorators return to `post_install`/`-standard` (which
   re-introduces the at_install-XOR warning) and this §14 record is removed;
   **no production behaviour changes** in this revert.

### 14.8 Remaining Task 011B gates (unchanged by this session)

- Full `core`/`product`/`sale` Odoo.sh suites green on the **new** head — the
  standard content is unchanged from the accepted `b680e8a` run; a formal re-run
  is PENDING (no runtime).
- Genuine independent-transaction concurrency route **observed** — PENDING the
  opt-in run.
- 100k benchmark latency/throughput numbers + **authoritative** backfill
  duration — PENDING runtime.
- Live/dev-store Shopify validation — PENDING, depends on **CORE-R2** runtime.
- ChatGPT final merge review — PENDING. PR #150 stays **open, draft,
  unmerged**.

## 15. Base-alignment session — CORE-R2 Foundation Slice 1 tip (2026-07-13)

This isolated parallel session performs **one clean base-alignment only**:
a normal merge of the current `Shopify-connector` integration tip into the
Task 011B branch. **No Odoo runtime executed in this session; no production
or test behavior changed; no CORE-R2 or Task 010B code adopted.**

### 15.1 Merge

- **Prior head:** `c234107db1256f3cec33e16ee14760eba9afea5f` (the accepted
  opt-in tag/harness/evidence commit — §14).
- **Integration tip merged:** `912801508155c6358e8f5f1a7a0aaf01ae573675`
  (`Shopify-connector` tip; **CORE-R2 Foundation Slice 1 / PR #156 merged**
  into it via merge commit `9128015`).
- **Normal merge, no rebase/squash/force-push, no cherry-pick:**
  `git merge --no-ff origin/Shopify-connector` → base-alignment merge commit
  **`2316128d606e5e990ff6e2c026caf302d4146f7e`**.
- **Verified:** `912801508155c6358e8f5f1a7a0aaf01ae573675` is an **ancestor**
  of the new head; `merge-base(HEAD, origin/Shopify-connector) ==
  912801508155c6358e8f5f1a7a0aaf01ae573675`.

### 15.2 Conflict — exactly one shared doc, resolved preserving both sides

CORE-R2 Foundation Slice 1 (PR #156) is confined to
`addons/shopify_connector_core/**` and docs; Task 011B is confined to
`addons/shopify_connector_sale/**` and docs — **no `addons/**` conflict
occurred** (git-verified: zero files under `addons/` show as unmerged).

The only conflict was **`docs/05-qa/architecture-review-log.md`**, because
this branch's (unchanged, inherited) AR-047 row sat immediately adjacent to
the new AR-045 row this branch's earlier session inserted, with no
intervening context line — git grouped the adjacent insertion and the
tip-side row edit into one hunk. Resolved by **preserving both sides
completely**: kept **ours** — the **AR-045** row (Task 011B, byte-unchanged)
— immediately followed by **theirs** — the updated **AR-047** row (CORE-R2,
now carrying the Foundation Slice 1 implementation/correction/hardening/
runtime-validation/exact-head-closure revisions appended in-place under the
same AR-047 id, per PR #156). Resulting order: **AR-043 → AR-044 (U0) →
AR-045 (Task 011B) → AR-047 (CORE-R2)**. **AR-046 is intentionally NOT
added** — Task 010B / PR #151 remains open, draft, and unmerged, so its
reserved AR-046 id is not fabricated here. No row was renumbered or
replaced; no line was lost from either side.

`docs/01-research/research-handoff.md` and
`docs/05-qa/sync-engine-risk-register.md` **auto-merged cleanly** (git
`Auto-merging`, no conflict) — the two branches' edits landed at disjoint
locations in both files, so both sides' content is fully preserved.

### 15.3 Net-diff verification (git-verified)

- Net PR diff vs `Shopify-connector` tip (`912801508155c6358e8f5f1a7a0aaf01ae573675`)
  remains **exactly the 8 Task 011B-owned files** — unchanged from §2 (no
  documentation-only alignment edit added a ninth file in this pass beyond
  this record itself, which was already one of the 8):
  `addons/shopify_connector_sale/models/__init__.py`,
  `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`,
  `addons/shopify_connector_sale/models/shopify_connector_res_partner.py`,
  `addons/shopify_connector_sale/tests/__init__.py`,
  `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py`,
  `docs/01-research/research-handoff.md`,
  `docs/05-qa/architecture-review-log.md`,
  `docs/05-qa/task-011b-validation-results.md` (this file).
- **No CORE-R2 file** (none of the 16 PR #156 files, incl.
  `shopify_connector_call_lease.py`, `test_disconnect_quiescence.py`,
  `task-core-r2-validation-results.md`) **appears as a net PR change.**
- **No Task 010B / PR #151 file** appears as a net PR change.
- **No issue #157 fixture fix** (`res_users`/`notification_type`) appears as
  a net PR change.
- **No `main` or plain `dev` branch was read, checked out, or modified.**
- The three production/test files
  (`shopify_connector_res_partner.py`, `shopify_connector_customer_importer.py`,
  `models/__init__.py`, `tests/__init__.py`,
  `test_customer_matching_scalability.py`) are **byte-identical** to the
  prior head `c234107` — **git-verified, empty diff** — confirming this
  alignment session changed **no production or test behavior**.

### 15.4 Status carried forward (not re-proven this session)

**No runtime executed in this environment.** This session does **not**
claim a runtime-green result on the newly aligned head, and does **not**
claim CORE-R2 is fully complete — only that **CORE-R2 Foundation Slice 1
(PR #156) is merged into `Shopify-connector` and was runtime-validated on
its own exact head** (`c0d455938b4a087407d6c712acbcc8bcf1b06feb`, build
`34818964`, per PR #156 / AR-047 — fresh install `0 failed, 0 error(s) of
325 tests`; CORE-R2 admission/lease classes green) — that validation is
CORE-R2's own evidence, carried by reference, not re-executed or re-claimed
here.

- **CORE-R2 Foundation Slice 1 is merged and runtime-validated** (its own
  exact-head evidence, §15 above) — but it is a **strict, dormant subset**
  of the CORE-R2 packet (no `disconnecting` state, no disconnect
  controller/cron, no `timed_out`/`completed` finalization, no
  product/customer call-site migration). **Full CORE-R2 completion is NOT
  claimed.**
- **SRR-03 (full disconnect-quiescence remediation) remains OPEN** —
  Foundation Slice 1's runtime-green admission half does not close
  admission-vs-disconnect linearization end to end.
- **Task 011B standard-suite evidence already accepted historically**
  (§14.2 — control-room review `4680380669`, head `b680e8a`, `320` standard
  tests, `0 failed, 0 error(s)`) remains accepted as **operator-provided
  branch build evidence**, not re-claimed as proof for the new head.
- **Exact-head standard-suite rerun on the newly aligned head
  (`2316128`) remains PENDING** — this session's merge changed only docs on
  the Task 011B side (production/test files byte-identical to `c234107`),
  so the standard content is unchanged, but a formal Odoo.sh rerun on the
  exact new head has **not** been executed or observed here.
- **Opt-in concurrency execution (`shopify_connector_customer_matching_concurrency`)
  remains PENDING** — not run this session (no Odoo runtime).
- **100,000-partner benchmark
  (`shopify_connector_customer_matching_benchmark`) remains PENDING** — not
  run this session.
- **Authoritative normalized-email backfill/upgrade duration measurement
  remains PENDING** — the in-test recompute proxy does not substitute for an
  actual 100k module-upgrade measurement on a runtime host.
- **Live Shopify validation remains blocked** — depends on the full CORE-R2
  remediation (SRR-03 OPEN), not merely Foundation Slice 1.
- **Issue #157** (`res_users.notification_type` post-init fixture artifact)
  **remains a separate, out-of-scope issue** — not investigated, not fixed,
  not absorbed into this alignment session or into Task 011B.
- **PR #150 remains draft and unmerged** — not marked ready, not merged,
  this session.

### 15.5 Static + adversarial checks — this session

See §16 (static validation) and §17 (adversarial review) below for the
checks executed in this alignment session.

## 16. Static validation — this base-alignment session

- `git merge-base --is-ancestor 9128015 HEAD` → **true**;
  `merge-base(HEAD, origin/Shopify-connector) == 912801508155c6358e8f5f1a7a0aaf01ae573675`
  — ancestry **PASS**.
- `python3 -m py_compile` on all 5 Task 011B Python files (both models +
  `__init__.py`, both test files) → **CLEAN**.
- `python3 -m compileall -q addons/shopify_connector_sale` → **CLEAN**.
- Exact changed-file inventory (`git diff --name-status 9128015 HEAD`) →
  **8 files**, matches §15.3 exactly (5 `addons/shopify_connector_sale/**`
  Python files, 3 docs).
- Repo-wide conflict-marker scan (`<<<<<<<`/`=======`/`>>>>>>>`) across all
  `*.py`/`*.md` → **NONE FOUND**.
- Task 011B's own addon diff vs the prior head `c234107`
  (`git diff c234107 HEAD -- addons/shopify_connector_sale/`) → **empty** —
  **no production or test behavior change** caused by this alignment
  session. (`addons/shopify_connector_core/**` shows the expected CORE-R2
  Foundation Slice 1 diff arriving via the merge — not a Task 011B change,
  not net-owned by this PR per §15.3.)
- **No CORE-R2 net-diff contamination** (§15.3 item 2) — **PASS**.
- **No Task 010B contamination** (§15.3 item 3) — **PASS**.
- **No issue #157 fixture fix** (§15.3 item 4) — **PASS**.
- Relative Markdown link validation on the three edited docs
  (`research-handoff.md`, `architecture-review-log.md`,
  `task-011b-validation-results.md`) → **351/351 relative links resolve**.
- PR #150 confirmed **open, draft, unmerged** throughout (re-checked via the
  GitHub API before and after the merge) — no local action changed that
  state.

## 17. Synchronous adversarial review — this base-alignment session

Performed in-session (not delegated to a background workflow), checking
specifically for the failure modes named in the task brief:

1. **Lost Task 011B history?** `git merge-base --is-ancestor c234107 HEAD`
   → **true** (190 Task 011B commits all remain reachable). **No loss.**
2. **Lost CORE-R2 history?** `git merge-base --is-ancestor 33505c1 HEAD`
   → **true** (PR #156's own head is an ancestor of the new Task 011B
   head). **No loss.**
3. **AR ordering correct?** `AR-043 → AR-044 → AR-045 → AR-047`, verified
   by direct grep of the resolved file. **Correct.**
4. **AR-046 accidentally inserted?** Zero `| AR-046 |` rows exist; the only
   `AR-046` occurrences are pre-existing prose inside the AR-047 row
   describing the reserved (not-yet-used) allocation. **Not inserted.**
5. **Stale base/head wording?** **FOUND AND CORRECTED** — the file's
   opening blockquote and §1 table still framed `ce504f` (the prior
   session's tip) as the "current" base. Corrected: the opening blockquote
   now leads with the 2026-07-13 session and marks the `ce504f` blockquote
   "superseded"; §1's `Current base SHA` / `Aligned PR head` / `Base
   verification` rows now read `9128015…` / `2316128…` and the prior value
   moved into the "Prior alignments" list. (The PR #150 body carried the
   same defect — corrected in the same pass, see the pushed PR body.)
6. **Production conflict resolution?** N/A — zero `addons/**` files
   conflicted (CORE-R2 Foundation Slice 1 is confined to
   `shopify_connector_core`, disjoint from Task 011B's
   `shopify_connector_sale`). Nothing to adjudicate.
7. **Task 010B contamination?** Net diff (§15.3) contains none of PR #151's
   23 files; PR #151 was read only for its current body (contamination
   avoidance), never merged, cherry-picked, or copied from. **Clean.**
8. **Premature runtime, benchmark, or live claims?** §15.4 explicitly
   states no runtime executed, no runtime-green claimed on the new head,
   and CORE-R2 full completion is not claimed — only that Foundation Slice
   1 (PR #156) is merged and was runtime-validated **on its own exact
   head**, carried by reference. Concurrency, 100k benchmark, authoritative
   backfill, and live Shopify are all explicitly marked PENDING/blocked.
   **No premature claim found.**
9. **Accidental implication that SRR-03 is closed?** §15.4 states verbatim
   "SRR-03 (full disconnect-quiescence remediation) remains OPEN." No
   wording in this session's edits states or implies otherwise. **Clean.**

**Outcome: one confirmed documentation defect found (item 5, stale
base/head wording) and corrected before push. No other defects found; no
correction loop required.**

## 18. Authoritative exact-head Odoo.sh runtime closure (2026-07-13, build `34844515`)

This is the **first actual Odoo runtime execution** of Task 011B — every
prior session (§3–§17) was authored/static-only. All numbers below are
observed on the live Odoo.sh dev build, not simulated. No production or test
code was modified this session (LOOP 9 no-op — no in-scope defect proven).

### 18.1 Build-to-commit identity (LOOP 0 gate — PASS)

| Item | Value |
| --- | --- |
| Exact code SHA | `git rev-parse HEAD` = `9895919a6cc191cb24f694c1b601a0304fedda15` (re-confirmed 4×) |
| Branch | tip of `claude/task-011b-customer-matching-k5ux9b` (detached HEAD at that tip; `origin/claude/task-011b-customer-matching-k5ux9b` decorates the same commit) |
| Working tree | **clean** — 0 unstaged, 0 staged, 0 untracked (verified via `git diff --stat HEAD`, `git diff --cached`, `git ls-files --others`) |
| Odoo.sh build ID | **34844515** |
| Database | `adamsmen-claude-task-011b-customer-matching-k5ux9b-34844515` |
| `ODOO_BUILD_URL` | `https://adamsmen-claude-task-011b-customer-matching-k5ux9b-34844515.dev.odoo.com` |
| Odoo version | **19.0**; PostgreSQL **16.14** |
| Integration base | `git merge-base --is-ancestor 912801508155c6358e8f5f1a7a0aaf01ae573675 HEAD` → **true** (ancestor) |
| Net PR scope | `git diff --name-only 9128015 HEAD` = **exactly the 8 Task 011B files** (5 `addons/shopify_connector_sale/**`, 3 docs); no PR #151 file, no issue-157 fixture fix |

### 18.2 Fresh install — GREEN (LOOP 1)

The build-time fresh install (`/home/odoo/logs/install.log`) ran
`odoo-bin -i adams_base,shopify_connector_core,shopify_connector_product,shopify_connector_sale --test-enable --test-tags /adams_base,/shopify_connector_core,/shopify_connector_product,/shopify_connector_sale,…` and finished **`Modules loaded.`** with:

- **`0 failed, 0 error(s) of 357 tests`** (build-time); per-module: core **252 tests / 1.92s / 4665 q**, product **61 / 1.67s / 2485 q**, sale **90 / 1.12s / 1602 q**; 9 post-tests.
- **0 WARNING** lines; 23 ERROR-level lines = all expected negative-constraint SQL (binding/product NOT-NULL + UNIQUE `assertRaises`) + 1 cosmetic docutils RST `Unexpected indentation`. **No `res_users.notification_type` / issue-157 error at fresh install.**

DB-schema facts (psql):

- `ir_model_fields` `res.partner.shopify_connector_email_normalized`: **store=t, index=t, readonly=t**, ttype=char.
- Physical column present (`character varying`, nullable); **btree** index `res_partner__shopify_connector_email_normalized_index` = `CREATE INDEX … USING btree (shopify_connector_email_normalized)`.
- All 4 modules `installed` (sale 19.0.1.0.0, core 19.0.1.6.0, product 19.0.1.0.0, adams_base 19.0.1.0).
- **CORE-R2 Foundation Slice 1 schema present**: `shopify_connector_call_lease`, `shopify_connector_location` (+ store/job/binding/credential/settings/log) — 10 `shopify_connector%` tables, 17 connector models; `customer_import_sync` `job_type` seam registered.
- Standard/opt-in tag separation proven at build: **32** `TestCustomerMatchingScalability` methods ran; `TestCustomerMatchingBenchmark`/`TestCustomerMatchingConcurrency`/`[TASK-011B-BENCHMARK]` = **0** occurrences.

**Fresh install (build-time `-i`) and the post-init `-u` reruns (§18.3) are recorded as distinct facts** — the fresh install is green with no #157; the `-u shopify_connector_core` rerun exposes the #157 artifact.

### 18.3 Standard suites — reruns (LOOP 2)

Each rerun: `odoo-bin -u <module> --test-enable --stop-after-init --no-http` (`-u` is required — `TestCustomerMatchingScalability` is an at_install class).

| Suite | `odoo.tests.result` | stats | WARN | SQL bad-query | Classification |
| --- | --- | --- | --- | --- | --- |
| `shopify_connector_core` | **0 failed, 6 error(s) of 264** | 159 tests / 1.05s / 1986 q | 1 | 17 | **6 = issue-157**; 11 expected-neg |
| `shopify_connector_product` | **0 failed, 0 error(s) of 53** | 61 / 1.45s / 2472 q | 0 | 6 | all expected-neg |
| `shopify_connector_sale` (011B) | **0 failed, 0 error(s) of 80** | 90 / 1.09s / 1595 q | 0 | 5 | all expected-neg |

Sale (Task 011B) rerun: **all 32** `TestCustomerMatchingScalability` methods ran; benchmark/concurrency correctly **absent** (0/0); **0 WARNING**; 5 expected-negative SQL — 2 UNIQUE dup-key (`store_partner_uniq`, `store_shopify_gid_uniq`) + 3 NOT-NULL (partner_id/shopify_gid/store_id) on `shopify_connector_customer_binding`, all traceable to `test_binding_uniqueness_constraint_backstop` and the binding-constraint tests (all passing `assertRaises`). Re-confirmed green **again** after all §18.6–§18.8 runtime operations: `0 failed, 0 error(s) of 80`, 32 methods, 0 warnings.

### 18.4 Focused 32-method class (LOOP 2/3)

`TestCustomerMatchingScalability` — **all 32** standard methods executed and passed (field store/index/readonly; compute `email_normalize(strict=False)`; create/change/clear/archived recompute; active + archived corpus equivalence vs the retained old-path reference; wrapped/mixed-case/unicode/shared-ambiguity recall; existing-binding shortcut; single-active bind; >1-active `ambiguous_match`; candidate cap 20; archived-only `duplicate_risk`; blind-create block; `binding_conflict`; uniqueness backstop; sequential post-commit conflict; 7 AST source guards; sanitized-diagnostic; INSERT-predicate). This directly proves LOOP 3's matching-correctness list (null/empty, wrapped display-name, mixed-case, non-ASCII, active lookup, archived fallback, ambiguous active/archived, exact candidate-set equivalence, indexed column usage, routing/binding-uniqueness identical, no full Python scan).

### 18.5 Indexed-lookup EXPLAIN evidence (LOOP 3/6) — on a persistent 100k corpus

A deterministic **committed** 100,000-partner corpus (`user.<idx>@bpersist011b.example`, 70k active / 30k archived) was created for meaningful plan evidence, `ANALYZE`d (honest stats: `reltuples=100044`, `relpages=5823`), then removed (§18.8).

| Path (mirrors the importer domain) | Plan | Est/actual rows | Exec time | Buffers |
| --- | --- | --- | --- | --- |
| Active-hit (`= v AND active`) | **Index Scan** on `res_partner__shopify_connector_email_normalized_index` | 1 / 1 | **0.029–0.036 ms** | 4 pages |
| Archived fallback (`= v AND NOT active`) | **Index Scan** (same index, `Filter: NOT active`) | 1 / 1 | **0.030 ms** | 4 pages |
| Forced seq scan (the removed O(n) full scan) | Seq Scan, **Rows Removed by Filter: 100,043** | — / 1 | **28.564 ms** | 5823 pages |

Planner cost: index scan **2.44** vs seq scan **5823** (~2400× cheaper). The candidate lookup uses the btree index and touches 4 pages — **no sequential full-partner scan** on the lookup path; the seq-scan contrast quantifies exactly the O(n) work Task 011B eliminated.

### 18.6 Genuine independent-transaction concurrency — DETERMINISTIC FAIL, classified ENVIRONMENT LIMITATION (LOOP 4/5) — GATE OPEN

> **⚠ SUPERSEDED / CORRECTED by §19 (review `4687443143`).** The
> "environment/pooler limitation" classification below is **WRONG**. The true
> cause is the **`Registry._lock` post_install deadlock** (CORE-R2 §4.2): the
> spawned worker blocked inside `api.Environment(cr_w, …)` and **never reached
> the SQL race** — which is exactly why no active/blocked query was observable
> (the "invisible backends" reasoning below inverted cause and effect: there was
> no query to see because the worker never issued one). A test-only fix
> (bounded-window `Registry._lock` decoupling) makes the genuine race pass 3/3
> stable. The text below is retained verbatim as the historical (mistaken)
> record; read **§19** for the correction, evidence, and fix.

Invocation: `odoo-bin -u shopify_connector_sale --test-enable --test-tags shopify_connector_customer_matching_concurrency --stop-after-init --no-http`. Tag isolation confirmed: only `test_genuine_independent_transaction_binding_race` runs (post_install, `-standard`, `-at_install`).

**Result: 4/4 runs FAIL deterministically** at `assertTrue(obs['worker_done'])` — *"worker did not finish within the bounded join timeout"* — after ~180s of bounded-timeout exhaustion. This is **not** an intermittent failure hidden behind later passes; it is deterministic and reported as such.

Root cause (proven, not inferred):

- Worker B blocks and never completes; its transaction surfaces `ERROR: could not serialize access due to concurrent update` on `UPDATE shopify_connector_job … WHERE id=<job>` only at process shutdown (Odoo cursors run **REPEATABLE READ**). The job nonetheless reaches the **correct terminal state every run** — `blocked_manual_review` / `binding_conflict`, **exactly 1 surviving binding, 1 partner** — so the **Task 011B production matching/routing logic is correct**; only the harness's independent-transaction liveness fails.
- **Not the drain cron:** `ir.cron` id 3 *"Shopify Connector: Job Dispatch Drain"* (5-min, background `dev=reload` server) was temporarily disabled (`active=false`) and the failure persisted identically.
- **Not the registry-change signal:** re-running **without `-u`** (no *"Registry changed, signaling"* emitted) still failed identically.
- **Not the database:** a standalone two-connection `psycopg2` **positive control** proved this DB fully supports the race — independent connections get **distinct backends** (A_pid≠B_pid), `pg_blocking_pids(B)` correctly attributes the block to **A**, and B unblocks with `UniqueViolation` the instant A commits (2.0s).
- **Environment topology:** the odoo test process's DB backends are **invisible in `pg_stat_activity`** to any external monitor (both psql and psycopg2 — 0 non-webshell backends observed across a 95s live monitor), while my own connections are fully visible. The Odoo.sh dev DB fronts odoo's connections behind a pooler/namespace domain, so the harness's in-process `pg_blocking_pids`/`pg_stat_activity` lock-attribution across mutually-visible independent backends **cannot function**, and B never observes its release within the bounded window.

**Classification: environment limitation.** The harness is explicitly *"authored to run under an explicit tag on a runtime host"* — a dedicated test DB with direct, mutually-visible backends. This shared/pooled Odoo.sh dev build is not that host. **No harness logic defect and no Task 011B production defect is implied** (positive DB-semantics control + correct final state). Per LOOP 9 the harness was **not modified** (no proven in-scope defect; modifying it to tolerate the pooled topology would be scope creep and could weaken the accepted genuine-race guarantees). **LOOP 5 three-clean-runs cannot be satisfied here; the concurrency gate remains OPEN for a dedicated runtime host**, consistent with the standing SRR-03/04/09 concurrency caveat the test docstring already restates.

### 18.7 100,000-partner benchmark — PASS (LOOP 6)

Invocation: `… --test-tags shopify_connector_customer_matching_benchmark`; **exit 0, `0 failed, 0 error(s)`**; ran 86.35s. (Being a single-transaction `TransactionCase`, it did **not** serialization-fail — confirming §18.6 is specific to the multi-connection machinery.)

**Exact corpus (in-Python counters == marker-scoped DB cross-check, both asserted):** total **100000**, active **70000**, archived **30000**, shared **1500**, wrapped **10500**, ordinary **88000**, non-null normalized **100000**.

**Exact 1,000-probe mix (asserted):** active-hit **700**, archived-hit **150**, miss **100**, ambiguous **50**.

**Measurements (emitted, not asserted):** corpus generation **80.897s**; 1,000-probe total **0.445s** → avg **0.445 ms**, throughput **2249.09 cust/s**; latency **p50 0.328 ms / p95 0.934 ms / max 1.296 ms**; in-test recompute backfill proxy **4.44s** (`status=measured`); `backfill_authoritative=PENDING`. Budgets (p95 ≤ 50 ms, ≥ 20 cust/s, backfill ≤ 600 s) are emitted only and are all met with wide margin — no SLA is asserted or invented.

### 18.8 Backfill / module-upgrade measurement (LOOP 7) — proxy + genuine single-DB `-u`; authoritative isolated-build GATE OPEN

Three distinct, clearly-separated tiers:

1. **In-test ORM recompute proxy:** **4.44s** (§18.7) — least authoritative (`modified()` + `flush_all()` + materialize).
2. **Genuine single-DB module-upgrade backfill (real `-u`):** on the persistent 100k corpus the `shopify_connector_email_normalized` column (+ its index) was dropped, then `odoo-bin -u shopify_connector_sale` was run. Odoo's actual module lifecycle **recreated the column, recreated the btree index, and backfilled all 100,000 rows** (verified: `column_exists=1`, `index_exists=1`, `corpus_non_null_normalized=100000`, `corpus_null_normalized=0`, sample value correct). Sale-module load **4.93s / 1231 q** vs a no-backfill baseline **0.12s / 122 q** → **isolated backfill cost ≈ 4.81s** for column + index + 100k-row backfill. This **cross-validates** the recompute proxy (4.44s). It is a real `-u` backfill (not the proxy, not manufactured), but the source tree during the `-u` is HEAD with the column manually dropped, not a separate build at the base commit.
3. **Fully-authoritative isolated base→head build upgrade: NOT PERFORMED — platform limitation.** The preferred method (a disposable build whose starting *code* is base `9128015`, advanced to head `9895919`, then `-u`) requires a second isolated Odoo.sh build/DB. This container is **linked to a single database and cannot create another** (AGENTS.md), and build provisioning is user/control-room-triggered, not agent-triggered. **This authoritative gate remains OPEN**, to be closed by the control room on a provisioned isolated build. Tier 2 is **not** claimed as a substitute; the requirement is not weakened or renamed.

### 18.9 Warning inventory (LOOP 10)

| Phase | WARNING lines |
| --- | --- |
| Fresh build install | **0** |
| `-u shopify_connector_core` rerun | **1** — `odoo.schema: Missing not-null constraint on res.users.notification_type` (issue-157 schema-reconciliation, base `res.users`, out of scope) |
| `-u shopify_connector_product` rerun | **0** |
| `-u shopify_connector_sale` rerun (incl. final re-verify) | **0** |
| 100k benchmark | **0** |

### 18.10 SQL ERROR-level inventory (LOOP 10)

All SQL `odoo.sql_db: bad query` ERROR lines are traced to a specific passing negative test or to issue-157:

- **Expected negative-constraint SQL (passing `assertRaises`):** `shopify_connector_customer_binding` NOT-NULL (partner_id, shopify_gid, store_id) + UNIQUE (`store_partner_uniq`, `store_shopify_gid_uniq`) — from `test_binding_uniqueness_constraint_backstop` / binding-constraint tests; `shopify_connector_product_*_binding` NOT-NULL — product negative tests. Present in fresh install, sale rerun (5), product rerun (6), and inside the core rerun (11).
- **Issue-157 (unexpected, known artifact):** 6× `null value in column "notification_type" of relation "res_users" violates not-null constraint`, only under `-u shopify_connector_core` (§18.11).
- **Environment-limited concurrency (§18.6):** `could not serialize access due to concurrent update` + `current transaction is aborted` on the synthetic job / job_log at shutdown — job state metadata only, **no customer PII / token / GraphQL body** (leak audit §18.12).

No SQL error is called "expected" without a passing negative test behind it.

### 18.11 Issue #157 classification (separate, NOT fixed)

The `-u shopify_connector_core` rerun produced **6 errors of 264** — all `setUpClass` failures with the identical root cause `psycopg2.errors.NotNullViolation: null value in column "notification_type" of relation "res_users"`, in six **core** test classes: `TestConnectionLifecycle`, `TestCredentialAccess`, `TestCredentialService`, `TestJobLogSystemAppend`, `TestReadinessSlotClosure`, `TestTestConnection`. Each calls `cls._create_group_user()` → `res.users.create({…})` without `notification_type`; on the `-u` schema-reconciliation the base `res.users` NOT-NULL column default is not applied (traceback preserved: `res_users.py:1357 → 580 → models.py:4711/4887`). This is **issue #157** — a base-Odoo `res.users` artifact in **core** test fixtures, exposed only by the core update lifecycle. It is **exclusive to `-u shopify_connector_core`** (product, sale, benchmark reruns had **0** notification_type errors — Task 011B is fully orthogonal). Classified as the **known issue-157 artifact**; **not fixed** (out of Task 011B scope; LOOP 9 forbids touching core). A green fresh install (§18.2, no #157) and this post-init `-u core` #157 artifact are recorded as **two distinct facts**.

### 18.12 Cleanup + leak audit (LOOP 11) — CLEAN

Environment controls applied and reverted: `ir.cron` id 3 was temporarily disabled during the concurrency/benchmark runs and **restored** (`active=true`, nextcall reset forward); the persistent 100k corpus was created and **deleted** (`VACUUM ANALYZE res_partner`). Post-run synthetic-residue sweep — **all zero**: corpus partners, benchmark partners, race partners/stores, customer bindings (0 total), `customer_import_sync` jobs, idle-in-transaction backends. Final DB size 164 MB.

Leak audit across all run logs: **0** Shopify tokens / auth headers / bearer (excluding the intentional in-test sentinel), **0** email-like strings (no customer PII, synthetic or real), **0** GraphQL bodies (the 3 "graphql" hits are test-method names). The only raw SQL in any log is job/job_log state-transition metadata (4 INSERT + 4 UPDATE), carrying no PII/credentials — consistent with the harness's type-only sanitized-diagnostic design.

### 18.13 Runtime corrections & gates

- **Runtime defects found in Task 011B production/test code: NONE.** No code changed this session (LOOP 9 no-op). No correction commit.
- **Concurrency gate: OPEN** — requires a dedicated runtime host (§18.6).
- **Authoritative isolated base→head build backfill: OPEN** — requires a control-room-provisioned second build (§18.8 tier 3).
- **Live Shopify validation: OPEN** — depends on CORE-R2 (no live request made).
- **SRR-03: OPEN.** Full CORE-R2 completion **not** claimed.
- **PR #150: open, draft, unmerged** — not marked ready, not merged.

## 19. Concurrency-harness correction — Registry._lock post_install deadlock (2026-07-13, review `4687443143`)

**This section corrects §18.6.** The prior "environment/pooler limitation"
classification was **wrong**; the genuine independent-transaction concurrency
test now passes **3/3 stable** in the working tree after a **test-only** fix.
No Task 011B production/model code changed.

### 19.1 Correct diagnosis (phase-evidence proven)

Control-room review `4687443143` identified the true cause as the **framework
defect already confirmed in CORE-R2 §4.2**: Odoo's `ThreadedServer.run()` holds
the reentrant `Registry._lock` across the **entire** preload/post_install phase
(`service/server.py`), so a **spawned** worker thread's
`api.Environment(cr_w, …)` → `Registry(cr.dbname)` → `Registry.__new__` →
`with cls._lock:` blocks forever on a lock the main thread owns and a different
thread can never acquire. The single-threaded parent transactions avoid this
(they build their Environment on the main thread, reentrantly).

Bounded, **sanitized** phase instrumentation (phase identifiers + exception
class names only — never SQL/email/payload/token/exc text) was added to the
worker and run **without** the fix. The observed trail:

```
['worker_thread_entered', 'cursor_opened', 'backend_pid_obtained',
 'before_api_environment']          last = before_api_environment
```

`after_api_environment` was **never reached** → the worker deadlocked inside
`api.Environment`, **never reached the SQL binding race**, and therefore never
issued the binding `INSERT`. This is why §18.6's external monitor saw no active
query: **there was no query to observe** — not a pooler hiding it. The
`pg_blocking_pids` evidence was absent because the race never started, exactly
as review `4687443143` warned not to mis-read.

### 19.2 Test-only correction (CORE-R2 §4.2 pattern, adapted)

Applied to `TestCustomerMatchingConcurrency.test_genuine_independent_transaction_binding_race`
only: for the **bounded worker window**, decouple the framework lock with a
fresh `threading.RLock()` —
`type(self.registry)._lock = threading.RLock()` before the worker starts,
**restored** in `finally` after the worker has terminated and closed its own
cursor. The registry is fully built and only **read** here (a cached
`registries[db]` lookup, never a rebuild), so this preserves real mutual
exclusion — the same decoupling Odoo's own `_registry_test_mode_patches`
performs. Adapted (not copied) to this **one-worker** test: **unlike** CORE-R2
it does **not** patch `registry.cursor` / use a shared `TestCursor` — every
connection stays an unchanged, real, independent `db_connect(dbname).cursor()`.

Explicitly **preserved / not weakened**: real independent PostgreSQL
connections; `pg_blocking_pids(B) ∋ A` attribution; the server-side
`INSERT INTO`-binding-table regex predicate; the real dispatcher; the
`unknown_system_error → retry_waiting` (`retry_count==1`, `next_retry_at`,
attempt+retry logs) first-collision route; the `binding_conflict →
blocked_manual_review` clean-retry route; the exactly-one-binding /
one-partner invariants; bounded joins; durable cleanup that re-raises + a
fresh-connection zero-residue verification; and no daemonization masking of an
alive worker (`worker_alive_final` still asserted false). New assertions added:
the worker must reach `after_api_environment` and `before_dispatch`, and A/B
must use **distinct backend PIDs**.

### 19.3 Working-tree results — 3/3 stable (correction evidence only)

`--test-tags shopify_connector_customer_matching_concurrency`, three clean runs
(fresh per-run uuid marker each), drain cron id 3 disabled for the window and
**restored** afterwards:

| Run | result | post-test | phase tail | distinct PIDs (A/B) | blocked_by_A | binding-INSERT | wait cleared | first collision | clean retry | bindings/partners | cleanup |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `0 failed, 0 of 1` | 0.23 s | `worker_done` | ✓ 3129486/3129488 | ✓ | ✓ | ✓ | retry_waiting / unknown_system_error / rc=1 | blocked_manual_review / binding_conflict | 1 / 1 (survivor `gid_a`) | all 0 |
| 2 | `0 failed, 0 of 1` | 0.22 s | `worker_done` | ✓ 3130226/3130235 | ✓ | ✓ | ✓ | same | same | 1 / 1 | all 0 |
| 3 | `0 failed, 0 of 1` | 0.16 s | `worker_done` | ✓ 3130515/3130518 | ✓ | ✓ | ✓ | same | same | 1 / 1 | all 0 |

Every run reached the full phase trail (`worker_thread_entered … after_api_environment …
before_dispatch … after_commit … worker_done`). Post-test time collapsed from
**~180 s (deadlock)** to **~0.2 s**. Sanitized phase/race evidence emitted with
the `[TASK-011B-CONCURRENCY]` prefix; leak audit of the new logs = 0 emails, 0
tokens (booleans + integer PIDs only).

### 19.4 Regression + scope

- Full `shopify_connector_sale` standard suite: **`0 failed, 0 error(s) of 80`**
  (90 stats), all **32** `TestCustomerMatchingScalability` methods, 0 WARNING,
  opt-in classes correctly excluded — the fix did not disturb the standard pass.
- `py_compile` / `compileall` **CLEAN**; **0** conflict markers.
- Changed files this session: **only**
  `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py`
  (+ this doc). Production `models/**` **byte-unchanged**. The 100k benchmark was
  **not** re-run (unchanged; §18.7/§18.8 evidence stands for the prior code SHA).

### 19.5 Status after the correction

- **Standard-suite + benchmark + EXPLAIN + backfill evidence from build
  `34844515` (§18) remains accepted for the prior code SHA
  `9895919…`** — unchanged by this test-only fix.
- **Exact-head rebuild is MANDATORY before final concurrency acceptance:** these
  3/3 results are working-tree correction evidence; final closure requires a new
  Odoo.sh build whose checked-out HEAD is the committed correction SHA.
- **Fully-authoritative isolated base→head backfill gate: still OPEN** (single
  linked DB).
- **Issue #157** (`res_users.notification_type`): **still separate**, not fixed.
- **SRR-03: OPEN. Live Shopify: blocked** (no live request). **PR #150: open,
  draft, unmerged** — not marked ready, not merged.
