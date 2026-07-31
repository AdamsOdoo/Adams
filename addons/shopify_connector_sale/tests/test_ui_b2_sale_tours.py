"""Batch 2 §10 -- driven-browser evidence for the order and tax surfaces.

Two surfaces, each reached the way an operator reaches it:

  * the order import controls on the store form,
  * the tax decision dialog, opened from the order that is stopped.

THE TAX BLOCK IS PRODUCED BY PRODUCTION CODE. The importer meets a `TaxLine`
with no mapping, raises its own structured evidence, and the dispatcher's own
`_route_failure` puts the job where it really goes. A hand-written job-log row
would let this pass against a taxonomy the product no longer uses.
"""

import json
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .test_order_import_mapping import OrderImportCase

STORE_ACTION = 'shopify_connector_core.action_shopify_connector_store'
JOB_ACTION = 'shopify_connector_core.action_shopify_connector_error_center'


@tagged('post_install', '-at_install', 'shopify_connector_b2_tours')
class TestUiB2SaleTours(OrderImportCase, HttpCase):
    """`OrderImportCase` brings the network-free order fixture substrate;
    `HttpCase` brings the browser. Both derive from `TransactionCase`, so the
    whole fixture rolls back at teardown and leaves no residue."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.settings.write({'sale_domain_enabled': True})
        cls.b2_operator = cls._b2_user(
            'b2sale_operator', 'group_shopify_connector_operator',
        )
        cls.b2_admin = cls._b2_user(
            'b2sale_admin', 'group_shopify_connector_admin',
        )

    @classmethod
    def _b2_user(cls, login, group):
        return cls.env['res.users'].create({
            'name': login,
            'login': login,
            'password': login,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            # EXACTLY the role under test; see the note in the product tour
            # fixture. `group_shopify_connector_user` implies Operator AND
            # Reviewer, so adding it would silently widen every role here.
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % group).id,
            ])],
        })

    def _url(self, action_xmlid, res_id=None):
        url = '/odoo/action-%s' % action_xmlid
        return '%s/%d' % (url, res_id) if res_id else url

    def _tax(self):
        company = self.env.company
        country = (
            company.account_fiscal_country_id
            or company.country_id
            or self.env.ref('base.us')
        )
        group = self.env['account.tax.group'].sudo().create({
            'name': 'B2 Tour Tax Group',
            'company_id': company.id,
            'country_id': country.id,
        })
        return self.env['account.tax'].sudo().create({
            'name': 'B2 Tour VAT 5',
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': group.id,
            'price_include_override': 'tax_excluded',
            'include_base_amount': False,
        })

    def _evidence(self):
        return {
            'title': 'B2 Tour VAT',
            'source': 'Shopify',
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': None,
            'priceSet': {
                'shopMoney': {'amount': '5.00'},
                'presentmentMoney': {'amount': '5.00'},
            },
        }

    def _order(self):
        return self.env['sale.order'].create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
        })

    def _tax_blocked_job(self):
        """A genuinely tax-blocked job, routed by the real dispatcher."""
        job = self._job(target='gid://shopify/Order/B2TOUR')
        with self.assertRaises(JobHandlerError) as blocked:
            self.Importer._resolve_taxes(
                self._order(), self.store, [self._evidence()], False,
                self.settings,
            )
        exc = blocked.exception
        self.env['shopify.connector.job.dispatch']._route_failure(
            job, exc.error_class, exc.reason, exc.technical_detail,
        )
        job.invalidate_recordset()
        self.assertTrue(job.tax_decision_pending)
        return job, json.loads(exc.technical_detail)

    # ------------------------------------------------------------------
    # the order controls
    # ------------------------------------------------------------------

    def test_order_controls_tour_starts_a_real_scan(self):
        before = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ])
        self.env.flush_all()
        self.start_tour(
            self._url(STORE_ACTION, self.store.id),
            'shopify_connector_b2_order_controls_tour',
            login='b2sale_operator',
        )
        after = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ])
        self.assertEqual(
            len(after), before + 1,
            'pressing the control must enqueue exactly one order scan',
        )
        self.assertEqual(after.job_source, 'manual_sync')
        self.assertEqual(after.state, 'queued')

    # ------------------------------------------------------------------
    # the tax decision
    # ------------------------------------------------------------------

    def test_tax_decision_tour_creates_the_mapping_and_resumes(self):
        tax = self._tax()
        job, detail = self._tax_blocked_job()
        scans_before = self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ])
        self.env.flush_all()
        self.start_tour(
            self._url(JOB_ACTION, job.id),
            'shopify_connector_b2_tax_decision_tour',
            login='b2sale_admin',
        )
        mapping = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping.account_tax_id, tax)
        self.assertEqual(
            mapping.shopify_tax_evidence_key, detail['fingerprint'],
            'the mapping must carry the fingerprint the importer raised, not '
            'one recovered from the sentence on screen',
        )
        job.invalidate_recordset()
        self.assertEqual(
            job.state, 'queued',
            'confirming must resume the exact order that was stopped',
        )
        self.assertEqual(
            self.Job.search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'order_import_scan'),
            ]),
            scans_before,
            'mapping a tax must not start a fresh order scan',
        )
