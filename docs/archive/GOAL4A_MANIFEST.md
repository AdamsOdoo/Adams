# Goal 4 Phase A Manifest — Settings-safety research + design

## Scope

Goal 4 Phase A is documentation-only research/planning for wizard-first setup and backend settings safety. No code, XML, security, manifest, migration, hook, README, test, or AUDIT changes are part of this task.

## Files read

- `AGENTS.md`
- `STATUS.md`
- `AUDIT.md`
- `FINALIZE.md`
- `docs/product/MENU_IA.md`
- `docs/architecture/DECISIONS.md`
- `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py`
- `addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml`
- `addons/shopify_connector_pro/models/shopify_backend.py`
- `addons/shopify_connector_pro/views/shopify_backend_views.xml`
- `addons/shopify_connector_pro/security/shopify_security.xml`
- `addons/shopify_connector_pro/sync/order_sync.py`
- `addons/shopify_connector_pro/sync/refund_sync.py`
- `addons/shopify_connector_pro/sync/inventory_sync.py`
- `addons/shopify_connector_pro/sync/payment_status_sync.py`
- `addons/shopify_connector_pro/sync/fulfillment_sync.py`
- `addons/shopify_connector_pro/sync/product_sync.py`
- `addons/shopify_connector_pro/sync/customer_sync.py`
- `addons/shopify_connector_pro/sync/base_exporter.py`
- `addons/shopify_connector_pro/sync/abandoned_cart_sync.py`
- `addons/shopify_connector_pro/models/account_move.py`
- `addons/shopify_connector_pro/models/sale_order.py`
- `addons/shopify_connector_pro/models/shopify_reconciliation.py`
- `addons/shopify_connector_pro/models/shopify_abandoned_cart.py`

## Commands run

```bash
git remote -v || true
git branch --show-current || true
git status --short
git rev-parse HEAD
git rev-parse --show-toplevel
test -f addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py && echo "wizard model exists" || echo "wizard model missing"
test -f addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml && echo "wizard view exists" || echo "wizard view missing"
test -f addons/shopify_connector_pro/models/shopify_backend.py && echo "backend model exists" || echo "backend model missing"
test -f addons/shopify_connector_pro/views/shopify_backend_views.xml && echo "backend views exist" || echo "backend views missing"
rg -n "_log_feature_skip" addons/shopify_connector_pro || true
PREWORK_HEAD=$(git rev-parse HEAD); echo "PREWORK_HEAD=$PREWORK_HEAD"
nl -ba addons/shopify_connector_pro/wizards/shopify_onboarding_wizard.py | sed -n '1,210p'
nl -ba addons/shopify_connector_pro/wizards/shopify_onboarding_wizard_views.xml | sed -n '1,130p'
nl -ba addons/shopify_connector_pro/models/shopify_backend.py | sed -n '1,230p'
nl -ba addons/shopify_connector_pro/models/shopify_backend.py | sed -n '312,465p'
nl -ba addons/shopify_connector_pro/models/shopify_backend.py | sed -n '1035,1310p'
nl -ba addons/shopify_connector_pro/views/shopify_backend_views.xml | sed -n '25,210p'
nl -ba addons/shopify_connector_pro/security/shopify_security.xml | sed -n '1,80p'
rg -n "company_id|warehouse_id|pricelist_id|shopify_location_id|import_currency_mode|auto_create_invoice|inventory_quantity_field|shipping_product_id|batch_size|reverse_sync_payment|reverse_sync_refund|external_fulfillment_handling|auto_handle_payment_transitions|reconciliation_order_days|enable_promoters|enable_payout_import|enable_gift_cards|enable_metafields|enable_customer_tags|auto_sync_collections|auto_sync_abandoned_carts|auto_create_abandoned_quotation" addons/shopify_connector_pro/{sync,models}
```

## Evidence tables produced

- Current onboarding wizard map.
- Wizard transition/method map.
- Backend settings lock matrix.
- Credential storage and rotation constraints.
- Existing security/visibility/write gates map.
- Consumer map for validation-sensitive and money-path settings.
- D1-D8 design decision recommendations.
- Phase B boundaries and test plan.

## Allowed files written

- `docs/product/GOAL4_SETTINGS_LOCK.md`
- `docs/archive/GOAL4A_MANIFEST.md`
- `docs/architecture/DECISIONS.md`
- `STATUS.md`

## No-code/no-XML confirmation

This Phase A task intentionally does not edit Python code, XML views/actions/menus, security files, manifests, tests, migrations, hooks, README, or `AUDIT.md`.

## Report-only AUDIT candidates

1. **Goal4-AUD-CAND-01 — No durable validated/go-live/locked backend state.** The wizard creates a backend as `state='connected'` before optional imports.
2. **Goal4-AUD-CAND-02 — Webhook registration failure is swallowed during onboarding.** The wizard catches all webhook registration exceptions and treats them as non-critical.
3. **Goal4-AUD-CAND-03 — Live backend settings are directly editable without validation.** Sensitive credentials, company, warehouse, sync, inventory, currency, invoice, payment, refund, fulfillment, and reconciliation settings appear in the backend form, while only Goal 2B feature flags have an explicit admin write gate.

## Unresolved design risks

- A permanent shadow-field design would require broad sync/cron/accounting consumer changes; the proposal avoids that by keeping active fields as validated/effective values.
- Webhook registration is currently optional/non-blocking in onboarding; Ahmed should decide whether failed webhook registration blocks validation.
- Existing connected backends need deterministic grandfathering metadata in Phase B to avoid upgrade breakage.
- Feature flags vary in risk: optional visibility flags may not need the same lock behavior as money-path/sync-impacting flags.

## Reviewer checklist

- Confirm the lock matrix classification for all money-path fields.
- Confirm whether explicit Go Live is desired versus automatic lock after wizard completion.
- Confirm whether pending values should be transient or persisted.
- Confirm webhook validation requirements.
- Confirm existing-backend upgrade posture.
- Confirm no code/XML/security/manifest/test changes were made.
