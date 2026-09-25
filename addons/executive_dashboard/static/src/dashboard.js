/** @odoo-module **/
import { Component, onMounted, onPatched, onWillStart, useExternalListener, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { Icon } from "./icons";
import { periodOptions, sectionInfo } from "./constants";
import { Welcome } from "./welcome";
import { SectionView } from "./section";
import { SidePanel } from "./side_panel";

const { DateTime } = luxon;
const MODEL = "executive.dashboard";

/**
 * Shell of the Executive Dashboard: navigation, top bar with the period
 * selector, Welcome, the current section and the side panel.
 *
 * Data flow: one `get_section` call per section and period. Results are kept
 * for the session (per section and period); reopening shows the kept result at
 * once and refreshes it quietly. Hovering a section prefetches it without
 * showing anything, so Welcome stays free of figures.
 */
export class ExecutiveDashboard extends Component {
    static template = "executive_dashboard.Dashboard";
    static components = { Icon, Welcome, SectionView, SidePanel };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.root = useRef("root");
        this.topbar = useRef("topbar");
        this.info = sectionInfo();
        this.periods = periodOptions();
        this.cache = new Map();
        this.inflight = new Map();
        this.seq = 0;
        const today = DateTime.local();
        this.state = useState({
            boot: null,
            page: "welcome",
            period: "month",
            customFrom: serializeDate(today.startOf("month")),
            customTo: serializeDate(today),
            data: null,
            loading: false,
            error: false,
            panel: null,
        });
        onWillStart(async () => {
            this.state.boot = await this.orm.call(MODEL, "get_bootstrap", []);
        });
        onMounted(() => this.measureTopbar());
        onPatched(() => this.measureTopbar());
        useExternalListener(window, "keydown", this.onKeydown);
        useExternalListener(window, "resize", this.measureTopbar);
    }

    // ------------------------------------------------------------ getters

    get sections() {
        return (this.state.boot?.sections || []).map((s) => ({ ...this.info[s.key], period: s.period }));
    }

    get navItems() {
        return [this.info.welcome, ...this.sections];
    }

    get current() {
        return this.sections.find((s) => s.key === this.state.page) || null;
    }

    get isWelcome() {
        return this.state.page === "welcome";
    }

    get showPeriod() {
        return Boolean(this.current?.period);
    }

    get title() {
        return this.isWelcome ? _t("Executive Dashboard") : this.current?.name;
    }

    get subtitle() {
        if (this.isWelcome) {
            return this.state.boot.company_name;
        }
        if (!this.showPeriod) {
            return _t("as of today");
        }
        const period = this.state.data?.period;
        if (!period) {
            return "";
        }
        const from = deserializeDate(period.date_from).toLocaleString(DateTime.DATE_MED);
        const to = deserializeDate(period.date_to).toLocaleString(DateTime.DATE_MED);
        return from === to ? from : `${from} – ${to}`;
    }

    // ------------------------------------------------------------ data

    cacheKey(section) {
        const s = this.info[section];
        const spec = this.sections.find((x) => x.key === section);
        if (!s || !spec?.period) {
            return `${section}|now`;
        }
        const { period, customFrom, customTo } = this.state;
        return period === "custom" ? `${section}|custom|${customFrom}|${customTo}` : `${section}|${period}`;
    }

    request(section, { refresh = false, silent = false } = {}) {
        const key = this.cacheKey(section);
        if (!refresh && this.inflight.has(key)) {
            return this.inflight.get(key);
        }
        const { period, customFrom, customTo } = this.state;
        const custom = period === "custom";
        const orm = silent ? this.orm.silent : this.orm;
        const promise = orm
            .call(MODEL, "get_section", [section, period, custom ? customFrom : null, custom ? customTo : null, refresh])
            .then((result) => {
                this.cache.set(key, result);
                return result;
            })
            .finally(() => this.inflight.delete(key));
        this.inflight.set(key, promise);
        return promise;
    }

    async load(section, { refresh = false } = {}) {
        const seq = ++this.seq;
        const cached = refresh ? null : this.cache.get(this.cacheKey(section));
        this.state.error = false;
        this.state.data = cached || null;
        this.state.loading = !cached;
        try {
            const result = await this.request(section, { refresh, silent: Boolean(cached) });
            // A newer page or period was chosen meanwhile: drop this result.
            if (seq === this.seq) {
                this.state.data = result;
            }
        } catch (error) {
            if (seq === this.seq && !cached) {
                this.state.error = true;
            }
            if (!cached) {
                throw error;
            }
        } finally {
            if (seq === this.seq) {
                this.state.loading = false;
            }
        }
    }

    prefetch(section) {
        if (section === "welcome" || this.cache.has(this.cacheKey(section))) {
            return;
        }
        this.request(section, { silent: true }).catch(() => {});
    }

    // ------------------------------------------------------------ navigation

    openPage(page) {
        if (page === this.state.page) {
            return;
        }
        this.state.panel = null;
        this.state.page = page;
        this.state.data = null;
        this.root.el?.querySelector(".ed-main")?.scrollTo({ top: 0 });
        if (page !== "welcome") {
            this.load(page);
        }
    }

    hideFigures() {
        this.cache.clear();
        this.openPage("welcome");
    }

    setPeriod(key) {
        this.state.period = key;
        if (!this.isWelcome && this.showPeriod) {
            this.load(this.state.page);
        }
    }

    onCustomDate(which, ev) {
        const value = ev.target.value;
        if (!value) {
            return;
        }
        this.state[which] = value;
        if (this.state.customFrom <= this.state.customTo) {
            this.load(this.state.page);
        }
    }

    refresh() {
        if (!this.isWelcome) {
            this.load(this.state.page, { refresh: true });
        }
    }

    openSettings() {
        this.action.doAction("executive_dashboard.action_settings");
    }

    // ------------------------------------------------------------ side panel

    openPanel(panel) {
        this.state.panel = panel;
    }

    closePanel() {
        this.state.panel = null;
    }

    openRecord(model, id) {
        this.state.panel = null;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ------------------------------------------------------------ events

    onKeydown(ev) {
        if (ev.key === "Escape" && this.state.panel) {
            this.closePanel();
        } else if (ev.key === "/" && !/INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName || "")
            && !document.activeElement?.isContentEditable) {
            ev.preventDefault();
            this.openPanel({ kind: "search" });
        }
    }

    measureTopbar() {
        const bar = this.topbar.el;
        if (bar && this.root.el) {
            this.root.el.style.setProperty("--tbh", `${bar.offsetHeight}px`);
        }
    }
}

registry.category("actions").add("executive_dashboard.dashboard", ExecutiveDashboard);
