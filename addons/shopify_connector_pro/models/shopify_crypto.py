# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Credential encryption helpers using Fernet symmetric encryption.

The encryption key is derived from the Odoo database UUID
(``ir.config_parameter`` key ``database.uuid``) via PBKDF2-HMAC-SHA256.
This means:
- Each database has a unique encryption key (non-portable tokens).
- The key material already exists — no extra configuration needed.
- System-admin-only access to ``database.uuid`` matches the threat model.
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from odoo import api, models

_logger = logging.getLogger(__name__)

# Fixed salt — safe because the input (database.uuid) is already a
# high-entropy random UUID.  Changing this salt would invalidate every
# encrypted token in every database, so treat it as immutable.
_PBKDF2_SALT = b'shopify_connector_pro_v1'
_PBKDF2_ITERATIONS = 480_000  # OWASP 2023 recommendation for HMAC-SHA256


class ShopifyCrypto(models.AbstractModel):
    """Abstract model providing encrypt/decrypt helpers.

    Not stored in the database — just a service layer accessible via
    ``self.env['shopify.crypto']``.
    """
    _name = 'shopify.crypto'
    _description = 'Shopify Credential Encryption Service'

    # ------------------------------------------------------------------
    # Key derivation
    # ------------------------------------------------------------------

    @api.model
    def _get_fernet_key(self):
        """Derive a 32-byte URL-safe-base64-encoded Fernet key from database.uuid."""
        db_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        if not db_uuid:
            raise ValueError(
                "Cannot derive encryption key: 'database.uuid' is not set. "
                "This should never happen in a properly initialized Odoo database."
            )
        # PBKDF2 produces exactly 32 raw bytes → base64-encode for Fernet
        raw_key = hashlib.pbkdf2_hmac(
            'sha256',
            db_uuid.encode('utf-8'),
            _PBKDF2_SALT,
            _PBKDF2_ITERATIONS,
            dklen=32,
        )
        return base64.urlsafe_b64encode(raw_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @api.model
    def encrypt(self, plaintext):
        """Encrypt a plaintext string.  Returns a Fernet token (str).

        Returns ``False`` if *plaintext* is falsy (Odoo convention for
        empty Char fields).
        """
        if not plaintext:
            return False
        fernet = Fernet(self._get_fernet_key())
        return fernet.encrypt(plaintext.encode('utf-8')).decode('ascii')

    @api.model
    def decrypt(self, ciphertext):
        """Decrypt a Fernet token back to plaintext (str).

        Returns ``False`` if *ciphertext* is falsy.
        Raises ``ValueError`` if the token is corrupt or the key has changed.
        """
        if not ciphertext:
            return False
        fernet = Fernet(self._get_fernet_key())
        try:
            return fernet.decrypt(ciphertext.encode('ascii')).decode('utf-8')
        except InvalidToken:
            _logger.error(
                "Failed to decrypt credential — the database UUID may have "
                "changed or the stored value is corrupt."
            )
            raise ValueError(
                "Cannot decrypt Shopify credential. If you restored this "
                "database from a different instance, please re-enter your "
                "Shopify access token and webhook secret."
            )
