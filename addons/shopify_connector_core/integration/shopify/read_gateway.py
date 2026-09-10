"""Core store/capability/location read gateway contracts.

The operation names below are references to existing checked-in GraphQL
documents.  The documents themselves are injected by the owning runtime so
this pure layer cannot invent fields or issue a request.  Each public method
performs one adapter call and returns only normalized DTOs.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .read_contracts import (
    CursorProgress,
    LocationDTO,
    ReadCompatibilityAdapter,
    ReadOperation,
    ReadPage,
    ReadResult,
    ReadShapeError,
    StoreCapabilityDTO,
    StoreIdentityDTO,
    page_from_connection,
    response_data,
    shopify_cursor,
)


STORE_CAPABILITY_OPERATION = ReadOperation(
    "ConnectorTestConnection",
)
LOCATION_PAGE_OPERATION = ReadOperation(
    "ConnectorFulfillmentLocations",
    variables=("cursor",),
    max_pages=100,
    max_items=5000,
    page_size=50,
)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReadShapeError("invalid_shape", f"Shopify read omitted {field_name}.")
    return value


class StoreCapabilityReadGateway:
    """Normalize the existing shop identity and access-scope query."""

    def __init__(self, adapter: ReadCompatibilityAdapter) -> None:
        if not isinstance(adapter, ReadCompatibilityAdapter):
            raise TypeError("adapter must be ReadCompatibilityAdapter")
        self.adapter = adapter

    def read(self, store: Any) -> ReadResult[StoreCapabilityDTO]:
        response = self.adapter.execute(store, STORE_CAPABILITY_OPERATION, {})
        data, observation = response_data(response, STORE_CAPABILITY_OPERATION.operation_name)
        shop = _mapping(data.get("shop"), "shop")
        installation = _mapping(data.get("currentAppInstallation"), "currentAppInstallation")
        scopes = installation.get("accessScopes")
        if not isinstance(scopes, (list, tuple)):
            raise ReadShapeError("invalid_shape", "Shopify read returned invalid access scopes.")
        handles: list[str] = []
        for scope in scopes:
            scope = _mapping(scope, "accessScopes item")
            handle = scope.get("handle")
            if not isinstance(handle, str) or not handle.strip():
                raise ReadShapeError("invalid_shape", "Shopify read returned an invalid scope handle.")
            handles.append(handle.strip())
        value = StoreCapabilityDTO(
            StoreIdentityDTO(shop.get("id"), shop.get("name"), shop.get("myshopifyDomain")),
            tuple(handles),
            observation.served_version,
        )
        return ReadResult(value, STORE_CAPABILITY_OPERATION.operation_name, observation)


class LocationReadGateway:
    """Normalize bounded Shopify location pages without mutating local cache."""

    def __init__(self, adapter: ReadCompatibilityAdapter) -> None:
        if not isinstance(adapter, ReadCompatibilityAdapter):
            raise TypeError("adapter must be ReadCompatibilityAdapter")
        self.adapter = adapter

    def read_page(
        self,
        store: Any,
        *,
        cursor: str | None = None,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ReadPage[LocationDTO]]:
        cursor = shopify_cursor(cursor)
        response = self.adapter.execute(
            store,
            LOCATION_PAGE_OPERATION,
            {"cursor": cursor},
        )
        data, observation = response_data(response, LOCATION_PAGE_OPERATION.operation_name)
        locations = _mapping(data.get("locations"), "locations")
        nodes = locations.get("nodes")
        if not isinstance(nodes, (list, tuple)):
            raise ReadShapeError("invalid_shape", "Shopify locations read returned invalid nodes.")
        items = tuple(
            LocationDTO(
                _mapping(node, "location").get("id"),
                _mapping(node, "location").get("name"),
                _mapping(node, "location").get("isActive"),
            )
            for node in nodes
        )
        page = page_from_connection(
            LOCATION_PAGE_OPERATION,
            cursor=cursor,
            page_info=_mapping(locations.get("pageInfo"), "locations.pageInfo"),
            items=items,
            observation=observation,
            progress=progress,
        )
        return ReadResult(page, LOCATION_PAGE_OPERATION.operation_name, observation)


__all__ = [
    "LOCATION_PAGE_OPERATION",
    "LocationReadGateway",
    "STORE_CAPABILITY_OPERATION",
    "StoreCapabilityReadGateway",
]
