/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * Frame of one section. The section's own component (registered by its file
 * in `executive_dashboard.sections`) receives the `get_section` result; until
 * the result arrives the frame shows placeholders.
 */
export const sectionRegistry = registry.category("executive_dashboard.sections");

export class SectionView extends Component {
    static template = "executive_dashboard.SectionView";
    static props = {
        section: Object,
        data: { type: [Object, { value: null }], optional: true },
        loading: Boolean,
        error: Boolean,
        openPanel: Function,
    };

    get component() {
        return sectionRegistry.get(this.props.section.key, null);
    }

    get status() {
        return this.props.data?.status;
    }
}
