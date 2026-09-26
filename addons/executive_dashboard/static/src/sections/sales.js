/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { formatFloat } from "@web/core/utils/numbers";
import { sectionRegistry } from "../section";
import { drawerRegistry } from "../side_panel";
import { Icon } from "../icons";
import { LineChart } from "../widgets/charts";
import { compact, deliveryChip, periodLabel, whole } from "../widgets/format";

/**
 * Sales: four figures, invoiced sales by month, salespeople, top products by
 * quantity, top customers by payments, recent orders with the order's own
 * Delivery Status, and recent quotations. A widget whose app is missing arrives
 * as null and is left out.
 */
export class SalesSection extends Component {
    static template = "executive_dashboard.SalesSection";
    static components = { Icon, LineChart };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.compact = compact;
        this.whole = whole;
        this.deliveryChip = deliveryChip;
        // Column names repeated on each card at phone width.
        this.labels = {
            ref: _t("Reference"), customer: _t("Customer"), date: _t("Date"), value: _t("Value"),
            delivery: _t("Delivery Status"), validity: _t("Expiration"), status: _t("Status"),
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
        const list = [];
        if (k.invoiced) {
            list.push({ key: "invoiced", icon: "doc", label: _t("Invoiced sales"), value: k.invoiced.amount,
                cap: _t("%s invoices", k.invoiced.count), open: () => this.open("invoices", this.periodArgs) });
        }
        list.push(
            { key: "orders", icon: "check", label: _t("Confirmed orders"), value: k.orders.amount,
              cap: _t("%s orders", k.orders.count), open: () => this.openOrders("orders") },
            { key: "quotes", icon: "inbox", label: _t("Open quotations"), value: k.quotations.amount,
              cap: _t("%s quotations · as of today", k.quotations.count), open: () => this.openOrders("quotations") },
            { key: "toinv", icon: "coin", label: _t("Orders to invoice"), value: k.to_invoice.amount,
              cap: _t("%s orders · as of today", k.to_invoice.count), open: () => this.openOrders("to_invoice") },
        );
        return list;
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
            series: [{ name: _t("Invoiced sales"), values: months.map((m) => m.amount), color: "var(--sec)", area: true }],
            partial: this.w.trend.partial,
        };
    }

    formatDate(value) {
        return deserializeDate(value).toFormat("d MMM");
    }

    // ------------------------------------------------------------ side panel

    open(name, args, crumb = _t("Sales")) {
        this.props.openPanel({ kind: "drawer", key: `sales.${name}`, args, crumb, sec: "sales" });
    }

    openOrders(kind) {
        this.open("orders", { ...this.periodArgs, kind });
    }

    openOrder(row) {
        this.open("order", { order_id: row.id }, _t("Recent orders"));
    }

    openQuotation(row) {
        this.open("order", { order_id: row.id }, _t("Recent quotations"));
    }
}

/**
 * Side panel of one order or quotation: its details, Delivery Status and
 * Invoice Status as Odoo stores them, and its lines (ordered, delivered,
 * invoiced). "Deliveries" lists its delivery orders in a nested panel.
 */
export class SalesOrderDrawer extends Component {
    static template = "executive_dashboard.SalesOrderDrawer";
    static components = { Icon };
    static props = { data: { type: [Object, { value: null }], optional: true }, open: Function, panel: Object };

    setup() {
        this.deliveryChip = deliveryChip;
        this.whole = whole;
        this.labels = { product: _t("Product"), ordered: _t("Ordered"), delivered: _t("Delivered"),
                        invoiced: _t("Invoiced") };
    }

    formatDate(value) {
        return value ? deserializeDate(value).toFormat("d MMM yyyy") : "—";
    }

    quantity(value) {
        return formatFloat(value, { digits: [false, 2] });
    }

    invoiceChip(status) {
        return { invoiced: "good", "to invoice": "warn", upselling: "info" }[status] || "neutral";
    }

    openDeliveries() {
        const { panel } = this.props;
        this.props.open({ kind: "drawer", key: "sales.deliveries", args: panel.args, crumb: this.props.data.title,
                          sec: panel.sec, back: panel });
    }
}

sectionRegistry.add("sales", SalesSection);
drawerRegistry.add("sales.order", SalesOrderDrawer);
