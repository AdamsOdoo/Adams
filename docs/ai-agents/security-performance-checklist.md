# 6) Security & Performance Check (Actionable)

## Odoo ORM Usage

- Prefer batched `create`/`write` over per-record loops.
- Avoid repeated `search` in loops; prefetch with domain-in queries.
- Use explicit indexes for external ID + company + instance keys.
- Use `sudo()` only where required and document why.
- Guard multi-company isolation in every domain.

## Shopify GraphQL/API Handling

- Use persisted/reusable query templates.
- Capture and store Shopify cost/throttle metadata per request.
- Implement adaptive backoff from throttle status, not fixed sleep.
- Use cursor-based pagination and checkpoint state.
- Log request IDs for support traceability.

## Webhooks

- Validate HMAC signature before payload parsing logic.
- Enforce replay window and unique event ID storage.
- Return fast ACK; offload heavy work to queue jobs.
- Keep webhook handlers idempotent and side-effect minimal.
- Dead-letter failed events with triage metadata.

## Idempotency

- Create immutable idempotency key strategy by resource type:
  - Orders: shop_id + order_id + version/update timestamp
  - Products: shop_id + product_id + updated_at
  - Fulfillments: shop_id + fulfillment_id + status_revision
- Persist processing status (received, processing, done, failed).
- Make retries safe; never assume exactly-once delivery.

## Rate Limiting

- Introduce shared token/cost budget per Shopify instance.
- Prioritize webhook-triggered reconciliation over bulk backfills.
- Apply exponential backoff with jitter.
- Implement circuit breaker for sustained throttle/error bursts.

## Minimum Observability

- Metrics: webhook lag, job throughput, retry count, API throttle events.
- Alerts: signature failures spike, dead-letter growth, sync backlog age.
- Structured logs with correlation IDs (request/event/job).
