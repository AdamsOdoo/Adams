# Reports, dashboards and figures

Users compare every number you show with Odoo's own reports. A KPI that disagrees with standard Odoo for the same filters is a defect, even if its code "works".

## The standard report is the authority

1. **Use the standard result when it exists.** If a standard report gives the figure, don't recompute it from the underlying records. Show it through the report itself (its menu or action with the right filters, a pivot or graph view on the report model) or read the report model with `_read_group` using the same domain as the drill-down.
2. **Financial statements, aged balances and tax figures** come from `account.report` records. Their definitions (lines and expressions) are in Community `account` (`addons/account/models/account_report.py`); the engine that computes them is the Enterprise `account_reports` app. Use that engine or link to the report; look up its methods with `oh src --module account_reports` when the Enterprise source is configured, otherwise check them on an Odoo.sh build. Don't rebuild a profit and loss, balance sheet or aged balance from journal items.
3. **A custom calculation needs a written reason**: no standard report provides the figure. Put the reason and the full definition in the feature notes: model, date field and period, document states, companies, currency and conversion date, sign convention, and the standard figure it must reconcile with, if any.
4. **One definition for the number and its list.** Compute the KPI and build its drill-down action from the same domain (one method returns both), so the records a user opens add up to the number shown.

| Figure | Standard report to use or match (Odoo 19) |
|---|---|
| Sales amounts, quantities, margins | `sale.report` (Sales > Reporting) |
| Invoiced revenue, invoice analysis | `account.invoice.report` (Invoicing > Reporting) |
| Profit and loss, balance sheet, aged receivables/payables, tax report | `account.report` records, computed by the Enterprise `account_reports` app (Accounting > Reporting) |
| Journal-level totals no report provides | Journal items (`account.move.line`) with `parent_state = 'posted'`, `balance` in company currency |
| Open amounts | `amount_residual_signed` on `account.move`; `amount_residual` on `account.move.line` |
| Purchases | `purchase.report` |
| Point of sale | `report.pos.order` |
| Stock on hand and forecast | `stock.quant` (on hand), `report.stock.quantity` (forecast), `stock.move.line` (done moves) |
| CRM activities, time off | `crm.activity.report`, `hr.leave.report` |

Before writing a query, open the standard report model in the source (`oh src "_name = 'sale.report'"`) and copy its filters and sign conventions.

## Get these right

- **Filters:** the same date field (invoice date or accounting date; order date or confirmation date), the same states (posted only, confirmed orders), the same companies (`self.env.companies`) and the same journals.
- **Signs and currency:** use the `*_signed` and company-currency fields (`amount_total_signed`, `balance`) to sum across documents; credit notes subtract. Don't add amounts in different currencies.
- **Time zones:** date boundaries are in the user's time zone for datetime fields. Use `fields.Date.context_today(self)` and convert datetimes carefully.
- **Multi-company:** aggregate only the allowed companies, and label figures in multi-currency setups.
- **Access:** compute as the user (with record rules) unless the figure is explicitly global. If you must use `sudo()`, say which data it exposes.
- **Drill-down:** every figure should open the records it counts. Return an action whose `domain` is the one used for the figure, so the user can check the total.
- **Performance:** aggregate in the database with `_read_group` or `SQL`, not by looping over records in Python.

Test a figure the way users will check it: build a small data set in the test, compute the expected value independently (for example with `_read_group` on the standard report model) and compare the two.

## QWeb PDF reports

```xml
<record id="action_report_fleet_x" model="ir.actions.report">
    <field name="name">Fleet X Sheet</field>
    <field name="model">fleet.x</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">my_module.report_fleet_x</field>
    <field name="binding_model_id" ref="model_fleet_x"/>
</record>
<template id="report_fleet_x">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="doc">
            <t t-call="my_module.report_fleet_x_document" t-lang="doc.partner_id.lang"/>
        </t>
    </t>
</template>
<template id="report_fleet_x_document">
    <t t-call="web.external_layout">
        <div class="page"><h2 t-field="doc.name"/></div>
    </t>
</template>
```

- `t-lang` renders each document in the partner's language, as the standard sale order report does.
- Use `t-field` (formatted, translated) rather than `t-out` for field values; add `t-options='{"widget": "monetary", "display_currency": doc.currency_id}'` for amounts.
- PDFs need wkhtmltopdf, which may be missing locally (`oh env` says so). Test the data and HTML locally with `report_type` `qweb-html` or by rendering the report in a test, and check the final PDF, including Arabic, on an Odoo.sh build.
