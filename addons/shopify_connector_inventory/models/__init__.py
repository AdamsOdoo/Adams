from . import shopify_connector_store_settings
from . import shopify_connector_location_mapping
from . import shopify_connector_inventory_product_binding
from . import shopify_connector_inventory_level_binding
from . import shopify_connector_inventory_service
# P07 reversible read call-site layer; imported after the unchanged service.
from . import shopify_connector_inventory_p07_read_adapter
# The typed gateway implementation belongs to inventory.  Register it after
# the call-site adapter while preserving core's optional-addon independence.
from . import shopify_connector_inventory_p07_gateway
# The guided setup's Location mapping seams. Imported AFTER the service,
# which they delegate to.
from . import shopify_connector_inventory_setup
