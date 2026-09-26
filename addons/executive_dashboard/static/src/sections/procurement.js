/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { ColumnChart } from "../widgets/charts";
import { compact, periodLabel, whole } from "../widgets/format";

/**
 * Procurement: purchases confirmed, orders to approve, late receipts and the
 * open purchase value; orders waiting for approval, late receipts, top
 * suppliers and purchases by month. A widget whose app is missing arrives as null.
 */
export class ProcurementSection extends Component {
    static template = "executive_dashboard.ProcurementSection";
    static components = { Icon, ColumnChart };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.compact = compact;
        this.whole = whole;
        // Column names repeated on each card at phone width.
        this.labels = {
            ref: _t("Reference"), supplier: _t("Supplier"), value: _t("Value"), date: _t("Order deadline"),
        };
    }

    get w() {
        return this.props.data.widgets;
    }

    get currency() {
        return this.w.currency.name;
    }

    get period() {
        return periodLabel(this.props.data.period);
    }

    get periodArgs() {
        const { key, date_from, date_to } = this.props.data.period;
        return { period: key, date_from, date_to };
    }

    get kpis() {
        const k = this.w.kpis;
        const list = [
            { key: "purchases", icon: "cart", label: _t("Purchases confirmed"), value: compact(k.purchases.amount),
              money: true, cap: _t("%s orders", k.purchases.count), open: () => this.openOrders("purchases") },
            { key: "approve", icon: "clock", label: _t("To approve"), value: whole(k.approve.count),
              cap: compact(k.approve.amount) + " " + this.currency, open: () => this.openOrders("approve") },
        ];
        if (k.late) {
            list.push({ key: "late", icon: "truck", label: _t("Late receipts"), value: whole(k.late.count),
                cap: _t("%s suppliers", k.late.partners), open: () => this.open("late", {}) });
        }
        if (k.open) {
            list.push({ key: "open", icon: "inbox", label: _t("Open purchase value"), value: compact(k.open.amount),
                money: true, cap: _t("Not yet received · %s orders", k.open.count),
                open: () => this.openOrders("open") });
        }
        return list;
    }

    get trendColumns() {
        return this.w.trend.map((m) => ({ label: deserializeDate(m.month).toFormat("MMM"), value: m.amount }));
    }

    formatDate(value) {
        return value ? deserializeDate(value).toFormat("d MMM yyyy") : "—";
    }

    // ------------------------------------------------------------ side panel

    open(name, args, crumb = _t("Procurement")) {
        this.props.openPanel({ kind: "drawer", key: `procurement.${name}`, args, crumb, sec: "procurement" });
    }

    openOrders(kind) {
        this.open("orders", kind === "purchases" ? { ...this.periodArgs, kind } : { kind });
    }

    openOrder(row) {
        this.open("order", { order_id: row.id }, _t("Waiting for approval"));
    }

    openPicking(row) {
        this.open("picking", { picking_id: row.id }, _t("Late receipts"));
    }

    /** The purchases confirmed in one month of the chart (up to the period's end). */
    openMonth(index) {
        const start = deserializeDate(this.w.trend[index].month);
        const end = start.endOf("month").startOf("day");
        const last = deserializeDate(this.props.data.period.date_to);
        this.open("orders", {
            kind: "purchases", period: "custom", date_from: start.toISODate(),
            date_to: (end < last ? end : last).toISODate(),
        });
    }
}

sectionRegistry.add("procurement", ProcurementSection);
