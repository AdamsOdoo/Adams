import uuid

from odoo.tests.common import TransactionCase


class TestShopifyConnectorLocation(TransactionCase):
    """F-4 permanent seam: `shopify.connector.location._resolve_odoo_location`.

    Core owns no mapping concept and no Odoo-location storage on this model
    itself -- the base implementation must always fail closed (`False`),
    performing no inventory-model lookup and introducing no core dependency
    on inventory. The inventory-owned override is tested in
    `shopify_connector_inventory/tests/test_location_mapping.py`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Loc Seam Test',
            'shop_domain': 'loc-seam-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        cls.Location = cls.env['shopify.connector.location']

    def test_base_seam_returns_false_for_unknown_gid(self):
        result = self.Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/999',
        )
        self.assertFalse(result)

    def test_base_seam_returns_false_even_with_matching_cache_entry(self):
        # The core cache entry (Shopify identity only) existing at all must
        # never be conflated with an Odoo-location mapping -- core has none.
        self.Location.sudo().create({
            'store_id': self.store.id,
            'shopify_location_gid': 'gid://shopify/Location/1',
            'name': 'Warehouse', 'shopify_location_active': True,
        })
        result = self.Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/1',
        )
        self.assertFalse(result)

    def test_base_seam_returns_false_for_empty_gid(self):
        self.assertFalse(self.Location._resolve_odoo_location(self.store, False))
        self.assertFalse(self.Location._resolve_odoo_location(self.store, ''))

    def test_base_seam_has_no_inventory_model_dependency(self):
        # Core must be installable/usable with no inventory addon present:
        # the base method must not reference the inventory-owned mapping
        # model at all. Verified at the source level (AST-free substring
        # check is sufficient here since the base implementation is a
        # single, trivial `return False`).
        import ast
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[1]
            / 'models' / 'shopify_connector_location.py'
        ).read_text('utf-8')
        tree = ast.parse(source)
        method = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_resolve_odoo_location'
        )
        calls = {
            node.func.attr for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(calls & {'search', 'browse', 'search_count'})
