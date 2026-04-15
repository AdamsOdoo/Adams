# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from ..shopify_api.queries.refund import FETCH_REFUNDS

_logger = logging.getLogger(__name__)


class RefundImporter:
    """Import refunds from Shopify and create credit notes in Odoo."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def import_refunds_for_order(self, order_binding):
        """Fetch and import all refunds for a given order binding."""
        if not order_binding.shopify_id:
            return 0, 0, 0

        try:
            body = self.client.execute(
                FETCH_REFUNDS,
                {'orderId': order_binding.shopify_id},
                estimated_cost=10,
            )
        except Exception as e:
            _logger.warning("Failed to fetch refunds for order %s: %s",
                            order_binding.shopify_id, e)
            return 0, 1, 0

        refunds = body.get('data', {}).get('order', {}).get('refunds', [])
        success = errors = skipped = 0

        for refund_data in refunds:
            shopify_refund_id = refund_data.get('id', '')
            existing = self.env['shopify.refund.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('shopify_id', '=', shopify_refund_id),
            ], limit=1)
            if existing:
                skipped += 1
                continue

            try:
                self._import_one_refund(refund_data, order_binding)
                success += 1
            except Exception as e:
                _logger.warning("Failed to import refund %s: %s", shopify_refund_id, e)
                errors += 1

        return success, errors, skipped

    def _import_one_refund(self, refund_data, order_binding):
        """Create a credit note from a Shopify refund."""
        shopify_refund_id = refund_data.get('id')
        total_refund = refund_data.get('totalRefundedSet', {}).get('shopMoney', {})
        refund_amount = float(total_refund.get('amount', 0))
        currency_code = total_refund.get('currencyCode', '')

        # Parse refund lines
        refund_lines = []
        for edge in refund_data.get('refundLineItems', {}).get('edges', []):
            node = edge.get('node', {})
            line_item = node.get('lineItem', {})
            variant = line_item.get('variant', {})
            subtotal = node.get('subtotalSet', {}).get('shopMoney', {})

            product = None
            variant_id = variant.get('id', '')
            if variant_id:
                vb = self.env['shopify.variant.binding'].search([
                    ('backend_id', '=', self.backend.id),
                    ('shopify_id', '=', variant_id),
                ], limit=1)
                if vb:
                    product = vb.odoo_id

            restock = (node.get('restockType', 'NO_RESTOCK') or 'NO_RESTOCK').lower()
            if restock not in ('no_restock', 'cancel', 'return'):
                restock = 'no_restock'

            refund_lines.append({
                'product_id': product.id if product else False,
                'quantity': node.get('quantity', 0),
                'amount': float(subtotal.get('amount', 0)),
                'restock_type': restock,
            })

        # Try to create credit note from posted invoice
        order = order_binding.odoo_id
        credit_note = None
        if order and order.invoice_ids:
            posted_invoices = order.invoice_ids.filtered(lambda i: i.state == 'posted')
            if posted_invoices:
                try:
                    move_reversal = self.env['account.move.reversal'].with_context(
                        active_model='account.move',
                        active_ids=posted_invoices[0].ids,
                    ).create({
                        'reason': refund_data.get('note') or 'Shopify Refund',
                        'journal_id': posted_invoices[0].journal_id.id,
                    })
                    reversal = move_reversal.refund_moves()
                    if reversal and reversal.get('res_id'):
                        credit_note = self.env['account.move'].browse(reversal['res_id'])
                except Exception as e:
                    _logger.warning("Could not create credit note for refund %s: %s",
                                    shopify_refund_id, e)

        binding_vals = {
            'backend_id': self.backend.id,
            'shopify_id': shopify_refund_id,
            'order_binding_id': order_binding.id,
            'shopify_order_id': order_binding.shopify_id,
            'refund_note': refund_data.get('note') or '',
            'refund_amount': refund_amount,
            'currency_code': currency_code,
            'sync_status': 'synced',
            'sync_checksum': shopify_refund_id,
            'last_sync_date': fields.Datetime.now(),
        }
        if credit_note:
            binding_vals['odoo_id'] = credit_note.id

        refund_binding = self.env['shopify.refund.binding'].create(binding_vals)

        for line in refund_lines:
            line['refund_binding_id'] = refund_binding.id
            self.env['shopify.refund.line'].create(line)

        return refund_binding


class RefundSync:
    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = RefundImporter(env, backend)

    def import_refunds(self):
        """Import refunds for orders with refund status."""
        order_bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('sync_status', '=', 'synced'),
            ('shopify_financial_status', 'in', ['refunded', 'partially_refunded']),
        ])
        total_success = total_errors = total_skipped = 0
        for ob in order_bindings:
            s, e, sk = self.importer.import_refunds_for_order(ob)
            total_success += s
            total_errors += e
            total_skipped += sk
        return total_success, total_errors, total_skipped
