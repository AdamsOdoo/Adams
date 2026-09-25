/** @odoo-module **/
import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { compact, whole } from "../widgets/format";

const MODEL = "executive.dashboard";
const SEARCH_DELAY = 300;

/**
 * Stock report: on-hand stock by product and warehouse. Filters, the "Hide zero
 * and negative stock" checkbox and paging are sent to the server, which returns
 * one page and the number of lines; the first page comes with the section.
 */
export class StockReport extends Component {
    static template = "executive_dashboard.StockReport";
    static components = { Icon };
    static props = { stock: Object, currency: String, openPanel: Function };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.whole = whole;
        this.seq = 0;
        const { filters } = this.props.stock;
        // Filters and page kept when the user left for a native screen and came back.
        const kept = this.env.edRecall?.("stock");
        this.state = useState(kept ? { ...kept, loading: false } : {
            data: this.props.stock, loading: false, ...filters,
            // Select values are strings.
            warehouse_id: filters.warehouse_id ? `${filters.warehouse_id}` : "",
            category_id: filters.category_id ? `${filters.category_id}` : "" });
        this.env.edRemember?.("stock", () => ({ ...this.state }));
        if (kept && !kept.data) {
            // Back from the browser's Back button: filters only, so load the first page with them.
            this.state.data = this.props.stock;
            this.load(0);
        }
        this.labels = {
            ref: _t("Reference"), product: _t("Product"), warehouse: _t("Warehouse"), onHand: _t("On hand"),
            reserved: _t("Reserved"), available: _t("Available"), unit: _t("Unit"), value: _t("Value"),
        };
        // A section refresh brings a new first page: keep the user's filters and page.
        onWillUpdateProps((next) => {
            if (next.stock !== this.props.stock) {
                this.load(this.state.data.page);
            }
        });
        onWillUnmount(() => clearTimeout(this.timer));
    }

    get args() {
        const s = this.state;
        return {
            warehouse_id: s.warehouse_id ? Number(s.warehouse_id) : false,
            category_id: s.category_id ? Number(s.category_id) : false,
            query: s.query, hide: s.hide,
        };
    }

    get range() {
        const { count, page, per } = this.state.data;
        return { from: count ? page * per + 1 : 0, to: Math.min(count, (page + 1) * per), count };
    }

    get lastPage() {
        const { count, per } = this.state.data;
        return Math.max(0, Math.ceil(count / per) - 1);
    }

    async load(page = 0) {
        const seq = ++this.seq;
        this.state.loading = true;
        try {
            const data = await this.orm.call(MODEL, "get_drawer", ["inventory.stock", { ...this.args, page }]);
            if (seq === this.seq) {
                this.state.data = data;
            }
        } finally {
            if (seq === this.seq) {
                this.state.loading = false;
            }
        }
    }

    onSelect(field, ev) {
        this.state[field] = ev.target.value;
        this.load();
    }

    onHide(ev) {
        this.state.hide = ev.target.checked;
        this.load();
    }

    onQuery(ev) {
        this.state.query = ev.target.value;
        clearTimeout(this.timer);
        this.timer = setTimeout(() => this.load(), SEARCH_DELAY);
    }

    /** Split `text` around case-insensitive matches of the search for <mark>. */
    highlight(text) {
        const q = this.state.data.filters.query.toLowerCase();
        const parts = [];
        const lower = (text || "").toLowerCase();
        let at = 0;
        let i = q ? lower.indexOf(q) : -1;
        while (i >= 0) {
            if (i > at) {
                parts.push({ text: text.slice(at, i), mark: false });
            }
            parts.push({ text: text.slice(i, i + q.length), mark: true });
            at = i + q.length;
            i = lower.indexOf(q, at);
        }
        if (at < (text || "").length) {
            parts.push({ text: text.slice(at), mark: false });
        }
        return parts;
    }

    /** Odoo's stock list with the same warehouse, category and search filters. */
    async openInOdoo() {
        await this.action.doAction(await this.orm.call(MODEL, "open_action", ["inventory.stock", this.args]));
    }

    openProduct(row) {
        this.props.openPanel({ kind: "drawer", key: "inventory.product", args: { product_id: row.product_id },
                               crumb: _t("Stock report"), sec: "inventory" });
    }
}

/**
 * Inventory: inventory value, late deliveries, deliveries and receipts due
 * today; delivery and receipt tiles (late, today, next 7 days, waiting); the
 * stock report. Current position only (no period).
 */
export class InventorySection extends Component {
    static template = "executive_dashboard.InventorySection";
    static components = { Icon, StockReport };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.compact = compact;
        this.whole = whole;
    }

    get w() {
        return this.props.data.widgets;
    }

    get currency() {
        return this.w.currency.name;
    }

    get kpis() {
        const k = this.w.kpis;
        const list = [];
        if (k.value) {
            list.push({ key: "value", icon: "box", label: _t("Inventory value"), value: compact(k.value.amount),
                money: true, cap: _t("As of today"), open: () => this.w.stock.can_open && this.openStock() });
        }
        list.push(
            { key: "late", icon: "truck", label: _t("Late deliveries"), value: whole(k.late.count),
              cap: k.late.count ? _t("Oldest %s days", k.late.oldest) : _t("Scheduled before today"),
              open: () => this.openPickings("outgoing", "late") },
            { key: "today", icon: "cal", label: _t("Deliveries due today"), value: whole(k.today.count),
              cap: _t("%s ready", k.today.ready), open: () => this.openPickings("outgoing", "today") },
            { key: "receipts", icon: "inbox", label: _t("Receipts due today"), value: whole(k.receipts.count),
              cap: _t("From %s suppliers", k.receipts.partners), open: () => this.openPickings("incoming", "today") },
        );
        return list;
    }

    tiles(code) {
        const t = this.w[code === "outgoing" ? "deliveries" : "receipts"];
        return [
            { bucket: "late", count: t.late, label: _t("Late"), cls: "crit" },
            { bucket: "today", count: t.today, label: _t("Due today"), cls: "sec" },
            { bucket: "week", count: t.week, label: _t("Next 7 days"), cls: "" },
            { bucket: "waiting", count: t.waiting, label: code === "outgoing" ? _t("Waiting for stock") : _t("Waiting"),
              cls: "warn" },
        ];
    }

    open(name, args) {
        this.props.openPanel({ kind: "drawer", key: `inventory.${name}`, args, crumb: _t("Inventory"), sec: "inventory" });
    }

    openPickings(code, bucket) {
        this.open("pickings", { code, bucket });
    }

    /** Odoo's stock list (valued locations of the current companies). */
    async openStock() {
        await this.action.doAction(await this.orm.call(MODEL, "open_action", ["inventory.stock", {}]));
    }
}

sectionRegistry.add("inventory", InventorySection);
