# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Payout / settlement import from Shopify Payments."""

import logging

from odoo import fields as odoo_fields

_logger = logging.getLogger(__name__)


class PayoutSync:
    """Import Shopify Payments payouts and their transaction breakdowns."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def import_payouts(self):
        """Fetch and import all new payouts from Shopify Payments."""
        from ..shopify_api.queries.payout import FETCH_PAYOUTS

        success = errors = 0
        cursor = None
        has_more = True

        while has_more:
            variables = {'first': 25}
            if cursor:
                variables['after'] = cursor

            try:
                body = self.client.execute(FETCH_PAYOUTS, variables, estimated_cost=10)
            except Exception as e:
                _logger.exception("Failed to fetch payouts: %s", e)
                return success, errors + 1

            account = body.get('data', {}).get('shopifyPaymentsAccount')
            if not account:
                _logger.info("No Shopify Payments account found for backend %s", self.backend.id)
                return success, errors

            payouts_data = account.get('payouts', {})
            edges = payouts_data.get('edges', [])
            page_info = payouts_data.get('pageInfo', {})

            for edge in edges:
                node = edge.get('node', {})
                try:
                    self._import_payout(node)
                    success += 1
                except Exception as e:
                    _logger.warning("Failed to import payout %s: %s", node.get('id'), e)
                    errors += 1

            has_more = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor') or None

        _logger.info(
            "Payout import for backend %s: %d success, %d errors",
            self.backend.id, success, errors,
        )
        return success, errors

    def _import_payout(self, node):
        """Import or update a single payout record."""
        Payout = self.env['shopify.payout']
        shopify_id = node.get('legacyResourceId') or node.get('id', '')

        existing = Payout.search([
            ('backend_id', '=', self.backend.id),
            ('shopify_payout_id', '=', str(shopify_id)),
        ], limit=1)

        currency = self._resolve_currency(
            node.get('net', {}).get('currencyCode', 'USD')
        )

        summary = node.get('summary', {})

        vals = {
            'backend_id': self.backend.id,
            'shopify_payout_id': str(shopify_id),
            'status': self._map_status(node.get('status', '')),
            'amount': float(node.get('net', {}).get('amount', 0)),
            'currency_id': currency.id if currency else False,
            'gross_amount': float(node.get('gross', {}).get('amount', 0)),
            'fees_amount': float(node.get('transactionFee', {}).get('amount', 0)),
            'payout_date': self._parse_date(node.get('issuedAt')),
        }

        if summary:
            vals['charges_amount'] = float(
                summary.get('chargesGross', {}).get('amount', 0)
            )
            vals['refunds_amount'] = float(
                summary.get('refundsGross', {}).get('amount', 0)
            )
            vals['adjustments_amount'] = float(
                summary.get('adjustmentsGross', {}).get('amount', 0)
            )

        if existing:
            existing.write(vals)
            payout = existing
        else:
            payout = Payout.create(vals)

        # Import transactions for this payout
        self._import_payout_transactions(payout, node.get('id', ''))

        return payout

    def _import_payout_transactions(self, payout, shopify_gid):
        """Import transaction lines for a payout."""
        from ..shopify_api.queries.payout import FETCH_PAYOUT_TRANSACTIONS

        PayoutTxn = self.env['shopify.payout.transaction']
        cursor = None
        has_more = True

        while has_more:
            variables = {'payoutId': shopify_gid, 'first': 50}
            if cursor:
                variables['after'] = cursor

            try:
                body = self.client.execute(
                    FETCH_PAYOUT_TRANSACTIONS, variables, estimated_cost=10,
                )
            except Exception as e:
                _logger.warning("Failed to fetch payout transactions: %s", e)
                return

            account = body.get('data', {}).get('shopifyPaymentsAccount')
            if not account:
                return

            txn_data = account.get('payoutTransactions', {})
            edges = txn_data.get('edges', [])
            page_info = txn_data.get('pageInfo', {})

            currency = payout.currency_id

            for edge in edges:
                txn = edge.get('node', {})
                txn_id = txn.get('id', '')

                existing_txn = PayoutTxn.search([
                    ('payout_id', '=', payout.id),
                    ('shopify_transaction_id', '=', txn_id),
                ], limit=1)

                txn_vals = {
                    'payout_id': payout.id,
                    'shopify_transaction_id': txn_id,
                    'transaction_type': (txn.get('type', '') or '').lower() or False,
                    'source_type': (txn.get('sourceType', '') or '').lower() or False,
                    'amount': float(txn.get('amount', {}).get('amount', 0)),
                    'fee': float(txn.get('fee', {}).get('amount', 0)),
                    'net': float(txn.get('net', {}).get('amount', 0)),
                    'currency_id': currency.id if currency else False,
                    'source_order_id': txn.get('sourceOrderTransactionId', ''),
                    'processed_at': self._parse_datetime(txn.get('processedAt')),
                }

                if existing_txn:
                    existing_txn.write(txn_vals)
                else:
                    PayoutTxn.create(txn_vals)

            has_more = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor') or None

    def _map_status(self, status):
        """Map Shopify payout status to selection value."""
        mapping = {
            'SCHEDULED': 'scheduled',
            'IN_TRANSIT': 'in_transit',
            'PAID': 'paid',
            'FAILED': 'failed',
            'CANCELLED': 'cancelled',
        }
        return mapping.get(status, 'scheduled')

    def _resolve_currency(self, currency_code):
        """Find the Odoo currency for a code."""
        return self.env['res.currency'].search(
            [('name', '=', currency_code)], limit=1,
        )

    def _parse_date(self, date_str):
        """Parse ISO date string to date."""
        if not date_str:
            return False
        try:
            return odoo_fields.Date.to_date(date_str[:10])
        except (ValueError, TypeError):
            return False

    def _parse_datetime(self, dt_str):
        """Parse ISO datetime string."""
        if not dt_str:
            return False
        try:
            return odoo_fields.Datetime.to_datetime(dt_str.replace('T', ' ').replace('Z', ''))
        except (ValueError, TypeError):
            return False
