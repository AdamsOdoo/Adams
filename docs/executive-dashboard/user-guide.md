# Executive Dashboard — user and administrator guide

This guide describes the scope approved in [owner-decisions.md](owner-decisions.md).
Company configuration and deployment qualification are recorded in the implementation status.
The dashboard uses native Odoo reports; a successful calculation is not confirmation
that the accounts are complete or the period is closed.

## Open and filter

For the authorized UAT, use [Adams For Men staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004).
This is the existing neutralized business database, with EGP company currency.
Production is not part of this handoff.

Open **Executive Dashboard** from Odoo's app menu. Select one authorized company,
period start/end and balance cutoff, then **Apply filters**. Changing the input fields
alone does not change the displayed scope. The applied dates are shown beneath the
filters. Period cards and balance cards have different date meanings.

Use the sidebar or the six department tabs. Finance and Sales start expanded;
supporting departments start compact. Expansion preferences are remembered per
user. On mobile, the menu receives focus when opened. Close it with × or Escape.
Dates and mixed-script account codes retain their order in Arabic.

Supplier-payment drilldowns identify their window and balance cutoff in the
native action title. Native XLSX filters and PDF headings retain that same scope.
The complete Aged Payable report remains separately available.

## Investigate a value

Use **Source & definition** for the exact value, native source, scope and retrieval
information. Large headlines can be abbreviated; the source drawer retains precision.
Use a card or supported row's native-report control to investigate in Odoo. Return
with the **Executive Dashboard** breadcrumb to restore applied filters and selected
lists while fetching fresh values. Native transactional actions remain in Odoo.

Profitability uses approved P&L/ratio definitions. Cash movement uses native CFS
rows; cash account balances use native GL. Their compositions can differ. The
standard short-term forecast is not a daily cash plan. Aging uses the selected
historical cutoff and native maturity buckets, not today's invoice residuals.

Supplier payment cards show outstanding posted bill installments at the balance
cutoff: overdue, due today, days 1–7 and days 1–30. The 30-day window includes
the first seven days. Standalone credits and unapplied payments remain in native
aging; the cards do not invent cross-bill netting. Open each card for the same
fixed due-date window in native Aged Payable. Missing budgets show **No target
configured**; report errors and restricted access remain distinct states.

Search bank/cash accounts by name or code. The matching count covers the complete
authorized directory; pages contain at most 25 rows. Archived and zero-balance
accounts remain discoverable. The visible page does not determine the headline.

Sales invoice amounts, confirmed orders and quotations are separate measures.
Commercial margin uses the installed native current-cost measure; it is not P&L
gross profit. Rankings preserve negative and unassigned values. Native delivery
quantities are shown by product and unit; quantities are not combined across units.
Inventory distinguishes current figures from historical cutoff figures. HR access
requires native HR rights and does not expose payroll.

## Export and availability

Open full analysis for grouped CSV export, or export through the native report.
The user's Odoo export permission still applies. CSV scope metadata includes the
selected dates and company, source and retrieval time. Large native datasets may
require the native report's full export route.

| Display | Meaning / action |
|---|---|
| Access restricted | Ask the administrator to review the user's existing native permissions. Dashboard membership grants no accounting/HR access. |
| App not installed | The corresponding native app is unavailable. |
| Not configured | A required definition or approval is missing or has changed. No estimated substitute is calculated. |
| No matching records | No authorized records match this scope. |
| Unsupported report scope | The selected native report/options cannot be represented by this adapter. Review the configuration. |
| Report unavailable | Retry, then report the scope and error time to the administrator. |
| Undefined ratio | The native denominator is zero; this is not a zero-percent result. |

## Administrator setup

Install `adams_executive_dashboard`. For licensed financial reports install
`adams_dashboard_finance` and activate full native Accounting; Invoicing alone does
not enable full report access. Optional native Sales, Purchase, Inventory, CRM and
Time Off apps enable their respective sources. Grant Executive Dashboard membership
plus the appropriate existing native rights. Do not install the disposable
`adams_dashboard_native_tests` addon in the customer's database.

After the owner selects reporting policies, an accounting manager configures
**Accounting → Configuration → Dashboard Financial Definitions**. Select the company,
metric, installed report variant, expression and any native denominator/detail/budget,
and document the meaning before approval. Definition changes invalidate approval.
Do not approve test/demo definitions as customer policy.

For deployment, pin the tested commit and database build, back up through the normal
Odoo deployment process, update both installed dashboard modules, and verify existing
mappings, rights, native values and assets. The qualified upgrade path and limitations
are recorded separately in the evidence dossier. A development test is not permission
to deploy to production.

## بدء الاستخدام بالعربية

افتح **لوحة الإدارة التنفيذية**، واختر الشركة المصرح بها وفترة التقرير وتاريخ
قطع الأرصدة، ثم طبّق المرشحات. تعديل الحقول وحده لا يغيّر نطاق القيم المعروضة.
استخدم **المصدر والتعريف** لعرض القيمة الدقيقة ومصدرها، وافتح التقرير القياسي
للتحقق من التفاصيل. ارجع من مسار التنقل إلى اللوحة لاستعادة الاختيارات وتحديث البيانات.

تظل صلاحيات المحاسبة والمبيعات والموارد البشرية والتصدير القياسية سارية.
«غير مهيأ» تعني أن التعريف أو اعتماده غير متاح؛ ولا تعني رصيداً صفرياً.
تعرض أعمار الديون أرصدة تاريخ القطع، وتبقى التوقعات النقدية القياسية منفصلة عن
الخطة النقدية اليومية. لا تعتمد تعريفات تجريبية نيابةً عن مالك الشركة.
