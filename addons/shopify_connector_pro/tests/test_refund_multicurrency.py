# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""AUD-019 — refund credit notes must carry the order/invoice currency.

Fail-before evidence for FINALIZE.md item 1: a refund on a EUR order
(company currency USD) must produce a EUR credit note that reconciles
against the EUR invoice. Before the fix, `_create_refund_credit_note`
passes no currency_id, so the credit note lands in company currency
with EUR numerals.
"""
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin
from .common import mute_case_loggers


class TestRefundCreditNoteMultiCurrency(ShopifyAccountingMixin, TransactionCase):

    def setUp(self):
        super().setUp()
        mute_case_loggers(self,
                          'odoo.addons.shopify_connector_pro.sync.refund_sync')
        # Self-provision EUR so the test runs on every strict profile
        # (EUR ships inactive on fresh DBs).
        self.eur = self.env['res.currency'].with_context(
            active_test=False,
        ).search([('name', '=', 'EUR')], limit=1)
        if not self.eur.active:
            self.eur.active = True
        if not self.env['res.currency.rate'].search([
            ('currency_id', '=', self.eur.id),
            ('company_id', '=', self.env.company.id),
        ]):
            self.env['res.currency.rate'].create({
                'currency_id': self.eur.id,
                'rate': 0.92,
                'name': '2026-01-01',
                'company_id': self.env.company.id,
            })

        self.backend = self.env['shopify.backend'].create({
            'name': 'MC Refund Store',
            'shop_url': 'mc-refund-test.myshopify.com',
            'access_token': 'shpat_mc_refund_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.partner = self._create_accounting_partner('EUR Buyer')
        self.product = self.env['product.product'].create({
            'name': 'EUR Widget',
            'list_price': 100.0,
        })
        self._set_product_income_account(self.product)

        eur_pricelist = self.env['product.pricelist'].create({
            'name': 'EUR Test Pricelist',
            'currency_id': self.eur.id,
            'company_id': self.env.company.id,
        })

        # EUR order: 2 × 100.00 EUR
        self.order = self.env['sale.order'].with_context(
            shopify_no_auto_export=True,
        ).create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': eur_pricelist.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        self.assertEqual(
            self.order.currency_id, self.eur,
            "Test precondition: sale order must be in EUR",
        )
        self.order.with_context(shopify_no_auto_export=True).action_confirm()
        self.invoice = self.order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()
        self.invoice.with_context(shopify_no_auto_export=True).action_post()
        self.assertEqual(
            self.invoice.currency_id, self.eur,
            "Test precondition: invoice must be in EUR",
        )

        self.order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Order/77001',
            'odoo_id': self.order.id,
            'shopify_order_name': '#MC-1001',
            'shopify_financial_status': 'partially_refunded',
            'sync_status': 'synced',
        })

        from ..sync.refund_sync import RefundImporter
        self.importer = RefundImporter.__new__(RefundImporter)
        self.importer.env = self.env
        self.importer.backend = self.backend
        self.importer.client = MagicMock()

    def _make_refund_data(self, refund_id, amount):
        return {
            'id': f'gid://shopify/Refund/{refund_id}',
            'totalRefundedSet': {
                'shopMoney': {
                    'amount': str(amount),
                    'currencyCode': 'EUR',
                },
            },
            'note': 'EUR partial refund',
            'refundLineItems': {'edges': []},
        }

    def test_credit_note_currency_from_order_when_no_invoice(self):
        """No posted invoice: the credit note takes the ORDER currency.

        Covers the fallback branch of the AUD-019 currency source
        (order.currency_id) with the same assertions as the
        posted-invoice branch.
        """
        # Remove the posted invoice so the fallback branch is exercised
        self.invoice.with_context(shopify_no_auto_export=True).button_cancel()
        self.assertFalse(self.order.invoice_ids.filtered(
            lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
        ))
        refund_data = self._make_refund_data(77002, 50.0)
        binding = self.importer._import_one_refund(
            refund_data, self.order_binding,
        )
        self.assertTrue(
            binding.odoo_id,
            "Credit note must be created and linked on the refund binding",
        )
        cn = binding.odoo_id
        self.assertEqual(cn.state, 'posted')
        self.assertEqual(
            cn.currency_id, self.eur,
            "AUD-019 fallback: with no posted invoice, the credit note "
            "must carry the ORDER currency (EUR), not the company currency",
        )
        self.assertAlmostEqual(
            cn.amount_total, 50.0, places=2,
            msg="Credit note total must equal the refunded EUR amount",
        )

    def test_currency_mismatch_degrades_visibly_no_credit_note(self):
        """Refund currency ≠ invoice currency: no credit note, error-state
        binding, actionable activity, nothing financial half-written."""
        refund_data = self._make_refund_data(77003, 100.0)
        refund_data['totalRefundedSet']['shopMoney']['currencyCode'] = 'USD'

        moves_before = self.env['account.move'].search_count([
            ('move_type', '=', 'out_refund'),
            ('company_id', '=', self.env.company.id),
        ])
        binding = self.importer._import_one_refund(
            refund_data, self.order_binding,
        )

        # Record lands in the right state, retryable
        self.assertFalse(binding.odoo_id, "No credit note may be linked")
        self.assertEqual(binding.sync_status, 'error')
        self.assertIn('activity', binding.sync_error or '',
                      "Binding error must point at the scheduled activity")

        # Nothing financial half-written
        moves_after = self.env['account.move'].search_count([
            ('move_type', '=', 'out_refund'),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertEqual(moves_before, moves_after,
                         "No credit note may be created on mismatch")

        # Merchant-visible message is actionable on its own:
        # names both currencies, states non-creation, states retryability
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
            ('summary', '=', 'Shopify refund credit note failed'),
        ], limit=1)
        self.assertTrue(activity, "A warning activity must be scheduled")
        note = activity.note or ''
        self.assertIn('USD', note, "Message must name the refund currency")
        self.assertIn('EUR', note,
                      "Message must name the invoice/order currency")
        self.assertIn('NOT created', note,
                      "Message must state the credit note was not created")
        self.assertIn('Retry Sync', note,
                      "Message must state how to retry after review")

    def test_credit_note_currency_matches_invoice_currency(self):
        """A EUR refund on a EUR order must post a EUR credit note.

        Production path: RefundImporter._import_one_refund →
        _create_refund_credit_note (no mocks of connector logic).
        """
        refund_data = self._make_refund_data(77001, 100.0)
        binding = self.importer._import_one_refund(
            refund_data, self.order_binding,
        )
        self.assertTrue(
            binding.odoo_id,
            "Credit note must be created and linked on the refund binding",
        )
        cn = binding.odoo_id
        self.assertEqual(cn.state, 'posted')
        self.assertEqual(
            cn.currency_id, self.eur,
            "AUD-019: credit note must be in the invoice currency (EUR), "
            "not the company currency — EUR amounts booked under %s "
            "misstate the books" % cn.currency_id.name,
        )
        self.assertAlmostEqual(
            cn.amount_total, 100.0, places=2,
            msg="Credit note total must equal the refunded EUR amount",
        )
