"""Batch 2 correction (F1/F2/F3, F7, F10) — reproducers that run at ANY head.

WHY THIS FILE IS SEPARATE FROM `test_product_match_decision.py`. That file
imports the symbols the correction introduced (`opaque_identity`,
`match_value_digest`, `MATCH_DIGEST_LEN`), so at the pre-correction head it
would fail at IMPORT time -- which proves nothing about the defect. Every test
here drives PUBLIC production routes only and imports nothing the starting head
`ccad8bf432868650abb80bfb2103bd8d397be549` does not already have, so the same
file is a genuine before/after reproducer rather than a description of one side.

WHAT IT REPRODUCES. `safe_match_preview` is a DISPLAY scrubber whose phone
pattern is `(?<!\\w)\\+?\\d[\\d\\s().-]{6,}\\d(?!\\w)`: a leading digit, six or
more digit/separator characters, a trailing digit. At the starting head it was
applied to the Shopify Product GID, the ProductVariant GID, the remote
`updatedAt` and the exact SKU/barcode match values -- and every realistic
Shopify GID suffix, every numeric SKU and every UPC-A/EAN-13 barcode matches
that pattern. The pre-correction fixtures used `gid://shopify/Product/8201` and
`DUP-TPL`, two of the few shapes it does NOT rewrite, which is exactly why a
green suite could sit on top of a broken route.

The data below is what a real store sends. Nothing else about these tests is
unusual: the ambiguity is produced by the real importer, routed by the real
dispatcher, recorded by the real `_route_failure` seam, decided through the
real wizard, and resumed through the real `action_manual_retry`. Transport is
patched at `_send`, so no test here can reach Shopify even by accident.
"""

import copy
import uuid
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
STAMP = '2026-07-30T09:15:00Z'

# The shapes a real Shopify store issues, and a real merchant types.
REAL_PRODUCT_GID = 'gid://shopify/Product/7346299043911'
REAL_PRODUCT_GID_2 = 'gid://shopify/Product/9876543210987'
REAL_VARIANT_GID = 'gid://shopify/ProductVariant/45123456789012'
NUMERIC_SKU = '1234567890123'
HYPHENATED_NUMERIC_SKU = '012-345-6789'

PRODUCT_SCAN_CRON_XMLID = (
    'shopify_connector_product.ir_cron_shopify_connector_product_scan'
)


class _FakeSendResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code
        self.headers = {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install')
class TestProductMatchRealDataAtAnyHead(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Decision = cls.env['shopify.connector.product.match.decision']
        cls.Wizard = cls.env[
            'shopify.connector.product.match.decision.wizard'
        ]
        cls.TemplateBinding = cls.env[
            'shopify.connector.product.template.binding'
        ]
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({
            'name': 'Real data other co',
        })
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Real data store',
            'shop_domain': 'real-data-match.myshopify.com',
            'api_version': '2026-07',
            'company_id': cls.company.id,
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
        cls.reviewer = cls._role_user(
            'reviewer', 'group_shopify_connector_reviewer', cls.company,
        )
        cls.admin = cls._role_user(
            'admin', 'group_shopify_connector_admin', cls.company,
        )
        cls.operator = cls._role_user(
            'operator', 'group_shopify_connector_operator', cls.company,
        )
        cls.auditor = cls._role_user(
            'auditor', 'group_shopify_connector_auditor', cls.company,
        )
        cls.foreign_admin = cls._role_user(
            'foreign', 'group_shopify_connector_admin', cls.other_company,
        )

    @classmethod
    def _role_user(cls, label, xmlid, company):
        return cls.env['res.users'].create({
            'name': 'Real data %s' % label,
            'login': 'real_data_match_%s' % label,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % xmlid).id,
            ])],
        })

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    # -- fixtures ------------------------------------------------------

    def _make_product(self, name, sku):
        template = self.env['product.template'].create({'name': name})
        template.product_variant_id.write({'default_code': sku})
        return template

    def _body(self, gid, variant_gid, sku, updated_at=STAMP):
        return {'data': {'product': {
            'id': gid,
            'title': 'Real data ambiguous product',
            'status': 'ACTIVE',
            'updatedAt': updated_at,
            'descriptionHtml': '', 'vendor': '', 'productType': '',
            'tags': [], 'featuredImage': None, 'options': [],
            'variants': {
                'nodes': [{
                    'id': variant_gid, 'sku': sku, 'barcode': None,
                    'price': '19.99', 'compareAtPrice': None,
                    'selectedOptions': [], 'image': None,
                    'inventoryItem': {
                        'id': 'gid://shopify/InventoryItem/1',
                    },
                }],
                'pageInfo': {'hasNextPage': False, 'endCursor': None},
            },
        }}}

    def _job(self, gid):
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid,
        })
        self.env.flush_all()
        return job

    def _drain(self, body):
        Client = self.env['shopify.connector.api.client']
        sent = []

        def fake_send(client_self, store, request_body, token=None):
            sent.append(copy.deepcopy(request_body or {}))
            return _FakeSendResponse(copy.deepcopy(body))

        self.env.flush_all()
        with patch.object(type(Client), '_send', fake_send):
            self.Dispatch.run_drain(20)
        return sent

    def _blocked(self, gid, variant_gid, sku, updated_at=STAMP):
        first = self._make_product('Real A %s' % sku, sku)
        second = self._make_product('Real B %s' % sku, sku)
        job = self._job(gid)
        sent = self._drain(self._body(gid, variant_gid, sku, updated_at))
        job.invalidate_recordset()
        self.assertTrue(sent, 'the importer never issued a Shopify read')
        self.assertEqual(
            job.state, 'blocked_manual_review',
            'the ambiguity did not block the job, so nothing below is about '
            'the decision route',
        )
        decision = self.Decision.search([('job_id', '=', job.id)])
        self.assertEqual(len(decision), 1)
        return job, decision, first, second

    def _confirm(self, decision, chosen, user=None):
        wizard = self.Wizard.with_user(user or self.admin).with_context(
            default_decision_id=decision.id,
        ).create({})
        wizard.write({'selected_template_id': chosen.id})
        return wizard.action_confirm()

    # -- F1/F2/F3 ------------------------------------------------------

    def test_the_display_scrubber_rewrites_every_shape_used_here(self):
        """The measurement the rest of this file rests on.

        Read through the PUBLIC preview field of a real decision rather than
        by importing the scrubber, so this runs at any head.
        """
        _job, decision, _a, _b = self._blocked(
            REAL_PRODUCT_GID, REAL_VARIANT_GID, NUMERIC_SKU,
        )
        self.assertEqual(
            decision.sku_preview, '[redacted-phone]',
            'a 13-digit SKU is not being rewritten by the display scrubber, '
            'so this environment does not exhibit the defect these tests are '
            'about',
        )

    def test_a_confirmed_decision_on_real_data_is_actually_consumed(self):
        """THE defect, end to end.

        At the starting head the decision key was built from the SANITIZED
        identity while `_confirmed_for` builds it from the RAW payload, so the
        two could never be equal: confirming and resuming ran the identical
        search, found the identical two candidates, and stopped again. The
        merchant could press the button forever.
        """
        job, decision, first, _second = self._blocked(
            REAL_PRODUCT_GID, REAL_VARIANT_GID, NUMERIC_SKU,
        )
        eligible = decision.eligible_candidates()
        self.assertIn(
            first.id, eligible.ids,
            'the reviewer was offered nothing to choose: the stored match '
            'value cannot find the Odoo records the importer just found',
        )
        self._confirm(decision, first)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

        self._drain(self._body(REAL_PRODUCT_GID, REAL_VARIANT_GID,
                               NUMERIC_SKU))
        job.invalidate_recordset()
        decision.invalidate_recordset()
        self.assertEqual(
            job.state, 'succeeded',
            'the resumed import stopped again instead of consuming the '
            'decision a human had already made',
        )
        self.assertEqual(decision.state, 'consumed')
        binding = self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', REAL_PRODUCT_GID),
        ])
        self.assertEqual(len(binding), 1)
        self.assertEqual(binding.product_template_id, first)
        self.assertEqual(binding.match_key, 'manual')

    def test_the_stored_identity_is_the_identity_shopify_sent(self):
        _job, decision, _a, _b = self._blocked(
            REAL_PRODUCT_GID, REAL_VARIANT_GID, NUMERIC_SKU,
        )
        self.assertEqual(
            decision.shopify_product_gid, REAL_PRODUCT_GID,
            'the decision records a rewritten Shopify identity, so it cannot '
            'name the product it is about',
        )
        self.assertEqual(decision.remote_updated_at, STAMP)

    def test_two_real_products_never_share_or_repoint_one_decision(self):
        """Both GIDs end in a long digit run, so the display scrubber
        collapses them to the same string. With the same `updatedAt` they
        produced ONE key at the starting head -- so the second product's
        failure found the first product's pending decision and re-pointed it
        at the second product's job."""
        first_job, first_decision, first_a, _first_b = self._blocked(
            REAL_PRODUCT_GID, REAL_VARIANT_GID, NUMERIC_SKU,
        )
        second_job, second_decision, _second_a, _second_b = self._blocked(
            REAL_PRODUCT_GID_2, 'gid://shopify/ProductVariant/45123456789029',
            HYPHENATED_NUMERIC_SKU,
        )
        self.assertNotEqual(
            first_decision, second_decision,
            'two different Shopify products share one decision row',
        )
        self.assertEqual(first_decision.job_id, first_job)
        self.assertEqual(
            second_decision.job_id, second_job,
            'one product\'s decision was re-pointed at another product\'s job',
        )
        self.assertEqual(
            first_decision.remote_updated_at,
            second_decision.remote_updated_at,
        )

        self._confirm(first_decision, first_a)
        first_job.invalidate_recordset()
        second_job.invalidate_recordset()
        second_decision.invalidate_recordset()
        self.assertEqual(first_job.state, 'queued')
        self.assertEqual(
            second_job.state, 'blocked_manual_review',
            'confirming one decision resumed an unrelated product\'s import',
        )
        self.assertEqual(second_decision.state, 'pending')

    def test_recording_one_ambiguity_does_not_supersede_an_unrelated_one(self):
        _first_job, neighbour, _a, _b = self._blocked(
            REAL_PRODUCT_GID_2, 'gid://shopify/ProductVariant/45123456789036',
            HYPHENATED_NUMERIC_SKU,
        )
        self.assertEqual(neighbour.state, 'pending')
        self._blocked(REAL_PRODUCT_GID, REAL_VARIANT_GID, NUMERIC_SKU)
        neighbour.invalidate_recordset()
        self.assertEqual(
            neighbour.state, 'pending',
            'an unrelated product superseded this merchant decision',
        )

    # -- F10 -----------------------------------------------------------

    def test_a_foreign_decision_is_refused_before_its_row_is_locked(self):
        """`SELECT ... FOR UPDATE` by primary key answers to no ACL and no
        record rule. With the lock taken first, a caller naming another
        company's decision id acquires a genuine write lock on that row --
        blocking its legitimate reviewer for the life of the transaction --
        and only afterwards learns they were not allowed to be there.

        Measured on the statements actually issued -- the cursor is wrapped
        for the duration of the call -- so this asserts what the code EXECUTED
        rather than what its source says.
        """
        _job, decision, _first, _second = self._blocked(
            REAL_PRODUCT_GID, REAL_VARIANT_GID, NUMERIC_SKU,
        )
        self.env.flush_all()

        recorded = []
        cursor_type = type(self.env.cr)
        original = cursor_type.execute

        def spy(cr_self, query, params=None, log_exceptions=True):
            recorded.append(
                query if isinstance(query, str)
                else str(getattr(query, 'code', query))
            )
            return original(cr_self, query, params, log_exceptions)

        wizard = self.Wizard.with_user(self.foreign_admin).with_context(
            default_decision_id=False,
        ).sudo().create({'decision_id': decision.id})
        with patch.object(cursor_type, 'execute', spy):
            with self.assertRaises(Exception) as refusal:
                wizard.with_user(self.foreign_admin).action_confirm()
        self.assertIsInstance(refusal.exception, (AccessError, UserError))
        self.assertTrue(
            recorded,
            'no statement was recorded, so the instrument is not measuring '
            'the call it claims to measure',
        )
        self.assertFalse(
            [
                text for text in recorded
                if 'FOR UPDATE' in text.upper()
                and 'shopify_connector_product_match_decision' in text
            ],
            'the refused caller took a row lock on a decision it was never '
            'allowed to reach, blocking its legitimate reviewer for the life '
            'of the transaction, and only then learned it was refused',
        )

    # -- F7 ------------------------------------------------------------

    def test_scheduled_product_state_is_false_while_the_cron_is_disabled(self):
        """The store flag is an INTENTION; the cron is what actually runs."""
        cron = self.env.ref(PRODUCT_SCAN_CRON_XMLID)
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.store.invalidate_recordset()
        self.assertTrue(cron.active)
        self.assertTrue(self.store.product_sync_scheduled)

        cron.sudo().write({'active': False})
        self.store.invalidate_recordset()
        self.assertFalse(
            self.store.product_sync_scheduled,
            'the store claims scheduled product import while the cron that '
            'would perform it is disabled, so the screen tells a merchant '
            'their catalog is being kept current when nothing is enqueued',
        )
        self.assertTrue(self.store.product_sync_domain_enabled)

        cron.sudo().write({'active': True})
        self.store.invalidate_recordset()
        self.assertTrue(self.store.product_sync_scheduled)

    def test_manual_product_import_survives_a_disabled_cron(self):
        self.env.ref(PRODUCT_SCAN_CRON_XMLID).sudo().write({'active': False})
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.store.invalidate_recordset()
        job = self.store.with_user(self.operator).action_sync_products_now()
        self.assertEqual(job.job_type, 'product_import_scan')
        with self.assertRaises(AccessError):
            self.store.with_user(self.auditor).action_sync_products_now()

    # -- F11 -----------------------------------------------------------

    def test_product_scan_is_durably_resumable_not_catalog_capped(self):
        import inspect

        service = self.env['shopify.connector.product.scan']
        source = inspect.getsource(type(service).run_scan)
        for required in (
            'product_scan_window_end_at',
            'product_scan_cursor',
            'product_scan_generation',
            'PRODUCT_SCAN_SLICE_PAGES',
            '_enqueue_product_scan',
        ):
            self.assertIn(required, source)
        self.assertIn('if not complete:', source)
