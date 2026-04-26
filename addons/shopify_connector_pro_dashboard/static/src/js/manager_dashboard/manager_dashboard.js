/** @odoo-module **/

import { Component, onWillStart, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

const PERIODS = [
    { key: "today", label: "Today" },
    { key: "wtd", label: "Week" },
    { key: "mtd", label: "Month" },
    { key: "ytd", label: "Year" },
    { key: "last_30", label: "30 days" },
    { key: "last_90", label: "90 days" },
];

export class ShopifyManagerDashboard extends Component {
    static template = "shopify_manager_dashboard.Main";
    static components = {};
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chartRef = useRef("trendChart");
        this.deliveriesChartRef = useRef("deliveriesChart");
        this._chart = null;
        this._deliveriesChart = null;

        this.state = useState({
            loading: true,
            periods: PERIODS,
            period: "mtd",
            backendIds: [],
            data: null,
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.refresh();
        });

        onMounted(() => this._renderCharts());
        onWillUnmount(() => this._destroyCharts());
    }

    async refresh() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "shopify.manager.dashboard",
                "get_data",
                [],
                { backend_ids: this.state.backendIds, period: this.state.period },
            );
            this.state.data = data;
            if (!this.state.backendIds.length && data.selected_backend_ids?.length) {
                this.state.backendIds = data.selected_backend_ids;
            }
        } finally {
            this.state.loading = false;
        }
        this._renderCharts();
    }

    async onPeriodChange(period) {
        this.state.period = period;
        await this.refresh();
    }

    async onBackendToggle(ev) {
        const id = parseInt(ev.target.value, 10);
        if (ev.target.checked) {
            if (!this.state.backendIds.includes(id)) {
                this.state.backendIds = [...this.state.backendIds, id];
            }
        } else {
            this.state.backendIds = this.state.backendIds.filter((b) => b !== id);
        }
        await this.refresh();
    }

    async onBackendAll() {
        this.state.backendIds = (this.state.data?.backends || []).map((b) => b.id);
        await this.refresh();
    }

    // ---------- Formatting helpers ----------

    formatCurrency(value) {
        const c = this.state.data?.currency || { symbol: "", position: "before", decimal_places: 2 };
        const n = Number(value || 0).toFixed(c.decimal_places);
        return c.position === "after" ? `${n} ${c.symbol}` : `${c.symbol}${n}`;
    }

    formatNumber(value) {
        return Number(value || 0).toLocaleString();
    }

    formatPct(value) {
        return `${Number(value || 0).toFixed(1)}%`;
    }

    deltaClass(delta) {
        if (delta > 0.5) return "o_smd_delta_up";
        if (delta < -0.5) return "o_smd_delta_down";
        return "o_smd_delta_flat";
    }

    deltaArrow(delta) {
        if (delta > 0.5) return "↑";
        if (delta < -0.5) return "↓";
        return "→";
    }

    // ---------- Drill-down click handlers ----------

    _backendDomain() {
        const ids = this.state.backendIds;
        return ids && ids.length ? [["shopify_bind_ids.backend_id", "in", ids]] : [];
    }

    openOrders() {
        const domain = [
            ...this._backendDomain(),
            ["date_order", ">=", this.state.data.date_from],
            ["date_order", "<", this.state.data.date_to],
            ["state", "in", ["sale", "done"]],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Shopify orders",
            res_model: "sale.order",
            domain,
            views: [[false, "list"], [false, "form"]],
        });
    }

    openPickings(stateFilter) {
        const ids = this.state.backendIds;
        const domain = [
            ["sale_id.shopify_bind_ids.backend_id", "in", ids],
            ["picking_type_code", "=", "outgoing"],
        ];
        if (stateFilter === "unfulfilled") {
            domain.push(["state", "in", ["waiting", "confirmed"]]);
        } else if (stateFilter === "ready") {
            domain.push(["state", "=", "assigned"]);
        } else if (stateFilter === "shipped") {
            domain.push(["state", "=", "done"]);
        } else if (stateFilter === "shipped_today") {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const iso = today.toISOString().slice(0, 19).replace("T", " ");
            domain.push(["state", "=", "done"], ["date_done", ">=", iso]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Deliveries",
            res_model: "stock.picking",
            domain,
            views: [[false, "list"], [false, "form"]],
        });
    }

    openCarts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Abandoned carts",
            res_model: "shopify.abandoned.cart",
            domain: [
                ["backend_id", "in", this.state.backendIds],
                ["abandoned_at", ">=", this.state.data.date_from],
                ["abandoned_at", "<", this.state.data.date_to],
            ],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openRefunds() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Refunds",
            res_model: "shopify.refund.binding",
            domain: [
                ["backend_id", "in", this.state.backendIds],
                ["create_date", ">=", this.state.data.date_from],
                ["create_date", "<", this.state.data.date_to],
            ],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openPayouts(status) {
        const domain = [["backend_id", "in", this.state.backendIds]];
        if (status) {
            domain.push(["status", "=", status]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Payouts",
            res_model: "shopify.payout",
            domain,
            views: [[false, "list"], [false, "form"]],
        });
    }

    openProduct(productId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "product.product",
            res_id: productId,
            views: [[false, "form"]],
        });
    }

    openCustomer(partnerId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
    }

    // ---------- Charts ----------

    _destroyCharts() {
        if (this._chart) {
            this._chart.destroy();
            this._chart = null;
        }
        if (this._deliveriesChart) {
            this._deliveriesChart.destroy();
            this._deliveriesChart = null;
        }
    }

    _renderCharts() {
        if (!this.state.data || typeof Chart === "undefined") return;
        this._destroyCharts();
        this._renderTrendChart();
        this._renderDeliveriesChart();
    }

    _renderTrendChart() {
        const canvas = this.chartRef.el;
        if (!canvas) return;
        const trend = this.state.data.trend || [];
        this._chart = new Chart(canvas.getContext("2d"), {
            data: {
                labels: trend.map((p) => p.date),
                datasets: [
                    {
                        type: "line",
                        label: "Revenue",
                        data: trend.map((p) => p.revenue),
                        borderColor: "#00a09d",
                        backgroundColor: "rgba(0, 160, 157, 0.1)",
                        tension: 0.25,
                        yAxisID: "y",
                        fill: true,
                    },
                    {
                        type: "bar",
                        label: "Orders",
                        data: trend.map((p) => p.orders),
                        backgroundColor: "rgba(112, 77, 254, 0.5)",
                        borderColor: "#704dfe",
                        yAxisID: "y1",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    y: { position: "left", beginAtZero: true, title: { display: true, text: "Revenue" } },
                    y1: { position: "right", beginAtZero: true, title: { display: true, text: "Orders" }, grid: { drawOnChartArea: false } },
                },
            },
        });
    }

    _renderDeliveriesChart() {
        const canvas = this.deliveriesChartRef.el;
        if (!canvas) return;
        const rows = this.state.data.deliveries.daily_breakdown || [];
        this._deliveriesChart = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: rows.map((r) => r.date),
                datasets: [
                    { label: "Shipped", data: rows.map((r) => r.done), backgroundColor: "#00a09d" },
                    { label: "Pending", data: rows.map((r) => r.pending), backgroundColor: "#f0ad4e" },
                    { label: "Cancelled", data: rows.map((r) => r.cancel), backgroundColor: "#d9534f" },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true },
                },
            },
        });
    }
}

registry.category("actions").add("shopify_manager_dashboard.main", ShopifyManagerDashboard);
