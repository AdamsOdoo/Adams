/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { deserializeDate } from "@web/core/l10n/dates";
import { sectionRegistry } from "../section";
import { Icon } from "../icons";
import { ColumnChart } from "../widgets/charts";
import { avatar, compact, periodLabel, whole } from "../widgets/format";

/**
 * CRM: open and weighted pipeline, new leads, won; pipeline by stage and by
 * salesperson; the open opportunities closing soonest. Stages, people and
 * opportunities open their records in the side panel.
 */
export class CrmSection extends Component {
    static template = "executive_dashboard.CrmSection";
    static components = { Icon, ColumnChart };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.compact = compact;
        this.whole = whole;
        this.avatar = avatar;
        this.labels = {
            opportunity: _t("Opportunity"), customer: _t("Customer"), revenue: _t("Expected revenue"),
            probability: _t("Probability"), closing: _t("Closing"), salesperson: _t("Salesperson"),
        };
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

    get kpis() {
        const k = this.w.kpis;
        return [
            { key: "pipeline", icon: "target", label: _t("Open pipeline"), value: compact(k.pipeline), money: true,
              cap: _t("%s opportunities · as of today", k.opportunities), open: () => this.open("pipeline", {}) },
            { key: "weighted", icon: "scale", label: _t("Weighted pipeline"), value: compact(k.weighted), money: true,
              cap: _t("By probability"), open: () => this.open("pipeline", {}) },
            { key: "leads", icon: "spark", label: _t("New leads"), value: whole(k.new_leads), money: false,
              cap: periodLabel(this.props.data.period), open: () => this.openList("leads") },
            { key: "won", icon: "trophy", label: _t("Won"), value: compact(k.won), money: true,
              cap: _t("%s opportunities", k.won_count), open: () => this.openList("won") },
        ];
    }

    get stageColumns() {
        return this.w.stages.map((s) => ({ label: s.name, value: s.amount }));
    }

    formatDate(value) {
        return value ? deserializeDate(value).toFormat("d MMM") : "—";
    }

    // ------------------------------------------------------------ side panel

    open(name, args, crumb = _t("CRM")) {
        this.props.openPanel({ kind: "drawer", key: `crm.${name}`, args, crumb, sec: "crm" });
    }

    openList(kind, extra = {}) {
        this.open("list", { ...this.periodArgs, kind, ...extra });
    }

    openStage(stage) {
        this.openList("stage", { stage_id: stage.id });
    }

    openLead(row) {
        this.open("opportunity", { lead_id: row.id }, _t("Closing soonest"));
    }
}

sectionRegistry.add("crm", CrmSection);
