# ED-001 acceptance plan

Development continues on the dedicated dashboard branch. Access and licensed
source inspection have succeeded. Latest evidence is in
[implementation status](implementation-status.md). Fifty native tests and sixteen
isolated controller tests pass on their recorded candidate. Bounded native browser
checks do not replace the full acceptance matrix below. Original v4 scope remains.

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

## Current gate ledger — 20 September 2026

| Gate | Evidence and remaining boundary |
|---|---|
| ED-ENV | Exact feature source/build and licensed source inspected; harness pin reverified. UAT company/localization/report policy and custom gaps still need owner decisions. |
| ED-AR / ED-FIN / ED-CASH / ED-LEDGER | Native adapters and bounded known-value fixtures pass, including historical settlement, dated accounts, aging, CFS, ledger scopes, budgets and standard forecast. Full customer-configured parity/journey matrix remains open. |
| ED-SEC | Native permission/company/RPC/export/context/revocation fixtures pass. Full role/field/currency/browser matrix remains open. |
| ED-SALES | Native grouped totals, 27-row completeness/export, recent records, commercial margin and scoped routes pass. Full UI/export/currency/UoM journeys remain open. |
| ED-OPS | Native historical/current stock quantity/valuation, forecast/history routes, workforce, leave, CRM and purchase worklists have bounded fixtures. Expanded warehouse/owner/aging/shortage acceptance remains open. |
| ED-UX / ED-ASYNC | 16 controller checks; native EN/AR at six widths with drawer/focus and drilldown assertions. Twelve captures retained. Full reference comparison, mobile interactions, zoom and accessibility remain open. |
| ED-DELIVERY | ac52010/build 38346414 passes 50 native install tests. Older core upgrade is retained for its original source only. Current finance upgrade and full UAT closure remain open. |
| ED-PERF / ED-FULFILL | Representative-volume p95 remains unmeasured. Native product/UoM delivery quantities pass; backlog value/on-time definitions require owner approval. |

Failed 63f9823/build 38346314 is retained as failed. Its native Sass defect was
fixed at ac52010 without weakening checks. Prior harness qualification is reused.
