# Backend-first live test plan

**Date:** 2026-08-18

**Candidate:** HEAD `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8`, tree
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

**Target:** only `testin-lzhbzhtc.myshopify.com`; never
`mqiu21-yz.myshopify.com`.

This plan is a gate definition. All Gates A–H are currently **not live-passed**;
Gate E is additionally blocked by the absent webhook implementation. A test
fixture, mock, completed Odoo job or HTTP 200 is not remote-success evidence.

## Preconditions and evidence contract

Before any mutation:

1. Verify exact HEAD/tree, Odoo.sh build/database, company and allowed-company
   context, actor and connector role.
2. Create or use a clean store row whose domain is exactly the authorized shop.
   Do not repurpose an immutable wrong-domain row.
3. Enter credentials only through the masked/write-only mechanism. Never print,
   screenshot or log a token.
4. Capture timestamp, store/company/location IDs, Odoo IDs, Shopify GIDs, job
   IDs/states, preview IDs, attempt IDs, expected-before/intended/actual state,
   fresh remote read, replay/no-op result, redacted logs and cleanup status.
5. Record whether a result is code fact, live evidence, inference or not proven.

## Gate matrix

| Gate | Production path | Required journey and pass criterion | Current state |
| --- | --- | --- | --- |
| A — Authentication and identity | Setup wizard → credential service → `store.action_test_connection()` / `_run_connection_probe()` | Exchange/obtain token for the correct shop; verify exact `myshopifyDomain`, scopes, API version `2026-07`, masked storage, credential state, generation fencing and stale-generation rejection. | **Not live-passed.** No exact-head token exchange/identity record in the ledger. |
| B — Read connectivity | `api.client.execute_business_read()` through production jobs | Read shop, locations, products, variants, InventoryItems, levels, orders and fulfillments where data exists; verify cursor pagination, GraphQL cost/throttle metadata and classification of transport/top-level/user errors. | **Not live-passed.** No exact-head fresh remote read recorded. |
| C — Product lifecycle | Product scan/import and product-export preview/apply | Import a uniquely prefixed Shopify product; repeat import; create/export from Odoo with preview; remote read-back; owned-field update; omission versus explicit clear; repeated no-op; archive/delete behavior if supported; duplicate/concurrency resistance. | **Not live-passed.** No exact-head Shopify mutation/read-back evidence. |
| D — Inventory lifecycle | Location mapping → pair binding → first-push preview → inventory mutation/reconcile | Verify exact InventoryItem/location binding; first-push review; expected-before CAS; idempotent mutation; fresh read-back; same-value no-op; stale/concurrent conflict; corrected retry after review; no duplicate effective mutation. | **Not live-passed.** No exact-head remote inventory evidence. |
| E — Webhook delivery | Future HTTPS controller → durable delivery → `webhook` job → domain handler | Verify actual subscription; generate real event; raw-body HMAC; fast 200; persisted/enqueued event; processed Odoo result; duplicate delivery no-op; invalid signature rejection; stale/out-of-order handling; reconciliation repair. | **Blocked by implementation.** No controller/subscription/delivery pipeline exists. |
| F — Orders and fulfillment | Order scan/import; fulfillment reader/Mode 1/Mode 2 handlers | Import order/customer/address; map taxes/discounts/payments; duplicate protection; cancellation/refund observation; partial fulfillment/backorder/tracking; fresh remote verification; replay. | **Not live-passed.** No exact-head order/fulfillment evidence. |
| G — Failure and recovery | Job dispatcher + mutation attempt + reconciliation | Safely exercise pre-response timeout, definitely-not-applied failure, possibly-applied outcome, throttle, auth revocation classification, transport failure, permanent validation, retry/backoff/manual review, recovery and crash/restart boundaries. | **Not live-passed.** Local tests do not prove live transport outcomes. |
| H — Security | Dedicated Odoo users/companies and direct RPC/URLs | No Access, Connector User, Connector Administrator; company/allowed-company switching; menus/actions/models/record rules/direct URLs/RPC/public methods; credential/confirmation/recovery/reconciliation/mode controls. Restore roles. | **Not live-passed.** Code controls exist; exact-head runtime matrix absent. |

## Gate-specific safeguards

- **Remote read-after-write:** every claimed mutation result requires a fresh
  Shopify read by stable GID; local job `succeeded` is insufficient.
- **Possibly applied:** do not resend the same intent until a reconciliation
  read proves absence or the existing remote effect is bound.
- **Wrong domain:** failed jobs 3186/3188 and record 555 are historical evidence
  for the wrong shop and cannot be used as valid-store proof.
- **Cleanup:** UAT objects receive a unique prefix, are recorded by GID and are
  deleted/archived only after bindings, attempts, logs and remote state are
  captured.
- **Webhook absence:** do not simulate Gate E with a mocked controller and call
  that a live delivery pass.

## Resume rule after correction

If a release-blocking correction changes code, repeat exact-head CI, fresh/warm/
migration Odoo.sh qualification and independent review before resuming the
interrupted live journey. Never mix evidence from the prior head with the new
head.
