# Live backend evidence ledger

> **Current-head pointer (2026-08-18):** the latest published test-only
> correction is
> recorded in the [exact-head assurance addendum](./exact-head-addendum-2026-08-18-f62.md)
> at `2b8108b9b69ca70b20a3b705a82e167ea13bb98a` / tree
> `522bcd01035cb44d241ff56c3deff3de272701c2`. Historical rows remain
> explicitly scoped and must not be promoted to current-head proof.

**Ledger date:** 2026-08-18

**Exact qualification candidate:** `2b8108b9b69ca70b20a3b705a82e167ea13bb98a` /
`522bcd01035cb44d241ff56c3deff3de272701c2`

This ledger is deliberately conservative. It records what is known and what is
missing; it does not turn CI, a queued job or a build into Shopify evidence.

## Environment and build facts

| Timestamp / source | Head/tree | Build/database | Store and actor | Evidence/result |
| --- | --- | --- | --- | --- |
| 2026-08-18 current qualification snapshot | `2b8108b9` / `522bcd01` | Odoo.sh exact-head qualification **blocked** by permitted cloud-browser automatic-review denial; no build/database or live Shopify result may be claimed | Authorized development shop remains `testin-lzhbzhtc.myshopify.com` only | No exact-head live credential, subscription, delivery or mutation evidence recorded. |
| 2026-08-18 Actions qualification | `f62db111` / `4b69d5d1` | [run `32127509348`](https://github.com/AdamsOdoo/Adams/actions/runs/32127509348) **cancelled after 180 minutes**; [fresh.log artifact `9326736197`](https://github.com/AdamsOdoo/Adams/actions/runs/32127509348/artifacts/9326736197) stopped at `sale core_dispatch_selftest` | Test-only qualification; no Shopify mutation | Earlier deterministic core/W2 thread-harness failures, illegal W2 transition fixture and quoted static guard contaminated store/worker state and cascaded. Non-acceptance evidence. |
| 2026-08-18 Actions re-run | `6805a1d8` / `60cb328e` | [run `32144921687`](https://github.com/AdamsOdoo/Adams/actions/runs/32144921687) **completed failure after approximately 48 minutes** | Test-only qualification; no Shopify mutation | Fresh/warm: `0 failed, 2 error(s)` each (admin actor and ISO timestamp fixtures); W2-only reached tests and failed solely the timestamp fixture; migration: `0/0` but exact optional-W1 skip initially rejected; non-standard: `0/0`. Non-acceptance evidence. |
| 2026-08-18 published correction | `2b8108b9` / `522bcd01` | Luna `0c7a064e…` / `daf6fd39…`; SOL Medium initially found a trailing-space mismatch, then accepted the amendment | Test-only; no Shopify mutation | Four changed paths are recorded in the exact-head addendum. Review acceptance does not substitute for runtime or live evidence. |
| 2026-08-18 accepted Actions run | `2b8108b9` / `522bcd01`; Odoo pin `30bde9…` | [run `32152200822`](https://github.com/AdamsOdoo/Adams/actions/runs/32152200822), job `95760574305`: **SUCCESS** | CI actor only; no Shopify mutation | Fresh 2,682 `0/0`, 40 tour markers/39 required; warm 2,682 `0/0`, zero same-version migrations; W2-only old W1 `19.0.1.0.0` → W2 `19.0.0.2.0`, two JSONB columns, W1 unchanged; migrations `50b…` and `0a15…` each 2,647 `0/0` first+second, scripts `5→0` and `4→0`; optional-W1 skip sanctioned only in migration; non-standard 62 `0/0` plus three HOOT suites. Accepted CI evidence only. |
| 2026-08-18 accepted artifact | Same | Artifact `9332374635`; digest `sha256:54edee9f0f733d8c4ddda3a6908a45b7b26de1c16556b924cf199827027a1e87` | N/A | Integrity evidence for the accepted CI artifact; not Odoo.sh or live Shopify evidence. |
| Historical 2026-08-18 control-room snapshot (pre-W1) | `b9ff84e` / `7da2d8c` | Odoo.sh exact-head build `36553922`: **success**; fresh exact-head database URL is held by the control room and is not reproduced in this writer-owned packet | No live credential or mutation performed | Historical build qualification is not current-head Shopify proof. |
| Historical pre-W1 last check | Same | [GitHub Actions run `32103926602`](https://github.com/AdamsOdoo/Adams/actions/runs/32103926602) was still **in progress** at that historical check | N/A | Superseded; current run status is recorded above. |
| Prior-build control-room fact | Earlier build `36550325` | Prior development database, not this exact head | Store `562` had the correct domain `testin-lzhbzhtc.myshopify.com`; no credential was present | Store row existence is not authentication or remote identity proof. |
| Prior-build control-room fact | Earlier build `36550325` | Prior development database | Historical record `555` was absent; failed jobs `3186` and `3188` remain preserved in documentation | Wrong-domain failure evidence is retained but does not prove the authorized shop invalid. |

## Gate ledger

| Gate | Exact-head live evidence required | Current result | Missing decisive evidence |
| --- | --- | --- | --- |
| A | Token exchange, returned shop identity/scopes/API version, masked storage, generation | **NOT RUN / NOT LIVE-PASSED** | Credential exchange and remote identity record for store 562/new correct store |
| B | Fresh GraphQL reads, pagination and throttle metadata | **NOT RUN / NOT LIVE-PASSED** | Remote GIDs, pages, cost and classification records |
| C | Product import/export lifecycle with fresh read-back and repeat/no-op | **NOT RUN / NOT LIVE-PASSED** | Shopify product/variant GIDs, local bindings, preview/attempt IDs and remote reads |
| D | InventoryItem/location/CAS/idempotency remote proof | **NOT RUN / NOT LIVE-PASSED** | Location/InventoryItem/level GIDs, expected-before, remote result and conflict recovery |
| E | Actual subscription/delivery/HMAC/persist/enqueue/process/dedup/reconcile | **NOT RUN / NOT LIVE-PASSED / EXTERNALLY BLOCKED** | W1/W2 source paths are present, but no exact-head Shopify delivery, replay/deduplication or reconciliation-repair evidence exists; Odoo.sh access is blocked and required domain handlers remain incomplete |
| F | Order/customer/tax/discount/cancel/refund/fulfillment/tracking proof | **NOT RUN / NOT LIVE-PASSED** | Order/fulfillment GIDs, bindings, replay and remote verification |
| G | Live timeout/uncertain/throttle/auth/retry/manual-review/recovery proof | **NOT RUN / NOT LIVE-PASSED** | Transport outcome evidence and crash/restart boundary records |
| H | Dedicated role/company/direct-URL/RPC matrix | **NOT RUN / NOT LIVE-PASSED** | Actor IDs, company contexts, denied/allowed action results and role restoration |

## Required row format for the next live run

Every journey must append a row containing:

`timestamp | exact HEAD/tree | build/database | actor/role | shop/company/location |
Odoo IDs | Shopify GIDs | subscription/delivery/event IDs | job IDs/states |
preview/attempt IDs | expected-before | intended | actual | fresh remote read |
replay/retry/no-op | redacted logs | cleanup`

For webhook evidence also include raw-body HMAC verdict, HTTP status/latency,
persisted delivery row, asynchronous job, duplicate delivery result, event
watermark and reconciliation repair result.

## Evidence gaps requiring parent update

1. The exact fresh database URL was not available to this docs writer and is
   intentionally not guessed. Add it to the control-room ledger before relying
   on the environment row as a reproducible link.
2. Actions run `32152200822` is accepted exact-head CI evidence. Runs
   `32127509348` and `32144921687` remain non-acceptance history. CI acceptance
   does not close the Odoo.sh or live backend gates.
3. No live Shopify credential, subscription, remote GID, job/attempt or fresh
   remote read is recorded for the exact candidate. The published
   `2b8108b9…` correction is test-only and does not supply live evidence.
