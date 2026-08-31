# Wave 4 Gate B fulfillment models. Dependency order: schema/bindings and the
# core selection/ondelete extensions load first; the fulfillment service base
# (shopify.connector.fulfillment.service, declared in the reader) loads before
# the sibling files that extend it; the dispatch registration and the
# stock.picking trigger load last.
from . import shopify_connector_fulfillment_binding
from . import shopify_connector_fulfillment_inbound_evidence
from . import shopify_connector_store_settings
from . import shopify_connector_job
from . import shopify_connector_readiness_check
from . import shopify_connector_fulfillment_reader
from . import shopify_connector_fulfillment_create_strategy
from . import shopify_connector_fulfillment_tracking_strategy
from . import shopify_connector_fulfillment_admission
from . import shopify_connector_fulfillment_inbound
from . import shopify_connector_fulfillment_review
from . import shopify_connector_fulfillment_mode2
from . import shopify_connector_fulfillment_scans
from . import shopify_connector_fulfillment_reconnect
from . import shopify_connector_ui_store360_fulfillment
from . import shopify_connector_job_dispatch
from . import stock_picking
# P07 final read dispatch layer; it delegates V1 through a private context
# marker and keeps fulfillment selection/mutation siblings unchanged.
from . import shopify_connector_fulfillment_p07_read_adapter
