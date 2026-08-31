"""P06 typed-read routing for the existing order scan producer."""

import json
from collections.abc import Mapping

from odoo import api, models

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (
    ReadGatewayError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


class ShopifyConnectorOrderScanP06(models.AbstractModel):
    """Add a reversible typed gateway without enlarging the V1 producer."""

    _inherit = 'shopify.connector.order.scan'

    @api.model
    def _read_order_scan_page(
        self, job, store, *, query_filter, cursor, seen_cursors, seen_gids,
    ):
        gateway = self.env['shopify.connector.read.gateway']
        if gateway._store_mode(store) == 'legacy':
            return super()._read_order_scan_page(
                job, store, query_filter=query_filter, cursor=cursor,
                seen_cursors=seen_cursors, seen_gids=seen_gids,
            )
        try:
            result = gateway.read_order_scan_page(
                job, store, query=query_filter, cursor=cursor,
            )
            return self._page_from_p06_gateway(
                result, seen_cursors, seen_gids,
            )
        except ReadGatewayError as exc:
            raise JobHandlerError(
                self._p06_error_class(exc),
                'Shopify order scan read was rejected by the typed gateway.',
                technical_detail=json.dumps({
                    'code': exc.code,
                    'operation': exc.operation_name,
                }, sort_keys=True),
            ) from exc

    @api.model
    def _page_from_p06_gateway(self, result, seen_cursors, seen_gids):
        if not isinstance(result, Mapping):
            raise ReadGatewayError(
                'invalid_result', 'The typed order scan returned no result.',
                'ConnectorOrderScan',
            )
        if result.get('operation_name') != 'ConnectorOrderScan':
            raise ReadGatewayError(
                'operation_mismatch',
                'The typed order scan returned the wrong operation.',
                'ConnectorOrderScan',
            )
        value = result.get('value')
        if not isinstance(value, Mapping):
            raise ReadGatewayError(
                'invalid_result', 'The typed order scan omitted its page.',
                'ConnectorOrderScan',
            )
        items = value.get('items')
        has_more = value.get('has_more')
        next_cursor = value.get('next_cursor')
        if (
            not isinstance(items, (list, tuple))
            or not isinstance(has_more, bool)
            or (has_more and not isinstance(next_cursor, str))
            or (not has_more and next_cursor is not None)
        ):
            raise ReadGatewayError(
                'pagination_invalid',
                'The typed order scan returned invalid page metadata.',
                'ConnectorOrderScan',
            )
        edges = []
        for item in items:
            if not isinstance(item, Mapping):
                raise ReadGatewayError(
                    'invalid_shape',
                    'The typed order scan returned an invalid summary item.',
                    'ConnectorOrderScan',
                )
            edges.append({
                'cursor': 'typed-edge:%s' % item.get('gid'),
                'node': {
                    'id': item.get('gid'),
                    'updatedAt': item.get('updated_at'),
                    'createdAt': item.get('created_at'),
                    'edited': item.get('edited'),
                    'test': item.get('test'),
                    'cancelledAt': item.get('cancelled_at'),
                    'displayFinancialStatus': (
                        item.get('display_financial_status')
                    ),
                },
            })
        return self._validate_page({
            'edges': edges,
            'pageInfo': {
                'hasNextPage': has_more,
                'endCursor': next_cursor,
            },
        }, seen_cursors, seen_gids)

    @staticmethod
    def _p06_error_class(error):
        shape_codes = {
            'cursor_invalid', 'cursor_loop', 'identity_duplicate',
            'identity_invalid', 'invalid_identity', 'invalid_result',
            'invalid_shape', 'missing_field', 'operation_mismatch',
            'page_limit', 'page_size', 'pagination_invalid', 'item_limit',
        }
        return (
            'data_shape_schema_mismatch'
            if error.code in shape_codes else 'unknown_system_error'
        )


__all__ = ['ShopifyConnectorOrderScanP06']
