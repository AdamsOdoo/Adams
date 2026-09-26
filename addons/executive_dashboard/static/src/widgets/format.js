/** @odoo-module **/
import { localization } from "@web/core/l10n/localization";
import { deserializeDate } from "@web/core/l10n/dates";
import { formatFloat, humanNumber } from "@web/core/utils/numbers";

/** Short figure for cards and charts, e.g. 15.2M, 84k, 622. */
export function compact(value) {
    if (Math.abs(value || 0) < 1000) {
        return whole(value);
    }
    const text = humanNumber(value, { decimals: 1, minDigits: 1 });
    const zero = localization.decimalPoint + "0";
    const i = text.search(/[^0-9]*$/);
    return text.slice(0, i).endsWith(zero) ? text.slice(0, i - zero.length) + text.slice(i) : text;
}

/** Whole figure with the user's separators, e.g. 9,845,200. */
export function whole(value) {
    return formatFloat(value || 0, { digits: [false, 0] });
}

/** Share of `part` in `total` as a whole percentage, or null when undefined. */
export function percent(part, total) {
    return total ? Math.round((part / total) * 1000) / 10 : null;
}

/** "Nice" axis bounds and step covering [min, max] in about four steps. */
export function niceScale(min, max) {
    min = Math.min(0, min);
    max = Math.max(0, max);
    if (max === min) {
        return { lo: 0, hi: 1, step: 1 };
    }
    const raw = (max - min) / 4;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].find((m) => m * mag >= raw) * mag;
    return { lo: Math.floor(min / step) * step, hi: Math.ceil(max / step) * step, step };
}

/** "1 Sep – 25 Sep 2026" for a `get_section` period ({ date_from, date_to }). */
export function periodLabel(period) {
    const from = deserializeDate(period.date_from);
    const to = deserializeDate(period.date_to);
    if (from.equals(to)) {
        return to.toFormat("d MMM yyyy");
    }
    return from.toFormat(from.year === to.year ? "d MMM" : "d MMM yyyy") + " – " + to.toFormat("d MMM yyyy");
}

const AVATAR_COLORS = ["#0b7a6d", "#2563c9", "#6d45c4", "#a35705", "#3b7a1a", "#b53461"];

/** Initials and a stable colour for a person's name, as on the reference page. */
export function avatar(name) {
    const text = name || "?";
    const sum = [...text].reduce((s, c) => s + c.charCodeAt(0), 0);
    const initials = text.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
    return { initials, color: AVATAR_COLORS[sum % AVATAR_COLORS.length] };
}

/** Chip colour of the native sales order Delivery Status (blue / orange / green, as Odoo's help says). */
export function deliveryChip(status) {
    return { pending: "info", started: "info", partial: "warn", full: "good" }[status] || "neutral";
}
