# Goal 1 Manifest — Product Behavior Contract

Date: 2026-06-12
Branch observed: `work` harness checkout for selected branch `claude/codex`.
Base for diff: `620a749` (Goal 0 operating docs present); Goal 0 base ancestor `e9357de` also present.

## Scope

Goal 1 is a read-code / write-docs goal. Production code is read-only. Writes are limited to the C1-allowed files.

## Source layout inspected

### `addons/shopify_connector_pro/sync/`
- `abandoned_cart_sync.py`, `accounting.py`, `base_exporter.py`, `base_importer.py`, `checksum.py`, `collection_export.py`, `collection_sync.py`, `customer_sync.py`, `customer_tag_sync.py`, `discount_import_sync.py`, `discount_sync.py`, `fulfillment_sync.py`, `gift_card_sync.py`, `inventory_sync.py`, `location_sync.py`, `metafield_sync.py`, `order_sync.py`, `payment_status_sync.py`, `payout_sync.py`, `product_sync.py`, `refund_sync.py`

### `addons/shopify_connector_pro/models/`
- `account_move.py`, `product_product.py`, `product_template.py`, `res_partner.py`, `sale_order.py`, `shopify_abandoned_cart.py`, `shopify_backend.py`, `shopify_binding.py`, `shopify_collection_binding.py`, `shopify_customer_binding.py`, `shopify_discount_code.py`, `shopify_discount_usage.py`, `shopify_field_mapping.py`, `shopify_gift_card.py`, `shopify_import_job.py`, `shopify_inventory_binding.py`, `shopify_location.py`, `shopify_metafield.py`, `shopify_metafield_mapping.py`, `shopify_order_binding.py`, `shopify_order_transaction.py`, `shopify_payment_gateway.py`, `shopify_payout.py`, `shopify_product_binding.py`, `shopify_promoter.py`, `shopify_reconciliation.py`, `shopify_refund_binding.py`, `shopify_refund_line.py`, `shopify_sync_log.py`, `shopify_tax_mapping.py`, `shopify_variant_binding.py`, `shopify_webhook_log.py`, `stock_move.py`, `stock_picking.py`

### `addons/shopify_connector_pro/controllers/`
- `webhook.py`

### `addons/shopify_connector_pro/shopify_api/`
- `client.py`, `rate_limiter.py`

### `addons/shopify_connector_pro/wizards/`
- `shopify_bulk_export_wizard.py`, `shopify_bulk_retry_wizard.py`, `shopify_demo_data_wizard.py`, `shopify_import_wizard.py`, `shopify_onboarding_wizard.py`, `shopify_sync_wizard.py`

## Contract section map

### Cluster A — Setup & products
- Setup — candidates: `wizards/shopify_onboarding_wizard.py`, `models/shopify_backend.py`, `wizards/shopify_import_wizard.py`.
- Initial product import — candidates: `sync/product_sync.py`, `models/shopify_product_binding.py`, `models/shopify_variant_binding.py`.
- Product update Odoo → Shopify — candidates: `sync/product_sync.py`, `models/product_template.py`, `models/product_product.py`, `sync/base_exporter.py`.
- Inventory sync — candidates: `sync/inventory_sync.py`, `models/shopify_inventory_binding.py`, `models/stock_move.py`.
- Product deleted/archived — candidates: `sync/product_sync.py`, `models/shopify_product_binding.py`.
- Settings changed after go-live — candidates: `models/shopify_backend.py`, `wizards/shopify_onboarding_wizard.py`.

### Cluster B — Orders & money
- New paid Shopify order — candidates: `sync/order_sync.py`, `sync/payment_status_sync.py`, `models/shopify_order_binding.py`.
- Unpaid/pending Shopify order — candidates: `sync/order_sync.py`, `sync/payment_status_sync.py`.
- Missing product on order import — candidates: `sync/order_sync.py`.
- Missing tax mapping — candidates: `sync/order_sync.py`, `models/shopify_tax_mapping.py`.
- Currency/rate missing — candidates: `sync/order_sync.py`, `sync/refund_sync.py`.
- Payouts — candidates: `sync/payout_sync.py`, `models/shopify_payout.py`.
- Reconciliation — candidates: `models/shopify_reconciliation.py`, `models/shopify_backend.py`.
- Total-check guard — candidates: `sync/accounting.py`, `sync/payment_status_sync.py`, `sync/order_sync.py`, relevant tests.

### Cluster C — Fulfillment & refunds
- Odoo delivery → Shopify fulfillment — candidates: `sync/fulfillment_sync.py`, `models/stock_picking.py`.
- Shopify fulfillment → Odoo delivery — candidates: `sync/fulfillment_sync.py`, `sync/order_sync.py`, `models/stock_picking.py`.
- Shopify refund → Odoo credit note — candidates: `sync/refund_sync.py`, `models/shopify_refund_binding.py`, `models/shopify_refund_line.py`.
- Odoo credit note → Shopify refund — candidates: `models/account_move.py`, `sync/refund_sync.py`.
- Abandoned cart → quotation — candidates: `sync/abandoned_cart_sync.py`, `models/shopify_abandoned_cart.py`.

### Cluster D — Platform & edge
- Gift cards — candidates: `sync/gift_card_sync.py`, `models/shopify_gift_card.py`.
- Promoters/discounts — candidates: `sync/discount_sync.py`, `sync/discount_import_sync.py`, `models/shopify_promoter.py`, `models/shopify_discount_code.py`.
- Metafields — candidates: `sync/metafield_sync.py`, `models/shopify_metafield.py`, `models/shopify_metafield_mapping.py`.
- Multi-store — candidates: `models/shopify_backend.py`, binding models, import/export domains.
- Multi-company — candidates: `models/shopify_backend.py`, binding models, security record rules (read-only evidence only).
- Shopify Markets/B2B — candidates: `sync/order_sync.py`, `models/shopify_backend.py`.
- Duplicate webhook — candidates: `controllers/webhook.py`, `models/shopify_webhook_log.py`.
- API throttling — candidates: `shopify_api/client.py`, `shopify_api/rate_limiter.py`.

## As-executed notes

- T0 committed before behavior contract edits.
- T1 verifies DEC-024 before broader contract filling.

## Final as-executed summary

- T1 closed DEC-024 with `DEC-024-CLOSE` after verifying guard code and tests.
- T2 filled all 27 behavior contract sections in four cluster commits.
- T3 filled 15 sync ownership matrix rows.
- T4 appended Goal 1 coverage debt to `COVERAGE.md` without populating normal coverage rows.
- T5 appended AUD-027, AUD-028, and AUD-029; no code was fixed.
- T6 appended three Ahmed escalation statements to `docs/architecture/DECISIONS.md`.
- T7 updated this manifest and `STATUS.md` for handoff.
