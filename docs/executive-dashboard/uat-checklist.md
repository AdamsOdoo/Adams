# Adams For Men dashboard — staging UAT

## Current continuation — blocked, not ready for acceptance

Use [implementation status](implementation-status.md) for the current source/build identity. Application `638af7eabd0186612856b7df8d9b59fd0c3d7506` (module versions19.0.1.7.0) has not reached a usable verified development build: build38534410 reported an Odoo.sh Platform error, following the same failure on38533796. Staging still has19.0.1.6.0 and has not received this iteration. Historical checked boxes below do not qualify the new candidate.

The owner decisions are settled for this delivery: UI07 removes comparable-period claims, UI08 uses standard Bank/Cash journals with signed unique-account values, and UI20 remains deferred with truthful Procurement worklists. Do not request those decisions again.

Short owner guide, **to use after the development visual gate and staging deployment pass**:

1. Confirm company/logo, period and balance cutoff, then compare Finance to the paired approved reference. Open the revenue value, return, expand the chart table and open a month. Check the matching scope and retained dashboard state.
2. In Inventory, apply warehouse/category/search, move to page2, open a product/location source and return. Narrow the filters and verify page/total recovery. Test no results and Clear.
3. Walk Sales rankings/recent records; Procurement approval/late worklists; CRM opportunity rows. Verify each destination and retained filters.
4. In HR, exercise Overview, Attendance, Time off, Shifts (Week/List) and Employees/work profile. Missing applications or restricted sources must stay honest. Do not install applications or widen permissions for review.
5. Check the representative desktop/narrow, light/dark and Arabic/RTL pairs. Report clipping, misplaced controls or missing content as unresolved defects. Test counts alone are insufficient.

## Historical candidate information (superseded)

## Final implementation candidate and staged testing

**STAGING AVAILABLE FOR OWNER HANDS-ON TESTING — NOT YET READY FOR FORMAL OWNER UAT.** Final published application feature **`b9461b76f3b1a1e1085fda87d55f6ef66ecca9b9`** has dashboard addon trees `adams_executive_dashboard` **`78710c2fc2334379aedc44939968d9a4e818f8ab`** and `adams_dashboard_finance` **`a01fdad4fcc866e02093c3c115d4c71432902313`**. Development build **38514095** passed **120/120 native post-tests** (403.75s, 118,807 queries), **65/65 focused frontend tests**, and its native browser matrix completed **28 English/Arabic × light/dark × seven-viewport cases**, retaining **532 actual Odoo screenshots and four actual dashboard PDFs**. The native PDF/browser output was captured; screenshot count is not by itself a full pixel parity sign-off.

The exact staged application is **`28b37d90d77571383b37e70212681e9730d5cf40`**, running build **38326320** with matching two addon trees and installed versions **19.0.1.5.0**. The final dashboard-only upgrade succeeded at **2026-09-23 06:16:25 UTC** after the manual **05:34:26 UTC** backup. Its translation-and-test-only change followed backend candidate `efcf40aa` / staging `44fdbe43`; the underlying calculation code stayed the same. The earlier staged **34/34 independent read-only probes** therefore support that unchanged backend, while the final published/deployed tree identities and browser/Arabic behavior are separately qualified on the final source. Do not label the old probe archive as a 34-check rerun on `28b37d`.

| Evidence boundary | Observed result and limit |
|---|---|
| Exact source and native/browser tests | Feature `b9461b76` / build38514095 120/120 native pass; 65/65 frontend pass; 28 bilingual/theme/viewport native browser cases, 532 PNGs/four PDFs captured. Staging `28b37d90`/build38326320 clean matching addon trees and both installed versions19.0.1.5.0 after a backed-up dashboard-only upgrade. |
| Independent report/data checks | Prior identical backend candidate `44fdbe43` passed **34/34 source-guarded read-only probes**: Finance9, Procurement/CRM5, Inventory/HR5, preservation/performance12, stock prefilter3. They reconcile selected real measures and preservation, not every record, permission, or the later Arabic-only code change. The native Aged Receivable signed bridge to dashboard totals and actual PDF/XLSX were inspected. |
| Live final dashboard journeys | All six departments and five HR tabs were navigated on staged final source. Real Partner Ledger and other native source actions, scope-labelled exports and XLSX/PDF, desktop Inventory Category plus functional `Source data` column, native valuation/forecast links, and authorized employee work-profile source were exercised. The earlier intercepted Partner Ledger link, Inventory Category omission and HR Owl crash are closed on this source. |
| HR capability limit | Attendance, Time Off and Planning are **uninstalled** on staging; those tabs show distinct missing-app states while Overview/Employees use permitted real data. Native fixtures cover populated optional-app records and source-specific rules. A live installed-app workflow cannot be claimed for this staging database. |
| Retained backend performance | On identical backend source and matched three-repeat ORM context, current stock page one **10.818→1.116s / 4,391→694 queries**, page two **11.205→1.068s / 4,404→672**, historical **21.745→1.918s / 4,379→662**; cash directory **0.110→0.103s / 84→84**. Cache invalidated between ORM repeats, DB buffers uncontrolled. Exact final staged RPC sample: Inventory **0.772s / 716 queries median (n=3)** and bootstrap **0.009s / 4 queries median (n=6)**. RPC/backend timing does not imply browser paint/network latency. Private raw final probe/browser records are indexed separately. |
| Remaining business and staging limits | UI07 comparable-period definition, UI08 bank-versus-cash classification and UI20 prototype monetary amounts versus approved native order-count worklists need explicit owner disposition. Only one company is authorized on this staging account, so live company-switch isolation is covered by native fixtures rather than a fabricated second staging company. Final owner visual/financial acceptance and production approval remain separate. |

Selected approved six-department/five-HR-tab HTML SHA-256: `36ec95831f3f1e82e0709594d5c177938e3b3805ccd763b1e59c13933b2d7f4a`. Private customer values, workforce records, Enterprise code and raw screenshots stay outside this repository; the evidence index binds them to the exact source and build. PR #214 remains draft. Main and production remain untouched.

The owner can start hands-on testing at [Adams For Men staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004). Treat the three source-definition decisions and the limits above as open; do not record formal owner acceptance or production release from a technical test pass.

Completed technical checks and remaining formal-acceptance gates:

- [x] Verify final feature `b9461b76`, exact core/finance addon trees, development build38514095 (native120/120 and frontend65/65) and stage `28b37d90`/build38326320, both installed versions19.0.1.5.0.
- [x] Preserve the 28 actual seven-viewport × bilingual/theme native browser cases (532 PNGs/four dashboard PDFs) and **15 paired HTML/Odoo screenshots** covering six departments, five HR views/profile and four Arabic/dark comparisons. Screenshot retention does not substitute for owner visual acceptance of every interaction.
- [x] Verify the dedicated desktop Inventory Category column, functional native Source data link, native valuation/forecast routes and signed real stock quantities on exact staging.
- [x] Reconcile 34 backend-identical read-only checks (9 Finance, 5 workspace, 5 Stock/HR, 12 preservation/performance, 3 prefilter), matching signs in inspected native Aged Receivable XLSX/PDF and actual staged CSV.
- [x] Retain three-repeat stock ORM/query evidence and final staged Inventory/Bootstrap RPC samples with dataset and cache caveats; do not present backend time as browser paint time.
- [x] Observe real Partner Ledger, six departments, all five HR tabs, permitted employee profile source, missing-app states and actual report/export actions on the final staged source.
- [x] Verify the fresh 05:34:26 UTC backup, final dashboard-only 06:16:25 UTC upgrade, exact running addon identities/versions and optional apps still uninstalled.
- [ ] Owner reviews all 15 pairs, significant menus/drawers/print, physical scrolling/zoom and the appearance/language/viewports against the approved HTML; report any material visual difference.
- [ ] Owner reviews the remaining business metrics, source-role/denied paths, rapid/invalid/retry and saved-return journeys in the staged scope. The native fixture suite covers role and company cases that one-company staging cannot exercise live.
- [ ] Resolve UI07 comparable-period definition, UI08 bank/cash classification and UI20 count-versus-amount disposition before **formal** owner UAT sign-off.
- [ ] Confirm test users' appearance/language restoration and record owner acceptance separately from PR merge or production release.

Owner hands-on walkthrough **available now on the staged candidate**; record findings without treating this walkthrough as formal acceptance:

1. Open the staging entry above using the authorized owner account. Confirm the release/build recorded in the final handoff, active company name/logo, dates and balance cutoff. If another authorized company exists, switch using Odoo's host company menu. The dashboard is single-active-company, not a consolidated total; the current staging account has only one authorized company.
2. **Finance:** compare accounting revenue, profit, balances and cash with their approved standard reports at identical company/period/cutoff. Check valid negative signs and report warnings. Open full signed overdue receivables/payables and individual aging buckets. Supplier-bill due-today/7-day/30-day schedules are separate worklists and must not be interpreted as all overdue payables. Review the bank/cash split limitation explicitly; do not infer a split from a combined total.
3. **Sales:** exercise invoice revenue/margin and sales-order rankings, Top 5/10, product value/quantity with the correct UoM, customer rankings and recent orders/quotations/posted invoices and credit notes. Open a row and return. For fulfillment, verify ordered/delivered/remaining native quantities and product/UoM source filters; preserve legitimate negative remaining quantities.
4. **Inventory:** search/filter warehouse/category, apply changes, sort and page; then compare an exact product/location row with its standard source. Reserved is the **current native quant reservation at that exact location in the product's stock unit**. Kit component reservations are not converted into kit quantities. Historical stock does not present current reservations as historical. Location quantity, warehouse/company valuation, reservations, forecast, stock history and replenishment have distinct source meanings; verify labels and scopes.
5. **Procurement and CRM:** inspect period purchase/opportunity measures and source rows. Approval and late-receipt counts are current order worklists, not period financial totals. Compare weighted and unweighted opportunity values with their labelled native definitions; open source records and return with selections preserved.
6. **HR:** use Overview, Attendance, Time off, Shifts and Employees with its independent applied period. Current workforce/open-session snapshots remain current even when viewing a past period. No-check-in-today is the authorized stored employee snapshot, **not an absence or lateness decision**. Open sessions have no invented completed duration. Time off uses overlapping requests and full native days/hours; the signed leave report has separate semantics. Shifts retain draft/published and assigned/unassigned scope, native allocated hours and overnight continuations without duplicate totals. Profiles show permitted work information; edits/approvals use standard applications. On this staging database, Attendances, Time Off and Planning are currently absent: verify clear missing-app states and usable authorized employee information. Do not install apps merely to make a dashboard card populate.
7. **Company identity:** use standard Company settings for name/logo. If authorized, refresh after a controlled settings change and switch between authorized companies. Confirm identity, values, source drawers and exports agree; previous-company employee records must disappear. Check logo aspect ratio/fallback and restore any temporary settings.
8. **Interaction and output:** name/save a view, change filters, restore/reset, navigate to source and back, refresh and use browser Back/Forward. Test a no-result search and an invalid date without losing the last valid results. Inspect English/Arabic and both native appearances, vertical/horizontal scrolling and numbered pages. Open actual CSV and PDF/print output, checking company, scope, signs and legibility.
9. Record each issue with department, company, dates/filters, expected source, actual result and screenshot. Sign owner acceptance only after reviewing open deviations. Keep PR #214 draft until the agreed next authorization; **owner acceptance does not authorize production or main deployment**.

## Historical records (preserved; not current candidate acceptance)

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
