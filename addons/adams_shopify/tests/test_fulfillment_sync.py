# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, call

from odoo.tests.common import TransactionCase


class TestFulfillmentSync(TransactionCase):

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
        self.partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@example.com',
        })
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
        })
        self.order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': 'gid://shopify/Order/5000',
            'sync_status': 'synced',
        })

    def test_push_skips_without_shopify_id(self):
        """Should not push fulfillment if binding has no shopify_id."""
        from ..sync.fulfillment_sync import FulfillmentSync

        binding_no_id = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': False,
            'sync_status': 'synced',
        })

        syncer = FulfillmentSync.__new__(FulfillmentSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        syncer.push_fulfillment(binding_no_id)
        syncer.client.execute.assert_not_called()
        syncer.client.execute_mutation.assert_not_called()

    def test_push_fulfillment_queries_fulfillment_orders(self):
        """Should query Shopify for fulfillment orders."""
        from ..sync.fulfillment_sync import FulfillmentSync

        syncer = FulfillmentSync.__new__(FulfillmentSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        # Return empty fulfillment orders
        syncer.client.execute.return_value = {
            'data': {
                'order': {
                    'fulfillmentOrders': {'edges': []}
                }
            }
        }

        syncer.push_fulfillment(self.order_binding)
        syncer.client.execute.assert_called_once()
        # No fulfillment orders → no mutation
        syncer.client.execute_mutation.assert_not_called()

    def test_push_fulfillment_creates_fulfillment(self):
        """Should create fulfillment for OPEN fulfillment orders with remaining items."""
        from ..sync.fulfillment_sync import FulfillmentSync

        syncer = FulfillmentSync.__new__(FulfillmentSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        syncer.client.execute.return_value = {
            'data': {
                'order': {
                    'fulfillmentOrders': {
                        'edges': [{
                            'node': {
                                'id': 'gid://shopify/FulfillmentOrder/1',
                                'status': 'OPEN',
                                'lineItems': {
                                    'edges': [{
                                        'node': {
                                            'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                                            'remainingQuantity': 2,
                                        }
                                    }]
                                }
                            }
                        }]
                    }
                }
            }
        }

        syncer.push_fulfillment(
            self.order_binding,
            tracking_number='TRACK123',
            tracking_url='https://track.example.com/TRACK123',
            tracking_company='FedEx',
        )

        syncer.client.execute_mutation.assert_called_once()
        call_args = syncer.client.execute_mutation.call_args
        variables = call_args[1].get('variables') or call_args[0][1]
        fulfillment = variables['fulfillment']

        # Verify tracking info
        self.assertEqual(fulfillment['trackingInfo']['number'], 'TRACK123')
        self.assertEqual(fulfillment['trackingInfo']['company'], 'FedEx')

        # Verify line items
        line_items_by_fo = fulfillment['lineItemsByFulfillmentOrder']
        self.assertEqual(len(line_items_by_fo), 1)
        self.assertEqual(
            line_items_by_fo[0]['fulfillmentOrderId'],
            'gid://shopify/FulfillmentOrder/1',
        )

    def test_push_skips_closed_fulfillment_orders(self):
        """Should skip fulfillment orders that are CLOSED."""
        from ..sync.fulfillment_sync import FulfillmentSync

        syncer = FulfillmentSync.__new__(FulfillmentSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        syncer.client.execute.return_value = {
            'data': {
                'order': {
                    'fulfillmentOrders': {
                        'edges': [{
                            'node': {
                                'id': 'gid://shopify/FulfillmentOrder/1',
                                'status': 'CLOSED',
                                'lineItems': {
                                    'edges': [{
                                        'node': {
                                            'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                                            'remainingQuantity': 2,
                                        }
                                    }]
                                }
                            }
                        }]
                    }
                }
            }
        }

        syncer.push_fulfillment(self.order_binding)
        syncer.client.execute_mutation.assert_not_called()

    def test_push_skips_zero_remaining(self):
        """Should skip line items with 0 remaining quantity."""
        from ..sync.fulfillment_sync import FulfillmentSync

        syncer = FulfillmentSync.__new__(FulfillmentSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        syncer.client.execute.return_value = {
            'data': {
                'order': {
                    'fulfillmentOrders': {
                        'edges': [{
                            'node': {
                                'id': 'gid://shopify/FulfillmentOrder/1',
                                'status': 'OPEN',
                                'lineItems': {
                                    'edges': [{
                                        'node': {
                                            'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                                            'remainingQuantity': 0,
                                        }
                                    }]
                                }
                            }
                        }]
                    }
                }
            }
        }

        syncer.push_fulfillment(self.order_binding)
        # No items to fulfill → no mutation
        syncer.client.execute_mutation.assert_not_called()
