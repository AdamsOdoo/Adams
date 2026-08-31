"""Webhook HMAC grace for sanctioned Shopify credential replacement."""

from odoo import api, fields, models


# Shopify documents a rotation overlap of up to one hour. Two hours is the
# conservative connector window: it covers that documented delivery window
# plus clock/queue skew, while the exact expiry remains durable and observable.
WEBHOOK_CLIENT_SECRET_GRACE_HOURS = 2


class ShopifyConnectorWebhookCredential(models.Model):
    """Keep one short-lived previous app secret without widening RPC access."""

    _inherit = 'shopify.connector.store.credential'

    webhook_previous_client_secret = fields.Char(
        copy=False,
        readonly=True,
        groups='base.group_no_one',
    )
    webhook_previous_client_secret_expires_at = fields.Datetime(
        copy=False,
        readonly=True,
        index=True,
        groups='base.group_no_one',
    )

    @api.model
    def _current_client_secret_locked(self, store):
        """Read the predecessor under the core store lifecycle lock."""
        # The core mutation service takes this same store -> credential lock
        # order. Holding the store row before reading the old value makes the
        # captured secret the immediate predecessor of this mutation; a
        # concurrent replacement cannot slip between the read and super().
        store._lock_store_for_lifecycle()
        return self._get_client_secret(store)

    @api.model
    def _record_client_secret_transition(
        self, store, previous_secret, current_secret,
    ):
        """Persist the previous secret only after a core-sanctioned mutation.

        The field is `base.group_no_one` and the write is a narrowly scoped
        superuser service write because ordinary Administrators must not gain
        RPC read access to a second secret. The caller has already completed
        the core store->credential lifecycle mutation; this extension writes
        only its own grace evidence in the same transaction.
        """
        credential = self.sudo().search([
            ('store_id', '=', store.id),
        ], limit=1)
        if not credential:
            return False
        # A grace window is only a replacement overlap. Clearing or switching
        # away from app credentials must revoke the old secret immediately.
        rotated = bool(
            previous_secret and current_secret
            and previous_secret != current_secret
        )
        values = {
            'webhook_previous_client_secret':
                previous_secret if rotated else False,
            'webhook_previous_client_secret_expires_at': (
                fields.Datetime.add(
                    fields.Datetime.now(),
                    hours=WEBHOOK_CLIENT_SECRET_GRACE_HOURS,
                ) if rotated else False
            ),
        }
        # `_mutate_token` is the core closed write surface. `sudo()` is exact
        # and field-scoped here solely because base.group_no_one deliberately
        # hides this secret from every ordinary RPC actor.
        self.sudo()._credential_surface('_mutate_token').browse(
            credential.id,
        ).write(values)
        return rotated

    @api.model
    def _hmac_secrets_for_store(self, store):
        """Return current then unexpired previous secret for local HMAC only."""
        credential = self.sudo().search([
            ('store_id', '=', store.id),
        ], limit=1)
        if not credential:
            return ()
        secrets = []
        current_secret = self._get_client_secret(store)
        if current_secret:
            secrets.append(current_secret)
        if (
            credential.webhook_previous_client_secret
            and credential.webhook_previous_client_secret_expires_at
            and credential.webhook_previous_client_secret_expires_at
            > fields.Datetime.now()
        ):
            secrets.append(credential.webhook_previous_client_secret)
        return tuple(secrets)

    @api.model
    def _hmac_rotation_pending(self, store):
        credential = self.sudo().search([
            ('store_id', '=', store.id),
        ], limit=1)
        return bool(
            credential
            and credential.webhook_previous_client_secret
            and credential.webhook_previous_client_secret_expires_at
            and credential.webhook_previous_client_secret_expires_at
            > fields.Datetime.now()
        )

    @api.model
    def action_set_client_credentials(self, store, client_id, client_secret):
        previous = self._current_client_secret_locked(store)
        result = super().action_set_client_credentials(
            store, client_id, client_secret,
        )
        self._record_client_secret_transition(
            store, previous, client_secret.strip(),
        )
        return result

    @api.model
    def action_set_token(self, store, value):
        previous = self._current_client_secret_locked(store)
        result = super().action_set_token(store, value)
        self._record_client_secret_transition(store, previous, False)
        return result

    @api.model
    def action_replace_token(self, store, value):
        previous = self._current_client_secret_locked(store)
        result = super().action_replace_token(store, value)
        self._record_client_secret_transition(store, previous, False)
        return result

    @api.model
    def _clear_token_under_store_lock(self, store):
        previous = self._current_client_secret_locked(store)
        result = super()._clear_token_under_store_lock(store)
        self._record_client_secret_transition(store, previous, False)
        return result
