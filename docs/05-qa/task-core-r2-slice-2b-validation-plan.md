# Task CORE-R2 — Foundation Slice 2B: Validation Plan

> **Status: Proposed validation plan for ChatGPT review. THE CODE GATE IS NOT
> OPEN.** Documentation only — no code, no tests executed, no live Shopify call,
> no runtime run performed in this session. **SRR-03 remains OPEN.**

**Model:** Opus 4.8. **Date prepared:** 2026-07-14.
**Revision 2 (2026-07-14):** corrected per control-room review **`4690659767`** —
every proof below is now stated against the **final integration-staging head**
(`claude/core-r2-slice-2b-integration`, packet §7), with new proofs for
loop-owned context ownership, no-result-escape, no-public-generic-`execute()`,
`execute_lifecycle` for setup/diagnostic, and precise flush semantics.
**Architecture:** AR-047.

Companion to
`docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`
(call-site inventory, change design RD-P/RD-C, integration-staging strategy) and
`docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md` (handoff, open
questions, adversarial findings). This file defines: (§1) the regression +
runtime test matrix that proves each activated call site is quiescence-correct;
(§2) the deployed multi-worker/multi-server validation plan proving SRR-03
across real workers/servers; and (§3) the SRR-03 closure criteria.

### 1.0 What the plan must prove on the final integration-staging head

**[CORE-R2 requirement]** All of the following are proven on the
`claude/core-r2-slice-2b-integration` head (Slice 2A merged into
`Shopify-connector` + PR #151/#150 heads + both call-site migrations + the
public-`execute()` closure), **never** on an isolated domain head:

- every **product** Admin-API **page** call uses `execute_business` (loop-owned);
- the **customer** Admin-API call uses `execute_business`;
- **no `execute_business` result escapes its context** before the required page
  work / terminal reconciliation completes (M14);
- **no public generic `execute()` entry remains** on the API-client model (M16);
- **test-connection / reconnect use `execute_lifecycle`** (M17);
- a disconnect **between product pages blocks the next page** (M9);
- a disconnect **after terminal admission permits terminal reconciliation to
  finish** with the in-memory token (M8/M18);
- **customer reconciliation holds the lease through the flush** (M2);
- **no explicit main-cursor commit**; `flush_all` materializes SQL in the main
  transaction only (M15);
- **all domain behavior remains unchanged** (M11/M12);
- the **integrated exact-head core / product / sale suites are green** (§1.4);
- the **deployed multi-worker proof is green three times** (§2);
- cleanup shows **zero leases / jobs / test data** (§2.1 assertion 12);
- **issue #157 remains separate** (§1.3);
- **SRR-03 stays OPEN until every §3 closure item passes**.

Historical PR #150/#151 runtime results are **supporting evidence only** (§6 of
the packet) — never final integrated-head evidence.

**Scope guard.** These tests exercise the **real** `execute_business`/`_admit`/
lease-ORM/`_release_lease`/`_send` boundary — never a monkeypatched lifecycle,
never a test-only timing hook — mirroring the merged evidence discipline
(`disconnect-quiescence-remediation-analysis.md` §24 Method;
`task-core-r2-validation-results.md` §3). The only injection seam is `_send`
(fake in-memory transport); no live Shopify, no live credential, no token in
tests.

---

## 1. Regression + runtime test matrix

### 1.1 What must be proven, per domain

**[CORE-R2 requirement]** For **each** activated domain (product, customer),
Slice 2B must prove the following. "Business call" = the admitted Admin-GraphQL
call issued through `execute_business` (for products, *each page*).

| # | Property to prove | Product proof (RD-P, §5.1 of packet) | Customer proof (RD-C, §5.2 of packet) |
| --- | --- | --- | --- |
| M1 | **Lease exists before transport.** A committed `shopify.connector.call.lease` row is visible on an independent connection before `_send` runs. | Assert one lease per page admission before that page's fake `_send` fires. | Assert one lease before the single fake `_send`. |
| M2 | **Lease remains through reconciliation.** The reconciliation-bearing lease is held for the whole reconciliation region (normalize + `_apply_import` + `flush_all`); **exactly one lease at a time** (no umbrella/double lease). | Terminal-page context: assert exactly one lease exists at the moment `_apply_import` writes bindings/prices/media and until `flush_all` completes; non-terminal pages held exactly one lease each and released it on `continue`. | Assert exactly one lease exists while `_apply_import` runs and until `flush_all`. |
| M3 | **Lease releases after successful reconciliation.** Post-context, lease count for the store == 0. | After `import_product_sync` returns, `count(call.lease)==0`. | After `import_customer_sync` returns, `count(call.lease)==0`. |
| M4 | **Lease releases after a transport exception.** A `_send` `RequestException`/`ShopifyClientError` leaves no lease. | Fake `_send` raises on a page → the page context `__exit__` releases; `count==0`; `JobHandlerError` surfaces. | Fake `_send` raises → `__exit__` releases; `count==0`; `JobHandlerError`. |
| M5 | **Lease releases after a normalization exception.** A payload that makes normalization/validation raise leaves no lease. | Malformed page/product → `data_shape_schema_mismatch` inside the context → released; `count==0`. | Malformed customer payload → `data_shape_schema_mismatch` inside the context → released; `count==0`. |
| M6 | **Lease releases after a local business-record exception.** A reconciliation failure (ambiguous/duplicate/binding-conflict/Odoo `ValidationError`) leaves no lease. | Force `ambiguous_match`/`duplicate_risk` in `_apply_import` → released; `count==0`; the JobHandlerError keeps its class. | Force `binding_conflict`/`ambiguous_match` → released; `count==0`; class preserved. |
| M7 | **Disconnect winning before admission blocks transport.** If the store is not `connected` / generation-bumped before `__enter__`, admission raises `ShopifyQuiescedError` and no `_send` runs. | Set store `disconnecting`/bump generation before the (first) page → `ShopifyQuiescedError`, fake `_send` never called, no lease, no write. | Same for the single call. |
| M8 | **Admission winning before disconnect lets the current call finish.** A call admitted (lease committed) before the disconnect's update-lock proceeds runs to completion under the observed lease. | With a lease held, a concurrent `action_disconnect` (Slice 2A) waits on the store-row update-lock until the page context releases. | Same for the single call. |
| M9 | **No second Shopify call after a disconnect request.** Once the gate observes the disconnect, no further business call is issued. | After a disconnect between page k and k+1, page k+1's `_admit` fails closed; fake `_send` call-count does not increase. | Not applicable beyond M7 (single call), but assert the fake `_send` is called exactly once on the happy path and zero times on a pre-admission refusal. |
| M10 | **Generation mismatch fails closed.** `store.connection_generation != job.expected_connection_generation` at admission → `ShopifyQuiescedError`, no call, no write. | Bump the store generation after enqueue; assert every page admission refuses. | Bump after enqueue; assert the call refuses. |
| M11 | **No duplicate binding is introduced.** The activated path creates exactly the same one binding per template/variant/customer as the pre-migration path. | Re-run a product import twice; assert exactly one template binding + N variant bindings; no phantom/duplicate. | Re-run a customer import twice; assert exactly one customer binding + one partner. |
| M12 | **Existing Task 010B / 011B behavior is unchanged.** All pre-migration domain tests pass byte-for-byte behavior. | Re-run all PR #151 classes (§1.3) green. | Re-run all PR #150 classes (§1.3) green. |
| M13 | **No token / PII leakage.** No token, Authorization header, GraphQL body, media byte, partner email/address, or product data appears in a lease row, a job log, or a server log. | Assert lease rows carry only `store_id/lease_key/job_id(Integer)/worker_ref/admitted_at/expires_at`; assert redaction on any error path; media bytes never logged. | Assert lease rows secret-free; the §8.2 candidate `technical_detail` shape is unchanged and carries no new PII. |
| M14 | **No `execute_business` result escapes its context.** No method returns a `result` (or a value derived from it before reconciliation) out of the `with` block; the loop owns the context (RD-P). | Source-level guard: no product-importer method returns an `execute_business` `result`; runtime guard: reconciliation observes a held lease (M2), impossible if the result had escaped a closed context. | Source-level guard: the single wrap keeps `result` inside the `with`; runtime M2 confirms the lease is held during reconciliation. |
| M15 | **No explicit main-cursor commit; flush materializes only.** `self.env.flush_all()` sends pending SQL to PostgreSQL in the current main transaction; it does not commit and does not make the write visible to another transaction. | Source-level guard: no `self.env.cr.commit(` in the product importer; assert the reconciliation is **not** visible on an independent connection until the natural handler-transaction commit (post-return). | Same guards for the customer importer. |
| M16 | **No public generic `execute()` entry remains** (closure, Prompt E). The API-client public surface is exactly `{execute_business, execute_lifecycle}`. | Source-level guard: `dir()`/public-method assertion on `shopify.connector.api.client` finds no public `execute`; no reachable `api.client.execute(` in any product file. | Same guard for any reachable `api.client.execute(` in the customer file. |
| M17 | **Test-connection / reconnect use `execute_lifecycle`.** The store lifecycle diagnostic calls route through `execute_lifecycle(purpose=…)`, never the business path and never a public `execute()`. | N/A (product domain) — asserted once at the core level: `action_test_connection`/reconnect call `execute_lifecycle`. | N/A (customer domain) — asserted once at the core level. |
| M18 | **Disconnect after terminal admission permits terminal reconciliation to finish.** A disconnect that lands *after* the terminal page is admitted (lease committed) does not abort the in-flight reconciliation; it completes with the in-memory token and releases its lease, and the controller finalizes only then. | On the terminal page: admit → commit lease → begin `_apply_import`; then a concurrent `action_disconnect` bumps generation but **waits** on the store-row update-lock / the controller counts the open lease; reconciliation finishes; lease releases; then finalize. | Same for the single customer call: an admitted call finishes reconciliation despite a concurrent disconnect. |

**[Recommendation]** M1–M10, M14–M18 are new **activation** tests authored in the
new per-domain files (`test_product_callsite_execute_business.py` /
`test_customer_callsite_execute_business.py`), plus the core-level M16/M17
assertions in the API-client / lifecycle test files (Prompt E). M11–M13 are partly
covered by re-running existing classes (§1.3) plus targeted new assertions.

### 1.2 Test construction constraints (mirror the merged discipline)

**[CORE-R2 requirement]**

- Drive the **real** `execute_business` context, `_admit`, the real lease ORM,
  real `_get_access_token`, and real `_release_lease`. The **only** seam is
  `_send` (fake in-memory `FakeResponse`, 200 OK, so `_normalize_response` runs
  for real). This mirrors `test_disconnect_quiescence.py`'s `FakeResponse`
  pattern.
- **Cross-connection visibility** (M1/M2/M8) uses genuine independent PostgreSQL
  connections (`odoo.sql_db.db_connect`), exactly as `TestGenuineRealAdmission`
  does — a `TransactionCase` single cursor cannot prove committed-lease
  visibility. Reuse that harness pattern; do **not** invent a lifecycle
  monkeypatch.
- **Generation-mismatch (M10), disconnect-ordering (M7/M8/M9/M18), and
  `execute_lifecycle` (M17)** require the Slice 2A generation bump + disconnect
  controller + `execute_lifecycle`. Under the corrected integration-staging
  strategy these are **always present** in the tree under test, because the
  staging branch is cut from a `Shopify-connector` that already merged Slice 2A
  (packet §5.4 hard prerequisite, §7 step 1). A run against a tree lacking Slice
  2A is **not** a valid Slice-2B validation and must not be recorded as one.

### 1.3 Exact existing classes to re-run unchanged

**[CORE-R2 requirement]** After each activation, re-run these to prove no
behavior regressed (byte-for-byte green):

**CORE-R2 admission foundation (Slice 1, must stay green both domains):**
`TestCallLeaseModelSchema` (7/7), `TestBusinessAdmission` (18/18), `TestApiClient`
(20/20), `TestJobEnqueue` (10/10), `TestGenuineRealAdmission` (9/9, ×3 stable) —
all in `addons/shopify_connector_core/tests/` (`test_disconnect_quiescence.py`,
`test_api_client.py`, `test_job_enqueue.py`).

**Product (Prompt P) — all PR #151 classes:** `TestProductTemplateBinding`,
`TestProductVariantBinding`, `TestProductImportMatching`,
`TestProductDuplicatePrevention`, `TestProductAttributeImport`,
`TestProductVariantGeneration`, `TestProductPriceImport`,
`TestProductMediaImport`, `TestProductRefreshAndStale`,
`TestProductRuntimePerformance` (opt-in `sc010b_performance`).

**Customer (Prompt C) — all PR #150 classes:** `TestCustomerBinding`,
`TestCustomerImportMatching`, `TestCustomerDuplicatePrevention`,
`TestCustomerFallbackPartner`, `TestCustomerMatchingScalability` (32 standard
methods), `TestCustomerMatchingBenchmark` (opt-in), `TestCustomerMatchingConcurrency`
(opt-in).

**[Fact]** Issue #157's seven post-init `res.users.notification_type` errors are
**baseline-attributed** and out of scope; they must not be "fixed" or absorbed by
Slice 2B. Record them as the known baseline artifact, exactly as PR #150/#151 do.

### 1.4 Exact-head runtime evidence to capture (on the integration-staging head)

**[CORE-R2 requirement]** The authoritative exact-head evidence is captured on the
**`claude/core-r2-slice-2b-integration` head** — after both child branches are
merged back (packet §7 step 5) and the public-`execute()` closure lands (step 6),
i.e. the head validated in step 7. Capture on Odoo.sh: build number; database
name; `git rev-parse HEAD` inside the build container (must equal the staging
head); build-time fresh-install count (`0 failed, 0 error(s) of N`); the **full
core, product, and sale** standard suite counts; the CORE-R2 admission classes
green; the new M1–M18 activation results; and the deployed multi-worker proof
(§2). No run is authoritative unless the checked-out code SHA is printed and
equals the staging head (mirror `task-core-r2-validation-results.md` §4.1
build-to-commit proof).

**[Fact]** A Prompt-P-only or Prompt-C-only **working-tree** run (local, before
merge-back) is a developer smoke check, **not** the authoritative evidence. The
integrated-head Odoo.sh run is the only evidence that counts for SRR-03. Historical
PR #150/#151 build evidence (34828304 @ `db534f8`; 34863138 @ `662e980`) is
supporting-only and is never the integrated-head evidence.

---

## 2. Deployed multi-worker / multi-server validation plan (SRR-03 / T-19)

**[CORE-R2 requirement]** SRR-03 closure requires a **genuine deployed** proof
across real workers/servers — not a `TransactionCase`. This is the merged
analysis's T-19 (Topology C) and the CORE-R2 packet's "two-server" proof
(`disconnect-quiescence-remediation-analysis.md` §19, §24;
`task-core-r2-disconnect-quiescence-packet.md` §15/§18). It runs on the **final
`claude/core-r2-slice-2b-integration` head** (packet §7 step 7) — the integrated
Slice 1 + Slice 2A + both call-site migrations + the public-`execute()` closure
(both call sites activated; the generation bump + disconnect controller +
`execute_lifecycle` present; no public generic `execute()` remaining).

### 2.1 Objective (the fourteen assertions: twelve deployed + two integrity)

A run is a **PASS** only if all of the following hold, observed on a real
deployed runtime:

1. **Worker/server A starts a business call** — A enters `execute_business` for
   an activated product/customer job and issues a real `_send` (fake transport
   seam; no live Shopify).
2. **A committed lease is visible from B** — a second worker/server B, on an
   independent connection, `SELECT`s the committed `call.lease` row A wrote before
   its `_send`.
3. **B requests disconnect** — B runs the real `action_disconnect` (Slice 2A):
   store → `disconnecting`, generation bumped, under the store-row update-lock.
4. **No new admission occurs** — after B's disconnect request, any new
   `execute_business.__enter__` for that store fails closed (`ShopifyQuiescedError`,
   generation/state gate); observe zero new lease inserts.
5. **The controller observes the lease** — the disconnect controller
   (`_run_disconnect_quiesce`), holding `FOR UPDATE` on the store row, counts the
   still-open lease A holds and keeps the store `quiescing` (does **not**
   finalize `completed`).
6. **Credentials remain until release or timeout** — the credential is **not**
   cleared while A's lease is open; it is cleared only at `completed` (zero
   leases) or on the `timed_out` path, under the controller's held update-lock.
7. **`completed` requires zero holders** — the store reaches `completed`/
   `disconnected` **only** after A releases its lease (lease count → 0). Assert no
   `completed` finalize occurs while any lease row exists.
8. **`timed_out` remains distinct** — if A's lease is still present at
   `DISCONNECT_QUIESCE_TIMEOUT`, the store finalizes **`timed_out`** (a distinct
   status), never `completed`; expiry alone never manufactures `completed`
   (direction C).
9. **The admitted call finishes with its in-memory token** — A completes its
   in-flight `_send`/reconciliation using the token snapshot it read at admission,
   even if the credential is cleared on the `timed_out` path.
10. **No later Shopify call occurs** — after the gate observes the disconnect, A
    issues no *additional* business call (for products: no page k+1 `_send`);
    B/A `_send` call-count does not increase post-refusal.
11. **Multi-server evidence identifies distinct process/backend identity** — the
    two participants are distinct OS processes / PG backends: assert distinct
    `worker_ref` (`<dbname>:<pid>`) on leases and distinct `pg_stat_activity`
    backend PIDs; for the two-server topology, two `odoo-bin` processes on one DB.
12. **Zero residue after completion** — after the run: `count(shopify.connector.
    call.lease) == 0`; no worker inside an `execute_business` context; no leaked
    backend/cursor/idle-transaction; no `ir_cron_trigger` residue; store states
    normalized.

Plus the two integrity assertions:

13. **No real customer/product data leakage** — no partner PII, product data,
    token, Authorization header, GraphQL body, or media byte in any lease row,
    job log, escalation snapshot, or server log across the whole run.
14. **No test-only lifecycle bypass** — every transition used the **real** merged
    `action_disconnect`/controller/`execute_business` path; no monkeypatch of the
    lifecycle/state mechanism and no test-only timing hook (only the `_send`
    transport seam is faked).

### 2.2 Environment requirements

**[CORE-R2 requirement]**

- **Runtime:** Odoo.sh (or another approved deployed runtime) on one PostgreSQL
  database, Odoo 19.0. Not a local `TransactionCase`.
- **Topology C (two-server):** two `odoo-bin` processes bound to the same DB
  (the merged §24 Topology C). Also run a `--workers >1` single-`odoo-bin`
  topology for the multi-worker case (INV-6).
- **Observation:** `pg_stat_activity` to observe the `FOR SHARE` (admission) vs
  `FOR NO KEY UPDATE`/`FOR UPDATE` (lifecycle/controller) lock waits and distinct
  backend PIDs.
- **Integrated tree:** Slice 1 + Slice 2A + both Slice 2B activations present. A
  run against a tree missing Slice 2A cannot prove SRR-03 (the gate/controller are
  absent).

### 2.3 Fixture strategy

- Real store rows in `connected` state with a present (fake) credential; real
  `shopify.connector.job` business jobs for the activated `product_import_sync` /
  `customer_import_sync` types, enqueued so each captures
  `expected_connection_generation`.
- Coordination between A and B via committed DB state + short bounded sleeps
  keyed on observing the committed lease (never a monkeypatched clock). A's `_send`
  is a fake that blocks on a committed signal row until B has requested the
  disconnect and the controller has polled — so the linearization window is
  actually exercised, not merely assumed.
- No live Shopify endpoint; no real merchant data — synthetic product/customer
  GIDs and synthetic partners only.

### 2.4 Transport seam vs live Shopify boundary

**[CORE-R2 requirement]** The **only** faked boundary is `_send` (the HTTP seam).
Admission, the lease ORM, the credential read, the store-row locks, the generation
gate, the disconnect controller, and lease release are all the **real** merged
code. **Live Shopify remains separately blocked** and is not part of this proof
(analysis §24 "no live Shopify"; §25 RR-7). Live/dev-store read-only Shopify
validation is a later, separately-gated activity that runs only **after** this
deployed multi-worker proof is green **and** SRR-03 is closed.

### 2.5 Exact evidence to collect

For each run, capture and store under `docs/05-qa/evidence/` (or the CORE-R2
validation record): Odoo.sh build number; DB name; `git rev-parse HEAD` in the
container (== integrated head); the two/N distinct backend PIDs and lease
`worker_ref`s; the committed-lease-visible-from-B timestamp; the disconnect
request + generation-bump audit; the controller poll snapshots
(`disconnect_open_lease_count`, `disconnect_oldest_admitted_at`); the finalize
outcome (`completed` vs `timed_out`) with the lease count at finalize; the
`_send` call-count before/after the disconnect (proving no later call); the
end-state residue scan (`count(call.lease)==0`, no leaked backend/cursor/idle txn);
and a redaction scan of all logs/rows for token/PII/body/media.

### 2.6 Timing bounds

- `MAX_CALL_LIFETIME`, `DISCONNECT_QUIESCE_TIMEOUT`, `POLL_DELAY` are tuning-only
  constants (analysis §26). The proof must exercise **both** the pre-timeout
  quiescing→`completed` path (A releases before timeout) **and** the
  past-timeout →`timed_out` path (A holds past `DISCONNECT_QUIESCE_TIMEOUT`).
- Completion is an SLA under a healthy scheduler, **not** a wall-clock guarantee
  (analysis §13); the *safety* property (the epoch gate refusing new admissions)
  is immediate and must be asserted independently of scheduler timing.
- `POLL_DELAY ≥ 1 minute` (the `_trigger` granularity); assert no busy-loop
  re-trigger of the same store.

### 2.7 Failure taxonomy (what a red run means)

| Symptom | Interpretation |
| --- | --- |
| A new lease inserted after B's disconnect request | Admission gate leaked — INV-2 violation; **blocker**. |
| `completed` finalize while a lease row exists | Quiescence detection wrong — INV-3 violation; **blocker**. |
| `timed_out` collapsed into `completed` (or vice-versa) | Direction-C distinctness broken; **blocker**. |
| Credential cleared while A's lease open | Credential-lifecycle violation; **blocker**. |
| A second `_send` after disconnect observed | Phase-C "zero further calls" violated; **blocker**. |
| Token/PII/body/media in any row or log | Redaction/secret-free violation; **blocker**. |
| Same-PID "two workers" / monkeypatched lifecycle | Not a genuine deployed proof; **invalid run**, re-do. |
| Lease residue / leaked backend after completion | Cleanup violation; **blocker**. |

### 2.8 Three-run stability requirement

**[CORE-R2 requirement]** Each topology (multi-worker `--workers>1`, and
two-server Topology C) must pass **three consecutive clean runs on the exact
head**, with zero residue each time — mirroring `TestGenuineRealAdmission`'s ×3
stability discipline and the Task-010B/011B ×3 concurrency stability. A single
green run is not sufficient.

---

## 3. SRR-03 closure criteria

**[CORE-R2 requirement]** SRR-03 (end-to-end disconnect quiescence) may be marked
**CLOSED** only when **every** box below is satisfied. **This documentation
session does not and cannot close SRR-03** — it defines the criteria only.
SRR-03 stays **OPEN**.

- [ ] **C1 — Slice 2A merged / runtime-green.** The disconnect controller,
      `disconnecting` state, two-phase `action_disconnect`, the store-row
      update-lock + `connection_generation` bump on every generation-changing
      transition, Direction-C `timed_out`/`completed` finalization + credential
      clear + lease cleanup, and the `ShopifyQuiescedError → skipped` dispatcher
      routing are merged and runtime-green.
- [ ] **C2 — Product call-site migrated (loop-owned RD-P) / integrated-head
      green.** Prompt P applied per RD-P; the product handler issues every Admin
      **page** call through `execute_business` (loop-owned context); no result
      escapes its context (M14); M1–M18 (product column) green; all PR #151 classes
      green — verified on the **integration-staging head** (§1.4), not an isolated
      product head.
- [ ] **C3 — Customer call-site migrated (RD-C) / integrated-head green.** Prompt
      C applied per RD-C; M1–M18 (customer column) green; all PR #150 classes
      green — verified on the integration-staging head.
- [ ] **C4 — Multi-worker / multi-server proof green.** §2 deployed plan passes
      all fourteen assertions, in both topologies, ×3 stable (§2.8), on the
      integration-staging head.
- [ ] **C5 — Public-`execute()` closure complete (Prompt E).** The
      public-`execute()` is removed/privatized on the staging branch (packet §6b);
      the API-client public surface is exactly `{execute_business,
      execute_lifecycle}`; `action_test_connection`/reconnect use `execute_lifecycle`
      (M17); static guards prove zero reachable `api.client.execute(` in any
      production file and a `_`-prefixed transport seam (M16). This is a **Slice-2B**
      deliverable, not a deferred item.
- [ ] **C6 — No unguarded Shopify business call site.** Every credentialed
      Admin-API call flows through `execute_business` (admission-gated). Media CDN
      GETs are excluded by definition (tokenless, non-business — §1 M13 asserts
      they leak nothing).
- [ ] **C7 — Lifecycle and timeout tests green.** The Slice 2A lifecycle-matrix,
      `disconnecting`-refusal, controller-quiescence, and direction-C
      `timed_out`/`completed`/credential-clear tests (analysis §24 T-1…T-14) are
      green on the integrated tree.
- [ ] **C8 — Ordered rollback verified.** The zero-holders-first ordered rollback
      (`task-core-r2-disconnect-quiescence-packet.md` §17; step 4 asserts
      `count(call.lease)==0` **and** no worker inside an `execute_business`
      context) is demonstrated/tested where feasible.
- [ ] **C9 — Single controlled integration merge; PR #150/#151 subsumed.** The
      protected, validated `claude/core-r2-slice-2b-integration` head reaches
      `Shopify-connector` via **one** integration PR (packet §7 step 8);
      **PR #150/#151 were never merged directly into `Shopify-connector`** while
      unguarded, and are closed as subsumed/merged **only after** that integration
      PR is accepted and merged. No unguarded domain handler ever landed on
      `Shopify-connector`; no shared CORE-R2 commit was double-applied; no
      sibling-branch history was duplicated; no explicit main-cursor commit exists
      (M15).
- [ ] **C10 — Final live-read validation authorized separately.** Live/dev-store
      read-only Shopify validation is a **separate** gate, authorized by ChatGPT
      only **after** C1–C9 are green. It is **not** part of SRR-03 closure and is
      not performed until explicitly authorized.

**[Fact]** As of this packet: C1 unmet (Slice 2A / PR #160 unmerged and not
runtime-green), C2/C3 unmet (migrations not implemented), C4 unmet (no deployed
proof), C5–C9 unmet, C10 not authorized. **SRR-03 = OPEN.** Issue #157 remains a
separate investigation throughout.

---

## 4. References

- `docs/03-architecture/disconnect-quiescence-remediation-analysis.md`: §5
  (INV-2/INV-3/INV-2L/INV-6), §6 (Phase A/B/C), §10 (lease + direction C), §13
  (controller scheduling), §14, §16 (timeout/escalation), §19 (multi-host), §23
  (ordered rollback), §24 (T-1…T-14, T-19 Topology C; Method constraints), §25
  (RR-7 live-proof), §26 (tuning constants).
- `docs/07-implementation-plan/task-core-r2-disconnect-quiescence-packet.md`:
  §12 (direction-C), §15 (concurrent proofs incl. two-server), §17 (ordered
  rollback), §18/§19 (DoD / future-PR requirements).
- `docs/05-qa/task-core-r2-validation-results.md`: §3 (proof→test mapping), §4.1
  (build-to-commit discipline), §9 (RR-C two-server deferred, RR-F single-DB).
- `docs/05-qa/task-010b-validation-results.md` (@ `e4669aa`);
  `docs/05-qa/task-011b-validation-results.md` (@ `10d0034`) — historical,
  supporting-only.
- PR #160 (`b3d23cb`, Slice 2A, draft, no runtime-green claimed — hard
  prerequisite); control-room review `4690659767` (REVISE — the correction driving
  Revision 2).
- Companion:
  `docs/07-implementation-plan/task-core-r2-slice-2b-callsite-runtime-packet.md`;
  `docs/07-implementation-plan/task-core-r2-slice-2b-handoff.md`.
