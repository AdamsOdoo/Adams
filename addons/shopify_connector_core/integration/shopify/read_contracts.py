"""Pure contracts shared by the first Shopify read gateways.

This module is deliberately smaller than the Odoo model layer.  It describes
one read operation, one bounded page, and immutable DTOs; it does not know
about credentials, ORM records, jobs, or Shopify transport.  Domain gateways
provide the operation descriptors and shape normalizers while the
compatibility adapter keeps the current API-client call path available for an
immediate rollback.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Generic, TypeVar

from ...domain.immutability import freeze_value, to_plain
from .read_money import MoneyDTO


T = TypeVar("T")
_GRAPHQL_QUERY_NAME = re.compile(r"\bquery\s+([_A-Za-z][_A-Za-z0-9]*)\b")
_GRAPHQL_MUTATION = re.compile(r"\bmutation\b")
_SHOPIFY_GID = re.compile(r"^gid://shopify/(?P<kind>[A-Za-z][A-Za-z0-9_]*)/(?P<id>[1-9][0-9]*)$")
_MYSHOPIFY_DOMAIN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$"
)
_MAX_TEXT = 4096
_MAX_CURSOR_LENGTH = 512
SHOPIFY_API_VERSION = "2026-07"


class ReadGatewayMode(str, Enum):
    """Migration modes for a read gateway's single delegate call."""

    LEGACY = "legacy"
    TYPED = "typed"


class ReadGatewayError(RuntimeError):
    """Safe, stable failure raised before a malformed DTO escapes the gateway."""

    def __init__(self, code: str, message: str, operation_name: str | None = None):
        if not isinstance(code, str) or not code.strip():
            raise ValueError("read error code must be non-empty")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("read error message must be non-empty")
        self.code = code
        self.message = message[:_MAX_TEXT]
        self.operation_name = operation_name
        super().__init__(self.message)


class ReadShapeError(ReadGatewayError):
    """The remote response was incomplete or outside the checked-in shape."""


def shopify_gid(value: Any, field_name: str = "Shopify identity", *, kind: str | None = None) -> str:
    """Validate one canonical numeric Shopify GID at the typed boundary."""

    if not isinstance(value, str):
        raise ReadShapeError("invalid_identity", f"Shopify read returned an invalid {field_name}.")
    match = _SHOPIFY_GID.fullmatch(value)
    if not match or (kind is not None and match.group("kind") != kind):
        raise ReadShapeError("invalid_identity", f"Shopify read returned an invalid {field_name}.")
    return value


def myshopify_domain(value: Any, field_name: str = "shop domain") -> str:
    """Validate the canonical lower-case ``*.myshopify.com`` identity."""

    if not isinstance(value, str) or not _MYSHOPIFY_DOMAIN.fullmatch(value):
        raise ReadShapeError("invalid_identity", f"Shopify read returned an invalid {field_name}.")
    return value


def shopify_cursor(value: Any, field_name: str = "cursor", *, allow_none: bool = True) -> str | None:
    """Validate one bounded opaque connection cursor before a remote call."""

    if value is None and allow_none:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > _MAX_CURSOR_LENGTH
    ):
        raise ReadGatewayError("cursor_invalid", f"Shopify read returned an invalid {field_name}.")
    return value


def _text(value: Any, field_name: str, *, required: bool = False) -> str | None:
    if value is None or value is False:
        if required:
            raise ReadShapeError("missing_field", f"Shopify read omitted {field_name}.")
        return None
    if not isinstance(value, str):
        raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")
    value = value.strip()
    if required and not value:
        raise ReadShapeError("missing_field", f"Shopify read omitted {field_name}.")
    return value or None


def _bool(value: Any, field_name: str, *, required: bool = False) -> bool | None:
    if value is None:
        if required:
            raise ReadShapeError("missing_field", f"Shopify read omitted {field_name}.")
        return None
    if not isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")
    return value


def _number(value: Any, field_name: str, *, required: bool = False) -> int | float | None:
    if value is None:
        if required:
            raise ReadShapeError("missing_field", f"Shopify read omitted {field_name}.")
        return None
    if isinstance(value, bool):
        raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")
    if value == "":
        if required:
            raise ReadShapeError("missing_field", f"Shopify read omitted {field_name}.")
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")
        return value
    if isinstance(value, str):
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ReadShapeError(
                "invalid_shape", f"Shopify read returned an invalid {field_name}."
            ) from exc
        if not math.isfinite(parsed):
            raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")
        return int(parsed) if parsed.is_integer() else parsed
    raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")


def _strings(value: Any, field_name: str, *, allow_none: bool = True) -> tuple[str, ...] | None:
    if value is None:
        if allow_none:
            return None
        raise ReadShapeError("missing_field", f"Shopify read omitted {field_name}.")
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ReadShapeError("invalid_shape", f"Shopify read returned an invalid {field_name}.")
    result: list[str] = []
    for item in value:
        text = _text(item, field_name, required=True)
        result.append(text or "")
    return tuple(result)


def _plain(value: Any) -> Any:
    """Convert nested DTOs and frozen containers to JSON-safe values."""

    if hasattr(value, "as_dict") and callable(value.as_dict):
        return value.as_dict()
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class ReadOperation:
    """A query descriptor bound to a checked-in operation document."""

    operation_name: str
    variables: tuple[str, ...] = ()
    required_variables: tuple[str, ...] = ()
    page_size: int | None = None
    max_pages: int = 1
    max_items: int | None = None

    def __post_init__(self) -> None:
        name = _text(self.operation_name, "operation_name", required=True)
        if not name or not _GRAPHQL_QUERY_NAME.fullmatch(f"query {name}"):
            raise ValueError("operation_name must be a GraphQL query name")
        if isinstance(self.variables, (str, bytes)) or not isinstance(self.variables, Sequence):
            raise TypeError("operation variables must be a sequence")
        if isinstance(self.required_variables, (str, bytes)) or not isinstance(self.required_variables, Sequence):
            raise TypeError("required variables must be a sequence")
        variables = tuple(self.variables)
        required = tuple(self.required_variables)
        if any(not isinstance(item, str) or not item.strip() for item in variables):
            raise ValueError("operation variables must be non-empty strings")
        if len(set(variables)) != len(variables):
            raise ValueError("operation variables must be unique")
        if any(item not in variables for item in required):
            raise ValueError("required_variables must be declared in variables")
        if isinstance(self.max_pages, bool) or not isinstance(self.max_pages, int) or self.max_pages <= 0:
            raise ValueError("max_pages must be a positive integer")
        if self.page_size is not None and (
            isinstance(self.page_size, bool)
            or not isinstance(self.page_size, int)
            or self.page_size <= 0
        ):
            raise ValueError("page_size must be a positive integer or None")
        if self.max_items is not None and (
            isinstance(self.max_items, bool)
            or not isinstance(self.max_items, int)
            or self.max_items <= 0
        ):
            raise ValueError("max_items must be a positive integer or None")
        object.__setattr__(self, "operation_name", name)
        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "required_variables", required)


@dataclass(frozen=True, slots=True)
class ReadObservation:
    """Non-business telemetry retained without carrying a raw GraphQL envelope."""

    requested_query_cost: int | float | None = None
    actual_query_cost: int | float | None = None
    maximum_available: int | float | None = None
    currently_available: int | float | None = None
    restore_rate: int | float | None = None
    request_id: str | None = None
    served_version: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "requested_query_cost",
            "actual_query_cost",
            "maximum_available",
            "currently_available",
            "restore_rate",
        ):
            value = getattr(self, name)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise TypeError(f"{name} must be numeric or None")
                if isinstance(value, float) and not math.isfinite(value):
                    raise ValueError(f"{name} must be finite")
        for name in ("request_id", "served_version"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise TypeError(f"{name} must be a non-empty string or None")

    @classmethod
    def from_response(cls, response: Mapping[str, Any] | Any) -> "ReadObservation":
        if not isinstance(response, Mapping):
            as_dict = getattr(response, "as_dict", None)
            if not callable(as_dict):
                raise ReadGatewayError("invalid_response", "Shopify read returned an invalid response envelope.")
            try:
                response = as_dict()
            except Exception as exc:  # pragma: no cover - supplied result object
                raise ReadGatewayError("invalid_response", "Shopify read returned an invalid response envelope.") from exc
        if not isinstance(response, Mapping):
            raise ReadGatewayError("invalid_response", "Shopify read returned an invalid response envelope.")
        extensions = response.get("extensions")
        if extensions is not None and not isinstance(extensions, Mapping):
            raise ReadGatewayError("invalid_response", "Shopify read returned malformed extensions.")

        cost = response.get("cost")
        if cost is not None and not isinstance(cost, Mapping):
            as_dict = getattr(cost, "as_dict", None)
            try:
                cost = as_dict() if callable(as_dict) else None
            except Exception as exc:  # pragma: no cover - supplied telemetry object
                raise ReadGatewayError("invalid_response", "Shopify read returned malformed cost telemetry.") from exc
            if not isinstance(cost, Mapping):
                raise ReadGatewayError("invalid_response", "Shopify read returned malformed cost telemetry.")
        if not isinstance(cost, Mapping):
            cost = extensions.get("cost") if extensions is not None else None
            if cost is not None and not isinstance(cost, Mapping):
                as_dict = getattr(cost, "as_dict", None)
                try:
                    cost = as_dict() if callable(as_dict) else None
                except Exception as exc:  # pragma: no cover - supplied telemetry object
                    raise ReadGatewayError("invalid_response", "Shopify read returned malformed cost telemetry.") from exc
                if not isinstance(cost, Mapping):
                    raise ReadGatewayError("invalid_response", "Shopify read returned malformed cost telemetry.")
        if not isinstance(cost, Mapping):
            cost = response.get("throttle_status")
            if cost is not None and not isinstance(cost, Mapping):
                as_dict = getattr(cost, "as_dict", None)
                try:
                    cost = as_dict() if callable(as_dict) else None
                except Exception as exc:  # pragma: no cover - supplied telemetry object
                    raise ReadGatewayError("invalid_response", "Shopify read returned malformed throttle telemetry.") from exc
                if not isinstance(cost, Mapping):
                    raise ReadGatewayError("invalid_response", "Shopify read returned malformed throttle telemetry.")
        if not isinstance(cost, Mapping):
            cost = {}
        throttle = cost.get("throttleStatus", cost)
        if not isinstance(throttle, Mapping):
            throttle = {}
        request_id = response.get("request_id", response.get("requestId"))
        served_version = response.get("served_version", response.get("servedVersion"))
        observation = cls(
            _number(cost.get("requestedQueryCost", cost.get("requested_query_cost")), "requestedQueryCost"),
            _number(cost.get("actualQueryCost", cost.get("actual_query_cost")), "actualQueryCost"),
            _number(throttle.get("maximumAvailable", throttle.get("maximum_available")), "maximumAvailable"),
            _number(throttle.get("currentlyAvailable", throttle.get("currently_available")), "currentlyAvailable"),
            _number(throttle.get("restoreRate", throttle.get("restore_rate")), "restoreRate"),
            _text(request_id, "request_id"),
            _text(served_version, "served_version"),
        )
        if observation.served_version != SHOPIFY_API_VERSION:
            raise ReadGatewayError(
                "api_version_mismatch",
                "Shopify read was not served by the pinned connector API version.",
            )
        return observation

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested_query_cost": self.requested_query_cost,
            "actual_query_cost": self.actual_query_cost,
            "maximum_available": self.maximum_available,
            "currently_available": self.currently_available,
            "restore_rate": self.restore_rate,
            "request_id": self.request_id,
            "served_version": self.served_version,
        }


@dataclass(frozen=True, slots=True)
class ReadResult(Generic[T]):
    """One normalized DTO plus its bounded operation observation."""

    value: T
    operation_name: str
    observation: ReadObservation = field(default_factory=ReadObservation)

    def __post_init__(self) -> None:
        _text(self.operation_name, "operation_name", required=True)
        if not isinstance(self.observation, ReadObservation):
            raise TypeError("observation must be ReadObservation")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "operation_name": self.operation_name,
            "value": _plain(self.value),
            "observation": self.observation.as_dict(),
        })


@dataclass(frozen=True, slots=True)
class ReadPage(Generic[T]):
    """A single connection page with explicit progress metadata."""

    items: tuple[T, ...]
    cursor: str | None
    next_cursor: str | None
    has_more: bool
    page_number: int
    max_pages: int
    observation: ReadObservation = field(default_factory=ReadObservation)

    def __post_init__(self) -> None:
        if isinstance(self.items, (str, bytes, Mapping)) or not isinstance(self.items, Sequence):
            raise TypeError("page items must be a JSON sequence")
        object.__setattr__(self, "items", tuple(self.items))
        for name in ("cursor", "next_cursor"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value.strip() or len(value) > _MAX_CURSOR_LENGTH
            ):
                raise ValueError(f"{name} must be a non-empty cursor or None")
        if not isinstance(self.has_more, bool):
            raise TypeError("has_more must be bool")
        if self.has_more and self.next_cursor is None:
            raise ValueError("a continuing page requires next_cursor")
        if not self.has_more and self.next_cursor is not None:
            raise ValueError("a terminal page cannot carry next_cursor")
        if isinstance(self.page_number, bool) or not isinstance(self.page_number, int) or self.page_number <= 0:
            raise ValueError("page_number must be positive")
        if isinstance(self.max_pages, bool) or not isinstance(self.max_pages, int) or self.max_pages <= 0:
            raise ValueError("max_pages must be positive")
        if self.page_number > self.max_pages:
            raise ValueError("page_number cannot exceed max_pages")
        if not isinstance(self.observation, ReadObservation):
            raise TypeError("observation must be ReadObservation")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "items": [_plain(item) for item in self.items],
            "cursor": self.cursor,
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
            "page_number": self.page_number,
            "max_pages": self.max_pages,
            "observation": self.observation.as_dict(),
        })


class CursorProgress:
    """Stateful, bounded cursor guard shared by paginated read callers."""

    def __init__(self, *, max_pages: int, max_items: int | None = None) -> None:
        if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages <= 0:
            raise ValueError("max_pages must be positive")
        if max_items is not None and (
            isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0
        ):
            raise ValueError("max_items must be positive or None")
        self.max_pages = max_pages
        self.max_items = max_items
        self.pages = 0
        self.items = 0
        self._seen_cursors: set[str] = set()
        self._seen_identities: set[str] = set()

    def accept(
        self,
        *,
        cursor: str | None,
        has_more: bool,
        next_cursor: str | None,
        item_count: int,
    ) -> int:
        """Validate and record one page, returning its one-based page number."""

        if self.pages >= self.max_pages:
            raise ReadGatewayError("page_limit", "Shopify read page limit was reached.")
        if cursor is not None:
            if not isinstance(cursor, str) or not cursor.strip() or len(cursor) > _MAX_CURSOR_LENGTH:
                raise ReadGatewayError("cursor_invalid", "Shopify read returned an invalid cursor.")
            if cursor in self._seen_cursors:
                raise ReadGatewayError("cursor_loop", "Shopify read cursor repeated.")
            self._seen_cursors.add(cursor)
        if isinstance(item_count, bool) or not isinstance(item_count, int) or item_count < 0:
            raise TypeError("item_count must be a non-negative integer")
        if self.max_items is not None and self.items + item_count > self.max_items:
            raise ReadGatewayError("item_limit", "Shopify read item limit was reached.")
        if not isinstance(has_more, bool):
            raise ReadGatewayError("pagination_invalid", "Shopify read returned invalid page metadata.")
        if has_more:
            if not isinstance(next_cursor, str) or not next_cursor.strip() or len(next_cursor) > _MAX_CURSOR_LENGTH:
                raise ReadGatewayError("cursor_invalid", "Shopify read omitted its next cursor.")
            if next_cursor == cursor or next_cursor in self._seen_cursors:
                raise ReadGatewayError("cursor_loop", "Shopify read cursor did not make progress.")
        elif next_cursor is not None:
            raise ReadGatewayError("pagination_invalid", "Terminal Shopify page carried a next cursor.")
        self.pages += 1
        self.items += item_count
        return self.pages

    def accept_identities(self, identities: Sequence[str]) -> None:
        """Reject duplicate stable identities across a paginated read.

        The check is intentionally separate from cursor progress because a
        Shopify connection can advance its cursor while returning an overlap.
        Callers validate identities before accepting the page, so an overlap
        cannot be mistaken for a new item or reach a local uniqueness error.
        """

        if isinstance(identities, (str, bytes, Mapping)) or not isinstance(identities, Sequence):
            raise TypeError("identities must be a sequence")
        page_ids: set[str] = set()
        for identity in identities:
            if not isinstance(identity, str) or not identity.strip():
                raise ReadGatewayError("identity_invalid", "Shopify read returned an invalid item identity.")
            if identity in page_ids or identity in self._seen_identities:
                raise ReadGatewayError("identity_duplicate", "Shopify read returned a duplicate item identity.")
            page_ids.add(identity)
        self._seen_identities.update(page_ids)


def page_from_connection(
    operation: ReadOperation,
    *,
    cursor: str | None,
    page_info: Mapping[str, Any],
    items: Sequence[T],
    observation: ReadObservation,
    progress: CursorProgress | None = None,
) -> ReadPage[T]:
    """Build a page while enforcing operation and cursor bounds."""

    if not isinstance(page_info, Mapping):
        raise ReadShapeError("pagination_invalid", "Shopify read omitted page metadata.", operation.operation_name)
    if isinstance(items, (str, bytes, Mapping)) or not isinstance(items, Sequence):
        raise ReadShapeError("invalid_shape", "Shopify read returned a non-sequence page.", operation.operation_name)
    if operation.page_size is not None and len(items) > operation.page_size:
        raise ReadGatewayError("page_size", "Shopify read returned more items than its page bound.", operation.operation_name)
    has_more = page_info.get("hasNextPage")
    next_cursor = page_info.get("endCursor")
    if progress is None:
        progress = CursorProgress(max_pages=operation.max_pages, max_items=operation.max_items)
    page_number = progress.accept(
        cursor=cursor,
        has_more=has_more,
        next_cursor=next_cursor,
        item_count=len(items),
    )
    return ReadPage(
        tuple(items), cursor, next_cursor if has_more else None,
        has_more, page_number, operation.max_pages, observation,
    )


def response_data(response: Any, operation_name: str) -> tuple[Mapping[str, Any], ReadObservation]:
    """Extract data and safe telemetry from legacy or typed result envelopes."""

    if hasattr(response, "as_dict") and callable(response.as_dict):
        try:
            response = response.as_dict()
        except Exception as exc:  # pragma: no cover - supplied result object
            raise ReadGatewayError("invalid_response", "Shopify read returned an invalid response envelope.", operation_name) from exc
    if isinstance(response, Mapping):
        envelope = response
    else:
        raise ReadGatewayError("invalid_response", "Shopify read returned an invalid response envelope.", operation_name)
    if "errors" in envelope:
        errors = envelope.get("errors")
        if not isinstance(errors, Sequence) or isinstance(errors, (str, bytes, Mapping)):
            raise ReadGatewayError("invalid_response", "Shopify read returned malformed errors.", operation_name)
        if any(not isinstance(item, Mapping) for item in errors):
            raise ReadGatewayError("invalid_response", "Shopify read returned malformed errors.", operation_name)
        if errors:
            raise ReadGatewayError("remote_error", "Shopify rejected the read request.", operation_name)
    if "data" not in envelope:
        raise ReadGatewayError("invalid_response", "Shopify read omitted its data object.", operation_name)
    data = envelope.get("data")
    if not isinstance(data, Mapping):
        raise ReadGatewayError("invalid_response", "Shopify read omitted its data object.", operation_name)
    observation = ReadObservation.from_response(envelope)
    if observation.served_version != SHOPIFY_API_VERSION:
        raise ReadGatewayError(
            "api_version_mismatch",
            "Shopify read was not served by the pinned connector API version.",
            operation_name,
        )
    return data, observation


class ReadCompatibilityAdapter:
    """One-call adapter for legacy API-client results with typed rollback mode.

    ``operation_documents`` is supplied by the owning integration boundary
    from its checked-in query constants.  This module intentionally carries no
    GraphQL field list.  Legacy mode invokes exactly
    ``legacy_delegate.execute(store, document, variables)`` once.  Typed mode
    invokes exactly ``typed_delegate.execute_read(store, operation, variables)``
    once.  No fallback call is attempted after a failure.
    """

    def __init__(
        self,
        legacy_delegate: Any,
        operation_documents: Mapping[str, str],
        *,
        typed_delegate: Any | None = None,
        mode: str | ReadGatewayMode = ReadGatewayMode.LEGACY,
    ) -> None:
        if legacy_delegate is None or not callable(getattr(legacy_delegate, "execute", None)):
            raise TypeError("legacy_delegate must expose execute")
        if not isinstance(operation_documents, Mapping):
            raise TypeError("operation_documents must be a mapping")
        docs: dict[str, str] = {}
        for name, document in operation_documents.items():
            if not isinstance(name, str) or not name.strip() or not isinstance(document, str):
                raise TypeError("operation documents must map names to strings")
            match = _GRAPHQL_QUERY_NAME.search(document)
            if not match or match.group(1) != name or _GRAPHQL_MUTATION.search(document):
                raise ValueError(f"operation document is not the checked-in query {name!r}")
            docs[name] = document
        try:
            mode = mode if isinstance(mode, ReadGatewayMode) else ReadGatewayMode(str(mode))
        except ValueError as exc:
            raise ValueError(f"unsupported read gateway mode: {mode!r}") from exc
        self._legacy_delegate = legacy_delegate
        self._typed_delegate = typed_delegate
        self._operation_documents = freeze_value(docs)
        self.mode = mode

    @property
    def is_legacy(self) -> bool:
        return self.mode is ReadGatewayMode.LEGACY

    def execute(
        self,
        store: Any,
        operation: ReadOperation,
        variables: Mapping[str, Any] | None = None,
    ) -> Any:
        if not isinstance(operation, ReadOperation):
            raise TypeError("operation must be ReadOperation")
        variables = {} if variables is None else variables
        if not isinstance(variables, Mapping):
            raise TypeError("variables must be a mapping")
        unknown = set(variables) - set(operation.variables)
        missing = set(operation.required_variables) - set(variables)
        if unknown:
            raise ReadGatewayError("invalid_variables", "Read variables are not part of the operation.", operation.operation_name)
        if missing:
            raise ReadGatewayError("missing_variables", "Read variables are incomplete.", operation.operation_name)
        try:
            safe_variables = to_plain(freeze_value(dict(variables)))
        except (TypeError, ValueError) as exc:
            raise ReadGatewayError(
                "invalid_variables", "Read variables are not JSON-safe.", operation.operation_name
            ) from exc
        try:
            if self.is_legacy:
                document = self._operation_documents.get(operation.operation_name)
                if not isinstance(document, str):
                    raise ReadGatewayError(
                        "operation_unconfigured",
                        "The checked-in Shopify read operation is not configured.",
                        operation.operation_name,
                    )
                # Exactly one legacy delegate call; never probe or retry here.
                return self._legacy_delegate.execute(store, document, safe_variables)
            execute_read = getattr(self._typed_delegate, "execute_read", None)
            if not callable(execute_read):
                raise ReadGatewayError(
                    "typed_delegate_unconfigured",
                    "The typed Shopify read delegate is not configured.",
                    operation.operation_name,
                )
            # Exactly one typed delegate call; no legacy fallback in typed mode.
            return execute_read(store, operation, safe_variables)
        except ReadGatewayError:
            raise
        except Exception as exc:  # pragma: no cover - delegate owns transport details
            raise ReadGatewayError(
                "delegate_failure", "Shopify read could not be completed.", operation.operation_name
            ) from exc

    def for_mode(self, mode: str | ReadGatewayMode) -> "ReadCompatibilityAdapter":
        return type(self)(
            self._legacy_delegate,
            self._operation_documents,
            typed_delegate=self._typed_delegate,
            mode=mode,
        )

    def rollback(self) -> "ReadCompatibilityAdapter":
        return self.for_mode(ReadGatewayMode.LEGACY)


@dataclass(frozen=True, slots=True)
class StoreIdentityDTO:
    """Shop identity returned by ``ConnectorTestConnection``."""

    gid: str
    name: str
    myshopify_domain: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "shop.id", required=True), "shop.id", kind="Shop"),
        )
        object.__setattr__(self, "name", _text(self.name, "shop.name", required=True))
        object.__setattr__(
            self, "myshopify_domain", _text(self.myshopify_domain, "shop.myshopifyDomain", required=True)
        )
        object.__setattr__(
            self,
            "myshopify_domain",
            myshopify_domain(self.myshopify_domain, "shop.myshopifyDomain"),
        )

    def as_dict(self) -> dict[str, str]:
        return {"gid": self.gid, "name": self.name, "myshopify_domain": self.myshopify_domain}


@dataclass(frozen=True, slots=True)
class StoreCapabilityDTO:
    """Shop identity and the exact granted access-scope handles."""

    store: StoreIdentityDTO
    granted_scopes: tuple[str, ...]
    api_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.store, StoreIdentityDTO):
            raise TypeError("store must be StoreIdentityDTO")
        scopes = _strings(self.granted_scopes, "granted_scopes", allow_none=False) or ()
        object.__setattr__(self, "granted_scopes", tuple(sorted(set(scopes))))
        object.__setattr__(self, "api_version", _text(self.api_version, "api_version", required=True))

    def as_dict(self) -> dict[str, Any]:
        return {
            "store": self.store.as_dict(),
            "granted_scopes": list(self.granted_scopes),
            "api_version": self.api_version,
        }


@dataclass(frozen=True, slots=True)
class LocationDTO:
    """A Shopify location observation; names never act as identity."""

    gid: str
    name: str
    is_active: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "gid",
            shopify_gid(_text(self.gid, "location.id", required=True), "location.id", kind="Location"),
        )
        object.__setattr__(self, "name", _text(self.name, "location.name", required=True))
        object.__setattr__(self, "is_active", _bool(self.is_active, "location.isActive"))

    def as_dict(self) -> dict[str, Any]:
        return {"gid": self.gid, "name": self.name, "is_active": self.is_active}


__all__ = [
    "CursorProgress",
    "LocationDTO",
    "MoneyDTO",
    "ReadCompatibilityAdapter",
    "ReadGatewayError",
    "ReadGatewayMode",
    "ReadObservation",
    "ReadOperation",
    "ReadPage",
    "ReadResult",
    "ReadShapeError",
    "SHOPIFY_API_VERSION",
    "StoreCapabilityDTO",
    "StoreIdentityDTO",
    "myshopify_domain",
    "page_from_connection",
    "response_data",
    "shopify_cursor",
    "shopify_gid",
]
