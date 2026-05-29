# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestFieldMappingImport(TransactionCase):
    """Test that custom field mappings are actually applied during import."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def _make_importer(self, cls):
        """Create an importer bypassing __init__ to avoid API client creation."""
        importer = cls.__new__(cls)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        return importer

    def _base_node(self, shopify_id, **overrides):
        """Build a minimal Shopify product node for testing."""
        node = {
            'id': shopify_id,
            'title': 'Test Product',
            'descriptionHtml': '',
            'vendor': '',
            'productType': '',
            'tags': [],
            'status': 'ACTIVE',
            'handle': 'test',
            'variants': {'edges': []},
            'images': {'edges': []},
        }
        node.update(overrides)
        return node

    def test_product_import_applies_custom_mapping(self):
        """A custom import mapping should write the Shopify value to the Odoo field."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node('gid://shopify/Product/999', vendor='ACME Corp')

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/999'),
        ])
        self.assertTrue(binding, "Binding should be created")
        self.assertEqual(
            binding.odoo_id.description_purchase,
            'ACME Corp',
            "Custom mapping should write vendor to description_purchase",
        )

    def test_product_import_mapping_overrides_default(self):
        """Custom mapping applied AFTER hardcoded defaults overrides them."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'name',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/998',
            title='Original Title',
            vendor='Override Name',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/998'),
        ])
        self.assertEqual(
            binding.odoo_id.name,
            'Override Name',
            "Custom mapping should override the hardcoded title->name default",
        )

    def test_import_mapping_skips_inactive(self):
        """Inactive mappings should be ignored."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': False,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/997',
            vendor='Should Not Appear',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/997'),
        ])
        self.assertFalse(
            binding.odoo_id.description_purchase,
            "Inactive mapping should not apply",
        )

    def test_import_mapping_respects_direction(self):
        """Export-only mappings should not apply during import."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'vendor',
            'direction': 'export',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/996',
            vendor='Export Only',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/996'),
        ])
        self.assertFalse(
            binding.odoo_id.description_purchase,
            "Export-only mapping should not apply during import",
        )

    def test_import_mapping_dotted_shopify_path(self):
        """Dotted shopify_field paths should traverse nested dicts."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'metafields.edges.0.node.value',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/995',
            title='Deep Path',
            metafields={
                'edges': [
                    {'node': {'value': 'Deep Value'}}
                ]
            },
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/995'),
        ])
        self.assertEqual(
            binding.odoo_id.description_purchase,
            'Deep Value',
            "Dotted path should traverse nested Shopify data",
        )

    def test_import_mapping_invalid_odoo_field_skipped(self):
        """Mapping with non-existent Odoo field should be skipped gracefully."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'nonexistent_field_xyz',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/994',
            title='Safe Product',
            vendor='Test',
        )

        # Should not raise — just skip the invalid mapping
        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/994'),
        ])
        self.assertTrue(binding, "Import should succeed despite invalid mapping")
        self.assertEqual(binding.odoo_id.name, 'Safe Product')

    def test_import_mapping_incompatible_type_skipped(self):
        """Mapping a string to a Many2one field should be skipped, not crash."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'categ_id',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/891',
            title='Type Safety Product',
            vendor='SomeVendor',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/891'),
        ])
        self.assertTrue(binding, "Import should succeed despite incompatible mapping")
        # Also verify via _apply_import_mappings directly: string should not land in vals
        vals = {}
        importer._apply_import_mappings(vals, node)
        self.assertNotIn('categ_id', vals, "String value should not be applied to Many2one field")

    def test_import_mapping_numeric_coercion(self):
        """Mapping a numeric string to a Float field should coerce correctly."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'weight',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/892',
            title='Numeric Coerce Product',
            vendor='42.5',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/892'),
        ])
        self.assertTrue(binding)
        self.assertAlmostEqual(binding.odoo_id.weight, 42.5)

    def test_import_mapping_unrecognized_boolean_skipped(self):
        """Mapping an unrecognized string to a Boolean field should be skipped.

        Without type safety, 'banana' → bool('banana') → True via ORM coercion,
        silently corrupting a False value. With the fix, unrecognized strings
        are skipped entirely.
        """
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'sale_ok',
            'shopify_field': 'vendor',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/893',
            title='Bool Skip Product',
            vendor='banana',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/893'),
        ])
        self.assertTrue(binding, "Import should succeed despite unrecognized boolean")
        # Set sale_ok to False explicitly, then re-import with 'banana' mapping.
        # If type safety works, sale_ok should stay False (mapping skipped).
        binding.odoo_id.sale_ok = False
        # Re-apply the mappings directly to test the guard
        vals = {'sale_ok': False}
        importer._apply_import_mappings(vals, node)
        # 'banana' is not a recognized boolean → should NOT be in vals
        self.assertFalse(
            vals.get('sale_ok'),
            "Unrecognized boolean 'banana' should be skipped, not coerced",
        )

    def test_import_mapping_missing_shopify_key_skipped(self):
        """Missing key in Shopify data should skip mapping, not crash."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'nonexistent.deep.path',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductImporter
        importer = self._make_importer(ProductImporter)
        node = self._base_node(
            'gid://shopify/Product/993',
            title='No Crash',
        )

        with patch.object(importer, '_import_images'):
            importer._import_one(node)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/993'),
        ])
        self.assertTrue(binding, "Import should succeed despite missing Shopify key")


class TestFieldMappingExport(TransactionCase):
    """Test that custom field mappings are applied during export."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })
        self.product = self.env['product.template'].create({
            'name': 'Export Widget',
            'list_price': 19.99,
            'default_code': 'EXP-001',
            'description_purchase': 'Internal note',
        })
        self.binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/Product/500',
            'sync_status': 'pending',
        })

    def _make_exporter(self, cls):
        """Create an exporter bypassing __init__ to avoid API client creation."""
        exporter = cls.__new__(cls)
        exporter.env = self.env
        exporter.backend = self.backend
        exporter.client = MagicMock()
        return exporter

    def test_export_applies_custom_mapping(self):
        """Custom export mapping should add fields to Shopify payload."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'metafield_note',
            'direction': 'export',
            'active': True,
        })

        from ..sync.product_sync import ProductExporter
        exporter = self._make_exporter(ProductExporter)
        exporter.client.execute_mutation.return_value = {
            'product': {'id': 'gid://shopify/Product/500'},
        }

        exporter._update_product(self.binding, self.product)

        # Check that the mutation was called with our custom mapping
        call_args = exporter.client.execute_mutation.call_args_list[0]
        variables = call_args[0][1]  # Second positional arg
        product_input = variables['input']
        self.assertEqual(
            product_input.get('metafield_note'),
            'Internal note',
            "Export mapping should inject custom field into Shopify payload",
        )

    def test_export_mapping_reads_dotted_odoo_field(self):
        """Dotted Odoo field path should traverse relational fields."""
        # Ensure product has a category with a known name
        categ = self.env['product.category'].create({'name': 'Test Export Category'})
        self.product.categ_id = categ

        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'categ_id.name',
            'shopify_field': 'customProductType',
            'direction': 'export',
            'active': True,
        })

        from ..sync.product_sync import ProductExporter
        exporter = self._make_exporter(ProductExporter)
        exporter.client.execute_mutation.return_value = {
            'product': {'id': 'gid://shopify/Product/500'},
        }

        exporter._update_product(self.binding, self.product)

        call_args = exporter.client.execute_mutation.call_args_list[0]
        variables = call_args[0][1]
        product_input = variables['input']
        self.assertEqual(
            product_input.get('customProductType'),
            'Test Export Category',
            "Dotted Odoo field should be resolved and exported",
        )

    def test_export_mapping_respects_direction(self):
        """Import-only mappings should not apply during export."""
        self.env['shopify.field.mapping'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'odoo_field': 'description_purchase',
            'shopify_field': 'importOnlyField',
            'direction': 'import',
            'active': True,
        })

        from ..sync.product_sync import ProductExporter
        exporter = self._make_exporter(ProductExporter)
        exporter.client.execute_mutation.return_value = {
            'product': {'id': 'gid://shopify/Product/500'},
        }

        exporter._update_product(self.binding, self.product)

        call_args = exporter.client.execute_mutation.call_args_list[0]
        variables = call_args[0][1]
        product_input = variables['input']
        self.assertNotIn(
            'importOnlyField',
            product_input,
            "Import-only mapping should not appear in export payload",
        )
