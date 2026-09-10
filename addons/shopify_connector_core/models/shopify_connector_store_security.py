"""Closed store create/write capabilities.

The legacy store model keeps its domain and lifecycle implementation compact;
this isolated inheritance supplies the server-side admission boundary.  The
object-identity sentinel is deliberately private to this module.
"""

from odoo import api, models
from odoo.exceptions import AccessError


# The form's ``readonly`` attribute is presentation only.  These columns are
# lifecycle, ownership, generation, or evidence state and therefore must not
# be writable through the ordinary ORM/RPC path, even when the caller has the
# Store Administrator ACL.  ``name`` is intentionally absent: it is the one
# operator-editable label on the store record.
STORE_PROTECTED_FIELDS = frozenset((
    'shop_domain',
    'state',
    'api_version',
    'api_health_state',
    'api_health_reason',
    'api_throttle_available',
    'api_throttle_maximum',
    'api_throttle_restore_rate',
    'api_throttle_observed_at',
    'webhook_ready',
    'last_test_connection_result',
    'last_test_connection_at',
    'last_test_connection_reason',
    'last_readiness_result',
    'last_readiness_at',
    'credential_present',
    'credential_last_verified_at',
    'credential_last_replaced_at',
    'credential_last_failure_reason',
    'granted_scopes',
    'granted_scopes_checked_at',
    'connection_generation',
    'disconnect_status',
    'disconnect_status_reason',
    'disconnect_open_lease_count',
    'disconnect_oldest_admitted_at',
    'disconnect_requested_at',
    'disconnect_requested_by',
    'disconnect_completed_at',
    'activation_state',
    'activation_changed_at',
    'activation_changed_by',
    'retire_requested_at',
    'retire_requested_by',
    'retire_reason',
    'company_id',
))

# A Python object identity, not a caller-controlled context value, opens this
# surface.  Odoo serializes RPC context values, so a remote caller cannot
# construct the sentinel.  ``env.su`` remains a deliberate compatibility
# escape for module init/migrations and the existing root cron/test harness;
# ordinary RPC users never run with ``su``.
STORE_WRITE_CONTEXT = 'shopify_store_write_surface'
STORE_SERVICE_SENTINEL_CONTEXT = 'shopify_store_service_sentinel'
STORE_SERVICE_SENTINEL = object()
STORE_WRITE_SURFACES = frozenset((
    '_company_assignment',
    '_credential',
    '_connection_probe',
    '_lifecycle',
    '_readiness',
    '_throttle',
))

# A store row is structural: the setup wizard may supply only the merchant's
# label/domain and the already-resolved owning company.  Lifecycle, API,
# readiness, credential, generation, and disconnect values must be defaults or
# service evidence, never create-time RPC inputs.  The explicit create surface
# is kept separate from the write surfaces so a setup caller cannot accidentally
# borrow a lifecycle capability merely by having created the row.
STORE_CREATE_CONTEXT = 'shopify_store_create_surface'
STORE_CREATE_SURFACES = frozenset(('_setup',))
STORE_INITIAL_CREATE_FIELDS = frozenset(('name', 'shop_domain', 'company_id'))


class ShopifyConnectorStoreSecurity(models.Model):
    _inherit = "shopify.connector.store"

    # The guarded create/write surface is kept in this small inheritance so
    # the legacy lifecycle model remains focused on domain behavior.
    @api.model
    def _assert_store_create_values(self, vals_list):
        """Refuse state injection into the one sanctioned initial shape."""
        supplied = set().union(*(set(vals) for vals in vals_list))
        unexpected = sorted(supplied - STORE_INITIAL_CREATE_FIELDS)
        if unexpected:
            raise AccessError(
                'A new Shopify store may be initialized only with its name, '
                'domain, and resolved company. Protected state must be '
                'established by the connector service. Fields: %s'
                % ', '.join(unexpected)
            )

    @api.model
    def _store_service_create(self, surface, vals):
        """Create one store through a named, private setup surface.

        The wizard resolves and validates the company before it elevates this
        call.  The opaque context value is still installed so the create seam
        remains explicit if a non-root service ever uses it; a remote caller
        cannot manufacture the object identity used by ``create``.
        """
        if surface not in STORE_CREATE_SURFACES:
            raise AccessError('Unknown Shopify store create surface.')
        self._assert_store_create_values([vals])
        return self.with_context(**{
            STORE_CREATE_CONTEXT: surface,
            STORE_SERVICE_SENTINEL_CONTEXT: STORE_SERVICE_SENTINEL,
        }).create(vals)

    @api.model
    def _store_create_surface_is_open(self):
        context = self.env.context
        return (
            context.get(STORE_SERVICE_SENTINEL_CONTEXT)
            is STORE_SERVICE_SENTINEL
            and context.get(STORE_CREATE_CONTEXT) in STORE_CREATE_SURFACES
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Admit only service-shaped non-root store creation.

        ``env.su`` is intentionally left compatible with module installation,
        migration scripts, and existing root fixtures.  Every ordinary ORM/RPC
        caller, even one granted a future create ACL, needs the private setup
        surface and cannot inject lifecycle/readiness/credential/generation or
        disconnect state.
        """
        if self.env.su:
            return super().create(vals_list)
        if not self._store_create_surface_is_open():
            raise AccessError(
                'Shopify stores can only be created by the connector setup '
                'service.'
            )
        self._assert_store_create_values(vals_list)
        return super().create(vals_list)

    def _store_service_write(self, surface, vals):
        """Write protected store state only from a named service surface.

        The method is private (and therefore not an RPC entry point), and the
        context it installs contains an opaque module-level object.  A string
        or boolean copied into an RPC context cannot satisfy the identity
        check in ``write``.  Keeping this helper on the store model also makes
        every internal writer auditable by surface name instead of spreading
        a caller-controlled bypass flag through the codebase.
        """
        if surface not in STORE_WRITE_SURFACES:
            raise AccessError('Unknown Shopify store write surface.')
        return self.with_context(**{
            STORE_WRITE_CONTEXT: surface,
            STORE_SERVICE_SENTINEL_CONTEXT: STORE_SERVICE_SENTINEL,
        }).write(vals)

    def _store_surface_is_open(self):
        context = self.env.context
        return (
            context.get(STORE_SERVICE_SENTINEL_CONTEXT)
            is STORE_SERVICE_SENTINEL
            and context.get(STORE_WRITE_CONTEXT) in STORE_WRITE_SURFACES
        )

    def write(self, vals):
        """Reject ordinary writes to lifecycle and ownership state.

        ``readonly`` fields are still writable through imports, RPC, and
        server-side ORM calls.  This guard is the server-side boundary.  Root
        services retain their existing migration/installer compatibility; all
        normal users must come through ``_store_service_write``.
        """
        protected = STORE_PROTECTED_FIELDS.intersection(vals)
        if (
            protected
            and not self.env.su
            and not self._store_surface_is_open()
        ):
            raise AccessError(
                'Lifecycle, ownership, generation, readiness, and disconnect '
                'state can only be changed by the connector service.'
            )
        return super().write(vals)
