# Goal 3 Phase A Manifest

## Scope

Goal 3 Phase A research/planning only. Implementation remains blocked pending Phase B approval.

## Exact files read

- `AGENTS.md`
- `STATUS.md`
- `addons/shopify_connector_pro/views/shopify_menu.xml`
- `addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml`
- `addons/shopify_connector_pro/views/manager_dashboard_action.xml`
- `addons/shopify_connector_pro_dashboard/views/manager_dashboard_action.xml`
- `addons/shopify_connector_pro/security/shopify_security.xml`
- All XML files under `addons/shopify_connector_pro/views/*.xml`
- All wizard XML files under `addons/shopify_connector_pro/wizards/*.xml`
- Dashboard XML files under `addons/shopify_connector_pro_dashboard/views/*.xml`
- `addons/shopify_connector_pro/__manifest__.py` and `addons/shopify_connector_pro_dashboard/__manifest__.py` for dashboard-module context only
- `docs/architecture/DECISIONS.md`

## Evidence tables produced

- Full current menu inventory in `docs/product/MENU_IA.md` section 2.
- Full button inventory in `docs/product/MENU_IA.md` section 3.
- Role/visibility map in `docs/product/MENU_IA.md` section 4.
- Preserved domains/groups regression guard in `docs/product/MENU_IA.md` section 7.

## Commands run

- `git remote -v || true`
- `git branch --show-current || true`
- `git status --short`
- `git rev-parse HEAD`
- `git rev-parse --show-toplevel`
- `rg -n "_log_feature_skip" addons/shopify_connector_pro || true`
- `find addons -path '*views*' -name '*.xml' | sort | rg 'shopify|dashboard' || true`
- `find addons -path '*security*' -type f | sort | rg 'shopify|dashboard' || true`
- `rg -n "<button\b" addons/shopify_connector_pro/views addons/shopify_connector_pro/wizards addons/shopify_connector_pro_dashboard/views`
- Python extraction scripts for menus, buttons, action domains, duplicate action IDs, and documentation generation.

## Allowed files written

- `docs/product/MENU_IA.md`
- `docs/archive/GOAL3A_MANIFEST.md`
- `docs/architecture/DECISIONS.md`
- `STATUS.md`

## No-code/no-XML confirmation

No Python, XML, security, manifest, test, sync, migration, hook, README, or AUDIT file was edited.

## AUDIT.md candidate findings, report-only

- Duplicate `action_manager_dashboard` record IDs exist in `addons/shopify_connector_pro/views/manager_dashboard_action.xml:3` and `addons/shopify_connector_pro_dashboard/views/manager_dashboard_action.xml:3`. The dashboard module manifest currently has `data: []`, so this may be historical/stub-only, but Phase B should classify it before any IA implementation.
- The `shopify_connector_pro_dashboard` manifest says the module is a hollow merged stub with no data files, while `addons/shopify_connector_pro_dashboard/views/manager_dashboard_menu.xml` still defines a separate top-level `Shopify Manager` menu. Treat as report-only until an upgrade-safe cleanup decision is approved.

- Promoter stat buttons are non-functional stubs: Orders, Revenue, Discounts, and Commission all call `action_dummy` at `addons/shopify_connector_pro/views/shopify_promoter_views.xml:32-42`, and `action_dummy` is a literal placeholder stub at `addons/shopify_connector_pro/models/shopify_promoter.py:58-60`. Since promoters are first-class v1 (DEC-022), these non-functional placeholder stat buttons are a Goal-3-relevant defect. Report-only in Phase A; do not edit AUDIT.md and do not fix in this task.
