"""Pure reconciliation evaluation for every P08 product/media operation."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._support import (
    BINDING_DEFINITION_READ_OPERATION,
    BINDING_NAMESPACE_OPERATION,
    MEDIA_ASSOCIATE_OPERATION,
    MEDIA_FILE_CREATE_OPERATION,
    MEDIA_STAGE_OPERATION,
    PRODUCT_CREATE_OPERATION,
    PRODUCT_UPDATE_OPERATION,
    VARIANTS_CREATE_OPERATION,
    VARIANTS_UPDATE_OPERATION,
    ProductExportPolicyError,
    canonical_fingerprint,
    fail,
    first,
    freeze_mapping,
    gid,
    money_equal,
    non_negative_int,
    sequence,
    text,
)


class ReadbackVerdict(str, Enum):
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    INCONCLUSIVE = "inconclusive"


_SERVER_READ_ATTESTATION = object()
_SERVER_READ_PROOF_KEY = secrets.token_bytes(32)


@dataclass(frozen=True)
class ReadbackResult:
    operation: str
    verdict: ReadbackVerdict
    reason_code: str
    expected_count: int = 0
    observed_count: int = 0
    matched: tuple[str, ...] = ()
    user_errors: tuple[Mapping[str, Any], ...] = ()
    store_identity: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "verdict", ReadbackVerdict(self.verdict))
        object.__setattr__(self, "operation", text(self.operation, "operation", max_length=256))
        object.__setattr__(self, "expected_count", non_negative_int(self.expected_count, "expected_count"))
        object.__setattr__(self, "observed_count", non_negative_int(self.observed_count, "observed_count"))
        if any(not isinstance(value, str) or not value for value in self.matched):
            fail("invalid_readback", "matched identities must be non-empty strings.")
        object.__setattr__(self, "matched", tuple(self.matched))
        object.__setattr__(self, "user_errors", tuple(freeze_mapping(dict(error)) for error in self.user_errors))
        if self.store_identity is not None:
            object.__setattr__(self, "store_identity", text(self.store_identity, "store_identity", max_length=512))

    @property
    def applied(self) -> bool:
        return self.verdict is ReadbackVerdict.APPLIED

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "verdict": self.verdict.value,
            "reason_code": self.reason_code,
            "expected_count": self.expected_count,
            "observed_count": self.observed_count,
            "matched": list(self.matched),
            "user_errors": [dict(error) for error in self.user_errors],
            "store_identity": self.store_identity,
        }


class BindingNamespaceReadEvidence:
    """Constructor-closed proof of one exact Shopify definition observation."""

    __slots__ = (
        "_operation", "_reason_code", "_store_identity", "_connection_generation",
        "_definition_gid", "_source", "_observation_fingerprint", "_proof_digest",
        "_seal",
    )

    def __init_subclass__(cls, **_kwargs: Any) -> None:
        fail("invalid_binding_evidence", "Binding evidence is sealed and cannot be subclassed.")

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "BindingNamespaceReadEvidence":
        fail("invalid_binding_evidence", "Binding evidence can only be produced by the Shopify read attestor.")

    def __setattr__(self, _name: str, _value: Any) -> None:
        fail("immutable_binding_evidence", "Binding evidence is immutable.")

    @property
    def operation(self) -> str:
        return self._operation

    @property
    def reason_code(self) -> str:
        return self._reason_code

    @property
    def store_identity(self) -> str:
        return self._store_identity

    @property
    def connection_generation(self) -> int:
        return self._connection_generation

    @property
    def definition_gid(self) -> str:
        return self._definition_gid

    @property
    def source(self) -> str:
        return self._source

    @property
    def observation_fingerprint(self) -> str:
        return self._observation_fingerprint

    def _proof_payload(self) -> dict[str, Any]:
        return {
            "operation": self._operation,
            "reason_code": self._reason_code,
            "store_identity": self._store_identity,
            "connection_generation": self._connection_generation,
            "definition_gid": self._definition_gid,
            "source": self._source,
            "observation_fingerprint": self._observation_fingerprint,
        }

    def _validate(self) -> None:
        if type(self) is not BindingNamespaceReadEvidence:
            fail("invalid_binding_evidence", "Binding evidence must be the exact sealed attestation type.")
        if self._seal is not _SERVER_READ_ATTESTATION:
            fail("invalid_binding_evidence", "Binding evidence is not an attested Shopify read proof.")
        payload_fingerprint = canonical_fingerprint(self._proof_payload())
        expected_digest = hashlib.sha256(_SERVER_READ_PROOF_KEY + payload_fingerprint.encode("ascii")).hexdigest()
        if self._proof_digest != expected_digest:
            fail("invalid_binding_evidence", "Binding evidence was copied or mutated after attestation.")

    def __copy__(self) -> "BindingNamespaceReadEvidence":
        fail("invalid_binding_evidence", "Binding evidence cannot be copied; retain the attested instance.")

    def __deepcopy__(self, _memo: Mapping[int, Any]) -> "BindingNamespaceReadEvidence":
        fail("invalid_binding_evidence", "Binding evidence cannot be copied; retain the attested instance.")

    def __reduce_ex__(self, _protocol: int) -> Any:
        fail("invalid_binding_evidence", "Binding evidence cannot be serialized as a trusted proof.")

    def __repr__(self) -> str:
        return f"BindingNamespaceReadEvidence(store_identity={self._store_identity!r}, connection_generation={self._connection_generation!r})"

    @classmethod
    def from_value(cls, value: Any) -> "BindingNamespaceReadEvidence | None":
        if value is None:
            return None
        if type(value) is BindingNamespaceReadEvidence:
            BindingNamespaceReadEvidence._validate(value)
            return value
        fail("invalid_binding_evidence", "binding_namespace_evidence must be typed server-attested evidence.")

    def as_dict(self) -> dict[str, Any]:
        BindingNamespaceReadEvidence._validate(self)
        return self._proof_payload()


def attest_binding_namespace_read(
    observed: Any,
    *,
    expected_store_identity: str,
    connection_generation: int,
) -> BindingNamespaceReadEvidence:
    """Evaluate raw Shopify read evidence and promote only an exact closed page."""

    if isinstance(connection_generation, bool) or not isinstance(connection_generation, int) or connection_generation < 0:
        fail("invalid_generation", "binding evidence generation must be a non-negative integer.")
    result = evaluate_remote_readback(
        BINDING_NAMESPACE_OPERATION,
        {
            "definition_key": "odoo_template_custom_id_v2",
            "type": "id",
            "owner": "PRODUCT",
        },
        observed,
        expected_store_identity=expected_store_identity,
    )
    if result.verdict is not ReadbackVerdict.APPLIED:
        fail("invalid_binding_evidence", "Binding readiness requires an applied exact definition readback.")
    if result.reason_code != "binding_definition_present" or result.store_identity is None or len(result.matched) != 1:
        fail("invalid_binding_evidence", "Binding readiness requires exact definition and store identity evidence.")
    evidence = object.__new__(BindingNamespaceReadEvidence)
    values = {
        "_operation": BINDING_DEFINITION_READ_OPERATION,
        "_reason_code": result.reason_code,
        "_store_identity": result.store_identity,
        "_connection_generation": connection_generation,
        "_definition_gid": gid(result.matched[0], "binding_evidence.definition_gid", kind="MetafieldDefinition"),
        "_source": "shopify_server_read",
        "_observation_fingerprint": canonical_fingerprint(observed),
        "_seal": _SERVER_READ_ATTESTATION,
    }
    for name, value in values.items():
        object.__setattr__(evidence, name, value)
    payload_fingerprint = canonical_fingerprint(evidence._proof_payload())
    object.__setattr__(
        evidence,
        "_proof_digest",
        hashlib.sha256(_SERVER_READ_PROOF_KEY + payload_fingerprint.encode("ascii")).hexdigest(),
    )
    BindingNamespaceReadEvidence._validate(evidence)
    return evidence


def _op(value: str) -> str:
    aliases = {
        "create": PRODUCT_CREATE_OPERATION,
        "product_create": PRODUCT_CREATE_OPERATION,
        "update": PRODUCT_UPDATE_OPERATION,
        "product_update": PRODUCT_UPDATE_OPERATION,
        "variant_update": VARIANTS_UPDATE_OPERATION,
        "variants_update": VARIANTS_UPDATE_OPERATION,
        "variant_create": VARIANTS_CREATE_OPERATION,
        "variants_create": VARIANTS_CREATE_OPERATION,
        "media_stage": MEDIA_STAGE_OPERATION,
        "media_file_create": MEDIA_FILE_CREATE_OPERATION,
        "media_associate": MEDIA_ASSOCIATE_OPERATION,
        "binding_namespace": BINDING_NAMESPACE_OPERATION,
    }
    if value in aliases:
        return aliases[value]
    return value


def _rows(value: Any, *names: str) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if isinstance(value.get("data"), Mapping):
            return _rows(value["data"], *names)
        for name in names:
            nested = value.get(name)
            if isinstance(nested, Mapping):
                for child in ("nodes", "items", "edges"):
                    if child in nested:
                        nested = nested[child]
                        break
            if isinstance(nested, Sequence) and not isinstance(nested, (str, bytes)):
                return [row for row in nested if isinstance(row, Mapping)]
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [row for row in value if isinstance(row, Mapping)]
    return []


def _product(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        nested = value.get("product")
        if isinstance(nested, Mapping):
            return nested
        if "product" in value:
            return None
        nested = value.get("data")
        if isinstance(nested, Mapping):
            return _product(nested)
        return value
    return None


def _variant_rows(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping) and isinstance(value.get("data"), Mapping):
        return _variant_rows(value["data"])
    product = _product(value)
    if product is not None:
        nested = product.get("variants")
        if isinstance(nested, Mapping):
            for child in ("nodes", "items"):
                if child in nested:
                    nested = nested[child]
                    break
        if isinstance(nested, Sequence) and not isinstance(nested, (str, bytes)):
            return [row for row in nested if isinstance(row, Mapping)]
    return _rows(value, "variants", "productVariants", "product_variants", "nodes")


def _media_rows(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if isinstance(value.get("data"), Mapping):
            return _media_rows(value["data"])
        node = value.get("node")
        if isinstance(node, Mapping):
            return [node]
        if "node" in value:
            return []
        for key in ("files", "media", "nodes"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                for child in ("nodes", "items"):
                    if child in nested:
                        nested = nested[child]
                        break
            if isinstance(nested, Sequence) and not isinstance(nested, (str, bytes)):
                return [row for row in nested if isinstance(row, Mapping)]
        product = value.get("product")
        if isinstance(product, Mapping):
            return _media_rows(product)
        file_row = value.get("file")
        if isinstance(file_row, Mapping):
            return [file_row]
        return [value]
    return []


def _field(row: Mapping[str, Any], name: str) -> Any:
    if name in row:
        return row[name]
    aliases = {
        "descriptionHtml": ("description_html", "description"),
        "productType": ("product_type",),
        "compareAtPrice": ("compare_at_price",),
        "barcode": ("bar_code",),
        "inventoryItem": ("inventory_item",),
    }
    for alias in aliases.get(name, ()):
        if alias in row:
            return row[alias]
    if name == "inventoryItem":
        return row.get("inventory_item")
    return None


def _equal(name: str, expected: Any, observed: Any) -> bool:
    if name in {"price", "compareAtPrice"}:
        return money_equal(expected, observed)
    if name == "inventoryItem":
        if isinstance(expected, Mapping):
            expected = expected.get("sku")
        if isinstance(observed, Mapping):
            observed = observed.get("sku")
    return expected == observed


def _errors(value: Any) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, Mapping):
        raw = value.get("userErrors", value.get("errors", ()))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        # A direct user-error list is accepted only when its entries have the
        # required message marker.  A normal list of products/variants must
        # never be mistaken for errors.
        raw = value if all(isinstance(row, Mapping) and "message" in row for row in value) else ()
    else:
        raw = ()
    if isinstance(raw, Mapping):
        raw = [raw]
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    return tuple(dict(row) for row in raw if isinstance(row, Mapping))


def _identity(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("myshopifyDomain", "shop_identity", "store_identity", "domain"):
            raw = value.get(key)
            if raw is not None:
                return raw if isinstance(raw, str) and raw.strip() else None
        for key in ("shop", "data"):
            nested = value.get(key)
            found = _identity(nested)
            if found:
                return found
    return None


def _response_root(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    data = value.get("data")
    return data if isinstance(data, Mapping) else value


def _target_connection(operation: str, observed: Any, expected: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return only the collection whose cardinality the verdict depends on."""

    root = _response_root(observed)
    if root is None:
        return None
    if operation == BINDING_NAMESPACE_OPERATION:
        connection = root.get("metafieldDefinitions")
    elif operation in {VARIANTS_UPDATE_OPERATION, VARIANTS_CREATE_OPERATION}:
        product = root.get("product")
        owner = product if isinstance(product, Mapping) else root
        connection = first(owner, "variants", "productVariants", "product_variants", default=None)
    elif operation == MEDIA_FILE_CREATE_OPERATION:
        connection = None if first(expected, "file_gid", "id", default=None) is not None else root.get("files")
    elif operation == MEDIA_ASSOCIATE_OPERATION:
        product = root.get("product")
        connection = product.get("media") if isinstance(product, Mapping) else None
    else:
        connection = None
    return connection if isinstance(connection, Mapping) else None


def _target_pagination_complete(operation: str, observed: Any, expected: Mapping[str, Any]) -> bool | None:
    connection = _target_connection(operation, observed, expected)
    if connection is None:
        return None
    page_info = connection.get("pageInfo")
    if not isinstance(page_info, Mapping) or not isinstance(page_info.get("hasNextPage"), bool):
        return None
    return not page_info["hasNextPage"]


def _singleton_cardinality(operation: str, observed: Any, expected: Mapping[str, Any]) -> bool:
    """Recognize only schema-singleton reads; arbitrary lists prove nothing."""

    if not isinstance(observed, Mapping):
        return False
    data = observed.get("data")
    if isinstance(data, Mapping):
        observed = data
    if operation in {PRODUCT_CREATE_OPERATION, PRODUCT_UPDATE_OPERATION}:
        return "product" in observed
    if operation == MEDIA_FILE_CREATE_OPERATION and first(expected, "file_gid", "id", default=None) is not None:
        return "node" in observed or "file" in observed
    return False


def _observed_gid(value: Any, kind: str, name: str) -> str | None:
    try:
        return gid(value, name, kind=kind)
    except ProductExportPolicyError:
        return None


def _base(
    operation: str,
    verdict: ReadbackVerdict,
    reason: str,
    *,
    expected_count: int = 0,
    observed_count: int = 0,
    matched: Sequence[str] = (),
    user_errors: Sequence[Mapping[str, Any]] = (),
    store_identity: str | None = None,
) -> ReadbackResult:
    return ReadbackResult(operation, verdict, reason, expected_count, observed_count, tuple(matched), tuple(user_errors), store_identity)


def _scalar_result(operation: str, expected: Mapping[str, Any], observed: Any, errors: tuple[Mapping[str, Any], ...], identity: str | None, expected_identity: str | None) -> ReadbackResult:
    product = _product(observed)
    if product is None:
        return _base(operation, ReadbackVerdict.NOT_APPLIED, "product_missing", expected_count=1, observed_count=0, user_errors=errors, store_identity=identity)
    product_gid = first(expected, "product_gid", "id", default=None)
    expected_gid = _observed_gid(product_gid, "Product", "expected.product_gid") if product_gid is not None else None
    if product_gid is not None and expected_gid is None:
        fail("invalid_gid", "expected.product_gid must be a canonical Shopify Product GID.")
    observed_gid = _observed_gid(first(product, "id", "product_gid", default=None), "Product", "observed.product_gid")
    if observed_gid is None:
        return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
    if expected_gid is not None and observed_gid != expected_gid:
        return _base(operation, ReadbackVerdict.NOT_APPLIED, "product_identity_mismatch", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
    mismatches = [name for name, value in expected.items() if name not in {"product_gid", "id", "template_id"} and not _equal(name, value, _field(product, name))]
    if mismatches:
        return _base(operation, ReadbackVerdict.NOT_APPLIED, "scalar_mismatch", expected_count=1, observed_count=1, matched=(), user_errors=errors, store_identity=identity)
    if errors:
        return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
    return _base(operation, ReadbackVerdict.APPLIED, "exact_scalar_values", expected_count=1, observed_count=1, matched=tuple(expected), store_identity=identity)


def evaluate_remote_readback(
    operation: str,
    expected: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    observed: Any,
    *,
    expected_store_identity: str | None = None,
    observed_store_identity: str | None = None,
    complete: bool = False,
    read_error: Any = None,
    send_state: str | None = None,
) -> ReadbackResult:
    """Classify a readback without ever authoring or replaying a mutation."""

    operation = _op(text(operation, "operation", max_length=256))
    if not isinstance(complete, bool):
        fail("invalid_boolean", "complete must be a strict boolean.")
    if expected is None:
        expected_map: Mapping[str, Any] = {}
    elif isinstance(expected, Mapping):
        expected_map = expected
    elif isinstance(expected, Sequence) and not isinstance(expected, (str, bytes)):
        expected_map = {}
    else:
        fail("invalid_readback", "expected readback values must be an object or sequence of objects.")
    expected_product_gid: str | None = None
    if operation in {VARIANTS_UPDATE_OPERATION, VARIANTS_CREATE_OPERATION, MEDIA_ASSOCIATE_OPERATION}:
        raw_expected_product = expected_map.get("product_gid")
        expected_product_gid = _observed_gid(raw_expected_product, "Product", "expected.product_gid")
        if expected_product_gid is None:
            fail("missing_product_identity", f"{operation} readback requires a canonical expected product_gid.")
    errors = _errors(observed)
    identity = observed_store_identity or _identity(observed)
    if expected_store_identity is not None:
        if identity is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "store_identity_missing", user_errors=errors, store_identity=identity)
        if identity != expected_store_identity:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "store_identity_mismatch", user_errors=errors, store_identity=identity)
    if read_error is not None:
        if send_state == "before_send":
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "send_not_attempted", user_errors=errors, store_identity=identity)
        return _base(operation, ReadbackVerdict.INCONCLUSIVE, "readback_unavailable", user_errors=errors, store_identity=identity)
    pagination = _target_pagination_complete(operation, observed, expected_map)
    if pagination is False:
        return _base(operation, ReadbackVerdict.INCONCLUSIVE, "readback_has_next_page", user_errors=errors, store_identity=identity)
    readback_complete = complete or pagination is True or _singleton_cardinality(operation, observed, expected_map)
    if not readback_complete:
        return _base(operation, ReadbackVerdict.INCONCLUSIVE, "readback_incomplete", user_errors=errors, store_identity=identity)

    if operation == PRODUCT_CREATE_OPERATION:
        nested_product = _product(observed)
        if isinstance(observed, Mapping) and "product" in observed:
            rows = [nested_product] if isinstance(nested_product, Mapping) and "id" in nested_product else []
        else:
            rows = _rows(observed, "products", "nodes")
        if len(rows) > 1:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "duplicate_remote_identity", expected_count=1, observed_count=len(rows), user_errors=errors, store_identity=identity)
        if not rows:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "product_not_found", expected_count=1, user_errors=errors, store_identity=identity)
        row = rows[0]
        expected_template = expected_map.get("template_id")
        custom_value = first(row, "template_id", "custom_id", "binding_value", default=None)
        observed_gid = _observed_gid(first(row, "id", "product_gid", default=None), "Product", "observed.product_gid")
        if observed_gid is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        if expected_template is None:
            fail("missing_binding_identity", "product create readback requires the expected connector binding value.")
        if isinstance(expected_template, bool) or not isinstance(expected_template, (str, int)):
            fail("invalid_template_id", "expected template_id must be a string or strict integer.")
        if custom_value is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "binding_missing", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        if isinstance(custom_value, bool) or not isinstance(custom_value, (str, int)):
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_binding_identity", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        if str(custom_value) != str(expected_template):
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "binding_mismatch", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        if errors:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        return _base(operation, ReadbackVerdict.APPLIED, "adopted_exact_binding", expected_count=1, observed_count=1, matched=(observed_gid,), store_identity=identity)

    if operation == PRODUCT_UPDATE_OPERATION:
        return _scalar_result(operation, expected_map, observed, errors, identity, expected_store_identity)

    if operation in {VARIANTS_UPDATE_OPERATION, VARIANTS_CREATE_OPERATION}:
        observed_product = _product(observed)
        observed_product_gid = _observed_gid(
            first(observed_product, "id", "product_gid", default=None) if isinstance(observed_product, Mapping) else None,
            "Product",
            "observed.product_gid",
        )
        if observed_product_gid is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_product_identity", user_errors=errors, store_identity=identity)
        if observed_product_gid != expected_product_gid:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "product_identity_mismatch", user_errors=errors, store_identity=identity)
        expected_rows = list(expected) if isinstance(expected, Sequence) and not isinstance(expected, (str, bytes)) else list(expected_map.get("variants", ()))
        expected_rows = [row for row in expected_rows if isinstance(row, Mapping)]
        if not expected_rows:
            fail("invalid_readback", "variant readback requires a non-empty expected identity set.")
        observed_rows = _variant_rows(observed)
        if operation == VARIANTS_CREATE_OPERATION:
            def _sku(row: Mapping[str, Any]) -> str:
                inventory = row.get("inventoryItem") or row.get("inventory_item")
                value = first(row, "sku", default=first(inventory, "sku", default="") if isinstance(inventory, Mapping) else "")
                return value if isinstance(value, str) else ""
            expected_skus = [_sku(row) for row in expected_rows]
            observed_skus = [_sku(row) for row in observed_rows]
            observed_ids = [_observed_gid(first(row, "id", "variant_gid", default=None), "ProductVariant", "observed.variant_gid") for row in observed_rows]
            if any(value is None for value in observed_ids):
                return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=len(expected_skus), observed_count=len(observed_rows), user_errors=errors, store_identity=identity)
            if len(observed_ids) != len(set(observed_ids)):
                return _base(operation, ReadbackVerdict.NOT_APPLIED, "duplicate_remote_variant_identity", expected_count=len(expected_skus), observed_count=len(observed_rows), user_errors=errors, store_identity=identity)
            if any(not sku for sku in expected_skus) or len(expected_skus) != len(set(expected_skus)):
                fail("invalid_readback", "variant create readback requires unique expected SKUs.")
            if any(observed_skus.count(sku) != 1 for sku in expected_skus) or len(observed_skus) < len(expected_skus):
                return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_or_duplicate_variant_create", expected_count=len(expected_skus), observed_count=len(observed_rows), user_errors=errors, store_identity=identity)
            if errors:
                return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=len(expected_skus), observed_count=len(observed_rows), user_errors=errors, store_identity=identity)
            return _base(operation, ReadbackVerdict.APPLIED, "exact_variant_skus", expected_count=len(expected_skus), observed_count=len(observed_rows), matched=tuple(expected_skus), store_identity=identity)
        observed_ids = [_observed_gid(first(row, "id", "variant_gid", default=None), "ProductVariant", "observed.variant_gid") for row in observed_rows]
        if any(value is None for value in observed_ids):
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=len(expected_rows), observed_count=len(observed_rows), user_errors=errors, store_identity=identity)
        if len(observed_ids) != len(set(observed_ids)):
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "duplicate_remote_variant_identity", expected_count=len(expected_rows), observed_count=len(observed_rows), user_errors=errors, store_identity=identity)
        by_id = {variant_id: row for variant_id, row in zip(observed_ids, observed_rows)}
        matched: list[str] = []
        for expected_row in expected_rows:
            raw_variant_id = first(expected_row, "id", "variant_gid", default=None)
            variant_id = _observed_gid(raw_variant_id, "ProductVariant", "expected.variant_gid")
            if variant_id is None:
                fail("invalid_gid", "expected variant identity must be canonical.")
            row = by_id.get(variant_id)
            if not variant_id or row is None:
                return _base(operation, ReadbackVerdict.NOT_APPLIED, "variant_missing", expected_count=len(expected_rows), observed_count=len(observed_rows), matched=matched, user_errors=errors, store_identity=identity)
            for name, value in expected_row.items():
                if name in {"id", "variant_gid"}:
                    continue
                if not _equal(name, value, _field(row, name)):
                    return _base(operation, ReadbackVerdict.NOT_APPLIED, "variant_mismatch", expected_count=len(expected_rows), observed_count=len(observed_rows), matched=matched, user_errors=errors, store_identity=identity)
            matched.append(variant_id)
        if errors:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=len(expected_rows), observed_count=len(observed_rows), matched=matched, user_errors=errors, store_identity=identity)
        return _base(operation, ReadbackVerdict.APPLIED, "exact_variant_values", expected_count=len(expected_rows), observed_count=len(observed_rows), matched=matched, store_identity=identity)

    if operation == MEDIA_STAGE_OPERATION:
        return _base(operation, ReadbackVerdict.INCONCLUSIVE, "stage_identity_cannot_prove_target", expected_count=1, observed_count=1 if observed is not None else 0, user_errors=errors, store_identity=identity)

    if operation == MEDIA_FILE_CREATE_OPERATION:
        rows = _media_rows(observed)
        raw_file_gid = first(expected_map, "file_gid", "id", default=None)
        expected_file_gid = None
        if raw_file_gid is not None:
            expected_file_gid = _observed_gid(raw_file_gid, "File", "expected.file_gid")
            if expected_file_gid is None:
                fail("invalid_gid", "expected.file_gid must be a canonical Shopify File GID.")
        raw_filename = first(expected_map, "filename", "name", default=None)
        filename = text(raw_filename, "expected.filename", max_length=1024) if raw_filename is not None else None
        if expected_file_gid is None and filename is None:
            fail("missing_media_identity", "File readback requires a filename or immutable File GID.")
        if expected_file_gid is not None:
            matching = [
                row for row in rows
                if _observed_gid(first(row, "id", "file_gid", default=None), "File", "observed.file_gid") == expected_file_gid
            ]
        else:
            matching = [row for row in rows if first(row, "filename", "name", default=None) == filename]
        if len(matching) > 1:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "duplicate_remote_file", expected_count=1, observed_count=len(matching), user_errors=errors, store_identity=identity)
        if not matching:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "file_not_found", expected_count=1, observed_count=len(rows), user_errors=errors, store_identity=identity)
        file_id = _observed_gid(first(matching[0], "id", "file_gid", default=None), "File", "observed.file_gid")
        if file_id is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        if errors:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        reason = "verified_exact_file_identity" if expected_file_gid is not None else "adopted_exact_filename"
        return _base(operation, ReadbackVerdict.APPLIED, reason, expected_count=1, observed_count=1, matched=(file_id,), store_identity=identity)

    if operation == MEDIA_ASSOCIATE_OPERATION:
        observed_product = _product(observed)
        observed_product_gid = _observed_gid(
            first(observed_product, "id", "product_gid", default=None) if isinstance(observed_product, Mapping) else None,
            "Product",
            "observed.product_gid",
        )
        if observed_product_gid is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_product_identity", user_errors=errors, store_identity=identity)
        if observed_product_gid != expected_product_gid:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "product_identity_mismatch", user_errors=errors, store_identity=identity)
        rows = _media_rows(observed)
        raw_expected_file = expected_map.get("file_gid", expected_map.get("id", ""))
        expected_file = _observed_gid(raw_expected_file, "File", "expected.file_gid")
        if expected_file is None:
            fail("invalid_gid", "expected.file_gid must be a canonical Shopify File GID.")
        observed_files = [_observed_gid(first(row, "id", "file_gid", default=None), "File", "observed.file_gid") for row in rows]
        if any(value is None for value in observed_files):
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=1, observed_count=len(rows), user_errors=errors, store_identity=identity)
        match = expected_file in observed_files
        if not match:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "media_reference_missing", expected_count=1, observed_count=len(rows), user_errors=errors, store_identity=identity)
        if errors:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=1, observed_count=len(rows), user_errors=errors, store_identity=identity)
        return _base(operation, ReadbackVerdict.APPLIED, "exact_media_reference", expected_count=1, observed_count=len(rows), matched=(expected_file,), store_identity=identity)

    if operation == BINDING_NAMESPACE_OPERATION:
        rows = _rows(observed, "metafieldDefinitions", "nodes")
        if not rows:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "binding_definition_not_found", expected_count=1, user_errors=errors, store_identity=identity)
        if len(rows) > 1:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "duplicate_binding_definition", expected_count=1, observed_count=len(rows), user_errors=errors, store_identity=identity)
        if errors:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "partial_user_errors", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        row = rows[0]
        definition_id = _observed_gid(first(row, "id", "definition_gid", default=None), "MetafieldDefinition", "observed.definition_gid")
        if definition_id is None:
            return _base(operation, ReadbackVerdict.INCONCLUSIVE, "invalid_remote_identity", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        expected_key = first(expected_map, "definition_key", "key", default=None)
        expected_type = first(expected_map, "type", default=None)
        expected_owner = first(expected_map, "owner", "owner_type", default=None)
        observed_key = row.get("key")
        observed_type = row.get("type")
        observed_owner = first(row, "ownerType", "owner_type", default=None)
        if isinstance(observed_type, Mapping):
            observed_type = observed_type.get("name")
        if isinstance(expected_type, Mapping):
            expected_type = expected_type.get("name")
        if expected_key is None or expected_type is None or expected_owner is None:
            fail("missing_binding_identity", "binding definition readback requires key, type, and owner expectations.")
        if observed_key != expected_key or observed_type != expected_type or observed_owner != expected_owner:
            return _base(operation, ReadbackVerdict.NOT_APPLIED, "binding_definition_mismatch", expected_count=1, observed_count=1, user_errors=errors, store_identity=identity)
        return _base(operation, ReadbackVerdict.APPLIED, "binding_definition_present", expected_count=1, observed_count=1, matched=(definition_id,), store_identity=identity)

    return _base(operation, ReadbackVerdict.INCONCLUSIVE, "unsupported_readback_operation", user_errors=errors, store_identity=identity)


def evaluate_readback(*args: Any, **kwargs: Any) -> ReadbackResult:
    return evaluate_remote_readback(*args, **kwargs)


def readback_verdict(*args: Any, **kwargs: Any) -> ReadbackResult:
    return evaluate_remote_readback(*args, **kwargs)


__all__ = [
    "BindingNamespaceReadEvidence", "ReadbackResult", "ReadbackVerdict",
    "attest_binding_namespace_read", "evaluate_readback", "evaluate_remote_readback",
    "readback_verdict",
]
