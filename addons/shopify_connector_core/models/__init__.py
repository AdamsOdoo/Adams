# SEC-3 (#197): the scope mixin is imported FIRST, deliberately.
# Odoo builds a module's models in registration order, which is import
# order, and a model whose `_inherit` names a mixin that has not been
# registered yet fails the whole registry load. `shopify_connector_api_client`
# imports `shopify_connector_mutation_attempt` at module level, so the
# attempt model registers on the very first line below unless the mixin is
# already in place.
from . import shopify_connector_scope_mixin
from . import shopify_connector_api_client
# Claim-fenced P10 read admission extends the established transport boundary.
# It must load after the client owner and before any runtime can register a
# network-capable read handler.
from . import shopify_connector_api_client_v2_read_claim
# The final V2 admission hook is isolated from the protected API client.  It
# runs on the second validation call made inside `_send`, after
# `execute_business` has completed credential/access work and immediately
# before the base transport method constructs the HTTP request.
from . import shopify_connector_api_client_v2_runtime
# P06 read gateway adapter: explicit core/product/sale read methods over the
# existing authorized API client; no table, writes, or lifecycle transitions.
from . import shopify_connector_read_gateway
# P07 shared compatibility runtime.  Optional domain gateways register through
# inheritance in their owning addons; core imports no domain implementation.
from . import shopify_connector_domain_read_gateway
from . import shopify_connector_store
# Keep the legacy store lifecycle implementation compact.  The server-side
# create/write admission guard is a small inheritance loaded immediately
# after the base model, before credential/settings services call it.
from . import shopify_connector_store_security
from . import shopify_connector_store_credential
# Credential ORM projection guards and narrow private accessors live in a
# separate inheritance so the credential history model stays baseline-sized.
from . import shopify_connector_store_credential_security
from . import shopify_connector_store_access_token
from . import shopify_connector_store_settings
# Keep structural settings admission and service-only state writes in a small
# inheritance so the legacy settings model stays baseline-sized.
from . import shopify_connector_store_settings_security
from . import shopify_connector_store_settings_v2
from . import shopify_connector_command_result
from . import shopify_connector_pii_retention
from . import shopify_connector_location
from . import shopify_connector_binding_mixin
from . import shopify_connector_job
from . import shopify_connector_mutation_attempt
# Keep V2 attempt identity in an additive inheritance so the protected
# evidence model remains baseline-sized.
from . import shopify_connector_mutation_attempt_v2_runtime
from . import shopify_connector_mutation_attempt_retention
# P09 additive runtime evidence.  Run owns the request; execution attempt
# references the already-registered job, run, and mutation-attempt models.
from . import shopify_connector_run
from . import shopify_connector_job_runtime
from . import shopify_connector_job_attempt
from . import shopify_connector_job_actions
from . import shopify_connector_job_enqueue
from . import shopify_connector_call_lease
from . import shopify_connector_job_dispatch
# Shared V2 mutation admission is an inherited seam loaded after the
# protected dispatcher; domain addons extend its registries with super().
from . import shopify_connector_v2_mutation_dispatch
# Final legacy-claim fence resolves the composed V2 mutation registry without
# enlarging either protected V1 hotspot.
from . import shopify_connector_job_v2_claim_fence
from . import shopify_connector_stale_owner_sweep
# P10 bounded read-only repository/runtime adapter.  Imported after both
# target abstract services so its compatibility overrides register safely.
from . import shopify_connector_v2_runtime
from . import shopify_connector_job_log
from . import shopify_connector_readiness_check
# U0 operator UI foundation: read-only dashboard aggregate service + two
# transient input wizards (no new business logic, no new persistent table).
from . import shopify_connector_ui_dashboard
from . import shopify_connector_ui_health
# P02 V2 read-only DTO facade.  It is intentionally imported after the
# existing dashboard services so the legacy surface and its model inheritance
# remain unchanged while the new named RPC boundary becomes available.
from . import shopify_connector_ui_facade
# P01/P02 explicit application seam.  It delegates only named read methods to
# the UI facade; no generic dispatch or write command is exposed yet.
from . import shopify_connector_application_facade
# P15 command replay extends the application facade, so it must be registered
# after the facade owner.  Loading it with the command-result model above makes
# a fresh Odoo registry fail before any connector test or migration can run.
from . import shopify_connector_p15_command_replay
# P04 explicit recovery adapters.  The base attention command contract is
# registered first; retry and administrator cancellation extend the same named
# application facade without introducing a generic dispatcher.
from . import shopify_connector_recovery_commands
from . import shopify_connector_recovery_job
from . import shopify_connector_recovery_cancellation
from . import shopify_connector_recovery_replay
from . import shopify_connector_job_cancel_wizard
from . import shopify_connector_mutation_resolution_wizard
# S1 guided setup. Imported after the readiness registry it delegates to and
# after the store/settings models it writes through -- it owns no table and no
# business rule of its own.
from . import shopify_connector_setup_wizard
# P15 backend-only typed store administration, scoped commands, and capacity /
# generation fences.  No UI assets or manifest wiring are introduced here.
from . import shopify_connector_p15_admin
# P15 operation options/admission are kept separate from the legacy command
# file so the named-command module remains below the repository's source-size
# guard.  This extension is still backend-only and has no UI asset wiring.
from . import shopify_connector_p15_operations
from . import shopify_connector_p15_setup_commands
from . import shopify_connector_p15_lifecycle
