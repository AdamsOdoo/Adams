"""Closed store-settings create/write capabilities.

The legacy settings model retains its configuration and readiness projection;
this isolated inheritance owns structural-row admission and service-only state
writes.  The object-identity sentinel remains private to this module.
"""

from odoo import api, models
from odoo.exceptions import AccessError


# Settings rows carry both merchant configuration and connector-owned state.
# ``readonly`` only affects the form client, so the structural/setup fields and
# fulfillment state below need a server-side write boundary as well.  Ordinary
# domain flags remain editable on the canonical settings surface; the fields in
# this set are either identity pointers, durable wizard/readiness state, or
# state-machine evidence owned by a service.
SETTINGS_PROTECTED_FIELDS = frozenset((
    'store_id',
    'company_id',
    'sec3_scope_quarantined',
    'setup_wizard_step_key',
    'setup_wizard_step',
    'setup_readiness_stale_since',
    'setup_completed_at',
    'setup_completed_uid',
    'setup_last_rerun_at',
    'setup_last_rerun_uid',
    'setup_step_payloads',
    'notification_default_enabled',
    # Fulfillment mode/switch, notification consent, and durable scan state.
    'fulfillment_operating_mode',
    'fulfillment_switch_in_progress',
    'fulfillment_mode_switch_nonce',
    'fulfillment_requested_mode',
    'fulfillment_mode_switch_state',
    'fulfillment_mode_switch_job_id',
    'fulfillment_mode_switch_failure_reason',
    'fulfillment_mode_switch_next_action',
    'fulfillment_mode_switch_next_retry_at',
    'fulfillment_mode_switch_is_stale',
    'fulfillment_mode_switch_verified_at',
    'fulfillment_last_mode_switch_at',
    'fulfillment_last_mode_switch_uid',
    'fulfillment_notification_confirmed',
    'fulfillment_last_reconciliation_at',
    'fulfillment_reconciliation_cursor_id',
    'fulfillment_reconciliation_generation',
    'fulfillment_reconciliation_observed_through_at',
    'fulfillment_catchup_pending_generation',
    'fulfillment_catchup_pending_observed_through_at',
    'fulfillment_catchup_pending_job_id',
    'fulfillment_catchup_generation',
    'fulfillment_catchup_observed_through_at',
))

# As with the store and credential models, the capability is a Python object
# identity.  A JSON/RPC caller can copy the context key and name but cannot
# manufacture this sentinel.  ``env.su`` is retained for module init,
# migrations, and existing root cron/test fixtures.
SETTINGS_WRITE_CONTEXT = 'shopify_settings_write_surface'
SETTINGS_SERVICE_SENTINEL_CONTEXT = 'shopify_settings_service_sentinel'
SETTINGS_SERVICE_SENTINEL = object()
SETTINGS_WRITE_SURFACES = frozenset((
    '_fulfillment_job',
    '_fulfillment_mode_switch',
    '_fulfillment_scan',
    '_fulfillment_system',
    '_readiness',
    '_setup',
))

# Settings rows are structural and one-per-store.  Only the owning store link
# is an initial value; all stored state (including fulfillment mode/switch
# evidence and setup progress) is defaulted or written by a named service.
SETTINGS_CREATE_CONTEXT = 'shopify_settings_create_surface'
SETTINGS_CREATE_SURFACES = frozenset(('_setup', '_canonical_settings'))
SETTINGS_INITIAL_CREATE_FIELDS = frozenset(('store_id',))


class ShopifyConnectorStoreSettingsSecurity(models.Model):
    _inherit = "shopify.connector.store.settings"

    @api.model
    def _additional_protected_settings_fields(self):
        """Return protected settings fields owned by an addon.

        The core set above remains the complete core contract.  Domain addons
        extend it through this small inheritance hook rather than having to
        edit (or duplicate) the core security boundary.
        """
        return frozenset()

    @api.model
    def _settings_protected_fields(self):
        """Return the core protected fields plus addon-owned fields."""
        return (
            SETTINGS_PROTECTED_FIELDS
            | self._additional_protected_settings_fields()
        )

    @api.model
    def _additional_settings_write_surfaces(self):
        """Return named protected-write surfaces owned by an addon."""
        return frozenset()

    @api.model
    def _settings_write_surfaces(self):
        """Return the core write surfaces plus addon-owned surfaces."""
        return SETTINGS_WRITE_SURFACES | self._additional_settings_write_surfaces()

    # ------------------------------------------------------------------
    # Closed service write surface
    # ------------------------------------------------------------------

    @api.model
    def _assert_settings_create_values(self, vals_list):
        """Refuse state injection into a newly-created settings row."""
        supplied = set().union(*(set(vals) for vals in vals_list))
        unexpected = sorted(supplied - SETTINGS_INITIAL_CREATE_FIELDS)
        if unexpected:
            raise AccessError(
                'A new store-settings row may contain only its owning store. '
                'Setup, readiness, and fulfillment state belong to the '
                'connector service. Fields: %s' % ', '.join(unexpected)
            )

    @api.model
    def _settings_service_create(self, surface, vals):
        """Create one structural row through a named private service seam."""
        if surface not in SETTINGS_CREATE_SURFACES:
            raise AccessError('Unknown Shopify settings create surface.')
        self._assert_settings_create_values([vals])
        return self.with_context(**{
            SETTINGS_CREATE_CONTEXT: surface,
            SETTINGS_SERVICE_SENTINEL_CONTEXT: SETTINGS_SERVICE_SENTINEL,
        }).create(vals)

    @api.model
    def _settings_create_surface_is_open(self):
        context = self.env.context
        return (
            context.get(SETTINGS_SERVICE_SENTINEL_CONTEXT)
            is SETTINGS_SERVICE_SENTINEL
            and context.get(SETTINGS_CREATE_CONTEXT)
            in SETTINGS_CREATE_SURFACES
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Admit only service-shaped non-root settings creation.

        Root remains compatible with module initialization, migrations, and
        existing fixtures.  A normal RPC/ORM caller, including an Administrator
        with a future create ACL, cannot create a duplicate row or seed any
        setup/readiness/fulfillment state directly.
        """
        if self.env.su:
            return super().create(vals_list)
        if not self._settings_create_surface_is_open():
            raise AccessError(
                'Store settings rows can only be created by the connector '
                'setup service.'
            )
        self._assert_settings_create_values(vals_list)
        return super().create(vals_list)

    def _settings_service_write(self, surface, vals):
        """Write service-owned settings state through a named capability.

        This private method is the only normal-user escape from the direct
        ``write`` guard.  It installs an opaque sentinel by object identity,
        not a caller-controlled boolean/string flag, and validates the surface
        name before doing any write.
        """
        if surface not in self._settings_write_surfaces():
            raise AccessError('Unknown Shopify settings write surface.')
        return self.with_context(**{
            SETTINGS_WRITE_CONTEXT: surface,
            SETTINGS_SERVICE_SENTINEL_CONTEXT: SETTINGS_SERVICE_SENTINEL,
        }).write(vals)

    def _settings_surface_is_open(self):
        context = self.env.context
        return (
            context.get(SETTINGS_SERVICE_SENTINEL_CONTEXT)
            is SETTINGS_SERVICE_SENTINEL
            and context.get(SETTINGS_WRITE_CONTEXT)
            in self._settings_write_surfaces()
        )

    def write(self, vals):
        """Reject direct mutation of settings identity and safety state."""
        protected = self._settings_protected_fields().intersection(vals)
        if (
            protected
            and not self.env.su
            and not self._settings_surface_is_open()
        ):
            raise AccessError(
                'Store identity, setup/readiness state, and fulfillment '
                'switch state can only be changed by the connector service.'
            )
        return super().write(vals)
