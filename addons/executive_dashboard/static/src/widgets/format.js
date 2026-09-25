/** @odoo-module **/
import { localization } from "@web/core/l10n/localization";
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
