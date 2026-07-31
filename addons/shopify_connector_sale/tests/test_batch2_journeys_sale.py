"""Batch 2 §9 -- consolidated vertical journey D-P0: orders and tax.

Configured through Store Settings, started through the production order
control, enumerated by the real scan, admitted through the real enqueue,
executed by the real dispatcher and importer, stopped by a tax fingerprint
the connector genuinely does not know, mapped through the real dialog, and
resumed as the exact same job.

THE TAX BLOCK IS PRODUCED BY DATA, NOT BY AN INJECTED EXCEPTION. The order
payload carries a `TaxLine` for which no `shopify.connector.tax.mapping`
exists, and everything after that is whatever the production code does about
it. A journey that raised the error itself would prove the recovery path works
against a failure the product no longer produces.
"""

import copy
import json
import uuid
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
)

from .test_order_import_mapping import OrderImportCase

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
ORDER_GID = 'gid://shopify/Order/JOURNEY-D'
ORDER_STAMP = '2026-07-17T11:00:00Z'


class _FakeSendResponse:

    def __init__(self, body):
        self._body = body
        self.status_code = 200
        self.headers = {API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install')
class TestBatch2SaleJourneys(OrderImportCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A credential is what makes the real admission gate admit a business
        # job at all. Seeded while the store is already `connected` in the
        # base fixture; the job below states the store's own generation.
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN,
        )
        # Seeding a credential on an already-connected store moves it out of
        # `connected` through the ordinary lifecycle. The journeys below are
        # about orders, not about reconnection, so the store is returned to
        # the state a merchant would have finished onboarding in.
        cls.store.write({'state': 'connected'})
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Mapping = cls.env['shopify.connector.tax.mapping']
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------

    def _tax(self, name='Journey VAT', amount=5.0):
        company = self.env.company
        country = (
            company.account_fiscal_country_id
            or company.country_id
            or self.env.ref('base.us')
        )
        group = self.env['account.tax.group'].sudo().create({
            'name': '%s Group' % name,
            'company_id': company.id,
            'country_id': country.id,
        })
        return self.env['account.tax'].sudo().create({
            'name': name,
            'amount': amount,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': group.id,
            'price_include_override': 'tax_excluded',
            'include_base_amount': False,
        })

    def _tax_line(self):
        return {
            'title': 'Journey VAT',
            'source': 'Shopify',
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': None,
            'priceSet': {
                'shopMoney': {'amount': '5.00'},
                'presentmentMoney': {'amount': '5.00'},
            },
        }

    def _graphql_order(self, gid=ORDER_GID, taxed=True):
        """The normalized fixture, re-expressed in the RAW wire shape."""
        payload = self._payload(gid=gid)
        payload['name'] = '#JOURNEY-D'
        payload['legacyResourceId'] = '990001'
        payload['updatedAt'] = ORDER_STAMP
        if taxed:
            zero = self._money('0.00')
            taxed_total = self._money('105.00')
            payload['taxLines'] = [self._tax_line()]
            payload['totalTaxSet'] = self._money('5.00')
            payload['currentTotalTaxSet'] = self._money('5.00')
            payload['totalPriceSet'] = taxed_total
            payload['currentTotalPriceSet'] = taxed_total
            payload['line_items'][0]['taxable'] = True
            payload['line_items'][0]['taxLines'] = [self._tax_line()]
            del zero
        line_items = payload.pop('line_items')
        shipping_lines = payload.pop('shipping_lines')
        discounts = payload.pop('discount_applications')
        payload['lineItems'] = {
            'edges': [
                {'cursor': 'li-%d' % index, 'node': node}
                for index, node in enumerate(line_items)
            ],
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        }
        payload['shippingLines'] = {
            'edges': [
                {'cursor': 'sl-%d' % index, 'node': node}
                for index, node in enumerate(shipping_lines)
            ],
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        }
        payload['discountApplications'] = {
            'edges': [
                {'cursor': 'da-%d' % index, 'node': node}
                for index, node in enumerate(discounts)
            ],
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        }
        return {'data': {'order': payload}}

    def _scan_page(self, gids, updated_at=ORDER_STAMP):
        return {'data': {'orders': {
            'edges': [
                {'cursor': 'c-%d' % index, 'node': {
                    'id': gid,
                    'updatedAt': updated_at,
                    'createdAt': '2026-07-17T09:00:00Z',
                    'edited': False,
                    'test': False,
                    'cancelledAt': None,
                    'displayFinancialStatus': 'PAID',
                }}
                for index, gid in enumerate(gids)
            ],
            'pageInfo': {'hasNextPage': False, 'endCursor': None},
        }}}

    def _patch_transport(self, scan_pages=(), orders=None):
        pages = list(scan_pages)
        orders = orders or {}
        sent = []
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, body, token=None):
            body = body or {}
            query = body.get('query') or ''
            sent.append(copy.deepcopy(body))
            if 'orders(' in query:
                if not pages:
                    raise AssertionError('an unexpected extra scan page')
                return _FakeSendResponse(copy.deepcopy(pages.pop(0)))
            if 'order(' in query:
                gid = (body.get('variables') or {}).get('id')
                if gid not in orders:
                    raise AssertionError('unstubbed order %r' % gid)
                return _FakeSendResponse(copy.deepcopy(orders[gid]))
            raise AssertionError('unexpected query: %s' % query[:80])

        return patch.object(type(Client), '_send', fake_send), sent

    def _drain(self, scan_pages=(), orders=None, limit=30):
        patcher, sent = self._patch_transport(scan_pages, orders)
        self.env.flush_all()
        with patcher:
            self.Dispatch.run_drain(limit)
        return sent

    def _scans(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ])

    def _imports(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_sync'),
        ])

    # ==================================================================
    # JOURNEY D-P0
    # ==================================================================

    def test_journey_d_orders_and_tax_end_to_end(self):
        store, settings = self.store, self.settings
        admin, operator = self.roles['admin'], self.roles['operator']

        # --- 1. Configure the sale prerequisites through Store Settings --
        settings.with_user(admin).write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
            'order_confirmation_policy': 'quotations_only',
        })
        self.assertTrue(settings.order_scheduled_sync_enabled)
        self.assertEqual(settings.order_company_id, self.env.company)

        # --- 2. Start manual order discovery through the real control ----
        scan = store.with_user(operator).action_sync_orders_now()
        self.assertEqual(scan.job_type, 'order_import_scan')
        self.assertEqual(scan.state, 'queued')

        # --- 3. Traverse scan -> enqueue -> dispatcher -> importer -------
        sent = self._drain(
            scan_pages=[self._scan_page([ORDER_GID])],
            orders={ORDER_GID: self._graphql_order()},
        )
        self.assertTrue(sent, 'no work was admitted')
        scan.invalidate_recordset()
        self.assertEqual(scan.state, 'succeeded')
        imports = self._imports()
        self.assertEqual(len(imports), 1)

        # --- 4. It stopped on an unknown tax fingerprint -----------------
        job = imports
        self.assertEqual(
            job.state, 'failed_retryable',
            'an unknown tax fingerprint is a MANUAL_FIX_THEN_RETRY class, so '
            'the dispatcher routes it here and not to blocked_manual_review',
        )
        self.assertEqual(job.error_class, 'odoo_validation_configuration')
        self.assertTrue(job.tax_decision_pending)
        evidence = job._tax_decision_evidence()
        self.assertTrue(evidence)
        self.assertEqual(evidence['rate_percentage'], '5')
        self.assertFalse(evidence['included'])
        # No order was created from a payload the connector could not price.
        self.assertFalse(self.Binding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', ORDER_GID),
        ]))

        # --- 5. Map it through an explicit same-company choice -----------
        tax = self._tax()
        action = job.with_user(admin).action_open_tax_mapping_decision()
        wizard = self.env[
            'shopify.connector.tax.decision.wizard'
        ].with_user(admin).with_context(action['context']).create({
            'account_tax_id': tax.id,
        })
        self.assertIn(tax, wizard.candidate_tax_ids)
        self.assertEqual(
            wizard.shopify_tax_evidence_key, evidence['fingerprint'],
        )
        wizard.action_confirm()
        mapping = self.Mapping.search([('store_id', '=', store.id)])
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping.account_tax_id, tax)
        self.assertEqual(mapping.company_id, store.company_id)

        # --- 6. The exact order job resumed, not a fresh scan ------------
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')
        self.assertEqual(
            len(self._scans()), 1,
            'mapping a tax must not start a second order scan',
        )

        # --- 7. It completes, and the result is visible ------------------
        self._drain(orders={ORDER_GID: self._graphql_order()})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        binding = self.Binding.search([
            ('store_id', '=', store.id), ('shopify_gid', '=', ORDER_GID),
        ])
        self.assertEqual(len(binding), 1)
        self.assertTrue(binding.sale_order_id)
        self.assertEqual(binding.sale_order_id.company_id, self.env.company)
        self.assertIn(tax, binding.sale_order_id.order_line.tax_ids)

        # --- 8. Schedule state and checkpoint, as the store reports them -
        settings.invalidate_recordset()
        self.assertTrue(settings.sale_order_last_import_checkpoint_at)
        store.invalidate_recordset()
        self.assertTrue(store.order_sync_scheduled)

    def test_journey_d_settings_constraints_are_still_the_authority(self):
        """Journey I's sale-side half: the canonical form saves through the
        ordinary write path, so every existing constraint still refuses.

        `_check_order_company_matches_store` (SEC-3 / #197.11) is the one
        chosen here -- a same-record, cross-field agreement rule that no ACL
        and no record rule would catch, so it can only hold because the write
        really went through `models.Model.write`.
        """
        settings = self.settings
        settings.with_user(self.roles['admin']).write({
            'sale_domain_enabled': True,
        })
        before = settings.order_company_id
        self.assertEqual(before, self.store.company_id)
        other_company = self.env['res.company'].sudo().create({
            'name': 'Journey D Foreign Co',
        })
        with self.assertRaises(ValidationError):
            settings.with_user(self.roles['admin']).write({
                'order_company_id': other_company.id,
            })
        settings.invalidate_recordset()
        self.assertEqual(settings.order_company_id, before)
        self.assertTrue(
            settings.sale_domain_enabled,
            'the refusal left something half-saved beside it',
        )

    def test_journey_d_an_operator_cannot_map_a_tax(self):
        self.settings.sudo().write({'sale_domain_enabled': True})
        self.store.with_user(self.roles['operator']).action_sync_orders_now()
        self._drain(
            scan_pages=[self._scan_page([ORDER_GID])],
            orders={ORDER_GID: self._graphql_order()},
        )
        job = self._imports()
        self.assertTrue(job.tax_decision_pending)
        for label in ('operator', 'reviewer', 'auditor'):
            with self.assertRaises(AccessError, msg=label):
                job.with_user(
                    self.roles[label]
                ).action_open_tax_mapping_decision()
        self.assertFalse(self.Mapping.search([]))

    def test_journey_d_the_whole_journey_issues_no_shopify_mutation(self):
        self.settings.sudo().write({'sale_domain_enabled': True})
        self.store.with_user(self.roles['operator']).action_sync_orders_now()
        sent = self._drain(
            scan_pages=[self._scan_page([ORDER_GID])],
            orders={ORDER_GID: self._graphql_order()},
        )
        self.assertTrue(sent)
        for request in sent:
            query = (request.get('query') or '').lower()
            self.assertNotIn('mutation', query)
            self.assertTrue(query.strip().startswith('query'))
        tax = self._tax()
        job = self._imports()
        wizard = self.env[
            'shopify.connector.tax.decision.wizard'
        ].with_user(self.roles['admin']).with_context(
            default_job_id=job.id,
        ).create({'account_tax_id': tax.id})
        client = self.env['shopify.connector.api.client']

        def refuse(*args, **kwargs):
            raise AssertionError('the decision route contacted Shopify')

        with patch.object(type(client), '_send', refuse):
            wizard.action_confirm()
        self.assertEqual(self.Mapping.search_count([]), 1)

    def test_journey_d_a_second_unmapped_tax_stops_again_rather_than_guessing(
        self,
    ):
        """A mapping is for one fingerprint, and only that one."""
        self.settings.sudo().write({'sale_domain_enabled': True})
        tax = self._tax()
        self.store.with_user(self.roles['operator']).action_sync_orders_now()
        self._drain(
            scan_pages=[self._scan_page([ORDER_GID])],
            orders={ORDER_GID: self._graphql_order()},
        )
        job = self._imports()
        wizard = self.env[
            'shopify.connector.tax.decision.wizard'
        ].with_user(self.roles['admin']).with_context(
            default_job_id=job.id,
        ).create({'account_tax_id': tax.id})
        wizard.action_confirm()

        # A DIFFERENT tax line: same store, different fingerprint.
        second_gid = 'gid://shopify/Order/JOURNEY-D2'
        body = self._graphql_order(gid=second_gid)
        other_line = dict(self._tax_line())
        other_line['title'] = 'Journey Other VAT'
        body['data']['order']['taxLines'] = [other_line]
        body['data']['order']['lineItems']['edges'][0]['node']['taxLines'] = [
            other_line,
        ]
        self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': second_gid,
            'expected_connection_generation': (
                self.store.connection_generation
            ),
        })
        self._drain(orders={second_gid: body})
        second = self.Job.search([
            ('store_id', '=', self.store.id),
            ('shopify_target_gid', '=', second_gid),
        ])
        self.assertEqual(second.state, 'failed_retryable')
        self.assertTrue(second.tax_decision_pending)
        self.assertNotEqual(
            json.loads(json.dumps(second._tax_decision_evidence()))[
                'fingerprint'
            ],
            self.Mapping.search([]).shopify_tax_evidence_key,
        )
