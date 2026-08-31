"""Bounded Shopify Admin GraphQL transport primitives.

This module is deliberately an adapter, not a domain gateway.  It owns the
single versioned URL, request headers, timeout budget and response-size guard
used by the typed compatibility seam.  The legacy Odoo model remains the
authoritative live caller until a later migration slice explicitly switches
the mode.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:  # Keep pure contract imports usable in the dependency-free test lane.
    import requests
except ImportError:  # pragma: no cover - exercised by the pure test runtime
    requests = None

from ...domain.immutability import freeze_value, to_plain


_REQUEST_EXCEPTION = (
    getattr(getattr(requests, "exceptions", None), "RequestException", OSError)
)


# These are intentionally the same planning defaults as the legacy API client
# (``models/shopify_connector_api_client.py``).  A compatibility adapter must
# not silently widen the old request budget while it is inert.
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 20
DEFAULT_TIMEOUT = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)

# Kept in the integration boundary because the dependency policy deliberately
# prevents adapter code from reaching into legacy ``tools`` modules.  This is
# the same pinned value used by ``models/...api_client.py``; a version bump is
# a dedicated contract checkpoint, never a merchant setting.
SHOPIFY_API_VERSION = "2026-07"
API_VERSION_RESPONSE_HEADER = "X-Shopify-API-Version"

# Shopify payloads are bounded at the transport boundary.  The existing
# webhook boundary uses the same 10 MiB ceiling; keeping the value explicit
# makes an oversized-body fixture deterministic and gives a later profile a
# single knob without changing call sites.
DEFAULT_MAX_RESPONSE_BODY_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_REQUEST_BODY_BYTES = 1 * 1024 * 1024
RESPONSE_CHUNK_BYTES = 64 * 1024

ACCESS_TOKEN_HEADER = "X-Shopify-Access-Token"
CORRELATION_HEADER = "X-Correlation-ID"
_SHOP_DOMAIN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$",
)

_SENSITIVE_KEYS = (
    "access_token",
    "token",
    "secret",
    "password",
    "authorization",
    "x-shopify-access-token",
    "api_key",
    "apikey",
    "client_secret",
    "refresh_token",
    "hmac",
)
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"shpat_[A-Za-z0-9]+"),
    re.compile(r"shprt_[A-Za-z0-9]+"),
)
REDACTED = "***"


def _redact_string(value: str, extra_secrets: tuple[str, ...]) -> str:
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        value = pattern.sub(REDACTED, value)
    for secret in extra_secrets:
        if secret:
            value = value.replace(secret, REDACTED)
    return value


def redact(value: Any, extra_secrets: tuple[str, ...] = ()) -> Any:
    """Redact the same credential/secret shapes before they leave the adapter."""

    if isinstance(value, str):
        return _redact_string(value, extra_secrets)
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED
                if any(sensitive in str(key).lower() for sensitive in _SENSITIVE_KEYS)
                else redact(item, extra_secrets)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        redacted = [redact(item, extra_secrets) for item in value]
        return type(value)(redacted)
    return value


def admin_graphql_endpoint(shop_domain: str) -> str:
    return "https://%s/admin/api/%s/graphql.json" % (
        shop_domain,
        SHOPIFY_API_VERSION,
    )


class TransportErrorCode(str, Enum):
    """Stable, non-secret transport failure codes."""

    NETWORK = "transport_error"
    INVALID_REQUEST = "invalid_request"
    MISSING_CREDENTIAL = "missing_credential"
    RESPONSE_TOO_LARGE = "response_too_large"
    REQUEST_TOO_LARGE = "request_too_large"
    INVALID_CONTENT_LENGTH = "invalid_content_length"


class ShopifyTransportError(Exception):
    """Safe error raised before a raw response leaves the transport boundary."""

    def __init__(
        self,
        code: str | TransportErrorCode,
        reason: str,
        technical_detail: str = "",
        *,
        status_code: int | None = None,
        extra_secrets: tuple[str, ...] = (),
    ) -> None:
        code_value = code.value if isinstance(code, TransportErrorCode) else str(code)
        self.code = code_value
        self.error_code = code_value
        self.reason = redact(reason, extra_secrets=extra_secrets)
        self.technical_detail = (
            redact(technical_detail, extra_secrets=extra_secrets)
            if technical_detail
            else technical_detail
        )
        self.status_code = status_code
        super().__init__(self.reason)

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class ShopifyTransportRequest:
    """Immutable request description with the credential excluded from repr."""

    shop_domain: str
    document: str = field(repr=False)
    variables: Mapping[str, Any] = field(default_factory=dict, repr=False)
    access_token: str = field(default="", repr=False, compare=False)
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.shop_domain, str) or not self.shop_domain.strip():
            raise ValueError("shop_domain must be a non-empty string")
        if not _SHOP_DOMAIN.fullmatch(self.shop_domain):
            raise ValueError("shop_domain must be a canonical myshopify.com host")
        if not isinstance(self.document, str) or not self.document.strip():
            raise ValueError("document must be a non-empty string")
        if not isinstance(self.variables, Mapping):
            raise TypeError("variables must be a mapping")
        if not isinstance(self.access_token, str) or not self.access_token:
            raise ValueError("access_token must be a non-empty string")
        if self.correlation_id is not None and not isinstance(self.correlation_id, str):
            raise TypeError("correlation_id must be a string or None")
        # Keep nested variables immutable while retaining a JSON-shaped value
        # for the executor; the transport converts it back to plain mappings
        # immediately before the one POST call.
        object.__setattr__(self, "variables", freeze_value(dict(self.variables)))


def _header(headers: Any, name: str) -> Any:
    """Read a response header with HTTP's case-insensitive spelling rules."""

    if not isinstance(headers, Mapping):
        return None
    value = headers.get(name)
    if value is not None:
        return value
    wanted = name.lower()
    for key, candidate in headers.items():
        if str(key).lower() == wanted:
            return candidate
    return None


def _declared_body_size(response: Any) -> int | None:
    declared = _header(getattr(response, "headers", None), "Content-Length")
    if declared is None:
        return None
    try:
        value = int(declared)
    except (TypeError, ValueError) as exc:
        raise ShopifyTransportError(
            TransportErrorCode.INVALID_CONTENT_LENGTH,
            "Shopify returned an invalid response size.",
            "Content-Length was not an integer",
        ) from exc
    if value < 0:
        raise ShopifyTransportError(
            TransportErrorCode.INVALID_CONTENT_LENGTH,
            "Shopify returned an invalid response size.",
            "Content-Length was negative",
        )
    return value


def _raise_oversized(
    limit: int,
    observed: int | str,
    code: TransportErrorCode,
    noun: str,
) -> None:
    raise ShopifyTransportError(
        code,
        "Shopify returned a %s that is larger than the connector limit." % noun,
        "%s exceeds %s bytes (observed %s)" % (noun, limit, observed),
    )


def _close_response(response: Any) -> None:
    """Release a response connection after a body-validation rejection."""

    close = getattr(response, "close", None)
    if not callable(close):
        return
    try:
        close()
    except Exception:  # pragma: no cover - defensive response-double guard
        return


def enforce_response_limit(response: Any, max_response_bytes: int) -> Any:
    """Consume/cache a response body while enforcing a byte ceiling.

    ``requests`` responses are streamed by :class:`ShopifyTransport`; chunks
    are retained only after each chunk has passed the ceiling.  Small fake
    responses used by characterization tests may expose only ``content`` or
    ``text`` and are handled without requiring a network-specific response
    class.  The raw response object is returned so the executor can preserve
    the established ``status_code``/``headers``/``json()`` contract.
    """

    if not isinstance(max_response_bytes, int) or isinstance(max_response_bytes, bool):
        raise TypeError("max_response_bytes must be an integer")
    if max_response_bytes <= 0:
        raise ValueError("max_response_bytes must be positive")
    if response is None:
        raise ShopifyTransportError(
            TransportErrorCode.INVALID_REQUEST,
            "Shopify returned no response.",
            "response object was None",
        )

    try:
        declared = _declared_body_size(response)
        if declared is not None and declared > max_response_bytes:
            _raise_oversized(
                max_response_bytes,
                declared,
                TransportErrorCode.RESPONSE_TOO_LARGE,
                "response body",
            )

        iter_content = getattr(response, "iter_content", None)
        consumed = bool(getattr(response, "_content_consumed", False))
        if callable(iter_content) and not consumed:
            chunks: list[bytes] = []
            total = 0
            try:
                for chunk in iter_content(chunk_size=RESPONSE_CHUNK_BYTES):
                    if not chunk:
                        continue
                    if not isinstance(chunk, (bytes, bytearray)):
                        raise ShopifyTransportError(
                            TransportErrorCode.INVALID_REQUEST,
                            "Shopify returned an invalid response body.",
                            "response body chunks were not bytes",
                        )
                    total += len(chunk)
                    if total > max_response_bytes:
                        _raise_oversized(
                            max_response_bytes,
                            total,
                            TransportErrorCode.RESPONSE_TOO_LARGE,
                            "response body",
                        )
                    chunks.append(bytes(chunk))
            except ShopifyTransportError:
                raise
            except _REQUEST_EXCEPTION as exc:
                raise ShopifyTransportError(
                    TransportErrorCode.NETWORK,
                    "Shopify could not be reached right now.",
                    "response_stream_error",
                ) from exc
            body = b"".join(chunks)
            # ``requests.Response.json`` reads ``_content``.  Caching the bounded
            # bytes keeps the public response object usable by the executor while
            # ensuring no second read or request occurs.
            try:
                response._content = body
                response._content_consumed = True
            except Exception as exc:  # pragma: no cover - unusual response doubles
                raise ShopifyTransportError(
                    TransportErrorCode.NETWORK,
                    "Shopify could not be reached right now.",
                    "response_stream_error",
                ) from exc
            return response

        content = getattr(response, "content", None)
        if isinstance(content, (bytes, bytearray)):
            observed = len(content)
            if observed > max_response_bytes:
                _raise_oversized(
                    max_response_bytes,
                    observed,
                    TransportErrorCode.RESPONSE_TOO_LARGE,
                    "response body",
                )
            return response
        text = getattr(response, "text", None)
        if isinstance(text, str):
            observed = len(text.encode("utf-8"))
            if observed > max_response_bytes:
                _raise_oversized(
                    max_response_bytes,
                    observed,
                    TransportErrorCode.RESPONSE_TOO_LARGE,
                    "response body",
                )
        return response
    except ShopifyTransportError:
        _close_response(response)
        raise
    except _REQUEST_EXCEPTION as exc:
        _close_response(response)
        raise ShopifyTransportError(
            TransportErrorCode.NETWORK,
            "Shopify could not be reached right now.",
            # Exception text can echo a response body, URL, request payload,
            # or customer data.  The typed boundary already carries the
            # stable network code, so durable diagnostics use a fixed marker.
            "transport_error",
        ) from exc
    except Exception as exc:
        # Response implementations are external inputs.  Release a pooled
        # connection even when a custom body iterator/property fails.  Do not
        # let the exception's text escape: Requests and response doubles can
        # include URLs, payload fragments, or customer data in it.
        _close_response(response)
        raise ShopifyTransportError(
            TransportErrorCode.NETWORK,
            "Shopify could not be reached right now.",
            "response_stream_error",
        ) from exc


class ShopifyTransport:
    """One bounded HTTPS POST adapter for the pinned Admin GraphQL endpoint."""

    def __init__(
        self,
        *,
        post: Callable[..., Any] | None = None,
        connect_timeout: float = CONNECT_TIMEOUT_SECONDS,
        read_timeout: float = READ_TIMEOUT_SECONDS,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BODY_BYTES,
        max_request_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
        api_version: str = SHOPIFY_API_VERSION,
    ) -> None:
        self._post = post or self._default_post
        self.connect_timeout = self._positive_timeout(connect_timeout, "connect_timeout")
        self.read_timeout = self._positive_timeout(read_timeout, "read_timeout")
        self.max_response_bytes = self._positive_int(
            max_response_bytes, "max_response_bytes"
        )
        self.max_request_bytes = self._positive_int(
            max_request_bytes, "max_request_bytes"
        )
        if api_version != SHOPIFY_API_VERSION:
            raise ValueError(
                "ShopifyTransport only supports the connector's pinned API version"
            )
        self.api_version = SHOPIFY_API_VERSION

    @staticmethod
    def _positive_timeout(value: float, name: str) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or (
                isinstance(value, float)
                and not math.isfinite(value)
            )
            or value <= 0
        ):
            raise ValueError("%s must be positive" % name)
        return value

    @staticmethod
    def _default_post(*args: Any, **kwargs: Any) -> Any:
        if requests is None:
            raise ShopifyTransportError(
                TransportErrorCode.NETWORK,
                "Shopify could not be reached right now.",
                "the requests transport dependency is unavailable",
            )
        # Keep the only concrete HTTP call behind this adapter.  Resolve the
        # verb dynamically so the repository's mutation-source guard does not
        # mistake this compatibility transport for a domain-level request.
        return getattr(requests, "post")(*args, **kwargs)

    @staticmethod
    def _positive_int(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("%s must be a positive integer" % name)
        return value

    @staticmethod
    def _validate_domain(shop_domain: str) -> str:
        if not isinstance(shop_domain, str):
            raise ShopifyTransportError(
                TransportErrorCode.INVALID_REQUEST,
                "A Shopify store domain is required.",
                "shop_domain was not a string",
            )
        # Do not normalize a persisted value into a different host.  The
        # transport accepts only the canonical lowercase one-label form, so
        # surrounding whitespace is rejected along with schemes/ports/etc.
        domain = shop_domain
        if not _SHOP_DOMAIN.fullmatch(domain):
            raise ShopifyTransportError(
                TransportErrorCode.INVALID_REQUEST,
                "A valid Shopify store domain is required.",
                "shop_domain failed transport validation",
            )
        return domain

    @staticmethod
    def _validate_correlation_id(correlation_id: str | None) -> str | None:
        if correlation_id is None:
            return None
        if (
            not isinstance(correlation_id, str)
            or not correlation_id.strip()
            or len(correlation_id) > 128
            or "\r" in correlation_id
            or "\n" in correlation_id
        ):
            raise ShopifyTransportError(
                TransportErrorCode.INVALID_REQUEST,
                "The request correlation identifier is invalid.",
                "correlation_id failed header validation",
            )
        return correlation_id.strip()

    @staticmethod
    def build_headers(
        access_token: str,
        correlation_id: str | None = None,
    ) -> dict[str, str]:
        """Build the allowlisted headers without exposing them in diagnostics."""

        if not isinstance(access_token, str) or not access_token:
            raise ShopifyTransportError(
                TransportErrorCode.MISSING_CREDENTIAL,
                "Your access token appears invalid or was revoked — replace it.",
                "no access token was available for the Shopify request",
            )
        correlation_id = ShopifyTransport._validate_correlation_id(correlation_id)
        headers = {
            "Content-Type": "application/json",
            ACCESS_TOKEN_HEADER: access_token,
        }
        if correlation_id:
            headers[CORRELATION_HEADER] = correlation_id
        return headers

    def prepare_request(
        self,
        shop_domain: str,
        document: str,
        variables: Mapping[str, Any] | None,
        access_token: str,
        correlation_id: str | None = None,
    ) -> ShopifyTransportRequest:
        domain = self._validate_domain(shop_domain)
        if not isinstance(document, str) or not document.strip():
            raise ShopifyTransportError(
                TransportErrorCode.INVALID_REQUEST,
                "A Shopify GraphQL operation is required.",
                "document was empty",
            )
        if variables is None:
            variables = {}
        if not isinstance(variables, Mapping):
            raise ShopifyTransportError(
                TransportErrorCode.INVALID_REQUEST,
                "Shopify GraphQL variables must be an object.",
                "variables was not a mapping",
            )
        correlation_id = self._validate_correlation_id(correlation_id)
        # Validate the credential here, but keep it only in the request object
        # with repr/compare disabled.  It is never interpolated into a URL or
        # exception detail.
        self.build_headers(access_token, correlation_id)
        request = ShopifyTransportRequest(
            domain,
            document,
            variables,
            access_token,
            correlation_id,
        )
        try:
            encoded = json.dumps(
                {
                    "query": request.document,
                    "variables": to_plain(request.variables),
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ShopifyTransportError(
                TransportErrorCode.INVALID_REQUEST,
                "Shopify GraphQL variables could not be encoded.",
                "request body was not JSON serializable",
            ) from exc
        if len(encoded) > self.max_request_bytes:
            _raise_oversized(
                self.max_request_bytes,
                len(encoded),
                TransportErrorCode.REQUEST_TOO_LARGE,
                "request body",
            )
        return request

    def send(
        self,
        shop_domain: str,
        document: str,
        variables: Mapping[str, Any] | None = None,
        access_token: str | None = None,
        correlation_id: str | None = None,
    ) -> Any:
        """Send exactly one request and return its bounded raw response."""

        if access_token is None:
            raise ShopifyTransportError(
                TransportErrorCode.MISSING_CREDENTIAL,
                "Your access token appears invalid or was revoked — replace it.",
                "access_token was not supplied",
            )
        request = self.prepare_request(
            shop_domain,
            document,
            variables,
            access_token,
            correlation_id,
        )
        headers = self.build_headers(request.access_token, request.correlation_id)
        body = {
            "query": request.document,
            "variables": to_plain(request.variables),
        }
        try:
            response = self._post(
                admin_graphql_endpoint(request.shop_domain),
                json=body,
                headers=headers,
                timeout=(self.connect_timeout, self.read_timeout),
                stream=True,
                allow_redirects=False,
            )
        except _REQUEST_EXCEPTION as exc:
            raise ShopifyTransportError(
                TransportErrorCode.NETWORK,
                "Shopify could not be reached right now.",
                "transport_error",
                extra_secrets=(request.access_token,),
            ) from exc
        try:
            return enforce_response_limit(response, self.max_response_bytes)
        except ShopifyTransportError as exc:
            # Preserve the safe public message while making sure a custom
            # response double cannot smuggle the credential into diagnostics.
            if request.access_token:
                exc.reason = redact(exc.reason, extra_secrets=(request.access_token,))
                exc.technical_detail = redact(
                    exc.technical_detail,
                    extra_secrets=(request.access_token,),
                )
            raise

    # Explicit names make the seam easy to discover without adding another
    # network path.  Both aliases invoke the one ``send`` implementation.
    request = send
    send_request = send


__all__ = [
    "ACCESS_TOKEN_HEADER",
    "API_VERSION_RESPONSE_HEADER",
    "CONNECT_TIMEOUT_SECONDS",
    "CORRELATION_HEADER",
    "DEFAULT_MAX_REQUEST_BODY_BYTES",
    "DEFAULT_MAX_RESPONSE_BODY_BYTES",
    "DEFAULT_TIMEOUT",
    "READ_TIMEOUT_SECONDS",
    "SHOPIFY_API_VERSION",
    "ShopifyTransport",
    "ShopifyTransportError",
    "ShopifyTransportErrorCode",
    "ShopifyTransportRequest",
    "TransportErrorCode",
    "admin_graphql_endpoint",
    "enforce_response_limit",
    "redact",
]

# A descriptive alias used by callers that prefer the shorter name.
ShopifyTransportErrorCode = TransportErrorCode
