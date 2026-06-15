# COVERAGE.md — Coverage Scaffold

> **SCAFFOLD — population is Goal 6.**

Purpose: **unmapped = untested = not done**.

This file will become the coverage map for workflows, buttons, crons, webhooks, negative paths, security paths, accounting paths, and UI paths. Goal 0 creates only the scaffold; no rows should be fabricated.

Button enumeration must come from XML views, not memory.

## Coverage Table Schema

| Surface | Type: workflow/button/cron/webhook/negative/security/accounting/ui | Test file::method | Profile | Status | Evidence |
|---|---|---|---|---|---|

No coverage rows are populated yet because Goal 6 owns verified population.

## Goal 1 identified coverage debt

Population remains Goal 6; this list only flags Goal 1 contract paths where no direct test citation was found during code reading.

- Setup → onboarding wizard connection/backend/webhook/import error visibility needs direct tests.
- Initial product import → SKU match, option/index variant matching, image failure, and binding idempotency need direct tests.
- Product update Odoo → Shopify → productSet/productUpdate/variant bulk update and export error marking need direct tests.
- Inventory sync → location/warehouse mapping, compareQuantity stale failure, and binding update need direct tests.
- Product deleted/archived → archive/delete lifecycle not specified or tested.
- Settings changed after go-live → DEC-020 lock/unlock/validation gap needs tests after implementation.
- Unpaid/pending Shopify order → transition table and activity/error behavior need direct tests.
- Missing product on order import → unresolved product-line policy needs direct tests after decision.
- Missing tax mapping → dropped-tax activity and guard interaction need direct tests.
- Currency/rate missing → visible error-state binding and retry path need direct tests.
- Payouts → payout import, transaction type fallback, missing currency, and accounting decision need tests.
- Reconciliation → mismatch sync-log creation and retry reset need tests.
- Shopify fulfillment → Odoo delivery → inbound modes, partial fulfillment limitation, and auto-validation failure need tests.
- Shopify refund → Odoo credit note → refund GID recovery, currency mismatch, over-refund, and tax fallback need direct tests.
- Odoo credit note → Shopify refund → reverse refund push, failure activity, and idempotency policy need tests.
- Abandoned cart → quotation → quote creation, unresolved product note line, currency pricelist fallback, and tag gap need tests.
- Gift cards → import/update/error handling and future liability behavior need tests.
- Promoters/discounts → discount export/import and promoter linkage need tests.
- Metafields → mapping import/export and conflict behavior need tests.
- Multi-store → backend-scoped binding/webhook isolation needs tests.
- Multi-company → company context and record-rule behavior needs tests.
- Shopify Markets/B2B → presentment currency behavior and B2B-specific gaps need tests.
- Duplicate webhook → per-backend webhook ID dedup, fingerprint fallback, stale payload, and dead-letter retry need tests.
- API throttling → rate limiter adaptation, Retry-After, circuit breaker, and sanitized errors need tests.

## Goal 2 Phase B verified feature-flag rows

These rows are populated now because Goal 2B introduced production feature-flag surfaces and matching tests.

| Surface | Type: workflow/button/cron/webhook/negative/security/accounting/ui | Test file::method | Profile | Status | Evidence |
|---|---|---|---|---|---|
| Backend feature-flag defaults | workflow | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_new_defaults_preserve_current_optional_behavior` | Local static check; Odoo runtime pending relay | Implemented | New backend defaults preserve current optional behavior for promoters, payouts, gift cards, metafields, and customer tags. |
| Feature-flag admin-only editing | security | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_admin_only_non_admin_cannot_flip_flags` | Local static check; Odoo runtime pending relay | Implemented | Non-admin Shopify users cannot write feature-flag fields. |
| Upgrade/default preservation | workflow | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_upgrade_seed_preserves_reused_fields_and_new_defaults` | Local static check; Odoo runtime pending relay | Implemented | Preserves `reverse_sync_refund=True`, `external_fulfillment_handling='auto_validate'`, `import_currency_mode='presentment'`, and seeds new fields explicitly. |
| Promoter discount cron disabled | cron/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_promoter_cron_off_logs_visible_skip` | Local static check; Odoo runtime pending relay | Implemented | OFF creates a `shopify.sync.log` skipped record and does not call discount export. |
| Collections cron disabled | cron/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_collections_reused_toggle_off_logs_visible_skip` | Local static check; Odoo runtime pending relay | Implemented | Reused `auto_sync_collections`; OFF creates a visible skipped sync log. |
| Payout import cron disabled | cron/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_payout_cron_off_logs_visible_skip` | Local static check; Odoo runtime pending relay | Implemented | OFF creates a visible skipped sync log and does not call `PayoutSync.import_payouts`. |
| Abandoned-cart import cron disabled | cron/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_abandoned_cart_reused_toggle_off_logs_visible_skip` | Local static check; Odoo runtime pending relay | Implemented | Reused `auto_sync_abandoned_carts`; OFF creates a visible skipped sync log. |
| Gift-card import disabled | workflow/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_gift_card_off_logs_skip_before_api_client` | Local static check; Odoo runtime pending relay | Implemented | OFF logs a skip before creating a Shopify API client. |
| Metafield import disabled | workflow/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_metafield_off_logs_skip_before_api_client` | Local static check; Odoo runtime pending relay | Implemented | OFF logs a skip before creating a Shopify API client. |
| Feature menu/action filtering | ui | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagMechanism.test_menu_actions_filter_disabled_backend_records` | Local static check; Odoo runtime pending relay | Implemented | Menu actions filter records by backend feature flag/reused toggle. |
| AUD-029 reverse refund push disabled | accounting/negative | `addons/shopify_connector_pro/tests/test_feature_flags.py::TestFeatureFlagReverseRefundMoneyPath.test_aud_029_reverse_refund_off_does_not_call_refund_create` | Local static check; Odoo runtime pending relay | Implemented | Posting a real `out_refund` credit note with `reverse_sync_refund=False` does not create a Shopify API client/refund mutation. |


## Goal 3 Phase B UI surface rows

Menu/button surface inventory is recorded here for Goal 6 mapping. Test references are intentionally not fabricated; Goal 6 owns final test mapping.

| Surface | Type: workflow/button/cron/webhook/negative/security/accounting/ui | Test file::method | Profile | Status | Evidence |
|---|---|---|---|---|---|
| Shopify root menu | menu | Goal 6 mapping pending | Local XML parse/reference check | present | `addons/shopify_connector_pro/views/shopify_menu.xml` |
| Store Overview menu | menu | Goal 6 mapping pending | Local XML parse/reference check | present | `menu_shopify_dashboard` -> `shopify_dashboard_action` |
| Manager Dashboard menu | menu | Goal 6 mapping pending | Local XML parse/reference check | present | `menu_shopify_manager_dashboard` -> `action_manager_dashboard` |
| Catalog Sync menu group | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Products, Inventory, Collections, Metafields, Locations |
| Sales Sync menu group | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Customers, Orders, Refunds, Transactions |
| Advanced / Optional Data menu group | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Abandoned Carts, Payouts, Gift Cards, Customer Tags, Promoters, Discount Codes, Discount Usage |
| Configuration menu group | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Admin configuration menus retained |
| Operations menu group | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Sync/import/retry/export/import jobs retained |
| Generate Demo Data menu | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Gated to `base.group_no_one` |
| Logs & Audit menu group | menu | Goal 6 mapping pending | Local XML parse/reference check | present | Sync Log, Webhook Log, Sync Analytics |
| Binding retry buttons | ui/button | Goal 6 mapping pending | Phase A XML inventory | present | Retry buttons on product/customer/order/inventory/collection/refund/discount bindings |
| Backend connection/webhook/action buttons | ui/button | Goal 6 mapping pending | Phase A XML inventory | present | Backend form buttons for test connection, webhooks, import locations, sync logs, reconciliation |
| Abandoned cart recovery buttons | ui/button | Goal 6 mapping pending | Phase A XML inventory | present | Create Quotation, Open Recovery URL, Mark Recovered |
| Wizard action buttons | ui/button | Goal 6 mapping pending | Phase A XML inventory | present | Sync/import/export/retry/onboarding/demo wizard buttons |
| Promoter stat buttons | ui/button | Goal 6 mapping pending | Phase A XML inventory | present | Present but AUD-032 open: `action_dummy` stubs deferred to Goal 8 |
