# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from .checksum import compute_checksum
from ..shopify_api.queries.discount_import import FETCH_DISCOUNT_CODES

_logger = logging.getLogger(__name__)


class DiscountImporter:
    """Import discount codes from Shopify into Odoo."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        from ..shopify_api.client import ShopifyClient
        self.client = ShopifyClient(backend)

    def import_discounts(self):
        """Fetch all code discounts from Shopify and import them."""
        nodes = self.client.fetch_paginated(
            FETCH_DISCOUNT_CODES, 'codeDiscountNodes',
            page_size=min(self.backend.batch_size, 50),
            estimated_cost_per_page=15,
        )

        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'discount',
            'operation': 'import',
        })
        success = errors = skipped = 0
        error_details = []

        for node in nodes:
            shopify_id = node.get('id', '')
            try:
                discount_data = node.get('codeDiscount', {})
                if not discount_data:
                    skipped += 1
                    continue

                # Extract the first code
                codes_edges = discount_data.get('codes', {}).get('edges', [])
                if not codes_edges:
                    skipped += 1
                    continue
                code = codes_edges[0].get('node', {}).get('code', '')
                if not code:
                    skipped += 1
                    continue

                # Check if already imported
                existing = self.env['shopify.discount.code'].search([
                    ('backend_id', '=', self.backend.id),
                    ('shopify_id', '=', shopify_id),
                ], limit=1)
                if existing:
                    self._update_discount(existing, discount_data, code)
                    skipped += 1
                    continue

                # Also check by code
                existing_by_code = self.env['shopify.discount.code'].search([
                    ('backend_id', '=', self.backend.id),
                    ('code', '=ilike', code),
                ], limit=1)
                if existing_by_code:
                    existing_by_code.shopify_id = shopify_id
                    existing_by_code._mark_synced(checksum=shopify_id)
                    skipped += 1
                    continue

                self._create_discount(shopify_id, discount_data, code)
                success += 1

            except Exception as e:
                _logger.warning("Failed to import discount %s: %s", shopify_id, e)
                errors += 1
                error_details.append(f"{shopify_id}: {e}")

        log._finalize(success, errors, skipped, '\n'.join(error_details) or None)
        return success, errors, skipped

    def _parse_discount_value(self, discount_data):
        """Extract discount type and value from Shopify customerGets."""
        customer_gets = discount_data.get('customerGets', {})
        value_data = customer_gets.get('value', {})

        if 'percentage' in value_data:
            return 'percentage', value_data['percentage'] * 100
        elif 'amount' in value_data:
            amount = value_data['amount']
            if isinstance(amount, dict):
                return 'fixed_amount', float(amount.get('amount', 0))
            return 'fixed_amount', float(amount)
        return 'percentage', 0

    def _parse_minimum(self, discount_data):
        """Extract minimum order amount from Shopify minimumRequirement."""
        min_req = discount_data.get('minimumRequirement', {})
        subtotal = min_req.get('greaterThanOrEqualToSubtotal', {})
        if isinstance(subtotal, dict):
            return float(subtotal.get('amount', 0))
        return 0

    def _create_discount(self, shopify_id, discount_data, code):
        """Create a new discount code binding from Shopify data."""
        discount_type, discount_value = self._parse_discount_value(discount_data)
        minimum = self._parse_minimum(discount_data)

        # Find or create a default promoter for imported discounts
        promoter = self.env['shopify.promoter'].search([
            ('company_id', '=', self.backend.company_id.id),
            ('name', '=', 'Shopify Imported'),
        ], limit=1)
        if not promoter:
            promoter = self.env['shopify.promoter'].create({
                'name': 'Shopify Imported',
                'partner_id': self.backend.company_id.partner_id.id,
                'company_id': self.backend.company_id.id,
                'code_prefix': 'IMP',
                'status': 'active',
            })

        self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'shopify_id': shopify_id,
            'promoter_id': promoter.id,
            'code': code,
            'discount_type': discount_type,
            'discount_value': discount_value,
            'minimum_order_amount': minimum,
            'usage_limit': discount_data.get('usageLimit') or 0,
            'active_on_shopify': discount_data.get('status') == 'ACTIVE',
            'starts_at': discount_data.get('startsAt') or False,
            'ends_at': discount_data.get('endsAt') or False,
            'sync_status': 'synced',
            'sync_checksum': shopify_id,
            'last_sync_date': fields.Datetime.now(),
        })

    def _update_discount(self, existing, discount_data, code):
        """Update an existing discount code binding."""
        discount_type, discount_value = self._parse_discount_value(discount_data)
        existing.write({
            'active_on_shopify': discount_data.get('status') == 'ACTIVE',
            'discount_type': discount_type,
            'discount_value': discount_value,
        })
        existing._mark_synced(checksum=existing.shopify_id)
