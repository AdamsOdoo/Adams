import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

export class PosSalesReportListController extends ListController {
    static components = { ...ListController.components, Dropdown, DropdownItem };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    /** What the printout must follow: the list's domain, grouping, visible columns and filters. */
    getPrintParams() {
        const { domain, groupBy } = this.model.root;
        const columns = this.getExportableFields().map((field) => field.name);
        const filters = this.env.searchModel.facets
            .filter((facet) => facet.type !== "groupBy")
            .map((facet) => {
                const values = facet.values.join(` ${facet.separator} `);
                return facet.title ? `${facet.title}: ${values}` : values;
            });
        return { domain, groupBy, columns, filters };
    }

    async onPrint(mode) {
        const { domain, groupBy, columns, filters } = this.getPrintParams();
        const action = await this.orm.call(
            "report.pos.order",
            "action_print_sales_report",
            [domain, groupBy, columns, mode, filters],
            { context: this.props.context }
        );
        await this.actionService.doAction(action);
    }
}

export const posSalesReportListView = {
    ...listView,
    Controller: PosSalesReportListController,
    buttonTemplate: "adams_pos_sales_report.ListView.Buttons",
};

registry.category("views").add("pos_sales_report_list", posSalesReportListView);
