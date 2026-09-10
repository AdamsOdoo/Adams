from . import shopify_connector_customer_binding
from . import shopify_connector_store_settings
from . import shopify_connector_setup_wizard
from . import shopify_connector_readiness_check
from . import shopify_connector_res_partner
from . import shopify_connector_customer_importer
from . import shopify_connector_order_binding
from . import shopify_connector_sale_order_line
from . import shopify_connector_sale_order_projection
from . import shopify_connector_order_importer
from . import shopify_connector_tax_mapping
from . import shopify_connector_order_scan
from . import shopify_connector_order_scan_p06
# Sales query documents and explicit gateway methods are registered only after
# the customer/order importers and scan service have defined their contracts.
from . import shopify_connector_read_gateway
from . import shopify_connector_order_reconnect
from . import shopify_connector_ui_store360_sale
