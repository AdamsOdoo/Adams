import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (  # noqa: E501
    MAX_PAGES,
    PAGE_SIZE,
    FulfillmentReadError,
)

# Path from `data` to the connection dict exercised by these tests. The reader
# maps this path to the `foCursor` cursor variable via `_cursor_var_for`.
CONNECTION_PATH = 'order.fulfillmentOrders'


def _fo(index):
    """A minimal FulfillmentOrder node (only the id matters to pagination)."""
    return {'id': 'gid://shopify/FulfillmentOrder/%d' % index}


def _page(nodes, has_next_page, end_cursor=None):
    """A `_read_data` return shaped as {'order': {'fulfillmentOrders': {...}}}."""
    return {
        'order': {
            'fulfillmentOrders': {
                'pageInfo': {
                    'hasNextPage': has_next_page,
                    'endCursor': end_cursor,
                },
                'nodes': nodes,
            },
        },
    }


class TestFulfillmentReaderPagination(TransactionCase):
    """Cursor-pagination fail-closed contract (reader §11.4). `_paginate`
    walks pageInfo.hasNextPage/endCursor to completion and returns the flat
    node list; a duplicate node id, a repeated or dropped endCursor, and
    exceeding the page cap before hasNextPage=False each fail closed with a
    FulfillmentReadError — a partial page set never proves completeness."""

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

    def _paginate(self):
        return self.Service._paginate(
            self.store,
            'query',
            {'orderId': 'gid://shopify/Order/1'},
            CONNECTION_PATH,
        )

    # ------------------------------------------------------------------
    # Constants
    # ------------------------------------------------------------------

    def test_pagination_constants(self):
        self.assertEqual(PAGE_SIZE, 50)
        self.assertEqual(MAX_PAGES, 100)

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_single_complete_page_returns_its_nodes(self):
        pages = [_page([_fo(1), _fo(2)], has_next_page=False)]
        with patch.object(
            type(self.Service), '_read_data', side_effect=pages,
        ) as mock_read:
            nodes = self._paginate()
        self.assertEqual(
            [n['id'] for n in nodes],
            ['gid://shopify/FulfillmentOrder/1',
             'gid://shopify/FulfillmentOrder/2'],
        )
        # A single complete page is read exactly once.
        self.assertEqual(mock_read.call_count, 1)

    def test_paginates_to_completion_across_multiple_pages(self):
        pages = [
            _page([_fo(1), _fo(2)], has_next_page=True, end_cursor='c1'),
            _page([_fo(3)], has_next_page=False),
        ]
        with patch.object(
            type(self.Service), '_read_data', side_effect=pages,
        ) as mock_read:
            nodes = self._paginate()
        self.assertEqual(
            [n['id'] for n in nodes],
            ['gid://shopify/FulfillmentOrder/1',
             'gid://shopify/FulfillmentOrder/2',
             'gid://shopify/FulfillmentOrder/3'],
        )
        # Exactly two reads: the second page's hasNextPage=False stops the walk.
        self.assertEqual(mock_read.call_count, 2)

    # ------------------------------------------------------------------
    # Fail-closed paths
    # ------------------------------------------------------------------

    def test_duplicate_node_id_across_pages_fails_closed(self):
        pages = [
            _page([_fo(1)], has_next_page=True, end_cursor='c1'),
            _page([_fo(1)], has_next_page=False),  # id repeats across pages
        ]
        with patch.object(
            type(self.Service), '_read_data', side_effect=pages,
        ):
            with self.assertRaises(FulfillmentReadError) as ctx:
                self._paginate()
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_repeated_end_cursor_fails_closed(self):
        pages = [
            _page([_fo(1)], has_next_page=True, end_cursor='c1'),
            # Distinct node id, but the same endCursor -> non-advancing cursor.
            _page([_fo(2)], has_next_page=True, end_cursor='c1'),
        ]
        with patch.object(
            type(self.Service), '_read_data', side_effect=pages,
        ):
            with self.assertRaises(FulfillmentReadError) as ctx:
                self._paginate()
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_dropped_end_cursor_fails_closed(self):
        # hasNextPage=True but no endCursor: the walk cannot advance safely.
        pages = [_page([_fo(1)], has_next_page=True, end_cursor=None)]
        with patch.object(
            type(self.Service), '_read_data', side_effect=pages,
        ):
            with self.assertRaises(FulfillmentReadError) as ctx:
                self._paginate()
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')

    def test_page_cap_reached_before_completion_fails_closed(self):
        # An endless connection: every page advertises another page with a
        # fresh (unique) cursor and a fresh node id, so neither the duplicate
        # guard nor the cursor guard trips before the fail-closed page cap.
        state = {'n': 0}

        def endless(*_args, **_kwargs):
            state['n'] += 1
            index = state['n']
            return _page(
                [_fo(index)],
                has_next_page=True,
                end_cursor='c%d' % index,
            )

        with patch.object(
            type(self.Service), '_read_data', side_effect=endless,
        ) as mock_read:
            with self.assertRaises(FulfillmentReadError) as ctx:
                self._paginate()
        self.assertEqual(ctx.exception.error_class, 'data_shape_schema_mismatch')
        # The cap bounds the number of reads: a partial set never proves
        # completion or absence.
        self.assertEqual(mock_read.call_count, MAX_PAGES)
