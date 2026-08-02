"""U1 action wiring -- every button reaches a real sanctioned action, and the
wizards delegate without deciding anything.
"""

import uuid

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

USER_ROLE = 'shopify_connector_core.group_shopify_connector_user'
ADMIN_ROLE = 'shopify_connector_core.group_shopify_connector_admin'


@tagged('post_install', '-at_install')
class TestUiActions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'U1 act',
            'shop_domain': 'u1a-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })
        base = cls.env.ref('base.group_user').id
        cls.admin_user = cls.env['res.users'].create({
            'name': 'u1 admin', 'login': 'u1act_admin_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [base, cls.env.ref(ADMIN_ROLE).id])],
        })
        cls.plain_user = cls.env['res.users'].create({
            'name': 'u1 user', 'login': 'u1act_user_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [base, cls.env.ref(USER_ROLE).id])],
        })

    # -------------------------------------------------------------- actions

    def test_every_sanctioned_action_exists_on_its_model(self):
        Evidence = self.env['shopify.connector.fulfillment.inbound.evidence']
        Binding = self.env['shopify.connector.fulfillment.binding']
        Settings = self.env['shopify.connector.store.settings']
        for model, method in (
            (Settings, 'action_start_mode2_switch'),
            (Settings, 'action_retry_mode2_switch'),
            (Settings, 'action_rollback_to_mode1'),
            (Binding, 'action_release_fulfillment_review'),
            (Evidence, 'action_import_tracking'),
            (Evidence, 'action_acknowledge_external'),
            (Evidence, 'action_validate_proposed'),
        ):
            self.assertTrue(
                callable(getattr(model, method, None)),
                'Sanctioned action %s is missing -- U1 wires to it.' % method,
            )

    def test_failed_or_running_switch_has_a_direct_return_to_mode1_control(self):
        view = self.env.ref(
            'shopify_connector_fulfillment.'
            'view_shopify_connector_store_settings_fulfillment_form'
        )
        arch = etree.fromstring(view.arch_db.encode())
        buttons = arch.xpath(
            "//button[@name='action_rollback_to_mode1' and @type='object']"
        )
        self.assertEqual(
            len(buttons), 1,
            'A failed/running switch must expose the sanctioned server '
            'rollback directly; the effective-Mode-derived wizard would '
            'request Mode 2 again while Mode 1 is still effective.',
        )
        invisible = buttons[0].get('invisible') or ''
        self.assertIn('fulfillment_switch_in_progress', invisible)
        self.assertIn('fulfillment_mode_switch_state', invisible)
        self.assertNotEqual(
            invisible.strip(), "fulfillment_operating_mode != 'mode2'",
            'Return to Mode 1 must not disappear merely because the failed '
            'switch correctly kept Mode 1 effective.',
        )
        self.assertTrue(buttons[0].get('confirm'))

    def test_all_u1_act_windows_resolve_to_an_existing_model(self):
        for xmlid in (
            'action_shopify_connector_fulfillment_review',
            'action_shopify_connector_fulfillment_binding',
            'action_shopify_connector_fulfillment_job',
            'action_shopify_connector_fulfillment_settings',
            'action_shopify_connector_fulfillment_mode_switch',
            'action_shopify_connector_fulfillment_review_release',
        ):
            action = self.env.ref('shopify_connector_fulfillment.%s' % xmlid)
            self.assertIn(action.res_model, self.env)

    def test_fulfillment_job_action_domain_names_exactly_the_ten_job_types(self):
        from odoo.addons.shopify_connector_fulfillment.models import (
            shopify_connector_job as job_module,
        )
        action = self.env.ref(
            'shopify_connector_fulfillment.action_shopify_connector_fulfillment_job'
        )
        domain = eval(action.domain)  # noqa: S307 -- static, test-local literal
        self.assertEqual(len(domain), 1)
        _field, _op, values = domain[0]
        self.assertEqual(
            sorted(values), sorted(job_module.FULFILLMENT_JOB_TYPES),
            'The U1 job screen must list exactly the ten declared fulfillment '
            'job types -- no more, no fewer, none invented.',
        )

    # -------------------------------------------------------------- wizards

    def test_mode_switch_wizard_targets_the_other_mode(self):
        Wizard = self.env['shopify.connector.fulfillment.mode.switch.wizard']
        wizard = Wizard.with_user(self.admin_user).with_context(
            default_settings_id=self.settings.id,
        ).create({'settings_id': self.settings.id})
        self.assertEqual(self.settings.fulfillment_operating_mode, 'mode1')
        self.assertEqual(
            wizard.target_mode, 'mode2',
            'From Mode 1 the only target is Mode 2 -- derived, never chosen.',
        )

    def test_mode_switch_wizard_confirm_delegates_to_the_sanctioned_action(self):
        Wizard = self.env['shopify.connector.fulfillment.mode.switch.wizard']
        wizard = Wizard.with_user(self.admin_user).with_context(
            default_settings_id=self.settings.id,
        ).create({'settings_id': self.settings.id})
        wizard.action_confirm()
        self.settings.invalidate_recordset()
        self.assertTrue(
            self.settings.fulfillment_switch_in_progress,
            'Confirm must reach action_start_mode2_switch.',
        )
        self.assertTrue(self.settings.fulfillment_mode_switch_nonce)

    def test_mode_switch_wizard_counts_are_non_authoritative_reads(self):
        Wizard = self.env['shopify.connector.fulfillment.mode.switch.wizard']
        wizard = Wizard.with_user(self.admin_user).with_context(
            default_settings_id=self.settings.id,
        ).create({'settings_id': self.settings.id})
        # No data -> zero. The point is that the wizard READ them rather than
        # deciding anything from them: confirming still works at zero.
        self.assertEqual(wizard.open_review_count, 0)
        self.assertEqual(wizard.in_flight_job_count, 0)
        wizard.action_confirm()
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.fulfillment_switch_in_progress)

    def test_release_wizard_requires_a_non_empty_reason(self):
        binding = self._make_binding()
        Wizard = self.env['shopify.connector.fulfillment.review.release.wizard']
        wizard = Wizard.with_user(self.plain_user).create({
            'binding_id': binding.id, 'reason': '   ',
        })
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_release_wizard_delegates_and_lets_the_server_refuse(self):
        """There is no blocked mutation, so the SERVER refuses. The wizard must
        surface that refusal rather than pre-judging eligibility itself."""
        binding = self._make_binding()
        Wizard = self.env['shopify.connector.fulfillment.review.release.wizard']
        wizard = Wizard.with_user(self.plain_user).create({
            'binding_id': binding.id, 'reason': 'operator decided',
        })
        # `plain_user` holds the Connector User role, which resolves to
        # Reviewer, so the ROLE check passes and the server refuses on the
        # precondition instead: there is no blocked mutation for this binding.
        # (Odoo's assertRaises does not accept a tuple of exception types.)
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def _make_binding(self):
        partner = self.env['res.partner'].create({'name': 'U1 C'})
        sale = self.env['sale.order'].create({'partner_id': partner.id})
        order_binding = self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Order/%s' % uuid.uuid4().hex,
            'sale_order_id': sale.id, 'status': 'active',
        })
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'sale_id': sale.id,
        })
        return self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/%s' % uuid.uuid4().hex,
            'picking_id': picking.id,
            'order_binding_id': order_binding.id,
            'status': 'active',
        })
