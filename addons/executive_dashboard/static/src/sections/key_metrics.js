/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { formatFloat } from "@web/core/utils/numbers";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { DonutChart } from "../widgets/charts";
import { compact, percent, whole } from "../widgets/format";

// The donut colours the five largest channels; the rest fold into one "Other" slice.
const PIE_MAX = 5;
// Rows of the channel table before "Show more".
const TABLE_ROWS = 10;

/**
 * Key metrics: net sales by channel, gross profit %, working capital, OTIF and ROAS for
 * the period (working capital at the period's end). Every figure, tile, slice and table
 * row opens its detail in the side panel, as on the approved mockup.
 */
export class KeyMetricsSection extends Component {
    static template = "executive_dashboard.KeyMetricsSection";
    static components = { Icon, DonutChart };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.compact = compact;
        this.whole = whole;
        this.state = useState({ rows: TABLE_ROWS });
    }

    get w() {
        return this.props.data.widgets;
    }

    get currency() {
        return this.w.currency.name;
    }

    get periodArgs() {
        const { key, date_from, date_to } = this.props.data.period;
        return { period: key, date_from, date_to };
    }

    pct(value) {
        return value === null || value === undefined ? "—" : formatFloat(value, { digits: [false, 1] }) + "%";
    }

    times(value) {
        return value === null || value === undefined ? "—" : formatFloat(value, { digits: [false, 2] }) + "×\u200e"; // the mark keeps × after the number in RTL
    }

    /** "26 Sep 2026": the balance date of the working capital (the period's end, never after today). */
    get asOf() {
        return deserializeDate(this.w.working_capital.as_of).toFormat("d MMM yyyy");
    }

    get kpis() {
        const { net_sales: net, gross_profit: gp, working_capital: wc, otif, roas } = this.w;
        const list = [
            { key: "net", icon: "coin", label: _t("Net sales"), value: compact(net.total), money: true,
              cap: _t("Excluding VAT"), open: () => this.open("net_sales") },
            { key: "gp", icon: "percent", label: _t("Gross profit %"), value: this.pct(gp.percent),
              cap: _t("Gross profit %s", compact(gp.gross_profit)), open: () => this.open("gross_profit") },
            { key: "wc", icon: "scale", label: _t("Working capital"), value: compact(wc.total), money: true,
              cap: _t("As of %s", this.asOf), open: () => this.open("working_capital") },
        ];
        if (otif) {
            list.push({ key: "otif", icon: "truck", label: _t("OTIF"), value: this.pct(otif.percent),
                        cap: _t("%(ok)s / %(due)s orders", { ok: otif.ok, due: otif.due }), open: () => this.open("otif") });
        }
        list.push({ key: "roas", icon: "megaphone", label: _t("ROAS"), value: this.times(roas.roas),
                    cap: roas.accounts ? _t("Ad spend %s", compact(roas.spend)) : _t("No advertising accounts chosen"),
                    open: () => this.open("roas") });
        if (wc.inventory !== null) {
            list.push({ key: "inv", icon: "box", label: _t("Inventory at cost"), value: compact(wc.inventory), money: true,
                        cap: _t("As of %s", this.asOf), open: () => this.open("inventory") });
        }
        return list;
    }

    // ------------------------------------------------------------ net sales by channel

    /** Channels with their colour: the five largest named channels in order, the rest grey. */
    get channels() {
        const named = this.w.net_sales.channels.filter((c) => c.id !== false);
        const total = this.w.net_sales.total;
        return this.w.net_sales.channels.map((c) => {
            const rank = c.id === false ? -1 : named.indexOf(c);
            return {
                ...c,
                key: c.id === false ? "none" : c.id,
                color: rank >= 0 && rank < PIE_MAX && c.net > 0 ? `var(--p${rank + 1})` : "var(--p0)",
                share: percent(c.net, total),
            };
        });
    }

    /** Column names, also shown next to each value when the table stacks on narrow screens. */
    get labels() {
        return { channel: _t("Channel"), invoiced: _t("Invoiced"), refunds: _t("Credit notes"),
                 net: _t("Net sales"), share: _t("Share") };
    }

    get shownChannels() {
        return this.channels.slice(0, this.state.rows);
    }

    showMoreChannels() {
        this.state.rows += TABLE_ROWS;
    }

    get slices() {
        const channels = this.channels.filter((c) => c.net > 0);
        const named = channels.filter((c) => c.id !== false);
        const top = named.slice(0, PIE_MAX);
        const rest = channels.filter((c) => !top.includes(c));
        const items = top.map((c) => ({ label: c.name, value: c.net, text: whole(c.net), color: c.color, channel: c }));
        if (rest.length) {
            const value = rest.reduce((s, c) => s + c.net, 0);
            items.push({ label: rest.length === 1 ? rest[0].name : _t("Other (%s)", rest.length), value,
                         text: whole(value), color: "var(--p0)", channel: rest.length === 1 ? rest[0] : null });
        }
        return items;
    }

    selectSlice(index) {
        const channel = this.slices[index]?.channel;
        if (channel) {
            this.openChannel(channel);
        } else {
            this.open("net_sales");
        }
    }

    openChannel(channel) {
        this.open("channel", { source_id: channel.id }, _t("Net sales by channel"));
    }

    // ------------------------------------------------------------ OTIF

    get otifTiles() {
        const o = this.w.otif;
        return [
            { kind: "ok", count: o.ok, label: _t("On time and in full"), cls: "good" },
            { kind: "not_full", count: o.not_full, label: _t("On time, not in full"), cls: "warn" },
            { kind: "late", count: o.late, label: _t("In full, late"), cls: "warn" },
            { kind: "both", count: o.both, label: _t("Late and not in full"), cls: "crit" },
        ];
    }

    // ------------------------------------------------------------ working capital

    get wcTiles() {
        const wc = this.w.working_capital;
        const tiles = [
            { key: "cash", sub: _t("Bank and Cash Accounts"), value: wc.cash, label: _t("Available cash"),
              cat: _t("Asset"), cls: "sec", open: () => this.open("bank_cash") },
        ];
        if (wc.inventory !== null) {
            tiles.push({ key: "inv", sub: _t("Stock valuation"), value: wc.inventory, label: _t("Inventory at cost"),
                         cat: _t("Asset"), cls: "sec", open: () => this.open("inventory") });
        }
        tiles.push(
            { key: "recv", sub: _t("Open customer invoices"), value: wc.receivables, label: _t("Accounts receivable"),
              cat: _t("Asset"), cls: "sec", open: () => this.open("open_items", { kind: "receivables", view: "aged" }) },
            { key: "pay", sub: _t("Open vendor bills"), value: wc.payables, label: _t("Accounts payable"),
              cat: _t("Liability"), cls: "warn", open: () => this.open("open_items", { kind: "payables", view: "aged" }) },
        );
        return tiles;
    }

    // ------------------------------------------------------------ side panel

    open(name, args = {}, crumb = _t("Key metrics")) {
        this.props.openPanel({ kind: "drawer", key: `key_metrics.${name}`, args: { ...this.periodArgs, ...args },
                               crumb, sec: "key_metrics" });
    }
}

sectionRegistry.add("key_metrics", KeyMetricsSection);
