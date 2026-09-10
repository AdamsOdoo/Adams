"""P06 typed-read routing for the existing product scan producer."""

from odoo import api, models

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (
    ReadGatewayError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..integration.shopify.read_gateway import (
    PRODUCT_SCAN_OPERATION,
    scan_page_from_gateway_result,
)
from .shopify_connector_product_scan import PRODUCT_SCAN_PAGE_SIZE


class ShopifyConnectorProductScanP06(models.AbstractModel):
    """Add a reversible typed gateway without enlarging the V1 producer."""

    _inherit = 'shopify.connector.product.scan'

    @api.model
    def _read_product_scan_page(
        self, job, store, *, query_filter, cursor, page_limit,
        seen_cursors, seen_gids, claim=None,
    ):
        gateway = self.env['shopify.connector.read.gateway']
        if claim is None and (
            page_limit > PRODUCT_SCAN_OPERATION.max_pages
            or gateway._store_mode(store) == 'legacy'
        ):
            return super()._read_product_scan_page(
                job, store, query_filter=query_filter, cursor=cursor,
                page_limit=page_limit, seen_cursors=seen_cursors,
                seen_gids=seen_gids,
            )
        try:
            result = gateway.read_product_page(
                job, store, query=query_filter, cursor=cursor, claim=claim,
            )
            return self._validate_p06_product_page(
                scan_page_from_gateway_result(result), cursor=cursor,
                seen_cursors=seen_cursors, seen_gids=seen_gids,
            )
        except ReadGatewayError as exc:
            raise self._p06_product_failure(exc) from exc

    @api.model
    def _p06_product_failure(self, exc):
        cause = exc.__cause__
        if isinstance(cause, ShopifyClientError):
            return JobHandlerError(
                cause.error_class, cause.reason, cause.technical_detail,
            )
        shape_codes = {
            'api_version_mismatch', 'cursor_invalid', 'cursor_loop',
            'identity_duplicate', 'identity_invalid', 'invalid_identity',
            'invalid_response', 'invalid_result', 'invalid_shape',
            'item_limit', 'missing_field', 'operation_mismatch', 'page_limit',
            'page_size', 'pagination_invalid',
        }
        error_class = (
            'data_shape_schema_mismatch'
            if exc.code in shape_codes else 'unknown_system_error'
        )
        return JobHandlerError(error_class, exc.message)

    @api.model
    def _validate_p06_product_page(
        self, page, *, cursor, seen_cursors, seen_gids,
    ):
        nodes = page.get('nodes') if isinstance(page, dict) else None
        has_next = page.get('has_next') if isinstance(page, dict) else None
        end_cursor = page.get('end_cursor') if isinstance(page, dict) else None
        if not isinstance(nodes, list) or not isinstance(has_next, bool):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify product scan gateway returned malformed page metadata.',
            )
        if len(nodes) > PRODUCT_SCAN_PAGE_SIZE:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify product scan gateway exceeded its page bound.',
            )
        for node in nodes:
            gid = node.get('id') if isinstance(node, dict) else None
            updated_at = node.get('updatedAt') if isinstance(node, dict) else None
            if not isinstance(gid, str) or not gid or not isinstance(updated_at, str) or not updated_at:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan gateway returned a malformed product.',
                )
            if gid in seen_gids:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan gateway returned a duplicate product identity.',
                )
            seen_gids.add(gid)
        if has_next:
            if (
                not isinstance(end_cursor, str) or not end_cursor
                or end_cursor == cursor or end_cursor in seen_cursors
            ):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan gateway did not advance its cursor.',
                )
            seen_cursors.add(end_cursor)
        elif end_cursor is not None:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify product scan gateway returned a terminal cursor.',
            )
        return page


__all__ = ['ShopifyConnectorProductScanP06']
