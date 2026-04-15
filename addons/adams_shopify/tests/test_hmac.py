# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import base64
import hashlib
import hmac
import unittest


class TestHMACVerification(unittest.TestCase):
    """Test HMAC verification logic used in the webhook controller."""

    def _verify_hmac(self, raw_body, hmac_header, secret):
        """Replicate the controller's HMAC verification logic."""
        if not secret or not hmac_header:
            return False
        computed = base64.b64encode(
            hmac.new(
                secret.encode('utf-8'),
                raw_body,
                hashlib.sha256,
            ).digest()
        ).decode('utf-8')
        return hmac.compare_digest(computed, hmac_header)

    def test_valid_hmac(self):
        """Should return True for a correctly signed payload."""
        secret = 'my_webhook_secret'
        body = b'{"id": 123, "topic": "products/create"}'
        expected = base64.b64encode(
            hmac.new(secret.encode(), body, hashlib.sha256).digest()
        ).decode()
        self.assertTrue(self._verify_hmac(body, expected, secret))

    def test_invalid_hmac(self):
        """Should return False for a tampered payload."""
        secret = 'my_webhook_secret'
        body = b'{"id": 123}'
        wrong_hmac = base64.b64encode(b'wrong').decode()
        self.assertFalse(self._verify_hmac(body, wrong_hmac, secret))

    def test_empty_secret(self):
        """Should return False if secret is empty."""
        self.assertFalse(self._verify_hmac(b'data', 'some_hmac', ''))

    def test_empty_hmac_header(self):
        """Should return False if HMAC header is empty."""
        self.assertFalse(self._verify_hmac(b'data', '', 'secret'))

    def test_none_values(self):
        """Should handle None values without crashing."""
        self.assertFalse(self._verify_hmac(b'data', None, 'secret'))
        self.assertFalse(self._verify_hmac(b'data', 'hmac', None))

    def test_different_secrets(self):
        """Same body with different secrets should fail."""
        body = b'{"test": true}'
        secret1 = 'secret_one'
        secret2 = 'secret_two'
        hmac1 = base64.b64encode(
            hmac.new(secret1.encode(), body, hashlib.sha256).digest()
        ).decode()
        self.assertFalse(self._verify_hmac(body, hmac1, secret2))

    def test_empty_body(self):
        """Should work with empty body."""
        secret = 'test_secret'
        body = b''
        expected = base64.b64encode(
            hmac.new(secret.encode(), body, hashlib.sha256).digest()
        ).decode()
        self.assertTrue(self._verify_hmac(body, expected, secret))
