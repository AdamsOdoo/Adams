# ED-001 acceptance plan

The first implementation slice is in progress after the owner deferred Odoo.sh login. The latest feature-specific contract passed 17 fresh-install and 12 core update tests in the private runner; full Enterprise discovery and browser acceptance remain blocked. Seven isolated JavaScript controller tests pass locally; they do not replace Odoo browser acceptance. These IDs retain the original v4 acceptance scope.

| IDs / gate | Required behavior and evidence |
|---|---|
| ED-ENV / G0 | Pin actual Community/Enterprise/dependency sources and build; inspect installed modules, company/localization, actions/variants, permissions and each source-catalog row. Record exact supported options and all custom-gap approvals. |
| ED-AR-01 / G1 | Independently specified 100,000 invoice, 40,000 settled by Aug 31 and 60,000 in September: native aging and dashboard both show 60,000 at Aug 31 and zero after final settlement under aligned scope. Expected results must not call the dashboard helper. |
| ED-AR-02 / G1 | Installments, due-today boundary, credits/refunds, partial settlement, unapplied payments, write-offs, overpayments, draft/cancelled, backdated entries, FX/rounding, negative totals, hidden-zero and paged rows. Match native cut-off semantics. |
| ED-AR-03 / G1 | Total/overdue/bucket -> same scoped native aging -> original record -> full matching export -> back navigation. Verify effective company, cut-off, search, posting state, currency, complete row set and safe spreadsheet content. |
| ED-SEC / every gate | Owner, finance, sales-only, no-dashboard and separate-company users; direct RPC, invalid companies/options, restricted fields/HR/export, permission revocation and stale old-company responses. No leaked aggregates, blanket sudo or unrestricted query endpoint. |
| ED-FIN / G2 | Independently specified balanced accounting case, losses/refunds; full-precision native P&L/BS/CFS/GL/TB/ratios/budgets parity for approved definitions; accounting revenue differs truthfully from invoiced sales. |
| ED-CASH / G2 | Add zero-balance bank and cash accounts; post bank and general-journal entries; rename/relink/archive; no-journal account; overlapping linkage; report-excluded directory entry; negative/foreign currency; company switching and more-than-one-page accounts. Next refresh discovers records without source/config list changes; native totals stay complete. |
| ED-LEDGER / G2 | Customer, vendor and dual-role partner; child/commercial contacts, opening balance, period movement and historical settlement. Native Partner Ledger and aging each match independently with their differences explained. |
| ED-DRIFT / G2–G4 | New report variant/expression/account/dimension; missing mapping; changed currency/group/filters; complete totals despite hidden/paged details. Expose unsupported scope or missing mapping; no guessed zero. |
| ED-SALES / G3 | Native Sale/Invoice Analysis totals, native distinct order count, exact event dates/state/tax/currency/UoM, inactive/unassigned salesperson, new dimension records, weighted averages and margin basis. Native UI/export is an independent comparator. |
| ED-FULFILL / G3 | Partial deliveries, returns/cancellation, line types, timezone, changed promises, missing history, open-late versus completed-late, attribution, missing targets and no completed deliveries. Definitions with genuine native gaps need approval before implementation. |
| ED-OPS / G4 | Native Inventory Stock/valuation/Forecast/Locations/Moves/Replenishment parity including consignment/returns/reservations/history; Purchase scope/averages/planned vs actual timing; dynamic vendors/products/warehouses/stages/departments; installed authorized CRM/HR measures. |
| ED-UX / each stable slice | Actual Odoo desktop/mobile English/Arabic, RTL/mixed references, keyboard/focus, chart tables, scoped drill-down/back, preference persistence, empty/loading/restricted/not-installed/not-configured/stale/error distinctions. Widths 320/390/768/1024/1440/1920; zoom/reflow. Supplied PNGs do not count. |
| ED-ASYNC / each stable slice | Delayed/failed sections, rapid filter changes, old response suppression, repeated refresh and component destruction. No unbounded polling or false freshness/completeness/reconciliation badges. |
| ED-PERF / G4 | Measure p95 usable Finance and filter refresh against representative volume/hardware; initial targets <=3s and <=2s, openly adjusted only with evidence. Profile query/record growth and concurrency; preserve native calculation fidelity. |
| ED-DELIVERY / G4 | Exact-source install/update, raw discovered test counts, independent review when available, real screenshots, private retained evidence with retrieval verification, configuration/user guidance/upgrade notes and finance-owner UAT. No unresolved Critical/High defects or unexplained report differences. |

Run affected slice checks during development and batch broad native/browser/security/performance tests at stable milestones. Reuse unchanged harness qualification. Any feature change invalidates only the relevant feature evidence unless wider risk justifies a broader rerun. A failed, blocked, skipped or zero-discovery campaign is not a pass.

Owner/finance UAT will confirm real source completeness, report variant/financial definitions, cut-off policy and any additional logic. Report parity does not audit the books. Development verification, UAT readiness, business acceptance and production release remain distinct states.

## Expanded implementation gate ledger

| Gate | Current evidence boundary |
|---|---|
| ED-ENV | Authorized onboarding Enterprise DB inspected. Feature build identity and licensed source still blocked at GitHub device verification; no new permission request. |
| ED-AR / ED-FIN / ED-LEDGER | Financial numeric adapters are not implemented. Native definitions/UI inspection is not parity evidence. |
| ED-CASH | Dynamic authorized account/journal metadata discovery implemented and tested. Native dated balances and full mandatory financial cases remain blocked. |
| ED-SEC | RPC membership/company checks, underlying account permissions, export checks, context validation and revocation covered by bounded fixtures. Full role/company/browser matrix remains pending. |
| ED-SALES | Invoice fixtures and grouped/trend/source action tests; expanded Sale/Purchase known-value fixtures passed. Currency/UoM/history/complete browser matrix still pending. |
| ED-OPS | Current Stock product quantities, native CRM weighted pipeline and signed Time Off adapter implemented. The HR test covers action scope, not leave-value parity. Other operational scope remains unfinished. |
| ED-UX / ED-ASYNC | Seven isolated controller checks and static/catalog checks. Stylesheet native compilation added. No deployed DOM/visual/RTL/mobile pass. |
| ED-DELIVERY | Feature-native install/update campaign passed on exact candidate 27817631693a4babb1a9d3434697cd7c3e0363cb. No UAT/release closure, independent review or production deployment. |
| ED-PERF / ED-FULFILL | Not run / not implemented; source discovery and business-definition approval remain required where native gaps are established. |

The failed expanded run is retained, not relabeled as passing. Corrected fixture
roles and flush boundaries are recorded alongside the new campaign result in
implementation-status.md. No application ACL was loosened to pass a fixture.
