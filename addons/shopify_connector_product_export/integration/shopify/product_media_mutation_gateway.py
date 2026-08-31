"""P08 product-media mutation gateway, retained as an unwired seam.

The V1 media pipeline has three Shopify mutations:

* ``stagedUploadsCreate`` creates one short-lived upload target;
* ``fileCreate`` creates one Shopify File from the staged resource URL; and
* ``fileUpdate`` adds the File's reference to one product.

This adapter preserves those documents and wire variables, but it does not
perform the upload, call Shopify, read the ORM, load credentials, retry, or
run reconciliation.  The runtime which eventually wires this seam owns the
durable intent/attempt transaction and schedules the readback described by
each operation's registry metadata.

Signed upload URLs and parameter values are deliberately never copied into
normalized payload/evidence.  The request still carries the exact V1 values;
only bounded digests and parameter names cross the result boundary.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
    DurableIntentDescriptor,
    MutationGateway,
    MutationGatewayError,
    MutationOutcome,
    MutationRequest,
    MutationResult,
    MutationShapeError,
    ReadbackPlanDescriptor,
    parse_user_errors,
    require_gid,
    require_text,
    response_data,
)
from odoo.addons.shopify_connector_core.integration.shopify.operation_registry import (
    ReadbackMetadata,
    ShopifyOperationRegistry,
    ShopifyOperationSpec,
    SideEffectMetadata,
)


SHOPIFY_API_VERSION = "2026-07"
STAGED_RESOURCE = "PRODUCT_IMAGE"
MEDIA_CONTENT_TYPE = "IMAGE"
IMAGE_MIME_PNG = "image/png"
MEDIA_HTTP_METHOD = "POST"
MAX_MEDIA_FILES = 1
MAX_MEDIA_PARAMETERS = 64

MEDIA_STAGE_OPERATION = "product_export.media_stage"
MEDIA_FILE_CREATE_OPERATION = "product_export.media_file_create"
MEDIA_ASSOCIATE_OPERATION = "product_export.media_associate"
MEDIA_STAGE_READ_OPERATION = "product_export.media_stage.read"
MEDIA_FILE_CREATE_READ_OPERATION = "product_export.media_file_create.read"
MEDIA_ASSOCIATE_READ_OPERATION = "product_export.media_associate.read"

MEDIA_STAGE_DOCUMENT = (
    "mutation ProductExportMediaStage($input: [StagedUploadInput!]!) { "
    "stagedUploadsCreate(input: $input) { "
    "stagedTargets { url resourceUrl parameters { name value } } "
    "userErrors { field message } } }"
)
MEDIA_FILE_CREATE_DOCUMENT = (
    "mutation ProductExportMediaFileCreate($files: [FileCreateInput!]!) { "
    "fileCreate(files: $files) { files { id fileStatus alt } "
    "userErrors { code field message } } }"
)
MEDIA_ASSOCIATE_DOCUMENT = (
    "mutation ProductExportMediaAssociate($files: [FileUpdateInput!]!) { "
    "fileUpdate(files: $files) { files { id fileStatus alt } "
    "userErrors { code field message } } }"
)

MEDIA_STAGE_READ_QUERY = (
    "query ProductExportMediaStageIdentity { "
    "shop { myshopifyDomain } }"
)
MEDIA_FILE_CREATE_READ_QUERY = (
    "query ProductExportMediaFind($query: String!) { "
    "files(first: 5, query: $query) { nodes { id fileStatus "
    "... on MediaImage { image { url } } } } "
    "shop { myshopifyDomain } }"
)
MEDIA_ASSOCIATE_READ_QUERY = (
    "query ProductExportMediaAssociated($id: ID!) { "
    "product(id: $id) { id media(first: 50) { nodes { id "
    "... on MediaImage { id fileStatus } } pageInfo { hasNextPage } } } "
    "shop { myshopifyDomain } }"
)


def _read(
    key: str,
    name: str,
    document: str,
    variables: Mapping[str, Any],
    summary: str,
) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        key,
        name,
        "query",
        SHOPIFY_API_VERSION,
        document,
        variables,
        "ProductMediaReadResult",
        "GraphQLError",
        SideEffectMetadata("observe", summary, False),
        fixture_keys=("readback_applied", "readback_not_applied", "readback_inconclusive"),
    )


def _mutation(
    key: str,
    name: str,
    document: str,
    variables: Mapping[str, Any],
    effect: SideEffectMetadata,
    read_key: str,
    strategy: str,
    summary: str,
) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        key,
        name,
        "mutation",
        SHOPIFY_API_VERSION,
        document,
        variables,
        "ProductMediaMutationResult",
        "GraphQLError",
        effect,
        ReadbackMetadata(True, read_key, strategy, summary),
        cost_expectation={"mode": "observed", "request_count": 1},
        fixture_keys=(
            "success",
            "user_errors",
            "top_level_error",
            "timeout_before_send",
            "timeout_after_send",
            "malformed_result",
        ),
    )


PRODUCT_MEDIA_MUTATION_REGISTRY = ShopifyOperationRegistry(
    (
        _read(
            MEDIA_STAGE_READ_OPERATION,
            "ProductExportMediaStageIdentity",
            MEDIA_STAGE_READ_QUERY,
            {},
            "Reads the expected Shopify shop identity after a staged-target acknowledgement was lost.",
        ),
        _read(
            MEDIA_FILE_CREATE_READ_OPERATION,
            "ProductExportMediaFind",
            MEDIA_FILE_CREATE_READ_QUERY,
            {"query": "String!"},
            "Finds the connector-generated filename after File creation; zero, one and ambiguous matches remain distinct.",
        ),
        _read(
            MEDIA_ASSOCIATE_READ_OPERATION,
            "ProductExportMediaAssociated",
            MEDIA_ASSOCIATE_READ_QUERY,
            {"id": "ID!"},
            "Reads one product's bounded media list to verify the File reference.",
        ),
        _mutation(
            MEDIA_STAGE_OPERATION,
            "ProductExportMediaStage",
            MEDIA_STAGE_DOCUMENT,
            {"input": "[StagedUploadInput!]!"},
            SideEffectMetadata("create", "Creates one short-lived Shopify staged upload target.", True),
            MEDIA_STAGE_READ_OPERATION,
            "verify_shop_identity_then_require_fresh_stage",
            "A staged target does not change store state; on uncertainty verify shop identity and require a fresh target instead of reusing unknown upload parameters.",
        ),
        _mutation(
            MEDIA_FILE_CREATE_OPERATION,
            "ProductExportMediaFileCreate",
            MEDIA_FILE_CREATE_DOCUMENT,
            {"files": "[FileCreateInput!]!"},
            SideEffectMetadata("create", "Creates one Shopify File from the connector's staged resource.", True),
            MEDIA_FILE_CREATE_READ_OPERATION,
            "read_exact_file_identity",
            "Verify the immutable File GID after acknowledgement; an unknown identity is never adopted or replayed blindly.",
        ),
        _mutation(
            MEDIA_ASSOCIATE_OPERATION,
            "ProductExportMediaAssociate",
            MEDIA_ASSOCIATE_DOCUMENT,
            {"files": "[FileUpdateInput!]!"},
            SideEffectMetadata("update", "Adds one existing File reference to one Shopify product.", True),
            MEDIA_ASSOCIATE_READ_OPERATION,
            "read_product_media_reference",
            "Read the canonical product's media and confirm the exact File GID is referenced; never replay an uncertain association.",
        ),
    )
)
PRODUCT_MEDIA_MUTATION_REGISTRY.freeze()


def _bounded_text(value: Any, field_name: str, *, allow_empty: bool = False, max_length: int = 4096) -> str:
    if allow_empty and value == "":
        return ""
    return require_text(value, field_name, max_length=max_length)


def _https_url(value: Any, field_name: str) -> str:
    url = require_text(value, field_name, max_length=16_384)
    if not url.startswith("https://"):
        raise MutationGatewayError("invalid_url", f"{field_name} must use HTTPS.")
    return url


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _intent(
    operation_key: str,
    scope: str | None,
    business: Mapping[str, Any] | None,
    preconditions: Mapping[str, Any] | None,
    idempotency_key: str,
    defaults: Mapping[str, Any],
    target: Mapping[str, Any],
) -> DurableIntentDescriptor:
    scope_value = scope or "product_media:" + str(
        target.get("product_gid") or target.get("file_gid") or target.get("filename") or target.get("resource")
    )
    return DurableIntentDescriptor(
        operation_key,
        scope_value,
        business if business is not None else defaults,
        preconditions if preconditions is not None else defaults,
        idempotency_key,
    )


def _request(
    spec: ShopifyOperationSpec,
    variables: Mapping[str, Any],
    intent: DurableIntentDescriptor,
    target: Mapping[str, Any],
) -> MutationRequest:
    return MutationRequest(
        spec,
        variables,
        intent,
        ReadbackPlanDescriptor.from_metadata(spec.readback, target),
    )


def _files_input(value: Any, field_name: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, Mapping)):
        raise MutationGatewayError("invalid_media_files", f"{field_name} must be a sequence.")
    rows = list(value)
    if len(rows) != MAX_MEDIA_FILES:
        raise MutationGatewayError("invalid_media_files", f"{field_name} must contain exactly one file.")
    return rows


def _normalize_status(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field_name, max_length=64)


def _normalize_alt(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field_name, allow_empty=True, max_length=4096)


def _normalize_file(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MutationShapeError("invalid_success_payload", f"{field_name} is malformed.")
    result: dict[str, Any] = {
        "id": require_gid(value.get("id"), "File", field_name + ".id"),
    }
    if "fileStatus" in value:
        result["file_status"] = _normalize_status(value["fileStatus"], field_name + ".fileStatus")
    if "alt" in value:
        result["alt"] = _normalize_alt(value["alt"], field_name + ".alt")
    return result


def _normalize_parameters(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_MEDIA_PARAMETERS:
        raise MutationShapeError("invalid_success_payload", "staged target parameters are malformed.")
    normalized: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise MutationShapeError("invalid_success_payload", "staged target parameter is malformed.")
        name = require_text(item.get("name"), "stagedTarget.parameters.name", max_length=256)
        parameter_value = require_text(item.get("value"), "stagedTarget.parameters.value", max_length=16_384)
        normalized.append({"name": name, "value_sha256": _digest(parameter_value)})
    return normalized


class ProductMediaMutationGateway(MutationGateway):
    """Build/classify the exact V1 staged upload, File and association writes."""

    def build_stage(
        self,
        filename: str,
        *,
        mime_type: str = IMAGE_MIME_PNG,
        resource: str = STAGED_RESOURCE,
        http_method: str = MEDIA_HTTP_METHOD,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        filename = require_text(filename, "filename", max_length=1024)
        if mime_type != IMAGE_MIME_PNG or resource != STAGED_RESOURCE or http_method != MEDIA_HTTP_METHOD:
            raise MutationGatewayError("unsupported_media_stage", "V1 media staging requires the reviewed image POST contract.")
        if not isinstance(mime_type, str) or not isinstance(resource, str) or not isinstance(http_method, str):
            raise MutationGatewayError("invalid_media_stage", "media stage fields must be strings.")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {
            "input": [{
                "filename": filename,
                "mimeType": IMAGE_MIME_PNG,
                "resource": STAGED_RESOURCE,
                "httpMethod": MEDIA_HTTP_METHOD,
            }],
        }
        defaults = {
            "filename": filename,
            "mime_type": IMAGE_MIME_PNG,
            "resource": STAGED_RESOURCE,
            "http_method": MEDIA_HTTP_METHOD,
        }
        target = {"filename": filename, "resource": STAGED_RESOURCE}
        intent = _intent(MEDIA_STAGE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(MEDIA_STAGE_OPERATION), variables, intent, target)

    def build_file_create(
        self,
        staged_resource_url: str,
        filename: str,
        *,
        alt: str = "",
        content_type: str = MEDIA_CONTENT_TYPE,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        staged_resource_url = _https_url(staged_resource_url, "staged_resource_url")
        filename = require_text(filename, "filename", max_length=1024)
        alt = _bounded_text(alt, "alt", allow_empty=True, max_length=4096)
        if content_type != MEDIA_CONTENT_TYPE:
            raise MutationGatewayError("unsupported_media_content_type", "V1 media File creation requires IMAGE contentType.")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {
            "files": [{
                "originalSource": staged_resource_url,
                "contentType": MEDIA_CONTENT_TYPE,
                "filename": filename,
                "alt": alt,
            }],
        }
        defaults = {
            "filename": filename,
            "staged_resource_url_sha256": _digest(staged_resource_url),
            "content_type": MEDIA_CONTENT_TYPE,
        }
        target = {"filename": filename}
        intent = _intent(MEDIA_FILE_CREATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(MEDIA_FILE_CREATE_OPERATION), variables, intent, target)

    def build_associate(
        self,
        file_gid: str,
        product_gid: str,
        *,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        file_gid = require_gid(file_gid, "File", "file_gid")
        product_gid = require_gid(product_gid, "Product", "product_gid")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {"files": [{"id": file_gid, "referencesToAdd": [product_gid]}]}
        defaults = {"file_gid": file_gid, "product_gid": product_gid, "references_to_add": [product_gid]}
        target = {"file_gid": file_gid, "product_gid": product_gid}
        intent = _intent(MEDIA_ASSOCIATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(MEDIA_ASSOCIATE_OPERATION), variables, intent, target)

    def _normalize_response(self, request: MutationRequest, response: Mapping[str, Any]) -> MutationResult:
        data = response_data(response)
        if request.operation_key == MEDIA_STAGE_OPERATION:
            name = "stagedUploadsCreate"
            payload = data.get(name)
        elif request.operation_key == MEDIA_FILE_CREATE_OPERATION:
            name = "fileCreate"
            payload = data.get(name)
        elif request.operation_key == MEDIA_ASSOCIATE_OPERATION:
            name = "fileUpdate"
            payload = data.get(name)
        else:
            raise MutationGatewayError("operation_not_supported", "Product media mutation is not supported by this gateway.")
        if not isinstance(payload, Mapping):
            raise MutationShapeError("missing_payload", f"{name} payload is missing.")
        errors = parse_user_errors(payload.get("userErrors"))
        if errors:
            partial_field = (
                payload.get("stagedTargets")
                if request.operation_key == MEDIA_STAGE_OPERATION
                else payload.get("files")
            )
            if partial_field is not None:
                return self._result(
                    request,
                    MutationOutcome.UNCERTAIN,
                    "ambiguous_user_errors",
                    f"Shopify returned {name} data alongside errors; verification is required.",
                    user_errors=errors,
                )
            return self._result(
                request,
                MutationOutcome.FAILED_CLEAN,
                "shopify_user_errors_validation",
                f"Shopify rejected {name}.",
                user_errors=errors,
            )
        if request.operation_key == MEDIA_STAGE_OPERATION:
            targets = payload.get("stagedTargets")
            if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], Mapping):
                raise MutationShapeError("invalid_success_payload", "stagedUploadsCreate did not return exactly one staged target.")
            target = targets[0]
            url = _https_url(target.get("url"), "stagedTarget.url")
            resource_url = _https_url(target.get("resourceUrl"), "stagedTarget.resourceUrl")
            parameters = _normalize_parameters(target.get("parameters"))
            normalized = {
                "staged_target": {
                    "url_sha256": _digest(url),
                    "resource_url_sha256": _digest(resource_url),
                    "parameter_names": [item["name"] for item in parameters],
                    "parameters": parameters,
                }
            }
            return self._result(
                request,
                MutationOutcome.SUCCEEDED,
                None,
                "Shopify accepted the staged upload target; verification remains required.",
                payload=normalized,
            )
        files = payload.get("files")
        rows = _files_input(files, name + ".files")
        normalized_file = _normalize_file(rows[0], name + ".files[0]")
        return self._result(
            request,
            MutationOutcome.SUCCEEDED,
            None,
            f"Shopify accepted {name}; verification remains required.",
            payload={"file": normalized_file},
        )


__all__ = [
    "IMAGE_MIME_PNG",
    "MEDIA_ASSOCIATE_DOCUMENT",
    "MEDIA_ASSOCIATE_OPERATION",
    "MEDIA_ASSOCIATE_READ_QUERY",
    "MEDIA_FILE_CREATE_DOCUMENT",
    "MEDIA_FILE_CREATE_OPERATION",
    "MEDIA_FILE_CREATE_READ_QUERY",
    "MEDIA_HTTP_METHOD",
    "MEDIA_STAGE_DOCUMENT",
    "MEDIA_STAGE_OPERATION",
    "MEDIA_STAGE_READ_QUERY",
    "MEDIA_CONTENT_TYPE",
    "PRODUCT_MEDIA_MUTATION_REGISTRY",
    "ProductMediaMutationGateway",
    "STAGED_RESOURCE",
]
