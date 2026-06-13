# Goal 2 Phase B Manifest — Feature Flag Implementation

Date: 2026-06-13  
Base: `review/full-audit` known-green commit `3fb645797748278c1c86d9dcc5c25fd884a6164e`  
Harness branch: `work` (accepted because HEAD exactly matches the known-green base)  
Authority: `docs/product/FEATURE_FLAGS.md` Phase A registry and DEC-028 (`Proposed — Phase B review`).

## Preflight Evidence

Executed before implementation:

```text
git branch --show-current        -> work
git rev-parse HEAD               -> 3fb645797748278c1c86d9dcc5c25fd884a6164e
git status --short               -> clean
rg -n "Goal 2 Phase A design complete" STATUS.md -> line 3 present
test -f docs/archive/GOAL2A_MANIFEST.md && echo GOAL2A-present
test -f docs/product/FEATURE_FLAGS.md && echo FEATURE_FLAGS-present
```

## Final Field List

| Registry feature | Final field used | Reused or new | N1/N3 justification | Fresh install default | Existing DB / upgrade default |
|---|---|---|---|---|---|
| Promoters / discount codes | `enable_promoters` | New backend boolean | No existing backend toggle gates promoter/discount-code surfaces or the discount cron. DEC-022 keeps this first-class and default ON. | ON | Explicitly seed ON so the existing always-running discount cron and existing menus remain available. |
| Collections | `auto_sync_collections` | Reused existing backend boolean | Existing field already gates collection cron/search and is listed by Phase A as the current behavior gate. No parallel `enable_collections` field. | ON (existing default) | Preserve each backend value; no migration conversion. |
| Abandoned carts → quotation | `auto_sync_abandoned_carts` + `auto_create_abandoned_quotation` | Reused existing backend booleans | N3 requires reusing both existing fields unless insufficient. `auto_sync_abandoned_carts` gates import/menu visibility; `auto_create_abandoned_quotation` continues to gate quotation creation. | Preserve existing defaults (`False`/`False`) | Preserve each backend value; no migration conversion. |
| Payout visibility import | `enable_payout_import` | New backend boolean | No existing backend toggle gates payout import; current cron imports for all connected backends. | ON | Explicitly seed ON so existing connected stores continue importing payouts. |
| Gift-card reference import | `enable_gift_cards` | New backend boolean | No existing backend toggle gates gift-card surfaces/import helpers. | ON | Explicitly seed ON to preserve existing record visibility/import availability. |
| Metafields / mappings | `enable_metafields` | New backend boolean | No existing backend toggle gates mapping/import/export helpers. | OFF | Explicitly seed OFF; existing records are retained, and Phase A default is OFF until mapping write-safety is tested. This hides an optional advanced surface but does not delete data or change core behavior. |
| Customer tags | `enable_customer_tags` | New backend boolean | No existing backend toggle gates customer-tag surface. | OFF | Explicitly seed OFF; existing records are retained, and Phase A default is OFF until product role is confirmed. |
| Reverse payment push | `reverse_sync_payment` | Reused existing backend boolean | N1 explicitly requires reusing the existing money-path toggle. | OFF (existing default) | Preserve each backend value; no migration conversion. |
| Reverse refund push | `reverse_sync_refund` | Reused existing backend boolean | N1 explicitly requires reusing the existing money-path toggle. AUD-029 is verified against this field. | OFF (existing default) | Preserve each backend value; no migration conversion. |
| External fulfillment auto-validation | `external_fulfillment_handling` | Reused existing backend selection | N1 explicitly requires reusing the existing selection; `auto_validate` remains the enabled state. | `activity` (existing default) | Preserve each backend value, including `auto_validate`; no migration conversion. |
| Shopify Markets / presentment currency | `import_currency_mode` | Reused existing backend selection | N1 explicitly requires reusing the existing selection; `presentment` remains the enabled state. | `company` (existing default) | Preserve each backend value, including `presentment`; no migration conversion. |

## Gating Points by Surface

Line references are from the known-green base before implementation.

| Feature | Surface | Planned gating point |
|---|---|---|
| Promoters / discount codes | Menus | `menu_shopify_promoters_section`, `menu_shopify_promoters`, `menu_shopify_discount_codes`, `menu_shopify_discount_usage` in `addons/shopify_connector_pro/views/shopify_menu.xml:197-218`. Runtime menu visibility is controlled by backend feature availability rather than deleting menus. |
| Promoters / discount codes | Cron | `_cron_sync_discounts` in `addons/shopify_connector_pro/models/shopify_backend.py:1144-1156`; when OFF, create visible skip evidence instead of silently returning. |
| Collections | Menu | `menu_shopify_collections` in `addons/shopify_connector_pro/views/shopify_menu.xml:136-140`; availability follows `auto_sync_collections`. |
| Collections | Cron/code path | `_cron_sync_collections` in `addons/shopify_connector_pro/models/shopify_backend.py:1158-1171`; search currently filters ON backends only, so Phase B adds visible skip evidence for connected OFF backends. |
| Abandoned carts | Menu | `menu_shopify_abandoned_carts` in `addons/shopify_connector_pro/views/shopify_menu.xml:160-164`; availability follows `auto_sync_abandoned_carts`. |
| Abandoned carts | Cron/code path | `_cron_import_abandoned_carts` in `addons/shopify_connector_pro/models/shopify_backend.py:1223-1238`; search currently filters ON backends only, so Phase B adds visible skip evidence for connected OFF backends. Quotation creation remains gated by `auto_create_abandoned_quotation` inside the abandoned-cart sync path. |
| Payout visibility import | Menu | `menu_shopify_payouts` in `addons/shopify_connector_pro/views/shopify_menu.xml:172-176`; availability follows `enable_payout_import`. |
| Payout visibility import | Cron/code path | `_cron_import_payouts` in `addons/shopify_connector_pro/models/shopify_backend.py:1173-1195`; OFF logs visible skip and does not call `PayoutSync.import_payouts`. |
| Gift-card reference import | Menu/code path | `menu_shopify_gift_cards` in `addons/shopify_connector_pro/views/shopify_menu.xml:178-182`; import helper in `addons/shopify_connector_pro/sync/gift_card_sync.py:20-97` will be guarded before Shopify API calls if invoked while OFF. |
| Metafields / mappings | Menus/code paths | `menu_shopify_metafields` in `addons/shopify_connector_pro/views/shopify_menu.xml:190-194`; import/export helpers in `addons/shopify_connector_pro/sync/metafield_sync.py:20-35` and `:91-134` will be guarded before Shopify API/model writes while OFF. |
| Customer tags | Menu | `menu_shopify_customer_tags` in `addons/shopify_connector_pro/views/shopify_menu.xml:184-188`; no scheduled/webhook sync path exists in the registry. |
| Reverse payment push | Code path | Existing gate in `addons/shopify_connector_pro/models/account_move.py:48-76` via `reverse_sync_payment`; Phase B verifies this remains complete and visible. |
| Reverse refund push | Code path | Existing gate in `addons/shopify_connector_pro/models/account_move.py:108-135` via `reverse_sync_refund`; Phase B adds/keeps AUD-029 production-path regression evidence that OFF does not call `refundCreate`. |
| External fulfillment auto-validation | Webhook/code branch | `external_fulfillment_handling == 'auto_validate'` branch in `addons/shopify_connector_pro/sync/fulfillment_sync.py:264-288`; no parallel boolean. |
| Presentment currency | Order/refund import code branch | `import_currency_mode == 'presentment'` branch in `addons/shopify_connector_pro/sync/order_sync.py:212` and refund currency handling in `addons/shopify_connector_pro/sync/refund_sync.py:65-70`; no parallel boolean and no core order/refund webhook gate. |

## Migration / Upgrade Plan

1. Add only these new backend columns: `enable_promoters`, `enable_payout_import`, `enable_gift_cards`, `enable_metafields`, and `enable_customer_tags`.
2. Reuse the existing toggles for collections, abandoned carts, reverse payment, reverse refund, fulfillment auto-validation, and presentment currency. Do not add `enable_collections`, `enable_abandoned_carts`, `enable_reverse_payment_push`, `enable_reverse_refund_push`, `enable_external_fulfillment_auto_validate`, or `enable_presentment_currency_import`.
3. Add a migration/post-init seeding step for the new columns so upgraded databases get explicit behavior-preserving values instead of relying on ORM defaults:
   - `enable_promoters = True`
   - `enable_payout_import = True`
   - `enable_gift_cards = True`
   - `enable_metafields = False`
   - `enable_customer_tags = False`
4. Existing field values are preserved in-place for reused toggles. In particular, existing `reverse_sync_refund=True`, `external_fulfillment_handling='auto_validate'`, and `import_currency_mode='presentment'` records must remain unchanged after `-u`.
5. New flag editing is restricted by a server-side `write` guard to `shopify_connector_pro.group_shopify_admin`, the existing connector admin group defined in `addons/shopify_connector_pro/security/shopify_security.xml` and used for full backend write access in `addons/shopify_connector_pro/security/ir.model.access.csv`.
6. Visible OFF evidence is recorded through connector-facing records/logging for cron/code paths; OFF never silently drops a webhook or scheduled event.

## Non-Flaggable Core Guardrail

Phase B must not add feature guards to core order/product/customer/inventory/refund-import/webhook-infrastructure/sync-log/import-job/error-digest/reconciliation/total-check/setup flows listed in `docs/product/FEATURE_FLAGS.md:29-40`. Any required change in those paths is an escalation stop.
