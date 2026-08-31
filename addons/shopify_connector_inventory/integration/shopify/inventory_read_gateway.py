"""Typed, bounded Shopify reads owned by the inventory domain.

This module is intentionally an adapter-sized seam.  It knows the checked-in
read documents and the shapes returned by the V1 inventory readers, but it does
not know Odoo models, jobs, credentials or mutation policy.  A caller supplies
one already-authorized ``delegate``.  Each page method invokes that delegate
exactly once; retries, leases and commits belong to the runtime above it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from odoo.addons.shopify_connector_core.domain.immutability import freeze_value, to_plain

from .inventory_documents import INVENTORY_PAIR_QUERY


SHOPIFY_API_VERSION = "2026-07"
MAX_PAGE_SIZE = 100
MAX_PAGES = 100
MAX_CURSOR_LENGTH = 512

INVENTORY_PAIR_OPERATION = "inventory_pair_read"
INVENTORY_LEVEL_OPERATION = "inventory_observation"
LOCATIONS_OPERATION = "inventory_locations"
READ_OPERATION_KEYS = frozenset(
    (INVENTORY_PAIR_OPERATION, INVENTORY_LEVEL_OPERATION, LOCATIONS_OPERATION)
)

INVENTORY_LEVEL_QUERY = (
    "query InventoryObservation($levelId: ID!) { "
    "inventoryLevel(id: $levelId) { id item { id tracked } location { id } "
    "quantities(names: [\"available\"]) { name quantity updatedAt } } "
    "shop { myshopifyDomain } }"
)

LOCATIONS_QUERY = (
    "query LocationsSync($cursor: String) { locations(first: 100, "
    "after: $cursor, includeInactive: false) { edges { cursor node { id name } } "
    "pageInfo { hasNextPage } } }"
)

_SHOP_DOMAIN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$"
)
_SIMPLE_GID = re.compile(r"^gid://shopify/(?P<kind>[A-Za-z][A-Za-z0-9_]*)/(?P<id>[1-9][0-9]*)$")
_LEVEL_GID = re.compile(
    r"^gid://shopify/InventoryLevel/(?P<level>[1-9][0-9]*)"
    r"\?inventory_item_id=(?P<item>[1-9][0-9]*)$"
)


class InventoryReadDelegate(Protocol):
    """The already-authorized one-page read boundary supplied by runtime."""

    def read(self, operation_key: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class InventoryReadError(ValueError):
    """A read was not complete or did not match the declared contract."""

    def __init__(self, message: str, code: str = "data_shape_schema_mismatch") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(message: str, code: str = "data_shape_schema_mismatch") -> None:
    raise InventoryReadError(message, code)


def _shop_domain(value: Any) -> str:
    if not isinstance(value, str) or not _SHOP_DOMAIN.fullmatch(value):
        _fail("Shopify returned a missing or malformed shop identity.")
    return value


def _simple_gid(value: Any, kind: str) -> str:
    if not isinstance(value, str):
        _fail("Shopify returned a non-string %s identity." % kind)
    match = _SIMPLE_GID.fullmatch(value)
    if not match or match.group("kind") != kind:
        _fail("Shopify returned a malformed %s GID." % kind)
    return value


def _level_gid(value: Any) -> tuple[str, str]:
    if not isinstance(value, str):
        _fail("Shopify returned a non-string InventoryLevel GID.")
    match = _LEVEL_GID.fullmatch(value)
    if not match:
        _fail("Shopify returned a malformed InventoryLevel GID.")
    return match.group("level"), match.group("item")


def _cursor(value: Any, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value or len(value) > MAX_CURSOR_LENGTH:
        _fail("Shopify returned a malformed pagination cursor.")
    return value


def _timestamp(value: Any, *, required: bool) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail("Shopify returned a missing inventory quantity timestamp.")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError, OverflowError):
        _fail("Shopify returned a malformed inventory quantity timestamp.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail("Shopify inventory quantity timestamp must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(response, Mapping):
        _fail("Shopify inventory read returned an invalid response envelope.")
    errors = response.get("errors")
    if "errors" in response:
        if (
            not isinstance(errors, (list, tuple))
            or any(not isinstance(item, Mapping) for item in errors)
        ):
            _fail("Shopify inventory read returned malformed errors.")
        if errors:
            _fail("Shopify rejected the inventory read.", "remote_error")
    extensions = response.get("extensions")
    if extensions is not None and not isinstance(extensions, Mapping):
        _fail("Shopify inventory read returned malformed extensions.")
    if isinstance(extensions, Mapping):
        cost = extensions.get("cost")
        if cost is not None and not isinstance(cost, Mapping):
            _fail("Shopify inventory read returned malformed cost telemetry.")
    served = response.get("served_version", response.get("servedVersion"))
    if served != SHOPIFY_API_VERSION:
        _fail(
            "Shopify inventory read was not served by the pinned API version.",
            "api_version_mismatch",
        )
    if not isinstance(response.get("data"), Mapping):
        _fail("Shopify inventory read returned no data object.")
    return response["data"]


def _read_once(
    delegate: InventoryReadDelegate | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
    operation_key: str,
    variables: Mapping[str, Any],
) -> Mapping[str, Any]:
    if operation_key not in READ_OPERATION_KEYS:
        _fail("Inventory read operation is not allowlisted.", "invalid_operation")
    try:
        frozen = freeze_value(dict(variables))
    except (TypeError, ValueError) as exc:
        raise InventoryReadError("Inventory read variables are malformed.", "validation_error") from exc
    plain = to_plain(frozen)
    try:
        if hasattr(delegate, "read"):
            result = delegate.read(operation_key, plain)
        else:
            result = delegate(operation_key, plain)
    except InventoryReadError:
        raise
    except Exception as exc:  # pragma: no cover - caller-specific transport
        raise InventoryReadError("Shopify inventory read could not be completed.", "shopify_unavailable") from exc
    if not isinstance(result, Mapping):
        _fail("Inventory read delegate returned a non-mapping response.")
    return result


@dataclass(frozen=True, slots=True)
class InventoryPairDTO:
    """Normalized equivalent of V1 ``_inventory_pair_read_result``."""

    store_identity: str
    item_exists: bool
    tracked: bool | None
    level_exists: bool
    inventory_level_gid: str | None
    available: int | None
    updated_at: str | None

    def __post_init__(self) -> None:
        _shop_domain(self.store_identity)
        for name in ("item_exists", "level_exists"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError("%s must be bool" % name)
        if self.tracked is not None and not isinstance(self.tracked, bool):
            raise TypeError("tracked must be bool or None")
        if not self.item_exists and (self.tracked is not None or self.level_exists):
            raise ValueError("a missing inventory item cannot have level state")
        if self.level_exists:
            if not self.inventory_level_gid or self.available is None:
                raise ValueError("an existing inventory level needs identity and quantity")
            _level_gid(self.inventory_level_gid)
            if isinstance(self.available, bool) or not isinstance(self.available, int):
                raise TypeError("available must be an integer or None")
        elif self.inventory_level_gid is not None or self.available is not None:
            raise ValueError("a missing inventory level cannot have level data")
        if self.updated_at is not None and not isinstance(self.updated_at, str):
            raise TypeError("updated_at must be a string or None")

    def to_legacy_dict(self) -> dict[str, Any]:
        """Return the exact key vocabulary emitted by the V1 pair reader."""
        return {
            "store_identity": self.store_identity,
            "item_exists": self.item_exists,
            "tracked": self.tracked,
            "level_exists": self.level_exists,
            "inventory_level_gid": self.inventory_level_gid,
            "available": self.available,
            "updated_at": self.updated_at or False,
        }


@dataclass(frozen=True, slots=True)
class InventoryLevelDTO:
    """Normalized equivalent of the webhook observation read output."""

    store_domain: str
    inventory_level_gid: str
    inventory_item_gid: str
    location_gid: str
    tracked: bool
    available: int
    source_updated_at: datetime

    def __post_init__(self) -> None:
        _shop_domain(self.store_domain)
        _level_gid(self.inventory_level_gid)
        _simple_gid(self.inventory_item_gid, "InventoryItem")
        _simple_gid(self.location_gid, "Location")
        if not isinstance(self.tracked, bool):
            raise TypeError("tracked must be bool")
        if isinstance(self.available, bool) or not isinstance(self.available, int):
            raise TypeError("available must be a strict integer")
        if not isinstance(self.source_updated_at, datetime) or self.source_updated_at.tzinfo is None:
            raise TypeError("source_updated_at must be timezone-aware")

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "store_domain": self.store_domain,
            "inventory_level_gid": self.inventory_level_gid,
            "inventory_item_gid": self.inventory_item_gid,
            "location_gid": self.location_gid,
            "tracked": self.tracked,
            "available": self.available,
            "source_updated_at": self.source_updated_at,
        }


@dataclass(frozen=True, slots=True)
class InventoryLocationDTO:
    gid: str
    name: str
    cursor: str | None = None

    def __post_init__(self) -> None:
        _simple_gid(self.gid, "Location")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("location name must be non-empty")
        _cursor(self.cursor, required=False)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {"gid": self.gid, "name": self.name, "cursor": self.cursor}


@dataclass(frozen=True, slots=True)
class InventoryLocationPageDTO:
    items: tuple[InventoryLocationDTO, ...]
    has_next_page: bool
    next_cursor: str | None
    store_domain: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        if any(not isinstance(item, InventoryLocationDTO) for item in self.items):
            raise TypeError("items must contain InventoryLocationDTO values")
        if not isinstance(self.has_next_page, bool):
            raise TypeError("has_next_page must be bool")
        if self.store_domain is not None:
            _shop_domain(self.store_domain)
        if self.has_next_page:
            _cursor(self.next_cursor)
        elif self.next_cursor is not None:
            _cursor(self.next_cursor, required=False)

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "edges": [item.to_legacy_dict() for item in self.items],
            "has_next_page": self.has_next_page,
            "next_cursor": self.next_cursor,
        }


class InventoryReadGateway:
    """Allowlisted inventory read gateway with bounded cursor traversal."""

    operation_documents = {
        INVENTORY_PAIR_OPERATION: INVENTORY_PAIR_QUERY,
        INVENTORY_LEVEL_OPERATION: INVENTORY_LEVEL_QUERY,
        LOCATIONS_OPERATION: LOCATIONS_QUERY,
    }

    def __init__(
        self,
        delegate: InventoryReadDelegate | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
        *,
        store_domain: str | None = None,
        max_pages: int = MAX_PAGES,
    ) -> None:
        if not callable(delegate) and not hasattr(delegate, "read"):
            raise TypeError("delegate must provide one read operation")
        if store_domain is not None:
            _shop_domain(store_domain)
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_PAGES:
            raise ValueError("max_pages must be between 1 and %d" % MAX_PAGES)
        self._delegate = delegate
        self.store_domain = store_domain
        self.max_pages = max_pages

    def _check_store(self, observed: str) -> None:
        if self.store_domain and observed != self.store_domain:
            _fail("Shopify returned a different shop identity.", "store_identity_mismatch")

    def read_inventory_pair(self, item_gid: str, location_gid: str) -> InventoryPairDTO:
        item_gid = _simple_gid(item_gid, "InventoryItem")
        location_gid = _simple_gid(location_gid, "Location")
        response = _read_once(
            self._delegate,
            INVENTORY_PAIR_OPERATION,
            {"itemId": item_gid, "locationId": location_gid},
        )
        data = _data(response)
        if "shop" not in data or "inventoryItem" not in data:
            _fail("Shopify inventory pair response omitted required fields.")
        shop = data["shop"]
        if not isinstance(shop, Mapping):
            _fail("Shopify inventory pair shop shape is malformed.")
        store_identity = _shop_domain(shop.get("myshopifyDomain"))
        self._check_store(store_identity)
        item = data["inventoryItem"]
        if item is None:
            return InventoryPairDTO(store_identity, False, None, False, None, None, None)
        if not isinstance(item, Mapping) or item.get("id") != item_gid or not isinstance(item.get("tracked"), bool):
            _fail("Shopify inventory item identity or tracked shape is malformed.")
        level = item.get("inventoryLevel")
        if level is None:
            return InventoryPairDTO(store_identity, True, item["tracked"], False, None, None, None)
        if not isinstance(level, Mapping):
            _fail("Shopify inventory level shape is malformed.")
        level_gid = level.get("id")
        _level_number, embedded_item = _level_gid(level_gid)
        if embedded_item != item_gid.rsplit("/", 1)[1]:
            _fail("Shopify InventoryLevel does not match its requested item.")
        level_item = level.get("item")
        level_location = level.get("location")
        if not isinstance(level_item, Mapping) or level_item.get("id") != item_gid:
            _fail("Shopify inventory level item identity does not match the request.")
        if not isinstance(level_location, Mapping) or level_location.get("id") != location_gid:
            _fail("Shopify inventory level location identity does not match the request.")
        quantities = level.get("quantities")
        if not isinstance(quantities, list):
            _fail("Shopify inventory level quantities shape is malformed.")
        available: int | None = None
        updated_at: str | None = None
        for quantity in quantities:
            if not isinstance(quantity, Mapping):
                _fail("Shopify inventory quantity shape is malformed.")
            if quantity.get("name") != "available":
                continue
            if available is not None:
                _fail("Shopify returned more than one available quantity entry.")
            value = quantity.get("quantity")
            if isinstance(value, bool) or not isinstance(value, int):
                _fail("Shopify available quantity is not a strict integer.")
            available = value
            timestamp = quantity.get("updatedAt")
            if timestamp is not None and not isinstance(timestamp, str):
                _fail("Shopify inventory quantity timestamp is malformed.")
            updated_at = timestamp
        if available is None:
            _fail("Shopify inventory level has no available quantity entry.")
        return InventoryPairDTO(store_identity, True, item["tracked"], True, level_gid, available, updated_at)

    def read_inventory_level(self, level_gid: str) -> InventoryLevelDTO:
        _level_gid(level_gid)
        response = _read_once(self._delegate, INVENTORY_LEVEL_OPERATION, {"levelId": level_gid})
        data = _data(response)
        if "shop" not in data or "inventoryLevel" not in data:
            _fail("Shopify inventory observation response omitted required fields.")
        shop = data["shop"]
        if not isinstance(shop, Mapping):
            _fail("Shopify inventory observation shop shape is malformed.")
        store_domain = _shop_domain(shop.get("myshopifyDomain"))
        self._check_store(store_domain)
        level = data["inventoryLevel"]
        if not isinstance(level, Mapping) or level.get("id") != level_gid:
            _fail("Shopify returned a different or malformed InventoryLevel identity.")
        item = level.get("item")
        location = level.get("location")
        item_id = _simple_gid(item.get("id") if isinstance(item, Mapping) else None, "InventoryItem")
        location_id = _simple_gid(location.get("id") if isinstance(location, Mapping) else None, "Location")
        _level_number, embedded_item = _level_gid(level_gid)
        if embedded_item != item_id.rsplit("/", 1)[1]:
            _fail("Shopify InventoryLevel does not match its item identity.")
        if not isinstance(item, Mapping) or not isinstance(item.get("tracked"), bool):
            _fail("Shopify inventory item tracked shape is malformed.")
        quantities = level.get("quantities")
        if not isinstance(quantities, list) or len(quantities) != 1:
            _fail("Shopify returned an ambiguous available quantity list.")
        quantity = quantities[0]
        if not isinstance(quantity, Mapping) or quantity.get("name") != "available":
            _fail("Shopify returned no uniquely identified available quantity.")
        available = quantity.get("quantity")
        if isinstance(available, bool) or not isinstance(available, int):
            _fail("Shopify available quantity is not a strict integer.")
        updated_at = _timestamp(quantity.get("updatedAt"), required=True)
        if updated_at is None:  # pragma: no cover - required=True
            _fail("Shopify inventory quantity timestamp is missing.")
        return InventoryLevelDTO(
            store_domain,
            level_gid,
            item_id,
            location_id,
            item["tracked"],
            available,
            updated_at,
        )

    def read_locations_page(self, after: str | None = None) -> InventoryLocationPageDTO:
        _cursor(after, required=False)
        response = _read_once(self._delegate, LOCATIONS_OPERATION, {"cursor": after})
        data = _data(response)
        if "locations" not in data:
            _fail("Shopify locations response omitted required fields.")
        # V1's LocationsSync document intentionally does not request ``shop``.
        # The runtime's store-scoped lease remains the authority; use the
        # constructor's expected domain when supplied and do not change the
        # wire document merely to add a second identity read.
        store_domain = self.store_domain
        connection = data["locations"]
        if not isinstance(connection, Mapping) or not isinstance(connection.get("edges"), list):
            _fail("Shopify locations connection shape is malformed.")
        if len(connection["edges"]) > MAX_PAGE_SIZE:
            _fail("Shopify locations page exceeded its supported size.")
        page_info = connection.get("pageInfo")
        if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
            _fail("Shopify locations pageInfo shape is malformed.")
        items: list[InventoryLocationDTO] = []
        for edge in connection["edges"]:
            if not isinstance(edge, Mapping) or not isinstance(edge.get("node"), Mapping):
                _fail("Shopify locations edge shape is malformed.")
            node = edge["node"]
            gid = _simple_gid(node.get("id"), "Location")
            name = node.get("name")
            if name is None:
                name = gid
            if not isinstance(name, str) or not name:
                _fail("Shopify location name shape is malformed.")
            edge_cursor = _cursor(edge.get("cursor"), required=False)
            items.append(InventoryLocationDTO(gid, name, edge_cursor))
        has_next = page_info["hasNextPage"]
        next_cursor = None
        if has_next:
            if not items:
                _fail("Shopify locations page hasNextPage without an edge cursor.")
            next_cursor = _cursor(items[-1].cursor)
        return InventoryLocationPageDTO(tuple(items), has_next, next_cursor, store_domain)

    def read_all_locations(self, after: str | None = None) -> tuple[InventoryLocationDTO, ...]:
        """Read a complete location set, bounded by ``max_pages``.

        The returned tuple is complete only when Shopify reports
        ``hasNextPage=False``.  A repeated cursor, duplicate identity or page
        cap raises instead of turning a partial read into an absence proof.
        """
        cursor = _cursor(after, required=False)
        seen_cursors: set[str] = set()
        seen_gids: set[str] = set()
        result: list[InventoryLocationDTO] = []
        for _ in range(self.max_pages):
            page = self.read_locations_page(cursor)
            for item in page.items:
                if item.gid in seen_gids:
                    _fail("Shopify locations pagination returned a duplicate identity.")
                seen_gids.add(item.gid)
                result.append(item)
            if not page.has_next_page:
                return tuple(result)
            cursor = _cursor(page.next_cursor)
            if cursor in seen_cursors:
                _fail("Shopify locations pagination repeated a cursor.")
            seen_cursors.add(cursor)
        _fail("Shopify locations pagination exceeded its safety cap.")


__all__ = ["INVENTORY_LEVEL_OPERATION", "INVENTORY_LEVEL_QUERY", "INVENTORY_PAIR_OPERATION", "INVENTORY_PAIR_QUERY", "InventoryLevelDTO", "InventoryLocationDTO", "InventoryLocationPageDTO", "InventoryPairDTO", "InventoryReadDelegate", "InventoryReadError", "InventoryReadGateway", "LOCATIONS_OPERATION", "LOCATIONS_QUERY", "MAX_PAGES", "MAX_PAGE_SIZE", "READ_OPERATION_KEYS"]
