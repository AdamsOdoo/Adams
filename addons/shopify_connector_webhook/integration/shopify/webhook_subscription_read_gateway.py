"""Typed read gateway for Shopify webhook subscriptions.

Only current remote facts cross this boundary.  Desired-state planning and
subscription mutations remain application/runtime concerns.  The delegate is
already authorized by the caller; each page is sent once, with bounded cursor
pagination and no Odoo or network dependency in this module.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from odoo.addons.shopify_connector_core.domain.immutability import freeze_value, to_plain


MAX_PAGE_SIZE = 100
MAX_PAGES = 20
MAX_CURSOR_LENGTH = 512
SHOPIFY_API_VERSION = "2026-07"

SUBSCRIPTIONS_OPERATION = "webhook_subscriptions"
READ_OPERATION_KEYS = frozenset((SUBSCRIPTIONS_OPERATION,))

SUBSCRIPTIONS_QUERY = """
query ConnectorWebhookSubscriptions($first: Int!, $after: String) {
  shop { myshopifyDomain }
  webhookSubscriptions(first: $first, after: $after) {
    nodes {
      id topic uri
      apiVersion { handle displayName supported }
      format includeFields
    }
    pageInfo { hasNextPage endCursor }
  }
}
""".strip()

_SHOP_DOMAIN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$"
)
_SUBSCRIPTION_GID = re.compile(
    r"^gid://shopify/WebhookSubscription/[1-9][0-9]*$"
)


class WebhookSubscriptionReadDelegate(Protocol):
    def read(self, operation_key: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


class WebhookSubscriptionReadError(ValueError):
    """The remote subscription response cannot prove its declared facts."""

    def __init__(self, message: str, code: str = "data_shape_schema_mismatch") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _fail(message: str, code: str = "data_shape_schema_mismatch") -> None:
    raise WebhookSubscriptionReadError(message, code)


def _domain(value: Any) -> str:
    if not isinstance(value, str) or not _SHOP_DOMAIN.fullmatch(value):
        _fail("Shopify returned a missing or malformed shop identity.")
    return value


def _cursor(value: Any, *, required: bool = False) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value or len(value) > MAX_CURSOR_LENGTH:
        _fail("Shopify returned a malformed webhook subscription cursor.")
    return value


def _data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(response, Mapping):
        _fail("Shopify webhook subscription read returned an invalid response envelope.")
    errors = response.get("errors")
    if "errors" in response:
        if (
            not isinstance(errors, (list, tuple))
            or any(not isinstance(item, Mapping) for item in errors)
        ):
            _fail("Shopify webhook subscription read returned malformed errors.")
        if errors:
            _fail("Shopify rejected the webhook subscription read.", "remote_error")
    extensions = response.get("extensions")
    if extensions is not None and not isinstance(extensions, Mapping):
        _fail("Shopify webhook subscription read returned malformed extensions.")
    if isinstance(extensions, Mapping):
        cost = extensions.get("cost")
        if cost is not None and not isinstance(cost, Mapping):
            _fail("Shopify webhook subscription read returned malformed cost telemetry.")
    served = response.get("served_version", response.get("servedVersion"))
    if served != SHOPIFY_API_VERSION:
        _fail(
            "Shopify webhook subscription read was not served by the pinned API version.",
            "api_version_mismatch",
        )
    if not isinstance(response.get("data"), Mapping):
        _fail("Shopify webhook subscription read returned no data object.")
    return response["data"]


def _read_once(
    delegate: WebhookSubscriptionReadDelegate | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
    operation_key: str,
    variables: Mapping[str, Any],
) -> Mapping[str, Any]:
    if operation_key not in READ_OPERATION_KEYS:
        _fail("Webhook subscription read operation is not allowlisted.", "invalid_operation")
    try:
        plain = to_plain(freeze_value(dict(variables)))
    except (TypeError, ValueError) as exc:
        raise WebhookSubscriptionReadError("Webhook read variables are malformed.", "validation_error") from exc
    try:
        result = delegate.read(operation_key, plain) if hasattr(delegate, "read") else delegate(operation_key, plain)
    except WebhookSubscriptionReadError:
        raise
    except Exception as exc:  # pragma: no cover - supplied transport decides details
        raise WebhookSubscriptionReadError("Shopify webhook read could not be completed.", "shopify_unavailable") from exc
    if not isinstance(result, Mapping):
        _fail("Webhook subscription read delegate returned a non-mapping response.")
    return result


def _version_handle(value: Any) -> str:
    if not isinstance(value, Mapping):
        _fail("Shopify returned a malformed webhook API version object.")
    handle = value.get("handle")
    display = value.get("displayName")
    supported = value.get("supported")
    if not isinstance(handle, str) or not handle.strip() or len(handle) > 32:
        _fail("Shopify webhook API version handle is malformed.")
    if not isinstance(display, str) or not display.strip() or len(display) > 256:
        _fail("Shopify webhook API version display name is malformed.")
    if not isinstance(supported, bool):
        _fail("Shopify webhook API version support flag is malformed.")
    return handle.strip()


def _include_fields(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        _fail("Shopify webhook includeFields shape is malformed.")
    result: set[str] = set()
    for field in value:
        if not isinstance(field, str) or not field or len(field) > 128:
            _fail("Shopify webhook includeFields entry is malformed.")
        result.add(field)
    return tuple(sorted(result))


def _uri_digest(node: Mapping[str, Any]) -> str | None:
    uri = node.get("uri")
    if uri is None:
        uri = node.get("callbackUrl")
    if uri is None or uri == "":
        return None
    if not isinstance(uri, str) or len(uri) > 4096:
        _fail("Shopify webhook callback URI is malformed.")
    return hashlib.sha256(uri.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionDTO:
    """Safe equivalent of V1 ``_read_actual_subscriptions`` entries."""

    id: str
    topic: str
    uri_digest: str | None
    observed_api_version: str
    format: str
    include_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _SUBSCRIPTION_GID.fullmatch(self.id):
            raise ValueError("id must be a canonical WebhookSubscription GID")
        if not isinstance(self.topic, str) or not self.topic or len(self.topic) > 128:
            raise ValueError("topic must be a bounded non-empty string")
        if self.uri_digest is not None:
            if not isinstance(self.uri_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", self.uri_digest):
                raise ValueError("uri_digest must be a SHA-256 digest")
        if not isinstance(self.observed_api_version, str) or not self.observed_api_version:
            raise ValueError("observed_api_version must be non-empty")
        if not isinstance(self.format, str) or not self.format or len(self.format) > 32:
            raise ValueError("format must be bounded and non-empty")
        if any(not isinstance(item, str) or not item for item in self.include_fields):
            raise ValueError("include_fields must contain non-empty strings")
        object.__setattr__(self, "include_fields", tuple(sorted(set(self.include_fields))))

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "uri_digest": self.uri_digest or False,
            "observed_api_version": self.observed_api_version,
            "format": self.format,
            "include_fields": list(self.include_fields),
        }


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionPageDTO:
    items: tuple[WebhookSubscriptionDTO, ...]
    store_domain: str
    has_next_page: bool
    next_cursor: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        if any(not isinstance(item, WebhookSubscriptionDTO) for item in self.items):
            raise TypeError("items must contain WebhookSubscriptionDTO values")
        _domain(self.store_domain)
        if not isinstance(self.has_next_page, bool):
            raise TypeError("has_next_page must be bool")
        if self.has_next_page:
            _cursor(self.next_cursor, required=True)
        else:
            _cursor(self.next_cursor)

    def to_legacy_list(self) -> list[dict[str, Any]]:
        return [item.to_legacy_dict() for item in self.items]


@dataclass(frozen=True, slots=True)
class WebhookSubscriptionCollectionDTO:
    items: tuple[WebhookSubscriptionDTO, ...]
    store_domain: str
    checkpoint: str | None
    complete: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        if any(not isinstance(item, WebhookSubscriptionDTO) for item in self.items):
            raise TypeError("items must contain WebhookSubscriptionDTO values")
        _domain(self.store_domain)
        _cursor(self.checkpoint)
        if not isinstance(self.complete, bool):
            raise TypeError("complete must be bool")
        if not self.complete:
            raise ValueError("a collection returned by read_all must be complete")

    def to_legacy_list(self) -> list[dict[str, Any]]:
        return [item.to_legacy_dict() for item in self.items]


class WebhookSubscriptionReadGateway:
    """Allowlisted current-subscription reads with a hard page cap."""

    operation_documents = {SUBSCRIPTIONS_OPERATION: SUBSCRIPTIONS_QUERY}

    def __init__(
        self,
        delegate: WebhookSubscriptionReadDelegate | Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
        *,
        store_domain: str | None = None,
        max_pages: int = MAX_PAGES,
    ) -> None:
        if not callable(delegate) and not hasattr(delegate, "read"):
            raise TypeError("delegate must provide one read operation")
        if store_domain is not None:
            _domain(store_domain)
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_PAGES:
            raise ValueError("max_pages must be between 1 and %d" % MAX_PAGES)
        self._delegate = delegate
        self.store_domain = store_domain
        self.max_pages = max_pages

    def _check_domain(self, observed: str) -> None:
        if self.store_domain and observed != self.store_domain:
            _fail("Shopify returned a different shop identity.", "store_identity_mismatch")

    def read_page(self, *, first: int = MAX_PAGE_SIZE, after: str | None = None) -> WebhookSubscriptionPageDTO:
        if isinstance(first, bool) or not isinstance(first, int) or not 1 <= first <= MAX_PAGE_SIZE:
            _fail("Webhook subscription page size is outside its safety bound.", "validation_error")
        _cursor(after)
        data = _data(_read_once(self._delegate, SUBSCRIPTIONS_OPERATION, {"first": first, "after": after}))
        shop = data.get("shop")
        if not isinstance(shop, Mapping):
            _fail("Shopify webhook subscription response omitted shop identity.")
        store_domain = _domain(shop.get("myshopifyDomain"))
        self._check_domain(store_domain)
        connection = data.get("webhookSubscriptions")
        if not isinstance(connection, Mapping) or not isinstance(connection.get("nodes"), list):
            _fail("Shopify webhook subscriptions connection is malformed.")
        if len(connection["nodes"]) > first:
            _fail("Shopify webhook subscriptions page exceeded its requested size.")
        page_info = connection.get("pageInfo")
        if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
            _fail("Shopify webhook subscriptions pageInfo is malformed.")
        items: list[WebhookSubscriptionDTO] = []
        for node in connection["nodes"]:
            if not isinstance(node, Mapping):
                _fail("Shopify webhook subscription node is malformed.")
            item_id = node.get("id")
            if not isinstance(item_id, str) or not _SUBSCRIPTION_GID.fullmatch(item_id):
                _fail("Shopify returned a malformed webhook subscription GID.")
            topic = node.get("topic")
            if not isinstance(topic, str) or not topic or len(topic) > 128:
                _fail("Shopify webhook subscription topic is malformed.")
            format_value = node.get("format")
            if not isinstance(format_value, str) or not format_value or len(format_value) > 32:
                _fail("Shopify webhook subscription format is malformed.")
            items.append(
                WebhookSubscriptionDTO(
                    item_id,
                    topic,
                    _uri_digest(node),
                    _version_handle(node.get("apiVersion")),
                    format_value,
                    _include_fields(node.get("includeFields")),
                )
            )
        next_cursor = _cursor(page_info.get("endCursor"))
        if page_info["hasNextPage"] and next_cursor is None:
            _fail("Shopify webhook subscriptions page omitted its next cursor.")
        return WebhookSubscriptionPageDTO(tuple(items), store_domain, page_info["hasNextPage"], next_cursor)

    def read_all(self, *, first: int = MAX_PAGE_SIZE, after: str | None = None) -> WebhookSubscriptionCollectionDTO:
        cursor = _cursor(after)
        seen_cursors: set[str] = set()
        seen_ids: set[str] = set()
        result: list[WebhookSubscriptionDTO] = []
        store_domain: str | None = None
        for _ in range(self.max_pages):
            page = self.read_page(first=first, after=cursor)
            store_domain = store_domain or page.store_domain
            for item in page.items:
                if item.id in seen_ids:
                    _fail("Shopify webhook pagination returned a duplicate subscription identity.")
                seen_ids.add(item.id)
                result.append(item)
            if not page.has_next_page:
                return WebhookSubscriptionCollectionDTO(tuple(result), store_domain or "", cursor)
            cursor = _cursor(page.next_cursor, required=True)
            if cursor in seen_cursors:
                _fail("Shopify webhook pagination repeated a cursor.")
            seen_cursors.add(cursor)
        _fail("Shopify webhook subscription pagination exceeded its safety cap.")


__all__ = [
    "MAX_PAGE_SIZE",
    "MAX_PAGES",
    "READ_OPERATION_KEYS",
    "SHOPIFY_API_VERSION",
    "SUBSCRIPTIONS_OPERATION",
    "SUBSCRIPTIONS_QUERY",
    "WebhookSubscriptionCollectionDTO",
    "WebhookSubscriptionDTO",
    "WebhookSubscriptionPageDTO",
    "WebhookSubscriptionReadDelegate",
    "WebhookSubscriptionReadError",
    "WebhookSubscriptionReadGateway",
]
