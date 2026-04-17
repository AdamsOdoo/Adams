# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields

from .base_exporter import BaseExporter
from .checksum import compute_checksum

_logger = logging.getLogger(__name__)


class DiscountExporter(BaseExporter):
    entity_name = 'discount'
    binding_model = 'shopify.discount.code'

    def _compute_checksum(self, binding):
        data = {
            'code': binding.code,
            'discount_type': binding.discount_type,
            'discount_value': binding.discount_value,
            'minimum_order_amount': binding.minimum_order_amount,
            'usage_limit': binding.usage_limit,
            'one_per_customer': binding.one_per_customer,
            'active_on_shopify': binding.active_on_shopify,
        }
        return compute_checksum(data)

    def _export_one(self, binding):
        if binding.shopify_id:
            self._update_discount(binding)
        else:
            self._create_discount(binding)

    def _create_discount(self, binding):
        if binding.discount_type == 'free_shipping':
            self._create_free_shipping_discount(binding)
        else:
            self._create_basic_discount(binding)

    def _create_basic_discount(self, binding):
        from ..shopify_api.queries.discount import DISCOUNT_CODE_BASIC_CREATE

        customer_gets = self._build_customer_gets(binding)
        variables = {
            'basicCodeDiscount': {
                'title': f"{binding.promoter_id.name} - {binding.code}",
                'code': binding.code,
                'startsAt': (
                    binding.starts_at.isoformat()
                    if binding.starts_at
                    else fields.Datetime.now().isoformat()
                ),
                'customerGets': customer_gets,
                'appliesOncePerCustomer': binding.one_per_customer,
            }
        }
        if binding.ends_at:
            variables['basicCodeDiscount']['endsAt'] = binding.ends_at.isoformat()
        if binding.usage_limit:
            variables['basicCodeDiscount']['usageLimit'] = binding.usage_limit
        if binding.minimum_order_amount:
            variables['basicCodeDiscount']['minimumRequirement'] = {
                'subtotal': {
                    'greaterThanOrEqualToSubtotal': str(binding.minimum_order_amount),
                }
            }

        result = self.client.execute_mutation(
            DISCOUNT_CODE_BASIC_CREATE,
            variables,
            result_key='discountCodeBasicCreate',
            estimated_cost=10,
        )
        discount_node = result.get('codeDiscountNode', {})
        binding.shopify_id = discount_node.get('id', '')

    def _create_free_shipping_discount(self, binding):
        from ..shopify_api.queries.discount import DISCOUNT_CODE_FREE_SHIPPING_CREATE

        starts_at = (
            binding.starts_at.isoformat()
            if binding.starts_at
            else fields.Datetime.now().isoformat()
        )
        variables = {
            'freeShippingCodeDiscount': {
                'title': f"{binding.promoter_id.name} - {binding.code}",
                'code': binding.code,
                'startsAt': starts_at,
                'appliesOncePerCustomer': binding.one_per_customer,
                'destination': {'all': True},
            }
        }
        if binding.ends_at:
            variables['freeShippingCodeDiscount']['endsAt'] = binding.ends_at.isoformat()
        if binding.usage_limit:
            variables['freeShippingCodeDiscount']['usageLimit'] = binding.usage_limit
        if binding.minimum_order_amount:
            variables['freeShippingCodeDiscount']['minimumRequirement'] = {
                'subtotal': {
                    'greaterThanOrEqualToSubtotal': str(binding.minimum_order_amount),
                }
            }

        result = self.client.execute_mutation(
            DISCOUNT_CODE_FREE_SHIPPING_CREATE,
            variables,
            result_key='discountCodeFreeShippingCreate',
            estimated_cost=10,
        )
        discount_node = result.get('codeDiscountNode', {})
        binding.shopify_id = discount_node.get('id', '')

    def _update_discount(self, binding):
        if binding.discount_type == 'free_shipping':
            self._update_free_shipping_discount(binding)
        else:
            self._update_basic_discount(binding)

    def _update_basic_discount(self, binding):
        from ..shopify_api.queries.discount import DISCOUNT_CODE_BASIC_UPDATE

        customer_gets = self._build_customer_gets(binding)
        variables = {
            'id': binding.shopify_id,
            'basicCodeDiscount': {
                'title': f"{binding.promoter_id.name} - {binding.code}",
                'customerGets': customer_gets,
                'appliesOncePerCustomer': binding.one_per_customer,
            }
        }
        if binding.ends_at:
            variables['basicCodeDiscount']['endsAt'] = binding.ends_at.isoformat()
        if binding.usage_limit:
            variables['basicCodeDiscount']['usageLimit'] = binding.usage_limit

        self.client.execute_mutation(
            DISCOUNT_CODE_BASIC_UPDATE,
            variables,
            result_key='discountCodeBasicUpdate',
            estimated_cost=10,
        )

    def _update_free_shipping_discount(self, binding):
        from ..shopify_api.queries.discount import DISCOUNT_CODE_FREE_SHIPPING_UPDATE

        variables = {
            'id': binding.shopify_id,
            'freeShippingCodeDiscount': {
                'title': f"{binding.promoter_id.name} - {binding.code}",
                'appliesOncePerCustomer': binding.one_per_customer,
                'destination': {'all': True},
            }
        }
        if binding.ends_at:
            variables['freeShippingCodeDiscount']['endsAt'] = binding.ends_at.isoformat()
        if binding.usage_limit:
            variables['freeShippingCodeDiscount']['usageLimit'] = binding.usage_limit

        self.client.execute_mutation(
            DISCOUNT_CODE_FREE_SHIPPING_UPDATE,
            variables,
            result_key='discountCodeFreeShippingUpdate',
            estimated_cost=10,
        )

    def _build_customer_gets(self, binding):
        if binding.discount_type == 'percentage':
            return {
                'value': {'percentage': binding.discount_value / 100.0},
                'items': {'allItems': True},
            }
        else:
            return {
                'value': {
                    'discountAmount': {
                        'amount': str(binding.discount_value),
                        'appliesOnEachItem': False,
                    },
                },
                'items': {'allItems': True},
            }


class DiscountSync:
    """Orchestrates discount code export."""

    def __init__(self, env, backend):
        self.env = env
        self.backend = backend
        self.exporter = DiscountExporter(env, backend)

    def export_discounts(self):
        return self.exporter.export_batch()
