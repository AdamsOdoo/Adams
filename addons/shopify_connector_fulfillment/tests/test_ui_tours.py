"""U1 rendered-view checks.

These are the server-side half of the U1 render evidence: every U1 view must
actually BUILD for each role (arch validation, field resolution, group
stripping, button/action resolution) rather than merely exist as a record.

The driven browser walk-through, screenshots, responsive/RTL and accessibility
checks are produced separately and recorded in
docs/05-qa/ui-u1-validation-results.md. Passing this file is NOT browser
evidence and must never be recorded as such.
"""

from odoo.tests.common import TransactionCase, tagged

import uuid

U1_VIEWS = (
    ('view_shopify_connector_fulfillment_evidence_search',
     'shopify.connector.fulfillment.inbound.evidence', 'search'),
    ('view_shopify_connector_fulfillment_evidence_list',
     'shopify.connector.fulfillment.inbound.evidence', 'list'),
    ('view_shopify_connector_fulfillment_evidence_form',
     'shopify.connector.fulfillment.inbound.evidence', 'form'),
    ('view_shopify_connector_fulfillment_binding_search',
     'shopify.connector.fulfillment.binding', 'search'),
    ('view_shopify_connector_fulfillment_binding_list',
     'shopify.connector.fulfillment.binding', 'list'),
    ('view_shopify_connector_fulfillment_binding_form',
     'shopify.connector.fulfillment.binding', 'form'),
    ('view_shopify_connector_store_settings_fulfillment_list',
     'shopify.connector.store.settings', 'list'),
    ('view_shopify_connector_store_settings_fulfillment_form',
     'shopify.connector.store.settings', 'form'),
    ('view_shopify_connector_job_fulfillment_search',
     'shopify.connector.job', 'search'),
    ('view_shopify_connector_fulfillment_mode_switch_wizard_form',
     'shopify.connector.fulfillment.mode.switch.wizard', 'form'),
    ('view_shopify_connector_fulfillment_review_release_wizard_form',
     'shopify.connector.fulfillment.review.release.wizard', 'form'),
)


@tagged('post_install', '-at_install')
class TestUiTours(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        base = cls.env.ref('base.group_user').id
        cls.connector_user = cls.env['res.users'].create({
            'name': 'u1 tour user', 'login': 'u1t_user_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [base, cls.env.ref(
                'shopify_connector_core.group_shopify_connector_user').id])],
        })
        cls.connector_admin = cls.env['res.users'].create({
            'name': 'u1 tour admin', 'login': 'u1t_admin_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [base, cls.env.ref(
                'shopify_connector_core.group_shopify_connector_admin').id])],
        })

    def test_every_u1_view_builds_for_both_roles(self):
        # The mode-switch wizard is Administrator-only by ACL -- a Connector
        # User is correctly refused, which the visibility matrix asserts
        # separately. Building it as a User here would assert the opposite of
        # the security contract.
        admin_only = {'view_shopify_connector_fulfillment_mode_switch_wizard_form'}
        for xmlid, model, view_type in U1_VIEWS:
            view = self.env.ref('shopify_connector_fulfillment.%s' % xmlid)
            self.assertEqual(view.model, model)
            self.assertEqual(view.type, view_type)
            roles = ((self.connector_admin,) if xmlid in admin_only
                     else (self.connector_user, self.connector_admin))
            for user in roles:
                result = self.env[model].with_user(user).get_view(
                    view_id=view.id, view_type=view_type,
                )
                self.assertTrue(
                    result.get('arch'),
                    'View %s produced no arch for %s' % (xmlid, user.login),
                )

    def test_every_u1_menu_resolves_to_a_loadable_action(self):
        for xmlid in (
            'menu_shopify_connector_fulfillment_review',
            'menu_shopify_connector_fulfillment_binding',
            'menu_shopify_connector_fulfillment_jobs',
            'menu_shopify_connector_fulfillment_settings',
        ):
            menu = self.env.ref('shopify_connector_fulfillment.%s' % xmlid)
            self.assertTrue(menu.action, '%s has no action' % xmlid)
            self.assertIn(menu.action.res_model, self.env)

    def test_the_fulfillment_branch_hangs_off_the_existing_u0_root(self):
        branch = self.env.ref(
            'shopify_connector_fulfillment.menu_shopify_connector_fulfillment')
        self.assertEqual(
            branch.parent_id,
            self.env.ref('shopify_connector_core.menu_shopify_connector_root'),
            'U1 must not create a second connector app menu.',
        )

    def test_list_views_are_read_only_surfaces(self):
        """U1 never edits a record inline; every change goes through a
        sanctioned action."""
        for xmlid, _model, view_type in U1_VIEWS:
            if view_type not in ('list', 'form'):
                continue
            arch = self.env.ref('shopify_connector_fulfillment.%s' % xmlid).arch
            if 'wizard' in xmlid:
                continue  # wizards are input surfaces by design
            self.assertIn('create="false"', arch, xmlid)
            self.assertIn('edit="false"', arch, xmlid)
