# SEC-3 (#197): the scope mixin is imported FIRST, deliberately.
# Odoo builds a module's models in registration order, which is import
# order, and a model whose `_inherit` names a mixin that has not been
# registered yet fails the whole registry load. `shopify_connector_api_client`
# imports `shopify_connector_mutation_attempt` at module level, so the
# attempt model registers on the very first line below unless the mixin is
# already in place.
from . import shopify_connector_scope_mixin
from . import shopify_connector_api_client
from . import shopify_connector_store
from . import shopify_connector_store_credential
from . import shopify_connector_store_settings
from . import shopify_connector_pii_retention
from . import shopify_connector_location
from . import shopify_connector_binding_mixin
from . import shopify_connector_job
from . import shopify_connector_mutation_attempt
from . import shopify_connector_job_actions
from . import shopify_connector_job_enqueue
from . import shopify_connector_call_lease
from . import shopify_connector_job_dispatch
from . import shopify_connector_stale_owner_sweep
from . import shopify_connector_job_log
from . import shopify_connector_readiness_check
# U0 operator UI foundation: read-only dashboard aggregate service + two
# transient input wizards (no new business logic, no new persistent table).
from . import shopify_connector_ui_dashboard
from . import shopify_connector_job_cancel_wizard
from . import shopify_connector_mutation_resolution_wizard
# S1 guided setup. Imported after the readiness registry it delegates to and
# after the store/settings models it writes through -- it owns no table and no
# business rule of its own.
from . import shopify_connector_setup_wizard
