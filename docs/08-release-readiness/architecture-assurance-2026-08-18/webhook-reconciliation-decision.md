# Webhook and reconciliation decision

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

## Decision

**[Decision] Adopt a hybrid inbound design for the accepted MVP: Shopify
webhooks as near-real-time signals, durable asynchronous processing, and
scheduled reconciliation as the correctness backstop.** Do not describe the
result as “real-time”; delivery and processing are asynchronous.

**[Code fact] The current checkout has no production webhook system.** This is
not a tested feature that merely lacks evidence. There is no `controllers/`
package or route, subscription registration, HMAC verifier, delivery/event
record, delivery-ID unique key, fast acknowledgement or webhook consumer. The
readiness check explicitly says webhook intake is not installed and returns
`not_applicable=True` (`shopify_connector_core/models/shopify_connector_readiness_check.py:_check_webhook_hmac`,
lines 436–453). The source guard intentionally prohibits a controller/webhook
surface (`shopify_connector_core/tests/test_ui_source_guards.py`, lines
149–176). The `webhook` job source in `shopify_connector_job.py:67-69` is only
vocabulary; no producer reaches it.

This absence is a **P0/P1 architecture gap** against the requested
near-real-time contract and blocks Gate E and both UI-UAT tracks that depend on
fresh inbound signals.

## Required topics (proposed, not yet registered)

The list is intentionally narrow. Exact topic names/scopes and API-version
availability must be verified during implementation against Shopify’s
[webhook reference and subscription guide](https://shopify.dev/docs/apps/build/webhooks/subscribe).

| Topic family | Purpose and ownership | Processing entry point / side effects | Deduplication, conflict and fallback |
| --- | --- | --- | --- |
| `products/create`, `products/update`, `products/delete` | Shopify-owned catalog signal; enqueue import/reconciliation for product/variant bindings | Persist event, enqueue product import/reconcile; never create by name | Store + delivery ID; payload/update timestamp watermark; product cursor scan repairs missed events |
| `inventory_levels/update` | Shopify inventory-level signal for drift detection; Odoo remains quantity authority after onboarding | Persist signal, read exact InventoryItem/location level, compare snapshot and block/review outbound conflict; do not blindly write Odoo stock | Store + delivery ID; triggered timestamp/update watermark; scheduled location/inventory reconciliation |
| `orders/create`, `orders/updated`, `orders/cancelled` | Shopify-owned order lifecycle signal | Persist event, enqueue customer/order import or lifecycle review | Store + delivery ID and order `updatedAt`; order overlap scan repairs loss/out-of-order delivery |
| `fulfillments/create`, `fulfillments/update` | Shopify fulfillment observation; Mode 2 only applies eligible evidenced changes | Read/reconcile fulfillment orders/fulfillments; update existing evidence/review state, not blind delivery creation | Store + delivery ID + fulfillment/order watermark; hourly/reconnect reconciliation |
| `refunds/create` | Shopify refund observation for supported order/review workflow | Persist and enqueue order/refund reconciliation; unsupported shapes go manual review | Store + delivery ID/event ID; order reconciliation fallback |
| `app/uninstalled` | Quiesce the store and fence credentials/jobs | Mark disconnecting/disconnected through lifecycle controller; preserve evidence and prevent new business jobs | Store + delivery ID; manual recovery/reconnect only after fresh identity/credential proof |
| Required privacy/compliance topics | Only when the distribution model/scopes require them | Route to a dedicated compliance handler with retention/deletion evidence | Store + delivery ID; no domain mutation; verify required topics before release |

## Bounded implementation decomposition

1. **Subscription lifecycle module.** Add a modular webhook addon or narrowly
   scoped extension. Persist expected topics, callback URI/version, remote
   subscription IDs where available, registration state, last reconciliation,
   failure reason and store/generation. Register during connection readiness;
   reconcile expected versus actual subscriptions after activation and on a
   scheduled health job. Do not subscribe indiscriminately.
2. **HTTPS ingress.** Add a route that preserves the raw request body, verifies
   `X-Shopify-Hmac-SHA256` with the registered client secret using a constant-
   time comparison, validates topic/version/host and resolves the Odoo store
   from trusted subscription/shop identity. Never trust payload identity alone.
3. **Durable delivery record.** Persist delivery ID, event ID, topic,
   subscription ID, shop/domain, triggered time, API version, signature result,
   payload hash and redacted payload/retention metadata. Add a unique
   store+delivery-ID constraint. Keep payload retention bounded and redact
   credentials/PII according to the existing retention policy.
4. **Fast acknowledgement.** After durable persistence, return HTTP 200 and
   enqueue `job_source='webhook'`; do not perform product/order/inventory
   mutation work in the HTTP request. Invalid HMAC/unknown shop/invalid topic
   must reject without mutation.
5. **Asynchronous handlers.** Reuse the existing job/lease/attempt substrate.
   Handlers must be idempotent, store/company scoped, generation fenced and
   timestamp-aware. Older events must not overwrite newer snapshots. Duplicate
   deliveries must be no-ops while distinct delivery IDs for one event remain
   correlatable by event ID.
6. **Recovery and reconciliation.** Retain current product/order/inventory/
   fulfillment scans. Add missing-event detection, dead-letter/manual-review
   state, subscription health diagnostics, uninstall handling and operator
   requeue/reconcile controls. A webhook delivery is a trigger, not a source of
   correctness by itself.

## Acceptance tests before UI UAT

- Actual expected subscriptions are visible remotely for the correct
  development shop; no subscription is created for the historical wrong shop.
- A real development-store event reaches the HTTPS endpoint, passes raw-body
  HMAC, is persisted, receives a fast 200, enqueues and processes asynchronously.
- The resulting Odoo binding/snapshot is verified by a fresh Shopify read.
- The same delivery ID is replayed and produces no duplicate side effect.
- An invalid signature is rejected and creates no job/business mutation.
- An out-of-order event cannot regress a newer local snapshot.
- A simulated missing delivery is repaired by scheduled reconciliation without
  a duplicate effective mutation.
- Uninstall/disconnect fences new work while preserving the delivery and
  mutation evidence.

## Sources

- [About Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks),
  accessed 2026-08-18.
- [Verify webhook deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries),
  accessed 2026-08-18.
- [Manage webhook subscriptions](https://shopify.dev/docs/apps/build/webhooks/subscribe),
  accessed 2026-08-18.
