import ast
import uuid
from pathlib import Path
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (  # noqa: E501
    FulfillmentReadError,
)


def _fo(location_gid, name='L'):
    """A FulfillmentOrder node carrying only its assigned location."""
    location = None if location_gid is None else {'id': location_gid, 'name': name}
    return {'assignedLocation': {'location': location}}


class TestFulfillmentLocationResolution(TransactionCase):
    """Location resolution (Q3) through the core `shopify.connector.location`
    cache only. All matched FOs must share exactly one assigned location that
    is present in the cache; a null location, two distinct locations, or a
    location absent from the cache each fail closed with `ambiguous_match`. The
    resolver never reads `shopify.connector.location.mapping` (inventory-domain
    model, not a fulfillment dependency)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'fulfillment_domain_enabled': True,
        })
        cls.Location = cls.env['shopify.connector.location'].sudo()
        # Two locations present in the core cache for this store.
        cls.Location.create({
            'store_id': cls.store.id,
            'shopify_location_gid': 'gid://shopify/Location/1',
            'name': 'Warehouse 1',
            'shopify_location_active': True,
        })
        cls.Location.create({
            'store_id': cls.store.id,
            'shopify_location_gid': 'gid://shopify/Location/2',
            'name': 'Warehouse 2',
            'shopify_location_active': True,
        })

    # ------------------------------------------------------------------
    # _resolve_single_location
    # ------------------------------------------------------------------

    def test_resolves_when_all_fos_share_one_cached_location(self):
        fos = [
            _fo('gid://shopify/Location/1'),
            _fo('gid://shopify/Location/1'),
        ]
        gid = self.Service._resolve_single_location(self.store, fos)
        self.assertEqual(gid, 'gid://shopify/Location/1')

    def test_null_assigned_location_is_ambiguous(self):
        # `assignedLocation.location` can be null (deleted/altered) -> fail closed.
        fos = [_fo(None)]
        with self.assertRaises(FulfillmentReadError) as ctx:
            self.Service._resolve_single_location(self.store, fos)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')

    def test_missing_assigned_location_key_is_ambiguous(self):
        fos = [{}]
        with self.assertRaises(FulfillmentReadError) as ctx:
            self.Service._resolve_single_location(self.store, fos)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')

    def test_two_distinct_locations_is_ambiguous(self):
        # Both locations are cached; the failure is spanning >1 location,
        # not a cache miss.
        fos = [
            _fo('gid://shopify/Location/1'),
            _fo('gid://shopify/Location/2'),
        ]
        with self.assertRaises(FulfillmentReadError) as ctx:
            self.Service._resolve_single_location(self.store, fos)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')

    def test_location_absent_from_cache_fails_closed(self):
        # A single shared location that is NOT in the core cache -> fail closed.
        fos = [
            _fo('gid://shopify/Location/999'),
            _fo('gid://shopify/Location/999'),
        ]
        with self.assertRaises(FulfillmentReadError) as ctx:
            self.Service._resolve_single_location(self.store, fos)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')

    def test_resolver_never_references_location_mapping(self):
        # The location.mapping model belongs to the inventory domain and is not
        # a dependency of this module; the resolver must resolve through the
        # core `shopify.connector.location` cache only. Assert this at the
        # source level so it holds even though the mapping model is absent from
        # this module's registry.
        source = (
            Path(__file__).resolve().parents[1]
            / 'models' / 'shopify_connector_fulfillment_reader.py'
        ).read_text('utf-8')
        tree = ast.parse(source)
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_resolve_single_location'
        )
        segment = ast.get_source_segment(source, method)
        # Assert on the executable body, not raw text: the docstring
        # deliberately names 'location.mapping' ("Never reads location.mapping"),
        # so a substring check on the source would false-positive. Collect the
        # string literals actually used in code (docstring excluded) and prove
        # the mapping model is never referenced there.
        body = list(method.body)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]  # drop the docstring node
        code_string_literals = {
            node.value
            for stmt in body
            for node in ast.walk(stmt)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn('location.mapping', code_string_literals)
        self.assertIn('shopify.connector.location', code_string_literals)

    # ------------------------------------------------------------------
    # _refresh_location_cache
    # ------------------------------------------------------------------

    def test_refresh_location_cache_creates_then_updates(self):
        # First refresh creates the row.
        with patch.object(
            type(self.Service), '_paginate',
            return_value=[{
                'id': 'gid://shopify/Location/50',
                'name': 'Warehouse A',
                'isActive': True,
            }],
        ):
            self.assertTrue(self.Service._refresh_location_cache(self.store))
        row = self.Location.search([
            ('store_id', '=', self.store.id),
            ('shopify_location_gid', '=', 'gid://shopify/Location/50'),
        ])
        self.assertEqual(len(row), 1)
        self.assertEqual(row.name, 'Warehouse A')
        self.assertTrue(row.shopify_location_active)

        # Second refresh upserts the SAME row (rename + deactivate), never
        # a duplicate.
        with patch.object(
            type(self.Service), '_paginate',
            return_value=[{
                'id': 'gid://shopify/Location/50',
                'name': 'Warehouse A (renamed)',
                'isActive': False,
            }],
        ):
            self.assertTrue(self.Service._refresh_location_cache(self.store))
        rows = self.Location.search([
            ('store_id', '=', self.store.id),
            ('shopify_location_gid', '=', 'gid://shopify/Location/50'),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.name, 'Warehouse A (renamed)')
        self.assertFalse(rows.shopify_location_active)
