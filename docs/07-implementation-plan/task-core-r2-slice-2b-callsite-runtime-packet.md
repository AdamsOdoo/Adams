# Task CORE-R2 — Foundation Slice 2B: Call-Site Activation & Runtime Packet

> **Status: Proposed packet for ChatGPT review. THE CODE GATE IS NOT OPEN.**
> This is a documentation-only session. It writes no code, changes no existing
> file, opens no implementation gate, modifies no PR, and closes no risk.
> **SRR-03 remains OPEN.** No live Shopify validation is performed or authorized
> here.

**Model:** Opus 4.8.
**Author role:** Claude (execution/research/documentation). Control-room review
and gating: ChatGPT (see `CLAUDE.md` §2, §5).
**Date prepared:** 2026-07-14.
**Architecture of record:** AR-047 (`docs/03-architecture/disconnect-quiescence-remediation-analysis.md`, Rev 4).
**Merged predecessor:** PR #156 — CORE-R2 Foundation Slice 1 (merged into
`Shopify-connector`).

This is the first of three Slice-2B packet files:

1. **`docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`** (this file)
   — state verification, exact call-site inventory, the required change design,
   the cross-branch integration strategy, and the two future implementation
   prompts (P and C).
2. `docs/05-qa/task-core-r2-slice-2b-validation-plan.md` — the regression/runtime
   test matrix, the deployed multi-worker/multi-server validation plan, and the
   SRR-03 closure criteria.
3. `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` — the session
   handoff, open questions, adversarial self-review, and the exact next-session
   prompt.

**Claim labelling (`CLAUDE.md` §8).** Every load-bearing statement below is
tagged **[Fact — current code]**, **[Fact — merged design]**, **[CORE-R2
requirement]**, **[Recommendation]**, or **[Open question]**. Line anchors are
given against a named SHA because the two integration targets (PR #150, PR #151)
carry *different* code than the `Shopify-connector` base.

---

## 0. What Slice 2B is (and is not)

**[Fact — merged design]** Neither the merged analysis
(`disconnect-quiescence-remediation-analysis.md`) nor the merged packet
(`task-core-r2-disconnect-quiescence-packet.md`) uses the words "Slice 2A" or
"Slice 2B". The analysis is organized by numbered sections (§1–§26) and
invariants (INV-1…INV-9); the CORE-R2 validation record
(`task-core-r2-validation-results.md` §5) records a single lumped **"Intentionally
deferred (Slice 2/3)"** bucket. **[Fact — current tasking]** The Slice-1 / 2A /
2B decomposition exists only in the control-room tasking (PR #156 is titled
"CORE-R2 Foundation Slice 1"; the current session brief names "Slice 2A … under
development in another branch" and "Slice 2B").

**[Recommendation]** This packet formalizes the decomposition as follows, carving
the merged §5 "Slice 2/3" deferral bucket into two slices. ChatGPT ratifies the
naming.

| Slice | Scope | Status |
| --- | --- | --- |
| **Slice 1** (PR #156, merged) | Committed `shopify.connector.call.lease` model + ACL; `execute_business` context manager + `_admit`/`_release_lease`; `_send(store, body, token)` single-snapshot; `store.connection_generation`; `job.expected_connection_generation` capture at enqueue. **Dormant** — no production call site uses `execute_business`. | Done, runtime-green (build 34818964 @ `c0d4559`). |
| **Slice 2A** (parallel branch, unmerged) | The disconnect *consumer/lifecycle* half: `disconnecting` state; two-phase `action_disconnect`; the store-row update-lock + `connection_generation` **bump** on every generation-changing transition; the disconnect controller `_run_disconnect_quiesce` + its cron + `POLL_DELAY`; Direction-C `timed_out`/`completed` finalization + credential clear + lease cleanup; the dispatcher's `ShopifyQuiescedError → skipped` routing; `disconnecting` in the non-startable set. | **Not this packet.** Do not depend on or modify its files. |
| **Slice 2B** (this packet's target) | The two business call-site *producers*: migrate the **product** importer and the **customer** importer from the direct value-returning `execute()` call to `with execute_business(job, store, query, variables) as result:`, with reconciliation inside the lease and the `job` threaded through. | Planned here; gate CLOSED. |

**[Open question — OQ-1]** The store test-connection call
(`shopify_connector_store.py:134`, `action_test_connection`) and the *removal /
privatization of public `execute()`* are, in the merged plan
(`disconnect-quiescence-remediation-analysis.md` §9.1/§9.3;
`task-core-r2-disconnect-quiescence-packet.md` §4/§9), coupled to a separate
`execute_lifecycle(store, query, purpose=…)` entry point. That work is **not a
business call site** and is **out of Slice 2B scope**. ChatGPT decides whether
the `execute_lifecycle` migration and the public-`execute()` removal live in
Slice 2A, a Slice 2C, or a dedicated task. Slice 2B does **not** remove
`execute()` (both importers and `action_test_connection` still reach it), so the
SRR-03 closure item "no stale public `execute()` call" (§9 of the validation
plan) is satisfied by that separate work, not by Slice 2B alone.

---

## 1. State verification (this session, 2026-07-14)

All checks performed against the live repository and GitHub.

| Check | Expected | Observed | Verdict |
| --- | --- | --- | --- |
| `Shopify-connector` tip | `912801508155c6358e8f5f1a7a0aaf01ae573675` | `origin/Shopify-connector` = `9128015…` | ✅ |
| Working branch tip | == required base SHA | `claude/core-r2-slice-2b-packet-l0is3j` = `9128015…` | ✅ |
| PR #156 | merged | `state=closed, merged=true, merged_at=2026-07-13T10:44:49Z` into `Shopify-connector` @ base `ce504f…` | ✅ |
| PR #150 (Task 011B, customer) | open, draft, unmerged @ `10d0034…` | `state=open, draft=true, merged=false`, head `10d0034e8e666684daa36f517788223976d74035` | ✅ |
| PR #151 (Task 010B, product) | open, draft, unmerged @ `e4669aa…` | `state=open, draft=true, merged=false`, head `e4669aaf206fe8436a6d8a524b083f48d56ac9df` | ✅ |
| PR #150 runtime evidence retained | yes | `docs/05-qa/task-011b-validation-results.md` @ `10d0034` — build 34863138, DB `…-34863138`, validated concurrency SHA `662e980…` | ✅ |
| PR #151 runtime evidence retained | yes | `docs/05-qa/task-010b-validation-results.md` @ `e4669aa` — build 34828304, DB `…-34828304`, validated SHA `db534f8…` | ✅ |
| Working tree | clean | `nothing to commit, working tree clean` (before writing this packet) | ✅ |
| Issue #157 | open, separate `res.users.notification_type` fixture investigation | open; not part of CORE-R2; must not be mixed in | ✅ |

**[Fact]** The local `Shopify-connector` ref was stale at fetch time
(`21d59ec…`, PR #147); the authoritative remote tip is `912801508…` and equals
the working branch base. No action needed — this packet builds on the working
branch, which already carries the required base SHA.

**Naming note.** The session brief's "preferred branch" is
`claude/core-r2-slice-2b-packet`; the governance-designated development branch is
`claude/core-r2-slice-2b-packet-l0is3j` (suffix is the session identifier). This
session uses the **designated** branch (which it is already on and which carries
the exact base SHA). The docs-only draft PR is opened from that branch.

---

## 2. Merged foundation contract (the seam Slice 2B activates)

**[Fact — current code, `Shopify-connector` @ `912801`]**
`addons/shopify_connector_core/models/shopify_connector_api_client.py`:

- `execute(self, store, query, variables=None)` — line 135. The **legacy**
  read-only path. Reads the token once for a missing-credential pre-check, calls
  `_send(store, body)`, returns `_normalize_response(store, response)` (the dict
  `{'data', 'throttle_status', …}`). Still the **only live caller** across the
  merged tree. Raises `ShopifyClientError` (never `ShopifyQuiescedError`).
- `execute_business(self, job, store, query, variables=None)` — line 172, a
  `@contextmanager`. `__enter__` performs `_admit(job, store)` (line 267 — store-row
  `SELECT … FOR SHARE`, fresh `state`+`connection_generation` read, gate,
  single token read, committed lease `INSERT`+`COMMIT` on an **owned side
  cursor**), then `_send(store, body, token)`, then `_normalize_response`, then
  **`yield result`**. `__exit__` runs `_release_lease(lease_key)` (line 372 —
  side-cursor `DELETE`+`COMMIT`) on **both** normal and exception exit, with
  deterministic exception precedence (`raise primary from release_error`; bare
  `raise` preserves the original traceback). No value-returning form, no manual
  release. **Dormant** — no production call site enters it.
- `ShopifyQuiescedError` — line 90. Raised by `_admit` on a fail-closed refusal:
  store row gone; no valid `job`; job belongs to another store; store not
  `connected`; or `store.connection_generation != job.expected_connection_generation`.
  Carries no token/payload.
- `ShopifyClientError` — line 61. The accepted DEC-009 error taxonomy. Raised by
  `_admit` on a missing/empty credential (`ERROR_AUTH`, `credential_invalid=True`)
  **before** any lease insert, and by `_send`/`_normalize_response` on
  transport/GraphQL failure.
- `_send(self, store, body, token=None)` — line 402. The single HTTP seam
  (`requests.post` to the versioned GraphQL endpoint). `execute_business` passes
  the one admission-time token snapshot; legacy `execute()` passes `token=None`
  and `_send` reads it once.

**[Fact — current code, `912801`]** Dispatcher
`shopify_connector_job_dispatch.py`:

- `run_drain(limit)` (line 115) → `Job._claim_for_dispatch(limit)` (job.py line 319,
  non-blocking `try_lock_for_update`) → `_dispatch_one` (line 156) → `_start_running`
  (line 163) → `_invoke_handler` (line 207).
- `_invoke_handler` (line 207): **Checkpoint 3** re-reads store state
  (`store.invalidate_recordset()`; if `job.job_source in BUSINESS_JOB_SOURCES and
  store.state != 'connected'` → `job._transition_skipped(...)`); resolves the
  handler by `job_type` via `_get_handlers()` (line 231); calls `handler(job)`
  (line 242). A `JobHandlerError` → `_route_failure` (line 244/269 — DEC-009
  routing). **Any other `Exception` → `_route_failure(job, 'unknown_system_error',
  …)`** (line 248-252). On success → `job.write({'state': 'succeeded', …})`.
- **`ShopifyQuiescedError` is not specially routed here** (that routing is Slice
  2A). Under the current merged dispatcher, an uncaught `ShopifyQuiescedError`
  from a handler would be caught by the generic boundary at line 248 and become
  `unknown_system_error` → the safety-net single-attempt retry. See §5.4 and
  OQ-2.

**[Fact — current code, `912801`]** Handler seam. Each domain module registers
its handler via classic Odoo inheritance
(`_inherit = 'shopify.connector.job.dispatch'`, `_get_handlers()` append). The
handler receives the full `job` record — **so the `job` argument
`execute_business` needs is available at the handler level in both domains.**

**[Fact — current code, `912801`]** Generation/lease state is **inert** today:
`store.connection_generation` (store.py line 89, default 0) is *read* by admission
and *captured* at enqueue (`job.expected_connection_generation`, enqueue.py
line 51), but **no lifecycle transition bumps it** — `action_disconnect`
(store.py line 356) clears the credential and cancels jobs but neither bumps the
generation nor takes an admission-conflicting update lock. The generation-mismatch
gate therefore cannot fire until Slice 2A adds the bump. This is the core reason
Slice 2B alone does not close SRR-03 (§5.5, §9 of the validation plan).

---

## 3. Call-site inventory — A. Product import

Two versions matter, because the **integration target is the PR #151 head, not
the base** (see §7). Both are documented.

### 3.1 Production path on `Shopify-connector` base (`912801`) — the literal current code

File: `addons/shopify_connector_product/models/shopify_connector_product_importer.py`.

| Aspect | Fact (anchor @ `912801`) |
| --- | --- |
| Dispatcher handler | `ShopifyConnectorJobDispatchProductExtension._handle_product_import_sync(self, job)` — line 717. Registered via `_get_handlers()` (line 711). |
| Job argument availability | **The handler has `job`, but does NOT pass it on.** Line 727-729: `import_product_sync(job.store_id, job.shopify_target_gid)` — no `job`. |
| Importer entry method | `ShopifyConnectorProductImporter.import_product_sync(self, store, shopify_product_gid)` — line 198. **No `job` parameter.** |
| API-client call | Single `self.env['shopify.connector.api.client'].execute(store, PRODUCT_IMPORT_QUERY, variables={'id': shopify_product_gid})` — line 213. `variants(first: 100)`; **no pagination** (a `>100`-variant product is *blocked*, not paginated — `_validate_payload` raises `data_shape_schema_mismatch` on `variants_has_next_page`, line 300). |
| Normalization | `_normalize_payload(result)` — line 221→225 (GraphQL dict → internal payload dict). |
| Template reconciliation | `_apply_import` (line 323) → `_resolve_template_binding` (line 426): existing binding → SKU→barcode candidate search → confident-no-match create; ambiguous/blind → `JobHandlerError`. |
| Variant reconciliation | `_apply_import` loop (line 345-354) → `_resolve_deterministic_variant` (line 361) + `_resolve_variant_binding` (line 543). |
| Media reconciliation | Snapshot-only: `shopify_primary_image_url` written on the bindings. **No network media download** in the base. |
| Transaction / savepoint | Single `with self.env.cr.savepoint():` **inside** `_apply_import` (line 338), wrapping the entire template+variant write sequence. The `execute()` call at line 213 is **outside** the savepoint (it runs in `import_product_sync` before `_apply_import`). |
| Exception handling | `except ShopifyClientError as exc: raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc` — line 217-220 (preserves DEC-009 class). Reconciliation raises `JobHandlerError('data_shape_schema_mismatch'/'ambiguous_match'/'duplicate_risk', …)`. |
| Return value | `import_product_sync` returns `_apply_import(...)` → `{'template_binding', 'variant_bindings'}`. **The handler discards it** (returns `None`). |

### 3.2 Integration target — PR #151 head (`e4669aa`, Task 010B) — the version the migration actually edits

File (extracted at head): same path.

| Aspect | Fact (anchor @ `e4669aa`) |
| --- | --- |
| Dispatcher handler | `_handle_product_import_sync(self, job)` — line 2043. **Already threads `job`:** line 2050-2052 `import_product_sync(job.store_id, job.shopify_target_gid, job=job)`. |
| Job argument availability | **`job` is already a parameter** of `import_product_sync(self, store, shopify_product_gid, job=None)` — line 198 — used for informational notes only. |
| API-client call | **Multi-page.** `_fetch_product_with_all_variant_pages(store, gid)` (line 230) runs a `while True:` loop (line 289) issuing one `execute()` **per variant page** through `_execute_query` (line 409; `execute(...)` at line 413, `variables={'id': gid, 'cursor': cursor}`). A `≤100`-variant product = **one** call; a larger product = **N** calls with strict cursor/torn-read/identity/dedup guards. |
| Normalization | `_normalize_payload(product_node)` — line 427 (consumes the accumulated single node). |
| Template / variant reconciliation | `_apply_import(store, payload, job=None, requested_gid=None)` — line 625 → `_apply_within_savepoint` (line 772): `_resolve_template` → `_resolve_variants` → `_apply_template_media` → `_apply_prices` → `shopify_updated_at` stamp. |
| Media reconciliation | **Network downloads.** `_prepare_media` (line 1732) fetches primary + per-variant images over the network via `_fetch_image` (line 1850), **outside** the DB savepoint (inside `with ExitStack()`, line 665). A download failure raises `JobHandlerError('shopify_temporary_server_network', …)`. **These are tokenless CDN GETs to image URLs, not Admin-API business calls** (see §5.3, AF-3). |
| Transaction / savepoint | Nested savepoints: an `updatedAt` short-circuit / archived path each has its own savepoint; the main write runs in `with self.env.cr.savepoint():` at line 667 wrapping `_apply_within_savepoint`. The `execute()` page calls (line 413) run **outside** every savepoint. |
| Exception handling | `_execute_query` re-raises `ShopifyClientError → JobHandlerError` (line 417-420). Reconciliation raises `JobHandlerError('data_shape_schema_mismatch'/'mapping_missing'/'ambiguous_match'/'duplicate_risk'/'shopify_temporary_server_network', …)`. |
| Return value | Dict `{'template_binding', 'variant_bindings', …, 'notes'}`; handler discards it. |

**[Fact]** The merged analysis §9.3 names the product call site as
`shopify_connector_product_importer.py:213` — the **base** single-call anchor.
PR #151 rewrote that method: the single `execute()` at line 213 became the
per-page `_execute_query`/`execute()` loop at lines 289–413. **The merged
CORE-R2 product-migration spec (a "single structural wrap") is therefore stale
w.r.t. the integration target** (see §5.1, §7 drift analysis).

---

## 4. Call-site inventory — B. Customer import

### 4.1 Production path on `Shopify-connector` base (`912801`)

File: `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`.

| Aspect | Fact (anchor @ `912801`) |
| --- | --- |
| Dispatcher handler | `ShopifyConnectorJobDispatchCustomerExtension._handle_customer_import_sync(self, job)` — line 504. Registered via `_get_handlers()` (line 498). |
| Job argument availability | **Already threaded.** Line 519-521: `import_customer_sync(job.store_id, job.shopify_target_gid, job=job)`. |
| Importer entry method | `import_customer_sync(self, store, shopify_customer_gid, job=False)` — line 91. **`job` is already a parameter** (used for `_log_unresolved_address_code`). |
| API-client call | Single `execute(store, CUSTOMER_IMPORT_QUERY, variables={'id': shopify_customer_gid})` — line 113. **No pagination** — exactly one call. |
| Normalization | `_normalize_payload(result)` — line 121→124. |
| Customer resolution | `_apply_import(store, payload, job=job)` (line 122→184) → `_resolve_customer_binding` (line 202): existing binding → email normalize → active-candidate search → binding-conflict guard → archived-match check → confident-no-match create. |
| Partner creation/update | `_create_partner(shopify_gid, payload, job=job)` — line 372 (person-only; `defaultAddress` mapping; country/state lookup-only). |
| Binding reconciliation | `CustomerBinding.create({… match_key='email' …})` on a bind/create; existing binding writes snapshot. |
| Transaction / savepoint | Single `with self.env.cr.savepoint():` **inside** `_apply_import` (line 198) wrapping `_resolve_customer_binding`. The `execute()` call (line 113) is **outside** the savepoint. |
| Exception handling | `except ShopifyClientError as exc: raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc` — line 117-120. Reconciliation raises `JobHandlerError('duplicate_risk'/'ambiguous_match'/'binding_conflict'/'data_shape_schema_mismatch', …)`. |
| Return value | Returns the `shopify.connector.customer.binding` record; handler discards it. |

### 4.2 Integration target — PR #150 head (`10d0034`, Task 011B)

**[Fact]** The customer importer's call-site structure is **byte-for-byte the
same shape at the PR #150 head**: `import_customer_sync(self, store,
shopify_customer_gid, job=False)` at line 96; `execute()` at line 118;
`_apply_import(store, payload, job=job)` at line 127; savepoint at line 203;
handler threads `job` at line 526. PR #150's 59-line importer diff adds only the
stored/indexed `shopify_connector_email_normalized` lookup on `res.partner` and
uses it in candidate discovery — **it does not touch the entry method, the
`execute()` call, or the reconciliation boundary.** The customer migration is
therefore identical whether applied to the base or the PR #150 head.

---

## 5. Required Slice 2B change design

**[CORE-R2 requirement]** Each importer moves from a direct, value-returning
`execute()` call to:

```python
with api_client.execute_business(job, store, query, variables) as result:
    ...            # normalization that can fail
    ...            # complete local binding/business reconciliation
    ...            # final local flush, still inside the context
# context exits (lease released) only AFTER the reconciliation boundary
```

**[CORE-R2 requirement]** The lease **must** cover: the HTTP call; the
normalization that can fail; **all** local binding/business reconciliation; and a
**final local flush** that makes the reconciliation durable *within the handler
transaction* before the context exits. The context exits — releasing the lease —
only after the accepted reconciliation boundary. (Analysis §6 Phase B: "the
handler completes its local Odoo reconciliation … The lease is released **after**
reconciliation.")

**[CORE-R2 requirement]** Do **not** redesign matching, pricing, customer
resolution, duplicate prevention, media behavior, or bindings. Slice 2B changes
only the transport/lease boundary and the `job` thread-through.

### 5.1 Product — the multi-page complication and its resolution

**[Fact]** `execute_business` performs **exactly one** `_send` per context
(`__enter__` issues one HTTP call and `yield`s one result). The PR #151 product
importer fetches **N pages** with N `execute()` calls. A single `execute_business`
context therefore cannot, by itself, express "fetch all pages under one lease."

**[Fact — merged design]** The analysis anticipates exactly this. §6 **Phase C**:
"re-admit via `execute_business`; fail-closed if quiescing/stale. **At most the
one currently-admitted call per handler; zero further calls after the gate
observes the disconnect.**" The merged model is **one admitted call per
`execute_business` context, re-admitted per subsequent call** — not one lease
spanning many calls.

**[Recommendation — RD-P (product design)]** Migrate the product path as
**per-page `execute_business`, with the full reconciliation performed inside the
terminal page's context**:

1. Restructure `import_product_sync` / `_fetch_product_with_all_variant_pages` so
   each page fetch is a guarded call. `_execute_query(store, gid, cursor)` becomes
   `with self.env['shopify.connector.api.client'].execute_business(job, store,
   PRODUCT_IMPORT_QUERY, variables={'id': gid, 'cursor': cursor}) as result:` and
   the page's shape-validation / accumulation logic runs **inside** that `with`.
2. **Non-terminal page** (`hasNextPage == True`): validate + accumulate + capture
   `endCursor` **inside** the context, then exit (its lease releases). The
   between-pages gap holds no lease — which is **sound**: no reconciliation has
   started and nothing is written until the terminal page (see AF-1). The **next**
   page's `__enter__` re-admits (Phase C) and **fails closed** if a disconnect/
   generation-bump landed in the gap.
3. **Terminal page** (`hasNextPage == False`): inside that final context,
   accumulate the last page, then run `_normalize_payload(product_node)` and the
   **entire** `_apply_import(...)` reconciliation (including the tokenless media
   download and the DB savepoint), then a `self.env.flush_all()`, **before** the
   context exits. The terminal lease thus covers the whole reconciliation.
4. Thread `job` from the handler (already present at PR #151 head, §3.2) into
   every `execute_business(job, …)`.

**[Recommendation]** The common case (`≤100` variants → one page) collapses to a
single `execute_business` context wrapping the one call + normalize + apply +
flush — the exact "single structural wrap" the merged §9.3 assumed. The loop
restructuring only adds handling for the multi-page tail.

**[Open question — OQ-3]** RD-P holds **no** continuous lease between pages
(gap-quiescence-safe per AF-1) but is not the only option. An alternative
(**umbrella first-page lease + nested per-page contexts**) would keep at least
one lease continuously held from the first admission through reconciliation while
still re-admitting each page; it is more complex and holds up to two leases
transiently. RD-P is recommended (simpler, directly backed by §6 Phase C, and
strictly fail-closed). **ChatGPT ratifies RD-P vs the umbrella variant before
Prompt P executes**, because it materially shapes the pagination method and is
not a mechanical substitution. Both satisfy "reconciliation under a lease" and
"no unguarded call"; they differ only in continuous-lease coverage during the
inter-page gap.

**[CORE-R2 requirement]** Under RD-P, exactly for the product path:

- **Methods that receive the `job` argument:** `import_product_sync` (already
  has it @ `e4669aa`), `_fetch_product_with_all_variant_pages`, `_execute_query`
  (each must receive `job` to pass into `execute_business`). No other product
  method changes signature.
- **Dispatcher thread-through:** none needed — `_handle_product_import_sync`
  already passes `job=job` (line 2050).
- **Indentation region:** the page-fetch body inside `_fetch_…_pages` moves under
  the per-page `with`; the terminal-page branch additionally hosts the
  re-indented `_normalize_payload` + `_apply_import` + `flush_all()`.
- **Exceptions:** keep `except ShopifyClientError as exc: raise
  JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc`
  wrapping each `with` (because `__enter__` can raise `ShopifyClientError` from
  admission-credential/transport/normalize). Let `ShopifyQuiescedError`
  **propagate uncaught** (fail-closed; routed to `skipped` by Slice 2A — OQ-2).
  Reconciliation `JobHandlerError`s propagate through `__exit__` (lease released)
  unchanged.
- **Return semantics:** unchanged — the terminal context returns the
  `{'template_binding', 'variant_bindings', …}` dict; the handler still discards
  it.
- **Generation mismatch:** each page's `_admit` compares
  `store.connection_generation` vs `job.expected_connection_generation` under
  `FOR SHARE`; a mismatch raises `ShopifyQuiescedError` → fail closed, no page
  call, no partial write (reconciliation never begins).
- **Disconnecting:** if the store leaves `connected` between pages, the next
  `_admit` refuses (`ShopifyQuiescedError`); no further Shopify call is issued.
- **Lease release on success:** terminal `__exit__` after `flush_all()` deletes +
  commits the terminal lease; non-terminal pages release their own leases on exit.
- **Lease release on reconciliation exception:** a reconciliation failure inside
  the terminal `with` triggers `__exit__` → `_release_lease` (release-once), then
  the `JobHandlerError` propagates with its original traceback.

### 5.2 Customer — single structural wrap

**[Recommendation — RD-C (customer design)]** The customer path is a clean 1:1
structural wrap (single call, no pagination). Replace lines 117-127 of
`import_customer_sync`:

```python
# BEFORE (@ 10d0034, lines 117-127)
try:
    result = self.env['shopify.connector.api.client'].execute(
        store, CUSTOMER_IMPORT_QUERY,
        variables={'id': shopify_customer_gid},
    )
except ShopifyClientError as exc:
    raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc
payload = self._normalize_payload(result)
return self._apply_import(store, payload, job=job)
```

```python
# AFTER (Slice 2B target)
client = self.env['shopify.connector.api.client']
try:
    with client.execute_business(
        job, store, CUSTOMER_IMPORT_QUERY,
        variables={'id': shopify_customer_gid},
    ) as result:
        payload = self._normalize_payload(result)
        outcome = self._apply_import(store, payload, job=job)
        self.env.flush_all()   # durable reconciliation within the handler txn,
        return outcome         # before the context releases the lease
except ShopifyClientError as exc:
    raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc
```

**[CORE-R2 requirement]** Exactly for the customer path:

- **Methods that receive `job`:** `import_customer_sync` (already has it),
  `_apply_import` (already has it). No other signature change.
- **Dispatcher thread-through:** none — `_handle_customer_import_sync` already
  passes `job=job` (line 526).
- **Indentation region:** the `_normalize_payload` + `_apply_import` +
  `flush_all` + `return` region re-indents under the `with`. The `try/except
  ShopifyClientError` wraps the `with` (so an admission-credential/transport/
  normalize `ShopifyClientError` from `__enter__` is still mapped to the same
  `JobHandlerError`).
- **Exceptions:** `ShopifyClientError` → `JobHandlerError` (unchanged taxonomy);
  `ShopifyQuiescedError` propagates uncaught (fail closed → `skipped` via Slice
  2A); reconciliation `JobHandlerError` propagates through `__exit__`.
- **Return semantics:** unchanged — returns the customer binding record; handler
  discards it.
- **Generation mismatch / disconnecting / lease release (success and
  reconciliation exception):** identical to §5.1's per-page semantics, but for
  the single call.

### 5.3 What the lease covers vs what it does not

**[Fact / Recommendation]**

- **Covered by the lease:** the Admin-GraphQL business call (`_send`), the
  API-client normalization (`_normalize_response` in `__enter__`), the importer
  normalization (`_normalize_payload`), the entire binding/business reconciliation
  (`_apply_import` and everything it calls), and the final `flush_all()`.
- **Not admission-gated (by design, unchanged):** the product **media CDN
  downloads** (`_fetch_image`). They are tokenless GETs to image URLs, not
  credentialed Admin-API business calls; the quiescence contract governs the
  credentialed business call, not CDN reads (AF-3). Because RD-P runs
  `_apply_import` (which triggers `_prepare_media`) **inside** the terminal lease,
  the CDN downloads happen while a lease is held — acceptable and requiring no
  media redesign.

### 5.4 Exception-routing dependency on Slice 2A

**[Open question — OQ-2]** After migration, `execute_business.__enter__` can raise
`ShopifyQuiescedError` on a fail-closed admission. The **current merged
dispatcher does not route it to `skipped`** — the `ShopifyQuiescedError → skipped`
routing is a Slice 2A item (`task-core-r2-disconnect-quiescence-packet.md` §4,
`shopify_connector_job_dispatch.py`; analysis §18). If Slice 2B's call sites are
activated **before** that routing exists, an admission refusal becomes
`unknown_system_error` (generic boundary, `_invoke_handler` line 248) → one
safety-net retry → re-refusal or Checkpoint-3 skip. **Not catastrophic, but
wrong-tier.** **[Recommendation]** Slice 2A (or at minimum its
`ShopifyQuiescedError → skipped` routing) **must land before or with** Slice 2B.
This drives the merge-ordering constraint in §7.

### 5.5 Why Slice 2B alone cannot fire the generation gate

**[Fact]** Until Slice 2A adds the `connection_generation` bump on
disconnect/reconnect, `store.connection_generation` and
`job.expected_connection_generation` are both `0` for every job, so the
generation-mismatch branch of `_admit` never triggers. The "generation mismatch
fails closed" behavior is therefore **real code but dormant** after Slice 2B; it
becomes exercisable only once Slice 2A is present. The multi-worker proof (§8 of
the validation plan) and SRR-03 closure (§9) require the **integrated 2A+2B**
system.

---

## 6. Runtime-evidence requirements for any branch this migration touches

**[CORE-R2 requirement]** PR #150 and PR #151 each already carry
**authoritative exact-head runtime evidence** at a specific validated SHA:

- PR #151 (product): build **34828304**, DB
  `adamsmen-claude-product-import-completeness-010b-5l-34828304`, validated code
  SHA **`db534f8…`**, fresh install `0 failed, 0 error(s) of 433 tests`.
- PR #150 (customer): concurrency build **34863138**, DB
  `adamsmen-…-k5ux9b-34863138`, validated concurrency SHA **`662e980…`**, fresh
  install `0 failed, 0 error(s) of 357 tests`; benchmark build 34844515 @
  `9895919`.

**[CORE-R2 requirement]** Editing either branch **invalidates its current
exact-head evidence.** Any branch that receives the Slice 2B migration must
produce **new exact-head Odoo.sh runtime evidence** at the new head SHA (fresh
install green + the domain suite green + the CORE-R2 admission/lease classes
green + the Slice-2B activation tests of §7 of the validation plan) before that
branch can be considered re-validated. This is a hard input to the integration
strategy (§7).

---

## 7. Cross-branch integration strategy

**[Fact — the constraints]**

- PR #150 and PR #151 are **frozen behind CORE-R2 / SRR-03** (both draft,
  unmerged, by policy) and each already has authoritative exact-head runtime
  evidence at a specific SHA.
- Slice 2A may be under development in a **third** branch; Slice 2B must not
  depend on its unmerged code nor modify its files.
- Modifying PR #150 or PR #151 requires **fresh** exact-head runtime evidence (§6).
- **Integration-base drift is real:** the merged analysis §9.3 product-migration
  spec targets the **base** single-call site (`:213`); PR #151's head replaced it
  with a multi-page loop. The product migration must be re-derived against the PR
  #151 head (RD-P), not applied per the stale §9.3 single-wrap.
- The generation gate and the disconnect controller (Slice 2A) are required for
  any *meaningful* runtime proof of the activated call sites (§5.4, §5.5).

### 7.1 Options evaluated

**Option A — apply each migration directly onto its domain PR branch.**
Product migration onto PR #151 (`claude/product-import-completeness-010b-5l07ci`);
customer migration onto PR #150 (`claude/task-011b-customer-matching-k5ux9b`),
after Slice 2A merges.

- *Against:* Each domain PR grows a second, cross-cutting concern (its Task-010B/
  011B scope **plus** a CORE-R2 activation), muddying review and the "net diff =
  N Task-owned files" scope-integrity claims both PRs make. Requires **two**
  fresh exact-head runtime validations (one per branch). The product branch would
  need the CORE-R2 lease/`execute_business` code present to even run the
  activation — but that code lives on `Shopify-connector` (Slice 1, merged) and
  Slice 2A (unmerged); so PR #151 would have to be rebased onto a base that
  already contains Slice 2A, coupling the two PRs' merge order tightly and
  risking a shared-CORE-R2-commit double-apply if not rebased cleanly.

**Option B — merge the domain PRs first (when authorized), then do both call-site
edits in one dedicated CORE-R2 integration PR.**
When ChatGPT authorizes, merge PR #151 and PR #150 into `Shopify-connector`
(after/with Slice 2A), then branch a single `claude/core-r2-slice-2b-callsite`
PR off the updated `Shopify-connector` that performs **only** the two call-site
migrations.

- *For:* One review surface for the activation; the two domain PRs stay
  single-concern and keep their existing evidence intact through merge; **no
  cherry-pick and no shared CORE-R2 commit is applied twice** (the integration PR
  branches from a base that already contains Slice 1 + 2A + both domains); one
  fresh exact-head runtime validation covers both activations against the fully
  integrated tree (the only tree where the generation gate + controller exist and
  the proof is meaningful); clean, additive rollback (revert one small PR);
  deterministic base.
- *Against:* Requires the domain PRs to be merge-authorized first (a control-room
  gate); the activation lands slightly later than under Option A.

**Option C — cherry-pick / rebased hybrid.** Reject. Any approach that copies a
shared CORE-R2 activation commit onto two independent branches (or cherry-picks
between PR #150/#151 and an integration branch) risks **history duplication** and
**double application of a shared CORE-R2 commit**, which the constraints
explicitly warn against.

### 7.2 Recommendation

**[Recommendation — INTEG]** **Adopt Option B.** It is the only option that
simultaneously: keeps PR #150/#151 single-concern with their existing evidence
intact; avoids cherry-picking or double-applying any shared CORE-R2 commit;
produces exactly **one** fresh exact-head runtime validation against the only
tree where the proof is meaningful (Slice 1 + Slice 2A + both domains present);
gives a clean single-PR rollback; and sidesteps integration-base drift by
re-deriving the product migration (RD-P) against the already-merged PR #151 head
code rather than the stale analysis §9.3 spec.

Under Option B, **Prompt P and Prompt C may still be two independent sessions**
(product-only and customer-only) that each open their **own** small integration
PR off the updated `Shopify-connector` — they touch disjoint files
(`shopify_connector_product/**` vs `shopify_connector_sale/**`) and need not be
combined. Keeping them separate preserves reviewable, single-domain PRs and
independent rollback. They are combined into one PR **only if** a later analysis
proves separate branches unsafe (it does not today — the files are disjoint).

### 7.3 Deterministic sequence (no implementation or merge performed here)

1. **Slice 2A** completes, is runtime-green, and is **merge-authorized** by
   ChatGPT; merge Slice 2A into `Shopify-connector`. (Adds the generation bump,
   the disconnect controller, and the `ShopifyQuiescedError → skipped` routing —
   the prerequisites from §5.4/§5.5.)
2. ChatGPT authorizes merge of **PR #151** (product) and **PR #150** (customer)
   into the post-2A `Shopify-connector`. Each merges on its own existing evidence
   (no new call-site code yet). Expected base for each: `Shopify-connector` after
   step 1.
3. **Prompt P** session: branch `claude/core-r2-p-product-callsite` off the
   updated `Shopify-connector` (base = tip after step 2); apply RD-P
   (product-only); produce fresh exact-head Odoo.sh evidence; open a docs+code
   draft PR → `Shopify-connector`.
4. **Prompt C** session: branch `claude/core-r2-c-customer-callsite` off the same
   updated `Shopify-connector`; apply RD-C (customer-only); produce fresh
   exact-head Odoo.sh evidence; open a docs+code draft PR → `Shopify-connector`.
5. **Deployed multi-worker/multi-server proof** (validation plan §8) runs against
   the tree with both activations present; SRR-03 closure checklist (validation
   plan §9) is evaluated. Live Shopify validation remains separately gated.

**[Recommendation]** Steps 3 and 4 are order-independent (disjoint files). Neither
depends on the other's head. Both depend on steps 1–2. This sequence has **no
cherry-pick, no shared-commit double-apply, and a single well-defined base per
step** (`integration-base drift` is eliminated because every later step branches
from a single moving `Shopify-connector` tip, never from a sibling feature
branch).

---

## 8. Future implementation prompt P — product call-site migration only

> **GATED. Do not execute until ChatGPT opens the gate for THIS task.** Built
> from `docs/06-prompts/implementation-task-template.md`.

**Objective.** Migrate the **single** product-import business call site from the
value-returning `execute()` (per-page loop) to `with execute_business(job, store,
query, variables) as result:` per RD-P (§5.1), with reconciliation inside the
terminal page's lease and `job` threaded into the page fetch. **No product
matching, pricing, attribute, variant, media, or binding behavior may change.**

**Required starting branch/head.** A branch off `Shopify-connector` **after**
Slice 2A and PR #151 are merged (§7.3 step 3). Confirm the base tip and that
`shopify_connector_core` contains the Slice 1 + Slice 2A lease/controller code
and `execute_business` before starting. Do **not** start from PR #151's raw head
in isolation (the lease/controller code would be absent).

**Allowed files.**
- `addons/shopify_connector_product/models/shopify_connector_product_importer.py`
  — **call-site-only**: thread `job` into `_fetch_product_with_all_variant_pages`
  / `_execute_query`; wrap each page call in `with execute_business(job, store,
  PRODUCT_IMPORT_QUERY, variables={'id': gid, 'cursor': cursor}) as result:`; run
  `_normalize_payload` + `_apply_import` + `self.env.flush_all()` inside the
  terminal page's context; preserve the `ShopifyClientError → JobHandlerError`
  mapping around each `with`. No other logic changes.
- `addons/shopify_connector_product/tests/test_product_callsite_execute_business.py`
  — **new** test file for the Slice-2B activation tests (validation plan §7).
- `docs/05-qa/task-core-r2-slice-2b-validation-results.md` — **new** runtime
  evidence record (or a clearly-scoped product section of it).

**Forbidden files.** Every path not listed above. Specifically: any
`shopify_connector_core` file (the foundation is frozen — do not edit
`execute_business`, `_admit`, `_release_lease`, `_send`, the lease model, the
dispatcher, the store, or the job model); any `shopify_connector_sale` file (that
is Prompt C); `adams_base`; any other module; `.claude/**`; CI; `main`; plain
`dev`; migrations/manifests unless a new test file requires a one-line test
registration (allowed only in the product module's `tests/__init__.py`). No live
Shopify call, credential, or token in any test. No monkeypatch of the
lifecycle/state mechanism and no test-only timing hook — use the real
`execute_business` gate + the `_send` transport-injection seam.

**Acceptance criteria.**
1. The product handler path issues **every** Shopify Admin call through
   `execute_business` (per page); a static guard asserts no `api.client.execute(`
   remains reachable from the product importer.
2. A lease exists before each page `_send`; at least one lease is held
   continuously through the terminal-page reconciliation; the lease releases
   after successful reconciliation and after every failure exit.
3. Reconciliation (template/variant/attribute/price/media/binding writes) is
   byte-for-byte behaviorally unchanged vs PR #151 (all Task-010B tests still
   green).
4. A disconnect/generation-bump landing **between** pages fails the next page
   closed (`ShopifyQuiescedError`), issues no further Shopify call, and writes no
   partial product.
5. `ShopifyQuiescedError` routes to `skipped` (relies on Slice 2A); no
   `unknown_system_error` for an admission refusal.
6. No token/PII/GraphQL-body/media-byte leakage in logs or lease rows.

**Tests.** New activation tests (validation plan §7 matrix, product column):
lease-before-transport; lease-through-reconciliation; lease-release-on-success;
release-on-transport/normalization/business-record exception; disconnect-wins-
before-admission (per page); admission-wins-before-disconnect; no-second-call-
after-disconnect (page N+1 blocked); generation-mismatch-fails-closed; no
duplicate binding. **Re-run unchanged:** all PR #151 classes
(`TestProductTemplateBinding`, `TestProductVariantBinding`,
`TestProductImportMatching`, `TestProductDuplicatePrevention`,
`TestProductAttributeImport`, `TestProductVariantGeneration`,
`TestProductPriceImport`, `TestProductMediaImport`, `TestProductRefreshAndStale`,
`TestProductRuntimePerformance`) and the CORE-R2 admission classes
(`TestCallLeaseModelSchema`, `TestBusinessAdmission`, `TestApiClient`,
`TestJobEnqueue`, `TestGenuineRealAdmission`).

**Static guards.** Source-level assertions: no `.execute(` call reachable from
`shopify_connector_product_importer.py`; `execute_business` used only as a
context manager (no value-returning capture); every page call passes a real
`job`; no `cr.commit()` on the main cursor in the importer.

**Rollback.** Revert the single call-site PR; the product importer returns to its
PR #151 behavior (dormant foundation, `execute()`); no schema change, no data
migration. Ordered rollback only after zero lease holders (mirror
`task-core-r2-disconnect-quiescence-packet.md` §17).

**Definition of done.** Code + tests written; tests pass; only allowed files
changed; exact-head Odoo.sh evidence captured (fresh install + product suite +
CORE-R2 classes + new activation tests all green); `pr-review-checklist.md`
section C satisfied; self-review classified; handoff + validation record updated;
SRR-03 stays OPEN; draft PR, not merged without ChatGPT review.

**Final report requirements.** Base SHA + branch + PR number + final head;
exact files changed; the fresh exact-head build number, DB name, and validated
SHA; the activation-test results; confirmation no `shopify_connector_sale` or
`shopify_connector_core` file changed; confirmation SRR-03 OPEN and no gate
opened beyond this task.

---

## 9. Future implementation prompt C — customer call-site migration only

> **GATED. Do not execute until ChatGPT opens the gate for THIS task.**

**Objective.** Migrate the **single** customer-import business call site to `with
execute_business(job, store, query, variables) as result:` per RD-C (§5.2), with
reconciliation inside the lease. **No customer matching, email-normalization,
partner-creation, duplicate-prevention, or binding behavior may change.**

**Required starting branch/head.** A branch off `Shopify-connector` **after**
Slice 2A and PR #150 are merged (§7.3 step 4). Confirm the base contains the
Slice 1 + 2A foundation and `execute_business`.

**Allowed files.**
- `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`
  — **call-site-only**: replace the `execute()` call (lines 117-127 @ `10d0034`)
  with the RD-C structural wrap; preserve `ShopifyClientError → JobHandlerError`;
  keep `job` threaded (already present).
- `addons/shopify_connector_sale/tests/test_customer_callsite_execute_business.py`
  — **new** activation test file.
- `docs/05-qa/task-core-r2-slice-2b-validation-results.md` — **new/shared**
  runtime record (customer section).

**Forbidden files.** Every path not listed. Specifically any
`shopify_connector_core` file (foundation frozen), any
`shopify_connector_product` file (that is Prompt P), `adams_base`, other modules,
`.claude/**`, CI, `main`, plain `dev`. No live Shopify call/credential/token in
tests; no lifecycle monkeypatch; no test-only timing hook.

**Acceptance criteria.**
1. The customer handler issues its Shopify Admin call through `execute_business`;
   static guard asserts no reachable `api.client.execute(`.
2. Lease exists before `_send`, held through `_apply_import` reconciliation,
   released after success and after every failure exit.
3. Customer matching/creation/binding behavior byte-for-byte unchanged vs PR #150
   (all Task-011B tests green, including the concurrency + benchmark opt-in
   classes where run).
4. A disconnect/generation-bump before admission fails the call closed
   (`ShopifyQuiescedError` → `skipped`), no Shopify call issued, no partner/
   binding written.
5. No token/PII leakage in logs or lease rows (candidate-payload
   `technical_detail` remains within the accepted §8.2 shape — do not change it).

**Tests.** New activation tests (validation plan §7 matrix, customer column):
the same lease-lifecycle, disconnect-ordering, generation-mismatch, and
no-duplicate-binding proofs as Prompt P, for the single customer call.
**Re-run unchanged:** all PR #150 classes (`TestCustomerBinding`,
`TestCustomerImportMatching`, `TestCustomerDuplicatePrevention`,
`TestCustomerFallbackPartner`, `TestCustomerMatchingScalability`,
`TestCustomerMatchingBenchmark`, `TestCustomerMatchingConcurrency`) and the
CORE-R2 admission classes.

**Static guards.** No `.execute(` reachable from
`shopify_connector_customer_importer.py`; `execute_business` used only as a
context manager; the call passes a real `job`; no main-cursor `cr.commit()`.

**Rollback.** Revert the single call-site PR; the customer importer returns to
PR #150 behavior; no schema/data change. Zero-holder-first ordered rollback.

**Definition of done.** As Prompt P, for the customer domain; SRR-03 stays OPEN;
draft PR only.

**Final report requirements.** As Prompt P, for the customer domain.

**[Recommendation]** Keep Prompt P and Prompt C **independent** (disjoint files,
independent PRs, independent rollback). Do **not** combine product and customer
changes into one giant session — the integration analysis (§7) shows the two
branches are safe to separate (disjoint `shopify_connector_product/**` vs
`shopify_connector_sale/**` file sets; no shared edited file).

---

## 10. Claim classification summary

| Class | Items |
| --- | --- |
| **[Fact — current code]** | §2, §3, §4 call-site inventories with anchors; the base vs PR-head differences; the multi-page product loop; the customer single call; `job` thread-through status per domain/version. |
| **[Fact — merged design]** | The `execute_business`/`_admit`/lease contract (§2); analysis §6 Phase A/B/C; §9.3's stale base-anchored spec; direction-C. |
| **[CORE-R2 requirement]** | The lease-coverage/reconciliation-boundary/flush rules (§5); fresh-evidence-on-edit (§6); "no matching/pricing/media redesign". |
| **[Recommendation]** | Slice decomposition (§0); RD-P (§5.1); RD-C (§5.2); Option B integration (§7.2); the deterministic sequence (§7.3); Prompt P/C independence (§9). |
| **[Open question]** | OQ-1 (`execute_lifecycle`/`execute()` removal placement); OQ-2 (`ShopifyQuiescedError → skipped` is Slice 2A; 2A-before-2B ordering); OQ-3 (RD-P per-page vs umbrella lease). See handoff §Open questions. |

## 11. Adversarial self-review

The full adversarial pass is recorded in
`docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` (§ Adversarial
findings AF-1…AF-12). Summary: the design does not let the lease end before
reconciliation (terminal-page context holds it through `flush_all`); `job` is
threaded (already present at both PR heads); there is no hidden second Admin call
(media is a tokenless CDN GET); no matching/pricing/media redesign; no double
application of a shared CORE-R2 commit (Option B branches from one moving base);
no stale validated-SHA assumption (fresh evidence mandated on any edit); no
test-only proof passed off as deployed proof (validation plan §8 is a deployed
plan); no live-Shopify claim; no token/PII logging; no giant combined session;
and **no implementation gate is opened by this packet.**

## 12. References

- `docs/03-architecture/disconnect-quiescence-remediation-analysis.md` (AR-047,
  Rev 4): §3, §6 (Phase A/B/C), §8, §9.1, §9.2, §9.3, §10, §14, §16, §18, §19,
  §22, §24 (T-1…T-14, T-19), §26.
- `docs/07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`:
  §4 (allowed files), §5 (forbidden), §9 (frozen API contract), §12 (direction-C
  timeout), §17 (ordered rollback), §18/§19 (DoD / future-PR requirements).
- `docs/05-qa/task-core-r2-validation-results.md`: §4.1–§4.3, §5 (Slice 2/3
  deferrals), §9 (RR-C, RR-F), §11.
- PR #156 (merged, Slice 1); PR #151 (`e4669aa`, Task 010B); PR #150
  (`10d0034`, Task 011B); Issue #157.
- Companion Slice-2B files:
  `docs/05-qa/task-core-r2-slice-2b-validation-plan.md`;
  `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md`.
