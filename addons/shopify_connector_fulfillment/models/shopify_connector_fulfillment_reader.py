import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Cursor-pagination fail-closed contract (packet §11.4). Decision-critical reads
# paginate via pageInfo.hasNextPage/endCursor to completion; a partial page set
# may never prove absence, select a target, prove mapping completeness, or
# authorize a mutation. Hitting the cap before completeness fails closed.
PAGE_SIZE = 50
MAX_PAGES = 100

# Read-only GraphQL documents (queries — never mutations). Fulfillment-order
# reads deliberately carry NO server-side status filter (a status:open filter
# would exclude IN_PROGRESS FOs); status is filtered client-side.
FULFILLMENT_ORDERS_QUERY = (
    'query($orderId: ID!, $foCursor: String) {\n'
    '  order(id: $orderId) {\n'
    '    id\n'
    '    fulfillmentOrders(first: %(page)d, after: $foCursor) {\n'
    '      pageInfo { hasNextPage endCursor }\n'
    '      nodes {\n'
    '        id\n'
    '        status\n'
    '        requestStatus\n'
    '        assignedLocation { location { id name } }\n'
    '        supportedActions { action }\n'
    '      }\n'
    '    }\n'
    '  }\n'
    '}'
) % {'page': PAGE_SIZE}

FULFILLMENT_ORDER_LINES_QUERY = (
    'query($foId: ID!, $lineCursor: String) {\n'
    '  fulfillmentOrder(id: $foId) {\n'
    '    id\n'
    '    lineItems(first: %(page)d, after: $lineCursor) {\n'
    '      pageInfo { hasNextPage endCursor }\n'
    '      nodes {\n'
    '        id\n'
    '        remainingQuantity\n'
    '        lineItem { id }\n'
    '      }\n'
    '    }\n'
    '  }\n'
    '}'
) % {'page': PAGE_SIZE}

ORDER_FULFILLMENTS_QUERY = (
    'query($orderId: ID!) {\n'
    '  order(id: $orderId) {\n'
    '    id\n'
    '    fulfillments(first: 250) {\n'
    '        id\n'
    '        status\n'
    '        displayStatus\n'
    '        trackingInfo { number url company }\n'
    '        fulfillmentLineItems(first: %(page)d) {\n'
    '          pageInfo { hasNextPage endCursor }\n'
    '          nodes { id quantity lineItem { id } }\n'
    '        }\n'
    '    }\n'
    '  }\n'
    '}'
) % {'page': PAGE_SIZE}

LOCATIONS_QUERY = (
    'query($cursor: String) {\n'
    '  locations(first: %(page)d, after: $cursor, includeInactive: true) {\n'
    '    pageInfo { hasNextPage endCursor }\n'
    '    nodes { id name isActive }\n'
    '  }\n'
    '}'
) % {'page': PAGE_SIZE}


class FulfillmentReadError(Exception):
    """A decision-critical fulfillment read could not complete safely.

    Carries a fixed core `error_class`; callers route it to the appropriate
    fail-closed disposition. Never used to prove absence — an incomplete or
    malformed read is inconclusive/ambiguous, never "not present".
    """

    def __init__(self, error_class, message):
        super().__init__(message)
        self.error_class = error_class
        self.message = message


class ShopifyConnectorFulfillmentService(models.AbstractModel):
    """The fulfillment domain service (read/matching/pagination base).

    One responsibility per file: this file owns the read-only Shopify reads,
    cursor pagination, FO-line-item 2-hop matching, and location resolution
    through the core `shopify.connector.location` cache (never
    `shopify.connector.location.mapping`). Admission, the two mutation
    strategies, inbound classification, Mode 2, review, and the scans extend
    this same model in sibling files.
    """

    _name = 'shopify.connector.fulfillment.service'
    _description = 'Shopify Connector Fulfillment Service'

    # ------------------------------------------------------------------
    # Read primitives
    # ------------------------------------------------------------------

    @api.model
    def _read_data(self, job, store, query, variables):
        """Execute a read-only GraphQL query through the core client and return
        its `data` dict. The core client validates the document contains no
        mutation and raises `ShopifyClientError` on transport failure."""
        client = self.env['shopify.connector.api.client']
        with client.execute_business_read(
            job, store, query, variables, purpose='fulfillment',
        ) as result:
            data = (result or {}).get('data')
            if not isinstance(data, dict):
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A fulfillment read returned no data object.',
                )
            return data

    @api.model
    def _paginate(self, job, store, query, variables, connection_path):
        """Cursor-paginate a connection to completion, fail-closed.

        `connection_path` is the dotted path from `data` to the connection dict
        (e.g. 'order.fulfillmentOrders'). Returns the flat list of nodes.
        Detects duplicate node ids and repeated cursors, and fails closed if the
        page cap is reached before `hasNextPage` is False — a partial read is
        never treated as complete.
        """
        cursor_var = self._cursor_var_for(connection_path)
        nodes = []
        seen_ids = set()
        seen_cursors = set()
        cursor = None
        for _page in range(MAX_PAGES):
            page_vars = dict(variables)
            page_vars[cursor_var] = cursor
            data = self._read_data(job, store, query, page_vars)
            connection = self._dig(data, connection_path)
            if not isinstance(connection, dict):
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A paginated read returned a malformed connection.',
                )
            page_nodes = connection.get('nodes')
            page_info = connection.get('pageInfo') or {}
            if not isinstance(page_nodes, list) or not isinstance(page_info, dict):
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A paginated read returned a malformed page.',
                )
            for node in page_nodes:
                node_id = isinstance(node, dict) and node.get('id')
                if node_id:
                    if node_id in seen_ids:
                        raise FulfillmentReadError(
                            'data_shape_schema_mismatch',
                            'A paginated read returned a duplicate node id.',
                        )
                    seen_ids.add(node_id)
                nodes.append(node)
            if not page_info.get('hasNextPage'):
                return nodes
            end_cursor = page_info.get('endCursor')
            if not end_cursor or end_cursor in seen_cursors:
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A paginated read repeated or dropped its cursor.',
                )
            seen_cursors.add(end_cursor)
            cursor = end_cursor
        # Cap reached before completeness: fail closed. Never treat the partial
        # set as complete (no absence proof, no target selection).
        raise FulfillmentReadError(
            'data_shape_schema_mismatch',
            'A paginated read exceeded the fail-closed page cap before '
            'completion; the result is incomplete and cannot prove absence.',
        )

    @api.model
    def _cursor_var_for(self, connection_path):
        if connection_path.endswith('fulfillmentOrders'):
            return 'foCursor'
        if connection_path.endswith('lineItems'):
            return 'lineCursor'
        return 'cursor'

    @api.model
    def _dig(self, data, dotted_path):
        node = data
        for part in dotted_path.split('.'):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return node

    # ------------------------------------------------------------------
    # Fulfillment-order reads (cursor-paginated to completion)
    # ------------------------------------------------------------------

    @api.model
    def _read_fulfillment_orders(self, job, store, order_gid):
        """Return every FulfillmentOrder for an order (cursor-paginated to
        completion), each with its line items (also paginated to completion).
        Client-side selection of OPEN/IN_PROGRESS FOs is left to the caller."""
        fos = self._paginate(
            job, store, FULFILLMENT_ORDERS_QUERY, {'orderId': order_gid},
            'order.fulfillmentOrders',
        )
        result = []
        for fo in fos:
            if not isinstance(fo, dict) or not fo.get('id'):
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A fulfillment order node is malformed.',
                )
            lines = self._paginate(
                job, store, FULFILLMENT_ORDER_LINES_QUERY, {'foId': fo['id']},
                'fulfillmentOrder.lineItems',
            )
            fo = dict(fo)
            fo['line_items'] = lines
            result.append(fo)
        return result

    @api.model
    def _read_order_fulfillments(self, job, store, order_gid):
        """Return every Fulfillment for an order from Shopify's list field.

        Shopify Admin API 2026-07 exposes ``Order.fulfillments`` as a list,
        not a connection: it has no ``nodes``, ``pageInfo`` or ``after``.
        The nested
        fulfillmentLineItems connection is fetched in one page; if any
        fulfillment has more line items than one page, decision-critical
        completeness cannot be proven — fail closed (§11.4)."""
        data = self._read_data(
            job, store, ORDER_FULFILLMENTS_QUERY, {'orderId': order_gid},
        )
        order = data.get('order') if isinstance(data, dict) else None
        fulfillments = order.get('fulfillments') if isinstance(order, dict) else None
        if not isinstance(fulfillments, list):
            raise FulfillmentReadError(
                'data_shape_schema_mismatch',
                'Shopify returned an invalid Order.fulfillments list shape.',
            )
        # The list field accepts only a first-count, not a cursor. Reaching the
        # requested bound cannot prove that another row was not truncated.
        if len(fulfillments) >= 250:
            raise FulfillmentReadError(
                'data_shape_schema_mismatch',
                'An order reached the supported 249-fulfillment read limit; '
                'decision-critical completeness cannot be proven.',
            )
        for node in fulfillments:
            if not isinstance(node, dict) or not node.get('id'):
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'Shopify returned a malformed fulfillment list entry.',
                )
            line_conn = (node or {}).get('fulfillmentLineItems') or {}
            page_info = line_conn.get('pageInfo') or {}
            if page_info.get('hasNextPage'):
                raise FulfillmentReadError(
                    'data_shape_schema_mismatch',
                    'A fulfillment has more line items than a single page; '
                    'decision-critical completeness cannot be proven.',
                )
        return fulfillments

    # ------------------------------------------------------------------
    # FO-line-item 2-hop matching (RA-023)
    # ------------------------------------------------------------------

    @api.model
    def _match_picking_to_fo_lines(self, picking, fos):
        """RA-023 explicit matching. For each done move line on the picking,
        resolve its Shopify line-item GID (via sale_line_id.shopify_line_item_gid)
        to a FulfillmentOrderLineItem GID through the 2-hop
        order-LineItem-GID -> FO-line lineItem.id -> FO-line id.

        Theme C correction: every resolved move line's quantity is first
        converted through Odoo's UoM API into the resolved sale line's own
        UoM (the unit Shopify's `remainingQuantity` is expressed against),
        then AGGREGATED per FulfillmentOrder line — never compared
        individually — before the single aggregate is capped at that line's
        `remainingQuantity`. A lot/serial-split shipment whose individual
        move lines each pass alone but jointly exceed the remaining quantity
        is rejected exactly like a single over-large line would be.

        Returns (line_inputs, diagnostics) where line_inputs is a dict keyed
        by FulfillmentOrder GID -> list of exactly one {id, quantity} entry
        per matched FO line. Never fulfils by guess: an unresolved line
        raises FulfillmentReadError('mapping_missing') and an
        over-remaining aggregate raises FulfillmentReadError('ambiguous_match').
        """
        # Build the reverse index: order LineItem GID -> [(fo_gid, fo_line_id,
        # remaining)]. Skip null-GID FO lines.
        index = {}
        for fo in fos:
            for fo_line in fo.get('line_items') or []:
                if not isinstance(fo_line, dict):
                    continue
                line_item = fo_line.get('lineItem') or {}
                order_line_gid = line_item.get('id')
                fo_line_id = fo_line.get('id')
                if not order_line_gid or not fo_line_id:
                    # Skip null-GID FO lines (they cannot be matched safely).
                    continue
                index.setdefault(order_line_gid, []).append({
                    'fo_gid': fo['id'],
                    'fo_line_id': fo_line_id,
                    'remaining': fo_line.get('remainingQuantity'),
                })

        # Aggregate every done move line's UoM-normalized quantity by the
        # single FulfillmentOrder line it resolves to, BEFORE any
        # remainingQuantity comparison (Theme C).
        aggregated = {}
        diagnostics = {'matched_lines': 0}
        for move_line in self._picking_done_move_lines(picking):
            sale_line = move_line.move_id.sale_line_id
            order_line_gid = sale_line.shopify_line_item_gid if sale_line else False
            quantity = self._fo_line_uom_quantity(move_line, sale_line)
            if quantity <= 0:
                continue
            if not order_line_gid:
                raise FulfillmentReadError(
                    'mapping_missing',
                    'A shipped move line has no Shopify line-item GID; the '
                    'fulfillment cannot be created by guess (RA-023).',
                )
            candidates = index.get(order_line_gid)
            if not candidates:
                raise FulfillmentReadError(
                    'mapping_missing',
                    'No FulfillmentOrder line matches Shopify line item %s.'
                    % order_line_gid,
                )
            if len(candidates) > 1:
                raise FulfillmentReadError(
                    'ambiguous_match',
                    'Shopify line item %s matches more than one open '
                    'FulfillmentOrder line.' % order_line_gid,
                )
            candidate = candidates[0]
            fo_line_id = candidate['fo_line_id']
            entry = aggregated.setdefault(fo_line_id, {
                'fo_gid': candidate['fo_gid'],
                'remaining': candidate['remaining'],
                'quantity': 0,
            })
            entry['quantity'] += quantity
            diagnostics['matched_lines'] += 1

        line_inputs = {}
        for fo_line_id, entry in aggregated.items():
            remaining = entry['remaining']
            if not isinstance(remaining, int) or entry['quantity'] > remaining:
                raise FulfillmentReadError(
                    'ambiguous_match',
                    'Aggregate shipped quantity %d exceeds the remaining '
                    'fulfillable quantity for FulfillmentOrder line %s.'
                    % (entry['quantity'], fo_line_id),
                )
            line_inputs.setdefault(entry['fo_gid'], []).append({
                'id': fo_line_id,
                'quantity': entry['quantity'],
            })
        if not line_inputs:
            raise FulfillmentReadError(
                'mapping_missing',
                'No shipped line resolved to an open FulfillmentOrder line.',
            )
        return line_inputs, diagnostics

    @api.model
    def _fo_line_uom_quantity(self, move_line, sale_line):
        """The move line's `quantity` (Odoo 19: never qty_done/quantity_done),
        UoM-converted to the resolved sale line's own UoM — the unit Shopify's
        `remainingQuantity` is expressed against — via the standard Odoo UoM
        conversion API. Falls back to the raw quantity when no sale line or
        no UoM is resolvable (an unmapped line already fails closed
        separately on the caller side)."""
        quantity = move_line.quantity or 0.0
        move_uom = move_line.product_uom_id
        target_uom = sale_line.product_uom_id if sale_line else False
        if move_uom and target_uom and move_uom != target_uom:
            quantity = move_uom._compute_quantity(quantity, target_uom)
        return int(round(quantity))

    @api.model
    def _picking_done_move_lines(self, picking):
        """Done move lines with a positive quantity (Odoo 19:
        stock.move.line.quantity — never qty_done/quantity_done)."""
        return picking.move_line_ids.filtered(
            lambda ml: ml.quantity and ml.quantity > 0.0
        )

    # ------------------------------------------------------------------
    # Location resolution (Q3): core shopify.connector.location cache only.
    # ------------------------------------------------------------------

    @api.model
    def _resolve_single_location(self, store, fos):
        """All matched FOs must share exactly one assignedLocation.location.id,
        resolvable in the core location cache. `assignedLocation.location` can be
        null (deleted/altered) -> fail closed. Never reads location.mapping."""
        location_gids = set()
        for fo in fos:
            assigned = (fo.get('assignedLocation') or {}).get('location') or {}
            gid = assigned.get('id')
            if not gid:
                raise FulfillmentReadError(
                    'ambiguous_match',
                    'A FulfillmentOrder has no resolvable assigned location.',
                )
            location_gids.add(gid)
        if len(location_gids) != 1:
            raise FulfillmentReadError(
                'ambiguous_match',
                'The matched FulfillmentOrders span more than one Shopify '
                'location.',
            )
        gid = next(iter(location_gids))
        cache = self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', store.id),
            ('shopify_location_gid', '=', gid),
        ], limit=1)
        if not cache:
            raise FulfillmentReadError(
                'ambiguous_match',
                'Shopify location %s is not present in the core location '
                'cache for this store.' % gid,
            )
        if not cache.shopify_location_active:
            # Theme I (F-6): a cached-but-deactivated location must fail
            # closed exactly like the three sibling checks above (null GID,
            # ambiguous multi-location, absent-from-cache) — it must not be
            # silently accepted merely because a stale cache row exists.
            raise FulfillmentReadError(
                'ambiguous_match',
                'Shopify location %s is present in the core location cache '
                'but is no longer active.' % gid,
            )
        return gid

    @api.model
    def _refresh_location_cache(self, job, store):
        """Q3 read-only Shopify-location refresh: upsert the core
        `shopify.connector.location` cache from a live locations read through
        sanctioned system code. Owns no inventory coupling; never touches
        location.mapping."""
        Location = self.env['shopify.connector.location'].sudo()
        nodes = self._paginate(job, store, LOCATIONS_QUERY, {}, 'locations')
        now = fields.Datetime.now()
        for node in nodes:
            if not isinstance(node, dict) or not node.get('id'):
                continue
            existing = Location.search([
                ('store_id', '=', store.id),
                ('shopify_location_gid', '=', node['id']),
            ], limit=1)
            vals = {
                'name': node.get('name') or node['id'],
                'shopify_location_active': bool(node.get('isActive', True)),
                'last_synced_at': now,
            }
            if existing:
                existing.write(vals)
            else:
                Location.create(dict(
                    vals,
                    store_id=store.id,
                    shopify_location_gid=node['id'],
                ))
        return True
