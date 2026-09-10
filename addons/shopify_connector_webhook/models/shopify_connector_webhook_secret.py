"""Store-scoped callback token and narrow HMAC-secret access helpers."""

import hashlib
import secrets
from urllib.parse import quote

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from psycopg2 import IntegrityError

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)


_SECRET_SERVICE_CONTEXT = 'shopify_connector_webhook_secret_service'
_SECRET_SERVICE_SENTINEL = object()


def callback_token_digest(token):
    """Return the non-reversible lookup digest for a callback token."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class ShopifyConnectorWebhookSecret(models.Model):
    """One unguessable callback token per store.

    The token is stored behind ``base.group_no_one`` because the public route
    needs to resolve it while ordinary connector users must never read it.
    This is access control, not encryption-at-rest; the token is never logged,
    returned by a public method, or placed in a delivery record.
    """

    _name = 'shopify.connector.webhook.secret'
    _description = 'Shopify Connector Webhook Callback Secret'

    store_id = fields.Many2one(
        'shopify.connector.store', required=True, index=True, readonly=True,
        ondelete='restrict',
    )
    company_id = fields.Many2one(
        'res.company', related='store_id.company_id', store=True, index=True,
        readonly=True,
    )
    # No RPC-visible group can read this field.  The route uses the exact
    # narrow sudo accessor below after resolving the store by token digest.
    callback_token = fields.Char(
        required=True, copy=False, readonly=True, groups='base.group_no_one',
    )
    token_digest = fields.Char(required=True, index=True, readonly=True)
    active = fields.Boolean(default=True, readonly=True)
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    _store_unique = models.Constraint(
        'UNIQUE(store_id)',
        'A Shopify store may have only one active webhook callback token.',
    )
    _digest_unique = models.Constraint(
        'UNIQUE(token_digest)',
        'Webhook callback tokens must be unique.',
    )

    @api.model
    def _service_context(self):
        return {
            _SECRET_SERVICE_CONTEXT: _SECRET_SERVICE_SENTINEL,
        }

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(_SECRET_SERVICE_CONTEXT)
            is not _SECRET_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Webhook callback secrets can only be created by the '
                'connector webhook service.'
            )
        return super().create(vals_list)

    def write(self, vals):
        if (
            not self.env.su
            or self.env.context.get(_SECRET_SERVICE_CONTEXT)
            is not _SECRET_SERVICE_SENTINEL
        ):
            raise AccessError(
                'Webhook callback secrets are immutable; callback-token '
                'rotation is disabled until an overlap and remote migration '
                'protocol is installed.'
            )
        return super().write(vals)

    def unlink(self):
        raise AccessError(
            'Webhook callback secrets are retained; rotation is not enabled '
            'by this foundation.'
        )

    @api.model
    def _ensure_for_store(self, store):
        """Create or return the one callback token for ``store``.

        The returned record remains an internal service object.  Callers must
        not serialize ``callback_token`` into views, jobs, logs, or responses.
        The unique constraint handles two concurrent onboarding/reconcile
        workers; the loser reloads the committed row after its savepoint.
        """
        store.ensure_one()
        Secret = self.sudo()
        existing = Secret.search([('store_id', '=', store.id)], limit=1)
        if existing:
            return existing
        token = secrets.token_urlsafe(32)
        values = {
            'store_id': store.id,
            'callback_token': token,
            'token_digest': callback_token_digest(token),
        }
        try:
            with self.env.cr.savepoint():
                return Secret.with_context(**self._service_context()).create(
                    values
                )
        except IntegrityError:
            existing = Secret.search([('store_id', '=', store.id)], limit=1)
            if existing:
                return existing
            raise

    @api.model
    def _find_by_token_digest(self, digest):
        if not isinstance(digest, str) or len(digest) != 64:
            return self.browse()
        return self.sudo().search([
            ('token_digest', '=', digest),
            ('active', '=', True),
        ], limit=1)

    @api.model
    def _client_secret_for_store(self, store):
        """Read only the HMAC secret for one already-resolved store.

        This is the sole route-ingestion secret read.  It is deliberately
        private, store-scoped, and returns the value only to the in-process
        HMAC comparison; it never enters an ORM record, log, exception, or
        HTTP response.
        """
        store.ensure_one()
        return self.env[
            'shopify.connector.store.credential'
        ]._get_client_secret(store)

    @api.model
    def _client_secrets_for_store(self, store):
        """Return current then unexpired previous app secret for HMAC only."""
        return self.env[
            'shopify.connector.store.credential'
        ]._hmac_secrets_for_store(store)

    @api.model
    def _callback_url_for_store(self, store):
        """Build the versioned HTTPS callback URL without exposing it.

        The URL is consumed only by the Shopify subscription mutation.  The
        secret path segment is never persisted in a subscription row or
        returned through an operator action.
        """
        store.ensure_one()
        secret = self._ensure_for_store(store)
        base_url = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url',
        )
        if not isinstance(base_url, str) or not base_url.startswith('https://'):
            raise ValidationError(
                'Webhook subscriptions require an HTTPS web.base.url.'
            )
        token = quote(secret.callback_token, safe='')
        return (
            '%s/shopify/webhook/%s/%s' % (
                base_url.rstrip('/'), token, SHOPIFY_API_VERSION,
            )
        )

    @api.model
    def _callback_url_digest_for_store(self, store):
        url = self._callback_url_for_store(store)
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    @api.model
    def _callback_path_label(self):
        """A non-secret operator label suitable for views and diagnostics."""
        return '/shopify/webhook/<store-callback-token>/%s' % (
            SHOPIFY_API_VERSION,
        )
