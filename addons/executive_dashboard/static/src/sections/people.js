/** @odoo-module **/
import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sectionRegistry } from "../section";
import { drawerRegistry } from "../side_panel";
import { Icon } from "../icons";
import { avatar, whole } from "../widgets/format";

const MODEL = "executive.dashboard";
const SEARCH_DELAY = 300;

/** Worked hours as "7:45", or "—". */
export function hours(value) {
    if (!value) {
        return "—";
    }
    const minutes = Math.round(value * 60);
    return Math.floor(minutes / 60) + ":" + ("" + (minutes % 60)).padStart(2, "0");
}

/** Chip class and label of today's attendance state (in / out / off / none). */
export function stateChip(state) {
    return {
        in: { cls: "good", label: _t("Checked in") },
        out: { cls: "neutral", label: _t("Checked out") },
        off: { cls: "info", label: _t("On time off") },
    }[state] || { cls: "warn", label: _t("Not checked in") };
}

function openEmployee(openPanel, employeeId, crumb) {
    openPanel({ kind: "drawer", key: "people.employee", args: { employee_id: employeeId }, crumb, sec: "people" });
}

/**
 * Employees directory: department filter and name search are sent to the
 * server, which returns one page and the number of employees; the first page
 * comes with the section.
 */
export class EmployeeDirectory extends Component {
    static template = "executive_dashboard.EmployeeDirectory";
    static components = { Icon };
    static props = { directory: Object, openPanel: Function };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.avatar = avatar;
        this.stateChip = stateChip;
        this.seq = 0;
        const { filters } = this.props.directory;
        // Filters and page kept when the user left for a native screen and came back.
        const kept = this.env.edRecall?.("directory");
        this.state = useState(kept ? { ...kept, loading: false } : {
            data: this.props.directory, loading: false, query: filters.query,
            // Select values are strings.
            department_id: filters.department_id ? `${filters.department_id}` : "" });
        this.env.edRemember?.("directory", () => ({ ...this.state }));
        if (kept && !kept.data) {
            // Back from the browser's Back button: filters only, so load the first page with them.
            this.state.data = this.props.directory;
            this.load(0);
        }
        this.labels = { employee: _t("Employee"), department: _t("Department"), checkIn: _t("Check in"),
                        status: _t("Status") };
        onWillUpdateProps((next) => {
            if (next.directory !== this.props.directory) {
                this.load(this.state.data.page);
            }
        });
        onWillUnmount(() => clearTimeout(this.timer));
    }

    get args() {
        return { department_id: this.state.department_id ? Number(this.state.department_id) : false,
                 query: this.state.query };
    }

    get range() {
        const { count, page, per } = this.state.data;
        return { from: count ? page * per + 1 : 0, to: Math.min(count, (page + 1) * per), count };
    }

    get lastPage() {
        const { count, per } = this.state.data;
        return Math.max(0, Math.ceil(count / per) - 1);
    }

    async load(page = 0) {
        const seq = ++this.seq;
        this.state.loading = true;
        try {
            const data = await this.orm.call(MODEL, "get_drawer", ["people.directory", { ...this.args, page }]);
            if (seq === this.seq) {
                this.state.data = data;
            }
        } finally {
            if (seq === this.seq) {
                this.state.loading = false;
            }
        }
    }

    onDepartment(ev) {
        this.state.department_id = ev.target.value;
        this.load();
    }

    onQuery(ev) {
        this.state.query = ev.target.value;
        clearTimeout(this.timer);
        this.timer = setTimeout(() => this.load(), SEARCH_DELAY);
    }

    async openInOdoo() {
        await this.action.doAction(await this.orm.call(MODEL, "open_action", ["people.directory", this.args]));
    }

    open(row) {
        openEmployee(this.props.openPanel, row.employee_id, _t("Employees directory"));
    }
}

/**
 * People: headcount, checked in today, on time off today, shifts today;
 * attendance today, time off (today and the next 7 days), shifts by time slot
 * (Planning), headcount by department and the employees directory. Current
 * position only (no period). A widget whose app is missing is not shown.
 */
export class PeopleSection extends Component {
    static template = "executive_dashboard.PeopleSection";
    static components = { Icon, EmployeeDirectory };
    static props = { data: Object, openPanel: Function };

    setup() {
        this.avatar = avatar;
        this.hours = hours;
        this.stateChip = stateChip;
        this.whole = whole;
        this.labels = { employee: _t("Employee"), checkIn: _t("Check in"), checkOut: _t("Check out"),
                        worked: _t("Worked"), status: _t("Status") };
    }

    get w() {
        return this.props.data.widgets;
    }

    get kpis() {
        const k = this.w.kpis;
        const list = [{ key: "headcount", icon: "people", label: _t("Headcount"), value: whole(k.headcount),
                        cap: _t("Active employees"), open: () => this.open("employees", {}) }];
        if (k.attendance) {
            list.push({ key: "attendance", icon: "check", label: _t("Checked in today"), value: whole(k.attendance.count),
                        cap: _t("%(in)s still in · %(out)s checked out", { in: k.attendance.still_in, out: k.attendance.checked_out }),
                        open: () => this.open("attendance", {}) });
        }
        if (k.leave) {
            list.push({ key: "leave", icon: "cal", label: _t("On time off today"), value: whole(k.leave.count),
                        cap: _t("Approved time off"), open: () => this.open("leave", {}) });
        }
        if (k.shifts) {
            list.push({ key: "shifts", icon: "clock", label: _t("Shifts today"), value: whole(k.shifts.count),
                        cap: _t("%s time slots", k.shifts.slots), open: () => this.open("shifts", {}) });
        }
        return list;
    }

    get departmentSpan() {
        return this.w.shifts ? "ed-span-6" : "ed-span-12";
    }

    open(name, args, crumb = _t("People")) {
        this.props.openPanel({ kind: "drawer", key: `people.${name}`, args, crumb, sec: "people" });
    }

    openEmployee(employeeId) {
        if (employeeId) {
            openEmployee(this.props.openPanel, employeeId, _t("People"));
        }
    }

    openDepartment(dept) {
        this.open("department", { department_id: dept.id }, _t("Headcount by department"));
    }
}

/** Side panel of today's attendance: one line per employee. */
export class AttendanceDrawer extends Component {
    static template = "executive_dashboard.AttendanceDrawer";
    static props = { data: { type: [Object, { value: null }], optional: true }, open: Function, panel: Object };

    setup() {
        this.avatar = avatar;
        this.hours = hours;
        this.stateChip = stateChip;
        this.labels = { employee: _t("Employee"), checkIn: _t("Check in"), checkOut: _t("Check out"),
                        worked: _t("Worked"), status: _t("Status") };
    }

    get more() {
        const { count, rows } = this.props.data || {};
        if (count <= (rows || []).length) {
            return "";
        }
        return this.props.data.action
            ? _t("Showing %(shown)s of %(count)s. Open list shows them all.", { shown: rows.length, count })
            : _t("Showing %(shown)s of %(count)s.", { shown: rows.length, count });
    }

    openRow(row) {
        this.props.open({ kind: "drawer", key: "people.employee", args: { employee_id: row.employee_id },
                          crumb: _t("Attendance today"), sec: "people", back: this.props.panel });
    }
}

/** Side panel of one employee: department, today's check-in/out, contact and status. */
export class EmployeeDrawer extends Component {
    static template = "executive_dashboard.EmployeeDrawer";
    static props = { data: { type: [Object, { value: null }], optional: true }, open: Function, panel: Object };

    setup() {
        this.stateChip = stateChip;
    }
}

sectionRegistry.add("people", PeopleSection);
drawerRegistry.add("people.attendance", AttendanceDrawer);
drawerRegistry.add("people.employee", EmployeeDrawer);
