"""U2 operator UI — inventory surfaces (S10 mapping, S11 guard, S19 workspace).

Same posture as the product U2 suite: hold the seams, not the domain logic.
Two things here need more than structural checks, because getting them wrong
would be dangerous rather than merely wrong:

  * **the first-push guard.** RA-008 exists because a blind first push
    overwrites a live storefront's quantities. The guard must be its own
    surface with its own filter, and its confirm action must be the
    server's, never a field write from a view.
  * **the two display-and-delegate wizards.** They exist only because two
    sanctioned server methods take required arguments that an Odoo object
    button cannot pass. A source guard asserts they stayed delegators and
    did not quietly grow logic.
"""

import ast
import os

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


# Issue #193 / #157 -- Odoo 19 test-phase contract; see the core suites.
@tagged('post_install', '-at_install')
class TestUiU2Inventory(TransactionCase):

    MENUS = (
        'menu_shopify_connector_inventory',
        'menu_shopify_connector_inventory_workspace',
        'menu_shopify_connector_inventory_first_push',
        'menu_shopify_connector_location_mapping',
    )
    ACTIONS = (
        'action_shopify_connector_inventory_workspace',
        'action_shopify_connector_inventory_first_push',
        'action_shopify_connector_location_mapping',
    )
    WIZARD_ACTIONS = (
        'action_shopify_connector_location_push_toggle_wizard',
        'action_shopify_connector_inventory_recheck_wizard',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mapping = cls.env['shopify.connector.location.mapping']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'U2 inventory store',
            'shop_domain': 'u2-inventory.myshopify.com',
            'api_version': '2026-07',
        })
        # `odoo_location_id` is REQUIRED on the mapping, so an "unmapped"
        # mapping row cannot exist. The fixture reflects that rather than
        # working around it.
        parent = cls.env['stock.location'].search(
            [('usage', '=', 'view')], limit=1,
        )
        # (store, odoo_location) is unique too, so each probe needs its own
        # Odoo location.
        cls.odoo_locations = cls.env['stock.location'].create([
            {'name': 'U2 loc A', 'usage': 'internal',
             'location_id': parent.id},
            {'name': 'U2 loc B', 'usage': 'internal',
             'location_id': parent.id},
        ])
        cls.odoo_location = cls.odoo_locations[0]

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

    def _mapping(self, gid='gid://shopify/Location/U2', location=None):
        return self.Mapping.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': gid,
            'match_key': 'manual',
            'shopify_location_name_snapshot': 'U2 warehouse',
            'odoo_location_id': (location or self.odoo_location).id,
        })

    # ------------------------------------------------------------------
    # Registration and structure
    # ------------------------------------------------------------------

    def test_every_declared_record_exists(self):
        for name in self.MENUS + self.ACTIONS + self.WIZARD_ACTIONS:
            self.assertTrue(
                self.env.ref('shopify_connector_inventory.%s' % name, False),
                'shopify_connector_inventory.%s is missing' % name,
            )

    def test_first_push_guard_is_its_own_filtered_surface(self):
        """RA-008: the ceremony must not be buried in the routine queue."""
        guard = self.env.ref(
            'shopify_connector_inventory.'
            'action_shopify_connector_inventory_first_push'
        )
        workspace = self.env.ref(
            'shopify_connector_inventory.'
            'action_shopify_connector_inventory_workspace'
        )
        self.assertNotEqual(guard.id, workspace.id)
        self.assertIn('first_push_state', guard.domain or '')
        self.assertIn('pending', guard.domain or '')

    # ------------------------------------------------------------------
    # Wizards: they must delegate, and only delegate
    # ------------------------------------------------------------------

    def test_push_toggle_wizard_delegates_to_the_sanctioned_action(self):
        mapping = self._mapping()
        admin = self._user('u2_inv_admin', [
            'shopify_connector_core.group_shopify_connector_admin',
        ])
        Wizard = self.env[
            'shopify.connector.location.push.toggle.wizard'
        ].with_user(admin).with_context(
            active_model='shopify.connector.location.mapping',
            active_id=mapping.id,
        )
        wizard = Wizard.create({})
        self.assertEqual(wizard.mapping_id, mapping)
        # The default is the OPPOSITE of the current state: the operator
        # opened the dialog to change something.
        before = mapping.push_enabled
        self.assertEqual(wizard.target_enabled, not before)
        wizard.action_confirm()
        mapping.invalidate_recordset()
        self.assertEqual(
            mapping.push_enabled, not before,
            'confirming the wizard must apply the state it displayed',
        )

    def test_recheck_wizard_requires_a_reason(self):
        """The reason lands on an audit trail, so blank is refused."""
        Wizard = self.env['shopify.connector.inventory.recheck.wizard']
        wizard = Wizard.new({'reason': '   '})
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_wizards_are_transient_and_own_no_table_of_record(self):
        for model_name in (
            'shopify.connector.location.push.toggle.wizard',
            'shopify.connector.inventory.recheck.wizard',
        ):
            model = self.env[model_name]
            self.assertTrue(
                model._transient,
                '%s must be a TransientModel' % model_name,
            )

    def test_wizard_module_contains_no_business_logic(self):
        """A delegator writes nothing and decides nothing.

        Asserted against the AST rather than by reading: the failure mode is
        somebody later "just adding" a write here, where it would bypass the
        server method's access checks and audit.
        """
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'wizards', 'shopify_connector_inventory_ui_wizards.py',
        )
        with open(path, encoding='utf-8') as handle:
            tree = ast.parse(handle.read(), filename=path)
        called = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(
            called & {
                'write', 'create', 'unlink', 'sudo', 'flush', 'commit',
                'execute_graphql', 'enqueue',
            },
            'the inventory UI wizards must only delegate, but call %s'
            % sorted(called & {
                'write', 'create', 'unlink', 'sudo', 'flush', 'commit',
                'execute_graphql', 'enqueue',
            }),
        )
        # And they must call exactly the sanctioned server actions.
        self.assertTrue({
            'action_set_push_enabled', 'action_recheck_inventory_pair',
        } <= called)

    # ------------------------------------------------------------------
    # Two-role visibility and outsider denial
    # ------------------------------------------------------------------

    def test_connector_user_reaches_every_action(self):
        user = self._user('u2_inv_user', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_inventory.%s' % name)
            self.env[action.res_model].with_user(user).search([], limit=1)

    def test_outsider_is_refused_by_the_server(self):
        outsider = self._user('u2_inv_outsider', [])
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_inventory.%s' % name)
            with self.assertRaises(AccessError):
                self.env[action.res_model].with_user(outsider).search(
                    [], limit=1,
                )

    def test_push_toggle_gating_matches_the_server_guard_exactly(self):
        """The view must gate on what the SERVER permits, not on a doc.

        `action_set_push_enabled` admits Operator or Administrator. The
        premium UX master specification lists this screen as User-read /
        Administrator-act, which disagrees. This test pins the view to the
        server: an auditor-only caller is refused, and a Connector User --
        who implies Operator -- is permitted. If the server guard is ever
        tightened to Administrator, this test fails and the button's
        `groups=` has to move with it.
        """
        mapping = self._mapping('gid://shopify/Location/U2Denied')
        auditor = self._user('u2_inv_auditor', [
            'shopify_connector_core.group_shopify_connector_auditor',
        ])
        before = mapping.push_enabled
        with self.assertRaises(AccessError):
            mapping.with_user(auditor).action_set_push_enabled(not before)
        mapping.invalidate_recordset()
        self.assertEqual(
            mapping.push_enabled, before,
            'a refused toggle must leave the mapping untouched',
        )

        connector_user = self._user('u2_inv_user_allowed', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        self.assertTrue(connector_user.has_group(
            'shopify_connector_core.group_shopify_connector_operator'
        ), 'Connector User must imply Operator for this gating to hold')
        mapping.with_user(connector_user).action_set_push_enabled(not before)
        mapping.invalidate_recordset()
        self.assertEqual(mapping.push_enabled, not before)

    # ------------------------------------------------------------------
    # SEC-3
    # ------------------------------------------------------------------

    def test_quarantined_mappings_are_invisible_to_the_running_ui(self):
        visible = self._mapping(
            'gid://shopify/Location/U2Visible', self.odoo_locations[0],
        )
        hidden = self._mapping(
            'gid://shopify/Location/U2Hidden', self.odoo_locations[1],
        )
        hidden.sudo().write({'sec3_scope_quarantined': True})
        user = self._user('u2_inv_scope', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        ids = self.Mapping.with_user(user).search([
            ('store_id', '=', self.store.id),
        ]).ids
        self.assertIn(visible.id, ids)
        self.assertNotIn(hidden.id, ids)
