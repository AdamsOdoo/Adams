# Executive Dashboard — user and administrator guide

This guide describes the scope approved in [owner-decisions.md](owner-decisions.md).
Company configuration and deployment qualification are recorded in the implementation status.
The dashboard uses Odoo reports; a successful calculation is not confirmation
that the accounts are complete or the period is closed.

## Open and filter

For the authorized UAT, use [Adams For Men staging](https://adamsmen-staging-38326320.dev.odoo.com/odoo/action-1004).
This is the existing neutralized business database, with EGP company currency.
Production is not part of this handoff.

Open **Executive Dashboard** from Odoo's app menu. Select one authorized company,
period start/end and balance cutoff, then **Apply filters**. Changing the input fields
alone does not change the displayed scope. The applied dates are shown beneath the
filters. Period cards and balance cards have different date meanings.

Use the sidebar or the enabled department tabs. Finance and Sales start expanded;
supporting departments start compact. Expansion preferences are remembered per
user. On mobile, the menu receives focus when opened. Close it with × or Escape.
Dates and mixed-script account codes retain their order in Arabic.

Supplier-payment drilldowns identify their window and balance cutoff in the
action title. XLSX filters and PDF headings retain that same scope.
The complete Aged Payable report remains separately available.

## Theme and saved views

The dashboard follows **Odoo → My Preferences → Theme** (System, Light or Dark).
There is no separate dashboard theme switch. In Arabic, the workspace and drawers
follow the right-to-left direction while dates and chart axes retain their order.

**Save view** remembers the applied company, dates, section expansion, Sales list
and ranking measure in this browser for the current user. Saved lists reopen at
the first page and reload current authorized records. **Restore view** revalidates the company and reloads
current values. **Reset view** returns to the default reporting dates and layout;
it does not delete the saved view or modify business records.

Finance shortcuts jump to Profitability, Liquidity, Working capital and Financial
position. The Management attention strip opens existing payment/collection
reports and purchasing worklists. It is not a custom alert scoring system. Use
**Show details** to expand it on mobile.

Full rankings open in a side drawer. Escape closes drawers; source controls remain
separate from the card's report link. Chart bars and exact-value table cells open
the corresponding monthly report. Sales list/ranking controls also support
Left/Right and Home/End keyboard navigation.

## Investigate a value

Use **Source & definition** for the exact value, source, scope and retrieval
information. Large headlines can be abbreviated; the source drawer retains precision.
Use a card or supported row's native-report control to investigate in Odoo. Return
with the **Executive Dashboard** breadcrumb to restore applied filters and selected
lists while fetching fresh values. transactional actions remain in Odoo.

Profitability uses approved P&L/ratio definitions. Cash movement uses the Cash Flow Statement; cash account balances use the General Ledger. The
standard short-term forecast is not a daily cash plan. Aging uses the selected
historical cutoff and maturity buckets, not today's invoice residuals.

Supplier payment cards show outstanding posted bill installments at the balance
cutoff: overdue, due today, days 1–7 and days 1–30. The 30-day window includes
the first seven days. Standalone credits and unapplied payments remain in aging; the cards do not invent cross-bill netting. Open each card for the same
fixed due-date window in Aged Payable. Missing budgets show **No target
configured**; report errors and restricted access remain distinct states.

Search bank/cash accounts by name or code. The matching count covers the complete
authorized directory; pages contain at most 25 rows. Archived accounts are hidden; active zero-balance
accounts remain discoverable. The visible page does not determine the headline.

Sales invoice amounts, confirmed orders and quotations are separate measures.
Commercial margin uses the installed current-cost measure; it is not P&L
gross profit. Rankings preserve negative and unassigned values. delivery
quantities are shown by product and unit; quantities are not combined across units.
Inventory distinguishes current figures from historical cutoff figures. HR access
requires HR rights and does not expose payroll.

## Export and availability

Open full analysis for grouped CSV export, or export through the report.
The user's Odoo export permission still applies. CSV scope metadata includes the
selected dates and company, source and retrieval time. Large datasets may
require the report's full export route.

| Display | Meaning / action |
|---|---|
| Access restricted | Ask the administrator to review the user's existing permissions. Dashboard membership grants no accounting/HR access. |
| App not installed | The corresponding app is unavailable. |
| Not configured | A required definition or approval is missing or has changed. No estimated substitute is calculated. |
| No matching records | No authorized records match this scope. |
| Unsupported report scope | The selected report/options cannot be represented by this adapter. Review the configuration. |
| Report unavailable | Retry, then report the scope and error time to the administrator. |
| Undefined ratio | The denominator is zero; this is not a zero-percent result. |

## Product ranking and section visibility

The Sales **Sold product ranking** widget shows the top five or ten products by net
invoiced sales value, excluding tax. It uses posted customer invoices less credit
notes in the applied company and invoice-date period. Negative values keep their
sign; choose Quantity sold to compare products within one selected unit. Select a product for
its Invoice Analysis, or **Full ranking** for the complete grouped analysis.

An administrator can choose **Dashboard Settings** in the sidebar, or open
**Settings → Executive Dashboard**. Enable only the sections needed for the current
company, then **Save** and reload the dashboard. For example, clear **Human
Resources** to hide HR from the sidebar, department tabs, content and summaries.
Each company has its own choices; all six sections initially remain enabled.
Visibility does not change application permissions. With all sections off,
the dashboard displays an explicit empty-workspace message.

The selected sidebar category follows the visible section when you scroll.
Selecting a category expands it and aligns its heading below the sticky navigation;
short sections near the page end retain the category you selected. Manual scrolling
resumes automatic tracking.

### ترتيب المنتجات وإظهار الأقسام

تعرض المبيعات أفضل خمسة منتجات حسب صافي قيمة المبيعات المفوترة دون الضريبة،
بعد خصم الإشعارات الدائنة، للشركة وفترة تاريخ الفاتورة المطبقتين. افتح المنتج
للوصول إلى تحليل الفواتير الأصلي، أو اختر الترتيب الكامل لعرض التحليل المجمع.

يمكن للمسؤول فتح **إعدادات لوحة المعلومات** واختيار الأقسام الظاهرة للشركة الحالية.
ألغِ تحديد **الموارد البشرية** لإخفائها، ثم احفظ وأعد تحميل اللوحة. لا تغير هذه
الاختيارات صلاحيات التطبيقات الأصلية. يتبع القسم المحدد في القائمة موضع التمرير.

## Administrator setup

Install `adams_executive_dashboard`. For licensed financial reports install
`adams_dashboard_finance` and activate full Accounting; Invoicing alone does
not enable full report access. Optional Sales, Purchase, Inventory, CRM and
Time Off apps enable their respective sources. Grant Executive Dashboard membership
plus the appropriate existing rights. Do not install the disposable
`adams_dashboard_native_tests` addon in the customer's database.

After the owner selects reporting policies, an accounting manager configures
**Accounting → Configuration → Dashboard Financial Definitions**. Select the company,
metric, installed report variant, expression and any denominator/detail/budget,
and document the meaning before approval. Definition changes invalidate approval.
Do not approve test/demo definitions as customer policy.

For deployment, pin the tested commit and database build, back up through the normal
Odoo deployment process, update both installed dashboard modules, and verify existing
mappings, rights, values and assets. The qualified upgrade path and limitations
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

تتبع ألوان اللوحة تفضيل المظهر في Odoo: النظام أو الفاتح أو الداكن.
يحفظ **حفظ العرض** الشركة والتواريخ والأقسام وقائمة المبيعات ومقياس ترتيب
مندوبي المبيعات لهذا المستخدم في المتصفح. يعيد **استعادة العرض** تحميل البيانات
الحالية المصرح بها من الصفحة الأولى، ولا يحفظ الأرصدة أو السجلات.
يعيد **إعادة تعيين العرض** التواريخ والتخطيط الافتراضيين دون حذف العرض المحفوظ.


## Workspace search and executive exports

Use the search field above the filters to find an invoice, vendor bill, confirmed
sales order or quotation by document reference or customer/vendor name. Enter
at least two characters. The selected company and applied period remain in force.
Invoices and bills include posted documents and credit notes only; orders are
confirmed; quotations include draft/sent records. Search does not treat the balance
cutoff as an invoice-date filter. Each page contains up to 25 records per document
type; select a type to narrow the result. access restrictions remain visible.
Opening a result uses the original Odoo form and does not change the record.
Press `/` outside editable fields to focus search; close its drawer or press Escape
to return to the workspace.

**Export summary** downloads a UTF-8 CSV of current authorized metric
results. It includes the company, period, balance cutoff, status, unit, source, retrieval time and scope fingerprint where the adapter supplies one. The four supplier-window rows retain their labelled window, source and balance cutoff; their fingerprint cell is blank. Blank unavailable values are not zero.
The Odoo export permission is required. Results are evaluated afresh, so
concurrent accounting changes may produce newer values than an older screen.
**Print summary** uses those same server-generated values in a print-friendly
summary. Review the preview, then choose Print / Save PDF to open the browser
print dialog. Close preview or press Escape to return.
The summary follows the user language. Currency values use company precision; counts remain whole numbers. Open a report for its full supporting rows and report-specific exports.

### البحث والتصدير والطباعة

استخدم حقل البحث أعلى عوامل التصفية للبحث برقم المستند أو اسم العميل أو المورد،
بحد أدنى حرفين. يلتزم البحث بالشركة والفترة المطبقتين ويعرض الفواتير المرحلة
وأوامر البيع المؤكدة وعروض الأسعار المسودة والمرسلة وفق صلاحيات المستخدم.
تعرض كل صفحة حتى 25 سجلاً لكل نوع مستند. اختر نوعاً محدداً لتضييق النتائج.
فتح النتيجة يعرض نموذج أودو الأصلي ولا يعدل المستند.

يُنزّل **تصدير الملخص** ملف CSV بالقيم الأصلية المحدثة، مع الشركة والتواريخ والوحدات
وحالة التوفر والمصدر ووقت الجلب. القيمة غير المتاحة ليست صفراً. تتطلب العملية
صلاحية التصدير الأصلية في أودو. يستخدم **طباعة الملخص** القيم نفسها في معاينة واضحة. اختر طباعة / حفظ PDF لفتح نافذة الطباعة في
المتصفح، أو أغلق المعاينة للعودة. للتفاصيل الكاملة استخدم التقرير الأصلي.

## Current UI enhancements — deployment qualification pending

Use **Top 5 / Top 10** for the Sales rankings. Salespeople have separate invoice and
confirmed-order widgets; customers use net invoices. Products can be ranked by
net invoiced value or **Quantity sold**. Quantity comparisons use one selected unit;
credit notes reduce the quantity.

In Inventory, choose **Explore current stock**, then select a warehouse, category,
product name/reference and optional **Inventory at date**. Choose **Update stock**.
A blank date shows current stock; a date shows stock at that day's end in your
Odoo timezone. Each row is one product and location. **Hide zero quantities** and
**Hide negative quantities** work independently at that location. **View stock**
opens matching source data. Current incoming/outgoing/forecast columns are omitted
for historical dates. Product-wide stock value is not repeated per location.

Cash shows opening balance, net movement and closing balance for the selected
period. The account list contains active bank/cash accounts. Open a balance or the
Cash Flow Statement to inspect supporting entries.

Use numbered pages alongside Previous/Next. Where a report does not provide a
last-page count, the dashboard offers already reached pages and the next available
page. **Arrange sections**, **Expand all** and **Collapse all** are personal browser
preferences; **Dashboard Settings** controls section visibility for the company.
A notice reminds you to apply edited date/company filters. **Retry section** reloads
a failed section without clearing successful sections.

### تحسينات الواجهة الحالية — التحقق من النشر قيد التنفيذ

اختر أفضل ٥ أو ١٠ في ترتيب المبيعات. تظهر قوائم منفصلة لمندوبي المبيعات حسب
الفواتير وأوامر البيع، وللعملاء والمنتجات. يمكن ترتيب المنتجات حسب القيمة أو
الكمية؛ تُقارن الكميات بوحدة واحدة وتُخصم الإشعارات الدائنة.

في المخزون اختر المستودع وفئة المنتج والاسم أو المرجع، وأدخل تاريخاً اختيارياً،
ثم اختر **تحديث المخزون**. اترك التاريخ فارغاً للمخزون الحالي. يعرض كل صف منتجاً
وموقعاً، وتعمل خيارات إخفاء الكميات الصفرية والسالبة بشكل مستقل لكل موقع.
اختر **عرض المخزون** لمراجعة البيانات المصدرية المطابقة.

تعرض النقدية الرصيد الافتتاحي وصافي الحركة والرصيد الختامي، وتُخفي قائمة الحسابات
الحسابات المؤرشفة. استخدم أرقام الصفحات للتنقل، و**ترتيب الأقسام** لحفظ ترتيبك
في هذا المتصفح. إعدادات إظهار الأقسام تخص الشركة؛ الترتيب والطي تفضيلات شخصية.
