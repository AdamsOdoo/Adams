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
            'shopify_connector_core.action_shopify_connector_store',
            'shopify_connector_core.action_shopify_connector_sync_center',
            'shopify_connector_core.action_shopify_connector_error_center',
            'shopify_connector_core.action_shopify_connector_job_log',
            'shopify_connector_core.action_shopify_connector_mutation_attempt',
            'shopify_connector_core.action_shopify_connector_job_cancel_wizard',
            'shopify_connector_core.action_shopify_connector_mutation_resolution_wizard',
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
            'shopify_connector_core.menu_shopify_connector_stores',
            'shopify_connector_core.menu_shopify_connector_sync_center',
            'shopify_connector_core.menu_shopify_connector_error_center',
            'shopify_connector_core.menu_shopify_connector_mutation_evidence',
            'shopify_connector_core.menu_shopify_connector_logs',
        ):
            self.assertTrue(self.env.ref(xmlid), "Missing menu %s" % xmlid)

    def test_views_resolve(self):
        for xmlid in (
            'shopify_connector_core.view_shopify_connector_store_list',
            'shopify_connector_core.view_shopify_connector_store_form',
            'shopify_connector_core.view_shopify_connector_store_search',
            'shopify_connector_core.view_shopify_connector_job_list',
            'shopify_connector_core.view_shopify_connector_job_form',
            'shopify_connector_core.view_shopify_connector_job_search',
            'shopify_connector_core.view_shopify_connector_job_log_list',
            'shopify_connector_core.view_shopify_connector_job_log_form',
            'shopify_connector_core.view_shopify_connector_mutation_attempt_list',
            'shopify_connector_core.view_shopify_connector_mutation_attempt_form',
            'shopify_connector_core.view_shopify_connector_job_cancel_wizard_form',
            'shopify_connector_core.view_shopify_connector_mutation_resolution_wizard_form',
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

    def test_manifest_depends_web(self):
        module = self.env['ir.module.module'].search(
            [('name', '=', 'shopify_connector_core')], limit=1)
        self.assertTrue(module)
        dep_names = module.dependencies_id.mapped('name')
        self.assertIn('web', dep_names,
                      "The U0 UI requires a dependency on 'web'.")

    def test_dashboard_client_action_tag(self):
        action = self.env.ref('shopify_connector_core.action_shopify_connector_dashboard')
        self.assertEqual(action.tag, 'shopify_connector_dashboard')
        self.assertEqual(action.type, 'ir.actions.client')
