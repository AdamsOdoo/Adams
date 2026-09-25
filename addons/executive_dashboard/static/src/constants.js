/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";

// Section order and Welcome card copy. Labels are resolved at call time so
// they use the loaded translations.
export function sectionInfo() {
    return {
        welcome: { key: "welcome", name: _t("Welcome") },
        finance: {
            key: "finance", name: _t("Finance"),
            description: _t("Revenue, profit, bank & cash, receivables and payables"),
            chips: [_t("Revenue"), _t("Bank & Cash"), _t("Receivables"), _t("Payables")],
        },
        sales: {
            key: "sales", name: _t("Sales"),
            description: _t("Invoiced sales, orders, salespeople, products and customers"),
            chips: [_t("Invoiced sales"), _t("Recent orders"), _t("Top products by quantity")],
        },
        crm: {
            key: "crm", name: _t("CRM"),
            description: _t("Pipeline, stages, new leads and won opportunities"),
            chips: [_t("Open pipeline"), _t("Pipeline by stage"), _t("Won")],
        },
        procurement: {
            key: "procurement", name: _t("Procurement"),
            description: _t("Purchases, approvals, receipts and suppliers"),
            chips: [_t("Waiting for approval"), _t("Late receipts"), _t("Purchases by month")],
        },
        inventory: {
            key: "inventory", name: _t("Inventory"),
            description: _t("Stock report, deliveries and receipts"),
            chips: [_t("Stock report"), _t("Deliveries"), _t("Receipts")],
        },
        people: {
            key: "people", name: _t("People"),
            description: _t("Attendance, time off, shifts, headcount and directory"),
            chips: [_t("Attendance today"), _t("Time off"), _t("Shifts today")],
        },
    };
}

export function periodOptions() {
    return [
        { key: "month", label: _t("This month") },
        { key: "last_month", label: _t("Last month") },
        { key: "quarter", label: _t("This quarter") },
        { key: "ytd", label: _t("Year to date") },
        { key: "custom", label: _t("Custom") },
    ];
}
