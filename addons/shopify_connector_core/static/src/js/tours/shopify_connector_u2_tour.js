/** @odoo-module **/
// Part of the Shopify Connector (U2 domain operator surfaces).
//
// Browser tour for the C1 split: routine domain work under Operations and
// durable mappings/safeguards under Administrator-only Configuration.
//
// WHY IT LIVES IN CORE. The surfaces it walks belong to four different
// addons (`shopify_connector_sale`, `_product`, `_inventory`, and the core
// root menu), and a tour can only be registered once. Core is the only module
// all four depend on, and it is the module that already owns
// `web.assets_backend` for the connector.
//
// It assumes all four domain addons are installed, which the canonical runner
// guarantees (`MODULES` in `tools/run_connector_suite.sh` installs every one).
// In a partial install this tour FAILS rather than skipping the missing
// branch — deliberately: a tour that quietly walks around an absent surface
// reports a pass for coverage it did not have.
//
// It is read-only by construction: every step either opens a menu or asserts
// that a list rendered. No step clicks a control that writes, enqueues a job,
// or contacts Shopify.

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

const coreMenu = (xmlid) => `[data-menu-xmlid="shopify_connector_core.${xmlid}"]`;
const menu = (module, xmlid) => `[data-menu-xmlid="${module}.${xmlid}"]`;
const topMenu = {
    Operations: coreMenu("menu_shopify_connector_operations"),
    Configuration: coreMenu("menu_shopify_connector_configuration"),
};

const openPath = (labels, content) => ({
    trigger: topMenu[labels[0]] || ".o_menu_sections",
    content,
    async run() {
        for (const label of labels) {
            const topEntry = [...document.querySelectorAll(
                topMenu[label] || "__missing__"
            )].find((candidate) => candidate.getClientRects().length);
            const textNode = [...document.querySelectorAll(
                ".o_menu_sections *, .o-dropdown--menu *"
            )].find((candidate) => candidate.textContent.trim() === label);
            const entry = topEntry || (textNode && (
                textNode.closest("a, button, [role='menuitem'], [data-menu-xmlid]")
                || textNode
            ));
            if (!entry) {
                throw new Error(`${label} is absent from the operator menu tree`);
            }
            entry.click();
            await new Promise((resolve) => setTimeout(resolve, 400));
        }
    },
});

// The connector's top-level branches collapse on navigation, so a child menu
// click needs its parent re-opened first. Expressed once here rather than
// repeated at every step.
registry.category("web_tour.tours").add("shopify_connector_u2_nav_tour", {
    url: "/odoo",
    steps: () => [
        // The `.o_app` tiles live inside the apps-menu sidebar and do not
        // exist in the DOM until it is opened (odoo/odoo@19.0
        // `web/static/src/webclient/navbar/navbar.xml`).
        stepUtils.showAppsMenuItem(),
        {
            trigger: `.o_app${coreMenu("menu_shopify_connector_root")}`,
            content: "Open the Shopify Connector app.",
            run: "click",
        },

        // --- Operations ---
        openPath(["Operations", "Orders"],
            "Open Orders."
        ),
        {
            trigger: ".o_list_view",
            content: "The orders surface renders.",
        },
        openPath(["Operations", "Inventory"],
            "Open Inventory."
        ),
        {
            trigger: ".o_list_view",
            content: "The inventory surface renders.",
        },

        // --- Configuration / Mappings ---
        openPath(["Configuration", "Customer Mappings"],
            "Customer mappings."
        ),
        {
            trigger: ".o_list_view",
            content: "The customer mappings render.",
        },
        openPath(["Configuration", "Product Mappings"],
            "Product mappings."
        ),
        {
            trigger: ".o_list_view",
            content: "The product mappings render.",
        },
        openPath(["Configuration", "Variant Mappings"],
            "Variant mappings."
        ),
        {
            trigger: ".o_list_view",
            content: "The variant mappings render.",
        },
        openPath(["Configuration", "Location Mappings"],
            "Location mappings."
        ),
        {
            trigger: ".o_list_view, .o_nocontent_help",
            content: "The location mappings render.",
        },

        // --- Configuration / Sync Rules ---
        openPath(["Configuration", "Inventory Safeguards"],
            "Inventory safeguards."
        ),
        {
            trigger: ".o_list_view, .o_nocontent_help",
            content: "The inventory safeguards render.",
        },
    ],
});
