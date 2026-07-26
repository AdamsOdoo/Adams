# Part of the Shopify Connector (U0 operator UI foundation).
#
# Browser-tour coverage for the primary U0 flow. The navigation tour is
# role-agnostic (every connector role reads every operator surface) and is the
# automated acceptance for "the operator UI is navigable and every screen
# renders". The role-action tours (operator retry/cancel, reviewer release,
# administrator mutation resolution) are registered in
# static/src/js/tours/shopify_connector_u0_tour.js and are executed in the
# driven Odoo.sh runtime campaign with seeded fixtures (validation doc
# §Runtime), because they depend on seeded jobs / mutation attempts.

from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiTours(HttpCase):

    def test_navigation_tour(self):
        new_test_user(
            self.env,
            login='u0_tour_auditor',
            password='u0_tour_auditor',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_auditor',
        )
        self.start_tour('/odoo', 'shopify_connector_u0_nav_tour', login='u0_tour_auditor')

    def test_u2_navigation_tour(self):
        """The U2 domain surfaces, driven in a browser.

        U2 shipped with server-side visibility and wiring tests and NO
        driven-browser evidence, which its own acceptance matrix requires.
        This walks orders, COD reconciliation, customer matching, product and
        variant matching, the inventory workspace, the first-push guard and
        location mapping.

        It is read-only: every step opens a menu or asserts a list rendered.
        No step clicks a control that writes, enqueues a job or contacts
        Shopify, so it leaves no residue.
        """
        new_test_user(
            self.env,
            login='u2_tour_user',
            password='u2_tour_user',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_user',
        )
        self.start_tour('/odoo', 'shopify_connector_u2_nav_tour',
                        login='u2_tour_user')
