# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Permanent total-check guard (DEC-011/012; AUD-001 workstream item 3a).

Computed invoice totals are compared against the Shopify charged total
(totalPriceSet, stamped on the order binding at import) before ANY
auto-posting. On mismatch beyond tolerance the invoice stays in DRAFT
with a warning activity — never wrong money, never silent failure.
"""
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestTotalGuardPaymentPath(ShopifyAccountingMixin, TransactionCase):
    """Guard on the payment-transition posting paths."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Guard Test Store',
            'shop_url': 'guard-test.myshopify.com',
            'access_token': 'shpat_guard_test',
            'company_id': self.env.company.id,
            'auto_handle_payment_transitions': True,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.partner = self._create_accounting_partner('Guard Buyer')
        self.product = self.env['product.product'].create({
            'name': 'Guard Widget', 'list_price': 100.0,
        })
        self.product.taxes_id = [(5, 0, 0)]
        self._set_product_income_account(self.product)
        self.order = self.env['sale.order'].with_context(
            shopify_no_auto_export=True,
        ).create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        self.order.with_context(shopify_no_auto_export=True).action_confirm()
        self.invoice = self.order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()

    def _binding(self, stamp, status='authorized', gid_suffix='1'):
        return self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': 'gid://shopify/Order/91%s' % gid_suffix,
            'shopify_order_name': '#GRD-%s' % gid_suffix,
            'shopify_financial_status': status,
            'sync_status': 'synced',
            'shopify_total_amount': stamp,
        })

    def _handler(self):
        from ..sync.payment_status_sync import PaymentStatusHandler
        return PaymentStatusHandler(self.env, self.backend)

    def _mismatch_activity(self):
        return self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
            ('summary', 'ilike', 'total mismatch'),
        ], limit=1)

    def test_mismatch_blocks_posting(self):
        """Stamp differs from the computed invoice total: the invoice
        must stay in DRAFT, an activity must explain it, and the binding
        must NOT advance to paid (retryable)."""
        binding = self._binding(stamp=999.99)
        result = self._handler().handle_status_change(
            binding, 'authorized', 'paid',
        )
        self.assertFalse(result, "Transition must report failure")
        self.assertEqual(
            self.invoice.state, 'draft',
            "Guard must block posting on total mismatch (DEC-011)",
        )
        self.assertEqual(
            binding.shopify_financial_status, 'authorized',
            "Binding must not advance when posting was blocked",
        )
        activity = self._mismatch_activity()
        self.assertTrue(activity, "Mismatch must be merchant-visible")
        note = activity.note or ''
        self.assertIn('999.99', note, "Message must state the Shopify total")
        self.assertIn('DRAFT', note, "Message must state the invoice state")

    def test_match_posts_normally(self):
        """Stamp equals the computed total: no false positive."""
        binding = self._binding(
            stamp=self.invoice.amount_total, gid_suffix='2',
        )
        result = self._handler().handle_status_change(
            binding, 'authorized', 'paid',
        )
        self.assertTrue(result)
        self.assertEqual(self.invoice.state, 'posted')
        self.assertFalse(self._mismatch_activity())

    def test_no_stamp_posts_normally(self):
        """Zero stamp (binding created before the field existed, upgraded
        DBs): the guard must skip — no behavior change for legacy data."""
        binding = self._binding(stamp=0.0, gid_suffix='3')
        result = self._handler().handle_status_change(
            binding, 'authorized', 'paid',
        )
        self.assertTrue(result)
        self.assertEqual(self.invoice.state, 'posted')

    def test_partially_paid_mismatch_blocks_posting(self):
        """Same guard on the partially-paid posting branch."""
        binding = self._binding(
            stamp=999.99, status='pending', gid_suffix='4',
        )
        result = self._handler().handle_status_change(
            binding, 'pending', 'partially_paid',
        )
        self.assertFalse(result)
        self.assertEqual(self.invoice.state, 'draft')
        self.assertTrue(self._mismatch_activity())


class TestTotalGuardAutoInvoice(ShopifyAccountingMixin, TransactionCase):
    """Guard on the order-import auto-invoice path, through the real
    importer (production path, simulator-grade node payload)."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Guard Import Store',
            'shop_url': 'guard-import.myshopify.com',
            'access_token': 'shpat_guard_import',
            'company_id': self.env.company.id,
            'auto_create_invoice': True,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.product = self.env['product.product'].create({
            'name': 'Guard Import Widget',
            'list_price': 50.0,
            'default_code': 'GRD-WIDGET-1',
        })
        self.product.taxes_id = [(5, 0, 0)]
        self._set_product_income_account(self.product)
        pb = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/9100',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/9200',
            'product_binding_id': pb.id,
            'sync_status': 'synced',
        })
        from ..sync.order_sync import OrderImporter
        self.importer = OrderImporter.__new__(OrderImporter)
        self.importer.env = self.env
        self.importer.backend = self.backend
        self.importer.client = MagicMock()
        self.importer._currency_cache = {}
        self.importer._pricelist_cache = {}
        self.importer._shipping_product = None

    def _node(self, total='120.0'):
        """Lines sum to 100.00 USD; Shopify claims `total` was charged.
        With total='120.0' the computed invoice (100.00) MUST NOT post."""
        money = lambda amt: {  # noqa: E731
            'shopMoney': {'amount': amt, 'currencyCode': 'USD'},
        }
        return {
            'id': 'gid://shopify/Order/9001',
            'name': '#GRDI-1001',
            'createdAt': '2026-06-01T10:00:00Z',
            'updatedAt': '2026-06-01T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'totalPriceSet': money(total),
            'customer': {
                'id': 'gid://shopify/Customer/9500',
                'email': 'guard-buyer@example.com',
                'firstName': 'Guard',
                'lastName': 'Buyer',
            },
            'shippingAddress': None,
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/9001',
                        'title': 'Guard Import Widget',
                        'quantity': 2,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/9200',
                            'sku': 'GRD-WIDGET-1',
                            'product': {'id': 'gid://shopify/Product/9100'},
                        },
                        'originalUnitPriceSet': money('50.0'),
                        'discountAllocations': [],
                        'taxLines': [],
                    }
                }]
            },
            'shippingLines': {'edges': []},
            'refunds': [],
        }

    def test_auto_invoice_mismatch_stays_draft_with_activity(self):
        """Shopify charged 120.00, computed invoice totals 100.00: the
        invoice must exist but stay DRAFT, with the mismatch activity;
        the binding must carry the 120.00 stamp."""
        self.importer._import_one(self._node(total='120.0'), None)

        order = self.env['sale.order'].search([
            ('shopify_order_name', '=', '#GRDI-1001'),
        ], limit=1)
        self.assertTrue(order, "Order must be imported")
        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state != 'cancel'
        )
        self.assertTrue(invoices, "Invoice must be created")
        self.assertEqual(
            invoices[0].state, 'draft',
            "Guard must keep the mismatched invoice in draft (DEC-011)",
        )
        activity = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
            ('summary', 'ilike', 'total mismatch'),
        ], limit=1)
        self.assertTrue(activity, "Mismatch must be merchant-visible")
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/9001'),
        ], limit=1)
        self.assertAlmostEqual(
            binding.shopify_total_amount, 120.0, places=2,
            msg="Shopify total must be stamped on the binding at import",
        )

    def test_auto_invoice_match_posts(self):
        """Totals agree: the invoice posts as before (no false positive)."""
        self.importer._import_one(self._node(total='100.0'), None)
        order = self.env['sale.order'].search([
            ('shopify_order_name', '=', '#GRDI-1001'),
        ], limit=1)
        posted = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
        )
        self.assertTrue(posted, "Matching invoice must post normally")
        self.assertAlmostEqual(posted[0].amount_total, 100.0, places=2)
