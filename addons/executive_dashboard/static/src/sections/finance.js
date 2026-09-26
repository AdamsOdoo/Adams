/** @odoo-module **/
import { Component, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { LineChart } from "../widgets/charts";
import { compact, percent, whole } from "../widgets/format";

const AGE_RAMP = ["--a1", "--a2", "--a3", "--a4", "--a5"];

/**
 * Finance: six figures, revenue & net profit by month, Bank & Cash, and
 * Receivables and Payables, each in one box with an Aged / Expected switch. Balances are
 * taken at the period's end (never after today). Every figure opens its
 * detail in the side panel; the panel's button (Open record / Open list / Open report) opens the native screen.
 */
export class FinanceSection extends Component {
    static template = "executive_dashboard.FinanceSection";
    static components = { Icon, LineChart };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.compact = compact;
        this.whole = whole;
        this.orm = useService("orm");
        this.action = useService("action");
        // Aged or Expected per box, kept for the way back from a native screen.
        this.views = useState(this.env.edRecall?.("finance.views") || { receivables: "aged", payables: "aged" });
        this.env.edRemember?.("finance.views", () => ({ ...this.views }));
        onWillUnmount(() => this.env.edForget?.("finance.views"));
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
              cap: _t("%(count)s accounts · as of %(date)s", { count: k.bank_cash_accounts, date: this.asOf }),
              open: () => this.open("bank_cash", this.periodArgs) },
            { key: "recv", icon: "down", label: _t("Receivables"), value: k.receivables,
              cap: this.overdueCap(this.w.receivables), open: () => this.openItems("receivables", "aged") },
            { key: "pay", icon: "up", label: _t("Payables"), value: k.payables,
              cap: this.overdueCap(this.w.payables), open: () => this.openItems("payables", "aged") },
        ];
    }

    /** Past-due invoices (bills) only: credits are shown apart, never netted into "overdue". */
    overdueCap(widget) {
        return widget.owed_overdue > 0 ? _t("Overdue %s", compact(widget.owed_overdue)) : _t("Nothing overdue");
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

    /** "26 Sep 2026": the balance date of this result (the period's end, never after today). */
    get asOf() {
        return deserializeDate(this.w.kpis.as_of).toFormat("d MMM yyyy");
    }

    get bankSubtitle() {
        return this.w.bank_cash.source === "report"
            ? _t("Balance Sheet › Bank and Cash Accounts · as of %s", this.asOf)
            : _t("Bank and cash accounts · as of %s", this.asOf);
    }

    setView(kind, view) {
        this.views[kind] = view;
    }

    /**
     * One box each for Receivables and Payables, with a switch between Aged (by days
     * overdue) and Expected (by due date). Each bucket is one bar row: label, bar scaled
     * to the largest amount, amount and, when every bucket has the same sign, its share.
     * Amounts owed are positive; unapplied credits and advances are negative.
     */
    openItemsPanels() {
        return ["receivables", "payables"].map((kind) => {
            const widget = this.w[kind];
            const recv = kind === "receivables";
            const view = this.views[kind];
            const aged = widget.aged;
            const buckets = view === "aged"
                ? aged.map((b, i) => ({
                    ...b, color: `var(${AGE_RAMP[aged.length > 1 ? Math.round((i * 4) / (aged.length - 1)) : 0]})`,
                }))
                : widget.expected.map((b) => ({ ...b, color: b.key === "overdue" ? "var(--crit)" : "var(--sec)" }));
            const total = view === "aged" ? widget.total : widget.expected.reduce((sum, b) => sum + b.value, 0);
            return this.bucketPanel({
                kind, view, total,
                title: recv ? _t("Receivables") : _t("Payables"),
                sub: view === "aged"
                    ? _t("By days overdue · as of %s", this.asOf)
                    : (recv ? _t("Customer payments by due date · as of %s", this.asOf)
                        : _t("Supplier payments by due date · as of %s", this.asOf)),
                owedOverdue: widget.owed_overdue,
                overduePct: widget.owed > 0 ? percent(widget.owed_overdue, widget.owed) : null,
                credits: widget.credits,
                creditsLabel: recv ? _t("Unapplied credits") : _t("Advances & unmatched payments"),
                netNote: total < 0
                    ? (recv ? _t("Net credit balance: unapplied credits exceed the open invoices.")
                        : _t("Net debit balance: advances and unmatched payments exceed the open bills."))
                    : "",
                difference: view === "aged" && widget.report && Math.abs(widget.difference) >= 1
                    ? widget.difference : 0,
                differenceNote: recv
                    ? _t("The open receivable journal items differ from the Aged Receivable report by %(amount)s %(currency)s.",
                        { amount: whole(widget.difference), currency: this.currency })
                    : _t("The open payable journal items differ from the Aged Payable report by %(amount)s %(currency)s.",
                        { amount: whole(widget.difference), currency: this.currency }),
                buckets,
            });
        });
    }

    bucketPanel(panel) {
        const values = panel.buckets.map((b) => b.value);
        const max = Math.max(0, ...values.map(Math.abs));
        // Shares of a total only make sense when every bucket has the same sign.
        const sameSign = values.every((v) => v >= 0) || values.every((v) => v <= 0);
        return {
            ...panel,
            id: panel.kind,
            rows: panel.buckets.map((b) => ({
                ...b,
                width: max > 0 ? (Math.abs(b.value) / max) * 100 : 0,
                color: b.value < 0 ? "var(--faint)" : b.color,
                share: sameSign ? percent(b.value, panel.total) : null,
            })),
        };
    }

    // ------------------------------------------------------------ side panel

    open(name, args, crumb = _t("Finance")) {
        this.props.openPanel({ kind: "drawer", key: `finance.${name}`, args, crumb, sec: "finance" });
    }

    openItems(kind, view, bucket) {
        this.open("open_items", { ...this.periodArgs, kind, view, ...(bucket ? { bucket } : {}) });
    }

    /** An account opens its native screen (the Trial Balance) at once. */
    async openAccount(row) {
        const action = await this.orm.call("executive.dashboard", "open_action",
            ["finance.account", { ...this.periodArgs, account_id: row.id }]);
        this.env.edLeaving?.();
        await this.action.doAction(action);
    }

}

sectionRegistry.add("finance", FinanceSection);
