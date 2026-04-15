# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import fields, tools

from .base_importer import BaseImporter
from .checksum import compute_checksum
from ..shopify_api.queries.abandoned_cart import FETCH_ABANDONED_CHECKOUTS

_logger = logging.getLogger(__name__)


class AbandonedCartImporter(BaseImporter):
    entity_name = 'abandoned_cart'
    binding_model = 'shopify.abandoned.cart'

    def _compute_shopify_checksum(self, node):
        return compute_checksum({
            'updatedAt': node.get('updatedAt', ''),
            'totalPrice': (
                node.get('totalPriceSet', {})
                .get('shopMoney', {})
                .get('amount', '')
            ),
        })

    def _import_one(self, node, existing_binding=None):
        shopify_id = node.get('id', '')
        checksum = self._compute_shopify_checksum(node)

        # Extract customer info
        customer = node.get('customer') or {}
        customer_name_parts = [
            customer.get('firstName', ''),
            customer.get('lastName', ''),
        ]
        customer_name = ' '.join(p for p in customer_name_parts if p).strip()

        # Extract price data
        total_price_set = node.get('totalPriceSet', {})
        shop_money = total_price_set.get('shopMoney', {})
        subtotal_set = node.get('subtotalPriceSet', {})
        subtotal_money = subtotal_set.get('shopMoney', {})

        # Serialize line items for later use
        line_items_data = []
        for edge in node.get('lineItems', {}).get('edges', []):
            li = edge.get('node', {})
            variant = li.get('variant') or {}
            price_set = li.get('originalUnitPriceSet', {})
            price = float(
                price_set.get('shopMoney', {}).get('amount', 0)
            )
            line_items_data.append({
                'title': li.get('title', ''),
                'quantity': li.get('quantity', 1),
                'variant_id': variant.get('id', ''),
                'product_id': (variant.get('product') or {}).get('id', ''),
                'sku': variant.get('sku', ''),
                'price': price,
            })

        vals = {
            'abandoned_at': node.get('createdAt'),
            'recovery_url': node.get('abandonedCheckoutUrl', ''),
            'customer_email': customer.get('email', ''),
            'customer_phone': customer.get('phone', ''),
            'customer_name': customer_name,
            'shopify_customer_id': customer.get('id', ''),
            'total_price': float(shop_money.get('amount', 0)),
            'subtotal_price': float(subtotal_money.get('amount', 0)),
            'currency_code': shop_money.get('currencyCode', 'USD'),
            'line_items_json': json.dumps(line_items_data),
            'sync_checksum': checksum,
            'sync_status': 'synced',
            'last_sync_date': fields.Datetime.now(),
        }

        if existing_binding:
            existing_binding.write(vals)
        else:
            vals.update({
                'backend_id': self.backend.id,
                'shopify_id': shopify_id,
            })
            binding = self.env['shopify.abandoned.cart'].create(vals)
            # Auto-create quotation if configured
            if self.backend.auto_create_abandoned_quotation:
                try:
                    binding._create_draft_quotation()
                except Exception as e:
                    _logger.warning(
                        "Failed to create quotation for abandoned cart %s: %s",
                        shopify_id, e,
                    )


class AbandonedCartSync:
    """Orchestrator for abandoned cart import."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.importer = AbandonedCartImporter(env, backend)

    def import_abandoned_carts(self):
        """Import abandoned checkouts from Shopify."""
        page_size = min(self.backend.batch_size or 50, 50)
        nodes = self.importer.client.fetch_paginated(
            FETCH_ABANDONED_CHECKOUTS,
            'abandonedCheckouts',
            page_size=page_size,
            estimated_cost_per_page=15,
        )
        success, errors, skipped = self.importer.import_batch(nodes)
        _logger.info(
            "Abandoned cart import for backend %s: %d imported, %d errors, %d skipped",
            self.backend.id, success, errors, skipped,
        )

        # Auto-detect recovered carts
        self._detect_recovered_carts()

        return success, errors, skipped

    def _detect_recovered_carts(self):
        """Mark abandoned carts as recovered if a matching order exists."""
        open_carts = self.env['shopify.abandoned.cart'].search([
            ('backend_id', '=', self.backend.id),
            ('recovered', '=', False),
            ('customer_email', '!=', False),
            ('abandoned_at', '!=', False),
        ])
        if not open_carts:
            return

        OrderBinding = self.env['shopify.order.binding']
        for cart in open_carts:
            normalized = tools.email_normalize(cart.customer_email)
            if not normalized:
                continue
            # Scope search to orders for this backend after the cart was
            # abandoned, matched by normalized customer email.
            matches = OrderBinding.search([
                ('backend_id', '=', self.backend.id),
                ('shopify_created_at', '>=', cart.abandoned_at),
                ('odoo_id.partner_id.email_normalized', '=', normalized),
            ], limit=1)
            if matches:
                cart.write({
                    'recovered': True,
                    'recovered_order_binding_id': matches.id,
                })
