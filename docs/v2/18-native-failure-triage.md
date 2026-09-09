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
