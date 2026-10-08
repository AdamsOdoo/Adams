# POS Sales Report

Status: in progress (review) · Size: M · Branch: `feature/pos-sales-report` · Modules (version): `adams_pos_sales_report` (19.0.1.0.0) · Last tested commit: see the evidence record

## Requirement
"A convenient report in the POS for reporting the sales that can be grouped by employee, product, session, date, etc. It should have all the necessary details and it can be printed as a report according to the visible fields, filters and grouping."

Goal: one list of POS sales lines that users filter, group and arrange on screen, and a PDF that prints exactly that view. The approved mockup is [`reference/pos-sales-report-mockup.html`](reference/pos-sales-report-mockup.html). The owner approved the proposed answers on 2026-10-08:
1. "Employee" is the cashier logged in on the till (POS employee login); orders without one show the Odoo user.
2. POS Administrators see the report and all sales; POS users have no access.
3. Margin only for POS Administrators.
4. Refunds included as negative lines, with an "Exclude refunds" filter.
5. Opens on this month, grouped by day.
6. No extra figure on the PDF.

## Acceptance criteria
- A1 Point of Sale › Reporting › Sales Report is visible to POS Administrators only; a POS user calling the print method or the report URL gets an access error → `TestPosSalesReport.test_access_pos_user_denied`, `test_menu_restricted`, `TestPosSalesReportTour.test_report_url_denied` (over HTTP)
- A2 One row per order line of paid and posted orders (draft and cancelled left out), with Date, Order, Session, Point of Sale, Employee, Customer, Product, Category, Quantity, Unit Price, Discount, Net, Tax, Total and Margin (optional columns) → `test_lines_columns`, `test_action_excludes_draft_orders`
- A3 Employee = the order's POS employee, else the order's user → `test_lines_columns`
- A4 Refunds are negative lines; filters "Exclude refunds", "Refunds only", "With discount", "Invoiced" → `test_lines_columns`, `test_filtered_nested_print` (a print with Exclude refunds)
- A5 Opens on the current month grouped by Order Date: Day → `TestPosSalesReportTour.test_print_follows_screen` (default grouping sent by the button), screenshots
- A6 Figures are Odoo's own POS analysis (`report.pos.order`): totals equal the orders' totals and taxes; lines of several currencies (companies with different currencies) are never added up: the print is refused, and one company prints in its own currency → `test_totals_match_orders`, `test_several_currencies_refused`
- A7 Print ▾ Summary / Detailed prints the current domain, grouping (any depth) and visible columns, with subtotals, grand total, the summary figures, payments per method (from the payments, so split payments are right) and taxes per tax (Sales Details computation) → `test_summary_groups`, `test_detailed_lines`, `test_payments_and_taxes`, `test_filtered_nested_print`, `test_render_html`, `TestPosSalesReportTour.test_print_follows_screen`
- A8 The server validates what the browser sends: unknown columns dropped, invalid grouping or mode refused → `test_invalid_input`
- A9 Multi-company: only the user's allowed companies → standard record rule `point_of_sale.rule_pos_order_report_multi_company` on `report.pos.order` (unchanged; the report reads as the user)
- A10 English and Arabic, right-to-left screen and PDF → `i18n/ar.po`, screenshots below
- A11 A detailed print over 5,000 lines is refused with a clear message; Summary (grouped or not) still prints, and never lists lines → `test_detailed_limit`, `test_detailed_lines`

## Design
- **Source:** the standard `report.pos.order` (Point of Sale › Reporting › Orders), one row per POS order line, amounts in company currency. The module adds columns to its SQL view, following the standard expressions: `cashier` (POS employee name, else the order user's name; shown as "Employee"), `qty` (a float; the standard `product_qty` is an integer), `price_unit`, `tax_amount` (total minus net, rounded like them), `is_refund` (quantity below zero) and `currency_id`. `pos_hr` already adds `employee_id` the same way.
- **Screen:** a list view on `report.pos.order` with `js_class="pos_sales_report_list"`, its own search view (filters and group-bys above) and an action with the domain `state in (paid, done)`. Orders Analysis (pivot/graph) is unchanged.
- **Print:** the Print ▾ button (Owl, `static/src/sales_report_list/`) sends the list's domain, `groupBy`, visible columns (`getExportableFields()`, the same rule as Export) and the filter facets as text to `report.pos.order.action_print_sales_report`. The server validates them (`_psr_options`) and returns a QWeb PDF action; the report model `report.adams_pos_sales_report.report_pos_sales` validates again (the report URL can be called directly) and builds the data as the user (`_psr_report_data`). Groups come from `formatted_read_group`, the call the list itself uses, so labels, order and group domains match the screen.
- **Summary figures:** Orders = distinct sales orders (refund orders not counted); Items sold = net quantity (refunds subtract; discount or reward product lines count as lines); Net, Tax, Total, Discounts = sums of the lines; Refunds = total of the refund lines; Avg. ticket = Total (refunds included) ÷ Orders. Discounts are line discounts only (`discount` %); a global discount or loyalty reward appears as its own product line.
- **Payments** are read from `pos.payment` for the orders in the report and converted with the order's rate. **Taxes** use `report.point_of_sale.report_saledetails._get_products_and_taxes_dict`, the Sales Details computation, up to 20,000 lines.
- **Access:** no new model or group. The menu and both entry points require `point_of_sale.group_pos_manager`. `report.pos.order` itself stays readable by POS users as in standard Odoo (Orders Analysis); this module adds no data they could not already read.

## Changes
- `addons/adams_pos_sales_report/` (new): `models/report_pos_order.py` (columns, print and report data), `models/pos_sales_report_pdf.py` (PDF values), `views/report_pos_order_views.xml` (list, search, action, menu), `report/pos_sales_report.xml` (A4 landscape paper format, report action, templates), `static/src/sales_report_list/` (Print ▾ button), `static/src/report/` (PDF styles, in the report assets so Arabic is mirrored), `i18n/ar.po`, tests and one tour.
- Depends on `point_of_sale` and `pos_hr`. Installing it installs `pos_hr` (and `hr`) if they are not installed yet; the employee login on the till stays a per-shop setting.

## Verification
- Local: `oh test adams_pos_sales_report --require …` (all fifteen tests) → PASSED, 15 tests executed (record `.odoo-harness/evidence/test-adams_pos_sales_report.json`, kept private: the evidence folder is git-ignored in this public repository).
- Static: `oh check adams_pos_sales_report` → PASSED, pylint-odoo 0 warnings.
- Screens (English and Arabic, verified by `oh shot`, demo data seeded with `screens/seed.py`): `screens/en_US/odoo-pos-sales-report.png`, `screens/ar_001/odoo-pos-sales-report.png`.
- Printout (report HTML, same template and data as the PDF; wkhtmltopdf is not installed locally): `screens/printout/sum-en.png`, `sum-ar.png` (Summary, Employee › Product), `det-en.png`, `det-ar.png` (Detailed, Employee).
- Odoo.sh development build: not run yet. Check there the real PDF in English and Arabic (page breaks, header and footer of the company layout).
- Review: independent (odoo-reviewer at f156a56; read-only not enforced in this environment). Fixed: Summary without grouping was refused above 5,000 lines (blocking; it now prints figures and totals only); amounts of several currencies were added under one currency (now refused, and the PDF uses the lines' currency); the taxes table counted lines after loading their ids (now counts first); tests added for the menu, the report URL, a filtered nested print, several currencies and the ungrouped Summary. Kept as is: grouping by Employee groups by name (two people with the same name share a group); the summary figure definitions are written above.

## Upgrade impact
New module, nothing deployed before: no migration. Uninstalling it removes the menu, report and fields; the extra joins stay in the `report.pos.order` database view (harmless) until `point_of_sale` is next updated, which recreates the view.

## User guide (English)
Point of Sale › Reporting › Sales Report (POS Administrators). The list opens on this month, grouped by day. Use the search bar to filter (period, Exclude refunds, With discount, Invoiced, a product, employee, session…) and to group (Employee, Product, Product Category, Session, Point of Sale, Customer, Order Date by day, week, month…); groups can be nested. Show or hide columns with the ⇄ icon at the end of the header. Then Print ▾: **Summary** prints the group totals, **Detailed** prints the groups with every line. The PDF shows the filters and grouping in words, the summary figures, payments per method and taxes per tax.

## دليل المستخدم (العربية)
نقطة البيع › التقارير › تقرير المبيعات (لمسؤولي نقطة البيع). تفتح القائمة على الشهر الحالي مجمّعة حسب اليوم. استخدم شريط البحث للتصفية (الفترة، استبعاد المبالغ المستردة، بها خصم، مفوتر، منتج أو موظف أو جلسة…) وللتجميع (الموظف، المنتج، فئة المنتج، الجلسة، نقطة البيع، العميل، تاريخ الطلب حسب اليوم أو الأسبوع أو الشهر…)، ويمكن تداخل المجموعات. أظهر الأعمدة أو أخفها من الأيقونة ⇄ في نهاية رأس الجدول. ثم اختر طباعة ▾: **ملخص** يطبع إجماليات المجموعات، و**تفصيلي** يطبع المجموعات مع كل سطورها. يعرض ملف PDF عوامل التصفية والتجميع بالكلمات، والأرقام الإجمالية، والمدفوعات حسب الطريقة، والضرائب حسب كل ضريبة.

## Open items and assumptions
- Assumption: depending on `pos_hr` is acceptable (decision 1 relies on the POS employee login).
- Payments are those of the orders in the report: with a filter on line details (a product, a category) the payments table covers whole orders and can exceed the lines' total. The PDF says so.
- Taxes per tax are skipped above 20,000 lines (the PDF says so); the summary figures always include the tax total.
- The printed filter text is the search bar's own wording, in the user's language.
- Grouping by Employee groups by name: two employees (or an employee and a user) with the same name share a group.
