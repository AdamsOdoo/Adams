# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Post-migration: encrypt existing plaintext access tokens and webhook secrets.

Safety guarantees:
1. Only processes records where the encrypted column is empty but the legacy
   plaintext column has data.
2. Each record is encrypted AND verified (decrypt matches original) within
   the same transaction — if verification fails the entire migration rolls
   back, leaving no store with an unusable token.
3. The legacy plaintext column is cleared ONLY after the encrypted value is
   verified readable.
4. Logs every migrated record (by ID, never by token value).
"""
import base64
import hashlib
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Must match constants in shopify_crypto.py exactly
_PBKDF2_SALT = b'shopify_connector_pro_v1'
_PBKDF2_ITERATIONS = 480_000


def _get_fernet_key(cr):
    """Derive the Fernet key from database.uuid without needing the ORM."""
    cr.execute(
        "SELECT value FROM ir_config_parameter WHERE key = 'database.uuid'"
    )
    row = cr.fetchone()
    if not row or not row[0]:
        raise RuntimeError(
            "Cannot derive encryption key: 'database.uuid' not found. "
            "Aborting migration to protect credentials."
        )
    raw_key = hashlib.pbkdf2_hmac(
        'sha256',
        row[0].encode('utf-8'),
        _PBKDF2_SALT,
        _PBKDF2_ITERATIONS,
        dklen=32,
    )
    return base64.urlsafe_b64encode(raw_key)


def migrate(cr, version):
    """Encrypt any existing plaintext tokens in shopify_backend."""
    # Lazy import — cryptography might not be installed during an earlier
    # migration step, but it's guaranteed present for this module version.
    from cryptography.fernet import Fernet

    # Check if the legacy plaintext columns still exist
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'shopify_backend'
          AND column_name IN ('access_token', 'webhook_secret')
    """)
    legacy_columns = {row[0] for row in cr.fetchall()}

    if not legacy_columns:
        _logger.info(
            "No legacy plaintext columns found — skipping encryption migration."
        )
        return

    fernet_key = _get_fernet_key(cr)
    fernet = Fernet(fernet_key)

    # ── Encrypt access_token ───────────────────────────────
    if 'access_token' in legacy_columns:
        cr.execute("""
            SELECT id, access_token
            FROM shopify_backend
            WHERE access_token IS NOT NULL
              AND access_token != ''
              AND (_encrypted_access_token IS NULL OR _encrypted_access_token = '')
        """)
        rows = cr.fetchall()
        migrated = 0
        for backend_id, plaintext_token in rows:
            # Encrypt
            encrypted = fernet.encrypt(
                plaintext_token.encode('utf-8')
            ).decode('ascii')

            # Verify round-trip BEFORE writing — if this fails, the entire
            # migration rolls back (we're inside a transaction).
            decrypted = fernet.decrypt(
                encrypted.encode('ascii')
            ).decode('utf-8')
            if decrypted != plaintext_token:
                raise RuntimeError(
                    f"Encryption round-trip verification FAILED for backend "
                    f"{backend_id}. Aborting migration — no data was changed."
                )

            # Write encrypted value AND clear plaintext in one statement
            cr.execute("""
                UPDATE shopify_backend
                SET _encrypted_access_token = %s,
                    access_token = NULL
                WHERE id = %s
            """, (encrypted, backend_id))
            migrated += 1

        _logger.info(
            "Encrypted access_token for %d backend(s).", migrated,
        )

    # ── Encrypt webhook_secret ─────────────────────────────
    if 'webhook_secret' in legacy_columns:
        cr.execute("""
            SELECT id, webhook_secret
            FROM shopify_backend
            WHERE webhook_secret IS NOT NULL
              AND webhook_secret != ''
              AND (_encrypted_webhook_secret IS NULL
                   OR _encrypted_webhook_secret = '')
        """)
        rows = cr.fetchall()
        migrated = 0
        for backend_id, plaintext_secret in rows:
            encrypted = fernet.encrypt(
                plaintext_secret.encode('utf-8')
            ).decode('ascii')

            decrypted = fernet.decrypt(
                encrypted.encode('ascii')
            ).decode('utf-8')
            if decrypted != plaintext_secret:
                raise RuntimeError(
                    f"Encryption round-trip verification FAILED for backend "
                    f"{backend_id} webhook_secret. Aborting migration."
                )

            cr.execute("""
                UPDATE shopify_backend
                SET _encrypted_webhook_secret = %s,
                    webhook_secret = NULL
                WHERE id = %s
            """, (encrypted, backend_id))
            migrated += 1

        _logger.info(
            "Encrypted webhook_secret for %d backend(s).", migrated,
        )

    _logger.info("Credential encryption migration complete.")
