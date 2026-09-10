"""Immutable sale-domain evidence DTOs for the P06 read gateway.

The fields mirror the existing customer/order query documents and are
intentionally observation-only.  No DTO in this module can create, confirm,
cancel, refund, or otherwise mutate an Odoo or Shopify record.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
import re
from types import MappingProxyType
from typing import Any

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import MoneyDTO, ReadPage, ReadShapeError, shopify_gid


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


def _bool(value: Any, field_name: str, *, required: bool = False) -> bool | None:
    if value is None:
        if required:
            raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
        return None
    if not isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return value


def _int(value: Any, field_name: str, *, required: bool = False) -> int | None:
    if value is None:
        if required:
            raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
        return None
    if isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    if not isinstance(value, int):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return value


def _mapping(value: Any, field_name: str, *, optional: bool = False) -> Mapping[str, Any] | None:
    if value is None or value is False:
        if optional:
            return None
        raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
    if not isinstance(value, Mapping):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return value


def _sequence(value: Any, field_name: str, *, optional: bool = False) -> list[Any] | tuple[Any, ...]:
    if value is None:
        if optional:
            return ()
        raise ReadShapeError("missing_field", f"Shopify sale read omitted {field_name}.")
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, (list, tuple)):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return value


def _money_side(value: Any, field_name: str, *, optional: bool = True) -> MoneyDTO | None:
    node = _mapping(value, field_name, optional=optional)
    if node is None:
        return None
    amount = node.get("amount")
    currency = node.get("currencyCode")
    if amount is None and currency is None:
        return None
    if amount is None or currency is None:
        raise ReadShapeError(
            "invalid_shape",
            f"Shopify sale read returned an incomplete {field_name} money side.",
        )
    return MoneyDTO(_text(amount, f"{field_name}.amount"), _text(currency, f"{field_name}.currencyCode"))


_CURRENCY_CODE_RE = re.compile(r"^[A-Z]{3}$")


def _currency_code(value: Any, field_name: str) -> str:
    value = _text(value, field_name, required=True)
    if value is None or not _CURRENCY_CODE_RE.fullmatch(value):
        raise ReadShapeError(
            "invalid_shape",
            f"Shopify sale read returned an invalid {field_name}.",
        )
    return value


def _tax_rate(value: Any, field_name: str) -> str | None:
    """Keep V1's finite numeric tax evidence in a canonical string form."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
        parsed = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = Decimal(text)
        except (InvalidOperation, ValueError) as exc:
            raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.") from exc
    else:
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    if not parsed.is_finite():
        raise ReadShapeError("invalid_shape", f"Shopify sale read returned invalid {field_name}.")
    return format(parsed, "f")


@dataclass(frozen=True, slots=True)
class MoneySetDTO:
    shop_money: MoneyDTO | None
    presentment_money: MoneyDTO | None

    def __post_init__(self) -> None:
        if self.shop_money is not None and not isinstance(self.shop_money, MoneyDTO):
            raise TypeError("shop_money must be MoneyDTO or None")
        if self.presentment_money is not None and not isinstance(self.presentment_money, MoneyDTO):
            raise TypeError("presentment_money must be MoneyDTO or None")

    def as_dict(self) -> dict[str, Any]:
        return {
            "shop_money": self.shop_money.as_dict() if self.shop_money else None,
            "presentment_money": self.presentment_money.as_dict() if self.presentment_money else None,
        }


def money_set(value: Any, field_name: str, *, optional: bool = True) -> MoneySetDTO | None:
    node = _mapping(value, field_name, optional=optional)
    if node is None:
        return None
    return MoneySetDTO(
        _money_side(node.get("shopMoney"), f"{field_name}.shopMoney"),
        _money_side(node.get("presentmentMoney"), f"{field_name}.presentmentMoney"),
    )


@dataclass(frozen=True, slots=True)
class AddressEvidenceDTO:
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    zip: str | None = None
    province_code: str | None = None
    country_code: str | None = None
    phone: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "first_name", "last_name", "name", "address1", "address2", "city",
            "zip", "province_code", "country_code", "phone",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), f"address.{name}"))

    def as_dict(self) -> dict[str, str | None]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "name": self.name,
            "address1": self.address1,
            "address2": self.address2,
            "city": self.city,
            "zip": self.zip,
            "province_code": self.province_code,
            "country_code": self.country_code,
            "phone": self.phone,
        }


def address(value: Any, field_name: str, *, optional: bool = True) -> AddressEvidenceDTO | None:
    node = _mapping(value, field_name, optional=optional)
    if node is None:
        return None
    return AddressEvidenceDTO(
        node.get("firstName"), node.get("lastName"), node.get("name"),
        node.get("address1"), node.get("address2"), node.get("city"),
        node.get("zip"), node.get("provinceCode"), node.get("countryCodeV2"),
        node.get("phone"),
    )


@dataclass(frozen=True, slots=True)
class CustomerEvidenceDTO:
    gid: str
    first_name: str | None
    last_name: str | None
    display_name: str | None
    email: str | None
    phone: str | None
    default_address: AddressEvidenceDTO | None
    updated_at: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "customer.id", required=True), "customer.id", kind="Customer"),
        )
        for name in ("first_name", "last_name", "display_name", "email", "phone", "updated_at"):
            object.__setattr__(self, name, _text(getattr(self, name), f"customer.{name}"))
        if self.default_address is not None and not isinstance(self.default_address, AddressEvidenceDTO):
            raise TypeError("default_address must be AddressEvidenceDTO or None")

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "email": self.email,
            "phone": self.phone,
            "default_address": self.default_address.as_dict() if self.default_address else None,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class OrderSummaryDTO:
    gid: str
    updated_at: str
    created_at: str | None
    edited: bool | None
    test: bool | None
    cancelled_at: str | None
    display_financial_status: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "order.id", required=True), "order.id", kind="Order"),
        )
        object.__setattr__(self, "updated_at", _text(self.updated_at, "order.updatedAt", required=True))
        for name in ("created_at", "cancelled_at", "display_financial_status"):
            object.__setattr__(self, name, _text(getattr(self, name), f"order.{name}"))
        for name in ("edited", "test"):
            object.__setattr__(self, name, _bool(getattr(self, name), f"order.{name}"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "updated_at": self.updated_at,
            "created_at": self.created_at,
            "edited": self.edited,
            "test": self.test,
            "cancelled_at": self.cancelled_at,
            "display_financial_status": self.display_financial_status,
        }


@dataclass(frozen=True, slots=True)
class TransactionEvidenceDTO:
    gid: str
    gateway: str | None
    kind: str | None
    status: str | None
    manual_payment_gateway: str | None
    processed_at: str | None
    amount: MoneySetDTO | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "transaction.id", required=True), "transaction.id", kind="Transaction"),
        )
        for name in ("gateway", "kind", "status", "manual_payment_gateway", "processed_at"):
            object.__setattr__(self, name, _text(getattr(self, name), f"transaction.{name}"))
        if self.amount is not None and not isinstance(self.amount, MoneySetDTO):
            raise TypeError("transaction.amount must be MoneySetDTO or None")

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "gateway": self.gateway,
            "kind": self.kind,
            "status": self.status,
            "manual_payment_gateway": self.manual_payment_gateway,
            "processed_at": self.processed_at,
            "amount": self.amount.as_dict() if self.amount else None,
        }


@dataclass(frozen=True, slots=True)
class TaxLineEvidenceDTO:
    title: str | None
    source: str | None
    rate: str | None
    rate_percentage: str | None
    channel_liable: bool | None
    price: MoneySetDTO | None

    def __post_init__(self) -> None:
        for name in ("title", "source"):
            object.__setattr__(self, name, _text(getattr(self, name), f"tax_line.{name}"))
        object.__setattr__(self, "rate", _tax_rate(self.rate, "tax_line.rate"))
        object.__setattr__(self, "rate_percentage", _tax_rate(self.rate_percentage, "tax_line.rate_percentage"))
        object.__setattr__(self, "channel_liable", _bool(self.channel_liable, "tax_line.channel_liable"))
        if self.price is not None and not isinstance(self.price, MoneySetDTO):
            raise TypeError("tax_line.price must be MoneySetDTO or None")

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "rate": self.rate,
            "rate_percentage": self.rate_percentage,
            "channel_liable": self.channel_liable,
            "price": self.price.as_dict() if self.price else None,
        }


@dataclass(frozen=True, slots=True)
class DiscountApplicationEvidenceDTO:
    typename: str
    index: int
    allocation_method: str
    target_type: str
    target_selection: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "typename", _text(self.typename, "discount_application.__typename", required=True))
        object.__setattr__(self, "index", _int(self.index, "discount_application.index", required=True))
        for name in ("allocation_method", "target_type", "target_selection"):
            object.__setattr__(self, name, _text(getattr(self, name), f"discount_application.{name}", required=True))

    def as_dict(self) -> dict[str, Any]:
        return {
            "typename": self.typename,
            "index": self.index,
            "allocation_method": self.allocation_method,
            "target_type": self.target_type,
            "target_selection": self.target_selection,
        }


@dataclass(frozen=True, slots=True)
class DiscountAllocationEvidenceDTO:
    amount: MoneySetDTO | None
    application: DiscountApplicationEvidenceDTO | None

    def __post_init__(self) -> None:
        if self.amount is not None and not isinstance(self.amount, MoneySetDTO):
            raise TypeError("discount allocation amount must be MoneySetDTO or None")
        if self.application is not None and not isinstance(self.application, DiscountApplicationEvidenceDTO):
            raise TypeError("discount allocation application must be typed")

    def as_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount.as_dict() if self.amount else None,
            "application": self.application.as_dict() if self.application else None,
        }


@dataclass(frozen=True, slots=True)
class OrderLineEvidenceDTO:
    gid: str
    name: str | None
    title: str | None
    variant_title: str | None
    quantity: int | None
    current_quantity: int | None
    sku: str | None
    is_gift_card: bool | None
    requires_shipping: bool
    taxable: bool
    variant_gid: str | None
    product_gid: str | None
    original_unit_price: MoneySetDTO | None
    original_total: MoneySetDTO | None
    discounted_unit_price: MoneySetDTO | None
    discounted_total: MoneySetDTO | None
    discounted_unit_price_after_all_discounts: MoneySetDTO | None
    discount_allocations: tuple[DiscountAllocationEvidenceDTO, ...]
    tax_lines: tuple[TaxLineEvidenceDTO, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "line_item.id", required=True), "line_item.id", kind="LineItem"),
        )
        for name in ("name", "title", "variant_title", "sku", "variant_gid", "product_gid"):
            object.__setattr__(self, name, _text(getattr(self, name), f"line_item.{name}"))
        for name in ("quantity", "current_quantity"):
            object.__setattr__(self, name, _int(getattr(self, name), f"line_item.{name}"))
        if self.variant_gid is not None:
            object.__setattr__(self, "variant_gid", shopify_gid(self.variant_gid, "line_item.variant.id", kind="ProductVariant"))
        if self.product_gid is not None:
            object.__setattr__(self, "product_gid", shopify_gid(self.product_gid, "line_item.product.id", kind="Product"))
        for name in ("is_gift_card", "requires_shipping", "taxable"):
            object.__setattr__(self, name, _bool(getattr(self, name), f"line_item.{name}", required=name in {"requires_shipping", "taxable"}))
        for name in ("original_unit_price", "original_total", "discounted_unit_price", "discounted_total", "discounted_unit_price_after_all_discounts"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, MoneySetDTO):
                raise TypeError(f"line_item.{name} must be MoneySetDTO or None")
        allocations = _sequence(self.discount_allocations, "line_item.discount_allocations")
        tax_lines = _sequence(self.tax_lines, "line_item.tax_lines")
        if any(not isinstance(item, DiscountAllocationEvidenceDTO) for item in allocations):
            raise TypeError("line_item.discount_allocations must be typed")
        if any(not isinstance(item, TaxLineEvidenceDTO) for item in tax_lines):
            raise TypeError("line_item.tax_lines must be typed")
        object.__setattr__(self, "discount_allocations", tuple(allocations))
        object.__setattr__(self, "tax_lines", tuple(tax_lines))

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "name": self.name,
            "title": self.title,
            "variant_title": self.variant_title,
            "quantity": self.quantity,
            "current_quantity": self.current_quantity,
            "sku": self.sku,
            "is_gift_card": self.is_gift_card,
            "requires_shipping": self.requires_shipping,
            "taxable": self.taxable,
            "variant_gid": self.variant_gid,
            "product_gid": self.product_gid,
            "original_unit_price": self.original_unit_price.as_dict() if self.original_unit_price else None,
            "original_total": self.original_total.as_dict() if self.original_total else None,
            "discounted_unit_price": self.discounted_unit_price.as_dict() if self.discounted_unit_price else None,
            "discounted_total": self.discounted_total.as_dict() if self.discounted_total else None,
            "discounted_unit_price_after_all_discounts": self.discounted_unit_price_after_all_discounts.as_dict() if self.discounted_unit_price_after_all_discounts else None,
            "discount_allocations": [item.as_dict() for item in self.discount_allocations],
            "tax_lines": [item.as_dict() for item in self.tax_lines],
        }


@dataclass(frozen=True, slots=True)
class ShippingLineEvidenceDTO:
    gid: str
    is_removed: bool | None
    title: str | None
    discounted_price: MoneySetDTO | None
    current_discounted_price: MoneySetDTO | None
    tax_lines: tuple[TaxLineEvidenceDTO, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "shipping_line.id", required=True), "shipping_line.id", kind="ShippingLine"),
        )
        object.__setattr__(self, "is_removed", _bool(self.is_removed, "shipping_line.isRemoved"))
        object.__setattr__(self, "title", _text(self.title, "shipping_line.title"))
        for name in ("discounted_price", "current_discounted_price"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, MoneySetDTO):
                raise TypeError(f"shipping_line.{name} must be MoneySetDTO or None")
        tax_lines = _sequence(self.tax_lines, "shipping_line.tax_lines")
        if any(not isinstance(item, TaxLineEvidenceDTO) for item in tax_lines):
            raise TypeError("shipping_line.tax_lines must be typed")
        object.__setattr__(self, "tax_lines", tuple(tax_lines))

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "is_removed": self.is_removed,
            "title": self.title,
            "discounted_price": self.discounted_price.as_dict() if self.discounted_price else None,
            "current_discounted_price": self.current_discounted_price.as_dict() if self.current_discounted_price else None,
            "tax_lines": [item.as_dict() for item in self.tax_lines],
        }


@dataclass(frozen=True, slots=True)
class OrderEvidenceDTO:
    gid: str
    name: str | None
    legacy_resource_id: str | None
    created_at: str
    processed_at: str | None
    updated_at: str
    edited: bool | None
    test: bool | None
    currency_code: str
    presentment_currency_code: str
    taxes_included: bool
    confirmed: bool | None
    closed: bool | None
    closed_at: str | None
    cancelled_at: str | None
    cancel_reason: str | None
    display_financial_status: str | None
    display_fulfillment_status: str | None
    email: str | None
    payment_gateway_names: tuple[str, ...]
    customer: CustomerEvidenceDTO | None
    billing_address: AddressEvidenceDTO | None
    shipping_address: AddressEvidenceDTO | None
    totals: Mapping[str, MoneySetDTO | None]
    cash_rounding: Mapping[str, MoneySetDTO | None]
    transactions: tuple[TransactionEvidenceDTO, ...]
    tax_lines: tuple[TaxLineEvidenceDTO, ...]
    line_items: ReadPage[OrderLineEvidenceDTO]
    shipping_lines: ReadPage[ShippingLineEvidenceDTO]
    discount_applications: ReadPage[DiscountApplicationEvidenceDTO]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "order.id", required=True), "order.id", kind="Order"),
        )
        object.__setattr__(self, "created_at", _text(self.created_at, "order.createdAt", required=True))
        object.__setattr__(self, "updated_at", _text(self.updated_at, "order.updatedAt", required=True))
        for name in (
            "name", "legacy_resource_id", "processed_at", "closed_at", "cancelled_at",
            "cancel_reason", "display_financial_status", "display_fulfillment_status", "email",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), f"order.{name}"))
        for name in ("currency_code", "presentment_currency_code"):
            object.__setattr__(self, name, _currency_code(getattr(self, name), f"order.{name}"))
        for name in ("edited", "test", "confirmed", "closed"):
            object.__setattr__(self, name, _bool(getattr(self, name), f"order.{name}"))
        object.__setattr__(self, "taxes_included", _bool(self.taxes_included, "order.taxesIncluded", required=True))
        gateways = _sequence(self.payment_gateway_names, "order.payment_gateway_names")
        if any(not isinstance(item, str) for item in gateways):
            raise TypeError("payment_gateway_names must contain strings")
        object.__setattr__(self, "payment_gateway_names", tuple(gateways))
        if self.customer is not None and not isinstance(self.customer, CustomerEvidenceDTO):
            raise TypeError("customer must be CustomerEvidenceDTO or None")
        for name in ("billing_address", "shipping_address"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, AddressEvidenceDTO):
                raise TypeError(f"{name} must be AddressEvidenceDTO or None")
        if not isinstance(self.totals, Mapping):
            raise TypeError("totals must be a mapping")
        if any(not isinstance(key, str) or not isinstance(value, (MoneySetDTO, type(None))) for key, value in self.totals.items()):
            raise TypeError("totals must map names to MoneySetDTO or None")
        if not isinstance(self.cash_rounding, Mapping):
            raise TypeError("cash_rounding must be a mapping")
        if any(not isinstance(key, str) or not isinstance(value, (MoneySetDTO, type(None))) for key, value in self.cash_rounding.items()):
            raise TypeError("cash_rounding must map names to MoneySetDTO or None")
        # Keep typed money values while making the two evidence maps immutable.
        # Their ``as_dict`` methods provide the JSON-safe RPC projection.
        object.__setattr__(self, "totals", MappingProxyType(dict(self.totals)))
        object.__setattr__(self, "cash_rounding", MappingProxyType(dict(self.cash_rounding)))
        transactions = _sequence(self.transactions, "order.transactions")
        tax_lines = _sequence(self.tax_lines, "order.tax_lines")
        if any(not isinstance(item, TransactionEvidenceDTO) for item in transactions):
            raise TypeError("transactions must be typed")
        if any(not isinstance(item, TaxLineEvidenceDTO) for item in tax_lines):
            raise TypeError("tax_lines must be typed")
        for name in ("line_items", "shipping_lines", "discount_applications"):
            if not isinstance(getattr(self, name), ReadPage):
                raise TypeError(f"{name} must be ReadPage")
        object.__setattr__(self, "transactions", tuple(transactions))
        object.__setattr__(self, "tax_lines", tuple(tax_lines))

    def as_dict(self) -> dict[str, Any]:
        return {
            "gid": self.gid,
            "name": self.name,
            "legacy_resource_id": self.legacy_resource_id,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "updated_at": self.updated_at,
            "edited": self.edited,
            "test": self.test,
            "currency_code": self.currency_code,
            "presentment_currency_code": self.presentment_currency_code,
            "taxes_included": self.taxes_included,
            "confirmed": self.confirmed,
            "closed": self.closed,
            "closed_at": self.closed_at,
            "cancelled_at": self.cancelled_at,
            "cancel_reason": self.cancel_reason,
            "display_financial_status": self.display_financial_status,
            "display_fulfillment_status": self.display_fulfillment_status,
            "email": self.email,
            "payment_gateway_names": list(self.payment_gateway_names),
            "customer": self.customer.as_dict() if self.customer else None,
            "billing_address": self.billing_address.as_dict() if self.billing_address else None,
            "shipping_address": self.shipping_address.as_dict() if self.shipping_address else None,
            "totals": {key: value.as_dict() if value else None for key, value in self.totals.items()},
            "cash_rounding": {key: value.as_dict() if value else None for key, value in self.cash_rounding.items()},
            "transactions": [item.as_dict() for item in self.transactions],
            "tax_lines": [item.as_dict() for item in self.tax_lines],
            "line_items": self.line_items.as_dict(),
            "shipping_lines": self.shipping_lines.as_dict(),
            "discount_applications": self.discount_applications.as_dict(),
        }


__all__ = [
    "AddressEvidenceDTO",
    "CustomerEvidenceDTO",
    "DiscountAllocationEvidenceDTO",
    "DiscountApplicationEvidenceDTO",
    "MoneySetDTO",
    "OrderEvidenceDTO",
    "OrderLineEvidenceDTO",
    "OrderSummaryDTO",
    "ShippingLineEvidenceDTO",
    "TaxLineEvidenceDTO",
    "TransactionEvidenceDTO",
    "address",
    "money_set",
]
