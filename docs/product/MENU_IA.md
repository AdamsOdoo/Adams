# PHASE A PROPOSAL — implementation pending Phase B GO

## 1. Executive summary

Goal 3 Phase A is research/planning only. No code, XML, security, manifest, test, sync, migration, hook, README, or AUDIT file is changed by this proposal.

Current IA has one live Shopify root tree from `addons/shopify_connector_pro`, with two live dashboard entries: `Store Overview` using `shopify_dashboard_action` and `Manager Dashboard` using `action_manager_dashboard` from the connector module. The companion `shopify_connector_pro_dashboard` module is a hollow/stub module whose manifest has `data: []` and `assets: {}`, so its dashboard XML files are defined in the repository but not loaded by the running app. The current live tree also exposes admin-only operations under an `Operations` section, including `Generate Demo Data`. Phase B should keep core operations visible, gate setup/configuration and destructive/demo operations for admins, and regroup flag-gated advanced actions so disabled features do not create confusing gaps.

## 2. Current menu tree

### Full current menu inventory

| XML id | Name | Parent | Seq | Action | Groups | Action/domain | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| menu_shopify_root | Shopify | (root) | 50 | (none) | shopify_connector_pro.group_shopify_user | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:5 |
| menu_shopify_dashboard | Store Overview | menu_shopify_root | 10 | shopify_dashboard_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:12 |
| menu_shopify_manager_dashboard | Manager Dashboard | menu_shopify_root | 15 | action_manager_dashboard | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:19 |
| menu_shopify_configuration | Configuration | menu_shopify_root | 20 | (none) | shopify_connector_pro.group_shopify_admin | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:26 |
| menu_shopify_stores | Shopify Stores | menu_shopify_configuration | 10 | shopify_backend_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:32 |
| menu_shopify_setup_wizard | Setup Wizard | menu_shopify_configuration | 20 | shopify_onboarding_wizard_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:38 |
| menu_shopify_payment_gateways | Payment Gateways | menu_shopify_configuration | 30 | shopify_payment_gateway_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:44 |
| menu_shopify_tax_mappings | Tax Mappings | menu_shopify_configuration | 40 | shopify_tax_mapping_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:50 |
| menu_shopify_metafield_mappings | Metafield Mappings | menu_shopify_configuration | 50 | shopify_metafield_mapping_action | (inherits/default) | [('backend_id.enable_metafields', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:56 |
| menu_shopify_operations | Operations | menu_shopify_root | 30 | (none) | shopify_connector_pro.group_shopify_admin | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:63 |
| menu_shopify_sync_now | Sync Now | menu_shopify_operations | 10 | shopify_sync_wizard_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:69 |
| menu_shopify_import_data | Import Data | menu_shopify_operations | 20 | shopify_import_wizard_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:75 |
| menu_shopify_bulk_retry | Retry Failed Records | menu_shopify_operations | 30 | shopify_bulk_retry_wizard_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:81 |
| menu_shopify_bulk_export | Bulk Export | menu_shopify_operations | 40 | shopify_bulk_export_wizard_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:87 |
| menu_shopify_import_jobs | Import Jobs | menu_shopify_operations | 50 | shopify_import_job_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:93 |
| menu_shopify_demo_data | Generate Demo Data | menu_shopify_operations | 90 | shopify_demo_data_wizard_action | shopify_connector_pro.group_shopify_admin | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:99 |
| menu_shopify_sync_status | Sync Status | menu_shopify_root | 40 | (none) | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:107 |
| menu_shopify_products | Products | menu_shopify_sync_status | 10 | shopify_product_binding_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:112 |
| menu_shopify_customers | Customers | menu_shopify_sync_status | 20 | shopify_customer_binding_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:118 |
| menu_shopify_orders | Orders | menu_shopify_sync_status | 30 | shopify_order_binding_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:124 |
| menu_shopify_inventory | Inventory | menu_shopify_sync_status | 40 | shopify_inventory_binding_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:130 |
| menu_shopify_collections | Collections | menu_shopify_sync_status | 50 | shopify_collection_binding_action | (inherits/default) | [('backend_id.auto_sync_collections', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:136 |
| menu_shopify_refunds | Refunds | menu_shopify_sync_status | 55 | shopify_refund_binding_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:142 |
| menu_shopify_locations | Locations | menu_shopify_sync_status | 60 | shopify_location_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:148 |
| menu_shopify_sync_additional | Additional Data | menu_shopify_sync_status | 100 | (none) | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:155 |
| menu_shopify_abandoned_carts | Abandoned Carts | menu_shopify_sync_additional | 10 | shopify_abandoned_cart_action | (inherits/default) | [('backend_id.auto_sync_abandoned_carts', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:160 |
| menu_shopify_transactions | Transactions | menu_shopify_sync_additional | 20 | shopify_order_transaction_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:166 |
| menu_shopify_payouts | Payouts | menu_shopify_sync_additional | 30 | shopify_payout_action | (inherits/default) | [('backend_id.enable_payout_import', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:172 |
| menu_shopify_gift_cards | Gift Cards | menu_shopify_sync_additional | 40 | shopify_gift_card_action | (inherits/default) | [('backend_id.enable_gift_cards', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:178 |
| menu_shopify_customer_tags | Customer Tags | menu_shopify_sync_additional | 50 | shopify_customer_tag_action | (inherits/default) | [('backend_id.enable_customer_tags', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:184 |
| menu_shopify_metafields | Metafields | menu_shopify_sync_additional | 60 | shopify_metafield_action | (inherits/default) | [('backend_id.enable_metafields', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:190 |
| menu_shopify_promoters_section | Promoters | menu_shopify_root | 45 | (none) | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:197 |
| menu_shopify_promoters | Promoters | menu_shopify_promoters_section | 10 | shopify_promoter_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:202 |
| menu_shopify_discount_codes | Discount Codes | menu_shopify_promoters_section | 20 | shopify_discount_code_action | (inherits/default) | [('backend_id.enable_promoters', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:208 |
| menu_shopify_discount_usage | Discount Usage | menu_shopify_promoters_section | 30 | shopify_discount_usage_action | (inherits/default) | [('backend_id.enable_promoters', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:214 |
| menu_shopify_logs | Logs | menu_shopify_root | 50 | (none) | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:221 |
| menu_shopify_sync_log | Sync Log | menu_shopify_logs | 10 | shopify_sync_log_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:226 |
| menu_shopify_webhook_log | Webhook Log | menu_shopify_logs | 20 | shopify_webhook_log_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:232 |
| menu_shopify_sync_analytics | Sync Analytics | menu_shopify_logs | 30 | shopify_sync_analytics_action | (inherits/default) | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:238 |
| menu_shopify_manager_root | Shopify Manager | (root) | 51 | (none) | shopify_connector_pro.group_shopify_user | (none) | addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml:8 — DEFINED in shopify_connector_pro_dashboard but NOT LOADED because manifest data is empty (`addons/shopify_connector_pro_dashboard/__manifest__.py:19`) |
| menu_shopify_manager_dashboard | Dashboard | menu_shopify_manager_root | 10 | action_manager_dashboard | (inherits/default) | (none) | addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml:14 — DEFINED in shopify_connector_pro_dashboard but NOT LOADED because manifest data is empty (`addons/shopify_connector_pro_dashboard/__manifest__.py:19`) |

### Tree shape

- Shopify (`menu_shopify_root`, user group) — source `addons/shopify_connector_pro/views/shopify_menu.xml:5`
  - Store Overview — `shopify_dashboard_action`, source `addons/shopify_connector_pro/views/shopify_menu.xml:12`
  - Manager Dashboard — `action_manager_dashboard`, source `addons/shopify_connector_pro/views/shopify_menu.xml:19`
  - Configuration (admin group) — source `addons/shopify_connector_pro/views/shopify_menu.xml:26`
    - Shopify Stores; Setup Wizard; Payment Gateways; Tax Mappings; Metafield Mappings
  - Operations (admin group) — source `addons/shopify_connector_pro/views/shopify_menu.xml:63`
    - Sync Now; Import Data; Retry Failed Records; Bulk Export; Import Jobs; Generate Demo Data
  - Sync Status — source `addons/shopify_connector_pro/views/shopify_menu.xml:107`
    - Products; Customers; Orders; Inventory; Collections; Refunds; Locations; Additional Data
  - Promoters — source `addons/shopify_connector_pro/views/shopify_menu.xml:197`
  - Logs — source `addons/shopify_connector_pro/views/shopify_menu.xml:221`
- Not live: `shopify_connector_pro_dashboard` defines `Shopify Manager` and child `Dashboard` XML at `addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml:8` and `:14`, but the module manifest has `data: []` and `assets: {}` at `addons/shopify_connector_pro_dashboard/__manifest__.py:19-20`, so those XML files are orphaned / not loaded.

Live-tree accuracy: the running app has one live Shopify root tree from `addons/shopify_connector_pro/views/shopify_menu.xml:5`; within that one tree, `Store Overview` uses `shopify_dashboard_action` at `addons/shopify_connector_pro/views/shopify_menu.xml:12-16`, and `Manager Dashboard` uses connector-module `action_manager_dashboard` at `addons/shopify_connector_pro/views/shopify_menu.xml:19-23` plus `addons/shopify_connector_pro/views/manager_dashboard_action.xml:3-6`.

## 3. Current button inventory

| String | Type | Name/method/action | Model | View | Core/advanced | Recommended role visibility | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Retry | object | action_retry_sync | product.template | product_template_form_shopify | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/product_template_views.xml:26 |
| View on Shopify | object | action_view_on_shopify | product.template | product_template_form_shopify | Core | User | addons/shopify_connector_pro/views/product_template_views.xml:29 |
| Retry | object | action_retry_sync | res.partner | res_partner_form_shopify | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/res_partner_views.xml:26 |
| View on Shopify | object | action_view_on_shopify | res.partner | res_partner_form_shopify | Core | User | addons/shopify_connector_pro/views/res_partner_views.xml:29 |
| View on Shopify | object | action_view_on_shopify | sale.order | sale_order_form_shopify | Core | User | addons/shopify_connector_pro/views/sale_order_views.xml:37 |
| Retry | object | action_retry_sync | sale.order | sale_order_form_shopify | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/sale_order_views.xml:40 |
| Create Quotation | object | action_create_quotation | shopify.abandoned.cart | shopify_abandoned_cart_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_abandoned_cart_views.xml:40 |
| Open Recovery URL | object | action_open_recovery_url | shopify.abandoned.cart | shopify_abandoned_cart_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_abandoned_cart_views.xml:45 |
| Mark Recovered | object | action_mark_recovered | shopify.abandoned.cart | shopify_abandoned_cart_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_abandoned_cart_views.xml:50 |
| Test Connection | object | action_test_connection | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:30 |
| Re-test Connection | object | action_test_connection | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:33 |
| Register Webhooks | object | action_register_webhooks | shopify.backend | shopify_backend_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:36 |
| Import Locations | object | action_import_locations | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:40 |
| Products | object | action_open_product_bindings | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:49 |
| Customers | object | action_open_customer_bindings | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:54 |
| Orders | object | action_open_order_bindings | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:59 |
| Inventory | object | action_open_inventory_bindings | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:64 |
| (stat/no string) | object | action_open_sync_logs | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:69 |
| (stat/no string) | object | action_open_shopify_admin | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:73 |
| Load Default Mappings | object | action_init_field_mappings | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:209 |
| Register All Webhooks | object | action_register_webhooks | shopify.backend | shopify_backend_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:264 |
| Check Status | object | action_check_webhook_status | shopify.backend | shopify_backend_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:268 |
| Unregister All | object | action_unregister_webhooks | shopify.backend | shopify_backend_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:272 |
| View Webhook Logs | object | action_open_webhook_logs | shopify.backend | shopify_backend_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:277 |
| Test Connection | object | action_test_connection | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:401 |
| Retry All Errors | object | action_retry_all_errors | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:403 |
| View Sync Logs | object | action_open_sync_logs | shopify.backend | shopify_backend_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:407 |
| View Error Details | object | action_open_error_bindings | shopify.backend | shopify_backend_view_form | Core | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:409 |
| Payment Mismatches | object | action_open_payment_mismatches | shopify.backend | shopify_backend_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:412 |
| Fulfillment Mismatches | object | action_open_fulfillment_mismatches | shopify.backend | shopify_backend_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_backend_views.xml:415 |
| Run Reconciliation | object | action_run_reconciliation | shopify.backend | shopify_backend_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_backend_views.xml:418 |
| Retry Sync | object | action_retry_sync | shopify.collection.binding | shopify_collection_binding_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_collection_binding_views.xml:31 |
| Retry Sync | object | action_retry_sync | shopify.customer.binding | shopify_customer_binding_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_customer_binding_views.xml:32 |
| Push to Shopify | object | action_push_to_shopify | shopify.discount.code | shopify_discount_code_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_discount_code_views.xml:32 |
| Re-push to Shopify | object | action_push_to_shopify | shopify.discount.code | shopify_discount_code_view_form | Advanced | User | addons/shopify_connector_pro/views/shopify_discount_code_views.xml:35 |
| Retry | object | action_retry_sync | shopify.discount.code | shopify_discount_code_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_discount_code_views.xml:38 |
| Cancel | object | action_cancel | shopify.import.job | shopify_import_job_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_import_job_views.xml:37 |
| Retry Sync | object | action_retry_sync | shopify.inventory.binding | shopify_inventory_binding_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_inventory_binding_views.xml:34 |
| Retry Sync | object | action_retry_sync | shopify.order.binding | shopify_order_binding_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_order_binding_views.xml:32 |
| Retry Sync | object | action_retry_sync | shopify.product.binding | shopify_product_binding_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_product_binding_views.xml:33 |
| Orders | object | action_dummy | shopify.promoter | shopify_promoter_view_form | Advanced — STUB (action_dummy) | User; report-only defect for Phase A | addons/shopify_connector_pro/views/shopify_promoter_views.xml:32 |
| Revenue | object | action_dummy | shopify.promoter | shopify_promoter_view_form | Advanced — STUB (action_dummy) | User; report-only defect for Phase A | addons/shopify_connector_pro/views/shopify_promoter_views.xml:35 |
| Discounts | object | action_dummy | shopify.promoter | shopify_promoter_view_form | Advanced — STUB (action_dummy) | User; report-only defect for Phase A | addons/shopify_connector_pro/views/shopify_promoter_views.xml:38 |
| Commission | object | action_dummy | shopify.promoter | shopify_promoter_view_form | Advanced — STUB (action_dummy) | User; report-only defect for Phase A | addons/shopify_connector_pro/views/shopify_promoter_views.xml:41 |
| Retry Sync | object | action_retry_sync | shopify.refund.binding | shopify_refund_binding_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_refund_binding_views.xml:30 |
| View Failed Records | object | action_open_error_bindings | shopify.sync.log | shopify_sync_log_view_form | Core | User | addons/shopify_connector_pro/views/shopify_sync_log_views.xml:37 |
| Retry | object | action_retry_webhook | shopify.webhook.log | shopify_webhook_log_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/views/shopify_webhook_log_views.xml:34 |
| Export | object | action_export | shopify.bulk.export.wizard | shopify_bulk_export_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_bulk_export_wizard_views.xml:19 |
| Cancel | special=cancel | cancel | shopify.bulk.export.wizard | shopify_bulk_export_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_bulk_export_wizard_views.xml:21 |
| Retry All | object | action_retry | shopify.bulk.retry.wizard | shopify_bulk_retry_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_bulk_retry_wizard_views.xml:14 |
| Cancel | special=cancel | cancel | shopify.bulk.retry.wizard | shopify_bulk_retry_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_bulk_retry_wizard_views.xml:15 |
| Generate Demo Data | object | action_seed | shopify.demo.data.wizard | shopify_demo_data_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_demo_data_wizard_views.xml:37 |
| Cancel | special=cancel | cancel | shopify.demo.data.wizard | shopify_demo_data_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_demo_data_wizard_views.xml:39 |
| Start Import | object | action_import | shopify.import.wizard | shopify_import_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_import_wizard_views.xml:26 |
| Cancel | special=cancel | cancel | shopify.import.wizard | shopify_import_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_import_wizard_views.xml:28 |
| Test Connection &amp; Next | object | action_test_connection | shopify.onboarding.wizard | shopify_onboarding_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:78 |
| Next | object | action_next_to_webhooks | shopify.onboarding.wizard | shopify_onboarding_wizard_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:84 |
| Create Store &amp; Next | object | action_next_to_import | shopify.onboarding.wizard | shopify_onboarding_wizard_view_form | Advanced | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:89 |
| Import &amp; Finish | object | action_finish | shopify.onboarding.wizard | shopify_onboarding_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:95 |
| Skip Import | object | action_skip_import | shopify.onboarding.wizard | shopify_onboarding_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:99 |
| Cancel | special=cancel | cancel | shopify.onboarding.wizard | shopify_onboarding_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:103 |
| Start Sync | object | action_sync | shopify.sync.wizard | shopify_sync_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_sync_wizard_views.xml:24 |
| Cancel | special=cancel | cancel | shopify.sync.wizard | shopify_sync_wizard_view_form | Core | Admin for mutating/recovery operations; User for read-only/open links | addons/shopify_connector_pro/wizards/shopify_sync_wizard_views.xml:26 |

## 4. Role / visibility map

### Security groups

| Group XML id | Name | Source | Current comment |
| --- | --- | --- | --- |
| group_shopify_user | User | addons/shopify_connector_pro/security/shopify_security.xml:22 | View Shopify sync status, orders, products, logs, and dashboard. Cannot configure backends or run sync operations. |
| group_shopify_admin | Administrator | addons/shopify_connector_pro/security/shopify_security.xml:34 | Full access to Shopify configuration, sync operations, wizards, backend settings, and all module features. |

### Menu visibility observations

- `menu_shopify_root` is explicitly limited to `shopify_connector_pro.group_shopify_user`, so normal Shopify users enter the app from the root menu.
- `menu_shopify_configuration` and `menu_shopify_operations` are explicitly admin-only; their children inherit that parent visibility unless they add stricter groups.
- `Generate Demo Data` also repeats `shopify_connector_pro.group_shopify_admin`, but it remains an easy admin-facing merchant action and should be gated further in Phase B.
- Sync Status, Promoters, and Logs are default-visible under the user-limited Shopify root. Their action domains, not menu groups, currently hide data for disabled feature flags.
- Core operational menus hidden from normal operators: `Sync Now`, `Import Data`, retry/export operations, and import jobs are under the admin-only Operations parent.
- Configuration/admin menus visible to non-admins: none directly found in menu XML; however advanced operational data under Sync Status/Promoters/Logs is user-visible unless the target action domain filters it.

## 5. Five IA decisions

### Decision 1 — One live tree with two dashboard entries, plus hollow companion dashboard module XML

Current evidence: the live connector menu exposes `Store Overview` at `addons/shopify_connector_pro/views/shopify_menu.xml:12-16` and `Manager Dashboard` at `addons/shopify_connector_pro/views/shopify_menu.xml:19-23`; connector-module `action_manager_dashboard` is defined at `addons/shopify_connector_pro/views/manager_dashboard_action.xml:3-6`. The companion dashboard module is a hollow/stub module: its manifest says it was merged into `shopify_connector_pro`, depends on the connector, and has `data: []` plus `assets: {}` at `addons/shopify_connector_pro_dashboard/__manifest__.py:5-20`. Therefore its XML files `addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml:8-18` and `addons/shopify_connector_pro_dashboard/views/manager_dashboard_action.xml:3-6` are orphaned / not loaded, and the running app does not have a second live `Shopify Manager` dashboard tree from that module.

Options:
1. Keep both live dashboard entries under the one Shopify root if Phase B confirms they render distinct content.
2. Consolidate to one dashboard entry if Phase B confirms `Store Overview` and `Manager Dashboard` are redundant.
3. Separately decide the fate of `shopify_connector_pro_dashboard`: delete orphaned XML in an upgrade-safe step, fold surviving assets/views into `shopify_connector_pro`, or formally tombstone the module.

Recommendation: keep `Store Overview` + `Manager Dashboard` with role-clear labels only if Phase B confirms they render distinct content; consolidate to one dashboard if they are redundant. Treat the companion dashboard module fate as a separate upgrade-safety decision, following the `shopify_connector_pro_base` / DEC-014 tombstone pattern rather than silently deleting historical module artifacts.

Rationale: merchant-first labels reduce ambiguity, the change is reversible, core operations remain under the one Shopify root, and the hollow companion module should be handled explicitly so upgrade paths stay safe.

### Decision 2 — Generate Demo Data merchant visibility

Current evidence: `Generate Demo Data` is under admin-only `Operations` at `addons/shopify_connector_pro/views/shopify_menu.xml:99`, opens `shopify_demo_data_wizard_action`, and the wizard has a primary `Generate Demo Data` button at `addons/shopify_connector_pro/wizards/shopify_demo_data_wizard_views.xml:37`.

Options:
1. Leave admin-visible under Operations.
2. Gate behind developer/debug-only and admin visibility.
3. Remove from merchant menu and keep only test/simulator access.

Recommendation: remove it from the merchant menu or gate it behind developer/debug-only plus admin in Phase B. Never leave it as an easy merchant one-click action.

Rationale: demo data can pollute production merchant records, is reversible only with cleanup effort, and does not preserve core operations.

### Decision 3 — Setup Wizard is buried under Configuration

Current evidence: `Setup Wizard` is currently a child of admin-only `Configuration` at `addons/shopify_connector_pro/views/shopify_menu.xml:38`.

Options:
1. Keep under Configuration.
2. Promote/reserve a first-run entry under Shopify root.
3. Duplicate under both first-run and Configuration.

Recommendation: reserve a top-level first-run `Setup` / `Getting Started` home for Goal 4 while retaining a Configuration entry for admins.

Rationale: merchant-first onboarding should be visible before configuration depth, but Phase A must only reserve placement and not design or implement the Goal 4 wizard flow.

### Decision 4 — Sync Status mixes core entities with flag-gated advanced ones

Current evidence: core entities and advanced/flag-gated actions live together under `Sync Status`: Collections at `addons/shopify_connector_pro/views/shopify_menu.xml:136` maps to an action domain `auto_sync_collections`; Additional Data at `:155` includes Abandoned Carts, Payouts, Gift Cards, Customer Tags, and Metafields whose actions carry feature domains.

Options:
1. Keep current flat tree.
2. Split Sync Status into Catalog / Sales / Advanced.
3. Keep Sync Status but add disabled-feature explanatory placeholders.

Recommendation: regroup in Phase B as Catalog, Sales, and Advanced/Optional Data; preserve all existing action domains so disabled advanced features do not show misleading records.

Rationale: preserves core operations, avoids disabled-feature gaps, and is reversible because it reorganizes menus/actions without changing sync logic.

### Decision 5 — Reserve a top-level slot for the Sync Command Center

Current evidence: current recovery surfaces are split between `Logs`, `Sync Log`, `Webhook Log`, Sync Analytics, backend smart buttons, and retry wizards; there is no top-level command-center menu in `shopify_menu.xml`.

Options:
1. Add nothing until Goal 5.
2. Reserve top-level `Command Center` in IA only.
3. Repurpose Logs as Command Center immediately.

Recommendation: reserve a top-level `Command Center` / `Sync Command Center` home after dashboards and before Operations, but implement nothing until Goal 5.

Rationale: aligns with DEC-021 target error UX, is reversible, and avoids Phase A overreach.

## 6. Proposed new menu tree

### Before

Current live before tree is the inventory in section 2 under one Shopify root: Store Overview, Manager Dashboard, Configuration, Operations, Sync Status, Promoters, and Logs. The `shopify_connector_pro_dashboard` XML still defines a separate Shopify Manager root in the repository, but it is not a live tree because the companion module manifest has empty `data` and `assets`.

### After proposal for Phase B review

- Shopify — users
  - Store Overview — users; operational status dashboard, if distinct
  - Manager Analytics — managers/admins; relabeled manager dashboard, if distinct
  - Or one consolidated Dashboard if Phase B confirms redundancy
  - Getting Started / Setup — admins; reserved Goal 4 home only
  - Command Center — users/admins by operation; reserved Goal 5 home only
  - Catalog Sync — users
    - Products, Inventory, Collections, Metafields where enabled
  - Sales Sync — users
    - Customers, Orders, Refunds, Transactions
  - Advanced / Optional Data — users, domains preserved
    - Abandoned Carts, Payouts, Gift Cards, Customer Tags, Promoters, Discount Codes, Discount Usage
  - Operations — admins
    - Sync Now, Import Data, Retry Failed Records, Bulk Export, Import Jobs
    - Generate Demo Data only if developer/debug/admin gated, otherwise no merchant menu
  - Configuration — admins
    - Stores, Payment Gateways, Tax Mappings, Metafield Mappings, Setup Wizard fallback
  - Logs & Audit — users/admins
    - Sync Log, Webhook Log, Sync Analytics

Reserved Goal 4 home: `Getting Started / Setup`; this proposal does not design or implement the wizard flow.

Reserved Goal 5 home: `Command Center`; this proposal does not design or implement the Sync Command Center.

## 7. Preserved domains / groups list

| Object | Groups marker | Domain/action domain | Source |
| --- | --- | --- | --- |
| menu_shopify_root | shopify_connector_pro.group_shopify_user | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:5 |
| menu_shopify_configuration | shopify_connector_pro.group_shopify_admin | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:26 |
| menu_shopify_metafield_mappings | (inherits/default) | [('backend_id.enable_metafields', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:56 |
| menu_shopify_operations | shopify_connector_pro.group_shopify_admin | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:63 |
| menu_shopify_demo_data | shopify_connector_pro.group_shopify_admin | (none) | addons/shopify_connector_pro/views/shopify_menu.xml:99 |
| menu_shopify_collections | (inherits/default) | [('backend_id.auto_sync_collections', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:136 |
| menu_shopify_abandoned_carts | (inherits/default) | [('backend_id.auto_sync_abandoned_carts', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:160 |
| menu_shopify_payouts | (inherits/default) | [('backend_id.enable_payout_import', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:172 |
| menu_shopify_gift_cards | (inherits/default) | [('backend_id.enable_gift_cards', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:178 |
| menu_shopify_customer_tags | (inherits/default) | [('backend_id.enable_customer_tags', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:184 |
| menu_shopify_metafields | (inherits/default) | [('backend_id.enable_metafields', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:190 |
| menu_shopify_discount_codes | (inherits/default) | [('backend_id.enable_promoters', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:208 |
| menu_shopify_discount_usage | (inherits/default) | [('backend_id.enable_promoters', '=', True)] | addons/shopify_connector_pro/views/shopify_menu.xml:214 |
| menu_shopify_manager_root | shopify_connector_pro.group_shopify_user | (none) | addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml:8 |
| shopify_abandoned_cart_action | (action) | [('backend_id.auto_sync_abandoned_carts', '=', True)] | addons/shopify_connector_pro/views/shopify_abandoned_cart_views.xml:144 |
| shopify_collection_binding_action | (action) | [('backend_id.auto_sync_collections', '=', True)] | addons/shopify_connector_pro/views/shopify_collection_binding_views.xml:87 |
| shopify_customer_tag_action | (action) | [('backend_id.enable_customer_tags', '=', True)] | addons/shopify_connector_pro/views/shopify_customer_tag_views.xml:40 |
| shopify_discount_code_action | (action) | [('backend_id.enable_promoters', '=', True)] | addons/shopify_connector_pro/views/shopify_discount_code_views.xml:127 |
| shopify_discount_usage_action | (action) | [('backend_id.enable_promoters', '=', True)] | addons/shopify_connector_pro/views/shopify_discount_usage_views.xml:50 |
| shopify_gift_card_action | (action) | [('backend_id.enable_gift_cards', '=', True)] | addons/shopify_connector_pro/views/shopify_gift_card_views.xml:75 |
| shopify_metafield_action | (action) | [('backend_id.enable_metafields', '=', True)] | addons/shopify_connector_pro/views/shopify_metafield_views.xml:37 |
| shopify_metafield_mapping_action | (action) | [('backend_id.enable_metafields', '=', True)] | addons/shopify_connector_pro/views/shopify_metafield_views.xml:62 |
| shopify_payout_action | (action) | [('backend_id.enable_payout_import', '=', True)] | addons/shopify_connector_pro/views/shopify_payout_views.xml:116 |
| shopify_payout_transaction_action | (action) | [('backend_id.enable_payout_import', '=', True)] | addons/shopify_connector_pro/views/shopify_payout_views.xml:167 |

Regression guard: Phase B must preserve every action domain above and every explicit `groups=` marker unless a reviewed IA change intentionally makes visibility stricter.


### AUDIT.md candidates, report-only

- Promoter stat buttons are non-functional stubs: Orders, Revenue, Discounts, and Commission all call `action_dummy` at `addons/shopify_connector_pro/views/shopify_promoter_views.xml:32-42`, and `action_dummy` is a literal placeholder stub at `addons/shopify_connector_pro/models/shopify_promoter.py:58-60`. Since promoters are first-class v1 (DEC-022), these non-functional placeholder stat buttons are a Goal-3-relevant defect. Report-only in Phase A; do not edit AUDIT.md and do not fix in this task.

## 8. Phase B implementation guardrails

- No production sync behavior changes as part of menu IA implementation.
- Preserve Goal 2B flag domains on action windows.
- Preserve admin-only access for Configuration and Operations unless a reviewed decision makes it stricter.
- Do not expose Generate Demo Data as an easy merchant one-click action.
- Do not design/implement Goal 4 wizard flow; only place the existing or future entry point.
- Do not design/implement Goal 5 command center; only reserve the menu home.
- If a broken menu/action reference is found, record it as an AUDIT.md candidate rather than fixing it in Phase A.

## 9. Open questions

1. Should the hollow dashboard module menu file be considered historical only, given its manifest has empty data, or should Phase B explicitly archive/remove its old menu XML in a separate upgrade-safe task?
2. Should Manager Analytics be user-visible or admin/manager-only? Current groups make it user-visible through the root.
3. Which Odoo/debug group should own demo data visibility if Phase B chooses debug/developer gating?
