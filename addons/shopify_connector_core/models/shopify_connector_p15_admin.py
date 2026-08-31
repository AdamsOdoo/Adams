"""Compatibility import for the split P15 administrator extensions.

The model classes are intentionally defined in cohesive files.  Existing
imports of this module remain valid, and importing this module preserves the
registration order: shared vocabulary, store, settings, typed reads, then
named commands.
"""

from .shopify_connector_p15_shared import (
    P15_CAPACITY_ADVISORY_CLASSID,
    P15_COMMAND_NAMES,
    P15_CURSOR_RE,
    P15_EDITABLE_SETTINGS_GROUP_FIELDS,
    P15_MAX_LIST_LIMIT,
    P15_MAX_SEARCH_LENGTH,
    P15_MAX_TEXT_SETTING_LENGTH,
    P15_READINESS_GROUP_LABELS,
    P15_SERVICE_SENTINEL,
    P15_SERVICE_SENTINEL_CONTEXT,
    P15_SETTINGS_GROUP_FIELDS,
    P15_SETTINGS_GROUP_LABELS,
    P15_SHA256_RE,
    _p15_datetime,
    _p15_nonnegative_int,
    _p15_parse_datetime,
    _p15_positive_id,
    _p15_safe_text,
)
from .shopify_connector_p15_store import ShopifyConnectorP15Store
from .shopify_connector_p15_settings import ShopifyConnectorP15Settings
from .shopify_connector_p15_ui import ShopifyConnectorP15UiFacade
from .shopify_connector_p15_actions import ShopifyConnectorP15Actions
from .shopify_connector_p15_commands import ShopifyConnectorP15ApplicationFacade

__all__ = [
    "P15_COMMAND_NAMES",
    "P15_EDITABLE_SETTINGS_GROUP_FIELDS",
    "P15_SETTINGS_GROUP_FIELDS",
    "ShopifyConnectorP15ApplicationFacade",
    "ShopifyConnectorP15Actions",
    "ShopifyConnectorP15Settings",
    "ShopifyConnectorP15Store",
    "ShopifyConnectorP15UiFacade",
]
