import inspect
import json
import re
from unittest.mock import patch

import requests

from odoo.tests.common import TransactionCase

from ..models import shopify_connector_api_client as client_module
from ..models.shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    ERROR_THROTTLE,
    ERROR_UNKNOWN,
    ShopifyClientError,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class FakeResponse:
    """Minimal stand-in for a `requests.Response` used by the `_send()`
    transport-injection seam -- no network call is ever made in this
    test module."""

    def __init__(
        self, status_code, json_body=None, headers=None, text=None,
        json_error=False,
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_body = json_body
        self._json_error = json_error
        if text is not None:
            self.text = text
        elif json_body is not None:
            self.text = json.dumps(json_body)
        else:
            self.text = ''

    def json(self):
        if self._json_error:
            raise ValueError('malformed JSON body')
        return self._json_body


def _success_body(domain='api-client-test.myshopify.com'):
    return {
        'data': {
            'shop': {
                'id': 'gid://shopify/Shop/1',
                'name': 'Test Shop',
                'myshopifyDomain': domain,
            },
            'currentAppInstallation': {
                'accessScopes': [{'handle': 'read_products'}],
            },
        },
    }


class TestApiClient(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'API Client Test Store',
            'shop_domain': 'api-client-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN
        )
        cls.Client = cls.env['shopify.connector.api.client']

    def _execute_with(self, fake_send):
        with patch.object(type(self.Client), '_send', fake_send):
            return self.Client.execute(self.store, 'query { shop { id } }')

    def _raises_with(self, response):
        with self.assertRaises(ShopifyClientError) as catcher:
            self._execute_with(lambda self, store, body, r=response: r)
        return catcher.exception

    # 1. Success fixture -> execute() returns parsed data, no exception.
    def test_success_fixture_returns_parsed_data(self):
        response = FakeResponse(200, json_body=_success_body())
        result = self._execute_with(lambda self, store, body: response)
        self.assertNotIn('version_fallforward', result)
        self.assertEqual(result['data']['shop']['name'], 'Test Shop')
        self.assertEqual(
            result['data']['currentAppInstallation']['accessScopes'],
            [{'handle': 'read_products'}],
        )

    # 2. ACCESS_DENIED (200-OK GraphQL error).
    def test_access_denied_graphql_error(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Access denied',
                'extensions': {'code': 'ACCESS_DENIED'},
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertTrue(exc.credential_invalid)

    # 3. THROTTLED (fixture marked unofficial/unconfirmed shape).
    def test_throttled_graphql_error_unofficial_shape(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            # unofficial/unconfirmed shape -- Open question #1/#3,
            # credential-connection-api-client-planning.md.
            'errors': [{
                'message': 'Throttled',
                'extensions': {'code': 'THROTTLED'},
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_THROTTLE)
        self.assertFalse(exc.credential_invalid)

    # 4. MAX_COST_EXCEEDED (official sample shape) -> unknown_system_error.
    def test_max_cost_exceeded_maps_to_unknown(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Query cost exceeded',
                'extensions': {
                    'code': 'MAX_COST_EXCEEDED', 'cost': 1200, 'maxCost': 1000,
                },
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_UNKNOWN)

    # 5. INTERNAL_SERVER_ERROR + requestId -> requestId in technical_detail.
    def test_internal_server_error_includes_request_id(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Internal error',
                'extensions': {
                    'code': 'INTERNAL_SERVER_ERROR', 'requestId': 'req-abc-123',
                },
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_TEMPORARY)
        self.assertIn('req-abc-123', exc.technical_detail)

    # 6. HTTP 401 -> auth, credential_invalid True (unconfirmed HTTP shape).
    def test_http_401_maps_to_auth_credential_invalid(self):
        exc = self._raises_with(FakeResponse(401, text='Unauthorized'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertTrue(exc.credential_invalid)

    # 7. HTTP 402 -> auth, credential_invalid False, billing/payment reason.
    def test_http_402_frozen_shop(self):
        exc = self._raises_with(FakeResponse(402, text='Payment required'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('billing/payment', exc.reason)

    # 8. HTTP 423 -> auth, credential_invalid False, locked reason.
    def test_http_423_locked_shop(self):
        exc = self._raises_with(FakeResponse(423, text='Locked'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('locked', exc.reason.lower())

    # 9. HTTP 403 -> auth, credential_invalid False, fraudulent reason.
    def test_http_403_fraudulent_store(self):
        exc = self._raises_with(FakeResponse(403, text='Fraudulent store'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('fraudulent', exc.reason.lower())

    # 10. SHOP_INACTIVE -> auth, credential_invalid False, inactive reason.
    def test_shop_inactive(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Shop inactive',
                'extensions': {'code': 'SHOP_INACTIVE'},
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('inactive', exc.reason.lower())

    # 11. HTTP 429 -> throttling.
    def test_http_429_throttled(self):
        exc = self._raises_with(FakeResponse(429, text='Too Many Requests'))
        self.assertEqual(exc.error_class, ERROR_THROTTLE)

    # 12. HTTP 500 -> temporary/network.
    def test_http_500_temporary(self):
        exc = self._raises_with(FakeResponse(500, text='Internal Server Error'))
        self.assertEqual(exc.error_class, ERROR_TEMPORARY)

    # 13. Timeout (simulated) -> temporary/network.
    def test_timeout_simulated(self):
        def raise_timeout(self, store, body):
            raise requests.exceptions.ConnectTimeout('simulated connect timeout')

        with self.assertRaises(ShopifyClientError) as catcher:
            self._execute_with(raise_timeout)
        self.assertEqual(catcher.exception.error_class, ERROR_TEMPORARY)

    # 14. Malformed JSON body -> unknown_system_error.
    def test_malformed_json_body(self):
        exc = self._raises_with(
            FakeResponse(200, text='not json', json_error=True)
        )
        self.assertEqual(exc.error_class, ERROR_UNKNOWN)

    # 15. X-Shopify-API-Version header mismatch -> version_fallforward, no exception.
    def test_version_fallforward_no_exception(self):
        response = FakeResponse(
            200, json_body=_success_body(),
            headers={'X-Shopify-API-Version': '2026-10'},
        )
        result = self._execute_with(lambda self, store, body: response)
        self.assertTrue(result.get('version_fallforward'))
        self.assertEqual(result.get('served_version'), '2026-10')

    # 16. The five permission-scope-auth reasons are pairwise distinct.
    def test_five_permission_scope_auth_reasons_pairwise_distinct(self):
        fixtures = {
            '402': FakeResponse(402, text='Payment required'),
            '423': FakeResponse(423, text='Locked'),
            '403': FakeResponse(403, text='Fraudulent'),
            'SHOP_INACTIVE': FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'SHOP_INACTIVE'},
                }],
            }),
            'ACCESS_DENIED': FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'ACCESS_DENIED'},
                }],
            }),
        }
        reasons = {label: self._raises_with(response).reason
                   for label, response in fixtures.items()}
        self.assertEqual(len(set(reasons.values())), len(reasons))

    # 17. Redaction: dummy token embedded in an error body/text.
    def test_redaction_of_dummy_token_in_error_body(self):
        leaking_token = 'shpat_DUMMYDUMMYDUMMY9999999999999999'
        exc = self._raises_with(
            FakeResponse(500, text='Internal error, token=%s' % leaking_token)
        )
        self.assertNotIn(leaking_token, str(exc))
        self.assertNotIn(leaking_token, exc.reason)
        self.assertNotIn(leaking_token, exc.technical_detail or '')

    # 18. Read-only guarantee: no mutation operation string; minimal public surface.
    def test_read_only_guarantee(self):
        source = inspect.getsource(client_module)
        self.assertIsNone(
            re.search(r'\bmutation\s*[\{\(]', source),
            'no GraphQL mutation operation string may appear in the client module',
        )
        public_methods = {
            name for name, value in vars(
                client_module.ShopifyConnectorApiClient
            ).items()
            if callable(value) and not name.startswith('_')
        }
        # CORE-R2 (AR-047) adds exactly one public entry point:
        # `execute_business`, the committed-admission-lease context manager.
        self.assertEqual(public_methods, {'execute', 'execute_business'})

    # 20 (CORE-R2 regression). execute() preserves the two-arg `_send` seam.
    # The token-snapshot change makes `_send(store, body, token=None)`; the
    # legacy execute() path must still call it as `_send(store, body)` (reading
    # the token itself), so the transport-seam tests that patch a two-arg
    # `_send` keep working and existing execute() callers stay operational.
    def test_execute_preserves_two_arg_send_seam(self):
        received = {}

        def fake_send(self, store, body, *extra):
            received['extra'] = extra
            return FakeResponse(200, json_body=_success_body())

        result = self._execute_with(fake_send)
        self.assertEqual(received['extra'], ())
        self.assertEqual(result['data']['shop']['name'], 'Test Shop')

    # 19. No credential leak across every fixture used above.
    def test_no_credential_leak_across_fixtures(self):
        fixtures = [
            FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'ACCESS_DENIED'},
                }],
            }),
            FakeResponse(401, text='Unauthorized %s' % DUMMY_TOKEN),
            FakeResponse(402, text='Payment required %s' % DUMMY_TOKEN),
            FakeResponse(500, text='Server error %s' % DUMMY_TOKEN),
        ]
        for response in fixtures:
            exc = self._raises_with(response)
            self.assertNotIn(DUMMY_TOKEN, str(exc))
            self.assertNotIn(DUMMY_TOKEN, exc.reason)
            self.assertNotIn(DUMMY_TOKEN, exc.technical_detail or '')
