"""U1 acceptance A4/A5 -- the two-layer authorization proof.

Layer 1 (visibility): a Connector User and a Connector Administrator are offered
different affordances, asserted against the EFFECTIVE runtime rule set -- what
`has_group` actually returns after implied-group closure -- not against the
union of declared groups (OQ-4).

Layer 2 (authorization): the server refuses a direct ORM/RPC call from a caller
without the internal capability group, with `AccessError` and ZERO side effects,
whether or not any button was ever rendered. A hidden button is never the
security control.
"""

import uuid

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

USER_ROLE = 'shopify_connector_core.group_shopify_connector_user'
ADMIN_ROLE = 'shopify_connector_core.group_shopify_connector_admin'
G_AUDITOR = 'shopify_connector_core.group_shopify_connector_auditor'
G_OPERATOR = 'shopify_connector_core.group_shopify_connector_operator'
G_REVIEWER = 'shopify_connector_core.group_shopify_connector_reviewer'


@tagged('post_install', '-at_install')
class TestUiVisibilityMatrix(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'U1 vis',
            'shop_domain': 'u1v-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })
        base = cls.env.ref('base.group_user').id

        def _mk(login, role_xmlid):
            groups = [base]
            if role_xmlid:
                groups.append(cls.env.ref(role_xmlid).id)
            return cls.env['res.users'].create({
                'name': login,
                'login': '%s_%s' % (login, uuid.uuid4().hex),
                'group_ids': [(6, 0, groups)],
            })

        cls.connector_user = _mk('u1_user', USER_ROLE)
        cls.connector_admin = _mk('u1_admin', ADMIN_ROLE)
        cls.outsider = _mk('u1_outsider', None)

    # ------------------------------------------------ implied-group closure

    def test_connector_user_resolves_to_operator_and_auditor_only(self):
        """User is routine operational, never Reviewer-capable."""
        user = self.connector_user
        for internal in (G_OPERATOR, G_AUDITOR):
            self.assertTrue(
                user.has_group(internal),
                'Connector User must resolve to %s' % internal,
            )
        self.assertFalse(user.has_group(G_REVIEWER))
        self.assertFalse(
            user.has_group(ADMIN_ROLE),
            'Connector User must NOT resolve to Administrator.',
        )

    def test_connector_admin_resolves_to_every_internal_group(self):
        admin = self.connector_admin
        for internal in (G_OPERATOR, G_REVIEWER, G_AUDITOR):
            self.assertTrue(admin.has_group(internal))
        self.assertTrue(
            admin.has_group(USER_ROLE),
            'Administrator implies the Connector User role.',
        )

    def test_outsider_resolves_to_no_connector_group(self):
        for group in (USER_ROLE, ADMIN_ROLE, G_OPERATOR, G_REVIEWER, G_AUDITOR):
            self.assertFalse(self.outsider.has_group(group))

    # ------------------------------------------------------------ visibility

    def test_fulfillment_menu_visibility_follows_the_two_roles(self):
        menu = self.env.ref(
            'shopify_connector_fulfillment.menu_shopify_connector_fulfillment'
        )
        self.assertEqual(
            menu.group_ids.mapped('id'), [self.env.ref(USER_ROLE).id],
            'The U1 menu must gate on the Connector User role only.',
        )
        visible_user = self.env['ir.ui.menu'].with_user(
            self.connector_user)._visible_menu_ids()
        visible_admin = self.env['ir.ui.menu'].with_user(
            self.connector_admin)._visible_menu_ids()
        visible_outsider = self.env['ir.ui.menu'].with_user(
            self.outsider)._visible_menu_ids()
        self.assertIn(menu.id, visible_user)
        self.assertIn(menu.id, visible_admin)
        self.assertNotIn(
            menu.id, visible_outsider,
            'A user outside every connector group must not see the menu.',
        )

    def test_mode_fields_are_administrator_only_for_a_connector_user(self):
        """Odoo strips `groups=`-restricted fields from a non-holder's view."""
        user_fields = self.env['shopify.connector.store.settings'].with_user(
            self.connector_user).fields_get()
        admin_fields = self.env['shopify.connector.store.settings'].with_user(
            self.connector_admin).fields_get()
        for restricted in (
            'fulfillment_operating_mode', 'fulfillment_switch_in_progress',
            'fulfillment_mode_switch_nonce',
            'fulfillment_requested_mode',
            'fulfillment_mode_switch_state',
            'fulfillment_mode_switch_job_id',
            'fulfillment_mode_switch_failure_reason',
            'fulfillment_mode_switch_next_action',
            'fulfillment_mode_switch_next_retry_at',
            'fulfillment_mode_switch_is_stale',
            'fulfillment_mode_switch_verified_at',
        ):
            self.assertNotIn(
                restricted, user_fields,
                '%s must be invisible to a Connector User.' % restricted,
            )
            self.assertIn(
                restricted, admin_fields,
                '%s must be available to a Connector Administrator.' % restricted,
            )

    def test_u1_views_render_for_both_roles(self):
        """The screens must actually build for each role, not just exist."""
        for user in (self.connector_user, self.connector_admin):
            for xmlid in (
                'shopify_connector_fulfillment.view_shopify_connector_fulfillment_evidence_list',
                'shopify_connector_fulfillment.view_shopify_connector_fulfillment_evidence_form',
                'shopify_connector_fulfillment.view_shopify_connector_fulfillment_binding_list',
                'shopify_connector_fulfillment.view_shopify_connector_fulfillment_binding_form',
            ):
                view = self.env.ref(xmlid)
                arch = self.env[view.model].with_user(user).get_view(
                    view_id=view.id, view_type=view.type,
                )
                self.assertTrue(arch.get('arch'))

    # --------------------------------------------------------- authorization

    def test_direct_rpc_mode_switch_is_denied_for_a_connector_user(self):
        """The decisive test: bypass the UI entirely and call the server."""
        settings = self.settings.with_user(self.connector_user)
        before_mode = self.settings.fulfillment_operating_mode
        before_jobs = self.env['shopify.connector.job'].search_count([
            ('store_id', '=', self.store.id),
        ])
        with self.assertRaises(AccessError):
            settings.action_start_mode2_switch()
        # Zero side effects.
        self.settings.invalidate_recordset()
        self.assertEqual(self.settings.fulfillment_operating_mode, before_mode)
        self.assertFalse(self.settings.fulfillment_switch_in_progress)
        self.assertFalse(self.settings.fulfillment_mode_switch_nonce)
        self.assertFalse(self.settings.fulfillment_requested_mode)
        self.assertFalse(self.settings.fulfillment_mode_switch_job_id)
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('store_id', '=', self.store.id),
            ]),
            before_jobs,
            'A denied mode switch must not enqueue a job.',
        )

    def test_direct_rpc_rollback_is_denied_for_a_connector_user(self):
        with self.assertRaises(AccessError):
            self.settings.with_user(self.connector_user).action_rollback_to_mode1()

    def test_mode_switch_is_allowed_for_a_connector_administrator(self):
        settings = self.settings.with_user(self.connector_admin)
        settings.action_start_mode2_switch()
        self.settings.invalidate_recordset()
        self.assertTrue(
            self.settings.fulfillment_switch_in_progress,
            'The Administrator path must actually work -- otherwise the '
            'negative tests above would pass vacuously.',
        )

    def test_outsider_cannot_read_any_u1_model(self):
        for model in (
            'shopify.connector.fulfillment.inbound.evidence',
            'shopify.connector.fulfillment.binding',
            'shopify.connector.store.settings',
        ):
            with self.assertRaises(AccessError):
                self.env[model].with_user(self.outsider).search([], limit=1)

    def test_no_privilege_escalation_through_the_wizard(self):
        """A Connector User may not reach an Administrator action by creating
        the wizard directly -- the wizard's own ACL and the sanctioned action
        both refuse."""
        Wizard = self.env['shopify.connector.fulfillment.mode.switch.wizard']
        with self.assertRaises(AccessError):
            Wizard.with_user(self.connector_user).create({
                'settings_id': self.settings.id, 'target_mode': 'mode2',
            })
