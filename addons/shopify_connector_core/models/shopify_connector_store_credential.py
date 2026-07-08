from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ShopifyConnectorStoreCredential(models.Model):
    """Admin-only Shopify Admin API credential for one store (Task 002).

    Access is default-deny: only `group_shopify_connector_admin` has an
    ACL row on this model -- auditor/operator/reviewer have no row at
    all (deliberate, not an omission), and `access_token` additionally
    carries its own field-level `groups=` as a second, independent
    layer.

    `access_token` is stored plain behind that access control -- it is
    **not encrypted**. It remains readable to any `sudo()`-context code
    path, to direct database access, and to database backups. This is
    the honest residual accepted via AR-022/AR-024/AR-025: masking and
    access control are real protections, encryption-at-rest is not one
    of them here, and no part of this module may claim otherwise.

    `client_id`, `client_secret`, a token cache, and an expiry field are
    deliberately absent: Task 002 supports exactly one credential shape
    (`token_variant='offline_custom_app'`, a single long-lived value).
    This model is the seam a future, separately gated task can extend
    (via `selection_add` plus new fields) once ChatGPT decides the
    MBQ-05 acquisition-path direction -- no migration of this shape is
    required to do so.

    The only sanctioned `sudo()` in this module is inside
    `_get_access_token`, scoped to the one store already being operated
    on (DEC-004).
    """

    _name = 'shopify.connector.store.credential'
    _description = 'Shopify Connector Store Credential'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    access_token = fields.Char(
        copy=False,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    token_variant = fields.Selection(
        selection=[('offline_custom_app', 'Offline Custom App Token')],
        default='offline_custom_app',
    )
    credential_state = fields.Selection(
        selection=[
            ('absent', 'Absent'),
            ('present', 'Present'),
            ('invalid', 'Invalid'),
        ],
        required=True,
        default='absent',
        readonly=True,
    )

    _store_id_uniq = models.Constraint(
        'UNIQUE(store_id)',
        'Only one credential record is allowed per store.',
    )

    @api.model
    def action_set_token(self, store, value):
        """Create-or-update the store's credential value.

        Runs as the calling user (no `sudo()`) so the ACL layer stays
        live: a non-admin caller fails with `AccessError` from the ORM
        itself. Any set/update -- including overwriting an *existing*
        credential row (e.g. re-entering/correcting a token) -- clears
        `credential_last_verified_at`: a token change invalidates
        whatever verification was recorded for the value it replaced,
        closing the Task 005 stale-evidence path at the source instead
        of relying on the credential row's own `write_date` as a
        freshness signal.
        """
        if not isinstance(value, str) or not value:
            raise ValidationError(
                "A non-empty credential value is required."
            )
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if credential:
            credential.write({
                'access_token': value,
                'credential_state': 'present',
            })
        else:
            credential = self.create({
                'store_id': store.id,
                'access_token': value,
                'credential_state': 'present',
            })
        store.write({
            'credential_present': True,
            'credential_last_verified_at': False,
        })
        return None

    @api.model
    def action_replace_token(self, store, value):
        """Replace the store's credential value and reset verification.

        Stamps `credential_last_replaced_at`; does not touch
        `last_test_connection_*` (Task 003 owns those).
        """
        if not isinstance(value, str) or not value:
            raise ValidationError(
                "A non-empty credential value is required."
            )
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if credential:
            credential.write({
                'access_token': value,
                'credential_state': 'present',
            })
        else:
            credential = self.create({
                'store_id': store.id,
                'access_token': value,
                'credential_state': 'present',
            })
        store.write({
            'credential_present': True,
            'credential_last_replaced_at': fields.Datetime.now(),
            'credential_last_verified_at': False,
        })
        return None

    @api.model
    def action_clear_token(self, store):
        """Empty the store's credential value, preserving history.

        Idempotent when no credential row exists yet: no error, no row
        created. The credential row itself and
        `credential_last_replaced_at` are never removed (MBQ-08).
        """
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if credential:
            credential.write({
                'access_token': False,
                'credential_state': 'absent',
            })
        store.write({
            'credential_present': False,
            'credential_last_verified_at': False,
            'credential_last_failure_reason': False,
        })
        return None

    @api.model
    def _get_access_token(self, store):
        """Internal-only accessor for the store's stored credential value.

        The only sanctioned `sudo()` in this module: scoped to reading
        the single credential row of `store`, for a caller already
        authorized to act on that store (DEC-004 -- this elevation
        never crosses store/record-rule boundaries). Never returns the
        value to logs or exceptions; never invoked by any Task 002
        shipped code path outside tests (its consumer is the future API
        client).
        """
        credential = self.sudo().search(
            [('store_id', '=', store.id)], limit=1
        )
        return credential.access_token if credential else False
