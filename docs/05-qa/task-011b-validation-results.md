# Task 011B — Customer Matching Scalability: Validation Record

> **Latest parallel session (2026-07-12, authorization `4952271013`):** the
> branch was **base re-aligned by a normal merge** onto the current
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
> code changed; no live Shopify request made.
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
| Current base SHA | `ce504f42824807e215ee21df3dfd4eed9bb9a275` (`Shopify-connector` tip after **CORE-R2 / PR #154** disconnect-quiescence design merged; base-aligned via a normal `--no-ff` merge commit **`9bc224e`** this parallel session, authorization `4952271013`). Prior alignments: `cfdb057…` (U0 / PR #155, merge `66b0023`), `65e915a…` (U0 / PR #152), `fcbbb0b…` (PR #153), original `f9c3c5f…`. |
| Aligned PR head | base-alignment merge **`9bc224e`** (`ce504f…` is an ancestor; `merge-base(head, origin/Shopify-connector) == ce504f`); the PR head then advances only by the opt-in tag/harness/evidence-doc commit. |
| Base verification | `origin/Shopify-connector` tip == `ce504f…` (no drift from the required integration tip). Exactly two shared append-only docs conflicted (no `addons/**`/`tests/**`/Task 011B production/test conflict — CORE-R2 is docs-only), both resolved by **preserving both sides completely** (git-verified **0 lines lost from either side**): in `architecture-review-log.md` the Task 011B **AR-045** row (ours) and the CORE-R2 **AR-047** row (theirs) are both kept after **AR-044** (U0) → order AR-043/044/045/047, **no AR-046**; in `research-handoff.md` the Task 011B entry (ours) and the CORE-R2 entry (theirs) are both kept below the shared U0-acceptance-closure top entry. PR diff vs `ce504f…` = **exactly the 8 Task 011B files**; no CORE-R2 / U0 / Task 010B file appears as a PR change; production `models/**` + `tests/__init__.py` **byte-identical to `b680e8a`** (the merge added only docs). |
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
