# V1 supported scope

## Distribution

This is a public Odoo connector module using merchant-managed Shopify custom-app credentials. It is not a Shopify App Store application, embedded app, OAuth installer, or Shopify billing integration. The merchant creates and controls the Shopify custom app and supplies either the supported Admin API access token or client-credentials configuration through the connector's write-only credential surface.

The permanent store identity must be the exact `*.myshopify.com` domain. The pinned Admin GraphQL API is `2026-07`.

## Supported behavior

| Domain | Fully supported | Manual review | Unsupported in v1 |
|---|---|---|---|
| Authentication | Identity/scope verification, rotation, disconnect/reconnect, generation fencing, subscription reconciliation | Missing scope, identity mismatch, credential loss | OAuth, public-app installation, billing |
| Products | Shopify→Odoo product/variant create/update; deterministic SKU/barcode matching; previewed Odoo→Shopify managed-field export; safe variant add | Ambiguous match, binding conflict, remote drift, deletion represented by stale binding | Destructive local deletion, broad publication automation |
| Inventory | Odoo-authoritative available quantity; explicit location mapping; first-push preview/confirmation; drift/CAS reconciliation | Missing mapping, stale preview, drift, uncertain mutation | Shopify quantity import into Odoo |
| Orders | Idempotent import of supported customer, addresses, lines, price, discount, tax, shipping, currency and payment evidence | Cancellation, void, expiry, refund, partial refund, unsafe post-import composition change | Automatic refund/return/credit-note accounting |
| Fulfillment | Accepted Mode 1/Mode 2 behavior, full/partial delivery, tracking, notification choice, idempotent replay and reconciliation | Remote conflict, cancellation, unsafe or uncertain outcome | Any accounting behavior outside the accepted fulfillment modes |
| Webhooks | Raw-body HMAC, durable payload-free receipt, deduplication, freshness, generation fence, scheduled backstop | Downstream failure or unsafe terminal job disposition | Treating acceleration as the sole correctness mechanism |

Product status is seeded from Shopify on import but is not exported unless the operator explicitly takes ownership by changing status. An imported ACTIVE product therefore remains published after a title-only export.

## Enforced public limits

| Boundary | V1 limit | Enforcement/evidence |
|---|---:|---|
| Stores per database | 10 | Essential readiness check |
| Products per store | 100,000 | Essential readiness check; resumable 10-page scan slices |
| Variants per product | 100 | Export preflight and Shopify validation; documented fail-closed boundary |
| Orders retained/imported per store window | 100,000 | Essential readiness population check; resumable 10-page scan slices |
| Inventory pairs per store | 100,000 | Essential readiness check; 200-row scan slices |
| Fulfillment bindings per store | 100,000 | Essential readiness check; 200-row reconciliation slices |
| Jobs admitted per store per minute | 1,000 | Essential readiness check and queue load gate |
| Queue drain | 50 jobs/pass by default, configurable 1–500 | Time-budgeted fair round-robin; enqueue wakeup plus cron fallback |
| Expected reconciliation delay | 60 minutes under supported load | Health/readiness freshness and cron evidence |
| Terminal low-risk jobs | 90 days | Bounded 2,000-row retention pass |
| Layer-2 resolved evidence detail | 180 days before masking | Unresolved evidence is never masked or deleted |
| Webhook envelopes | 30 days | Bounded 2,000-row deletion pass |

Exceeding an enforced population or recent-arrival boundary fails the essential `Supported deployment size` readiness check. These are supported limits, not claims of unlimited scale.
