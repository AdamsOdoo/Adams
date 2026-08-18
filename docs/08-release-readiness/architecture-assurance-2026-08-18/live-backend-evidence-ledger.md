# Live backend evidence ledger

**Ledger date:** 2026-08-18

**Exact candidate:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

This ledger is deliberately conservative. It records what is known and what is
missing; it does not turn CI, a queued job or a build into Shopify evidence.

## Environment and build facts

| Timestamp / source | Head/tree | Build/database | Store and actor | Evidence/result |
| --- | --- | --- | --- | --- |
| 2026-08-18 control-room snapshot | `b9ff84e` / `7da2d8c` | Odoo.sh exact-head build `36553922`: **success**; fresh exact-head database URL is held by the control room and is not reproduced in this writer-owned packet | No live credential or mutation performed | Build qualification is not live Shopify proof. |
| 2026-08-18 last check | Same | [GitHub Actions run `32103926602`](https://github.com/AdamsOdoo/Adams/actions/runs/32103926602) was still **in progress** at the last check | N/A | Do not call the suite accepted until the run completes and exact head is confirmed. |
| Prior-build control-room fact | Earlier build `36550325` | Prior development database, not this exact head | Store `562` had the correct domain `testin-lzhbzhtc.myshopify.com`; no credential was present | Store row existence is not authentication or remote identity proof. |
| Prior-build control-room fact | Earlier build `36550325` | Prior development database | Historical record `555` was absent; failed jobs `3186` and `3188` remain preserved in documentation | Wrong-domain failure evidence is retained but does not prove the authorized shop invalid. |

## Gate ledger

| Gate | Exact-head live evidence required | Current result | Missing decisive evidence |
| --- | --- | --- | --- |
| A | Token exchange, returned shop identity/scopes/API version, masked storage, generation | **NOT RUN / NOT LIVE-PASSED** | Credential exchange and remote identity record for store 562/new correct store |
| B | Fresh GraphQL reads, pagination and throttle metadata | **NOT RUN / NOT LIVE-PASSED** | Remote GIDs, pages, cost and classification records |
| C | Product import/export lifecycle with fresh read-back and repeat/no-op | **NOT RUN / NOT LIVE-PASSED** | Shopify product/variant GIDs, local bindings, preview/attempt IDs and remote reads |
| D | InventoryItem/location/CAS/idempotency remote proof | **NOT RUN / NOT LIVE-PASSED** | Location/InventoryItem/level GIDs, expected-before, remote result and conflict recovery |
| E | Actual subscription/delivery/HMAC/persist/enqueue/process/dedup/reconcile | **BLOCKED** | Entire production webhook system is absent |
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
2. Actions run `32103926602` must be rechecked after completion; an in-progress
   run cannot be described as accepted.
3. No live Shopify credential, subscription, remote GID, job/attempt or fresh
   remote read is recorded for the exact candidate.
