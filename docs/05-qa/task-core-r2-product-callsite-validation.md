# Task CORE-R2 Slice 2B — Product Call-Site Migration: Validation Record

> **Scope: PRODUCT domain only.** This records the transport/lease-boundary
> migration of the Task 010B product importer from the legacy value-returning
> api-client `execute()` to the CORE-R2 `execute_business()` admission-lease
> context manager (AR-047, RD-P). It is a **transport-only** change: no product
> matching, variant, pricing, attribute, media, binding, or refresh behaviour is
> redesigned. **This is a normal GitHub session with no Odoo runtime; no
> integrated runtime-green is claimed here. Prompt E (public-`execute()` closure)
> remains blocked. SRR-03 remains OPEN.**

**Model:** Opus 4.8.
**Author role:** Claude (execution/implementation). Control-room review/gating:
ChatGPT (`CLAUDE.md` §2).
**Architecture of record:** AR-047
(`docs/03-architecture/disconnect-quiescence-remediation-analysis.md`).
**Packet:**
`docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`
(§5.1 RD-P, §5.3 lease coverage, §5.4 exception routing, §5.6 Race A/Race B,
§8 Prompt P). **Validation plan:**
`docs/05-qa/task-core-r2-slice-2b-validation-plan.md` (product M1–M18).

**Claim labelling (`CLAUDE.md` §8):** every load-bearing statement below is a
**[Fact — code]** (verifiable in the changed source/static output) or a
**[Recommendation]** / **[Open]** where noted.

---

## 1. State verification

| Check | Expected | Observed | Verdict |
| --- | --- | --- | --- |
| Working branch | `claude/core-r2-product-callsite` | `claude/core-r2-product-callsite` | ✅ |
| Required starting head | `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79` | identical (integration branch head) | ✅ |
| Integration branch head | `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79` | identical | ✅ |
| PR #160 (Slice 2A) | merged | merged into `Shopify-connector` | ✅ |
| PR #150 (customer) | open/draft/unmerged | open, draft, unmerged (`10d0034`) | ✅ |
| PR #151 (product) | open/draft/unmerged | open, draft, unmerged (`e4669aa`) | ✅ |
| PR #151 head ancestor of base | yes | `e4669aa…` is an ancestor of `4f2cd7e…` | ✅ |
| PR #150 head ancestor of base | yes | `10d0034…` is an ancestor of `4f2cd7e…` | ✅ |
| Post-Slice-2A base ancestor | yes | `a3fd6cd…` is an ancestor of `4f2cd7e…` | ✅ |
| Existing PR from this child branch → integration | none | none | ✅ |
| Working tree | clean at start | clean | ✅ |

**Starting head:** `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79`.
**Final head:** recorded in the draft PR (this branch's pushed tip after the
three Slice-2B commits below).
**Product domain source:** PR #151 head `e4669aaf206fe8436a6d8a524b083f48d56ac9df`.

---

## 2. Exact changed files

Production (1):
- `addons/shopify_connector_product/models/shopify_connector_product_importer.py`

Tests (4):
- `addons/shopify_connector_product/tests/test_product_import_matching.py`
- `addons/shopify_connector_product/tests/test_product_refresh_and_stale.py`
- `addons/shopify_connector_product/tests/test_product_runtime_performance.py`
- `addons/shopify_connector_product/tests/test_product_variant_generation.py`

Documentation (2):
- `docs/05-qa/task-core-r2-product-callsite-validation.md` (this file)
- `docs/07-implementation-plan/task-core-r2-product-callsite-handoff.md`

**[Fact — code]** No `shopify_connector_core`, `shopify_connector_sale`,
manifest, XML, security, CSV, or `adams_base` file changed (git changed-file
inventory vs the starting head confirms exactly the paths above).

---

## 3. Old call-site shape (removed)

**[Fact — code]** At the PR #151 head the product importer fetched all variant
pages through a value-returning helper, then reconciled the accumulated node
*outside* any transport boundary:

```
import_product_sync(store, gid, job)
  product_node = _fetch_product_with_all_variant_pages(store, gid)  # loop of execute()
       _execute_query(store, gid, cursor) -> api.client.execute(...) -> returns result
  payload  = _normalize_payload(product_node)     # AFTER the fetch returned
  _apply_import(store, payload, job, requested_gid=gid)   # reconciliation, outside transport
```

The value-returning `_execute_query` (and the loop that returned the accumulated
node) means an API response *escaped* the transport before the caller
reconciled — incompatible with the `execute_business` context manager, whose
lease must span reconciliation (RD-P §5.1).

Both helpers — `_execute_query` and `_fetch_product_with_all_variant_pages` —
are **dissolved** (removed). No production caller reaches `api.client.execute(`.

---

## 4. New loop-owned context shape

**[Fact — code]** `import_product_sync` now owns the pagination loop; each page
opens and closes its own `execute_business` context, and no API result escapes
its context:

```
import_product_sync(store, gid, job):
  client = env['shopify.connector.api.client']
  state = { cursor, product_node, accumulated_variants, seen_cursors,
            seen_variant_gids, first_updated_present, first_updated_at, page_count }
  while True:
    state.page_count += 1
    if page_count > MAX_VARIANT_PAGES: raise _schema_error(...)   # in-memory backstop, no lease
    try:
      with client.execute_business(job, store, PRODUCT_IMPORT_QUERY,
                                   variables={id: gid, cursor: state.cursor}) as result:
        disposition = _consume_variant_page(result, gid, state)  # all guards, in-memory only
        if disposition == 'absent':      # null product on page one (terminal)
          outcome = _handle_absent_product(store, gid, job)
          env.flush_all(); return outcome                        # inside the lease
        if disposition == 'terminal':
          state.product_node['variants'] = {'nodes': state.accumulated_variants}
          payload = _normalize_payload(state.product_node)
          outcome = _apply_import(store, payload, job=job, requested_gid=gid)
          env.flush_all(); return outcome                        # inside the lease
        # disposition == 'continue': non-terminal page -> with-block exits
        #   (this page's lease releases), next iteration re-admits.
    except ShopifyClientError as exc:
      raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc
```

`_consume_variant_page(result, gid, state)` contains the Task 010B page
validation/accumulation verbatim and returns `'absent' | 'terminal' |
'continue'`; it performs **no** Odoo business write (in-memory accumulation
only), so a non-terminal page leaves the DB untouched before its lease releases.

**[Fact — static]** AST scan of the importer: exactly one `execute_business`
`with`-block in `import_product_sync`; **all** `flush_all()` calls (2) and
**all** `return` statements (2) are nested inside that `with`-block; the first
positional argument to `execute_business` is the `job` name.

---

## 5. Lease coverage

**[Fact — code]** Per Shopify Admin variant page: **exactly one** committed
`shopify.connector.call.lease`, held from before that page's `_send` transport
through the page body, released on the page's `with`-exit.

- **Non-terminal page:** the lease covers the page call + validation +
  in-memory accumulation + next-cursor capture, then releases on `continue`
  (the with-block exits). Zero business writes.
- **Terminal page:** the same lease additionally covers `_normalize_payload`,
  the complete `_apply_import` reconciliation (template/variant matching,
  attribute reuse/locking, sparse variant generation, price/compare-at
  handling, the media preparation `_prepare_media` + its tokenless CDN GETs,
  and the `self.env.cr.savepoint()` write sequence), the final
  `self.env.flush_all()`, and the return-value construction — all before the
  context exits.
- **Absent page:** the lease covers `_handle_absent_product` (stale-marking /
  data-error decision) + `flush_all` + return.

**At most one lease at a time** (no umbrella/double lease). Admission and
release are owned entirely by the core `execute_business` context manager; the
importer never accesses the lease model, never creates or releases a lease, and
never issues an explicit `self.env.cr.commit()` — the later commit is the
natural dispatcher/RPC transaction boundary. `flush_all()` **materialises the
reconciliation SQL in the current main transaction** (it does not commit and
does not make the work visible to other transactions); its only role is to
guarantee the reconciliation SQL has executed before the lease releases.

Media CDN downloads are **not** converted into Shopify Admin API calls; they
remain tokenless `requests` GETs inside `_fetch_image`, unchanged, running
inside the terminal lease (packet AF-3).

---

## 6. Exception handling

**[Fact — code]**

- `ShopifyClientError` from `execute_business.__enter__` (admission-credential /
  transport / GraphQL normalization) → mapped to
  `JobHandlerError(error_class, reason, technical_detail) from exc` around the
  `with` — the accepted DEC-009 taxonomy and original-exception chaining are
  preserved.
- **`ShopifyQuiescedError` propagates uncaught** from the importer. The `except`
  clause is narrow (`except ShopifyClientError`), never `except Exception` and
  never a bare `except`, so a fail-closed admission refusal (store not
  connected, generation moved, missing/invalid job) is left for Slice 2A's
  dispatcher `skipped` routing.
- Reconciliation `JobHandlerError`s (`data_shape_schema_mismatch`,
  `mapping_missing`, `ambiguous_match`, `duplicate_risk`, `binding_conflict`,
  `shopify_temporary_server_network`) propagate through `__exit__` (lease
  released once) unchanged.
- No legacy `execute()` fallback exists; `job` is required and threaded into
  every page admission.

---

## 7. Authored tests

### 7.1 New activation class — `TestProductCallSiteExecuteBusiness`
(`test_product_import_matching.py`)

- **A. Static/public-call guards** — `test_source_guard_execute_business_only`
  (no reachable `.execute(`; `_execute_query` / `_fetch_product_with_all_variant_pages`
  dissolved; `execute_business(` used and admitted with `job`);
  `test_source_guard_no_manual_lease_or_commit` (no `call.lease`,
  `_release_lease`, `cr.commit(`; `flush_all()` present);
  `test_no_legacy_execute_fallback_at_runtime` (spies `execute`, proves it is
  never called while the import succeeds).
- **B. One-page product** —
  `test_single_page_one_lease_reconciles_flushes_releases` (exactly one lease at
  transport and through reconciliation, released after; one API call; binding
  created); `test_single_page_return_and_bindings_come_from_terminal_context`.
- **C. Multi-page product** —
  `test_multi_page_one_lease_per_page_terminal_reconciles` (N API calls for N
  pages; one lease at a time; **zero** product binding at every page's
  transport; reconciliation invoked once, at the terminal page; N variants
  imported); `test_multi_page_existing_cursor_and_dedup_guards_still_fire`.
- **D. Failure and lifecycle** —
  `test_transport_client_error_routes_and_releases_once`;
  `test_normalization_error_releases_once`;
  `test_reconciliation_error_releases_once`;
  `test_media_error_releases_once`;
  `test_quiesced_admission_propagates_uncaught_no_transport_no_write`
  (ShopifyQuiescedError uncaught, no transport, no lease, no write);
  `test_disconnect_between_pages_fails_next_admission_no_partial_write`
  (Race-A per page: a generation bump between pages fails the next admission
  closed — page 2 never transports, no partial product, no leaked lease).

### 7.2 Adapted existing Task 010B tests (item E — regression)

The transport-driving tests in `test_product_import_matching.py`,
`test_product_refresh_and_stale.py`, `test_product_runtime_performance.py`
(the `run_drain` feasibility test), and `test_product_variant_generation.py`
now drive the **real** `execute_business` gate + `_send` transport seam instead
of stubbing the legacy `execute()`: a credential is seeded (while
`setup_incomplete`, so generation stays 0), the store is connected, a real job
is threaded, and `registry_enter_test_mode()` lets the admission side cursor see
the fixture. Every existing Task 010B assertion is retained; no existing test
was weakened. The `_apply_import`-direct unit tests (attribute, duplicate,
media, price, template/variant binding, and the pure matching/normalization
cases) are unaffected — they exercise reconciliation directly and touch no
transport. The one test that formerly asserted on the dissolved
`_fetch_product_with_all_variant_pages` return value now drives
`import_product_sync` and asserts both accumulated variants imported.

---

## 8. Static results

**[Fact — static]** (this normal GitHub session; no Odoo runtime)

- `py_compile`: **pass** on the production importer and all four changed test
  files.
- `compileall` for `addons/shopify_connector_product/`: **pass**.
- Conflict-marker scan: **none** in the changed files.
- Changed-file inventory: exactly the 5 code/test files above (+ these 2 docs).
- AST/source scan of the importer: **no** production `.execute(` call;
  `execute_business` used with `job` as first arg; `flush_all()` (both sites)
  and `return` (both sites) inside the terminal `with`; **no** `cr.commit(`;
  **no** `call.lease` / `_release_lease` / `_admit` reference; the dissolved
  helpers are absent.
- Secret/URL scan of the diff: clean — the only token-shaped string is the
  clearly-marked non-secret `DUMMY_TOKEN` test constant; no live token, no
  `X-Shopify-Access-Token`, no `…/admin/api/…` URL introduced.
- No available non-Odoo pure test harness exists for this addon (Odoo is not
  importable in this environment); the tests are Odoo `TransactionCase`s and run
  under the Odoo test runner, not here.

**[Open] Runtime still pending.** Odoo runtime (fresh install + full
core/product/sale suites + CORE-R2 admission classes + these activation tests)
is **not** run in this session and is **not** claimed. The integrated staging
head is **not** runtime-green.

---

## 9. Adversarial review

A multi-lens adversarial pass covered the packet §9 checklist: API result
returned after context exit; terminal reconciliation outside the lease;
non-terminal page writing business records; two simultaneous leases; job omitted
on a later page; `ShopifyQuiescedError` incorrectly remapped; cursor state lost
between contexts; final page fetched twice; pagination guard weakened; media
behaviour redesigned; explicit main-cursor commit; product behaviour drift;
customer/core contamination. Findings and their resolution are recorded in the
handoff (`task-core-r2-product-callsite-handoff.md`, Adversarial findings).

---

## 10. Rollback

**[Fact]** Rollback is a normal revert of this child PR **before** integration:
reverting the three Slice-2B commits returns the product importer to its PR #151
behaviour (dormant foundation, legacy `execute()` loop). No schema change and no
data migration is introduced, so no down-migration is required. The inherited
Task 010B domain history is preserved (never rewritten). Ordered rollback of any
future live activation follows the packet §17 zero-holders rule.

---

## 11. Gate status / stop condition

- **[Fact]** Transport/lease-boundary migration only; Task 010B behaviour
  preserved.
- **[Open]** Integrated staging **not** runtime-green; runtime validation
  pending on the staging head after merge-back.
- **[Fact]** **Prompt E (public-`execute()` closure) remains blocked** — not
  begun here.
- **[Fact]** **SRR-03 remains OPEN.**
- **Stop condition:** this session ends after pushing the child branch and
  opening the draft PR into `claude/core-r2-slice-2b-integration`. No merge, no
  runtime run, no live Shopify request, no real token. Await ChatGPT review.
