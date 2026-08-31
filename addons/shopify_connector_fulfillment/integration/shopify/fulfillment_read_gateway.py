"""Typed, bounded Shopify fulfillment reads.

The gateway preserves the shapes emitted by the V1 fulfillment reader while
making pagination and identity checks explicit.  It is deliberately pure:
Odoo repositories, leases, retries and all remote writes remain outside this
module.  A supplied delegate is called exactly once for every page/batch.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from odoo.addons.shopify_connector_core.domain.immutability import freeze_value, to_plain

from .fulfillment_documents import FULFILLMENT_NODE_QUERY, ORDER_FULFILLMENTS_QUERY


MAX_PAGE_SIZE = 250
DEFAULT_PAGE_SIZE = 50
MAX_PAGES = 100
MAX_BATCH = 50
MAX_BATCH_ITEMS = 1000
MAX_CURSOR_LENGTH = 512
SHOPIFY_API_VERSION = "2026-07"

FULFILLMENT_ORDERS_OPERATION = "fulfillment_orders_for_order"
FULFILLMENT_ORDER_LINES_OPERATION = "fulfillment_order_lines"
ORDER_FULFILLMENTS_OPERATION = "order_fulfillments"
FULFILLMENT_NODE_OPERATION = "fulfillment_node"
FULFILLMENT_NODES_OPERATION = "fulfillment_nodes"
LOCATIONS_OPERATION = "fulfillment_locations"
READ_OPERATION_KEYS = frozenset(
    (
        FULFILLMENT_ORDERS_OPERATION,
        FULFILLMENT_ORDER_LINES_OPERATION,
        ORDER_FULFILLMENTS_OPERATION,
        FULFILLMENT_NODE_OPERATION,
        FULFILLMENT_NODES_OPERATION,
        LOCATIONS_OPERATION,
    )
)

FULFILLMENT_ORDERS_QUERY = (
    "query ConnectorFulfillmentOrdersForOrder($orderId: ID!, $foCursor: String) { "
    "order(id: $orderId) { id fulfillmentOrders(first: 50, after: $foCursor) { "
    "pageInfo { hasNextPage endCursor } nodes { id status requestStatus "
    "assignedLocation { location { id name } } supportedActions { action } } } } }"
)
FULFILLMENT_ORDER_LINES_QUERY = (
    "query ConnectorFulfillmentOrderLines($foId: ID!, $lineCursor: String) { "
    "fulfillmentOrder(id: $foId) { id lineItems(first: 50, after: $lineCursor) { "
    "pageInfo { hasNextPage endCursor } nodes { id remainingQuantity lineItem { id } } } } }"
)
FULFILLMENT_NODES_QUERY = (
    "query ConnectorFulfillmentNodes($ids: [ID!]!) { nodes(ids: $ids) { ... on Fulfillment { "
    "id status displayStatus trackingInfo { number url company } } } }"
)
LOCATIONS_QUERY = (
    "query ConnectorFulfillmentLocations($cursor: String) { locations(first: 50, after: $cursor, "
    "includeInactive: true) { pageInfo { hasNextPage endCursor } nodes { id name isActive } } }"
)

_GID = re.compile(r"^gid://shopify/(?P<kind>[A-Za-z][A-Za-z0-9_]*)/(?P<id>[1-9][0-9]*)$")


class FulfillmentReadDelegate(Protocol):
    def read(self, operation_key: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class FulfillmentReadError(ValueError):
    """A fulfillment read is incomplete, malformed or identity-ambiguous."""

    def __init__(self, message: str, code: str = "data_shape_schema_mismatch") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(message: str, code: str = "data_shape_schema_mismatch") -> None:
    raise FulfillmentReadError(message, code)


def _gid(value: Any, kind: str) -> str:
    if not isinstance(value, str):
        _fail("Shopify returned a non-string %s identity." % kind)
    match = _GID.fullmatch(value)
    if not match or match.group("kind") != kind:
        _fail("Shopify returned a malformed %s GID." % kind)
    return value


def _cursor(value: Any, *, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value or len(value) > MAX_CURSOR_LENGTH:
        _fail("Shopify returned a malformed fulfillment pagination cursor.")
    return value


def _data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(response, Mapping):
        _fail("Shopify fulfillment read returned an invalid response envelope.")
    errors = response.get("errors")
    if "errors" in response:
        if (
            not isinstance(errors, (list, tuple))
            or any(not isinstance(item, Mapping) for item in errors)
        ):
            _fail("Shopify fulfillment read returned malformed errors.")
        if errors:
            _fail("Shopify rejected the fulfillment read.", "remote_error")
    extensions = response.get("extensions")
    if extensions is not None and not isinstance(extensions, Mapping):
        _fail("Shopify fulfillment read returned malformed extensions.")
    if isinstance(extensions, Mapping):
        cost = extensions.get("cost")
        if cost is not None and not isinstance(cost, Mapping):
            _fail("Shopify fulfillment read returned malformed cost telemetry.")
    served = response.get("served_version", response.get("servedVersion"))
    if served != SHOPIFY_API_VERSION:
        _fail(
            "Shopify fulfillment read was not served by the pinned API version.",
            "api_version_mismatch",
        )
    if not isinstance(response.get("data"), Mapping):
        _fail("Shopify fulfillment read returned no data object.")
    return response["data"]


def _read_once(
    delegate: FulfillmentReadDelegate | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
    operation_key: str,
    variables: Mapping[str, Any],
) -> Mapping[str, Any]:
    if operation_key not in READ_OPERATION_KEYS:
        _fail("Fulfillment read operation is not allowlisted.", "invalid_operation")
    try:
        plain = to_plain(freeze_value(dict(variables)))
    except (TypeError, ValueError) as exc:
        raise FulfillmentReadError("Fulfillment read variables are malformed.", "validation_error") from exc
    try:
        result = delegate.read(operation_key, plain) if hasattr(delegate, "read") else delegate(operation_key, plain)
    except FulfillmentReadError:
        raise
    except Exception as exc:  # pragma: no cover - supplied transport decides details
        raise FulfillmentReadError("Shopify fulfillment read could not be completed.", "shopify_unavailable") from exc
    if not isinstance(result, Mapping):
        _fail("Fulfillment read delegate returned a non-mapping response.")
    return result


def _safe_text(value: Any, field: str, *, allow_none: bool = True) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        _fail("Shopify fulfillment %s shape is malformed." % field)
    return value


@dataclass(frozen=True, slots=True)
class FulfillmentOrderLineDTO:
    id: str
    remaining_quantity: int
    line_item_id: str | None

    def __post_init__(self) -> None:
        _gid(self.id, "FulfillmentOrderLineItem")
        if isinstance(self.remaining_quantity, bool) or not isinstance(self.remaining_quantity, int) or self.remaining_quantity < 0:
            raise ValueError("remaining_quantity must be a non-negative integer")
        if self.line_item_id is not None:
            _gid(self.line_item_id, "LineItem")

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "remainingQuantity": self.remaining_quantity,
            "lineItem": {"id": self.line_item_id} if self.line_item_id else None,
        }


@dataclass(frozen=True, slots=True)
class FulfillmentOrderDTO:
    id: str
    status: str
    request_status: str | None
    assigned_location: Mapping[str, Any] | None
    supported_actions: tuple[str, ...]
    line_items: tuple[FulfillmentOrderLineDTO, ...] = ()

    def __post_init__(self) -> None:
        _gid(self.id, "FulfillmentOrder")
        _safe_text(self.status, "status", allow_none=False)
        _safe_text(self.request_status, "requestStatus")
        if self.assigned_location is not None:
            if not isinstance(self.assigned_location, Mapping):
                raise TypeError("assigned_location must be a mapping or None")
            object.__setattr__(self, "assigned_location", freeze_value(dict(self.assigned_location)))
        if any(not isinstance(value, str) or not value for value in self.supported_actions):
            raise ValueError("supported_actions must contain non-empty strings")
        object.__setattr__(self, "supported_actions", tuple(self.supported_actions))
        object.__setattr__(self, "line_items", tuple(self.line_items))
        if any(not isinstance(item, FulfillmentOrderLineDTO) for item in self.line_items):
            raise TypeError("line_items must contain FulfillmentOrderLineDTO values")

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "requestStatus": self.request_status,
            "assignedLocation": to_plain(self.assigned_location) if self.assigned_location is not None else None,
            "supportedActions": [{"action": value} for value in self.supported_actions],
            "line_items": [item.to_legacy_dict() for item in self.line_items],
        }


@dataclass(frozen=True, slots=True)
class FulfillmentPageDTO:
    items: tuple[Any, ...]
    has_next_page: bool
    next_cursor: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.has_next_page, bool):
            raise TypeError("has_next_page must be bool")
        object.__setattr__(self, "items", tuple(self.items))
        if self.has_next_page:
            _cursor(self.next_cursor, required=True)
        else:
            _cursor(self.next_cursor)

    def to_legacy_list(self) -> list[dict[str, Any]]:
        return [item.to_legacy_dict() for item in self.items]


@dataclass(frozen=True, slots=True)
class FulfillmentRecordDTO:
    id: str
    status: str | None
    display_status: str | None
    tracking_info: Mapping[str, Any] | None
    line_items: tuple[Mapping[str, Any], ...] = ()
    # ``Order.fulfillments`` always selects the nested connection in V1,
    # including when it is empty.  Keep that distinction so a typed result
    # can be converted back to the exact V1 dictionary vocabulary rather than
    # silently omitting an empty connection.
    include_line_items: bool = False
    line_items_page_info: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        _gid(self.id, "Fulfillment")
        _safe_text(self.status, "status")
        _safe_text(self.display_status, "displayStatus")
        if self.tracking_info is not None:
            if not isinstance(self.tracking_info, Mapping):
                raise TypeError("tracking_info must be a mapping or None")
            object.__setattr__(self, "tracking_info", freeze_value(dict(self.tracking_info)))
        object.__setattr__(self, "line_items", tuple(freeze_value(dict(item)) for item in self.line_items))
        if not isinstance(self.include_line_items, bool):
            raise TypeError("include_line_items must be bool")
        if self.line_items_page_info is not None:
            if not isinstance(self.line_items_page_info, Mapping):
                raise TypeError("line_items_page_info must be a mapping or None")
            object.__setattr__(
                self,
                "line_items_page_info",
                freeze_value(dict(self.line_items_page_info)),
            )

    def to_legacy_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "status": self.status,
            "displayStatus": self.display_status,
            "trackingInfo": to_plain(self.tracking_info) if self.tracking_info is not None else None,
        }
        if self.include_line_items:
            result["fulfillmentLineItems"] = {
                "pageInfo": to_plain(self.line_items_page_info)
                if self.line_items_page_info is not None
                else {"hasNextPage": False, "endCursor": None},
                "nodes": [to_plain(item) for item in self.line_items],
            }
        return result


@dataclass(frozen=True, slots=True)
class FulfillmentLocationDTO:
    id: str
    name: str
    is_active: bool
    cursor: str | None = None

    def __post_init__(self) -> None:
        _gid(self.id, "Location")
        _safe_text(self.name, "location name", allow_none=False)
        if not isinstance(self.is_active, bool):
            raise TypeError("is_active must be bool")
        _cursor(self.cursor)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "isActive": self.is_active}


class FulfillmentReadGateway:
    """Typed read surface with explicit operation keys and bounded traversal."""

    operation_documents = {
        FULFILLMENT_ORDERS_OPERATION: FULFILLMENT_ORDERS_QUERY,
        FULFILLMENT_ORDER_LINES_OPERATION: FULFILLMENT_ORDER_LINES_QUERY,
        ORDER_FULFILLMENTS_OPERATION: ORDER_FULFILLMENTS_QUERY,
        FULFILLMENT_NODE_OPERATION: FULFILLMENT_NODE_QUERY,
        FULFILLMENT_NODES_OPERATION: FULFILLMENT_NODES_QUERY,
        LOCATIONS_OPERATION: LOCATIONS_QUERY,
    }

    def __init__(self, delegate: FulfillmentReadDelegate | Callable[[str, Mapping[str, Any]], Mapping[str, Any]], *, max_pages: int = MAX_PAGES) -> None:
        if not callable(delegate) and not hasattr(delegate, "read"):
            raise TypeError("delegate must provide one read operation")
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_PAGES:
            raise ValueError("max_pages must be between 1 and %d" % MAX_PAGES)
        self._delegate = delegate
        self.max_pages = max_pages

    def read_fulfillment_orders_page(self, order_gid: str, cursor: str | None = None) -> FulfillmentPageDTO:
        order_gid = _gid(order_gid, "Order")
        _cursor(cursor)
        data = _data(_read_once(self._delegate, FULFILLMENT_ORDERS_OPERATION, {"orderId": order_gid, "foCursor": cursor}))
        order = data.get("order")
        if not isinstance(order, Mapping) or order.get("id") != order_gid:
            _fail("Shopify fulfillment-order read returned a different order identity.")
        connection = order.get("fulfillmentOrders")
        return self._fulfillment_order_page(connection)

    def _fulfillment_order_page(self, connection: Any) -> FulfillmentPageDTO:
        if not isinstance(connection, Mapping) or not isinstance(connection.get("nodes"), list):
            _fail("Shopify fulfillment-order connection shape is malformed.")
        page_info = connection.get("pageInfo")
        if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
            _fail("Shopify fulfillment-order pageInfo shape is malformed.")
        items: list[FulfillmentOrderDTO] = []
        for node in connection["nodes"]:
            items.append(self._fulfillment_order(node))
        next_cursor = _cursor(page_info.get("endCursor"))
        if page_info["hasNextPage"] and next_cursor is None:
            _fail("Shopify fulfillment-order page omitted its next cursor.")
        return FulfillmentPageDTO(tuple(items), page_info["hasNextPage"], next_cursor)

    def _fulfillment_order(self, node: Any) -> FulfillmentOrderDTO:
        if not isinstance(node, Mapping):
            _fail("Shopify returned a malformed FulfillmentOrder node.")
        assigned = node.get("assignedLocation")
        if assigned is not None and not isinstance(assigned, Mapping):
            _fail("Shopify fulfillment assignedLocation shape is malformed.")
        actions = node.get("supportedActions")
        if not isinstance(actions, list):
            _fail("Shopify fulfillment supportedActions shape is malformed.")
        action_values: list[str] = []
        for action in actions:
            if not isinstance(action, Mapping):
                _fail("Shopify fulfillment action shape is malformed.")
            value = _safe_text(action.get("action"), "supported action", allow_none=False)
            action_values.append(value or "")
        return FulfillmentOrderDTO(
            _gid(node.get("id"), "FulfillmentOrder"),
            _safe_text(node.get("status"), "status", allow_none=False) or "",
            _safe_text(node.get("requestStatus"), "requestStatus"),
            assigned,
            tuple(action_values),
        )

    def read_fulfillment_order_lines_page(self, fulfillment_order_gid: str, cursor: str | None = None) -> FulfillmentPageDTO:
        fulfillment_order_gid = _gid(fulfillment_order_gid, "FulfillmentOrder")
        _cursor(cursor)
        data = _data(_read_once(self._delegate, FULFILLMENT_ORDER_LINES_OPERATION, {"foId": fulfillment_order_gid, "lineCursor": cursor}))
        order = data.get("fulfillmentOrder")
        if not isinstance(order, Mapping) or order.get("id") != fulfillment_order_gid:
            _fail("Shopify fulfillment-order-line read returned a different order identity.")
        connection = order.get("lineItems")
        if not isinstance(connection, Mapping) or not isinstance(connection.get("nodes"), list):
            _fail("Shopify fulfillment-order line connection shape is malformed.")
        page_info = connection.get("pageInfo")
        if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
            _fail("Shopify fulfillment-order line pageInfo shape is malformed.")
        lines: list[FulfillmentOrderLineDTO] = []
        for node in connection["nodes"]:
            if not isinstance(node, Mapping):
                _fail("Shopify returned a malformed fulfillment-order line.")
            remaining = node.get("remainingQuantity")
            if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining < 0:
                _fail("Shopify returned a malformed remaining quantity.")
            line = node.get("lineItem")
            line_gid = _gid(line.get("id") if isinstance(line, Mapping) else None, "LineItem") if line is not None else None
            lines.append(FulfillmentOrderLineDTO(_gid(node.get("id"), "FulfillmentOrderLineItem"), remaining, line_gid))
        next_cursor = _cursor(page_info.get("endCursor"))
        if page_info["hasNextPage"] and next_cursor is None:
            _fail("Shopify fulfillment-order line page omitted its next cursor.")
        return FulfillmentPageDTO(tuple(lines), page_info["hasNextPage"], next_cursor)

    def read_fulfillment_orders(self, order_gid: str) -> tuple[FulfillmentOrderDTO, ...]:
        cursor: str | None = None
        seen: set[str] = set()
        result: list[FulfillmentOrderDTO] = []
        for _ in range(self.max_pages):
            page = self.read_fulfillment_orders_page(order_gid, cursor)
            for item in page.items:
                if item.id in seen:
                    _fail("Shopify fulfillment-order pagination returned a duplicate identity.")
                seen.add(item.id)
                line_cursor: str | None = None
                lines: list[FulfillmentOrderLineDTO] = []
                for _line_page in range(self.max_pages):
                    line_page = self.read_fulfillment_order_lines_page(item.id, line_cursor)
                    lines.extend(line_page.items)
                    if not line_page.has_next_page:
                        break
                    if line_page.next_cursor == line_cursor:
                        _fail("Shopify fulfillment-order line pagination repeated a cursor.")
                    line_cursor = line_page.next_cursor
                else:
                    _fail("Shopify fulfillment-order line pagination exceeded its safety cap.")
                result.append(FulfillmentOrderDTO(item.id, item.status, item.request_status, item.assigned_location, item.supported_actions, tuple(lines)))
            if not page.has_next_page:
                return tuple(result)
            if page.next_cursor == cursor:
                _fail("Shopify fulfillment-order pagination repeated a cursor.")
            cursor = page.next_cursor
        _fail("Shopify fulfillment-order pagination exceeded its safety cap.")

    def read_order_fulfillments(self, order_gid: str) -> tuple[FulfillmentRecordDTO, ...]:
        order_gid = _gid(order_gid, "Order")
        data = _data(_read_once(self._delegate, ORDER_FULFILLMENTS_OPERATION, {"orderId": order_gid}))
        order = data.get("order")
        if not isinstance(order, Mapping) or order.get("id") != order_gid or not isinstance(order.get("fulfillments"), list):
            _fail("Shopify returned an invalid Order.fulfillments shape.")
        fulfillments = order["fulfillments"]
        if len(fulfillments) >= 250:
            _fail("Shopify fulfillment list reached its supported completeness bound.")
        result: list[FulfillmentRecordDTO] = []
        for node in fulfillments:
            result.append(self._record(node, require_lines=True))
        return tuple(result)

    def _record(self, node: Any, *, require_lines: bool = False) -> FulfillmentRecordDTO:
        if not isinstance(node, Mapping):
            _fail("Shopify returned a malformed Fulfillment record.")
        line_items: tuple[Mapping[str, Any], ...] = ()
        line_items_page_info: Mapping[str, Any] | None = None
        if require_lines:
            connection = node.get("fulfillmentLineItems")
            if not isinstance(connection, Mapping):
                _fail("Shopify fulfillment line connection is malformed.")
            page_info = connection.get("pageInfo")
            if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
                _fail("Shopify fulfillment line pageInfo is malformed.")
            if page_info["hasNextPage"]:
                _fail("A fulfillment has more line items than the supported one-page bound.")
            line_items_page_info = dict(page_info)
            nodes = connection.get("nodes")
            if not isinstance(nodes, list):
                _fail("Shopify fulfillment line nodes are malformed.")
            line_items = tuple(freeze_value(dict(item)) for item in nodes if isinstance(item, Mapping))
            if len(line_items) != len(nodes):
                _fail("Shopify fulfillment line node is malformed.")
        tracking = node.get("trackingInfo")
        if tracking is not None and not isinstance(tracking, Mapping):
            _fail("Shopify fulfillment trackingInfo shape is malformed.")
        return FulfillmentRecordDTO(
            _gid(node.get("id"), "Fulfillment"),
            _safe_text(node.get("status"), "status"),
            _safe_text(node.get("displayStatus"), "displayStatus"),
            tracking,
            line_items,
            require_lines,
            line_items_page_info,
        )

    def read_fulfillment(self, fulfillment_gid: str) -> FulfillmentRecordDTO | None:
        fulfillment_gid = _gid(fulfillment_gid, "Fulfillment")
        data = _data(_read_once(self._delegate, FULFILLMENT_NODE_OPERATION, {"id": fulfillment_gid}))
        if "fulfillment" not in data:
            _fail("Shopify fulfillment node response omitted the node field.")
        node = data["fulfillment"]
        return None if node is None else self._record(node)

    def read_fulfillments_batch(self, fulfillment_gids: list[str] | tuple[str, ...]) -> dict[str, FulfillmentRecordDTO | None]:
        if (
            isinstance(fulfillment_gids, (str, bytes, Mapping))
            or not isinstance(fulfillment_gids, (list, tuple))
        ):
            _fail("Fulfillment batch identities must be a bounded sequence.", "validation_error")
        if len(fulfillment_gids) > MAX_BATCH_ITEMS:
            _fail("Fulfillment batch exceeded its supported size.", "validation_error")
        requested = list(dict.fromkeys(_gid(value, "Fulfillment") for value in fulfillment_gids))
        if not requested:
            return {}
        result: dict[str, FulfillmentRecordDTO | None] = {}
        for offset in range(0, len(requested), MAX_BATCH):
            batch = requested[offset : offset + MAX_BATCH]
            data = _data(_read_once(self._delegate, FULFILLMENT_NODES_OPERATION, {"ids": batch}))
            nodes = data.get("nodes")
            if not isinstance(nodes, list) or len(nodes) != len(batch):
                _fail("Shopify returned an invalid fulfillment nodes batch.")
            for expected, node in zip(batch, nodes):
                result[expected] = None if node is None else self._record(node)
                if node is not None and result[expected] is not None and result[expected].id != expected:
                    _fail("Shopify fulfillment nodes batch did not preserve identity.")
        return result

    def read_locations_page(self, cursor: str | None = None) -> FulfillmentPageDTO:
        _cursor(cursor)
        data = _data(_read_once(self._delegate, LOCATIONS_OPERATION, {"cursor": cursor}))
        connection = data.get("locations")
        if not isinstance(connection, Mapping) or not isinstance(connection.get("nodes"), list):
            _fail("Shopify fulfillment locations connection is malformed.")
        if len(connection["nodes"]) > DEFAULT_PAGE_SIZE:
            _fail("Shopify fulfillment locations page exceeded its supported size.")
        page_info = connection.get("pageInfo")
        if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
            _fail("Shopify fulfillment locations pageInfo is malformed.")
        locations: list[FulfillmentLocationDTO] = []
        for node in connection["nodes"]:
            if not isinstance(node, Mapping):
                _fail("Shopify fulfillment location node is malformed.")
            if not isinstance(node.get("isActive"), bool):
                _fail("Shopify fulfillment location isActive shape is malformed.")
            locations.append(FulfillmentLocationDTO(_gid(node.get("id"), "Location"), _safe_text(node.get("name"), "location name", allow_none=False) or "", node["isActive"]))
        next_cursor = _cursor(page_info.get("endCursor"))
        if page_info["hasNextPage"] and next_cursor is None:
            _fail("Shopify fulfillment locations page omitted its next cursor.")
        return FulfillmentPageDTO(tuple(locations), page_info["hasNextPage"], next_cursor)


__all__ = ["DEFAULT_PAGE_SIZE", "FULFILLMENT_NODE_OPERATION", "FULFILLMENT_NODE_QUERY", "FULFILLMENT_NODES_OPERATION", "FULFILLMENT_NODES_QUERY", "FULFILLMENT_ORDER_LINES_OPERATION", "FULFILLMENT_ORDER_LINES_QUERY", "FULFILLMENT_ORDERS_OPERATION", "FULFILLMENT_ORDERS_QUERY", "FulfillmentLocationDTO", "FulfillmentOrderDTO", "FulfillmentOrderLineDTO", "FulfillmentPageDTO", "FulfillmentReadDelegate", "FulfillmentReadError", "FulfillmentReadGateway", "FulfillmentRecordDTO", "LOCATIONS_OPERATION", "LOCATIONS_QUERY", "MAX_BATCH", "MAX_BATCH_ITEMS", "MAX_PAGES", "ORDER_FULFILLMENTS_OPERATION", "ORDER_FULFILLMENTS_QUERY", "READ_OPERATION_KEYS"]
