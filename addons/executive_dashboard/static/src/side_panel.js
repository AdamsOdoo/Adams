/** @odoo-module **/
import { Component, onWillStart, onWillUnmount, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Icon } from "./icons";

const MODEL = "executive.dashboard";
const SEARCH_DELAY = 250;

/** Custom side-panel bodies, keyed like the drawer (`<section>.<name>`). */
export const drawerRegistry = registry.category("executive_dashboard.drawers");

/**
 * Side panel. `panel` is null (closed), `{ kind: "search" }`, or
 * `{ kind: "drawer", key: "<section>.<name>", args, crumb, back }` whose
 * content comes from `get_drawer` when it opens. The generic body shows
 * `rows` (each may open a nested drawer, or a native screen through its own
 * `action`), an optional `total` and a button to the native screen when the
 * drawer names an `action`. The server keeps an `action` only when the user may
 * open that screen; its `kind` names the button: Open record, Open list or
 * Open report.
 */
export class SidePanel extends Component {
    static template = "executive_dashboard.SidePanel";
    static components = { Icon };
    static props = {
        panel: { type: [Object, { value: null }], optional: true },
        close: Function,
        open: Function,
        openRecord: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.drawerEl = useRef("drawer");
        this.searchInput = useRef("searchInput");
        this.closeBtn = useRef("closeBtn");
        this.seq = 0;
        this.state = useState({ data: null, loading: false, query: "", results: null, searching: false });
        // A panel restored from the breadcrumb (coming back from a native screen) loads at once.
        onWillStart(() => this.props.panel && this.reset(this.props.panel));
        onWillUpdateProps((next) => {
            if (next.panel !== this.props.panel) {
                this.reset(next.panel);
            }
        });
        useEffect(
            (panel) => {
                if (panel) {
                    (panel.kind === "search" ? this.searchInput.el : this.closeBtn.el)?.focus();
                    this.drawerEl.el.querySelector(".ed-drawer-body")?.scrollTo({ top: 0 });
                }
            },
            () => [this.props.panel]
        );
        onWillUnmount(() => clearTimeout(this.timer));
    }

    get isOpen() {
        return Boolean(this.props.panel);
    }

    get customBody() {
        const key = this.props.panel?.key;
        return key ? drawerRegistry.get(key, null) : null;
    }

    reset(panel) {
        const seq = ++this.seq;
        clearTimeout(this.timer);
        Object.assign(this.state, { data: null, loading: false, query: "", results: null, searching: false });
        if (panel?.kind === "drawer") {
            this.state.loading = true;
            this.orm.call(MODEL, "get_drawer", [panel.key, panel.args || {}]).then(
                (data) => {
                    if (seq === this.seq) {
                        Object.assign(this.state, { data, loading: false });
                    }
                },
                (error) => {
                    if (seq === this.seq) {
                        this.state.loading = false;
                    }
                    throw error;
                }
            );
        }
    }

    // ------------------------------------------------------------ search

    onSearchInput(ev) {
        const query = ev.target.value;
        this.state.query = query;
        clearTimeout(this.timer);
        if (query.trim().length < 2) {
            this.state.results = null;
            return;
        }
        this.timer = setTimeout(() => this.runSearch(query), SEARCH_DELAY);
    }

    async runSearch(query) {
        const seq = ++this.seq;
        this.state.searching = true;
        const results = await this.orm.call(MODEL, "global_search", [query]);
        if (seq === this.seq) {
            Object.assign(this.state, { results, searching: false });
        }
    }

    /** Split `text` around case-insensitive matches of the query for <mark>. */
    highlight(text) {
        const q = this.state.query.trim().toLowerCase();
        const parts = [];
        const lower = text.toLowerCase();
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
        if (at < text.length) {
            parts.push({ text: text.slice(at), mark: false });
        }
        return parts;
    }

    // ------------------------------------------------------------ actions

    /** Button label of a native screen: `kind` is record, list or report. */
    openLabel(kind) {
        return { record: _t("Open record"), report: _t("Open report") }[kind] || _t("Open list");
    }

    async openTarget(target) {
        if (target) {
            const action = await this.orm.call(MODEL, "open_action", [target.key, target.args || {}]);
            // The panel stays open: the breadcrumb brings the user back to it.
            await this.action.doAction(action);
        }
    }

    openNative() {
        return this.openTarget(this.state.data?.action);
    }

    openRow(row) {
        if (row.open) {
            this.props.open({ kind: "drawer", sec: this.props.panel.sec, ...row.open, back: this.props.panel });
        } else if (row.action) {
            this.openTarget(row.action);
        }
    }

    onKeydown(ev) {
        if (ev.key !== "Tab") {
            return;
        }
        const focusable = [...this.drawerEl.el.querySelectorAll("button, input, [tabindex]:not([tabindex='-1'])")]
            .filter((el) => !el.disabled && el.offsetParent !== null);
        if (!focusable.length) {
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (ev.shiftKey && document.activeElement === first) {
            ev.preventDefault();
            last.focus();
        } else if (!ev.shiftKey && document.activeElement === last) {
            ev.preventDefault();
            first.focus();
        }
    }
}
