# Sold products, section visibility and scroll tracking

Authorized follow-up: add a sold-product ranking, allow unwanted sections such as
HR to be disabled in Settings, and correct the left category highlight while scrolling.

Allowed changes: the two dashboard addons, their native/controller tests and this
feature dossier. Existing work is preserved. Production, other addons and financial
mappings/business data are excluded. Authorized Adams staging remains the UAT target.

## Behavior and implementation

- Sales shows the top five native Invoice Analysis product groups by signed net
  invoiced sales, excluding tax. Posted customer invoices/credit notes use the applied
  company and invoice-date period. Full ranking and product-specific native report
  actions use existing scoped adapters. No independent sales calculation is added.
- Administrators use Settings → Executive Dashboard or the dashboard's Settings
  shortcut to enable/disable each of six sections for the selected company. All are
  enabled by default for compatibility. Save and reload the dashboard. Hidden
  sections disappear from both navigation surfaces, section bodies, automatic
  requests and executive summaries. These visibility choices do not change native
  permissions or prevent authorized access to the native applications.
- Scroll tracking measures the sticky navigation height instead of a fixed 110px
  assumption, handles the end of the page, and retains a clicked short section when
  it cannot align at the top. Wheel/touch/keyboard/scrollbar input resumes position
  tracking. ResizeObserver handles asynchronously changing section heights.
- English/Arabic captions, existing native light/dark styling and keyboard access
  are retained. An all-disabled company has an explicit empty workspace message.

## Acceptance and evidence

Required: independent known-value product/refund/date/draft/archived fixtures and
native product drilldown; company-specific settings persistence and unauthorized
writes; hidden sections absent in native UI; real browser product content and
click/manual-scroll selection across the existing EN/AR/light/dark/six-width matrix;
focused stale-response, hidden-source loading and scroll-geometry controller tests.

Current local result: **28 controller checks pass**. Candidate source
`6ac4798ab98a395a4d96bdd3b5c1fdb64233ca35`, tree
`bc059673d702a5f8fd7b3eba1ec333543c0f3e06`. Native qualification and live
staging screenshots are **pending**, not passed: Odoo.sh still shows Build queued
with no candidate logs/CONNECT link. Its error dialog found no errors; platform
health reports all systems operational, which does not prove this build ran.
Existing staging remains 06a5274b. A fresh native backup is verified at
2026-09-21 08:28:54 UTC at that revision. HR has not yet been disabled in live
staging; do so through the new native Settings view after the qualified upgrade.
The guide and UAT checklist document the new journeys for that deployment.

Native settings view structure follows Odoo 19's own [base_setup settings view](https://github.com/odoo/odoo/blob/19.0/addons/base_setup/views/res_config_settings_views.xml).

## Upgrade and recovery

Addon versions 19.0.1.3.0 introduce six Boolean company columns and related native
settings fields. Existing companies default to all sections enabled; no financial
schema, formula or ACL is changed. Upgrade both addons. Re-enable a section to restore
its display. Reverting code should retain these harmless columns and preserve all
business data; return only the two addon directories to the previous qualified
staging 06a5274b if recovery is needed. Owner acceptance and production release remain
separate from implementation/native test results.
