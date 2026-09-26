/** @odoo-module **/
import { Component, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { compact, niceScale } from "./format";

/**
 * Keeps `state.width` equal to the host's width so the SVG is drawn in real
 * pixels (text is never stretched). SVG coordinates are not mirrored by the
 * RTL stylesheet, so charts flip their x axis themselves.
 */
function useChartWidth(ref, state) {
    let observer = null;
    useEffect(
        () => {
            const el = ref.el;
            if (!el) {
                return;
            }
            const measure = () => {
                const width = Math.round(el.clientWidth);
                if (width && width !== state.width) {
                    state.width = width;
                }
            };
            measure();
            observer = new ResizeObserver(measure);
            observer.observe(el);
            return () => observer.disconnect();
        },
        () => []
    );
    onWillUnmount(() => observer?.disconnect());
}

/**
 * Monthly line chart. `series`: [{ name, values, color, area }], `labels` and
 * `titles` per point. With `partial`, the last segment is dashed (month to date).
 */
export class LineChart extends Component {
    static template = "executive_dashboard.LineChart";
    static props = {
        series: Array,
        labels: Array,
        titles: Array,
        partial: { type: Boolean, optional: true },
        height: { type: Number, optional: true },
        onClick: { type: Function, optional: true },
    };

    setup() {
        this.host = useRef("host");
        this.state = useState({ width: 600, hover: null });
        useChartWidth(this.host, this.state);
    }

    get geo() {
        const W = Math.max(280, this.state.width);
        const H = this.props.height || 240;
        const pad = { l: 48, r: 14, t: 10, b: 26 };
        const rtl = localization.direction === "rtl";
        const n = Math.max(1, this.props.labels.length - 1);
        const all = this.props.series.flatMap((s) => s.values);
        const { lo, hi, step } = niceScale(Math.min(...all), Math.max(...all));
        const x0 = (i) => pad.l + (i * (W - pad.l - pad.r)) / n;
        const X = (i) => (rtl ? W - x0(i) : x0(i));
        const Y = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * (H - pad.t - pad.b);
        const ticks = [];
        for (let v = lo; v <= hi + step / 2; v += step) {
            ticks.push({ y: Y(v), label: compact(v) });
        }
        const gridX1 = rtl ? pad.r : pad.l;
        const gridX2 = rtl ? W - pad.l : W - pad.r;
        const labelX = rtl ? W - pad.l + 8 : pad.l - 8;
        const narrow = W < 420;
        const xlabels = this.props.labels.map((label, i) => ({ x: X(i), label: narrow && i % 2 ? "" : label }));
        const last = this.props.labels.length - 1;
        const solidEnd = this.props.partial ? last - 1 : last;
        const lines = this.props.series.map((s) => {
            // Plain concatenation: the asset minifier drops spaces inside nested template literals.
            const pts = s.values.map((v, i) => [X(i), Y(v)]);
            const path = (list) => list.map((p, i) => (i ? "L" : "M") + p[0] + " " + p[1]).join("");
            const solid = path(pts.slice(0, solidEnd + 1));
            const dashed = this.props.partial && last > 0 ? path([pts[last - 1], pts[last]]) : "";
            const base = Y(Math.max(lo, 0));
            const area = s.area ? path([...pts, [X(last), base], [X(0), base]]) + "Z" : "";
            return { ...s, solid, dashed, area, end: pts[last] };
        });
        return { W, H, pad, rtl, n, X, Y, ticks, gridX1, gridX2, labelX, xlabels, lines, last };
    }

    get tip() {
        const i = this.state.hover;
        if (i === null) {
            return null;
        }
        const { X, W, Y } = this.geo;
        const px = X(i);
        return {
            x: px,
            left: px > W / 2 ? px - 176 : px + 14,
            title: this.props.titles[i],
            dots: this.props.series.map((s) => ({ color: s.color, cy: Y(s.values[i]) })),
            rows: this.props.series.map((s) => ({ name: s.name, color: s.color, value: compact(s.values[i]) })),
        };
    }

    onPointerMove(ev) {
        const svg = ev.currentTarget.ownerSVGElement;
        const rect = svg.getBoundingClientRect();
        const { W, pad, n, rtl } = this.geo;
        let px = ((ev.clientX - rect.left) * W) / rect.width;
        if (rtl) {
            px = W - px;
        }
        const i = Math.round((px - pad.l) / ((W - pad.l - pad.r) / n));
        this.state.hover = Math.max(0, Math.min(n, i));
    }

    onPointerLeave() {
        this.state.hover = null;
    }
}

/**
 * Column chart. `items`: [{ label, value, color }]; `onSelect(index)` opens
 * the column's records.
 */
export class ColumnChart extends Component {
    static template = "executive_dashboard.ColumnChart";
    static props = {
        items: Array,
        height: { type: Number, optional: true },
        onSelect: { type: Function, optional: true },
    };

    setup() {
        this.host = useRef("host");
        this.state = useState({ width: 400 });
        useChartWidth(this.host, this.state);
    }

    get geo() {
        const W = Math.max(240, this.state.width);
        const H = this.props.height || 190;
        const pad = { l: 6, r: 6, t: 22, b: 26 };
        const rtl = localization.direction === "rtl";
        const items = this.props.items;
        const values = items.map((d) => d.value);
        const hi = Math.max(0, ...values) * 1.1 || 1;
        const lo = Math.min(0, ...values) * 1.1;
        const bw = (W - pad.l - pad.r) / Math.max(1, items.length);
        const cw = Math.min(48, bw * 0.58);
        const Y = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * (H - pad.t - pad.b);
        const base = Y(0);
        const cols = items.map((d, i) => {
            const c = pad.l + bw * i + bw / 2;
            const cx = rtl ? W - c : c;
            const top = Math.min(Y(d.value), base);
            const bottom = Math.max(Y(d.value), base);
            const r = Math.min(4, (bottom - top) / 2);
            const a = cx - cw / 2;
            const path = bottom - top < 0.5 ? "" :
                ["M", a, bottom, "V", top + r, "Q", a, top, a + r, top, "H", a + cw - r,
                    "Q", a + cw, top, a + cw, top + r, "V", bottom, "Z"].join(" ");
            return { ...d, i, cx, hitX: cx - bw / 2, bw, path, labelY: top - 6, value: compact(d.value) };
        });
        return { W, H, pad, base, cols };
    }

    select(i) {
        this.props.onSelect?.(i);
    }

    onKey(ev, i) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.select(i);
        }
    }
}
