"""Compatibility exports for the split Shopify GraphQL boundary.

The typed value objects/cost observations live in :mod:`graphql_types` and
:mod:`cost`; one-response execution/normalization lives in
:mod:`response_normalizer`.  This module remains the stable import surface for
existing callers and fixtures.
"""

from .cost import CostMetadata, ThrottleStatus, _number
from .graphql_types import (
    GraphQLError,
    GraphQLResult,
    GraphQLUserError,
    ShopifyGraphQLExecutionError,
    _freeze_json,
    _header,
    _safe_request_id,
)
from .response_normalizer import (
    ERROR_API_VERSION,
    ERROR_AUTH,
    ERROR_COST_EXCEEDED,
    ERROR_DATA_SHAPE,
    ERROR_TEMPORARY,
    ERROR_THROTTLE,
    ERROR_UNKNOWN,
    MAX_COST_EXCEEDED,
    OPERATION_VERSION_MISMATCH,
    REASON_API_VERSION,
    REASON_COST_EXCEEDED,
    REASON_DATA_SHAPE,
    REASON_THROTTLED,
    REASON_TEMPORARY,
    REASON_TOKEN_INVALID,
    REASON_UNKNOWN,
    RESPONSE_TOO_LARGE,
    GraphQLExecutor,
    _cost_from_body,
    _cost_from_error,
    _parse_graphql_error,
    _parse_user_error,
    _user_errors,
)


# Short aliases are intentionally additive; the longer names remain the
# canonical documentation vocabulary.
GraphQLCost = CostMetadata
GraphQLCostMetadata = CostMetadata
GraphQLThrottleStatus = ThrottleStatus
GraphQLExecutorError = ShopifyGraphQLExecutionError
ExecutorError = ShopifyGraphQLExecutionError
ShopifyExecutor = GraphQLExecutor
ShopifyExecutorError = ShopifyGraphQLExecutionError


__all__ = [
    "CostMetadata",
    "ERROR_API_VERSION",
    "ERROR_AUTH",
    "ERROR_COST_EXCEEDED",
    "ERROR_DATA_SHAPE",
    "ERROR_TEMPORARY",
    "ERROR_THROTTLE",
    "ERROR_UNKNOWN",
    "ExecutorError",
    "GraphQLCost",
    "GraphQLCostMetadata",
    "GraphQLError",
    "GraphQLExecutor",
    "GraphQLExecutorError",
    "GraphQLResult",
    "GraphQLThrottleStatus",
    "GraphQLUserError",
    "MAX_COST_EXCEEDED",
    "OPERATION_VERSION_MISMATCH",
    "RESPONSE_TOO_LARGE",
    "ShopifyGraphQLExecutionError",
    "ShopifyExecutor",
    "ShopifyExecutorError",
    "ThrottleStatus",
]
