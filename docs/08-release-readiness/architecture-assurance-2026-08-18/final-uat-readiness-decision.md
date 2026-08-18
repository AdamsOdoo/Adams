# UAT readiness decision

**Date:** 2026-08-18

**Candidate:** PR #206, branch `codex/ui-restructure-implementation`, HEAD
`b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8`, tree
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

**Decision type:** provisional control-room decision; not a product-owner
release sign-off.

## Decision

**NOT ASSURED — CORE ARCHITECTURE GAPS.**

Do not begin controlled merchant UI UAT on this exact head. The Odoo-side
durable job/mutation/recovery foundation is a viable base, but the absence of
production webhooks is a core capability gap and no live Shopify mutation has
been proven. This packet therefore does not authorize UAT or PR readiness.

## Track decisions

| Track | Decision | Blocking conditions |
| --- | --- | --- |
| Product/inventory UI UAT | **BLOCKED** | Gate A/B live identity/read proof; product lifecycle Gate C; inventory Gate D; hybrid webhook/reconciliation Gate E; correction of inventory direction copy; exact-head CI/build/database linkage. |
| Order/fulfillment UI UAT | **BLOCKED** | Gate A/B; order/customer/tax/payment Gate F; fulfillment Mode 1/Mode 2 remote proof; webhook/reconciliation Gate E; explicit Mode 2 contract/copy; failure recovery Gate G. |
| Production-release planning | **BLOCKED / NOT READY** | Webhook architecture, scale decision, live Gates A–H, dedicated-user security evidence, exact-head independent review and measured performance remain open. |

## Gate status

| Gate | Status | Evidence interpretation |
| --- | --- | --- |
| A | Not live-passed | Correct domain is known; credential exchange/remote identity is absent from exact-head ledger. |
| B | Not live-passed | Source client and pagination/throttle handling exist; fresh remote reads are absent. |
| C | Not live-passed | Product code/tests exist; live create/update/read-back/replay is absent. |
| D | Not live-passed | Inventory CAS/idempotency code exists; live InventoryItem/location/quantity evidence is absent. |
| E | Blocked | No controller/subscription/HMAC/delivery pipeline exists. |
| F | Not live-passed | Sale/fulfillment code exists; live order/fulfillment evidence is absent. |
| G | Not live-passed | Local failure taxonomy exists; live uncertain/timeout/restart proof is absent. |
| H | Not live-passed | ACL/company/source controls exist; exact-head dedicated-user runtime matrix is absent. |

## Conditions to revisit

1. Add and independently review the bounded hybrid webhook/reconciliation
   capability described in [`webhook-reconciliation-decision.md`](./webhook-reconciliation-decision.md).
2. Resolve product/order scale limits with resumable enumeration or Shopify Bulk
   Operations; publish supported production volumes.
3. Correct setup direction copy for inventory and fulfillment.
4. Re-run exact-head GitHub Actions (including run `32103926602` after it
   completes), Odoo.sh fresh/warm/migration qualification and independent review.
5. Run Gates A–H against only `testin-lzhbzhtc.myshopify.com`, with fresh remote
   reads, IDs, attempt evidence, replay/no-op results and cleanup.
6. Measure queue throughput, GraphQL cost/throttle recovery, query counts,
   memory, cron duration and multi-store fairness against provisional budgets.
7. Restore all temporary roles/users after Gate H and preserve redacted evidence.

When all conditions are met, issue a new dated exact-head decision. Do not
retroactively upgrade this packet to “ASSURED.”
