# Executive dashboard — report-first handoff v4

19 September 2026

## Use these files

1. `Astra_Dashboard_Implementation_Prompt_v4.md`: implementation task.
2. `Dashboard_Report_First_Contract_v4.md`: authoritative data, report-selection, security and acceptance requirements. Replaces v2/v3 contracts.
3. `Odoo_Executive_Dashboard_UX_v2.html`: unchanged visual/interaction reference with fictional fixtures, not production calculation logic.

The PNG files are unchanged v2 visual previews, not live Odoo evidence.

## What changed

Report-first is explicitly mandatory for every department, including Partner Ledger, native aging, Inventory Stock/valuation/Forecast and related views, Sales Analysis, Invoice Analysis, Purchase Analysis/vendor measures, and relevant CRM/HR reports. Section 2.6 identifies source boundaries and the need for different native report adapters, dynamic dimensions, and verification of actual metric formulas. The acceptance matrix now checks parity across all enabled report families, not only Finance. Existing dynamic bank/cash discovery remains mandatory.

No live Odoo implementation or integration test was performed for this documentation update. No repository, source transactions or report definitions were changed. Documentation/package integrity checks do not establish application correctness. All installation-specific actions, methods and field mappings must be verified in the intended authorized development environment.

## Priority

Data accuracy first. Native result when available. Supported native grouping/filtering before new formulas. Explain and approve genuine gaps before enabling custom logic. Click through with matching scope. Never replace unavailable native results with guessed or sample figures.
