"""P07 domain read compatibility adapter.

The domain gateways are pure and deliberately do not know about Odoo jobs,
credentials or company scope.  This model is their one Odoo boundary.  It
keeps the existing V1 method as the rollback delegate, while the typed path
uses the same authorized ``execute_business_read``/``execute_business`` or
lifecycle transport seam.  No mutation, schema, job transition or retry
policy lives here.

Each V1 method opts in with the private context marker below.  That makes the
legacy callback explicit and prevents the adapter from recursively re-entering
itself.  In ``legacy`` mode the callback is the only remote path.  In
``compare_reads`` mode it remains the returned business answer and the typed
read is a deterministic, digest-only sample.  ``v2`` uses only the typed
gateway.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from odoo import api, models
from odoo.exceptions import UserError

from ..integration.shopify.read_comparison import (
    ReadComparisonEvidence,
    safe_digest,
    should_compare,
)
from ..integration.shopify.read_contracts import ReadGatewayError


P07_LEGACY_CONTEXT_KEY = "shopify_connector_p07_legacy_read"
P07_SAMPLE_MODULUS = 100


def _json_safe(value: Any) -> Any:
    """Normalize only comparison values; never persist the value itself."""

    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "as_dict") and callable(value.as_dict):
        return _json_safe(value.as_dict())
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _digest(value: Any) -> str:
    """Return a payload-free digest, including V1's datetime evidence."""

    return safe_digest(_json_safe(value))


class _AuthorizedP07Delegate:
    """Call the already-authorized client exactly once per typed page."""

    def __init__(
        self,
        client: Any,
        store: Any,
        job: Any,
        documents: Mapping[str, str],
        *,
        purpose: str,
        webhook: bool = False,
        lifecycle: bool = False,
    ) -> None:
        self.client = client
        self.store = store
        self.job = job
        self.documents = documents
        self.purpose = purpose
        self.webhook = webhook
        self.lifecycle = lifecycle
        self.lifecycle_snapshot: Mapping[str, Any] | None = None

    def read(self, operation_key: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        document = self.documents.get(operation_key)
        if not isinstance(document, str):
            raise ReadGatewayError(
                "operation_unconfigured",
                "The checked-in Shopify domain read is not configured.",
                operation_key,
            )
        if self.webhook and self.lifecycle:
            if self.lifecycle_snapshot is None:
                # One snapshot covers the complete cursor traversal.  This is
                # the same lifecycle admission lifetime as V1 bootstrap and
                # avoids mixing credential generations between pages.
                self.lifecycle_snapshot = self.client._admit_lifecycle(
                    self.store, "readiness_probe",
                )
            return self.client._send_lifecycle(
                self.store,
                document,
                self.lifecycle_snapshot["token"],
                dict(variables),
            )
        if self.webhook:
            with self.client.execute_business(
                self.job, self.store, document, dict(variables),
            ) as result:
                return result
        with self.client.execute_business_read(
            self.job,
            self.store,
            document,
            dict(variables),
            purpose=self.purpose,
        ) as result:
            return result

    def finish_lifecycle(self) -> None:
        """Apply V1's post-network supersession fence once, after all pages."""

        if self.lifecycle_snapshot is not None and self.store._lifecycle_probe_superseded(
            self.lifecycle_snapshot
        ):
            # Use the existing client/store exception path.  Importing the
            # exception only here keeps the optional lifecycle test seam lazy.
            from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
                ShopifyQuiescedError,
            )

            raise ShopifyQuiescedError(
                "The webhook subscription read was superseded by a lifecycle "
                "or credential change; no evidence was written."
            )


class ShopifyConnectorDomainReadGateway(models.AbstractModel):
    """Authorized P07 adapter added to the single core read model."""

    _inherit = "shopify.connector.read.gateway"

    # ------------------------------------------------------------------
    # Shared mode/delegate helpers
    # ------------------------------------------------------------------

    @api.model
    def _p07_gateway(self, family: str):
        """Return the owning pure gateway, its exact documents and error type."""

        if family == "inventory":
            from odoo.addons.shopify_connector_inventory.integration.shopify.inventory_read_gateway import (
                InventoryReadGateway,
            )

            return InventoryReadGateway, dict(InventoryReadGateway.operation_documents)
        if family == "fulfillment":
            from odoo.addons.shopify_connector_fulfillment.integration.shopify.fulfillment_read_gateway import (
                FulfillmentReadGateway,
            )

            return FulfillmentReadGateway, dict(FulfillmentReadGateway.operation_documents)
        if family == "webhook":
            from odoo.addons.shopify_connector_webhook.integration.shopify.webhook_subscription_read_gateway import (
                WebhookSubscriptionReadGateway,
            )

            return WebhookSubscriptionReadGateway, dict(
                WebhookSubscriptionReadGateway.operation_documents
            )
        raise UserError("The requested Shopify domain read is not installed.")

    @api.model
    def _p07_run(
        self,
        *,
        family: str,
        operation_name: str,
        purpose: str,
        store: Any,
        job: Any,
        variables: Mapping[str, Any],
        typed_reader: Callable[[_AuthorizedP07Delegate], Any],
        legacy_reader: Callable[[], Any] | None,
        webhook: bool = False,
        lifecycle: bool = False,
    ) -> Any:
        store = self._assert_store(store)
        mode = self._store_mode(store)
        if mode in ("legacy", "compare_reads") and not callable(legacy_reader):
            raise UserError("The V1 rollback reader is not configured.")
        if mode == "legacy":
            return legacy_reader()

        _gateway_type, documents = self._p07_gateway(family)
        delegate = _AuthorizedP07Delegate(
            self.env["shopify.connector.api.client"],
            store,
            job,
            documents,
            purpose=purpose,
            webhook=webhook,
            lifecycle=lifecycle,
        )
        if mode == "v2":
            return typed_reader(delegate)

        # ``compare_reads`` uses the same deterministic sample primitive as
        # P06.  The legacy result is returned even when typed parsing fails.
        legacy = legacy_reader()
        if not should_compare(
            store.id,
            operation_name,
            variables,
            modulus=P07_SAMPLE_MODULUS,
        ):
            return legacy
        try:
            typed = typed_reader(delegate)
        except Exception:
            evidence = ReadComparisonEvidence(
                operation_name,
                True,
                False,
                _digest(legacy),
                None,
                typed_error=True,
            )
        else:
            legacy_digest = _digest(legacy)
            typed_digest = _digest(typed)
            evidence = ReadComparisonEvidence(
                operation_name,
                True,
                legacy_digest == typed_digest,
                legacy_digest,
                typed_digest,
            )
        self._p07_record_comparison(job, evidence)
        return legacy

    @api.model
    def _p07_record_comparison(
        self,
        job: Any,
        evidence: ReadComparisonEvidence,
    ) -> None:
        if not job:
            return
        self.env["shopify.connector.job.log"]._system_append(
            job,
            "verification_read",
            "P07 %s read comparison %s."
            % (evidence.operation_name, "matched" if evidence.equal else "differed"),
            technical_detail=json.dumps(
                evidence.as_dict(), sort_keys=True, separators=(",", ":")
            ),
        )

    @api.model
    def _p07_delegate_gateway(self, delegate: _AuthorizedP07Delegate, family: str):
        Gateway, _documents = self._p07_gateway(family)
        return Gateway(delegate, store_domain=delegate.store.shop_domain) if family in (
            "inventory", "webhook"
        ) else Gateway(delegate)

    # ------------------------------------------------------------------
    # Inventory reads
    # ------------------------------------------------------------------

    @api.model
    def read_inventory_pair(self, job: Any, store: Any, binding: Any) -> dict[str, Any]:
        item_gid = getattr(binding, "shopify_inventory_item_gid", False)
        mapping = getattr(binding, "location_mapping_id", False)
        location_gid = getattr(mapping, "shopify_gid", False)

        def typed(delegate: _AuthorizedP07Delegate) -> dict[str, Any]:
            gateway = self._p07_delegate_gateway(delegate, "inventory")
            return gateway.read_inventory_pair(item_gid, location_gid).to_legacy_dict()

        def legacy() -> Any:
            return self.env["shopify.connector.inventory.service"].with_context(
                **{P07_LEGACY_CONTEXT_KEY: True}
            )._read_shopify_inventory_pair(job, store, binding)

        return self._p07_run(
            family="inventory",
            operation_name="InventoryPairRead",
            purpose="inventory",
            store=store,
            job=job,
            variables={"itemId": item_gid, "locationId": location_gid},
            typed_reader=typed,
            legacy_reader=legacy,
        )

    @api.model
    def read_inventory_level(
        self, job: Any, store: Any, level_gid: str,
    ) -> dict[str, Any]:
        def typed(delegate: _AuthorizedP07Delegate) -> dict[str, Any]:
            gateway = self._p07_delegate_gateway(delegate, "inventory")
            result = gateway.read_inventory_level(level_gid).to_legacy_dict()
            # V1 hands the observation service a UTC-naive datetime, while
            # the pure DTO intentionally retains timezone awareness.
            stamp = result.get("source_updated_at")
            if isinstance(stamp, datetime) and stamp.tzinfo is not None:
                result["source_updated_at"] = stamp.astimezone(timezone.utc).replace(
                    tzinfo=None
                )
            return result

        def legacy() -> Any:
            return self.env[
                "shopify.connector.inventory.observation.service"
            ].with_context(**{P07_LEGACY_CONTEXT_KEY: True})._read_inventory_level(
                job, store, level_gid
            )

        return self._p07_run(
            family="inventory",
            operation_name="InventoryObservation",
            purpose="inventory",
            store=store,
            job=job,
            variables={"levelId": level_gid},
            typed_reader=typed,
            legacy_reader=legacy,
        )

    # ------------------------------------------------------------------
    # Fulfillment reads
    # ------------------------------------------------------------------

    @api.model
    def read_fulfillment_orders(
        self, job: Any, store: Any, order_gid: str,
    ) -> list[dict[str, Any]]:
        def typed(delegate: _AuthorizedP07Delegate) -> list[dict[str, Any]]:
            gateway = self._p07_delegate_gateway(delegate, "fulfillment")
            return [item.to_legacy_dict() for item in gateway.read_fulfillment_orders(order_gid)]

        def legacy() -> Any:
            return self.env["shopify.connector.fulfillment.service"].with_context(
                **{P07_LEGACY_CONTEXT_KEY: True}
            )._read_fulfillment_orders(job, store, order_gid)

        return self._p07_run(
            family="fulfillment",
            operation_name="ConnectorFulfillmentOrdersForOrder",
            purpose="fulfillment",
            store=store,
            job=job,
            variables={"orderId": order_gid},
            typed_reader=typed,
            legacy_reader=legacy,
        )

    @api.model
    def read_order_fulfillments(
        self, job: Any, store: Any, order_gid: str,
    ) -> list[dict[str, Any]]:
        def typed(delegate: _AuthorizedP07Delegate) -> list[dict[str, Any]]:
            gateway = self._p07_delegate_gateway(delegate, "fulfillment")
            return [item.to_legacy_dict() for item in gateway.read_order_fulfillments(order_gid)]

        def legacy() -> Any:
            return self.env["shopify.connector.fulfillment.service"].with_context(
                **{P07_LEGACY_CONTEXT_KEY: True}
            )._read_order_fulfillments(job, store, order_gid)

        return self._p07_run(
            family="fulfillment",
            operation_name="ConnectorOrderFulfillments",
            purpose="fulfillment",
            store=store,
            job=job,
            variables={"orderId": order_gid},
            typed_reader=typed,
            legacy_reader=legacy,
        )

    @api.model
    def read_fulfillment(
        self, job: Any, store: Any, fulfillment_gid: str,
    ) -> dict[str, Any] | None:
        def typed(delegate: _AuthorizedP07Delegate) -> dict[str, Any] | None:
            gateway = self._p07_delegate_gateway(delegate, "fulfillment")
            item = gateway.read_fulfillment(fulfillment_gid)
            return item.to_legacy_dict() if item is not None else None

        def legacy() -> Any:
            return self.env["shopify.connector.fulfillment.service"].with_context(
                **{P07_LEGACY_CONTEXT_KEY: True}
            )._read_fulfillment(job, store, fulfillment_gid)

        return self._p07_run(
            family="fulfillment",
            operation_name="ConnectorFulfillmentNode",
            purpose="fulfillment",
            store=store,
            job=job,
            variables={"id": fulfillment_gid},
            typed_reader=typed,
            legacy_reader=legacy,
        )

    @api.model
    def read_fulfillments_batch(
        self, job: Any, store: Any, fulfillment_gids: list[str] | tuple[str, ...],
    ) -> dict[str, dict[str, Any] | None]:
        def typed(delegate: _AuthorizedP07Delegate) -> dict[str, dict[str, Any] | None]:
            gateway = self._p07_delegate_gateway(delegate, "fulfillment")
            result = gateway.read_fulfillments_batch(fulfillment_gids)
            return {
                key: (value.to_legacy_dict() if value is not None else None)
                for key, value in result.items()
            }

        def legacy() -> Any:
            return self.env["shopify.connector.fulfillment.service"].with_context(
                **{P07_LEGACY_CONTEXT_KEY: True}
            )._read_fulfillments_batch(job, store, fulfillment_gids)

        return self._p07_run(
            family="fulfillment",
            operation_name="ConnectorFulfillmentNodes",
            purpose="fulfillment",
            store=store,
            job=job,
            variables={"ids": list(fulfillment_gids)},
            typed_reader=typed,
            legacy_reader=legacy,
        )

    # ------------------------------------------------------------------
    # Webhook subscription reads
    # ------------------------------------------------------------------

    @api.model
    def read_webhook_subscriptions(
        self, store: Any, job: Any, *, lifecycle: bool = False,
    ) -> list[dict[str, Any]]:
        def typed(delegate: _AuthorizedP07Delegate) -> list[dict[str, Any]]:
            gateway = self._p07_delegate_gateway(delegate, "webhook")
            result = gateway.read_all()
            delegate.finish_lifecycle()
            return result.to_legacy_list()

        def legacy() -> Any:
            return self.env["shopify.connector.webhook.subscription"].with_context(
                **{P07_LEGACY_CONTEXT_KEY: True}
            )._read_actual_subscriptions(store, job, lifecycle=lifecycle)

        return self._p07_run(
            family="webhook",
            operation_name="ConnectorWebhookSubscriptions",
            purpose="webhook",
            store=store,
            job=job,
            variables={"first": 100, "after": None},
            typed_reader=typed,
            legacy_reader=legacy,
            webhook=True,
            lifecycle=lifecycle,
        )


__all__ = ["P07_LEGACY_CONTEXT_KEY", "ShopifyConnectorDomainReadGateway"]
