"""S1: the guided setup wizard, driven in a real browser.

The server tests in `test_setup_wizard.py` prove every step's method is correct
and correctly guarded. They cannot prove there is a control that reaches it.

That distinction is the whole reason S1 was recorded as not implemented while
its pieces existed: a credential service, a readiness registry, settings
fields and an activation contract were all present and correct, and there was
no route through them. A browser is the only place "the operator can get from
nothing to an activated store" is a testable claim.

These tours contact no Shopify store. Step 5's probe is answered by a
stand-in installed on the module's existing `_send` transport seam before the
browser starts, so the real client, the real admission gate and the real
response taxonomy all run with only the socket absent.
"""

from unittest.mock import patch

from odoo.tests.common import HttpCase, new_test_user, tagged

from .test_api_client import FakeResponse

TOUR_SHOP_DOMAIN = 's1-tour.myshopify.com'
RESUME_SHOP_DOMAIN = 's1-resume.myshopify.com'


@tagged('post_install', '-at_install', 'shopify_connector_s1')
class TestUiSetupTours(HttpCase):

    def _admin(self, login):
        user = new_test_user(
            self.env, login=login, password=login,
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_admin',
        )
        user.sudo().write({
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
        })
        return user

    def _transport(self, domain):
        """Answer the ONE transport method locally, for exactly one domain.

        The granted-scope set is the connector's OWN declaration rather than a
        hand-written list: the traversal has to reach activation, and
        `required_scopes` is an essential readiness check, so a fixture that
        granted fewer scopes than the connector requires would block the tour
        for a reason that has nothing to do with the wizard.
        """
        Client = type(self.env['shopify.connector.api.client'])
        scopes = self.env[
            'shopify.connector.readiness.check'
        ].REQUIRED_MVP_SCOPES
        response = FakeResponse(200, json_body={
            'data': {
                'shop': {
                    'id': 'gid://shopify/Shop/1',
                    'name': 'S1 Tour Shop',
                    'myshopifyDomain': domain,
                },
                'currentAppInstallation': {
                    'accessScopes': [
                        {'handle': scope} for scope in scopes
                    ],
                },
            },
        })

        def responder(_self, _store, request, token=None,
                      mutation_context=None):
            return response

        return patch.object(Client, '_send', responder)

    def _make_readiness_passable(self):
        """Satisfy the environment-owned essential checks.

        `web.base.url` is an essential check and a test server's default is
        plain HTTP, so without this the traversal is blocked by the ENVIRONMENT
        rather than by anything the wizard did -- and a tour that can never
        reach activation cannot prove activation is reachable.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://s1-tour.example.test',
        )

    def test_setup_wizard_traverses_all_eleven_steps(self):
        """Nothing to an activated store, through the browser, in order.

        The tour asserts the step COUNT as well as each step's name at every
        stop ("Step 4 of 11"), so a dropped, added or reordered step fails
        here rather than passing quietly.
        """
        self._admin('s1_tour_admin')
        self._make_readiness_passable()
        self.env.flush_all()
        with self._transport(TOUR_SHOP_DOMAIN):
            self.start_tour(
                '/odoo', 'shopify_connector_s1_setup_tour',
                login='s1_tour_admin',
            )
        store = self.env['shopify.connector.store'].sudo().search(
            [('shop_domain', '=', TOUR_SHOP_DOMAIN)], limit=1,
        )
        self.assertTrue(store, 'the browser traversal created no store')
        self.assertEqual(
            store.state, 'connected',
            'the traversal did not reach an activated store',
        )
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        self.assertTrue(settings.setup_completed_at)
        self.assertEqual(settings.setup_completed_uid.login, 's1_tour_admin')
        self.assertTrue(
            settings.sale_domain_enabled,
            'the direction chosen in the browser did not persist',
        )
        self.assertEqual(settings.product_first_sync_source, 'odoo_source')
        self.assertEqual(settings.price_source_of_truth, 'odoo_authoritative')
        self.assertFalse(
            settings.notification_default_enabled,
            'the notification default must stay off unless opted into',
        )
        # Activation starts nothing.
        self.assertFalse(
            self.env['shopify.connector.job'].sudo().search([
                ('store_id', '=', store.id),
                ('state', 'in', ('queued', 'running')),
            ]),
            'activation enqueued a job',
        )
        # And the credential never came back out.
        logs = self.env['shopify.connector.job.log'].sudo().search([
            ('store_id', '=', store.id),
        ])
        blob = ' '.join(
            (logs.mapped('message') or [])
            + [str(v) for v in logs.mapped('technical_detail') if v]
            + [str(v) for v in logs.mapped('payload_snapshot') if v]
        )
        self.assertNotIn('shpat_', blob, 'a token reached the audit trail')

    def test_the_dashboard_empty_state_opens_setup(self):
        """Entry route 1 of 3, clicked rather than asserted from a payload."""
        self._admin('s1_dash_admin')
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_dashboard_entry_tour',
            login='s1_dash_admin',
        )

    def _seed_resumable_store(self):
        """A store left mid-setup at step 7, with one direction saved."""
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'S1 Resume Store',
            'shop_domain': RESUME_SHOP_DOMAIN,
            'company_id': self.env.company.id,
        })
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'sale_domain_enabled': True,
            'setup_wizard_step': 7,
        })
        return store

    def test_setup_resumes_at_the_step_it_was_left_on(self):
        """Save & Exit and resume, observed in the browser.

        Durable progress is only durable if the NEXT session sees it, which is
        why the resume point is a column on the settings record rather than
        anything in this browser's storage.
        """
        self._admin('s1_resume_admin')
        store = self._seed_resumable_store()
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_resume_tour',
            login='s1_resume_admin',
        )
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        self.assertGreaterEqual(
            settings.setup_wizard_step, 7,
            'Save & Exit rewound the resume point',
        )
        self.assertTrue(
            settings.sale_domain_enabled,
            'resuming discarded a saved choice',
        )

    def test_setup_is_operable_by_keyboard_alone(self):
        """Full keyboard traversal, and focus moves to the step heading.

        Asserted in the page rather than inferred from the stylesheet: a
        `tabindex` that exists in the template and a heading that actually
        receives focus after an advance are different claims.
        """
        self._admin('s1_keyboard_admin')
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_keyboard_tour',
            login='s1_keyboard_admin',
        )
