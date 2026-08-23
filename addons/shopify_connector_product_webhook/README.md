# Shopify Connector Product Webhooks (W2)

This addon is the bounded product-domain slice of the connector webhook
pipeline. It activates exactly:

- `products/create`
- `products/update`
- `products/delete`

The generic webhook addon verifies the HTTPS request, HMAC, shop identity,
delivery ID and raw
payload digest before persisting a payload-free evidence envelope. The W2
handler then:

1. resolves the store from that verified delivery row;
2. requires Shopify's explicit `admin_graphql_api_id` with a
   `gid://shopify/Product/` type (it never constructs a GID from numeric `id`);
3. checks the connected store, company/store scope, current connection
   generation and product inbound ownership;
4. admits one existing `product_import_sync` child job through the core enqueue
   service, keyed by Shopify's canonical `updatedAt` stamp when available and
   scoped so duplicate or overlapping deliveries coalesce;
5. returns operator evidence that the child job will perform the authoritative
   Shopify read.

For `products/delete`, that read returns no Shopify node; the existing importer
marks the product and variant bindings stale for review and never deletes or
archives the Odoo product.

No Shopify API call is made while processing a webhook. The child importer is
the only remote-read path, and the scheduled product scan remains the fallback
for missed, delayed or out-of-order delivery. The importer extension takes a
binding row lock and rejects a comparable `updatedAt` older than the stored
successful snapshot, preserving monotonic product evidence.

The Product webhook topic payloads are documented by Shopify's current Admin
GraphQL webhook reference:
<https://shopify.dev/docs/api/webhooks/latest/products/update>.
