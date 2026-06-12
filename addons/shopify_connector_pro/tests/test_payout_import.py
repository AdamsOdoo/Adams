# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestPayoutImport(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })

    def _make_payout_response(self, payouts, has_next=False):
        return {
            'data': {
                'shopifyPaymentsAccount': {
                    'payouts': {
                        'edges': [
                            {'cursor': f'c{i}', 'node': p}
                            for i, p in enumerate(payouts)
                        ],
                        'pageInfo': {
                            'hasNextPage': has_next,
                            'endCursor': 'cursor_end',
                        },
                    },
                },
            },
        }

    def _make_txn_response(self, transactions):
        return {
            'data': {
                'shopifyPaymentsAccount': {
                    'payoutTransactions': {
                        'edges': [
                            {'cursor': f't{i}', 'node': t}
                            for i, t in enumerate(transactions)
                        ],
                        'pageInfo': {'hasNextPage': False, 'endCursor': None},
                    },
                },
            },
        }

    def test_import_payout_creates_record(self):
        """Importing a payout should create a shopify.payout record."""
        from ..sync.payout_sync import PayoutSync
        syncer = PayoutSync.__new__(PayoutSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        payout_node = {
            'id': 'gid://shopify/ShopifyPaymentsPayout/100',
            'legacyResourceId': '100',
            'status': 'PAID',
            'net': {'amount': '950.00', 'currencyCode': 'USD'},
            'gross': {'amount': '1000.00', 'currencyCode': 'USD'},
            'transactionFee': {'amount': '50.00', 'currencyCode': 'USD'},
            'summary': {
                'chargesGross': {'amount': '1000.00'},
                'refundsGross': {'amount': '0.00'},
                'adjustmentsGross': {'amount': '0.00'},
                'chargesFee': {'amount': '30.00'},
                'refundsFee': {'amount': '0.00'},
                'adjustmentsFee': {'amount': '0.00'},
            },
            'issuedAt': '2026-03-15',
        }

        syncer.client.execute.side_effect = [
            self._make_payout_response([payout_node]),
            self._make_txn_response([]),
        ]

        success, errors = syncer.import_payouts()
        self.assertEqual(success, 1)
        self.assertEqual(errors, 0)

        payout = self.env['shopify.payout'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_payout_id', '=', '100'),
        ])
        self.assertTrue(payout)
        self.assertEqual(payout.status, 'paid')
        self.assertAlmostEqual(payout.amount, 950.0)
        self.assertAlmostEqual(payout.gross_amount, 1000.0)
        self.assertAlmostEqual(payout.fees_amount, 50.0)

    def test_duplicate_payout_updates_instead_of_duplicate(self):
        """Importing the same payout twice should update, not duplicate."""
        self.env['shopify.payout'].create({
            'backend_id': self.backend.id,
            'shopify_payout_id': '200',
            'status': 'scheduled',
            'amount': 500.0,
        })

        from ..sync.payout_sync import PayoutSync
        syncer = PayoutSync.__new__(PayoutSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        payout_node = {
            'id': 'gid://shopify/ShopifyPaymentsPayout/200',
            'legacyResourceId': '200',
            'status': 'PAID',
            'net': {'amount': '500.00', 'currencyCode': 'USD'},
            'gross': {'amount': '550.00', 'currencyCode': 'USD'},
            'transactionFee': {'amount': '50.00', 'currencyCode': 'USD'},
            'summary': {},
            'issuedAt': '2026-03-20',
        }
        syncer.client.execute.side_effect = [
            self._make_payout_response([payout_node]),
            self._make_txn_response([]),
        ]
        syncer.import_payouts()

        payouts = self.env['shopify.payout'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_payout_id', '=', '200'),
        ])
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts.status, 'paid')

    def test_no_shopify_payments_account(self):
        """Should handle missing Shopify Payments account gracefully."""
        from ..sync.payout_sync import PayoutSync
        syncer = PayoutSync.__new__(PayoutSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()
        syncer.client.execute.return_value = {
            'data': {'shopifyPaymentsAccount': None},
        }

        success, errors = syncer.import_payouts()
        self.assertEqual(success, 0)
        self.assertEqual(errors, 0)

    def test_payout_with_transactions(self):
        """Should import transactions linked to the payout."""
        from ..sync.payout_sync import PayoutSync
        syncer = PayoutSync.__new__(PayoutSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        payout_node = {
            'id': 'gid://shopify/ShopifyPaymentsPayout/300',
            'legacyResourceId': '300',
            'status': 'PAID',
            'net': {'amount': '100.00', 'currencyCode': 'USD'},
            'gross': {'amount': '110.00', 'currencyCode': 'USD'},
            'transactionFee': {'amount': '10.00', 'currencyCode': 'USD'},
            'summary': {},
            'issuedAt': '2026-03-25',
        }
        txn = {
            'id': 'gid://shopify/ShopifyPaymentsPayoutTransaction/1',
            'type': 'CHARGE',
            'sourceType': 'CHARGE',
            'amount': {'amount': '110.00', 'currencyCode': 'USD'},
            'fee': {'amount': '10.00', 'currencyCode': 'USD'},
            'net': {'amount': '100.00', 'currencyCode': 'USD'},
            'sourceOrderTransactionId': 'gid://shopify/OrderTransaction/999',
            'processedAt': '2026-03-25T12:00:00Z',
        }

        syncer.client.execute.side_effect = [
            self._make_payout_response([payout_node]),
            self._make_txn_response([txn]),
        ]
        syncer.import_payouts()

        payout = self.env['shopify.payout'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_payout_id', '=', '300'),
        ])
        self.assertEqual(payout.transaction_count, 1)
        self.assertEqual(payout.transaction_ids[0].transaction_type, 'charge')
        self.assertAlmostEqual(payout.transaction_ids[0].amount, 110.0)

    @mute_logger('odoo.addons.shopify_connector_pro.sync.payout_sync')
    def test_api_error_returns_error_count(self):
        """API errors should be counted, not crash."""
        from ..sync.payout_sync import PayoutSync
        syncer = PayoutSync.__new__(PayoutSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()
        syncer.client.execute.side_effect = Exception("API error")

        success, errors = syncer.import_payouts()
        self.assertEqual(success, 0)
        self.assertEqual(errors, 1)
