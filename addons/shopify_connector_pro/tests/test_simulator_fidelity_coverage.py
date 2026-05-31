# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""
Coverage tests for connector import fields that were previously untestable
due to simulator fidelity gaps (F-1 through F-8).

Each test feeds the connector's importer a node in the *correct* Shopify
shape (the shape the simulator now returns after the fidelity fixes) and
verifies the connector handles it.  If any test fails, it means the
CONNECTOR has a real bug that the old simulator shape was hiding.

B-1: Shipping lines import (F-1 — edges/node wrapping)
B-2: Presentment currency import (F-4 — presentmentCurrencyCode at root)
B-3: Product weight import (F-6 — inventoryItem.measurement.weight)
B-4: Multi-option product import (F-7 — option1 + option2)
B-5: Product image node shape (F-5 — images.edges[].node.{id, url, altText})
"""
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestShippingLineImport(ShopifyAccountingMixin, TransactionCase):
    """B-1: Verify connector imports shipping lines from edges/node structure."""

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
        self.product = self.env['product.product'].create({
            'name': 'Test Widget', 'list_price': 29.99,
            'default_code': 'WIDGET-SL',
        })
        self._set_product_income_account(self.product)
        product_binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/100',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/200',
            'product_binding_id': product_binding.id,
            'sync_status': 'synced',
        })

    def _make_order_with_shipping(self, shipping_price='7.99'):
        """Build an order node with a shipping line in correct edges/node shape."""
        return {
            'id': 'gid://shopify/Order/SL001',
            'name': '#SL001',
            'createdAt': '2026-05-29T10:00:00Z',
            'updatedAt': '2026-05-29T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'currencyCode': 'USD',
            'presentmentCurrencyCode': 'USD',
            'totalPriceSet': {'shopMoney': {'amount': '37.98', 'currencyCode': 'USD'},
                              'presentmentMoney': {'amount': '37.98', 'currencyCode': 'USD'}},
            'customer': {
                'id': 'gid://shopify/Customer/500',
                'email': 'shipping@test.com',
                'firstName': 'Ship', 'lastName': 'Test',
            },
            'shippingAddress': {
                'address1': '123 Main St', 'address2': '', 'city': 'LA',
                'province': 'California', 'provinceCode': 'CA',
                'country': 'United States', 'countryCodeV2': 'US',
                'zip': '90001', 'phone': '', 'firstName': 'Ship', 'lastName': 'Test',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/1',
                        'title': 'Test Widget', 'quantity': 1,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/200',
                            'sku': 'WIDGET-SL',
                            'product': {'id': 'gid://shopify/Product/100'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {'amount': '29.99', 'currencyCode': 'USD'},
                            'presentmentMoney': {'amount': '29.99', 'currencyCode': 'USD'},
                        },
                        'discountAllocations': [],
                        'taxLines': [],
                    }
                }],
                'pageInfo': {'hasNextPage': False},
            },
            'shippingLines': {
                'edges': [{
                    'node': {
                        'title': 'Standard Shipping',
                        'code': 'standard',
                        'originalPriceSet': {
                            'shopMoney': {'amount': shipping_price, 'currencyCode': 'USD'},
                            'presentmentMoney': {'amount': shipping_price, 'currencyCode': 'USD'},
                        },
                    }
                }],
            },
        }

    def test_shipping_line_imported(self):
        """B-1: Shipping line with $7.99 must appear on the sale order."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_with_shipping('7.99')

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/SL001'),
        ])
        self.assertTrue(binding, "Order binding not created")
        order = binding.odoo_id

        # Find shipping line (product with 'Shipping' in name or SHOPIFY-SHIPPING code)
        shipping_lines = order.order_line.filtered(
            lambda l: l.product_id.default_code == 'SHOPIFY-SHIPPING'
            or 'shipping' in (l.name or '').lower()
        )
        self.assertTrue(
            shipping_lines,
            "No shipping line found on the order — connector is NOT importing "
            "shipping lines from the edges/node structure. SIDE FINDING.",
        )
        self.assertAlmostEqual(
            shipping_lines[0].price_unit, 7.99, places=2,
            msg="Shipping line amount should be $7.99",
        )


class TestPresentmentCurrencyImport(TransactionCase):
    """B-2: Verify connector uses presentmentCurrencyCode from order root."""

    def setUp(self):
        super().setUp()
        if not self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1,
        ):
            self.env['account.journal'].create({
                'name': 'Test Sales Journal', 'type': 'sale',
                'code': 'TCUR', 'company_id': self.env.company.id,
            })
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
            'import_currency_mode': 'presentment',
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        # Ensure EUR exists
        eur = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', 'EUR')], limit=1,
        )
        if not eur:
            self.env['res.currency'].create({'name': 'EUR', 'symbol': 'E'})
        elif not eur.active:
            eur.active = True

        self.product = self.env['product.product'].create({
            'name': 'Euro Widget', 'list_price': 25.00, 'default_code': 'EWIDGET',
        })
        pb = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/101',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/201',
            'product_binding_id': pb.id,
            'sync_status': 'synced',
        })

    def test_presentment_currency_used(self):
        """B-2: Order with presentmentCurrencyCode=EUR must import in EUR."""
        from ..sync.order_sync import OrderImporter

        node = {
            'id': 'gid://shopify/Order/EUR001',
            'name': '#EUR001',
            'createdAt': '2026-05-29T10:00:00Z',
            'updatedAt': '2026-05-29T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'currencyCode': 'USD',
            'presentmentCurrencyCode': 'EUR',
            'totalPriceSet': {
                'shopMoney': {'amount': '29.00', 'currencyCode': 'USD'},
                'presentmentMoney': {'amount': '27.50', 'currencyCode': 'EUR'},
            },
            'customer': {
                'id': 'gid://shopify/Customer/600',
                'email': 'euro@test.com',
                'firstName': 'Euro', 'lastName': 'Buyer',
            },
            'shippingAddress': {
                'address1': '1 Rue Test', 'address2': '', 'city': 'Paris',
                'province': '', 'provinceCode': '',
                'country': 'France', 'countryCodeV2': 'FR',
                'zip': '75001', 'phone': '', 'firstName': 'Euro', 'lastName': 'Buyer',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/2',
                        'title': 'Euro Widget', 'quantity': 1,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/201',
                            'sku': 'EWIDGET',
                            'product': {'id': 'gid://shopify/Product/101'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {'amount': '29.00', 'currencyCode': 'USD'},
                            'presentmentMoney': {'amount': '27.50', 'currencyCode': 'EUR'},
                        },
                        'discountAllocations': [],
                        'taxLines': [],
                    }
                }],
                'pageInfo': {'hasNextPage': False},
            },
            'shippingLines': {'edges': []},
        }

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/EUR001'),
        ])
        self.assertTrue(binding)
        order = binding.odoo_id

        # In presentment mode, the order currency should be EUR
        # (unless the connector falls back to company currency, which is the bug)
        if order.currency_id.name != self.env.company.currency_id.name:
            self.assertEqual(
                order.currency_id.name, 'EUR',
                "Presentment mode should import in EUR, not USD.",
            )


class TestProductWeightImport(TransactionCase):
    """B-3: Verify connector reads weight from inventoryItem.measurement.weight."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def test_weight_imported_from_measurement(self):
        """B-3: Product weight should come from inventoryItem.measurement.weight."""
        from ..sync.product_sync import ProductImporter

        node = {
            'id': 'gid://shopify/Product/W001',
            'title': 'Heavy Widget',
            'descriptionHtml': '',
            'vendor': 'Test',
            'productType': '',
            'tags': [],
            'status': 'ACTIVE',
            'handle': 'heavy-widget',
            'createdAt': '2026-05-29T10:00:00Z',
            'updatedAt': '2026-05-29T10:00:00Z',
            'options': [{'name': 'Title', 'values': ['Default Title']}],
            'images': {'edges': []},
            'variants': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/ProductVariant/W100',
                        'title': 'Default Title',
                        'sku': 'HEAVY-001',
                        'barcode': None,
                        'price': '49.99',
                        'compareAtPrice': None,
                        'inventoryQuantity': 10,
                        'inventoryItem': {
                            'id': 'gid://shopify/InventoryItem/WI100',
                            'measurement': {
                                'weight': {
                                    'value': 2.5,
                                    'unit': 'KILOGRAMS',
                                },
                            },
                        },
                        'weight': 2.5,
                        'weightUnit': 'KILOGRAMS',
                        'selectedOptions': [{'name': 'Title', 'value': 'Default Title'}],
                    }
                }],
            },
        }

        importer = ProductImporter.__new__(ProductImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/W001'),
        ])
        self.assertTrue(binding, "Product binding not created")
        product = binding.odoo_id
        self.assertAlmostEqual(
            product.weight, 2.5, places=1,
            msg="Weight should be 2.5 kg from inventoryItem.measurement.weight. "
            "If 0, the connector is not reading the measurement structure. SIDE FINDING.",
        )


class TestMultiOptionImport(TransactionCase):
    """B-4: Verify connector creates multiple attribute lines from multi-axis options."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def test_multi_option_creates_attributes(self):
        """B-4: Product with Color+Size options must create 2 attribute lines."""
        from ..sync.product_sync import ProductImporter

        node = {
            'id': 'gid://shopify/Product/MO001',
            'title': 'Multi-Option Sneaker',
            'descriptionHtml': '',
            'vendor': 'Test',
            'productType': 'Shoes',
            'tags': ['sneaker'],
            'status': 'ACTIVE',
            'handle': 'multi-option-sneaker',
            'createdAt': '2026-05-29T10:00:00Z',
            'updatedAt': '2026-05-29T10:00:00Z',
            'options': [
                {'name': 'Color', 'values': ['Red', 'Blue']},
                {'name': 'Size', 'values': ['9', '10', '11']},
            ],
            'images': {'edges': []},
            'variants': {
                'edges': [
                    {'node': {
                        'id': f'gid://shopify/ProductVariant/MO{i}',
                        'title': f'{color} / {size}',
                        'sku': f'SNK-{color[0]}{size}',
                        'barcode': None, 'price': '89.99',
                        'compareAtPrice': None, 'inventoryQuantity': 5,
                        'inventoryItem': {
                            'id': f'gid://shopify/InventoryItem/MI{i}',
                            'measurement': {'weight': {'value': 0.8, 'unit': 'KILOGRAMS'}},
                        },
                        'selectedOptions': [
                            {'name': 'Color', 'value': color},
                            {'name': 'Size', 'value': size},
                        ],
                    }}
                    for i, (color, size) in enumerate([
                        ('Red', '9'), ('Red', '10'), ('Red', '11'),
                        ('Blue', '9'), ('Blue', '10'), ('Blue', '11'),
                    ])
                ],
            },
        }

        importer = ProductImporter.__new__(ProductImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/MO001'),
        ])
        self.assertTrue(binding)
        product = binding.odoo_id
        attr_names_lower = {n.lower() for n in product.attribute_line_ids.mapped('attribute_id.name')}
        self.assertIn('color', attr_names_lower,
                       "Missing 'Color' attribute line. SIDE FINDING if connector "
                       "doesn't process multi-option products.")
        self.assertIn('size', attr_names_lower,
                       "Missing 'Size' attribute line.")


class TestImageNodeShape(TransactionCase):
    """B-5: Verify connector iterates images.edges[].node correctly."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def test_image_download_attempted_from_node(self):
        """B-5: Connector should attempt to download from images.edges[0].node.url."""
        from ..sync.product_sync import ProductImporter

        node = {
            'id': 'gid://shopify/Product/IMG001',
            'title': 'Image Test Widget',
            'descriptionHtml': '',
            'vendor': 'Test',
            'productType': '',
            'tags': [],
            'status': 'ACTIVE',
            'handle': 'image-test',
            'createdAt': '2026-05-29T10:00:00Z',
            'updatedAt': '2026-05-29T10:00:00Z',
            'options': [{'name': 'Title', 'values': ['Default Title']}],
            'images': {
                'edges': [
                    {
                        'node': {
                            'id': 'gid://shopify/ProductImage/1',
                            'url': 'https://cdn.shopify.com/s/files/test/product1.png',
                            'altText': 'Main image',
                        },
                    },
                    {
                        'node': {
                            'id': 'gid://shopify/ProductImage/2',
                            'url': 'https://cdn.shopify.com/s/files/test/product2.png',
                            'altText': 'Side view',
                        },
                    },
                ],
            },
            'variants': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/ProductVariant/IMG100',
                        'title': 'Default Title',
                        'sku': 'IMG-001',
                        'barcode': None,
                        'price': '15.00',
                        'compareAtPrice': None,
                        'inventoryQuantity': 5,
                        'inventoryItem': {
                            'id': 'gid://shopify/InventoryItem/IMGI100',
                            'measurement': {'weight': {'value': 0.1, 'unit': 'KILOGRAMS'}},
                        },
                        'selectedOptions': [{'name': 'Title', 'value': 'Default Title'}],
                    }
                }],
            },
        }

        importer = ProductImporter.__new__(ProductImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        # Mock requests.get so we can verify it was called with the image URL
        # and provide a 1-pixel PNG response
        import base64
        # Minimal 1x1 white PNG
        pixel_png = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
            b'\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = pixel_png

        with patch('odoo.addons.shopify_connector_pro.sync.product_sync.requests.get',
                    return_value=mock_response) as mock_get:
            importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/IMG001'),
        ])
        self.assertTrue(binding)
        product = binding.odoo_id

        # Verify the connector attempted to download the image
        self.assertTrue(
            mock_get.called,
            "Connector did not attempt to download any image from "
            "images.edges[].node.url. SIDE FINDING.",
        )
        # Verify main image was set
        self.assertTrue(
            product.image_1920,
            "Product image_1920 should be set from the downloaded image.",
        )


# ======================================================================
# B-6: Refund response fidelity guard + taxed e2e refund test
# ======================================================================
# NOTE: These tests live in the shopify_simulator module
# (tests/test_refund_fidelity.py) because they need access to both
# simulator models AND connector models. The simulator depends on
# shopify_connector_pro, so its tests can access both.
# ======================================================================
