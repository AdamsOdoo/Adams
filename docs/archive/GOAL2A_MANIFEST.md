# Goal 2 Phase A Manifest — Feature Flag Research/Design

Status: as-executed research/design only. No Phase B implementation performed.

## Files read

- `AGENTS.md` — operating rules and standing approvals.
- `STATUS.md` — current Goal 1 handoff and green Odoo.sh loop state.
- `docs/product/FEATURE_FLAGS.md` — Goal 0 scaffold replaced by Phase A draft.
- `docs/product/BEHAVIOR_CONTRACT.md` — DEC-025/026/027 references and v1 conservative defaults.
- `docs/architecture/DECISIONS.md` — DEC-025/026/027 and new proposed Phase A ADR location.
- `addons/shopify_connector_pro/models/shopify_backend.py` — existing backend-scoped toggles, cron entry points, webhook registration.
- `addons/shopify_connector_pro/models/account_move.py` — reverse payment/refund toggle gates.
- `addons/shopify_connector_pro/models/shopify_product_binding.py` — product direction gate.
- `addons/shopify_connector_pro/models/res_partner.py` — customer reverse export direction gate.
- `addons/shopify_connector_pro/models/stock_move.py` — inventory auto-sync gate.
- `addons/shopify_connector_pro/sync/order_sync.py` — invoice/currency behavior gates.
- `addons/shopify_connector_pro/sync/payment_status_sync.py` — payment-transition gate.
- `addons/shopify_connector_pro/sync/fulfillment_sync.py` — external fulfillment mode gate.
- `addons/shopify_connector_pro/sync/gift_card_sync.py` — reference-only gift-card import behavior.
- `addons/shopify_connector_pro/sync/payout_sync.py` — visibility-only payout import behavior.
- `addons/shopify_connector_pro/controllers/webhook.py` — webhook receive, rate limit, dedup, enqueue.
- `addons/shopify_connector_pro/models/shopify_webhook_log.py` — webhook dispatch topics.
- `addons/shopify_connector_pro/data/shopify_cron.xml` — scheduled surfaces.
- `addons/shopify_connector_pro/views/shopify_menu.xml` and related view XML files — menu/action surfaces.
- `addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml` and `manager_dashboard_action.xml` — dashboard module surfaces.

## Local Odoo source inspection

Local Odoo framework source was not present in checked locations (`/workspace/odoo`, `/workspace/odoo19`, `/home/odoo`, `/opt/odoo`, `/usr/lib/python3/dist-packages/odoo`, `/workspace/Adams/odoo`), and `importlib.util.find_spec('odoo')` returned no installed Python module. Phase A therefore used project-local Odoo patterns as evidence rather than uncited framework memory.

## Existing connector toggles / behavior gates

| Field / gate | Evidence | What it gates today | Scope today | Default | Money path? |
|---|---|---|---|---|---|
| `auto_sync_products` | `addons/shopify_connector_pro/models/shopify_backend.py:80`, `addons/shopify_connector_pro/models/shopify_backend.py:1084-1096` | Scheduled product sync searches connected backends with this boolean true. | Backend/store | `True` | No direct posting path. |
| `product_sync_direction` | `addons/shopify_connector_pro/models/shopify_backend.py:81-85`, `addons/shopify_connector_pro/models/shopify_product_binding.py:73` | Product import/export direction selection. | Backend/store | `both` | Indirect catalog/price path. |
| `auto_export_on_change` | `addons/shopify_connector_pro/models/shopify_backend.py:89-91` | Product auto-export preference; Phase A did not inspect every write hook. | Backend/store | `True` | Indirect catalog/price path. |
| `auto_sync_customers` | `addons/shopify_connector_pro/models/shopify_backend.py:93`, `addons/shopify_connector_pro/models/shopify_backend.py:1123-1142` | Scheduled customer sync searches connected backends with this boolean true. | Backend/store | `True` | No. |
| `customer_sync_direction` | `addons/shopify_connector_pro/models/shopify_backend.py:94-98`, `addons/shopify_connector_pro/models/shopify_backend.py:1128-1138` | Customer cron import/export direction. | Backend/store | `import` | No. |
| `auto_sync_orders` | `addons/shopify_connector_pro/models/shopify_backend.py:108`, `addons/shopify_connector_pro/models/shopify_backend.py:1097-1108`, `addons/shopify_connector_pro/models/shopify_backend.py:1197-1221` | Scheduled order import and refund import backend selection. | Backend/store | `True` | Yes: orders/refunds/invoices. |
| `auto_create_invoice` | `addons/shopify_connector_pro/models/shopify_backend.py:112-114`, `addons/shopify_connector_pro/sync/order_sync.py:345-348` | Auto-creates invoice during order import when enabled. | Backend/store | `True` | Yes: invoices. |
| `import_currency_mode` | `addons/shopify_connector_pro/models/shopify_backend.py:115-124`, `addons/shopify_connector_pro/sync/order_sync.py:212`, `addons/shopify_connector_pro/sync/refund_sync.py:65-70` | Selects company/store/presentment currency handling for imported orders/refunds. | Backend/store | `company` | Yes: currency/totals. |
| `auto_sync_inventory` | `addons/shopify_connector_pro/models/shopify_backend.py:126-133`, `addons/shopify_connector_pro/models/shopify_backend.py:1110-1121`, `addons/shopify_connector_pro/models/stock_move.py:28` | Scheduled and stock-move-triggered inventory export. | Backend/store | `True` | No direct posting path. |
| `auto_sync_collections` | `addons/shopify_connector_pro/models/shopify_backend.py:135`, `addons/shopify_connector_pro/models/shopify_backend.py:1158-1171` | Scheduled collection import. | Backend/store | `True` | No. |
| `auto_sync_abandoned_carts` | `addons/shopify_connector_pro/models/shopify_backend.py:138-145`, `addons/shopify_connector_pro/models/shopify_backend.py:1223-1228` | Scheduled abandoned-cart import. | Backend/store | `False` | Potential quotation/order precursor, not posted accounting. |
| `auto_create_abandoned_quotation` | `addons/shopify_connector_pro/models/shopify_backend.py:142-145` | Quotation creation preference for abandoned carts. | Backend/store | `False` | Quotation only; no posted accounting. |
| `external_fulfillment_handling` | `addons/shopify_connector_pro/models/shopify_backend.py:148-155`, `addons/shopify_connector_pro/sync/fulfillment_sync.py:264-288` | Shopify-created fulfillment handling: ignore, activity, or auto-validate delivery. | Backend/store | `activity` | Inventory/delivery impact, not accounting posting. |
| `auto_handle_payment_transitions` | `addons/shopify_connector_pro/models/shopify_backend.py:156-160`, `addons/shopify_connector_pro/sync/payment_status_sync.py:63` | Automatic invoice posting/cancel behavior from Shopify payment transitions. | Backend/store | `True` | Yes: invoices. |
| `reverse_sync_payment` | `addons/shopify_connector_pro/models/shopify_backend.py:161-165`, `addons/shopify_connector_pro/models/account_move.py:48-65` | Marks Shopify order paid when Odoo invoice posts, if order also allows reverse sync. | Backend/store + order gate | `False` | Yes: payment state. |
| `reverse_sync_refund` | `addons/shopify_connector_pro/models/shopify_backend.py:166-170`, `addons/shopify_connector_pro/models/account_move.py:108-135` | Creates Shopify refund when Odoo credit note posts, if order also allows reverse sync. | Backend/store + order gate | `False` | Yes: real refund. |
| `reconciliation_order_days` | `addons/shopify_connector_pro/models/shopify_backend.py:171-174` | Reconciliation lookback setting. | Backend/store | `30` | Yes: reconciliation visibility. |
| `batch_size` | `addons/shopify_connector_pro/models/shopify_backend.py:182-207` | Batch/pagination sizing, constrained to 1..250. | Backend/store | `50` | No. |
| `shopify_reverse_sync` | `addons/shopify_connector_pro/models/sale_order.py:29`, `addons/shopify_connector_pro/models/account_move.py:56-65`, `addons/shopify_connector_pro/models/account_move.py:123-132` | Per-order opt-in gate for reverse payment/refund sync. | Order | model default inspected as field default if present; no backend default. | Yes. |

## Odoo/project toggle pattern table

| Pattern | Evidence | Write/read mechanics | Upgrade behavior | Access-rights implication |
|---|---|---|---|---|
| `res.config.settings` + `ir.config_parameter` | Odoo source absent; project reads `web.base.url` from `ir.config_parameter` at `addons/shopify_connector_pro/models/shopify_backend.py:859-860`, and tests set `database.uuid` with `set_param` at `addons/shopify_connector_pro/tests/test_credential_encryption.py:72-79`. | Settings transient models typically write persistent parameters; project examples read parameters via `sudo().get_param()` and tests write via `sudo().set_param()`. | Parameter survives module upgrades as DB data unless explicitly changed. | Usually requires system/settings access; project examples use `sudo`, so Phase B must avoid exposing user-level toggles through unrestricted reads/writes. |
| Company-dependent setting | Odoo source absent; project uses explicit `company_id` on backend and related records rather than `company_dependent=True`, e.g. backend company field at `addons/shopify_connector_pro/models/shopify_backend.py:59-68`. | Write/read is normal model data scoped by the record's company. | Existing backend rows keep their value through upgrades. | Access controlled by record rules/groups and company access; no implicit global parameter leakage. |
| Groups-based visibility | `addons/shopify_connector_pro/views/shopify_menu.xml:5-8`, `addons/shopify_connector_pro/views/shopify_menu.xml:26-30`, and credential fields at `addons/shopify_connector_pro/models/shopify_backend.py:40-56`. | XML `groups` hides menu entries; field `groups` restricts field access/readability. | XML definitions update on module upgrade; group assignments persist as security data. | Good for role access, not sufficient for feature OFF semantics because backend cron/webhook code still needs explicit gates. |
| Plain model boolean / selection field | Backend booleans/selections at `addons/shopify_connector_pro/models/shopify_backend.py:80-170`; cron methods search on booleans at `addons/shopify_connector_pro/models/shopify_backend.py:1084-1228`. | Values live on `shopify.backend` and are read directly by cron/sync/accounting methods. | New fields need defaults for fresh rows and explicit migration/post-init strategy for existing rows when the default differs. | Fits existing admin/backend security model and per-store scope; Phase B must ensure only admin-level users can modify flags. |

## Surface enumeration summary

### Crons

| XML id | Evidence | Method called | Feature | Classification |
|---|---|---|---|---|
| `ir_cron_shopify_sync_products` | `addons/shopify_connector_pro/data/shopify_cron.xml:4-11` | `model._cron_sync_products()` | Products | CORE |
| `ir_cron_shopify_sync_customers` | `addons/shopify_connector_pro/data/shopify_cron.xml:13-20` | `model._cron_sync_customers()` | Customers | CORE |
| `ir_cron_shopify_import_orders` | `addons/shopify_connector_pro/data/shopify_cron.xml:22-29` | `model._cron_import_orders()` | Orders | CORE |
| `ir_cron_shopify_sync_inventory` | `addons/shopify_connector_pro/data/shopify_cron.xml:31-38` | `model._cron_sync_inventory()` | Inventory | CORE |
| `ir_cron_shopify_process_webhooks` | `addons/shopify_connector_pro/data/shopify_cron.xml:40-47` | `model._cron_process_pending()` | Webhook infrastructure | CORE |
| `ir_cron_shopify_sync_discounts` | `addons/shopify_connector_pro/data/shopify_cron.xml:49-56` | `model._cron_sync_discounts()` | Promoters/discount codes | ADVANCED, default ON |
| `ir_cron_shopify_sync_collections` | `addons/shopify_connector_pro/data/shopify_cron.xml:58-65` | `model._cron_sync_collections()` | Collections | ADVANCED |
| `ir_cron_shopify_import_refunds` | `addons/shopify_connector_pro/data/shopify_cron.xml:67-74` | `model._cron_import_refunds()` | Shopify refund import | CORE |
| `ir_cron_shopify_import_payouts` | `addons/shopify_connector_pro/data/shopify_cron.xml:76-83` | `model._cron_import_payouts()` | Payout visibility import | ADVANCED |
| `ir_cron_shopify_process_import_jobs` | `addons/shopify_connector_pro/data/shopify_cron.xml:85-92` | `model._cron_process_import_jobs()` | Import job infrastructure | CORE |
| `ir_cron_shopify_reconcile` | `addons/shopify_connector_pro/data/shopify_cron.xml:94-101` | `model._cron_reconcile()` | Reconciliation | CORE |
| `ir_cron_shopify_import_abandoned_carts` | `addons/shopify_connector_pro/data/shopify_cron.xml:103-110` | `model._cron_import_abandoned_carts()` | Abandoned carts | ADVANCED, default ON once implemented per DEC-019 |
| `ir_cron_shopify_error_digest` | `addons/shopify_connector_pro/data/shopify_cron.xml:112-119` | `model._cron_send_error_digest()` | Error visibility | CORE |

### Menus/actions

| Surface | Evidence | Feature | Classification |
|---|---|---|---|
| Root/dashboard/manager/config/operations/sync/log menus | `addons/shopify_connector_pro/views/shopify_menu.xml:5-110`, `addons/shopify_connector_pro/views/shopify_menu.xml:221-242` | Setup, operations, observability | CORE |
| Product/customer/order/inventory/refund/location menus | `addons/shopify_connector_pro/views/shopify_menu.xml:112-152` | Core synced entities | CORE |
| Collections menu/action | `addons/shopify_connector_pro/views/shopify_menu.xml:136-140`, `addons/shopify_connector_pro/views/shopify_collection_binding_views.xml:87` | Collections | ADVANCED |
| Abandoned carts menu/action | `addons/shopify_connector_pro/views/shopify_menu.xml:160-164`, `addons/shopify_connector_pro/views/shopify_abandoned_cart_views.xml:144` | Abandoned carts | ADVANCED |
| Transactions menu/action | `addons/shopify_connector_pro/views/shopify_menu.xml:166-170`, `addons/shopify_connector_pro/views/shopify_payment_gateway_views.xml:87` | Order transactions | CORE for payment visibility |
| Payouts menu/action | `addons/shopify_connector_pro/views/shopify_menu.xml:172-176`, `addons/shopify_connector_pro/views/shopify_payout_views.xml:116` | Payout visibility | ADVANCED |
| Gift cards menu/action | `addons/shopify_connector_pro/views/shopify_menu.xml:178-182`, `addons/shopify_connector_pro/views/shopify_gift_card_views.xml:75` | Gift-card reference data | ADVANCED |
| Customer tags menu/action | `addons/shopify_connector_pro/views/shopify_menu.xml:184-188`, `addons/shopify_connector_pro/views/shopify_customer_tag_views.xml:40` | Customer tags | ADVANCED |
| Metafields menus/actions | `addons/shopify_connector_pro/views/shopify_menu.xml:56-60`, `addons/shopify_connector_pro/views/shopify_menu.xml:190-194`, `addons/shopify_connector_pro/views/shopify_metafield_views.xml:37`, `addons/shopify_connector_pro/views/shopify_metafield_views.xml:61` | Metafields and mappings | ADVANCED |
| Promoters/discount menus/actions | `addons/shopify_connector_pro/views/shopify_menu.xml:197-218`, `addons/shopify_connector_pro/views/shopify_promoter_views.xml:112`, `addons/shopify_connector_pro/views/shopify_discount_code_views.xml:127`, `addons/shopify_connector_pro/views/shopify_discount_usage_views.xml:50` | Promoters/discounts | ADVANCED, default ON and first-class v1 |
| Isolated dashboard module menu/action | `addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml:8-18`, `addons/shopify_connector_pro_dashboard/views/manager_dashboard_action.xml:3` | Manager dashboard | CORE observability unless later separated by product decision |

### Webhook topics

| Topic | Registration evidence | Dispatch evidence | Feature | Classification |
|---|---|---|---|---|
| `PRODUCTS_CREATE` / `products/create` | `addons/shopify_connector_pro/models/shopify_backend.py:851-852` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:179-181` | Products | CORE |
| `PRODUCTS_UPDATE` / `products/update` | `addons/shopify_connector_pro/models/shopify_backend.py:851-852` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:179-181` | Products | CORE |
| `PRODUCTS_DELETE` / `products/delete` | `addons/shopify_connector_pro/models/shopify_backend.py:851-852` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:182` | Product deletion/archive | CORE |
| `ORDERS_CREATE` / `orders/create` | `addons/shopify_connector_pro/models/shopify_backend.py:853` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:183` | Orders | CORE |
| `ORDERS_UPDATED` / `orders/updated` | `addons/shopify_connector_pro/models/shopify_backend.py:853` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:184` | Orders/status | CORE |
| `ORDERS_CANCELLED` / `orders/cancelled` | `addons/shopify_connector_pro/models/shopify_backend.py:853` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:185` | Order cancellation | CORE |
| `CUSTOMERS_CREATE` / `customers/create` | `addons/shopify_connector_pro/models/shopify_backend.py:854` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:186` | Customers | CORE |
| `CUSTOMERS_UPDATE` / `customers/update` | `addons/shopify_connector_pro/models/shopify_backend.py:854` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:187` | Customers | CORE |
| `INVENTORY_LEVELS_UPDATE` / `inventory_levels/update` | `addons/shopify_connector_pro/models/shopify_backend.py:855` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:188` | Inventory | CORE |
| `FULFILLMENTS_CREATE` / `fulfillments/create` | `addons/shopify_connector_pro/models/shopify_backend.py:856` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:189` | Fulfillment | CORE |
| `refunds/create` | not registered in current list | `addons/shopify_connector_pro/models/shopify_webhook_log.py:190` | Refund import | CORE dispatch present; registration gap remains outside Phase A scope |
| `APP_UNINSTALLED` / `app/uninstalled` | `addons/shopify_connector_pro/models/shopify_backend.py:857` | `addons/shopify_connector_pro/models/shopify_webhook_log.py:191` | App uninstall hygiene | CORE |
| `customers/data_request` | not registered in current list | `addons/shopify_connector_pro/models/shopify_webhook_log.py:192-193` | GDPR compliance | CORE |
| `customers/redact` | not registered in current list | `addons/shopify_connector_pro/models/shopify_webhook_log.py:192-194` | GDPR compliance | CORE |
| `shop/redact` | not registered in current list | `addons/shopify_connector_pro/models/shopify_webhook_log.py:192-195` | GDPR compliance | CORE |

## Escalation dependency result

No new Ahmed escalation is required for Phase A. DEC-025, DEC-026, and DEC-027 close the expected high-stakes defaults for gift-card accounting, payout accounting, and reverse refund push. Remaining Phase A mechanism choices are reversible design choices under standing approval and are recorded as Proposed only for Phase B review.
