# STATUS.md — Current State

Updated 2026-06-13 — Goal 2 Phase B implemented in branch; Odoo runtime verification pending relay because this Codex workspace has no Odoo checkout/runtime.

## What changed
- Goal 2B manifest was recorded before code in `docs/archive/GOAL2B_MANIFEST.md`.
- Backend-scoped feature flags were implemented for promoters, payout import, gift cards, metafields, and customer tags; existing toggles were reused for collections, abandoned carts, reverse payment/refund, external fulfillment handling, and presentment currency.
- Disabled optional cron/code paths now create visible `shopify.sync.log` skip evidence instead of silent returns.
- Feature menu actions filter records by the final backend flag/reused toggle; existing records are retained.
- AUD-029 coverage was added for posting a real credit note with reverse refund push OFF and asserting Shopify refund creation is not called.

## Verified locally
- `git branch --show-current`, `git rev-parse HEAD`, `git log --oneline -5`, `git status --short`, Phase A marker/file checks passed at session start on known-green base `3fb645797748278c1c86d9dcc5c25fd884a6164e`.
- `python3 -m py_compile $(find addons/shopify_connector_pro -name '*.py' -print)` passed.
- XML parse check over `addons/shopify_connector_pro/**/*.xml` passed.
- Odoo runtime tests could not run locally: `/home/user/odoo/odoo-bin` is absent and `import odoo` raises `ModuleNotFoundError`.

## Pending verification
- Ahmed/Odoo.sh relay must run the Goal 2B feature-flag test tags and at least one full suite command from the final relay block.
- Required three-profile counts (`adams_test_fresh`, `adams_strict1`, `adams_strict_vat`) and install/upgrade log cleanliness remain pending Odoo.sh/runtime confirmation.
- AUD-029 fail-before/pass-after is limited by the known-green base already containing the reused `reverse_sync_refund` guard; the new regression test is ready for Odoo runtime execution.

## Next action
- Send Goal 2B to Claude adversarial review after Ahmed relays Odoo.sh/runtime results.
- Do not merge and do not proceed to Goal 3 until runtime counts/logs are confirmed and any findings are fixed or accepted.
