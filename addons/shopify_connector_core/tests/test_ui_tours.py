# Part of the Shopify Connector (U0 operator UI foundation).
#
# Browser-tour coverage for the primary U0 flow. The navigation tour uses the
# visible Connector User role; the hidden capability groups are authorization
# primitives, not customer navigation roles. The role-action tours (operator
# retry/cancel, reviewer release,
# administrator mutation resolution) are registered in
# static/src/js/tours/shopify_connector_u0_tour.js and are executed in the
# driven Odoo.sh runtime campaign with seeded fixtures (validation doc
# §Runtime), because they depend on seeded jobs / mutation attempts.

from odoo.tests.common import HttpCase, new_test_user, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    SHOPIFY_API_VERSION,
)


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiTours(HttpCase):

    def test_navigation_tour(self):
        new_test_user(
            self.env,
            login='u0_tour_user',
            password='u0_tour_user',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_user',
        )
        # Store 360: a connected store takes the dashboard out of the
        # first-run empty state so the tour can assert the 360 shell
        # (period filter, page-updated timestamp, health region, flow
        # table) and the Sync Operations Analysis surface. Core-only
        # fixture — commercial regions are driven in the sale module's
        # browser tours, where order fixtures exist.
        self.env['shopify.connector.store'].sudo().create({
            'name': 'U0 Tour Store',
            'shop_domain': 'u0-tour-store.myshopify.com',
            'api_version': SHOPIFY_API_VERSION,
            'state': 'connected',
            'credential_present': True,
        })
        self.start_tour('/odoo', 'shopify_connector_u0_nav_tour', login='u0_tour_user')

    def test_u2_navigation_tour(self):
        """The U2 domain surfaces, driven in a browser.

        This now exercises the C1 split: routine order/inventory destinations
        under Operations and durable mappings/safeguards under Administrator-
        only Configuration.

        It is read-only: every step opens a menu or asserts a list rendered.
        No step clicks a control that writes, enqueues a job or contacts
        Shopify, so it leaves no residue.
        """
        new_test_user(
            self.env,
            login='u2_tour_admin',
            password='u2_tour_admin',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_admin',
        )
        self.start_tour('/odoo', 'shopify_connector_u2_nav_tour',
                        login='u2_tour_admin')
