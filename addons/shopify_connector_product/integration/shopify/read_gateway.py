"""Typed product/variant reads over the existing Shopify query documents.

No GraphQL text is defined here.  The operation descriptors name the exact
queries already present in ``shopify_connector_product.models``; callers inject
those checked-in documents into :class:`ReadCompatibilityAdapter`.  The
gateway is read-only and deliberately leaves matching, binding and export
policy to their existing owners.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any

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


PRODUCT_SCAN_OPERATION = ReadOperation(
    "ConnectorProductScan",
    variables=("first", "after", "query"),
    required_variables=("first", "query"),
    page_size=100,
    max_pages=10,
    max_items=1000,
)
PRODUCT_READ_OPERATION = ReadOperation(
    "ConnectorProductImport",
    variables=("id", "cursor"),
    required_variables=("id",),
    page_size=100,
    # 2,048 variants at Shopify's checked-in page size of 100 require no
    # more than 21 pages.  Keeping the ceiling tied to the item bound avoids
    # accepting an effectively unbounded connection on malformed responses.
    max_pages=21,
    max_items=2048,
)


def _mapping(value: Any, field_name: str, *, optional: bool = False) -> Mapping[str, Any] | None:
    if value is None or value is False:
        if optional:
            return None
        raise ReadShapeError("missing_field", f"Shopify product read omitted {field_name}.")
    if not isinstance(value, Mapping):
        raise ReadShapeError("invalid_shape", f"Shopify product read returned invalid {field_name}.")
    return value


def _text(value: Any, field_name: str, *, required: bool = False) -> str | None:
    if value is None or value is False:
        if required:
            raise ReadShapeError("missing_field", f"Shopify product read omitted {field_name}.")
        return None
    if not isinstance(value, str):
        raise ReadShapeError("invalid_shape", f"Shopify product read returned invalid {field_name}.")
    value = value.strip()
    if required and not value:
        raise ReadShapeError("missing_field", f"Shopify product read omitted {field_name}.")
    return value or None


def _optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify product read returned invalid {field_name}.")
    return value


def _optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify product read returned invalid {field_name}.")
    if value == "":
        return None
    if not isinstance(value, int):
        raise ReadShapeError("invalid_shape", f"Shopify product read returned invalid {field_name}.")
    return value


def _price(value: Any) -> float | None:
    """Mirror the V1 product normalizer's optional decimal-to-float rule."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ReadShapeError("invalid_shape", "Shopify product read returned an invalid price.")
    if value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _selected_options(value: Any) -> tuple["SelectedOptionDTO", ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ReadShapeError("invalid_shape", "Shopify product read returned invalid selectedOptions.")
    result = []
    for option in value:
        option = _mapping(option, "selectedOptions item")
        result.append(SelectedOptionDTO(_text(option.get("name"), "selectedOptions.name"), _text(option.get("value"), "selectedOptions.value")))
    # Shopify's singleton transport option is not a business option in V1.
    if len(result) == 1 and (result[0].name or "").strip().lower() == "title" and (result[0].value or "").strip().lower() == "default title":
        return ()
    return tuple(result)


def _option_specs(value: Any) -> tuple["ProductOptionDTO", ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ReadShapeError("invalid_shape", "Shopify product read returned invalid options.")
    options: list[ProductOptionDTO] = []
    for raw in value:
        option = _mapping(raw, "options item")
        values = option.get("optionValues")
        if values is None:
            values = []
        if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Sequence):
            raise ReadShapeError("invalid_shape", "Shopify product read returned invalid optionValues.")
        option_values = tuple(
            ProductOptionValueDTO(_text(_mapping(item, "optionValues item").get("id"), "optionValues.id"), _text(_mapping(item, "optionValues item").get("name"), "optionValues.name", required=True))
            for item in values
        )
        options.append(
            ProductOptionDTO(
                _text(option.get("id"), "options.id"),
                _text(option.get("name"), "options.name"),
                _optional_int(option.get("position"), "options.position") or 0,
                option_values,
            )
        )
    # Match the existing normalization's deterministic Shopify-position order
    # and hide the conventional one-variant transport option.
    options.sort(key=lambda item: item.position)
    if len(options) == 1 and (options[0].name or "").strip().lower() == "title" and tuple((item.name or "").strip().lower() for item in options[0].values) == ("default title",):
        return ()
    return tuple(options)


@dataclass(frozen=True, slots=True)
class SelectedOptionDTO:
    name: str | None
    value: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _text(self.name, "selected_option.name"))
        object.__setattr__(self, "value", _text(self.value, "selected_option.value"))

    def as_dict(self) -> dict[str, str | None]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True, slots=True)
class ProductOptionValueDTO:
    gid: str | None
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "option_value.id"), "option_value.id", kind="ProductOptionValue")
            if self.gid is not None else None,
        )
        object.__setattr__(self, "name", _text(self.name, "option_value.name", required=True))

    def as_dict(self) -> dict[str, str | None]:
        return {"gid": self.gid, "name": self.name}


@dataclass(frozen=True, slots=True)
class ProductOptionDTO:
    gid: str | None
    name: str | None
    position: int
    values: tuple[ProductOptionValueDTO, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "option.id"), "option.id", kind="ProductOption")
            if self.gid is not None else None,
        )
        object.__setattr__(self, "name", _text(self.name, "option.name"))
        if isinstance(self.position, bool) or not isinstance(self.position, int) or self.position < 0:
            raise ValueError("option.position must be a non-negative integer")
        if any(not isinstance(value, ProductOptionValueDTO) for value in self.values):
            raise TypeError("option.values must contain ProductOptionValueDTO values")
        object.__setattr__(self, "values", tuple(self.values))

    def as_dict(self) -> dict[str, Any]:
        return {"gid": self.gid, "name": self.name, "position": self.position, "values": [item.as_dict() for item in self.values]}


@dataclass(frozen=True, slots=True)
class VariantDTO:
    gid: str
    sku: str | None
    barcode: str | None
    price: float | None
    compare_at_price: float | None
    selected_options: tuple[SelectedOptionDTO, ...]
    option_values: str | None
    image_url: str | None
    inventory_item_gid: str | None
    inventory_tracked: bool | None
    inventory_tracked_known: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "variant.id", required=True), "variant.id", kind="ProductVariant"),
        )
        for name in ("sku", "barcode", "option_values", "image_url", "inventory_item_gid"):
            object.__setattr__(self, name, _text(getattr(self, name), f"variant.{name}"))
        if self.inventory_item_gid is not None:
            object.__setattr__(
                self,
                "inventory_item_gid",
                shopify_gid(self.inventory_item_gid, "variant.inventoryItem.id", kind="InventoryItem"),
            )
        for name in ("price", "compare_at_price"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f"variant.{name} must be a finite number or None")
        if any(not isinstance(item, SelectedOptionDTO) for item in self.selected_options):
            raise TypeError("variant.selected_options must contain SelectedOptionDTO values")
        object.__setattr__(self, "selected_options", tuple(self.selected_options))
        if not isinstance(self.inventory_tracked_known, bool):
            raise TypeError("variant.inventory_tracked_known must be bool")
        if self.inventory_tracked_known and not isinstance(self.inventory_tracked, bool):
            raise TypeError("known inventory tracking must be bool")
        if not self.inventory_tracked_known and self.inventory_tracked is not None:
            raise ValueError("unknown inventory tracking must be None")

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "sku": self.sku,
            "barcode": self.barcode,
            "price": self.price,
            "compare_at_price": self.compare_at_price,
            "selected_options": [item.as_dict() for item in self.selected_options],
            "option_values": self.option_values,
            "image_url": self.image_url,
            "inventory_item_gid": self.inventory_item_gid,
            "inventory_tracked": self.inventory_tracked,
            "inventory_tracked_known": self.inventory_tracked_known,
        }


@dataclass(frozen=True, slots=True)
class ProductSummaryDTO:
    gid: str
    updated_at: str
    status: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "product.id", required=True), "product.id", kind="Product"),
        )
        object.__setattr__(self, "updated_at", _text(self.updated_at, "product.updatedAt", required=True))
        object.__setattr__(self, "status", _text(self.status, "product.status"))

    def as_dict(self) -> dict[str, str | None]:
        return {"gid": self.gid, "updated_at": self.updated_at, "status": self.status}


@dataclass(frozen=True, slots=True)
class ProductDTO:
    gid: str
    title: str | None
    status: str | None
    description_html: str | None
    vendor: str | None
    product_type: str | None
    tags: tuple[str, ...] | None
    updated_at: str | None
    image_url: str | None
    options: tuple[ProductOptionDTO, ...]
    variants: ReadPage[VariantDTO]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "product.id", required=True), "product.id", kind="Product"),
        )
        for name in ("title", "status", "description_html", "vendor", "product_type", "updated_at", "image_url"):
            object.__setattr__(self, name, _text(getattr(self, name), f"product.{name}"))
        if self.tags is not None:
            if isinstance(self.tags, (str, bytes, Mapping)) or not isinstance(self.tags, Sequence):
                raise TypeError("product.tags must be a sequence")
            if any(not isinstance(item, str) for item in self.tags):
                raise TypeError("product.tags must contain strings")
            object.__setattr__(self, "tags", tuple(self.tags))
        if any(not isinstance(item, ProductOptionDTO) for item in self.options):
            raise TypeError("product.options must contain ProductOptionDTO values")
        object.__setattr__(self, "options", tuple(self.options))
        if not isinstance(self.variants, ReadPage):
            raise TypeError("product.variants must be ReadPage")

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "title": self.title,
            "status": self.status,
            "description_html": self.description_html,
            "vendor": self.vendor,
            "product_type": self.product_type,
            "tags": list(self.tags) if self.tags is not None else None,
            "updated_at": self.updated_at,
            "image_url": self.image_url,
            "options": [item.as_dict() for item in self.options],
            "variants": self.variants.as_dict(),
        }


def _edge_list(connection: Mapping[str, Any], field_name: str) -> list[Mapping[str, Any]]:
    edges = connection.get("edges")
    if not isinstance(edges, (list, tuple)):
        raise ReadShapeError("invalid_shape", f"Shopify product read omitted {field_name}.edges.")
    result: list[Mapping[str, Any]] = []
    cursors: set[str] = set()
    for edge in edges:
        edge = _mapping(edge, f"{field_name} edge")
        edge_cursor = _text(edge.get("cursor"), f"{field_name}.edge.cursor", required=True)
        if edge_cursor in cursors:
            raise ReadShapeError("cursor_loop", f"Shopify product read repeated a {field_name} edge cursor.")
        cursors.add(edge_cursor or "")
        result.append(_mapping(edge.get("node"), f"{field_name}.edge.node") or {})
    return result


class ProductReadGateway:
    """One-call-per-page product and variant read facade."""

    def __init__(self, adapter: ReadCompatibilityAdapter) -> None:
        if not isinstance(adapter, ReadCompatibilityAdapter):
            raise TypeError("adapter must be ReadCompatibilityAdapter")
        self.adapter = adapter

    def read_product_page(
        self,
        store: Any,
        *,
        query: str = "",
        cursor: str | None = None,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ReadPage[ProductSummaryDTO]]:
        if not isinstance(query, str):
            raise TypeError("product scan query must be a string")
        cursor = shopify_cursor(cursor)
        response = self.adapter.execute(
            store,
            PRODUCT_SCAN_OPERATION,
            {"first": PRODUCT_SCAN_OPERATION.page_size, "after": cursor, "query": query},
        )
        data, observation = response_data(response, PRODUCT_SCAN_OPERATION.operation_name)
        products = _mapping(data.get("products"), "products")
        items = tuple(
            ProductSummaryDTO(
                _mapping(node, "product").get("id"),
                _mapping(node, "product").get("updatedAt"),
                _mapping(node, "product").get("status"),
            )
            for node in _edge_list(products, "products")
        )
        active_progress = progress or CursorProgress(
            max_pages=PRODUCT_SCAN_OPERATION.max_pages,
            max_items=PRODUCT_SCAN_OPERATION.max_items,
        )
        active_progress.accept_identities(tuple(item.gid for item in items))
        page = page_from_connection(
            PRODUCT_SCAN_OPERATION,
            cursor=cursor,
            page_info=_mapping(products.get("pageInfo"), "products.pageInfo"),
            items=items,
            observation=observation,
            progress=active_progress,
        )
        return ReadResult(page, PRODUCT_SCAN_OPERATION.operation_name, observation)

    def read_product(
        self,
        store: Any,
        product_gid: str,
        *,
        cursor: str | None = None,
        progress: CursorProgress | None = None,
    ) -> ReadResult[ProductDTO | None]:
        cursor = shopify_cursor(cursor)
        product_gid = shopify_gid(product_gid, "product_gid", kind="Product")
        response = self.adapter.execute(
            store,
            PRODUCT_READ_OPERATION,
            {"id": product_gid, "cursor": cursor},
        )
        data, observation = response_data(response, PRODUCT_READ_OPERATION.operation_name)
        product = data.get("product")
        if product is None:
            return ReadResult(None, PRODUCT_READ_OPERATION.operation_name, observation)
        product = _mapping(product, "product")
        if product.get("id") != product_gid:
            raise ReadShapeError("identity_mismatch", "Shopify product read returned the wrong product identity.")
        variants = _mapping(product.get("variants"), "product.variants")
        variant_nodes = variants.get("nodes")
        if not isinstance(variant_nodes, (list, tuple)):
            raise ReadShapeError("invalid_shape", "Shopify product read returned invalid variants.nodes.")
        variant_items = tuple(self._variant(node) for node in variant_nodes)
        active_progress = progress or CursorProgress(
            max_pages=PRODUCT_READ_OPERATION.max_pages,
            max_items=PRODUCT_READ_OPERATION.max_items,
        )
        active_progress.accept_identities(tuple(item.gid for item in variant_items))
        tags = product.get("tags")
        if tags is not None and (isinstance(tags, (str, bytes, Mapping)) or not isinstance(tags, Sequence)):
            raise ReadShapeError("invalid_shape", "Shopify product read returned invalid product.tags.")
        normalized_tags = (
            tuple(_text(item, "product.tags item", required=True) or "" for item in tags)
            if tags is not None else None
        )
        variant_page = page_from_connection(
            PRODUCT_READ_OPERATION,
            cursor=cursor,
            page_info=_mapping(variants.get("pageInfo"), "product.variants.pageInfo"),
            items=variant_items,
            observation=observation,
            progress=active_progress,
        )
        featured = _mapping(product.get("featuredImage"), "product.featuredImage", optional=True)
        value = ProductDTO(
            product.get("id"),
            product.get("title"),
            (product.get("status") or "").lower() or None,
            product.get("descriptionHtml"),
            product.get("vendor"),
            product.get("productType"),
            normalized_tags,
            product.get("updatedAt"),
            featured.get("url") if featured else None,
            _option_specs(product.get("options")),
            variant_page,
        )
        return ReadResult(value, PRODUCT_READ_OPERATION.operation_name, observation)

    def _variant(self, raw: Any) -> VariantDTO:
        variant = _mapping(raw, "variant")
        selected = _selected_options(variant.get("selectedOptions"))
        inventory = _mapping(variant.get("inventoryItem"), "variant.inventoryItem", optional=True)
        option_values = " / ".join(
            f"{item.name}: {item.value}" for item in selected if item.name and item.value
        ) or None
        tracked = inventory.get("tracked") if inventory else None
        known = isinstance(tracked, bool)
        return VariantDTO(
            variant.get("id"),
            variant.get("sku") or None,
            variant.get("barcode") or None,
            _price(variant.get("price")),
            _price(variant.get("compareAtPrice")),
            selected,
            option_values,
            (_mapping(variant.get("image"), "variant.image", optional=True) or {}).get("url"),
            (inventory or {}).get("id"),
            tracked if known else None,
            known,
        )


__all__ = [
    "PRODUCT_READ_OPERATION",
    "PRODUCT_SCAN_OPERATION",
    "ProductDTO",
    "ProductOptionDTO",
    "ProductOptionValueDTO",
    "ProductReadGateway",
    "ProductSummaryDTO",
    "SelectedOptionDTO",
    "VariantDTO",
]
