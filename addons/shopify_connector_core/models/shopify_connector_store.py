import json
import uuid

from odoo import fields, models
from odoo.exceptions import UserError

from ..tools.redaction import redact
from .shopify_connector_api_client import ShopifyClientError

# The read-only test-connection query (Task 003) -- confirmed in the
# 2026-07 official reference (Facts #7/#8,
# credential-connection-api-client-planning.md); no mutation, no
# variables needed.
TEST_CONNECTION_QUERY = """
query ConnectorTestConnection {
  shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } }
}
"""


class ShopifyConnectorStore(models.Model):
    """The DEC-006 store-scoping anchor every other core model references.

    Holds connection lifecycle, API version/health, and readiness
    metadata, plus non-secret credential status mirrors only. This
    model stores no secret value itself: the credential presence flag,
    replacement/verification timestamps, failure reason, and
    granted-scope snapshot below are all non-secret status mirrors,
    written only by the credential service (Task 002). The actual
    secret credential value is persisted exclusively on the dedicated
    Admin-only `shopify.connector.store.credential` model.
    """

    _name = 'shopify.connector.store'
    _description = 'Shopify Connector Store'

    name = fields.Char(required=True)
    shop_domain = fields.Char(required=True, index=True, readonly=True)
    state = fields.Selection(
        selection=[
            ('setup_incomplete', 'Setup Incomplete'),
            ('connected', 'Connected'),
            ('reconnect_needed', 'Reconnect Needed'),
            ('disconnected', 'Disconnected'),
        ],
        required=True,
        index=True,
        default='setup_incomplete',
        readonly=True,
    )
    api_version = fields.Char(required=True)
    api_health_state = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('throttled', 'Throttled'),
            ('degraded', 'Degraded'),
        ],
        readonly=True,
    )
    api_health_reason = fields.Char(readonly=True)
    webhook_ready = fields.Boolean(default=False, readonly=True)
    last_test_connection_result = fields.Selection(
        selection=[('pass', 'Pass'), ('fail', 'Fail')],
        readonly=True,
    )
    last_test_connection_at = fields.Datetime(readonly=True)
    last_test_connection_reason = fields.Char(readonly=True)
    last_readiness_result = fields.Selection(
        selection=[('pass', 'Pass'), ('fail', 'Fail'), ('warning', 'Warning')],
        readonly=True,
    )
    last_readiness_at = fields.Datetime(readonly=True)
    credential_present = fields.Boolean(default=False, readonly=True)
    credential_last_verified_at = fields.Datetime(readonly=True)
    credential_last_replaced_at = fields.Datetime(readonly=True)
    credential_last_failure_reason = fields.Char(readonly=True)
    granted_scopes = fields.Text(readonly=True)
    granted_scopes_checked_at = fields.Datetime(readonly=True)

    _sql_constraints = [
        (
            'shop_domain_uniq',
            'unique(shop_domain)',
            'A store already exists for this Shopify shop domain.',
        ),
    ]

    def action_test_connection(self):
        """Run one read-only Shopify test-connection check (Task 003).

        Admin-invoked (store write access is Admin-only per the merged
        ACL, so this is enforced by the existing ACL, not a new guard).
        Creates exactly one `job_type='core_test_connection'` job per
        run, with a fresh UUID4 `payload_hash` nonce so repeat runs never
        collide on `store_idempotency_key_uniq` --
        `core_readiness_check`'s identical latent exposure is untouched
        (TD-001). Writes only the store mirrors, the credential's
        `credential_state` (only for a genuine token-invalid signal), and
        the job/job.log rows -- never the token, never a raw response
        body outside the client's already-redacted `technical_detail`.
        """
        self.ensure_one()
        if not self.credential_present:
            raise UserError(
                'Enter a credential before testing the connection.'
            )
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job = Job.create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', 'Test connection attempt started.',
        )

        try:
            result = self.env['shopify.connector.api.client'].execute(
                self, TEST_CONNECTION_QUERY
            )
        except ShopifyClientError as exc:
            self.write({
                'last_test_connection_result': 'fail',
                'last_test_connection_at': fields.Datetime.now(),
                'last_test_connection_reason': redact(exc.reason),
            })
            if exc.credential_invalid:
                credential = self.env[
                    'shopify.connector.store.credential'
                ].search([('store_id', '=', self.id)], limit=1)
                if credential:
                    credential.write({'credential_state': 'invalid'})
            job.write({
                'error_class': exc.error_class,
                'state': 'failed_final',
                'finished_at': fields.Datetime.now(),
            })
            JobLog._system_append(
                job, 'attempt', redact(exc.reason),
                technical_detail=exc.technical_detail,
                from_state='running', to_state='failed_final',
            )
            return None

        data = result.get('data') or {}
        shop = data.get('shop') or {}
        if shop.get('myshopifyDomain') != self.shop_domain:
            reason = (
                "The connected Shopify store does not match this "
                "store's configured domain — check the domain and "
                "reconnect."
            )
            self.write({
                'last_test_connection_result': 'fail',
                'last_test_connection_at': fields.Datetime.now(),
                'last_test_connection_reason': redact(reason),
            })
            job.write({
                'error_class': 'odoo_validation_configuration',
                'state': 'failed_final',
                'finished_at': fields.Datetime.now(),
            })
            JobLog._system_append(
                job, 'attempt', redact(reason),
                from_state='running', to_state='failed_final',
            )
            return None

        access_scopes = (
            data.get('currentAppInstallation') or {}
        ).get('accessScopes') or []
        self.write({
            'last_test_connection_result': 'pass',
            'last_test_connection_at': fields.Datetime.now(),
            'last_test_connection_reason': False,
            'credential_last_verified_at': fields.Datetime.now(),
            'granted_scopes': json.dumps(
                [scope['handle'] for scope in access_scopes]
            ),
            'granted_scopes_checked_at': fields.Datetime.now(),
        })
        if result.get('version_fallforward'):
            self.write({
                'api_health_state': 'degraded',
                'api_health_reason': redact(
                    'Shopify served API version %s instead of the '
                    'configured %s.' % (
                        result.get('served_version'), self.api_version,
                    )
                ),
            })
        job.write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt',
            'Connection verified with %s.' % shop.get('name'),
            from_state='running', to_state='succeeded',
        )
        return None
