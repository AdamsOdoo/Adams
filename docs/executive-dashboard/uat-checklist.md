# Adams For Men dashboard — staging UAT

## Current owner UAT entry — 22 September 2026

Use [Adams For Men staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004).
Technical preparation is complete at feature `948a006a` / build38418408 and
staging `9af98d42` / build38419464. See [qualification, evidence and limits](uat-handoff-20260922.md).
Both Medium visual findings are closed by separate rendered review; 65 native
tests and 37 controller checks pass. All 21 metric values, 21 cash rows and cash
bridge are unchanged at the September 1–21 comparison scope. HR remains disabled.

The remaining owner tasks are financial interpretation/source-warning review,
visual acceptance against UX v2, and acceptance of normal business journeys.
Keep the owner checklist below unsigned until the owner completes it. Keep PR #214
draft. No production or main action is authorized.

## Historical checkpoint — superseded by the handoff above

## Current visual-polish follow-up — not yet ready for owner UAT

The current polish work is **under qualification**. The `a88e9628` readiness
statement retained below is historical and does not approve the new candidate.
The latest reviewed run (`7930`, build **38414698**) passed 65 Odoo tests and
retained 240 captures, but review of 40 contact sheets found **Medium RTL
stock-table clipping**. The correction is implemented at `c17dd27e4eb982eee995f547d93e5e44de19b6a1` but remains open until new rendering evidence confirms it. Build38415574 reported a platform error and Cloud Browser disconnected. Staging remains65ccfa9c; no new upgrade occurred. The backup at18:56:40UTC and before-values are retained.

Before inviting owner UAT, complete and record:

- [ ] Final source SHA/tree and successful qualification build: **pending**.
- [ ] Final English/Arabic × Odoo Light/Dark × six-width visual review: **pending**.
- [ ] Durable final screenshot archive, manifest and checksum: **pending**.
- [ ] Exact staging revision, verified backup and dashboard-only upgrade build: **pending**.
- [ ] Staging journeys and unchanged critical displayed values: **pending**.
- [ ] Independent review with no unresolved Critical/High issues and explicit RTL clipping disposition: **pending**.
- [ ] Restore agreed user language/theme after testing: **pending**.

Owner acceptance remains separate. Keep PR #214 draft; main and production remain
prohibited. See [current implementation status](implementation-status.md) and
[qualification history](change-20260921-visual-polish.md).

## Previous enhancement UAT baseline — historical


Use the authorized **Adams For Men staging database**, company **Adams For Men**,
currency **EGP**. Production and main are excluded. The agreed scope is recorded
in [owner decisions](owner-decisions.md). See [implementation status](implementation-status.md)
for the exact tested/deployed source and evidence boundaries.

Current enhancement candidate: **a88e9628**, core **19.0.1.4.1**, finance **19.0.1.4.0**.
The candidate is **ready for owner UAT**. Build **38409118** passed **65 Odoo tests,
zero failures/errors**; **37 controller checks** pass. Staging **65ccfa9c**, upgrade
build **38409525**, contains the qualified addon trees. All 22 displayed values
matched the initial upgrade snapshot; HR was then disabled through Settings.
Fresh pre-upgrade backup: **2026-09-21 16:35:54 UTC**, staging 06a5274b.
Owner UAT signoff is not implied by automated or technical checks.

Technical evidence: initial 22-value comparison unchanged; final 21-value comparison
unchanged after hiding HR. The filtered Inventory/CRM scroll boundary now passes.
The unchecked boxes below are reserved for the owner’s acceptance.

## Start UAT

Open [Executive Dashboard in staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004)
or use the app menu. Use existing authorized Odoo roles.
Select the company, period and Balance as of date, then Apply filters. Check the
applied dates before comparing any result. Returning through the dashboard
breadcrumb restores the scope and reloads current authorized values.

| Journey | Acceptance check |
|---|---|
| Profitability | Revenue, gross profit, operating expenses, net profit and ratios match the same posted-only native reports. Native warnings remain visible. |
| Cash | Compare Bank and cash to Balance Sheet, account balances to General Ledger and opening/movement/closing to Cash Flow Statement. Standard forecast keeps its native meaning. |
| AR and AP | Compare totals, overdue and signed aging buckets at the selected cutoff. Follow native report and partner/document routes. Credits and unapplied payments retain native aging treatment. |
| Supplier windows | Check overdue, due today, days 1–7 and days 1–30. The 30-day window includes the first seven days. Drill-down and export must identify and retain the same bill-installment window. |
| Budgets | Use existing applicable native budgets only. This staging company has none configured; expect No target configured. |
| Sales | Compare invoiced sales, confirmed orders and quotations separately. Check salesperson/customer breakdowns, recent documents, native analysis and export. |
| Product ranking | Compare Top 5/10 net invoiced product values to Invoice Analysis for the same company/date range. Check Quantity sold by one unit; credit notes reduce quantities. Open a product and Full ranking. |
| Section settings | As administrator disable HR, Save and reload: HR disappears from both navigation surfaces, body and summary. Re-enable and verify it returns. Verify choices are company-specific; all-disabled has a clear empty state. |
| Scroll tracking | Scroll down and up; the active category follows the visible section beneath the sticky tabs. Click a short final section and verify it stays selected. Repeat after resizing and in Arabic. |
| Fulfillment | Inspect ordered, delivered and remaining quantities by product/UoM. No mixed-unit headline, valued backlog or custom on-time percentage is required. |
| Inventory | Filter stock by warehouse, category, product and date. Compare each product/location row to the stock report; test independent zero/negative hiding, numbered pages, source data and return navigation. Historical dates omit current availability/forecast columns. |
| Purchasing | Inspect awaiting-approval and native late-receipt worklists. Open a record and return. Viewing does not approve, receive or bill an order. |
| CRM and HR | Use existing native opportunity and workforce sources. Empty results remain explicit. Time Off is not installed in this staging database, so leave hours correctly show App not installed. |
| Access | Dashboard membership must not grant native accounting, HR, stock or export rights. Check each intended UAT user's existing permissions before granting access. |
| Search | Find posted invoices/bills and confirmed orders/draft-sent quotations by reference or party. Validate company/period, unavailable types, paging and the original native form. |
| Summary exports | Download CSV and use Print summary. Verify actual native values, units, dates, blank unavailable values, warning labels and native export rights. |
| Preferences | Save quotations and commercial margin, change both selectors, restore, and verify both selections and dates return with freshly loaded data. Native Odoo theme/language control appearance. |
| UI | Compare the supplied reference layout in English and Arabic, including mobile navigation, long mixed-script names, exact source values, negative signs, focus and table scrolling. |

## Record owner acceptance

Record the tester, native role, company, applied dates and language/theme for each
journey. For a defect, retain the exact action, expected native report result,
observed result and screenshot; do not edit accounting records to force a match.
Use the source-bound evidence in implementation-status.md as the engineering
baseline. A UAT-ready staging candidate still requires finance/owner signoff.

| Acceptance | Tester / date / result |
|---|---|
| Finance source and cutoff agreement | Pending owner UAT |
| Sales and operational journeys | Pending owner UAT |
| English/Arabic visual fit to supplied reference | Pending owner UAT |
| Intended users and native permissions | Pending owner UAT |
| Production release decision | Not authorized |

## Staging accounting observations

Native reports warn that unposted journal entries exist. They are excluded under
the owner's posted-only policy. A successful dashboard/native comparison is not
approval of the accounting data, closing process or unusual balances. Business
users should investigate those records in native Odoo during UAT; development
does not adjust financial records to make dashboard figures look conventional.

## Deployment and evidence boundaries

Only `adams_executive_dashboard` and `adams_dashboard_finance` are deployed to
staging. Disposable test addons are excluded. Existing staging code is preserved.
The pre-install staging backup is dated **2026-09-20 18:04:30 UTC**. Installation
preserved the recorded hashes of 1,047 accounting documents, six users' existing
company/group permissions and 250 native report expressions. Subsequent setup
added dashboard membership to the existing administrator and approved 13 mappings
against the inspected native definitions; it added no native financial rights.

Previous qualified addon source was `adbe2997718aad8ad57c341b071415a910f7a8f4`; historical staging
commit is `29121a55098acefcc9d55031c2dd0bb68942d4c9`. That historical native run
passed 58 tests and the final staging update preserves accounting/access/report/
mapping hashes. The staging environment expires on **19 October 2026**.

The private harness pin and unchanged qualification are reused. Native automated
checks, retained screenshots, current-company comparisons and owner acceptance
are distinct. Independent engineering review and owner UAT signoff must be recorded
before calling this an approved release. No main merge or production deployment
is authorized by this checklist.

## Current-design enhancement owner acceptance (technical checks passed; owner signoff pending)

- [ ] Existing layout retained; English/Arabic and Odoo light/dark reflow without clipping.
- [ ] Invoice and order salesperson rankings use their correct periods and source records.
- [ ] Top 5/10 works for all rankings; quantity ranking isolates the selected product unit and deducts refunds.
- [ ] Warehouse/category/product filters and historical date agree with the stock report for each location.
- [ ] Parent locations do not include child quantities twice; zero/negative hiding works independently.
- [ ] Stock page numbers, drilldown and return preserve the applied location/date scope.
- [ ] Archived bank/cash accounts are absent; opening + movement = closing in the Cash Flow Statement.
- [ ] No confusing activity subsection or technical “native” wording remains in dashboard guidance.
- [ ] Every paginated widget has numbered pages; unavailable totals are not invented.
- [ ] Settings save/reload hides HR; company visibility remains separate from personal ordering/collapse.
- [ ] Manual scroll and clicked left category remain synchronized, including short bottom sections.
- [ ] Draft filter notice, per-section retry and last-updated text are clear and usable.
