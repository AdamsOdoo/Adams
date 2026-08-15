# Part of the Shopify Connector (U0 operator UI foundation).
#
# Installation / integrity tests for the U0 batch. Running at all proves the
# module (with the new views, menus, actions, assets and models) installed
# cleanly; these assertions then prove every U0 external ID resolves, the new
# models are registered, and the manifest wiring is correct. Full fresh-install
# / upgrade / uninstall-reinstall / zero-residue is exercised by the Odoo.sh
# runtime campaign (validation doc §Runtime).

from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiInstallation(TransactionCase):

    def test_actions_resolve(self):
        for xmlid in (
            'shopify_connector_core.action_shopify_connector_dashboard',
            'shopify_connector_core.action_shopify_connector_health',
            'shopify_connector_core.action_shopify_connector_store',
            'shopify_connector_core.action_shopify_connector_sync_center',
            'shopify_connector_core.action_shopify_connector_error_center',
            'shopify_connector_core.action_shopify_connector_job_log',
            'shopify_connector_core.action_shopify_connector_mutation_attempt',
            'shopify_connector_core.action_shopify_connector_job_cancel_wizard',
            'shopify_connector_core.action_shopify_connector_mutation_resolution_wizard',
            'shopify_connector_core.action_shopify_connector_sync_analysis',
        ):
            self.assertTrue(self.env.ref(xmlid), "Missing action %s" % xmlid)

    def test_menus_resolve_and_are_gated(self):
        root = self.env.ref('shopify_connector_core.menu_shopify_connector_root')
        auditor = self.env.ref('shopify_connector_core.group_shopify_connector_auditor')
        # Odoo 19: ir.ui.menu exposes access groups as `group_ids`
        # (the pre-19 `groups_id` name was removed).
        self.assertIn(auditor, root.group_ids,
                      "Root connector menu must be gated to the connector groups.")
        for xmlid in (
            'shopify_connector_core.menu_shopify_connector_dashboard',
            'shopify_connector_core.menu_shopify_connector_connector_health',
            'shopify_connector_core.menu_shopify_connector_operations',
            'shopify_connector_core.menu_shopify_connector_stores',
            'shopify_connector_core.menu_shopify_connector_store_records',
            'shopify_connector_core.menu_shopify_connector_sync_center',
            'shopify_connector_core.menu_shopify_connector_error_center',
            'shopify_connector_core.menu_shopify_connector_mutation_evidence',
            'shopify_connector_core.menu_shopify_connector_reporting',
            'shopify_connector_core.menu_shopify_connector_sync_analysis',
            'shopify_connector_core.menu_shopify_connector_logs',
            'shopify_connector_core.menu_shopify_connector_configuration',
        ):
            self.assertTrue(self.env.ref(xmlid), "Missing menu %s" % xmlid)

    def test_root_exposes_exactly_the_four_signed_pillars(self):
        root = self.env.ref('shopify_connector_core.menu_shopify_connector_root')
        active = root.child_id.filtered('active').sorted('sequence')
        self.assertEqual(
            active.mapped('name'),
            ['Dashboard', 'Operations', 'Reporting', 'Configuration'],
        )
        user = self.env.ref('shopify_connector_core.group_shopify_connector_user')
        admin = self.env.ref('shopify_connector_core.group_shopify_connector_admin')
        self.assertEqual(active[:3].mapped('group_ids'), user)
        self.assertEqual(active[3].group_ids, admin)

    def test_core_destinations_use_merchant_vocabulary(self):
        expected = {
            'menu_shopify_connector_connector_health': 'Connector Health',
            'menu_shopify_connector_sync_center': 'Runs & Recovery',
            'menu_shopify_connector_error_center': 'Needs Attention',
            'menu_shopify_connector_sync_analysis': 'Sync Performance',
            'menu_shopify_connector_logs': 'Audit Trail',
            'menu_shopify_connector_stores': 'Stores & Onboarding',
            'menu_shopify_connector_store_records': 'Stores',
        }
        for xmlid, label in expected.items():
            menu = self.env.ref('shopify_connector_core.%s' % xmlid)
            self.assertEqual(menu.name, label)
            self.assertTrue(menu.active)
        self.assertFalse(
            self.env.ref(
                'shopify_connector_core.menu_shopify_connector_mutation_evidence'
            ).active,
            'Mutation evidence must be a contextual drill-down, not navigation.',
        )

    def test_complete_suite_has_the_exact_signed_destination_tree(self):
        """Assert the cross-addon tree when all six product modules exist."""
        required = (
            'shopify_connector_sale.menu_shopify_connector_orders',
            'shopify_connector_product_export.menu_shopify_connector_product_export',
            'shopify_connector_inventory.menu_shopify_connector_inventory',
            'shopify_connector_fulfillment.menu_shopify_connector_fulfillment',
        )
        if not all(self.env.ref(xmlid, False) for xmlid in required):
            self.skipTest('The cross-addon navigation contract needs all six addons.')

        expected = {
            'menu_shopify_connector_dashboard': [
                'Sales Dashboard', 'Connector Health',
            ],
            'menu_shopify_connector_operations': [
                'Orders', 'Product Imports/Exports', 'Inventory',
                'Fulfillments', 'Runs & Recovery', 'Needs Attention',
            ],
            'menu_shopify_connector_reporting': [
                'Sales Analysis', 'Sync Performance', 'Audit Trail',
            ],
            'menu_shopify_connector_configuration': [
                'Stores & Onboarding', 'Sync Rules', 'Mappings',
                'Export Settings', 'Fulfillment Settings and Mode',
            ],
        }
        for pillar_xmlid, labels in expected.items():
            pillar = self.env.ref(
                'shopify_connector_core.%s' % pillar_xmlid
            )
            actual = pillar.child_id.filtered('active').sorted(
                'sequence'
            ).mapped('name')
            self.assertEqual(actual, labels, pillar.name)

        active_navigation = self.env[
            'ir.ui.menu'
        ].search([('id', 'child_of', self.env.ref(
            'shopify_connector_core.menu_shopify_connector_root'
        ).id), ('active', '=', True)])
        forbidden = {
            'Mutation Evidence', 'First-Push Guard', 'Sync Center',
            'Error & Review Center', 'Fulfillment Jobs', 'Export Diagnostics',
        }
        self.assertFalse(set(active_navigation.mapped('name')) & forbidden)

    def test_views_resolve(self):
        for xmlid in (
            'shopify_connector_core.view_shopify_connector_store_list',
            'shopify_connector_core.view_shopify_connector_store_form',
            'shopify_connector_core.view_shopify_connector_store_search',
            'shopify_connector_core.view_shopify_connector_job_list',
            'shopify_connector_core.view_shopify_connector_attention_list',
            'shopify_connector_core.view_shopify_connector_job_form',
            'shopify_connector_core.view_shopify_connector_job_search',
            'shopify_connector_core.view_shopify_connector_job_log_list',
            'shopify_connector_core.view_shopify_connector_job_log_form',
            'shopify_connector_core.view_shopify_connector_mutation_attempt_list',
            'shopify_connector_core.view_shopify_connector_mutation_attempt_form',
            'shopify_connector_core.view_shopify_connector_job_cancel_wizard_form',
            'shopify_connector_core.view_shopify_connector_mutation_resolution_wizard_form',
            'shopify_connector_core.view_shopify_connector_job_analysis_search',
            'shopify_connector_core.view_shopify_connector_job_analysis_graph',
            'shopify_connector_core.view_shopify_connector_job_analysis_pivot',
        ):
            self.assertTrue(self.env.ref(xmlid), "Missing view %s" % xmlid)

    def test_new_models_registered(self):
        self.assertIn('shopify.connector.ui.dashboard', self.env)
        self.assertIn('shopify.connector.job.cancel.wizard', self.env)
        self.assertIn('shopify.connector.mutation.resolution.wizard', self.env)
        # The dashboard service is abstract: no table, and it answers a
        # connector user (it is connector-users-only; the framework superuser
        # is not a connector-group member, so exercise it as an Auditor).
        self.assertTrue(self.env['shopify.connector.ui.dashboard']._abstract)
        viewer = new_test_user(
            self.env, login='u0_install_viewer',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor')
        data = self.env['shopify.connector.ui.dashboard'].with_user(
            viewer).get_dashboard_data()
        self.assertIn('state', data)
        # Store 360: the second RPC answers the same caller with the full
        # section set (the owning modules' sections appear when installed).
        payload = self.env['shopify.connector.ui.dashboard'].with_user(
            viewer).get_store_360_data()
        for key in ('meta', 'health', 'flows', 'critical', 'generated_at'):
            self.assertIn(key, payload)
        sales = self.env['shopify.connector.ui.dashboard'].with_user(
            viewer).get_sales_dashboard_data()
        health = self.env['shopify.connector.ui.dashboard'].with_user(
            viewer).get_connector_health_data()
        self.assertIn('commercial', sales)
        self.assertNotIn('health', sales)
        self.assertIn('health', health)
        self.assertNotIn('commercial', health)

    def test_manifest_depends_web(self):
        module = self.env['ir.module.module'].search(
            [('name', '=', 'shopify_connector_core')], limit=1)
        self.assertTrue(module)
        dep_names = module.dependencies_id.mapped('name')
        self.assertIn('web', dep_names,
                      "The U0 UI requires a dependency on 'web'.")

    def test_dashboard_client_action_tag(self):
        action = self.env.ref('shopify_connector_core.action_shopify_connector_dashboard')
        self.assertEqual(action.name, 'Sales Dashboard')
        self.assertEqual(action.tag, 'shopify_connector_sales_dashboard')
        self.assertEqual(action.type, 'ir.actions.client')
        health = self.env.ref(
            'shopify_connector_core.action_shopify_connector_health'
        )
        self.assertEqual(health.name, 'Connector Health')
        self.assertEqual(health.tag, 'shopify_connector_health')
        self.assertEqual(health.type, 'ir.actions.client')
        self.assertEqual(
            self.env.ref(
                'shopify_connector_core.menu_shopify_connector_connector_health'
            ).action,
            health,
        )

    def test_store_configuration_action_is_administrator_only(self):
        admin = self.env.ref(
            'shopify_connector_core.group_shopify_connector_admin'
        )
        action = self.env.ref(
            'shopify_connector_core.action_shopify_connector_store'
        )
        self.assertEqual(action.group_ids, admin)
