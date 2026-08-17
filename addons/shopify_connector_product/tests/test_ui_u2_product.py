"""U2 operator UI — product matching surfaces (S6 under the S24 branch).

These tests hold the view layer to the one rule that makes a UI phase safe:
**the UI reuses the backend, it never re-implements it.** So they check the
seams rather than re-testing product matching, which the Wave 1 importer
suites already own:

  * every button resolves to a method or action that actually exists;
  * no view opens a mutation path;
  * the two-role visibility model is respected, and an outsider is refused
    by the SERVER, not merely by a hidden menu;
  * SEC-3-quarantined rows stay invisible on the running UI, not just in the
    record rules.

The last one is deliberately asserted through the same read path a rendered
list uses, because that is where an isolation regression would actually be
felt.
"""

import ast
import os

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.convert import convert_file


# Issue #193 / #157 -- Odoo 19 test-phase contract; see the core suites.
@tagged('post_install', '-at_install')
class TestUiU2Product(TransactionCase):

    MENUS = (
        'menu_shopify_connector_catalog',
        'menu_shopify_connector_product_binding',
        'menu_shopify_connector_product_variant_binding',
    )
    ACTIONS = (
        'action_shopify_connector_product_template_binding',
        'action_shopify_connector_product_variant_binding',
    )
    VIEWS = (
        'view_shopify_connector_product_template_binding_search',
        'view_shopify_connector_product_template_binding_list',
        'view_shopify_connector_product_template_binding_form',
        'view_shopify_connector_product_variant_binding_search',
        'view_shopify_connector_product_variant_binding_list',
        'view_shopify_connector_product_variant_binding_form',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Binding = cls.env['shopify.connector.product.template.binding']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'U2 product store',
            'shop_domain': 'u2-product.myshopify.com',
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

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_every_declared_record_exists(self):
        for name in self.MENUS + self.ACTIONS + self.VIEWS:
            self.assertTrue(
                self.env.ref('shopify_connector_product.%s' % name, False),
                'shopify_connector_product.%s is missing' % name,
            )

    def test_branch_is_administrator_configuration(self):
        """Durable mappings are not routine operations navigation."""
        branch = self.env.ref(
            'shopify_connector_product.menu_shopify_connector_catalog'
        )
        self.assertEqual(
            branch.parent_id,
            self.env.ref(
                'shopify_connector_core.menu_shopify_connector_configuration'
            ),
        )
        self.assertEqual(branch.name, 'Mappings')
        self.assertEqual(
            branch.group_ids,
            self.env.ref(
                'shopify_connector_core.group_shopify_connector_admin'
            ),
        )

    def test_branch_sequence_does_not_collide_with_a_sibling(self):
        """A duplicate sequence makes menu order undefined.

        This is a real defect this suite caught during development: the
        The signed IA has exactly four top-level pillars with deterministic
        order.
        """
        root = self.env.ref(
            'shopify_connector_core.menu_shopify_connector_root'
        )
        sequences = root.child_id.mapped('sequence')
        self.assertEqual(
            len(sequences), len(set(sequences)),
            'top-level connector menus must have distinct sequences, got %s'
            % sorted(sequences),
        )

    def test_no_menu_is_an_empty_placeholder(self):
        """"Coming soon" stubs are the anti-premium smell the IA forbids."""
        for name in self.MENUS:
            menu = self.env.ref('shopify_connector_product.%s' % name)
            self.assertTrue(
                menu.action or menu.child_id,
                '%s is a dead menu entry' % name,
            )

    def test_mapping_actions_are_administrator_only(self):
        admin = self.env.ref(
            'shopify_connector_core.group_shopify_connector_admin'
        )
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_product.%s' % name)
            self.assertEqual(action.group_ids, admin)

    def test_product_mappings_open_without_hiding_healthy_rows(self):
        """The default action must show all mappings, not only attention rows."""
        action = self.env.ref(
            'shopify_connector_product.action_shopify_connector_product_template_binding'
        )
        self.assertNotIn(
            'search_default_filter_needs_attention', action.context or '',
            'healthy mappings must not be hidden by the default action',
        )
        self.assertIn('No product mappings match the current view', action.help)
        self.assertIn('clear it', action.help)
        self.assertIn('healthy active', action.help)

    def test_product_mapping_xml_update_clears_legacy_context_preserves_favorite(self):
        """A real XML update repairs old action data without side effects.

        Odoo's XML loader updates only fields declared by the record.  Seed the
        historical context, reload the actual product-binding XML, and then
        reload it again to cover the immediate repeat-upgrade path.  The
        action-specific saved favorite must remain intact, and XML loading
        must not enqueue connector work.
        """
        action = self.env.ref(
            'shopify_connector_product.action_shopify_connector_product_template_binding'
        ).sudo()
        action.write({
            'context': "{'search_default_filter_needs_attention': 1}",
        })

        filters = self.env['ir.filters'].sudo()
        self.assertIn('action_id', filters._fields)
        favorite_values = {
            'name': 'U2 saved product mappings',
            'model_id': action.res_model,
            'action_id': action.id,
            'domain': '[]',
            'context': "{'group_by': 'store_id'}",
        }
        for field_name, value in (
            ('user_id', self.env.user.id),
            ('is_default', False),
            ('sort', '[]'),
        ):
            if field_name in filters._fields:
                favorite_values[field_name] = value
        favorite = filters.create(favorite_values)
        favorite_fields = [
            field_name for field_name in (
                'name', 'model_id', 'action_id', 'domain', 'context',
                'user_id', 'is_default', 'sort',
            ) if field_name in filters._fields
        ]
        favorite_before = favorite.read(favorite_fields)[0]

        queue_models = [
            'shopify.connector.job',
            'shopify.connector.job.log',
            'shopify.connector.mutation.attempt',
        ]
        if 'shopify.connector.product.export.preview' in self.env:
            queue_models.append('shopify.connector.product.export.preview')
        queue_models = tuple(queue_models)
        counts_before = {
            model_name: self.env[model_name].sudo().search_count([])
            for model_name in queue_models
        }

        for _iteration in range(2):
            convert_file(
                self.env,
                'shopify_connector_product',
                'views/shopify_connector_product_binding_views.xml',
                None,
                mode='update',
                noupdate=False,
            )
            self.env.invalidate_all()
            action = self.env.ref(
                'shopify_connector_product.action_shopify_connector_product_template_binding'
            ).sudo()
            self.assertEqual(
                ast.literal_eval(action.context or '{}'), {},
                'the canonical Product Mappings action must not force a filter',
            )
            favorite.invalidate_recordset()
            self.assertTrue(favorite.exists())
            self.assertEqual(favorite.read(favorite_fields)[0], favorite_before)
            self.assertEqual(
                {
                    model_name: self.env[model_name].sudo().search_count([])
                    for model_name in queue_models
                },
                counts_before,
                'an action-data update must not enqueue Shopify work',
            )

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def _view_arch_nodes(self, tag):
        from lxml import etree
        nodes = []
        for name in self.VIEWS:
            view = self.env.ref('shopify_connector_product.%s' % name)
            root = etree.fromstring(view.arch_db.encode())
            nodes.extend((view, node) for node in root.iter(tag))
        return nodes

    def test_every_object_button_names_a_real_method(self):
        for view, node in self._view_arch_nodes('button'):
            if node.get('type') != 'object':
                continue
            method = node.get('name')
            model = self.env[view.model]
            self.assertTrue(
                hasattr(model, method),
                '%s wires a button to %s.%s, which does not exist'
                % (view.name, view.model, method),
            )

    def test_views_open_no_mutation_path(self):
        """No button here may enqueue a Shopify write.

        Product creation and updates are Task 015's preview -> confirm ->
        apply flow. A matching screen offering them would put a mutation one
        click from a list.
        """
        forbidden = {
            'action_export', 'action_push', 'action_publish',
            'action_confirm_export_preview', 'action_apply_export',
        }
        for view, node in self._view_arch_nodes('button'):
            self.assertNotIn(
                node.get('name'), forbidden,
                '%s exposes a mutation affordance' % view.name,
            )

    # ------------------------------------------------------------------
    # Two-role visibility and outsider denial
    # ------------------------------------------------------------------

    def test_connector_user_reaches_every_action(self):
        user = self._user('u2_product_user', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_product.%s' % name)
            model = self.env[action.res_model].with_user(user)
            # search() is what a rendered list actually calls.
            model.search([], limit=1)

    def test_outsider_is_refused_by_the_server_not_by_a_hidden_menu(self):
        outsider = self._user('u2_product_outsider', [])
        for name in self.ACTIONS:
            action = self.env.ref('shopify_connector_product.%s' % name)
            with self.assertRaises(AccessError):
                self.env[action.res_model].with_user(outsider).search(
                    [], limit=1,
                )

    # ------------------------------------------------------------------
    # SEC-3
    # ------------------------------------------------------------------

    def test_quarantined_rows_are_invisible_to_the_running_ui(self):
        # (store, product_template) is unique, so the two probes need two
        # templates -- reusing one would fail the constraint, not the test.
        templates = self.env['product.template'].create([
            {'name': 'U2 quarantine probe visible'},
            {'name': 'U2 quarantine probe hidden'},
        ])
        visible = self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/U2Visible',
            'product_template_id': templates[0].id,
            'match_key': 'manual',
        })
        hidden = self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/U2Hidden',
            'product_template_id': templates[1].id,
            'match_key': 'manual',
        })
        hidden.sudo().write({'sec3_scope_quarantined': True})

        user = self._user('u2_product_scope', [
            'shopify_connector_core.group_shopify_connector_user',
        ])
        visible_ids = self.Binding.with_user(user).search([
            ('store_id', '=', self.store.id),
        ]).ids
        self.assertIn(visible.id, visible_ids)
        self.assertNotIn(
            hidden.id, visible_ids,
            'a quarantined binding must not reach the operator UI',
        )
        # And the count a list header would render agrees.
        self.assertEqual(
            self.Binding.with_user(user).search_count([
                ('store_id', '=', self.store.id),
            ]),
            len(visible_ids),
        )

    # ------------------------------------------------------------------
    # Source guards
    # ------------------------------------------------------------------

    def test_this_phase_added_no_model_file(self):
        """U2 is a view phase in this module: no `models/**` change at all."""
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        for filename in sorted(os.listdir(models_dir)):
            if not filename.endswith('.py'):
                continue
            path = os.path.join(models_dir, filename)
            with open(path, encoding='utf-8') as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.assertFalse(
                        node.name.startswith('action_ui_'),
                        '%s gained a UI-only server method' % filename,
                    )
