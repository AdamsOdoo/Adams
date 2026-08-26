# Production-path inventory

**Date:** 2026-08-18

**Exact head/tree:** `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8` /
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

This is a source-grounded inventory, not a runtime certification. File and
method names below refer to the exact checkout.

## Addon topology

| Addon | Depends on | Production responsibility | Explicit boundary |
| --- | --- | --- | --- |
| `shopify_connector_core` (`19.0.1.23.0`) | `base`, `web` | Store/settings/location cache, credential service, GraphQL client, job/attempt/lease substrate, setup/readiness, dashboards, cron | No product/order/inventory/fulfillment handlers; manifest states scan/reconciliation based, with no webhook subscription/delivery pipeline and no OAuth flow. |
| `shopify_connector_product` (`19.0.2.11.0`) | core, `product` | Shopify→Odoo product/variant import, matching, bindings and scheduled scan | Import-only; no Shopify write-back, webhook pipeline or OAuth. |
| `shopify_connector_product_export` (`19.0.1.2.0`) | core, product | Explicit Odoo→Shopify product/media export with preview, confirmation and reconciliation | Separate optional write-risk surface; non-destructive allowlist and no blind retry. |
| `shopify_connector_inventory` (`19.0.1.8.0`) | core, product, `stock` | Location mappings, InventoryItem/level bindings, Odoo available quantity push, CAS, first-push preview and reconciliation | Odoo is source of truth after onboarding; no Shopify→Odoo stock write and reviewed baseline import is deferred. |
| `shopify_connector_sale` (`19.0.2.11.0`) | core, product, `sale` | Shopify customer/order import, tax/discount/payment decisions, bindings and scan | Import-only; no customer export or Shopify mutation. |
| `shopify_connector_fulfillment` (`19.0.1.6.0`) | core, sale, `stock_delivery`, `sale_stock` | Mode 1 Odoo outbound fulfillment/tracking; Mode 2 conservative inbound reconciliation and mode transitions | Scan/reconciliation based; no webhook delivery pipeline. |

## Real production entry points

### Setup and lifecycle

1. `shopify.connector.setup.wizard.save_store_identity()` validates a bare
   `.myshopify.com` domain, refuses a duplicate domain, and creates a new
   store under the active company (`shopify_connector_setup_wizard.py:1307-1367`).
   It does not silently repurpose a store whose immutable domain differs.
2. `save_credential()` is the write-only credential entry point
   (`...setup_wizard.py:1373+`); the credential model controls token/cache
   provenance and secret access.
3. `run_readiness()` consumes stored evidence only; it does not make a Shopify
   request (`...setup_wizard.py:1473-1492`).
4. `activate()` reruns readiness, refuses blocking/waiting checks, calls
   `store.action_activate()`, and triggers only selected existing enqueue crons
   (`...setup_wizard.py:1741-1849`). It does not register webhooks.
5. `shopify.connector.store.action_test_connection()` and
   `_run_connection_probe()` perform the lifecycle probe with fixed internal
   purposes, one credential snapshot, post-network generation/credential
   revalidation and audited job/log evidence (`...store.py:598-847`).
6. `action_activate()`, `action_disconnect()`, `_run_disconnect_quiesce()` and
   `action_reconnect()` implement lifecycle state, generation fencing and
   quiescence (`...store.py:1038-1760`).

### API and credential path

- `shopify.connector.api.client.execute_business_read()` admits a bounded
  business read only for a running, owned job and holds a durable call lease
  through normalization and caller reconciliation
  (`shopify_connector_api_client.py:417-587`).
- `execute_business()` and `_admit_mutation()` require an immutable mutation
  job/attempt context, current store generation, pending attempt and one
  transport admission (`...api_client.py:588-930`).
- `_send()` performs the HTTPS Admin GraphQL POST with bounded connect/read
  timeouts and the masked access token header (`...api_client.py:1035-1078`).
- `_normalize_response()` classifies HTTP, top-level GraphQL, user-error and
  throttle responses and requires the configured API-version response header
  (`...api_client.py:1380-1470`).
- The configured GraphQL API version is the code constant `2026-07` in
  `shopify_connector_core/tools/api_version.py`; the store field is constrained
  to that value.
- `shopify_connector_store_credential.py` supports offline Admin tokens and
  Dev Dashboard client-credential token exchange/cache. It masks/write-protects
  credentials and redacts logs, but makes no encryption-at-rest claim.

### Jobs, attempts and transaction boundaries

- Business job sources include `webhook`, `manual_sync`, `scheduled_sync`,
  `reconciliation` and `odoo_event` (`shopify_connector_job.py:60-69`). The
  `webhook` value has no producer in this checkout.
- `shopify.connector.job.create()` gates business jobs on a connected store and
  captures `expected_connection_generation` (`...job.py:327-370`).
- `_claim_for_dispatch()` uses Odoo 19 `try_lock_for_update()` and rechecks the
  row under lock (`...job.py:620-675`). Its own docstring correctly states that
  `TransactionCase` does not prove actual concurrent workers.
- `shopify.connector.job.dispatch.run_drain()` is the cron entry point. It
  applies a default batch of 20 (configurable 1–500), per-job commit progress,
  time budget and local throttle backpressure (`...job_dispatch.py:187-370`).
- `shopify.connector.mutation.attempt` is immutable per job and records intent,
  fingerprints, expected generation, idempotency identity, observed outcome and
  merchant status. Only a reconciliation read can promote an uncertain attempt
  to verified (`shopify_connector_mutation_attempt.py:83+`).
- `shopify.connector.call.lease` is the durable network-admission record used
  by disconnect quiescence (`shopify_connector_call_lease.py:4+`).

### Domain paths

| Domain | Producer/handler | Remote operation | Local evidence/recovery |
| --- | --- | --- | --- |
| Product import | `product_scan.py:_cron_enqueue_product_scans`; `product_importer.py` handler | Paginated product/variant GraphQL reads | Cursor/checkpoint and binding/match decisions; ambiguous matches go to review. |
| Product export | `product_export_service.py` preview/apply and `_transport` | `productSet` only for safe create; `productUpdate`, bulk variant mutations, media operations for explicit fields | Preview ID, confirmation, remote read and `updatedAt` freshness check; stale/uncertain paths reconcile. |
| Inventory | `inventory_service.py:run_inventory_push_scan`, stock-move enqueue hook | `inventoryActivate`, `inventorySetQuantities` with expected-before and `@idempotent` | Pair binding, first-push preview, CAS conflict/reconciliation and manual release action. |
| Orders/customers | `order_scan.py:_cron_enqueue_order_scans`; importers | Read-only orders/customers/lines/discounts/shipping/tax data | Store-scoped bindings, overlap cursor, tax decisions and review states. |
| Fulfillment | `fulfillment_scans.py:_cron_enqueue_reconciliation_checks`; create/tracking strategies | `fulfillmentCreate`, `fulfillmentTrackingInfoUpdate` in Mode 1; reads in Mode 2 | Picking/fulfillment binding, intent fingerprint, read-back reconciliation and review queue. |

## Scheduled entry points and cadence

| XML record | Entry point | Cadence | Assurance meaning |
| --- | --- | --- | --- |
| `shopify_connector_core/data/shopify_connector_cron_drain.xml` | `job.dispatch.run_drain()` | 5 minutes | Queue progress/backpressure, not inbound event freshness. |
| `.../shopify_connector_cron_disconnect.xml` | `store._run_disconnect_quiesce()` | 5 minutes | Lifecycle safety. |
| `shopify_connector_product/data/shopify_connector_product_cron.xml` | `store._cron_enqueue_product_scans()` | 1 hour | Polling/reconciliation fallback only. |
| `shopify_connector_sale/data/shopify_connector_sale_cron.xml` | `store._cron_enqueue_order_scans()` | 15 minutes | Polling/reconciliation fallback only. |
| `shopify_connector_inventory/data/shopify_connector_inventory_cron.xml` | `inventory.service.run_inventory_push_scan()` | 15 minutes | Odoo outbound drift scan; not Shopify inbound quantity authority. |
| `shopify_connector_fulfillment/data/shopify_connector_fulfillment_cron.xml` | `store._cron_enqueue_reconciliation_checks()` | 60 minutes | Fulfillment reconciliation only. |

## Webhook inventory result

**[Code fact] No production webhook system exists.** There is no
`controllers/` directory, HTTP route, subscription model/registration call,
HMAC verifier, raw-body event record, delivery-ID unique key, callback
acknowledgement or asynchronous webhook handler. The readiness check explicitly
returns `not_applicable=True` in
`shopify_connector_readiness_check.py:_check_webhook_hmac()`
(`:436-453`), and the source guard intentionally rejects such a surface
(`tests/test_ui_source_guards.py:149-176`).

The current architecture therefore provides durable scheduled/manual pulls and
domain reconciliation, but not the requested near-real-time signal path.
