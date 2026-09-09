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
