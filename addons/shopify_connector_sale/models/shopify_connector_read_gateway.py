"""Sales-owned P06 methods on the shared authorized read gateway."""

from __future__ import annotations

from typing import Any

from odoo import api, models

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (
    CursorProgress,
)

from ..integration.shopify.read_gateway import (
    CUSTOMER_READ_OPERATION,
    ORDER_DISCOUNT_APPLICATIONS_OPERATION,
    ORDER_HEADER_OPERATION,
    ORDER_LINE_ITEMS_OPERATION,
    ORDER_SCAN_OPERATION,
    ORDER_SHIPPING_LINES_OPERATION,
    CustomerReadGateway,
    OrderReadGateway,
)
from .shopify_connector_customer_importer import CUSTOMER_IMPORT_QUERY
from .shopify_connector_order_importer import (
    ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY,
    ORDER_HEADER_QUERY,
    ORDER_LINE_ITEMS_PAGE_QUERY,
    ORDER_SHIPPING_LINES_PAGE_QUERY,
)
from .shopify_connector_order_scan import ORDER_SCAN_QUERY


class ShopifyConnectorSaleReadGateway(models.AbstractModel):
    """Register sales documents and explicit customer/order read operations."""

    _inherit = "shopify.connector.read.gateway"

    @api.model
    def _extend_documents(
        self, names: set[str] | frozenset[str], documents: dict[str, str],
    ) -> dict[str, str]:
        documents = dict(super()._extend_documents(names, documents))
        if "ConnectorCustomerImport" in names:
            documents["ConnectorCustomerImport"] = CUSTOMER_IMPORT_QUERY
        providers = {
            "ConnectorOrderScan": ORDER_SCAN_QUERY,
            "ConnectorOrderHeader": ORDER_HEADER_QUERY,
            "ConnectorOrderLineItemsPage": ORDER_LINE_ITEMS_PAGE_QUERY,
            "ConnectorOrderShippingLinesPage": ORDER_SHIPPING_LINES_PAGE_QUERY,
            "ConnectorOrderDiscountApplicationsPage": (
                ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY
            ),
        }
        for name in names & providers.keys():
            documents[name] = providers[name]
        return documents

    @api.model
    def read_customer(
        self, job: Any, store: Any, customer_gid: str, *, claim: Any = None,
    ) -> dict[str, Any]:
        result = self._run(
            store,
            job,
            CUSTOMER_READ_OPERATION,
            {"ConnectorCustomerImport"},
            lambda adapter: CustomerReadGateway(adapter).read_customer(store, customer_gid),
            {"id": customer_gid},
            purpose="customer_import",
            claim=claim,
        )
        return self._rpc(result)

    @api.model
    def read_order_scan_page(
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
            "first": ORDER_SCAN_OPERATION.page_size,
            "after": cursor,
            "query": query,
        }
        result = self._run(
            store,
            job,
            ORDER_SCAN_OPERATION,
            {"ConnectorOrderScan"},
            lambda adapter: OrderReadGateway(adapter).read_order_scan_page(
                store, query=query, cursor=cursor, progress=progress
            ),
            variables,
            purpose="order_scan",
            claim=claim,
        )
        return self._rpc(result)

    @api.model
    def read_order_header(
        self, job: Any, store: Any, order_gid: str, *, claim: Any = None,
    ) -> dict[str, Any]:
        result = self._run(
            store,
            job,
            ORDER_HEADER_OPERATION,
            {"ConnectorOrderHeader"},
            lambda adapter: OrderReadGateway(adapter).read_order_header(store, order_gid),
            {"id": order_gid},
            purpose="order_import",
            claim=claim,
        )
        return self._rpc(result)

    @api.model
    def read_order_line_items_page(
        self,
        job: Any,
        store: Any,
        order_gid: str,
        *,
        cursor: str,
        progress: CursorProgress | None = None,
        claim: Any = None,
    ) -> dict[str, Any]:
        result = self._run(
            store,
            job,
            ORDER_LINE_ITEMS_OPERATION,
            {"ConnectorOrderLineItemsPage"},
            lambda adapter: OrderReadGateway(adapter).read_order_line_items_page(
                store, order_gid, cursor=cursor, progress=progress
            ),
            {"id": order_gid, "after": cursor},
            purpose="order_import",
            claim=claim,
        )
        return self._rpc(result)

    @api.model
    def read_order_shipping_lines_page(
        self,
        job: Any,
        store: Any,
        order_gid: str,
        *,
        cursor: str,
        progress: CursorProgress | None = None,
        claim: Any = None,
    ) -> dict[str, Any]:
        result = self._run(
            store,
            job,
            ORDER_SHIPPING_LINES_OPERATION,
            {"ConnectorOrderShippingLinesPage"},
            lambda adapter: OrderReadGateway(adapter).read_order_shipping_lines_page(
                store, order_gid, cursor=cursor, progress=progress
            ),
            {"id": order_gid, "after": cursor},
            purpose="order_import",
            claim=claim,
        )
        return self._rpc(result)

    @api.model
    def read_order_discount_applications_page(
        self,
        job: Any,
        store: Any,
        order_gid: str,
        *,
        cursor: str,
        progress: CursorProgress | None = None,
        claim: Any = None,
    ) -> dict[str, Any]:
        result = self._run(
            store,
            job,
            ORDER_DISCOUNT_APPLICATIONS_OPERATION,
            {"ConnectorOrderDiscountApplicationsPage"},
            lambda adapter: OrderReadGateway(adapter).read_order_discount_applications_page(
                store, order_gid, cursor=cursor, progress=progress
            ),
            {"id": order_gid, "after": cursor},
            purpose="order_import",
            claim=claim,
        )
        return self._rpc(result)


__all__ = ["ShopifyConnectorSaleReadGateway"]
