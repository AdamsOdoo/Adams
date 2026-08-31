"""One-response Shopify GraphQL normalization and typed execution boundary."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from ...domain.immutability import to_plain
from .cost import CostMetadata
from .graphql_types import (
    GraphQLError,
    GraphQLResult,
    GraphQLUserError,
    ShopifyGraphQLExecutionError,
    _freeze_json,
    _header,
    _safe_request_id,
)
from .operation_registry import ShopifyOperationRegistry, ShopifyOperationSpec
from .transport import (
    API_VERSION_RESPONSE_HEADER,
    DEFAULT_MAX_RESPONSE_BODY_BYTES,
    SHOPIFY_API_VERSION,
    ShopifyTransportError,
    TransportErrorCode,
    enforce_response_limit,
    redact,
)


# These values intentionally mirror the legacy model's fixed job taxonomy.  A
# typed GraphQL code is carried alongside them; the compatibility facade does
# not add a seventeenth legacy job class.
ERROR_TEMPORARY = "shopify_temporary_server_network"
ERROR_AUTH = "shopify_permission_scope_auth"
ERROR_THROTTLE = "shopify_throttling_rate_limit"
ERROR_UNKNOWN = "unknown_system_error"
ERROR_DATA_SHAPE = "data_shape_schema_mismatch"
ERROR_API_VERSION = "odoo_validation_configuration"
ERROR_COST_EXCEEDED = "shopify_cost_exceeded"

MAX_COST_EXCEEDED = "MAX_COST_EXCEEDED"
RESPONSE_TOO_LARGE = "response_too_large"
OPERATION_VERSION_MISMATCH = "operation_version_mismatch"

REASON_TOKEN_INVALID = "Your access token appears invalid or was revoked — replace it."
REASON_TEMPORARY = "Shopify could not be reached right now — this is usually temporary."
REASON_THROTTLED = "Shopify is asking us to slow down — try again shortly."
REASON_UNKNOWN = (
    "Shopify returned a response we could not interpret — try again, "
    "and contact support if it persists."
)
REASON_DATA_SHAPE = (
    "Shopify returned a data shape the connector does not support — "
    "check the configured API version and connector compatibility."
)
REASON_API_VERSION = (
    "Shopify did not serve the Admin API version this connector is built "
    "for, so the response was refused rather than acted on. This needs a "
    "configuration or connector-version fix, not a retry."
)
REASON_COST_EXCEEDED = (
    "Shopify rejected this request because its query cost exceeded the "
    "available budget."
)


def _cost_from_body(body: Mapping[str, Any]) -> CostMetadata | None:
    extensions = body.get("extensions")
    if not isinstance(extensions, Mapping):
        return None
    return CostMetadata.from_payload(extensions.get("cost"))


def _cost_from_error(error: Mapping[str, Any]) -> CostMetadata | None:
    extensions = error.get("extensions")
    if not isinstance(extensions, Mapping):
        return None
    return CostMetadata.from_payload(extensions.get("cost"))


def _safe_api_version(value: Any) -> str:
    """Keep untrusted version-header diagnostics to a safe fixed shape."""

    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}", value):
        return value
    return "invalid"


def _parse_graphql_error(
    value: Any, extra_secrets: tuple[str, ...] = ()
) -> GraphQLError:
    if not isinstance(value, Mapping):
        raise ValueError("top-level GraphQL errors must be objects")
    extensions = value.get("extensions")
    if not isinstance(extensions, Mapping):
        extensions = {}
    path = value.get("path")
    if not isinstance(path, Sequence) or isinstance(path, (str, bytes)):
        path = ()
    return GraphQLError(
        redact(
            value.get("message") or "Shopify returned a GraphQL error.",
            extra_secrets=extra_secrets,
        ),
        redact(extensions.get("code"), extra_secrets=extra_secrets),
        tuple(path),
        redact(extensions.get("requestId"), extra_secrets=extra_secrets)
        if extensions.get("requestId") is not None
        else None,
    )


def _parse_user_error(
    value: Any, extra_secrets: tuple[str, ...] = ()
) -> GraphQLUserError:
    if not isinstance(value, Mapping):
        raise ValueError("userErrors entries must be objects")
    fields = value.get("field", value.get("fields", ()))
    if fields is None:
        fields = ()
    if isinstance(fields, str):
        fields = (fields,)
    if not isinstance(fields, Sequence):
        fields = ()
    return GraphQLUserError(
        redact(
            value.get("message") or "Shopify rejected the requested change.",
            extra_secrets=extra_secrets,
        ),
        tuple(redact(field, extra_secrets=extra_secrets) for field in fields),
        redact(value.get("code"), extra_secrets=extra_secrets),
    )


def _user_errors(
    value: Any,
    depth: int = 0,
    extra_secrets: tuple[str, ...] = (),
) -> list[GraphQLUserError]:
    if depth > 8:
        return []
    result: list[GraphQLUserError] = []
    if isinstance(value, Mapping):
        candidate = value.get("userErrors")
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            for item in candidate:
                try:
                    result.append(_parse_user_error(item, extra_secrets=extra_secrets))
                except (TypeError, ValueError):
                    # A malformed optional user-error entry is represented by
                    # the surrounding response shape, not leaked as raw data.
                    continue
        for child in value.values():
            result.extend(_user_errors(child, depth + 1, extra_secrets))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            result.extend(_user_errors(child, depth + 1, extra_secrets))
    return result


class GraphQLExecutor:
    """Execute one registered/document operation and normalize one response."""

    def __init__(
        self,
        transport: Any = None,
        *,
        operation_registry: ShopifyOperationRegistry | None = None,
        registry: ShopifyOperationRegistry | None = None,
        api_version: str = SHOPIFY_API_VERSION,
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BODY_BYTES,
    ) -> None:
        if api_version != SHOPIFY_API_VERSION:
            raise ValueError(
                "GraphQLExecutor only supports the connector's pinned API version"
            )
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes <= 0
        ):
            raise ValueError("max_response_bytes must be a positive integer")
        self.transport = transport
        self.operation_registry = (
            operation_registry
            if operation_registry is not None
            else registry
        )
        self.api_version = SHOPIFY_API_VERSION
        self.max_response_bytes = max_response_bytes

    def _operation_document(self, operation: Any) -> str:
        spec = operation
        if self.operation_registry is not None:
            if isinstance(operation, str) and operation in self.operation_registry:
                spec = self.operation_registry.require_operation(operation)
            elif isinstance(operation, ShopifyOperationSpec):
                registered = self.operation_registry.get(operation.operation_key)
                if registered is None or registered != operation:
                    raise ShopifyGraphQLExecutionError(
                        ERROR_API_VERSION,
                        "The Shopify operation is not registered.",
                        "operation spec was not present in the registry",
                        error_code="OPERATION_NOT_REGISTERED",
                    )
                spec = registered
            else:
                raise ShopifyGraphQLExecutionError(
                    ERROR_API_VERSION,
                    "The Shopify operation is not registered.",
                    "operation must be a registered key or spec",
                    error_code="OPERATION_NOT_REGISTERED",
                )
        if isinstance(spec, ShopifyOperationSpec):
            if spec.api_version != self.api_version:
                raise ShopifyGraphQLExecutionError(
                    ERROR_API_VERSION,
                    REASON_API_VERSION,
                    "operation api version %s != connector %s" % (
                        spec.api_version,
                        self.api_version,
                    ),
                    error_code=OPERATION_VERSION_MISMATCH,
                )
            return spec.document
        if not isinstance(spec, str) or not spec.strip():
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                "A Shopify GraphQL operation is required.",
                "operation document was empty",
                error_code="INVALID_OPERATION",
            )
        return spec

    def execute(
        self,
        operation: Any,
        shop_domain: str | None = None,
        access_token: str | None = None,
        variables: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        **aliases: Any,
    ) -> GraphQLResult:
        """Send one operation through the injected transport.

        ``store_domain`` and ``token`` are accepted as descriptive aliases for
        test/facade callers.  They do not trigger a credential lookup; the
        credential is always supplied by the caller that owns that boundary.
        """

        if shop_domain is None:
            shop_domain = aliases.pop("store_domain", None)
        if access_token is None:
            access_token = aliases.pop("token", None)
        if correlation_id is None:
            correlation_id = aliases.pop("request_id", None)
        if aliases:
            unexpected = ", ".join(sorted(aliases))
            raise TypeError("unexpected execute arguments: %s" % unexpected)
        document = self._operation_document(operation)
        if not shop_domain:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                "A Shopify store domain is required.",
                "shop_domain was empty",
                error_code="INVALID_REQUEST",
            )
        if not access_token:
            raise ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                REASON_TOKEN_INVALID,
                "access_token was not supplied",
                error_code="MISSING_CREDENTIAL",
                credential_invalid=True,
            )
        variables = {} if variables is None else variables
        if not isinstance(variables, Mapping):
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                "Shopify GraphQL variables must be an object.",
                "variables was not a mapping",
                error_code="INVALID_VARIABLES",
            )
        try:
            safe_variables = _freeze_json(dict(variables), "variables")
            plain_variables = to_plain(safe_variables)
        except (TypeError, ValueError) as exc:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                "Shopify GraphQL variables must be JSON values.",
                # The validation path walks caller-provided keys and can
                # otherwise echo request-derived identifiers into durable
                # diagnostics.  Keep this detail fixed; the public code is
                # already sufficient for remediation.
                "variables failed JSON validation",
                error_code="INVALID_VARIABLES",
            ) from exc
        sender = getattr(self.transport, "send", None)
        if not callable(sender):
            sender = self.transport if callable(self.transport) else None
        if sender is None:
            raise ShopifyGraphQLExecutionError(
                ERROR_TEMPORARY,
                REASON_TEMPORARY,
                "no Shopify transport was configured",
                error_code="TRANSPORT_UNCONFIGURED",
            )
        try:
            if correlation_id is None:
                response = sender(shop_domain, document, plain_variables, access_token)
            else:
                response = sender(
                    shop_domain,
                    document,
                    plain_variables,
                    access_token,
                    correlation_id=correlation_id,
                )
        except ShopifyTransportError as exc:
            raise self._from_transport_error(
                exc,
                extra_secrets=(access_token,),
            ) from exc
        except Exception as exc:  # transport boundary fails closed
            raise ShopifyGraphQLExecutionError(
                ERROR_TEMPORARY,
                REASON_TEMPORARY,
                "transport_error",
                error_code=TransportErrorCode.NETWORK.value,
                extra_secrets=(access_token,),
            ) from exc
        return self.normalize_response(
            response,
            extra_secrets=(access_token,),
        )

    def _from_transport_error(
        self,
        error: ShopifyTransportError,
        extra_secrets: tuple[str, ...] = (),
    ) -> ShopifyGraphQLExecutionError:
        if error.code == TransportErrorCode.MISSING_CREDENTIAL.value:
            error_class = ERROR_AUTH
            reason = REASON_TOKEN_INVALID
            credential_invalid = True
        elif error.code == TransportErrorCode.NETWORK.value:
            error_class = ERROR_TEMPORARY
            reason = REASON_TEMPORARY
            credential_invalid = False
        else:
            error_class = ERROR_UNKNOWN
            reason = REASON_UNKNOWN
            credential_invalid = False
        return ShopifyGraphQLExecutionError(
            error_class,
            reason,
            error.technical_detail,
            error_code=error.code,
            credential_invalid=credential_invalid,
            status_code=error.status_code,
            extra_secrets=extra_secrets,
        )

    @staticmethod
    def _technical_detail(
        response: Any,
        extra: str | None = None,
        extra_secrets: tuple[str, ...] = (),
    ) -> str:
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and not isinstance(status_code, bool):
            status = str(status_code)
        elif isinstance(status_code, str) and status_code.isdigit():
            status = status_code[:3]
        else:
            status = "unknown"
        parts = ["HTTP %s" % status]
        if extra:
            context = str(extra).strip()
            if context in {
                "malformed top-level errors",
                "graphql_error",
                "graphql_request_id_present",
            }:
                parts.append(context)
            elif context.startswith("graphql_code="):
                code = context[len("graphql_code="):].strip()
                if code and len(code) <= 64 and re.fullmatch(r"[A-Za-z0-9_.-]+", code):
                    parts.append("graphql_code=" + code)
                else:
                    parts.append("graphql_error")
            else:
                # Callers may pass untrusted response-derived context; do not
                # copy it into evidence/log fields.  Keep only a fixed marker.
                parts.append("graphql_error")
        return redact(" ".join(parts), extra_secrets=extra_secrets)

    def _served_version(
        self,
        response: Any,
        extra_secrets: tuple[str, ...] = (),
    ) -> str:
        served = _header(
            getattr(response, "headers", None), API_VERSION_RESPONSE_HEADER
        )
        if not served:
            raise ShopifyGraphQLExecutionError(
                ERROR_API_VERSION,
                REASON_API_VERSION,
                "no %s header on the response; expected %s"
                % (API_VERSION_RESPONSE_HEADER, self.api_version),
                error_code="MISSING_SERVED_VERSION",
                extra_secrets=extra_secrets,
            )
        if served != self.api_version:
            raise ShopifyGraphQLExecutionError(
                ERROR_API_VERSION,
                REASON_API_VERSION,
                "served api version %s != connector %s" % (
                    _safe_api_version(served), self.api_version
                ),
                error_code=OPERATION_VERSION_MISMATCH,
                extra_secrets=extra_secrets,
            )
        return served

    def _error_from_graphql_errors(
        self,
        errors: Sequence[Any],
        response: Any,
        cost: CostMetadata | None,
        extra_secrets: tuple[str, ...] = (),
    ) -> ShopifyGraphQLExecutionError:
        try:
            parsed = tuple(
                _parse_graphql_error(value, extra_secrets=extra_secrets)
                for value in errors
            )
        except (TypeError, ValueError):
            return ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                self._technical_detail(
                    response,
                    "malformed top-level errors",
                    extra_secrets=extra_secrets,
                ),
                error_code="MALFORMED_GRAPHQL_ERRORS",
                status_code=getattr(response, "status_code", None),
                extra_secrets=extra_secrets,
            )
        first = parsed[0] if parsed else GraphQLError(REASON_UNKNOWN)
        code = first.code
        if cost is None and errors and isinstance(errors[0], Mapping):
            try:
                cost = _cost_from_error(errors[0])
            except (TypeError, ValueError):
                return ShopifyGraphQLExecutionError(
                    ERROR_UNKNOWN,
                    REASON_UNKNOWN,
                    self._technical_detail(
                        response,
                        "invalid_cost_metadata",
                        extra_secrets=extra_secrets,
                    ),
                    error_code="INVALID_COST_METADATA",
                    status_code=getattr(response, "status_code", None),
                    extra_secrets=extra_secrets,
                )
        detail_extra = (
            "graphql_request_id_present"
            if first.request_id
            else "graphql_code=%s" % code
            if code
            else "graphql_error"
        )
        technical = self._technical_detail(
            response,
            detail_extra,
            extra_secrets=extra_secrets,
        )
        kwargs = {
            "error_code": code,
            "request_id": first.request_id,
            "cost": cost,
            "status_code": getattr(response, "status_code", None),
            "extra_secrets": extra_secrets,
        }
        if code == "ACCESS_DENIED":
            return ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                REASON_TOKEN_INVALID,
                technical,
                credential_invalid=True,
                **kwargs,
            )
        if code == "SHOP_INACTIVE":
            return ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                "This store is inactive.",
                technical,
                **kwargs,
            )
        if code == "THROTTLED":
            return ShopifyGraphQLExecutionError(
                ERROR_THROTTLE,
                REASON_THROTTLED,
                technical,
                **kwargs,
            )
        if code == "INTERNAL_SERVER_ERROR":
            return ShopifyGraphQLExecutionError(
                ERROR_TEMPORARY,
                REASON_TEMPORARY,
                technical,
                **kwargs,
            )
        normalized_code = str(code or "").replace("_", "").lower()
        normalized_message = first.message.lower()
        if (
            normalized_code in {"selectionmismatch", "schemaselection", "undefinedfield"}
            or "must have a selection of subfields" in normalized_message
            or "selection mismatch" in normalized_message
        ):
            return ShopifyGraphQLExecutionError(
                ERROR_DATA_SHAPE,
                REASON_DATA_SHAPE,
                technical,
                **kwargs,
            )
        if code == MAX_COST_EXCEEDED:
            return ShopifyGraphQLExecutionError(
                ERROR_COST_EXCEEDED,
                REASON_COST_EXCEEDED,
                technical,
                **kwargs,
            )
        return ShopifyGraphQLExecutionError(
            ERROR_UNKNOWN,
            REASON_UNKNOWN,
            technical,
            **kwargs,
        )

    def normalize_response(
        self,
        response: Any,
        *,
        extra_secrets: tuple[str, ...] = (),
    ) -> GraphQLResult:
        """Normalize one raw response, matching legacy error ordering."""

        try:
            enforce_response_limit(response, self.max_response_bytes)
        except ShopifyTransportError as exc:
            raise self._from_transport_error(exc, extra_secrets=extra_secrets) from exc
        detail = lambda extra=None: self._technical_detail(  # noqa: E731
            response,
            extra,
            extra_secrets=extra_secrets,
        )
        status_code = getattr(response, "status_code", None)
        if status_code == 401:
            raise ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                REASON_TOKEN_INVALID,
                detail(),
                error_code="HTTP_401",
                credential_invalid=True,
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        if status_code == 402:
            raise ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                "Shopify has frozen this store, most commonly for a billing/payment issue — resolve it in Shopify, then retry.",
                detail(),
                error_code="HTTP_402",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        if status_code == 423:
            raise ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                "This store has been locked by Shopify.",
                detail(),
                error_code="HTTP_423",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        if status_code == 403:
            raise ShopifyGraphQLExecutionError(
                ERROR_AUTH,
                "Shopify has flagged this store as fraudulent.",
                detail(),
                error_code="HTTP_403",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        if status_code == 429:
            raise ShopifyGraphQLExecutionError(
                ERROR_THROTTLE,
                REASON_THROTTLED,
                detail(),
                error_code="HTTP_429",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        if isinstance(status_code, int) and status_code >= 500:
            raise ShopifyGraphQLExecutionError(
                ERROR_TEMPORARY,
                REASON_TEMPORARY,
                detail(),
                error_code="HTTP_5XX",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        if status_code != 200:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                detail(),
                error_code="HTTP_%s" % status_code,
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        try:
            body = response.json()
        except (ValueError, TypeError, AttributeError) as exc:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                detail(),
                error_code="MALFORMED_JSON",
                status_code=status_code,
                extra_secrets=extra_secrets,
            ) from exc
        if not isinstance(body, Mapping):
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                detail(),
                error_code="INVALID_JSON_SHAPE",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        try:
            cost = _cost_from_body(body)
        except (TypeError, ValueError) as exc:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                detail(),
                error_code="INVALID_COST_METADATA",
                status_code=status_code,
                extra_secrets=extra_secrets,
            ) from exc
        errors = body.get("errors")
        if "errors" in body:
            if not isinstance(errors, Sequence) or isinstance(errors, (str, bytes)):
                raise ShopifyGraphQLExecutionError(
                    ERROR_UNKNOWN,
                    REASON_UNKNOWN,
                    detail("malformed top-level errors"),
                    error_code="MALFORMED_GRAPHQL_ERRORS",
                    status_code=status_code,
                    extra_secrets=extra_secrets,
                )
            if errors:
                raise self._error_from_graphql_errors(
                    errors,
                    response,
                    cost,
                    extra_secrets=extra_secrets,
                )
        served_version = self._served_version(response, extra_secrets=extra_secrets)
        data = body.get("data")
        if not isinstance(data, Mapping):
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                detail(),
                error_code="INVALID_JSON_DATA",
                status_code=status_code,
                extra_secrets=extra_secrets,
            )
        user_errors = tuple(_user_errors(data, extra_secrets=extra_secrets))
        request_id = _safe_request_id(
            _header(getattr(response, "headers", None), "X-Request-ID")
        )
        try:
            return GraphQLResult(
                data=data,
                errors=(),
                user_errors=user_errors,
                cost=cost,
                request_id=request_id,
                served_version=served_version,
                status_code=status_code,
            )
        except (TypeError, ValueError) as exc:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                "Shopify returned data outside the JSON contract.",
                error_code="INVALID_JSON_DATA",
                status_code=status_code,
                extra_secrets=extra_secrets,
            ) from exc

    # Descriptive aliases keep direct fixture tests readable and all route to
    # the same one-response normalizer.
    normalize = normalize_response
    execute_response = normalize_response


__all__ = [
    "ERROR_API_VERSION",
    "ERROR_AUTH",
    "ERROR_COST_EXCEEDED",
    "ERROR_DATA_SHAPE",
    "ERROR_TEMPORARY",
    "ERROR_THROTTLE",
    "ERROR_UNKNOWN",
    "GraphQLExecutor",
    "MAX_COST_EXCEEDED",
    "OPERATION_VERSION_MISMATCH",
    "RESPONSE_TOO_LARGE",
    "REASON_API_VERSION",
    "REASON_COST_EXCEEDED",
    "REASON_DATA_SHAPE",
    "REASON_THROTTLED",
    "REASON_TEMPORARY",
    "REASON_TOKEN_INVALID",
    "REASON_UNKNOWN",
]
