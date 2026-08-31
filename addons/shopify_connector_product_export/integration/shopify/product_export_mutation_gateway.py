"""P08 product-export mutation gateway, retained as an unwired seam.

The documents below are the exact V1 product export operations: connector
binding-definition bootstrap, safe ``productSet`` create, scalar
``productUpdate``, bulk variant update and bulk variant create.  The adapter
accepts already-built allowlisted inputs from the domain service and returns
only immutable normalized evidence.  It owns no product policy, ORM writes,
credentials, HTTP, retries or reconciliation reads.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
    DurableIntentDescriptor,
    MutationGateway,
    MutationGatewayError,
    MutationOutcome,
    MutationRequest,
    MutationShapeError,
    ReadbackPlanDescriptor,
    freeze_json,
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
MAX_EXPORT_VARIANTS = 100
BINDING_METAFIELD_KEY = "odoo_template_custom_id_v2"
BINDING_METAFIELD_TYPE = "id"
BINDING_METAFIELD_OWNER = "PRODUCT"

BINDING_NAMESPACE_OPERATION = "product_export.binding_namespace"
PRODUCT_CREATE_OPERATION = "product_export.create"
PRODUCT_UPDATE_OPERATION = "product_export.update"
VARIANTS_UPDATE_OPERATION = "product_export.variants_update"
VARIANTS_CREATE_OPERATION = "product_export.variants_create"
BINDING_DEFINITION_READ_OPERATION = "product_export.binding_definition.read"
PRODUCT_CREATE_READ_OPERATION = "product_export.create.read"
PRODUCT_UPDATE_READ_OPERATION = "product_export.update.read"
VARIANTS_UPDATE_READ_OPERATION = "product_export.variants_update.read"
VARIANTS_CREATE_READ_OPERATION = "product_export.variants_create.read"

BINDING_DEFINITION_QUERY = (
    "query ProductExportBindingDefinition($key: String!) { "
    "metafieldDefinitions(first: 1, ownerType: PRODUCT, key: $key) { "
    "nodes { id key ownerType type { name } } pageInfo { hasNextPage } } shop { myshopifyDomain } }"
)
BINDING_NAMESPACE_DOCUMENT = (
    "mutation ProductExportBindingNamespace($definition: MetafieldDefinitionInput!) { "
    "metafieldDefinitionCreate(definition: $definition) { "
    "createdDefinition { id key namespace type { name } } "
    "userErrors { code field message } } }"
)
PRODUCT_CREATE_DOCUMENT = (
    "mutation ProductExportCreate($input: ProductSetInput!, "
    "$identifier: ProductSetIdentifiers!) { "
    "productSet(input: $input, identifier: $identifier, synchronous: true) { "
    "product { id handle title status updatedAt descriptionHtml vendor "
    "productType tags variants(first: 100) { nodes { id sku barcode price compareAtPrice "
    "selectedOptions { name value } inventoryItem { id sku tracked } } } } "
    "userErrors { code field message } } }"
)
PRODUCT_UPDATE_DOCUMENT = (
    "mutation ProductExportUpdate($product: ProductUpdateInput!, "
    "$identifier: ProductUpdateIdentifiers!) { "
    "productUpdate(product: $product, identifier: $identifier) { "
    "product { id updatedAt title descriptionHtml vendor productType tags status } "
    "userErrors { field message } } }"
)
VARIANTS_UPDATE_DOCUMENT = (
    "mutation ProductExportVariantsUpdate($productId: ID!, "
    "$variants: [ProductVariantsBulkInput!]!, $allowPartialUpdates: Boolean) { "
    "productVariantsBulkUpdate(productId: $productId, variants: $variants, "
    "allowPartialUpdates: $allowPartialUpdates) { "
    "productVariants { id barcode price compareAtPrice inventoryItem { id sku } } "
    "userErrors { code field message } } }"
)
VARIANTS_CREATE_DOCUMENT = (
    "mutation ProductExportVariantsCreate($productId: ID!, "
    "$variants: [ProductVariantsBulkInput!]!, "
    "$strategy: ProductVariantsBulkCreateStrategy) { "
    "productVariantsBulkCreate(productId: $productId, variants: $variants, strategy: $strategy) { "
    "productVariants { id sku barcode price compareAtPrice selectedOptions { name value } "
    "inventoryItem { id sku tracked } } userErrors { code field message } } }"
)

PRODUCT_CREATE_READ_QUERY = (
    "query ProductExportReconcileCreate($identifier: ProductIdentifierInput!) { "
    "product: productByIdentifier(identifier: $identifier) { id title status "
    "descriptionHtml vendor productType tags updatedAt variants(first: 100) { nodes { id sku barcode price compareAtPrice "
    "selectedOptions { name value } inventoryItem { id sku tracked } } pageInfo { hasNextPage } } } "
    "shop { myshopifyDomain } }"
)
PRODUCT_UPDATE_READ_QUERY = (
    "query ProductExportReconcileUpdate($id: ID!) { product(id: $id) { id title descriptionHtml vendor productType tags status updatedAt } shop { myshopifyDomain } }"
)
VARIANTS_UPDATE_READ_QUERY = (
    "query ProductExportReconcileVariants($id: ID!) { product(id: $id) { id variants(first: 100) { nodes { id barcode price compareAtPrice inventoryItem { id sku } } pageInfo { hasNextPage } } } shop { myshopifyDomain } }"
)
VARIANTS_CREATE_READ_QUERY = (
    "query ProductExportReconcileVariantCreate($id: ID!) { product(id: $id) { id variants(first: 100) { nodes { id sku barcode price compareAtPrice inventoryItem { id sku tracked } } pageInfo { hasNextPage } } } shop { myshopifyDomain } }"
)


def _read(key: str, name: str, document: str, variables: Mapping[str, Any], summary: str) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(key, name, "query", SHOPIFY_API_VERSION, document, variables, "ProductReadResult", "GraphQLError", SideEffectMetadata("observe", summary, False), fixture_keys=("readback_applied", "readback_not_applied", "readback_inconclusive"))


def _mutation(key: str, name: str, document: str, variables: Mapping[str, Any], effect: SideEffectMetadata, read_key: str, strategy: str, summary: str) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(key, name, "mutation", SHOPIFY_API_VERSION, document, variables, "ProductMutationResult", "GraphQLError", effect, ReadbackMetadata(True, read_key, strategy, summary), cost_expectation={"mode": "observed", "request_count": 1}, fixture_keys=("success", "user_errors", "top_level_error", "timeout_before_send", "timeout_after_send", "malformed_result"))


PRODUCT_EXPORT_MUTATION_REGISTRY = ShopifyOperationRegistry(
    (
        _read(BINDING_DEFINITION_READ_OPERATION, "ProductExportBindingDefinition", BINDING_DEFINITION_QUERY, {"key": "String!"}, "Reads the connector-owned binding definition after bootstrap uncertainty."),
        _read(PRODUCT_CREATE_READ_OPERATION, "ProductExportReconcileCreate", PRODUCT_CREATE_READ_QUERY, {"identifier": "ProductIdentifierInput!"}, "Reads the canonical product identified by the connector binding."),
        _read(PRODUCT_UPDATE_READ_OPERATION, "ProductExportReconcileUpdate", PRODUCT_UPDATE_READ_QUERY, {"id": "ID!"}, "Reads exact scalar values after a possible product update."),
        _read(VARIANTS_UPDATE_READ_OPERATION, "ProductExportReconcileVariants", VARIANTS_UPDATE_READ_QUERY, {"id": "ID!"}, "Reads exact variant values after a possible bulk update."),
        _read(VARIANTS_CREATE_READ_OPERATION, "ProductExportReconcileVariantCreate", VARIANTS_CREATE_READ_QUERY, {"id": "ID!"}, "Reads variants by product and SKU after a possible bulk create."),
        _mutation(BINDING_NAMESPACE_OPERATION, "ProductExportBindingNamespace", BINDING_NAMESPACE_DOCUMENT, {"definition": "MetafieldDefinitionInput!"}, SideEffectMetadata("create", "Creates the connector-owned product binding definition.", True), BINDING_DEFINITION_READ_OPERATION, "read_binding_definition", "An existing compatible definition is the desired state; no duplicate definition is created."),
        _mutation(PRODUCT_CREATE_OPERATION, "ProductExportCreate", PRODUCT_CREATE_DOCUMENT, {"input": "ProductSetInput!", "identifier": "ProductSetIdentifiers!"}, SideEffectMetadata("create", "Creates one new Shopify product through the V1 custom-id ProductSet path.", True), PRODUCT_CREATE_READ_OPERATION, "read_product_by_binding", "Read the connector custom-id product and adopt it if a create acknowledgement was lost; never replay blindly."),
        _mutation(PRODUCT_UPDATE_OPERATION, "ProductExportUpdate", PRODUCT_UPDATE_DOCUMENT, {"product": "ProductUpdateInput!", "identifier": "ProductUpdateIdentifiers!"}, SideEffectMetadata("update", "Updates only the confirmed Odoo-owned scalar product fields.", True), PRODUCT_UPDATE_READ_OPERATION, "read_product_scalars", "Read the canonical product and compare exactly the confirmed scalar fields; never resend an uncertain update."),
        _mutation(VARIANTS_UPDATE_OPERATION, "ProductExportVariantsUpdate", VARIANTS_UPDATE_DOCUMENT, {"productId": "ID!", "variants": "[ProductVariantsBulkInput!]!", "allowPartialUpdates": "Boolean"}, SideEffectMetadata("update", "Updates a bounded all-or-nothing set of existing Shopify variants.", True), VARIANTS_UPDATE_READ_OPERATION, "read_product_variants", "Read the canonical product variants and compare each requested variant; never replay an uncertain batch."),
        _mutation(VARIANTS_CREATE_OPERATION, "ProductExportVariantsCreate", VARIANTS_CREATE_DOCUMENT, {"productId": "ID!", "variants": "[ProductVariantsBulkInput!]!", "strategy": "ProductVariantsBulkCreateStrategy"}, SideEffectMetadata("create", "Creates a bounded set of Shopify variants while preserving the standalone default variant.", True), VARIANTS_CREATE_READ_OPERATION, "read_product_variants_by_sku", "Read the canonical product and adopt exact SKU identities after uncertainty; never create a second variant blindly."),
    )
)
PRODUCT_EXPORT_MUTATION_REGISTRY.freeze()


def _intent(operation_key: str, scope: str | None, business: Mapping[str, Any] | None, preconditions: Mapping[str, Any] | None, idempotency_key: str, defaults: Mapping[str, Any], target: Mapping[str, Any]) -> DurableIntentDescriptor:
    return DurableIntentDescriptor(operation_key, scope or "product_export:" + str(target.get("product_gid") or target.get("template_id") or target.get("definition_key")), business if business is not None else defaults, preconditions if preconditions is not None else defaults, idempotency_key)


def _request(spec: ShopifyOperationSpec, variables: Mapping[str, Any], intent: DurableIntentDescriptor, target: Mapping[str, Any]) -> MutationRequest:
    return MutationRequest(spec, variables, intent, ReadbackPlanDescriptor.from_metadata(spec.readback, target))


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MutationGatewayError("invalid_input", f"{field_name} must be an object.")
    return dict(value)


def _allow(value: Mapping[str, Any], allowed: set[str], field_name: str) -> dict[str, Any]:
    unknown = set(value) - allowed
    if unknown:
        raise MutationGatewayError("unsupported_field", f"{field_name} contains an unsupported field.")
    return value.copy()


def _product_variant(value: Any, *, require_id: bool, field_name: str) -> dict[str, Any]:
    raw = _mapping(value, field_name)
    allowed = {"id", "sku", "barcode", "price", "compareAtPrice", "optionValues", "inventoryItem"}
    entry = _allow(raw, allowed, field_name)
    if require_id:
        entry["id"] = require_gid(entry.get("id"), "ProductVariant", field_name + ".id")
    elif "id" in entry:
        raise MutationGatewayError("unsupported_field", f"{field_name}.id is not allowed on create.")
    if "inventoryItem" in entry:
        item = _mapping(entry["inventoryItem"], field_name + ".inventoryItem")
        if set(item) != {"sku"}:
            raise MutationGatewayError("unsupported_field", f"{field_name}.inventoryItem accepts sku only.")
        entry["inventoryItem"] = {"sku": require_text(item["sku"], field_name + ".inventoryItem.sku", max_length=512)}
    for key in ("sku", "barcode"):
        if key in entry:
            entry[key] = require_text(entry[key], field_name + "." + key, max_length=512)
    for key in ("price", "compareAtPrice"):
        if key in entry and entry[key] is not None:
            entry[key] = require_text(entry[key], field_name + "." + key, max_length=128)
    if "optionValues" in entry:
        options = entry["optionValues"]
        if not isinstance(options, list) or not options or len(options) > 3:
            raise MutationGatewayError("invalid_input", f"{field_name}.optionValues must be a non-empty list.")
        normalized_options: list[dict[str, str]] = []
        for option in options:
            row = _mapping(option, field_name + ".optionValues[]")
            if set(row) != {"optionName", "name"}:
                raise MutationGatewayError("unsupported_field", "variant option values must use optionName and name.")
            normalized_options.append({
                "optionName": require_text(row["optionName"], "optionName", max_length=256),
                "name": require_text(row["name"], "option value name", max_length=256),
            })
        entry["optionValues"] = normalized_options
    return entry


def _product_scalars(value: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    """Validate the V1 scalar ProductSet/ProductUpdate input surface."""

    normalized = _allow(
        value,
        {"title", "descriptionHtml", "vendor", "productType", "tags", "status"},
        field_name,
    )
    for key in ("title", "descriptionHtml", "vendor", "productType", "status"):
        if key in normalized:
            normalized[key] = require_text(normalized[key], field_name + "." + key, max_length=65_536)
    if "tags" in normalized:
        tags = normalized["tags"]
        if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() or len(tag) > 256 for tag in tags):
            raise MutationGatewayError("invalid_input", field_name + ".tags must be a list of bounded strings.")
        normalized["tags"] = list(tags)
    return normalized


class ProductExportMutationGateway(MutationGateway):
    """Pure request/result adapter for V1 product export mutations."""

    def build_binding_namespace(self, *, idempotency_key: str, operation_scope_key: str | None = None, business_intent: Mapping[str, Any] | None = None, preconditions_snapshot: Mapping[str, Any] | None = None) -> MutationRequest:
        require_text(idempotency_key, "idempotency_key", max_length=512)
        definition = {"key": BINDING_METAFIELD_KEY, "name": "Odoo product template id", "ownerType": BINDING_METAFIELD_OWNER, "type": BINDING_METAFIELD_TYPE, "description": "Connector-owned binding identity written by the Odoo Shopify connector. Do not edit."}
        defaults = {"definition_key": BINDING_METAFIELD_KEY, "owner": BINDING_METAFIELD_OWNER, "type": BINDING_METAFIELD_TYPE}
        target = {"definition_key": BINDING_METAFIELD_KEY}
        intent = _intent(BINDING_NAMESPACE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(BINDING_NAMESPACE_OPERATION), {"definition": definition}, intent, target)

    def build_create(self, product_input: Mapping[str, Any], template_id: str | int, *, idempotency_key: str, operation_scope_key: str | None = None, business_intent: Mapping[str, Any] | None = None, preconditions_snapshot: Mapping[str, Any] | None = None) -> MutationRequest:
        raw = _mapping(product_input, "product_input")
        allowed = {"title", "descriptionHtml", "vendor", "productType", "tags", "status", "productOptions", "variants"}
        normalized = _allow(raw, allowed, "product_input")
        scalar_values = {
            key: value
            for key, value in normalized.items()
            if key in {"title", "descriptionHtml", "vendor", "productType", "tags", "status"}
        }
        normalized.update(_product_scalars(scalar_values, "product_input"))
        if "variants" in normalized:
            variants = normalized["variants"]
            if not isinstance(variants, list) or len(variants) > MAX_EXPORT_VARIANTS:
                raise MutationGatewayError("invalid_input", "product_input.variants exceeds the V1 bound.")
            normalized["variants"] = [_product_variant(item, require_id=False, field_name="variants[]") for item in variants]
        if "productOptions" in normalized:
            options = normalized["productOptions"]
            if not isinstance(options, list) or len(options) > 3:
                raise MutationGatewayError("invalid_input", "productOptions exceeds the V1 bound.")
            normalized_options: list[dict[str, Any]] = []
            for option in options:
                row = _mapping(option, "productOptions[]")
                if set(row) != {"name", "values"} or not isinstance(row["values"], list) or not row["values"]:
                    raise MutationGatewayError("invalid_input", "productOptions entries must use name and non-empty values.")
                option_name = require_text(row["name"], "productOptions[].name", max_length=256)
                option_values: list[dict[str, str]] = []
                for value in row["values"]:
                    value_row = _mapping(value, "productOptions[].values[]")
                    if set(value_row) != {"name"}:
                        raise MutationGatewayError("unsupported_field", "productOptions values accept name only.")
                    option_values.append({
                        "name": require_text(value_row["name"], "productOptions[].values[].name", max_length=256),
                    })
                normalized_options.append({"name": option_name, "values": option_values})
            normalized["productOptions"] = normalized_options
        frozen = freeze_json(normalized, "product_input")
        if isinstance(template_id, bool) or not isinstance(template_id, (str, int)):
            raise MutationGatewayError("invalid_template_id", "template_id must be a string or strict integer.")
        template_value = require_text(str(template_id), "template_id", max_length=128)
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {"input": frozen, "identifier": {"customId": {"key": BINDING_METAFIELD_KEY, "value": template_value}}}
        defaults = {"template_id": template_value, "variant_count": len(normalized.get("variants") or []), "status": normalized.get("status", "")}
        target = {"template_id": template_value}
        intent = _intent(PRODUCT_CREATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(PRODUCT_CREATE_OPERATION), variables, intent, target)

    def build_update(self, product_gid: str, product_input: Mapping[str, Any], *, idempotency_key: str, operation_scope_key: str | None = None, business_intent: Mapping[str, Any] | None = None, preconditions_snapshot: Mapping[str, Any] | None = None) -> MutationRequest:
        product_gid = require_gid(product_gid, "Product", "product_gid")
        raw = _mapping(product_input, "product_input")
        normalized = _product_scalars(raw, "product_input")
        if not normalized:
            raise MutationGatewayError("invalid_input", "product_input must contain a confirmed scalar field.")
        freeze_json(normalized, "product_input")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {"product": normalized, "identifier": {"id": product_gid}}
        defaults = {"product_gid": product_gid, "fields": sorted(normalized)}
        target = {"product_gid": product_gid}
        intent = _intent(PRODUCT_UPDATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(PRODUCT_UPDATE_OPERATION), variables, intent, target)

    def build_variants_update(self, product_gid: str, variants: Sequence[Mapping[str, Any]], *, idempotency_key: str, operation_scope_key: str | None = None, business_intent: Mapping[str, Any] | None = None, preconditions_snapshot: Mapping[str, Any] | None = None) -> MutationRequest:
        product_gid = require_gid(product_gid, "Product", "product_gid")
        if not isinstance(variants, Sequence) or isinstance(variants, (str, bytes, Mapping)) or not variants or len(variants) > MAX_EXPORT_VARIANTS:
            raise MutationGatewayError("invalid_input", "variants must be a bounded non-empty sequence.")
        normalized = [_product_variant(item, require_id=True, field_name="variants[]") for item in variants]
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {"productId": product_gid, "variants": normalized, "allowPartialUpdates": False}
        defaults = {"product_gid": product_gid, "variant_gids": sorted(item["id"] for item in normalized)}
        target = {"product_gid": product_gid}
        intent = _intent(VARIANTS_UPDATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(VARIANTS_UPDATE_OPERATION), variables, intent, target)

    def build_variants_create(self, product_gid: str, variants: Sequence[Mapping[str, Any]], *, idempotency_key: str, strategy: str = "PRESERVE_STANDALONE_VARIANT", operation_scope_key: str | None = None, business_intent: Mapping[str, Any] | None = None, preconditions_snapshot: Mapping[str, Any] | None = None) -> MutationRequest:
        product_gid = require_gid(product_gid, "Product", "product_gid")
        if strategy != "PRESERVE_STANDALONE_VARIANT":
            raise MutationGatewayError("invalid_strategy", "Only PRESERVE_STANDALONE_VARIANT is allowed by V1.")
        if not isinstance(variants, Sequence) or isinstance(variants, (str, bytes, Mapping)) or not variants or len(variants) > MAX_EXPORT_VARIANTS:
            raise MutationGatewayError("invalid_input", "variants must be a bounded non-empty sequence.")
        normalized = [_product_variant(item, require_id=False, field_name="variants[]") for item in variants]
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {"productId": product_gid, "variants": normalized, "strategy": strategy}
        defaults = {"product_gid": product_gid, "strategy": strategy, "variant_count": len(normalized)}
        target = {"product_gid": product_gid}
        intent = _intent(VARIANTS_CREATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(VARIANTS_CREATE_OPERATION), variables, intent, target)

    def _normalize_response(self, request: MutationRequest, response: Mapping[str, Any]) -> MutationResult:
        data = response_data(response)
        payload_name = {BINDING_NAMESPACE_OPERATION: "metafieldDefinitionCreate", PRODUCT_CREATE_OPERATION: "productSet", PRODUCT_UPDATE_OPERATION: "productUpdate", VARIANTS_UPDATE_OPERATION: "productVariantsBulkUpdate", VARIANTS_CREATE_OPERATION: "productVariantsBulkCreate"}.get(request.operation_key)
        if payload_name is None:
            raise MutationGatewayError("operation_not_supported", "Product export mutation operation is not supported by this gateway.")
        payload = data.get(payload_name)
        if not isinstance(payload, Mapping):
            raise MutationShapeError("missing_payload", f"{payload_name} payload is missing.")
        errors = parse_user_errors(payload.get("userErrors"))
        if errors:
            partial_field = (
                payload.get("createdDefinition")
                if request.operation_key == BINDING_NAMESPACE_OPERATION
                else payload.get("product")
                if request.operation_key in {PRODUCT_CREATE_OPERATION, PRODUCT_UPDATE_OPERATION}
                else payload.get("productVariants")
            )
            if partial_field is not None:
                return self._result(
                    request,
                    MutationOutcome.UNCERTAIN,
                    "ambiguous_user_errors",
                    f"Shopify returned {payload_name} data alongside errors; verification is required.",
                    user_errors=errors,
                )
            return self._result(request, MutationOutcome.FAILED_CLEAN, "shopify_user_errors_validation", f"Shopify rejected {payload_name}.", user_errors=errors)
        if request.operation_key == BINDING_NAMESPACE_OPERATION:
            created = payload.get("createdDefinition")
            if not isinstance(created, Mapping) or created.get("key") != BINDING_METAFIELD_KEY or (created.get("type") or {}).get("name") != BINDING_METAFIELD_TYPE:
                raise MutationShapeError("invalid_success_payload", "binding definition response did not prove the connector-owned definition.")
            definition_gid = require_gid(created.get("id"), "MetafieldDefinition", "createdDefinition.id")
            return self._result(request, MutationOutcome.SUCCEEDED, None, "Shopify accepted the binding definition; verification remains required.", payload={"definition_id": definition_gid, "key": BINDING_METAFIELD_KEY, "type": BINDING_METAFIELD_TYPE})
        if request.operation_key in {PRODUCT_CREATE_OPERATION, PRODUCT_UPDATE_OPERATION}:
            product = payload.get("product")
            if not isinstance(product, Mapping):
                raise MutationShapeError("missing_success_payload", f"{payload_name} returned no product.")
            normalized = self._product(product)
            return self._result(request, MutationOutcome.SUCCEEDED, None, f"Shopify accepted {payload_name}; verification remains required.", payload={"product": normalized})
        variants = payload.get("productVariants")
        if not isinstance(variants, list) or not variants:
            raise MutationShapeError("missing_success_payload", f"{payload_name} returned no product variants.")
        return self._result(request, MutationOutcome.SUCCEEDED, None, f"Shopify accepted {payload_name}; verification remains required.", payload={"product_variants": [self._variant(item) for item in variants]})

    def _product(self, value: Mapping[str, Any]) -> Mapping[str, Any]:
        result: dict[str, Any] = {"id": require_gid(value.get("id"), "Product", "product.id")}
        for key in ("handle", "title", "status", "updatedAt", "descriptionHtml", "vendor", "productType"):
            if key in value and value[key] is not None:
                result[key] = require_text(value[key], "product." + key, max_length=65536)
        if "tags" in value:
            tags = value["tags"]
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag.strip() or len(tag) > 256 for tag in tags):
                raise MutationShapeError("invalid_success_payload", "product.tags is malformed.")
            result["tags"] = list(tags)
        if "variants" in value:
            connection = value["variants"]
            if not isinstance(connection, Mapping) or not isinstance(connection.get("nodes"), list) or len(connection["nodes"]) > MAX_EXPORT_VARIANTS:
                raise MutationShapeError("invalid_success_payload", "product.variants is malformed.")
            result["variants"] = [self._variant(item) for item in connection["nodes"]]
        return result

    def _variant(self, value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise MutationShapeError("invalid_success_payload", "product variant result is malformed.")
        result: dict[str, Any] = {"id": require_gid(value.get("id"), "ProductVariant", "productVariant.id")}
        for key in ("sku", "barcode", "price", "compareAtPrice"):
            if key in value and value[key] is not None:
                result[key] = require_text(value[key], "productVariant." + key, max_length=2048)
        inventory = value.get("inventoryItem")
        if inventory is not None:
            if not isinstance(inventory, Mapping):
                raise MutationShapeError("invalid_success_payload", "product variant inventoryItem is malformed.")
            result["inventory_item"] = {"id": require_gid(inventory.get("id"), "InventoryItem", "inventoryItem.id")}
            for key in ("sku", "tracked"):
                if key in inventory and inventory[key] is not None:
                    if key == "tracked" and not isinstance(inventory[key], bool):
                        raise MutationShapeError("invalid_success_payload", "inventoryItem.tracked is malformed.")
                    if key == "sku":
                        result["inventory_item"][key] = require_text(inventory[key], "inventoryItem.sku", max_length=512)
                    else:
                        result["inventory_item"][key] = inventory[key]
        if "selectedOptions" in value:
            options = value["selectedOptions"]
            if not isinstance(options, list):
                raise MutationShapeError("invalid_success_payload", "product variant selectedOptions is malformed.")
            normalized_options: list[dict[str, str]] = []
            for item in options:
                if not isinstance(item, Mapping):
                    raise MutationShapeError("invalid_success_payload", "product variant selectedOption is malformed.")
                normalized_options.append({
                    "name": require_text(item.get("name"), "selectedOption.name", max_length=256),
                    "value": require_text(item.get("value"), "selectedOption.value", max_length=256),
                })
            result["selected_options"] = normalized_options
        return result


__all__ = [
    "BINDING_DEFINITION_QUERY",
    "BINDING_NAMESPACE_OPERATION",
    "PRODUCT_CREATE_DOCUMENT",
    "PRODUCT_CREATE_OPERATION",
    "PRODUCT_EXPORT_MUTATION_REGISTRY",
    "PRODUCT_UPDATE_DOCUMENT",
    "PRODUCT_UPDATE_OPERATION",
    "VARIANTS_CREATE_DOCUMENT",
    "VARIANTS_CREATE_OPERATION",
    "VARIANTS_UPDATE_DOCUMENT",
    "VARIANTS_UPDATE_OPERATION",
    "ProductExportMutationGateway",
]
