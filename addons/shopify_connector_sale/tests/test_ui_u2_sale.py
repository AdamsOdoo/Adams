"""U2 operator UI — order, COD and customer surfaces (S16/S17/S18/S8).

The load-bearing assertion in this module is that **the five independent
order state dimensions are never merged into one badge.** An order can be
paid and unshipped, shipped and unpaid, or cancelled after both; a single
merged "order state" chip has to pick a winner, and whichever it picks is
wrong for some operator. The list and form are checked against the actual
view architecture for that, not by reading.

The second is the SEC-2 PII posture: no masked column, no unmask toggle, and
a refresh flag on rows the pre-SEC-2 sweep destroyed -- flagged, never
reconstructed.
"""

import ast
import os

from lxml import etree

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


# Issue #193 / #157 -- Odoo 19 test-phase contract; see the core suites.
@tagged('post_install', '-at_install')
class TestUiU2Sale(TransactionCase):

    MENUS = (
        'menu_shopify_connector_orders',
        'menu_shopify_connector_order_workspace',
        'menu_shopify_connector_cod_reconciliation',
        'menu_shopify_connector_customer_binding',
    )
    ACTIONS = (
        'action_shopify_connector_order_workspace',
        'action_shopify_connector_cod_reconciliation',
        'action_shopify_connector_customer_binding',
    )

    # The five dimensions the master specification keeps separate.
    ORDER_DIMENSION_FIELDS = (
        'shopify_financial_status_snapshot',
        'shopify_fulfillment_status_snapshot',
        'status',
        'manual_gateway_approval_state',
        'shopify_cancelled_at',
    )
    COD_DIMENSION_FIELDS = (
        'cod_commercial_state',
        'cod_fulfillment_state',
        'cod_collection_state',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.OrderBinding = cls.env['shopify.connector.order.binding']
        cls.CustomerBinding = cls.env['shopify.connector.customer.binding']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'U2 sale store',
            'shop_domain': 'u2-sale.myshopify.com',
            'api_version': '2026-07',
        })

    @classmethod
    def _user(cls, login, group_xmlids):
        groups = [cls.env.ref('base.group_user').id]
        groups += [cls.env.ref(x).id for x in group_xmlids]
        return cls.env['res.users'].create({
            'name': login,
            'login': login,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, groups)],
        })

    def _arch(self, xmlid):
        view = self.env.ref('shopify_connector_sale.%s' % xmlid)
        return etree.fromstring(view.arch_db.encode())

    def _field_names(self, root):
        return {node.get('name') for node in root.iter('field')}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_every_declared_record_exists(self):
        for name in self.MENUS + self.ACTIONS:
            self.assertTrue(
                self.env.ref('shopify_connector_sale.%s' % name, False),
                'shopify_connector_sale.%s is missing' % name,
            )

    def test_customer_matching_lives_under_the_catalog_branch(self):
        """One matching home, not a second one under Orders."""
        menu = self.env.ref(
            'shopify_connector_sale.menu_shopify_connector_customer_binding'
        )
        self.assertEqual(
            menu.parent_id,
            self.env.ref(
                'shopify_connector_product.menu_shopify_connector_catalog'
            ),
        )

    # ------------------------------------------------------------------
    # The dimensions stay separate
    # ------------------------------------------------------------------

    def test_order_list_renders_every_dimension_separately(self):
        rendered = self._field_names(
            self._arch('view_shopify_connector_order_binding_list')
        )
        for name in self.ORDER_DIMENSION_FIELDS:
            self.assertIn(
                name, rendered,
                'the orders list must show %s as its own column' % name,
            )

    def test_cod_list_renders_all_three_cod_dimensions(self):
        rendered = self._field_names(
            self._arch('view_shopify_connector_order_binding_cod_list')
        )
        for name in self.COD_DIMENSION_FIELDS:
            self.assertIn(name, rendered)

    def test_no_view_invents_a_merged_order_state(self):
        """A computed "overall state" would have to pick a winner."""
        for xmlid in (
            'view_shopify_connector_order_binding_list',
            'view_shopify_connector_order_binding_cod_list',
            'view_shopify_connector_order_binding_form',
        ):
            rendered = self._field_names(self._arch(xmlid))
            for invented in (
                'order_state', 'overall_state', 'combined_status',
                'summary_state',
            ):
                self.assertNotIn(invented, rendered)

    def test_order_form_labels_whose_view_of_the_order_each_strip_is(self):
        """"Paid" must never read as "the connector agrees it is paid"."""
        root = self._arch('view_shopify_connector_order_binding_form')
        headings = {
            node.get('string') for node in root.iter('group')
            if node.get('string')
        }
        self.assertIn('What Shopify says', headings)
        self.assertIn('What this connector concluded', headings)

    # ------------------------------------------------------------------
    # SEC-2 PII posture on the customer surface
    # ------------------------------------------------------------------

    def test_customer_views_expose_no_masked_field_or_unmask_affordance(self):
        for xmlid in (
            'view_shopify_connector_customer_binding_search',
            'view_shopify_connector_customer_binding_list',
            'view_shopify_connector_customer_binding_form',
        ):
            root = self._arch(xmlid)
            rendered = self._field_names(root)
            self.assertNotIn('pii_snapshot_masked', rendered)
            for node in root.iter('button'):
                self.assertNotIn(
                    'unmask', (node.get('name') or '').lower(),
                )
                self.assertNotIn(
                    'reveal', (node.get('string') or '').lower(),
                )

    def test_refresh_required_rows_are_filterable(self):
        """A per-record flag is useless for remediating a bulk sweep."""
        partner = self.env['res.partner'].create({'name': 'U2 masked'})
        clean_partner = self.env['res.partner'].create({'name': 'U2 clean'})
        masked = self.CustomerBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/U2Masked',
            'partner_id': partner.id,
            'match_key': 'email',
            'shopify_display_name': '***',
            'shopify_email_snapshot': '***',
            'shopify_phone_snapshot': '***',
        })
        clean = self.CustomerBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/U2Clean',
            'partner_id': clean_partner.id,
            'match_key': 'email',
            'shopify_display_name': 'Real Name',
            'shopify_email_snapshot': 'real@example.com',
            'shopify_phone_snapshot': '+971500000000',
        })
        found = self.CustomerBinding.sudo().search([
            ('store_id', '=', self.store.id),
            ('pii_snapshot_refresh_required', '=', True),
        ])
        self.assertIn(masked, found)
        self.assertNotIn(clean, found)
        # And the negation is the exact complement.
        complement = self.CustomerBinding.sudo().search([
            ('store_id', '=', self.store.id),
            ('pii_snapshot_refresh_required', '=', False),
        ])
        self.assertIn(clean, complement)
        self.assertNotIn(masked, complement)

    # ------------------------------------------------------------------
    # Manual-gateway approval wizard
    # ------------------------------------------------------------------

    def test_approval_wizard_requires_a_reason(self):
        """Optional on the server, mandatory for a human. Deliberate."""
        wizard = self.env[
            'shopify.connector.manual.gateway.approval.wizard'
        ].new({'reason': '  '})
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_approval_wizard_module_contains_no_business_logic(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'wizards', 'shopify_connector_sale_ui_wizards.py',
        )
        with open(path, encoding='utf-8') as handle:
            tree = ast.parse(handle.read(), filename=path)
        called = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        forbidden = {
            'write', 'create', 'unlink', 'sudo', 'commit', 'flush',
            'execute_graphql', 'enqueue',
        }
        self.assertFalse(called & forbidden)
        self.assertIn('action_approve_manual_gateway_order', called)

    # ------------------------------------------------------------------
    # Two-role visibility and outsider denial
    # ------------------------------------------------------------------

    def test_connector_user_reaches_every_action(self):
        user = self._user('u2_sale_user', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_sale.%s' % name)
            self.env[action.res_model].with_user(user).search([], limit=1)

    def test_outsider_is_refused_by_the_server(self):
        outsider = self._user('u2_sale_outsider', [])
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_sale.%s' % name)
            with self.assertRaises(AccessError):
                self.env[action.res_model].with_user(outsider).search(
                    [], limit=1,
                )

    # ------------------------------------------------------------------
    # SEC-3
    # ------------------------------------------------------------------

    def test_quarantined_orders_are_invisible_to_the_running_ui(self):
        # `sale_order_id` is REQUIRED on the binding, so an order binding
        # without an Odoo order cannot exist. The fixture reflects that.
        partner = self.env['res.partner'].create({'name': 'U2 order partner'})

        def _binding(gid):
            order = self.env['sale.order'].create({
                'partner_id': partner.id,
            })
            return self.OrderBinding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': gid,
                'match_key': 'manual',
                'shopify_order_name': gid.rsplit('/', 1)[-1],
                'sale_order_id': order.id,
            })

        visible = _binding('gid://shopify/Order/U2Visible')
        hidden = _binding('gid://shopify/Order/U2Hidden')
        hidden.sudo().write({'sec3_scope_quarantined': True})
        user = self._user('u2_sale_scope', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        ids = self.OrderBinding.with_user(user).search([
            ('store_id', '=', self.store.id),
        ]).ids
        self.assertIn(visible.id, ids)
        self.assertNotIn(hidden.id, ids)
