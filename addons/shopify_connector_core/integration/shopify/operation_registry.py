"""Typed, checked-in Shopify operation specifications.

Only metadata is defined here.  The transport, GraphQL executor and domain
gateways are later work; this package performs no HTTP or Shopify operation.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ...domain.identifiers import require_key
from ...domain.immutability import freeze_value
from ...domain.registry import DuplicateRegistryKey, Registry, RegistryFrozen
from ...domain.states import OperationType


_OPERATION_NAME = re.compile(r"^[_A-Za-z][_A-Za-z0-9]*$")
_API_VERSION = re.compile(r"^[0-9]{4}-[0-9]{2}$")


def _tokenize(document: str) -> list[tuple[str, str]]:
    """Tokenize only the GraphQL surface needed for operation metadata.

    This is deliberately not a GraphQL validator.  Shopify's schema validator
    remains the authority for fields and types.  The bounded lexer only needs
    to identify top-level operation definitions and variable declarations so
    the checked-in contract cannot silently claim a different operation.
    """

    tokens: list[tuple[str, str]] = []
    index = 0
    length = len(document)
    if document.startswith("\ufeff"):
        index = 1
    punctuation = set("!$&():=@[]{|}")
    while index < length:
        char = document[index]
        if char in " \t\r\n,":
            index += 1
            continue
        if char == "#":
            newline = document.find("\n", index)
            index = length if newline == -1 else newline + 1
            continue
        if document.startswith("...", index):
            tokens.append(("punct", "..."))
            index += 3
            continue
        if char in punctuation:
            tokens.append(("punct", char))
            index += 1
            continue
        if document.startswith('"""', index):
            end = document.find('"""', index + 3)
            if end == -1:
                raise ValueError("operation document contains an unterminated block string")
            tokens.append(("value", document[index : end + 3]))
            index = end + 3
            continue
        if char == '"':
            cursor = index + 1
            escaped = False
            while cursor < length:
                current = document[cursor]
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    break
                elif current in "\r\n":
                    raise ValueError("operation document contains an invalid string")
                cursor += 1
            if cursor >= length or document[cursor] != '"':
                raise ValueError("operation document contains an unterminated string")
            tokens.append(("value", document[index : cursor + 1]))
            index = cursor + 1
            continue
        if char == "_" or ("A" <= char <= "Z") or ("a" <= char <= "z"):
            cursor = index + 1
            while cursor < length and (
                document[cursor] == "_"
                or ("A" <= document[cursor] <= "Z")
                or ("a" <= document[cursor] <= "z")
                or ("0" <= document[cursor] <= "9")
            ):
                cursor += 1
            tokens.append(("name", document[index:cursor]))
            index = cursor
            continue
        if char.isdigit() or char == "-":
            cursor = index + 1
            while cursor < length and (document[cursor].isalnum() or document[cursor] in ".+-"):
                cursor += 1
            tokens.append(("value", document[index:cursor]))
            index = cursor
            continue
        raise ValueError("operation document contains unsupported GraphQL character")
    return tokens


def _skip_balanced(
    tokens: list[tuple[str, str]],
    index: int,
    opening: str,
    closing: str,
) -> int:
    """Return the first token after one balanced GraphQL group."""

    if index >= len(tokens) or tokens[index] != ("punct", opening):
        raise ValueError("operation document has an invalid GraphQL group")
    depth = 0
    while index < len(tokens):
        kind, value = tokens[index]
        if kind == "punct" and value == opening:
            depth += 1
        elif kind == "punct" and value == closing:
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise ValueError("operation document has an unterminated GraphQL group")


def _operation_metadata(document: str) -> tuple[str, str, tuple[str, ...]]:
    """Return the one named operation's type, name and declared variables."""

    tokens = _tokenize(document)
    operations: list[tuple[str, str | None, tuple[str, ...]]] = []
    index = 0
    while index < len(tokens):
        kind, value = tokens[index]
        if kind == "punct" and value == "{":
            operations.append(("query", None, ()))
            index = _skip_balanced(tokens, index, "{", "}")
            continue
        if kind != "name":
            raise ValueError("operation document must contain a top-level operation")
        if value in {"query", "mutation"}:
            operation_type = value
            index += 1
            if index >= len(tokens) or tokens[index][0] != "name":
                raise ValueError("operation document must use a named operation")
            operation_name = tokens[index][1]
            variables: set[str] = set()
            index += 1
            body_index: int | None = None
            paren_depth = 0
            bracket_depth = 0
            while index < len(tokens):
                token_kind, token_value = tokens[index]
                if token_kind == "punct":
                    if token_value == "(":
                        paren_depth += 1
                    elif token_value == ")":
                        if paren_depth == 0:
                            raise ValueError("operation document has an unmatched ')'")
                        paren_depth -= 1
                    elif token_value == "[":
                        bracket_depth += 1
                    elif token_value == "]":
                        if bracket_depth == 0:
                            raise ValueError("operation document has an unmatched ']'")
                        bracket_depth -= 1
                    elif token_value == "{" and paren_depth == 0 and bracket_depth == 0:
                        body_index = index
                        break
                    elif token_value == "$" and paren_depth > 0:
                        if index + 1 >= len(tokens) or tokens[index + 1][0] != "name":
                            raise ValueError("operation document has an invalid variable name")
                        variables.add(tokens[index + 1][1])
                index += 1
            if body_index is None or paren_depth or bracket_depth:
                raise ValueError("operation document must have a balanced selection set")
            index = _skip_balanced(tokens, body_index, "{", "}")
            operations.append((operation_type, operation_name, tuple(sorted(variables))))
            continue
        if value == "fragment":
            # Fragments are definitions, not operations.  Skip the fragment
            # header with the same delimiter rules, then its selection set.
            index += 1
            paren_depth = 0
            bracket_depth = 0
            body_index = None
            while index < len(tokens):
                token_kind, token_value = tokens[index]
                if token_kind == "punct":
                    if token_value == "(":
                        paren_depth += 1
                    elif token_value == ")":
                        if paren_depth == 0:
                            raise ValueError("fragment has an unmatched ')'")
                        paren_depth -= 1
                    elif token_value == "[":
                        bracket_depth += 1
                    elif token_value == "]":
                        if bracket_depth == 0:
                            raise ValueError("fragment has an unmatched ']'")
                        bracket_depth -= 1
                    elif token_value == "{" and paren_depth == 0 and bracket_depth == 0:
                        body_index = index
                        break
                index += 1
            if body_index is None:
                raise ValueError("fragment must have a selection set")
            index = _skip_balanced(tokens, body_index, "{", "}")
            continue
        raise ValueError("operation document contains an unsupported top-level definition")
    if len(operations) != 1:
        raise ValueError("operation document must contain exactly one operation")
    operation_type, operation_name, variables = operations[0]
    if operation_name is None:
        raise ValueError("operation document must use a named operation")
    return operation_type, operation_name, variables


def _mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise TypeError(f"{field_name} keys must be non-empty strings")
    return freeze_value(dict(value))


@dataclass(frozen=True, slots=True)
class OperationIdentity:
    operation_key: str
    operation_name: str
    api_version: str

    def __post_init__(self) -> None:
        require_key(self.operation_key, "operation_key")
        if not isinstance(self.operation_name, str) or not _OPERATION_NAME.fullmatch(self.operation_name):
            raise ValueError("operation_name must be a stable GraphQL name")
        if not isinstance(self.api_version, str) or not _API_VERSION.fullmatch(self.api_version):
            raise ValueError("api_version must use YYYY-MM")


@dataclass(frozen=True, slots=True)
class SideEffectMetadata:
    """Human/audit metadata describing a remote effect, if any."""

    kind: str
    summary: str
    remote: bool

    def __post_init__(self) -> None:
        allowed = {"none", "observe", "create", "update", "delete", "notify", "reconcile"}
        if not isinstance(self.kind, str):
            raise TypeError("side-effect kind must be a string")
        if self.kind not in allowed:
            raise ValueError(f"unsupported side-effect kind: {self.kind!r}")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("side-effect summary must be non-empty")
        if not isinstance(self.remote, bool):
            raise TypeError("remote must be bool")
        if self.kind in {"none", "observe"} and self.remote:
            raise ValueError("none/observe side effects cannot be remote")
        if self.kind not in {"none", "observe"} and not self.remote:
            raise ValueError("remote side effects must be marked remote")


@dataclass(frozen=True, slots=True)
class ReadbackMetadata:
    """The explicit readback plan required for an uncertain mutation."""

    required: bool = False
    operation_key: str | None = None
    strategy: str = ""
    summary: str = ""
    outcomes: tuple[str, ...] = ("applied", "not_applied", "inconclusive")

    def __post_init__(self) -> None:
        if not isinstance(self.required, bool):
            raise TypeError("readback.required must be bool")
        if not isinstance(self.strategy, str) or not isinstance(self.summary, str):
            raise TypeError("readback strategy and summary must be strings")
        if self.operation_key is not None:
            require_key(self.operation_key, "readback operation_key")
        if isinstance(self.outcomes, (str, bytes, Mapping)):
            raise TypeError("readback outcomes must be a sequence of strings")
        outcomes = tuple(self.outcomes)
        if any(not isinstance(value, str) or not value.strip() for value in outcomes):
            raise ValueError("readback outcomes must be non-empty strings")
        if len(set(outcomes)) != len(outcomes):
            raise ValueError("readback outcomes must be unique")
        if self.required and not self.strategy.strip():
            raise ValueError("a required readback needs an explicit strategy")
        if self.required and self.operation_key is None:
            raise ValueError("a required readback needs an operation_key")
        if not self.required and (self.operation_key is not None or self.strategy.strip() or self.summary.strip()):
            raise ValueError("optional readback metadata must be empty")
        if self.required and not self.summary.strip():
            raise ValueError("a required readback needs a summary")
        object.__setattr__(self, "outcomes", outcomes)


@dataclass(frozen=True, slots=True)
class ShopifyOperationSpec:
    """All reviewed metadata for one named Shopify GraphQL operation."""

    operation_key: str
    operation_name: str
    operation_type: str | OperationType
    api_version: str
    document: str
    variables: Mapping[str, Any]
    result: Any
    error: Any
    side_effect: SideEffectMetadata
    readback: ReadbackMetadata = field(default_factory=ReadbackMetadata)
    cost_expectation: Mapping[str, Any] = field(default_factory=dict)
    pagination: Mapping[str, Any] = field(default_factory=dict)
    fixture_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        identity = OperationIdentity(self.operation_key, self.operation_name, self.api_version)
        operation_type = (
            self.operation_type.value
            if isinstance(self.operation_type, OperationType)
            else self.operation_type
        )
        if not isinstance(operation_type, str):
            raise TypeError("operation_type must be a string or OperationType")
        if operation_type not in {item.value for item in OperationType}:
            raise ValueError(f"unsupported operation type: {operation_type!r}")
        if not isinstance(self.document, str) or not self.document.strip():
            raise ValueError("operation document must be non-empty")
        try:
            document_type, document_name, declared_variables = _operation_metadata(self.document)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if document_type != operation_type or document_name != identity.operation_name:
            raise ValueError("operation metadata does not match its GraphQL document")
        variables = _mapping(self.variables, "variables")
        if any(not _OPERATION_NAME.fullmatch(key) for key in variables):
            raise ValueError("variable schema keys must be GraphQL names")
        if set(variables) != set(declared_variables):
            raise ValueError("variable metadata must exactly match document declarations")
        if self.result is None or self.error is None:
            raise ValueError("result and error metadata are required")
        if not isinstance(self.side_effect, SideEffectMetadata):
            raise TypeError("side_effect must be SideEffectMetadata")
        if not isinstance(self.readback, ReadbackMetadata):
            raise TypeError("readback must be ReadbackMetadata")
        if operation_type == OperationType.MUTATION.value:
            if not self.side_effect.remote:
                raise ValueError("mutations must declare a remote side effect")
            if not self.readback.required:
                raise ValueError("mutations must declare a readback strategy")
        else:
            if self.side_effect.remote:
                raise ValueError("queries cannot declare a remote side effect")
        object.__setattr__(self, "operation_type", operation_type)
        object.__setattr__(self, "variables", _mapping(variables, "variables"))
        object.__setattr__(self, "cost_expectation", _mapping(self.cost_expectation, "cost_expectation"))
        object.__setattr__(self, "pagination", _mapping(self.pagination, "pagination"))
        if isinstance(self.fixture_keys, (str, bytes)):
            raise TypeError("fixture_keys must be a sequence of keys")
        fixture_keys = tuple(self.fixture_keys)
        if any(not isinstance(key, str) or not key.strip() for key in fixture_keys):
            raise ValueError("fixture_keys must contain non-empty strings")
        if len(set(fixture_keys)) != len(fixture_keys):
            raise ValueError("fixture_keys must be unique")
        object.__setattr__(self, "fixture_keys", fixture_keys)

    @property
    def identity(self) -> OperationIdentity:
        return OperationIdentity(self.operation_key, self.operation_name, self.api_version)

    @property
    def variable_schema(self) -> Mapping[str, Any]:
        return self.variables

    @property
    def result_type(self) -> Any:
        return self.result

    @property
    def error_type(self) -> Any:
        return self.error


class ShopifyOperationRegistry(Registry[ShopifyOperationSpec]):
    """Explicit operation registry with no discovery or fallback behavior."""

    def __init__(self, specs: Iterable[ShopifyOperationSpec] = ()) -> None:
        super().__init__()
        self.register_many(specs)

    def register(self, spec: ShopifyOperationSpec) -> ShopifyOperationSpec:  # type: ignore[override]
        self.register_many((spec,))
        return spec

    def register_many(self, specs: Iterable[ShopifyOperationSpec]) -> None:  # type: ignore[override]
        batch = tuple(specs)
        if self.frozen:
            raise RegistryFrozen("registry is frozen")
        for spec in batch:
            if not isinstance(spec, ShopifyOperationSpec):
                raise TypeError("operation registry accepts ShopifyOperationSpec only")
        known_keys = set(self.keys())
        known_names = {item.operation_name for item in self.values()}
        batch_keys: set[str] = set()
        batch_names: set[str] = set()
        batch_by_key: dict[str, ShopifyOperationSpec] = {}
        for spec in batch:
            if spec.operation_key in known_keys or spec.operation_key in batch_keys:
                raise DuplicateRegistryKey(
                    f"operation key already registered: {spec.operation_key}"
                )
            if spec.operation_name in known_names or spec.operation_name in batch_names:
                raise DuplicateRegistryKey(
                    f"GraphQL operation name already registered: {spec.operation_name}"
                )
            batch_keys.add(spec.operation_key)
            batch_names.add(spec.operation_name)
            batch_by_key[spec.operation_key] = spec
        for spec in batch:
            if not spec.readback.required:
                continue
            target = self.get(spec.readback.operation_key)
            if target is None:
                target = batch_by_key.get(spec.readback.operation_key)
            if target is None:
                raise ValueError(
                    f"readback operation is not registered: {spec.readback.operation_key}"
                )
            if target.operation_type != OperationType.QUERY.value:
                raise ValueError("readback operation must reference a query")
            if target.operation_key == spec.operation_key:
                raise ValueError("a mutation cannot read back through itself")
        for spec in batch:
            super().register(spec.operation_key, spec)

    def require_operation(self, operation_key: str) -> ShopifyOperationSpec:
        return self.require(operation_key)


__all__ = [
    "OperationIdentity",
    "ReadbackMetadata",
    "ShopifyOperationRegistry",
    "ShopifyOperationSpec",
    "SideEffectMetadata",
]
