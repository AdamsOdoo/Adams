# Official conformance matrix

**Review date:** 2026-08-18

**Code under review:** HEAD `b9ff84ef47d8ed8c94bdfee7e22089e01c8ac8b8`, tree
`7da2d8c678eeabd0325c6c7c892a019bcc657cee`

The official URLs below are the requested baseline. “Conformance” means the
code path is aligned with the documented behavior; it is not a live
certification. Current-version pages were accessed/reviewed on 2026-08-18.

| Baseline | Official behavior relevant to this connector | Exact-head evidence | Result / action |
| --- | --- | --- | --- |
| [Shopify webhooks](https://shopify.dev/docs/apps/build/webhooks) | Webhooks provide near-real-time event signals; delivery ordering is not guaranteed; Shopify recommends reconciliation jobs because delivery can be missed or mishandled. | Core manifests say freshness is scan/reconciliation based; no controller, subscription or event consumer; `readiness_check.py:_check_webhook_hmac()` returns not-applicable. | **Gap.** Add asynchronous webhook signal path and retain scans. |
| [Verify webhook deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries) | HTTPS deliveries require HMAC over the raw request body; use delivery ID for duplicate detection; acknowledge quickly and queue burst processing. | No raw-body route, HMAC verifier, delivery-ID record or queue producer exists. | **Not implemented.** Required for Gate E. |
| [Webhook subscriptions](https://shopify.dev/docs/apps/build/webhooks/subscribe) | Subscription lifecycle may be app-specific or shop-specific; topic, URI, API version and subscription identity must be managed consistently. | No subscription model, registration/reconciliation query or lifecycle handler. | **Not implemented.** Decide shop-specific store-scoped lifecycle for this connector or document app-specific deployment. |
| [GraphQL API limits](https://shopify.dev/docs/api/usage/limits) | Cost is calculated per app/store; responses expose requested/actual cost and throttle status; queries and mutations have bounded limits. | `_normalize_response()` parses `extensions.cost.throttleStatus`; store persists available/max/restore rate; dispatch excludes backpressured stores. | **Aligned in code; live cost/backpressure behavior not measured.** |
| [Bulk Operations queries](https://shopify.dev/docs/api/usage/bulk-operations/queries) | Bulk queries run asynchronously and are appropriate for large connections/volumes; operation status/result handling is required. | No `bulkOperationRunQuery`, bulk status/result model or bulk download path in production addons. Product/order scans have finite page caps. | **Scale gap.** Add bulk or resumable enumeration before claiming large-store support. |
| [Idempotent requests](https://shopify.dev/docs/api/usage/idempotent-requests) | Supported mutations accept idempotency keys/`@idempotent`; repeated requests with same key/parameters execute once. | Inventory `inventorySetQuantities` and activation include `@idempotent(key: $idempotencyKey)`; fulfillment create/tracking explicitly do not and use intent scope/read reconciliation. | **Partially aligned by mutation.** Verify every configured API-2026-07 mutation and preserve manual review for unsupported idempotency. |
| [Odoo 19 security](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html) | ACLs, record rules, field access and public-method authorization must be enforced server-side; `sudo()` must not widen access unintentionally. | ACL CSV/XML rules, company rules, protected binding mixin and `_ensure_connector_admin_boundary()` are present; services use narrow elevated reads/writes. | **Code controls present; exact-head dedicated-user/runtime proof not complete.** |
| [Odoo 19 performance](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html) | Batch/prefetch discipline, bounded work, indexes and appropriate ORM locking are expected. | `try_lock_for_update()`, indexed/store-scoped constraints, dispatch batch/time budget, cursor pagination and bounded scans are present. | **Code-aligned but capacity unproven.** Query/throughput/runtime measurements required. |
| [Odoo.sh scheduled actions FAQ](https://www.odoo.com/documentation/19.0/administration/odoo_sh/advanced/frequent_technical_questions.html) | Scheduled action frequency/work must respect hosted execution limits; small bounded batches are operationally safer. | Core drain/disconnect every 5 minutes, per-job commit/progress; domain scans 15–60 minutes and bounded pages. | **Operationally bounded, but not near-real-time.** Validate backlog recovery on target build. |

## API-version and GraphQL-specific findings

- `shopify_connector_core/tools/api_version.py` fixes the Admin GraphQL API to
  `2026-07`; store configuration and response header are checked against this
  constant. This is a **[Code fact]**, not evidence that every operation is
  valid against the remote schema.
- GraphQL top-level errors, user errors, HTTP classes and throttle metadata are
  normalized in `shopify_connector_api_client.py:_normalize_response()`.
- Inventory quantity writes are absolute/CAS operations and carry the
  documented idempotency directive. Fulfillment mutations deliberately rely on
  business intent, operation scope and remote reconciliation because the code
  records those operations as lacking the directive.
- Product export deliberately avoids relying on omitted-list-field semantics for
  updates; `productSet` is confined to the guarded create path. This is a code
  safety decision, not a claim that Shopify’s omitted-field semantics are
  universally benign.

## Conformance limitations

1. No official document can substitute for a fresh read-after-write against
   `testin-lzhbzhtc.myshopify.com`.
2. Tests and source guards prove intended local behavior; they do not prove
   HTTPS ingress, Shopify delivery, API credentials, remote IDs or API-version
   schema validity.
3. Odoo security tests do not replace exact-head Odoo.sh tests with dedicated
   users, multiple companies and direct RPC/URL attempts.
