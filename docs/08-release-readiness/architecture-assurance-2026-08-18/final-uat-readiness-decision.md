# UAT readiness decision

> **Current-head pointer (2026-08-18):** use the [exact-head assurance
> addendum](./exact-head-addendum-2026-08-18-f62.md) for the published
> test-only correction `2b8108b9b69ca70b20a3b705a82e167ea13bb98a` /
> `522bcd01035cb44d241ff56c3deff3de272701c2` decision. The earlier
> `b9ff84ef` snapshot remains historical evidence.

**Date:** 2026-08-18

**Current qualification candidate:** PR #206, branch
`codex/ui-restructure-implementation`, HEAD
`2b8108b9b69ca70b20a3b705a82e167ea13bb98a`, tree
`522bcd01035cb44d241ff56c3deff3de272701c2`

**Decision type:** provisional control-room decision; not a product-owner
release sign-off.

## Decision

**NOT ASSURED — CORE ARCHITECTURE GAPS.**

Do not begin controlled merchant UI UAT on this exact head. The Odoo-side
durable job/mutation/recovery foundation is a viable base, but W1/W2 cover only
bounded lifecycle/product webhook slices; inventory, order, refund and
fulfillment near-real-time paths remain incomplete, and no exact-head live
Shopify mutation has been proven. Odoo.sh qualification is externally blocked.
This packet therefore does not authorize UAT or PR readiness.

Actions run `32144921687` completed **failure after approximately 48 minutes**.
Fresh/warm each had `0 failed, 2 error(s)` from the admin-actor and ISO
timestamp fixtures; W2-only reached tests and failed solely the same timestamp
fixture; migration and non-standard reported `0 failed, 0 error(s)`, although
the exact optional-W1 migration skip was initially rejected. Luna corrections
`0c7a064e…` / `daf6fd39…` were published as test-only `2b8108b9…` /
`522bcd01…`. SOL Medium found a trailing-space mismatch, then accepted the
amendment. Exact-head run `32152200822` / job `95760574305` completed
**SUCCESS** against Odoo pin `30bde9…`: fresh/warm each ran 2,682 tests `0/0`,
the W2-only schema bridge passed, both migration bases ran 2,647 tests `0/0`
twice with zero second-pass scripts, and non-standard ran 62 tests `0/0` plus
three HOOT suites. This is accepted CI evidence only; it is not Odoo.sh, live
Shopify, or Gate A–H evidence.

## Track decisions

| Track | Decision | Blocking conditions |
| --- | --- | --- |
| Product/inventory UI UAT | **BLOCKED** | Gate A/B live identity/read proof; product lifecycle Gate C; inventory Gate D; hybrid webhook/reconciliation Gate E; correction of inventory direction copy; exact-head Odoo.sh build/database linkage. |
| Order/fulfillment UI UAT | **BLOCKED** | Gate A/B; order/customer/tax/payment Gate F; fulfillment Mode 1/Mode 2 remote proof; webhook/reconciliation Gate E; explicit Mode 2 contract/copy; failure recovery Gate G. |
| Production-release planning | **BLOCKED / NOT READY** | Webhook architecture, scale decision, live Gates A–H, dedicated-user security evidence, exact-head independent review and measured performance remain open. |

## Gate status

| Gate | Status | Evidence interpretation |
| --- | --- | --- |
| A | Not live-passed | Correct domain is known; credential exchange/remote identity is absent from exact-head ledger. |
| B | Not live-passed | Source client and pagination/throttle handling exist; fresh remote reads are absent. |
| C | Not live-passed | Product code/tests exist; live create/update/read-back/replay is absent. |
| D | Not live-passed | Inventory CAS/idempotency code exists; live InventoryItem/location/quantity evidence is absent. |
| E | Not live-passed / externally blocked | W1/W2 controller/subscription/HMAC/delivery paths are source-reviewed, but no exact-head Shopify delivery, replay/deduplication or reconciliation-repair evidence exists; required domain slices remain incomplete and Odoo.sh is inaccessible. |
| F | Not live-passed | Sale/fulfillment code exists; live order/fulfillment evidence is absent. |
| G | Not live-passed | Local failure taxonomy exists; live uncertain/timeout/restart proof is absent. |
| H | Not live-passed | ACL/company/source controls exist; exact-head dedicated-user runtime matrix is absent. |

## Conditions to revisit

1. Add and independently review the bounded hybrid webhook/reconciliation
   capability described in [`webhook-reconciliation-decision.md`](./webhook-reconciliation-decision.md).
2. Resolve product/order scale limits with resumable enumeration or Shopify Bulk
   Operations; publish supported production volumes.
3. Correct setup direction copy for inventory and fulfillment.
4. Preserve accepted exact-head Actions run `32152200822` and obtain Odoo.sh
   fresh/warm/migration qualification when the external access blocker is
   cleared; runs `32127509348` and `32144921687` remain non-acceptance history.
5. Run Gates A–H against only `testin-lzhbzhtc.myshopify.com`, with fresh remote
   reads, IDs, attempt evidence, replay/no-op results and cleanup.
6. Measure queue throughput, GraphQL cost/throttle recovery, query counts,
   memory, cron duration and multi-store fairness against provisional budgets.
7. Restore all temporary roles/users after Gate H and preserve redacted evidence.

When all conditions are met, issue a new dated exact-head decision. Do not
retroactively upgrade this packet to “ASSURED.”
