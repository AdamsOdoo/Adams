"""Typed customer/order evidence reads over the existing sale queries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Callable, TypeVar

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (
    CursorProgress,
    ReadCompatibilityAdapter,
    ReadOperation,
    ReadPage,
    ReadResult,
    ReadShapeError,
    page_from_connection,
    response_data,
    shopify_cursor,
    shopify_gid,
)

from .read_dto import (
    AddressEvidenceDTO,
    CustomerEvidenceDTO,
    DiscountAllocationEvidenceDTO,
    DiscountApplicationEvidenceDTO,
    MoneySetDTO,
    OrderEvidenceDTO,
    OrderLineEvidenceDTO,
    OrderSummaryDTO,
    ShippingLineEvidenceDTO,
    TaxLineEvidenceDTO,
    TransactionEvidenceDTO,
    address,
    money_set,
)


CUSTOMER_READ_OPERATION = ReadOperation(
    "ConnectorCustomerImport",
    variables=("id",),
    required_variables=("id",),
)
ORDER_SCAN_OPERATION = ReadOperation(
    "ConnectorOrderScan",
    variables=("first", "after", "query"),
    required_variables=("first", "query"),
    page_size=100,
    max_pages=10,
    max_items=1000,
)
ORDER_HEADER_OPERATION = ReadOperation(
    "ConnectorOrderHeader",
    variables=("id",),
    required_variables=("id",),
    page_size=100,
    max_items=100,
    max_pages=1,
)
ORDER_LINE_ITEMS_OPERATION = ReadOperation(
    "ConnectorOrderLineItemsPage",
    variables=("id", "after"),
    required_variables=("id", "after"),
    page_size=100,
    max_pages=100,
    max_items=10000,
)
ORDER_SHIPPING_LINES_OPERATION = ReadOperation(
    "ConnectorOrderShippingLinesPage",
    variables=("id", "after"),
    required_variables=("id", "after"),
    page_size=50,
    max_pages=100,
    max_items=5000,
)
ORDER_DISCOUNT_APPLICATIONS_OPERATION = ReadOperation(
    "ConnectorOrderDiscountApplicationsPage",
    variables=("id", "after"),
    required_variables=("id", "after"),
    page_size=50,
    max_pages=100,
    max_items=5000,
)

_T = TypeVar("_T")


def _mapping(value: Any, field_name: str, *, optional: bool = False) -> Mapping[str, Any] | None:
    if value is None or value is False:
        if optional:
            return None
        raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
    if not isinstance(value, Mapping):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return value


def _text(value: Any, field_name: str, *, required: bool = False) -> str | None:
    if value is None or value is False:
        if required:
            raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
        return None
    if not isinstance(value, str):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    value = value.strip()
    if required and not value:
        raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
    return value or None


def _sequence(value: Any, field_name: str, *, optional: bool = False) -> Sequence[Any]:
    if value is None:
        if optional:
            return ()
        raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, (list, tuple)):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return value


def _edge_nodes(connection: Mapping[str, Any], field_name: str) -> list[Mapping[str, Any]]:
    edges = _sequence(connection.get("edges"), f"{field_name}.edges")
    seen: set[str] = set()
    nodes: list[Mapping[str, Any]] = []
    for edge in edges:
        edge = _mapping(edge, f"{field_name}.edge")
        edge_cursor = _text(edge.get("cursor"), f"{field_name}.edge.cursor", required=True)
        if edge_cursor in seen:
            raise ReadShapeError("cursor_loop", f"Shopify sale read repeated a {field_name} edge cursor.")
        seen.add(edge_cursor or "")
        nodes.append(_mapping(edge.get("node"), f"{field_name}.edge.node") or {})
    return nodes


def _customer(node: Any, field_name: str = "customer", *, optional: bool = True) -> CustomerEvidenceDTO | None:
    customer = _mapping(node, field_name, optional=optional)
    if customer is None:
        return None
    email_node = _mapping(customer.get("defaultEmailAddress"), f"{field_name}.defaultEmailAddress", optional=True)
    phone_node = _mapping(customer.get("defaultPhoneNumber"), f"{field_name}.defaultPhoneNumber", optional=True)
    return CustomerEvidenceDTO(
        customer.get("id"),
        customer.get("firstName"),
        customer.get("lastName"),
        customer.get("displayName"),
        (email_node or {}).get("emailAddress"),
        (phone_node or {}).get("phoneNumber"),
        address(customer.get("defaultAddress"), f"{field_name}.defaultAddress"),
        customer.get("updatedAt"),
    )


def _tax_line(node: Any, field_name: str = "tax_line") -> TaxLineEvidenceDTO:
    node = _mapping(node, field_name) or {}
    return TaxLineEvidenceDTO(
        node.get("title"), node.get("source"), node.get("rate"),
        node.get("ratePercentage"), node.get("channelLiable"),
        money_set(node.get("priceSet"), f"{field_name}.priceSet"),
    )


def _tax_lines(value: Any, field_name: str) -> tuple[TaxLineEvidenceDTO, ...]:
    return tuple(_tax_line(item, f"{field_name} item") for item in _sequence(value, field_name, optional=True))


def _discount_application(node: Any, field_name: str = "discount_application") -> DiscountApplicationEvidenceDTO:
    node = _mapping(node, field_name) or {}
    return DiscountApplicationEvidenceDTO(
        node.get("__typename"), node.get("index"), node.get("allocationMethod"),
        node.get("targetType"), node.get("targetSelection"),
    )


def _discount_allocations(value: Any, field_name: str) -> tuple[DiscountAllocationEvidenceDTO, ...]:
    result = []
    for item in _sequence(value, field_name, optional=True):
        item = _mapping(item, f"{field_name} item") or {}
        application_node = _mapping(item.get("discountApplication"), f"{field_name}.discountApplication", optional=True)
        result.append(
            DiscountAllocationEvidenceDTO(
                money_set(item.get("allocatedAmountSet"), f"{field_name}.allocatedAmountSet"),
                _discount_application(application_node, f"{field_name}.discountApplication") if application_node else None,
            )
        )
    return tuple(result)


def _line_item(node: Any, field_name: str = "line_item") -> OrderLineEvidenceDTO:
    node = _mapping(node, field_name) or {}
    variant = _mapping(node.get("variant"), f"{field_name}.variant", optional=True)
    product = _mapping(node.get("product"), f"{field_name}.product", optional=True)
    return OrderLineEvidenceDTO(
        node.get("id"), node.get("name"), node.get("title"), node.get("variantTitle"),
        node.get("quantity"), node.get("currentQuantity"), node.get("sku"),
        node.get("isGiftCard"), node.get("requiresShipping"), node.get("taxable"),
        (variant or {}).get("id"), (product or {}).get("id"),
        money_set(node.get("originalUnitPriceSet"), f"{field_name}.originalUnitPriceSet"),
        money_set(node.get("originalTotalSet"), f"{field_name}.originalTotalSet"),
        money_set(node.get("discountedUnitPriceSet"), f"{field_name}.discountedUnitPriceSet"),
        money_set(node.get("discountedTotalSet"), f"{field_name}.discountedTotalSet"),
        money_set(node.get("discountedUnitPriceAfterAllDiscountsSet"), f"{field_name}.discountedUnitPriceAfterAllDiscountsSet"),
        _discount_allocations(node.get("discountAllocations"), f"{field_name}.discountAllocations"),
        _tax_lines(node.get("taxLines"), f"{field_name}.taxLines"),
    )


def _shipping_line(node: Any, field_name: str = "shipping_line") -> ShippingLineEvidenceDTO:
    node = _mapping(node, field_name) or {}
    return ShippingLineEvidenceDTO(
        node.get("id"), node.get("isRemoved"), node.get("title"),
        money_set(node.get("discountedPriceSet"), f"{field_name}.discountedPriceSet"),
        money_set(node.get("currentDiscountedPriceSet"), f"{field_name}.currentDiscountedPriceSet"),
        _tax_lines(node.get("taxLines"), f"{field_name}.taxLines"),
    )


def _transaction(node: Any, field_name: str = "transaction") -> TransactionEvidenceDTO:
    node = _mapping(node, field_name) or {}
    return TransactionEvidenceDTO(
        node.get("id"), node.get("gateway"), node.get("kind"), node.get("status"),
        node.get("manualPaymentGateway"), node.get("processedAt"),
        money_set(node.get("amountSet"), f"{field_name}.amountSet"),
    )


def _page(
    operation: ReadOperation,
    connection: Mapping[str, Any],
    *,
    cursor: str | None,
    observation: Any,
    converter: Callable[[Any, str], _T],
    field_name: str,
    progress: CursorProgress | None,
) -> ReadPage[_T]:
    nodes = _edge_nodes(connection, field_name)
    items = tuple(converter(item, f"{field_name} item") for item in nodes)
    page_info = _mapping(connection.get("pageInfo"), f"{field_name}.pageInfo")
    return page_from_connection(
        operation,
        cursor=cursor,
        page_info=page_info or {},
        items=items,
        observation=observation,
        progress=progress,
    )


class CustomerReadGateway:
    """Normalize the exact read-only customer evidence query."""

    def __init__(self, adapter: ReadCompatibilityAdapter) -> None:
        if not isinstance(adapter, ReadCompatibilityAdapter):
            raise TypeError("adapter must be ReadCompatibilityAdapter")
        self.adapter = adapter

    def read_customer(self, store: Any, customer_gid: str) -> ReadResult[CustomerEvidenceDTO | None]:
        customer_gid = shopify_gid(customer_gid, "customer_gid", kind="Customer")
        response = self.adapter.execute(store, CUSTOMER_READ_OPERATION, {"id": customer_gid})
        data, observation = response_data(response, CUSTOMER_READ_OPERATION.operation_name)
        value = _customer(data.get("customer"), "customer")
        if value is not None and value.gid != customer_gid:
            raise ReadShapeError("identity_mismatch", "Shopify customer read returned the wrong customer identity.")
        return ReadResult(value, CUSTOMER_READ_OPERATION.operation_name, observation)


class OrderReadGateway:
    """Normalize order scan/header evidence and each bounded child page."""

    def __init__(self, adapter: ReadCompatibilityAdapter) -> None:
        if not isinstance(adapter, ReadCompatibilityAdapter):
            raise TypeError("adapter must be ReadCompatibilityAdapter")
        self.adapter = adapter

    def read_order_scan_page(
        self,
        store: Any,
        *,
        query: str = "",
        cursor: str | None = None,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ReadPage[OrderSummaryDTO]]:
        if not isinstance(query, str):
            raise TypeError("order scan query must be a string")
        cursor = shopify_cursor(cursor)
        response = self.adapter.execute(
            store,
            ORDER_SCAN_OPERATION,
            {"first": ORDER_SCAN_OPERATION.page_size, "after": cursor, "query": query},
        )
        data, observation = response_data(response, ORDER_SCAN_OPERATION.operation_name)
        orders = _mapping(data.get("orders"), "orders")
        items = tuple(
            OrderSummaryDTO(
                _mapping(node, "order").get("id"),
                _mapping(node, "order").get("updatedAt"),
                _mapping(node, "order").get("createdAt"),
                _mapping(node, "order").get("edited"),
                _mapping(node, "order").get("test"),
                _mapping(node, "order").get("cancelledAt"),
                _mapping(node, "order").get("displayFinancialStatus"),
            )
            for node in _edge_nodes(orders, "orders")
        )
        page = page_from_connection(
            ORDER_SCAN_OPERATION,
            cursor=cursor,
            page_info=_mapping(orders.get("pageInfo"), "orders.pageInfo") or {},
            items=items,
            observation=observation,
            progress=progress,
        )
        return ReadResult(page, ORDER_SCAN_OPERATION.operation_name, observation)

    def read_order_header(self, store: Any, order_gid: str) -> ReadResult[OrderEvidenceDTO | None]:
        self._require_gid(order_gid, "order_gid", "Order")
        response = self.adapter.execute(store, ORDER_HEADER_OPERATION, {"id": order_gid})
        data, observation = response_data(response, ORDER_HEADER_OPERATION.operation_name)
        order = data.get("order")
        if order is None:
            return ReadResult(None, ORDER_HEADER_OPERATION.operation_name, observation)
        value = self._order(order, observation)
        if value.gid != order_gid:
            raise ReadShapeError("identity_mismatch", "Shopify order read returned the wrong order identity.")
        return ReadResult(value, ORDER_HEADER_OPERATION.operation_name, observation)

    def read_order_line_items_page(
        self,
        store: Any,
        order_gid: str,
        *,
        cursor: str,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ReadPage[OrderLineEvidenceDTO]]:
        return self._read_child_page(store, order_gid, cursor, ORDER_LINE_ITEMS_OPERATION, "lineItems", _line_item, progress)

    def read_order_shipping_lines_page(
        self,
        store: Any,
        order_gid: str,
        *,
        cursor: str,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ReadPage[ShippingLineEvidenceDTO]]:
        return self._read_child_page(store, order_gid, cursor, ORDER_SHIPPING_LINES_OPERATION, "shippingLines", _shipping_line, progress)

    def read_order_discount_applications_page(
        self,
        store: Any,
        order_gid: str,
        *,
        cursor: str,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ReadPage[DiscountApplicationEvidenceDTO]]:
        return self._read_child_page(store, order_gid, cursor, ORDER_DISCOUNT_APPLICATIONS_OPERATION, "discountApplications", _discount_application, progress)

    def _read_child_page(
        self,
        store: Any,
        order_gid: str,
        cursor: str,
        operation: ReadOperation,
        field_name: str,
        converter: Callable[[Any, str], _T],
        progress: CursorProgress | None,
    ) -> ReadResult[ReadPage[_T]]:
        self._require_gid(order_gid, "order_gid", "Order")
        cursor = shopify_cursor(cursor, allow_none=False)
        response = self.adapter.execute(store, operation, {"id": order_gid, "after": cursor})
        data, observation = response_data(response, operation.operation_name)
        order = _mapping(data.get("order"), "order")
        if order.get("id") != order_gid:
            raise ReadShapeError("identity_mismatch", "Shopify order read returned the wrong order identity.")
        _text(order.get("updatedAt"), "order.updatedAt", required=True)
        connection = _mapping(order.get(field_name), field_name)
        page = _page(
            operation, connection or {}, cursor=cursor, observation=observation,
            converter=converter, field_name=field_name, progress=progress,
        )
        return ReadResult(page, operation.operation_name, observation)

    def _order(self, raw: Any, observation: Any) -> OrderEvidenceDTO:
        order = _mapping(raw, "order") or {}
        line_items = _mapping(order.get("lineItems"), "lineItems")
        shipping_lines = _mapping(order.get("shippingLines"), "shippingLines")
        discount_applications = _mapping(order.get("discountApplications"), "discountApplications")
        if line_items is None or shipping_lines is None or discount_applications is None:
            raise ReadShapeError("missing_field", "Shopify order read omitted a required evidence connection.")
        transactions = tuple(_transaction(item) for item in _sequence(order.get("transactions"), "transactions", optional=True))
        tax_lines = tuple(_tax_line(item) for item in _sequence(order.get("taxLines"), "taxLines", optional=True))
        total_fields = (
            "totalPriceSet", "subtotalPriceSet", "totalTaxSet", "totalDiscountsSet",
            "totalShippingPriceSet", "totalTipReceivedSet", "currentTotalPriceSet",
            "currentTotalTaxSet", "currentShippingPriceSet", "currentTotalAdditionalFeesSet",
            "currentTotalDutiesSet",
        )
        totals = {name: money_set(order.get(name), f"order.{name}") for name in total_fields}
        rounding = _mapping(order.get("totalCashRoundingAdjustment"), "totalCashRoundingAdjustment", optional=True) or {}
        cash_rounding = {
            name: money_set(rounding.get(name), f"order.totalCashRoundingAdjustment.{name}")
            for name in ("paymentSet", "refundSet")
        }
        gateways = _sequence(order.get("paymentGatewayNames"), "paymentGatewayNames", optional=True)
        if any(not isinstance(item, str) for item in gateways):
            raise ReadShapeError("invalid_shape", "Shopify order read returned invalid payment gateway names.")
        return OrderEvidenceDTO(
            order.get("id"), order.get("name"), order.get("legacyResourceId"),
            order.get("createdAt"), order.get("processedAt"), order.get("updatedAt"),
            order.get("edited"), order.get("test"), order.get("currencyCode"),
            order.get("presentmentCurrencyCode"), order.get("taxesIncluded"),
            order.get("confirmed"), order.get("closed"), order.get("closedAt"),
            order.get("cancelledAt"), order.get("cancelReason"),
            order.get("displayFinancialStatus"), order.get("displayFulfillmentStatus"),
            order.get("email"), tuple(gateways), _customer(order.get("customer")),
            address(order.get("billingAddress"), "billingAddress"),
            address(order.get("shippingAddress"), "shippingAddress"), totals, cash_rounding,
            transactions, tax_lines,
            _page(ORDER_HEADER_OPERATION, line_items, cursor=None, observation=observation, converter=_line_item, field_name="lineItems", progress=None),
            _page(ORDER_HEADER_OPERATION, shipping_lines, cursor=None, observation=observation, converter=_shipping_line, field_name="shippingLines", progress=None),
            _page(ORDER_HEADER_OPERATION, discount_applications, cursor=None, observation=observation, converter=_discount_application, field_name="discountApplications", progress=None),
        )

    @staticmethod
    def _require_gid(value: Any, field_name: str, kind: str) -> None:
        shopify_gid(value, field_name, kind=kind)


__all__ = [
    "CUSTOMER_READ_OPERATION",
    "CustomerReadGateway",
    "ORDER_DISCOUNT_APPLICATIONS_OPERATION",
    "ORDER_HEADER_OPERATION",
    "ORDER_LINE_ITEMS_OPERATION",
    "ORDER_SCAN_OPERATION",
    "ORDER_SHIPPING_LINES_OPERATION",
    "OrderReadGateway",
]
