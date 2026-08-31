"""Product-owned P06 methods on the shared authorized read gateway."""

from __future__ import annotations

from typing import Any

from odoo import api, models

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (
    CursorProgress,
)

from ..integration.shopify.read_gateway import (
    PRODUCT_READ_OPERATION,
    PRODUCT_SCAN_OPERATION,
    ProductReadGateway,
)
from .shopify_connector_product_importer import PRODUCT_IMPORT_QUERY
from .shopify_connector_product_scan import PRODUCT_SCAN_QUERY


class ShopifyConnectorProductReadGateway(models.AbstractModel):
    """Register product documents and explicit product read operations."""

    _inherit = "shopify.connector.read.gateway"

    @api.model
    def _extend_documents(
        self, names: set[str] | frozenset[str], documents: dict[str, str],
    ) -> dict[str, str]:
        documents = dict(super()._extend_documents(names, documents))
        if "ConnectorProductScan" in names:
            documents["ConnectorProductScan"] = PRODUCT_SCAN_QUERY
        if "ConnectorProductImport" in names:
            documents["ConnectorProductImport"] = PRODUCT_IMPORT_QUERY
        return documents

    @api.model
    def read_product_page(
        self,
        job: Any,
        store: Any,
        *,
        query: str = "",
        cursor: str | None = None,
        progress: CursorProgress | None = None,
        claim: Any = None,
    ) -> dict[str, Any]:
        variables = {
            "first": PRODUCT_SCAN_OPERATION.page_size,
            "after": cursor,
            "query": query,
        }
        result = self._run(
            store,
            job,
            PRODUCT_SCAN_OPERATION,
            {"ConnectorProductScan"},
            lambda adapter: ProductReadGateway(adapter).read_product_page(
                store, query=query, cursor=cursor, progress=progress
            ),
            variables,
            purpose="product_scan",
            claim=claim,
        )
        return self._rpc(result)

    @api.model
    def read_product(
        self,
        job: Any,
        store: Any,
        product_gid: str,
        *,
        cursor: str | None = None,
        progress: CursorProgress | None = None,
        claim: Any = None,
    ) -> dict[str, Any]:
        variables = {"id": product_gid, "cursor": cursor}
        result = self._run(
            store,
            job,
            PRODUCT_READ_OPERATION,
            {"ConnectorProductImport"},
            lambda adapter: ProductReadGateway(adapter).read_product(
                store, product_gid, cursor=cursor, progress=progress
            ),
            variables,
            purpose="product_import",
            claim=claim,
        )
        return self._rpc(result)


__all__ = ["ShopifyConnectorProductReadGateway"]
