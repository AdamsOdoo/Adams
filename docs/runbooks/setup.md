# Setup runbook

1. Install the connector addons appropriate to the selected domains. Use the pinned Odoo 19 source and upgrade all installed connector addons together.
2. In Shopify Admin, create a merchant-managed custom app for the exact permanent `*.myshopify.com` store. This module is not installed through the Shopify App Store.
3. Grant the scopes shown by the connector. The baseline read set is `read_products`, `read_customers`, `read_orders`, `read_inventory`, `read_locations`, and `read_merchant_managed_fulfillment_orders`; enabled write domains additionally require their displayed write scopes.
4. Enter the permanent myshopify domain and credential through the guided write-only form. Never paste a credential into logs, screenshots, source, fixtures, or support messages.
5. Run identity, credential, scope, API-version, and webhook checks. Correct any mismatch; do not override an essential failure.
6. Select domains and authorities. Inventory must state Odoo as authority. Shopify quantity is read only for comparison.
7. Map every push-enabled Shopify location to an Odoo internal location.
8. Review product/price authority and notification choices.
9. Generate every inventory first-push preview. If quantity changes, regenerate; stale previews cannot be confirmed.
10. Run final readiness. `Connected — Initial Sync Pending` is not `Ready`.
11. Activate. Activation starts selected read/import scans. It writes nothing to Shopify until a protected preview/confirmation or supported fulfillment action is completed.
12. Follow initial-sync progress and resolve blocking exceptions. Ready requires complete fresh producer/child evidence, mappings, first-push decisions, and no blocking exception.

Wrong domains, identity mismatches, missing scopes, invalid credentials, unsupported scale, or stale evidence are fail-closed setup results.
