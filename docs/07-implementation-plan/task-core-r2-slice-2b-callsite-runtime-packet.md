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
**Revision 2 (2026-07-14):** corrected per control-room review **`4690659767`
(REVISE)** — replaced the rejected direct-merge "Option B" with the
**integration-staging strategy** (§7); made **RD-P loop-owned** so no lease
releases before terminal reconciliation (§5.1); corrected **flush semantics**
(materialize-in-transaction, not commit/durable — §5); **resolved** the
public-`execute()` closure into Slice 2B (§6b, Prompt E); and rebased future
Prompts P/C/E on the staging branch (§8/§9/§9c). No code; no gate; SRR-03 OPEN.
**Architecture of record:** AR-047 (`docs/03-architecture/disconnect-quiescence-remediation-analysis.md`, Rev 4).
**Merged predecessor:** PR #156 — CORE-R2 Foundation Slice 1 (merged into
`Shopify-connector`).
**Hard prerequisite:** PR #160 — CORE-R2 Slice 2A (draft, unmerged, **no
runtime-green claimed**). Do not depend on its final code or SHA until it is
runtime-green and merged.

This is the first of three Slice-2B packet files:

1. **`docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`** (this file)
   — state verification, exact call-site inventory, the required change design,
   the integration-staging strategy, and the three future implementation prompts
   (P product, C customer, E public-`execute()` closure).
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
| **Slice 2A** (PR #160, draft, unmerged) | The disconnect *consumer/lifecycle* half: `disconnecting` state; two-phase `action_disconnect`; the store-row update-lock + `connection_generation` **bump** on every generation-changing transition; the disconnect controller `_run_disconnect_quiesce` + its cron + `POLL_DELAY` (1 min) + `DISCONNECT_QUIESCE_TIMEOUT` (15 min); Direction-C `timed_out`/`completed` finalization + credential clear + lease cleanup; `disconnecting` in the non-startable set; **`execute_lifecycle(purpose=…)`** as the new setup/diagnostic entry, with `action_test_connection` migrated onto it. **PR #160 removes neither the public `execute()`** — that is a Slice 2B integration-closure item (§6b). | **Not this packet.** PR #160 is draft, **no runtime-green claimed** (static validation only). **Do not depend on its final code or SHA until it is runtime-green and merged.** |
| **Slice 2B** (this packet's target) | The two business call-site *producers* **plus** the public-`execute()` closure: migrate the **product** importer and the **customer** importer from the direct value-returning `execute()` call to `with execute_business(job, store, query, variables) as result:` (reconciliation inside the lease, `job` threaded), and as a final integration-closure step (§6b) privatize/remove the public unguarded `execute()` so no production caller can bypass `execute_business`/`execute_lifecycle`. | Planned here; gate CLOSED. |

**[Resolved — was OQ-1; corrected per review `4690659767`]** The public
`execute()` removal/privatization is **owned by Slice 2B** as its final
integration-closure step (§6b), performed **after** both domain migrations, once
`execute_lifecycle` (delivered by Slice 2A / PR #160) is the setup/diagnostic
entry and `execute_business` is the sole business entry. Slice 2A migrates
`action_test_connection` onto `execute_lifecycle` but leaves the public
`execute()` present; Slice 2B's closure (Prompt E, §9c) privatizes the transport
seam and proves, via static guards, that no production caller reaches
`api.client.execute(...)`. The SRR-03 closure item "no stale public `execute()`
call" (validation plan §3 C5) is therefore satisfied **inside Slice 2B**, not
deferred indefinitely.

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
**final local flush** (`self.env.flush_all()`) that materializes the pending
reconciliation SQL **within the current main transaction** before the context
exits. The context exits — releasing the lease — only after the accepted
reconciliation boundary. (Analysis §6 Phase B: "the handler completes its local
Odoo reconciliation … The lease is released **after** reconciliation.")

**[CORE-R2 requirement — flush semantics, precise]** `self.env.flush_all()`
**sends pending ORM changes to PostgreSQL inside the current main transaction**.
It does **not** commit, and it does **not** make the reconciliation visible to any
other transaction. Its only role here is to guarantee the reconciliation SQL has
*executed* before the `execute_business` context exits (so the lease-release does
not precede the reconciliation write). The **later commit is performed by the
natural dispatcher/RPC transaction boundary** (Odoo commits the drain/handler
transaction after the handler returns). **No explicit main-cursor
`self.env.cr.commit()` is authorized** anywhere in either importer. The accepted
lease-through-reconciliation contract therefore ends **after the reconciliation
code and the flush — not after the outer transaction commit.** (See §5.3.)

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

**[Recommendation — RD-P (product design), corrected per review `4690659767`]**
Migrate the product path as **per-page `execute_business` in which the pagination
loop itself owns every `with` block**, with the full reconciliation performed
**inside the terminal page's own context**. The critical correction: a helper
that enters `execute_business` and `return`s `result` to its caller **cannot
work** — returning exits the context and releases the lease **before** the caller
reconciles. Therefore `_execute_query` (the old per-page helper) is **dissolved**;
the loop in `import_product_sync` / `_fetch_product_with_all_variant_pages` opens
and closes each page's context directly, and no API result ever escapes its own
context.

**Required structural pseudocode (the loop owns the context):**

```python
@api.model
def import_product_sync(self, store, shopify_product_gid, job=None):
    client = self.env['shopify.connector.api.client']
    gid = shopify_product_gid
    cursor = None
    # accumulation state (cursor, seen_cursors, seen_variant_gids,
    # first_updated_at, product_node, accumulated_variants, page_count) lives
    # in this method's locals — never crosses a context boundary as a return.
    while True:
        try:
            with client.execute_business(
                job, store, PRODUCT_IMPORT_QUERY,
                variables={'id': gid, 'cursor': cursor},
            ) as result:
                # ALL page work happens INSIDE this page's context:
                page = self._validate_and_extract_page(result, gid, ...)  # existing guards
                self._accumulate_page(page, ...)                          # existing dedup/torn-read
                if page['has_next_page']:
                    cursor = self._validated_next_cursor(page, ...)       # existing cursor guards
                    continue                                              # exit+release this lease,
                                                                          # loop re-admits next page
                # TERMINAL page — do the whole reconciliation before leaving:
                payload = self._normalize_payload(self._accumulated_product_node())
                outcome = self._apply_import(
                    store, payload, job=job, requested_gid=gid,
                )
                self.env.flush_all()
                return outcome
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class, exc.reason, exc.technical_detail,
            ) from exc
```

**[CORE-R2 requirement — explicit rules for RD-P]**

- **No API result may be returned from a helper and reconciled after its
  `execute_business` context has exited.** The `with` block is opened by the loop,
  and every use of `result` occurs inside that same block. `_execute_query` (which
  returned `result`) is removed.
- **Every page's response validation and accumulation occur before that page's
  lease releases** (inside its own `with`).
- **No business/Odoo reconciliation begins before the terminal page.** Non-terminal
  pages only validate + accumulate in memory + capture the next cursor, then
  `continue` (their lease releases; nothing is written).
- **Disconnect between pages causes the next admission to fail closed.** The next
  loop iteration's `execute_business.__enter__` re-admits (Phase C); a
  disconnect/generation-bump in the gap → `ShopifyQuiescedError` → no page call,
  no partial write (reconciliation never began).
- **The terminal page's lease covers, in order, all of:** final accumulation of
  the last page; `_normalize_payload`; the media preparation currently invoked by
  `_apply_import` (`_prepare_media`, tokenless CDN GETs — AF-3); the
  `self.env.cr.savepoint()` reconciliation inside `_apply_import`; the final
  `self.env.flush_all()`; and the return-value construction — all **before** the
  context exits.
- **No additional Shopify Admin call occurs outside `execute_business`.** Every
  page call is a `with execute_business(...)`; no reachable `api.client.execute(`.
- **Do not introduce an umbrella/double lease.** Exactly one lease is held at a
  time (the current page's); non-terminal pages release before the next admits.
  (The earlier "umbrella first-page lease" alternative is **withdrawn** — the
  loop-owned single-lease-at-a-time model is the accepted design.)
- **Preserve all existing guards** verbatim: cursor strict-advance /
  no-repeat, product-`id` identity, `updatedAt` torn-read, zero-node
  forward-progress, per-variant-GID dedup, and the `MAX_VARIANT_PAGES` /
  `MAX_ACCUMULATED_VARIANTS` backstops. They simply run inside each page's context
  instead of inside the removed `_execute_query`.

**[Recommendation]** The common case (`≤100` variants → one page) collapses to a
single `execute_business` context wrapping the one call + normalize + apply +
flush + return — the exact "single structural wrap" the merged §9.3 assumed. The
loop restructuring only adds handling for the multi-page tail; it is otherwise the
same body.

**[CORE-R2 requirement]** Under RD-P, exactly for the product path:

- **Methods that receive the `job` argument:** `import_product_sync` (already has
  it @ `e4669aa`) threads `job` into the loop; the loop passes `job` into every
  `execute_business(job, …)`. The removed `_execute_query` needs no `job`. Helper
  methods that only validate/accumulate a page in memory do **not** touch
  `execute_business` and keep their signatures.
- **Dispatcher thread-through:** none needed — `_handle_product_import_sync`
  already passes `job=job` (line 2050).
- **Indentation region:** the entire page-work body (validate + accumulate + the
  terminal-page `normalize` + `_apply_import` + `flush_all` + `return`) is
  re-indented **under the loop-owned `with`**. `_execute_query` is dissolved into
  the loop.
- **Exceptions:** the `except ShopifyClientError → JobHandlerError` wraps the
  `with` (because `__enter__` can raise `ShopifyClientError` from
  admission-credential/transport/normalize). `ShopifyQuiescedError` **propagates
  uncaught** (fail-closed; routed to `skipped` by Slice 2A — OQ-2). Reconciliation
  `JobHandlerError`s propagate through `__exit__` (lease released) unchanged.
- **Return semantics:** unchanged — the terminal context returns the
  `{'template_binding', 'variant_bindings', …}` dict; the handler still discards
  it. The `return` sits **inside** the terminal `with` (so `__exit__` releases the
  lease on the way out, after `flush_all`).
- **Generation mismatch:** each page's `_admit` compares
  `store.connection_generation` vs `job.expected_connection_generation` under
  `FOR SHARE`; a mismatch raises `ShopifyQuiescedError` → fail closed, no page
  call, no partial write.
- **Disconnecting:** if the store leaves `connected` between pages, the next
  `_admit` refuses (`ShopifyQuiescedError`); no further Shopify call is issued.
- **Lease release on success:** terminal `__exit__` after `flush_all()` deletes +
  commits the terminal lease; non-terminal pages release their own leases on
  `continue`/exit.
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
        self.env.flush_all()   # materialize reconciliation SQL in the main txn
        return outcome         # (no commit); context then releases the lease
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
- **Not extended by the lease:** the **transaction commit**. The lease contract
  ends after the reconciliation code and `flush_all()` (which materializes SQL in
  the main transaction), **not** after the outer transaction commits. The commit is
  the natural dispatcher/RPC boundary's responsibility, occurring *after* the
  handler returns and the lease has released. No explicit main-cursor commit is
  authorized (§5 flush-semantics rule).
- **Not admission-gated (by design, unchanged):** the product **media CDN
  downloads** (`_fetch_image`). They are tokenless GETs to image URLs, not
  credentialed Admin-API business calls; the quiescence contract governs the
  credentialed business call, not CDN reads (AF-3). Because RD-P runs
  `_apply_import` (which triggers `_prepare_media`) **inside** the terminal lease,
  the CDN downloads happen while a lease is held — acceptable and requiring no
  media redesign.

### 5.4 Exception-routing dependency on Slice 2A (hard prerequisite)

**[CORE-R2 requirement]** After migration, `execute_business.__enter__` can raise
`ShopifyQuiescedError` on a fail-closed admission. A correct `skipped` routing for
that exception is a Slice 2A concern (`task-core-r2-disconnect-quiescence-packet.md`
§4, `shopify_connector_job_dispatch.py`; analysis §18). If Slice 2B's call sites
were activated **before** that routing exists, an admission refusal would fall to
the dispatcher's generic boundary (`_invoke_handler` line 248) →
`unknown_system_error` → one safety-net retry → re-refusal or Checkpoint-3 skip —
wrong-tier. **The corrected integration-staging strategy (§7) makes Slice 2A a
hard prerequisite: it must be runtime-green and merged into `Shopify-connector`
before the Slice 2B integration branch is even created.** No Slice 2B activation
runs against a tree lacking Slice 2A.

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

## 6. Runtime-evidence rule — historical domain evidence vs integrated-head evidence

**[Fact]** PR #150 and PR #151 each carry exact-head runtime evidence at a
specific isolated validated SHA:

- PR #151 (product): build **34828304**, DB
  `adamsmen-claude-product-import-completeness-010b-5l-34828304`, validated code
  SHA **`db534f8…`**, fresh install `0 failed, 0 error(s) of 433 tests`.
- PR #150 (customer): concurrency build **34863138**, DB
  `adamsmen-…-k5ux9b-34863138`, validated concurrency SHA **`662e980…`**, fresh
  install `0 failed, 0 error(s) of 357 tests`; benchmark build 34844515 @
  `9895919`.

**[CORE-R2 requirement]** That evidence is **historical, isolated, domain-level
evidence** for those two heads *before* CORE-R2 activation. It is **supporting
evidence only** and is **never** presentable as evidence for the *integrated*
tree. The integrated tree (Slice 2A + PR #151 + PR #150 + both call-site
migrations + the public-`execute()` closure) is a **different** code tree and
must produce **its own** fresh exact-head Odoo.sh evidence at the integration
head (validation plan §2/§3): fresh install green + full core/product/sale suites
green + the CORE-R2 admission/lease classes green + all Slice-2B activation tests
green + the deployed multi-worker proof (×3). The corrected strategy (§7)
therefore does **not** edit PR #150/#151 branches at all — it merges their heads
into a dedicated staging branch and validates the staging head.

---

## 6b. Public-`execute()` closure design (final Slice-2B integration step)

**[Recommendation — resolves former OQ-1, per review `4690659767`]** After both
domain migrations are present on the staging branch (§7 step 5), and given that
Slice 2A (PR #160) already delivers `execute_lifecycle(purpose=…)` and migrated
`action_test_connection` onto it, Slice 2B performs a **separately scoped closure
commit** (§7 step 6; Prompt E, §9c) that removes the last unguarded public
entry.

**[CORE-R2 requirement — closure design]**

1. **Inspect the merged Slice-2A API-client implementation first.** The closure is
   written against the **actual** merged `execute_lifecycle`/transport code, not
   against a predicted shape. Confirm `execute_lifecycle` is the only
   setup/diagnostic entry and that `_send(store, body, token)` is the single HTTP
   seam before changing anything.
2. **Move any remaining legacy lifecycle transport implementation behind a
   private, underscore-prefixed model method.** No public method may retain a
   generic "run an arbitrary query" transport body.
3. **Two entry points only:** `execute_business` is the **sole** business-handler
   entry (admission-gated, context manager); `execute_lifecycle` is the **sole**
   setup/diagnostic entry (purpose→state matrix). Both ultimately reach the single
   private `_send`.
4. **Remove the public unguarded `execute()`** — or make it **unreachable and
   fail-closed** (e.g. it raises rather than issuing any transport). **No
   production caller may call `api.client.execute(...)`.**
5. **No RPC-callable arbitrary-purpose bypass** — `execute_lifecycle`'s `purpose`
   is a fixed enum bound to the allowed-state matrix; there is no generic
   pass-through purpose that would re-open an unguarded path.
6. **No duplicated transport or normalization logic** — the closure factors
   transport/normalization to the single private seam; it does not fork a second
   copy.
7. **The existing error taxonomy remains unchanged** — `ShopifyClientError` /
   `ShopifyQuiescedError` classes, messages, and `credential_invalid` semantics
   are untouched.

**[CORE-R2 requirement — future allowed files for the closure (Prompt E)]**

- **Production:** `addons/shopify_connector_core/models/shopify_connector_api_client.py`.
- **Tests:** the existing API-client and lifecycle test files **required by the
  merged Slice-2A code** (e.g. `addons/shopify_connector_core/tests/test_api_client.py`
  and whatever `execute_lifecycle` test file Slice 2A introduced) — updated so the
  public-surface assertions match the closed surface.
- **Documentation:** the Slice-2B validation record and the Slice-2B handoff.

**[CORE-R2 requirement — source guards the closure must prove]**

- **Zero production `.execute(` callers on the API-client model** — a static
  source scan finds no reachable `api.client.execute(` in any production file
  (importers, store, dispatcher, readiness, anywhere).
- **Business calls use `execute_business`** — every credentialed Admin-API
  business call flows through the context manager.
- **Setup/diagnostic calls use `execute_lifecycle`** — `action_test_connection`
  (and reconnect) use it, never `execute()`.
- **Private transport methods start with `_`** — the surviving transport seam is
  `_send` (and any lifecycle helper) with an underscore prefix; no public generic
  transport method remains.
- **No public generic bypass remains** — the public method surface of
  `shopify.connector.api.client` is exactly `{execute_business, execute_lifecycle}`
  (no public `execute`), asserted by a source-level test.

**[Fact]** This closure is why SRR-03 item C5 ("no stale public `execute()`
call") lands **inside** Slice 2B rather than being deferred. It runs **last**
(after both call sites are migrated) so no caller is orphaned mid-closure.

---

## 7. Cross-branch integration strategy (corrected per review `4690659767`)

**[Fact — the gate this protects]** PR #150 and PR #151 are **frozen behind full
CORE-R2 / SRR-03**. Their Shopify-calling domain handlers still use the
**unguarded legacy `execute()`**. **They must never be merged into
`Shopify-connector` while their handlers remain unguarded** — doing so would
place live, admission-unprotected Shopify-calling code on the integration branch,
which is exactly the gate the whole CORE-R2 effort exists to hold. The prior
"Option B" (merge PR #150/#151 into `Shopify-connector` first, protect the call
sites afterward) **reversed that gate and is rejected.**

**[Recommendation — INTEG, corrected]** Use a **controlled integration-staging
strategy**. The domain PRs are integrated and protected on a *dedicated staging
branch that is not `Shopify-connector` and not a release branch*; only the fully
protected, fully validated result reaches `Shopify-connector`, in one controlled
PR. No implementation or merge is performed by this docs session.

### 7.1 The eight-step staging sequence (deterministic)

**Step 1 — Slice 2A first.** CORE-R2 Slice 2A (PR #160) becomes **exact-head
runtime-green**, control-room accepted, and **merged into `Shopify-connector`**.
Only after that is its generation-bump / disconnect-controller /
`ShopifyQuiescedError → skipped` / `execute_lifecycle` code available as an
integration base (§5.4 hard prerequisite). **Do not depend on PR #160's code or
SHA until it is runtime-green and merged.**

**Step 2 — create the integration staging branch.** From the **post-Slice-2A
`Shopify-connector` tip**, create:

```
claude/core-r2-slice-2b-integration
```

This branch is **not** `Shopify-connector` and is **not** a release branch. It is
the single controlled place where the unguarded domain handlers and their
protection are brought together before any of it can reach `Shopify-connector`.

**Step 3 — merge the domain PR heads into the staging branch only.** Merge the
**exact accepted heads** of **PR #151** (`e4669aa`) and **PR #150** (`10d0034`)
into `claude/core-r2-slice-2b-integration` using **normal merge commits**. **Do
not merge either PR into `Shopify-connector`.** Rules:

- **preserve their complete commit history** (normal merge commits, no squash, no
  rebase-flatten, no cherry-pick);
- **preserve their runtime evidence as historical domain evidence** (§6) — do not
  restate it as integrated-head evidence;
- **do not claim the integrated tree is runtime-green** (it has not been built or
  tested at this point);
- **stop on any `addons/**` conflict** and escalate to the control room rather
  than resolving a code conflict unilaterally;
- **shared-document conflicts** (e.g. both PRs touch `research-handoff.md` /
  `architecture-review-log.md`) **require explicit preservation of both
  histories** — never drop one side.

**Step 4 — two disjoint child branches from the same staging head.** From the
**same** `claude/core-r2-slice-2b-integration` head (after step 3), create:

```
claude/core-r2-product-callsite     # Prompt P applies RD-P here
claude/core-r2-customer-callsite    # Prompt C applies RD-C here
```

The product and customer sessions **may run in parallel** because their domain
files are disjoint (`shopify_connector_product/**` vs `shopify_connector_sale/**`).
Both children branch from the identical staging head (no divergent bases).

**Step 5 — merge both child branches back into staging.** Merge
`claude/core-r2-product-callsite` and `claude/core-r2-customer-callsite` back into
`claude/core-r2-slice-2b-integration` using **normal merge commits**. Now the
staging branch holds Slice 2A (via its base) + both domain PRs + both call-site
migrations.

**Step 6 — public-`execute()` closure on staging.** Perform the final
public-`execute()` privatization/removal (§6b) **on the staging branch** in a
**separately scoped closure commit** (Prompt E), after both domain migrations are
present so every business caller already uses `execute_business` and
`action_test_connection` already uses `execute_lifecycle`.

**Step 7 — validate the staging head.** On the `claude/core-r2-slice-2b-integration`
head, run (validation plan §2/§3):

- fresh installation;
- the complete **core** suite;
- the complete **product** suite;
- the complete **sale** suite;
- **all** Slice-2B activation tests (M1–M18, both domains);
- the **genuine deployed multi-worker proof, three times**;
- cleanup/leak audit (zero leases / jobs / test data);
- the **public-entry static audit** (no reachable `api.client.execute(`).

**Step 8 — one controlled integration PR.** Open **one** integration PR from
`claude/core-r2-slice-2b-integration` → `Shopify-connector`. **Only after that PR
is control-room accepted and merged** may PR #150 and PR #151 be **closed as
subsumed/merged**. PR #150/#151 are never merged directly into `Shopify-connector`
themselves.

### 7.2 What this strategy guarantees

- **No unguarded domain handler ever lands on `Shopify-connector`** — the domain
  code is protected (call-site migrated) and the public `execute()` closed on the
  staging branch *before* the single integration PR reaches `Shopify-connector`.
- **No cherry-pick and no shared CORE-R2 commit is applied twice** — Slice 1 and
  Slice 2A live once, on the base the staging branch is cut from; the domain PRs
  arrive via normal merge commits that preserve history; the two child branches
  share one staging head.
- **Historical domain evidence is preserved, not overstated** — PR #150/#151
  evidence stays attached to their commits as supporting evidence; the integrated
  tree earns its **own** fresh exact-head evidence at the staging head.
- **Clean rollback** — revert the single integration PR to remove the whole
  activation; the staging branch and child branches remain for re-work; the
  zero-holders ordered rollback (packet §17) governs any live teardown.
- **Review clarity** — the control room reviews one integration PR whose diff is
  the two call-site migrations + the `execute()` closure, over a base that already
  contains the (separately reviewed) domain PRs and Slice 2A.

**[Recommendation]** Prompt P and Prompt C stay **independent, single-domain**
sessions (disjoint files, parallel-safe), integrated on the shared staging branch
(steps 4–5); Prompt E is the core-only closure (step 6). None is combined into a
giant session; none starts from a `Shopify-connector` base that already merged
unguarded domain handlers (that base never exists under this strategy).

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

**Required starting branch/head.** The child branch **`claude/core-r2-product-callsite`**,
cut from the **`claude/core-r2-slice-2b-integration`** head (§7 step 4) — i.e.
after Slice 2A is merged into `Shopify-connector` **and** PR #151/#150 heads are
merged into the staging branch. **Never start from a `Shopify-connector` base
that already directly merged the unguarded domain handlers** (that base does not
exist under the corrected strategy) nor from PR #151's raw head in isolation (the
Slice 1 + Slice 2A lease/controller code would be absent). Confirm the staging
head contains `execute_business`, the Slice 2A generation-bump/controller, and
the PR #151 product code before starting.

**Allowed files.**
- `addons/shopify_connector_product/models/shopify_connector_product_importer.py`
  — **call-site-only, loop-owned context (RD-P, §5.1)**: the pagination loop in
  `import_product_sync` / `_fetch_product_with_all_variant_pages` **itself opens
  and closes each page's `with execute_business(job, store, PRODUCT_IMPORT_QUERY,
  variables={'id': gid, 'cursor': cursor}) as result:`**. **Dissolve `_execute_query`
  — do not keep any helper that enters `execute_business` and `return`s `result`
  to its caller** (returning would release the lease before reconciliation). Every
  page's validation + accumulation runs inside its own context; the terminal page
  runs `_normalize_payload` + `_apply_import` + `self.env.flush_all()` + `return`
  inside that final context. Preserve the `ShopifyClientError → JobHandlerError`
  mapping around the `with`, and all existing cursor/identity/torn-read/dedup
  guards. No other logic changes.
- `addons/shopify_connector_product/tests/test_product_callsite_execute_business.py`
  — **new** test file for the Slice-2B activation tests (validation plan §1).
- `addons/shopify_connector_product/tests/__init__.py` — **only** the one-line
  registration of the new test file.
- `docs/05-qa/task-core-r2-slice-2b-validation-results.md` — **new** runtime
  evidence record (or a clearly-scoped product section of it).

**Forbidden files.** Every path not listed above. Specifically: any
`shopify_connector_core` file (the foundation **and Slice 2A** are frozen — do
not edit `execute_business`, `_admit`, `_release_lease`, `_send`, `execute_lifecycle`,
the lease model, the dispatcher, the store, or the job model — the public-`execute()`
closure is Prompt E, not here); any `shopify_connector_sale` file (that is Prompt
C); `adams_base`; any other module; `.claude/**`; CI; `main`; plain `dev`;
`Shopify-connector`; migrations/manifests. No live Shopify call, credential, or
token in any test. No monkeypatch of the lifecycle/state mechanism and no
test-only timing hook — use the real `execute_business` gate + the `_send`
transport-injection seam.

**Implementation-safety instruction (RD-P).** The `with execute_business(...)`
block **must be opened by the loop itself**, never inside a helper that returns
`result`. A reviewer/static guard must confirm no method returns an
`execute_business` `result` to a caller that then reconciles it. The terminal-page
`return` sits **inside** the terminal `with` so `__exit__` releases the lease
after `flush_all`.

**Acceptance criteria.**
1. The product handler path issues **every** Shopify Admin page call through
   `execute_business` (loop-owned context); a static guard asserts no
   `api.client.execute(` remains reachable from the product importer.
2. **Exactly one lease at a time** (loop-owned, no umbrella/double lease). A lease
   exists before each page `_send`; the **terminal page's** lease is held through
   the whole terminal reconciliation (`_normalize_payload` + `_apply_import` +
   `flush_all`); non-terminal pages release on `continue`; the lease releases
   after successful reconciliation and after every failure exit.
3. **No `execute_business` result escapes its context** — no method returns a
   `result` (or a value derived from it before reconciliation) out of the `with`
   block for the caller to reconcile later.
4. Reconciliation (template/variant/attribute/price/media/binding writes) is
   byte-for-byte behaviorally unchanged vs PR #151 (all Task-010B tests still
   green).
5. A disconnect/generation-bump landing **between** pages fails the next page
   closed (`ShopifyQuiescedError`), issues no further Shopify call, and writes no
   partial product.
6. `ShopifyQuiescedError` routes to `skipped` (relies on the merged Slice 2A); no
   `unknown_system_error` for an admission refusal.
7. `flush_all()` is used (no explicit main-cursor `cr.commit()`); no token/PII/
   GraphQL-body/media-byte leakage in logs or lease rows.

**Tests.** New activation tests (validation plan §1 matrix, product column):
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
context manager (no value-returning capture); **no method returns an
`execute_business` `result` to a caller** (loop owns the context); every page
call passes a real `job`; no `cr.commit()` on the main cursor in the importer.

**Working-tree tests.** All new activation tests and the re-run domain classes
must pass on the working tree (local run) before commit; the deployed exact-head
Odoo.sh run is separate (below).

**Rollback.** The child branch's commits are reverted from
`claude/core-r2-slice-2b-integration`; the product importer returns to its PR #151
behavior (dormant foundation, `execute()`); no schema change, no data migration.
Ordered rollback only after zero lease holders (mirror
`task-core-r2-disconnect-quiescence-packet.md` §17).

**Definition of done.** Code + tests written; working-tree tests pass; only
allowed files changed; the commits are merged back into
`claude/core-r2-slice-2b-integration` (§7 step 5); **committed-head Odoo.sh
validation is captured after that merge-back** (the integrated staging head — not
an isolated product head — earns the exact-head evidence: fresh install + full
core/product/sale suites + CORE-R2 classes + the new activation tests all green);
`pr-review-checklist.md` section C satisfied; self-review classified; handoff +
validation record updated; SRR-03 stays OPEN; no direct PR to `Shopify-connector`
(the single integration PR is §7 step 8).

**Final report requirements.** Starting staging head + child branch + final head;
exact files changed; the committed-head Odoo.sh build number, DB name, and
validated SHA captured **after merge-back into staging**; the activation-test
results; confirmation no `shopify_connector_sale` or `shopify_connector_core` file
changed; confirmation SRR-03 OPEN and no gate opened beyond this task.

---

## 9. Future implementation prompt C — customer call-site migration only

> **GATED. Do not execute until ChatGPT opens the gate for THIS task.**

**Objective.** Migrate the **single** customer-import business call site to `with
execute_business(job, store, query, variables) as result:` per RD-C (§5.2), with
reconciliation inside the lease. **No customer matching, email-normalization,
partner-creation, duplicate-prevention, or binding behavior may change.**

**Required starting branch/head.** The child branch **`claude/core-r2-customer-callsite`**,
cut from the **`claude/core-r2-slice-2b-integration`** head (§7 step 4) — the same
staging head Prompt P uses. **Never start from a `Shopify-connector` base that
already directly merged the unguarded domain handlers** (no such base exists under
the corrected strategy). Confirm the staging head contains `execute_business`,
Slice 2A, and the PR #150 customer code.

**Allowed files.**
- `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py`
  — **call-site-only**: replace the `execute()` call (lines 117-127 @ `10d0034`)
  with the RD-C structural wrap; preserve `ShopifyClientError → JobHandlerError`;
  keep `job` threaded (already present); use `self.env.flush_all()` (no
  main-cursor commit).
- `addons/shopify_connector_sale/tests/test_customer_callsite_execute_business.py`
  — **new** activation test file.
- `addons/shopify_connector_sale/tests/__init__.py` — **only** the one-line
  registration of the new test file.
- `docs/05-qa/task-core-r2-slice-2b-validation-results.md` — **new/shared**
  runtime record (customer section).

**Forbidden files.** Every path not listed. Specifically any
`shopify_connector_core` file (foundation **and Slice 2A** frozen; the
public-`execute()` closure is Prompt E), any `shopify_connector_product` file
(that is Prompt P), `adams_base`, other modules, `.claude/**`, CI, `main`, plain
`dev`, `Shopify-connector`. No live Shopify call/credential/token in tests; no
lifecycle monkeypatch; no test-only timing hook.

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

**Tests.** New activation tests (validation plan §1 matrix, customer column):
the same lease-lifecycle, disconnect-ordering, generation-mismatch, and
no-duplicate-binding proofs as Prompt P, for the single customer call.
**Re-run unchanged:** all PR #150 classes (`TestCustomerBinding`,
`TestCustomerImportMatching`, `TestCustomerDuplicatePrevention`,
`TestCustomerFallbackPartner`, `TestCustomerMatchingScalability`,
`TestCustomerMatchingBenchmark`, `TestCustomerMatchingConcurrency`) and the
CORE-R2 admission classes.

**Static guards.** No `.execute(` reachable from
`shopify_connector_customer_importer.py`; `execute_business` used only as a
context manager; the `result` never escapes the `with` block; the call passes a
real `job`; no main-cursor `cr.commit()`.

**Working-tree tests.** New activation tests + re-run domain classes pass locally
before commit; committed-head Odoo.sh run is captured after merge-back into
staging.

**Rollback.** Revert the child branch's commits from
`claude/core-r2-slice-2b-integration`; the customer importer returns to PR #150
behavior; no schema/data change. Zero-holder-first ordered rollback.

**Definition of done.** As Prompt P, for the customer domain: working-tree tests
pass; commits merged back into `claude/core-r2-slice-2b-integration`;
committed-head Odoo.sh validation captured after merge-back; SRR-03 stays OPEN; no
direct PR to `Shopify-connector`.

**Final report requirements.** As Prompt P, for the customer domain (staging head
+ child branch + final head; committed-head evidence after merge-back).

**[Recommendation]** Keep Prompt P and Prompt C **independent** (disjoint files,
parallel-safe child branches, independent rollback) but **integrated on the same
`claude/core-r2-slice-2b-integration` branch** (§7 steps 4–5) before the final
proof. Do **not** combine product and customer changes into one giant session —
the integration analysis (§7) shows the two child branches are safe to separate
(disjoint `shopify_connector_product/**` vs `shopify_connector_sale/**` file sets;
no shared edited file).

---

## 9c. Future implementation prompt E — public-`execute()` entry closure only

> **GATED. Do not execute until ChatGPT opens the gate for THIS task.** Core-only.
> **May run only after Prompt P and Prompt C have been merged back into
> `claude/core-r2-slice-2b-integration`** (§7 step 6) — never before both call
> sites are migrated.

**Objective.** Close the API-client public surface per §6b: privatize/remove the
public unguarded `execute()` so `execute_business` (business) and
`execute_lifecycle` (setup/diagnostic, delivered by Slice 2A) are the only public
entries, and no production caller can reach `api.client.execute(...)`. **No error
taxonomy, transport, or normalization behavior may change.**

**Required starting branch/head.** The `claude/core-r2-slice-2b-integration` head
**after** steps 4–5 (both call-site migrations merged back). Inspect the merged
Slice-2A `execute_lifecycle`/`_send` implementation first (§6b step 1).

**Allowed files.**
- `addons/shopify_connector_core/models/shopify_connector_api_client.py` — move
  any residual legacy transport body behind a private `_`-prefixed method; remove
  or fail-close the public `execute()`; keep `execute_business`/`execute_lifecycle`
  as the only public entries; no duplicated transport/normalization.
- The existing API-client + lifecycle test files required by the merged Slice-2A
  code (e.g. `addons/shopify_connector_core/tests/test_api_client.py` and the
  Slice-2A `execute_lifecycle` test file) — update public-surface assertions.
- `docs/05-qa/task-core-r2-slice-2b-validation-results.md` and the Slice-2B
  handoff — record the closure.

**Forbidden files.** Every path not listed; any product/sale file; `adams_base`;
other modules; `.claude/**`; CI; `main`; plain `dev`; `Shopify-connector`. No new
public generic-purpose entry; no live Shopify call/credential/token in tests.

**Acceptance criteria + static guards (§6b).** Zero production `.execute(` callers
on the API-client model; business calls use `execute_business`; setup/diagnostic
calls use `execute_lifecycle`; the surviving transport seam is `_`-prefixed
(`_send`); the public method surface is exactly `{execute_business,
execute_lifecycle}`; no RPC-callable arbitrary-purpose bypass; error taxonomy
unchanged (`TestApiClient` and the lifecycle tests green).

**Rollback.** Revert the closure commit; `execute()` returns to public. No
schema/data change. **Definition of done / final report:** as Prompt P, core-only;
committed-head Odoo.sh validation on the staging head after the closure; SRR-03
stays OPEN.

**[Recommendation]** Prompt E is the **last** Slice-2B step before the single
integration PR (§7 step 8). It must not run before both call sites are migrated,
or it would orphan a live `execute()` caller.

---

## 10. Claim classification summary

| Class | Items |
| --- | --- |
| **[Fact — current code]** | §2, §3, §4 call-site inventories with anchors; the base vs PR-head differences; the multi-page product loop; the customer single call; `job` thread-through status per domain/version. |
| **[Fact — merged design]** | The `execute_business`/`_admit`/lease contract (§2); analysis §6 Phase A/B/C; §9.3's stale base-anchored spec; direction-C. |
| **[CORE-R2 requirement]** | The lease-coverage/reconciliation-boundary rules and the precise `flush_all` (materialize-not-commit) semantics (§5, §5.3); RD-P loop-owned context (§5.1); historical-vs-integrated evidence (§6); public-`execute()` closure design + guards (§6b); Slice-2A-first hard prerequisite (§5.4); "no matching/pricing/media redesign". |
| **[Recommendation]** | Slice decomposition (§0); RD-P loop-owned design (§5.1); RD-C (§5.2); **integration-staging strategy, 8 steps (§7)** replacing the rejected Option B; Prompt P/C/E (§8/§9/§9c). |
| **[Resolved — previously open]** | OQ-1 → public-`execute()` closure owned by Slice 2B (§0, §6b, Prompt E). OQ-3 → RD-P is loop-owned per-page, single-lease-at-a-time; the umbrella alternative is withdrawn (§5.1). OQ-2 → firmed into a hard prerequisite: Slice 2A (PR #160) must be runtime-green and merged before the staging branch is created (§5.4, §7 step 1). |
| **[Open question]** | Residual: OQ-5 (`flush_all` exactness confirmed against Odoo 19 by the implementing session) and PR #160's own runtime-green + control-room acceptance (external prerequisite, tracked, not this packet's to resolve). See handoff §Open questions. |

## 11. Adversarial self-review

The full adversarial pass is recorded in
`docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` (§ Adversarial
findings AF-1…AF-13). Summary: no unguarded domain handler reaches
`Shopify-connector` (staging strategy, §7); the lease never ends before
reconciliation (terminal-page context holds it through `flush_all`); no
`execute_business` result escapes its context (loop owns the `with`, RD-P);
`job` is threaded (present at both PR heads); no hidden second Admin call (media
is a tokenless CDN GET); no matching/pricing/media redesign; no explicit
main-cursor commit and `flush_all` is described as materialize-not-commit; no
public `execute()` bypass survives closure (§6b); no shared CORE-R2 commit is
double-applied and no sibling-branch history duplication (staging strategy); child
branches share one staging head; historical PR #150/#151 evidence is not passed
off as integrated evidence; no product/customer scope mixing; no premature SRR-03
closure; no live-Shopify claim; no token/PII logging; and **no implementation
gate is opened by this packet.**

## 12. References

- `docs/03-architecture/disconnect-quiescence-remediation-analysis.md` (AR-047,
  Rev 4): §3, §6 (Phase A/B/C), §8, §9.1, §9.2, §9.3, §10, §14, §16, §18, §19,
  §22, §24 (T-1…T-14, T-19), §26.
- `docs/07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`:
  §4 (allowed files), §5 (forbidden), §9 (frozen API contract), §12 (direction-C
  timeout), §17 (ordered rollback), §18/§19 (DoD / future-PR requirements).
- `docs/05-qa/task-core-r2-validation-results.md`: §4.1–§4.3, §5 (Slice 2/3
  deferrals), §9 (RR-C, RR-F), §11.
- PR #156 (merged, Slice 1); **PR #160 (`b3d23cb`, Slice 2A, draft, no
  runtime-green claimed — hard prerequisite)**; PR #151 (`e4669aa`, Task 010B);
  PR #150 (`10d0034`, Task 011B); Issue #157.
- **Control-room review `4690659767` (REVISE)** — the correction driving this
  revision (integration-staging strategy; RD-P loop ownership; flush semantics;
  public-`execute()` closure; staging-based prompts).
- Companion Slice-2B files:
  `docs/05-qa/task-core-r2-slice-2b-validation-plan.md`;
  `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md`.
