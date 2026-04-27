# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for cursor-based pagination logic.
"""
from .common import SimulatorTestCase
from ..handlers.base_handler import (
    encode_cursor,
    decode_cursor,
    paginate_records,
    build_response,
    build_error_response,
    build_mutation_response,
)


class TestCursorEncoding(SimulatorTestCase):
    """Test cursor encode/decode roundtrip."""

    def test_roundtrip(self):
        """Encoding then decoding should return the original offset."""
        for offset in [0, 1, 49, 100, 9999]:
            cursor = encode_cursor(offset)
            self.assertIsInstance(cursor, str)
            decoded = decode_cursor(cursor)
            self.assertEqual(decoded, offset)

    def test_invalid_cursor_returns_zero(self):
        """Invalid cursor should decode to 0."""
        self.assertEqual(decode_cursor('not-a-cursor'), 0)
        self.assertEqual(decode_cursor(''), 0)

    def test_cursors_are_opaque_strings(self):
        """Cursors should be base64-encoded strings."""
        cursor = encode_cursor(5)
        self.assertIsInstance(cursor, str)
        # Should be valid base64
        import base64
        base64.b64decode(cursor)  # Should not raise


class TestPaginateRecords(SimulatorTestCase):
    """Test paginate_records with Odoo recordsets."""

    def _create_products(self, count):
        """Seed N products and return them in ID order."""
        for i in range(count):
            self._seed_product(f'Page Product {i}')
        return self.env['sim.shopify.product'].search(
            [('config_id', '=', self.sim_config.id)],
            order='id asc',
        )

    def test_single_page(self):
        """All records fit in one page."""
        records = self._create_products(3)
        result = paginate_records(records, first=10)
        self.assertEqual(len(result['edges']), 3)
        self.assertFalse(result['pageInfo']['hasNextPage'])

    def test_first_page(self):
        """First page of multi-page result."""
        records = self._create_products(5)
        result = paginate_records(records, first=2)
        self.assertEqual(len(result['edges']), 2)
        self.assertTrue(result['pageInfo']['hasNextPage'])
        self.assertIsNotNone(result['pageInfo']['endCursor'])

    def test_second_page_via_after(self):
        """Second page using cursor from first page."""
        records = self._create_products(5)
        page1 = paginate_records(records, first=2)
        cursor = page1['pageInfo']['endCursor']
        page2 = paginate_records(records, first=2, after=cursor)
        self.assertEqual(len(page2['edges']), 2)
        # IDs should not overlap
        ids1 = {e['node']['id'] for e in page1['edges']}
        ids2 = {e['node']['id'] for e in page2['edges']}
        self.assertTrue(ids1.isdisjoint(ids2))

    def test_last_page(self):
        """Last page should have hasNextPage=False."""
        records = self._create_products(5)
        page1 = paginate_records(records, first=3)
        cursor = page1['pageInfo']['endCursor']
        page2 = paginate_records(records, first=3, after=cursor)
        self.assertEqual(len(page2['edges']), 2)
        self.assertFalse(page2['pageInfo']['hasNextPage'])

    def test_empty_recordset(self):
        """Empty recordset should return empty edges."""
        records = self.env['sim.shopify.product'].browse()
        result = paginate_records(records, first=10)
        self.assertEqual(result['edges'], [])
        self.assertFalse(result['pageInfo']['hasNextPage'])
        self.assertIsNone(result['pageInfo']['endCursor'])

    def test_exact_page_boundary(self):
        """When total equals first, hasNextPage should be False."""
        records = self._create_products(5)
        result = paginate_records(records, first=5)
        self.assertEqual(len(result['edges']), 5)
        self.assertFalse(result['pageInfo']['hasNextPage'])

    def test_full_scan_collects_all(self):
        """Paginating through all pages should yield all records."""
        records = self._create_products(7)
        all_ids = set()
        cursor = None
        pages = 0
        while True:
            result = paginate_records(records, first=3, after=cursor)
            for edge in result['edges']:
                all_ids.add(edge['node']['id'])
            pages += 1
            if not result['pageInfo']['hasNextPage']:
                break
            cursor = result['pageInfo']['endCursor']
        self.assertEqual(len(all_ids), 7)
        self.assertEqual(pages, 3)  # 3+3+1


class TestResponseBuilders(SimulatorTestCase):
    """Test response envelope builders."""

    def test_build_response(self):
        """Should create proper Shopify response envelope."""
        resp = build_response({'shop': {'name': 'Test'}}, {'cost': {}})
        self.assertIn('data', resp)
        self.assertIn('extensions', resp)
        self.assertNotIn('errors', resp)

    def test_build_response_with_errors(self):
        """Should include errors when provided."""
        resp = build_response(None, {'cost': {}}, errors=[{'message': 'oops'}])
        self.assertIn('errors', resp)
        self.assertEqual(resp['errors'][0]['message'], 'oops')

    def test_build_error_response(self):
        """Should create error-only response."""
        resp = build_error_response('Something failed')
        self.assertIn('errors', resp)
        self.assertEqual(resp['errors'][0]['message'], 'Something failed')
        self.assertNotIn('data', resp)

    def test_build_mutation_response(self):
        """Should create mutation response with userErrors."""
        resp = build_mutation_response('productUpdate', {'product': {'id': '1'}})
        self.assertIn('productUpdate', resp)
        self.assertEqual(resp['productUpdate']['userErrors'], [])
        self.assertEqual(resp['productUpdate']['product']['id'], '1')

    def test_build_mutation_response_with_errors(self):
        """Should include userErrors when provided."""
        resp = build_mutation_response(
            'productUpdate',
            {'product': None},
            user_errors=[{'field': ['id'], 'message': 'Not found'}],
        )
        self.assertEqual(len(resp['productUpdate']['userErrors']), 1)
