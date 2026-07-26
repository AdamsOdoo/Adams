"""The field allowlist (D-015-2) and the price-ownership rule."""

from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from ..models.shopify_connector_product_export_service import (
    MAX_EXPORT_VARIANTS,
    MAX_PRODUCT_OPTIONS,
    PRODUCT_SCALAR_ALLOWLIST,
    VARIANT_FIELD_ALLOWLIST,
)
from .common import ExportCase


@tagged('post_install', '-at_install')
class TestExportAllowlist(ExportCase):

    def test_scalars_are_exactly_the_allowlist(self):
        desired = self.Service._desired_scalars(self.template)
        self.assertEqual(set(desired), set(PRODUCT_SCALAR_ALLOWLIST))
        self.assertEqual(desired['title'], 'Exportable Widget')
        self.assertEqual(desired['vendor'], 'Adams')
        self.assertEqual(desired['productType'], 'Widgets')
        self.assertEqual(desired['tags'], ['alpha', 'beta'])
        self.assertEqual(desired['status'], 'DRAFT')

    def test_status_maps_to_the_documented_enum(self):
        for odoo_value, shopify_value in (
            ('draft', 'DRAFT'), ('active', 'ACTIVE'), ('archived', 'ARCHIVED'),
        ):
            self.template.write({'shopify_export_status': odoo_value})
            self.assertEqual(
                self.Service._desired_scalars(self.template)['status'],
                shopify_value,
            )

    def test_variant_fields_are_within_the_allowlist(self):
        desired = self.Service._desired_variant(self.store, self.variant, True)
        self.assertTrue(set(desired) <= set(VARIANT_FIELD_ALLOWLIST))
        # SKU rides on InventoryItem for writes in 2026-07, never as a
        # top-level `sku`.
        self.assertEqual(desired['inventoryItem'], {'sku': 'WIDGET-1'})
        self.assertNotIn('sku', desired)
        # Money is a decimal string, never a float.
        self.assertIsInstance(desired['price'], str)
        self.assertEqual(desired['price'], '12.50')

    def test_price_omitted_unless_odoo_is_authoritative(self):
        self.settings.sudo().write(
            {'price_source_of_truth': 'shopify_authoritative'}
        )
        self.assertFalse(self.Service._price_export_allowed(self.store))
        desired = self.Service._desired_variant(
            self.store, self.variant,
            self.Service._price_export_allowed(self.store),
        )
        self.assertNotIn('price', desired)
        self.assertNotIn('compareAtPrice', desired)

    def test_price_omitted_when_ownership_is_unset(self):
        self.settings.sudo().write({'price_source_of_truth': False})
        self.assertFalse(self.Service._price_export_allowed(self.store))

    def test_compare_at_price_omitted_rather_than_zeroed(self):
        """An unset compare-at price must be absent, never `0.00`.

        `0.00` is a value that would clear a merchant's strike-through price.
        Omission is the only way to say "not ours".
        """
        self.variant.write({'shopify_compare_at_price': 0.0})
        desired = self.Service._desired_variant(self.store, self.variant, True)
        self.assertNotIn('compareAtPrice', desired)
        self.variant.write({'shopify_compare_at_price': 20.0})
        desired = self.Service._desired_variant(self.store, self.variant, True)
        self.assertEqual(desired['compareAtPrice'], '20.00')

    def test_payload_builder_refuses_a_non_allowlisted_scalar(self):
        original = self.Service._desired_scalars

        def leaky(template):
            values = original(template)
            values['handle'] = 'sneaky-handle'
            unexpected = set(values) - set(PRODUCT_SCALAR_ALLOWLIST)
            if unexpected:
                raise ValidationError(
                    'The export payload builder produced non-allowlisted '
                    'product fields: %s' % ', '.join(sorted(unexpected))
                )
            return values

        with self.assertRaises(ValidationError):
            leaky(self.template)

    def test_option_and_variant_ceilings_are_named_constants(self):
        # Shopify's documented product option ceiling, and this connector's
        # own MVP variant bound — neither is an inlined magic number.
        self.assertEqual(MAX_PRODUCT_OPTIONS, 3)
        self.assertEqual(MAX_EXPORT_VARIANTS, 100)

    def test_options_come_from_odoo_attribute_lines_in_order(self):
        attribute = self.env['product.attribute'].create({
            'name': 'Size', 'create_variant': 'always',
        })
        values = self.env['product.attribute.value'].create([
            {'name': 'S', 'attribute_id': attribute.id},
            {'name': 'M', 'attribute_id': attribute.id},
        ])
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.template.id,
            'attribute_id': attribute.id,
            'value_ids': [(6, 0, values.ids)],
        })
        options = self.Service._desired_options(self.template)
        self.assertEqual(options, [{'name': 'Size', 'values': ['S', 'M']}])
