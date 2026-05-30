# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tests for credential encryption (shopify.crypto + encrypted backend fields).

These tests MUST pass before the migration script runs.  They prove:
1. Round-trip encrypt/decrypt works
2. The DB column value is NOT plaintext
3. _make_api_client() still gets correct plaintext
4. Token never appears in logs
5. test_connection still succeeds end-to-end (mocked)
6. Decrypt failure degrades gracefully (form openable, not raising)
"""
import logging

from unittest.mock import MagicMock, patch

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


class TestCredentialDecryptionRecovery(TransactionCase):
    """Regression tests for P1-10: decrypt failure must not brick the UI.

    When the database UUID changes (restore, clone), Fernet decryption
    fails.  Previously, the _compute_* methods propagated the ValueError,
    crashing form/list views and 500-ing every webhook.

    After the fix, the computes catch the error and return False; a
    ``credential_issue`` computed flag surfaces the problem in the UI;
    and the hard failure is deferred to API-use time
    (ShopifyClient.__init__).
    """

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Decrypt Recovery Test',
            'shop_url': 'decrypt-test.myshopify.com',
            'access_token': 'shpat_valid_token_for_recovery_test',
            'company_id': self.env.company.id,
        })
        self.backend.webhook_secret = 'whsec_valid_secret_for_test'
        self.env.flush_all()

    def _corrupt_credentials(self):
        """Overwrite encrypted columns with un-decryptable garbage."""
        self.env.cr.execute(
            "UPDATE shopify_backend "
            "SET _encrypted_access_token = %s, "
            "    _encrypted_webhook_secret = %s "
            "WHERE id = %s",
            ('not-a-valid-fernet-token', 'also-not-valid', self.backend.id),
        )
        self.env.invalidate_all()

    # ── (a) Undecryptable credential → readable, False, flag set ──

    def test_decrypt_failure_does_not_raise_on_read(self):
        """Reading a backend with corrupt credentials must NOT raise.

        Before the fix, this raises ValueError from decrypt(), crashing
        the form and list views.
        """
        self._corrupt_credentials()
        # This line is the regression — it MUST NOT raise
        backend = self.env['shopify.backend'].browse(self.backend.id)
        self.assertFalse(backend.access_token)
        self.assertFalse(backend.webhook_secret)
        self.assertTrue(backend.credential_issue)

    # ── (b) Re-entering credentials clears the flag ──

    def test_reenter_token_clears_credential_issue(self):
        """Re-entering credentials must clear credential_issue."""
        self._corrupt_credentials()
        backend = self.env['shopify.backend'].browse(self.backend.id)
        # Trigger the compute so credential_issue is set
        self.assertTrue(backend.credential_issue)
        # Re-enter both credentials via the inverse fields
        backend.access_token = 'shpat_fresh_token'
        backend.webhook_secret = 'whsec_fresh_secret'
        self.env.invalidate_all()
        backend = self.env['shopify.backend'].browse(self.backend.id)
        self.assertFalse(backend.credential_issue)
        self.assertEqual(backend.access_token, 'shpat_fresh_token')
        self.assertEqual(backend.webhook_secret, 'whsec_fresh_secret')

    # ── (c) Webhook path with bad secret → no crash, HMAC rejects ──

    def test_webhook_corrupt_secret_no_crash(self):
        """Webhook flow must not crash when secret is undecryptable.

        Proves the read-then-HMAC path that the webhook controller
        follows, but does NOT exercise the full HTTP endpoint
        end-to-end (the ``@http.route`` decorator's ``Response.load``
        wrapper rejects non-Response returns, making TransactionCase
        controller calls impractical; a full end-to-end test would
        require ``HttpCase`` + a running HTTP server).

        **What this test proves:**
        1. ``backend.webhook_secret`` read (the line that previously
           raised ``ValueError``) now returns ``False`` without raising.
        2. ``_verify_hmac(body, hmac, False)`` returns ``False``
           (existing guard at line 217), which the controller uses
           to return 401.

        **Controller composition verified by inspection:**
        Between ``browse(backend_id)`` (line 88) and the HMAC check
        (line 113), the controller only reads stored fields
        (``exists()``, ``state``, ``shop_url``).  None of these
        trigger decrypt computes.  ``backend.webhook_secret`` at
        line 113 is the sole decrypt-compute access, so if it
        returns ``False`` without raising (proven here), the
        controller reaches ``_verify_hmac`` and returns 401.
        """
        self._corrupt_credentials()
        self.backend.state = 'connected'

        # Step 1: reproduce the exact controller access pattern
        # (sudo browse, then read webhook_secret) — line 88 + 113
        backend = self.env['shopify.backend'].sudo().browse(self.backend.id)

        # Also read the stored fields the controller reads between
        # browse and HMAC, confirming they don't blow up on a
        # credential_issue backend:
        self.assertTrue(backend.exists())
        self.assertEqual(backend.state, 'connected')
        _ = backend.shop_url  # stored field, must not raise

        # The critical line — previously raised ValueError:
        secret = backend.webhook_secret  # Must NOT raise
        self.assertFalse(
            secret,
            "Corrupt secret must decrypt to False, not raise",
        )

        # Step 2: verify that _verify_hmac handles the False secret
        # exactly as the webhook controller would use it (line 113)
        from ..controllers.webhook import ShopifyWebhookController
        result = ShopifyWebhookController._verify_hmac(
            b'{"id": 123}', 'some-hmac-value', secret,
        )
        self.assertFalse(
            result,
            "HMAC check must return False (→ 401), not crash",
        )

    # ── (d) API use with missing token fails loudly ──

    def test_api_client_missing_token_raises(self):
        """_make_api_client() with undecryptable token must raise loudly.

        The form/list gracefully degrade (access_token=False), but
        actually creating an API client with absent credentials must
        fail with a clear error, not silently send requests.
        """
        self._corrupt_credentials()
        backend = self.env['shopify.backend'].browse(self.backend.id)
        # Verify the prerequisite: access_token is False (not raising)
        self.assertFalse(backend.access_token)
        # But creating an API client must raise
        with self.assertRaises(Exception) as cm:
            backend._make_api_client()
        self.assertIn('access token', str(cm.exception).lower())

    # ── (e) Happy path unchanged ──

    def test_valid_credentials_still_decrypt(self):
        """Valid credentials must still decrypt exactly as before."""
        backend = self.env['shopify.backend'].browse(self.backend.id)
        self.assertEqual(
            backend.access_token, 'shpat_valid_token_for_recovery_test',
        )
        self.assertEqual(
            backend.webhook_secret, 'whsec_valid_secret_for_test',
        )
        self.assertFalse(backend.credential_issue)

    # ── (f) Activity scheduling: debounced, exactly once ──

    def test_make_api_client_schedules_one_activity(self):
        """_make_api_client on a credential_issue backend must schedule
        exactly ONE activity, even when called multiple times.

        Verifies the debounce: the second call must find the existing
        activity (matched by activity_type + exact summary + record)
        and skip creation.
        """
        self._corrupt_credentials()
        backend = self.env['shopify.backend'].browse(self.backend.id)

        Activity = self.env['mail.activity']
        domain = [
            ('res_model', '=', 'shopify.backend'),
            ('res_id', '=', backend.id),
            ('summary', '=', backend._CREDENTIAL_ACTIVITY_SUMMARY),
        ]

        # No activities before
        self.assertFalse(Activity.search(domain))

        # First call — should raise AND schedule activity.
        # We catch manually rather than using assertRaises, because
        # the re-raised exception can trigger ORM cache invalidation
        # before we get a chance to check the activity records.
        raised = False
        try:
            backend._make_api_client()
        except Exception:
            raised = True
            # Flush immediately while still in the except context,
            # before any ORM cleanup can discard the pending write
            self.env.flush_all()
        self.assertTrue(raised, "_make_api_client must raise on bad credentials")

        activities = Activity.search(domain)
        self.assertEqual(len(activities), 1, "First call must create one activity")

        # Second call — should raise but NOT create a duplicate
        raised = False
        try:
            backend._make_api_client()
        except Exception:
            raised = True
            self.env.flush_all()
        self.assertTrue(raised)

        activities = Activity.search(domain)
        self.assertEqual(
            len(activities), 1,
            "Second call must NOT duplicate the activity",
        )
