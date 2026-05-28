# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from ..shopify_api.queries.gift_card import FETCH_GIFT_CARDS

_logger = logging.getLogger(__name__)


class GiftCardSync:
    """Import gift cards from Shopify."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.client = backend._make_api_client()

    def import_gift_cards(self):
        """Fetch all gift cards from Shopify and create/update records."""
        nodes = self.client.fetch_paginated(
            FETCH_GIFT_CARDS, 'giftCards',
            page_size=min(self.backend.batch_size, 50),
            estimated_cost_per_page=10,
        )

        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'gift_card',
            'operation': 'import',
        })
        success = errors = skipped = 0
        error_details = []
        for node in nodes:
            shopify_id = node.get('id', '')
            try:
                existing = self.env['shopify.gift.card'].search([
                    ('backend_id', '=', self.backend.id),
                    ('shopify_id', '=', shopify_id),
                ], limit=1)

                initial_val = node.get('initialValue', {})
                balance_val = node.get('balance', {})

                vals = {
                    'code_masked': node.get('maskedCode', ''),
                    'initial_amount': float(initial_val.get('amount', 0)),
                    'balance': float(balance_val.get('amount', 0)),
                    'currency_code': initial_val.get('currencyCode', ''),
                    'status': 'enabled' if node.get('enabled') else 'disabled',
                    'expires_on': node.get('expiresOn') or False,
                }

                # Link to customer binding if available
                customer_data = node.get('customer') or {}
                customer_id = customer_data.get('id', '')
                if customer_id:
                    cb = self.env['shopify.customer.binding'].search([
                        ('backend_id', '=', self.backend.id),
                        ('shopify_id', '=', customer_id),
                    ], limit=1)
                    if cb:
                        vals['customer_binding_id'] = cb.id

                # Link to order binding if available
                order_data = node.get('order') or {}
                order_id = order_data.get('id', '')
                if order_id:
                    ob = self.env['shopify.order.binding'].search([
                        ('backend_id', '=', self.backend.id),
                        ('shopify_id', '=', order_id),
                    ], limit=1)
                    if ob:
                        vals['order_binding_id'] = ob.id

                if existing:
                    existing.write(vals)
                    existing._mark_synced(checksum=shopify_id)
                    skipped += 1
                else:
                    vals.update({
                        'backend_id': self.backend.id,
                        'shopify_id': shopify_id,
                        'sync_status': 'synced',
                        'sync_checksum': shopify_id,
                        'last_sync_date': fields.Datetime.now(),
                    })
                    self.env['shopify.gift.card'].create(vals)
                    success += 1

            except Exception as e:
                _logger.warning("Failed to import gift card %s: %s", shopify_id, e)
                errors += 1
                error_details.append(f"{shopify_id}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped
