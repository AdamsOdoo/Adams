# Executive dashboard — report-first implementation and data-assurance contract

Version 4.0 · 19 September 2026 · All-department report-first production requirements

**Companion:** `Odoo_Executive_Dashboard_UX_v2.html` is the visual/interaction reference. It contains fictional, simplified, read-only sample records. It is not an Odoo add-on, accounting engine or proof of source-data accuracy. This contract supersedes the version 2 and version 3 data-source requirements and takes precedence over all HTML fixture calculations, source labels, assumptions and screenshots for production. The HTML remains unchanged as a visual/interaction reference. No live Odoo code or integration is delivered by this document.

## 1. Scope and information architecture

| Workspace | Required contents |
|---|---|
| Finance / Profitability | Accounting revenue; gross profit/margin; net result/margin; operating expenses; signed trend; relevant target and comparability information. |
| Finance / Liquidity | Balance Sheet bank/cash balance; dynamically discovered accounts with native report balances; standard Cash Flow Statement measures; separately identified standard forecast or approved enhanced cash plan. |
| Finance / Working capital | Customer receivables, supplier payables, due-date aging, overdue totals, upcoming payments and collection/payment worklists. |
| Sales / Commercial performance | Net invoiced sales; confirmed order value; open quotations; recent orders/quotes; salesperson revenue/gross-contribution ranking; targets and top customers. |
| Sales / Fulfillment | Remaining order backlog; overdue unfulfilled commitments; on-time completion; completed-late versus open-late distinction. |
| Supporting departments | CRM stage/value overview; Inventory value/aging/shortages; Procurement commitments/approvals/late supplies; HR aggregated workforce/leave. Respect installed-module and permission boundaries. |

Keep Finance and Sales expanded by default; remember presentation preferences. Supporting sections begin compact. Mobile attention details are expandable so they do not displace all headline information. Prototype scenario controls and RTL preview controls are development aids, not production functionality.

Every meaningful number/row/chart selection needs either a scoped supporting route or an explicit explanation of its availability. Use native Odoo report/list/form actions for real investigation and transactional workflows. Do not make a KPI click execute payment, send messages or approve a transaction.

## 2. Calculation authority: standard reports across every department

**Data accuracy is the first priority.** For any metric already provided by a standard Odoo report, the dashboard must consume that report's evaluated numeric result through the actual installed report engine. It must not reproduce the result using its own journal-item sums, invoice sums, payment sums, currency conversion, recognition rules or aging logic. The native report is the calculation authority, not merely a comparator after an independent implementation.

Production lineage is: original business documents / posted Odoo records → approved native report and its calculation engine → thin, secured dashboard adapter → widget / chart / export → the same native report and supporting records. Source-data completeness and accounting correctness remain finance responsibilities; matching a report does not independently audit the books.

The finance owner approves the applicable report variant, relevant financial statement lines, accounting basis, cut-off/close policy, currency, and any necessary extension. Sales and operations approve commercial and fulfillment definitions. Developers verify correct retrieval, mapping, permissions and presentation. Agents may not invent or silently change accounting policy.

**Coverage is company-wide:** Finance, partner accounts, Sales, Purchase, Inventory, CRM and HR must use the relevant installed standard report whenever it already provides the requested measure. This is not an Accounting-only rule. Section 2.6 makes the additional report families, selection rules and technical distinctions explicit. A new chart, ranking or department panel does not justify a second calculation engine.

### 2.1 Source precedence

1. **Direct native report result:** first choice for all available financial and operational measures. Use the actual company/localization report selected and approved in the installation.
2. **Composition of native report results:** only when a required measure is not already exposed. Examples include an explicitly disclosed subtotal of non-overlapping report buckets or a ratio of two report values. Prefer an auditable Odoo report expression referencing existing expressions when supported. Register the formula; do not recreate the underlying financial values.
3. **Native operational reports and record views:** use standard Invoice Analysis, Sales Analysis, stock/valuation/forecast, Purchase, CRM and HR sources for their actual business meaning. Lists of recent orders or quotations can use native records; they are not financial statements.
4. **Approved additional logic:** only for a demonstrated gap. Inspect the installed features first, explain source inputs, formula, boundary cases, user label and supporting detail, then record approval for the business definition. Use the register in section 2.5. No duplicated accounting engine is permitted as a fallback.

Report access failure, missing licensed modules, missing mappings or unsupported options result in `restricted`, `not_installed`, `not_configured`, `unsupported_scope` or `error`—never a homemade replacement, fabricated zero or demo data. Do not describe an extension as a standard report value.

### 2.2 Verified metric-to-report mapping

These are dashboard requirements, not unverified action IDs or assertions that identical report lines exist in every localization. Discover and record the actual report, variant, line/expression, column/column-group and options in the target installation [S1, S13, S14].

| Metric / family | Authoritative production source | Adapter behavior and key boundary |
|---|---|---|
| `finance.revenue` | Approved revenue line/expression in Profit and Loss | Read native result and native comparison periods. Do not replace with invoiced sales or a new income-account sum. |
| `finance.gross_profit` | Approved P&L gross-profit result, when provided | No invoice-estimated-cost substitute. If absent, propose a native expression referencing approved revenue and cost-of-revenue lines; approve before enabling. |
| `finance.net_profit` | P&L net-result line/expression | Preserve the native result and sign. Do not subtract invented taxes, accruals or depreciation. “After tax” only if the chosen report result and completed accounts support it. |
| `finance.operating_expenses` | P&L expense result / approved child report lines | Labels and breakdown follow report categories. An absent subtotal requires a disclosed native report expression, not new SQL account classification. |
| `finance.gross_margin`, `finance.net_margin`, other ratios | Existing Executive Summary or approved financial report expressions first | Verify exact meaning and denominator before reuse. Add a formula using report results only if the required measure is absent. |
| `finance.assets`, `finance.liabilities`, `finance.equity` | Balance Sheet lines | As-of date, native currency/translation and report variant. Preserve any report adjustments. |
| `finance.cash_balance` | Approved Balance Sheet bank/cash or cash-equivalent line(s) | Headline result comes from the report. Clearly state the approved composition if cash equivalents differ from physical bank/cash. Dynamic account rows must explain that composition. |
| `finance.cash_account_balance` | Native Balance Sheet account detail or General Ledger / Trial Balance closing-balance result under aligned options | Account-level result, not the sum of only the bank journal's entries. General-journal adjustments affecting the account must not be lost. No current bank-dashboard figure used as a historical substitute. |
| `finance.cash_flow.*`, `finance.net_cash_movement` | Standard Cash Flow Statement's appropriate evaluated results | Preserve operating, investing, financing, other/unclassified, opening, movement, closing and FX/reconciliation lines as actually supplied. Do not independently classify receipts/payments or silently net away exceptions. |
| `finance.receivables`, `finance.receivables.aging` | Native Aged Receivable total, buckets and details | Use the native historical cut-off computation; not today's residual. Match installment, credit, rounding and sign rules. |
| `finance.receivables.overdue` | Native overdue subtotal where supplied; otherwise disclosed composition of native overdue buckets | Match native due-today and bucket boundaries exactly. No separate aging algorithm. Do not sum a paged partner sample to obtain the total. |
| `finance.payables`, `finance.payables.aging`, `finance.payables.overdue` | Corresponding Aged Payable results | Same principles as receivables. Purchase commitments are not posted payable debt. |
| `finance.partner_activity`, customer/vendor statements and balances | Partner Ledger with explicit receivable/payable account scope, partner grouping, period, opening-balance and reconciliation options | Use its native debit/credit/balance and movement detail where supplied. Aging and overdue KPIs still come from Aged Receivable/Payable. A partner can be both customer and vendor; do not silently net their roles or double-count commercial entities [S22]. |
| `finance.budget.*` | Existing approved financial/analytic budget reports or budget columns for matching scope | No assumed targets or straight-line proration unless approved. Match the relevant dimension and version of the budget [S18]. |
| `finance.standard_forecast` | Native Executive Summary / installed cash-planning report, if its definition matches the requested widget | Keep the native name, horizon and assumptions. The documented Executive Summary already includes a short-term cash forecast; inspect before proposing an alternative [S1]. |
| `finance.cash_plan.*` | Approved enhanced daily expected-receipt/payment plan only where standard functionality does not meet the requested definition | Separate from actual Cash Flow Statement and standard forecast; section 2.5. No duplicate feature merely to draw a different chart. |
| `sales.invoiced_sales`, `sales.salesperson_ranking`, top customers/products | Standard Invoice Analysis under approved posted customer invoice/credit-note, date, salesperson/customer and currency options | Prefer the native report model/aggregation, not parallel invoice arithmetic. Preserve an unassigned bucket and all eligible people, including historical inactive staff. Ranking is sorting/grouping a standard report result [S17]. |
| `sales.confirmed_orders`, current delivery quantities | Standard Sales Analysis measures under approved scope | Native ordered/delivered/to-deliver quantities and existing measure semantics first. Distinct order counts, not line counts. Native record lists support recent orders/quotes [S16]. |
| `sales.open_quotations` | Native quotation list/report with agreed draft/sent, validity and creation-period filters | Filtering/counting is operational selection, not custom accounting. Historical status may require history; do not infer past state from current state. |
| `sales.margin_ranking` | Existing standard commercial margin measure if approved and accurately labelled | Do not call invoice/order margin accounting P&L gross profit. Public Odoo 19 Invoice Analysis uses product `standard_price` for its margin expression; verify actual installed extensions and valuation basis [S17]. If posted COGS by salesperson is requested but not available, disclose the gap and seek approval rather than allocate costs arbitrarily. |
| `sales.backlog_value`, `sales.on_time_delivery` | Matching installed native operational report if one exists; additional logic only for the remaining definition gap | Section 2.5; no historical reconstruction from today's quantities or editable current promise alone. |
| `inventory.*` | Standard Odoo 19 valuation/stock/forecast reports | Fix the chosen operational/accounting basis, company, warehouse and ownership scope. Financial stock balances use the Balance Sheet. Do not force different report definitions to have identical totals [S7]. |
| `crm.*`, `procurement.*`, `hr.*` | Native reports and authorized record views of installed apps | Discover configured stages, people, departments, warehouses, vendors and approvals dynamically. Custom exceptions only where necessary; payroll remains separately restricted. |

### 2.3 Report adapters: retrieval and formatting, not duplicated formulas

Use the installed native report engine server-side. Public `account.report` code documents reports, variants, line codes, expressions, columns and options, but does not establish that a particular Enterprise handler/method is available in this target. Verify licensed code, dependencies and callable interfaces before implementing the adapter [S14]. Do not invent public RPC endpoints or assume private methods are remotely callable.

Each financial adapter must:

- Resolve an approved report variant and stable technical line/expression mapping. Do not match translated English labels, row numbers, screen positions, hardcoded database IDs or an assumed chart-of-accounts code range.
- Use the report's option preparation and validated company, dates, posted/draft state, accounting basis, currency, supported analytic/journal/branch filters and comparison columns. Persist the effective options for the supporting action.
- Read evaluated numeric values with the applicable expression and column identity, sign, currency and precision. Do not parse formatted “1.2M” strings or scrape HTML/PDF/XLSX. Do not mistake definitions in `account.report.line` for evaluated balances.
- Retrieve complete authoritative totals independently of unfolded-row limits, search results, pagination and hidden-zero presentation. Account for custom handlers and dynamic line IDs via verified native mechanisms.
- Reuse one calculation per report/options set for related widgets; do not run P&L independently for every card. A monthly series uses native period/comparison results or native evaluations for each explicitly defined month, not a parallel monthly aggregation.
- Attach report/variant identity, expression/column identity, options fingerprint, mapping version, scope, evaluated-at timestamp, source-cut-off and available warnings. Do not claim a source revision or change timestamp unless the target actually provides one.
- Open the same native report with the effective options and the relevant detail route. A correct report result attached to an incorrect label or filter is a defect.

If an additional financial subtotal is genuinely required, prefer an approved report expression referencing existing results. Odoo's aggregation/cross-report expressions are documented [S13]. Do not copy and fork the entire report just to expose one widget. Do not change the standard report's accounting definition to make an existing dashboard number match.

The initial implementation should avoid long-lived financial-result caches. Deduplicate/batch work within a request, and re-evaluate on refresh/filter change. Add permission-scoped bounded caching only after evidence demonstrates a need and tests prove correctness across record/configuration/permission changes. Smoothness must not be obtained by showing old data as current.

### 2.4 Dynamic bank and cash accounts: mandatory

**No bank name, journal ID, account ID, account code, number of accounts or fixed account array is hardcoded.** The mockup's account rows are examples only.

Odoo models bank/cash accounts separately from journal metadata. Bank creation links a dedicated journal and ledger account; account/journal type and company/currency relationships are available in standard models [S15, S19, S20]. Verify the installed Odoo 19 fields, including its company/branch relationships; do not blindly reuse older-version `company_id` assumptions on accounts.

Implementation rules:

1. Discover authorized, configured bank/cash journals and their ledger-account links, plus eligible bank/cash chart-of-accounts records that have no journal. Use account types and verified report membership—not names containing “bank” or “cash.” The public type `asset_cash` and journal types `bank`/`cash` are inspection starting points, not substitutes for confirming the installed schema and report scope.
2. Treat `(company scope, ledger account identity)` as the balance identity. Journal labels, bank information and currency are metadata. If journal links overlap, do not count a ledger balance twice; show shared configuration or a setup exception instead. Do not confuse a customer's/vendor's saved bank details with company cash accounts.
3. Obtain every amount through native Balance Sheet account detail or aligned General Ledger/Trial Balance closing results. Do not calculate only movements recorded in the bank journal; accounting adjustments may use other journals. Do not replace ledger balances with bank statement, suspense, outstanding-payment or “available funds” figures.
4. The eligible account list updates on the next completed refresh after account/journal creation, rename, link change or allowed reclassification—without installing a module update or editing dashboard settings. Data/configuration changes invalidate any applicable cache. Validate whether report membership changes and surface inconsistencies; never silently alter the report's total or source policy.
5. Include newly configured eligible zero-balance accounts by default in the account directory. Obtain a confirmed zero using the native include-zero/complete-result semantics; missing/hidden report lines alone are not proof of zero. When no balance can be established, say “Balance unavailable.” A user may hide zero rows as a presentation preference with the hidden count visible; the authoritative total does not change.
6. Eligible CoA accounts without a linked bank/cash journal remain discoverable, with “No linked journal” shown. A journal with missing/ineligible/misclassified setup appears as a configuration exception, not as a fabricated balance. A record merely named “Bank” must not enter the cash total if its actual configuration/report classification does not support that.
7. Account directory membership and financial-report composition are separate concepts. If an eligible account is excluded by the approved report variant/filter, show that fact in the directory/exception view; do not add its balance to the official total. Likewise, show additional report cash-equivalent components when they explain why a native total is broader than bank/cash rows.
8. Renames change labels, not identity. Include relevant archived accounts and their balances/activity in historical or current report detail according to the native report; do not discard history because a journal is now inactive. An account created after a historical cut-off may appear in today's directory but must not be represented as having existed at that past date without evidence.
9. Negative balances remain signed. Credit-card liabilities, outstanding/suspense accounts and cash equivalents follow the approved report classification and may need separately labelled lines. They are not automatically added as positive cash because a payment journal references them. Preserve/report any FX or other bridge components when comparing the bank list, Balance Sheet and Cash Flow Statement.
10. Native source totals remain complete when the interface shows only the first accounts. Show “Showing X of Y” and a full searchable account directory; do not make the visible slice the headline total. Apply the same rules to exports, mobile and drill-downs.

Acceptance examples: add a zero-balance AED bank account; add petty cash; post into the new account in disposable test data; record a general-journal adjustment to it; rename it; change its valid linkage; switch company; include an account without a journal; inspect an archived account's historical balance; inspect foreign-currency and negative balances. New qualifying records must appear and their balances must match native report detail, without a code change.

### 2.5 Additional-logic register: explain before enabling

Every proposed custom metric must state the gap in the installed native reports, source report/record inputs, exact calculation, inclusion/exclusion rules, currency/dates, owner, supporting detail and expected test results. Status starts as `proposed` until the material business definition is approved. Reuse an exact native equivalent whenever found. These are candidate methods, not claims that the installed product lacks those features.

| Candidate | When extra logic is justified | Proposed method and proof |
|---|---|---|
| Scheduled daily cash outlook and minimum cash | Standard forecast lacks the requested daily schedule, committed collections, obligations or scenarios | Start with the native reported cash position on the same scope. For each date, add explicit expected receipts and subtract planned payments from that date's opening balance. Take the minimum of the resulting daily balances and report its date. Reuse native forecast/payment scheduling if adequate. Link every schedule item to native historical open-item amounts or an approved separate obligation. Deduplicate PO → bill → payment transitions; account for credits, installments, tax/currency and prior settlements. Never count pipeline as guaranteed cash. Present expected dates and assumptions; forecast is not actual Cash Flow Statement. |
| Payments due in 7/30 days | Native aged-payable/maturity report does not already expose the exact future date buckets | Group native report-provided open maturity amounts by the requested due-date window. No invoice-header due date for installments; no today's residual for historical scope. Show overdue separately and identify credits/unallocated amounts. Supplier bills are not all payroll/tax/loan obligations; broader payment plans require explicit additional schedules. |
| A missing margin / current ratio / period variance / target attainment | Corresponding standard Executive Summary, comparison or budget result absent or definition intentionally different | Reuse native values first. Only if missing, apply the approved arithmetic to native report outputs, e.g. P&L net result ÷ P&L revenue. Native monetary components are never recreated. Zero/negative denominators and loss-to-profit transitions need truthful N/A/explanatory handling. Targets come from approved budgets, not invented values. |
| Remaining delivery backlog value | Native report provides to-deliver quantities but no matching value definition | First reuse native available measures. For goods, propose summing remaining committed quantity × approved discounted tax-exclusive sales-line unit price, using native unit/currency treatment. Exclude down-payment/non-deliverable lines; define returns, overdelivery, cancellation, services, kits and discounts explicitly. Current native quantities are not past-cut-off quantities: require movement/history or an approved snapshot for historical backlog. |
| On-time delivery | An installed standard delivery report does not match the approved commitment/completion definition | Proposed dispatch KPI: eligible completed deliveries meeting an original recorded deadline ÷ eligible completed deliveries with a known original deadline. Define units, grace period, timezones, partial shipments and split orders. Display coverage/excluded cases. N/A when there is no eligible denominator. Keep open-overdue orders separate. Customer receipt requires proof-of-delivery data; do not relabel warehouse completion. Original promises must be retained prospectively when history is missing. |
| Collection rate | Native KPI does not match the explicitly requested definition | First agree a fixed invoice/due cohort and time horizon. Attribute actual cash allocated to it through standard reconciled settlement evidence; separate credit notes and write-offs from cash. Denominator and treatment of opening balances/refunds must be approved. Do not invent a rate by dividing all receipts by all invoices. Prefer standard debtors-days measures when that is the actual decision need. |
| Management attention / targets / thresholds | Native reports have values but not the owner-specific intervention rule | Apply configured materiality, due-date and ownership rules to native report results or authorized operational exceptions. Each alert shows source, amount, reason, owner and next action. Deduplicate alerts and hide resolved cases. Threshold colors do not change underlying values. |
| Stock aging, shortage exposure, procurement risk or historical CRM progression | Requested definition is not covered by the installed native report | Reuse valuation/forecast/CRM/Purchase reports first. Define aging versus nonmovement, physical versus projected shortage, and order-value attribution without double counting. Require history for past pipeline states. Provide a separate definition/approval/test before delivery; do not fabricate quantities, valuation or historical events. |

Sorting salespeople or showing recent orders is not permission to create another financial calculation. The default is native report grouping and native records. Additional cost allocation or historical attribution is a separate approved requirement, not something the agent silently invents.

### 2.6 Mandatory report catalog across departments

The developer must inspect the installed standard reports before implementing widgets in each department. Available report names, actions, fields, filters and backend methods depend on the installation; this table is a source-selection requirement, not a claim that every measure is already installed or exposed. Existing approved customized/localized report variants must be identified, not bypassed.

| Report family to inspect | Intended dashboard use | Mandatory interpretation boundary |
|---|---|---|
| Profit and Loss, Balance Sheet, Cash Flow Statement, Executive Summary, General Ledger, Trial Balance and applicable budgets | Existing financial results, cash position, classified cash flow, account detail, native ratios and comparisons | Preserve section 2.2 authority, sign, precision, report variant and effective options. |
| **Partner Ledger**, customer statements and installed follow-up variants | Customer/vendor account activity and reported balances; ledger drill-down from the selected partner | Preserve account types, commercial-partner/child-contact treatment, opening balances, posting and reconciliation options. Do not use the period's movements alone as closing debt. A combined partner balance is not automatically a customer receivable or supplier payable. [S22] |
| **Aged Receivable and Aged Payable** | Outstanding balances, overdue balances, native aging buckets and supporting open items at the selected cut-off | These remain the source of maturity/aging, not a separately grouped Partner Ledger or invoice residual calculation. Cross-check with the ledger only after making the report scopes and balance definitions comparable. [S1, S22] |
| **Inventory Stock / valuation reports and valuation detail** | Operational inventory quantities and valuation by supported company/product/location/warehouse scope, with native historical views where available | Reuse the native Odoo 19 valuation result; do not recreate FIFO, AVCO, standard-cost calculations or older-version valuation-layer assumptions. Financial stock assets remain sourced from the Balance Sheet. Show the chosen basis in the widget label. [S7, S23] |
| **Inventory Forecast, Locations, Moves History, Replenishment and applicable Inventory analysis** | On-hand versus unreserved stock, expected incoming/outgoing supply and demand, stock movements, location views and replenishment exceptions | Use each native result's supported warehouse/location/owner/date context. Future projected shortage is not physical stockout. Current state is not past state. Detailed source documents and timing must remain inspectable. [S23, S24] |
| **Sales Analysis** | Confirmed order value, products/customers/salespeople/teams, native ordered/delivered/to-deliver/invoiced quantities and existing order measures | Match order status, selected date field, tax basis, currency, unit and aggregation. Ordered or order-linked invoiced amounts are not interchangeable with posted Invoice Analysis or P&L revenue. Use verified distinct-order count when requested, not report-row or line count. [S16] |
| **Invoice Analysis** | Posted net invoiced sales or bills, invoice/credit-note analysis, appropriate customer/product/salesperson rankings | Retain invoice type, posting state, date basis, returns/credits and native currency treatment. Native commercial margin does not become posted accounting gross profit by renaming it. [S17] |
| **Purchase Analysis and installed vendor-performance / receipt reports** | Purchase order values, vendor/category/buyer analysis, ordered/received/billed quantities, available native confirmation and receipt-related measures | Purchase commitments are not posted payables, cash payments or P&L expenses. Inspect the actual formula for timing measures; report labels are not sufficient proof of the event measured. Late/open receipts use matching native operations views when no exact analysis measure exists. [S25, S26] |
| **CRM pipeline/forecast/activity reports** and corresponding authorized native views | Existing pipeline, stage and expected-closing views, probability-weighted amounts and activities | Discover configured stages/teams. Current stage distribution is not a historical conversion funnel; existing measures must match the requested cohort/horizon. |
| **HR reports** in installed Employees, Attendance, Time Off, Planning and Payroll modules | Existing aggregate workforce, leave, attendance and capacity measures where relevant and authorized | Module presence does not authorize all users. Scheduled work is not actual attendance. Payroll remains separately protected. Do not create employee-sensitive detail merely to fill a generic dashboard card. |

**Inspection outcome per widget.** Record one of: exact native measure; native measure requiring supported grouping/filtering; approved composition of native results; genuine custom gap; unavailable/restricted/unsupported. Record the actual report/action, technical source, measure/expression, aggregation, date field, effective domain/context/options, company, unit/currency, source class and destination. Discovery does not authorize arbitrary report endpoints or exposure of every report in the UI. Finance-first hierarchy and the approved widget scope remain unchanged.

**Different report technologies require different thin adapters.** Accounting may use `account.report` and licensed handlers; Sales Analysis and Purchase Analysis have native report models such as `sale.report` and `purchase.report`; Invoice Analysis has `account.invoice.report`. Inventory has native views and specialized computations that must be inspected. Reuse the actual native backend used by the report, including its grouped aggregation or business computation. Do not route every report through `account.report`, scrape rendered screens, copy the native SQL into a parallel custom report, or invent a universal report API. Native ORM aggregation of a report's provided measures is report reuse, not duplication of its underlying transaction formulas. [S14, S16, S17, S26]

**Measure semantics need code-level verification.** For example, the reviewed public Odoo 19 Purchase Analysis base source computes its `delay_pass` (Days to Receive) using the purchase line's planned date and the order date. Do not relabel that measure as actual receipt lead time or on-time supplier delivery without verifying installed extensions and the actual event basis. Keep the native measure truthfully described or register the different requested measure as a gap. Similarly, an average, a percentage, a distinct order count and a monetary sum require their native aggregation—not sums of displayed subtotals. The documentation and installed source are evidence; the installed native behavior and approved definition resolve differences. [S25, S26]

**No meaningless grand totals.** Use native monetary conversion and unit semantics. Do not aggregate incompatible quantities (e.g. kg, units and hours) into a single quantity KPI or add mixed currency amounts without the report's approved conversion. Preserve unknown/unassigned groups. A top-five ranking or the visible page is never the complete report total. Averages of subgroup averages are not replacements for the native overall measure.

**Dynamic dimensions.** In addition to section 2.4 bank/cash discovery, derive vendors, customers, product categories, products, warehouses, locations, salespeople, teams, CRM stages and departments from the authorized native report groups or configuration as appropriate. Never hardcode the sample entities. New eligible records become selectable/discoverable on refresh without code changes; their result appears when they belong to the selected report scope. Preserve historical inactive entities when the native report includes them. Do not force zero rows into every ranking or claim unavailable historical data exists.

**Cross-report reconciliation does not mean making unlike reports equal.** Inventory operational valuation and accounting stock can differ under Odoo 19's recognition/closing process; use the standard Accounting inventory-valuation review to investigate rather than post or invent a balancing value. Partner Ledger versus aging requires aligned account types, cut-off and partner treatment. Sales Analysis versus Invoice Analysis versus P&L reflects different business events. Purchase Analysis versus Aged Payable reflects commitments versus posted outstanding debt. Each widget must match its own intended native source; differences between valid different definitions must be explained, never concealed. [S1, S7, S16, S17, S22, S26]

**Additional-logic discipline applies to every department.** Before writing a custom metric, show the native measures inspected and why none satisfies the requested definition, then use section 2.5's gap/source/formula/approval/tests register. Native grouping, sorting and drill-down configuration are preferred over new calculations. A missing optional module does not justify a silent custom replacement.

## 3. Shared scope and time rules

**Period versus position.** Revenue/profit/movement use a period. Cash, outstanding debt and backlog use an as-of cutoff. CRM/current stock/workforce may be current snapshots. Forecasts use a forward horizon from an identified snapshot. Unsupported filters must be explicitly excluded or rejected—not silently applied to unrelated dates.

**Historical balances.** Do not take today's `amount_residual` as a past-period answer. Use the native dated report calculation through its handler. A separately rebuilt equivalent is not permitted for a metric already available from that report. An illustrative invoice of 100,000 with 40,000 settled by August 31 and 60,000 in September is 60,000 outstanding on August 31 even if today's balance is zero. Installment lines may have multiple aging buckets for one invoice. Backdated entries can restate history; distinguish recalculated history from a formally retained “as reported” close snapshot when required.

**Fair comparison.** Match comparable elapsed periods; handle loss-to-profit transitions and zero prior denominators without misleading percentage changes. Do not compare partial September to all of August without saying so.

**Company/branch.** Start from the verified authorized company. This prototype has one fictional company/two fictional branches, not consolidated group accounting. Verify whether branch dimensions exist consistently across ledger, bank, expenses and transactions. Show unallocated/shared amounts or unavailable branch profit rather than fabricate allocations. Multi-company aggregation requires approved currency and elimination rules; it is not a sum of mixed currency numbers.

**Currency and rounding.** Follow native company/report-currency, conversion-date and rounding rules; test comparison using currency precision, then format the result. Keep native/document currencies visible where relevant. “2.33M” is a presentation abbreviation, not reconciliation precision.

**Targets/history.** Missing budgets/targets produce “Not configured.” Do not infer targets from prior actuals. Where original promises or historical stage states were not recorded, expose coverage and define prospective capture rather than invent history. Prototype linear target proration is not an approved production calendar policy.

**Forecast hygiene.** Keep forecasts separate from actual cash-flow reporting. Record input snapshot, expected dates and source lineage. Do not use later actual outcomes as though they had been known at an earlier forecast date. Avoid counting a PO, its subsequent bill and the planned payment as three different obligations. Pipeline is not a guaranteed receipt. A positive month-end balance must not hide an intermediate low point.

## 4. Shared metric response and traceability

Use a small versioned registry, not a generic analytics platform. A proposed payload shape is:

```json
{
  "metric_id": "finance.receivables.overdue",
  "definition_version": "4",
  "value": 60000.00,
  "unit": "money",
  "currency": "AED",
  "scope": {"company_ids": [1], "branch_ids": [], "as_of": "2026-08-31", "posting_state": "posted"},
  "source_kind": "native_report",
  "source_report": {"report_ref": "verified-at-installation", "variant_ref": "verified-at-installation", "line_or_expression_ref": "verified-at-installation", "column_ref": "verified-at-installation", "options_fingerprint": "opaque-server-value"},
  "derivation": null,
  "availability": "ok",
  "freshness": "unknown",
  "completeness": "provisional",
  "reconciliation": "not_run",
  "computed_at": "2026-09-19T09:00:00Z",
  "source_as_of": "2026-08-31",
  "warnings": [],
  "request_id": "opaque-request-reference",
  "drilldown_key": "receivables.overdue"
}
```

Illustrative JSON only; company ID/value/time are not real project identifiers. Support availability `ok`, `no_activity`, `not_configured`, `not_installed`, `unsupported_scope`, `restricted`, `error`; freshness `fresh`, `stale`, `unknown`; completeness `provisional`, `closed`, `unknown`; reconciliation `not_run`, `matched`, `mismatch`, `outdated`. Keep these dimensions separate. Financial-period close status must come from an approved close process, not merely a lock-date guess.

For nonfinancial sources, the provenance must also identify the native backend kind (financial handler, analytical report model or operational report/service), actual technical model/action, selected measure, native aggregation, date field, effective domain/context, groupings and unit where applicable. Use verified fields; financial expression identities are not imposed on reports without expressions.

Identify every widget source as `native_report`, `report_derived`, `operational_records`, or `forecast` (as appropriate); financial results may not masquerade as another class. A genuine monetary zero is allowed. A denominator-free rate, restricted result, failed request or unavailable definition has no invented numeric value. Displaying stale permitted data requires its actual source timestamp and a visible warning. Withhold old-company data immediately on company changes. Do not display sample fallback values after a live failure.

Return only authorized source/report metadata. Resolve actions server-side from allowlisted metric keys plus validated scope; do not accept arbitrary model names/domains/SQL supplied by a client or agent. Provide bounded paginated detail methods. Use these same secured services for future read-only agent access; no new AI service is required now.

Cards, charts, exports and drill-downs must preserve definition and scope. Account for source changes between requests: use a coherent report calculation where needed, include snapshot/request metadata, and explicitly refresh when the source changed. An unchanged URL/filter is not proof of an unchanged ledger.

## 5. Accuracy acceptance matrix

| Test family | Required evidence |
|---|---|
| Known accounting case | Construct balanced Odoo entries with independently specified expected revenue, COGS, expenses and net result. Check signed losses and refunds. Do not compute expected results by calling the metric helper being tested. |
| Historical settlement | Use the 100,000/40,000/60,000 example above, current and historical cutoffs, plus backdated entries and installment maturities. Verify correct native-report treatment. |
| Credits and edge cases | Partial payments, credit notes, supplier refunds, unallocated receipts, write-offs, overpayments, due-today, canceled/draft documents and multicurrency rounding. |
| Standard-report agreement | Compare every report-backed metric across Finance, Sales, Purchase, Inventory and other enabled departments to its approved native report with identical company, branch support, currency, dates, posting state, accounting basis and report mapping. Compare full precision with currency-aware rounding. Any unexplained difference outside the documented native currency/rounding precision blocks qualification, even when management would call the amount immaterial. Verify the native UI/export independently of the dashboard adapter; comparing the adapter against itself is not evidence. |
| Distinct business measures | A recognition/accrual adjustment can change accounting revenue without changing net invoiced sales. A confirmed order is not an invoice or cash receipt. Demonstrate the distinction. |
| Drill-down/export | Report/record links retain applicable filters and cutoffs; searched export matches all matching authorized rows, not only the visible page. Test zero rows, pagination, changed sources and return navigation. Include scope/units/source timestamp/definition in exports; prevent spreadsheet-formula injection. |
| Cash | Native opening, movement, closing and any explicit FX/other lines form the native report bridge. Internal transfers are treated by the standard Cash Flow Statement. Do not silently drop unclassified lines or force incompatible cash scopes to match. External bank reconciliation and source freshness remain separate controls. |
| Dynamic bank/cash | Execute all section 2.4 creation, zero-balance, rename, archive, no-journal, overlapping-link, general-journal adjustment, historical, multicurrency, negative-balance and authorization cases. Directory and report membership must remain explicit; no module update or hardcoded list edit. |
| Report variation / drift | Test changed revenue/expense accounts, report variant, expression mapping, supported filters, translation, currency columns, hidden zero lines and more rows than the unfolding limit. Confirm the standard result flows through automatically or an invalid mapping is rejected visibly. |
| Native versus extra logic | Every metric has a source class. Reject duplicated native financial or operational report formulas. Each genuine additional formula has a recorded business definition, approval, independent cases and drill-down. Test standard commercial margin separately from P&L gross profit. |
| Sales/fulfillment | Partial deliveries/cancellations/returns, mixed line types, timezone boundaries, changed promises, missing original history, attribution splits, missing targets, loss-making contribution and no completed deliveries. |
| Partner Ledger and aging | Test a customer, vendor and dual-role partner; child contacts/commercial entities; opening balance, period activity, credit notes, partial settlements and historical cut-off. Match each source independently; explain differences until scope and meaning are aligned. Do not net receivable/payable roles silently. |
| Inventory report fidelity | Compare dashboard quantities and operational values to the native stock/valuation/forecast view for each supported company/location/warehouse/date/owner scope. Cover returns, partial moves, reservations, valuation changes, consignment and historical availability where supported. Confirm accounting valuation is labelled separately and differences route to native review. |
| Purchase and Sales Analysis | Match the native order and invoice report measures, date fields, status filters, native currency/UoM treatment, distinct-order versus line counts and subgroup aggregations. Check refunds/returns, partial receipts/deliveries/billing, tax-inclusive versus untaxed values, average measures, unknown salesperson/vendor groups and measures whose labels obscure planned versus actual events. |
| Dynamic reporting dimensions | Add authorized vendors, customers, salespeople/teams, warehouse/location/category and stage/department fixtures only for installed applicable modules; verify selection, grouping, scope, new eligible activity and historical inactive groups without a source-code change. |
| Permissions | Owner, finance-authorized, sales-only and no-dashboard roles; separate companies; restricted fields/HR; direct RPC requests; export; caches; revoked access. Unauthorized aggregates must not leak even when records are hidden. |
| Source completeness | Finance owner reviews missing/unposted documents, classification, accruals, reconciliations and period close. Matching a report alone does not prove correct real-world books. Record outstanding limitations and owner. |

A “reconciled” indicator requires recorded evidence for that metric/definition/scope/source state. A previous test run or a successful response must not generate a misleading live green badge. Changes to report mappings, source data or relevant logic invalidate or age that evidence according to a documented policy.

## 6. UX, resilience and performance acceptance

Use native client-action/ORM/security patterns [S8, S9]. Build reusable components, accessible labels, visible keyboard focus, usable tap targets, chart data alternatives and full English/Arabic localization. WCAG 2.2 AA is a design/verification target, not an assumed certification [S12]. Test widths 320, 390, 768, 1024, 1440 and 1920, reflow/zoom, RTL and mixed-script document references.

Test delayed requests, section failures, rapid filter changes, stale responses, repeated refresh, component destruction and empty/large datasets. Avoid unbounded background polling. Refresh visible sections at a documented cadence appropriate to actual source freshness. Saved layout/filter preferences never save new authorization. Back navigation restores applicable report search, filters and scroll; changed records/access are revalidated.

Use native report batching, shared evaluations per options set and profiling rather than per-record calls [S10]. Performance optimization must preserve the native reporting calculation; raw-transaction reimplementation is not a shortcut. Start without heavy cache/snapshot infrastructure; add only when measurement justifies it. Server detail pagination defaults to a bounded page. Measure initial usable Finance view, filter refresh, large detail/report behavior, concurrency and query/record growth against representative data and agreed hardware. Proposed initial budgets: p95 usable Finance ≤3 seconds and ordinary filter refresh ≤2 seconds. Validate/adjust openly before acceptance; these are targets, not measured results or guarantees.

Security checks apply to the underlying calculations, cache keys, direct RPC, exports and records. Do not use blanket superuser access or trust client-provided company IDs [S9]. Log sanitized metric/request IDs, timings and error categories rather than unnecessary bank/customer/employee details.

## 7. Implementation gates and deliverables

G0: verified environment, installed-report catalog across all departments and exact-native-versus-gap classification for every widget, licensed report APIs, report/variant/expression/column/action mapping, effective-option contracts, permissions, additional-logic register and test harness. Explain any report gap and proposed formula to the owner before enabling it.

G1: a report-backed receivables vertical journey using native aging results (not new settlement arithmetic), with independent expectations, native UI/report parity and actual browser/permission evidence.

G2: complete report-backed Finance, dynamic bank/cash acceptance, Cash Flow Statement, and any approved separately labelled cash-plan extension. Native margins/forecasts/budgets are inspected before inventing substitutes.

G3: complete native-report-backed Sales and fulfillment with distinct Sales Analysis/Invoice Analysis bases, partial delivery and attribution coverage.

G4: native-report-backed Inventory, Purchase, CRM and HR as applicable; partner/detail and cross-report consistency checks; install/update, English/Arabic, performance, independent review where available, and owner/finance UAT handoff.

Use applicable Python, frontend and browser integration tests [S11]. Record skipped/blocked tests, unavailable dependencies and actual discovered test counts. A static screenshot or offline fixture pass is not Odoo integration evidence. No unresolved Critical/High defects or unexplained differences from the intended native financial or operational report (outside documented native precision) are acceptable as UAT-ready. Document lesser findings; business UAT and release authorization remain distinct.

Keep one living dossier: configuration/metric decisions, actual fields/actions, source commit and environment identity, test commands/raw results, real Odoo screenshots, user guidance, upgrade notes, known limitations and next action. A checksum confirms bytes, not execution provenance.

## Primary sources

Reference list inherited from v3, with the relevant Accounting, Sales, Purchase, Inventory and invoice-report sources rechecked for this v4 revision on 19 September 2026. Exact APIs depend on the target source and licensed modules; verify again during implementation. Not every inherited reference was re-opened for this documentation update.

- [S1 — Odoo 19 accounting reports](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/reporting.rst)
- [S2 — Odoo 19 account journal-item source](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/models/account_move_line.py)
- [S3 — Odoo 19 partial reconciliation source](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/models/account_partial_reconcile.py)
- [S4 — Odoo 19 payments](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/payments.rst)
- [S5 — Odoo 19 bank reconciliation](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/bank/reconciliation.rst)
- [S6 — Odoo 19 sale/stock order integration](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/sale_stock/models/sale_order.py)
- [S7 — Odoo 19 inventory valuation](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/inventory_and_mrp/inventory/inventory_valuation/cheat_sheet.rst)
- [S8 — Odoo 19 Owl client action](https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/howtos/javascript_client_action.rst)
- [S9 — Odoo 19 security](https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/backend/security.rst)
- [S10 — Odoo 19 performance](https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/backend/performance.rst)
- [S11 — Odoo 19 testing](https://raw.githubusercontent.com/odoo/documentation/19.0/content/developer/reference/backend/testing.rst)
- [S12 — W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)

- [S13 — Odoo 19 report variants, expressions and cross-report formulas](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/reporting/customize.rst)
- [S14 — Odoo 19 account.report definitions](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/models/account_report.py)
- [S15 — Odoo 19 bank and cash account configuration](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/bank.rst)
- [S16 — Odoo 19 Sales Analysis source](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/sale/report/sale_report.py)
- [S17 — Odoo 19 Invoice Analysis source, including commercial margin](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/report/account_invoice_report.py)
- [S18 — Odoo 19 budgets](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/reporting/budget.rst)
- [S19 — Odoo 19 chart-of-accounts model](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/models/account_account.py)
- [S20 — Odoo 19 journal model](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/account/models/account_journal.py)
- [S21 — Odoo 19 account-type and chart-of-accounts documentation](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/get_started/chart_of_accounts.rst)


- [S22 — Odoo 19 Partner Ledger and Aged Receivable overview](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/finance/accounting/customer_invoices.rst)
- [S23 — Odoo 19 Inventory Stock report](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/inventory_and_mrp/inventory/warehouses_storage/reporting/stock.rst)
- [S24 — Odoo 19 Inventory Forecast report](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/inventory_and_mrp/inventory/warehouses_storage/reporting/forecast.rst)
- [S25 — Odoo 19 Purchase Analysis measures](https://raw.githubusercontent.com/odoo/documentation/19.0/content/applications/inventory_and_mrp/purchase/advanced/analyze.rst)
- [S26 — Odoo 19 Purchase Analysis implementation](https://raw.githubusercontent.com/odoo/odoo/19.0/addons/purchase/report/purchase_report.py)

## Version 4 status and boundary

This revision makes the existing report-first policy explicit across all departments, adds Partner Ledger and detailed Inventory/Purchase/Sales source selection, distinguishes the different native report backends, strengthens operational parity and dynamic-dimension tests, and requires inspection of actual measure semantics before custom development. Prior dynamic bank/cash, data-assurance, security and UX requirements remain mandatory. This v4 contract and prompt replace the prior implementation documents.

The v2 HTML, its fixtures and previews are unchanged and remain visual/interaction references only. No Odoo implementation, connected-database inspection, live report mapping, permission test, dynamic-account test or performance test was performed in this documentation revision. No code repository, accounting records, report definitions or permissions were changed. All installed-environment discovery and implementation acceptance remain work for the verified development environment.
