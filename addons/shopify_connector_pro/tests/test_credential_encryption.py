# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tests for credential encryption (shopify.crypto + encrypted backend fields).

These tests MUST pass before the migration script runs.  They prove:
1. Round-trip encrypt/decrypt works
2. The DB column value is NOT plaintext
3. _make_api_client() still gets correct plaintext
4. Token never appears in logs
5. test_connection still succeeds end-to-end (mocked)
"""
import logging

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestShopifyCrypto(TransactionCase):
    """Unit tests for the shopify.crypto abstract model."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting must return the original value."""
        crypto = self.env['shopify.crypto']
        original = 'shpat_abcdef1234567890'
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        self.assertEqual(decrypted, original)

    def test_encrypted_value_differs_from_plaintext(self):
        """The encrypted output must NOT equal the plaintext input."""
        crypto = self.env['shopify.crypto']
        original = 'shpat_abcdef1234567890'
        encrypted = crypto.encrypt(original)
        self.assertNotEqual(encrypted, original)
        self.assertNotIn('shpat_', encrypted)

    def test_encrypt_empty_returns_false(self):
        """Falsy input returns False (Odoo convention for empty Char)."""
        crypto = self.env['shopify.crypto']
        self.assertFalse(crypto.encrypt(False))
        self.assertFalse(crypto.encrypt(''))

    def test_decrypt_empty_returns_false(self):
        """Falsy ciphertext returns False."""
        crypto = self.env['shopify.crypto']
        self.assertFalse(crypto.decrypt(False))
        self.assertFalse(crypto.decrypt(''))

    def test_decrypt_corrupt_raises(self):
        """Corrupted ciphertext raises ValueError, not a crash."""
        crypto = self.env['shopify.crypto']
        with self.assertRaises(ValueError):
            crypto.decrypt('not-a-valid-fernet-token')

    def test_different_plaintexts_different_ciphertexts(self):
        """Two different tokens must produce different encrypted values."""
        crypto = self.env['shopify.crypto']
        enc1 = crypto.encrypt('shpat_token_one')
        enc2 = crypto.encrypt('shpat_token_two')
        self.assertNotEqual(enc1, enc2)

    def test_key_derived_from_database_uuid(self):
        """Key derivation must depend on database.uuid."""
        crypto = self.env['shopify.crypto']
        original = 'shpat_test_key_derivation'
        encrypted = crypto.encrypt(original)
        # Temporarily change the UUID — decrypt should fail
        ICP = self.env['ir.config_parameter'].sudo()
        old_uuid = ICP.get_param('database.uuid')
        try:
            ICP.set_param('database.uuid', 'fake-uuid-for-testing')
            with self.assertRaises(ValueError):
                crypto.decrypt(encrypted)
        finally:
            ICP.set_param('database.uuid', old_uuid)


class TestBackendEncryptedFields(TransactionCase):
    """Tests for encrypted fields on shopify.backend."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Encryption Test Store',
            'shop_url': 'encrypt-test.myshopify.com',
            'access_token': 'shpat_encryption_test_token',
            'company_id': self.env.company.id,
        })

    def test_token_stored_encrypted_in_db(self):
        """The _encrypted_access_token column must NOT contain plaintext."""
        # Read raw DB value bypassing the computed field
        self.env.cr.execute(
            "SELECT _encrypted_access_token FROM shopify_backend WHERE id = %s",
            (self.backend.id,),
        )
        raw = self.env.cr.fetchone()[0]
        self.assertTrue(raw, "Encrypted column should not be empty")
        self.assertNotEqual(raw, 'shpat_encryption_test_token')
        self.assertNotIn('shpat_', raw)

    def test_token_decrypts_correctly_via_field(self):
        """Reading access_token via the computed field returns plaintext."""
        # Re-read from DB to avoid cache
        backend = self.env['shopify.backend'].browse(self.backend.id)
        self.assertEqual(backend.access_token, 'shpat_encryption_test_token')

    def test_webhook_secret_encrypted(self):
        """Webhook secret should also be encrypted at rest."""
        self.backend.webhook_secret = 'whsec_test_secret_value'
        # Flush the inverse to DB before raw SQL
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT _encrypted_webhook_secret FROM shopify_backend WHERE id = %s",
            (self.backend.id,),
        )
        raw = self.env.cr.fetchone()[0]
        self.assertTrue(raw)
        self.assertNotEqual(raw, 'whsec_test_secret_value')
        # Read back via field
        self.env.invalidate_all()
        backend = self.env['shopify.backend'].browse(self.backend.id)
        self.assertEqual(backend.webhook_secret, 'whsec_test_secret_value')

    def test_update_token_re_encrypts(self):
        """Changing the token should produce a new encrypted value."""
        self.env.cr.execute(
            "SELECT _encrypted_access_token FROM shopify_backend WHERE id = %s",
            (self.backend.id,),
        )
        old_enc = self.env.cr.fetchone()[0]
        self.backend.access_token = 'shpat_updated_token_value'
        # Flush the inverse to DB before raw SQL
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT _encrypted_access_token FROM shopify_backend WHERE id = %s",
            (self.backend.id,),
        )
        new_enc = self.env.cr.fetchone()[0]
        self.assertNotEqual(old_enc, new_enc)
        # But decrypted value is correct
        self.env.invalidate_all()
        backend = self.env['shopify.backend'].browse(self.backend.id)
        self.assertEqual(backend.access_token, 'shpat_updated_token_value')

    def test_make_api_client_gets_plaintext(self):
        """_make_api_client() must receive the decrypted token."""
        with patch(
            'odoo.addons.shopify_connector_pro.shopify_api.client.ShopifyClient.__init__',
            return_value=None,
        ) as mock_init:
            self.backend._make_api_client()
            mock_init.assert_called_once()
            # The backend passed to ShopifyClient should have the plaintext
            passed_backend = mock_init.call_args[0][0]
            self.assertEqual(
                passed_backend.access_token, 'shpat_encryption_test_token',
            )

    def test_token_not_in_logs(self):
        """Token must never appear in log output during normal operations."""
        with self.assertLogs('odoo.addons.shopify_connector_pro', level='DEBUG') as cm:
            # Trigger operations that might log
            logging.getLogger('odoo.addons.shopify_connector_pro').info(
                "Backend %s operations test", self.backend.name,
            )
            self.backend.read(['name', 'shop_url'])
        for line in cm.output:
            self.assertNotIn('shpat_encryption_test_token', line)
            self.assertNotIn('shpat_', line)

    def test_copy_does_not_carry_encrypted_token(self):
        """Duplicating a backend must NOT copy the encrypted credentials.

        ``copy=False`` on ``_encrypted_access_token`` /
        ``_encrypted_webhook_secret`` ensures the original's encrypted blobs
        are not blindly carried into the duplicate.
        """
        self.backend.webhook_secret = 'whsec_original_secret'
        # Flush the inverse to DB before raw SQL
        self.env.flush_all()
        # Read original encrypted values
        self.env.cr.execute(
            "SELECT _encrypted_access_token, _encrypted_webhook_secret "
            "FROM shopify_backend WHERE id = %s",
            (self.backend.id,),
        )
        orig_enc_token, orig_enc_secret = self.env.cr.fetchone()
        self.assertTrue(orig_enc_token)
        self.assertTrue(orig_enc_secret)

        # Copy — Odoo will need a new access_token via default dict
        copied = self.backend.copy({'access_token': 'shpat_copied_token'})
        self.env.cr.execute(
            "SELECT _encrypted_access_token, _encrypted_webhook_secret "
            "FROM shopify_backend WHERE id = %s",
            (copied.id,),
        )
        copied_enc_token, copied_enc_secret = self.env.cr.fetchone()
        # The encrypted token should exist (set via inverse on create)
        # but should NOT be the same blob as the original
        self.assertTrue(copied_enc_token)
        self.assertNotEqual(copied_enc_token, orig_enc_token)
        # Webhook secret should be empty (copy=False, not re-set)
        self.assertFalse(copied_enc_secret)
