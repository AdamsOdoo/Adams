# Native campaign failure triage — 9 September 2026

This is a diagnosis record. Document 13 owns current execution state; document 16 owns the remaining delivery program. A correction below is not a native pass until executed on its identified candidate. UI redesign remains parked.

## Verified input

- Source: `695aa801fbc04ea78376bf675f81451207577ef8`.
- [Native campaign 34320216972](https://github.com/AdamsOdoo/Adams/actions/runs/34320216972), job `102365032132`, failed. [Policy campaign 34320216952](https://github.com/AdamsOdoo/Adams/actions/runs/34320216952) passed.
- Detailed artifact `10093285071`: SHA-256 `6c70fe20efa913e316c3ec6dc577ae6ce7049cebcfac970de1241d2a104cadcb`. Downloaded archive hash and embedded source/head metadata were verified. Previous artifact-download failures are resolved; do not treat detailed native logs as inaccessible.
- Fresh and warm: **58 failures, 685 errors, 2,999 tests** each. Lite/Full candidate installations pass. Old-core W2: 10 errors of 18 tests. Nonstandard lane: 4 failures/33 errors of 70 tests. Migration and browser gates also fail.
- The [machine-readable fresh-log index](evidence/native-695aa801-failure-index.json) accounts for **all 743 failure/error headers**, including 31 subtests. The first extraction counted 712 ordinary headers; those counts must not be mixed with the complete index.

## Root families and correction order

| Family | Evidence and implication | Next proof |
| --- | --- | --- |
| Operational fixture activation | **667/743 headers** stop at the active-store admission guard (648 ordinary cases plus 19 subtests). Connected credentials and active execution are separate states. Shared and independent-cursor fixtures must declare both where their scenario requires operational work. | Affected native classes, including draft/paused/retired negative controls and genuine barriers. Do not remove or broaden the production guard. |
| Actor and protected-surface fixtures | Recovery mode setup uses an actor without connector-admin membership; four read-provider calls lack connector-user identity. Settings/credential test setup also predates protected creation/write surfaces. | Use real scoped actors and owning fixture surfaces; preserve denial and no-side-effect assertions. |
| Store-admin DTO serialization | A nested lifecycle mapping contains raw `AllowedActionDTO` dataclasses, rejected by the immutable JSON-shaped mapping contract. | Serialize nested actions using the existing serializer; native projection must JSON-encode and expose identical action data without credentials. |
| Structural tests after extraction | Mutation documents and transport responsibilities moved into typed gateways. Old assertions inspect former files; source guards and explicit sudo inventories also report new paths. | Inspect actual gateways and permission boundaries before updating exact inventories. Preserve document/directive, no-bypass and authorization assertions. No blanket allowlists. |
| Security coverage and lineage | SEC-3 omits newer durable store-scoped models and connector relations. Historic SQL fixtures omit required activation fields. A recovery fixture violates job/attempt/run lineage. | Extend row builders and relation proofs, preserve historic isolation, and correct authoritative fixture lineage. These are open security gates. |
| Odoo-native data/API assumptions | An old `groups_id` field name, callable field defaults, and duplicate empty variant combinations stop tests. | Match the pinned Odoo model API and valid business fixtures; execute the intended assertions. |
| Scheduled/webhook/UI cascades | Several tests observe no queued child, manual review, stale-reason mismatch or tour timeout. Activation may explain these, but their own assertions have not yet passed. | Rerun after activation repair; keep each residual failure open until its actual cause is established. |
| Old-core W2 compatibility | Current runtime schema is absent when W2 installs over the frozen old W1 origin without upgrading it. Isolated column additions would conceal the broader ownership problem. | Prove the supported bridge and owning migrations against the original fixture; never replace it with an upgraded dependency and call it a mixed-version pass. |

## Execution discipline

1. Repair shared setup roots in one coherent batch, keeping operational and intentionally blocked stores distinct. Preserve independent-cursor fixtures and concurrency barriers.
2. Run a focused native prerequisite with the pinned Odoo checkout, existing module closure and disposable PostgreSQL database. Verify source, selected classes, nonzero execution, failures/errors and skips. Save its own logs and summary.
3. The unchanged full campaign runs only after that prerequisite succeeds. Focused success is diagnostic evidence, never a replacement for fresh/warm, Lite/Full, old-core W2, migration, nonstandard, browser or live qualification.
4. Diagnose residual assertions from exact-candidate logs. Do not equate falling raw counts or passing dependency-free checks with runtime qualification.

## Non-activation headers by class

These 76 headers include downstream effects and structural drift, not 76 proven independent defects. Exact case names and log line numbers are in the index above.

| Class | Headers |
| --- | ---: |
| `TestBatch2ProductJourneys` | 1 |
| `TestExportSourceGuards` | 12 |
| `TestFulfillmentModeSwitch` | 2 |
| `TestFulfillmentReaderPagination` | 2 |
| `TestFulfillmentScans` | 2 |
| `TestFulfillmentSourceGuards` | 1 |
| `TestInventoryPushMechanics` | 2 |
| `TestInventoryTriggers` | 1 |
| `TestMutationRecovery` | 4 |
| `TestMutationSourceGuards` | 5 |
| `TestOrderScanTriggers` | 1 |
| `TestP15StoreAdmin` | 1 |
| `TestProductContractRepair` | 2 |
| `TestProductScanP10` | 1 |
| `TestProductScanProducer` | 1 |
| `TestSec2Roles` | 1 |
| `TestSec3HistoricRows` | 3 |
| `TestSec3InventoryCompleteness` | 2 |
| `TestSec3ModelMatrix` | 1 |
| `TestShopifyConnectorFulfillmentWebhook` | 3 |
| `TestShopifyConnectorInventoryWebhookW3` | 6 |
| `TestShopifyConnectorProductWebhookW2` | 2 |
| `TestShopifyConnectorSaleWebhook` | 6 |
| `TestShopifyConnectorWebhookP11` | 1 |
| `TestShopifyConnectorWebhookW1` | 3 |
| `TestTaxDecisionRoute` | 1 |
| `TestUiActions` | 2 |
| `TestUiB2ProductTours` | 1 |
| `TestUiB2SaleTours` | 1 |
| `TestUiSourceGuards` | 1 |
| `TestUiU2SaleActionTours` | 1 |
| `TestUiVisibilityMatrix` | 1 |
| `TestV2MutationRuntime` | 1 |
| `TestV2RecoveryCommands` | 1 |

## Focused experiment 1 — source 768eadbed92c1552b070d2b8302724208a1a8467

[Run 34327810048](https://github.com/AdamsOdoo/Adams/actions/runs/34327810048) completed the prerequisite in **233 seconds**: **401 tests, zero assertion failures, nine errors, no selected skips or missing classes**. The full campaign was correctly not executed. [Structured summary](evidence/native-focus-768eadb-summary.json). Artifact `10094634993` checksum: `3779eb7d54e70e200688a18f2fc200f249f4d985387e8dcc6141be8923483b01`. Its source, pin, clean checkout and checksum were verified.

Seven selected classes reported no failures/errors: BusinessAdmission, InventoryPushMechanics, ProductMatchDecision, V2RuntimeAdapter, P15StoreAdmin, JobEnqueue and JobDispatch. This qualifies only those executed class scenarios on this source; the full domain/release gate is still open.

Residuals:

- Seven ProductImportMatching errors still hit activation: direct job creation and two alternate helpers bypassed the earlier `_import_job` fix. The initial fixture attribution overstated coverage. Move operational activation to class setup while retaining domain-disabled/missing-settings negatives.
- Two MutationRecovery errors hit the C2 scope fence only for the secondary copied store. Preserve the scope fence and diagnose the fixture/identity mismatch before considering any correction.

Separate migration review found that the existing P15 post-migration runs after the ORM fills the new activation column with `draft`. The pinned [field initialization](https://github.com/odoo/odoo/blob/30bde9ff758834a4912c5ae55843d3a7dad849f1/odoo/orm/fields.py) calls [model `_init_column`](https://github.com/odoo/odoo/blob/30bde9ff758834a4912c5ae55843d3a7dad849f1/odoo/orm/models.py), so the post-hook's NULL-only backfill cannot identify legacy connected stores. A core-owned pre-migration and PostgreSQL regression are prepared for the next source. They preserve explicit paused/retired/draft values and do not claim to reconstruct intent on databases already upgraded by the faulty path. They were not part of experiment 1 and need native plus genuine-upgrade proof.

## Focused experiment 2 — source 01801efdf75a7cf22a7b2b84295d15ab9f3c61c9

[Run 34329325518](https://github.com/AdamsOdoo/Adams/actions/runs/34329325518): **402 tests, two failures, zero errors, no selected skips or missing classes**, in 334 seconds. [Structured summary](evidence/native-focus-01801ef-summary.json). Verified artifact `10095310384`, SHA-256 `d047bf786f74e170ed061246eb9119da438aa025c7c2c96476668096ab228e53`. Policy run `34329325508` passes; the full campaign did not execute.

The seven product fixture errors are resolved, and the added PostgreSQL migration regression passes. The two precise C2 diagnostics both report `store_state`: each copied secondary fixture is `setup_incomplete` while activation is `active`; run state, runtime mode, companies and both generation triples agree. Correct only those fixture connection states through the owning lifecycle surface. Retain the C2 fence and diagnostic precondition.

The next prerequisite adds the six SEC-3/runtime/command-result classes and mutation-source guards. Its larger scope is not numerically comparable to this 402-test run. SEC-3 repairs add three missing durable models to the matrix and three job-parent relations to the historic quarantine sweep. The five previously identified mutation-source guard failures are extraction drift under separate correction; keep that class in the prerequisite so a known unresolved boundary check cannot launch the expensive full campaign.

## Focused experiment 3 — source e087d961c8cf24091d313b9331a150f12cb539dc

[Run 34330476348](https://github.com/AdamsOdoo/Adams/actions/runs/34330476348): **490 tests, six failures, zero errors, no selected skips or missing classes**, in 232 seconds. [Structured summary](evidence/native-focus-e087d961-summary.json). Verified artifact `10095706407`, SHA-256 `3b95716bbdd61bdd94a4211a6313361d8163b33aecf75b9973967f992f2e8e97`. Policy `34330476419` passes; full campaign did not execute.

All six added SEC-3/runtime/command-result classes pass, including the new historic cross-store runtime quarantine regression. Both copied-store C2 preconditions now pass. Five failures remain in the previously identified mutation-source guard extraction checks. The sixth is the foreign C1 fixture's copied job defaulting to `draft`; it never constituted the intended older running candidate. Seed running state, timestamp and owner explicitly and assert that fixture before the sweep, preserving the post-sweep foreign-state assertions.

The next candidate also corrects two original-campaign fixture assertions: the webhook non-admin user uses Odoo 19's `group_ids` (verified against the pinned res.users source), and mutation configuration default is checked through `default_get` instead of comparing the framework-normalized callable to integer zero. Add both complete classes to the prerequisite; no production permissions/defaults change.

The original SEC-2 failure is a production composition defect, not a stale fixture: sale's `create` inserted `order_company_id` before core's closed structural validator. Move that derivation into a private cooperative preparation hook invoked by core only after original nonroot input and service capability validation. No context bypass or expanded caller allowlist is introduced. Native regressions cover ambient company A/store B, rejected caller-supplied company, unchanged input dictionaries, root two-company batch derivation and explicit mismatch refusal. Separate read-only review found no issue. The next prerequisite adds SEC-2 and sale company isolation along with the cancellation class whose synthetic uncertain evidence was missing its owning run/configuration identity (21 classes total).

Next packet (read-only diagnosis, not yet corrected): product-export gateways/domain support duplicate the canonical API-version literal; fulfillment's exact model-file inventory omits three existing P06/P07 adapters; the W1 subscription projection test searches the former model source instead of its two owning gateway documents. Preserve exact file/operation boundaries when correcting them. Further export subtest failures still need complete reconciliation; do not equate this partial diagnosis with a passing class.

## Focused experiment 4 — source 7c4b89bce6c1d6599b898e7e57719c4b41240d4f

[Run 34332566803](https://github.com/AdamsOdoo/Adams/actions/runs/34332566803): **553 tests, one failure, one error, no selected skips/missing classes**, 260 seconds. [Structured summary](evidence/native-focus-7c4b89bc-summary.json). Artifact `10096536931`, verified SHA-256 `75542cb5e389e1b9410953f3627065fd024c4957dbf73a1b0d2e17a17fa53b9e`. Full campaign did not execute.

Mutation-source guards, the prior C1 fixture, webhook actor fixture, default assertion, original SEC-2 model-boundary regression, and root mixed-company settings regression pass. Remaining error: the new nonroot company-derivation regression forgot that shipped settings ACLs deny create entirely. Like the existing SEC-2 test, it needs a temporary test-only ACL to reach the deeper model boundary. No production ACL changes are warranted. Earlier wording implying demonstrated broken merchant onboarding was too broad: current canonical/setup services already perform controlled elevation; the ordering defect was proven at the nonroot internal extension boundary under the original test's hypothetical create ACL.

Remaining failure: cancellation reports zero protected uncertain jobs after the synthetic attempt's run/configuration identity was corrected. Trace the raw SQL candidate-selection boundary against pending ORM stored-field updates before deciding whether it is a production defect or further fixture mismatch.

Cancellation review confirms missing ORM/SQL synchronization: the first raw job query sees pending stored-related company/state fields before the later ORM count flushes them. Flush the selected job fields and run ownership fields at that boundary, without adding fixture flushes or changing lock order. The actual native rerun remains required.

The next 29-class candidate consolidates the canonical API pin without changing its value; adds the eleven exact zero-sudo entries and three existing fulfillment adapters; checks owning query values; replaces reader namespaces with authorized real store/job fixtures; canonicalizes generated domain suffixes; uses genuine attribute-backed export variants and normalizes whitespace in unchanged safety text. The exact UI inventory also asserts the parked P16 file remains absent from the manifest. Full local suite: 461 pass; native proof remains pending.

## Expanded domain prerequisite: 9faaf3be

[Run 34334141258](https://github.com/AdamsOdoo/Adams/actions/runs/34334141258) executed 696 tests across 29 complete selected classes: two failures, two errors, no selected skips or missing classes, 276.505 seconds. Policy 34334141213 passes. Artifact 10097190577 SHA-256 `a9cd0867ce7bf488b32926bba6039da902d63bc77f306584e3038b915abb5c96` was verified; see `evidence/native-focus-9faaf3be-summary.json`. Full campaign remains unexecuted on this candidate.

Cancellation and settings boundary regressions now pass. The product duplicate-identity fixture still created a second empty attribute combination; it must use the existing genuine variant helper. Retired-topic cleanup correctly refuses an observation without an expected callback digest; the fixture must supply the matching ownership evidence. Neither fix warrants weakening production constraints.

The two W3 residuals reveal an actual worker-path gap: the real observation handler reaches P07 admission as the root cron actor, which lacks a connector role, and the temporary transport error is consequently never reached. Separate read-only tracing confirms the dispatcher also retains its ambient company when invoking handlers for claimable other-company stores. Preserve user gateway checks, authorize only a validated internal job path, and prove company rebinding with native worker tests. Direct reader mocks are insufficient proof of the installed cron path.


Both CI workflows previously grouped by `github.ref`, so push and PR events for the same source ran duplicate campaigns. Their groups now use source repository plus head branch, retaining distinct workflow prefixes and all triggers/checks. A fork with the same branch name remains separate. Source checkout is still explicitly the PR head or pushed SHA; base/PR fields remain event metadata only. This follows GitHub's [concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) and [context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts) contracts. Verify the surviving run through the full Actions run collection, since the connector's commit wrapper filters to PR events.


The prepared worker correction uses an object-identity capability minted only after dispatch claims the job, with cursor/job/store/company identity and running-state checks. Both dispatcher and job execute in the owning company; ordinary user authorization and the downstream API admission lease remain required. W3 tests that directly invoke a handler or `_dispatch_one` intentionally bypass the claim boundary, so they now use a real connector operator. Their role correction alone is not worker qualification; the dedicated native cron regressions must prove the production entry.


Prepared candidate verification: 461 dependency-free tests pass (20.071 seconds), static/core dependency/change-size/changed syntax/whitespace checks pass. The selected native inventory contains 31 complete classes. New tests cover private-capability denials, configured root server action with foreign-company P06 admission, and the real claimed P07 observation handler with ORM evidence/no stock or mutation effects. These use a shared test cursor and mocked reader/remote-I/O seams: they do not prove separate-cursor `method_direct_trigger`, a live API lease or concurrent workers. Those remain distinct qualification items. Handoff 13 was reduced to current state and continuation rules; prior checkpoints remain in Git history, with raw experiment evidence retained here.


Read-only follow-up while `af771c91` runs: all 84 original failure headers across `TestFulfillmentModeSwitch` (16), `TestFulfillmentScans` (14), `TestShopifyConnectorFulfillmentWebhook` (16), `TestShopifyConnectorSaleWebhook` (8) and `TestTaxDecisionRoute` (30) trace to activation rejection: 70 direct errors and 14 caught-enqueue downstream outcomes. Raw original fresh-log ranges 40650–40671, 40973–40994, 41366–41398 and 39049–39060 show representative rejection-before-assertion chains. Current primary/secondary fixtures already carry the owning activation service from local source c632743 (published equivalent ab3611a9). No additional production correction is justified from these old logs. The current 31-class prerequisite excludes these five classes; their native rerun/full campaign remains necessary and no pass is claimed.


## Worker candidate af771c91

[Native 34336740112](https://github.com/AdamsOdoo/Adams/actions/runs/34336740112), job 102417807016: **707 tests, one failure, one error**, 247.758 seconds, no selected skips/missing classes. Policy 34336740133 and packaging pass; full campaign did not execute. Artifact 10098186454 SHA-256 `c926b4fea737825bf65854a51be96e31b6a69d141783f49bf51a8f2f51363f5c` verified; original summary retained.

The worker P06 admission/company positive, claimed real P07 observation path, root/no-capability and nonroot-sudo refusals, and prior W3/W2 residual corrections pass. One new negative test created two jobs with the same computed idempotency key; it now supplies distinct payload hashes without altering the uniqueness constraint. The export test reached its assertion but did not raise: the corrected fixture explicitly selects both current attribute-backed combinations and seeds/asserts equal SKUs before preflight. Its native outcome is pending. The multi-case capability-negative test did not reach its assertions because fixture flush failed, so its complete proof remains open.

A separate source guard still expected dispatch through `self`; its follow-up checks claim-before-scope and both dispatch branches through the scoped worker. Static execution passes. The next native prerequisite retains all31 classes and adds complete mutation dispatch plus the five activation-cascade classes above (37 total). This is test/evidence-only follow-up; no additional production change or compatibility waiver is included.


Further read-only attribution while `1063cb07` waits: 60 original headers across `TestBatch2ProductJourneys` (6), `TestInventoryTriggers` (22), `TestProductScanP10` (8), `TestProductScanProducer` (17) and `TestOrderScanTriggers` (7) comprise 55 direct P15 activation refusals and five caught/no-child cascades. Product cron and stock-event logs show the rejection before the no-job assertion; the order-cron case mutes that logger but follows the same guarded enqueue/catch path. Current primary and secondary fixtures are already activated from c632743/ab3611a9. No additional production defect is established by these old traces. The 37-class prerequisite excludes these classes; the complete 77 directly declared methods, including secondary-store and stock-event cases, need current native/full execution before closure.

## Continuation result: 1063cb0

Native run 34337913595 completed 834 tests / 0 failures / 1 error in 296.609 seconds, with 37 selected classes present and no selected skips. Policy and packaging pass; full campaign skipped. Artifact 10098860989 checksum verified: `e2018d4cd8440837f666d9f31b900d9a26529a32aced37ca0faa03694f304660`. Original summary: `evidence/native-focus-1063cb0-summary.json`.

The sole traceback is TestFulfillmentScans.test_batched_reader_requires_exact_requested_identity, rejected by the reader role guard before identity assertions. The follow-up uses an ordinary same-company connector operator for service, store and job, following the qualified pagination fixture. Both exact identity assertions and the production authorization guard remain. Independent read-only review confirmed this diagnosis; native correction proof is pending.

### Process-death evidence scope recovered during continuation

The `1063cb0` focused runner explicitly enables `SHOPIFY_LAYER2_RUN_PROCESS_DEATH=1`. Its raw log starts `TestMutationRecovery.test_real_process_death_harness`, completes the class without a test error, and reports no selected skips. This executes six real child-process termination boundaries with independent database cursors and persisted recovery assertions. Child `KeyboardInterrupt` traces occur at the three intentionally terminated sleep points; they are not recorded test failures. The remaining three boundaries call `os._exit`.

This is supporting proof for the synthetic `mutation_dispatch_selftest` strategy and its persisted recovery contract. It does not qualify actual Shopify mutations, every domain's process-death behavior, or actual Odoo scheduler acquisition. The full runner still treats this harness as opt-in; do not generalize a focused execution into every full lane.

## Consolidated native campaign: a77741a

Run [34342033182](https://github.com/AdamsOdoo/Adams/actions/runs/34342033182), artifact 10101998991 SHA-256 `56717f24eb33445fe954870076613ed63f2a39890af01ff010c5672855a9482d`, downloaded and verified. Exact source and Odoo pin verified; original full/focused summaries preserved alongside previous evidence.

| Lane | Result |
| --- | --- |
| Focused | 834 tests, 0 failures, 0 errors; 37 classes, no selected skips |
| Fresh | 3012 tests, 3 failures, 1 error |
| Warm | 3012 tests, 19 failures, 2 errors |
| Lite / Full installation | Both pass |
| Two genuine migrations | Each 2877 tests, 3 failures, 1 error; 20/19 migration scripts |
| Each repeated upgrade | 2877 tests, 19 failures, 2 errors |
| Old-core W2-only | 18 tests, 0 failures, 10 errors |
| Nonstandard | 70 tests, 4 failures, 31 errors |

### Root-cause grouping before another publication

- Fulfillment concurrency cleanup deletes jobs before their restricted audit logs. Its committed store 669 survives fresh; warm clones fresh and setup/dashboard/uninstall then encounter that store. Both migration/repeat pairs reproduce the same leak with store 614. Fix producer cleanup and assert zero residue; do not change dashboard semantics or erase legitimate stores.
- Inventory withdrawal actor test includes root's initial activation audit. Snapshot before action; assert exactly four new decision audit jobs, all the deciding administrator, rather than filtering by actor.
- Mutation success test obtains C2's cursor from Odoo's shared test registry; its independent observer requires real committed C2 visibility. Replace only the test registry cursor factory with genuine pooled cursors; retain full callback trace and terminal succeeded assertion. Native verification still required.
- Export custom-ID exact-query fixture omits current pageInfo completeness selection; preserve lookup and pagination expectations.
- Product/customer/order/tax/visual intended-active fixtures omit activation, blocking business setup. Correct sanctioned activation across owning fixtures, retain inactive/disconnect negatives, trace newly reached authorization and transaction boundaries.
- P10: snapshot serialization conflict in claim/cancel, forbidden shared-test commit during stale-owner case, and company cleanup FK errors. Preserve real concurrency assertions; isolate company-hook side effects in a disposable P10 database and require the entire tag explicitly. Do not ignore deadlocks, skip tests, or represent a fixture-only retry as scheduler retry proof.
- Visual overflow inventory lacks existing V2 and parked prototype selectors. Measuring a selector does not manifest or approve the prototype.
- Policy metadata omission: catalog provenance must match frozen inventory; validate final generated evidence before publication.

The old-core compatibility proposal remains unaccepted. Repairs above are in progress, not qualified results.
