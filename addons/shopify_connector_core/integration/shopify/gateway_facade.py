"""Rollback-safe facade around the existing Shopify API-client surface."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from .graphql_executor import (
    CostMetadata,
    GraphQLError,
    GraphQLExecutor,
    GraphQLResult,
    GraphQLUserError,
    ShopifyGraphQLExecutionError,
    ERROR_API_VERSION,
    ERROR_UNKNOWN,
    OPERATION_VERSION_MISMATCH,
    REASON_API_VERSION,
    REASON_UNKNOWN,
)
from .transport import SHOPIFY_API_VERSION


class ShopifyFacadeMode(str, Enum):
    """Explicit migration modes; legacy delegation is the default."""

    LEGACY = "legacy"
    TYPED = "typed"


def _mode(value: str | ShopifyFacadeMode) -> ShopifyFacadeMode:
    if isinstance(value, ShopifyFacadeMode):
        return value
    aliases = {
        "legacy_delegate": ShopifyFacadeMode.LEGACY,
        "compatibility": ShopifyFacadeMode.LEGACY,
        "new": ShopifyFacadeMode.TYPED,
    }
    value = str(value)
    if value in aliases:
        return aliases[value]
    try:
        return ShopifyFacadeMode(value)
    except ValueError as exc:
        raise ValueError("unsupported Shopify facade mode: %s" % value) from exc


def _legacy_users(value: Any, depth: int = 0) -> list[GraphQLUserError]:
    if depth > 8:
        return []
    result: list[GraphQLUserError] = []
    if isinstance(value, Mapping):
        candidate = value.get("userErrors")
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            for item in candidate:
                if not isinstance(item, Mapping):
                    continue
                fields = item.get("field", item.get("fields", ()))
                if fields is None:
                    fields = ()
                if isinstance(fields, str):
                    fields = (fields,)
                if not isinstance(fields, Sequence):
                    fields = ()
                result.append(
                    GraphQLUserError(
                        item.get("message") or "Shopify rejected the requested change.",
                        tuple(fields),
                        item.get("code"),
                    )
                )
        for child in value.values():
            result.extend(_legacy_users(child, depth + 1))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            result.extend(_legacy_users(child, depth + 1))
    return result


class ShopifyGatewayFacade:
    """Expose legacy calls and an opt-in typed view with one delegate call.

    The facade intentionally does not read credentials, construct URLs or
    issue HTTP requests.  In both modes ``delegate.execute`` is called once;
    typed mode only adapts the already-normalized legacy result.  This gives a
    deployment a simple rollback switch while preserving domain call sites
    and the legacy client's mutation/request-count semantics.
    """

    def __init__(
        self,
        legacy_delegate: Any,
        *,
        mode: str | ShopifyFacadeMode = ShopifyFacadeMode.LEGACY,
        executor: GraphQLExecutor | None = None,
    ) -> None:
        if legacy_delegate is None:
            raise ValueError("legacy_delegate is required")
        execute = getattr(legacy_delegate, "execute", None)
        if not callable(execute):
            raise TypeError("legacy_delegate must expose execute")
        self._legacy_delegate = legacy_delegate
        self.mode = _mode(mode)
        self.executor = executor

    @property
    def legacy_delegate(self) -> Any:
        return self._legacy_delegate

    @property
    def is_legacy(self) -> bool:
        return self.mode is ShopifyFacadeMode.LEGACY

    def _delegate_execute(self, store: Any, query: str, variables: Mapping[str, Any] | None):
        # Keep the old argument shape exactly.  In particular, do not perform
        # a second credential lookup or call a second transport on adaptation.
        if variables is None:
            return self._legacy_delegate.execute(store, query)
        return self._legacy_delegate.execute(store, query, variables)

    def execute(
        self,
        store: Any,
        query: str,
        variables: Mapping[str, Any] | None = None,
    ) -> Any:
        if self.is_legacy:
            return self._delegate_execute(store, query, variables)
        return self.execute_typed(store, query, variables)

    def execute_legacy(
        self,
        store: Any,
        query: str,
        variables: Mapping[str, Any] | None = None,
    ) -> Any:
        """Force one legacy delegate call regardless of configured mode."""

        return self._delegate_execute(store, query, variables)

    def execute_typed(
        self,
        store: Any,
        query: str,
        variables: Mapping[str, Any] | None = None,
    ) -> GraphQLResult:
        """Adapt one legacy result into the typed result contract."""

        result = self._delegate_execute(store, query, variables)
        if isinstance(result, GraphQLResult):
            return result
        if not isinstance(result, Mapping):
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                "legacy delegate returned a non-mapping result",
                error_code="INVALID_LEGACY_RESULT",
            )
        served_version = result.get("served_version")
        if served_version != SHOPIFY_API_VERSION:
            raise ShopifyGraphQLExecutionError(
                ERROR_API_VERSION,
                REASON_API_VERSION,
                "legacy result served api version did not equal connector version",
                error_code=OPERATION_VERSION_MISMATCH,
            )
        try:
            cost = CostMetadata.from_result_payload(result.get("cost"))
            if cost is None:
                cost = CostMetadata.from_result_payload(
                    result.get("throttle_status")
                )
        except (TypeError, ValueError) as exc:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                "legacy result contained invalid cost metadata",
                error_code="INVALID_COST_METADATA",
            ) from exc
        errors: list[GraphQLError] = []
        raw_errors = result.get("errors")
        if "errors" in result and (
            not isinstance(raw_errors, Sequence)
            or isinstance(raw_errors, (str, bytes))
        ):
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                "legacy result contained malformed GraphQL errors",
                error_code="MALFORMED_GRAPHQL_ERRORS",
            )
        if isinstance(raw_errors, Sequence) and not isinstance(raw_errors, (str, bytes)):
            for item in raw_errors:
                if not isinstance(item, Mapping):
                    raise ShopifyGraphQLExecutionError(
                        ERROR_UNKNOWN,
                        REASON_UNKNOWN,
                        "legacy result contained malformed GraphQL errors",
                        error_code="MALFORMED_GRAPHQL_ERRORS",
                    )
                errors.append(
                    GraphQLError(
                        item.get("message") or REASON_UNKNOWN,
                        item.get("code"),
                        tuple(item.get("path") or ()),
                        item.get("request_id", item.get("requestId")),
                    )
                )
        request_id = result.get("request_id", result.get("requestId"))
        data = result.get("data")
        if not isinstance(data, Mapping):
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                "legacy result contained non-object GraphQL data",
                error_code="INVALID_JSON_DATA",
            )
        return GraphQLResult(
            data=data,
            errors=tuple(errors),
            user_errors=tuple(_legacy_users(result.get("data"))),
            cost=cost,
            request_id=request_id,
            served_version=served_version,
            status_code=result.get("status_code", 200),
        )

    def execute_registered(
        self,
        operation: Any,
        *,
        shop_domain: str,
        access_token: str,
        variables: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> GraphQLResult:
        """Opt-in direct typed operation path for later registered callers.

        It is deliberately not used by ``execute`` and therefore cannot alter
        current domain call sites or remote request counts.  A transport must
        be supplied explicitly when this future-facing method is requested.
        """

        if self.executor is None:
            raise ShopifyGraphQLExecutionError(
                ERROR_UNKNOWN,
                REASON_UNKNOWN,
                "typed operation execution is not configured",
                error_code="EXECUTOR_UNCONFIGURED",
            )
        return self.executor.execute(
            operation,
            shop_domain=shop_domain,
            access_token=access_token,
            variables=variables,
            correlation_id=correlation_id,
        )

    def for_mode(self, mode: str | ShopifyFacadeMode) -> "ShopifyGatewayFacade":
        """Return an equivalent facade with an explicit migration mode."""

        return type(self)(
            self._legacy_delegate,
            mode=mode,
            executor=self.executor,
        )

    def rollback(self) -> "ShopifyGatewayFacade":
        """Return a legacy-delegating facade for immediate rollback."""

        return self.for_mode(ShopifyFacadeMode.LEGACY)


# Compatibility aliases make the seam discoverable under the names used by
# both the roadmap (gateway facade) and the P05 task (client facade).
ShopifyClientFacade = ShopifyGatewayFacade
ShopifyApiClientFacade = ShopifyGatewayFacade
GatewayFacade = ShopifyGatewayFacade
GatewayMode = ShopifyFacadeMode
FacadeMode = ShopifyFacadeMode


__all__ = [
    "FacadeMode",
    "GatewayFacade",
    "GatewayMode",
    "ShopifyApiClientFacade",
    "ShopifyClientFacade",
    "ShopifyFacadeMode",
    "ShopifyGatewayFacade",
]
