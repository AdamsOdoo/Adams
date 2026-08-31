"""Pure contracts for the staged Shopify mutation boundary.

The V1 connector owns admission, database transactions, credentials and the
actual Shopify client.  P08 only extracts the part that can be reviewed in
isolation: a checked-in operation, a canonical JSON request, an immutable
durable intent/readback descriptor, and a normalized one-response result.

There is deliberately no Odoo import, ORM access, credential lookup, HTTP
client, retry loop or readback call in this module.  A gateway receives one
already-authorized delegate and invokes it at most once for one admitted
request.  The runtime above this boundary is still responsible for committing
the intent, claiming attempts, scheduling readback and choosing retry policy.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from ...domain.identifiers import require_key, require_shopify_gid
from ...domain.immutability import freeze_value, to_plain
from .operation_registry import (
    ReadbackMetadata,
    ShopifyOperationRegistry,
    ShopifyOperationSpec,
)


MAX_MUTATION_JSON_BYTES = 1_000_000
MAX_MUTATION_JSON_DEPTH = 16
MAX_MUTATION_COLLECTION_ITEMS = 1_000
MAX_MUTATION_TEXT = 65_536
MAX_USER_ERRORS = 32
MAX_ERROR_FIELDS = 16
MAX_ERROR_FIELD_TEXT = 256
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ERROR_CODE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_GID = re.compile(
    r"^gid://shopify/(?P<kind>[A-Za-z][A-Za-z0-9_]*)/(?P<id>[1-9][0-9]*)$"
)


class MutationOutcome(str, Enum):
    """The only direct result dispositions a mutation adapter can assert."""

    SUCCEEDED = "succeeded"
    FAILED_CLEAN = "failed_clean"
    UNCERTAIN = "uncertain"


class MutationGatewayError(ValueError):
    """A request or response cannot satisfy its checked-in contract."""

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not _ERROR_CODE.fullmatch(code):
            raise ValueError("mutation error code must be non-empty")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("mutation error message must be non-empty")
        self.code = code[:128]
        self.message = message[:MAX_MUTATION_TEXT]
        super().__init__(self.message)


class MutationShapeError(MutationGatewayError):
    """A response was received but does not prove a declared result shape."""


class MutationTransportError(RuntimeError):
    """Delegate transport failure with explicit certainty when available.

    ``after_send=False`` is only for a delegate that can prove that the
    request never left its boundary.  ``None`` is intentionally treated as
    uncertain by the adapter.  Normal ``TimeoutError``/unknown exceptions are
    also uncertain because the remote side may have applied the mutation.
    """

    def __init__(
        self,
        message: str = "Shopify mutation transport failed.",
        *,
        after_send: bool | None = None,
        code: str = "shopify_temporary_server_network",
    ) -> None:
        if not isinstance(after_send, (bool, type(None))):
            raise TypeError("after_send must be bool or None")
        self.after_send = after_send
        self.code = (
            code
            if isinstance(code, str) and _ERROR_CODE.fullmatch(code)
            else "shopify_temporary_server_network"
        )
        # Technical messages are intentionally not propagated to the public
        # result.  Keep only a bounded type-like marker for debugging/tests.
        self.safe_message = "Shopify mutation transport did not complete."
        super().__init__(self.safe_message)


def _validate_json(value: Any, path: str = "$", depth: int = 0) -> None:
    """Validate bounded JSON without coercing attacker-controlled values."""

    if depth > MAX_MUTATION_JSON_DEPTH:
        raise MutationGatewayError("json_depth_exceeded", "Mutation JSON nesting is too deep.")
    if value is None or isinstance(value, (str, bool, int)):
        if isinstance(value, str) and len(value) > MAX_MUTATION_TEXT:
            raise MutationGatewayError("json_value_too_large", "Mutation text value is too large.")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MutationGatewayError("invalid_json", "Mutation JSON contains a non-finite number.")
        return
    if isinstance(value, Mapping):
        if len(value) > MAX_MUTATION_COLLECTION_ITEMS:
            raise MutationGatewayError("json_collection_too_large", "Mutation object is too large.")
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise MutationGatewayError("invalid_json", "Mutation object keys must be non-empty strings.")
            _validate_json(item, f"{path}.{key}", depth + 1)
        return
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_MUTATION_COLLECTION_ITEMS:
            raise MutationGatewayError("json_collection_too_large", "Mutation array is too large.")
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]", depth + 1)
        return
    raise MutationGatewayError(
        "invalid_json",
        "Mutation contract values must be JSON-shaped.",
    )


def freeze_json(value: Any, field_name: str = "value") -> Mapping[str, Any] | tuple[Any, ...] | Any:
    """Copy and freeze one bounded JSON value for a contract object."""

    try:
        _validate_json(value, field_name)
        frozen = freeze_value(value)
        encoded = json.dumps(to_plain(frozen), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except MutationGatewayError:
        raise
    except (TypeError, ValueError) as exc:
        raise MutationGatewayError("invalid_json", f"{field_name} is not valid JSON.") from exc
    if len(encoded.encode("utf-8")) > MAX_MUTATION_JSON_BYTES:
        raise MutationGatewayError("json_body_too_large", "Mutation JSON body is too large.")
    return frozen


def require_gid(value: Any, kind: str | None = None, field_name: str = "Shopify GID") -> str:
    """Require a canonical numeric Shopify GID, optionally of one kind."""

    try:
        gid = require_shopify_gid(value)
    except (TypeError, ValueError) as exc:
        raise MutationGatewayError("invalid_gid", f"{field_name} is not a canonical Shopify GID.") from exc
    match = _GID.fullmatch(gid)
    if match is None or (kind is not None and match.group("kind") != kind):
        expected = f" {kind}" if kind else ""
        raise MutationGatewayError("invalid_gid", f"{field_name} must be a canonical{expected} Shopify GID.")
    return gid


def require_text(value: Any, field_name: str, *, max_length: int = MAX_MUTATION_TEXT) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise MutationGatewayError("invalid_text", f"{field_name} must be a bounded non-empty string.")
    return value


def require_integer(value: Any, field_name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise MutationGatewayError("invalid_integer", f"{field_name} must be a strict integer.")
    if minimum is not None and value < minimum:
        raise MutationGatewayError("invalid_integer", f"{field_name} must be at least {minimum}.")
    return value


def _canonical_fingerprint(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(to_plain(freeze_json(value, "fingerprint")), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DurableIntentDescriptor:
    """Data the runtime can persist before transport without ORM coupling."""

    operation_key: str
    operation_scope_key: str
    business_intent: Mapping[str, Any]
    preconditions_snapshot: Mapping[str, Any]
    idempotency_key: str
    fingerprint: str = ""

    def __post_init__(self) -> None:
        try:
            require_key(self.operation_key, "intent operation_key")
        except (TypeError, ValueError) as exc:
            raise MutationGatewayError("invalid_operation", "Intent operation key is not allowlisted.") from exc
        require_text(self.operation_scope_key, "operation_scope_key", max_length=512)
        require_text(self.idempotency_key, "idempotency_key", max_length=512)
        if not isinstance(self.business_intent, Mapping):
            raise MutationGatewayError("invalid_intent", "business_intent must be a JSON object.")
        if not isinstance(self.preconditions_snapshot, Mapping):
            raise MutationGatewayError("invalid_intent", "preconditions_snapshot must be a JSON object.")
        business = freeze_json(dict(self.business_intent), "business_intent")
        preconditions = freeze_json(dict(self.preconditions_snapshot), "preconditions_snapshot")
        object.__setattr__(self, "business_intent", business)
        object.__setattr__(self, "preconditions_snapshot", preconditions)
        fingerprint = self.fingerprint
        computed = _canonical_fingerprint({
            "operation_key": self.operation_key,
            "operation_scope_key": self.operation_scope_key,
            "business_intent": to_plain(business),
            "preconditions_snapshot": to_plain(preconditions),
        })
        if fingerprint:
            if not isinstance(fingerprint, str) or not _SHA256.fullmatch(fingerprint) or fingerprint != computed:
                raise MutationGatewayError("invalid_fingerprint", "intent fingerprint must be lowercase SHA-256.")
        else:
            fingerprint = computed
        object.__setattr__(self, "fingerprint", fingerprint)

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_key": self.operation_key,
            "operation_scope_key": self.operation_scope_key,
            "business_intent": to_plain(self.business_intent),
            "preconditions_snapshot": to_plain(self.preconditions_snapshot),
            "idempotency_key": self.idempotency_key,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ReadbackPlanDescriptor:
    """A read-only verification plan; execution belongs to a later runtime."""

    operation_key: str
    strategy: str
    summary: str
    target: Mapping[str, Any]
    max_reads: int = 3
    outcomes: tuple[str, ...] = ("applied", "not_applied", "inconclusive")

    def __post_init__(self) -> None:
        try:
            require_key(self.operation_key, "readback operation_key")
        except (TypeError, ValueError) as exc:
            raise MutationGatewayError("invalid_readback", "Readback operation key is not allowlisted.") from exc
        require_text(self.strategy, "readback strategy", max_length=256)
        require_text(self.summary, "readback summary", max_length=2048)
        if not isinstance(self.target, Mapping):
            raise MutationGatewayError("invalid_readback", "readback target must be a JSON object.")
        target = freeze_json(dict(self.target), "readback target")
        object.__setattr__(self, "target", target)
        if isinstance(self.max_reads, bool) or not isinstance(self.max_reads, int) or not 1 <= self.max_reads <= 3:
            raise MutationGatewayError("invalid_readback", "readback max_reads must be between one and three.")
        if isinstance(self.outcomes, (str, bytes)) or not isinstance(self.outcomes, Sequence):
            raise MutationGatewayError("invalid_readback", "readback outcomes must be a sequence.")
        outcomes = tuple(self.outcomes)
        if not outcomes or len(set(outcomes)) != len(outcomes) or any(not isinstance(item, str) or not item for item in outcomes):
            raise MutationGatewayError("invalid_readback", "readback outcomes must be unique non-empty strings.")
        object.__setattr__(self, "outcomes", outcomes)

    @classmethod
    def from_metadata(cls, metadata: ReadbackMetadata, target: Mapping[str, Any]) -> "ReadbackPlanDescriptor":
        if not isinstance(metadata, ReadbackMetadata) or not metadata.required:
            raise MutationGatewayError("invalid_readback", "mutation must have a required readback metadata entry.")
        return cls(metadata.operation_key or "", metadata.strategy, metadata.summary, target, outcomes=metadata.outcomes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_key": self.operation_key,
            "strategy": self.strategy,
            "summary": self.summary,
            "target": to_plain(self.target),
            "max_reads": self.max_reads,
            "outcomes": list(self.outcomes),
        }


@dataclass(frozen=True, slots=True)
class MutationRequest:
    """Immutable canonical request passed to one already-authorized delegate."""

    operation: ShopifyOperationSpec
    variables: Mapping[str, Any]
    intent: DurableIntentDescriptor
    readback: ReadbackPlanDescriptor

    def __post_init__(self) -> None:
        if not isinstance(self.operation, ShopifyOperationSpec) or self.operation.operation_type != "mutation":
            raise MutationGatewayError("invalid_operation", "Mutation request requires a registered mutation spec.")
        if not isinstance(self.intent, DurableIntentDescriptor):
            raise MutationGatewayError("invalid_intent", "Mutation request requires a durable intent descriptor.")
        if not isinstance(self.readback, ReadbackPlanDescriptor):
            raise MutationGatewayError("invalid_readback", "Mutation request requires a readback plan descriptor.")
        if not isinstance(self.variables, Mapping):
            raise MutationGatewayError("invalid_variables", "Mutation variables must be an object.")
        variables = freeze_json(dict(self.variables), "variables")
        if set(variables) != set(self.operation.variable_schema):
            raise MutationGatewayError("invalid_variables", "Mutation variables do not match the operation schema.")
        if self.intent.operation_key != self.operation.operation_key:
            raise MutationGatewayError("invalid_intent", "Intent operation does not match the request operation.")
        metadata = self.operation.readback
        if self.readback.operation_key != metadata.operation_key or self.readback.strategy != metadata.strategy:
            raise MutationGatewayError("invalid_readback", "Readback plan does not match the operation metadata.")
        object.__setattr__(self, "variables", variables)

    @property
    def operation_key(self) -> str:
        return self.operation.operation_key

    @property
    def operation_name(self) -> str:
        return self.operation.operation_name

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_key": self.operation_key,
            "operation_name": self.operation_name,
            "variables": to_plain(self.variables),
            "intent": self.intent.as_dict(),
            "readback": self.readback.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class MutationUserError:
    """Safe user-error evidence; remote message text never crosses the seam."""

    code: str | None = None
    fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.code is not None and (not isinstance(self.code, str) or not _ERROR_CODE.fullmatch(self.code)):
            raise MutationGatewayError("invalid_user_error", "userErrors.code is malformed.")
        if isinstance(self.fields, (str, bytes)) or not isinstance(self.fields, Sequence):
            raise MutationGatewayError("invalid_user_error", "userErrors.field is malformed.")
        fields = tuple(self.fields)
        if len(fields) > MAX_ERROR_FIELDS or any(not isinstance(item, str) or not item or len(item) > MAX_ERROR_FIELD_TEXT for item in fields):
            raise MutationGatewayError("invalid_user_error", "userErrors.field is malformed.")
        object.__setattr__(self, "fields", fields)

    @classmethod
    def from_raw(cls, value: Any) -> "MutationUserError":
        if not isinstance(value, Mapping):
            raise MutationShapeError("invalid_user_errors", "Mutation userErrors entries must be objects.")
        # V1's schema has a required message even though it is deliberately
        # not persisted. Requiring it prevents a malformed falsey entry from
        # being mistaken for a clean rejection.
        message = value.get("message")
        if not isinstance(message, str) or not message.strip() or len(message) > MAX_MUTATION_TEXT:
            raise MutationShapeError("invalid_user_errors", "Mutation userErrors entries must contain a bounded message.")
        fields = value.get("field", value.get("fields", ()))
        if fields is None:
            fields = ()
        if isinstance(fields, str):
            fields = (fields,)
        if not isinstance(fields, Sequence) or isinstance(fields, (bytes, Mapping)):
            raise MutationShapeError("invalid_user_errors", "Mutation userErrors.field must be a string sequence.")
        code = value.get("code")
        return cls(code=code, fields=tuple(fields))

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "fields": list(self.fields)}


@dataclass(frozen=True, slots=True)
class MutationResult:
    """Immutable normalized outcome with bounded, redacted evidence."""

    operation_key: str
    operation_name: str
    outcome: MutationOutcome | str
    error_code: str | None
    safe_message: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    user_errors: tuple[MutationUserError, ...] = ()
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            require_key(self.operation_key, "result operation_key")
        except (TypeError, ValueError) as exc:
            raise MutationGatewayError("invalid_operation", "Result operation key is not allowlisted.") from exc
        require_text(self.operation_name, "result operation_name", max_length=256)
        try:
            outcome = self.outcome if isinstance(self.outcome, MutationOutcome) else MutationOutcome(self.outcome)
        except (TypeError, ValueError) as exc:
            raise MutationGatewayError("invalid_outcome", "Mutation outcome is not supported.") from exc
        object.__setattr__(self, "outcome", outcome.value)
        if self.error_code is not None and (not isinstance(self.error_code, str) or not self.error_code.strip() or len(self.error_code) > 128):
            raise MutationGatewayError("invalid_error", "Mutation error code is malformed.")
        require_text(self.safe_message, "safe_message", max_length=2048)
        if not isinstance(self.payload, Mapping) or not isinstance(self.evidence, Mapping):
            raise MutationGatewayError("invalid_result", "Mutation payload and evidence must be objects.")
        object.__setattr__(self, "payload", freeze_json(dict(self.payload), "payload"))
        object.__setattr__(self, "evidence", freeze_json(dict(self.evidence), "evidence"))
        errors = tuple(self.user_errors)
        if len(errors) > MAX_USER_ERRORS or any(not isinstance(item, MutationUserError) for item in errors):
            raise MutationGatewayError("invalid_user_errors", "Mutation userErrors are malformed.")
        object.__setattr__(self, "user_errors", errors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_key": self.operation_key,
            "operation_name": self.operation_name,
            "outcome": self.outcome,
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "payload": to_plain(self.payload),
            "user_errors": [item.as_dict() for item in self.user_errors],
            "evidence": to_plain(self.evidence),
        }


class MutationDelegate(Protocol):
    """Already-authorized one-request boundary supplied by the runtime."""

    def execute(self, operation: ShopifyOperationSpec, variables: Mapping[str, Any]) -> Mapping[str, Any] | Any:
        ...


def _response_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    as_dict = getattr(value, "as_dict", None)
    if callable(as_dict):
        candidate = as_dict()
        if isinstance(candidate, Mapping):
            return candidate
    raise MutationShapeError("invalid_response", "Mutation delegate returned no response object.")


def response_data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the data object after validating top-level GraphQL errors.

    A non-empty top-level error list is never classified as a clean rejection:
    GraphQL does not prove whether a remote mutation resolver ran before the
    error was returned, so domain gateways route it to verification.
    """

    errors = response.get("errors", [])
    if errors is None:
        errors = []
    if not isinstance(errors, list):
        raise MutationShapeError("invalid_top_level_errors", "Top-level GraphQL errors must be a list.")
    if errors:
        if len(errors) > MAX_USER_ERRORS:
            raise MutationShapeError("invalid_top_level_errors", "Top-level GraphQL errors exceeded their bound.")
        # Only retain bounded count/code evidence.  Messages and paths may
        # carry merchant data and never cross the mutation result boundary.
        for error in errors:
            if not isinstance(error, Mapping):
                raise MutationShapeError("invalid_top_level_errors", "Top-level GraphQL errors must be objects.")
            code = error.get("code")
            if code is None and isinstance(error.get("extensions"), Mapping):
                code = error["extensions"].get("code")
            if code is not None:
                if not isinstance(code, str) or not code.strip() or len(code) > 128:
                    raise MutationShapeError("invalid_top_level_errors", "Top-level GraphQL error code is malformed.")
        raise MutationShapeError("top_level_graphql_error", "Shopify returned a top-level GraphQL error.")
    data = response.get("data")
    if not isinstance(data, Mapping):
        raise MutationShapeError("missing_data", "Shopify mutation response omitted its data object.")
    return data


def parse_user_errors(value: Any) -> tuple[MutationUserError, ...]:
    """Normalize one mutation ``userErrors`` list without retaining messages."""

    if not isinstance(value, list):
        raise MutationShapeError("invalid_user_errors", "Mutation userErrors must be a list.")
    if len(value) > MAX_USER_ERRORS:
        raise MutationShapeError("invalid_user_errors", "Mutation userErrors exceeded its bound.")
    return tuple(MutationUserError.from_raw(item) for item in value)


class MutationGateway:
    """One-call adapter base shared by all P08 domain mutation gateways."""

    def __init__(self, delegate: MutationDelegate | Callable[[ShopifyOperationSpec, Mapping[str, Any]], Any], registry: ShopifyOperationRegistry) -> None:
        if not callable(delegate) and not callable(getattr(delegate, "execute", None)):
            raise TypeError("delegate must provide execute(operation, variables)")
        if not isinstance(registry, ShopifyOperationRegistry):
            raise TypeError("registry must be ShopifyOperationRegistry")
        self._delegate = delegate
        self.registry = registry

    def execute(self, request: MutationRequest) -> MutationResult:
        if not isinstance(request, MutationRequest):
            raise TypeError("request must be MutationRequest")
        registered = self.registry.get(request.operation_key)
        # The registry is the authority for the complete operation contract,
        # not only its GraphQL text.  Comparing the frozen spec prevents a
        # caller from smuggling a same-name operation with altered variables,
        # side-effect metadata, readback, API version or result declaration.
        if registered is None or registered != request.operation:
            raise MutationGatewayError("operation_not_registered", "Mutation operation is not registered by this gateway.")
        variables = to_plain(request.variables)
        try:
            if callable(getattr(self._delegate, "execute", None)):
                response = self._delegate.execute(request.operation, variables)
            else:
                response = self._delegate(request.operation, variables)  # type: ignore[misc]
        except MutationTransportError as exc:
            outcome = MutationOutcome.FAILED_CLEAN if exc.after_send is False else MutationOutcome.UNCERTAIN
            return self._result(
                request,
                outcome,
                exc.code if outcome is MutationOutcome.UNCERTAIN else "transport_not_sent",
                "Shopify did not complete the mutation request.",
                evidence={"transport": "not_sent" if exc.after_send is False else "uncertain"},
            )
        except TimeoutError:
            return self._result(request, MutationOutcome.UNCERTAIN, "shopify_temporary_server_network", "The mutation response timed out; verification is required.", evidence={"transport": "timeout"})
        except Exception:
            return self._result(request, MutationOutcome.UNCERTAIN, "shopify_temporary_server_network", "The mutation response could not be classified; verification is required.", evidence={"transport": "exception"})
        try:
            return self._normalize_response(request, _response_mapping(response))
        except (MutationShapeError, MutationGatewayError) as exc:
            return self._result(request, MutationOutcome.UNCERTAIN, exc.code, "Shopify returned an incomplete mutation result; verification is required.", evidence={"response_shape": exc.code})
        except Exception:
            # A delegate response adapter is outside this seam.  If it fails
            # while materializing a response, no mutation certainty can be
            # inferred and the exception text must not escape into evidence.
            return self._result(request, MutationOutcome.UNCERTAIN, "invalid_response", "Shopify returned an unclassifiable mutation result; verification is required.", evidence={"response_shape": "invalid_response"})

    def execute_once(self, request: MutationRequest) -> MutationResult:
        """Descriptive alias emphasizing that no retry or second call occurs."""

        return self.execute(request)

    def _result(self, request: MutationRequest, outcome: MutationOutcome | str, error_code: str | None, message: str, *, payload: Mapping[str, Any] | None = None, user_errors: Sequence[MutationUserError] = (), evidence: Mapping[str, Any] | None = None) -> MutationResult:
        return MutationResult(request.operation_key, request.operation_name, outcome, error_code, message, payload or {}, tuple(user_errors), evidence or {})

    def _normalize_response(self, request: MutationRequest, response: Mapping[str, Any]) -> MutationResult:
        raise NotImplementedError


__all__ = [
    "DurableIntentDescriptor",
    "MAX_MUTATION_COLLECTION_ITEMS",
    "MAX_MUTATION_JSON_BYTES",
    "MAX_MUTATION_JSON_DEPTH",
    "MAX_MUTATION_TEXT",
    "MutationDelegate",
    "MutationGateway",
    "MutationGatewayError",
    "MutationOutcome",
    "MutationRequest",
    "MutationResult",
    "MutationShapeError",
    "MutationTransportError",
    "MutationUserError",
    "ReadbackPlanDescriptor",
    "freeze_json",
    "parse_user_errors",
    "require_gid",
    "require_integer",
    "require_text",
    "response_data",
]
