# CORE-R2 Slice 2B — Customer Call-Site Migration: Validation Record

> **Status: implementation session — static validation only. NOT runtime-green.**
> This document records the customer-domain call-site migration
> (Slice 2B, Prompt C / RD-C) from the legacy value-returning api-client
> `execute()` to the CORE-R2 `execute_business()` admission-lease context
> manager. **No Odoo runtime was available in this session** — the exact-head
> Odoo.sh evidence is captured later, on the integration-staging head, after
> merge-back (packet §7). **SRR-03 remains OPEN. Prompt E remains blocked. No
> live Shopify call was made.**

**Model:** Opus 4.8.
**Date:** 2026-07-14.
**Architecture of record:** AR-047 (`docs/03-architecture/disconnect-quiescence-remediation-analysis.md`).
**Packet:** `docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md` §5.2 (RD-C), §9 (Prompt C).

**Claim labelling (`CLAUDE.md` §8).** Every load-bearing statement is tagged
**[Fact — code]**, **[Fact — static result]**, **[CORE-R2 requirement]**,
or **[Runtime pending]**.

---

## 1. State verification

| Check | Expected | Observed | Verdict |
| --- | --- | --- | --- |
| Working branch | `claude/core-r2-customer-callsite` | `claude/core-r2-customer-callsite` | ✅ |
| Starting head | `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79` | `4f2cd7e…` | ✅ |
| Integration staging tip | identical head | `origin/claude/core-r2-slice-2b-integration` = `4f2cd7e…` | ✅ |
| Working tree | clean at start | clean | ✅ |
| PR #160 (Slice 2A) | merged | `state=closed, merged=true` | ✅ |
| PR #150 (Task 011B, customer) | open/draft/unmerged | `state=open, draft=true, merged=false`, head `10d0034…` | ✅ |
| PR #151 (Task 010B, product) | open/draft/unmerged | `state=open, draft=true, merged=false`, head `e4669aa…` | ✅ |
| Product head ancestor of `4f2cd7e` | yes | `e4669aa…` is ancestor | ✅ |
| Customer head ancestor of `4f2cd7e` | yes | `10d0034…` is ancestor | ✅ |
| Post-Slice-2A base ancestor of `4f2cd7e` | yes | `a3fd6cd…` is ancestor | ✅ |
| Existing child PR (head=callsite branch) | none | `list_pull_requests` returned `[]` | ✅ |

**[Fact]** The session brief's stated working branch and starting head match the
live remote exactly. (A harness-provisioned placeholder branch,
`claude/core-r2-slice-2b-customer-ou4mao`, was deleted at origin at session
start; work proceeds on the task-designated `claude/core-r2-customer-callsite`
at the required head, per the explicit task instruction.)

- **Starting head:** `4f2cd7e4e09c591d4b63dd77888dd22f355f5c79`
- **Final head:** *(the docs commit on `claude/core-r2-customer-callsite`; see §11 / handoff)*

---

## 2. Exact changed files — the five-file PR scope

**[Fact — static result]** The PR (`claude/core-r2-customer-callsite` →
`claude/core-r2-slice-2b-integration`) changes **exactly five files**: one
production importer, two customer test files, and these two domain-specific
evidence documents. `git diff --stat` against the starting head:

| File | Kind | Change |
| --- | --- | --- |
| `addons/shopify_connector_sale/models/shopify_connector_customer_importer.py` | Production | Call-site migration (`import_customer_sync`) + docstring accuracy |
| `addons/shopify_connector_sale/tests/test_customer_import_matching.py` | Tests | Adapt 6 transport-stub tests + rewrite AST guard + new `TestCustomerCallsiteExecuteBusiness` (unit lease guards; the disconnected-store test is a **pre-admission refusal**, not Race A) |
| `addons/shopify_connector_sale/tests/test_customer_matching_scalability.py` | Tests | Fail-loud lease-leak cleanup on the existing genuine race; **new genuine independent-connection lifecycle proofs** (`_CustomerGenuineHelpers` + M1/M2/Race A/Race B classes) |
| `docs/05-qa/task-core-r2-customer-callsite-validation.md` | Docs | This validation record |
| `docs/07-implementation-plan/task-core-r2-customer-callsite-handoff.md` | Docs | The session handoff |

**No other file changed.** No `shopify_connector_core`, `shopify_connector_product`,
manifest, XML, security, data, migration, CI, or shared handoff/AR file is in the
diff. Confirmed by `git diff --name-only`. (The earlier "(3)" wording counted only
the code/test files and is corrected here to the true five-file PR scope, per
review `4695664662` #5.)

---

## 3. Old vs new call-site structure

**[Fact — code]** Before (`import_customer_sync`, @ `10d0034`/`4f2cd7e`):

```python
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

**[Fact — code]** After (Slice 2B):

```python
client = self.env['shopify.connector.api.client']
try:
    with client.execute_business(
        job, store, CUSTOMER_IMPORT_QUERY,
        variables={'id': shopify_customer_gid},
    ) as result:
        payload = self._normalize_payload(result)
        outcome = self._apply_import(store, payload, job=job)
        self.env.flush_all()   # materialize reconciliation SQL; no commit
        return outcome
except ShopifyClientError as exc:
    raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail) from exc
```

The only structural change is the transport/lease boundary and the `job`
thread-through into `execute_business`. The reconciliation
(`_normalize_payload`, `_apply_import`, and everything below) is byte-for-byte
unchanged.

---

## 4. Lease boundary (§5.3)

**[CORE-R2 requirement — satisfied]** The single committed admission lease covers,
in order and inside the one `with` block:

1. the Shopify Admin GraphQL customer call (issued by `execute_business.__enter__`
   via `_admit` → `_send(store, body, token)`);
2. the API-client normalization (`_normalize_response` in `__enter__`);
3. the importer normalization (`_normalize_payload(result)`);
4. the **entire** matching/reconciliation (`_apply_import` → savepoint →
   `_resolve_customer_binding` → candidate search → partner/binding writes);
5. the final `self.env.flush_all()` (materialize-in-transaction, **not** commit);
6. the return-value construction (`return outcome`).

The lease releases only on `with`-exit (`__exit__` → `_release_lease`), **after**
reconciliation and flush. **Not extended by the lease:** the outer transaction
commit — performed by the natural dispatcher/RPC boundary after the handler
returns. **No explicit main-cursor commit is issued** (AST-verified, §7).

---

## 5. Exception behaviour (§4 contract)

**[Fact — code, verified against `shopify_connector_api_client.py`]**

| Trigger | Path | Outcome |
| --- | --- | --- |
| Missing/empty credential | `_admit` raises `ShopifyClientError(ERROR_AUTH, …)` in `__enter__`, before any lease | caught by `except ShopifyClientError` → `JobHandlerError('shopify_permission_scope_auth', …)`; class/reason/technical_detail preserved; `from exc` chained |
| Transport / GraphQL failure | `_send`/`_normalize_response` raise `ShopifyClientError` in the body → `__exit__` releases lease once → re-raise | caught → `JobHandlerError(<mapped class>, …)`; DEC-009 taxonomy preserved |
| Missing shop_domain/api_version | `execute_business` raises `UserError` before admission | propagates (unchanged from the old `execute()` behaviour) |
| Fail-closed admission (store gone / no job / wrong store / not `connected` / generation mismatch) | `_admit` raises `ShopifyQuiescedError` in `__enter__`, before any lease | **propagates UNCAUGHT** (the `except` catches only `ShopifyClientError`) → routed by the integrated Slice 2A dispatcher through the fail-closed `skipped` contract |
| Reconciliation failure (`ambiguous_match` / `binding_conflict` / `duplicate_risk` / `data_shape_schema_mismatch`) | `_apply_import` raises `JobHandlerError` in the body → `__exit__` releases lease once → re-raise | propagates unchanged (not a `ShopifyClientError`, so not re-wrapped) |

**[CORE-R2 requirement — satisfied]** `ShopifyQuiescedError` is never converted to
`unknown_system_error`, never caught by a broad `Exception`, and never remapped —
AST-verified that the sole `except` clause catches exactly `ShopifyClientError`.

---

## 6. Regression coverage (behaviour that must not change)

**[Fact — code]** The reconciliation path is unchanged; the following Task
011/011B classes/tests continue to exercise it and were **not weakened** (53
assertions added across the diff, **0 removed**):

- `TestCustomerImportMatching` — existing-binding-first; single-active-email bind;
  case-folding; recall-safe wrapped/display-name match; binding_conflict;
  ambiguous_match (+ 20-cap); create-path address mapping; unresolvable
  country/state leaves field empty; existing-matched-partner address never
  written; person-only create; null email/address tolerated; sale-domain gating;
  zero-mutation. *(The six end-to-end tests that previously stubbed `execute` now
  drive the real `execute_business` + `_send` seam; their behavioural assertions
  are identical.)*
- `TestCustomerDuplicatePrevention` — reimport idempotency; recall-safe
  active/archived; missing/empty email; archived-only; uniqueness backstop;
  no order/product/inventory side effects. *(Unchanged — direct `_apply_import`.)*
- `TestCustomerFallbackPartner` — posture-A behaviour; no auto-create.
  *(Unchanged — direct `_apply_import`.)*
- `TestCustomerBinding` — required fields, uniqueness, ACL matrix.
  *(Unchanged — no API call.)*
- `TestCustomerMatchingScalability` — indexed-column field/compute; old-vs-new
  candidate-set equivalence; routing regression; source guards.
  *(Unchanged — direct `_find_*`/`_apply_import`.)*
- `TestCustomerMatchingBenchmark` (opt-in) — unchanged.
- `TestCustomerMatchingConcurrency` (opt-in, genuine two-transaction race) —
  **adapted only at the transport seam**: `execute` stub → `_send` stub;
  credential + generation provisioned on the committed setup so `_admit` passes;
  the binding-INSERT uniqueness race, the attributed lock-wait proof, the
  two-stage `retry_waiting` → `binding_conflict` routing, the single-survivor
  invariant, and all durable-cleanup/leak assertions are **unchanged**. A
  defensive `call.lease` sweep was added to `_durable_cleanup`.

---

## 7. Static validation results

**[Fact — static result]** All run this session (no Odoo runtime):

- `py_compile` — production importer + all five customer test files: **OK**.
- `compileall addons/shopify_connector_sale` — **OK**.
- Conflict-marker scan (`addons/shopify_connector_sale`, `docs/`) — **none**.
- Changed-file inventory — exactly the 3 allowed files; no core/product/manifest/
  XML/security file touched.
- **AST/source invariant scan of the migrated importer — 16/16 PASS:**
  one `execute_business` call / zero `execute` calls; `job` first positional;
  `with` binds `result`; `_normalize_payload` / `_apply_import` / `flush_all` /
  `return` all inside the `with`; `flush_all` before `return`; `result` used only
  inside the `with`; no `commit`; no `_admit`/`_release_lease`/`_send`/lifecycle
  seam access; no `call.lease`/`lease_key` strings; the sole `except` catches only
  `ShopifyClientError`; `ShopifyQuiescedError` not caught; no broad
  `Exception`/`BaseException` handler.
- Secret/PII scan — only the non-secret placeholder `shpat_DUMMYDUMMYDUMMY…`
  token and reserved test domains (`@example.com`, `@callsite.example`); no real
  token, key, or PII.
- Changed-assertion review — 0 existing assertions removed or weakened.

**[Runtime pending]** Odoo test execution, fresh-install/full-suite green, the
Slice-2B activation tests, and the deployed multi-worker proof are captured later
on the integration-staging head (packet §7 step 7). **This session does not claim
Odoo runtime-green.**

---

## 8. Tests — four distinct layers (corrected per review `4695664662`)

The customer proofs are now cleanly separated into four layers; the earlier
mislabelling of a pre-set-state test as "Race A" is corrected.

### 8.1 Unit lease guards — `TestCustomerCallsiteExecuteBusiness` (standard CI)

In `test_customer_import_matching.py`, driving the real
`execute_business`/`_admit`/`_release_lease` path via the `_send` seam under
registry test mode (a single shared connection):

- **Static guards:** no bare `execute(`; `execute_business` receives a real `job`;
  no explicit commit; no manual lease/transport seam access; `result` never
  escapes the context; every `return` is inside it.
- **Success:** one context (one transport, one reconciliation, one release); lease
  observed before transport and during reconciliation; binding materialized before
  the lease releases; return value is the matched binding; lease released after.
- **Error:** `ShopifyClientError` → `JobHandlerError` (DEC-009 class preserved),
  release-once; normalization/ambiguity/binding_conflict/partner-write failures
  each release once; `ShopifyQuiescedError` propagates uncaught with **no
  transport** and **no leaked lease**.
- **Pre-admission refusals (NOT Race A):** `test_quiesced_error_propagates_…`
  (generation mismatch) and `test_disconnected_store_fails_closed_…` (store not
  `connected`) prove the **pre-admission/fail-closed refusal** only. They are
  explicitly **not** the concurrent disconnect-vs-admission ordering — that is the
  genuine Race A below. The test comments and this record now say so.

These are unit lease counts under registry test mode; per the validation plan they
are *supporting* evidence and **cannot** prove committed-lease visibility on an
independent connection.

### 8.2 Genuine independent-connection lifecycle proofs (opt-in, runtime)

**New** in `test_customer_matching_scalability.py` — `_CustomerGenuineHelpers` +
three classes tagged
`('post_install','-at_install','-standard','shopify_connector_customer_callsite_lifecycle')`,
authored to run on a genuine multi-connection PostgreSQL runtime host (like the
existing `TestCustomerMatchingConcurrency`). They use real `db_connect`
connections (bounded statement/lock timeouts, distinct backend PIDs), the REAL
`execute_business`/`_admit`/`_release_lease` path, the REAL
`action_disconnect`/admission lock protocol, and the REAL
`_run_disconnect_quiesce` controller. Only `_send` is the transport seam;
production lifecycle/state is never monkeypatched. The reconciliation pause is a
genuine `UNIQUE(store,partner)` index wait (a second connection holds an
uncommitted binding, then **rolls back** so the admitted call succeeds).

| Class / test | Proves |
| --- | --- |
| `TestCustomerCallsiteLeaseVisibilityGenuine.test_m1_…` | **M1** — the committed lease is visible on an independent connection **before** `_send`, carries the real captured token, and releases on context exit. |
| `…LeaseVisibilityGenuine.test_m2_…` | **M2** — the same single lease is held while `_apply_import` is genuinely **paused mid-reconciliation**, then released only after reconciliation completes. |
| `TestCustomerCallsiteRaceAGenuine.test_race_a_disconnect_first_…` | **Race A / M8 (disconnect-first)** — a real `action_disconnect` committed before admission makes `_admit` read the fresh committed state and raise `ShopifyQuiescedError`; **zero transport, no lease, no binding**. |
| `…RaceAGenuine.test_race_a_admission_first_…` | **Race A / M8 (admission-first)** — `_admit` commits the lease + token first; a real disconnect committed during the call returns; the admitted call continues with its **old in-memory token** and binds; lease releases; credential preserved. |
| `TestCustomerCallsiteRaceBGenuine.test_race_b_…` | **Race B / M18** — a real `action_disconnect` landing after a committed admission **returns without waiting** for the paused reconciliation (the disconnect's `FOR NO KEY UPDATE` does not conflict with the in-flight binding's `FOR KEY SHARE`); the controller **defers** finalization while the lease is open (its `FOR UPDATE SKIP LOCKED` safely skips the in-flight store) and finalizes `completed` + clears the credential **only after** the call releases its lease. |

### 8.3 Cleanup correction (review `4695664662` #4)

`TestCustomerMatchingConcurrency` now captures the committed lease count on an
**independent connection before any cleanup**, asserts it is zero (a release
regression is fail-loud and cannot be masked by the cleanup's own lease sweep),
and includes a `leases` entry in the independent verification map.

### 8.4 Regression

The existing Task 011/011B suites are unchanged (§6); `0` existing assertions were
removed or weakened.

The `execute`→`execute_business` AST guard
(`test_source_level_single_execute_business_call_uses_fixed_query_constant`)
asserts exactly one `execute_business` call, **zero** `execute` calls, and the
fixed `CUSTOMER_IMPORT_QUERY` constant.

### 8.5 Which tests were executed

**[Runtime pending]** No Odoo runtime was available in this session. **None of the
above tests were executed here.** They are authored and pass `py_compile` /
`compileall` only. The unit lease guards (§8.1) run in standard CI; the genuine
lifecycle proofs (§8.2) are `-standard` and run explicitly on the runtime host via
`--test-tags shopify_connector_customer_callsite_lifecycle`. Execution is captured
on the integration-staging head after merge-back (§9). **No test is claimed to
have passed.**

---

## 9. Runtime status

**[Runtime pending]** No Odoo runtime in this session. The integrated
exact-head Odoo.sh evidence (fresh install + core/product/sale suites + CORE-R2
admission classes + the Slice-2B activation tests + multi-worker proof) is
produced after this child branch is merged back into
`claude/core-r2-slice-2b-integration` (packet §7 steps 5–7). **No runtime-green
is claimed here.**

---

## 10. Gates

- **Prompt E (legacy public `execute()` closure) remains BLOCKED** — it is a
  separate, later, core-only session that runs only after *both* domain call
  sites are migrated and merged back to staging (packet §9c). This session does
  not touch `shopify_connector_core` and does not close the public surface.
- **SRR-03 remains OPEN** — full CORE-R2 disconnect quiescence is not closed by a
  call-site migration; the generation gate is dormant until the integrated 2A+2B
  system runs (packet §5.5).
- **No merge, no live Shopify call, no runtime-green claim, no PR closure.**

---

## 11. Rollback

**[Fact]** Rollback is a normal revert of this child PR before integration; no
schema or data migration is introduced. Reverting restores the inherited Task
011B `import_customer_sync` (legacy `execute()`), which remains intact below the
call site. Ordered rollback (zero lease holders first) mirrors
`task-core-r2-disconnect-quiescence-packet.md` §17 for any future live teardown.
