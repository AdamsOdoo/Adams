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
