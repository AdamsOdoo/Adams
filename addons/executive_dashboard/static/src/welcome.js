/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Icon } from "./icons";

const { DateTime } = luxon;

/** Welcome: greeting, date, company, search and the section cards. No figures. */
export class Welcome extends Component {
    static template = "executive_dashboard.Welcome";
    static components = { Icon };
    static props = {
        boot: Object,
        sections: Array,
        openPage: Function,
        prefetch: Function,
        openSearch: Function,
    };

    get greeting() {
        const first = (this.props.boot.user_name || "").trim().split(/\s+/)[0];
        return _t("Greetings, %(name)s", { name: first });
    }

    get today() {
        return DateTime.local().toLocaleString({ weekday: "long", day: "numeric", month: "long", year: "numeric" });
    }
}
