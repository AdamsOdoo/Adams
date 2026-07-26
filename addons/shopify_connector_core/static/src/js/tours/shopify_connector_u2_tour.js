/** @odoo-module **/
// Part of the Shopify Connector (U2 domain operator surfaces).
//
// Browser tour for the U2 surfaces — orders, COD reconciliation, customer and
// catalog matching, inventory. U2 shipped with server-side visibility and
// wiring tests but with NO driven-browser evidence at all, which its own
// acceptance matrix requires; this closes that.
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

// The connector's top-level branches collapse on navigation, so a child menu
// click needs its parent re-opened first. Expressed once here rather than
// repeated at every step.
const openBranch = (trigger, content) => [
    { trigger, content, run: "click" },
];

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

        // --- Orders (S9 family) ---
        ...openBranch(
            menu("shopify_connector_sale", "menu_shopify_connector_orders"),
            "Open the Orders branch."
        ),
        ...openBranch(
            menu("shopify_connector_sale", "menu_shopify_connector_order_workspace"),
            "Orders workspace."
        ),
        {
            trigger: ".o_list_view",
            content: "The orders workspace renders.",
        },

        // --- COD reconciliation ---
        ...openBranch(
            menu("shopify_connector_sale", "menu_shopify_connector_orders"),
            "Re-open the Orders branch."
        ),
        ...openBranch(
            menu("shopify_connector_sale", "menu_shopify_connector_cod_reconciliation"),
            "COD reconciliation."
        ),
        {
            trigger: ".o_list_view",
            content: "The COD reconciliation surface renders.",
        },

        // --- Catalog matching (S6/S8), including customer matching ---
        // Customer Matching is parented to the CATALOG branch, not Orders
        // (`shopify_connector_sale_menus.xml` sets
        // `parent="shopify_connector_product.menu_shopify_connector_catalog"`),
        // even though the menu is declared in the sale addon. Walking it from
        // the branch it actually renders under is the point of a browser tour.
        ...openBranch(
            menu("shopify_connector_product", "menu_shopify_connector_catalog"),
            "Open the Catalog branch."
        ),
        ...openBranch(
            menu("shopify_connector_sale", "menu_shopify_connector_customer_binding"),
            "Customer matching."
        ),
        {
            trigger: ".o_list_view",
            content: "The customer-binding surface renders.",
        },
        ...openBranch(
            menu("shopify_connector_product", "menu_shopify_connector_catalog"),
            "Re-open the Catalog branch."
        ),
        ...openBranch(
            menu("shopify_connector_product", "menu_shopify_connector_product_binding"),
            "Product matching."
        ),
        {
            trigger: ".o_list_view",
            content: "The product-binding surface renders.",
        },
        ...openBranch(
            menu("shopify_connector_product", "menu_shopify_connector_catalog"),
            "Re-open the Catalog branch."
        ),
        ...openBranch(
            menu("shopify_connector_product", "menu_shopify_connector_product_variant_binding"),
            "Variant matching."
        ),
        {
            trigger: ".o_list_view",
            content: "The variant-binding surface renders.",
        },

        // --- Inventory (S10-S12) ---
        ...openBranch(
            menu("shopify_connector_inventory", "menu_shopify_connector_inventory"),
            "Open the Inventory branch."
        ),
        ...openBranch(
            menu("shopify_connector_inventory", "menu_shopify_connector_inventory_workspace"),
            "Inventory workspace."
        ),
        {
            trigger: ".o_list_view",
            content: "The inventory workspace renders.",
        },
        ...openBranch(
            menu("shopify_connector_inventory", "menu_shopify_connector_inventory"),
            "Re-open the Inventory branch."
        ),
        ...openBranch(
            menu("shopify_connector_inventory", "menu_shopify_connector_inventory_first_push"),
            "First-push guard."
        ),
        {
            trigger: ".o_list_view, .o_nocontent_help",
            content:
                "The first-push guard surface renders — rows, or the empty state " +
                "that says there are none.",
        },
        ...openBranch(
            menu("shopify_connector_inventory", "menu_shopify_connector_inventory"),
            "Re-open the Inventory branch."
        ),
        ...openBranch(
            menu("shopify_connector_inventory", "menu_shopify_connector_location_mapping"),
            "Location mapping."
        ),
        {
            trigger: ".o_list_view, .o_nocontent_help",
            content: "The location-mapping surface renders.",
        },
    ],
});
