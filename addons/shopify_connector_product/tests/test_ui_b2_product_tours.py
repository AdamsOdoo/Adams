"""Batch 2 §10 -- driven-browser evidence for the catalog surfaces.

Three surfaces, each reached the way an operator reaches it:

  * the product import controls on the store form,
  * the pending product match decision, opened from the job that is stopped,
  * the resolved binding the decision produced.

THE FIXTURE IS PRODUCED BY PRODUCTION CODE. The pending decision below is not
hand-written: the real importer meets two Odoo products carrying the same SKU,
the real dispatcher routes the failure, and the real `_route_failure` seam
records the decision. A hand-built row would let these tours pass against a
shape the product no longer produces.

NO SHOPIFY. Transport is patched at `_send` while the fixture is built, and
the browser steps enqueue job ROWS at most -- no tour starts a dispatcher, and
the store's only credential is a non-secret test constant.
"""

import copy
import uuid
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
STAMP = '2026-07-30T10:00:00Z'

# Batch 2 correction (F1/F2/F3): PRODUCTION-SHAPED identity in the browser.
#
# These seeds used to be `gid://shopify/Product/TOUR` and `TOUR-DUP` -- two of
# the very few shapes `safe_match_preview`'s phone pattern does NOT rewrite, so
# the browser evidence proved the route worked for identities no Shopify store
# issues. A real Product GID carries a 13-digit suffix and a real SKU is
# routinely all digits; both are rewritten by that scrubber, which is what made
# the decision unconsumable. The tour now drives those shapes end to end, and
# asserts on screen that the display preview IS sanitized while the identity
# beside it is NOT.
TOUR_PRODUCT_GID = 'gid://shopify/Product/7346299043911'
TOUR_DONE_GID = 'gid://shopify/Product/7346299043928'
TOUR_NUMERIC_SKU = '1234567890123'
TOUR_REDACTED_SKU_PREVIEW = '[redacted-phone]'
STORE_ACTION = 'shopify_connector_core.action_shopify_connector_store'
JOB_ACTION = 'shopify_connector_core.action_shopify_connector_error_center'
BINDING_ACTION = (
    'shopify_connector_product.action_shopify_connector_product_template_binding'
)


class _FakeSendResponse:

    def __init__(self, body):
        self._body = body
        self.status_code = 200
        self.headers = {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install', 'shopify_connector_b2_tours')
class TestUiB2ProductTours(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'B2 tour store',
            'shop_domain': 'b2-product-tour.myshopify.com',
            'api_version': '2026-07',
            'company_id': cls.env.company.id,
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        cls.store.write({'state': 'connected'})
        cls.Job = cls.env['shopify.connector.job']
        cls.Decision = cls.env['shopify.connector.product.match.decision']
        cls.TemplateBinding = cls.env[
            'shopify.connector.product.template.binding'
        ]
        cls.operator = cls._tour_user(
            'b2prod_operator', 'group_shopify_connector_operator',
        )
        cls.reviewer = cls._tour_user(
            'b2prod_reviewer', 'group_shopify_connector_reviewer',
        )
        cls.auditor = cls._tour_user(
            'b2prod_auditor', 'group_shopify_connector_auditor',
        )

    @classmethod
    def _tour_user(cls, login, group):
        return cls.env['res.users'].create({
            'name': login,
            'login': login,
            'password': login,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            # EXACTLY the role under test, and that is load bearing.
            # `group_shopify_connector_user` implies BOTH Operator and
            # Reviewer (`shopify_connector_security.xml`), so adding it "so
            # the menus work" hands an auditor the operator control and an
            # operator the reviewer control -- and both denied-role tours then
            # measure a fixture that granted what it was written to refuse.
            # Every tour below opens its surface by URL and needs no menu.
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % group).id,
            ])],
        })

    def _url(self, action_xmlid, res_id=None):
        url = '/odoo/action-%s' % action_xmlid
        return '%s/%d' % (url, res_id) if res_id else url

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------

    def _product(self, name, sku):
        template = self.env['product.template'].create({'name': name})
        template.product_variant_id.write({'default_code': sku})
        return template

    def _body(self, gid, sku):
        return {'data': {'product': {
            'id': gid, 'title': 'Tour ambiguous product', 'status': 'ACTIVE',
            'updatedAt': STAMP, 'descriptionHtml': '', 'vendor': '',
            'productType': '', 'tags': [], 'featuredImage': None,
            'options': [],
            'variants': {
                'nodes': [{
                    'id': '%s-v' % gid, 'sku': sku, 'barcode': None,
                    'price': '9.99', 'compareAtPrice': None,
                    'selectedOptions': [], 'image': None,
                    'inventoryItem': {'id': 'gid://shopify/InventoryItem/1'},
                }],
                'pageInfo': {'hasNextPage': False, 'endCursor': None},
            },
        }}}

    def _drain(self, body):
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, request_body, token=None):
            return _FakeSendResponse(copy.deepcopy(body))

        self.env.flush_all()
        with patch.object(type(Client), '_send', fake_send):
            self.env['shopify.connector.job.dispatch'].run_drain(10)

    def _blocked_job(self, gid=TOUR_PRODUCT_GID, sku=TOUR_NUMERIC_SKU):
        """A genuinely blocked import, with a genuinely recorded decision."""
        self._product('Tour candidate A', sku)
        self._product('Tour candidate B', sku)
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid,
        })
        self._drain(self._body(gid, sku))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        return job, decision

    # ------------------------------------------------------------------
    # the product controls
    # ------------------------------------------------------------------

    def test_product_controls_tour_starts_a_real_scan(self):
        before = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_scan'),
        ])
        self.env.flush_all()
        self.start_tour(
            self._url(STORE_ACTION, self.store.id),
            'shopify_connector_b2_product_controls_tour',
            login='b2prod_operator',
        )
        after = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_scan'),
        ])
        self.assertEqual(
            len(after), before + 1,
            'pressing the control must enqueue exactly one catalog scan',
        )
        self.assertEqual(after.job_source, 'manual_sync')
        self.assertEqual(after.state, 'queued')

    def test_product_controls_are_absent_for_a_role_the_server_refuses(self):
        self.env.flush_all()
        self.start_tour(
            self._url(STORE_ACTION, self.store.id),
            'shopify_connector_b2_product_controls_denied_tour',
            login='b2prod_auditor',
        )
        self.assertFalse(self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_scan'),
        ]))

    # ------------------------------------------------------------------
    # the match decision, and the binding it produces
    # ------------------------------------------------------------------

    def test_match_decision_tour_records_the_choice_and_resumes(self):
        job, decision = self._blocked_job()
        self.env.flush_all()
        self.start_tour(
            self._url(JOB_ACTION, job.id),
            'shopify_connector_b2_product_match_decision_tour',
            login='b2prod_reviewer',
        )
        job.invalidate_recordset()
        decision.invalidate_recordset()
        # The DATABASE consequence, verified in Python rather than inferred
        # from what the screen said.
        self.assertEqual(decision.state, 'confirmed')
        self.assertEqual(decision.resolved_uid, self.reviewer)
        self.assertTrue(decision.resolved_at)
        self.assertIn(
            decision.selected_template_id,
            decision.candidate_template_ids,
            'the browser recorded a choice that was never a candidate',
        )
        # The EXACT record the tour named, not merely "one of the two". The
        # tour now types the name and asserts the field holds it, so anything
        # else here means the browser chose something the tour did not.
        self.assertEqual(
            decision.selected_template_id.name, 'Tour candidate A',
            'the browser recorded a different candidate from the one the '
            'tour selected by name',
        )
        self.assertEqual(decision.resumed_job_state, 'queued')
        self.assertEqual(
            job.state, 'queued',
            'confirming must resume the exact job that was stopped',
        )
        self.assertFalse(job.manual_review_subreason)

    def test_match_decision_control_is_absent_for_an_operator(self):
        """An Operator may START an import and may not decide a match."""
        job, decision = self._blocked_job(
            gid='gid://shopify/Product/7346299043935', sku='0123456789012',
        )
        self.env.flush_all()
        self.start_tour(
            self._url(JOB_ACTION, job.id),
            'shopify_connector_b2_product_match_decision_denied_tour',
            login='b2prod_operator',
        )
        decision.invalidate_recordset()
        job.invalidate_recordset()
        self.assertEqual(decision.state, 'pending')
        self.assertFalse(decision.resolved_uid)
        self.assertEqual(job.state, 'blocked_manual_review')

    def test_resolved_binding_tour_shows_a_human_made_match(self):
        job, decision = self._blocked_job(
            gid=TOUR_DONE_GID, sku='4006381333931',
        )
        chosen = decision.candidate_template_ids[0]
        self.env[
            'shopify.connector.product.match.decision.wizard'
        ].with_user(self.reviewer).with_context(
            default_decision_id=decision.id,
        ).create({'selected_template_id': chosen.id}).action_confirm()
        self._drain(self._body(
            TOUR_DONE_GID, '4006381333931',
        ))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        binding = self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', TOUR_DONE_GID),
        ])
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.match_key, 'manual')
        self.env.flush_all()
        # The binding's own form, by id. The Product Matching LIST action
        # carries `search_default_filter_needs_attention`, so a healthy
        # `active` binding is correctly absent from it -- opening the list and
        # asserting a row would be asserting that filter is broken.
        self.start_tour(
            self._url(BINDING_ACTION, binding.id),
            'shopify_connector_b2_resolved_binding_tour',
            login='b2prod_reviewer',
        )
        binding.invalidate_recordset()
        self.assertEqual(
            binding.product_template_id, chosen,
            'the binding must still point where the human said, after the '
            'browser looked at it',
        )

    # ------------------------------------------------------------------
    # the workspace's own accessibility contract
    # ------------------------------------------------------------------

    def test_decision_state_is_text_as_well_as_colour(self):
        """WCAG 1.4.1: colour is never the only carrier of a state.

        The Match Decisions list decorates rows by state, which is useful and
        is not information on its own. This asserts the state is ALSO rendered
        as a field -- i.e. as words a reader can see and a screen reader can
        announce -- rather than trusting the comment in the view that says so.
        """
        from lxml import etree
        view = self.env.ref(
            'shopify_connector_product.'
            'view_shopify_connector_product_match_decision_list'
        )
        arch = etree.fromstring(view.arch_db)
        list_node = arch if arch.tag == 'list' else arch.find('.//list')
        self.assertIsNotNone(list_node)
        decorations = [
            key for key in list_node.attrib if key.startswith('decoration-')
        ]
        self.assertTrue(
            decorations, 'the list carries no state decoration at all'
        )
        state_fields = arch.xpath("//field[@name='state']")
        self.assertTrue(
            state_fields,
            'the list decorates rows by state but never renders the state as '
            'text, so colour would be the only carrier (WCAG 1.4.1)',
        )
