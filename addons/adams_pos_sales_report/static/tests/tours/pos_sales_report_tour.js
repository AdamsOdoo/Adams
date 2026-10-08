import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("adams_pos_sales_report_print", {
    steps: () => [
        { trigger: ".o_list_view .o_list_table" },
        { trigger: ".o_facet_value:contains('Day')" },
        { trigger: "button.o_psr_print", run: "click" },
        { trigger: ".o_psr_print_summary", run: "click" },
        { trigger: ".o_notification:contains('PSR print requested')" },
    ],
});
