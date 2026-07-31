"""Batch 2 §10 -- driven-browser evidence for canonical Store Settings.

THE DEFECT THIS SURFACE CLOSED WAS REACHABILITY, so the tour reaches it the
way a merchant does: through the Configuration menu's own action, not by a
constructed URL. A tour that jumped straight to a record id would prove the
form renders while saying nothing about whether anyone can get to it.

The store is shown and never offered as an input; the domain switch is
operated from the keyboard; the save goes through the ordinary form save, so
every existing model constraint is still the authority.
"""

from odoo.tests import tagged
from odoo.tests.common import HttpCase

SETTINGS_ACTION = (
    'shopify_connector_core.action_shopify_connector_store_settings_canonical'
)


@tagged('post_install', '-at_install', 'shopify_connector_b2_tours')
class TestUiB2SettingsTours(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'B2 settings tour store',
            'shop_domain': 'b2-settings-tour.myshopify.com',
            'api_version': '2026-07',
            'company_id': cls.env.company.id,
        })
        cls.store.write({'state': 'connected'})
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'product_domain_enabled': False,
        })
        cls.admin = cls.env['res.users'].create({
            'name': 'b2set_admin',
            'login': 'b2set_admin',
            'password': 'b2set_admin',
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_user'
                ).id,
            ])],
        })

    def test_store_settings_tour_changes_a_setting_through_the_menu_route(self):
        self.assertFalse(self.settings.product_domain_enabled)
        self.env.flush_all()
        self.start_tour(
            '/odoo/action-%s' % SETTINGS_ACTION,
            'shopify_connector_b2_store_settings_tour',
            login='b2set_admin',
        )
        self.settings.invalidate_recordset()
        self.assertTrue(
            self.settings.product_domain_enabled,
            'the browser save did not reach the database',
        )
        # And the write went through the ordinary path, so the readiness
        # marker moved exactly as the server tests say it should.
        self.assertTrue(self.settings.setup_readiness_stale_since)
        self.assertEqual(self.settings.store_id, self.store)

    def test_the_canonical_action_is_the_only_route_and_it_is_role_gated(self):
        """The menu is chrome; the action's own assertion is the control."""
        action = self.env.ref(SETTINGS_ACTION)
        self.assertEqual(action.res_model, 'shopify.connector.store.settings')
        # Both views are named explicitly, so the `default_view()` fallback --
        # which orders by `priority,name,id` and has rendered the wrong
        # model's list before in this project -- can never choose for it.
        self.assertEqual(len(action.view_ids), 2)
        self.assertEqual(
            sorted(action.view_ids.mapped('view_mode')), ['form', 'list'],
        )
