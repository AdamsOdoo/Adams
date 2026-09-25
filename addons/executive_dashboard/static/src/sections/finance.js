/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { LineChart } from "../widgets/charts";
import { compact, percent, whole } from "../widgets/format";

const AGE_RAMP = ["--a1", "--a2", "--a3", "--a4", "--a5"];

/**
 * Finance: six figures, revenue & net profit by month, Bank & Cash, and
 * Receivables and Payables, each in an Aged and an Expected box. Every figure opens its
 * detail in the side panel; the panel's button (Open record / Open list / Open report) opens the native screen.
 */
export class FinanceSection extends Component {
    static template = "executive_dashboard.FinanceSection";
    static components = { Icon, LineChart };
    static props = { data: Object, openPanel: Function };

    setup() {
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

    /**
     * Four boxes: Receivables and Payables, each Aged (by days overdue) and Expected
     * (by due date). Each bucket is one bar row: label, bar scaled to the largest
     * bucket, amount and share of the total. A row opens its detail.
     */
    openItemsPanels() {
        const panels = [];
        for (const kind of ["receivables", "payables"]) {
            const widget = this.w[kind];
            const recv = kind === "receivables";
            const aged = widget.aged;
            panels.push(this.bucketPanel(kind, "aged", recv ? _t("Receivables · Aged") : _t("Payables · Aged"),
                _t("By days overdue · as of today"), widget.total, widget.overdue,
                aged.map((b, i) => ({
                    ...b, color: `var(${AGE_RAMP[aged.length > 1 ? Math.round((i * 4) / (aged.length - 1)) : 0]})`,
                }))));
            panels.push(this.bucketPanel(kind, "expected", recv ? _t("Receivables · Expected") : _t("Payables · Expected"),
                recv ? _t("Customer payments by due date") : _t("Supplier payments by due date"),
                widget.expected.reduce((sum, b) => sum + b.value, 0), widget.overdue,
                widget.expected.map((b) => ({ ...b, color: b.key === "overdue" ? "var(--crit)" : "var(--sec)" }))));
        }
        return panels;
    }

    bucketPanel(kind, view, title, sub, total, overdue, buckets) {
        const max = Math.max(0, ...buckets.map((b) => b.value));
        return {
            id: `${kind}-${view}`, kind, view, title, sub, total, overdue,
            overduePct: percent(overdue, total),
            rows: buckets.map((b) => ({
                ...b,
                width: max > 0 ? Math.max(0, (b.value / max) * 100) : 0,
                share: percent(b.value, total),
            })),
        };
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

}

sectionRegistry.add("finance", FinanceSection);
