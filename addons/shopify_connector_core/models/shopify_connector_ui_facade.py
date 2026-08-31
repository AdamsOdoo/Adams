"""Versioned, read-only V2 query facade.

The facade remains one exact Odoo model and public RPC boundary.  Its
projection implementations are split into cohesive plain-Python mixins so
individual files stay reviewable without changing model registration, record
access, DTO conversion, or query behavior.
"""

from __future__ import annotations

from odoo import models

from .shopify_connector_ui_facade_attention import (
    ShopifyConnectorUiFacadeAttentionMixin,
)
from .shopify_connector_ui_facade_attention_query import (
    ShopifyConnectorUiFacadeAttentionQueryMixin,
)
from .shopify_connector_ui_facade_overview import (
    ShopifyConnectorUiFacadeOverviewMixin,
)
from .shopify_connector_ui_facade_run import ShopifyConnectorUiFacadeRunMixin
from .shopify_connector_ui_facade_support import (
    ShopifyConnectorUiFacadeSupportMixin,
)


class ShopifyConnectorUiFacade(
    ShopifyConnectorUiFacadeOverviewMixin,
    ShopifyConnectorUiFacadeAttentionQueryMixin,
    ShopifyConnectorUiFacadeAttentionMixin,
    ShopifyConnectorUiFacadeRunMixin,
    ShopifyConnectorUiFacadeSupportMixin,
    models.AbstractModel,
):
    """The V2 read boundary over legacy connector records."""

    _name = "shopify.connector.ui.facade"
    _description = "Shopify Connector V2 Read Facade"

    MAX_ATTENTION_ITEMS = 80
    MAX_TIMELINE_EVENTS = 200
    MAX_HISTORY_EVENTS = 20
    MAX_ACTIVITY_DAYS = 7
    MAX_AFFECTED_RECORDS = 20
    MAX_RUN_ACTIONS = 200
    MAX_OVERVIEW_JOBS = 200

    _JOB_ATTENTION_STATES = (
        "blocked_manual_review",
        "failed_retryable",
        "failed_final",
    )
    _SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}
    _WORKFLOW_ANCHOR_FIELDS = {
        "catalog": "product_last_import_success_at",
        "orders": "sale_order_catchup_synced_through_at",
        "inventory": "inventory_last_push_scan_at",
        "fulfillment": "fulfillment_catchup_observed_through_at",
    }
    _PROVIDER_RANK = {
        "manual_review_job": 0,
        "mutation_uncertainty": 1,
        "product_match": 2,
        "inventory_mapping": 3,
        "fulfillment_review": 4,
        "readiness_failure": 5,
    }

    # These names are code-owned provider adapters, not client input.  Never
    # replace this with a model name supplied by an RPC caller.
    _OPTIONAL_MODELS = frozenset(
        (
            "shopify.connector.mutation.attempt",
            "shopify.connector.product.match.decision",
            "shopify.connector.location",
            "shopify.connector.location.mapping",
            "shopify.connector.inventory.level.binding",
            "shopify.connector.fulfillment.inbound.evidence",
        )
    )


__all__ = ["ShopifyConnectorUiFacade"]
