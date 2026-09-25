/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { ColumnChart, LineChart } from "../widgets/charts";
import { compact, percent, whole } from "../widgets/format";

const AGE_RAMP = ["--a1", "--a2", "--a3", "--a4", "--a5"];

/**
 * Finance: six figures, revenue & net profit by month, Bank & Cash, and
 * Receivables / Payables with Aged and Expected views. Every figure opens its
 * detail in the side panel; the panel's button (Open record / Open list / Open report) opens the native screen.
 */
export class FinanceSection extends Component {
    static template = "executive_dashboard.FinanceSection";
    static components = { Icon, LineChart, ColumnChart };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.state = useState({ receivables: "aged", payables: "aged" });
        this.compact = compact;
        this.whole = whole;
    }

    get w() {
        return this.props.data.widgets;
    }

    get currency() {
        return this.w.currency.name;
    }

    /** Period of this result, passed to the drawers so they use the same dates. */
    get periodArgs() {
        const { key, date_from, date_to } = this.props.data.period;
        return { period: key, date_from, date_to };
    }

    get kpis() {
        const k = this.w.kpis;
        const margin = (value) => {
            const pct = percent(value, k.revenue);
            return pct === null ? "" : _t("%s% margin", pct);
        };
        return [
            { key: "revenue", icon: "coin", label: _t("Revenue"), value: k.revenue,
              cap: _t("%s invoices · posted", k.invoices), open: () => this.open("revenue", this.periodArgs) },
            { key: "gross", icon: "scale", label: _t("Gross profit"), value: k.gross_profit,
              cap: margin(k.gross_profit), open: () => this.open("revenue", this.periodArgs) },
            { key: "net", icon: "spark", label: _t("Net profit"), value: k.net_profit,
              cap: margin(k.net_profit), open: () => this.open("revenue", this.periodArgs) },
            { key: "bank", icon: "bank", label: _t("Bank & Cash"), value: k.bank_cash,
              cap: _t("%s accounts · as of today", k.bank_cash_accounts), open: () => this.open("bank_cash", {}) },
            { key: "recv", icon: "down", label: _t("Receivables"), value: k.receivables,
              cap: _t("Overdue %s", compact(k.receivables_overdue)), open: () => this.openItems("receivables", "aged") },
            { key: "pay", icon: "up", label: _t("Payables"), value: k.payables,
              cap: _t("Overdue %s", compact(k.payables_overdue)), open: () => this.openItems("payables", "aged") },
        ];
    }

    get trend() {
        const months = this.w.trend.months;
        const dates = months.map((m) => deserializeDate(m.month));
        return {
            labels: dates.map((d) => d.toFormat("MMM")),
            titles: dates.map((d, i) => {
                const title = d.toFormat("MMMM yyyy");
                return i === dates.length - 1 && this.w.trend.partial ? _t("%s · to date", title) : title;
            }),
            series: [
                { name: _t("Revenue"), values: months.map((m) => m.revenue), color: "var(--s1)", area: true },
                { name: _t("Net profit"), values: months.map((m) => m.net_profit), color: "var(--s2)" },
            ],
            partial: this.w.trend.partial,
        };
    }

    get bankSubtitle() {
        return this.w.bank_cash.source === "report"
            ? _t("Balance Sheet › Bank and Cash Accounts · as of today")
            : _t("Bank and cash accounts · as of today");
    }

    openItemsPanels() {
        return ["receivables", "payables"].map((kind) => {
            const widget = this.w[kind];
            const view = this.state[kind];
            const aged = widget.aged;
            return {
                kind,
                view,
                title: kind === "receivables" ? _t("Receivables") : _t("Payables"),
                sub: `${kind === "receivables" ? _t("Open customer invoices") : _t("Open vendor bills")} · ${_t("as of today")}`,
                note: kind === "receivables"
                    ? _t("Amounts customers are due to pay, by invoice due date.")
                    : _t("Amounts due to suppliers, by bill due date."),
                total: view === "aged" ? widget.total : widget.expected.reduce((s, b) => s + b.value, 0),
                aged: aged.map((b, i) => ({
                    ...b,
                    color: `var(${AGE_RAMP[aged.length > 1 ? Math.round((i * 4) / (aged.length - 1)) : 0]})`,
                    flex: Math.max(0, b.value),
                })),
                columns: widget.expected.map((b) => ({
                    label: b.label, value: b.value, key: b.key,
                    color: b.key === "overdue" ? "var(--crit)" : null,
                })),
            };
        });
    }

    // ------------------------------------------------------------ side panel

    open(name, args, crumb = _t("Finance")) {
        this.props.openPanel({ kind: "drawer", key: `finance.${name}`, args, crumb, sec: "finance" });
    }

    openItems(kind, view, bucket) {
        this.open("open_items", bucket ? { kind, view, bucket } : { kind, view });
    }

    openAccount(row) {
        this.open("account", { account_id: row.id }, _t("Bank & Cash"));
    }

    setView(kind, view) {
        this.state[kind] = view;
    }
}

sectionRegistry.add("finance", FinanceSection);
