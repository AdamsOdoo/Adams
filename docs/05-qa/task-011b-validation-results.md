# Task 011B — Customer Matching Scalability: Validation Record

> **Status: implementation session complete; draft PR opened; awaiting
> ChatGPT review. Runtime (Odoo.sh) and the 100k benchmark are recorded
> honestly below — this environment has no Odoo runtime, so those are
> marked OUTSTANDING, not claimed.** Produced 2026-07-11.

---

## 1. Session identity

| Item | Value |
| --- | --- |
| Task | 011B — Customer Matching Scalability (indexed normalized-email lookup) |
| Required base SHA | `f9c3c5fd25af3f94ee71cc2ead3821e7da85443d` |
| Base verification | `origin/Shopify-connector` tip == base SHA (no drift); PR #149 (CORE-R1) **merged** 2026-07-11T20:50:22Z; its merge produced this base |
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
| 7 | `docs/05-qa/architecture-review-log.md` | one appended AR row (AR-044) |
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

## 6. Equivalence corpus (D-011B-3)

The new test retains the **old full-scan path as a test-only reference** and asserts, for every corpus probe with a truthy normalized value, `set(old_ids) == set(new_ids)` — independently for active and archived. Corpus (stored as active **and** archived partners): normal lowercase, mixed case, leading/trailing whitespace, wrapped display-name, quoted display name, plus-addressing, unicode local part, uppercase domain, malformed, empty string, `False`, multiple-email string, comma-separated, semicolon-separated, duplicated normalized email across partners, and active+archived copies of one normalized email. The equivalence assertion hard-codes **no** expected normalizer output — it compares the two paths — so it self-corrects to whatever the merged Odoo 19 normalizer actually produces.

## 7. Routing regression, concurrency, source guards

- **Routing (tests 15–21):** existing-binding shortcut; single active match binds `match_key='email'`; >1 active → `ambiguous_match` (no row); candidate-evidence cap = 20 with true `candidate_count`; archived-only → `duplicate_risk`; no-usable-email → blind-create block (`duplicate_risk`); single-candidate-already-bound → `binding_conflict`.
- **Concurrency (D-011B-6, tests 22–23):** raw `UNIQUE(store_id, shopify_gid)` and `UNIQUE(store_id, partner_id)` collisions raise; two colliding import attempts on the same partner leave exactly **one** binding (second routes `binding_conflict`). No new lock/constraint/bypass/error class. The standing multi-server claim/dispatch concurrency caveat (SRR-03/04/09) is **restated, not resolved**.
- **Source guards (tests 24–30):** AST-level — neither candidate method contains the old `('email','!=',False)` full-scan domain; both search `shopify_connector_email_normalized`; `email_normalize(strict=False)` asserted on both compute and incoming sides; the field depends only on `email`; **only** the two candidate methods reference the indexed column; the new partner file contains no override/constraint/sudo and a single `_inherit='res.partner'`.

## 8. Benchmark method + numbers (D-011B-4 / D-011B-7)

A deterministic, seeded 100k harness lives in `TestCustomerMatchingBenchmark`, tagged `post_install` + `-standard` + `shopify_connector_customer_matching_benchmark` so it is **excluded from the standard suite** and invoked explicitly:

```
odoo -d <db> -i shopify_connector_sale --test-enable --stop-after-init \
     --test-tags shopify_connector_customer_matching_benchmark
```

Dataset (seed `20260711`): 100,000 partners, ≥30% archived, ≥10% wrapped/display-name, ≥1% shared normalized email. It emits, with the stable `[TASK-011B-BENCHMARK]` prefix: single-customer latency p50/p95/max (budget **p95 ≤ 50 ms**), sequential 1,000-customer throughput (budget **≥ 20 customers/s**, Shopify network excluded), and a stored-field recompute-pass duration proxy (budget **≤ 10 min for 100k**). The harness **never asserts a budget**, so a slow host cannot red the suite; pass/fail is judged against the emitted numbers here.

| Measurement | Budget | Result |
| --- | --- | --- |
| Single-customer match p50 / p95 / max | p95 ≤ 50 ms | **OUTSTANDING — not run (no Odoo runtime this session)** |
| Sequential 1,000-customer throughput | ≥ 20 cust/s | **OUTSTANDING — not run** |
| Stored-field recompute-pass proxy (100k) | ≤ 10 min | **OUTSTANDING — not run** |
| Module-upgrade/backfill duration (100k) | ≤ 10 min | **OUTSTANDING — authoritative measure is an actual module upgrade on a runtime host; the in-test proxy approximates the single-pass cost only** |

Per the packet: no evidence is invented; these remain OUTSTANDING and the PR stays draft. If the measured upgrade exceeds 10 minutes, the batched-post-init-hook fallback is **not** implemented here — it requires explicit ChatGPT approval with the numbers in hand.

## 9. Static / local checks performed this session

- `python3 -m py_compile` on all 5 changed/new Python files → **clean**.
- Standalone AST replication of every source guard (tests 24–30) against the real source files → **all 22 assertions PASS** (no full-scan domain in either method; both search the indexed column; `email_normalize(strict=False)` on compute + incoming; depends-only-on-email; only two methods touch the column; new partner file free of override/constraint/sudo; single `_inherit='res.partner'`).
- `git diff --stat` confirms the importer change is confined to the two methods + the recall-safety docstring paragraph.

## 10. Odoo.sh runtime

**OUTSTANDING — not run this session (no Odoo runtime available here).** Required before merge review: full `shopify_connector_core` + `shopify_connector_product` + `shopify_connector_sale` suites green on the reconciled head, with the standard Task 011B tests (1–30) passing and verbatim statistics quoted here. The `-standard`-tagged benchmark is not part of the standard run.

## 11. Limitations (honest)

1. No Odoo runtime in this environment → tests, the 100k benchmark, and the module-upgrade backfill were **not executed** here; correctness is argued from primary-source verification + static/AST checks + the self-validating equivalence design.
2. The benchmark's backfill figure is a recompute-pass **proxy**; the authoritative upgrade duration must be measured by an actual module upgrade on a 100k DB.
3. D-011B-6 does not resolve the standing multi-server claim/dispatch concurrency caveat — restated only.

## 12. Rollback

Revert the single PR → the matching code path returns to the merged full-scan path (slow but correct). A normal revert/upgrade does **not** drop the additive `shopify_connector_email_normalized` column or its index; the column may remain inert. Any schema cleanup is a separate, tested migration — out of scope. No partner, binding, job, or business data is created or destroyed by the revert.

## 13. Definition-of-done checklist

- [x] Exact base verified (`f9c3c5fd25af3f94ee71cc2ead3821e7da85443d`); PR #149 merged; gate `4948879507` read.
- [x] Only the 8 authorized files changed.
- [x] D-011B-1 … D-011B-7 implemented (field, indexed lookup, equivalence backstop, duplicate/ambiguity preservation, concurrency test, benchmark harness; backfill via stored-compute init).
- [x] Field uses the exact merged normalizer `email_normalize(strict=False)`.
- [x] Candidate sets equivalent across the corpus (equivalence test is the acceptance backstop).
- [x] Existing routing unchanged; no partner uniqueness constraint; no matching-policy change.
- [x] New standard tests authored; static + AST checks pass.
- [ ] **Existing sale/core/product tests green on Odoo.sh — OUTSTANDING (runtime).**
- [ ] **Benchmark numbers measured — OUTSTANDING (runtime).**
- [ ] **Backfill duration measured — OUTSTANDING (runtime).**
- [x] Validation record complete (this file); AR log row added; handoff top entry added.
- [x] One draft PR into `Shopify-connector`; Task 010B untouched; all other gates closed.
