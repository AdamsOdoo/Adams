"""P08 webhook-subscription mutation adapters, intentionally unwired.

Desired/current subscription planning and the HMAC inbox remain owned by the
existing webhook models.  This file only preserves the two checked-in Admin
GraphQL mutation contracts and turns one delegate response into immutable,
payload-free evidence.  It never reads secrets, calls HTTP, writes Odoo,
retries or performs the later reconciliation read.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from shopify_connector_core.integration.shopify.mutation_contracts import (
    DurableIntentDescriptor,
    MutationGateway,
    MutationGatewayError,
    MutationOutcome,
    MutationRequest,
    MutationShapeError,
    ReadbackPlanDescriptor,
    parse_user_errors,
    require_gid,
    require_text,
    response_data,
)
from shopify_connector_core.integration.shopify.operation_registry import (
    ReadbackMetadata,
    ShopifyOperationRegistry,
    ShopifyOperationSpec,
    SideEffectMetadata,
)

from .webhook_subscription_read_gateway import SUBSCRIPTIONS_QUERY as WEBHOOK_SUBSCRIPTIONS_QUERY


SHOPIFY_API_VERSION = "2026-07"
WEBHOOK_SUBSCRIPTION_CREATE_OPERATION = "webhook.subscription.create"
WEBHOOK_SUBSCRIPTION_DELETE_OPERATION = "webhook.subscription.delete"
WEBHOOK_SUBSCRIPTIONS_READ_OPERATION = "webhook.subscriptions.read"

WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT = """
mutation ConnectorWebhookSubscriptionCreate(
  $topic: WebhookSubscriptionTopic!,
  $webhookSubscription: WebhookSubscriptionInput!
) {
  webhookSubscriptionCreate(
    topic: $topic,
    webhookSubscription: $webhookSubscription
  ) {
    userErrors { field message }
    webhookSubscription {
      id topic uri
      apiVersion { handle displayName supported }
      format includeFields
    }
  }
}
""".strip()
WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT = """
mutation ConnectorWebhookSubscriptionDelete($id: ID!) {
  webhookSubscriptionDelete(id: $id) {
    deletedWebhookSubscriptionId
    userErrors { field message }
  }
}
""".strip()

_TOPIC = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_API_VERSION = re.compile(r"^[0-9]{4}-[0-9]{2}$")


def _read_spec() -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        WEBHOOK_SUBSCRIPTIONS_READ_OPERATION,
        "ConnectorWebhookSubscriptions",
        "query",
        SHOPIFY_API_VERSION,
        WEBHOOK_SUBSCRIPTIONS_QUERY,
        {"first": "Int!", "after": "String"},
        "WebhookSubscriptionReadResult",
        "GraphQLError",
        SideEffectMetadata("observe", "Reads desired/current webhook subscription facts for mutation verification.", False),
        fixture_keys=("readback_applied", "readback_not_applied", "readback_inconclusive"),
    )


def _mutation_spec(key: str, name: str, document: str, variables: Mapping[str, Any], effect: SideEffectMetadata, strategy: str, summary: str) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        key,
        name,
        "mutation",
        SHOPIFY_API_VERSION,
        document,
        variables,
        "WebhookSubscriptionMutationResult",
        "GraphQLError",
        effect,
        ReadbackMetadata(True, WEBHOOK_SUBSCRIPTIONS_READ_OPERATION, strategy, summary),
        cost_expectation={"mode": "observed", "request_count": 1},
        fixture_keys=("success", "user_errors", "top_level_error", "timeout_before_send", "timeout_after_send", "malformed_result"),
    )


WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY = ShopifyOperationRegistry(
    (
        _read_spec(),
        _mutation_spec(
            WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
            "ConnectorWebhookSubscriptionCreate",
            WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT,
            {"topic": "WebhookSubscriptionTopic!", "webhookSubscription": "WebhookSubscriptionInput!"},
            SideEffectMetadata("create", "Creates one connector-owned Shopify webhook subscription.", True),
            "find_exact_desired_subscription",
            "List current subscriptions and match topic, callback digest, format, fields and API version; never create a second one on uncertainty.",
        ),
        _mutation_spec(
            WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
            "ConnectorWebhookSubscriptionDelete",
            WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT,
            {"id": "ID!"},
            SideEffectMetadata("delete", "Deletes one exact Shopify webhook subscription identity.", True),
            "confirm_subscription_absent",
            "List current subscriptions and confirm the exact subscription identity is absent; never retry blindly.",
        ),
    )
)
WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY.freeze()


def _uri_digest(uri: str) -> str:
    return hashlib.sha256(uri.encode("utf-8")).hexdigest()


def _include_fields(value: Sequence[str] | None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes, Mapping)):
        raise MutationGatewayError("invalid_include_fields", "include_fields must be a string sequence or None.")
    fields = list(value)
    if len(fields) > 128 or any(not isinstance(item, str) or not item or len(item) > 128 for item in fields):
        raise MutationGatewayError("invalid_include_fields", "include_fields contains an invalid field.")
    return fields or None


def _intent(operation_key: str, scope: str | None, business: Mapping[str, Any] | None, preconditions: Mapping[str, Any] | None, idempotency_key: str, defaults: Mapping[str, Any], target: Mapping[str, Any]) -> DurableIntentDescriptor:
    return DurableIntentDescriptor(
        operation_key,
        scope or "webhook_subscription:" + str(target.get("subscription_gid") or target.get("topic")),
        business if business is not None else defaults,
        preconditions if preconditions is not None else defaults,
        idempotency_key,
    )


def _request(spec: ShopifyOperationSpec, variables: Mapping[str, Any], intent: DurableIntentDescriptor, target: Mapping[str, Any]) -> MutationRequest:
    return MutationRequest(spec, variables, intent, ReadbackPlanDescriptor.from_metadata(spec.readback, target))


class WebhookSubscriptionMutationGateway(MutationGateway):
    """Build/classify exact subscription create and delete mutations."""

    def build_create(
        self,
        topic: str,
        callback_uri: str,
        *,
        include_fields: Sequence[str] | None = None,
        expected_api_version: str = SHOPIFY_API_VERSION,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        if not isinstance(topic, str) or not _TOPIC.fullmatch(topic):
            raise MutationGatewayError("invalid_topic", "topic must be a Shopify webhook topic enum.")
        require_text(callback_uri, "callback_uri", max_length=4096)
        if not callback_uri.startswith("https://"):
            raise MutationGatewayError("invalid_callback_uri", "callback_uri must use HTTPS.")
        if not isinstance(expected_api_version, str) or not _API_VERSION.fullmatch(expected_api_version):
            raise MutationGatewayError("invalid_api_version", "expected_api_version must use YYYY-MM.")
        fields = _include_fields(include_fields)
        require_text(idempotency_key, "idempotency_key", max_length=512)
        # The URI is required by Shopify's request, but only its digest enters
        # durable intent/readback evidence. The callback token never becomes
        # a normalized result or operator evidence value.
        digest = _uri_digest(callback_uri)
        defaults = {
            "action": "create",
            "topic": topic,
            "callback_url_digest": digest,
            "expected_api_version": expected_api_version,
            "expected_include_fields": fields or [],
            "format": "JSON",
        }
        target = {"topic": topic, "callback_url_digest": digest}
        intent = _intent(WEBHOOK_SUBSCRIPTION_CREATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        variables = {
            "topic": topic,
            "webhookSubscription": {"uri": callback_uri, "format": "JSON", "includeFields": fields},
        }
        return _request(self.registry.require_operation(WEBHOOK_SUBSCRIPTION_CREATE_OPERATION), variables, intent, target)

    def build_delete(
        self,
        subscription_gid: str,
        *,
        topic: str | None = None,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        subscription_gid = require_gid(subscription_gid, "WebhookSubscription", "subscription_gid")
        if topic is not None and (not isinstance(topic, str) or not _TOPIC.fullmatch(topic)):
            raise MutationGatewayError("invalid_topic", "topic must be a Shopify webhook topic enum.")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        defaults = {"action": "delete", "subscription_gid": subscription_gid, "topic": topic or ""}
        target = {"subscription_gid": subscription_gid}
        intent = _intent(WEBHOOK_SUBSCRIPTION_DELETE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(WEBHOOK_SUBSCRIPTION_DELETE_OPERATION), {"id": subscription_gid}, intent, target)

    def _normalize_response(self, request: MutationRequest, response: Mapping[str, Any]) -> Any:
        data = response_data(response)
        if request.operation_key == WEBHOOK_SUBSCRIPTION_CREATE_OPERATION:
            payload = data.get("webhookSubscriptionCreate")
            name = "webhookSubscriptionCreate"
        elif request.operation_key == WEBHOOK_SUBSCRIPTION_DELETE_OPERATION:
            payload = data.get("webhookSubscriptionDelete")
            name = "webhookSubscriptionDelete"
        else:
            raise MutationGatewayError("operation_not_supported", "Webhook subscription mutation operation is not supported by this gateway.")
        if not isinstance(payload, Mapping):
            raise MutationShapeError("missing_payload", f"{name} payload is missing.")
        errors = parse_user_errors(payload.get("userErrors"))
        if errors:
            partial_field = (
                payload.get("webhookSubscription")
                if request.operation_key == WEBHOOK_SUBSCRIPTION_CREATE_OPERATION
                else payload.get("deletedWebhookSubscriptionId")
            )
            if partial_field is not None:
                return self._result(
                    request,
                    MutationOutcome.UNCERTAIN,
                    "ambiguous_user_errors",
                    f"Shopify returned {name} data alongside errors; verification is required.",
                    user_errors=errors,
                )
            return self._result(request, MutationOutcome.FAILED_CLEAN, "shopify_user_errors_validation", f"Shopify rejected {name}.", user_errors=errors)
        if request.operation_key == WEBHOOK_SUBSCRIPTION_DELETE_OPERATION:
            deleted_gid = require_gid(payload.get("deletedWebhookSubscriptionId"), "WebhookSubscription", "deletedWebhookSubscriptionId")
            return self._result(request, MutationOutcome.SUCCEEDED, None, "Shopify accepted the subscription deletion; verification remains required.", payload={"deleted_subscription_gid": deleted_gid})
        node = payload.get("webhookSubscription")
        if not isinstance(node, Mapping):
            raise MutationShapeError("missing_success_payload", "webhookSubscriptionCreate returned no subscription object.")
        subscription_gid = require_gid(node.get("id"), "WebhookSubscription", "webhookSubscription.id")
        topic = node.get("topic")
        if not isinstance(topic, str) or not _TOPIC.fullmatch(topic):
            raise MutationShapeError("invalid_success_payload", "webhookSubscriptionCreate returned an invalid topic.")
        api_version = node.get("apiVersion")
        if not isinstance(api_version, Mapping):
            raise MutationShapeError("invalid_success_payload", "webhookSubscriptionCreate returned no API version object.")
        handle = api_version.get("handle")
        display_name = api_version.get("displayName")
        supported = api_version.get("supported")
        if not isinstance(handle, str) or not handle.strip() or len(handle) > 32 or not isinstance(display_name, str) or not display_name.strip() or len(display_name) > 256 or not isinstance(supported, bool):
            raise MutationShapeError("invalid_success_payload", "webhookSubscriptionCreate returned an invalid API version object.")
        fmt = node.get("format")
        if not isinstance(fmt, str) or not fmt.strip() or len(fmt) > 32:
            raise MutationShapeError("invalid_success_payload", "webhookSubscriptionCreate returned an invalid format.")
        fields = node.get("includeFields")
        normalized_fields = _include_fields(fields)
        uri = node.get("uri", node.get("callbackUrl"))
        if uri is None:
            uri_digest = None
        else:
            require_text(uri, "webhookSubscription.uri", max_length=4096)
            uri_digest = _uri_digest(uri)
        normalized = {
            "subscription": {
                "id": subscription_gid,
                "topic": topic,
                "uri_digest": uri_digest,
                "api_version": handle,
                "format": fmt,
                "include_fields": normalized_fields or [],
            }
        }
        return self._result(request, MutationOutcome.SUCCEEDED, None, "Shopify accepted the subscription creation; verification remains required.", payload=normalized)


__all__ = [
    "SHOPIFY_API_VERSION",
    "WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT",
    "WEBHOOK_SUBSCRIPTION_CREATE_OPERATION",
    "WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT",
    "WEBHOOK_SUBSCRIPTION_DELETE_OPERATION",
    "WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY",
    "WEBHOOK_SUBSCRIPTIONS_QUERY",
    "WEBHOOK_SUBSCRIPTIONS_READ_OPERATION",
    "WebhookSubscriptionMutationGateway",
]
