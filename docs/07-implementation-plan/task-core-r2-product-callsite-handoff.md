# CORE-R2 Slice 2B — Product Call-Site Migration: Session Handoff

**Session type:** one narrow product-domain implementation session (CORE-R2
Slice 2B, Prompt P). **Model:** Opus 4.8. **Author:** Claude
(execution/implementation); review/gating: ChatGPT (`CLAUDE.md` §2).

**Revision 2 (control-room review `4695667571`, REVISE) — test/evidence
correction only.** The production migration is unchanged (frozen). Added the
genuine independent-`db_connect`-connection lifecycle class
`TestProductCallSiteLifecycleGenuine` (M1/M2 committed-lease visibility; Race
A/M8 in both orderings via the real `action_disconnect`/`_admit` protocol; Race
B/M18 on the terminal page with the real `_run_disconnect_quiesce` controller),
and **reclassified** the same-transaction generation-bump between-pages test as
**M9/M10** (no-second-call / generation mismatch) — it is no longer described as
Race A. The genuine tests are authored + compile but are **not executed** in
this GitHub session (no PostgreSQL/Odoo) and are not claimed green. No
core/sale/live change; Prompt E blocked; SRR-03 OPEN.

**Revision 3 (control-room review `4696396464`, REVISE) — product test/evidence
correction only.** The production importer stays **byte-for-byte frozen**. Five
targeted fixes to `TestProductCallSiteLifecycleGenuine`, all inside the same
three allowed files:
1. **Runtime tag** — imported `tagged` and decorated the class
   `@tagged('post_install', '-at_install', '-standard',
   'shopify_connector_product_callsite_lifecycle')` so it is excluded from the
   standard CI suite and runs only on its explicit tag. The exact tag is echoed
   in the validation doc (§7.3, §8), this handoff, the PR body, and the runtime
   command.
2. **Zero-residue master-data cleanup** — a successful genuine import commits
   real `product.template`/`product.product` (and, for the M1/M2 structured
   fixture, a per-test `product.attribute` + values). `_cleanup` now captures
   those ids by **exact id from the store's own template bindings**, unlinks in
   FK-safe ORM order (variant bindings → template bindings → templates → orphan
   values → orphan attributes, each attribute/value removed only when no line
   still references it), then deletes the connector rows; `_assert_zero_residue`
   verifies zero rows for every connector table **and** every captured
   master-data id. No pre-existing record is touched (unique markers + exact-id
   deletion, never a name search).
3. **Cleanup-first, fail-loud teardown** — the threaded tests no longer call
   `_assert_workers_dead()` before cleanup. A single `_finalize_threaded` in
   `finally` sets every resume gate, bounded-joins the workers, records
   liveness, runs durable cleanup + zero-residue **only when all workers have
   stopped**, and otherwise skips destructive cleanup (a live worker may hold
   locks), preserves sanitized findings, and fails loudly — so no assertion can
   skip cleanup and no stuck worker can deadlock or false-pass.
4. **Race-specific token proofs** — the admission-first (`blocking_send`) and
   M18 (`ok_send`) fakes now record their `_send` `token` argument; each test
   asserts exactly one transport carrying the pre-disconnect `DUMMY_TOKEN`.
   M1/M2 additionally commits its worker transaction so the committed
   reconciliation (three bindings) is observed cross-connection and the
   master-data cleanup path is genuinely exercised.
5. **Classification unchanged** — the between-pages generation-bump test stays
   **M9/M10** (not Race A).

Still authored-only: the genuine lifecycle tests **compile** (`py_compile`,
`compileall`) but are **not executed** here (no PostgreSQL/Odoo) and are not
claimed green. No core/sale/live change; Prompt E blocked; SRR-03 OPEN.

## Session summary

Migrated the Task 010B product importer from the legacy value-returning
api-client `execute()` to the CORE-R2 `execute_business()` admission-lease
context manager (AR-047, RD-P). The pagination loop in `import_product_sync`
now **owns** every per-page `execute_business` context; the terminal page's
reconciliation (normalize → `_apply_import` → `flush_all` → return) runs
**inside** its own lease; the value-returning `_execute_query` and
`_fetch_product_with_all_variant_pages` helpers are **dissolved**. This is a
transport/lease-boundary change only — no product matching, variant, pricing,
attribute, media, binding, or refresh behaviour is redesigned.

## Branch and commits

- **Branch:** `claude/core-r2-product-callsite`
- **Starting head:** `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79` (identical to the
  `claude/core-r2-slice-2b-integration` head).
- **Product domain source:** PR #151 head
  `e4669aaf206fe8436a6d8a524b083f48d56ac9df` (an ancestor of the base).
- **Post-Slice-2A base:** `a3fd6cdfcb6f3654ae81a48a7f4e694994d4762b` (ancestor).
- **Commits (focused):** (1) product call-site migration; (2) focused product
  tests; (3) product validation + handoff docs; (4) Revision-2 genuine lifecycle
  race tests; (5) Revision-2 evidence reclassification; (6) Revision-3 test tag +
  master-data zero-residue + cleanup-first teardown + token proofs (review
  `4696396464`).
- **Final head:** the pushed tip of `claude/core-r2-product-callsite` (recorded
  in the draft PR).
- **Draft PR:** head `claude/core-r2-product-callsite` → base
  `claude/core-r2-slice-2b-integration` (draft; not merged).

## Files created or updated

Production (1): `addons/shopify_connector_product/models/shopify_connector_product_importer.py`.
Tests (4): `test_product_import_matching.py`, `test_product_refresh_and_stale.py`,
`test_product_runtime_performance.py`, `test_product_variant_generation.py`
(all under `addons/shopify_connector_product/tests/`).
Docs (2): `docs/05-qa/task-core-r2-product-callsite-validation.md`,
`docs/07-implementation-plan/task-core-r2-product-callsite-handoff.md`.
No core, sale, manifest, XML, security, CSV, or `adams_base` file changed.

## What changed

1. **`import_product_sync`** rewritten to own a `while True` pagination loop
   whose body is a `with client.execute_business(job, store,
   PRODUCT_IMPORT_QUERY, variables={id, cursor}) as result:` block. Each page's
   validation/accumulation runs inside that block via `_consume_variant_page`;
   the terminal page runs `_normalize_payload` + `_apply_import` + `flush_all` +
   `return` inside the block; the `absent` (null-product page-one) path runs
   `_handle_absent_product` + `flush_all` + `return` inside the block; a
   non-terminal page falls out of the block (lease released) and the loop
   re-admits. `except ShopifyClientError → JobHandlerError` wraps the `with`;
   `ShopifyQuiescedError` propagates uncaught.
2. **`_consume_variant_page(result, gid, state)`** — new helper containing the
   Task 010B page guards verbatim (cursor strict-advance/no-repeat, product-id
   identity, updatedAt torn-read, zero-node forward-progress, per-variant-GID
   dedup, `MAX_ACCUMULATED_VARIANTS`), returning `'absent' | 'terminal' |
   'continue'`. In-memory accumulation only; **no** Odoo business write.
3. **`_execute_query` and `_fetch_product_with_all_variant_pages` removed.** No
   production caller reaches `api.client.execute(`; no helper returns an
   `execute_business` result to an outer reconciler.
4. **Tests:** a `TestProductCallSiteExecuteBusiness` registry-test-mode
   activation class (static/public-call guards, one/multi-page lease lifecycle,
   failure paths, and the **M9/M10** next-admission-refusal), a **new**
   `TestProductCallSiteLifecycleGenuine` class using genuine independent
   `db_connect` connections for **M1/M2**, **Race A/M8** (both orderings), and
   **Race B/M18** with the real `action_disconnect`/`_admit`/`_run_disconnect_quiesce`
   protocol (only `_send` replaced; `_apply_import` observe/pause spy;
   `@tagged(..., '-standard', 'shopify_connector_product_callsite_lifecycle')`
   opt-in exclusion; race-specific `_send`-`token` assertions; bounded timeouts +
   cleanup-first/fail-loud teardown + by-exact-id master-data + connector
   zero-residue), plus adaptation of the transport-driving Task 010B tests to the
   real gate + `_send` seam (credential seeded while `setup_incomplete`, store
   connected, real job threaded, `registry_enter_test_mode()`). The genuine class
   is authored + compiles; it is executed only under the Odoo runtime (pending),
   never here.

Old vs new call-site shapes, lease coverage, exception handling, authored tests,
and static results are detailed in
`docs/05-qa/task-core-r2-product-callsite-validation.md` (§3–§8).

## Evidence and citations added

- Validation record §8 (static results) — `py_compile`/`compileall` pass,
  conflict-marker scan clean, changed-file inventory, AST proof (no `.execute(`,
  `execute_business` with `job`, `flush_all` + `return` inside the terminal
  `with`, no `cr.commit`), secret/URL scan clean.
- All claims labelled per `CLAUDE.md` §8.

## Assumptions

- The `claude/core-r2-slice-2b-integration` base already carries Slice 2A
  (merged PR #160 capability: generation bump, disconnect controller,
  `ShopifyQuiescedError → skipped` routing) and the PR #151 product code —
  verified by ancestry of `e4669aa` and `a3fd6cd` under `4f2cd7e`.
- `registry_enter_test_mode()` + a credential seeded while `setup_incomplete`
  (generation 0) reproduces the sanctioned admission-test harness used by the
  core `TestBusinessAdmission` / `TestApiClient` classes.

## Adversarial findings

A multi-lens adversarial pass covered the packet §9 checklist (result escape,
terminal reconciliation boundary, non-terminal write, double lease, job
thread-through, `ShopifyQuiescedError` remap, cursor-state carry, final-page
double-fetch, pagination-guard weakening, media redesign, main-cursor commit,
product drift, core/customer contamination) and the test correctness of the new
seam.

Nine independent reviewers (one per §9 lens) plus per-finding refutation
verification ran over the diff. **Eight lenses returned no findings** —
confirming: no API result escapes its context; the terminal reconciliation +
`flush_all` + `return` sit inside the terminal lease; non-terminal pages perform
no business write; at most one lease is held at a time and `job` is threaded to
every page admission; `ShopifyQuiescedError` is never remapped and the `except`
is narrow (`ShopifyClientError` only); every pagination guard is preserved
verbatim with no final-page double-fetch or cursor-state loss; no main-cursor
commit and no media redesign; and only `shopify_connector_product` files changed
(public `execute()` untouched).

**AF-P1 [Confirmed → Fixed] (test-correctness).** The migrated regression guard
`test_variant_single_page_not_blocked` drove `import_product_sync(self.store,
'gid://shopify/Product/982')` **without a `job`** — its multi-line call with a
literal GID was missed by the `job=`-insertion sweep that covered the
`(self.store, gid)` call form. Under the real admission gate this would raise an
uncaught `ShopifyQuiescedError` ("a business Shopify call requires a valid job")
before any transport, so the happy-path guard would error spuriously.
**Resolution:** the call now passes `job=self._import_job(gid)`. A follow-up
programmatic sweep confirms **every** `import_product_sync` call across all four
changed test files reaches a `job=` — no other instance of this class exists.
No production defect was found.

**Revision-2 self-review (genuine lifecycle tests).** The
`TestProductCallSiteLifecycleGenuine` class was authored against the accepted
core `TestGenuineRealAdmission`/`_DisconnectHelpers` harness and reasoned
through path-by-path: (a) the `_apply_import` observe/delegate spy uses the
proven `real = type(X).method; real(self, …)` pattern already used by the core
`counting_release` test; (b) the mid-reconcile controller's store `FOR UPDATE`
is uncontended because the terminal `_admit` already released `FOR SHARE` and
the paused reconciliation holds only the committed **lease** row, not the store
row; (c) the disconnect's queued-job sweep never conflicts with the worker
(the worker only reads the job; empty notes → no `_emit_notes` write); (d) all
waits are bounded and threads are joined + asserted dead before cleanup; (e)
cleanup deletes bindings before jobs (FK order) and the zero-residue verifier
covers leases/store/credential/job/both binding tables. **These tests are not
executed here** (no PostgreSQL/registry), so any residual Odoo-runtime-only
behaviour (attribute-lock seeding, exact MVCC visibility timing) is a
runtime-execution obligation, not a green claim.

**Revision-3 self-review (review `4696396464`).** Path-by-path over the five
fixes: (a) the `@tagged` decorator carries `-standard` (source-scanned), so CI
never picks the class up implicitly; (b) `_cleanup` captures master-data ids
**before** unlinking any binding and deletes strictly by exact id, unlinking
bindings→templates→orphan-values→orphan-attributes (each value/attribute gated
on "no attribute line still references it"), so a value shared with a
pre-existing product can never be removed and no name search is used — the
importer maps the Shopify option name straight to `product.attribute.name`, and
the M1/M2 per-test `SC2B-<uuid>` marker guarantees the attribute is created
fresh (never a reused pre-existing one) and is unambiguously test-owned; (c)
`_finalize_threaded` runs in `finally` and cannot be short-circuited by a body
assertion — cleanup + zero-residue run only once every worker is joined-dead,
and a still-alive worker fails loud **without** destructive cleanup (no delete
against a lock it may hold, no hang: `_open_bounded`'s statement/lock timeouts
bound every cursor); (d) the admission-first and M18 fakes record the `_send`
`token` and assert exactly one transport with the pre-disconnect `DUMMY_TOKEN`,
and M1/M2 commits its worker so the committed master data is genuinely present
for the cleanup proof; (e) the between-pages test remains **M9/M10**. No
production defect surfaced; the importer stays byte-for-byte frozen. As with
Revision 2, these are **authored, not executed** — the exact MVCC/lock timing is
a runtime obligation, never described as green.

## Open questions

- **OQ-P1 [Open]** — Odoo runtime green on the integrated staging head (fresh
  install + full core/product/sale suites + CORE-R2 admission classes + the new
  activation tests + deployed multi-worker proof) is a later gate, not this
  session's to close. Runtime is **pending**; integrated staging is **not**
  runtime-green.
- **OQ-P2 [Open]** — `flush_all()` exactness against Odoo 19 (materialise-in-txn
  semantics) is confirmed by design here and by the AST placement proof; final
  confirmation is a runtime obligation of the validating session.

## Risks

- The migration widens the `except ShopifyClientError` to wrap the whole
  page `with` (previously only the transport call). Mitigation: the only
  `ShopifyClientError` source inside the block is `execute_business.__enter__`;
  `_consume_variant_page`/`_apply_import` raise `JobHandlerError`, never
  `ShopifyClientError`, so routing is unchanged (verified in the review).
- Registry test-mode is applied class-wide for the pure-transaction test classes
  but **only** inside the single `run_drain` test for the runtime-performance
  class, which also runs a genuine separate-connection concurrency test — so the
  concurrency test's independent cursors are untouched.

## Learning feedback loop

- **What worked:** carving the page validation into `_consume_variant_page`
  (returning a disposition, never the API result) kept every Task 010B guard
  verbatim while letting the loop own the lease — the single hardest constraint
  of RD-P.
- **Watch:** any future edit must keep the terminal `return`/`flush_all` inside
  the terminal `with`; the AST guard test
  (`test_source_guard_*`) and the runtime lease-lifecycle tests are the
  regression tripwires.

## What ChatGPT should review

1. RD-P conformance: loop owns each context; terminal reconciliation + flush +
   return inside the terminal lease; no result escapes its context (§4–§5 of the
   validation record).
2. Exception contract: `ShopifyQuiescedError` uncaught; `ShopifyClientError →
   JobHandlerError` preserved (§6).
3. Test fidelity: existing Task 010B assertions intact; the registry-test-mode
   activation tests prove the importer-level lease lifecycle and the **M9/M10**
   next-admission-refusal (the between-pages generation-bump test is M9/M10, not
   Race A); the genuine `db_connect` `TestProductCallSiteLifecycleGenuine` class
   proves **M1/M2**, **Race A/M8** (both orderings), and **Race B/M18** with the
   real `action_disconnect`/`_admit`/controller — authored, pending Odoo runtime
   execution (not claimed green).
4. Scope: only `shopify_connector_product` files changed; public `execute()`
   untouched (Prompt E remains blocked).

## Recommended next session

Customer call-site migration (Prompt C, `claude/core-r2-customer-callsite`) — an
independent, disjoint-file session — and then Prompt E (public-`execute()`
closure) only after **both** call sites are merged back into
`claude/core-r2-slice-2b-integration`.

## Stop confirmation

Session stops after pushing `claude/core-r2-product-callsite` and opening the
draft PR into `claude/core-r2-slice-2b-integration`. **No** merge, **no** Odoo
runtime run, **no** live Shopify request, **no** real token, **no** change to
PR #150/#151, **no** integration-branch edit, **no** Shopify-connector edit.

## Quality gate confirmation

- Scoped objective only (product call-site migration): **YES**
- Only allowed files changed: **YES**
- Claims cited/classified: **YES**
- Static checks pass (compile / AST / conflict / secret): **YES**
- Integrated runtime-green claimed: **NO** (correctly pending)
- Prompt E begun: **NO** (correctly blocked)
- SRR-03: **OPEN** (correctly not closed)

---

## Integrated-staging update (CORE-R2 Slice 2B integration session, 2026-07-14)

> **Session type:** controlled integration/validation only — no new design, no
> code authored. Merges three already control-room-accepted PRs onto
> `claude/core-r2-slice-2b-integration` and runs available static validation.
> **Prompt E BLOCKED. SRR-03 OPEN. No final `claude/core-r2-slice-2b-integration`
> → `Shopify-connector` PR opened. No Task 012 implementation begun. No live
> Shopify request.**

### Merge sequence and exact commits

1. **PR #159** (Task 012 order-import decision closure, docs-only, no gate) —
   marked ready, merge-commit into `Shopify-connector` (accepted head
   `d953272acbbef9318082d81158e242f0e5170d80`, control-room review
   `4697419280`).
   - **PR #159 merge commit:** `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`
   - **Shopify-connector head after PR #159:** `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b`
     (parents: prior tip `a3fd6cdfcb6f3654ae81a48a7f4e694994d4762b` +
     PR #159 head `d953272acbbef9318082d81158e242f0e5170d80`).
2. **Staging alignment** — merged the new `Shopify-connector` head into
   `claude/core-r2-slice-2b-integration` with a normal (non-fast-forward)
   merge commit; zero conflicts (exactly the five Task 012 Markdown files
   applied cleanly).
   - **Staging alignment merge commit:** `1a8d5adf31fb5194a16cff9e4344857c8d0139bb`
3. **PR #161** (CORE-R2 Slice 2B customer call-site migration) — marked ready,
   merge-commit into `claude/core-r2-slice-2b-integration` (accepted head
   `29b8dd12d406737b10e5834c657e5b214b8e1227`, control-room review
   `4697421328`, "ACCEPT FOR INTEGRATION-STAGING MERGE").
   - **PR #161 merge commit:** `78c7bd85039b9bc1daba0e3b70b6806ccade0cc4`
4. **PR #162** (CORE-R2 Slice 2B product call-site migration) — marked ready,
   merge-commit into `claude/core-r2-slice-2b-integration` (accepted head
   `cda4b6f04027a68dc58586412b1546465f25706d`, control-room review
   `4697422563`, "ACCEPT FOR INTEGRATION-STAGING MERGE").
   - **PR #162 merge commit:** `0c7b6f42bb111067455897f44146d66f9e62d4c2`

**Final exact `claude/core-r2-slice-2b-integration` SHA (before this handoff
commit):** `0c7b6f42bb111067455897f44146d66f9e62d4c2`.

Every merge was a plain `merge` (no squash, no rebase, no force-push). Each
merge commit's own diff was audited against its source PR's declared file
scope and found to introduce **no unrelated file**:
- PR #159 merge delta = exactly the 5 Task 012 Markdown files.
- Staging-alignment merge delta = the same 5 files (fast-forward-equivalent
  content).
- PR #161 merge delta = exactly its declared 5 files (customer importer +
  2 test files + 2 docs).
- PR #162 merge delta = exactly its declared 7 files (product importer +
  4 test files + 2 docs).

### Ancestry proof (`git merge-base --is-ancestor <sha> 0c7b6f42…`)

All six required ancestors verified present on the final staging head:

| Required ancestor | SHA | Result |
| --- | --- | --- |
| PR #159 accepted head | `d953272acbbef9318082d81158e242f0e5170d80` | ✅ ancestor |
| PR #161 accepted head | `29b8dd12d406737b10e5834c657e5b214b8e1227` | ✅ ancestor |
| PR #162 accepted head | `cda4b6f04027a68dc58586412b1546465f25706d` | ✅ ancestor |
| PR #150 accepted source | `10d0034e8e666684daa36f517788223976d74035` | ✅ ancestor |
| PR #151 accepted source | `e4669aaf206fe8436a6d8a524b083f48d56ac9df` | ✅ ancestor |
| Shopify-connector head after PR #159 | `dd6ecb8fe2d014989a86618035ef9bf1fe9f0b7b` | ✅ ancestor |

No conflict markers on the final head (`grep` scan for
`<<<<<<<`/`=======`/`>>>>>>>` clean). Working tree clean at every step.
`main` (`a5d45432a9b60f724c1aff700f4b371ea019960e`) and the repo's `staging`
branch were never touched; no plain `dev` branch exists in this repository.
No child PR (#161/#162) was merged directly into `Shopify-connector` — both
went only into `claude/core-r2-slice-2b-integration`. PR #150 and PR #151
remain open/draft/unmerged (re-verified after all merges).

### Static validation on the final staging SHA (`0c7b6f42…`)

All of the following ran directly against the checked-out final staging SHA:

- **Python compilation** — `py_compile` + `compileall` clean for
  `shopify_connector_core`, `shopify_connector_product`, `shopify_connector_sale`
  (every `.py` file compiles).
- **Manifest static inspection** — all three manifests load via
  `ast.literal_eval`; every `data`-listed file (security XML/CSV, cron XML,
  attribute-lock XML) resolves on disk.
- **XML parsing** — all 4 XML files parse (`xml.etree.ElementTree`), 0
  failures.
- **CSV / security-reference inspection** — all 3 `ir.model.access.csv`
  files parse with a `model_id:id` on every row.
- **Conflict-marker scan** — clean across the final staging tree.
- **Legacy-call search** — no bare `.execute(` call remains in
  `shopify_connector_customer_importer.py` or
  `shopify_connector_product_importer.py`; both call `execute_business`
  exclusively (5 and 6 occurrences respectively).
- **AST guards:**
  - Customer importer's single Shopify call site uses
    `client.execute_business(...)`, never legacy `execute()`.
  - Product importer's pagination loop issues `execute_business` on **every**
    page (the `while True` loop body); no `_execute_query`/
    `_fetch_product_with_all_variant_pages` helper remains.
  - The one production call site of `import_product_sync` (in
    `_handle_product_import_sync`) passes `job=job` explicitly; a full sweep
    of every `import_product_sync(` call site (production + all test files)
    found none missing `job=`.
  - The one production call site of `import_customer_sync` passes `job=job`
    explicitly.
  - `ShopifyQuiescedError` and `ShopifyClientError` are independent
    `Exception` subclasses (no inheritance relationship); both importers'
    `except ShopifyClientError` clauses cannot and do not catch
    `ShopifyQuiescedError` — it propagates uncaught in both call sites.
- **Runtime-tag audit** — all three genuine lifecycle test classes carry
  `-standard` alongside their custom tag:
  `TestCustomerCallsiteLeaseVisibilityGenuine`,
  `TestCustomerCallsiteRaceAGenuine`, `TestCustomerCallsiteRaceBGenuine`
  (`shopify_connector_customer_callsite_lifecycle`), and
  `TestProductCallSiteLifecycleGenuine`
  (`shopify_connector_product_callsite_lifecycle`) — none will run in the
  standard CI suite.
- **Forbidden-monkeypatch audit** — every `patch.object` target across both
  changed test files is one of `{_send, _apply_import, cursor, _lock}` (plus
  pre-existing, out-of-scope `execute`/`_fetch_image` patches in unrelated
  legacy/media tests); zero occurrences of
  `action_disconnect`/`_admit`/`_release_lease`/`_run_disconnect_quiesce`/
  `connection_generation` as a patch target.
- **Secret / live-URL scan** — no hardcoded API key/token/password pattern in
  any of the three connector addons; the only `myshopify.com`/`admin/api/`
  literal outside `tests/` is the parameterized URL-template line in
  `shopify_connector_api_client.py` (`'https://%s/admin/api/%s/graphql.json'
  % (...)`), not a live endpoint.
- **Full changed-file and ancestry audit** — see the merge-sequence and
  ancestry sections above; confirmed exact, no unrelated implementation
  change from any of the three merges performed this session.

No accepted production code was altered to satisfy a cosmetic static
preference; nothing was changed outside the three merge commits themselves.

### Integrated Odoo runtime validation — PENDING (no runtime available)

This session's environment has **no importable `odoo` module** (`import
odoo` → `ModuleNotFoundError`), **no `odoo-bin` on PATH**, and **no
responding PostgreSQL server** (`pg_isready` → "no response"; no `postgres`
process running). Per the session's own instructions, **no runtime-green is
claimed**, no child PR was revised on the basis of static speculation, and no
new test was invented. Integrated runtime validation is classified
**PENDING** and must be executed on an Odoo 19 runtime (Odoo.sh or an
equivalent host with PostgreSQL) against the exact final staging SHA above
(or the post-handoff SHA recorded at the top of this update, whichever the
runtime session checks out).

**Exact commands to run on that runtime**, all against staging SHA
`0c7b6f42bb111067455897f44146d66f9e62d4c2` (or its handoff-commit descendant):

```
# 1. Fresh install (all four modules)
odoo-bin -d <db> -i adams_base,shopify_connector_core,shopify_connector_product,shopify_connector_sale \
  --test-enable --stop-after-init --log-level=test

# 2. Customer call-site lifecycle (genuine M1/M2/Race-A/Race-B, opt-in tag)
odoo-bin -d <db> -u shopify_connector_sale --test-enable \
  --test-tags shopify_connector_customer_callsite_lifecycle \
  --stop-after-init --log-level=test

# 3. Product call-site lifecycle (genuine M1/M2/Race-A/Race-B, opt-in tag)
odoo-bin -d <db> -u shopify_connector_product --test-enable \
  --test-tags shopify_connector_product_callsite_lifecycle \
  --stop-after-init --log-level=test

# 4. Existing customer import and matching suites (standard suite)
odoo-bin -d <db> -u shopify_connector_sale --test-enable \
  --test-tags /shopify_connector_sale --stop-after-init --log-level=test

# 5. Existing product import, matching, variant-generation, refresh and
#    stale-data suites (standard suite)
odoo-bin -d <db> -u shopify_connector_product --test-enable \
  --test-tags /shopify_connector_product --stop-after-init --log-level=test

# 6. Relevant CORE-R2 admission, lease, disconnect and controller tests
odoo-bin -d <db> -u shopify_connector_core --test-enable \
  --test-tags /shopify_connector_core --stop-after-init --log-level=test
```

**Tests pending (all groups):**
1. `shopify_connector_customer_callsite_lifecycle` (M1/M2, Race A/M8 both
   orderings, Race B/M18 primary lease-count proof, lock-skip coverage).
2. `shopify_connector_product_callsite_lifecycle` (M1/M2, Race A/M8 both
   orderings, Race B/M18, M9/M10 between-pages).
3. Existing `shopify_connector_sale` customer import/matching/duplicate-
   prevention/fallback-partner/binding suites (Task 011/011B).
4. Existing `shopify_connector_product` product import/matching/duplicate-
   prevention/attribute/media/price/template-binding/variant-binding/
   variant-generation/refresh-and-stale/runtime-performance suites
   (Task 010/010B).
5. `shopify_connector_core` admission, lease, job-dispatch, disconnect-
   quiescence, readiness, connection-lifecycle and credential controller
   suites (CORE-R1/CORE-R2 Slice 2A).

No fix was made, because no failure was reproduced (no runtime execution
occurred). Nothing in this session touched a test's expected behavior.

### Gate status confirmation

- **Prompt E: BLOCKED** (unchanged — legacy public `execute()` closure not
  started).
- **SRR-03: OPEN** (unchanged — not closed by this session).
- **No final `claude/core-r2-slice-2b-integration` → `Shopify-connector`
  integration PR was opened** this session.
- **No Task 012 implementation begun** (PR #159 merge froze documentation
  only; no code/model/view/manifest file was created or touched).
- **No live Shopify request** was made at any point.
- **PR #150 and PR #151 remain open, draft, and unmerged** (re-verified
  after all merges completed).

## Runtime CORRECTION addendum (2026-07-14)

Runtime-validated on Odoo.sh build **34912503** from staging `63d10fb` (branch
`claude/core-r2-slice-2b-runtime-correction`). The product M18 concurrent-
disconnect serialization (finding #2) and the product cron-trigger residue
(finding #3) are closed: the M18 test drives the REAL scheduled `run_drain`,
proving the retry-then-refuse contract (one transport, zero binding,
`failed_retryable`, 40001 evidenced; fixture enables `product_domain_enabled`),
and the product genuine class now owns its connector-cron triggers via a per-test
baseline (independently-verified cron-trigger residue = 0, was +4/run). Production
fix is the common core dispatcher retry boundary
(`shopify_connector_job_dispatch.py`). **Product lifecycle tag `0 failed/0 error
of 4`, ×3; zero product/attribute + cron-trigger residue. No live Shopify request.
SRR-03 OPEN. Prompt E BLOCKED. Draft correction PR only — not merged. PR #150/#151
untouched.** See `../05-qa/task-core-r2-validation-results.md` §RTC and
`../05-qa/task-core-r2-product-callsite-validation.md` §12.
