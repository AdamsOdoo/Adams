# V2 UI Task Baseline

> Repository-derived inventory only. Runtime reachability, rendered states and
> end-to-end completion remain measured evidence and are never inferred here.

## Provenance

- Source ref: `9e1ca0f2cb6017b5031558e4528818090ad854f0`
- Source SHA: `9e1ca0f2cb6017b5031558e4528818090ad854f0`
- Generator schema: `2`

## Inventory counts

| Surface | Count |
| --- | ---: |
| Menus | 46 |
| Window actions | 45 |
| Client actions | 4 |
| Views | 108 |
| JavaScript components | 21 |
| Registered tours | 42 |
| Static XML template files | 6 |

## Menus and actions

| XML ID | Model | Source |
| --- | --- | --- |
| `shopify_connector_core.action_shopify_connector_dashboard` | `ir.actions.client` | `addons/shopify_connector_core/views/shopify_connector_dashboard_views.xml` |
| `shopify_connector_core.action_shopify_connector_error_center` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_job_views.xml` |
| `shopify_connector_core.action_shopify_connector_health` | `ir.actions.client` | `addons/shopify_connector_core/views/shopify_connector_dashboard_views.xml` |
| `shopify_connector_core.action_shopify_connector_job_attempt` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_runtime_views.xml` |
| `shopify_connector_core.action_shopify_connector_job_cancel_wizard` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_ui_wizard_views.xml` |
| `shopify_connector_core.action_shopify_connector_job_log` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_job_log_views.xml` |
| `shopify_connector_core.action_shopify_connector_mutation_attempt` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_mutation_attempt_views.xml` |
| `shopify_connector_core.action_shopify_connector_mutation_resolution_wizard` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_ui_wizard_views.xml` |
| `shopify_connector_core.action_shopify_connector_run` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_runtime_views.xml` |
| `shopify_connector_core.action_shopify_connector_setup_wizard` | `ir.actions.client` | `addons/shopify_connector_core/views/shopify_connector_setup_views.xml` |
| `shopify_connector_core.action_shopify_connector_store` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_store_views.xml` |
| `shopify_connector_core.action_shopify_connector_store_settings_canonical` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_store_settings_views.xml` |
| `shopify_connector_core.action_shopify_connector_sync_analysis` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_job_analysis_views.xml` |
| `shopify_connector_core.action_shopify_connector_sync_center` | `ir.actions.act_window` | `addons/shopify_connector_core/views/shopify_connector_job_views.xml` |
| `shopify_connector_core.menu_shopify_connector_configuration` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_connector_health` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_dashboard` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_error_center` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_logs` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_mutation_evidence` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_operations` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_reporting` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_root` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_setup_wizard` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_setup_views.xml` |
| `shopify_connector_core.menu_shopify_connector_store_records` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_store_settings` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_store_settings_views.xml` |
| `shopify_connector_core.menu_shopify_connector_stores` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_sync_analysis` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_core.menu_shopify_connector_sync_center` | `ir.ui.menu` | `addons/shopify_connector_core/views/shopify_connector_menus.xml` |
| `shopify_connector_fulfillment.action_shopify_connector_fulfillment_binding` | `ir.actions.act_window` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_binding_views.xml` |
| `shopify_connector_fulfillment.action_shopify_connector_fulfillment_job` | `ir.actions.act_window` | `addons/shopify_connector_fulfillment/views/shopify_connector_job_fulfillment_views.xml` |
| `shopify_connector_fulfillment.action_shopify_connector_fulfillment_mode_switch` | `ir.actions.act_window` | `addons/shopify_connector_fulfillment/wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml` |
| `shopify_connector_fulfillment.action_shopify_connector_fulfillment_review` | `ir.actions.act_window` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_review_views.xml` |
| `shopify_connector_fulfillment.action_shopify_connector_fulfillment_review_release` | `ir.actions.act_window` | `addons/shopify_connector_fulfillment/wizards/shopify_connector_fulfillment_mode_switch_wizard_views.xml` |
| `shopify_connector_fulfillment.action_shopify_connector_fulfillment_settings` | `ir.actions.act_window` | `addons/shopify_connector_fulfillment/views/shopify_connector_store_settings_fulfillment_views.xml` |
| `shopify_connector_fulfillment.menu_shopify_connector_fulfillment` | `ir.ui.menu` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_menus.xml` |
| `shopify_connector_fulfillment.menu_shopify_connector_fulfillment_binding` | `ir.ui.menu` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_menus.xml` |
| `shopify_connector_fulfillment.menu_shopify_connector_fulfillment_jobs` | `ir.ui.menu` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_menus.xml` |
| `shopify_connector_fulfillment.menu_shopify_connector_fulfillment_review` | `ir.ui.menu` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_menus.xml` |
| `shopify_connector_fulfillment.menu_shopify_connector_fulfillment_settings` | `ir.ui.menu` | `addons/shopify_connector_fulfillment/views/shopify_connector_fulfillment_menus.xml` |
| `shopify_connector_inventory.action_shopify_connector_first_push_withdraw_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_inventory_first_push` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_inventory_recheck_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_inventory_workspace` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_location_map_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_location_mapping` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_location_push_toggle_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_location_refresh_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_location_remap_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.action_shopify_connector_location_withdraw_all_wizard` | `ir.actions.act_window` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_wizard_views.xml` |
| `shopify_connector_inventory.menu_shopify_connector_inventory` | `ir.ui.menu` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_menus.xml` |
| `shopify_connector_inventory.menu_shopify_connector_inventory_first_push` | `ir.ui.menu` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_menus.xml` |
| `shopify_connector_inventory.menu_shopify_connector_inventory_workspace` | `ir.ui.menu` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_menus.xml` |
| `shopify_connector_inventory.menu_shopify_connector_location_map` | `ir.ui.menu` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_menus.xml` |
| `shopify_connector_inventory.menu_shopify_connector_location_mapping` | `ir.ui.menu` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_menus.xml` |
| `shopify_connector_inventory.menu_shopify_connector_location_refresh` | `ir.ui.menu` | `addons/shopify_connector_inventory/views/shopify_connector_inventory_menus.xml` |
| `shopify_connector_product.action_shopify_connector_product_match_decision` | `ir.actions.act_window` | `addons/shopify_connector_product/views/shopify_connector_product_match_decision_views.xml` |
| `shopify_connector_product.action_shopify_connector_product_template_binding` | `ir.actions.act_window` | `addons/shopify_connector_product/views/shopify_connector_product_binding_views.xml` |
| `shopify_connector_product.action_shopify_connector_product_variant_binding` | `ir.actions.act_window` | `addons/shopify_connector_product/views/shopify_connector_product_binding_views.xml` |
| `shopify_connector_product.menu_shopify_connector_catalog` | `ir.ui.menu` | `addons/shopify_connector_product/views/shopify_connector_product_menus.xml` |
| `shopify_connector_product.menu_shopify_connector_product_binding` | `ir.ui.menu` | `addons/shopify_connector_product/views/shopify_connector_product_menus.xml` |
| `shopify_connector_product.menu_shopify_connector_product_match_decision` | `ir.ui.menu` | `addons/shopify_connector_product/views/shopify_connector_product_match_decision_views.xml` |
| `shopify_connector_product.menu_shopify_connector_product_variant_binding` | `ir.ui.menu` | `addons/shopify_connector_product/views/shopify_connector_product_menus.xml` |
| `shopify_connector_product_export.action_shopify_connector_export_backfill` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_diagnostics_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_export_diagnostics` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_diagnostics_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_export_diff` | `ir.actions.client` | `addons/shopify_connector_product_export/views/shopify_connector_export_diff_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_product_export_confirm_wizard` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_wizard_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_product_export_preview` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_product_export_request_wizard` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_wizard_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_product_media_binding` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_views.xml` |
| `shopify_connector_product_export.action_shopify_connector_store_settings_export` | `ir.actions.act_window` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_views.xml` |
| `shopify_connector_product_export.menu_shopify_connector_product_export` | `ir.ui.menu` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_menus.xml` |
| `shopify_connector_product_export.menu_shopify_connector_product_export_backfill` | `ir.ui.menu` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_menus.xml` |
| `shopify_connector_product_export.menu_shopify_connector_product_export_diagnostics` | `ir.ui.menu` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_menus.xml` |
| `shopify_connector_product_export.menu_shopify_connector_product_export_media` | `ir.ui.menu` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_menus.xml` |
| `shopify_connector_product_export.menu_shopify_connector_product_export_preview` | `ir.ui.menu` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_menus.xml` |
| `shopify_connector_product_export.menu_shopify_connector_product_export_settings` | `ir.ui.menu` | `addons/shopify_connector_product_export/views/shopify_connector_product_export_menus.xml` |
| `shopify_connector_sale.action_shopify_connector_cod_reconciliation` | `ir.actions.act_window` | `addons/shopify_connector_sale/views/shopify_connector_order_binding_views.xml` |
| `shopify_connector_sale.action_shopify_connector_customer_binding` | `ir.actions.act_window` | `addons/shopify_connector_sale/views/shopify_connector_customer_binding_views.xml` |
| `shopify_connector_sale.action_shopify_connector_manual_gateway_approval_wizard` | `ir.actions.act_window` | `addons/shopify_connector_sale/views/shopify_connector_sale_wizard_views.xml` |
| `shopify_connector_sale.action_shopify_connector_order_workspace` | `ir.actions.act_window` | `addons/shopify_connector_sale/views/shopify_connector_order_binding_views.xml` |
| `shopify_connector_sale.action_shopify_connector_orders_awaiting_configuration` | `ir.actions.act_window` | `addons/shopify_connector_sale/views/shopify_connector_tax_decision_views.xml` |
| `shopify_connector_sale.action_shopify_connector_tax_mapping` | `ir.actions.act_window` | `addons/shopify_connector_sale/views/shopify_connector_tax_decision_views.xml` |
| `shopify_connector_sale.menu_shopify_connector_cod_reconciliation` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_sale_menus.xml` |
| `shopify_connector_sale.menu_shopify_connector_customer_binding` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_sale_menus.xml` |
| `shopify_connector_sale.menu_shopify_connector_order_workspace` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_sale_menus.xml` |
| `shopify_connector_sale.menu_shopify_connector_orders` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_sale_menus.xml` |
| `shopify_connector_sale.menu_shopify_connector_orders_awaiting_configuration` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_tax_decision_views.xml` |
| `shopify_connector_sale.menu_shopify_connector_sales_analysis` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_sale_menus.xml` |
| `shopify_connector_sale.menu_shopify_connector_sales_dashboard` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_sale_menus.xml` |
| `shopify_connector_sale.menu_shopify_connector_tax_mapping` | `ir.ui.menu` | `addons/shopify_connector_sale/views/shopify_connector_tax_decision_views.xml` |
| `shopify_connector_webhook.action_shopify_connector_webhook_delivery` | `ir.actions.act_window` | `addons/shopify_connector_webhook/views/shopify_connector_webhook_views.xml` |
| `shopify_connector_webhook.action_shopify_connector_webhook_subscription` | `ir.actions.act_window` | `addons/shopify_connector_webhook/views/shopify_connector_webhook_views.xml` |
| `shopify_connector_webhook.menu_shopify_connector_webhook_deliveries` | `ir.ui.menu` | `addons/shopify_connector_webhook/views/shopify_connector_webhook_views.xml` |
| `shopify_connector_webhook.menu_shopify_connector_webhook_subscriptions` | `ir.ui.menu` | `addons/shopify_connector_webhook/views/shopify_connector_webhook_views.xml` |

## JavaScript components

| Component | Source |
| --- | --- |
| `AttentionWorkspace` | `addons/shopify_connector_core/static/src/v2/connector_v2_attention.js` |
| `HealthBand` | `addons/shopify_connector_core/static/src/v2/connector_v2_overview.js` |
| `Overview` | `addons/shopify_connector_core/static/src/v2/connector_v2_overview.js` |
| `P16CredentialPanel` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16DiagnosticsPanel` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16LifecyclePanel` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16PhaseRail` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16ReadinessPanel` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16SettingsGroups` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16SetupStepControls` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_setup_controls.js` |
| `P16StatePanel` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `P16StoreList` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_components.js` |
| `RunTimeline` | `addons/shopify_connector_core/static/src/v2/connector_v2_run.js` |
| `ShopifyConnectorDashboard` | `addons/shopify_connector_core/static/src/js/shopify_connector_dashboard.js` |
| `ShopifyConnectorExportDiff` | `addons/shopify_connector_product_export/static/src/js/shopify_connector_export_diff.js` |
| `ShopifyConnectorP16Admin` | `addons/shopify_connector_core/static/src/p16/shopify_connector_p16_admin.js` |
| `ShopifyConnectorSetupWizard` | `addons/shopify_connector_core/static/src/js/shopify_connector_setup_wizard.js` |
| `ShopifyConnectorV2Action` | `addons/shopify_connector_core/static/src/v2/connector_v2_action_controller.js` |
| `StateMessage` | `addons/shopify_connector_core/static/src/v2/connector_v2_status.js` |
| `StatusPill` | `addons/shopify_connector_core/static/src/v2/connector_v2_status.js` |
| `StoreSwitcher` | `addons/shopify_connector_core/static/src/v2/connector_v2_overview.js` |

## Registered browser tours

| Tour | Source |
| --- | --- |
| `shopify_connector_b2_order_controls_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_product_controls_denied_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_product_controls_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_product_match_decision_denied_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_product_match_decision_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_resolved_binding_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_store360_drilldown_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_store_settings_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_b2_tax_decision_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_b2_tour.js` |
| `shopify_connector_s1_dashboard_entry_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_keyboard_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_location_refresh_dispatch_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_location_refresh_failure_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_location_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_new_store_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_readiness_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_resume_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_s1_setup_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_s1_setup_tour.js` |
| `shopify_connector_u0_admin_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u0_tour.js` |
| `shopify_connector_u0_nav_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u0_tour.js` |
| `shopify_connector_u0_operator_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u0_tour.js` |
| `shopify_connector_u0_reviewer_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u0_tour.js` |
| `shopify_connector_u2_first_push_confirm_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_first_push_denied_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_first_push_pending_has_no_control_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_first_push_withdraw_stale_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_first_push_withdraw_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_location_withdraw_all_denied_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_location_withdraw_all_stale_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_location_withdraw_all_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_nav_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_tour.js` |
| `shopify_connector_u2_order_approval_denied_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_order_approval_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_push_toggle_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_quarantined_is_not_listed_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_recheck_blank_reason_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u2_recheck_tour` | `addons/shopify_connector_core/static/src/js/tours/shopify_connector_u2_action_tour.js` |
| `shopify_connector_u3_checksum_ack_tour` | `addons/shopify_connector_product_export/static/src/js/tours/shopify_connector_u3_export_tour.js` |
| `shopify_connector_u3_export_keyboard_tour` | `addons/shopify_connector_product_export/static/src/js/tours/shopify_connector_u3_export_tour.js` |
| `shopify_connector_u3_export_nav_tour` | `addons/shopify_connector_product_export/static/src/js/tours/shopify_connector_u3_export_tour.js` |
| `shopify_connector_u3_export_review_tour` | `addons/shopify_connector_product_export/static/src/js/tours/shopify_connector_u3_export_tour.js` |
| `shopify_connector_u3_media_resume_tour` | `addons/shopify_connector_product_export/static/src/js/tours/shopify_connector_u3_export_tour.js` |

## P00 runtime tasks still required

- Prove every advertised setup and operation entry point is reachable for its role.
- Record loading, empty, blocked, failure, recovery and terminal states in a browser.
- Measure event-to-visible-state latency and active progress feedback.
- Execute U1–U14 on their routed wave; this inventory is not journey evidence.
