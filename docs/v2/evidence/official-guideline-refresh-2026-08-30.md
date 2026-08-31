# Official Shopify and Odoo Contract Refresh — 2026-08-30

This is a source refresh, not release evidence. It records the official
technical rules that the implementation and exact-candidate tests must prove.
Only Shopify/Odoo primary sources and the repository-pinned Odoo source are
normative; competitor behavior is never a technical authority.

## Shopify Admin GraphQL

Sources inspected on 2026-08-30:

- [Admin GraphQL API 2026-07 reference](https://shopify.dev/docs/api/admin-graphql/2026-07)
- [API usage and rate limits](https://shopify.dev/docs/api/usage/limits)

Locked implications:

- The endpoint and all checked-in documents remain pinned to `2026-07`; API
  version is not a merchant setting.
- A GraphQL HTTP 200 is not success by itself. Top-level `errors`, mutation
  `userErrors`, data shape, served API version and expected store identity are
  independently classified.
- Every checked-in document has one unique operation name and one typed owner.
- The executor records `requestedQueryCost`, `actualQueryCost`,
  `maximumAvailable`, `currentlyAvailable` and `restoreRate` when returned.
  `MAX_COST_EXCEEDED` is a first-class fail-closed class, not an unknown error.
- Pagination is bounded and proves `pageInfo`, cursor progress, identity and
  completeness. An incomplete read never proves absence or authorizes a write.
- Mutations declare side-effect class, connector/Shopify idempotency posture,
  exact readback and uncertainty policy before registration.

## Shopify webhooks

Sources inspected on 2026-08-30:

- [Shopify webhook architecture](https://shopify.dev/docs/apps/build/webhooks)
- [Verify webhook deliveries](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries)

Locked implications:

- Verify the raw request-body HMAC with constant-time comparison before parsing
  or trusting headers/payload.
- Deduplicate by Shopify delivery ID and keep acknowledgement work bounded.
- Delivery order is not assumed, within or across topics.
- Webhooks are acceleration hints, never the only consistency mechanism;
  bounded scheduled/manual reconciliation repairs missed or mishandled events.
- Long work runs asynchronously after durable local evidence. Event timestamp,
  admission, worker start and visible completion are measured separately.

## Odoo 19

Sources inspected on 2026-08-30:

- [Odoo 19 security reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- [Odoo 19 performance reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/performance.html)
- [Odoo 19 testing reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html)
- [Odoo 19 Owl component reference](https://www.odoo.com/documentation/19.0/developer/reference/frontend/owl_components.html)
- repository-pinned Odoo source SHA in `tools/odoo-pin.txt`

Locked implications:

- ACLs and record rules are complemented by explicit authorization in every
  public RPC/command method; hiding a control is not authorization.
- Multi-company and exact-store isolation applies to aggregates, counts,
  suggestions, child IDs and mutations as well as ordinary record reads.
- ORM batching, `read_group`, prefetch-aware access, bounded searches and
  measured query counts are the default. Reviewed parameterized SQL is allowed
  only when profiling proves it necessary and its record-rule semantics are
  reproduced explicitly.
- Business side effects are explicit service/command calls, not surprising
  generic `create`/`write` hooks.
- Owl is used for composed operational workspaces; native Odoo list, form,
  search, actions and accessibility behavior remain native where they fit.
- unit, ORM, browser, install/update, migration, security, concurrency and
  performance evidence are distinct gates. A green unit lane cannot replace a
  missing lifecycle or live contract test.

## Current implementation consequences

Already preserved from V1: version/store fences, HMAC-before-parse, payload-free
delivery evidence, deduplication, reconciliation, bounded mutation uncertainty,
server-side role/store checks and exact Odoo pinning.

Release-blocking foundation work still required: typed ownership for all 48
documents, full cost normalization/governor, transaction-coupled job wake-up,
priority and aging, bounded stale-owner recovery, production-shaped
query/latency proof, and live 2026-07 canaries for every operation family.
The wake-up remains in the same database transaction as durable job admission:
a rollback removes both and a commit preserves both. These gaps are assigned
to P01/P05/P10/P17 and may not be hidden by the frontend.
