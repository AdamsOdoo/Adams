"""Menu actions must name their views, not win a sort.

`ir.ui.view._order` is `"priority,name,id"`, so an action with no view
reference resolves whichever view happens to sort first for that model.
Every view on `shopify.connector.store.settings` sits at the default
priority 16, which left the tie to be broken on the view's *name* -- and
`Export Settings` lost it to the fulfillment list.
"""

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestExportActionViewBinding(TransactionCase):

    def _action(self, xmlid):
        return self.env.ref('shopify_connector_product_export.%s' % xmlid)

    def _bound(self, action, view_mode):
        """The view this action binds for `view_mode`, or False."""
        for view in action.view_ids:
            if view.view_mode == view_mode:
                return view.view_id
        return False

    # ------------------------------------------------------------------
    # Export Settings
    # ------------------------------------------------------------------

    def test_export_settings_binds_the_export_views(self):
        action = self._action('action_shopify_connector_store_settings_export')
        self.assertEqual(action.res_model, 'shopify.connector.store.settings')
        self.assertEqual(action.view_mode, 'list,form')
        self.assertEqual(
            self._bound(action, 'list'),
            self.env.ref('shopify_connector_product_export.'
                         'view_shopify_connector_store_settings_list_export'),
        )
        self.assertEqual(
            self._bound(action, 'form'),
            self.env.ref('shopify_connector_product_export.'
                         'view_shopify_connector_store_settings_form_export'),
        )

    def test_export_settings_does_not_resolve_the_fulfillment_list(self):
        """The exact defect: a name-ordered fallback to another module."""
        action = self._action('action_shopify_connector_store_settings_export')
        fulfillment = self.env.ref(
            'shopify_connector_fulfillment.'
            'view_shopify_connector_store_settings_fulfillment_list',
            raise_if_not_found=False,
        )
        if not fulfillment:
            self.skipTest('shopify_connector_fulfillment is not installed')
        self.assertNotEqual(self._bound(action, 'list'), fulfillment)
        # And prove the fallback really would have chosen it, so this test
        # keeps failing for the right reason if the binding is ever dropped.
        default_list = self.env['ir.ui.view'].default_view(
            'shopify.connector.store.settings', 'list',
        )
        self.assertEqual(
            default_list, fulfillment.id,
            'the unbound fallback no longer resolves the fulfillment list; '
            'this test needs rewriting rather than deleting',
        )

    def test_the_export_list_shows_the_export_columns(self):
        view = self.env.ref('shopify_connector_product_export.'
                            'view_shopify_connector_store_settings_list_export')
        arch = view.arch_db
        for field in (
            'product_export_domain_enabled',
            'product_export_binding_namespace_ready',
            'price_source_of_truth',
            'media_source_of_truth',
        ):
            with self.subTest(field=field):
                self.assertIn(field, arch)

    # ------------------------------------------------------------------
    # Empty states on every menu-reachable action in this module
    # ------------------------------------------------------------------

    def test_every_menu_reachable_action_has_an_empty_state(self):
        menus = self.env['ir.ui.menu'].search([])
        module = 'shopify_connector_product_export'
        missing = []
        for menu in menus:
            action = menu.action
            if not action or action._name != 'ir.actions.act_window':
                continue
            xmlid = action.get_external_id().get(action.id) or ''
            if not xmlid.startswith('%s.' % module):
                continue
            if not action.help:
                missing.append(xmlid)
        self.assertFalse(
            missing,
            'a menu-reachable action with no empty state shows a bare '
            '"no records" surface the operator cannot act on: %s' % missing,
        )

    def test_exported_media_binds_its_own_views(self):
        action = self._action('action_shopify_connector_product_media_binding')
        self.assertEqual(
            self._bound(action, 'list'),
            self.env.ref('shopify_connector_product_export.'
                         'view_shopify_connector_product_media_binding_list'),
        )
        self.assertEqual(
            self._bound(action, 'form'),
            self.env.ref('shopify_connector_product_export.'
                         'view_shopify_connector_product_media_binding_form'),
        )
