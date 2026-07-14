# CORE-R2 Slice 2B — Product Call-Site Migration: Session Handoff

**Session type:** one narrow product-domain implementation session (CORE-R2
Slice 2B, Prompt P). **Model:** Opus 4.8. **Author:** Claude
(execution/implementation); review/gating: ChatGPT (`CLAUDE.md` §2).

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
- **Commits (three focused):** (1) product call-site migration; (2) focused
  product tests; (3) product validation + handoff docs.
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
4. **Tests:** a new `TestProductCallSiteExecuteBusiness` activation class, plus
   adaptation of the transport-driving Task 010B tests to the real gate + `_send`
   seam (credential seeded while `setup_incomplete`, store connected, real job
   threaded, `registry_enter_test_mode()`).

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
3. Test fidelity: existing Task 010B assertions intact; new activation tests
   prove the lease lifecycle, Race-A-per-page, and no-partial-write.
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
