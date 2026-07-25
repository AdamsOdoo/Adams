# Pre-Wave-5 repository debt discovery

> **Status:** `[Fact — audit executed]` for the discovery; `[Decision — implemented]`
> for the corrections marked FIXED. **Date:** 2026-07-25.
> Covers workstream 8 of the pre-Wave-5 stabilization gate: TODO/FIXME markers,
> skipped or structurally non-executing tests, stale compatibility workarounds,
> known-failure classifications, missing CI/lifecycle/security coverage, and
> untracked P0/P1/material-P2 defects.
> **Nothing here closes an issue.** Exact-SHA Odoo.sh evidence and independent
> review remain outstanding for every item.

## 1. Method

Static sweep of `addons/**` plus **execution** of every suite on a local
disposable Odoo 19 + PostgreSQL 16.13 runtime. Execution matters: three of the
findings below (D-4, D-5, D-6) are invisible to static analysis and only appear
when the code actually runs.

## 2. Findings

| ID | Area | Finding | Severity | Status |
| --- | --- | --- | --- | --- |
| D-1 | TODO/FIXME markers | **Zero** `TODO`, `FIXME`, `XXX`, `HACK` or `WORKAROUND` markers across all `addons/**` `.py`/`.xml`/`.csv`. | — | Clean |
| D-2 | Dead test files | Every `test_*.py` in all five modules is imported by its package `__init__.py`. No structurally dead test file. | — | Clean |
| D-3 | Test phase | 79 test classes ran `at_install` and failed a warm `-u` with NOT NULL violations. | High | **FIXED** — issue #193/#157 |
| D-4 | Fixture integrity | `test_pii_least_privilege` back-dated `create_date` through `create()` values, which Odoo honours **only while the registry is loading**. At `post_install` the back-date was silently dropped and the retention assertion stopped testing what it claimed. | Medium | **FIXED** |
| D-5 | Test residue | `test_inventory_concurrency` left committed `stock.location`, `product.template`, `product.product`, `res.users` and `res.partner` rows behind. | Medium | **FIXED** — issue #198 |
| D-6 | Non-executing tests | **8 test classes carry `-standard` and never run in a normal `--test-enable` pass**, including four *genuine concurrency proofs*. A "full suite green" claim silently excluded them. | **Material P2** | **FIXED** — see §3; the runner and CI now execute them automatically |
| D-7 | Harness never executed | The fulfillment external-process harness had **two defects that made it fail on first run**, proving it had never actually been executed. | **Material P2** | **FIXED** — see §4 |
| D-8 | Cross-company reads | 8 of 10 company-scoped connector models had no record rule. | Material P2 (for UAT/RC) | **FIXED** — issue #197, see the SEC-3 audit |
| D-9 | Customer-facing roles | The two SEC-2 roles did not exist; only the four internal capability groups. | Blocks U1 | **FIXED** — issue #196 |
| D-10 | No CI | `.github/` absent on every release-relevant branch (DEC-041 E5); all evidence manually produced. | Material P2 | **FIXED** — DEC-041 D8; see §3 for the two defects the first version shipped with |
| D-11 | No performance baseline | No reproducible benchmark existed to compare two SHAs. | Blocks perf acceptance | **FIXED** — issue #199 |
| D-12 | Environment-gated skips | Two tests skip on capability, not on defect: `test_real_process_death_harness` ("opt-in outside Odoo.sh") and `test_ui_tours.test_navigation_tour` ("websocket-client module is not installed"). | Low | **Open — tracked** |
| D-13 | `store.settings` company pointers | `order_company_id` may point at a company the acting administrator is not in. Product question, not a defect. | Low | **Open — tracked** |

## 2b. Findings added by the 2026-07-25 control-room correction

| ID | Area | Finding | Severity | Status |
| --- | --- | --- | --- | --- |
| D-14 | CI completeness | The first CI/runner shipped with `TEST_TAGS` defaulting to empty and the workflow calling the script with no `--tags`, so **the eight `-standard` classes were still never executed continuously**. D-6 and D8 were reported fixed while the mechanism that was supposed to fix them excluded exactly the tests in question. | **Material P2** | **FIXED** — the runner now runs a third pass over the complete tag set by default; skipping is opt-*out* only |
| D-15 | Odoo pin | `ODOO_REF=19.0` is a *moving branch*, and the Actions cache was keyed `odoo-src-19.0`, so a restored cache could execute an arbitrary older Odoo commit forever while every artifact still read "19.0". Neither is a pin. | **Material P2** | **FIXED** — `tools/odoo-pin.txt` holds an immutable SHA, the runner verifies the checkout against it on every run and aborts on mismatch, and the cache key is `hashFiles('tools/odoo-pin.txt')` |
| D-16 | PERF-0 validity | `pg_stat_statements.total_exec_time` was reported as `lock_wait_ms_delta`. It is statement **execution** time, not lock-wait time; a workload that never blocks still accumulates it. The `lock_contention` scenario was also single-process and uncontended, so it could only ever measure the uncontended floor. | **Material P2** | **FIXED** — renamed to `sql_exec_time_ms_delta`; genuine two-connection blocking contention added, with `wait_event` observation and a SKIP-LOCKED comparison |
| D-17 | PERF-0 coverage | The order, inventory and fulfillment scan/reconciliation workloads required by #199 were absent, and the scan scenarios would have searched empty tables. | Material P2 | **FIXED** — three scan scenarios plus a reconciliation sweep, each seeding a real dataset sized from `--batch` |
| D-18 | PERF-0 residue | The post-teardown check looked at the store row and three tables. A benchmark can leave a credential, lease or binding behind and still report "clean", silently changing the dataset for the next run. | Medium | **FIXED** — 16-table sweep, FK-safe teardown including the circular job/attempt pointer |
| D-19 | SEC-3 ownership | Nine control-plane models were classified NEUTRAL, leaving stores, credentials, settings, locations, jobs, logs, attempts and leases cross-company readable. `order_company_id` was a second, independent ownership selector. | **Material P2** | **FIXED** — store-rooted ownership, fail-closed rules, `order_company_id` constrained to agree with the store; see the SEC-3 audit |
| D-21 | Self-inflicted, found by testing | Three defects in this round's OWN corrections: the dirty-worktree warning called `log()` before it was defined (silent); a bad Odoo pin aborted with a raw git error instead of the diagnostic; and the rewritten summary heredoc left the old JSON body behind, so a fully green run exited 127. Each was found by *running* the guard rather than assuming it worked. | Medium | **FIXED** |
| D-20 | Measurement window | `test_ui_performance` charged a pending ORM flush from its own fixture to the dashboard call, so a newly added stored field made the dashboard look super-linear (17 → 19 queries, both `UPDATE ... SET company_id`). | Low | **FIXED** — the fixture flushes before measurement; the assertion stays strict equality |

## 2c. Findings added by the 2026-07-25 exact-head/evidence-integrity round

Every entry here was found by *running* the thing, not by reading it.

| ID | Area | Finding | Severity | Status |
| --- | --- | --- | --- | --- |
| D-22 | CI identity | GitHub Actions run 30153827606 succeeded and its artifact recorded `connector_sha: 60ea6690…` — GitHub's **synthetic pull-request merge commit**, not PR #203's head `156a4a74…`. `actions/checkout` defaults to `refs/pull/N/merge` on a `pull_request` event: a real commit, in no branch, that nobody reviewed. Every number in that artifact was accurate about a commit the PR does not contain. | **Material P2** | **FIXED** — the workflow checks out `github.event.pull_request.head.sha`, and the runner now *verifies* its checkout against the declared source head and aborts on mismatch rather than publishing |
| D-23 | PERF-0 residue | `build_domain_dataset` created `res.partner`, `product.template` (and therefore `product.product`), `sale.order` and `sale.order.line`; the residue sweep covered store-scoped connector tables only. "Zero residue across all scenarios" was true about the tables it looked at and false about the dataset. | **Material P2** | **FIXED** — every row is tracked by exact id, torn down child-before-parent, and re-verified from a new transaction |
| D-24 | PERF-0 residue, second layer | Tracking only what the harness creates *explicitly* is not enough. `_create_attempt_intent` mints attempts through the Layer-2 seam, `_system_append` writes job logs, and the admission scenarios exist precisely to make the real cron enqueue jobs — 350 attempts and 7 jobs per scenario, all untracked. The first honest teardown failed on an FK from an untracked attempt. | **Material P2** | **FIXED** — rows above a pre-run per-table watermark are adopted and deleted by exact id; a watermark cannot reach a pre-existing row |
| D-25 | PERF-0 residue, third layer | `product.value` (stock_account's valuation layer) is written as a **side effect** of creating a product and is not removed with its template — 50 rows per scenario, invisible to every hand-written table list including this file's own. Found only by the whole-database `id > watermark` sweep. | Medium | **FIXED** — swept, adopted, deleted by exact id; the sweep is what makes a future fixture unable to escape quietly |
| D-26 | PERF-0 labels | `order_scan` / `inventory_scan` / `fulfillment_scan` read as reconciliation throughput while their bodies performed a `search` and a `read`. | Medium | **FIXED** — renamed `*_projection`, and the genuine network-free cron admission paths added as separate scenarios |
| D-27 | PERF-0 contention | The blocked actor was raw SQL `FOR UPDATE`. The connector's production claim path is `_claim_for_dispatch` → `try_lock_for_update` → `FOR UPDATE SKIP LOCKED`, which does **not** block. Measuring a blocking `FOR UPDATE` and labelling it connector acquisition described a code path the connector never takes. | **Material P2** | **FIXED** — the production claim is exercised against a held row and its **no-wait** behaviour reported as the production result; the raw blocking experiment is retained, relabelled `database lock calibration` |
| D-28 | SEC-3 test honesty | `test_sec3_store_ownership.py` described broader coverage than it performed: `CONTROL_PLANE_MODELS` was consumed by no test, `test_every_control_plane_model_is_isolated` exercised 3 of 8, and a test named for mutation attempts created none. | **Material P2** | **FIXED** — one authoritative inventory now drives every test, and a completeness guard fails when a durable store-scoped model has no entry |
| D-29 | SEC-3 same-store gap | Company equality cannot express same-**store** agreement, because one company may own several stores. A row in store A pointing at a connector parent in store B passes every company check. Genuinely open relations: variant→template binding, evidence→order binding, evidence→fulfillment binding, evidence line→sale line, and `job.superseded_by_job_id` — the last found by the new completeness guard, not by reading the model. | **Material P2** | **FIXED** — `shopify.connector.scope.mixin`: ORM constraints for new rows, a non-guessing quarantine for historic ones |
| D-30 | SEC-3 structural closure | Three declared relations *cannot* disagree, because the child's store is a stored `related` field through that same relation (`job.log.job_id`, `mutation.attempt.job_id`, `evidence.line.evidence_id`). Recorded as structurally safe rather than claimed as enforcement — a constraint there could never fire. | — | Recorded |
| D-31 | Registry import order | Odoo builds a module's models in *import* order, and `shopify_connector_api_client` imports `shopify_connector_mutation_attempt` at module level. Adding a mixin anywhere but first in `models/__init__.py` fails the whole registry load with "inherits from non-existing model". | Low | **FIXED** — the mixin is imported first, with the reason recorded at the import |

### Non-blocking follow-ups recorded, not fixed in this round

| ID | Finding | Why not now |
| --- | --- | --- |
| D-32 | The per-record reconciliation **handlers** (`_handle_order_import_scan`, `_handle_inventory_push_sync`, `_handle_fulfillment_reconciliation_check`) all perform Shopify reads, so no local harness can measure them. PERF-0 measures the admission paths and the local ledger computation only. | Measuring them needs either a live store or a sanctioned transport fake. Inventing a fake to manufacture a number would make the baseline look more complete than it is. **Issue #199 stays open.** |
| D-33 | `shopify.connector.call.lease.job_id` is an `Integer`, not a `Many2one`, so there is no FK and no relational scope check is possible on it. | Changing a persisted column's type is a schema migration well outside an evidence-integrity correction. Recorded for the Wave-5 schema review. |
| D-34 | `product.value` teardown is enumerated by model name. A future Odoo version renaming that model would silently drop it from the explicit teardown — though the whole-database sweep would still catch the residue and fail the run. | The sweep already fails closed on it, so this is a diagnostics nicety, not a correctness gap. |

## 3. D-6 — the eight non-executing classes

Classification: **Fact**, confirmed by executing the standard suite and grepping
its log: none of the six custom tags appears.

| Class | Tag required to run it |
| --- | --- |
| `TestProductCallSiteLifecycleGenuine` | `shopify_connector_product_callsite_lifecycle` |
| `TestProductRuntimePerformance` | `sc010b_performance` |
| `TestCustomerMatchingBenchmark` | `shopify_connector_customer_matching_benchmark` |
| `TestCustomerMatchingConcurrency` | `shopify_connector_customer_matching_concurrency` |
| `TestCustomerCallsiteLeaseVisibilityGenuine` | `shopify_connector_customer_callsite_lifecycle` |
| `TestCustomerCallsiteRaceAGenuine` | `shopify_connector_customer_callsite_lifecycle` |
| `TestCustomerCallsiteRaceBGenuine` | `shopify_connector_customer_callsite_lifecycle` |
| `TestOrderDiscoveryConcurrencyGenuine` | `shopify_connector_order_discovery_concurrency` |

`-standard` is a legitimate Odoo mechanism for expensive or process-spawning
tests, and these are correctly tagged. The debt is **not the tag** — it is that
nothing ever ran them, so their status was unknown while the acceptance matrix
recorded suites as green.

**Executed 2026-07-25**, all six tags together: **18 tests, 1 failed** on first
execution, then **0 failed, 0 errors of 18** after the correction in §5. That
failure had been latent for the entire life of these tests.

**Correction:** `tools/run_connector_suite.sh` and the CI workflow are the
standing mechanism for running the standard suite; the non-standard tags must be
named explicitly and are listed here so they cannot be forgotten again. Wiring
them into a scheduled CI job is a follow-up, recorded as still open.

## 4. D-7 — the fulfillment harness had never been run

The 9-scenario external-process fulfillment harness failed 2 scenarios on its
first genuine execution. Both are **harness defects, not production defects** —
in each case production behaved correctly and the harness was wrong:

1. **`operation_scope_serialization`** drove a job `queued -> succeeded`
   directly. `LEGAL_JOB_TRANSITIONS` (`shopify_connector_job.py` L23-L43) routes
   every terminal success through `running`, so production raised
   *"Illegal Shopify job transition: queued -> succeeded"*. The harness now
   drives the real path. Had it short-circuited the state machine, the scenario
   would have been proving scope release against a transition production never
   performs.
2. **`reconciliation_replacement_race`** cleanup hit
   `ForeignKeyViolation` on `shopify_connector_job_mutation_attempt_id_fkey`.
   The job/attempt FK pair is **circular** — `mutation_attempt.job_id -> job`
   and `job.mutation_attempt_id -> attempt` — so neither side can be deleted
   first. The cleanup now clears the reverse pointer before deleting.

**Inference.** A harness that fails immediately when first executed had not been
executed. This is consistent with `mvp-program-state.md` §1, which records the
Wave 3 external-process harness as "explicitly infrastructure-deferred, not
claimed executed" — the record was honest; the harness was simply unproven.

**After correction:** all 9 fulfillment scenarios and all 3 core scenarios pass
with genuinely distinct OS process IDs per worker and zero residue.

## 5. The teardown FK-safety family

Three independent instances of one root cause were found, which is why it is
called out separately rather than as three unrelated bugs:

| Where | Defect |
| --- | --- |
| `test_inventory_concurrency` (#198) | committed business rows never removed |
| fulfillment harness (D-7.2) | circular job/attempt FK deleted in the wrong order |
| `test_customer_matching_scalability` | `_durable_cleanup` removed only the rows the test creates *deliberately*, leaving the ones production creates as a **side effect** — a credential, a mutation attempt, a cached location, and store-scoped job logs — so deleting the store raised `ForeignKeyViolation`. Removing those then raised `AccessError`, because the attempt/log/credential models are deliberately undeletable through the ORM; teardown now uses store-scoped SQL for exactly those three. |

**Recommendation (not yet a decision).** Any fixture that commits should own an
exact-id, FK-complete teardown and a residue assertion. The pattern now exists
in `TestInventoryConcurrencyResidue` and can be lifted into a shared helper when
a fourth instance appears.

## 6. Coverage still missing

- **Exact-SHA Odoo.sh runtime** for this stabilization head. The local runtime
  is a faithful reproduction, never a substitute.
- **Live Shopify** (Gate D / CV-013, issues #185/#186/#200) — deferred by
  product-owner ruling until the Wave-5 candidate freezes. No Shopify operation
  occurred in this audit.
- **UI-delta SEC-3** — U1 does not exist yet.
- **A first green GitHub Actions run.** The workflow is corrected and
  syntax-validated, but this environment cannot execute Actions; until a run
  exists on the corrected head, CI is `IMPLEMENTED — RUNTIME PENDING`, not
  proven.
- **Driven browser/visual UAT** — unchanged, still deferred.
