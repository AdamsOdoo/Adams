/** @odoo-module **/
import { Component, onMounted, onPatched, onWillStart, toRaw, useExternalListener, useRef, useState, useSubEnv } from "@odoo/owl";
import { useSetupAction } from "@web/search/action_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { serializeDate } from "@web/core/l10n/dates";
import { Icon } from "./icons";
import { periodOptions, sectionInfo } from "./constants";
import { Welcome } from "./welcome";
import { SectionView } from "./section";
import { SidePanel } from "./side_panel";

const { DateTime } = luxon;
const MODEL = "executive.dashboard";
// Where the user was, kept in this browser tab for the browser's Back button (the
// breadcrumb state covers Odoo's own breadcrumbs). No figures are stored.
const RETURN_KEY = "executive_dashboard.return";
const RETURN_MINUTES = 10;

function takeReturn() {
    try {
        const kept = JSON.parse(sessionStorage.getItem(RETURN_KEY) || "null");
        sessionStorage.removeItem(RETURN_KEY);
        return kept && Date.now() - kept.at < RETURN_MINUTES * 60000 ? kept : null;
    } catch {
        return null;
    }
}

/**
 * Shell of the Executive Dashboard: navigation, top bar with the period
 * selector, Welcome, the current section and the side panel.
 *
 * Data flow: one `get_section` call per section and period. Results are kept
 * for the session (per section and period); reopening shows the kept result at
 * once and refreshes it quietly. Hovering a section prefetches it without
 * showing anything, so Welcome stays free of figures.
 *
 * Leaving for a native screen (a report, a list, a record) keeps the page, period,
 * dates, open side panel, scroll position, section results and table filters in
 * the action's breadcrumb state; coming back restores them as they were.
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
        const saved = this.props.state?.executiveDashboard || takeReturn();
        this.pendingScroll = saved ? saved.scroll || 0 : null;
        this.cache = new Map(saved?.cache || []);
        // Table filters and pages kept by the sections (stock report, directory).
        this.memory = { ...(saved?.memory || {}) };
        this.keepers = {};
        useSubEnv({
            edRecall: (key) => this.memory[key],
            edRemember: (key, snapshot) => { this.keepers[key] = snapshot; },
        });
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
            // Dates of the figures on screen, shown read-only unless the period is Custom.
            shownFrom: null,
            shownTo: null,
        });
        if (saved) {
            Object.assign(this.state, saved.view);
        }
        useSetupAction({ getLocalState: () => ({ executiveDashboard: this.exportState() }) });
        onWillStart(async () => {
            this.state.boot = await this.orm.call(MODEL, "get_bootstrap", []);
            if (saved && !this.isWelcome) {
                // Coming back: the kept result is on screen from the first render.
                this.state.data = this.cache.get(this.cacheKey(this.state.page)) || null;
            }
        });
        onMounted(() => {
            this.measureTopbar();
            if (saved && !this.isWelcome) {
                // Kept result at once (breadcrumb) and refreshed quietly; then back to where the user was.
                this.restoreScroll();
                this.load(this.state.page).catch(() => {});
            }
        });
        onPatched(() => {
            this.measureTopbar();
            this.restoreScroll();
        });
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
        return this.periods.find((p) => p.key === this.state.period)?.label || "";
    }

    get customHint() {
        return _t("Choose Custom to change the dates");
    }

    get isCustom() {
        return this.state.period === "custom";
    }

    /** Values of the date fields: the Custom dates, else the dates of the figures on screen. */
    get dateFrom() {
        return this.isCustom ? this.state.customFrom : this.state.shownFrom || "";
    }

    get dateTo() {
        return this.isCustom ? this.state.customTo : this.state.shownTo || "";
    }

    showDates(result) {
        const period = result?.period;
        if (period?.date_from && period?.date_to) {
            this.state.shownFrom = period.date_from;
            this.state.shownTo = period.date_to;
        }
    }

    // ------------------------------------------------------------ breadcrumb state

    restoreScroll() {
        if (this.pendingScroll !== null && this.state.data) {
            this.root.el?.querySelector(".ed-main")?.scrollTo({ top: this.pendingScroll });
            this.pendingScroll = null;
        }
    }

    exportState() {
        const { page, period, customFrom, customTo, panel, shownFrom, shownTo } = this.state;
        for (const [key, snapshot] of Object.entries(this.keepers)) {
            this.memory[key] = snapshot();
        }
        const kept = {
            view: { page, period, customFrom, customTo, shownFrom, shownTo,
                    panel: panel ? JSON.parse(JSON.stringify(toRaw(panel))) : null },
            scroll: this.root.el?.querySelector(".ed-main")?.scrollTop || 0,
            memory: this.memory,
        };
        if (page !== "welcome") {
            try {
                // Filters only: table pages carry figures, so they are left out.
                const memory = Object.fromEntries(Object.entries(this.memory).map(
                    ([key, { data, loading, ...filters }]) => [key, filters]));
                sessionStorage.setItem(RETURN_KEY, JSON.stringify({ ...kept, memory, at: Date.now() }));
            } catch {
                // Storage unavailable: the breadcrumb still brings the user back.
            }
        }
        return { ...kept, cache: [...this.cache.entries()] };
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
        this.showDates(cached);
        try {
            const result = await this.request(section, { refresh, silent: Boolean(cached) });
            // A newer page or period was chosen meanwhile: drop this result.
            if (seq === this.seq) {
                this.state.data = result;
                this.showDates(result);
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
        try {
            sessionStorage.removeItem(RETURN_KEY);
        } catch {
            // Nothing kept.
        }
        this.openPage("welcome");
    }

    setPeriod(key) {
        if (key === "custom" && !this.isCustom && this.state.shownFrom) {
            // Start from the dates on screen, so choosing Custom changes nothing until edited.
            this.state.customFrom = this.state.shownFrom;
            this.state.customTo = this.state.shownTo;
        }
        this.state.period = key;
        if (!this.isWelcome && this.showPeriod) {
            this.load(this.state.page);
        }
    }

    onCustomDate(which, ev) {
        const value = ev.target.value;
        if (!value || !this.isCustom) {
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
        // A drawer stays open for the way back; a search result closes the search.
        if (this.state.panel?.kind === "search") {
            this.state.panel = null;
        }
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
