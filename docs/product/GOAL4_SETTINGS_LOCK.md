PHASE A PROPOSAL — implementation pending Phase B GO

# Goal 4 Phase A — Settings-safety research + design

## 1. Executive summary

Goal 4 should make setup wizard-first and make live settings safer without changing sync, money, or credential behavior during Phase A. Today the onboarding wizard tests credentials using a temporary backend object, then creates a real `shopify.backend` with `state='connected'` before the optional initial import step; there is no separate validated/go-live/locked concept. Evidence: the wizard step enum is `connection`, `settings`, `webhooks`, `import`, and `done` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:13-20`; the real backend is created in `action_next_to_import` with `state='connected'` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:79-90`; the initial import happens later in `action_finish` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:103-168`.

Recommendation for Phase B: use a hybrid safety model. Active backend fields remain the last validated/effective settings; safe cosmetic fields can be written directly; credential/connection fields and staged/money-path fields should be changed through a validation path and only applied to active fields after the relevant test succeeds. This preserves the current sync consumers by keeping existing field reads pointed at effective values, while preventing unvalidated credentials, company, currency, inventory, invoice, refund, and payment settings from silently taking effect.

This document is research/design only. It does not implement locks, fields, migrations, wizards, tests, security changes, or XML changes.

## 2. Current wizard map

### Wizard model and fields

| Item | Current evidence | Design implication |
|---|---|---|
| Model | `shopify.onboarding.wizard` transient model in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:9-11`. | Goal 4 can extend the first-run UX without replacing the backend model. |
| Steps | Selection values `connection`, `settings`, `webhooks`, `import`, `done` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:13-20`; view sections mirror the same steps in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:13-74`. | Current wizard already has an IA skeleton for validation but lacks a durable validated result. |
| Connection fields | `name`, `shop_url`, `access_token`, `webhook_secret` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:22-27`; connection UI fields in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:20-28` and webhook secret UI in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:55-56`. | Credentials should become REQUIRES-RETEST inputs. |
| Odoo settings | `company_id`, `warehouse_id`, `pricelist_id` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:28-33`; UI in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:39-44`. | These are validation-sensitive, with `company_id` also MONEY-PATH. |
| Import options | `import_products`, `import_customers`, `import_orders`, and `order_days` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:35-39`; import UI in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:67-72`. | Initial import should remain optional and not define go-live by itself. |
| Result fields | `backend_id` and `connection_status` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:41-43`. | Phase B needs durable validation metadata on the backend, not only transient status text. |

### Wizard methods and transitions

| Method/button | Current behavior | Evidence |
|---|---|---|
| `action_open_onboarding` | Opens the wizard as a modal `ir.actions.act_window`. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:45-53`; action record in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:109-114`. |
| `action_test_connection` / “Test Connection & Next” | Builds a local `TempBackend`, sets `shop_url`, `access_token`, hard-codes API version `2026-01`, creates a `ShopifyClient`, fetches shop info, sets `connection_status`, and advances to `settings` on success; failure remains visible in `connection_status`. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:55-73`; button in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:78-81`. |
| `action_next_to_webhooks` / “Next” | Sets `step='webhooks'` and reopens the wizard. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:75-77`; button in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:84-86`. |
| `action_next_to_import` / “Create Store & Next” | Creates the real backend, writes credentials/settings, sets `state='connected'`, optionally registers webhooks, initializes field mappings, then moves to import. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:79-101`; button in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:89-92`. |
| `action_finish` / “Import & Finish” | Runs selected product/customer/order imports by calling backend cron methods directly; logs handled import errors into `shopify.sync.log`; then opens the backend with notification. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:103-168`; button in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:95-98`. |
| `action_skip_import` / “Skip Import” | Opens the created backend without running imports. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:170-180`; button in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml:99-101`. |
| `_reopen` | Reopens the same wizard record as a modal. | `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:182-189`. |

### Current validation/go-live finding

There is no durable `validated`, `go_live`, `locked`, `settings_lock`, or `validated_at` backend concept in the current wizard/backend evidence. The closest current state is `state='connected'`, set while creating the backend in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:81-90`, before optional imports in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:103-168`.

## 3. Full settings lock matrix

Scope: persisted or user-editable backend configuration/settings fields. Pure computed counts, display-only dashboard counters, operational timestamps, and transient status fields are excluded unless they affect sync behavior, validation state, locking, credentials, or go-live semantics.

| Field | Type | Definition | UI evidence | Controls | Money-path? | Sync/destructive? | Credential/security? | Proposed class | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| `name` | Char | `addons/shopify_connector_pro/models/shopify_backend.py:21` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:90-93` | Store display name. | N | N | N | SAFE-ANYTIME | Cosmetic label only. |
| `shop_url` | Char | `addons/shopify_connector_pro/models/shopify_backend.py:22-25` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:99-101` | Shopify shop identity and API target. | N | Y | Y | REQUIRES-RETEST | Changing it redirects all API calls and must not take effect until tested. |
| `access_token` | computed/inverse Char | `addons/shopify_connector_pro/models/shopify_backend.py:40-45` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:99-103` | Shopify Admin API authentication. | N | Y | Y | REQUIRES-RETEST | Secret rotation must be possible but only effective after successful connection test. |
| `webhook_secret` | computed/inverse Char | `addons/shopify_connector_pro/models/shopify_backend.py:52-57` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:99-103` | Webhook validation secret. | N | Y | Y | REQUIRES-RETEST | A bad secret can break webhook trust and must be retested/validated. |
| `api_version` | Char | `addons/shopify_connector_pro/models/shopify_backend.py:46-51` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:99-103` | Shopify API compatibility version. | N | Y | N | REQUIRES-RETEST | Unsupported version can break sync/API calls. |
| `company_id` | Many2one | `addons/shopify_connector_pro/models/shopify_backend.py:60-63` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:105-110` | Company used for synced records/accounting. | Y | Y | N | MONEY-PATH | Wrong company can create/locate accounting, orders, refunds, taxes, and payments in the wrong legal entity. |
| `warehouse_id` | Many2one | `addons/shopify_connector_pro/models/shopify_backend.py:64-69` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:105-110` | Warehouse for orders/inventory/location mapping. | N | Y | N | STAGED / VALIDATION-GATED | Affects stock/order fulfillment behavior. |
| `pricelist_id` | Many2one | `addons/shopify_connector_pro/models/shopify_backend.py:70-73` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:105-110` | Price export/import pricing context. | Y | Y | N | MONEY-PATH | Pricing changes can alter commercial amounts and must be validated. |
| `shopify_location_id` | Char | `addons/shopify_connector_pro/models/shopify_backend.py:74-77` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:105-110` | Primary Shopify location for inventory sync. | N | Y | N | STAGED / VALIDATION-GATED | Wrong location can push/pull inventory to the wrong stock location. |
| `auto_sync_products` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:80` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:121-128` | Enables product sync cron. | N | Y | N | STAGED / VALIDATION-GATED | Enables/disables an operational sync surface. |
| `product_sync_direction` | Selection | `addons/shopify_connector_pro/models/shopify_backend.py:81-85` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:121-128` | Product import/export direction. | N | Y | N | STAGED / VALIDATION-GATED | Direction changes can overwrite catalog data in either system. |
| `product_sync_interval` | Integer | `addons/shopify_connector_pro/models/shopify_backend.py:86-88` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:121-128` | Product cron cadence. | N | Y | N | STAGED / VALIDATION-GATED | Scheduling change affects sync load/timing. |
| `auto_export_on_change` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:89-91` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:121-128` | Product push-on-change behavior. | N | Y | N | STAGED / VALIDATION-GATED | Can immediately export changes. |
| `auto_sync_customers` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:93` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:130-137` | Enables customer sync. | N | Y | N | STAGED / VALIDATION-GATED | Enables/disables a data sync surface. |
| `customer_sync_direction` | Selection | `addons/shopify_connector_pro/models/shopify_backend.py:94-98` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:130-137` | Customer import/export direction. | N | Y | N | STAGED / VALIDATION-GATED | Direction can change customer master-data ownership. |
| `customer_sync_interval` | Integer | `addons/shopify_connector_pro/models/shopify_backend.py:99-101` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:130-137` | Customer cron cadence. | N | Y | N | STAGED / VALIDATION-GATED | Scheduling change affects load/timing. |
| `customer_dedup_field` | Selection | `addons/shopify_connector_pro/models/shopify_backend.py:102-106` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:130-137` | Customer matching rule. | N | Y | N | STAGED / VALIDATION-GATED | Wrong dedupe can merge/link customers incorrectly. |
| `auto_sync_orders` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:108` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:141-148` | Enables order import. | Y | Y | N | MONEY-PATH | Controls whether sales documents enter Odoo. |
| `order_sync_interval` | Integer | `addons/shopify_connector_pro/models/shopify_backend.py:109-111` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:141-148` | Order cron cadence. | Y | Y | N | MONEY-PATH | Timing of order/money document creation. |
| `auto_create_invoice` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:112-114` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:141-148` | Invoice creation during order import. | Y | Y | N | MONEY-PATH | Directly controls invoice generation. |
| `import_currency_mode` | Selection | `addons/shopify_connector_pro/models/shopify_backend.py:115-124` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:141-148` | Currency for imported orders. | Y | Y | N | MONEY-PATH + FEATURE-FLAG | Wrong currency mode can create wrong-money documents. Existing Goal 2B gate also covers it. |
| `auto_sync_inventory` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:126` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:150-155` | Enables inventory push. | N | Y | N | STAGED / VALIDATION-GATED | Can change Shopify stock availability. |
| `inventory_sync_interval` | Integer | `addons/shopify_connector_pro/models/shopify_backend.py:127-129` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:150-155` | Inventory cron cadence. | N | Y | N | STAGED / VALIDATION-GATED | Scheduling affects stock updates. |
| `inventory_quantity_field` | Selection | `addons/shopify_connector_pro/models/shopify_backend.py:130-133` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:150-155` | Quantity source for inventory push. | N | Y | N | STAGED / VALIDATION-GATED | Wrong quantity field can over/under sell. |
| `auto_sync_collections` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:135` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:158-160` | Enables collection sync. | N | Y | N | FEATURE-FLAG | Existing Goal 2B admin gate covers writes; sync-affecting so validation-gated after go-live. |
| `enable_promoters` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:138-141` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:173-180` | Enables promoter/discount surfaces. | N | Y | N | FEATURE-FLAG | Admin-gated optional feature; validate if it starts cron/import behavior. |
| `enable_payout_import` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:142-145` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:173-180` | Enables payout import. | Y | Y | N | MONEY-PATH + FEATURE-FLAG | Payout/reconciliation path should be strict staged. |
| `enable_gift_cards` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:146-149` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:173-180` | Enables gift-card sync/features. | Y | Y | N | MONEY-PATH + FEATURE-FLAG | Gift cards are money-like liabilities; strict staged. |
| `enable_metafields` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:150-153` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:173-180` | Enables metafield sync. | N | Y | N | FEATURE-FLAG | Optional advanced visibility/sync; admin-gated and likely validation-gated only if auto sync is enabled. |
| `enable_customer_tags` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:154-157` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:173-180` | Enables customer tag surfaces/sync. | N | Y | N | FEATURE-FLAG | Optional advanced visibility; admin-gated anytime if no destructive sync, otherwise staged. |
| `auto_sync_abandoned_carts` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:160-163` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:168-171` | Enables abandoned-cart import. | N | Y | N | FEATURE-FLAG | Sync-affecting and should be validation-gated. |
| `auto_create_abandoned_quotation` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:164-167` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:168-171` | Converts abandoned carts to quotations. | Y | Y | N | MONEY-PATH + FEATURE-FLAG | Creates sales documents and should be strict staged. |
| `external_fulfillment_handling` | Selection | `addons/shopify_connector_pro/models/shopify_backend.py:170-177` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:185-188` | Shopify→Odoo fulfillment handling behavior. | N | Y | N | FEATURE-FLAG / STAGED | Existing Goal 2B gate covers writes; fulfillment behavior is operationally risky. |
| `auto_handle_payment_transitions` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:178-182` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:190-191` | Automatic payment transitions. | Y | Y | N | MONEY-PATH | Affects payment state transitions. |
| `reverse_sync_payment` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:183-187` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:195-197` | Odoo→Shopify payment reverse sync. | Y | Y | N | MONEY-PATH + FEATURE-FLAG | Existing Goal 2B gate covers writes; money-path behavior must be strict staged. |
| `reverse_sync_refund` | Boolean | `addons/shopify_connector_pro/models/shopify_backend.py:188-192` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:195-197` | Odoo→Shopify refund reverse sync. | Y | Y | N | MONEY-PATH + FEATURE-FLAG | Existing Goal 2B gate covers writes; refund path must be strict staged. |
| `reconciliation_order_days` | Integer | `addons/shopify_connector_pro/models/shopify_backend.py:209-212` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:199-200` | Refund/reconciliation lookback. | N | Y | N | STAGED / VALIDATION-GATED | Affects reconciliation/lookback scan scope, not direct money creation. |
| `shipping_product_id` | Many2one | `addons/shopify_connector_pro/models/shopify_backend.py:214-218` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:162-164` | Shipping line product for imported orders/refunds. | Y | Y | N | MONEY-PATH | Wrong product can misclassify shipping revenue/refunds. |
| `batch_size` | Integer | `addons/shopify_connector_pro/models/shopify_backend.py:220` | `addons/shopify_connector_pro/views/shopify_backend_views.xml:162-164` | Page/batch size for sync jobs. | N | Y | N | STAGED / VALIDATION-GATED | Performance/safety setting with validation constraints. |

### Feature-flag gate cross-check

The existing feature-flag set includes `enable_promoters`, `enable_payout_import`, `enable_gift_cards`, `enable_metafields`, `enable_customer_tags`, `auto_sync_collections`, `auto_sync_abandoned_carts`, `auto_create_abandoned_quotation`, `reverse_sync_payment`, `reverse_sync_refund`, `external_fulfillment_handling`, and `import_currency_mode` in `addons/shopify_connector_pro/models/shopify_backend.py:194-207`. The current `write()` override requires `shopify_connector_pro.group_shopify_admin` for non-superuser writes touching that set in `addons/shopify_connector_pro/models/shopify_backend.py:1049-1056`. Goal 4 must preserve this admin gate and add validation semantics on top of it, not replace it.

### Cross-check notes

Fields present in code but broader than the initial sensitive-field list include `product_sync_direction`, `auto_export_on_change`, `customer_sync_direction`, `customer_dedup_field`, `auto_sync_products`, `auto_sync_customers`, `auto_sync_orders`, `auto_sync_inventory`, `product_sync_interval`, `customer_sync_interval`, `order_sync_interval`, and `inventory_sync_interval`. These are not all money-path, but they affect destructive or high-volume sync behavior and should be staged/validation-gated once the backend is live.

Expected sensitive fields not found as direct backend settings in the current code include explicit tax-mapping setting fields on `shopify.backend`; tax behavior appears to be consumed in sync/accounting paths rather than as a simple backend field in this file.

Excluded non-config fields considered: computed counts such as `product_bind_count`, `customer_bind_count`, `order_bind_count`, `inventory_bind_count`; display shop info such as `shop_name` and `shop_plan`; health/activity counters; operational timestamps such as last sync fields; and `credential_issue` display state. `credential_issue` is covered in credential constraints because it affects safe rotation/error UX, but it is not itself a merchant-editable setting.

## 4. Credential constraints

The backend stores actual secrets in encrypted DB columns `_encrypted_access_token` and `_encrypted_webhook_secret`, while the public fields `access_token` and `webhook_secret` are non-stored computed/inverse fields in `addons/shopify_connector_pro/models/shopify_backend.py:27-45` and `addons/shopify_connector_pro/models/shopify_backend.py:52-57`. The compute methods decrypt stored values and set `credential_issue` if decryption fails; decryption failures are logged without exposing plaintext in `addons/shopify_connector_pro/models/shopify_backend.py:334-356` and `addons/shopify_connector_pro/models/shopify_backend.py:369-382`. The inverse methods validate/encrypt new values in `addons/shopify_connector_pro/models/shopify_backend.py:358-367` and `addons/shopify_connector_pro/models/shopify_backend.py:384-387`.

The `create()` override intercepts plaintext `access_token` and `webhook_secret`, removes them from incoming values, validates/encrypts them, and stores them in `_encrypted_access_token` and `_encrypted_webhook_secret` in `addons/shopify_connector_pro/models/shopify_backend.py:389-410`. `_make_api_client` returns a `ShopifyClient(self)` and, when `credential_issue` is active, schedules a credential recovery activity before re-raising in `addons/shopify_connector_pro/models/shopify_backend.py:433-461`.

The wizard's connection test does not create a backend. It creates an in-memory `TempBackend`, sets `shop_url`, `access_token`, and `api_version='2026-01'`, then fetches shop info through `ShopifyClient` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:55-73`. Goal 4 should reuse this temp-backend pattern for credential rotation/re-test, then only activate new encrypted credentials after a successful test. Plaintext secrets must not be written into chatter, `shopify.sync.log`, decision docs, audit reports, or validation failure messages.

## 5. Existing gates to compose with

| Gate | Evidence | Goal 4 composition rule |
|---|---|---|
| Shopify User group | `group_shopify_user` is read-only/monitoring-oriented in `addons/shopify_connector_pro/security/shopify_security.xml:17-28`. | Users should not unlock settings or activate validation-sensitive changes. |
| Shopify Admin group | `group_shopify_admin` implies user and has full configuration/sync access in `addons/shopify_connector_pro/security/shopify_security.xml:30-40`. | Admin should be the primary unlock/validation authority, with reason-required audit. |
| Credential fields group | `access_token` and `webhook_secret` are restricted to `shopify_connector_pro.group_shopify_admin` in `addons/shopify_connector_pro/models/shopify_backend.py:40-57`. | Credential lock must not broaden visibility. |
| Backend buttons | Test/Re-test, Register Webhooks, and Import Locations are visible from the backend header in `addons/shopify_connector_pro/views/shopify_backend_views.xml:30-45`. | Phase B may add validation actions but should preserve current operational entry points. |
| Settings visibility | Connection, Odoo settings, sync settings, and status sync pages expose sensitive fields in `addons/shopify_connector_pro/views/shopify_backend_views.xml:97-201`. | Locks/readonly/invisible UX must apply here after go-live. |
| Advanced feature flag UI | Advanced flags are admin-only in `addons/shopify_connector_pro/views/shopify_backend_views.xml:173-180`. | Keep this gate and layer validation for money/sync-affecting flags. |
| Goal 2B write gate | Non-superusers without `group_shopify_admin` cannot write `_FEATURE_FLAG_FIELDS` in `addons/shopify_connector_pro/models/shopify_backend.py:1049-1056`. | Goal 4 must not weaken this server-side gate. |
| Backend state | Current backend state values are `draft`, `connected`, and `error` in `addons/shopify_connector_pro/models/shopify_backend.py:262-266`; form statusbar shows `draft,connected` in `addons/shopify_connector_pro/views/shopify_backend_views.xml:44-45`. | Add validated/locked metadata rather than overloading `state` without migration/UX design. |

## 6. Consumer map

Purpose: estimate Phase B cost for ensuring sync/cron/accounting uses only validated/effective settings. Preferred design keeps active backend fields as validated values and stages unvalidated changes outside those active fields, reducing changes in consumer code.

| Field/class | Consumer samples | Implementation impact |
|---|---|---|
| `company_id` MONEY-PATH | Orders use backend company/warehouse values in order vals in `addons/shopify_connector_pro/sync/order_sync.py:203-204`; payment status sync searches company-specific records in `addons/shopify_connector_pro/sync/payment_status_sync.py:448`; refunds search company-specific partners/products in `addons/shopify_connector_pro/sync/refund_sync.py:193-213`. | Do not let a changed company take effect before validation. Active field as last validated value avoids broad consumer rewrites. |
| `warehouse_id` STAGED | Orders include `warehouse_id` in `addons/shopify_connector_pro/sync/order_sync.py:203-204`; inventory derives backend location/warehouse pairs in `addons/shopify_connector_pro/sync/inventory_sync.py:98-99`; abandoned carts create quotations with warehouse in `addons/shopify_connector_pro/models/shopify_abandoned_cart.py:160-161`. | Staged apply-after-validation is safer than letting warehouse change mid-sync. |
| `pricelist_id` MONEY-PATH | Product export reads backend pricelist in `addons/shopify_connector_pro/sync/product_sync.py:59`; order import can assign derived pricelist in `addons/shopify_connector_pro/sync/order_sync.py:275`; abandoned cart quotations can assign a matching pricelist in `addons/shopify_connector_pro/models/shopify_abandoned_cart.py:172-179`. | Price context changes are money-sensitive and should only activate after validation. |
| `shopify_location_id` STAGED | Inventory sync comments and logic describe backend location/warehouse use in `addons/shopify_connector_pro/sync/inventory_sync.py:17` and fallback to backend location/warehouse in `addons/shopify_connector_pro/sync/inventory_sync.py:98-99`. | Location changes should require validation/import-location confirmation. |
| `import_currency_mode` MONEY-PATH | Order import reads the mode in `addons/shopify_connector_pro/sync/order_sync.py:212-213` and presentment handling in `addons/shopify_connector_pro/sync/order_sync.py:519`; refunds read it in `addons/shopify_connector_pro/sync/refund_sync.py:65-70`. | Strict staged; never silently change currency semantics. |
| `auto_create_invoice` MONEY-PATH | Order import checks invoice auto-create in `addons/shopify_connector_pro/sync/order_sync.py:117`, `addons/shopify_connector_pro/sync/order_sync.py:181`, and `addons/shopify_connector_pro/sync/order_sync.py:345`. | Strict staged; controls creation of posted-accounting-adjacent documents. |
| `inventory_quantity_field` STAGED | Inventory sync reads `backend.inventory_quantity_field` in `addons/shopify_connector_pro/sync/inventory_sync.py:65`. | Validate before activation to avoid over/under-stock pushes. |
| `shipping_product_id` MONEY-PATH | Order/refund shipping lines use backend shipping product in `addons/shopify_connector_pro/sync/order_sync.py:1119` and `addons/shopify_connector_pro/sync/refund_sync.py:310`. | Strict staged; affects product/account classification. |
| `batch_size` STAGED | Exporter and sync jobs use backend batch size in `addons/shopify_connector_pro/sync/base_exporter.py:30`, `addons/shopify_connector_pro/sync/customer_sync.py:326`, `addons/shopify_connector_pro/sync/product_sync.py:536`, and `addons/shopify_connector_pro/sync/order_sync.py:1214`. | Staged/performance validation; active field can stay effective value. |
| Reverse sync MONEY-PATH | Account move reverse sync checks `reverse_sync_payment` in `addons/shopify_connector_pro/models/account_move.py:64` and `reverse_sync_refund` in `addons/shopify_connector_pro/models/account_move.py:131`; sale order compute depends on both in `addons/shopify_connector_pro/models/sale_order.py:43-56`. | Strict staged and admin-gated; high user-visible Shopify/money impact. |
| Fulfillment/payment transitions | Fulfillment sync reads `external_fulfillment_handling` in `addons/shopify_connector_pro/sync/fulfillment_sync.py:264`; payment status sync exits if `auto_handle_payment_transitions` is off in `addons/shopify_connector_pro/sync/payment_status_sync.py:63`. | Staged, with money-path treatment for payment transitions. |
| Reconciliation lookback | Reconciliation reads `reconciliation_order_days` in `addons/shopify_connector_pro/models/shopify_reconciliation.py:172-176` and `addons/shopify_connector_pro/models/shopify_reconciliation.py:316`; refunds also use it in `addons/shopify_connector_pro/sync/refund_sync.py:619-645`. | STAGED / VALIDATION-GATED for reconciliation/lookback scope; validate before activation, but not classified as direct money creation. |
| Feature flags in crons | Cron search domains use `enable_promoters` in `addons/shopify_connector_pro/models/shopify_backend.py:1201-1206`, `auto_sync_collections` in `addons/shopify_connector_pro/models/shopify_backend.py:1218-1223`, `enable_payout_import` in `addons/shopify_connector_pro/models/shopify_backend.py:1236-1241`, and `auto_sync_abandoned_carts` in `addons/shopify_connector_pro/models/shopify_backend.py:1289-1294`. | Optional visibility flags can remain admin-editable; cron/sync/money flags should stage because domains immediately affect execution. |

Implementation risk: a “sync/cron reads validated shadow values” design would require many touch points across order, refund, payment, reconciliation, inventory, fulfillment, and crons. The smallest safe design is to keep active backend fields as the validated/effective values and prevent unvalidated writes from landing on those fields.

## 7. Design decisions D1-D8 with recommendations

### D1 — Go-live definition

Current evidence: `state='connected'` is set during backend creation before optional imports in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:81-90`; initial imports run later and may be skipped in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:103-180`.

Options considered: first successful connection test; first successful import; first order sync; manual admin go-live toggle; `state=connected + validated timestamp`; hybrid.

Recommendation: hybrid explicit go-live. A successful connection test produces a connection-validated backend; field mappings initialization should be part of backend creation; import remains optional; an explicit admin “Go Live / Lock Settings” action marks the backend live/locked with a validation timestamp. `state='connected'` remains connection status, not the whole safety state.

Rationale: merchant-first because setup still works through the wizard; reversible because admin can unlock and revalidate; never-wrong-money because imports/orders do not silently define money safety; smallest-safe-diff because it avoids redefining all current `state` semantics.

Effort/risk: adds metadata and UX; avoids changing crons immediately beyond checking live/validated if Phase B chooses that.

### D2 — Lock mechanism

Current evidence: sensitive backend fields are directly visible/editable today in `addons/shopify_connector_pro/views/shopify_backend_views.xml:97-201`; only Goal 2B feature-flag writes have a dedicated admin gate in `addons/shopify_connector_pro/models/shopify_backend.py:1049-1056`.

Options considered: direct write blocked until unlock; pending/shadow fields applied on validation; draft settings snapshot; validation wizard before write; write allowed but sync/cron uses last_validated values.

Recommendation: hybrid apply-after-validation. SAFE-ANYTIME fields write directly. REQUIRES-RETEST credentials/connection identity and STAGED/MONEY-PATH settings are edited through a validation wizard or pending payload, tested, and only then applied to active backend fields. For high-risk or expensive fields, use block-until-unlock plus validate-before-save rather than permanent shadow fields. Do not allow active sync/cron fields to contain unvalidated values.

Rationale: merchant-first because users see why changes are staged; reversible because failed validation leaves current effective settings intact; never-wrong-money because active fields remain last validated values; smallest-safe-diff because existing consumers can continue reading existing backend fields.

Effort/risk: requires careful wizard/server-side write guard design. Lower risk than updating every consumer to read a parallel validated field set.

### D3 — Unlock authority

Current evidence: Shopify Admin has full configuration authority in `addons/shopify_connector_pro/security/shopify_security.xml:30-40`, while Shopify User is read-only/monitoring-oriented in `addons/shopify_connector_pro/security/shopify_security.xml:17-28`.

Recommendation: `shopify_connector_pro.group_shopify_admin` only, with temporary unlock and required reason. Odoo system admins can be members of that group; do not create an implicit bypass except `SUPERUSER_ID` for technical install/migration operations. Unlocks should expire or be one-transaction/one-wizard scoped rather than sticky.

Rationale: preserves current product roles, avoids exposing merchant users to destructive configuration, and provides reversible/admin-audited changes.

### D4 — Audit

Current evidence: backend inherits chatter through `mail.thread` and `mail.activity.mixin` in `addons/shopify_connector_pro/models/shopify_backend.py:14-17`; wizard import failures already create `shopify.sync.log` records in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:123-133`.

Recommendation: use chatter for administrative unlock/change/activation events and `shopify.sync.log` for validation failures that affect sync readiness. Record field names, old/new non-secret values, who unlocked, reason, validation timestamp, failed validation attempts, and activated values. For secrets, record only that a credential was changed/validated; never record plaintext or reversible encrypted values. Avoid a new audit model unless chatter + sync log cannot satisfy review/reporting needs.

### D5 — Feature-flag interaction

Current evidence: `_FEATURE_FLAG_FIELDS` and the admin write gate are in `addons/shopify_connector_pro/models/shopify_backend.py:194-207` and `addons/shopify_connector_pro/models/shopify_backend.py:1049-1056`.

Recommendation: preserve the existing admin gate. Treat money-path flags (`enable_payout_import`, `enable_gift_cards`, `auto_create_abandoned_quotation`, `reverse_sync_payment`, `reverse_sync_refund`, `import_currency_mode`) as strict staged/money-path. Treat sync-affecting flags (`auto_sync_collections`, `auto_sync_abandoned_carts`, `external_fulfillment_handling`) as at least staged/validation-gated after go-live. Optional visibility flags (`enable_metafields`, `enable_customer_tags`, and possibly `enable_promoters` when only showing UI) can remain admin-editable anytime unless they trigger automatic sync or document creation.

### D6 — Credential interaction

Current evidence: credentials are encrypted in create/inverse methods in `addons/shopify_connector_pro/models/shopify_backend.py:358-410`, and the wizard temp backend connection test avoids writing credentials before test in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:55-73`.

Recommendation: credential rotation should open a validation flow that accepts new shop URL/API version/token/secret, tests with a temp backend, and writes encrypted active credentials only after success. `credential_issue` should force recovery/re-entry and remain compatible with lock state. Failed tests must not activate pending credentials, and logs must mask secrets.

### D7 — Onboarding outcome

Current evidence: backend creation and field mapping initialization occur in `action_next_to_import` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:79-101`; imports are optional and can be skipped in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:103-180`.

Recommendation: the wizard should produce a connection-validated backend. “Validated” for first-run means credentials/shop URL/API version passed connection test, required Odoo settings are present, and field mappings were initialized. Webhook registration should be attempted when configured but should not be mandatory for validation until webhook reliability is redesigned; initial import remains optional and is not a go-live prerequisite. Skip import should still leave a connection-validated backend but not imply data sync success.

### D8 — Upgrade posture

Current evidence: existing backend states are only `draft`, `connected`, and `error` in `addons/shopify_connector_pro/models/shopify_backend.py:262-266`; existing live stores likely have connected backends without validation metadata.

Recommendation: grandfather existing `connected` backends as effective/validated on upgrade and lock them after upgrade only with explicit metadata such as “grandfathered validation.” Do not break existing stores or force credential re-entry during upgrade. Draft/error backends remain unlocked/unvalidated until a successful validation path. Prefer a migration/post-init default in Phase B over doing nothing, because the safety model needs deterministic metadata.

## 8. Proposed Phase B implementation boundaries

Phase B should be limited to: backend validation/lock metadata; safe server-side write guards; a settings validation/unlock flow; wizard updates to set validation metadata; UI readonly/visibility for locked fields; audit/chatter/sync-log messages; migration/post-init defaults; and targeted tests. It should not refactor sync engines, money/tax calculation, Shopify API semantics beyond existing test calls, controllers, promoter views, or Goal 5 Command Center.

Implementation should avoid changing every sync consumer by ensuring active backend fields remain the effective validated values. Pending/unvalidated values should live in a transient validation wizard or a compact pending payload and only be applied to active fields after validation succeeds.

## 9. Migration / upgrade posture

Existing connected stores must continue to sync after upgrade. Phase B should backfill validation metadata for current connected backends as “grandfathered/effective,” leave active settings unchanged, and only enforce validation on subsequent sensitive edits. Draft/error backends should not be marked go-live without a successful validation path. Credential encryption must remain untouched; no migration should expose or rewrite plaintext secrets.

## 10. Phase B test plan

Required tests to implement later, not in Phase A:

- Non-admin cannot unlock or activate validation-sensitive changes.
- Locked sensitive field cannot take effect without validation.
- Admin unlock permits a staged change but does not activate it until validation succeeds.
- Failed connection test does not activate credentials/settings.
- Successful validation activates settings and records audit evidence.
- Sync/cron consumes only validated/effective values.
- Wizard produces a connection-validated backend.
- Existing DB upgrades safely and keeps current connected stores effective.
- Credentials remain encrypted and plaintext secrets are not logged/audited.
- Goal 2B admin gate remains enforced for `_FEATURE_FLAG_FIELDS`.
- Odoo.sh fresh install, upgrade, and full suite are green before acceptance/merge.

## 11. Report-only AUDIT candidates

These are report-only Phase A findings; do not edit `AUDIT.md` in this task.

1. **Goal4-AUD-CAND-01 — No durable validated/go-live/locked backend state.** The wizard creates a backend with `state='connected'` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:81-90`, while imports are optional later in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:103-180`.
2. **Goal4-AUD-CAND-02 — Webhook registration failure is swallowed during onboarding.** `action_next_to_import` catches all exceptions from `backend.action_register_webhooks()` and uses `pass  # Non-critical` in `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py:92-97`. This may overlap prior webhook reliability audit history and should be checked before assigning a new AUD ID.
3. **Goal4-AUD-CAND-03 — Live backend settings are currently directly editable without validation.** Sensitive connection, company, warehouse, sync, money, fulfillment, payment, and reconciliation fields are visible in `addons/shopify_connector_pro/views/shopify_backend_views.xml:97-201`, while the only explicit server-side write gate found is the Goal 2B feature-flag admin gate in `addons/shopify_connector_pro/models/shopify_backend.py:1049-1056`.

## 12. Open questions for Ahmed

1. Should “Go Live / Lock Settings” be an explicit merchant/admin action after connection validation, or should it happen automatically when the wizard completes?
2. Should webhook registration failure block first-run validation, or remain visible-but-non-blocking until a later webhook reliability goal?
3. Which optional feature flags should remain admin-editable anytime versus requiring validation after go-live?
4. Should Phase B introduce a persistent pending settings model, or keep pending values inside a transient validation wizard to minimize data-model footprint?
5. Should existing connected backends be locked immediately after upgrade as grandfathered/effective, or remain unlocked until the first admin edit?
