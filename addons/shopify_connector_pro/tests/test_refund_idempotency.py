# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Item 5: refund idempotency (AUD-021) + cumulative over-refund guard
(AUD-022). All tests run through the production import path
(`import_refunds_for_order` / `_import_one_refund`)."""
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin
from .common import mute_case_loggers


class RefundGuardFixture(ShopifyAccountingMixin):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Refund Guard Store',
            'shop_url': 'refund-guard.myshopify.com',
            'access_token': 'shpat_refund_guard',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.partner = self._create_accounting_partner('Guard Refund Buyer')
        self.product = self.env['product.product'].create({
            'name': 'Guard Refund Widget',
            'list_price': 100.0,
        })
        self._set_product_income_account(self.product)
        # Confirmed order 2 × $100 = $200, invoice posted
        self.order = self.env['sale.order'].with_context(
            shopify_no_auto_export=True,
        ).create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        self.order.with_context(shopify_no_auto_export=True).action_confirm()
        self.invoice = self.order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()
        self.invoice.with_context(shopify_no_auto_export=True).action_post()
        self.order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Order/5001',
            'odoo_id': self.order.id,
            'shopify_order_name': '#RG-1001',
            'shopify_financial_status': 'paid',
            'sync_status': 'synced',
        })
        from ..sync.refund_sync import RefundImporter
        self.importer = RefundImporter.__new__(RefundImporter)
        self.importer.env = self.env
        self.importer.backend = self.backend
        self.importer.client = MagicMock()

    def _refund(self, refund_id, amount):
        return {
            'id': 'gid://shopify/Refund/%s' % refund_id,
            'totalRefundedSet': {
                'shopMoney': {
                    'amount': str(amount), 'currencyCode': 'USD',
                },
            },
            'note': 'guard test refund',
            'refundLineItems': {'edges': []},
        }

    def _serve(self, *refunds):
        self.importer.client.execute.return_value = {
            'data': {'order': {'refunds': list(refunds)}},
        }

    def _posted_credit_notes(self):
        return self.env['account.move'].search([
            ('move_type', '=', 'out_refund'),
            ('partner_id', '=', self.partner.id),
            ('state', '=', 'posted'),
        ])


class TestRefundIdempotency(RefundGuardFixture, TransactionCase):
    """AUD-021: a failure between credit-note posting and binding
    creation must not leave an orphaned credit note that duplicates on
    the next sync."""

    def setUp(self):
        super().setUp()
        mute_case_loggers(self,
                          'odoo.addons.shopify_connector_pro.sync.refund_sync')

    def test_binding_failure_does_not_orphan_credit_note(self):
        self._serve(self._refund(6001, 50.0))
        Binding = self.env['shopify.refund.binding']
        with patch.object(type(Binding), 'create',
                          side_effect=Exception('simulated binding crash')):
            _s, errors, _sk = self.importer.import_refunds_for_order(
                self.order_binding)
        self.assertEqual(errors, 1, "The failure must be counted")
        self.assertFalse(
            self._posted_credit_notes(),
            "AUD-021: the posted credit note must not survive a binding-"
            "creation failure (orphan = duplicate on retry)",
        )
        # The next sync must import the refund exactly once.
        s, errors, _sk = self.importer.import_refunds_for_order(
            self.order_binding)
        self.assertEqual((s, errors), (1, 0))
        self.assertEqual(
            len(self._posted_credit_notes()), 1,
            "Exactly ONE credit note after the retry",
        )

    def test_refund_gid_recovery_guard(self):
        """Even if the refund binding disappears (manual cleanup, partial
        restore), the GID stamped on the credit note must prevent a
        second posting."""
        self._serve(self._refund(6002, 80.0))
        s, errors, _sk = self.importer.import_refunds_for_order(
            self.order_binding)
        self.assertEqual((s, errors), (1, 0))
        cns = self._posted_credit_notes()
        self.assertEqual(len(cns), 1)
        self.assertEqual(
            cns.shopify_refund_gid, 'gid://shopify/Refund/6002',
            "The credit note must carry the Shopify refund GID",
        )
        # Simulate binding loss, then re-import the same refund.
        self.env['shopify.refund.binding'].search([
            ('order_binding_id', '=', self.order_binding.id),
        ]).unlink()
        s, errors, _sk = self.importer.import_refunds_for_order(
            self.order_binding)
        self.assertEqual(
            len(self._posted_credit_notes()), 1,
            "AUD-021: the GID guard must reuse the existing credit note, "
            "never post a second one",
        )


class TestOverRefundGuard(RefundGuardFixture, TransactionCase):
    """AUD-022: cumulative refunds beyond the posted invoice total must
    not post silently."""

    def setUp(self):
        super().setUp()
        mute_case_loggers(self,
                          'odoo.addons.shopify_connector_pro.sync.refund_sync')

    def test_cumulative_over_refund_blocked_visibly(self):
        self._serve(self._refund(7001, 150.0))
        s, errors, _sk = self.importer.import_refunds_for_order(
            self.order_binding)
        self.assertEqual((s, errors), (1, 0))
        self.assertEqual(len(self._posted_credit_notes()), 1)

        # Second refund pushes the total to 250 > 200 invoiced.
        self._serve(self._refund(7001, 150.0), self._refund(7002, 100.0))
        self.importer.import_refunds_for_order(self.order_binding)
        self.assertEqual(
            len(self._posted_credit_notes()), 1,
            "AUD-022: the over-refund credit note must NOT post "
            "(cumulative 250.00 vs 200.00 invoiced)",
        )
        over_binding = self.env['shopify.refund.binding'].search([
            ('shopify_id', '=', 'gid://shopify/Refund/7002'),
        ])
        self.assertTrue(over_binding, "Binding must exist for retry")
        self.assertEqual(
            over_binding.sync_status, 'error',
            "The blocked refund must land in error state, not synced",
        )
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ]).filtered(
            lambda a: 'exceed' in ((a.note or '') + (a.summary or '')).lower()
        )
        self.assertTrue(
            activity,
            "The merchant must be told the refund exceeds the invoiced "
            "amount",
        )

    def test_exact_full_cumulative_refunds_post(self):
        """Two partial refunds summing exactly to the invoice total must
        both post — the guard must not block legitimate refunds."""
        self._serve(self._refund(7101, 120.0))
        s, errors, _sk = self.importer.import_refunds_for_order(
            self.order_binding)
        self.assertEqual((s, errors), (1, 0))
        self._serve(self._refund(7101, 120.0), self._refund(7102, 80.0))
        s, errors, _sk = self.importer.import_refunds_for_order(
            self.order_binding)
        self.assertEqual((s, errors), (1, 0))
        cns = self._posted_credit_notes()
        self.assertEqual(len(cns), 2, "Both legitimate refunds must post")
        self.assertAlmostEqual(sum(cns.mapped('amount_total')), 200.0,
                               places=2)
